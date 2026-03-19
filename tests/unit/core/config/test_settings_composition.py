"""
Composed Settings Class Tests

TDD RED PHASE: Tests for the new Settings class that composes all domain settings.

Goal: Replace config_legacy.py (820 lines) with a clean composed Settings class
that inherits fields from all domain settings without duplication.

These tests verify that:
1. Settings inherits fields from all domain settings (Auth, LLM, Storage, etc.)
2. Settings includes additional service/environment fields
3. Settings has all methods from legacy Settings (validate_production_config, load_secrets)
4. Backward compatibility is maintained for existing imports
"""

import gc

import pytest


pytestmark = [
    pytest.mark.unit,
    pytest.mark.core,
    pytest.mark.config,
]


@pytest.mark.xdist_group(name="test_settings_composition")
class TestSettingsComposition:
    """Tests for composed Settings class that inherits from all domain settings."""

    def teardown_method(self) -> None:
        """Force GC to prevent mock accumulation in xdist workers."""
        gc.collect()

    def test_settings_has_auth_fields(self) -> None:
        """
        GIVEN the composed Settings class
        WHEN accessing authentication fields
        THEN all AuthSettings fields should be available
        """
        from mcp_server_langgraph.core.config import Settings

        settings = Settings()

        # AuthSettings fields
        assert hasattr(settings, "jwt_secret_key")
        assert hasattr(settings, "jwt_algorithm")
        assert hasattr(settings, "dpop_required")
        assert hasattr(settings, "keycloak_server_url")
        assert hasattr(settings, "openfga_api_url")

    def test_settings_has_llm_fields(self) -> None:
        """
        GIVEN the composed Settings class
        WHEN accessing LLM fields
        THEN all LLMSettings fields should be available
        """
        from mcp_server_langgraph.core.config import Settings

        settings = Settings()

        # LLMSettings fields
        assert hasattr(settings, "llm_provider")
        assert hasattr(settings, "model_name")
        assert hasattr(settings, "model_temperature")
        assert hasattr(settings, "anthropic_api_key")
        assert hasattr(settings, "enable_fallback")
        assert hasattr(settings, "fallback_models")

    def test_settings_has_storage_fields(self) -> None:
        """
        GIVEN the composed Settings class
        WHEN accessing storage fields
        THEN all StorageSettings fields should be available
        """
        from mcp_server_langgraph.core.config import Settings

        settings = Settings()

        # StorageSettings fields
        assert hasattr(settings, "database_url")
        assert hasattr(settings, "redis_url")
        assert hasattr(settings, "session_backend")
        assert hasattr(settings, "checkpoint_backend")
        assert hasattr(settings, "qdrant_url")

    def test_settings_has_observability_fields(self) -> None:
        """
        GIVEN the composed Settings class
        WHEN accessing observability fields
        THEN all ObservabilitySettings fields should be available
        """
        from mcp_server_langgraph.core.config import Settings

        settings = Settings()

        # ObservabilitySettings fields
        assert hasattr(settings, "otlp_endpoint")
        assert hasattr(settings, "enable_tracing")
        assert hasattr(settings, "langsmith_api_key")
        assert hasattr(settings, "log_level")

    def test_settings_has_agent_fields(self) -> None:
        """
        GIVEN the composed Settings class
        WHEN accessing agent fields
        THEN all AgentSettings fields should be available
        """
        from mcp_server_langgraph.core.config import Settings

        settings = Settings()

        # AgentSettings fields
        assert hasattr(settings, "max_iterations")
        assert hasattr(settings, "enable_checkpointing")
        assert hasattr(settings, "enable_context_compaction")
        assert hasattr(settings, "enable_verification")

    def test_settings_has_compliance_fields(self) -> None:
        """
        GIVEN the composed Settings class
        WHEN accessing compliance fields
        THEN all ComplianceSettings fields should be available
        """
        from mcp_server_langgraph.core.config import Settings

        settings = Settings()

        # ComplianceSettings fields
        assert hasattr(settings, "hipaa_integrity_secret")
        assert hasattr(settings, "gdpr_storage_backend")
        assert hasattr(settings, "audit_integrity_secret")

    def test_settings_has_streaming_fields(self) -> None:
        """
        GIVEN the composed Settings class
        WHEN accessing streaming fields
        THEN all StreamingSettings fields should be available
        """
        from mcp_server_langgraph.core.config import Settings

        settings = Settings()

        # StreamingSettings fields
        assert hasattr(settings, "streaming_enabled")
        assert hasattr(settings, "streaming_max_chunk_size")
        assert hasattr(settings, "streaming_idle_timeout_seconds")

    def test_settings_has_service_fields(self) -> None:
        """
        GIVEN the composed Settings class
        WHEN accessing service fields
        THEN service-specific fields should be available

        These are NOT in domain settings but are essential for the service.
        """
        from mcp_server_langgraph.core.config import Settings

        settings = Settings()

        # Service-specific fields (not in domain settings)
        assert hasattr(settings, "service_name")
        assert hasattr(settings, "service_version")
        assert hasattr(settings, "environment")
        assert hasattr(settings, "cors_allowed_origins")

    def test_settings_has_infisical_fields(self) -> None:
        """
        GIVEN the composed Settings class
        WHEN accessing Infisical fields
        THEN Infisical secret management fields should be available
        """
        from mcp_server_langgraph.core.config import Settings

        settings = Settings()

        # Infisical integration fields
        assert hasattr(settings, "infisical_site_url")
        assert hasattr(settings, "infisical_client_id")
        assert hasattr(settings, "infisical_client_secret")
        assert hasattr(settings, "infisical_project_id")

    def test_settings_has_langgraph_platform_fields(self) -> None:
        """
        GIVEN the composed Settings class
        WHEN accessing LangGraph Platform fields
        THEN LangGraph platform fields should be available
        """
        from mcp_server_langgraph.core.config import Settings

        settings = Settings()

        # LangGraph Platform fields
        assert hasattr(settings, "langgraph_api_key")
        assert hasattr(settings, "langgraph_deployment_url")
        assert hasattr(settings, "langgraph_api_url")


