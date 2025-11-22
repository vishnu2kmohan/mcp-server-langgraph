"""
Timeout enforcement for async operations.

Prevents hanging requests by enforcing time limits on all async operations.
Uses asyncio.timeout() (Python 3.11+) or asyncio.wait_for() (Python 3.10).

See ADR-0026 for design rationale.
"""

import asyncio
import functools
import logging
import sys
from collections.abc import Callable
from typing import Any, ParamSpec, TypeVar

from opentelemetry import trace

from mcp_server_langgraph.observability.telemetry import timeout_exceeded_counter
from mcp_server_langgraph.resilience.config import get_resilience_config

logger = logging.getLogger(__name__)
tracer = trace.get_tracer(__name__)

P = ParamSpec("P")
T = TypeVar("T")


class TimeoutConfig:
    """Timeout configuration for different operation types"""

    def __init__(
        self,
        default: int = 30,
        llm: int = 60,
        auth: int = 5,
        db: int = 10,
        http: int = 15,
    ):
        self.default = default
        self.llm = llm
        self.auth = auth
        self.db = db
        self.http = http

    @classmethod
    def from_resilience_config(cls) -> "TimeoutConfig":
        """Load from global resilience configuration"""
        config = get_resilience_config()
        return cls(
            default=config.timeout.default,
            llm=config.timeout.llm,
            auth=config.timeout.auth,
            db=config.timeout.db,
            http=config.timeout.http,
        )


def get_timeout_for_operation(operation_type: str) -> int:
    """
    Get timeout value for an operation type.

    Args:
        operation_type: Type of operation (llm, auth, db, http, default)

    Returns:
        Timeout in seconds
    """
    config = TimeoutConfig.from_resilience_config()
    return getattr(config, operation_type, config.default)


def with_timeout(
    seconds: int | None = None,
    operation_type: str | None = None,
) -> Callable[[Callable[P, T]], Callable[P, T]]:
    """
    Decorator to enforce timeout on async functions.

    Args:
        seconds: Timeout in seconds (overrides operation_type)
        operation_type: Type of operation (llm, auth, db, http) for auto-timeout

    Usage:
        # Explicit timeout
        @with_timeout(seconds=30)
        async def call_external_api() -> dict[str, Any]:
            async with httpx.AsyncClient() as client:
                return await client.get("https://api.example.com")

        # Auto-timeout based on operation type
        @with_timeout(operation_type="llm")
        async def generate_response(prompt: str) -> str:
            # Uses LLM timeout (60s by default)
            return await llm_client.generate(prompt)

        # Combine with other resilience patterns
        @circuit_breaker(name="llm")
        @retry_with_backoff(max_attempts=3)
        @with_timeout(operation_type="llm")
        async def call_llm(prompt: str) -> str:
            return await llm_client.generate(prompt)
    """

    def decorator(func: Callable[P, T]) -> Callable[P, T]:
        # Determine timeout value
        if seconds is not None:
            timeout_value = seconds
        elif operation_type is not None:
            timeout_value = get_timeout_for_operation(operation_type)
        else:
            timeout_value = get_timeout_for_operation("default")

        @functools.wraps(func)
        async def async_wrapper(*args: P.args, **kwargs: P.kwargs) -> T:
            """Async wrapper with timeout enforcement"""
            with tracer.start_as_current_span(
                f"timeout.{func.__name__}",
                attributes={
                    "timeout.seconds": timeout_value,
                    "timeout.operation_type": operation_type or "default",
                },
            ) as span:
                try:
                    # Use asyncio.timeout() for Python 3.11+, wait_for() for 3.10
                    if sys.version_info >= (3, 11):
                        async with asyncio.timeout(timeout_value):
                            result = await func(*args, **kwargs)  # type: ignore[misc]
                    else:
                        result = await asyncio.wait_for(
                            func(*args, **kwargs),
                            timeout=timeout_value,
                        )

                    span.set_attribute("timeout.exceeded", False)
                    return result  # type: ignore[no-any-return]

                except asyncio.TimeoutError as e:
                    # Timeout exceeded
                    span.set_attribute("timeout.exceeded", True)

                    logger.warning(
                        f"Timeout exceeded: {func.__name__} ({timeout_value}s)",
                        extra={
                            "function": func.__name__,
                            "timeout_seconds": timeout_value,
                            "operation_type": operation_type or "default",
                        },
                    )

                    # Emit metric
                    timeout_exceeded_counter.add(
                        1,
                        attributes={
                            "function": func.__name__,
                            "operation_type": operation_type or "default",
                            "timeout_seconds": timeout_value,
                        },
                    )

                    # Wrap in our custom exception
                    from mcp_server_langgraph.core.exceptions import TimeoutError as MCPTimeoutError

                    raise MCPTimeoutError(
                        message=f"Operation timed out after {timeout_value}s",
                        metadata={
                            "function": func.__name__,
                            "timeout_seconds": timeout_value,
                            "operation_type": operation_type or "default",
                        },
                    ) from e

        # Only works with async functions
        import asyncio as aio

        if not aio.iscoroutinefunction(func):
            raise TypeError(f"@with_timeout can only be applied to async functions, got {func.__name__}")

        return async_wrapper  # type: ignore

    return decorator


