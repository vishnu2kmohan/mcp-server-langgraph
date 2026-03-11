"""
Tests for MCPBridge.

TDD: These tests define the expected behavior of MCPBridge,
which provides communication between the unified API and MCP server.

Tests verify:
1. send_chat_message() calls MCP agent_chat tool
2. stream_chat_message() yields streaming chunks
3. Error handling for connection failures
4. Error handling for permission denied
5. Factory function returns configured bridge when MCP_SERVER_URL is set
6. MCP Protocol 2025-11-25 features:
   - Resources (list, read, subscribe)
   - Sampling (createMessage)
   - Elicitation (form, url modes)
   - Tasks (get, cancel, list, result)
   - Session management
   - Error code handling
"""

from __future__ import annotations

import gc
from typing import TYPE_CHECKING
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

pytestmark = pytest.mark.unit

if TYPE_CHECKING:
    pass


class TestMCPBridge:
    """Test suite for MCPBridge."""

    def teardown_method(self) -> None:
        """Force GC to prevent mock accumulation in xdist workers."""
        gc.collect()

    # =========================================================================
    # send_chat_message() tests
    # =========================================================================

    @pytest.mark.asyncio
    async def test_send_chat_message_calls_agent_chat_tool(self) -> None:
        """GIVEN an MCPBridge with configured client
        WHEN send_chat_message() is called
        THEN it calls the agent_chat MCP tool
        """
        from mcp_server_langgraph.api.v1.mcp_bridge import MCPBridge, MCPClient

        from mcp_server_langgraph.api.v1.mcp_bridge import MCPToolResult

        mock_client = MagicMock(spec=MCPClient)
        mock_client.call_tool = AsyncMock(
            return_value=MCPToolResult(
                content=[{"type": "text", "text": "Hello from agent!"}],
            )
        )

        bridge = MCPBridge(mcp_client=mock_client)
        response = await bridge.send_chat_message(
            session_id="test-session",
            message="Hello",
            user_id="alice",
        )

        mock_client.call_tool.assert_called_once()
        call_args = mock_client.call_tool.call_args
        assert call_args[0][0] == "agent_chat"
        assert response.content == "Hello from agent!"

    @pytest.mark.asyncio
    async def test_send_chat_message_includes_thread_id(self) -> None:
        """GIVEN an MCPBridge
        WHEN send_chat_message() is called
        THEN it constructs thread_id from user_id and session_id
        """
        from mcp_server_langgraph.api.v1.mcp_bridge import MCPBridge, MCPClient, MCPToolResult

        mock_client = MagicMock(spec=MCPClient)
        mock_client.call_tool = AsyncMock(
            return_value=MCPToolResult(
                content=[{"type": "text", "text": "Response"}],
            )
        )

        bridge = MCPBridge(mcp_client=mock_client)
        await bridge.send_chat_message(
            session_id="session-123",
            message="Hello",
            user_id="bob",
        )

        call_args = mock_client.call_tool.call_args
        arguments = call_args[0][1]
        assert arguments["thread_id"] == "bob_session-123"
        assert arguments["user_id"] == "bob"

    @pytest.mark.asyncio
    async def test_send_chat_message_raises_chat_error_on_connection_failure(self) -> None:
        """GIVEN an MCPBridge with unreachable server
        WHEN send_chat_message() is called
        THEN it raises ChatError
        """
        from mcp_server_langgraph.api.v1.mcp_bridge import (
            ChatError,
            MCPBridge,
            MCPClient,
            MCPConnectionError,
        )

        mock_client = MagicMock(spec=MCPClient)
        mock_client.call_tool = AsyncMock(side_effect=MCPConnectionError("Connection refused"))

        bridge = MCPBridge(mcp_client=mock_client)

        with pytest.raises(ChatError) as exc_info:
            await bridge.send_chat_message(
                session_id="test-session",
                message="Hello",
            )

        assert "Chat failed" in str(exc_info.value)

    @pytest.mark.asyncio
    async def test_send_chat_message_raises_chat_error_on_permission_denied(self) -> None:
        """GIVEN an MCPBridge with unauthorized access
        WHEN send_chat_message() is called
        THEN it raises ChatError with permission message
        """
        from mcp_server_langgraph.api.v1.mcp_bridge import (
            ChatError,
            MCPBridge,
            MCPClient,
            MCPPermissionError,
        )

        mock_client = MagicMock(spec=MCPClient)
        mock_client.call_tool = AsyncMock(side_effect=MCPPermissionError("Access denied"))

        bridge = MCPBridge(mcp_client=mock_client)

        with pytest.raises(ChatError) as exc_info:
            await bridge.send_chat_message(
                session_id="test-session",
                message="Hello",
            )

        assert "Permission denied" in str(exc_info.value)

    @pytest.mark.asyncio
    async def test_send_chat_message_raises_error_when_not_configured(self) -> None:
        """GIVEN an MCPBridge without client
        WHEN send_chat_message() is called
        THEN it raises ChatError
        """
        from mcp_server_langgraph.api.v1.mcp_bridge import ChatError, MCPBridge

        bridge = MCPBridge()  # No client configured

        with pytest.raises(ChatError) as exc_info:
            await bridge.send_chat_message(
                session_id="test-session",
                message="Hello",
            )

        assert "not configured" in str(exc_info.value)

    # =========================================================================
    # stream_chat_message() tests
    # =========================================================================

    @pytest.mark.asyncio
    async def test_stream_chat_message_yields_chunks(self) -> None:
        """GIVEN an MCPBridge with streaming client
        WHEN stream_chat_message() is called
        THEN it yields ChatChunk objects
        """
        from mcp_server_langgraph.api.v1.mcp_bridge import MCPBridge, MCPClient

        async def mock_stream(*args, **kwargs):
            yield {"content": [{"type": "text", "text": "Hello"}]}
            yield {"content": [{"type": "text", "text": " world"}]}

        mock_client = MagicMock(spec=MCPClient)
        mock_client.stream_tool_call = mock_stream

        bridge = MCPBridge(mcp_client=mock_client)
        chunks = []
        async for chunk in bridge.stream_chat_message(
            session_id="test-session",
            message="Hello",
        ):
            if not chunk.is_final:
                chunks.append(chunk)

        assert len(chunks) == 2
        assert chunks[0].content == "Hello"
        assert chunks[1].content == " world"

    @pytest.mark.asyncio
    async def test_stream_chat_message_ends_with_final_chunk(self) -> None:
        """GIVEN streaming response
        WHEN stream ends
        THEN final chunk has is_final=True
        """
        from mcp_server_langgraph.api.v1.mcp_bridge import MCPBridge, MCPClient

        async def mock_stream(*args, **kwargs):
            yield {"content": [{"type": "text", "text": "Hi"}]}

        mock_client = MagicMock(spec=MCPClient)
        mock_client.stream_tool_call = mock_stream

        bridge = MCPBridge(mcp_client=mock_client)
        chunks = []
        async for chunk in bridge.stream_chat_message(
            session_id="test-session",
            message="Hello",
        ):
            chunks.append(chunk)

        # Last chunk should have is_final=True
        assert chunks[-1].is_final is True

    # =========================================================================
    # is_configured property tests
    # =========================================================================

    def test_is_configured_returns_true_when_client_set(self) -> None:
        """GIVEN an MCPBridge with client
        WHEN is_configured is checked
        THEN it returns True
        """
        from mcp_server_langgraph.api.v1.mcp_bridge import MCPBridge

        bridge = MCPBridge(mcp_url="http://localhost:8001")

        assert bridge.is_configured is True

    def test_is_configured_returns_false_when_no_client(self) -> None:
        """GIVEN an MCPBridge without client
        WHEN is_configured is checked
        THEN it returns False
        """
        from mcp_server_langgraph.api.v1.mcp_bridge import MCPBridge

        bridge = MCPBridge()

        assert bridge.is_configured is False

    # =========================================================================
    # get_mcp_bridge() factory tests
    # =========================================================================

    @pytest.mark.asyncio
    async def test_get_mcp_bridge_returns_none_when_no_env(self, monkeypatch: pytest.MonkeyPatch) -> None:
        """GIVEN no MCP_SERVER_URL environment variable
        WHEN get_mcp_bridge() is called
        THEN it returns None
        """
        from mcp_server_langgraph.api.v1.mcp_bridge import get_mcp_bridge, reset_mcp_bridge

        # Use monkeypatch to remove the env var (auto-cleanup after test)
        monkeypatch.delenv("MCP_SERVER_URL", raising=False)

        # Reset the singleton first
        reset_mcp_bridge()

        # With no env var set, bridge should be None
        bridge = get_mcp_bridge()
        assert bridge is None, f"Expected None but got {bridge}"

        # Reset singleton to avoid affecting other tests
        reset_mcp_bridge()

    @pytest.mark.asyncio
    async def test_get_mcp_bridge_returns_bridge_when_url_set(self) -> None:
        """GIVEN MCP_SERVER_URL environment variable
        WHEN get_mcp_bridge() is called
        THEN it returns configured MCPBridge
        """
        from mcp_server_langgraph.api.v1.mcp_bridge import (
            MCPBridge,
            get_mcp_bridge,
            reset_mcp_bridge,
        )

        reset_mcp_bridge()

        with patch("os.getenv", side_effect=lambda *a, **kw: "http://localhost:8001"):
            bridge = get_mcp_bridge()

        assert bridge is not None
        assert isinstance(bridge, MCPBridge)
        assert bridge.is_configured is True

        # Cleanup
        reset_mcp_bridge()


