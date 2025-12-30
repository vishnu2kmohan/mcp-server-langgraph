"""
Redis Rate Limiter Integration Tests.

Integration tests for Redis-backed WebSocket rate limiting using actual Redis.
Tests distributed rate limiting behavior across multiple connections.

Prerequisites:
- Redis must be running (uses docker-compose.test.yml redis-test container)
- Tests are skipped if Redis is not available

Architecture:
- Uses real Redis connections to verify rate limiting behavior
- Tests feature flag integration for distributed rate limiting
- Verifies failover behavior when Redis is unavailable
"""

from __future__ import annotations

import asyncio
import gc
import os
from typing import AsyncGenerator

import pytest
import redis.asyncio as redis

pytestmark = [
    pytest.mark.integration,
    pytest.mark.websocket,
    pytest.mark.redis,
    pytest.mark.xdist_group(name="redis_rate_limiter_integration"),
]

# Redis connection settings from test environment
REDIS_HOST = os.getenv("REDIS_HOST", "localhost")
REDIS_PORT = int(os.getenv("REDIS_PORT", "9379"))
REDIS_RATE_LIMIT_DB = int(os.getenv("REDIS_RATE_LIMIT_DB", "3"))


async def is_redis_available() -> bool:
    """Check if Redis is available for testing."""
    try:
        client = redis.Redis(
            host=REDIS_HOST,
            port=REDIS_PORT,
            db=REDIS_RATE_LIMIT_DB,
            decode_responses=True,
        )
        await client.ping()
        await client.aclose()
        return True
    except Exception:
        return False


@pytest.fixture
async def redis_client() -> AsyncGenerator[redis.Redis, None]:
    """Create a Redis client for testing."""
    client = redis.Redis(
        host=REDIS_HOST,
        port=REDIS_PORT,
        db=REDIS_RATE_LIMIT_DB,
        decode_responses=False,  # Binary mode for rate limiter compatibility
    )

    # Clean up test keys before each test
    async for key in client.scan_iter(match="ratelimit:ws:test:*"):
        await client.delete(key)

    yield client

    # Clean up test keys after each test
    async for key in client.scan_iter(match="ratelimit:ws:test:*"):
        await client.delete(key)

    await client.aclose()


@pytest.mark.skipif(
    not asyncio.get_event_loop().run_until_complete(is_redis_available()),
    reason="Redis not available",
)
class TestRedisUserRateLimiterIntegration:
    """Integration tests for RedisUserRateLimiter with real Redis."""

    def teardown_method(self) -> None:
        """Force GC to prevent mock accumulation in xdist workers."""
        gc.collect()

    @pytest.mark.asyncio
    async def test_rate_limit_increments_correctly(self, redis_client) -> None:
        """
        GIVEN a RedisUserRateLimiter with a real Redis connection
        WHEN incrementing the counter multiple times
        THEN the counter tracks correctly and respects the limit.
        """
        from mcp_server_langgraph.websocket.rate_limiter import RedisUserRateLimiter

        limiter = RedisUserRateLimiter(
            redis_client=redis_client,
            max_messages=5,
            window_seconds=60,
            key_prefix="ratelimit:ws:test:",
        )

        user_id = "integration-test-user-1"

        # First 5 messages should be allowed
        for i in range(5):
            result = await limiter.check_and_increment(user_id)
            assert result is True, f"Message {i + 1} should be allowed"

        # 6th message should be blocked
        result = await limiter.check_and_increment(user_id)
        assert result is False, "6th message should be blocked"

    @pytest.mark.asyncio
    async def test_get_remaining_quota(self, redis_client) -> None:
        """
        GIVEN a RedisUserRateLimiter with some messages consumed
        WHEN checking remaining quota
        THEN the remaining count is accurate.
        """
        from mcp_server_langgraph.websocket.rate_limiter import RedisUserRateLimiter

        limiter = RedisUserRateLimiter(
            redis_client=redis_client,
            max_messages=100,
            window_seconds=60,
            key_prefix="ratelimit:ws:test:",
        )

        user_id = "integration-test-user-2"

        # Initially should have full quota
        remaining = await limiter.get_remaining(user_id)
        assert remaining == 100

        # Consume 30 messages
        for _ in range(30):
            await limiter.check_and_increment(user_id)

        # Should have 70 remaining
        remaining = await limiter.get_remaining(user_id)
        assert remaining == 70

    @pytest.mark.asyncio
    async def test_different_users_have_separate_limits(self, redis_client) -> None:
        """
        GIVEN multiple users with the same rate limit
        WHEN they each consume their quota
        THEN their limits are tracked independently.
        """
        from mcp_server_langgraph.websocket.rate_limiter import RedisUserRateLimiter

        limiter = RedisUserRateLimiter(
            redis_client=redis_client,
            max_messages=10,
            window_seconds=60,
            key_prefix="ratelimit:ws:test:",
        )

        user_a = "integration-test-user-a"
        user_b = "integration-test-user-b"

        # User A consumes their full quota
        for _ in range(10):
            await limiter.check_and_increment(user_a)

        # User B should still have full quota
        remaining_b = await limiter.get_remaining(user_b)
        assert remaining_b == 10

        # User A should be blocked
        result_a = await limiter.check_and_increment(user_a)
        assert result_a is False

        # User B can still send
        result_b = await limiter.check_and_increment(user_b)
        assert result_b is True

    @pytest.mark.asyncio
    async def test_key_expiry_is_set(self, redis_client) -> None:
        """
        GIVEN a RedisUserRateLimiter
        WHEN a rate limit key is created
        THEN the key has an expiry set.
        """
        from mcp_server_langgraph.websocket.rate_limiter import RedisUserRateLimiter

        limiter = RedisUserRateLimiter(
            redis_client=redis_client,
            max_messages=100,
            window_seconds=60,
            key_prefix="ratelimit:ws:test:",
        )

        user_id = "integration-test-user-expiry"
        await limiter.check_and_increment(user_id)

        # Check that the key has a TTL
        key = f"ratelimit:ws:test:{user_id}"
        ttl = await redis_client.ttl(key)

        assert ttl > 0, "Key should have a TTL set"
        assert ttl <= 60, "TTL should be at most 60 seconds"


