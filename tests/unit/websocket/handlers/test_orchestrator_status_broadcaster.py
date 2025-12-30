"""
OrchestratorStatusBroadcaster Unit Tests.

TDD tests for broadcasting AI orchestrator status updates to WebSocket clients.
Following the pattern from test_devtools.py and test_trace_broadcaster.py.
"""

from __future__ import annotations

from datetime import UTC, datetime
from unittest.mock import AsyncMock

import pytest

from mcp_server_langgraph.websocket.handlers.orchestrator_status import (
    OrchestratorStatus,
    OrchestratorStatusBroadcaster,
    OrchestratorStatusHandler,
    OrchestratorStatusBroadcasterProtocol,
    TaskCategory,
    TaskInfo,
    get_orchestrator_status_broadcaster,
    reset_orchestrator_status_broadcaster,
)
from mcp_server_langgraph.websocket.types import (
    AuthUser,
    MessageEnvelope,
    WebSocketConfig,
)

pytestmark = [pytest.mark.unit, pytest.mark.websocket]


class TestOrchestratorStatusBroadcaster:
    """Test suite for OrchestratorStatusBroadcaster."""

    def setup_method(self) -> None:
        """Reset broadcaster before each test."""
        reset_orchestrator_status_broadcaster()

    def teardown_method(self) -> None:
        """Clean up after each test."""
        reset_orchestrator_status_broadcaster()

    # =========================================================================
    # Subscription Tests
    # =========================================================================

    @pytest.mark.asyncio
    async def test_subscribe_adds_websocket(self) -> None:
        """Subscribing adds WebSocket to subscribers list."""
        broadcaster = OrchestratorStatusBroadcaster()
        ws = AsyncMock()

        await broadcaster.subscribe(ws, user_id="user-123")

        assert broadcaster.subscriber_count == 1

    @pytest.mark.asyncio
    async def test_unsubscribe_removes_websocket(self) -> None:
        """Unsubscribing removes WebSocket from subscribers list."""
        broadcaster = OrchestratorStatusBroadcaster()
        ws = AsyncMock()

        await broadcaster.subscribe(ws, user_id="user-123")
        await broadcaster.unsubscribe(ws)

        assert broadcaster.subscriber_count == 0

    @pytest.mark.asyncio
    async def test_multiple_subscribers(self) -> None:
        """Multiple WebSockets can subscribe."""
        broadcaster = OrchestratorStatusBroadcaster()
        ws1 = AsyncMock()
        ws2 = AsyncMock()
        ws3 = AsyncMock()

        await broadcaster.subscribe(ws1, user_id="user-1")
        await broadcaster.subscribe(ws2, user_id="user-2")
        await broadcaster.subscribe(ws3, user_id="user-3")

        assert broadcaster.subscriber_count == 3

    @pytest.mark.asyncio
    async def test_unsubscribe_nonexistent_does_nothing(self) -> None:
        """Unsubscribing a non-subscribed WebSocket doesn't error."""
        broadcaster = OrchestratorStatusBroadcaster()
        ws = AsyncMock()

        # Should not raise
        await broadcaster.unsubscribe(ws)

        assert broadcaster.subscriber_count == 0

    # =========================================================================
    # Broadcast Status Tests
    # =========================================================================

    @pytest.mark.asyncio
    async def test_broadcast_orchestrator_status(self) -> None:
        """Broadcasting status sends to all subscribers."""
        broadcaster = OrchestratorStatusBroadcaster()
        ws1 = AsyncMock()
        ws2 = AsyncMock()

        await broadcaster.subscribe(ws1, user_id="user-1")
        await broadcaster.subscribe(ws2, user_id="user-2")

        await broadcaster.broadcast_status(
            status=OrchestratorStatus.PROCESSING,
            message="Analyzing persona...",
            task_type="persona_analysis",
            category=TaskCategory.UX,
        )

        # Both WebSockets should receive the message
        ws1.send_json.assert_called_once()
        ws2.send_json.assert_called_once()

        # Check message structure
        call_args = ws1.send_json.call_args[0][0]
        assert call_args["type"] == "orchestrator_status"
        assert call_args["payload"]["status"] == "processing"
        assert call_args["payload"]["message"] == "Analyzing persona..."
        assert call_args["payload"]["task_type"] == "persona_analysis"
        assert call_args["payload"]["category"] == "ux"

    @pytest.mark.asyncio
    async def test_broadcast_task_started(self) -> None:
        """Broadcasting task_started sends correct message."""
        broadcaster = OrchestratorStatusBroadcaster()
        ws = AsyncMock()

        await broadcaster.subscribe(ws, user_id="user-1")

        task_info = TaskInfo(
            task_id="task-123",
            task_type="error_analysis",
            category=TaskCategory.UX,
            started_at=datetime.now(UTC),
        )
        await broadcaster.broadcast_task_started(task_info)

        ws.send_json.assert_called_once()
        call_args = ws.send_json.call_args[0][0]
        assert call_args["type"] == "task_started"
        assert call_args["payload"]["task_id"] == "task-123"
        assert call_args["payload"]["task_type"] == "error_analysis"
        assert call_args["payload"]["category"] == "ux"
        assert "started_at" in call_args["payload"]

    @pytest.mark.asyncio
    async def test_broadcast_task_completed(self) -> None:
        """Broadcasting task_completed sends correct message."""
        broadcaster = OrchestratorStatusBroadcaster()
        ws = AsyncMock()

        await broadcaster.subscribe(ws, user_id="user-1")

        task_info = TaskInfo(
            task_id="task-456",
            task_type="disclosure_analysis",
            category=TaskCategory.UX,
            started_at=datetime.now(UTC),
            completed_at=datetime.now(UTC),
            success=True,
        )
        await broadcaster.broadcast_task_completed(task_info)

        ws.send_json.assert_called_once()
        call_args = ws.send_json.call_args[0][0]
        assert call_args["type"] == "task_completed"
        assert call_args["payload"]["task_id"] == "task-456"
        assert call_args["payload"]["success"] is True
        assert "completed_at" in call_args["payload"]

    @pytest.mark.asyncio
    async def test_broadcast_task_failed(self) -> None:
        """Broadcasting task_failed sends correct message."""
        broadcaster = OrchestratorStatusBroadcaster()
        ws = AsyncMock()

        await broadcaster.subscribe(ws, user_id="user-1")

        task_info = TaskInfo(
            task_id="task-789",
            task_type="nudge_recommendation",
            category=TaskCategory.UX,
            started_at=datetime.now(UTC),
            completed_at=datetime.now(UTC),
            success=False,
            error="LLM rate limit exceeded",
        )
        await broadcaster.broadcast_task_failed(task_info)

        ws.send_json.assert_called_once()
        call_args = ws.send_json.call_args[0][0]
        assert call_args["type"] == "task_failed"
        assert call_args["payload"]["task_id"] == "task-789"
        assert call_args["payload"]["error"] == "LLM rate limit exceeded"
        assert "failed_at" in call_args["payload"]

    # =========================================================================
    # Error Handling Tests
    # =========================================================================

    @pytest.mark.asyncio
    async def test_failed_send_removes_subscriber(self) -> None:
        """Failed WebSocket send removes the subscriber."""
        broadcaster = OrchestratorStatusBroadcaster()
        ws = AsyncMock()
        ws.send_json.side_effect = Exception("Connection closed")

        await broadcaster.subscribe(ws, user_id="user-1")

        await broadcaster.broadcast_status(
            status=OrchestratorStatus.IDLE,
            message=None,
        )

        # Subscriber should be removed after failed send
        assert broadcaster.subscriber_count == 0

    @pytest.mark.asyncio
    async def test_one_failed_subscriber_doesnt_affect_others(self) -> None:
        """One failed subscriber doesn't prevent others from receiving."""
        broadcaster = OrchestratorStatusBroadcaster()
        ws1 = AsyncMock()
        ws1.send_json.side_effect = Exception("Connection closed")
        ws2 = AsyncMock()

        await broadcaster.subscribe(ws1, user_id="user-1")
        await broadcaster.subscribe(ws2, user_id="user-2")

        await broadcaster.broadcast_status(
            status=OrchestratorStatus.PROCESSING,
            message="Test",
        )

        # ws1 failed, but ws2 should still receive
        ws2.send_json.assert_called_once()
        assert broadcaster.subscriber_count == 1

    # =========================================================================
    # User Filtering Tests
    # =========================================================================

    @pytest.mark.asyncio
    async def test_broadcast_to_specific_user(self) -> None:
        """Broadcasting to specific user only sends to that user."""
        broadcaster = OrchestratorStatusBroadcaster()
        ws1 = AsyncMock()
        ws2 = AsyncMock()

        await broadcaster.subscribe(ws1, user_id="user-1")
        await broadcaster.subscribe(ws2, user_id="user-2")

        await broadcaster.broadcast_status(
            status=OrchestratorStatus.PROCESSING,
            message="User-specific task",
            user_id="user-1",
        )

        # Only ws1 should receive
        ws1.send_json.assert_called_once()
        ws2.send_json.assert_not_called()

    @pytest.mark.asyncio
    async def test_broadcast_to_all_users_when_no_filter(self) -> None:
        """Broadcasting without user filter sends to all."""
        broadcaster = OrchestratorStatusBroadcaster()
        ws1 = AsyncMock()
        ws2 = AsyncMock()

        await broadcaster.subscribe(ws1, user_id="user-1")
        await broadcaster.subscribe(ws2, user_id="user-2")

        await broadcaster.broadcast_status(
            status=OrchestratorStatus.IDLE,
            message=None,
        )

        # Both should receive
        ws1.send_json.assert_called_once()
        ws2.send_json.assert_called_once()

    # =========================================================================
    # Task Category Tests
    # =========================================================================

    @pytest.mark.parametrize(
        "category",
        [
            TaskCategory.UX,
            TaskCategory.SESSION,
            TaskCategory.CONVERSATION,
            TaskCategory.CANVAS,
            TaskCategory.DIAGRAM,
            TaskCategory.TRACE,
            TaskCategory.HITL,
            TaskCategory.COMMAND,
        ],
    )
    @pytest.mark.asyncio
    async def test_all_task_categories_broadcast(self, category: TaskCategory) -> None:
        """All task categories can be broadcast."""
        broadcaster = OrchestratorStatusBroadcaster()
        ws = AsyncMock()

        await broadcaster.subscribe(ws, user_id="user-1")

        task_info = TaskInfo(
            task_id=f"task-{category.value}",
            task_type="test_task",
            category=category,
            started_at=datetime.now(UTC),
        )
        await broadcaster.broadcast_task_started(task_info)

        ws.send_json.assert_called_once()
        call_args = ws.send_json.call_args[0][0]
        assert call_args["payload"]["category"] == category.value

    # =========================================================================
    # Singleton Tests
    # =========================================================================

    def test_singleton_returns_same_instance(self) -> None:
        """get_orchestrator_status_broadcaster returns singleton."""
        reset_orchestrator_status_broadcaster()

        broadcaster1 = get_orchestrator_status_broadcaster()
        broadcaster2 = get_orchestrator_status_broadcaster()

        assert broadcaster1 is broadcaster2

    def test_reset_creates_new_instance(self) -> None:
        """reset_orchestrator_status_broadcaster creates new instance."""
        broadcaster1 = get_orchestrator_status_broadcaster()
        reset_orchestrator_status_broadcaster()
        broadcaster2 = get_orchestrator_status_broadcaster()

        assert broadcaster1 is not broadcaster2


