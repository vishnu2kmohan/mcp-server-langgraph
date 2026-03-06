"""Tests for HierarchicalToolRegistry.

TDD: These tests define the contract for scope-aware tool registration
and lookup.

ADR-0092: Hierarchical Capability Architecture
"""

from __future__ import annotations

import gc

import pytest

pytestmark = pytest.mark.unit


@pytest.mark.unit
class TestHierarchicalToolRegistryBasic:
    """Tests for HierarchicalToolRegistry basic functionality."""

    def teardown_method(self) -> None:
        """Force GC to prevent mock accumulation in xdist workers."""
        gc.collect()

    def test_hierarchical_tool_registry_exists(self) -> None:
        """Test HierarchicalToolRegistry class exists."""
        from mcp_server_langgraph.tools.hierarchical import HierarchicalToolRegistry

        assert HierarchicalToolRegistry is not None

    def test_has_register_for_scope_method(self) -> None:
        """Test HierarchicalToolRegistry has register_for_scope method."""
        from mcp_server_langgraph.tools.hierarchical import HierarchicalToolRegistry

        registry = HierarchicalToolRegistry()
        assert hasattr(registry, "register_for_scope")
        assert callable(registry.register_for_scope)

    def test_has_get_for_scope_method(self) -> None:
        """Test HierarchicalToolRegistry has get_for_scope method."""
        from mcp_server_langgraph.tools.hierarchical import HierarchicalToolRegistry

        registry = HierarchicalToolRegistry()
        assert hasattr(registry, "get_for_scope")
        assert callable(registry.get_for_scope)

    def test_has_list_for_scope_method(self) -> None:
        """Test HierarchicalToolRegistry has list_for_scope method."""
        from mcp_server_langgraph.tools.hierarchical import HierarchicalToolRegistry

        registry = HierarchicalToolRegistry()
        assert hasattr(registry, "list_for_scope")
        assert callable(registry.list_for_scope)


@pytest.mark.unit
class TestHierarchicalToolRegistration:
    """Tests for scope-based tool registration."""

    def teardown_method(self) -> None:
        """Force GC to prevent mock accumulation in xdist workers."""
        gc.collect()

    def test_register_tool_at_project_scope(self) -> None:
        """Test registering a tool at PROJECT scope."""
        from mcp_server_langgraph.capabilities.provider import ToolSpec
        from mcp_server_langgraph.core.scopes import CapabilityScope
        from mcp_server_langgraph.tools.hierarchical import HierarchicalToolRegistry

        registry = HierarchicalToolRegistry()
        tool = ToolSpec(name="project-tool", description="A project tool")

        registry.register_for_scope(tool, CapabilityScope.PROJECT)

        result = registry.get_for_scope("project-tool", CapabilityScope.PROJECT)
        assert result is not None
        assert result.name == "project-tool"

    def test_register_tool_at_user_scope(self) -> None:
        """Test registering a tool at USER scope."""
        from mcp_server_langgraph.capabilities.provider import ToolSpec
        from mcp_server_langgraph.core.scopes import CapabilityScope
        from mcp_server_langgraph.tools.hierarchical import HierarchicalToolRegistry

        registry = HierarchicalToolRegistry()
        tool = ToolSpec(name="user-tool", description="A user tool")

        registry.register_for_scope(tool, CapabilityScope.USER)

        result = registry.get_for_scope("user-tool", CapabilityScope.USER)
        assert result is not None

    def test_register_tool_at_session_scope(self) -> None:
        """Test registering a tool at SESSION scope."""
        from mcp_server_langgraph.capabilities.provider import ToolSpec
        from mcp_server_langgraph.core.scopes import CapabilityScope
        from mcp_server_langgraph.tools.hierarchical import HierarchicalToolRegistry

        registry = HierarchicalToolRegistry()
        tool = ToolSpec(name="session-tool", description="A session tool")

        registry.register_for_scope(tool, CapabilityScope.SESSION)

        result = registry.get_for_scope("session-tool", CapabilityScope.SESSION)
        assert result is not None