@pytest.mark.xdist_group(name="test_settings_composition")
class TestSettingsMethods:
    """Tests for Settings methods that were in config_legacy."""

    def teardown_method(self) -> None:
        """Force GC to prevent mock accumulation in xdist workers."""
        gc.collect()

    def test_settings_has_validate_production_config(self) -> None:
        """
        GIVEN the composed Settings class
        WHEN checking for methods
        THEN validate_production_config should exist
        """
        from mcp_server_langgraph.core.config import Settings

        settings = Settings()
        assert hasattr(settings, "validate_production_config")
        assert callable(settings.validate_production_config)

    def test_settings_has_get_mock_authorization_enabled(self) -> None:
        """
        GIVEN the composed Settings class
        WHEN checking for methods
        THEN get_mock_authorization_enabled should exist
        """
        from mcp_server_langgraph.core.config import Settings

        settings = Settings()
        assert hasattr(settings, "get_mock_authorization_enabled")
        assert callable(settings.get_mock_authorization_enabled)

    def test_settings_has_get_cors_origins(self) -> None:
        """
        GIVEN the composed Settings class
        WHEN checking for methods
        THEN get_cors_origins should exist
        """
        from mcp_server_langgraph.core.config import Settings

        settings = Settings()
        assert hasattr(settings, "get_cors_origins")
        assert callable(settings.get_cors_origins)

    def test_settings_has_load_secrets(self) -> None:
        """
        GIVEN the composed Settings class
        WHEN checking for methods
        THEN load_secrets should exist
        """
        from mcp_server_langgraph.core.config import Settings

        settings = Settings()
        assert hasattr(settings, "load_secrets")
        assert callable(settings.load_secrets)

    def test_settings_has_redis_url_aliases(self) -> None:
        """
        GIVEN the composed Settings class
        WHEN accessing Redis URL aliases
        THEN both checkpoint and session URL properties should work
        """
        from mcp_server_langgraph.core.config import Settings

        settings = Settings()

        # Redis URL properties (backward compatibility)
        assert hasattr(settings, "redis_checkpoint_url")
        assert hasattr(settings, "redis_session_url")

        # They should return string values
        assert isinstance(settings.redis_checkpoint_url, str)
        assert isinstance(settings.redis_session_url, str)


