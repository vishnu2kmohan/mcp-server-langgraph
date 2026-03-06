"""
Unit tests for Skill Installer

Tests the skill installation from marketplaces with real uv commands
for dependency installation.

TDD: RED phase - tests define expected behavior.
"""

from __future__ import annotations

import asyncio
import gc
import textwrap
from pathlib import Path
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from mcp_server_langgraph.skills.installer import (
    SkillInstaller,
)

pytestmark = [pytest.mark.unit, pytest.mark.skills]


class TestSkillInstallerBasic:
    """Test suite for basic skill installer functionality."""

    def teardown_method(self) -> None:
        """Force GC to prevent mock accumulation in xdist workers."""
        gc.collect()

    def test_skill_installer_exists(self) -> None:
        """GIVEN the skills module
        WHEN importing SkillInstaller
        THEN it should be available
        """
        installer = SkillInstaller()
        assert installer is not None

    def test_installer_has_default_path(self) -> None:
        """GIVEN a SkillInstaller with no path
        WHEN checking install_path
        THEN it should use the default path
        """
        installer = SkillInstaller()
        assert installer.install_path == Path.home() / ".mcp-langgraph" / "skills"

    def test_installer_accepts_custom_path(self, tmp_path: Path) -> None:
        """GIVEN a custom install path
        WHEN creating SkillInstaller
        THEN it should use the custom path
        """
        installer = SkillInstaller(install_path=tmp_path / "custom-skills")
        assert installer.install_path == tmp_path / "custom-skills"


class TestSkillInstallerInstall:
    """Test suite for skill installation."""

    def teardown_method(self) -> None:
        """Force GC to prevent mock accumulation in xdist workers."""
        gc.collect()

    @pytest.mark.asyncio
    async def test_install_creates_skill_directory(self, tmp_path: Path) -> None:
        """GIVEN a skill to install
        WHEN installing the skill
        THEN the skill directory should be created
        """
        installer = SkillInstaller(install_path=tmp_path)

        # Mock marketplace client to return skill metadata
        with patch.object(
            installer,
            "_fetch_skill_from_marketplace",
            new_callable=AsyncMock,
            return_value={
                "name": "test-skill",
                "description": "A test skill",
                "content": "# Test Skill\n\nInstructions here.",
            },
        ):
            result = await installer.install("test-skill", source="anthropic")

        assert result.success is True
        assert (tmp_path / "test-skill").exists()

    @pytest.mark.asyncio
    async def test_install_creates_skill_md_file(self, tmp_path: Path) -> None:
        """GIVEN a skill with content
        WHEN installing the skill
        THEN SKILL.md file should be created
        """
        installer = SkillInstaller(install_path=tmp_path)

        skill_content = textwrap.dedent("""
        ---
        name: web-research
        description: Research topics on the web
        dependencies:
          - httpx>=0.25.0
        ---

        # Web Research Skill

        Research topics using web search.
        """).strip()

        with patch.object(
            installer,
            "_fetch_skill_from_marketplace",
            new_callable=AsyncMock,
            return_value={
                "name": "web-research",
                "description": "Research topics on the web",
                "content": skill_content,
            },
        ):
            result = await installer.install("web-research", source="anthropic")

        assert result.success is True
        skill_md = tmp_path / "web-research" / "SKILL.md"
        assert skill_md.exists()
        assert "Research topics" in skill_md.read_text()

    @pytest.mark.asyncio
    async def test_install_returns_installed_path(self, tmp_path: Path) -> None:
        """GIVEN a successful installation
        WHEN checking the result
        THEN installed_path should point to the skill directory
        """
        installer = SkillInstaller(install_path=tmp_path)

        with patch.object(
            installer,
            "_fetch_skill_from_marketplace",
            new_callable=AsyncMock,
            return_value={"name": "my-skill", "content": "# Skill"},
        ):
            result = await installer.install("my-skill")

        assert result.installed_path == str(tmp_path / "my-skill")

    @pytest.mark.asyncio
    async def test_install_failure_returns_error(self, tmp_path: Path) -> None:
        """GIVEN a marketplace error
        WHEN installing a skill
        THEN result should indicate failure with error message
        """
        installer = SkillInstaller(install_path=tmp_path)

        with patch.object(
            installer,
            "_fetch_skill_from_marketplace",
            new_callable=AsyncMock,
            side_effect=Exception("Marketplace unavailable"),
        ):
            result = await installer.install("nonexistent-skill")

        assert result.success is False
        assert "Marketplace unavailable" in result.error


