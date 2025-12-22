"""
MCP Tool Registry for managing tools from external MCP servers.

Provides a registry to track, import, and manage tools from multiple
external MCP servers following the patterns from Claude Agent SDK,
Google ADK, and OpenAI Agents SDK.
"""

from dataclasses import dataclass, field
from typing import Any, Protocol

from mcp_server_langgraph.observability.telemetry import logger


@dataclass
class MCPToolDefinition:
    """Definition of a tool from an external MCP server."""

    server_name: str
    """Name of the MCP server providing this tool."""

    name: str
    """Tool name as provided by the server."""

    description: str
    """Human-readable description of what the tool does."""

    input_schema: dict[str, Any]
    """JSON Schema for the tool's input parameters."""

    qualified_name: str = field(init=False)
    """Fully qualified name in format 'server_name:tool_name'."""

    def __post_init__(self):
        """Set qualified_name after initialization."""
        self.qualified_name = f"{self.server_name}:{self.name}"


@dataclass
class MCPServerConfig:
    """Configuration for connecting to an external MCP server."""

    name: str
    """Unique identifier for this server."""

    command: str | None = None
    """Command to spawn server process (for stdio transport)."""

    args: list[str] | None = None
    """Arguments for the command."""

    url: str | None = None
    """URL for HTTP/SSE/WebSocket transport."""

    env: dict[str, str] | None = None
    """Environment variables to set for the server process."""

    auth: dict[str, Any] | None = None
    """Authentication configuration (tokens, credentials)."""

    timeout: float = 30.0
    """Default timeout for tool calls in seconds."""

    tool_allowlist: list[str] | None = None
    """If set, only these tools are exposed (whitelist)."""

    tool_blocklist: list[str] | None = None
    """If set, these tools are hidden (blacklist)."""


class MCPClientSessionProtocol(Protocol):
    """Protocol for MCP client sessions."""

    async def connect(self) -> None:
        """Establish connection to MCP server."""
        ...

    async def disconnect(self) -> None:
        """Close connection to MCP server."""
        ...

    async def list_tools(self) -> list[dict[str, Any]]:
        """Get available tools from the server."""
        ...

    async def call_tool(self, name: str, arguments: dict[str, Any]) -> Any:
        """Execute a tool on this server."""
        ...

    @property
    def is_connected(self) -> bool:
        """Check if connected."""
        ...


