"""Tests for UnifiedToolRegistry.

TDD: These tests define the contract for the unified tool registry that
combines MCP tools with hierarchical scope-aware tools.

ADR-0092: Hierarchical Capability Architecture
"""

from __future__ import annotations

import gc

import pytest

pytestmark = pytest.mark.unit


@pytest.mark.unit
@pytest.mark.xdist_group(name="unified_registry_basic")
class TestUnifiedToolRegistryBasic:
    """Tests for UnifiedToolRegistry basic functionality."""

    def teardown_method(self) -> None:
        """Force GC to prevent mock accumulation in xdist workers."""
        gc.collect()

    def test_unified_registry_exists(self) -> None:
        """Test UnifiedToolRegistry class exists."""
        from mcp_server_langgraph.tools.unified_registry import UnifiedToolRegistry

        assert UnifiedToolRegistry is not None

    def test_unified_registry_accepts_hierarchical_registry(self) -> None:
        """Test UnifiedToolRegistry accepts hierarchical_registry parameter."""
        from mcp_server_langgraph.tools.hierarchical import HierarchicalToolRegistry
        from mcp_server_langgraph.tools.unified_registry import UnifiedToolRegistry

        hierarchical = HierarchicalToolRegistry()
        registry = UnifiedToolRegistry(hierarchical_registry=hierarchical)

        assert registry.hierarchical_registry is hierarchical

    def test_unified_registry_accepts_mcp_registry(self) -> None:
        """Test UnifiedToolRegistry accepts mcp_registry parameter."""
        from mcp_server_langgraph.mcp.client.tool_registry import MCPToolRegistry
        from mcp_server_langgraph.tools.unified_registry import UnifiedToolRegistry

        mcp = MCPToolRegistry()
        registry = UnifiedToolRegistry(mcp_registry=mcp)

        assert registry.mcp_registry is mcp

    def test_unified_registry_creates_default_registries(self) -> None:
        """Test UnifiedToolRegistry creates default registries if not provided."""
        from mcp_server_langgraph.tools.unified_registry import UnifiedToolRegistry

        registry = UnifiedToolRegistry()

        assert registry.hierarchical_registry is not None
        assert registry.mcp_registry is not None


@pytest.mark.unit
@pytest.mark.xdist_group(name="unified_registry_get")
class TestUnifiedToolRegistryGet:
    """Tests for UnifiedToolRegistry get operations."""

    def teardown_method(self) -> None:
        """Force GC to prevent mock accumulation in xdist workers."""
        gc.collect()

    def test_get_for_scope_returns_hierarchical_tool(self) -> None:
        """Test get_for_scope returns tool from hierarchical registry."""
        from mcp_server_langgraph.capabilities.provider import ToolSpec
        from mcp_server_langgraph.core.scopes import CapabilityScope
        from mcp_server_langgraph.tools.hierarchical import HierarchicalToolRegistry
        from mcp_server_langgraph.tools.unified_registry import UnifiedToolRegistry

        hierarchical = HierarchicalToolRegistry()
        tool = ToolSpec(name="test-tool", description="Test tool")
        hierarchical.register_for_scope(tool, CapabilityScope.PROJECT)

        registry = UnifiedToolRegistry(hierarchical_registry=hierarchical)
        result = registry.get_for_scope("test-tool", CapabilityScope.TASK)

        assert result is not None
        assert result.name == "test-tool"

    def test_get_for_scope_returns_none_for_missing(self) -> None:
        """Test get_for_scope returns None for missing tool."""
        from mcp_server_langgraph.core.scopes import CapabilityScope
        from mcp_server_langgraph.tools.unified_registry import UnifiedToolRegistry

        registry = UnifiedToolRegistry()
        result = registry.get_for_scope("nonexistent", CapabilityScope.TASK)

        assert result is None

    def test_get_mcp_tool_returns_mcp_tool(self) -> None:
        """Test get_mcp_tool returns tool from MCP registry."""
        from mcp_server_langgraph.mcp.client.tool_registry import (
            MCPToolDefinition,
            MCPToolRegistry,
        )
        from mcp_server_langgraph.tools.unified_registry import UnifiedToolRegistry

        mcp = MCPToolRegistry()
        # Manually add a tool to the registry
        tool_def = MCPToolDefinition(
            server_name="test-server",
            name="mcp-tool",
            description="MCP tool",
            input_schema={},
        )
        mcp._tools[tool_def.qualified_name] = tool_def

        registry = UnifiedToolRegistry(mcp_registry=mcp)
        result = registry.get_mcp_tool("test-server:mcp-tool")

        assert result is not None
        assert result.name == "mcp-tool"

    def test_get_mcp_tool_returns_none_for_missing(self) -> None:
        """Test get_mcp_tool returns None for missing tool."""
        from mcp_server_langgraph.tools.unified_registry import UnifiedToolRegistry

        registry = UnifiedToolRegistry()
        result = registry.get_mcp_tool("nonexistent:tool")

        assert result is None


