"""
Unit tests for Skill Discovery

Tests progressive skill discovery functionality including
searching, filtering, and loading skills on-demand.

TDD: RED phase - these tests define expected behavior before implementation.
"""

import gc
import textwrap

import pytest

pytestmark = [pytest.mark.unit, pytest.mark.skills]


@pytest.mark.unit
class TestSkillDiscoveryBasic:
    """Test suite for basic skill discovery"""

    def teardown_method(self) -> None:
        """Force GC to prevent mock accumulation in xdist workers"""
        gc.collect()

    def test_skill_discovery_exists(self):
        """GIVEN the skills module
        WHEN importing SkillDiscovery
        THEN it should be available
        """
        from mcp_server_langgraph.skills.discovery import SkillDiscovery

        discovery = SkillDiscovery()
        assert discovery is not None

    def test_discovery_has_registry(self):
        """GIVEN a SkillDiscovery instance
        WHEN checking the registry
        THEN it should have a SkillRegistry
        """
        from mcp_server_langgraph.skills.discovery import SkillDiscovery
        from mcp_server_langgraph.skills.registry import SkillRegistry

        discovery = SkillDiscovery()

        assert hasattr(discovery, "registry")
        assert isinstance(discovery.registry, SkillRegistry)

    def test_discovery_list_available(self):
        """GIVEN a SkillDiscovery with loaded skills
        WHEN listing available skills
        THEN all registered skills should be returned
        """
        from mcp_server_langgraph.skills.discovery import SkillDiscovery
        from mcp_server_langgraph.skills.models import Skill

        discovery = SkillDiscovery()
        discovery.registry.register(Skill(name="skill-1", description="First"))
        discovery.registry.register(Skill(name="skill-2", description="Second"))

        available = discovery.list_available()

        assert len(available) == 2


@pytest.mark.unit
class TestSkillDiscoveryProgressive:
    """Test suite for progressive skill disclosure"""

    def teardown_method(self) -> None:
        """Force GC to prevent mock accumulation in xdist workers"""
        gc.collect()

    def test_get_skill_summary(self):
        """GIVEN registered skills
        WHEN getting skill summaries
        THEN minimal info should be returned
        """
        from mcp_server_langgraph.skills.discovery import SkillDiscovery
        from mcp_server_langgraph.skills.models import Skill

        discovery = SkillDiscovery()
        discovery.registry.register(
            Skill(
                name="web-research",
                description="Research topics using web search",
                instructions="Detailed instructions here...",
            )
        )

        summaries = discovery.get_skill_summaries()

        assert len(summaries) == 1
        summary = summaries[0]
        assert summary["name"] == "web-research"
        assert summary["description"] == "Research topics using web search"
        # Instructions should NOT be in summary (progressive disclosure)
        assert "instructions" not in summary

    def test_get_full_skill(self):
        """GIVEN a registered skill
        WHEN getting full skill details
        THEN complete skill information should be returned
        """
        from mcp_server_langgraph.skills.discovery import SkillDiscovery
        from mcp_server_langgraph.skills.models import Skill

        discovery = SkillDiscovery()
        discovery.registry.register(
            Skill(
                name="web-research",
                description="Research topics",
                instructions="Use web search to find information...",
            )
        )

        skill = discovery.get_skill("web-research")

        assert skill is not None
        assert skill.name == "web-research"
        assert "Use web search" in skill.instructions

    def test_get_skill_not_found_returns_none(self):
        """GIVEN a SkillDiscovery
        WHEN getting a nonexistent skill
        THEN None should be returned
        """
        from mcp_server_langgraph.skills.discovery import SkillDiscovery

        discovery = SkillDiscovery()

        assert discovery.get_skill("nonexistent") is None


@pytest.mark.unit
class TestSkillDiscoveryLoading:
    """Test suite for skill loading functionality"""

    def teardown_method(self) -> None:
        """Force GC to prevent mock accumulation in xdist workers"""
        gc.collect()

    def test_load_skills_from_directory(self, tmp_path):
        """GIVEN a directory with SKILL.md files
        WHEN loading skills from directory
        THEN skills should be discovered and registered
        """
        from mcp_server_langgraph.skills.discovery import SkillDiscovery

        # Create skill directories
        skill_dir1 = tmp_path / "skill-1"
        skill_dir1.mkdir()
        (skill_dir1 / "SKILL.md").write_text(
            textwrap.dedent("""
            ---
            name: skill-1
            description: First skill
            ---
            # First Skill
            """)
        )

        skill_dir2 = tmp_path / "skill-2"
        skill_dir2.mkdir()
        (skill_dir2 / "SKILL.md").write_text(
            textwrap.dedent("""
            ---
            name: skill-2
            description: Second skill
            ---
            # Second Skill
            """)
        )

        discovery = SkillDiscovery()
        count = discovery.load_from_directory(tmp_path)

        assert count == 2
        assert discovery.get_skill("skill-1") is not None
        assert discovery.get_skill("skill-2") is not None

    def test_load_skills_ignores_invalid(self, tmp_path):
        """GIVEN a directory with valid and invalid SKILL.md files
        WHEN loading skills
        THEN invalid skills should be skipped
        """
        from mcp_server_langgraph.skills.discovery import SkillDiscovery

        # Valid skill
        skill_dir1 = tmp_path / "valid-skill"
        skill_dir1.mkdir()
        (skill_dir1 / "SKILL.md").write_text(
            textwrap.dedent("""
            ---
            name: valid-skill
            description: Valid skill
            ---
            # Valid Skill
            """)
        )

        # Invalid skill (missing description)
        skill_dir2 = tmp_path / "invalid-skill"
        skill_dir2.mkdir()
        (skill_dir2 / "SKILL.md").write_text(
            textwrap.dedent("""
            ---
            name: invalid-skill
            ---
            # Invalid Skill
            """)
        )

        discovery = SkillDiscovery()
        count = discovery.load_from_directory(tmp_path)

        assert count == 1
        assert discovery.get_skill("valid-skill") is not None
        assert discovery.get_skill("invalid-skill") is None


@pytest.mark.unit
class TestSkillDiscoverySearch:
    """Test suite for skill search functionality"""

    def teardown_method(self) -> None:
        """Force GC to prevent mock accumulation in xdist workers"""
        gc.collect()

    def test_search_skills_by_query(self):
        """GIVEN registered skills
        WHEN searching by query
        THEN matching skills should be returned
        """
        from mcp_server_langgraph.skills.discovery import SkillDiscovery
        from mcp_server_langgraph.skills.models import Skill

        discovery = SkillDiscovery()
        discovery.registry.register(Skill(name="web-research", description="Research using web search"))
        discovery.registry.register(Skill(name="code-analysis", description="Analyze code"))
        discovery.registry.register(Skill(name="file-search", description="Search files"))

        results = discovery.search("search")

        assert len(results) == 2
        names = [s.name for s in results]
        assert "web-research" in names
        assert "file-search" in names

    def test_search_returns_summaries(self):
        """GIVEN registered skills
        WHEN searching with summary mode
        THEN summaries should be returned instead of full skills
        """
        from mcp_server_langgraph.skills.discovery import SkillDiscovery
        from mcp_server_langgraph.skills.models import Skill

        discovery = SkillDiscovery()
        discovery.registry.register(
            Skill(
                name="web-research",
                description="Research topics",
                instructions="Long instructions...",
            )
        )

        results = discovery.search("research", summary_only=True)

        assert len(results) == 1
        assert isinstance(results[0], dict)
        assert "instructions" not in results[0]