class TestTaskInfo:
    """Test suite for TaskInfo dataclass."""

    def test_task_info_creation(self) -> None:
        """TaskInfo can be created with required fields."""
        now = datetime.now(UTC)
        task = TaskInfo(
            task_id="task-123",
            task_type="persona_analysis",
            category=TaskCategory.UX,
            started_at=now,
        )

        assert task.task_id == "task-123"
        assert task.task_type == "persona_analysis"
        assert task.category == TaskCategory.UX
        assert task.started_at == now
        assert task.completed_at is None
        assert task.success is None
        assert task.error is None

    def test_task_info_with_completion(self) -> None:
        """TaskInfo can include completion information."""
        now = datetime.now(UTC)
        task = TaskInfo(
            task_id="task-456",
            task_type="error_analysis",
            category=TaskCategory.UX,
            started_at=now,
            completed_at=now,
            success=True,
        )

        assert task.completed_at == now
        assert task.success is True

    def test_task_info_with_error(self) -> None:
        """TaskInfo can include error information."""
        now = datetime.now(UTC)
        task = TaskInfo(
            task_id="task-789",
            task_type="nudge_recommendation",
            category=TaskCategory.UX,
            started_at=now,
            completed_at=now,
            success=False,
            error="Rate limit exceeded",
        )

        assert task.success is False
        assert task.error == "Rate limit exceeded"

    def test_task_info_to_dict(self) -> None:
        """TaskInfo.to_dict() returns correct structure."""
        now = datetime.now(UTC)
        task = TaskInfo(
            task_id="task-123",
            task_type="persona_analysis",
            category=TaskCategory.UX,
            started_at=now,
        )

        result = task.to_dict()

        assert result["task_id"] == "task-123"
        assert result["task_type"] == "persona_analysis"
        assert result["category"] == "ux"
        assert "started_at" in result


