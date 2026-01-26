"""
Unit tests for Skill Registry

Tests the local skill registry for registering, discovering,
and managing skills.

TDD: RED phase - these tests define expected behavior before implementation.
"""

import gc

import pytest

pytestmark = [pytest.mark.unit, pytest.mark.skills]


@pytest.mark.unit
@pytest.mark.xdist_group(name="test_skill_registry_basic")
class TestSkillRegistryBasic:
    """Test suite for basic registry functionality"""

    def teardown_method(self) -> None:
        """Force GC to prevent mock accumulation in xdist workers"""
        gc.collect()

    def test_skill_registry_exists(self):
        """GIVEN the skills module
        WHEN importing SkillRegistry
        THEN it should be available
        """
        from mcp_server_langgraph.skills.registry import SkillRegistry

        registry = SkillRegistry()
        assert registry is not None

    def test_register_skill_adds_to_registry(self):
        """GIVEN a SkillRegistry
        WHEN registering a skill
        THEN the skill should be stored
        """
        from mcp_server_langgraph.skills.models import Skill
        from mcp_server_langgraph.skills.registry import SkillRegistry

        registry = SkillRegistry()
        skill = Skill(name="test-skill", description="A test skill")

        registry.register(skill)

        assert registry.get("test-skill") is not None

    def test_get_skill_by_name(self):
        """GIVEN a registry with skills
        WHEN getting by name
        THEN correct skill should be returned
        """
        from mcp_server_langgraph.skills.models import Skill
        from mcp_server_langgraph.skills.registry import SkillRegistry

        registry = SkillRegistry()
        skill = Skill(name="my-skill", description="My skill")
        registry.register(skill)

        retrieved = registry.get("my-skill")

        assert retrieved is not None
        assert retrieved.name == "my-skill"

    def test_get_nonexistent_skill_returns_none(self):
        """GIVEN a registry
        WHEN getting a nonexistent skill
        THEN None should be returned
        """
        from mcp_server_langgraph.skills.registry import SkillRegistry

        registry = SkillRegistry()

        assert registry.get("nonexistent") is None

    def test_list_all_skills(self):
        """GIVEN a registry with skills
        WHEN listing all skills
        THEN all skills should be returned
        """
        from mcp_server_langgraph.skills.models import Skill
        from mcp_server_langgraph.skills.registry import SkillRegistry

        registry = SkillRegistry()
        registry.register(Skill(name="skill-1", description="First"))
        registry.register(Skill(name="skill-2", description="Second"))

        all_skills = registry.list_all()

        assert len(all_skills) == 2
        names = [s.name for s in all_skills]
        assert "skill-1" in names
        assert "skill-2" in names


@pytest.mark.unit
@pytest.mark.xdist_group(name="test_skill_registry_unregister")
class TestSkillRegistryUnregister:
    """Test suite for skill unregistration"""

    def teardown_method(self) -> None:
        """Force GC to prevent mock accumulation in xdist workers"""
        gc.collect()

    def test_unregister_skill_removes_from_registry(self):
        """GIVEN a registry with a skill
        WHEN unregistering the skill
        THEN it should be removed
        """
        from mcp_server_langgraph.skills.models import Skill
        from mcp_server_langgraph.skills.registry import SkillRegistry

        registry = SkillRegistry()
        skill = Skill(name="removable", description="Will be removed")
        registry.register(skill)

        registry.unregister("removable")

        assert registry.get("removable") is None

    def test_unregister_nonexistent_no_error(self):
        """GIVEN a registry
        WHEN unregistering a nonexistent skill
        THEN no error should be raised
        """
        from mcp_server_langgraph.skills.registry import SkillRegistry

        registry = SkillRegistry()

        # Should not raise
        registry.unregister("nonexistent")


