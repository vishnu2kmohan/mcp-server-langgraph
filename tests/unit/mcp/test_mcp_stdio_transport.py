"""
TDD Tests for MCP STDIO Transport

These tests verify the STDIO transport implementation for MCP client sessions.
Written FIRST before implementation (RED phase) per ADR-0082.

Reference: https://modelcontextprotocol.io/specification/2025-11-25/basic/transports
"""

import gc
import json
from unittest.mock import AsyncMock, MagicMock, patch

import pytest


MCP_PROTOCOL_VERSION = "2025-11-25"


pytestmark = pytest.mark.unit


@pytest.mark.xdist_group(name="mcp_stdio_transport")
class TestMCPSTDIOTransportConnect:
    """Test suite for STDIO transport connection."""

    def teardown_method(self):
        """Force GC to prevent mock accumulation in xdist workers."""
        gc.collect()

    @pytest.mark.unit
    @pytest.mark.asyncio
    async def test_connect_spawns_subprocess(self):
        """GIVEN an MCPClientSession with STDIO config
        WHEN connect is called
        THEN it spawns a subprocess with the command"""
        from mcp_server_langgraph.mcp.client.session_manager import MCPClientSession
        from mcp_server_langgraph.mcp.client.tool_registry import MCPServerConfig

        config = MCPServerConfig(
            name="test-server",
            command="echo",
            args=["test"],
        )

        session = MCPClientSession(config)

        # Mock subprocess creation
        mock_process = AsyncMock(return_value=None)
        mock_stdin = MagicMock()
        mock_stdin.write = MagicMock()
        mock_stdin.drain = AsyncMock(return_value=None)
        mock_process.stdin = mock_stdin
        mock_process.stdout = AsyncMock(return_value=None)
        mock_process.returncode = None

        # Mock the initialize response
        init_response = (
            json.dumps(
                {
                    "jsonrpc": "2.0",
                    "id": "mock-id",
                    "result": {
                        "protocolVersion": MCP_PROTOCOL_VERSION,
                        "capabilities": {"tools": {}},
                        "serverInfo": {"name": "test", "version": "1.0"},
                    },
                }
            )
            + "\n"
        )
        mock_process.stdout.readline = AsyncMock(return_value=init_response.encode())

        with patch("asyncio.create_subprocess_exec", return_value=mock_process) as mock_exec:
            await session.connect()

            mock_exec.assert_called_once()
            call_args = mock_exec.call_args
            assert call_args[0][0] == "echo"
            assert call_args[0][1] == "test"

    @pytest.mark.unit
    @pytest.mark.asyncio
    async def test_connect_sends_initialize_request(self):
        """GIVEN an MCPClientSession
        WHEN connect is called
        THEN it sends an initialize request over stdin"""
        from mcp_server_langgraph.mcp.client.session_manager import MCPClientSession
        from mcp_server_langgraph.mcp.client.tool_registry import MCPServerConfig

        config = MCPServerConfig(
            name="test-server",
            command="echo",
            args=[],
        )

        session = MCPClientSession(config)

        mock_process = AsyncMock(return_value=None)
        mock_stdin = MagicMock()
        mock_process.stdin = mock_stdin
        mock_process.stdout = AsyncMock(return_value=None)
        mock_process.returncode = None

        # Capture what's written to stdin
        written_data: list[bytes] = []
        mock_stdin.write = MagicMock(side_effect=lambda data: written_data.append(data))
        mock_stdin.drain = AsyncMock(return_value=None)

        # Mock the initialize response
        init_response = (
            json.dumps(
                {
                    "jsonrpc": "2.0",
                    "id": "any",
                    "result": {
                        "protocolVersion": MCP_PROTOCOL_VERSION,
                        "capabilities": {"tools": {}},
                        "serverInfo": {"name": "test", "version": "1.0"},
                    },
                }
            )
            + "\n"
        )
        mock_process.stdout.readline = AsyncMock(return_value=init_response.encode())

        with patch("asyncio.create_subprocess_exec", return_value=mock_process):
            await session.connect()

        # Check that initialize request was sent
        assert len(written_data) >= 1
        init_request = json.loads(written_data[0].decode())
        assert init_request["method"] == "initialize"
        assert init_request["jsonrpc"] == "2.0"
        assert "protocolVersion" in init_request["params"]

    @pytest.mark.unit
    @pytest.mark.asyncio
    async def test_connect_sends_initialized_notification(self):
        """GIVEN an MCPClientSession
        WHEN initialize succeeds
        THEN it sends initialized notification"""
        from mcp_server_langgraph.mcp.client.session_manager import MCPClientSession
        from mcp_server_langgraph.mcp.client.tool_registry import MCPServerConfig

        config = MCPServerConfig(
            name="test-server",
            command="echo",
            args=[],
        )

        session = MCPClientSession(config)

        mock_process = AsyncMock(return_value=None)
        mock_stdin = MagicMock()
        mock_process.stdin = mock_stdin
        mock_process.stdout = AsyncMock(return_value=None)
        mock_process.returncode = None

        # Capture what's written to stdin
        written_data: list[bytes] = []
        mock_stdin.write = MagicMock(side_effect=lambda data: written_data.append(data))
        mock_stdin.drain = AsyncMock(return_value=None)

        # Mock the initialize response
        init_response = (
            json.dumps(
                {
                    "jsonrpc": "2.0",
                    "id": "any",
                    "result": {
                        "protocolVersion": MCP_PROTOCOL_VERSION,
                        "capabilities": {"tools": {}},
                        "serverInfo": {"name": "test", "version": "1.0"},
                    },
                }
            )
            + "\n"
        )
        mock_process.stdout.readline = AsyncMock(return_value=init_response.encode())

        with patch("asyncio.create_subprocess_exec", return_value=mock_process):
            await session.connect()

        # Check that initialized notification was sent (second write)
        assert len(written_data) >= 2
        initialized_notification = json.loads(written_data[1].decode())
        assert initialized_notification["method"] == "notifications/initialized"
        assert "id" not in initialized_notification  # Notifications have no id

    @pytest.mark.unit
    @pytest.mark.asyncio
    async def test_connect_stores_server_capabilities(self):
        """GIVEN an MCPClientSession
        WHEN connect succeeds
        THEN server capabilities are stored"""
        from mcp_server_langgraph.mcp.client.session_manager import MCPClientSession
        from mcp_server_langgraph.mcp.client.tool_registry import MCPServerConfig

        config = MCPServerConfig(
            name="test-server",
            command="echo",
            args=[],
        )

        session = MCPClientSession(config)

        mock_process = AsyncMock(return_value=None)
        mock_stdin = MagicMock()
        mock_process.stdin = mock_stdin
        mock_process.stdout = AsyncMock(return_value=None)
        mock_process.returncode = None
        mock_stdin.write = MagicMock()
        mock_stdin.drain = AsyncMock(return_value=None)

        # Mock the initialize response with capabilities
        init_response = (
            json.dumps(
                {
                    "jsonrpc": "2.0",
                    "id": "any",
                    "result": {
                        "protocolVersion": MCP_PROTOCOL_VERSION,
                        "capabilities": {
                            "tools": {"listChanged": True},
                            "resources": {"subscribe": True},
                        },
                        "serverInfo": {"name": "playwright", "version": "1.2.0"},
                    },
                }
            )
            + "\n"
        )
        mock_process.stdout.readline = AsyncMock(return_value=init_response.encode())

        with patch("asyncio.create_subprocess_exec", return_value=mock_process):
            await session.connect()

        # Verify server info is stored
        assert session.server_info is not None
        assert session.server_info.server_name == "playwright"
        assert session.server_info.has_tools is True
        assert session.server_info.tools_list_changed is True