class TestOrchestratorStatus:
    """Test suite for OrchestratorStatus enum."""

    def test_orchestrator_status_enum_contains_expected_values(self) -> None:
        """OrchestratorStatus has expected values."""
        assert OrchestratorStatus.IDLE.value == "idle"
        assert OrchestratorStatus.PROCESSING.value == "processing"
        assert OrchestratorStatus.ERROR.value == "error"


class TestTaskCategory:
    """Test suite for TaskCategory enum."""

    def test_task_category_enum_contains_all_expected_values(self) -> None:
        """TaskCategory has all expected values."""
        expected = {"ux", "session", "conversation", "canvas", "diagram", "trace", "hitl", "command", "alert"}
        actual = {c.value for c in TaskCategory}
        assert actual == expected


# =============================================================================
# Handler Tests
# =============================================================================


class TestOrchestratorStatusHandler:
    """Test suite for OrchestratorStatusHandler (WebSocketBase compliant)."""

    def setup_method(self) -> None:
        """Reset broadcaster before each test."""
        reset_orchestrator_status_broadcaster()

    def teardown_method(self) -> None:
        """Clean up after each test."""
        reset_orchestrator_status_broadcaster()

    # =========================================================================
    # Constructor Tests
    # =========================================================================

    def test_handler_extends_websocket_base(self) -> None:
        """Handler should extend WebSocketBase."""
        from mcp_server_langgraph.websocket.base import WebSocketBase

        config = WebSocketConfig(
            endpoint_name="orchestrator-status",
            require_auth=True,
        )
        handler = OrchestratorStatusHandler(
            config=config,
            broadcaster=OrchestratorStatusBroadcaster(),
        )

        assert isinstance(handler, WebSocketBase)

    def test_handler_uses_singleton_broadcaster_when_none_provided(self) -> None:
        """Handler uses singleton broadcaster when none provided."""
        reset_orchestrator_status_broadcaster()

        config = WebSocketConfig(endpoint_name="orchestrator-status")
        handler1 = OrchestratorStatusHandler(config=config)
        handler2 = OrchestratorStatusHandler(config=config)

        assert handler1._broadcaster is handler2._broadcaster

    def test_handler_accepts_custom_broadcaster(self) -> None:
        """Handler can accept a custom broadcaster."""
        config = WebSocketConfig(endpoint_name="orchestrator-status")
        custom_broadcaster = OrchestratorStatusBroadcaster()
        handler = OrchestratorStatusHandler(
            config=config,
            broadcaster=custom_broadcaster,
        )

        assert handler._broadcaster is custom_broadcaster

    # =========================================================================
    # on_connect Tests
    # =========================================================================

    @pytest.mark.asyncio
    async def test_on_connect_subscribes_to_broadcaster(self) -> None:
        """on_connect should subscribe WebSocket to broadcaster."""
        broadcaster = OrchestratorStatusBroadcaster()
        config = WebSocketConfig(endpoint_name="orchestrator-status")
        handler = OrchestratorStatusHandler(config=config, broadcaster=broadcaster)

        # Simulate WebSocket connection
        ws = AsyncMock()
        handler._websocket = ws

        user = AuthUser(id="user-123", username="user123", email="test@example.com")
        await handler.on_connect(user)

        assert broadcaster.subscriber_count == 1
        assert handler._subscribed is True
        assert handler._user_id == "user-123"

    @pytest.mark.asyncio
    async def test_on_connect_logs_user_info(self) -> None:
        """on_connect should store user ID for filtering."""
        broadcaster = OrchestratorStatusBroadcaster()
        config = WebSocketConfig(endpoint_name="orchestrator-status")
        handler = OrchestratorStatusHandler(config=config, broadcaster=broadcaster)

        ws = AsyncMock()
        handler._websocket = ws

        user = AuthUser(id="admin-user", username="admin", email="admin@example.com")
        await handler.on_connect(user)

        assert handler._user_id == "admin-user"

    # =========================================================================
    # on_disconnect Tests
    # =========================================================================

    @pytest.mark.asyncio
    async def test_on_disconnect_unsubscribes_from_broadcaster(self) -> None:
        """on_disconnect should unsubscribe WebSocket from broadcaster."""
        broadcaster = OrchestratorStatusBroadcaster()
        config = WebSocketConfig(endpoint_name="orchestrator-status")
        handler = OrchestratorStatusHandler(config=config, broadcaster=broadcaster)

        ws = AsyncMock()
        handler._websocket = ws

        # First connect
        user = AuthUser(id="user-456", username="user456", email="test@example.com")
        await handler.on_connect(user)
        assert broadcaster.subscriber_count == 1

        # Then disconnect
        await handler.on_disconnect()
        assert broadcaster.subscriber_count == 0

    @pytest.mark.asyncio
    async def test_on_disconnect_handles_not_subscribed(self) -> None:
        """on_disconnect should handle case where not subscribed."""
        broadcaster = OrchestratorStatusBroadcaster()
        config = WebSocketConfig(endpoint_name="orchestrator-status")
        handler = OrchestratorStatusHandler(config=config, broadcaster=broadcaster)

        ws = AsyncMock()
        handler._websocket = ws
        handler._subscribed = False

        # Should not raise
        await handler.on_disconnect()
        assert broadcaster.subscriber_count == 0

    # =========================================================================
    # handle_message Tests
    # =========================================================================

    @pytest.mark.asyncio
    async def test_handle_message_subscribe(self) -> None:
        """handle_message should handle subscribe message."""
        broadcaster = OrchestratorStatusBroadcaster()
        config = WebSocketConfig(endpoint_name="orchestrator-status")
        handler = OrchestratorStatusHandler(config=config, broadcaster=broadcaster)

        ws = AsyncMock()
        handler._websocket = ws
        handler._user_id = "user-789"
        handler._subscribed = False

        message = MessageEnvelope(type="subscribe", id="msg-1")
        response = await handler.handle_message(message)

        assert response is not None
        assert response.type == "subscribed"
        assert response.id == "msg-1"
        assert handler._subscribed is True

    @pytest.mark.asyncio
    async def test_handle_message_unsubscribe(self) -> None:
        """handle_message should handle unsubscribe message."""
        broadcaster = OrchestratorStatusBroadcaster()
        config = WebSocketConfig(endpoint_name="orchestrator-status")
        handler = OrchestratorStatusHandler(config=config, broadcaster=broadcaster)

        ws = AsyncMock()
        handler._websocket = ws
        handler._user_id = "user-789"

        # First subscribe
        await broadcaster.subscribe(ws, user_id="user-789")
        handler._subscribed = True

        message = MessageEnvelope(type="unsubscribe", id="msg-2")
        response = await handler.handle_message(message)

        assert response is not None
        assert response.type == "unsubscribed"
        assert response.id == "msg-2"
        assert handler._subscribed is False

    @pytest.mark.asyncio
    async def test_handle_message_unknown_type_returns_none(self) -> None:
        """handle_message should return None for unknown message types."""
        broadcaster = OrchestratorStatusBroadcaster()
        config = WebSocketConfig(endpoint_name="orchestrator-status")
        handler = OrchestratorStatusHandler(config=config, broadcaster=broadcaster)

        ws = AsyncMock()
        handler._websocket = ws

        message = MessageEnvelope(type="unknown_type", id="msg-3")
        response = await handler.handle_message(message)

        assert response is None

    @pytest.mark.asyncio
    async def test_handle_message_get_status_returns_current_status(self) -> None:
        """handle_message should handle get_status message."""
        broadcaster = OrchestratorStatusBroadcaster()
        config = WebSocketConfig(endpoint_name="orchestrator-status")
        handler = OrchestratorStatusHandler(config=config, broadcaster=broadcaster)

        ws = AsyncMock()
        handler._websocket = ws

        message = MessageEnvelope(type="get_status", id="msg-4")
        response = await handler.handle_message(message)

        assert response is not None
        assert response.type == "status"
        assert response.id == "msg-4"
        assert "status" in response.payload
        assert response.payload["status"] == "idle"

    # =========================================================================
    # Protocol Tests
    # =========================================================================

    def test_broadcaster_implements_protocol(self) -> None:
        """OrchestratorStatusBroadcaster should implement the protocol."""
        broadcaster = OrchestratorStatusBroadcaster()
        assert isinstance(broadcaster, OrchestratorStatusBroadcasterProtocol)

    # =========================================================================
    # Integration with WebSocketConfig
    # =========================================================================

    def test_handler_respects_config(self) -> None:
        """Handler should respect WebSocketConfig settings."""
        config = WebSocketConfig(
            endpoint_name="orchestrator-status",
            require_auth=True,
            authz_resource_type="ai",
            authz_resource_id="orchestrator",
            authz_required_relation="viewer",
            rate_limit_per_minute=200,
            message_timeout=30,
        )
        handler = OrchestratorStatusHandler(
            config=config,
            broadcaster=OrchestratorStatusBroadcaster(),
        )

        assert handler.config.endpoint_name == "orchestrator-status"
        assert handler.config.require_auth is True
        assert handler.config.authz_resource_type == "ai"
        assert handler.config.authz_resource_id == "orchestrator"
        assert handler.config.authz_required_relation == "viewer"


