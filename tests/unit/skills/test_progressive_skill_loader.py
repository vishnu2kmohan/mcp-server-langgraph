"""Tests for ProgressiveSkillLoader.

TDD: These tests define the contract for the ProgressiveSkillLoader that
implements 4-stage progressive skill loading with semantic relevance.

ADR-0092: Hierarchical Capability Architecture
"""

from __future__ import annotations

import gc

import pytest

pytestmark = pytest.mark.unit


@pytest.mark.unit
@pytest.mark.xdist_group(name="progressive_skill_loader_basic")
class TestProgressiveSkillLoaderBasic:
    """Tests for ProgressiveSkillLoader basic functionality."""

    def teardown_method(self) -> None:
        """Force GC to prevent mock accumulation in xdist workers."""
        gc.collect()

    def test_progressive_skill_loader_exists(self) -> None:
        """Test ProgressiveSkillLoader class exists."""
        from mcp_server_langgraph.skills.progressive_loader import (
            ProgressiveSkillLoader,
        )

        assert ProgressiveSkillLoader is not None

    def test_progressive_skill_loader_accepts_registry(self) -> None:
        """Test ProgressiveSkillLoader accepts skill registry."""
        from mcp_server_langgraph.skills.hierarchical import HierarchicalSkillRegistry
        from mcp_server_langgraph.skills.progressive_loader import (
            ProgressiveSkillLoader,
        )

        registry = HierarchicalSkillRegistry()
        loader = ProgressiveSkillLoader(skill_registry=registry)

        assert loader.skill_registry is registry

    def test_progressive_skill_loader_has_load_for_task_method(self) -> None:
        """Test ProgressiveSkillLoader has load_for_task method."""
        from mcp_server_langgraph.skills.progressive_loader import (
            ProgressiveSkillLoader,
        )

        loader = ProgressiveSkillLoader()
        assert hasattr(loader, "load_for_task")


@pytest.mark.unit
@pytest.mark.xdist_group(name="progressive_skill_loader_stages")
class TestProgressiveSkillLoaderStages:
    """Tests for ProgressiveSkillLoader 4-stage loading."""

    def teardown_method(self) -> None:
        """Force GC to prevent mock accumulation in xdist workers."""
        gc.collect()

    @pytest.mark.asyncio
    async def test_stage1_loads_explicitly_requested_skills(self) -> None:
        """Test Stage 1: Load explicitly requested skills from router."""
        from mcp_server_langgraph.skills.models import Skill
        from mcp_server_langgraph.core.scopes import CapabilityScope
        from mcp_server_langgraph.skills.hierarchical import HierarchicalSkillRegistry
        from mcp_server_langgraph.skills.progressive_loader import (
            ProgressiveSkillLoader,
        )

        registry = HierarchicalSkillRegistry()
        skill = Skill(name="code-review", description="Review code")
        registry.register_for_scope(skill, CapabilityScope.PROJECT)

        loader = ProgressiveSkillLoader(skill_registry=registry)
        result = await loader.load_for_task(
            task_description="Review the code",
            scope=CapabilityScope.TASK,
            requested_skills=["code-review"],
        )

        assert len(result) >= 1
        assert any(s.name == "code-review" for s in result)

    @pytest.mark.asyncio
    async def test_stage2_loads_scope_default_skills(self) -> None:
        """Test Stage 2: Load scope default skills with 'default' tag."""
        from mcp_server_langgraph.skills.models import Skill
        from mcp_server_langgraph.core.scopes import CapabilityScope
        from mcp_server_langgraph.skills.hierarchical import HierarchicalSkillRegistry
        from mcp_server_langgraph.skills.progressive_loader import (
            ProgressiveSkillLoader,
        )

        registry = HierarchicalSkillRegistry()
        # Register a default skill at project scope (using 'default' tag)
        default_skill = Skill(
            name="project-default",
            description="Default project skill",
            tags=["default"],
        )
        registry.register_for_scope(default_skill, CapabilityScope.PROJECT)

        loader = ProgressiveSkillLoader(skill_registry=registry)
        result = await loader.load_for_task(
            task_description="Do something",
            scope=CapabilityScope.TASK,
            requested_skills=[],
            include_defaults=True,
        )

        assert any(s.name == "project-default" for s in result)

    @pytest.mark.asyncio
    async def test_stage3_respects_max_skills_limit(self) -> None:
        """Test Stage 3: Progressive loading respects max_skills limit."""
        from mcp_server_langgraph.skills.models import Skill
        from mcp_server_langgraph.core.scopes import CapabilityScope
        from mcp_server_langgraph.skills.hierarchical import HierarchicalSkillRegistry
        from mcp_server_langgraph.skills.progressive_loader import (
            ProgressiveSkillLoader,
        )

        registry = HierarchicalSkillRegistry()
        # Register many skills
        for i in range(10):
            skill = Skill(name=f"skill-{i}", description=f"Skill {i}")
            registry.register_for_scope(skill, CapabilityScope.PROJECT)

        loader = ProgressiveSkillLoader(skill_registry=registry)
        result = await loader.load_for_task(
            task_description="Do many things",
            scope=CapabilityScope.TASK,
            requested_skills=[f"skill-{i}" for i in range(10)],
            max_skills=5,
        )

        assert len(result) <= 5

    @pytest.mark.asyncio
    async def test_returns_empty_for_no_matching_skills(self) -> None:
        """Test returns empty list when no skills match."""
        from mcp_server_langgraph.core.scopes import CapabilityScope
        from mcp_server_langgraph.skills.progressive_loader import (
            ProgressiveSkillLoader,
        )

        loader = ProgressiveSkillLoader()
        result = await loader.load_for_task(
            task_description="Unknown task",
            scope=CapabilityScope.TASK,
            requested_skills=["nonexistent-skill"],
        )

        assert result == []


