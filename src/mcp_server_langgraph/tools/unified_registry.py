"""UnifiedToolRegistry combining MCP and hierarchical tool registries.

Provides a unified interface for tool lookup that checks both:
- HierarchicalToolRegistry for scope-aware tool resolution
- MCPToolRegistry for tools from external MCP servers

The lookup priority is:
1. Hierarchical registry (scope-aware, higher priority)
2. MCP registry (external tools, fallback)

ADR Reference: adr/adr-0092-hierarchical-capability-architecture.md
"""

from __future__ import annotations


from mcp_server_langgraph.capabilities.provider import ToolSpec
from mcp_server_langgraph.core.scopes import CapabilityScope
from mcp_server_langgraph.mcp.client.tool_registry import (
    MCPToolDefinition,
    MCPToolRegistry,
)
from mcp_server_langgraph.tools.hierarchical import HierarchicalToolRegistry


class UnifiedToolRegistry:
    """Unified tool registry combining MCP and hierarchical tools.

    Provides a single interface for looking up tools from both
    the scope-aware hierarchical registry and external MCP servers.

    Attributes:
        hierarchical_registry: Registry for scope-aware tools
        mcp_registry: Registry for MCP server tools
    """

    def __init__(
        self,
        hierarchical_registry: HierarchicalToolRegistry | None = None,
        mcp_registry: MCPToolRegistry | None = None,
    ) -> None:
        """Initialize the unified tool registry.

        Args:
            hierarchical_registry: Optional hierarchical tool registry
            mcp_registry: Optional MCP tool registry
        """
        self.hierarchical_registry = hierarchical_registry if hierarchical_registry is not None else HierarchicalToolRegistry()
        self.mcp_registry = mcp_registry if mcp_registry is not None else MCPToolRegistry()

    def get_for_scope(
        self,
        name: str,
        scope: CapabilityScope,
        resolve_upward: bool = True,
    ) -> ToolSpec | None:
        """Get a tool from the hierarchical registry by scope.

        Args:
            name: Tool name
            scope: Capability scope for resolution
            resolve_upward: Whether to resolve through parent scopes

        Returns:
            ToolSpec if found, None otherwise
        """
        return self.hierarchical_registry.get_for_scope(name, scope, resolve_upward)

    def get_mcp_tool(self, qualified_name: str) -> MCPToolDefinition | None:
        """Get a tool from the MCP registry by qualified name.

        Args:
            qualified_name: Qualified name in format 'server_name:tool_name'

        Returns:
            MCPToolDefinition if found, None otherwise
        """
        return self.mcp_registry.get_tool(qualified_name)

    def get(
        self,
        name: str,
        scope: CapabilityScope,
        resolve_upward: bool = True,
    ) -> ToolSpec | MCPToolDefinition | None:
        """Get a tool by name, checking hierarchical first then MCP.

        This is the unified lookup method that:
        1. Checks hierarchical registry first (scope-aware)
        2. Falls back to MCP registry if not found

        Args:
            name: Tool name (or qualified MCP name)
            scope: Capability scope for hierarchical resolution
            resolve_upward: Whether to resolve through parent scopes

        Returns:
            ToolSpec or MCPToolDefinition if found, None otherwise
        """
        # Check hierarchical registry first
        tool = self.get_for_scope(name, scope, resolve_upward)
        if tool is not None:
            return tool

        # Fall back to MCP registry
        return self.get_mcp_tool(name)

    def list_for_scope(
        self,
        scope: CapabilityScope,
        include_parent_scopes: bool = True,
        include_mcp: bool = False,
    ) -> list[ToolSpec]:
        """List all tools available at a scope.

        Args:
            scope: Capability scope
            include_parent_scopes: Include tools from parent scopes
            include_mcp: Include tools from MCP servers

        Returns:
            List of ToolSpec objects
        """
        # Get hierarchical tools
        tools = self.hierarchical_registry.list_for_scope(scope, include_parent_scopes=include_parent_scopes)

        # Optionally include MCP tools
        if include_mcp:
            mcp_tools = self._convert_mcp_tools_to_specs()
            tools.extend(mcp_tools)

        return tools

    def _convert_mcp_tools_to_specs(self) -> list[ToolSpec]:
        """Convert MCP tool definitions to ToolSpec objects.

        Returns:
            List of ToolSpec objects from MCP registry
        """
        mcp_tools: list[ToolSpec] = []
        for tool_def in self.mcp_registry._tools.values():
            spec = ToolSpec(
                name=tool_def.name,
                description=tool_def.description,
                schema=tool_def.input_schema,
            )
            mcp_tools.append(spec)
        return mcp_tools
