"""
TDD Test Suite for Dependency Injection Container

Following TDD principles:
1. Write tests first (this file)
2. Run tests (they should fail - Red)
3. Implement minimum code to pass (Green)
4. Refactor (Refactor)

These tests define the behavior we want from the container pattern.
"""

from typing import Optional
from unittest.mock import Mock, patch

import pytest

# Import the container module (doesn't exist yet - TDD Red phase)
# We'll create this module after writing the tests
from mcp_server_langgraph.core.container import (
    ApplicationContainer,
    AuthProvider,
    ContainerConfig,
    StorageProvider,
    TelemetryProvider,
)


@pytest.mark.unit
class TestContainerConfiguration:
    """Test container configuration"""

    def test_container_config_defaults(self):
        """Test that container config has sensible defaults"""
        config = ContainerConfig()

        assert config.environment == "development"
        assert config.enable_telemetry is False
        assert config.enable_auth is False
        assert config.log_level == "INFO"

    def test_container_config_test_mode(self):
        """Test that test mode is detected from environment"""
        config = ContainerConfig(environment="test")

        assert config.environment == "test"
        assert config.enable_telemetry is False  # Telemetry disabled in tests
        assert config.enable_auth is False  # Auth disabled in tests

    def test_container_config_production_mode(self):
        """Test that production mode enforces requirements"""
        config = ContainerConfig(environment="production")

        assert config.environment == "production"
        # Production should default to enabling security features
        assert config.enable_auth is True
        assert config.enable_telemetry is True


class TestApplicationContainer:
    """Test the main application container"""

    def test_container_initialization_test_mode(self):
        """Test container initializes with no-op providers in test mode"""
        config = ContainerConfig(environment="test")
        container = ApplicationContainer(config)

        # Settings should be available
        assert container.settings is not None
        assert container.settings.environment == "test"

        # Telemetry should be no-op
        telemetry = container.get_telemetry()
        assert telemetry is not None
        assert isinstance(telemetry, TelemetryProvider)

        # Auth should be no-op or in-memory
        auth = container.get_auth()
        assert auth is not None
        assert isinstance(auth, AuthProvider)

    def test_container_initialization_development_mode(self):
        """Test container initializes with development defaults"""
        config = ContainerConfig(environment="development")
        container = ApplicationContainer(config)

        assert container.settings.environment == "development"
        assert container.get_telemetry() is not None
        assert container.get_auth() is not None

    def test_container_settings_injectable(self):
        """Test that settings can be injected (overridden) for testing"""
        from mcp_server_langgraph.core.config import Settings

        # Create custom settings
        custom_settings = Settings(environment="test", log_level="DEBUG", jwt_secret_key="test-secret-123")

        config = ContainerConfig(environment="test")
        container = ApplicationContainer(config, settings=custom_settings)

        assert container.settings.environment == "test"
        assert container.settings.log_level == "DEBUG"
        assert container.settings.jwt_secret_key == "test-secret-123"

    def test_container_telemetry_lazy_initialization(self):
        """Test that telemetry is lazily initialized"""
        config = ContainerConfig(environment="test")
        container = ApplicationContainer(config)

        # Telemetry shouldn't be initialized until requested
        assert not hasattr(container, "_telemetry_instance")

        # First call initializes
        telemetry1 = container.get_telemetry()
        assert hasattr(container, "_telemetry_instance")

        # Second call returns same instance
        telemetry2 = container.get_telemetry()
        assert telemetry1 is telemetry2

    def test_container_multiple_instances_independent(self):
        """Test that multiple container instances are independent"""
        config1 = ContainerConfig(environment="test")
        config2 = ContainerConfig(environment="development")

        container1 = ApplicationContainer(config1)
        container2 = ApplicationContainer(config2)

        assert container1.settings.environment == "test"
        assert container2.settings.environment == "development"

        # Each should have independent telemetry
        telemetry1 = container1.get_telemetry()
        telemetry2 = container2.get_telemetry()
        assert telemetry1 is not telemetry2

    def test_container_provides_storage(self):
        """Test that container provides storage backends"""
        config = ContainerConfig(environment="test")
        container = ApplicationContainer(config)

        storage = container.get_storage()
        assert storage is not None
        assert isinstance(storage, StorageProvider)

    def test_container_test_mode_no_initialization_side_effects(self):
        """Test that creating container in test mode has no global side effects"""
        # This is critical - test containers shouldn't modify global state

        with patch("mcp_server_langgraph.observability.telemetry.init_observability") as mock_init:
            config = ContainerConfig(environment="test")
            container = ApplicationContainer(config)

            # Get telemetry - should NOT call global init_observability
            _telemetry = container.get_telemetry()  # noqa: F841

            # The global init function should never be called for test containers
            mock_init.assert_not_called()