# =============================================================================
# Prometheus Metrics Tests (TDD - RED phase)
# =============================================================================


class TestOrchestratorStatusMetrics:
    """Test suite for Prometheus metrics integration."""

    def setup_method(self) -> None:
        """Reset broadcaster before each test."""
        reset_orchestrator_status_broadcaster()

    def teardown_method(self) -> None:
        """Clean up after each test."""
        reset_orchestrator_status_broadcaster()

    def test_broadcaster_has_get_metrics_method(self) -> None:
        """Broadcaster should expose metrics via get_metrics()."""
        broadcaster = OrchestratorStatusBroadcaster()
        assert hasattr(broadcaster, "get_metrics")
        assert callable(broadcaster.get_metrics)

    def test_get_metrics_returns_subscriber_count(self) -> None:
        """get_metrics should include subscriber_count."""
        broadcaster = OrchestratorStatusBroadcaster()
        metrics = broadcaster.get_metrics()
        assert "subscriber_count" in metrics
        assert metrics["subscriber_count"] == 0

    def test_get_metrics_returns_active_task_count(self) -> None:
        """get_metrics should include active_task_count."""
        broadcaster = OrchestratorStatusBroadcaster()
        metrics = broadcaster.get_metrics()
        assert "active_task_count" in metrics
        assert metrics["active_task_count"] == 0

    def test_get_metrics_returns_total_tasks_started(self) -> None:
        """get_metrics should include total_tasks_started counter."""
        broadcaster = OrchestratorStatusBroadcaster()
        metrics = broadcaster.get_metrics()
        assert "total_tasks_started" in metrics
        assert metrics["total_tasks_started"] == 0

    def test_get_metrics_returns_total_tasks_completed(self) -> None:
        """get_metrics should include total_tasks_completed counter."""
        broadcaster = OrchestratorStatusBroadcaster()
        metrics = broadcaster.get_metrics()
        assert "total_tasks_completed" in metrics
        assert metrics["total_tasks_completed"] == 0

    def test_get_metrics_returns_total_tasks_failed(self) -> None:
        """get_metrics should include total_tasks_failed counter."""
        broadcaster = OrchestratorStatusBroadcaster()
        metrics = broadcaster.get_metrics()
        assert "total_tasks_failed" in metrics
        assert metrics["total_tasks_failed"] == 0

    @pytest.mark.asyncio
    async def test_metrics_update_on_task_started(self) -> None:
        """Metrics should update when task starts."""
        broadcaster = OrchestratorStatusBroadcaster()

        task_info = TaskInfo(
            task_id="task-metrics-1",
            task_type="persona_analysis",
            category=TaskCategory.UX,
            started_at=datetime.now(UTC),
        )
        await broadcaster.broadcast_task_started(task_info)

        metrics = broadcaster.get_metrics()
        assert metrics["total_tasks_started"] == 1
        assert metrics["active_task_count"] == 1

    @pytest.mark.asyncio
    async def test_metrics_update_on_task_completed(self) -> None:
        """Metrics should update when task completes."""
        broadcaster = OrchestratorStatusBroadcaster()

        task_info = TaskInfo(
            task_id="task-metrics-2",
            task_type="error_analysis",
            category=TaskCategory.UX,
            started_at=datetime.now(UTC),
        )
        await broadcaster.broadcast_task_started(task_info)

        task_info.completed_at = datetime.now(UTC)
        task_info.success = True
        await broadcaster.broadcast_task_completed(task_info)

        metrics = broadcaster.get_metrics()
        assert metrics["total_tasks_completed"] == 1
        assert metrics["active_task_count"] == 0

    @pytest.mark.asyncio
    async def test_metrics_update_on_task_failed(self) -> None:
        """Metrics should update when task fails."""
        broadcaster = OrchestratorStatusBroadcaster()

        task_info = TaskInfo(
            task_id="task-metrics-3",
            task_type="intent_detect",
            category=TaskCategory.CONVERSATION,
            started_at=datetime.now(UTC),
        )
        await broadcaster.broadcast_task_started(task_info)

        task_info.error = "Test error"
        await broadcaster.broadcast_task_failed(task_info)

        metrics = broadcaster.get_metrics()
        assert metrics["total_tasks_failed"] == 1
        assert metrics["active_task_count"] == 0


