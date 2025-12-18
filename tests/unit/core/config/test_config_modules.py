"""
Tests for decomposed configuration modules.

TDD: These tests are written FIRST before implementation.
They define the expected behavior of the decomposed config modules.
"""

import pytest

pytestmark = pytest.mark.unit


@pytest.mark.unit
@pytest.mark.xdist_group(name="test_config_module_imports")
class TestConfigModuleImports:
    """Test that all config modules can be imported."""

    def test_import_settings_from_package(self):
        """Settings should be importable from the config package."""
        from mcp_server_langgraph.core.config import Settings

        assert Settings is not None

    def test_import_settings_global_instance(self):
        """Global settings instance should be importable."""
        from mcp_server_langgraph.core.config import settings

        assert settings is not None

    def test_settings_is_singleton(self):
        """Importing settings multiple times should return same instance."""
        from mcp_server_langgraph.core.config import settings as settings1
        from mcp_server_langgraph.core.config import settings as settings2

        assert settings1 is settings2


@pytest.mark.unit
@pytest.mark.xdist_group(name="test_settings_defaults")
class TestSettingsDefaults:
    """Test that Settings has correct default values."""

    def test_default_environment_is_development_when_not_set(self, monkeypatch):
        """Default environment should be development when not set."""
        # Clear ENVIRONMENT env var to test true default
        monkeypatch.delenv("ENVIRONMENT", raising=False)

        from mcp_server_langgraph.core.config import Settings

        s = Settings()
        assert s.environment == "development"

    def test_default_service_name(self):
        """Default service name should be set."""
        from mcp_server_langgraph.core.config import Settings

        s = Settings()
        assert s.service_name == "mcp-server-langgraph"

    def test_default_auth_provider(self):
        """Default auth provider should be inmemory."""
        from mcp_server_langgraph.core.config import Settings

        s = Settings()
        assert s.auth_provider == "inmemory"

    def test_default_checkpoint_backend(self):
        """Default checkpoint backend should be memory."""
        from mcp_server_langgraph.core.config import Settings

        s = Settings()
        assert s.checkpoint_backend == "memory"


@pytest.mark.unit
@pytest.mark.xdist_group(name="test_settings_validation")
class TestSettingsValidation:
    """Test Settings validation logic."""

    def test_production_validation_inmemory_auth_blocked(self):
        """Production with inmemory auth should raise ValueError."""
        from mcp_server_langgraph.core.config import Settings

        with pytest.raises(ValueError, match="inmemory.*not allowed in production"):
            Settings(environment="production", auth_provider="inmemory")

    def test_production_validation_mock_auth_blocked(self):
        """Production with mock authorization should raise ValueError."""
        from mcp_server_langgraph.core.config import Settings

        with pytest.raises(ValueError, match="Mock authorization"):
            Settings(
                environment="production",
                auth_provider="keycloak",
                keycloak_client_secret="test",
                enable_mock_authorization=True,
                jwt_secret_key="secure-key-for-testing-only-32chars!",
                gdpr_storage_backend="postgres",
            )

    def test_development_allows_mock_auth(self):
        """Development should allow mock authorization."""
        from mcp_server_langgraph.core.config import Settings

        s = Settings(environment="development", enable_mock_authorization=True)
        assert s.get_mock_authorization_enabled() is True


@pytest.mark.unit
@pytest.mark.xdist_group(name="test_settings_methods")
class TestSettingsMethods:
    """Test Settings helper methods."""

    def test_get_mock_authorization_enabled_explicit(self):
        """Explicit setting should be respected."""
        from mcp_server_langgraph.core.config import Settings

        s = Settings(enable_mock_authorization=False)
        assert s.get_mock_authorization_enabled() is False

        s = Settings(enable_mock_authorization=True)
        assert s.get_mock_authorization_enabled() is True

    def test_get_mock_authorization_enabled_auto(self):
        """Auto-determination should enable in dev, disable in prod."""
        from mcp_server_langgraph.core.config import Settings

        s = Settings(environment="development", enable_mock_authorization=None)
        assert s.get_mock_authorization_enabled() is True

    def test_get_cors_origins_development(self):
        """Development should have default CORS origins."""
        from mcp_server_langgraph.core.config import Settings

        s = Settings(environment="development")
        origins = s.get_cors_origins()
        assert "http://localhost:3000" in origins
        assert "http://localhost:5173" in origins

    def test_get_cors_origins_explicit(self):
        """Explicit CORS origins should be used."""
        from mcp_server_langgraph.core.config import Settings

        s = Settings(cors_allowed_origins=["https://example.com"])
        origins = s.get_cors_origins()
        assert origins == ["https://example.com"]


@pytest.mark.unit
@pytest.mark.xdist_group(name="test_settings_field_validators")
class TestSettingsFieldValidators:
    """Test field validators parse correctly."""

    def test_parse_comma_separated_list_cors(self):
        """CORS origins should parse from comma-separated string."""
        from mcp_server_langgraph.core.config import Settings

        s = Settings(cors_allowed_origins="http://a.com, http://b.com")
        assert s.cors_allowed_origins == ["http://a.com", "http://b.com"]

    def test_parse_comma_separated_list_already_list(self):
        """List input should pass through unchanged."""
        from mcp_server_langgraph.core.config import Settings

        s = Settings(cors_allowed_origins=["http://a.com", "http://b.com"])
        assert s.cors_allowed_origins == ["http://a.com", "http://b.com"]


@pytest.mark.unit
@pytest.mark.xdist_group(name="test_settings_backwards_compat")
class TestSettingsBackwardsCompatibility:
    """Test backwards compatibility with existing code."""

    def test_all_expected_fields_exist(self):
        """All expected fields should exist on Settings."""
        from mcp_server_langgraph.core.config import Settings

        s = Settings()

        # Core fields
        assert hasattr(s, "service_name")
        assert hasattr(s, "environment")

        # Auth fields
        assert hasattr(s, "jwt_secret_key")
        assert hasattr(s, "auth_provider")
        assert hasattr(s, "keycloak_server_url")
        assert hasattr(s, "openfga_api_url")

        # LLM fields
        assert hasattr(s, "llm_provider")
        assert hasattr(s, "model_name")
        assert hasattr(s, "anthropic_api_key")
        assert hasattr(s, "openai_api_key")

        # Storage fields
        assert hasattr(s, "database_url")
        assert hasattr(s, "redis_url")
        assert hasattr(s, "checkpoint_backend")

        # Observability fields
        assert hasattr(s, "otlp_endpoint")
        assert hasattr(s, "enable_tracing")
        assert hasattr(s, "langsmith_api_key")

        # Agent fields
        assert hasattr(s, "enable_context_compaction")
        assert hasattr(s, "enable_verification")
        assert hasattr(s, "max_refinement_attempts")

    def test_existing_import_path_works(self):
        """Existing import path should still work."""
        # This is the primary import path used throughout the codebase
        from mcp_server_langgraph.core.config import Settings, settings

        assert Settings is not None
        assert settings is not None
