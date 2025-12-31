"""
Unit tests for Cost Tracking WebSocket Handler.

Tests the CostTrackingHandler class for real-time cost monitoring.
"""

from __future__ import annotations

import gc
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

pytestmark = [
    pytest.mark.unit,
    pytest.mark.websocket,
    pytest.mark.xdist_group(name="websocket_cost_tracking_handler"),
]

RATE_LIMITER_PATCH = "mcp_server_langgraph.websocket.rate_limiter.get_websocket_rate_limiter"


@pytest.mark.xdist_group(name="websocket_cost_tracking_init")
class TestCostTrackingHandlerInit:
    """Tests for CostTrackingHandler initialization."""

    def teardown_method(self) -> None:
        """Force GC to prevent mock accumulation in xdist workers."""
        gc.collect()

    def test_init_stores_cost_service(self) -> None:
        """GIVEN cost_service WHEN creating handler THEN stores service."""
        from mcp_server_langgraph.websocket.handlers.cost_tracking import (
            CostTrackingHandler,
        )
        from mcp_server_langgraph.websocket.types import WebSocketConfig

        config = WebSocketConfig(endpoint_name="cost-tracking")
        mock_service = MagicMock()

        with patch(RATE_LIMITER_PATCH, return_value=MagicMock()):
            handler = CostTrackingHandler(config=config, cost_service=mock_service)

        assert handler._cost_service is mock_service
        assert handler.subscribed_sessions == set()
        assert handler.subscribed_users == set()

    def test_init_with_metrics(self) -> None:
        """GIVEN metrics WHEN creating handler THEN stores metrics."""
        from mcp_server_langgraph.websocket.handlers.cost_tracking import (
            CostTrackingHandler,
        )
        from mcp_server_langgraph.websocket.types import WebSocketConfig

        config = WebSocketConfig(endpoint_name="cost-tracking")
        mock_service = MagicMock()
        mock_metrics = MagicMock()

        with patch(RATE_LIMITER_PATCH, return_value=MagicMock()):
            handler = CostTrackingHandler(config=config, cost_service=mock_service, metrics=mock_metrics)

        assert handler._metrics is mock_metrics


@pytest.mark.xdist_group(name="websocket_cost_tracking_lifecycle")
class TestCostTrackingHandlerLifecycle:
    """Tests for CostTrackingHandler lifecycle hooks."""

    def teardown_method(self) -> None:
        """Force GC to prevent mock accumulation in xdist workers."""
        gc.collect()

    @pytest.mark.asyncio
    async def test_on_connect_logs_connection(self) -> None:
        """GIVEN user WHEN on_connect called THEN logs connection."""
        from mcp_server_langgraph.websocket.handlers.cost_tracking import (
            CostTrackingHandler,
        )
        from mcp_server_langgraph.websocket.types import AuthUser, WebSocketConfig

        config = WebSocketConfig(endpoint_name="cost-tracking")
        mock_service = AsyncMock()  # noqa: async-mock-config

        with patch(RATE_LIMITER_PATCH, return_value=MagicMock()):
            handler = CostTrackingHandler(config=config, cost_service=mock_service)

        user = AuthUser(id="user-123", username="testuser")

        # Should not raise
        await handler.on_connect(user)

    @pytest.mark.asyncio
    async def test_on_disconnect_clears_subscriptions(self) -> None:
        """GIVEN subscriptions WHEN on_disconnect called THEN clears."""
        from mcp_server_langgraph.websocket.handlers.cost_tracking import (
            CostTrackingHandler,
        )
        from mcp_server_langgraph.websocket.types import WebSocketConfig

        config = WebSocketConfig(endpoint_name="cost-tracking")
        mock_service = AsyncMock()  # noqa: async-mock-config

        with patch(RATE_LIMITER_PATCH, return_value=MagicMock()):
            handler = CostTrackingHandler(config=config, cost_service=mock_service)

        handler.subscribed_sessions = {"session-1", "session-2"}
        handler.subscribed_users = {"user-1"}

        await handler.on_disconnect()

        assert handler.subscribed_sessions == set()
        assert handler.subscribed_users == set()


