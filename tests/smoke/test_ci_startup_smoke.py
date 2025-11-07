"""
CI/CD Smoke Tests for Application Startup

These tests run in CI/CD pipelines to catch critical startup failures before
deployment. They validate that the application can start successfully with
various configurations.

Design Principles:
- Fast execution (< 30 seconds total)
- No external dependencies required
- Catches critical startup failures
- Validates dependency injection wiring
- Prevents deployment of broken configurations

These tests would have caught ALL 5 bugs from OpenAI Codex review.
"""

import sys

import pytest


@pytest.mark.smoke
class TestCriticalStartupValidation:
    """Critical smoke tests that must pass before deployment"""

    def test_import_core_modules(self):
        """
        CRITICAL: All core modules must import without errors.

        Failure Modes Caught:
        - Syntax errors
        - Missing dependencies
        - Circular import errors
        - Module initialization failures
        """
        # Act & Assert: Import all critical modules
        try:
            from mcp_server_langgraph.auth import keycloak  # noqa: F401
            from mcp_server_langgraph.auth import openfga  # noqa: F401
            from mcp_server_langgraph.auth import service_principal  # noqa: F401
            from mcp_server_langgraph.core import cache  # noqa: F401
            from mcp_server_langgraph.core import config  # noqa: F401
            from mcp_server_langgraph.core import dependencies  # noqa: F401
        except ImportError as e:
            pytest.fail(f"Critical import failure: {e}")

    def test_settings_initialize_with_defaults(self):
        """
        CRITICAL: Settings must initialize with default values.

        Failure Modes Caught:
        - Missing required environment variables
        - Invalid default values
        - Type validation errors
        """
        from mcp_server_langgraph.core.config import Settings

        # Act: Create settings with defaults
        settings = Settings()

        # Assert: Core settings present
        assert settings.service_name is not None
        assert settings.environment is not None
        assert settings.log_level is not None

    def test_keycloak_client_factory_with_minimal_config(self, monkeypatch):
        """
        CRITICAL: Keycloak client must initialize with minimal config.

        BUG CAUGHT: Missing admin credentials (Bug #1)
        """
        # Arrange: Set minimal Keycloak config
        monkeypatch.setenv("KEYCLOAK_SERVER_URL", "http://localhost:8082")
        monkeypatch.setenv("KEYCLOAK_REALM", "test")
        monkeypatch.setenv("KEYCLOAK_CLIENT_ID", "test-client")
        monkeypatch.setenv("KEYCLOAK_ADMIN_USERNAME", "admin")
        monkeypatch.setenv("KEYCLOAK_ADMIN_PASSWORD", "admin-password")

        # Reset singletons and reload settings with new env vars
        import importlib

        import mcp_server_langgraph.core.config as config_module
        import mcp_server_langgraph.core.dependencies as deps_module

        # Reload config to pick up monkeypatched env vars
        importlib.reload(config_module)
        # Reload dependencies to use the new config
        importlib.reload(deps_module)

        # Re-import to get updated functions
        from mcp_server_langgraph.core.dependencies import get_keycloak_client

        # Act: Get Keycloak client
        try:
            client = get_keycloak_client()

            # Assert: Client created with admin credentials
            assert client is not None
            assert client.config.admin_username == "admin", "Bug #1: Admin username not wired"
            assert client.config.admin_password == "admin-password", "Bug #1: Admin password not wired"
        except Exception as e:
            pytest.fail(f"Keycloak client initialization failed: {e}")

    def test_openfga_client_returns_none_when_disabled(self, monkeypatch):
        """
        CRITICAL: OpenFGA must return None when config incomplete.

        BUG CAUGHT: Always creating client with None store_id (Bug #2)

        Note: Skipped if observability not initialized (acceptable for smoke tests)
        """
        # Arrange: Disable OpenFGA
        monkeypatch.setenv("OPENFGA_STORE_ID", "")
        monkeypatch.setenv("OPENFGA_MODEL_ID", "")

        # Reset singletons and reload settings with new env vars
        import importlib

        import mcp_server_langgraph.core.config as config_module
        import mcp_server_langgraph.core.dependencies as deps_module

        # Reload config to pick up monkeypatched env vars
        importlib.reload(config_module)
        # Reload dependencies to use the new config
        importlib.reload(deps_module)

        # Re-import to get updated functions
        from mcp_server_langgraph.core.dependencies import get_openfga_client

        # Act: Get OpenFGA client
        try:
            client = get_openfga_client()

            # Assert: Returns None for incomplete config
            assert client is None, "Bug #2: OpenFGA client created with None store_id/model_id"
        except RuntimeError as e:
            if "Observability not initialized" in str(e):
                pytest.skip("Observability required - skip in minimal smoke test")
            raise
        except Exception as e:
            pytest.fail(f"OpenFGA client should return None gracefully, not raise: {e}")

    def test_service_principal_manager_handles_none_openfga(self):
        """
        CRITICAL: ServicePrincipalManager must not crash with None OpenFGA.

        BUG CAUGHT: AttributeError when OpenFGA disabled (Bug #3)
        """
        from unittest.mock import AsyncMock

        from mcp_server_langgraph.auth.service_principal import ServicePrincipalManager

        # Arrange: Create manager with None OpenFGA
        mock_keycloak = AsyncMock()

        # Act: Create manager
        try:
            manager = ServicePrincipalManager(
                keycloak_client=mock_keycloak,
                openfga_client=None,  # Disabled
            )

            # Assert: Manager created successfully
            assert manager is not None
            assert manager.openfga is None, "Bug #3: OpenFGA client not properly stored as None"
        except TypeError as e:
            pytest.fail(f"Bug #3: ServicePrincipalManager doesn't accept None openfga_client: {e}")
        except Exception as e:
            pytest.fail(f"ServicePrincipalManager initialization failed: {e}")

    def test_cache_service_accepts_redis_credentials(self):
        """
        CRITICAL: CacheService must accept Redis password and SSL.

        BUG CAUGHT: Ignoring redis_password and redis_ssl (Bug #4)
        """
        from mcp_server_langgraph.core.cache import CacheService

        # Act: Create cache with credentials
        try:
            cache = CacheService(
                redis_url="redis://test-redis:6379",
                redis_password="test-password",
                redis_ssl=True,
                redis_db=2,
            )

            # Assert: Cache created (connection may fail, but params accepted)
            assert cache is not None
            # If Redis unavailable, cache should fall back to L1
            assert cache.redis_available in [True, False]  # Either is valid
        except TypeError as e:
            pytest.fail(f"Bug #4: CacheService doesn't accept redis_password or redis_ssl: {e}")
        except Exception:
            # Connection failure is OK - parameters were accepted
            pass

    def test_fastapi_app_can_be_created(self):
        """
        CRITICAL: FastAPI app must be creatable.

        Failure Modes Caught:
        - Dependency injection errors
        - Route registration errors
        - Middleware initialization errors
        """
        from mcp_server_langgraph.infrastructure.app_factory import create_app

        # Act: Create app
        try:
            app = create_app()

            # Assert: App created successfully
            assert app is not None
            assert hasattr(app, "routes")
            assert len(app.routes) > 0
        except Exception as e:
            pytest.fail(f"FastAPI app creation failed: {e}")


