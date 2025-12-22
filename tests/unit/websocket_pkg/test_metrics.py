"""Unit tests for WebSocket metrics collection.

Tests the WebSocketMetrics class that provides standardized metrics
collection for all WebSocket endpoints with optional OpenTelemetry integration.
"""

from __future__ import annotations

import gc
from unittest.mock import MagicMock, patch

import pytest


@pytest.mark.unit
@pytest.mark.websocket
@pytest.mark.xdist_group(name="websocket_metrics")
class TestWebSocketMetricsInitialization:
    """Test suite for WebSocketMetrics initialization."""

    def teardown_method(self) -> None:
        """Force GC to prevent mock accumulation in xdist workers."""
        gc.collect()

    def test_init_with_defaults(self) -> None:
        """Test WebSocketMetrics initialization with default values."""
        from mcp_server_langgraph.websocket.metrics import WebSocketMetrics

        metrics = WebSocketMetrics(endpoint_name="test_endpoint")

        assert metrics.endpoint_name == "test_endpoint"
        assert metrics.active_connections == 0
        assert metrics.total_connections == 0
        assert metrics.messages_received == 0
        assert metrics.messages_sent == 0
        assert metrics.errors == 0
        assert metrics.rate_limit_exceeded == 0
        assert metrics.connections_rejected == 0
        assert metrics.average_latency == 0.0
        assert metrics._otel_available is False

    def test_init_without_otel(self) -> None:
        """Test WebSocketMetrics initialization without OpenTelemetry."""
        from mcp_server_langgraph.websocket.metrics import WebSocketMetrics

        metrics = WebSocketMetrics(endpoint_name="notifications", enable_otel=False)

        assert metrics._otel_available is False
        assert metrics._otel_meter is None

    def test_init_with_otel_enabled(self) -> None:
        """Test WebSocketMetrics initialization with OpenTelemetry enabled."""
        from mcp_server_langgraph.websocket.metrics import WebSocketMetrics

        # OpenTelemetry should be available in test environment
        metrics = WebSocketMetrics(endpoint_name="alerts", enable_otel=True)

        assert metrics._otel_available is True
        assert metrics._otel_meter is not None


@pytest.mark.unit
@pytest.mark.websocket
@pytest.mark.xdist_group(name="websocket_metrics")
class TestWebSocketMetricsRecording:
    """Test suite for WebSocketMetrics recording methods."""

    def teardown_method(self) -> None:
        """Force GC to prevent mock accumulation in xdist workers."""
        gc.collect()

    def test_record_connection(self) -> None:
        """Test recording a new connection."""
        from mcp_server_langgraph.websocket.metrics import WebSocketMetrics

        metrics = WebSocketMetrics(endpoint_name="test")

        metrics.record_connection(user_id="user-1")

        assert metrics.active_connections == 1
        assert metrics.total_connections == 1

    def test_record_multiple_connections(self) -> None:
        """Test recording multiple connections."""
        from mcp_server_langgraph.websocket.metrics import WebSocketMetrics

        metrics = WebSocketMetrics(endpoint_name="test")

        metrics.record_connection(user_id="user-1")
        metrics.record_connection(user_id="user-2")
        metrics.record_connection(user_id="user-3")

        assert metrics.active_connections == 3
        assert metrics.total_connections == 3

    def test_record_disconnect(self) -> None:
        """Test recording a disconnection."""
        from mcp_server_langgraph.websocket.metrics import WebSocketMetrics

        metrics = WebSocketMetrics(endpoint_name="test")
        metrics.record_connection()
        metrics.record_connection()

        metrics.record_disconnect()

        assert metrics.active_connections == 1
        assert metrics.total_connections == 2

    def test_record_disconnect_never_goes_negative(self) -> None:
        """Test that active connections never goes negative."""
        from mcp_server_langgraph.websocket.metrics import WebSocketMetrics

        metrics = WebSocketMetrics(endpoint_name="test")

        # Disconnect without any connections
        metrics.record_disconnect()
        metrics.record_disconnect()

        assert metrics.active_connections == 0

    def test_record_message_received(self) -> None:
        """Test recording received messages."""
        from mcp_server_langgraph.websocket.metrics import WebSocketMetrics

        metrics = WebSocketMetrics(endpoint_name="test")

        metrics.record_message_received(message_type="ping", user_id="user-1")
        metrics.record_message_received(message_type="subscribe")

        assert metrics.messages_received == 2

    def test_record_message_sent(self) -> None:
        """Test recording sent messages."""
        from mcp_server_langgraph.websocket.metrics import WebSocketMetrics

        metrics = WebSocketMetrics(endpoint_name="test")

        metrics.record_message_sent(message_type="pong", user_id="user-1")
        metrics.record_message_sent(message_type="data")
        metrics.record_message_sent()

        assert metrics.messages_sent == 3

    def test_record_error(self) -> None:
        """Test recording errors."""
        from mcp_server_langgraph.websocket.metrics import WebSocketMetrics

        metrics = WebSocketMetrics(endpoint_name="test")

        metrics.record_error(error_type="timeout", user_id="user-1")
        metrics.record_error(error_type="invalid_message")

        assert metrics.errors == 2

    def test_record_rate_limit_exceeded(self) -> None:
        """Test recording rate limit exceeded events."""
        from mcp_server_langgraph.websocket.metrics import WebSocketMetrics

        metrics = WebSocketMetrics(endpoint_name="test")

        metrics.record_rate_limit_exceeded(user_id="user-1")
        metrics.record_rate_limit_exceeded(user_id="user-2")

        assert metrics.rate_limit_exceeded == 2

    def test_record_connection_rejected(self) -> None:
        """Test recording rejected connections."""
        from mcp_server_langgraph.websocket.metrics import WebSocketMetrics

        metrics = WebSocketMetrics(endpoint_name="test")

        metrics.record_connection_rejected(reason="unauthorized", user_id="user-1")
        metrics.record_connection_rejected(reason="rate_limited")

        assert metrics.connections_rejected == 2


