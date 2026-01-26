"""
WebSocketRateLimiter Unit Tests.

TDD tests for WebSocket rate limiting functionality.
"""

from __future__ import annotations

import gc
from datetime import UTC, datetime, timedelta

import pytest

pytestmark = [pytest.mark.unit, pytest.mark.websocket]


@pytest.mark.xdist_group(name="websocket_rate_limiter")
class TestMessageRateLimiter:
    """Test single connection rate limiter."""

    def teardown_method(self) -> None:
        """Force GC to prevent mock accumulation in xdist workers."""
        gc.collect()

    def test_allows_messages_under_limit(self) -> None:
        """
        GIVEN a rate limiter with max_messages=5
        WHEN 5 messages are sent
        THEN all should be allowed.
        """
        from mcp_server_langgraph.websocket.rate_limiter import MessageRateLimiter

        limiter = MessageRateLimiter(max_messages=5, window_seconds=60)

        for i in range(5):
            assert limiter.check_and_increment() is True, f"Message {i + 1} should be allowed"

    def test_blocks_messages_over_limit(self) -> None:
        """
        GIVEN a rate limiter with max_messages=5
        WHEN 6 messages are sent
        THEN the 6th should be blocked.
        """
        from mcp_server_langgraph.websocket.rate_limiter import MessageRateLimiter

        limiter = MessageRateLimiter(max_messages=5, window_seconds=60)

        for _ in range(5):
            limiter.check_and_increment()

        assert limiter.check_and_increment() is False, "6th message should be blocked"

    def test_resets_after_window_expires(self) -> None:
        """
        GIVEN a rate limiter that has reached its limit
        WHEN the window expires
        THEN messages should be allowed again.
        """
        from mcp_server_langgraph.websocket.rate_limiter import MessageRateLimiter

        limiter = MessageRateLimiter(max_messages=2, window_seconds=1)

        # Use up the limit
        limiter.check_and_increment()
        limiter.check_and_increment()
        assert limiter.check_and_increment() is False

        # Simulate window expiry
        limiter._window_start = datetime.now(UTC) - timedelta(seconds=2)

        # Should be allowed again
        assert limiter.check_and_increment() is True

    def test_reset_clears_counter(self) -> None:
        """
        GIVEN a rate limiter with messages counted
        WHEN reset() is called
        THEN counter should be cleared.
        """
        from mcp_server_langgraph.websocket.rate_limiter import MessageRateLimiter

        limiter = MessageRateLimiter(max_messages=2, window_seconds=60)

        limiter.check_and_increment()
        limiter.check_and_increment()
        assert limiter.check_and_increment() is False

        limiter.reset()

        assert limiter.check_and_increment() is True


@pytest.mark.xdist_group(name="websocket_rate_limiter")
class TestUserRateLimiter:
    """Test per-user rate limiter."""

    def teardown_method(self) -> None:
        """Force GC to prevent mock accumulation in xdist workers."""
        gc.collect()

    def test_tracks_users_independently(self) -> None:
        """
        GIVEN a per-user rate limiter
        WHEN different users send messages
        THEN each user should have independent limits.
        """
        from mcp_server_langgraph.websocket.rate_limiter import UserRateLimiter

        limiter = UserRateLimiter(max_messages=2, window_seconds=60)

        # User A uses up limit
        assert limiter.check_and_increment("user-a") is True
        assert limiter.check_and_increment("user-a") is True
        assert limiter.check_and_increment("user-a") is False

        # User B should still have full limit
        assert limiter.check_and_increment("user-b") is True
        assert limiter.check_and_increment("user-b") is True
        assert limiter.check_and_increment("user-b") is False

    def test_get_user_count(self) -> None:
        """
        GIVEN a per-user rate limiter
        WHEN different users send messages
        THEN user count should be tracked.
        """
        from mcp_server_langgraph.websocket.rate_limiter import UserRateLimiter

        limiter = UserRateLimiter(max_messages=5, window_seconds=60)

        limiter.check_and_increment("user-a")
        limiter.check_and_increment("user-b")
        limiter.check_and_increment("user-c")

        assert limiter.get_user_count() == 3

    def test_cleanup_expired_removes_old_users(self) -> None:
        """
        GIVEN a per-user rate limiter with expired user windows
        WHEN cleanup_expired() is called
        THEN expired users should be removed.
        """
        from mcp_server_langgraph.websocket.rate_limiter import UserRateLimiter

        limiter = UserRateLimiter(max_messages=5, window_seconds=1)

        limiter.check_and_increment("user-a")
        limiter.check_and_increment("user-b")

        # Simulate expiry
        for user_limiter in limiter._user_limiters.values():
            user_limiter._window_start = datetime.now(UTC) - timedelta(seconds=2)

        limiter.cleanup_expired()

        assert limiter.get_user_count() == 0


