"""
Config Router Tests

TDD tests for the /api/v1/config endpoint that exposes server defaults.

This endpoint is critical for 12-Factor App compliance (Principle III: Config):
- Frontend fetches backend configuration at startup
- Single source of truth for LLM model, max tokens, etc.
- Eliminates hardcoded frontend defaults
"""

import gc
from unittest.mock import patch

import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient

pytestmark = pytest.mark.unit


@pytest.fixture
def test_client() -> TestClient:
    """Create test client for config router."""
    from mcp_server_langgraph.api.v1.config import config_router
    from mcp_server_langgraph.auth.dependencies import get_current_user

    app = FastAPI()
    app.include_router(config_router, prefix="/api/v1")

    # Mock authentication
    mock_user = {
        "sub": "test-user-id",
        "user_id": "test-user-id",
        "username": "testuser",
        "roles": ["admin"],
        "realm_access": {"roles": ["admin"]},
    }
    app.dependency_overrides[get_current_user] = lambda: mock_user

    return TestClient(app)


@pytest.mark.xdist_group(name="test_config_router")
@pytest.mark.unit
@pytest.mark.api
class TestConfigRouter:
    """Tests for the config router endpoints."""

    def teardown_method(self) -> None:
        """Force GC to prevent mock accumulation in xdist workers."""
        gc.collect()

    def test_get_defaults_returns_model_name_from_settings(self, test_client: TestClient) -> None:
        """Verify /api/v1/config/defaults returns model_name from settings."""
        response = test_client.get("/api/v1/config/defaults")

        assert response.status_code == 200
        data = response.json()
        assert "model_name" in data
        # Should be a non-empty string from settings
        assert isinstance(data["model_name"], str)
        assert len(data["model_name"]) > 0

    def test_get_defaults_returns_max_tokens_from_settings(self, test_client: TestClient) -> None:
        """Verify /api/v1/config/defaults returns max_tokens from settings."""
        response = test_client.get("/api/v1/config/defaults")

        assert response.status_code == 200
        data = response.json()
        assert "max_tokens" in data
        # Should be a positive integer from settings
        assert isinstance(data["max_tokens"], int)
        assert data["max_tokens"] > 0

    def test_get_defaults_returns_model_provider(self, test_client: TestClient) -> None:
        """Verify /api/v1/config/defaults returns inferred model_provider."""
        response = test_client.get("/api/v1/config/defaults")

        assert response.status_code == 200
        data = response.json()
        assert "model_provider" in data
        # Should be one of the supported providers
        assert data["model_provider"] in ["openai", "anthropic", "google", "azure", "unknown"]

    def test_get_defaults_returns_temperature(self, test_client: TestClient) -> None:
        """Verify /api/v1/config/defaults returns temperature."""
        response = test_client.get("/api/v1/config/defaults")

        assert response.status_code == 200
        data = response.json()
        assert "temperature" in data
        # Temperature should be between 0 and 2
        assert isinstance(data["temperature"], (int, float))
        assert 0 <= data["temperature"] <= 2

    def test_get_defaults_uses_settings_singleton(self, test_client: TestClient) -> None:
        """Verify the endpoint uses the settings singleton, not hardcoded values."""
        # Mock settings to return specific values
        with patch("mcp_server_langgraph.api.v1.config.settings") as mock_settings:
            mock_settings.model_name = "test-custom-model-v2"
            mock_settings.model_max_tokens = 16384
            mock_settings.temperature = 0.5

            response = test_client.get("/api/v1/config/defaults")

            assert response.status_code == 200
            data = response.json()
            assert data["model_name"] == "test-custom-model-v2"
            assert data["max_tokens"] == 16384
            assert data["temperature"] == 0.5

    def test_get_defaults_infers_openai_provider(self, test_client: TestClient) -> None:
        """Verify OpenAI models are correctly identified."""
        with patch("mcp_server_langgraph.api.v1.config.settings") as mock_settings:
            mock_settings.model_name = "gpt-4o-mini"
            mock_settings.model_max_tokens = 8192
            mock_settings.temperature = 0.7

            response = test_client.get("/api/v1/config/defaults")

            assert response.status_code == 200
            data = response.json()
            assert data["model_provider"] == "openai"

    def test_get_defaults_infers_anthropic_provider(self, test_client: TestClient) -> None:
        """Verify Anthropic models are correctly identified."""
        with patch("mcp_server_langgraph.api.v1.config.settings") as mock_settings:
            mock_settings.model_name = "claude-3-opus"
            mock_settings.model_max_tokens = 8192
            mock_settings.temperature = 0.7

            response = test_client.get("/api/v1/config/defaults")

            assert response.status_code == 200
            data = response.json()
            assert data["model_provider"] == "anthropic"

    def test_get_defaults_infers_google_provider(self, test_client: TestClient) -> None:
        """Verify Google models are correctly identified."""
        with patch("mcp_server_langgraph.api.v1.config.settings") as mock_settings:
            mock_settings.model_name = "gemini-2.5-flash"
            mock_settings.model_max_tokens = 8192
            mock_settings.temperature = 0.7

            response = test_client.get("/api/v1/config/defaults")

            assert response.status_code == 200
            data = response.json()
            assert data["model_provider"] == "google"

    def test_get_defaults_infers_azure_provider(self, test_client: TestClient) -> None:
        """Verify Azure models are correctly identified."""
        with patch("mcp_server_langgraph.api.v1.config.settings") as mock_settings:
            mock_settings.model_name = "azure/gpt-4"
            mock_settings.model_max_tokens = 8192
            mock_settings.temperature = 0.7

            response = test_client.get("/api/v1/config/defaults")

            assert response.status_code == 200
            data = response.json()
            assert data["model_provider"] == "azure"

    def test_get_defaults_returns_all_required_fields(self, test_client: TestClient) -> None:
        """Verify the response contains all required fields for frontend hydration."""
        response = test_client.get("/api/v1/config/defaults")

        assert response.status_code == 200
        data = response.json()

        # All required fields for SessionConfig on frontend
        required_fields = ["model_name", "model_provider", "max_tokens", "temperature"]
        for field in required_fields:
            assert field in data, f"Missing required field: {field}"


