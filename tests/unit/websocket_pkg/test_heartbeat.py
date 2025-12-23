"""
Unit tests for WebSocket Heartbeat Manager.

Tests the HeartbeatManager class for server-initiated heartbeat functionality.
"""

import asyncio
import gc
from datetime import UTC, datetime, timedelta
from unittest.mock import AsyncMock, MagicMock

import pytest

pytestmark = [
    pytest.mark.unit,
    pytest.mark.websocket,
    pytest.mark.xdist_group(name="websocket_heartbeat"),
]


@pytest.mark.xdist_group(name="websocket_heartbeat")
class TestHeartbeatManagerInit:
    """Tests for HeartbeatManager initialization."""

    def teardown_method(self) -> None:
        """Force GC to prevent mock accumulation in xdist workers."""
        gc.collect()

    def test_init_with_defaults(self) -> None:
        """GIVEN no custom values WHEN creating manager THEN uses defaults."""
        from mcp_server_langgraph.websocket.heartbeat import HeartbeatManager

        manager = HeartbeatManager()

        assert manager.interval == 30
        assert manager.timeout == 90  # 3x interval
        assert manager._on_timeout is None
        assert manager._task is None
        assert manager._websocket is None
        assert manager._running is False

    def test_init_with_custom_interval(self) -> None:
        """GIVEN custom interval WHEN creating manager THEN uses it and calculates timeout."""
        from mcp_server_langgraph.websocket.heartbeat import HeartbeatManager

        manager = HeartbeatManager(interval=10)

        assert manager.interval == 10
        assert manager.timeout == 30  # 3x interval

    def test_init_with_custom_timeout(self) -> None:
        """GIVEN custom timeout WHEN creating manager THEN uses it."""
        from mcp_server_langgraph.websocket.heartbeat import HeartbeatManager

        manager = HeartbeatManager(interval=10, timeout=60)

        assert manager.interval == 10
        assert manager.timeout == 60  # Custom, not 3x interval

    def test_init_with_on_timeout_callback(self) -> None:
        """GIVEN on_timeout callback WHEN creating manager THEN stores it."""
        from mcp_server_langgraph.websocket.heartbeat import HeartbeatManager

        async def timeout_handler() -> None:
            pass

        manager = HeartbeatManager(on_timeout=timeout_handler)

        assert manager._on_timeout is timeout_handler


@pytest.mark.xdist_group(name="websocket_heartbeat")
class TestHeartbeatManagerProperties:
    """Tests for HeartbeatManager properties."""

    def teardown_method(self) -> None:
        """Force GC to prevent mock accumulation in xdist workers."""
        gc.collect()

    def test_last_activity_returns_timestamp(self) -> None:
        """GIVEN manager WHEN getting last_activity THEN returns datetime."""
        from mcp_server_langgraph.websocket.heartbeat import HeartbeatManager

        manager = HeartbeatManager()
        activity = manager.last_activity

        assert isinstance(activity, datetime)
        assert activity.tzinfo is not None

    def test_is_alive_returns_true_when_within_timeout(self) -> None:
        """GIVEN recent activity WHEN checking is_alive THEN returns True."""
        from mcp_server_langgraph.websocket.heartbeat import HeartbeatManager

        manager = HeartbeatManager(timeout=60)
        manager._last_activity = datetime.now(UTC)

        assert manager.is_alive is True

    def test_is_alive_returns_false_when_past_timeout(self) -> None:
        """GIVEN old activity WHEN checking is_alive THEN returns False."""
        from mcp_server_langgraph.websocket.heartbeat import HeartbeatManager

        manager = HeartbeatManager(timeout=60)
        manager._last_activity = datetime.now(UTC) - timedelta(seconds=120)

        assert manager.is_alive is False


