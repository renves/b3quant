"""Base classes for option pricing models"""

from abc import ABC, abstractmethod
from typing import Literal, Protocol

import numpy as np


class PricingModel(ABC):
    """Abstract base class for all option pricing models"""

    @abstractmethod
    def price(
        self,
        S: float | np.ndarray,
        K: float | np.ndarray,
        T: float | np.ndarray,
        r: float | np.ndarray,
        option_type: Literal["call", "put"],
        **kwargs,
    ) -> float | np.ndarray:
        """
        Calculate option price.

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
        option_type : {'call', 'put'}
            Type of option
        **kwargs
            Additional model-specific parameters

        Returns
        -------
        float | np.ndarray
            Option price
        """
        pass

    @abstractmethod
    def validate_inputs(self, **kwargs) -> None:
        """
        Validate model inputs.

        Parameters
        ----------
        **kwargs
            Model parameters to validate

        Raises
        ------
        ValueError
            If any input is invalid
        """
        pass


class GreeksCalculator(Protocol):
    """Protocol for models that compute Greeks (sensitivity measures)"""

    def delta(
        self,
        S: float | np.ndarray,
        K: float | np.ndarray,
        T: float | np.ndarray,
        r: float | np.ndarray,
        option_type: Literal["call", "put"],
        **kwargs,
    ) -> float | np.ndarray:
        """
        Calculate Delta (first derivative w.r.t. underlying price).

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
        option_type : {'call', 'put'}
            Type of option
        **kwargs
            Additional parameters

        Returns
        -------
        float | np.ndarray
            Delta value (range: 0 to 1 for calls, -1 to 0 for puts)
        """
        ...

    def gamma(
        self,
        S: float | np.ndarray,
        K: float | np.ndarray,
        T: float | np.ndarray,
        r: float | np.ndarray,
        **kwargs,
    ) -> float | np.ndarray:
        """
        Calculate Gamma (second derivative w.r.t. underlying price).

        Gamma measures the rate of change of delta with respect to
        changes in the underlying asset price.

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
        **kwargs
            Additional parameters

        Returns
        -------
        float | np.ndarray
            Gamma value (always positive)
        """
        ...

    def vega(
        self,
        S: float | np.ndarray,
        K: float | np.ndarray,
        T: float | np.ndarray,
        r: float | np.ndarray,
        **kwargs,
    ) -> float | np.ndarray:
        """
        Calculate Vega (derivative w.r.t. volatility).

        Vega measures the sensitivity of option price to changes
        in the volatility of the underlying asset.

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
        **kwargs
            Additional parameters

        Returns
        -------
        float | np.ndarray
            Vega value (always positive)
        """
        ...

    def theta(
        self,
        S: float | np.ndarray,
        K: float | np.ndarray,
        T: float | np.ndarray,
        r: float | np.ndarray,
        option_type: Literal["call", "put"],
        **kwargs,
    ) -> float | np.ndarray:
        """
        Calculate Theta (derivative w.r.t. time).

        Theta measures the rate of decay of option value as time
        passes (time decay). Typically negative for long positions.

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
        option_type : {'call', 'put'}
            Type of option
        **kwargs
            Additional parameters

        Returns
        -------
        float | np.ndarray
            Theta value (typically negative)
        """
        ...

    def rho(
        self,
        S: float | np.ndarray,
        K: float | np.ndarray,
        T: float | np.ndarray,
        r: float | np.ndarray,
        option_type: Literal["call", "put"],
        **kwargs,
    ) -> float | np.ndarray:
        """
        Calculate Rho (derivative w.r.t. risk-free rate).

        Rho measures the sensitivity of option price to changes
        in the risk-free interest rate.

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
        option_type : {'call', 'put'}
            Type of option
        **kwargs
            Additional parameters

        Returns
        -------
        float | np.ndarray
            Rho value (positive for calls, negative for puts)
        """
        ...
