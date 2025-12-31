"""
TDD Tests for Redis-backed WebSocket Rate Limiting.

Tests the RedisUserRateLimiter and RedisWebSocketRateLimiter classes
for distributed rate limiting across multiple instances.

Following TDD RED-GREEN-REFACTOR cycle:
- RED: Write failing tests that define expected behavior
- GREEN: Implement minimal code to make tests pass
- REFACTOR: Improve code quality while keeping tests green
"""

from __future__ import annotations

import gc
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

pytestmark = [
    pytest.mark.unit,
    pytest.mark.websocket,
    pytest.mark.redis,
    pytest.mark.xdist_group(name="redis_rate_limiter"),
]


class TestRedisUserRateLimiterImports:
    """Test that Redis rate limiter classes can be imported."""

    def teardown_method(self) -> None:
        """Force GC to prevent mock accumulation in xdist workers."""
        gc.collect()

    def test_can_import_redis_user_rate_limiter(self) -> None:
        """RedisUserRateLimiter should be importable from rate_limiter module."""
        from mcp_server_langgraph.websocket.rate_limiter import RedisUserRateLimiter

        assert RedisUserRateLimiter is not None

    def test_can_import_redis_websocket_rate_limiter(self) -> None:
        """RedisWebSocketRateLimiter should be importable."""
        from mcp_server_langgraph.websocket.rate_limiter import (
            RedisWebSocketRateLimiter,
        )

        assert RedisWebSocketRateLimiter is not None


@pytest.mark.xdist_group(name="redis_rate_limiter")
class TestRedisUserRateLimiterInstantiation:
    """Test RedisUserRateLimiter initialization."""

    def teardown_method(self) -> None:
        """Force GC to prevent mock accumulation in xdist workers."""
        gc.collect()

    def test_instantiation_with_redis_client(self) -> None:
        """Should accept a Redis client on initialization."""
        from mcp_server_langgraph.websocket.rate_limiter import RedisUserRateLimiter

        mock_redis = AsyncMock()  # noqa: async-mock-config
        limiter = RedisUserRateLimiter(
            redis_client=mock_redis,
            max_messages=100,
            window_seconds=60,
        )

        assert limiter is not None
        assert limiter.max_messages == 100
        assert limiter.window_seconds == 60

    def test_key_prefix_default(self) -> None:
        """Should have a default key prefix for Redis keys."""
        from mcp_server_langgraph.websocket.rate_limiter import RedisUserRateLimiter

        mock_redis = AsyncMock()  # noqa: async-mock-config
        limiter = RedisUserRateLimiter(
            redis_client=mock_redis,
            max_messages=100,
            window_seconds=60,
        )

        assert limiter.key_prefix == "ratelimit:ws:user:"

    def test_key_prefix_custom(self) -> None:
        """Should accept custom key prefix."""
        from mcp_server_langgraph.websocket.rate_limiter import RedisUserRateLimiter

        mock_redis = AsyncMock()  # noqa: async-mock-config
        limiter = RedisUserRateLimiter(
            redis_client=mock_redis,
            max_messages=100,
            window_seconds=60,
            key_prefix="custom:prefix:",
        )

        assert limiter.key_prefix == "custom:prefix:"


