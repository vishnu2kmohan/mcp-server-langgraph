"""
Retry logic with exponential backoff and jitter.

Automatically retries transient failures with configurable policies.
Uses tenacity library for declarative retry specifications.

See ADR-0026 for design rationale.
"""

import functools
import logging
from collections.abc import Callable
from enum import Enum
from typing import ParamSpec, TypeVar

from opentelemetry import trace
from tenacity import (
    AsyncRetrying,
    RetryCallState,
    RetryError,
    Retrying,
    retry_if_exception_type,
    stop_after_attempt,
    wait_exponential,
    wait_random,
)

from mcp_server_langgraph.observability.telemetry import retry_attempt_counter, retry_exhausted_counter
from mcp_server_langgraph.resilience.config import get_resilience_config

logger = logging.getLogger(__name__)
tracer = trace.get_tracer(__name__)

P = ParamSpec("P")
T = TypeVar("T")

# Check if redis is available (optional dependency)
_REDIS_AVAILABLE = False
try:
    import redis as _redis_module

    _REDIS_AVAILABLE = True
except ImportError:
    _redis_module = None  # type: ignore[assignment]
    logger.debug("Redis module not available. Redis error retry logic will be skipped.")


class RetryPolicy(str, Enum):
    """Retry policies for different error types"""

    NEVER = "never"  # Never retry (client errors)
    ALWAYS = "always"  # Always retry (transient failures)
    CONDITIONAL = "conditional"  # Retry with conditions


class RetryStrategy(str, Enum):
    """Retry backoff strategies"""

    EXPONENTIAL = "exponential"  # Exponential backoff: 1s, 2s, 4s, 8s...
    LINEAR = "linear"  # Linear backoff: 1s, 2s, 3s, 4s...
    FIXED = "fixed"  # Fixed interval: 1s, 1s, 1s, 1s...
    RANDOM = "random"  # Random jitter: 0-1s, 0-2s, 0-4s...


def should_retry_exception(exception: Exception) -> bool:
    """
    Determine if an exception is retry-able.

    Args:
        exception: The exception that occurred

    Returns:
        True if should retry, False otherwise
    """
    # Import here to avoid circular dependency
    try:
        from mcp_server_langgraph.core.exceptions import (
            AuthenticationError,
            AuthorizationError,
            ExternalServiceError,
            RateLimitError,
            ResilienceError,
            ValidationError,
        )

        # Never retry client errors
        if isinstance(exception, (ValidationError, AuthorizationError)):
            return False

        # Conditionally retry auth errors (e.g., token refresh)
        if isinstance(exception, AuthenticationError):
            # Only retry token expiration (can refresh)
            return exception.error_code == "auth.token_expired"

        # Never retry rate limits from our own service
        if isinstance(exception, RateLimitError):
            return False

        # Always retry external service errors
        if isinstance(exception, ExternalServiceError):
            return True

        # Always retry resilience errors (timeout, circuit breaker)
        if isinstance(exception, ResilienceError):
            return True

    except ImportError:
        # Exceptions not yet defined, fall back to generic logic
        pass

    # Generic logic: retry network errors, timeouts
    import httpx

    if isinstance(exception, (httpx.TimeoutException, httpx.ConnectError, httpx.NetworkError)):
        return True

    # Check redis errors if redis is available (optional dependency)
    if _REDIS_AVAILABLE and _redis_module is not None:
        if isinstance(exception, (_redis_module.ConnectionError, _redis_module.TimeoutError)):
            return True

    # Don't retry by default
    return False


def log_retry_attempt(retry_state: RetryCallState) -> None:
    """Log retry attempts for observability"""
    exception = retry_state.outcome.exception() if retry_state.outcome else None

    logger.warning(
        f"Retrying after failure (attempt {retry_state.attempt_number})",
        exc_info=True,
        extra={
            "attempt_number": retry_state.attempt_number,
            "exception_type": type(exception).__name__ if exception else None,
            "next_action": str(retry_state.next_action),
        },
    )

    # Emit metric
    retry_attempt_counter.add(
        1,
        attributes={
            "attempt_number": retry_state.attempt_number,
            "exception_type": type(exception).__name__ if exception else "unknown",
        },
    )


