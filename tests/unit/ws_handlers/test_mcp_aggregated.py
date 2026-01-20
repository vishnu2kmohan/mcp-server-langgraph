"""
MCP Aggregated WebSocket Handler Tests.

TDD tests for the MCP Aggregated WebSocket using the standardized WebSocketBase.

Tests verify:
- Handler extends WebSocketBase correctly
- Method signatures match base class contract
- Subscribe/unsubscribe/get_counts flows work
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
    """Create a mock MCP aggregated broadcaster."""
    broadcaster = MagicMock()
    broadcaster.subscribe = AsyncMock()  # noqa: async-mock-config
    broadcaster.unsubscribe = AsyncMock()  # noqa: async-mock-config
    broadcaster.get_current_counts = AsyncMock(  # noqa: async-mock-config
        return_value={
            "total_servers": 3,
            "total_tools": 15,
            "total_resources": 10,
            "total_prompts": 5,
        }
    )
    return broadcaster


@pytest.mark.xdist_group(name="mcp_aggregated_ws")
class TestMCPAggregatedHandlerConstruction:
    """Test MCPAggregatedHandler initialization and base class contract."""

    def teardown_method(self) -> None:
        """Force GC to prevent mock accumulation in xdist workers."""
        gc.collect()

    def test_handler_extends_websocket_base(self, mock_broadcaster: MagicMock) -> None:
        """
        GIVEN the MCPAggregatedHandler class
        WHEN checking its base classes
        THEN it should extend WebSocketBase.
        """
        from mcp_server_langgraph.websocket.base import WebSocketBase
        from mcp_server_langgraph.websocket.handlers.mcp_aggregated import (
            MCPAggregatedHandler,
        )

        handler = MCPAggregatedHandler(
            config=WebSocketConfig(endpoint_name="mcp-aggregated"),
            broadcaster=mock_broadcaster,
        )
        assert isinstance(handler, WebSocketBase)

    def test_handler_has_handle_message_method(
        self, mock_broadcaster: MagicMock
    ) -> None:
        """
        GIVEN the MCPAggregatedHandler class
        WHEN inspecting its methods
        THEN it should implement handle_message.
        """
        from mcp_server_langgraph.websocket.handlers.mcp_aggregated import (
            MCPAggregatedHandler,
        )

        handler = MCPAggregatedHandler(
            config=WebSocketConfig(endpoint_name="mcp-aggregated"),
            broadcaster=mock_broadcaster,
        )
        assert hasattr(handler, "handle_message")
        assert callable(getattr(handler, "handle_message"))


@pytest.mark.xdist_group(name="mcp_aggregated_ws")
class TestMCPAggregatedLifecycle:
    """Test MCP Aggregated WebSocket lifecycle methods."""

    def teardown_method(self) -> None:
        """Force GC to prevent mock accumulation in xdist workers."""
        gc.collect()

    @pytest.mark.asyncio
    async def test_on_connect_receives_auth_user(
        self, mock_websocket: MagicMock, mock_broadcaster: MagicMock
    ) -> None:
        """
        GIVEN an MCPAggregatedHandler
        WHEN on_connect is called
        THEN it should accept AuthUser and subscribe.
        """
        from mcp_server_langgraph.websocket.handlers.mcp_aggregated import (
            MCPAggregatedHandler,
        )
        from mcp_server_langgraph.websocket.types import AuthUser

        handler = MCPAggregatedHandler(
            config=WebSocketConfig(endpoint_name="mcp-aggregated"),
            broadcaster=mock_broadcaster,
        )
        handler._websocket = mock_websocket

        user = AuthUser(id="test-user", username="testuser")
        await handler.on_connect(user)

        assert handler._user_id == "test-user"
        mock_broadcaster.subscribe.assert_called_once()

    @pytest.mark.asyncio
    async def test_on_disconnect_clears_subscription(
        self, mock_websocket: MagicMock, mock_broadcaster: MagicMock
    ) -> None:
        """
        GIVEN an MCPAggregatedHandler with subscription
        WHEN on_disconnect is called
        THEN it should unsubscribe.
        """
        from mcp_server_langgraph.websocket.handlers.mcp_aggregated import (
            MCPAggregatedHandler,
        )
        from mcp_server_langgraph.websocket.types import AuthUser

        handler = MCPAggregatedHandler(
            config=WebSocketConfig(endpoint_name="mcp-aggregated"),
            broadcaster=mock_broadcaster,
        )
        handler._websocket = mock_websocket
        handler._user = AuthUser(id="test-user", username="testuser")
        handler._subscribed = True

        await handler.on_disconnect()

        mock_broadcaster.unsubscribe.assert_called_once()


@pytest.mark.xdist_group(name="mcp_aggregated_ws")
class TestMCPAggregatedMessageHandling:
    """Test MCP Aggregated message handling."""

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
        from mcp_server_langgraph.websocket.handlers.mcp_aggregated import (
            MCPAggregatedHandler,
        )

        handler = MCPAggregatedHandler(
            config=WebSocketConfig(endpoint_name="mcp-aggregated"),
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
        from mcp_server_langgraph.websocket.handlers.mcp_aggregated import (
            MCPAggregatedHandler,
        )

        handler = MCPAggregatedHandler(
            config=WebSocketConfig(endpoint_name="mcp-aggregated"),
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
    async def test_handle_get_counts(self, mock_broadcaster: MagicMock) -> None:
        """
        GIVEN a get_counts message
        WHEN handle_message is called
        THEN it should return capability counts.
        """
        from mcp_server_langgraph.websocket.handlers.mcp_aggregated import (
            MCPAggregatedHandler,
        )

        handler = MCPAggregatedHandler(
            config=WebSocketConfig(endpoint_name="mcp-aggregated"),
            broadcaster=mock_broadcaster,
        )

        message = MessageEnvelope(
            type="get_counts",
            payload={},
            id="msg-3",
        )

        response = await handler.handle_message(message)

        assert response is not None
        assert isinstance(response, MessageEnvelope)
        assert response.type == "capability_counts"
        mock_broadcaster.get_current_counts.assert_called_once()
