"""
Streaming Chunk Size and Max Age Tests

TDD RED Phase: Tests for verifying chunk size limits and max age usage.
"""

from __future__ import annotations

import gc
from unittest.mock import AsyncMock, patch

import pytest


pytestmark = [
    pytest.mark.unit,
    pytest.mark.api,
    pytest.mark.websocket,
]


@pytest.mark.xdist_group(name="test_streaming_chunk_limits")
class TestStreamingHandlerChunkSizeLimit:
    """Tests for StreamingToolCallHandler chunk size limiting."""

    def teardown_method(self) -> None:
        """Force GC to prevent mock accumulation in xdist workers."""
        gc.collect()

    @pytest.mark.asyncio
    async def test_streaming_handler_accepts_max_chunk_size(self) -> None:
        """
        GIVEN StreamingToolCallHandler
        WHEN constructed
        THEN should accept optional max_chunk_size parameter.
        """
        from mcp_server_langgraph.api.v1.mcp_websocket import (
            StreamingToolCallHandler,
            AuthenticatedMCPHandler,
        )

        handler = AuthenticatedMCPHandler(user_id="user:test")

        streaming_handler = StreamingToolCallHandler(
            mcp_handler=handler,
            send_notification=AsyncMock(return_value=None),  # async-mock-configured (callback)  # noqa: async-mock-config
            max_chunk_size=32768,
        )

        assert streaming_handler.max_chunk_size == 32768

    @pytest.mark.asyncio
    async def test_streaming_handler_truncates_oversized_chunks(self) -> None:
        """
        GIVEN StreamingToolCallHandler with max_chunk_size
        WHEN streaming a chunk larger than max_chunk_size
        THEN should truncate the chunk before sending.
        """
        from mcp_server_langgraph.api.v1.mcp_websocket import (
            StreamingToolCallHandler,
            AuthenticatedMCPHandler,
        )

        handler = AuthenticatedMCPHandler(user_id="user:test")
        send_notification = AsyncMock(return_value=None)  # async-mock-configured  # noqa: async-mock-config

        streaming_handler = StreamingToolCallHandler(
            mcp_handler=handler,
            send_notification=send_notification,
            max_chunk_size=100,  # Small limit for testing
        )

        # Mock execute_tool_streaming to yield oversized chunk
        async def mock_streaming(*args, **kwargs):
            yield {"type": "text", "text": "x" * 200, "is_final": True}  # 200 bytes

        with patch.object(handler, "execute_tool_streaming", side_effect=mock_streaming):
            await streaming_handler.handle_streaming_call(
                message_id=1,
                tool_name="test-tool",
                arguments={},
            )

        # Find the chunk notification and verify it was truncated
        chunk_notifications = [
            call
            for call in send_notification.call_args_list
            if call.args and call.args[0].get("method") == "$/streaming/chunk"
        ]
        assert len(chunk_notifications) >= 1

        # The chunk text should be <= max_chunk_size
        chunk_content = chunk_notifications[0].args[0]["params"]["content"]
        assert len(chunk_content["text"]) <= 100

    @pytest.mark.asyncio
    async def test_streaming_handler_default_chunk_size_unlimited(self) -> None:
        """
        GIVEN StreamingToolCallHandler without max_chunk_size
        WHEN streaming
        THEN should not truncate chunks.
        """
        from mcp_server_langgraph.api.v1.mcp_websocket import (
            StreamingToolCallHandler,
            AuthenticatedMCPHandler,
        )

        handler = AuthenticatedMCPHandler(user_id="user:test")
        send_notification = AsyncMock(return_value=None)  # async-mock-configured  # noqa: async-mock-config

        streaming_handler = StreamingToolCallHandler(
            mcp_handler=handler,
            send_notification=send_notification,
            # No max_chunk_size - should be unlimited
        )

        # max_chunk_size should be None or 0 (unlimited)
        assert streaming_handler.max_chunk_size is None or streaming_handler.max_chunk_size == 0


@pytest.mark.xdist_group(name="test_streaming_chunk_limits")
class TestLifecycleManagerMaxAge:
    """Tests for lifecycle manager using streaming_max_age_seconds."""

    def teardown_method(self) -> None:
        """Force GC to prevent mock accumulation in xdist workers."""
        gc.collect()

    @pytest.mark.asyncio
    async def test_lifecycle_manager_accepts_max_age_seconds(self) -> None:
        """
        GIVEN MCPWebSocketLifecycleManager
        WHEN constructed
        THEN should accept max_age_seconds parameter.
        """
        from mcp_server_langgraph.api.v1.mcp_websocket import MCPWebSocketLifecycleManager

        manager = MCPWebSocketLifecycleManager(
            max_age_seconds=7200,  # 2 hours
        )

        assert manager.max_age_seconds == 7200

    @pytest.mark.asyncio
    async def test_lifecycle_manager_uses_max_age_in_cleanup(self) -> None:
        """
        GIVEN MCPWebSocketLifecycleManager with max_age_seconds
        WHEN cleanup_stream_metrics is called
        THEN should pass max_age_seconds to the collector.
        """
        from mcp_server_langgraph.api.v1.mcp_websocket import MCPWebSocketLifecycleManager

        manager = MCPWebSocketLifecycleManager(
            max_age_seconds=1800,  # 30 minutes
        )

        # Call cleanup and verify max_age is used
        # Patch the module where lifecycle.py imports streaming_metrics_collector from
        with patch("mcp_server_langgraph.mcp.websocket.lifecycle.streaming_metrics_collector") as mock_collector:
            mock_collector.cleanup_old_streams.return_value = 5
            removed = await manager.cleanup_stream_metrics()

        mock_collector.cleanup_old_streams.assert_called_once_with(1800)
        assert removed == 5

    @pytest.mark.asyncio
    async def test_lifecycle_manager_default_max_age(self) -> None:
        """
        GIVEN MCPWebSocketLifecycleManager without max_age_seconds
        WHEN checking
        THEN should use default value (3600 seconds = 1 hour).
        """
        from mcp_server_langgraph.api.v1.mcp_websocket import MCPWebSocketLifecycleManager

        manager = MCPWebSocketLifecycleManager()

        assert manager.max_age_seconds == 3600


@pytest.mark.xdist_group(name="test_streaming_chunk_limits")
class TestCreateLifecycleManagerWithMaxAge:
    """Tests for lifecycle manager factory with max_age_seconds."""

    def teardown_method(self) -> None:
        """Force GC to prevent mock accumulation in xdist workers."""
        gc.collect()

    def test_create_lifecycle_manager_passes_max_age(self) -> None:
        """
        GIVEN StreamingSettings with custom max_age_seconds
        WHEN create_mcp_lifecycle_manager is called
        THEN should create manager with configured max_age.
        """
        from mcp_server_langgraph.api.v1.mcp_websocket import create_mcp_lifecycle_manager
        from mcp_server_langgraph.core.config.streaming import StreamingSettings

        settings = StreamingSettings(
            streaming_max_age_seconds=7200,  # 2 hours
        )

        manager = create_mcp_lifecycle_manager(streaming_settings=settings)

        assert manager.max_age_seconds == 7200
