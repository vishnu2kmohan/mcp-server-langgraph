"""
Tests for AI Explanation Metrics.

Tests the OpenTelemetry metrics for explanation generation:
- Generation count (with cache hit/miss)
- Generation latency histogram
- Cache hit rate gauge
- Analysis type breakdown

TDD: These tests are written FIRST before implementation.
"""

from __future__ import annotations

import gc
from unittest.mock import patch

import pytest


pytestmark = pytest.mark.unit


@pytest.mark.xdist_group(name="explanation_metrics")
class TestExplanationMetrics:
    """Tests for explanation generation metrics."""

    def teardown_method(self) -> None:
        """Force GC to prevent mock accumulation in xdist workers."""
        gc.collect()

    def test_explanation_generation_counter_exists(self) -> None:
        """Test that explanation generation counter metric exists."""
        from mcp_server_langgraph.agents.metrics import explanation_generation_counter

        assert explanation_generation_counter is not None
        # NoOp counters still have add method
        assert hasattr(explanation_generation_counter, "add")

    def test_explanation_latency_histogram_exists(self) -> None:
        """Test that explanation latency histogram metric exists."""
        from mcp_server_langgraph.agents.metrics import explanation_latency_histogram

        assert explanation_latency_histogram is not None
        # NoOp histograms still have record method
        assert hasattr(explanation_latency_histogram, "record")

    def test_explanation_cache_hit_counter_exists(self) -> None:
        """Test that cache hit counter metric exists."""
        from mcp_server_langgraph.agents.metrics import explanation_cache_counter

        assert explanation_cache_counter is not None
        # NoOp counters still have add method
        assert hasattr(explanation_cache_counter, "add")

    def test_record_explanation_generation_records_all_attributes(self) -> None:
        """Test that record_explanation_generation records correct attributes."""
        from mcp_server_langgraph.agents.metrics import record_explanation_generation

        with patch("mcp_server_langgraph.agents.metrics.explanation_generation_counter") as mock_counter:
            with patch("mcp_server_langgraph.agents.metrics.explanation_latency_histogram") as mock_histogram:
                record_explanation_generation(
                    approval_id="test-approval-123",
                    duration_ms=150.5,
                    success=True,
                    cached=False,
                    analysis_types=["uncertainty", "risk", "alternatives"],
                )

                # Verify counter was called
                mock_counter.add.assert_called_once()
                call_args = mock_counter.add.call_args
                assert call_args[0][0] == 1  # count
                attributes = call_args[0][1]
                assert attributes["success"] == "true"
                assert attributes["cached"] == "false"

                # Verify histogram was called
                mock_histogram.record.assert_called_once()
                hist_args = mock_histogram.record.call_args
                assert hist_args[0][0] == 150.5  # duration_ms

    def test_record_explanation_generation_with_cache_hit(self) -> None:
        """Test that cache hit is recorded correctly."""
        from mcp_server_langgraph.agents.metrics import record_explanation_generation

        with patch("mcp_server_langgraph.agents.metrics.explanation_generation_counter"):
            with patch("mcp_server_langgraph.agents.metrics.explanation_cache_counter") as mock_cache:
                record_explanation_generation(
                    approval_id="test-approval-456",
                    duration_ms=5.0,  # Fast because cached
                    success=True,
                    cached=True,
                )

                # Verify cache counter incremented for hit
                mock_cache.add.assert_called_once()
                cache_args = mock_cache.add.call_args
                assert cache_args[0][0] == 1
                assert cache_args[0][1]["cache_result"] == "hit"

    def test_record_explanation_generation_with_cache_miss(self) -> None:
        """Test that cache miss is recorded correctly."""
        from mcp_server_langgraph.agents.metrics import record_explanation_generation

        with patch("mcp_server_langgraph.agents.metrics.explanation_generation_counter"):
            with patch("mcp_server_langgraph.agents.metrics.explanation_cache_counter") as mock_cache:
                record_explanation_generation(
                    approval_id="test-approval-789",
                    duration_ms=200.0,
                    success=True,
                    cached=False,
                )

                # Verify cache counter incremented for miss
                mock_cache.add.assert_called_once()
                cache_args = mock_cache.add.call_args
                assert cache_args[0][0] == 1
                assert cache_args[0][1]["cache_result"] == "miss"

    def test_record_explanation_generation_failure(self) -> None:
        """Test that failed generation is recorded with error type."""
        from mcp_server_langgraph.agents.metrics import record_explanation_generation

        with patch("mcp_server_langgraph.agents.metrics.explanation_generation_counter"):
            with patch("mcp_server_langgraph.agents.metrics.explanation_error_counter") as mock_error:
                record_explanation_generation(
                    approval_id="test-approval-fail",
                    duration_ms=50.0,
                    success=False,
                    cached=False,
                    error_type="llm_timeout",
                )

                # Verify error counter was called
                mock_error.add.assert_called_once()
                error_args = mock_error.add.call_args
                assert error_args[0][0] == 1
                assert error_args[0][1]["error_type"] == "llm_timeout"


