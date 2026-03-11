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


def _make_http_response(
    *,
    status: int = 200,
    json_data: dict[str, Any] | None = None,
    headers: dict[str, str] | None = None,
    text: str = "",
) -> MagicMock:
    """Create a properly-configured aiohttp response mock.

    Returns a fresh MagicMock that works as an async context manager with
    concrete integer ``status``, avoiding auto-generated MagicMock attributes
    that cause ``TypeError: '>=' not supported between instances of
    'AsyncMock' and 'int'`` under xdist parallel execution.
    """
    mock = MagicMock()
    mock.status = status
    mock.headers = headers if headers is not None else {}
    mock.json = AsyncMock(return_value=json_data if json_data is not None else {})
    mock.text = AsyncMock(return_value=text)
    mock.__aenter__ = AsyncMock(return_value=mock)
    mock.__aexit__ = AsyncMock(return_value=None)
    return mock


def _make_init_json(
    *,
    server_name: str = "test-http",
    server_version: str = "1.0",
    capabilities: dict[str, Any] | None = None,
) -> dict[str, Any]:
    """Build a standard MCP initialize JSON-RPC response body."""
    return {
        "jsonrpc": "2.0",
        "id": "init-id",
        "result": {
            "protocolVersion": MCP_PROTOCOL_VERSION,
            "capabilities": capabilities if capabilities is not None else {"tools": {}},
            "serverInfo": {"name": server_name, "version": server_version},
        },
    }


def _make_init_response(
    *,
    session_id: str | None = "session-123",
    server_name: str = "test-http",
    server_version: str = "1.0",
    capabilities: dict[str, Any] | None = None,
) -> MagicMock:
    """Create a mock aiohttp response for the MCP ``initialize`` handshake."""
    headers = {"MCP-Session-Id": session_id} if session_id else {}
    return _make_http_response(
        status=200,
        json_data=_make_init_json(
            server_name=server_name,
            server_version=server_version,
            capabilities=capabilities,
        ),
        headers=headers,
    )


def _make_notification_response() -> MagicMock:
    """Create a mock aiohttp response for the ``notifications/initialized`` POST."""
    return _make_http_response(status=200)


def _make_tools_list_response() -> MagicMock:
    """Create a mock aiohttp response for ``tools/list``."""
    return _make_http_response(
        status=200,
        json_data={
            "jsonrpc": "2.0",
            "id": "tools-id",
            "result": {
                "tools": [
                    {"name": "screenshot", "description": "Take screenshot", "inputSchema": {}},
                ],
            },
        },
    )


def _make_tools_call_response() -> MagicMock:
    """Create a mock aiohttp response for ``tools/call``."""
    return _make_http_response(
        status=200,
        json_data={
            "jsonrpc": "2.0",
            "id": "call-id",
            "result": {
                "content": [{"type": "text", "text": "Screenshot saved"}],
                "isError": False,
            },
        },
    )


def _route_post(*args: Any, **kwargs: Any) -> MagicMock:
    """Default POST router: dispatch by ``method`` field in the JSON body.

    Always returns a *fresh* mock so that each ``async with`` block gets its
    own context-manager instance with a concrete ``.status`` integer.

    Accepts the same signature as ``aiohttp.ClientSession.post(url, *, json=, headers=)``.
    """
    json_body = kwargs.get("json") or {}
    method = json_body.get("method")
    if method == "initialize":
        return _make_init_response()
    if method == "notifications/initialized":
        return _make_notification_response()
    if method == "tools/list":
        return _make_tools_list_response()
    if method == "tools/call":
        return _make_tools_call_response()
    # Fallback: return a generic 200 response
    return _make_http_response(status=200)


def _make_http_client(
    *,
    side_effect: Any = None,
) -> MagicMock:
    """Create a mock ``aiohttp.ClientSession`` with routed ``post()``.

    By default, ``post()`` dispatches to ``_route_post`` so each call gets a
    *fresh* response mock, preventing xdist cross-test mock leakage.
    """
    mock_client = MagicMock()
    mock_client.post = MagicMock(side_effect=side_effect if side_effect is not None else _route_post)
    mock_client.close = AsyncMock(return_value=None)
    return mock_client


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

        mock_client = _make_http_client()

        with patch("aiohttp.ClientSession", side_effect=lambda *a, **kw: mock_client):
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

        mock_client = _make_http_client()

        with patch("aiohttp.ClientSession", side_effect=lambda *a, **kw: mock_client):
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

        # Use a custom init response with a specific session ID
        def route_with_session_id(*args, **kwargs):
            method = kwargs.get("json", {}).get("method")
            if method == "initialize":
                return _make_init_response(session_id="session-abc123")
            return _route_post(*args, **kwargs)

        mock_client = _make_http_client(side_effect=route_with_session_id)

        with patch("aiohttp.ClientSession", side_effect=lambda *a, **kw: mock_client):
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

        # Use a custom init response with specific capabilities
        def route_with_capabilities(*args, **kwargs):
            method = kwargs.get("json", {}).get("method")
            if method == "initialize":
                return _make_init_response(
                    server_name="playwright-http",
                    server_version="2.0",
                    capabilities={
                        "tools": {"listChanged": True},
                        "resources": {"subscribe": False},
                    },
                )
            return _route_post(*args, **kwargs)

        mock_client = _make_http_client(side_effect=route_with_capabilities)

        with patch("aiohttp.ClientSession", side_effect=lambda *a, **kw: mock_client):
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
            return _route_post(**kwargs)

        mock_client = _make_http_client(side_effect=track_request)

        with patch("aiohttp.ClientSession", side_effect=lambda *a, **kw: mock_client):
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
            return _route_post(**kwargs)

        mock_client = _make_http_client(side_effect=track_request)

        with patch("aiohttp.ClientSession", side_effect=lambda *a, **kw: mock_client):
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

        # The initialize POST must return an error response
        def route_error(*args, **kwargs):
            method = kwargs.get("json", {}).get("method")
            if method == "initialize":
                return _make_http_response(
                    status=500,
                    text="Internal Server Error",
                )
            return _route_post(*args, **kwargs)

        mock_client = _make_http_client(side_effect=route_error)

        with patch("aiohttp.ClientSession", side_effect=lambda *a, **kw: mock_client):
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

        # The initialize POST returns HTTP 200 but a JSON-RPC error body
        def route_protocol_error(*args, **kwargs):
            method = kwargs.get("json", {}).get("method")
            if method == "initialize":
                return _make_http_response(
                    status=200,
                    json_data={
                        "jsonrpc": "2.0",
                        "id": "init-id",
                        "error": {
                            "code": -32600,
                            "message": "Invalid Request",
                        },
                    },
                    headers={},
                )
            return _route_post(*args, **kwargs)

        mock_client = _make_http_client(side_effect=route_protocol_error)

        with patch("aiohttp.ClientSession", side_effect=lambda *a, **kw: mock_client):
            with pytest.raises(ConnectionError, match="Initialize failed"):
                await session.connect()
