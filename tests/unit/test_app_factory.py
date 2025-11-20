"""
Tests for FastAPI app factory pattern with settings override.

Verifies that create_app() accepts settings_override parameter,
allowing tests to customize configuration without affecting global state.
"""

import gc

import pytest
from fastapi import FastAPI

from mcp_server_langgraph.core.config import Settings


@pytest.mark.unit
@pytest.mark.xdist_group(name="testappfactorypattern")
class TestAppFactoryPattern:
    """Test app factory pattern for test configurability"""

    def teardown_method(self) -> None:
        """Force GC to prevent mock accumulation in xdist workers"""
        gc.collect()

    def test_create_app_with_default_settings(self):
        """
        Test that create_app() works with default settings.

        This is the current behavior - should continue to work.
        """
        from mcp_server_langgraph.app import create_app
        from mcp_server_langgraph.observability.telemetry import shutdown_observability

        try:
            app = create_app()
            assert isinstance(app, FastAPI)
            assert app.title == "MCP Server LangGraph API"
        finally:
            shutdown_observability()

    def test_create_app_with_settings_override(self):
        """
        Test that create_app() accepts settings_override parameter.

        This is the new feature - tests can provide custom settings.
        """
        from mcp_server_langgraph.app import create_app
        from mcp_server_langgraph.observability.telemetry import shutdown_observability

        try:
            # Create custom test settings
            test_settings = Settings(
                environment="test",
                auth_provider="inmemory",
                jwt_secret_key="test-override-secret-key",
                gdpr_storage_backend="memory",
                service_name="test-service-override",
            )

            # Should accept settings_override parameter
            app = create_app(settings_override=test_settings)

            assert isinstance(app, FastAPI)
            # Verify the app was created with override settings
            # (we can't directly check settings inside app, but creation should succeed)
        finally:
            shutdown_observability()

    def test_multiple_app_instances_with_different_settings(self):
        """
        Test that multiple app instances can be created with different settings.

        This ensures no global state pollution between instances.
        """
        from mcp_server_langgraph.app import create_app
        from mcp_server_langgraph.observability.telemetry import shutdown_observability

        try:
            # Create first app with test settings
            settings1 = Settings(
                environment="test",
                auth_provider="inmemory",
                jwt_secret_key="secret-1",
                gdpr_storage_backend="memory",
                service_name="app-1",
            )
            app1 = create_app(settings_override=settings1)

            # Shutdown first app's observability
            shutdown_observability()

            # Create second app with different settings
            settings2 = Settings(
                environment="test",
                auth_provider="inmemory",
                jwt_secret_key="secret-2",
                gdpr_storage_backend="memory",
                service_name="app-2",
            )
            app2 = create_app(settings_override=settings2)

            # Both should be valid FastAPI instances
            assert isinstance(app1, FastAPI)
            assert isinstance(app2, FastAPI)

            # They should be different instances
            assert app1 is not app2

        finally:
            shutdown_observability()

    def test_create_app_without_override_uses_global_settings(self):
        """
        Test that create_app() without override uses global settings.

        Backward compatibility - existing usage should work unchanged.
        """
        from mcp_server_langgraph.app import create_app
        from mcp_server_langgraph.core.config import settings as global_settings
        from mcp_server_langgraph.observability.telemetry import shutdown_observability

        try:
            app = create_app()

            # Should successfully create app
            assert isinstance(app, FastAPI)

            # Global settings should still exist
            assert global_settings is not None

        finally:
            shutdown_observability()


@pytest.mark.unit
@pytest.mark.xdist_group(name="testappfactorybackwardcompatibility")
class TestAppFactoryBackwardCompatibility:
    """Test backward compatibility with existing deployment patterns"""

    def teardown_method(self) -> None:
        """Force GC to prevent mock accumulation in xdist workers"""
        gc.collect()

    def test_module_level_app_variable_exists(self):
        """
        Test that module-level 'app' variable exists for uvicorn.

        Deployment scripts use: uvicorn mcp_server_langgraph.app:app
        This must continue to work.
        """
        from mcp_server_langgraph.app import app

        # Module-level app should exist
        assert app is not None
        assert isinstance(app, FastAPI)


@pytest.mark.xdist_group(name="app_factory_router_tests")
class TestAppFactoryRouterMounting:
    """
    P1: Test router mounting order and registration
    """

    def teardown_method(self):
        """Force GC to prevent mock accumulation in xdist workers"""
        gc.collect()

    def test_health_router_mounted(self):
        """
        Test that health router is mounted and accessible
        """
        from fastapi.testclient import TestClient

        from mcp_server_langgraph.app import create_app
        from mcp_server_langgraph.observability.telemetry import shutdown_observability

        try:
            # Given: App
            app = create_app()
            client = TestClient(app)

            # When: Request health endpoint
            response = client.get("/health")

            # Then: Should return 200
            assert response.status_code == 200
            assert response.json()["status"] == "healthy"
        finally:
            shutdown_observability()

    def test_uvicorn_can_import_app(self):
        """
        Test that uvicorn can import the app variable.

        Simulates: uvicorn mcp_server_langgraph.app:app
        """
        import importlib

        # This is how uvicorn imports the app
        module = importlib.import_module("mcp_server_langgraph.app")
        app = module.app

        assert app is not None
        assert isinstance(app, FastAPI)


@pytest.mark.xdist_group(name="app_factory_router_tests")
class TestAppFactoryRouterMounting:
    """
    P1: Test router mounting order and registration
    """

    def teardown_method(self):
        """Force GC to prevent mock accumulation in xdist workers"""
        gc.collect()

    def test_health_router_mounted(self):
        """
        Test that health router is mounted and accessible
        """
        from fastapi.testclient import TestClient

        from mcp_server_langgraph.app import create_app
        from mcp_server_langgraph.observability.telemetry import shutdown_observability

        try:
            # Given: App
            app = create_app()
            client = TestClient(app)

            # When: Request health endpoint
            response = client.get("/health")

            # Then: Should return 200
            assert response.status_code == 200
            assert response.json()["status"] == "healthy"
        finally:
            shutdown_observability()
