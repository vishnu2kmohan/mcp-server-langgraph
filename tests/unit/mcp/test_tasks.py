"""
Tests for MCP Tasks Feature (SEP-1686).

MCP 2025-11-25 adds experimental Tasks feature for tracking long-running
operations with status, progress, and result polling.

TDD: RED phase - Define expected behavior for SEP-1686 implementation.
"""

import gc

import pytest

pytestmark = pytest.mark.unit


@pytest.mark.xdist_group(name="mcp_tasks")
class TestTaskStatus:
    """Test TaskStatus enum values."""

    def teardown_method(self) -> None:
        """Clean up after each test."""
        gc.collect()

    def test_task_status_values(self) -> None:
        """TaskStatus should have all required states."""
        from mcp_server_langgraph.mcp.tasks import TaskStatus

        assert TaskStatus.WORKING == "working"
        assert TaskStatus.INPUT_REQUIRED == "input_required"
        assert TaskStatus.COMPLETED == "completed"
        assert TaskStatus.FAILED == "failed"
        assert TaskStatus.CANCELLED == "cancelled"


@pytest.mark.xdist_group(name="mcp_tasks")
class TestTaskModel:
    """Test Task model."""

    def teardown_method(self) -> None:
        """Clean up after each test."""
        gc.collect()

    def test_task_creation_with_required_fields(self) -> None:
        """Task should be created with required fields."""
        from mcp_server_langgraph.mcp.tasks import Task, TaskStatus

        task = Task(
            id="task-123",
            operation="code_execution",
            status=TaskStatus.WORKING,
        )

        assert task.id == "task-123"
        assert task.operation == "code_execution"
        assert task.status == TaskStatus.WORKING
        assert task.progress == 0.0
        assert task.result is None
        assert task.error is None

    def test_task_with_progress(self) -> None:
        """Task should track progress 0.0 to 1.0."""
        from mcp_server_langgraph.mcp.tasks import Task, TaskStatus

        task = Task(
            id="task-456",
            operation="data_processing",
            status=TaskStatus.WORKING,
            progress=0.75,
        )

        assert task.progress == 0.75

    def test_task_with_checkpoint_id(self) -> None:
        """Task should link to LangGraph checkpoint."""
        from mcp_server_langgraph.mcp.tasks import Task, TaskStatus

        task = Task(
            id="task-789",
            operation="agent_workflow",
            status=TaskStatus.WORKING,
            checkpoint_id="checkpoint-abc123",
        )

        assert task.checkpoint_id == "checkpoint-abc123"

    def test_task_with_result(self) -> None:
        """Completed task should have result."""
        from mcp_server_langgraph.mcp.tasks import Task, TaskStatus

        task = Task(
            id="task-completed",
            operation="compute",
            status=TaskStatus.COMPLETED,
            progress=1.0,
            result={"output": "success", "value": 42},
        )

        assert task.status == TaskStatus.COMPLETED
        assert task.result == {"output": "success", "value": 42}

    def test_task_with_error(self) -> None:
        """Failed task should have error message."""
        from mcp_server_langgraph.mcp.tasks import Task, TaskStatus

        task = Task(
            id="task-failed",
            operation="risky_operation",
            status=TaskStatus.FAILED,
            error="Connection timeout after 30 seconds",
        )

        assert task.status == TaskStatus.FAILED
        assert "timeout" in task.error.lower()


