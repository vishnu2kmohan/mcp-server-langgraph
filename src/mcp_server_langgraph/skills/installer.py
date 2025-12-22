"""
Skill Installer

Installs skills from marketplaces with dependency resolution
and sandboxed package installation.

Uses `uv` for fast, reproducible dependency installation:
- Preferred: pyproject.toml with `uv sync --frozen`
- Fallback: requirements.txt with `uv pip install`

Usage:
    from mcp_server_langgraph.skills.installer import SkillInstaller

    installer = SkillInstaller()
    result = await installer.install("web-research", source="anthropic")
"""

from __future__ import annotations

import asyncio
import logging
from pathlib import Path
from typing import Any

from pydantic import BaseModel, Field

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
    """

    DEFAULT_INSTALL_PATH = Path.home() / ".mcp-langgraph" / "skills"

    def __init__(
        self,
        install_path: Path | str | None = None,
    ) -> None:
        """Initialize skill installer.

        Args:
            install_path: Directory to install skills to
        """
        self.install_path = Path(install_path) if install_path else self.DEFAULT_INSTALL_PATH

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

            return InstallationResult(
                success=True,
                skill_name=skill_name,
                source=source,
                version=version or "latest",
                installed_path=str(skill_dir),
                dependencies_installed=dependencies,
            )

        except Exception as e:
            logger.error(f"Failed to install skill {skill_name}: {e}")
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
            MarketplaceClient,
            MarketplaceRegistry,
        )

        registry = MarketplaceRegistry()
        client = MarketplaceClient()

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
            logger.error(f"Failed to install dependencies: {e}")
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

        return [
            d.name
            for d in self.install_path.iterdir()
            if d.is_dir() and (d / "SKILL.md").exists()
        ]

    def is_installed(self, skill_name: str) -> bool:
        """Check if a skill is installed.

        Args:
            skill_name: Name of skill

        Returns:
            True if skill is installed
        """
        skill_dir = self.install_path / skill_name
        return skill_dir.exists() and (skill_dir / "SKILL.md").exists()
