"""
Unit tests for Audit WebSocket Handler.

Tests the AuditHandler class for real-time audit event streaming.
"""

from __future__ import annotations

import gc
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

pytestmark = [
    pytest.mark.unit,
    pytest.mark.websocket,
    pytest.mark.xdist_group(name="websocket_audit_handler"),
]

RATE_LIMITER_PATCH = "mcp_server_langgraph.websocket.rate_limiter.get_websocket_rate_limiter"


@pytest.mark.xdist_group(name="websocket_audit_handler_init")
class TestAuditHandlerInit:
    """Tests for AuditHandler initialization."""

    def teardown_method(self) -> None:
        """Force GC to prevent mock accumulation in xdist workers."""
        gc.collect()

    def test_init_stores_broadcaster(self) -> None:
        """GIVEN broadcaster WHEN creating handler THEN stores broadcaster."""
        from mcp_server_langgraph.websocket.handlers.audit import AuditFilter, AuditHandler
        from mcp_server_langgraph.websocket.types import WebSocketConfig

        config = WebSocketConfig(endpoint_name="audit")
        mock_broadcaster = MagicMock()

        with patch(RATE_LIMITER_PATCH, return_value=MagicMock()):
            handler = AuditHandler(config=config, broadcaster=mock_broadcaster)

        assert handler._broadcaster is mock_broadcaster
        assert isinstance(handler._current_filter, AuditFilter)
        assert handler.user_id is None


@pytest.mark.xdist_group(name="websocket_audit_handler_lifecycle")
class TestAuditHandlerLifecycle:
    """Tests for AuditHandler lifecycle hooks."""

    def teardown_method(self) -> None:
        """Force GC to prevent mock accumulation in xdist workers."""
        gc.collect()

    @pytest.mark.asyncio
    async def test_on_connect_subscribes(self) -> None:
        """GIVEN user WHEN on_connect called THEN subscribes with empty filter."""
        from mcp_server_langgraph.websocket.handlers.audit import AuditHandler
        from mcp_server_langgraph.websocket.types import AuthUser, WebSocketConfig

        config = WebSocketConfig(endpoint_name="audit")
        mock_broadcaster = AsyncMock(return_value=None)  # noqa: async-mock-config

        with patch(RATE_LIMITER_PATCH, return_value=MagicMock()):
            handler = AuditHandler(config=config, broadcaster=mock_broadcaster)

        mock_ws = AsyncMock(return_value=None)  # noqa: async-mock-config
        handler._websocket = mock_ws
        user = AuthUser(id="user-123", username="testuser")
        handler._user = user  # Base class sets this before calling on_connect

        await handler.on_connect(user)

        assert handler.user_id == "user-123"
        mock_broadcaster.subscribe.assert_called_once()

    @pytest.mark.asyncio
    async def test_on_disconnect_unsubscribes(self) -> None:
        """GIVEN connected WHEN on_disconnect called THEN unsubscribes."""
        from mcp_server_langgraph.websocket.handlers.audit import AuditHandler
        from mcp_server_langgraph.websocket.types import AuthUser, WebSocketConfig

        config = WebSocketConfig(endpoint_name="audit")
        mock_broadcaster = AsyncMock(return_value=None)  # noqa: async-mock-config

        with patch(RATE_LIMITER_PATCH, return_value=MagicMock()):
            handler = AuditHandler(config=config, broadcaster=mock_broadcaster)

        mock_ws = AsyncMock(return_value=None)  # noqa: async-mock-config
        handler._websocket = mock_ws
        handler._user = AuthUser(id="user-123", username="user-123")

        await handler.on_disconnect()

        mock_broadcaster.unsubscribe.assert_called_once_with(mock_ws)