class TestSkillInstallerDependencies:
    """Test suite for dependency resolution and installation."""

    def teardown_method(self) -> None:
        """Force GC to prevent mock accumulation in xdist workers."""
        gc.collect()

    @pytest.mark.asyncio
    async def test_resolve_dependencies_returns_packages(self) -> None:
        """GIVEN skill metadata with dependencies
        WHEN resolving dependencies
        THEN packages list should be populated
        """
        installer = SkillInstaller()
        metadata = {
            "dependencies": ["httpx>=0.25.0", "beautifulsoup4>=4.12.0"],
        }

        resolution = await installer.resolve_dependencies(metadata)

        assert resolution.success is True
        assert len(resolution.packages) == 2
        assert "httpx>=0.25.0" in resolution.packages

    @pytest.mark.asyncio
    async def test_resolve_dependencies_empty_list(self) -> None:
        """GIVEN skill metadata without dependencies
        WHEN resolving dependencies
        THEN packages list should be empty
        """
        installer = SkillInstaller()
        metadata = {}

        resolution = await installer.resolve_dependencies(metadata)

        assert resolution.success is True
        assert len(resolution.packages) == 0

    @pytest.mark.asyncio
    async def test_install_dependencies_with_pyproject_toml(self, tmp_path: Path) -> None:
        """GIVEN a skill directory with pyproject.toml
        WHEN installing dependencies
        THEN uv sync should be called
        """
        skill_dir = tmp_path / "skill-with-pyproject"
        skill_dir.mkdir()

        # Create pyproject.toml
        pyproject = skill_dir / "pyproject.toml"
        pyproject.write_text(
            textwrap.dedent("""
            [project]
            name = "test-skill"
            version = "1.0.0"
            dependencies = ["httpx>=0.25.0"]
        """).strip()
        )

        installer = SkillInstaller()

        with patch(
            "mcp_server_langgraph.skills.installer.asyncio.create_subprocess_exec",
            new_callable=AsyncMock,
        ) as mock_exec:
            mock_process = AsyncMock(spec=asyncio.subprocess.Process)
            mock_process.returncode = 0
            mock_process.communicate = AsyncMock(return_value=(b"", b""))
            mock_exec.return_value = mock_process

            result = await installer.install_dependencies(skill_dir, [])

        assert result is True
        # Verify uv sync was called
        mock_exec.assert_called()
        call_args = mock_exec.call_args[0]
        assert "uv" in call_args[0]
        assert "sync" in call_args

    @pytest.mark.asyncio
    async def test_install_dependencies_with_requirements_txt(self, tmp_path: Path) -> None:
        """GIVEN a skill directory with requirements.txt
        WHEN installing dependencies
        THEN uv pip install should be called
        """
        skill_dir = tmp_path / "skill-with-requirements"
        skill_dir.mkdir()

        # Create requirements.txt
        requirements = skill_dir / "requirements.txt"
        requirements.write_text("httpx>=0.25.0\nbeautifulsoup4>=4.12.0\n")

        installer = SkillInstaller()

        with patch(
            "mcp_server_langgraph.skills.installer.asyncio.create_subprocess_exec",
            new_callable=AsyncMock,
        ) as mock_exec:
            mock_process = AsyncMock(spec=asyncio.subprocess.Process)
            mock_process.returncode = 0
            mock_process.communicate = AsyncMock(return_value=(b"", b""))
            mock_exec.return_value = mock_process

            result = await installer.install_dependencies(skill_dir, [])

        assert result is True
        # Verify uv pip install was called
        mock_exec.assert_called()
        call_args = mock_exec.call_args[0]
        assert "uv" in call_args[0]
        assert "pip" in call_args
        assert "install" in call_args

    @pytest.mark.asyncio
    async def test_install_dependencies_creates_requirements_from_list(self, tmp_path: Path) -> None:
        """GIVEN a skill directory without dependency files
        WHEN installing with a dependencies list
        THEN requirements.txt should be created and uv called
        """
        skill_dir = tmp_path / "skill-no-deps-file"
        skill_dir.mkdir()

        installer = SkillInstaller()
        dependencies = ["httpx>=0.25.0", "pyyaml>=6.0"]

        with patch(
            "mcp_server_langgraph.skills.installer.asyncio.create_subprocess_exec",
            new_callable=AsyncMock,
        ) as mock_exec:
            mock_process = AsyncMock(spec=asyncio.subprocess.Process)
            mock_process.returncode = 0
            mock_process.communicate = AsyncMock(return_value=(b"", b""))
            mock_exec.return_value = mock_process

            result = await installer.install_dependencies(skill_dir, dependencies)

        assert result is True
        # Check requirements.txt was created
        requirements = skill_dir / "requirements.txt"
        assert requirements.exists()
        content = requirements.read_text()
        assert "httpx>=0.25.0" in content
        assert "pyyaml>=6.0" in content

    @pytest.mark.asyncio
    async def test_install_dependencies_handles_uv_failure(self, tmp_path: Path) -> None:
        """GIVEN uv command fails
        WHEN installing dependencies
        THEN result should be False
        """
        skill_dir = tmp_path / "skill-uv-fail"
        skill_dir.mkdir()
        (skill_dir / "requirements.txt").write_text("invalid-package-xyz\n")

        installer = SkillInstaller()

        with patch(
            "mcp_server_langgraph.skills.installer.asyncio.create_subprocess_exec",
            new_callable=AsyncMock,
        ) as mock_exec:
            mock_process = AsyncMock(spec=asyncio.subprocess.Process)
            mock_process.returncode = 1
            mock_process.communicate = AsyncMock(return_value=(b"", b"ERROR: Package not found"))
            mock_exec.return_value = mock_process

            result = await installer.install_dependencies(skill_dir, [])

        assert result is False


