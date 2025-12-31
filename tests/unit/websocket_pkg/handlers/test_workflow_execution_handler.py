"""
Unit tests for Workflow Execution WebSocket Handler.

Tests the WorkflowExecutionHandler class for real-time workflow execution.
"""

from __future__ import annotations

import gc
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

pytestmark = [
    pytest.mark.unit,
    pytest.mark.websocket,
    pytest.mark.xdist_group(name="websocket_workflow_execution_handler"),
]

RATE_LIMITER_PATCH = "mcp_server_langgraph.websocket.rate_limiter.get_websocket_rate_limiter"


@pytest.mark.xdist_group(name="websocket_workflow_execution_init")
class TestWorkflowExecutionHandlerInit:
    """Tests for WorkflowExecutionHandler initialization."""

    def teardown_method(self) -> None:
        """Force GC to prevent mock accumulation in xdist workers."""
        gc.collect()

    def test_init_stores_execution_service(self) -> None:
        """GIVEN execution_service WHEN creating handler THEN stores service."""
        from mcp_server_langgraph.websocket.handlers.workflow_execution import (
            WorkflowExecutionHandler,
        )
        from mcp_server_langgraph.websocket.types import WebSocketConfig

        config = WebSocketConfig(endpoint_name="workflow-execution")
        mock_service = MagicMock()

        with patch(RATE_LIMITER_PATCH, return_value=MagicMock()):
            handler = WorkflowExecutionHandler(
                config=config,
                execution_service=mock_service,
                workflow_id="workflow-123",
            )

        assert handler._execution_service is mock_service
        assert handler._workflow_id == "workflow-123"
        assert handler._current_execution_id is None

    def test_init_with_metrics(self) -> None:
        """GIVEN metrics WHEN creating handler THEN stores metrics."""
        from mcp_server_langgraph.websocket.handlers.workflow_execution import (
            WorkflowExecutionHandler,
        )
        from mcp_server_langgraph.websocket.types import WebSocketConfig

        config = WebSocketConfig(endpoint_name="workflow-execution")
        mock_service = MagicMock()
        mock_metrics = MagicMock()

        with patch(RATE_LIMITER_PATCH, return_value=MagicMock()):
            handler = WorkflowExecutionHandler(
                config=config,
                execution_service=mock_service,
                workflow_id="workflow-123",
                metrics=mock_metrics,
            )

        assert handler._metrics is mock_metrics


@pytest.mark.xdist_group(name="websocket_workflow_execution_lifecycle")
class TestWorkflowExecutionHandlerLifecycle:
    """Tests for WorkflowExecutionHandler lifecycle hooks."""

    def teardown_method(self) -> None:
        """Force GC to prevent mock accumulation in xdist workers."""
        gc.collect()

    @pytest.mark.asyncio
    async def test_on_connect_logs(self) -> None:
        """GIVEN user WHEN on_connect called THEN logs connection."""
        from mcp_server_langgraph.websocket.handlers.workflow_execution import (
            WorkflowExecutionHandler,
        )
        from mcp_server_langgraph.websocket.types import AuthUser, WebSocketConfig

        config = WebSocketConfig(endpoint_name="workflow-execution")
        mock_service = AsyncMock()  # noqa: async-mock-config

        with patch(RATE_LIMITER_PATCH, return_value=MagicMock()):
            handler = WorkflowExecutionHandler(
                config=config,
                execution_service=mock_service,
                workflow_id="workflow-123",
            )

        user = AuthUser(id="user-123", username="testuser")

        # Should not raise
        await handler.on_connect(user)

    @pytest.mark.asyncio
    async def test_on_disconnect_logs(self) -> None:
        """GIVEN connected WHEN on_disconnect called THEN logs."""
        from mcp_server_langgraph.websocket.handlers.workflow_execution import (
            WorkflowExecutionHandler,
        )
        from mcp_server_langgraph.websocket.types import WebSocketConfig

        config = WebSocketConfig(endpoint_name="workflow-execution")
        mock_service = AsyncMock()  # noqa: async-mock-config

        with patch(RATE_LIMITER_PATCH, return_value=MagicMock()):
            handler = WorkflowExecutionHandler(
                config=config,
                execution_service=mock_service,
                workflow_id="workflow-123",
            )

        # Should not raise
        await handler.on_disconnect()


