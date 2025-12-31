"""
Alert WebSocket Handler Tests.

TDD tests for the Alert WebSocket using the standardized WebSocketBase.
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
    ws.accept = AsyncMock()  # noqa: async-mock-config
    ws.close = AsyncMock()  # noqa: async-mock-config
    ws.send_json = AsyncMock()  # noqa: async-mock-config
    ws.send_text = AsyncMock()  # noqa: async-mock-config
    ws.receive_json = AsyncMock()  # noqa: async-mock-config
    ws.receive_text = AsyncMock()  # noqa: async-mock-config
    ws.query_params = {}
    ws.headers = {}
    ws.client_state = MagicMock()
    return ws


@pytest.fixture
def mock_alert_broadcaster() -> MagicMock:
    """Create a mock alert broadcaster."""
    broadcaster = MagicMock()
    broadcaster.subscribe = AsyncMock()  # noqa: async-mock-config
    broadcaster.unsubscribe = AsyncMock()  # noqa: async-mock-config
    broadcaster.broadcast = AsyncMock()  # noqa: async-mock-config
    return broadcaster


@pytest.mark.xdist_group(name="alert_ws")
class TestAlertHandler:
    """Test Alert WebSocket using WebSocketBase."""

    def teardown_method(self) -> None:
        """Force GC to prevent mock accumulation in xdist workers."""
        gc.collect()

    @pytest.mark.asyncio
    async def test_handler_extends_websocket_base(self) -> None:
        """
        GIVEN the AlertHandler class
        WHEN checking its base classes
        THEN it should extend WebSocketBase.
        """
        from mcp_server_langgraph.websocket.base import WebSocketBase
        from mcp_server_langgraph.websocket.handlers.alert import (
            AlertHandler,
        )

        assert issubclass(AlertHandler, WebSocketBase)

    @pytest.mark.asyncio
    async def test_handles_subscribe_message(self, mock_websocket: MagicMock, mock_alert_broadcaster: MagicMock) -> None:
        """
        GIVEN an active admin connection
        WHEN a subscribe message is received
        THEN subscription should be confirmed.
        """
        from mcp_server_langgraph.websocket.handlers.alert import (
            AlertHandler,
        )

        handler = AlertHandler(
            config=WebSocketConfig(require_auth=False, endpoint_name="alerts"),
            broadcaster=mock_alert_broadcaster,
        )

        message = MessageEnvelope(
            type="subscribe",
            payload={},
        )

        response = await handler.handle_message(message)

        assert response is not None
        assert response.type == "subscribed"

    @pytest.mark.asyncio
    async def test_handles_unsubscribe_message(self, mock_websocket: MagicMock, mock_alert_broadcaster: MagicMock) -> None:
        """
        GIVEN an active subscription
        WHEN an unsubscribe message is received
        THEN unsubscription should be confirmed.
        """
        from mcp_server_langgraph.websocket.handlers.alert import (
            AlertHandler,
        )

        handler = AlertHandler(
            config=WebSocketConfig(require_auth=False, endpoint_name="alerts"),
            broadcaster=mock_alert_broadcaster,
        )
        handler._subscribed = True

        message = MessageEnvelope(
            type="unsubscribe",
            payload={},
        )

        response = await handler.handle_message(message)

        assert response is not None
        assert response.type == "unsubscribed"
        assert handler._subscribed is False

    @pytest.mark.asyncio
    async def test_handles_get_recent_message(self, mock_websocket: MagicMock, mock_alert_broadcaster: MagicMock) -> None:
        """
        GIVEN an active connection
        WHEN a get_recent message is received
        THEN recent alerts should be returned.
        """
        from mcp_server_langgraph.websocket.handlers.alert import (
            AlertHandler,
        )

        mock_alert_broadcaster.get_recent_alerts = AsyncMock(
            return_value=[
                {"alert_id": "alert-1", "severity": "critical"},
                {"alert_id": "alert-2", "severity": "warning"},
            ]
        )

        handler = AlertHandler(
            config=WebSocketConfig(require_auth=False, endpoint_name="alerts"),
            broadcaster=mock_alert_broadcaster,
        )

        message = MessageEnvelope(
            type="get_recent",
            payload={"limit": 10},
        )

        response = await handler.handle_message(message)

        assert response is not None
        assert response.type == "recent_alerts"
        assert response.payload is not None
        assert "alerts" in response.payload

    @pytest.mark.asyncio
    async def test_returns_error_for_unknown_message(
        self, mock_websocket: MagicMock, mock_alert_broadcaster: MagicMock
    ) -> None:
        """
        GIVEN an active connection
        WHEN an unknown message type is received
        THEN an error response should be returned.
        """
        from mcp_server_langgraph.websocket.handlers.alert import (
            AlertHandler,
        )

        handler = AlertHandler(
            config=WebSocketConfig(require_auth=False, endpoint_name="alerts"),
            broadcaster=mock_alert_broadcaster,
        )

        message = MessageEnvelope(
            type="unknown_type",
            payload={},
        )

        response = await handler.handle_message(message)

        assert response is not None
        assert response.type == "error"

    @pytest.mark.asyncio
    async def test_push_alert(self, mock_websocket: MagicMock, mock_alert_broadcaster: MagicMock) -> None:
        """
        GIVEN an active subscription
        WHEN push_alert is called
        THEN alert should be sent to client.
        """
        from mcp_server_langgraph.websocket.handlers.alert import (
            AlertHandler,
        )

        handler = AlertHandler(
            config=WebSocketConfig(require_auth=False, endpoint_name="alerts"),
            broadcaster=mock_alert_broadcaster,
        )
        handler._websocket = mock_websocket
        handler._subscribed = True

        await handler.push_alert(
            {
                "alert_id": "alert-1",
                "name": "High CPU",
                "severity": "critical",
                "state": "firing",
                "message": "CPU usage above 90%",
            }
        )

        mock_websocket.send_json.assert_called_once()
        call_args = mock_websocket.send_json.call_args[0][0]
        assert call_args["type"] == "alert"
        assert call_args["payload"]["alert_id"] == "alert-1"

    @pytest.mark.asyncio
    async def test_push_alert_not_sent_when_unsubscribed(
        self, mock_websocket: MagicMock, mock_alert_broadcaster: MagicMock
    ) -> None:
        """
        GIVEN a connection that is not subscribed
        WHEN push_alert is called
        THEN alert should not be sent.
        """
        from mcp_server_langgraph.websocket.handlers.alert import (
            AlertHandler,
        )

        handler = AlertHandler(
            config=WebSocketConfig(require_auth=False, endpoint_name="alerts"),
            broadcaster=mock_alert_broadcaster,
        )
        handler._websocket = mock_websocket
        handler._subscribed = False

        await handler.push_alert(
            {
                "alert_id": "alert-1",
                "severity": "critical",
            }
        )

        mock_websocket.send_json.assert_not_called()
