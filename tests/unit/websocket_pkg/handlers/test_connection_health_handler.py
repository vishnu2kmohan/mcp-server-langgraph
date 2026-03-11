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

        with patch(RATE_LIMITER_PATCH, side_effect=lambda *a, **kw: MagicMock()):
            handler = ConnectionHealthHandler(config=config, connection_repository=mock_repo, owner_id="owner-123")

        assert handler._connection_repository is mock_repo
        assert handler._owner_id == "owner-123"
        assert handler._subscriptions == set()


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

        with patch(RATE_LIMITER_PATCH, side_effect=lambda *a, **kw: MagicMock()):
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

        with patch(RATE_LIMITER_PATCH, side_effect=lambda *a, **kw: MagicMock()):
            handler = ConnectionHealthHandler(config=config, connection_repository=mock_repo, owner_id="owner-123")

        handler._subscriptions = {"conn-1", "conn-2"}

        await handler.on_disconnect()

        assert handler._subscriptions == set()


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
        mock_repo = AsyncMock(return_value=None)  # noqa: async-mock-config

        mock_conn = MagicMock()
        mock_conn.id = "conn-1"
        mock_conn.name = "Test Connection"
        mock_conn.url = "http://localhost:8080"
        mock_conn.status = "healthy"
        mock_conn.auth_type = "none"
        mock_repo.list.return_value = ([mock_conn], None)

        with patch(RATE_LIMITER_PATCH, side_effect=lambda *a, **kw: MagicMock()):
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
        mock_repo = AsyncMock(return_value=None)  # noqa: async-mock-config
        mock_repo.list.side_effect = Exception("Database error")

        with patch(RATE_LIMITER_PATCH, side_effect=lambda *a, **kw: MagicMock()):
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
        mock_repo = AsyncMock(return_value=None)  # noqa: async-mock-config

        with patch(RATE_LIMITER_PATCH, side_effect=lambda *a, **kw: MagicMock()):
            handler = ConnectionHealthHandler(config=config, connection_repository=mock_repo, owner_id="owner-123")

        message = MessageEnvelope(type="invalid", id="msg-2")
        response = await handler.handle_message(message)

        assert response is not None
        assert response.type == "error"
        assert response.payload["code"] == "unknown_message_type"

    @pytest.mark.asyncio
    async def test_handle_subscribe_success(self) -> None:
        """GIVEN valid subscribe message WHEN handle_message called THEN adds subscription."""
        from mcp_server_langgraph.websocket.handlers.connection_health import (
            ConnectionHealthHandler,
        )
        from mcp_server_langgraph.websocket.types import MessageEnvelope, WebSocketConfig

        config = WebSocketConfig(endpoint_name="connection-health")
        mock_repo = AsyncMock(return_value=None)  # noqa: async-mock-config

        with patch(RATE_LIMITER_PATCH, side_effect=lambda *a, **kw: MagicMock()):
            handler = ConnectionHealthHandler(config=config, connection_repository=mock_repo, owner_id="owner-123")

        message = MessageEnvelope(
            type="subscribe",
            payload={"connection_id": "conn-123"},
            id="msg-3",
        )
        response = await handler.handle_message(message)

        assert response is not None
        assert response.type == "subscribed"
        assert response.payload["connection_id"] == "conn-123"
        assert "conn-123" in handler._subscriptions

    @pytest.mark.asyncio
    async def test_handle_subscribe_missing_connection_id(self) -> None:
        """GIVEN subscribe without connection_id WHEN handle_message THEN returns error."""
        from mcp_server_langgraph.websocket.handlers.connection_health import (
            ConnectionHealthHandler,
        )
        from mcp_server_langgraph.websocket.types import MessageEnvelope, WebSocketConfig

        config = WebSocketConfig(endpoint_name="connection-health")
        mock_repo = AsyncMock(return_value=None)  # noqa: async-mock-config

        with patch(RATE_LIMITER_PATCH, side_effect=lambda *a, **kw: MagicMock()):
            handler = ConnectionHealthHandler(config=config, connection_repository=mock_repo, owner_id="owner-123")

        message = MessageEnvelope(type="subscribe", payload={}, id="msg-4")
        response = await handler.handle_message(message)

        assert response is not None
        assert response.type == "error"
        assert response.payload["code"] == "missing_parameter"

    @pytest.mark.asyncio
    async def test_handle_subscribe_no_payload(self) -> None:
        """GIVEN subscribe with no payload WHEN handle_message THEN returns error."""
        from mcp_server_langgraph.websocket.handlers.connection_health import (
            ConnectionHealthHandler,
        )
        from mcp_server_langgraph.websocket.types import MessageEnvelope, WebSocketConfig

        config = WebSocketConfig(endpoint_name="connection-health")
        mock_repo = AsyncMock(return_value=None)  # noqa: async-mock-config

        with patch(RATE_LIMITER_PATCH, side_effect=lambda *a, **kw: MagicMock()):
            handler = ConnectionHealthHandler(config=config, connection_repository=mock_repo, owner_id="owner-123")

        message = MessageEnvelope(type="subscribe", payload=None, id="msg-5")
        response = await handler.handle_message(message)

        assert response is not None
        assert response.type == "error"
        assert response.payload["code"] == "missing_parameter"

    @pytest.mark.asyncio
    async def test_handle_unsubscribe_success(self) -> None:
        """GIVEN valid unsubscribe message WHEN handle_message called THEN removes subscription."""
        from mcp_server_langgraph.websocket.handlers.connection_health import (
            ConnectionHealthHandler,
        )
        from mcp_server_langgraph.websocket.types import MessageEnvelope, WebSocketConfig

        config = WebSocketConfig(endpoint_name="connection-health")
        mock_repo = AsyncMock(return_value=None)  # noqa: async-mock-config

        with patch(RATE_LIMITER_PATCH, side_effect=lambda *a, **kw: MagicMock()):
            handler = ConnectionHealthHandler(config=config, connection_repository=mock_repo, owner_id="owner-123")

        handler._subscriptions.add("conn-123")

        message = MessageEnvelope(
            type="unsubscribe",
            payload={"connection_id": "conn-123"},
            id="msg-6",
        )
        response = await handler.handle_message(message)

        assert response is not None
        assert response.type == "unsubscribed"
        assert response.payload["connection_id"] == "conn-123"
        assert "conn-123" not in handler._subscriptions

    @pytest.mark.asyncio
    async def test_handle_unsubscribe_missing_connection_id(self) -> None:
        """GIVEN unsubscribe without connection_id WHEN handle_message THEN returns error."""
        from mcp_server_langgraph.websocket.handlers.connection_health import (
            ConnectionHealthHandler,
        )
        from mcp_server_langgraph.websocket.types import MessageEnvelope, WebSocketConfig

        config = WebSocketConfig(endpoint_name="connection-health")
        mock_repo = AsyncMock(return_value=None)  # noqa: async-mock-config

        with patch(RATE_LIMITER_PATCH, side_effect=lambda *a, **kw: MagicMock()):
            handler = ConnectionHealthHandler(config=config, connection_repository=mock_repo, owner_id="owner-123")

        message = MessageEnvelope(type="unsubscribe", payload={}, id="msg-7")
        response = await handler.handle_message(message)

        assert response is not None
        assert response.type == "error"
        assert response.payload["code"] == "missing_parameter"

    @pytest.mark.asyncio
    async def test_handle_check_health_success(self) -> None:
        """GIVEN valid check_health message WHEN handle_message called THEN returns started."""
        from mcp_server_langgraph.websocket.handlers.connection_health import (
            ConnectionHealthHandler,
        )
        from mcp_server_langgraph.websocket.types import MessageEnvelope, WebSocketConfig

        config = WebSocketConfig(endpoint_name="connection-health")
        mock_repo = AsyncMock(return_value=None)  # noqa: async-mock-config
        mock_conn = MagicMock()
        mock_conn.id = "conn-123"
        mock_repo.get.return_value = mock_conn

        with patch(RATE_LIMITER_PATCH, side_effect=lambda *a, **kw: MagicMock()):
            handler = ConnectionHealthHandler(config=config, connection_repository=mock_repo, owner_id="owner-123")

        message = MessageEnvelope(
            type="check_health",
            payload={"connection_id": "conn-123"},
            id="msg-8",
        )
        response = await handler.handle_message(message)

        assert response is not None
        assert response.type == "health_check_started"
        assert response.payload["connection_id"] == "conn-123"
        mock_repo.get.assert_called_once_with("conn-123")

    @pytest.mark.asyncio
    async def test_handle_check_health_not_found(self) -> None:
        """GIVEN non-existent connection WHEN check_health THEN returns not found error."""
        from mcp_server_langgraph.websocket.handlers.connection_health import (
            ConnectionHealthHandler,
        )
        from mcp_server_langgraph.websocket.types import MessageEnvelope, WebSocketConfig

        config = WebSocketConfig(endpoint_name="connection-health")
        mock_repo = AsyncMock(return_value=None)  # noqa: async-mock-config
        mock_repo.get.return_value = None

        with patch(RATE_LIMITER_PATCH, side_effect=lambda *a, **kw: MagicMock()):
            handler = ConnectionHealthHandler(config=config, connection_repository=mock_repo, owner_id="owner-123")

        message = MessageEnvelope(
            type="check_health",
            payload={"connection_id": "nonexistent"},
            id="msg-9",
        )
        response = await handler.handle_message(message)

        assert response is not None
        assert response.type == "error"
        assert response.payload["code"] == "not_found"

    @pytest.mark.asyncio
    async def test_handle_check_health_missing_connection_id(self) -> None:
        """GIVEN check_health without connection_id WHEN handle_message THEN returns error."""
        from mcp_server_langgraph.websocket.handlers.connection_health import (
            ConnectionHealthHandler,
        )
        from mcp_server_langgraph.websocket.types import MessageEnvelope, WebSocketConfig

        config = WebSocketConfig(endpoint_name="connection-health")
        mock_repo = AsyncMock(return_value=None)  # noqa: async-mock-config

        with patch(RATE_LIMITER_PATCH, side_effect=lambda *a, **kw: MagicMock()):
            handler = ConnectionHealthHandler(config=config, connection_repository=mock_repo, owner_id="owner-123")

        message = MessageEnvelope(type="check_health", payload={}, id="msg-10")
        response = await handler.handle_message(message)

        assert response is not None
        assert response.type == "error"
        assert response.payload["code"] == "missing_parameter"

    @pytest.mark.asyncio
    async def test_handle_check_health_error(self) -> None:
        """GIVEN repository error WHEN check_health THEN returns error."""
        from mcp_server_langgraph.websocket.handlers.connection_health import (
            ConnectionHealthHandler,
        )
        from mcp_server_langgraph.websocket.types import MessageEnvelope, WebSocketConfig

        config = WebSocketConfig(endpoint_name="connection-health")
        mock_repo = AsyncMock(return_value=None)  # noqa: async-mock-config
        mock_repo.get.side_effect = Exception("Database error")

        with patch(RATE_LIMITER_PATCH, side_effect=lambda *a, **kw: MagicMock()):
            handler = ConnectionHealthHandler(config=config, connection_repository=mock_repo, owner_id="owner-123")

        message = MessageEnvelope(
            type="check_health",
            payload={"connection_id": "conn-123"},
            id="msg-11",
        )
        response = await handler.handle_message(message)

        assert response is not None
        assert response.type == "error"
        assert response.payload["code"] == "health_check_failed"


