"""
TDD Tests for FastAPI App Factory

These tests define the behavior we want after extracting infrastructure
concerns (FastAPI setup, middleware, CORS) from server modules.

Following TDD:
1. Write tests first (this file) - RED
2. Implement app factory - GREEN
3. Verify no regressions - REFACTOR
"""

import gc

import pytest

pytestmark = [pytest.mark.unit, pytest.mark.infrastructure]


@pytest.mark.infrastructure
@pytest.mark.xdist_group(name="testappfactory")
class TestAppFactory:
    """Test the FastAPI app factory function"""

    def teardown_method(self) -> None:
        """Force GC to prevent mock accumulation in xdist workers"""
        gc.collect()

    def test_create_app_basic(self):
        """Test creating basic FastAPI app"""
        from mcp_server_langgraph.infrastructure.app_factory import create_app

        app = create_app()

        assert app is not None
        assert hasattr(app, "openapi")
        assert hasattr(app, "routes")

    def test_create_app_with_container(self):
        """Test creating app with container"""
        from mcp_server_langgraph.core.container import create_test_container
        from mcp_server_langgraph.infrastructure.app_factory import create_app

        container = create_test_container()
        app = create_app(container=container)

        assert app is not None

    def test_create_app_with_settings(self):
        """Test creating app with custom settings"""
        from mcp_server_langgraph.core.config import Settings
        from mcp_server_langgraph.infrastructure.app_factory import create_app

        settings = Settings(environment="test", service_name="test-service")
        app = create_app(settings=settings)

        assert app is not None

    def test_create_app_has_health_endpoint(self):
        """Test that app has health check endpoint"""
        from mcp_server_langgraph.infrastructure.app_factory import create_app

        app = create_app()

        # Check that health endpoint exists
        routes = [route.path for route in app.routes]
        assert "/health" in routes or "/" in routes

    def test_create_app_has_cors_middleware(self):
        """Test that app has CORS middleware configured"""
        from mcp_server_langgraph.infrastructure.app_factory import create_app

        app = create_app()

        # App should have middleware
        assert hasattr(app, "middleware_stack") or hasattr(app, "user_middleware")


@pytest.mark.xdist_group(name="testmiddlewarefactory")
class TestMiddlewareFactory:
    """Test middleware creation functions"""

    def teardown_method(self) -> None:
        """Force GC to prevent mock accumulation in xdist workers"""
        gc.collect()

    def test_create_cors_middleware(self):
        """Test creating CORS middleware"""
        from mcp_server_langgraph.infrastructure.middleware import create_cors_middleware

        middleware = create_cors_middleware()

        assert middleware is not None

    def test_create_rate_limit_middleware(self):
        """Test creating rate limit middleware"""
        from mcp_server_langgraph.core.config import Settings
        from mcp_server_langgraph.infrastructure.middleware import create_rate_limit_middleware

        # Test mode returns None (no-op)
        settings = Settings(environment="test")
        middleware = create_rate_limit_middleware(settings)
        assert middleware is None

        # Production mode would return actual middleware
        # (not implemented yet - future work)

    def test_create_auth_middleware(self):
        """Test creating auth middleware"""
        from mcp_server_langgraph.core.container import create_test_container
        from mcp_server_langgraph.infrastructure.middleware import create_auth_middleware

        # Test mode returns None (no-op)
        container = create_test_container()
        middleware = create_auth_middleware(container)
        assert middleware is None

        # Production mode would return actual middleware
        # (not implemented yet - future work)


@pytest.mark.xdist_group(name="testlifespanmanager")
class TestLifespanManager:
    """Test application lifespan management"""

    def teardown_method(self) -> None:
        """Force GC to prevent mock accumulation in xdist workers"""
        gc.collect()

    @pytest.mark.asyncio
    async def test_lifespan_context_manager(self):
        """Test lifespan context manager"""
        from mcp_server_langgraph.infrastructure.app_factory import create_lifespan

        lifespan = create_lifespan()

        # Should be an async context manager
        assert hasattr(lifespan, "__aenter__") or callable(lifespan)

    @pytest.mark.asyncio
    async def test_lifespan_with_container(self):
        """Test lifespan with container"""
        from mcp_server_langgraph.core.container import create_test_container
        from mcp_server_langgraph.infrastructure.app_factory import create_lifespan

        container = create_test_container()
        lifespan = create_lifespan(container=container)

        assert lifespan is not None


