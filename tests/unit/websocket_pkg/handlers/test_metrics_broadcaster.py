"""
Tests for MetricsBroadcaster.

TDD: These tests define the expected behavior for real-time session-scoped
metrics streaming to the DevTools Metrics tab.

The MetricsBroadcaster solves the gap where:
- Console logs stream in real-time via DevToolsBroadcaster
- Traces stream in real-time via TraceBroadcaster
- BUT metrics are polled from Mimir via API (not real-time)

This broadcaster enables:
- Session-scoped metric updates pushed via WebSocket
- Real-time visibility into http_requests_total, llm_tokens_total, etc.
- Sparkline data updates without polling
"""

from __future__ import annotations

import gc
from typing import Any
from unittest.mock import AsyncMock, MagicMock

import pytest

# Module-level markers
pytestmark = [
    pytest.mark.unit,
    pytest.mark.observability,
    pytest.mark.websocket,
    pytest.mark.xdist_group(name="metrics_broadcaster"),
]


def teardown_module() -> None:
    """Force GC to prevent mock accumulation in xdist workers."""
    gc.collect()


class TestMetricsBroadcasterSubscription:
    """
    Tests for MetricsBroadcaster subscription management.

    Similar to DevToolsBroadcaster, this manages WebSocket subscriptions
    and broadcasts metric updates to subscribed clients.
    """

    def teardown_method(self) -> None:
        """Force GC to prevent mock accumulation in xdist workers."""
        gc.collect()

    @pytest.mark.asyncio
    async def test_subscribe_adds_websocket_to_subscribers(self) -> None:
        """
        GIVEN a MetricsBroadcaster
        WHEN subscribe is called with a websocket
        THEN the websocket should be added to subscribers.
        """
        from mcp_server_langgraph.websocket.handlers.metrics_broadcaster import (
            MetricsBroadcaster,
        )

        broadcaster = MetricsBroadcaster()
        mock_websocket = MagicMock()

        await broadcaster.subscribe(mock_websocket, user_id="user-123")

        assert broadcaster.subscriber_count == 1

    @pytest.mark.asyncio
    async def test_subscribe_with_session_id_filter(self) -> None:
        """
        GIVEN a MetricsBroadcaster
        WHEN subscribe is called with session_id
        THEN the subscription should be scoped to that session.
        """
        from mcp_server_langgraph.websocket.handlers.metrics_broadcaster import (
            MetricsBroadcaster,
        )

        broadcaster = MetricsBroadcaster()
        mock_websocket = MagicMock()

        await broadcaster.subscribe(
            mock_websocket,
            user_id="user-123",
            session_id="session-abc",
        )

        assert broadcaster.subscriber_count == 1
        # Internal check that session filter is set
        assert broadcaster.get_session_id_for_subscriber(mock_websocket) == "session-abc"

    @pytest.mark.asyncio
    async def test_unsubscribe_removes_websocket(self) -> None:
        """
        GIVEN a MetricsBroadcaster with a subscribed websocket
        WHEN unsubscribe is called
        THEN the websocket should be removed from subscribers.
        """
        from mcp_server_langgraph.websocket.handlers.metrics_broadcaster import (
            MetricsBroadcaster,
        )

        broadcaster = MetricsBroadcaster()
        mock_websocket = MagicMock()

        await broadcaster.subscribe(mock_websocket, user_id="user-123")
        assert broadcaster.subscriber_count == 1

        await broadcaster.unsubscribe(mock_websocket)
        assert broadcaster.subscriber_count == 0


