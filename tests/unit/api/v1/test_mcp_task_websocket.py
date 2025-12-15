"""
Tests for MCP Task Status WebSocket.

TDD: These tests define the expected behavior of the task status WebSocket,
which provides real-time task status updates to clients.

Endpoints tested:
- WS /api/v1/mcp/tasks/ws - Subscribe to task status updates

Message types:
- subscribe: Subscribe to a specific task
- unsubscribe: Unsubscribe from a task
- list: List all tasks for the session
- ping: Heartbeat

Response types:
- task_status: Current status of a task
- task_update: Status change notification
- task_list: List of all active tasks
- pong: Heartbeat response
- error: Error message
"""

from __future__ import annotations

import gc
from datetime import datetime
from typing import TYPE_CHECKING
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient

if TYPE_CHECKING:
    pass


pytestmark = [
    pytest.mark.unit,
    pytest.mark.api,
    pytest.mark.websocket,
]


@pytest.fixture
def app_with_task_ws() -> FastAPI:
    """Create a FastAPI app with the task WebSocket router mounted."""
    from fastapi import FastAPI

    from mcp_server_langgraph.api.v1.mcp_task_websocket import mcp_task_ws_router

    app = FastAPI()
    app.include_router(mcp_task_ws_router, prefix="/api/v1")
    return app


@pytest.fixture
def client(app_with_task_ws: FastAPI) -> TestClient:
    """Create a test client."""
    return TestClient(app_with_task_ws)


@pytest.mark.xdist_group(name="mcp_task_ws")
class TestTaskWebSocketConnection:
    """Tests for WebSocket connection handling."""

    def teardown_method(self) -> None:
        """Force GC to prevent mock accumulation in xdist workers."""
        gc.collect()

    def test_websocket_accepts_connection(self, client: TestClient) -> None:
        """
        GIVEN a task WebSocket endpoint
        WHEN a client connects
        THEN the connection is accepted
        """
        with patch("mcp_server_langgraph.api.v1.mcp_task_websocket.get_mcp_service") as mock_get:
            mock_service = MagicMock()
            mock_service.list_tasks = AsyncMock(return_value=[])
            mock_get.return_value = mock_service

            with client.websocket_connect("/api/v1/mcp/tasks/ws") as websocket:
                # Consume initial task list
                websocket.receive_json()

                # Connection established, send ping to verify
                websocket.send_json({"type": "ping"})
                response = websocket.receive_json()
                assert response["type"] == "pong"

    def test_websocket_sends_initial_task_list(self, client: TestClient) -> None:
        """
        GIVEN a task WebSocket endpoint with active tasks
        WHEN a client connects
        THEN it receives the current task list
        """
        from mcp_server_langgraph.api.v1.mcp_bridge import MCPTask, TaskStatus

        mock_tasks = [
            MCPTask(
                task_id="task-1",
                status=TaskStatus.WORKING,
                created_at=datetime.now(),
                last_updated_at=datetime.now(),
            ),
        ]

        with patch("mcp_server_langgraph.api.v1.mcp_task_websocket.get_mcp_service") as mock_get:
            mock_service = MagicMock()
            mock_service.list_tasks = AsyncMock(return_value=mock_tasks)
            mock_get.return_value = mock_service

            with client.websocket_connect("/api/v1/mcp/tasks/ws") as websocket:
                # First message should be the task list
                response = websocket.receive_json()
                assert response["type"] == "task_list"
                assert len(response["tasks"]) == 1
                assert response["tasks"][0]["task_id"] == "task-1"


