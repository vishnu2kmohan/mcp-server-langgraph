"""Capability Scope Hierarchy for ADR-0092.

Defines the 7-level scope hierarchy for capability resolution.
Scopes determine where tools, skills, and memory configurations come from,
with higher-precedence scopes overriding lower-precedence ones.

Usage:
    from mcp_server_langgraph.core.scopes import (
        CapabilityScope,
        SCOPE_PRECEDENCE,
        get_precedence,
        has_higher_precedence,
    )

    # Check if task scope overrides user scope
    if has_higher_precedence(CapabilityScope.TASK, CapabilityScope.USER):
        # Use task-scoped configuration
        ...

ADR Reference: adr/adr-0092-hierarchical-capability-architecture.md
"""

from __future__ import annotations

from enum import StrEnum


class CapabilityScope(StrEnum):
    """7-level capability scope hierarchy.

    Scopes from broadest to most specific:
    - ENTERPRISE: Organization-wide defaults (/etc/studio/STUDIO.md)
    - ORGANIZATION: Org-specific config (.studio/orgs/{org_id}/STUDIO.md)
    - PROJECT: Project-level config (./STUDIO.md)
    - TEAM: Team-specific config (.studio/teams/{team_id}/STUDIO.md)
    - USER: User preferences (~/.studio/STUDIO.md)
    - SESSION: In-memory session context
    - TASK: Current task execution context (highest precedence)

    Higher-precedence scopes override lower-precedence ones when resolving
    capabilities (tools, skills, memory).
    """

    ENTERPRISE = "enterprise"
    ORGANIZATION = "organization"
    PROJECT = "project"
    TEAM = "team"
    USER = "user"
    SESSION = "session"
    TASK = "task"


# Precedence order from highest (index 0) to lowest (index 6)
# TASK overrides SESSION overrides USER, etc.
SCOPE_PRECEDENCE: tuple[CapabilityScope, ...] = (
    CapabilityScope.TASK,
    CapabilityScope.SESSION,
    CapabilityScope.USER,
    CapabilityScope.TEAM,
    CapabilityScope.PROJECT,
    CapabilityScope.ORGANIZATION,
    CapabilityScope.ENTERPRISE,
)


def get_precedence(scope: CapabilityScope) -> int:
    """Get the precedence value for a scope.

    Lower values = higher precedence.
    TASK has precedence 0 (highest), ENTERPRISE has precedence 6 (lowest).

    Args:
        scope: The CapabilityScope to check

    Returns:
        Integer precedence value (0 = highest, 6 = lowest)
    """
    return SCOPE_PRECEDENCE.index(scope)


def has_higher_precedence(scope_a: CapabilityScope, scope_b: CapabilityScope) -> bool:
    """Check if scope_a has higher precedence than scope_b.

    Args:
        scope_a: First scope to compare
        scope_b: Second scope to compare

    Returns:
        True if scope_a has higher precedence (lower index) than scope_b.
        False if scope_a has equal or lower precedence.

    Example:
        >>> has_higher_precedence(CapabilityScope.TASK, CapabilityScope.USER)
        True
        >>> has_higher_precedence(CapabilityScope.USER, CapabilityScope.TASK)
        False
        >>> has_higher_precedence(CapabilityScope.USER, CapabilityScope.USER)
        False
    """
    return get_precedence(scope_a) < get_precedence(scope_b)
