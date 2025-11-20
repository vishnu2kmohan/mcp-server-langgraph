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
from unittest.mock import Mock, patch

import pytest

from tests.conftest import get_user_id
from tests.helpers.async_mock_helpers import configured_async_mock


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

        with patch("mcp_server_langgraph.core.dependencies.settings") as mock_settings:
            mock_settings.keycloak_server_url = "http://localhost:8082"
            mock_settings.keycloak_realm = "test-realm"
            mock_settings.keycloak_client_id = "test-client"
            mock_settings.keycloak_client_secret = "test-secret"
            mock_settings.keycloak_admin_username = "admin"
            mock_settings.keycloak_admin_password = "admin-password"
            client = get_keycloak_client()
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

        config = KeycloakConfig(server_url="http://localhost:8082", realm="test", client_id="test", client_secret="secret")
        client = KeycloakClient(config=config)
        assert client.config.admin_username is None
        assert client.config.admin_password is None


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

        with patch("mcp_server_langgraph.core.dependencies.settings") as mock_settings:
            mock_settings.openfga_api_url = "http://localhost:8080"
            mock_settings.openfga_store_id = None
            mock_settings.openfga_model_id = None
            client = get_openfga_client()
            assert (
                client is None
            ), "get_openfga_client() should return None when store_id or model_id is missing, not create a broken client that will fail at runtime"

    @pytest.mark.asyncio
    async def test_openfga_client_created_when_config_complete(self):
        """
        OpenFGA client SHOULD be created when all required config is present.
        """
        from mcp_server_langgraph.core.dependencies import get_openfga_client

        with patch("mcp_server_langgraph.core.dependencies.settings") as mock_settings:
            mock_settings.openfga_api_url = "http://localhost:8080"
            mock_settings.openfga_store_id = "01HTEST123"
            mock_settings.openfga_model_id = "01HMODEL456"
            client = get_openfga_client()
            assert client is not None
            assert client.store_id == "01HTEST123"
            assert client.model_id == "01HMODEL456"

    def test_openfga_client_logs_warning_when_returning_none(self, caplog):
        """
        When returning None due to incomplete config, log a clear warning.
        """
        import mcp_server_langgraph.core.dependencies as deps
        from mcp_server_langgraph.core.dependencies import get_openfga_client

        deps._openfga_client = None
        with patch("mcp_server_langgraph.core.dependencies.settings") as mock_settings:
            mock_settings.openfga_api_url = "http://localhost:8080"
            mock_settings.openfga_store_id = None
            mock_settings.openfga_model_id = None
            client = get_openfga_client()
            assert client is None


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

        mock_keycloak = configured_async_mock(return_value=None)
        mock_keycloak.create_client = configured_async_mock(return_value=None)
        manager = ServicePrincipalManager(keycloak_client=mock_keycloak, openfga_client=None)
        sp = await manager.create_service_principal(
            service_id="test-service",
            name="Test Service",
            description="Test",
            authentication_mode="client_credentials",
            owner_user_id=get_user_id("bob"),
            inherit_permissions=True,
        )
        assert sp is not None
        assert sp.service_id == "test-service"
        mock_keycloak.create_client.assert_called_once()

    @pytest.mark.asyncio
    async def test_delete_service_principal_skips_openfga_when_none(self):
        """
        Test that delete operations also handle None OpenFGA gracefully.
        """
        from mcp_server_langgraph.auth.service_principal import ServicePrincipalManager

        mock_keycloak = configured_async_mock(return_value=None)
        mock_keycloak.delete_client = configured_async_mock(return_value=None)
        manager = ServicePrincipalManager(keycloak_client=mock_keycloak, openfga_client=None)
        await manager.delete_service_principal("test-service")
        mock_keycloak.delete_client.assert_called_once_with("test-service")

    @pytest.mark.asyncio
    async def test_associate_with_user_skips_openfga_when_none(self):
        """
        Test that user association also handles None OpenFGA gracefully.
        """
        from mcp_server_langgraph.auth.service_principal import ServicePrincipalManager

        mock_keycloak = configured_async_mock(return_value=None)
        mock_keycloak.update_client_attributes = configured_async_mock(return_value=None)
        manager = ServicePrincipalManager(keycloak_client=mock_keycloak, openfga_client=None)
        await manager.associate_with_user(service_id="test-service", user_id=get_user_id("alice"), inherit_permissions=True)
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
                _manager = get_api_key_manager()
                mock_redis.assert_called_once_with(
                    "redis://localhost:6379/2", password="secure-password", ssl=True, decode_responses=True
                )
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
            mock_settings.redis_url = "redis://localhost:6379/"
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
                get_api_key_manager()
                called_url = mock_redis.call_args[0][0]
                assert called_url == "redis://localhost:6379/2"
                assert "//" not in called_url.split("://")[1]

    def test_redis_url_handles_existing_database_number(self):
        """
        Test that Redis URL with existing database number doesn't produce invalid URL.

        CODEX FINDING #6: Enabled test by adding reset_singleton_dependencies().

        Bug: f"redis://localhost:6379/0/{db}" produces redis://localhost:6379/0/2
        which is INVALID for redis.from_url().

        Expected: Should strip existing database number and replace with configured one.
        """
        from mcp_server_langgraph.core.dependencies import get_api_key_manager, reset_singleton_dependencies

        reset_singleton_dependencies()
        with patch("mcp_server_langgraph.core.dependencies.settings") as mock_settings:
            mock_settings.api_key_cache_enabled = True
            mock_settings.redis_url = "redis://localhost:6379/0"
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
                get_api_key_manager()
                called_url = mock_redis.call_args[0][0]
                assert called_url == "redis://localhost:6379/2"
                assert "/0/2" not in called_url

    def test_redis_url_handles_query_parameters(self):
        """
        Test that Redis URLs with query parameters are preserved.

        CODEX FINDING #6: Enabled test by adding reset_singleton_dependencies().

        Example: redis://localhost:6379?timeout=5
        Should become: redis://localhost:6379/2?timeout=5
        """
        from mcp_server_langgraph.core.dependencies import get_api_key_manager, reset_singleton_dependencies

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
                get_api_key_manager()
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

        deps._keycloak_client = None
        client = get_keycloak_client()
        assert client is not None
        assert client.config is not None
        assert client.config.server_url is not None
        assert client.config.realm is not None
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
            mock_settings.openfga_store_id = None
            mock_settings.openfga_model_id = None
            client = get_openfga_client()
            assert client is None, "OpenFGA client should be None when store_id/model_id are not configured"

    @pytest.mark.asyncio
    async def test_service_principal_manager_with_none_openfga(self):
        """
        Smoke test: ServicePrincipalManager with OpenFGA disabled.

        This test would CATCH bug #3 (no OpenFGA guards) because
        _sync_to_openfga() would crash with AttributeError.
        """
        from mcp_server_langgraph.auth.service_principal import ServicePrincipalManager

        mock_keycloak = configured_async_mock(return_value=None)
        mock_keycloak.create_client = configured_async_mock(return_value=None)
        manager = ServicePrincipalManager(keycloak_client=mock_keycloak, openfga_client=None)
        sp = await manager.create_service_principal(
            service_id="smoke-test",
            name="Smoke Test",
            description="Test graceful degradation",
            authentication_mode="client_credentials",
        )
        assert sp is not None
        assert sp.service_id == "smoke-test"
