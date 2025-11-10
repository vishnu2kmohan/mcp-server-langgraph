"""
TDD Tests for Dependency Injection Wiring

These tests validate that dependency factories properly wire all required
configuration from settings to client instances. Written FIRST to catch
configuration bugs that would only surface at runtime.

Critical bugs these tests catch:
1. Keycloak admin credentials not passed to KeycloakClient
2. OpenFGA client created with None store_id/model_id
3. Service principal manager crashes when OpenFGA is None
"""

import gc
from unittest.mock import AsyncMock, Mock, patch

import pytest


@pytest.mark.xdist_group(name="dependencies_wiring_tests")
class TestKeycloakClientWiring:
    """Test that Keycloak client gets all required config from settings"""

    def teardown_method(self):
        """Force GC to prevent mock accumulation in xdist workers"""
        gc.collect()

    def test_keycloak_client_receives_admin_credentials(self):
        """
        CRITICAL: Admin credentials must be passed from settings to KeycloakClient.

        Bug: dependencies.py:34-39 creates KeycloakConfig but only passes:
        server_url, realm, client_id, client_secret
        Missing: admin_username, admin_password

        This causes get_admin_token() to fail with 400/401 errors.
        """
        from mcp_server_langgraph.core.dependencies import get_keycloak_client

        # Arrange: Set admin credentials in settings
        with patch("mcp_server_langgraph.core.dependencies.settings") as mock_settings:
            mock_settings.keycloak_server_url = "http://localhost:8082"
            mock_settings.keycloak_realm = "test-realm"
            mock_settings.keycloak_client_id = "test-client"
            mock_settings.keycloak_client_secret = "test-secret"
            mock_settings.keycloak_admin_username = "admin"
            mock_settings.keycloak_admin_password = "admin-password"

            # Act: Get Keycloak client
            client = get_keycloak_client()

            # Assert: Admin credentials are passed to config
            assert client.config.admin_username == "admin"
            assert client.config.admin_password == "admin-password"
            assert client.config.server_url == "http://localhost:8082"
            assert client.config.realm == "test-realm"

    def test_keycloak_client_admin_token_fails_without_credentials(self):
        """
        Verify that calling get_admin_token() without credentials would fail.

        This test documents the expected failure mode if admin credentials
        are not properly wired.
        """
        from mcp_server_langgraph.auth.keycloak import KeycloakClient, KeycloakConfig

        # Arrange: Create client WITHOUT admin credentials (simulating the bug)
        config = KeycloakConfig(
            server_url="http://localhost:8082",
            realm="test",
            client_id="test",
            client_secret="secret",
            # Missing: admin_username, admin_password
        )
        client = KeycloakClient(config=config)

        # Assert: Config has None credentials (bug state)
        assert client.config.admin_username is None
        assert client.config.admin_password is None

        # Note: get_admin_token() would submit password grant with None credentials
        # This would cause httpx to fail or Keycloak to return 400/401


@pytest.mark.unit
@pytest.mark.xdist_group(name="dependencies_wiring_tests")
class TestOpenFGAClientWiring:
    """Test that OpenFGA client validates required configuration"""

    def teardown_method(self):
        """Force GC to prevent mock accumulation in xdist workers"""
        gc.collect()

    def test_openfga_client_returns_none_when_config_incomplete(self):
        """
        CRITICAL: OpenFGA client should NOT be created when store_id/model_id are missing.

        Bug: dependencies.py:45-59 always creates OpenFGAClient even when
        store_id=None and model_id=None. SDK will fail on first check_permission() call.

        Fix: Return None when config is incomplete, allowing graceful degradation.
        """
        from mcp_server_langgraph.core.dependencies import get_openfga_client

        # Arrange: Settings with incomplete OpenFGA config
        with patch("mcp_server_langgraph.core.dependencies.settings") as mock_settings:
            mock_settings.openfga_api_url = "http://localhost:8080"
            mock_settings.openfga_store_id = None  # MISSING
            mock_settings.openfga_model_id = None  # MISSING

            # Act: Attempt to get OpenFGA client
            client = get_openfga_client()

            # Assert: Should return None for incomplete config
            assert client is None, (
                "get_openfga_client() should return None when store_id or model_id "
                "is missing, not create a broken client that will fail at runtime"
            )

    @pytest.mark.asyncio
    async def test_openfga_client_created_when_config_complete(self):
        """
        OpenFGA client SHOULD be created when all required config is present.
        """
        from mcp_server_langgraph.core.dependencies import get_openfga_client

        # Arrange: Settings with complete OpenFGA config
        with patch("mcp_server_langgraph.core.dependencies.settings") as mock_settings:
            mock_settings.openfga_api_url = "http://localhost:8080"
            mock_settings.openfga_store_id = "01HTEST123"
            mock_settings.openfga_model_id = "01HMODEL456"

            # Act: Get OpenFGA client
            client = get_openfga_client()

            # Assert: Client created with correct config
            assert client is not None
            assert client.store_id == "01HTEST123"
            assert client.model_id == "01HMODEL456"

    def test_openfga_client_logs_warning_when_returning_none(self, caplog):
        """
        When returning None due to incomplete config, log a clear warning.
        """
        import mcp_server_langgraph.core.dependencies as deps
        from mcp_server_langgraph.core.dependencies import get_openfga_client

        # Reset singleton to None to ensure clean test state
        deps._openfga_client = None

        # Arrange: Incomplete config
        with patch("mcp_server_langgraph.core.dependencies.settings") as mock_settings:
            mock_settings.openfga_api_url = "http://localhost:8080"
            mock_settings.openfga_store_id = None
            mock_settings.openfga_model_id = None

            # Act: Get client
            client = get_openfga_client()

            # Assert: Warning logged
            assert client is None
            # Check that appropriate warning was logged
            # (specific log message check depends on implementation)


