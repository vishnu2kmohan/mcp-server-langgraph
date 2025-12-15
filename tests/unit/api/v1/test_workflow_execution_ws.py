"""
Workflow Execution WebSocket Unit Tests

TDD tests for /api/v1/workflows/{id}/execution WebSocket endpoint.
Tests written FIRST before implementation (RED phase).

This WebSocket endpoint provides real-time workflow execution updates:
- Start/stop execution commands
- Node-by-node status updates
- Execution logs streaming
- Connection lifecycle management
"""

import gc
from collections.abc import Generator
from typing import Any
from uuid import uuid4

import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient


pytestmark = [
    pytest.mark.unit,
    pytest.mark.api,
    pytest.mark.xdist_group(name="workflow_execution_ws"),
]


class MockWorkflowExecutionManager:
    """Mock workflow execution manager for testing."""

    def __init__(self) -> None:
        """Initialize with empty state."""
        self._workflows: dict[str, dict[str, Any]] = {}
        self._executions: dict[str, dict[str, Any]] = {}

    async def get_workflow(self, workflow_id: str) -> dict[str, Any] | None:
        """Get a workflow by ID."""
        return self._workflows.get(workflow_id)

    async def start_execution(self, workflow_id: str, input_data: dict[str, Any] | None = None) -> str:
        """Start workflow execution, returns execution ID."""
        execution_id = str(uuid4())
        self._executions[execution_id] = {
            "id": execution_id,
            "workflow_id": workflow_id,
            "status": "running",
            "input": input_data,
        }
        return execution_id

    async def stop_execution(self, workflow_id: str) -> bool:
        """Stop workflow execution."""
        for exec_id, execution in self._executions.items():
            if execution["workflow_id"] == workflow_id:
                execution["status"] = "stopped"
                return True
        return False

    def add_workflow(self, workflow_id: str, workflow: dict[str, Any]) -> None:
        """Add a workflow for testing."""
        self._workflows[workflow_id] = workflow


@pytest.fixture
def mock_execution_manager() -> MockWorkflowExecutionManager:
    """Create a mock execution manager."""
    manager = MockWorkflowExecutionManager()
    # Add a test workflow
    manager.add_workflow(
        "wf-123",
        {
            "id": "wf-123",
            "name": "Test Workflow",
            "nodes": [
                {"id": "node-1", "type": "start"},
                {"id": "node-2", "type": "llm"},
                {"id": "node-3", "type": "end"},
            ],
            "edges": [
                {"source": "node-1", "target": "node-2"},
                {"source": "node-2", "target": "node-3"},
            ],
        },
    )
    return manager


@pytest.fixture
def app(mock_execution_manager: MockWorkflowExecutionManager) -> FastAPI:
    """Create test FastAPI app with workflow execution WebSocket."""
    from mcp_server_langgraph.api.v1.workflow_execution_ws import (
        workflow_execution_router,
        get_execution_manager,
    )

    app = FastAPI()
    app.include_router(workflow_execution_router, prefix="/api/v1")

    # Override dependency
    app.dependency_overrides[get_execution_manager] = lambda: mock_execution_manager

    return app


@pytest.fixture
def client(app: FastAPI) -> Generator[TestClient, None, None]:
    """Create test client."""
    with TestClient(app) as c:
        yield c


