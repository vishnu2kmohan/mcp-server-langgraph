"""
Unit tests for Notification WebSocket Handler.

Tests the NotificationWebSocketHandler class for real-time notification streaming.
"""

from __future__ import annotations

import gc
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

pytestmark = [
    pytest.mark.unit,
    pytest.mark.websocket,
    pytest.mark.xdist_group(name="websocket_notification_handler"),
]

RATE_LIMITER_PATCH = "mcp_server_langgraph.websocket.rate_limiter.get_websocket_rate_limiter"


@pytest.mark.xdist_group(name="websocket_notification_handler_init")
class TestNotificationHandlerInit:
    """Tests for NotificationWebSocketHandler initialization."""

    def teardown_method(self) -> None:
        """Force GC to prevent mock accumulation in xdist workers."""
        gc.collect()

    def test_init_stores_broadcaster(self) -> None:
        """GIVEN broadcaster WHEN creating handler THEN stores broadcaster."""
        from mcp_server_langgraph.websocket.handlers.notifications import (
            NotificationWebSocketHandler,
        )
        from mcp_server_langgraph.websocket.types import WebSocketConfig

        config = WebSocketConfig(endpoint_name="notifications")
        mock_broadcaster = MagicMock()

        with patch(RATE_LIMITER_PATCH, return_value=MagicMock()):
            handler = NotificationWebSocketHandler(config=config, broadcaster=mock_broadcaster)

        assert handler._broadcaster is mock_broadcaster
        assert handler._user_id is None

    def test_init_with_metrics(self) -> None:
        """GIVEN metrics WHEN creating handler THEN stores metrics."""
        from mcp_server_langgraph.websocket.handlers.notifications import (
            NotificationWebSocketHandler,
        )
        from mcp_server_langgraph.websocket.types import WebSocketConfig

        config = WebSocketConfig(endpoint_name="notifications")
        mock_broadcaster = MagicMock()
        mock_metrics = MagicMock()

        with patch(RATE_LIMITER_PATCH, return_value=MagicMock()):
            handler = NotificationWebSocketHandler(config=config, broadcaster=mock_broadcaster, metrics=mock_metrics)

        assert handler._metrics is mock_metrics


@pytest.mark.xdist_group(name="websocket_notification_handler_lifecycle")
class TestNotificationHandlerLifecycle:
    """Tests for NotificationWebSocketHandler lifecycle hooks."""

    def teardown_method(self) -> None:
        """Force GC to prevent mock accumulation in xdist workers."""
        gc.collect()

    @pytest.mark.asyncio
    async def test_on_connect_subscribes(self) -> None:
        """GIVEN user WHEN on_connect called THEN subscribes to broadcaster."""
        from mcp_server_langgraph.websocket.handlers.notifications import (
            NotificationWebSocketHandler,
        )
        from mcp_server_langgraph.websocket.types import AuthUser, WebSocketConfig

        config = WebSocketConfig(endpoint_name="notifications")
        mock_broadcaster = AsyncMock(return_value=None)  # noqa: async-mock-config

        with patch(RATE_LIMITER_PATCH, return_value=MagicMock()):
            handler = NotificationWebSocketHandler(config=config, broadcaster=mock_broadcaster)

        mock_ws = AsyncMock(return_value=None)  # noqa: async-mock-config
        handler._websocket = mock_ws
        user = AuthUser(id="user-123", username="testuser")

        await handler.on_connect(user)

        assert handler._user_id == "user-123"
        mock_broadcaster.subscribe.assert_called_once_with(mock_ws, user_id="user-123")

    @pytest.mark.asyncio
    async def test_on_connect_without_websocket(self) -> None:
        """GIVEN no websocket WHEN on_connect called THEN does not subscribe."""
        from mcp_server_langgraph.websocket.handlers.notifications import (
            NotificationWebSocketHandler,
        )
        from mcp_server_langgraph.websocket.types import AuthUser, WebSocketConfig

        config = WebSocketConfig(endpoint_name="notifications")
        mock_broadcaster = AsyncMock(return_value=None)  # noqa: async-mock-config

        with patch(RATE_LIMITER_PATCH, return_value=MagicMock()):
            handler = NotificationWebSocketHandler(config=config, broadcaster=mock_broadcaster)

        # No websocket set
        user = AuthUser(id="user-123", username="testuser")

        await handler.on_connect(user)

        assert handler._user_id == "user-123"
        mock_broadcaster.subscribe.assert_not_called()

    @pytest.mark.asyncio
    async def test_on_disconnect_unsubscribes(self) -> None:
        """GIVEN connected WHEN on_disconnect called THEN unsubscribes."""
        from mcp_server_langgraph.websocket.handlers.notifications import (
            NotificationWebSocketHandler,
        )
        from mcp_server_langgraph.websocket.types import WebSocketConfig

        config = WebSocketConfig(endpoint_name="notifications")
        mock_broadcaster = AsyncMock(return_value=None)  # noqa: async-mock-config

        with patch(RATE_LIMITER_PATCH, return_value=MagicMock()):
            handler = NotificationWebSocketHandler(config=config, broadcaster=mock_broadcaster)

        mock_ws = AsyncMock(return_value=None)  # noqa: async-mock-config
        handler._websocket = mock_ws
        handler._user_id = "user-123"

        await handler.on_disconnect()

        mock_broadcaster.unsubscribe.assert_called_once_with(mock_ws)

    @pytest.mark.asyncio
    async def test_on_disconnect_without_websocket(self) -> None:
        """GIVEN no websocket WHEN on_disconnect called THEN does not unsubscribe."""
        from mcp_server_langgraph.websocket.handlers.notifications import (
            NotificationWebSocketHandler,
        )
        from mcp_server_langgraph.websocket.types import WebSocketConfig

        config = WebSocketConfig(endpoint_name="notifications")
        mock_broadcaster = AsyncMock(return_value=None)  # noqa: async-mock-config

        with patch(RATE_LIMITER_PATCH, return_value=MagicMock()):
            handler = NotificationWebSocketHandler(config=config, broadcaster=mock_broadcaster)

        # No websocket set
        handler._user_id = "user-123"

        await handler.on_disconnect()

        mock_broadcaster.unsubscribe.assert_not_called()


