"""
Orchestrator Status WebSocket Integration Tests.

Integration tests for /api/v1/ws/orchestrator/status endpoint.
Tests the full WebSocket flow for AI orchestrator status updates.

Architecture:
- Uses Starlette TestClient for actual WebSocket connections
- Tests subscription, message broadcasting, and lifecycle events
- Validates authorization and message format
"""

from __future__ import annotations

import gc
from datetime import UTC, datetime, timedelta
from typing import Generator

import jwt
import pytest
from fastapi import FastAPI, WebSocket
from starlette.testclient import TestClient

from mcp_server_langgraph.websocket.handlers.orchestrator_status import (
    OrchestratorStatus,
    OrchestratorStatusBroadcaster,
    OrchestratorStatusHandler,
    TaskCategory,
    TaskInfo,
    get_orchestrator_status_broadcaster,
    reset_orchestrator_status_broadcaster,
)
from mcp_server_langgraph.websocket.types import WebSocketConfig

pytestmark = [
    pytest.mark.integration,
    pytest.mark.websocket,
    pytest.mark.orchestrator,
]

# Test JWT secret for integration tests
TEST_JWT_SECRET = "integration-test-jwt-secret-for-orchestrator-status"


def _create_test_jwt(
    user_id: str = "user:alice",
    username: str = "alice",
    roles: list[str] | None = None,
    email: str = "alice@example.com",
    expires_in: int = 3600,
    secret: str = TEST_JWT_SECRET,
) -> str:
    """Create a test JWT token for integration tests."""
    if roles is None:
        roles = ["user"]
    now = datetime.now(UTC)
    payload = {
        "sub": user_id,
        "username": username,
        "email": email,
        "roles": roles,
        "exp": now + timedelta(seconds=expires_in),
        "iat": now,
        "jti": f"{username}_{int(now.timestamp() * 1000)}",
    }
    return jwt.encode(payload, secret, algorithm="HS256")


@pytest.fixture
def test_broadcaster() -> Generator[OrchestratorStatusBroadcaster, None, None]:
    """Create a test broadcaster instance."""
    reset_orchestrator_status_broadcaster()
    broadcaster = get_orchestrator_status_broadcaster()
    yield broadcaster
    reset_orchestrator_status_broadcaster()


@pytest.fixture
def test_app(test_broadcaster: OrchestratorStatusBroadcaster) -> FastAPI:
    """Create a test FastAPI app with orchestrator status endpoint."""
    app = FastAPI()

    @app.websocket("/api/v1/ws/orchestrator/status")
    async def orchestrator_status_endpoint(websocket: WebSocket) -> None:
        handler = OrchestratorStatusHandler(
            config=WebSocketConfig(
                endpoint_name="orchestrator-status-test",
                require_auth=False,  # Disable auth for testing
                rate_limit_per_minute=600,
                message_timeout=30,
            ),
            broadcaster=test_broadcaster,
        )
        await handler.run(websocket)

    return app


@pytest.fixture
def test_client(test_app: FastAPI) -> Generator[TestClient, None, None]:
    """Create a test client for the app."""
    with TestClient(test_app) as client:
        yield client


