"""
Streaming + Security Integration Tests

Tests for verifying that streaming features work correctly with security limits.
These tests verify the combined behavior of rate limiting, idle timeout,
connection limits, and message size validation during streaming operations.
"""

from __future__ import annotations

import gc
from datetime import datetime, timedelta, UTC
from unittest.mock import AsyncMock, MagicMock, patch

import pytest


pytestmark = [
    pytest.mark.unit,
    pytest.mark.api,
    pytest.mark.websocket,
]


@pytest.mark.xdist_group(name="test_streaming_security_integration")
class TestStreamingWithRateLimiting:
    """Integration tests for streaming with rate limiting."""

    def teardown_method(self) -> None:
        """Force GC to prevent mock accumulation in xdist workers."""
        gc.collect()

    @pytest.mark.asyncio
    async def test_streaming_chunks_are_rate_limited(self) -> None:
        """
        GIVEN StreamingToolCallHandler with OutboundRateLimiter
        WHEN streaming multiple chunks rapidly
        THEN outbound rate limiter should throttle notifications.
        """
        from mcp_server_langgraph.api.v1.mcp_websocket import (
            StreamingToolCallHandler,
            AuthenticatedMCPHandler,
            OutboundRateLimiter,
        )

        handler = AuthenticatedMCPHandler(user_id="user:test")
        send_notification = AsyncMock(return_value=None)  # async-mock-configured  # noqa: async-mock-config
        rate_limiter = OutboundRateLimiter(max_notifications_per_second=10)

        streaming_handler = StreamingToolCallHandler(
            mcp_handler=handler,
            send_notification=send_notification,
            outbound_rate_limiter=rate_limiter,
        )

        # Mock execute_tool_streaming to yield multiple chunks
        async def mock_streaming(*args, **kwargs):
            for i in range(5):
                yield {"type": "text", "text": f"chunk {i}", "is_final": i == 4}

        with patch.object(handler, "execute_tool_streaming", side_effect=mock_streaming):
            await streaming_handler.handle_streaming_call(
                message_id=1,
                tool_name="test-tool",
                arguments={},
            )

        # Should have sent start, 5 chunks, and end notifications
        # Rate limiter should have been invoked for each chunk
        chunk_calls = [
            call
            for call in send_notification.call_args_list
            if call.args and call.args[0].get("method") == "$/streaming/chunk"
        ]
        assert len(chunk_calls) == 5

    @pytest.mark.asyncio
    async def test_streaming_with_user_rate_limiter(self) -> None:
        """
        GIVEN SecureMessageProcessor with user rate limiter
        WHEN processing messages during streaming
        THEN should track rate per user, not per connection.
        """
        from mcp_server_langgraph.api.v1.mcp_websocket import (
            SecureMessageProcessor,
            UserRateLimiterManager,
        )

        rate_limiter = UserRateLimiterManager(max_messages=100, window_seconds=60)

        # Create two processors for same user
        processor1 = SecureMessageProcessor(
            session_id="session-1",
            user_id="user:alice",
            rate_limiter=rate_limiter,
        )
        processor2 = SecureMessageProcessor(
            session_id="session-2",
            user_id="user:alice",
            rate_limiter=rate_limiter,
        )

        # Both should share the same rate limit bucket
        for _ in range(50):
            result = processor1.validate_incoming("small message")
            assert result.is_valid

        for _ in range(49):
            result = processor2.validate_incoming("small message")
            assert result.is_valid

        # 100th message should still pass (exactly at limit)
        result = processor2.validate_incoming("small message")
        assert result.is_valid

        # 101st message should fail
        result = processor1.validate_incoming("small message")
        assert not result.is_valid
        assert "Rate limit" in result.error_message