@pytest.mark.unit
@pytest.mark.websocket
@pytest.mark.xdist_group(name="websocket_metrics")
class TestWebSocketMetricsLatency:
    """Test suite for WebSocketMetrics latency tracking."""

    def teardown_method(self) -> None:
        """Force GC to prevent mock accumulation in xdist workers."""
        gc.collect()

    def test_record_latency(self) -> None:
        """Test recording message latency."""
        from mcp_server_langgraph.websocket.metrics import WebSocketMetrics

        metrics = WebSocketMetrics(endpoint_name="test")

        metrics.record_latency(latency_ms=10.5, message_type="data")
        metrics.record_latency(latency_ms=20.5)

        assert metrics.average_latency == 15.5

    def test_record_message_latency_from_seconds(self) -> None:
        """Test recording latency from seconds."""
        from mcp_server_langgraph.websocket.metrics import WebSocketMetrics

        metrics = WebSocketMetrics(endpoint_name="test")

        metrics.record_message_latency(message_type="data", latency_seconds=0.1)
        metrics.record_message_latency(latency_seconds=0.2)

        assert metrics.average_latency == 150.0  # (100 + 200) / 2

    def test_average_latency_empty(self) -> None:
        """Test average latency with no data."""
        from mcp_server_langgraph.websocket.metrics import WebSocketMetrics

        metrics = WebSocketMetrics(endpoint_name="test")

        assert metrics.average_latency == 0.0

    def test_latency_buffer_limit(self) -> None:
        """Test that latency buffer is limited to 1000 entries."""
        from mcp_server_langgraph.websocket.metrics import WebSocketMetrics

        metrics = WebSocketMetrics(endpoint_name="test")

        # Add more than 1000 latencies
        for i in range(1200):
            metrics.record_latency(float(i))

        # Should only keep last 1000
        assert len(metrics._latencies) == 1000
        # First entry should be 200 (1200 - 1000)
        assert metrics._latencies[0] == 200.0