@pytest.mark.xdist_group(name="websocket_rate_limiter")
class TestWebSocketRateLimiter:
    """Test combined WebSocket rate limiter."""

    def teardown_method(self) -> None:
        """Force GC to prevent mock accumulation in xdist workers."""
        gc.collect()

    def test_check_message_with_user(self) -> None:
        """
        GIVEN a WebSocket rate limiter
        WHEN check_message() is called with user_id
        THEN user rate limiting should apply.
        """
        from mcp_server_langgraph.websocket.rate_limiter import WebSocketRateLimiter

        limiter = WebSocketRateLimiter(messages_per_minute=2, max_users=100)

        assert limiter.check_message("user-a") is True
        assert limiter.check_message("user-a") is True
        assert limiter.check_message("user-a") is False

    def test_check_message_without_user(self) -> None:
        """
        GIVEN a WebSocket rate limiter
        WHEN check_message() is called without user_id
        THEN global rate limiting should apply.
        """
        from mcp_server_langgraph.websocket.rate_limiter import WebSocketRateLimiter

        limiter = WebSocketRateLimiter(messages_per_minute=3, max_users=100)

        assert limiter.check_message() is True
        assert limiter.check_message() is True
        assert limiter.check_message() is True
        assert limiter.check_message() is False

    def test_get_remaining_quota_user(self) -> None:
        """
        GIVEN a WebSocket rate limiter
        WHEN get_remaining_quota() is called for a user
        THEN remaining quota should be returned.
        """
        from mcp_server_langgraph.websocket.rate_limiter import WebSocketRateLimiter

        limiter = WebSocketRateLimiter(messages_per_minute=5, max_users=100)

        limiter.check_message("user-a")
        limiter.check_message("user-a")

        remaining = limiter.get_remaining_quota("user-a")
        assert remaining == 3

    def test_get_stats_returns_limit_info(self) -> None:
        """
        GIVEN a WebSocket rate limiter with activity
        WHEN get_stats() is called
        THEN statistics should be returned.
        """
        from mcp_server_langgraph.websocket.rate_limiter import WebSocketRateLimiter

        limiter = WebSocketRateLimiter(messages_per_minute=10, max_users=100)

        limiter.check_message("user-a")
        limiter.check_message("user-b")

        stats = limiter.get_stats()

        assert stats["messages_per_minute"] == 10
        assert stats["active_users"] == 2


@pytest.mark.xdist_group(name="websocket_rate_limiter")
class TestConnectionRateLimiter:
    """Test connection rate limiting."""

    def teardown_method(self) -> None:
        """Force GC to prevent mock accumulation in xdist workers."""
        gc.collect()

    def test_allows_connections_under_limit(self) -> None:
        """
        GIVEN a connection rate limiter
        WHEN connections are under the limit
        THEN they should be allowed.
        """
        from mcp_server_langgraph.websocket.rate_limiter import ConnectionRateLimiter

        limiter = ConnectionRateLimiter(max_connections=3)

        assert limiter.check_connection() is True
        assert limiter.check_connection() is True
        assert limiter.check_connection() is True

    def test_blocks_connections_over_limit(self) -> None:
        """
        GIVEN a connection rate limiter at capacity
        WHEN another connection is attempted
        THEN it should be blocked.
        """
        from mcp_server_langgraph.websocket.rate_limiter import ConnectionRateLimiter

        limiter = ConnectionRateLimiter(max_connections=2)

        limiter.check_connection()
        limiter.check_connection()

        assert limiter.check_connection() is False

    def test_release_connection_frees_slot(self) -> None:
        """
        GIVEN a connection rate limiter at capacity
        WHEN release_connection() is called
        THEN a new connection should be allowed.
        """
        from mcp_server_langgraph.websocket.rate_limiter import ConnectionRateLimiter

        limiter = ConnectionRateLimiter(max_connections=2)

        limiter.check_connection()
        limiter.check_connection()
        assert limiter.check_connection() is False

        limiter.release_connection()
        assert limiter.check_connection() is True
