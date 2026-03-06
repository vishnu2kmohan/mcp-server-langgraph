"""HierarchicalSkillRegistry for scope-aware skill management.

Extends the base SkillRegistry with hierarchical scope support,
enabling skill registration and lookup based on CapabilityScope.

Scope Resolution:
- Skills registered at higher scopes (PROJECT, USER) are available at
  lower scopes (SESSION, TASK)
- Lower scope skills override higher scope skills with the same name
- Resolution follows the scope precedence order from ADR-0092

Usage:
    from mcp_server_langgraph.skills.hierarchical import HierarchicalSkillRegistry
    from mcp_server_langgraph.core.scopes import CapabilityScope

    registry = HierarchicalSkillRegistry()
    registry.register_for_scope(skill, CapabilityScope.PROJECT)
    skill = registry.get_for_scope("skill-name", CapabilityScope.TASK)

ADR Reference: adr/adr-0092-hierarchical-capability-architecture.md
"""

from __future__ import annotations

from collections import defaultdict

from mcp_server_langgraph.core.scopes import (
    CapabilityScope,
    SCOPE_PRECEDENCE,
)
from mcp_server_langgraph.skills.models import Skill
from mcp_server_langgraph.skills.registry import SkillRegistry


class HierarchicalSkillRegistry(SkillRegistry):
    """Skill registry with hierarchical scope support.

    Extends SkillRegistry to support scope-based registration and lookup.
    Skills can be registered at specific scopes, and lookup resolves
    from the requested scope upward through parent scopes.

    Attributes:
        _scoped_skills: Dict mapping scope -> name -> skill
    """

    def __init__(self) -> None:
        """Initialize hierarchical skill registry."""
        super().__init__()
        # Scoped storage: scope -> name -> skill
        self._scoped_skills: dict[CapabilityScope, dict[str, Skill]] = defaultdict(dict)

    def register_for_scope(self, skill: Skill, scope: CapabilityScope) -> None:
        """Register a skill at a specific scope.

        Args:
            skill: Skill to register
            scope: CapabilityScope to register at
        """
        self._scoped_skills[scope][skill.name] = skill
        # Also register in base registry for backward compatibility
        super().register(skill)

    def get_for_scope(
        self,
        name: str,
        scope: CapabilityScope,
        resolve_upward: bool = True,
    ) -> Skill | None:
        """Get a skill by name, resolving through scope hierarchy.

        Looks for the skill at the specified scope first, then
        traverses upward through parent scopes until found.

        Args:
            name: Skill name to look up
            scope: Starting scope for resolution
            resolve_upward: If True, resolve through parent scopes

        Returns:
            Skill if found, None otherwise
        """
        if resolve_upward:
            # Get scopes to check, starting from requested scope
            scopes_to_check = self._get_resolution_order(scope)

            for check_scope in scopes_to_check:
                if check_scope in self._scoped_skills:
                    if name in self._scoped_skills[check_scope]:
                        return self._scoped_skills[check_scope][name]

            # Fall back to base registry
            return super().get(name)
        else:
            # Only check the specified scope
            if scope in self._scoped_skills:
                return self._scoped_skills[scope].get(name)
            return None

    def list_for_scope(
        self,
        scope: CapabilityScope,
        include_parent_scopes: bool = True,
    ) -> list[Skill]:
        """List skills available at a scope.

        Returns all skills visible at the specified scope, optionally
        including skills from parent scopes. When including parent
        scopes, lower scope skills override higher scope skills with
        the same name.

        Args:
            scope: Scope to list skills for
            include_parent_scopes: If True, include skills from parent scopes

        Returns:
            List of skills available at this scope
        """
        if include_parent_scopes:
            # Collect skills from all parent scopes, with lower scopes overriding
            skills_by_name: dict[str, Skill] = {}

            # Traverse from highest scope to lowest (so lower overrides higher)
            scopes_to_check = list(reversed(self._get_resolution_order(scope)))

            for check_scope in scopes_to_check:
                if check_scope in self._scoped_skills:
                    skills_by_name.update(self._scoped_skills[check_scope])

            return list(skills_by_name.values())
        else:
            # Only return skills from this exact scope
            if scope in self._scoped_skills:
                return list(self._scoped_skills[scope].values())
            return []

    def unregister_for_scope(self, name: str, scope: CapabilityScope) -> None:
        """Unregister a skill from a specific scope.

        Args:
            name: Skill name to unregister
            scope: Scope to unregister from
        """
        if scope in self._scoped_skills:
            self._scoped_skills[scope].pop(name, None)

    def clear_scope(self, scope: CapabilityScope) -> None:
        """Clear all skills from a specific scope.

        Args:
            scope: Scope to clear
        """
        if scope in self._scoped_skills:
            self._scoped_skills[scope].clear()

    def list_all(self) -> list[Skill]:
        """List all skills across all scopes.

        Returns:
            List of all registered skills
        """
        # Collect from scoped storage
        all_skills: dict[str, Skill] = {}

        for scope_skills in self._scoped_skills.values():
            all_skills.update(scope_skills)

        # Also include any skills only in base registry
        for skill in super().list_all():
            if skill.name not in all_skills:
                all_skills[skill.name] = skill

        return list(all_skills.values())

    def _get_resolution_order(self, scope: CapabilityScope) -> list[CapabilityScope]:
        """Get the order of scopes to check for resolution.

        Returns scopes from the requested scope upward to root,
        ordered by precedence (highest first).

        Args:
            scope: Starting scope

        Returns:
            List of scopes in resolution order
        """
        # Find the index of the current scope in precedence order
        try:
            scope_idx = SCOPE_PRECEDENCE.index(scope)
        except ValueError:
            # If scope not in precedence list, just return it alone
            return [scope]

        # Return scopes from current to lowest precedence
        return list(SCOPE_PRECEDENCE[scope_idx:])
