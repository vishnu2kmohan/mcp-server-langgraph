"""Tests for CapabilityScope enum.

TDD: These tests define the contract for the capability scope hierarchy
that determines tool/skill/memory resolution precedence.

ADR-0092: Hierarchical Capability Architecture
"""

from __future__ import annotations

import gc
from enum import StrEnum

import pytest

pytestmark = pytest.mark.unit


@pytest.mark.unit
@pytest.mark.orchestrator
@pytest.mark.xdist_group(name="capability_scope")
class TestCapabilityScopeEnum:
    """Tests for CapabilityScope enum existence and structure."""

    def teardown_method(self) -> None:
        """Force GC to prevent mock accumulation in xdist workers."""
        gc.collect()

    def test_capability_scope_exists(self) -> None:
        """Test that CapabilityScope class exists."""
        from mcp_server_langgraph.core.scopes import CapabilityScope

        assert CapabilityScope is not None

    def test_capability_scope_is_str_enum(self) -> None:
        """Test CapabilityScope is a StrEnum for easy serialization."""
        from mcp_server_langgraph.core.scopes import CapabilityScope

        assert issubclass(CapabilityScope, StrEnum)

    def test_capability_scope_has_seven_levels(self) -> None:
        """Test CapabilityScope has exactly 7 scope levels.

        The 7 levels from broadest to most specific:
        - ENTERPRISE: Organization-wide defaults (/etc/studio/STUDIO.md)
        - ORGANIZATION: Org-specific config (.studio/orgs/{org_id}/STUDIO.md)
        - PROJECT: Project-level config (./STUDIO.md)
        - TEAM: Team-specific config (.studio/teams/{team_id}/STUDIO.md)
        - USER: User preferences (~/.studio/STUDIO.md)
        - SESSION: In-memory session context
        - TASK: Current task execution context (highest precedence)
        """
        from mcp_server_langgraph.core.scopes import CapabilityScope

        scope_values = list(CapabilityScope)
        assert len(scope_values) == 7

    def test_capability_scope_enterprise_level(self) -> None:
        """Test ENTERPRISE scope exists for org-wide defaults."""
        from mcp_server_langgraph.core.scopes import CapabilityScope

        assert hasattr(CapabilityScope, "ENTERPRISE")
        assert CapabilityScope.ENTERPRISE.value == "enterprise"

    def test_capability_scope_organization_level(self) -> None:
        """Test ORGANIZATION scope exists."""
        from mcp_server_langgraph.core.scopes import CapabilityScope

        assert hasattr(CapabilityScope, "ORGANIZATION")
        assert CapabilityScope.ORGANIZATION.value == "organization"

    def test_capability_scope_project_level(self) -> None:
        """Test PROJECT scope exists."""
        from mcp_server_langgraph.core.scopes import CapabilityScope

        assert hasattr(CapabilityScope, "PROJECT")
        assert CapabilityScope.PROJECT.value == "project"

    def test_capability_scope_team_level(self) -> None:
        """Test TEAM scope exists."""
        from mcp_server_langgraph.core.scopes import CapabilityScope

        assert hasattr(CapabilityScope, "TEAM")
        assert CapabilityScope.TEAM.value == "team"

    def test_capability_scope_user_level(self) -> None:
        """Test USER scope exists."""
        from mcp_server_langgraph.core.scopes import CapabilityScope

        assert hasattr(CapabilityScope, "USER")
        assert CapabilityScope.USER.value == "user"

    def test_capability_scope_session_level(self) -> None:
        """Test SESSION scope exists."""
        from mcp_server_langgraph.core.scopes import CapabilityScope

        assert hasattr(CapabilityScope, "SESSION")
        assert CapabilityScope.SESSION.value == "session"

    def test_capability_scope_task_level(self) -> None:
        """Test TASK scope exists (highest precedence)."""
        from mcp_server_langgraph.core.scopes import CapabilityScope

        assert hasattr(CapabilityScope, "TASK")
        assert CapabilityScope.TASK.value == "task"