@pytest.mark.xdist_group(name="test_config_router")
@pytest.mark.unit
@pytest.mark.api
class TestConfigModelsEndpoint:
    """Tests for GET /config/models endpoint - available LLM models for selection."""

    def teardown_method(self) -> None:
        """Force GC to prevent mock accumulation in xdist workers."""
        gc.collect()

    def test_get_models_returns_200(self, test_client: TestClient) -> None:
        """Verify /api/v1/config/models returns 200 OK."""
        response = test_client.get("/api/v1/config/models")

        assert response.status_code == 200

    def test_get_models_returns_list_structure(self, test_client: TestClient) -> None:
        """Verify /api/v1/config/models returns a list of models."""
        response = test_client.get("/api/v1/config/models")

        assert response.status_code == 200
        data = response.json()
        assert isinstance(data, list)
        assert len(data) > 0  # Should have at least one model

    def test_get_models_has_required_fields(self, test_client: TestClient) -> None:
        """Verify each model has required fields: id, name, provider."""
        response = test_client.get("/api/v1/config/models")

        assert response.status_code == 200
        data = response.json()

        for model in data:
            assert "id" in model, "Model missing 'id' field"
            assert "name" in model, "Model missing 'name' field"
            assert "provider" in model, "Model missing 'provider' field"

    def test_get_models_includes_anthropic_models(self, test_client: TestClient) -> None:
        """Verify Anthropic Claude models are included."""
        response = test_client.get("/api/v1/config/models")

        assert response.status_code == 200
        data = response.json()

        providers = [m["provider"] for m in data]
        assert "anthropic" in providers

    def test_get_models_includes_openai_models(self, test_client: TestClient) -> None:
        """Verify OpenAI GPT models are included."""
        response = test_client.get("/api/v1/config/models")

        assert response.status_code == 200
        data = response.json()

        providers = [m["provider"] for m in data]
        assert "openai" in providers

    def test_get_models_includes_google_models(self, test_client: TestClient) -> None:
        """Verify Google Gemini models are included."""
        response = test_client.get("/api/v1/config/models")

        assert response.status_code == 200
        data = response.json()

        providers = [m["provider"] for m in data]
        assert "google" in providers

    def test_get_models_includes_supports_thinking_flag(self, test_client: TestClient) -> None:
        """Verify models include supports_thinking flag for extended thinking capability."""
        response = test_client.get("/api/v1/config/models")

        assert response.status_code == 200
        data = response.json()

        # At least some models should have the supports_thinking field
        for model in data:
            assert "supports_thinking" in model, f"Model {model['id']} missing 'supports_thinking' field"
            assert isinstance(model["supports_thinking"], bool)

    def test_get_models_thinking_models_identified_correctly(self, test_client: TestClient) -> None:
        """Verify models that support extended thinking are marked correctly."""
        response = test_client.get("/api/v1/config/models")

        assert response.status_code == 200
        data = response.json()

        # Claude 3.5 Sonnet and Claude 3 Opus should support thinking
        thinking_capable_ids = ["claude-3-5-sonnet", "claude-3-opus", "claude-sonnet-4-5"]
        for model in data:
            if any(tc in model["id"] for tc in thinking_capable_ids):
                assert model["supports_thinking"] is True, f"Model {model['id']} should support thinking"

    def test_get_models_includes_supports_vision_flag(self, test_client: TestClient) -> None:
        """Verify models include supports_vision flag for vision/image capability."""
        response = test_client.get("/api/v1/config/models")

        assert response.status_code == 200
        data = response.json()

        # All models should have the supports_vision field
        for model in data:
            assert "supports_vision" in model, f"Model {model['id']} missing 'supports_vision' field"
            assert isinstance(model["supports_vision"], bool)

    def test_get_models_includes_supports_tools_flag(self, test_client: TestClient) -> None:
        """Verify models include supports_tools flag for tool/function calling capability."""
        response = test_client.get("/api/v1/config/models")

        assert response.status_code == 200
        data = response.json()

        # All models should have the supports_tools field
        for model in data:
            assert "supports_tools" in model, f"Model {model['id']} missing 'supports_tools' field"
            assert isinstance(model["supports_tools"], bool)

    def test_get_models_vision_capable_models_identified_correctly(self, test_client: TestClient) -> None:
        """Verify models with vision capability are marked correctly."""
        response = test_client.get("/api/v1/config/models")

        assert response.status_code == 200
        data = response.json()

        # Claude and GPT-4o models support vision, o1 models do not
        vision_capable_ids = ["claude-3-5-sonnet", "claude-3-opus", "claude-3-haiku", "gpt-4o", "gemini"]
        no_vision_ids = ["o1-preview", "o1-mini"]

        for model in data:
            if any(vc in model["id"] for vc in vision_capable_ids):
                assert model["supports_vision"] is True, f"Model {model['id']} should support vision"
            if any(nv in model["id"] for nv in no_vision_ids):
                assert model["supports_vision"] is False, f"Model {model['id']} should NOT support vision"

    def test_get_models_tools_capable_models_identified_correctly(self, test_client: TestClient) -> None:
        """Verify models with tool calling capability are marked correctly."""
        response = test_client.get("/api/v1/config/models")

        assert response.status_code == 200
        data = response.json()

        # Most models support tools, o1 models do not
        tools_capable_ids = ["claude-3-5-sonnet", "claude-3-opus", "gpt-4o", "gemini"]
        no_tools_ids = ["o1-preview", "o1-mini"]

        for model in data:
            if any(tc in model["id"] for tc in tools_capable_ids):
                assert model["supports_tools"] is True, f"Model {model['id']} should support tools"
            if any(nt in model["id"] for nt in no_tools_ids):
                assert model["supports_tools"] is False, f"Model {model['id']} should NOT support tools"


