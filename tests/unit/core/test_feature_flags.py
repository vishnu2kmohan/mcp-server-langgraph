"""
Unit tests for core/feature_flags.py.

Tests feature flag configuration and helper functions.
Follows TDD principles and memory safety patterns for pytest-xdist.
"""

import gc

import pytest

pytestmark = pytest.mark.unit


@pytest.mark.xdist_group(name="feature_flags")
class TestFeatureFlagsDefaults:
    """Test FeatureFlags default values."""

    def teardown_method(self):
        """Force GC to prevent mock accumulation in xdist workers."""
        gc.collect()

    @pytest.mark.unit
    def test_pydantic_ai_routing_enabled_by_default(self):
        """Test that Pydantic AI routing is enabled by default."""
        from mcp_server_langgraph.core.feature_flags import FeatureFlags

        flags = FeatureFlags()

        assert flags.enable_pydantic_ai_routing is True

    @pytest.mark.unit
    def test_pydantic_ai_responses_enabled_by_default(self):
        """Test that Pydantic AI responses is enabled by default."""
        from mcp_server_langgraph.core.feature_flags import FeatureFlags

        flags = FeatureFlags()

        assert flags.enable_pydantic_ai_responses is True

    @pytest.mark.unit
    def test_confidence_threshold_has_valid_default(self):
        """Test that confidence threshold has valid default."""
        from mcp_server_langgraph.core.feature_flags import FeatureFlags

        flags = FeatureFlags()

        assert 0.0 <= flags.pydantic_ai_confidence_threshold <= 1.0
        assert flags.pydantic_ai_confidence_threshold == 0.7

    @pytest.mark.unit
    def test_llm_fallback_enabled_by_default(self):
        """Test that LLM fallback is enabled by default."""
        from mcp_server_langgraph.core.feature_flags import FeatureFlags

        flags = FeatureFlags()

        assert flags.enable_llm_fallback is True

    @pytest.mark.unit
    def test_openfga_enabled_by_default(self):
        """Test that OpenFGA is enabled by default."""
        from mcp_server_langgraph.core.feature_flags import FeatureFlags

        flags = FeatureFlags()

        assert flags.enable_openfga is True

    @pytest.mark.unit
    def test_experimental_features_disabled_by_default(self):
        """Test that experimental features are disabled by default."""
        from mcp_server_langgraph.core.feature_flags import FeatureFlags

        flags = FeatureFlags()

        assert flags.enable_experimental_features is False

    @pytest.mark.unit
    def test_rate_limiting_enabled_by_default(self):
        """Test that rate limiting is enabled by default."""
        from mcp_server_langgraph.core.feature_flags import FeatureFlags

        flags = FeatureFlags()

        assert flags.enable_rate_limiting is True


@pytest.mark.xdist_group(name="feature_flags")
class TestFeatureFlagsMethods:
    """Test FeatureFlags helper methods."""

    def teardown_method(self):
        """Force GC to prevent mock accumulation in xdist workers."""
        gc.collect()

    @pytest.mark.unit
    def test_is_feature_enabled_returns_true_for_enabled_feature(self):
        """Test is_feature_enabled returns True for enabled feature."""
        from mcp_server_langgraph.core.feature_flags import FeatureFlags

        flags = FeatureFlags()

        assert flags.is_feature_enabled("enable_rate_limiting") is True

    @pytest.mark.unit
    def test_is_feature_enabled_returns_false_for_disabled_feature(self):
        """Test is_feature_enabled returns False for disabled feature."""
        from mcp_server_langgraph.core.feature_flags import FeatureFlags

        flags = FeatureFlags()

        assert flags.is_feature_enabled("enable_experimental_features") is False

    @pytest.mark.unit
    def test_is_feature_enabled_returns_false_for_unknown_feature(self):
        """Test is_feature_enabled returns False for unknown feature."""
        from mcp_server_langgraph.core.feature_flags import FeatureFlags

        flags = FeatureFlags()

        assert flags.is_feature_enabled("nonexistent_feature") is False

    @pytest.mark.unit
    def test_get_feature_value_returns_correct_value(self):
        """Test get_feature_value returns correct value."""
        from mcp_server_langgraph.core.feature_flags import FeatureFlags

        flags = FeatureFlags()

        assert flags.get_feature_value("max_agent_iterations") == 10

    @pytest.mark.unit
    def test_get_feature_value_returns_default_for_unknown_feature(self):
        """Test get_feature_value returns default for unknown feature."""
        from mcp_server_langgraph.core.feature_flags import FeatureFlags

        flags = FeatureFlags()

        assert flags.get_feature_value("unknown_feature", default="fallback") == "fallback"

    @pytest.mark.unit
    def test_should_use_experimental_requires_master_switch(self):
        """Test should_use_experimental requires master switch."""
        from mcp_server_langgraph.core.feature_flags import FeatureFlags

        flags = FeatureFlags()

        # Master switch is off by default
        assert flags.should_use_experimental("enable_multi_agent_collaboration") is False

    @pytest.mark.unit
    def test_should_use_experimental_with_master_switch_enabled(self):
        """Test should_use_experimental with master switch enabled."""
        from mcp_server_langgraph.core.feature_flags import FeatureFlags

        # Create flags with experimental enabled
        flags = FeatureFlags(
            enable_experimental_features=True,
            enable_multi_agent_collaboration=True,
        )

        assert flags.should_use_experimental("enable_multi_agent_collaboration") is True