@pytest.mark.xdist_group(name="mcp_stdio_transport")
class TestMCPSTDIOTransportListTools:
    """Test suite for STDIO transport tools/list."""

    def teardown_method(self):
        """Force GC to prevent mock accumulation in xdist workers."""
        gc.collect()

    @pytest.mark.unit
    @pytest.mark.asyncio
    async def test_list_tools_sends_request(self):
        """GIVEN a connected MCPClientSession
        WHEN list_tools is called
        THEN it sends tools/list request"""
        from mcp_server_langgraph.mcp.client.session_manager import MCPClientSession
        from mcp_server_langgraph.mcp.client.tool_registry import MCPServerConfig

        config = MCPServerConfig(
            name="test-server",
            command="echo",
            args=[],
        )

        session = MCPClientSession(config)

        mock_process = AsyncMock(return_value=None)
        mock_stdin = MagicMock()
        mock_process.stdin = mock_stdin
        mock_process.stdout = AsyncMock(return_value=None)
        mock_process.returncode = None

        written_data: list[bytes] = []
        mock_stdin.write = MagicMock(side_effect=lambda data: written_data.append(data))
        mock_stdin.drain = AsyncMock(return_value=None)

        # Responses: initialize, then tools/list
        responses = [
            json.dumps(
                {
                    "jsonrpc": "2.0",
                    "id": "init",
                    "result": {
                        "protocolVersion": MCP_PROTOCOL_VERSION,
                        "capabilities": {"tools": {}},
                        "serverInfo": {"name": "test", "version": "1.0"},
                    },
                }
            )
            + "\n",
            json.dumps(
                {
                    "jsonrpc": "2.0",
                    "id": "tools",
                    "result": {
                        "tools": [
                            {"name": "screenshot", "description": "Take screenshot", "inputSchema": {}},
                        ],
                    },
                }
            )
            + "\n",
        ]
        response_iter = iter(responses)
        mock_process.stdout.readline = AsyncMock(side_effect=lambda: next(response_iter).encode())

        with patch("asyncio.create_subprocess_exec", return_value=mock_process):
            await session.connect()
            await session.list_tools()

        # Find the tools/list request in written data
        tools_requests = [json.loads(d.decode()) for d in written_data if b"tools/list" in d]
        assert len(tools_requests) == 1
        assert tools_requests[0]["method"] == "tools/list"

    @pytest.mark.unit
    @pytest.mark.asyncio
    async def test_list_tools_returns_parsed_tools(self):
        """GIVEN a connected MCPClientSession
        WHEN list_tools is called
        THEN it returns parsed tool definitions"""
        from mcp_server_langgraph.mcp.client.session_manager import MCPClientSession
        from mcp_server_langgraph.mcp.client.tool_registry import MCPServerConfig

        config = MCPServerConfig(name="test-server", command="echo", args=[])
        session = MCPClientSession(config)

        mock_process = AsyncMock(return_value=None)
        mock_stdin = MagicMock()
        mock_process.stdin = mock_stdin
        mock_process.stdout = AsyncMock(return_value=None)
        mock_process.returncode = None
        mock_stdin.write = MagicMock()
        mock_stdin.drain = AsyncMock(return_value=None)

        # Responses: initialize, then tools/list
        responses = [
            json.dumps(
                {
                    "jsonrpc": "2.0",
                    "id": "init",
                    "result": {
                        "protocolVersion": MCP_PROTOCOL_VERSION,
                        "capabilities": {"tools": {}},
                        "serverInfo": {"name": "test", "version": "1.0"},
                    },
                }
            )
            + "\n",
            json.dumps(
                {
                    "jsonrpc": "2.0",
                    "id": "tools",
                    "result": {
                        "tools": [
                            {
                                "name": "screenshot",
                                "description": "Take a screenshot",
                                "inputSchema": {
                                    "type": "object",
                                    "properties": {"url": {"type": "string"}},
                                },
                            },
                            {
                                "name": "click",
                                "description": "Click element",
                                "inputSchema": {"type": "object"},
                            },
                        ],
                    },
                }
            )
            + "\n",
        ]
        response_iter = iter(responses)
        mock_process.stdout.readline = AsyncMock(side_effect=lambda: next(response_iter).encode())

        with patch("asyncio.create_subprocess_exec", return_value=mock_process):
            await session.connect()
            tools = await session.list_tools()

        assert len(tools) == 2
        assert tools[0]["name"] == "screenshot"
        assert tools[1]["name"] == "click"


