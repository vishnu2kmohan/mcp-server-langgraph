"""
Fallback strategies for graceful degradation.

Provides fallback responses when primary services are unavailable.
Enables fail-open vs fail-closed behavior per service.

See ADR-0026 for design rationale.
"""

import functools
import logging
from typing import Any, Callable, Dict, Optional, ParamSpec, TypeVar

from opentelemetry import trace

from mcp_server_langgraph.observability.telemetry import fallback_used_counter

logger = logging.getLogger(__name__)
tracer = trace.get_tracer(__name__)

P = ParamSpec("P")
T = TypeVar("T")


class FallbackStrategy:
    """
    Base class for fallback strategies.

    Subclass this to create custom fallback behaviors.
    """

    def get_fallback_value(self, *args: Any, **kwargs: Any) -> Any:
        """
        Get fallback value when primary operation fails.

        Args:
            *args: Original function arguments
            **kwargs: Original function keyword arguments

        Returns:
            Fallback value
        """
        raise NotImplementedError("Subclasses must implement get_fallback_value()")


class DefaultValueFallback(FallbackStrategy):
    """Return a default value on failure"""

    def __init__(self, default_value: Any) -> None:
        self.default_value = default_value

    def get_fallback_value(self, *args: Any, **kwargs: Any) -> Any:
        return self.default_value


class CachedValueFallback(FallbackStrategy):
    """Return cached value on failure"""

    def __init__(self, cache_key_fn: Optional[Callable[..., str]] = None) -> None:
        self.cache_key_fn = cache_key_fn or self._default_cache_key
        self._cache: Dict[str, Any] = {}

    def _default_cache_key(self, *args: Any, **kwargs: Any) -> str:
        """Generate cache key from arguments"""
        return f"{args}:{kwargs}"

    def cache_value(self, value: Any, *args: Any, **kwargs: Any) -> None:
        """Cache a value for future fallback"""
        key = self.cache_key_fn(*args, **kwargs)
        self._cache[key] = value

    def get_fallback_value(self, *args: Any, **kwargs: Any) -> Any:
        """Get cached value or None"""
        key = self.cache_key_fn(*args, **kwargs)
        return self._cache.get(key)


class FunctionFallback(FallbackStrategy):
    """Call a fallback function on failure"""

    def __init__(self, fallback_fn: Callable[..., Any]) -> None:
        self.fallback_fn = fallback_fn

    def get_fallback_value(self, *args: Any, **kwargs: Any) -> Any:
        return self.fallback_fn(*args, **kwargs)


class StaleDataFallback(FallbackStrategy):
    """Return stale data with warning on failure"""

    def __init__(self, max_staleness_seconds: int = 3600) -> None:
        self.max_staleness_seconds = max_staleness_seconds
        self._cache: Dict[str, tuple[Any, float]] = {}  # value, timestamp

    def cache_value(self, value: Any, key: str) -> None:
        """Cache value with timestamp"""
        import time

        self._cache[key] = (value, time.time())

    def get_fallback_value(self, *args: Any, **kwargs: Any) -> Optional[Any]:
        """Get stale data if within staleness limit"""
        import time

        # Support both direct key (single arg) and generated key (multiple args/kwargs)
        if len(args) == 1 and not kwargs and isinstance(args[0], str):
            key = args[0]
        else:
            key = str(args) + str(kwargs)

        if key in self._cache:
            value, timestamp = self._cache[key]
            age = time.time() - timestamp
            if age < self.max_staleness_seconds:
                logger.warning(
                    f"Using stale data (age: {age:.1f}s)",
                    extra={"staleness_seconds": age, "max_staleness": self.max_staleness_seconds},
                )
                return value

        return None


# Predefined fallback strategies for common scenarios
FALLBACK_STRATEGIES = {
    # Authorization: Fail-open (allow by default)
    "openfga_allow": DefaultValueFallback(default_value=True),
    # Authorization: Fail-closed (deny by default)
    "openfga_deny": DefaultValueFallback(default_value=False),
    # Cache: Return None on cache miss
    "cache_miss": DefaultValueFallback(default_value=None),
    # Empty list fallback
    "empty_list": DefaultValueFallback(default_value=[]),
    # Empty dict fallback
    "empty_dict": DefaultValueFallback(default_value={}),
}