@pytest.mark.unit
@pytest.mark.xdist_group(name="progressive_skill_loader_priority")
class TestProgressiveSkillLoaderPriority:
    """Tests for ProgressiveSkillLoader skill priority."""

    def teardown_method(self) -> None:
        """Force GC to prevent mock accumulation in xdist workers."""
        gc.collect()

    @pytest.mark.asyncio
    async def test_requested_skills_have_highest_priority(self) -> None:
        """Test explicitly requested skills have highest priority."""
        from mcp_server_langgraph.skills.models import Skill
        from mcp_server_langgraph.core.scopes import CapabilityScope
        from mcp_server_langgraph.skills.hierarchical import HierarchicalSkillRegistry
        from mcp_server_langgraph.skills.progressive_loader import (
            ProgressiveSkillLoader,
        )

        registry = HierarchicalSkillRegistry()
        requested = Skill(name="requested-skill", description="Requested")
        default_skill = Skill(name="default-skill", description="Default", tags=["default"])
        registry.register_for_scope(requested, CapabilityScope.PROJECT)
        registry.register_for_scope(default_skill, CapabilityScope.PROJECT)

        loader = ProgressiveSkillLoader(skill_registry=registry)
        result = await loader.load_for_task(
            task_description="Task",
            scope=CapabilityScope.TASK,
            requested_skills=["requested-skill"],
            include_defaults=True,
            max_skills=1,
        )

        # Requested skill should be first
        assert len(result) == 1
        assert result[0].name == "requested-skill"

    @pytest.mark.asyncio
    async def test_no_duplicate_skills_in_result(self) -> None:
        """Test result contains no duplicate skills."""
        from mcp_server_langgraph.skills.models import Skill
        from mcp_server_langgraph.core.scopes import CapabilityScope
        from mcp_server_langgraph.skills.hierarchical import HierarchicalSkillRegistry
        from mcp_server_langgraph.skills.progressive_loader import (
            ProgressiveSkillLoader,
        )

        registry = HierarchicalSkillRegistry()
        skill = Skill(name="unique-skill", description="Unique", tags=["default"])
        registry.register_for_scope(skill, CapabilityScope.PROJECT)

        loader = ProgressiveSkillLoader(skill_registry=registry)
        result = await loader.load_for_task(
            task_description="Task",
            scope=CapabilityScope.TASK,
            requested_skills=["unique-skill"],  # Also in defaults
            include_defaults=True,
        )

        # Should only appear once
        names = [s.name for s in result]
        assert names.count("unique-skill") == 1