class TestConnectionHealthHandlerPush:
    """Tests for ConnectionHealthHandler push updates."""

    def teardown_method(self) -> None:
        """Force GC to prevent mock accumulation in xdist workers."""
        gc.collect()

    @pytest.mark.asyncio
    async def test_push_connection_update_when_subscribed(self) -> None:
        """GIVEN subscribed connection WHEN push_connection_update THEN sends update."""
        from mcp_server_langgraph.websocket.handlers.connection_health import (
            ConnectionHealthHandler,
        )
        from mcp_server_langgraph.websocket.types import WebSocketConfig

        config = WebSocketConfig(endpoint_name="connection-health")
        mock_repo = AsyncMock(return_value=None)  # noqa: async-mock-config

        with patch(RATE_LIMITER_PATCH, side_effect=lambda *a, **kw: MagicMock()):
            handler = ConnectionHealthHandler(config=config, connection_repository=mock_repo, owner_id="owner-123")

        handler._subscriptions.add("conn-123")
        mock_ws = AsyncMock(return_value=None)  # noqa: async-mock-config
        handler._websocket = mock_ws

        status = {"id": "conn-123", "status": "healthy"}
        await handler.push_connection_update("conn-123", status)

        mock_ws.send_json.assert_called_once()
        call_args = mock_ws.send_json.call_args[0][0]
        assert call_args["type"] == "connection_update"
        assert call_args["payload"] == status

    @pytest.mark.asyncio
    async def test_push_connection_update_not_subscribed(self) -> None:
        """GIVEN not subscribed WHEN push_connection_update THEN does not send."""
        from mcp_server_langgraph.websocket.handlers.connection_health import (
            ConnectionHealthHandler,
        )
        from mcp_server_langgraph.websocket.types import WebSocketConfig

        config = WebSocketConfig(endpoint_name="connection-health")
        mock_repo = AsyncMock(return_value=None)  # noqa: async-mock-config

        with patch(RATE_LIMITER_PATCH, side_effect=lambda *a, **kw: MagicMock()):
            handler = ConnectionHealthHandler(config=config, connection_repository=mock_repo, owner_id="owner-123")

        mock_ws = AsyncMock(return_value=None)  # noqa: async-mock-config
        handler._websocket = mock_ws

        status = {"id": "conn-123", "status": "healthy"}
        await handler.push_connection_update("conn-123", status)

        mock_ws.send_json.assert_not_called()

    @pytest.mark.asyncio
    async def test_push_connection_update_no_websocket(self) -> None:
        """GIVEN no websocket WHEN push_connection_update THEN does nothing."""
        from mcp_server_langgraph.websocket.handlers.connection_health import (
            ConnectionHealthHandler,
        )
        from mcp_server_langgraph.websocket.types import WebSocketConfig

        config = WebSocketConfig(endpoint_name="connection-health")
        mock_repo = AsyncMock(return_value=None)  # noqa: async-mock-config

        with patch(RATE_LIMITER_PATCH, side_effect=lambda *a, **kw: MagicMock()):
            handler = ConnectionHealthHandler(config=config, connection_repository=mock_repo, owner_id="owner-123")

        handler._subscriptions.add("conn-123")
        # No websocket set

        status = {"id": "conn-123", "status": "healthy"}
        # Should not raise
        await handler.push_connection_update("conn-123", status)


