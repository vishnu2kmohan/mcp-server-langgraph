"""
Tests for FastAPI app factory pattern with settings override.

Verifies that create_app() accepts settings_override parameter,
allowing tests to customize configuration without affecting global state.
"""

import gc

import pytest
from fastapi import FastAPI

from mcp_server_langgraph.core.config import Settings

pytestmark = pytest.mark.unit


@pytest.mark.unit
class TestAppFactoryPattern:
    """Test app factory pattern for test configurability"""

    def teardown_method(self) -> None:
        """Force GC to prevent mock accumulation in xdist workers"""
        gc.collect()

    def test_create_app_with_default_settings(self):
        """
        Test that create_app() works with default settings.

        This is the current behavior - should continue to work.
        Uses skip_startup_validation=True to avoid DB dependency in unit tests.
        """
        from mcp_server_langgraph.app import create_app
        from mcp_server_langgraph.observability.telemetry import shutdown_observability

        try:
            app = create_app(skip_startup_validation=True)
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

            # Should accept settings_override parameter (skip validation for unit tests)
            app = create_app(settings_override=test_settings, skip_startup_validation=True)

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
            app1 = create_app(settings_override=settings1, skip_startup_validation=True)

            # Create second app with different settings (without shutting down first)
            settings2 = Settings(
                environment="test",
                auth_provider="inmemory",
                jwt_secret_key="secret-2",
                gdpr_storage_backend="memory",
                service_name="app-2",
            )
            app2 = create_app(settings_override=settings2, skip_startup_validation=True)

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
            app = create_app(skip_startup_validation=True)

            # Should successfully create app
            assert isinstance(app, FastAPI)

            # Global settings should still exist
            assert global_settings is not None

        finally:
            shutdown_observability()


@pytest.mark.unit
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
            app = create_app(skip_startup_validation=True)
            client = TestClient(app)

            # When: Request health endpoint
            response = client.get("/api/v1/health")

            # Then: Should return 200
            assert response.status_code == 200
            assert "status" in response.json()  # Status varies based on DB availability
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


@pytest.mark.unit
class TestAppStartupSequence:
    """Tests for app.py lifespan startup sequence (v26).

    Verifies canonical startup: sync_mcp_tools() THEN index_all_tools().
    """

    def teardown_method(self) -> None:
        """Force GC to prevent mock accumulation in xdist workers."""
        gc.collect()

    @pytest.mark.asyncio
    async def test_lifespan_calls_sync_mcp_tools(self, monkeypatch):
        """Lifespan calls sync_mcp_tools() during startup."""
        from unittest.mock import AsyncMock, MagicMock, patch

        call_order: list[str] = []

        async def mock_sync_mcp_tools():
            call_order.append("sync_mcp_tools")

        async def mock_index_all_tools():
            call_order.append("index_all_tools")

        # Mock bootstrap_all to return a minimal state
        mock_state = MagicMock()
        mock_state.security = None
        mock_state.http = None
        mock_state.storage = None
        mock_state.websocket = None
        mock_state.context_graph = None
        mock_state.skills = None
        mock_state.cleanup = AsyncMock(return_value=None)

        with (
            patch("mcp_server_langgraph.app.bootstrap_all", return_value=mock_state),
            patch("mcp_server_langgraph.app.run_startup_validation_async", new_callable=AsyncMock),
            patch(
                "mcp_server_langgraph.tools.unified_registry.sync_mcp_tools",
                mock_sync_mcp_tools,
            ),
            patch(
                "mcp_server_langgraph.bootstrap.semantic.index_all_tools",
                mock_index_all_tools,
            ),
        ):
            from mcp_server_langgraph.app import create_app
            from mcp_server_langgraph.observability.telemetry import shutdown_observability

            try:
                app = create_app(skip_startup_validation=True)
                # Trigger lifespan
                async with app.router.lifespan_context(app):
                    pass

                assert "sync_mcp_tools" in call_order
            finally:
                shutdown_observability()

    @pytest.mark.asyncio
    async def test_lifespan_calls_index_all_tools_after_sync_mcp_tools(self, monkeypatch):
        """Lifespan calls index_all_tools() AFTER sync_mcp_tools()."""
        from unittest.mock import AsyncMock, MagicMock, patch

        call_order: list[str] = []

        async def mock_sync_mcp_tools():
            call_order.append("sync_mcp_tools")

        async def mock_index_all_tools():
            call_order.append("index_all_tools")

        mock_state = MagicMock()
        mock_state.security = None
        mock_state.http = None
        mock_state.storage = None
        mock_state.websocket = None
        mock_state.context_graph = None
        mock_state.skills = None
        mock_state.cleanup = AsyncMock(return_value=None)

        with (
            patch("mcp_server_langgraph.app.bootstrap_all", return_value=mock_state),
            patch("mcp_server_langgraph.app.run_startup_validation_async", new_callable=AsyncMock),
            patch(
                "mcp_server_langgraph.tools.unified_registry.sync_mcp_tools",
                mock_sync_mcp_tools,
            ),
            patch(
                "mcp_server_langgraph.bootstrap.semantic.index_all_tools",
                mock_index_all_tools,
            ),
        ):
            from mcp_server_langgraph.app import create_app
            from mcp_server_langgraph.observability.telemetry import shutdown_observability

            try:
                app = create_app(skip_startup_validation=True)
                async with app.router.lifespan_context(app):
                    pass

                # Both should be called
                assert "sync_mcp_tools" in call_order
                assert "index_all_tools" in call_order

                # sync_mcp_tools MUST come before index_all_tools
                assert call_order.index("sync_mcp_tools") < call_order.index("index_all_tools")
            finally:
                shutdown_observability()

    @pytest.mark.asyncio
    async def test_lifespan_handles_mcp_sync_failure_gracefully(self, monkeypatch):
        """Lifespan continues even if MCP sync/index fails."""
        from unittest.mock import AsyncMock, MagicMock, patch

        async def mock_sync_mcp_tools():
            raise RuntimeError("MCP connection failed")

        mock_state = MagicMock()
        mock_state.security = None
        mock_state.http = None
        mock_state.storage = None
        mock_state.websocket = None
        mock_state.context_graph = None
        mock_state.skills = None
        mock_state.cleanup = AsyncMock(return_value=None)

        with (
            patch("mcp_server_langgraph.app.bootstrap_all", return_value=mock_state),
            patch("mcp_server_langgraph.app.run_startup_validation_async", new_callable=AsyncMock),
            patch(
                "mcp_server_langgraph.tools.unified_registry.sync_mcp_tools",
                mock_sync_mcp_tools,
            ),
        ):
            from mcp_server_langgraph.app import create_app
            from mcp_server_langgraph.observability.telemetry import shutdown_observability

            try:
                app = create_app(skip_startup_validation=True)
                # Should NOT raise even though sync failed
                async with app.router.lifespan_context(app):
                    pass
            finally:
                shutdown_observability()
