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
        # Note: enable_multi_agent_collaboration was deprecated in Sprint Block 5
        assert flags.should_use_experimental("enable_loop_agent") is False

    @pytest.mark.unit
    def test_should_use_experimental_with_master_switch_enabled(self):
        """Test should_use_experimental with master switch enabled."""
        from mcp_server_langgraph.core.feature_flags import FeatureFlags

        # Create flags with experimental enabled
        # Note: enable_multi_agent_collaboration was deprecated in Sprint Block 5
        # and merged into enable_multi_agent_orchestration + multi_agent_strategy
        flags = FeatureFlags(
            enable_experimental_features=True,
            enable_loop_agent=True,  # Using loop_agent as an experimental flag
        )

        assert flags.should_use_experimental("enable_loop_agent") is True


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


@pytest.mark.xdist_group(name="feature_flags")
class TestAIUXFeatureFlags:
    """Test AI UX feature flags for Phase 6 AI-Native Integration."""

    def teardown_method(self):
        """Force GC to prevent mock accumulation in xdist workers."""
        gc.collect()

    @pytest.mark.unit
    def test_enable_ai_disclosure_default_true(self):
        """Test that AI disclosure analysis is enabled by default."""
        from mcp_server_langgraph.core.feature_flags import FeatureFlags

        flags = FeatureFlags()
        assert flags.enable_ai_disclosure is True

    @pytest.mark.unit
    def test_enable_ai_empty_states_default_true(self):
        """Test that AI empty states is enabled by default."""
        from mcp_server_langgraph.core.feature_flags import FeatureFlags

        flags = FeatureFlags()
        assert flags.enable_ai_empty_states is True

    @pytest.mark.unit
    def test_enable_ai_nudges_default_true(self):
        """Test that AI nudges is enabled by default."""
        from mcp_server_langgraph.core.feature_flags import FeatureFlags

        flags = FeatureFlags()
        assert flags.enable_ai_nudges is True

    @pytest.mark.unit
    def test_enable_ai_error_recovery_default_true(self):
        """Test that AI error recovery is enabled by default."""
        from mcp_server_langgraph.core.feature_flags import FeatureFlags

        flags = FeatureFlags()
        assert flags.enable_ai_error_recovery is True

    @pytest.mark.unit
    def test_enable_ai_onboarding_default_true(self):
        """Test that AI onboarding is enabled by default."""
        from mcp_server_langgraph.core.feature_flags import FeatureFlags

        flags = FeatureFlags()
        assert flags.enable_ai_onboarding is True

    @pytest.mark.unit
    def test_enable_ai_metrics_insights_default_true(self):
        """Test that AI metrics insights is enabled by default."""
        from mcp_server_langgraph.core.feature_flags import FeatureFlags

        flags = FeatureFlags()
        assert flags.enable_ai_metrics_insights is True

    @pytest.mark.unit
    def test_enable_ai_persona_analysis_default_true(self):
        """Test that AI persona analysis is enabled by default."""
        from mcp_server_langgraph.core.feature_flags import FeatureFlags

        flags = FeatureFlags()
        assert flags.enable_ai_persona_analysis is True

    @pytest.mark.unit
    def test_ai_ux_flags_configurable(self):
        """Test that AI UX features are configurable."""
        from mcp_server_langgraph.core.feature_flags import FeatureFlags

        flags = FeatureFlags(
            enable_ai_disclosure=False,
            enable_ai_empty_states=False,
            enable_ai_nudges=False,
            enable_ai_error_recovery=False,
            enable_ai_onboarding=False,
            enable_ai_metrics_insights=False,
            enable_ai_persona_analysis=False,
        )

        assert flags.enable_ai_disclosure is False
        assert flags.enable_ai_empty_states is False
        assert flags.enable_ai_nudges is False
        assert flags.enable_ai_error_recovery is False
        assert flags.enable_ai_onboarding is False
        assert flags.enable_ai_metrics_insights is False
        assert flags.enable_ai_persona_analysis is False

    @pytest.mark.unit
    def test_get_ui_features_includes_ai_ux_flags(self):
        """Test that UI features include AI UX flags."""
        from mcp_server_langgraph.core.feature_flags import FeatureFlags

        flags = FeatureFlags()
        features = flags.get_ui_features_for_role("admin")

        # Verify all AI UX flags are included
        assert "ai_disclosure" in features
        assert "ai_empty_states" in features
        assert "ai_nudges" in features
        assert "ai_error_recovery" in features
        assert "ai_onboarding" in features
        assert "ai_metrics_insights" in features
        assert "ai_persona_analysis" in features

    @pytest.mark.unit
    def test_ai_ux_flags_available_for_all_roles(self):
        """Test that AI UX flags are available for all roles."""
        from mcp_server_langgraph.core.feature_flags import FeatureFlags

        flags = FeatureFlags()

        admin_features = flags.get_ui_features_for_role("admin")
        user_features = flags.get_ui_features_for_role("user")

        # AI features should be available to all roles
        assert admin_features["ai_disclosure"] is True
        assert user_features["ai_disclosure"] is True
        assert admin_features["ai_nudges"] is True
        assert user_features["ai_nudges"] is True


