"""
WebSocket Resilience Integration Tests.

TDD tests for circuit breaker and timeout protection in WebSocket handlers.
"""

from __future__ import annotations

import gc
from unittest.mock import AsyncMock, MagicMock, patch

import pybreaker
import pytest

from mcp_server_langgraph.resilience.circuit_breaker import CircuitBreakerState
from mcp_server_langgraph.websocket.resilience import (
    WebSocketServices,
    get_circuit_breaker_state,
    is_circuit_open,
    with_circuit_breaker,
)

pytestmark = [pytest.mark.unit, pytest.mark.websocket, pytest.mark.resilience]


@pytest.mark.xdist_group(name="websocket_resilience")
class TestWithCircuitBreaker:
    """Test with_circuit_breaker async utility function."""

    def teardown_method(self) -> None:
        """Force GC to prevent mock accumulation in xdist workers."""
        gc.collect()

    @pytest.mark.asyncio
    async def test_successful_operation_returns_result(self) -> None:
        """
        GIVEN a successful async operation
        WHEN called with circuit breaker protection
        THEN it should return the operation result.
        """
        expected = {"data": "test_result"}

        async def successful_op():
            return expected

        with patch(
            "mcp_server_langgraph.websocket.resilience.get_circuit_breaker"
        ) as mock_get_cb:
            mock_breaker = MagicMock()
            mock_breaker.call_async = AsyncMock(return_value=expected)
            mock_get_cb.return_value = mock_breaker

            result = await with_circuit_breaker("test_service", successful_op())

            assert result == expected
            mock_get_cb.assert_called_once_with("test_service")

    @pytest.mark.asyncio
    async def test_circuit_open_uses_static_fallback(self) -> None:
        """
        GIVEN a circuit breaker in open state
        WHEN called with a static fallback value
        THEN it should return the fallback.
        """
        fallback_value = {"error": "Service unavailable"}

        async def failing_op():
            raise Exception("Service down")

        with patch(
            "mcp_server_langgraph.websocket.resilience.get_circuit_breaker"
        ) as mock_get_cb:
            mock_breaker = MagicMock()
            mock_breaker.call_async = AsyncMock(
                side_effect=pybreaker.CircuitBreakerError()
            )
            mock_get_cb.return_value = mock_breaker

            result = await with_circuit_breaker(
                "test_service",
                failing_op(),
                fallback=fallback_value,
            )

            assert result == fallback_value

    @pytest.mark.asyncio
    async def test_circuit_open_uses_sync_fallback_function(self) -> None:
        """
        GIVEN a circuit breaker in open state
        WHEN called with a sync fallback function
        THEN it should call and return the fallback function result.
        """

        async def failing_op():
            raise Exception("Service down")

        fallback_called = []

        def sync_fallback():
            fallback_called.append(True)
            return True  # Fail open

        with patch(
            "mcp_server_langgraph.websocket.resilience.get_circuit_breaker"
        ) as mock_get_cb:
            mock_breaker = MagicMock()
            mock_breaker.call_async = AsyncMock(
                side_effect=pybreaker.CircuitBreakerError()
            )
            mock_get_cb.return_value = mock_breaker

            result = await with_circuit_breaker(
                "test_service",
                failing_op(),
                fallback_fn=sync_fallback,
            )

            assert result is True
            assert len(fallback_called) == 1

    @pytest.mark.asyncio
    async def test_circuit_open_uses_async_fallback_function(self) -> None:
        """
        GIVEN a circuit breaker in open state
        WHEN called with an async fallback function
        THEN it should await and return the fallback function result.
        """

        async def failing_op():
            raise Exception("Service down")

        async def async_fallback():
            return {"cached": True}

        with patch(
            "mcp_server_langgraph.websocket.resilience.get_circuit_breaker"
        ) as mock_get_cb:
            mock_breaker = MagicMock()
            mock_breaker.call_async = AsyncMock(
                side_effect=pybreaker.CircuitBreakerError()
            )
            mock_get_cb.return_value = mock_breaker

            result = await with_circuit_breaker(
                "test_service",
                failing_op(),
                fallback_fn=async_fallback,
            )

            assert result == {"cached": True}

    @pytest.mark.asyncio
    async def test_circuit_open_raises_without_fallback(self) -> None:
        """
        GIVEN a circuit breaker in open state
        WHEN called without any fallback
        THEN it should re-raise CircuitBreakerError.
        """

        async def failing_op():
            raise Exception("Service down")

        with patch(
            "mcp_server_langgraph.websocket.resilience.get_circuit_breaker"
        ) as mock_get_cb:
            mock_breaker = MagicMock()
            mock_breaker.call_async = AsyncMock(
                side_effect=pybreaker.CircuitBreakerError()
            )
            mock_get_cb.return_value = mock_breaker

            with pytest.raises(pybreaker.CircuitBreakerError):
                await with_circuit_breaker("test_service", failing_op())

    @pytest.mark.asyncio
    async def test_fallback_fn_takes_precedence_over_fallback(self) -> None:
        """
        GIVEN both fallback and fallback_fn provided
        WHEN circuit is open
        THEN fallback_fn should be used (it's checked first).
        """

        async def failing_op():
            raise Exception("Service down")

        with patch(
            "mcp_server_langgraph.websocket.resilience.get_circuit_breaker"
        ) as mock_get_cb:
            mock_breaker = MagicMock()
            mock_breaker.call_async = AsyncMock(
                side_effect=pybreaker.CircuitBreakerError()
            )
            mock_get_cb.return_value = mock_breaker

            result = await with_circuit_breaker(
                "test_service",
                failing_op(),
                fallback={"static": True},
                fallback_fn=lambda: {"dynamic": True},
            )

            assert result == {"dynamic": True}


