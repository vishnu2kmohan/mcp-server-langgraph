"""
Tests for the extended /me endpoint with persona fields.

Sprint 4: Persona/RBAC Coherence

Tests cover:
- base_persona and sub_persona in response
- visible_modules based on persona
- feature_flags exposure
- api_version for client compatibility
"""

import pytest

from mcp_server_langgraph.api.v1.user import (
    compute_persona,
    get_visible_modules_for_persona,
    UserInfoResponse,
    PERSONA_VISIBLE_MODULES,
)

pytestmark = pytest.mark.unit


class TestComputePersona:
    """Tests for compute_persona function."""

    def test_admin_role_returns_admin(self):
        """Admin role should return admin persona."""
        assert compute_persona(["admin"]) == "admin"

    def test_developer_role_returns_developer(self):
        """Developer role should return developer persona."""
        assert compute_persona(["developer"]) == "developer"

    def test_no_special_role_returns_user(self):
        """No special roles should return user persona."""
        assert compute_persona([]) == "user"
        assert compute_persona(["viewer"]) == "user"

    def test_admin_takes_priority(self):
        """Admin should take priority over developer."""
        assert compute_persona(["admin", "developer"]) == "admin"

    def test_developer_takes_priority_over_user(self):
        """Developer should take priority over user."""
        assert compute_persona(["developer", "viewer"]) == "developer"


class TestGetVisibleModulesForPersona:
    """Tests for get_visible_modules_for_persona function."""

    def test_admin_gets_all_modules(self):
        """Admin persona should have access to all modules."""
        modules = get_visible_modules_for_persona("admin")
        assert "admin" in modules
        assert "chat" in modules
        assert "audit" in modules
        assert "compliance" in modules
        assert len(modules) >= 10  # Admin has many modules

    def test_alice_builder_gets_dev_modules(self):
        """Alice builder should have development modules."""
        modules = get_visible_modules_for_persona("alice-builder")
        assert "chat" in modules
        assert "flows" in modules
        assert "mcp" in modules
        assert "agents" in modules
        assert "admin" not in modules  # No admin access

    def test_bob_gets_limited_modules(self):
        """Bob (standard user) should have limited modules."""
        modules = get_visible_modules_for_persona("bob")
        assert "chat" in modules
        assert "projects" in modules
        assert "admin" not in modules
        assert "audit" not in modules

    def test_unknown_persona_gets_empty_list(self):
        """Unknown persona should get empty list."""
        modules = get_visible_modules_for_persona("unknown-persona")
        assert modules == []

    def test_auditor_gets_audit_modules(self):
        """Auditor should have audit-related modules."""
        modules = get_visible_modules_for_persona("auditor")
        assert "audit" in modules
        assert "compliance" in modules
        assert "help" in modules
        assert "chat" not in modules  # Auditor doesn't need chat


class TestUserInfoResponseModel:
    """Tests for UserInfoResponse model."""

    def test_response_includes_api_version(self):
        """Response should include api_version field."""
        response = UserInfoResponse(
            user_id="user:test",
            username="test",
            persona="user",
            roles=[],
        )
        assert hasattr(response, "api_version")
        assert response.api_version == "2"

    def test_response_includes_base_persona(self):
        """Response should include base_persona field."""
        response = UserInfoResponse(
            user_id="user:test",
            username="test",
            persona="admin",
            roles=["admin"],
        )
        assert response.persona == "admin"

    def test_response_includes_sub_persona(self):
        """Response should include optional sub_persona field."""
        response = UserInfoResponse(
            user_id="user:test",
            username="test",
            persona="developer",
            sub_persona="alice-builder",
            roles=["developer"],
        )
        assert response.sub_persona == "alice-builder"

    def test_response_includes_visible_modules(self):
        """Response should include visible_modules list."""
        response = UserInfoResponse(
            user_id="user:test",
            username="test",
            persona="admin",
            visible_modules=["chat", "admin", "audit"],
            roles=["admin"],
        )
        assert "chat" in response.visible_modules
        assert "admin" in response.visible_modules

    def test_response_includes_feature_flags(self):
        """Response should include feature_flags dict."""
        response = UserInfoResponse(
            user_id="user:test",
            username="test",
            persona="user",
            feature_flags={"focus_mode": True, "canvas_shortcuts": False},
            roles=[],
        )
        assert response.feature_flags["focus_mode"] is True
        assert response.feature_flags["canvas_shortcuts"] is False


class TestPersonaVisibleModulesMapping:
    """Tests for PERSONA_VISIBLE_MODULES constant."""

    def test_all_personas_have_mapping(self):
        """All 8 personas should have visible modules mapping."""
        expected_personas = [
            "admin",
            "security-admin",
            "auditor",
            "alice-builder",
            "alice-analyst",
            "alice-devops",
            "compliance-officer",
            "bob",
        ]
        for persona in expected_personas:
            assert persona in PERSONA_VISIBLE_MODULES, f"Missing mapping for {persona}"
            assert len(PERSONA_VISIBLE_MODULES[persona]) > 0, f"Empty modules for {persona}"

    def test_help_module_available_to_all(self):
        """Help module should be available to all personas."""
        for persona, modules in PERSONA_VISIBLE_MODULES.items():
            assert "help" in modules, f"Help missing for {persona}"
