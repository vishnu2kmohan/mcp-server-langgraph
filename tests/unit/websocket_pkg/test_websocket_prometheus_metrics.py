"""
WebSocket Metrics Tests.

TDD tests for WebSocket connection and message metrics
collected via WebSocketMetrics class with OpenTelemetry integration.

These metrics track:
- WebSocket connections and disconnections
- Message send/receive counts
- Errors, rate limiting, and connection rejections
- Message processing latency
"""

import gc

import pytest

pytestmark = pytest.mark.unit


@pytest.mark.xdist_group(name="websocket_prometheus_metrics")
class TestWebSocketMetrics:
    """Test WebSocket metrics collection."""

    def teardown_method(self) -> None:
        """Force GC to prevent mock accumulation in xdist workers."""
        gc.collect()

    def test_websocket_metrics_initialization(self) -> None:
        """WebSocketMetrics should initialize with zero counters."""
        from mcp_server_langgraph.websocket.metrics import WebSocketMetrics

        metrics = WebSocketMetrics(endpoint_name="notifications")
        assert metrics.active_connections == 0
        assert metrics.total_connections == 0
        assert metrics.messages_received == 0
        assert metrics.messages_sent == 0
        assert metrics.errors == 0

    def test_record_connection_increments_counters(self) -> None:
        """Recording a connection should increment active and total counters."""
        from mcp_server_langgraph.websocket.metrics import WebSocketMetrics

        metrics = WebSocketMetrics(endpoint_name="notifications")
        metrics.record_connection(user_id="user-123")

        assert metrics.active_connections == 1
        assert metrics.total_connections == 1

    def test_record_disconnect_decrements_active(self) -> None:
        """Recording a disconnect should decrement active connections."""
        from mcp_server_langgraph.websocket.metrics import WebSocketMetrics

        metrics = WebSocketMetrics(endpoint_name="notifications")
        metrics.record_connection()
        metrics.record_disconnect()

        assert metrics.active_connections == 0
        assert metrics.total_connections == 1

    def test_record_disconnect_does_not_go_negative(self) -> None:
        """Active connections should not go below zero."""
        from mcp_server_langgraph.websocket.metrics import WebSocketMetrics

        metrics = WebSocketMetrics(endpoint_name="notifications")
        metrics.record_disconnect()

        assert metrics.active_connections == 0

    def test_record_message_received(self) -> None:
        """Recording a received message should increment the counter."""
        from mcp_server_langgraph.websocket.metrics import WebSocketMetrics

        metrics = WebSocketMetrics(endpoint_name="notifications")
        metrics.record_message_received(message_type="ping")

        assert metrics.messages_received == 1

    def test_record_message_sent(self) -> None:
        """Recording a sent message should increment the counter."""
        from mcp_server_langgraph.websocket.metrics import WebSocketMetrics

        metrics = WebSocketMetrics(endpoint_name="notifications")
        metrics.record_message_sent(message_type="pong")

        assert metrics.messages_sent == 1

    def test_record_error_increments_error_counter(self) -> None:
        """Recording an error should increment the error counter."""
        from mcp_server_langgraph.websocket.metrics import WebSocketMetrics

        metrics = WebSocketMetrics(endpoint_name="notifications")
        metrics.record_error(error_type="network_error")

        assert metrics.errors == 1

    def test_record_rate_limit_exceeded(self) -> None:
        """Recording rate limit exceeded should increment the counter."""
        from mcp_server_langgraph.websocket.metrics import WebSocketMetrics

        metrics = WebSocketMetrics(endpoint_name="notifications")
        metrics.record_rate_limit_exceeded(user_id="user-123")

        assert metrics.rate_limit_exceeded == 1

    def test_record_connection_rejected(self) -> None:
        """Recording a rejected connection should increment the counter."""
        from mcp_server_langgraph.websocket.metrics import WebSocketMetrics

        metrics = WebSocketMetrics(endpoint_name="notifications")
        metrics.record_connection_rejected(reason="auth_failed")

        assert metrics.connections_rejected == 1

    def test_record_token_expired(self) -> None:
        """Recording a token expiration should increment the counter."""
        from mcp_server_langgraph.websocket.metrics import WebSocketMetrics

        metrics = WebSocketMetrics(endpoint_name="notifications")
        metrics.record_token_expired(user_id="user-123")

        assert metrics.token_expirations == 1

    def test_record_latency_updates_histogram(self) -> None:
        """Recording latency should update the histogram."""
        from mcp_server_langgraph.websocket.metrics import WebSocketMetrics

        metrics = WebSocketMetrics(endpoint_name="notifications")
        metrics.record_latency(latency_ms=50.0)

        assert metrics.average_latency == 50.0

    def test_record_message_latency_converts_seconds_to_ms(self) -> None:
        """record_message_latency should convert seconds to milliseconds."""
        from mcp_server_langgraph.websocket.metrics import WebSocketMetrics

        metrics = WebSocketMetrics(endpoint_name="devtools")
        metrics.record_message_latency(message_type="request", latency_seconds=0.5)

        assert metrics.average_latency == 500.0

    def test_get_stats_returns_all_metrics(self) -> None:
        """get_stats should return a dictionary with all metric values."""
        from mcp_server_langgraph.websocket.metrics import WebSocketMetrics

        metrics = WebSocketMetrics(endpoint_name="traces")
        metrics.record_connection()
        metrics.record_message_received()

        stats = metrics.get_stats()
        assert stats["endpoint_name"] == "traces"
        assert stats["active_connections"] == 1
        assert stats["total_connections"] == 1
        assert stats["messages_received"] == 1

    def test_reset_clears_all_metrics(self) -> None:
        """reset should set all counters back to zero."""
        from mcp_server_langgraph.websocket.metrics import WebSocketMetrics

        metrics = WebSocketMetrics(endpoint_name="traces")
        metrics.record_connection()
        metrics.record_error()
        metrics.reset()

        assert metrics.active_connections == 0
        assert metrics.total_connections == 0
        assert metrics.errors == 0