class TestTelemetryProvider:
    """Test the telemetry provider abstraction"""

    def test_noop_telemetry_provider(self):
        """Test that no-op telemetry provider doesn't throw errors"""
        from mcp_server_langgraph.core.container import NoOpTelemetryProvider

        provider = NoOpTelemetryProvider()

        # Should have logger, metrics, tracer attributes
        assert provider.logger is not None
        assert provider.metrics is not None
        assert provider.tracer is not None

        # Should not raise errors when used
        provider.logger.info("test")
        provider.metrics.counter("test", 1)
        with provider.tracer.start_as_current_span("test"):
            pass

    def test_production_telemetry_provider_initializes(self):
        """Test that production telemetry provider initializes correctly"""
        from mcp_server_langgraph.core.config import Settings
        from mcp_server_langgraph.core.container import ProductionTelemetryProvider

        settings = Settings(
            environment="production",
            auth_provider="keycloak",
            gdpr_storage_backend="postgres",
            jwt_secret_key="test-secret-key-min-32-chars-long-for-security",
            enable_tracing=True,
            enable_metrics=True,
        )

        provider = ProductionTelemetryProvider(settings)

        assert provider.logger is not None
        assert provider.metrics is not None
        assert provider.tracer is not None


class TestAuthProvider:
    """Test the auth provider abstraction"""

    def test_noop_auth_provider(self):
        """Test that no-op auth provider works for tests"""
        from mcp_server_langgraph.core.container import NoOpAuthProvider

        provider = NoOpAuthProvider()

        # Should accept any token
        assert provider.validate_token("any-token") is True

        # Should return mock user
        user = provider.get_current_user("any-token")
        assert user is not None
        assert user.get("user_id") == "test-user"

    def test_inmemory_auth_provider(self):
        """Test in-memory auth provider for development"""
        from mcp_server_langgraph.core.container import InMemoryAuthProvider

        provider = InMemoryAuthProvider()

        # Should be able to create tokens
        token = provider.create_token(user_id="test-123", username="testuser")
        assert token is not None

        # Should validate created tokens
        assert provider.validate_token(token) is True

        # Should retrieve user from token
        user = provider.get_current_user(token)
        assert user["user_id"] == "test-123"
        assert user["username"] == "testuser"


class TestStorageProvider:
    """Test the storage provider abstraction"""

    def test_memory_storage_provider(self):
        """Test in-memory storage provider for tests"""
        from mcp_server_langgraph.core.container import MemoryStorageProvider

        provider = MemoryStorageProvider()

        # Should support basic operations
        provider.set("key1", "value1")
        assert provider.get("key1") == "value1"

        provider.delete("key1")
        assert provider.get("key1") is None

    def test_redis_storage_provider(self):
        """Test Redis storage provider configuration"""
        from mcp_server_langgraph.core.config import Settings
        from mcp_server_langgraph.core.container import RedisStorageProvider

        settings = Settings(environment="development", redis_host="localhost", redis_port=6379)

        # Provider should be created (connection happens lazily)
        provider = RedisStorageProvider(settings)
        assert provider is not None


class TestContainerTestHelpers:
    """Test helper functions for creating test containers"""

    def test_create_test_container_helper(self):
        """Test that create_test_container helper works"""
        from mcp_server_langgraph.core.container import create_test_container

        container = create_test_container()

        assert container.settings.environment == "test"
        assert container.get_telemetry() is not None
        assert container.get_auth() is not None
        assert container.get_storage() is not None

    def test_create_test_container_with_overrides(self):
        """Test that test container accepts overrides"""
        from mcp_server_langgraph.core.config import Settings
        from mcp_server_langgraph.core.container import create_test_container

        custom_settings = Settings(environment="test", log_level="DEBUG")

        container = create_test_container(settings=custom_settings)

        assert container.settings.log_level == "DEBUG"