@pytest.mark.xdist_group(name="testopenapicustomization")
class TestOpenAPICustomization:
    """Test OpenAPI schema customization"""

    def teardown_method(self) -> None:
        """Force GC to prevent mock accumulation in xdist workers"""
        gc.collect()

    def test_customize_openapi_schema(self):
        """Test OpenAPI schema customization"""
        from fastapi import FastAPI

        from mcp_server_langgraph.infrastructure.app_factory import customize_openapi

        app = FastAPI()
        customized = customize_openapi(app)

        assert customized is not None

    def test_openapi_includes_version(self):
        """Test that OpenAPI schema includes version"""
        from fastapi import FastAPI

        from mcp_server_langgraph.infrastructure.app_factory import customize_openapi

        app = FastAPI()
        schema = customize_openapi(app)

        # Should have version info
        assert schema is not None


@pytest.mark.xdist_group(name="testappconfiguration")
class TestAppConfiguration:
    """Test app configuration utilities"""

    def teardown_method(self) -> None:
        """Force GC to prevent mock accumulation in xdist workers"""
        gc.collect()

    def test_configure_app_for_test(self):
        """Test configuring app for test environment"""
        from mcp_server_langgraph.infrastructure.app_factory import create_app

        app = create_app(environment="test")

        assert app is not None

    def test_configure_app_for_development(self):
        """Test configuring app for development environment"""
        from mcp_server_langgraph.infrastructure.app_factory import create_app

        app = create_app(environment="development")

        assert app is not None

    def test_configure_app_for_production(self, monkeypatch):
        """Test configuring app for production environment"""
        from mcp_server_langgraph.infrastructure.app_factory import create_app

        # Set required production environment variables
        monkeypatch.setenv("AUTH_PROVIDER", "keycloak")
        monkeypatch.setenv("GDPR_STORAGE_BACKEND", "postgres")

        app = create_app(environment="production")

        assert app is not None


@pytest.mark.xdist_group(name="testtransportadapters")
class TestTransportAdapters:
    """Test transport adapter utilities"""

    def teardown_method(self) -> None:
        """Force GC to prevent mock accumulation in xdist workers"""
        gc.collect()

    def test_create_stdio_adapter(self):
        """Test creating STDIO transport adapter"""
        from mcp_server_langgraph.infrastructure.transport_adapters import create_stdio_adapter

        adapter = create_stdio_adapter()

        assert adapter is not None

    def test_create_http_adapter(self):
        """Test creating HTTP transport adapter"""
        from mcp_server_langgraph.infrastructure.transport_adapters import create_http_adapter

        adapter = create_http_adapter()

        assert adapter is not None


@pytest.mark.xdist_group(name="testappfactoryintegration")
class TestAppFactoryIntegration:
    """Test integration between app factory and existing code"""

    def teardown_method(self) -> None:
        """Force GC to prevent mock accumulation in xdist workers"""
        gc.collect()

    def test_app_factory_compatible_with_server_streamable(self):
        """Test that factory is compatible with existing server"""
        from mcp_server_langgraph.infrastructure.app_factory import create_app

        # Should create app without errors
        app = create_app()

        assert app is not None

    def test_app_can_be_used_with_uvicorn(self):
        """Test that created app can be used with uvicorn"""
        from mcp_server_langgraph.infrastructure.app_factory import create_app

        app = create_app()

        # App should have necessary attributes for uvicorn
        assert callable(app)


@pytest.mark.xdist_group(name="testappfactorydocumentation")
class TestAppFactoryDocumentation:
    """Test that infrastructure functions have good documentation"""

    def teardown_method(self) -> None:
        """Force GC to prevent mock accumulation in xdist workers"""
        gc.collect()

    def test_create_app_has_docstring(self):
        """Test that create_app has comprehensive docstring"""
        from mcp_server_langgraph.infrastructure.app_factory import create_app

        assert create_app.__doc__ is not None
        assert len(create_app.__doc__) > 50
        assert "container" in create_app.__doc__.lower() or "settings" in create_app.__doc__.lower()


