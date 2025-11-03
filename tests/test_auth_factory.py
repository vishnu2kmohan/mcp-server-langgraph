"""Comprehensive tests for auth factory module

Tests the factory functions for creating AuthMiddleware, UserProvider, and SessionStore
based on configuration settings.
"""

from unittest.mock import MagicMock, patch

import pytest

from mcp_server_langgraph.auth.factory import create_auth_middleware, create_session_store, create_user_provider
from mcp_server_langgraph.auth.middleware import AuthMiddleware
from mcp_server_langgraph.auth.session import RedisSessionStore, SessionStore
from mcp_server_langgraph.auth.user_provider import InMemoryUserProvider, KeycloakUserProvider, UserProvider

# ============================================================================
# Fixtures
# ============================================================================


@pytest.fixture
def mock_settings():
    """Create mock settings object"""
    settings = MagicMock()
    # Default settings for inmemory provider
    settings.auth_provider = "inmemory"
    settings.auth_mode = "token"
    settings.session_backend = "memory"
    settings.jwt_secret_key = "test-secret-key-change-in-production"
    settings.use_password_hashing = False
    # Keycloak settings
    settings.keycloak_server_url = "http://localhost:8180"
    settings.keycloak_realm = "test-realm"
    settings.keycloak_client_id = "test-client"
    settings.keycloak_client_secret = "test-secret"
    settings.keycloak_admin_username = "admin"
    settings.keycloak_admin_password = "admin-password"
    settings.keycloak_verify_ssl = True
    settings.keycloak_timeout = 10
    # Redis settings
    settings.redis_url = "redis://localhost:6379/1"
    settings.redis_password = None
    settings.redis_ssl = False
    settings.session_ttl_seconds = 3600
    settings.session_sliding_window = True
    settings.session_max_concurrent = 5
    return settings


@pytest.fixture
def mock_openfga_client():
    """Create mock OpenFGA client"""
    return MagicMock()


# ============================================================================
# Tests for create_user_provider()
# ============================================================================


@pytest.mark.unit
class TestCreateUserProvider:
    """Test create_user_provider factory function"""

    def test_create_inmemory_provider(self, mock_settings):
        """Test creating InMemoryUserProvider"""
        provider = create_user_provider(mock_settings)

        assert isinstance(provider, InMemoryUserProvider)
        assert provider is not None

    def test_create_inmemory_provider_with_openfga(self, mock_settings, mock_openfga_client):
        """Test creating InMemoryUserProvider with OpenFGA client"""
        provider = create_user_provider(mock_settings, mock_openfga_client)

        assert isinstance(provider, InMemoryUserProvider)
        # Provider should be created successfully
        assert provider is not None

    def test_create_inmemory_provider_missing_jwt_secret(self, mock_settings):
        """Test error when JWT secret missing for InMemory provider"""
        mock_settings.jwt_secret_key = None

        with pytest.raises(ValueError, match="JWT secret key required"):
            create_user_provider(mock_settings)

    @patch("mcp_server_langgraph.auth.factory.KeycloakUserProvider")
    def test_create_keycloak_provider(self, mock_keycloak_class, mock_settings, mock_openfga_client):
        """Test creating KeycloakUserProvider"""
        mock_settings.auth_provider = "keycloak"
        mock_keycloak_instance = MagicMock(spec=KeycloakUserProvider)
        mock_keycloak_class.return_value = mock_keycloak_instance

        create_user_provider(mock_settings, mock_openfga_client)

        # Verify KeycloakUserProvider was instantiated
        assert mock_keycloak_class.called
        call_kwargs = mock_keycloak_class.call_args[1]
        assert "config" in call_kwargs
        assert "openfga_client" in call_kwargs
        assert call_kwargs["openfga_client"] == mock_openfga_client
        assert call_kwargs["sync_on_login"] is True

    def test_create_keycloak_provider_missing_client_secret(self, mock_settings):
        """Test error when Keycloak client secret missing"""
        mock_settings.auth_provider = "keycloak"
        mock_settings.keycloak_client_secret = None

        with pytest.raises(ValueError, match="Keycloak client secret required"):
            create_user_provider(mock_settings)

    def test_create_provider_invalid_type(self, mock_settings):
        """Test error for unknown provider type"""
        mock_settings.auth_provider = "invalid_provider"

        with pytest.raises(ValueError, match="Unknown auth provider"):
            create_user_provider(mock_settings)

    def test_create_provider_case_insensitive(self, mock_settings):
        """Test provider type is case-insensitive"""
        mock_settings.auth_provider = "INMEMORY"

        provider = create_user_provider(mock_settings)

        assert isinstance(provider, InMemoryUserProvider)


# ============================================================================
# Tests for Production Environment Guards (TDD RED phase)
# ============================================================================


