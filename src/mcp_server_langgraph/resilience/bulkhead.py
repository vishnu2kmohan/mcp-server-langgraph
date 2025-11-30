"""
Bulkhead isolation pattern for resource pool limits.

Prevents resource exhaustion by limiting concurrent operations per resource type.
Uses asyncio.Semaphore for concurrency control.

See ADR-0026 for design rationale.
"""

import asyncio
import functools
import logging
from collections.abc import Callable
from typing import Any, ParamSpec, TypeVar

from opentelemetry import trace

from mcp_server_langgraph.observability.telemetry import bulkhead_active_operations_gauge, bulkhead_rejected_counter
from mcp_server_langgraph.resilience.config import get_resilience_config

logger = logging.getLogger(__name__)
tracer = trace.get_tracer(__name__)

P = ParamSpec("P")
T = TypeVar("T")


class BulkheadConfig:
    """Bulkhead configuration for different resource types"""

    def __init__(
        self,
        llm_limit: int = 10,
        openfga_limit: int = 50,
        redis_limit: int = 100,
        db_limit: int = 20,
    ):
        self.llm_limit = llm_limit
        self.openfga_limit = openfga_limit
        self.redis_limit = redis_limit
        self.db_limit = db_limit

    @classmethod
    def from_resilience_config(cls) -> "BulkheadConfig":
        """Load from global resilience configuration"""
        config = get_resilience_config()
        return cls(
            llm_limit=config.bulkhead.llm_limit,
            openfga_limit=config.bulkhead.openfga_limit,
            redis_limit=config.bulkhead.redis_limit,
            db_limit=config.bulkhead.db_limit,
        )


# Global semaphores for resource types
_bulkhead_semaphores: dict[str, asyncio.Semaphore] = {}


def get_bulkhead(resource_type: str, limit: int | None = None) -> asyncio.Semaphore:
    """
    Get or create a bulkhead semaphore for a resource type.

    Args:
        resource_type: Type of resource (llm, openfga, redis, db, custom)
        limit: Concurrency limit (optional override)

    Returns:
        asyncio.Semaphore for the resource type
    """
    if resource_type in _bulkhead_semaphores:
        return _bulkhead_semaphores[resource_type]

    # Determine limit
    if limit is None:
        config = BulkheadConfig.from_resilience_config()
        limit = getattr(config, f"{resource_type}_limit", 10)  # Default to 10

    # Create semaphore
    semaphore = asyncio.Semaphore(limit)
    _bulkhead_semaphores[resource_type] = semaphore

    logger.info(
        f"Created bulkhead for {resource_type}",
        extra={"resource_type": resource_type, "limit": limit},
    )

    return semaphore


def with_bulkhead(
    resource_type: str,
    limit: int | None = None,
    wait: bool = True,
) -> Callable[[Callable[P, T]], Callable[P, T]]:
    """
    Decorator to limit concurrent executions of a function.

    Args:
        resource_type: Type of resource (llm, openfga, redis, db, custom)
        limit: Concurrency limit (overrides config)
        wait: If True, wait for slot. If False, reject immediately if no slots available.

    Usage:
        # Limit to 10 concurrent LLM calls
        @with_bulkhead(resource_type="llm", limit=10)
        async def call_llm(prompt: str) -> str:
            async with httpx.AsyncClient() as client:
                response = await client.post(...)
                return response.json()

        # Reject immediately if no slots (fail-fast)
        @with_bulkhead(resource_type="openfga", wait=False)
        async def check_permission(user: str, resource: str) -> bool:
            return await openfga_client.check(user, resource)

        # Combine with other resilience patterns
        @circuit_breaker(name="llm")
        @retry_with_backoff(max_attempts=3)
        @with_timeout(operation_type="llm")
        @with_bulkhead(resource_type="llm")
        async def call_llm_with_resilience(prompt: str) -> str:
            return await llm_client.generate(prompt)
    """

    def decorator(func: Callable[P, T]) -> Callable[P, T]:
        # Get or create bulkhead semaphore
        semaphore = get_bulkhead(resource_type, limit)

        @functools.wraps(func)
        async def async_wrapper(*args: P.args, **kwargs: P.kwargs) -> T:
            """Async wrapper with bulkhead isolation"""
            # Get waiters count safely (attribute may not exist in all Python versions)
            try:
                waiters_count = len(semaphore._waiters) if hasattr(semaphore, "_waiters") and semaphore._waiters else 0
            except (AttributeError, TypeError):
                waiters_count = 0

            with tracer.start_as_current_span(
                f"bulkhead.{resource_type}",
                attributes={
                    "bulkhead.resource_type": resource_type,
                    "bulkhead.limit": limit or 10,
                    "bulkhead.available": semaphore._value if hasattr(semaphore, "_value") else 0,
                },
            ) as span:
                # Check if slots are available (semaphore._value == 0 means no slots)
                slots_available = semaphore._value if hasattr(semaphore, "_value") else 1
                if not wait and slots_available == 0:
                    # No slots available, reject immediately
                    span.set_attribute("bulkhead.rejected", True)

                    logger.warning(
                        f"Bulkhead rejected request: {resource_type}",
                        extra={
                            "resource_type": resource_type,
                            "function": func.__name__,
                            "reason": "no_available_slots",
                        },
                    )

                    # Emit metric
                    try:
                        bulkhead_rejected_counter.add(
                            1,
                            attributes={
                                "resource_type": resource_type,
                                "function": func.__name__,
                            },
                        )
                    except RuntimeError:
                        # Observability not initialized (can happen in tests or during shutdown)
                        pass

                    # Raise our custom exception
                    from mcp_server_langgraph.core.exceptions import BulkheadRejectedError

                    raise BulkheadRejectedError(
                        message=f"Bulkhead rejected request for {resource_type} (no available slots)",
                        metadata={
                            "resource_type": resource_type,
                            "function": func.__name__,
                            "limit": limit or 10,
                        },
                    )

                # Acquire semaphore (wait if necessary)
                async with semaphore:
                    span.set_attribute("bulkhead.rejected", False)
                    span.set_attribute("bulkhead.active", waiters_count + 1)

                    # Emit metric for active operations
                    # Get active count safely (since we're inside the semaphore, use the value we calculated earlier)
                    active_count = waiters_count + 1
                    try:
                        bulkhead_active_operations_gauge.set(
                            active_count,
                            attributes={"resource_type": resource_type},
                        )
                    except RuntimeError:
                        # Observability not initialized (can happen in tests or during shutdown)
                        pass

                    # Execute function
                    result = await func(*args, **kwargs)  # type: ignore[misc]

                    return result  # type: ignore[no-any-return]

        # Only works with async functions
        import asyncio as aio

        if not aio.iscoroutinefunction(func):
            msg = f"@with_bulkhead can only be applied to async functions, got {func.__name__}"
            raise TypeError(msg)

        return async_wrapper  # type: ignore

    return decorator


