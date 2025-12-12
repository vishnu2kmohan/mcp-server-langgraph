"""
MCP Tasks Feature (SEP-1686).

MCP 2025-11-25 adds experimental Tasks feature for tracking long-running
operations with status, progress, and result polling.

Tasks enable:
- Tracking long-running operations
- Progress updates and status polling
- Integration with LangGraph checkpoints
- Cancellation and cleanup

Reference: https://modelcontextprotocol.io/specification/2025-11-25
"""

import uuid
from datetime import datetime
from enum import Enum
from typing import Any

from pydantic import BaseModel, Field


class TaskStatus(str, Enum):
    """Status of an MCP task.

    States:
    - WORKING: Task is actively processing
    - INPUT_REQUIRED: Task needs user input to continue
    - COMPLETED: Task finished successfully
    - FAILED: Task failed with error
    - CANCELLED: Task was cancelled by user/system
    """

    WORKING = "working"
    INPUT_REQUIRED = "input_required"
    COMPLETED = "completed"
    FAILED = "failed"
    CANCELLED = "cancelled"


class Task(BaseModel):
    """MCP Task for tracking long-running operations.

    Integrates with LangGraph checkpoints for resumable workflows.
    """

    id: str
    operation: str
    status: TaskStatus
    progress: float = 0.0  # 0.0 to 1.0
    checkpoint_id: str | None = None  # Link to LangGraph checkpoint
    created_at: datetime = Field(default_factory=lambda: datetime.now(tz=None))
    updated_at: datetime = Field(default_factory=lambda: datetime.now(tz=None))
    result: Any | None = None
    error: str | None = None

    def to_api_response(self) -> dict[str, Any]:
        """Convert task to API response format."""
        response: dict[str, Any] = {
            "id": self.id,
            "operation": self.operation,
            "status": self.status.value,
            "progress": self.progress,
            "created_at": self.created_at.isoformat(),
            "updated_at": self.updated_at.isoformat(),
        }

        if self.checkpoint_id is not None:
            response["checkpoint_id"] = self.checkpoint_id

        if self.result is not None:
            response["result"] = self.result

        if self.error is not None:
            response["error"] = self.error

        return response


class TaskHandler:
    """Handler for managing MCP tasks.

    Provides in-memory task storage. For production, use Redis-backed
    implementation for persistence across restarts.
    """

    def __init__(self) -> None:
        """Initialize the task handler."""
        self._tasks: dict[str, Task] = {}

    def create_task(
        self,
        operation: str,
        checkpoint_id: str | None = None,
    ) -> Task:
        """Create a new task.

        Args:
            operation: Name of the operation being performed
            checkpoint_id: Optional LangGraph checkpoint ID

        Returns:
            New Task in WORKING status
        """
        task = Task(
            id=str(uuid.uuid4()),
            operation=operation,
            status=TaskStatus.WORKING,
            checkpoint_id=checkpoint_id,
        )
        self._tasks[task.id] = task
        return task

    def get_task(self, task_id: str) -> Task | None:
        """Get a task by ID.

        Args:
            task_id: Task identifier

        Returns:
            Task if found, None otherwise
        """
        return self._tasks.get(task_id)

    def update_status(self, task_id: str, status: TaskStatus) -> Task | None:
        """Update task status.

        Args:
            task_id: Task identifier
            status: New status

        Returns:
            Updated Task if found, None otherwise
        """
        task = self._tasks.get(task_id)
        if task is None:
            return None

        task.status = status
        task.updated_at = datetime.now(tz=None)
        return task

    def update_progress(self, task_id: str, progress: float) -> Task | None:
        """Update task progress.

        Args:
            task_id: Task identifier
            progress: Progress value (0.0 to 1.0)

        Returns:
            Updated Task if found, None otherwise
        """
        task = self._tasks.get(task_id)
        if task is None:
            return None

        task.progress = max(0.0, min(1.0, progress))
        task.updated_at = datetime.now(tz=None)
        return task

    def complete_task(self, task_id: str, result: Any = None) -> Task | None:
        """Complete a task with optional result.

        Args:
            task_id: Task identifier
            result: Task result data

        Returns:
            Completed Task if found, None otherwise
        """
        task = self._tasks.get(task_id)
        if task is None:
            return None

        task.status = TaskStatus.COMPLETED
        task.progress = 1.0
        task.result = result
        task.updated_at = datetime.now(tz=None)
        return task

    def fail_task(self, task_id: str, error: str) -> Task | None:
        """Fail a task with error message.

        Args:
            task_id: Task identifier
            error: Error message

        Returns:
            Failed Task if found, None otherwise
        """
        task = self._tasks.get(task_id)
        if task is None:
            return None

        task.status = TaskStatus.FAILED
        task.error = error
        task.updated_at = datetime.now(tz=None)
        return task

    def cancel_task(self, task_id: str) -> bool:
        """Cancel a task.

        Args:
            task_id: Task identifier

        Returns:
            True if task was cancelled, False if not found
        """
        task = self._tasks.get(task_id)
        if task is None:
            return False

        task.status = TaskStatus.CANCELLED
        task.updated_at = datetime.now(tz=None)
        return True

    def list_tasks(self, user_id: str | None = None) -> list[Task]:
        """List all tasks, optionally filtered by user.

        Args:
            user_id: Optional user ID to filter by (not implemented yet)

        Returns:
            List of tasks
        """
        # TODO: Add user filtering when auth is integrated
        return list(self._tasks.values())

    def cleanup_completed(self, max_age_seconds: int = 3600) -> int:
        """Remove old completed/failed/cancelled tasks.

        Args:
            max_age_seconds: Maximum age for completed tasks

        Returns:
            Number of tasks removed
        """
        now = datetime.now(tz=None)
        to_remove = []

        for task_id, task in self._tasks.items():
            if task.status in (
                TaskStatus.COMPLETED,
                TaskStatus.FAILED,
                TaskStatus.CANCELLED,
            ):
                age = (now - task.updated_at).total_seconds()
                if age > max_age_seconds:
                    to_remove.append(task_id)

        for task_id in to_remove:
            del self._tasks[task_id]

        return len(to_remove)
