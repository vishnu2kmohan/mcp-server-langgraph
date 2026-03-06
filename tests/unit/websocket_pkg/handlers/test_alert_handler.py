"""
Unit tests for Alert WebSocket Handler.

Tests the AlertHandler class for real-time alert streaming.
"""

from __future__ import annotations

import gc
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

pytestmark = [
    pytest.mark.unit,
    pytest.mark.websocket,
    pytest.mark.xdist_group(name="websocket_alert_handler"),
]

RATE_LIMITER_PATCH = "mcp_server_langgraph.websocket.rate_limiter.get_websocket_rate_limiter"


class TestAlertHandlerInit:
    """Tests for AlertHandler initialization."""

    def teardown_method(self) -> None:
        """Force GC to prevent mock accumulation in xdist workers."""
        gc.collect()

    def test_init_stores_broadcaster(self) -> None:
        """GIVEN broadcaster WHEN creating handler THEN stores broadcaster."""
        from mcp_server_langgraph.websocket.handlers.alert import AlertHandler
        from mcp_server_langgraph.websocket.types import WebSocketConfig

        config = WebSocketConfig(endpoint_name="alerts")
        mock_broadcaster = MagicMock()

        with patch(RATE_LIMITER_PATCH, return_value=MagicMock()):
            handler = AlertHandler(config=config, broadcaster=mock_broadcaster)

        assert handler._broadcaster is mock_broadcaster
        assert handler._subscribed is False
        assert handler.user_id is None

    def test_init_with_metrics(self) -> None:
        """GIVEN metrics WHEN creating handler THEN stores metrics."""
        from mcp_server_langgraph.websocket.handlers.alert import AlertHandler
        from mcp_server_langgraph.websocket.types import WebSocketConfig

        config = WebSocketConfig(endpoint_name="alerts")
        mock_broadcaster = MagicMock()
        mock_metrics = MagicMock()

        with patch(RATE_LIMITER_PATCH, return_value=MagicMock()):
            handler = AlertHandler(config=config, broadcaster=mock_broadcaster, metrics=mock_metrics)

        assert handler._metrics is mock_metrics


class TestAlertHandlerLifecycle:
    """Tests for AlertHandler lifecycle hooks."""

    def teardown_method(self) -> None:
        """Force GC to prevent mock accumulation in xdist workers."""
        gc.collect()

    @pytest.mark.asyncio
    async def test_on_connect_stores_user_id(self) -> None:
        """GIVEN user WHEN on_connect called THEN stores user_id."""
        from mcp_server_langgraph.websocket.handlers.alert import AlertHandler
        from mcp_server_langgraph.websocket.types import AuthUser, WebSocketConfig

        config = WebSocketConfig(endpoint_name="alerts")
        mock_broadcaster = MagicMock()

        with patch(RATE_LIMITER_PATCH, return_value=MagicMock()):
            handler = AlertHandler(config=config, broadcaster=mock_broadcaster)

        user = AuthUser(id="user-123", username="testuser")
        handler._user = user  # Base class sets this before calling on_connect

        await handler.on_connect(user)

        assert handler.user_id == "user-123"

    @pytest.mark.asyncio
    async def test_on_disconnect_unsubscribes(self) -> None:
        """GIVEN subscribed handler WHEN on_disconnect called THEN unsubscribes."""
        from mcp_server_langgraph.websocket.handlers.alert import AlertHandler
        from mcp_server_langgraph.websocket.types import AuthUser, WebSocketConfig

        config = WebSocketConfig(endpoint_name="alerts")
        mock_broadcaster = AsyncMock(return_value=None)  # noqa: async-mock-config

        with patch(RATE_LIMITER_PATCH, return_value=MagicMock()):
            handler = AlertHandler(config=config, broadcaster=mock_broadcaster)

        mock_ws = AsyncMock(return_value=None)  # noqa: async-mock-config
        handler._websocket = mock_ws
        handler._subscribed = True
        handler._user = AuthUser(id="user-123", username="user-123")

        await handler.on_disconnect()

        mock_broadcaster.unsubscribe.assert_called_once_with(mock_ws)
        assert handler._subscribed is False

    @pytest.mark.asyncio
    async def test_on_disconnect_without_subscription(self) -> None:
        """GIVEN not subscribed WHEN on_disconnect called THEN does not unsubscribe."""
        from mcp_server_langgraph.websocket.handlers.alert import AlertHandler
        from mcp_server_langgraph.websocket.types import WebSocketConfig

        config = WebSocketConfig(endpoint_name="alerts")
        mock_broadcaster = AsyncMock(return_value=None)  # noqa: async-mock-config

        with patch(RATE_LIMITER_PATCH, return_value=MagicMock()):
            handler = AlertHandler(config=config, broadcaster=mock_broadcaster)

        handler._subscribed = False

        await handler.on_disconnect()

        mock_broadcaster.unsubscribe.assert_not_called()


