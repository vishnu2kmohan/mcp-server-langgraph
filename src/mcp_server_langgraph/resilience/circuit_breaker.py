"""
Circuit breaker pattern implementation using pybreaker.

Prevents cascade failures by failing fast when a service is unhealthy.
Automatically recovers by testing the service periodically.

States:
- CLOSED: Normal operation, requests pass through
- OPEN: Service is failing, fail fast without calling service
- HALF_OPEN: Testing if service has recovered

See ADR-0026 for design rationale.
"""

import functools
import logging
from datetime import datetime
from enum import Enum
from typing import Any, Callable, Dict, Optional, ParamSpec, TypeVar

import pybreaker
from opentelemetry import trace

from mcp_server_langgraph.resilience.config import get_resilience_config

logger = logging.getLogger(__name__)
tracer = trace.get_tracer(__name__)

P = ParamSpec("P")
T = TypeVar("T")


class CircuitBreakerState(str, Enum):
    """Circuit breaker states"""

    CLOSED = "closed"  # Normal operation
    OPEN = "open"  # Failing, reject requests
    HALF_OPEN = "half_open"  # Testing recovery


class CircuitBreakerMetricsListener(pybreaker.CircuitBreakerListener):
    """
    Listener for circuit breaker events.

    Emits metrics and logs for observability.
    """

    def __init__(self, name: str) -> None:
        self.name = name
        self._state = CircuitBreakerState.CLOSED
        self._last_state_change = datetime.now()

    def state_change(
        self, breaker: pybreaker.CircuitBreaker, old: pybreaker.CircuitBreakerState, new: pybreaker.CircuitBreakerState
    ) -> None:
        """Called when circuit breaker state changes"""
        old_state = self._map_state(old)
        new_state = self._map_state(new)

        logger.warning(
            f"Circuit breaker state changed: {self.name}",
            extra={
                "service": self.name,
                "old_state": old_state.value,
                "new_state": new_state.value,
                "failure_count": breaker.fail_counter,
            },
        )

        # Record state change time
        self._state = new_state
        self._last_state_change = datetime.now()

        # Emit metric
        from mcp_server_langgraph.observability.telemetry import circuit_breaker_state_gauge

        circuit_breaker_state_gauge.set(
            1 if new_state == CircuitBreakerState.OPEN else 0,
            attributes={"service": self.name, "state": new_state.value},
        )

    # type: ignore[override]
    def before_call(self, breaker: pybreaker.CircuitBreaker, func: Callable[..., Any], *args: Any, **kwargs: Any) -> None:
        """Called before calling the protected function"""
        pass

    def success(self, breaker: pybreaker.CircuitBreaker) -> None:
        """Called on successful call"""
        from mcp_server_langgraph.observability.telemetry import circuit_breaker_success_counter

        circuit_breaker_success_counter.add(1, attributes={"service": self.name})

    def failure(self, breaker: pybreaker.CircuitBreaker, exception: Exception) -> None:  # type: ignore[override]
        """Called on failed call"""
        from mcp_server_langgraph.observability.telemetry import circuit_breaker_failure_counter

        logger.warning(
            f"Circuit breaker failure: {self.name}",
            exc_info=True,
            extra={
                "service": self.name,
                "failure_count": breaker.fail_counter,
                "exception_type": type(exception).__name__,
            },
        )

        circuit_breaker_failure_counter.add(
            1,
            attributes={
                "service": self.name,
                "exception_type": type(exception).__name__,
            },
        )

    @staticmethod
    def _map_state(state: pybreaker.CircuitBreakerState) -> CircuitBreakerState:
        """Map pybreaker state to our enum"""
        if state == pybreaker.STATE_CLOSED:  # type: ignore[comparison-overlap]
            return CircuitBreakerState.CLOSED
        elif state == pybreaker.STATE_OPEN:  # type: ignore[comparison-overlap]
            return CircuitBreakerState.OPEN
        else:  # STATE_HALF_OPEN
            return CircuitBreakerState.HALF_OPEN


# Global circuit breaker instances
_circuit_breakers: Dict[str, pybreaker.CircuitBreaker] = {}


