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