@pytest.mark.xdist_group(name="orchestrator_status_websocket")
class TestOrchestratorStatusWebSocketConnection:
    """Test WebSocket connection lifecycle for orchestrator status."""

    def teardown_method(self):
        """Force GC to prevent mock accumulation in xdist workers."""
        gc.collect()

    def test_websocket_connection_succeeds(self, test_client: TestClient) -> None:
        """Test that WebSocket connection can be established."""
        with test_client.websocket_connect("/api/v1/ws/orchestrator/status?v=1.0.0") as ws:
            # Connection successful
            assert ws is not None

    def test_websocket_receives_subscribed_on_connect(self, test_client: TestClient) -> None:
        """Test that client receives subscribed message on connect."""
        with test_client.websocket_connect("/api/v1/ws/orchestrator/status?v=1.0.0") as ws:
            # Send subscribe message
            ws.send_json({"type": "subscribe", "id": "test-1"})
            response = ws.receive_json()

            assert response["type"] == "subscribed"
            assert response["id"] == "test-1"
            assert response["payload"]["status"] == "subscribed"

    def test_websocket_unsubscribe_message(self, test_client: TestClient) -> None:
        """Test that client can unsubscribe from updates."""
        with test_client.websocket_connect("/api/v1/ws/orchestrator/status?v=1.0.0") as ws:
            # First subscribe
            ws.send_json({"type": "subscribe", "id": "test-1"})
            ws.receive_json()  # subscribed response

            # Then unsubscribe
            ws.send_json({"type": "unsubscribe", "id": "test-2"})
            response = ws.receive_json()

            assert response["type"] == "unsubscribed"
            assert response["id"] == "test-2"

    def test_websocket_get_status_returns_idle(self, test_client: TestClient) -> None:
        """Test that get_status returns idle when no tasks running."""
        with test_client.websocket_connect("/api/v1/ws/orchestrator/status?v=1.0.0") as ws:
            ws.send_json({"type": "get_status", "id": "test-3"})
            response = ws.receive_json()

            assert response["type"] == "status"
            assert response["id"] == "test-3"
            assert response["payload"]["status"] == "idle"
            assert response["payload"]["activeTasks"] == 0
            # New fields for reconnection support
            assert "activeTaskTypes" in response["payload"]
            assert response["payload"]["activeTaskTypes"] == []


@pytest.mark.xdist_group(name="orchestrator_status_websocket")
class TestOrchestratorStatusBroadcasting:
    """Test message broadcasting for orchestrator status."""

    def teardown_method(self):
        """Force GC to prevent mock accumulation in xdist workers."""
        gc.collect()

    @pytest.mark.asyncio
    async def test_broadcaster_subscriber_count(self, test_broadcaster: OrchestratorStatusBroadcaster) -> None:
        """Test that broadcaster correctly tracks subscriber count."""
        from unittest.mock import MagicMock

        assert test_broadcaster.subscriber_count == 0

        # Add a mock subscriber
        mock_ws = MagicMock()
        await test_broadcaster.subscribe(mock_ws, user_id="user-1")

        assert test_broadcaster.subscriber_count == 1

        await test_broadcaster.unsubscribe(mock_ws)
        assert test_broadcaster.subscriber_count == 0

    @pytest.mark.asyncio
    async def test_broadcaster_sends_status_to_subscribers(self, test_broadcaster: OrchestratorStatusBroadcaster) -> None:
        """Test that broadcaster sends status updates to subscribers."""
        from unittest.mock import AsyncMock, MagicMock

        mock_ws = MagicMock()
        mock_ws.send_json = AsyncMock(return_value=None)

        await test_broadcaster.subscribe(mock_ws)

        await test_broadcaster.broadcast_status(
            status=OrchestratorStatus.PROCESSING,
            message="Analyzing...",
            task_type="persona_analysis",
            category=TaskCategory.UX,
        )

        mock_ws.send_json.assert_called_once()
        call_args = mock_ws.send_json.call_args[0][0]
        assert call_args["type"] == "orchestrator_status"
        assert call_args["payload"]["status"] == "processing"
        assert call_args["payload"]["message"] == "Analyzing..."

    @pytest.mark.asyncio
    async def test_broadcaster_sends_task_lifecycle_events(self, test_broadcaster: OrchestratorStatusBroadcaster) -> None:
        """Test that broadcaster sends task lifecycle events."""
        from unittest.mock import AsyncMock, MagicMock

        mock_ws = MagicMock()
        mock_ws.send_json = AsyncMock(return_value=None)

        await test_broadcaster.subscribe(mock_ws)

        # Create task info
        task_info = TaskInfo(
            task_id="task-123",
            task_type="persona_analysis",
            category=TaskCategory.UX,
            started_at=datetime.now(UTC),
        )

        # Test task_started
        await test_broadcaster.broadcast_task_started(task_info)
        call_args = mock_ws.send_json.call_args[0][0]
        assert call_args["type"] == "task_started"
        assert call_args["payload"]["task_id"] == "task-123"

        # Test task_completed
        task_info.completed_at = datetime.now(UTC)
        task_info.success = True
        await test_broadcaster.broadcast_task_completed(task_info)
        call_args = mock_ws.send_json.call_args[0][0]
        assert call_args["type"] == "task_completed"
        assert call_args["payload"]["success"] is True

    @pytest.mark.asyncio
    async def test_broadcaster_filters_by_user_id(self, test_broadcaster: OrchestratorStatusBroadcaster) -> None:
        """Test that broadcaster filters messages by user_id."""
        from unittest.mock import AsyncMock, MagicMock

        ws_user1 = MagicMock()
        ws_user1.send_json = AsyncMock(return_value=None)

        ws_user2 = MagicMock()
        ws_user2.send_json = AsyncMock(return_value=None)

        await test_broadcaster.subscribe(ws_user1, user_id="user-1")
        await test_broadcaster.subscribe(ws_user2, user_id="user-2")

        # Broadcast to user-1 only
        await test_broadcaster.broadcast_status(
            status=OrchestratorStatus.PROCESSING,
            message="Processing for user-1",
            user_id="user-1",
        )

        ws_user1.send_json.assert_called_once()
        ws_user2.send_json.assert_not_called()