@pytest.mark.unit
@pytest.mark.websocket
@pytest.mark.xdist_group(name="websocket_metrics")
class TestWebSocketMetricsStats:
    """Test suite for WebSocketMetrics stats reporting."""

    def teardown_method(self) -> None:
        """Force GC to prevent mock accumulation in xdist workers."""
        gc.collect()

    def test_get_stats(self) -> None:
        """Test getting all metrics as a dictionary."""
        from mcp_server_langgraph.websocket.metrics import WebSocketMetrics

        metrics = WebSocketMetrics(endpoint_name="notifications")
        metrics.record_connection()
        metrics.record_message_received()
        metrics.record_message_sent()
        metrics.record_error()
        metrics.record_latency(50.0)

        stats = metrics.get_stats()

        assert stats["endpoint_name"] == "notifications"
        assert stats["active_connections"] == 1
        assert stats["total_connections"] == 1
        assert stats["messages_received"] == 1
        assert stats["messages_sent"] == 1
        assert stats["errors"] == 1
        assert stats["rate_limit_exceeded"] == 0
        assert stats["connections_rejected"] == 0
        assert stats["average_latency_ms"] == 50.0

    def test_reset(self) -> None:
        """Test resetting all metrics to zero."""
        from mcp_server_langgraph.websocket.metrics import WebSocketMetrics

        metrics = WebSocketMetrics(endpoint_name="test")
        metrics.record_connection()
        metrics.record_message_received()
        metrics.record_error()
        metrics.record_latency(100.0)

        metrics.reset()

        assert metrics.active_connections == 0
        assert metrics.total_connections == 0
        assert metrics.messages_received == 0
        assert metrics.messages_sent == 0
        assert metrics.errors == 0
        assert metrics.average_latency == 0.0


@pytest.mark.unit
@pytest.mark.websocket
@pytest.mark.xdist_group(name="websocket_metrics")
class TestWebSocketMetricsOTel:
    """Test suite for WebSocketMetrics OpenTelemetry integration."""

    def teardown_method(self) -> None:
        """Force GC to prevent mock accumulation in xdist workers."""
        gc.collect()

    def test_otel_connection_counter(self) -> None:
        """Test that OTel counter is called for connections."""
        from mcp_server_langgraph.websocket.metrics import WebSocketMetrics

        metrics = WebSocketMetrics(endpoint_name="test", enable_otel=True)

        # Mock the counter
        metrics._otel_connections_total = MagicMock()

        metrics.record_connection(user_id="user-1")

        metrics._otel_connections_total.add.assert_called_once()

    def test_otel_message_counters(self) -> None:
        """Test that OTel counters are called for messages."""
        from mcp_server_langgraph.websocket.metrics import WebSocketMetrics

        metrics = WebSocketMetrics(endpoint_name="test", enable_otel=True)

        # Mock the counters
        metrics._otel_messages_received = MagicMock()
        metrics._otel_messages_sent = MagicMock()

        metrics.record_message_received(message_type="ping")
        metrics.record_message_sent(message_type="pong")

        metrics._otel_messages_received.add.assert_called_once()
        metrics._otel_messages_sent.add.assert_called_once()

    def test_otel_error_counter(self) -> None:
        """Test that OTel counter is called for errors."""
        from mcp_server_langgraph.websocket.metrics import WebSocketMetrics

        metrics = WebSocketMetrics(endpoint_name="test", enable_otel=True)

        # Mock the counter
        metrics._otel_errors = MagicMock()

        metrics.record_error(error_type="timeout")

        metrics._otel_errors.add.assert_called_once()

    def test_otel_latency_histogram(self) -> None:
        """Test that OTel histogram is called for latency."""
        from mcp_server_langgraph.websocket.metrics import WebSocketMetrics

        metrics = WebSocketMetrics(endpoint_name="test", enable_otel=True)

        # Mock the histogram
        metrics._otel_latency = MagicMock()

        metrics.record_latency(latency_ms=25.5, message_type="data")

        metrics._otel_latency.record.assert_called_once_with(
            25.5, {"endpoint": "test", "type": "data"}
        )


@pytest.mark.unit
@pytest.mark.websocket
@pytest.mark.xdist_group(name="websocket_metrics")
class TestGetMeter:
    """Test suite for get_meter function."""

    def teardown_method(self) -> None:
        """Force GC to prevent mock accumulation in xdist workers."""
        gc.collect()

    def test_get_meter_returns_meter(self) -> None:
        """Test that get_meter returns an OpenTelemetry meter."""
        from mcp_server_langgraph.websocket.metrics import get_meter

        meter = get_meter("test_meter")

        assert meter is not None
