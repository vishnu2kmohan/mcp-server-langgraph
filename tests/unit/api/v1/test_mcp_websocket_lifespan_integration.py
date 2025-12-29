"""
MCP WebSocket Lifespan Integration Tests

Tests for verifying that MCP WebSocket lifecycle management is properly
integrated with the FastAPI application lifespan.

TDD RED Phase: These tests define the expected behavior for lifespan wiring.
"""

from __future__ import annotations

import asyncio
import gc
from unittest.mock import AsyncMock, patch

import pytest

pytestmark = [
    pytest.mark.unit,
    pytest.mark.api,
    pytest.mark.websocket,
]


@pytest.mark.xdist_group(name="test_mcp_websocket_lifespan_integration")
class TestMCPWebSocketLifespanIntegration:
    """Tests for MCP WebSocket lifespan integration with FastAPI app."""

    def teardown_method(self) -> None:
        """Force GC to prevent mock accumulation in xdist workers."""
        gc.collect()

    def test_mcp_websocket_lifecycle_manager_exists(self) -> None:
        """
        GIVEN the MCP WebSocket module
        WHEN importing
        THEN should have MCPWebSocketLifecycleManager class.
        """
        from mcp_server_langgraph.api.v1.mcp_websocket import MCPWebSocketLifecycleManager

        assert MCPWebSocketLifecycleManager is not None

    def test_lifecycle_manager_has_startup_method(self) -> None:
        """
        GIVEN an MCPWebSocketLifecycleManager instance
        WHEN checking methods
        THEN should have async startup method.
        """
        from mcp_server_langgraph.api.v1.mcp_websocket import MCPWebSocketLifecycleManager

        manager = MCPWebSocketLifecycleManager()
        assert hasattr(manager, "startup")
        assert asyncio.iscoroutinefunction(manager.startup)

    def test_lifecycle_manager_has_shutdown_method(self) -> None:
        """
        GIVEN an MCPWebSocketLifecycleManager instance
        WHEN checking methods
        THEN should have async shutdown method.
        """
        from mcp_server_langgraph.api.v1.mcp_websocket import MCPWebSocketLifecycleManager

        manager = MCPWebSocketLifecycleManager()
        assert hasattr(manager, "shutdown")
        assert asyncio.iscoroutinefunction(manager.shutdown)

    @pytest.mark.asyncio
    async def test_lifecycle_manager_startup_starts_cleanup_task(self) -> None:
        """
        GIVEN an MCPWebSocketLifecycleManager
        WHEN startup is called
        THEN should start the idle cleanup background task.
        """
        from mcp_server_langgraph.api.v1.mcp_websocket import MCPWebSocketLifecycleManager

        manager = MCPWebSocketLifecycleManager()

        await manager.startup()

        assert manager.cleanup_task is not None
        assert not manager.cleanup_task.done()

        # Cleanup
        await manager.shutdown()

    @pytest.mark.asyncio
    async def test_lifecycle_manager_shutdown_cancels_cleanup_task(self) -> None:
        """
        GIVEN an MCPWebSocketLifecycleManager with running cleanup task
        WHEN shutdown is called
        THEN should cancel the cleanup task.
        """
        from mcp_server_langgraph.api.v1.mcp_websocket import MCPWebSocketLifecycleManager

        manager = MCPWebSocketLifecycleManager()

        await manager.startup()
        cleanup_task = manager.cleanup_task

        await manager.shutdown()

        assert cleanup_task.cancelled() or cleanup_task.done()

    @pytest.mark.asyncio
    async def test_lifecycle_manager_shutdown_calls_graceful_shutdown(self) -> None:
        """
        GIVEN an MCPWebSocketLifecycleManager
        WHEN shutdown is called
        THEN should call graceful_shutdown for all connections.
        """
        from mcp_server_langgraph.api.v1.mcp_websocket import MCPWebSocketLifecycleManager

        manager = MCPWebSocketLifecycleManager()

        with patch(
            "mcp_server_langgraph.mcp.websocket.lifecycle.graceful_shutdown",
            new_callable=AsyncMock,
        ) as mock_graceful_shutdown:
            await manager.startup()
            await manager.shutdown()

            mock_graceful_shutdown.assert_called_once()