@pytest.mark.xdist_group(name="test_config_router")
@pytest.mark.unit
@pytest.mark.api
class TestConfigModelsFromModelRegistry:
    """Tests for GET /config/models using ModelRegistry (feature flag enabled).

    When FF_USE_MODEL_REGISTRY_FOR_FRONTEND=true, the endpoint should use
    ModelRegistry.get_frontend_models() instead of hardcoded AVAILABLE_MODELS.
    This ensures single source of truth for model capabilities.
    """

    def teardown_method(self) -> None:
        """Force GC to prevent mock accumulation in xdist workers."""
        gc.collect()

    def test_get_models_uses_registry_when_flag_enabled(self, test_client: TestClient) -> None:
        """Verify /api/v1/config/models uses ModelRegistry when flag enabled."""
        with patch("mcp_server_langgraph.api.v1.config.feature_flags") as mock_flags:
            mock_flags.use_model_registry_for_frontend = True

            response = test_client.get("/api/v1/config/models")

            assert response.status_code == 200
            data = response.json()
            # Should return models from registry
            assert isinstance(data, list)
            assert len(data) > 0

    def test_get_models_uses_available_models_when_flag_disabled(self, test_client: TestClient) -> None:
        """Verify /api/v1/config/models uses AVAILABLE_MODELS when flag disabled."""
        with patch("mcp_server_langgraph.api.v1.config.feature_flags") as mock_flags:
            mock_flags.use_model_registry_for_frontend = False

            response = test_client.get("/api/v1/config/models")

            assert response.status_code == 200
            data = response.json()
            # Should return models from AVAILABLE_MODELS (legacy)
            assert isinstance(data, list)
            # Check for legacy model IDs
            model_ids = [m["id"] for m in data]
            # Legacy AVAILABLE_MODELS has claude-3-5-sonnet
            assert "claude-3-5-sonnet" in model_ids

    def test_registry_models_have_required_fields(self, test_client: TestClient) -> None:
        """Verify models from registry have all required fields."""
        with patch("mcp_server_langgraph.api.v1.config.feature_flags") as mock_flags:
            mock_flags.use_model_registry_for_frontend = True

            response = test_client.get("/api/v1/config/models")

            assert response.status_code == 200
            data = response.json()

            for model in data:
                assert "id" in model, "Model missing 'id' field"
                assert "name" in model, "Model missing 'name' field"
                assert "provider" in model, "Model missing 'provider' field"
                assert "supports_thinking" in model, "Model missing 'supports_thinking' field"
                assert "supports_vision" in model, "Model missing 'supports_vision' field"
                assert "supports_tools" in model, "Model missing 'supports_tools' field"

    def test_registry_includes_claude_opus_4_5(self, test_client: TestClient) -> None:
        """Verify registry includes Claude Opus 4.5 model."""
        with patch("mcp_server_langgraph.api.v1.config.feature_flags") as mock_flags:
            mock_flags.use_model_registry_for_frontend = True

            response = test_client.get("/api/v1/config/models")

            assert response.status_code == 200
            data = response.json()
            model_ids = [m["id"] for m in data]

            # Registry has claude-opus-4-5 public_id
            assert "claude-opus-4-5" in model_ids

    def test_registry_includes_all_providers(self, test_client: TestClient) -> None:
        """Verify registry models include all providers."""
        with patch("mcp_server_langgraph.api.v1.config.feature_flags") as mock_flags:
            mock_flags.use_model_registry_for_frontend = True

            response = test_client.get("/api/v1/config/models")

            assert response.status_code == 200
            data = response.json()
            providers = {m["provider"] for m in data}

            assert "anthropic" in providers
            assert "google" in providers
            assert "openai" in providers

    def test_feature_flag_use_model_registry_for_frontend_exists(self) -> None:
        """Test that use_model_registry_for_frontend flag exists in feature flags."""
        from mcp_server_langgraph.core.feature_flags import feature_flags

        assert hasattr(feature_flags, "use_model_registry_for_frontend")

    def test_feature_flag_default_is_true(self) -> None:
        """Test that use_model_registry_for_frontend defaults to True (ModelRegistry is now the default source)."""
        from mcp_server_langgraph.core.feature_flags import FeatureFlags

        # Create fresh instance to check default
        flags = FeatureFlags()
        assert flags.use_model_registry_for_frontend is True

    def test_registry_models_include_status_field(self, test_client: TestClient) -> None:
        """Verify models from registry include status field for lifecycle management."""
        with patch("mcp_server_langgraph.api.v1.config.feature_flags") as mock_flags:
            mock_flags.use_model_registry_for_frontend = True

            response = test_client.get("/api/v1/config/models")

            assert response.status_code == 200
            data = response.json()

            for model in data:
                assert "status" in model, f"Model {model['id']} missing 'status' field"
                assert model["status"] in ["current", "preview", "legacy", "deprecated"]

    def test_registry_deprecated_models_have_sunset_date(self, test_client: TestClient) -> None:
        """Verify deprecated models include sunset_date field."""
        with patch("mcp_server_langgraph.api.v1.config.feature_flags") as mock_flags:
            mock_flags.use_model_registry_for_frontend = True

            response = test_client.get("/api/v1/config/models")

            assert response.status_code == 200
            data = response.json()

            deprecated_models = [m for m in data if m.get("status") == "deprecated"]
            assert len(deprecated_models) > 0, "No deprecated models found in registry"

            for model in deprecated_models:
                assert "sunset_date" in model, f"Deprecated model {model['id']} missing 'sunset_date' field"
                # Validate ISO 8601 date format (YYYY-MM-DD)
                import re

                assert re.match(r"^\d{4}-\d{2}-\d{2}$", model["sunset_date"]), (
                    f"Model {model['id']} has invalid sunset_date format: {model['sunset_date']}"
                )

    def test_registry_non_deprecated_models_no_sunset_date(self, test_client: TestClient) -> None:
        """Verify non-deprecated models do NOT include sunset_date field."""
        with patch("mcp_server_langgraph.api.v1.config.feature_flags") as mock_flags:
            mock_flags.use_model_registry_for_frontend = True

            response = test_client.get("/api/v1/config/models")

            assert response.status_code == 200
            data = response.json()

            non_deprecated_models = [m for m in data if m.get("status") != "deprecated"]
            assert len(non_deprecated_models) > 0, "No non-deprecated models found in registry"

            for model in non_deprecated_models:
                assert "sunset_date" not in model, f"Non-deprecated model {model['id']} should NOT have 'sunset_date' field"


