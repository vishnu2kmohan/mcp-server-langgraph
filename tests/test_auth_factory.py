"""Comprehensive tests for auth factory module

Tests the factory functions for creating AuthMiddleware, UserProvider, and SessionStore
based on configuration settings.
"""

from unittest.mock import MagicMock, patch

import pytest

from mcp_server_langgraph.auth.factory import create_auth_middleware, create_session_store, create_user_provider
from mcp_server_langgraph.auth.middleware import AuthMiddleware
from mcp_server_langgraph.auth.session import InMemorySessionStore, RedisSessionStore, SessionStore
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

    def test_create_keycloak_provider_missing_admin_password(self, mock_settings):
        """Test error when Keycloak admin password missing"""
        mock_settings.auth_provider = "keycloak"
        mock_settings.keycloak_admin_password = None

        with pytest.raises(ValueError, match="Keycloak admin password required"):
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

        # Should return InMemorySessionStore instance (bug fixed)
        assert store is not None
        assert isinstance(store, InMemorySessionStore)

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

        # Should return InMemorySessionStore (bug fixed, case-insensitive)
        assert store is not None
        assert isinstance(store, InMemorySessionStore)


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


# ============================================================================
# TDD RED Phase: Tests for OpenAI Codex Security Findings
# ============================================================================


@pytest.mark.unit
class TestRedisSessionStoreSignatureFix:
    """
    TDD RED phase tests for Redis session store signature mismatch.

    These tests use the REAL RedisSessionStore class (not mocked) to expose
    the bug where factory.py passes parameters that RedisSessionStore.__init__()
    doesn't accept.

    Expected behavior: These tests will FAIL until the signature is fixed.
    """

    def test_redis_session_store_accepts_password_parameter(self, mock_settings):
        """
        Test that RedisSessionStore accepts password parameter.

        RED: Will fail with TypeError: __init__() got unexpected keyword argument 'password'
        """
        # This should NOT raise TypeError
        try:
            store = RedisSessionStore(
                redis_url="redis://localhost:6379/1",
                password="test-password",  # This parameter is not accepted currently
                default_ttl_seconds=3600,
                sliding_window=True,
                max_concurrent_sessions=5,
                ssl=False,
            )
            # If we got here, password parameter is accepted
            assert store is not None
        except TypeError as e:
            # Expected to fail in RED phase
            pytest.fail(f"RedisSessionStore does not accept 'password' parameter: {e}")

    def test_redis_session_store_accepts_ttl_seconds_parameter(self, mock_settings):
        """
        Test that RedisSessionStore accepts ttl_seconds parameter (as used by factory).

        RED: Will fail because factory uses 'ttl_seconds' but class expects 'default_ttl_seconds'
        """
        # Factory passes ttl_seconds, but class expects default_ttl_seconds
        try:
            store = RedisSessionStore(
                redis_url="redis://localhost:6379/1",
                ttl_seconds=3600,  # Factory uses this name
                sliding_window=True,
                max_concurrent_sessions=5,
                ssl=False,
            )
            # If we got here, ttl_seconds parameter is accepted
            assert store is not None
        except TypeError as e:
            # Expected to fail in RED phase
            pytest.fail(f"RedisSessionStore does not accept 'ttl_seconds' parameter: {e}")

    @patch("redis.asyncio.from_url")
    def test_factory_creates_redis_store_with_real_class(self, mock_redis_client, mock_settings):
        """
        Test that factory can actually instantiate RedisSessionStore with real signature.

        RED: Will fail with TypeError due to signature mismatch between factory and class.
        """
        mock_settings.auth_mode = "session"
        mock_settings.session_backend = "redis"
        mock_settings.redis_url = "redis://localhost:6379/1"
        mock_settings.redis_password = "test-password"
        mock_settings.session_ttl_seconds = 3600

        # This will call the REAL RedisSessionStore (not mocked), exposing the bug
        try:
            store = create_session_store(mock_settings)
            # If we got here, signature is compatible
            assert store is not None
            assert isinstance(store, RedisSessionStore)
        except TypeError as e:
            # Expected to fail in RED phase with signature mismatch
            pytest.fail(f"Factory cannot instantiate RedisSessionStore: {e}")