@pytest.mark.xdist_group(name="test_mcp_websocket_lifespan_integration")
class TestMCPWebSocketAppStateIntegration:
    """Tests for MCP WebSocket integration with app.state."""

    def teardown_method(self) -> None:
        """Force GC to prevent mock accumulation in xdist workers."""
        gc.collect()

    def test_get_mcp_lifecycle_manager_exists(self) -> None:
        """
        GIVEN the MCP WebSocket module
        WHEN importing
        THEN should have get_mcp_lifecycle_manager function.
        """
        from mcp_server_langgraph.api.v1.mcp_websocket import get_mcp_lifecycle_manager

        assert callable(get_mcp_lifecycle_manager)

    def test_get_mcp_lifecycle_manager_returns_singleton(self) -> None:
        """
        GIVEN multiple calls to get_mcp_lifecycle_manager
        WHEN getting the manager
        THEN should return the same instance (singleton).
        """
        from mcp_server_langgraph.api.v1.mcp_websocket import get_mcp_lifecycle_manager

        manager1 = get_mcp_lifecycle_manager()
        manager2 = get_mcp_lifecycle_manager()

        assert manager1 is manager2

    @pytest.mark.asyncio
    async def test_lifespan_stores_websocket_lifecycle_in_app_state(self) -> None:
        """
        GIVEN the FastAPI app with lifespan handler
        WHEN the app starts up
        THEN should store websocket_lifecycle in app.state.
        """
        from starlette.testclient import TestClient
        from mcp_server_langgraph.app import create_app
        from mcp_server_langgraph.core.config import Settings

        # Create app with test settings
        test_settings = Settings()
        app = create_app(settings_override=test_settings, skip_startup_validation=True)

        # Use TestClient which handles lifespan properly
        with TestClient(app, raise_server_exceptions=False) as client:
            # Make a request to trigger lifespan
            client.get("/health/ready")
            # app.state should have websocket_lifecycle after startup
            assert hasattr(app.state, "websocket_lifecycle")

    @pytest.mark.asyncio
    async def test_websocket_lifecycle_in_app_state_is_lifecycle_manager(self) -> None:
        """
        GIVEN the FastAPI app after startup
        WHEN checking app.state.websocket_lifecycle
        THEN should be an MCPWebSocketLifecycleManager instance or None.
        """
        from starlette.testclient import TestClient
        from mcp_server_langgraph.api.v1.mcp_websocket import MCPWebSocketLifecycleManager
        from mcp_server_langgraph.app import create_app
        from mcp_server_langgraph.core.config import Settings

        test_settings = Settings()
        app = create_app(settings_override=test_settings, skip_startup_validation=True)

        with TestClient(app, raise_server_exceptions=False) as client:
            # Make a request to trigger lifespan
            client.get("/health/ready")
            lifecycle = app.state.websocket_lifecycle
            # Should be either None or MCPWebSocketLifecycleManager
            assert lifecycle is None or isinstance(lifecycle, MCPWebSocketLifecycleManager)


@pytest.mark.xdist_group(name="test_mcp_websocket_lifespan_integration")
class TestMCPWebSocketBootstrapIntegration:
    """Tests for MCP WebSocket integration with bootstrap module."""

    def teardown_method(self) -> None:
        """Force GC to prevent mock accumulation in xdist workers."""
        gc.collect()

    @pytest.mark.asyncio
    async def test_bootstrap_starts_mcp_websocket_lifecycle(self) -> None:
        """
        GIVEN the bootstrap module
        WHEN bootstrap_all is called
        THEN should start MCP WebSocket lifecycle manager.

        NOTE: This test verifies the integration point exists.
        The actual wiring is in the bootstrap module.
        """
        from mcp_server_langgraph.api.v1.mcp_websocket import get_mcp_lifecycle_manager

        # The lifecycle manager should be accessible
        manager = get_mcp_lifecycle_manager()
        assert manager is not None


