"""
Orchestrator Status WebSocket Handler.

Provides real-time AI orchestrator status updates to the Studio frontend.
Broadcasts task progress (started, completed, failed) and overall status.

Features:
    - Real-time orchestrator status updates
    - Task lifecycle events (started, completed, failed)
    - Support for all task categories (UX, SESSION, CONVERSATION, etc.)
    - User-specific filtering for multi-tenant support
    - Automatic cleanup of disconnected subscribers

Message Types (Server -> Client):
    - orchestrator_status: Overall orchestrator status update
    - task_started: A task has started processing
    - task_completed: A task completed successfully
    - task_failed: A task failed with error
    - workflow_validation_started: Workflow validation has started
    - workflow_validation_passed: Workflow validation passed
    - workflow_validation_failed: Workflow validation failed
    - workflow_draft_saved: A workflow draft was saved
    - workflow_published: A workflow was published

Example Messages:
    orchestrator_status:
        {
            "type": "orchestrator_status",
            "payload": {
                "status": "processing",
                "message": "Analyzing persona...",
                "task_type": "persona_analysis",
                "category": "ux"
            }
        }

    task_started:
        {
            "type": "task_started",
            "payload": {
                "task_id": "uuid",
                "task_type": "error_analysis",
                "category": "ux",
                "started_at": "2025-12-29T10:00:00Z"
            }
        }
"""

from __future__ import annotations

import logging
from dataclasses import dataclass
from datetime import UTC, datetime
from enum import Enum
from typing import TYPE_CHECKING, Any, Protocol, runtime_checkable

from mcp_server_langgraph.websocket import orchestrator_prometheus_metrics as prom_metrics

from mcp_server_langgraph.websocket.base import WebSocketBase
from mcp_server_langgraph.websocket.mixins import BroadcasterMixin
from mcp_server_langgraph.websocket.types import (
    AuthUser,
    MessageEnvelope,
    WebSocketConfig,
)

if TYPE_CHECKING:
    from fastapi import WebSocket

    from mcp_server_langgraph.websocket.metrics import WebSocketMetrics

logger = logging.getLogger(__name__)


# =============================================================================
# Enums and Data Classes
# =============================================================================


class OrchestratorStatus(Enum):
    """Status values for the AI orchestrator."""

    IDLE = "idle"
    PROCESSING = "processing"
    ERROR = "error"


class TaskCategory(Enum):
    """Task categories matching StudioOrchestrator's TaskCategory enum."""

    UX = "ux"
    SESSION = "session"
    CONVERSATION = "conversation"
    CANVAS = "canvas"
    DIAGRAM = "diagram"
    TRACE = "trace"
    HITL = "hitl"
    COMMAND = "command"
    ALERT = "alert"
    WORKFLOW = "workflow"  # Workflow validation and lifecycle events


@dataclass
class TaskInfo:
    """Information about an orchestrator task."""

    task_id: str
    task_type: str
    category: TaskCategory
    started_at: datetime
    completed_at: datetime | None = None
    success: bool | None = None
    error: str | None = None
    progress: int | None = None  # 0-100 percentage

    def to_dict(self) -> dict[str, Any]:
        """Convert to dictionary for JSON serialization."""
        result = {
            "task_id": self.task_id,
            "task_type": self.task_type,
            "category": self.category.value,
            "started_at": self.started_at.isoformat(),
        }
        if self.completed_at is not None:
            result["completed_at"] = self.completed_at.isoformat()
        if self.success is not None:
            result["success"] = self.success
        if self.error is not None:
            result["error"] = self.error
        if self.progress is not None:
            result["progress"] = self.progress
        return result


# =============================================================================
# Broadcaster Implementation
# =============================================================================