@pytest.mark.unit
@pytest.mark.xdist_group(name="progressive_skill_loader_scope")
class TestProgressiveSkillLoaderScope:
    """Tests for ProgressiveSkillLoader scope resolution."""

    def teardown_method(self) -> None:
        """Force GC to prevent mock accumulation in xdist workers."""
        gc.collect()

    @pytest.mark.asyncio
    async def test_resolves_skills_from_parent_scopes(self) -> None:
        """Test skills are resolved from parent scopes."""
        from mcp_server_langgraph.skills.models import Skill
        from mcp_server_langgraph.core.scopes import CapabilityScope
        from mcp_server_langgraph.skills.hierarchical import HierarchicalSkillRegistry
        from mcp_server_langgraph.skills.progressive_loader import (
            ProgressiveSkillLoader,
        )

        registry = HierarchicalSkillRegistry()
        project_skill = Skill(name="project-skill", description="From project")
        registry.register_for_scope(project_skill, CapabilityScope.PROJECT)

        loader = ProgressiveSkillLoader(skill_registry=registry)
        result = await loader.load_for_task(
            task_description="Task",
            scope=CapabilityScope.TASK,  # Lower scope than PROJECT
            requested_skills=["project-skill"],
        )

        assert any(s.name == "project-skill" for s in result)

    @pytest.mark.asyncio
    async def test_respects_scope_hierarchy(self) -> None:
        """Test loader respects scope hierarchy for skill resolution."""
        from mcp_server_langgraph.skills.models import Skill
        from mcp_server_langgraph.core.scopes import CapabilityScope
        from mcp_server_langgraph.skills.hierarchical import HierarchicalSkillRegistry
        from mcp_server_langgraph.skills.progressive_loader import (
            ProgressiveSkillLoader,
        )

        registry = HierarchicalSkillRegistry()
        # Same skill name at different scopes
        task_skill = Skill(name="override-skill", description="Task level")
        project_skill = Skill(name="override-skill", description="Project level")

        registry.register_for_scope(task_skill, CapabilityScope.TASK)
        registry.register_for_scope(project_skill, CapabilityScope.PROJECT)

        loader = ProgressiveSkillLoader(skill_registry=registry)
        result = await loader.load_for_task(
            task_description="Task",
            scope=CapabilityScope.TASK,
            requested_skills=["override-skill"],
        )

        # Task-level skill should override project-level
        assert len(result) == 1
        assert result[0].description == "Task level"


@pytest.mark.unit
@pytest.mark.xdist_group(name="loaded_skills_result")
class TestLoadedSkillsResult:
    """Tests for LoadedSkills result dataclass."""

    def teardown_method(self) -> None:
        """Force GC to prevent mock accumulation in xdist workers."""
        gc.collect()

    def test_loaded_skills_result_exists(self) -> None:
        """Test LoadedSkills dataclass exists."""
        from mcp_server_langgraph.skills.progressive_loader import LoadedSkills

        assert LoadedSkills is not None

    def test_loaded_skills_has_skills_field(self) -> None:
        """Test LoadedSkills has skills field."""
        from mcp_server_langgraph.skills.models import Skill
        from mcp_server_langgraph.skills.progressive_loader import LoadedSkills

        skill = Skill(name="test", description="Test")
        loaded = LoadedSkills(skills=[skill], stages_used=["stage1"])

        assert loaded.skills == [skill]

    def test_loaded_skills_has_stages_used_field(self) -> None:
        """Test LoadedSkills tracks which stages were used."""
        from mcp_server_langgraph.skills.progressive_loader import LoadedSkills

        loaded = LoadedSkills(skills=[], stages_used=["stage1", "stage2"])

        assert "stage1" in loaded.stages_used
        assert "stage2" in loaded.stages_used