@pytest.mark.unit
class TestHierarchicalToolResolution:
    """Tests for scope-based tool resolution."""

    def teardown_method(self) -> None:
        """Force GC to prevent mock accumulation in xdist workers."""
        gc.collect()

    def test_get_for_scope_resolves_upward(self) -> None:
        """Test get_for_scope resolves from parent scopes."""
        from mcp_server_langgraph.capabilities.provider import ToolSpec
        from mcp_server_langgraph.core.scopes import CapabilityScope
        from mcp_server_langgraph.tools.hierarchical import HierarchicalToolRegistry

        registry = HierarchicalToolRegistry()
        tool = ToolSpec(name="shared-tool", description="Shared tool")

        # Register at PROJECT scope
        registry.register_for_scope(tool, CapabilityScope.PROJECT)

        # Should be accessible from TASK scope
        result = registry.get_for_scope("shared-tool", CapabilityScope.TASK)
        assert result is not None
        assert result.name == "shared-tool"

    def test_lower_scope_overrides_higher_scope(self) -> None:
        """Test lower scope tools override higher scope tools."""
        from mcp_server_langgraph.capabilities.provider import ToolSpec
        from mcp_server_langgraph.core.scopes import CapabilityScope
        from mcp_server_langgraph.tools.hierarchical import HierarchicalToolRegistry

        registry = HierarchicalToolRegistry()

        # Register at PROJECT scope
        project_tool = ToolSpec(name="override-test", description="Project version")
        registry.register_for_scope(project_tool, CapabilityScope.PROJECT)

        # Register at SESSION scope (higher precedence)
        session_tool = ToolSpec(name="override-test", description="Session version")
        registry.register_for_scope(session_tool, CapabilityScope.SESSION)

        # Should get SESSION version when querying from TASK
        result = registry.get_for_scope("override-test", CapabilityScope.TASK)
        assert result is not None
        assert result.description == "Session version"

    def test_list_for_scope_merges_parent_scopes(self) -> None:
        """Test list_for_scope merges tools from parent scopes."""
        from mcp_server_langgraph.capabilities.provider import ToolSpec
        from mcp_server_langgraph.core.scopes import CapabilityScope
        from mcp_server_langgraph.tools.hierarchical import HierarchicalToolRegistry

        registry = HierarchicalToolRegistry()

        # Register tools at different scopes
        project_tool = ToolSpec(name="project-only", description="Project tool")
        session_tool = ToolSpec(name="session-only", description="Session tool")

        registry.register_for_scope(project_tool, CapabilityScope.PROJECT)
        registry.register_for_scope(session_tool, CapabilityScope.SESSION)

        # List at TASK scope should include both
        results = registry.list_for_scope(CapabilityScope.TASK, include_parent_scopes=True)
        names = [t.name for t in results]

        assert "project-only" in names
        assert "session-only" in names


@pytest.mark.unit
class TestHierarchicalToolMisc:
    """Tests for miscellaneous tool registry functionality."""

    def teardown_method(self) -> None:
        """Force GC to prevent mock accumulation in xdist workers."""
        gc.collect()

    def test_register_flat_method_works(self) -> None:
        """Test flat register() method for backward compat."""
        from mcp_server_langgraph.capabilities.provider import ToolSpec
        from mcp_server_langgraph.tools.hierarchical import HierarchicalToolRegistry

        registry = HierarchicalToolRegistry()
        tool = ToolSpec(name="flat-tool", description="Flat tool")

        registry.register(tool)

        result = registry.get("flat-tool")
        assert result is not None

    def test_list_all_includes_scoped(self) -> None:
        """Test list_all() includes scoped tools."""
        from mcp_server_langgraph.capabilities.provider import ToolSpec
        from mcp_server_langgraph.core.scopes import CapabilityScope
        from mcp_server_langgraph.tools.hierarchical import HierarchicalToolRegistry

        registry = HierarchicalToolRegistry()
        tool = ToolSpec(name="scoped-tool", description="Scoped tool")

        registry.register_for_scope(tool, CapabilityScope.PROJECT)

        all_tools = registry.list_all()
        names = [t.name for t in all_tools]
        assert "scoped-tool" in names