@pytest.mark.xdist_group(name="feature_flags_decorator")
class TestFeatureGatedDecorator:
    """Test the @feature_gated decorator for easier testing."""

    def teardown_method(self):
        """Force GC to prevent mock accumulation in xdist workers."""
        gc.collect()

    @pytest.mark.unit
    def test_feature_gated_decorator_exists(self):
        """Test that the feature_gated decorator is importable."""
        from mcp_server_langgraph.core.feature_flags import feature_gated

        assert feature_gated is not None
        assert callable(feature_gated)

    @pytest.mark.unit
    def test_feature_gated_allows_enabled_feature(self):
        """Test that decorator allows execution when feature is enabled."""
        from mcp_server_langgraph.core.feature_flags import feature_gated

        @feature_gated("enable_streaming_responses", "Streaming Responses")
        def decorated_function():
            return "success"

        # enable_streaming_responses is True by default
        result = decorated_function()
        assert result == "success"

    @pytest.mark.unit
    def test_feature_gated_blocks_disabled_feature(self, monkeypatch):
        """Test that decorator raises FeatureDisabledError when feature is disabled."""
        import sys

        from mcp_server_langgraph.core.exceptions import FeatureDisabledError

        # Set environment variables to disable the feature and test mode bypass
        # The environment variables are read by Pydantic-settings when creating FeatureFlags
        monkeypatch.setenv("FF_ENABLE_SKILLS_SYSTEM", "false")
        monkeypatch.setenv("FF_TEST_MODE", "false")

        # Create a fresh FeatureFlags instance that reads from the patched environment
        from mcp_server_langgraph.core.feature_flags import FeatureFlags, feature_gated

        test_flags = FeatureFlags()

        # Verify the flag is actually disabled
        assert test_flags.enable_skills_system is False

        # Get the actual module object from sys.modules to patch the singleton
        ff_module = sys.modules["mcp_server_langgraph.core.feature_flags"]

        original_flags = ff_module.feature_flags
        ff_module.feature_flags = test_flags

        try:
            # Define a decorated function that uses require_feature on our test instance
            @feature_gated("enable_skills_system", "Skills System")
            def decorated_function():
                return "success"

            # With the flag disabled, calling the function should raise FeatureDisabledError
            with pytest.raises(FeatureDisabledError) as exc_info:
                decorated_function()

            assert "Skills System" in str(exc_info.value)
        finally:
            # Restore the original singleton
            ff_module.feature_flags = original_flags

    @pytest.mark.unit
    def test_feature_gated_preserves_function_signature(self):
        """Test that decorator preserves the original function signature."""
        from mcp_server_langgraph.core.feature_flags import feature_gated

        @feature_gated("enable_streaming_responses", "Streaming Responses")
        def greet(name: str, greeting: str = "Hello") -> str:
            """Greet someone."""
            return f"{greeting}, {name}!"

        # Function name and docstring should be preserved
        assert greet.__name__ == "greet"
        assert greet.__doc__ == "Greet someone."

        # Function should work with arguments
        result = greet("World")
        assert result == "Hello, World!"

        result = greet("Alice", greeting="Hi")
        assert result == "Hi, Alice!"

    @pytest.mark.unit
    @pytest.mark.asyncio
    async def test_feature_gated_works_with_async_functions(self):
        """Test that decorator works with async functions."""
        from mcp_server_langgraph.core.feature_flags import feature_gated

        @feature_gated("enable_streaming_responses", "Streaming Responses")
        async def async_func():
            return "async success"

        result = await async_func()
        assert result == "async success"

    @pytest.mark.unit
    def test_feature_gated_works_with_class_methods(self):
        """Test that decorator works with class methods."""
        from mcp_server_langgraph.core.feature_flags import feature_gated

        class TestClass:
            @feature_gated("enable_streaming_responses", "Streaming Responses")
            def method(self, value: int) -> int:
                return value * 2

        obj = TestClass()
        result = obj.method(21)
        assert result == 42

    @pytest.mark.unit
    def test_feature_gated_is_mockable(self, monkeypatch):
        """Test that decorated functions can be easily mocked for testing."""
        import sys

        from mcp_server_langgraph.core.feature_flags import feature_gated

        @feature_gated("enable_skills_system", "Skills System")
        def protected_func():
            return "protected result"

        # Use shared MockFeatureFlags with the feature enabled
        from tests.fixtures.feature_flags_fixtures import MockFeatureFlags

        # Patch the feature_flags
        ff_module = sys.modules["mcp_server_langgraph.core.feature_flags"]
        monkeypatch.setattr(ff_module, "feature_flags", MockFeatureFlags(enable_skills_system=True))

        # Now the function should work
        result = protected_func()
        assert result == "protected result"


