"""
Metrics Session WebSocket Handler Tests.

TDD tests for the Metrics Session WebSocket using the standardized WebSocketBase.

Tests verify:
- Handler extends WebSocketBase correctly
- Method signatures match base class contract
- Subscribe/unsubscribe flows work

NOTE: These tests expect the CORRECTED signatures matching WebSocketBase:
- on_connect(user: AuthUser) - not optional
- on_disconnect() - no parameters
- handle_message(message: MessageEnvelope) - no user parameter
"""

from __future__ import annotations

import gc
from unittest.mock import AsyncMock, MagicMock

import pytest

from mcp_server_langgraph.websocket import MessageEnvelope, WebSocketConfig

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


@pytest.mark.xdist_group(name="metrics_session_ws")
class TestMetricsSessionHandlerConstruction:
    """Test MetricsSessionHandler initialization and base class contract."""

    def teardown_method(self) -> None:
        """Force GC to prevent mock accumulation in xdist workers."""
        gc.collect()

    def test_handler_extends_websocket_base(self) -> None:
        """
        GIVEN the MetricsSessionHandler class
        WHEN checking its base classes
        THEN it should extend WebSocketBase.
        """
        from mcp_server_langgraph.websocket.base import WebSocketBase
        from mcp_server_langgraph.websocket.handlers.metrics_session import (
            MetricsSessionHandler,
        )

        handler = MetricsSessionHandler(config=WebSocketConfig(endpoint_name="metrics-session"))
        assert isinstance(handler, WebSocketBase)

    def test_handler_has_handle_message_method(self) -> None:
        """
        GIVEN the MetricsSessionHandler class
        WHEN inspecting its methods
        THEN it should implement handle_message.
        """
        from mcp_server_langgraph.websocket.handlers.metrics_session import (
            MetricsSessionHandler,
        )

        handler = MetricsSessionHandler(config=WebSocketConfig(endpoint_name="metrics-session"))
        assert hasattr(handler, "handle_message")
        assert callable(handler.handle_message)


@pytest.mark.xdist_group(name="metrics_session_ws")
class TestMetricsSessionLifecycle:
    """Test Metrics Session WebSocket lifecycle methods."""

    def teardown_method(self) -> None:
        """Force GC to prevent mock accumulation in xdist workers."""
        gc.collect()

    @pytest.mark.asyncio
    async def test_on_connect_receives_auth_user(self, mock_websocket: MagicMock) -> None:
        """
        GIVEN a MetricsSessionHandler
        WHEN on_connect is called
        THEN it should accept AuthUser (non-optional).
        """
        from mcp_server_langgraph.websocket.handlers.metrics_session import (
            MetricsSessionHandler,
        )
        from mcp_server_langgraph.websocket.types import AuthUser

        handler = MetricsSessionHandler(config=WebSocketConfig(endpoint_name="metrics-session"))
        handler._websocket = mock_websocket

        user = AuthUser(id="test-user", username="testuser")

        # Should not raise - signature: on_connect(user: AuthUser)
        await handler.on_connect(user)

    @pytest.mark.asyncio
    async def test_on_disconnect_has_no_parameters(self, mock_websocket: MagicMock) -> None:
        """
        GIVEN a MetricsSessionHandler with subscriptions
        WHEN on_disconnect is called
        THEN it should take no parameters and clear subscriptions.
        """
        from mcp_server_langgraph.websocket.handlers.metrics_session import (
            MetricsSessionHandler,
        )
        from mcp_server_langgraph.websocket.types import AuthUser

        handler = MetricsSessionHandler(config=WebSocketConfig(endpoint_name="metrics-session"))
        handler._websocket = mock_websocket
        handler._user = AuthUser(id="test-user", username="testuser")
        handler._subscribed_sessions = {"session-1", "session-2"}

        # Should not raise - signature: on_disconnect()
        await handler.on_disconnect()

        assert handler._subscribed_sessions == set()


