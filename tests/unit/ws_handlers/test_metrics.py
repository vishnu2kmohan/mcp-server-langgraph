"""
WebSocketMetrics Unit Tests.

TDD tests for WebSocket metrics collection and reporting.
"""

from __future__ import annotations

import gc
from unittest.mock import MagicMock, patch

import pytest

pytestmark = [pytest.mark.unit, pytest.mark.websocket]


@pytest.mark.xdist_group(name="websocket_metrics")
class TestWebSocketMetricsRecording:
    """Test WebSocketMetrics recording functionality."""

    def teardown_method(self) -> None:
        """Force GC to prevent mock accumulation in xdist workers."""
        gc.collect()

    def test_record_connection_increments_active(self) -> None:
        """
        GIVEN a WebSocketMetrics instance
        WHEN record_connection() is called
        THEN active_connections should increment.
        """
        from mcp_server_langgraph.websocket.metrics import WebSocketMetrics

        metrics = WebSocketMetrics(endpoint_name="test")
        assert metrics.active_connections == 0

        metrics.record_connection()
        assert metrics.active_connections == 1

        metrics.record_connection()
        assert metrics.active_connections == 2

    def test_record_disconnect_decrements_active(self) -> None:
        """
        GIVEN a WebSocketMetrics with active connections
        WHEN record_disconnect() is called
        THEN active_connections should decrement.
        """
        from mcp_server_langgraph.websocket.metrics import WebSocketMetrics

        metrics = WebSocketMetrics(endpoint_name="test")
        metrics.record_connection()
        metrics.record_connection()
        assert metrics.active_connections == 2

        metrics.record_disconnect()
        assert metrics.active_connections == 1

    def test_record_disconnect_does_not_go_negative(self) -> None:
        """
        GIVEN a WebSocketMetrics with no active connections
        WHEN record_disconnect() is called
        THEN active_connections should remain 0.
        """
        from mcp_server_langgraph.websocket.metrics import WebSocketMetrics

        metrics = WebSocketMetrics(endpoint_name="test")
        metrics.record_disconnect()
        assert metrics.active_connections == 0

    def test_record_message_received(self) -> None:
        """
        GIVEN a WebSocketMetrics instance
        WHEN record_message_received() is called
        THEN messages_received counter should increment.
        """
        from mcp_server_langgraph.websocket.metrics import WebSocketMetrics

        metrics = WebSocketMetrics(endpoint_name="test")
        assert metrics.messages_received == 0

        metrics.record_message_received(message_type="ping")
        assert metrics.messages_received == 1

    def test_record_message_sent(self) -> None:
        """
        GIVEN a WebSocketMetrics instance
        WHEN record_message_sent() is called
        THEN messages_sent counter should increment.
        """
        from mcp_server_langgraph.websocket.metrics import WebSocketMetrics

        metrics = WebSocketMetrics(endpoint_name="test")
        assert metrics.messages_sent == 0

        metrics.record_message_sent(message_type="pong")
        assert metrics.messages_sent == 1

    def test_record_error(self) -> None:
        """
        GIVEN a WebSocketMetrics instance
        WHEN record_error() is called
        THEN errors counter should increment.
        """
        from mcp_server_langgraph.websocket.metrics import WebSocketMetrics

        metrics = WebSocketMetrics(endpoint_name="test")
        assert metrics.errors == 0

        metrics.record_error(error_type="protocol_error")
        assert metrics.errors == 1


@pytest.mark.xdist_group(name="websocket_metrics")
class TestWebSocketMetricsRateLimiting:
    """Test WebSocketMetrics rate limiting tracking."""

    def teardown_method(self) -> None:
        """Force GC to prevent mock accumulation in xdist workers."""
        gc.collect()

    def test_record_rate_limit_exceeded(self) -> None:
        """
        GIVEN a WebSocketMetrics instance
        WHEN record_rate_limit_exceeded() is called
        THEN rate_limit_exceeded counter should increment.
        """
        from mcp_server_langgraph.websocket.metrics import WebSocketMetrics

        metrics = WebSocketMetrics(endpoint_name="test")
        assert metrics.rate_limit_exceeded == 0

        metrics.record_rate_limit_exceeded(user_id="user-123")
        assert metrics.rate_limit_exceeded == 1

    def test_record_connection_rejected(self) -> None:
        """
        GIVEN a WebSocketMetrics instance
        WHEN record_connection_rejected() is called
        THEN connections_rejected counter should increment.
        """
        from mcp_server_langgraph.websocket.metrics import WebSocketMetrics

        metrics = WebSocketMetrics(endpoint_name="test")
        assert metrics.connections_rejected == 0

        metrics.record_connection_rejected(reason="auth_failed")
        assert metrics.connections_rejected == 1