@pytest.mark.unit
@pytest.mark.xdist_group(name="unified_registry_unified")
class TestUnifiedToolRegistryUnified:
    """Tests for UnifiedToolRegistry unified get operation."""

    def teardown_method(self) -> None:
        """Force GC to prevent mock accumulation in xdist workers."""
        gc.collect()

    def test_get_checks_hierarchical_first(self) -> None:
        """Test get checks hierarchical registry first."""
        from mcp_server_langgraph.capabilities.provider import ToolSpec
        from mcp_server_langgraph.core.scopes import CapabilityScope
        from mcp_server_langgraph.tools.hierarchical import HierarchicalToolRegistry
        from mcp_server_langgraph.tools.unified_registry import UnifiedToolRegistry

        hierarchical = HierarchicalToolRegistry()
        tool = ToolSpec(name="search", description="Hierarchical search")
        hierarchical.register_for_scope(tool, CapabilityScope.PROJECT)

        registry = UnifiedToolRegistry(hierarchical_registry=hierarchical)
        result = registry.get("search", CapabilityScope.TASK)

        assert result is not None
        assert result.name == "search"
        assert result.description == "Hierarchical search"

    def test_get_falls_back_to_mcp(self) -> None:
        """Test get falls back to MCP registry when not in hierarchical."""
        from mcp_server_langgraph.core.scopes import CapabilityScope
        from mcp_server_langgraph.mcp.client.tool_registry import (
            MCPToolDefinition,
            MCPToolRegistry,
        )
        from mcp_server_langgraph.tools.unified_registry import UnifiedToolRegistry

        mcp = MCPToolRegistry()
        tool_def = MCPToolDefinition(
            server_name="test-server",
            name="mcp-only-tool",
            description="MCP only tool",
            input_schema={},
        )
        mcp._tools[tool_def.qualified_name] = tool_def

        registry = UnifiedToolRegistry(mcp_registry=mcp)
        result = registry.get("test-server:mcp-only-tool", CapabilityScope.TASK)

        assert result is not None
        assert result.name == "mcp-only-tool"


