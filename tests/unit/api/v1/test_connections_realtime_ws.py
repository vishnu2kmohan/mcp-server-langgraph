"""
Unit tests for Connections Realtime WebSocket endpoint.

Tests the connections_realtime_ws.py endpoint which provides
real-time connection status updates replacing polling.

TDD: RED phase - tests written before implementation.
"""

import gc

import pytest

pytestmark = [
    pytest.mark.unit,
    pytest.mark.websocket,
    pytest.mark.api,
    pytest.mark.xdist_group(name="connections_realtime_ws"),
]


@pytest.mark.xdist_group(name="connections_realtime_ws")
class TestConnectionsRealtimeWebSocketHandler:
    """Tests for ConnectionsRealtimeWebSocketHandler class."""

    def teardown_method(self) -> None:
        """Force GC to prevent mock accumulation in xdist workers."""
        gc.collect()

    def test_handler_class_exists_in_module(self) -> None:
        """GIVEN the module WHEN importing THEN handler class exists."""
        from mcp_server_langgraph.api.v1.connections_realtime_ws import (
            ConnectionsRealtimeWebSocketHandler,
        )

        assert ConnectionsRealtimeWebSocketHandler is not None

    def test_handler_extends_websocket_base(self) -> None:
        """GIVEN handler WHEN checking inheritance THEN extends WebSocketBase."""
        from mcp_server_langgraph.api.v1.connections_realtime_ws import (
            ConnectionsRealtimeWebSocketHandler,
        )
        from mcp_server_langgraph.websocket.base import WebSocketBase

        assert issubclass(ConnectionsRealtimeWebSocketHandler, WebSocketBase)

    def test_handler_config_has_correct_endpoint_name(self) -> None:
        """GIVEN handler WHEN checking config THEN endpoint name is correct."""
        from mcp_server_langgraph.api.v1.connections_realtime_ws import (
            ConnectionsRealtimeWebSocketHandler,
        )

        handler = ConnectionsRealtimeWebSocketHandler()
        assert handler.config.endpoint_name == "connections-realtime"

    def test_handler_requires_auth(self) -> None:
        """GIVEN handler WHEN checking config THEN auth is required."""
        from mcp_server_langgraph.api.v1.connections_realtime_ws import (
            ConnectionsRealtimeWebSocketHandler,
        )

        handler = ConnectionsRealtimeWebSocketHandler()
        assert handler.config.require_auth is True


@pytest.mark.xdist_group(name="connections_realtime_ws")
class TestConnectionsRealtimeMessageHandling:
    """Tests for message handling in ConnectionsRealtimeWebSocketHandler."""

    def teardown_method(self) -> None:
        """Force GC to prevent mock accumulation in xdist workers."""
        gc.collect()

    @pytest.mark.asyncio
    async def test_subscribe_message_adds_subscription(self) -> None:
        """GIVEN subscribe message WHEN handling THEN connection is subscribed."""
        from mcp_server_langgraph.api.v1.connections_realtime_ws import (
            ConnectionsRealtimeWebSocketHandler,
        )
        from mcp_server_langgraph.websocket.types import MessageEnvelope

        handler = ConnectionsRealtimeWebSocketHandler()

        # Create subscribe message
        message = MessageEnvelope(
            type="subscribe",
            payload={"connection_id": "conn_123"},
        )

        response = await handler.handle_message(message)

        # Should return connection status
        assert response is not None
        assert response.type == "connection_status"

    @pytest.mark.asyncio
    async def test_subscribe_all_message_subscribes_all(self) -> None:
        """GIVEN subscribe_all message WHEN handling THEN all connections subscribed."""
        from mcp_server_langgraph.api.v1.connections_realtime_ws import (
            ConnectionsRealtimeWebSocketHandler,
        )
        from mcp_server_langgraph.websocket.types import MessageEnvelope

        handler = ConnectionsRealtimeWebSocketHandler()

        message = MessageEnvelope(type="subscribe_all")

        response = await handler.handle_message(message)

        assert response is not None
        assert response.type == "subscribed_all"
        assert response.payload["subscribed"] is True

    @pytest.mark.asyncio
    async def test_unsubscribe_message_removes_subscription(self) -> None:
        """GIVEN unsubscribe message WHEN handling THEN connection is unsubscribed."""
        from mcp_server_langgraph.api.v1.connections_realtime_ws import (
            ConnectionsRealtimeWebSocketHandler,
        )
        from mcp_server_langgraph.websocket.types import MessageEnvelope

        handler = ConnectionsRealtimeWebSocketHandler()

        message = MessageEnvelope(
            type="unsubscribe",
            payload={"connection_id": "conn_123"},
        )

        response = await handler.handle_message(message)

        assert response is not None
        assert response.type == "unsubscribed"

    @pytest.mark.asyncio
    async def test_refresh_message_returns_connection_list(self) -> None:
        """GIVEN refresh message WHEN handling THEN returns connection list."""
        from mcp_server_langgraph.api.v1.connections_realtime_ws import (
            ConnectionsRealtimeWebSocketHandler,
        )
        from mcp_server_langgraph.websocket.types import MessageEnvelope

        handler = ConnectionsRealtimeWebSocketHandler()

        message = MessageEnvelope(type="refresh")

        response = await handler.handle_message(message)

        assert response is not None
        assert response.type == "connection_list"
        assert "connections" in response.payload

    @pytest.mark.asyncio
    async def test_request_health_check_triggers_check(self) -> None:
        """GIVEN health check request WHEN handling THEN triggers health check."""
        from mcp_server_langgraph.api.v1.connections_realtime_ws import (
            ConnectionsRealtimeWebSocketHandler,
        )
        from mcp_server_langgraph.websocket.types import MessageEnvelope

        handler = ConnectionsRealtimeWebSocketHandler()

        message = MessageEnvelope(
            type="request_health_check",
            payload={"connection_id": "conn_123"},
        )

        response = await handler.handle_message(message)

        assert response is not None
        assert response.type == "health_check_result"
        assert "connection_id" in response.payload


