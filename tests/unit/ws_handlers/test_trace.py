"""
Trace WebSocket Handler Tests.

TDD tests for the Trace WebSocket using the standardized WebSocketBase.

Tests verify:
- Handler extends WebSocketBase correctly
- Method signatures match base class contract
- Subscribe/unsubscribe/filter flows work
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


@pytest.fixture
def mock_broadcaster() -> MagicMock:
    """Create a mock trace broadcaster."""
    broadcaster = MagicMock()
    broadcaster.subscribe = AsyncMock(return_value=None)  # noqa: async-mock-config
    broadcaster.unsubscribe = AsyncMock(return_value=None)  # noqa: async-mock-config
    broadcaster.get_recent_traces = AsyncMock(return_value=[])  # noqa: async-mock-config
    return broadcaster


@pytest.mark.xdist_group(name="trace_ws")
class TestTraceHandlerConstruction:
    """Test TraceHandler initialization and base class contract."""

    def teardown_method(self) -> None:
        """Force GC to prevent mock accumulation in xdist workers."""
        gc.collect()

    def test_handler_extends_websocket_base(self, mock_broadcaster: MagicMock) -> None:
        """
        GIVEN the TraceHandler class
        WHEN checking its base classes
        THEN it should extend WebSocketBase.
        """
        from mcp_server_langgraph.websocket.base import WebSocketBase
        from mcp_server_langgraph.websocket.handlers.trace import TraceHandler

        handler = TraceHandler(
            config=WebSocketConfig(endpoint_name="traces"),
            broadcaster=mock_broadcaster,
        )
        assert isinstance(handler, WebSocketBase)

    def test_handler_uses_broadcaster_mixin(self, mock_broadcaster: MagicMock) -> None:
        """
        GIVEN the TraceHandler class
        WHEN checking its base classes
        THEN it should use BroadcasterMixin for subscription state management.
        """
        from mcp_server_langgraph.websocket.handlers.trace import TraceHandler
        from mcp_server_langgraph.websocket.mixins import BroadcasterMixin

        assert issubclass(TraceHandler, BroadcasterMixin)

    def test_handler_has_handle_message_method(self, mock_broadcaster: MagicMock) -> None:
        """
        GIVEN the TraceHandler class
        WHEN inspecting its methods
        THEN it should implement handle_message.
        """
        from mcp_server_langgraph.websocket.handlers.trace import TraceHandler

        handler = TraceHandler(
            config=WebSocketConfig(endpoint_name="traces"),
            broadcaster=mock_broadcaster,
        )
        assert hasattr(handler, "handle_message")
        assert callable(handler.handle_message)


@pytest.mark.xdist_group(name="trace_ws")
class TestTraceLifecycle:
    """Test Trace WebSocket lifecycle methods."""

    def teardown_method(self) -> None:
        """Force GC to prevent mock accumulation in xdist workers."""
        gc.collect()

    @pytest.mark.asyncio
    async def test_on_connect_receives_auth_user(self, mock_websocket: MagicMock, mock_broadcaster: MagicMock) -> None:
        """
        GIVEN a TraceHandler
        WHEN on_connect is called
        THEN it should accept AuthUser and subscribe.
        """
        from mcp_server_langgraph.websocket.handlers.trace import TraceHandler
        from mcp_server_langgraph.websocket.types import AuthUser

        handler = TraceHandler(
            config=WebSocketConfig(endpoint_name="traces"),
            broadcaster=mock_broadcaster,
        )
        handler._websocket = mock_websocket

        user = AuthUser(id="test-user", username="testuser")
        # Set _user to simulate what run() does before calling on_connect()
        handler._user = user
        await handler.on_connect(user)

        # Use public user_id property from base class
        assert handler.user_id == "test-user"
        mock_broadcaster.subscribe.assert_called_once()

    @pytest.mark.asyncio
    async def test_on_disconnect_clears_subscription(self, mock_websocket: MagicMock, mock_broadcaster: MagicMock) -> None:
        """
        GIVEN a TraceHandler with subscription
        WHEN on_disconnect is called
        THEN it should unsubscribe.
        """
        from mcp_server_langgraph.websocket.handlers.trace import TraceHandler
        from mcp_server_langgraph.websocket.types import AuthUser

        handler = TraceHandler(
            config=WebSocketConfig(endpoint_name="traces"),
            broadcaster=mock_broadcaster,
        )
        handler._websocket = mock_websocket
        handler._user = AuthUser(id="test-user", username="testuser")
        handler._subscribed = True

        await handler.on_disconnect()

        mock_broadcaster.unsubscribe.assert_called_once()


@pytest.mark.xdist_group(name="trace_ws")
class TestTraceMessageHandling:
    """Test Trace message handling."""

    def teardown_method(self) -> None:
        """Force GC to prevent mock accumulation in xdist workers."""
        gc.collect()

    @pytest.mark.asyncio
    async def test_handle_subscribe(self, mock_broadcaster: MagicMock) -> None:
        """
        GIVEN a subscribe message
        WHEN handle_message is called
        THEN it should return subscribed response.
        """
        from mcp_server_langgraph.websocket.handlers.trace import TraceHandler

        handler = TraceHandler(
            config=WebSocketConfig(endpoint_name="traces"),
            broadcaster=mock_broadcaster,
        )

        message = MessageEnvelope(
            type="subscribe",
            payload={},
            id="msg-1",
        )

        response = await handler.handle_message(message)

        assert response is not None
        assert isinstance(response, MessageEnvelope)
        assert response.type == "subscribed"

    @pytest.mark.asyncio
    async def test_handle_unsubscribe(self, mock_broadcaster: MagicMock) -> None:
        """
        GIVEN an unsubscribe message
        WHEN handle_message is called
        THEN it should return unsubscribed response.
        """
        from mcp_server_langgraph.websocket.handlers.trace import TraceHandler

        handler = TraceHandler(
            config=WebSocketConfig(endpoint_name="traces"),
            broadcaster=mock_broadcaster,
        )
        handler._subscribed = True

        message = MessageEnvelope(
            type="unsubscribe",
            payload={},
            id="msg-2",
        )

        response = await handler.handle_message(message)

        assert response is not None
        assert isinstance(response, MessageEnvelope)
        assert response.type == "unsubscribed"

    @pytest.mark.asyncio
    async def test_handle_set_filter(self, mock_websocket: MagicMock, mock_broadcaster: MagicMock) -> None:
        """
        GIVEN a set_filter message
        WHEN handle_message is called
        THEN it should update filter and respond.
        """
        from mcp_server_langgraph.websocket.handlers.trace import TraceHandler

        handler = TraceHandler(
            config=WebSocketConfig(endpoint_name="traces"),
            broadcaster=mock_broadcaster,
        )
        handler._websocket = mock_websocket
        handler._subscribed = True

        message = MessageEnvelope(
            type="set_filter",
            payload={"service_name": "my-service", "status": "ERROR"},
            id="msg-3",
        )

        response = await handler.handle_message(message)

        assert response is not None
        assert response.type == "filter_updated"
        assert handler._current_filter.service_name == "my-service"
        assert handler._current_filter.status == "ERROR"

    @pytest.mark.asyncio
    async def test_handle_clear_filter(self, mock_websocket: MagicMock, mock_broadcaster: MagicMock) -> None:
        """
        GIVEN a clear_filter message
        WHEN handle_message is called
        THEN it should clear filter.
        """
        from mcp_server_langgraph.websocket.handlers.trace import (
            TraceFilter,
            TraceHandler,
        )

        handler = TraceHandler(
            config=WebSocketConfig(endpoint_name="traces"),
            broadcaster=mock_broadcaster,
        )
        handler._websocket = mock_websocket
        handler._subscribed = True
        handler._current_filter = TraceFilter(service_name="old-service")

        message = MessageEnvelope(
            type="clear_filter",
            payload={},
            id="msg-4",
        )

        response = await handler.handle_message(message)

        assert response is not None
        assert response.type == "filter_cleared"
        assert handler._current_filter.service_name is None

    @pytest.mark.asyncio
    async def test_handle_get_recent(self, mock_broadcaster: MagicMock) -> None:
        """
        GIVEN a get_recent message
        WHEN handle_message is called
        THEN it should return recent traces.
        """
        from mcp_server_langgraph.websocket.handlers.trace import TraceHandler

        mock_broadcaster.get_recent_traces.return_value = [{"trace_id": "trace-1", "service_name": "test"}]

        handler = TraceHandler(
            config=WebSocketConfig(endpoint_name="traces"),
            broadcaster=mock_broadcaster,
        )

        message = MessageEnvelope(
            type="get_recent",
            payload={"limit": 10},
            id="msg-5",
        )

        response = await handler.handle_message(message)

        assert response is not None
        assert response.type == "recent_traces"
        mock_broadcaster.get_recent_traces.assert_called_once()

    @pytest.mark.asyncio
    async def test_handle_unknown_type_returns_error(self, mock_broadcaster: MagicMock) -> None:
        """
        GIVEN an unknown message type
        WHEN handle_message is called
        THEN it should return an error response.
        """
        from mcp_server_langgraph.websocket.handlers.trace import TraceHandler

        handler = TraceHandler(
            config=WebSocketConfig(endpoint_name="traces"),
            broadcaster=mock_broadcaster,
        )

        message = MessageEnvelope(
            type="unknown_type",
            payload={},
            id="msg-6",
        )

        response = await handler.handle_message(message)

        assert response is not None
        assert isinstance(response, MessageEnvelope)
        assert response.type == "error"


@pytest.mark.xdist_group(name="trace_ws")
class TestTraceSessionIdFromQueryParams:
    """Test session_id extraction from WebSocket query parameters.

    These tests verify that TraceHandler properly extracts session_id
    from URL query parameters during on_connect, enabling session-scoped
    trace filtering for OTEL spans related to a specific session.
    """

    def teardown_method(self) -> None:
        """Force GC to prevent mock accumulation in xdist workers."""
        gc.collect()

    @pytest.mark.asyncio
    async def test_on_connect_extracts_session_id_from_query_params(self, mock_broadcaster: MagicMock) -> None:
        """
        GIVEN a WebSocket connection with session_id in query params
        WHEN on_connect is called
        THEN the handler should extract and store the session_id for filtering.
        """
        from mcp_server_langgraph.websocket.handlers.trace import TraceHandler
        from mcp_server_langgraph.websocket.types import AuthUser

        # Create websocket with session_id in query params
        ws = MagicMock()
        ws.accept = AsyncMock(return_value=None)
        ws.close = AsyncMock(return_value=None)
        ws.send_json = AsyncMock(return_value=None)
        ws.query_params = {"v": "1.0.0", "session_id": "session-abc-123"}
        ws.headers = {}

        handler = TraceHandler(
            config=WebSocketConfig(endpoint_name="traces"),
            broadcaster=mock_broadcaster,
        )
        handler._websocket = ws

        user = AuthUser(id="test-user", username="testuser")
        await handler.on_connect(user)

        # Verify session_id was extracted and stored in filter
        assert handler._session_id == "session-abc-123"

    @pytest.mark.asyncio
    async def test_on_connect_without_session_id_works(self, mock_websocket: MagicMock, mock_broadcaster: MagicMock) -> None:
        """
        GIVEN a WebSocket connection without session_id in query params
        WHEN on_connect is called
        THEN the handler should still work with None session_id.
        """
        from mcp_server_langgraph.websocket.handlers.trace import TraceHandler
        from mcp_server_langgraph.websocket.types import AuthUser

        # mock_websocket has query_params = {} (no session_id)
        handler = TraceHandler(
            config=WebSocketConfig(endpoint_name="traces"),
            broadcaster=mock_broadcaster,
        )
        handler._websocket = mock_websocket

        user = AuthUser(id="test-user", username="testuser")
        await handler.on_connect(user)

        # Should work with None session_id (receives all traces)
        assert handler._session_id is None
        mock_broadcaster.subscribe.assert_called_once()