class OrchestratorStatusBroadcaster:
    """
    Broadcaster for AI orchestrator status updates.

    Manages WebSocket subscriptions and broadcasts orchestrator status
    and task lifecycle events to connected clients.

    Usage:
        broadcaster = get_orchestrator_status_broadcaster()

        # Subscribe a client (typically done in WebSocket handler)
        await broadcaster.subscribe(websocket, user_id="user-123")

        # Broadcast status from orchestrator
        await broadcaster.broadcast_status(
            status=OrchestratorStatus.PROCESSING,
            message="Analyzing persona...",
            task_type="persona_analysis",
            category=TaskCategory.UX,
        )

        # Broadcast task lifecycle events
        await broadcaster.broadcast_task_started(task_info)
        await broadcaster.broadcast_task_completed(task_info)
        await broadcaster.broadcast_task_failed(task_info)

        # Unsubscribe when WebSocket disconnects
        await broadcaster.unsubscribe(websocket)
    """

    def __init__(self) -> None:
        """Initialize the broadcaster."""
        # Map of websocket -> user_id
        self._subscribers: dict[Any, str | None] = {}
        # Track active tasks for status queries on reconnect
        self._active_tasks: dict[str, TaskInfo] = {}
        # Track overall orchestrator status
        self._current_status: OrchestratorStatus = OrchestratorStatus.IDLE
        self._current_message: str | None = None
        # Metrics counters
        self._total_tasks_started: int = 0
        self._total_tasks_completed: int = 0
        self._total_tasks_failed: int = 0
        # Queue tracking (tasks waiting to start)
        self._queued_tasks: dict[str, dict[str, Any]] = {}

    @property
    def subscriber_count(self) -> int:
        """Get the number of active subscribers."""
        return len(self._subscribers)

    @property
    def active_task_count(self) -> int:
        """Get the number of currently active tasks."""
        return len(self._active_tasks)

    @property
    def current_status(self) -> OrchestratorStatus:
        """Get the current orchestrator status."""
        return self._current_status

    @property
    def queue_depth(self) -> int:
        """Get the number of tasks waiting in queue."""
        return len(self._queued_tasks)

    def get_status_snapshot(self) -> dict[str, Any]:
        """Get a snapshot of current orchestrator status for reconnecting clients.

        Returns:
            Dict with status, message, active task count, queue depth, and progress.
        """
        # Build progress map for active tasks
        active_progress: dict[str, int | None] = {}
        for task_id, task in self._active_tasks.items():
            if task.progress is not None:
                active_progress[task_id] = task.progress

        return {
            "status": self._current_status.value,
            "message": self._current_message,
            "activeTasks": len(self._active_tasks),
            "activeTaskTypes": [t.task_type for t in self._active_tasks.values()],
            "activeTaskProgress": active_progress,
            "queueDepth": len(self._queued_tasks),
        }

    def get_metrics(self) -> dict[str, int]:
        """Get metrics for Prometheus/monitoring integration.

        Returns:
            Dict with subscriber_count, active_task_count, queue_depth,
            and task lifecycle counters.
        """
        return {
            "subscriber_count": self.subscriber_count,
            "active_task_count": self.active_task_count,
            "queue_depth": self.queue_depth,
            "total_tasks_started": self._total_tasks_started,
            "total_tasks_completed": self._total_tasks_completed,
            "total_tasks_failed": self._total_tasks_failed,
        }

    async def subscribe(
        self,
        websocket: WebSocket,
        user_id: str | None = None,
    ) -> None:
        """
        Subscribe a WebSocket to orchestrator status updates.

        Args:
            websocket: The WebSocket connection to subscribe.
            user_id: Optional user ID for filtering broadcasts.
        """
        self._subscribers[websocket] = user_id
        prom_metrics.record_subscriber_change(1)
        logger.info(
            "Client subscribed to orchestrator status",
            extra={
                "user_id": user_id,
                "subscriber_count": len(self._subscribers),
            },
        )

    async def unsubscribe(self, websocket: WebSocket) -> None:
        """
        Unsubscribe a WebSocket from orchestrator status updates.

        Args:
            websocket: The WebSocket connection to unsubscribe.
        """
        if websocket in self._subscribers:
            user_id = self._subscribers.pop(websocket)
            prom_metrics.record_subscriber_change(-1)
            logger.info(
                "Client unsubscribed from orchestrator status",
                extra={
                    "user_id": user_id,
                    "subscriber_count": len(self._subscribers),
                },
            )

    async def _broadcast(
        self,
        message: dict[str, Any],
        user_id: str | None = None,
    ) -> None:
        """
        Broadcast a message to subscribers.

        Args:
            message: The message to broadcast.
            user_id: Optional user ID to filter recipients.
        """
        failed_subscribers: list[Any] = []

        for websocket, sub_user_id in list(self._subscribers.items()):
            # Filter by user if specified
            if user_id and sub_user_id and sub_user_id != user_id:
                continue

            try:
                await websocket.send_json(message)
            except Exception as e:
                logger.warning(
                    "Failed to send orchestrator status, removing subscriber",
                    extra={
                        "error": str(e),
                        "user_id": sub_user_id,
                    },
                )
                failed_subscribers.append(websocket)

        # Remove failed subscribers
        for ws in failed_subscribers:
            self._subscribers.pop(ws, None)

    async def broadcast_status(
        self,
        status: OrchestratorStatus,
        message: str | None = None,
        task_type: str | None = None,
        category: TaskCategory | None = None,
        user_id: str | None = None,
    ) -> None:
        """
        Broadcast an orchestrator status update.

        Args:
            status: Current orchestrator status.
            message: Optional human-readable status message.
            task_type: Optional task type being processed.
            category: Optional task category.
            user_id: Optional user ID to filter recipients.
        """
        # Track current status for reconnecting clients
        self._current_status = status
        self._current_message = message

        payload: dict[str, Any] = {"status": status.value}
        if message is not None:
            payload["message"] = message
        if task_type is not None:
            payload["task_type"] = task_type
        if category is not None:
            payload["category"] = category.value

        await self._broadcast(
            {"type": "orchestrator_status", "payload": payload},
            user_id=user_id,
        )

    async def broadcast_task_started(
        self,
        task_info: TaskInfo,
        user_id: str | None = None,
    ) -> None:
        """
        Broadcast a task started event.

        Args:
            task_info: Information about the started task.
            user_id: Optional user ID to filter recipients.
        """
        # Track active task for status queries on reconnect
        self._active_tasks[task_info.task_id] = task_info
        # Update metrics counter
        self._total_tasks_started += 1
        # Remove from queue if it was queued
        self._queued_tasks.pop(task_info.task_id, None)
        # Update Prometheus metrics
        prom_metrics.record_task_started(
            category=task_info.category.value,
            task_type=task_info.task_type,
        )
        prom_metrics.set_queue_depth(len(self._queued_tasks))

        await self._broadcast(
            {
                "type": "task_started",
                "payload": {
                    "task_id": task_info.task_id,
                    "task_type": task_info.task_type,
                    "category": task_info.category.value,
                    "started_at": task_info.started_at.isoformat(),
                },
            },
            user_id=user_id,
        )

    async def broadcast_task_completed(
        self,
        task_info: TaskInfo,
        user_id: str | None = None,
    ) -> None:
        """
        Broadcast a task completed event.

        Args:
            task_info: Information about the completed task.
            user_id: Optional user ID to filter recipients.
        """
        # Remove task from active tracking
        self._active_tasks.pop(task_info.task_id, None)
        # Update metrics counter
        self._total_tasks_completed += 1
        # Update Prometheus metrics
        prom_metrics.record_task_completed(
            category=task_info.category.value,
            task_type=task_info.task_type,
        )

        completed_at = task_info.completed_at or datetime.now(UTC)
        await self._broadcast(
            {
                "type": "task_completed",
                "payload": {
                    "task_id": task_info.task_id,
                    "task_type": task_info.task_type,
                    "category": task_info.category.value,
                    "completed_at": completed_at.isoformat(),
                    "success": task_info.success,
                },
            },
            user_id=user_id,
        )

    async def broadcast_task_failed(
        self,
        task_info: TaskInfo,
        user_id: str | None = None,
    ) -> None:
        """
        Broadcast a task failed event.

        Args:
            task_info: Information about the failed task.
            user_id: Optional user ID to filter recipients.
        """
        # Remove task from active tracking
        self._active_tasks.pop(task_info.task_id, None)
        # Update metrics counter
        self._total_tasks_failed += 1
        # Update Prometheus metrics
        prom_metrics.record_task_failed(
            category=task_info.category.value,
            task_type=task_info.task_type,
            reason=task_info.error or "unknown",
        )

        failed_at = task_info.completed_at or datetime.now(UTC)
        await self._broadcast(
            {
                "type": "task_failed",
                "payload": {
                    "task_id": task_info.task_id,
                    "task_type": task_info.task_type,
                    "category": task_info.category.value,
                    "failed_at": failed_at.isoformat(),
                    "error": task_info.error,
                },
            },
            user_id=user_id,
        )

    async def broadcast_task_progress(
        self,
        task_id: str,
        progress: int,
        message: str | None = None,
        user_id: str | None = None,
    ) -> None:
        """
        Broadcast a task progress update.

        Args:
            task_id: The task ID being updated.
            progress: Progress percentage (0-100).
            message: Optional progress message.
            user_id: Optional user ID to filter recipients.
        """
        # Update the task's progress if it's active
        if task_id in self._active_tasks:
            self._active_tasks[task_id].progress = progress

        payload: dict[str, Any] = {
            "task_id": task_id,
            "progress": progress,
        }
        if message is not None:
            payload["message"] = message

        await self._broadcast(
            {"type": "task_progress", "payload": payload},
            user_id=user_id,
        )

    async def queue_task(
        self,
        task_id: str,
        task_type: str,
        category: TaskCategory,
        user_id: str | None = None,
    ) -> None:
        """
        Add a task to the queue (before it starts processing).

        Args:
            task_id: The task ID.
            task_type: The type of task.
            category: The task category.
            user_id: Optional user ID to filter broadcasts.
        """
        self._queued_tasks[task_id] = {
            "task_id": task_id,
            "task_type": task_type,
            "category": category.value,
            "queued_at": datetime.now(UTC).isoformat(),
        }
        # Update Prometheus queue depth
        prom_metrics.set_queue_depth(len(self._queued_tasks))

        await self._broadcast(
            {
                "type": "queue_update",
                "payload": {
                    "action": "added",
                    "task_id": task_id,
                    "task_type": task_type,
                    "category": category.value,
                    "queue_depth": len(self._queued_tasks),
                },
            },
            user_id=user_id,
        )

    # =========================================================================
    # Workflow Validation Events (Chat-to-Workflow Feature)
    # =========================================================================

    async def broadcast_workflow_validation_started(
        self,
        workflow_id: str,
        user_id: str | None = None,
    ) -> None:
        """
        Broadcast that workflow validation has started.

        Args:
            workflow_id: The workflow being validated.
            user_id: Optional user ID to filter recipients.
        """
        await self._broadcast(
            {
                "type": "workflow_validation_started",
                "payload": {
                    "workflow_id": workflow_id,
                    "started_at": datetime.now(UTC).isoformat(),
                },
            },
            user_id=user_id,
        )

    async def broadcast_workflow_validation_passed(
        self,
        workflow_id: str,
        warnings: list[str] | None = None,
        user_id: str | None = None,
    ) -> None:
        """
        Broadcast that workflow validation passed.

        Args:
            workflow_id: The workflow that was validated.
            warnings: Optional list of validation warnings.
            user_id: Optional user ID to filter recipients.
        """
        payload: dict[str, Any] = {
            "workflow_id": workflow_id,
            "valid": True,
            "completed_at": datetime.now(UTC).isoformat(),
        }
        if warnings:
            payload["warnings"] = warnings

        await self._broadcast(
            {"type": "workflow_validation_passed", "payload": payload},
            user_id=user_id,
        )

    async def broadcast_workflow_validation_failed(
        self,
        workflow_id: str,
        errors: list[str],
        warnings: list[str] | None = None,
        user_id: str | None = None,
    ) -> None:
        """
        Broadcast that workflow validation failed.

        Args:
            workflow_id: The workflow that was validated.
            errors: List of validation errors.
            warnings: Optional list of validation warnings.
            user_id: Optional user ID to filter recipients.
        """
        payload: dict[str, Any] = {
            "workflow_id": workflow_id,
            "valid": False,
            "errors": errors,
            "completed_at": datetime.now(UTC).isoformat(),
        }
        if warnings:
            payload["warnings"] = warnings

        await self._broadcast(
            {"type": "workflow_validation_failed", "payload": payload},
            user_id=user_id,
        )

    async def broadcast_workflow_draft_saved(
        self,
        workflow_id: str,
        version: int,
        user_id: str | None = None,
    ) -> None:
        """
        Broadcast that a workflow draft was saved.

        Args:
            workflow_id: The workflow that was saved.
            version: The version number of the saved draft.
            user_id: Optional user ID to filter recipients.
        """
        await self._broadcast(
            {
                "type": "workflow_draft_saved",
                "payload": {
                    "workflow_id": workflow_id,
                    "version": version,
                    "saved_at": datetime.now(UTC).isoformat(),
                },
            },
            user_id=user_id,
        )

    async def broadcast_workflow_published(
        self,
        workflow_id: str,
        version: int,
        user_id: str | None = None,
    ) -> None:
        """
        Broadcast that a workflow was published.

        Args:
            workflow_id: The workflow that was published.
            version: The version number that was published.
            user_id: Optional user ID to filter recipients.
        """
        await self._broadcast(
            {
                "type": "workflow_published",
                "payload": {
                    "workflow_id": workflow_id,
                    "version": version,
                    "published_at": datetime.now(UTC).isoformat(),
                },
            },
            user_id=user_id,
        )


