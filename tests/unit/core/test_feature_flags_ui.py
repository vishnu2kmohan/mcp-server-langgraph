"""
UI Feature Flags Unit Tests

Tests for UI-specific feature flags per TDD methodology.
Tests written FIRST before implementation (RED phase).

These flags control visibility of UI features based on user roles/tiers.
"""

import gc

import pytest


pytestmark = [
    pytest.mark.unit,
    pytest.mark.core,
]


@pytest.mark.xdist_group(name="test_feature_flags_ui")
class TestUIFeatureFlags:
    """Tests for UI feature flags in FeatureFlags class."""

    def teardown_method(self) -> None:
        """Force GC to prevent mock accumulation in xdist workers."""
        gc.collect()

    def test_enable_workflows_feature_default_true(self) -> None:
        """
        GIVEN default feature flags
        WHEN FeatureFlags is instantiated
        THEN enable_workflows_feature should be True
        """
        from mcp_server_langgraph.core.feature_flags import FeatureFlags

        flags = FeatureFlags()

        assert flags.enable_workflows_feature is True

    def test_enable_sessions_feature_default_true(self) -> None:
        """
        GIVEN default feature flags
        WHEN FeatureFlags is instantiated
        THEN enable_sessions_feature should be True
        """
        from mcp_server_langgraph.core.feature_flags import FeatureFlags

        flags = FeatureFlags()

        assert flags.enable_sessions_feature is True

    def test_enable_cost_dashboard_default_true(self) -> None:
        """
        GIVEN default feature flags
        WHEN FeatureFlags is instantiated
        THEN enable_cost_dashboard should be True
        """
        from mcp_server_langgraph.core.feature_flags import FeatureFlags

        flags = FeatureFlags()

        assert flags.enable_cost_dashboard is True

    def test_enable_cost_dashboard_users_default_false(self) -> None:
        """
        GIVEN default feature flags
        WHEN FeatureFlags is instantiated
        THEN enable_cost_dashboard_users should be False (admin-only by default)
        """
        from mcp_server_langgraph.core.feature_flags import FeatureFlags

        flags = FeatureFlags()

        assert flags.enable_cost_dashboard_users is False

    def test_enable_observability_ui_default_true(self) -> None:
        """
        GIVEN default feature flags
        WHEN FeatureFlags is instantiated
        THEN enable_observability_ui should be True
        """
        from mcp_server_langgraph.core.feature_flags import FeatureFlags

        flags = FeatureFlags()

        assert flags.enable_observability_ui is True

    def test_enable_code_export_default_true(self) -> None:
        """
        GIVEN default feature flags
        WHEN FeatureFlags is instantiated
        THEN enable_code_export should be True
        """
        from mcp_server_langgraph.core.feature_flags import FeatureFlags

        flags = FeatureFlags()

        assert flags.enable_code_export is True

    def test_enable_ai_suggestions_default_true(self) -> None:
        """
        GIVEN default feature flags
        WHEN FeatureFlags is instantiated
        THEN enable_ai_suggestions should be True
        """
        from mcp_server_langgraph.core.feature_flags import FeatureFlags

        flags = FeatureFlags()

        assert flags.enable_ai_suggestions is True

    def test_enable_mcp_websocket_default_false(self) -> None:
        """
        GIVEN default feature flags
        WHEN FeatureFlags is instantiated
        THEN enable_mcp_websocket should be False (experimental)
        """
        from mcp_server_langgraph.core.feature_flags import FeatureFlags

        flags = FeatureFlags()

        assert flags.enable_mcp_websocket is False


@pytest.mark.xdist_group(name="test_feature_flags_ui")
class TestUIFeatureFlagsEnvironmentOverride:
    """Tests for overriding UI feature flags via environment variables."""

    def teardown_method(self) -> None:
        """Force GC to prevent mock accumulation in xdist workers."""
        gc.collect()

    def test_workflows_feature_can_be_disabled_via_env(self, monkeypatch: pytest.MonkeyPatch) -> None:
        """
        GIVEN FF_ENABLE_WORKFLOWS_FEATURE=false in environment
        WHEN FeatureFlags is instantiated
        THEN enable_workflows_feature should be False
        """
        monkeypatch.setenv("FF_ENABLE_WORKFLOWS_FEATURE", "false")

        from mcp_server_langgraph.core.feature_flags import FeatureFlags

        flags = FeatureFlags()

        assert flags.enable_workflows_feature is False

    def test_sessions_feature_can_be_disabled_via_env(self, monkeypatch: pytest.MonkeyPatch) -> None:
        """
        GIVEN FF_ENABLE_SESSIONS_FEATURE=false in environment
        WHEN FeatureFlags is instantiated
        THEN enable_sessions_feature should be False
        """
        monkeypatch.setenv("FF_ENABLE_SESSIONS_FEATURE", "false")

        from mcp_server_langgraph.core.feature_flags import FeatureFlags

        flags = FeatureFlags()

        assert flags.enable_sessions_feature is False

    def test_cost_dashboard_users_can_be_enabled_via_env(self, monkeypatch: pytest.MonkeyPatch) -> None:
        """
        GIVEN FF_ENABLE_COST_DASHBOARD_USERS=true in environment
        WHEN FeatureFlags is instantiated
        THEN enable_cost_dashboard_users should be True
        """
        monkeypatch.setenv("FF_ENABLE_COST_DASHBOARD_USERS", "true")

        from mcp_server_langgraph.core.feature_flags import FeatureFlags

        flags = FeatureFlags()

        assert flags.enable_cost_dashboard_users is True

    def test_mcp_websocket_can_be_enabled_via_env(self, monkeypatch: pytest.MonkeyPatch) -> None:
        """
        GIVEN FF_ENABLE_MCP_WEBSOCKET=true in environment
        WHEN FeatureFlags is instantiated
        THEN enable_mcp_websocket should be True
        """
        monkeypatch.setenv("FF_ENABLE_MCP_WEBSOCKET", "true")

        from mcp_server_langgraph.core.feature_flags import FeatureFlags

        flags = FeatureFlags()

        assert flags.enable_mcp_websocket is True


