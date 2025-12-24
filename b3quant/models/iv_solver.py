"""
Implied Volatility Solver with multiple robust methods.

Implements a three-tier solver architecture:
1. Pre-validation & edge case filtering
2. Fast path: Newton-Raphson with vega
3. Robust fallback: Brent's method

Based on academic research and industry best practices:
- Brenner & Subrahmanyam (1988): Initial guess approximation
- Jäckel, P. (2015): "Let's Be Rational" - Advanced methods
- Industry standards: CBOE, Bloomberg approaches

Examples:
    >>> from b3quant.models.iv_solver import ImpliedVolatilitySolver
    >>> solver = ImpliedVolatilitySolver()
    >>>
    >>> # Single option
    >>> iv = solver.solve(
    ...     price=5.50,
    ...     S=100,
    ...     K=100,
    ...     T=30/365,
    ...     r=0.05,
    ...     option_type='call'
    ... )
    >>>
    >>> # Vectorized (entire option chain)
    >>> ivs = solver.solve_vectorized(
    ...     prices=prices_array,
    ...     S=S_array,
    ...     K=K_array,
    ...     T=T_array,
    ...     r=r,
    ...     option_type='call'
    ... )
"""

import logging
from typing import Literal

import numpy as np
from scipy.optimize import brentq
from scipy.stats import norm

from .. import config

logger = logging.getLogger(__name__)


