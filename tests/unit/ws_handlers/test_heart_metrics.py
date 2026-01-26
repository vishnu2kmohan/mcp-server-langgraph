"""
HEART Metrics WebSocket Handler Tests.

TDD tests for the HEART Metrics WebSocket using the standardized WebSocketBase.
"""

from __future__ import annotations

import gc
from unittest.mock import AsyncMock, MagicMock

import pytest

from mcp_server_langgraph.websocket import (
    MessageEnvelope,
    WebSocketConfig,
)

pytestmark = [pytest.mark.unit, pytest.mark.websocket]


@pytest.fixture
def mock_websocket() -> MagicMock:
    """Create a mock WebSocket for testing."""
    ws = MagicMock()
    ws.accept = AsyncMock(return_value=None)  # noqa: async-mock-config
    ws.close = AsyncMock(return_value=None)  # noqa: async-mock-config
    ws.send_json = AsyncMock(return_value=None)  # noqa: async-mock-config
    ws.send_text = AsyncMock(return_value=None)  # noqa: async-mock-config
    ws.receive_json = AsyncMock(return_value=None)  # noqa: async-mock-config
    ws.receive_text = AsyncMock(return_value=None)  # noqa: async-mock-config
    ws.query_params = {}
    ws.headers = {}
    ws.client_state = MagicMock()
    return ws


@pytest.fixture
def mock_metrics_service() -> MagicMock:
    """Create a mock HEART metrics service."""
    service = MagicMock()
    service.get_current_snapshot = AsyncMock(
        return_value={
            "happiness": {"score": 85, "trend": "up"},
            "engagement": {"score": 72, "trend": "stable"},
            "adoption": {"score": 90, "trend": "up"},
            "retention": {"score": 88, "trend": "stable"},
            "task_success": {"score": 95, "trend": "up"},
        }
    )
    service.get_dimension_metrics = AsyncMock(
        return_value={
            "score": 85,
            "trend": "up",
            "samples": 1000,
        }
    )
    return service


@pytest.mark.xdist_group(name="heart_metrics_ws")
class TestHeartMetricsHandler:
    """Test HEART Metrics WebSocket using WebSocketBase."""

    def teardown_method(self) -> None:
        """Force GC to prevent mock accumulation in xdist workers."""
        gc.collect()

    @pytest.mark.asyncio
    async def test_handler_extends_websocket_base(self) -> None:
        """
        GIVEN the HeartMetricsHandler class
        WHEN checking its base classes
        THEN it should extend WebSocketBase.
        """
        from mcp_server_langgraph.websocket.base import WebSocketBase
        from mcp_server_langgraph.websocket.handlers.heart_metrics import (
            HeartMetricsHandler,
        )

        assert issubclass(HeartMetricsHandler, WebSocketBase)

    @pytest.mark.asyncio
    async def test_sends_initial_snapshot_on_connect(self, mock_websocket: MagicMock, mock_metrics_service: MagicMock) -> None:
        """
        GIVEN a new WebSocket connection
        WHEN on_connect is called
        THEN the initial HEART metrics snapshot should be sent.
        """
        from mcp_server_langgraph.websocket.handlers.heart_metrics import (
            HeartMetricsHandler,
        )
        from mcp_server_langgraph.websocket.types import AuthUser

        handler = HeartMetricsHandler(
            config=WebSocketConfig(require_auth=True, endpoint_name="heart-metrics"),
            metrics_service=mock_metrics_service,
        )
        handler._websocket = mock_websocket

        user = AuthUser(id="test-user", username="test")
        await handler.on_connect(user)

        # Should have sent metrics_snapshot message
        mock_websocket.send_json.assert_called_once()
        call_args = mock_websocket.send_json.call_args[0][0]
        assert call_args["type"] == "metrics_snapshot"
        assert "metrics" in call_args

    @pytest.mark.asyncio
    async def test_handles_set_time_range(self, mock_websocket: MagicMock, mock_metrics_service: MagicMock) -> None:
        """
        GIVEN an active connection
        WHEN a set_time_range message is received
        THEN the time range should be updated and new snapshot sent.
        """
        from mcp_server_langgraph.websocket.handlers.heart_metrics import (
            HeartMetricsHandler,
        )

        handler = HeartMetricsHandler(
            config=WebSocketConfig(require_auth=True, endpoint_name="heart-metrics"),
            metrics_service=mock_metrics_service,
        )

        message = MessageEnvelope(
            type="set_time_range",
            payload={"time_range": "7d"},
        )

        response = await handler.handle_message(message)

        assert response is not None
        assert response.type == "metrics_snapshot"
        assert handler.time_range == "7d"

    @pytest.mark.asyncio
    async def test_handles_subscribe_dimension(self, mock_websocket: MagicMock, mock_metrics_service: MagicMock) -> None:
        """
        GIVEN an active connection
        WHEN a subscribe_dimension message is received
        THEN the client should be subscribed to that dimension.
        """
        from mcp_server_langgraph.websocket.handlers.heart_metrics import (
            HeartMetricsHandler,
        )

        handler = HeartMetricsHandler(
            config=WebSocketConfig(require_auth=True, endpoint_name="heart-metrics"),
            metrics_service=mock_metrics_service,
        )

        message = MessageEnvelope(
            type="subscribe_dimension",
            payload={"dimension": "happiness"},
        )

        response = await handler.handle_message(message)

        assert response is not None
        assert response.type == "dimension_update"
        assert "happiness" in handler.subscribed_dimensions

    @pytest.mark.asyncio
    async def test_handles_unsubscribe_dimension(self, mock_websocket: MagicMock, mock_metrics_service: MagicMock) -> None:
        """
        GIVEN an active connection with dimension subscriptions
        WHEN an unsubscribe_dimension message is received
        THEN the client should be unsubscribed from that dimension.
        """
        from mcp_server_langgraph.websocket.handlers.heart_metrics import (
            HeartMetricsHandler,
        )

        handler = HeartMetricsHandler(
            config=WebSocketConfig(require_auth=True, endpoint_name="heart-metrics"),
            metrics_service=mock_metrics_service,
        )
        handler.subscribed_dimensions.add("happiness")

        message = MessageEnvelope(
            type="unsubscribe_dimension",
            payload={"dimension": "happiness"},
        )

        response = await handler.handle_message(message)

        assert response is not None
        assert response.type == "unsubscribed"
        assert "happiness" not in handler.subscribed_dimensions