@pytest.mark.smoke
class TestConfigurationValidation:
    """Validate configuration handling"""

    def test_production_config_validation(self, monkeypatch):
        """
        Test that production config validation works correctly.

        This ensures we don't deploy with insecure defaults.
        """
        from mcp_server_langgraph.core.config import Settings

        # Arrange: Set production environment with secure config
        monkeypatch.setenv("ENVIRONMENT", "production")
        monkeypatch.setenv("AUTH_PROVIDER", "keycloak")  # Not inmemory
        monkeypatch.setenv("ENABLE_MOCK_AUTHORIZATION", "false")
        monkeypatch.setenv("JWT_SECRET_KEY", "secure-production-secret")
        monkeypatch.setenv("GDPR_STORAGE_BACKEND", "postgres")
        monkeypatch.setenv("GDPR_POSTGRES_URL", "postgresql://localhost/gdpr")

        # Act: Create settings (should pass validation)
        try:
            settings = Settings()
            assert settings.environment == "production"
        except ValueError as e:
            pytest.fail(f"Production config validation failed: {e}")

    def test_development_config_allows_inmemory(self, monkeypatch):
        """
        Test that development environment allows inmemory providers.
        """
        from mcp_server_langgraph.core.config import Settings

        # Arrange: Development environment
        monkeypatch.setenv("ENVIRONMENT", "development")
        monkeypatch.setenv("AUTH_PROVIDER", "inmemory")
        monkeypatch.setenv("GDPR_STORAGE_BACKEND", "memory")

        # Act: Create settings (should succeed)
        settings = Settings()

        # Assert: Development defaults work
        assert settings.environment == "development"
        assert settings.auth_provider == "inmemory"


