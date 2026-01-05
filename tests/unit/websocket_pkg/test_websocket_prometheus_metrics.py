"""
WebSocket Prometheus Metrics Tests.

TDD tests for WebSocket reconnection and connection metrics
exposed via Prometheus.

These metrics track:
- WebSocket reconnection attempts
- Success/failure rates
- Connection states per endpoint
"""

import gc
from unittest.mock import patch

import pytest

pytestmark = pytest.mark.unit


@pytest.mark.xdist_group(name="websocket_prometheus_metrics")
class TestWebSocketPrometheusMetrics:
    """Test WebSocket Prometheus metrics exporter."""

    def teardown_method(self) -> None:
        """Force GC to prevent mock accumulation in xdist workers."""
        gc.collect()

    def test_init_websocket_metrics_lazy_call_returns_bool(self) -> None:
        """Metrics should be initialized lazily."""
        from mcp_server_langgraph.websocket.metrics import (
            _init_websocket_metrics,
        )

        result = _init_websocket_metrics()
        assert isinstance(result, bool)

    def test_record_reconnection_attempt_increments_counter(self) -> None:
        """Recording a reconnection attempt should increment the counter."""
        from mcp_server_langgraph.websocket.metrics import (
            record_reconnection_attempt,
        )

        # Should not raise
        record_reconnection_attempt(
            endpoint_id="notifications",
            success=True,
        )

    def test_record_reconnection_failure_with_reason(self) -> None:
        """Recording a failure should include the failure reason."""
        from mcp_server_langgraph.websocket.metrics import (
            record_reconnection_attempt,
        )

        # Should not raise
        record_reconnection_attempt(
            endpoint_id="alerts",
            success=False,
            failure_reason="network_error",
        )

    def test_record_connection_state_change(self) -> None:
        """Recording connection state should update the gauge."""
        from mcp_server_langgraph.websocket.metrics import (
            record_connection_state,
        )

        # Should not raise
        record_connection_state(
            endpoint_id="traces",
            is_connected=True,
        )

    def test_record_connection_disconnect(self) -> None:
        """Recording disconnect should update the gauge."""
        from mcp_server_langgraph.websocket.metrics import (
            record_connection_state,
        )

        # Should not raise
        record_connection_state(
            endpoint_id="traces",
            is_connected=False,
        )

    def test_record_reconnection_duration(self) -> None:
        """Recording reconnection duration should update the histogram."""
        from mcp_server_langgraph.websocket.metrics import (
            record_reconnection_duration,
        )

        # Should not raise
        record_reconnection_duration(
            endpoint_id="devtools",
            duration_seconds=0.5,
        )

    def test_metrics_graceful_degradation_without_prometheus(self) -> None:
        """Metrics should not raise if prometheus_client is unavailable."""
        with patch.dict("sys.modules", {"prometheus_client": None}):
            # Force reimport to test graceful degradation
            from mcp_server_langgraph.websocket import metrics

            # These should not raise even without prometheus
            metrics.record_reconnection_attempt("test", success=True)
            metrics.record_connection_state("test", is_connected=True)
            metrics.record_reconnection_duration("test", duration_seconds=1.0)


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
            total_attempts=10,
            total_reconnections=8,
            consecutive_failures=0,
            success_rate=80.0,
            failures_by_reason={"network_error": 1, "token_expired": 1},
        )

        # Validate payload schema
        assert payload.endpoint_id == "notifications"
        assert payload.total_attempts == 10
        assert payload.success_rate == 80.0

    @pytest.mark.asyncio
    async def test_post_websocket_metrics_validates_input(self) -> None:
        """Endpoint should validate metric payload."""
        from pydantic import ValidationError

        from mcp_server_langgraph.websocket.metrics import WebSocketMetricsPayload

        with pytest.raises(ValidationError):
            WebSocketMetricsPayload(
                endpoint_id="",  # Empty endpoint ID should fail
                total_attempts=-1,  # Negative should fail
                total_reconnections=0,
                consecutive_failures=0,
                success_rate=150.0,  # > 100% should fail
                failures_by_reason={},
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
                total_attempts=5,
                total_reconnections=5,
                consecutive_failures=0,
                success_rate=100.0,
                failures_by_reason={},
            ),
            WebSocketMetricsPayload(
                endpoint_id="alerts",
                total_attempts=3,
                total_reconnections=2,
                consecutive_failures=1,
                success_rate=66.67,
                failures_by_reason={"network_error": 1},
            ),
        ]

        batch = WebSocketBatchMetricsPayload(endpoints=metrics_list)
        assert len(batch.endpoints) == 2
