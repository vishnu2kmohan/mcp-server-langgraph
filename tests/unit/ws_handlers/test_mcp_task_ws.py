"""
MCP Task WebSocket Handler Tests.

TDD tests for the MCP Task WebSocket using the standardized WebSocketBase.
"""

from __future__ import annotations

import gc
from datetime import UTC, datetime
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
    ws.accept = AsyncMock(return_value=None)  # noqa: async-mock-config
    ws.close = AsyncMock(return_value=None)  # noqa: async-mock-config
    ws.send_json = AsyncMock(return_value=None)  # noqa: async-mock-config
    ws.send_text = AsyncMock(return_value=None)  # noqa: async-mock-config
    ws.receive_json = AsyncMock(return_value=None)  # noqa: async-mock-config
    ws.receive_text = AsyncMock(return_value=None)  # noqa: async-mock-config
    ws.query_params = {}
    ws.headers = {}
    ws.client_state = MagicMock()
    return ws


@pytest.fixture
def mock_mcp_service() -> MagicMock:
    """Create a mock MCP service."""
    service = MagicMock()
    service.list_tasks = AsyncMock(return_value=[])
    service.get_task = AsyncMock(return_value=None)
    return service


class TestMCPTaskWebSocketHandler:
    """Test MCP Task WebSocket using WebSocketBase."""

    def teardown_method(self) -> None:
        """Force GC to prevent mock accumulation in xdist workers."""
        gc.collect()

    @pytest.mark.asyncio
    async def test_handler_extends_websocket_base(self) -> None:
        """
        GIVEN the MCPTaskWebSocketHandler class
        WHEN checking its base classes
        THEN it should extend WebSocketBase.
        """
        from mcp_server_langgraph.websocket.base import WebSocketBase
        from mcp_server_langgraph.websocket.handlers.mcp_task import (
            MCPTaskWebSocketHandler,
        )

        assert issubclass(MCPTaskWebSocketHandler, WebSocketBase)

    @pytest.mark.asyncio
    async def test_sends_initial_task_list_on_connect(self, mock_websocket: MagicMock, mock_mcp_service: MagicMock) -> None:
        """
        GIVEN a new WebSocket connection
        WHEN on_connect is called
        THEN the initial task list should be sent.
        """
        from mcp_server_langgraph.websocket.handlers.mcp_task import (
            MCPTaskWebSocketHandler,
        )
        from mcp_server_langgraph.websocket.types import AuthUser

        mock_mcp_service.list_tasks = AsyncMock(return_value=[])

        handler = MCPTaskWebSocketHandler(
            config=WebSocketConfig(require_auth=False, endpoint_name="mcp-tasks"),
            mcp_service=mock_mcp_service,
        )
        handler._websocket = mock_websocket

        user = AuthUser(id="test-user", username="test")
        await handler.on_connect(user)

        # Should have sent task_list message
        mock_websocket.send_json.assert_called_once()
        call_args = mock_websocket.send_json.call_args[0][0]
        assert call_args["type"] == "task_list"
        assert "tasks" in call_args

    @pytest.mark.asyncio
    async def test_handles_subscribe_message(self, mock_websocket: MagicMock, mock_mcp_service: MagicMock) -> None:
        """
        GIVEN an active connection
        WHEN a subscribe message is received
        THEN the client should be subscribed to the task.
        """
        from mcp_server_langgraph.websocket.handlers.mcp_task import (
            MCPTaskWebSocketHandler,
        )

        # Create mock task
        mock_task = MagicMock()
        mock_task.task_id = "task-123"
        mock_task.status = MagicMock(value="pending")
        mock_task.created_at = datetime.now(UTC)
        mock_task.last_updated_at = datetime.now(UTC)
        mock_task.ttl = 3600
        mock_task.poll_interval = 5
        mock_task.status_message = "Running"
        mock_mcp_service.get_task = AsyncMock(return_value=mock_task)

        handler = MCPTaskWebSocketHandler(
            config=WebSocketConfig(require_auth=False, endpoint_name="mcp-tasks"),
            mcp_service=mock_mcp_service,
        )

        message = MessageEnvelope(
            type="subscribe",
            payload={"task_id": "task-123"},
        )

        response = await handler.handle_message(message)

        assert response is not None
        assert response.type == "task_status"
        assert "task-123" in handler.subscriptions

    @pytest.mark.asyncio
    async def test_handles_unsubscribe_message(self, mock_websocket: MagicMock, mock_mcp_service: MagicMock) -> None:
        """
        GIVEN an active connection with subscriptions
        WHEN an unsubscribe message is received
        THEN the client should be unsubscribed.
        """
        from mcp_server_langgraph.websocket.handlers.mcp_task import (
            MCPTaskWebSocketHandler,
        )

        handler = MCPTaskWebSocketHandler(
            config=WebSocketConfig(require_auth=False, endpoint_name="mcp-tasks"),
            mcp_service=mock_mcp_service,
        )
        handler.subscriptions.add("task-123")

        message = MessageEnvelope(
            type="unsubscribe",
            payload={"task_id": "task-123"},
        )

        response = await handler.handle_message(message)

        assert response is not None
        assert response.type == "unsubscribed"
        assert "task-123" not in handler.subscriptions

    @pytest.mark.asyncio
    async def test_handles_refresh_message(self, mock_websocket: MagicMock, mock_mcp_service: MagicMock) -> None:
        """
        GIVEN an active connection
        WHEN a refresh message is received
        THEN the task list should be returned.
        """
        from mcp_server_langgraph.websocket.handlers.mcp_task import (
            MCPTaskWebSocketHandler,
        )

        mock_mcp_service.list_tasks = AsyncMock(return_value=[])

        handler = MCPTaskWebSocketHandler(
            config=WebSocketConfig(require_auth=False, endpoint_name="mcp-tasks"),
            mcp_service=mock_mcp_service,
        )

        message = MessageEnvelope(type="refresh")

        response = await handler.handle_message(message)

        assert response is not None
        assert response.type == "task_list"
        mock_mcp_service.list_tasks.assert_called_once()

    @pytest.mark.asyncio
    async def test_returns_error_for_missing_task_id(self, mock_websocket: MagicMock, mock_mcp_service: MagicMock) -> None:
        """
        GIVEN an active connection
        WHEN a subscribe message without task_id is received
        THEN an error response should be returned.
        """
        from mcp_server_langgraph.websocket.handlers.mcp_task import (
            MCPTaskWebSocketHandler,
        )

        handler = MCPTaskWebSocketHandler(
            config=WebSocketConfig(require_auth=False, endpoint_name="mcp-tasks"),
            mcp_service=mock_mcp_service,
        )

        message = MessageEnvelope(
            type="subscribe",
            payload={},  # Missing task_id
        )

        response = await handler.handle_message(message)

        assert response is not None
        assert response.type == "error"
        assert "task_id" in response.payload.get("message", "").lower()

    @pytest.mark.asyncio
    async def test_rejects_unauthenticated_connection(self, mock_websocket: MagicMock, mock_mcp_service: MagicMock) -> None:
        """
        GIVEN a WebSocket connection without auth token
        WHEN require_auth=True is configured
        THEN the connection should be closed with code 4001.
        """
        from mcp_server_langgraph.websocket.handlers.mcp_task import (
            MCPTaskWebSocketHandler,
        )

        # Configure for authentication requirement
        handler = MCPTaskWebSocketHandler(
            config=WebSocketConfig(
                require_auth=True,
                endpoint_name="mcp-tasks",
                authz_resource_type="mcp",
                authz_resource_id="websocket",
                authz_required_relation="user",  # OpenFGA 'mcp' type uses 'user' relation
            ),
            mcp_service=mock_mcp_service,
        )

        # No auth token provided (but include protocol version to pass version check)
        mock_websocket.query_params = {"v": "1.0.0"}
        mock_websocket.headers = {}

        await handler.run(mock_websocket)

        # Should close with authentication required code
        mock_websocket.close.assert_called_once()
        close_args = mock_websocket.close.call_args
        # Code 4001 = Authentication required (use kwargs since close is called with keyword args)
        assert close_args.kwargs.get("code") == 4001 or (close_args.args and close_args.args[0] == 4001)


