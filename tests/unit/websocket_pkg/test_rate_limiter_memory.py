"""
Unit tests for in-memory WebSocket Rate Limiting.

Tests the MessageRateLimiter, UserRateLimiter, ConnectionRateLimiter,
and WebSocketRateLimiter classes for in-memory rate limiting.
"""

from __future__ import annotations

import gc
from datetime import UTC, datetime, timedelta
from unittest.mock import MagicMock, patch

import pytest

pytestmark = [
    pytest.mark.unit,
    pytest.mark.websocket,
    pytest.mark.xdist_group(name="memory_rate_limiter"),
]


@pytest.mark.xdist_group(name="message_rate_limiter")
class TestMessageRateLimiter:
    """Tests for MessageRateLimiter class."""

    def teardown_method(self) -> None:
        """Force GC to prevent mock accumulation in xdist workers."""
        gc.collect()

    def test_init_stores_parameters(self) -> None:
        """GIVEN rate limiter params WHEN creating THEN stores them."""
        from mcp_server_langgraph.websocket.rate_limiter import MessageRateLimiter

        limiter = MessageRateLimiter(max_messages=100, window_seconds=60)

        assert limiter.max_messages == 100
        assert limiter.window_seconds == 60
        assert limiter._message_count == 0

    def test_check_and_increment_allows_first_message(self) -> None:
        """GIVEN new limiter WHEN first message THEN allows it."""
        from mcp_server_langgraph.websocket.rate_limiter import MessageRateLimiter

        limiter = MessageRateLimiter(max_messages=10, window_seconds=60)

        result = limiter.check_and_increment()

        assert result is True
        assert limiter._message_count == 1

    def test_check_and_increment_allows_up_to_limit(self) -> None:
        """GIVEN limiter at limit-1 WHEN message THEN allows it."""
        from mcp_server_langgraph.websocket.rate_limiter import MessageRateLimiter

        limiter = MessageRateLimiter(max_messages=5, window_seconds=60)

        # Use up to limit
        for i in range(5):
            assert limiter.check_and_increment() is True

        assert limiter._message_count == 5

    def test_check_and_increment_blocks_at_limit(self) -> None:
        """GIVEN limiter at limit WHEN message THEN blocks it."""
        from mcp_server_langgraph.websocket.rate_limiter import MessageRateLimiter

        limiter = MessageRateLimiter(max_messages=5, window_seconds=60)

        # Hit the limit
        for _ in range(5):
            limiter.check_and_increment()

        # Next message should be blocked
        result = limiter.check_and_increment()

        assert result is False

    def test_check_and_increment_resets_after_window_expires(self) -> None:
        """GIVEN limiter at limit with expired window WHEN message THEN allows it."""
        from mcp_server_langgraph.websocket.rate_limiter import MessageRateLimiter

        limiter = MessageRateLimiter(max_messages=5, window_seconds=60)

        # Hit the limit
        for _ in range(5):
            limiter.check_and_increment()

        # Simulate window expiration
        limiter._window_start = datetime.now(UTC) - timedelta(seconds=61)

        # Next message should be allowed (window reset)
        result = limiter.check_and_increment()

        assert result is True
        assert limiter._message_count == 1

    def test_get_remaining_returns_full_quota_initially(self) -> None:
        """GIVEN new limiter WHEN get_remaining THEN returns max."""
        from mcp_server_langgraph.websocket.rate_limiter import MessageRateLimiter

        limiter = MessageRateLimiter(max_messages=100, window_seconds=60)

        remaining = limiter.get_remaining()

        assert remaining == 100

    def test_get_remaining_decreases_with_usage(self) -> None:
        """GIVEN limiter with usage WHEN get_remaining THEN returns correct value."""
        from mcp_server_langgraph.websocket.rate_limiter import MessageRateLimiter

        limiter = MessageRateLimiter(max_messages=100, window_seconds=60)

        # Use 30 messages
        for _ in range(30):
            limiter.check_and_increment()

        remaining = limiter.get_remaining()

        assert remaining == 70

    def test_get_remaining_returns_max_after_window_expires(self) -> None:
        """GIVEN expired window WHEN get_remaining THEN returns max."""
        from mcp_server_langgraph.websocket.rate_limiter import MessageRateLimiter

        limiter = MessageRateLimiter(max_messages=100, window_seconds=60)

        # Use some messages
        for _ in range(50):
            limiter.check_and_increment()

        # Expire window
        limiter._window_start = datetime.now(UTC) - timedelta(seconds=61)

        remaining = limiter.get_remaining()

        assert remaining == 100

    def test_get_retry_after_returns_time_until_reset(self) -> None:
        """GIVEN active window WHEN get_retry_after THEN returns remaining time."""
        from mcp_server_langgraph.websocket.rate_limiter import MessageRateLimiter

        limiter = MessageRateLimiter(max_messages=100, window_seconds=60)

        # Set window start to 30 seconds ago
        limiter._window_start = datetime.now(UTC) - timedelta(seconds=30)

        retry_after = limiter.get_retry_after()

        # Should be approximately 30 seconds left
        assert 28 <= retry_after <= 32

    def test_get_retry_after_returns_zero_when_expired(self) -> None:
        """GIVEN expired window WHEN get_retry_after THEN returns 0."""
        from mcp_server_langgraph.websocket.rate_limiter import MessageRateLimiter

        limiter = MessageRateLimiter(max_messages=100, window_seconds=60)

        # Expire window
        limiter._window_start = datetime.now(UTC) - timedelta(seconds=61)

        retry_after = limiter.get_retry_after()

        assert retry_after == 0

    def test_reset_clears_state(self) -> None:
        """GIVEN limiter with usage WHEN reset THEN clears count and resets window."""
        from mcp_server_langgraph.websocket.rate_limiter import MessageRateLimiter

        limiter = MessageRateLimiter(max_messages=100, window_seconds=60)

        # Use some messages
        for _ in range(50):
            limiter.check_and_increment()

        before_reset = datetime.now(UTC)
        limiter.reset()
        after_reset = datetime.now(UTC)

        assert limiter._message_count == 0
        assert before_reset <= limiter._window_start <= after_reset