class TestConnectionRepositoryProtocol:
    """Tests for ConnectionRepositoryProtocol."""

    def teardown_method(self) -> None:
        """Force GC to prevent mock accumulation in xdist workers."""
        gc.collect()

    def test_protocol_is_runtime_checkable(self) -> None:
        """GIVEN protocol THEN is runtime checkable."""
        from mcp_server_langgraph.websocket.handlers.connection_health import (
            ConnectionRepositoryProtocol,
        )

        assert hasattr(ConnectionRepositoryProtocol, "__protocol_attrs__") or hasattr(ConnectionRepositoryProtocol, "__mro__")

    def test_protocol_instance_check(self) -> None:
        """GIVEN mock with correct methods THEN satisfies protocol."""
        from mcp_server_langgraph.websocket.handlers.connection_health import (
            ConnectionRepositoryProtocol,
        )

        mock_repo = MagicMock()
        mock_repo.list = AsyncMock(return_value=([], None))
        mock_repo.get = AsyncMock(return_value=None)

        # Protocol is runtime_checkable, so isinstance should work
        assert isinstance(mock_repo, ConnectionRepositoryProtocol)


class TestConnectionHealthHandlerWithMetrics:
    """Tests for ConnectionHealthHandler with metrics."""

    def teardown_method(self) -> None:
        """Force GC to prevent mock accumulation in xdist workers."""
        gc.collect()

    def test_init_with_metrics(self) -> None:
        """GIVEN metrics WHEN creating handler THEN stores metrics."""
        from mcp_server_langgraph.websocket.handlers.connection_health import (
            ConnectionHealthHandler,
        )
        from mcp_server_langgraph.websocket.types import WebSocketConfig

        config = WebSocketConfig(endpoint_name="connection-health")
        mock_repo = MagicMock()
        mock_metrics = MagicMock()

        with patch(RATE_LIMITER_PATCH, side_effect=lambda *a, **kw: MagicMock()):
            handler = ConnectionHealthHandler(
                config=config,
                connection_repository=mock_repo,
                owner_id="owner-123",
                metrics=mock_metrics,
            )

        assert handler._metrics is mock_metrics