@pytest.mark.xdist_group(name="feature_flags_test_mode")
class TestFeatureFlagsTestMode:
    """Test the test-mode override via environment variable."""

    def teardown_method(self):
        """Force GC to prevent mock accumulation in xdist workers."""
        gc.collect()

    @pytest.mark.unit
    def test_test_mode_bypasses_feature_check(self, monkeypatch):
        """Test that FF_TEST_MODE=true bypasses all feature flag checks."""
        # Set test mode before importing
        monkeypatch.setenv("FF_TEST_MODE", "true")

        # Re-import to pick up the env var
        from mcp_server_langgraph.core.feature_flags import FeatureFlags

        flags = FeatureFlags()

        # Even disabled features should pass in test mode
        # This should NOT raise FeatureDisabledError
        flags.require_feature("enable_skills_system", "Skills System")

    @pytest.mark.unit
    def test_test_mode_is_case_insensitive(self, monkeypatch):
        """Test that FF_TEST_MODE accepts various true values."""
        from mcp_server_langgraph.core.feature_flags import FeatureFlags

        for value in ["true", "TRUE", "True", "1", "yes", "YES"]:
            monkeypatch.setenv("FF_TEST_MODE", value)
            flags = FeatureFlags()

            # Should not raise
            flags.require_feature("enable_skills_system", "Skills System")

    @pytest.mark.unit
    def test_test_mode_false_enforces_flags(self, monkeypatch):
        """Test that FF_TEST_MODE=false still enforces feature flags."""
        from mcp_server_langgraph.core.exceptions import FeatureDisabledError
        from mcp_server_langgraph.core.feature_flags import FeatureFlags

        # Disable test mode and the feature we're testing
        monkeypatch.setenv("FF_TEST_MODE", "false")
        monkeypatch.setenv("FF_ENABLE_SKILLS_SYSTEM", "false")
        flags = FeatureFlags()

        with pytest.raises(FeatureDisabledError):
            flags.require_feature("enable_skills_system", "Skills System")

    @pytest.mark.unit
    def test_test_mode_not_set_enforces_flags(self, monkeypatch):
        """Test that without FF_TEST_MODE, feature flags are enforced."""
        from mcp_server_langgraph.core.exceptions import FeatureDisabledError
        from mcp_server_langgraph.core.feature_flags import FeatureFlags

        # Remove test mode and disable the feature we're testing
        monkeypatch.delenv("FF_TEST_MODE", raising=False)
        monkeypatch.setenv("FF_ENABLE_SKILLS_SYSTEM", "false")
        flags = FeatureFlags()

        with pytest.raises(FeatureDisabledError):
            flags.require_feature("enable_skills_system", "Skills System")

    @pytest.mark.unit
    def test_is_test_mode_property(self):
        """Test that FeatureFlags has an is_test_mode property."""
        from mcp_server_langgraph.core.feature_flags import FeatureFlags

        flags = FeatureFlags()

        # Should have the property
        assert hasattr(flags, "is_test_mode")

    @pytest.mark.unit
    def test_is_test_mode_returns_correct_value(self, monkeypatch):
        """Test that is_test_mode property returns correct value."""
        from mcp_server_langgraph.core.feature_flags import FeatureFlags

        # Test mode off
        monkeypatch.delenv("FF_TEST_MODE", raising=False)
        flags = FeatureFlags()
        assert flags.is_test_mode is False

        # Test mode on
        monkeypatch.setenv("FF_TEST_MODE", "true")
        flags = FeatureFlags()
        assert flags.is_test_mode is True


