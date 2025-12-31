"""
Unit tests for HEART Metrics WebSocket Handler.

Tests the HeartMetricsHandler class for real-time HEART metrics streaming.
"""

from __future__ import annotations

import gc
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

pytestmark = [
    pytest.mark.unit,
    pytest.mark.websocket,
    pytest.mark.xdist_group(name="websocket_heart_metrics_handler"),
]

RATE_LIMITER_PATCH = "mcp_server_langgraph.websocket.rate_limiter.get_websocket_rate_limiter"


@pytest.mark.xdist_group(name="websocket_heart_metrics_init")
class TestHeartMetricsHandlerInit:
    """Tests for HeartMetricsHandler initialization."""

    def teardown_method(self) -> None:
        """Force GC to prevent mock accumulation in xdist workers."""
        gc.collect()

    def test_init_stores_metrics_service(self) -> None:
        """GIVEN metrics_service WHEN creating handler THEN stores service."""
        from mcp_server_langgraph.websocket.handlers.heart_metrics import (
            HeartMetricsHandler,
        )
        from mcp_server_langgraph.websocket.types import WebSocketConfig

        config = WebSocketConfig(endpoint_name="heart-metrics")
        mock_service = MagicMock()

        with patch(RATE_LIMITER_PATCH, return_value=MagicMock()):
            handler = HeartMetricsHandler(config=config, metrics_service=mock_service)

        assert handler._metrics_service is mock_service
        assert handler.time_range == "24h"
        assert handler.subscribed_dimensions == set()

    def test_init_with_metrics(self) -> None:
        """GIVEN metrics WHEN creating handler THEN stores metrics."""
        from mcp_server_langgraph.websocket.handlers.heart_metrics import (
            HeartMetricsHandler,
        )
        from mcp_server_langgraph.websocket.types import WebSocketConfig

        config = WebSocketConfig(endpoint_name="heart-metrics")
        mock_service = MagicMock()
        mock_metrics = MagicMock()

        with patch(RATE_LIMITER_PATCH, return_value=MagicMock()):
            handler = HeartMetricsHandler(config=config, metrics_service=mock_service, metrics=mock_metrics)

        assert handler._metrics is mock_metrics


@pytest.mark.xdist_group(name="websocket_heart_metrics_lifecycle")
class TestHeartMetricsHandlerLifecycle:
    """Tests for HeartMetricsHandler lifecycle hooks."""

    def teardown_method(self) -> None:
        """Force GC to prevent mock accumulation in xdist workers."""
        gc.collect()

    @pytest.mark.asyncio
    async def test_on_connect_sends_snapshot(self) -> None:
        """GIVEN user WHEN on_connect called THEN sends metrics snapshot."""
        from mcp_server_langgraph.websocket.handlers.heart_metrics import (
            HeartMetricsHandler,
        )
        from mcp_server_langgraph.websocket.types import AuthUser, WebSocketConfig

        config = WebSocketConfig(endpoint_name="heart-metrics")
        mock_service = AsyncMock()  # noqa: async-mock-config
        mock_service.get_current_snapshot.return_value = {
            "happiness": 0.85,
            "engagement": 0.72,
            "adoption": 0.65,
            "retention": 0.90,
            "task_success": 0.88,
        }

        with patch(RATE_LIMITER_PATCH, return_value=MagicMock()):
            handler = HeartMetricsHandler(config=config, metrics_service=mock_service)

        mock_ws = AsyncMock()  # noqa: async-mock-config
        handler._websocket = mock_ws
        user = AuthUser(id="user-123", username="testuser")

        await handler.on_connect(user)

        mock_service.get_current_snapshot.assert_called_once_with("24h")
        mock_ws.send_json.assert_called_once()
        sent_data = mock_ws.send_json.call_args[0][0]
        assert sent_data["type"] == "metrics_snapshot"
        assert "metrics" in sent_data

    @pytest.mark.asyncio
    async def test_on_disconnect_clears_subscriptions(self) -> None:
        """GIVEN subscriptions WHEN on_disconnect called THEN clears."""
        from mcp_server_langgraph.websocket.handlers.heart_metrics import (
            HeartMetricsHandler,
        )
        from mcp_server_langgraph.websocket.types import WebSocketConfig

        config = WebSocketConfig(endpoint_name="heart-metrics")
        mock_service = AsyncMock()  # noqa: async-mock-config

        with patch(RATE_LIMITER_PATCH, return_value=MagicMock()):
            handler = HeartMetricsHandler(config=config, metrics_service=mock_service)

        handler.subscribed_dimensions = {"happiness", "engagement"}

        await handler.on_disconnect()

        assert handler.subscribed_dimensions == set()


