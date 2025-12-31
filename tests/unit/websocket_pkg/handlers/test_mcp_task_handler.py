"""
Unit tests for MCP Task WebSocket Handler.

Tests the MCPTaskWebSocketHandler class for MCP task status updates.
"""

from __future__ import annotations

import gc
from datetime import datetime
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

pytestmark = [
    pytest.mark.unit,
    pytest.mark.websocket,
    pytest.mark.xdist_group(name="websocket_mcp_task_handler"),
]

RATE_LIMITER_PATCH = "mcp_server_langgraph.websocket.rate_limiter.get_websocket_rate_limiter"


class MockTask:
    """Mock task object for testing."""

    def __init__(
        self,
        task_id: str,
        status: str = "pending",
        created_at: datetime | None = None,
        last_updated_at: datetime | None = None,
    ):
        self.task_id = task_id
        self.status = MagicMock(value=status)
        self.created_at = created_at or datetime.now()
        self.last_updated_at = last_updated_at or datetime.now()
        self.ttl = 3600
        self.poll_interval = 5
        self.status_message = None


@pytest.mark.xdist_group(name="websocket_mcp_task_init")
class TestMCPTaskWebSocketHandlerInit:
    """Tests for MCPTaskWebSocketHandler initialization."""

    def teardown_method(self) -> None:
        """Force GC to prevent mock accumulation in xdist workers."""
        gc.collect()

    def test_init_stores_mcp_service(self) -> None:
        """GIVEN mcp_service WHEN creating handler THEN stores service."""
        from mcp_server_langgraph.websocket.handlers.mcp_task import (
            MCPTaskWebSocketHandler,
        )
        from mcp_server_langgraph.websocket.types import WebSocketConfig

        config = WebSocketConfig(endpoint_name="mcp-tasks")
        mock_service = MagicMock()

        with patch(RATE_LIMITER_PATCH, return_value=MagicMock()):
            handler = MCPTaskWebSocketHandler(config=config, mcp_service=mock_service)

        assert handler._mcp_service is mock_service
        assert handler.subscriptions == set()

    def test_init_with_metrics(self) -> None:
        """GIVEN metrics WHEN creating handler THEN stores metrics."""
        from mcp_server_langgraph.websocket.handlers.mcp_task import (
            MCPTaskWebSocketHandler,
        )
        from mcp_server_langgraph.websocket.types import WebSocketConfig

        config = WebSocketConfig(endpoint_name="mcp-tasks")
        mock_service = MagicMock()
        mock_metrics = MagicMock()

        with patch(RATE_LIMITER_PATCH, return_value=MagicMock()):
            handler = MCPTaskWebSocketHandler(config=config, mcp_service=mock_service, metrics=mock_metrics)

        assert handler._metrics is mock_metrics


@pytest.mark.xdist_group(name="websocket_mcp_task_lifecycle")
class TestMCPTaskWebSocketHandlerLifecycle:
    """Tests for MCPTaskWebSocketHandler lifecycle hooks."""

    def teardown_method(self) -> None:
        """Force GC to prevent mock accumulation in xdist workers."""
        gc.collect()

    @pytest.mark.asyncio
    async def test_on_connect_sends_task_list(self) -> None:
        """GIVEN user WHEN on_connect called THEN sends task list."""
        from mcp_server_langgraph.websocket.handlers.mcp_task import (
            MCPTaskWebSocketHandler,
        )
        from mcp_server_langgraph.websocket.types import AuthUser, WebSocketConfig

        config = WebSocketConfig(endpoint_name="mcp-tasks")
        mock_service = AsyncMock()  # noqa: async-mock-config
        mock_service.list_tasks.return_value = [
            MockTask("task-1", "running"),
            MockTask("task-2", "pending"),
        ]

        with patch(RATE_LIMITER_PATCH, return_value=MagicMock()):
            handler = MCPTaskWebSocketHandler(config=config, mcp_service=mock_service)

        mock_ws = AsyncMock()  # noqa: async-mock-config
        handler._websocket = mock_ws
        user = AuthUser(id="user-123", username="testuser")

        await handler.on_connect(user)

        mock_service.list_tasks.assert_called_once()
        mock_ws.send_json.assert_called_once()
        sent_data = mock_ws.send_json.call_args[0][0]
        assert sent_data["type"] == "task_list"
        assert len(sent_data["tasks"]) == 2

    @pytest.mark.asyncio
    async def test_on_disconnect_clears_subscriptions(self) -> None:
        """GIVEN subscriptions WHEN on_disconnect called THEN clears."""
        from mcp_server_langgraph.websocket.handlers.mcp_task import (
            MCPTaskWebSocketHandler,
        )
        from mcp_server_langgraph.websocket.types import WebSocketConfig

        config = WebSocketConfig(endpoint_name="mcp-tasks")
        mock_service = AsyncMock()  # noqa: async-mock-config

        with patch(RATE_LIMITER_PATCH, return_value=MagicMock()):
            handler = MCPTaskWebSocketHandler(config=config, mcp_service=mock_service)

        handler.subscriptions = {"task-1", "task-2"}

        await handler.on_disconnect()

        assert handler.subscriptions == set()