@pytest.mark.xdist_group(name="test_feature_flags_ui")
class TestUIFeatureFlagsHelperMethods:
    """Tests for helper methods with UI feature flags."""

    def teardown_method(self) -> None:
        """Force GC to prevent mock accumulation in xdist workers."""
        gc.collect()

    def test_is_feature_enabled_works_for_ui_flags(self) -> None:
        """
        GIVEN default feature flags
        WHEN is_feature_enabled is called with UI flag name
        THEN it should return correct boolean value
        """
        from mcp_server_langgraph.core.feature_flags import FeatureFlags

        flags = FeatureFlags()

        assert flags.is_feature_enabled("enable_workflows_feature") is True
        assert flags.is_feature_enabled("enable_mcp_websocket") is False

    def test_get_feature_value_works_for_ui_flags(self) -> None:
        """
        GIVEN default feature flags
        WHEN get_feature_value is called with UI flag name
        THEN it should return correct value
        """
        from mcp_server_langgraph.core.feature_flags import FeatureFlags

        flags = FeatureFlags()

        assert flags.get_feature_value("enable_cost_dashboard") is True
        assert flags.get_feature_value("enable_cost_dashboard_users") is False


@pytest.mark.xdist_group(name="test_feature_flags_ui")
class TestGetUIFeaturesForRole:
    """Tests for get_ui_features_for_role method."""

    def teardown_method(self) -> None:
        """Force GC to prevent mock accumulation in xdist workers."""
        gc.collect()

    def test_admin_gets_all_features(self) -> None:
        """
        GIVEN default feature flags
        WHEN get_ui_features_for_role is called with 'admin' role
        THEN all UI features should be enabled
        """
        from mcp_server_langgraph.core.feature_flags import FeatureFlags

        flags = FeatureFlags()
        features = flags.get_ui_features_for_role("admin")

        assert features["workflows"] is True
        assert features["sessions"] is True
        assert features["cost_dashboard"] is True
        assert features["observability"] is True
        assert features["code_export"] is True
        assert features["ai_suggestions"] is True

    def test_user_gets_filtered_features(self) -> None:
        """
        GIVEN cost_dashboard_users is disabled (default)
        WHEN get_ui_features_for_role is called with 'user' role
        THEN cost_dashboard should be False for non-admin users
        """
        from mcp_server_langgraph.core.feature_flags import FeatureFlags

        flags = FeatureFlags()
        features = flags.get_ui_features_for_role("user")

        assert features["workflows"] is True
        assert features["sessions"] is True
        # Cost dashboard disabled for regular users by default
        assert features["cost_dashboard"] is False
        assert features["observability"] is True

    def test_user_gets_cost_dashboard_when_enabled(self, monkeypatch: pytest.MonkeyPatch) -> None:
        """
        GIVEN FF_ENABLE_COST_DASHBOARD_USERS=true
        WHEN get_ui_features_for_role is called with 'user' role
        THEN cost_dashboard should be True for regular users
        """
        monkeypatch.setenv("FF_ENABLE_COST_DASHBOARD_USERS", "true")

        from mcp_server_langgraph.core.feature_flags import FeatureFlags

        flags = FeatureFlags()
        features = flags.get_ui_features_for_role("user")

        assert features["cost_dashboard"] is True

    def test_features_dict_includes_mcp_websocket_status(self) -> None:
        """
        GIVEN default feature flags
        WHEN get_ui_features_for_role is called
        THEN result should include mcp_websocket key
        """
        from mcp_server_langgraph.core.feature_flags import FeatureFlags

        flags = FeatureFlags()
        features = flags.get_ui_features_for_role("admin")

        assert "mcp_websocket" in features
        # Experimental, so False by default
        assert features["mcp_websocket"] is False
