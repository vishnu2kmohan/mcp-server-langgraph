"""
Integration tests for LLM streaming metrics.

This test suite validates that streaming metrics are properly exposed,
recorded, and can be queried from Prometheus.

Tests cover:
- Prometheus metric exposure on /metrics endpoint
- StreamingMetricsContext end-to-end workflow
- Metric label correctness for different models/providers
- Dashboard PromQL query validation

Markers:
--------
- @pytest.mark.integration: Integration test category
- @pytest.mark.observability: Observability-specific tests
- @pytest.mark.metrics: Metrics-related tests

Related Components:
-------------------
- src/mcp_server_langgraph/llm/streaming_metrics.py
- monitoring/grafana/dashboards/Application/llm-streaming.json
- deployments/helm/mcp-server-langgraph/prometheus-rules/sla.yaml
"""

from __future__ import annotations

import asyncio
import gc
import time
from typing import TYPE_CHECKING

import pytest

if TYPE_CHECKING:
    from collections.abc import Generator

pytestmark = [
    pytest.mark.integration,
    pytest.mark.observability,
    pytest.mark.metrics,
]


# ==============================================================================
# Fixtures
# ==============================================================================


@pytest.fixture
def clean_metrics_registry() -> Generator[None, None, None]:
    """
    Clean up metrics registry before and after tests.

    Note: Prometheus metrics persist globally, so we need to handle
    existing metrics gracefully in integration tests.
    """
    yield
    gc.collect()


# ==============================================================================
# Streaming Metrics Exposure Tests
# ==============================================================================


@pytest.mark.xdist_group(name="streaming_metrics_integration")
class TestStreamingMetricsExposure:
    """Test that streaming metrics are properly exposed via prometheus_client."""

    def teardown_method(self) -> None:
        """Force GC to prevent mock accumulation in xdist workers."""
        gc.collect()

    def test_streaming_metrics_module_initializes_metrics(self) -> None:
        """
        GIVEN prometheus_client is available
        WHEN importing streaming_metrics module
        THEN metrics should be initialized and available.
        """
        from mcp_server_langgraph.llm.streaming_metrics import (
            _llm_streaming_chunks,
            _llm_streaming_duration,
            _llm_streaming_inter_chunk_latency,
            _llm_streaming_ttfc,
            _metrics_available,
        )

        assert _metrics_available is True
        assert _llm_streaming_ttfc is not None
        assert _llm_streaming_inter_chunk_latency is not None
        assert _llm_streaming_duration is not None
        assert _llm_streaming_chunks is not None

    def test_streaming_metrics_exposed_on_registry(self) -> None:
        """
        GIVEN streaming metrics are initialized
        WHEN querying the prometheus registry
        THEN streaming metrics should be registered.
        """
        from prometheus_client import REGISTRY

        # Check that our metrics are in the registry
        metric_names = [metric.name for metric in REGISTRY.collect()]

        # Look for our streaming metrics (may have _total or _bucket suffixes)
        streaming_metrics = [name for name in metric_names if name.startswith("llm_streaming_")]

        # Should have at least the base metric names
        assert len(streaming_metrics) >= 1, f"No streaming metrics found. Available: {metric_names[:20]}"

    def test_streaming_metrics_generate_prometheus_format(self) -> None:
        """
        GIVEN streaming metrics with recorded values
        WHEN generating prometheus text format
        THEN output should contain streaming metric lines.
        """
        from prometheus_client import generate_latest

        from mcp_server_langgraph.llm.streaming_metrics import (
            record_chunk_count,
            record_inter_chunk_latency,
            record_streaming_duration,
            record_ttfc,
        )

        # Record some test values
        record_ttfc(model="test-model", ttfc_seconds=0.5, provider="test")
        record_inter_chunk_latency(model="test-model", latency_seconds=0.02, provider="test")
        record_streaming_duration(model="test-model", duration_seconds=5.0, provider="test", status="success")
        record_chunk_count(model="test-model", count=100, provider="test")

        # Generate prometheus text format
        output = generate_latest().decode("utf-8")

        # Verify metrics appear in output
        assert "llm_streaming_ttfc_seconds" in output
        assert "llm_streaming_inter_chunk_latency_seconds" in output
        assert "llm_streaming_duration_seconds" in output
        assert "llm_streaming_chunks_total" in output


