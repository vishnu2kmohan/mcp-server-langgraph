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

    def test_enable_mcp_websocket_default_true(self) -> None:
        """
        GIVEN default feature flags
        WHEN FeatureFlags is instantiated
        THEN enable_mcp_websocket should be True (production-ready)
        """
        from mcp_server_langgraph.core.feature_flags import FeatureFlags

        flags = FeatureFlags()

        assert flags.enable_mcp_websocket is True

    def test_enable_interactive_artifacts_default_true(self) -> None:
        """
        GIVEN default feature flags
        WHEN FeatureFlags is instantiated
        THEN enable_interactive_artifacts should be True
        """
        from mcp_server_langgraph.core.feature_flags import FeatureFlags

        flags = FeatureFlags()

        assert flags.enable_interactive_artifacts is True


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

    def test_interactive_artifacts_can_be_disabled_via_env(self, monkeypatch: pytest.MonkeyPatch) -> None:
        """
        GIVEN FF_ENABLE_INTERACTIVE_ARTIFACTS=false in environment
        WHEN FeatureFlags is instantiated
        THEN enable_interactive_artifacts should be False
        """
        monkeypatch.setenv("FF_ENABLE_INTERACTIVE_ARTIFACTS", "false")

        from mcp_server_langgraph.core.feature_flags import FeatureFlags

        flags = FeatureFlags()

        assert flags.enable_interactive_artifacts is False


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
        assert flags.is_feature_enabled("enable_mcp_websocket") is True

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
        # Production-ready, so True by default
        assert features["mcp_websocket"] is True

    def test_features_dict_includes_interactive_artifacts(self) -> None:
        """
        GIVEN default feature flags
        WHEN get_ui_features_for_role is called
        THEN result should include interactive_artifacts key set to True
        """
        from mcp_server_langgraph.core.feature_flags import FeatureFlags

        flags = FeatureFlags()
        features = flags.get_ui_features_for_role("user")

        assert "interactive_artifacts" in features
        assert features["interactive_artifacts"] is True


@pytest.mark.xdist_group(name="test_feature_flags_ui")
class TestDevToolsFeatureFlags:
    """Tests for DevTools feature flags (Chrome DevTools-like debugging panel)."""

    def teardown_method(self) -> None:
        """Force GC to prevent mock accumulation in xdist workers."""
        gc.collect()

    def test_devtools_panel_default_true(self) -> None:
        """
        GIVEN default feature flags
        WHEN FeatureFlags is instantiated
        THEN devtools_panel should be True (master toggle enabled by default)
        """
        from mcp_server_langgraph.core.feature_flags import FeatureFlags

        flags = FeatureFlags()

        assert flags.devtools_panel is True

    def test_devtools_ai_insights_default_false(self) -> None:
        """
        GIVEN default feature flags
        WHEN FeatureFlags is instantiated
        THEN devtools_ai_insights should be False (experimental feature)
        """
        from mcp_server_langgraph.core.feature_flags import FeatureFlags

        flags = FeatureFlags()

        assert flags.devtools_ai_insights is False

    def test_devtools_ai_layout_default_false(self) -> None:
        """
        GIVEN default feature flags
        WHEN FeatureFlags is instantiated
        THEN devtools_ai_layout should be False (experimental feature)
        """
        from mcp_server_langgraph.core.feature_flags import FeatureFlags

        flags = FeatureFlags()

        assert flags.devtools_ai_layout is False

    def test_devtools_network_tab_default_true(self) -> None:
        """
        GIVEN default feature flags
        WHEN FeatureFlags is instantiated
        THEN devtools_network_tab should be True
        """
        from mcp_server_langgraph.core.feature_flags import FeatureFlags

        flags = FeatureFlags()

        assert flags.devtools_network_tab is True


