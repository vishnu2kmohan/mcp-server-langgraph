"""
Unit tests for MCPAggregatedHandler.

TDD: These tests define expected behavior for real-time MCP capability updates.
The handler should:
- Support subscription to capability change events
- Push real-time updates when tools/resources/prompts are changed
- Support server-specific subscription filtering
- Notify clients when servers are registered/unregistered

Reference: MCP Protocol 2025-11-25 capability aggregation
"""

import gc
from unittest.mock import AsyncMock, MagicMock

import pytest

from mcp_server_langgraph.websocket.types import (
    AuthUser,
    MessageEnvelope,
    WebSocketConfig,
)

# Mark all tests in this module as unit tests
pytestmark = pytest.mark.unit


@pytest.fixture
def mock_broadcaster():
    """Create a mock MCP aggregated broadcaster."""
    broadcaster = MagicMock()
    broadcaster.subscribe = AsyncMock(return_value=None)
    broadcaster.unsubscribe = AsyncMock(return_value=None)
    broadcaster.get_current_counts = AsyncMock(
        return_value={
            "total_servers": 2,
            "total_tools": 10,
            "total_resources": 5,
            "total_prompts": 3,
        }
    )
    return broadcaster


@pytest.fixture
def handler_config():
    """Create a standard MCP aggregated handler configuration."""
    return WebSocketConfig(
        endpoint_name="mcp-aggregated",
        require_auth=True,
        authz_resource_type="mcp",
        authz_resource_id="aggregated-capabilities",
        authz_required_relation="viewer",
        rate_limit_per_minute=600,
        message_timeout=30,
    )


@pytest.fixture
def mock_user():
    """Create a mock authenticated user."""
    return AuthUser(
        id="user-123",
        username="testuser",
        email="test@example.com",
        roles=["developer"],
    )


@pytest.mark.xdist_group(name="mcp_aggregated_handler")
class TestMCPAggregatedHandler:
    """Tests for MCPAggregatedHandler class."""

    def teardown_method(self) -> None:
        """Force GC to prevent mock accumulation in xdist workers."""
        gc.collect()

    def test_handler_initializes_with_config_and_broadcaster(self, handler_config, mock_broadcaster) -> None:
        """Test handler initialization with required dependencies."""
        from mcp_server_langgraph.websocket.handlers.mcp_aggregated import (
            MCPAggregatedHandler,
        )

        handler = MCPAggregatedHandler(
            config=handler_config,
            broadcaster=mock_broadcaster,
        )

        assert handler._broadcaster is mock_broadcaster

    @pytest.mark.asyncio
    async def test_on_connect_subscribes_to_broadcaster(self, handler_config, mock_broadcaster, mock_user) -> None:
        """Test that on_connect subscribes to capability broadcaster."""
        from mcp_server_langgraph.websocket.handlers.mcp_aggregated import (
            MCPAggregatedHandler,
        )

        handler = MCPAggregatedHandler(
            config=handler_config,
            broadcaster=mock_broadcaster,
        )
        handler._websocket = MagicMock()

        await handler.on_connect(mock_user)

        mock_broadcaster.subscribe.assert_called_once()
        assert handler._user_id == "user-123"

    @pytest.mark.asyncio
    async def test_on_disconnect_unsubscribes_from_broadcaster(self, handler_config, mock_broadcaster, mock_user) -> None:
        """Test that on_disconnect unsubscribes from broadcaster."""
        from mcp_server_langgraph.websocket.handlers.mcp_aggregated import (
            MCPAggregatedHandler,
        )

        handler = MCPAggregatedHandler(
            config=handler_config,
            broadcaster=mock_broadcaster,
        )
        handler._websocket = MagicMock()
        handler._subscribed = True

        await handler.on_disconnect()

        mock_broadcaster.unsubscribe.assert_called_once()

    @pytest.mark.asyncio
    async def test_handle_subscribe_message(self, handler_config, mock_broadcaster) -> None:
        """Test handling subscribe message."""
        from mcp_server_langgraph.websocket.handlers.mcp_aggregated import (
            MCPAggregatedHandler,
        )

        handler = MCPAggregatedHandler(
            config=handler_config,
            broadcaster=mock_broadcaster,
        )
        handler._websocket = MagicMock()
        handler._user_id = "user-123"

        message = MessageEnvelope(type="subscribe", id="req-1")
        response = await handler.handle_message(message)

        assert response is not None
        assert response.type == "subscribed"
        assert response.id == "req-1"

    @pytest.mark.asyncio
    async def test_handle_get_counts_message(self, handler_config, mock_broadcaster) -> None:
        """Test handling get_counts message returns current capability counts."""
        from mcp_server_langgraph.websocket.handlers.mcp_aggregated import (
            MCPAggregatedHandler,
        )

        handler = MCPAggregatedHandler(
            config=handler_config,
            broadcaster=mock_broadcaster,
        )
        handler._websocket = MagicMock()
        handler._user_id = "user-123"

        message = MessageEnvelope(type="get_counts", id="req-2")
        response = await handler.handle_message(message)

        assert response is not None
        assert response.type == "capability_counts"
        assert response.id == "req-2"
        assert response.payload is not None
        assert "total_servers" in response.payload
        assert "total_tools" in response.payload

    @pytest.mark.asyncio
    async def test_handle_unsubscribe_message(self, handler_config, mock_broadcaster) -> None:
        """Test handling unsubscribe message."""
        from mcp_server_langgraph.websocket.handlers.mcp_aggregated import (
            MCPAggregatedHandler,
        )

        handler = MCPAggregatedHandler(
            config=handler_config,
            broadcaster=mock_broadcaster,
        )
        handler._websocket = MagicMock()
        handler._user_id = "user-123"
        handler._subscribed = True

        message = MessageEnvelope(type="unsubscribe", id="req-3")
        response = await handler.handle_message(message)

        assert response is not None
        assert response.type == "unsubscribed"
        assert response.id == "req-3"