@pytest.mark.xdist_group(name="test_settings_composition")
class TestSettingsBackwardCompatibility:
    """Tests to ensure backward compatibility with existing code."""

    def teardown_method(self) -> None:
        """Force GC to prevent mock accumulation in xdist workers."""
        gc.collect()

    def test_settings_singleton_exists(self) -> None:
        """
        GIVEN the config module
        WHEN importing settings
        THEN a global settings instance should be available
        """
        from mcp_server_langgraph.core.config import settings

        assert settings is not None

    def test_settings_class_can_be_imported(self) -> None:
        """
        GIVEN the config module
        WHEN importing Settings class
        THEN the class should be importable
        """
        from mcp_server_langgraph.core.config import Settings

        assert Settings is not None

    def test_domain_settings_can_be_imported(self) -> None:
        """
        GIVEN the config module
        WHEN importing domain-specific settings
        THEN all should be importable for granular use
        """
        from mcp_server_langgraph.core.config import (
            AuthSettings,
            LLMSettings,
            StorageSettings,
            ObservabilitySettings,
            AgentSettings,
            ComplianceSettings,
            StreamingSettings,
        )

        assert AuthSettings is not None
        assert LLMSettings is not None
        assert StorageSettings is not None
        assert ObservabilitySettings is not None
        assert AgentSettings is not None
        assert ComplianceSettings is not None
        assert StreamingSettings is not None

    def test_settings_default_values_match_legacy(self) -> None:
        """
        GIVEN the composed Settings class
        WHEN checking default values
        THEN they should match the legacy defaults

        Note: environment may be overridden by ENVIRONMENT env var in test runs.
        """
        from mcp_server_langgraph.core.config import Settings

        settings = Settings()

        # Key defaults that must be preserved
        # Note: environment can be "test" or "development" depending on env vars
        assert settings.environment in ("development", "test")
        assert settings.llm_provider == "google"
        assert settings.model_name == "gemini-2.5-flash"
        assert settings.jwt_algorithm == "HS256"
        assert settings.auth_provider == "inmemory"
        assert settings.session_backend == "memory"
        assert settings.log_level == "INFO"


@pytest.mark.xdist_group(name="test_settings_composition")
class TestAgenticMemoryBackendSettings:
    """Tests for agentic memory backend settings (12-factor stateless processes)."""

    def teardown_method(self) -> None:
        gc.collect()

    def test_settings_has_notes_backend(self) -> None:
        from mcp_server_langgraph.core.config import Settings

        settings = Settings()
        assert hasattr(settings, "notes_backend")
        assert settings.notes_backend == "memory"

    def test_settings_has_phase_checkpoint_backend(self) -> None:
        from mcp_server_langgraph.core.config import Settings

        settings = Settings()
        assert hasattr(settings, "phase_checkpoint_backend")
        assert settings.phase_checkpoint_backend == "memory"

    def test_settings_has_agent_state_backend(self) -> None:
        from mcp_server_langgraph.core.config import Settings

        settings = Settings()
        assert hasattr(settings, "agent_state_backend")
        assert settings.agent_state_backend == "memory"

    def test_settings_has_evidence_backend(self) -> None:
        from mcp_server_langgraph.core.config import Settings

        settings = Settings()
        assert hasattr(settings, "evidence_backend")
        assert settings.evidence_backend == "memory"

    def test_phase_checkpoint_backend_distinct_from_checkpoint_backend(self) -> None:
        """Verify phase_checkpoint_backend is distinct from checkpoint_backend (LangGraph conversation state)."""
        from mcp_server_langgraph.core.config import Settings

        settings = Settings()
        # Both exist and are independent
        assert hasattr(settings, "checkpoint_backend")
        assert hasattr(settings, "phase_checkpoint_backend")
        # They can differ (both default to memory but control different things)
        assert settings.checkpoint_backend == "memory"
        assert settings.phase_checkpoint_backend == "memory"

    def test_storage_settings_has_agentic_memory_fields(self) -> None:
        from mcp_server_langgraph.core.config import StorageSettings

        storage = StorageSettings()
        assert storage.notes_backend == "memory"
        assert storage.phase_checkpoint_backend == "memory"
        assert storage.agent_state_backend == "memory"
        assert storage.evidence_backend == "memory"
