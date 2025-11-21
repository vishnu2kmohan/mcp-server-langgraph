"""
Retry utilities with exponential backoff and jitter.

Provides decorators and functions for retrying operations that may fail
transiently, particularly useful for database and network operations.
"""

import asyncio
import random
import time
from typing import Callable, TypeVar, Any
from functools import wraps

from mcp_server_langgraph.observability.telemetry import logger

T = TypeVar("T")


async def retry_with_backoff(
    func: Callable[..., Any],
    max_retries: int = 3,
    initial_delay: float = 1.0,
    max_delay: float = 32.0,
    exponential_base: float = 2.0,
    jitter: bool = True,
    max_timeout: float | None = 60.0,
    retryable_exceptions: tuple[type[Exception], ...] | None = None,
) -> Any:
    """
    Retry an async function with exponential backoff and jitter.

    Args:
        func: Async function to retry
        max_retries: Maximum number of retry attempts (default: 3)
        initial_delay: Initial delay in seconds (default: 1.0)
        max_delay: Maximum delay between retries (default: 32.0)
        exponential_base: Base for exponential backoff (default: 2.0)
        jitter: Add random jitter to avoid thundering herd (default: True)
        max_timeout: Maximum total time to spend retrying in seconds (default: 60.0)
        retryable_exceptions: Tuple of exception types to retry (default: all)

    Returns:
        Result of the function call

    Raises:
        Exception: Re-raises the last exception if all retries are exhausted

    Example:
        async def connect_db():
            return await asyncpg.connect("postgresql://...")

        result = await retry_with_backoff(
            connect_db,
            max_retries=3,
            initial_delay=1.0
        )
    """
    start_time = time.time()
    last_exception: Exception | None = None

    for attempt in range(max_retries + 1):  # +1 for initial attempt
        try:
            result = await func()
            if attempt > 0:
                logger.info(f"Success after {attempt} retry attempts")
            return result

        except Exception as e:
            last_exception = e

            # Check if this exception type should be retried
            if retryable_exceptions and not isinstance(e, retryable_exceptions):
                logger.debug(f"Non-retryable exception: {type(e).__name__}")
                raise

            # Check if we've exhausted retries
            if attempt >= max_retries:
                logger.error(f"Failed after {attempt + 1} attempts (including initial): {e}")
                raise Exception(f"Failed after {attempt + 1} attempts: {e}") from e

            # Check if we've exceeded max timeout
            if max_timeout:
                elapsed = time.time() - start_time
                if elapsed >= max_timeout:
                    logger.error(f"Retry timeout exceeded ({elapsed:.1f}s >= {max_timeout}s)")
                    raise Exception(f"Retry timeout exceeded after {elapsed:.1f}s (max: {max_timeout}s)") from e

            # Calculate delay with exponential backoff
            delay = min(initial_delay * (exponential_base**attempt), max_delay)

            # Add jitter (±20% randomness)
            if jitter:
                jitter_factor = random.uniform(0.8, 1.2)
                delay = delay * jitter_factor

            logger.warning(f"Attempt {attempt + 1}/{max_retries + 1} failed: {e}. " f"Retrying in {delay:.2f}s...")

            await asyncio.sleep(delay)

    # Should never reach here, but just in case
    if last_exception:
        raise last_exception
    raise RuntimeError("Retry logic error: no exception recorded")


def async_retry(
    max_retries: int = 3,
    initial_delay: float = 1.0,
    max_delay: float = 32.0,
    exponential_base: float = 2.0,
    jitter: bool = True,
    max_timeout: float | None = 60.0,
    retryable_exceptions: tuple[type[Exception], ...] | None = None,
) -> Callable[[Callable[..., Any]], Callable[..., Any]]:
    """
    Decorator for retrying async functions with exponential backoff.

    Args:
        Same as retry_with_backoff()

    Returns:
        Decorated function with retry logic

    Example:
        @async_retry(max_retries=3, initial_delay=1.0)
        async def connect_to_database():
            return await asyncpg.connect("postgresql://...")
    """

    def decorator(func: Callable[..., Any]) -> Callable[..., Any]:
        @wraps(func)
        async def wrapper(*args: Any, **kwargs: Any) -> Any:
            async def _call() -> Any:
                return await func(*args, **kwargs)

            return await retry_with_backoff(
                _call,
                max_retries=max_retries,
                initial_delay=initial_delay,
                max_delay=max_delay,
                exponential_base=exponential_base,
                jitter=jitter,
                max_timeout=max_timeout,
                retryable_exceptions=retryable_exceptions,
            )

        return wrapper

    return decorator