class TestAlertHandlerMessages:
    """Tests for AlertHandler message handling."""

    def teardown_method(self) -> None:
        """Force GC to prevent mock accumulation in xdist workers."""
        gc.collect()

    @pytest.mark.asyncio
    async def test_handle_subscribe(self) -> None:
        """GIVEN subscribe message WHEN handle_message called THEN subscribes."""
        from mcp_server_langgraph.websocket.handlers.alert import AlertHandler
        from mcp_server_langgraph.websocket.types import AuthUser, MessageEnvelope, WebSocketConfig

        config = WebSocketConfig(endpoint_name="alerts")
        mock_broadcaster = AsyncMock(return_value=None)  # noqa: async-mock-config

        with patch(RATE_LIMITER_PATCH, return_value=MagicMock()):
            handler = AlertHandler(config=config, broadcaster=mock_broadcaster)

        mock_ws = AsyncMock(return_value=None)  # noqa: async-mock-config
        handler._websocket = mock_ws
        handler._user = AuthUser(id="user-123", username="user-123")

        message = MessageEnvelope(type="subscribe", id="msg-1")
        response = await handler.handle_message(message)

        assert response is not None
        assert response.type == "subscribed"
        assert response.id == "msg-1"
        mock_broadcaster.subscribe.assert_called_once_with(mock_ws, user_id="user-123")
        assert handler._subscribed is True

    @pytest.mark.asyncio
    async def test_handle_subscribe_already_subscribed(self) -> None:
        """GIVEN already subscribed WHEN subscribe again THEN does not re-subscribe."""
        from mcp_server_langgraph.websocket.handlers.alert import AlertHandler
        from mcp_server_langgraph.websocket.types import AuthUser, MessageEnvelope, WebSocketConfig

        config = WebSocketConfig(endpoint_name="alerts")
        mock_broadcaster = AsyncMock(return_value=None)  # noqa: async-mock-config

        with patch(RATE_LIMITER_PATCH, return_value=MagicMock()):
            handler = AlertHandler(config=config, broadcaster=mock_broadcaster)

        mock_ws = AsyncMock(return_value=None)  # noqa: async-mock-config
        handler._websocket = mock_ws
        handler._subscribed = True  # Already subscribed
        handler._user = AuthUser(id="user-123", username="user-123")

        message = MessageEnvelope(type="subscribe", id="msg-1")
        response = await handler.handle_message(message)

        assert response is not None
        assert response.type == "subscribed"
        mock_broadcaster.subscribe.assert_not_called()

    @pytest.mark.asyncio
    async def test_handle_unsubscribe(self) -> None:
        """GIVEN subscribed WHEN unsubscribe message THEN unsubscribes."""
        from mcp_server_langgraph.websocket.handlers.alert import AlertHandler
        from mcp_server_langgraph.websocket.types import MessageEnvelope, WebSocketConfig

        config = WebSocketConfig(endpoint_name="alerts")
        mock_broadcaster = AsyncMock(return_value=None)  # noqa: async-mock-config

        with patch(RATE_LIMITER_PATCH, return_value=MagicMock()):
            handler = AlertHandler(config=config, broadcaster=mock_broadcaster)

        mock_ws = AsyncMock(return_value=None)  # noqa: async-mock-config
        handler._websocket = mock_ws
        handler._subscribed = True

        message = MessageEnvelope(type="unsubscribe", id="msg-2")
        response = await handler.handle_message(message)

        assert response is not None
        assert response.type == "unsubscribed"
        assert response.id == "msg-2"
        mock_broadcaster.unsubscribe.assert_called_once_with(mock_ws)
        assert handler._subscribed is False

    @pytest.mark.asyncio
    async def test_handle_unsubscribe_not_subscribed(self) -> None:
        """GIVEN not subscribed WHEN unsubscribe message THEN returns unsubscribed."""
        from mcp_server_langgraph.websocket.handlers.alert import AlertHandler
        from mcp_server_langgraph.websocket.types import MessageEnvelope, WebSocketConfig

        config = WebSocketConfig(endpoint_name="alerts")
        mock_broadcaster = AsyncMock(return_value=None)  # noqa: async-mock-config

        with patch(RATE_LIMITER_PATCH, return_value=MagicMock()):
            handler = AlertHandler(config=config, broadcaster=mock_broadcaster)

        handler._subscribed = False

        message = MessageEnvelope(type="unsubscribe", id="msg-2")
        response = await handler.handle_message(message)

        assert response is not None
        assert response.type == "unsubscribed"
        mock_broadcaster.unsubscribe.assert_not_called()

    @pytest.mark.asyncio
    async def test_handle_get_recent(self) -> None:
        """GIVEN get_recent message WHEN handle_message called THEN returns alerts."""
        from mcp_server_langgraph.websocket.handlers.alert import AlertHandler
        from mcp_server_langgraph.websocket.types import MessageEnvelope, WebSocketConfig

        config = WebSocketConfig(endpoint_name="alerts")
        mock_broadcaster = AsyncMock(return_value=None)  # noqa: async-mock-config
        mock_broadcaster.get_recent_alerts.return_value = [
            {"id": "alert-1", "message": "Test alert"},
            {"id": "alert-2", "message": "Another alert"},
        ]

        with patch(RATE_LIMITER_PATCH, return_value=MagicMock()):
            handler = AlertHandler(config=config, broadcaster=mock_broadcaster)

        message = MessageEnvelope(type="get_recent", id="msg-3", payload={"limit": 5})
        response = await handler.handle_message(message)

        assert response is not None
        assert response.type == "recent_alerts"
        assert response.id == "msg-3"
        assert response.payload["count"] == 2
        assert len(response.payload["alerts"]) == 2
        mock_broadcaster.get_recent_alerts.assert_called_once_with(limit=5)

    @pytest.mark.asyncio
    async def test_handle_get_recent_default_limit(self) -> None:
        """GIVEN get_recent without limit WHEN handle_message called THEN uses default limit."""
        from mcp_server_langgraph.websocket.handlers.alert import AlertHandler
        from mcp_server_langgraph.websocket.types import MessageEnvelope, WebSocketConfig

        config = WebSocketConfig(endpoint_name="alerts")
        mock_broadcaster = AsyncMock(return_value=None)  # noqa: async-mock-config
        mock_broadcaster.get_recent_alerts.return_value = []

        with patch(RATE_LIMITER_PATCH, return_value=MagicMock()):
            handler = AlertHandler(config=config, broadcaster=mock_broadcaster)

        message = MessageEnvelope(type="get_recent", id="msg-4")
        response = await handler.handle_message(message)

        assert response is not None
        assert response.type == "recent_alerts"
        mock_broadcaster.get_recent_alerts.assert_called_once_with(limit=10)

    @pytest.mark.asyncio
    async def test_handle_get_recent_error(self) -> None:
        """GIVEN error getting alerts WHEN handle_message called THEN returns error."""
        from mcp_server_langgraph.websocket.handlers.alert import AlertHandler
        from mcp_server_langgraph.websocket.types import MessageEnvelope, WebSocketConfig

        config = WebSocketConfig(endpoint_name="alerts")
        mock_broadcaster = AsyncMock(return_value=None)  # noqa: async-mock-config
        mock_broadcaster.get_recent_alerts.side_effect = Exception("Database error")

        with patch(RATE_LIMITER_PATCH, return_value=MagicMock()):
            handler = AlertHandler(config=config, broadcaster=mock_broadcaster)

        message = MessageEnvelope(type="get_recent", id="msg-5")
        response = await handler.handle_message(message)

        assert response is not None
        assert response.type == "error"
        assert response.id == "msg-5"
        assert response.payload["code"] == "get_recent_failed"

    @pytest.mark.asyncio
    async def test_handle_unknown_message_type(self) -> None:
        """GIVEN unknown message type WHEN handle_message called THEN returns error."""
        from mcp_server_langgraph.websocket.handlers.alert import AlertHandler
        from mcp_server_langgraph.websocket.types import MessageEnvelope, WebSocketConfig

        config = WebSocketConfig(endpoint_name="alerts")
        mock_broadcaster = AsyncMock(return_value=None)  # noqa: async-mock-config

        with patch(RATE_LIMITER_PATCH, return_value=MagicMock()):
            handler = AlertHandler(config=config, broadcaster=mock_broadcaster)

        message = MessageEnvelope(type="unknown_type", id="msg-6")
        response = await handler.handle_message(message)

        assert response is not None
        assert response.type == "error"
        assert response.id == "msg-6"
        assert response.payload["code"] == "unknown_message_type"