class TestSkillInstallerUninstall:
    """Test suite for skill uninstallation."""

    def teardown_method(self) -> None:
        """Force GC to prevent mock accumulation in xdist workers."""
        gc.collect()

    @pytest.mark.asyncio
    async def test_uninstall_removes_skill_directory(self, tmp_path: Path) -> None:
        """GIVEN an installed skill
        WHEN uninstalling
        THEN the skill directory should be removed
        """
        skill_dir = tmp_path / "to-uninstall"
        skill_dir.mkdir()
        (skill_dir / "SKILL.md").write_text("# Skill")

        installer = SkillInstaller(install_path=tmp_path)

        result = await installer.uninstall("to-uninstall")

        assert result is True
        assert not skill_dir.exists()

    @pytest.mark.asyncio
    async def test_uninstall_nonexistent_returns_false(self, tmp_path: Path) -> None:
        """GIVEN a skill that doesn't exist
        WHEN uninstalling
        THEN result should be False
        """
        installer = SkillInstaller(install_path=tmp_path)

        result = await installer.uninstall("nonexistent")

        assert result is False


class TestSkillInstallerList:
    """Test suite for listing installed skills."""

    def teardown_method(self) -> None:
        """Force GC to prevent mock accumulation in xdist workers."""
        gc.collect()

    def test_list_installed_empty(self, tmp_path: Path) -> None:
        """GIVEN no installed skills
        WHEN listing installed
        THEN empty list should be returned
        """
        installer = SkillInstaller(install_path=tmp_path)
        tmp_path.mkdir(exist_ok=True)

        result = installer.list_installed()

        assert result == []

    def test_list_installed_returns_skills_with_skill_md(self, tmp_path: Path) -> None:
        """GIVEN directories with SKILL.md
        WHEN listing installed
        THEN only valid skill directories should be returned
        """
        # Create valid skill
        valid_skill = tmp_path / "valid-skill"
        valid_skill.mkdir()
        (valid_skill / "SKILL.md").write_text("# Valid")

        # Create directory without SKILL.md
        invalid_dir = tmp_path / "not-a-skill"
        invalid_dir.mkdir()

        installer = SkillInstaller(install_path=tmp_path)

        result = installer.list_installed()

        assert len(result) == 1
        assert "valid-skill" in result

    def test_is_installed_true(self, tmp_path: Path) -> None:
        """GIVEN an installed skill
        WHEN checking is_installed
        THEN True should be returned
        """
        skill_dir = tmp_path / "installed-skill"
        skill_dir.mkdir()
        (skill_dir / "SKILL.md").write_text("# Skill")

        installer = SkillInstaller(install_path=tmp_path)

        assert installer.is_installed("installed-skill") is True

    def test_is_installed_false(self, tmp_path: Path) -> None:
        """GIVEN a non-existent skill
        WHEN checking is_installed
        THEN False should be returned
        """
        installer = SkillInstaller(install_path=tmp_path)

        assert installer.is_installed("not-installed") is False


