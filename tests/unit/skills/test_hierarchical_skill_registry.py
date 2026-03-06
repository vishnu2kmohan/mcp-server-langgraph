"""Tests for HierarchicalSkillRegistry.

TDD: These tests define the contract for scope-aware skill registration
and lookup, extending the existing flat SkillRegistry.

ADR-0092: Hierarchical Capability Architecture
"""

from __future__ import annotations

import gc

import pytest

pytestmark = pytest.mark.unit


@pytest.mark.unit
class TestHierarchicalSkillRegistryBasic:
    """Tests for HierarchicalSkillRegistry basic functionality."""

    def teardown_method(self) -> None:
        """Force GC to prevent mock accumulation in xdist workers."""
        gc.collect()

    def test_hierarchical_skill_registry_exists(self) -> None:
        """Test HierarchicalSkillRegistry class exists."""
        from mcp_server_langgraph.skills.hierarchical import HierarchicalSkillRegistry

        assert HierarchicalSkillRegistry is not None

    def test_hierarchical_skill_registry_extends_base(self) -> None:
        """Test HierarchicalSkillRegistry extends SkillRegistry."""
        from mcp_server_langgraph.skills.hierarchical import HierarchicalSkillRegistry

        # Should have base registry methods
        registry = HierarchicalSkillRegistry()
        assert hasattr(registry, "register")
        assert hasattr(registry, "get")
        assert hasattr(registry, "list_all")

    def test_has_register_for_scope_method(self) -> None:
        """Test HierarchicalSkillRegistry has register_for_scope method."""
        from mcp_server_langgraph.skills.hierarchical import HierarchicalSkillRegistry

        registry = HierarchicalSkillRegistry()
        assert hasattr(registry, "register_for_scope")
        assert callable(registry.register_for_scope)

    def test_has_get_for_scope_method(self) -> None:
        """Test HierarchicalSkillRegistry has get_for_scope method."""
        from mcp_server_langgraph.skills.hierarchical import HierarchicalSkillRegistry

        registry = HierarchicalSkillRegistry()
        assert hasattr(registry, "get_for_scope")
        assert callable(registry.get_for_scope)

    def test_has_list_for_scope_method(self) -> None:
        """Test HierarchicalSkillRegistry has list_for_scope method."""
        from mcp_server_langgraph.skills.hierarchical import HierarchicalSkillRegistry

        registry = HierarchicalSkillRegistry()
        assert hasattr(registry, "list_for_scope")
        assert callable(registry.list_for_scope)


@pytest.mark.unit
class TestHierarchicalSkillRegistration:
    """Tests for scope-based skill registration."""

    def teardown_method(self) -> None:
        """Force GC to prevent mock accumulation in xdist workers."""
        gc.collect()

    def test_register_skill_at_project_scope(self) -> None:
        """Test registering a skill at PROJECT scope."""
        from mcp_server_langgraph.core.scopes import CapabilityScope
        from mcp_server_langgraph.skills.hierarchical import HierarchicalSkillRegistry
        from mcp_server_langgraph.skills.models import Skill

        registry = HierarchicalSkillRegistry()
        skill = Skill(
            name="project-skill",
            description="A project skill",
            instructions="Do something",
        )

        registry.register_for_scope(skill, CapabilityScope.PROJECT)

        # Should be retrievable at project scope
        result = registry.get_for_scope("project-skill", CapabilityScope.PROJECT)
        assert result is not None
        assert result.name == "project-skill"

    def test_register_skill_at_user_scope(self) -> None:
        """Test registering a skill at USER scope."""
        from mcp_server_langgraph.core.scopes import CapabilityScope
        from mcp_server_langgraph.skills.hierarchical import HierarchicalSkillRegistry
        from mcp_server_langgraph.skills.models import Skill

        registry = HierarchicalSkillRegistry()
        skill = Skill(
            name="user-skill",
            description="A user skill",
            instructions="User action",
        )

        registry.register_for_scope(skill, CapabilityScope.USER)

        result = registry.get_for_scope("user-skill", CapabilityScope.USER)
        assert result is not None

    def test_register_skill_at_session_scope(self) -> None:
        """Test registering a skill at SESSION scope."""
        from mcp_server_langgraph.core.scopes import CapabilityScope
        from mcp_server_langgraph.skills.hierarchical import HierarchicalSkillRegistry
        from mcp_server_langgraph.skills.models import Skill

        registry = HierarchicalSkillRegistry()
        skill = Skill(
            name="session-skill",
            description="A session skill",
            instructions="Session action",
        )

        registry.register_for_scope(skill, CapabilityScope.SESSION)

        result = registry.get_for_scope("session-skill", CapabilityScope.SESSION)
        assert result is not None


