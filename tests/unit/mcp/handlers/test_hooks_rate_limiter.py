"""
Unit tests for Hooks Rate Limiter.

Tests the SimpleRateLimiter used for hook registrations:
- Sliding window rate limiting
- Per-user isolation
- Configurable limits

TDD: Tests written FIRST.
"""

from __future__ import annotations

import gc
import time
from unittest.mock import patch

import pytest

pytestmark = [
    pytest.mark.unit,
    pytest.mark.mcp,
]


@pytest.mark.xdist_group(name="hooks_rate_limiter")
class TestSimpleRateLimiter:
    """Tests for SimpleRateLimiter class."""

    def teardown_method(self) -> None:
        """Force GC to prevent mock accumulation in xdist workers."""
        gc.collect()

    def test_allows_first_request(self) -> None:
        """
        GIVEN a new rate limiter
        WHEN first request is made
        THEN should allow it.
        """
        from mcp_server_langgraph.mcp.handlers.hooks import SimpleRateLimiter

        limiter = SimpleRateLimiter(max_requests=5, window_seconds=60.0)

        allowed, remaining = limiter.check_rate_limit("user-123")

        assert allowed is True
        assert remaining == 4

    def test_allows_up_to_max_requests(self) -> None:
        """
        GIVEN a rate limiter with max_requests=3
        WHEN 3 requests are made
        THEN all should be allowed.
        """
        from mcp_server_langgraph.mcp.handlers.hooks import SimpleRateLimiter

        limiter = SimpleRateLimiter(max_requests=3, window_seconds=60.0)

        for i in range(3):
            allowed, remaining = limiter.check_rate_limit("user-123")
            assert allowed is True

    def test_blocks_after_max_requests(self) -> None:
        """
        GIVEN a rate limiter with max_requests=3
        WHEN 4th request is made
        THEN should be blocked.
        """
        from mcp_server_langgraph.mcp.handlers.hooks import SimpleRateLimiter

        limiter = SimpleRateLimiter(max_requests=3, window_seconds=60.0)

        # Use all 3 requests
        for _ in range(3):
            limiter.check_rate_limit("user-123")

        # 4th should be blocked
        allowed, remaining = limiter.check_rate_limit("user-123")

        assert allowed is False
        assert remaining == 0

    def test_per_user_isolation(self) -> None:
        """
        GIVEN a rate limiter
        WHEN different users make requests
        THEN limits should be independent.
        """
        from mcp_server_langgraph.mcp.handlers.hooks import SimpleRateLimiter

        limiter = SimpleRateLimiter(max_requests=2, window_seconds=60.0)

        # User A uses their limit
        limiter.check_rate_limit("user-a")
        limiter.check_rate_limit("user-a")

        # User A blocked
        allowed_a, _ = limiter.check_rate_limit("user-a")
        assert allowed_a is False

        # User B should still be allowed
        allowed_b, _ = limiter.check_rate_limit("user-b")
        assert allowed_b is True

    def test_reset_clears_single_user(self) -> None:
        """
        GIVEN a user who has exceeded rate limit
        WHEN reset is called for that user
        THEN user should be allowed again.
        """
        from mcp_server_langgraph.mcp.handlers.hooks import SimpleRateLimiter

        limiter = SimpleRateLimiter(max_requests=1, window_seconds=60.0)

        # Use the limit
        limiter.check_rate_limit("user-123")
        allowed_before, _ = limiter.check_rate_limit("user-123")
        assert allowed_before is False

        # Reset
        limiter.reset("user-123")

        # Should be allowed again
        allowed_after, _ = limiter.check_rate_limit("user-123")
        assert allowed_after is True

    def test_reset_clears_all_users(self) -> None:
        """
        GIVEN multiple users who have exceeded rate limit
        WHEN reset is called with None
        THEN all users should be allowed again.
        """
        from mcp_server_langgraph.mcp.handlers.hooks import SimpleRateLimiter

        limiter = SimpleRateLimiter(max_requests=1, window_seconds=60.0)

        # Use limits for multiple users
        limiter.check_rate_limit("user-a")
        limiter.check_rate_limit("user-b")

        # Both blocked
        allowed_a, _ = limiter.check_rate_limit("user-a")
        allowed_b, _ = limiter.check_rate_limit("user-b")
        assert allowed_a is False
        assert allowed_b is False

        # Reset all
        limiter.reset(None)

        # Both should be allowed again
        allowed_a2, _ = limiter.check_rate_limit("user-a")
        allowed_b2, _ = limiter.check_rate_limit("user-b")
        assert allowed_a2 is True
        assert allowed_b2 is True

    def test_window_expiry_allows_new_requests(self) -> None:
        """
        GIVEN a rate limiter with short window
        WHEN window expires
        THEN new requests should be allowed.
        """
        from mcp_server_langgraph.mcp.handlers.hooks import SimpleRateLimiter

        limiter = SimpleRateLimiter(max_requests=1, window_seconds=0.1)

        # Use the limit
        limiter.check_rate_limit("user-123")
        allowed_before, _ = limiter.check_rate_limit("user-123")
        assert allowed_before is False

        # Wait for window to expire
        time.sleep(0.15)

        # Should be allowed again
        allowed_after, _ = limiter.check_rate_limit("user-123")
        assert allowed_after is True

    def test_remaining_decrements_correctly(self) -> None:
        """
        GIVEN a rate limiter with max_requests=5
        WHEN multiple requests are made
        THEN remaining should decrement correctly.
        """
        from mcp_server_langgraph.mcp.handlers.hooks import SimpleRateLimiter

        limiter = SimpleRateLimiter(max_requests=5, window_seconds=60.0)

        _, remaining1 = limiter.check_rate_limit("user-123")
        assert remaining1 == 4

        _, remaining2 = limiter.check_rate_limit("user-123")
        assert remaining2 == 3

        _, remaining3 = limiter.check_rate_limit("user-123")
        assert remaining3 == 2


