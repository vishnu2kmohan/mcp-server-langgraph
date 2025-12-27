"""
Unified MCP Capability Registry for managing all MCP capabilities.

Combines tool, resource, and prompt registries into a single unified
interface for managing capabilities from external MCP servers.

Reference: MCP Protocol Specification 2025-11-25
"""

from typing import Any, Protocol

from mcp_server_langgraph.mcp.client.prompt_registry import (
    MCPPromptDefinition,
    MCPPromptRegistry,
)
from mcp_server_langgraph.mcp.client.resource_registry import (
    MCPResourceDefinition,
    MCPResourceRegistry,
)
from mcp_server_langgraph.mcp.client.tool_registry import (
    MCPServerConfig,
    MCPToolDefinition,
    MCPToolRegistry,
)
from mcp_server_langgraph.observability.telemetry import logger


class MCPFullSessionProtocol(Protocol):
    """Protocol for sessions with full capability support."""

    async def connect(self) -> None:
        """Establish connection to MCP server."""
        ...

    async def disconnect(self) -> None:
        """Close connection to MCP server."""
        ...

    async def list_tools(self) -> list[dict[str, Any]]:
        """Get available tools from the server."""
        ...

    async def list_resources(self) -> list[dict[str, Any]]:
        """Get available resources from the server."""
        ...

    async def list_prompts(self) -> list[dict[str, Any]]:
        """Get available prompts from the server."""
        ...

    @property
    def is_connected(self) -> bool:
        """Check if connected."""
        ...