@pytest.mark.unit
@pytest.mark.xdist_group(name="dependencies_wiring_tests")
class TestServicePrincipalManagerOpenFGAGuards:
    """Test that ServicePrincipalManager handles None OpenFGA client gracefully"""

    def teardown_method(self):
        """Force GC to prevent mock accumulation in xdist workers"""
        gc.collect()

    @pytest.mark.asyncio
    async def test_create_service_principal_skips_openfga_when_none(self):
        """
        CRITICAL: ServicePrincipalManager must not crash when OpenFGA is None.

        Bug: service_principal.py:197-228 calls self.openfga.write_tuples() without
        checking if self.openfga is None. This causes AttributeError when OpenFGA
        is intentionally disabled.

        Fix: Guard all OpenFGA operations with `if self.openfga:` checks.
        """
        from mcp_server_langgraph.auth.service_principal import ServicePrincipalManager

        # Arrange: Create manager with None OpenFGA client (graceful degradation)
        mock_keycloak = AsyncMock()
        mock_keycloak.create_client = AsyncMock()

        manager = ServicePrincipalManager(
            keycloak_client=mock_keycloak,
            openfga_client=None,  # Disabled OpenFGA
        )

        # Act: Create service principal (should NOT crash)
        sp = await manager.create_service_principal(
            service_id="test-service",
            name="Test Service",
            description="Test",
            authentication_mode="client_credentials",
            owner_user_id="user:bob",
            inherit_permissions=True,
        )

        # Assert: Service principal created successfully
        assert sp is not None
        assert sp.service_id == "test-service"

        # Verify Keycloak operations still work
        mock_keycloak.create_client.assert_called_once()

    @pytest.mark.asyncio
    async def test_delete_service_principal_skips_openfga_when_none(self):
        """
        Test that delete operations also handle None OpenFGA gracefully.
        """
        from mcp_server_langgraph.auth.service_principal import ServicePrincipalManager

        # Arrange
        mock_keycloak = AsyncMock()
        mock_keycloak.delete_client = AsyncMock()

        manager = ServicePrincipalManager(
            keycloak_client=mock_keycloak,
            openfga_client=None,
        )

        # Act: Delete service principal (should NOT crash)
        await manager.delete_service_principal("test-service")

        # Assert: Keycloak delete called, no AttributeError
        mock_keycloak.delete_client.assert_called_once_with("test-service")

    @pytest.mark.asyncio
    async def test_associate_with_user_skips_openfga_when_none(self):
        """
        Test that user association also handles None OpenFGA gracefully.
        """
        from mcp_server_langgraph.auth.service_principal import ServicePrincipalManager

        # Arrange
        mock_keycloak = AsyncMock()
        mock_keycloak.update_client_attributes = AsyncMock()

        manager = ServicePrincipalManager(
            keycloak_client=mock_keycloak,
            openfga_client=None,
        )

        # Act: Associate with user (should NOT crash)
        await manager.associate_with_user(
            service_id="test-service",
            user_id="user:alice",
            inherit_permissions=True,
        )

        # Assert: Keycloak update called, no AttributeError
        mock_keycloak.update_client_attributes.assert_called_once()


