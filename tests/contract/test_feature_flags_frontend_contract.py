"""
Contract test to ensure frontend feature flags are exposed by backend.

This test prevents the bug where a feature flag is used in frontend code
but not returned by the backend's get_ui_features_for_role() method.

The bug manifests as features appearing "disabled" in the UI even when
the environment variable is set to true, because the frontend never
receives the flag value from the API.

Example: FF_ENABLE_SKILLS_MARKETPLACE=true was set, but the Skills UI
showed "Disabled" because get_ui_features_for_role() didn't include
the enable_skills_marketplace flag in its return dictionary.
"""

import re
import subprocess
from pathlib import Path

import pytest

from mcp_server_langgraph.core.feature_flags import get_feature_flags

pytestmark = pytest.mark.contract

# Feature flags that MUST be exposed to frontend
# These are referenced in frontend code via isEnabled() or useFeatureFlag()
# If a flag is used in frontend but not in this list, the dynamic scan will catch it
FRONTEND_REQUIRED_FLAGS = {
    # Skills Marketplace Features (ADR-0072)
    "skills_marketplace",
    "skills_system",
    # Core UI features
    "workflows",
    "sessions",
    "cost_dashboard",
    "observability",
    "code_export",
    "interactive_artifacts",
    "slash_commands",
    "url_content_fetch",
    # AI features
    "ai_suggestions",
    "ai_onboarding",
    "ai_empty_states",
    "ai_empty_state",  # Singular alias used by useAIEmptyState.ts
    "ai_nudges",
    "nudges",  # Alias for frontend compatibility
    "ai_disclosure",
    "ai_error_recovery",
    "ai_ux",
    "genui",
    # Canvas features
    "studio_canvas_shell",
    "canvas_editable",
    "canvas_agents",
    "canvas_ai_palette",
    # DevTools
    "devtools_panel",
    # StudioShell features
    "kb_focus",
    "enhanced_model_selector",
    "show_chat_avatars",
    "panel_zoom",
    "mobile_drawer",
    "command_palette",
    "keyboard_shortcuts",
    "theme_customization",
    "confirmation_dialogs",
    # Onboarding & surveys (App.tsx)
    "onboarding_wizard",
    "guided_tour",
    "sus_survey",
    # Studio AI intelligence (useAIIntelligenceConfig.ts)
    "studio_ai",
    "agent_hitl",
    "hitl_ai",
    "ai_ux_websocket",
    # Orchestrator
    "orchestrator_selector",
    # Plan features
    "plan_search",
    "plan_templates",
    # Workflow from chat
    "workflow_from_chat",
    # Admin Dashboard AI Quality (Phase 5)
    "ai_quality_metrics",
    # Markdown References ([[type:qualifier:id]] syntax)
    "markdown_references",
}


