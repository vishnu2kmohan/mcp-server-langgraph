"""
Unit tests for Connections Realtime WebSocket Handler.

Tests the ConnectionsRealtimeHandler class for real-time connection status updates.
"""

from __future__ import annotations

import gc
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

pytestmark = [
    pytest.mark.unit,
    pytest.mark.websocket,
    pytest.mark.xdist_group(name="websocket_connections_realtime_handler"),
]

RATE_LIMITER_PATCH = "mcp_server_langgraph.websocket.rate_limiter.get_websocket_rate_limiter"


class TestConnectionsRealtimeHandlerInit:
    """Tests for ConnectionsRealtimeHandler initialization."""

    def teardown_method(self) -> None:
        """Force GC to prevent mock accumulation in xdist workers."""
        gc.collect()

    def test_init_stores_connection_service(self) -> None:
        """GIVEN connection_service WHEN creating handler THEN stores service."""
        from mcp_server_langgraph.websocket.handlers.connections_realtime import (
            ConnectionsRealtimeHandler,
        )
        from mcp_server_langgraph.websocket.types import WebSocketConfig

        config = WebSocketConfig(endpoint_name="connections-realtime")
        mock_service = MagicMock()

        with patch(RATE_LIMITER_PATCH, side_effect=lambda *a, **kw: MagicMock()):
            handler = ConnectionsRealtimeHandler(config=config, connection_service=mock_service)

        assert handler._connection_service is mock_service
        assert handler.subscriptions == set()
        assert handler.subscribe_all is False

    def test_init_with_metrics(self) -> None:
        """GIVEN metrics WHEN creating handler THEN stores metrics."""
        from mcp_server_langgraph.websocket.handlers.connections_realtime import (
            ConnectionsRealtimeHandler,
        )
        from mcp_server_langgraph.websocket.types import WebSocketConfig

        config = WebSocketConfig(endpoint_name="connections-realtime")
        mock_service = MagicMock()
        mock_metrics = MagicMock()

        with patch(RATE_LIMITER_PATCH, side_effect=lambda *a, **kw: MagicMock()):
            handler = ConnectionsRealtimeHandler(config=config, connection_service=mock_service, metrics=mock_metrics)

        assert handler._metrics is mock_metrics


class TestConnectionsRealtimeHandlerLifecycle:
    """Tests for ConnectionsRealtimeHandler lifecycle hooks."""

    def teardown_method(self) -> None:
        """Force GC to prevent mock accumulation in xdist workers."""
        gc.collect()

    @pytest.mark.asyncio
    async def test_on_connect_sends_connection_list(self) -> None:
        """GIVEN user WHEN on_connect called THEN sends connection list."""
        from mcp_server_langgraph.websocket.handlers.connections_realtime import (
            ConnectionsRealtimeHandler,
        )
        from mcp_server_langgraph.websocket.types import AuthUser, WebSocketConfig

        config = WebSocketConfig(endpoint_name="connections-realtime")
        mock_service = AsyncMock(return_value=None)  # noqa: async-mock-config
        mock_service.list_connections.return_value = [
            {"id": "conn-1", "name": "Connection 1", "status": "healthy"},
            {"id": "conn-2", "name": "Connection 2", "status": "unhealthy"},
        ]

        with patch(RATE_LIMITER_PATCH, side_effect=lambda *a, **kw: MagicMock()):
            handler = ConnectionsRealtimeHandler(config=config, connection_service=mock_service)

        mock_ws = AsyncMock(return_value=None)  # noqa: async-mock-config
        handler._websocket = mock_ws
        user = AuthUser(id="user-123", username="testuser")

        await handler.on_connect(user)

        mock_service.list_connections.assert_called_once()
        mock_ws.send_json.assert_called_once()
        sent_data = mock_ws.send_json.call_args[0][0]
        assert sent_data["type"] == "connection_list"
        assert len(sent_data["connections"]) == 2

    @pytest.mark.asyncio
    async def test_on_disconnect_clears_subscriptions(self) -> None:
        """GIVEN subscriptions WHEN on_disconnect called THEN clears."""
        from mcp_server_langgraph.websocket.handlers.connections_realtime import (
            ConnectionsRealtimeHandler,
        )
        from mcp_server_langgraph.websocket.types import WebSocketConfig

        config = WebSocketConfig(endpoint_name="connections-realtime")
        mock_service = AsyncMock(return_value=None)  # noqa: async-mock-config

        with patch(RATE_LIMITER_PATCH, side_effect=lambda *a, **kw: MagicMock()):
            handler = ConnectionsRealtimeHandler(config=config, connection_service=mock_service)

        handler.subscriptions = {"conn-1", "conn-2"}
        handler.subscribe_all = True

        await handler.on_disconnect()

        assert handler.subscriptions == set()
        assert handler.subscribe_all is False


