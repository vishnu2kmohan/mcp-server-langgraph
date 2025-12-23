"""
Unit tests for Connection Health WebSocket Handler.

Tests the ConnectionHealthHandler class for real-time connection monitoring.
"""

from __future__ import annotations

import gc
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

pytestmark = [
    pytest.mark.unit,
    pytest.mark.websocket,
    pytest.mark.xdist_group(name="websocket_connection_health_handler"),
]

RATE_LIMITER_PATCH = "mcp_server_langgraph.websocket.rate_limiter.get_websocket_rate_limiter"


@pytest.mark.xdist_group(name="websocket_connection_health_init")
class TestConnectionHealthHandlerInit:
    """Tests for ConnectionHealthHandler initialization."""

    def teardown_method(self) -> None:
        """Force GC to prevent mock accumulation in xdist workers."""
        gc.collect()

    def test_init_stores_repository(self) -> None:
        """GIVEN repository WHEN creating handler THEN stores repository."""
        from mcp_server_langgraph.websocket.handlers.connection_health import (
            ConnectionHealthHandler,
        )
        from mcp_server_langgraph.websocket.types import WebSocketConfig

        config = WebSocketConfig(endpoint_name="connection-health")
        mock_repo = MagicMock()

        with patch(RATE_LIMITER_PATCH, return_value=MagicMock()):
            handler = ConnectionHealthHandler(config=config, connection_repository=mock_repo, owner_id="owner-123")

        assert handler._connection_repository is mock_repo
        assert handler._owner_id == "owner-123"
        assert handler._subscriptions == set()


@pytest.mark.xdist_group(name="websocket_connection_health_lifecycle")
class TestConnectionHealthHandlerLifecycle:
    """Tests for ConnectionHealthHandler lifecycle hooks."""

    def teardown_method(self) -> None:
        """Force GC to prevent mock accumulation in xdist workers."""
        gc.collect()

    @pytest.mark.asyncio
    async def test_on_connect_logs(self) -> None:
        """GIVEN user WHEN on_connect called THEN logs connection."""
        from mcp_server_langgraph.websocket.handlers.connection_health import (
            ConnectionHealthHandler,
        )
        from mcp_server_langgraph.websocket.types import AuthUser, WebSocketConfig

        config = WebSocketConfig(endpoint_name="connection-health")
        mock_repo = MagicMock()

        with patch(RATE_LIMITER_PATCH, return_value=MagicMock()):
            handler = ConnectionHealthHandler(config=config, connection_repository=mock_repo, owner_id="owner-123")

        user = AuthUser(id="user-123", username="testuser")

        # Should not raise
        await handler.on_connect(user)

    @pytest.mark.asyncio
    async def test_on_disconnect_clears_subscriptions(self) -> None:
        """GIVEN subscriptions WHEN on_disconnect called THEN clears."""
        from mcp_server_langgraph.websocket.handlers.connection_health import (
            ConnectionHealthHandler,
        )
        from mcp_server_langgraph.websocket.types import WebSocketConfig

        config = WebSocketConfig(endpoint_name="connection-health")
        mock_repo = MagicMock()

        with patch(RATE_LIMITER_PATCH, return_value=MagicMock()):
            handler = ConnectionHealthHandler(config=config, connection_repository=mock_repo, owner_id="owner-123")

        handler._subscriptions = {"conn-1", "conn-2"}

        await handler.on_disconnect()

        assert handler._subscriptions == set()


@pytest.mark.xdist_group(name="websocket_connection_health_messages")
class TestConnectionHealthHandlerMessages:
    """Tests for ConnectionHealthHandler message handling."""

    def teardown_method(self) -> None:
        """Force GC to prevent mock accumulation in xdist workers."""
        gc.collect()

    @pytest.mark.asyncio
    async def test_handle_refresh(self) -> None:
        """GIVEN refresh message WHEN handle_message called THEN returns connections."""
        from mcp_server_langgraph.websocket.handlers.connection_health import (
            ConnectionHealthHandler,
        )
        from mcp_server_langgraph.websocket.types import MessageEnvelope, WebSocketConfig

        config = WebSocketConfig(endpoint_name="connection-health")
        mock_repo = AsyncMock()

        mock_conn = MagicMock()
        mock_conn.id = "conn-1"
        mock_conn.name = "Test Connection"
        mock_conn.url = "http://localhost:8080"
        mock_conn.status = "healthy"
        mock_conn.auth_type = "none"
        mock_repo.list.return_value = ([mock_conn], None)

        with patch(RATE_LIMITER_PATCH, return_value=MagicMock()):
            handler = ConnectionHealthHandler(config=config, connection_repository=mock_repo, owner_id="owner-123")

        message = MessageEnvelope(type="refresh", id="msg-1")
        response = await handler.handle_message(message)

        assert response is not None
        assert response.type == "connection_status"
        assert len(response.payload["connections"]) == 1
        mock_repo.list.assert_called_once()

    @pytest.mark.asyncio
    async def test_handle_refresh_error(self) -> None:
        """GIVEN error WHEN handle_message refresh THEN returns error."""
        from mcp_server_langgraph.websocket.handlers.connection_health import (
            ConnectionHealthHandler,
        )
        from mcp_server_langgraph.websocket.types import MessageEnvelope, WebSocketConfig

        config = WebSocketConfig(endpoint_name="connection-health")
        mock_repo = AsyncMock()
        mock_repo.list.side_effect = Exception("Database error")

        with patch(RATE_LIMITER_PATCH, return_value=MagicMock()):
            handler = ConnectionHealthHandler(config=config, connection_repository=mock_repo, owner_id="owner-123")

        message = MessageEnvelope(type="refresh", id="msg-1")
        response = await handler.handle_message(message)

        assert response is not None
        assert response.type == "error"
        assert response.payload["code"] == "refresh_failed"

    @pytest.mark.asyncio
    async def test_handle_unknown_message_type(self) -> None:
        """GIVEN unknown message type WHEN handle_message called THEN returns error."""
        from mcp_server_langgraph.websocket.handlers.connection_health import (
            ConnectionHealthHandler,
        )
        from mcp_server_langgraph.websocket.types import MessageEnvelope, WebSocketConfig

        config = WebSocketConfig(endpoint_name="connection-health")
        mock_repo = AsyncMock()

        with patch(RATE_LIMITER_PATCH, return_value=MagicMock()):
            handler = ConnectionHealthHandler(config=config, connection_repository=mock_repo, owner_id="owner-123")

        message = MessageEnvelope(type="invalid", id="msg-2")
        response = await handler.handle_message(message)

        assert response is not None
        assert response.type == "error"
        assert response.payload["code"] == "unknown_message_type"
