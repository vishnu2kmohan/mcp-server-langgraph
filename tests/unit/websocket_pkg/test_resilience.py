"""Unit tests for WebSocket resilience integration.

Tests circuit breaker and timeout protection for WebSocket handlers
when calling external services.
"""

from __future__ import annotations

import gc
from unittest.mock import AsyncMock, MagicMock, patch

import pybreaker
import pytest

from mcp_server_langgraph.resilience.circuit_breaker import CircuitBreakerState


@pytest.mark.unit
@pytest.mark.websocket
@pytest.mark.xdist_group(name="websocket_resilience")
class TestWithCircuitBreaker:
    """Test suite for with_circuit_breaker function."""

    def teardown_method(self) -> None:
        """Force GC to prevent mock accumulation in xdist workers."""
        gc.collect()

    @pytest.mark.asyncio
    async def test_executes_operation_successfully(self) -> None:
        """Test successful operation execution."""
        from mcp_server_langgraph.websocket.resilience import with_circuit_breaker

        mock_breaker = MagicMock()
        mock_breaker.call_async = AsyncMock(return_value="success")

        with patch(
            "mcp_server_langgraph.websocket.resilience.get_circuit_breaker",
            return_value=mock_breaker,
        ):
            async_op = AsyncMock(return_value="result")()
            result = await with_circuit_breaker("test_service", async_op)

        assert result == "success"

    @pytest.mark.asyncio
    async def test_uses_static_fallback_on_circuit_open(self) -> None:
        """Test static fallback is used when circuit is open."""
        from mcp_server_langgraph.websocket.resilience import with_circuit_breaker

        mock_breaker = MagicMock()
        mock_breaker.call_async = AsyncMock(side_effect=pybreaker.CircuitBreakerError())

        with patch(
            "mcp_server_langgraph.websocket.resilience.get_circuit_breaker",
            return_value=mock_breaker,
        ):
            async_op = AsyncMock()()
            result = await with_circuit_breaker(
                "test_service",
                async_op,
                fallback={"error": "service unavailable"},
            )

        assert result == {"error": "service unavailable"}

    @pytest.mark.asyncio
    async def test_uses_fallback_function_on_circuit_open(self) -> None:
        """Test fallback function is called when circuit is open."""
        from mcp_server_langgraph.websocket.resilience import with_circuit_breaker

        mock_breaker = MagicMock()
        mock_breaker.call_async = AsyncMock(side_effect=pybreaker.CircuitBreakerError())

        fallback_fn = MagicMock(return_value="fallback_value")

        with patch(
            "mcp_server_langgraph.websocket.resilience.get_circuit_breaker",
            return_value=mock_breaker,
        ):
            async_op = AsyncMock()()
            result = await with_circuit_breaker(
                "test_service",
                async_op,
                fallback_fn=fallback_fn,
            )

        fallback_fn.assert_called_once()
        assert result == "fallback_value"

    @pytest.mark.asyncio
    async def test_uses_async_fallback_function(self) -> None:
        """Test async fallback function is awaited when circuit is open."""
        from mcp_server_langgraph.websocket.resilience import with_circuit_breaker

        mock_breaker = MagicMock()
        mock_breaker.call_async = AsyncMock(side_effect=pybreaker.CircuitBreakerError())

        async def async_fallback() -> str:
            return "async_fallback_value"

        with patch(
            "mcp_server_langgraph.websocket.resilience.get_circuit_breaker",
            return_value=mock_breaker,
        ):
            async_op = AsyncMock()()
            result = await with_circuit_breaker(
                "test_service",
                async_op,
                fallback_fn=async_fallback,
            )

        assert result == "async_fallback_value"

    @pytest.mark.asyncio
    async def test_fallback_fn_takes_precedence_over_fallback(self) -> None:
        """Test fallback_fn is used when both fallback and fallback_fn provided."""
        from mcp_server_langgraph.websocket.resilience import with_circuit_breaker

        mock_breaker = MagicMock()
        mock_breaker.call_async = AsyncMock(side_effect=pybreaker.CircuitBreakerError())

        with patch(
            "mcp_server_langgraph.websocket.resilience.get_circuit_breaker",
            return_value=mock_breaker,
        ):
            async_op = AsyncMock()()
            result = await with_circuit_breaker(
                "test_service",
                async_op,
                fallback="static_value",
                fallback_fn=lambda: "fn_value",
            )

        assert result == "fn_value"

    @pytest.mark.asyncio
    async def test_raises_when_circuit_open_without_fallback(self) -> None:
        """Test exception is raised when circuit is open and no fallback."""
        from mcp_server_langgraph.websocket.resilience import with_circuit_breaker

        mock_breaker = MagicMock()
        mock_breaker.call_async = AsyncMock(side_effect=pybreaker.CircuitBreakerError())

        with patch(
            "mcp_server_langgraph.websocket.resilience.get_circuit_breaker",
            return_value=mock_breaker,
        ):
            async_op = AsyncMock()()

            with pytest.raises(pybreaker.CircuitBreakerError):
                await with_circuit_breaker("test_service", async_op)

    @pytest.mark.asyncio
    async def test_logs_warning_on_circuit_open(self) -> None:
        """Test warning is logged when circuit is open."""
        from mcp_server_langgraph.websocket.resilience import with_circuit_breaker

        mock_breaker = MagicMock()
        mock_breaker.call_async = AsyncMock(side_effect=pybreaker.CircuitBreakerError())

        with patch(
            "mcp_server_langgraph.websocket.resilience.get_circuit_breaker",
            return_value=mock_breaker,
        ):
            with patch(
                "mcp_server_langgraph.websocket.resilience.logger"
            ) as mock_logger:
                async_op = AsyncMock()()
                await with_circuit_breaker(
                    "my_service", async_op, fallback="default"
                )

                mock_logger.warning.assert_called_once()
                call_args = mock_logger.warning.call_args
                assert "my_service" in str(call_args)