@pytest.mark.xdist_group(name="mcp_stdio_transport")
class TestMCPSTDIOTransportCallTool:
    """Test suite for STDIO transport tools/call."""

    def teardown_method(self):
        """Force GC to prevent mock accumulation in xdist workers."""
        gc.collect()

    @pytest.mark.unit
    @pytest.mark.asyncio
    async def test_call_tool_sends_request(self):
        """GIVEN a connected MCPClientSession
        WHEN call_tool is called
        THEN it sends tools/call request with arguments"""
        from mcp_server_langgraph.mcp.client.session_manager import MCPClientSession
        from mcp_server_langgraph.mcp.client.tool_registry import MCPServerConfig

        config = MCPServerConfig(name="test-server", command="echo", args=[])
        session = MCPClientSession(config)

        mock_process = AsyncMock(return_value=None)
        mock_stdin = MagicMock()
        mock_process.stdin = mock_stdin
        mock_process.stdout = AsyncMock(return_value=None)
        mock_process.returncode = None

        written_data: list[bytes] = []
        mock_stdin.write = MagicMock(side_effect=lambda data: written_data.append(data))
        mock_stdin.drain = AsyncMock(return_value=None)

        # Responses: initialize, then tools/call
        responses = [
            json.dumps(
                {
                    "jsonrpc": "2.0",
                    "id": "init",
                    "result": {
                        "protocolVersion": MCP_PROTOCOL_VERSION,
                        "capabilities": {"tools": {}},
                        "serverInfo": {"name": "test", "version": "1.0"},
                    },
                }
            )
            + "\n",
            json.dumps(
                {
                    "jsonrpc": "2.0",
                    "id": "call",
                    "result": {
                        "content": [{"type": "text", "text": "Screenshot saved"}],
                        "isError": False,
                    },
                }
            )
            + "\n",
        ]
        response_iter = iter(responses)
        mock_process.stdout.readline = AsyncMock(side_effect=lambda: next(response_iter).encode())

        with patch("asyncio.create_subprocess_exec", return_value=mock_process):
            await session.connect()
            await session.call_tool("screenshot", {"url": "https://example.com"})

        # Find the tools/call request
        call_requests = [json.loads(d.decode()) for d in written_data if b"tools/call" in d]
        assert len(call_requests) == 1
        assert call_requests[0]["method"] == "tools/call"
        assert call_requests[0]["params"]["name"] == "screenshot"
        assert call_requests[0]["params"]["arguments"]["url"] == "https://example.com"

    @pytest.mark.unit
    @pytest.mark.asyncio
    async def test_call_tool_returns_content(self):
        """GIVEN a successful tool call
        WHEN result is returned
        THEN content is extracted correctly"""
        from mcp_server_langgraph.mcp.client.session_manager import MCPClientSession
        from mcp_server_langgraph.mcp.client.tool_registry import MCPServerConfig

        config = MCPServerConfig(name="test-server", command="echo", args=[])
        session = MCPClientSession(config)

        mock_process = AsyncMock(return_value=None)
        mock_stdin = MagicMock()
        mock_process.stdin = mock_stdin
        mock_process.stdout = AsyncMock(return_value=None)
        mock_process.returncode = None
        mock_stdin.write = MagicMock()
        mock_stdin.drain = AsyncMock(return_value=None)

        # Responses: initialize, then tools/call
        responses = [
            json.dumps(
                {
                    "jsonrpc": "2.0",
                    "id": "init",
                    "result": {
                        "protocolVersion": MCP_PROTOCOL_VERSION,
                        "capabilities": {"tools": {}},
                        "serverInfo": {"name": "test", "version": "1.0"},
                    },
                }
            )
            + "\n",
            json.dumps(
                {
                    "jsonrpc": "2.0",
                    "id": "call",
                    "result": {
                        "content": [
                            {"type": "text", "text": "Screenshot saved to /tmp/shot.png"},
                            {"type": "image", "data": "base64...", "mimeType": "image/png"},
                        ],
                        "isError": False,
                    },
                }
            )
            + "\n",
        ]
        response_iter = iter(responses)
        mock_process.stdout.readline = AsyncMock(side_effect=lambda: next(response_iter).encode())

        with patch("asyncio.create_subprocess_exec", return_value=mock_process):
            await session.connect()
            result = await session.call_tool("screenshot", {"url": "https://example.com"})

        assert "content" in result
        assert len(result["content"]) == 2
        assert result["content"][0]["type"] == "text"
        assert result["isError"] is False

    @pytest.mark.unit
    @pytest.mark.asyncio
    async def test_call_tool_handles_error_response(self):
        """GIVEN a tool that returns isError=True
        WHEN call_tool is called
        THEN the error is returned in result"""
        from mcp_server_langgraph.mcp.client.session_manager import MCPClientSession
        from mcp_server_langgraph.mcp.client.tool_registry import MCPServerConfig

        config = MCPServerConfig(name="test-server", command="echo", args=[])
        session = MCPClientSession(config)

        mock_process = AsyncMock(return_value=None)
        mock_stdin = MagicMock()
        mock_process.stdin = mock_stdin
        mock_process.stdout = AsyncMock(return_value=None)
        mock_process.returncode = None
        mock_stdin.write = MagicMock()
        mock_stdin.drain = AsyncMock(return_value=None)

        # Responses: initialize, then tools/call with error
        responses = [
            json.dumps(
                {
                    "jsonrpc": "2.0",
                    "id": "init",
                    "result": {
                        "protocolVersion": MCP_PROTOCOL_VERSION,
                        "capabilities": {"tools": {}},
                        "serverInfo": {"name": "test", "version": "1.0"},
                    },
                }
            )
            + "\n",
            json.dumps(
                {
                    "jsonrpc": "2.0",
                    "id": "call",
                    "result": {
                        "content": [
                            {"type": "text", "text": "Error: Element not found"},
                        ],
                        "isError": True,
                    },
                }
            )
            + "\n",
        ]
        response_iter = iter(responses)
        mock_process.stdout.readline = AsyncMock(side_effect=lambda: next(response_iter).encode())

        with patch("asyncio.create_subprocess_exec", return_value=mock_process):
            await session.connect()
            result = await session.call_tool("click", {"selector": ".missing"})

        assert result["isError"] is True
        assert "Error" in result["content"][0]["text"]