@pytest.mark.xdist_group(name="connections_realtime_ws")
class TestConnectionsRealtimeRouter:
    """Tests for the router endpoint."""

    def teardown_method(self) -> None:
        """Force GC to prevent mock accumulation in xdist workers."""
        gc.collect()

    def test_router_object_exists_in_module(self) -> None:
        """GIVEN the module WHEN importing THEN router exists."""
        from mcp_server_langgraph.api.v1.connections_realtime_ws import router

        assert router is not None

    def test_router_has_websocket_route(self) -> None:
        """GIVEN router WHEN checking routes THEN has websocket route."""
        from mcp_server_langgraph.api.v1.connections_realtime_ws import router

        # Check that router has routes
        routes = router.routes
        assert len(routes) > 0

        # Check for websocket route
        websocket_routes = [r for r in routes if hasattr(r, "path")]
        assert len(websocket_routes) > 0


@pytest.mark.xdist_group(name="connections_realtime_ws")
class TestConnectionsRealtimeServiceIntegration:
    """Tests for ConnectionsServiceAdapter integration."""

    def teardown_method(self) -> None:
        """Force GC to prevent mock accumulation in xdist workers."""
        gc.collect()

    @pytest.mark.asyncio
    async def test_get_connection_status_uses_service_adapter(self) -> None:
        """_get_connection_status delegates to ConnectionsServiceAdapter."""
        from unittest.mock import AsyncMock

        from mcp_server_langgraph.api.v1.connections_realtime_ws import (
            ConnectionsRealtimeWebSocketHandler,
        )

        mock_service = AsyncMock(return_value=None)  # noqa: async-mock-config
        mock_service.get_connection.return_value = {
            "id": "conn-123",
            "name": "Test Connection",
            "status": "connected",
            "server_type": "mcp",
        }

        handler = ConnectionsRealtimeWebSocketHandler()
        handler._connections_service = mock_service

        result = await handler._get_connection_status("conn-123")

        assert result["id"] == "conn-123"
        assert result["name"] == "Test Connection"
        assert result["status"] == "connected"
        mock_service.get_connection.assert_called_once_with("conn-123")

    @pytest.mark.asyncio
    async def test_get_connection_status_fallback_when_not_found(self) -> None:
        """_get_connection_status returns fallback when connection not found."""
        from unittest.mock import AsyncMock

        from mcp_server_langgraph.api.v1.connections_realtime_ws import (
            ConnectionsRealtimeWebSocketHandler,
        )

        mock_service = AsyncMock(return_value=None)  # noqa: async-mock-config
        mock_service.get_connection.return_value = None

        handler = ConnectionsRealtimeWebSocketHandler()
        handler._connections_service = mock_service

        result = await handler._get_connection_status("nonexistent")

        # Should return a sensible fallback
        assert result["id"] == "nonexistent"
        assert "status" in result

    @pytest.mark.asyncio
    async def test_get_all_connections_delegates_to_service(self) -> None:
        """_get_all_connections delegates to ConnectionsServiceAdapter."""
        from unittest.mock import AsyncMock

        from mcp_server_langgraph.api.v1.connections_realtime_ws import (
            ConnectionsRealtimeWebSocketHandler,
        )

        mock_connections = [
            {"id": "conn-1", "name": "Connection 1", "status": "connected"},
            {"id": "conn-2", "name": "Connection 2", "status": "disconnected"},
        ]
        mock_service = AsyncMock(return_value=None)  # noqa: async-mock-config
        mock_service.list_connections.return_value = mock_connections

        handler = ConnectionsRealtimeWebSocketHandler()
        handler._connections_service = mock_service

        result = await handler._get_all_connections()

        assert len(result) == 2
        assert result[0]["id"] == "conn-1"
        assert result[1]["id"] == "conn-2"
        mock_service.list_connections.assert_called_once()

    @pytest.mark.asyncio
    async def test_perform_health_check_uses_service(self) -> None:
        """_perform_health_check delegates to ConnectionsServiceAdapter."""
        from unittest.mock import AsyncMock

        from mcp_server_langgraph.api.v1.connections_realtime_ws import (
            ConnectionsRealtimeWebSocketHandler,
        )

        mock_service = AsyncMock(return_value=None)  # noqa: async-mock-config
        mock_service.get_connection_health.return_value = {
            "connection_id": "conn-123",
            "healthy": True,
            "status": "connected",
        }

        handler = ConnectionsRealtimeWebSocketHandler()
        handler._connections_service = mock_service

        result = await handler._perform_health_check("conn-123")

        assert result["connection_id"] == "conn-123"
        assert result["healthy"] is True
        mock_service.get_connection_health.assert_called_once_with("conn-123")

    @pytest.mark.asyncio
    async def test_get_all_connections_graceful_on_service_error(self) -> None:
        """_get_all_connections returns empty list on service error."""
        from unittest.mock import AsyncMock

        from mcp_server_langgraph.api.v1.connections_realtime_ws import (
            ConnectionsRealtimeWebSocketHandler,
        )

        mock_service = AsyncMock(return_value=None)  # noqa: async-mock-config
        mock_service.list_connections.side_effect = Exception("Service unavailable")

        handler = ConnectionsRealtimeWebSocketHandler()
        handler._connections_service = mock_service

        result = await handler._get_all_connections()

        # Should gracefully return empty list
        assert result == []
