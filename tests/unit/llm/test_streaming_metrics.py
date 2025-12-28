"""
Tests for LLM streaming metrics.

TDD: Tests written FIRST before implementation.

Metrics to track:
- llm_streaming_ttfc_seconds: Time To First Chunk histogram
- llm_streaming_inter_chunk_latency_seconds: Inter-chunk latency histogram
- llm_streaming_duration_seconds: Total streaming duration histogram
- llm_streaming_chunks_total: Counter of chunks emitted per stream
"""

from __future__ import annotations

import gc

import pytest

pytestmark = [pytest.mark.unit, pytest.mark.llm, pytest.mark.metrics]


@pytest.mark.xdist_group(name="streaming_metrics")
class TestStreamingMetricsModule:
    """Tests for streaming metrics module existence."""

    def teardown_method(self) -> None:
        """Force GC to prevent mock accumulation in xdist workers."""
        gc.collect()

    def test_streaming_metrics_module_exists(self) -> None:
        """
        GIVEN the llm package
        WHEN importing streaming_metrics
        THEN should be available.
        """
        from mcp_server_langgraph.llm import streaming_metrics

        assert streaming_metrics is not None

    def test_record_ttfc_function_exists(self) -> None:
        """
        GIVEN streaming_metrics module
        WHEN checking for record_ttfc function
        THEN should be available.
        """
        from mcp_server_langgraph.llm.streaming_metrics import record_ttfc

        assert callable(record_ttfc)

    def test_record_inter_chunk_latency_function_exists(self) -> None:
        """
        GIVEN streaming_metrics module
        WHEN checking for record_inter_chunk_latency function
        THEN should be available.
        """
        from mcp_server_langgraph.llm.streaming_metrics import record_inter_chunk_latency

        assert callable(record_inter_chunk_latency)

    def test_record_streaming_duration_function_exists(self) -> None:
        """
        GIVEN streaming_metrics module
        WHEN checking for record_streaming_duration function
        THEN should be available.
        """
        from mcp_server_langgraph.llm.streaming_metrics import record_streaming_duration

        assert callable(record_streaming_duration)

    def test_record_chunk_count_function_exists(self) -> None:
        """
        GIVEN streaming_metrics module
        WHEN checking for record_chunk_count function
        THEN should be available.
        """
        from mcp_server_langgraph.llm.streaming_metrics import record_chunk_count

        assert callable(record_chunk_count)


@pytest.mark.xdist_group(name="streaming_metrics")
class TestRecordTTFC:
    """Tests for Time To First Chunk recording."""

    def teardown_method(self) -> None:
        """Force GC to prevent mock accumulation in xdist workers."""
        gc.collect()

    def test_record_ttfc_with_valid_values(self) -> None:
        """
        GIVEN valid model and TTFC value
        WHEN calling record_ttfc
        THEN should not raise exception.
        """
        from mcp_server_langgraph.llm.streaming_metrics import record_ttfc

        # Should not raise
        record_ttfc(model="gpt-4", ttfc_seconds=0.5, provider="openai")

    def test_record_ttfc_with_zero_value(self) -> None:
        """
        GIVEN TTFC of zero
        WHEN calling record_ttfc
        THEN should handle gracefully.
        """
        from mcp_server_langgraph.llm.streaming_metrics import record_ttfc

        # Zero is valid (instant first chunk)
        record_ttfc(model="gpt-4", ttfc_seconds=0.0, provider="openai")

    def test_record_ttfc_with_high_latency(self) -> None:
        """
        GIVEN high TTFC value
        WHEN calling record_ttfc
        THEN should record without error.
        """
        from mcp_server_langgraph.llm.streaming_metrics import record_ttfc

        # High latency (30 seconds)
        record_ttfc(model="claude-3-opus", ttfc_seconds=30.0, provider="anthropic")


@pytest.mark.xdist_group(name="streaming_metrics")
class TestRecordInterChunkLatency:
    """Tests for inter-chunk latency recording."""

    def teardown_method(self) -> None:
        """Force GC to prevent mock accumulation in xdist workers."""
        gc.collect()

    def test_record_inter_chunk_latency_with_valid_values(self) -> None:
        """
        GIVEN valid model and inter-chunk latency
        WHEN calling record_inter_chunk_latency
        THEN should not raise exception.
        """
        from mcp_server_langgraph.llm.streaming_metrics import record_inter_chunk_latency

        record_inter_chunk_latency(model="gpt-4", latency_seconds=0.05, provider="openai")

    def test_record_inter_chunk_latency_with_small_value(self) -> None:
        """
        GIVEN very small inter-chunk latency
        WHEN calling record_inter_chunk_latency
        THEN should record without error.
        """
        from mcp_server_langgraph.llm.streaming_metrics import record_inter_chunk_latency

        # Very fast chunks (1ms)
        record_inter_chunk_latency(model="gemini-2.0-flash", latency_seconds=0.001, provider="google")