@pytest.mark.unit
@pytest.mark.xdist_group(name="test_skill_registry_search")
class TestSkillRegistrySearch:
    """Test suite for skill search functionality"""

    def teardown_method(self) -> None:
        """Force GC to prevent mock accumulation in xdist workers"""
        gc.collect()

    def test_search_by_name(self):
        """GIVEN a registry with skills
        WHEN searching by name pattern
        THEN matching skills should be returned
        """
        from mcp_server_langgraph.skills.models import Skill
        from mcp_server_langgraph.skills.registry import SkillRegistry

        registry = SkillRegistry()
        registry.register(Skill(name="web-search", description="Web search"))
        registry.register(Skill(name="code-search", description="Code search"))
        registry.register(Skill(name="document-analysis", description="Docs"))

        results = registry.search("search")

        assert len(results) == 2
        names = [s.name for s in results]
        assert "web-search" in names
        assert "code-search" in names

    def test_search_by_description(self):
        """GIVEN a registry with skills
        WHEN searching by description keyword
        THEN matching skills should be returned
        """
        from mcp_server_langgraph.skills.models import Skill
        from mcp_server_langgraph.skills.registry import SkillRegistry

        registry = SkillRegistry()
        registry.register(Skill(name="skill-1", description="Analyze documents"))
        registry.register(Skill(name="skill-2", description="Search the web"))

        results = registry.search("analyze")

        assert len(results) == 1
        assert results[0].name == "skill-1"

    def test_search_by_tags(self):
        """GIVEN a registry with tagged skills
        WHEN searching by tag
        THEN matching skills should be returned
        """
        from mcp_server_langgraph.skills.models import Skill
        from mcp_server_langgraph.skills.registry import SkillRegistry

        registry = SkillRegistry()
        registry.register(
            Skill(
                name="research-skill",
                description="Research",
                tags=["research", "web"],
            )
        )
        registry.register(
            Skill(
                name="code-skill",
                description="Code",
                tags=["development", "automation"],
            )
        )

        results = registry.search("research")

        assert len(results) == 1
        assert results[0].name == "research-skill"

    def test_search_empty_query_returns_all(self):
        """GIVEN a registry with skills
        WHEN searching with empty query
        THEN all skills should be returned
        """
        from mcp_server_langgraph.skills.models import Skill
        from mcp_server_langgraph.skills.registry import SkillRegistry

        registry = SkillRegistry()
        registry.register(Skill(name="skill-1", description="First"))
        registry.register(Skill(name="skill-2", description="Second"))

        results = registry.search("")

        assert len(results) == 2


@pytest.mark.unit
@pytest.mark.xdist_group(name="test_skill_registry_source")
class TestSkillRegistrySource:
    """Test suite for skill source tracking"""

    def teardown_method(self) -> None:
        """Force GC to prevent mock accumulation in xdist workers"""
        gc.collect()

    def test_list_by_source(self):
        """GIVEN skills from different sources
        WHEN listing by source
        THEN only matching source skills returned
        """
        from mcp_server_langgraph.skills.models import Skill
        from mcp_server_langgraph.skills.registry import SkillRegistry

        registry = SkillRegistry()
        registry.register(
            Skill(
                name="anthropic-skill",
                description="From Anthropic",
                source="https://github.com/anthropics/skills",
            )
        )
        registry.register(
            Skill(
                name="local-skill",
                description="Local skill",
                source="local",
            )
        )

        anthropic_skills = registry.list_by_source("anthropics/skills")

        assert len(anthropic_skills) == 1
        assert anthropic_skills[0].name == "anthropic-skill"

    def test_list_local_skills(self):
        """GIVEN a mix of local and remote skills
        WHEN listing local skills
        THEN only local skills returned
        """
        from mcp_server_langgraph.skills.models import Skill
        from mcp_server_langgraph.skills.registry import SkillRegistry

        registry = SkillRegistry()
        registry.register(Skill(name="local-1", description="Local", source="local"))
        registry.register(
            Skill(
                name="remote-1",
                description="Remote",
                source="https://github.com/example/skills",
            )
        )

        local_skills = registry.list_by_source("local")

        assert len(local_skills) == 1
        assert local_skills[0].name == "local-1"


@pytest.mark.unit
@pytest.mark.xdist_group(name="test_skill_registry_clear")
class TestSkillRegistryClear:
    """Test suite for clearing the registry"""

    def teardown_method(self) -> None:
        """Force GC to prevent mock accumulation in xdist workers"""
        gc.collect()

    def test_clear_removes_all_skills(self):
        """GIVEN a registry with skills
        WHEN clearing the registry
        THEN all skills should be removed
        """
        from mcp_server_langgraph.skills.models import Skill
        from mcp_server_langgraph.skills.registry import SkillRegistry

        registry = SkillRegistry()
        registry.register(Skill(name="skill-1", description="First"))
        registry.register(Skill(name="skill-2", description="Second"))

        registry.clear()

        assert len(registry.list_all()) == 0