@pytest.mark.unit
@pytest.mark.orchestrator
@pytest.mark.xdist_group(name="capability_scope_precedence")
class TestCapabilityScopePrecedence:
    """Tests for CapabilityScope precedence ordering."""

    def teardown_method(self) -> None:
        """Force GC to prevent mock accumulation in xdist workers."""
        gc.collect()

    def test_scope_precedence_list_exists(self) -> None:
        """Test SCOPE_PRECEDENCE list is defined."""
        from mcp_server_langgraph.core.scopes import SCOPE_PRECEDENCE

        assert SCOPE_PRECEDENCE is not None
        assert isinstance(SCOPE_PRECEDENCE, (list, tuple))

    def test_scope_precedence_has_all_scopes(self) -> None:
        """Test precedence list contains all 7 scopes."""
        from mcp_server_langgraph.core.scopes import CapabilityScope, SCOPE_PRECEDENCE

        assert len(SCOPE_PRECEDENCE) == 7
        for scope in CapabilityScope:
            assert scope in SCOPE_PRECEDENCE

    def test_task_has_highest_precedence(self) -> None:
        """Test TASK scope has highest precedence (first in list)."""
        from mcp_server_langgraph.core.scopes import CapabilityScope, SCOPE_PRECEDENCE

        # Highest precedence = first in list (index 0)
        assert SCOPE_PRECEDENCE[0] == CapabilityScope.TASK

    def test_enterprise_has_lowest_precedence(self) -> None:
        """Test ENTERPRISE scope has lowest precedence (last in list)."""
        from mcp_server_langgraph.core.scopes import CapabilityScope, SCOPE_PRECEDENCE

        # Lowest precedence = last in list
        assert SCOPE_PRECEDENCE[-1] == CapabilityScope.ENTERPRISE

    def test_session_higher_than_user(self) -> None:
        """Test SESSION scope has higher precedence than USER."""
        from mcp_server_langgraph.core.scopes import CapabilityScope, SCOPE_PRECEDENCE

        session_idx = SCOPE_PRECEDENCE.index(CapabilityScope.SESSION)
        user_idx = SCOPE_PRECEDENCE.index(CapabilityScope.USER)
        # Lower index = higher precedence
        assert session_idx < user_idx

    def test_project_higher_than_organization(self) -> None:
        """Test PROJECT scope has higher precedence than ORGANIZATION."""
        from mcp_server_langgraph.core.scopes import CapabilityScope, SCOPE_PRECEDENCE

        project_idx = SCOPE_PRECEDENCE.index(CapabilityScope.PROJECT)
        org_idx = SCOPE_PRECEDENCE.index(CapabilityScope.ORGANIZATION)
        assert project_idx < org_idx

    def test_full_precedence_order(self) -> None:
        """Test complete precedence ordering from highest to lowest.

        Expected order (highest to lowest):
        TASK > SESSION > USER > TEAM > PROJECT > ORGANIZATION > ENTERPRISE
        """
        from mcp_server_langgraph.core.scopes import CapabilityScope, SCOPE_PRECEDENCE

        expected_order = [
            CapabilityScope.TASK,
            CapabilityScope.SESSION,
            CapabilityScope.USER,
            CapabilityScope.TEAM,
            CapabilityScope.PROJECT,
            CapabilityScope.ORGANIZATION,
            CapabilityScope.ENTERPRISE,
        ]
        assert list(SCOPE_PRECEDENCE) == expected_order


@pytest.mark.unit
@pytest.mark.orchestrator
@pytest.mark.xdist_group(name="capability_scope_utils")
class TestCapabilityScopeUtilities:
    """Tests for CapabilityScope utility functions."""

    def teardown_method(self) -> None:
        """Force GC to prevent mock accumulation in xdist workers."""
        gc.collect()

    def test_get_precedence_returns_int(self) -> None:
        """Test get_precedence function returns integer precedence."""
        from mcp_server_langgraph.core.scopes import CapabilityScope, get_precedence

        result = get_precedence(CapabilityScope.TASK)
        assert isinstance(result, int)

    def test_task_has_precedence_zero(self) -> None:
        """Test TASK has precedence 0 (highest)."""
        from mcp_server_langgraph.core.scopes import CapabilityScope, get_precedence

        assert get_precedence(CapabilityScope.TASK) == 0

    def test_enterprise_has_precedence_six(self) -> None:
        """Test ENTERPRISE has precedence 6 (lowest)."""
        from mcp_server_langgraph.core.scopes import CapabilityScope, get_precedence

        assert get_precedence(CapabilityScope.ENTERPRISE) == 6

    def test_has_higher_precedence_function(self) -> None:
        """Test has_higher_precedence comparison function."""
        from mcp_server_langgraph.core.scopes import CapabilityScope, has_higher_precedence

        # TASK should have higher precedence than SESSION
        assert has_higher_precedence(CapabilityScope.TASK, CapabilityScope.SESSION) is True
        assert has_higher_precedence(CapabilityScope.SESSION, CapabilityScope.TASK) is False

    def test_has_higher_precedence_equal_scopes(self) -> None:
        """Test has_higher_precedence with equal scopes returns False."""
        from mcp_server_langgraph.core.scopes import CapabilityScope, has_higher_precedence

        # Same scope should not be "higher" than itself
        assert has_higher_precedence(CapabilityScope.USER, CapabilityScope.USER) is False

    def test_scope_from_string(self) -> None:
        """Test creating CapabilityScope from string value."""
        from mcp_server_langgraph.core.scopes import CapabilityScope

        # StrEnum allows direct comparison with strings
        assert CapabilityScope("project") == CapabilityScope.PROJECT
        assert CapabilityScope("task") == CapabilityScope.TASK

    def test_scope_string_value(self) -> None:
        """Test CapabilityScope string value for serialization."""
        from mcp_server_langgraph.core.scopes import CapabilityScope

        # StrEnum values should be usable as strings
        scope = CapabilityScope.PROJECT
        assert str(scope) == "project"
        assert scope == "project"
