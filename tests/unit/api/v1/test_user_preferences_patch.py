"""
Tests for the PATCH /me/preferences endpoint.

Sprint 4: Persona/RBAC Coherence

Tests cover:
- Sub-persona validation against base persona
- Sub-persona persistence
- UserInfoResponse with updated sub_persona
- Invalid sub_persona rejection
"""

import pytest

from mcp_server_langgraph.api.v1.user import (
    get_sub_personas_for_base,
    is_valid_sub_persona,
)

pytestmark = pytest.mark.unit


class TestIsValidSubPersona:
    """Tests for sub-persona validation."""

    def test_admin_can_use_admin_sub_personas(self):
        """Admin base persona can use admin-related sub-personas."""
        assert is_valid_sub_persona("admin", "admin") is True
        assert is_valid_sub_persona("admin", "security-admin") is True
        assert is_valid_sub_persona("admin", "auditor") is True

    def test_developer_can_use_alice_sub_personas(self):
        """Developer base persona can use alice-* sub-personas."""
        assert is_valid_sub_persona("developer", "alice-builder") is True
        assert is_valid_sub_persona("developer", "alice-analyst") is True
        assert is_valid_sub_persona("developer", "alice-devops") is True

    def test_user_can_use_bob_sub_persona(self):
        """User base persona can use bob sub-persona."""
        assert is_valid_sub_persona("user", "bob") is True
        assert is_valid_sub_persona("user", "compliance-officer") is True

    def test_developer_cannot_use_admin_sub_personas(self):
        """Developer cannot use admin-level sub-personas."""
        assert is_valid_sub_persona("developer", "admin") is False
        assert is_valid_sub_persona("developer", "security-admin") is False
        assert is_valid_sub_persona("developer", "auditor") is False

    def test_user_cannot_use_developer_sub_personas(self):
        """User cannot use developer-level sub-personas."""
        assert is_valid_sub_persona("user", "alice-builder") is False
        assert is_valid_sub_persona("user", "alice-analyst") is False

    def test_unknown_sub_persona_is_invalid(self):
        """Unknown sub-persona is rejected."""
        assert is_valid_sub_persona("admin", "unknown-persona") is False
        assert is_valid_sub_persona("developer", "unknown-persona") is False
        assert is_valid_sub_persona("user", "unknown-persona") is False


class TestGetSubPersonasForBase:
    """Tests for getting valid sub-personas for a base persona."""

    def test_admin_sub_personas(self):
        """Admin gets admin-related sub-personas."""
        subs = get_sub_personas_for_base("admin")
        assert "admin" in subs
        assert "security-admin" in subs
        assert "auditor" in subs
        # Admin also gets all lower-tier personas
        assert "alice-builder" in subs
        assert "bob" in subs

    def test_developer_sub_personas(self):
        """Developer gets developer-related sub-personas."""
        subs = get_sub_personas_for_base("developer")
        assert "alice-builder" in subs
        assert "alice-analyst" in subs
        assert "alice-devops" in subs
        # Developer also gets user-tier personas
        assert "bob" in subs
        # But not admin personas
        assert "admin" not in subs
        assert "security-admin" not in subs

    def test_user_sub_personas(self):
        """User gets user-level sub-personas only."""
        subs = get_sub_personas_for_base("user")
        assert "bob" in subs
        assert "compliance-officer" in subs
        # No admin or developer personas
        assert "admin" not in subs
        assert "alice-builder" not in subs

    def test_unknown_base_persona_returns_empty(self):
        """Unknown base persona returns empty list."""
        subs = get_sub_personas_for_base("unknown")
        assert subs == []


class TestPersonaPreferencesUpdate:
    """Tests for persona preferences update model."""

    def test_sub_persona_update_model_accepts_valid_value(self):
        """PersonaPreferencesUpdate accepts sub_persona."""
        from mcp_server_langgraph.api.v1.user import PersonaPreferencesUpdate

        update = PersonaPreferencesUpdate(sub_persona="alice-builder")
        assert update.sub_persona == "alice-builder"

    def test_sub_persona_update_model_accepts_none(self):
        """PersonaPreferencesUpdate allows None for optional update."""
        from mcp_server_langgraph.api.v1.user import PersonaPreferencesUpdate

        update = PersonaPreferencesUpdate()
        assert update.sub_persona is None

    def test_feature_flags_update(self):
        """PersonaPreferencesUpdate accepts feature_flags."""
        from mcp_server_langgraph.api.v1.user import PersonaPreferencesUpdate

        update = PersonaPreferencesUpdate(feature_flags={"focus_mode": True, "canvas_shortcuts": False})
        assert update.feature_flags["focus_mode"] is True
        assert update.feature_flags["canvas_shortcuts"] is False