@pytest.mark.xdist_group(name="websocket_heart_metrics_messages")
class TestHeartMetricsHandlerMessages:
    """Tests for HeartMetricsHandler message handling."""

    def teardown_method(self) -> None:
        """Force GC to prevent mock accumulation in xdist workers."""
        gc.collect()

    @pytest.mark.asyncio
    async def test_handle_set_time_range(self) -> None:
        """GIVEN set_time_range message WHEN handle_message called THEN updates."""
        from mcp_server_langgraph.websocket.handlers.heart_metrics import (
            HeartMetricsHandler,
        )
        from mcp_server_langgraph.websocket.types import MessageEnvelope, WebSocketConfig

        config = WebSocketConfig(endpoint_name="heart-metrics")
        mock_service = AsyncMock()  # noqa: async-mock-config
        mock_service.get_current_snapshot.return_value = {"happiness": 0.85}

        with patch(RATE_LIMITER_PATCH, return_value=MagicMock()):
            handler = HeartMetricsHandler(config=config, metrics_service=mock_service)

        message = MessageEnvelope(type="set_time_range", id="msg-1", payload={"time_range": "7d"})
        response = await handler.handle_message(message)

        assert response is not None
        assert response.type == "metrics_snapshot"
        assert response.id == "msg-1"
        assert handler.time_range == "7d"
        mock_service.get_current_snapshot.assert_called_once_with("7d")

    @pytest.mark.asyncio
    async def test_handle_set_time_range_invalid(self) -> None:
        """GIVEN invalid time_range WHEN handle_message called THEN error."""
        from mcp_server_langgraph.websocket.handlers.heart_metrics import (
            HeartMetricsHandler,
        )
        from mcp_server_langgraph.websocket.types import MessageEnvelope, WebSocketConfig

        config = WebSocketConfig(endpoint_name="heart-metrics")
        mock_service = AsyncMock()  # noqa: async-mock-config

        with patch(RATE_LIMITER_PATCH, return_value=MagicMock()):
            handler = HeartMetricsHandler(config=config, metrics_service=mock_service)

        message = MessageEnvelope(type="set_time_range", id="msg-1", payload={"time_range": "invalid"})
        response = await handler.handle_message(message)

        assert response is not None
        assert response.type == "error"
        assert response.payload["code"] == "invalid_time_range"

    @pytest.mark.asyncio
    async def test_handle_set_time_range_default(self) -> None:
        """GIVEN set_time_range without time_range WHEN handle_message THEN uses default."""
        from mcp_server_langgraph.websocket.handlers.heart_metrics import (
            HeartMetricsHandler,
        )
        from mcp_server_langgraph.websocket.types import MessageEnvelope, WebSocketConfig

        config = WebSocketConfig(endpoint_name="heart-metrics")
        mock_service = AsyncMock()  # noqa: async-mock-config
        mock_service.get_current_snapshot.return_value = {"happiness": 0.85}

        with patch(RATE_LIMITER_PATCH, return_value=MagicMock()):
            handler = HeartMetricsHandler(config=config, metrics_service=mock_service)

        message = MessageEnvelope(type="set_time_range", id="msg-1", payload={})
        response = await handler.handle_message(message)

        assert response is not None
        assert response.type == "metrics_snapshot"
        assert handler.time_range == "24h"  # Default

    @pytest.mark.asyncio
    async def test_handle_subscribe_dimension(self) -> None:
        """GIVEN subscribe_dimension message WHEN handle_message called THEN subscribes."""
        from mcp_server_langgraph.websocket.handlers.heart_metrics import (
            HeartMetricsHandler,
        )
        from mcp_server_langgraph.websocket.types import MessageEnvelope, WebSocketConfig

        config = WebSocketConfig(endpoint_name="heart-metrics")
        mock_service = AsyncMock()  # noqa: async-mock-config
        mock_service.get_dimension_metrics.return_value = {
            "value": 0.85,
            "trend": "up",
            "change": 0.05,
        }

        with patch(RATE_LIMITER_PATCH, return_value=MagicMock()):
            handler = HeartMetricsHandler(config=config, metrics_service=mock_service)

        message = MessageEnvelope(type="subscribe_dimension", id="msg-1", payload={"dimension": "happiness"})
        response = await handler.handle_message(message)

        assert response is not None
        assert response.type == "dimension_update"
        assert response.id == "msg-1"
        assert "happiness" in handler.subscribed_dimensions
        mock_service.get_dimension_metrics.assert_called_once_with("happiness", "24h")

    @pytest.mark.asyncio
    async def test_handle_subscribe_dimension_missing_dimension(self) -> None:
        """GIVEN subscribe_dimension without dimension WHEN handle_message THEN error."""
        from mcp_server_langgraph.websocket.handlers.heart_metrics import (
            HeartMetricsHandler,
        )
        from mcp_server_langgraph.websocket.types import MessageEnvelope, WebSocketConfig

        config = WebSocketConfig(endpoint_name="heart-metrics")
        mock_service = AsyncMock()  # noqa: async-mock-config

        with patch(RATE_LIMITER_PATCH, return_value=MagicMock()):
            handler = HeartMetricsHandler(config=config, metrics_service=mock_service)

        message = MessageEnvelope(type="subscribe_dimension", id="msg-1", payload={})
        response = await handler.handle_message(message)

        assert response is not None
        assert response.type == "error"
        assert response.payload["code"] == "missing_dimension"

    @pytest.mark.asyncio
    async def test_handle_subscribe_dimension_invalid_dimension(self) -> None:
        """GIVEN subscribe_dimension with invalid dimension WHEN handle_message THEN error."""
        from mcp_server_langgraph.websocket.handlers.heart_metrics import (
            HeartMetricsHandler,
        )
        from mcp_server_langgraph.websocket.types import MessageEnvelope, WebSocketConfig

        config = WebSocketConfig(endpoint_name="heart-metrics")
        mock_service = AsyncMock()  # noqa: async-mock-config

        with patch(RATE_LIMITER_PATCH, return_value=MagicMock()):
            handler = HeartMetricsHandler(config=config, metrics_service=mock_service)

        message = MessageEnvelope(type="subscribe_dimension", id="msg-1", payload={"dimension": "invalid"})
        response = await handler.handle_message(message)

        assert response is not None
        assert response.type == "error"
        assert response.payload["code"] == "invalid_dimension"

    @pytest.mark.asyncio
    async def test_handle_unsubscribe_dimension(self) -> None:
        """GIVEN unsubscribe_dimension message WHEN handle_message called THEN unsubscribes."""
        from mcp_server_langgraph.websocket.handlers.heart_metrics import (
            HeartMetricsHandler,
        )
        from mcp_server_langgraph.websocket.types import MessageEnvelope, WebSocketConfig

        config = WebSocketConfig(endpoint_name="heart-metrics")
        mock_service = AsyncMock()  # noqa: async-mock-config

        with patch(RATE_LIMITER_PATCH, return_value=MagicMock()):
            handler = HeartMetricsHandler(config=config, metrics_service=mock_service)

        handler.subscribed_dimensions = {"happiness", "engagement"}

        message = MessageEnvelope(type="unsubscribe_dimension", id="msg-1", payload={"dimension": "happiness"})
        response = await handler.handle_message(message)

        assert response is not None
        assert response.type == "unsubscribed"
        assert "happiness" not in handler.subscribed_dimensions
        assert "engagement" in handler.subscribed_dimensions

    @pytest.mark.asyncio
    async def test_handle_unknown_message_type(self) -> None:
        """GIVEN unknown message type WHEN handle_message called THEN returns error."""
        from mcp_server_langgraph.websocket.handlers.heart_metrics import (
            HeartMetricsHandler,
        )
        from mcp_server_langgraph.websocket.types import MessageEnvelope, WebSocketConfig

        config = WebSocketConfig(endpoint_name="heart-metrics")
        mock_service = AsyncMock()  # noqa: async-mock-config

        with patch(RATE_LIMITER_PATCH, return_value=MagicMock()):
            handler = HeartMetricsHandler(config=config, metrics_service=mock_service)

        message = MessageEnvelope(type="invalid", id="msg-1")
        response = await handler.handle_message(message)

        assert response is not None
        assert response.type == "error"
        assert response.payload["code"] == "unknown_message_type"