@pytest.mark.xdist_group(name="feature_flags")
class TestFeatureFlagsGlobal:
    """Test global feature flags functions."""

    def teardown_method(self):
        """Force GC to prevent mock accumulation in xdist workers."""
        gc.collect()

    @pytest.mark.unit
    def test_get_feature_flags_returns_instance(self):
        """Test get_feature_flags returns FeatureFlags instance."""
        from mcp_server_langgraph.core.feature_flags import (
            FeatureFlags,
            get_feature_flags,
        )

        flags = get_feature_flags()

        assert isinstance(flags, FeatureFlags)

    @pytest.mark.unit
    def test_is_enabled_convenience_function_works(self):
        """Test is_enabled convenience function works."""
        from mcp_server_langgraph.core.feature_flags import is_enabled

        # Default enabled feature
        assert is_enabled("enable_rate_limiting") is True

        # Default disabled feature
        assert is_enabled("enable_experimental_features") is False


@pytest.mark.xdist_group(name="feature_flags")
class TestFeatureFlagsValidation:
    """Test FeatureFlags field validation."""

    def teardown_method(self):
        """Force GC to prevent mock accumulation in xdist workers."""
        gc.collect()

    @pytest.mark.unit
    def test_confidence_threshold_must_be_between_zero_and_one(self):
        """Test that confidence threshold must be 0-1."""
        from pydantic import ValidationError

        from mcp_server_langgraph.core.feature_flags import FeatureFlags

        with pytest.raises(ValidationError):
            FeatureFlags(pydantic_ai_confidence_threshold=1.5)

    @pytest.mark.unit
    def test_llm_timeout_has_valid_range(self):
        """Test that LLM timeout has valid range."""
        from pydantic import ValidationError

        from mcp_server_langgraph.core.feature_flags import FeatureFlags

        # Too low
        with pytest.raises(ValidationError):
            FeatureFlags(llm_timeout_seconds=5)

        # Too high
        with pytest.raises(ValidationError):
            FeatureFlags(llm_timeout_seconds=400)

    @pytest.mark.unit
    def test_max_agent_iterations_has_valid_range(self):
        """Test that max_agent_iterations has valid range."""
        from pydantic import ValidationError

        from mcp_server_langgraph.core.feature_flags import FeatureFlags

        # Too low
        with pytest.raises(ValidationError):
            FeatureFlags(max_agent_iterations=0)

        # Too high
        with pytest.raises(ValidationError):
            FeatureFlags(max_agent_iterations=100)

    @pytest.mark.unit
    def test_rate_limit_requests_has_valid_range(self):
        """Test that rate limit requests has valid range."""
        from mcp_server_langgraph.core.feature_flags import FeatureFlags

        # Valid value
        flags = FeatureFlags(rate_limit_requests_per_minute=100)
        assert flags.rate_limit_requests_per_minute == 100