@pytest.mark.xdist_group(name="redis_rate_limiter")
class TestRedisUserRateLimiterCheckAndIncrement:
    """Test RedisUserRateLimiter.check_and_increment method."""

    def teardown_method(self) -> None:
        """Force GC to prevent mock accumulation in xdist workers."""
        gc.collect()

    @pytest.mark.asyncio
    async def test_check_and_increment_allows_under_limit(self) -> None:
        """Should return True when under the limit."""
        from mcp_server_langgraph.websocket.rate_limiter import RedisUserRateLimiter

        mock_redis = AsyncMock()  # noqa: async-mock-config
        # Simulate Redis INCR returning 1 (first message)
        mock_redis.incr.return_value = 1
        mock_redis.expire.return_value = True

        limiter = RedisUserRateLimiter(
            redis_client=mock_redis,
            max_messages=100,
            window_seconds=60,
        )

        result = await limiter.check_and_increment("user-123")

        assert result is True
        mock_redis.incr.assert_called_once()

    @pytest.mark.asyncio
    async def test_check_and_increment_blocks_over_limit(self) -> None:
        """Should return False when over the limit."""
        from mcp_server_langgraph.websocket.rate_limiter import RedisUserRateLimiter

        mock_redis = AsyncMock()  # noqa: async-mock-config
        # Simulate Redis INCR returning 101 (over limit of 100)
        mock_redis.incr.return_value = 101
        mock_redis.expire.return_value = True

        limiter = RedisUserRateLimiter(
            redis_client=mock_redis,
            max_messages=100,
            window_seconds=60,
        )

        result = await limiter.check_and_increment("user-123")

        assert result is False

    @pytest.mark.asyncio
    async def test_check_and_increment_sets_expiry(self) -> None:
        """Should set expiry on the Redis key."""
        from mcp_server_langgraph.websocket.rate_limiter import RedisUserRateLimiter

        mock_redis = AsyncMock()  # noqa: async-mock-config
        mock_redis.incr.return_value = 1
        mock_redis.expire.return_value = True

        limiter = RedisUserRateLimiter(
            redis_client=mock_redis,
            max_messages=100,
            window_seconds=60,
        )

        await limiter.check_and_increment("user-123")

        # Should set expire with NX flag (only if not exists)
        mock_redis.expire.assert_called_once()
        call_args = mock_redis.expire.call_args
        assert call_args[0][1] == 60  # window_seconds

    @pytest.mark.asyncio
    async def test_check_and_increment_uses_correct_key(self) -> None:
        """Should use the correct Redis key format."""
        from mcp_server_langgraph.websocket.rate_limiter import RedisUserRateLimiter

        mock_redis = AsyncMock()  # noqa: async-mock-config
        mock_redis.incr.return_value = 1
        mock_redis.expire.return_value = True

        limiter = RedisUserRateLimiter(
            redis_client=mock_redis,
            max_messages=100,
            window_seconds=60,
            key_prefix="ratelimit:ws:user:",
        )

        await limiter.check_and_increment("user-456")

        expected_key = "ratelimit:ws:user:user-456"
        mock_redis.incr.assert_called_with(expected_key)


@pytest.mark.xdist_group(name="redis_rate_limiter")
class TestRedisUserRateLimiterGetRemaining:
    """Test RedisUserRateLimiter.get_remaining method."""

    def teardown_method(self) -> None:
        """Force GC to prevent mock accumulation in xdist workers."""
        gc.collect()

    @pytest.mark.asyncio
    async def test_get_remaining_with_no_key(self) -> None:
        """Should return max_messages when key doesn't exist."""
        from mcp_server_langgraph.websocket.rate_limiter import RedisUserRateLimiter

        mock_redis = AsyncMock()  # noqa: async-mock-config
        mock_redis.get.return_value = None

        limiter = RedisUserRateLimiter(
            redis_client=mock_redis,
            max_messages=100,
            window_seconds=60,
        )

        remaining = await limiter.get_remaining("user-123")

        assert remaining == 100

    @pytest.mark.asyncio
    async def test_get_remaining_with_existing_count(self) -> None:
        """Should return remaining quota based on current count."""
        from mcp_server_langgraph.websocket.rate_limiter import RedisUserRateLimiter

        mock_redis = AsyncMock()  # noqa: async-mock-config
        mock_redis.get.return_value = b"30"  # 30 messages used

        limiter = RedisUserRateLimiter(
            redis_client=mock_redis,
            max_messages=100,
            window_seconds=60,
        )

        remaining = await limiter.get_remaining("user-123")

        assert remaining == 70  # 100 - 30

    @pytest.mark.asyncio
    async def test_get_remaining_at_limit(self) -> None:
        """Should return 0 when at the limit."""
        from mcp_server_langgraph.websocket.rate_limiter import RedisUserRateLimiter

        mock_redis = AsyncMock()  # noqa: async-mock-config
        mock_redis.get.return_value = b"100"

        limiter = RedisUserRateLimiter(
            redis_client=mock_redis,
            max_messages=100,
            window_seconds=60,
        )

        remaining = await limiter.get_remaining("user-123")

        assert remaining == 0