@pytest.mark.xdist_group(name="websocket_audit_handler_messages")
class TestAuditHandlerMessages:
    """Tests for AuditHandler message handling."""

    def teardown_method(self) -> None:
        """Force GC to prevent mock accumulation in xdist workers."""
        gc.collect()

    @pytest.mark.asyncio
    async def test_handle_set_filter(self) -> None:
        """GIVEN set_filter message WHEN handle_message called THEN updates filter."""
        from mcp_server_langgraph.websocket.handlers.audit import AuditHandler
        from mcp_server_langgraph.websocket.types import MessageEnvelope, WebSocketConfig

        config = WebSocketConfig(endpoint_name="audit")
        mock_broadcaster = AsyncMock(return_value=None)  # noqa: async-mock-config

        with patch(RATE_LIMITER_PATCH, return_value=MagicMock()):
            handler = AuditHandler(config=config, broadcaster=mock_broadcaster)

        mock_ws = AsyncMock(return_value=None)  # noqa: async-mock-config
        handler._websocket = mock_ws

        message = MessageEnvelope(
            type="set_filter",
            id="msg-1",
            payload={
                "categories": ["security"],
                "regulations": ["gdpr"],
            },
        )
        response = await handler.handle_message(message)

        assert response is not None
        assert response.type == "filter_updated"
        assert response.id == "msg-1"
        assert response.payload["filter"]["categories"] == ["security"]
        assert response.payload["filter"]["regulations"] == ["gdpr"]
        mock_broadcaster.unsubscribe.assert_called_once()
        mock_broadcaster.subscribe.assert_called_once()

    @pytest.mark.asyncio
    async def test_handle_clear_filter(self) -> None:
        """GIVEN clear_filter message WHEN handle_message called THEN clears filter."""
        from mcp_server_langgraph.websocket.handlers.audit import AuditHandler
        from mcp_server_langgraph.websocket.types import MessageEnvelope, WebSocketConfig

        config = WebSocketConfig(endpoint_name="audit")
        mock_broadcaster = AsyncMock(return_value=None)  # noqa: async-mock-config

        with patch(RATE_LIMITER_PATCH, return_value=MagicMock()):
            handler = AuditHandler(config=config, broadcaster=mock_broadcaster)

        mock_ws = AsyncMock(return_value=None)  # noqa: async-mock-config
        handler._websocket = mock_ws
        handler._current_filter.categories = ["old_category"]

        message = MessageEnvelope(type="clear_filter", id="msg-2")
        response = await handler.handle_message(message)

        assert response is not None
        assert response.type == "filter_updated"
        assert response.id == "msg-2"
        assert response.payload["filter"]["categories"] is None
        assert handler._current_filter.categories is None

    @pytest.mark.asyncio
    async def test_handle_unknown_message_type(self) -> None:
        """GIVEN unknown message type WHEN handle_message called THEN returns error."""
        from mcp_server_langgraph.websocket.handlers.audit import AuditHandler
        from mcp_server_langgraph.websocket.types import MessageEnvelope, WebSocketConfig

        config = WebSocketConfig(endpoint_name="audit")
        mock_broadcaster = AsyncMock(return_value=None)  # noqa: async-mock-config

        with patch(RATE_LIMITER_PATCH, return_value=MagicMock()):
            handler = AuditHandler(config=config, broadcaster=mock_broadcaster)

        message = MessageEnvelope(type="invalid", id="msg-3")
        response = await handler.handle_message(message)

        assert response is not None
        assert response.type == "error"
        assert response.payload["code"] == "unknown_message_type"


@pytest.mark.xdist_group(name="websocket_audit_handler_push")
class TestAuditHandlerPush:
    """Tests for AuditHandler push functionality."""

    def teardown_method(self) -> None:
        """Force GC to prevent mock accumulation in xdist workers."""
        gc.collect()

    @pytest.mark.asyncio
    async def test_push_audit_event(self) -> None:
        """GIVEN websocket WHEN push_audit_event called THEN sends event."""
        from mcp_server_langgraph.websocket.handlers.audit import AuditHandler
        from mcp_server_langgraph.websocket.types import WebSocketConfig

        config = WebSocketConfig(endpoint_name="audit")
        mock_broadcaster = AsyncMock(return_value=None)  # noqa: async-mock-config

        with patch(RATE_LIMITER_PATCH, return_value=MagicMock()):
            handler = AuditHandler(config=config, broadcaster=mock_broadcaster)

        mock_ws = AsyncMock(return_value=None)  # noqa: async-mock-config
        handler._websocket = mock_ws

        event = {"id": "event-1", "category": "security", "action": "login"}
        await handler.push_audit_event(event)

        mock_ws.send_json.assert_called_once()
        sent_data = mock_ws.send_json.call_args[0][0]
        assert sent_data["type"] == "audit_event"
        assert sent_data["payload"] == event

    @pytest.mark.asyncio
    async def test_push_audit_event_no_websocket(self) -> None:
        """GIVEN no websocket WHEN push_audit_event called THEN does not send."""
        from mcp_server_langgraph.websocket.handlers.audit import AuditHandler
        from mcp_server_langgraph.websocket.types import WebSocketConfig

        config = WebSocketConfig(endpoint_name="audit")
        mock_broadcaster = AsyncMock(return_value=None)  # noqa: async-mock-config

        with patch(RATE_LIMITER_PATCH, return_value=MagicMock()):
            handler = AuditHandler(config=config, broadcaster=mock_broadcaster)

        # No websocket set
        event = {"id": "event-1"}
        await handler.push_audit_event(event)
        # Should not raise


@pytest.mark.xdist_group(name="websocket_audit_filter")
class TestAuditFilter:
    """Tests for AuditFilter dataclass."""

    def teardown_method(self) -> None:
        """Force GC to prevent mock accumulation in xdist workers."""
        gc.collect()

    def test_audit_filter_without_args_has_all_none_fields(self) -> None:
        """GIVEN no args WHEN creating AuditFilter THEN all fields are None."""
        from mcp_server_langgraph.websocket.handlers.audit import AuditFilter

        filter_ = AuditFilter()

        assert filter_.categories is None
        assert filter_.regulations is None
        assert filter_.actors is None
        assert filter_.event_types is None

    def test_audit_filter_with_args_stores_provided_values(self) -> None:
        """GIVEN values WHEN creating AuditFilter THEN stores values."""
        from mcp_server_langgraph.websocket.handlers.audit import AuditFilter

        filter_ = AuditFilter(
            categories=["security", "compliance"],
            regulations=["gdpr", "hipaa"],
            actors=["user-1"],
            event_types=["create", "delete"],
        )

        assert filter_.categories == ["security", "compliance"]
        assert filter_.regulations == ["gdpr", "hipaa"]
        assert filter_.actors == ["user-1"]
        assert filter_.event_types == ["create", "delete"]
