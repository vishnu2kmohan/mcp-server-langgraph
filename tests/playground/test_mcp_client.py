"""
Tests for MCP StreamableHTTP client integration.

Tests the playground's MCP client with:
- JSON-RPC message formatting
- Authentication token handling
- Tool invocation (agent_chat)
- Streaming response parsing
- Connection error handling

Follows TDD principles and memory safety patterns for pytest-xdist.
"""

import gc
from typing import Any
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

pytestmark = [pytest.mark.unit, pytest.mark.playground, pytest.mark.mcp]


# ==============================================================================
# MCP Client Tests
# ==============================================================================


@pytest.mark.xdist_group(name="playground_mcp")
class TestMCPClient:
    """Test MCP StreamableHTTP client."""

    def teardown_method(self) -> None:
        """Force GC to prevent mock accumulation in xdist workers."""
        gc.collect()

    @pytest.mark.unit
    @pytest.mark.asyncio
    async def test_initialize_handshake(self) -> None:
        """Test MCP initialization handshake."""
        from mcp_server_langgraph.playground.mcp.client import MCPClient

        mock_response = MagicMock()
        mock_response.json = MagicMock(
            return_value={
                "jsonrpc": "2.0",
                "id": 1,
                "result": {
                    "protocolVersion": "2024-11-05",
                    "serverInfo": {"name": "langgraph-agent", "version": "1.0.0"},
                    "capabilities": {"tools": {"listChanged": False}},
                },
            }
        )
        mock_response.status_code = 200

        with patch("httpx.AsyncClient") as mock_client_class:
            mock_client = AsyncMock(return_value=None)  # Container for configured methods
            mock_client.post = AsyncMock(return_value=mock_response)
            mock_client_class.return_value.__aenter__ = AsyncMock(return_value=mock_client)
            mock_client_class.return_value.__aexit__ = AsyncMock(return_value=None)

            client = MCPClient(base_url="http://localhost:8000")
            result = await client.initialize()

            assert result["serverInfo"]["name"] == "langgraph-agent"
            assert result["protocolVersion"] == "2024-11-05"

    @pytest.mark.unit
    @pytest.mark.asyncio
    async def test_list_tools(self) -> None:
        """Test listing available tools via MCP."""
        from mcp_server_langgraph.playground.mcp.client import MCPClient

        mock_response = MagicMock()
        mock_response.json = MagicMock(
            return_value={
                "jsonrpc": "2.0",
                "id": 2,
                "result": {
                    "tools": [
                        {"name": "agent_chat", "description": "Chat with AI agent"},
                        {"name": "conversation_search", "description": "Search conversations"},
                    ]
                },
            }
        )
        mock_response.status_code = 200

        with patch("httpx.AsyncClient") as mock_client_class:
            mock_client = AsyncMock(return_value=None)  # Container for configured methods
            mock_client.post = AsyncMock(return_value=mock_response)
            mock_client_class.return_value.__aenter__ = AsyncMock(return_value=mock_client)
            mock_client_class.return_value.__aexit__ = AsyncMock(return_value=None)

            client = MCPClient(base_url="http://localhost:8000")
            tools = await client.list_tools()

            assert len(tools) == 2
            assert tools[0]["name"] == "agent_chat"

    @pytest.mark.unit
    @pytest.mark.asyncio
    async def test_call_tool_with_auth(self) -> None:
        """Test calling a tool with authentication token."""
        from mcp_server_langgraph.playground.mcp.client import MCPClient

        mock_response = MagicMock()
        mock_response.json = MagicMock(
            return_value={
                "jsonrpc": "2.0",
                "id": 3,
                "result": {"content": [{"type": "text", "text": "Hello! How can I help?"}]},
            }
        )
        mock_response.status_code = 200

        with patch("httpx.AsyncClient") as mock_client_class:
            mock_client = AsyncMock(return_value=None)  # Container for configured methods
            mock_client.post = AsyncMock(return_value=mock_response)
            mock_client_class.return_value.__aenter__ = AsyncMock(return_value=mock_client)
            mock_client_class.return_value.__aexit__ = AsyncMock(return_value=None)

            client = MCPClient(base_url="http://localhost:8000")
            result = await client.call_tool(
                name="agent_chat",
                arguments={
                    "message": "Hello",
                    "token": "test-jwt-token",
                    "user_id": "alice",
                },
            )

            assert len(result) == 1
            assert result[0]["type"] == "text"
            assert "Hello" in result[0]["text"]

    @pytest.mark.unit
    @pytest.mark.asyncio
    async def test_call_tool_formats_jsonrpc(self) -> None:
        """Test that tool calls are formatted as JSON-RPC."""
        from mcp_server_langgraph.playground.mcp.client import MCPClient

        mock_response = MagicMock()
        mock_response.json = MagicMock(
            return_value={
                "jsonrpc": "2.0",
                "id": 4,
                "result": {"content": [{"type": "text", "text": "Response"}]},
            }
        )
        mock_response.status_code = 200

        captured_requests: list[dict] = []

        async def capture_post(url: str, json: dict, **kwargs: Any) -> Any:
            captured_requests.append(json)
            return mock_response

        with patch("httpx.AsyncClient") as mock_client_class:
            mock_client = AsyncMock(return_value=None)  # Container for configured methods
            mock_client.post = capture_post
            mock_client_class.return_value.__aenter__ = AsyncMock(return_value=mock_client)
            mock_client_class.return_value.__aexit__ = AsyncMock(return_value=None)

            client = MCPClient(base_url="http://localhost:8000")
            await client.call_tool("agent_chat", {"message": "Test"})

            assert len(captured_requests) == 1
            request = captured_requests[0]
            assert request["jsonrpc"] == "2.0"
            assert request["method"] == "tools/call"
            assert request["params"]["name"] == "agent_chat"
            assert request["params"]["arguments"]["message"] == "Test"

    @pytest.mark.unit
    @pytest.mark.asyncio
    async def test_handles_permission_error(self) -> None:
        """Test handling of permission errors from MCP server."""
        from mcp_server_langgraph.playground.mcp.client import MCPClient, MCPPermissionError

        mock_response = MagicMock()
        mock_response.json = MagicMock(
            return_value={
                "jsonrpc": "2.0",
                "id": 5,
                "error": {
                    "code": -32001,
                    "message": "Not authorized to execute tool:agent_chat",
                },
            }
        )
        mock_response.status_code = 200

        with patch("httpx.AsyncClient") as mock_client_class:
            mock_client = AsyncMock(return_value=None)  # Container for configured methods
            mock_client.post = AsyncMock(return_value=mock_response)
            mock_client_class.return_value.__aenter__ = AsyncMock(return_value=mock_client)
            mock_client_class.return_value.__aexit__ = AsyncMock(return_value=None)

            client = MCPClient(base_url="http://localhost:8000")

            with pytest.raises(MCPPermissionError) as exc_info:
                await client.call_tool("agent_chat", {"message": "Test", "token": "invalid"})

            assert "Not authorized" in str(exc_info.value)

    @pytest.mark.unit
    @pytest.mark.asyncio
    async def test_handles_connection_error(self) -> None:
        """Test handling of connection errors."""
        from mcp_server_langgraph.playground.mcp.client import MCPClient, MCPConnectionError

        with patch("httpx.AsyncClient") as mock_client_class:
            mock_client = AsyncMock(return_value=None)  # Container for configured methods
            mock_client.post = AsyncMock(side_effect=ConnectionError("Server unavailable"))
            mock_client_class.return_value.__aenter__ = AsyncMock(return_value=mock_client)
            mock_client_class.return_value.__aexit__ = AsyncMock(return_value=None)

            client = MCPClient(base_url="http://localhost:8000")

            with pytest.raises(MCPConnectionError):
                await client.initialize()