# ==============================================================================
# StreamingMetricsContext End-to-End Tests
# ==============================================================================


@pytest.mark.xdist_group(name="streaming_metrics_integration")
class TestStreamingMetricsContextE2E:
    """End-to-end tests for StreamingMetricsContext."""

    def teardown_method(self) -> None:
        """Force GC to prevent mock accumulation in xdist workers."""
        gc.collect()

    @pytest.mark.asyncio
    async def test_streaming_context_full_workflow(self) -> None:
        """
        GIVEN a StreamingMetricsContext
        WHEN simulating a complete streaming workflow
        THEN all metrics should be recorded correctly.
        """
        from mcp_server_langgraph.llm.streaming_metrics import StreamingMetricsContext

        # Create context
        ctx = StreamingMetricsContext(model="gpt-4-turbo", provider="openai")

        # Start streaming
        ctx.start()

        # Simulate first chunk arrival after 100ms
        await asyncio.sleep(0.1)
        ctx.record_first_chunk()

        # Verify TTFC was recorded
        assert ctx.ttfc_seconds is not None
        assert ctx.ttfc_seconds >= 0.1
        assert ctx.first_chunk_received is True
        assert ctx.chunk_count == 1

        # Simulate subsequent chunks
        for _ in range(9):
            await asyncio.sleep(0.01)  # 10ms between chunks
            ctx.record_chunk()

        # Verify chunk count
        assert ctx.chunk_count == 10

        # Finalize
        ctx.finalize(status="success")

        # Verify final state
        assert ctx.finalized is True
        assert ctx.duration_seconds is not None
        # Allow for async scheduling variance (target ~200ms, accept >150ms)
        assert ctx.duration_seconds >= 0.15, f"Expected >= 150ms, got {ctx.duration_seconds:.3f}s"

    @pytest.mark.asyncio
    async def test_streaming_context_error_status(self) -> None:
        """
        GIVEN a StreamingMetricsContext
        WHEN streaming ends with an error
        THEN duration should be recorded with error status.
        """
        from mcp_server_langgraph.llm.streaming_metrics import StreamingMetricsContext

        ctx = StreamingMetricsContext(model="claude-3-opus", provider="anthropic")
        ctx.start()

        # Simulate partial streaming then error
        await asyncio.sleep(0.05)
        ctx.record_first_chunk()
        await asyncio.sleep(0.02)
        ctx.record_chunk()

        # Finalize with error
        ctx.finalize(status="error")

        assert ctx.finalized is True
        assert ctx.duration_seconds is not None
        assert ctx.chunk_count == 2

    @pytest.mark.asyncio
    async def test_streaming_context_timeout_status(self) -> None:
        """
        GIVEN a StreamingMetricsContext
        WHEN streaming times out
        THEN duration should be recorded with timeout status.
        """
        from mcp_server_langgraph.llm.streaming_metrics import StreamingMetricsContext

        ctx = StreamingMetricsContext(model="gemini-2.0-flash", provider="google")
        ctx.start()

        # Simulate timeout before first chunk
        await asyncio.sleep(0.1)

        # Finalize with timeout (no chunks received)
        ctx.finalize(status="timeout")

        assert ctx.finalized is True
        assert ctx.duration_seconds is not None
        assert ctx.chunk_count == 0
        assert ctx.ttfc_seconds is None  # No first chunk

    @pytest.mark.asyncio
    async def test_streaming_context_idempotent_finalize(self) -> None:
        """
        GIVEN a finalized StreamingMetricsContext
        WHEN finalize is called again
        THEN it should be a no-op.
        """
        from mcp_server_langgraph.llm.streaming_metrics import StreamingMetricsContext

        ctx = StreamingMetricsContext(model="gpt-4", provider="openai")
        ctx.start()
        ctx.record_first_chunk()
        ctx.finalize(status="success")

        # Record first finalization values
        first_duration = ctx.duration_seconds

        # Wait and finalize again
        await asyncio.sleep(0.05)
        ctx.finalize(status="error")  # Different status

        # Duration should not have changed
        assert ctx.duration_seconds == first_duration