@pytest.mark.xdist_group(name="websocket_cost_tracking_messages")
class TestCostTrackingHandlerMessages:
    """Tests for CostTrackingHandler message handling."""

    def teardown_method(self) -> None:
        """Force GC to prevent mock accumulation in xdist workers."""
        gc.collect()

    @pytest.mark.asyncio
    async def test_handle_subscribe_session(self) -> None:
        """GIVEN subscribe_session message WHEN handle_message called THEN subscribes."""
        from mcp_server_langgraph.websocket.handlers.cost_tracking import (
            CostTrackingHandler,
        )
        from mcp_server_langgraph.websocket.types import MessageEnvelope, WebSocketConfig

        config = WebSocketConfig(endpoint_name="cost-tracking")
        mock_service = AsyncMock()  # noqa: async-mock-config
        mock_service.get_session_cost.return_value = {
            "total_cost": 0.50,
            "total_tokens": 5000,
            "session_id": "session-1",
        }

        with patch(RATE_LIMITER_PATCH, return_value=MagicMock()):
            handler = CostTrackingHandler(config=config, cost_service=mock_service)

        message = MessageEnvelope(type="subscribe_session", id="msg-1", payload={"session_id": "session-1"})
        response = await handler.handle_message(message)

        assert response is not None
        assert response.type == "session_total"
        assert response.id == "msg-1"
        assert "session-1" in handler.subscribed_sessions
        mock_service.get_session_cost.assert_called_once_with("session-1")

    @pytest.mark.asyncio
    async def test_handle_subscribe_session_missing_session_id(self) -> None:
        """GIVEN subscribe_session without session_id WHEN handle_message THEN error."""
        from mcp_server_langgraph.websocket.handlers.cost_tracking import (
            CostTrackingHandler,
        )
        from mcp_server_langgraph.websocket.types import MessageEnvelope, WebSocketConfig

        config = WebSocketConfig(endpoint_name="cost-tracking")
        mock_service = AsyncMock()  # noqa: async-mock-config

        with patch(RATE_LIMITER_PATCH, return_value=MagicMock()):
            handler = CostTrackingHandler(config=config, cost_service=mock_service)

        message = MessageEnvelope(type="subscribe_session", id="msg-1", payload={})
        response = await handler.handle_message(message)

        assert response is not None
        assert response.type == "error"
        assert response.payload["code"] == "missing_session_id"

    @pytest.mark.asyncio
    async def test_handle_subscribe_session_error(self) -> None:
        """GIVEN service error WHEN subscribe_session THEN returns error."""
        from mcp_server_langgraph.websocket.handlers.cost_tracking import (
            CostTrackingHandler,
        )
        from mcp_server_langgraph.websocket.types import MessageEnvelope, WebSocketConfig

        config = WebSocketConfig(endpoint_name="cost-tracking")
        mock_service = AsyncMock()  # noqa: async-mock-config
        mock_service.get_session_cost.side_effect = Exception("Database error")

        with patch(RATE_LIMITER_PATCH, return_value=MagicMock()):
            handler = CostTrackingHandler(config=config, cost_service=mock_service)

        message = MessageEnvelope(type="subscribe_session", id="msg-1", payload={"session_id": "session-1"})
        response = await handler.handle_message(message)

        assert response is not None
        assert response.type == "error"
        assert response.payload["code"] == "session_cost_error"

    @pytest.mark.asyncio
    async def test_handle_subscribe_user(self) -> None:
        """GIVEN subscribe_user message WHEN handle_message called THEN subscribes."""
        from mcp_server_langgraph.websocket.handlers.cost_tracking import (
            CostTrackingHandler,
        )
        from mcp_server_langgraph.websocket.types import MessageEnvelope, WebSocketConfig

        config = WebSocketConfig(endpoint_name="cost-tracking")
        mock_service = AsyncMock()  # noqa: async-mock-config
        mock_service.get_user_budget.return_value = {
            "user_id": "user-1",
            "budget_limit": 100.00,
            "current_usage": 45.50,
            "remaining": 54.50,
        }

        with patch(RATE_LIMITER_PATCH, return_value=MagicMock()):
            handler = CostTrackingHandler(config=config, cost_service=mock_service)

        message = MessageEnvelope(type="subscribe_user", id="msg-1", payload={"user_id": "user-1"})
        response = await handler.handle_message(message)

        assert response is not None
        assert response.type == "user_budget"
        assert response.id == "msg-1"
        assert "user-1" in handler.subscribed_users
        mock_service.get_user_budget.assert_called_once_with("user-1")

    @pytest.mark.asyncio
    async def test_handle_subscribe_user_missing_user_id(self) -> None:
        """GIVEN subscribe_user without user_id WHEN handle_message THEN error."""
        from mcp_server_langgraph.websocket.handlers.cost_tracking import (
            CostTrackingHandler,
        )
        from mcp_server_langgraph.websocket.types import MessageEnvelope, WebSocketConfig

        config = WebSocketConfig(endpoint_name="cost-tracking")
        mock_service = AsyncMock()  # noqa: async-mock-config

        with patch(RATE_LIMITER_PATCH, return_value=MagicMock()):
            handler = CostTrackingHandler(config=config, cost_service=mock_service)

        message = MessageEnvelope(type="subscribe_user", id="msg-1", payload={})
        response = await handler.handle_message(message)

        assert response is not None
        assert response.type == "error"
        assert response.payload["code"] == "missing_user_id"

    @pytest.mark.asyncio
    async def test_handle_subscribe_user_error(self) -> None:
        """GIVEN service error WHEN subscribe_user THEN returns error."""
        from mcp_server_langgraph.websocket.handlers.cost_tracking import (
            CostTrackingHandler,
        )
        from mcp_server_langgraph.websocket.types import MessageEnvelope, WebSocketConfig

        config = WebSocketConfig(endpoint_name="cost-tracking")
        mock_service = AsyncMock()  # noqa: async-mock-config
        mock_service.get_user_budget.side_effect = Exception("User not found")

        with patch(RATE_LIMITER_PATCH, return_value=MagicMock()):
            handler = CostTrackingHandler(config=config, cost_service=mock_service)

        message = MessageEnvelope(type="subscribe_user", id="msg-1", payload={"user_id": "user-1"})
        response = await handler.handle_message(message)

        assert response is not None
        assert response.type == "error"
        assert response.payload["code"] == "user_budget_error"

    @pytest.mark.asyncio
    async def test_handle_unsubscribe_session(self) -> None:
        """GIVEN unsubscribe with session_id WHEN handle_message THEN unsubscribes."""
        from mcp_server_langgraph.websocket.handlers.cost_tracking import (
            CostTrackingHandler,
        )
        from mcp_server_langgraph.websocket.types import MessageEnvelope, WebSocketConfig

        config = WebSocketConfig(endpoint_name="cost-tracking")
        mock_service = AsyncMock()  # noqa: async-mock-config

        with patch(RATE_LIMITER_PATCH, return_value=MagicMock()):
            handler = CostTrackingHandler(config=config, cost_service=mock_service)

        handler.subscribed_sessions = {"session-1", "session-2"}

        message = MessageEnvelope(type="unsubscribe", id="msg-1", payload={"session_id": "session-1"})
        response = await handler.handle_message(message)

        assert response is not None
        assert response.type == "unsubscribed"
        assert "session-1" not in handler.subscribed_sessions
        assert "session-2" in handler.subscribed_sessions

    @pytest.mark.asyncio
    async def test_handle_unsubscribe_user(self) -> None:
        """GIVEN unsubscribe with user_id WHEN handle_message THEN unsubscribes."""
        from mcp_server_langgraph.websocket.handlers.cost_tracking import (
            CostTrackingHandler,
        )
        from mcp_server_langgraph.websocket.types import MessageEnvelope, WebSocketConfig

        config = WebSocketConfig(endpoint_name="cost-tracking")
        mock_service = AsyncMock()  # noqa: async-mock-config

        with patch(RATE_LIMITER_PATCH, return_value=MagicMock()):
            handler = CostTrackingHandler(config=config, cost_service=mock_service)

        handler.subscribed_users = {"user-1", "user-2"}

        message = MessageEnvelope(type="unsubscribe", id="msg-1", payload={"user_id": "user-1"})
        response = await handler.handle_message(message)

        assert response is not None
        assert response.type == "unsubscribed"
        assert "user-1" not in handler.subscribed_users
        assert "user-2" in handler.subscribed_users

    @pytest.mark.asyncio
    async def test_handle_unknown_message_type(self) -> None:
        """GIVEN unknown message type WHEN handle_message called THEN returns error."""
        from mcp_server_langgraph.websocket.handlers.cost_tracking import (
            CostTrackingHandler,
        )
        from mcp_server_langgraph.websocket.types import MessageEnvelope, WebSocketConfig

        config = WebSocketConfig(endpoint_name="cost-tracking")
        mock_service = AsyncMock()  # noqa: async-mock-config

        with patch(RATE_LIMITER_PATCH, return_value=MagicMock()):
            handler = CostTrackingHandler(config=config, cost_service=mock_service)

        message = MessageEnvelope(type="invalid", id="msg-1")
        response = await handler.handle_message(message)

        assert response is not None
        assert response.type == "error"
        assert response.payload["code"] == "unknown_message_type"