class MCPUnifiedRegistry:
    """Unified registry for all MCP capabilities (tools, resources, prompts).

    This class provides a single interface for managing connections to
    external MCP servers and aggregating their capabilities with proper
    namespacing to avoid collisions.

    Example:
        registry = MCPUnifiedRegistry()

        config = MCPServerConfig(
            name="code-assistant",
            url="http://localhost:8080/mcp",
        )

        await registry.register_server(config)

        # Access all capabilities
        tools = registry.get_tools()
        resources = registry.get_resources()
        prompts = registry.get_prompts()

        # Get summary for a server
        summary = registry.get_server_capabilities("code-assistant")
        # {"tool_count": 5, "resource_count": 3, "prompt_count": 2}

        await registry.unregister_server("code-assistant")
    """

    def __init__(self) -> None:
        """Initialize unified registry with sub-registries."""
        self._tool_registry = MCPToolRegistry()
        self._resource_registry = MCPResourceRegistry()
        self._prompt_registry = MCPPromptRegistry()
        self._sessions: dict[str, MCPFullSessionProtocol] = {}
        self._server_configs: dict[str, MCPServerConfig] = {}

    def _create_session(self, config: MCPServerConfig) -> MCPFullSessionProtocol:
        """Create a client session for the given config.

        This method can be overridden in tests to inject mock sessions.
        """
        from mcp_server_langgraph.mcp.client.session_manager import MCPClientSession

        return MCPClientSession(config)

    async def register_server(
        self,
        config: MCPServerConfig,
    ) -> dict[str, int]:
        """Register an MCP server and import all its capabilities.

        Args:
            config: Server configuration including connection details

        Returns:
            Dict with counts of imported capabilities:
                - tool_count: Number of tools imported
                - resource_count: Number of resources imported
                - prompt_count: Number of prompts imported

        Raises:
            ValueError: If server with same name already registered
            ConnectionError: If unable to connect to server
        """
        if config.name in self._sessions:
            raise ValueError(f"Server '{config.name}' already registered")

        logger.info(
            "Registering MCP server (unified)",
            extra={"server_name": config.name},
        )

        # Create and connect session
        session = self._create_session(config)
        await session.connect()

        # Store session and config
        self._sessions[config.name] = session
        self._server_configs[config.name] = config

        # Import all capabilities
        tool_count = 0
        resource_count = 0
        prompt_count = 0

        # Import tools - also register with tool_registry internals
        try:
            raw_tools = await session.list_tools()
            # Initialize tool_registry internal state
            self._tool_registry._servers[config.name] = session
            self._tool_registry._server_configs[config.name] = config
            self._tool_registry._server_tools[config.name] = []
            # Import tools
            tools = self._tool_registry._import_tools(config.name, raw_tools, config)
            tool_count = len(tools)
        except Exception as e:
            logger.warning(
                "Failed to import tools",
                extra={"server_name": config.name, "error": str(e)},
            )

        # Import resources
        try:
            resources = await self._resource_registry.import_resources(config.name, session)
            resource_count = len(resources)
        except Exception as e:
            logger.warning(
                "Failed to import resources",
                extra={"server_name": config.name, "error": str(e)},
            )

        # Import prompts
        try:
            prompts = await self._prompt_registry.import_prompts(config.name, session)
            prompt_count = len(prompts)
        except Exception as e:
            logger.warning(
                "Failed to import prompts",
                extra={"server_name": config.name, "error": str(e)},
            )

        logger.info(
            "MCP server registered (unified)",
            extra={
                "server_name": config.name,
                "tool_count": tool_count,
                "resource_count": resource_count,
                "prompt_count": prompt_count,
            },
        )

        return {
            "tool_count": tool_count,
            "resource_count": resource_count,
            "prompt_count": prompt_count,
        }

    async def unregister_server(self, name: str) -> None:
        """Disconnect from an MCP server and remove all its capabilities.

        Args:
            name: Name of the server to unregister

        Raises:
            KeyError: If server not registered
        """
        if name not in self._sessions:
            raise KeyError(f"Server '{name}' not registered")

        logger.info("Unregistering MCP server (unified)", extra={"server_name": name})

        # Disconnect session
        session = self._sessions[name]
        try:
            await session.disconnect()
        except Exception as e:
            logger.warning(
                "Error disconnecting from server",
                extra={"server_name": name, "error": str(e)},
            )

        # Remove all capabilities (handle cases where some may not exist)
        try:
            await self._tool_registry.unregister_server(name)
        except KeyError:
            pass  # Tools may not have been imported

        self._resource_registry.unregister_server(name)
        self._prompt_registry.unregister_server(name)

        # Remove session and config
        del self._sessions[name]
        self._server_configs.pop(name, None)

        logger.info("MCP server unregistered (unified)", extra={"server_name": name})

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
        return self._tool_registry.get_tools(server_name)

    def get_resources(
        self,
        server_name: str | None = None,
    ) -> list[MCPResourceDefinition]:
        """Get all resources or resources from a specific server.

        Args:
            server_name: If provided, only return resources from this server

        Returns:
            List of resource definitions
        """
        return self._resource_registry.get_resources(server_name)

    def get_prompts(
        self,
        server_name: str | None = None,
    ) -> list[MCPPromptDefinition]:
        """Get all prompts or prompts from a specific server.

        Args:
            server_name: If provided, only return prompts from this server

        Returns:
            List of prompt definitions
        """
        return self._prompt_registry.get_prompts(server_name)

    def get_tool(self, qualified_name: str) -> MCPToolDefinition | None:
        """Get a specific tool by qualified name."""
        return self._tool_registry.get_tool(qualified_name)

    def get_resource(self, qualified_name: str) -> MCPResourceDefinition | None:
        """Get a specific resource by qualified name."""
        return self._resource_registry.get_resource(qualified_name)

    def get_prompt(self, qualified_name: str) -> MCPPromptDefinition | None:
        """Get a specific prompt by qualified name."""
        return self._prompt_registry.get_prompt(qualified_name)

    def get_server_names(self) -> list[str]:
        """Get names of all registered servers."""
        return list(self._sessions.keys())

    def get_server_capabilities(self, server_name: str) -> dict[str, int]:
        """Get capability summary for a server.

        Args:
            server_name: Name of the server

        Returns:
            Dict with counts:
                - tool_count: Number of tools
                - resource_count: Number of resources
                - prompt_count: Number of prompts
        """
        tool_count = len(self._tool_registry._server_tools.get(server_name, []))
        resource_count = len(self._resource_registry._server_resources.get(server_name, []))
        prompt_count = len(self._prompt_registry._server_prompts.get(server_name, []))

        return {
            "tool_count": tool_count,
            "resource_count": resource_count,
            "prompt_count": prompt_count,
        }

    def get_session(self, server_name: str) -> MCPFullSessionProtocol | None:
        """Get the session for a specific server."""
        return self._sessions.get(server_name)

    async def refresh_all(self, server_name: str) -> dict[str, int]:
        """Refresh all capabilities from a server.

        Args:
            server_name: Name of the server to refresh

        Returns:
            Dict with updated capability counts

        Raises:
            KeyError: If server not registered
        """
        if server_name not in self._sessions:
            raise KeyError(f"Server '{server_name}' not registered")

        session = self._sessions[server_name]
        self._server_configs[server_name]

        # Refresh tools
        await self._tool_registry.refresh_tools(server_name)

        # Re-import resources (clear and re-import)
        self._resource_registry.unregister_server(server_name)
        await self._resource_registry.import_resources(server_name, session)

        # Re-import prompts (clear and re-import)
        self._prompt_registry.unregister_server(server_name)
        await self._prompt_registry.import_prompts(server_name, session)

        return self.get_server_capabilities(server_name)


# Singleton instance for application-wide registry
_unified_registry: MCPUnifiedRegistry | None = None


def get_unified_registry() -> MCPUnifiedRegistry:
    """Get the application-wide unified registry instance."""
    global _unified_registry
    if _unified_registry is None:
        _unified_registry = MCPUnifiedRegistry()
    return _unified_registry


def reset_unified_registry() -> None:
    """Reset the unified registry (for testing)."""
    global _unified_registry
    _unified_registry = None