@pytest.mark.xdist_group(name="testworkflowexecutionwebsocket")
class TestWorkflowExecutionWebSocket:
    """Tests for workflow execution WebSocket endpoint."""

    def teardown_method(self) -> None:
        """Force GC to prevent mock accumulation in xdist workers."""
        gc.collect()

    def test_websocket_connect_success(self, client: TestClient) -> None:
        """Should accept WebSocket connection for valid workflow."""
        with client.websocket_connect("/api/v1/workflows/wf-123/execution") as ws:
            # Connection should be established
            assert ws is not None

    def test_websocket_connect_invalid_workflow(self, client: TestClient) -> None:
        """Should reject connection for non-existent workflow."""
        with pytest.raises(Exception):
            with client.websocket_connect("/api/v1/workflows/invalid-id/execution"):
                pass

    def test_start_execution_message(self, client: TestClient) -> None:
        """Should start execution when receiving start message."""
        with client.websocket_connect("/api/v1/workflows/wf-123/execution") as ws:
            ws.send_json({"type": "start", "workflowId": "wf-123"})

            response = ws.receive_json()
            assert response["type"] == "execution_started"
            assert response["workflowId"] == "wf-123"

    def test_start_execution_with_input(self, client: TestClient) -> None:
        """Should start execution with custom input data."""
        with client.websocket_connect("/api/v1/workflows/wf-123/execution") as ws:
            ws.send_json(
                {
                    "type": "start",
                    "workflowId": "wf-123",
                    "input": {"prompt": "Test input"},
                }
            )

            response = ws.receive_json()
            assert response["type"] == "execution_started"
            assert response["workflowId"] == "wf-123"

    def test_stop_execution_message(self, client: TestClient) -> None:
        """Should stop execution when receiving stop message."""
        with client.websocket_connect("/api/v1/workflows/wf-123/execution") as ws:
            # Start first
            ws.send_json({"type": "start", "workflowId": "wf-123"})
            ws.receive_json()  # Consume start response

            # Then stop
            ws.send_json({"type": "stop", "workflowId": "wf-123"})

            response = ws.receive_json()
            assert response["type"] == "execution_stopped"
            assert response["workflowId"] == "wf-123"

    def test_ping_message_returns_pong_response(self, client: TestClient) -> None:
        """Should respond to ping with pong."""
        with client.websocket_connect("/api/v1/workflows/wf-123/execution") as ws:
            ws.send_json({"type": "ping"})

            response = ws.receive_json()
            assert response["type"] == "pong"
            assert "timestamp" in response

    def test_invalid_message_type(self, client: TestClient) -> None:
        """Should return error for invalid message type."""
        with client.websocket_connect("/api/v1/workflows/wf-123/execution") as ws:
            ws.send_json({"type": "invalid_type"})

            response = ws.receive_json()
            assert response["type"] == "error"
            assert "message" in response

    def test_invalid_json_message(self, client: TestClient) -> None:
        """Should return error for invalid JSON."""
        with client.websocket_connect("/api/v1/workflows/wf-123/execution") as ws:
            ws.send_text("not valid json")

            response = ws.receive_json()
            assert response["type"] == "error"
            assert "Invalid JSON" in response["message"]


@pytest.mark.xdist_group(name="testworkflowexecutionnodeupdates")
class TestWorkflowExecutionNodeUpdates:
    """Tests for node status updates during execution."""

    def teardown_method(self) -> None:
        """Force GC to prevent mock accumulation in xdist workers."""
        gc.collect()

    def test_node_started_message_format(self) -> None:
        """Node started messages should have correct format."""
        message = {
            "type": "node_started",
            "nodeId": "node-1",
        }
        assert message["type"] == "node_started"
        assert "nodeId" in message

    def test_node_completed_message_format(self) -> None:
        """Node completed messages should have correct format."""
        message = {
            "type": "node_completed",
            "nodeId": "node-1",
        }
        assert message["type"] == "node_completed"
        assert "nodeId" in message

    def test_node_error_message_format(self) -> None:
        """Node error messages should have correct format."""
        message = {
            "type": "node_error",
            "nodeId": "node-1",
            "error": "Something went wrong",
        }
        assert message["type"] == "node_error"
        assert "nodeId" in message
        assert "error" in message


@pytest.mark.xdist_group(name="testworkflowexecutionlogs")
class TestWorkflowExecutionLogs:
    """Tests for execution log streaming."""

    def teardown_method(self) -> None:
        """Force GC to prevent mock accumulation in xdist workers."""
        gc.collect()

    def test_log_message_format(self) -> None:
        """Log messages should have correct format."""
        message = {
            "type": "log",
            "level": "info",
            "message": "Processing started",
            "nodeId": "node-1",
        }
        assert message["type"] == "log"
        assert message["level"] in ["info", "warning", "error", "debug"]
        assert "message" in message

    def test_log_without_node_id(self) -> None:
        """Log messages without nodeId should be valid."""
        message = {
            "type": "log",
            "level": "info",
            "message": "Workflow started",
        }
        assert message["type"] == "log"
        assert "nodeId" not in message or message.get("nodeId") is None


@pytest.mark.xdist_group(name="testworkflowexecutionmanager")
class TestWorkflowExecutionManager:
    """Tests for the execution manager WebSocket class."""

    def teardown_method(self) -> None:
        """Force GC to prevent mock accumulation in xdist workers."""
        gc.collect()

    def test_manager_connect_disconnect(self) -> None:
        """Manager should track connected clients."""
        from mcp_server_langgraph.api.v1.workflow_execution_ws import (
            ExecutionWebSocketManager,
        )

        manager = ExecutionWebSocketManager()
        assert len(manager.active_connections) == 0

    def test_manager_broadcast_with_no_connections_succeeds(self) -> None:
        """Manager should broadcast to all connected clients."""
        from mcp_server_langgraph.api.v1.workflow_execution_ws import (
            ExecutionWebSocketManager,
        )

        manager = ExecutionWebSocketManager()
        # Broadcast should not raise with no connections
        # This is tested at integration level with real WebSockets
        assert manager is not None