@pytest.mark.xdist_group(name="redis_rate_limiter")
class TestRedisUserRateLimiterFailover:
    """Test RedisUserRateLimiter graceful degradation."""

    def teardown_method(self) -> None:
        """Force GC to prevent mock accumulation in xdist workers."""
        gc.collect()

    @pytest.mark.asyncio
    async def test_fail_open_on_redis_error(self) -> None:
        """Should allow request when Redis is unavailable (fail-open)."""
        from mcp_server_langgraph.websocket.rate_limiter import RedisUserRateLimiter

        mock_redis = AsyncMock()  # noqa: async-mock-config
        mock_redis.incr.side_effect = Exception("Redis connection failed")

        limiter = RedisUserRateLimiter(
            redis_client=mock_redis,
            max_messages=100,
            window_seconds=60,
            fail_open=True,
        )

        result = await limiter.check_and_increment("user-123")

        # Should allow request (fail-open)
        assert result is True

    @pytest.mark.asyncio
    async def test_fail_closed_on_redis_error(self) -> None:
        """Should deny request when Redis is unavailable if fail_open=False."""
        from mcp_server_langgraph.websocket.rate_limiter import RedisUserRateLimiter

        mock_redis = AsyncMock()  # noqa: async-mock-config
        mock_redis.incr.side_effect = Exception("Redis connection failed")

        limiter = RedisUserRateLimiter(
            redis_client=mock_redis,
            max_messages=100,
            window_seconds=60,
            fail_open=False,
        )

        result = await limiter.check_and_increment("user-123")

        # Should deny request (fail-closed)
        assert result is False

    @pytest.mark.asyncio
    async def test_get_remaining_returns_max_on_error(self) -> None:
        """Should return max_messages on Redis error (optimistic)."""
        from mcp_server_langgraph.websocket.rate_limiter import RedisUserRateLimiter

        mock_redis = AsyncMock()  # noqa: async-mock-config
        mock_redis.get.side_effect = Exception("Redis connection failed")

        limiter = RedisUserRateLimiter(
            redis_client=mock_redis,
            max_messages=100,
            window_seconds=60,
            fail_open=True,
        )

        remaining = await limiter.get_remaining("user-123")

        assert remaining == 100


class TestRedisWebSocketRateLimiterInstantiation:
    """Test RedisWebSocketRateLimiter initialization."""

    def teardown_method(self) -> None:
        """Force GC to prevent mock accumulation in xdist workers."""
        gc.collect()

    def test_instantiation_with_redis_url(self) -> None:
        """Should accept Redis URL for initialization."""
        from mcp_server_langgraph.websocket.rate_limiter import (
            RedisWebSocketRateLimiter,
        )

        limiter = RedisWebSocketRateLimiter(
            redis_url="redis://localhost:6379/3",
            messages_per_minute=600,
        )

        assert limiter is not None
        assert limiter.messages_per_minute == 600

    def test_lazy_redis_connection(self) -> None:
        """Should not connect to Redis until first use."""
        from mcp_server_langgraph.websocket.rate_limiter import (
            RedisWebSocketRateLimiter,
        )

        limiter = RedisWebSocketRateLimiter(
            redis_url="redis://localhost:6379/3",
            messages_per_minute=600,
        )

        # Should not have connected yet
        assert limiter._redis_client is None


@pytest.mark.xdist_group(name="redis_rate_limiter")
class TestRedisWebSocketRateLimiterCheckMessage:
    """Test RedisWebSocketRateLimiter.check_message method."""

    def teardown_method(self) -> None:
        """Force GC to prevent mock accumulation in xdist workers."""
        gc.collect()

    @pytest.mark.asyncio
    async def test_check_message_allows_under_limit(self) -> None:
        """Should allow message when under limit."""
        from mcp_server_langgraph.websocket.rate_limiter import (
            RedisUserRateLimiter,
            RedisWebSocketRateLimiter,
        )

        mock_redis = AsyncMock()  # noqa: async-mock-config
        mock_redis.incr.return_value = 1
        mock_redis.expire.return_value = True

        limiter = RedisWebSocketRateLimiter(
            redis_url="redis://localhost:6379/3",
            messages_per_minute=600,
        )
        limiter._redis_client = mock_redis
        limiter._user_limiter = RedisUserRateLimiter(
            redis_client=mock_redis,
            max_messages=600,
            window_seconds=60,
        )

        result = await limiter.check_message("user-123")

        assert result is True

    @pytest.mark.asyncio
    async def test_check_message_blocks_over_limit(self) -> None:
        """Should block message when over limit."""
        from mcp_server_langgraph.websocket.rate_limiter import (
            RedisUserRateLimiter,
            RedisWebSocketRateLimiter,
        )

        mock_redis = AsyncMock()  # noqa: async-mock-config
        mock_redis.incr.return_value = 601  # Over 600 limit
        mock_redis.expire.return_value = True

        limiter = RedisWebSocketRateLimiter(
            redis_url="redis://localhost:6379/3",
            messages_per_minute=600,
        )
        limiter._redis_client = mock_redis
        limiter._user_limiter = RedisUserRateLimiter(
            redis_client=mock_redis,
            max_messages=600,
            window_seconds=60,
        )

        result = await limiter.check_message("user-123")

        assert result is False


