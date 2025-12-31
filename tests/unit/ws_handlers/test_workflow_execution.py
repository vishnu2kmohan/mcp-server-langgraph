"""
Workflow Execution WebSocket Handler Tests.

TDD tests for the Workflow Execution WebSocket using the standardized WebSocketBase.
"""

from __future__ import annotations

import gc
from unittest.mock import AsyncMock, MagicMock

import pytest

from mcp_server_langgraph.websocket import (
    MessageEnvelope,
    WebSocketConfig,
)

pytestmark = [pytest.mark.unit, pytest.mark.websocket]


@pytest.fixture
def mock_websocket() -> MagicMock:
    """Create a mock WebSocket for testing."""
    ws = MagicMock()
    ws.accept = AsyncMock()  # noqa: async-mock-config
    ws.close = AsyncMock()  # noqa: async-mock-config
    ws.send_json = AsyncMock()  # noqa: async-mock-config
    ws.send_text = AsyncMock()  # noqa: async-mock-config
    ws.receive_json = AsyncMock()  # noqa: async-mock-config
    ws.receive_text = AsyncMock()  # noqa: async-mock-config
    ws.query_params = {}
    ws.headers = {}
    ws.client_state = MagicMock()
    return ws


@pytest.fixture
def mock_execution_service() -> MagicMock:
    """Create a mock execution service."""
    service = MagicMock()
    service.get_workflow = AsyncMock(
        return_value={
            "id": "workflow-1",
            "name": "Test Workflow",
            "nodes": [],
        }
    )
    service.start_execution = AsyncMock(return_value="exec-123")
    service.stop_execution = AsyncMock(return_value=True)
    service.get_execution_status = AsyncMock(
        return_value={
            "id": "exec-123",
            "status": "running",
        }
    )
    return service


@pytest.mark.xdist_group(name="workflow_execution_ws")
class TestWorkflowExecutionHandler:
    """Test Workflow Execution WebSocket using WebSocketBase."""

    def teardown_method(self) -> None:
        """Force GC to prevent mock accumulation in xdist workers."""
        gc.collect()

    @pytest.mark.asyncio
    async def test_handler_extends_websocket_base(self) -> None:
        """
        GIVEN the WorkflowExecutionHandler class
        WHEN checking its base classes
        THEN it should extend WebSocketBase.
        """
        from mcp_server_langgraph.websocket.base import WebSocketBase
        from mcp_server_langgraph.websocket.handlers.workflow_execution import (
            WorkflowExecutionHandler,
        )

        assert issubclass(WorkflowExecutionHandler, WebSocketBase)

    @pytest.mark.asyncio
    async def test_handles_start_message(self, mock_websocket: MagicMock, mock_execution_service: MagicMock) -> None:
        """
        GIVEN an active connection
        WHEN a start message is received
        THEN execution should be started and response sent.
        """
        from mcp_server_langgraph.websocket.handlers.workflow_execution import (
            WorkflowExecutionHandler,
        )

        handler = WorkflowExecutionHandler(
            config=WebSocketConfig(require_auth=False, endpoint_name="workflow-exec"),
            execution_service=mock_execution_service,
            workflow_id="workflow-1",
        )

        message = MessageEnvelope(
            type="start",
            payload={"input": {"key": "value"}},
        )

        response = await handler.handle_message(message)

        assert response is not None
        assert response.type == "execution_started"
        assert response.payload is not None
        assert response.payload.get("execution_id") == "exec-123"
        mock_execution_service.start_execution.assert_called_once()

    @pytest.mark.asyncio
    async def test_handles_stop_message(self, mock_websocket: MagicMock, mock_execution_service: MagicMock) -> None:
        """
        GIVEN an active execution
        WHEN a stop message is received
        THEN execution should be stopped and response sent.
        """
        from mcp_server_langgraph.websocket.handlers.workflow_execution import (
            WorkflowExecutionHandler,
        )

        handler = WorkflowExecutionHandler(
            config=WebSocketConfig(require_auth=False, endpoint_name="workflow-exec"),
            execution_service=mock_execution_service,
            workflow_id="workflow-1",
        )

        message = MessageEnvelope(
            type="stop",
            payload={},
        )

        response = await handler.handle_message(message)

        assert response is not None
        assert response.type == "execution_stopped"
        mock_execution_service.stop_execution.assert_called_once()

    @pytest.mark.asyncio
    async def test_handles_status_message(self, mock_websocket: MagicMock, mock_execution_service: MagicMock) -> None:
        """
        GIVEN an active execution
        WHEN a status message is received
        THEN current execution status should be returned.
        """
        from mcp_server_langgraph.websocket.handlers.workflow_execution import (
            WorkflowExecutionHandler,
        )

        handler = WorkflowExecutionHandler(
            config=WebSocketConfig(require_auth=False, endpoint_name="workflow-exec"),
            execution_service=mock_execution_service,
            workflow_id="workflow-1",
        )

        message = MessageEnvelope(
            type="status",
            payload={},
        )

        response = await handler.handle_message(message)

        assert response is not None
        assert response.type == "execution_status"
        mock_execution_service.get_execution_status.assert_called_once()

    @pytest.mark.asyncio
    async def test_returns_error_for_unknown_message(
        self, mock_websocket: MagicMock, mock_execution_service: MagicMock
    ) -> None:
        """
        GIVEN an active connection
        WHEN an unknown message type is received
        THEN an error response should be returned.
        """
        from mcp_server_langgraph.websocket.handlers.workflow_execution import (
            WorkflowExecutionHandler,
        )

        handler = WorkflowExecutionHandler(
            config=WebSocketConfig(require_auth=False, endpoint_name="workflow-exec"),
            execution_service=mock_execution_service,
            workflow_id="workflow-1",
        )

        message = MessageEnvelope(
            type="unknown_type",
            payload={},
        )

        response = await handler.handle_message(message)

        assert response is not None
        assert response.type == "error"

    @pytest.mark.asyncio
    async def test_push_node_update(self, mock_websocket: MagicMock, mock_execution_service: MagicMock) -> None:
        """
        GIVEN an active connection
        WHEN push_node_update is called
        THEN node update should be sent to client.
        """
        from mcp_server_langgraph.websocket.handlers.workflow_execution import (
            WorkflowExecutionHandler,
        )

        handler = WorkflowExecutionHandler(
            config=WebSocketConfig(require_auth=False, endpoint_name="workflow-exec"),
            execution_service=mock_execution_service,
            workflow_id="workflow-1",
        )
        handler._websocket = mock_websocket

        await handler.push_node_update("node-1", "started")

        mock_websocket.send_json.assert_called_once()
        call_args = mock_websocket.send_json.call_args[0][0]
        assert call_args["type"] == "node_started"
        assert call_args["payload"]["node_id"] == "node-1"
