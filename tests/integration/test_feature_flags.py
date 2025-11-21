"""Unit tests for feature flags system"""

import gc
import os
from unittest.mock import patch

import pytest

pytestmark = pytest.mark.integration


@pytest.mark.unit
@pytest.mark.xdist_group(name="testfeatureflags")
class TestFeatureFlags:
    """Test Feature Flag system"""

    def teardown_method(self) -> None:
        """Force GC to prevent mock accumulation in xdist workers"""
        gc.collect()

    def test_default_feature_flags(self):
        """Test default feature flag values"""
        from mcp_server_langgraph.core.feature_flags import FeatureFlags

        flags = FeatureFlags()

        # Verify critical defaults
        assert flags.enable_pydantic_ai_routing is True
        assert flags.enable_pydantic_ai_responses is True
        assert flags.enable_llm_fallback is True
        assert flags.enable_openfga is True
        assert flags.openfga_strict_mode is False  # Fail-open by default
        assert flags.enable_experimental_features is False

    def test_environment_variable_override(self):
        """Test that environment variables override defaults"""
        from mcp_server_langgraph.core.feature_flags import FeatureFlags

        with patch.dict(
            os.environ,
            {
                "FF_ENABLE_PYDANTIC_AI_ROUTING": "false",
                "FF_ENABLE_LANGSMITH": "true",
                "FF_OPENFGA_STRICT_MODE": "true",
            },
        ):
            flags = FeatureFlags()

            assert flags.enable_pydantic_ai_routing is False
            assert flags.enable_langsmith is True
            assert flags.openfga_strict_mode is True

    def test_numeric_flag_validation(self):
        """Test numeric flag values and validation"""
        from mcp_server_langgraph.core.feature_flags import FeatureFlags

        flags = FeatureFlags()

        # Test default numeric values
        assert flags.pydantic_ai_confidence_threshold == 0.7
        assert flags.llm_timeout_seconds == 60
        assert flags.max_agent_iterations == 10
        assert flags.rate_limit_requests_per_minute == 60

    def test_numeric_flag_constraints(self):
        """Test numeric flags enforce min/max constraints"""
        from pydantic import ValidationError

        from mcp_server_langgraph.core.feature_flags import FeatureFlags

        # Test confidence threshold must be between 0 and 1
        with pytest.raises(ValidationError):
            FeatureFlags(pydantic_ai_confidence_threshold=1.5)

        with pytest.raises(ValidationError):
            FeatureFlags(pydantic_ai_confidence_threshold=-0.1)

        # Valid values should work
        flags = FeatureFlags(pydantic_ai_confidence_threshold=0.9)
        assert flags.pydantic_ai_confidence_threshold == 0.9

    def test_is_feature_enabled(self):
        """Test is_feature_enabled helper method"""
        from mcp_server_langgraph.core.feature_flags import FeatureFlags

        flags = FeatureFlags()

        assert flags.is_feature_enabled("enable_pydantic_ai_routing") is True
        assert flags.is_feature_enabled("enable_langsmith") is False
        assert flags.is_feature_enabled("nonexistent_flag") is False

    def test_get_feature_value(self):
        """Test get_feature_value with defaults"""
        from mcp_server_langgraph.core.feature_flags import FeatureFlags

        flags = FeatureFlags()

        # Existing flag
        assert flags.get_feature_value("llm_timeout_seconds") == 60

        # Non-existing flag with default
        assert flags.get_feature_value("nonexistent_flag", "default_value") == "default_value"

        # Non-existing flag without default
        assert flags.get_feature_value("nonexistent_flag") is None

    def test_experimental_features_master_switch(self):
        """Test experimental features require master switch"""
        from mcp_server_langgraph.core.feature_flags import FeatureFlags

        # Master switch off
        flags = FeatureFlags(
            enable_experimental_features=False, enable_multi_agent_collaboration=True, enable_tool_reflection=True
        )

        assert flags.should_use_experimental("enable_multi_agent_collaboration") is False
        assert flags.should_use_experimental("enable_tool_reflection") is False

        # Master switch on
        flags = FeatureFlags(
            enable_experimental_features=True, enable_multi_agent_collaboration=True, enable_tool_reflection=False
        )

        assert flags.should_use_experimental("enable_multi_agent_collaboration") is True
        assert flags.should_use_experimental("enable_tool_reflection") is False

    def test_global_feature_flags_instance(self):
        """Test global feature flags singleton"""
        from mcp_server_langgraph.core.feature_flags import feature_flags, get_feature_flags

        assert feature_flags is not None
        assert get_feature_flags() is feature_flags

    def test_is_enabled_convenience_function(self):
        """Test is_enabled convenience function"""
        from mcp_server_langgraph.core.feature_flags import is_enabled

        # Should use global instance
        assert is_enabled("enable_pydantic_ai_routing") in [True, False]
        assert isinstance(is_enabled("enable_langsmith"), bool)

    def test_cache_configuration(self):
        """Test caching feature flags"""
        from mcp_server_langgraph.core.feature_flags import FeatureFlags

        flags = FeatureFlags(enable_response_caching=True, cache_ttl_seconds=600, enable_request_batching=True)

        assert flags.enable_response_caching is True
        assert flags.cache_ttl_seconds == 600
        assert flags.enable_request_batching is True

    def test_security_flags(self):
        """Test security-related feature flags"""
        from mcp_server_langgraph.core.feature_flags import FeatureFlags

        flags = FeatureFlags()

        assert flags.enable_rate_limiting is True
        assert flags.enable_input_validation is True
        assert flags.rate_limit_requests_per_minute > 0
        assert flags.max_input_length > 0

    def test_observability_flags(self):
        """Test observability feature flags"""
        from mcp_server_langgraph.core.feature_flags import FeatureFlags

        flags = FeatureFlags(
            enable_detailed_logging=True, enable_trace_sampling=True, trace_sample_rate=0.25, enable_langsmith=True
        )

        assert flags.enable_detailed_logging is True
        assert flags.enable_trace_sampling is True
        assert flags.trace_sample_rate == 0.25
        assert flags.enable_langsmith is True

    def test_agent_behavior_flags(self):
        """Test agent behavior configuration"""
        from mcp_server_langgraph.core.feature_flags import FeatureFlags

        flags = FeatureFlags(max_agent_iterations=25, enable_agent_memory=True, memory_max_messages=500)

        assert flags.max_agent_iterations == 25
        assert flags.enable_agent_memory is True
        assert flags.memory_max_messages == 500

    def test_openfga_configuration(self):
        """Test OpenFGA feature flags"""
        from mcp_server_langgraph.core.feature_flags import FeatureFlags

        # Default: fail-open (permissive)
        flags1 = FeatureFlags()
        assert flags1.enable_openfga is True
        assert flags1.openfga_strict_mode is False

        # Strict mode: fail-closed
        flags2 = FeatureFlags(openfga_strict_mode=True)
        assert flags2.openfga_strict_mode is True

    @pytest.mark.xfail(strict=True, reason="Integration with config.py not yet implemented")
    @pytest.mark.integration
    def test_feature_flag_integration_with_config(self):
        """Test feature flags integrate with main config"""
        # This would test integration with config.py
        # Will be implemented when config.py is updated
        pytest.fail("Feature flag integration with config.py not yet implemented")


