"""
Connections Realtime WebSocket Handler Tests.

TDD tests for the Connections Realtime WebSocket using the standardized WebSocketBase.
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
def mock_connection_service() -> MagicMock:
    """Create a mock connection service."""
    service = MagicMock()
    service.list_connections = AsyncMock(return_value=[])
    service.get_connection = AsyncMock(return_value=None)
    service.get_connection_health = AsyncMock(return_value={"status": "healthy"})
    return service


@pytest.mark.xdist_group(name="connections_realtime_ws")
class TestConnectionsRealtimeHandler:
    """Test Connections Realtime WebSocket using WebSocketBase."""

    def teardown_method(self) -> None:
        """Force GC to prevent mock accumulation in xdist workers."""
        gc.collect()

    @pytest.mark.asyncio
    async def test_handler_extends_websocket_base(self) -> None:
        """
        GIVEN the ConnectionsRealtimeHandler class
        WHEN checking its base classes
        THEN it should extend WebSocketBase.
        """
        from mcp_server_langgraph.websocket.base import WebSocketBase
        from mcp_server_langgraph.websocket.handlers.connections_realtime import (
            ConnectionsRealtimeHandler,
        )

        assert issubclass(ConnectionsRealtimeHandler, WebSocketBase)

    @pytest.mark.asyncio
    async def test_sends_initial_connection_list_on_connect(
        self, mock_websocket: MagicMock, mock_connection_service: MagicMock
    ) -> None:
        """
        GIVEN a new WebSocket connection
        WHEN on_connect is called
        THEN the initial connection list should be sent.
        """
        from mcp_server_langgraph.websocket.handlers.connections_realtime import (
            ConnectionsRealtimeHandler,
        )
        from mcp_server_langgraph.websocket.types import AuthUser

        mock_connection_service.list_connections = AsyncMock(
            return_value=[
                {"id": "conn-1", "name": "Test Connection", "status": "connected"},
            ]
        )

        handler = ConnectionsRealtimeHandler(
            config=WebSocketConfig(require_auth=True, endpoint_name="connections-realtime"),
            connection_service=mock_connection_service,
        )
        handler._websocket = mock_websocket

        user = AuthUser(id="test-user", username="test")
        await handler.on_connect(user)

        # Should have sent connection_list message
        mock_websocket.send_json.assert_called_once()
        call_args = mock_websocket.send_json.call_args[0][0]
        assert call_args["type"] == "connection_list"
        assert "connections" in call_args

    @pytest.mark.asyncio
    async def test_handles_subscribe_message(self, mock_websocket: MagicMock, mock_connection_service: MagicMock) -> None:
        """
        GIVEN an active connection
        WHEN a subscribe message is received
        THEN the client should be subscribed to connection updates.
        """
        from mcp_server_langgraph.websocket.handlers.connections_realtime import (
            ConnectionsRealtimeHandler,
        )

        mock_connection_service.get_connection = AsyncMock(
            return_value={
                "id": "conn-1",
                "name": "Test Connection",
                "status": "connected",
            }
        )

        handler = ConnectionsRealtimeHandler(
            config=WebSocketConfig(require_auth=True, endpoint_name="connections-realtime"),
            connection_service=mock_connection_service,
        )

        message = MessageEnvelope(
            type="subscribe",
            payload={"connection_id": "conn-1"},
        )

        response = await handler.handle_message(message)

        assert response is not None
        assert response.type == "connection_status"
        assert "conn-1" in handler.subscriptions

    @pytest.mark.asyncio
    async def test_handles_subscribe_all_message(self, mock_websocket: MagicMock, mock_connection_service: MagicMock) -> None:
        """
        GIVEN an active connection
        WHEN a subscribe_all message is received
        THEN the client should be subscribed to all connection updates.
        """
        from mcp_server_langgraph.websocket.handlers.connections_realtime import (
            ConnectionsRealtimeHandler,
        )

        handler = ConnectionsRealtimeHandler(
            config=WebSocketConfig(require_auth=True, endpoint_name="connections-realtime"),
            connection_service=mock_connection_service,
        )

        message = MessageEnvelope(type="subscribe_all")

        response = await handler.handle_message(message)

        assert response is not None
        assert response.type == "subscribed_all"
        assert handler.subscribe_all is True

    @pytest.mark.asyncio
    async def test_handles_request_health_check(self, mock_websocket: MagicMock, mock_connection_service: MagicMock) -> None:
        """
        GIVEN an active connection
        WHEN a request_health_check message is received
        THEN the health check result should be returned.
        """
        from mcp_server_langgraph.websocket.handlers.connections_realtime import (
            ConnectionsRealtimeHandler,
        )

        mock_connection_service.get_connection_health = AsyncMock(
            return_value={
                "connection_id": "conn-1",
                "status": "healthy",
                "latency_ms": 42,
                "last_check": datetime.now(UTC).isoformat(),
            }
        )

        handler = ConnectionsRealtimeHandler(
            config=WebSocketConfig(require_auth=True, endpoint_name="connections-realtime"),
            connection_service=mock_connection_service,
        )

        message = MessageEnvelope(
            type="request_health_check",
            payload={"connection_id": "conn-1"},
        )

        response = await handler.handle_message(message)

        assert response is not None
        assert response.type == "health_check_result"
        mock_connection_service.get_connection_health.assert_called_once_with("conn-1")

    @pytest.mark.asyncio
    async def test_handles_unsubscribe_message(self, mock_websocket: MagicMock, mock_connection_service: MagicMock) -> None:
        """
        GIVEN an active connection with subscriptions
        WHEN an unsubscribe message is received
        THEN the client should be unsubscribed.
        """
        from mcp_server_langgraph.websocket.handlers.connections_realtime import (
            ConnectionsRealtimeHandler,
        )

        handler = ConnectionsRealtimeHandler(
            config=WebSocketConfig(require_auth=True, endpoint_name="connections-realtime"),
            connection_service=mock_connection_service,
        )
        handler.subscriptions.add("conn-1")

        message = MessageEnvelope(
            type="unsubscribe",
            payload={"connection_id": "conn-1"},
        )

        response = await handler.handle_message(message)

        assert response is not None
        assert response.type == "unsubscribed"
        assert "conn-1" not in handler.subscriptions
