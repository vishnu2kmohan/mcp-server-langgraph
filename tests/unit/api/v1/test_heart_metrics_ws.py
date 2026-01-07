"""
Unit tests for HEART Metrics WebSocket endpoint.

Tests the heart_metrics_ws.py endpoint which provides
real-time HEART metrics streaming replacing polling.

TDD: RED phase - tests written before implementation.
"""

import gc
from unittest.mock import AsyncMock, patch

import pytest

pytestmark = [
    pytest.mark.unit,
    pytest.mark.websocket,
    pytest.mark.api,
    pytest.mark.xdist_group(name="heart_metrics_ws"),
]


@pytest.mark.xdist_group(name="heart_metrics_ws")
class TestHeartMetricsWebSocketHandler:
    """Tests for HeartMetricsWebSocketHandler class."""

    def teardown_method(self) -> None:
        """Force GC to prevent mock accumulation in xdist workers."""
        gc.collect()

    def test_handler_class_exists_on_import(self) -> None:
        """GIVEN the module WHEN importing THEN handler class exists."""
        from mcp_server_langgraph.api.v1.heart_metrics_ws import (
            HeartMetricsWebSocketHandler,
        )

        assert HeartMetricsWebSocketHandler is not None

    def test_handler_extends_websocket_base(self) -> None:
        """GIVEN handler WHEN checking inheritance THEN extends WebSocketBase."""
        from mcp_server_langgraph.api.v1.heart_metrics_ws import (
            HeartMetricsWebSocketHandler,
        )
        from mcp_server_langgraph.websocket.base import WebSocketBase

        assert issubclass(HeartMetricsWebSocketHandler, WebSocketBase)

    def test_handler_config_has_correct_endpoint_name(self) -> None:
        """GIVEN handler WHEN checking config THEN endpoint name is correct."""
        from mcp_server_langgraph.api.v1.heart_metrics_ws import (
            HeartMetricsWebSocketHandler,
        )

        handler = HeartMetricsWebSocketHandler()
        assert handler.config.endpoint_name == "heart-metrics"

    def test_handler_requires_auth(self) -> None:
        """GIVEN handler WHEN checking config THEN auth is required."""
        from mcp_server_langgraph.api.v1.heart_metrics_ws import (
            HeartMetricsWebSocketHandler,
        )

        handler = HeartMetricsWebSocketHandler()
        assert handler.config.require_auth is True


@pytest.mark.xdist_group(name="heart_metrics_ws")
class TestHeartMetricsMessageHandling:
    """Tests for message handling in HeartMetricsWebSocketHandler."""

    def teardown_method(self) -> None:
        """Force GC to prevent mock accumulation in xdist workers."""
        gc.collect()

    @pytest.mark.asyncio
    async def test_get_snapshot_returns_metrics(self) -> None:
        """GIVEN get_snapshot message WHEN handling THEN returns metrics snapshot."""
        from mcp_server_langgraph.api.v1.heart_metrics_ws import (
            HeartMetricsWebSocketHandler,
        )
        from mcp_server_langgraph.websocket.types import MessageEnvelope

        handler = HeartMetricsWebSocketHandler()

        message = MessageEnvelope(
            type="get_snapshot",
            payload={"time_range": "24h"},
        )

        response = await handler.handle_message(message)

        assert response is not None
        assert response.type == "metrics_snapshot"
        assert "snapshot" in response.payload

    @pytest.mark.asyncio
    async def test_set_time_range_updates_range(self) -> None:
        """GIVEN set_time_range message WHEN handling THEN updates range."""
        from mcp_server_langgraph.api.v1.heart_metrics_ws import (
            HeartMetricsWebSocketHandler,
        )
        from mcp_server_langgraph.websocket.types import MessageEnvelope

        handler = HeartMetricsWebSocketHandler()

        message = MessageEnvelope(
            type="set_time_range",
            payload={"time_range": "7d"},
        )

        response = await handler.handle_message(message)

        assert response is not None
        assert response.type == "time_range_updated"
        assert response.payload["time_range"] == "7d"

    @pytest.mark.asyncio
    async def test_subscribe_dimension_returns_confirmation(self) -> None:
        """GIVEN subscribe_dimension message WHEN handling THEN confirms."""
        from mcp_server_langgraph.api.v1.heart_metrics_ws import (
            HeartMetricsWebSocketHandler,
        )
        from mcp_server_langgraph.websocket.types import MessageEnvelope

        handler = HeartMetricsWebSocketHandler()

        message = MessageEnvelope(
            type="subscribe_dimension",
            payload={"dimension": "happiness"},
        )

        response = await handler.handle_message(message)

        assert response is not None
        assert response.type == "subscribed"
        assert response.payload["dimension"] == "happiness"

    @pytest.mark.asyncio
    async def test_unsubscribe_dimension_returns_confirmation(self) -> None:
        """GIVEN unsubscribe_dimension message WHEN handling THEN confirms."""
        from mcp_server_langgraph.api.v1.heart_metrics_ws import (
            HeartMetricsWebSocketHandler,
        )
        from mcp_server_langgraph.websocket.types import MessageEnvelope

        handler = HeartMetricsWebSocketHandler()

        message = MessageEnvelope(
            type="unsubscribe_dimension",
            payload={"dimension": "happiness"},
        )

        response = await handler.handle_message(message)

        assert response is not None
        assert response.type == "unsubscribed"
        assert response.payload["dimension"] == "happiness"