@pytest.mark.xdist_group(name="websocket_mcp_task_messages")
class TestMCPTaskWebSocketHandlerMessages:
    """Tests for MCPTaskWebSocketHandler message handling."""

    def teardown_method(self) -> None:
        """Force GC to prevent mock accumulation in xdist workers."""
        gc.collect()

    @pytest.mark.asyncio
    async def test_handle_subscribe(self) -> None:
        """GIVEN subscribe message WHEN handle_message called THEN subscribes."""
        from mcp_server_langgraph.websocket.handlers.mcp_task import (
            MCPTaskWebSocketHandler,
        )
        from mcp_server_langgraph.websocket.types import MessageEnvelope, WebSocketConfig

        config = WebSocketConfig(endpoint_name="mcp-tasks")
        mock_service = AsyncMock()  # noqa: async-mock-config
        mock_service.get_task.return_value = MockTask("task-1", "running")

        with patch(RATE_LIMITER_PATCH, return_value=MagicMock()):
            handler = MCPTaskWebSocketHandler(config=config, mcp_service=mock_service)

        message = MessageEnvelope(type="subscribe", id="msg-1", payload={"task_id": "task-1"})
        response = await handler.handle_message(message)

        assert response is not None
        assert response.type == "task_status"
        assert response.id == "msg-1"
        assert "task-1" in handler.subscriptions
        mock_service.get_task.assert_called_once_with("task-1")

    @pytest.mark.asyncio
    async def test_handle_subscribe_missing_task_id(self) -> None:
        """GIVEN subscribe without task_id WHEN handle_message THEN error."""
        from mcp_server_langgraph.websocket.handlers.mcp_task import (
            MCPTaskWebSocketHandler,
        )
        from mcp_server_langgraph.websocket.types import MessageEnvelope, WebSocketConfig

        config = WebSocketConfig(endpoint_name="mcp-tasks")
        mock_service = AsyncMock()  # noqa: async-mock-config

        with patch(RATE_LIMITER_PATCH, return_value=MagicMock()):
            handler = MCPTaskWebSocketHandler(config=config, mcp_service=mock_service)

        message = MessageEnvelope(type="subscribe", id="msg-1", payload={})
        response = await handler.handle_message(message)

        assert response is not None
        assert response.type == "error"
        assert response.payload["code"] == "missing_task_id"

    @pytest.mark.asyncio
    async def test_handle_subscribe_task_not_found(self) -> None:
        """GIVEN non-existent task WHEN subscribe THEN error."""
        from mcp_server_langgraph.websocket.handlers.mcp_task import (
            MCPTaskWebSocketHandler,
        )
        from mcp_server_langgraph.websocket.types import MessageEnvelope, WebSocketConfig

        config = WebSocketConfig(endpoint_name="mcp-tasks")
        mock_service = AsyncMock()  # noqa: async-mock-config
        mock_service.get_task.return_value = None

        with patch(RATE_LIMITER_PATCH, return_value=MagicMock()):
            handler = MCPTaskWebSocketHandler(config=config, mcp_service=mock_service)

        message = MessageEnvelope(type="subscribe", id="msg-1", payload={"task_id": "nonexistent"})
        response = await handler.handle_message(message)

        assert response is not None
        assert response.type == "error"
        assert response.payload["code"] == "task_not_found"

    @pytest.mark.asyncio
    async def test_handle_subscribe_error(self) -> None:
        """GIVEN service error WHEN subscribe THEN returns error."""
        from mcp_server_langgraph.websocket.handlers.mcp_task import (
            MCPTaskWebSocketHandler,
        )
        from mcp_server_langgraph.websocket.types import MessageEnvelope, WebSocketConfig

        config = WebSocketConfig(endpoint_name="mcp-tasks")
        mock_service = AsyncMock()  # noqa: async-mock-config
        mock_service.get_task.side_effect = Exception("Database error")

        with patch(RATE_LIMITER_PATCH, return_value=MagicMock()):
            handler = MCPTaskWebSocketHandler(config=config, mcp_service=mock_service)

        message = MessageEnvelope(type="subscribe", id="msg-1", payload={"task_id": "task-1"})
        response = await handler.handle_message(message)

        assert response is not None
        assert response.type == "error"
        assert response.payload["code"] == "subscribe_error"

    @pytest.mark.asyncio
    async def test_handle_unsubscribe(self) -> None:
        """GIVEN unsubscribe message WHEN handle_message called THEN unsubscribes."""
        from mcp_server_langgraph.websocket.handlers.mcp_task import (
            MCPTaskWebSocketHandler,
        )
        from mcp_server_langgraph.websocket.types import MessageEnvelope, WebSocketConfig

        config = WebSocketConfig(endpoint_name="mcp-tasks")
        mock_service = AsyncMock()  # noqa: async-mock-config

        with patch(RATE_LIMITER_PATCH, return_value=MagicMock()):
            handler = MCPTaskWebSocketHandler(config=config, mcp_service=mock_service)

        handler.subscriptions = {"task-1", "task-2"}

        message = MessageEnvelope(type="unsubscribe", id="msg-1", payload={"task_id": "task-1"})
        response = await handler.handle_message(message)

        assert response is not None
        assert response.type == "unsubscribed"
        assert "task-1" not in handler.subscriptions
        assert "task-2" in handler.subscriptions

    @pytest.mark.asyncio
    async def test_handle_refresh(self) -> None:
        """GIVEN refresh message WHEN handle_message called THEN returns task list."""
        from mcp_server_langgraph.websocket.handlers.mcp_task import (
            MCPTaskWebSocketHandler,
        )
        from mcp_server_langgraph.websocket.types import MessageEnvelope, WebSocketConfig

        config = WebSocketConfig(endpoint_name="mcp-tasks")
        mock_service = AsyncMock()  # noqa: async-mock-config
        mock_service.list_tasks.return_value = [
            MockTask("task-1", "completed"),
            MockTask("task-2", "running"),
        ]

        with patch(RATE_LIMITER_PATCH, return_value=MagicMock()):
            handler = MCPTaskWebSocketHandler(config=config, mcp_service=mock_service)

        message = MessageEnvelope(type="refresh", id="msg-1")
        response = await handler.handle_message(message)

        assert response is not None
        assert response.type == "task_list"
        assert response.id == "msg-1"
        assert len(response.payload["tasks"]) == 2
        mock_service.list_tasks.assert_called_once()

    @pytest.mark.asyncio
    async def test_handle_unknown_message_type(self) -> None:
        """GIVEN unknown message type WHEN handle_message called THEN returns error."""
        from mcp_server_langgraph.websocket.handlers.mcp_task import (
            MCPTaskWebSocketHandler,
        )
        from mcp_server_langgraph.websocket.types import MessageEnvelope, WebSocketConfig

        config = WebSocketConfig(endpoint_name="mcp-tasks")
        mock_service = AsyncMock()  # noqa: async-mock-config

        with patch(RATE_LIMITER_PATCH, return_value=MagicMock()):
            handler = MCPTaskWebSocketHandler(config=config, mcp_service=mock_service)

        message = MessageEnvelope(type="invalid", id="msg-1")
        response = await handler.handle_message(message)

        assert response is not None
        assert response.type == "error"
        assert response.payload["code"] == "unknown_message_type"


