"""UnifiedToolRegistry combining MCP and hierarchical tool registries.

Provides a unified interface for tool lookup that checks both:
- HierarchicalToolRegistry for scope-aware tool resolution
- MCPToolRegistry for tools from external MCP servers
- Native LLM provider tools (v7)

The lookup priority is:
1. Hierarchical registry (scope-aware, higher priority)
2. MCP registry (external tools, fallback)

ADR Reference: adr/adr-0092-hierarchical-capability-architecture.md

Native Tools Integration (v7):
- RegisteredTool: Unified representation for builtin, MCP, and native tools
- tool_id format: "source:name" (e.g., "builtin:web_search", "mcp:github:create_issue")
- Syncs from CachedUnifiedRegistry for MCP tools
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import TYPE_CHECKING, Any, Literal

from mcp_server_langgraph.capabilities.provider import ToolSpec
from mcp_server_langgraph.core.scopes import CapabilityScope
from mcp_server_langgraph.mcp.client.tool_registry import (
    MCPToolDefinition,
    MCPToolRegistry,
)
from mcp_server_langgraph.tools.hierarchical import HierarchicalToolRegistry

if TYPE_CHECKING:
    from langchain_core.tools import BaseTool

# Type alias for tool source
ToolSource = Literal["builtin", "mcp", "native"]


@dataclass
class RegisteredTool:
    """A tool in the unified registry (v7).

    Provides a unified representation for builtin, MCP, and native tools
    with consistent tool_id for selection and tracking.

    Attributes:
        tool_id: Unique ID for selection (e.g., "builtin:web_search", "mcp:github:create_issue")
        name: LangChain-compatible name for binding (e.g., "github_create_issue")
        qualified_name: API-compatible name (same as name for builtin; qualified for MCP)
        source: Tool source type
        display_name: Human-readable display name
        description: Tool description
        category: Tool category for grouping
        tool: BaseTool for builtin/mcp; None for native
        native_config: Provider-specific config for native tools
        server_name: MCP server name (MCP tools only)
        provider: Native provider name (native tools only)
        requires_sandbox: Whether tool requires sandbox environment
        fallback_builtin: Builtin tool name for fallback (native tools only)
    """

    tool_id: str
    name: str
    qualified_name: str
    source: ToolSource
    display_name: str
    description: str
    category: str | None
    tool: BaseTool | None
    native_config: dict[str, Any] | None = None
    server_name: str | None = None
    provider: str | None = None
    requires_sandbox: bool = False
    fallback_builtin: str | None = None


class UnifiedToolRegistry:
    """Unified tool registry combining MCP, hierarchical, and native tools.

    Provides a single interface for looking up tools from:
    - Scope-aware hierarchical registry
    - External MCP servers
    - Native LLM provider tools (v7)

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

        # v7: Source-aware tool registry for native tools integration
        self._by_id: dict[str, RegisteredTool] = {}
        self._by_lc_name: dict[str, list[RegisteredTool]] = {}
        self._by_qualified_name: dict[str, RegisteredTool] = {}

    # =========================================================================
    # v7: Native Tools Integration Methods
    # =========================================================================

    def register_builtin(self, tool: BaseTool, category: str | None = None) -> None:
        """Register a built-in tool.

        Args:
            tool: LangChain BaseTool instance
            category: Tool category for grouping
        """
        from mcp_server_langgraph.tools.constants import tool_requires_sandbox

        tool_id = f"builtin:{tool.name}"
        qualified_name = tool.name  # Same as name for builtins

        reg = RegisteredTool(
            tool_id=tool_id,
            name=tool.name,
            qualified_name=qualified_name,
            source="builtin",
            display_name=tool.name.replace("_", " ").title(),
            description=tool.description or "",
            category=category,
            tool=tool,
            requires_sandbox=tool_requires_sandbox(tool.name),
        )
        self._by_id[tool_id] = reg
        self._by_lc_name.setdefault(tool.name, []).append(reg)
        self._by_qualified_name[qualified_name] = reg

    def register_mcp_from_cached(self, mcp_tool_dict: dict[str, Any], tool: BaseTool) -> None:
        """Register MCP tool from CachedUnifiedRegistry dict + proxy.

        CRITICAL (v7): Use qualified_name from cached registry for tool_id.
        This maintains compatibility with existing API consumers.

        Args:
            mcp_tool_dict: Dict from CachedUnifiedRegistry with qualified_name
            tool: MCPToolProxy with .name in underscore format
        """
        qualified_name = mcp_tool_dict.get("qualified_name", tool.name)
        tool_id = f"mcp:{qualified_name}"  # e.g., "mcp:github:create_issue"
        lc_name = tool.name  # e.g., "github_create_issue" (underscore for LangChain)
        server_name = mcp_tool_dict.get("server_name", "")

        reg = RegisteredTool(
            tool_id=tool_id,
            name=lc_name,  # LangChain name for binding
            qualified_name=qualified_name,  # API name for display
            source="mcp",
            display_name=f"{mcp_tool_dict.get('name', lc_name)} ({server_name})",
            description=mcp_tool_dict.get("description", tool.description or ""),
            category="mcp",
            tool=tool,
            server_name=server_name,
        )
        self._by_id[tool_id] = reg
        self._by_lc_name.setdefault(lc_name, []).append(reg)
        self._by_qualified_name[qualified_name] = reg

    def register_native(
        self,
        name: str,
        provider: str,
        provider_type: str,
        description: str,
        fallback_builtin: str | None = None,
    ) -> None:
        """Register a native provider tool.

        Args:
            name: Tool name
            provider: Provider name (e.g., "anthropic", "google")
            provider_type: Provider's type identifier
            description: Tool description
            fallback_builtin: Builtin tool to fall back to
        """
        tool_id = f"native:{name}"
        reg = RegisteredTool(
            tool_id=tool_id,
            name=name,
            qualified_name=name,
            source="native",
            display_name=f"{name.replace('_', ' ').title()} (Native)",
            description=description,
            category="native",
            tool=None,
            native_config={"type": provider_type, "provider": provider},
            provider=provider,
            fallback_builtin=fallback_builtin,
        )
        self._by_id[tool_id] = reg
        self._by_lc_name.setdefault(name, []).append(reg)
        self._by_qualified_name[name] = reg

    def get_by_id(self, tool_id: str) -> RegisteredTool | None:
        """Get tool by unique tool_id.

        Args:
            tool_id: Unique tool identifier (e.g., "builtin:web_search")

        Returns:
            RegisteredTool if found, None otherwise
        """
        return self._by_id.get(tool_id)

    def get_by_lc_name(self, lc_name: str) -> list[RegisteredTool]:
        """Get tools by LangChain name.

        May return multiple tools if same name exists in different sources.

        Args:
            lc_name: LangChain tool name

        Returns:
            List of matching RegisteredTool objects
        """
        return self._by_lc_name.get(lc_name, [])

    def get_by_qualified_name(self, qualified_name: str) -> RegisteredTool | None:
        """Get tool by qualified_name (for API compatibility).

        Args:
            qualified_name: Qualified name (e.g., "github:create_issue")

        Returns:
            RegisteredTool if found, None otherwise
        """
        return self._by_qualified_name.get(qualified_name)

    def get_all(self) -> list[RegisteredTool]:
        """Get all registered tools.

        Returns:
            List of all RegisteredTool objects
        """
        return list(self._by_id.values())

    def filter_by_source(self, source: ToolSource) -> list[RegisteredTool]:
        """Filter tools by source.

        Args:
            source: Tool source ("builtin", "mcp", "native")

        Returns:
            List of tools from the specified source
        """
        return [t for t in self._by_id.values() if t.source == source]

    def resolve_tool_ids(self, tool_ids: list[str]) -> tuple[list[BaseTool], list[dict[str, Any]]]:
        """Resolve tool_ids to executable tools and native configs.

        Args:
            tool_ids: List of tool_id strings

        Returns:
            Tuple of (lc_tools, native_configs)
        """
        lc_tools: list[BaseTool] = []
        native_configs: list[dict[str, Any]] = []

        for tool_id in tool_ids:
            reg = self._by_id.get(tool_id)
            if not reg:
                continue
            if reg.source == "native" and reg.native_config:
                native_configs.append(reg.native_config)
            elif reg.tool:
                lc_tools.append(reg.tool)

        return lc_tools, native_configs

    def clear_mcp_tools(self) -> None:
        """Clear MCP tools for re-sync."""
        mcp_ids = [tid for tid, reg in self._by_id.items() if reg.source == "mcp"]
        for tid in mcp_ids:
            reg = self._by_id.pop(tid)
            self._by_qualified_name.pop(reg.qualified_name, None)
            if reg.name in self._by_lc_name:
                self._by_lc_name[reg.name] = [r for r in self._by_lc_name[reg.name] if r.source != "mcp"]

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