@pytest.mark.xdist_group(name="redis_rate_limiter")
class TestRedisWebSocketRateLimiterStats:
    """Test RedisWebSocketRateLimiter statistics methods."""

    def teardown_method(self) -> None:
        """Force GC to prevent mock accumulation in xdist workers."""
        gc.collect()

    @pytest.mark.asyncio
    async def test_get_stats_returns_expected_format(self) -> None:
        """Should return stats in expected format."""
        from mcp_server_langgraph.websocket.rate_limiter import (
            RedisUserRateLimiter,
            RedisWebSocketRateLimiter,
        )

        mock_redis = AsyncMock()  # noqa: async-mock-config
        mock_redis.get.return_value = b"50"

        limiter = RedisWebSocketRateLimiter(
            redis_url="redis://localhost:6379/3",
            messages_per_minute=600,
        )
        limiter._redis_client = mock_redis
        limiter._user_limiter = RedisUserRateLimiter(
            redis_client=mock_redis,
            max_messages=600,
            window_seconds=60,
        )

        stats = await limiter.get_stats("user-123")

        assert "remaining" in stats
        assert "limit" in stats
        assert "used" in stats
        assert stats["limit"] == 600

    @pytest.mark.asyncio
    async def test_get_remaining_quota(self) -> None:
        """Should return remaining quota for user."""
        from mcp_server_langgraph.websocket.rate_limiter import (
            RedisUserRateLimiter,
            RedisWebSocketRateLimiter,
        )

        mock_redis = AsyncMock()  # noqa: async-mock-config
        mock_redis.get.return_value = b"100"

        limiter = RedisWebSocketRateLimiter(
            redis_url="redis://localhost:6379/3",
            messages_per_minute=600,
        )
        limiter._redis_client = mock_redis
        limiter._user_limiter = RedisUserRateLimiter(
            redis_client=mock_redis,
            max_messages=600,
            window_seconds=60,
        )

        remaining = await limiter.get_remaining_quota("user-123")

        assert remaining == 500  # 600 - 100


@pytest.mark.xdist_group(name="redis_rate_limiter")
class TestRedisWebSocketRateLimiterFactory:
    """Test factory function for creating Redis rate limiter."""

    def teardown_method(self) -> None:
        """Force GC to prevent mock accumulation in xdist workers."""
        gc.collect()

    @pytest.mark.asyncio
    async def test_create_from_settings(self) -> None:
        """Should create limiter from application settings."""
        from mcp_server_langgraph.websocket.rate_limiter import (
            create_redis_rate_limiter,
        )

        mock_settings = MagicMock(
            redis_host="localhost",
            redis_port=6379,
            redis_rate_limit_db=3,
        )

        with patch(
            "mcp_server_langgraph.core.config.settings",
            mock_settings,
        ):
            limiter = create_redis_rate_limiter(messages_per_minute=600)

            assert limiter is not None

    @pytest.mark.asyncio
    async def test_feature_flag_controls_redis_usage(self) -> None:
        """Should return in-memory limiter when feature flag disabled."""
        from mcp_server_langgraph.websocket.rate_limiter import (
            get_websocket_rate_limiter,
            WebSocketRateLimiter,
        )

        with patch("mcp_server_langgraph.core.feature_flags.get_feature_flags") as mock_ff:
            mock_ff.return_value = MagicMock(
                enable_distributed_rate_limiting=False,
            )

            limiter = get_websocket_rate_limiter(messages_per_minute=600)

            # Should return in-memory limiter, not Redis limiter
            assert isinstance(limiter, WebSocketRateLimiter)