@pytest.mark.xdist_group(name="websocket_resilience")
class TestGetCircuitBreakerState:
    """Test get_circuit_breaker_state helper function."""

    def teardown_method(self) -> None:
        """Force GC to prevent mock accumulation in xdist workers."""
        gc.collect()

    def test_returns_closed_state(self) -> None:
        """
        GIVEN a circuit breaker in closed state
        WHEN getting state
        THEN it should return CircuitBreakerState.CLOSED.
        """
        with patch(
            "mcp_server_langgraph.websocket.resilience.get_circuit_breaker"
        ) as mock_get_cb:
            mock_breaker = MagicMock()
            mock_breaker.current_state = pybreaker.STATE_CLOSED
            mock_get_cb.return_value = mock_breaker

            state = get_circuit_breaker_state("test_service")

            assert state == CircuitBreakerState.CLOSED

    def test_returns_open_state(self) -> None:
        """
        GIVEN a circuit breaker in open state
        WHEN getting state
        THEN it should return CircuitBreakerState.OPEN.
        """
        with patch(
            "mcp_server_langgraph.websocket.resilience.get_circuit_breaker"
        ) as mock_get_cb:
            mock_breaker = MagicMock()
            mock_breaker.current_state = pybreaker.STATE_OPEN
            mock_get_cb.return_value = mock_breaker

            state = get_circuit_breaker_state("test_service")

            assert state == CircuitBreakerState.OPEN

    def test_returns_half_open_state(self) -> None:
        """
        GIVEN a circuit breaker in half-open state
        WHEN getting state
        THEN it should return CircuitBreakerState.HALF_OPEN.
        """
        with patch(
            "mcp_server_langgraph.websocket.resilience.get_circuit_breaker"
        ) as mock_get_cb:
            mock_breaker = MagicMock()
            mock_breaker.current_state = pybreaker.STATE_HALF_OPEN
            mock_get_cb.return_value = mock_breaker

            state = get_circuit_breaker_state("test_service")

            assert state == CircuitBreakerState.HALF_OPEN


@pytest.mark.xdist_group(name="websocket_resilience")
class TestIsCircuitOpen:
    """Test is_circuit_open helper function."""

    def teardown_method(self) -> None:
        """Force GC to prevent mock accumulation in xdist workers."""
        gc.collect()

    def test_returns_true_when_open(self) -> None:
        """
        GIVEN a circuit breaker in open state
        WHEN checking is_circuit_open
        THEN it should return True.
        """
        with patch(
            "mcp_server_langgraph.websocket.resilience.get_circuit_breaker_state"
        ) as mock_get_state:
            mock_get_state.return_value = CircuitBreakerState.OPEN

            result = is_circuit_open("test_service")

            assert result is True

    def test_returns_false_when_closed(self) -> None:
        """
        GIVEN a circuit breaker in closed state
        WHEN checking is_circuit_open
        THEN it should return False.
        """
        with patch(
            "mcp_server_langgraph.websocket.resilience.get_circuit_breaker_state"
        ) as mock_get_state:
            mock_get_state.return_value = CircuitBreakerState.CLOSED

            result = is_circuit_open("test_service")

            assert result is False

    def test_returns_false_when_half_open(self) -> None:
        """
        GIVEN a circuit breaker in half-open state
        WHEN checking is_circuit_open
        THEN it should return False (allowing test request).
        """
        with patch(
            "mcp_server_langgraph.websocket.resilience.get_circuit_breaker_state"
        ) as mock_get_state:
            mock_get_state.return_value = CircuitBreakerState.HALF_OPEN

            result = is_circuit_open("test_service")

            assert result is False


@pytest.mark.xdist_group(name="websocket_resilience")
class TestWebSocketServices:
    """Test WebSocketServices predefined service names."""

    def test_has_redis_service_name(self) -> None:
        """WebSocketServices should have REDIS service name."""
        assert hasattr(WebSocketServices, "REDIS")
        assert WebSocketServices.REDIS == "websocket_redis"

    def test_has_openfga_service_name(self) -> None:
        """WebSocketServices should have OPENFGA service name."""
        assert hasattr(WebSocketServices, "OPENFGA")
        assert WebSocketServices.OPENFGA == "websocket_openfga"

    def test_has_database_service_name(self) -> None:
        """WebSocketServices should have DATABASE service name."""
        assert hasattr(WebSocketServices, "DATABASE")
        assert WebSocketServices.DATABASE == "websocket_database"

    def test_has_metrics_service_name(self) -> None:
        """WebSocketServices should have METRICS_SERVICE service name."""
        assert hasattr(WebSocketServices, "METRICS_SERVICE")
        assert WebSocketServices.METRICS_SERVICE == "websocket_metrics"

    def test_has_cost_service_name(self) -> None:
        """WebSocketServices should have COST_SERVICE service name."""
        assert hasattr(WebSocketServices, "COST_SERVICE")
        assert WebSocketServices.COST_SERVICE == "websocket_cost"

    def test_has_notifications_service_name(self) -> None:
        """WebSocketServices should have NOTIFICATIONS service name."""
        assert hasattr(WebSocketServices, "NOTIFICATIONS")
        assert WebSocketServices.NOTIFICATIONS == "websocket_notifications"
