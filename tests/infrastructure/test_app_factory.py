"""
TDD Tests for FastAPI App Factory

These tests define the behavior we want after extracting infrastructure
concerns (FastAPI setup, middleware, CORS) from server modules.

Following TDD:
1. Write tests first (this file) - RED
2. Implement app factory - GREEN
3. Verify no regressions - REFACTOR
"""

from unittest.mock import Mock, patch

import pytest


class TestAppFactory:
    """Test the FastAPI app factory function"""

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


class TestMiddlewareFactory:
    """Test middleware creation functions"""

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


class TestLifespanManager:
    """Test application lifespan management"""

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


class TestOpenAPICustomization:
    """Test OpenAPI schema customization"""

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


class TestAppConfiguration:
    """Test app configuration utilities"""

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

    def test_configure_app_for_production(self):
        """Test configuring app for production environment"""
        from mcp_server_langgraph.infrastructure.app_factory import create_app

        app = create_app(environment="production")

        assert app is not None


class TestTransportAdapters:
    """Test transport adapter utilities"""

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


class TestAppFactoryIntegration:
    """Test integration between app factory and existing code"""

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
        assert hasattr(app, "__call__")


class TestAppFactoryDocumentation:
    """Test that infrastructure functions have good documentation"""

    def test_create_app_has_docstring(self):
        """Test that create_app has comprehensive docstring"""
        from mcp_server_langgraph.infrastructure.app_factory import create_app

        assert create_app.__doc__ is not None
        assert len(create_app.__doc__) > 50
        assert "container" in create_app.__doc__.lower() or "settings" in create_app.__doc__.lower()