@pytest.mark.xdist_group(name="mcp_aggregated_handler")
class TestMCPAggregatedBroadcaster:
    """Tests for MCPAggregatedBroadcaster class."""

    def teardown_method(self) -> None:
        """Force GC to prevent mock accumulation in xdist workers."""
        gc.collect()

    def test_broadcaster_can_be_instantiated(self) -> None:
        """Test broadcaster instantiation."""
        from mcp_server_langgraph.websocket.handlers.mcp_aggregated import (
            MCPAggregatedBroadcaster,
        )

        broadcaster = MCPAggregatedBroadcaster()

        assert broadcaster is not None
        assert broadcaster._subscribers == {}

    @pytest.mark.asyncio
    async def test_subscribe_adds_websocket_to_subscribers(self) -> None:
        """Test subscribing a WebSocket."""
        from mcp_server_langgraph.websocket.handlers.mcp_aggregated import (
            MCPAggregatedBroadcaster,
        )

        broadcaster = MCPAggregatedBroadcaster()
        mock_ws = MagicMock()
        mock_ws.send_json = AsyncMock(return_value=None)

        await broadcaster.subscribe(mock_ws, user_id="user-123")

        assert mock_ws in broadcaster._subscribers
        assert broadcaster._subscribers[mock_ws] == "user-123"

    @pytest.mark.asyncio
    async def test_unsubscribe_removes_websocket_from_subscribers(self) -> None:
        """Test unsubscribing a WebSocket."""
        from mcp_server_langgraph.websocket.handlers.mcp_aggregated import (
            MCPAggregatedBroadcaster,
        )

        broadcaster = MCPAggregatedBroadcaster()
        mock_ws = MagicMock()
        await broadcaster.subscribe(mock_ws, user_id="user-123")

        await broadcaster.unsubscribe(mock_ws)

        assert mock_ws not in broadcaster._subscribers

    @pytest.mark.asyncio
    async def test_broadcast_tools_changed_sends_to_all_subscribers(self) -> None:
        """Test broadcasting tools changed event uses JSON-RPC 2.0 format.

        Reference: MCP Protocol 2025-11-25 notifications/tools/list_changed
        """
        from mcp_server_langgraph.websocket.handlers.mcp_aggregated import (
            MCPAggregatedBroadcaster,
        )

        broadcaster = MCPAggregatedBroadcaster()
        mock_ws1 = MagicMock()
        mock_ws1.send_json = AsyncMock(return_value=None)
        mock_ws2 = MagicMock()
        mock_ws2.send_json = AsyncMock(return_value=None)

        await broadcaster.subscribe(mock_ws1, user_id="user-1")
        await broadcaster.subscribe(mock_ws2, user_id="user-2")

        await broadcaster.broadcast_tools_changed(server_name="test-server", count=5)

        # Both subscribers should receive the message
        assert mock_ws1.send_json.call_count == 1
        assert mock_ws2.send_json.call_count == 1

        # Check message content - MCP JSON-RPC 2.0 format
        call_args = mock_ws1.send_json.call_args[0][0]
        assert call_args["jsonrpc"] == "2.0"
        assert call_args["method"] == "notifications/tools/list_changed"
        assert call_args["params"]["serverName"] == "test-server"
        assert call_args["params"]["count"] == 5

    @pytest.mark.asyncio
    async def test_broadcast_resources_changed(self) -> None:
        """Test broadcasting resources changed event uses JSON-RPC 2.0 format.

        Reference: MCP Protocol 2025-11-25 notifications/resources/list_changed
        """
        from mcp_server_langgraph.websocket.handlers.mcp_aggregated import (
            MCPAggregatedBroadcaster,
        )

        broadcaster = MCPAggregatedBroadcaster()
        mock_ws = MagicMock()
        mock_ws.send_json = AsyncMock(return_value=None)
        await broadcaster.subscribe(mock_ws, user_id="user-1")

        await broadcaster.broadcast_resources_changed(server_name="test-server", count=3)

        call_args = mock_ws.send_json.call_args[0][0]
        assert call_args["jsonrpc"] == "2.0"
        assert call_args["method"] == "notifications/resources/list_changed"
        assert call_args["params"]["serverName"] == "test-server"

    @pytest.mark.asyncio
    async def test_broadcast_prompts_changed(self) -> None:
        """Test broadcasting prompts changed event uses JSON-RPC 2.0 format.

        Reference: MCP Protocol 2025-11-25 notifications/prompts/list_changed
        """
        from mcp_server_langgraph.websocket.handlers.mcp_aggregated import (
            MCPAggregatedBroadcaster,
        )

        broadcaster = MCPAggregatedBroadcaster()
        mock_ws = MagicMock()
        mock_ws.send_json = AsyncMock(return_value=None)
        await broadcaster.subscribe(mock_ws, user_id="user-1")

        await broadcaster.broadcast_prompts_changed(server_name="test-server", count=2)

        call_args = mock_ws.send_json.call_args[0][0]
        assert call_args["jsonrpc"] == "2.0"
        assert call_args["method"] == "notifications/prompts/list_changed"
        assert call_args["params"]["serverName"] == "test-server"

    @pytest.mark.asyncio
    async def test_broadcast_server_registered(self) -> None:
        """Test broadcasting server registered event uses JSON-RPC 2.0 format.

        Note: Server registration is an extension to standard MCP notifications.
        """
        from mcp_server_langgraph.websocket.handlers.mcp_aggregated import (
            MCPAggregatedBroadcaster,
        )

        broadcaster = MCPAggregatedBroadcaster()
        mock_ws = MagicMock()
        mock_ws.send_json = AsyncMock(return_value=None)
        await broadcaster.subscribe(mock_ws, user_id="user-1")

        await broadcaster.broadcast_server_registered(
            server_name="new-server",
            tool_count=5,
            resource_count=3,
            prompt_count=2,
        )

        call_args = mock_ws.send_json.call_args[0][0]
        assert call_args["jsonrpc"] == "2.0"
        assert call_args["method"] == "notifications/server/registered"
        assert call_args["params"]["serverName"] == "new-server"
        assert call_args["params"]["toolCount"] == 5
        assert call_args["params"]["resourceCount"] == 3
        assert call_args["params"]["promptCount"] == 2

    @pytest.mark.asyncio
    async def test_broadcast_server_unregistered(self) -> None:
        """Test broadcasting server unregistered event uses JSON-RPC 2.0 format.

        Note: Server unregistration is an extension to standard MCP notifications.
        """
        from mcp_server_langgraph.websocket.handlers.mcp_aggregated import (
            MCPAggregatedBroadcaster,
        )

        broadcaster = MCPAggregatedBroadcaster()
        mock_ws = MagicMock()
        mock_ws.send_json = AsyncMock(return_value=None)
        await broadcaster.subscribe(mock_ws, user_id="user-1")

        await broadcaster.broadcast_server_unregistered(server_name="old-server")

        call_args = mock_ws.send_json.call_args[0][0]
        assert call_args["jsonrpc"] == "2.0"
        assert call_args["method"] == "notifications/server/unregistered"
        assert call_args["params"]["serverName"] == "old-server"

    @pytest.mark.asyncio
    async def test_broadcast_handles_closed_connection_gracefully(self) -> None:
        """Test that broadcast removes closed connections gracefully."""
        from mcp_server_langgraph.websocket.handlers.mcp_aggregated import (
            MCPAggregatedBroadcaster,
        )

        broadcaster = MCPAggregatedBroadcaster()
        mock_ws = MagicMock()
        mock_ws.send_json = AsyncMock(side_effect=Exception("Connection closed"))
        await broadcaster.subscribe(mock_ws, user_id="user-1")

        # Should not raise - connection should be removed
        await broadcaster.broadcast_tools_changed(server_name="test", count=1)

        # Subscriber should have been removed due to error
        assert mock_ws not in broadcaster._subscribers