class MCPToolRegistry:
    """Registry for tools from external MCP servers.

    This class manages the lifecycle of connections to external MCP servers
    and maintains a catalog of their available tools.

    Example:
        registry = MCPToolRegistry()

        config = MCPServerConfig(
            name="playwright",
            command="npx",
            args=["@playwright/mcp@latest"],
            tool_allowlist=["screenshot", "click"],
        )

        tools = await registry.register_server(config)
        # tools now available for agents to use

        await registry.unregister_server("playwright")
    """

    def __init__(self):
        """Initialize an empty registry."""
        self._servers: dict[str, MCPClientSessionProtocol] = {}
        self._server_configs: dict[str, MCPServerConfig] = {}
        self._tools: dict[str, MCPToolDefinition] = {}
        self._server_tools: dict[str, list[str]] = {}

    def _create_session(self, config: MCPServerConfig) -> MCPClientSessionProtocol:
        """Create a client session for the given config.

        This method can be overridden in tests to inject mock sessions.
        """
        # Import here to avoid circular dependency and allow late binding
        from mcp_server_langgraph.mcp.client.session_manager import MCPClientSession

        return MCPClientSession(config)

    async def register_server(
        self,
        config: MCPServerConfig,
    ) -> list[MCPToolDefinition]:
        """Register an MCP server and import its tools.

        Args:
            config: Server configuration including connection details

        Returns:
            List of tool definitions imported from the server

        Raises:
            ValueError: If server with same name already registered
            ConnectionError: If unable to connect to server
        """
        if config.name in self._servers:
            raise ValueError(f"Server '{config.name}' already registered")

        logger.info(
            "Registering MCP server",
            extra={"server_name": config.name, "command": config.command, "url": config.url}
        )

        # Create and connect session
        session = self._create_session(config)
        await session.connect()

        # Store session and config
        self._servers[config.name] = session
        self._server_configs[config.name] = config
        self._server_tools[config.name] = []

        # Import tools
        raw_tools = await session.list_tools()
        tools = self._import_tools(config.name, raw_tools, config)

        logger.info(
            "MCP server registered",
            extra={"server_name": config.name, "tool_count": len(tools)}
        )

        return tools

    def _import_tools(
        self,
        server_name: str,
        raw_tools: list[dict[str, Any]],
        config: MCPServerConfig,
    ) -> list[MCPToolDefinition]:
        """Import tools from raw server response, applying filters."""
        imported_tools: list[MCPToolDefinition] = []

        for raw_tool in raw_tools:
            tool_name = raw_tool.get("name", "")

            # Apply allowlist filter
            if config.tool_allowlist is not None:
                if tool_name not in config.tool_allowlist:
                    continue

            # Apply blocklist filter
            if config.tool_blocklist is not None:
                if tool_name in config.tool_blocklist:
                    continue

            # Create tool definition
            tool = MCPToolDefinition(
                server_name=server_name,
                name=tool_name,
                description=raw_tool.get("description", ""),
                input_schema=raw_tool.get("inputSchema", {}),
            )

            # Register tool
            self._tools[tool.qualified_name] = tool
            self._server_tools[server_name].append(tool.qualified_name)
            imported_tools.append(tool)

        return imported_tools

    async def unregister_server(self, name: str) -> None:
        """Disconnect from an MCP server and remove its tools.

        Args:
            name: Name of the server to unregister

        Raises:
            KeyError: If server not registered
        """
        if name not in self._servers:
            raise KeyError(f"Server '{name}' not registered")

        logger.info("Unregistering MCP server", extra={"server_name": name})

        # Disconnect session
        session = self._servers[name]
        await session.disconnect()

        # Remove tools
        if name in self._server_tools:
            for qualified_name in self._server_tools[name]:
                self._tools.pop(qualified_name, None)
            del self._server_tools[name]

        # Remove server
        del self._servers[name]
        self._server_configs.pop(name, None)

        logger.info("MCP server unregistered", extra={"server_name": name})

    def get_tools(
        self,
        server_name: str | None = None,
    ) -> list[MCPToolDefinition]:
        """Get all tools or tools from a specific server.

        Args:
            server_name: If provided, only return tools from this server

        Returns:
            List of tool definitions
        """
        if server_name is not None:
            qualified_names = self._server_tools.get(server_name, [])
            return [self._tools[qn] for qn in qualified_names if qn in self._tools]

        return list(self._tools.values())

    async def refresh_tools(self, server_name: str) -> list[MCPToolDefinition]:
        """Refresh tool list from a server.

        Re-queries the server for its current tool list and updates
        the registry accordingly.

        Args:
            server_name: Name of the server to refresh

        Returns:
            Updated list of tool definitions

        Raises:
            KeyError: If server not registered
        """
        if server_name not in self._servers:
            raise KeyError(f"Server '{server_name}' not registered")

        session = self._servers[server_name]
        config = self._server_configs[server_name]

        # Remove old tools
        if server_name in self._server_tools:
            for qualified_name in self._server_tools[server_name]:
                self._tools.pop(qualified_name, None)
            self._server_tools[server_name] = []

        # Re-import tools
        raw_tools = await session.list_tools()
        tools = self._import_tools(server_name, raw_tools, config)

        logger.info(
            "MCP server tools refreshed",
            extra={"server_name": server_name, "tool_count": len(tools)}
        )

        return tools

    def get_tool(self, qualified_name: str) -> MCPToolDefinition | None:
        """Get a specific tool by qualified name.

        Args:
            qualified_name: Fully qualified name in format 'server:tool'

        Returns:
            Tool definition if found, None otherwise
        """
        return self._tools.get(qualified_name)

    def get_server_names(self) -> list[str]:
        """Get names of all registered servers.

        Returns:
            List of server names
        """
        return list(self._server_tools.keys())

    def get_session(self, server_name: str) -> MCPClientSessionProtocol | None:
        """Get the session for a specific server.

        Args:
            server_name: Name of the server

        Returns:
            Session if registered, None otherwise
        """
        return self._servers.get(server_name)
