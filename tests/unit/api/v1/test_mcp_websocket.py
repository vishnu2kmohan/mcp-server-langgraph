"""
MCP WebSocket Handler Unit Tests

Tests for the MCP WebSocket handler per TDD methodology.
Tests the WebSocket endpoint that provides MCP 2025-11-25 compliant communication.
"""

from __future__ import annotations

import gc
from unittest.mock import AsyncMock, patch

import pytest
from starlette.websockets import WebSocket

pytestmark = [
    pytest.mark.unit,
    pytest.mark.api,
    pytest.mark.websocket,
]


@pytest.mark.xdist_group(name="test_mcp_websocket")
class TestMCPWebSocketHandler:
    """Tests for MCP WebSocket handler."""

    def teardown_method(self) -> None:
        """Force GC to prevent mock accumulation in xdist workers."""
        gc.collect()

    def test_websocket_endpoint_exists(self) -> None:
        """
        GIVEN the v1 router with MCP WebSocket
        WHEN importing the websocket router
        THEN should have websocket endpoint defined.
        """
        from mcp_server_langgraph.api.v1.mcp_websocket import mcp_websocket_router

        # Check router has websocket routes
        routes = [r for r in mcp_websocket_router.routes]
        websocket_routes = [r for r in routes if hasattr(r, "path") and "/ws" in r.path]
        assert len(websocket_routes) > 0, "Should have at least one websocket route"

    def test_mcp_message_handler_exists(self) -> None:
        """
        GIVEN the MCP WebSocket module
        WHEN importing message handler
        THEN should export MCPMessageHandler class.
        """
        from mcp_server_langgraph.api.v1.mcp_websocket import MCPMessageHandler

        assert MCPMessageHandler is not None

    def test_message_handler_handles_initialize(self) -> None:
        """
        GIVEN an MCPMessageHandler instance
        WHEN handling an initialize message
        THEN should return proper initialize response.
        """
        from mcp_server_langgraph.api.v1.mcp_websocket import MCPMessageHandler

        handler = MCPMessageHandler()

        message = {
            "jsonrpc": "2.0",
            "id": 1,
            "method": "initialize",
            "params": {
                "protocolVersion": "2025-11-25",
                "capabilities": {},
                "clientInfo": {"name": "test-client", "version": "1.0.0"},
            },
        }

        response = handler.handle_sync(message)

        assert response["jsonrpc"] == "2.0"
        assert response["id"] == 1
        assert "result" in response
        assert response["result"]["protocolVersion"] == "2025-11-25"
        assert "serverInfo" in response["result"]
        assert "capabilities" in response["result"]

    def test_message_handler_handles_unknown_method(self) -> None:
        """
        GIVEN an MCPMessageHandler instance
        WHEN handling an unknown method
        THEN should return method not found error.
        """
        from mcp_server_langgraph.api.v1.mcp_websocket import MCPMessageHandler

        handler = MCPMessageHandler()

        message = {
            "jsonrpc": "2.0",
            "id": 1,
            "method": "unknown/method",
            "params": {},
        }

        response = handler.handle_sync(message)

        assert response["jsonrpc"] == "2.0"
        assert response["id"] == 1
        assert "error" in response
        assert response["error"]["code"] == -32601  # Method not found

    def test_message_handler_handles_invalid_json(self) -> None:
        """
        GIVEN an MCPMessageHandler instance
        WHEN handling invalid JSON
        THEN should return parse error.
        """
        from mcp_server_langgraph.api.v1.mcp_websocket import MCPMessageHandler

        handler = MCPMessageHandler()

        # Simulate what would happen with invalid JSON
        response = handler.handle_parse_error()

        assert response["jsonrpc"] == "2.0"
        assert response["id"] is None
        assert "error" in response
        assert response["error"]["code"] == -32700  # Parse error

    def test_message_handler_handles_invalid_request(self) -> None:
        """
        GIVEN an MCPMessageHandler instance
        WHEN handling a request without required fields
        THEN should return invalid request error.
        """
        from mcp_server_langgraph.api.v1.mcp_websocket import MCPMessageHandler

        handler = MCPMessageHandler()

        # Missing method field
        message = {"jsonrpc": "2.0", "id": 1}

        response = handler.handle_sync(message)

        assert response["jsonrpc"] == "2.0"
        assert "error" in response
        assert response["error"]["code"] == -32600  # Invalid request


