"""
Unit tests for Cost Tracking WebSocket endpoint.

Tests the cost_tracking_ws.py endpoint which provides
real-time cost tracking during LLM operations.

TDD: RED phase - tests written before implementation.
"""

import gc

import pytest

pytestmark = [
    pytest.mark.unit,
    pytest.mark.websocket,
    pytest.mark.api,
    pytest.mark.xdist_group(name="cost_tracking_ws"),
]


@pytest.mark.xdist_group(name="cost_tracking_ws")
class TestCostTrackingWebSocketHandler:
    """Tests for CostTrackingWebSocketHandler class."""

    def teardown_method(self) -> None:
        """Force GC to prevent mock accumulation in xdist workers."""
        gc.collect()

    def test_handler_exists(self) -> None:
        """GIVEN the module WHEN importing THEN handler class exists."""
        from mcp_server_langgraph.api.v1.cost_tracking_ws import (
            CostTrackingWebSocketHandler,
        )

        assert CostTrackingWebSocketHandler is not None

    def test_handler_extends_websocket_base(self) -> None:
        """GIVEN handler WHEN checking inheritance THEN extends WebSocketBase."""
        from mcp_server_langgraph.api.v1.cost_tracking_ws import (
            CostTrackingWebSocketHandler,
        )
        from mcp_server_langgraph.websocket.base import WebSocketBase

        assert issubclass(CostTrackingWebSocketHandler, WebSocketBase)

    def test_handler_config_has_correct_endpoint_name(self) -> None:
        """GIVEN handler WHEN checking config THEN endpoint name is correct."""
        from mcp_server_langgraph.api.v1.cost_tracking_ws import (
            CostTrackingWebSocketHandler,
        )

        handler = CostTrackingWebSocketHandler()
        assert handler.config.endpoint_name == "cost-tracking"

    def test_handler_requires_auth(self) -> None:
        """GIVEN handler WHEN checking config THEN auth is required."""
        from mcp_server_langgraph.api.v1.cost_tracking_ws import (
            CostTrackingWebSocketHandler,
        )

        handler = CostTrackingWebSocketHandler()
        assert handler.config.require_auth is True


@pytest.mark.xdist_group(name="cost_tracking_ws")
class TestCostTrackingMessageHandling:
    """Tests for message handling in CostTrackingWebSocketHandler."""

    def teardown_method(self) -> None:
        """Force GC to prevent mock accumulation in xdist workers."""
        gc.collect()

    @pytest.mark.asyncio
    async def test_subscribe_session_returns_total(self) -> None:
        """GIVEN subscribe_session message WHEN handling THEN returns session total."""
        from mcp_server_langgraph.api.v1.cost_tracking_ws import (
            CostTrackingWebSocketHandler,
        )
        from mcp_server_langgraph.websocket.types import MessageEnvelope

        handler = CostTrackingWebSocketHandler()

        message = MessageEnvelope(
            type="subscribe_session",
            payload={"session_id": "sess_123"},
        )

        response = await handler.handle_message(message)

        assert response is not None
        assert response.type == "session_total"
        assert "session_id" in response.payload

    @pytest.mark.asyncio
    async def test_subscribe_user_returns_budget(self) -> None:
        """GIVEN subscribe_user message WHEN handling THEN returns user budget."""
        from mcp_server_langgraph.api.v1.cost_tracking_ws import (
            CostTrackingWebSocketHandler,
        )
        from mcp_server_langgraph.websocket.types import MessageEnvelope

        handler = CostTrackingWebSocketHandler()

        message = MessageEnvelope(
            type="subscribe_user",
            payload={"user_id": "user_123"},
        )

        response = await handler.handle_message(message)

        assert response is not None
        assert response.type == "user_budget"
        assert "user_id" in response.payload

    @pytest.mark.asyncio
    async def test_unsubscribe_returns_confirmation(self) -> None:
        """GIVEN unsubscribe message WHEN handling THEN confirms."""
        from mcp_server_langgraph.api.v1.cost_tracking_ws import (
            CostTrackingWebSocketHandler,
        )
        from mcp_server_langgraph.websocket.types import MessageEnvelope

        handler = CostTrackingWebSocketHandler()

        message = MessageEnvelope(
            type="unsubscribe",
            payload={"session_id": "sess_123"},
        )

        response = await handler.handle_message(message)

        assert response is not None
        assert response.type == "unsubscribed"


@pytest.mark.xdist_group(name="cost_tracking_ws")
class TestCostTrackingRouter:
    """Tests for the router endpoint."""

    def teardown_method(self) -> None:
        """Force GC to prevent mock accumulation in xdist workers."""
        gc.collect()

    def test_router_exists(self) -> None:
        """GIVEN the module WHEN importing THEN router exists."""
        from mcp_server_langgraph.api.v1.cost_tracking_ws import router

        assert router is not None

    def test_router_has_websocket_route(self) -> None:
        """GIVEN router WHEN checking routes THEN has websocket route."""
        from mcp_server_langgraph.api.v1.cost_tracking_ws import router

        routes = router.routes
        assert len(routes) > 0