@pytest.mark.xdist_group(name="websocket_heart_metrics_push")
class TestHeartMetricsHandlerPush:
    """Tests for HeartMetricsHandler push functionality."""

    def teardown_method(self) -> None:
        """Force GC to prevent mock accumulation in xdist workers."""
        gc.collect()

    @pytest.mark.asyncio
    async def test_push_dimension_update_when_subscribed(self) -> None:
        """GIVEN subscribed WHEN push_dimension_update THEN sends."""
        from mcp_server_langgraph.websocket.handlers.heart_metrics import (
            HeartMetricsHandler,
        )
        from mcp_server_langgraph.websocket.types import WebSocketConfig

        config = WebSocketConfig(endpoint_name="heart-metrics")
        mock_service = AsyncMock()  # noqa: async-mock-config

        with patch(RATE_LIMITER_PATCH, return_value=MagicMock()):
            handler = HeartMetricsHandler(config=config, metrics_service=mock_service)

        mock_ws = AsyncMock()  # noqa: async-mock-config
        handler._websocket = mock_ws
        handler.subscribed_dimensions.add("happiness")

        await handler.push_dimension_update("happiness", {"value": 0.90, "trend": "up"})

        mock_ws.send_json.assert_called_once()

    @pytest.mark.asyncio
    async def test_push_dimension_update_when_not_subscribed(self) -> None:
        """GIVEN not subscribed WHEN push_dimension_update THEN does not send."""
        from mcp_server_langgraph.websocket.handlers.heart_metrics import (
            HeartMetricsHandler,
        )
        from mcp_server_langgraph.websocket.types import WebSocketConfig

        config = WebSocketConfig(endpoint_name="heart-metrics")
        mock_service = AsyncMock()  # noqa: async-mock-config

        with patch(RATE_LIMITER_PATCH, return_value=MagicMock()):
            handler = HeartMetricsHandler(config=config, metrics_service=mock_service)

        mock_ws = AsyncMock()  # noqa: async-mock-config
        handler._websocket = mock_ws
        # Not subscribed

        await handler.push_dimension_update("happiness", {"value": 0.90})

        mock_ws.send_json.assert_not_called()

    @pytest.mark.asyncio
    async def test_push_threshold_alert(self) -> None:
        """GIVEN websocket WHEN push_threshold_alert THEN sends."""
        from mcp_server_langgraph.websocket.handlers.heart_metrics import (
            HeartMetricsHandler,
        )
        from mcp_server_langgraph.websocket.types import WebSocketConfig

        config = WebSocketConfig(endpoint_name="heart-metrics")
        mock_service = AsyncMock()  # noqa: async-mock-config

        with patch(RATE_LIMITER_PATCH, return_value=MagicMock()):
            handler = HeartMetricsHandler(config=config, metrics_service=mock_service)

        mock_ws = AsyncMock()  # noqa: async-mock-config
        handler._websocket = mock_ws

        await handler.push_threshold_alert("engagement", "low", 0.45)

        mock_ws.send_json.assert_called_once()
        sent_data = mock_ws.send_json.call_args[0][0]
        assert sent_data["type"] == "threshold_alert"
        assert sent_data["payload"]["dimension"] == "engagement"
        assert sent_data["payload"]["threshold"] == "low"
        assert sent_data["payload"]["current_value"] == 0.45

    @pytest.mark.asyncio
    async def test_push_threshold_alert_no_websocket(self) -> None:
        """GIVEN no websocket WHEN push_threshold_alert THEN does not send."""
        from mcp_server_langgraph.websocket.handlers.heart_metrics import (
            HeartMetricsHandler,
        )
        from mcp_server_langgraph.websocket.types import WebSocketConfig

        config = WebSocketConfig(endpoint_name="heart-metrics")
        mock_service = AsyncMock()  # noqa: async-mock-config

        with patch(RATE_LIMITER_PATCH, return_value=MagicMock()):
            handler = HeartMetricsHandler(config=config, metrics_service=mock_service)

        # No websocket
        await handler.push_threshold_alert("engagement", "low", 0.45)
        # Should not raise