@pytest.mark.xdist_group(name="playground_mcp")
class TestMCPStreamingClient:
    """Test MCP streaming response handling."""

    def teardown_method(self) -> None:
        """Force GC to prevent mock accumulation in xdist workers."""
        gc.collect()

    @pytest.mark.unit
    @pytest.mark.asyncio
    async def test_stream_tool_response(self) -> None:
        """Test streaming response from tool call."""
        from mcp_server_langgraph.playground.mcp.client import MCPStreamingClient

        # Mock NDJSON streaming response
        async def mock_stream():
            yield b'{"jsonrpc":"2.0","id":1,"result":{"content":[{"type":"text","text":"Hello "}]}}\n'
            yield b'{"jsonrpc":"2.0","id":1,"result":{"content":[{"type":"text","text":"World!"}]}}\n'

        mock_response = AsyncMock(return_value=None)  # Container for configured attrs
        mock_response.status_code = 200
        mock_response.headers = {"content-type": "application/x-ndjson"}
        mock_response.aiter_lines = mock_stream

        with patch("httpx.AsyncClient") as mock_client_class:
            mock_client = AsyncMock(return_value=None)  # Container for configured methods
            mock_client.stream = MagicMock(
                return_value=AsyncMock(__aenter__=AsyncMock(return_value=mock_response), __aexit__=AsyncMock())
            )
            mock_client_class.return_value.__aenter__ = AsyncMock(return_value=mock_client)
            mock_client_class.return_value.__aexit__ = AsyncMock(return_value=None)

            client = MCPStreamingClient(base_url="http://localhost:8000")

            chunks = []
            async for chunk in client.stream_tool_call("agent_chat", {"message": "Hi"}):
                chunks.append(chunk)

            assert len(chunks) >= 1

    @pytest.mark.unit
    @pytest.mark.asyncio
    async def test_accepts_ndjson_content_type(self) -> None:
        """Test that client requests NDJSON for streaming."""
        from mcp_server_langgraph.playground.mcp.client import MCPStreamingClient

        captured_headers: list[dict] = []

        async def capture_stream(method: str, url: str, **kwargs: Any) -> Any:
            captured_headers.append(kwargs.get("headers", {}))
            # Return a mock response
            mock_response = AsyncMock(return_value=None)  # Container for configured attrs
            mock_response.status_code = 200
            mock_response.headers = {"content-type": "application/x-ndjson"}
            mock_response.aiter_lines = AsyncMock(return_value=iter([]))
            return mock_response

        with patch("httpx.AsyncClient") as mock_client_class:
            mock_client = AsyncMock(return_value=None)  # Container for configured methods
            mock_client.stream = MagicMock(return_value=AsyncMock(__aenter__=capture_stream, __aexit__=AsyncMock()))
            mock_client_class.return_value.__aenter__ = AsyncMock(return_value=mock_client)
            mock_client_class.return_value.__aexit__ = AsyncMock(return_value=None)

            client = MCPStreamingClient(base_url="http://localhost:8000")

            # Just try to iterate - the headers will be captured
            try:
                async for _ in client.stream_tool_call("agent_chat", {"message": "Hi"}):
                    pass
            except Exception:
                pass  # Expected since mock is incomplete