class TestSkillInstallerMarketplace:
    """Test suite for marketplace fetch functionality (lines 150-166)."""

    def teardown_method(self) -> None:
        """Force GC to prevent mock accumulation in xdist workers."""
        gc.collect()

    @pytest.mark.asyncio
    async def test_fetch_skill_from_marketplace_success(self, tmp_path: Path) -> None:
        """GIVEN a valid marketplace and skill
        WHEN fetching skill from marketplace
        THEN skill data should be returned
        """
        installer = SkillInstaller(install_path=tmp_path)

        with patch("mcp_server_langgraph.skills.marketplace.MarketplaceRegistry") as mock_registry_class:
            with patch("mcp_server_langgraph.skills.marketplace.MarketplaceClient") as mock_client_class:
                # Setup registry mock
                mock_registry = MagicMock()
                mock_marketplace = MagicMock()
                mock_registry.get.return_value = mock_marketplace
                mock_registry_class.return_value = mock_registry

                # Setup client mock
                mock_client = MagicMock()
                mock_client.fetch_skill = AsyncMock(
                    return_value={
                        "name": "test-skill",
                        "content": "# Test Skill",
                        "dependencies": ["httpx>=0.25.0"],
                    }
                )
                mock_client_class.return_value = mock_client

                result = await installer._fetch_skill_from_marketplace("test-skill", "anthropic")

                assert result["name"] == "test-skill"
                assert "content" in result
                mock_registry.get.assert_called_once_with("anthropic")
                mock_client.fetch_skill.assert_called_once_with(mock_marketplace, "test-skill")

    @pytest.mark.asyncio
    async def test_fetch_skill_from_marketplace_unknown_marketplace(self, tmp_path: Path) -> None:
        """GIVEN an unknown marketplace name
        WHEN fetching skill from marketplace
        THEN ValueError should be raised
        """
        installer = SkillInstaller(install_path=tmp_path)

        with patch("mcp_server_langgraph.skills.marketplace.MarketplaceRegistry") as mock_registry_class:
            with patch("mcp_server_langgraph.skills.marketplace.MarketplaceClient"):
                # Registry returns None for unknown marketplace
                mock_registry = MagicMock()
                mock_registry.get.return_value = None
                mock_registry_class.return_value = mock_registry

                with pytest.raises(ValueError, match="Unknown marketplace"):
                    await installer._fetch_skill_from_marketplace("test-skill", "unknown-marketplace")

    @pytest.mark.asyncio
    async def test_fetch_skill_from_marketplace_skill_not_found(self, tmp_path: Path) -> None:
        """GIVEN a valid marketplace but non-existent skill
        WHEN fetching skill from marketplace
        THEN ValueError should be raised
        """
        installer = SkillInstaller(install_path=tmp_path)

        with patch("mcp_server_langgraph.skills.marketplace.MarketplaceRegistry") as mock_registry_class:
            with patch("mcp_server_langgraph.skills.marketplace.MarketplaceClient") as mock_client_class:
                # Setup registry mock - marketplace exists
                mock_registry = MagicMock()
                mock_marketplace = MagicMock()
                mock_registry.get.return_value = mock_marketplace
                mock_registry_class.return_value = mock_registry

                # Setup client mock - skill not found
                mock_client = MagicMock()
                mock_client.fetch_skill = AsyncMock(return_value=None)
                mock_client_class.return_value = mock_client

                with pytest.raises(ValueError, match="Skill not found"):
                    await installer._fetch_skill_from_marketplace("nonexistent-skill", "anthropic")