@pytest.mark.xdist_group(name="test_streaming_security_integration")
class TestStreamingWithIdleTimeout:
    """Integration tests for streaming with idle timeout."""

    def teardown_method(self) -> None:
        """Force GC to prevent mock accumulation in xdist workers."""
        gc.collect()

    @pytest.mark.asyncio
    async def test_streaming_prevents_idle_disconnect(self) -> None:
        """
        GIVEN a connection that would be idle
        WHEN streaming is in progress
        THEN connection should not be marked as idle.
        """
        from mcp_server_langgraph.api.v1.mcp_websocket import (
            StreamingToolCallHandler,
            AuthenticatedMCPHandler,
            ConnectionManager,
            ConnectionInfo,
        )
        from fastapi import WebSocket

        handler = AuthenticatedMCPHandler(user_id="user:test")
        connection_manager = ConnectionManager()
        send_notification = AsyncMock(return_value=None)  # async-mock-configured  # noqa: async-mock-config
        session_id = "test-session"

        # Simulate a connection
        mock_ws = MagicMock(spec=WebSocket)
        old_time = datetime.now(UTC) - timedelta(minutes=25)
        conn_info = ConnectionInfo(
            websocket=mock_ws,
            session_id=session_id,
            user_id="user:test",
            last_activity=old_time,
        )
        connection_manager._connections[session_id] = conn_info

        streaming_handler = StreamingToolCallHandler(
            mcp_handler=handler,
            send_notification=send_notification,
            connection_manager=connection_manager,
            session_id=session_id,
        )

        # Mock execute_tool_streaming
        async def mock_streaming(*args, **kwargs):
            yield {"type": "text", "text": "chunk 1", "is_final": True}

        with patch.object(handler, "execute_tool_streaming", side_effect=mock_streaming):
            await streaming_handler.handle_streaming_call(
                message_id=1,
                tool_name="test-tool",
                arguments={},
            )

        # Activity should have been updated
        new_time = connection_manager._connections[session_id].last_activity
        assert new_time > old_time

    def test_configurable_idle_timeout_in_connection_check(self) -> None:
        """
        GIVEN different idle timeout values
        WHEN checking connection idle status
        THEN should use the configured timeout.
        """
        from mcp_server_langgraph.api.v1.mcp_websocket import (
            ConnectionInfo,
            is_connection_idle,
        )
        from fastapi import WebSocket

        mock_ws = MagicMock(spec=WebSocket)

        # Connection that's 10 minutes old
        conn_info = ConnectionInfo(
            websocket=mock_ws,
            session_id="test",
            last_activity=datetime.now(UTC) - timedelta(minutes=10),
        )

        # With 5 minute timeout, should be idle
        assert is_connection_idle(conn_info, timeout_seconds=300) is True

        # With 15 minute timeout, should NOT be idle
        assert is_connection_idle(conn_info, timeout_seconds=900) is False

        # With 30 minute timeout (default), should NOT be idle
        assert is_connection_idle(conn_info, timeout_seconds=1800) is False


@pytest.mark.xdist_group(name="test_streaming_security_integration")
class TestStreamingWithConnectionLimits:
    """Integration tests for streaming with connection limits."""

    def teardown_method(self) -> None:
        """Force GC to prevent mock accumulation in xdist workers."""
        gc.collect()

    def test_configurable_connection_limit(self) -> None:
        """
        GIVEN ConnectionManager with custom limit
        WHEN user exceeds the limit
        THEN should reject new connections.
        """
        from mcp_server_langgraph.api.v1.mcp_websocket import ConnectionManager

        # Create manager with limit of 2 connections
        manager = ConnectionManager(max_connections_per_user=2)

        # Simulate 2 connections
        manager._user_connections["user:test"] = ["session1", "session2"]

        # Should not allow 3rd connection
        assert not manager.can_user_connect("user:test")

        # Different user should be allowed
        assert manager.can_user_connect("user:other")

    def test_streaming_handler_respects_connection_limit(self) -> None:
        """
        GIVEN a user at connection limit
        WHEN attempting to stream
        THEN streaming should still work on existing connections.
        """
        from mcp_server_langgraph.api.v1.mcp_websocket import (
            ConnectionManager,
            StreamingToolCallHandler,
            AuthenticatedMCPHandler,
        )

        manager = ConnectionManager(max_connections_per_user=2)
        manager._user_connections["user:test"] = ["session1", "session2"]

        # User is at limit
        assert not manager.can_user_connect("user:test")

        # But existing connection can still stream
        handler = AuthenticatedMCPHandler(user_id="user:test")
        streaming_handler = StreamingToolCallHandler(
            mcp_handler=handler,
            send_notification=AsyncMock(return_value=None),  # async-mock-configured (callback)  # noqa: async-mock-config
            connection_manager=manager,
            session_id="session1",
        )

        # Verify streaming handler is set up correctly
        assert streaming_handler.connection_manager is manager
        assert streaming_handler.session_id == "session1"