@pytest.mark.unit
@pytest.mark.xdist_group(name="unified_registry_list")
class TestUnifiedToolRegistryList:
    """Tests for UnifiedToolRegistry list operations."""

    def teardown_method(self) -> None:
        """Force GC to prevent mock accumulation in xdist workers."""
        gc.collect()

    def test_list_for_scope_includes_hierarchical_tools(self) -> None:
        """Test list_for_scope includes tools from hierarchical registry."""
        from mcp_server_langgraph.capabilities.provider import ToolSpec
        from mcp_server_langgraph.core.scopes import CapabilityScope
        from mcp_server_langgraph.tools.hierarchical import HierarchicalToolRegistry
        from mcp_server_langgraph.tools.unified_registry import UnifiedToolRegistry

        hierarchical = HierarchicalToolRegistry()
        tool = ToolSpec(name="tool-1", description="Tool 1")
        hierarchical.register_for_scope(tool, CapabilityScope.PROJECT)

        registry = UnifiedToolRegistry(hierarchical_registry=hierarchical)
        result = registry.list_for_scope(CapabilityScope.TASK)

        assert len(result) >= 1
        assert any(t.name == "tool-1" for t in result)

    def test_list_for_scope_includes_mcp_tools(self) -> None:
        """Test list_for_scope includes tools from MCP registry."""
        from mcp_server_langgraph.core.scopes import CapabilityScope
        from mcp_server_langgraph.mcp.client.tool_registry import (
            MCPToolDefinition,
            MCPToolRegistry,
        )
        from mcp_server_langgraph.tools.unified_registry import UnifiedToolRegistry

        mcp = MCPToolRegistry()
        tool_def = MCPToolDefinition(
            server_name="test-server",
            name="mcp-tool",
            description="MCP tool",
            input_schema={},
        )
        mcp._tools[tool_def.qualified_name] = tool_def

        registry = UnifiedToolRegistry(mcp_registry=mcp)
        result = registry.list_for_scope(CapabilityScope.TASK, include_mcp=True)

        assert len(result) >= 1
        assert any(t.name == "mcp-tool" for t in result)

    def test_list_for_scope_excludes_mcp_by_default(self) -> None:
        """Test list_for_scope excludes MCP tools by default."""
        from mcp_server_langgraph.core.scopes import CapabilityScope
        from mcp_server_langgraph.mcp.client.tool_registry import (
            MCPToolDefinition,
            MCPToolRegistry,
        )
        from mcp_server_langgraph.tools.unified_registry import UnifiedToolRegistry

        mcp = MCPToolRegistry()
        tool_def = MCPToolDefinition(
            server_name="test-server",
            name="mcp-only",
            description="MCP only",
            input_schema={},
        )
        mcp._tools[tool_def.qualified_name] = tool_def

        registry = UnifiedToolRegistry(mcp_registry=mcp)
        result = registry.list_for_scope(CapabilityScope.TASK, include_mcp=False)

        # MCP tools should not be included
        assert not any(t.name == "mcp-only" for t in result)


# =============================================================================
# v7: Native Tools Integration Tests
# =============================================================================


@pytest.mark.unit
@pytest.mark.xdist_group(name="unified_registry_v7_registered_tool")
class TestRegisteredTool:
    """Tests for RegisteredTool dataclass (v7)."""

    def teardown_method(self) -> None:
        """Force GC to prevent mock accumulation in xdist workers."""
        gc.collect()

    def test_registered_tool_has_required_fields(self) -> None:
        """RegisteredTool should have all required fields."""
        from mcp_server_langgraph.tools.unified_registry import RegisteredTool

        tool = RegisteredTool(
            tool_id="builtin:web_search",
            name="web_search",
            qualified_name="web_search",
            source="builtin",
            display_name="Web Search",
            description="Search the web",
            category="search",
            tool=None,
        )

        assert tool.tool_id == "builtin:web_search"
        assert tool.name == "web_search"
        assert tool.qualified_name == "web_search"
        assert tool.source == "builtin"
        assert tool.display_name == "Web Search"
        assert tool.description == "Search the web"
        assert tool.category == "search"

    def test_registered_tool_native_has_extra_fields(self) -> None:
        """RegisteredTool for native tools should have extra fields."""
        from mcp_server_langgraph.tools.unified_registry import RegisteredTool

        tool = RegisteredTool(
            tool_id="native:web_search",
            name="web_search",
            qualified_name="web_search",
            source="native",
            display_name="Web Search (Native)",
            description="Native web search",
            category="native",
            tool=None,
            native_config={"type": "web_search_20250305"},
            provider="anthropic",
            fallback_builtin="web_search",
        )

        assert tool.native_config == {"type": "web_search_20250305"}
        assert tool.provider == "anthropic"
        assert tool.fallback_builtin == "web_search"