class TestSkillInstallerExceptionHandling:
    """Test suite for exception handling in dependency installation (lines 238-241)."""

    def teardown_method(self) -> None:
        """Force GC to prevent mock accumulation in xdist workers."""
        gc.collect()

    @pytest.mark.asyncio
    async def test_install_dependencies_no_deps_returns_true(self, tmp_path: Path) -> None:
        """GIVEN a skill directory without dependency files and empty list
        WHEN installing dependencies
        THEN should return True without calling uv
        """
        skill_dir = tmp_path / "skill-no-deps"
        skill_dir.mkdir()

        installer = SkillInstaller()

        with patch(
            "mcp_server_langgraph.skills.installer.asyncio.create_subprocess_exec",
            new_callable=AsyncMock,
        ) as mock_exec:
            result = await installer.install_dependencies(skill_dir, [])

        assert result is True
        # uv should not be called when no dependencies
        mock_exec.assert_not_called()

    @pytest.mark.asyncio
    async def test_install_dependencies_exception_returns_false(self, tmp_path: Path) -> None:
        """GIVEN an exception during dependency installation
        WHEN installing dependencies
        THEN should log error and return False
        """
        skill_dir = tmp_path / "skill-exception"
        skill_dir.mkdir()

        # Create requirements.txt to trigger uv call
        (skill_dir / "requirements.txt").write_text("httpx>=0.25.0\n")

        installer = SkillInstaller()

        with patch(
            "mcp_server_langgraph.skills.installer.asyncio.create_subprocess_exec",
            new_callable=AsyncMock,
            side_effect=OSError("Command not found: uv"),
        ):
            with patch("mcp_server_langgraph.skills.installer.logger") as mock_logger:
                result = await installer.install_dependencies(skill_dir, [])

        assert result is False
        # Error should be logged (uses logger.exception which includes traceback)
        mock_logger.exception.assert_called_once()
        assert "Failed to install dependencies" in str(mock_logger.exception.call_args)


# =============================================================================
# NEW: Tests for list_marketplace_skills() - TDD RED Phase
# =============================================================================


