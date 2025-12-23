"""
Audit WebSocket Handler Tests.

TDD tests for the Audit WebSocket using the standardized WebSocketBase.
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
def mock_audit_broadcaster() -> MagicMock:
    """Create a mock audit event broadcaster."""
    broadcaster = MagicMock()
    broadcaster.subscribe = AsyncMock()
    broadcaster.unsubscribe = AsyncMock()
    broadcaster.broadcast = AsyncMock()
    return broadcaster


@pytest.mark.xdist_group(name="audit_ws")
class TestAuditHandler:
    """Test Audit WebSocket using WebSocketBase."""

    def teardown_method(self) -> None:
        """Force GC to prevent mock accumulation in xdist workers."""
        gc.collect()

    @pytest.mark.asyncio
    async def test_handler_extends_websocket_base(self) -> None:
        """
        GIVEN the AuditHandler class
        WHEN checking its base classes
        THEN it should extend WebSocketBase.
        """
        from mcp_server_langgraph.websocket.base import WebSocketBase
        from mcp_server_langgraph.websocket.handlers.audit import (
            AuditHandler,
        )

        assert issubclass(AuditHandler, WebSocketBase)

    @pytest.mark.asyncio
    async def test_handles_set_filter_message(self, mock_websocket: MagicMock, mock_audit_broadcaster: MagicMock) -> None:
        """
        GIVEN an active connection
        WHEN a set_filter message is received
        THEN filter should be updated and confirmed.
        """
        from mcp_server_langgraph.websocket.handlers.audit import (
            AuditHandler,
        )

        handler = AuditHandler(
            config=WebSocketConfig(require_auth=False, endpoint_name="audit"),
            broadcaster=mock_audit_broadcaster,
        )
        handler._websocket = mock_websocket

        message = MessageEnvelope(
            type="set_filter",
            payload={
                "categories": ["security", "authentication"],
                "regulations": ["HIPAA"],
            },
        )

        response = await handler.handle_message(message)

        assert response is not None
        assert response.type == "filter_updated"
        assert response.payload is not None
        assert response.payload.get("filter") is not None
        mock_audit_broadcaster.unsubscribe.assert_called_once()
        mock_audit_broadcaster.subscribe.assert_called()

    @pytest.mark.asyncio
    async def test_handles_clear_filter_message(self, mock_websocket: MagicMock, mock_audit_broadcaster: MagicMock) -> None:
        """
        GIVEN an active connection with filters
        WHEN a clear_filter message is received
        THEN filters should be cleared.
        """
        from mcp_server_langgraph.websocket.handlers.audit import (
            AuditHandler,
        )

        handler = AuditHandler(
            config=WebSocketConfig(require_auth=False, endpoint_name="audit"),
            broadcaster=mock_audit_broadcaster,
        )
        handler._websocket = mock_websocket

        message = MessageEnvelope(
            type="clear_filter",
            payload={},
        )

        response = await handler.handle_message(message)

        assert response is not None
        assert response.type == "filter_updated"
        # Filter should be empty/cleared
        assert response.payload is not None
        filter_data = response.payload.get("filter", {})
        # Either None or empty lists
        assert filter_data.get("categories") is None or filter_data.get("categories") == []

    @pytest.mark.asyncio
    async def test_returns_error_for_unknown_message(
        self, mock_websocket: MagicMock, mock_audit_broadcaster: MagicMock
    ) -> None:
        """
        GIVEN an active connection
        WHEN an unknown message type is received
        THEN an error response should be returned.
        """
        from mcp_server_langgraph.websocket.handlers.audit import (
            AuditHandler,
        )

        handler = AuditHandler(
            config=WebSocketConfig(require_auth=False, endpoint_name="audit"),
            broadcaster=mock_audit_broadcaster,
        )

        message = MessageEnvelope(
            type="unknown_type",
            payload={},
        )

        response = await handler.handle_message(message)

        assert response is not None
        assert response.type == "error"

    @pytest.mark.asyncio
    async def test_push_audit_event(self, mock_websocket: MagicMock, mock_audit_broadcaster: MagicMock) -> None:
        """
        GIVEN an active connection
        WHEN push_audit_event is called
        THEN event should be sent to client.
        """
        from mcp_server_langgraph.websocket.handlers.audit import (
            AuditHandler,
        )

        handler = AuditHandler(
            config=WebSocketConfig(require_auth=False, endpoint_name="audit"),
            broadcaster=mock_audit_broadcaster,
        )
        handler._websocket = mock_websocket

        await handler.push_audit_event(
            {
                "event_id": "evt-001",
                "timestamp": "2025-01-15T10:30:00Z",
                "category": "authentication",
                "event_type": "login_success",
                "actor": "user:alice",
            }
        )

        mock_websocket.send_json.assert_called_once()
        call_args = mock_websocket.send_json.call_args[0][0]
        assert call_args["type"] == "audit_event"
        assert call_args["payload"]["event_id"] == "evt-001"

    @pytest.mark.asyncio
    async def test_on_connect_subscribes_to_broadcaster(
        self, mock_websocket: MagicMock, mock_audit_broadcaster: MagicMock
    ) -> None:
        """
        GIVEN a new connection
        WHEN on_connect is called
        THEN handler should subscribe to broadcaster.
        """
        from mcp_server_langgraph.websocket.handlers.audit import (
            AuditHandler,
        )
        from mcp_server_langgraph.websocket.types import AuthUser

        handler = AuditHandler(
            config=WebSocketConfig(require_auth=False, endpoint_name="audit"),
            broadcaster=mock_audit_broadcaster,
        )
        handler._websocket = mock_websocket

        user = AuthUser(id="user-123", username="testuser", roles=["admin"])
        await handler.on_connect(user)

        mock_audit_broadcaster.subscribe.assert_called_once()

    @pytest.mark.asyncio
    async def test_on_disconnect_unsubscribes_from_broadcaster(
        self, mock_websocket: MagicMock, mock_audit_broadcaster: MagicMock
    ) -> None:
        """
        GIVEN an active connection
        WHEN on_disconnect is called
        THEN handler should unsubscribe from broadcaster.
        """
        from mcp_server_langgraph.websocket.handlers.audit import (
            AuditHandler,
        )

        handler = AuditHandler(
            config=WebSocketConfig(require_auth=False, endpoint_name="audit"),
            broadcaster=mock_audit_broadcaster,
        )
        handler._websocket = mock_websocket

        await handler.on_disconnect()

        mock_audit_broadcaster.unsubscribe.assert_called_once_with(mock_websocket)