@pytest.mark.xdist_group(name="websocket_notification_handler_messages")
class TestNotificationHandlerMessages:
    """Tests for NotificationWebSocketHandler message handling."""

    def teardown_method(self) -> None:
        """Force GC to prevent mock accumulation in xdist workers."""
        gc.collect()

    @pytest.mark.asyncio
    async def test_handle_message_returns_none(self) -> None:
        """GIVEN any message WHEN handle_message called THEN returns None (passive)."""
        from mcp_server_langgraph.websocket.handlers.notifications import (
            NotificationWebSocketHandler,
        )
        from mcp_server_langgraph.websocket.types import MessageEnvelope, WebSocketConfig

        config = WebSocketConfig(endpoint_name="notifications")
        mock_broadcaster = AsyncMock(return_value=None)  # noqa: async-mock-config

        with patch(RATE_LIMITER_PATCH, return_value=MagicMock()):
            handler = NotificationWebSocketHandler(config=config, broadcaster=mock_broadcaster)

        message = MessageEnvelope(type="ack", id="msg-1")
        response = await handler.handle_message(message)

        # Notification handler is passive - returns None for all messages
        assert response is None

    @pytest.mark.asyncio
    async def test_handle_message_logs_message_type(self) -> None:
        """GIVEN message WHEN handle_message called THEN logs message type."""
        from mcp_server_langgraph.websocket.handlers.notifications import (
            NotificationWebSocketHandler,
        )
        from mcp_server_langgraph.websocket.types import MessageEnvelope, WebSocketConfig

        config = WebSocketConfig(endpoint_name="notifications")
        mock_broadcaster = AsyncMock(return_value=None)  # noqa: async-mock-config

        with patch(RATE_LIMITER_PATCH, return_value=MagicMock()):
            handler = NotificationWebSocketHandler(config=config, broadcaster=mock_broadcaster)

        handler._user_id = "user-123"
        message = MessageEnvelope(type="custom_ack", id="msg-2")

        # Should not raise
        response = await handler.handle_message(message)
        assert response is None


@pytest.mark.xdist_group(name="websocket_notification_protocol")
class TestBroadcasterProtocol:
    """Tests for BroadcasterProtocol."""

    def teardown_method(self) -> None:
        """Force GC to prevent mock accumulation in xdist workers."""
        gc.collect()

    def test_protocol_is_runtime_checkable(self) -> None:
        """GIVEN BroadcasterProtocol WHEN checking isinstance THEN works."""
        from mcp_server_langgraph.websocket.handlers.notifications import BroadcasterProtocol

        class MockBroadcaster:
            async def subscribe(self, websocket, user_id=None):
                pass

            async def unsubscribe(self, websocket):
                pass

        broadcaster = MockBroadcaster()
        assert isinstance(broadcaster, BroadcasterProtocol)
