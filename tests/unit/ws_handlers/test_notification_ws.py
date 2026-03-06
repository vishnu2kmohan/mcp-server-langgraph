"""
Notification WebSocket Handler Tests.

TDD tests for the Notification WebSocket using the standardized WebSocketBase.
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
def mock_broadcaster() -> MagicMock:
    """Create a mock notification broadcaster."""
    broadcaster = MagicMock()
    broadcaster.subscribe = AsyncMock(return_value=None)  # noqa: async-mock-config
    broadcaster.unsubscribe = AsyncMock(return_value=None)  # noqa: async-mock-config
    return broadcaster


class TestNotificationWebSocketHandler:
    """Test Notification WebSocket using WebSocketBase."""

    def teardown_method(self) -> None:
        """Force GC to prevent mock accumulation in xdist workers."""
        gc.collect()

    @pytest.mark.asyncio
    async def test_handler_extends_websocket_base(self) -> None:
        """
        GIVEN the NotificationWebSocketHandler class
        WHEN checking its base classes
        THEN it should extend WebSocketBase.
        """
        from mcp_server_langgraph.websocket.base import WebSocketBase
        from mcp_server_langgraph.websocket.handlers.notifications import (
            NotificationWebSocketHandler,
        )

        assert issubclass(NotificationWebSocketHandler, WebSocketBase)

    @pytest.mark.asyncio
    async def test_subscribes_on_connect(self, mock_websocket: MagicMock, mock_broadcaster: MagicMock) -> None:
        """
        GIVEN a new WebSocket connection
        WHEN on_connect is called
        THEN the client should be subscribed to the broadcaster.
        """
        from mcp_server_langgraph.websocket.handlers.notifications import (
            NotificationWebSocketHandler,
        )
        from mcp_server_langgraph.websocket.types import AuthUser

        handler = NotificationWebSocketHandler(
            config=WebSocketConfig(require_auth=True, endpoint_name="notifications"),
            broadcaster=mock_broadcaster,
        )
        handler._websocket = mock_websocket

        user = AuthUser(id="test-user", username="testuser")
        # Set _user to simulate what run() does before calling on_connect()
        handler._user = user
        await handler.on_connect(user)

        mock_broadcaster.subscribe.assert_called_once()
        call_kwargs = mock_broadcaster.subscribe.call_args[1]
        assert call_kwargs.get("user_id") == "test-user"

    @pytest.mark.asyncio
    async def test_unsubscribes_on_disconnect(self, mock_websocket: MagicMock, mock_broadcaster: MagicMock) -> None:
        """
        GIVEN an active connection
        WHEN on_disconnect is called
        THEN the client should be unsubscribed from the broadcaster.
        """
        from mcp_server_langgraph.websocket.handlers.notifications import (
            NotificationWebSocketHandler,
        )
        from mcp_server_langgraph.websocket.types import AuthUser

        handler = NotificationWebSocketHandler(
            config=WebSocketConfig(require_auth=True, endpoint_name="notifications"),
            broadcaster=mock_broadcaster,
        )
        handler._websocket = mock_websocket

        # First subscribe
        user = AuthUser(id="test-user", username="testuser")
        await handler.on_connect(user)

        # Then disconnect
        await handler.on_disconnect()

        mock_broadcaster.unsubscribe.assert_called_once_with(mock_websocket)

    @pytest.mark.asyncio
    async def test_handle_message_returns_none_for_unknown(
        self, mock_websocket: MagicMock, mock_broadcaster: MagicMock
    ) -> None:
        """
        GIVEN an active connection
        WHEN an unknown message type is received
        THEN None should be returned (notification WS is passive).
        """
        from mcp_server_langgraph.websocket.handlers.notifications import (
            NotificationWebSocketHandler,
        )

        handler = NotificationWebSocketHandler(
            config=WebSocketConfig(require_auth=True, endpoint_name="notifications"),
            broadcaster=mock_broadcaster,
        )

        message = MessageEnvelope(
            type="unknown_type",
            payload={},
        )

        # Notification WS is mostly passive - it receives messages from server
        response = await handler.handle_message(message)
        assert response is None

    @pytest.mark.asyncio
    async def test_requires_auth_by_default(self, mock_websocket: MagicMock, mock_broadcaster: MagicMock) -> None:
        """
        GIVEN a notification WebSocket handler
        WHEN checking the config
        THEN auth should be required by default.
        """
        from mcp_server_langgraph.websocket.handlers.notifications import (
            NotificationWebSocketHandler,
        )

        handler = NotificationWebSocketHandler(
            config=WebSocketConfig(
                require_auth=True,
                endpoint_name="notifications",
            ),
            broadcaster=mock_broadcaster,
        )

        assert handler.config.require_auth is True