class TestMCPClient:
    """Test suite for MCPClient."""

    def teardown_method(self) -> None:
        """Force GC to prevent mock accumulation in xdist workers."""
        gc.collect()

    @pytest.mark.asyncio
    async def test_call_tool_builds_jsonrpc_request(self) -> None:
        """GIVEN an MCPClient
        WHEN call_tool() is called
        THEN it builds a proper JSON-RPC request
        """
        from mcp_server_langgraph.api.v1.mcp_bridge import MCPClient

        client = MCPClient(base_url="http://localhost:8001")

        with patch("httpx.AsyncClient") as mock_httpx:
            mock_response = MagicMock()
            mock_response.json.return_value = {
                "jsonrpc": "2.0",
                "id": 1,
                "result": {"content": []},
            }

            mock_client_instance = MagicMock()
            mock_client_instance.post = AsyncMock(return_value=mock_response)
            mock_client_instance.__aenter__ = AsyncMock(return_value=mock_client_instance)
            mock_client_instance.__aexit__ = AsyncMock(return_value=None)
            mock_httpx.return_value = mock_client_instance

            await client.call_tool("agent_chat", {"message": "Hello"})

            # Verify the request structure
            call_args = mock_client_instance.post.call_args
            request_body = call_args.kwargs.get("json", call_args[1].get("json", {}))
            assert request_body["jsonrpc"] == "2.0"
            assert request_body["method"] == "tools/call"
            assert request_body["params"]["name"] == "agent_chat"

    @pytest.mark.asyncio
    async def test_call_tool_handles_error_response(self) -> None:
        """GIVEN an error response from MCP server
        WHEN call_tool() is called
        THEN it raises MCPError
        """
        from mcp_server_langgraph.api.v1.mcp_bridge import MCPClient, MCPError

        client = MCPClient(base_url="http://localhost:8001")

        with patch("httpx.AsyncClient") as mock_httpx:
            mock_response = MagicMock()
            mock_response.json.return_value = {
                "jsonrpc": "2.0",
                "id": 1,
                "error": {"code": -32603, "message": "Internal error"},
            }

            mock_client_instance = MagicMock()
            mock_client_instance.post = AsyncMock(return_value=mock_response)
            mock_client_instance.__aenter__ = AsyncMock(return_value=mock_client_instance)
            mock_client_instance.__aexit__ = AsyncMock(return_value=None)
            mock_httpx.return_value = mock_client_instance

            with pytest.raises(MCPError) as exc_info:
                await client.call_tool("agent_chat", {"message": "Hello"})

            assert "Internal error" in str(exc_info.value)


