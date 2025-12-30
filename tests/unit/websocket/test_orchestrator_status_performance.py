"""
Performance Tests for Orchestrator Status Broadcaster.

Tests concurrency, throughput, and scalability of the WebSocket broadcaster
under simulated load conditions.

These tests verify:
1. Concurrent subscriber handling (many simultaneous connections)
2. Broadcast throughput (many messages to many subscribers)
3. Task lifecycle throughput (start/complete/fail operations)
4. Memory efficiency (no leaks under load)
5. Queue depth handling (stress testing the queue)
"""

from __future__ import annotations

import asyncio
import gc
import os
import time
from typing import TYPE_CHECKING
from unittest.mock import AsyncMock

import pytest

if TYPE_CHECKING:
    pass

pytestmark = [
    pytest.mark.unit,
    pytest.mark.websocket,
    pytest.mark.orchestrator,
    pytest.mark.performance,
]


@pytest.mark.xdist_group(name="orchestrator_status_performance")
class TestOrchestratorStatusConcurrency:
    """Test concurrent subscriber handling."""

    def teardown_method(self) -> None:
        """Force GC to prevent mock accumulation in xdist workers."""
        gc.collect()

    def setup_method(self) -> None:
        """Reset broadcaster singleton before each test."""
        from mcp_server_langgraph.websocket.handlers.orchestrator_status import (
            reset_orchestrator_status_broadcaster,
        )

        reset_orchestrator_status_broadcaster()

    @pytest.mark.asyncio
    async def test_handles_100_concurrent_subscribers(self) -> None:
        """
        GIVEN the orchestrator status broadcaster
        WHEN 100 WebSocket clients subscribe concurrently
        THEN all subscriptions should complete without error
        """
        from mcp_server_langgraph.websocket.handlers.orchestrator_status import (
            OrchestratorStatusBroadcaster,
        )

        broadcaster = OrchestratorStatusBroadcaster()
        num_subscribers = 100

        # Create mock WebSockets
        mock_websockets = [AsyncMock(spec=["send_json"]) for _ in range(num_subscribers)]

        # Subscribe all concurrently
        subscribe_tasks = [broadcaster.subscribe(ws, user_id=f"user-{i}") for i, ws in enumerate(mock_websockets)]
        await asyncio.gather(*subscribe_tasks)

        assert broadcaster.subscriber_count == num_subscribers
        assert len(broadcaster._subscribers) == num_subscribers

    @pytest.mark.asyncio
    async def test_handles_100_concurrent_unsubscribes(self) -> None:
        """
        GIVEN 100 subscribed WebSocket clients
        WHEN all clients unsubscribe concurrently
        THEN all unsubscriptions should complete without error
        """
        from mcp_server_langgraph.websocket.handlers.orchestrator_status import (
            OrchestratorStatusBroadcaster,
        )

        broadcaster = OrchestratorStatusBroadcaster()
        num_subscribers = 100

        # Create and subscribe mock WebSockets
        mock_websockets = [AsyncMock(spec=["send_json"]) for _ in range(num_subscribers)]

        for i, ws in enumerate(mock_websockets):
            await broadcaster.subscribe(ws, user_id=f"user-{i}")

        assert broadcaster.subscriber_count == num_subscribers

        # Unsubscribe all concurrently
        unsubscribe_tasks = [broadcaster.unsubscribe(ws) for ws in mock_websockets]
        await asyncio.gather(*unsubscribe_tasks)

        assert broadcaster.subscriber_count == 0

    @pytest.mark.asyncio
    async def test_subscribe_unsubscribe_interleaved(self) -> None:
        """
        GIVEN the orchestrator status broadcaster
        WHEN subscribes and unsubscribes are interleaved concurrently
        THEN subscriber count should remain consistent
        """
        from mcp_server_langgraph.websocket.handlers.orchestrator_status import (
            OrchestratorStatusBroadcaster,
        )

        broadcaster = OrchestratorStatusBroadcaster()
        batch_size = 50

        # Create mock WebSockets
        subscribe_batch = [AsyncMock(spec=["send_json"]) for _ in range(batch_size)]
        unsubscribe_batch = [AsyncMock(spec=["send_json"]) for _ in range(batch_size)]

        # Subscribe unsubscribe_batch first
        for i, ws in enumerate(unsubscribe_batch):
            await broadcaster.subscribe(ws, user_id=f"user-unsub-{i}")

        assert broadcaster.subscriber_count == batch_size

        # Interleave: subscribe new + unsubscribe old
        tasks = []
        for i in range(batch_size):
            tasks.append(broadcaster.subscribe(subscribe_batch[i], user_id=f"user-sub-{i}"))
            tasks.append(broadcaster.unsubscribe(unsubscribe_batch[i]))

        await asyncio.gather(*tasks)

        assert broadcaster.subscriber_count == batch_size


