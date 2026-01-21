"""
DevTools WebSocket Handler Tests.

TDD tests for the DevTools WebSocket using the standardized WebSocketBase.

Tests verify:
- Handler extends WebSocketBase correctly
- Method signatures match base class contract
- Subscribe/unsubscribe/context flows work
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
def mock_broadcaster() -> MagicMock:
    """Create a mock devtools broadcaster."""
    broadcaster = MagicMock()
    broadcaster.subscribe = AsyncMock()  # noqa: async-mock-config
    broadcaster.unsubscribe = AsyncMock()  # noqa: async-mock-config
    return broadcaster


@pytest.mark.xdist_group(name="devtools_ws")
class TestDevToolsHandlerConstruction:
    """Test DevToolsHandler initialization and base class contract."""

    def teardown_method(self) -> None:
        """Force GC to prevent mock accumulation in xdist workers."""
        gc.collect()

    def test_handler_extends_websocket_base(self, mock_broadcaster: MagicMock) -> None:
        """
        GIVEN the DevToolsHandler class
        WHEN checking its base classes
        THEN it should extend WebSocketBase.
        """
        from mcp_server_langgraph.websocket.base import WebSocketBase
        from mcp_server_langgraph.websocket.handlers.devtools import DevToolsHandler

        handler = DevToolsHandler(
            config=WebSocketConfig(endpoint_name="devtools"),
            broadcaster=mock_broadcaster,
        )
        assert isinstance(handler, WebSocketBase)

    def test_handler_uses_broadcaster_mixin(self, mock_broadcaster: MagicMock) -> None:
        """
        GIVEN the DevToolsHandler class
        WHEN checking its base classes
        THEN it should use BroadcasterMixin for subscription state management.
        """
        from mcp_server_langgraph.websocket.handlers.devtools import DevToolsHandler
        from mcp_server_langgraph.websocket.mixins import BroadcasterMixin

        assert issubclass(DevToolsHandler, BroadcasterMixin)

    def test_handler_has_handle_message_method(
        self, mock_broadcaster: MagicMock
    ) -> None:
        """
        GIVEN the DevToolsHandler class
        WHEN inspecting its methods
        THEN it should implement handle_message.
        """
        from mcp_server_langgraph.websocket.handlers.devtools import DevToolsHandler

        handler = DevToolsHandler(
            config=WebSocketConfig(endpoint_name="devtools"),
            broadcaster=mock_broadcaster,
        )
        assert hasattr(handler, "handle_message")
        assert callable(getattr(handler, "handle_message"))


@pytest.mark.xdist_group(name="devtools_ws")
class TestDevToolsLifecycle:
    """Test DevTools WebSocket lifecycle methods."""

    def teardown_method(self) -> None:
        """Force GC to prevent mock accumulation in xdist workers."""
        gc.collect()

    @pytest.mark.asyncio
    async def test_on_connect_receives_auth_user(
        self, mock_websocket: MagicMock, mock_broadcaster: MagicMock
    ) -> None:
        """
        GIVEN a DevToolsHandler
        WHEN on_connect is called
        THEN it should accept AuthUser and subscribe.
        """
        from mcp_server_langgraph.websocket.handlers.devtools import DevToolsHandler
        from mcp_server_langgraph.websocket.types import AuthUser

        handler = DevToolsHandler(
            config=WebSocketConfig(endpoint_name="devtools"),
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
    async def test_on_disconnect_clears_subscription(
        self, mock_websocket: MagicMock, mock_broadcaster: MagicMock
    ) -> None:
        """
        GIVEN a DevToolsHandler with subscription
        WHEN on_disconnect is called
        THEN it should unsubscribe.
        """
        from mcp_server_langgraph.websocket.handlers.devtools import DevToolsHandler
        from mcp_server_langgraph.websocket.types import AuthUser

        handler = DevToolsHandler(
            config=WebSocketConfig(endpoint_name="devtools"),
            broadcaster=mock_broadcaster,
        )
        handler._websocket = mock_websocket
        handler._user = AuthUser(id="test-user", username="testuser")
        handler._subscribed = True

        await handler.on_disconnect()

        mock_broadcaster.unsubscribe.assert_called_once()


@pytest.mark.xdist_group(name="devtools_ws")
class TestDevToolsMessageHandling:
    """Test DevTools message handling."""

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
        from mcp_server_langgraph.websocket.handlers.devtools import DevToolsHandler

        handler = DevToolsHandler(
            config=WebSocketConfig(endpoint_name="devtools"),
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
    async def test_handle_subscribe_with_context(
        self, mock_broadcaster: MagicMock
    ) -> None:
        """
        GIVEN a subscribe message with contextEntityId
        WHEN handle_message is called
        THEN it should store the context.
        """
        from mcp_server_langgraph.websocket.handlers.devtools import DevToolsHandler

        handler = DevToolsHandler(
            config=WebSocketConfig(endpoint_name="devtools"),
            broadcaster=mock_broadcaster,
        )

        message = MessageEnvelope(
            type="subscribe",
            payload={"contextEntityId": "session-123"},
            id="msg-1",
        )

        response = await handler.handle_message(message)

        assert response is not None
        assert response.type == "subscribed"
        assert handler._context_entity_id == "session-123"

    @pytest.mark.asyncio
    async def test_handle_unsubscribe(self, mock_broadcaster: MagicMock) -> None:
        """
        GIVEN an unsubscribe message
        WHEN handle_message is called
        THEN it should return unsubscribed response.
        """
        from mcp_server_langgraph.websocket.handlers.devtools import DevToolsHandler

        handler = DevToolsHandler(
            config=WebSocketConfig(endpoint_name="devtools"),
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
    async def test_handle_set_context(
        self, mock_websocket: MagicMock, mock_broadcaster: MagicMock
    ) -> None:
        """
        GIVEN a set_context message
        WHEN handle_message is called
        THEN it should update context and re-subscribe.
        """
        from mcp_server_langgraph.websocket.handlers.devtools import DevToolsHandler

        handler = DevToolsHandler(
            config=WebSocketConfig(endpoint_name="devtools"),
            broadcaster=mock_broadcaster,
        )
        handler._websocket = mock_websocket
        handler._subscribed = True

        message = MessageEnvelope(
            type="set_context",
            payload={"contextEntityId": "workflow-456"},
            id="msg-3",
        )

        response = await handler.handle_message(message)

        assert response is not None
        assert response.type == "context_updated"
        assert handler._context_entity_id == "workflow-456"


@pytest.mark.xdist_group(name="devtools_ws")
class TestDevToolsContextIdFromQueryParams:
    """Test context_id extraction from WebSocket query parameters.

    These tests verify that DevToolsHandler properly extracts context_id
    from URL query parameters during on_connect, enabling session-scoped
    trace filtering without requiring a separate subscribe message.

    This is critical for the LangGraph trace streaming flow where the
    frontend connects with ?context_id=<session_id> in the URL.
    """

    def teardown_method(self) -> None:
        """Force GC to prevent mock accumulation in xdist workers."""
        gc.collect()

    @pytest.mark.asyncio
    async def test_on_connect_extracts_context_id_from_query_params(
        self, mock_broadcaster: MagicMock
    ) -> None:
        """
        GIVEN a WebSocket connection with context_id in query params
        WHEN on_connect is called
        THEN the handler should extract and store the context_id.
        """
        from mcp_server_langgraph.websocket.handlers.devtools import DevToolsHandler
        from mcp_server_langgraph.websocket.types import AuthUser

        # Create websocket with context_id in query params
        ws = MagicMock()
        ws.accept = AsyncMock()
        ws.close = AsyncMock()
        ws.send_json = AsyncMock()
        ws.query_params = {"v": "1.0.0", "context_id": "session-abc-123"}
        ws.headers = {}

        handler = DevToolsHandler(
            config=WebSocketConfig(endpoint_name="devtools"),
            broadcaster=mock_broadcaster,
        )
        handler._websocket = ws

        user = AuthUser(id="test-user", username="testuser")
        await handler.on_connect(user)

        # Verify context_id was extracted from query params
        assert handler._context_entity_id == "session-abc-123"

    @pytest.mark.asyncio
    async def test_on_connect_passes_context_id_to_broadcaster_subscribe(
        self, mock_broadcaster: MagicMock
    ) -> None:
        """
        GIVEN a WebSocket connection with context_id in query params
        WHEN on_connect subscribes to the broadcaster
        THEN the context_entity_id should be passed to broadcaster.subscribe.
        """
        from mcp_server_langgraph.websocket.handlers.devtools import DevToolsHandler
        from mcp_server_langgraph.websocket.types import AuthUser

        # Create websocket with context_id in query params
        ws = MagicMock()
        ws.accept = AsyncMock()
        ws.close = AsyncMock()
        ws.send_json = AsyncMock()
        ws.query_params = {"v": "1.0.0", "context_id": "session-xyz-789"}
        ws.headers = {}

        handler = DevToolsHandler(
            config=WebSocketConfig(endpoint_name="devtools"),
            broadcaster=mock_broadcaster,
        )
        handler._websocket = ws

        user = AuthUser(id="test-user", username="testuser")
        await handler.on_connect(user)

        # Verify broadcaster.subscribe was called with the context_id
        mock_broadcaster.subscribe.assert_called_once()
        call_kwargs = mock_broadcaster.subscribe.call_args[1]
        assert call_kwargs.get("context_entity_id") == "session-xyz-789"

    @pytest.mark.asyncio
    async def test_on_connect_handles_missing_context_id_gracefully(
        self, mock_websocket: MagicMock, mock_broadcaster: MagicMock
    ) -> None:
        """
        GIVEN a WebSocket connection without context_id in query params
        WHEN on_connect is called
        THEN the handler should still work with None context.
        """
        from mcp_server_langgraph.websocket.handlers.devtools import DevToolsHandler
        from mcp_server_langgraph.websocket.types import AuthUser

        # mock_websocket has query_params = {} (no context_id)
        handler = DevToolsHandler(
            config=WebSocketConfig(endpoint_name="devtools"),
            broadcaster=mock_broadcaster,
        )
        handler._websocket = mock_websocket

        user = AuthUser(id="test-user", username="testuser")
        await handler.on_connect(user)

        # Should work with None context
        assert handler._context_entity_id is None
        mock_broadcaster.subscribe.assert_called_once()

    @pytest.mark.asyncio
    async def test_subscribe_message_overrides_query_param_context(
        self, mock_broadcaster: MagicMock
    ) -> None:
        """
        GIVEN a handler with context_id from query params
        WHEN a subscribe message provides a different contextEntityId
        THEN the message context should override the URL context.
        """
        from mcp_server_langgraph.websocket.handlers.devtools import DevToolsHandler
        from mcp_server_langgraph.websocket.types import AuthUser

        # Create websocket with context_id in query params
        ws = MagicMock()
        ws.accept = AsyncMock()
        ws.close = AsyncMock()
        ws.send_json = AsyncMock()
        ws.query_params = {"v": "1.0.0", "context_id": "initial-session"}
        ws.headers = {}

        handler = DevToolsHandler(
            config=WebSocketConfig(endpoint_name="devtools"),
            broadcaster=mock_broadcaster,
        )
        handler._websocket = ws

        # Connect and get initial context from URL
        user = AuthUser(id="test-user", username="testuser")
        await handler.on_connect(user)
        assert handler._context_entity_id == "initial-session"

        # Send subscribe message with different context
        message = MessageEnvelope(
            type="subscribe",
            payload={"contextEntityId": "override-session"},
            id="msg-1",
        )
        await handler.handle_message(message)

        # Message context should override URL context
        assert handler._context_entity_id == "override-session"