@pytest.mark.xdist_group(name="test_mcp_websocket_lifespan_integration")
class TestMCPWebSocketCleanupTaskBehavior:
    """Tests for cleanup task behavior during lifecycle."""

    def teardown_method(self) -> None:
        """Force GC to prevent mock accumulation in xdist workers."""
        gc.collect()

    @pytest.mark.asyncio
    async def test_cleanup_task_runs_periodically(self) -> None:
        """
        GIVEN an MCPWebSocketLifecycleManager with short cleanup interval
        WHEN running for a short period
        THEN cleanup task should execute at least once.
        """
        from mcp_server_langgraph.api.v1.mcp_websocket import MCPWebSocketLifecycleManager

        # Create manager with short interval for testing
        manager = MCPWebSocketLifecycleManager(cleanup_interval=0.1)

        with patch(
            "mcp_server_langgraph.mcp.websocket.lifecycle.cleanup_idle_connections",
            new_callable=AsyncMock,
            return_value=0,
        ) as mock_cleanup:
            await manager.startup()

            # Wait for at least one cleanup cycle
            await asyncio.sleep(0.15)

            await manager.shutdown()

            # Should have been called at least once
            assert mock_cleanup.call_count >= 1

    @pytest.mark.asyncio
    async def test_shutdown_is_idempotent(self) -> None:
        """
        GIVEN an MCPWebSocketLifecycleManager
        WHEN shutdown is called multiple times
        THEN should handle gracefully without errors.
        """
        from mcp_server_langgraph.api.v1.mcp_websocket import MCPWebSocketLifecycleManager

        manager = MCPWebSocketLifecycleManager()

        await manager.startup()

        # Should not raise on multiple shutdowns
        await manager.shutdown()
        await manager.shutdown()
        await manager.shutdown()

    @pytest.mark.asyncio
    async def test_startup_is_idempotent(self) -> None:
        """
        GIVEN an MCPWebSocketLifecycleManager already started
        WHEN startup is called again
        THEN should not create duplicate tasks.
        """
        from mcp_server_langgraph.api.v1.mcp_websocket import MCPWebSocketLifecycleManager

        manager = MCPWebSocketLifecycleManager()

        await manager.startup()
        first_task = manager.cleanup_task

        await manager.startup()
        second_task = manager.cleanup_task

        # Should be the same task (no duplicate)
        assert first_task is second_task

        await manager.shutdown()