@pytest.mark.unit
@pytest.mark.xdist_group(name="unified_registry_v7_builtin")
class TestUnifiedRegistryBuiltinTools:
    """Tests for builtin tool registration (v7)."""

    def teardown_method(self) -> None:
        """Force GC to prevent mock accumulation in xdist workers."""
        gc.collect()

    def test_register_builtin_creates_tool_id(self) -> None:
        """register_builtin should create tool_id with builtin: prefix."""
        from unittest.mock import MagicMock

        from mcp_server_langgraph.tools.unified_registry import UnifiedToolRegistry

        registry = UnifiedToolRegistry()

        mock_tool = MagicMock()
        mock_tool.name = "web_search"
        mock_tool.description = "Search the web"

        registry.register_builtin(mock_tool, category="search")

        tools = registry.get_all()
        assert len(tools) == 1
        assert tools[0].tool_id == "builtin:web_search"
        assert tools[0].source == "builtin"

    def test_get_by_id_returns_builtin(self) -> None:
        """get_by_id should return builtin tool."""
        from unittest.mock import MagicMock

        from mcp_server_langgraph.tools.unified_registry import UnifiedToolRegistry

        registry = UnifiedToolRegistry()

        mock_tool = MagicMock()
        mock_tool.name = "calculator"
        mock_tool.description = "Math operations"

        registry.register_builtin(mock_tool, category="calculator")

        result = registry.get_by_id("builtin:calculator")
        assert result is not None
        assert result.tool_id == "builtin:calculator"


@pytest.mark.unit
@pytest.mark.xdist_group(name="unified_registry_v7_native")
class TestUnifiedRegistryNativeTools:
    """Tests for native tool registration (v7)."""

    def teardown_method(self) -> None:
        """Force GC to prevent mock accumulation in xdist workers."""
        gc.collect()

    def test_register_native_creates_tool_id(self) -> None:
        """register_native should create tool_id with native: prefix."""
        from mcp_server_langgraph.tools.unified_registry import UnifiedToolRegistry

        registry = UnifiedToolRegistry()

        registry.register_native(
            name="web_search",
            provider="anthropic",
            provider_type="web_search_20250305",
            description="Native web search",
            fallback_builtin="web_search",
        )

        tools = registry.get_all()
        assert len(tools) == 1
        assert tools[0].tool_id == "native:web_search"
        assert tools[0].source == "native"

    def test_native_tool_has_native_config(self) -> None:
        """Native tools should have native_config."""
        from mcp_server_langgraph.tools.unified_registry import UnifiedToolRegistry

        registry = UnifiedToolRegistry()

        registry.register_native(
            name="web_search",
            provider="anthropic",
            provider_type="web_search_20250305",
            description="Native web search",
            fallback_builtin="web_search",
        )

        tool = registry.get_by_id("native:web_search")
        assert tool is not None
        assert tool.native_config == {
            "type": "web_search_20250305",
            "provider": "anthropic",
        }