@pytest.mark.xdist_group(name="mcp_tasks")
class TestTaskHandler:
    """Test TaskHandler for managing task lifecycle."""

    def teardown_method(self) -> None:
        """Clean up after each test."""
        gc.collect()

    def test_create_task_returns_working_task(self) -> None:
        """TaskHandler should create new tasks."""
        from mcp_server_langgraph.mcp.tasks import TaskHandler

        handler = TaskHandler()
        task = handler.create_task("code_execution")

        assert task.id is not None
        assert task.operation == "code_execution"
        assert task.status.value == "working"
        assert task.progress == 0.0

    def test_get_task_returns_created_task(self) -> None:
        """TaskHandler should retrieve tasks by ID."""
        from mcp_server_langgraph.mcp.tasks import TaskHandler

        handler = TaskHandler()
        created = handler.create_task("test_op")

        retrieved = handler.get_task(created.id)

        assert retrieved is not None
        assert retrieved.id == created.id

    def test_get_task_not_found(self) -> None:
        """TaskHandler should return None for unknown task."""
        from mcp_server_langgraph.mcp.tasks import TaskHandler

        handler = TaskHandler()
        result = handler.get_task("nonexistent-task-id")

        assert result is None

    def test_update_status_changes_task_state(self) -> None:
        """TaskHandler should update task status."""
        from mcp_server_langgraph.mcp.tasks import TaskHandler, TaskStatus

        handler = TaskHandler()
        task = handler.create_task("workflow")

        handler.update_status(task.id, TaskStatus.INPUT_REQUIRED)

        updated = handler.get_task(task.id)
        assert updated is not None
        assert updated.status == TaskStatus.INPUT_REQUIRED

    def test_update_progress_sets_new_value(self) -> None:
        """TaskHandler should update task progress."""
        from mcp_server_langgraph.mcp.tasks import TaskHandler

        handler = TaskHandler()
        task = handler.create_task("processing")

        handler.update_progress(task.id, 0.5)

        updated = handler.get_task(task.id)
        assert updated is not None
        assert updated.progress == 0.5

    def test_complete_task_sets_completed_status(self) -> None:
        """TaskHandler should complete task with result."""
        from mcp_server_langgraph.mcp.tasks import TaskHandler, TaskStatus

        handler = TaskHandler()
        task = handler.create_task("compute")

        handler.complete_task(task.id, result={"answer": 42})

        completed = handler.get_task(task.id)
        assert completed is not None
        assert completed.status == TaskStatus.COMPLETED
        assert completed.progress == 1.0
        assert completed.result == {"answer": 42}

    def test_fail_task_sets_failed_status(self) -> None:
        """TaskHandler should fail task with error."""
        from mcp_server_langgraph.mcp.tasks import TaskHandler, TaskStatus

        handler = TaskHandler()
        task = handler.create_task("risky")

        handler.fail_task(task.id, error="Something went wrong")

        failed = handler.get_task(task.id)
        assert failed is not None
        assert failed.status == TaskStatus.FAILED
        assert failed.error == "Something went wrong"

    def test_cancel_task_sets_cancelled_status(self) -> None:
        """TaskHandler should cancel task."""
        from mcp_server_langgraph.mcp.tasks import TaskHandler, TaskStatus

        handler = TaskHandler()
        task = handler.create_task("long_running")

        result = handler.cancel_task(task.id)

        assert result is True
        cancelled = handler.get_task(task.id)
        assert cancelled is not None
        assert cancelled.status == TaskStatus.CANCELLED

    def test_list_tasks_returns_all_tasks(self) -> None:
        """TaskHandler should list all tasks."""
        from mcp_server_langgraph.mcp.tasks import TaskHandler

        handler = TaskHandler()
        handler.create_task("task1")
        handler.create_task("task2")
        handler.create_task("task3")

        tasks = handler.list_tasks()

        assert len(tasks) == 3


@pytest.mark.xdist_group(name="mcp_tasks")
class TestTaskSerialization:
    """Test Task serialization for API responses."""

    def teardown_method(self) -> None:
        """Clean up after each test."""
        gc.collect()

    def test_task_to_dict(self) -> None:
        """Task should serialize to dict."""
        from mcp_server_langgraph.mcp.tasks import Task, TaskStatus

        task = Task(
            id="serialize-test",
            operation="test",
            status=TaskStatus.WORKING,
            progress=0.25,
        )

        data = task.model_dump()

        assert data["id"] == "serialize-test"
        assert data["operation"] == "test"
        assert data["status"] == "working"
        assert data["progress"] == 0.25

    def test_task_to_api_response(self) -> None:
        """Task should format for API response."""
        from mcp_server_langgraph.mcp.tasks import Task, TaskStatus

        task = Task(
            id="api-test",
            operation="api_call",
            status=TaskStatus.COMPLETED,
            progress=1.0,
            result={"data": "response"},
        )

        response = task.to_api_response()

        assert response["id"] == "api-test"
        assert response["status"] == "completed"
        assert "result" in response
