"""
TDD Tests for MCP Streamable HTTP Transport

These tests verify the Streamable HTTP transport implementation for MCP client sessions.
Written FIRST before implementation (RED phase) per ADR-0082.

Reference: https://modelcontextprotocol.io/specification/2025-11-25/basic/transports
"""

import gc
from typing import Any
from unittest.mock import AsyncMock, MagicMock, patch

import pytest


MCP_PROTOCOL_VERSION = "2025-11-25"


pytestmark = pytest.mark.unit


@pytest.mark.xdist_group(name="mcp_http_transport")
class TestMCPHTTPTransportConnect:
    """Test suite for HTTP transport connection."""

    def teardown_method(self):
        """Force GC to prevent mock accumulation in xdist workers."""
        gc.collect()

    @pytest.mark.unit
    @pytest.mark.asyncio
    async def test_connect_sends_initialize_request_via_http(self):
        """GIVEN an MCPClientSession with HTTP config
        WHEN connect is called
        THEN it sends an initialize request via HTTP POST"""
        from mcp_server_langgraph.mcp.client.session_manager import MCPClientSession
        from mcp_server_langgraph.mcp.client.tool_registry import MCPServerConfig

        config = MCPServerConfig(
            name="test-server",
            url="http://localhost:8080/mcp",
        )

        session = MCPClientSession(config)

        # Mock HTTP response (must be async context manager for aiohttp)
        mock_response = MagicMock()
        mock_response.status = 200
        mock_response.json = AsyncMock(
            return_value={
                "jsonrpc": "2.0",
                "id": "init-id",
                "result": {
                    "protocolVersion": MCP_PROTOCOL_VERSION,
                    "capabilities": {"tools": {}},
                    "serverInfo": {"name": "test-http", "version": "1.0"},
                },
            }
        )
        mock_response.headers = {"MCP-Session-Id": "session-123"}
        # Make response an async context manager
        mock_response.__aenter__ = AsyncMock(return_value=mock_response)
        mock_response.__aexit__ = AsyncMock(return_value=None)

        # Mock the HTTP client - post() returns async context manager
        mock_client = MagicMock()
        mock_client.post = MagicMock(return_value=mock_response)
        mock_client.close = AsyncMock(return_value=None)

        with patch("aiohttp.ClientSession", return_value=mock_client):
            await session.connect()

        mock_client.post.assert_called()
        # Verify initialize request was sent (first call, before notifications/initialized)
        first_call_kwargs = mock_client.post.call_args_list[0].kwargs
        assert first_call_kwargs.get("json", {}).get("method") == "initialize"

    @pytest.mark.unit
    @pytest.mark.asyncio
    async def test_connect_includes_mcp_headers(self):
        """GIVEN an MCPClientSession with HTTP config
        WHEN connect is called
        THEN request includes required MCP headers"""
        from mcp_server_langgraph.mcp.client.session_manager import MCPClientSession
        from mcp_server_langgraph.mcp.client.tool_registry import MCPServerConfig

        config = MCPServerConfig(
            name="test-server",
            url="http://localhost:8080/mcp",
        )

        session = MCPClientSession(config)

        # Mock HTTP response (must be async context manager)
        mock_response = MagicMock()
        mock_response.status = 200
        mock_response.json = AsyncMock(
            return_value={
                "jsonrpc": "2.0",
                "id": "init-id",
                "result": {
                    "protocolVersion": MCP_PROTOCOL_VERSION,
                    "capabilities": {"tools": {}},
                    "serverInfo": {"name": "test-http", "version": "1.0"},
                },
            }
        )
        mock_response.headers = {}
        mock_response.__aenter__ = AsyncMock(return_value=mock_response)
        mock_response.__aexit__ = AsyncMock(return_value=None)

        mock_client = MagicMock()
        mock_client.post = MagicMock(return_value=mock_response)
        mock_client.close = AsyncMock(return_value=None)

        with patch("aiohttp.ClientSession", return_value=mock_client):
            await session.connect()

        # Check headers on first call (initialize request)
        first_call_kwargs = mock_client.post.call_args_list[0].kwargs
        headers = first_call_kwargs.get("headers", {})
        assert headers.get("MCP-Protocol-Version") == MCP_PROTOCOL_VERSION
        assert "application/json" in headers.get("Accept", "")
        assert headers.get("Content-Type") == "application/json"

    @pytest.mark.unit
    @pytest.mark.asyncio
    async def test_connect_stores_session_id(self):
        """GIVEN HTTP server returns MCP-Session-Id header
        WHEN connect succeeds
        THEN session ID is stored for subsequent requests"""
        from mcp_server_langgraph.mcp.client.session_manager import MCPClientSession
        from mcp_server_langgraph.mcp.client.tool_registry import MCPServerConfig

        config = MCPServerConfig(
            name="test-server",
            url="http://localhost:8080/mcp",
        )

        session = MCPClientSession(config)

        # Mock HTTP response with session ID (must be async context manager)
        mock_response = MagicMock()
        mock_response.status = 200
        mock_response.json = AsyncMock(
            return_value={
                "jsonrpc": "2.0",
                "id": "init-id",
                "result": {
                    "protocolVersion": MCP_PROTOCOL_VERSION,
                    "capabilities": {"tools": {}},
                    "serverInfo": {"name": "test-http", "version": "1.0"},
                },
            }
        )
        mock_response.headers = {"MCP-Session-Id": "session-abc123"}
        mock_response.__aenter__ = AsyncMock(return_value=mock_response)
        mock_response.__aexit__ = AsyncMock(return_value=None)

        mock_client = MagicMock()
        mock_client.post = MagicMock(return_value=mock_response)
        mock_client.close = AsyncMock(return_value=None)

        with patch("aiohttp.ClientSession", return_value=mock_client):
            await session.connect()

        assert session._session_id == "session-abc123"

    @pytest.mark.unit
    @pytest.mark.asyncio
    async def test_connect_stores_server_capabilities(self):
        """GIVEN HTTP server returns initialize result
        WHEN connect succeeds
        THEN server capabilities are stored"""
        from mcp_server_langgraph.mcp.client.session_manager import MCPClientSession
        from mcp_server_langgraph.mcp.client.tool_registry import MCPServerConfig

        config = MCPServerConfig(
            name="test-server",
            url="http://localhost:8080/mcp",
        )

        session = MCPClientSession(config)

        mock_response = MagicMock()
        mock_response.status = 200
        mock_response.json = AsyncMock(
            return_value={
                "jsonrpc": "2.0",
                "id": "init-id",
                "result": {
                    "protocolVersion": MCP_PROTOCOL_VERSION,
                    "capabilities": {
                        "tools": {"listChanged": True},
                        "resources": {"subscribe": False},
                    },
                    "serverInfo": {"name": "playwright-http", "version": "2.0"},
                },
            }
        )
        mock_response.headers = {}
        mock_response.__aenter__ = AsyncMock(return_value=mock_response)
        mock_response.__aexit__ = AsyncMock(return_value=None)

        mock_client = MagicMock()
        mock_client.post = MagicMock(return_value=mock_response)
        mock_client.close = AsyncMock(return_value=None)

        with patch("aiohttp.ClientSession", return_value=mock_client):
            await session.connect()

        assert session.server_info is not None
        assert session.server_info.server_name == "playwright-http"
        assert session.server_info.has_tools is True
        assert session.server_info.tools_list_changed is True