@pytest.mark.xdist_group(name="redis_rate_limiter")
class TestRateLimitInfo:
    """Test rate limit info structure for error responses."""

    def teardown_method(self) -> None:
        """Force GC to prevent mock accumulation in xdist workers."""
        gc.collect()

    def test_rate_limit_info_has_required_fields(self) -> None:
        """RateLimitInfo should have limit, remaining, and retry_after fields."""
        from mcp_server_langgraph.websocket.rate_limiter import RateLimitInfo

        info = RateLimitInfo(limit=600, remaining=0, retry_after=30)

        assert info.limit == 600
        assert info.remaining == 0
        assert info.retry_after == 30

    def test_rate_limit_info_to_dict(self) -> None:
        """RateLimitInfo should convert to dict for JSON serialization."""
        from mcp_server_langgraph.websocket.rate_limiter import RateLimitInfo

        info = RateLimitInfo(limit=600, remaining=100, retry_after=45)
        result = info.to_dict()

        assert result == {
            "limit": 600,
            "remaining": 100,
            "retry_after": 45,
        }

    def test_in_memory_limiter_provides_rate_limit_info(self) -> None:
        """In-memory rate limiter should return RateLimitInfo on check."""
        from mcp_server_langgraph.websocket.rate_limiter import (
            WebSocketRateLimiter,
            RateLimitInfo,
        )

        limiter = WebSocketRateLimiter(messages_per_minute=10)

        # Make several requests
        for _ in range(10):
            limiter.check_message("user-123")

        # Get rate limit info
        info = limiter.get_rate_limit_info("user-123")

        assert isinstance(info, RateLimitInfo)
        assert info.limit == 10
        assert info.remaining == 0
        assert info.retry_after >= 0  # Should be <= 60 seconds

    @pytest.mark.asyncio
    async def test_redis_limiter_provides_rate_limit_info(self) -> None:
        """Redis rate limiter should return RateLimitInfo on check."""
        from mcp_server_langgraph.websocket.rate_limiter import (
            RedisWebSocketRateLimiter,
            RateLimitInfo,
        )

        mock_redis = AsyncMock()  # noqa: async-mock-config
        mock_redis.get.return_value = b"10"  # 10 messages used
        mock_redis.ttl.return_value = 45  # 45 seconds until window resets

        with patch(
            "mcp_server_langgraph.websocket.rate_limiter.RedisWebSocketRateLimiter._ensure_connected",
            new_callable=AsyncMock,
        ):
            limiter = RedisWebSocketRateLimiter(
                redis_url="redis://localhost:6379/3",
                messages_per_minute=100,
            )
            limiter._redis_client = mock_redis

            info = await limiter.get_rate_limit_info("user-123")

            assert isinstance(info, RateLimitInfo)
            assert info.limit == 100
            # remaining should be 100 - 10 = 90
            assert info.remaining >= 0