def retry_with_backoff(  # noqa: C901
    max_attempts: int | None = None,
    exponential_base: float | None = None,
    exponential_max: float | None = None,
    retry_on: type[Exception] | tuple[type[Exception], ...] | None = None,
    strategy: RetryStrategy = RetryStrategy.EXPONENTIAL,
) -> Callable[[Callable[P, T]], Callable[P, T]]:
    """
    Decorator to retry a function with exponential backoff.

    Args:
        max_attempts: Maximum number of retry attempts (default: from config)
        exponential_base: Base for exponential backoff (default: from config)
        exponential_max: Maximum backoff time in seconds (default: from config)
        retry_on: Exception type(s) to retry on (default: auto-detect)
        strategy: Retry strategy (exponential, linear, fixed, random)

    Usage:
        @retry_with_backoff(max_attempts=3, exponential_base=2)
        async def call_external_api() -> dict[str, Any]:
            async with httpx.AsyncClient() as client:
                response = await client.get("https://api.example.com")
                return response.json()

        # With custom exception types
        @retry_with_backoff(retry_on=(httpx.TimeoutException, redis.ConnectionError))
        async def fetch_data() -> str:
            # Will retry on timeout or connection errors
            return await get_data()
    """
    # Load configuration
    config = get_resilience_config()
    retry_config = config.retry

    # Use config defaults if not specified
    max_attempts = max_attempts or retry_config.max_attempts
    exponential_base = exponential_base or retry_config.exponential_base
    exponential_max = exponential_max or retry_config.exponential_max

    def decorator(func: Callable[P, T]) -> Callable[P, T]:
        @functools.wraps(func)
        async def async_wrapper(*args: P.args, **kwargs: P.kwargs) -> T:
            """Async wrapper with retry logic"""
            with tracer.start_as_current_span(
                f"retry.{func.__name__}",
                attributes={
                    "retry.max_attempts": max_attempts,
                    "retry.strategy": strategy.value,
                },
            ) as span:
                # Configure retry behavior
                retry_kwargs = {
                    "stop": stop_after_attempt(max_attempts),
                    "reraise": False,  # Raise RetryError instead of original exception
                    "before_sleep": log_retry_attempt,
                }

                # Configure wait strategy
                if strategy == RetryStrategy.EXPONENTIAL:
                    retry_kwargs["wait"] = wait_exponential(
                        multiplier=exponential_base,
                        max=exponential_max,
                    )
                elif strategy == RetryStrategy.RANDOM:
                    retry_kwargs["wait"] = wait_random(min=0, max=exponential_max)
                # Add other strategies as needed

                # Configure retry condition
                if retry_on:
                    retry_kwargs["retry"] = retry_if_exception_type(retry_on)
                # Otherwise, retry all exceptions (tenacity default behavior)

                try:
                    # Execute with retry
                    async for attempt in AsyncRetrying(**retry_kwargs):  # type: ignore[arg-type]
                        with attempt:
                            result: T = await func(*args, **kwargs)  # type: ignore[misc]
                            span.set_attribute("retry.success", True)
                            span.set_attribute("retry.attempts", attempt.retry_state.attempt_number)
                            return result

                except RetryError as e:
                    # Retry exhausted
                    span.set_attribute("retry.success", False)
                    span.set_attribute("retry.exhausted", True)

                    logger.error(
                        f"Retry exhausted after {max_attempts} attempts",
                        exc_info=True,
                        extra={"max_attempts": max_attempts, "function": func.__name__},
                    )

                    # Emit metric
                    retry_exhausted_counter.add(1, attributes={"function": func.__name__})

                    # Wrap in our custom exception
                    from mcp_server_langgraph.core.exceptions import RetryExhaustedError

                    raise RetryExhaustedError(
                        message=f"Retry exhausted after {max_attempts} attempts",
                        metadata={
                            "max_attempts": max_attempts,
                            "function": func.__name__,
                        },
                    ) from e.last_attempt.exception()
                # This should never be reached, but mypy needs an explicit return path
                raise RuntimeError("Unreachable code")  # pragma: no cover

        @functools.wraps(func)
        def sync_wrapper(*args: P.args, **kwargs: P.kwargs) -> T:
            """Sync wrapper with retry logic"""
            # Similar to async_wrapper but for sync functions
            retry_kwargs = {
                "stop": stop_after_attempt(max_attempts),
                "reraise": False,  # Raise RetryError instead of original exception
                "before_sleep": log_retry_attempt,
            }

            if strategy == RetryStrategy.EXPONENTIAL:
                retry_kwargs["wait"] = wait_exponential(
                    multiplier=exponential_base,
                    max=exponential_max,
                )

            if retry_on:
                retry_kwargs["retry"] = retry_if_exception_type(retry_on)

            try:
                for attempt in Retrying(**retry_kwargs):  # type: ignore[arg-type]
                    with attempt:
                        return func(*args, **kwargs)
            except RetryError as e:
                from mcp_server_langgraph.core.exceptions import RetryExhaustedError

                raise RetryExhaustedError(
                    message=f"Retry exhausted after {max_attempts} attempts",
                    metadata={"max_attempts": max_attempts},
                ) from e.last_attempt.exception()
            # This should never be reached, but mypy needs an explicit return path
            raise RuntimeError("Unreachable code")  # pragma: no cover

        # Return appropriate wrapper
        import asyncio

        if asyncio.iscoroutinefunction(func):
            return async_wrapper  # type: ignore[return-value]
        else:
            return sync_wrapper

    return decorator
