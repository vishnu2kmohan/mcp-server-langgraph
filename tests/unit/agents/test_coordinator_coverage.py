"""
Comprehensive tests for the Coordinator class.

These tests cover subagent lifecycle management, parallel execution,
artifact storage, and error handling to achieve 75%+ coverage.
"""

from __future__ import annotations

import gc
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from mcp_server_langgraph.agents.coordinator import Coordinator
from mcp_server_langgraph.agents.subagent import Subagent, SubagentResult, SubagentStatus

pytestmark = [pytest.mark.unit, pytest.mark.agents]


def create_mock_subagent(
    task_id: str,
    status: SubagentStatus = SubagentStatus.PENDING,
    execute_result: SubagentResult | None = None,
) -> Subagent:
    """Create a mock subagent for testing."""
    subagent = MagicMock(spec=Subagent)
    subagent.task_id = task_id
    subagent.status = status
    subagent.execute = AsyncMock(
        return_value=execute_result
        or SubagentResult(task_id=task_id, success=True, output="test output")
    )
    subagent.cancel = MagicMock()
    return subagent


@pytest.mark.xdist_group(name="test_coordinator_lifecycle")
class TestCoordinatorLifecycle:
    """Tests for subagent registration and lifecycle."""

    def teardown_method(self) -> None:
        """Force GC to prevent memory accumulation."""
        gc.collect()

    def test_coordinator_init_creates_artifact_storage(self) -> None:
        """Test that coordinator creates default artifact storage."""
        coordinator = Coordinator()
        assert coordinator.artifact_storage is not None

    def test_coordinator_init_accepts_custom_storage(self) -> None:
        """Test that coordinator accepts custom artifact storage."""
        from mcp_server_langgraph.agents.artifacts import ArtifactStorage

        storage = ArtifactStorage()
        coordinator = Coordinator(artifact_storage=storage)
        assert coordinator.artifact_storage is storage

    def test_register_subagent(self) -> None:
        """Test registering a subagent."""
        coordinator = Coordinator()
        subagent = create_mock_subagent("task-1")

        coordinator.register_subagent(subagent)

        assert coordinator.get_subagent("task-1") is subagent

    def test_register_multiple_subagents(self) -> None:
        """Test registering multiple subagents."""
        coordinator = Coordinator()

        for i in range(5):
            subagent = create_mock_subagent(f"task-{i}")
            coordinator.register_subagent(subagent)

        assert len(coordinator.list_subagents()) == 5

    def test_unregister_subagent(self) -> None:
        """Test unregistering a subagent."""
        coordinator = Coordinator()
        subagent = create_mock_subagent("task-1")
        coordinator.register_subagent(subagent)

        coordinator.unregister_subagent("task-1")

        assert coordinator.get_subagent("task-1") is None

    def test_unregister_nonexistent_subagent_no_error(self) -> None:
        """Test that unregistering nonexistent subagent doesn't raise."""
        coordinator = Coordinator()
        coordinator.unregister_subagent("nonexistent")  # Should not raise

    def test_get_subagent_returns_none_for_missing(self) -> None:
        """Test that get_subagent returns None for missing task."""
        coordinator = Coordinator()
        assert coordinator.get_subagent("missing") is None

    def test_list_subagents_empty(self) -> None:
        """Test listing subagents when none registered."""
        coordinator = Coordinator()
        assert coordinator.list_subagents() == []

    def test_list_subagents_returns_all(self) -> None:
        """Test that list_subagents returns all registered subagents."""
        coordinator = Coordinator()
        subagents = [create_mock_subagent(f"task-{i}") for i in range(3)]
        for sa in subagents:
            coordinator.register_subagent(sa)

        listed = coordinator.list_subagents()

        assert len(listed) == 3
        assert all(sa in listed for sa in subagents)


@pytest.mark.xdist_group(name="test_coordinator_status")
class TestCoordinatorStatus:
    """Tests for status tracking."""

    def teardown_method(self) -> None:
        """Force GC to prevent memory accumulation."""
        gc.collect()

    def test_get_status_summary_empty(self) -> None:
        """Test status summary with no subagents."""
        coordinator = Coordinator()
        assert coordinator.get_status_summary() == {}

    def test_get_status_summary_single_status(self) -> None:
        """Test status summary with all same status."""
        coordinator = Coordinator()
        for i in range(3):
            subagent = create_mock_subagent(f"task-{i}", SubagentStatus.PENDING)
            coordinator.register_subagent(subagent)

        summary = coordinator.get_status_summary()

        assert summary == {"pending": 3}

    def test_get_status_summary_mixed_statuses(self) -> None:
        """Test status summary with mixed statuses."""
        coordinator = Coordinator()

        statuses = [
            SubagentStatus.PENDING,
            SubagentStatus.PENDING,
            SubagentStatus.RUNNING,
            SubagentStatus.COMPLETED,
            SubagentStatus.FAILED,
        ]

        for i, status in enumerate(statuses):
            subagent = create_mock_subagent(f"task-{i}", status)
            coordinator.register_subagent(subagent)

        summary = coordinator.get_status_summary()

        assert summary["pending"] == 2
        assert summary["running"] == 1
        assert summary["completed"] == 1
        assert summary["failed"] == 1


