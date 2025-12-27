"""
Contract Tests: User /me Endpoint - Frontend Contract

These tests ensure the backend /api/v1/me response matches the frontend expectations.
Prevents module ID drift and ensures API contract stability.

Sprint 4: Added for StudioShell navigation auto-loading fix.
"""

import pytest

from src.mcp_server_langgraph.api.v1.user import PERSONA_VISIBLE_MODULES

pytestmark = pytest.mark.contract


# Frontend NAV_ITEMS IDs (must stay in sync with ActivityBar.tsx NAV_ITEMS)
# This is the authoritative list from ActivityBar.tsx KNOWN_NAV_IDS
FRONTEND_NAV_ITEM_IDS = {
    # Core Work
    "projects",
    "chat",
    "workflows",
    # AI & Data
    "agents",
    "mcp",
    "vectors",
    "connections",
    "files",
    # Observability
    "traces",
    "observability",
    "cost",
    # Admin
    "admin",
    "audit",
    "compliance",
    # Bottom items
    "help",
    "settings",
}

# Legacy IDs that should NOT appear in visible_modules
DEPRECATED_MODULE_IDS = {
    "flows",  # Renamed to "workflows"
    "costs",  # Renamed to "cost"
    "metrics",  # Renamed to "observability"
}


@pytest.mark.contract
class TestUserMeFrontendContract:
    """
    Contract tests ensuring backend visible_modules match frontend NAV_ITEMS.

    These tests prevent:
    - Module ID drift (backend using "flows" while frontend expects "workflows")
    - Missing modules (backend returns IDs that frontend doesn't recognize)
    - Breaking changes to the API contract
    """

    def test_all_visible_modules_are_valid_nav_items(self):
        """
        Every module ID in PERSONA_VISIBLE_MODULES must exist in frontend NAV_ITEMS.

        This prevents returning IDs that the frontend can't render.
        """
        for persona, modules in PERSONA_VISIBLE_MODULES.items():
            for module_id in modules:
                assert module_id in FRONTEND_NAV_ITEM_IDS, (
                    f"Persona '{persona}' has module '{module_id}' which is not a valid "
                    f"frontend NAV_ITEM ID. Valid IDs: {sorted(FRONTEND_NAV_ITEM_IDS)}"
                )

    def test_no_deprecated_module_ids(self):
        """
        No deprecated module IDs should appear in visible_modules.

        This catches cases where old IDs slip back in.
        """
        for persona, modules in PERSONA_VISIBLE_MODULES.items():
            for deprecated_id in DEPRECATED_MODULE_IDS:
                assert deprecated_id not in modules, (
                    f"Persona '{persona}' uses deprecated module ID '{deprecated_id}'. Use the normalized ID instead."
                )

    def test_module_ids_are_normalized(self):
        """
        Verify specific normalizations are in place:
        - "workflows" instead of "flows"
        - "cost" instead of "costs"
        - "observability" instead of "metrics"
        """
        # Check admin has normalized IDs
        admin_modules = PERSONA_VISIBLE_MODULES.get("admin", [])

        # Should have "workflows" not "flows"
        assert "workflows" in admin_modules, "Admin should have 'workflows' module"
        assert "flows" not in admin_modules, "Admin should not have deprecated 'flows'"

        # Should have "cost" not "costs"
        assert "cost" in admin_modules, "Admin should have 'cost' module"
        assert "costs" not in admin_modules, "Admin should not have deprecated 'costs'"

        # Should have "observability"
        assert "observability" in admin_modules, "Admin should have 'observability' module"

    def test_admin_has_full_access(self):
        """Admin persona should have access to all core modules."""
        admin_modules = set(PERSONA_VISIBLE_MODULES.get("admin", []))

        # Core modules every admin should have
        required_admin_modules = {
            "projects",
            "chat",
            "workflows",
            "agents",
            "mcp",
            "traces",
            "cost",
            "admin",
            "settings",
            "help",
        }

        missing = required_admin_modules - admin_modules
        assert not missing, f"Admin is missing required modules: {missing}"

    def test_bob_has_limited_access(self):
        """Bob (end user) should have limited access."""
        bob_modules = set(PERSONA_VISIBLE_MODULES.get("bob", []))

        # Bob should NOT have admin modules
        admin_only_modules = {"admin", "audit", "compliance"}
        has_admin = bob_modules & admin_only_modules
        assert not has_admin, f"Bob should not have admin modules: {has_admin}"

        # Bob SHOULD have basic modules
        assert "chat" in bob_modules, "Bob should have chat access"
        assert "projects" in bob_modules, "Bob should have projects access"
        assert "help" in bob_modules, "Bob should have help access"

    def test_alice_builder_has_dev_modules(self):
        """Alice Builder (developer) should have development modules."""
        alice_modules = set(PERSONA_VISIBLE_MODULES.get("alice-builder", []))

        # Developer should have these
        required_dev_modules = {"chat", "workflows", "agents", "mcp"}
        missing = required_dev_modules - alice_modules
        assert not missing, f"Alice Builder is missing required modules: {missing}"

    def test_persona_visible_modules_uses_list_type(self):
        """
        Visible modules should be lists (ordered) not sets.

        Order matters for UI rendering.
        """
        for persona, modules in PERSONA_VISIBLE_MODULES.items():
            assert isinstance(modules, list), (
                f"Persona '{persona}' visible_modules should be a list, got {type(modules).__name__}"
            )

    def test_no_duplicate_modules_per_persona(self):
        """Each persona should not have duplicate module IDs."""
        for persona, modules in PERSONA_VISIBLE_MODULES.items():
            seen = set()
            for module_id in modules:
                assert module_id not in seen, f"Persona '{persona}' has duplicate module ID '{module_id}'"
                seen.add(module_id)
