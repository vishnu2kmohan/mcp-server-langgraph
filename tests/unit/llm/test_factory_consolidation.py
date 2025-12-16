"""
Tests for LLM Factory Consolidation (DRY refactoring).

TDD: Write tests FIRST, then implementation.

This tests the consolidated create_model function that replaces
the separate create_summarization_model and create_verification_model functions.
"""

import gc
import os

import pytest
from unittest.mock import MagicMock, Mock

from mcp_server_langgraph.llm.factory import (
    LLMFactory,
    _get_provider_kwargs,
    create_llm_from_config,
    create_model,
    ModelType,
)

# Mark all tests in this module as unit tests
pytestmark = pytest.mark.unit


@pytest.mark.xdist_group(name="testmodeltypeenum")
class TestModelTypeEnum:
    """Test the ModelType enum for different model purposes."""

    def teardown_method(self):
        """Force GC to prevent mock accumulation in xdist workers."""
        gc.collect()

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


@pytest.mark.xdist_group(name="testcreatemodelfunction")
class TestCreateModelFunction:
    """Test the consolidated create_model function."""

    def teardown_method(self):
        """Force GC to prevent mock accumulation in xdist workers."""
        gc.collect()

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


@pytest.mark.xdist_group(name="vertex_location_always_passed")
class TestVertexLocationAlwaysPassed:
    """
    Test that vertex_location is always passed to LiteLLM for Vertex AI.

    Regression test for bug where vertex_location was only passed when
    vertex_project was also set. This caused LiteLLM to use its default
    location (us-central1) even when VERTEX_LOCATION=global was configured.
    """

    def teardown_method(self):
        """Force GC to prevent mock accumulation in xdist workers."""
        gc.collect()

    @pytest.fixture
    def mock_config_vertex_no_project(self):
        """Config with vertex_location but NO vertex_project (uses ADC)."""
        config = Mock()
        config.vertex_project = None
        config.google_project_id = None
        config.vertex_location = "global"  # Should be passed even without project
        return config

    @pytest.fixture
    def mock_config_vertex_with_project(self):
        """Config with both vertex_location and vertex_project."""
        config = Mock()
        config.vertex_project = "my-gcp-project"
        config.google_project_id = None
        config.vertex_location = "us-east5"
        return config

    def test_vertex_location_passed_without_project(self, mock_config_vertex_no_project):
        """vertex_location MUST be passed even when vertex_project is not set.

        GIVEN: Config with vertex_location="global" but no vertex_project
        WHEN: _get_provider_kwargs is called for vertex_ai provider
        THEN: vertex_location should be in the returned kwargs
        """
        kwargs = _get_provider_kwargs(mock_config_vertex_no_project, "vertex_ai")

        assert "vertex_location" in kwargs, (
            "vertex_location must be passed to LiteLLM even without vertex_project. "
            "LiteLLM can auto-detect project via ADC but NOT location."
        )
        assert kwargs["vertex_location"] == "global"

    def test_vertex_project_not_passed_when_not_set(self, mock_config_vertex_no_project):
        """vertex_project should NOT be passed when not configured (let ADC handle it)."""
        kwargs = _get_provider_kwargs(mock_config_vertex_no_project, "vertex_ai")

        assert "vertex_project" not in kwargs, (
            "vertex_project should not be passed when not configured. LiteLLM will use ADC to auto-detect the project."
        )

    def test_both_vertex_location_and_project_passed(self, mock_config_vertex_with_project):
        """Both vertex_location and vertex_project should be passed when configured."""
        kwargs = _get_provider_kwargs(mock_config_vertex_with_project, "vertex_ai")

        assert "vertex_location" in kwargs
        assert kwargs["vertex_location"] == "us-east5"
        assert "vertex_project" in kwargs
        assert kwargs["vertex_project"] == "my-gcp-project"

    def test_google_provider_also_passes_location(self, mock_config_vertex_no_project):
        """'google' provider should also pass vertex_location for Gemini via Vertex."""
        kwargs = _get_provider_kwargs(mock_config_vertex_no_project, "google")

        assert "vertex_location" in kwargs
        assert kwargs["vertex_location"] == "global"


@pytest.mark.unit
@pytest.mark.xdist_group(name="vertex_ai_env_vars")
class TestVertexAIEnvironmentVariables:
    """Test that VERTEXAI_LOCATION env var is set correctly by _setup_environment.

    LiteLLM reads VERTEXAI_LOCATION directly to determine the Vertex AI location.
    Without this env var, LiteLLM defaults to us-central1 even if vertex_location
    is passed as a parameter.
    """

    def teardown_method(self):
        """Clean up environment variables after each test."""
        gc.collect()
        # Clean up VERTEXAI_* env vars
        for key in ["VERTEXAI_LOCATION", "VERTEXAI_PROJECT"]:
            if key in os.environ:
                del os.environ[key]

    @pytest.fixture
    def mock_config_vertex(self):
        """Config for Vertex AI provider with location set."""
        config = MagicMock()
        config.llm_provider = "vertex_ai"
        config.model_name = "vertex_ai/gemini-3-pro-preview"
        config.vertex_location = "global"
        config.vertex_project = "test-project-123"
        config.google_project_id = None
        config.model_timeout = 60
        config.enable_fallback = False
        config.fallback_models = []
        return config

    def test_setup_environment_sets_vertexai_location(self, mock_config_vertex):
        """_setup_environment MUST set VERTEXAI_LOCATION env var.

        GIVEN: Config with vertex_location="global"
        WHEN: LLMFactory._setup_environment is called
        THEN: VERTEXAI_LOCATION env var should be set to "global"
        """
        factory = LLMFactory(
            provider="vertex_ai",
            model_name="vertex_ai/gemini-3-pro-preview",
        )
        factory._setup_environment(config=mock_config_vertex)

        assert "VERTEXAI_LOCATION" in os.environ, "VERTEXAI_LOCATION must be set for LiteLLM to use correct location"
        assert os.environ["VERTEXAI_LOCATION"] == "global"

    def test_setup_environment_sets_vertexai_project(self, mock_config_vertex):
        """_setup_environment should set VERTEXAI_PROJECT if configured."""
        factory = LLMFactory(
            provider="vertex_ai",
            model_name="vertex_ai/gemini-3-pro-preview",
        )
        factory._setup_environment(config=mock_config_vertex)

        assert "VERTEXAI_PROJECT" in os.environ
        assert os.environ["VERTEXAI_PROJECT"] == "test-project-123"

    def test_google_provider_sets_vertexai_location(self, mock_config_vertex):
        """Google provider should also set VERTEXAI_LOCATION for Gemini routing."""
        mock_config_vertex.llm_provider = "google"

        factory = LLMFactory(
            provider="google",
            model_name="gemini-3-pro-preview",
        )
        factory._setup_environment(config=mock_config_vertex)

        assert "VERTEXAI_LOCATION" in os.environ
        assert os.environ["VERTEXAI_LOCATION"] == "global"