@pytest.mark.xdist_group(name="websocket_workflow_execution_messages")
class TestWorkflowExecutionHandlerMessages:
    """Tests for WorkflowExecutionHandler message handling."""

    def teardown_method(self) -> None:
        """Force GC to prevent mock accumulation in xdist workers."""
        gc.collect()

    @pytest.mark.asyncio
    async def test_handle_start(self) -> None:
        """GIVEN start message WHEN handle_message called THEN starts execution."""
        from mcp_server_langgraph.websocket.handlers.workflow_execution import (
            WorkflowExecutionHandler,
        )
        from mcp_server_langgraph.websocket.types import MessageEnvelope, WebSocketConfig

        config = WebSocketConfig(endpoint_name="workflow-execution")
        mock_service = AsyncMock()  # noqa: async-mock-config
        mock_service.start_execution.return_value = "exec-123"

        with patch(RATE_LIMITER_PATCH, return_value=MagicMock()):
            handler = WorkflowExecutionHandler(
                config=config,
                execution_service=mock_service,
                workflow_id="workflow-123",
            )

        message = MessageEnvelope(type="start", id="msg-1", payload={"input": {"key": "value"}})
        response = await handler.handle_message(message)

        assert response is not None
        assert response.type == "execution_started"
        assert response.id == "msg-1"
        assert response.payload["execution_id"] == "exec-123"
        assert handler._current_execution_id == "exec-123"
        mock_service.start_execution.assert_called_once_with("workflow-123", {"key": "value"})

    @pytest.mark.asyncio
    async def test_handle_start_no_input(self) -> None:
        """GIVEN start message without input WHEN handle_message called THEN starts."""
        from mcp_server_langgraph.websocket.handlers.workflow_execution import (
            WorkflowExecutionHandler,
        )
        from mcp_server_langgraph.websocket.types import MessageEnvelope, WebSocketConfig

        config = WebSocketConfig(endpoint_name="workflow-execution")
        mock_service = AsyncMock()  # noqa: async-mock-config
        mock_service.start_execution.return_value = "exec-123"

        with patch(RATE_LIMITER_PATCH, return_value=MagicMock()):
            handler = WorkflowExecutionHandler(
                config=config,
                execution_service=mock_service,
                workflow_id="workflow-123",
            )

        message = MessageEnvelope(type="start", id="msg-1")
        response = await handler.handle_message(message)

        assert response is not None
        assert response.type == "execution_started"
        mock_service.start_execution.assert_called_once_with("workflow-123", None)

    @pytest.mark.asyncio
    async def test_handle_start_error(self) -> None:
        """GIVEN service error WHEN start THEN returns error."""
        from mcp_server_langgraph.websocket.handlers.workflow_execution import (
            WorkflowExecutionHandler,
        )
        from mcp_server_langgraph.websocket.types import MessageEnvelope, WebSocketConfig

        config = WebSocketConfig(endpoint_name="workflow-execution")
        mock_service = AsyncMock()  # noqa: async-mock-config
        mock_service.start_execution.side_effect = Exception("Workflow not found")

        with patch(RATE_LIMITER_PATCH, return_value=MagicMock()):
            handler = WorkflowExecutionHandler(
                config=config,
                execution_service=mock_service,
                workflow_id="workflow-123",
            )

        message = MessageEnvelope(type="start", id="msg-1")
        response = await handler.handle_message(message)

        assert response is not None
        assert response.type == "error"
        assert response.payload["code"] == "start_failed"

    @pytest.mark.asyncio
    async def test_handle_stop(self) -> None:
        """GIVEN stop message WHEN handle_message called THEN stops execution."""
        from mcp_server_langgraph.websocket.handlers.workflow_execution import (
            WorkflowExecutionHandler,
        )
        from mcp_server_langgraph.websocket.types import MessageEnvelope, WebSocketConfig

        config = WebSocketConfig(endpoint_name="workflow-execution")
        mock_service = AsyncMock()  # noqa: async-mock-config
        mock_service.stop_execution.return_value = True

        with patch(RATE_LIMITER_PATCH, return_value=MagicMock()):
            handler = WorkflowExecutionHandler(
                config=config,
                execution_service=mock_service,
                workflow_id="workflow-123",
            )

        handler._current_execution_id = "exec-123"

        message = MessageEnvelope(type="stop", id="msg-1")
        response = await handler.handle_message(message)

        assert response is not None
        assert response.type == "execution_stopped"
        assert response.id == "msg-1"
        assert handler._current_execution_id is None
        mock_service.stop_execution.assert_called_once_with("workflow-123")

    @pytest.mark.asyncio
    async def test_handle_stop_no_execution(self) -> None:
        """GIVEN no running execution WHEN stop THEN returns error."""
        from mcp_server_langgraph.websocket.handlers.workflow_execution import (
            WorkflowExecutionHandler,
        )
        from mcp_server_langgraph.websocket.types import MessageEnvelope, WebSocketConfig

        config = WebSocketConfig(endpoint_name="workflow-execution")
        mock_service = AsyncMock()  # noqa: async-mock-config
        mock_service.stop_execution.return_value = False

        with patch(RATE_LIMITER_PATCH, return_value=MagicMock()):
            handler = WorkflowExecutionHandler(
                config=config,
                execution_service=mock_service,
                workflow_id="workflow-123",
            )

        message = MessageEnvelope(type="stop", id="msg-1")
        response = await handler.handle_message(message)

        assert response is not None
        assert response.type == "error"
        assert response.payload["code"] == "stop_failed"

    @pytest.mark.asyncio
    async def test_handle_stop_error(self) -> None:
        """GIVEN service error WHEN stop THEN returns error."""
        from mcp_server_langgraph.websocket.handlers.workflow_execution import (
            WorkflowExecutionHandler,
        )
        from mcp_server_langgraph.websocket.types import MessageEnvelope, WebSocketConfig

        config = WebSocketConfig(endpoint_name="workflow-execution")
        mock_service = AsyncMock()  # noqa: async-mock-config
        mock_service.stop_execution.side_effect = Exception("Stop failed")

        with patch(RATE_LIMITER_PATCH, return_value=MagicMock()):
            handler = WorkflowExecutionHandler(
                config=config,
                execution_service=mock_service,
                workflow_id="workflow-123",
            )

        message = MessageEnvelope(type="stop", id="msg-1")
        response = await handler.handle_message(message)

        assert response is not None
        assert response.type == "error"
        assert response.payload["code"] == "stop_failed"

    @pytest.mark.asyncio
    async def test_handle_status(self) -> None:
        """GIVEN status message WHEN handle_message called THEN returns status."""
        from mcp_server_langgraph.websocket.handlers.workflow_execution import (
            WorkflowExecutionHandler,
        )
        from mcp_server_langgraph.websocket.types import MessageEnvelope, WebSocketConfig

        config = WebSocketConfig(endpoint_name="workflow-execution")
        mock_service = AsyncMock()  # noqa: async-mock-config
        mock_service.get_execution_status.return_value = {
            "state": "running",
            "current_node": "process_data",
            "progress": 0.5,
        }

        with patch(RATE_LIMITER_PATCH, return_value=MagicMock()):
            handler = WorkflowExecutionHandler(
                config=config,
                execution_service=mock_service,
                workflow_id="workflow-123",
            )

        message = MessageEnvelope(type="status", id="msg-1")
        response = await handler.handle_message(message)

        assert response is not None
        assert response.type == "execution_status"
        assert response.id == "msg-1"
        assert response.payload["workflow_id"] == "workflow-123"
        assert response.payload["status"]["state"] == "running"
        mock_service.get_execution_status.assert_called_once_with("workflow-123")

    @pytest.mark.asyncio
    async def test_handle_status_error(self) -> None:
        """GIVEN service error WHEN status THEN returns error."""
        from mcp_server_langgraph.websocket.handlers.workflow_execution import (
            WorkflowExecutionHandler,
        )
        from mcp_server_langgraph.websocket.types import MessageEnvelope, WebSocketConfig

        config = WebSocketConfig(endpoint_name="workflow-execution")
        mock_service = AsyncMock()  # noqa: async-mock-config
        mock_service.get_execution_status.side_effect = Exception("Status unavailable")

        with patch(RATE_LIMITER_PATCH, return_value=MagicMock()):
            handler = WorkflowExecutionHandler(
                config=config,
                execution_service=mock_service,
                workflow_id="workflow-123",
            )

        message = MessageEnvelope(type="status", id="msg-1")
        response = await handler.handle_message(message)

        assert response is not None
        assert response.type == "error"
        assert response.payload["code"] == "status_failed"

    @pytest.mark.asyncio
    async def test_handle_unknown_message_type(self) -> None:
        """GIVEN unknown message type WHEN handle_message called THEN returns error."""
        from mcp_server_langgraph.websocket.handlers.workflow_execution import (
            WorkflowExecutionHandler,
        )
        from mcp_server_langgraph.websocket.types import MessageEnvelope, WebSocketConfig

        config = WebSocketConfig(endpoint_name="workflow-execution")
        mock_service = AsyncMock()  # noqa: async-mock-config

        with patch(RATE_LIMITER_PATCH, return_value=MagicMock()):
            handler = WorkflowExecutionHandler(
                config=config,
                execution_service=mock_service,
                workflow_id="workflow-123",
            )

        message = MessageEnvelope(type="invalid", id="msg-1")
        response = await handler.handle_message(message)

        assert response is not None
        assert response.type == "error"
        assert response.payload["code"] == "unknown_message_type"