# =============================================================================
# MCP Protocol 2025-11-25 Feature Tests
# =============================================================================


class TestMCPProtocol2025Features:
    """Test suite for MCP Protocol 2025-11-25 features."""

    def teardown_method(self) -> None:
        """Force GC to prevent mock accumulation in xdist workers."""
        gc.collect()

    # =========================================================================
    # MCPClient Initialization Tests
    # =========================================================================

    @pytest.mark.asyncio
    async def test_initialize_sends_protocol_version(self) -> None:
        """GIVEN an MCPClient
        WHEN initialize() is called
        THEN it sends the correct protocol version
        """
        from mcp_server_langgraph.api.v1.mcp_bridge import MCPClient, MCP_PROTOCOL_VERSION

        client = MCPClient(base_url="http://localhost:8001")

        with patch("httpx.AsyncClient") as mock_httpx:
            mock_response = MagicMock()
            mock_response.headers = {"MCP-Session-Id": "session-123"}
            mock_response.json.return_value = {
                "jsonrpc": "2.0",
                "id": 1,
                "result": {
                    "protocolVersion": MCP_PROTOCOL_VERSION,
                    "capabilities": {},
                    "serverInfo": {"name": "test-server", "version": "1.0.0"},
                },
            }

            mock_client_instance = MagicMock()
            mock_client_instance.post = AsyncMock(return_value=mock_response)
            mock_client_instance.__aenter__ = AsyncMock(return_value=mock_client_instance)
            mock_client_instance.__aexit__ = AsyncMock(return_value=None)
            mock_httpx.return_value = mock_client_instance

            await client.initialize()

            call_args = mock_client_instance.post.call_args
            headers = call_args.kwargs.get("headers", {})
            assert headers.get("MCP-Protocol-Version") == MCP_PROTOCOL_VERSION

    @pytest.mark.asyncio
    async def test_initialize_extracts_session_id(self) -> None:
        """GIVEN an MCP server response with session ID
        WHEN initialize() is called
        THEN it stores the session ID
        """
        from mcp_server_langgraph.api.v1.mcp_bridge import MCPClient

        client = MCPClient(base_url="http://localhost:8001")

        with patch("httpx.AsyncClient") as mock_httpx:
            mock_response = MagicMock()
            mock_response.headers = {"MCP-Session-Id": "unique-session-456"}
            mock_response.json.return_value = {
                "jsonrpc": "2.0",
                "id": 1,
                "result": {
                    "protocolVersion": "2025-11-25",
                    "capabilities": {},
                    "serverInfo": {"name": "test-server", "version": "1.0.0"},
                },
            }

            mock_client_instance = MagicMock()
            mock_client_instance.post = AsyncMock(return_value=mock_response)
            mock_client_instance.__aenter__ = AsyncMock(return_value=mock_client_instance)
            mock_client_instance.__aexit__ = AsyncMock(return_value=None)
            mock_httpx.return_value = mock_client_instance

            await client.initialize()

            assert client.session_id == "unique-session-456"
            assert client.is_initialized is True

    # =========================================================================
    # Resources Tests
    # =========================================================================

    @pytest.mark.asyncio
    async def test_list_resources_returns_resources(self) -> None:
        """GIVEN an MCPClient
        WHEN list_resources() is called
        THEN it returns a list of MCPResource objects
        """
        from mcp_server_langgraph.api.v1.mcp_bridge import MCPClient, MCPResource

        client = MCPClient(base_url="http://localhost:8001")

        with patch("httpx.AsyncClient") as mock_httpx:
            mock_response = MagicMock()
            mock_response.json.return_value = {
                "jsonrpc": "2.0",
                "id": 1,
                "result": {
                    "resources": [
                        {
                            "uri": "file:///test.txt",
                            "name": "test.txt",
                            "title": "Test File",
                            "mimeType": "text/plain",
                        },
                        {
                            "uri": "file:///data.json",
                            "name": "data.json",
                            "mimeType": "application/json",
                        },
                    ],
                },
            }

            mock_client_instance = MagicMock()
            mock_client_instance.post = AsyncMock(return_value=mock_response)
            mock_client_instance.__aenter__ = AsyncMock(return_value=mock_client_instance)
            mock_client_instance.__aexit__ = AsyncMock(return_value=None)
            mock_httpx.return_value = mock_client_instance

            resources, next_cursor = await client.list_resources()

            assert len(resources) == 2
            assert isinstance(resources[0], MCPResource)
            assert resources[0].uri == "file:///test.txt"
            assert resources[0].name == "test.txt"
            assert resources[0].mime_type == "text/plain"

    @pytest.mark.asyncio
    async def test_read_resource_returns_content(self) -> None:
        """GIVEN an MCPClient
        WHEN read_resource() is called with a URI
        THEN it returns the resource content
        """
        from mcp_server_langgraph.api.v1.mcp_bridge import MCPClient, MCPResourceContent

        client = MCPClient(base_url="http://localhost:8001")

        with patch("httpx.AsyncClient") as mock_httpx:
            mock_response = MagicMock()
            mock_response.json.return_value = {
                "jsonrpc": "2.0",
                "id": 1,
                "result": {
                    "contents": [
                        {
                            "uri": "file:///test.txt",
                            "mimeType": "text/plain",
                            "text": "Hello, World!",
                        },
                    ],
                },
            }

            mock_client_instance = MagicMock()
            mock_client_instance.post = AsyncMock(return_value=mock_response)
            mock_client_instance.__aenter__ = AsyncMock(return_value=mock_client_instance)
            mock_client_instance.__aexit__ = AsyncMock(return_value=None)
            mock_httpx.return_value = mock_client_instance

            contents = await client.read_resource("file:///test.txt")

            assert len(contents) == 1
            assert isinstance(contents[0], MCPResourceContent)
            assert contents[0].text == "Hello, World!"
            assert contents[0].mime_type == "text/plain"

    @pytest.mark.asyncio
    async def test_subscribe_resource_returns_success(self) -> None:
        """GIVEN an MCPClient
        WHEN subscribe_resource() is called
        THEN it returns True on success
        """
        from mcp_server_langgraph.api.v1.mcp_bridge import MCPClient

        client = MCPClient(base_url="http://localhost:8001")

        with patch("httpx.AsyncClient") as mock_httpx:
            mock_response = MagicMock()
            mock_response.json.return_value = {
                "jsonrpc": "2.0",
                "id": 1,
                "result": {},
            }

            mock_client_instance = MagicMock()
            mock_client_instance.post = AsyncMock(return_value=mock_response)
            mock_client_instance.__aenter__ = AsyncMock(return_value=mock_client_instance)
            mock_client_instance.__aexit__ = AsyncMock(return_value=None)
            mock_httpx.return_value = mock_client_instance

            result = await client.subscribe_resource("file:///test.txt")

            assert result is True

    # =========================================================================
    # Sampling Tests
    # =========================================================================

    @pytest.mark.asyncio
    async def test_create_message_sends_sampling_request(self) -> None:
        """GIVEN an MCPClient
        WHEN create_message() is called
        THEN it sends a sampling/createMessage request
        """
        from mcp_server_langgraph.api.v1.mcp_bridge import MCPClient, SamplingResponse

        client = MCPClient(base_url="http://localhost:8001")

        with patch("httpx.AsyncClient") as mock_httpx:
            mock_response = MagicMock()
            mock_response.json.return_value = {
                "jsonrpc": "2.0",
                "id": 1,
                "result": {
                    "role": "assistant",
                    "content": {"type": "text", "text": "Hello from LLM!"},
                    "model": "claude-3-sonnet",
                    "stopReason": "end_turn",
                },
            }

            mock_client_instance = MagicMock()
            mock_client_instance.post = AsyncMock(return_value=mock_response)
            mock_client_instance.__aenter__ = AsyncMock(return_value=mock_client_instance)
            mock_client_instance.__aexit__ = AsyncMock(return_value=None)
            mock_httpx.return_value = mock_client_instance

            messages = [
                {"role": "user", "content": {"type": "text", "text": "Hello"}},
            ]
            response = await client.create_message(messages=messages, max_tokens=100)

            assert isinstance(response, SamplingResponse)
            assert response.role == "assistant"
            assert response.model == "claude-3-sonnet"

            # Verify the request method
            call_args = mock_client_instance.post.call_args
            request_body = call_args.kwargs.get("json", {})
            assert request_body["method"] == "sampling/createMessage"

    # =========================================================================
    # Elicitation Tests
    # =========================================================================

    @pytest.mark.asyncio
    async def test_create_elicitation_form_mode(self) -> None:
        """GIVEN an MCPClient
        WHEN create_elicitation() is called with form mode
        THEN it sends the correct request
        """
        from mcp_server_langgraph.api.v1.mcp_bridge import (
            MCPClient,
            ElicitationMode,
            ElicitationResponse,
            ElicitationAction,
        )

        client = MCPClient(base_url="http://localhost:8001")

        with patch("httpx.AsyncClient") as mock_httpx:
            mock_response = MagicMock()
            mock_response.json.return_value = {
                "jsonrpc": "2.0",
                "id": 1,
                "result": {
                    "action": "accept",
                    "content": {"username": "alice", "email": "alice@example.com"},
                },
            }

            mock_client_instance = MagicMock()
            mock_client_instance.post = AsyncMock(return_value=mock_response)
            mock_client_instance.__aenter__ = AsyncMock(return_value=mock_client_instance)
            mock_client_instance.__aexit__ = AsyncMock(return_value=None)
            mock_httpx.return_value = mock_client_instance

            schema = {
                "type": "object",
                "properties": {
                    "username": {"type": "string"},
                    "email": {"type": "string", "format": "email"},
                },
            }
            response = await client.create_elicitation(
                message="Please provide your details",
                mode=ElicitationMode.FORM,
                requested_schema=schema,
            )

            assert isinstance(response, ElicitationResponse)
            assert response.action == ElicitationAction.ACCEPT
            assert response.content["username"] == "alice"

    @pytest.mark.asyncio
    async def test_create_elicitation_url_mode_requires_url(self) -> None:
        """GIVEN an MCPClient
        WHEN create_elicitation() is called with url mode without URL
        THEN it raises MCPInvalidParamsError
        """
        from mcp_server_langgraph.api.v1.mcp_bridge import (
            MCPClient,
            ElicitationMode,
            MCPInvalidParamsError,
        )

        client = MCPClient(base_url="http://localhost:8001")

        with pytest.raises(MCPInvalidParamsError) as exc_info:
            await client.create_elicitation(
                message="Please authenticate",
                mode=ElicitationMode.URL,
                # Missing url parameter
            )

        assert "URL is required" in str(exc_info.value)

    # =========================================================================
    # Tasks Tests
    # =========================================================================

    @pytest.mark.asyncio
    async def test_get_task_returns_task_status(self) -> None:
        """GIVEN an MCPClient
        WHEN get_task() is called
        THEN it returns the task status
        """
        from mcp_server_langgraph.api.v1.mcp_bridge import MCPClient, MCPTask, TaskStatus

        client = MCPClient(base_url="http://localhost:8001")

        with patch("httpx.AsyncClient") as mock_httpx:
            mock_response = MagicMock()
            mock_response.json.return_value = {
                "jsonrpc": "2.0",
                "id": 1,
                "result": {
                    "taskId": "task-123",
                    "status": "working",
                    "createdAt": "2024-12-14T10:00:00Z",
                    "lastUpdatedAt": "2024-12-14T10:00:05Z",
                    "statusMessage": "Processing step 2/5",
                },
            }

            mock_client_instance = MagicMock()
            mock_client_instance.post = AsyncMock(return_value=mock_response)
            mock_client_instance.__aenter__ = AsyncMock(return_value=mock_client_instance)
            mock_client_instance.__aexit__ = AsyncMock(return_value=None)
            mock_httpx.return_value = mock_client_instance

            task = await client.get_task("task-123")

            assert isinstance(task, MCPTask)
            assert task.task_id == "task-123"
            assert task.status == TaskStatus.WORKING
            assert task.status_message == "Processing step 2/5"

    @pytest.mark.asyncio
    async def test_cancel_task_returns_cancelled_status(self) -> None:
        """GIVEN an MCPClient
        WHEN cancel_task() is called
        THEN it returns the task with cancelled status
        """
        from mcp_server_langgraph.api.v1.mcp_bridge import MCPClient, MCPTask, TaskStatus

        client = MCPClient(base_url="http://localhost:8001")

        with patch("httpx.AsyncClient") as mock_httpx:
            mock_response = MagicMock()
            mock_response.json.return_value = {
                "jsonrpc": "2.0",
                "id": 1,
                "result": {
                    "taskId": "task-123",
                    "status": "cancelled",
                    "createdAt": "2024-12-14T10:00:00Z",
                    "lastUpdatedAt": "2024-12-14T10:01:00Z",
                },
            }

            mock_client_instance = MagicMock()
            mock_client_instance.post = AsyncMock(return_value=mock_response)
            mock_client_instance.__aenter__ = AsyncMock(return_value=mock_client_instance)
            mock_client_instance.__aexit__ = AsyncMock(return_value=None)
            mock_httpx.return_value = mock_client_instance

            task = await client.cancel_task("task-123")

            assert isinstance(task, MCPTask)
            assert task.status == TaskStatus.CANCELLED

    @pytest.mark.asyncio
    async def test_list_tasks_returns_active_tasks(self) -> None:
        """GIVEN an MCPClient
        WHEN list_tasks() is called
        THEN it returns a list of active tasks
        """
        from mcp_server_langgraph.api.v1.mcp_bridge import MCPClient, MCPTask

        client = MCPClient(base_url="http://localhost:8001")

        with patch("httpx.AsyncClient") as mock_httpx:
            mock_response = MagicMock()
            mock_response.json.return_value = {
                "jsonrpc": "2.0",
                "id": 1,
                "result": {
                    "tasks": [
                        {
                            "taskId": "task-1",
                            "status": "working",
                            "createdAt": "2024-12-14T10:00:00Z",
                            "lastUpdatedAt": "2024-12-14T10:00:05Z",
                        },
                        {
                            "taskId": "task-2",
                            "status": "completed",
                            "createdAt": "2024-12-14T09:00:00Z",
                            "lastUpdatedAt": "2024-12-14T09:30:00Z",
                        },
                    ],
                },
            }

            mock_client_instance = MagicMock()
            mock_client_instance.post = AsyncMock(return_value=mock_response)
            mock_client_instance.__aenter__ = AsyncMock(return_value=mock_client_instance)
            mock_client_instance.__aexit__ = AsyncMock(return_value=None)
            mock_httpx.return_value = mock_client_instance

            tasks, next_cursor = await client.list_tasks()

            assert len(tasks) == 2
            assert isinstance(tasks[0], MCPTask)
            assert tasks[0].task_id == "task-1"

    # =========================================================================
    # Error Code Handling Tests
    # =========================================================================

    @pytest.mark.asyncio
    async def test_error_code_32001_raises_permission_error(self) -> None:
        """GIVEN an error response with code -32001
        WHEN processing the response
        THEN it raises MCPPermissionError
        """
        from mcp_server_langgraph.api.v1.mcp_bridge import MCPClient, MCPPermissionError

        client = MCPClient(base_url="http://localhost:8001")

        with patch("httpx.AsyncClient") as mock_httpx:
            mock_response = MagicMock()
            mock_response.headers = {}
            mock_response.json.return_value = {
                "jsonrpc": "2.0",
                "id": 1,
                "error": {"code": -32001, "message": "Permission denied"},
            }

            mock_client_instance = MagicMock()
            mock_client_instance.post = AsyncMock(return_value=mock_response)
            mock_client_instance.__aenter__ = AsyncMock(return_value=mock_client_instance)
            mock_client_instance.__aexit__ = AsyncMock(return_value=None)
            mock_httpx.return_value = mock_client_instance

            with pytest.raises(MCPPermissionError) as exc_info:
                await client.call_tool("test_tool", {})

            assert exc_info.value.code == -32001

    @pytest.mark.asyncio
    async def test_error_code_32002_raises_resource_not_found(self) -> None:
        """GIVEN an error response with code -32002
        WHEN processing the response
        THEN it raises MCPResourceNotFoundError
        """
        from mcp_server_langgraph.api.v1.mcp_bridge import MCPClient, MCPResourceNotFoundError

        client = MCPClient(base_url="http://localhost:8001")

        with patch("httpx.AsyncClient") as mock_httpx:
            mock_response = MagicMock()
            mock_response.json.return_value = {
                "jsonrpc": "2.0",
                "id": 1,
                "error": {
                    "code": -32002,
                    "message": "Resource not found",
                    "data": {"uri": "file:///missing.txt"},
                },
            }

            mock_client_instance = MagicMock()
            mock_client_instance.post = AsyncMock(return_value=mock_response)
            mock_client_instance.__aenter__ = AsyncMock(return_value=mock_client_instance)
            mock_client_instance.__aexit__ = AsyncMock(return_value=None)
            mock_httpx.return_value = mock_client_instance

            with pytest.raises(MCPResourceNotFoundError) as exc_info:
                await client.read_resource("file:///missing.txt")

            assert exc_info.value.code == -32002

    @pytest.mark.asyncio
    async def test_error_code_32042_raises_elicitation_required(self) -> None:
        """GIVEN an error response with code -32042
        WHEN processing the response
        THEN it raises MCPElicitationRequiredError
        """
        from mcp_server_langgraph.api.v1.mcp_bridge import MCPClient, MCPElicitationRequiredError

        client = MCPClient(base_url="http://localhost:8001")

        with patch("httpx.AsyncClient") as mock_httpx:
            mock_response = MagicMock()
            mock_response.headers = {}
            mock_response.json.return_value = {
                "jsonrpc": "2.0",
                "id": 1,
                "error": {
                    "code": -32042,
                    "message": "Elicitation required",
                    "data": {
                        "elicitations": [
                            {"type": "form", "schema": {"type": "object"}},
                        ],
                    },
                },
            }

            mock_client_instance = MagicMock()
            mock_client_instance.post = AsyncMock(return_value=mock_response)
            mock_client_instance.__aenter__ = AsyncMock(return_value=mock_client_instance)
            mock_client_instance.__aexit__ = AsyncMock(return_value=None)
            mock_httpx.return_value = mock_client_instance

            with pytest.raises(MCPElicitationRequiredError) as exc_info:
                await client.call_tool("test_tool", {})

            assert exc_info.value.code == -32042
            assert len(exc_info.value.elicitations) == 1