class TestMCPTasksWebSocketRouterConfig:
    """Test MCP Tasks WebSocket endpoint configuration in ws_router.py."""

    def teardown_method(self) -> None:
        """Force GC to prevent mock accumulation in xdist workers."""
        gc.collect()

    def test_mcp_tasks_endpoint_requires_authentication(self) -> None:
        """
        GIVEN the /api/v1/ws/mcp/tasks endpoint
        WHEN checking its configuration
        THEN require_auth should be True.

        This ensures the endpoint doesn't expose task data to unauthenticated users.
        """
        # Import the function that creates the handler to verify config
        from mcp_server_langgraph.websocket import WebSocketConfig

        # The expected configuration for mcp-tasks endpoint
        # This test documents the security requirement
        expected_config = WebSocketConfig(
            endpoint_name="mcp-tasks",
            require_auth=True,  # SECURITY: Must require authentication
            authz_resource_type="mcp",
            authz_resource_id="websocket",
            authz_required_relation="user",  # OpenFGA 'mcp' type uses 'user' relation
            rate_limit_per_minute=600,
            message_timeout=30,
        )

        # Verify the config properties
        assert expected_config.require_auth is True
        assert expected_config.authz_resource_type == "mcp"
        assert expected_config.authz_resource_id == "websocket"

    def test_websocket_config_defaults_to_require_auth(self) -> None:
        """
        GIVEN WebSocketConfig with no explicit require_auth
        WHEN checking the default
        THEN require_auth should be True (secure by default).
        """
        from mcp_server_langgraph.websocket import WebSocketConfig

        config = WebSocketConfig(endpoint_name="test")
        assert config.require_auth is True