@pytest.mark.unit
class TestRedisMetadataSerializationFix:
    """
    TDD RED phase tests for Redis metadata serialization bug.

    These tests verify that metadata roundtrips correctly through Redis
    (stored as JSON, retrieved as JSON).

    Expected behavior: These tests will FAIL until str() is replaced with json.dumps().
    """

    @pytest.mark.asyncio
    async def test_redis_metadata_roundtrip_preserves_data(self):
        """
        Test that session metadata survives roundtrip to Redis storage.

        RED: Will fail because str() produces non-JSON format that json.loads() cannot parse.
        """
        # Use real RedisSessionStore with mock Redis client
        from unittest.mock import AsyncMock

        # Create a real storage dict to simulate Redis behavior
        redis_storage = {}

        mock_redis = AsyncMock()

        # Mock hset to actually store data (handles both hset(key, mapping) and hset(key, field, value))
        async def mock_hset(key, field=None, value=None, mapping=None, **kwargs):
            if mapping:
                if key not in redis_storage:
                    redis_storage[key] = {}
                redis_storage[key].update(mapping)
            elif field is not None:
                if key not in redis_storage:
                    redis_storage[key] = {}
                redis_storage[key][field] = value
            return 1

        # Mock hgetall to retrieve stored data
        async def mock_hgetall(key):
            return redis_storage.get(key, {})

        # Mock other required methods
        mock_redis.hset.side_effect = mock_hset
        mock_redis.hgetall.side_effect = mock_hgetall
        mock_redis.expire = AsyncMock(return_value=True)
        mock_redis.rpush = AsyncMock(return_value=1)
        mock_redis.lrange = AsyncMock(return_value=[])

        with patch("redis.asyncio.from_url", return_value=mock_redis):
            store = RedisSessionStore(redis_url="redis://localhost:6379/0")

            metadata = {
                "ip": "192.168.1.100",
                "device": "mobile",
                "browser": "Chrome",
                "count": 42,
            }

            # Create session with metadata
            session_id = await store.create(
                user_id="user:test",
                username="test",
                roles=["user"],
                metadata=metadata,
            )

            # Retrieve session
            session = await store.get(session_id)

            # Metadata should be identical - this will FAIL in RED phase
            assert session is not None
            assert session.metadata == metadata, f"Expected {metadata}, got {session.metadata}"
            assert session.metadata["ip"] == "192.168.1.100"
            assert session.metadata["device"] == "mobile"
            assert session.metadata["count"] == 42

    @pytest.mark.asyncio
    async def test_redis_nested_metadata_serializes_correctly(self):
        """
        Test that nested metadata objects serialize correctly in Redis.

        RED: Will fail with JSON decode error on complex nested structures.
        """
        from unittest.mock import AsyncMock

        # Create a real storage dict
        redis_storage = {}

        mock_redis = AsyncMock()

        async def mock_hset(key, field=None, value=None, mapping=None, **kwargs):
            if mapping:
                if key not in redis_storage:
                    redis_storage[key] = {}
                redis_storage[key].update(mapping)
            elif field is not None:
                if key not in redis_storage:
                    redis_storage[key] = {}
                redis_storage[key][field] = value
            return 1

        async def mock_hgetall(key):
            return redis_storage.get(key, {})

        mock_redis.hset.side_effect = mock_hset
        mock_redis.hgetall.side_effect = mock_hgetall
        mock_redis.expire = AsyncMock(return_value=True)
        mock_redis.rpush = AsyncMock(return_value=1)
        mock_redis.lrange = AsyncMock(return_value=[])

        with patch("redis.asyncio.from_url", return_value=mock_redis):
            store = RedisSessionStore(redis_url="redis://localhost:6379/0")

            metadata = {
                "user_preferences": {
                    "theme": "dark",
                    "language": "en",
                    "notifications": True,
                },
                "session_info": {
                    "login_count": 5,
                    "last_ips": ["192.168.1.1", "192.168.1.2"],
                },
            }

            session_id = await store.create(
                user_id="user:test",
                username="test",
                roles=["user"],
                metadata=metadata,
            )

            session = await store.get(session_id)

            # Nested structures should be preserved - will FAIL in RED phase
            assert session is not None
            assert session.metadata == metadata, f"Expected {metadata}, got {session.metadata}"
            assert session.metadata["user_preferences"]["theme"] == "dark"
            assert session.metadata["session_info"]["login_count"] == 5
            assert "192.168.1.1" in session.metadata["session_info"]["last_ips"]