@pytest.mark.xdist_group(name="user_rate_limiter")
class TestUserRateLimiter:
    """Tests for UserRateLimiter class."""

    def teardown_method(self) -> None:
        """Force GC to prevent mock accumulation in xdist workers."""
        gc.collect()

    def test_init_stores_parameters(self) -> None:
        """GIVEN rate limiter params WHEN creating THEN stores them."""
        from mcp_server_langgraph.websocket.rate_limiter import UserRateLimiter

        limiter = UserRateLimiter(max_messages=100, window_seconds=60)

        assert limiter.max_messages == 100
        assert limiter.window_seconds == 60
        assert limiter._user_limiters == {}

    def test_check_and_increment_creates_user_limiter(self) -> None:
        """GIVEN new user WHEN check_and_increment THEN creates limiter."""
        from mcp_server_langgraph.websocket.rate_limiter import UserRateLimiter

        limiter = UserRateLimiter(max_messages=100, window_seconds=60)

        result = limiter.check_and_increment("user-123")

        assert result is True
        assert "user-123" in limiter._user_limiters

    def test_check_and_increment_isolates_users(self) -> None:
        """GIVEN multiple users WHEN one hits limit THEN others unaffected."""
        from mcp_server_langgraph.websocket.rate_limiter import UserRateLimiter

        limiter = UserRateLimiter(max_messages=5, window_seconds=60)

        # User 1 hits limit
        for _ in range(5):
            limiter.check_and_increment("user-1")
        assert limiter.check_and_increment("user-1") is False

        # User 2 should still be allowed
        assert limiter.check_and_increment("user-2") is True

    def test_get_remaining_for_new_user(self) -> None:
        """GIVEN new user WHEN get_remaining THEN returns max."""
        from mcp_server_langgraph.websocket.rate_limiter import UserRateLimiter

        limiter = UserRateLimiter(max_messages=100, window_seconds=60)

        remaining = limiter.get_remaining("user-new")

        assert remaining == 100

    def test_get_remaining_for_existing_user(self) -> None:
        """GIVEN user with usage WHEN get_remaining THEN returns correct value."""
        from mcp_server_langgraph.websocket.rate_limiter import UserRateLimiter

        limiter = UserRateLimiter(max_messages=100, window_seconds=60)

        # User uses 25 messages
        for _ in range(25):
            limiter.check_and_increment("user-123")

        remaining = limiter.get_remaining("user-123")

        assert remaining == 75

    def test_get_retry_after_for_new_user(self) -> None:
        """GIVEN new user WHEN get_retry_after THEN returns 0."""
        from mcp_server_langgraph.websocket.rate_limiter import UserRateLimiter

        limiter = UserRateLimiter(max_messages=100, window_seconds=60)

        retry_after = limiter.get_retry_after("user-new")

        assert retry_after == 0

    def test_get_retry_after_for_existing_user(self) -> None:
        """GIVEN user with active window WHEN get_retry_after THEN returns time."""
        from mcp_server_langgraph.websocket.rate_limiter import UserRateLimiter

        limiter = UserRateLimiter(max_messages=100, window_seconds=60)

        # Create user limiter
        limiter.check_and_increment("user-123")

        retry_after = limiter.get_retry_after("user-123")

        # Should be close to 60 seconds
        assert 58 <= retry_after <= 60

    def test_get_user_count(self) -> None:
        """GIVEN multiple users WHEN get_user_count THEN returns count."""
        from mcp_server_langgraph.websocket.rate_limiter import UserRateLimiter

        limiter = UserRateLimiter(max_messages=100, window_seconds=60)

        limiter.check_and_increment("user-1")
        limiter.check_and_increment("user-2")
        limiter.check_and_increment("user-3")

        assert limiter.get_user_count() == 3

    def test_cleanup_expired_removes_old_limiters(self) -> None:
        """GIVEN expired user windows WHEN cleanup_expired THEN removes them."""
        from mcp_server_langgraph.websocket.rate_limiter import UserRateLimiter

        limiter = UserRateLimiter(max_messages=100, window_seconds=60)

        # Create user limiters
        limiter.check_and_increment("user-1")
        limiter.check_and_increment("user-2")

        # Expire one user's window
        limiter._user_limiters["user-1"]._window_start = datetime.now(UTC) - timedelta(seconds=61)

        # Cleanup
        limiter.cleanup_expired()

        # Only user-2 should remain
        assert "user-1" not in limiter._user_limiters
        assert "user-2" in limiter._user_limiters


