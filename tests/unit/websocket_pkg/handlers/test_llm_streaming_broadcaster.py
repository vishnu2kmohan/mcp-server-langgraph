"""
Tests for LLMStreamingBroadcaster.

TDD: These tests define the expected behavior for real-time LLM streaming
observability in the DevTools panel.

The LLMStreamingBroadcaster solves the gap where:
- Streaming metrics (TTFC, inter-chunk latency) are recorded to Prometheus
- BUT not pushed to WebSocket for real-time visibility

This broadcaster enables:
- Real-time TTFC visibility while streaming
- Per-chunk metrics pushed via WebSocket
- Streaming performance monitoring in DevTools
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
    pytest.mark.xdist_group(name="llm_streaming_broadcaster"),
]


def teardown_module() -> None:
    """Force GC to prevent mock accumulation in xdist workers."""
    gc.collect()


class TestLLMStreamingBroadcasterSubscription:
    """
    Tests for LLMStreamingBroadcaster subscription management.
    """

    def teardown_method(self) -> None:
        """Force GC to prevent mock accumulation in xdist workers."""
        gc.collect()

    @pytest.mark.asyncio
    async def test_subscribe_adds_websocket_to_subscribers(self) -> None:
        """
        GIVEN a LLMStreamingBroadcaster
        WHEN subscribe is called with a websocket
        THEN the websocket should be added to subscribers.
        """
        from mcp_server_langgraph.websocket.handlers.llm_streaming_broadcaster import (
            LLMStreamingBroadcaster,
        )

        broadcaster = LLMStreamingBroadcaster()
        mock_websocket = MagicMock()

        await broadcaster.subscribe(mock_websocket, session_id="session-123")

        assert broadcaster.subscriber_count == 1

    @pytest.mark.asyncio
    async def test_unsubscribe_removes_websocket(self) -> None:
        """
        GIVEN a LLMStreamingBroadcaster with a subscribed websocket
        WHEN unsubscribe is called
        THEN the websocket should be removed from subscribers.
        """
        from mcp_server_langgraph.websocket.handlers.llm_streaming_broadcaster import (
            LLMStreamingBroadcaster,
        )

        broadcaster = LLMStreamingBroadcaster()
        mock_websocket = MagicMock()

        await broadcaster.subscribe(mock_websocket, session_id="session-123")
        assert broadcaster.subscriber_count == 1

        await broadcaster.unsubscribe(mock_websocket)
        assert broadcaster.subscriber_count == 0


class TestLLMStreamingBroadcasterStreamingStart:
    """
    Tests for broadcasting streaming start events.
    """

    def teardown_method(self) -> None:
        """Force GC to prevent mock accumulation in xdist workers."""
        gc.collect()

    @pytest.mark.asyncio
    async def test_broadcast_streaming_started(self) -> None:
        """
        GIVEN a LLMStreamingBroadcaster with subscribers
        WHEN broadcast_streaming_started is called
        THEN subscribers should receive streaming_started event.
        """
        from mcp_server_langgraph.websocket.handlers.llm_streaming_broadcaster import (
            LLMStreamingBroadcaster,
        )

        broadcaster = LLMStreamingBroadcaster()
        mock_ws = MagicMock()
        mock_ws.send_json = AsyncMock()

        await broadcaster.subscribe(mock_ws, session_id="session-123")

        await broadcaster.broadcast_streaming_started(
            stream_id="stream-abc",
            session_id="session-123",
            model="gpt-4",
            provider="openai",
        )

        mock_ws.send_json.assert_called_once()
        call_args = mock_ws.send_json.call_args[0][0]

        assert call_args["type"] == "streaming_started"
        assert call_args["payload"]["stream_id"] == "stream-abc"
        assert call_args["payload"]["model"] == "gpt-4"
        assert call_args["payload"]["provider"] == "openai"
        assert "timestamp" in call_args["payload"]


class TestLLMStreamingBroadcasterFirstChunk:
    """
    Tests for broadcasting first chunk (TTFC) events.
    """

    def teardown_method(self) -> None:
        """Force GC to prevent mock accumulation in xdist workers."""
        gc.collect()

    @pytest.mark.asyncio
    async def test_broadcast_first_chunk_with_ttfc(self) -> None:
        """
        GIVEN a LLMStreamingBroadcaster with subscribers
        WHEN broadcast_first_chunk is called
        THEN subscribers should receive first_chunk event with TTFC.
        """
        from mcp_server_langgraph.websocket.handlers.llm_streaming_broadcaster import (
            LLMStreamingBroadcaster,
        )

        broadcaster = LLMStreamingBroadcaster()
        mock_ws = MagicMock()
        mock_ws.send_json = AsyncMock()

        await broadcaster.subscribe(mock_ws, session_id="session-123")

        await broadcaster.broadcast_first_chunk(
            stream_id="stream-abc",
            session_id="session-123",
            ttfc_ms=150.5,  # 150.5ms TTFC
            chunk_size=42,
        )

        mock_ws.send_json.assert_called_once()
        call_args = mock_ws.send_json.call_args[0][0]

        assert call_args["type"] == "first_chunk"
        assert call_args["payload"]["stream_id"] == "stream-abc"
        assert call_args["payload"]["ttfc_ms"] == 150.5
        assert call_args["payload"]["chunk_size"] == 42


class TestLLMStreamingBroadcasterChunkReceived:
    """
    Tests for broadcasting chunk received events.
    """

    def teardown_method(self) -> None:
        """Force GC to prevent mock accumulation in xdist workers."""
        gc.collect()

    @pytest.mark.asyncio
    async def test_broadcast_chunk_received(self) -> None:
        """
        GIVEN a LLMStreamingBroadcaster with subscribers
        WHEN broadcast_chunk_received is called
        THEN subscribers should receive chunk_received event.
        """
        from mcp_server_langgraph.websocket.handlers.llm_streaming_broadcaster import (
            LLMStreamingBroadcaster,
        )

        broadcaster = LLMStreamingBroadcaster()
        mock_ws = MagicMock()
        mock_ws.send_json = AsyncMock()

        await broadcaster.subscribe(mock_ws, session_id="session-123")

        await broadcaster.broadcast_chunk_received(
            stream_id="stream-abc",
            session_id="session-123",
            chunk_index=5,
            chunk_size=25,
            inter_chunk_latency_ms=12.3,
        )

        mock_ws.send_json.assert_called_once()
        call_args = mock_ws.send_json.call_args[0][0]

        assert call_args["type"] == "chunk_received"
        assert call_args["payload"]["stream_id"] == "stream-abc"
        assert call_args["payload"]["chunk_index"] == 5
        assert call_args["payload"]["chunk_size"] == 25
        assert call_args["payload"]["inter_chunk_latency_ms"] == 12.3


class TestLLMStreamingBroadcasterStreamingCompleted:
    """
    Tests for broadcasting streaming completed events.
    """

    def teardown_method(self) -> None:
        """Force GC to prevent mock accumulation in xdist workers."""
        gc.collect()

    @pytest.mark.asyncio
    async def test_broadcast_streaming_completed(self) -> None:
        """
        GIVEN a LLMStreamingBroadcaster with subscribers
        WHEN broadcast_streaming_completed is called
        THEN subscribers should receive streaming_completed event.
        """
        from mcp_server_langgraph.websocket.handlers.llm_streaming_broadcaster import (
            LLMStreamingBroadcaster,
        )

        broadcaster = LLMStreamingBroadcaster()
        mock_ws = MagicMock()
        mock_ws.send_json = AsyncMock()

        await broadcaster.subscribe(mock_ws, session_id="session-123")

        await broadcaster.broadcast_streaming_completed(
            stream_id="stream-abc",
            session_id="session-123",
            status="success",
            total_duration_ms=2500.0,
            total_chunks=25,
            total_tokens=150,
            estimated_cost_usd=0.0023,
        )

        mock_ws.send_json.assert_called_once()
        call_args = mock_ws.send_json.call_args[0][0]

        assert call_args["type"] == "streaming_completed"
        assert call_args["payload"]["stream_id"] == "stream-abc"
        assert call_args["payload"]["status"] == "success"
        assert call_args["payload"]["total_duration_ms"] == 2500.0
        assert call_args["payload"]["total_chunks"] == 25
        assert call_args["payload"]["total_tokens"] == 150
        assert call_args["payload"]["estimated_cost_usd"] == 0.0023


class TestLLMStreamingBroadcasterSessionFiltering:
    """
    Tests for session-scoped event filtering.
    """

    def teardown_method(self) -> None:
        """Force GC to prevent mock accumulation in xdist workers."""
        gc.collect()

    @pytest.mark.asyncio
    async def test_events_filtered_by_session_id(self) -> None:
        """
        GIVEN subscribers with different session_id filters
        WHEN broadcast events are called with session_id
        THEN only matching subscribers should receive events.
        """
        from mcp_server_langgraph.websocket.handlers.llm_streaming_broadcaster import (
            LLMStreamingBroadcaster,
        )

        broadcaster = LLMStreamingBroadcaster()

        mock_ws1 = MagicMock()
        mock_ws1.send_json = AsyncMock()
        mock_ws2 = MagicMock()
        mock_ws2.send_json = AsyncMock()

        await broadcaster.subscribe(mock_ws1, session_id="session-A")
        await broadcaster.subscribe(mock_ws2, session_id="session-B")

        await broadcaster.broadcast_streaming_started(
            stream_id="stream-abc",
            session_id="session-A",
            model="gpt-4",
            provider="openai",
        )

        # Only ws1 (session-A) should receive it
        mock_ws1.send_json.assert_called_once()
        mock_ws2.send_json.assert_not_called()


class TestLLMStreamingBroadcasterSingleton:
    """
    Tests for singleton pattern.
    """

    def teardown_method(self) -> None:
        """Force GC to prevent mock accumulation in xdist workers."""
        gc.collect()

    @pytest.mark.asyncio
    async def test_singleton_pattern(self) -> None:
        """
        GIVEN the LLM streaming broadcaster module
        WHEN get_llm_streaming_broadcaster is called multiple times
        THEN it should return the same instance.
        """
        from mcp_server_langgraph.websocket.handlers.llm_streaming_broadcaster import (
            get_llm_streaming_broadcaster,
            reset_llm_streaming_broadcaster,
        )

        reset_llm_streaming_broadcaster()

        broadcaster1 = get_llm_streaming_broadcaster()
        broadcaster2 = get_llm_streaming_broadcaster()

        assert broadcaster1 is broadcaster2

        reset_llm_streaming_broadcaster()


class TestLLMStreamingBroadcasterMetricsIntegration:
    """
    Tests for integration with MetricsBroadcaster.
    """

    def teardown_method(self) -> None:
        """Force GC to prevent mock accumulation in xdist workers."""
        gc.collect()

    @pytest.mark.asyncio
    async def test_streaming_events_include_model_provider(self) -> None:
        """
        GIVEN LLM streaming events
        WHEN broadcast
        THEN they should include model and provider for metric labeling.
        """
        from mcp_server_langgraph.websocket.handlers.llm_streaming_broadcaster import (
            LLMStreamingBroadcaster,
        )

        broadcaster = LLMStreamingBroadcaster()
        mock_ws = MagicMock()
        mock_ws.send_json = AsyncMock()

        await broadcaster.subscribe(mock_ws, session_id="session-123")

        await broadcaster.broadcast_streaming_started(
            stream_id="stream-abc",
            session_id="session-123",
            model="claude-3-opus",
            provider="anthropic",
        )

        call_args = mock_ws.send_json.call_args[0][0]
        assert call_args["payload"]["model"] == "claude-3-opus"
        assert call_args["payload"]["provider"] == "anthropic"

    @pytest.mark.asyncio
    async def test_first_chunk_emits_to_metrics_broadcaster(self) -> None:
        """
        GIVEN a LLMStreamingBroadcaster with metrics_broadcaster
        WHEN first_chunk is broadcast
        THEN it should also emit TTFC metric to metrics broadcaster.
        """
        from mcp_server_langgraph.websocket.handlers.llm_streaming_broadcaster import (
            LLMStreamingBroadcaster,
        )
        from mcp_server_langgraph.websocket.handlers.metrics_broadcaster import (
            MetricsBroadcaster,
        )

        metrics_broadcaster = MetricsBroadcaster()
        metrics_ws = MagicMock()
        metrics_ws.send_json = AsyncMock()
        await metrics_broadcaster.subscribe(metrics_ws, session_id="session-123")

        broadcaster = LLMStreamingBroadcaster(metrics_broadcaster=metrics_broadcaster)
        stream_ws = MagicMock()
        stream_ws.send_json = AsyncMock()
        await broadcaster.subscribe(stream_ws, session_id="session-123")

        await broadcaster.broadcast_first_chunk(
            stream_id="stream-abc",
            session_id="session-123",
            ttfc_ms=150.5,
            chunk_size=42,
            model="gpt-4",
            provider="openai",
        )

        # Stream WS receives first_chunk event
        stream_ws.send_json.assert_called_once()

        # Metrics WS receives llm_streaming_ttfc_ms metric
        metrics_ws.send_json.assert_called_once()
        metrics_call = metrics_ws.send_json.call_args[0][0]
        assert metrics_call["type"] == "metric"
        assert metrics_call["payload"]["name"] == "llm_streaming_ttfc_ms"
        assert metrics_call["payload"]["value"] == 150.5