@pytest.mark.unit
class TestMemorySessionStoreFix:
    """
    TDD RED phase tests for memory session store factory bug.

    Tests verify that factory returns a functional InMemorySessionStore
    instead of None.

    Expected behavior: These tests will FAIL until factory returns InMemorySessionStore().
    """

    def test_factory_creates_memory_session_store(self, mock_settings):
        """
        Test that factory creates InMemorySessionStore for memory backend.

        RED: Will fail because factory returns None instead of InMemorySessionStore().
        """
        mock_settings.auth_mode = "session"
        mock_settings.session_backend = "memory"

        store = create_session_store(mock_settings)

        # Should return InMemorySessionStore, not None
        assert store is not None, "Factory returned None for memory backend"
        assert isinstance(store, InMemorySessionStore)

    @pytest.mark.asyncio
    async def test_memory_sessions_work_with_session_auth_mode(self, mock_settings):
        """
        Test that memory sessions are functional for session auth mode.

        RED: Will fail because factory returns None, making sessions non-functional.
        """
        mock_settings.auth_mode = "session"
        mock_settings.session_backend = "memory"
        mock_settings.session_ttl_seconds = 3600

        store = create_session_store(mock_settings)

        # Store should be functional
        assert store is not None

        # Should be able to create sessions
        session_id = await store.create(
            user_id="user:test",
            username="test",
            roles=["user"],
        )

        assert session_id is not None

        # Should be able to retrieve sessions
        session = await store.get(session_id)
        assert session is not None
        assert session.user_id == "user:test"

    def test_memory_session_store_uses_configured_ttl(self, mock_settings):
        """
        Test that memory session store uses TTL from settings.

        RED: Will fail because factory doesn't pass settings to InMemorySessionStore.
        """
        mock_settings.auth_mode = "session"
        mock_settings.session_backend = "memory"
        mock_settings.session_ttl_seconds = 7200
        mock_settings.session_sliding_window = False
        mock_settings.session_max_concurrent = 10

        store = create_session_store(mock_settings)

        assert store is not None
        assert isinstance(store, InMemorySessionStore)
        assert store.default_ttl == 7200
        assert store.sliding_window is False
        assert store.max_concurrent == 10


# ============================================================================
# TDD Tests: OpenAI Codex Finding #3 - Session Store Registration
# ============================================================================


@pytest.mark.unit
class TestSessionStoreRegistration:
    """
    TDD tests for session store registration bug (OpenAI Codex Finding #3).

    Validates that create_auth_middleware() registers the session store globally
    via set_session_store() so GDPR/session APIs use the configured store.
    """

    def test_create_auth_middleware_registers_memory_session_store_globally(self, mock_settings):
        """Test that memory session store is registered globally after middleware creation"""
        import mcp_server_langgraph.auth.session as session_module
        from mcp_server_langgraph.auth.session import get_session_store

        # Reset global state
        session_module._session_store = None

        # Configure for memory sessions
        mock_settings.auth_mode = "session"
        mock_settings.session_backend = "memory"

        # Create middleware
        middleware = create_auth_middleware(mock_settings)

        # Verify middleware has session store
        assert middleware.session_store is not None
        assert isinstance(middleware.session_store, InMemorySessionStore)

        # CRITICAL: Verify session store was registered globally
        global_store = get_session_store()
        assert global_store is not None, "Session store not registered globally"
        assert global_store is middleware.session_store, "Global store differs from middleware store"

    @patch("mcp_server_langgraph.auth.factory.RedisSessionStore")
    def test_create_auth_middleware_registers_redis_session_store_globally(self, mock_redis_class, mock_settings):
        """Test that Redis session store is registered globally"""
        import mcp_server_langgraph.auth.session as session_module
        from mcp_server_langgraph.auth.session import get_session_store

        # Reset global state
        session_module._session_store = None

        # Configure for Redis sessions
        mock_settings.auth_mode = "session"
        mock_settings.session_backend = "redis"
        mock_redis_instance = MagicMock(spec=RedisSessionStore)
        mock_redis_class.return_value = mock_redis_instance

        # Create middleware
        middleware = create_auth_middleware(mock_settings)

        # Verify Redis store was registered globally
        global_store = get_session_store()
        assert global_store is not None, "Redis session store not registered globally"
        assert global_store is mock_redis_instance

    @pytest.mark.asyncio
    async def test_session_persistence_across_middleware_and_gdpr_endpoints(self, mock_settings):
        """Test session created via middleware is accessible via GDPR endpoints"""
        import mcp_server_langgraph.auth.session as session_module
        from mcp_server_langgraph.auth.session import get_session_store

        # Reset global state
        session_module._session_store = None

        # Configure memory sessions
        mock_settings.auth_mode = "session"
        mock_settings.session_backend = "memory"

        # Create middleware
        middleware = create_auth_middleware(mock_settings)

        # Create session via middleware's session store
        session_id = await middleware.session_store.create(
            user_id="user:gdpr_test",
            username="gdpr_test",
            roles=["user"],
            metadata={"ip": "192.168.1.1"},
        )

        # Simulate GDPR endpoint retrieving the session
        gdpr_store = get_session_store()
        retrieved_session = await gdpr_store.get(session_id)

        # CRITICAL: Session must be retrievable (same store instance)
        assert retrieved_session is not None, "Session not found - stores are different instances"
        assert retrieved_session.user_id == "user:gdpr_test"
        assert retrieved_session.metadata["ip"] == "192.168.1.1"