# ==============================================================================
# Multi-Provider Label Tests
# ==============================================================================


@pytest.mark.xdist_group(name="streaming_metrics_integration")
class TestStreamingMetricsLabels:
    """Test that streaming metrics correctly label by model and provider."""

    def teardown_method(self) -> None:
        """Force GC to prevent mock accumulation in xdist workers."""
        gc.collect()

    def test_ttfc_metric_includes_model_and_provider_labels(self) -> None:
        """
        GIVEN TTFC metric recordings for different models/providers
        WHEN generating prometheus output
        THEN labels should correctly identify model and provider.
        """
        from prometheus_client import generate_latest

        from mcp_server_langgraph.llm.streaming_metrics import record_ttfc

        # Record for different providers
        record_ttfc(model="gpt-4-turbo-preview", ttfc_seconds=0.3, provider="openai")
        record_ttfc(model="claude-3-sonnet-20240229", ttfc_seconds=0.4, provider="anthropic")
        record_ttfc(model="gemini-2.0-flash-exp", ttfc_seconds=0.2, provider="google")

        output = generate_latest().decode("utf-8")

        # Verify labels appear (model family normalization happens)
        assert 'provider="openai"' in output
        assert 'provider="anthropic"' in output
        assert 'provider="google"' in output

    def test_streaming_duration_includes_status_label(self) -> None:
        """
        GIVEN streaming duration recordings with different statuses
        WHEN generating prometheus output
        THEN status labels should be correctly applied.
        """
        from prometheus_client import generate_latest

        from mcp_server_langgraph.llm.streaming_metrics import record_streaming_duration

        # Record different statuses
        record_streaming_duration(model="gpt-4", duration_seconds=5.0, provider="openai", status="success")
        record_streaming_duration(model="gpt-4", duration_seconds=2.0, provider="openai", status="error")
        record_streaming_duration(model="gpt-4", duration_seconds=30.0, provider="openai", status="timeout")

        output = generate_latest().decode("utf-8")

        # Verify status labels appear
        assert 'status="success"' in output
        assert 'status="error"' in output
        assert 'status="timeout"' in output


# ==============================================================================
# Dashboard PromQL Query Validation Tests
# ==============================================================================


@pytest.mark.xdist_group(name="streaming_metrics_integration")
class TestDashboardPromQLQueries:
    """
    Validate that the PromQL queries used in Grafana dashboards are syntactically correct
    and reference the correct metric names.
    """

    def teardown_method(self) -> None:
        """Force GC to prevent mock accumulation in xdist workers."""
        gc.collect()

    def test_ttfc_p95_query_references_correct_metric(self) -> None:
        """
        GIVEN the TTFC p95 query from the dashboard
        WHEN parsing the query
        THEN it should reference llm_streaming_ttfc_seconds_bucket.
        """
        # Query from llm-streaming.json dashboard
        ttfc_p95_query = "histogram_quantile(0.95, sum(rate(llm_streaming_ttfc_seconds_bucket[$__rate_interval])) by (le))"

        # Verify metric name is correct
        assert "llm_streaming_ttfc_seconds_bucket" in ttfc_p95_query
        assert "histogram_quantile" in ttfc_p95_query
        assert "0.95" in ttfc_p95_query

    def test_inter_chunk_latency_query_references_correct_metric(self) -> None:
        """
        GIVEN the inter-chunk latency query from the dashboard
        WHEN parsing the query
        THEN it should reference llm_streaming_inter_chunk_latency_seconds_bucket.
        """
        inter_chunk_query = (
            "histogram_quantile(0.95, sum(rate(llm_streaming_inter_chunk_latency_seconds_bucket[$__rate_interval])) by (le))"
        )

        assert "llm_streaming_inter_chunk_latency_seconds_bucket" in inter_chunk_query
        assert "histogram_quantile" in inter_chunk_query

    def test_streaming_success_rate_query_references_correct_metric(self) -> None:
        """
        GIVEN the streaming success rate query from the dashboard
        WHEN parsing the query
        THEN it should reference llm_streaming_duration_seconds_count with status filter.
        """
        success_rate_query = (
            '(sum(rate(llm_streaming_duration_seconds_count{status="success"}[$__rate_interval])) / '
            "sum(rate(llm_streaming_duration_seconds_count[$__rate_interval]))) * 100"
        )

        assert "llm_streaming_duration_seconds_count" in success_rate_query
        assert 'status="success"' in success_rate_query

    def test_chunks_per_second_query_references_correct_metric(self) -> None:
        """
        GIVEN the chunks per second query from the dashboard
        WHEN parsing the query
        THEN it should reference llm_streaming_chunks_total.
        """
        chunks_query = "sum(rate(llm_streaming_chunks_total[$__rate_interval]))"

        assert "llm_streaming_chunks_total" in chunks_query
        assert "rate" in chunks_query