@pytest.mark.xdist_group(name="websocket_heartbeat")
class TestHeartbeatManagerStart:
    """Tests for HeartbeatManager start method."""

    def teardown_method(self) -> None:
        """Force GC to prevent mock accumulation in xdist workers."""
        gc.collect()

    @pytest.mark.asyncio
    async def test_start_sets_websocket(self) -> None:
        """GIVEN websocket WHEN starting THEN stores websocket reference."""
        from mcp_server_langgraph.websocket.heartbeat import HeartbeatManager

        manager = HeartbeatManager(interval=1)
        mock_ws = MagicMock()

        task = await manager.start(mock_ws)

        assert manager._websocket is mock_ws
        assert manager._running is True
        assert manager._task is task

        # Clean up
        await manager.stop()

    @pytest.mark.asyncio
    async def test_start_returns_task(self) -> None:
        """GIVEN websocket WHEN starting THEN returns asyncio task."""
        from mcp_server_langgraph.websocket.heartbeat import HeartbeatManager

        manager = HeartbeatManager(interval=1)
        mock_ws = MagicMock()

        task = await manager.start(mock_ws)

        assert isinstance(task, asyncio.Task)

        # Clean up
        await manager.stop()

    @pytest.mark.asyncio
    async def test_start_resets_last_activity(self) -> None:
        """GIVEN old activity WHEN starting THEN resets last_activity."""
        from mcp_server_langgraph.websocket.heartbeat import HeartbeatManager

        manager = HeartbeatManager(interval=1)
        manager._last_activity = datetime.now(UTC) - timedelta(hours=1)
        mock_ws = MagicMock()

        before = datetime.now(UTC)
        await manager.start(mock_ws)
        after = datetime.now(UTC)

        assert before <= manager._last_activity <= after

        # Clean up
        await manager.stop()


@pytest.mark.xdist_group(name="websocket_heartbeat")
class TestHeartbeatManagerStop:
    """Tests for HeartbeatManager stop method."""

    def teardown_method(self) -> None:
        """Force GC to prevent mock accumulation in xdist workers."""
        gc.collect()

    @pytest.mark.asyncio
    async def test_stop_sets_running_false(self) -> None:
        """GIVEN running manager WHEN stopping THEN sets running to False."""
        from mcp_server_langgraph.websocket.heartbeat import HeartbeatManager

        manager = HeartbeatManager(interval=1)
        mock_ws = MagicMock()

        await manager.start(mock_ws)
        await manager.stop()

        assert manager._running is False
        assert manager._task is None

    @pytest.mark.asyncio
    async def test_stop_cancels_task(self) -> None:
        """GIVEN running task WHEN stopping THEN cancels task."""
        from mcp_server_langgraph.websocket.heartbeat import HeartbeatManager

        manager = HeartbeatManager(interval=1)
        mock_ws = MagicMock()

        task = await manager.start(mock_ws)
        await manager.stop()

        assert task.cancelled() or task.done()

    @pytest.mark.asyncio
    async def test_stop_handles_no_task(self) -> None:
        """GIVEN no task WHEN stopping THEN does not raise."""
        from mcp_server_langgraph.websocket.heartbeat import HeartbeatManager

        manager = HeartbeatManager()

        # Should not raise
        await manager.stop()

        assert manager._running is False


@pytest.mark.xdist_group(name="websocket_heartbeat")
class TestHeartbeatManagerOnPong:
    """Tests for HeartbeatManager on_pong method."""

    def teardown_method(self) -> None:
        """Force GC to prevent mock accumulation in xdist workers."""
        gc.collect()

    @pytest.mark.asyncio
    async def test_on_pong_updates_last_activity(self) -> None:
        """GIVEN old activity WHEN on_pong called THEN updates timestamp."""
        from mcp_server_langgraph.websocket.heartbeat import HeartbeatManager

        manager = HeartbeatManager()
        manager._last_activity = datetime.now(UTC) - timedelta(minutes=5)
        old_activity = manager._last_activity

        before = datetime.now(UTC)
        await manager.on_pong()
        after = datetime.now(UTC)

        assert manager._last_activity > old_activity
        assert before <= manager._last_activity <= after


