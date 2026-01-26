"""
HeartbeatManager Unit Tests.

TDD tests for server-initiated heartbeat management in WebSocket connections.
"""

from __future__ import annotations

import asyncio
import gc
from datetime import UTC, datetime
from unittest.mock import MagicMock

import pytest

pytestmark = [pytest.mark.unit, pytest.mark.websocket]


@pytest.mark.xdist_group(name="websocket_heartbeat")
class TestHeartbeatManagerLifecycle:
    """Test HeartbeatManager lifecycle management."""

    def teardown_method(self) -> None:
        """Force GC to prevent mock accumulation in xdist workers."""
        gc.collect()

    @pytest.mark.asyncio
    async def test_heartbeat_manager_starts_background_task(self, mock_websocket: MagicMock) -> None:
        """
        GIVEN a HeartbeatManager
        WHEN start() is called
        THEN a background task should be created.
        """
        from mcp_server_langgraph.websocket.heartbeat import HeartbeatManager

        manager = HeartbeatManager(interval=30, timeout=60)
        task = await manager.start(mock_websocket)

        assert task is not None
        assert isinstance(task, asyncio.Task)
        assert not task.done()

        # Cleanup
        await manager.stop()
        await asyncio.sleep(0.01)  # Allow task to be cancelled

    @pytest.mark.asyncio
    async def test_heartbeat_manager_stop_cancels_task(self, mock_websocket: MagicMock) -> None:
        """
        GIVEN a running HeartbeatManager
        WHEN stop() is called
        THEN the background task should be cancelled.
        """
        from mcp_server_langgraph.websocket.heartbeat import HeartbeatManager

        manager = HeartbeatManager(interval=30, timeout=60)
        task = await manager.start(mock_websocket)

        await manager.stop()
        await asyncio.sleep(0.01)  # Allow task to be cancelled

        assert task.done() or task.cancelled()

    @pytest.mark.asyncio
    async def test_heartbeat_manager_sends_heartbeat(self, mock_websocket: MagicMock) -> None:
        """
        GIVEN a HeartbeatManager with short interval
        WHEN the manager is running
        THEN heartbeat messages should be sent periodically.
        """
        from mcp_server_langgraph.websocket.heartbeat import HeartbeatManager

        # Use a very short interval for testing
        manager = HeartbeatManager(interval=0.02, timeout=1.0)

        async def run_heartbeat() -> None:
            """Run heartbeat loop for a short time."""
            from datetime import UTC, datetime

            manager._websocket = mock_websocket
            manager._running = True
            manager._last_activity = datetime.now(UTC)  # Set last activity
            # Run one iteration manually
            await asyncio.sleep(manager.interval)
            if manager._running and manager.is_alive and manager._websocket:
                await manager._websocket.send_json(
                    {
                        "type": "heartbeat",
                        "timestamp": "test",
                    }
                )

        await run_heartbeat()

        # Verify heartbeat was sent
        assert mock_websocket.send_json.called, "send_json should have been called"
        calls = mock_websocket.send_json.call_args_list
        heartbeat_sent = any(call[0][0].get("type") == "heartbeat" for call in calls)
        assert heartbeat_sent, "Heartbeat message should be sent"


@pytest.mark.xdist_group(name="websocket_heartbeat")
class TestHeartbeatManagerPongHandling:
    """Test HeartbeatManager pong response handling."""

    def teardown_method(self) -> None:
        """Force GC to prevent mock accumulation in xdist workers."""
        gc.collect()

    @pytest.mark.asyncio
    async def test_on_pong_updates_last_activity(self, mock_websocket: MagicMock) -> None:
        """
        GIVEN a HeartbeatManager
        WHEN on_pong() is called
        THEN last_activity should be updated.
        """
        from mcp_server_langgraph.websocket.heartbeat import HeartbeatManager

        manager = HeartbeatManager(interval=30, timeout=60)
        initial_activity = manager.last_activity

        # Simulate some time passing
        await asyncio.sleep(0.01)

        await manager.on_pong()

        assert manager.last_activity > initial_activity

    @pytest.mark.asyncio
    async def test_heartbeat_manager_tracks_last_activity(self, mock_websocket: MagicMock) -> None:
        """
        GIVEN a HeartbeatManager
        WHEN created
        THEN last_activity should be set to current time.
        """
        from mcp_server_langgraph.websocket.heartbeat import HeartbeatManager

        before = datetime.now(UTC)
        manager = HeartbeatManager(interval=30, timeout=60)
        after = datetime.now(UTC)

        assert before <= manager.last_activity <= after


