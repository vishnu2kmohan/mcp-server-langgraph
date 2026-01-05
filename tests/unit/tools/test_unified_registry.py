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