@pytest.mark.xdist_group(name="connection_rate_limiter")
class TestConnectionRateLimiter:
    """Tests for ConnectionRateLimiter class."""

    def teardown_method(self) -> None:
        """Force GC to prevent mock accumulation in xdist workers."""
        gc.collect()

    def test_init_stores_max_connections(self) -> None:
        """GIVEN max_connections WHEN creating THEN stores it."""
        from mcp_server_langgraph.websocket.rate_limiter import ConnectionRateLimiter

        limiter = ConnectionRateLimiter(max_connections=1000)

        assert limiter.max_connections == 1000
        assert limiter._active_connections == 0

    def test_check_connection_allows_under_limit(self) -> None:
        """GIVEN connections under limit WHEN check_connection THEN allows."""
        from mcp_server_langgraph.websocket.rate_limiter import ConnectionRateLimiter

        limiter = ConnectionRateLimiter(max_connections=100)

        result = limiter.check_connection()

        assert result is True
        assert limiter._active_connections == 1

    def test_check_connection_blocks_at_limit(self) -> None:
        """GIVEN connections at limit WHEN check_connection THEN blocks."""
        from mcp_server_langgraph.websocket.rate_limiter import ConnectionRateLimiter

        limiter = ConnectionRateLimiter(max_connections=2)

        limiter.check_connection()
        limiter.check_connection()

        result = limiter.check_connection()

        assert result is False
        assert limiter._active_connections == 2

    def test_release_connection_decrements_count(self) -> None:
        """GIVEN active connections WHEN release_connection THEN decrements."""
        from mcp_server_langgraph.websocket.rate_limiter import ConnectionRateLimiter

        limiter = ConnectionRateLimiter(max_connections=100)

        limiter.check_connection()
        limiter.check_connection()
        assert limiter._active_connections == 2

        limiter.release_connection()

        assert limiter._active_connections == 1

    def test_release_connection_does_not_go_negative(self) -> None:
        """GIVEN no connections WHEN release_connection THEN stays at 0."""
        from mcp_server_langgraph.websocket.rate_limiter import ConnectionRateLimiter

        limiter = ConnectionRateLimiter(max_connections=100)

        limiter.release_connection()

        assert limiter._active_connections == 0

    def test_active_connections_property(self) -> None:
        """GIVEN limiter WHEN accessing property THEN returns count."""
        from mcp_server_langgraph.websocket.rate_limiter import ConnectionRateLimiter

        limiter = ConnectionRateLimiter(max_connections=100)

        limiter.check_connection()
        limiter.check_connection()

        assert limiter.active_connections == 2