@pytest.mark.xdist_group(name="mcp_http_transport")
class TestMCPHTTPTransportToolOperations:
    """Test suite for HTTP transport tool operations."""

    def teardown_method(self):
        """Force GC to prevent mock accumulation in xdist workers."""
        gc.collect()

    @pytest.mark.unit
    @pytest.mark.asyncio
    async def test_list_tools_sends_request_with_session_id(self):
        """GIVEN a connected HTTP session
        WHEN list_tools is called
        THEN it sends tools/list request with session ID header"""
        from mcp_server_langgraph.mcp.client.session_manager import MCPClientSession
        from mcp_server_langgraph.mcp.client.tool_registry import MCPServerConfig

        config = MCPServerConfig(
            name="test-server",
            url="http://localhost:8080/mcp",
        )

        session = MCPClientSession(config)

        # Track requests
        requests_sent: list[dict[str, Any]] = []

        def track_request(*args, **kwargs):
            requests_sent.append(kwargs)
            method = kwargs.get("json", {}).get("method")
            if method == "initialize":
                return _make_init_response()
            if method == "notifications/initialized":
                # Return a simple response for notification
                mock = MagicMock()
                mock.status = 200
                mock.__aenter__ = AsyncMock(return_value=mock)
                mock.__aexit__ = AsyncMock(return_value=None)
                return mock
            return _make_tools_list_response()

        mock_client = MagicMock()
        mock_client.post = MagicMock(side_effect=track_request)
        mock_client.close = AsyncMock(return_value=None)

        with patch("aiohttp.ClientSession", return_value=mock_client):
            await session.connect()
            await session.list_tools()

        # Find the tools/list request
        tools_requests = [r for r in requests_sent if r.get("json", {}).get("method") == "tools/list"]
        assert len(tools_requests) == 1
        headers = tools_requests[0].get("headers", {})
        # Session ID should be included if server provided one
        assert "MCP-Session-Id" in headers or session._session_id is None

    @pytest.mark.unit
    @pytest.mark.asyncio
    async def test_call_tool_sends_request(self):
        """GIVEN a connected HTTP session
        WHEN call_tool is called
        THEN it sends tools/call request with arguments"""
        from mcp_server_langgraph.mcp.client.session_manager import MCPClientSession
        from mcp_server_langgraph.mcp.client.tool_registry import MCPServerConfig

        config = MCPServerConfig(
            name="test-server",
            url="http://localhost:8080/mcp",
        )

        session = MCPClientSession(config)

        requests_sent: list[dict[str, Any]] = []

        def track_request(*args, **kwargs):
            requests_sent.append(kwargs)
            method = kwargs.get("json", {}).get("method")
            if method == "initialize":
                return _make_init_response()
            if method == "notifications/initialized":
                # Return a simple response for notification
                mock = MagicMock()
                mock.status = 200
                mock.__aenter__ = AsyncMock(return_value=mock)
                mock.__aexit__ = AsyncMock(return_value=None)
                return mock
            if method == "tools/call":
                return _make_tools_call_response()
            return _make_tools_list_response()

        mock_client = MagicMock()
        mock_client.post = MagicMock(side_effect=track_request)
        mock_client.close = AsyncMock(return_value=None)

        with patch("aiohttp.ClientSession", return_value=mock_client):
            await session.connect()
            await session.call_tool("screenshot", {"url": "https://example.com"})

        call_requests = [r for r in requests_sent if r.get("json", {}).get("method") == "tools/call"]
        assert len(call_requests) == 1
        params = call_requests[0].get("json", {}).get("params", {})
        assert params["name"] == "screenshot"
        assert params["arguments"]["url"] == "https://example.com"


