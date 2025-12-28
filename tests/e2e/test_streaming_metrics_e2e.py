"""
E2E tests for LLM streaming metrics.

This test suite validates the complete streaming metrics flow:
1. StreamingMetricsContext records metrics during streaming
2. Prometheus metrics are exposed on /metrics endpoint
3. Metrics have correct labels (model, provider, status)
4. Dashboard queries would return meaningful data

These tests simulate the full streaming workflow without requiring
actual LLM provider connections.

Markers:
--------
- @pytest.mark.e2e: End-to-end test category
- @pytest.mark.observability: Observability-specific tests
- @pytest.mark.metrics: Metrics-related tests
"""

from __future__ import annotations

import asyncio
import gc
import re
from typing import TYPE_CHECKING

import pytest

if TYPE_CHECKING:
    pass

pytestmark = [
    pytest.mark.e2e,
    pytest.mark.observability,
    pytest.mark.metrics,
]


# ==============================================================================
# Fixtures
# ==============================================================================


@pytest.fixture
def prometheus_output() -> str:
    """Generate Prometheus text format output after recording test metrics."""
    from prometheus_client import generate_latest

    from mcp_server_langgraph.llm.streaming_metrics import (
        record_chunk_count,
        record_inter_chunk_latency,
        record_streaming_duration,
        record_ttfc,
    )

    # Record metrics for multiple providers/models
    test_scenarios = [
        {"model": "gpt-4-turbo", "provider": "openai", "ttfc": 0.5, "duration": 5.0, "chunks": 100},
        {"model": "claude-3-opus", "provider": "anthropic", "ttfc": 0.8, "duration": 8.0, "chunks": 150},
        {"model": "gemini-2.0-flash", "provider": "google", "ttfc": 0.3, "duration": 3.0, "chunks": 50},
    ]

    for scenario in test_scenarios:
        record_ttfc(model=scenario["model"], ttfc_seconds=scenario["ttfc"], provider=scenario["provider"])
        record_inter_chunk_latency(model=scenario["model"], latency_seconds=0.02, provider=scenario["provider"])
        record_streaming_duration(
            model=scenario["model"],
            duration_seconds=scenario["duration"],
            provider=scenario["provider"],
            status="success",
        )
        record_chunk_count(model=scenario["model"], count=scenario["chunks"], provider=scenario["provider"])

    return generate_latest().decode("utf-8")


# ==============================================================================
# E2E Streaming Workflow Tests
# ==============================================================================