@pytest.mark.skipif(
    not asyncio.get_event_loop().run_until_complete(is_redis_available()),
    reason="Redis not available",
)
class TestRedisWebSocketRateLimiterIntegration:
    """Integration tests for RedisWebSocketRateLimiter with real Redis."""

    def teardown_method(self) -> None:
        """Force GC to prevent mock accumulation in xdist workers."""
        gc.collect()

    @pytest.mark.asyncio
    async def test_websocket_rate_limiter_with_real_redis(self, redis_client) -> None:
        """
        GIVEN a RedisWebSocketRateLimiter
        WHEN checking messages through the rate limiter
        THEN rate limiting works correctly.
        """
        from mcp_server_langgraph.websocket.rate_limiter import (
            RedisUserRateLimiter,
            RedisWebSocketRateLimiter,
        )

        redis_url = f"redis://{REDIS_HOST}:{REDIS_PORT}/{REDIS_RATE_LIMIT_DB}"
        limiter = RedisWebSocketRateLimiter(
            redis_url=redis_url,
            messages_per_minute=10,
        )

        # Manually set up the internal components for testing
        limiter._redis_client = redis_client
        limiter._user_limiter = RedisUserRateLimiter(
            redis_client=redis_client,
            max_messages=10,
            window_seconds=60,
            key_prefix="ratelimit:ws:test:ws:",
        )

        user_id = "integration-test-ws-user"

        # Check message should work for first 10
        for i in range(10):
            result = await limiter.check_message(user_id)
            assert result is True, f"Message {i + 1} should be allowed"

        # 11th should be blocked
        result = await limiter.check_message(user_id)
        assert result is False

    @pytest.mark.asyncio
    async def test_get_stats_returns_accurate_data(self, redis_client) -> None:
        """
        GIVEN a RedisWebSocketRateLimiter with some messages consumed
        WHEN getting stats
        THEN the stats are accurate.
        """
        from mcp_server_langgraph.websocket.rate_limiter import (
            RedisUserRateLimiter,
            RedisWebSocketRateLimiter,
        )

        redis_url = f"redis://{REDIS_HOST}:{REDIS_PORT}/{REDIS_RATE_LIMIT_DB}"
        limiter = RedisWebSocketRateLimiter(
            redis_url=redis_url,
            messages_per_minute=100,
        )

        limiter._redis_client = redis_client
        limiter._user_limiter = RedisUserRateLimiter(
            redis_client=redis_client,
            max_messages=100,
            window_seconds=60,
            key_prefix="ratelimit:ws:test:stats:",
        )

        user_id = "integration-test-stats-user"

        # Consume 25 messages
        for _ in range(25):
            await limiter.check_message(user_id)

        # Get stats
        stats = await limiter.get_stats(user_id)

        assert stats["limit"] == 100
        assert stats["used"] == 25
        assert stats["remaining"] == 75