@pytest.mark.contract
class TestFeatureFlagsFrontendContract:
    """Contract tests for feature flag exposure to frontend."""

    def test_all_required_frontend_flags_are_exposed(self) -> None:
        """
        Verify all feature flags used in frontend are returned by get_ui_features_for_role().

        This test prevents silent failures where frontend checks for a flag that
        the backend never returns, causing features to appear disabled.
        """
        flags = get_feature_flags()
        ui_features_admin = flags.get_ui_features_for_role("admin")
        ui_features_user = flags.get_ui_features_for_role("user")

        # Combine all exposed flags from both roles
        exposed_flags = set(ui_features_admin.keys()) | set(ui_features_user.keys())

        # Find missing flags
        missing = FRONTEND_REQUIRED_FLAGS - exposed_flags

        assert not missing, (
            f"Feature flags used in frontend but NOT exposed by backend:\n"
            f"  {sorted(missing)}\n\n"
            f"Fix: Add these flags to get_ui_features_for_role() in feature_flags.py\n"
            f"Location: src/mcp_server_langgraph/core/feature_flags.py:1776"
        )

    def test_skills_marketplace_flag_exposed(self) -> None:
        """
        Specific regression test for skills marketplace flag.

        This was the original bug: FF_ENABLE_SKILLS_MARKETPLACE=true was set,
        but SkillsPage.tsx checked isEnabled() with a flag name that wasn't
        in get_ui_features_for_role().

        Fixed: Now uses standard naming convention (skills_marketplace, not enable_skills_marketplace).
        """
        flags = get_feature_flags()
        ui_features = flags.get_ui_features_for_role("admin")

        assert "skills_marketplace" in ui_features, (
            "skills_marketplace must be exposed to frontend. SkillsPage.tsx:78 depends on this flag."
        )

        assert "skills_system" in ui_features, (
            "skills_system must be exposed to frontend. Skills system functionality depends on this flag."
        )

    def test_admin_and_user_roles_have_consistent_flag_keys(self) -> None:
        """
        Verify admin and user roles return the same flag keys (values may differ).

        This prevents bugs where a flag is only exposed to one role,
        causing frontend code to behave unexpectedly based on role.
        """
        flags = get_feature_flags()
        admin_flags = set(flags.get_ui_features_for_role("admin").keys())
        user_flags = set(flags.get_ui_features_for_role("user").keys())

        # All flags should be present in both roles (values may differ)
        admin_only = admin_flags - user_flags
        user_only = user_flags - admin_flags

        assert not admin_only, f"Flags only exposed to admin: {admin_only}"
        assert not user_only, f"Flags only exposed to user: {user_only}"

    @pytest.mark.skipif(
        not Path("src/mcp_server_langgraph/studio/frontend/src").exists(),
        reason="Frontend directory not found",
    )
    def test_scan_frontend_for_undocumented_flag_usage(self) -> None:
        """
        Dynamically scan frontend code to find all isEnabled() calls and verify exposure.

        This catches cases where a developer adds a flag check in frontend code
        but forgets to add it to get_ui_features_for_role() in the backend.
        """
        frontend_dir = Path("src/mcp_server_langgraph/studio/frontend/src")

        # Find all isEnabled("flag_name") calls in frontend production code
        # Exclude test files (*.test.*, *.spec.*, __tests__) to avoid false positives
        # from mock data in test files
        result = subprocess.run(
            [
                "grep",
                "-rhoE",
                "--include=*.ts",
                "--include=*.tsx",
                "--exclude=*.test.*",
                "--exclude=*.spec.*",
                "--exclude-dir=__tests__",
                "--exclude-dir=mocks",
                r'isEnabled\(["\x27]([^"\x27]+)["\x27]\)',
                str(frontend_dir),
            ],
            capture_output=True,
            text=True,
            check=False,
        )

        if result.returncode != 0 and not result.stdout:
            pytest.skip("No isEnabled() calls found or grep failed")

        # Extract flag names from matches like: isEnabled("flag_name")
        frontend_flags = set(re.findall(r'isEnabled\(["\']([^"\']+)["\']\)', result.stdout))

        if not frontend_flags:
            pytest.skip("No isEnabled() calls found in frontend")

        # Get exposed flags from backend
        flags = get_feature_flags()
        ui_features = flags.get_ui_features_for_role("admin")
        exposed_flags = set(ui_features.keys())

        # Find gaps - flags used in frontend but not exposed
        missing = frontend_flags - exposed_flags

        if missing:
            # Format as actionable error message
            pytest.fail(
                f"Frontend uses these flags that backend doesn't expose:\n"
                f"  {sorted(missing)}\n\n"
                f"Either:\n"
                f"  1. Add to get_ui_features_for_role() in feature_flags.py\n"
                f"  2. Or fix the frontend to use the correct flag name\n\n"
                f"Note: Add new flags to FRONTEND_REQUIRED_FLAGS in this test file"
            )

    def test_no_duplicate_flag_aliases(self) -> None:
        """
        Verify there are no conflicting flag aliases that could cause confusion.

        Example: 'ai_nudges' and 'nudges' should both point to the same value.
        """
        flags = get_feature_flags()
        ui_features = flags.get_ui_features_for_role("admin")

        # Known aliases - these should have the same value
        aliases = [
            ("ai_nudges", "nudges"),
            ("ai_persona_analysis", "persona_analysis"),
        ]

        for primary, alias in aliases:
            if primary in ui_features and alias in ui_features:
                assert ui_features[primary] == ui_features[alias], (
                    f"Alias mismatch: {primary}={ui_features[primary]} but {alias}={ui_features[alias]}"
                )

    def test_exposed_flag_names_follow_convention(self) -> None:
        """
        Enforce naming convention: exposed flag names should NOT use enable_ prefix.

        Convention in this codebase:
        - Backend field names: enable_skills_marketplace, enable_workflows_feature
        - Exposed API names: skills_marketplace, workflows (no enable_ prefix)

        This prevents the common bug where frontend uses a different naming
        convention than what the backend exposes.

        Regression prevention: Skills UI "disabled" bug (2025-01-10)
        """
        flags = get_feature_flags()
        ui_features = flags.get_ui_features_for_role("admin")

        # Find flags that violate the naming convention
        violations = [k for k in ui_features.keys() if k.startswith("enable_")]

        assert not violations, (
            f"Exposed flag names should NOT use 'enable_' prefix.\n"
            f"Violations: {sorted(violations)}\n\n"
            f"Convention:\n"
            f"  - Backend field: enable_skills_marketplace\n"
            f"  - Exposed name: skills_marketplace (no enable_ prefix)\n\n"
            f"Fix: In get_ui_features_for_role(), use short names like:\n"
            f'  "skills_marketplace": self.enable_skills_marketplace'
        )