@pytest.mark.xdist_group(name="websocket_cost_tracking_push")
class TestCostTrackingHandlerPush:
    """Tests for CostTrackingHandler push functionality."""

    def teardown_method(self) -> None:
        """Force GC to prevent mock accumulation in xdist workers."""
        gc.collect()

    @pytest.mark.asyncio
    async def test_push_cost_event_when_subscribed(self) -> None:
        """GIVEN subscribed WHEN push_cost_event THEN sends."""
        from mcp_server_langgraph.websocket.handlers.cost_tracking import (
            CostTrackingHandler,
        )
        from mcp_server_langgraph.websocket.types import WebSocketConfig

        config = WebSocketConfig(endpoint_name="cost-tracking")
        mock_service = AsyncMock()  # noqa: async-mock-config

        with patch(RATE_LIMITER_PATCH, return_value=MagicMock()):
            handler = CostTrackingHandler(config=config, cost_service=mock_service)

        mock_ws = AsyncMock()  # noqa: async-mock-config
        handler._websocket = mock_ws
        handler.subscribed_sessions.add("session-1")

        await handler.push_cost_event("session-1", {"cost": 0.05, "tokens": 500, "model": "gpt-4"})

        mock_ws.send_json.assert_called_once()

    @pytest.mark.asyncio
    async def test_push_cost_event_when_not_subscribed(self) -> None:
        """GIVEN not subscribed WHEN push_cost_event THEN does not send."""
        from mcp_server_langgraph.websocket.handlers.cost_tracking import (
            CostTrackingHandler,
        )
        from mcp_server_langgraph.websocket.types import WebSocketConfig

        config = WebSocketConfig(endpoint_name="cost-tracking")
        mock_service = AsyncMock()  # noqa: async-mock-config

        with patch(RATE_LIMITER_PATCH, return_value=MagicMock()):
            handler = CostTrackingHandler(config=config, cost_service=mock_service)

        mock_ws = AsyncMock()  # noqa: async-mock-config
        handler._websocket = mock_ws
        # Not subscribed

        await handler.push_cost_event("session-1", {"cost": 0.05})

        mock_ws.send_json.assert_not_called()

    @pytest.mark.asyncio
    async def test_push_budget_warning_when_subscribed(self) -> None:
        """GIVEN subscribed WHEN push_budget_warning THEN sends."""
        from mcp_server_langgraph.websocket.handlers.cost_tracking import (
            CostTrackingHandler,
        )
        from mcp_server_langgraph.websocket.types import WebSocketConfig

        config = WebSocketConfig(endpoint_name="cost-tracking")
        mock_service = AsyncMock()  # noqa: async-mock-config

        with patch(RATE_LIMITER_PATCH, return_value=MagicMock()):
            handler = CostTrackingHandler(config=config, cost_service=mock_service)

        mock_ws = AsyncMock()  # noqa: async-mock-config
        handler._websocket = mock_ws
        handler.subscribed_users.add("user-1")

        await handler.push_budget_warning("user-1", {"threshold": 0.80, "current_usage_percent": 0.85})

        mock_ws.send_json.assert_called_once()

    @pytest.mark.asyncio
    async def test_push_budget_warning_when_not_subscribed(self) -> None:
        """GIVEN not subscribed WHEN push_budget_warning THEN does not send."""
        from mcp_server_langgraph.websocket.handlers.cost_tracking import (
            CostTrackingHandler,
        )
        from mcp_server_langgraph.websocket.types import WebSocketConfig

        config = WebSocketConfig(endpoint_name="cost-tracking")
        mock_service = AsyncMock()  # noqa: async-mock-config

        with patch(RATE_LIMITER_PATCH, return_value=MagicMock()):
            handler = CostTrackingHandler(config=config, cost_service=mock_service)

        mock_ws = AsyncMock()  # noqa: async-mock-config
        handler._websocket = mock_ws
        # Not subscribed

        await handler.push_budget_warning("user-1", {"threshold": 0.80})

        mock_ws.send_json.assert_not_called()


@pytest.mark.xdist_group(name="websocket_cost_tracking_protocol")
class TestCostServiceProtocol:
    """Tests for CostServiceProtocol."""

    def teardown_method(self) -> None:
        """Force GC to prevent mock accumulation in xdist workers."""
        gc.collect()

    def test_protocol_is_runtime_checkable(self) -> None:
        """GIVEN CostServiceProtocol WHEN checking isinstance THEN works."""
        from mcp_server_langgraph.websocket.handlers.cost_tracking import (
            CostServiceProtocol,
        )

        class MockCostService:
            async def get_session_cost(self, session_id: str):
                return {}

            async def get_user_budget(self, user_id: str):
                return {}

        service = MockCostService()
        assert isinstance(service, CostServiceProtocol)
