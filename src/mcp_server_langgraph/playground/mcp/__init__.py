"""
MCP protocol integration for the Interactive Playground.

Provides client and integration components for MCP StreamableHTTP:
- MCPClient: Synchronous MCP client
- MCPStreamingClient: Streaming MCP client
- PlaygroundMCPBridge: Bridge between playground and MCP

Example:
    from mcp_server_langgraph.playground.mcp import (
        MCPClient,
        PlaygroundMCPBridge,
    )

    client = MCPClient(base_url="http://localhost:8000")
    bridge = PlaygroundMCPBridge(mcp_client=client)
"""

from .client import (
    MCPClient,
    MCPConnectionError,
    MCPError,
    MCPPermissionError,
    MCPStreamingClient,
    MCPValidationError,
)
from .integration import ChatChunk, ChatError, ChatResponse, PlaygroundMCPBridge

__all__ = [
    # Client
    "MCPClient",
    "MCPStreamingClient",
    # Exceptions
    "MCPError",
    "MCPConnectionError",
    "MCPPermissionError",
    "MCPValidationError",
    "ChatError",
    # Integration
    "PlaygroundMCPBridge",
    "ChatResponse",
    "ChatChunk",
]