@pytest.mark.xdist_group(name="streaming_metrics")
class TestRecordStreamingDuration:
    """Tests for total streaming duration recording."""

    def teardown_method(self) -> None:
        """Force GC to prevent mock accumulation in xdist workers."""
        gc.collect()

    def test_record_streaming_duration_with_valid_values(self) -> None:
        """
        GIVEN valid model and streaming duration
        WHEN calling record_streaming_duration
        THEN should not raise exception.
        """
        from mcp_server_langgraph.llm.streaming_metrics import record_streaming_duration

        record_streaming_duration(model="gpt-4", duration_seconds=5.5, provider="openai", status="success")

    def test_record_streaming_duration_with_error_status(self) -> None:
        """
        GIVEN streaming that ended with error
        WHEN calling record_streaming_duration
        THEN should record with error status.
        """
        from mcp_server_langgraph.llm.streaming_metrics import record_streaming_duration

        record_streaming_duration(model="claude-3-sonnet", duration_seconds=2.0, provider="anthropic", status="error")


@pytest.mark.xdist_group(name="streaming_metrics")
class TestRecordChunkCount:
    """Tests for chunk count recording."""

    def teardown_method(self) -> None:
        """Force GC to prevent mock accumulation in xdist workers."""
        gc.collect()

    def test_record_chunk_count_with_valid_values(self) -> None:
        """
        GIVEN valid model and chunk count
        WHEN calling record_chunk_count
        THEN should not raise exception.
        """
        from mcp_server_langgraph.llm.streaming_metrics import record_chunk_count

        record_chunk_count(model="gpt-4", count=100, provider="openai")

    def test_record_chunk_count_with_single_chunk(self) -> None:
        """
        GIVEN single chunk stream
        WHEN calling record_chunk_count
        THEN should record correctly.
        """
        from mcp_server_langgraph.llm.streaming_metrics import record_chunk_count

        record_chunk_count(model="gemini-2.0-flash", count=1, provider="google")

    def test_record_chunk_count_with_large_count(self) -> None:
        """
        GIVEN large chunk count
        WHEN calling record_chunk_count
        THEN should record without error.
        """
        from mcp_server_langgraph.llm.streaming_metrics import record_chunk_count

        # Long streaming response (1000 chunks)
        record_chunk_count(model="claude-3-opus", count=1000, provider="anthropic")


@pytest.mark.xdist_group(name="streaming_metrics")
class TestStreamingMetricsContext:
    """Tests for streaming metrics context manager."""

    def teardown_method(self) -> None:
        """Force GC to prevent mock accumulation in xdist workers."""
        gc.collect()

    def test_streaming_metrics_context_exists(self) -> None:
        """
        GIVEN streaming_metrics module
        WHEN checking for StreamingMetricsContext
        THEN should be available.
        """
        from mcp_server_langgraph.llm.streaming_metrics import StreamingMetricsContext

        assert StreamingMetricsContext is not None

    @pytest.mark.asyncio
    async def test_streaming_metrics_context_records_ttfc(self) -> None:
        """
        GIVEN a StreamingMetricsContext
        WHEN first chunk is received
        THEN should record TTFC.
        """
        from mcp_server_langgraph.llm.streaming_metrics import StreamingMetricsContext

        ctx = StreamingMetricsContext(model="gpt-4", provider="openai")
        ctx.start()

        # Simulate receiving first chunk
        ctx.record_first_chunk()

        # TTFC should be recorded
        assert ctx.ttfc_seconds is not None
        assert ctx.ttfc_seconds >= 0

    @pytest.mark.asyncio
    async def test_streaming_metrics_context_records_inter_chunk_latency(self) -> None:
        """
        GIVEN a StreamingMetricsContext
        WHEN multiple chunks are received
        THEN should track inter-chunk latencies.
        """
        import asyncio
        from mcp_server_langgraph.llm.streaming_metrics import StreamingMetricsContext

        ctx = StreamingMetricsContext(model="gpt-4", provider="openai")
        ctx.start()
        ctx.record_first_chunk()

        # Simulate receiving subsequent chunks
        await asyncio.sleep(0.01)
        ctx.record_chunk()
        await asyncio.sleep(0.01)
        ctx.record_chunk()

        assert ctx.chunk_count >= 3  # first + 2 subsequent

    @pytest.mark.asyncio
    async def test_streaming_metrics_context_finalize_records_all_metrics(self) -> None:
        """
        GIVEN a StreamingMetricsContext with recorded chunks
        WHEN finalized
        THEN should emit all metrics.
        """
        from mcp_server_langgraph.llm.streaming_metrics import StreamingMetricsContext

        ctx = StreamingMetricsContext(model="gpt-4", provider="openai")
        ctx.start()
        ctx.record_first_chunk()
        ctx.record_chunk()
        ctx.record_chunk()

        # Finalize
        ctx.finalize(status="success")

        assert ctx.finalized
        assert ctx.duration_seconds is not None
        assert ctx.duration_seconds >= 0