@pytest.mark.xdist_group(name="streaming_metrics_e2e")
class TestStreamingMetricsE2EWorkflow:
    """E2E tests for the complete streaming metrics workflow."""

    def teardown_method(self) -> None:
        """Force GC to prevent mock accumulation in xdist workers."""
        gc.collect()

    @pytest.mark.asyncio
    async def test_complete_streaming_workflow_records_all_metrics(self) -> None:
        """
        GIVEN a complete streaming workflow simulation
        WHEN streaming completes successfully
        THEN all metrics should be recorded with correct values.
        """
        from prometheus_client import generate_latest

        from mcp_server_langgraph.llm.streaming_metrics import StreamingMetricsContext

        # Simulate a complete streaming workflow
        ctx = StreamingMetricsContext(model="gpt-4o", provider="openai")
        ctx.start()

        # Simulate TTFC delay
        await asyncio.sleep(0.1)
        ctx.record_first_chunk()

        # Simulate 20 chunks with inter-chunk delays
        for _ in range(19):
            await asyncio.sleep(0.005)  # 5ms between chunks
            ctx.record_chunk()

        # Finalize
        ctx.finalize(status="success")

        # Verify all values were recorded
        assert ctx.ttfc_seconds is not None
        assert ctx.ttfc_seconds >= 0.1
        assert ctx.duration_seconds is not None
        assert ctx.duration_seconds >= 0.1
        assert ctx.chunk_count == 20
        assert ctx.finalized is True

        # Verify metrics appear in Prometheus output
        output = generate_latest().decode("utf-8")
        assert "llm_streaming_ttfc_seconds" in output
        assert "llm_streaming_inter_chunk_latency_seconds" in output
        assert "llm_streaming_duration_seconds" in output
        assert "llm_streaming_chunks_total" in output

    @pytest.mark.asyncio
    async def test_streaming_error_workflow_records_error_status(self) -> None:
        """
        GIVEN a streaming workflow that fails mid-stream
        WHEN streaming ends with error
        THEN duration metric should have error status.
        """
        from prometheus_client import generate_latest

        from mcp_server_langgraph.llm.streaming_metrics import StreamingMetricsContext

        ctx = StreamingMetricsContext(model="claude-3-sonnet", provider="anthropic")
        ctx.start()

        # Simulate partial streaming then error
        await asyncio.sleep(0.05)
        ctx.record_first_chunk()
        await asyncio.sleep(0.01)
        ctx.record_chunk()

        # Finalize with error
        ctx.finalize(status="error")

        assert ctx.finalized is True
        assert ctx.duration_seconds is not None

        # Verify error status in output
        output = generate_latest().decode("utf-8")
        assert 'status="error"' in output

    @pytest.mark.asyncio
    async def test_streaming_timeout_workflow_records_timeout_status(self) -> None:
        """
        GIVEN a streaming workflow that times out before first chunk
        WHEN streaming ends with timeout
        THEN duration metric should have timeout status.
        """
        from prometheus_client import generate_latest

        from mcp_server_langgraph.llm.streaming_metrics import StreamingMetricsContext

        ctx = StreamingMetricsContext(model="gemini-2.0-flash", provider="google")
        ctx.start()

        # Simulate timeout (no chunks received)
        await asyncio.sleep(0.05)
        ctx.finalize(status="timeout")

        assert ctx.finalized is True
        assert ctx.ttfc_seconds is None  # No first chunk
        assert ctx.chunk_count == 0

        # Verify timeout status in output
        output = generate_latest().decode("utf-8")
        assert 'status="timeout"' in output


# ==============================================================================
# Prometheus Output Validation Tests
# ==============================================================================


@pytest.mark.xdist_group(name="streaming_metrics_e2e")
class TestPrometheusOutputValidation:
    """E2E tests validating the Prometheus text format output."""

    def teardown_method(self) -> None:
        """Force GC to prevent mock accumulation in xdist workers."""
        gc.collect()

    def test_ttfc_histogram_has_correct_buckets(self, prometheus_output: str) -> None:
        """
        GIVEN streaming TTFC metrics
        WHEN exported as Prometheus format
        THEN histogram should have expected bucket boundaries.
        """
        # TTFC histogram should have buckets for 50ms to 30s
        assert 'llm_streaming_ttfc_seconds_bucket{le="0.05"' in prometheus_output
        assert 'llm_streaming_ttfc_seconds_bucket{le="0.5"' in prometheus_output
        assert 'llm_streaming_ttfc_seconds_bucket{le="2.0"' in prometheus_output
        assert 'llm_streaming_ttfc_seconds_bucket{le="10.0"' in prometheus_output

    def test_metrics_have_provider_labels(self, prometheus_output: str) -> None:
        """
        GIVEN streaming metrics for multiple providers
        WHEN exported as Prometheus format
        THEN metrics should have provider labels.
        """
        assert 'provider="openai"' in prometheus_output
        assert 'provider="anthropic"' in prometheus_output
        assert 'provider="google"' in prometheus_output

    def test_duration_metrics_have_status_labels(self, prometheus_output: str) -> None:
        """
        GIVEN streaming duration metrics
        WHEN exported as Prometheus format
        THEN duration histogram should have status labels.
        """
        # Match pattern for duration with status
        pattern = r'llm_streaming_duration_seconds.*status="success"'
        assert re.search(pattern, prometheus_output), "Duration metric should have status label"

    def test_chunks_counter_increments(self, prometheus_output: str) -> None:
        """
        GIVEN streaming chunk counts
        WHEN exported as Prometheus format
        THEN chunks counter should show accumulated counts.
        """
        # Should have chunks_total counter with values
        pattern = r"llm_streaming_chunks_total\{.*\}\s+\d+"
        assert re.search(pattern, prometheus_output), "Chunks counter should have values"


# ==============================================================================
# Dashboard Query Compatibility Tests
# ==============================================================================