@pytest.mark.xdist_group(name="websocket_heartbeat")
class TestHeartbeatLoop:
    """Tests for HeartbeatManager heartbeat loop."""

    def teardown_method(self) -> None:
        """Force GC to prevent mock accumulation in xdist workers."""
        gc.collect()

    @pytest.mark.asyncio
    async def test_heartbeat_loop_sends_heartbeat(self) -> None:
        """GIVEN running manager WHEN interval passes THEN sends heartbeat."""
        from mcp_server_langgraph.websocket.heartbeat import HeartbeatManager

        manager = HeartbeatManager(interval=0.1, timeout=10)
        mock_ws = MagicMock()
        mock_ws.send_json = AsyncMock()

        await manager.start(mock_ws)
        await asyncio.sleep(0.15)  # Wait for heartbeat
        await manager.stop()

        mock_ws.send_json.assert_called()
        call_args = mock_ws.send_json.call_args[0][0]
        assert call_args["type"] == "heartbeat"
        assert "timestamp" in call_args

    @pytest.mark.asyncio
    async def test_heartbeat_loop_calls_timeout_callback_on_timeout(self) -> None:
        """GIVEN timeout WHEN no pong received THEN calls timeout callback."""
        from mcp_server_langgraph.websocket.heartbeat import HeartbeatManager

        timeout_called = asyncio.Event()

        async def on_timeout() -> None:
            timeout_called.set()

        manager = HeartbeatManager(interval=0.05, timeout=0.01, on_timeout=on_timeout)
        mock_ws = MagicMock()
        mock_ws.send_json = AsyncMock()

        await manager.start(mock_ws)
        try:
            await asyncio.wait_for(timeout_called.wait(), timeout=1.0)
        except TimeoutError:
            pytest.fail("Timeout callback was not called")
        finally:
            await manager.stop()

    @pytest.mark.asyncio
    async def test_heartbeat_loop_stops_on_send_failure(self) -> None:
        """GIVEN send failure WHEN sending heartbeat THEN calls timeout callback."""
        from mcp_server_langgraph.websocket.heartbeat import HeartbeatManager

        timeout_called = asyncio.Event()

        async def on_timeout() -> None:
            timeout_called.set()

        manager = HeartbeatManager(interval=0.05, timeout=10, on_timeout=on_timeout)
        mock_ws = MagicMock()
        mock_ws.send_json = AsyncMock(side_effect=Exception("Connection closed"))

        await manager.start(mock_ws)
        try:
            await asyncio.wait_for(timeout_called.wait(), timeout=1.0)
        except TimeoutError:
            pytest.fail("Timeout callback was not called on send failure")
        finally:
            await manager.stop()

    @pytest.mark.asyncio
    async def test_heartbeat_loop_handles_cancelled_error(self) -> None:
        """GIVEN cancelled task WHEN in heartbeat loop THEN exits gracefully."""
        from mcp_server_langgraph.websocket.heartbeat import HeartbeatManager

        manager = HeartbeatManager(interval=5)  # Long interval
        mock_ws = MagicMock()
        mock_ws.send_json = AsyncMock()

        task = await manager.start(mock_ws)
        await asyncio.sleep(0.01)  # Let loop start
        await manager.stop()

        # Task should be done without raising
        assert task.cancelled() or task.done()

    @pytest.mark.asyncio
    async def test_heartbeat_loop_stops_when_running_false(self) -> None:
        """GIVEN running set to False WHEN in loop THEN exits."""
        from mcp_server_langgraph.websocket.heartbeat import HeartbeatManager

        manager = HeartbeatManager(interval=0.05)
        mock_ws = MagicMock()
        mock_ws.send_json = AsyncMock()

        task = await manager.start(mock_ws)
        await asyncio.sleep(0.03)
        manager._running = False  # Stop without calling stop()
        await asyncio.sleep(0.1)  # Wait for loop to exit

        assert task.done()