@pytest.mark.xdist_group(name="websocket_metrics")
class TestWebSocketMetricsLatency:
    """Test WebSocketMetrics latency tracking."""

    def teardown_method(self) -> None:
        """Force GC to prevent mock accumulation in xdist workers."""
        gc.collect()

    def test_record_latency(self) -> None:
        """
        GIVEN a WebSocketMetrics instance
        WHEN record_latency() is called with a latency value
        THEN the latency should be recorded.
        """
        from mcp_server_langgraph.websocket.metrics import WebSocketMetrics

        metrics = WebSocketMetrics(endpoint_name="test")

        # Record some latencies
        metrics.record_latency(10.5, message_type="request")
        metrics.record_latency(20.0, message_type="request")
        metrics.record_latency(15.0, message_type="request")

        # Check that latencies are being tracked
        assert len(metrics._latencies) == 3
        assert metrics.average_latency == pytest.approx(15.17, rel=0.1)


@pytest.mark.xdist_group(name="websocket_metrics")
class TestWebSocketMetricsConfiguration:
    """Test WebSocketMetrics configuration."""

    def teardown_method(self) -> None:
        """Force GC to prevent mock accumulation in xdist workers."""
        gc.collect()

    def test_endpoint_name_is_set(self) -> None:
        """
        GIVEN an endpoint name
        WHEN WebSocketMetrics is created
        THEN the endpoint_name should be stored.
        """
        from mcp_server_langgraph.websocket.metrics import WebSocketMetrics

        metrics = WebSocketMetrics(endpoint_name="notifications")
        assert metrics.endpoint_name == "notifications"

    def test_get_stats_returns_all_metrics(self) -> None:
        """
        GIVEN a WebSocketMetrics with various recordings
        WHEN get_stats() is called
        THEN a dictionary with all metrics should be returned.
        """
        from mcp_server_langgraph.websocket.metrics import WebSocketMetrics

        metrics = WebSocketMetrics(endpoint_name="test")
        metrics.record_connection()
        metrics.record_message_received(message_type="ping")
        metrics.record_message_sent(message_type="pong")

        stats = metrics.get_stats()

        assert stats["endpoint_name"] == "test"
        assert stats["active_connections"] == 1
        assert stats["messages_received"] == 1
        assert stats["messages_sent"] == 1


@pytest.mark.xdist_group(name="websocket_metrics")
class TestWebSocketMetricsOpenTelemetry:
    """Test WebSocketMetrics OpenTelemetry integration."""

    def teardown_method(self) -> None:
        """Force GC to prevent mock accumulation in xdist workers."""
        gc.collect()

    def test_otel_meter_created_when_available(self) -> None:
        """
        GIVEN OpenTelemetry is available
        WHEN WebSocketMetrics is created
        THEN OTel meter should be used.
        """
        from mcp_server_langgraph.websocket.metrics import WebSocketMetrics

        with patch("mcp_server_langgraph.websocket.metrics.get_meter") as mock_get_meter:
            mock_meter = MagicMock()
            mock_get_meter.return_value = mock_meter

            metrics = WebSocketMetrics(endpoint_name="test", enable_otel=True)

            mock_get_meter.assert_called_once()

    def test_fallback_when_otel_not_available(self) -> None:
        """
        GIVEN OpenTelemetry is not available
        WHEN WebSocketMetrics is created
        THEN fallback metrics should be used.
        """
        from mcp_server_langgraph.websocket.metrics import WebSocketMetrics

        with patch(
            "mcp_server_langgraph.websocket.metrics.get_meter",
            side_effect=ImportError("No OTel"),
        ):
            metrics = WebSocketMetrics(endpoint_name="test", enable_otel=True)

            # Should still work with fallback
            metrics.record_connection()
            assert metrics.active_connections == 1