def get_circuit_breaker(name: str) -> pybreaker.CircuitBreaker:
    """
    Get or create a circuit breaker for a service.

    Args:
        name: Service name (e.g., "llm", "openfga", "redis")

    Returns:
        CircuitBreaker instance
    """
    if name in _circuit_breakers:
        return _circuit_breakers[name]

    # Load configuration
    config = get_resilience_config()
    cb_config = config.circuit_breakers.get(name)

    if not cb_config:
        # Create default config
        from mcp_server_langgraph.resilience.config import CircuitBreakerConfig

        cb_config = CircuitBreakerConfig(name=name)

    # Create circuit breaker
    breaker = pybreaker.CircuitBreaker(
        fail_max=cb_config.fail_max,
        reset_timeout=cb_config.timeout_duration,  # pybreaker uses reset_timeout, not timeout_duration
        exclude=[],  # Don't exclude any exceptions
        listeners=[CircuitBreakerMetricsListener(name)],
        name=name,
    )

    _circuit_breakers[name] = breaker
    logger.info(
        f"Created circuit breaker: {name}",
        extra={
            "fail_max": cb_config.fail_max,
            "timeout_duration": cb_config.timeout_duration,
        },
    )

    return breaker


def circuit_breaker(  # noqa: C901
    name: str,
    fail_max: Optional[int] = None,
    timeout: Optional[int] = None,
    fallback: Optional[Callable[..., Any]] = None,
) -> Callable[[Callable[P, T]], Callable[P, T]]:
    """
    Decorator to protect a function with a circuit breaker.

    Args:
        name: Service name for the circuit breaker
        fail_max: Max failures before opening (optional override)
        timeout: Timeout duration in seconds (optional override)
        fallback: Fallback function to call when circuit is open

    Usage:
        @circuit_breaker(name="llm", fail_max=5, timeout=60)
        async def call_llm(prompt: str) -> str:
            return await llm_client.generate(prompt)

        # With fallback
        @circuit_breaker(name="openfga", fallback=lambda *args: True)
        async def check_permission(user: str, resource: str) -> bool:
            return await openfga_client.check(user, resource)
    """

    def decorator(func: Callable[P, T]) -> Callable[P, T]:
        # Get or create circuit breaker
        breaker = get_circuit_breaker(name)

        # Override config if provided
        if fail_max is not None:
            breaker._fail_max = fail_max
        if timeout is not None:
            breaker._reset_timeout = timeout  # pybreaker uses _reset_timeout in seconds

        @functools.wraps(func)
        async def async_wrapper(*args: P.args, **kwargs: P.kwargs) -> T:
            """Async wrapper with circuit breaker"""
            import asyncio

            with tracer.start_as_current_span(
                f"circuit_breaker.{name}",
                attributes={
                    "circuit_breaker.name": name,
                    "circuit_breaker.state": breaker.current_state,
                },
            ) as span:
                try:
                    # Wrap the async function in a sync callable for pybreaker
                    # pybreaker will handle the state transitions
                    def _sync_wrapper() -> None:
                        # This won't work directly - we need a different approach
                        raise RuntimeError("Should not be called directly")

                    # Call before_call to handle state transitions (OPEN -> HALF_OPEN after timeout)
                    try:
                        with breaker._lock:
                            # This will transition to HALF_OPEN if timeout elapsed, or raise if still OPEN
                            breaker.state.before_call(func, *args, **kwargs)
                            # Also notify listeners
                            for listener in breaker.listeners:
                                listener.before_call(breaker, func, *args, **kwargs)
                    except pybreaker.CircuitBreakerError:
                        # Circuit is still OPEN (timeout not elapsed)
                        span.set_attribute("circuit_breaker.success", False)
                        span.set_attribute("circuit_breaker.fallback_used", fallback is not None)

                        logger.warning(
                            f"Circuit breaker open for {name}, failing fast",
                            extra={"service": name, "fallback": fallback is not None},
                        )

                        if fallback:
                            logger.info(f"Using fallback for {name}")
                            if asyncio.iscoroutinefunction(fallback):
                                return await fallback(*args, **kwargs)  # type: ignore[no-any-return]
                            else:
                                return fallback(*args, **kwargs)  # type: ignore[no-any-return]
                        else:
                            # Raise our custom exception
                            from mcp_server_langgraph.core.exceptions import CircuitBreakerOpenError

                            raise CircuitBreakerOpenError(
                                message=f"Circuit breaker open for {name}",
                                metadata={"service": name, "state": breaker.current_state},
                            )

                    # Call the function
                    try:
                        result: T = await func(*args, **kwargs)  # type: ignore[misc]

                        # Success - handle via state machine
                        with breaker._lock:
                            breaker._state_storage.increment_counter()
                            for listener in breaker.listeners:  # type: ignore[assignment]
                                listener.success(breaker)
                            breaker.state.on_success()

                        span.set_attribute("circuit_breaker.success", True)
                        return result

                    except Exception as e:
                        # Failure - handle via state machine
                        try:
                            with breaker._lock:
                                if breaker.is_system_error(e):
                                    breaker._inc_counter()
                                    for listener in breaker.listeners:  # type: ignore[assignment]
                                        listener.failure(breaker, e)
                                    breaker.state.on_failure(e)
                                else:
                                    # Not a system error, treat as success
                                    breaker._state_storage.increment_counter()
                                    for listener in breaker.listeners:  # type: ignore[assignment]
                                        listener.success(breaker)
                                    breaker.state.on_success()
                        except pybreaker.CircuitBreakerError:
                            # Circuit just opened on this failure
                            # Don't use fallback here - the circuit opened because of THIS failure
                            # Fallback is only used when circuit is already open BEFORE the call
                            pass

                        # Re-raise the original exception
                        span.set_attribute("circuit_breaker.success", False)
                        raise

                except pybreaker.CircuitBreakerError as e:  # noqa: F841
                    # This shouldn't happen with our manual implementation, but just in case
                    span.set_attribute("circuit_breaker.success", False)
                    raise

        @functools.wraps(func)
        def sync_wrapper(*args: P.args, **kwargs: P.kwargs) -> T:
            """Sync wrapper with circuit breaker"""
            # Similar to async_wrapper but for sync functions
            try:
                result: T = breaker.call(func, *args, **kwargs)
                return result
            except pybreaker.CircuitBreakerError as e:
                if fallback:
                    return fallback(*args, **kwargs)  # type: ignore[no-any-return]
                else:
                    from mcp_server_langgraph.core.exceptions import CircuitBreakerOpenError

                    raise CircuitBreakerOpenError(
                        message=f"Circuit breaker open for {name}",
                        metadata={"service": name},
                    ) from e

        # Return appropriate wrapper
        import asyncio

        if asyncio.iscoroutinefunction(func):
            return async_wrapper  # type: ignore[return-value]
        else:
            return sync_wrapper

    return decorator