@pytest.mark.xdist_group(name="feature_flags")
class TestSuggestionFeatureFlags:
    """Test suggestion-related feature flags."""

    def teardown_method(self):
        """Force GC to prevent mock accumulation in xdist workers."""
        gc.collect()

    @pytest.mark.unit
    def test_enable_streaming_suggestions_default_true(self):
        """Test that streaming suggestions is enabled by default."""
        from mcp_server_langgraph.core.feature_flags import FeatureFlags

        flags = FeatureFlags()
        assert flags.enable_streaming_suggestions is True

    @pytest.mark.unit
    def test_enable_personalized_suggestions_default_true(self):
        """Test that personalized suggestions is enabled by default."""
        from mcp_server_langgraph.core.feature_flags import FeatureFlags

        flags = FeatureFlags()
        assert flags.enable_personalized_suggestions is True

    @pytest.mark.unit
    def test_suggestion_rate_limit_per_minute_default(self):
        """Test that suggestion rate limit has correct default."""
        from mcp_server_langgraph.core.feature_flags import FeatureFlags

        flags = FeatureFlags()
        assert flags.suggestion_rate_limit_per_minute == 60

    @pytest.mark.unit
    def test_suggestion_rate_limit_configurable(self):
        """Test that suggestion rate limit is configurable."""
        from mcp_server_langgraph.core.feature_flags import FeatureFlags

        flags = FeatureFlags(suggestion_rate_limit_per_minute=120)
        assert flags.suggestion_rate_limit_per_minute == 120

    @pytest.mark.unit
    def test_enable_distributed_rate_limiting_default_false(self):
        """Test that distributed rate limiting is disabled by default."""
        from mcp_server_langgraph.core.feature_flags import FeatureFlags

        flags = FeatureFlags()
        assert flags.enable_distributed_rate_limiting is False

    @pytest.mark.unit
    def test_suggestion_cache_ttl_seconds_default(self):
        """Test that suggestion cache TTL has correct default."""
        from mcp_server_langgraph.core.feature_flags import FeatureFlags

        flags = FeatureFlags()
        assert flags.suggestion_cache_ttl_seconds == 300

    @pytest.mark.unit
    def test_enable_suggestion_quality_tracking_default_true(self):
        """Test that suggestion quality tracking is enabled by default."""
        from mcp_server_langgraph.core.feature_flags import FeatureFlags

        flags = FeatureFlags()
        assert flags.enable_suggestion_quality_tracking is True

    @pytest.mark.unit
    def test_enable_suggestion_prewarm_default_false(self):
        """Test that suggestion pre-warming is disabled by default."""
        from mcp_server_langgraph.core.feature_flags import FeatureFlags

        flags = FeatureFlags()
        assert flags.enable_suggestion_prewarm is False

    @pytest.mark.unit
    def test_max_conversation_history_messages_default(self):
        """Test that max conversation history has correct default."""
        from mcp_server_langgraph.core.feature_flags import FeatureFlags

        flags = FeatureFlags()
        assert flags.max_conversation_history_messages == 5

    @pytest.mark.unit
    def test_enable_conversation_history_validation_default_true(self):
        """Test that conversation history validation is enabled by default."""
        from mcp_server_langgraph.core.feature_flags import FeatureFlags

        flags = FeatureFlags()
        assert flags.enable_conversation_history_validation is True


@pytest.mark.xdist_group(name="feature_flags")
class TestChatUXFeatureFlags:
    """Test chat UX feature flags (URL fetch, slash commands, style presets)."""

    def teardown_method(self):
        """Force GC to prevent mock accumulation in xdist workers."""
        gc.collect()

    @pytest.mark.unit
    def test_enable_url_content_fetch_default_true(self):
        """Test that URL content fetch is enabled by default."""
        from mcp_server_langgraph.core.feature_flags import FeatureFlags

        flags = FeatureFlags()
        assert flags.enable_url_content_fetch is True

    @pytest.mark.unit
    def test_enable_url_content_fetch_configurable(self):
        """Test that URL content fetch can be disabled."""
        from mcp_server_langgraph.core.feature_flags import FeatureFlags

        flags = FeatureFlags(enable_url_content_fetch=False)
        assert flags.enable_url_content_fetch is False

    @pytest.mark.unit
    def test_enable_slash_commands_default_true(self):
        """Test that slash commands are enabled by default."""
        from mcp_server_langgraph.core.feature_flags import FeatureFlags

        flags = FeatureFlags()
        assert flags.enable_slash_commands is True

    @pytest.mark.unit
    def test_enable_slash_commands_configurable(self):
        """Test that slash commands can be disabled."""
        from mcp_server_langgraph.core.feature_flags import FeatureFlags

        flags = FeatureFlags(enable_slash_commands=False)
        assert flags.enable_slash_commands is False

    @pytest.mark.unit
    def test_enable_style_presets_default_true(self):
        """Test that style presets are enabled by default."""
        from mcp_server_langgraph.core.feature_flags import FeatureFlags

        flags = FeatureFlags()
        assert flags.enable_style_presets is True

    @pytest.mark.unit
    def test_enable_style_presets_configurable(self):
        """Test that style presets can be disabled."""
        from mcp_server_langgraph.core.feature_flags import FeatureFlags

        flags = FeatureFlags(enable_style_presets=False)
        assert flags.enable_style_presets is False