class TestConnectionsRealtimeHandlerMessages:
    """Tests for ConnectionsRealtimeHandler message handling."""

    def teardown_method(self) -> None:
        """Force GC to prevent mock accumulation in xdist workers."""
        gc.collect()

    @pytest.mark.asyncio
    async def test_handle_subscribe(self) -> None:
        """GIVEN subscribe message WHEN handle_message called THEN subscribes."""
        from mcp_server_langgraph.websocket.handlers.connections_realtime import (
            ConnectionsRealtimeHandler,
        )
        from mcp_server_langgraph.websocket.types import MessageEnvelope, WebSocketConfig

        config = WebSocketConfig(endpoint_name="connections-realtime")
        mock_service = AsyncMock(return_value=None)  # noqa: async-mock-config
        mock_service.get_connection.return_value = {
            "id": "conn-1",
            "name": "Test Connection",
            "status": "healthy",
        }

        with patch(RATE_LIMITER_PATCH, side_effect=lambda *a, **kw: MagicMock()):
            handler = ConnectionsRealtimeHandler(config=config, connection_service=mock_service)

        message = MessageEnvelope(type="subscribe", id="msg-1", payload={"connection_id": "conn-1"})
        response = await handler.handle_message(message)

        assert response is not None
        assert response.type == "connection_status"
        assert response.id == "msg-1"
        assert "conn-1" in handler.subscriptions
        mock_service.get_connection.assert_called_once_with("conn-1")

    @pytest.mark.asyncio
    async def test_handle_subscribe_missing_connection_id(self) -> None:
        """GIVEN subscribe without connection_id WHEN handle_message THEN error."""
        from mcp_server_langgraph.websocket.handlers.connections_realtime import (
            ConnectionsRealtimeHandler,
        )
        from mcp_server_langgraph.websocket.types import MessageEnvelope, WebSocketConfig

        config = WebSocketConfig(endpoint_name="connections-realtime")
        mock_service = AsyncMock(return_value=None)  # noqa: async-mock-config

        with patch(RATE_LIMITER_PATCH, side_effect=lambda *a, **kw: MagicMock()):
            handler = ConnectionsRealtimeHandler(config=config, connection_service=mock_service)

        message = MessageEnvelope(type="subscribe", id="msg-1", payload={})
        response = await handler.handle_message(message)

        assert response is not None
        assert response.type == "error"
        assert response.payload["code"] == "missing_connection_id"

    @pytest.mark.asyncio
    async def test_handle_subscribe_connection_not_found(self) -> None:
        """GIVEN non-existent connection WHEN subscribe THEN error."""
        from mcp_server_langgraph.websocket.handlers.connections_realtime import (
            ConnectionsRealtimeHandler,
        )
        from mcp_server_langgraph.websocket.types import MessageEnvelope, WebSocketConfig

        config = WebSocketConfig(endpoint_name="connections-realtime")
        mock_service = AsyncMock(return_value=None)  # noqa: async-mock-config
        mock_service.get_connection.return_value = None

        with patch(RATE_LIMITER_PATCH, side_effect=lambda *a, **kw: MagicMock()):
            handler = ConnectionsRealtimeHandler(config=config, connection_service=mock_service)

        message = MessageEnvelope(type="subscribe", id="msg-1", payload={"connection_id": "nonexistent"})
        response = await handler.handle_message(message)

        assert response is not None
        assert response.type == "error"
        assert response.payload["code"] == "connection_not_found"

    @pytest.mark.asyncio
    async def test_handle_subscribe_error(self) -> None:
        """GIVEN service error WHEN subscribe THEN returns error."""
        from mcp_server_langgraph.websocket.handlers.connections_realtime import (
            ConnectionsRealtimeHandler,
        )
        from mcp_server_langgraph.websocket.types import MessageEnvelope, WebSocketConfig

        config = WebSocketConfig(endpoint_name="connections-realtime")
        mock_service = AsyncMock(return_value=None)  # noqa: async-mock-config
        mock_service.get_connection.side_effect = Exception("Database error")

        with patch(RATE_LIMITER_PATCH, side_effect=lambda *a, **kw: MagicMock()):
            handler = ConnectionsRealtimeHandler(config=config, connection_service=mock_service)

        message = MessageEnvelope(type="subscribe", id="msg-1", payload={"connection_id": "conn-1"})
        response = await handler.handle_message(message)

        assert response is not None
        assert response.type == "error"
        assert response.payload["code"] == "subscribe_error"

    @pytest.mark.asyncio
    async def test_handle_subscribe_all(self) -> None:
        """GIVEN subscribe_all message WHEN handle_message THEN subscribes to all."""
        from mcp_server_langgraph.websocket.handlers.connections_realtime import (
            ConnectionsRealtimeHandler,
        )
        from mcp_server_langgraph.websocket.types import MessageEnvelope, WebSocketConfig

        config = WebSocketConfig(endpoint_name="connections-realtime")
        mock_service = AsyncMock(return_value=None)  # noqa: async-mock-config

        with patch(RATE_LIMITER_PATCH, side_effect=lambda *a, **kw: MagicMock()):
            handler = ConnectionsRealtimeHandler(config=config, connection_service=mock_service)

        message = MessageEnvelope(type="subscribe_all", id="msg-1")
        response = await handler.handle_message(message)

        assert response is not None
        assert response.type == "subscribed_all"
        assert handler.subscribe_all is True

    @pytest.mark.asyncio
    async def test_handle_unsubscribe(self) -> None:
        """GIVEN unsubscribe message WHEN handle_message THEN unsubscribes."""
        from mcp_server_langgraph.websocket.handlers.connections_realtime import (
            ConnectionsRealtimeHandler,
        )
        from mcp_server_langgraph.websocket.types import MessageEnvelope, WebSocketConfig

        config = WebSocketConfig(endpoint_name="connections-realtime")
        mock_service = AsyncMock(return_value=None)  # noqa: async-mock-config

        with patch(RATE_LIMITER_PATCH, side_effect=lambda *a, **kw: MagicMock()):
            handler = ConnectionsRealtimeHandler(config=config, connection_service=mock_service)

        handler.subscriptions = {"conn-1", "conn-2"}

        message = MessageEnvelope(type="unsubscribe", id="msg-1", payload={"connection_id": "conn-1"})
        response = await handler.handle_message(message)

        assert response is not None
        assert response.type == "unsubscribed"
        assert "conn-1" not in handler.subscriptions
        assert "conn-2" in handler.subscriptions

    @pytest.mark.asyncio
    async def test_handle_request_health_check(self) -> None:
        """GIVEN health check message WHEN handle_message THEN returns health."""
        from mcp_server_langgraph.websocket.handlers.connections_realtime import (
            ConnectionsRealtimeHandler,
        )
        from mcp_server_langgraph.websocket.types import MessageEnvelope, WebSocketConfig

        config = WebSocketConfig(endpoint_name="connections-realtime")
        mock_service = AsyncMock(return_value=None)  # noqa: async-mock-config
        mock_service.get_connection_health.return_value = {
            "status": "healthy",
            "latency_ms": 50,
            "last_checked": "2024-01-01T00:00:00Z",
        }

        with patch(RATE_LIMITER_PATCH, side_effect=lambda *a, **kw: MagicMock()):
            handler = ConnectionsRealtimeHandler(config=config, connection_service=mock_service)

        message = MessageEnvelope(type="request_health_check", id="msg-1", payload={"connection_id": "conn-1"})
        response = await handler.handle_message(message)

        assert response is not None
        assert response.type == "health_check_result"
        mock_service.get_connection_health.assert_called_once_with("conn-1")

    @pytest.mark.asyncio
    async def test_handle_request_health_check_missing_connection_id(self) -> None:
        """GIVEN health check without connection_id WHEN handle_message THEN error."""
        from mcp_server_langgraph.websocket.handlers.connections_realtime import (
            ConnectionsRealtimeHandler,
        )
        from mcp_server_langgraph.websocket.types import MessageEnvelope, WebSocketConfig

        config = WebSocketConfig(endpoint_name="connections-realtime")
        mock_service = AsyncMock(return_value=None)  # noqa: async-mock-config

        with patch(RATE_LIMITER_PATCH, side_effect=lambda *a, **kw: MagicMock()):
            handler = ConnectionsRealtimeHandler(config=config, connection_service=mock_service)

        message = MessageEnvelope(type="request_health_check", id="msg-1", payload={})
        response = await handler.handle_message(message)

        assert response is not None
        assert response.type == "error"
        assert response.payload["code"] == "missing_connection_id"

    @pytest.mark.asyncio
    async def test_handle_request_health_check_error(self) -> None:
        """GIVEN health check error WHEN handle_message THEN returns error."""
        from mcp_server_langgraph.websocket.handlers.connections_realtime import (
            ConnectionsRealtimeHandler,
        )
        from mcp_server_langgraph.websocket.types import MessageEnvelope, WebSocketConfig

        config = WebSocketConfig(endpoint_name="connections-realtime")
        mock_service = AsyncMock(return_value=None)  # noqa: async-mock-config
        mock_service.get_connection_health.side_effect = Exception("Service unavailable")

        with patch(RATE_LIMITER_PATCH, side_effect=lambda *a, **kw: MagicMock()):
            handler = ConnectionsRealtimeHandler(config=config, connection_service=mock_service)

        message = MessageEnvelope(type="request_health_check", id="msg-1", payload={"connection_id": "conn-1"})
        response = await handler.handle_message(message)

        assert response is not None
        assert response.type == "error"
        assert response.payload["code"] == "health_check_error"

    @pytest.mark.asyncio
    async def test_handle_unknown_message_type(self) -> None:
        """GIVEN unknown message type WHEN handle_message called THEN returns error."""
        from mcp_server_langgraph.websocket.handlers.connections_realtime import (
            ConnectionsRealtimeHandler,
        )
        from mcp_server_langgraph.websocket.types import MessageEnvelope, WebSocketConfig

        config = WebSocketConfig(endpoint_name="connections-realtime")
        mock_service = AsyncMock(return_value=None)  # noqa: async-mock-config

        with patch(RATE_LIMITER_PATCH, side_effect=lambda *a, **kw: MagicMock()):
            handler = ConnectionsRealtimeHandler(config=config, connection_service=mock_service)

        message = MessageEnvelope(type="invalid", id="msg-1")
        response = await handler.handle_message(message)

        assert response is not None
        assert response.type == "error"
        assert response.payload["code"] == "unknown_message_type"