@pytest.mark.xdist_group(name="mcp_stdio_transport")
class TestMCPSTDIOTransportDisconnect:
    """Test suite for STDIO transport disconnection."""

    def teardown_method(self):
        """Force GC to prevent mock accumulation in xdist workers."""
        gc.collect()

    @pytest.mark.unit
    @pytest.mark.asyncio
    async def test_disconnect_terminates_process(self):
        """GIVEN a connected MCPClientSession
        WHEN disconnect is called
        THEN the subprocess is terminated"""
        from mcp_server_langgraph.mcp.client.session_manager import MCPClientSession
        from mcp_server_langgraph.mcp.client.tool_registry import MCPServerConfig

        config = MCPServerConfig(name="test-server", command="echo", args=[])
        session = MCPClientSession(config)

        mock_process = AsyncMock(return_value=None)
        mock_stdin = MagicMock()
        mock_process.stdin = mock_stdin
        mock_process.stdout = AsyncMock(return_value=None)
        mock_process.returncode = None
        mock_process.terminate = MagicMock()
        mock_process.wait = AsyncMock(return_value=None)
        mock_stdin.write = MagicMock()
        mock_stdin.drain = AsyncMock(return_value=None)

        init_response = (
            json.dumps(
                {
                    "jsonrpc": "2.0",
                    "id": "init",
                    "result": {
                        "protocolVersion": MCP_PROTOCOL_VERSION,
                        "capabilities": {"tools": {}},
                        "serverInfo": {"name": "test", "version": "1.0"},
                    },
                }
            )
            + "\n"
        )
        mock_process.stdout.readline = AsyncMock(return_value=init_response.encode())

        with patch("asyncio.create_subprocess_exec", return_value=mock_process):
            await session.connect()
            assert session.is_connected is True

            await session.disconnect()

        mock_process.terminate.assert_called_once()
        assert session.is_connected is False

    @pytest.mark.unit
    @pytest.mark.asyncio
    async def test_disconnect_clears_server_info(self):
        """GIVEN a connected MCPClientSession
        WHEN disconnect is called
        THEN server_info is cleared"""
        from mcp_server_langgraph.mcp.client.session_manager import MCPClientSession
        from mcp_server_langgraph.mcp.client.tool_registry import MCPServerConfig

        config = MCPServerConfig(name="test-server", command="echo", args=[])
        session = MCPClientSession(config)

        mock_process = AsyncMock(return_value=None)
        mock_stdin = MagicMock()
        mock_process.stdin = mock_stdin
        mock_process.stdout = AsyncMock(return_value=None)
        mock_process.returncode = None
        mock_process.terminate = MagicMock()
        mock_process.wait = AsyncMock(return_value=None)
        mock_stdin.write = MagicMock()
        mock_stdin.drain = AsyncMock(return_value=None)

        init_response = (
            json.dumps(
                {
                    "jsonrpc": "2.0",
                    "id": "init",
                    "result": {
                        "protocolVersion": MCP_PROTOCOL_VERSION,
                        "capabilities": {"tools": {}},
                        "serverInfo": {"name": "test", "version": "1.0"},
                    },
                }
            )
            + "\n"
        )
        mock_process.stdout.readline = AsyncMock(return_value=init_response.encode())

        with patch("asyncio.create_subprocess_exec", return_value=mock_process):
            await session.connect()
            assert session.server_info is not None

            await session.disconnect()

        assert session.server_info is None