def with_fallback(  # noqa: C901
    fallback: Optional[Any] = None,
    fallback_fn: Optional[Callable[..., Any]] = None,
    fallback_strategy: Optional[FallbackStrategy] = None,
    fallback_on: Optional[tuple[type, ...]] = None,
) -> Callable[[Callable[P, T]], Callable[P, T]]:
    """
    Decorator to provide fallback value when function raises exception.

    Args:
        fallback: Static fallback value
        fallback_fn: Function to call for fallback value
        fallback_strategy: FallbackStrategy instance for advanced fallback
        fallback_on: Exception types to catch (default: all exceptions)

    Usage:
        # Static fallback
        @with_fallback(fallback=True)
        async def check_permission(user: str, resource: str) -> bool:
            # Returns True if OpenFGA is down (fail-open)
            return await openfga_client.check(user, resource)

        # Function fallback
        @with_fallback(fallback_fn=lambda user, res: user == "admin")
        async def check_permission(user: str, resource: str) -> bool:
            # Admins always allowed if OpenFGA is down
            return await openfga_client.check(user, resource)

        # Cached value fallback
        cache_strategy = CachedValueFallback()
        @with_fallback(fallback_strategy=cache_strategy)
        async def get_user_profile(user_id: str) -> dict[str, Any]:
            profile = await db.get_user(user_id)
            cache_strategy.cache_value(profile, user_id)
            return profile

        # Specific exception types
        @with_fallback(fallback=[], fallback_on=(httpx.TimeoutError, redis.ConnectionError))
        async def fetch_items() -> list:
            # Returns [] only on timeout/connection errors
            return await get_items()
    """
    # Validate arguments
    if sum([fallback is not None, fallback_fn is not None, fallback_strategy is not None]) != 1:
        raise ValueError("Exactly one of fallback, fallback_fn, or fallback_strategy must be provided")

    # Determine exception types to catch
    exception_types = fallback_on or (Exception,)

    def decorator(func: Callable[P, T]) -> Callable[P, T]:
        @functools.wraps(func)
        async def async_wrapper(*args: P.args, **kwargs: P.kwargs) -> T:
            """Async wrapper with fallback"""
            with tracer.start_as_current_span(
                f"fallback.{func.__name__}",
                attributes={"fallback.enabled": True},
            ) as span:
                try:
                    # Try primary operation
                    result: T = await func(*args, **kwargs)  # type: ignore[misc]
                    span.set_attribute("fallback.used", False)
                    return result

                except BaseException as e:
                    # Check if this is an exception type we should handle
                    if not isinstance(e, exception_types):
                        raise

                    # Primary operation failed, use fallback
                    span.set_attribute("fallback.used", True)
                    span.set_attribute("fallback.exception_type", type(e).__name__)

                    logger.warning(
                        f"Using fallback for {func.__name__}",
                        exc_info=True,
                        extra={
                            "function": func.__name__,
                            "exception_type": type(e).__name__,
                            "fallback_type": "static" if fallback is not None else "function" if fallback_fn else "strategy",
                        },
                    )

                    # Emit metric
                    fallback_used_counter.add(
                        1,
                        attributes={
                            "function": func.__name__,
                            "exception_type": type(e).__name__,
                        },
                    )

                    # Determine fallback value
                    if fallback is not None:
                        return fallback  # type: ignore[no-any-return]
                    elif fallback_fn is not None:
                        if asyncio.iscoroutinefunction(fallback_fn):
                            return await fallback_fn(*args, **kwargs)  # type: ignore[no-any-return]
                        else:
                            return fallback_fn(*args, **kwargs)  # type: ignore[no-any-return]
                    else:  # fallback_strategy is not None
                        return fallback_strategy.get_fallback_value(*args, **kwargs)  # type: ignore[no-any-return,union-attr]

        @functools.wraps(func)
        def sync_wrapper(*args: P.args, **kwargs: P.kwargs) -> T:
            """Sync wrapper with fallback"""
            try:
                return func(*args, **kwargs)
            except BaseException as e:
                # Check if this is an exception type we should handle
                if not isinstance(e, exception_types):
                    raise

                logger.warning(f"Using fallback for {func.__name__}", exc_info=True)

                if fallback is not None:
                    return fallback  # type: ignore[no-any-return]
                elif fallback_fn is not None:
                    return fallback_fn(*args, **kwargs)  # type: ignore[no-any-return]
                else:  # fallback_strategy is not None
                    return fallback_strategy.get_fallback_value(*args, **kwargs)  # type: ignore[no-any-return,union-attr]

        # Return appropriate wrapper
        import asyncio

        if asyncio.iscoroutinefunction(func):
            return async_wrapper  # type: ignore[return-value]
        else:
            return sync_wrapper

    return decorator


# Convenience decorators for common fallback scenarios
def fail_open(func: Callable[P, bool]) -> Callable[P, bool]:
    """
    Decorator for fail-open authorization (allow on error).

    Usage:
        @fail_open
        async def check_permission(user: str, resource: str) -> bool:
            return await openfga_client.check(user, resource)
    """
    return with_fallback(fallback=True)(func)


def fail_closed(func: Callable[P, bool]) -> Callable[P, bool]:
    """
    Decorator for fail-closed authorization (deny on error).

    Usage:
        @fail_closed
        async def check_admin_permission(user: str) -> bool:
            return await openfga_client.check(user, "admin")
    """
    return with_fallback(fallback=False)(func)


def return_empty_on_error(func: Callable[P, T]) -> Callable[P, T]:
    """
    Decorator to return empty value on error (list/dict/None).

    Usage:
        @return_empty_on_error
        async def get_user_list() -> list:
            return await db.query_users()  # Returns [] on error
    """

    def determine_empty_value() -> Any:
        """Determine empty value based on return type hint"""
        import inspect

        sig = inspect.signature(func)
        return_type = sig.return_annotation

        if return_type == list or "List" in str(return_type):
            return []
        elif return_type == dict or "Dict" in str(return_type):
            return {}
        else:
            return None

    return with_fallback(fallback=determine_empty_value())(func)
