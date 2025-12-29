"""MCP protocol server implementations."""

from __future__ import annotations

from types import ModuleType
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from . import server_stdio, server_streamable, streaming

# Entry points for different transports
__all__ = [
    "server_stdio",  # stdio transport
    "server_streamable",  # StreamableHTTP transport
    "streaming",  # Streaming utilities
]


def __getattr__(name: str) -> ModuleType:
    """Lazy import modules to avoid loading external dependencies at import time."""
    if name == "server_stdio":
        from . import server_stdio

        return server_stdio
    elif name == "server_streamable":
        from . import server_streamable

        return server_streamable
    elif name == "streaming":
        from . import streaming

        return streaming
    raise AttributeError(f"module 'mcp_server_langgraph.mcp' has no attribute '{name}'")
