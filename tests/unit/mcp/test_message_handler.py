"""
Tests for MCP Message Handler module.

Tests the extracted MCPMessageHandler and AuthenticatedMCPHandler classes
to ensure proper module structure and backward compatibility.
"""

from __future__ import annotations

import gc

import pytest


pytestmark = [pytest.mark.unit, pytest.mark.mcp]


@pytest.mark.xdist_group(name="mcp_message_handler")
class TestMCPMessageHandlerModuleImports:
    """Tests that the new module can be imported correctly."""

    def teardown_method(self) -> None:
        """Force GC to prevent mock accumulation in xdist workers."""
        gc.collect()

    def test_can_import_mcp_message_handler(self) -> None:
        """Test that MCPMessageHandler can be imported from new location."""
        from mcp_server_langgraph.mcp.message_handler import MCPMessageHandler

        assert MCPMessageHandler is not None

    def test_can_import_authenticated_mcp_handler(self) -> None:
        """Test that AuthenticatedMCPHandler can be imported from new location."""
        from mcp_server_langgraph.mcp.message_handler import AuthenticatedMCPHandler

        assert AuthenticatedMCPHandler is not None

    def test_backward_compatible_import_from_mcp_websocket(self) -> None:
        """Test backward compatibility import from api.v1.mcp_websocket."""
        from mcp_server_langgraph.api.v1.mcp_websocket import (
            MCPMessageHandler,
            AuthenticatedMCPHandler,
        )

        # Should still be importable from old location
        assert MCPMessageHandler is not None
        assert AuthenticatedMCPHandler is not None

    def test_both_imports_are_same_class(self) -> None:
        """Test that imports from both locations reference the same class."""
        from mcp_server_langgraph.mcp.message_handler import (
            MCPMessageHandler as NewHandler,
            AuthenticatedMCPHandler as NewAuthHandler,
        )
        from mcp_server_langgraph.api.v1.mcp_websocket import (
            MCPMessageHandler as OldHandler,
            AuthenticatedMCPHandler as OldAuthHandler,
        )

        assert NewHandler is OldHandler
        assert NewAuthHandler is OldAuthHandler


@pytest.mark.xdist_group(name="mcp_message_handler")
class TestMCPMessageHandlerBasicFunctionality:
    """Tests for basic MCPMessageHandler functionality."""

    def teardown_method(self) -> None:
        """Force GC to prevent mock accumulation in xdist workers."""
        gc.collect()

    def test_handler_instantiation(self) -> None:
        """Test that MCPMessageHandler can be instantiated."""
        from mcp_server_langgraph.mcp.message_handler import MCPMessageHandler

        handler = MCPMessageHandler()
        assert handler is not None
        assert handler.protocol_version == "2025-11-25"

    def test_handler_has_capabilities(self) -> None:
        """Test that handler exposes MCP capabilities."""
        from mcp_server_langgraph.mcp.message_handler import MCPMessageHandler

        handler = MCPMessageHandler()
        assert "tools" in handler.capabilities
        assert "resources" in handler.capabilities
        assert "prompts" in handler.capabilities
        assert "streaming" in handler.capabilities

    def test_handler_has_server_info(self) -> None:
        """Test that handler has server information."""
        from mcp_server_langgraph.mcp.message_handler import MCPMessageHandler

        handler = MCPMessageHandler()
        assert "name" in handler.server_info
        assert "version" in handler.server_info

    @pytest.mark.asyncio
    async def test_handle_initialize(self) -> None:
        """Test handling initialize request."""
        from mcp_server_langgraph.mcp.message_handler import MCPMessageHandler

        handler = MCPMessageHandler()
        response = await handler.handle({"jsonrpc": "2.0", "id": 1, "method": "initialize", "params": {}})

        assert response["jsonrpc"] == "2.0"
        assert response["id"] == 1
        assert "result" in response
        assert "protocolVersion" in response["result"]
        assert "capabilities" in response["result"]

    @pytest.mark.asyncio
    async def test_handle_tools_list(self) -> None:
        """Test handling tools/list request."""
        from mcp_server_langgraph.mcp.message_handler import MCPMessageHandler

        handler = MCPMessageHandler()
        response = await handler.handle({"jsonrpc": "2.0", "id": 2, "method": "tools/list", "params": {}})

        assert response["id"] == 2
        assert "result" in response
        assert "tools" in response["result"]

    @pytest.mark.asyncio
    async def test_handle_unknown_method(self) -> None:
        """Test handling unknown method returns error."""
        from mcp_server_langgraph.mcp.message_handler import MCPMessageHandler

        handler = MCPMessageHandler()
        response = await handler.handle({"jsonrpc": "2.0", "id": 3, "method": "unknown/method", "params": {}})

        assert response["id"] == 3
        assert "error" in response
        assert response["error"]["code"] == -32601  # METHOD_NOT_FOUND