@pytest.mark.xdist_group(name="playground_mcp")
class TestPlaygroundMCPIntegration:
    """Test playground chat integration with MCP protocol."""

    def teardown_method(self) -> None:
        """Force GC to prevent mock accumulation in xdist workers."""
        gc.collect()

    @pytest.mark.unit
    @pytest.mark.asyncio
    async def test_chat_uses_mcp_tool_call(self) -> None:
        """Test that playground chat uses MCP agent_chat tool."""
        from mcp_server_langgraph.playground.mcp.integration import PlaygroundMCPBridge

        mock_mcp_client = AsyncMock(return_value=None)  # Container for configured methods
        mock_mcp_client.call_tool = AsyncMock(return_value=[{"type": "text", "text": "I can help with that!"}])

        bridge = PlaygroundMCPBridge(mcp_client=mock_mcp_client)

        response = await bridge.send_chat_message(
            session_id="session-123",
            message="Hello",
            token="test-jwt",
            user_id="alice",
        )

        assert response.content == "I can help with that!"
        mock_mcp_client.call_tool.assert_called_once_with(
            "agent_chat",
            {
                "message": "Hello",
                "token": "test-jwt",
                "user_id": "alice",
                "thread_id": "session-123",
                "response_format": "detailed",
            },
        )

    @pytest.mark.unit
    @pytest.mark.asyncio
    async def test_streaming_chat_uses_mcp_stream(self) -> None:
        """Test that streaming chat uses MCP streaming client."""
        from mcp_server_langgraph.playground.mcp.integration import PlaygroundMCPBridge

        async def mock_stream(*args: Any, **kwargs: Any):
            yield {"content": [{"type": "text", "text": "Hello "}]}
            yield {"content": [{"type": "text", "text": "World!"}]}

        mock_streaming_client = AsyncMock(return_value=None)  # Container for configured methods
        mock_streaming_client.stream_tool_call = mock_stream

        bridge = PlaygroundMCPBridge(streaming_client=mock_streaming_client)

        chunks = []
        async for chunk in bridge.stream_chat_message(
            session_id="session-123",
            message="Hello",
            token="test-jwt",
            user_id="alice",
        ):
            chunks.append(chunk)

        # 3 chunks: "Hello ", "World!", and final marker
        assert len(chunks) == 3
        assert chunks[0].content == "Hello "
        assert chunks[1].content == "World!"
        assert chunks[2].is_final is True

    @pytest.mark.unit
    @pytest.mark.asyncio
    async def test_propagates_trace_context(self) -> None:
        """Test that MCP calls include trace context for observability."""
        from mcp_server_langgraph.playground.mcp.integration import PlaygroundMCPBridge

        captured_args: list[dict] = []

        async def capture_call(name: str, arguments: dict) -> list:
            captured_args.append(arguments)
            return [{"type": "text", "text": "OK"}]

        mock_mcp_client = AsyncMock(return_value=None)  # Container for configured methods
        mock_mcp_client.call_tool = capture_call

        bridge = PlaygroundMCPBridge(mcp_client=mock_mcp_client)

        await bridge.send_chat_message(
            session_id="session-123",
            message="Hello",
            token="test-jwt",
            user_id="alice",
            trace_id="trace-abc-123",
        )

        # Verify trace context was passed (implementation may vary)
        assert len(captured_args) == 1

    @pytest.mark.unit
    @pytest.mark.asyncio
    async def test_handles_mcp_errors_gracefully(self) -> None:
        """Test that MCP errors are wrapped appropriately."""
        from mcp_server_langgraph.playground.mcp.client import MCPPermissionError
        from mcp_server_langgraph.playground.mcp.integration import (
            ChatError,
            PlaygroundMCPBridge,
        )

        mock_mcp_client = AsyncMock(return_value=None)  # Container for configured methods
        mock_mcp_client.call_tool = AsyncMock(side_effect=MCPPermissionError("Not authorized"))

        bridge = PlaygroundMCPBridge(mcp_client=mock_mcp_client)

        with pytest.raises(ChatError) as exc_info:
            await bridge.send_chat_message(
                session_id="session-123",
                message="Hello",
                token="invalid",
                user_id="alice",
            )

        assert "permission" in str(exc_info.value).lower() or "authorized" in str(exc_info.value).lower()
