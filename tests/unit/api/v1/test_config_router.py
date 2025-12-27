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

    app = FastAPI()
    app.include_router(config_router, prefix="/api/v1")
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