class TestSkillInstallerListMarketplaceSkills:
    """Test suite for list_marketplace_skills() method.

    This method fetches skills from a marketplace with full metadata
    (name, description, version, tags, author) instead of just directory names.
    """

    def teardown_method(self) -> None:
        """Force GC to prevent mock accumulation in xdist workers."""
        gc.collect()

    @pytest.mark.asyncio
    async def test_list_marketplace_skills_exists(self) -> None:
        """GIVEN a SkillInstaller
        WHEN calling list_marketplace_skills
        THEN the method should exist and be callable
        """
        installer = SkillInstaller()
        assert hasattr(installer, "list_marketplace_skills")
        assert callable(installer.list_marketplace_skills)

    @pytest.mark.asyncio
    async def test_list_marketplace_skills_returns_list(self, tmp_path: Path) -> None:
        """GIVEN a valid marketplace
        WHEN listing marketplace skills
        THEN a list of skill metadata dictionaries should be returned
        """
        installer = SkillInstaller(install_path=tmp_path)

        with patch("mcp_server_langgraph.skills.marketplace.MarketplaceRegistry") as mock_registry_class:
            with patch("mcp_server_langgraph.skills.marketplace.MarketplaceClient") as mock_client_class:
                # Setup registry mock
                mock_registry = MagicMock()
                mock_marketplace = MagicMock()
                mock_marketplace.type = "github"
                mock_marketplace.uri = "https://github.com/anthropics/skills"
                mock_registry.get.return_value = mock_marketplace
                mock_registry_class.return_value = mock_registry

                # Setup client mock with full metadata
                mock_client = MagicMock()
                mock_client.list_skills_with_metadata = AsyncMock(
                    return_value=[
                        {
                            "name": "web-research",
                            "description": "Research topics on the web",
                            "version": "1.0.0",
                            "tags": ["research", "web"],
                            "author": "Anthropic",
                        },
                        {
                            "name": "code-review",
                            "description": "Review code changes",
                            "version": "1.2.0",
                            "tags": ["code", "review"],
                            "author": "Anthropic",
                        },
                    ]
                )
                mock_client_class.return_value = mock_client

                result = await installer.list_marketplace_skills("anthropic")

                assert isinstance(result, list)
                assert len(result) == 2

    @pytest.mark.asyncio
    async def test_list_marketplace_skills_returns_full_metadata(self, tmp_path: Path) -> None:
        """GIVEN a marketplace with skills
        WHEN listing marketplace skills
        THEN each skill should have name, description, version, tags, and author
        """
        installer = SkillInstaller(install_path=tmp_path)

        with patch("mcp_server_langgraph.skills.marketplace.MarketplaceRegistry") as mock_registry_class:
            with patch("mcp_server_langgraph.skills.marketplace.MarketplaceClient") as mock_client_class:
                mock_registry = MagicMock()
                mock_marketplace = MagicMock()
                mock_registry.get.return_value = mock_marketplace
                mock_registry_class.return_value = mock_registry

                mock_client = MagicMock()
                mock_client.list_skills_with_metadata = AsyncMock(
                    return_value=[
                        {
                            "name": "web-research",
                            "description": "Research topics on the web",
                            "version": "1.0.0",
                            "tags": ["research", "web"],
                            "author": "Anthropic",
                        },
                    ]
                )
                mock_client_class.return_value = mock_client

                result = await installer.list_marketplace_skills("anthropic")

                assert len(result) == 1
                skill = result[0]
                assert "name" in skill
                assert "description" in skill
                assert "version" in skill
                assert "tags" in skill
                assert skill["name"] == "web-research"
                assert skill["version"] == "1.0.0"

    @pytest.mark.asyncio
    async def test_list_marketplace_skills_unknown_marketplace(self, tmp_path: Path) -> None:
        """GIVEN an unknown marketplace name
        WHEN listing marketplace skills
        THEN ValueError should be raised
        """
        installer = SkillInstaller(install_path=tmp_path)

        with patch("mcp_server_langgraph.skills.marketplace.MarketplaceRegistry") as mock_registry_class:
            mock_registry = MagicMock()
            mock_registry.get.return_value = None
            mock_registry_class.return_value = mock_registry

            with pytest.raises(ValueError, match="Unknown marketplace"):
                await installer.list_marketplace_skills("unknown-marketplace")

    @pytest.mark.asyncio
    async def test_list_marketplace_skills_empty_marketplace(self, tmp_path: Path) -> None:
        """GIVEN an empty marketplace
        WHEN listing marketplace skills
        THEN empty list should be returned
        """
        installer = SkillInstaller(install_path=tmp_path)

        with patch("mcp_server_langgraph.skills.marketplace.MarketplaceRegistry") as mock_registry_class:
            with patch("mcp_server_langgraph.skills.marketplace.MarketplaceClient") as mock_client_class:
                mock_registry = MagicMock()
                mock_marketplace = MagicMock()
                mock_registry.get.return_value = mock_marketplace
                mock_registry_class.return_value = mock_registry

                mock_client = MagicMock()
                mock_client.list_skills_with_metadata = AsyncMock(return_value=[])
                mock_client_class.return_value = mock_client

                result = await installer.list_marketplace_skills("anthropic")

                assert result == []


# =============================================================================
# NEW: Tests for install_skill() - TDD RED Phase
# =============================================================================