# =============================================================================
# Progress Percentage Tests (TDD - RED phase)
# =============================================================================


class TestTaskProgress:
    """Test suite for task progress tracking."""

    def setup_method(self) -> None:
        """Reset broadcaster before each test."""
        reset_orchestrator_status_broadcaster()

    def teardown_method(self) -> None:
        """Clean up after each test."""
        reset_orchestrator_status_broadcaster()

    def test_task_info_has_progress_field(self) -> None:
        """TaskInfo should have optional progress field (0-100)."""
        task_info = TaskInfo(
            task_id="task-progress-1",
            task_type="trace_summarize",
            category=TaskCategory.TRACE,
            started_at=datetime.now(UTC),
        )
        # Progress should be None by default
        assert hasattr(task_info, "progress")
        assert task_info.progress is None

    def test_task_info_progress_can_be_set(self) -> None:
        """TaskInfo progress should accept 0-100 values."""
        task_info = TaskInfo(
            task_id="task-progress-2",
            task_type="diagram_analyze",
            category=TaskCategory.DIAGRAM,
            started_at=datetime.now(UTC),
            progress=50,
        )
        assert task_info.progress == 50

    def test_task_info_to_dict_includes_progress(self) -> None:
        """to_dict should include progress when set."""
        task_info = TaskInfo(
            task_id="task-progress-3",
            task_type="code_analyze",
            category=TaskCategory.CANVAS,
            started_at=datetime.now(UTC),
            progress=75,
        )
        result = task_info.to_dict()
        assert "progress" in result
        assert result["progress"] == 75

    @pytest.mark.asyncio
    async def test_broadcast_task_progress_sends_event(self) -> None:
        """Broadcaster should have broadcast_task_progress method."""
        broadcaster = OrchestratorStatusBroadcaster()
        ws = AsyncMock()
        await broadcaster.subscribe(ws)

        task_info = TaskInfo(
            task_id="task-progress-4",
            task_type="risk_assess",
            category=TaskCategory.HITL,
            started_at=datetime.now(UTC),
        )
        await broadcaster.broadcast_task_started(task_info)
        ws.reset_mock()

        # Update progress
        await broadcaster.broadcast_task_progress(
            task_id="task-progress-4",
            progress=50,
            message="Halfway done...",
        )

        ws.send_json.assert_called_once()
        call_args = ws.send_json.call_args[0][0]
        assert call_args["type"] == "task_progress"
        assert call_args["payload"]["task_id"] == "task-progress-4"
        assert call_args["payload"]["progress"] == 50

    @pytest.mark.asyncio
    async def test_get_status_snapshot_includes_task_progress(self) -> None:
        """Status snapshot should include progress for active tasks."""
        broadcaster = OrchestratorStatusBroadcaster()

        task_info = TaskInfo(
            task_id="task-progress-5",
            task_type="session_summarize",
            category=TaskCategory.SESSION,
            started_at=datetime.now(UTC),
            progress=30,
        )
        await broadcaster.broadcast_task_started(task_info)

        snapshot = broadcaster.get_status_snapshot()
        assert "activeTaskProgress" in snapshot
        assert "task-progress-5" in snapshot["activeTaskProgress"]
        assert snapshot["activeTaskProgress"]["task-progress-5"] == 30