@pytest.mark.unit
class TestHierarchicalSkillResolution:
    """Tests for scope-based skill resolution."""

    def teardown_method(self) -> None:
        """Force GC to prevent mock accumulation in xdist workers."""
        gc.collect()

    def test_get_for_scope_resolves_upward(self) -> None:
        """Test get_for_scope resolves from parent scopes."""
        from mcp_server_langgraph.core.scopes import CapabilityScope
        from mcp_server_langgraph.skills.hierarchical import HierarchicalSkillRegistry
        from mcp_server_langgraph.skills.models import Skill

        registry = HierarchicalSkillRegistry()
        skill = Skill(
            name="shared-skill",
            description="Shared skill",
            instructions="Shared action",
        )

        # Register at PROJECT scope
        registry.register_for_scope(skill, CapabilityScope.PROJECT)

        # Should be accessible from TASK scope (child of PROJECT)
        result = registry.get_for_scope("shared-skill", CapabilityScope.TASK)
        assert result is not None
        assert result.name == "shared-skill"

    def test_lower_scope_overrides_higher_scope(self) -> None:
        """Test lower scope skills override higher scope skills."""
        from mcp_server_langgraph.core.scopes import CapabilityScope
        from mcp_server_langgraph.skills.hierarchical import HierarchicalSkillRegistry
        from mcp_server_langgraph.skills.models import Skill

        registry = HierarchicalSkillRegistry()

        # Register at PROJECT scope
        project_skill = Skill(
            name="override-test",
            description="Project version",
            instructions="Project action",
        )
        registry.register_for_scope(project_skill, CapabilityScope.PROJECT)

        # Register at SESSION scope (lower = higher precedence)
        session_skill = Skill(
            name="override-test",
            description="Session version",
            instructions="Session action",
        )
        registry.register_for_scope(session_skill, CapabilityScope.SESSION)

        # When querying from TASK, should get SESSION version
        result = registry.get_for_scope("override-test", CapabilityScope.TASK)
        assert result is not None
        assert result.description == "Session version"

    def test_list_for_scope_merges_parent_scopes(self) -> None:
        """Test list_for_scope merges skills from parent scopes."""
        from mcp_server_langgraph.core.scopes import CapabilityScope
        from mcp_server_langgraph.skills.hierarchical import HierarchicalSkillRegistry
        from mcp_server_langgraph.skills.models import Skill

        registry = HierarchicalSkillRegistry()

        # Register skills at different scopes
        project_skill = Skill(
            name="project-only",
            description="Project skill",
            instructions="Project",
        )
        session_skill = Skill(
            name="session-only",
            description="Session skill",
            instructions="Session",
        )

        registry.register_for_scope(project_skill, CapabilityScope.PROJECT)
        registry.register_for_scope(session_skill, CapabilityScope.SESSION)

        # List at TASK scope should include both
        results = registry.list_for_scope(CapabilityScope.TASK, include_parent_scopes=True)
        names = [s.name for s in results]

        assert "project-only" in names
        assert "session-only" in names


@pytest.mark.unit
class TestHierarchicalSkillBackwardCompatibility:
    """Tests for backward compatibility with flat registry."""

    def teardown_method(self) -> None:
        """Force GC to prevent mock accumulation in xdist workers."""
        gc.collect()

    def test_flat_register_still_works(self) -> None:
        """Test flat register() method still works."""
        from mcp_server_langgraph.skills.hierarchical import HierarchicalSkillRegistry
        from mcp_server_langgraph.skills.models import Skill

        registry = HierarchicalSkillRegistry()
        skill = Skill(
            name="flat-skill",
            description="Flat skill",
            instructions="Flat action",
        )

        # Old-style registration should work
        registry.register(skill)

        # Should be retrievable with flat get()
        result = registry.get("flat-skill")
        assert result is not None

    def test_flat_list_all_includes_scoped(self) -> None:
        """Test list_all() includes scoped skills."""
        from mcp_server_langgraph.core.scopes import CapabilityScope
        from mcp_server_langgraph.skills.hierarchical import HierarchicalSkillRegistry
        from mcp_server_langgraph.skills.models import Skill

        registry = HierarchicalSkillRegistry()
        skill = Skill(
            name="scoped-skill",
            description="Scoped skill",
            instructions="Scoped action",
        )

        registry.register_for_scope(skill, CapabilityScope.PROJECT)

        # list_all should include scoped skills
        all_skills = registry.list_all()
        names = [s.name for s in all_skills]
        assert "scoped-skill" in names