class TestSkillInstallerInstallSkillMethod:
    """Test suite for install_skill() method.

    This method wraps install() and integrates with version tracking
    for the auto-update system.
    """

    def teardown_method(self) -> None:
        """Force GC to prevent mock accumulation in xdist workers."""
        gc.collect()

    @pytest.mark.asyncio
    async def test_install_skill_exists(self) -> None:
        """GIVEN a SkillInstaller
        WHEN checking for install_skill method
        THEN the method should exist and be callable
        """
        installer = SkillInstaller()
        assert hasattr(installer, "install_skill")
        assert callable(installer.install_skill)

    @pytest.mark.asyncio
    async def test_install_skill_installs_skill(self, tmp_path: Path) -> None:
        """GIVEN a valid skill name
        WHEN calling install_skill
        THEN the skill should be installed
        """
        installer = SkillInstaller(install_path=tmp_path)

        with patch.object(
            installer,
            "_fetch_skill_from_marketplace",
            new_callable=AsyncMock,
            return_value={
                "name": "test-skill",
                "description": "A test skill",
                "content": "---\nname: test-skill\nversion: 1.0.0\n---\n# Test Skill",
                "version": "1.0.0",
            },
        ):
            result = await installer.install_skill("test-skill")

            assert result.success is True
            assert result.skill_name == "test-skill"
            assert (tmp_path / "test-skill" / "SKILL.md").exists()

    @pytest.mark.asyncio
    async def test_install_skill_with_version(self, tmp_path: Path) -> None:
        """GIVEN a skill name and version
        WHEN calling install_skill
        THEN the specific version should be installed
        """
        installer = SkillInstaller(install_path=tmp_path)

        with patch.object(
            installer,
            "_fetch_skill_from_marketplace",
            new_callable=AsyncMock,
            return_value={
                "name": "versioned-skill",
                "content": "---\nname: versioned-skill\nversion: 2.0.0\n---\n# Skill",
                "version": "2.0.0",
            },
        ):
            result = await installer.install_skill("versioned-skill", version="2.0.0")

            assert result.success is True
            assert result.version == "2.0.0"

    @pytest.mark.asyncio
    async def test_install_skill_with_marketplace(self, tmp_path: Path) -> None:
        """GIVEN a skill name and marketplace
        WHEN calling install_skill
        THEN the skill should be fetched from the correct marketplace
        """
        installer = SkillInstaller(install_path=tmp_path)

        with patch.object(
            installer,
            "_fetch_skill_from_marketplace",
            new_callable=AsyncMock,
            return_value={
                "name": "enterprise-skill",
                "content": "# Enterprise Skill",
            },
        ) as mock_fetch:
            await installer.install_skill("enterprise-skill", marketplace="enterprise")

            mock_fetch.assert_called_once_with("enterprise-skill", "enterprise")

    @pytest.mark.asyncio
    async def test_install_skill_returns_installation_result(self, tmp_path: Path) -> None:
        """GIVEN a successful installation
        WHEN checking the result
        THEN it should be an InstallationResult with all fields populated
        """
        from mcp_server_langgraph.skills.installer import InstallationResult

        installer = SkillInstaller(install_path=tmp_path)

        with patch.object(
            installer,
            "_fetch_skill_from_marketplace",
            new_callable=AsyncMock,
            return_value={
                "name": "result-skill",
                "content": "# Result Skill",
            },
        ):
            result = await installer.install_skill("result-skill")

            assert isinstance(result, InstallationResult)
            assert result.success is True
            assert result.skill_name == "result-skill"
            assert result.installed_path is not None

    @pytest.mark.asyncio
    async def test_install_skill_notifies_auto_update_scheduler(self, tmp_path: Path) -> None:
        """GIVEN a successful installation
        WHEN install_skill completes
        THEN the auto-update scheduler should be notified of the installed version
        """
        installer = SkillInstaller(install_path=tmp_path)

        with patch.object(
            installer,
            "_fetch_skill_from_marketplace",
            new_callable=AsyncMock,
            return_value={
                "name": "tracked-skill",
                "content": "---\nname: tracked-skill\nversion: 1.5.0\n---\n# Tracked Skill",
                "version": "1.5.0",
            },
        ):
            with patch("mcp_server_langgraph.skills.auto_update.get_auto_update_scheduler") as mock_get_scheduler:
                mock_scheduler = MagicMock()
                mock_get_scheduler.return_value = mock_scheduler

                result = await installer.install_skill("tracked-skill", version="1.5.0", marketplace="anthropic")

                assert result.success is True
                mock_scheduler.register_installed_skill.assert_called_once_with(
                    skill_name="tracked-skill",
                    version="1.5.0",
                    marketplace="anthropic",
                )

    @pytest.mark.asyncio
    async def test_install_skill_failure_does_not_notify_scheduler(self, tmp_path: Path) -> None:
        """GIVEN a failed installation
        WHEN install_skill fails
        THEN the auto-update scheduler should NOT be notified
        """
        installer = SkillInstaller(install_path=tmp_path)

        with patch.object(
            installer,
            "_fetch_skill_from_marketplace",
            new_callable=AsyncMock,
            side_effect=Exception("Marketplace error"),
        ):
            with patch("mcp_server_langgraph.skills.auto_update.get_auto_update_scheduler") as mock_get_scheduler:
                mock_scheduler = MagicMock()
                mock_get_scheduler.return_value = mock_scheduler

                result = await installer.install_skill("failing-skill")

                assert result.success is False
                mock_scheduler.register_installed_skill.assert_not_called()
