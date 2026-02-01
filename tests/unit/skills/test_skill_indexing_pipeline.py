"""Unit tests for skill indexing pipeline.

TDD Cycle: RED -> GREEN -> REFACTOR

Tests verify that:
1. SkillsState includes skill_search_tool field
2. init_skills creates SkillSearchTool when feature flag enabled
3. Skills are indexed on install
4. Skills are de-indexed on uninstall
5. Existing skills are indexed during bootstrap

ADR Reference: ADR-0092, ADR-0099
"""

import gc
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

pytestmark = [pytest.mark.unit, pytest.mark.skills]


@pytest.mark.xdist_group(name="test_skill_indexing")
class TestSkillsStateSkillSearchTool:
    """Test SkillsState includes SkillSearchTool."""

    def teardown_method(self) -> None:
        """Force GC to prevent mock accumulation in xdist workers."""
        gc.collect()

    def test_skills_state_has_skill_search_tool_field(self):
        """
        GIVEN: SkillsState dataclass
        WHEN: Creating instance
        THEN: Should have skill_search_tool field (defaults to None)
        """
        from mcp_server_langgraph.bootstrap.skills import SkillsState

        state = SkillsState()
        assert hasattr(state, "skill_search_tool")
        assert state.skill_search_tool is None

    def test_skills_state_accepts_skill_search_tool(self):
        """
        GIVEN: SkillsState dataclass
        WHEN: Creating instance with skill_search_tool
        THEN: Should store the tool
        """
        from mcp_server_langgraph.bootstrap.skills import SkillsState

        mock_tool = MagicMock()
        state = SkillsState(skill_search_tool=mock_tool)
        assert state.skill_search_tool is mock_tool


@pytest.mark.xdist_group(name="test_skill_indexing")
class TestInitSkillsBootstrap:
    """Test init_skills creates SkillSearchTool."""

    def teardown_method(self) -> None:
        """Force GC to prevent mock accumulation in xdist workers."""
        gc.collect()

    @pytest.mark.asyncio
    async def test_init_skills_creates_skill_search_tool_when_enabled(self):
        """
        GIVEN: enable_semantic_skill_search=True
        WHEN: Calling init_skills
        THEN: SkillsState.skill_search_tool should be set
        """
        from mcp_server_langgraph.bootstrap.skills import init_skills

        mock_tool = MagicMock()

        with (
            patch(
                "mcp_server_langgraph.skills.auto_update.is_auto_update_enabled",
                return_value=False,
            ),
            patch(
                "mcp_server_langgraph.bootstrap.skills.create_marketplace_admin_router",
                return_value=(MagicMock(), MagicMock()),
            ),
            patch("mcp_server_langgraph.core.feature_flags.feature_flags") as mock_flags,
            patch(
                "mcp_server_langgraph.skills.adapters.create_skill_search_tool",
                return_value=mock_tool,
            ) as mock_create,
        ):
            mock_flags.enable_semantic_skill_search = True

            mock_settings = MagicMock()
            state = await init_skills(mock_settings)

            mock_create.assert_called_once()
            assert state.skill_search_tool is mock_tool

    @pytest.mark.asyncio
    async def test_init_skills_skips_skill_search_tool_when_disabled(self):
        """
        GIVEN: enable_semantic_skill_search=False
        WHEN: Calling init_skills
        THEN: SkillsState.skill_search_tool should be None
        """
        from mcp_server_langgraph.bootstrap.skills import init_skills

        with (
            patch(
                "mcp_server_langgraph.skills.auto_update.is_auto_update_enabled",
                return_value=False,
            ),
            patch(
                "mcp_server_langgraph.bootstrap.skills.create_marketplace_admin_router",
                return_value=(MagicMock(), MagicMock()),
            ),
            patch("mcp_server_langgraph.core.feature_flags.feature_flags") as mock_flags,
            patch(
                "mcp_server_langgraph.skills.adapters.create_skill_search_tool",
            ) as mock_create,
        ):
            mock_flags.enable_semantic_skill_search = False

            mock_settings = MagicMock()
            state = await init_skills(mock_settings)

            mock_create.assert_not_called()
            assert state.skill_search_tool is None