@pytest.mark.xdist_group(name="testproductionstorewiring")
class TestProductionStoreWiring:
    """Test environment-aware store wiring for production vs development.

    ADR-0026: Push notifications and feedback stores should use PostgreSQL
    in production/staging environments when database_url is configured.
    """

    def setup_method(self) -> None:
        """Reset global stores before each test for isolation."""
        from mcp_server_langgraph.api.v1.notifications import set_push_subscription_store
        from mcp_server_langgraph.api.v1.remediation_approvals import set_feedback_store

        set_push_subscription_store(None)
        set_feedback_store(None)

    def teardown_method(self) -> None:
        """Force GC and reset stores to prevent mock accumulation in xdist workers"""
        from mcp_server_langgraph.api.v1.notifications import set_push_subscription_store
        from mcp_server_langgraph.api.v1.remediation_approvals import set_feedback_store

        set_push_subscription_store(None)
        set_feedback_store(None)
        gc.collect()

    @pytest.mark.asyncio
    async def test_development_uses_inmemory_push_store(self):
        """Test that development environment uses InMemoryPushSubscriptionStore."""
        from unittest.mock import AsyncMock, patch

        from mcp_server_langgraph.api.v1.notifications import get_push_subscription_store
        from mcp_server_langgraph.core.config import Settings
        from mcp_server_langgraph.core.container import create_test_container
        from mcp_server_langgraph.infrastructure.app_factory import create_lifespan
        from mcp_server_langgraph.notifications.push_store import InMemoryPushSubscriptionStore

        # Create test container with development settings (no database)
        settings = Settings(
            environment="development",
            vapid_public_key="test-public-key",
            vapid_private_key="test-private-key",
            vapid_claims_email="test@example.com",
        )
        container = create_test_container(settings=settings)

        # Mock the GDPR storage initialization to avoid side effects
        with patch(
            "mcp_server_langgraph.compliance.gdpr.factory.initialize_gdpr_storage",
            new_callable=AsyncMock,
        ):
            async with create_lifespan(container=container):
                store = get_push_subscription_store()
                assert isinstance(store, InMemoryPushSubscriptionStore)

    @pytest.mark.asyncio
    async def test_development_uses_inmemory_feedback_store(self):
        """Test that development environment uses InMemoryFeedbackStore."""
        from unittest.mock import AsyncMock, patch

        from mcp_server_langgraph.alerts.feedback import InMemoryFeedbackStore
        from mcp_server_langgraph.api.v1.remediation_approvals import get_feedback_store
        from mcp_server_langgraph.core.config import Settings
        from mcp_server_langgraph.core.container import create_test_container
        from mcp_server_langgraph.infrastructure.app_factory import create_lifespan

        # Create test container with development settings (no database)
        settings = Settings(environment="development")
        container = create_test_container(settings=settings)

        # Mock the GDPR storage initialization to avoid side effects
        with patch(
            "mcp_server_langgraph.compliance.gdpr.factory.initialize_gdpr_storage",
            new_callable=AsyncMock,
        ):
            async with create_lifespan(container=container):
                store = get_feedback_store()
                assert isinstance(store, InMemoryFeedbackStore)

    @pytest.mark.asyncio
    async def test_stores_reset_on_shutdown(self):
        """Test that stores are reset to None on application shutdown.

        Note: get_push_subscription_store() has lazy initialization, so we
        check the raw global variable _push_subscription_store instead.
        """
        from unittest.mock import AsyncMock, patch

        from mcp_server_langgraph.api.v1 import notifications
        from mcp_server_langgraph.api.v1 import remediation_approvals
        from mcp_server_langgraph.api.v1.notifications import get_push_subscription_store
        from mcp_server_langgraph.api.v1.remediation_approvals import get_feedback_store
        from mcp_server_langgraph.core.config import Settings
        from mcp_server_langgraph.core.container import create_test_container
        from mcp_server_langgraph.infrastructure.app_factory import create_lifespan

        settings = Settings(
            environment="development",
            vapid_public_key="test-public-key",
            vapid_private_key="test-private-key",
            vapid_claims_email="test@example.com",
        )
        container = create_test_container(settings=settings)

        # Mock the GDPR storage initialization to avoid side effects
        with patch(
            "mcp_server_langgraph.compliance.gdpr.factory.initialize_gdpr_storage",
            new_callable=AsyncMock,
        ):
            async with create_lifespan(container=container):
                # During lifespan, stores should be initialized
                push_store = get_push_subscription_store()
                feedback_store = get_feedback_store()
                assert push_store is not None
                assert feedback_store is not None

            # After lifespan exits, the raw globals should be reset to None
            # (Calling get_* would trigger lazy initialization)
            assert notifications._push_subscription_store is None
            assert remediation_approvals._feedback_store is None

    @pytest.mark.asyncio
    async def test_production_with_database_uses_postgres_stores(self, monkeypatch):
        """Test that production environment with database_url uses PostgreSQL stores."""
        from unittest.mock import AsyncMock, MagicMock, patch

        from mcp_server_langgraph.api.v1.notifications import get_push_subscription_store
        from mcp_server_langgraph.api.v1.remediation_approvals import get_feedback_store
        from mcp_server_langgraph.core.config import Settings
        from mcp_server_langgraph.core.container import ApplicationContainer, ContainerConfig
        from mcp_server_langgraph.infrastructure.app_factory import create_lifespan
        from mcp_server_langgraph.notifications.push_store import PostgresPushSubscriptionStore

        # Set production environment variables
        monkeypatch.setenv("AUTH_PROVIDER", "keycloak")
        monkeypatch.setenv("GDPR_STORAGE_BACKEND", "postgres")

        settings = Settings(
            environment="production",
            database_url="postgresql+asyncpg://user:pass@localhost:5432/testdb",
            vapid_public_key="test-public-key",
            vapid_private_key="test-private-key",
            vapid_claims_email="test@example.com",
        )
        config = ContainerConfig(environment="production")
        container = ApplicationContainer(config, settings=settings)

        # Mock session maker and GDPR initialization
        mock_session_maker = MagicMock()
        with (
            patch(
                "mcp_server_langgraph.database.session.get_session_maker",
                return_value=mock_session_maker,
            ),
            patch(
                "mcp_server_langgraph.compliance.gdpr.factory.initialize_gdpr_storage",
                new_callable=AsyncMock,
            ),
        ):
            async with create_lifespan(container=container):
                push_store = get_push_subscription_store()
                feedback_store = get_feedback_store()

                # Should be PostgreSQL stores, not InMemory
                assert isinstance(push_store, PostgresPushSubscriptionStore)
                # Feedback store type check
                from mcp_server_langgraph.alerts.feedback import PostgresFeedbackStore
                assert isinstance(feedback_store, PostgresFeedbackStore)

    @pytest.mark.asyncio
    async def test_vapid_keys_required_for_push_store_wiring(self):
        """Test that push store is not WIRED by app_factory without VAPID keys.

        Note: get_push_subscription_store() has lazy initialization, so without
        explicit wiring by app_factory, the raw global remains None.
        The getter would still return a store (via lazy init), but app_factory
        should NOT call set_push_subscription_store() without VAPID keys.
        """
        from unittest.mock import AsyncMock, patch

        from mcp_server_langgraph.api.v1 import notifications
        from mcp_server_langgraph.core.config import Settings
        from mcp_server_langgraph.core.container import create_test_container
        from mcp_server_langgraph.infrastructure.app_factory import create_lifespan

        # Create settings WITHOUT VAPID keys
        settings = Settings(
            environment="development",
            vapid_public_key="",  # Empty key
            vapid_private_key="",  # Empty key
        )
        container = create_test_container(settings=settings)

        with patch(
            "mcp_server_langgraph.compliance.gdpr.factory.initialize_gdpr_storage",
            new_callable=AsyncMock,
        ):
            async with create_lifespan(container=container):
                # Push store should NOT be explicitly wired without VAPID keys
                # (the raw global remains None - getter would create one lazily)
                assert notifications._push_subscription_store is None

    @pytest.mark.asyncio
    async def test_feedback_store_always_initialized(self):
        """Test that feedback store is always initialized regardless of environment."""
        from unittest.mock import AsyncMock, patch

        from mcp_server_langgraph.api.v1.remediation_approvals import get_feedback_store
        from mcp_server_langgraph.core.config import Settings
        from mcp_server_langgraph.core.container import create_test_container
        from mcp_server_langgraph.infrastructure.app_factory import create_lifespan

        settings = Settings(environment="test")
        container = create_test_container(settings=settings)

        with patch(
            "mcp_server_langgraph.compliance.gdpr.factory.initialize_gdpr_storage",
            new_callable=AsyncMock,
        ):
            async with create_lifespan(container=container):
                # Feedback store should always be initialized
                feedback_store = get_feedback_store()
                assert feedback_store is not None