@pytest.mark.xdist_group(name="test_mcp_websocket")
class TestMCPWebSocketToolsHandler:
    """Tests for MCP WebSocket tools/* methods."""

    def teardown_method(self) -> None:
        """Force GC to prevent mock accumulation in xdist workers."""
        gc.collect()

    @pytest.mark.asyncio
    async def test_tools_list_returns_tools(self) -> None:
        """
        GIVEN an MCPMessageHandler instance
        WHEN handling tools/list message
        THEN should return list of available tools.
        """
        from mcp_server_langgraph.api.v1.mcp_websocket import MCPMessageHandler

        handler = MCPMessageHandler()

        message = {
            "jsonrpc": "2.0",
            "id": 2,
            "method": "tools/list",
            "params": {},
        }

        response = await handler.handle(message)

        assert response["jsonrpc"] == "2.0"
        assert response["id"] == 2
        assert "result" in response
        assert "tools" in response["result"]
        assert isinstance(response["result"]["tools"], list)

    @pytest.mark.asyncio
    async def test_tools_call_executes_tool(self) -> None:
        """
        GIVEN an MCPMessageHandler instance with mock tool executor
        WHEN handling tools/call message
        THEN should execute the tool and return result.
        """
        from mcp_server_langgraph.api.v1.mcp_websocket import MCPMessageHandler

        handler = MCPMessageHandler()

        # Mock the tool executor
        with patch.object(
            handler,
            "execute_tool",
            new_callable=AsyncMock,
            return_value=[{"type": "text", "text": "Tool result"}],
        ):
            message = {
                "jsonrpc": "2.0",
                "id": 3,
                "method": "tools/call",
                "params": {
                    "name": "test-tool",
                    "arguments": {"query": "test"},
                },
            }

            response = await handler.handle(message)

            assert response["jsonrpc"] == "2.0"
            assert response["id"] == 3
            assert "result" in response
            assert "content" in response["result"]


@pytest.mark.xdist_group(name="test_mcp_websocket")
class TestMCPWebSocketResourcesHandler:
    """Tests for MCP WebSocket resources/* methods."""

    def teardown_method(self) -> None:
        """Force GC to prevent mock accumulation in xdist workers."""
        gc.collect()

    @pytest.mark.asyncio
    async def test_resources_list_returns_resources(self) -> None:
        """
        GIVEN an MCPMessageHandler instance
        WHEN handling resources/list message
        THEN should return list of available resources.
        """
        from mcp_server_langgraph.api.v1.mcp_websocket import MCPMessageHandler

        handler = MCPMessageHandler()

        message = {
            "jsonrpc": "2.0",
            "id": 4,
            "method": "resources/list",
            "params": {},
        }

        response = await handler.handle(message)

        assert response["jsonrpc"] == "2.0"
        assert response["id"] == 4
        assert "result" in response
        assert "resources" in response["result"]
        assert isinstance(response["result"]["resources"], list)

    @pytest.mark.asyncio
    async def test_resources_read_returns_content(self) -> None:
        """
        GIVEN an MCPMessageHandler instance
        WHEN handling resources/read message
        THEN should return resource content.
        """
        from mcp_server_langgraph.api.v1.mcp_websocket import MCPMessageHandler

        handler = MCPMessageHandler()

        message = {
            "jsonrpc": "2.0",
            "id": 5,
            "method": "resources/read",
            "params": {"uri": "config://test/resource"},
        }

        response = await handler.handle(message)

        assert response["jsonrpc"] == "2.0"
        assert response["id"] == 5
        assert "result" in response
        assert "contents" in response["result"]


