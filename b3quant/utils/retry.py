"""Retry utilities with exponential backoff and jitter"""

import logging
import random
import time
from collections.abc import Callable
from functools import wraps
from typing import Any

logger = logging.getLogger(__name__)


def exponential_backoff_with_jitter(
    attempt: int,
    base_delay: float = 1.0,
    max_delay: float = 60.0,
    jitter: bool = True,
) -> float:
    """
    Calculate delay for exponential backoff with optional jitter.

    This implements a jitter-based exponential backoff to prevent
    the "thundering herd" problem where multiple clients retry
    simultaneously after a failure.

    Args:
        attempt: Retry attempt number (0-indexed)
        base_delay: Base delay in seconds (default: 1.0)
        max_delay: Maximum delay cap in seconds (default: 60.0)
        jitter: Whether to add random jitter (default: True)

    Returns:
        Delay in seconds to wait before next attempt

    Examples:
        >>> # First retry: ~1-2 seconds
        >>> delay = exponential_backoff_with_jitter(0)
        >>> print(f"{delay:.2f}s")

        >>> # Third retry: ~4-8 seconds
        >>> delay = exponential_backoff_with_jitter(2)
        >>> print(f"{delay:.2f}s")

    References:
        AWS Architecture Blog - Exponential Backoff And Jitter
        https://aws.amazon.com/blogs/architecture/exponential-backoff-and-jitter/
    """
    # Calculate exponential delay: base * 2^attempt
    delay = base_delay * (2**attempt)

    # Cap at maximum delay
    delay = min(delay, max_delay)

    # Add jitter: random value between 0 and calculated delay
    if jitter:
        delay = random.uniform(0, delay)

    return delay  # type: ignore[no-any-return]


def retry_with_backoff(
    max_retries: int = 3,
    base_delay: float = 1.0,
    max_delay: float = 60.0,
    jitter: bool = True,
    exceptions: tuple[type[Exception], ...] = (Exception,),
    on_retry: Callable[[int, Exception], None] | None = None,
):
    """
    Decorator for retrying functions with exponential backoff and jitter.

    Args:
        max_retries: Maximum number of retry attempts (default: 3)
        base_delay: Base delay in seconds (default: 1.0)
        max_delay: Maximum delay cap in seconds (default: 60.0)
        jitter: Whether to add random jitter (default: True)
        exceptions: Tuple of exception types to catch and retry (default: all)
        on_retry: Optional callback called on each retry with (attempt, exception)

    Returns:
        Decorated function with retry logic

    Examples:
        >>> @retry_with_backoff(max_retries=3, base_delay=1.0)
        ... def download_file(url):
        ...     response = requests.get(url)
        ...     response.raise_for_status()
        ...     return response.content

        >>> # With custom exception handling
        >>> @retry_with_backoff(
        ...     max_retries=5,
        ...     exceptions=(requests.exceptions.RequestException,)
        ... )
        ... def fetch_data(url):
        ...     return requests.get(url).json()
    """

    def decorator(func: Callable) -> Callable:
        @wraps(func)
        def wrapper(*args, **kwargs) -> Any:
            for attempt in range(max_retries):
                try:
                    return func(*args, **kwargs)

                except exceptions as e:
                    # Last attempt - re-raise the exception
                    if attempt == max_retries - 1:
                        logger.error(
                            f"{func.__name__} failed after {max_retries} attempts: {e}"
                        )
                        raise

                    # Calculate delay with jitter
                    delay = exponential_backoff_with_jitter(
                        attempt=attempt,
                        base_delay=base_delay,
                        max_delay=max_delay,
                        jitter=jitter,
                    )

                    logger.warning(
                        f"{func.__name__} attempt {attempt + 1}/{max_retries} failed: {e}. "
                        f"Retrying in {delay:.2f}s..."
                    )

                    # Call optional retry callback
                    if on_retry:
                        on_retry(attempt, e)

                    # Wait before retry
                    time.sleep(delay)

            # Should never reach here, but safety fallback
            raise RuntimeError(f"{func.__name__} retry loop completed unexpectedly")

        return wrapper

    return decorator
