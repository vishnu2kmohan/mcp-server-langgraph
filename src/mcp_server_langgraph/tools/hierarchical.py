"""HierarchicalToolRegistry for scope-aware tool management.

Provides hierarchical scope support for tool registration and lookup,
enabling tools to be registered at specific CapabilityScope levels with
proper resolution order.

Scope Resolution:
- Tools registered at higher scopes (PROJECT, USER) are available at
  lower scopes (SESSION, TASK)
- Lower scope tools override higher scope tools with the same name
- Resolution follows the scope precedence order from ADR-0092

Usage:
    from mcp_server_langgraph.tools.hierarchical import HierarchicalToolRegistry
    from mcp_server_langgraph.core.scopes import CapabilityScope

    registry = HierarchicalToolRegistry()
    registry.register_for_scope(tool, CapabilityScope.PROJECT)
    tool = registry.get_for_scope("tool-name", CapabilityScope.TASK)

ADR Reference: adr/adr-0092-hierarchical-capability-architecture.md
"""

from __future__ import annotations

from collections import defaultdict

from mcp_server_langgraph.capabilities.provider import ToolSpec
from mcp_server_langgraph.core.scopes import (
    CapabilityScope,
    SCOPE_PRECEDENCE,
)


class HierarchicalToolRegistry:
    """Tool registry with hierarchical scope support.

    Supports scope-based registration and lookup for tools.
    Tools can be registered at specific scopes, and lookup resolves
    from the requested scope upward through parent scopes.

    Attributes:
        _scoped_tools: Dict mapping scope -> name -> tool
        _flat_tools: Dict for backward-compatible flat registration
    """

    def __init__(self) -> None:
        """Initialize hierarchical tool registry."""
        # Scoped storage: scope -> name -> tool
        self._scoped_tools: dict[CapabilityScope, dict[str, ToolSpec]] = defaultdict(dict)
        # Flat storage for backward compatibility
        self._flat_tools: dict[str, ToolSpec] = {}

    def register_for_scope(self, tool: ToolSpec, scope: CapabilityScope) -> None:
        """Register a tool at a specific scope.

        Args:
            tool: ToolSpec to register
            scope: CapabilityScope to register at
        """
        self._scoped_tools[scope][tool.name] = tool
        # Also register in flat registry for backward compatibility
        self._flat_tools[tool.name] = tool

    def get_for_scope(
        self,
        name: str,
        scope: CapabilityScope,
        resolve_upward: bool = True,
    ) -> ToolSpec | None:
        """Get a tool by name, resolving through scope hierarchy.

        Looks for the tool at the specified scope first, then
        traverses upward through parent scopes until found.

        Args:
            name: Tool name to look up
            scope: Starting scope for resolution
            resolve_upward: If True, resolve through parent scopes

        Returns:
            ToolSpec if found, None otherwise
        """
        if resolve_upward:
            # Get scopes to check, starting from requested scope
            scopes_to_check = self._get_resolution_order(scope)

            for check_scope in scopes_to_check:
                if check_scope in self._scoped_tools:
                    if name in self._scoped_tools[check_scope]:
                        return self._scoped_tools[check_scope][name]

            # Fall back to flat registry
            return self._flat_tools.get(name)
        else:
            # Only check the specified scope
            if scope in self._scoped_tools:
                return self._scoped_tools[scope].get(name)
            return None

    def list_for_scope(
        self,
        scope: CapabilityScope,
        include_parent_scopes: bool = True,
    ) -> list[ToolSpec]:
        """List tools available at a scope.

        Returns all tools visible at the specified scope, optionally
        including tools from parent scopes. When including parent
        scopes, lower scope tools override higher scope tools with
        the same name.

        Args:
            scope: Scope to list tools for
            include_parent_scopes: If True, include tools from parent scopes

        Returns:
            List of tools available at this scope
        """
        if include_parent_scopes:
            # Collect tools from all parent scopes, with lower scopes overriding
            tools_by_name: dict[str, ToolSpec] = {}

            # Traverse from highest scope to lowest (so lower overrides higher)
            scopes_to_check = list(reversed(self._get_resolution_order(scope)))

            for check_scope in scopes_to_check:
                if check_scope in self._scoped_tools:
                    tools_by_name.update(self._scoped_tools[check_scope])

            return list(tools_by_name.values())
        else:
            # Only return tools from this exact scope
            if scope in self._scoped_tools:
                return list(self._scoped_tools[scope].values())
            return []

    def register(self, tool: ToolSpec) -> None:
        """Register a tool without specific scope (flat registration).

        Provided for backward compatibility with non-hierarchical usage.

        Args:
            tool: ToolSpec to register
        """
        self._flat_tools[tool.name] = tool

    def get(self, name: str) -> ToolSpec | None:
        """Get a tool by name from flat registry.

        Provided for backward compatibility with non-hierarchical usage.

        Args:
            name: Tool name to look up

        Returns:
            ToolSpec if found, None otherwise
        """
        return self._flat_tools.get(name)

    def unregister_for_scope(self, name: str, scope: CapabilityScope) -> None:
        """Unregister a tool from a specific scope.

        Args:
            name: Tool name to unregister
            scope: Scope to unregister from
        """
        if scope in self._scoped_tools:
            self._scoped_tools[scope].pop(name, None)

    def clear_scope(self, scope: CapabilityScope) -> None:
        """Clear all tools from a specific scope.

        Args:
            scope: Scope to clear
        """
        if scope in self._scoped_tools:
            self._scoped_tools[scope].clear()

    def list_all(self) -> list[ToolSpec]:
        """List all tools across all scopes.

        Returns:
            List of all registered tools
        """
        # Collect from scoped storage
        all_tools: dict[str, ToolSpec] = {}

        for scope_tools in self._scoped_tools.values():
            all_tools.update(scope_tools)

        # Also include any tools only in flat registry
        for name, tool in self._flat_tools.items():
            if name not in all_tools:
                all_tools[name] = tool

        return list(all_tools.values())

    def _get_resolution_order(self, scope: CapabilityScope) -> list[CapabilityScope]:
        """Get the order of scopes to check for resolution.

        Returns scopes from the requested scope upward to root,
        ordered by precedence (highest first).

        Args:
            scope: Starting scope

        Returns:
            List of scopes in resolution order
        """
        # Find the index of the current scope in precedence order
        try:
            scope_idx = SCOPE_PRECEDENCE.index(scope)
        except ValueError:
            # If scope not in precedence list, just return it alone
            return [scope]

        # Return scopes from current to lowest precedence
        return list(SCOPE_PRECEDENCE[scope_idx:])
