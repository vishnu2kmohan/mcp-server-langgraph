"""
Skill Registry

Local skill registry for registering, discovering, and managing skills.

Usage:
    from mcp_server_langgraph.skills.registry import SkillRegistry

    registry = SkillRegistry()
    registry.register(skill)
    skill = registry.get("web-research")
"""

from __future__ import annotations

from mcp_server_langgraph.skills.models import Skill


class SkillRegistry:
    """Registry for managing skills.

    Provides registration, lookup, search, and filtering capabilities
    for skills loaded from SKILL.md files.
    """

    def __init__(self) -> None:
        """Initialize an empty skill registry."""
        self._skills: dict[str, Skill] = {}

    def register(self, skill: Skill) -> None:
        """Register a skill in the registry.

        Args:
            skill: Skill to register
        """
        self._skills[skill.name] = skill

    def get(self, name: str) -> Skill | None:
        """Get a skill by name.

        Args:
            name: Skill name to look up

        Returns:
            Skill if found, None otherwise
        """
        return self._skills.get(name)

    def list_all(self) -> list[Skill]:
        """List all registered skills.

        Returns:
            List of all skills in the registry
        """
        return list(self._skills.values())

    def unregister(self, name: str) -> None:
        """Unregister a skill by name.

        Does not raise an error if the skill doesn't exist.

        Args:
            name: Name of skill to remove
        """
        self._skills.pop(name, None)

    def search(self, query: str) -> list[Skill]:
        """Search skills by name, description, or tags.

        Args:
            query: Search query string (case-insensitive)

        Returns:
            List of matching skills
        """
        if not query:
            return self.list_all()

        query_lower = query.lower()
        results: list[Skill] = []

        for skill in self._skills.values():
            # Search in name
            if query_lower in skill.name.lower():
                results.append(skill)
                continue

            # Search in description
            if query_lower in skill.description.lower():
                results.append(skill)
                continue

            # Search in tags
            for tag in skill.tags:
                if query_lower in tag.lower():
                    results.append(skill)
                    break

        return results

    def list_by_source(self, source: str) -> list[Skill]:
        """List skills from a specific source.

        Args:
            source: Source to filter by (e.g., "local", "anthropics/skills")

        Returns:
            List of skills from the specified source
        """
        source_lower = source.lower()
        return [
            skill
            for skill in self._skills.values()
            if source_lower in skill.source.lower()
        ]

    def clear(self) -> None:
        """Remove all skills from the registry."""
        self._skills.clear()