@pytest.mark.xdist_group(name="websocket_mcp_task_conversion")
class TestMCPTaskWebSocketHandlerConversion:
    """Tests for MCPTaskWebSocketHandler task conversion."""

    def teardown_method(self) -> None:
        """Force GC to prevent mock accumulation in xdist workers."""
        gc.collect()

    def test_convert_task_to_dict(self) -> None:
        """GIVEN task object WHEN _convert_task_to_dict called THEN returns dict."""
        from mcp_server_langgraph.websocket.handlers.mcp_task import (
            MCPTaskWebSocketHandler,
        )
        from mcp_server_langgraph.websocket.types import WebSocketConfig

        config = WebSocketConfig(endpoint_name="mcp-tasks")
        mock_service = AsyncMock()  # noqa: async-mock-config

        with patch(RATE_LIMITER_PATCH, return_value=MagicMock()):
            handler = MCPTaskWebSocketHandler(config=config, mcp_service=mock_service)

        task = MockTask("task-123", "running")
        task.status_message = "Processing..."

        result = handler._convert_task_to_dict(task)

        assert result["task_id"] == "task-123"
        assert result["status"] == "running"
        assert result["ttl"] == 3600
        assert result["poll_interval"] == 5
        assert result["status_message"] == "Processing..."

    def test_convert_task_to_dict_string_status(self) -> None:
        """GIVEN task with string status WHEN _convert_task_to_dict called THEN converts."""
        from mcp_server_langgraph.websocket.handlers.mcp_task import (
            MCPTaskWebSocketHandler,
        )
        from mcp_server_langgraph.websocket.types import WebSocketConfig

        config = WebSocketConfig(endpoint_name="mcp-tasks")
        mock_service = AsyncMock()  # noqa: async-mock-config

        with patch(RATE_LIMITER_PATCH, return_value=MagicMock()):
            handler = MCPTaskWebSocketHandler(config=config, mcp_service=mock_service)

        task = MockTask("task-123")
        task.status = "pending"  # String instead of enum

        result = handler._convert_task_to_dict(task)

        assert result["status"] == "pending"