@pytest.mark.xdist_group(name="test_feature_flags_ui")
class TestDevToolsFeatureFlagsEnvironmentOverride:
    """Tests for overriding DevTools feature flags via environment variables."""

    def teardown_method(self) -> None:
        """Force GC to prevent mock accumulation in xdist workers."""
        gc.collect()

    def test_devtools_panel_can_be_disabled_via_env(self, monkeypatch: pytest.MonkeyPatch) -> None:
        """
        GIVEN FF_DEVTOOLS_PANEL=false in environment
        WHEN FeatureFlags is instantiated
        THEN devtools_panel should be False
        """
        monkeypatch.setenv("FF_DEVTOOLS_PANEL", "false")

        from mcp_server_langgraph.core.feature_flags import FeatureFlags

        flags = FeatureFlags()

        assert flags.devtools_panel is False

    def test_devtools_ai_insights_can_be_enabled_via_env(self, monkeypatch: pytest.MonkeyPatch) -> None:
        """
        GIVEN FF_DEVTOOLS_AI_INSIGHTS=true in environment
        WHEN FeatureFlags is instantiated
        THEN devtools_ai_insights should be True
        """
        monkeypatch.setenv("FF_DEVTOOLS_AI_INSIGHTS", "true")

        from mcp_server_langgraph.core.feature_flags import FeatureFlags

        flags = FeatureFlags()

        assert flags.devtools_ai_insights is True

    def test_devtools_ai_layout_can_be_enabled_via_env(self, monkeypatch: pytest.MonkeyPatch) -> None:
        """
        GIVEN FF_DEVTOOLS_AI_LAYOUT=true in environment
        WHEN FeatureFlags is instantiated
        THEN devtools_ai_layout should be True
        """
        monkeypatch.setenv("FF_DEVTOOLS_AI_LAYOUT", "true")

        from mcp_server_langgraph.core.feature_flags import FeatureFlags

        flags = FeatureFlags()

        assert flags.devtools_ai_layout is True

    def test_devtools_network_tab_can_be_disabled_via_env(self, monkeypatch: pytest.MonkeyPatch) -> None:
        """
        GIVEN FF_DEVTOOLS_NETWORK_TAB=false in environment
        WHEN FeatureFlags is instantiated
        THEN devtools_network_tab should be False
        """
        monkeypatch.setenv("FF_DEVTOOLS_NETWORK_TAB", "false")

        from mcp_server_langgraph.core.feature_flags import FeatureFlags

        flags = FeatureFlags()

        assert flags.devtools_network_tab is False


@pytest.mark.xdist_group(name="test_feature_flags_ui")
class TestDevToolsFeatureFlagsInUIFeatures:
    """Tests for DevTools feature flags in get_ui_features_for_role."""

    def teardown_method(self) -> None:
        """Force GC to prevent mock accumulation in xdist workers."""
        gc.collect()

    def test_devtools_flags_included_in_ui_features_for_admin(self) -> None:
        """
        GIVEN default feature flags
        WHEN get_ui_features_for_role is called with 'admin' role
        THEN result should include all devtools flags
        """
        from mcp_server_langgraph.core.feature_flags import FeatureFlags

        flags = FeatureFlags()
        features = flags.get_ui_features_for_role("admin")

        assert "devtools_panel" in features
        assert "devtools_ai_insights" in features
        assert "devtools_ai_layout" in features
        assert "devtools_network_tab" in features

    def test_devtools_flags_have_correct_default_values_for_admin(self) -> None:
        """
        GIVEN default feature flags
        WHEN get_ui_features_for_role is called with 'admin' role
        THEN devtools flags should have correct default values
        """
        from mcp_server_langgraph.core.feature_flags import FeatureFlags

        flags = FeatureFlags()
        features = flags.get_ui_features_for_role("admin")

        assert features["devtools_panel"] is True
        assert features["devtools_ai_insights"] is False
        assert features["devtools_ai_layout"] is False
        assert features["devtools_network_tab"] is True

    def test_devtools_flags_included_in_ui_features_for_user(self) -> None:
        """
        GIVEN default feature flags
        WHEN get_ui_features_for_role is called with 'user' role
        THEN result should include devtools flags (available to all roles)
        """
        from mcp_server_langgraph.core.feature_flags import FeatureFlags

        flags = FeatureFlags()
        features = flags.get_ui_features_for_role("user")

        assert "devtools_panel" in features
        assert features["devtools_panel"] is True

    def test_devtools_ai_flags_enabled_via_env_reflected_in_features(self, monkeypatch: pytest.MonkeyPatch) -> None:
        """
        GIVEN devtools AI flags enabled via environment
        WHEN get_ui_features_for_role is called
        THEN features should reflect enabled state
        """
        monkeypatch.setenv("FF_DEVTOOLS_AI_INSIGHTS", "true")
        monkeypatch.setenv("FF_DEVTOOLS_AI_LAYOUT", "true")

        from mcp_server_langgraph.core.feature_flags import FeatureFlags

        flags = FeatureFlags()
        features = flags.get_ui_features_for_role("admin")

        assert features["devtools_ai_insights"] is True
        assert features["devtools_ai_layout"] is True

    def test_is_feature_enabled_works_for_devtools_flags(self) -> None:
        """
        GIVEN default feature flags
        WHEN is_feature_enabled is called with devtools flag names
        THEN it should return correct boolean values
        """
        from mcp_server_langgraph.core.feature_flags import FeatureFlags

        flags = FeatureFlags()

        assert flags.is_feature_enabled("devtools_panel") is True
        assert flags.is_feature_enabled("devtools_ai_insights") is False
        assert flags.is_feature_enabled("devtools_ai_layout") is False
        assert flags.is_feature_enabled("devtools_network_tab") is True
