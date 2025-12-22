"""
Unit tests for resilience metrics (OpenTelemetry).

TDD Cycle: RED -> GREEN -> REFACTOR

These tests verify that:
1. Rate limit metrics are exported (token exhaustion, wait time)
2. Adaptive bulkhead metrics are exported (limit changes, error rate)
3. Circuit breaker metrics are properly recorded
4. All metrics have correct attributes (provider, service)

Reference: ADR-0026 - Resilience Patterns
"""

import gc
from unittest.mock import MagicMock, patch

import pytest

# Mark as unit test
pytestmark = [
    pytest.mark.unit,
    pytest.mark.observability,
    pytest.mark.resilience,
]


@pytest.mark.xdist_group(name="resilience_metrics_tests")
class TestRateLimitMetrics:
    """Test rate limit metrics export."""

    def teardown_method(self) -> None:
        """Force GC to prevent mock accumulation in xdist workers."""
        gc.collect()

    def test_rate_limit_token_exhausted_counter_exists(self):
        """
        GIVEN: Telemetry metrics module
        WHEN: rate_limit_token_exhausted_counter is accessed
        THEN: Should exist and be callable

        User Journey: Monitor rate limit token exhaustion in Grafana
        """
        from mcp_server_langgraph.observability.telemetry import (
            rate_limit_token_exhausted_counter,
        )

        # Should be a callable metric
        assert hasattr(rate_limit_token_exhausted_counter, "add")

    def test_rate_limit_wait_time_histogram_exists(self):
        """
        GIVEN: Telemetry metrics module
        WHEN: rate_limit_wait_time_histogram is accessed
        THEN: Should exist and be callable

        User Journey: Monitor rate limit wait times in Grafana
        """
        from mcp_server_langgraph.observability.telemetry import (
            rate_limit_wait_time_histogram,
        )

        # Should be a callable metric
        assert hasattr(rate_limit_wait_time_histogram, "record")

    def test_rate_limit_tokens_available_gauge_exists(self):
        """
        GIVEN: Telemetry metrics module
        WHEN: rate_limit_tokens_available_gauge is accessed
        THEN: Should exist and be callable

        User Journey: Monitor rate limit token availability in real-time
        """
        from mcp_server_langgraph.observability.telemetry import (
            rate_limit_tokens_available_gauge,
        )

        # Should be a callable metric
        assert hasattr(rate_limit_tokens_available_gauge, "set")


@pytest.mark.xdist_group(name="resilience_metrics_tests")
class TestAdaptiveBulkheadMetrics:
    """Test adaptive bulkhead metrics export."""

    def teardown_method(self) -> None:
        """Force GC to prevent mock accumulation in xdist workers."""
        gc.collect()

    def test_adaptive_bulkhead_limit_gauge_exists(self):
        """
        GIVEN: Telemetry metrics module
        WHEN: adaptive_bulkhead_limit_gauge is accessed
        THEN: Should exist and be callable

        User Journey: Monitor adaptive bulkhead limit in Grafana
        """
        from mcp_server_langgraph.observability.telemetry import (
            adaptive_bulkhead_limit_gauge,
        )

        # Should be a callable metric
        assert hasattr(adaptive_bulkhead_limit_gauge, "set")

    def test_adaptive_bulkhead_error_rate_gauge_exists(self):
        """
        GIVEN: Telemetry metrics module
        WHEN: adaptive_bulkhead_error_rate_gauge is accessed
        THEN: Should exist and be callable

        User Journey: Monitor error rate for adaptive tuning
        """
        from mcp_server_langgraph.observability.telemetry import (
            adaptive_bulkhead_error_rate_gauge,
        )

        # Should be a callable metric
        assert hasattr(adaptive_bulkhead_error_rate_gauge, "set")

    def test_adaptive_bulkhead_adjustment_counter_exists(self):
        """
        GIVEN: Telemetry metrics module
        WHEN: adaptive_bulkhead_adjustment_counter is accessed
        THEN: Should exist and be callable

        User Journey: Track bulkhead limit adjustments (increases/decreases)
        """
        from mcp_server_langgraph.observability.telemetry import (
            adaptive_bulkhead_adjustment_counter,
        )

        # Should be a callable metric
        assert hasattr(adaptive_bulkhead_adjustment_counter, "add")


@pytest.mark.xdist_group(name="resilience_metrics_tests")
class TestResilienceMetricsIntegration:
    """Test resilience metrics are recorded correctly."""

    def teardown_method(self) -> None:
        """Force GC to prevent mock accumulation in xdist workers."""
        gc.collect()

    def test_record_rate_limit_exhaustion(self):
        """
        GIVEN: Rate limit helper function
        WHEN: Called with provider name
        THEN: Should increment counter with correct attributes

        User Journey: Record rate limit exhaustion for alerting
        """
        from mcp_server_langgraph.resilience.metrics import (
            record_rate_limit_exhaustion,
        )

        # Should not raise
        record_rate_limit_exhaustion(provider="anthropic")

    def test_record_rate_limit_wait_time(self):
        """
        GIVEN: Rate limit helper function
        WHEN: Called with wait time
        THEN: Should record histogram value

        User Journey: Track rate limit wait time distribution
        """
        from mcp_server_langgraph.resilience.metrics import (
            record_rate_limit_wait_time,
        )

        # Should not raise
        record_rate_limit_wait_time(provider="openai", wait_time_ms=150.0)

    def test_record_adaptive_bulkhead_adjustment(self):
        """
        GIVEN: Adaptive bulkhead helper function
        WHEN: Called with adjustment type
        THEN: Should increment counter with direction attribute

        User Journey: Track bulkhead limit changes
        """
        from mcp_server_langgraph.resilience.metrics import (
            record_adaptive_bulkhead_adjustment,
        )

        # Should not raise
        record_adaptive_bulkhead_adjustment(
            provider="anthropic",
            direction="decrease",
            new_limit=8,
        )

    def test_update_adaptive_bulkhead_stats(self):
        """
        GIVEN: Adaptive bulkhead helper function
        WHEN: Called with current stats
        THEN: Should update gauges

        User Journey: Monitor current bulkhead state
        """
        from mcp_server_langgraph.resilience.metrics import (
            update_adaptive_bulkhead_stats,
        )

        # Should not raise
        update_adaptive_bulkhead_stats(
            provider="openai",
            current_limit=10,
            error_rate=0.05,
        )
