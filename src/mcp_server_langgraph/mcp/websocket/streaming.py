"""
MCP WebSocket Streaming Support.

This module provides streaming tool call handling and metrics collection
for MCP WebSocket connections.

Migrated from: api.v1.mcp_websocket
"""

from __future__ import annotations

import logging
import uuid
from dataclasses import dataclass
from datetime import datetime, UTC
from typing import Any, Callable, TYPE_CHECKING

if TYPE_CHECKING:
    from mcp_server_langgraph.mcp.websocket.connection_manager import ConnectionManager

logger = logging.getLogger(__name__)


def _utc_now() -> datetime:
    """Return current UTC time with timezone awareness."""
    return datetime.now(UTC)


@dataclass
class StreamStats:
    """Statistics for a single stream."""

    chunk_count: int = 0
    total_bytes: int = 0
    start_time: datetime | None = None
    end_time: datetime | None = None

    @property
    def avg_chunk_size(self) -> float:
        """Calculate average chunk size."""
        if self.chunk_count == 0:
            return 0.0
        return self.total_bytes / self.chunk_count

    @property
    def duration_ms(self) -> float:
        """Calculate duration in milliseconds."""
        if self.start_time is None or self.end_time is None:
            return 0.0
        return (self.end_time - self.start_time).total_seconds() * 1000


class StreamingMetricsCollector:
    """
    Collects metrics for streaming tool calls.

    Tracks chunks per stream, total bytes, average chunk size,
    and stream duration for observability.
    """

    def __init__(self) -> None:
        """Initialize the streaming metrics collector."""
        self._streams: dict[str, StreamStats] = {}

    def record_stream_start(self, stream_id: str) -> None:
        """
        Record the start of a stream.

        Args:
            stream_id: Unique identifier for the stream.
        """
        self._streams[stream_id] = StreamStats(start_time=_utc_now())

    def record_chunk(self, stream_id: str, chunk_size: int) -> None:
        """
        Record a chunk being sent.

        Args:
            stream_id: Unique identifier for the stream.
            chunk_size: Size of the chunk in bytes.
        """
        if stream_id not in self._streams:
            self._streams[stream_id] = StreamStats()
        stats = self._streams[stream_id]
        stats.chunk_count += 1
        stats.total_bytes += chunk_size

    def record_stream_end(self, stream_id: str) -> None:
        """
        Record the end of a stream.

        Args:
            stream_id: Unique identifier for the stream.
        """
        if stream_id in self._streams:
            self._streams[stream_id].end_time = _utc_now()

    def is_stream_active(self, stream_id: str) -> bool:
        """
        Check if a stream is active (started but not ended).

        Args:
            stream_id: Unique identifier for the stream.

        Returns:
            True if stream is active, False otherwise.
        """
        if stream_id not in self._streams:
            return False
        stats = self._streams[stream_id]
        return stats.start_time is not None and stats.end_time is None

    def get_stream_stats(self, stream_id: str) -> dict[str, Any]:
        """
        Get statistics for a specific stream.

        Args:
            stream_id: Unique identifier for the stream.

        Returns:
            Dictionary with chunk_count, total_bytes, avg_chunk_size, duration_ms.
        """
        if stream_id not in self._streams:
            return {
                "chunk_count": 0,
                "total_bytes": 0,
                "avg_chunk_size": 0.0,
                "duration_ms": 0.0,
            }
        stats = self._streams[stream_id]
        return {
            "chunk_count": stats.chunk_count,
            "total_bytes": stats.total_bytes,
            "avg_chunk_size": stats.avg_chunk_size,
            "duration_ms": stats.duration_ms,
        }

    def get_aggregate_stats(self) -> dict[str, Any]:
        """
        Get aggregate statistics across all streams.

        Returns:
            Dictionary with total_streams, total_chunks, total_bytes.
        """
        total_streams = len(self._streams)
        total_chunks = sum(s.chunk_count for s in self._streams.values())
        total_bytes = sum(s.total_bytes for s in self._streams.values())

        return {
            "total_streams": total_streams,
            "total_chunks": total_chunks,
            "total_bytes": total_bytes,
        }

    def cleanup_old_streams(self, max_age_seconds: float) -> int:
        """
        Remove completed streams older than max_age_seconds.

        Active streams (without end_time) are never removed.

        Args:
            max_age_seconds: Maximum age in seconds for completed streams.
                            Use 0 to remove all completed streams.

        Returns:
            Number of streams removed.
        """
        now = _utc_now()
        to_remove: list[str] = []

        for stream_id, stats in self._streams.items():
            # Skip active streams (no end_time)
            if stats.end_time is None:
                continue

            # Check age
            age_seconds = (now - stats.end_time).total_seconds()
            if age_seconds >= max_age_seconds:
                to_remove.append(stream_id)

        for stream_id in to_remove:
            del self._streams[stream_id]

        return len(to_remove)


# Global streaming metrics collector instance
streaming_metrics_collector = StreamingMetricsCollector()