@pytest.mark.xdist_group(name="orchestrator_status_websocket")
class TestOrchestratorStatusMessageFormats:
    """Test message format validation for orchestrator status."""

    def teardown_method(self):
        """Force GC to prevent mock accumulation in xdist workers."""
        gc.collect()

    def test_orchestrator_status_message_format(self, test_client: TestClient) -> None:
        """Test orchestrator_status message format matches frontend expectations."""
        # The frontend hook (useAIOrchestratorStatus) expects:
        # {
        #   type: "orchestrator_status",
        #   payload: {
        #     status: "idle" | "processing" | "error",
        #     message?: string,
        #     task_type?: string,
        #     category?: string
        #   }
        # }
        with test_client.websocket_connect("/api/v1/ws/orchestrator/status?v=1.0.0") as ws:
            ws.send_json({"type": "get_status", "id": "format-test"})
            response = ws.receive_json()

            # Verify structure
            assert "type" in response
            assert "payload" in response
            assert "status" in response["payload"]

    def test_task_started_message_format(self) -> None:
        """Test task_started message format matches frontend expectations."""
        # Frontend expects:
        # {
        #   type: "task_started",
        #   payload: {
        #     task_id: string,
        #     task_type: string,
        #     category: string,
        #     started_at: string (ISO)
        #   }
        # }
        task_info = TaskInfo(
            task_id="task-abc",
            task_type="persona_analysis",
            category=TaskCategory.UX,
            started_at=datetime.now(UTC),
        )

        result = task_info.to_dict()

        assert "task_id" in result
        assert "task_type" in result
        assert "category" in result
        assert "started_at" in result
        assert result["task_id"] == "task-abc"
        assert result["category"] == "ux"

    def test_all_task_categories_have_valid_values(self) -> None:
        """Test that all TaskCategory enum values are valid strings."""
        expected_categories = {
            "ux",
            "session",
            "conversation",
            "canvas",
            "diagram",
            "trace",
            "hitl",
            "command",
            "alert",
            "workflow",
        }
        actual_categories = {c.value for c in TaskCategory}

        assert actual_categories == expected_categories

    def test_all_orchestrator_statuses_have_valid_values(self) -> None:
        """Test that all OrchestratorStatus enum values are valid strings."""
        expected_statuses = {"idle", "processing", "error"}
        actual_statuses = {s.value for s in OrchestratorStatus}

        assert actual_statuses == expected_statuses