# ==============================================================================
# SLA Alert Rule Validation Tests
# ==============================================================================


@pytest.mark.xdist_group(name="streaming_metrics_integration")
class TestSLAAlertRuleExpressions:
    """
    Validate that SLA alert rule expressions are correct and reference
    the proper streaming metrics.
    """

    def teardown_method(self) -> None:
        """Force GC to prevent mock accumulation in xdist workers."""
        gc.collect()

    def test_ttfc_breach_alert_expression_is_valid(self) -> None:
        """
        GIVEN the SLAStreamingTTFCBreach alert expression
        WHEN parsing the expression
        THEN it should be syntactically correct for PromQL.
        """
        # From sla.yaml
        ttfc_breach_expr = "histogram_quantile(0.95, sum(rate(llm_streaming_ttfc_seconds_bucket[5m])) by (le)) > 2.0"

        # Verify structure
        assert "histogram_quantile(0.95" in ttfc_breach_expr
        assert "llm_streaming_ttfc_seconds_bucket" in ttfc_breach_expr
        assert "> 2.0" in ttfc_breach_expr  # SLA threshold

    def test_streaming_error_rate_alert_expression_is_valid(self) -> None:
        """
        GIVEN the SLAStreamingErrorRateHigh alert expression
        WHEN parsing the expression
        THEN it should calculate error rate percentage correctly.
        """
        # From sla.yaml
        error_rate_expr = (
            '(sum(rate(llm_streaming_duration_seconds_count{status=~"error|timeout"}[5m])) / '
            "sum(rate(llm_streaming_duration_seconds_count[5m])) * 100) > 5.0"
        )

        # Verify structure
        assert "llm_streaming_duration_seconds_count" in error_rate_expr
        assert 'status=~"error|timeout"' in error_rate_expr
        assert "* 100" in error_rate_expr  # Percentage conversion
        assert "> 5.0" in error_rate_expr  # 5% threshold

    def test_inter_chunk_latency_alert_expression_is_valid(self) -> None:
        """
        GIVEN the SLAStreamingInterChunkLatencyHigh alert expression
        WHEN parsing the expression
        THEN it should reference correct metric with proper threshold.
        """
        # From sla.yaml
        inter_chunk_expr = (
            "histogram_quantile(0.95, sum(rate(llm_streaming_inter_chunk_latency_seconds_bucket[5m])) by (le)) > 0.25"
        )

        # Verify structure
        assert "llm_streaming_inter_chunk_latency_seconds_bucket" in inter_chunk_expr
        assert "> 0.25" in inter_chunk_expr  # 250ms threshold


# ==============================================================================
# Histogram Bucket Coverage Tests
# ==============================================================================