class TestConnectionsRealtimeHandlerPush:
    """Tests for ConnectionsRealtimeHandler push functionality."""

    def teardown_method(self) -> None:
        """Force GC to prevent mock accumulation in xdist workers."""
        gc.collect()

    @pytest.mark.asyncio
    async def test_push_connection_update_when_subscribed(self) -> None:
        """GIVEN subscribed WHEN push_connection_update THEN sends."""
        from mcp_server_langgraph.websocket.handlers.connections_realtime import (
            ConnectionsRealtimeHandler,
        )
        from mcp_server_langgraph.websocket.types import WebSocketConfig

        config = WebSocketConfig(endpoint_name="connections-realtime")
        mock_service = AsyncMock(return_value=None)  # noqa: async-mock-config

        with patch(RATE_LIMITER_PATCH, side_effect=lambda *a, **kw: MagicMock()):
            handler = ConnectionsRealtimeHandler(config=config, connection_service=mock_service)

        mock_ws = AsyncMock(return_value=None)  # noqa: async-mock-config
        handler._websocket = mock_ws
        handler.subscriptions.add("conn-1")

        connection = {"id": "conn-1", "name": "Test", "status": "healthy"}
        await handler.push_connection_update(connection)

        mock_ws.send_json.assert_called_once()

    @pytest.mark.asyncio
    async def test_push_connection_update_when_subscribe_all(self) -> None:
        """GIVEN subscribe_all WHEN push_connection_update THEN sends."""
        from mcp_server_langgraph.websocket.handlers.connections_realtime import (
            ConnectionsRealtimeHandler,
        )
        from mcp_server_langgraph.websocket.types import WebSocketConfig

        config = WebSocketConfig(endpoint_name="connections-realtime")
        mock_service = AsyncMock(return_value=None)  # noqa: async-mock-config

        with patch(RATE_LIMITER_PATCH, side_effect=lambda *a, **kw: MagicMock()):
            handler = ConnectionsRealtimeHandler(config=config, connection_service=mock_service)

        mock_ws = AsyncMock(return_value=None)  # noqa: async-mock-config
        handler._websocket = mock_ws
        handler.subscribe_all = True

        connection = {"id": "conn-1", "name": "Test", "status": "healthy"}
        await handler.push_connection_update(connection)

        mock_ws.send_json.assert_called_once()

    @pytest.mark.asyncio
    async def test_push_connection_update_when_not_subscribed(self) -> None:
        """GIVEN not subscribed WHEN push_connection_update THEN does not send."""
        from mcp_server_langgraph.websocket.handlers.connections_realtime import (
            ConnectionsRealtimeHandler,
        )
        from mcp_server_langgraph.websocket.types import WebSocketConfig

        config = WebSocketConfig(endpoint_name="connections-realtime")
        mock_service = AsyncMock(return_value=None)  # noqa: async-mock-config

        with patch(RATE_LIMITER_PATCH, side_effect=lambda *a, **kw: MagicMock()):
            handler = ConnectionsRealtimeHandler(config=config, connection_service=mock_service)

        mock_ws = AsyncMock(return_value=None)  # noqa: async-mock-config
        handler._websocket = mock_ws
        # Not subscribed to this connection
        handler.subscriptions = {"conn-2"}
        handler.subscribe_all = False

        connection = {"id": "conn-1", "name": "Test", "status": "healthy"}
        await handler.push_connection_update(connection)

        mock_ws.send_json.assert_not_called()

    @pytest.mark.asyncio
    async def test_push_connection_update_no_id(self) -> None:
        """GIVEN connection without id WHEN push_connection_update THEN does not send."""
        from mcp_server_langgraph.websocket.handlers.connections_realtime import (
            ConnectionsRealtimeHandler,
        )
        from mcp_server_langgraph.websocket.types import WebSocketConfig

        config = WebSocketConfig(endpoint_name="connections-realtime")
        mock_service = AsyncMock(return_value=None)  # noqa: async-mock-config

        with patch(RATE_LIMITER_PATCH, side_effect=lambda *a, **kw: MagicMock()):
            handler = ConnectionsRealtimeHandler(config=config, connection_service=mock_service)

        mock_ws = AsyncMock(return_value=None)  # noqa: async-mock-config
        handler._websocket = mock_ws
        handler.subscribe_all = True

        connection = {"name": "Test", "status": "healthy"}  # No id
        await handler.push_connection_update(connection)

        mock_ws.send_json.assert_not_called()


class TestConnectionServiceProtocol:
    """Tests for ConnectionServiceProtocol."""

    def teardown_method(self) -> None:
        """Force GC to prevent mock accumulation in xdist workers."""
        gc.collect()

    def test_protocol_is_runtime_checkable(self) -> None:
        """GIVEN ConnectionServiceProtocol WHEN checking isinstance THEN works."""
        from mcp_server_langgraph.websocket.handlers.connections_realtime import (
            ConnectionServiceProtocol,
        )

        class MockConnectionService:
            async def list_connections(self):
                return []

            async def get_connection(self, connection_id: str):
                return None

            async def get_connection_health(self, connection_id: str):
                return {}

        service = MockConnectionService()
        assert isinstance(service, ConnectionServiceProtocol)