@pytest.mark.xdist_group(name="test_coordinator_execution")
class TestCoordinatorExecution:
    """Tests for parallel execution."""

    def teardown_method(self) -> None:
        """Force GC to prevent memory accumulation."""
        gc.collect()

    @pytest.mark.asyncio
    async def test_execute_all_empty(self) -> None:
        """Test execute_all with no subagents."""
        coordinator = Coordinator()
        results = await coordinator.execute_all()
        assert results == []

    @pytest.mark.asyncio
    async def test_execute_all_no_pending(self) -> None:
        """Test execute_all with no pending subagents."""
        coordinator = Coordinator()
        subagent = create_mock_subagent("task-1", SubagentStatus.COMPLETED)
        coordinator.register_subagent(subagent)

        results = await coordinator.execute_all()

        assert results == []
        subagent.execute.assert_not_called()

    @pytest.mark.asyncio
    async def test_execute_all_pending_subagents(self) -> None:
        """Test execute_all executes all pending subagents."""
        coordinator = Coordinator()

        for i in range(3):
            subagent = create_mock_subagent(f"task-{i}", SubagentStatus.PENDING)
            coordinator.register_subagent(subagent)

        results = await coordinator.execute_all()

        assert len(results) == 3
        assert all(r.success for r in results)

    @pytest.mark.asyncio
    async def test_execute_all_handles_exceptions(self) -> None:
        """Test that execute_all handles exceptions from subagents."""
        coordinator = Coordinator()

        # One successful, one failing
        good_subagent = create_mock_subagent("task-good")
        bad_subagent = create_mock_subagent("task-bad")
        bad_subagent.execute = AsyncMock(side_effect=RuntimeError("Execution failed"))

        coordinator.register_subagent(good_subagent)
        coordinator.register_subagent(bad_subagent)

        results = await coordinator.execute_all()

        assert len(results) == 2
        # Find results by task_id
        good_result = next(r for r in results if r.task_id == "task-good")
        bad_result = next(r for r in results if r.task_id == "task-bad")

        assert good_result.success is True
        assert bad_result.success is False
        assert "Execution failed" in bad_result.error

    @pytest.mark.asyncio
    async def test_execute_subagent_found(self) -> None:
        """Test executing a specific subagent."""
        coordinator = Coordinator()
        expected_result = SubagentResult(
            task_id="task-1", success=True, output="specific output"
        )
        subagent = create_mock_subagent("task-1", execute_result=expected_result)
        coordinator.register_subagent(subagent)

        result = await coordinator.execute_subagent("task-1")

        assert result == expected_result
        subagent.execute.assert_called_once()

    @pytest.mark.asyncio
    async def test_execute_subagent_not_found(self) -> None:
        """Test executing a nonexistent subagent."""
        coordinator = Coordinator()

        result = await coordinator.execute_subagent("nonexistent")

        assert result is None


@pytest.mark.xdist_group(name="test_coordinator_artifacts")
class TestCoordinatorArtifacts:
    """Tests for artifact storage operations."""

    def teardown_method(self) -> None:
        """Force GC to prevent memory accumulation."""
        gc.collect()

    def test_store_artifact(self) -> None:
        """Test storing an artifact."""
        coordinator = Coordinator()

        coordinator.store_artifact("task-1", "output", {"key": "value"})

        artifacts = coordinator.collect_artifacts("task-1")
        assert len(artifacts) == 1
        assert artifacts[0] == {"key": "value"}

    def test_store_multiple_artifacts(self) -> None:
        """Test storing multiple artifacts for same task."""
        coordinator = Coordinator()

        coordinator.store_artifact("task-1", "output1", "data1")
        coordinator.store_artifact("task-1", "output2", "data2")

        artifacts = coordinator.collect_artifacts("task-1")
        assert len(artifacts) == 2
        assert "data1" in artifacts
        assert "data2" in artifacts

    def test_collect_artifacts_empty(self) -> None:
        """Test collecting artifacts when none stored."""
        coordinator = Coordinator()
        artifacts = coordinator.collect_artifacts("task-1")
        assert artifacts == []


@pytest.mark.xdist_group(name="test_coordinator_cancel")
class TestCoordinatorCancel:
    """Tests for cancellation operations."""

    def teardown_method(self) -> None:
        """Force GC to prevent memory accumulation."""
        gc.collect()

    def test_cancel_all_no_running(self) -> None:
        """Test cancel_all with no running subagents."""
        coordinator = Coordinator()
        subagent = create_mock_subagent("task-1", SubagentStatus.PENDING)
        coordinator.register_subagent(subagent)

        cancelled = coordinator.cancel_all()

        assert cancelled == 0
        subagent.cancel.assert_not_called()

    def test_cancel_all_running_subagents(self) -> None:
        """Test cancel_all cancels running subagents."""
        coordinator = Coordinator()

        running1 = create_mock_subagent("task-1", SubagentStatus.RUNNING)
        running2 = create_mock_subagent("task-2", SubagentStatus.RUNNING)
        pending = create_mock_subagent("task-3", SubagentStatus.PENDING)

        coordinator.register_subagent(running1)
        coordinator.register_subagent(running2)
        coordinator.register_subagent(pending)

        cancelled = coordinator.cancel_all()

        assert cancelled == 2
        running1.cancel.assert_called_once()
        running2.cancel.assert_called_once()
        pending.cancel.assert_not_called()

    def test_clear(self) -> None:
        """Test clearing all subagents and artifacts."""
        coordinator = Coordinator()
        subagent = create_mock_subagent("task-1")
        coordinator.register_subagent(subagent)
        coordinator.store_artifact("task-1", "output", "data")

        coordinator.clear()

        assert coordinator.list_subagents() == []
        assert coordinator.collect_artifacts("task-1") == []