@pytest.mark.xdist_group(name="mcp_http_transport")
class TestMCPHTTPTransportErrorHandling:
    """Test suite for HTTP transport error handling."""

    def teardown_method(self):
        """Force GC to prevent mock accumulation in xdist workers."""
        gc.collect()

    @pytest.mark.unit
    @pytest.mark.asyncio
    async def test_connect_raises_on_http_error(self):
        """GIVEN HTTP server returns error status
        WHEN connect is called
        THEN ConnectionError is raised"""
        from mcp_server_langgraph.mcp.client.session_manager import MCPClientSession
        from mcp_server_langgraph.mcp.client.tool_registry import MCPServerConfig

        config = MCPServerConfig(
            name="test-server",
            url="http://localhost:8080/mcp",
        )

        session = MCPClientSession(config)

        mock_response = MagicMock()
        mock_response.status = 500
        mock_response.text = AsyncMock(return_value="Internal Server Error")
        mock_response.__aenter__ = AsyncMock(return_value=mock_response)
        mock_response.__aexit__ = AsyncMock(return_value=None)

        mock_client = MagicMock()
        mock_client.post = MagicMock(return_value=mock_response)
        mock_client.close = AsyncMock(return_value=None)

        with patch("aiohttp.ClientSession", return_value=mock_client):
            with pytest.raises(ConnectionError, match="HTTP error|status"):
                await session.connect()

    @pytest.mark.unit
    @pytest.mark.asyncio
    async def test_connect_raises_on_protocol_error(self):
        """GIVEN HTTP server returns JSON-RPC error
        WHEN connect is called
        THEN ConnectionError is raised"""
        from mcp_server_langgraph.mcp.client.session_manager import MCPClientSession
        from mcp_server_langgraph.mcp.client.tool_registry import MCPServerConfig

        config = MCPServerConfig(
            name="test-server",
            url="http://localhost:8080/mcp",
        )

        session = MCPClientSession(config)

        mock_response = MagicMock()
        mock_response.status = 200
        mock_response.json = AsyncMock(
            return_value={
                "jsonrpc": "2.0",
                "id": "init-id",
                "error": {
                    "code": -32600,
                    "message": "Invalid Request",
                },
            }
        )
        mock_response.headers = {}
        mock_response.__aenter__ = AsyncMock(return_value=mock_response)
        mock_response.__aexit__ = AsyncMock(return_value=None)

        mock_client = MagicMock()
        mock_client.post = MagicMock(return_value=mock_response)
        mock_client.close = AsyncMock(return_value=None)

        with patch("aiohttp.ClientSession", return_value=mock_client):
            with pytest.raises(ConnectionError, match="Initialize failed"):
                await session.connect()