@pytest.mark.xdist_group(name="mcp_task_ws")
class TestTaskWebSocketSubscription:
    """Tests for task subscription handling."""

    def teardown_method(self) -> None:
        """Force GC to prevent mock accumulation in xdist workers."""
        gc.collect()

    def test_subscribe_to_task_returns_current_status(self, client: TestClient) -> None:
        """
        GIVEN an active task
        WHEN client subscribes to it
        THEN it receives the current task status
        """
        from mcp_server_langgraph.api.v1.mcp_bridge import MCPTask, TaskStatus

        mock_task = MCPTask(
            task_id="task-123",
            status=TaskStatus.WORKING,
            created_at=datetime.now(),
            last_updated_at=datetime.now(),
            status_message="Processing...",
        )

        with patch("mcp_server_langgraph.api.v1.mcp_task_websocket.get_mcp_service") as mock_get:
            mock_service = MagicMock()
            mock_service.list_tasks = AsyncMock(return_value=[])
            mock_service.get_task = AsyncMock(return_value=mock_task)
            mock_get.return_value = mock_service

            with client.websocket_connect("/api/v1/mcp/tasks/ws") as websocket:
                # Consume initial task list
                websocket.receive_json()

                # Subscribe to a specific task
                websocket.send_json({"type": "subscribe", "task_id": "task-123"})
                response = websocket.receive_json()

                assert response["type"] == "task_status"
                assert response["task"]["task_id"] == "task-123"
                assert response["task"]["status"] == "working"

    def test_unsubscribe_from_task(self, client: TestClient) -> None:
        """
        GIVEN a subscribed task
        WHEN client unsubscribes
        THEN it receives confirmation
        """
        with patch("mcp_server_langgraph.api.v1.mcp_task_websocket.get_mcp_service") as mock_get:
            mock_service = MagicMock()
            mock_service.list_tasks = AsyncMock(return_value=[])
            mock_get.return_value = mock_service

            with client.websocket_connect("/api/v1/mcp/tasks/ws") as websocket:
                # Consume initial task list
                websocket.receive_json()

                # Unsubscribe from a task
                websocket.send_json({"type": "unsubscribe", "task_id": "task-123"})
                response = websocket.receive_json()

                assert response["type"] == "unsubscribed"
                assert response["task_id"] == "task-123"


@pytest.mark.xdist_group(name="mcp_task_ws")
class TestTaskWebSocketMessages:
    """Tests for WebSocket message handling."""

    def teardown_method(self) -> None:
        """Force GC to prevent mock accumulation in xdist workers."""
        gc.collect()

    def test_ping_returns_pong(self, client: TestClient) -> None:
        """
        GIVEN an active WebSocket connection
        WHEN client sends ping
        THEN server responds with pong
        """
        with patch("mcp_server_langgraph.api.v1.mcp_task_websocket.get_mcp_service") as mock_get:
            mock_service = MagicMock()
            mock_service.list_tasks = AsyncMock(return_value=[])
            mock_get.return_value = mock_service

            with client.websocket_connect("/api/v1/mcp/tasks/ws") as websocket:
                # Consume initial task list
                websocket.receive_json()

                websocket.send_json({"type": "ping"})
                response = websocket.receive_json()

                assert response["type"] == "pong"

    def test_refresh_returns_task_list(self, client: TestClient) -> None:
        """
        GIVEN an active WebSocket connection
        WHEN client sends refresh
        THEN server returns updated task list
        """
        from mcp_server_langgraph.api.v1.mcp_bridge import MCPTask, TaskStatus

        mock_tasks = [
            MCPTask(
                task_id="task-1",
                status=TaskStatus.COMPLETED,
                created_at=datetime.now(),
                last_updated_at=datetime.now(),
            ),
        ]

        with patch("mcp_server_langgraph.api.v1.mcp_task_websocket.get_mcp_service") as mock_get:
            mock_service = MagicMock()
            mock_service.list_tasks = AsyncMock(return_value=mock_tasks)
            mock_get.return_value = mock_service

            with client.websocket_connect("/api/v1/mcp/tasks/ws") as websocket:
                # Consume initial task list
                websocket.receive_json()

                websocket.send_json({"type": "refresh"})
                response = websocket.receive_json()

                assert response["type"] == "task_list"
                assert len(response["tasks"]) == 1

    def test_unknown_message_type_returns_error(self, client: TestClient) -> None:
        """
        GIVEN an active WebSocket connection
        WHEN client sends unknown message type
        THEN server returns error
        """
        with patch("mcp_server_langgraph.api.v1.mcp_task_websocket.get_mcp_service") as mock_get:
            mock_service = MagicMock()
            mock_service.list_tasks = AsyncMock(return_value=[])
            mock_get.return_value = mock_service

            with client.websocket_connect("/api/v1/mcp/tasks/ws") as websocket:
                # Consume initial task list
                websocket.receive_json()

                websocket.send_json({"type": "unknown_type"})
                response = websocket.receive_json()

                assert response["type"] == "error"
                assert "unknown" in response["message"].lower()


