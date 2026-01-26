"""
Cost Tracking WebSocket Handler Tests.

TDD tests for the Cost Tracking WebSocket using the standardized WebSocketBase.
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
def mock_cost_service() -> MagicMock:
    """Create a mock cost tracking service."""
    service = MagicMock()
    service.get_session_cost = AsyncMock(
        return_value={
            "session_id": "session-1",
            "total_cost": 1.25,
            "token_count": 5000,
        }
    )
    service.get_user_budget = AsyncMock(
        return_value={
            "user_id": "user-1",
            "budget_limit": 100.0,
            "current_usage": 45.50,
            "remaining": 54.50,
        }
    )
    return service


@pytest.mark.xdist_group(name="cost_tracking_ws")
class TestCostTrackingHandler:
    """Test Cost Tracking WebSocket using WebSocketBase."""

    def teardown_method(self) -> None:
        """Force GC to prevent mock accumulation in xdist workers."""
        gc.collect()

    @pytest.mark.asyncio
    async def test_handler_extends_websocket_base(self) -> None:
        """
        GIVEN the CostTrackingHandler class
        WHEN checking its base classes
        THEN it should extend WebSocketBase.
        """
        from mcp_server_langgraph.websocket.base import WebSocketBase
        from mcp_server_langgraph.websocket.handlers.cost_tracking import (
            CostTrackingHandler,
        )

        assert issubclass(CostTrackingHandler, WebSocketBase)

    @pytest.mark.asyncio
    async def test_handles_subscribe_session(self, mock_websocket: MagicMock, mock_cost_service: MagicMock) -> None:
        """
        GIVEN an active connection
        WHEN a subscribe_session message is received
        THEN the client should be subscribed to session cost updates.
        """
        from mcp_server_langgraph.websocket.handlers.cost_tracking import (
            CostTrackingHandler,
        )

        handler = CostTrackingHandler(
            config=WebSocketConfig(require_auth=True, endpoint_name="cost-tracking"),
            cost_service=mock_cost_service,
        )

        message = MessageEnvelope(
            type="subscribe_session",
            payload={"session_id": "session-1"},
        )

        response = await handler.handle_message(message)

        assert response is not None
        assert response.type == "session_total"
        assert "session-1" in handler.subscribed_sessions

    @pytest.mark.asyncio
    async def test_handles_subscribe_user(self, mock_websocket: MagicMock, mock_cost_service: MagicMock) -> None:
        """
        GIVEN an active connection
        WHEN a subscribe_user message is received
        THEN the client should be subscribed to user budget updates.
        """
        from mcp_server_langgraph.websocket.handlers.cost_tracking import (
            CostTrackingHandler,
        )

        handler = CostTrackingHandler(
            config=WebSocketConfig(require_auth=True, endpoint_name="cost-tracking"),
            cost_service=mock_cost_service,
        )

        message = MessageEnvelope(
            type="subscribe_user",
            payload={"user_id": "user-1"},
        )

        response = await handler.handle_message(message)

        assert response is not None
        assert response.type == "user_budget"
        assert "user-1" in handler.subscribed_users

    @pytest.mark.asyncio
    async def test_handles_unsubscribe(self, mock_websocket: MagicMock, mock_cost_service: MagicMock) -> None:
        """
        GIVEN an active connection with subscriptions
        WHEN an unsubscribe message is received
        THEN the client should be unsubscribed.
        """
        from mcp_server_langgraph.websocket.handlers.cost_tracking import (
            CostTrackingHandler,
        )

        handler = CostTrackingHandler(
            config=WebSocketConfig(require_auth=True, endpoint_name="cost-tracking"),
            cost_service=mock_cost_service,
        )
        handler.subscribed_sessions.add("session-1")

        message = MessageEnvelope(
            type="unsubscribe",
            payload={"session_id": "session-1"},
        )

        response = await handler.handle_message(message)

        assert response is not None
        assert response.type == "unsubscribed"
        assert "session-1" not in handler.subscribed_sessions