class TimeoutContext:
    """
    Context manager for timeout enforcement (alternative to decorator).

    Usage:
        async with TimeoutContext(seconds=30) as timeout:
            result = await some_async_operation()
    """

    def __init__(
        self,
        seconds: int | None = None,
        operation_type: str | None = None,
    ):
        if seconds is not None:
            self.timeout_value = seconds
        elif operation_type is not None:
            self.timeout_value = get_timeout_for_operation(operation_type)
        else:
            self.timeout_value = get_timeout_for_operation("default")

        self.operation_type = operation_type or "default"
        self._context_manager = None

    async def __aenter__(self) -> None:
        """Enter timeout context"""
        if sys.version_info >= (3, 11):
            self._context_manager = asyncio.timeout(self.timeout_value)  # type: ignore[assignment]
        else:
            # For Python 3.10, we'll handle timeout differently
            self._start_time = asyncio.get_event_loop().time()

        if self._context_manager:
            await self._context_manager.__aenter__()  # type: ignore[unreachable]

        return self  # type: ignore[return-value]

    async def __aexit__(self, exc_type, exc_val, exc_tb: Any) -> None:  # type: ignore[no-untyped-def]
        """Exit timeout context"""
        if self._context_manager:
            try:  # type: ignore[unreachable]
                await self._context_manager.__aexit__(exc_type, exc_val, exc_tb)
            except asyncio.TimeoutError as e:
                # Convert to our custom exception
                from mcp_server_langgraph.core.exceptions import TimeoutError as MCPTimeoutError

                raise MCPTimeoutError(
                    message=f"Operation timed out after {self.timeout_value}s",
                    metadata={
                        "timeout_seconds": self.timeout_value,
                        "operation_type": self.operation_type,
                    },
                ) from e
        elif hasattr(self, "_start_time"):
            # Manual timeout check for Python 3.10
            elapsed = asyncio.get_event_loop().time() - self._start_time
            if elapsed > self.timeout_value and exc_type is None:
                from mcp_server_langgraph.core.exceptions import TimeoutError as MCPTimeoutError

                raise MCPTimeoutError(
                    message=f"Operation timed out after {self.timeout_value}s",
                    metadata={
                        "timeout_seconds": self.timeout_value,
                        "operation_type": self.operation_type,
                        "elapsed_seconds": elapsed,
                    },
                )

        return None  # Don't suppress exceptions


# Convenience functions for common timeout patterns
async def run_with_timeout(  # type: ignore[no-untyped-def]
    coro,
    seconds: int | None = None,
    operation_type: str | None = None,
):
    """
    Run a coroutine with timeout.

    Args:
        coro: Coroutine to run
        seconds: Timeout in seconds
        operation_type: Operation type for auto-timeout

    Returns:
        Result of the coroutine

    Raises:
        TimeoutError: If operation exceeds timeout

    Usage:
        result = await run_with_timeout(
            llm_client.generate(prompt),
            operation_type="llm"
        )
    """
    async with TimeoutContext(seconds=seconds, operation_type=operation_type):
        return await coro
