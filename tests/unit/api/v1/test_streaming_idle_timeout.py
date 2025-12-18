"""
Streaming Idle Timeout Reset Tests

TDD RED Phase: Tests for verifying idle timeout is reset during streaming.
Each streaming chunk should count as activity to prevent premature disconnection.
"""

from __future__ import annotations

import gc
from unittest.mock import AsyncMock, MagicMock, patch
from datetime import datetime, timedelta, UTC

import pytest


pytestmark = [
    pytest.mark.unit,
    pytest.mark.api,
    pytest.mark.websocket,
]


@pytest.mark.xdist_group(name="test_streaming_idle_timeout")
class TestStreamingResetsIdleTimeout:
    """Tests for streaming chunk activity updating idle timeout."""

    def teardown_method(self) -> None:
        """Force GC to prevent mock accumulation in xdist workers."""
        gc.collect()

    @pytest.mark.asyncio
    async def test_streaming_handler_accepts_connection_manager(self) -> None:
        """
        GIVEN StreamingToolCallHandler
        WHEN constructed
        THEN should accept optional connection_manager parameter.
        """
        from mcp_server_langgraph.api.v1.mcp_websocket import (
            StreamingToolCallHandler,
            AuthenticatedMCPHandler,
            ConnectionManager,
        )

        handler = AuthenticatedMCPHandler(user_id="user:test")
        connection_manager = ConnectionManager()

        streaming_handler = StreamingToolCallHandler(
            mcp_handler=handler,
            send_notification=AsyncMock(),
            connection_manager=connection_manager,
        )

        assert streaming_handler.connection_manager is connection_manager

    @pytest.mark.asyncio
    async def test_streaming_handler_accepts_session_id(self) -> None:
        """
        GIVEN StreamingToolCallHandler
        WHEN constructed
        THEN should accept optional session_id parameter.
        """
        from mcp_server_langgraph.api.v1.mcp_websocket import (
            StreamingToolCallHandler,
            AuthenticatedMCPHandler,
        )

        handler = AuthenticatedMCPHandler(user_id="user:test")

        streaming_handler = StreamingToolCallHandler(
            mcp_handler=handler,
            send_notification=AsyncMock(),
            session_id="test-session-123",
        )

        assert streaming_handler.session_id == "test-session-123"

    @pytest.mark.asyncio
    async def test_streaming_chunk_updates_activity(self) -> None:
        """
        GIVEN StreamingToolCallHandler with connection_manager and session_id
        WHEN streaming chunks are sent
        THEN should call connection_manager.update_activity for each chunk.
        """
        from mcp_server_langgraph.api.v1.mcp_websocket import (
            StreamingToolCallHandler,
            AuthenticatedMCPHandler,
        )

        handler = AuthenticatedMCPHandler(user_id="user:test")
        mock_connection_manager = MagicMock()
        send_notification = AsyncMock()

        streaming_handler = StreamingToolCallHandler(
            mcp_handler=handler,
            send_notification=send_notification,
            connection_manager=mock_connection_manager,
            session_id="test-session-123",
        )

        # Mock execute_tool_streaming to yield 3 chunks
        async def mock_streaming(*args, **kwargs):
            yield {"type": "text", "text": "chunk 1", "is_final": False}
            yield {"type": "text", "text": "chunk 2", "is_final": False}
            yield {"type": "text", "text": "chunk 3", "is_final": True}

        with patch.object(handler, "execute_tool_streaming", side_effect=mock_streaming):
            await streaming_handler.handle_streaming_call(
                message_id=1,
                tool_name="test-tool",
                arguments={},
            )

        # Should have updated activity for each chunk
        assert mock_connection_manager.update_activity.call_count == 3
        mock_connection_manager.update_activity.assert_called_with("test-session-123")


@pytest.mark.xdist_group(name="test_streaming_idle_timeout")
class TestConnectionActivityReset:
    """Tests for connection activity reset functionality."""

    def teardown_method(self) -> None:
        """Force GC to prevent mock accumulation in xdist workers."""
        gc.collect()

    def test_update_activity_updates_last_activity_timestamp(self) -> None:
        """
        GIVEN a ConnectionManager with active connection
        WHEN update_activity is called
        THEN should update the last_activity timestamp.
        """
        from mcp_server_langgraph.api.v1.mcp_websocket import (
            ConnectionManager,
            ConnectionInfo,
        )
        from fastapi import WebSocket

        manager = ConnectionManager()
        mock_ws = MagicMock(spec=WebSocket)

        # Manually add a connection
        old_time = datetime.now(UTC) - timedelta(minutes=30)
        conn_info = ConnectionInfo(
            websocket=mock_ws,
            session_id="test-session",
            user_id="user:test",
            last_activity=old_time,
        )
        manager._connections["test-session"] = conn_info

        # Update activity
        manager.update_activity("test-session")

        # Verify timestamp was updated to be more recent
        new_time = manager._connections["test-session"].last_activity
        assert new_time > old_time

    def test_streaming_during_idle_prevents_disconnect(self) -> None:
        """
        GIVEN a connection that would be considered idle
        WHEN streaming is in progress (activity updated)
        THEN connection should not be marked as idle.
        """
        from mcp_server_langgraph.api.v1.mcp_websocket import (
            ConnectionInfo,
            is_connection_idle,
        )
        from fastapi import WebSocket

        mock_ws = MagicMock(spec=WebSocket)

        # Create connection that was idle but now has fresh activity
        conn_info = ConnectionInfo(
            websocket=mock_ws,
            session_id="test-session",
            user_id="user:test",
            last_activity=datetime.now(UTC),  # Fresh activity
        )

        # Should NOT be idle
        assert not is_connection_idle(conn_info)