@pytest.mark.xdist_group(name="websocket_rate_limiter")
class TestWebSocketRateLimiter:
    """Tests for WebSocketRateLimiter class."""

    def teardown_method(self) -> None:
        """Force GC to prevent mock accumulation in xdist workers."""
        gc.collect()

    def test_init_stores_parameters(self) -> None:
        """GIVEN params WHEN creating THEN stores them."""
        from mcp_server_langgraph.websocket.rate_limiter import WebSocketRateLimiter

        limiter = WebSocketRateLimiter(messages_per_minute=600, max_users=10000, cleanup_interval=300)

        assert limiter.messages_per_minute == 600
        assert limiter.max_users == 10000
        assert limiter.cleanup_interval == 300

    def test_check_message_with_user_id(self) -> None:
        """GIVEN user_id WHEN check_message THEN uses user limiter."""
        from mcp_server_langgraph.websocket.rate_limiter import WebSocketRateLimiter

        limiter = WebSocketRateLimiter(messages_per_minute=100)

        result = limiter.check_message("user-123")

        assert result is True

    def test_check_message_without_user_id(self) -> None:
        """GIVEN no user_id WHEN check_message THEN uses global limiter."""
        from mcp_server_langgraph.websocket.rate_limiter import WebSocketRateLimiter

        limiter = WebSocketRateLimiter(messages_per_minute=100)

        result = limiter.check_message()

        assert result is True

    def test_get_remaining_quota_with_user_id(self) -> None:
        """GIVEN user_id WHEN get_remaining_quota THEN uses user limiter."""
        from mcp_server_langgraph.websocket.rate_limiter import WebSocketRateLimiter

        limiter = WebSocketRateLimiter(messages_per_minute=100)

        # Use some messages
        for _ in range(30):
            limiter.check_message("user-123")

        remaining = limiter.get_remaining_quota("user-123")

        assert remaining == 70

    def test_get_remaining_quota_without_user_id(self) -> None:
        """GIVEN no user_id WHEN get_remaining_quota THEN uses global limiter."""
        from mcp_server_langgraph.websocket.rate_limiter import WebSocketRateLimiter

        limiter = WebSocketRateLimiter(messages_per_minute=100)

        # Use some global messages
        for _ in range(20):
            limiter.check_message()

        remaining = limiter.get_remaining_quota()

        assert remaining == 80

    def test_get_stats_returns_expected_format(self) -> None:
        """GIVEN limiter WHEN get_stats THEN returns expected structure."""
        from mcp_server_langgraph.websocket.rate_limiter import WebSocketRateLimiter

        limiter = WebSocketRateLimiter(messages_per_minute=600)

        # Add some users
        limiter.check_message("user-1")
        limiter.check_message("user-2")

        stats = limiter.get_stats()

        assert "messages_per_minute" in stats
        assert "active_users" in stats
        assert "global_remaining" in stats
        assert stats["messages_per_minute"] == 600
        assert stats["active_users"] == 2

    def test_get_rate_limit_info_with_user_id(self) -> None:
        """GIVEN user_id WHEN get_rate_limit_info THEN returns user's info."""
        from mcp_server_langgraph.websocket.rate_limiter import (
            WebSocketRateLimiter,
            RateLimitInfo,
        )

        limiter = WebSocketRateLimiter(messages_per_minute=100)

        # Use some messages
        for _ in range(30):
            limiter.check_message("user-123")

        info = limiter.get_rate_limit_info("user-123")

        assert isinstance(info, RateLimitInfo)
        assert info.limit == 100
        assert info.remaining == 70

    def test_get_rate_limit_info_without_user_id(self) -> None:
        """GIVEN no user_id WHEN get_rate_limit_info THEN returns global info."""
        from mcp_server_langgraph.websocket.rate_limiter import (
            WebSocketRateLimiter,
            RateLimitInfo,
        )

        limiter = WebSocketRateLimiter(messages_per_minute=100)

        # Use some global messages
        for _ in range(40):
            limiter.check_message()

        info = limiter.get_rate_limit_info()

        assert isinstance(info, RateLimitInfo)
        assert info.limit == 100
        assert info.remaining == 60

    def test_maybe_cleanup_runs_after_interval(self) -> None:
        """GIVEN elapsed cleanup interval WHEN check_message THEN runs cleanup."""
        from mcp_server_langgraph.websocket.rate_limiter import WebSocketRateLimiter

        limiter = WebSocketRateLimiter(messages_per_minute=100, cleanup_interval=60)

        # Create a user
        limiter.check_message("user-1")

        # Expire the user's window
        limiter._user_limiter._user_limiters["user-1"]._window_start = datetime.now(UTC) - timedelta(seconds=61)

        # Set last cleanup to long ago
        limiter._last_cleanup = datetime.now(UTC) - timedelta(seconds=61)

        # This should trigger cleanup
        limiter.check_message("user-2")

        # User-1 should be cleaned up (expired)
        assert "user-1" not in limiter._user_limiter._user_limiters
        assert "user-2" in limiter._user_limiter._user_limiters