@pytest.mark.xdist_group(name="websocket_prometheus_metrics")
class TestWebSocketMetricsAPI:
    """Test REST API endpoint for receiving frontend WebSocket metrics."""

    def teardown_method(self) -> None:
        """Force GC to prevent mock accumulation in xdist workers."""
        gc.collect()

    @pytest.mark.asyncio
    async def test_post_websocket_metrics_endpoint_exists(self) -> None:
        """POST /api/v1/websocket/metrics should accept frontend metrics."""
        from mcp_server_langgraph.websocket.metrics import WebSocketMetricsPayload

        payload = WebSocketMetricsPayload(
            endpoint_id="notifications",
            reconnect_count=8,
            total_connect_time_ms=1200.0,
            last_disconnect_reason="network_error",
            error_count=2,
            messages_sent=50,
            messages_received=45,
        )

        # Validate payload schema
        assert payload.endpoint_id == "notifications"
        assert payload.reconnect_count == 8
        assert payload.messages_sent == 50

    @pytest.mark.asyncio
    async def test_post_websocket_metrics_validates_input(self) -> None:
        """Endpoint should validate metric payload."""
        from pydantic import ValidationError

        from mcp_server_langgraph.websocket.metrics import WebSocketMetricsPayload

        with pytest.raises(ValidationError):
            WebSocketMetricsPayload(
                endpoint_id="",  # Empty endpoint ID should fail (min_length=1)
                reconnect_count=-1,  # Negative should fail (ge=0)
                total_connect_time_ms=0,
                error_count=0,
                messages_sent=0,
                messages_received=0,
            )

    @pytest.mark.asyncio
    async def test_batch_metrics_payload(self) -> None:
        """Batch payload should contain multiple endpoint metrics."""
        from mcp_server_langgraph.websocket.metrics import (
            WebSocketBatchMetricsPayload,
            WebSocketMetricsPayload,
        )

        metrics_list = [
            WebSocketMetricsPayload(
                endpoint_id="notifications",
                reconnect_count=5,
                total_connect_time_ms=800.0,
                error_count=0,
                messages_sent=20,
                messages_received=18,
            ),
            WebSocketMetricsPayload(
                endpoint_id="alerts",
                reconnect_count=2,
                total_connect_time_ms=400.0,
                last_disconnect_reason="network_error",
                error_count=1,
                messages_sent=10,
                messages_received=8,
            ),
        ]

        batch = WebSocketBatchMetricsPayload(endpoints=metrics_list)
        assert len(batch.endpoints) == 2