@pytest.mark.xdist_group(name="test_mcp_websocket")
class TestMCPWebSocketPromptsHandler:
    """Tests for MCP WebSocket prompts/* methods."""

    def teardown_method(self) -> None:
        """Force GC to prevent mock accumulation in xdist workers."""
        gc.collect()

    @pytest.mark.asyncio
    async def test_prompts_list_returns_prompts(self) -> None:
        """
        GIVEN an MCPMessageHandler instance
        WHEN handling prompts/list message
        THEN should return list of available prompts.
        """
        from mcp_server_langgraph.api.v1.mcp_websocket import MCPMessageHandler

        handler = MCPMessageHandler()

        message = {
            "jsonrpc": "2.0",
            "id": 6,
            "method": "prompts/list",
            "params": {},
        }

        response = await handler.handle(message)

        assert response["jsonrpc"] == "2.0"
        assert response["id"] == 6
        assert "result" in response
        assert "prompts" in response["result"]

    @pytest.mark.asyncio
    async def test_prompts_get_returns_messages(self) -> None:
        """
        GIVEN an MCPMessageHandler instance
        WHEN handling prompts/get message
        THEN should return prompt messages.
        """
        from mcp_server_langgraph.api.v1.mcp_websocket import MCPMessageHandler

        handler = MCPMessageHandler()

        message = {
            "jsonrpc": "2.0",
            "id": 7,
            "method": "prompts/get",
            "params": {
                "name": "code_review",
                "arguments": {"code": "def hello(): pass", "language": "python"},
            },
        }

        response = await handler.handle(message)

        assert response["jsonrpc"] == "2.0"
        assert response["id"] == 7
        assert "result" in response
        assert "messages" in response["result"]


@pytest.mark.xdist_group(name="test_mcp_websocket")
class TestMCPWebSocketStreamingExtensions:
    """Tests for MCP WebSocket streaming extensions."""

    def teardown_method(self) -> None:
        """Force GC to prevent mock accumulation in xdist workers."""
        gc.collect()

    @pytest.mark.asyncio
    async def test_streaming_start_notification(self) -> None:
        """
        GIVEN an MCPMessageHandler instance
        WHEN starting a streaming tool call
        THEN should emit $/streaming/start notification.
        """
        from mcp_server_langgraph.api.v1.mcp_websocket import MCPMessageHandler

        handler = MCPMessageHandler()

        # Create streaming notification
        notification = handler.create_streaming_start_notification(stream_id="stream-123", tool_call_id=3)

        assert notification["jsonrpc"] == "2.0"
        assert "id" not in notification  # Notifications have no id
        assert notification["method"] == "$/streaming/start"
        assert notification["params"]["streamId"] == "stream-123"

    @pytest.mark.asyncio
    async def test_streaming_chunk_notification(self) -> None:
        """
        GIVEN an MCPMessageHandler instance
        WHEN streaming a chunk
        THEN should emit $/streaming/chunk notification.
        """
        from mcp_server_langgraph.api.v1.mcp_websocket import MCPMessageHandler

        handler = MCPMessageHandler()

        notification = handler.create_streaming_chunk_notification(
            stream_id="stream-123",
            content={"type": "text", "text": "Partial..."},
        )

        assert notification["method"] == "$/streaming/chunk"
        assert notification["params"]["streamId"] == "stream-123"
        assert notification["params"]["content"]["type"] == "text"

    @pytest.mark.asyncio
    async def test_streaming_end_notification(self) -> None:
        """
        GIVEN an MCPMessageHandler instance
        WHEN ending a stream
        THEN should emit $/streaming/end notification.
        """
        from mcp_server_langgraph.api.v1.mcp_websocket import MCPMessageHandler

        handler = MCPMessageHandler()

        notification = handler.create_streaming_end_notification(stream_id="stream-123")

        assert notification["method"] == "$/streaming/end"
        assert notification["params"]["streamId"] == "stream-123"


