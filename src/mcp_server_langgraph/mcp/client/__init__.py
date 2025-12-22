"""
MCP Client Module

Provides client capabilities to consume tools from external MCP servers.
This enables our agents to use tools from Playwright, GitHub, Slack, and other
MCP-compatible servers.

Architecture:
    MCPToolRegistry   - Track tools from multiple external MCP servers
    MCPToolProxy      - Wrap MCP tools as LangChain BaseTool
    MCPExecutor       - Route tool calls to external MCP servers
    MCPClientSession  - Manage connection lifecycle to individual servers

Protocol:
    MCPRequest        - JSON-RPC 2.0 request message
    MCPResponse       - JSON-RPC 2.0 response message
    MCPNotification   - JSON-RPC 2.0 notification (no response expected)
    ServerInfo        - Parsed server capabilities from initialize response

See ADR-0082 for detailed design rationale.
"""

from mcp_server_langgraph.mcp.client.executor import (
    MCPExecutor,
    MCPToolCall,
    MCPToolResult,
)
from mcp_server_langgraph.mcp.client.protocol import (
    MCP_PROTOCOL_VERSION,
    MCPNotification,
    MCPRequest,
    MCPResponse,
    ServerInfo,
)
from mcp_server_langgraph.mcp.client.session_manager import (
    MCPClientSession,
    MCPTransportType,
)
from mcp_server_langgraph.mcp.client.tool_proxy import (
    MCPToolProxy,
    create_proxies_from_registry,
)
from mcp_server_langgraph.mcp.client.tool_registry import (
    MCPServerConfig,
    MCPToolDefinition,
    MCPToolRegistry,
)

__all__ = [
    # Protocol
    "MCP_PROTOCOL_VERSION",
    "MCPRequest",
    "MCPResponse",
    "MCPNotification",
    "ServerInfo",
    # Registry
    "MCPServerConfig",
    "MCPToolDefinition",
    "MCPToolRegistry",
    # Proxy
    "MCPToolProxy",
    "create_proxies_from_registry",
    # Executor
    "MCPExecutor",
    "MCPToolCall",
    "MCPToolResult",
    # Session
    "MCPClientSession",
    "MCPTransportType",
]