@pytest.mark.xdist_group(name="test_skill_indexing")
class TestSkillIndexingOnInstall:
    """Test skills are indexed when installed."""

    def teardown_method(self) -> None:
        """Force GC to prevent mock accumulation in xdist workers."""
        gc.collect()

    @pytest.mark.asyncio
    async def test_skill_indexed_after_install(self):
        """
        GIVEN: SkillInstaller with skill_search_tool configured
        WHEN: Installing a skill
        THEN: skill_search_tool.index_skill should be called
        """
        from mcp_server_langgraph.skills.installer import SkillInstaller

        mock_tool = AsyncMock(return_value=None)
        mock_tool.index_skill = AsyncMock(return_value=None)

        installer = SkillInstaller(skill_search_tool=mock_tool)

        with patch.object(installer, "_fetch_skill_from_marketplace", new_callable=AsyncMock) as mock_fetch:
            # Mock skill data with metadata
            mock_fetch.return_value = {
                "content": "# Test Skill\nInstructions here.",
                "description": "A test skill",
                "tags": ["test"],
                "dependencies": [],
            }

            await installer.install("test-skill", source="anthropic")

            # Verify index_skill was called
            mock_tool.index_skill.assert_called_once()

    @pytest.mark.asyncio
    async def test_skill_not_indexed_when_tool_unavailable(self):
        """
        GIVEN: SkillInstaller without skill_search_tool
        WHEN: Installing a skill
        THEN: Should still succeed (no indexing error)
        """
        from mcp_server_langgraph.skills.installer import SkillInstaller

        installer = SkillInstaller(skill_search_tool=None)

        with patch.object(installer, "_fetch_skill_from_marketplace", new_callable=AsyncMock) as mock_fetch:
            mock_fetch.return_value = {
                "content": "# Test Skill",
                "description": "A test skill",
                "dependencies": [],
            }

            # Should not raise even without search tool
            result = await installer.install("test-skill", source="anthropic")
            assert result is not None
            assert result.success is True


@pytest.mark.xdist_group(name="test_skill_indexing")
class TestSkillDeindexingOnUninstall:
    """Test skills are de-indexed when uninstalled."""

    def teardown_method(self) -> None:
        """Force GC to prevent mock accumulation in xdist workers."""
        gc.collect()

    @pytest.mark.asyncio
    async def test_skill_deindexed_after_uninstall(self, tmp_path):
        """
        GIVEN: SkillInstaller with skill_search_tool configured
        WHEN: Uninstalling a skill
        THEN: skill_search_tool.remove_skill should be called
        """
        from mcp_server_langgraph.skills.installer import SkillInstaller

        mock_tool = AsyncMock(return_value=None)
        mock_tool.remove_skill = AsyncMock(return_value=None)

        installer = SkillInstaller(
            install_path=tmp_path,
            skill_search_tool=mock_tool,
        )

        # Create a skill directory to uninstall
        skill_dir = tmp_path / "test-skill"
        skill_dir.mkdir()
        (skill_dir / "SKILL.md").write_text("# Test Skill")

        await installer.uninstall("test-skill")

        # Verify remove_skill was called
        mock_tool.remove_skill.assert_called_once_with("test-skill")

    @pytest.mark.asyncio
    async def test_skill_not_deindexed_when_tool_unavailable(self, tmp_path):
        """
        GIVEN: SkillInstaller without skill_search_tool
        WHEN: Uninstalling a skill
        THEN: Should still succeed (no deindexing error)
        """
        from mcp_server_langgraph.skills.installer import SkillInstaller

        installer = SkillInstaller(
            install_path=tmp_path,
            skill_search_tool=None,
        )

        # Create a skill directory to uninstall
        skill_dir = tmp_path / "test-skill"
        skill_dir.mkdir()
        (skill_dir / "SKILL.md").write_text("# Test Skill")

        # Should not raise even without search tool
        result = await installer.uninstall("test-skill")
        assert result is True


@pytest.mark.xdist_group(name="test_skill_indexing")
class TestExistingSkillsIndexing:
    """Test existing skills are indexed during bootstrap."""

    def teardown_method(self) -> None:
        """Force GC to prevent mock accumulation in xdist workers."""
        gc.collect()

    @pytest.mark.asyncio
    async def test_skill_search_tool_passed_to_installer(self):
        """
        GIVEN: Semantic search enabled with skill_search_tool created
        WHEN: Calling init_skills with auto-update enabled
        THEN: SkillInstaller should receive skill_search_tool
        """
        from mcp_server_langgraph.bootstrap.skills import init_skills

        mock_tool = MagicMock()

        mock_installer_instance = MagicMock()
        mock_installer_instance.list_installed.return_value = []
        mock_installer_class = MagicMock(return_value=mock_installer_instance)

        mock_scheduler = MagicMock()
        mock_scheduler.start = AsyncMock(return_value=None)

        with (
            patch(
                "mcp_server_langgraph.skills.auto_update.is_auto_update_enabled",
                return_value=True,  # Enable auto-update to trigger SkillInstaller creation
            ),
            patch(
                "mcp_server_langgraph.skills.auto_update.AutoUpdateScheduler",
                return_value=mock_scheduler,
            ),
            patch(
                "mcp_server_langgraph.bootstrap.skills.create_marketplace_admin_router",
                return_value=(MagicMock(), MagicMock()),
            ),
            patch("mcp_server_langgraph.core.feature_flags.feature_flags") as mock_flags,
            patch(
                "mcp_server_langgraph.skills.adapters.create_skill_search_tool",
                return_value=mock_tool,
            ),
            patch(
                "mcp_server_langgraph.skills.installer.SkillInstaller",
                mock_installer_class,
            ),
        ):
            mock_flags.enable_semantic_skill_search = True

            mock_settings = MagicMock()
            await init_skills(mock_settings)

            # Verify SkillInstaller was called with skill_search_tool
            mock_installer_class.assert_called_once_with(skill_search_tool=mock_tool)