@pytest.mark.xdist_group(name="mcp_message_handler")
class TestAuthenticatedMCPHandler:
    """Tests for AuthenticatedMCPHandler functionality."""

    def teardown_method(self) -> None:
        """Force GC to prevent mock accumulation in xdist workers."""
        gc.collect()

    def test_authenticated_handler_instantiation(self) -> None:
        """Test AuthenticatedMCPHandler can be instantiated with user context."""
        from mcp_server_langgraph.mcp.message_handler import AuthenticatedMCPHandler

        handler = AuthenticatedMCPHandler(
            user_id="test-user",
            roles=["admin", "user"],
        )

        assert handler.user_id == "test-user"
        assert "admin" in handler.roles
        assert "user" in handler.roles

    def test_authenticated_handler_extends_base(self) -> None:
        """Test AuthenticatedMCPHandler extends MCPMessageHandler."""
        from mcp_server_langgraph.mcp.message_handler import (
            MCPMessageHandler,
            AuthenticatedMCPHandler,
        )

        handler = AuthenticatedMCPHandler(user_id="test")
        assert isinstance(handler, MCPMessageHandler)

    def test_authenticated_handler_has_session_id(self) -> None:
        """Test AuthenticatedMCPHandler can track session ID."""
        from mcp_server_langgraph.mcp.message_handler import AuthenticatedMCPHandler

        handler = AuthenticatedMCPHandler(
            user_id="test-user",
            session_id="session-123",
        )

        assert handler.session_id == "session-123"

    @pytest.mark.asyncio
    async def test_authenticated_handler_handles_initialize(self) -> None:
        """Test AuthenticatedMCPHandler handles initialize like base."""
        from mcp_server_langgraph.mcp.message_handler import AuthenticatedMCPHandler

        handler = AuthenticatedMCPHandler(user_id="test-user")
        response = await handler.handle({"jsonrpc": "2.0", "id": 1, "method": "initialize", "params": {}})

        assert "result" in response
        assert "protocolVersion" in response["result"]


@pytest.mark.xdist_group(name="mcp_message_handler")
class TestMCPMessageHandlerExports:
    """Tests for module __all__ exports."""

    def teardown_method(self) -> None:
        """Force GC to prevent mock accumulation in xdist workers."""
        gc.collect()

    def test_module_exports_all(self) -> None:
        """Test that __all__ exports the expected classes."""
        from mcp_server_langgraph.mcp import message_handler

        assert "MCPMessageHandler" in message_handler.__all__
        assert "AuthenticatedMCPHandler" in message_handler.__all__

    def test_module_exports_error_codes(self) -> None:
        """Test that module exports JSON-RPC error codes."""
        from mcp_server_langgraph.mcp.message_handler import (
            PARSE_ERROR,
            INVALID_REQUEST,
            METHOD_NOT_FOUND,
            INVALID_PARAMS,
            INTERNAL_ERROR,
        )

        assert PARSE_ERROR == -32700
        assert INVALID_REQUEST == -32600
        assert METHOD_NOT_FOUND == -32601
        assert INVALID_PARAMS == -32602
        assert INTERNAL_ERROR == -32603
