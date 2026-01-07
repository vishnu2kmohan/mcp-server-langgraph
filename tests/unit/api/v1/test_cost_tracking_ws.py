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

    def test_handler_class_exists_on_import(self) -> None:
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

    def test_router_exists_on_import(self) -> None:
        """GIVEN the module WHEN importing THEN router exists."""
        from mcp_server_langgraph.api.v1.cost_tracking_ws import router

        assert router is not None

    def test_router_has_websocket_route(self) -> None:
        """GIVEN router WHEN checking routes THEN has websocket route."""
        from mcp_server_langgraph.api.v1.cost_tracking_ws import router

        routes = router.routes
        assert len(routes) > 0


@pytest.mark.xdist_group(name="cost_tracking_ws")
class TestCostTrackingServiceIntegration:
    """Tests for CostTrackingServiceAdapter integration."""

    def teardown_method(self) -> None:
        """Force GC to prevent mock accumulation in xdist workers."""
        gc.collect()

    @pytest.mark.asyncio
    async def test_subscribe_session_uses_service_adapter(self) -> None:
        """GIVEN handler WHEN subscribe_session THEN uses CostTrackingServiceAdapter.

        TDD: This test verifies the handler delegates to the actual service
        rather than using inline mock data.
        """
        from unittest.mock import AsyncMock, patch

        from mcp_server_langgraph.api.v1.cost_tracking_ws import (
            CostTrackingWebSocketHandler,
        )
        from mcp_server_langgraph.websocket.types import MessageEnvelope

        # Mock session cost from service
        mock_session_cost = {
            "session_id": "sess_test",
            "total_cost": 1.23,
            "token_count": 5000,
            "updated_at": "2025-01-01T00:00:00Z",
        }

        with patch("mcp_server_langgraph.api.v1.cost_tracking_ws.get_websocket_cost_service") as mock_get_service:
            mock_service = AsyncMock()
            mock_service.get_session_cost.return_value = mock_session_cost
            mock_get_service.return_value = mock_service

            handler = CostTrackingWebSocketHandler()

            message = MessageEnvelope(
                type="subscribe_session",
                payload={"session_id": "sess_test"},
            )

            response = await handler.handle_message(message)

            # Verify service was called
            mock_service.get_session_cost.assert_called_once_with("sess_test")

            # Verify response uses service data
            # Note: Handler transforms total_cost to Decimal string
            assert response is not None
            assert response.type == "session_total"
            assert response.payload["total_cost"] == "1.23"
            assert response.payload["token_count"] == 5000

    @pytest.mark.asyncio
    async def test_subscribe_user_uses_service_adapter(self) -> None:
        """GIVEN handler WHEN subscribe_user THEN uses CostTrackingServiceAdapter."""
        from unittest.mock import AsyncMock, patch

        from mcp_server_langgraph.api.v1.cost_tracking_ws import (
            CostTrackingWebSocketHandler,
        )
        from mcp_server_langgraph.websocket.types import MessageEnvelope

        # Mock user budget from service
        mock_user_budget = {
            "user_id": "user_test",
            "budget_limit": 100.0,
            "current_usage": 25.50,
            "remaining": 74.50,
        }

        with patch("mcp_server_langgraph.api.v1.cost_tracking_ws.get_websocket_cost_service") as mock_get_service:
            mock_service = AsyncMock()
            mock_service.get_user_budget.return_value = mock_user_budget
            mock_get_service.return_value = mock_service

            handler = CostTrackingWebSocketHandler()

            message = MessageEnvelope(
                type="subscribe_user",
                payload={"user_id": "user_test"},
            )

            response = await handler.handle_message(message)

            # Verify service was called
            mock_service.get_user_budget.assert_called_once_with("user_test")

            # Verify response uses service data
            assert response is not None
            assert response.type == "user_budget"
            assert response.payload["budget_limit"] == 100.0
            assert response.payload["current_usage"] == 25.50

    @pytest.mark.asyncio
    async def test_handler_initializes_with_service(self) -> None:
        """GIVEN handler WHEN initialized THEN has service attribute."""
        from unittest.mock import AsyncMock, patch

        from mcp_server_langgraph.api.v1.cost_tracking_ws import (
            CostTrackingWebSocketHandler,
        )

        with patch("mcp_server_langgraph.api.v1.cost_tracking_ws.get_websocket_cost_service") as mock_get_service:
            mock_service = AsyncMock()  # noqa: async-mock-config
            mock_get_service.return_value = mock_service

            handler = CostTrackingWebSocketHandler()

            # Verify handler has service reference
            assert hasattr(handler, "_cost_service")
            assert handler._cost_service is mock_service