class TestMCPBridge2025Features:
    """Test suite for MCPBridge MCP 2025-11-25 feature integration."""

    def teardown_method(self) -> None:
        """Force GC to prevent mock accumulation in xdist workers."""
        gc.collect()

    # =========================================================================
    # Bridge Resource Methods
    # =========================================================================

    @pytest.mark.asyncio
    async def test_bridge_read_resource_delegates_to_client(self) -> None:
        """GIVEN an MCPBridge with configured client
        WHEN read_resource() is called
        THEN it delegates to the client
        """
        from mcp_server_langgraph.api.v1.mcp_bridge import (
            MCPBridge,
            MCPClient,
            MCPResourceContent,
        )

        mock_client = MagicMock(spec=MCPClient)
        mock_client.read_resource = AsyncMock(
            return_value=[
                MCPResourceContent(
                    uri="file:///test.txt",
                    mime_type="text/plain",
                    text="Hello!",
                )
            ]
        )

        bridge = MCPBridge(mcp_client=mock_client)
        contents = await bridge.read_resource("file:///test.txt")

        mock_client.read_resource.assert_called_once_with("file:///test.txt")
        assert len(contents) == 1
        assert contents[0].text == "Hello!"

    @pytest.mark.asyncio
    async def test_bridge_read_resource_raises_when_not_configured(self) -> None:
        """GIVEN an MCPBridge without client
        WHEN read_resource() is called
        THEN it raises ChatError
        """
        from mcp_server_langgraph.api.v1.mcp_bridge import MCPBridge, ChatError

        bridge = MCPBridge()

        with pytest.raises(ChatError) as exc_info:
            await bridge.read_resource("file:///test.txt")

        assert "not configured" in str(exc_info.value)

    # =========================================================================
    # Bridge Sampling Methods
    # =========================================================================

    @pytest.mark.asyncio
    async def test_bridge_request_sampling_with_model_hints(self) -> None:
        """GIVEN an MCPBridge
        WHEN request_sampling() is called with model hints
        THEN it builds correct model preferences
        """
        from mcp_server_langgraph.api.v1.mcp_bridge import (
            MCPBridge,
            MCPClient,
            SamplingResponse,
        )

        mock_client = MagicMock(spec=MCPClient)
        mock_client.create_message = AsyncMock(
            return_value=SamplingResponse(
                role="assistant",
                content={"type": "text", "text": "Response"},
                model="claude-3-sonnet",
            )
        )

        bridge = MCPBridge(mcp_client=mock_client)
        messages = [{"role": "user", "content": "Hello"}]

        response = await bridge.request_sampling(
            messages=messages,
            max_tokens=100,
            model_hints=["claude-3-sonnet", "gpt-4"],
            intelligence_priority=0.8,
            speed_priority=0.2,
        )

        assert response.model == "claude-3-sonnet"
        mock_client.create_message.assert_called_once()

        # Verify model preferences were passed
        call_kwargs = mock_client.create_message.call_args.kwargs
        assert call_kwargs["model_preferences"]["intelligencePriority"] == 0.8
        assert call_kwargs["model_preferences"]["speedPriority"] == 0.2

    # =========================================================================
    # Bridge Elicitation Methods
    # =========================================================================

    @pytest.mark.asyncio
    async def test_bridge_request_user_input_uses_form_mode(self) -> None:
        """GIVEN an MCPBridge
        WHEN request_user_input() is called
        THEN it uses form elicitation mode
        """
        from mcp_server_langgraph.api.v1.mcp_bridge import (
            MCPBridge,
            MCPClient,
            ElicitationResponse,
            ElicitationAction,
            ElicitationMode,
        )

        mock_client = MagicMock(spec=MCPClient)
        mock_client.create_elicitation = AsyncMock(
            return_value=ElicitationResponse(
                action=ElicitationAction.ACCEPT,
                content={"name": "Alice"},
            )
        )

        bridge = MCPBridge(mcp_client=mock_client)
        schema = {"type": "object", "properties": {"name": {"type": "string"}}}

        response = await bridge.request_user_input(
            message="Enter your name",
            schema=schema,
        )

        assert response.action == ElicitationAction.ACCEPT
        mock_client.create_elicitation.assert_called_once_with(
            message="Enter your name",
            mode=ElicitationMode.FORM,
            requested_schema=schema,
        )

    @pytest.mark.asyncio
    async def test_bridge_request_user_url_action_uses_url_mode(self) -> None:
        """GIVEN an MCPBridge
        WHEN request_user_url_action() is called
        THEN it uses url elicitation mode
        """
        from mcp_server_langgraph.api.v1.mcp_bridge import (
            MCPBridge,
            MCPClient,
            ElicitationResponse,
            ElicitationAction,
            ElicitationMode,
        )

        mock_client = MagicMock(spec=MCPClient)
        mock_client.create_elicitation = AsyncMock(
            return_value=ElicitationResponse(
                action=ElicitationAction.ACCEPT,
                content=None,
            )
        )

        bridge = MCPBridge(mcp_client=mock_client)

        response = await bridge.request_user_url_action(
            message="Please authenticate via OAuth",
            url="https://oauth.example.com/authorize",
        )

        assert response.action == ElicitationAction.ACCEPT
        mock_client.create_elicitation.assert_called_once_with(
            message="Please authenticate via OAuth",
            mode=ElicitationMode.URL,
            url="https://oauth.example.com/authorize",
        )

    # =========================================================================
    # Bridge Task Methods
    # =========================================================================

    @pytest.mark.asyncio
    async def test_bridge_list_tasks_aggregates_paginated_results(self) -> None:
        """GIVEN an MCPClient that returns paginated tasks
        WHEN bridge.list_tasks() is called
        THEN it aggregates all pages
        """
        from mcp_server_langgraph.api.v1.mcp_bridge import (
            MCPBridge,
            MCPClient,
            MCPTask,
            TaskStatus,
        )
        from datetime import datetime

        mock_client = MagicMock(spec=MCPClient)

        # First page returns 2 tasks with cursor
        # Second page returns 1 task without cursor
        mock_client.list_tasks = AsyncMock(
            side_effect=[
                (
                    [
                        MCPTask(
                            task_id="task-1",
                            status=TaskStatus.WORKING,
                            created_at=datetime.now(),
                            last_updated_at=datetime.now(),
                        ),
                        MCPTask(
                            task_id="task-2",
                            status=TaskStatus.WORKING,
                            created_at=datetime.now(),
                            last_updated_at=datetime.now(),
                        ),
                    ],
                    "cursor-page-2",
                ),
                (
                    [
                        MCPTask(
                            task_id="task-3",
                            status=TaskStatus.COMPLETED,
                            created_at=datetime.now(),
                            last_updated_at=datetime.now(),
                        ),
                    ],
                    None,
                ),
            ]
        )

        bridge = MCPBridge(mcp_client=mock_client)
        tasks = await bridge.list_tasks()

        assert len(tasks) == 3
        assert tasks[0].task_id == "task-1"
        assert tasks[2].task_id == "task-3"

    @pytest.mark.asyncio
    async def test_bridge_call_tool_with_task_support(self) -> None:
        """GIVEN an MCPBridge
        WHEN call_tool() is called with as_task=True
        THEN it passes task_ttl to the client
        """
        from mcp_server_langgraph.api.v1.mcp_bridge import (
            MCPBridge,
            MCPClient,
            MCPToolResult,
        )

        mock_client = MagicMock(spec=MCPClient)
        mock_client.call_tool = AsyncMock(
            return_value=MCPToolResult(
                content=[{"type": "task", "task": {"taskId": "task-123"}}],
                is_error=False,
            )
        )

        bridge = MCPBridge(mcp_client=mock_client)

        _ = await bridge.call_tool(
            tool_name="long_running_tool",
            arguments={"input": "data"},
            as_task=True,
            task_ttl=120000,
        )

        mock_client.call_tool.assert_called_once_with(
            "long_running_tool",
            {"input": "data"},
            task_ttl=120000,
        )
