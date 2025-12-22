"""Black-Scholes option pricing model with Greeks"""

import logging
import numpy as np
from scipy import stats
from typing import Literal

from .base import PricingModel, GreeksCalculator

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
        pass

    def price(
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
            return S * np.exp(-q * T) * stats.norm.cdf(d1) - K * np.exp(
                -r * T
            ) * stats.norm.cdf(d2)
        elif option_type.lower() == "put":
            return K * np.exp(-r * T) * stats.norm.cdf(-d2) - S * np.exp(
                -q * T
            ) * stats.norm.cdf(-d1)
        else:
            raise ValueError(f"Invalid option_type: {option_type}. Must be 'call' or 'put'")

    def delta(
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
            return np.exp(-q * T) * stats.norm.cdf(d1)
        elif option_type.lower() == "put":
            return -np.exp(-q * T) * stats.norm.cdf(-d1)
        else:
            raise ValueError(f"Invalid option_type: {option_type}")

    def gamma(
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
        return np.exp(-q * T) * stats.norm.pdf(d1) / (S * sigma * np.sqrt(T))

    def vega(
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
        return S * np.exp(-q * T) * stats.norm.pdf(d1) * np.sqrt(T)

    def theta(
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
            return term1 + term2 + term3
        elif option_type.lower() == "put":
            term2 = r * K * np.exp(-r * T) * stats.norm.cdf(-d2)
            term3 = -q * S * np.exp(-q * T) * stats.norm.cdf(-d1)
            return term1 + term2 + term3
        else:
            raise ValueError(f"Invalid option_type: {option_type}")

    def rho(
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
            return K * T * np.exp(-r * T) * stats.norm.cdf(d2)
        elif option_type.lower() == "put":
            return -K * T * np.exp(-r * T) * stats.norm.cdf(-d2)
        else:
            raise ValueError(f"Invalid option_type: {option_type}")

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