class ImpliedVolatilitySolver:
    """
    Multi-method implied volatility solver.

    Uses a three-tier architecture for robustness and performance:
    - Tier 1: Validation and edge case filtering
    - Tier 2: Newton-Raphson solver (fast path)
    - Tier 3: Brent's method (robust fallback)

    Attributes:
        max_iterations: Maximum iterations for Newton-Raphson
        tolerance: Convergence tolerance (price error)
        min_vol: Minimum allowed volatility (default 0.01%)
        max_vol: Maximum allowed volatility (default 500%)
        damping: Damping factor for Newton-Raphson stability (0.5-1.0)
        vega_threshold: Minimum vega for Newton-Raphson
    """

    def __init__(
        self,
        max_iterations: int | None = None,
        tolerance: float | None = None,
        min_vol: float | None = None,
        max_vol: float | None = None,
        damping: float = 0.8,
        vega_threshold: float = 1e-6,
    ):
        """
        Initialize IV solver.

        Args:
            max_iterations: Max iterations for Newton-Raphson
            tolerance: Price error tolerance
            min_vol: Minimum volatility bound
            max_vol: Maximum volatility bound
            damping: Newton-Raphson damping factor (0.5-1.0)
            vega_threshold: Minimum vega for Newton-Raphson
        """
        self.max_iterations = max_iterations or config.IV_SOLVER_MAX_ITERATIONS
        self.tolerance = tolerance or config.IV_SOLVER_TOLERANCE
        self.min_vol = min_vol or config.IV_SOLVER_MIN_VOL
        self.max_vol = max_vol or config.IV_SOLVER_MAX_VOL
        self.damping = damping
        self.vega_threshold = vega_threshold

    def solve(
        self,
        price: float,
        S: float,
        K: float,
        T: float,
        r: float,
        q: float = 0.0,
        option_type: Literal["call", "put"] = "call",
        method: Literal["auto", "newton", "brent"] = "auto",
    ) -> float | None:
        """
        Calculate implied volatility for a single option.

        Args:
            price: Market price of the option
            S: Spot price of underlying
            K: Strike price
            T: Time to maturity (years)
            r: Risk-free rate
            q: Dividend yield (default 0)
            option_type: 'call' or 'put'
            method: Solver method ('auto', 'newton', 'brent')

        Returns:
            Implied volatility (σ), or None if calculation fails

        Examples:
            >>> solver = ImpliedVolatilitySolver()
            >>> iv = solver.solve(5.50, S=100, K=100, T=0.25, r=0.05)
            >>> print(f"IV: {iv:.2%}")
        """
        # Tier 1: Pre-validation & edge case filtering
        if not self._validate_inputs(price, S, K, T, r, q):
            return None

        # Check if deep ITM (nearly intrinsic value)
        intrinsic = self._intrinsic_value(S, K, option_type)
        if price - intrinsic < config.IV_INTRINSIC_MARGIN:
            logger.debug(
                f"Option too close to intrinsic value: {price:.4f} vs {intrinsic:.4f}"
            )
            return None

        # Handle near expiration (T < 1 day)
        if T < 1 / 365:
            logger.debug(f"Time to expiry too small: {T:.6f} years")
            return self._handle_near_expiry(price, S, K, T, r, q, option_type)

        # Tier 2: Fast path (Newton-Raphson)
        if method in ("auto", "newton"):
            # Get initial guess
            sigma_0 = self._initial_guess(price, S, K, T, option_type)

            iv = self._newton_raphson(price, S, K, T, r, q, option_type, sigma_0)

            if iv is not None and self.min_vol <= iv <= self.max_vol:
                return iv

            if method == "newton":
                logger.warning("Newton-Raphson failed to converge")
                return None

        # Tier 3: Robust fallback (Brent's method)
        if method in ("auto", "brent"):
            try:
                return self._brent_method(price, S, K, T, r, q, option_type)
            except Exception as e:
                logger.warning(f"Brent's method failed: {e}")
                return None

        return None

    def solve_vectorized(
        self,
        prices: np.ndarray,
        S: np.ndarray | float,
        K: np.ndarray,
        T: np.ndarray | float,
        r: float | np.ndarray,
        q: float | np.ndarray = 0.0,
        option_type: Literal["call", "put"] | np.ndarray = "call",
        method: Literal["auto", "newton", "brent"] = "auto",
    ) -> np.ndarray:
        """
        Calculate implied volatilities for multiple options (vectorized).

        Args:
            prices: Array of market prices
            S: Spot price(s) - scalar or array
            K: Array of strike prices
            T: Time(s) to maturity - scalar or array
            r: Risk-free rate(s) - scalar or array
            q: Dividend yield(s) - scalar or array (default 0)
            option_type: 'call', 'put', or array of types
            method: Solver method

        Returns:
            Array of implied volatilities (NaN for failed calculations)

        Examples:
            >>> solver = ImpliedVolatilitySolver()
            >>> ivs = solver.solve_vectorized(
            ...     prices=np.array([5.50, 3.20, 1.80]),
            ...     S=100,
            ...     K=np.array([100, 105, 110]),
            ...     T=0.25,
            ...     r=0.05
            ... )
        """
        n = len(prices)
        ivs = np.full(n, np.nan)

        # Broadcast scalars to arrays
        if np.isscalar(S):
            S = np.full(n, S)
        if np.isscalar(T):
            T = np.full(n, T)
        if np.isscalar(r):
            r = np.full(n, r)
        if np.isscalar(q):
            q = np.full(n, q)
        if isinstance(option_type, str):
            option_type = np.array([option_type] * n)

        # Solve for each option
        for i in range(n):
            try:
                iv = self.solve(
                    price=prices[i],
                    S=S[i],  # type: ignore[index]
                    K=K[i],
                    T=T[i],  # type: ignore[index]
                    r=r[i],  # type: ignore[index]
                    q=q[i],  # type: ignore[index]
                    option_type=option_type[i],  # type: ignore[index]
                    method=method,
                )
                if iv is not None:
                    ivs[i] = iv
            except Exception as e:
                logger.debug(f"Failed to solve IV for option {i}: {e}")
                continue

        return ivs

    def _validate_inputs(
        self,
        price: float,
        S: float,
        K: float,
        T: float,
        r: float,
        q: float,
    ) -> bool:
        """Validate input parameters."""
        # Price must be positive
        if price <= 0:
            logger.debug(f"Invalid price: {price}")
            return False

        # Spot and strike must be positive
        if S <= 0 or K <= 0:
            logger.debug(f"Invalid S or K: S={S}, K={K}")
            return False

        # Time must be positive
        if T <= 0:
            logger.debug(f"Invalid time to maturity: {T}")
            return False

        # Check arbitrage bounds
        intrinsic = max(S - K, 0)  # For calls
        if price < intrinsic:
            logger.debug(f"Price below intrinsic: {price} < {intrinsic}")
            return False

        if price > S:  # Call can't be worth more than stock
            logger.debug(f"Call price > stock price: {price} > {S}")
            return False

        return True

    def _intrinsic_value(self, S: float, K: float, option_type: str) -> float:
        """Calculate intrinsic value."""
        if option_type.lower() == "call":
            return max(S - K, 0)
        else:
            return max(K - S, 0)

    def _initial_guess(
        self,
        price: float,
        S: float,
        K: float,
        T: float,
        option_type: str,
    ) -> float:
        """
        Generate initial volatility guess using Brenner-Subrahmanyam approximation.

        For ATM options: σ ≈ √(2π/T) * (C/S)

        Reference:
            Brenner & Subrahmanyam (1988)
            "A Simple Formula to Compute the Implied Standard Deviation"
        """
        # Brenner-Subrahmanyam works best for ATM options
        moneyness = abs(np.log(S / K))

        if moneyness < 0.1:  # Near ATM
            sigma_guess = np.sqrt(2 * np.pi / T) * (price / S)
        else:
            # For ITM/OTM, use a heuristic based on moneyness
            sigma_guess = 0.2 + moneyness  # Start with higher vol for OTM

        # Ensure guess is within bounds
        return float(np.clip(sigma_guess, self.min_vol, self.max_vol))

    def _newton_raphson(
        self,
        price: float,
        S: float,
        K: float,
        T: float,
        r: float,
        q: float,
        option_type: str,
        sigma_0: float,
    ) -> float | None:
        """
        Newton-Raphson IV solver using vega as derivative.

        σ_(n+1) = σ_n - α * [BS_Price(σ_n) - Market_Price] / Vega(σ_n)

        where α is the damping factor (0.5-1.0) for stability.
        """
        sigma = sigma_0

        for iteration in range(self.max_iterations):
            # Calculate BS price and vega
            bs_price = self._black_scholes_price(S, K, T, r, sigma, q, option_type)
            vega_val = self._vega(S, K, T, r, sigma, q)

            # Check convergence
            price_diff = bs_price - price
            if abs(price_diff) < self.tolerance:
                return sigma

            # Check vega threshold (avoid division by very small numbers)
            if vega_val < self.vega_threshold:
                logger.debug(
                    f"Vega too small ({vega_val:.2e}) at iteration {iteration}"
                )
                return None  # Fall back to Brent

            # Newton-Raphson update with damping
            sigma_new = sigma - self.damping * (price_diff / vega_val)

            # Enforce bounds
            sigma_new = float(np.clip(sigma_new, self.min_vol, self.max_vol))

            # Check for convergence in sigma
            if abs(sigma_new - sigma) < 1e-8:
                return sigma_new

            sigma = sigma_new

        logger.debug(
            f"Newton-Raphson did not converge after {self.max_iterations} iterations"
        )
        return None

    def _brent_method(
        self,
        price: float,
        S: float,
        K: float,
        T: float,
        r: float,
        q: float,
        option_type: str,
    ) -> float:
        """
        Brent's method for robust IV calculation.

        Guaranteed to converge if root is bracketed.
        Uses scipy.optimize.brentq for optimized implementation.
        """

        def objective(sigma: float) -> float:
            bs_price = self._black_scholes_price(S, K, T, r, sigma, q, option_type)
            return bs_price - price

        # Use brentq with explicit bounds
        return brentq(
            objective,
            a=self.min_vol,
            b=self.max_vol,
            xtol=self.tolerance,
            rtol=self.tolerance,
            maxiter=100,
        )

    def _handle_near_expiry(
        self,
        price: float,
        S: float,
        K: float,
        T: float,
        r: float,
        q: float,
        option_type: str,
    ) -> float | None:
        """Handle options very close to expiration (T < 1 day)."""
        # Use floor of 1 day for numerical stability
        T_safe = max(T, 1 / 365)

        # Use Brent's method for near-expiry options (more robust)
        try:
            return self._brent_method(price, S, K, T_safe, r, q, option_type)
        except Exception:
            return None

    def _black_scholes_price(
        self,
        S: float,
        K: float,
        T: float,
        r: float,
        sigma: float,
        q: float,
        option_type: str,
    ) -> float:
        """Calculate Black-Scholes option price."""
        d1 = (np.log(S / K) + (r - q + 0.5 * sigma**2) * T) / (sigma * np.sqrt(T))
        d2 = d1 - sigma * np.sqrt(T)

        if option_type.lower() == "call":
            return float(
                S * np.exp(-q * T) * norm.cdf(d1) - K * np.exp(-r * T) * norm.cdf(d2)
            )
        else:
            return float(
                K * np.exp(-r * T) * norm.cdf(-d2) - S * np.exp(-q * T) * norm.cdf(-d1)
            )

    def _vega(
        self,
        S: float,
        K: float,
        T: float,
        r: float,
        sigma: float,
        q: float,
    ) -> float:
        """Calculate option vega (∂Price/∂σ)."""
        d1 = (np.log(S / K) + (r - q + 0.5 * sigma**2) * T) / (sigma * np.sqrt(T))
        return float(S * np.exp(-q * T) * norm.pdf(d1) * np.sqrt(T))