@pytest.mark.xdist_group(name="feature_flags")
class TestUIFeaturesForRole:
    """Test get_ui_features_for_role method."""

    def teardown_method(self):
        """Force GC to prevent mock accumulation in xdist workers."""
        gc.collect()

    @pytest.mark.unit
    def test_get_ui_features_for_admin_includes_all_features(self):
        """Test that admin role gets all UI features."""
        from mcp_server_langgraph.core.feature_flags import FeatureFlags

        flags = FeatureFlags()
        features = flags.get_ui_features_for_role("admin")

        assert features["workflows"] is True
        assert features["sessions"] is True
        assert features["cost_dashboard"] is True
        assert features["observability"] is True
        assert features["url_content_fetch"] is True
        assert features["slash_commands"] is True
        assert features["style_presets"] is True

    @pytest.mark.unit
    def test_get_ui_features_for_user_respects_user_flags(self):
        """Test that user role respects user-specific flags."""
        from mcp_server_langgraph.core.feature_flags import FeatureFlags

        # By default, cost_dashboard_users is False
        flags = FeatureFlags()
        features = flags.get_ui_features_for_role("user")

        # User should not see cost dashboard by default
        assert features["cost_dashboard"] is False
        # But should see other features
        assert features["workflows"] is True
        assert features["sessions"] is True
        assert features["url_content_fetch"] is True
        assert features["slash_commands"] is True
        assert features["style_presets"] is True

    @pytest.mark.unit
    def test_get_ui_features_for_user_with_cost_dashboard_enabled(self):
        """Test that user gets cost dashboard when enable_cost_dashboard_users is True."""
        from mcp_server_langgraph.core.feature_flags import FeatureFlags

        flags = FeatureFlags(enable_cost_dashboard_users=True)
        features = flags.get_ui_features_for_role("user")

        assert features["cost_dashboard"] is True

    @pytest.mark.unit
    def test_get_ui_features_includes_new_chat_ux_flags(self):
        """Test that UI features include new chat UX flags."""
        from mcp_server_langgraph.core.feature_flags import FeatureFlags

        flags = FeatureFlags()
        features = flags.get_ui_features_for_role("admin")

        # Verify all new chat UX flags are included
        assert "url_content_fetch" in features
        assert "slash_commands" in features
        assert "style_presets" in features

    @pytest.mark.unit
    def test_get_ui_features_respects_disabled_flags(self):
        """Test that UI features respect disabled flag values."""
        from mcp_server_langgraph.core.feature_flags import FeatureFlags

        flags = FeatureFlags(
            enable_url_content_fetch=False,
            enable_slash_commands=False,
            enable_style_presets=False,
        )
        features = flags.get_ui_features_for_role("admin")

        assert features["url_content_fetch"] is False
        assert features["slash_commands"] is False
        assert features["style_presets"] is False

    @pytest.mark.unit
    def test_get_ui_features_case_insensitive_role(self):
        """Test that role comparison is case-insensitive."""
        from mcp_server_langgraph.core.feature_flags import FeatureFlags

        flags = FeatureFlags()

        # Admin in various cases should get same result
        features_admin = flags.get_ui_features_for_role("admin")
        features_admin_upper = flags.get_ui_features_for_role("ADMIN")
        features_admin_mixed = flags.get_ui_features_for_role("Admin")

        assert features_admin["cost_dashboard"] == features_admin_upper["cost_dashboard"]
        assert features_admin["cost_dashboard"] == features_admin_mixed["cost_dashboard"]