class TestMetricsBroadcasterBroadcasting:
    """
    Tests for MetricsBroadcaster broadcasting functionality.
    """

    def teardown_method(self) -> None:
        """Force GC to prevent mock accumulation in xdist workers."""
        gc.collect()

    @pytest.mark.asyncio
    async def test_broadcast_metric_sends_to_all_subscribers(self) -> None:
        """
        GIVEN a MetricsBroadcaster with multiple subscribers
        WHEN broadcast_metric is called
        THEN all subscribers should receive the metric.
        """
        from mcp_server_langgraph.websocket.handlers.metrics_broadcaster import (
            MetricsBroadcaster,
        )

        broadcaster = MetricsBroadcaster()

        mock_ws1 = MagicMock()
        mock_ws1.send_json = AsyncMock()
        mock_ws2 = MagicMock()
        mock_ws2.send_json = AsyncMock()

        await broadcaster.subscribe(mock_ws1, user_id="user-1")
        await broadcaster.subscribe(mock_ws2, user_id="user-2")

        await broadcaster.broadcast_metric(
            name="http_requests_total",
            value=42,
            labels={"method": "GET", "path": "/api/chat"},
        )

        mock_ws1.send_json.assert_called_once()
        mock_ws2.send_json.assert_called_once()

        # Check message format
        call_args = mock_ws1.send_json.call_args[0][0]
        assert call_args["type"] == "metric"
        assert call_args["payload"]["name"] == "http_requests_total"
        assert call_args["payload"]["value"] == 42

    @pytest.mark.asyncio
    async def test_broadcast_metric_filters_by_session_id(self) -> None:
        """
        GIVEN subscribers with different session_id filters
        WHEN broadcast_metric is called with session_id
        THEN only matching subscribers should receive it.
        """
        from mcp_server_langgraph.websocket.handlers.metrics_broadcaster import (
            MetricsBroadcaster,
        )

        broadcaster = MetricsBroadcaster()

        mock_ws1 = MagicMock()
        mock_ws1.send_json = AsyncMock()
        mock_ws2 = MagicMock()
        mock_ws2.send_json = AsyncMock()

        await broadcaster.subscribe(mock_ws1, user_id="user-1", session_id="session-A")
        await broadcaster.subscribe(mock_ws2, user_id="user-2", session_id="session-B")

        await broadcaster.broadcast_metric(
            name="llm_tokens_total",
            value=100,
            session_id="session-A",
        )

        # Only ws1 (session-A) should receive it
        mock_ws1.send_json.assert_called_once()
        mock_ws2.send_json.assert_not_called()

    @pytest.mark.asyncio
    async def test_broadcast_removes_failed_subscribers(self) -> None:
        """
        GIVEN a subscriber that raises on send
        WHEN broadcast_metric is called
        THEN the failed subscriber should be removed.
        """
        from mcp_server_langgraph.websocket.handlers.metrics_broadcaster import (
            MetricsBroadcaster,
        )

        broadcaster = MetricsBroadcaster()

        mock_ws_good = MagicMock()
        mock_ws_good.send_json = AsyncMock()

        mock_ws_bad = MagicMock()
        mock_ws_bad.send_json = AsyncMock(side_effect=Exception("Connection closed"))

        await broadcaster.subscribe(mock_ws_good, user_id="user-1")
        await broadcaster.subscribe(mock_ws_bad, user_id="user-2")
        assert broadcaster.subscriber_count == 2

        await broadcaster.broadcast_metric(name="test_metric", value=1)

        # Bad subscriber should be removed
        assert broadcaster.subscriber_count == 1


class TestMetricsBroadcasterMetricTypes:
    """
    Tests for different metric types the broadcaster handles.
    """

    def teardown_method(self) -> None:
        """Force GC to prevent mock accumulation in xdist workers."""
        gc.collect()

    @pytest.mark.asyncio
    async def test_broadcast_counter_metric(self) -> None:
        """
        GIVEN a MetricsBroadcaster
        WHEN broadcasting a counter metric
        THEN message should include counter type metadata.
        """
        from mcp_server_langgraph.websocket.handlers.metrics_broadcaster import (
            MetricsBroadcaster,
            MetricType,
        )

        broadcaster = MetricsBroadcaster()
        mock_ws = MagicMock()
        mock_ws.send_json = AsyncMock()

        await broadcaster.subscribe(mock_ws, user_id="user-1")

        await broadcaster.broadcast_metric(
            name="http_requests_total",
            value=100,
            metric_type=MetricType.COUNTER,
        )

        call_args = mock_ws.send_json.call_args[0][0]
        assert call_args["payload"]["metric_type"] == "counter"

    @pytest.mark.asyncio
    async def test_broadcast_gauge_metric(self) -> None:
        """
        GIVEN a MetricsBroadcaster
        WHEN broadcasting a gauge metric
        THEN message should include gauge type metadata.
        """
        from mcp_server_langgraph.websocket.handlers.metrics_broadcaster import (
            MetricsBroadcaster,
            MetricType,
        )

        broadcaster = MetricsBroadcaster()
        mock_ws = MagicMock()
        mock_ws.send_json = AsyncMock()

        await broadcaster.subscribe(mock_ws, user_id="user-1")

        await broadcaster.broadcast_metric(
            name="agent_active_sessions",
            value=5,
            metric_type=MetricType.GAUGE,
        )

        call_args = mock_ws.send_json.call_args[0][0]
        assert call_args["payload"]["metric_type"] == "gauge"

    @pytest.mark.asyncio
    async def test_broadcast_histogram_metric(self) -> None:
        """
        GIVEN a MetricsBroadcaster
        WHEN broadcasting a histogram metric
        THEN message should include histogram data.
        """
        from mcp_server_langgraph.websocket.handlers.metrics_broadcaster import (
            MetricsBroadcaster,
            MetricType,
        )

        broadcaster = MetricsBroadcaster()
        mock_ws = MagicMock()
        mock_ws.send_json = AsyncMock()

        await broadcaster.subscribe(mock_ws, user_id="user-1")

        await broadcaster.broadcast_metric(
            name="http_request_duration_seconds",
            value=0.15,
            metric_type=MetricType.HISTOGRAM,
            histogram_buckets={"0.1": 5, "0.5": 8, "1.0": 10},
        )

        call_args = mock_ws.send_json.call_args[0][0]
        assert call_args["payload"]["metric_type"] == "histogram"
        assert "histogram_buckets" in call_args["payload"]