@pytest.mark.xdist_group(name="rate_limit_error_response")
class TestRateLimitErrorResponse:
    """Tests for rate limit info in WebSocket error responses."""

    def teardown_method(self) -> None:
        """Force GC to prevent mock accumulation in xdist workers."""
        gc.collect()

    @pytest.mark.asyncio
    async def test_rate_limit_error_includes_limit_info(self) -> None:
        """
        GIVEN a WebSocket connection that exceeds rate limit
        WHEN rate limit error is sent
        THEN the error includes limit, remaining, and retry_after fields.
        """
        from mcp_server_langgraph.websocket.base import WebSocketBase
        from mcp_server_langgraph.websocket.types import (
            MessageEnvelope,
            WebSocketConfig,
        )
        from mcp_server_langgraph.websocket.rate_limiter import RateLimitInfo

        # Create a mock WebSocket
        mock_ws = AsyncMock()  # noqa: async-mock-config
        sent_messages: list[dict] = []
        mock_ws.send_json = AsyncMock(side_effect=lambda m: sent_messages.append(m))

        # Create a concrete implementation for testing
        class TestWebSocket(WebSocketBase):
            async def handle_message(self, message: MessageEnvelope):
                return None

        config = WebSocketConfig(
            endpoint_name="test",
            rate_limit_per_minute=10,
        )
        ws_handler = TestWebSocket(config)
        ws_handler._websocket = mock_ws

        # Create rate limit info
        rate_limit_info = RateLimitInfo(limit=10, remaining=0, retry_after=45)

        # Send error with rate limit info
        await ws_handler._send_error(
            mock_ws,
            "Rate limit exceeded",
            code="rate_limit_exceeded",
            correlation_id="test-123",
            rate_limit_info=rate_limit_info,
        )

        # Verify the sent message includes rate limit info
        assert len(sent_messages) == 1
        error_msg = sent_messages[0]
        assert error_msg["type"] == "error"
        assert error_msg["payload"]["code"] == "rate_limit_exceeded"
        assert error_msg["payload"]["rate_limit"]["limit"] == 10
        assert error_msg["payload"]["rate_limit"]["remaining"] == 0
        assert error_msg["payload"]["rate_limit"]["retry_after"] == 45


@pytest.mark.xdist_group(name="redis_health_check")
class TestRedisHealthCheck:
    """Tests for Redis connection health check."""

    def teardown_method(self) -> None:
        """Force GC to prevent mock accumulation in xdist workers."""
        gc.collect()

    @pytest.mark.asyncio
    async def test_health_check_returns_healthy_when_redis_responds(self) -> None:
        """
        GIVEN a Redis rate limiter with a healthy connection
        WHEN health_check is called
        THEN it returns a healthy status.
        """
        from mcp_server_langgraph.websocket.rate_limiter import (
            RedisWebSocketRateLimiter,
        )

        mock_redis = AsyncMock()  # noqa: async-mock-config
        mock_redis.ping.return_value = True

        with patch(
            "mcp_server_langgraph.websocket.rate_limiter.RedisWebSocketRateLimiter._ensure_connected",
            new_callable=AsyncMock,
        ):
            limiter = RedisWebSocketRateLimiter(
                redis_url="redis://localhost:6379/3",
                messages_per_minute=100,
            )
            limiter._redis_client = mock_redis

            health = await limiter.health_check()

            assert health["healthy"] is True
            assert health["component"] == "redis_rate_limiter"
            mock_redis.ping.assert_called_once()

    @pytest.mark.asyncio
    async def test_health_check_returns_unhealthy_on_ping_failure(self) -> None:
        """
        GIVEN a Redis rate limiter with a failing connection
        WHEN health_check is called
        THEN it returns an unhealthy status with error message.
        """
        from mcp_server_langgraph.websocket.rate_limiter import (
            RedisWebSocketRateLimiter,
        )

        mock_redis = AsyncMock()  # noqa: async-mock-config
        mock_redis.ping.side_effect = Exception("Connection refused")

        with patch(
            "mcp_server_langgraph.websocket.rate_limiter.RedisWebSocketRateLimiter._ensure_connected",
            new_callable=AsyncMock,
        ):
            limiter = RedisWebSocketRateLimiter(
                redis_url="redis://localhost:6379/3",
                messages_per_minute=100,
            )
            limiter._redis_client = mock_redis

            health = await limiter.health_check()

            assert health["healthy"] is False
            assert health["component"] == "redis_rate_limiter"
            assert "error" in health
            assert "Connection refused" in health["error"]

    @pytest.mark.asyncio
    async def test_health_check_returns_unhealthy_when_not_connected(self) -> None:
        """
        GIVEN a Redis rate limiter that has not connected yet
        WHEN health_check is called
        THEN it returns an unhealthy status indicating no connection.
        """
        from mcp_server_langgraph.websocket.rate_limiter import (
            RedisWebSocketRateLimiter,
        )

        limiter = RedisWebSocketRateLimiter(
            redis_url="redis://localhost:6379/3",
            messages_per_minute=100,
        )
        # Don't set _redis_client - simulating not connected

        health = await limiter.health_check()

        assert health["healthy"] is False
        assert health["component"] == "redis_rate_limiter"
        assert "error" in health
        assert "not connected" in health["error"].lower()