@pytest.mark.xdist_group(name="test_mcp_websocket_lifespan_integration")
class TestMCPWebSocketMetricsCleanupTask:
    """Tests for stream metrics cleanup task scheduling."""

    def teardown_method(self) -> None:
        """Force GC to prevent mock accumulation in xdist workers."""
        gc.collect()

    def test_lifecycle_manager_has_metrics_cleanup_task_attribute(self) -> None:
        """
        GIVEN an MCPWebSocketLifecycleManager
        WHEN checking attributes
        THEN should have metrics_cleanup_task attribute.
        """
        from mcp_server_langgraph.api.v1.mcp_websocket import MCPWebSocketLifecycleManager

        manager = MCPWebSocketLifecycleManager()
        assert hasattr(manager, "metrics_cleanup_task")

    def test_lifecycle_manager_has_metrics_cleanup_interval(self) -> None:
        """
        GIVEN an MCPWebSocketLifecycleManager
        WHEN checking attributes
        THEN should have metrics_cleanup_interval attribute (default 300 seconds).
        """
        from mcp_server_langgraph.api.v1.mcp_websocket import MCPWebSocketLifecycleManager

        manager = MCPWebSocketLifecycleManager()
        assert hasattr(manager, "metrics_cleanup_interval")
        assert manager.metrics_cleanup_interval == 300  # 5 minutes default

    @pytest.mark.asyncio
    async def test_startup_starts_metrics_cleanup_task(self) -> None:
        """
        GIVEN an MCPWebSocketLifecycleManager
        WHEN startup is called
        THEN should start metrics cleanup background task.
        """
        from mcp_server_langgraph.api.v1.mcp_websocket import MCPWebSocketLifecycleManager

        manager = MCPWebSocketLifecycleManager()

        await manager.startup()

        assert manager.metrics_cleanup_task is not None
        assert not manager.metrics_cleanup_task.done()

        await manager.shutdown()

    @pytest.mark.asyncio
    async def test_metrics_cleanup_task_runs_periodically(self) -> None:
        """
        GIVEN an MCPWebSocketLifecycleManager with short cleanup interval
        WHEN running for a short period
        THEN metrics cleanup should execute at least once.
        """
        from mcp_server_langgraph.api.v1.mcp_websocket import MCPWebSocketLifecycleManager

        # Create manager with short interval for testing
        manager = MCPWebSocketLifecycleManager(
            cleanup_interval=0.5,
            metrics_cleanup_interval=0.1,
        )

        cleanup_calls = []
        original_cleanup = manager.cleanup_stream_metrics

        async def track_cleanup(*args, **kwargs):
            cleanup_calls.append(1)
            return await original_cleanup(*args, **kwargs)

        with patch.object(manager, "cleanup_stream_metrics", side_effect=track_cleanup):
            await manager.startup()

            # Wait for at least one cleanup cycle
            await asyncio.sleep(0.15)

            await manager.shutdown()

        # Should have been called at least once
        assert len(cleanup_calls) >= 1

    @pytest.mark.asyncio
    async def test_shutdown_cancels_metrics_cleanup_task(self) -> None:
        """
        GIVEN an MCPWebSocketLifecycleManager with running metrics cleanup
        WHEN shutdown is called
        THEN should cancel the metrics cleanup task.
        """
        from mcp_server_langgraph.api.v1.mcp_websocket import MCPWebSocketLifecycleManager

        manager = MCPWebSocketLifecycleManager()

        await manager.startup()
        metrics_task = manager.metrics_cleanup_task

        await manager.shutdown()

        assert metrics_task.cancelled() or metrics_task.done()

    @pytest.mark.asyncio
    async def test_shutdown_calls_cleanup_stream_metrics(self) -> None:
        """
        GIVEN an MCPWebSocketLifecycleManager
        WHEN shutdown is called
        THEN should call cleanup_stream_metrics to clear old metrics.
        """
        from mcp_server_langgraph.api.v1.mcp_websocket import MCPWebSocketLifecycleManager

        manager = MCPWebSocketLifecycleManager()

        cleanup_called = False
        original_cleanup = manager.cleanup_stream_metrics

        async def track_cleanup(*args, **kwargs):
            nonlocal cleanup_called
            cleanup_called = True
            return await original_cleanup(*args, **kwargs)

        with patch.object(manager, "cleanup_stream_metrics", side_effect=track_cleanup):
            await manager.startup()
            await manager.shutdown()

        assert cleanup_called, "cleanup_stream_metrics should be called during shutdown"

    @pytest.mark.asyncio
    async def test_shutdown_cleanup_uses_zero_max_age(self) -> None:
        """
        GIVEN an MCPWebSocketLifecycleManager
        WHEN shutdown is called
        THEN should cleanup all completed streams (max_age_seconds=0).
        """
        from mcp_server_langgraph.api.v1.mcp_websocket import (
            MCPWebSocketLifecycleManager,
            streaming_metrics_collector,
        )

        manager = MCPWebSocketLifecycleManager()

        # Add a completed stream
        test_stream_id = "shutdown-cleanup-test"
        streaming_metrics_collector.record_stream_start(test_stream_id)
        streaming_metrics_collector.record_stream_end(test_stream_id)

        await manager.startup()
        await manager.shutdown()

        # The completed stream should have been cleaned up
        stats = streaming_metrics_collector.get_stream_stats(test_stream_id)
        # If cleaned up, chunk_count should be 0 (default for missing stream)
        # Note: This tests the expected behavior - cleanup with max_age=0
        assert stats["chunk_count"] == 0, "Completed stream should be cleaned up on shutdown"