class TestAlertHandlerPush:
    """Tests for AlertHandler push functionality."""

    def teardown_method(self) -> None:
        """Force GC to prevent mock accumulation in xdist workers."""
        gc.collect()

    @pytest.mark.asyncio
    async def test_push_alert_when_subscribed(self) -> None:
        """GIVEN subscribed WHEN push_alert called THEN sends alert."""
        from mcp_server_langgraph.websocket.handlers.alert import AlertHandler
        from mcp_server_langgraph.websocket.types import WebSocketConfig

        config = WebSocketConfig(endpoint_name="alerts")
        mock_broadcaster = AsyncMock(return_value=None)  # noqa: async-mock-config

        with patch(RATE_LIMITER_PATCH, return_value=MagicMock()):
            handler = AlertHandler(config=config, broadcaster=mock_broadcaster)

        mock_ws = AsyncMock(return_value=None)  # noqa: async-mock-config
        handler._websocket = mock_ws
        handler._subscribed = True

        alert = {"id": "alert-1", "severity": "critical", "message": "Test alert"}
        await handler.push_alert(alert)

        mock_ws.send_json.assert_called_once()
        sent_data = mock_ws.send_json.call_args[0][0]
        assert sent_data["type"] == "alert"
        assert sent_data["payload"] == alert

    @pytest.mark.asyncio
    async def test_push_alert_when_not_subscribed(self) -> None:
        """GIVEN not subscribed WHEN push_alert called THEN does not send."""
        from mcp_server_langgraph.websocket.handlers.alert import AlertHandler
        from mcp_server_langgraph.websocket.types import WebSocketConfig

        config = WebSocketConfig(endpoint_name="alerts")
        mock_broadcaster = AsyncMock(return_value=None)  # noqa: async-mock-config

        with patch(RATE_LIMITER_PATCH, return_value=MagicMock()):
            handler = AlertHandler(config=config, broadcaster=mock_broadcaster)

        mock_ws = AsyncMock(return_value=None)  # noqa: async-mock-config
        handler._websocket = mock_ws
        handler._subscribed = False

        alert = {"id": "alert-1", "message": "Test"}
        await handler.push_alert(alert)

        mock_ws.send_json.assert_not_called()

    @pytest.mark.asyncio
    async def test_push_alert_no_websocket(self) -> None:
        """GIVEN no websocket WHEN push_alert called THEN does not send."""
        from mcp_server_langgraph.websocket.handlers.alert import AlertHandler
        from mcp_server_langgraph.websocket.types import WebSocketConfig

        config = WebSocketConfig(endpoint_name="alerts")
        mock_broadcaster = AsyncMock(return_value=None)  # noqa: async-mock-config

        with patch(RATE_LIMITER_PATCH, return_value=MagicMock()):
            handler = AlertHandler(config=config, broadcaster=mock_broadcaster)

        handler._subscribed = True
        # No websocket set

        alert = {"id": "alert-1", "message": "Test"}
        await handler.push_alert(alert)

        # Should not raise, just silently skip