@pytest.mark.xdist_group(name="feature_flags_hitl")
class TestHITLFeatureFlags:
    """Test Human-in-the-Loop (HITL) feature flags for confidence-based approval."""

    def teardown_method(self):
        """Force GC to prevent mock accumulation in xdist workers."""
        gc.collect()

    @pytest.mark.unit
    def test_enable_agent_hitl_default_true(self):
        """Test that agent HITL is enabled by default."""
        from mcp_server_langgraph.core.feature_flags import FeatureFlags

        flags = FeatureFlags()
        assert flags.enable_agent_hitl is True

    @pytest.mark.unit
    def test_enable_agent_hitl_configurable(self):
        """Test that agent HITL can be disabled."""
        from mcp_server_langgraph.core.feature_flags import FeatureFlags

        flags = FeatureFlags(enable_agent_hitl=False)
        assert flags.enable_agent_hitl is False

    @pytest.mark.unit
    def test_agent_hitl_confidence_threshold_default(self):
        """Test that HITL confidence threshold defaults to 0.7."""
        from mcp_server_langgraph.core.feature_flags import FeatureFlags

        flags = FeatureFlags()
        assert flags.agent_hitl_confidence_threshold == 0.7

    @pytest.mark.unit
    def test_agent_hitl_confidence_threshold_configurable(self):
        """Test that HITL confidence threshold is configurable."""
        from mcp_server_langgraph.core.feature_flags import FeatureFlags

        flags = FeatureFlags(agent_hitl_confidence_threshold=0.8)
        assert flags.agent_hitl_confidence_threshold == 0.8

    @pytest.mark.unit
    def test_agent_hitl_confidence_threshold_validation(self):
        """Test that HITL confidence threshold must be 0-1."""
        from pydantic import ValidationError

        from mcp_server_langgraph.core.feature_flags import FeatureFlags

        with pytest.raises(ValidationError):
            FeatureFlags(agent_hitl_confidence_threshold=1.5)

        with pytest.raises(ValidationError):
            FeatureFlags(agent_hitl_confidence_threshold=-0.1)

    @pytest.mark.unit
    def test_agent_hitl_auto_approve_threshold_default(self):
        """Test that auto-approve threshold defaults to 0.9."""
        from mcp_server_langgraph.core.feature_flags import FeatureFlags

        flags = FeatureFlags()
        assert flags.agent_hitl_auto_approve_threshold == 0.9

    @pytest.mark.unit
    def test_agent_hitl_auto_approve_threshold_configurable(self):
        """Test that auto-approve threshold is configurable."""
        from mcp_server_langgraph.core.feature_flags import FeatureFlags

        flags = FeatureFlags(agent_hitl_auto_approve_threshold=0.95)
        assert flags.agent_hitl_auto_approve_threshold == 0.95

    @pytest.mark.unit
    def test_agent_hitl_auto_approve_threshold_validation(self):
        """Test that auto-approve threshold must be 0-1."""
        from pydantic import ValidationError

        from mcp_server_langgraph.core.feature_flags import FeatureFlags

        with pytest.raises(ValidationError):
            FeatureFlags(agent_hitl_auto_approve_threshold=1.2)

        with pytest.raises(ValidationError):
            FeatureFlags(agent_hitl_auto_approve_threshold=-0.5)

    @pytest.mark.unit
    def test_agent_hitl_approval_timeout_seconds_default(self):
        """Test that approval timeout defaults to 3600 seconds (1 hour)."""
        from mcp_server_langgraph.core.feature_flags import FeatureFlags

        flags = FeatureFlags()
        assert flags.agent_hitl_approval_timeout_seconds == 3600

    @pytest.mark.unit
    def test_agent_hitl_approval_timeout_seconds_configurable(self):
        """Test that approval timeout is configurable."""
        from mcp_server_langgraph.core.feature_flags import FeatureFlags

        flags = FeatureFlags(agent_hitl_approval_timeout_seconds=7200)
        assert flags.agent_hitl_approval_timeout_seconds == 7200

    @pytest.mark.unit
    def test_agent_hitl_approval_timeout_validation(self):
        """Test that approval timeout has valid range (60s - 86400s)."""
        from pydantic import ValidationError

        from mcp_server_langgraph.core.feature_flags import FeatureFlags

        # Too low (less than 60 seconds)
        with pytest.raises(ValidationError):
            FeatureFlags(agent_hitl_approval_timeout_seconds=30)

        # Too high (more than 24 hours)
        with pytest.raises(ValidationError):
            FeatureFlags(agent_hitl_approval_timeout_seconds=100000)

    @pytest.mark.unit
    def test_enable_agent_hitl_push_notifications_default_true(self):
        """Test that HITL push notifications are enabled by default."""
        from mcp_server_langgraph.core.feature_flags import FeatureFlags

        flags = FeatureFlags()
        assert flags.enable_agent_hitl_push_notifications is True

    @pytest.mark.unit
    def test_enable_agent_hitl_push_notifications_configurable(self):
        """Test that HITL push notifications can be disabled."""
        from mcp_server_langgraph.core.feature_flags import FeatureFlags

        flags = FeatureFlags(enable_agent_hitl_push_notifications=False)
        assert flags.enable_agent_hitl_push_notifications is False

    @pytest.mark.unit
    def test_enable_agent_hitl_websocket_default_true(self):
        """Test that HITL WebSocket is enabled by default."""
        from mcp_server_langgraph.core.feature_flags import FeatureFlags

        flags = FeatureFlags()
        assert flags.enable_agent_hitl_websocket is True

    @pytest.mark.unit
    def test_enable_agent_hitl_websocket_configurable(self):
        """Test that HITL WebSocket can be disabled."""
        from mcp_server_langgraph.core.feature_flags import FeatureFlags

        flags = FeatureFlags(enable_agent_hitl_websocket=False)
        assert flags.enable_agent_hitl_websocket is False

    @pytest.mark.unit
    def test_get_ui_features_includes_hitl_flags(self):
        """Test that UI features include HITL flags."""
        from mcp_server_langgraph.core.feature_flags import FeatureFlags

        flags = FeatureFlags()
        features = flags.get_ui_features_for_role("admin")

        assert "agent_hitl" in features
        assert features["agent_hitl"] is True

    @pytest.mark.unit
    def test_get_ui_features_hitl_available_for_all_roles(self):
        """Test that HITL features are available to all roles."""
        from mcp_server_langgraph.core.feature_flags import FeatureFlags

        flags = FeatureFlags()

        admin_features = flags.get_ui_features_for_role("admin")
        user_features = flags.get_ui_features_for_role("user")
        viewer_features = flags.get_ui_features_for_role("viewer")

        assert admin_features["agent_hitl"] is True
        assert user_features["agent_hitl"] is True
        assert viewer_features["agent_hitl"] is True