@pytest.mark.xdist_group(name="mcp_task_ws")
class TestTaskWebSocketManager:
    """Tests for TaskWebSocketManager class."""

    def teardown_method(self) -> None:
        """Force GC to prevent mock accumulation in xdist workers."""
        gc.collect()

    def test_manager_tracks_connections(self) -> None:
        """
        GIVEN a TaskWebSocketManager
        WHEN a connection is added
        THEN it is tracked in active connections
        """
        from mcp_server_langgraph.api.v1.mcp_task_websocket import TaskWebSocketManager

        manager = TaskWebSocketManager()
        mock_websocket = MagicMock()

        manager.connect("client-1", mock_websocket)

        assert "client-1" in manager.active_connections

    def test_manager_removes_disconnected_clients(self) -> None:
        """
        GIVEN a connected client
        WHEN it disconnects
        THEN it is removed from active connections
        """
        from mcp_server_langgraph.api.v1.mcp_task_websocket import TaskWebSocketManager

        manager = TaskWebSocketManager()
        mock_websocket = MagicMock()

        manager.connect("client-1", mock_websocket)
        manager.disconnect("client-1")

        assert "client-1" not in manager.active_connections

    def test_manager_tracks_subscriptions(self) -> None:
        """
        GIVEN a TaskWebSocketManager with connected client
        WHEN client subscribes to a task
        THEN subscription is tracked
        """
        from mcp_server_langgraph.api.v1.mcp_task_websocket import TaskWebSocketManager

        manager = TaskWebSocketManager()
        mock_websocket = MagicMock()

        manager.connect("client-1", mock_websocket)
        manager.subscribe("client-1", "task-123")

        assert "task-123" in manager.subscriptions.get("client-1", set())

    def test_manager_removes_subscription_on_unsubscribe(self) -> None:
        """
        GIVEN a subscribed client
        WHEN client unsubscribes
        THEN subscription is removed
        """
        from mcp_server_langgraph.api.v1.mcp_task_websocket import TaskWebSocketManager

        manager = TaskWebSocketManager()
        mock_websocket = MagicMock()

        manager.connect("client-1", mock_websocket)
        manager.subscribe("client-1", "task-123")
        manager.unsubscribe("client-1", "task-123")

        assert "task-123" not in manager.subscriptions.get("client-1", set())

    def test_manager_cleans_up_subscriptions_on_disconnect(self) -> None:
        """
        GIVEN a subscribed client
        WHEN it disconnects
        THEN subscriptions are cleaned up
        """
        from mcp_server_langgraph.api.v1.mcp_task_websocket import TaskWebSocketManager

        manager = TaskWebSocketManager()
        mock_websocket = MagicMock()

        manager.connect("client-1", mock_websocket)
        manager.subscribe("client-1", "task-123")
        manager.disconnect("client-1")

        assert "client-1" not in manager.subscriptions


@pytest.mark.xdist_group(name="mcp_task_ws")
class TestTaskWebSocketErrorHandling:
    """Tests for error handling in WebSocket."""

    def teardown_method(self) -> None:
        """Force GC to prevent mock accumulation in xdist workers."""
        gc.collect()

    def test_subscribe_to_nonexistent_task_returns_error(self, client: TestClient) -> None:
        """
        GIVEN a non-existent task
        WHEN client subscribes to it
        THEN server returns error
        """
        from mcp_server_langgraph.api.v1.mcp_bridge import MCPTaskNotFoundError

        with patch("mcp_server_langgraph.api.v1.mcp_task_websocket.get_mcp_service") as mock_get:
            mock_service = MagicMock()
            mock_service.list_tasks = AsyncMock(return_value=[])
            mock_service.get_task = AsyncMock(side_effect=MCPTaskNotFoundError("Task not found", task_id="task-999"))
            mock_get.return_value = mock_service

            with client.websocket_connect("/api/v1/mcp/tasks/ws") as websocket:
                # Consume initial task list
                websocket.receive_json()

                websocket.send_json({"type": "subscribe", "task_id": "task-999"})
                response = websocket.receive_json()

                assert response["type"] == "error"
                assert "not found" in response["message"].lower()

    def test_malformed_json_returns_error(self, client: TestClient) -> None:
        """
        GIVEN an active WebSocket connection
        WHEN client sends malformed JSON
        THEN server returns error
        """
        with patch("mcp_server_langgraph.api.v1.mcp_task_websocket.get_mcp_service") as mock_get:
            mock_service = MagicMock()
            mock_service.list_tasks = AsyncMock(return_value=[])
            mock_get.return_value = mock_service

            with client.websocket_connect("/api/v1/mcp/tasks/ws") as websocket:
                # Consume initial task list
                websocket.receive_json()

                # Send raw text that isn't valid JSON
                websocket.send_text("not valid json {{{")
                response = websocket.receive_json()

                assert response["type"] == "error"