# =============================================================================
# Global Registry (Singleton Pattern)
# =============================================================================

_registry: UnifiedToolRegistry | None = None


def get_tool_registry() -> UnifiedToolRegistry:
    """Get the global tool registry singleton.

    Creates and initializes the registry on first call,
    populating with builtin and native tools.

    Returns:
        Global UnifiedToolRegistry instance
    """
    global _registry
    if _registry is None:
        _registry = _initialize_registry()
    return _registry


def invalidate_registry() -> None:
    """Invalidate the global registry singleton.

    Call this to force re-initialization on next get_tool_registry() call.
    Useful for testing or when MCP connections change.
    """
    global _registry
    _registry = None


async def sync_mcp_tools() -> None:
    """Sync MCP tools from CachedUnifiedRegistry.

    Called at startup and on MCP connection changes.
    """
    from mcp_server_langgraph.observability.telemetry import logger

    registry = get_tool_registry()
    registry.clear_mcp_tools()

    try:
        from mcp_server_langgraph.mcp.client.cached_unified_registry import (
            get_cached_unified_registry,
        )
        from mcp_server_langgraph.mcp.client.tool_proxy import get_mcp_tool_proxies

        cached = get_cached_unified_registry()
        mcp_tool_dicts = await cached.get_tools()
        tool_proxies = await get_mcp_tool_proxies()

        # Create lookup by qualified_name
        proxy_by_qualified: dict[str, Any] = {}
        for t in tool_proxies:
            server = getattr(t, "mcp_server", "")
            tool_name = getattr(t, "mcp_tool_name", t.name)
            key = f"{server}:{tool_name}"
            proxy_by_qualified[key] = t

        for mcp_dict in mcp_tool_dicts:
            qualified_name = mcp_dict.get("qualified_name", "")
            proxy = proxy_by_qualified.get(qualified_name)
            if proxy:
                registry.register_mcp_from_cached(mcp_dict, proxy)

        logger.info(f"Synced {len(mcp_tool_dicts)} MCP tools to registry")

    except ImportError as e:
        logger.debug(f"MCP client not available for sync: {e}")
    except Exception as e:
        logger.warning(f"Failed to sync MCP tools: {e}")


def _initialize_registry() -> UnifiedToolRegistry:
    """Initialize registry with builtins and native tools.

    MCP tools are synced separately via sync_mcp_tools().

    Returns:
        Initialized UnifiedToolRegistry
    """
    from mcp_server_langgraph.tools import get_all_tools
    from mcp_server_langgraph.tools.constants import TOOL_CATEGORY_MAP
    from mcp_server_langgraph.tools.native_registry import NATIVE_TOOLS

    registry = UnifiedToolRegistry()

    # Register builtin tools
    try:
        for tool in get_all_tools():
            category = TOOL_CATEGORY_MAP.get(tool.name)
            registry.register_builtin(tool, category)
    except Exception:
        # Tools module may not be fully initialized in tests
        pass

    # Register native tools
    for (_name, _provider), defn in NATIVE_TOOLS.items():
        registry.register_native(
            name=defn.name,
            provider=defn.provider,
            provider_type=defn.provider_type,
            description=defn.description,
            fallback_builtin=defn.fallback_builtin,
        )

    return registry