class TestMetricsBroadcasterSparklineData:
    """
    Tests for sparkline data aggregation.

    The MetricsTab displays sparkline visualizations for each metric.
    The broadcaster should maintain recent values for sparkline rendering.
    """

    def teardown_method(self) -> None:
        """Force GC to prevent mock accumulation in xdist workers."""
        gc.collect()

    @pytest.mark.asyncio
    async def test_broadcast_includes_sparkline_history(self) -> None:
        """
        GIVEN a MetricsBroadcaster with historical metric values
        WHEN broadcast_metric is called
        THEN message should include sparkline data points.
        """
        from mcp_server_langgraph.websocket.handlers.metrics_broadcaster import (
            MetricsBroadcaster,
        )

        broadcaster = MetricsBroadcaster()
        mock_ws = MagicMock()
        mock_ws.send_json = AsyncMock()

        await broadcaster.subscribe(mock_ws, user_id="user-1")

        # Simulate multiple metric updates to build sparkline
        for i in range(5):
            await broadcaster.broadcast_metric(
                name="http_requests_total",
                value=i * 10,
            )

        # Last call should include sparkline
        call_args = mock_ws.send_json.call_args[0][0]
        sparkline = call_args["payload"].get("sparkline", [])
        assert len(sparkline) == 5
        assert sparkline == [0, 10, 20, 30, 40]

    @pytest.mark.asyncio
    async def test_sparkline_respects_max_points(self) -> None:
        """
        GIVEN a MetricsBroadcaster with many historical values
        WHEN broadcast_metric is called
        THEN sparkline should be limited to max_sparkline_points.
        """
        from mcp_server_langgraph.websocket.handlers.metrics_broadcaster import (
            MetricsBroadcaster,
        )

        broadcaster = MetricsBroadcaster(max_sparkline_points=10)
        mock_ws = MagicMock()
        mock_ws.send_json = AsyncMock()

        await broadcaster.subscribe(mock_ws, user_id="user-1")

        # Send more than max points
        for i in range(20):
            await broadcaster.broadcast_metric(
                name="test_metric",
                value=i,
            )

        # Should only keep last 10
        call_args = mock_ws.send_json.call_args[0][0]
        sparkline = call_args["payload"].get("sparkline", [])
        assert len(sparkline) == 10
        assert sparkline == list(range(10, 20))


class TestMetricsBroadcasterSnapshot:
    """
    Tests for metrics snapshot functionality.

    On reconnect, clients need a snapshot of current metric values.
    """

    def teardown_method(self) -> None:
        """Force GC to prevent mock accumulation in xdist workers."""
        gc.collect()

    @pytest.mark.asyncio
    async def test_get_metrics_snapshot(self) -> None:
        """
        GIVEN a MetricsBroadcaster with accumulated metrics
        WHEN get_metrics_snapshot is called
        THEN it should return all current metric values.
        """
        from mcp_server_langgraph.websocket.handlers.metrics_broadcaster import (
            MetricsBroadcaster,
        )

        broadcaster = MetricsBroadcaster()
        mock_ws = MagicMock()
        mock_ws.send_json = AsyncMock()
        await broadcaster.subscribe(mock_ws, user_id="user-1")

        # Accumulate some metrics
        await broadcaster.broadcast_metric(name="http_requests_total", value=100)
        await broadcaster.broadcast_metric(name="llm_tokens_total", value=500)
        await broadcaster.broadcast_metric(name="agent_active_sessions", value=3)

        snapshot = broadcaster.get_metrics_snapshot()

        assert "http_requests_total" in snapshot
        assert snapshot["http_requests_total"]["value"] == 100
        assert "llm_tokens_total" in snapshot
        assert snapshot["llm_tokens_total"]["value"] == 500

    @pytest.mark.asyncio
    async def test_get_metrics_snapshot_by_session(self) -> None:
        """
        GIVEN a MetricsBroadcaster with session-scoped metrics
        WHEN get_metrics_snapshot is called with session_id
        THEN it should return only metrics for that session.
        """
        from mcp_server_langgraph.websocket.handlers.metrics_broadcaster import (
            MetricsBroadcaster,
        )

        broadcaster = MetricsBroadcaster()
        mock_ws = MagicMock()
        mock_ws.send_json = AsyncMock()
        await broadcaster.subscribe(mock_ws, user_id="user-1")

        await broadcaster.broadcast_metric(
            name="http_requests_total",
            value=50,
            session_id="session-A",
        )
        await broadcaster.broadcast_metric(
            name="http_requests_total",
            value=100,
            session_id="session-B",
        )

        snapshot_a = broadcaster.get_metrics_snapshot(session_id="session-A")
        snapshot_b = broadcaster.get_metrics_snapshot(session_id="session-B")

        assert snapshot_a["http_requests_total"]["value"] == 50
        assert snapshot_b["http_requests_total"]["value"] == 100