@pytest.mark.xdist_group(name="feature_flags_redis_l2")
class TestFrontendRedisL2CacheFeatureFlags:
    """Test frontend Redis L2 cache feature flags for tiered caching."""

    def teardown_method(self) -> None:
        """Force GC to prevent mock accumulation in xdist workers."""
        gc.collect()

    @pytest.mark.unit
    def test_enable_frontend_redis_l2_cache_default_false(self):
        """Test that frontend Redis L2 cache is disabled by default."""
        from mcp_server_langgraph.core.feature_flags import FeatureFlags

        flags = FeatureFlags()
        assert flags.enable_frontend_redis_l2_cache is False

    @pytest.mark.unit
    def test_enable_frontend_redis_l2_cache_can_be_enabled(self):
        """Test that frontend Redis L2 cache can be enabled."""
        from mcp_server_langgraph.core.feature_flags import FeatureFlags

        flags = FeatureFlags(enable_frontend_redis_l2_cache=True)
        assert flags.enable_frontend_redis_l2_cache is True

    @pytest.mark.unit
    def test_frontend_redis_l2_cache_ttl_default(self):
        """Test default TTL for frontend Redis L2 cache."""
        from mcp_server_langgraph.core.feature_flags import FeatureFlags

        flags = FeatureFlags()
        assert flags.frontend_redis_l2_cache_ttl_seconds == 300  # 5 minutes

    @pytest.mark.unit
    def test_frontend_redis_l2_cache_ttl_configurable(self):
        """Test that TTL for frontend Redis L2 cache is configurable."""
        from mcp_server_langgraph.core.feature_flags import FeatureFlags

        flags = FeatureFlags(frontend_redis_l2_cache_ttl_seconds=600)
        assert flags.frontend_redis_l2_cache_ttl_seconds == 600

    @pytest.mark.unit
    def test_frontend_redis_l2_cache_ttl_validation(self):
        """Test TTL validation bounds (60s-3600s)."""
        from mcp_server_langgraph.core.feature_flags import FeatureFlags

        # Valid range
        flags_min = FeatureFlags(frontend_redis_l2_cache_ttl_seconds=60)
        assert flags_min.frontend_redis_l2_cache_ttl_seconds == 60

        flags_max = FeatureFlags(frontend_redis_l2_cache_ttl_seconds=3600)
        assert flags_max.frontend_redis_l2_cache_ttl_seconds == 3600

    @pytest.mark.unit
    def test_enable_frontend_redis_l2_cache_rate_limiting_default(self):
        """Test that rate limiting for frontend Redis L2 cache is enabled by default."""
        from mcp_server_langgraph.core.feature_flags import FeatureFlags

        flags = FeatureFlags()
        assert flags.enable_frontend_redis_l2_rate_limiting is True

    @pytest.mark.unit
    def test_frontend_redis_l2_rate_limit_configurable(self):
        """Test that rate limit for frontend Redis L2 cache is configurable."""
        from mcp_server_langgraph.core.feature_flags import FeatureFlags

        flags = FeatureFlags(frontend_redis_l2_rate_limit_per_minute=120)
        assert flags.frontend_redis_l2_rate_limit_per_minute == 120

    @pytest.mark.unit
    def test_get_ui_features_includes_frontend_redis_l2_cache(self):
        """Test that UI features include frontend Redis L2 cache flag."""
        from mcp_server_langgraph.core.feature_flags import FeatureFlags

        flags = FeatureFlags()
        features = flags.get_ui_features_for_role("admin")

        assert "frontend_redis_l2_cache" in features

    @pytest.mark.unit
    def test_frontend_redis_l2_cache_available_for_all_roles(self):
        """Test that frontend Redis L2 cache is available to all roles when enabled."""
        from mcp_server_langgraph.core.feature_flags import FeatureFlags

        flags = FeatureFlags(enable_frontend_redis_l2_cache=True)

        admin_features = flags.get_ui_features_for_role("admin")
        user_features = flags.get_ui_features_for_role("user")

        assert admin_features["frontend_redis_l2_cache"] is True
        assert user_features["frontend_redis_l2_cache"] is True


