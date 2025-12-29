"""
WebSocket Bootstrap Tests

TDD RED Phase: Tests for StreamingSettings wiring to MCPWebSocketLifecycleManager.
"""

from __future__ import annotations

import gc

import pytest
from unittest.mock import patch


pytestmark = [
    pytest.mark.unit,
    pytest.mark.websocket,
]


@pytest.mark.xdist_group(name="test_websocket_bootstrap")
class TestWebSocketBootstrapImports:
    """Test websocket bootstrap module imports."""

    def teardown_method(self) -> None:
        """Force GC to prevent mock accumulation in xdist workers."""
        gc.collect()

    def test_import_websocket_bootstrap(self) -> None:
        """WebSocket bootstrap should be importable."""
        from mcp_server_langgraph.bootstrap import websocket

        assert websocket is not None
        assert hasattr(websocket, "init_websocket_lifecycle")

    def test_websocket_state_class_exists(self) -> None:
        """WebSocketState should exist."""
        from mcp_server_langgraph.bootstrap.websocket import WebSocketState

        assert WebSocketState is not None


@pytest.mark.xdist_group(name="test_websocket_bootstrap")
class TestInitWebSocketLifecycleWithSettings:
    """Tests for init_websocket_lifecycle with StreamingSettings."""

    def teardown_method(self) -> None:
        """Force GC to prevent mock accumulation in xdist workers."""
        gc.collect()

    @pytest.mark.asyncio
    async def test_init_websocket_lifecycle_accepts_settings(self) -> None:
        """
        GIVEN StreamingSettings
        WHEN init_websocket_lifecycle is called with settings
        THEN should not raise and return WebSocketState.
        """
        from mcp_server_langgraph.bootstrap.websocket import init_websocket_lifecycle
        from mcp_server_langgraph.core.config.streaming import StreamingSettings

        settings = StreamingSettings()

        # Reset singleton for test isolation
        with patch(
            "mcp_server_langgraph.mcp.websocket.lifecycle._lifecycle_manager",
            None,
        ):
            state = await init_websocket_lifecycle(streaming_settings=settings)

        assert state is not None
        assert state.mcp_lifecycle_manager is not None

        # Cleanup
        await state.cleanup()

    @pytest.mark.asyncio
    async def test_lifecycle_manager_uses_config_cleanup_interval(self) -> None:
        """
        GIVEN StreamingSettings with custom cleanup interval
        WHEN lifecycle manager is initialized
        THEN should use the configured cleanup_interval.
        """
        from mcp_server_langgraph.bootstrap.websocket import init_websocket_lifecycle
        from mcp_server_langgraph.core.config.streaming import StreamingSettings

        settings = StreamingSettings(
            streaming_idle_cleanup_interval=120,  # 2 minutes instead of default 60
        )

        with patch(
            "mcp_server_langgraph.mcp.websocket.lifecycle._lifecycle_manager",
            None,
        ):
            state = await init_websocket_lifecycle(streaming_settings=settings)

        assert state.mcp_lifecycle_manager is not None
        assert state.mcp_lifecycle_manager.cleanup_interval == 120

        # Cleanup
        await state.cleanup()

    @pytest.mark.asyncio
    async def test_lifecycle_manager_uses_config_metrics_cleanup_interval(self) -> None:
        """
        GIVEN StreamingSettings with custom metrics cleanup interval
        WHEN lifecycle manager is initialized
        THEN should use the configured metrics_cleanup_interval.
        """
        from mcp_server_langgraph.bootstrap.websocket import init_websocket_lifecycle
        from mcp_server_langgraph.core.config.streaming import StreamingSettings

        settings = StreamingSettings(
            streaming_metrics_cleanup_interval=600,  # 10 minutes instead of default 300
        )

        with patch(
            "mcp_server_langgraph.mcp.websocket.lifecycle._lifecycle_manager",
            None,
        ):
            state = await init_websocket_lifecycle(streaming_settings=settings)

        assert state.mcp_lifecycle_manager is not None
        assert state.mcp_lifecycle_manager.metrics_cleanup_interval == 600

        # Cleanup
        await state.cleanup()

    @pytest.mark.asyncio
    async def test_init_websocket_lifecycle_without_settings_uses_defaults(self) -> None:
        """
        GIVEN no streaming settings passed
        WHEN init_websocket_lifecycle is called
        THEN should use default intervals (backward compatible).
        """
        from mcp_server_langgraph.bootstrap.websocket import init_websocket_lifecycle

        with patch(
            "mcp_server_langgraph.mcp.websocket.lifecycle._lifecycle_manager",
            None,
        ):
            state = await init_websocket_lifecycle()

        assert state.mcp_lifecycle_manager is not None
        # Default values
        assert state.mcp_lifecycle_manager.cleanup_interval == 60
        assert state.mcp_lifecycle_manager.metrics_cleanup_interval == 300

        # Cleanup
        await state.cleanup()


