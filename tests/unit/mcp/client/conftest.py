"""
Pytest configuration for MCP client unit tests.

Mocks the external MCP SDK modules to allow testing without the full SDK.

This is needed because mcp_server_langgraph/mcp/__init__.py imports server_stdio
which in turn imports from the external MCP SDK (mcp.server.stdio).
"""

import sys
from types import ModuleType
from unittest.mock import MagicMock


def _create_mcp_module() -> ModuleType:
    """Create mock mcp root module."""
    mock = ModuleType("mcp")
    mock.Server = MagicMock()  # type: ignore[attr-defined]
    return mock


def _create_mcp_server_module() -> ModuleType:
    """Create mock mcp.server module."""
    mock = ModuleType("mcp.server")
    mock.Server = MagicMock()  # type: ignore[attr-defined]
    return mock


def _create_mcp_server_stdio_module() -> ModuleType:
    """Create mock mcp.server.stdio module with stdio_server."""
    mock = ModuleType("mcp.server.stdio")
    # stdio_server is an async context manager function
    mock.stdio_server = MagicMock()  # type: ignore[attr-defined]
    mock.StdioServerTransport = MagicMock()  # type: ignore[attr-defined]
    return mock


def _create_mcp_server_sse_module() -> ModuleType:
    """Create mock mcp.server.sse module."""
    mock = ModuleType("mcp.server.sse")
    mock.SseServerTransport = MagicMock()  # type: ignore[attr-defined]
    return mock


def _create_mcp_server_streamable_http_module() -> ModuleType:
    """Create mock mcp.server.streamable_http module."""
    mock = ModuleType("mcp.server.streamable_http")
    mock.StreamableHTTPServerTransport = MagicMock()  # type: ignore[attr-defined]
    return mock


def _create_mcp_types_module() -> ModuleType:
    """Create mock mcp.types module with type definitions."""
    mock = ModuleType("mcp.types")
    # Add common type classes as MagicMocks
    mock.Tool = MagicMock()  # type: ignore[attr-defined]
    mock.Resource = MagicMock()  # type: ignore[attr-defined]
    mock.Prompt = MagicMock()  # type: ignore[attr-defined]
    mock.TextContent = MagicMock()  # type: ignore[attr-defined]
    mock.ImageContent = MagicMock()  # type: ignore[attr-defined]
    mock.CallToolResult = MagicMock()  # type: ignore[attr-defined]
    mock.GetPromptResult = MagicMock()  # type: ignore[attr-defined]
    mock.ReadResourceResult = MagicMock()  # type: ignore[attr-defined]
    return mock


def _create_mcp_client_module() -> ModuleType:
    """Create mock mcp.client module."""
    mock = ModuleType("mcp.client")
    mock.ClientSession = MagicMock()  # type: ignore[attr-defined]
    return mock


def _create_mcp_client_session_module() -> ModuleType:
    """Create mock mcp.client.session module."""
    mock = ModuleType("mcp.client.session")
    mock.ClientSession = MagicMock()  # type: ignore[attr-defined]
    return mock


# Mock the external MCP SDK modules before any imports
# Only mock if not already present (e.g., if full SDK is installed)
# The order matters - parent modules must be mocked before child modules

if "mcp" not in sys.modules:
    sys.modules["mcp"] = _create_mcp_module()

if "mcp.server" not in sys.modules:
    sys.modules["mcp.server"] = _create_mcp_server_module()

if "mcp.server.stdio" not in sys.modules:
    sys.modules["mcp.server.stdio"] = _create_mcp_server_stdio_module()

if "mcp.server.sse" not in sys.modules:
    sys.modules["mcp.server.sse"] = _create_mcp_server_sse_module()

if "mcp.server.streamable_http" not in sys.modules:
    sys.modules["mcp.server.streamable_http"] = _create_mcp_server_streamable_http_module()

if "mcp.types" not in sys.modules:
    sys.modules["mcp.types"] = _create_mcp_types_module()

if "mcp.client" not in sys.modules:
    sys.modules["mcp.client"] = _create_mcp_client_module()

if "mcp.client.session" not in sys.modules:
    sys.modules["mcp.client.session"] = _create_mcp_client_session_module()