# =============================================================================
# Singleton Instance
# =============================================================================

_broadcaster: OrchestratorStatusBroadcaster | None = None


def get_orchestrator_status_broadcaster() -> OrchestratorStatusBroadcaster:
    """
    Get the application-wide orchestrator status broadcaster instance.

    Returns:
        Singleton OrchestratorStatusBroadcaster instance.
    """
    global _broadcaster
    if _broadcaster is None:
        _broadcaster = OrchestratorStatusBroadcaster()
    return _broadcaster


def reset_orchestrator_status_broadcaster() -> None:
    """Reset the orchestrator status broadcaster (for testing)."""
    global _broadcaster
    _broadcaster = None


# =============================================================================
# Broadcaster Protocol
# =============================================================================


@runtime_checkable
class OrchestratorStatusBroadcasterProtocol(Protocol):
    """Protocol defining the orchestrator status broadcaster interface.

    This protocol defines all methods that StudioOrchestrator and other
    orchestrators may call to broadcast status updates to WebSocket clients.
    """

    async def subscribe(
        self,
        websocket: WebSocket,
        user_id: str | None = None,
    ) -> None:
        """Subscribe to orchestrator status updates."""
        ...

    async def unsubscribe(self, websocket: WebSocket) -> None:
        """Unsubscribe from orchestrator status updates."""
        ...

    async def broadcast_status(
        self,
        status: OrchestratorStatus,
        message: str | None = None,
        task_type: str | None = None,
        category: TaskCategory | None = None,
        user_id: str | None = None,
    ) -> None:
        """Broadcast an orchestrator status update."""
        ...

    async def broadcast_task_started(
        self,
        task_info: TaskInfo,
        user_id: str | None = None,
    ) -> None:
        """Broadcast a task started event."""
        ...

    async def broadcast_task_completed(
        self,
        task_info: TaskInfo,
        user_id: str | None = None,
    ) -> None:
        """Broadcast a task completed event."""
        ...

    async def broadcast_task_failed(
        self,
        task_info: TaskInfo,
        user_id: str | None = None,
    ) -> None:
        """Broadcast a task failed event."""
        ...

    async def broadcast_task_progress(
        self,
        task_id: str,
        progress: int,
        message: str | None = None,
        user_id: str | None = None,
    ) -> None:
        """Broadcast a task progress update."""
        ...

    async def queue_task(
        self,
        task_id: str,
        task_type: str,
        category: TaskCategory,
        user_id: str | None = None,
    ) -> None:
        """Add a task to the queue."""
        ...

    def get_status_snapshot(self) -> dict[str, Any]:
        """Get a snapshot of current orchestrator status for reconnecting clients."""
        ...

    def get_metrics(self) -> dict[str, int]:
        """Get metrics for monitoring integration."""
        ...

    @property
    def queue_depth(self) -> int:
        """Get the number of tasks waiting in queue."""
        ...