@pytest.mark.xdist_group(name="redis_rate_limiter_extras")
class TestRedisUserRateLimiterExtras:
    """Additional tests for RedisUserRateLimiter coverage."""

    def teardown_method(self) -> None:
        """Force GC to prevent mock accumulation in xdist workers."""
        gc.collect()

    @pytest.mark.asyncio
    async def test_get_retry_after_with_ttl(self) -> None:
        """GIVEN Redis TTL WHEN get_retry_after THEN returns TTL value."""
        from unittest.mock import AsyncMock

        from mcp_server_langgraph.websocket.rate_limiter import RedisUserRateLimiter

        mock_redis = AsyncMock()  # noqa: async-mock-config
        mock_redis.ttl.return_value = 45

        limiter = RedisUserRateLimiter(redis_client=mock_redis, max_messages=100, window_seconds=60)

        retry_after = await limiter.get_retry_after("user-123")

        assert retry_after == 45

    @pytest.mark.asyncio
    async def test_get_retry_after_no_key(self) -> None:
        """GIVEN no key in Redis WHEN get_retry_after THEN returns 0."""
        from unittest.mock import AsyncMock

        from mcp_server_langgraph.websocket.rate_limiter import RedisUserRateLimiter

        mock_redis = AsyncMock()  # noqa: async-mock-config
        mock_redis.ttl.return_value = -2  # Key doesn't exist

        limiter = RedisUserRateLimiter(redis_client=mock_redis, max_messages=100, window_seconds=60)

        retry_after = await limiter.get_retry_after("user-123")

        assert retry_after == 0

    @pytest.mark.asyncio
    async def test_get_retry_after_no_expire(self) -> None:
        """GIVEN key without expire WHEN get_retry_after THEN returns 0."""
        from unittest.mock import AsyncMock

        from mcp_server_langgraph.websocket.rate_limiter import RedisUserRateLimiter

        mock_redis = AsyncMock()  # noqa: async-mock-config
        mock_redis.ttl.return_value = -1  # Key has no expire

        limiter = RedisUserRateLimiter(redis_client=mock_redis, max_messages=100, window_seconds=60)

        retry_after = await limiter.get_retry_after("user-123")

        assert retry_after == 0

    @pytest.mark.asyncio
    async def test_get_retry_after_on_error(self) -> None:
        """GIVEN Redis error WHEN get_retry_after THEN returns 0."""
        from unittest.mock import AsyncMock

        from mcp_server_langgraph.websocket.rate_limiter import RedisUserRateLimiter

        mock_redis = AsyncMock()  # noqa: async-mock-config
        mock_redis.ttl.side_effect = Exception("Redis error")

        limiter = RedisUserRateLimiter(redis_client=mock_redis, max_messages=100, window_seconds=60)

        retry_after = await limiter.get_retry_after("user-123")

        assert retry_after == 0