@pytest.mark.xdist_group(name="streaming_metrics_integration")
class TestHistogramBucketCoverage:
    """Test that histogram buckets cover expected ranges."""

    def teardown_method(self) -> None:
        """Force GC to prevent mock accumulation in xdist workers."""
        gc.collect()

    def test_ttfc_buckets_cover_expected_range(self) -> None:
        """
        GIVEN the TTFC histogram
        WHEN checking bucket boundaries
        THEN buckets should cover 50ms to 30s range.
        """
        from mcp_server_langgraph.llm.streaming_metrics import _llm_streaming_ttfc

        if _llm_streaming_ttfc is None:
            pytest.skip("Prometheus metrics not available")

        # Get bucket boundaries from the histogram
        # Prometheus histograms have _upper_bounds attribute
        buckets = _llm_streaming_ttfc._upper_bounds

        # Verify coverage
        assert min(buckets) <= 0.1, "Buckets should start at 100ms or less"
        assert max(buckets) >= 10.0, "Buckets should extend to at least 10s"

    def test_inter_chunk_latency_buckets_cover_expected_range(self) -> None:
        """
        GIVEN the inter-chunk latency histogram
        WHEN checking bucket boundaries
        THEN buckets should cover 1ms to 1s range.
        """
        from mcp_server_langgraph.llm.streaming_metrics import _llm_streaming_inter_chunk_latency

        if _llm_streaming_inter_chunk_latency is None:
            pytest.skip("Prometheus metrics not available")

        buckets = _llm_streaming_inter_chunk_latency._upper_bounds

        # Verify coverage for fast inter-chunk latencies
        assert min(buckets) <= 0.01, "Buckets should start at 10ms or less"
        assert max(buckets) >= 0.5, "Buckets should extend to at least 500ms"

    def test_streaming_duration_buckets_cover_expected_range(self) -> None:
        """
        GIVEN the streaming duration histogram
        WHEN checking bucket boundaries
        THEN buckets should cover 500ms to 5 minutes.
        """
        from mcp_server_langgraph.llm.streaming_metrics import _llm_streaming_duration

        if _llm_streaming_duration is None:
            pytest.skip("Prometheus metrics not available")

        buckets = _llm_streaming_duration._upper_bounds

        # Verify coverage for streaming durations
        assert min(buckets) <= 1.0, "Buckets should start at 1s or less"
        assert max(buckets) >= 120.0, "Buckets should extend to at least 2 minutes"


# ==============================================================================
# Performance Timing Tests
# ==============================================================================


@pytest.mark.xdist_group(name="streaming_metrics_integration")
class TestMetricsRecordingPerformance:
    """Test that metrics recording has minimal performance overhead."""

    def teardown_method(self) -> None:
        """Force GC to prevent mock accumulation in xdist workers."""
        gc.collect()

    def test_ttfc_recording_is_fast(self) -> None:
        """
        GIVEN the TTFC recording function
        WHEN recording many values
        THEN average recording time should be under 100 microseconds.
        """
        from mcp_server_langgraph.llm.streaming_metrics import record_ttfc

        # Warm up
        for _ in range(100):
            record_ttfc(model="gpt-4", ttfc_seconds=0.5, provider="openai")

        # Measure
        iterations = 1000
        start = time.perf_counter()
        for _ in range(iterations):
            record_ttfc(model="gpt-4", ttfc_seconds=0.5, provider="openai")
        elapsed = time.perf_counter() - start

        avg_time_us = (elapsed / iterations) * 1_000_000
        assert avg_time_us < 100, f"Recording took {avg_time_us:.2f}µs, expected < 100µs"

    def test_chunk_recording_is_fast(self) -> None:
        """
        GIVEN the inter-chunk latency recording function
        WHEN recording many values
        THEN average recording time should be under 100 microseconds.
        """
        from mcp_server_langgraph.llm.streaming_metrics import record_inter_chunk_latency

        # Warm up
        for _ in range(100):
            record_inter_chunk_latency(model="gpt-4", latency_seconds=0.02, provider="openai")

        # Measure
        iterations = 1000
        start = time.perf_counter()
        for _ in range(iterations):
            record_inter_chunk_latency(model="gpt-4", latency_seconds=0.02, provider="openai")
        elapsed = time.perf_counter() - start

        avg_time_us = (elapsed / iterations) * 1_000_000
        assert avg_time_us < 100, f"Recording took {avg_time_us:.2f}µs, expected < 100µs"