@pytest.mark.xdist_group(name="websocket_mcp_task_push")
class TestMCPTaskWebSocketHandlerPush:
    """Tests for MCPTaskWebSocketHandler push functionality."""

    def teardown_method(self) -> None:
        """Force GC to prevent mock accumulation in xdist workers."""
        gc.collect()

    @pytest.mark.asyncio
    async def test_push_task_update_when_subscribed(self) -> None:
        """GIVEN subscribed WHEN push_task_update THEN sends."""
        from mcp_server_langgraph.websocket.handlers.mcp_task import (
            MCPTaskWebSocketHandler,
        )
        from mcp_server_langgraph.websocket.types import WebSocketConfig

        config = WebSocketConfig(endpoint_name="mcp-tasks")
        mock_service = AsyncMock()  # noqa: async-mock-config

        with patch(RATE_LIMITER_PATCH, return_value=MagicMock()):
            handler = MCPTaskWebSocketHandler(config=config, mcp_service=mock_service)

        mock_ws = AsyncMock()  # noqa: async-mock-config
        handler._websocket = mock_ws
        handler.subscriptions.add("task-1")

        task = MockTask("task-1", "completed")
        await handler.push_task_update(task)

        mock_ws.send_json.assert_called_once()

    @pytest.mark.asyncio
    async def test_push_task_update_when_not_subscribed(self) -> None:
        """GIVEN not subscribed WHEN push_task_update THEN does not send."""
        from mcp_server_langgraph.websocket.handlers.mcp_task import (
            MCPTaskWebSocketHandler,
        )
        from mcp_server_langgraph.websocket.types import WebSocketConfig

        config = WebSocketConfig(endpoint_name="mcp-tasks")
        mock_service = AsyncMock()  # noqa: async-mock-config

        with patch(RATE_LIMITER_PATCH, return_value=MagicMock()):
            handler = MCPTaskWebSocketHandler(config=config, mcp_service=mock_service)

        mock_ws = AsyncMock()  # noqa: async-mock-config
        handler._websocket = mock_ws
        # Not subscribed

        task = MockTask("task-1", "completed")
        await handler.push_task_update(task)

        mock_ws.send_json.assert_not_called()

    @pytest.mark.asyncio
    async def test_push_task_update_no_websocket(self) -> None:
        """GIVEN no websocket WHEN push_task_update THEN does not send."""
        from mcp_server_langgraph.websocket.handlers.mcp_task import (
            MCPTaskWebSocketHandler,
        )
        from mcp_server_langgraph.websocket.types import WebSocketConfig

        config = WebSocketConfig(endpoint_name="mcp-tasks")
        mock_service = AsyncMock()  # noqa: async-mock-config

        with patch(RATE_LIMITER_PATCH, return_value=MagicMock()):
            handler = MCPTaskWebSocketHandler(config=config, mcp_service=mock_service)

        handler.subscriptions.add("task-1")
        # No websocket

        task = MockTask("task-1", "completed")
        await handler.push_task_update(task)
        # Should not raise


@pytest.mark.xdist_group(name="websocket_mcp_task_protocol")
class TestMCPServiceProtocol:
    """Tests for MCPServiceProtocol."""

    def teardown_method(self) -> None:
        """Force GC to prevent mock accumulation in xdist workers."""
        gc.collect()

    def test_protocol_is_runtime_checkable(self) -> None:
        """GIVEN MCPServiceProtocol WHEN checking isinstance THEN works."""
        from mcp_server_langgraph.websocket.handlers.mcp_task import MCPServiceProtocol

        class MockMCPService:
            async def list_tasks(self):
                return []

            async def get_task(self, task_id: str):
                return None

        service = MockMCPService()
        assert isinstance(service, MCPServiceProtocol)
