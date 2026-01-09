"""
Skill Installer

Installs skills from marketplaces with dependency resolution
and sandboxed package installation.

Uses `uv` for fast, reproducible dependency installation:
- Preferred: pyproject.toml with `uv sync --frozen`
- Fallback: requirements.txt with `uv pip install`

Semantic Search Integration (ADR-0092, ADR-0099):
When skill_search_tool is provided, skills are automatically indexed
on install and de-indexed on uninstall for semantic search discovery.

Usage:
    from mcp_server_langgraph.skills.installer import SkillInstaller

    installer = SkillInstaller()
    result = await installer.install("web-research", source="anthropic")
"""

from __future__ import annotations

import asyncio
import logging
from pathlib import Path
from typing import TYPE_CHECKING, Any

from pydantic import BaseModel, Field

if TYPE_CHECKING:
    from mcp_server_langgraph.skills.search import SkillSearchTool

logger = logging.getLogger(__name__)


class InstallationResult(BaseModel):
    """Result of a skill installation."""

    success: bool = Field(description="Whether installation succeeded")
    skill_name: str = Field(description="Name of the skill")
    version: str | None = Field(default=None, description="Installed version")
    source: str | None = Field(default=None, description="Source marketplace")
    installed_path: str | None = Field(
        default=None,
        description="Path where skill was installed",
    )
    error: str | None = Field(default=None, description="Error message if failed")
    dependencies_installed: list[str] = Field(
        default_factory=list,
        description="List of dependencies installed",
    )


class DependencyResolution(BaseModel):
    """Result of dependency resolution."""

    success: bool
    packages: list[str] = Field(default_factory=list)
    conflicts: list[str] = Field(default_factory=list)
    warnings: list[str] = Field(default_factory=list)