class BulkheadContext:
    """
    Context manager for bulkhead isolation (alternative to decorator).

    Usage:
        async with BulkheadContext(resource_type="llm"):
            result = await call_llm(prompt)
    """

    def __init__(
        self,
        resource_type: str,
        limit: int | None = None,
        wait: bool = True,
    ):
        self.resource_type = resource_type
        self.semaphore = get_bulkhead(resource_type, limit)
        self.wait = wait

    async def __aenter__(self) -> None:
        """Acquire bulkhead slot"""
        # Check if slots are available (semaphore._value == 0 means no slots)
        slots_available = self.semaphore._value if hasattr(self.semaphore, "_value") else 1
        if not self.wait and slots_available == 0:
            # Reject immediately if no slots
            from mcp_server_langgraph.core.exceptions import BulkheadRejectedError

            # Calculate total limit safely
            waiters_count = (
                len(self.semaphore._waiters) if hasattr(self.semaphore, "_waiters") and self.semaphore._waiters else 0
            )
            total_limit = self.semaphore._value + waiters_count if hasattr(self.semaphore, "_value") else 10

            raise BulkheadRejectedError(
                message=f"Bulkhead rejected request for {self.resource_type}",
                metadata={
                    "resource_type": self.resource_type,
                    "limit": total_limit,
                },
            )

        await self.semaphore.acquire()
        return self  # type: ignore[return-value]

    async def __aexit__(self, exc_type, exc_val, exc_tb: Any) -> None:  # type: ignore[no-untyped-def]
        """Release bulkhead slot"""
        self.semaphore.release()
        return None  # Don't suppress exceptions


def get_bulkhead_stats(resource_type: str | None = None) -> dict[str, dict[str, int]]:
    """
    Get statistics for bulkheads.

    Args:
        resource_type: Specific resource type, or None for all

    Returns:
        Dictionary with bulkhead statistics

    Usage:
        stats = get_bulkhead_stats()
        # {
        #     "llm": {"limit": 10, "available": 3, "active": 7, "waiting": 2},
        #     "openfga": {"limit": 50, "available": 45, "active": 5, "waiting": 0},
        # }
    """
    stats = {}

    resource_types = [resource_type] if resource_type else _bulkhead_semaphores.keys()

    for res_type in resource_types:
        if res_type not in _bulkhead_semaphores:
            continue

        semaphore = _bulkhead_semaphores[res_type]

        # Safely get semaphore attributes
        try:
            available = semaphore._value if hasattr(semaphore, "_value") else 0
            waiters = semaphore._waiters if hasattr(semaphore, "_waiters") and semaphore._waiters else []
            active = len(waiters)
            waiting = len([w for w in waiters if not w.done()]) if waiters else 0
        except (AttributeError, TypeError):
            available = 0
            active = 0
            waiting = 0

        stats[res_type] = {
            "limit": available + active,
            "available": available,
            "active": active,
            "waiting": waiting,
        }

    return stats


def reset_bulkhead(resource_type: str) -> None:
    """
    Reset a bulkhead (for testing).

    Args:
        resource_type: Resource type to reset

    Warning: Only use this for testing! In production, bulkheads should not be reset.
    """
    if resource_type in _bulkhead_semaphores:
        del _bulkhead_semaphores[resource_type]
        logger.warning(f"Bulkhead reset for {resource_type} (testing only)")


def reset_all_bulkheads() -> None:
    """
    Reset all bulkheads (for testing).

    Warning: Only use this for testing! In production, bulkheads should not be reset.
    """
    _bulkhead_semaphores.clear()
    logger.warning("All bulkheads reset (testing only)")