@pytest.mark.xdist_group(name="orchestrator_status_performance")
class TestOrchestratorStatusBroadcastThroughput:
    """Test broadcast message throughput."""

    def teardown_method(self) -> None:
        """Force GC to prevent mock accumulation in xdist workers."""
        gc.collect()

    def setup_method(self) -> None:
        """Reset broadcaster singleton before each test."""
        from mcp_server_langgraph.websocket.handlers.orchestrator_status import (
            reset_orchestrator_status_broadcaster,
        )

        reset_orchestrator_status_broadcaster()

    @pytest.mark.asyncio
    async def test_broadcast_to_100_subscribers_under_100ms(self) -> None:
        """
        GIVEN 100 subscribed WebSocket clients
        WHEN broadcasting a status update
        THEN broadcast should complete in under 100ms
        """
        from mcp_server_langgraph.websocket.handlers.orchestrator_status import (
            OrchestratorStatus,
            OrchestratorStatusBroadcaster,
            TaskCategory,
        )

        broadcaster = OrchestratorStatusBroadcaster()
        num_subscribers = 100

        # Create and subscribe mock WebSockets
        mock_websockets = [AsyncMock(spec=["send_json"]) for _ in range(num_subscribers)]
        for ws in mock_websockets:
            ws.send_json = AsyncMock()  # Ensure send_json is async

        for i, ws in enumerate(mock_websockets):
            await broadcaster.subscribe(ws, user_id=f"user-{i}")

        # Measure broadcast time
        start = time.perf_counter()
        await broadcaster.broadcast_status(
            status=OrchestratorStatus.PROCESSING,
            message="Test broadcast",
            task_type="test_task",
            category=TaskCategory.UX,
        )
        elapsed_ms = (time.perf_counter() - start) * 1000

        # Verify all received
        for ws in mock_websockets:
            assert ws.send_json.called

        # Verify time constraint
        assert elapsed_ms < 100, f"Broadcast took {elapsed_ms:.2f}ms, expected < 100ms"

    @pytest.mark.asyncio
    async def test_100_broadcasts_to_50_subscribers_under_1s(self) -> None:
        """
        GIVEN 50 subscribed WebSocket clients
        WHEN broadcasting 100 status updates sequentially
        THEN all broadcasts should complete in under 1 second
        """
        from mcp_server_langgraph.websocket.handlers.orchestrator_status import (
            OrchestratorStatus,
            OrchestratorStatusBroadcaster,
            TaskCategory,
        )

        broadcaster = OrchestratorStatusBroadcaster()
        num_subscribers = 50
        num_broadcasts = 100

        # Create and subscribe mock WebSockets
        mock_websockets = [AsyncMock(spec=["send_json"]) for _ in range(num_subscribers)]
        for ws in mock_websockets:
            ws.send_json = AsyncMock()

        for i, ws in enumerate(mock_websockets):
            await broadcaster.subscribe(ws, user_id=f"user-{i}")

        # Measure broadcast time
        start = time.perf_counter()
        for n in range(num_broadcasts):
            await broadcaster.broadcast_status(
                status=OrchestratorStatus.PROCESSING,
                message=f"Test broadcast {n}",
                task_type="test_task",
                category=TaskCategory.UX,
            )
        elapsed_s = time.perf_counter() - start

        # Verify message count
        total_messages = sum(ws.send_json.call_count for ws in mock_websockets)
        expected_messages = num_subscribers * num_broadcasts
        assert total_messages == expected_messages

        # Verify time constraint
        assert elapsed_s < 1.0, f"Broadcasts took {elapsed_s:.2f}s, expected < 1s"