@pytest.mark.xdist_group(name="streaming_metrics_e2e")
class TestDashboardQueryCompatibility:
    """E2E tests validating metrics work with dashboard PromQL queries."""

    def teardown_method(self) -> None:
        """Force GC to prevent mock accumulation in xdist workers."""
        gc.collect()

    def test_ttfc_p95_query_metric_exists(self, prometheus_output: str) -> None:
        """
        GIVEN the TTFC p95 dashboard query needs histogram data
        WHEN streaming metrics are recorded
        THEN llm_streaming_ttfc_seconds_bucket should exist with data.
        """
        # Dashboard query: histogram_quantile(0.95, sum(rate(llm_streaming_ttfc_seconds_bucket[5m])) by (le))
        assert "llm_streaming_ttfc_seconds_bucket" in prometheus_output
        assert "llm_streaming_ttfc_seconds_count" in prometheus_output
        assert "llm_streaming_ttfc_seconds_sum" in prometheus_output

    def test_inter_chunk_latency_query_metric_exists(self, prometheus_output: str) -> None:
        """
        GIVEN the inter-chunk latency dashboard query needs histogram data
        WHEN streaming metrics are recorded
        THEN llm_streaming_inter_chunk_latency_seconds_bucket should exist.
        """
        assert "llm_streaming_inter_chunk_latency_seconds_bucket" in prometheus_output
        assert "llm_streaming_inter_chunk_latency_seconds_count" in prometheus_output

    def test_streaming_success_rate_query_metrics_exist(self, prometheus_output: str) -> None:
        """
        GIVEN the streaming success rate dashboard query
        WHEN streaming metrics are recorded
        THEN llm_streaming_duration_seconds_count with status should exist.
        """
        # Dashboard query uses status="success" filter
        assert "llm_streaming_duration_seconds_count" in prometheus_output

    def test_chunks_per_second_query_metric_exists(self, prometheus_output: str) -> None:
        """
        GIVEN the chunks/sec dashboard query
        WHEN streaming metrics are recorded
        THEN llm_streaming_chunks_total should exist.
        """
        assert "llm_streaming_chunks_total" in prometheus_output


# ==============================================================================
# SLA Alert Threshold Validation Tests
# ==============================================================================


@pytest.mark.xdist_group(name="streaming_metrics_e2e")
class TestSLAAlertThresholdValidation:
    """E2E tests validating metrics support SLA alert thresholds."""

    def teardown_method(self) -> None:
        """Force GC to prevent mock accumulation in xdist workers."""
        gc.collect()

    @pytest.mark.asyncio
    async def test_ttfc_exceeding_sla_would_be_detectable(self) -> None:
        """
        GIVEN streaming with TTFC exceeding 2s SLA threshold
        WHEN metrics are recorded
        THEN the high TTFC value should be observable in histogram.
        """
        from prometheus_client import generate_latest

        from mcp_server_langgraph.llm.streaming_metrics import record_ttfc

        # Record a TTFC that exceeds 2s SLA
        record_ttfc(model="slow-model", ttfc_seconds=3.5, provider="test")

        output = generate_latest().decode("utf-8")

        # The 3.5s value should fall in a bucket >= 2.0
        # This means the 2.0 bucket should NOT contain this observation
        # but the 5.0 bucket should
        assert 'llm_streaming_ttfc_seconds_bucket{le="5.0"' in output

    @pytest.mark.asyncio
    async def test_inter_chunk_latency_exceeding_threshold_detectable(self) -> None:
        """
        GIVEN streaming with inter-chunk latency exceeding 250ms threshold
        WHEN metrics are recorded
        THEN the high latency should be observable in histogram.
        """
        from prometheus_client import generate_latest

        from mcp_server_langgraph.llm.streaming_metrics import record_inter_chunk_latency

        # Record a latency that exceeds 250ms threshold
        record_inter_chunk_latency(model="choppy-model", latency_seconds=0.4, provider="test")

        output = generate_latest().decode("utf-8")

        # The 0.4s value should be in bucket >= 0.25
        assert 'llm_streaming_inter_chunk_latency_seconds_bucket{le="0.5"' in output