@pytest.mark.xdist_group(name="feature_flags_intelligence")
class TestGranularIntelligenceFeatureFlags:
    """Test granular intelligence feature flags for StudioShell AI capabilities.

    These flags provide fine-grained control over AI intelligence features:
    - Session Intelligence (summarize, group, similarity)
    - Conversation Intelligence (intent, context, goal)
    - Canvas Intelligence (artifact, code, diff)
    - Diagram Intelligence (analyze, to-code)
    - Trace Intelligence (summarize, anomaly)
    - HITL AI (risk assessment, decision history)
    - Generative UI (dynamic component rendering)
    """

    def teardown_method(self) -> None:
        """Force GC to prevent mock accumulation in xdist workers."""
        gc.collect()

    @pytest.mark.unit
    def test_enable_session_intelligence_default_false(self):
        """Test that session intelligence is disabled by default."""
        from mcp_server_langgraph.core.feature_flags import FeatureFlags

        flags = FeatureFlags()
        assert flags.enable_session_intelligence is False

    @pytest.mark.unit
    def test_enable_session_intelligence_can_be_enabled(self):
        """Test that session intelligence can be enabled."""
        from mcp_server_langgraph.core.feature_flags import FeatureFlags

        flags = FeatureFlags(enable_session_intelligence=True)
        assert flags.enable_session_intelligence is True

    @pytest.mark.unit
    def test_enable_conversation_intelligence_default_false(self):
        """Test that conversation intelligence is disabled by default."""
        from mcp_server_langgraph.core.feature_flags import FeatureFlags

        flags = FeatureFlags()
        assert flags.enable_conversation_intelligence is False

    @pytest.mark.unit
    def test_enable_conversation_intelligence_can_be_enabled(self):
        """Test that conversation intelligence can be enabled."""
        from mcp_server_langgraph.core.feature_flags import FeatureFlags

        flags = FeatureFlags(enable_conversation_intelligence=True)
        assert flags.enable_conversation_intelligence is True

    @pytest.mark.unit
    def test_enable_canvas_intelligence_default_false(self):
        """Test that canvas intelligence is disabled by default."""
        from mcp_server_langgraph.core.feature_flags import FeatureFlags

        flags = FeatureFlags()
        assert flags.enable_canvas_intelligence is False

    @pytest.mark.unit
    def test_enable_canvas_intelligence_can_be_enabled(self):
        """Test that canvas intelligence can be enabled."""
        from mcp_server_langgraph.core.feature_flags import FeatureFlags

        flags = FeatureFlags(enable_canvas_intelligence=True)
        assert flags.enable_canvas_intelligence is True

    @pytest.mark.unit
    def test_enable_diagram_intelligence_default_false(self):
        """Test that diagram intelligence is disabled by default."""
        from mcp_server_langgraph.core.feature_flags import FeatureFlags

        flags = FeatureFlags()
        assert flags.enable_diagram_intelligence is False

    @pytest.mark.unit
    def test_enable_diagram_intelligence_can_be_enabled(self):
        """Test that diagram intelligence can be enabled."""
        from mcp_server_langgraph.core.feature_flags import FeatureFlags

        flags = FeatureFlags(enable_diagram_intelligence=True)
        assert flags.enable_diagram_intelligence is True

    @pytest.mark.unit
    def test_enable_trace_intelligence_default_false(self):
        """Test that trace intelligence is disabled by default."""
        from mcp_server_langgraph.core.feature_flags import FeatureFlags

        flags = FeatureFlags()
        assert flags.enable_trace_intelligence is False

    @pytest.mark.unit
    def test_enable_trace_intelligence_can_be_enabled(self):
        """Test that trace intelligence can be enabled."""
        from mcp_server_langgraph.core.feature_flags import FeatureFlags

        flags = FeatureFlags(enable_trace_intelligence=True)
        assert flags.enable_trace_intelligence is True

    @pytest.mark.unit
    def test_enable_hitl_ai_default_false(self):
        """Test that HITL AI is disabled by default."""
        from mcp_server_langgraph.core.feature_flags import FeatureFlags

        flags = FeatureFlags()
        assert flags.enable_hitl_ai is False

    @pytest.mark.unit
    def test_enable_hitl_ai_can_be_enabled(self):
        """Test that HITL AI can be enabled."""
        from mcp_server_langgraph.core.feature_flags import FeatureFlags

        flags = FeatureFlags(enable_hitl_ai=True)
        assert flags.enable_hitl_ai is True

    @pytest.mark.unit
    def test_enable_genui_default_false(self):
        """Test that generative UI is disabled by default."""
        from mcp_server_langgraph.core.feature_flags import FeatureFlags

        flags = FeatureFlags()
        assert flags.enable_genui is False

    @pytest.mark.unit
    def test_enable_genui_can_be_enabled(self):
        """Test that generative UI can be enabled."""
        from mcp_server_langgraph.core.feature_flags import FeatureFlags

        flags = FeatureFlags(enable_genui=True)
        assert flags.enable_genui is True

    @pytest.mark.unit
    def test_granular_flags_require_studio_ai_master_flag(self):
        """Test that granular flags only take effect when enable_studio_ai is True."""
        from mcp_server_langgraph.core.feature_flags import FeatureFlags

        # Granular flags enabled but master disabled - should report not ready
        flags = FeatureFlags(
            enable_studio_ai=False,
            enable_session_intelligence=True,
            enable_canvas_intelligence=True,
        )
        # Granular flags still have their values
        assert flags.enable_session_intelligence is True
        assert flags.enable_canvas_intelligence is True
        # But master flag is off
        assert flags.enable_studio_ai is False

    @pytest.mark.unit
    def test_all_granular_flags_enabled_together(self):
        """Test enabling all granular intelligence flags together."""
        from mcp_server_langgraph.core.feature_flags import FeatureFlags

        flags = FeatureFlags(
            enable_studio_ai=True,
            enable_session_intelligence=True,
            enable_conversation_intelligence=True,
            enable_canvas_intelligence=True,
            enable_diagram_intelligence=True,
            enable_trace_intelligence=True,
            enable_hitl_ai=True,
            enable_genui=True,
        )
        assert flags.enable_studio_ai is True
        assert flags.enable_session_intelligence is True
        assert flags.enable_conversation_intelligence is True
        assert flags.enable_canvas_intelligence is True
        assert flags.enable_diagram_intelligence is True
        assert flags.enable_trace_intelligence is True
        assert flags.enable_hitl_ai is True
        assert flags.enable_genui is True

    @pytest.mark.unit
    def test_get_ui_features_includes_intelligence_flags(self):
        """Test that UI features include intelligence flags."""
        from mcp_server_langgraph.core.feature_flags import FeatureFlags

        flags = FeatureFlags()
        features = flags.get_ui_features_for_role("admin")

        # Verify intelligence flags are included in UI features
        assert "session_intelligence" in features
        assert "conversation_intelligence" in features
        assert "canvas_intelligence" in features
        assert "diagram_intelligence" in features
        assert "trace_intelligence" in features
        assert "hitl_ai" in features
        assert "genui" in features

    @pytest.mark.unit
    def test_intelligence_flags_in_ui_features_default_false(self):
        """Test that intelligence flags in UI features are False by default."""
        from mcp_server_langgraph.core.feature_flags import FeatureFlags

        flags = FeatureFlags()
        features = flags.get_ui_features_for_role("admin")

        assert features["session_intelligence"] is False
        assert features["conversation_intelligence"] is False
        assert features["canvas_intelligence"] is False
        assert features["diagram_intelligence"] is False
        assert features["trace_intelligence"] is False
        assert features["hitl_ai"] is False
        assert features["genui"] is False

    @pytest.mark.unit
    def test_intelligence_flags_in_ui_features_when_enabled(self):
        """Test that intelligence flags appear in UI features when enabled."""
        from mcp_server_langgraph.core.feature_flags import FeatureFlags

        flags = FeatureFlags(
            enable_session_intelligence=True,
            enable_canvas_intelligence=True,
        )
        features = flags.get_ui_features_for_role("admin")

        assert features["session_intelligence"] is True
        assert features["canvas_intelligence"] is True
        # Others still False
        assert features["conversation_intelligence"] is False