@pytest.mark.xdist_group(name="websocket_workflow_execution_push")
class TestWorkflowExecutionHandlerPush:
    """Tests for WorkflowExecutionHandler push functionality."""

    def teardown_method(self) -> None:
        """Force GC to prevent mock accumulation in xdist workers."""
        gc.collect()

    @pytest.mark.asyncio
    async def test_push_node_update(self) -> None:
        """GIVEN websocket WHEN push_node_update THEN sends."""
        from mcp_server_langgraph.websocket.handlers.workflow_execution import (
            WorkflowExecutionHandler,
        )
        from mcp_server_langgraph.websocket.types import WebSocketConfig

        config = WebSocketConfig(endpoint_name="workflow-execution")
        mock_service = AsyncMock()  # noqa: async-mock-config

        with patch(RATE_LIMITER_PATCH, return_value=MagicMock()):
            handler = WorkflowExecutionHandler(
                config=config,
                execution_service=mock_service,
                workflow_id="workflow-123",
            )

        mock_ws = AsyncMock()  # noqa: async-mock-config
        handler._websocket = mock_ws

        await handler.push_node_update("node-1", "started", {"input": "data"})

        mock_ws.send_json.assert_called_once()
        sent_data = mock_ws.send_json.call_args[0][0]
        assert sent_data["type"] == "node_started"
        assert sent_data["payload"]["node_id"] == "node-1"

    @pytest.mark.asyncio
    async def test_push_node_update_completed(self) -> None:
        """GIVEN completed status WHEN push_node_update THEN sends node_completed."""
        from mcp_server_langgraph.websocket.handlers.workflow_execution import (
            WorkflowExecutionHandler,
        )
        from mcp_server_langgraph.websocket.types import WebSocketConfig

        config = WebSocketConfig(endpoint_name="workflow-execution")
        mock_service = AsyncMock()  # noqa: async-mock-config

        with patch(RATE_LIMITER_PATCH, return_value=MagicMock()):
            handler = WorkflowExecutionHandler(
                config=config,
                execution_service=mock_service,
                workflow_id="workflow-123",
            )

        mock_ws = AsyncMock()  # noqa: async-mock-config
        handler._websocket = mock_ws

        await handler.push_node_update("node-1", "completed")

        mock_ws.send_json.assert_called_once()
        sent_data = mock_ws.send_json.call_args[0][0]
        assert sent_data["type"] == "node_completed"

    @pytest.mark.asyncio
    async def test_push_node_update_no_websocket(self) -> None:
        """GIVEN no websocket WHEN push_node_update THEN does not send."""
        from mcp_server_langgraph.websocket.handlers.workflow_execution import (
            WorkflowExecutionHandler,
        )
        from mcp_server_langgraph.websocket.types import WebSocketConfig

        config = WebSocketConfig(endpoint_name="workflow-execution")
        mock_service = AsyncMock()  # noqa: async-mock-config

        with patch(RATE_LIMITER_PATCH, return_value=MagicMock()):
            handler = WorkflowExecutionHandler(
                config=config,
                execution_service=mock_service,
                workflow_id="workflow-123",
            )

        # No websocket
        await handler.push_node_update("node-1", "started")
        # Should not raise

    @pytest.mark.asyncio
    async def test_push_log(self) -> None:
        """GIVEN websocket WHEN push_log THEN sends."""
        from mcp_server_langgraph.websocket.handlers.workflow_execution import (
            WorkflowExecutionHandler,
        )
        from mcp_server_langgraph.websocket.types import WebSocketConfig

        config = WebSocketConfig(endpoint_name="workflow-execution")
        mock_service = AsyncMock()  # noqa: async-mock-config

        with patch(RATE_LIMITER_PATCH, return_value=MagicMock()):
            handler = WorkflowExecutionHandler(
                config=config,
                execution_service=mock_service,
                workflow_id="workflow-123",
            )

        mock_ws = AsyncMock()  # noqa: async-mock-config
        handler._websocket = mock_ws

        await handler.push_log("info", "Processing started", "node-1")

        mock_ws.send_json.assert_called_once()
        sent_data = mock_ws.send_json.call_args[0][0]
        assert sent_data["type"] == "log"
        assert sent_data["payload"]["level"] == "info"
        assert sent_data["payload"]["message"] == "Processing started"
        assert sent_data["payload"]["node_id"] == "node-1"

    @pytest.mark.asyncio
    async def test_push_log_without_node_id(self) -> None:
        """GIVEN no node_id WHEN push_log THEN sends without node_id."""
        from mcp_server_langgraph.websocket.handlers.workflow_execution import (
            WorkflowExecutionHandler,
        )
        from mcp_server_langgraph.websocket.types import WebSocketConfig

        config = WebSocketConfig(endpoint_name="workflow-execution")
        mock_service = AsyncMock()  # noqa: async-mock-config

        with patch(RATE_LIMITER_PATCH, return_value=MagicMock()):
            handler = WorkflowExecutionHandler(
                config=config,
                execution_service=mock_service,
                workflow_id="workflow-123",
            )

        mock_ws = AsyncMock()  # noqa: async-mock-config
        handler._websocket = mock_ws

        await handler.push_log("warning", "Warning message")

        mock_ws.send_json.assert_called_once()
        sent_data = mock_ws.send_json.call_args[0][0]
        assert "node_id" not in sent_data["payload"]

    @pytest.mark.asyncio
    async def test_push_execution_completed(self) -> None:
        """GIVEN websocket WHEN push_execution_completed THEN sends."""
        from mcp_server_langgraph.websocket.handlers.workflow_execution import (
            WorkflowExecutionHandler,
        )
        from mcp_server_langgraph.websocket.types import WebSocketConfig

        config = WebSocketConfig(endpoint_name="workflow-execution")
        mock_service = AsyncMock()  # noqa: async-mock-config

        with patch(RATE_LIMITER_PATCH, return_value=MagicMock()):
            handler = WorkflowExecutionHandler(
                config=config,
                execution_service=mock_service,
                workflow_id="workflow-123",
            )

        mock_ws = AsyncMock()  # noqa: async-mock-config
        handler._websocket = mock_ws

        await handler.push_execution_completed({"output": "result"})

        mock_ws.send_json.assert_called_once()
        sent_data = mock_ws.send_json.call_args[0][0]
        assert sent_data["type"] == "execution_completed"
        assert sent_data["payload"]["workflow_id"] == "workflow-123"
        assert sent_data["payload"]["result"] == {"output": "result"}

    @pytest.mark.asyncio
    async def test_push_execution_completed_no_result(self) -> None:
        """GIVEN no result WHEN push_execution_completed THEN sends without result."""
        from mcp_server_langgraph.websocket.handlers.workflow_execution import (
            WorkflowExecutionHandler,
        )
        from mcp_server_langgraph.websocket.types import WebSocketConfig

        config = WebSocketConfig(endpoint_name="workflow-execution")
        mock_service = AsyncMock()  # noqa: async-mock-config

        with patch(RATE_LIMITER_PATCH, return_value=MagicMock()):
            handler = WorkflowExecutionHandler(
                config=config,
                execution_service=mock_service,
                workflow_id="workflow-123",
            )

        mock_ws = AsyncMock()  # noqa: async-mock-config
        handler._websocket = mock_ws

        await handler.push_execution_completed()

        mock_ws.send_json.assert_called_once()
        sent_data = mock_ws.send_json.call_args[0][0]
        assert "result" not in sent_data["payload"]

    @pytest.mark.asyncio
    async def test_push_execution_error(self) -> None:
        """GIVEN websocket WHEN push_execution_error THEN sends."""
        from mcp_server_langgraph.websocket.handlers.workflow_execution import (
            WorkflowExecutionHandler,
        )
        from mcp_server_langgraph.websocket.types import WebSocketConfig

        config = WebSocketConfig(endpoint_name="workflow-execution")
        mock_service = AsyncMock()  # noqa: async-mock-config

        with patch(RATE_LIMITER_PATCH, return_value=MagicMock()):
            handler = WorkflowExecutionHandler(
                config=config,
                execution_service=mock_service,
                workflow_id="workflow-123",
            )

        mock_ws = AsyncMock()  # noqa: async-mock-config
        handler._websocket = mock_ws

        await handler.push_execution_error("Node failed: timeout")

        mock_ws.send_json.assert_called_once()
        sent_data = mock_ws.send_json.call_args[0][0]
        assert sent_data["type"] == "execution_error"
        assert sent_data["payload"]["workflow_id"] == "workflow-123"
        assert sent_data["payload"]["error"] == "Node failed: timeout"


@pytest.mark.xdist_group(name="websocket_workflow_execution_protocol")
class TestExecutionServiceProtocol:
    """Tests for ExecutionServiceProtocol."""

    def teardown_method(self) -> None:
        """Force GC to prevent mock accumulation in xdist workers."""
        gc.collect()

    def test_protocol_is_runtime_checkable(self) -> None:
        """GIVEN ExecutionServiceProtocol WHEN checking isinstance THEN works."""
        from mcp_server_langgraph.websocket.handlers.workflow_execution import (
            ExecutionServiceProtocol,
        )

        class MockExecutionService:
            async def get_workflow(self, workflow_id: str):
                return None

            async def start_execution(self, workflow_id: str, input_data=None):
                return "exec-id"

            async def stop_execution(self, workflow_id: str):
                return True

            async def get_execution_status(self, workflow_id: str):
                return {}

        service = MockExecutionService()
        assert isinstance(service, ExecutionServiceProtocol)