@pytest.mark.xdist_group(name="redis_ws_rate_limiter_extras")
class TestRedisWebSocketRateLimiterExtras:
    """Additional tests for RedisWebSocketRateLimiter coverage."""

    def teardown_method(self) -> None:
        """Force GC to prevent mock accumulation in xdist workers."""
        gc.collect()

    @pytest.mark.asyncio
    async def test_check_message_anonymous_user(self) -> None:
        """GIVEN no user_id WHEN check_message THEN uses anonymous key."""
        from unittest.mock import AsyncMock

        from mcp_server_langgraph.websocket.rate_limiter import (
            RedisUserRateLimiter,
            RedisWebSocketRateLimiter,
        )

        mock_redis = AsyncMock()  # noqa: async-mock-config
        mock_redis.incr.return_value = 1
        mock_redis.expire.return_value = True

        limiter = RedisWebSocketRateLimiter(redis_url="redis://localhost:6379/3", messages_per_minute=600)
        limiter._redis_client = mock_redis
        limiter._user_limiter = RedisUserRateLimiter(redis_client=mock_redis, max_messages=600, window_seconds=60)

        result = await limiter.check_message()  # No user_id

        assert result is True
        # Should use __anonymous__ as key
        mock_redis.incr.assert_called_once()

    @pytest.mark.asyncio
    async def test_check_message_when_limiter_none(self) -> None:
        """GIVEN no user_limiter WHEN check_message THEN returns fail_open."""
        from mcp_server_langgraph.websocket.rate_limiter import (
            RedisWebSocketRateLimiter,
        )

        limiter = RedisWebSocketRateLimiter(redis_url="redis://localhost:6379/3", messages_per_minute=600, fail_open=True)
        limiter._redis_client = MagicMock()
        limiter._user_limiter = None

        with patch.object(limiter, "_ensure_connected"):
            result = await limiter.check_message("user-123")

        assert result is True  # fail_open=True

    @pytest.mark.asyncio
    async def test_get_remaining_quota_when_limiter_none(self) -> None:
        """GIVEN no user_limiter WHEN get_remaining_quota THEN returns max."""
        from mcp_server_langgraph.websocket.rate_limiter import (
            RedisWebSocketRateLimiter,
        )

        limiter = RedisWebSocketRateLimiter(redis_url="redis://localhost:6379/3", messages_per_minute=600)
        limiter._redis_client = MagicMock()
        limiter._user_limiter = None

        with patch.object(limiter, "_ensure_connected"):
            remaining = await limiter.get_remaining_quota("user-123")

        assert remaining == 600

    @pytest.mark.asyncio
    async def test_get_stats_anonymous(self) -> None:
        """GIVEN no user_id WHEN get_stats THEN uses anonymous."""
        from unittest.mock import AsyncMock

        from mcp_server_langgraph.websocket.rate_limiter import (
            RedisUserRateLimiter,
            RedisWebSocketRateLimiter,
        )

        mock_redis = AsyncMock()  # noqa: async-mock-config
        mock_redis.get.return_value = b"10"

        limiter = RedisWebSocketRateLimiter(redis_url="redis://localhost:6379/3", messages_per_minute=600)
        limiter._redis_client = mock_redis
        limiter._user_limiter = RedisUserRateLimiter(redis_client=mock_redis, max_messages=600, window_seconds=60)

        stats = await limiter.get_stats()  # No user_id

        assert stats["user_id"] == "__anonymous__"

    @pytest.mark.asyncio
    async def test_get_rate_limit_info_anonymous(self) -> None:
        """GIVEN no user_id WHEN get_rate_limit_info THEN uses anonymous."""
        from unittest.mock import AsyncMock

        from mcp_server_langgraph.websocket.rate_limiter import (
            RedisUserRateLimiter,
            RedisWebSocketRateLimiter,
            RateLimitInfo,
        )

        mock_redis = AsyncMock()  # noqa: async-mock-config
        mock_redis.get.return_value = b"50"
        mock_redis.ttl.return_value = 30

        limiter = RedisWebSocketRateLimiter(redis_url="redis://localhost:6379/3", messages_per_minute=600)
        limiter._redis_client = mock_redis
        limiter._user_limiter = RedisUserRateLimiter(redis_client=mock_redis, max_messages=600, window_seconds=60)

        info = await limiter.get_rate_limit_info()  # No user_id

        assert isinstance(info, RateLimitInfo)
        assert info.limit == 600

    @pytest.mark.asyncio
    async def test_close_closes_redis(self) -> None:
        """GIVEN connected limiter WHEN close THEN closes redis."""
        from unittest.mock import AsyncMock

        from mcp_server_langgraph.websocket.rate_limiter import (
            RedisWebSocketRateLimiter,
        )

        mock_redis = AsyncMock()  # noqa: async-mock-config

        limiter = RedisWebSocketRateLimiter(redis_url="redis://localhost:6379/3", messages_per_minute=600)
        limiter._redis_client = mock_redis
        limiter._user_limiter = MagicMock()

        await limiter.close()

        mock_redis.close.assert_called_once()
        assert limiter._redis_client is None
        assert limiter._user_limiter is None