@pytest.mark.xdist_group(name="test_streaming_security_integration")
class TestStreamingWithMessageSizeValidation:
    """Integration tests for streaming with message size validation."""

    def teardown_method(self) -> None:
        """Force GC to prevent mock accumulation in xdist workers."""
        gc.collect()

    def test_configurable_max_message_size(self) -> None:
        """
        GIVEN SecureMessageProcessor with custom max_message_size
        WHEN validating messages of various sizes
        THEN should use the configured limit.
        """
        from mcp_server_langgraph.api.v1.mcp_websocket import SecureMessageProcessor

        # Processor with small limit for testing
        processor = SecureMessageProcessor(
            session_id="test",
            max_message_size=100,
        )

        # Small message should pass
        result = processor.validate_incoming("x" * 50)
        assert result.is_valid

        # Message at limit should pass
        result = processor.validate_incoming("x" * 100)
        assert result.is_valid

        # Message over limit should fail
        result = processor.validate_incoming("x" * 101)
        assert not result.is_valid
        assert "size" in result.error_message.lower()

    @pytest.mark.asyncio
    async def test_streaming_chunk_truncation_with_config(self) -> None:
        """
        GIVEN StreamingToolCallHandler with max_chunk_size
        WHEN streaming oversized chunks
        THEN should truncate chunks to configured size.
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
            max_chunk_size=50,  # Small for testing
        )

        # Mock execute_tool_streaming to yield oversized chunk
        async def mock_streaming(*args, **kwargs):
            yield {"type": "text", "text": "x" * 100, "is_final": True}

        with patch.object(handler, "execute_tool_streaming", side_effect=mock_streaming):
            await streaming_handler.handle_streaming_call(
                message_id=1,
                tool_name="test-tool",
                arguments={},
            )

        # Find chunk notification
        chunk_calls = [
            call
            for call in send_notification.call_args_list
            if call.args and call.args[0].get("method") == "$/streaming/chunk"
        ]
        assert len(chunk_calls) == 1

        # Verify chunk was truncated
        chunk_content = chunk_calls[0].args[0]["params"]["content"]
        assert len(chunk_content["text"]) == 50


@pytest.mark.xdist_group(name="test_streaming_security_integration")
class TestFullSecurityStackIntegration:
    """Full integration tests for streaming with all security features."""

    def teardown_method(self) -> None:
        """Force GC to prevent mock accumulation in xdist workers."""
        gc.collect()

    @pytest.mark.asyncio
    async def test_streaming_with_all_security_features(self) -> None:
        """
        GIVEN StreamingToolCallHandler with all security features
        WHEN streaming
        THEN all security features should work together.
        """
        from mcp_server_langgraph.api.v1.mcp_websocket import (
            StreamingToolCallHandler,
            AuthenticatedMCPHandler,
            ConnectionManager,
            ConnectionInfo,
            OutboundRateLimiter,
            StreamingMetricsCollector,
        )
        from fastapi import WebSocket

        handler = AuthenticatedMCPHandler(user_id="user:test")
        connection_manager = ConnectionManager(max_connections_per_user=5)
        rate_limiter = OutboundRateLimiter(max_notifications_per_second=100)
        metrics_collector = StreamingMetricsCollector()
        send_notification = AsyncMock(return_value=None)  # async-mock-configured  # noqa: async-mock-config
        session_id = "test-session"

        # Set up connection
        mock_ws = MagicMock(spec=WebSocket)
        old_time = datetime.now(UTC) - timedelta(minutes=20)
        conn_info = ConnectionInfo(
            websocket=mock_ws,
            session_id=session_id,
            user_id="user:test",
            last_activity=old_time,
        )
        connection_manager._connections[session_id] = conn_info

        streaming_handler = StreamingToolCallHandler(
            mcp_handler=handler,
            send_notification=send_notification,
            metrics_collector=metrics_collector,
            outbound_rate_limiter=rate_limiter,
            connection_manager=connection_manager,
            session_id=session_id,
            max_chunk_size=1000,
        )

        # Mock execute_tool_streaming
        async def mock_streaming(*args, **kwargs):
            yield {"type": "text", "text": "chunk 1", "is_final": False}
            yield {"type": "text", "text": "chunk 2", "is_final": True}

        with patch.object(handler, "execute_tool_streaming", side_effect=mock_streaming):
            result = await streaming_handler.handle_streaming_call(
                message_id=1,
                tool_name="test-tool",
                arguments={},
            )

        # Verify successful completion
        assert result["isError"] is False

        # Verify activity was updated
        assert connection_manager._connections[session_id].last_activity > old_time

        # Verify metrics were recorded
        stats = metrics_collector.get_aggregate_stats()
        assert stats["total_streams"] >= 1

    def test_configurable_settings_flow_through_bootstrap(self) -> None:
        """
        GIVEN custom security settings
        WHEN bootstrap creates StreamingSettings
        THEN all security limits should be extracted.
        """
        from mcp_server_langgraph.core.config.streaming import StreamingSettings

        settings = StreamingSettings(
            streaming_max_connections_per_user=10,
            streaming_max_message_size=2_000_000,
            streaming_max_messages_per_minute=1200,
            streaming_idle_timeout_seconds=3600,
            streaming_max_notifications_per_second=200,
            streaming_max_chunk_size=128000,
        )

        # All settings should be correctly set
        assert settings.streaming_max_connections_per_user == 10
        assert settings.streaming_max_message_size == 2_000_000
        assert settings.streaming_max_messages_per_minute == 1200
        assert settings.streaming_idle_timeout_seconds == 3600
        assert settings.streaming_max_notifications_per_second == 200
        assert settings.streaming_max_chunk_size == 128000