@pytest.mark.unit
@pytest.mark.xdist_group(name="testfeatureflagedgecases")
class TestFeatureFlagEdgeCases:
    """Test edge cases and error handling"""

    def teardown_method(self) -> None:
        """Force GC to prevent mock accumulation in xdist workers"""
        gc.collect()

    def test_invalid_confidence_threshold(self):
        """Test confidence threshold validation"""
        from pydantic import ValidationError

        from mcp_server_langgraph.core.feature_flags import FeatureFlags

        # Too high
        with pytest.raises(ValidationError):
            FeatureFlags(pydantic_ai_confidence_threshold=2.0)

        # Too low
        with pytest.raises(ValidationError):
            FeatureFlags(pydantic_ai_confidence_threshold=-1.0)

    def test_invalid_timeout(self):
        """Test timeout validation"""
        from pydantic import ValidationError

        from mcp_server_langgraph.core.feature_flags import FeatureFlags

        # Too low
        with pytest.raises(ValidationError):
            FeatureFlags(llm_timeout_seconds=5)

        # Too high
        with pytest.raises(ValidationError):
            FeatureFlags(llm_timeout_seconds=400)

    def test_invalid_sample_rate(self):
        """Test sample rate validation"""
        from pydantic import ValidationError

        from mcp_server_langgraph.core.feature_flags import FeatureFlags

        with pytest.raises(ValidationError):
            FeatureFlags(trace_sample_rate=1.5)

        with pytest.raises(ValidationError):
            FeatureFlags(trace_sample_rate=-0.5)

    def test_boolean_string_conversion(self):
        """Test that string 'true'/'false' are converted correctly"""
        from mcp_server_langgraph.core.feature_flags import FeatureFlags

        with patch.dict(
            os.environ,
            {
                "FF_ENABLE_PYDANTIC_AI_ROUTING": "True",
                "FF_ENABLE_LANGSMITH": "FALSE",
                "FF_ENABLE_OPENFGA": "1",
                "FF_OPENFGA_STRICT_MODE": "0",
            },
        ):
            flags = FeatureFlags()

            assert flags.enable_pydantic_ai_routing is True
            assert flags.enable_langsmith is False
            assert flags.enable_openfga is True
            assert flags.openfga_strict_mode is False