@pytest.mark.xdist_group(name="test_mcp_websocket")
class TestMCPWebSocketTraceExtensions:
    """Tests for MCP WebSocket trace extensions."""

    def teardown_method(self) -> None:
        """Force GC to prevent mock accumulation in xdist workers."""
        gc.collect()

    def test_trace_span_notification(self) -> None:
        """
        GIVEN an MCPMessageHandler instance
        WHEN creating a trace span notification
        THEN should emit $/trace/span notification with OpenTelemetry data.
        """
        from mcp_server_langgraph.api.v1.mcp_websocket import MCPMessageHandler

        handler = MCPMessageHandler()

        notification = handler.create_trace_span_notification(
            trace_id="abc123",
            span_id="def456",
            name="tools/call",
            start_time="2025-01-01T00:00:00Z",
            end_time="2025-01-01T00:00:01Z",
            status="OK",
            attributes={"tool.name": "test-tool"},
        )

        assert notification["method"] == "$/trace/span"
        assert notification["params"]["traceId"] == "abc123"
        assert notification["params"]["spanId"] == "def456"
        assert notification["params"]["name"] == "tools/call"
        assert notification["params"]["status"] == "OK"

    def test_trace_event_notification(self) -> None:
        """
        GIVEN an MCPMessageHandler instance
        WHEN creating a trace event notification
        THEN should emit $/trace/event notification.
        """
        from mcp_server_langgraph.api.v1.mcp_websocket import MCPMessageHandler

        handler = MCPMessageHandler()

        notification = handler.create_trace_event_notification(
            span_id="def456",
            name="llm.completion",
            timestamp="2025-01-01T00:00:00.500Z",
            attributes={"llm.model": "gpt-4"},
        )

        assert notification["method"] == "$/trace/event"
        assert notification["params"]["spanId"] == "def456"
        assert notification["params"]["name"] == "llm.completion"


@pytest.mark.xdist_group(name="test_mcp_websocket")
class TestMCPWebSocketConnection:
    """Tests for MCP WebSocket connection handling."""

    def teardown_method(self) -> None:
        """Force GC to prevent mock accumulation in xdist workers."""
        gc.collect()

    def test_connection_manager_exists(self) -> None:
        """
        GIVEN the MCP WebSocket module
        WHEN importing
        THEN should have ConnectionManager for managing WebSocket connections.
        """
        from mcp_server_langgraph.api.v1.mcp_websocket import ConnectionManager

        manager = ConnectionManager()
        assert hasattr(manager, "connect")
        assert hasattr(manager, "disconnect")
        assert hasattr(manager, "broadcast")

    @pytest.mark.asyncio
    async def test_connection_manager_tracks_connections(self) -> None:
        """
        GIVEN a ConnectionManager
        WHEN a connection is added
        THEN should track the connection.
        """
        from mcp_server_langgraph.api.v1.mcp_websocket import ConnectionManager

        manager = ConnectionManager()
        mock_websocket = AsyncMock(spec=WebSocket)

        await manager.connect(mock_websocket, session_id="test-session")

        assert manager.get_connection_count() == 1
        assert manager.has_connection("test-session")

    @pytest.mark.asyncio
    async def test_connection_manager_removes_on_disconnect(self) -> None:
        """
        GIVEN a ConnectionManager with an active connection
        WHEN disconnecting
        THEN should remove the connection.
        """
        from mcp_server_langgraph.api.v1.mcp_websocket import ConnectionManager

        manager = ConnectionManager()
        mock_websocket = AsyncMock(spec=WebSocket)

        await manager.connect(mock_websocket, session_id="test-session")
        manager.disconnect("test-session")

        assert manager.get_connection_count() == 0
        assert not manager.has_connection("test-session")

    @pytest.mark.asyncio
    async def test_connection_manager_sends_to_session(self) -> None:
        """
        GIVEN a ConnectionManager with an active connection
        WHEN sending a message to a session
        THEN should send via the WebSocket.
        """
        from mcp_server_langgraph.api.v1.mcp_websocket import ConnectionManager

        manager = ConnectionManager()
        mock_websocket = AsyncMock(spec=WebSocket)

        await manager.connect(mock_websocket, session_id="test-session")
        await manager.send_to_session("test-session", {"jsonrpc": "2.0", "method": "test"})

        mock_websocket.send_json.assert_called_once()
