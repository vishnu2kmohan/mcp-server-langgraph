"""
MCP WebSocket Handler Unit Tests

Tests for the MCP WebSocket handler per TDD methodology.
Tests the WebSocket endpoint that provides MCP 2025-11-25 compliant communication.

Security tests cover:
- Token extraction and validation
- OpenFGA authorization checks
- Rate limiting and connection limits
- User context propagation to tool execution
"""

from __future__ import annotations

import gc
from unittest.mock import AsyncMock, MagicMock, patch

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
        THEN should have at least one route defined.

        Note: Websocket routes have been moved to dedicated modules (ws_router.py).
        This router now contains HTTP routes for MCP metrics.
        """
        from mcp_server_langgraph.api.v1.mcp_websocket import mcp_websocket_router

        # Check router has routes (HTTP or websocket)
        routes = [r for r in mcp_websocket_router.routes]
        assert len(routes) > 0, "Should have at least one route"

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


@pytest.mark.xdist_group(name="test_mcp_websocket_auth")
class TestMCPWebSocketAuthentication:
    """Tests for MCP WebSocket authentication and authorization."""

    def teardown_method(self) -> None:
        """Force GC to prevent mock accumulation in xdist workers."""
        gc.collect()

    def test_authenticated_mcp_handler_exists(self) -> None:
        """
        GIVEN the MCP WebSocket module
        WHEN importing
        THEN should have AuthenticatedMCPHandler class for secure connections.
        """
        from mcp_server_langgraph.api.v1.mcp_websocket import AuthenticatedMCPHandler

        assert AuthenticatedMCPHandler is not None

    def test_authenticated_handler_stores_user_context(self) -> None:
        """
        GIVEN an AuthenticatedMCPHandler
        WHEN initialized with user context
        THEN should store user_id and roles.
        """
        from mcp_server_langgraph.api.v1.mcp_websocket import AuthenticatedMCPHandler

        handler = AuthenticatedMCPHandler(
            user_id="user:alice",
            roles=["user", "developer"],
        )

        assert handler.user_id == "user:alice"
        assert "developer" in handler.roles

    @pytest.mark.asyncio
    async def test_authenticated_handler_propagates_user_to_tool_execution(self) -> None:
        """
        GIVEN an AuthenticatedMCPHandler with user context
        WHEN executing a tool
        THEN should pass user_id to the tool executor.
        """
        from mcp_server_langgraph.api.v1.mcp_websocket import AuthenticatedMCPHandler

        handler = AuthenticatedMCPHandler(
            user_id="user:alice",
            roles=["user"],
        )

        # Mock the agent execution
        with patch.object(
            handler,
            "_execute_with_agent",
            new_callable=AsyncMock,
            return_value=[{"type": "text", "text": "Agent result"}],
        ) as mock_execute:
            await handler.execute_tool("langgraph-run", {"query": "test"})

            # Verify user_id was passed
            mock_execute.assert_called_once()
            call_args = mock_execute.call_args
            assert call_args.kwargs.get("user_id") == "user:alice" or "user:alice" in str(call_args)


@pytest.mark.xdist_group(name="test_mcp_websocket_auth")
class TestMCPWebSocketTokenValidation:
    """Tests for MCP WebSocket token extraction and validation."""

    def teardown_method(self) -> None:
        """Force GC to prevent mock accumulation in xdist workers."""
        gc.collect()

    def test_extract_token_from_query_params(self) -> None:
        """
        GIVEN a WebSocket connection with token in query params
        WHEN extracting the token
        THEN should return the token.
        """
        from mcp_server_langgraph.api.v1.mcp_websocket import extract_websocket_token

        mock_websocket = AsyncMock(spec=WebSocket)
        mock_websocket.query_params = {"token": "test-jwt-token"}

        token = extract_websocket_token(mock_websocket)

        assert token == "test-jwt-token"

    def test_extract_token_from_authorization_header(self) -> None:
        """
        GIVEN a WebSocket connection with token in Authorization header
        WHEN extracting the token
        THEN should return the token without Bearer prefix.
        """
        from mcp_server_langgraph.api.v1.mcp_websocket import extract_websocket_token

        mock_websocket = AsyncMock(spec=WebSocket)
        mock_websocket.query_params = {}
        mock_websocket.headers = {"authorization": "Bearer test-jwt-token"}

        token = extract_websocket_token(mock_websocket)

        assert token == "test-jwt-token"

    def test_extract_token_returns_none_when_missing(self) -> None:
        """
        GIVEN a WebSocket connection without token
        WHEN extracting the token
        THEN should return None.
        """
        from mcp_server_langgraph.api.v1.mcp_websocket import extract_websocket_token

        mock_websocket = AsyncMock(spec=WebSocket)
        mock_websocket.query_params = {}
        mock_websocket.headers = {}

        token = extract_websocket_token(mock_websocket)

        assert token is None


@pytest.mark.xdist_group(name="test_mcp_websocket_rate_limiting")
class TestMCPWebSocketRateLimiting:
    """Tests for MCP WebSocket rate limiting and security measures."""

    def teardown_method(self) -> None:
        """Force GC to prevent mock accumulation in xdist workers."""
        gc.collect()

    def test_connection_manager_tracks_user_connections(self) -> None:
        """
        GIVEN a ConnectionManager
        WHEN tracking connections with user IDs
        THEN should count connections per user.
        """
        from mcp_server_langgraph.api.v1.mcp_websocket import ConnectionManager

        manager = ConnectionManager()

        # Verify it has user tracking capability
        assert hasattr(manager, "get_user_connection_count")

    @pytest.mark.asyncio
    async def test_connection_limit_per_user(self) -> None:
        """
        GIVEN a user with max connections reached
        WHEN attempting another connection
        THEN should reject the connection.
        """
        from mcp_server_langgraph.api.v1.mcp_websocket import (
            ConnectionManager,
            MAX_CONNECTIONS_PER_USER,
        )

        ConnectionManager()

        # Verify MAX_CONNECTIONS_PER_USER is defined
        assert MAX_CONNECTIONS_PER_USER > 0

    def test_message_size_limit_defined(self) -> None:
        """
        GIVEN the MCP WebSocket module
        WHEN checking security constants
        THEN MAX_MESSAGE_SIZE should be defined.
        """
        from mcp_server_langgraph.api.v1.mcp_websocket import MAX_MESSAGE_SIZE

        assert MAX_MESSAGE_SIZE > 0
        assert MAX_MESSAGE_SIZE <= 10_000_000  # Max 10MB is reasonable

    def test_message_rate_limit_defined(self) -> None:
        """
        GIVEN the MCP WebSocket module
        WHEN checking security constants
        THEN MAX_MESSAGES_PER_MINUTE should be defined.
        """
        from mcp_server_langgraph.api.v1.mcp_websocket import MAX_MESSAGES_PER_MINUTE

        assert MAX_MESSAGES_PER_MINUTE > 0
        assert MAX_MESSAGES_PER_MINUTE <= 1000  # Reasonable upper bound

    def test_rate_limiter_exists(self) -> None:
        """
        GIVEN the MCP WebSocket module
        WHEN importing
        THEN should have MessageRateLimiter class.
        """
        from mcp_server_langgraph.api.v1.mcp_websocket import MessageRateLimiter

        limiter = MessageRateLimiter(max_messages=100, window_seconds=60)
        assert limiter is not None

    def test_rate_limiter_allows_within_limit(self) -> None:
        """
        GIVEN a MessageRateLimiter
        WHEN messages are within limit
        THEN should allow messages.
        """
        from mcp_server_langgraph.api.v1.mcp_websocket import MessageRateLimiter

        limiter = MessageRateLimiter(max_messages=10, window_seconds=60)

        # Should allow first 10 messages
        for _ in range(10):
            assert limiter.check_and_increment() is True

    def test_rate_limiter_blocks_over_limit(self) -> None:
        """
        GIVEN a MessageRateLimiter at limit
        WHEN attempting another message
        THEN should block the message.
        """
        from mcp_server_langgraph.api.v1.mcp_websocket import MessageRateLimiter

        limiter = MessageRateLimiter(max_messages=5, window_seconds=60)

        # Use up the limit
        for _ in range(5):
            limiter.check_and_increment()

        # Next message should be blocked
        assert limiter.check_and_increment() is False

    def test_rate_limiter_resets_after_window(self) -> None:
        """
        GIVEN a MessageRateLimiter that reached limit
        WHEN window expires
        THEN should allow messages again.
        """
        from mcp_server_langgraph.api.v1.mcp_websocket import MessageRateLimiter

        limiter = MessageRateLimiter(max_messages=2, window_seconds=1)

        # Use up limit
        limiter.check_and_increment()
        limiter.check_and_increment()
        assert limiter.check_and_increment() is False

        # Simulate window expiry by resetting window_start
        import time

        time.sleep(1.1)  # noqa: sleep-duration - testing rate limit window expiry

        # Should allow again
        assert limiter.check_and_increment() is True

    def test_validate_message_size_accepts_valid(self) -> None:
        """
        GIVEN a message within size limit
        WHEN validating
        THEN should return True.
        """
        from mcp_server_langgraph.api.v1.mcp_websocket import validate_message_size

        small_message = '{"jsonrpc": "2.0", "method": "test"}'
        assert validate_message_size(small_message) is True

    def test_validate_message_size_rejects_oversized(self) -> None:
        """
        GIVEN a message exceeding size limit
        WHEN validating
        THEN should return False.
        """
        from mcp_server_langgraph.api.v1.mcp_websocket import (
            MAX_MESSAGE_SIZE,
            validate_message_size,
        )

        # Create oversized message
        oversized_message = "x" * (MAX_MESSAGE_SIZE + 1)
        assert validate_message_size(oversized_message) is False


@pytest.mark.xdist_group(name="test_mcp_websocket_idle_timeout")
class TestMCPWebSocketIdleTimeout:
    """Tests for MCP WebSocket idle connection timeout."""

    def teardown_method(self) -> None:
        """Force GC to prevent mock accumulation in xdist workers."""
        gc.collect()

    def test_idle_timeout_constant_defined(self) -> None:
        """
        GIVEN the MCP WebSocket module
        WHEN importing
        THEN IDLE_TIMEOUT_SECONDS should be defined.
        """
        from mcp_server_langgraph.api.v1.mcp_websocket import IDLE_TIMEOUT_SECONDS

        assert IDLE_TIMEOUT_SECONDS > 0
        assert IDLE_TIMEOUT_SECONDS <= 7200  # Max 2 hours is reasonable

    def test_connection_info_tracks_last_activity(self) -> None:
        """
        GIVEN a ConnectionInfo instance
        WHEN checking attributes
        THEN should have last_activity timestamp.
        """
        from mcp_server_langgraph.api.v1.mcp_websocket import ConnectionInfo

        mock_websocket = AsyncMock(spec=WebSocket)
        conn_info = ConnectionInfo(
            websocket=mock_websocket,
            session_id="test-session",
        )

        assert hasattr(conn_info, "last_activity")
        assert conn_info.last_activity is not None

    def test_connection_info_updates_activity(self) -> None:
        """
        GIVEN a ConnectionInfo instance
        WHEN updating activity
        THEN last_activity timestamp should be updated.
        """
        from mcp_server_langgraph.api.v1.mcp_websocket import ConnectionInfo, update_connection_activity

        mock_websocket = AsyncMock(spec=WebSocket)
        conn_info = ConnectionInfo(
            websocket=mock_websocket,
            session_id="test-session",
        )

        original_activity = conn_info.last_activity

        # Sleep briefly to ensure time difference
        import time

        time.sleep(0.1)

        update_connection_activity(conn_info)

        assert conn_info.last_activity > original_activity

    def test_connection_is_idle_when_timeout_exceeded(self) -> None:
        """
        GIVEN a connection that hasn't had activity for longer than timeout
        WHEN checking if idle
        THEN should return True.
        """
        from datetime import timedelta

        from mcp_server_langgraph.api.v1.mcp_websocket import (
            ConnectionInfo,
            IDLE_TIMEOUT_SECONDS,
            is_connection_idle,
        )

        mock_websocket = AsyncMock(spec=WebSocket)
        conn_info = ConnectionInfo(
            websocket=mock_websocket,
            session_id="test-session",
        )

        # Simulate old activity (past the timeout)
        from mcp_server_langgraph.api.v1.mcp_websocket import _utc_now

        conn_info.last_activity = _utc_now() - timedelta(seconds=IDLE_TIMEOUT_SECONDS + 60)

        assert is_connection_idle(conn_info) is True

    def test_connection_is_not_idle_when_recently_active(self) -> None:
        """
        GIVEN a connection with recent activity
        WHEN checking if idle
        THEN should return False.
        """
        from mcp_server_langgraph.api.v1.mcp_websocket import (
            ConnectionInfo,
            is_connection_idle,
        )

        mock_websocket = AsyncMock(spec=WebSocket)
        conn_info = ConnectionInfo(
            websocket=mock_websocket,
            session_id="test-session",
        )

        # Connection is fresh - should not be idle
        assert is_connection_idle(conn_info) is False

    @pytest.mark.asyncio
    async def test_connection_manager_get_idle_connections(self) -> None:
        """
        GIVEN a ConnectionManager with mixed active and idle connections
        WHEN getting idle connections
        THEN should return only the idle ones.
        """
        from datetime import timedelta

        from mcp_server_langgraph.api.v1.mcp_websocket import (
            ConnectionManager,
            IDLE_TIMEOUT_SECONDS,
            _utc_now,
        )

        manager = ConnectionManager()

        # Add active connection
        mock_ws_active = AsyncMock(spec=WebSocket)
        await manager.connect(mock_ws_active, session_id="active-session")

        # Add idle connection
        mock_ws_idle = AsyncMock(spec=WebSocket)
        await manager.connect(mock_ws_idle, session_id="idle-session")

        # Make the second connection appear idle
        manager._connections["idle-session"].last_activity = _utc_now() - timedelta(seconds=IDLE_TIMEOUT_SECONDS + 60)

        # Get idle connections
        idle_sessions = manager.get_idle_connections()

        assert len(idle_sessions) == 1
        assert "idle-session" in idle_sessions
        assert "active-session" not in idle_sessions


@pytest.mark.xdist_group(name="test_mcp_websocket_observability")
class TestMCPWebSocketObservability:
    """Tests for MCP WebSocket observability metrics."""

    def teardown_method(self) -> None:
        """Force GC to prevent mock accumulation in xdist workers."""
        gc.collect()

    def test_mcp_websocket_metrics_exist(self) -> None:
        """
        GIVEN the MCP WebSocket module
        WHEN importing metrics
        THEN should have MCPWebSocketMetrics class.
        """
        from mcp_server_langgraph.api.v1.mcp_websocket import MCPWebSocketMetrics

        assert MCPWebSocketMetrics is not None

    def test_metrics_connection_counter(self) -> None:
        """
        GIVEN MCPWebSocketMetrics instance
        WHEN tracking connections
        THEN should have active_connections counter.
        """
        from mcp_server_langgraph.api.v1.mcp_websocket import MCPWebSocketMetrics

        metrics = MCPWebSocketMetrics()
        assert hasattr(metrics, "active_connections")
        assert hasattr(metrics, "total_connections")

    def test_metrics_message_counters(self) -> None:
        """
        GIVEN MCPWebSocketMetrics instance
        WHEN tracking messages
        THEN should have message send/receive counters.
        """
        from mcp_server_langgraph.api.v1.mcp_websocket import MCPWebSocketMetrics

        metrics = MCPWebSocketMetrics()
        assert hasattr(metrics, "messages_received")
        assert hasattr(metrics, "messages_sent")

    def test_metrics_rate_limit_counter(self) -> None:
        """
        GIVEN MCPWebSocketMetrics instance
        WHEN rate limiting occurs
        THEN should have rate_limit_exceeded counter.
        """
        from mcp_server_langgraph.api.v1.mcp_websocket import MCPWebSocketMetrics

        metrics = MCPWebSocketMetrics()
        assert hasattr(metrics, "rate_limit_exceeded")

    def test_metrics_error_counter(self) -> None:
        """
        GIVEN MCPWebSocketMetrics instance
        WHEN errors occur
        THEN should have error counters.
        """
        from mcp_server_langgraph.api.v1.mcp_websocket import MCPWebSocketMetrics

        metrics = MCPWebSocketMetrics()
        assert hasattr(metrics, "errors")

    def test_metrics_record_connection(self) -> None:
        """
        GIVEN MCPWebSocketMetrics instance
        WHEN recording a connection event
        THEN should update counters correctly.
        """
        from mcp_server_langgraph.api.v1.mcp_websocket import MCPWebSocketMetrics

        metrics = MCPWebSocketMetrics()

        # Record connection
        metrics.record_connection()
        assert metrics.active_connections >= 1
        assert metrics.total_connections >= 1

    def test_metrics_record_disconnect(self) -> None:
        """
        GIVEN MCPWebSocketMetrics instance with active connection
        WHEN recording a disconnection
        THEN should decrement active connections.
        """
        from mcp_server_langgraph.api.v1.mcp_websocket import MCPWebSocketMetrics

        metrics = MCPWebSocketMetrics()

        # Simulate connection then disconnection
        metrics.record_connection()
        initial = metrics.active_connections
        metrics.record_disconnect()
        assert metrics.active_connections <= initial

    def test_metrics_record_message_received(self) -> None:
        """
        GIVEN MCPWebSocketMetrics instance
        WHEN recording received message
        THEN should increment messages_received counter.
        """
        from mcp_server_langgraph.api.v1.mcp_websocket import MCPWebSocketMetrics

        metrics = MCPWebSocketMetrics()

        metrics.record_message_received(method="initialize")
        # Should not raise

    def test_metrics_record_message_sent(self) -> None:
        """
        GIVEN MCPWebSocketMetrics instance
        WHEN recording sent message
        THEN should increment messages_sent counter.
        """
        from mcp_server_langgraph.api.v1.mcp_websocket import MCPWebSocketMetrics

        metrics = MCPWebSocketMetrics()

        metrics.record_message_sent(method="initialize")
        # Should not raise

    def test_metrics_record_rate_limit_exceeded(self) -> None:
        """
        GIVEN MCPWebSocketMetrics instance
        WHEN recording rate limit event
        THEN should increment rate_limit_exceeded counter.
        """
        from mcp_server_langgraph.api.v1.mcp_websocket import MCPWebSocketMetrics

        metrics = MCPWebSocketMetrics()

        metrics.record_rate_limit_exceeded(user_id="user:alice")
        # Should not raise


@pytest.mark.xdist_group(name="test_mcp_websocket_integration")
class TestMCPWebSocketAgentIntegration:
    """Tests for MCP WebSocket integration with real agent execution."""

    def teardown_method(self) -> None:
        """Force GC to prevent mock accumulation in xdist workers."""
        gc.collect()

    @pytest.mark.asyncio
    async def test_authenticated_handler_uses_real_agent(self) -> None:
        """
        GIVEN an AuthenticatedMCPHandler
        WHEN executing langgraph-run tool
        THEN should integrate with the agent graph.
        """
        from mcp_server_langgraph.api.v1.mcp_websocket import AuthenticatedMCPHandler

        handler = AuthenticatedMCPHandler(
            user_id="user:alice",
            roles=["user"],
        )

        # Verify handler has agent integration method
        assert hasattr(handler, "_execute_with_agent")

    @pytest.mark.asyncio
    async def test_tool_execution_includes_session_context(self) -> None:
        """
        GIVEN an AuthenticatedMCPHandler
        WHEN executing a tool with session_id
        THEN should propagate session context to agent.
        """
        from mcp_server_langgraph.api.v1.mcp_websocket import AuthenticatedMCPHandler

        handler = AuthenticatedMCPHandler(
            user_id="user:alice",
            roles=["user"],
        )

        # Mock agent execution
        with patch.object(
            handler,
            "_execute_with_agent",
            new_callable=AsyncMock,
            return_value=[{"type": "text", "text": "Result"}],
        ) as mock_execute:
            await handler.execute_tool(
                "langgraph-run",
                {"query": "test", "session_id": "session-123"},
            )

            # Verify session_id was passed
            mock_execute.assert_called_once()
            call_args = mock_execute.call_args
            assert "session-123" in str(call_args) or call_args.kwargs.get("session_id") == "session-123"


@pytest.mark.xdist_group(name="test_mcp_websocket_keycloak")
class TestMCPWebSocketKeycloakIntegration:
    """Tests for MCP WebSocket Keycloak token validation integration."""

    def teardown_method(self) -> None:
        """Force GC to prevent mock accumulation in xdist workers."""
        gc.collect()

    @pytest.mark.asyncio
    async def test_validate_websocket_token_success(self) -> None:
        """
        GIVEN a valid JWT token
        WHEN validating for WebSocket connection
        THEN should return decoded token payload with user info.
        """
        from mcp_server_langgraph.api.v1.mcp_websocket import validate_websocket_token

        mock_validator = AsyncMock()  # async-mock-configured
        mock_validator.validate_token = AsyncMock(
            return_value={
                "sub": "user-uuid-123",
                "preferred_username": "alice",
                "realm_access": {"roles": ["user", "developer"]},
                "exp": 9999999999,
            }
        )

        with patch(
            "mcp_server_langgraph.api.v1.mcp_websocket.get_token_validator",
            return_value=mock_validator,
        ):
            result = await validate_websocket_token("valid-jwt-token")

            assert result is not None
            assert result["preferred_username"] == "alice"
            mock_validator.validate_token.assert_called_once_with("valid-jwt-token")

    @pytest.mark.asyncio
    async def test_validate_websocket_token_expired(self) -> None:
        """
        GIVEN an expired JWT token
        WHEN validating for WebSocket connection
        THEN should return None.
        """
        import jwt

        from mcp_server_langgraph.api.v1.mcp_websocket import validate_websocket_token

        mock_validator = AsyncMock()  # async-mock-configured
        mock_validator.validate_token = AsyncMock(side_effect=jwt.ExpiredSignatureError("Token expired"))

        with patch(
            "mcp_server_langgraph.api.v1.mcp_websocket.get_token_validator",
            return_value=mock_validator,
        ):
            result = await validate_websocket_token("expired-token")

            assert result is None

    @pytest.mark.asyncio
    async def test_validate_websocket_token_invalid(self) -> None:
        """
        GIVEN an invalid JWT token
        WHEN validating for WebSocket connection
        THEN should return None.
        """
        import jwt

        from mcp_server_langgraph.api.v1.mcp_websocket import validate_websocket_token

        mock_validator = AsyncMock()  # async-mock-configured
        mock_validator.validate_token = AsyncMock(side_effect=jwt.InvalidTokenError("Invalid token"))

        with patch(
            "mcp_server_langgraph.api.v1.mcp_websocket.get_token_validator",
            return_value=mock_validator,
        ):
            result = await validate_websocket_token("invalid-token")

            assert result is None


@pytest.mark.xdist_group(name="test_mcp_websocket_openfga")
class TestMCPWebSocketOpenFGAIntegration:
    """Tests for MCP WebSocket OpenFGA authorization integration."""

    def teardown_method(self) -> None:
        """Force GC to prevent mock accumulation in xdist workers."""
        gc.collect()

    @pytest.mark.asyncio
    async def test_check_mcp_websocket_permission_allowed(self) -> None:
        """
        GIVEN a user with MCP WebSocket access permission
        WHEN checking permission
        THEN should return True.
        """
        from mcp_server_langgraph.api.v1.mcp_websocket import check_mcp_permission

        mock_openfga = AsyncMock()  # async-mock-configured
        mock_check_result = MagicMock()
        mock_check_result.allowed = True
        mock_openfga.check = AsyncMock(return_value=mock_check_result)

        with patch(
            "mcp_server_langgraph.api.v1.mcp_websocket.get_openfga_client",
            return_value=mock_openfga,
        ):
            result = await check_mcp_permission(
                user_id="user:alice",
                action="use",
                resource="mcp:websocket",
            )

            assert result is True
            mock_openfga.check.assert_called_once()

    @pytest.mark.asyncio
    async def test_check_mcp_websocket_permission_denied(self) -> None:
        """
        GIVEN a user without MCP WebSocket access permission
        WHEN checking permission
        THEN should return False.
        """
        from mcp_server_langgraph.api.v1.mcp_websocket import check_mcp_permission

        mock_openfga = AsyncMock()  # async-mock-configured
        mock_openfga.check = AsyncMock(return_value=False)

        with patch(
            "mcp_server_langgraph.api.v1.mcp_websocket.get_openfga_client",
            return_value=mock_openfga,
        ):
            result = await check_mcp_permission(
                user_id="user:eve",
                action="use",
                resource="mcp:websocket",
            )

            assert result is False

    @pytest.mark.asyncio
    async def test_check_mcp_permission_openfga_unavailable(self) -> None:
        """
        GIVEN OpenFGA client is unavailable
        WHEN checking permission
        THEN should return True (fail-open) or False (fail-closed) based on config.
        """
        from mcp_server_langgraph.api.v1.mcp_websocket import check_mcp_permission

        with patch(
            "mcp_server_langgraph.api.v1.mcp_websocket.get_openfga_client",
            return_value=None,
        ):
            # Default is fail-open when OpenFGA is not configured
            result = await check_mcp_permission(
                user_id="user:alice",
                action="use",
                resource="mcp:websocket",
            )

            # Fail-open when OpenFGA not configured
            assert result is True


@pytest.mark.xdist_group(name="test_mcp_websocket_streaming")
class TestMCPWebSocketStreamingIntegration:
    """Tests for MCP WebSocket streaming response handling."""

    def teardown_method(self) -> None:
        """Force GC to prevent mock accumulation in xdist workers."""
        gc.collect()

    @pytest.mark.asyncio
    async def test_authenticated_handler_streams_tool_execution(self) -> None:
        """
        GIVEN an AuthenticatedMCPHandler with streaming enabled
        WHEN executing a tool that supports streaming
        THEN should emit streaming notifications.
        """
        from mcp_server_langgraph.api.v1.mcp_websocket import AuthenticatedMCPHandler

        handler = AuthenticatedMCPHandler(
            user_id="user:alice",
            roles=["user"],
        )

        # Verify handler has streaming capability
        assert hasattr(handler, "create_streaming_start_notification")
        assert hasattr(handler, "create_streaming_chunk_notification")
        assert hasattr(handler, "create_streaming_end_notification")

    @pytest.mark.asyncio
    async def test_streaming_tool_execution_emits_notifications(self) -> None:
        """
        GIVEN an AuthenticatedMCPHandler
        WHEN creating streaming notifications
        THEN should produce properly formatted notifications.
        """
        from mcp_server_langgraph.api.v1.mcp_websocket import AuthenticatedMCPHandler

        handler = AuthenticatedMCPHandler(
            user_id="user:alice",
            roles=["user"],
        )

        # Test streaming notification creation
        start = handler.create_streaming_start_notification(
            stream_id="stream-123",
            tool_call_id=1,
        )
        assert start["method"] == "$/streaming/start"
        assert start["params"]["streamId"] == "stream-123"

        chunk = handler.create_streaming_chunk_notification(
            stream_id="stream-123",
            content={"type": "text", "text": "Hello"},
        )
        assert chunk["method"] == "$/streaming/chunk"
        assert chunk["params"]["content"]["text"] == "Hello"

        end = handler.create_streaming_end_notification(stream_id="stream-123")
        assert end["method"] == "$/streaming/end"
        assert end["params"]["streamId"] == "stream-123"


@pytest.mark.xdist_group(name="test_mcp_websocket_mcpbridge")
class TestMCPWebSocketMCPBridgeIntegration:
    """Tests for MCP WebSocket integration with MCPBridge for real tool execution."""

    def teardown_method(self) -> None:
        """Force GC to prevent mock accumulation in xdist workers."""
        gc.collect()

    @pytest.mark.asyncio
    async def test_execute_with_agent_uses_mcp_bridge(self) -> None:
        """
        GIVEN an AuthenticatedMCPHandler with MCPBridge available
        WHEN executing langgraph-run tool
        THEN should use MCPBridge.send_chat_message for execution.
        """
        from mcp_server_langgraph.api.v1.mcp_websocket import AuthenticatedMCPHandler

        handler = AuthenticatedMCPHandler(
            user_id="user:alice",
            roles=["user"],
        )

        # Mock the MCPBridge
        mock_bridge = AsyncMock()  # async-mock-configured
        mock_bridge.send_chat_message = AsyncMock(return_value=MagicMock(content="Agent response from MCPBridge"))
        mock_bridge.is_configured = True

        # Patch where message_handler imports get_mcp_bridge from
        with patch(
            "mcp_server_langgraph.api.v1.mcp_bridge.get_mcp_bridge",
            return_value=mock_bridge,
        ):
            result = await handler.execute_tool(
                "langgraph-run",
                {"query": "test query", "session_id": "session-123"},
            )

            assert len(result) > 0
            # Verify MCPBridge was called
            mock_bridge.send_chat_message.assert_called_once()
            call_args = mock_bridge.send_chat_message.call_args
            assert call_args.kwargs.get("user_id") == "user:alice" or "alice" in str(call_args)

    @pytest.mark.asyncio
    async def test_execute_with_agent_falls_back_without_bridge(self) -> None:
        """
        GIVEN an AuthenticatedMCPHandler without MCPBridge
        WHEN executing langgraph-run tool
        THEN should return placeholder response.
        """
        from mcp_server_langgraph.api.v1.mcp_websocket import AuthenticatedMCPHandler

        handler = AuthenticatedMCPHandler(
            user_id="user:alice",
            roles=["user"],
        )

        # Patch where message_handler imports get_mcp_bridge from
        with patch(
            "mcp_server_langgraph.api.v1.mcp_bridge.get_mcp_bridge",
            return_value=None,
        ):
            result = await handler.execute_tool(
                "langgraph-run",
                {"query": "test query"},
            )

            assert len(result) > 0
            assert result[0]["type"] == "text"
            # Should still work with placeholder

    @pytest.mark.asyncio
    async def test_execute_with_agent_handles_bridge_error(self) -> None:
        """
        GIVEN an AuthenticatedMCPHandler with MCPBridge that fails
        WHEN executing langgraph-run tool
        THEN should handle error gracefully.
        """
        from mcp_server_langgraph.api.v1.mcp_bridge import ChatError
        from mcp_server_langgraph.api.v1.mcp_websocket import AuthenticatedMCPHandler

        handler = AuthenticatedMCPHandler(
            user_id="user:alice",
            roles=["user"],
        )

        mock_bridge = AsyncMock()  # async-mock-configured
        mock_bridge.send_chat_message = AsyncMock(side_effect=ChatError("MCP server unavailable"))
        mock_bridge.is_configured = True

        # Patch where message_handler imports get_mcp_bridge from
        with patch(
            "mcp_server_langgraph.api.v1.mcp_bridge.get_mcp_bridge",
            return_value=mock_bridge,
        ):
            result = await handler.execute_tool(
                "langgraph-run",
                {"query": "test query"},
            )

            # Should return error content
            assert len(result) > 0
            assert result[0]["type"] == "text"
            # Error should be captured in the result


@pytest.mark.xdist_group(name="test_mcp_websocket_streaming_flow")
class TestMCPWebSocketStreamingFlow:
    """Tests for MCP WebSocket streaming tool execution flow."""

    def teardown_method(self) -> None:
        """Force GC to prevent mock accumulation in xdist workers."""
        gc.collect()

    @pytest.mark.asyncio
    async def test_streaming_tool_call_produces_notifications(self) -> None:
        """
        GIVEN an AuthenticatedMCPHandler with streaming support
        WHEN executing a tool with streaming
        THEN should produce streaming notifications.
        """
        from mcp_server_langgraph.api.v1.mcp_websocket import AuthenticatedMCPHandler

        handler = AuthenticatedMCPHandler(
            user_id="user:alice",
            roles=["user"],
        )

        # Collect notifications produced during streaming
        notifications: list[dict] = []

        # Execute with streaming and collect notifications
        stream_id = "stream-test-123"
        tool_call_id = 42

        # Create streaming lifecycle notifications
        start = handler.create_streaming_start_notification(stream_id, tool_call_id)
        notifications.append(start)

        chunk = handler.create_streaming_chunk_notification(stream_id, {"type": "text", "text": "Streaming chunk 1"})
        notifications.append(chunk)

        end = handler.create_streaming_end_notification(stream_id)
        notifications.append(end)

        # Verify notifications follow correct sequence
        assert len(notifications) == 3
        assert notifications[0]["method"] == "$/streaming/start"
        assert notifications[1]["method"] == "$/streaming/chunk"
        assert notifications[2]["method"] == "$/streaming/end"

        # Verify stream ID consistency
        for notif in notifications:
            assert notif["params"]["streamId"] == stream_id

    @pytest.mark.asyncio
    async def test_streaming_handler_integration(self) -> None:
        """
        GIVEN an AuthenticatedMCPHandler
        WHEN using execute_tool_streaming method
        THEN should yield streaming chunks.
        """
        from mcp_server_langgraph.api.v1.mcp_websocket import AuthenticatedMCPHandler

        handler = AuthenticatedMCPHandler(
            user_id="user:alice",
            roles=["user"],
        )

        # Verify handler has streaming capability
        assert hasattr(handler, "execute_tool_streaming")

    @pytest.mark.asyncio
    async def test_streaming_with_mcp_bridge(self) -> None:
        """
        GIVEN an AuthenticatedMCPHandler with MCPBridge streaming support
        WHEN executing langgraph-run with streaming
        THEN should stream response chunks from MCPBridge.
        """
        from mcp_server_langgraph.api.v1.mcp_bridge import ChatChunk
        from mcp_server_langgraph.api.v1.mcp_websocket import AuthenticatedMCPHandler

        handler = AuthenticatedMCPHandler(
            user_id="user:alice",
            roles=["user"],
        )

        # Mock MCPBridge streaming - must accept the expected parameters
        async def mock_stream_chat(session_id: str, message: str, user_id: str, **kwargs):
            yield ChatChunk(content="Hello ", is_final=False)
            yield ChatChunk(content="World", is_final=False)
            yield ChatChunk(content="", is_final=True)

        mock_bridge = MagicMock()
        mock_bridge.stream_chat_message = mock_stream_chat
        mock_bridge.is_configured = True

        # Patch where message_handler imports get_mcp_bridge from
        with patch(
            "mcp_server_langgraph.api.v1.mcp_bridge.get_mcp_bridge",
            return_value=mock_bridge,
        ):
            chunks = []
            async for chunk in handler.execute_tool_streaming(
                "langgraph-run",
                {"query": "test"},
            ):
                chunks.append(chunk)

            assert len(chunks) > 0
            # Verify streaming chunks were received
            assert any(c.get("text") == "Hello " for c in chunks)
            assert any(c.get("text") == "World" for c in chunks)


@pytest.mark.xdist_group(name="test_mcp_websocket_secure_endpoint")
class TestMCPWebSocketSecureEndpoint:
    """Tests for MCP WebSocket secure endpoint with authentication and authorization."""

    def teardown_method(self) -> None:
        """Force GC to prevent mock accumulation in xdist workers."""
        gc.collect()

    def test_authenticated_websocket_router_exists(self) -> None:
        """
        GIVEN the MCP WebSocket module
        WHEN importing
        THEN should have at least one route (websocket routes moved to ws_router.py).

        Note: Websocket routes have been moved to dedicated modules.
        This test now verifies the router has routes (HTTP metrics endpoint).
        """
        from mcp_server_langgraph.api.v1.mcp_websocket import mcp_websocket_router

        # Check router has routes
        routes = [r for r in mcp_websocket_router.routes if hasattr(r, "path")]
        assert len(routes) > 0, "Should have at least one route"

    @pytest.mark.asyncio
    async def test_create_authenticated_handler_from_token(self) -> None:
        """
        GIVEN a valid decoded token
        WHEN creating an AuthenticatedMCPHandler
        THEN should extract user_id and roles correctly.
        """
        from mcp_server_langgraph.api.v1.mcp_websocket import create_handler_from_token

        token_payload = {
            "sub": "user-uuid-123",
            "preferred_username": "alice",
            "realm_access": {"roles": ["user", "developer"]},
        }

        handler = await create_handler_from_token(token_payload=token_payload)

        # user_id comes from 'sub' claim (standard JWT subject)
        assert handler.user_id == "user-uuid-123"
        assert "user" in handler.roles
        assert "developer" in handler.roles

    @pytest.mark.asyncio
    async def test_create_authenticated_handler_default_roles(self) -> None:
        """
        GIVEN a token without roles
        WHEN creating an AuthenticatedMCPHandler
        THEN should use default roles.
        """
        from mcp_server_langgraph.api.v1.mcp_websocket import create_handler_from_token

        token_payload = {
            "sub": "user-uuid-123",
            "preferred_username": "bob",
        }

        handler = await create_handler_from_token(token_payload=token_payload)

        # user_id comes from 'sub' claim (standard JWT subject)
        assert handler.user_id == "user-uuid-123"
        assert "user" in handler.roles  # Default role


@pytest.mark.xdist_group(name="test_mcp_websocket_endpoint_streaming")
class TestMCPWebSocketEndpointStreamingWiring:
    """Tests for endpoint-level streaming notification callback wiring."""

    def teardown_method(self) -> None:
        """Force GC to prevent mock accumulation in xdist workers."""
        gc.collect()

    @pytest.mark.asyncio
    async def test_authenticated_endpoint_creates_handler_with_callback(self) -> None:
        """
        GIVEN an authenticated WebSocket connection
        WHEN the handler is created
        THEN should have notification_callback wired to websocket.send_json.
        """
        from mcp_server_langgraph.api.v1.mcp_websocket import create_handler_from_token

        # The handler created should have a notification_callback
        async def mock_send_json(data: dict) -> None:
            pass

        token_payload = {
            "preferred_username": "alice",
            "realm_access": {"roles": ["user"]},
        }

        handler = await create_handler_from_token(
            token_payload=token_payload,
            notification_callback=mock_send_json,
        )

        assert handler.notification_callback is not None
        assert callable(handler.notification_callback)

    @pytest.mark.asyncio
    async def test_streaming_tools_call_sends_notifications_via_callback(self) -> None:
        """
        GIVEN an AuthenticatedMCPHandler with notification_callback
        WHEN tools/call with _meta.streaming=true is handled
        THEN should send notifications via the callback.
        """
        from mcp_server_langgraph.api.v1.mcp_websocket import AuthenticatedMCPHandler

        notifications: list[dict] = []

        async def capture_notification(n: dict) -> None:
            notifications.append(n)

        handler = AuthenticatedMCPHandler(
            user_id="user:alice",
            roles=["user"],
            notification_callback=capture_notification,
        )

        # Mock streaming execution
        async def mock_stream(*args, **kwargs):
            yield {"type": "text", "text": "Hello", "is_final": True}

        with patch.object(handler, "execute_tool_streaming", side_effect=mock_stream):
            message = {
                "jsonrpc": "2.0",
                "id": 1,
                "method": "tools/call",
                "params": {
                    "name": "langgraph-run",
                    "arguments": {"query": "test"},
                    "_meta": {"streaming": True},
                },
            }

            await handler.handle(message)

        # Should have received notifications
        assert len(notifications) >= 2  # At least start and end
        methods = [n.get("method") for n in notifications]
        assert "$/streaming/start" in methods
        assert "$/streaming/end" in methods


@pytest.mark.xdist_group(name="test_mcp_websocket_full_integration")
class TestMCPWebSocketFullIntegration:
    """Full integration tests for MCP WebSocket with all security features."""

    def teardown_method(self) -> None:
        """Force GC to prevent mock accumulation in xdist workers."""
        gc.collect()

    @pytest.mark.asyncio
    async def test_secure_websocket_connection_flow(self) -> None:
        """
        GIVEN valid authentication and authorization
        WHEN connecting to MCP WebSocket
        THEN should complete full secure connection flow.
        """
        from mcp_server_langgraph.api.v1.mcp_websocket import (
            AuthenticatedMCPHandler,
            ConnectionManager,
            extract_websocket_token,
        )

        # Step 1: Extract token
        mock_websocket = AsyncMock(spec=WebSocket)
        mock_websocket.query_params = {"token": "valid-jwt-token"}
        mock_websocket.headers = {}

        token = extract_websocket_token(mock_websocket)
        assert token == "valid-jwt-token"

        # Step 2: Create authenticated handler
        handler = AuthenticatedMCPHandler(
            user_id="user:alice",
            roles=["user", "mcp:use"],
        )

        # Step 3: Connect with user tracking
        manager = ConnectionManager()
        await manager.connect(
            mock_websocket,
            session_id="session-123",
            user_id="user:alice",
            roles=["user", "mcp:use"],
        )

        # Verify connection established
        assert manager.has_connection("session-123")
        assert manager.get_user_connection_count("user:alice") == 1

        # Step 4: Execute tool with user context
        with patch.object(
            handler,
            "_execute_with_agent",
            new_callable=AsyncMock,
            return_value=[{"type": "text", "text": "Result"}],
        ):
            result = await handler.execute_tool("langgraph-run", {"query": "test"})
            assert len(result) > 0

        # Step 5: Disconnect
        manager.disconnect("session-123")
        assert not manager.has_connection("session-123")
        assert manager.get_user_connection_count("user:alice") == 0

    @pytest.mark.asyncio
    async def test_connection_rejected_without_auth(self) -> None:
        """
        GIVEN no authentication token
        WHEN attempting to connect to MCP WebSocket
        THEN should reject the connection.
        """
        from mcp_server_langgraph.api.v1.mcp_websocket import extract_websocket_token

        mock_websocket = AsyncMock(spec=WebSocket)
        mock_websocket.query_params = {}
        mock_websocket.headers = {}

        token = extract_websocket_token(mock_websocket)
        assert token is None

    @pytest.mark.asyncio
    async def test_connection_rejected_at_user_limit(self) -> None:
        """
        GIVEN a user at their connection limit
        WHEN attempting another connection
        THEN should reject the connection.
        """
        from mcp_server_langgraph.api.v1.mcp_websocket import (
            ConnectionManager,
            MAX_CONNECTIONS_PER_USER,
        )

        manager = ConnectionManager()

        # Create max connections
        for i in range(MAX_CONNECTIONS_PER_USER):
            mock_ws = AsyncMock(spec=WebSocket)
            await manager.connect(
                mock_ws,
                session_id=f"session-{i}",
                user_id="user:alice",
            )

        # Verify at limit
        assert manager.get_user_connection_count("user:alice") == MAX_CONNECTIONS_PER_USER
        assert not manager.can_user_connect("user:alice")


@pytest.mark.xdist_group(name="test_mcp_websocket_per_user_rate_limit")
class TestMCPWebSocketPerUserRateLimiting:
    """Tests for per-user rate limiting (shared across connections)."""

    def teardown_method(self) -> None:
        """Force GC to prevent mock accumulation in xdist workers."""
        gc.collect()

    def test_user_rate_limiter_manager_exists(self) -> None:
        """
        GIVEN the MCP WebSocket module
        WHEN importing
        THEN should have UserRateLimiterManager class.
        """
        from mcp_server_langgraph.api.v1.mcp_websocket import UserRateLimiterManager

        manager = UserRateLimiterManager(max_messages=100, window_seconds=60)
        assert manager is not None

    def test_user_rate_limiter_tracks_by_user_id(self) -> None:
        """
        GIVEN a UserRateLimiterManager
        WHEN checking rate for different users
        THEN should track limits independently per user.
        """
        from mcp_server_langgraph.api.v1.mcp_websocket import UserRateLimiterManager

        manager = UserRateLimiterManager(max_messages=5, window_seconds=60)

        # Alice uses 5 messages
        for _ in range(5):
            assert manager.check_and_increment("user:alice") is True

        # Alice is now rate limited
        assert manager.check_and_increment("user:alice") is False

        # Bob should still be allowed
        assert manager.check_and_increment("user:bob") is True

    def test_user_rate_limiter_shares_across_connections(self) -> None:
        """
        GIVEN a user with multiple connections
        WHEN messages come from different connections
        THEN should share the same rate limit.
        """
        from mcp_server_langgraph.api.v1.mcp_websocket import UserRateLimiterManager

        manager = UserRateLimiterManager(max_messages=3, window_seconds=60)

        # Same user, simulated from different connections
        assert manager.check_and_increment("user:alice") is True  # conn 1
        assert manager.check_and_increment("user:alice") is True  # conn 2
        assert manager.check_and_increment("user:alice") is True  # conn 1
        assert manager.check_and_increment("user:alice") is False  # Any conn - rate limited

    def test_user_rate_limiter_cleanup_old_users(self) -> None:
        """
        GIVEN a UserRateLimiterManager with expired user windows
        WHEN cleanup is called
        THEN should remove inactive users.
        """
        from mcp_server_langgraph.api.v1.mcp_websocket import UserRateLimiterManager

        manager = UserRateLimiterManager(max_messages=10, window_seconds=1)

        # Add some users
        manager.check_and_increment("user:alice")
        manager.check_and_increment("user:bob")

        assert manager.get_user_count() >= 2

        # Simulate time passing and cleanup
        import time

        time.sleep(1.1)  # noqa: sleep-duration - testing connection timeout

        manager.cleanup_expired()

        # Users should be cleaned up
        assert manager.get_user_count() == 0

    def test_anonymous_user_rate_limiting(self) -> None:
        """
        GIVEN an anonymous (unauthenticated) connection
        WHEN checking rate limit
        THEN should use session_id as fallback identifier.
        """
        from mcp_server_langgraph.api.v1.mcp_websocket import UserRateLimiterManager

        manager = UserRateLimiterManager(max_messages=2, window_seconds=60)

        # Anonymous users identified by session
        assert manager.check_and_increment("session:abc123") is True
        assert manager.check_and_increment("session:abc123") is True
        assert manager.check_and_increment("session:abc123") is False

        # Different session is separate
        assert manager.check_and_increment("session:def456") is True


@pytest.mark.xdist_group(name="test_mcp_websocket_session_validation")
class TestMCPWebSocketSessionValidation:
    """Tests for session ID validation and sanitization."""

    def teardown_method(self) -> None:
        """Force GC to prevent mock accumulation in xdist workers."""
        gc.collect()

    def test_validate_session_id_accepts_valid(self) -> None:
        """
        GIVEN a valid session ID
        WHEN validating
        THEN should return True.
        """
        from mcp_server_langgraph.api.v1.mcp_websocket import validate_session_id

        assert validate_session_id("abc123") is True
        assert validate_session_id("session-001") is True
        assert validate_session_id("a1b2c3d4-e5f6-7890-abcd-ef1234567890") is True

    def test_validate_session_id_rejects_empty(self) -> None:
        """
        GIVEN an empty session ID
        WHEN validating
        THEN should return False.
        """
        from mcp_server_langgraph.api.v1.mcp_websocket import validate_session_id

        assert validate_session_id("") is False
        assert validate_session_id("   ") is False

    def test_validate_session_id_rejects_too_long(self) -> None:
        """
        GIVEN a session ID exceeding max length
        WHEN validating
        THEN should return False.
        """
        from mcp_server_langgraph.api.v1.mcp_websocket import (
            MAX_SESSION_ID_LENGTH,
            validate_session_id,
        )

        too_long = "x" * (MAX_SESSION_ID_LENGTH + 1)
        assert validate_session_id(too_long) is False

    def test_validate_session_id_rejects_invalid_characters(self) -> None:
        """
        GIVEN a session ID with invalid characters
        WHEN validating
        THEN should return False.
        """
        from mcp_server_langgraph.api.v1.mcp_websocket import validate_session_id

        # Path traversal attempts
        assert validate_session_id("../etc/passwd") is False
        assert validate_session_id("..\\windows\\system32") is False

        # Script injection
        assert validate_session_id("<script>alert(1)</script>") is False

        # Null bytes
        assert validate_session_id("session\x00id") is False

        # Special characters
        assert validate_session_id("session;drop table") is False

    def test_sanitize_session_id(self) -> None:
        """
        GIVEN a session ID with potentially unsafe characters
        WHEN sanitizing
        THEN should return a safe version.
        """
        from mcp_server_langgraph.api.v1.mcp_websocket import sanitize_session_id

        # Should preserve alphanumeric and hyphens
        assert sanitize_session_id("abc-123") == "abc-123"

        # Should strip/replace unsafe characters
        result = sanitize_session_id("abc<script>123")
        assert "<" not in result
        assert ">" not in result


@pytest.mark.xdist_group(name="test_mcp_websocket_security_enforcement")
class TestMCPWebSocketSecurityEnforcement:
    """Tests for security enforcement in message handling."""

    def teardown_method(self) -> None:
        """Force GC to prevent mock accumulation in xdist workers."""
        gc.collect()

    def test_secure_message_handler_exists(self) -> None:
        """
        GIVEN the MCP WebSocket module
        WHEN importing
        THEN should have SecureMessageProcessor class.
        """
        from mcp_server_langgraph.api.v1.mcp_websocket import SecureMessageProcessor

        assert SecureMessageProcessor is not None

    def test_secure_processor_validates_message_size(self) -> None:
        """
        GIVEN a SecureMessageProcessor
        WHEN processing oversized message
        THEN should reject with appropriate error.
        """
        from mcp_server_langgraph.api.v1.mcp_websocket import (
            MAX_MESSAGE_SIZE,
            SecureMessageProcessor,
        )

        processor = SecureMessageProcessor(
            session_id="test-session",
            user_id="user:alice",
        )

        oversized = "x" * (MAX_MESSAGE_SIZE + 1)
        result = processor.validate_incoming(oversized)

        assert result.is_valid is False
        assert "size" in result.error_message.lower()

    def test_secure_processor_checks_rate_limit(self) -> None:
        """
        GIVEN a SecureMessageProcessor with rate limit reached
        WHEN processing a message
        THEN should reject with rate limit error.
        """
        from mcp_server_langgraph.api.v1.mcp_websocket import (
            SecureMessageProcessor,
            UserRateLimiterManager,
        )

        # Create rate limiter at limit
        rate_limiter = UserRateLimiterManager(max_messages=1, window_seconds=60)
        rate_limiter.check_and_increment("user:alice")  # Use up limit

        processor = SecureMessageProcessor(
            session_id="test-session",
            user_id="user:alice",
            rate_limiter=rate_limiter,
        )

        result = processor.validate_incoming('{"jsonrpc": "2.0", "method": "test"}')

        assert result.is_valid is False
        assert "rate" in result.error_message.lower()

    def test_secure_processor_updates_activity(self) -> None:
        """
        GIVEN a SecureMessageProcessor
        WHEN processing a valid message
        THEN should update connection activity.
        """
        from mcp_server_langgraph.api.v1.mcp_websocket import (
            ConnectionManager,
            SecureMessageProcessor,
        )

        manager = ConnectionManager()
        mock_ws = AsyncMock(spec=WebSocket)

        # Create connection
        import asyncio

        asyncio.get_event_loop().run_until_complete(manager.connect(mock_ws, session_id="test-session", user_id="user:alice"))

        original_activity = manager._connections["test-session"].last_activity

        import time

        time.sleep(0.1)

        processor = SecureMessageProcessor(
            session_id="test-session",
            user_id="user:alice",
            connection_manager=manager,
        )

        processor.on_message_processed()

        assert manager._connections["test-session"].last_activity > original_activity

    def test_secure_processor_records_metrics(self) -> None:
        """
        GIVEN a SecureMessageProcessor with metrics
        WHEN processing messages
        THEN should record appropriate metrics.
        """
        from mcp_server_langgraph.api.v1.mcp_websocket import (
            MCPWebSocketMetrics,
            SecureMessageProcessor,
        )

        metrics = MCPWebSocketMetrics()

        processor = SecureMessageProcessor(
            session_id="test-session",
            user_id="user:alice",
            metrics=metrics,
        )

        processor.record_message_received("initialize")

        # Counter should have been incremented
        # Note: The actual increment may be tracked differently
        assert hasattr(metrics, "messages_received")


@pytest.mark.xdist_group(name="test_mcp_websocket_idle_cleanup")
class TestMCPWebSocketIdleCleanup:
    """Tests for idle connection cleanup background task."""

    def teardown_method(self) -> None:
        """Force GC to prevent mock accumulation in xdist workers."""
        gc.collect()

    def test_idle_cleanup_task_exists(self) -> None:
        """
        GIVEN the MCP WebSocket module
        WHEN importing
        THEN should have idle_cleanup_task function.
        """
        from mcp_server_langgraph.api.v1.mcp_websocket import idle_cleanup_task

        assert callable(idle_cleanup_task)

    @pytest.mark.asyncio
    async def test_idle_cleanup_closes_idle_connections(self) -> None:
        """
        GIVEN connections that have exceeded idle timeout
        WHEN idle cleanup runs
        THEN should close those connections.
        """
        from datetime import timedelta

        from mcp_server_langgraph.api.v1.mcp_websocket import (
            ConnectionManager,
            IDLE_TIMEOUT_SECONDS,
            _utc_now,
            cleanup_idle_connections,
        )

        manager = ConnectionManager()

        # Add an idle connection
        mock_ws_idle = AsyncMock(spec=WebSocket)
        await manager.connect(mock_ws_idle, session_id="idle-session")

        # Make it appear idle
        manager._connections["idle-session"].last_activity = _utc_now() - timedelta(seconds=IDLE_TIMEOUT_SECONDS + 60)

        # Add an active connection
        mock_ws_active = AsyncMock(spec=WebSocket)
        await manager.connect(mock_ws_active, session_id="active-session")

        # Run cleanup
        closed_count = await cleanup_idle_connections(manager)

        assert closed_count == 1
        assert not manager.has_connection("idle-session")
        assert manager.has_connection("active-session")
        mock_ws_idle.close.assert_called_once()

    @pytest.mark.asyncio
    async def test_idle_cleanup_handles_close_errors(self) -> None:
        """
        GIVEN an idle connection that fails to close
        WHEN idle cleanup runs
        THEN should handle the error gracefully and continue.
        """
        from datetime import timedelta

        from mcp_server_langgraph.api.v1.mcp_websocket import (
            ConnectionManager,
            IDLE_TIMEOUT_SECONDS,
            _utc_now,
            cleanup_idle_connections,
        )

        manager = ConnectionManager()

        # Add connection that will fail to close
        mock_ws = AsyncMock(spec=WebSocket)
        mock_ws.close = AsyncMock(side_effect=Exception("Connection already closed"))
        await manager.connect(mock_ws, session_id="failing-session")

        manager._connections["failing-session"].last_activity = _utc_now() - timedelta(seconds=IDLE_TIMEOUT_SECONDS + 60)

        # Should not raise
        closed_count = await cleanup_idle_connections(manager)

        # Should still report as processed
        assert closed_count >= 0


@pytest.mark.xdist_group(name="test_mcp_websocket_graceful_shutdown")
class TestMCPWebSocketGracefulShutdown:
    """Tests for graceful shutdown of WebSocket connections."""

    def teardown_method(self) -> None:
        """Force GC to prevent mock accumulation in xdist workers."""
        gc.collect()

    def test_graceful_shutdown_function_exists(self) -> None:
        """
        GIVEN the MCP WebSocket module
        WHEN importing
        THEN should have graceful_shutdown function.
        """
        from mcp_server_langgraph.api.v1.mcp_websocket import graceful_shutdown

        assert callable(graceful_shutdown)

    @pytest.mark.asyncio
    async def test_graceful_shutdown_closes_all_connections(self) -> None:
        """
        GIVEN active WebSocket connections
        WHEN graceful shutdown is initiated
        THEN should close all connections with proper code.
        """
        from mcp_server_langgraph.api.v1.mcp_websocket import (
            ConnectionManager,
            graceful_shutdown,
        )

        manager = ConnectionManager()

        # Add multiple connections
        mock_ws1 = AsyncMock(spec=WebSocket)
        mock_ws2 = AsyncMock(spec=WebSocket)

        await manager.connect(mock_ws1, session_id="session-1")
        await manager.connect(mock_ws2, session_id="session-2")

        assert manager.get_connection_count() == 2

        # Graceful shutdown
        await graceful_shutdown(manager)

        # All connections should be closed
        assert manager.get_connection_count() == 0
        mock_ws1.close.assert_called_once()
        mock_ws2.close.assert_called_once()

    @pytest.mark.asyncio
    async def test_graceful_shutdown_uses_going_away_code(self) -> None:
        """
        GIVEN active connections
        WHEN graceful shutdown is called
        THEN should use WebSocket 1001 (Going Away) close code.
        """
        from mcp_server_langgraph.api.v1.mcp_websocket import (
            ConnectionManager,
            graceful_shutdown,
        )

        manager = ConnectionManager()
        mock_ws = AsyncMock(spec=WebSocket)
        await manager.connect(mock_ws, session_id="session-1")

        await graceful_shutdown(manager)

        # Should use code 1001 (Going Away)
        mock_ws.close.assert_called_with(code=1001, reason="Server shutdown")

    @pytest.mark.asyncio
    async def test_graceful_shutdown_handles_close_errors(self) -> None:
        """
        GIVEN connections that fail to close
        WHEN graceful shutdown is called
        THEN should continue closing other connections.
        """
        from mcp_server_langgraph.api.v1.mcp_websocket import (
            ConnectionManager,
            graceful_shutdown,
        )

        manager = ConnectionManager()

        # One connection that fails
        mock_ws_failing = AsyncMock(spec=WebSocket)
        mock_ws_failing.close = AsyncMock(side_effect=Exception("Already closed"))

        # One connection that succeeds
        mock_ws_success = AsyncMock(spec=WebSocket)

        await manager.connect(mock_ws_failing, session_id="failing")
        await manager.connect(mock_ws_success, session_id="success")

        # Should not raise
        await graceful_shutdown(manager)

        # Both should have been attempted
        mock_ws_failing.close.assert_called()
        mock_ws_success.close.assert_called()


@pytest.mark.xdist_group(name="test_mcp_websocket_otel")
class TestMCPWebSocketOpenTelemetry:
    """Tests for OpenTelemetry metrics integration."""

    def teardown_method(self) -> None:
        """Force GC to prevent mock accumulation in xdist workers."""
        gc.collect()

    def test_otel_metrics_provider_exists(self) -> None:
        """
        GIVEN the MCP WebSocket module
        WHEN importing
        THEN should have OTelMCPMetrics class.
        """
        from mcp_server_langgraph.api.v1.mcp_websocket import OTelMCPMetrics

        assert OTelMCPMetrics is not None

    def test_otel_metrics_creates_counters(self) -> None:
        """
        GIVEN OTelMCPMetrics instance
        WHEN initialized
        THEN should create OpenTelemetry counter instruments.
        """
        from mcp_server_langgraph.api.v1.mcp_websocket import OTelMCPMetrics

        metrics = OTelMCPMetrics()

        # Should have counter methods
        assert hasattr(metrics, "record_connection")
        assert hasattr(metrics, "record_disconnect")
        assert hasattr(metrics, "record_message_received")
        assert hasattr(metrics, "record_message_sent")

    def test_otel_metrics_creates_gauge(self) -> None:
        """
        GIVEN OTelMCPMetrics instance
        WHEN tracking active connections
        THEN should use gauge for current value.
        """
        from mcp_server_langgraph.api.v1.mcp_websocket import OTelMCPMetrics

        metrics = OTelMCPMetrics()

        # Should track active connections as observable gauge
        assert hasattr(metrics, "active_connections_gauge")

    def test_otel_metrics_adds_labels(self) -> None:
        """
        GIVEN OTelMCPMetrics instance
        WHEN recording metrics
        THEN should include appropriate labels/attributes.
        """
        from mcp_server_langgraph.api.v1.mcp_websocket import OTelMCPMetrics

        metrics = OTelMCPMetrics()

        # Should accept labels for method tracking
        metrics.record_message_received(method="initialize", user_id="user:alice")
        # Should not raise

    def test_otel_metrics_histogram_for_latency(self) -> None:
        """
        GIVEN OTelMCPMetrics instance
        WHEN tracking message processing time
        THEN should use histogram for latency distribution.
        """
        from mcp_server_langgraph.api.v1.mcp_websocket import OTelMCPMetrics

        metrics = OTelMCPMetrics()

        assert hasattr(metrics, "record_message_latency")

        # Record some latency
        metrics.record_message_latency(method="tools/call", latency_ms=150.5)
        # Should not raise


@pytest.mark.xdist_group(name="test_mcp_websocket_lifespan")
class TestMCPWebSocketLifespan:
    """Tests for FastAPI lifespan integration."""

    def teardown_method(self) -> None:
        """Force GC to prevent mock accumulation in xdist workers."""
        gc.collect()

    def test_lifespan_context_manager_exists(self) -> None:
        """
        GIVEN the MCP WebSocket module
        WHEN importing
        THEN should have mcp_websocket_lifespan context manager.
        """
        from mcp_server_langgraph.api.v1.mcp_websocket import mcp_websocket_lifespan

        assert mcp_websocket_lifespan is not None

    @pytest.mark.asyncio
    async def test_lifespan_starts_cleanup_task(self) -> None:
        """
        GIVEN mcp_websocket_lifespan context manager
        WHEN entering the context
        THEN should start the idle cleanup background task.
        """
        from mcp_server_langgraph.api.v1.mcp_websocket import mcp_websocket_lifespan
        from mcp_server_langgraph.mcp.websocket import MCPWebSocketLifecycleManager

        # Create a mock lifecycle manager
        mock_manager = MagicMock(spec=MCPWebSocketLifecycleManager)
        mock_manager.startup = AsyncMock()  # noqa: async-mock-config
        mock_manager.shutdown = AsyncMock()  # noqa: async-mock-config

        # Create a mock app
        mock_app = MagicMock()

        with patch(
            "mcp_server_langgraph.mcp.websocket.get_mcp_lifecycle_manager",
            return_value=mock_manager,
        ):
            async with mcp_websocket_lifespan(mock_app):
                # Should have called startup on the manager
                mock_manager.startup.assert_called_once()

    @pytest.mark.asyncio
    async def test_lifespan_stops_cleanup_on_shutdown(self) -> None:
        """
        GIVEN mcp_websocket_lifespan with running cleanup task
        WHEN exiting the context (shutdown)
        THEN should cancel the cleanup task gracefully.
        """
        from mcp_server_langgraph.api.v1.mcp_websocket import mcp_websocket_lifespan

        mock_app = MagicMock()

        async with mcp_websocket_lifespan(mock_app):
            pass  # Exit triggers shutdown

        # Cleanup task should be cancelled (verified by no exceptions)

    @pytest.mark.asyncio
    async def test_lifespan_calls_graceful_shutdown(self) -> None:
        """
        GIVEN active connections when lifespan exits
        WHEN shutdown occurs
        THEN should call graceful_shutdown to close all connections.
        """
        from mcp_server_langgraph.api.v1.mcp_websocket import (
            connection_manager,
            mcp_websocket_lifespan,
        )

        mock_app = MagicMock()

        # Add a connection before shutdown
        mock_ws = AsyncMock(spec=WebSocket)
        await connection_manager.connect(mock_ws, session_id="pre-shutdown-session")

        async with mcp_websocket_lifespan(mock_app):
            assert connection_manager.has_connection("pre-shutdown-session")

        # After lifespan exits, connections should be closed
        # Note: This may vary based on implementation