# Helper functions for creating mock responses (must be async context managers)
def _make_init_response():
    mock = MagicMock()
    mock.status = 200
    mock.json = AsyncMock(
        return_value={
            "jsonrpc": "2.0",
            "id": "init-id",
            "result": {
                "protocolVersion": MCP_PROTOCOL_VERSION,
                "capabilities": {"tools": {}},
                "serverInfo": {"name": "test-http", "version": "1.0"},
            },
        }
    )
    mock.headers = {"MCP-Session-Id": "session-123"}
    mock.__aenter__ = AsyncMock(return_value=mock)
    mock.__aexit__ = AsyncMock(return_value=None)
    return mock


def _make_tools_list_response():
    mock = MagicMock()
    mock.status = 200
    mock.json = AsyncMock(
        return_value={
            "jsonrpc": "2.0",
            "id": "tools-id",
            "result": {
                "tools": [
                    {"name": "screenshot", "description": "Take screenshot", "inputSchema": {}},
                ],
            },
        }
    )
    mock.headers = {}
    mock.__aenter__ = AsyncMock(return_value=mock)
    mock.__aexit__ = AsyncMock(return_value=None)
    return mock


def _make_tools_call_response():
    mock = MagicMock()
    mock.status = 200
    mock.json = AsyncMock(
        return_value={
            "jsonrpc": "2.0",
            "id": "call-id",
            "result": {
                "content": [{"type": "text", "text": "Screenshot saved"}],
                "isError": False,
            },
        }
    )
    mock.headers = {}
    mock.__aenter__ = AsyncMock(return_value=mock)
    mock.__aexit__ = AsyncMock(return_value=None)
    return mock