@pytest.mark.xdist_group(name="rate_limiter_factory")
class TestRateLimiterFactory:
    """Tests for rate limiter factory functions."""

    def teardown_method(self) -> None:
        """Force GC to prevent mock accumulation in xdist workers."""
        gc.collect()

    def test_get_websocket_rate_limiter_returns_redis_when_enabled(self) -> None:
        """GIVEN distributed flag enabled WHEN get_websocket_rate_limiter THEN returns Redis limiter."""
        from mcp_server_langgraph.websocket.rate_limiter import (
            RedisWebSocketRateLimiter,
            get_websocket_rate_limiter,
        )

        mock_ff = MagicMock()
        mock_ff.enable_distributed_rate_limiting = True

        mock_settings = MagicMock(redis_host="localhost", redis_port=6379, redis_rate_limit_db=5)

        with patch(
            "mcp_server_langgraph.core.feature_flags.get_feature_flags",
            return_value=mock_ff,
        ):
            with patch(
                "mcp_server_langgraph.core.config.settings",
                mock_settings,
            ):
                limiter = get_websocket_rate_limiter(messages_per_minute=600)

        assert isinstance(limiter, RedisWebSocketRateLimiter)

    def test_get_websocket_rate_limiter_handles_feature_flag_error(self) -> None:
        """GIVEN feature flag error WHEN get_websocket_rate_limiter THEN falls back to memory."""
        from mcp_server_langgraph.websocket.rate_limiter import (
            WebSocketRateLimiter,
            get_websocket_rate_limiter,
        )

        with patch(
            "mcp_server_langgraph.core.feature_flags.get_feature_flags",
            side_effect=Exception("Feature flags unavailable"),
        ):
            limiter = get_websocket_rate_limiter(messages_per_minute=600)

        assert isinstance(limiter, WebSocketRateLimiter)