@pytest.mark.xdist_group(name="heart_metrics_ws")
class TestHeartMetricsRouter:
    """Tests for the router endpoint."""

    def teardown_method(self) -> None:
        """Force GC to prevent mock accumulation in xdist workers."""
        gc.collect()

    def test_router_exists_on_import(self) -> None:
        """GIVEN the module WHEN importing THEN router exists."""
        from mcp_server_langgraph.api.v1.heart_metrics_ws import router

        assert router is not None

    def test_router_has_websocket_route(self) -> None:
        """GIVEN router WHEN checking routes THEN has websocket route."""
        from mcp_server_langgraph.api.v1.heart_metrics_ws import router

        routes = router.routes
        assert len(routes) > 0


@pytest.mark.xdist_group(name="heart_metrics_ws")
class TestHeartMetricsServiceIntegration:
    """Tests for HeartMetricsServiceAdapter integration."""

    def teardown_method(self) -> None:
        """Force GC to prevent mock accumulation in xdist workers."""
        gc.collect()

    @pytest.mark.asyncio
    async def test_get_snapshot_uses_service_adapter(self) -> None:
        """GIVEN handler WHEN get_snapshot THEN uses HeartMetricsServiceAdapter.

        TDD: This test verifies the handler delegates to the actual service
        rather than using inline mock data.
        """
        from mcp_server_langgraph.api.v1.heart_metrics_ws import (
            HeartMetricsWebSocketHandler,
        )
        from mcp_server_langgraph.websocket.types import MessageEnvelope

        # Mock the service to verify it's called
        mock_snapshot = {
            "happiness": {"score": 99, "trend": "up", "change": 1.0},
            "engagement": {"score": 88, "trend": "stable", "change": 0.0},
            "adoption": {"score": 77, "trend": "down", "change": -1.0},
            "retention": {"score": 66, "trend": "stable", "change": 0.0},
            "task_success": {"score": 55, "trend": "up", "change": 2.0},
            "time_range": "24h",
            "last_updated": "2025-01-01T00:00:00Z",
        }

        with patch("mcp_server_langgraph.api.v1.heart_metrics_ws.get_websocket_heart_metrics_service") as mock_get_service:
            mock_service = AsyncMock()
            mock_service.get_current_snapshot.return_value = mock_snapshot
            mock_get_service.return_value = mock_service

            handler = HeartMetricsWebSocketHandler()

            message = MessageEnvelope(
                type="get_snapshot",
                payload={"time_range": "24h"},
            )

            response = await handler.handle_message(message)

            # Verify service was called
            mock_service.get_current_snapshot.assert_called_once_with("24h")

            # Verify response uses service data
            assert response is not None
            assert response.type == "metrics_snapshot"
            assert response.payload["snapshot"]["happiness"]["score"] == 99

    @pytest.mark.asyncio
    async def test_handler_initializes_with_service(self) -> None:
        """GIVEN handler WHEN initialized THEN has service attribute."""
        from mcp_server_langgraph.api.v1.heart_metrics_ws import (
            HeartMetricsWebSocketHandler,
        )

        with patch("mcp_server_langgraph.api.v1.heart_metrics_ws.get_websocket_heart_metrics_service") as mock_get_service:
            mock_service = AsyncMock()  # noqa: async-mock-config
            mock_get_service.return_value = mock_service

            handler = HeartMetricsWebSocketHandler()

            # Verify handler has service reference
            assert hasattr(handler, "_metrics_service")
            assert handler._metrics_service is mock_service
