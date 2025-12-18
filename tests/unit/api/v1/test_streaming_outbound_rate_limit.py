"""
Streaming Outbound Rate Limiting Tests

TDD RED Phase: Tests for verifying outbound rate limiting on streaming notifications.
Prevents overwhelming clients with too many rapid chunk notifications.
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


@pytest.mark.xdist_group(name="test_streaming_outbound_rate_limit")
class TestOutboundRateLimiterExists:
    """Tests for outbound rate limiter class existence."""

    def teardown_method(self) -> None:
        """Force GC to prevent mock accumulation in xdist workers."""
        gc.collect()

    def test_outbound_rate_limiter_class_exists(self) -> None:
        """
        GIVEN the mcp_websocket module
        WHEN importing
        THEN should have OutboundRateLimiter class.
        """
        from mcp_server_langgraph.api.v1.mcp_websocket import OutboundRateLimiter

        assert OutboundRateLimiter is not None

    def test_outbound_rate_limiter_has_check_method(self) -> None:
        """
        GIVEN OutboundRateLimiter instance
        WHEN checking methods
        THEN should have async check_and_wait method.
        """
        from mcp_server_langgraph.api.v1.mcp_websocket import OutboundRateLimiter

        limiter = OutboundRateLimiter(max_notifications_per_second=100)
        assert hasattr(limiter, "check_and_wait")

    def test_outbound_rate_limiter_configurable(self) -> None:
        """
        GIVEN OutboundRateLimiter
        WHEN constructed with custom rate
        THEN should store the configured rate.
        """
        from mcp_server_langgraph.api.v1.mcp_websocket import OutboundRateLimiter

        limiter = OutboundRateLimiter(max_notifications_per_second=50)
        assert limiter.max_notifications_per_second == 50


@pytest.mark.xdist_group(name="test_streaming_outbound_rate_limit")
class TestOutboundRateLimiterBehavior:
    """Tests for outbound rate limiter behavior."""

    def teardown_method(self) -> None:
        """Force GC to prevent mock accumulation in xdist workers."""
        gc.collect()

    @pytest.mark.asyncio
    async def test_rate_limiter_allows_under_limit(self) -> None:
        """
        GIVEN OutboundRateLimiter with 100/sec limit
        WHEN sending 10 notifications quickly
        THEN should allow all without waiting.
        """
        from mcp_server_langgraph.api.v1.mcp_websocket import OutboundRateLimiter
        import time

        limiter = OutboundRateLimiter(max_notifications_per_second=100)

        start = time.monotonic()
        for _ in range(10):
            await limiter.check_and_wait()
        elapsed = time.monotonic() - start

        # Should complete quickly (< 100ms) since we're under the limit
        assert elapsed < 0.1

    @pytest.mark.asyncio
    async def test_rate_limiter_throttles_over_limit(self) -> None:
        """
        GIVEN OutboundRateLimiter with 10/sec limit
        WHEN sending 15 notifications quickly
        THEN should introduce delays to maintain rate.
        """
        from mcp_server_langgraph.api.v1.mcp_websocket import OutboundRateLimiter
        import time

        # 10 per second = 100ms between notifications
        limiter = OutboundRateLimiter(max_notifications_per_second=10)

        start = time.monotonic()
        for _ in range(15):
            await limiter.check_and_wait()
        elapsed = time.monotonic() - start

        # 15 notifications at 10/sec should take at least ~0.4 seconds
        # (first 10 are free, next 5 require waits)
        assert elapsed >= 0.4

    @pytest.mark.asyncio
    async def test_rate_limiter_resets_after_window(self) -> None:
        """
        GIVEN OutboundRateLimiter after window expires
        WHEN sending new notifications
        THEN should allow them without delay.
        """
        from mcp_server_langgraph.api.v1.mcp_websocket import OutboundRateLimiter
        import asyncio
        import time

        limiter = OutboundRateLimiter(max_notifications_per_second=5)

        # Send 5 notifications
        for _ in range(5):
            await limiter.check_and_wait()

        # Wait for window to reset
        await asyncio.sleep(1.1)

        # Should be able to send more without delay
        start = time.monotonic()
        for _ in range(5):
            await limiter.check_and_wait()
        elapsed = time.monotonic() - start

        assert elapsed < 0.1


@pytest.mark.xdist_group(name="test_streaming_outbound_rate_limit")
class TestStreamingHandlerUsesRateLimiter:
    """Tests for StreamingToolCallHandler using outbound rate limiter."""

    def teardown_method(self) -> None:
        """Force GC to prevent mock accumulation in xdist workers."""
        gc.collect()

    @pytest.mark.asyncio
    async def test_streaming_handler_has_rate_limiter_param(self) -> None:
        """
        GIVEN StreamingToolCallHandler
        WHEN constructed
        THEN should accept optional outbound_rate_limiter parameter.
        """
        from mcp_server_langgraph.api.v1.mcp_websocket import (
            StreamingToolCallHandler,
            AuthenticatedMCPHandler,
            OutboundRateLimiter,
        )

        handler = AuthenticatedMCPHandler(user_id="user:test")
        rate_limiter = OutboundRateLimiter(max_notifications_per_second=100)

        streaming_handler = StreamingToolCallHandler(
            mcp_handler=handler,
            send_notification=AsyncMock(),
            outbound_rate_limiter=rate_limiter,
        )

        assert streaming_handler.outbound_rate_limiter is rate_limiter

    @pytest.mark.asyncio
    async def test_streaming_handler_rate_limits_chunks(self) -> None:
        """
        GIVEN StreamingToolCallHandler with rate limiter
        WHEN streaming many chunks rapidly
        THEN should apply rate limiting between chunks.
        """
        from mcp_server_langgraph.api.v1.mcp_websocket import (
            StreamingToolCallHandler,
            AuthenticatedMCPHandler,
            OutboundRateLimiter,
        )
        import time

        # Create handler with low rate limit
        handler = AuthenticatedMCPHandler(user_id="user:test")
        rate_limiter = OutboundRateLimiter(max_notifications_per_second=10)
        send_notification = AsyncMock()

        streaming_handler = StreamingToolCallHandler(
            mcp_handler=handler,
            send_notification=send_notification,
            outbound_rate_limiter=rate_limiter,
        )

        # Mock execute_tool_streaming to yield many chunks quickly
        async def mock_streaming(*args, **kwargs):
            for i in range(15):
                yield {"type": "text", "text": f"chunk {i}", "is_final": i == 14}

        with patch.object(handler, "execute_tool_streaming", side_effect=mock_streaming):
            start = time.monotonic()
            await streaming_handler.handle_streaming_call(
                message_id=1,
                tool_name="test-tool",
                arguments={},
            )
            elapsed = time.monotonic() - start

        # Should take at least some time due to rate limiting
        # 15 chunks + start + end = 17 notifications
        # At 10/sec, excess 7 require ~0.7 sec of delays
        assert elapsed >= 0.5


@pytest.mark.xdist_group(name="test_streaming_outbound_rate_limit")
class TestStreamingSettingsRateLimit:
    """Tests for StreamingSettings rate limit configuration."""

    def teardown_method(self) -> None:
        """Force GC to prevent mock accumulation in xdist workers."""
        gc.collect()

    def test_streaming_settings_has_rate_limit_field(self) -> None:
        """
        GIVEN StreamingSettings
        WHEN checking attributes
        THEN should have streaming_max_notifications_per_second field.
        """
        from mcp_server_langgraph.core.config.streaming import StreamingSettings

        settings = StreamingSettings()
        assert hasattr(settings, "streaming_max_notifications_per_second")
        assert isinstance(settings.streaming_max_notifications_per_second, int)

    def test_streaming_settings_rate_limit_default(self) -> None:
        """
        GIVEN StreamingSettings with no override
        WHEN checking streaming_max_notifications_per_second
        THEN should default to reasonable value (100).
        """
        from mcp_server_langgraph.core.config.streaming import StreamingSettings

        settings = StreamingSettings()
        # Default to 100 notifications per second
        assert settings.streaming_max_notifications_per_second == 100

    def test_streaming_settings_rate_limit_configurable(self) -> None:
        """
        GIVEN StreamingSettings with custom rate
        WHEN checking streaming_max_notifications_per_second
        THEN should use the configured value.
        """
        from mcp_server_langgraph.core.config.streaming import StreamingSettings

        settings = StreamingSettings(streaming_max_notifications_per_second=50)
        assert settings.streaming_max_notifications_per_second == 50