@pytest.mark.xdist_group(name="orchestrator_status_performance")
class TestOrchestratorStatusTaskLifecycleThroughput:
    """Test task lifecycle event throughput."""

    def teardown_method(self) -> None:
        """Force GC to prevent mock accumulation in xdist workers."""
        gc.collect()

    def setup_method(self) -> None:
        """Reset broadcaster singleton before each test."""
        from mcp_server_langgraph.websocket.handlers.orchestrator_status import (
            reset_orchestrator_status_broadcaster,
        )

        reset_orchestrator_status_broadcaster()

    @pytest.mark.asyncio
    async def test_100_task_lifecycle_events_under_500ms(self) -> None:
        """
        GIVEN 20 subscribed WebSocket clients
        WHEN processing 100 complete task lifecycles (start -> complete)
        THEN all events should broadcast in under 500ms
        """
        from datetime import UTC, datetime

        from mcp_server_langgraph.websocket.handlers.orchestrator_status import (
            OrchestratorStatusBroadcaster,
            TaskCategory,
            TaskInfo,
        )

        broadcaster = OrchestratorStatusBroadcaster()
        num_subscribers = 20
        num_tasks = 100

        # Create and subscribe mock WebSockets
        mock_websockets = [AsyncMock(spec=["send_json"]) for _ in range(num_subscribers)]
        for ws in mock_websockets:
            ws.send_json = AsyncMock()

        for i, ws in enumerate(mock_websockets):
            await broadcaster.subscribe(ws, user_id=f"user-{i}")

        # Measure lifecycle throughput
        start = time.perf_counter()
        for i in range(num_tasks):
            task_info = TaskInfo(
                task_id=f"task-{i}",
                task_type="test_task",
                category=TaskCategory.UX,
                started_at=datetime.now(UTC),
            )
            await broadcaster.broadcast_task_started(task_info)

            # Complete the task
            task_info.completed_at = datetime.now(UTC)
            task_info.success = True
            await broadcaster.broadcast_task_completed(task_info)

        elapsed_ms = (time.perf_counter() - start) * 1000

        # Verify no active tasks remain
        assert broadcaster.active_task_count == 0

        # Verify counters
        assert broadcaster._total_tasks_started == num_tasks
        assert broadcaster._total_tasks_completed == num_tasks

        # Verify time constraint
        assert elapsed_ms < 500, f"Lifecycle events took {elapsed_ms:.2f}ms, expected < 500ms"

    @pytest.mark.asyncio
    async def test_concurrent_task_starts_and_completes(self) -> None:
        """
        GIVEN 10 subscribed WebSocket clients
        WHEN 50 tasks start and 50 tasks complete concurrently
        THEN all events should broadcast correctly
        """
        from datetime import UTC, datetime

        from mcp_server_langgraph.websocket.handlers.orchestrator_status import (
            OrchestratorStatusBroadcaster,
            TaskCategory,
            TaskInfo,
        )

        broadcaster = OrchestratorStatusBroadcaster()
        num_subscribers = 10
        num_tasks = 50

        # Create and subscribe mock WebSockets
        mock_websockets = [AsyncMock(spec=["send_json"]) for _ in range(num_subscribers)]
        for ws in mock_websockets:
            ws.send_json = AsyncMock()

        for i, ws in enumerate(mock_websockets):
            await broadcaster.subscribe(ws, user_id=f"user-{i}")

        # Pre-create task infos for starts
        start_tasks_info = [
            TaskInfo(
                task_id=f"task-start-{i}",
                task_type="test_task",
                category=TaskCategory.SESSION,
                started_at=datetime.now(UTC),
            )
            for i in range(num_tasks)
        ]

        # Pre-start tasks for completes
        complete_tasks_info = []
        for i in range(num_tasks):
            task_info = TaskInfo(
                task_id=f"task-complete-{i}",
                task_type="test_task",
                category=TaskCategory.CONVERSATION,
                started_at=datetime.now(UTC),
            )
            await broadcaster.broadcast_task_started(task_info)
            task_info.completed_at = datetime.now(UTC)
            task_info.success = True
            complete_tasks_info.append(task_info)

        # Run starts and completes concurrently
        start_tasks = [broadcaster.broadcast_task_started(t) for t in start_tasks_info]
        complete_tasks = [broadcaster.broadcast_task_completed(t) for t in complete_tasks_info]

        await asyncio.gather(*start_tasks, *complete_tasks)

        # Verify active tasks (only the new starts should be active)
        assert broadcaster.active_task_count == num_tasks
        assert broadcaster._total_tasks_started == num_tasks * 2
        assert broadcaster._total_tasks_completed == num_tasks


