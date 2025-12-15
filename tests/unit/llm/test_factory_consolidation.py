"""
Tests for LLM Factory Consolidation (DRY refactoring).

TDD: Write tests FIRST, then implementation.

This tests the consolidated create_model function that replaces
the separate create_summarization_model and create_verification_model functions.
"""

import gc

import pytest
from unittest.mock import Mock

from mcp_server_langgraph.llm.factory import (
    LLMFactory,
    create_llm_from_config,
    create_model,
    ModelType,
)

# Mark all tests in this module as unit tests
pytestmark = pytest.mark.unit


class TestModelTypeEnum:
    """Test the ModelType enum for different model purposes."""

    def test_model_type_has_primary(self):
        """Primary model type should exist."""
        assert ModelType.PRIMARY is not None
        assert ModelType.PRIMARY.value == "primary"

    def test_model_type_has_summarization(self):
        """Summarization model type should exist."""
        assert ModelType.SUMMARIZATION is not None
        assert ModelType.SUMMARIZATION.value == "summarization"

    def test_model_type_has_verification(self):
        """Verification model type should exist."""
        assert ModelType.VERIFICATION is not None
        assert ModelType.VERIFICATION.value == "verification"


class TestCreateModelFunction:
    """Test the consolidated create_model function."""

    @pytest.fixture
    def mock_config(self):
        """Create a mock config object with all required attributes."""
        config = Mock()
        # Primary model settings
        config.llm_provider = "google"
        config.model_name = "gemini-2.5-flash"
        config.model_temperature = 0.7
        config.model_max_tokens = 4096
        config.model_timeout = 60
        config.enable_fallback = False
        config.fallback_models = []
        # Summarization model settings
        config.use_dedicated_summarization_model = False
        config.summarization_model_provider = None
        config.summarization_model_name = None
        config.summarization_model_temperature = 0.3
        config.summarization_model_max_tokens = 2048
        # Verification model settings
        config.use_dedicated_verification_model = False
        config.verification_model_provider = None
        config.verification_model_name = None
        config.verification_model_temperature = 0.0
        config.verification_model_max_tokens = 1024
        return config

    def test_create_model_primary_returns_factory(self, mock_config):
        """create_model with PRIMARY type returns LLMFactory."""
        factory = create_model(mock_config, ModelType.PRIMARY)
        assert isinstance(factory, LLMFactory)

    def test_create_model_primary_uses_primary_settings(self, mock_config):
        """create_model with PRIMARY uses primary model settings."""
        factory = create_model(mock_config, ModelType.PRIMARY)
        assert factory.model_name == "gemini-2.5-flash"
        assert factory.temperature == 0.7
        assert factory.max_tokens == 4096

    def test_create_model_summarization_fallback_to_primary(self, mock_config):
        """Summarization falls back to primary when not explicitly enabled."""
        mock_config.use_dedicated_summarization_model = False
        factory = create_model(mock_config, ModelType.SUMMARIZATION)
        # Should use primary model settings
        assert factory.model_name == "gemini-2.5-flash"

    def test_create_model_summarization_uses_dedicated_when_enabled(self, mock_config):
        """Summarization uses dedicated model when explicitly enabled."""
        mock_config.use_dedicated_summarization_model = True
        mock_config.summarization_model_provider = "anthropic"
        mock_config.summarization_model_name = "claude-3-haiku"
        mock_config.anthropic_api_key = "test-key"

        factory = create_model(mock_config, ModelType.SUMMARIZATION)
        assert factory.model_name == "claude-3-haiku"
        assert factory.temperature == 0.3
        assert factory.max_tokens == 2048

    def test_create_model_verification_fallback_to_primary(self, mock_config):
        """Verification falls back to primary when not explicitly enabled."""
        mock_config.use_dedicated_verification_model = False
        factory = create_model(mock_config, ModelType.VERIFICATION)
        # Should use primary model settings
        assert factory.model_name == "gemini-2.5-flash"

    def test_create_model_verification_uses_dedicated_when_enabled(self, mock_config):
        """Verification uses dedicated model when explicitly enabled."""
        mock_config.use_dedicated_verification_model = True
        mock_config.verification_model_provider = "openai"
        mock_config.verification_model_name = "gpt-4o"
        mock_config.openai_api_key = "test-key"

        factory = create_model(mock_config, ModelType.VERIFICATION)
        assert factory.model_name == "gpt-4o"
        assert factory.temperature == 0.0
        assert factory.max_tokens == 1024

    def test_create_model_summarization_inherits_provider_when_not_set(self, mock_config):
        """Summarization inherits primary provider when not explicitly set."""
        mock_config.use_dedicated_summarization_model = True
        mock_config.summarization_model_provider = None  # Not set
        mock_config.summarization_model_name = "gemini-2.5-flash-lite"

        factory = create_model(mock_config, ModelType.SUMMARIZATION)
        # Should inherit provider from primary
        assert factory.provider == "google"


@pytest.mark.xdist_group(name="llm_factory_backward_compat")
class TestBackwardCompatibility:
    """Test that existing functions still work (backward compatibility)."""

    def teardown_method(self):
        """Force GC to prevent mock accumulation in xdist workers"""
        gc.collect()

    @pytest.fixture
    def mock_config(self):
        """Create a mock config object."""
        config = Mock()
        config.llm_provider = "google"
        config.model_name = "gemini-2.5-flash"
        config.model_temperature = 0.7
        config.model_max_tokens = 4096
        config.model_timeout = 60
        config.enable_fallback = False
        config.fallback_models = []
        config.use_dedicated_summarization_model = False
        config.use_dedicated_verification_model = False
        return config

    def test_create_llm_from_config_still_works(self, mock_config):
        """Existing create_llm_from_config function still works."""
        factory = create_llm_from_config(mock_config)
        assert isinstance(factory, LLMFactory)
        assert factory.model_name == "gemini-2.5-flash"

    def test_create_summarization_model_still_works(self, mock_config):
        """Existing create_summarization_model function still works."""
        from mcp_server_langgraph.llm.factory import create_summarization_model

        factory = create_summarization_model(mock_config)
        # Use type name check to avoid xdist module reimport issues with isinstance
        assert type(factory).__name__ == "LLMFactory"

    def test_create_verification_model_still_works(self, mock_config):
        """Existing create_verification_model function still works."""
        from mcp_server_langgraph.llm.factory import create_verification_model

        factory = create_verification_model(mock_config)
        # Use type name check to avoid xdist module reimport issues with isinstance
        assert type(factory).__name__ == "LLMFactory"