@pytest.mark.xdist_group(name="feature_flags")
class TestUXEnhancementFeatureFlags:
    """Test UX enhancement feature flags (Priority 1-3 from competitive analysis)."""

    def teardown_method(self):
        """Force GC to prevent mock accumulation in xdist workers."""
        gc.collect()

    @pytest.mark.unit
    def test_enable_user_preferences_sync_default_true(self):
        """Test that user preferences sync is enabled by default."""
        from mcp_server_langgraph.core.feature_flags import FeatureFlags

        flags = FeatureFlags()
        assert flags.enable_user_preferences_sync is True

    @pytest.mark.unit
    def test_enable_session_export_default_true(self):
        """Test that session export is enabled by default."""
        from mcp_server_langgraph.core.feature_flags import FeatureFlags

        flags = FeatureFlags()
        assert flags.enable_session_export is True

    @pytest.mark.unit
    def test_enable_project_context_default_true(self):
        """Test that project context is enabled by default."""
        from mcp_server_langgraph.core.feature_flags import FeatureFlags

        flags = FeatureFlags()
        assert flags.enable_project_context is True

    @pytest.mark.unit
    def test_enable_onboarding_wizard_default_true(self):
        """Test that onboarding wizard is enabled by default."""
        from mcp_server_langgraph.core.feature_flags import FeatureFlags

        flags = FeatureFlags()
        assert flags.enable_onboarding_wizard is True

    @pytest.mark.unit
    def test_enable_guided_tour_default_true(self):
        """Test that guided tour is enabled by default."""
        from mcp_server_langgraph.core.feature_flags import FeatureFlags

        flags = FeatureFlags()
        assert flags.enable_guided_tour is True

    @pytest.mark.unit
    def test_enable_sus_survey_default_true(self):
        """Test that SUS survey is enabled by default."""
        from mcp_server_langgraph.core.feature_flags import FeatureFlags

        flags = FeatureFlags()
        assert flags.enable_sus_survey is True

    @pytest.mark.unit
    def test_enable_command_palette_default_true(self):
        """Test that command palette is enabled by default."""
        from mcp_server_langgraph.core.feature_flags import FeatureFlags

        flags = FeatureFlags()
        assert flags.enable_command_palette is True

    @pytest.mark.unit
    def test_enable_keyboard_shortcuts_default_true(self):
        """Test that keyboard shortcuts are enabled by default."""
        from mcp_server_langgraph.core.feature_flags import FeatureFlags

        flags = FeatureFlags()
        assert flags.enable_keyboard_shortcuts is True

    @pytest.mark.unit
    def test_enable_theme_customization_default_true(self):
        """Test that theme customization is enabled by default."""
        from mcp_server_langgraph.core.feature_flags import FeatureFlags

        flags = FeatureFlags()
        assert flags.enable_theme_customization is True

    @pytest.mark.unit
    def test_enable_confirmation_dialogs_default_true(self):
        """Test that confirmation dialogs are enabled by default."""
        from mcp_server_langgraph.core.feature_flags import FeatureFlags

        flags = FeatureFlags()
        assert flags.enable_confirmation_dialogs is True

    @pytest.mark.unit
    def test_ux_features_configurable(self):
        """Test that UX enhancement features are configurable."""
        from mcp_server_langgraph.core.feature_flags import FeatureFlags

        flags = FeatureFlags(
            enable_user_preferences_sync=False,
            enable_session_export=False,
            enable_command_palette=False,
        )

        assert flags.enable_user_preferences_sync is False
        assert flags.enable_session_export is False
        assert flags.enable_command_palette is False

    @pytest.mark.unit
    def test_get_ui_features_includes_ux_enhancement_flags(self):
        """Test that UI features include UX enhancement flags."""
        from mcp_server_langgraph.core.feature_flags import FeatureFlags

        flags = FeatureFlags()
        features = flags.get_ui_features_for_role("admin")

        # Verify all UX enhancement flags are included
        assert "user_preferences_sync" in features
        assert "session_export" in features
        assert "project_context" in features
        assert "onboarding_wizard" in features
        assert "guided_tour" in features
        assert "sus_survey" in features
        assert "command_palette" in features
        assert "keyboard_shortcuts" in features
        assert "theme_customization" in features
        assert "confirmation_dialogs" in features