@pytest.mark.xdist_group(name="test_config_router")
@pytest.mark.unit
@pytest.mark.api
class TestConfigModelsDeprecationWarning:
    """Tests for deprecation warning when using legacy AVAILABLE_MODELS."""

    def teardown_method(self) -> None:
        """Force GC to prevent mock accumulation in xdist workers."""
        gc.collect()

    def test_deprecation_warning_emitted_when_flag_disabled(self, test_client: TestClient) -> None:
        """Verify DeprecationWarning is emitted when using legacy AVAILABLE_MODELS."""
        import warnings

        with patch("mcp_server_langgraph.api.v1.config.feature_flags") as mock_flags:
            mock_flags.use_model_registry_for_frontend = False

            with warnings.catch_warnings(record=True) as caught_warnings:
                warnings.simplefilter("always")

                response = test_client.get("/api/v1/config/models")

                assert response.status_code == 200

                # Find the deprecation warning
                deprecation_warnings = [
                    w
                    for w in caught_warnings
                    if issubclass(w.category, DeprecationWarning) and "AVAILABLE_MODELS" in str(w.message)
                ]
                assert len(deprecation_warnings) == 1, "Expected exactly one AVAILABLE_MODELS deprecation warning"
                assert "ModelRegistry" in str(deprecation_warnings[0].message)

    def test_no_deprecation_warning_when_flag_enabled(self, test_client: TestClient) -> None:
        """Verify no deprecation warning when using ModelRegistry (flag enabled)."""
        import warnings

        with patch("mcp_server_langgraph.api.v1.config.feature_flags") as mock_flags:
            mock_flags.use_model_registry_for_frontend = True

            with warnings.catch_warnings(record=True) as caught_warnings:
                warnings.simplefilter("always")

                response = test_client.get("/api/v1/config/models")

                assert response.status_code == 200

                # No AVAILABLE_MODELS deprecation warning should be emitted
                deprecation_warnings = [
                    w
                    for w in caught_warnings
                    if issubclass(w.category, DeprecationWarning) and "AVAILABLE_MODELS" in str(w.message)
                ]
                assert len(deprecation_warnings) == 0, (
                    "No AVAILABLE_MODELS deprecation warning expected when using ModelRegistry"
                )