# =============================================================================
# Task Queue Depth Tests (TDD - RED phase)
# =============================================================================


class TestTaskQueueDepth:
    """Test suite for task queue depth indicator."""

    def setup_method(self) -> None:
        """Reset broadcaster before each test."""
        reset_orchestrator_status_broadcaster()

    def teardown_method(self) -> None:
        """Clean up after each test."""
        reset_orchestrator_status_broadcaster()

    def test_broadcaster_has_queue_depth_property(self) -> None:
        """Broadcaster should have queue_depth property."""
        broadcaster = OrchestratorStatusBroadcaster()
        assert hasattr(broadcaster, "queue_depth")
        assert broadcaster.queue_depth == 0

    @pytest.mark.asyncio
    async def test_queue_depth_increments_on_task_queued(self) -> None:
        """queue_depth should increment when task is queued."""
        broadcaster = OrchestratorStatusBroadcaster()

        # Queue a task (different from starting - it's waiting)
        await broadcaster.queue_task(
            task_id="task-queue-1",
            task_type="persona_analysis",
            category=TaskCategory.UX,
        )

        assert broadcaster.queue_depth == 1

    @pytest.mark.asyncio
    async def test_queue_depth_decrements_on_task_started(self) -> None:
        """queue_depth should decrement when queued task starts."""
        broadcaster = OrchestratorStatusBroadcaster()

        # Queue then start
        await broadcaster.queue_task(
            task_id="task-queue-2",
            task_type="error_analysis",
            category=TaskCategory.UX,
        )
        assert broadcaster.queue_depth == 1

        task_info = TaskInfo(
            task_id="task-queue-2",
            task_type="error_analysis",
            category=TaskCategory.UX,
            started_at=datetime.now(UTC),
        )
        await broadcaster.broadcast_task_started(task_info)

        assert broadcaster.queue_depth == 0

    @pytest.mark.asyncio
    async def test_broadcast_queue_update_sends_event(self) -> None:
        """Broadcaster should send queue_update when queue changes."""
        broadcaster = OrchestratorStatusBroadcaster()
        ws = AsyncMock()
        await broadcaster.subscribe(ws)

        await broadcaster.queue_task(
            task_id="task-queue-3",
            task_type="disclosure_analysis",
            category=TaskCategory.UX,
        )

        # Check that queue_update was broadcast
        calls = [call[0][0] for call in ws.send_json.call_args_list]
        queue_updates = [c for c in calls if c.get("type") == "queue_update"]
        assert len(queue_updates) >= 1
        assert queue_updates[-1]["payload"]["queue_depth"] == 1

    def test_get_status_snapshot_includes_queue_depth(self) -> None:
        """Status snapshot should include queue_depth."""
        broadcaster = OrchestratorStatusBroadcaster()
        snapshot = broadcaster.get_status_snapshot()
        assert "queueDepth" in snapshot
        assert snapshot["queueDepth"] == 0

    def test_get_metrics_includes_queue_depth(self) -> None:
        """get_metrics should include queue_depth."""
        broadcaster = OrchestratorStatusBroadcaster()
        metrics = broadcaster.get_metrics()
        assert "queue_depth" in metrics
        assert metrics["queue_depth"] == 0