def reset_circuit_breaker(name: str) -> None:
    """
    Manually reset a circuit breaker to closed state.

    Args:
        name: Service name

    Usage:
        reset_circuit_breaker("llm")  # Force close circuit
    """
    if name in _circuit_breakers:
        breaker = _circuit_breakers[name]
        # Use the proper pybreaker API to close the circuit
        breaker.close()
        logger.info(f"Circuit breaker manually reset: {name}")


def get_circuit_breaker_state(name: str) -> CircuitBreakerState:
    """
    Get current state of a circuit breaker.

    Args:
        name: Service name

    Returns:
        Current circuit breaker state
    """
    if name not in _circuit_breakers:
        return CircuitBreakerState.CLOSED

    breaker = _circuit_breakers[name]
    return CircuitBreakerMetricsListener._map_state(breaker.current_state)  # type: ignore[arg-type]


def get_all_circuit_breaker_states() -> Dict[str, CircuitBreakerState]:
    """
    Get states of all circuit breakers.

    Returns:
        Dictionary mapping service name to state
    """
    return {name: get_circuit_breaker_state(name) for name in _circuit_breakers}


def reset_all_circuit_breakers() -> None:
    """
    Reset all circuit breakers (for testing).

    This clears the global circuit breaker registry.
    """
    _circuit_breakers.clear()
    logger.info("All circuit breakers reset")