class TestProductionAuthValidation:
    """Test that production environments require proper external auth"""

    def test_production_validates_auth_provider_at_settings_level(self):
        """
        SECURITY: Production validation happens at Settings level (even better than container).

        Finding #6 claimed container.get_auth() returns InMemoryAuthProvider in production.
        ACTUAL: Settings class validates auth_provider BEFORE container initialization!

        This test documents the EXISTING security feature that prevents the issue.
        """
        from pydantic_core import ValidationError

        from mcp_server_langgraph.core.config import Settings

        # Act & Assert: Settings validation should fail for production with inmemory auth
        with pytest.raises(ValidationError) as exc_info:
            Settings(
                environment="production",
                auth_provider="inmemory",  # Not allowed in production
                jwt_secret_key="test-secret-key-min-32-chars-long-for-security",
            )

        # Validation error should mention the security issue
        error_message = str(exc_info.value)
        assert "AUTH_PROVIDER=inmemory is not allowed in production" in error_message
        assert "keycloak" in error_message.lower()

    def test_production_validates_gdpr_storage_at_settings_level(self):
        """
        SECURITY: Production also validates GDPR storage backend.

        This ensures production uses postgres, not in-memory storage.
        """
        from pydantic_core import ValidationError

        from mcp_server_langgraph.core.config import Settings

        # Act & Assert: Settings validation should fail for production with memory storage
        with pytest.raises(ValidationError) as exc_info:
            Settings(
                environment="production",
                auth_provider="keycloak",
                gdpr_storage_backend="memory",  # Not allowed in production
                keycloak_server_url="https://keycloak.example.com",
                jwt_secret_key="test-secret-key-min-32-chars-long-for-security",
            )

        # Validation error should mention GDPR requirement
        error_message = str(exc_info.value)
        assert "GDPR_STORAGE_BACKEND=memory is not allowed in production" in error_message
        assert "postgres" in error_message.lower()

    def test_production_allows_keycloak_when_configured(self):
        """Test that production with Keycloak configuration succeeds"""
        from mcp_server_langgraph.core.config import Settings

        # Production with Keycloak AND postgres properly configured
        settings = Settings(
            environment="production",
            auth_provider="keycloak",  # Required for production
            gdpr_storage_backend="postgres",  # Required for production
            keycloak_server_url="https://keycloak.example.com",
            keycloak_realm="production",
            keycloak_client_id="mcp-server",
            keycloak_client_secret="secure-secret",
            jwt_secret_key="test-secret-key-min-32-chars-long-for-security",
            database_url="postgresql://user:pass@localhost/db",  # Postgres required
        )

        config = ContainerConfig(environment="production", enable_auth=True)
        container = ApplicationContainer(config, settings=settings)

        # Should NOT raise - Keycloak AND postgres are properly configured
        auth = container.get_auth()
        assert auth is not None

    def test_development_allows_inmemory_auth(self):
        """Test that development mode allows InMemoryAuthProvider"""
        from mcp_server_langgraph.core.config import Settings
        from mcp_server_langgraph.core.container import InMemoryAuthProvider

        settings = Settings(environment="development", enable_auth=True)
        config = ContainerConfig(environment="development")
        container = ApplicationContainer(config, settings=settings)

        # Development should allow InMemoryAuthProvider
        auth = container.get_auth()
        assert auth is not None
        # Should be InMemoryAuthProvider in development
        assert isinstance(auth, InMemoryAuthProvider)

    def test_production_validation_enforces_security_even_with_auth_disabled(self):
        """
        SECURITY: Production ALWAYS requires keycloak auth_provider and postgres storage.

        Even if enable_auth=False, the Settings validator ensures production
        deployments have production-grade backends configured.
        """
        from pydantic_core import ValidationError

        from mcp_server_langgraph.core.config import Settings

        # Act & Assert: Production validation is STRICT - even with enable_auth=False
        with pytest.raises(ValidationError) as exc_info:
            Settings(
                environment="production",
                enable_auth=False,
                # Defaults to auth_provider=inmemory, gdpr_storage_backend=memory
                # Both are blocked in production
            )

        error_message = str(exc_info.value)
        assert "AUTH_PROVIDER=inmemory is not allowed in production" in error_message
        assert "GDPR_STORAGE_BACKEND=memory is not allowed in production" in error_message


class TestContainerIntegrationWithExistingCode:
    """Test that container integrates with existing codebase"""

    def test_container_compatible_with_current_settings(self):
        """Test that container works with existing Settings class"""
        from mcp_server_langgraph.core.config import Settings
        from mcp_server_langgraph.core.container import ApplicationContainer, ContainerConfig

        # Existing Settings class should work
        settings = Settings()

        config = ContainerConfig(environment=settings.environment)
        container = ApplicationContainer(config, settings=settings)

        assert container.settings is settings

    @pytest.mark.integration
    def test_container_can_create_agent(self):
        """Test that container can provide dependencies for agent creation"""
        from mcp_server_langgraph.core.container import create_test_container

        container = create_test_container()

        # Container should provide everything needed for agent
        settings = container.settings
        telemetry = container.get_telemetry()
        storage = container.get_storage()

        assert settings is not None
        assert telemetry is not None
        assert storage is not None

        # These should be sufficient to create an agent
        # (actual agent creation will be tested separately)

    @pytest.mark.integration
    def test_container_can_create_mcp_server(self):
        """Test that container can provide dependencies for MCP server creation"""
        from mcp_server_langgraph.core.container import create_test_container

        container = create_test_container()

        # Container should provide everything needed for server
        settings = container.settings
        telemetry = container.get_telemetry()
        auth = container.get_auth()

        assert settings is not None
        assert telemetry is not None
        assert auth is not None

        # These should be sufficient to create an MCP server
        # (actual server creation will be tested separately)
