"""
Meta-tests for Feature Flag Consistency.

TDD Cycle: RED -> GREEN -> REFACTOR

These tests validate that feature flags are properly wired between:
1. Backend FeatureFlags class (source of truth)
2. API endpoints that expose flags to frontend
3. Frontend code that consumes flags

Bug Context:
- Frontend used `enable_studio_ai` but backend returned `studio_ai`
- Multiple flags had naming mismatches causing features to appear disabled
- Some flags expected by frontend were not returned by API

Reference: Feature Flag Management System (core/feature_flags.py)
"""

import gc

import pytest

# Mark as meta test (validates codebase quality, not functionality)
pytestmark = [
    pytest.mark.meta,
    pytest.mark.unit,
]


@pytest.mark.xdist_group(name="test_feature_flag_consistency")
class TestOrchestratorRegistryConsistency:
    """Verify orchestrator registry feature flags are in AGENT_FEATURE_FLAGS."""

    def teardown_method(self) -> None:
        """Force GC to prevent mock accumulation in xdist workers."""
        gc.collect()

    def test_all_orchestrator_flags_in_agent_feature_flags(self):
        """
        GIVEN: ORCHESTRATOR_REGISTRY with feature_flag for each orchestrator
        WHEN: Comparing with AGENT_FEATURE_FLAGS list
        THEN: All orchestrator flags should be present

        Bug Context: Missing orchestrator flags caused them to show as disabled
        """
        from mcp_server_langgraph.agents.registry import ORCHESTRATOR_REGISTRY
        from mcp_server_langgraph.api.v1.agents import AGENT_FEATURE_FLAGS

        missing_flags = []
        for name, info in ORCHESTRATOR_REGISTRY.items():
            if info.feature_flag not in AGENT_FEATURE_FLAGS:
                missing_flags.append(f"{name}: {info.feature_flag}")

        assert not missing_flags, (
            f"Orchestrator flags missing from AGENT_FEATURE_FLAGS:\n"
            f"  {chr(10).join(missing_flags)}\n"
            f"Add these to AGENT_FEATURE_FLAGS in api/v1/agents.py"
        )

    def test_agent_feature_flags_exist_in_feature_flags_class(self):
        """
        GIVEN: AGENT_FEATURE_FLAGS list
        WHEN: Checking each flag exists in FeatureFlags class
        THEN: All listed flags should be defined attributes

        Bug Context: Typos in flag names would cause AttributeError
        """
        from mcp_server_langgraph.api.v1.agents import AGENT_FEATURE_FLAGS
        from mcp_server_langgraph.core.feature_flags import FeatureFlags

        invalid_flags = []
        for flag_name in AGENT_FEATURE_FLAGS:
            if not hasattr(FeatureFlags, "__annotations__") or flag_name not in FeatureFlags.model_fields:
                # Check if it's a valid field
                try:
                    FeatureFlags.model_fields[flag_name]
                except KeyError:
                    invalid_flags.append(flag_name)

        assert not invalid_flags, (
            f"AGENT_FEATURE_FLAGS contains invalid flag names:\n"
            f"  {chr(10).join(invalid_flags)}\n"
            f"These flags don't exist in FeatureFlags class"
        )


@pytest.mark.xdist_group(name="test_feature_flag_consistency")
class TestUIFeaturesConsistency:
    """Verify UI features returned by API match what frontend expects."""

    def teardown_method(self) -> None:
        """Force GC to prevent mock accumulation in xdist workers."""
        gc.collect()

    def test_ui_features_include_all_enable_prefixed_flags(self):
        """
        GIVEN: Frontend code using isEnabled('enable_xxx') pattern
        WHEN: Calling get_ui_features_for_role()
        THEN: Should include both 'enable_xxx' AND 'xxx' variants for compatibility

        Bug Context: Frontend used enable_studio_ai but backend returned studio_ai
        Note: This test documents the naming convention - frontend should use
        the same names as backend (without enable_ prefix for UI flags)
        """
        from mcp_server_langgraph.core.feature_flags import feature_flags

        ui_features = feature_flags.get_ui_features_for_role("admin")

        # These are the key UI flags that MUST be present
        # (using the naming convention from get_ui_features_for_role)
        required_ui_flags = [
            "studio_ai",
            "agent_hitl",
            "hitl_ai",
            "genui",
            "ai_onboarding",
            "ai_disclosure",
            "ai_suggestions",
            "cost_dashboard",
            "observability",
            "workflows",
            "sessions",
        ]

        missing = [flag for flag in required_ui_flags if flag not in ui_features]
        assert not missing, f"UI features missing: {missing}"

    def test_ai_ux_flags_exposed_to_frontend(self):
        """
        GIVEN: AI UX feature flags in FeatureFlags class
        WHEN: Calling get_ui_features_for_role()
        THEN: AI UX flags should be exposed for frontend consumption

        Bug Context: enable_ai_ux and enable_ai_ux_websocket were not exposed
        """
        from mcp_server_langgraph.core.feature_flags import feature_flags

        ui_features = feature_flags.get_ui_features_for_role("admin")

        # AI UX related flags that should be exposed
        ai_ux_flags = [
            "ai_ux",  # Master AI UX toggle
            "ai_ux_websocket",  # WebSocket for AI UX
            "ai_ux_streaming",  # Streaming for AI UX
        ]

        missing = [flag for flag in ai_ux_flags if flag not in ui_features]
        assert not missing, (
            f"AI UX flags missing from UI features: {missing}\nAdd these to get_ui_features_for_role() in feature_flags.py"
        )


@pytest.mark.xdist_group(name="test_feature_flag_consistency")
class TestFeatureFlagNamingConventions:
    """Verify consistent naming conventions across the codebase."""

    def teardown_method(self) -> None:
        """Force GC to prevent mock accumulation in xdist workers."""
        gc.collect()

    def test_ui_features_use_consistent_naming(self):
        """
        GIVEN: get_ui_features_for_role() returns a dict
        WHEN: Checking key naming patterns
        THEN: Keys should not have 'enable_' prefix (stripped for frontend)

        Design Decision: UI features strip 'enable_' prefix for cleaner frontend code
        """
        from mcp_server_langgraph.core.feature_flags import feature_flags

        ui_features = feature_flags.get_ui_features_for_role("admin")

        # All keys should NOT start with 'enable_' (that's the internal name)
        enable_prefixed = [key for key in ui_features.keys() if key.startswith("enable_")]

        # Allow these specific exceptions (some UI flags intentionally keep prefix)
        # If this list grows, reconsider the naming convention
        allowed_exceptions: list[str] = []

        unexpected = [key for key in enable_prefixed if key not in allowed_exceptions]
        assert not unexpected, (
            f"UI features should not use 'enable_' prefix:\n"
            f"  {chr(10).join(unexpected)}\n"
            f"Either add to allowed_exceptions or rename in get_ui_features_for_role()"
        )

    def test_feature_flags_class_uses_snake_case(self):
        """
        GIVEN: FeatureFlags class field names
        WHEN: Checking naming convention
        THEN: All should be snake_case (lowercase with underscores)
        """
        from mcp_server_langgraph.core.feature_flags import FeatureFlags

        invalid_names = []
        for field_name in FeatureFlags.model_fields.keys():
            # Check for common violations
            if field_name != field_name.lower():
                invalid_names.append(f"{field_name} (contains uppercase)")
            if "-" in field_name:
                invalid_names.append(f"{field_name} (contains hyphen)")

        assert not invalid_names, f"Feature flags should be snake_case: {invalid_names}"