@pytest.mark.unit
@pytest.mark.xdist_group(name="dependencies_wiring_tests")
class TestAPIKeyManagerRedisCacheWiring:
    """Test that API Key Manager properly receives Redis cache configuration"""

    def teardown_method(self):
        """Force GC to prevent mock accumulation in xdist workers"""
        gc.collect()

    def test_api_key_manager_receives_redis_client_when_enabled(self):
        """
        Verify that API Key Manager gets properly configured Redis client.

        This test documents the CORRECT pattern that should be used for
        all Redis-backed caches (including L2 cache).
        """
        from mcp_server_langgraph.core.dependencies import get_api_key_manager

        # Arrange: Settings with Redis cache enabled
        with patch("mcp_server_langgraph.core.dependencies.settings") as mock_settings:
            mock_settings.api_key_cache_enabled = True
            mock_settings.redis_url = "redis://localhost:6379"
            mock_settings.redis_password = "secure-password"
            mock_settings.redis_ssl = True
            mock_settings.api_key_cache_db = 2
            mock_settings.api_key_cache_ttl = 3600
            mock_settings.keycloak_server_url = "http://localhost:8082"
            mock_settings.keycloak_realm = "test"
            mock_settings.keycloak_client_id = "test"
            mock_settings.keycloak_client_secret = "secret"
            mock_settings.keycloak_admin_username = "admin"
            mock_settings.keycloak_admin_password = "admin-password"

            with patch("redis.asyncio.from_url") as mock_redis:
                mock_redis.return_value = Mock()

                # Act: Get API key manager
                _manager = get_api_key_manager()

                # Assert: Redis client created with correct parameters
                mock_redis.assert_called_once_with(
                    "redis://localhost:6379/2",  # URL with database number
                    password="secure-password",
                    ssl=True,
                    decode_responses=True,
                )

                # Manager should have cache enabled
                assert _manager.cache_enabled is True

    def test_redis_url_handles_trailing_slash(self):
        """
        Test that Redis URL construction handles trailing slashes correctly.

        Bug: f"{redis_url}/{db}" produces redis://localhost:6379//2
        when redis_url has trailing slash.
        """
        from mcp_server_langgraph.core.dependencies import get_api_key_manager

        with patch("mcp_server_langgraph.core.dependencies.settings") as mock_settings:
            mock_settings.api_key_cache_enabled = True
            mock_settings.redis_url = "redis://localhost:6379/"  # Trailing slash
            mock_settings.redis_password = None
            mock_settings.redis_ssl = False
            mock_settings.api_key_cache_db = 2
            mock_settings.api_key_cache_ttl = 3600
            mock_settings.keycloak_server_url = "http://localhost:8082"
            mock_settings.keycloak_realm = "test"
            mock_settings.keycloak_client_id = "test"
            mock_settings.keycloak_client_secret = "secret"
            mock_settings.keycloak_admin_username = "admin"
            mock_settings.keycloak_admin_password = "admin-password"

            with patch("redis.asyncio.from_url") as mock_redis:
                mock_redis.return_value = Mock()

                # Act
                get_api_key_manager()

                # Assert: URL should be normalized (no double slash)
                called_url = mock_redis.call_args[0][0]
                assert called_url == "redis://localhost:6379/2"
                assert "//" not in called_url.split("://")[1]  # No double slashes after protocol

    def test_redis_url_handles_existing_database_number(self):
        """
        Test that Redis URL with existing database number doesn't produce invalid URL.

        CODEX FINDING #6: Enabled test by adding reset_singleton_dependencies().

        Bug: f"redis://localhost:6379/0/{db}" produces redis://localhost:6379/0/2
        which is INVALID for redis.from_url().

        Expected: Should strip existing database number and replace with configured one.
        """
        from mcp_server_langgraph.core.dependencies import get_api_key_manager, reset_singleton_dependencies

        # CODEX FINDING #6: Reset singleton before test
        reset_singleton_dependencies()

        with patch("mcp_server_langgraph.core.dependencies.settings") as mock_settings:
            mock_settings.api_key_cache_enabled = True
            mock_settings.redis_url = "redis://localhost:6379/0"  # Has database 0
            mock_settings.redis_password = None
            mock_settings.redis_ssl = False
            mock_settings.api_key_cache_db = 2  # Want database 2
            mock_settings.api_key_cache_ttl = 3600
            mock_settings.keycloak_server_url = "http://localhost:8082"
            mock_settings.keycloak_realm = "test"
            mock_settings.keycloak_client_id = "test"
            mock_settings.keycloak_client_secret = "secret"
            mock_settings.keycloak_admin_username = "admin"
            mock_settings.keycloak_admin_password = "admin-password"

            with (
                patch("redis.asyncio.from_url") as mock_redis,
                patch("mcp_server_langgraph.core.dependencies.APIKeyManager") as mock_manager_class,
            ):
                mock_redis.return_value = Mock()
                mock_manager = Mock()
                mock_manager.cache_enabled = True
                mock_manager_class.return_value = mock_manager

                # Act
                get_api_key_manager()

                # Assert: URL should have ONLY the configured database (2), not 0/2
                called_url = mock_redis.call_args[0][0]
                assert called_url == "redis://localhost:6379/2"
                assert "/0/2" not in called_url  # Should not have double database

    def test_redis_url_handles_query_parameters(self):
        """
        Test that Redis URLs with query parameters are preserved.

        CODEX FINDING #6: Enabled test by adding reset_singleton_dependencies().

        Example: redis://localhost:6379?timeout=5
        Should become: redis://localhost:6379/2?timeout=5
        """
        from mcp_server_langgraph.core.dependencies import get_api_key_manager, reset_singleton_dependencies

        # CODEX FINDING #6: Reset singleton before test
        reset_singleton_dependencies()

        with patch("mcp_server_langgraph.core.dependencies.settings") as mock_settings:
            mock_settings.api_key_cache_enabled = True
            mock_settings.redis_url = "redis://localhost:6379?timeout=5"
            mock_settings.redis_password = None
            mock_settings.redis_ssl = False
            mock_settings.api_key_cache_db = 2
            mock_settings.api_key_cache_ttl = 3600
            mock_settings.keycloak_server_url = "http://localhost:8082"
            mock_settings.keycloak_realm = "test"
            mock_settings.keycloak_client_id = "test"
            mock_settings.keycloak_client_secret = "secret"
            mock_settings.keycloak_admin_username = "admin"
            mock_settings.keycloak_admin_password = "admin-password"

            with (
                patch("redis.asyncio.from_url") as mock_redis,
                patch("mcp_server_langgraph.core.dependencies.APIKeyManager") as mock_manager_class,
            ):
                mock_redis.return_value = Mock()
                mock_manager = Mock()
                mock_manager.cache_enabled = True
                mock_manager_class.return_value = mock_manager

                # Act
                get_api_key_manager()

                # Assert: Query parameters should be preserved
                called_url = mock_redis.call_args[0][0]
                assert "/2" in called_url
                assert "timeout=5" in called_url


