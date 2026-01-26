"""
Tests for MCP Client Session Manager null check error paths.

These tests verify that ConnectionError is raised when MCP responses
succeed but return None results, which would indicate a protocol violation.

TDD: GREEN phase - tests verify null check implementation works correctly.
"""

from __future__ import annotations

import gc
from typing import Any
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

pytestmark = [
    pytest.mark.unit,
    pytest.mark.mcp,
]


class MockMCPResponse:
    """Mock MCP response for testing."""

    def __init__(
        self,
        is_success: bool = True,
        result: dict[str, Any] | None = None,
        error: dict[str, Any] | None = None,
    ) -> None:
        self.is_success = is_success
        self.result = result
        self.error = error


@pytest.mark.unit
@pytest.mark.xdist_group(name="mcp_client_session_null_checks")
class TestMCPClientSessionNullChecks:
    """Test suite for MCP client session manager null check error paths."""

    def teardown_method(self) -> None:
        """Force GC to prevent mock accumulation in xdist workers."""
        gc.collect()

    @pytest.mark.asyncio
    async def test_initialize_stdio_raises_when_result_is_none(self) -> None:
        """GIVEN a successful MCP initialize response with None result.

        WHEN calling _connect_stdio
        THEN ConnectionError should be raised with descriptive message.
        """
        from mcp_server_langgraph.mcp.client.session_manager import MCPClientSession
        from mcp_server_langgraph.mcp.client.tool_registry import MCPServerConfig

        config = MCPServerConfig(
            name="test-server",
            command="echo",
            args=["test"],
        )

        session = MCPClientSession(config)

        # Mock successful response with None result
        mock_response = MockMCPResponse(is_success=True, result=None)

        # Patch methods on the class, not the instance
        with (
            patch.object(MCPClientSession, "_send_request_stdio", new_callable=AsyncMock),
            patch.object(MCPClientSession, "_read_response_stdio", new_callable=AsyncMock, return_value=mock_response),
        ):
            # Call _connect_stdio directly to bypass process spawning
            with pytest.raises(ConnectionError) as exc_info:
                await session._connect_stdio()

            assert "no result" in str(exc_info.value).lower()

    @pytest.mark.asyncio
    async def test_list_tools_stdio_raises_when_result_is_none(self) -> None:
        """GIVEN a successful tools/list response with None result.

        WHEN listing tools via STDIO transport
        THEN ConnectionError should be raised with descriptive message.
        """
        from mcp_server_langgraph.mcp.client.session_manager import (
            MCPClientSession,
            MCPTransportType,
        )
        from mcp_server_langgraph.mcp.client.tool_registry import MCPServerConfig

        config = MCPServerConfig(
            name="test-server",
            command="echo",
            args=["test"],
        )

        session = MCPClientSession(config)
        session._connected = True
        session.transport_type = MCPTransportType.STDIO

        # Mock successful response with None result
        mock_response = MockMCPResponse(is_success=True, result=None)

        with (
            patch.object(session, "_send_request_stdio", new_callable=AsyncMock),
            patch.object(session, "_read_response_stdio", new_callable=AsyncMock, return_value=mock_response),
        ):
            with pytest.raises(ConnectionError) as exc_info:
                await session._list_tools_stdio()

            assert "no result" in str(exc_info.value).lower()
            assert "tools/list" in str(exc_info.value).lower()

    @pytest.mark.asyncio
    async def test_call_tool_stdio_raises_when_result_is_none(self) -> None:
        """GIVEN a successful tools/call response with None result.

        WHEN calling a tool via STDIO transport
        THEN ConnectionError should be raised with descriptive message.
        """
        from mcp_server_langgraph.mcp.client.session_manager import (
            MCPClientSession,
            MCPTransportType,
        )
        from mcp_server_langgraph.mcp.client.tool_registry import MCPServerConfig

        config = MCPServerConfig(
            name="test-server",
            command="echo",
            args=["test"],
        )

        session = MCPClientSession(config)
        session._connected = True
        session.transport_type = MCPTransportType.STDIO

        # Mock successful response with None result
        mock_response = MockMCPResponse(is_success=True, result=None)

        with (
            patch.object(session, "_send_request_stdio", new_callable=AsyncMock),
            patch.object(session, "_read_response_stdio", new_callable=AsyncMock, return_value=mock_response),
        ):
            with pytest.raises(ConnectionError) as exc_info:
                await session._call_tool_stdio("test_tool", {"arg": "value"})

            assert "no result" in str(exc_info.value).lower()
            assert "tools/call" in str(exc_info.value).lower()