class TestMetricsBroadcasterIntegration:
    """
    Integration tests for MetricsBroadcaster with middleware.
    """

    def teardown_method(self) -> None:
        """Force GC to prevent mock accumulation in xdist workers."""
        gc.collect()

    @pytest.mark.asyncio
    async def test_singleton_pattern(self) -> None:
        """
        GIVEN the metrics broadcaster module
        WHEN get_metrics_broadcaster is called multiple times
        THEN it should return the same instance.
        """
        from mcp_server_langgraph.websocket.handlers.metrics_broadcaster import (
            get_metrics_broadcaster,
            reset_metrics_broadcaster,
        )

        reset_metrics_broadcaster()  # Ensure clean state

        broadcaster1 = get_metrics_broadcaster()
        broadcaster2 = get_metrics_broadcaster()

        assert broadcaster1 is broadcaster2

        reset_metrics_broadcaster()  # Cleanup


class TestMetricsBroadcasterTrend:
    """
    Tests for trend calculation based on sparkline data.
    """

    def teardown_method(self) -> None:
        """Force GC to prevent mock accumulation in xdist workers."""
        gc.collect()

    @pytest.mark.asyncio
    async def test_broadcast_includes_trend(self) -> None:
        """
        GIVEN historical metric values
        WHEN broadcast_metric is called
        THEN message should include calculated trend.
        """
        from mcp_server_langgraph.websocket.handlers.metrics_broadcaster import (
            MetricsBroadcaster,
        )

        broadcaster = MetricsBroadcaster()
        mock_ws = MagicMock()
        mock_ws.send_json = AsyncMock()
        await broadcaster.subscribe(mock_ws, user_id="user-1")

        # Increasing values = "up" trend
        for v in [10, 20, 30, 40, 50]:
            await broadcaster.broadcast_metric(name="requests", value=v)

        call_args = mock_ws.send_json.call_args[0][0]
        assert call_args["payload"]["trend"] == "up"

    @pytest.mark.asyncio
    async def test_broadcast_trend_down(self) -> None:
        """
        GIVEN decreasing metric values
        WHEN broadcast_metric is called
        THEN trend should be "down".
        """
        from mcp_server_langgraph.websocket.handlers.metrics_broadcaster import (
            MetricsBroadcaster,
        )

        broadcaster = MetricsBroadcaster()
        mock_ws = MagicMock()
        mock_ws.send_json = AsyncMock()
        await broadcaster.subscribe(mock_ws, user_id="user-1")

        for v in [50, 40, 30, 20, 10]:
            await broadcaster.broadcast_metric(name="sessions", value=v)

        call_args = mock_ws.send_json.call_args[0][0]
        assert call_args["payload"]["trend"] == "down"

    @pytest.mark.asyncio
    async def test_broadcast_trend_stable(self) -> None:
        """
        GIVEN stable metric values
        WHEN broadcast_metric is called
        THEN trend should be "stable".
        """
        from mcp_server_langgraph.websocket.handlers.metrics_broadcaster import (
            MetricsBroadcaster,
        )

        broadcaster = MetricsBroadcaster()
        mock_ws = MagicMock()
        mock_ws.send_json = AsyncMock()
        await broadcaster.subscribe(mock_ws, user_id="user-1")

        for v in [50, 51, 50, 49, 50]:
            await broadcaster.broadcast_metric(name="stable_metric", value=v)

        call_args = mock_ws.send_json.call_args[0][0]
        assert call_args["payload"]["trend"] == "stable"