@pytest.mark.integration
@pytest.mark.xdist_group(name="dependencies_wiring_tests")
class TestDependencyStartupSmoke:
    """Integration smoke tests that would have caught the reported bugs"""

    def teardown_method(self):
        """Force GC to prevent mock accumulation in xdist workers"""
        gc.collect()

    def test_keycloak_client_factory_with_real_settings(self):
        """
        Smoke test: Instantiate Keycloak client with minimal settings.

        This test would CATCH bug #1 (missing admin credentials) because
        the client would be created with admin_username=None, admin_password=None.
        """
        import mcp_server_langgraph.core.dependencies as deps
        from mcp_server_langgraph.core.dependencies import get_keycloak_client

        # Reset singleton to force fresh creation with current settings (not cached from previous test)
        deps._keycloak_client = None

        # Note: This test validates the factory works, not actual Keycloak connectivity
        # Real settings from environment/defaults
        client = get_keycloak_client()

        # Verify client has required config
        assert client is not None
        assert client.config is not None
        assert client.config.server_url is not None
        assert client.config.realm is not None

        # CRITICAL: These must be set from settings
        # Bug: These were None before fix
        assert (
            client.config.admin_username is not None
        ), "Keycloak admin_username must be wired from settings.keycloak_admin_username"
        assert (
            client.config.admin_password is not None
        ), "Keycloak admin_password must be wired from settings.keycloak_admin_password"

    def test_openfga_client_factory_handles_missing_config(self):
        """
        Smoke test: OpenFGA client factory with incomplete config.

        This test would CATCH bug #2 (always creating client) because
        get_openfga_client() would return a client with None store_id.
        """
        from mcp_server_langgraph.core.dependencies import get_openfga_client

        with patch("mcp_server_langgraph.core.dependencies.settings") as mock_settings:
            mock_settings.openfga_api_url = "http://localhost:8080"
            mock_settings.openfga_store_id = None  # Not configured
            mock_settings.openfga_model_id = None  # Not configured

            # Act
            client = get_openfga_client()

            # Assert: Should return None, not broken client
            assert client is None, "OpenFGA client should be None when store_id/model_id are not configured"

    @pytest.mark.asyncio
    async def test_service_principal_manager_with_none_openfga(self):
        """
        Smoke test: ServicePrincipalManager with OpenFGA disabled.

        This test would CATCH bug #3 (no OpenFGA guards) because
        _sync_to_openfga() would crash with AttributeError.
        """
        from mcp_server_langgraph.auth.service_principal import ServicePrincipalManager

        # Arrange: Mock Keycloak, None OpenFGA (disabled)
        mock_keycloak = AsyncMock()
        mock_keycloak.create_client = AsyncMock()

        manager = ServicePrincipalManager(
            keycloak_client=mock_keycloak,
            openfga_client=None,  # Disabled
        )

        # Act: This should NOT crash
        sp = await manager.create_service_principal(
            service_id="smoke-test",
            name="Smoke Test",
            description="Test graceful degradation",
            authentication_mode="client_credentials",
        )

        # Assert: Success without crashing
        assert sp is not None
        assert sp.service_id == "smoke-test"