@pytest.mark.xdist_group(name="orchestrator_status_performance")
class TestOrchestratorStatusQueueStress:
    """Test queue handling under stress."""

    def teardown_method(self) -> None:
        """Force GC to prevent mock accumulation in xdist workers."""
        gc.collect()

    def setup_method(self) -> None:
        """Reset broadcaster singleton before each test."""
        from mcp_server_langgraph.websocket.handlers.orchestrator_status import (
            reset_orchestrator_status_broadcaster,
        )

        reset_orchestrator_status_broadcaster()

    @pytest.mark.asyncio
    async def test_queue_100_tasks_performance(self) -> None:
        """
        GIVEN the orchestrator status broadcaster
        WHEN 100 tasks are queued rapidly
        THEN queue depth should track correctly with acceptable performance
        """
        from mcp_server_langgraph.websocket.handlers.orchestrator_status import (
            OrchestratorStatusBroadcaster,
            TaskCategory,
        )

        broadcaster = OrchestratorStatusBroadcaster()
        num_tasks = 100

        # Create and subscribe a mock WebSocket
        mock_ws = AsyncMock(spec=["send_json"])
        mock_ws.send_json = AsyncMock()
        await broadcaster.subscribe(mock_ws, user_id="user-1")

        # Measure queue time
        start = time.perf_counter()
        for i in range(num_tasks):
            await broadcaster.queue_task(
                task_id=f"task-{i}",
                task_type="queued_task",
                category=TaskCategory.CANVAS,
            )
        elapsed_ms = (time.perf_counter() - start) * 1000

        # Verify queue depth
        assert broadcaster.queue_depth == num_tasks

        # Verify performance
        assert elapsed_ms < 200, f"Queuing took {elapsed_ms:.2f}ms, expected < 200ms"

    @pytest.mark.asyncio
    async def test_queue_and_start_interleaved(self) -> None:
        """
        GIVEN tasks in queue
        WHEN tasks are started (removing from queue)
        THEN queue depth should decrease correctly
        """
        from datetime import UTC, datetime

        from mcp_server_langgraph.websocket.handlers.orchestrator_status import (
            OrchestratorStatusBroadcaster,
            TaskCategory,
            TaskInfo,
        )

        broadcaster = OrchestratorStatusBroadcaster()
        num_tasks = 50

        # Create and subscribe a mock WebSocket
        mock_ws = AsyncMock(spec=["send_json"])
        mock_ws.send_json = AsyncMock()
        await broadcaster.subscribe(mock_ws, user_id="user-1")

        # Queue all tasks
        for i in range(num_tasks):
            await broadcaster.queue_task(
                task_id=f"task-{i}",
                task_type="interleaved_task",
                category=TaskCategory.DIAGRAM,
            )

        assert broadcaster.queue_depth == num_tasks

        # Start half the tasks (should remove from queue)
        for i in range(num_tasks // 2):
            task_info = TaskInfo(
                task_id=f"task-{i}",
                task_type="interleaved_task",
                category=TaskCategory.DIAGRAM,
                started_at=datetime.now(UTC),
            )
            await broadcaster.broadcast_task_started(task_info)

        # Verify queue reduced
        assert broadcaster.queue_depth == num_tasks // 2
        assert broadcaster.active_task_count == num_tasks // 2


@pytest.mark.xdist_group(name="orchestrator_status_performance")
class TestOrchestratorStatusProgressThroughput:
    """Test task progress update throughput."""

    def teardown_method(self) -> None:
        """Force GC to prevent mock accumulation in xdist workers."""
        gc.collect()

    def setup_method(self) -> None:
        """Reset broadcaster singleton before each test."""
        from mcp_server_langgraph.websocket.handlers.orchestrator_status import (
            reset_orchestrator_status_broadcaster,
        )

        reset_orchestrator_status_broadcaster()

    @pytest.mark.asyncio
    async def test_100_progress_updates_single_task(self) -> None:
        """
        GIVEN an active task with subscribers
        WHEN sending 100 progress updates (0-100%)
        THEN all updates should broadcast quickly
        """
        from datetime import UTC, datetime

        from mcp_server_langgraph.websocket.handlers.orchestrator_status import (
            OrchestratorStatusBroadcaster,
            TaskCategory,
            TaskInfo,
        )

        broadcaster = OrchestratorStatusBroadcaster()
        num_subscribers = 10

        # Create and subscribe mock WebSockets
        mock_websockets = [AsyncMock(spec=["send_json"]) for _ in range(num_subscribers)]
        for ws in mock_websockets:
            ws.send_json = AsyncMock()

        for i, ws in enumerate(mock_websockets):
            await broadcaster.subscribe(ws, user_id=f"user-{i}")

        # Start a task
        task_info = TaskInfo(
            task_id="progress-task",
            task_type="long_running",
            category=TaskCategory.TRACE,
            started_at=datetime.now(UTC),
        )
        await broadcaster.broadcast_task_started(task_info)

        # Send 100 progress updates
        start = time.perf_counter()
        for progress in range(101):
            await broadcaster.broadcast_task_progress(
                task_id="progress-task",
                progress=progress,
                message=f"Processing {progress}%",
            )
        elapsed_ms = (time.perf_counter() - start) * 1000

        # Verify task progress is tracked
        assert broadcaster._active_tasks["progress-task"].progress == 100

        # Verify performance
        assert elapsed_ms < 300, f"Progress updates took {elapsed_ms:.2f}ms, expected < 300ms"

    @pytest.mark.asyncio
    async def test_concurrent_progress_updates_multiple_tasks(self) -> None:
        """
        GIVEN 10 active tasks with subscribers
        WHEN sending concurrent progress updates to all tasks
        THEN all updates should be delivered correctly
        """
        from datetime import UTC, datetime

        from mcp_server_langgraph.websocket.handlers.orchestrator_status import (
            OrchestratorStatusBroadcaster,
            TaskCategory,
            TaskInfo,
        )

        broadcaster = OrchestratorStatusBroadcaster()
        num_tasks = 10
        num_subscribers = 5

        # Create and subscribe mock WebSockets
        mock_websockets = [AsyncMock(spec=["send_json"]) for _ in range(num_subscribers)]
        for ws in mock_websockets:
            ws.send_json = AsyncMock()

        for i, ws in enumerate(mock_websockets):
            await broadcaster.subscribe(ws, user_id=f"user-{i}")

        # Start all tasks
        for i in range(num_tasks):
            task_info = TaskInfo(
                task_id=f"multi-task-{i}",
                task_type="concurrent_task",
                category=TaskCategory.HITL,
                started_at=datetime.now(UTC),
            )
            await broadcaster.broadcast_task_started(task_info)

        # Send concurrent progress updates
        update_tasks = []
        for i in range(num_tasks):
            for progress in [25, 50, 75, 100]:
                update_tasks.append(
                    broadcaster.broadcast_task_progress(
                        task_id=f"multi-task-{i}",
                        progress=progress,
                    )
                )

        await asyncio.gather(*update_tasks)

        # Verify all tasks have final progress
        for i in range(num_tasks):
            task = broadcaster._active_tasks.get(f"multi-task-{i}")
            assert task is not None
            assert task.progress == 100


@pytest.mark.xdist_group(name="orchestrator_status_performance")
class TestOrchestratorStatusFailedSubscriberCleanup:
    """Test cleanup of failed subscribers under load."""

    def teardown_method(self) -> None:
        """Force GC to prevent mock accumulation in xdist workers."""
        gc.collect()

    def setup_method(self) -> None:
        """Reset broadcaster singleton before each test."""
        from mcp_server_langgraph.websocket.handlers.orchestrator_status import (
            reset_orchestrator_status_broadcaster,
        )

        reset_orchestrator_status_broadcaster()

    @pytest.mark.asyncio
    async def test_cleanup_50_percent_failed_subscribers(self) -> None:
        """
        GIVEN 100 subscribers where 50 fail to receive
        WHEN broadcasting
        THEN failed subscribers should be removed automatically
        """
        from mcp_server_langgraph.websocket.handlers.orchestrator_status import (
            OrchestratorStatus,
            OrchestratorStatusBroadcaster,
            TaskCategory,
        )

        broadcaster = OrchestratorStatusBroadcaster()
        num_subscribers = 100
        num_failing = 50

        # Create mock WebSockets - half will fail
        mock_websockets = []
        for i in range(num_subscribers):
            ws = AsyncMock(spec=["send_json"])
            if i < num_failing:
                # These will raise on send
                ws.send_json = AsyncMock(side_effect=Exception("Connection closed"))
            else:
                ws.send_json = AsyncMock()
            mock_websockets.append(ws)

        for i, ws in enumerate(mock_websockets):
            await broadcaster.subscribe(ws, user_id=f"user-{i}")

        assert broadcaster.subscriber_count == num_subscribers

        # Broadcast - should trigger cleanup
        await broadcaster.broadcast_status(
            status=OrchestratorStatus.PROCESSING,
            message="Test cleanup",
            task_type="test_task",
            category=TaskCategory.COMMAND,
        )

        # Verify failed subscribers were removed
        assert broadcaster.subscriber_count == num_subscribers - num_failing

    @pytest.mark.asyncio
    async def test_broadcast_continues_after_some_failures(self) -> None:
        """
        GIVEN subscribers where some fail
        WHEN broadcasting
        THEN successful subscribers should still receive messages
        """
        from mcp_server_langgraph.websocket.handlers.orchestrator_status import (
            OrchestratorStatus,
            OrchestratorStatusBroadcaster,
            TaskCategory,
        )

        broadcaster = OrchestratorStatusBroadcaster()
        num_healthy = 30
        num_failing = 10

        # Create healthy subscribers
        healthy_websockets = []
        for i in range(num_healthy):
            ws = AsyncMock(spec=["send_json"])
            ws.send_json = AsyncMock()
            healthy_websockets.append(ws)
            await broadcaster.subscribe(ws, user_id=f"healthy-{i}")

        # Create failing subscribers
        for i in range(num_failing):
            ws = AsyncMock(spec=["send_json"])
            ws.send_json = AsyncMock(side_effect=Exception("Failed"))
            await broadcaster.subscribe(ws, user_id=f"failing-{i}")

        # Broadcast
        await broadcaster.broadcast_status(
            status=OrchestratorStatus.IDLE,
            message="Recovery test",
            task_type="test",
            category=TaskCategory.ALERT,
        )

        # Verify healthy subscribers received message
        for ws in healthy_websockets:
            assert ws.send_json.called

        # Verify subscriber count reflects cleanup
        assert broadcaster.subscriber_count == num_healthy


@pytest.mark.xdist_group(name="orchestrator_status_performance")
@pytest.mark.skipif(
    os.getenv("PYTEST_XDIST_WORKER") is not None,
    reason="Memory-intensive test skipped in parallel mode",
)
class TestOrchestratorStatusMemoryEfficiency:
    """Test memory efficiency under sustained load."""

    def teardown_method(self) -> None:
        """Force GC to prevent mock accumulation in xdist workers."""
        gc.collect()

    def setup_method(self) -> None:
        """Reset broadcaster singleton before each test."""
        from mcp_server_langgraph.websocket.handlers.orchestrator_status import (
            reset_orchestrator_status_broadcaster,
        )

        reset_orchestrator_status_broadcaster()

    @pytest.mark.asyncio
    async def test_no_memory_leak_after_1000_subscribe_unsubscribe_cycles(self) -> None:
        """
        GIVEN the orchestrator status broadcaster
        WHEN subscribing and unsubscribing 1000 times
        THEN internal data structures should not grow
        """
        from mcp_server_langgraph.websocket.handlers.orchestrator_status import (
            OrchestratorStatusBroadcaster,
        )

        broadcaster = OrchestratorStatusBroadcaster()
        num_cycles = 1000

        for _ in range(num_cycles):
            ws = AsyncMock(spec=["send_json"])
            await broadcaster.subscribe(ws, user_id="cycle-user")
            await broadcaster.unsubscribe(ws)

        # After all cycles, should have no subscribers
        assert broadcaster.subscriber_count == 0
        assert len(broadcaster._subscribers) == 0

    @pytest.mark.asyncio
    async def test_no_memory_leak_after_1000_task_lifecycles(self) -> None:
        """
        GIVEN the orchestrator status broadcaster
        WHEN processing 1000 complete task lifecycles
        THEN active_tasks dict should not grow
        """
        from datetime import UTC, datetime

        from mcp_server_langgraph.websocket.handlers.orchestrator_status import (
            OrchestratorStatusBroadcaster,
            TaskCategory,
            TaskInfo,
        )

        broadcaster = OrchestratorStatusBroadcaster()
        num_cycles = 1000

        # Subscribe a minimal WebSocket to enable broadcasts
        ws = AsyncMock(spec=["send_json"])
        ws.send_json = AsyncMock()
        await broadcaster.subscribe(ws, user_id="test-user")

        for i in range(num_cycles):
            task_info = TaskInfo(
                task_id=f"lifecycle-task-{i}",
                task_type="lifecycle_test",
                category=TaskCategory.UX,
                started_at=datetime.now(UTC),
            )
            await broadcaster.broadcast_task_started(task_info)
            task_info.completed_at = datetime.now(UTC)
            task_info.success = True
            await broadcaster.broadcast_task_completed(task_info)

        # After all cycles, should have no active tasks
        assert broadcaster.active_task_count == 0
        assert len(broadcaster._active_tasks) == 0

        # Counters should reflect all cycles
        assert broadcaster._total_tasks_started == num_cycles
        assert broadcaster._total_tasks_completed == num_cycles

    @pytest.mark.asyncio
    async def test_queue_memory_cleared_on_task_start(self) -> None:
        """
        GIVEN tasks queued in broadcaster
        WHEN tasks are started
        THEN queue memory should be freed
        """
        from datetime import UTC, datetime

        from mcp_server_langgraph.websocket.handlers.orchestrator_status import (
            OrchestratorStatusBroadcaster,
            TaskCategory,
            TaskInfo,
        )

        broadcaster = OrchestratorStatusBroadcaster()
        num_tasks = 100

        # Subscribe a minimal WebSocket
        ws = AsyncMock(spec=["send_json"])
        ws.send_json = AsyncMock()
        await broadcaster.subscribe(ws, user_id="test-user")

        # Queue all tasks
        for i in range(num_tasks):
            await broadcaster.queue_task(
                task_id=f"queue-task-{i}",
                task_type="queue_test",
                category=TaskCategory.SESSION,
            )

        assert broadcaster.queue_depth == num_tasks

        # Start all tasks (should remove from queue)
        for i in range(num_tasks):
            task_info = TaskInfo(
                task_id=f"queue-task-{i}",
                task_type="queue_test",
                category=TaskCategory.SESSION,
                started_at=datetime.now(UTC),
            )
            await broadcaster.broadcast_task_started(task_info)

        # Queue should be empty
        assert broadcaster.queue_depth == 0
        assert len(broadcaster._queued_tasks) == 0
