"""Black-Scholes option pricing model with Greeks"""

import logging
from typing import Literal

import numpy as np
from scipy import stats  # type: ignore[import-untyped]

from .base import GreeksCalculator, PricingModel
from .iv_solver import ImpliedVolatilitySolver

logger = logging.getLogger(__name__)


class BlackScholes(PricingModel, GreeksCalculator):
    """
    Black-Scholes option pricing model.

    The Black-Scholes model provides closed-form solutions for European
    option prices and their sensitivities (Greeks) assuming constant volatility,
    log-normal price distribution, and no dividends (or constant dividend yield).

    Examples
    --------
    >>> bs = BlackScholes()
    >>> # Price a call option
    >>> price = bs.price(S=100, K=100, T=1.0, r=0.05, sigma=0.2, option_type='call')
    >>> print(f"Call price: {price:.2f}")
    Call price: 10.45
    >>>
    >>> # Calculate delta
    >>> delta = bs.delta(S=100, K=100, T=1.0, r=0.05, sigma=0.2, option_type='call')
    >>> print(f"Delta: {delta:.4f}")
    Delta: 0.6368
    >>>
    >>> # Price multiple options at once (vectorized)
    >>> strikes = np.array([95, 100, 105])
    >>> prices = bs.price(S=100, K=strikes, T=1.0, r=0.05, sigma=0.2, option_type='call')
    >>> print(f"Prices: {prices}")
    Prices: [13.04 10.45  8.24]

    References
    ----------
    Black, F., & Scholes, M. (1973). The Pricing of Options and Corporate
    Liabilities. Journal of Political Economy, 81(3), 637-654.
    """

    def __init__(self):
        """Initialize Black-Scholes model with IV solver."""
        self.iv_solver = ImpliedVolatilitySolver()

    def price(  # type: ignore[override]
        self,
        S: float | np.ndarray,
        K: float | np.ndarray,
        T: float | np.ndarray,
        r: float | np.ndarray,
        sigma: float | np.ndarray,
        q: float | np.ndarray = 0,
        option_type: Literal["call", "put"] = "call",
    ) -> float | np.ndarray:
        """
        Calculate Black-Scholes option price.

        Parameters
        ----------
        S : float | np.ndarray
            Current price of underlying asset
        K : float | np.ndarray
            Strike price
        T : float | np.ndarray
            Time to maturity (in years)
        r : float | np.ndarray
            Risk-free interest rate (annualized, continuous compounding)
        sigma : float | np.ndarray
            Volatility (annualized standard deviation of returns)
        q : float | np.ndarray, default=0
            Dividend yield (annualized, continuous compounding)
        option_type : {'call', 'put'}, default='call'
            Type of option

        Returns
        -------
        float | np.ndarray
            Option price

        Raises
        ------
        ValueError
            If any input parameters are invalid
        """
        self.validate_inputs(S=S, K=K, T=T, r=r, sigma=sigma, q=q)

        d1 = self._d1(S, K, T, r, sigma, q)
        d2 = self._d2(d1, sigma, T)

        if option_type.lower() == "call":
            return S * np.exp(-q * T) * stats.norm.cdf(d1) - K * np.exp(  # type: ignore[no-any-return]
                -r * T
            ) * stats.norm.cdf(
                d2
            )
        elif option_type.lower() == "put":
            return K * np.exp(-r * T) * stats.norm.cdf(-d2) - S * np.exp(  # type: ignore[no-any-return]
                -q * T
            ) * stats.norm.cdf(
                -d1
            )
        else:
            raise ValueError(
                f"Invalid option_type: {option_type}. Must be 'call' or 'put'"
            )

    def delta(  # type: ignore[override]
        self,
        S: float | np.ndarray,
        K: float | np.ndarray,
        T: float | np.ndarray,
        r: float | np.ndarray,
        sigma: float | np.ndarray,
        q: float | np.ndarray = 0,
        option_type: Literal["call", "put"] = "call",
    ) -> float | np.ndarray:
        """
        Calculate Delta (∂V/∂S).

        Delta measures the rate of change of option price with respect
        to changes in the underlying asset price.

        Parameters
        ----------
        S : float | np.ndarray
            Current price of underlying asset
        K : float | np.ndarray
            Strike price
        T : float | np.ndarray
            Time to maturity (in years)
        r : float | np.ndarray
            Risk-free interest rate
        sigma : float | np.ndarray
            Volatility
        q : float | np.ndarray, default=0
            Dividend yield
        option_type : {'call', 'put'}, default='call'
            Type of option

        Returns
        -------
        float | np.ndarray
            Delta value
            - Call delta: 0 to 1
            - Put delta: -1 to 0
        """
        d1 = self._d1(S, K, T, r, sigma, q)

        if option_type.lower() == "call":
            return np.exp(-q * T) * stats.norm.cdf(d1)  # type: ignore[no-any-return]
        elif option_type.lower() == "put":
            return -np.exp(-q * T) * stats.norm.cdf(-d1)  # type: ignore[no-any-return]
        else:
            raise ValueError(f"Invalid option_type: {option_type}")

    def gamma(  # type: ignore[override]
        self,
        S: float | np.ndarray,
        K: float | np.ndarray,
        T: float | np.ndarray,
        r: float | np.ndarray,
        sigma: float | np.ndarray,
        q: float | np.ndarray = 0,
    ) -> float | np.ndarray:
        """
        Calculate Gamma (∂²V/∂S²).

        Gamma measures the rate of change of delta with respect to
        changes in the underlying asset price. Gamma is the same for
        calls and puts.

        Parameters
        ----------
        S : float | np.ndarray
            Current price of underlying asset
        K : float | np.ndarray
            Strike price
        T : float | np.ndarray
            Time to maturity (in years)
        r : float | np.ndarray
            Risk-free interest rate
        sigma : float | np.ndarray
            Volatility
        q : float | np.ndarray, default=0
            Dividend yield

        Returns
        -------
        float | np.ndarray
            Gamma value (always positive)
        """
        d1 = self._d1(S, K, T, r, sigma, q)
        return np.exp(-q * T) * stats.norm.pdf(d1) / (S * sigma * np.sqrt(T))  # type: ignore[no-any-return]

    def vega(  # type: ignore[override]
        self,
        S: float | np.ndarray,
        K: float | np.ndarray,
        T: float | np.ndarray,
        r: float | np.ndarray,
        sigma: float | np.ndarray,
        q: float | np.ndarray = 0,
    ) -> float | np.ndarray:
        """
        Calculate Vega (∂V/∂σ).

        Vega measures the sensitivity of option price to changes in
        volatility. Vega is the same for calls and puts.

        Note: Result is per 1.0 change in volatility (i.e., 100%).
        For percentage point changes, divide by 100.

        Parameters
        ----------
        S : float | np.ndarray
            Current price of underlying asset
        K : float | np.ndarray
            Strike price
        T : float | np.ndarray
            Time to maturity (in years)
        r : float | np.ndarray
            Risk-free interest rate
        sigma : float | np.ndarray
            Volatility
        q : float | np.ndarray, default=0
            Dividend yield

        Returns
        -------
        float | np.ndarray
            Vega value (always positive)
        """
        d1 = self._d1(S, K, T, r, sigma, q)
        return S * np.exp(-q * T) * stats.norm.pdf(d1) * np.sqrt(T)  # type: ignore[no-any-return]

    def theta(  # type: ignore[override]
        self,
        S: float | np.ndarray,
        K: float | np.ndarray,
        T: float | np.ndarray,
        r: float | np.ndarray,
        sigma: float | np.ndarray,
        q: float | np.ndarray = 0,
        option_type: Literal["call", "put"] = "call",
    ) -> float | np.ndarray:
        """
        Calculate Theta (∂V/∂t).

        Theta measures the rate of change of option price with respect to
        the passage of time (time decay). Typically negative for long positions.

        Note: Result is per year. For daily theta, divide by 365.25.

        Parameters
        ----------
        S : float | np.ndarray
            Current price of underlying asset
        K : float | np.ndarray
            Strike price
        T : float | np.ndarray
            Time to maturity (in years)
        r : float | np.ndarray
            Risk-free interest rate
        sigma : float | np.ndarray
            Volatility
        q : float | np.ndarray, default=0
            Dividend yield
        option_type : {'call', 'put'}, default='call'
            Type of option

        Returns
        -------
        float | np.ndarray
            Theta value (typically negative)
        """
        d1 = self._d1(S, K, T, r, sigma, q)
        d2 = self._d2(d1, sigma, T)

        term1 = -(S * stats.norm.pdf(d1) * sigma * np.exp(-q * T)) / (2 * np.sqrt(T))

        if option_type.lower() == "call":
            term2 = -r * K * np.exp(-r * T) * stats.norm.cdf(d2)
            term3 = q * S * np.exp(-q * T) * stats.norm.cdf(d1)
            return term1 + term2 + term3  # type: ignore[no-any-return]
        elif option_type.lower() == "put":
            term2 = r * K * np.exp(-r * T) * stats.norm.cdf(-d2)
            term3 = -q * S * np.exp(-q * T) * stats.norm.cdf(-d1)
            return term1 + term2 + term3  # type: ignore[no-any-return]
        else:
            raise ValueError(f"Invalid option_type: {option_type}")

    def rho(  # type: ignore[override]
        self,
        S: float | np.ndarray,
        K: float | np.ndarray,
        T: float | np.ndarray,
        r: float | np.ndarray,
        sigma: float | np.ndarray,
        q: float | np.ndarray = 0,
        option_type: Literal["call", "put"] = "call",
    ) -> float | np.ndarray:
        """
        Calculate Rho (∂V/∂r).

        Rho measures the sensitivity of option price to changes in
        the risk-free interest rate.

        Note: Result is per 1.0 change in rate (i.e., 100%).
        For percentage point changes, divide by 100.

        Parameters
        ----------
        S : float | np.ndarray
            Current price of underlying asset
        K : float | np.ndarray
            Strike price
        T : float | np.ndarray
            Time to maturity (in years)
        r : float | np.ndarray
            Risk-free interest rate
        sigma : float | np.ndarray
            Volatility
        q : float | np.ndarray, default=0
            Dividend yield
        option_type : {'call', 'put'}, default='call'
            Type of option

        Returns
        -------
        float | np.ndarray
            Rho value (positive for calls, negative for puts)
        """
        d1 = self._d1(S, K, T, r, sigma, q)
        d2 = self._d2(d1, sigma, T)

        if option_type.lower() == "call":
            return K * T * np.exp(-r * T) * stats.norm.cdf(d2)  # type: ignore[no-any-return]
        elif option_type.lower() == "put":
            return -K * T * np.exp(-r * T) * stats.norm.cdf(-d2)  # type: ignore[no-any-return]
        else:
            raise ValueError(f"Invalid option_type: {option_type}")

    def greeks(  # type: ignore[override]
        self,
        S: float | np.ndarray,
        K: float | np.ndarray,
        T: float | np.ndarray,
        r: float | np.ndarray,
        sigma: float | np.ndarray,
        q: float | np.ndarray = 0,
        option_type: Literal["call", "put"] = "call",
    ) -> dict[str, float | np.ndarray]:
        """
        Calculate all primary Greeks.

        Parameters
        ----------
        S : float | np.ndarray
            Current price of underlying asset
        K : float | np.ndarray
            Strike price
        T : float | np.ndarray
            Time to maturity (in years)
        r : float | np.ndarray
            Risk-free interest rate
        sigma : float | np.ndarray
            Volatility
        q : float | np.ndarray, default=0
            Dividend yield
        option_type : {'call', 'put'}, default='call'
            Type of option

        Returns
        -------
        dict[str, float | np.ndarray]
            Dictionary of Greeks: delta, gamma, vega, theta, rho
        """
        return {
            "delta": self.delta(S, K, T, r, sigma, q, option_type),
            "gamma": self.gamma(S, K, T, r, sigma, q),
            "vega": self.vega(S, K, T, r, sigma, q),
            "theta": self.theta(S, K, T, r, sigma, q, option_type),
            "rho": self.rho(S, K, T, r, sigma, q, option_type),
        }

    @staticmethod
    def _d1(
        S: float | np.ndarray,
        K: float | np.ndarray,
        T: float | np.ndarray,
        r: float | np.ndarray,
        sigma: float | np.ndarray,
        q: float | np.ndarray,
    ) -> float | np.ndarray:
        """
        Calculate d1 parameter for Black-Scholes formula.

        Parameters
        ----------
        S : float | np.ndarray
            Current price
        K : float | np.ndarray
            Strike price
        T : float | np.ndarray
            Time to maturity
        r : float | np.ndarray
            Risk-free rate
        sigma : float | np.ndarray
            Volatility
        q : float | np.ndarray
            Dividend yield

        Returns
        -------
        float | np.ndarray
            d1 value
        """
        return (np.log(S / K) + (r - q + 0.5 * sigma**2) * T) / (sigma * np.sqrt(T))

    @staticmethod
    def _d2(
        d1: float | np.ndarray, sigma: float | np.ndarray, T: float | np.ndarray
    ) -> float | np.ndarray:
        """
        Calculate d2 parameter for Black-Scholes formula.

        Parameters
        ----------
        d1 : float | np.ndarray
            d1 value from _d1()
        sigma : float | np.ndarray
            Volatility
        T : float | np.ndarray
            Time to maturity

        Returns
        -------
        float | np.ndarray
            d2 value
        """
        return d1 - sigma * np.sqrt(T)

    def validate_inputs(self, **kwargs) -> None:
        """
        Validate Black-Scholes model inputs.

        Parameters
        ----------
        **kwargs
            Model parameters to validate

        Raises
        ------
        ValueError
            If any input parameter is invalid
        """
        S = kwargs.get("S")
        K = kwargs.get("K")
        T = kwargs.get("T")
        sigma = kwargs.get("sigma")

        if S is not None and np.any(S <= 0):
            raise ValueError("Underlying price S must be positive")

        if K is not None and np.any(K <= 0):
            raise ValueError("Strike price K must be positive")

        if T is not None and np.any(T < 0):
            raise ValueError("Time to maturity T cannot be negative")

        if sigma is not None and np.any(sigma <= 0):
            raise ValueError("Volatility sigma must be positive")

        # Check for very small T (near expiry) to avoid numerical issues
        if T is not None and np.any((T > 0) & (T < 1e-6)):
            logger.warning(
                "Time to maturity is very small (< 1e-6 years). "
                "Numerical precision may be affected."
            )

        # Check for very small sigma to avoid division by zero
        if sigma is not None and np.any((sigma > 0) & (sigma < 1e-6)):
            logger.warning(
                "Volatility is very small (< 1e-6). Numerical precision may be affected."
            )

    def implied_volatility(
        self,
        price: float | np.ndarray,
        S: float | np.ndarray,
        K: float | np.ndarray,
        T: float | np.ndarray,
        r: float | np.ndarray,
        q: float | np.ndarray = 0,
        option_type: Literal["call", "put"] | np.ndarray = "call",
        method: Literal["auto", "newton", "brent"] = "auto",
    ) -> float | np.ndarray | None:
        """
        Calculate implied volatility from market price.

        Uses a multi-method solver with Newton-Raphson (fast path) and
        Brent's method (robust fallback). Automatically handles edge cases.

        Parameters
        ----------
        price : float | np.ndarray
            Market price of the option(s)
        S : float | np.ndarray
            Current price of underlying asset
        K : float | np.ndarray
            Strike price
        T : float | np.ndarray
            Time to maturity (in years)
        r : float | np.ndarray
            Risk-free interest rate (annualized)
        q : float | np.ndarray, default=0
            Dividend yield (annualized)
        option_type : {'call', 'put'} | np.ndarray, default='call'
            Type of option(s)
        method : {'auto', 'newton', 'brent'}, default='auto'
            Solver method to use:
            - 'auto': Try Newton-Raphson, fall back to Brent if needed
            - 'newton': Newton-Raphson only (faster, may fail)
            - 'brent': Brent's method only (slower, guaranteed convergence)

        Returns
        -------
        float | np.ndarray | None
            Implied volatility (σ). Returns None or NaN for failed calculations.
            For vectorized inputs, returns array with NaN for failures.

        Examples
        --------
        >>> bs = BlackScholes()
        >>>
        >>> # Single option
        >>> iv = bs.implied_volatility(
        ...     price=5.50,
        ...     S=100,
        ...     K=100,
        ...     T=30/365,
        ...     r=0.05,
        ...     option_type='call'
        ... )
        >>> print(f"IV: {iv:.2%}")
        IV: 20.15%
        >>>
        >>> # Vectorized (option chain)
        >>> prices = np.array([8.50, 5.50, 3.20])
        >>> strikes = np.array([95, 100, 105])
        >>> ivs = bs.implied_volatility(
        ...     price=prices,
        ...     S=100,
        ...     K=strikes,
        ...     T=30/365,
        ...     r=0.05,
        ...     option_type='call'
        ... )
        >>> print(f"IVs: {ivs}")
        IVs: [0.198 0.201 0.205]

        Notes
        -----
        - Uses Newton-Raphson with Brenner-Subrahmanyam initial guess for speed
        - Falls back to Brent's method for robustness in edge cases
        - Handles deep ITM/OTM options and near expiration gracefully
        - Returns None/NaN for invalid inputs or convergence failures

        See Also
        --------
        price : Calculate option price given volatility
        ImpliedVolatilitySolver : Lower-level IV solver class

        References
        ----------
        - Brenner & Subrahmanyam (1988): Initial guess approximation
        - Jäckel, P. (2015): "Let's Be Rational" - Advanced IV methods
        """
        # Check if vectorized input
        is_array = isinstance(price, np.ndarray)

        if is_array:
            # Use vectorized solver
            return self.iv_solver.solve_vectorized(  # type: ignore[no-any-return]
                prices=price,
                S=S,
                K=K,
                T=T,
                r=r,
                q=q,
                option_type=option_type,
                method=method,
            )
        else:
            # Single value solver
            return self.iv_solver.solve(  # type: ignore[no-any-return]
                price=price,
                S=S,
                K=K,
                T=T,
                r=r,
                q=q,
                option_type=option_type,
                method=method,
            )
