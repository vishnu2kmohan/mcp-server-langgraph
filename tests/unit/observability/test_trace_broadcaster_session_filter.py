"""
Tests for TraceBroadcaster session_id filtering.

TDD: These tests verify session-scoped filtering for DevTools integration.
"""

from __future__ import annotations

import gc
from unittest.mock import AsyncMock, MagicMock

import pytest

# Module-level markers
pytestmark = [
    pytest.mark.unit,
    pytest.mark.observability,
    pytest.mark.xdist_group(name="trace_broadcaster_session"),
]


def teardown_module() -> None:
    """Force GC to prevent mock accumulation in xdist workers."""
    gc.collect()


class TestTraceBroadcasterSessionFilter:
    """Tests for session_id filtering in TraceBroadcaster."""

    def teardown_method(self) -> None:
        """Force GC to prevent mock accumulation in xdist workers."""
        gc.collect()

    @pytest.mark.asyncio
    async def test_filter_with_session_id_matches_span(self) -> None:
        """
        GIVEN a TraceFilter with session_id
        WHEN a span with matching session_id is broadcast
        THEN the subscriber should receive the span.
        """
        from mcp_server_langgraph.observability.trace_broadcaster import (
            TraceBroadcaster,
            TraceFilter,
        )

        broadcaster = TraceBroadcaster()
        mock_ws = MagicMock()
        mock_ws.send_json = AsyncMock(return_value=None)

        # Subscribe with session_id filter
        await broadcaster.subscribe(
            mock_ws,
            filter_=TraceFilter(session_id="session-123"),
        )

        # Broadcast span with matching session_id
        await broadcaster.broadcast_span(
            {
                "trace_id": "trace-abc",
                "span_id": "span-def",
                "service_name": "my-service",
                "operation_name": "process",
                "session_id": "session-123",
            }
        )

        mock_ws.send_json.assert_called_once()
        call_args = mock_ws.send_json.call_args[0][0]
        assert call_args["type"] == "trace_span"
        assert call_args["payload"]["session_id"] == "session-123"

    @pytest.mark.asyncio
    async def test_filter_with_session_id_rejects_non_matching_span(self) -> None:
        """
        GIVEN a TraceFilter with session_id
        WHEN a span with different session_id is broadcast
        THEN the subscriber should NOT receive the span.
        """
        from mcp_server_langgraph.observability.trace_broadcaster import (
            TraceBroadcaster,
            TraceFilter,
        )

        broadcaster = TraceBroadcaster()
        mock_ws = MagicMock()
        mock_ws.send_json = AsyncMock(return_value=None)

        # Subscribe with session_id filter
        await broadcaster.subscribe(
            mock_ws,
            filter_=TraceFilter(session_id="session-123"),
        )

        # Broadcast span with different session_id
        await broadcaster.broadcast_span(
            {
                "trace_id": "trace-abc",
                "span_id": "span-def",
                "service_name": "my-service",
                "operation_name": "process",
                "session_id": "session-456",  # Different session
            }
        )

        mock_ws.send_json.assert_not_called()

    @pytest.mark.asyncio
    async def test_filter_without_session_id_receives_all_spans(self) -> None:
        """
        GIVEN a TraceFilter without session_id (None)
        WHEN any span is broadcast
        THEN the subscriber should receive all spans.
        """
        from mcp_server_langgraph.observability.trace_broadcaster import (
            TraceBroadcaster,
            TraceFilter,
        )

        broadcaster = TraceBroadcaster()
        mock_ws = MagicMock()
        mock_ws.send_json = AsyncMock(return_value=None)

        # Subscribe without session_id filter
        await broadcaster.subscribe(
            mock_ws,
            filter_=TraceFilter(),  # No session filter
        )

        # Broadcast span with session_id
        await broadcaster.broadcast_span(
            {
                "trace_id": "trace-abc",
                "session_id": "session-123",
            }
        )

        # Broadcast span without session_id
        await broadcaster.broadcast_span(
            {
                "trace_id": "trace-def",
            }
        )

        assert mock_ws.send_json.call_count == 2

    @pytest.mark.asyncio
    async def test_session_combined_with_other_filters(self) -> None:
        """
        GIVEN a TraceFilter with session_id AND service_name
        WHEN spans are broadcast
        THEN only spans matching BOTH criteria should be received.
        """
        from mcp_server_langgraph.observability.trace_broadcaster import (
            TraceBroadcaster,
            TraceFilter,
        )

        broadcaster = TraceBroadcaster()
        mock_ws = MagicMock()
        mock_ws.send_json = AsyncMock(return_value=None)

        # Subscribe with combined filter
        await broadcaster.subscribe(
            mock_ws,
            filter_=TraceFilter(
                session_id="session-123",
                service_name="my-service",
            ),
        )

        # Matches both
        await broadcaster.broadcast_span(
            {
                "trace_id": "trace-1",
                "session_id": "session-123",
                "service_name": "my-service",
            }
        )

        # Wrong session_id
        await broadcaster.broadcast_span(
            {
                "trace_id": "trace-2",
                "session_id": "session-456",
                "service_name": "my-service",
            }
        )

        # Wrong service_name
        await broadcaster.broadcast_span(
            {
                "trace_id": "trace-3",
                "session_id": "session-123",
                "service_name": "other-service",
            }
        )

        # Only first span should be received
        assert mock_ws.send_json.call_count == 1
        call_args = mock_ws.send_json.call_args[0][0]
        assert call_args["payload"]["trace_id"] == "trace-1"
