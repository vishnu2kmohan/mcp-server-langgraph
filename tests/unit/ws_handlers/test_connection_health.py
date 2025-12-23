"""
Connection Health WebSocket Handler Tests.

TDD tests for the Connection Health WebSocket using the standardized WebSocketBase.
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
    ws.accept = AsyncMock()
    ws.close = AsyncMock()
    ws.send_json = AsyncMock()
    ws.send_text = AsyncMock()
    ws.receive_json = AsyncMock()
    ws.receive_text = AsyncMock()
    ws.query_params = {}
    ws.headers = {}
    ws.client_state = MagicMock()
    return ws


@pytest.fixture
def mock_connection_repository() -> MagicMock:
    """Create a mock connection repository."""
    repo = MagicMock()
    repo.list = AsyncMock(
        return_value=(
            [
                MagicMock(
                    id="conn-1",
                    name="Connection 1",
                    url="http://localhost:8080",
                    status="connected",
                    auth_type="none",
                    server_name="MCP Server",
                    server_version="1.0.0",
                    tool_count=5,
                    resource_count=3,
                    prompt_count=2,
                ),
                MagicMock(
                    id="conn-2",
                    name="Connection 2",
                    url="http://localhost:8081",
                    status="disconnected",
                    auth_type="bearer",
                    server_name=None,
                    server_version=None,
                    tool_count=0,
                    resource_count=0,
                    prompt_count=0,
                ),
            ],
            2,
        )
    )
    repo.get = AsyncMock(
        return_value=MagicMock(
            id="conn-1",
            name="Connection 1",
            status="connected",
        )
    )
    return repo


@pytest.mark.xdist_group(name="connection_health_ws")
class TestConnectionHealthHandler:
    """Test Connection Health WebSocket using WebSocketBase."""

    def teardown_method(self) -> None:
        """Force GC to prevent mock accumulation in xdist workers."""
        gc.collect()

    @pytest.mark.asyncio
    async def test_handler_extends_websocket_base(self) -> None:
        """
        GIVEN the ConnectionHealthHandler class
        WHEN checking its base classes
        THEN it should extend WebSocketBase.
        """
        from mcp_server_langgraph.websocket.base import WebSocketBase
        from mcp_server_langgraph.websocket.handlers.connection_health import (
            ConnectionHealthHandler,
        )

        assert issubclass(ConnectionHealthHandler, WebSocketBase)

    @pytest.mark.asyncio
    async def test_handles_refresh_message(self, mock_websocket: MagicMock, mock_connection_repository: MagicMock) -> None:
        """
        GIVEN an active connection
        WHEN a refresh message is received
        THEN all connection statuses should be returned.
        """
        from mcp_server_langgraph.websocket.handlers.connection_health import (
            ConnectionHealthHandler,
        )

        handler = ConnectionHealthHandler(
            config=WebSocketConfig(require_auth=False, endpoint_name="conn-health"),
            connection_repository=mock_connection_repository,
            owner_id="user-123",
        )

        message = MessageEnvelope(
            type="refresh",
            payload={},
        )

        response = await handler.handle_message(message)

        assert response is not None
        assert response.type == "connection_status"
        assert response.payload is not None
        assert "connections" in response.payload
        mock_connection_repository.list.assert_called_once()

    @pytest.mark.asyncio
    async def test_handles_subscribe_message(self, mock_websocket: MagicMock, mock_connection_repository: MagicMock) -> None:
        """
        GIVEN an active connection
        WHEN a subscribe message is received
        THEN subscription should be confirmed.
        """
        from mcp_server_langgraph.websocket.handlers.connection_health import (
            ConnectionHealthHandler,
        )

        handler = ConnectionHealthHandler(
            config=WebSocketConfig(require_auth=False, endpoint_name="conn-health"),
            connection_repository=mock_connection_repository,
            owner_id="user-123",
        )

        message = MessageEnvelope(
            type="subscribe",
            payload={"connection_id": "conn-1"},
        )

        response = await handler.handle_message(message)

        assert response is not None
        assert response.type == "subscribed"
        assert response.payload is not None
        assert response.payload.get("connection_id") == "conn-1"

    @pytest.mark.asyncio
    async def test_handles_unsubscribe_message(self, mock_websocket: MagicMock, mock_connection_repository: MagicMock) -> None:
        """
        GIVEN an active connection with a subscription
        WHEN an unsubscribe message is received
        THEN unsubscription should be confirmed.
        """
        from mcp_server_langgraph.websocket.handlers.connection_health import (
            ConnectionHealthHandler,
        )

        handler = ConnectionHealthHandler(
            config=WebSocketConfig(require_auth=False, endpoint_name="conn-health"),
            connection_repository=mock_connection_repository,
            owner_id="user-123",
        )
        # First subscribe
        handler._subscriptions.add("conn-1")

        message = MessageEnvelope(
            type="unsubscribe",
            payload={"connection_id": "conn-1"},
        )

        response = await handler.handle_message(message)

        assert response is not None
        assert response.type == "unsubscribed"
        assert "conn-1" not in handler._subscriptions

    @pytest.mark.asyncio
    async def test_handles_check_health_message(
        self, mock_websocket: MagicMock, mock_connection_repository: MagicMock
    ) -> None:
        """
        GIVEN an active connection
        WHEN a check_health message is received
        THEN health check should be initiated.
        """
        from mcp_server_langgraph.websocket.handlers.connection_health import (
            ConnectionHealthHandler,
        )

        handler = ConnectionHealthHandler(
            config=WebSocketConfig(require_auth=False, endpoint_name="conn-health"),
            connection_repository=mock_connection_repository,
            owner_id="user-123",
        )

        message = MessageEnvelope(
            type="check_health",
            payload={"connection_id": "conn-1"},
        )

        response = await handler.handle_message(message)

        assert response is not None
        assert response.type == "health_check_started"
        assert response.payload is not None
        assert response.payload.get("connection_id") == "conn-1"

    @pytest.mark.asyncio
    async def test_returns_error_for_unknown_message(
        self, mock_websocket: MagicMock, mock_connection_repository: MagicMock
    ) -> None:
        """
        GIVEN an active connection
        WHEN an unknown message type is received
        THEN an error response should be returned.
        """
        from mcp_server_langgraph.websocket.handlers.connection_health import (
            ConnectionHealthHandler,
        )

        handler = ConnectionHealthHandler(
            config=WebSocketConfig(require_auth=False, endpoint_name="conn-health"),
            connection_repository=mock_connection_repository,
            owner_id="user-123",
        )

        message = MessageEnvelope(
            type="unknown_type",
            payload={},
        )

        response = await handler.handle_message(message)

        assert response is not None
        assert response.type == "error"

    @pytest.mark.asyncio
    async def test_returns_error_for_missing_connection_id(
        self, mock_websocket: MagicMock, mock_connection_repository: MagicMock
    ) -> None:
        """
        GIVEN an active connection
        WHEN a subscribe message without connection_id is received
        THEN an error response should be returned.
        """
        from mcp_server_langgraph.websocket.handlers.connection_health import (
            ConnectionHealthHandler,
        )

        handler = ConnectionHealthHandler(
            config=WebSocketConfig(require_auth=False, endpoint_name="conn-health"),
            connection_repository=mock_connection_repository,
            owner_id="user-123",
        )

        message = MessageEnvelope(
            type="subscribe",
            payload={},  # Missing connection_id
        )

        response = await handler.handle_message(message)

        assert response is not None
        assert response.type == "error"
        assert response.payload is not None
        assert "connection_id" in response.payload.get("message", "").lower()

    @pytest.mark.asyncio
    async def test_push_connection_update(self, mock_websocket: MagicMock, mock_connection_repository: MagicMock) -> None:
        """
        GIVEN an active connection with subscription
        WHEN push_connection_update is called
        THEN update should be sent to client.
        """
        from mcp_server_langgraph.websocket.handlers.connection_health import (
            ConnectionHealthHandler,
        )

        handler = ConnectionHealthHandler(
            config=WebSocketConfig(require_auth=False, endpoint_name="conn-health"),
            connection_repository=mock_connection_repository,
            owner_id="user-123",
        )
        handler._websocket = mock_websocket
        handler._subscriptions.add("conn-1")

        await handler.push_connection_update(
            "conn-1",
            {"id": "conn-1", "status": "connected"},
        )

        mock_websocket.send_json.assert_called_once()
        call_args = mock_websocket.send_json.call_args[0][0]
        assert call_args["type"] == "connection_update"
        assert call_args["payload"]["id"] == "conn-1"