@pytest.mark.xdist_group(name="metrics_session_ws")
class TestMetricsSessionMessageHandling:
    """Test Metrics Session message handling."""

    def teardown_method(self) -> None:
        """Force GC to prevent mock accumulation in xdist workers."""
        gc.collect()

    @pytest.mark.asyncio
    async def test_handle_subscribe_requires_session_id(self) -> None:
        """
        GIVEN a subscribe message without session_id
        WHEN handle_message is called
        THEN it should return an error response.
        """
        from mcp_server_langgraph.websocket.handlers.metrics_session import (
            MetricsSessionHandler,
        )

        handler = MetricsSessionHandler(config=WebSocketConfig(endpoint_name="metrics-session"))

        message = MessageEnvelope(
            type="subscribe",
            payload={},  # Missing session_id
            id="msg-1",
        )

        response = await handler.handle_message(message)

        assert response is not None
        assert isinstance(response, MessageEnvelope)
        assert response.type == "error"

    @pytest.mark.asyncio
    async def test_handle_subscribe_with_session_id(self) -> None:
        """
        GIVEN a subscribe message with session_id
        WHEN handle_message is called
        THEN it should return session_metrics response.
        """
        from mcp_server_langgraph.websocket.handlers.metrics_session import (
            MetricsSessionHandler,
        )

        handler = MetricsSessionHandler(config=WebSocketConfig(endpoint_name="metrics-session"))

        message = MessageEnvelope(
            type="subscribe",
            payload={"session_id": "session-123"},
            id="msg-2",
        )

        response = await handler.handle_message(message)

        assert response is not None
        assert isinstance(response, MessageEnvelope)
        assert response.type == "session_metrics"
        assert "session-123" in handler._subscribed_sessions

    @pytest.mark.asyncio
    async def test_handle_unsubscribe(self) -> None:
        """
        GIVEN an unsubscribe message
        WHEN handle_message is called
        THEN it should return unsubscribed response.
        """
        from mcp_server_langgraph.websocket.handlers.metrics_session import (
            MetricsSessionHandler,
        )

        handler = MetricsSessionHandler(config=WebSocketConfig(endpoint_name="metrics-session"))
        handler._subscribed_sessions = {"session-123"}

        message = MessageEnvelope(
            type="unsubscribe",
            payload={"session_id": "session-123"},
            id="msg-3",
        )

        response = await handler.handle_message(message)

        assert response is not None
        assert isinstance(response, MessageEnvelope)
        assert response.type == "unsubscribed"
        assert "session-123" not in handler._subscribed_sessions

    @pytest.mark.asyncio
    async def test_handle_ping_returns_pong(self) -> None:
        """
        GIVEN a ping message
        WHEN handle_message is called
        THEN it should return a pong response.
        """
        from mcp_server_langgraph.websocket.handlers.metrics_session import (
            MetricsSessionHandler,
        )

        handler = MetricsSessionHandler(config=WebSocketConfig(endpoint_name="metrics-session"))

        message = MessageEnvelope(
            type="ping",
            payload={},
            id="msg-4",
        )

        response = await handler.handle_message(message)

        assert response is not None
        assert isinstance(response, MessageEnvelope)
        assert response.type == "pong"

    @pytest.mark.asyncio
    async def test_handle_unknown_type_returns_error(self) -> None:
        """
        GIVEN an unknown message type
        WHEN handle_message is called
        THEN it should return an error response.
        """
        from mcp_server_langgraph.websocket.handlers.metrics_session import (
            MetricsSessionHandler,
        )

        handler = MetricsSessionHandler(config=WebSocketConfig(endpoint_name="metrics-session"))

        message = MessageEnvelope(
            type="unknown_type",
            payload={},
            id="msg-5",
        )

        response = await handler.handle_message(message)

        assert response is not None
        assert isinstance(response, MessageEnvelope)
        assert response.type == "error"