@pytest.mark.unit
class TestProductionEnvironmentGuards:
    """
    Test production environment guards for InMemoryUserProvider.

    TDD RED phase: Tests written FIRST to define security requirements.
    These tests will FAIL until environment guards are implemented.
    """

    def test_inmemory_provider_blocked_in_production(self, mock_settings):
        """
        Test InMemoryUserProvider is blocked in production environment.

        RED: Will fail until environment guard is implemented in factory.py
        """
        mock_settings.auth_provider = "inmemory"
        mock_settings.environment = "production"

        with pytest.raises(RuntimeError, match="InMemoryUserProvider is not allowed in production"):
            create_user_provider(mock_settings)

    def test_inmemory_provider_blocked_in_staging(self, mock_settings):
        """Test InMemoryUserProvider is blocked in staging environment"""
        mock_settings.auth_provider = "inmemory"
        mock_settings.environment = "staging"

        with pytest.raises(RuntimeError, match="InMemoryUserProvider is not allowed in production"):
            create_user_provider(mock_settings)

    def test_inmemory_provider_allowed_in_development(self, mock_settings):
        """Test InMemoryUserProvider is allowed in development"""
        mock_settings.auth_provider = "inmemory"
        mock_settings.environment = "development"

        provider = create_user_provider(mock_settings)

        assert isinstance(provider, InMemoryUserProvider)

    def test_inmemory_provider_allowed_in_test(self, mock_settings):
        """Test InMemoryUserProvider is allowed in test environment"""
        mock_settings.auth_provider = "inmemory"
        mock_settings.environment = "test"

        provider = create_user_provider(mock_settings)

        assert isinstance(provider, InMemoryUserProvider)

    def test_inmemory_provider_default_environment_is_development(self, mock_settings):
        """Test default environment is development (safe fallback)"""
        mock_settings.auth_provider = "inmemory"
        # No environment attribute set

        provider = create_user_provider(mock_settings)

        # Should succeed (defaults to development)
        assert isinstance(provider, InMemoryUserProvider)

    def test_keycloak_provider_allowed_in_production(self, mock_settings):
        """Test KeycloakUserProvider is allowed in production"""
        mock_settings.auth_provider = "keycloak"
        mock_settings.environment = "production"

        with patch("mcp_server_langgraph.auth.factory.KeycloakUserProvider"):
            provider = create_user_provider(mock_settings)

            # Should succeed (Keycloak is production-safe)
            assert provider is not None

    def test_environment_validation_case_insensitive(self, mock_settings):
        """Test environment names are case-insensitive"""
        mock_settings.auth_provider = "inmemory"
        mock_settings.environment = "PRODUCTION"

        with pytest.raises(RuntimeError, match="InMemoryUserProvider is not allowed in production"):
            create_user_provider(mock_settings)


# ============================================================================
# Tests for create_session_store()
# ============================================================================


@pytest.mark.unit
class TestCreateSessionStore:
    """Test create_session_store factory function"""

    def test_create_session_store_disabled_for_token_auth(self, mock_settings):
        """Test session store returns None when auth_mode is token"""
        mock_settings.auth_mode = "token"

        store = create_session_store(mock_settings)

        assert store is None

    def test_create_memory_session_store(self, mock_settings):
        """Test creating in-memory session store"""
        mock_settings.auth_mode = "session"
        mock_settings.session_backend = "memory"

        store = create_session_store(mock_settings)

        # Currently returns None - in-memory not implemented yet
        assert store is None

    @patch("mcp_server_langgraph.auth.factory.RedisSessionStore")
    def test_create_redis_session_store(self, mock_redis_class, mock_settings):
        """Test creating Redis session store"""
        mock_settings.auth_mode = "session"
        mock_settings.session_backend = "redis"
        mock_redis_instance = MagicMock(spec=RedisSessionStore)
        mock_redis_class.return_value = mock_redis_instance

        store = create_session_store(mock_settings)

        # Verify RedisSessionStore was instantiated with correct parameters
        mock_redis_class.assert_called_once_with(
            redis_url=mock_settings.redis_url,
            password=mock_settings.redis_password,
            ssl=mock_settings.redis_ssl,
            ttl_seconds=mock_settings.session_ttl_seconds,
            sliding_window=mock_settings.session_sliding_window,
            max_concurrent_sessions=mock_settings.session_max_concurrent,
        )
        assert store == mock_redis_instance

    def test_create_redis_session_store_missing_url(self, mock_settings):
        """Test error when Redis URL missing"""
        mock_settings.auth_mode = "session"
        mock_settings.session_backend = "redis"
        mock_settings.redis_url = None

        with pytest.raises(ValueError, match="Redis URL required"):
            create_session_store(mock_settings)

    def test_create_session_store_invalid_backend(self, mock_settings):
        """Test error for unknown session backend"""
        mock_settings.auth_mode = "session"
        mock_settings.session_backend = "invalid_backend"

        with pytest.raises(ValueError, match="Unknown session backend"):
            create_session_store(mock_settings)

    def test_create_session_store_case_insensitive(self, mock_settings):
        """Test session backend is case-insensitive"""
        mock_settings.auth_mode = "session"
        mock_settings.session_backend = "MEMORY"

        store = create_session_store(mock_settings)

        # Returns None (in-memory not implemented)
        assert store is None


# ============================================================================
# Tests for create_auth_middleware()
# ============================================================================


