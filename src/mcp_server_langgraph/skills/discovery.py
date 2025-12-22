"""
Skill Discovery

Progressive skill discovery with search and filtering capabilities.

Implements Anthropic's progressive disclosure pattern where skill
summaries are returned initially, and full details on-demand.

Usage:
    from mcp_server_langgraph.skills.discovery import SkillDiscovery

    discovery = SkillDiscovery()
    discovery.load_from_directory("/path/to/skills")
    summaries = discovery.get_skill_summaries()
    full_skill = discovery.get_skill("web-research")
"""

from __future__ import annotations

from pathlib import Path
from typing import Any

from mcp_server_langgraph.skills.loader import SkillError, SkillLoader
from mcp_server_langgraph.skills.models import Skill
from mcp_server_langgraph.skills.registry import SkillRegistry


class SkillDiscovery:
    """Progressive skill discovery service.

    Provides search, filtering, and on-demand loading of skills
    with support for progressive disclosure (summaries vs full details).
    """

    def __init__(self, registry: SkillRegistry | None = None) -> None:
        """Initialize skill discovery.

        Args:
            registry: Optional existing registry. Creates new if not provided.
        """
        self.registry = registry or SkillRegistry()
        self._loader = SkillLoader()

    def list_available(self) -> list[Skill]:
        """List all available skills.

        Returns:
            List of all registered skills
        """
        return self.registry.list_all()

    def get_skill_summaries(self) -> list[dict[str, Any]]:
        """Get summaries of all skills (progressive disclosure).

        Returns minimal information to reduce token usage.
        Full skill details can be retrieved with get_skill().

        Returns:
            List of skill summary dictionaries
        """
        summaries = []
        for skill in self.registry.list_all():
            summaries.append(self._to_summary(skill))
        return summaries

    def _to_summary(self, skill: Skill) -> dict[str, Any]:
        """Convert skill to summary dict.

        Args:
            skill: Skill to summarize

        Returns:
            Dictionary with minimal skill info
        """
        return {
            "name": skill.name,
            "description": skill.description,
            "version": skill.version,
            "tags": skill.tags,
        }

    def get_skill(self, name: str) -> Skill | None:
        """Get full skill details by name.

        Args:
            name: Skill name to retrieve

        Returns:
            Full Skill object if found, None otherwise
        """
        return self.registry.get(name)

    def load_from_directory(self, directory: Path | str) -> int:
        """Load all skills from a directory tree.

        Discovers SKILL.md files in subdirectories and registers them.
        Invalid skills are skipped with warnings.

        Args:
            directory: Base directory to search for skills

        Returns:
            Number of skills successfully loaded
        """
        directory = Path(directory)
        if not directory.exists():
            return 0

        count = 0
        for skill_file in directory.rglob("SKILL.md"):
            try:
                skill = self._loader.load_from_path(skill_file)
                self.registry.register(skill)
                count += 1
            except SkillError:
                # Skip invalid skills during discovery
                pass

        return count

    def search(
        self,
        query: str,
        summary_only: bool = False,
    ) -> list[Skill] | list[dict[str, Any]]:
        """Search skills by query.

        Args:
            query: Search query (matches name, description, tags)
            summary_only: If True, return summaries instead of full skills

        Returns:
            List of matching skills or skill summaries
        """
        results = self.registry.search(query)

        if summary_only:
            return [self._to_summary(skill) for skill in results]

        return results