@pytest.mark.xdist_group(name="explanation_metrics")
class TestExplanationAnalysisMetrics:
    """Tests for per-analysis-type metrics."""

    def teardown_method(self) -> None:
        """Force GC to prevent mock accumulation in xdist workers."""
        gc.collect()

    def test_record_explanation_analysis_task(self) -> None:
        """Test recording individual analysis task metrics."""
        from mcp_server_langgraph.agents.metrics import record_explanation_analysis_task

        with patch("mcp_server_langgraph.agents.metrics.explanation_analysis_counter") as mock_counter:
            with patch("mcp_server_langgraph.agents.metrics.explanation_analysis_duration_histogram") as mock_histogram:
                record_explanation_analysis_task(
                    analysis_type="uncertainty_analysis",
                    duration_ms=45.0,
                    success=True,
                )

                mock_counter.add.assert_called_once()
                counter_args = mock_counter.add.call_args
                assert counter_args[0][1]["analysis_type"] == "uncertainty_analysis"
                assert counter_args[0][1]["success"] == "true"

                mock_histogram.record.assert_called_once()
                hist_args = mock_histogram.record.call_args
                assert hist_args[0][0] == 45.0
                assert hist_args[0][1]["analysis_type"] == "uncertainty_analysis"

    def test_record_all_analysis_types(self) -> None:
        """Test recording metrics for all analysis types."""
        from mcp_server_langgraph.agents.metrics import record_explanation_analysis_task

        analysis_types = [
            "uncertainty_analysis",
            "risk_analysis",
            "alternatives_analysis",
            "evidence_extraction",
        ]

        with patch("mcp_server_langgraph.agents.metrics.explanation_analysis_counter") as mock_counter:
            for analysis_type in analysis_types:
                record_explanation_analysis_task(
                    analysis_type=analysis_type,
                    duration_ms=30.0,
                    success=True,
                )

            assert mock_counter.add.call_count == 4


@pytest.mark.xdist_group(name="explanation_metrics")
class TestExplanationOrchestratorMetrics:
    """Tests for explanation orchestrator-level metrics."""

    def teardown_method(self) -> None:
        """Force GC to prevent mock accumulation in xdist workers."""
        gc.collect()

    def test_record_explanation_orchestration(self) -> None:
        """Test recording full orchestration metrics."""
        from mcp_server_langgraph.agents.metrics import record_explanation_orchestration

        with patch("mcp_server_langgraph.agents.metrics.explanation_orchestration_counter") as mock_counter:
            with patch("mcp_server_langgraph.agents.metrics.explanation_orchestration_duration_histogram") as mock_histogram:
                record_explanation_orchestration(
                    task_count=4,
                    successful_count=4,
                    duration_ms=120.0,
                    success=True,
                )

                mock_counter.add.assert_called()
                mock_histogram.record.assert_called_once()

    def test_record_explanation_orchestration_partial_failure(self) -> None:
        """Test recording partial failure metrics."""
        from mcp_server_langgraph.agents.metrics import record_explanation_orchestration

        with patch("mcp_server_langgraph.agents.metrics.explanation_orchestration_counter") as mock_counter:
            record_explanation_orchestration(
                task_count=4,
                successful_count=3,
                duration_ms=100.0,
                success=True,  # Still overall success
            )

            # Should record both successful and failed task counts
            assert mock_counter.add.call_count >= 1