@pytest.mark.unit
@pytest.mark.xdist_group(name="mcp_client_session_null_checks_http")
class TestMCPClientSessionNullChecksHTTP:
    """Test suite for MCP client session manager null checks via HTTP transport."""

    def teardown_method(self) -> None:
        """Force GC to prevent mock accumulation in xdist workers."""
        gc.collect()

    @pytest.mark.asyncio
    async def test_initialize_http_raises_when_result_is_none(self) -> None:
        """GIVEN a successful MCP initialize response with None result.

        WHEN connecting via HTTP transport
        THEN ConnectionError should be raised with descriptive message.
        """
        from mcp_server_langgraph.mcp.client.session_manager import MCPClientSession
        from mcp_server_langgraph.mcp.client.tool_registry import MCPServerConfig

        config = MCPServerConfig(
            name="test-server",
            url="http://localhost:8080/mcp",
        )

        session = MCPClientSession(config)

        # Create mock HTTP response context manager
        mock_resp = MagicMock()
        mock_resp.status = 200
        mock_resp.headers = {}
        mock_resp.json = AsyncMock(return_value={"jsonrpc": "2.0", "id": 1, "result": None})

        # Create async context manager mock
        mock_context = MagicMock()
        mock_context.__aenter__ = AsyncMock(return_value=mock_resp)
        mock_context.__aexit__ = AsyncMock(return_value=None)

        # Mock the HTTP client - must patch aiohttp.ClientSession since _connect_http creates its own
        mock_http_client = MagicMock()
        mock_http_client.post = MagicMock(return_value=mock_context)
        mock_http_client.close = AsyncMock(return_value=None)

        with patch("aiohttp.ClientSession", return_value=mock_http_client):
            with pytest.raises(ConnectionError) as exc_info:
                await session._connect_http()

            assert "no result" in str(exc_info.value).lower()

    @pytest.mark.asyncio
    async def test_list_tools_http_raises_when_result_is_none(self) -> None:
        """GIVEN a successful tools/list HTTP response with None result.

        WHEN listing tools via HTTP transport
        THEN ConnectionError should be raised with descriptive message.
        """
        from mcp_server_langgraph.mcp.client.session_manager import MCPClientSession
        from mcp_server_langgraph.mcp.client.tool_registry import MCPServerConfig

        config = MCPServerConfig(
            name="test-server",
            url="http://localhost:8080/mcp",
        )

        session = MCPClientSession(config)
        session._connected = True

        # Create mock HTTP response context manager
        mock_resp = MagicMock()
        mock_resp.status = 200
        mock_resp.json = AsyncMock(return_value={"jsonrpc": "2.0", "id": 1, "result": None})

        mock_context = MagicMock()
        mock_context.__aenter__ = AsyncMock(return_value=mock_resp)
        mock_context.__aexit__ = AsyncMock(return_value=None)

        mock_http_client = MagicMock()
        mock_http_client.post = MagicMock(return_value=mock_context)

        session._http_client = mock_http_client

        with pytest.raises(ConnectionError) as exc_info:
            await session._list_tools_http()

        assert "no result" in str(exc_info.value).lower()

    @pytest.mark.asyncio
    async def test_call_tool_http_raises_when_result_is_none(self) -> None:
        """GIVEN a successful tools/call HTTP response with None result.

        WHEN calling a tool via HTTP transport
        THEN ConnectionError should be raised with descriptive message.
        """
        from mcp_server_langgraph.mcp.client.session_manager import MCPClientSession
        from mcp_server_langgraph.mcp.client.tool_registry import MCPServerConfig

        config = MCPServerConfig(
            name="test-server",
            url="http://localhost:8080/mcp",
        )

        session = MCPClientSession(config)
        session._connected = True

        # Create mock HTTP response context manager
        mock_resp = MagicMock()
        mock_resp.status = 200
        mock_resp.json = AsyncMock(return_value={"jsonrpc": "2.0", "id": 1, "result": None})

        mock_context = MagicMock()
        mock_context.__aenter__ = AsyncMock(return_value=mock_resp)
        mock_context.__aexit__ = AsyncMock(return_value=None)

        mock_http_client = MagicMock()
        mock_http_client.post = MagicMock(return_value=mock_context)

        session._http_client = mock_http_client

        with pytest.raises(ConnectionError) as exc_info:
            await session._call_tool_http("test_tool", {"arg": "value"})

        assert "no result" in str(exc_info.value).lower()