@pytest.mark.xdist_group(name="websocket_heart_metrics_constants")
class TestHeartMetricsConstants:
    """Tests for HEART metrics constants."""

    def teardown_method(self) -> None:
        """Force GC to prevent mock accumulation in xdist workers."""
        gc.collect()

    def test_heart_dimensions_constant_contains_expected_dimensions(self) -> None:
        """GIVEN HEART_DIMENSIONS WHEN accessed THEN contains expected dimensions."""
        from mcp_server_langgraph.websocket.handlers.heart_metrics import (
            HEART_DIMENSIONS,
        )

        expected = {"happiness", "engagement", "adoption", "retention", "task_success"}
        assert expected == HEART_DIMENSIONS

    def test_valid_time_ranges(self) -> None:
        """GIVEN VALID_TIME_RANGES WHEN accessed THEN contains expected ranges."""
        from mcp_server_langgraph.websocket.handlers.heart_metrics import (
            VALID_TIME_RANGES,
        )

        expected = {"1h", "6h", "24h", "7d", "30d", "90d"}
        assert expected == VALID_TIME_RANGES


@pytest.mark.xdist_group(name="websocket_heart_metrics_protocol")
class TestHeartMetricsServiceProtocol:
    """Tests for HeartMetricsServiceProtocol."""

    def teardown_method(self) -> None:
        """Force GC to prevent mock accumulation in xdist workers."""
        gc.collect()

    def test_protocol_is_runtime_checkable(self) -> None:
        """GIVEN HeartMetricsServiceProtocol WHEN checking isinstance THEN works."""
        from mcp_server_langgraph.websocket.handlers.heart_metrics import (
            HeartMetricsServiceProtocol,
        )

        class MockHeartMetricsService:
            async def get_current_snapshot(self, time_range: str = "24h"):
                return {}

            async def get_dimension_metrics(self, dimension: str, time_range: str = "24h"):
                return {}

        service = MockHeartMetricsService()
        assert isinstance(service, HeartMetricsServiceProtocol)