@pytest.mark.xdist_group(name="mcp_stdio_transport")
class TestMCPSTDIOTransportErrorHandling:
    """Test suite for STDIO transport error handling."""

    def teardown_method(self):
        """Force GC to prevent mock accumulation in xdist workers."""
        gc.collect()

    @pytest.mark.unit
    @pytest.mark.asyncio
    async def test_connect_raises_on_failed_spawn(self):
        """GIVEN invalid command
        WHEN connect is called
        THEN ConnectionError is raised"""
        from mcp_server_langgraph.mcp.client.session_manager import MCPClientSession
        from mcp_server_langgraph.mcp.client.tool_registry import MCPServerConfig

        config = MCPServerConfig(
            name="test-server",
            command="/nonexistent/command",
            args=[],
        )

        session = MCPClientSession(config)

        with patch(
            "asyncio.create_subprocess_exec",
            side_effect=FileNotFoundError("Command not found"),
        ):
            with pytest.raises(ConnectionError, match="Failed to spawn"):
                await session.connect()

    @pytest.mark.unit
    @pytest.mark.asyncio
    async def test_connect_raises_on_protocol_error(self):
        """GIVEN server returns invalid response
        WHEN connect is called
        THEN ConnectionError is raised"""
        from mcp_server_langgraph.mcp.client.session_manager import MCPClientSession
        from mcp_server_langgraph.mcp.client.tool_registry import MCPServerConfig

        config = MCPServerConfig(name="test-server", command="echo", args=[])
        session = MCPClientSession(config)

        mock_process = AsyncMock(return_value=None)
        mock_stdin = MagicMock()
        mock_process.stdin = mock_stdin
        mock_process.stdout = AsyncMock(return_value=None)
        mock_process.returncode = None
        mock_process.terminate = MagicMock()
        mock_stdin.write = MagicMock()
        mock_stdin.drain = AsyncMock(return_value=None)

        # Return error response
        error_response = (
            json.dumps(
                {
                    "jsonrpc": "2.0",
                    "id": "init",
                    "error": {
                        "code": -32600,
                        "message": "Invalid Request",
                    },
                }
            )
            + "\n"
        )
        mock_process.stdout.readline = AsyncMock(return_value=error_response.encode())

        with patch("asyncio.create_subprocess_exec", return_value=mock_process):
            with pytest.raises(ConnectionError, match="Initialize failed"):
                await session.connect()

    @pytest.mark.unit
    @pytest.mark.asyncio
    async def test_call_tool_raises_when_not_connected(self):
        """GIVEN an MCPClientSession that's not connected
        WHEN call_tool is called
        THEN ConnectionError is raised"""
        from mcp_server_langgraph.mcp.client.session_manager import MCPClientSession
        from mcp_server_langgraph.mcp.client.tool_registry import MCPServerConfig

        config = MCPServerConfig(name="test-server", command="echo", args=[])
        session = MCPClientSession(config)

        with pytest.raises(ConnectionError, match="Not connected"):
            await session.call_tool("screenshot", {"url": "https://example.com"})