@pytest.mark.skipif(
    not asyncio.get_event_loop().run_until_complete(is_redis_available()),
    reason="Redis not available",
)
class TestDistributedRateLimitingIntegration:
    """Integration tests for distributed rate limiting across connections."""

    def teardown_method(self) -> None:
        """Force GC to prevent mock accumulation in xdist workers."""
        gc.collect()

    @pytest.mark.asyncio
    async def test_rate_limit_shared_across_connections(self, redis_client) -> None:
        """
        GIVEN multiple rate limiter instances for the same user
        WHEN they both consume quota
        THEN the quota is shared (not per-instance).
        """
        from mcp_server_langgraph.websocket.rate_limiter import RedisUserRateLimiter

        # Create two separate limiter instances (simulating multiple server instances)
        limiter_1 = RedisUserRateLimiter(
            redis_client=redis_client,
            max_messages=10,
            window_seconds=60,
            key_prefix="ratelimit:ws:test:distributed:",
        )

        limiter_2 = RedisUserRateLimiter(
            redis_client=redis_client,
            max_messages=10,
            window_seconds=60,
            key_prefix="ratelimit:ws:test:distributed:",
        )

        user_id = "distributed-test-user"

        # Instance 1 consumes 5 messages
        for _ in range(5):
            await limiter_1.check_and_increment(user_id)

        # Instance 2 should see the same remaining quota
        remaining_from_2 = await limiter_2.get_remaining(user_id)
        assert remaining_from_2 == 5, "Second instance should see shared quota"

        # Instance 2 consumes remaining 5
        for _ in range(5):
            await limiter_2.check_and_increment(user_id)

        # Both instances should now see the user as blocked
        result_1 = await limiter_1.check_and_increment(user_id)
        result_2 = await limiter_2.check_and_increment(user_id)

        assert result_1 is False, "Instance 1 should see user blocked"
        assert result_2 is False, "Instance 2 should see user blocked"


class TestFeatureFlagControlledRateLimiting:
    """Tests for feature flag controlled rate limiter selection."""

    def teardown_method(self) -> None:
        """Force GC to prevent mock accumulation in xdist workers."""
        gc.collect()

    def test_in_memory_limiter_returned_when_flag_disabled(self) -> None:
        """
        GIVEN enable_distributed_rate_limiting is False
        WHEN get_websocket_rate_limiter is called
        THEN in-memory WebSocketRateLimiter is returned.
        """
        from unittest.mock import MagicMock, patch

        from mcp_server_langgraph.websocket.rate_limiter import (
            WebSocketRateLimiter,
            get_websocket_rate_limiter,
        )

        with patch("mcp_server_langgraph.core.feature_flags.get_feature_flags") as mock_ff:
            mock_ff.return_value = MagicMock(enable_distributed_rate_limiting=False)

            limiter = get_websocket_rate_limiter(messages_per_minute=600)

            assert isinstance(limiter, WebSocketRateLimiter)

    def test_redis_limiter_returned_when_flag_enabled(self) -> None:
        """
        GIVEN enable_distributed_rate_limiting is True
        WHEN get_websocket_rate_limiter is called
        THEN RedisWebSocketRateLimiter is returned.
        """
        from unittest.mock import MagicMock, patch

        from mcp_server_langgraph.websocket.rate_limiter import (
            RedisWebSocketRateLimiter,
            get_websocket_rate_limiter,
        )

        with patch("mcp_server_langgraph.core.feature_flags.get_feature_flags") as mock_ff:
            mock_ff.return_value = MagicMock(enable_distributed_rate_limiting=True)

            with patch("mcp_server_langgraph.core.config.settings") as mock_settings:
                mock_settings.redis_host = "localhost"
                mock_settings.redis_port = 6379
                mock_settings.redis_rate_limit_db = 3

                limiter = get_websocket_rate_limiter(messages_per_minute=600)

                assert isinstance(limiter, RedisWebSocketRateLimiter)