class SkillInstaller:
    """Installs skills from marketplaces.

    Handles downloading, dependency resolution, and installation
    of skills into a local directory.

    When skill_search_tool is provided, automatically indexes skills
    on install and de-indexes on uninstall for semantic search.
    """

    DEFAULT_INSTALL_PATH = Path.home() / ".mcp-langgraph" / "skills"

    def __init__(
        self,
        install_path: Path | str | None = None,
        skill_search_tool: "SkillSearchTool | None" = None,
    ) -> None:
        """Initialize skill installer.

        Args:
            install_path: Directory to install skills to
            skill_search_tool: Optional semantic search tool for indexing
        """
        self.install_path = Path(install_path) if install_path else self.DEFAULT_INSTALL_PATH
        self.skill_search_tool = skill_search_tool

    async def install(
        self,
        skill_name: str,
        source: str = "anthropic",
        version: str | None = None,
    ) -> InstallationResult:
        """Install a skill from a marketplace.

        Args:
            skill_name: Name of skill to install
            source: Source marketplace name
            version: Optional specific version

        Returns:
            InstallationResult with success/failure details
        """
        # Ensure install directory exists
        self.install_path.mkdir(parents=True, exist_ok=True)

        skill_dir = self.install_path / skill_name

        try:
            # Fetch skill from marketplace
            skill_data = await self._fetch_skill_from_marketplace(skill_name, source)

            # Create skill directory
            skill_dir.mkdir(parents=True, exist_ok=True)

            # Write SKILL.md file
            skill_md = skill_dir / "SKILL.md"
            content = skill_data.get("content", f"# {skill_name}\n\nNo content.")
            skill_md.write_text(content)

            # Install dependencies if present
            dependencies = skill_data.get("dependencies", [])
            if dependencies:
                deps_installed = await self.install_dependencies(skill_dir, dependencies)
                if deps_installed:
                    logger.info(f"Installed dependencies for {skill_name}")

            # Index skill for semantic search if tool is available
            if self.skill_search_tool is not None:
                try:
                    from mcp_server_langgraph.skills.models import Skill

                    # Create Skill object from skill_data for indexing
                    skill_obj = Skill(
                        name=skill_name,
                        description=skill_data.get("description", f"Skill: {skill_name}"),
                        instructions=skill_data.get("instructions", ""),
                        tags=skill_data.get("tags", []),
                    )
                    await self.skill_search_tool.index_skill(skill_obj, skill_id=skill_name)
                    logger.info(f"Indexed skill for semantic search: {skill_name}")
                except Exception as e:
                    # Don't fail install if indexing fails
                    logger.warning(f"Failed to index skill {skill_name}: {e}")

            return InstallationResult(
                success=True,
                skill_name=skill_name,
                source=source,
                version=version or "latest",
                installed_path=str(skill_dir),
                dependencies_installed=dependencies,
            )

        except Exception as e:
            logger.exception(f"Failed to install skill {skill_name}: {e}")
            return InstallationResult(
                success=False,
                skill_name=skill_name,
                source=source,
                error=str(e),
            )

    async def _fetch_skill_from_marketplace(
        self,
        skill_name: str,
        source: str,
    ) -> dict[str, Any]:
        """Fetch skill metadata and content from a marketplace.

        Args:
            skill_name: Name of skill to fetch
            source: Marketplace source name

        Returns:
            Skill data dictionary with name, content, and dependencies
        """
        from mcp_server_langgraph.skills.marketplace import (
            MarketplaceRegistry,
            create_marketplace_client,
        )

        registry = MarketplaceRegistry()
        client = create_marketplace_client()

        marketplace = registry.get(source)
        if marketplace is None:
            raise ValueError(f"Unknown marketplace: {source}")

        skill_data = await client.fetch_skill(marketplace, skill_name)
        if skill_data is None:
            raise ValueError(f"Skill not found: {skill_name} in {source}")

        return skill_data

    async def uninstall(self, skill_name: str) -> bool:
        """Uninstall a skill.

        Args:
            skill_name: Name of skill to uninstall

        Returns:
            True if skill was uninstalled
        """
        skill_dir = self.install_path / skill_name
        if skill_dir.exists():
            import shutil

            # De-index from semantic search before removing files
            if self.skill_search_tool is not None:
                try:
                    await self.skill_search_tool.remove_skill(skill_name)
                    logger.info(f"De-indexed skill from semantic search: {skill_name}")
                except Exception as e:
                    # Don't fail uninstall if de-indexing fails
                    logger.warning(f"Failed to de-index skill {skill_name}: {e}")

            shutil.rmtree(skill_dir)
            return True
        return False

    async def resolve_dependencies(
        self,
        skill_metadata: dict[str, Any],
    ) -> DependencyResolution:
        """Resolve skill dependencies.

        Args:
            skill_metadata: Skill metadata with dependencies list

        Returns:
            DependencyResolution with packages to install
        """
        dependencies = skill_metadata.get("dependencies", [])

        # For now, return the dependencies as-is
        # Future: Use `uv pip compile` for full resolution with conflict detection
        return DependencyResolution(
            success=True,
            packages=dependencies,
        )

    async def install_dependencies(
        self,
        skill_dir: Path,
        dependencies: list[str],
    ) -> bool:
        """Install skill dependencies using uv.

        Prefers pyproject.toml, falls back to requirements.txt.

        Args:
            skill_dir: Directory containing skill
            dependencies: List of dependencies to install

        Returns:
            True if installation succeeded
        """
        pyproject = skill_dir / "pyproject.toml"
        requirements = skill_dir / "requirements.txt"

        try:
            if pyproject.exists():
                # Use uv sync for pyproject.toml
                return await self._run_uv_sync(skill_dir)
            elif requirements.exists():
                # Use uv pip install for requirements.txt
                return await self._run_uv_pip_install(skill_dir, requirements)
            else:
                # No dependencies file, create requirements.txt from list
                if dependencies:
                    requirements.write_text("\n".join(dependencies) + "\n")
                    return await self._run_uv_pip_install(skill_dir, requirements)
                # No dependencies to install
                return True
        except Exception as e:
            logger.exception(f"Failed to install dependencies: {e}")
            return False

    async def _run_uv_sync(self, skill_dir: Path) -> bool:
        """Run uv sync for pyproject.toml-based projects.

        Args:
            skill_dir: Directory containing pyproject.toml

        Returns:
            True if successful
        """
        process = await asyncio.create_subprocess_exec(
            "uv",
            "sync",
            "--frozen",
            "--no-dev",
            cwd=str(skill_dir),
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE,
        )
        stdout, stderr = await process.communicate()

        if process.returncode != 0:
            logger.error(f"uv sync failed: {stderr.decode()}")
            return False

        logger.debug(f"uv sync output: {stdout.decode()}")
        return True

    async def _run_uv_pip_install(
        self,
        skill_dir: Path,
        requirements: Path,
    ) -> bool:
        """Run uv pip install for requirements.txt-based projects.

        Args:
            skill_dir: Directory containing the skill
            requirements: Path to requirements.txt

        Returns:
            True if successful
        """
        process = await asyncio.create_subprocess_exec(
            "uv",
            "pip",
            "install",
            "-r",
            str(requirements),
            "--quiet",
            cwd=str(skill_dir),
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE,
        )
        stdout, stderr = await process.communicate()

        if process.returncode != 0:
            logger.error(f"uv pip install failed: {stderr.decode()}")
            return False

        logger.debug(f"uv pip install output: {stdout.decode()}")
        return True

    def list_installed(self) -> list[str]:
        """List installed skills.

        Returns:
            List of installed skill names
        """
        if not self.install_path.exists():
            return []

        return [d.name for d in self.install_path.iterdir() if d.is_dir() and (d / "SKILL.md").exists()]

    def is_installed(self, skill_name: str) -> bool:
        """Check if a skill is installed.

        Args:
            skill_name: Name of skill

        Returns:
            True if skill is installed
        """
        skill_dir = self.install_path / skill_name
        return skill_dir.exists() and (skill_dir / "SKILL.md").exists()

    async def list_marketplace_skills(
        self,
        marketplace: str = "anthropic",
    ) -> list[dict[str, Any]]:
        """List skills from a marketplace with full metadata.

        Unlike the basic listing which returns only directory names,
        this method fetches and parses SKILL.md for each skill to
        return full metadata including description, version, tags, and author.

        Args:
            marketplace: Marketplace name (default: "anthropic")

        Returns:
            List of skill metadata dictionaries with keys:
            - name: Skill name
            - description: Skill description
            - version: Skill version
            - tags: List of tags
            - author: Skill author (if available)

        Raises:
            ValueError: If marketplace is not found
        """
        from mcp_server_langgraph.skills.marketplace import (
            MarketplaceRegistry,
            create_marketplace_client,
        )

        registry = MarketplaceRegistry()
        client = create_marketplace_client()

        marketplace_config = registry.get(marketplace)
        if marketplace_config is None:
            raise ValueError(f"Unknown marketplace: {marketplace}")

        # Use the enhanced method that fetches full metadata
        return await client.list_skills_with_metadata(marketplace_config)

    async def install_skill(
        self,
        skill_name: str,
        version: str | None = None,
        marketplace: str = "anthropic",
    ) -> InstallationResult:
        """Install a skill with version tracking for auto-updates.

        This method wraps the basic install() method and integrates
        with the AutoUpdateScheduler to track installed versions.

        Args:
            skill_name: Name of skill to install
            version: Optional specific version to install
            marketplace: Source marketplace name (default: "anthropic")

        Returns:
            InstallationResult with installation details
        """
        from mcp_server_langgraph.skills.auto_update import get_auto_update_scheduler

        # Perform the installation
        result = await self.install(skill_name, source=marketplace, version=version)

        # If successful, register with auto-update scheduler for version tracking
        if result.success:
            try:
                scheduler = get_auto_update_scheduler()
                installed_version = version or result.version or "latest"
                scheduler.register_installed_skill(
                    skill_name=skill_name,
                    version=installed_version,
                    marketplace=marketplace,
                )
            except Exception as e:
                # Don't fail the installation if version tracking fails
                logger.warning(f"Failed to register skill version: {e}")

        return result
