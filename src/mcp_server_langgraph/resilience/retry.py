"""
Retry logic with exponential backoff and jitter.

Automatically retries transient failures with configurable policies.
Uses tenacity library for declarative retry specifications.

See ADR-0026 for design rationale.
"""

import functools
import logging
import random
from collections.abc import Callable
from datetime import datetime
from email.utils import parsedate_to_datetime
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
from mcp_server_langgraph.resilience.config import JitterStrategy, get_resilience_config

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


# =============================================================================
# Jitter and Retry-After Utilities
# =============================================================================


def calculate_jitter_delay(
    base_delay: float,
    prev_delay: float | None,
    max_delay: float,
    strategy: JitterStrategy,
) -> float:
    """Calculate delay with jitter based on strategy.

    Args:
        base_delay: Base delay without jitter
        prev_delay: Previous delay (for decorrelated jitter)
        max_delay: Maximum allowed delay
        strategy: Jitter strategy to use

    Returns:
        Delay with jitter applied

    See: https://aws.amazon.com/blogs/architecture/exponential-backoff-and-jitter/
    """
    if strategy == JitterStrategy.SIMPLE:
        # Simple jitter: +/- 20% of base delay
        jitter_factor = random.uniform(0.8, 1.2)
        return min(base_delay * jitter_factor, max_delay)

    elif strategy == JitterStrategy.FULL:
        # Full jitter: random(0, delay)
        return random.uniform(0, min(base_delay, max_delay))

    else:  # JitterStrategy.DECORRELATED
        # Decorrelated jitter: min(cap, random(base, prev * 3))
        # Reference: AWS Architecture Blog
        if prev_delay is None:
            prev_delay = base_delay
        return min(max_delay, random.uniform(base_delay, prev_delay * 3))


def parse_retry_after(value: str | int | float | None) -> float | None:
    """Parse Retry-After header value (RFC 7231).

    Args:
        value: Either seconds (int/float) or HTTP-date string

    Returns:
        Seconds to wait, or None if unparseable
    """
    if value is None:
        return None

    # Integer or float seconds
    if isinstance(value, (int, float)):
        return float(value)

    # String: try as number first
    try:
        return float(value)
    except ValueError:
        pass

    # String: try as HTTP-date
    try:
        retry_date = parsedate_to_datetime(value)
        delta = retry_date - datetime.now(retry_date.tzinfo)
        return max(0.0, delta.total_seconds())
    except Exception:
        return None


def extract_retry_after_from_exception(exception: Exception) -> float | None:
    """Extract Retry-After value from LiteLLM/httpx exception.

    Args:
        exception: The caught exception

    Returns:
        Seconds to wait, or None if not available
    """
    # Check for retry_after attribute (LiteLLM may add this)
    if hasattr(exception, "retry_after"):
        return parse_retry_after(exception.retry_after)

    # Check for response headers (httpx exceptions)
    if hasattr(exception, "response") and exception.response is not None:
        headers = getattr(exception.response, "headers", {})
        if headers:
            retry_after = headers.get("Retry-After") or headers.get("retry-after")
            if retry_after:
                return parse_retry_after(retry_after)

    # Check LiteLLM's llm_provider_response_headers
    if hasattr(exception, "llm_provider_response_headers"):
        headers = exception.llm_provider_response_headers or {}
        retry_after = headers.get("Retry-After") or headers.get("retry-after")
        if retry_after:
            return parse_retry_after(retry_after)

    return None


def is_overload_error(exception: Exception) -> bool:
    """Determine if exception indicates service overload.

    Checks for:
    - HTTP 529 status code
    - "overloaded" in error message
    - LLMOverloadError type

    Args:
        exception: The exception to check

    Returns:
        True if this is an overload error, False otherwise
    """
    # Check our custom exception type
    try:
        from mcp_server_langgraph.core.exceptions import LLMOverloadError

        if isinstance(exception, LLMOverloadError):
            return True
    except ImportError:
        pass

    # Check status code (LiteLLM exceptions have status_code attribute)
    status_code = getattr(exception, "status_code", None)
    if status_code == 529:
        return True

    # Check error message patterns
    error_msg = str(exception).lower()
    overload_patterns = [
        "overload",
        "service is overloaded",
        "capacity",
    ]

    # 503 + overload message = treat as overload
    if status_code == 503 and any(p in error_msg for p in overload_patterns):
        return True

    # Pure message-based detection (including "529" in message)
    return "overload" in error_msg or "529" in error_msg


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
    jitter_strategy: JitterStrategy | None = None,
    overload_aware: bool = False,
) -> Callable[[Callable[P, T]], Callable[P, T]]:
    """
    Decorator to retry a function with exponential backoff.

    Args:
        max_attempts: Maximum number of retry attempts (default: from config)
        exponential_base: Base for exponential backoff (default: from config)
        exponential_max: Maximum backoff time in seconds (default: from config)
        retry_on: Exception type(s) to retry on (default: auto-detect)
        strategy: Retry strategy (exponential, linear, fixed, random)
        jitter_strategy: Jitter strategy for randomizing delays (default: from config)
        overload_aware: Enable extended retry behavior for 529/overload errors

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

        # With overload awareness for 529 errors
        @retry_with_backoff(max_attempts=3, overload_aware=True)
        async def call_llm() -> str:
            # Will use extended retry config for 529 overload errors
            return await llm_client.generate(prompt)
    """
    # Load configuration
    config = get_resilience_config()
    retry_config = config.retry

    # Use config defaults if not specified
    max_attempts = max_attempts or retry_config.max_attempts
    exponential_base = exponential_base or retry_config.exponential_base
    exponential_max = exponential_max or retry_config.exponential_max
    jitter_strategy = jitter_strategy or retry_config.jitter_strategy

    # Note: overload_aware enables extended retry behavior for 529/overload errors
    # Future enhancement: dynamically adjust max_attempts and backoff for overload
    _ = overload_aware  # Mark as used for now

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
                msg = "Unreachable code"
                raise RuntimeError(msg)  # pragma: no cover

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
            msg = "Unreachable code"
            raise RuntimeError(msg)  # pragma: no cover

        # Return appropriate wrapper
        import asyncio

        if asyncio.iscoroutinefunction(func):
            return async_wrapper  # type: ignore[return-value]
        else:
            return sync_wrapper

    return decorator