@pytest.mark.unit
class TestCreateAuthMiddleware:
    """Test create_auth_middleware factory function"""

    def test_create_auth_middleware_inmemory(self, mock_settings):
        """Test creating AuthMiddleware with InMemory provider"""
        middleware = create_auth_middleware(mock_settings)

        assert isinstance(middleware, AuthMiddleware)
        assert middleware.secret_key == mock_settings.jwt_secret_key
        assert middleware.user_provider is not None
        assert isinstance(middleware.user_provider, InMemoryUserProvider)

    def test_create_auth_middleware_with_openfga(self, mock_settings, mock_openfga_client):
        """Test creating AuthMiddleware with OpenFGA client"""
        middleware = create_auth_middleware(mock_settings, mock_openfga_client)

        assert isinstance(middleware, AuthMiddleware)
        assert middleware.openfga == mock_openfga_client  # Changed from openfga_client to openfga

    @patch("mcp_server_langgraph.auth.factory.KeycloakUserProvider")
    def test_create_auth_middleware_keycloak(self, mock_keycloak_class, mock_settings, mock_openfga_client):
        """Test creating AuthMiddleware with Keycloak provider"""
        mock_settings.auth_provider = "keycloak"
        mock_keycloak_instance = MagicMock(spec=KeycloakUserProvider)
        mock_keycloak_class.return_value = mock_keycloak_instance

        middleware = create_auth_middleware(mock_settings, mock_openfga_client)

        assert isinstance(middleware, AuthMiddleware)
        assert middleware.user_provider == mock_keycloak_instance

    @patch("mcp_server_langgraph.auth.factory.RedisSessionStore")
    def test_create_auth_middleware_with_sessions(self, mock_redis_class, mock_settings):
        """Test creating AuthMiddleware with session store"""
        mock_settings.auth_mode = "session"
        mock_settings.session_backend = "redis"
        mock_redis_instance = MagicMock(spec=RedisSessionStore)
        mock_redis_class.return_value = mock_redis_instance

        middleware = create_auth_middleware(mock_settings)

        assert isinstance(middleware, AuthMiddleware)
        assert middleware.session_store == mock_redis_instance

    def test_create_auth_middleware_token_mode_no_sessions(self, mock_settings):
        """Test AuthMiddleware has no session store in token mode"""
        mock_settings.auth_mode = "token"

        middleware = create_auth_middleware(mock_settings)

        assert isinstance(middleware, AuthMiddleware)
        assert middleware.session_store is None

    def test_create_auth_middleware_missing_jwt_secret(self, mock_settings):
        """Test error propagates from user provider creation"""
        mock_settings.jwt_secret_key = None

        with pytest.raises(ValueError, match="JWT secret key required"):
            create_auth_middleware(mock_settings)

    def test_create_auth_middleware_missing_keycloak_secret(self, mock_settings):
        """Test error propagates from Keycloak provider creation"""
        mock_settings.auth_provider = "keycloak"
        mock_settings.keycloak_client_secret = None

        with pytest.raises(ValueError, match="Keycloak client secret required"):
            create_auth_middleware(mock_settings)


# ============================================================================
# Integration Tests
# ============================================================================


@pytest.mark.unit
class TestFactoryIntegration:
    """Integration tests for factory module"""

    def test_full_middleware_creation_flow(self, mock_settings, mock_openfga_client):
        """Test complete middleware creation with all components"""
        mock_settings.auth_provider = "inmemory"
        mock_settings.auth_mode = "token"

        middleware = create_auth_middleware(mock_settings, mock_openfga_client)

        # Verify all components are properly wired
        assert isinstance(middleware, AuthMiddleware)
        assert isinstance(middleware.user_provider, InMemoryUserProvider)
        assert middleware.openfga == mock_openfga_client  # Changed from openfga_client to openfga
        assert middleware.session_store is None  # Token mode
        assert middleware.secret_key == mock_settings.jwt_secret_key

    @patch("mcp_server_langgraph.auth.factory.KeycloakUserProvider")
    @patch("mcp_server_langgraph.auth.factory.RedisSessionStore")
    def test_full_production_setup(self, mock_redis_class, mock_keycloak_class, mock_settings, mock_openfga_client):
        """Test production-like setup with Keycloak and Redis"""
        # Configure production-like settings
        mock_settings.auth_provider = "keycloak"
        mock_settings.auth_mode = "session"
        mock_settings.session_backend = "redis"

        mock_keycloak_instance = MagicMock(spec=KeycloakUserProvider)
        mock_keycloak_class.return_value = mock_keycloak_instance
        mock_redis_instance = MagicMock(spec=RedisSessionStore)
        mock_redis_class.return_value = mock_redis_instance

        middleware = create_auth_middleware(mock_settings, mock_openfga_client)

        # Verify production components
        assert isinstance(middleware, AuthMiddleware)
        assert middleware.user_provider == mock_keycloak_instance
        assert middleware.session_store == mock_redis_instance
        assert middleware.openfga == mock_openfga_client  # Changed from openfga_client to openfga
