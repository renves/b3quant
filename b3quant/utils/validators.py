"""Input validation utilities for option pricing models"""

from typing import Any

import numpy as np


def validate_positive(value: Any, name: str) -> None:
    """
    Validate that a value is positive.

    Parameters
    ----------
    value : Any
        Value to validate (scalar or array)
    name : str
        Name of the parameter for error messages

    Raises
    ------
    ValueError
        If value is not positive
    """
    if np.any(value <= 0):
        raise ValueError(f"{name} must be positive")


def validate_non_negative(value: Any, name: str) -> None:
    """
    Validate that a value is non-negative.

    Parameters
    ----------
    value : Any
        Value to validate (scalar or array)
    name : str
        Name of the parameter for error messages

    Raises
    ------
    ValueError
        If value is negative
    """
    if np.any(value < 0):
        raise ValueError(f"{name} cannot be negative")


def validate_bounded(value: Any, name: str, lower: float, upper: float) -> None:
    """
    Validate that a value is within bounds.

    Parameters
    ----------
    value : Any
        Value to validate (scalar or array)
    name : str
        Name of the parameter for error messages
    lower : float
        Lower bound (exclusive)
    upper : float
        Upper bound (exclusive)

    Raises
    ------
    ValueError
        If value is outside bounds
    """
    if np.any(value <= lower) or np.any(value >= upper):
        raise ValueError(f"{name} must be in range ({lower}, {upper})")


def validate_option_type(option_type: str) -> None:
    """
    Validate option type string.

    Parameters
    ----------
    option_type : str
        Option type to validate

    Raises
    ------
    ValueError
        If option type is not 'call' or 'put' (case insensitive)
    """
    if option_type.lower() not in ["call", "put"]:
        raise ValueError(f"Invalid option_type: {option_type}. Must be 'call' or 'put'")


def validate_price_strike_relation(
    price: float | np.ndarray,
    S: float | np.ndarray,
    K: float | np.ndarray,
    option_type: str,
) -> None:
    """
    Validate that option price satisfies basic arbitrage bounds.

    Parameters
    ----------
    price : float | np.ndarray
        Option price
    S : float | np.ndarray
        Underlying price
    K : float | np.ndarray
        Strike price
    option_type : str
        Option type ('call' or 'put')

    Raises
    ------
    ValueError
        If price violates arbitrage bounds
    """
    if option_type.lower() == "call":
        # Call price cannot exceed underlying price
        if np.any(price > S):
            raise ValueError("Call option price cannot exceed underlying price")
        # Call price cannot be less than intrinsic value (ignoring time value of money)
        intrinsic = np.maximum(S - K, 0)
        if np.any(price < intrinsic - 1e-6):  # Small tolerance for numerical errors
            raise ValueError("Call option price below intrinsic value")
    else:  # put
        # Put price cannot exceed strike price
        if np.any(price > K):
            raise ValueError("Put option price cannot exceed strike price")
        # Put price cannot be less than intrinsic value
        intrinsic = np.maximum(K - S, 0)
        if np.any(price < intrinsic - 1e-6):
            raise ValueError("Put option price below intrinsic value")
