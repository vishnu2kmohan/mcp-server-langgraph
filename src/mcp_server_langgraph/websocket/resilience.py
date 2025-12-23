"""
WebSocket Resilience Integration.

Provides circuit breaker and timeout protection for WebSocket handlers
when calling external services.

Usage:
    from mcp_server_langgraph.websocket.resilience import with_circuit_breaker

    class MyHandler(WebSocketBase):
        async def _fetch_from_service(self, id: str) -> dict:
            return await with_circuit_breaker(
                "my_service",
                self._service.get(id),
                fallback={"error": "Service unavailable"},
            )

Known Issues
------------

**pybreaker call_async Bug (as of pybreaker 1.2.0)**

The pybreaker library's ``call_async`` method has a bug where it references
``gen`` (tornado.gen) without importing it, causing a ``NameError``:

    NameError: name 'gen' is not defined

This affects the ``with_circuit_breaker`` function in this module.

**Workaround Options:**

1. **Use synchronous calls with asyncio.to_thread** (Recommended for I/O-bound):

   .. code-block:: python

       from mcp_server_langgraph.resilience.circuit_breaker import get_circuit_breaker

       breaker = get_circuit_breaker("my_service")
       result = await asyncio.to_thread(breaker.call, sync_operation)

2. **Use synchronous calls directly** (for quick operations):

   .. code-block:: python

       breaker = get_circuit_breaker("my_service")
       result = breaker.call(sync_operation)

3. **Install tornado** (adds dependency but fixes the bug):

   .. code-block:: bash

       pip install tornado

**Status:** Issue tracked at https://github.com/danielfm/pybreaker/issues
Consider migrating to ``aiobreaker`` for a pure async implementation.
"""

from __future__ import annotations

import logging
from collections.abc import Awaitable, Callable
from typing import TypeVar

import pybreaker

from mcp_server_langgraph.resilience.circuit_breaker import (
    CircuitBreakerState,
    get_circuit_breaker,
)

logger = logging.getLogger(__name__)

T = TypeVar("T")


async def with_circuit_breaker(
    service_name: str,
    operation: Awaitable[T],
    fallback: T | None = None,
    fallback_fn: Callable[[], T | Awaitable[T]] | None = None,
) -> T:
    """
    Execute an async operation with circuit breaker protection.

    This is designed for use within WebSocket handlers to protect
    external service calls (Redis, OpenFGA, databases, etc.).

    Args:
        service_name: Name of the service for circuit breaker tracking
        operation: The async operation to execute
        fallback: Static fallback value if circuit is open
        fallback_fn: Fallback function to call if circuit is open

    Returns:
        Result of the operation, or fallback if circuit is open

    Raises:
        pybreaker.CircuitBreakerError: If circuit is open and no fallback provided

    Example:
        # Simple fallback
        result = await with_circuit_breaker(
            "redis",
            redis.get("key"),
            fallback=None,
        )

        # Dynamic fallback
        result = await with_circuit_breaker(
            "openfga",
            openfga.check(user, resource),
            fallback_fn=lambda: True,  # Fail open
        )
    """
    breaker = get_circuit_breaker(service_name)

    try:
        # Execute the operation through the circuit breaker
        # pybreaker's call_async is untyped
        result: T = await breaker.call_async(lambda: operation)  # type: ignore[no-untyped-call]
        return result

    except pybreaker.CircuitBreakerError:
        # Circuit is open, use fallback if provided
        logger.warning(
            f"Circuit breaker open for {service_name}, using fallback",
            extra={"service": service_name},
        )

        if fallback_fn is not None:
            fallback_result = fallback_fn()
            if hasattr(fallback_result, "__await__"):
                return await fallback_result
            return fallback_result

        if fallback is not None:
            return fallback

        # No fallback, re-raise
        raise


def get_circuit_breaker_state(service_name: str) -> CircuitBreakerState:
    """
    Get the current state of a circuit breaker.

    Args:
        service_name: Name of the service

    Returns:
        Current circuit breaker state
    """
    breaker = get_circuit_breaker(service_name)
    state = breaker.current_state

    if state == pybreaker.STATE_CLOSED:
        return CircuitBreakerState.CLOSED
    elif state == pybreaker.STATE_OPEN:
        return CircuitBreakerState.OPEN
    else:
        return CircuitBreakerState.HALF_OPEN


def is_circuit_open(service_name: str) -> bool:
    """
    Check if a circuit breaker is currently open.

    Args:
        service_name: Name of the service

    Returns:
        True if circuit is open, False otherwise
    """
    return get_circuit_breaker_state(service_name) == CircuitBreakerState.OPEN


# Pre-defined service names for WebSocket handlers
class WebSocketServices:
    """Standard service names for WebSocket circuit breakers."""

    REDIS = "websocket_redis"
    OPENFGA = "websocket_openfga"
    DATABASE = "websocket_database"
    METRICS_SERVICE = "websocket_metrics"
    COST_SERVICE = "websocket_cost"
    NOTIFICATIONS = "websocket_notifications"