# =============================================================================
# WebSocket Handler
# =============================================================================


class OrchestratorStatusHandler(WebSocketBase, BroadcasterMixin):
    """
    WebSocket handler for real-time AI orchestrator status updates.

    Extends WebSocketBase to provide orchestrator status streaming with the
    standardized infrastructure (auth, rate limiting, metrics, etc.).

    This is a pub/sub handler where:
    1. Clients subscribe on connect
    2. The broadcaster pushes status updates to clients
    3. Clients can request current status via get_status message

    Message Types (Client -> Server):
        - subscribe: Subscribe to status updates
        - unsubscribe: Unsubscribe from status updates
        - get_status: Request current orchestrator status

    Response Types (Server -> Client):
        - subscribed: Successfully subscribed
        - unsubscribed: Successfully unsubscribed
        - status: Current orchestrator status
        - orchestrator_status: Real-time status update (pushed)
        - task_started: Task started (pushed)
        - task_completed: Task completed (pushed)
        - task_failed: Task failed (pushed)

    Usage:
        handler = OrchestratorStatusHandler(
            config=WebSocketConfig(
                endpoint_name="orchestrator-status",
                require_auth=True,
                authz_resource_type="ai",
                authz_resource_id="orchestrator",
                authz_required_relation="viewer",
            ),
            broadcaster=get_orchestrator_status_broadcaster(),
        )
        await handler.run(websocket)
    """

    def __init__(
        self,
        config: WebSocketConfig,
        broadcaster: OrchestratorStatusBroadcasterProtocol | None = None,
        metrics: WebSocketMetrics | None = None,
    ) -> None:
        """
        Initialize the orchestrator status handler.

        Args:
            config: WebSocket configuration.
            broadcaster: Broadcaster for managing subscriptions. Uses singleton if not provided.
            metrics: Optional metrics collector.
        """
        super().__init__(config=config, metrics=metrics)
        self._broadcaster = broadcaster or get_orchestrator_status_broadcaster()
        # Note: _subscribed is managed by BroadcasterMixin

    async def on_connect(self, user: AuthUser) -> None:
        """
        Handle connection establishment.

        Subscribes the client to the orchestrator status broadcaster.

        Args:
            user: The authenticated user.
        """
        if self._websocket:
            # Use BroadcasterMixin's subscribe() with user_id kwarg
            await self.subscribe(user_id=self.user_id)
            logger.info(
                f"Orchestrator status stream connected: user={self.user_id}",
                extra={"user_id": self.user_id},
            )

    async def on_disconnect(self) -> None:
        """
        Handle connection teardown.

        Unsubscribes the client from the orchestrator status broadcaster.
        """
        # Use BroadcasterMixin's unsubscribe() for cleanup
        await self.unsubscribe()
        logger.info(
            f"Orchestrator status stream disconnected: user={self.user_id}",
            extra={"user_id": self.user_id},
        )

    async def handle_message(self, message: MessageEnvelope) -> MessageEnvelope | None:
        """
        Handle incoming messages.

        Supports subscribe, unsubscribe, and get_status messages.

        Args:
            message: The incoming message envelope.

        Returns:
            Response envelope or None.
        """
        logger.debug(
            f"Received message type: {message.type}",
            extra={"message_type": message.type, "user_id": self.user_id},
        )

        if message.type == "subscribe":
            if self._websocket and not self._subscribed:
                # Use BroadcasterMixin's subscribe()
                await self.subscribe(user_id=self.user_id)

            return self.create_subscribed_response(
                correlation_id=message.id,
                extra_payload={"status": "subscribed"},
            )

        elif message.type == "unsubscribe":
            # Use BroadcasterMixin's unsubscribe()
            await self.unsubscribe()

            return self.create_unsubscribed_response(
                correlation_id=message.id,
                extra_payload={"status": "unsubscribed"},
            )

        elif message.type == "get_status":
            # Return current orchestrator status from broadcaster
            status_snapshot = self._broadcaster.get_status_snapshot()
            return MessageEnvelope(
                type="status",
                id=message.id,
                payload=status_snapshot,
            )

        # Unknown message types return None (handled by base class)
        return None