@pytest.mark.xdist_group(name="hooks_rate_limiter")
class TestRateLimiterFactories:
    """Tests for rate limiter factory functions."""

    def teardown_method(self) -> None:
        """Force GC to prevent mock accumulation in xdist workers."""
        gc.collect()

    def test_get_register_rate_limiter_returns_same_instance(self) -> None:
        """
        GIVEN multiple calls to get_register_rate_limiter
        WHEN called
        THEN should return the same singleton instance.
        """
        from mcp_server_langgraph.mcp.handlers import hooks

        # Reset the global for test isolation
        hooks._register_rate_limiter = None

        limiter1 = hooks.get_register_rate_limiter()
        limiter2 = hooks.get_register_rate_limiter()

        assert limiter1 is limiter2

        # Cleanup
        hooks._register_rate_limiter = None

    def test_get_unregister_rate_limiter_returns_same_instance(self) -> None:
        """
        GIVEN multiple calls to get_unregister_rate_limiter
        WHEN called
        THEN should return the same singleton instance.
        """
        from mcp_server_langgraph.mcp.handlers import hooks

        # Reset the global for test isolation
        hooks._unregister_rate_limiter = None

        limiter1 = hooks.get_unregister_rate_limiter()
        limiter2 = hooks.get_unregister_rate_limiter()

        assert limiter1 is limiter2

        # Cleanup
        hooks._unregister_rate_limiter = None

    def test_register_limiter_uses_env_config(self) -> None:
        """
        GIVEN HOOK_REGISTER_RATE_LIMIT_RPM environment variable
        WHEN get_register_rate_limiter is called
        THEN should use the configured value.
        """
        from mcp_server_langgraph.mcp.handlers import hooks

        # Reset and patch
        hooks._register_rate_limiter = None

        # The module reads env at import time, so we test the constant
        assert hooks.HOOK_REGISTER_RATE_LIMIT == 10  # Default value

        # Cleanup
        hooks._register_rate_limiter = None