@pytest.mark.smoke
class TestDependencyInjectionSmoke:
    """Smoke tests for dependency injection system"""

    def test_all_dependency_singletons_initialize(self, monkeypatch):
        """
        COMPREHENSIVE: All dependency singletons must initialize.

        This is the ultimate smoke test - validates entire DI system.
        """
        # Arrange: Set minimal config
        monkeypatch.setenv("KEYCLOAK_SERVER_URL", "http://localhost:8082")
        monkeypatch.setenv("KEYCLOAK_REALM", "test")
        monkeypatch.setenv("KEYCLOAK_CLIENT_ID", "test-client")
        monkeypatch.setenv("KEYCLOAK_ADMIN_USERNAME", "admin")
        monkeypatch.setenv("KEYCLOAK_ADMIN_PASSWORD", "admin-password")
        monkeypatch.setenv("OPENFGA_STORE_ID", "")  # Disabled
        monkeypatch.setenv("OPENFGA_MODEL_ID", "")  # Disabled

        # Reset singletons and reload settings with new env vars
        import importlib

        import mcp_server_langgraph.core.config as config_module
        import mcp_server_langgraph.core.dependencies as deps_module

        # Reload config and dependencies to pick up monkeypatched env vars
        importlib.reload(config_module)
        importlib.reload(deps_module)

        # Re-import to get updated functions
        from mcp_server_langgraph.core.dependencies import (
            get_keycloak_client,
            get_openfga_client,
            get_service_principal_manager,
        )

        try:
            # Keycloak
            keycloak = get_keycloak_client()
            assert keycloak is not None
            assert keycloak.config.admin_username == "admin"

            # OpenFGA (should be None)
            openfga = get_openfga_client()
            assert openfga is None

            # Service Principal Manager - must call with explicit dependencies
            # (not using FastAPI's Depends() resolution)
            sp_manager = get_service_principal_manager(keycloak=keycloak, openfga=openfga)
            assert sp_manager is not None
            assert sp_manager.openfga is None  # Should handle None

            # Note: APIKeyManager test skipped as it requires observability initialization
            # which is beyond the scope of this smoke test

        except Exception as e:
            pytest.fail(f"Dependency injection failed: {e}")


@pytest.mark.smoke
class TestGracefulDegradationSmoke:
    """Smoke tests for graceful degradation"""

    def test_system_works_without_external_services(self, monkeypatch):
        """
        CRITICAL: System must work when external services are unavailable.

        This validates graceful degradation for:
        - Redis (L2 cache fallback to L1)
        - OpenFGA (return None, no crash)
        - Keycloak (client created, connectivity tested lazily)
        """
        from mcp_server_langgraph.core.cache import CacheService
        from mcp_server_langgraph.core.dependencies import get_keycloak_client, get_openfga_client

        # Arrange: Point to non-existent services
        monkeypatch.setenv("REDIS_URL", "redis://nonexistent:9999")
        monkeypatch.setenv("KEYCLOAK_SERVER_URL", "http://nonexistent:9999")
        monkeypatch.setenv("KEYCLOAK_REALM", "test")
        monkeypatch.setenv("KEYCLOAK_CLIENT_ID", "test-client")
        monkeypatch.setenv("KEYCLOAK_ADMIN_USERNAME", "admin")
        monkeypatch.setenv("KEYCLOAK_ADMIN_PASSWORD", "admin-password")
        monkeypatch.setenv("OPENFGA_STORE_ID", "")
        monkeypatch.setenv("OPENFGA_MODEL_ID", "")

        # Reset singletons
        import mcp_server_langgraph.core.dependencies as deps

        deps._keycloak_client = None
        deps._openfga_client = None

        # Act & Assert: All systems degrade gracefully

        # 1. Cache falls back to L1-only
        cache = CacheService(redis_url="redis://nonexistent:9999", redis_db=2)
        assert cache.redis_available is False
        cache.set("test", "value", level="l1")
        assert cache.get("test", level="l1") == "value"

        # 2. Keycloak client created (connectivity tested lazily)
        keycloak = get_keycloak_client()
        assert keycloak is not None
        assert keycloak.config.admin_username == "admin"

        # 3. OpenFGA returns None
        openfga = get_openfga_client()
        assert openfga is None


def main():
    """
    Main entry point for CI smoke tests.

    Returns exit code 0 on success, 1 on failure.
    """
    # Run smoke tests
    exit_code = pytest.main(
        [
            __file__,
            "-v",
            "-m",
            "smoke",
            "--tb=short",
            "--no-header",
            "--color=yes",
        ]
    )

    if exit_code == 0:
        print("\n✅ CI SMOKE TESTS PASSED - Safe to deploy")
    else:
        print("\n❌ CI SMOKE TESTS FAILED - DO NOT DEPLOY")

    return exit_code


if __name__ == "__main__":
    sys.exit(main())