@pytest.mark.xdist_group(name="feature_flags_consolidation")
class TestFeatureFlagConsolidation:
    """Test Sprint Block 5 feature flag consolidation methods.

    Tests for unified helper methods and strategy enums that replace deprecated flags:
    - get_rate_limit(feature) - Unified rate limiting with feature-specific overrides
    - get_cache_ttl(feature) - Unified cache TTL with feature-specific overrides
    - effective_suggestion_strategy - Backward-compatible suggestion strategy
    - multi_agent_strategy - Multi-agent coordination strategy enum
    - suggestion_strategy - Suggestion generation strategy enum
    """

    def teardown_method(self) -> None:
        """Force GC to prevent mock accumulation in xdist workers."""
        gc.collect()

    # =========================================================================
    # get_rate_limit() Tests
    # =========================================================================

    @pytest.mark.unit
    def test_get_rate_limit_api_returns_rate_limit_requests_per_minute(self):
        """Test get_rate_limit returns API rate limit for 'api' feature."""
        from mcp_server_langgraph.core.feature_flags import FeatureFlags

        flags = FeatureFlags(rate_limit_requests_per_minute=100)
        assert flags.get_rate_limit("api") == 100

    @pytest.mark.unit
    def test_get_rate_limit_none_returns_rate_limit_requests_per_minute(self):
        """Test get_rate_limit returns API rate limit when feature is None."""
        from mcp_server_langgraph.core.feature_flags import FeatureFlags

        flags = FeatureFlags(rate_limit_requests_per_minute=100)
        assert flags.get_rate_limit(None) == 100
        assert flags.get_rate_limit() == 100  # Default argument

    @pytest.mark.unit
    def test_get_rate_limit_suggestions_returns_suggestion_rate_limit(self):
        """Test get_rate_limit returns suggestion-specific rate limit."""
        from mcp_server_langgraph.core.feature_flags import FeatureFlags

        flags = FeatureFlags(suggestion_rate_limit_per_minute=120)
        assert flags.get_rate_limit("suggestions") == 120

    @pytest.mark.unit
    def test_get_rate_limit_frontend_cache_returns_frontend_rate_limit(self):
        """Test get_rate_limit returns frontend cache rate limit."""
        from mcp_server_langgraph.core.feature_flags import FeatureFlags

        flags = FeatureFlags(frontend_redis_l2_rate_limit_per_minute=90)
        assert flags.get_rate_limit("frontend_cache") == 90

    @pytest.mark.unit
    def test_get_rate_limit_websocket_returns_websocket_rate_limit(self):
        """Test get_rate_limit returns WebSocket rate limit."""
        from mcp_server_langgraph.core.feature_flags import FeatureFlags

        flags = FeatureFlags(websocket_rate_limit_per_minute=200)
        assert flags.get_rate_limit("websocket") == 200

    @pytest.mark.unit
    def test_get_rate_limit_unknown_feature_returns_default(self):
        """Test get_rate_limit returns default for unknown features."""
        from mcp_server_langgraph.core.feature_flags import FeatureFlags

        flags = FeatureFlags(default_rate_limit_per_minute=75)
        assert flags.get_rate_limit("unknown_feature") == 75
        assert flags.get_rate_limit("custom_endpoint") == 75

    @pytest.mark.unit
    def test_get_rate_limit_default_rate_limit_per_minute_default_value(self):
        """Test default_rate_limit_per_minute has correct default value."""
        from mcp_server_langgraph.core.feature_flags import FeatureFlags

        flags = FeatureFlags()
        assert flags.default_rate_limit_per_minute == 60

    # =========================================================================
    # get_cache_ttl() Tests
    # =========================================================================

    @pytest.mark.unit
    def test_get_cache_ttl_llm_returns_cache_ttl_seconds(self):
        """Test get_cache_ttl returns LLM cache TTL."""
        from mcp_server_langgraph.core.feature_flags import FeatureFlags

        flags = FeatureFlags(cache_ttl_seconds=600)
        assert flags.get_cache_ttl("llm") == 600

    @pytest.mark.unit
    def test_get_cache_ttl_suggestions_returns_suggestion_cache_ttl(self):
        """Test get_cache_ttl returns suggestion-specific cache TTL."""
        from mcp_server_langgraph.core.feature_flags import FeatureFlags

        flags = FeatureFlags(suggestion_cache_ttl_seconds=450)
        assert flags.get_cache_ttl("suggestions") == 450

    @pytest.mark.unit
    def test_get_cache_ttl_ai_ux_returns_ai_ux_cache_ttl(self):
        """Test get_cache_ttl returns AI UX cache TTL."""
        from mcp_server_langgraph.core.feature_flags import FeatureFlags

        flags = FeatureFlags(ai_ux_redis_cache_ttl_seconds=180)
        assert flags.get_cache_ttl("ai_ux") == 180

    @pytest.mark.unit
    def test_get_cache_ttl_frontend_cache_returns_frontend_cache_ttl(self):
        """Test get_cache_ttl returns frontend cache TTL."""
        from mcp_server_langgraph.core.feature_flags import FeatureFlags

        flags = FeatureFlags(frontend_redis_l2_cache_ttl_seconds=360)
        assert flags.get_cache_ttl("frontend_cache") == 360

    @pytest.mark.unit
    def test_get_cache_ttl_openfga_returns_openfga_cache_ttl(self):
        """Test get_cache_ttl returns OpenFGA cache TTL."""
        from mcp_server_langgraph.core.feature_flags import FeatureFlags

        flags = FeatureFlags(openfga_cache_ttl_seconds=240)
        assert flags.get_cache_ttl("openfga") == 240

    @pytest.mark.unit
    def test_get_cache_ttl_unknown_feature_returns_default(self):
        """Test get_cache_ttl returns default for unknown features."""
        from mcp_server_langgraph.core.feature_flags import FeatureFlags

        flags = FeatureFlags(default_cache_ttl_seconds=500)
        assert flags.get_cache_ttl("unknown_feature") == 500
        assert flags.get_cache_ttl("custom_cache") == 500

    @pytest.mark.unit
    def test_get_cache_ttl_none_returns_default(self):
        """Test get_cache_ttl returns default when feature is None."""
        from mcp_server_langgraph.core.feature_flags import FeatureFlags

        flags = FeatureFlags(default_cache_ttl_seconds=400)
        assert flags.get_cache_ttl(None) == 400
        assert flags.get_cache_ttl() == 400  # Default argument

    @pytest.mark.unit
    def test_get_cache_ttl_default_cache_ttl_seconds_default_value(self):
        """Test default_cache_ttl_seconds has correct default value."""
        from mcp_server_langgraph.core.feature_flags import FeatureFlags

        flags = FeatureFlags()
        assert flags.default_cache_ttl_seconds == 300

    # =========================================================================
    # effective_suggestion_strategy Tests
    # =========================================================================

    @pytest.mark.unit
    def test_effective_suggestion_strategy_returns_llm_by_default(self):
        """Test effective_suggestion_strategy returns 'llm' by default."""
        from mcp_server_langgraph.core.feature_flags import FeatureFlags

        flags = FeatureFlags()
        assert flags.effective_suggestion_strategy == "llm"

    @pytest.mark.unit
    def test_effective_suggestion_strategy_returns_heuristic_when_llm_disabled(self):
        """Test effective_suggestion_strategy returns 'heuristic' when deprecated flag is False."""
        from mcp_server_langgraph.core.feature_flags import FeatureFlags

        flags = FeatureFlags(enable_llm_suggestions=False)
        assert flags.effective_suggestion_strategy == "heuristic"

    @pytest.mark.unit
    def test_effective_suggestion_strategy_respects_new_strategy_field(self):
        """Test effective_suggestion_strategy uses new suggestion_strategy field."""
        from mcp_server_langgraph.core.feature_flags import FeatureFlags

        flags = FeatureFlags(suggestion_strategy="hybrid")
        assert flags.effective_suggestion_strategy == "hybrid"

    @pytest.mark.unit
    def test_effective_suggestion_strategy_deprecated_flag_overrides_strategy(self):
        """Test deprecated enable_llm_suggestions=False overrides suggestion_strategy."""
        from mcp_server_langgraph.core.feature_flags import FeatureFlags

        # Even with strategy="llm", disabled deprecated flag forces heuristic
        flags = FeatureFlags(suggestion_strategy="llm", enable_llm_suggestions=False)
        assert flags.effective_suggestion_strategy == "heuristic"

    # =========================================================================
    # suggestion_strategy Tests
    # =========================================================================

    @pytest.mark.unit
    def test_suggestion_strategy_default_is_llm(self):
        """Test suggestion_strategy defaults to 'llm'."""
        from mcp_server_langgraph.core.feature_flags import FeatureFlags

        flags = FeatureFlags()
        assert flags.suggestion_strategy == "llm"

    @pytest.mark.unit
    def test_suggestion_strategy_can_be_set_to_heuristic(self):
        """Test suggestion_strategy can be set to 'heuristic'."""
        from mcp_server_langgraph.core.feature_flags import FeatureFlags

        flags = FeatureFlags(suggestion_strategy="heuristic")
        assert flags.suggestion_strategy == "heuristic"

    @pytest.mark.unit
    def test_suggestion_strategy_can_be_set_to_hybrid(self):
        """Test suggestion_strategy can be set to 'hybrid'."""
        from mcp_server_langgraph.core.feature_flags import FeatureFlags

        flags = FeatureFlags(suggestion_strategy="hybrid")
        assert flags.suggestion_strategy == "hybrid"

    @pytest.mark.unit
    def test_suggestion_strategy_included_in_ui_features(self):
        """Test suggestion_strategy is included in get_ui_features_for_role."""
        from mcp_server_langgraph.core.feature_flags import FeatureFlags

        flags = FeatureFlags(suggestion_strategy="hybrid")
        features = flags.get_ui_features_for_role("admin")
        assert features["suggestion_strategy"] == "hybrid"

    # =========================================================================
    # multi_agent_strategy Tests
    # =========================================================================

    @pytest.mark.unit
    def test_multi_agent_strategy_default_is_orchestrator(self):
        """Test multi_agent_strategy defaults to 'orchestrator'."""
        from mcp_server_langgraph.core.feature_flags import FeatureFlags

        flags = FeatureFlags()
        assert flags.multi_agent_strategy == "orchestrator"

    @pytest.mark.unit
    def test_multi_agent_strategy_can_be_set_to_peer(self):
        """Test multi_agent_strategy can be set to 'peer'."""
        from mcp_server_langgraph.core.feature_flags import FeatureFlags

        flags = FeatureFlags(multi_agent_strategy="peer")
        assert flags.multi_agent_strategy == "peer"

    @pytest.mark.unit
    def test_multi_agent_strategy_can_be_set_to_hybrid(self):
        """Test multi_agent_strategy can be set to 'hybrid'."""
        from mcp_server_langgraph.core.feature_flags import FeatureFlags

        flags = FeatureFlags(multi_agent_strategy="hybrid")
        assert flags.multi_agent_strategy == "hybrid"

    @pytest.mark.unit
    def test_enable_multi_agent_collaboration_is_removed(self):
        """Test enable_multi_agent_collaboration flag was removed."""
        from mcp_server_langgraph.core.feature_flags import FeatureFlags

        flags = FeatureFlags()
        # The deprecated flag should not exist
        assert not hasattr(flags, "enable_multi_agent_collaboration")