@pytest.mark.xdist_group(name="test_websocket_bootstrap")
class TestLifecycleManagerFactoryWithConfig:
    """Tests for lifecycle manager factory accepting config."""

    def teardown_method(self) -> None:
        """Force GC to prevent mock accumulation in xdist workers."""
        gc.collect()

    def test_create_lifecycle_manager_with_settings(self) -> None:
        """
        GIVEN StreamingSettings
        WHEN creating lifecycle manager with settings
        THEN should use configured intervals.
        """
        from mcp_server_langgraph.api.v1.mcp_websocket import MCPWebSocketLifecycleManager
        from mcp_server_langgraph.core.config.streaming import StreamingSettings

        settings = StreamingSettings(
            streaming_idle_cleanup_interval=90,
            streaming_metrics_cleanup_interval=450,
        )

        manager = MCPWebSocketLifecycleManager(
            cleanup_interval=settings.streaming_idle_cleanup_interval,
            metrics_cleanup_interval=settings.streaming_metrics_cleanup_interval,
        )

        assert manager.cleanup_interval == 90
        assert manager.metrics_cleanup_interval == 450

    def test_create_mcp_lifecycle_manager_factory_accepts_settings(self) -> None:
        """
        GIVEN the module
        WHEN importing
        THEN should have create_mcp_lifecycle_manager function that accepts settings.
        """
        from mcp_server_langgraph.api.v1.mcp_websocket import (
            create_mcp_lifecycle_manager,
        )

        assert create_mcp_lifecycle_manager is not None
        assert callable(create_mcp_lifecycle_manager)

    def test_create_mcp_lifecycle_manager_with_streaming_settings(self) -> None:
        """
        GIVEN StreamingSettings
        WHEN create_mcp_lifecycle_manager is called
        THEN should return manager with configured intervals.
        """
        from mcp_server_langgraph.api.v1.mcp_websocket import create_mcp_lifecycle_manager
        from mcp_server_langgraph.core.config.streaming import StreamingSettings

        settings = StreamingSettings(
            streaming_idle_cleanup_interval=75,
            streaming_metrics_cleanup_interval=500,
        )

        manager = create_mcp_lifecycle_manager(streaming_settings=settings)

        assert manager.cleanup_interval == 75
        assert manager.metrics_cleanup_interval == 500


@pytest.mark.xdist_group(name="test_websocket_bootstrap")
class TestAppLifespanUsesStreamingSettings:
    """Tests for verifying app lifespan passes streaming settings."""

    def teardown_method(self) -> None:
        """Force GC to prevent mock accumulation in xdist workers."""
        gc.collect()

    def test_settings_has_streaming_properties(self) -> None:
        """
        GIVEN the main Settings class
        WHEN checking attributes
        THEN should have streaming configuration properties.
        """
        from mcp_server_langgraph.core.config import Settings

        settings = Settings()

        assert hasattr(settings, "streaming_idle_cleanup_interval")
        assert hasattr(settings, "streaming_metrics_cleanup_interval")
        assert hasattr(settings, "streaming_enabled")

    @pytest.mark.asyncio
    async def test_bootstrap_websocket_uses_main_settings(self) -> None:
        """
        GIVEN main Settings with streaming config
        WHEN init_websocket_lifecycle is called with settings
        THEN lifecycle manager should use those values.
        """
        from mcp_server_langgraph.bootstrap.websocket import init_websocket_lifecycle
        from mcp_server_langgraph.core.config.streaming import StreamingSettings

        # Create settings with custom values
        settings = StreamingSettings(
            streaming_idle_cleanup_interval=45,
            streaming_metrics_cleanup_interval=900,
        )

        with patch(
            "mcp_server_langgraph.mcp.websocket.lifecycle._lifecycle_manager",
            None,
        ):
            state = await init_websocket_lifecycle(streaming_settings=settings)

        assert state.mcp_lifecycle_manager.cleanup_interval == 45
        assert state.mcp_lifecycle_manager.metrics_cleanup_interval == 900

        await state.cleanup()