@pytest.mark.unit
@pytest.mark.xdist_group(name="unified_registry_v7_mcp")
class TestUnifiedRegistryMCPToolsV7:
    """Tests for MCP tool registration with v7 tool_id format."""

    def teardown_method(self) -> None:
        """Force GC to prevent mock accumulation in xdist workers."""
        gc.collect()

    def test_mcp_tool_id_uses_qualified_name(self) -> None:
        """MCP tool_id should use qualified_name format: mcp:{qualified_name}."""
        from unittest.mock import MagicMock

        from mcp_server_langgraph.tools.unified_registry import UnifiedToolRegistry

        registry = UnifiedToolRegistry()

        mock_tool = MagicMock()
        mock_tool.name = "github_create_issue"
        mock_tool.description = "Create issue"

        registry.register_mcp_from_cached(
            mcp_tool_dict={
                "qualified_name": "github:create_issue",
                "name": "create_issue",
                "description": "Create a GitHub issue",
                "server_name": "github",
            },
            tool=mock_tool,
        )

        tools = registry.get_all()
        assert len(tools) == 1
        # tool_id uses colon-separated qualified_name
        assert tools[0].tool_id == "mcp:github:create_issue"
        # name uses underscore for LangChain compatibility
        assert tools[0].name == "github_create_issue"

    def test_clear_mcp_tools_removes_only_mcp(self) -> None:
        """clear_mcp_tools should remove only MCP tools."""
        from unittest.mock import MagicMock

        from mcp_server_langgraph.tools.unified_registry import UnifiedToolRegistry

        registry = UnifiedToolRegistry()

        # Register builtin
        mock_builtin = MagicMock()
        mock_builtin.name = "calculator"
        mock_builtin.description = "Math"
        registry.register_builtin(mock_builtin, category="calculator")

        # Register MCP
        mock_mcp = MagicMock()
        mock_mcp.name = "github_create_issue"
        mock_mcp.description = "Create issue"
        registry.register_mcp_from_cached(
            mcp_tool_dict={
                "qualified_name": "github:create_issue",
                "name": "create_issue",
                "description": "Create issue",
                "server_name": "github",
            },
            tool=mock_mcp,
        )

        assert len(registry.get_all()) == 2

        registry.clear_mcp_tools()

        tools = registry.get_all()
        assert len(tools) == 1
        assert tools[0].source == "builtin"


@pytest.mark.unit
@pytest.mark.xdist_group(name="unified_registry_v7_resolve")
class TestUnifiedRegistryResolveToolIds:
    """Tests for resolve_tool_ids method (v7)."""

    def teardown_method(self) -> None:
        """Force GC to prevent mock accumulation in xdist workers."""
        gc.collect()

    def test_resolve_tool_ids_separates_native_and_builtin(self) -> None:
        """resolve_tool_ids should separate native configs from LC tools."""
        from unittest.mock import MagicMock

        from mcp_server_langgraph.tools.unified_registry import UnifiedToolRegistry

        registry = UnifiedToolRegistry()

        mock_tool = MagicMock()
        mock_tool.name = "calculator"
        mock_tool.description = "Math"

        registry.register_builtin(mock_tool, category="calculator")
        registry.register_native(
            name="web_search",
            provider="anthropic",
            provider_type="web_search_20250305",
            description="Search",
            fallback_builtin="web_search",
        )

        lc_tools, native_configs = registry.resolve_tool_ids(["builtin:calculator", "native:web_search"])

        assert len(lc_tools) == 1
        assert lc_tools[0] == mock_tool
        assert len(native_configs) == 1
        assert native_configs[0]["type"] == "web_search_20250305"


@pytest.mark.unit
@pytest.mark.xdist_group(name="unified_registry_v7_global")
class TestGlobalRegistry:
    """Tests for global registry functions (v7)."""

    def teardown_method(self) -> None:
        """Reset registry and force GC."""
        from mcp_server_langgraph.tools.unified_registry import invalidate_registry

        invalidate_registry()
        gc.collect()

    def test_get_tool_registry_returns_singleton(self) -> None:
        """get_tool_registry should return the same instance."""
        from mcp_server_langgraph.tools.unified_registry import (
            get_tool_registry,
            invalidate_registry,
        )

        # Reset state
        invalidate_registry()

        registry1 = get_tool_registry()
        registry2 = get_tool_registry()

        assert registry1 is registry2

    def test_invalidate_registry_clears_singleton(self) -> None:
        """invalidate_registry should clear the singleton."""
        from mcp_server_langgraph.tools.unified_registry import (
            get_tool_registry,
            invalidate_registry,
        )

        registry1 = get_tool_registry()
        invalidate_registry()
        registry2 = get_tool_registry()

        # After invalidation, a new instance should be created
        assert registry1 is not registry2
