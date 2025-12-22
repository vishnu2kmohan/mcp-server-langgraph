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

    def test_handler_exists(self) -> None:
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

    def test_router_exists(self) -> None:
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