class StreamingToolCallHandler:
    """
    Handles streaming tool calls by emitting MCP streaming notifications.

    Wraps an AuthenticatedMCPHandler and emits $/streaming/start, $/streaming/chunk,
    and $/streaming/end notifications during streaming tool execution.

    Usage:
        async def send_notification(n):
            await websocket.send_json(n)

        streaming_handler = StreamingToolCallHandler(
            mcp_handler=handler,
            send_notification=send_notification,
        )
        result = await streaming_handler.handle_streaming_call(
            message_id=1,
            tool_name="langgraph-run",
            arguments={"query": "test"},
        )
    """

    def __init__(
        self,
        mcp_handler: Any,
        send_notification: Callable[[dict[str, Any]], Any],
        metrics_collector: StreamingMetricsCollector | None = None,
        outbound_rate_limiter: Any | None = None,
        connection_manager: ConnectionManager | None = None,
        session_id: str | None = None,
        max_chunk_size: int | None = None,
    ) -> None:
        """
        Initialize the streaming tool call handler.

        Args:
            mcp_handler: The authenticated MCP handler for tool execution.
            send_notification: Async callback to send notifications to client.
            metrics_collector: Optional metrics collector for stream statistics.
            outbound_rate_limiter: Optional rate limiter for outbound notifications.
            connection_manager: Optional connection manager for activity tracking.
            session_id: Optional session ID for activity updates.
            max_chunk_size: Optional max chunk size in bytes. Chunks larger than this are truncated.
        """
        self.mcp_handler = mcp_handler
        self.send_notification = send_notification
        self.metrics_collector = metrics_collector
        self.outbound_rate_limiter = outbound_rate_limiter
        self.connection_manager = connection_manager
        self.session_id = session_id
        self.max_chunk_size = max_chunk_size
        self._stream_counter = 0
        self._client_disconnected = False

    def _generate_stream_id(self) -> str:
        """Generate a unique stream ID."""
        self._stream_counter += 1
        return f"stream-{uuid.uuid4().hex[:12]}-{self._stream_counter}"

    async def handle_streaming_call(
        self,
        message_id: int,
        tool_name: str,
        arguments: dict[str, Any],
    ) -> dict[str, Any]:
        """
        Handle a streaming tool call.

        Emits streaming notifications and returns the final result.
        Handles WebSocket disconnection gracefully without raising.

        Args:
            message_id: The JSON-RPC message ID (toolCallId).
            tool_name: Name of the tool to execute.
            arguments: Tool arguments.

        Returns:
            Result dict with content and isError flag.
        """
        stream_id = self._generate_stream_id()
        collected_content: list[dict[str, Any]] = []
        is_error = False
        self._client_disconnected = False

        # Record stream start if metrics collector is provided
        if self.metrics_collector:
            self.metrics_collector.record_stream_start(stream_id)

        try:
            # Send stream start notification
            start_notification = {
                "jsonrpc": "2.0",
                "method": "$/streaming/start",
                "params": {
                    "streamId": stream_id,
                    "toolCallId": message_id,
                },
            }
            await self._send_with_rate_limit(start_notification)

            # Execute tool with streaming
            async for chunk in self.mcp_handler.execute_tool_streaming(tool_name, arguments):
                if self._client_disconnected:
                    break

                # Apply chunk size limit if configured
                chunk_content = chunk.get("text", "")
                if self.max_chunk_size and len(chunk_content) > self.max_chunk_size:
                    chunk_content = chunk_content[: self.max_chunk_size]
                    chunk = {**chunk, "text": chunk_content, "truncated": True}

                # Record chunk metrics
                if self.metrics_collector:
                    self.metrics_collector.record_chunk(stream_id, len(chunk_content))

                # Send chunk notification
                chunk_notification = {
                    "jsonrpc": "2.0",
                    "method": "$/streaming/chunk",
                    "params": {
                        "streamId": stream_id,
                        "content": chunk,
                    },
                }
                await self._send_with_rate_limit(chunk_notification)

                # Collect content
                collected_content.append(chunk)

                # Update connection activity
                if self.connection_manager and self.session_id:
                    self.connection_manager.update_activity(self.session_id)

        except Exception as e:
            logger.exception(f"Error during streaming tool call: {e}")
            is_error = True
            collected_content.append({"type": "text", "text": str(e)})

        finally:
            # Record stream end
            if self.metrics_collector:
                self.metrics_collector.record_stream_end(stream_id)

            # Send stream end notification (if client still connected)
            if not self._client_disconnected:
                try:
                    end_notification = {
                        "jsonrpc": "2.0",
                        "method": "$/streaming/end",
                        "params": {
                            "streamId": stream_id,
                        },
                    }
                    await self._send_with_rate_limit(end_notification)
                except Exception:
                    pass  # Ignore errors when sending end notification

        return {
            "content": collected_content,
            "isError": is_error,
        }

    async def _send_with_rate_limit(self, notification: dict[str, Any]) -> None:
        """
        Send a notification with optional rate limiting.

        Args:
            notification: The notification to send.
        """
        try:
            if self.outbound_rate_limiter:
                await self.outbound_rate_limiter.check_and_wait()
            await self.send_notification(notification)
        except Exception as e:
            logger.warning(f"Failed to send notification: {e}")
            self._client_disconnected = True
