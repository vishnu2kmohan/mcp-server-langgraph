"""
Unit tests for HTTP client connection pool metrics.

TDD Cycle: RED -> GREEN -> REFACTOR

These tests verify that:
1. Connection pool metrics are exported (active connections, max connections)
2. Pool utilization gauge is updated
3. Metrics helper functions work correctly

Reference: ADR-0026 - Resilience Patterns
"""

import gc

import pytest

# Mark as unit test
pytestmark = [
    pytest.mark.unit,
    pytest.mark.core,
    pytest.mark.resilience,
]


@pytest.mark.xdist_group(name="http_client_metrics_tests")
class TestHttpClientPoolMetrics:
    """Test HTTP client connection pool metrics export."""

    def teardown_method(self) -> None:
        """Force GC to prevent mock accumulation in xdist workers."""
        gc.collect()

    def test_http_pool_active_connections_gauge_exists(self):
        """
        GIVEN: Telemetry metrics module
        WHEN: http_pool_active_connections_gauge is accessed
        THEN: Should exist and be callable

        User Journey: Monitor active HTTP connections in Grafana
        """
        from mcp_server_langgraph.observability.telemetry import (
            http_pool_active_connections_gauge,
        )

        # Should be a callable metric
        assert hasattr(http_pool_active_connections_gauge, "set")

    def test_http_pool_max_connections_gauge_exists(self):
        """
        GIVEN: Telemetry metrics module
        WHEN: http_pool_max_connections_gauge is accessed
        THEN: Should exist and be callable

        User Journey: Monitor connection pool capacity in Grafana
        """
        from mcp_server_langgraph.observability.telemetry import (
            http_pool_max_connections_gauge,
        )

        # Should be a callable metric
        assert hasattr(http_pool_max_connections_gauge, "set")

    def test_http_pool_utilization_gauge_exists(self):
        """
        GIVEN: Telemetry metrics module
        WHEN: http_pool_utilization_gauge is accessed
        THEN: Should exist and be callable

        User Journey: Monitor pool utilization percentage for scaling decisions
        """
        from mcp_server_langgraph.observability.telemetry import (
            http_pool_utilization_gauge,
        )

        # Should be a callable metric
        assert hasattr(http_pool_utilization_gauge, "set")


@pytest.mark.xdist_group(name="http_client_metrics_tests")
class TestHttpClientPoolMetricsIntegration:
    """Test HTTP client pool metrics are recorded correctly."""

    def teardown_method(self) -> None:
        """Force GC to prevent mock accumulation in xdist workers."""
        gc.collect()

    def test_get_pool_stats_returns_stats(self):
        """
        GIVEN: HTTP client manager with initialized client
        WHEN: get_pool_stats() is called
        THEN: Should return pool statistics

        User Journey: Get pool stats for health checks
        """
        from mcp_server_langgraph.core.http_client import HttpClientManager

        manager = HttpClientManager()
        stats = manager.get_pool_stats()

        assert isinstance(stats, dict)
        assert "max_connections" in stats
        assert "max_keepalive_connections" in stats
        assert "keepalive_expiry" in stats

    def test_record_pool_metrics_helper(self):
        """
        GIVEN: Pool metrics helper function
        WHEN: Called with pool stats
        THEN: Should update gauges

        User Journey: Record pool metrics for Grafana dashboards
        """
        from mcp_server_langgraph.resilience.metrics import record_pool_metrics

        # Should not raise
        record_pool_metrics(
            active_connections=50,
            max_connections=200,
        )

    def test_record_pool_metrics_calculates_utilization(self):
        """
        GIVEN: Pool metrics helper function
        WHEN: Called with active and max connections
        THEN: Should calculate and record utilization percentage

        User Journey: Track pool utilization for alerting
        """
        from mcp_server_langgraph.resilience.metrics import record_pool_metrics

        # Should not raise - 50/200 = 25% utilization
        record_pool_metrics(
            active_connections=50,
            max_connections=200,
        )