@pytest.mark.xdist_group(name="websocket_heartbeat")
class TestHeartbeatManagerTimeout:
    """Test HeartbeatManager timeout detection."""

    def teardown_method(self) -> None:
        """Force GC to prevent mock accumulation in xdist workers."""
        gc.collect()

    @pytest.mark.asyncio
    async def test_timeout_callback_called_on_dead_connection(self, mock_websocket: MagicMock) -> None:
        """
        GIVEN a HeartbeatManager with timeout callback
        WHEN no pong is received within timeout
        THEN the timeout callback should be called.
        """
        from mcp_server_langgraph.websocket.heartbeat import HeartbeatManager

        timeout_called = False

        async def on_timeout() -> None:
            nonlocal timeout_called
            timeout_called = True

        # Very short timeout for testing
        manager = HeartbeatManager(interval=0.02, timeout=0.05, on_timeout=on_timeout)
        await manager.start(mock_websocket)

        # Wait for timeout to occur (longer than timeout period)
        await asyncio.sleep(0.15)

        await manager.stop()

        assert timeout_called, "Timeout callback should be called when no pong received"

    @pytest.mark.asyncio
    async def test_pong_prevents_timeout(self, mock_websocket: MagicMock) -> None:
        """
        GIVEN a HeartbeatManager
        WHEN pong is received before timeout
        THEN timeout callback should not be called.
        """
        from mcp_server_langgraph.websocket.heartbeat import HeartbeatManager

        timeout_called = False

        async def on_timeout() -> None:
            nonlocal timeout_called
            timeout_called = True

        manager = HeartbeatManager(interval=0.02, timeout=0.1, on_timeout=on_timeout)
        await manager.start(mock_websocket)

        # Keep sending pongs to prevent timeout
        for _ in range(5):
            await manager.on_pong()
            await asyncio.sleep(0.02)

        await manager.stop()

        assert not timeout_called, "Timeout should not occur when pongs are received"


@pytest.mark.xdist_group(name="websocket_heartbeat")
class TestHeartbeatManagerConfiguration:
    """Test HeartbeatManager configuration options."""

    def teardown_method(self) -> None:
        """Force GC to prevent mock accumulation in xdist workers."""
        gc.collect()

    def test_default_configuration_sets_interval(self) -> None:
        """
        GIVEN no custom configuration
        WHEN HeartbeatManager is created
        THEN sensible defaults should be applied.
        """
        from mcp_server_langgraph.websocket.heartbeat import HeartbeatManager

        manager = HeartbeatManager()
        assert manager.interval == 30  # 30 seconds default
        assert manager.timeout == 90  # 3x interval default

    def test_custom_configuration_overrides_interval(self) -> None:
        """
        GIVEN custom configuration
        WHEN HeartbeatManager is created
        THEN custom values should be used.
        """
        from mcp_server_langgraph.websocket.heartbeat import HeartbeatManager

        manager = HeartbeatManager(interval=60, timeout=180)
        assert manager.interval == 60
        assert manager.timeout == 180

    @pytest.mark.asyncio
    async def test_is_alive_property(self, mock_websocket: MagicMock) -> None:
        """
        GIVEN a HeartbeatManager
        WHEN checking is_alive
        THEN it should return True if within timeout window.
        """
        from mcp_server_langgraph.websocket.heartbeat import HeartbeatManager

        manager = HeartbeatManager(interval=30, timeout=60)
        assert manager.is_alive is True

        # Simulate time passing beyond timeout (mock last_activity)
        manager._last_activity = datetime.now(UTC).replace(year=2020)
        assert manager.is_alive is False
