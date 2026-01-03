"""
Tests for StreamingMetricsContext integration with LLMStreamingBroadcaster.

TDD: These tests verify that streaming metrics are pushed to WebSocket
in real-time alongside Prometheus recording.
"""

from __future__ import annotations

import asyncio
import gc
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

# Module-level markers
pytestmark = [
    pytest.mark.unit,
    pytest.mark.llm,
    pytest.mark.observability,
    pytest.mark.xdist_group(name="streaming_metrics_integration"),
]


def teardown_module() -> None:
    """Force GC to prevent mock accumulation in xdist workers."""
    gc.collect()


class TestStreamingMetricsContextBroadcasterIntegration:
    """Tests for StreamingMetricsContext WebSocket broadcaster integration."""

    def teardown_method(self) -> None:
        """Force GC to prevent mock accumulation in xdist workers."""
        gc.collect()

    def test_context_accepts_session_id_parameter(self) -> None:
        """
        GIVEN StreamingMetricsContext
        WHEN initialized with session_id
        THEN session_id should be stored.
        """
        from mcp_server_langgraph.llm.streaming_metrics import StreamingMetricsContext

        ctx = StreamingMetricsContext(
            model="gpt-4",
            provider="openai",
            session_id="session-123",
        )

        assert ctx.session_id == "session-123"

    def test_context_accepts_stream_id_parameter(self) -> None:
        """
        GIVEN StreamingMetricsContext
        WHEN initialized with stream_id
        THEN stream_id should be stored.
        """
        from mcp_server_langgraph.llm.streaming_metrics import StreamingMetricsContext

        ctx = StreamingMetricsContext(
            model="gpt-4",
            provider="openai",
            stream_id="stream-abc",
        )

        assert ctx.stream_id == "stream-abc"

    def test_context_generates_stream_id_if_not_provided(self) -> None:
        """
        GIVEN StreamingMetricsContext
        WHEN initialized without stream_id
        THEN a stream_id should be auto-generated.
        """
        from mcp_server_langgraph.llm.streaming_metrics import StreamingMetricsContext

        ctx = StreamingMetricsContext(
            model="gpt-4",
            provider="openai",
        )

        assert ctx.stream_id is not None
        assert len(ctx.stream_id) > 0

    @pytest.mark.asyncio
    async def test_start_broadcasts_streaming_started_when_session_id_provided(self) -> None:
        """
        GIVEN StreamingMetricsContext with session_id
        WHEN start() is called
        THEN broadcast_streaming_started should be queued.
        """
        from mcp_server_langgraph.llm.streaming_metrics import StreamingMetricsContext

        mock_broadcaster = MagicMock()
        mock_broadcaster.broadcast_streaming_started = AsyncMock()

        with patch(
            "mcp_server_langgraph.llm.streaming_metrics.get_llm_streaming_broadcaster",
            return_value=mock_broadcaster,
        ):
            ctx = StreamingMetricsContext(
                model="gpt-4",
                provider="openai",
                session_id="session-123",
            )
            ctx.start()

            # Allow async task to execute
            await asyncio.sleep(0.01)

            mock_broadcaster.broadcast_streaming_started.assert_called_once()
            call_kwargs = mock_broadcaster.broadcast_streaming_started.call_args[1]
            assert call_kwargs["session_id"] == "session-123"
            assert call_kwargs["model"] == "gpt-4"
            assert call_kwargs["provider"] == "openai"

    @pytest.mark.asyncio
    async def test_start_does_not_broadcast_when_no_session_id(self) -> None:
        """
        GIVEN StreamingMetricsContext without session_id
        WHEN start() is called
        THEN broadcast_streaming_started should NOT be called.
        """
        from mcp_server_langgraph.llm.streaming_metrics import StreamingMetricsContext

        mock_broadcaster = MagicMock()
        mock_broadcaster.broadcast_streaming_started = AsyncMock()

        with patch(
            "mcp_server_langgraph.llm.streaming_metrics.get_llm_streaming_broadcaster",
            return_value=mock_broadcaster,
        ):
            ctx = StreamingMetricsContext(
                model="gpt-4",
                provider="openai",
                # No session_id
            )
            ctx.start()

            await asyncio.sleep(0.01)

            mock_broadcaster.broadcast_streaming_started.assert_not_called()

    @pytest.mark.asyncio
    async def test_record_first_chunk_broadcasts_with_ttfc(self) -> None:
        """
        GIVEN StreamingMetricsContext with session_id that has been started
        WHEN record_first_chunk() is called
        THEN broadcast_first_chunk should be called with TTFC.
        """
        from mcp_server_langgraph.llm.streaming_metrics import StreamingMetricsContext

        mock_broadcaster = MagicMock()
        mock_broadcaster.broadcast_streaming_started = AsyncMock()
        mock_broadcaster.broadcast_first_chunk = AsyncMock()

        with patch(
            "mcp_server_langgraph.llm.streaming_metrics.get_llm_streaming_broadcaster",
            return_value=mock_broadcaster,
        ):
            ctx = StreamingMetricsContext(
                model="gpt-4",
                provider="openai",
                session_id="session-123",
            )
            ctx.start()
            await asyncio.sleep(0.01)

            ctx.record_first_chunk()
            await asyncio.sleep(0.01)

            mock_broadcaster.broadcast_first_chunk.assert_called_once()
            call_kwargs = mock_broadcaster.broadcast_first_chunk.call_args[1]
            assert call_kwargs["session_id"] == "session-123"
            assert call_kwargs["ttfc_ms"] > 0  # Should be positive
            assert call_kwargs["model"] == "gpt-4"
            assert call_kwargs["provider"] == "openai"

    @pytest.mark.asyncio
    async def test_record_chunk_broadcasts_chunk_received(self) -> None:
        """
        GIVEN StreamingMetricsContext that has recorded first chunk
        WHEN record_chunk() is called
        THEN broadcast_chunk_received should be called.
        """
        from mcp_server_langgraph.llm.streaming_metrics import StreamingMetricsContext

        mock_broadcaster = MagicMock()
        mock_broadcaster.broadcast_streaming_started = AsyncMock()
        mock_broadcaster.broadcast_first_chunk = AsyncMock()
        mock_broadcaster.broadcast_chunk_received = AsyncMock()

        with patch(
            "mcp_server_langgraph.llm.streaming_metrics.get_llm_streaming_broadcaster",
            return_value=mock_broadcaster,
        ):
            ctx = StreamingMetricsContext(
                model="gpt-4",
                provider="openai",
                session_id="session-123",
            )
            ctx.start()
            await asyncio.sleep(0.01)

            ctx.record_first_chunk()
            await asyncio.sleep(0.01)

            ctx.record_chunk()
            await asyncio.sleep(0.01)

            mock_broadcaster.broadcast_chunk_received.assert_called_once()
            call_kwargs = mock_broadcaster.broadcast_chunk_received.call_args[1]
            assert call_kwargs["session_id"] == "session-123"
            assert call_kwargs["chunk_index"] == 2  # Second chunk
            assert call_kwargs["inter_chunk_latency_ms"] >= 0

    @pytest.mark.asyncio
    async def test_finalize_broadcasts_streaming_completed(self) -> None:
        """
        GIVEN StreamingMetricsContext that has been used for streaming
        WHEN finalize() is called
        THEN broadcast_streaming_completed should be called.
        """
        from mcp_server_langgraph.llm.streaming_metrics import StreamingMetricsContext

        mock_broadcaster = MagicMock()
        mock_broadcaster.broadcast_streaming_started = AsyncMock()
        mock_broadcaster.broadcast_first_chunk = AsyncMock()
        mock_broadcaster.broadcast_streaming_completed = AsyncMock()

        with patch(
            "mcp_server_langgraph.llm.streaming_metrics.get_llm_streaming_broadcaster",
            return_value=mock_broadcaster,
        ):
            ctx = StreamingMetricsContext(
                model="gpt-4",
                provider="openai",
                session_id="session-123",
            )
            ctx.start()
            await asyncio.sleep(0.01)

            ctx.record_first_chunk()
            await asyncio.sleep(0.01)

            ctx.finalize(status="success")
            await asyncio.sleep(0.01)

            mock_broadcaster.broadcast_streaming_completed.assert_called_once()
            call_kwargs = mock_broadcaster.broadcast_streaming_completed.call_args[1]
            assert call_kwargs["session_id"] == "session-123"
            assert call_kwargs["status"] == "success"
            assert call_kwargs["total_chunks"] == 1
            assert call_kwargs["total_duration_ms"] > 0

    @pytest.mark.asyncio
    async def test_finalize_with_error_status(self) -> None:
        """
        GIVEN StreamingMetricsContext
        WHEN finalize() is called with error status
        THEN broadcast should include error status.
        """
        from mcp_server_langgraph.llm.streaming_metrics import StreamingMetricsContext

        mock_broadcaster = MagicMock()
        mock_broadcaster.broadcast_streaming_started = AsyncMock()
        mock_broadcaster.broadcast_streaming_completed = AsyncMock()

        with patch(
            "mcp_server_langgraph.llm.streaming_metrics.get_llm_streaming_broadcaster",
            return_value=mock_broadcaster,
        ):
            ctx = StreamingMetricsContext(
                model="gpt-4",
                provider="openai",
                session_id="session-123",
            )
            ctx.start()
            await asyncio.sleep(0.01)

            ctx.finalize(status="error")
            await asyncio.sleep(0.01)

            call_kwargs = mock_broadcaster.broadcast_streaming_completed.call_args[1]
            assert call_kwargs["status"] == "error"

    @pytest.mark.asyncio
    async def test_broadcast_failure_does_not_affect_prometheus_metrics(self) -> None:
        """
        GIVEN StreamingMetricsContext with session_id
        WHEN broadcaster fails
        THEN Prometheus metrics should still be recorded.
        """
        from mcp_server_langgraph.llm.streaming_metrics import StreamingMetricsContext

        mock_broadcaster = MagicMock()
        mock_broadcaster.broadcast_streaming_started = AsyncMock(side_effect=Exception("WebSocket error"))

        with patch(
            "mcp_server_langgraph.llm.streaming_metrics.get_llm_streaming_broadcaster",
            return_value=mock_broadcaster,
        ):
            ctx = StreamingMetricsContext(
                model="gpt-4",
                provider="openai",
                session_id="session-123",
            )

            # Should not raise
            ctx.start()
            await asyncio.sleep(0.01)

            # Context should still work
            assert ctx._start_time is not None
