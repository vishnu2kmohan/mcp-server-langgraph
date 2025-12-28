"""
Pytest configuration for MCP client unit tests.

Mocks the external MCP SDK modules to allow testing without the full SDK.

This is needed because mcp_server_langgraph/mcp/__init__.py imports server_stdio
which in turn imports from the external MCP SDK (mcp.server.stdio).

SDK Mock Pattern
================

Problem:
    The MCP SDK (Model Context Protocol) is an optional dependency. In CI
    environments or minimal installations, it may not be installed. Tests that
    import our mcp_server_langgraph.mcp modules would fail with ImportError.

Solution:
    This conftest.py injects mock modules into sys.modules ONLY when the real
    SDK is not available. This allows tests to run without the full SDK.

CRITICAL: SDK Availability Check
    We MUST check if the real SDK is available BEFORE injecting mocks.
    If the real SDK IS installed, we skip mocking entirely to avoid:

    1. Mock Pollution: MagicMock objects replacing real types like TextContent
    2. Test Failures: Tests expecting real string values get MagicMock instead
    3. False Positives: Tests pass with mocks but would fail with real SDK

    Example of the bug this prevents:
        # Without SDK check, TextContent becomes MagicMock
        result = handler.get_skill("nonexistent")
        assert "not found" in result[0].text.lower()  # FAILS!
        # result[0].text is MagicMock, not a string

When Mocks Apply:
    - CI environments without mcp package installed
    - Minimal development environments
    - Isolated unit tests that don't need real SDK behavior

When Mocks Do NOT Apply:
    - Normal development with mcp package installed (via pyproject.toml)
    - Integration tests requiring real SDK behavior
    - Any environment where `from mcp.types import TextContent` succeeds

See Also:
    - ADR-0073: MCP WebSocket Migration (deprecation shim pattern)
    - scripts/validators/check_mcp_namespace_collision.py (prevents __init__.py)
"""

import sys
from types import ModuleType
from unittest.mock import MagicMock

# Check if the real MCP SDK is available BEFORE defining mocks
_MCP_SDK_AVAILABLE = False
try:
    from mcp.types import TextContent  # noqa: F401

    _MCP_SDK_AVAILABLE = True
except ImportError:
    _MCP_SDK_AVAILABLE = False


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


# Mock the external MCP SDK modules ONLY if the real SDK is not installed.
# If the real SDK is available, skip mocking to avoid polluting tests that
# depend on real types (e.g., TextContent string values instead of MagicMocks).
#
# The order matters - parent modules must be mocked before child modules

if not _MCP_SDK_AVAILABLE:
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