@pytest.mark.unit
@pytest.mark.websocket
@pytest.mark.xdist_group(name="websocket_resilience")
class TestGetCircuitBreakerState:
    """Test suite for get_circuit_breaker_state function."""

    def teardown_method(self) -> None:
        """Force GC to prevent mock accumulation in xdist workers."""
        gc.collect()

    def test_returns_closed_state(self) -> None:
        """Test returns CLOSED when circuit is closed."""
        from mcp_server_langgraph.websocket.resilience import get_circuit_breaker_state

        mock_breaker = MagicMock()
        mock_breaker.current_state = pybreaker.STATE_CLOSED

        with patch(
            "mcp_server_langgraph.websocket.resilience.get_circuit_breaker",
            return_value=mock_breaker,
        ):
            state = get_circuit_breaker_state("test_service")

        assert state == CircuitBreakerState.CLOSED

    def test_returns_open_state(self) -> None:
        """Test returns OPEN when circuit is open."""
        from mcp_server_langgraph.websocket.resilience import get_circuit_breaker_state

        mock_breaker = MagicMock()
        mock_breaker.current_state = pybreaker.STATE_OPEN

        with patch(
            "mcp_server_langgraph.websocket.resilience.get_circuit_breaker",
            return_value=mock_breaker,
        ):
            state = get_circuit_breaker_state("test_service")

        assert state == CircuitBreakerState.OPEN

    def test_returns_half_open_state(self) -> None:
        """Test returns HALF_OPEN when circuit is half-open."""
        from mcp_server_langgraph.websocket.resilience import get_circuit_breaker_state

        mock_breaker = MagicMock()
        mock_breaker.current_state = pybreaker.STATE_HALF_OPEN

        with patch(
            "mcp_server_langgraph.websocket.resilience.get_circuit_breaker",
            return_value=mock_breaker,
        ):
            state = get_circuit_breaker_state("test_service")

        assert state == CircuitBreakerState.HALF_OPEN


@pytest.mark.unit
@pytest.mark.websocket
@pytest.mark.xdist_group(name="websocket_resilience")
class TestIsCircuitOpen:
    """Test suite for is_circuit_open function."""

    def teardown_method(self) -> None:
        """Force GC to prevent mock accumulation in xdist workers."""
        gc.collect()

    def test_returns_true_when_open(self) -> None:
        """Test returns True when circuit is open."""
        from mcp_server_langgraph.websocket.resilience import is_circuit_open

        mock_breaker = MagicMock()
        mock_breaker.current_state = pybreaker.STATE_OPEN

        with patch(
            "mcp_server_langgraph.websocket.resilience.get_circuit_breaker",
            return_value=mock_breaker,
        ):
            result = is_circuit_open("test_service")

        assert result is True

    def test_returns_false_when_closed(self) -> None:
        """Test returns False when circuit is closed."""
        from mcp_server_langgraph.websocket.resilience import is_circuit_open

        mock_breaker = MagicMock()
        mock_breaker.current_state = pybreaker.STATE_CLOSED

        with patch(
            "mcp_server_langgraph.websocket.resilience.get_circuit_breaker",
            return_value=mock_breaker,
        ):
            result = is_circuit_open("test_service")

        assert result is False

    def test_returns_false_when_half_open(self) -> None:
        """Test returns False when circuit is half-open."""
        from mcp_server_langgraph.websocket.resilience import is_circuit_open

        mock_breaker = MagicMock()
        mock_breaker.current_state = pybreaker.STATE_HALF_OPEN

        with patch(
            "mcp_server_langgraph.websocket.resilience.get_circuit_breaker",
            return_value=mock_breaker,
        ):
            result = is_circuit_open("test_service")

        assert result is False


@pytest.mark.unit
@pytest.mark.websocket
@pytest.mark.xdist_group(name="websocket_resilience")
class TestWebSocketServices:
    """Test suite for WebSocketServices constants."""

    def teardown_method(self) -> None:
        """Force GC to prevent mock accumulation in xdist workers."""
        gc.collect()

    def test_redis_service_name(self) -> None:
        """Test REDIS service name constant."""
        from mcp_server_langgraph.websocket.resilience import WebSocketServices

        assert WebSocketServices.REDIS == "websocket_redis"

    def test_openfga_service_name(self) -> None:
        """Test OPENFGA service name constant."""
        from mcp_server_langgraph.websocket.resilience import WebSocketServices

        assert WebSocketServices.OPENFGA == "websocket_openfga"

    def test_database_service_name(self) -> None:
        """Test DATABASE service name constant."""
        from mcp_server_langgraph.websocket.resilience import WebSocketServices

        assert WebSocketServices.DATABASE == "websocket_database"

    def test_metrics_service_name(self) -> None:
        """Test METRICS_SERVICE service name constant."""
        from mcp_server_langgraph.websocket.resilience import WebSocketServices

        assert WebSocketServices.METRICS_SERVICE == "websocket_metrics"

    def test_cost_service_name(self) -> None:
        """Test COST_SERVICE service name constant."""
        from mcp_server_langgraph.websocket.resilience import WebSocketServices

        assert WebSocketServices.COST_SERVICE == "websocket_cost"

    def test_notifications_service_name(self) -> None:
        """Test NOTIFICATIONS service name constant."""
        from mcp_server_langgraph.websocket.resilience import WebSocketServices

        assert WebSocketServices.NOTIFICATIONS == "websocket_notifications"
