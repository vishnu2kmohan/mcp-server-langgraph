"""Unit tests for rate_limiter.py - Rate Limiting Middleware"""

import gc
from unittest.mock import MagicMock, patch

import pytest
from fastapi import Request

from mcp_server_langgraph.middleware.rate_limiter import (

pytestmark = pytest.mark.unit

    get_dynamic_limit,
    get_rate_limit_for_tier,
    get_rate_limit_key,
    get_user_id_from_jwt,
    get_user_tier,
)


@pytest.mark.api
@pytest.mark.xdist_group(name="rate_limiter_tests")
class TestRateLimiterUserExtraction:
    """Test extracting user info from JWT tokens for rate limiting"""

    def teardown_method(self):
        """Force GC to prevent mock accumulation in xdist workers"""
        gc.collect()

    def test_get_user_id_from_jwt_with_valid_token(self):
        """Test extracting user ID from request.state.user set by AuthMiddleware"""
        # Create mock request with user already set by AuthMiddleware
        request = MagicMock(spec=Request)

        # Mock request.state.user as it would be set by AuthMiddleware
        request.state.user = {"user_id": "user:alice", "sub": "user:alice"}

        user_id = get_user_id_from_jwt(request)

        assert user_id == "user:alice"

    def test_get_user_id_from_jwt_with_user_id_claim(self):
        """Test extracting user_id claim from request.state.user"""
        request = MagicMock(spec=Request)

        # Mock request.state.user with user_id claim
        request.state.user = {"user_id": "alice_123"}

        user_id = get_user_id_from_jwt(request)

        assert user_id == "alice_123"

    def test_get_user_id_from_jwt_with_expired_token(self):
        """Test that user ID is extracted even with expired token data in state"""
        request = MagicMock(spec=Request)

        # AuthMiddleware would have set this even for expired tokens (by design for rate limiting)
        request.state.user = {"user_id": "user:bob", "sub": "user:bob"}

        user_id = get_user_id_from_jwt(request)

        assert user_id == "user:bob"

    def test_get_user_id_from_jwt_with_invalid_token(self):
        """Test handling when AuthMiddleware didn't set user (invalid token)"""
        request = MagicMock(spec=Request)
        # No user set in request.state (AuthMiddleware rejected the token)
        request.state.user = None

        user_id = get_user_id_from_jwt(request)

        assert user_id is None

    def test_get_user_id_from_jwt_without_bearer_token(self):
        """Test handling request without user in state (no auth)"""
        request = MagicMock(spec=Request)
        # No user attribute in request.state at all
        delattr(request.state, "user") if hasattr(request.state, "user") else None

        user_id = get_user_id_from_jwt(request)

        assert user_id is None

    def test_get_user_id_from_jwt_with_malformed_header(self):
        """Test handling when state.user is not set (malformed header)"""
        request = MagicMock(spec=Request)
        # AuthMiddleware didn't set user due to malformed header
        request.state.user = None

        user_id = get_user_id_from_jwt(request)

        assert user_id is None


@pytest.mark.unit
@pytest.mark.api
@pytest.mark.xdist_group(name="rate_limiter_tests")
class TestRateLimiterTierExtraction:
    """Test tier extraction for tiered rate limiting"""

    def teardown_method(self):
        """Force GC to prevent mock accumulation in xdist workers"""
        gc.collect()

    def test_get_user_tier_for_premium_user(self):
        """Test extracting premium tier from request.state.user"""
        request = MagicMock(spec=Request)

        # Mock user with premium tier in roles
        request.state.user = {"user_id": "user:alice", "roles": ["premium"]}

        tier = get_user_tier(request)

        assert tier == "premium"

    def test_get_user_tier_for_enterprise_user(self):
        """Test extracting enterprise tier from request.state.user"""
        request = MagicMock(spec=Request)

        # Mock user with enterprise role
        request.state.user = {"user_id": "user:admin", "roles": ["enterprise"]}

        tier = get_user_tier(request)

        assert tier == "enterprise"

    def test_get_user_tier_defaults_to_free(self):
        """Test default tier when user has no roles or tier field"""
        request = MagicMock(spec=Request)

        # Mock user without roles or tier fields
        request.state.user = {"user_id": "user:newuser"}

        tier = get_user_tier(request)

        assert tier == "free"

    def test_get_user_tier_for_anonymous_user(self):
        """Test anonymous tier when no user in state"""
        request = MagicMock(spec=Request)
        # No user in state
        request.state.user = None

        tier = get_user_tier(request)

        assert tier == "anonymous"

    def test_get_user_tier_with_plan_claim(self):
        """Test extracting tier from 'plan' field (fallback from roles)"""
        request = MagicMock(spec=Request)

        # Mock user with plan field instead of roles
        request.state.user = {"user_id": "user:alice", "plan": "standard"}

        tier = get_user_tier(request)

        assert tier == "standard"

    def test_get_user_tier_rejects_invalid_tiers(self):
        """Test that invalid tier names default to free"""
        request = MagicMock(spec=Request)

        # Mock user with invalid tier value
        request.state.user = {"user_id": "user:hacker", "tier": "super_mega_unlimited"}

        tier = get_user_tier(request)

        # Should default to free for invalid tiers
        assert tier == "free"


@pytest.mark.unit
@pytest.mark.api
@pytest.mark.xdist_group(name="rate_limiter_tests")
class TestRateLimiterKeyGeneration:
    """Test rate limit key generation (user > IP > global)"""

    def teardown_method(self):
        """Force GC to prevent mock accumulation in xdist workers"""
        gc.collect()

    def test_get_rate_limit_key_for_authenticated_user(self):
        """Test rate limit key uses user ID for authenticated users"""
        request = MagicMock(spec=Request)

        # Mock authenticated user in request.state
        request.state.user = {"user_id": "user:alice"}

        key = get_rate_limit_key(request)

        assert key == "user:user:alice"

    def test_get_rate_limit_key_for_anonymous_by_ip(self):
        """Test rate limit key uses IP address for anonymous users"""
        request = MagicMock(spec=Request)
        # No user in state
        request.state.user = None

        with patch("mcp_server_langgraph.middleware.rate_limiter.get_remote_address") as mock_get_ip:
            mock_get_ip.return_value = "192.168.1.100"

            key = get_rate_limit_key(request)

        assert key == "ip:192.168.1.100"

    def test_get_rate_limit_key_fallback_to_global(self):
        """Test rate limit key falls back to global when no user ID or IP"""
        request = MagicMock(spec=Request)
        # No user in state
        request.state.user = None

        with patch("mcp_server_langgraph.middleware.rate_limiter.get_remote_address") as mock_get_ip:
            mock_get_ip.return_value = None  # No IP either

            key = get_rate_limit_key(request)

        assert key == "global:anonymous"


@pytest.mark.unit
@pytest.mark.api
@pytest.mark.xdist_group(name="rate_limiter_tests")
class TestRateLimiterTierLimits:
    """Test tiered rate limit values"""

    def teardown_method(self):
        """Force GC to prevent mock accumulation in xdist workers"""
        gc.collect()

    def test_rate_limit_for_tier_anonymous(self):
        """Test anonymous users get lowest limit"""
        limit = get_rate_limit_for_tier("anonymous")
        assert limit == "10/minute"

    def test_rate_limit_for_tier_free(self):
        """Test free tier users get basic limit"""
        limit = get_rate_limit_for_tier("free")
        assert limit == "60/minute"

    def test_rate_limit_for_tier_standard(self):
        """Test standard tier users get higher limit"""
        limit = get_rate_limit_for_tier("standard")
        assert limit == "300/minute"

    def test_rate_limit_for_tier_premium(self):
        """Test premium tier users get generous limit"""
        limit = get_rate_limit_for_tier("premium")
        assert limit == "1000/minute"

    def test_rate_limit_for_tier_enterprise(self):
        """Test enterprise tier users get unlimited access"""
        limit = get_rate_limit_for_tier("enterprise")
        assert limit == "999999/minute"

    def test_rate_limit_for_invalid_tier_defaults_to_free(self):
        """Test invalid tier defaults to free tier limit"""
        limit = get_rate_limit_for_tier("invalid_tier")
        assert limit == "60/minute"


@pytest.mark.unit
@pytest.mark.api
@pytest.mark.xdist_group(name="rate_limiter_tests")
class TestDynamicRateLimiting:
    """Test dynamic rate limit determination"""

    def teardown_method(self):
        """Force GC to prevent mock accumulation in xdist workers"""
        gc.collect()

    def test_get_dynamic_limit_for_premium_user(self):
        """Test dynamic rate limiting applies premium limits"""
        request = MagicMock(spec=Request)

        # Mock premium user in request.state
        request.state.user = {"user_id": "user:premium_user", "roles": ["premium"]}

        limit = get_dynamic_limit(request)

        assert limit == "1000/minute"

    def test_get_dynamic_limit_for_anonymous_user(self):
        """Test dynamic rate limiting applies anonymous limits"""
        request = MagicMock(spec=Request)
        # No user in state
        request.state.user = None

        limit = get_dynamic_limit(request)

        assert limit == "10/minute"

    def test_get_dynamic_limit_for_enterprise_user(self):
        """Test dynamic rate limiting applies enterprise limits"""
        request = MagicMock(spec=Request)

        # Mock enterprise user in request.state
        request.state.user = {"user_id": "user:enterprise_user", "roles": ["enterprise"]}

        limit = get_dynamic_limit(request)

        assert limit == "999999/minute"


@pytest.mark.unit
@pytest.mark.api
@pytest.mark.xdist_group(name="rate_limiter_tests")
class TestRateLimiterSecurityProperties:
    """Test security properties of rate limiter"""

    def teardown_method(self):
        """Force GC to prevent mock accumulation in xdist workers"""
        gc.collect()

    def test_rate_limiter_does_not_expose_secret_key(self):
        """
        SECURITY: Ensure rate limiter doesn't expose JWT secret in errors.

        Rate limiting should gracefully handle errors without leaking sensitive info.
        """
        request = MagicMock(spec=Request)
        # No user in state (malformed token rejected by AuthMiddleware)
        request.state.user = None

        # Should not raise exception or expose secret
        user_id = get_user_id_from_jwt(request)
        tier = get_user_tier(request)

        assert user_id is None
        assert tier == "anonymous"

    def test_rate_limiter_prevents_tier_escalation(self):
        """
        SECURITY: Ensure users cannot escalate their tier via crafted JWTs.

        Invalid tiers should be rejected and downgraded to free tier.
        """
        request = MagicMock(spec=Request)

        # Mock user with invalid tier (AuthMiddleware would have validated signature but tier is invalid)
        request.state.user = {"user_id": "user:attacker", "tier": "super_admin"}

        tier = get_user_tier(request)
        limit = get_rate_limit_for_tier(tier)

        # Should get free tier, not enterprise
        assert tier == "free"
        assert limit == "60/minute"
        assert limit != "999999/minute"

    def test_rate_limiter_handles_jwt_signature_verification_failure(self):
        """
        SECURITY: Ensure rate limiter handles JWT signature verification failures.

        Tokens signed with wrong key should be rejected by AuthMiddleware (treated as anonymous).
        """
        request = MagicMock(spec=Request)

        # AuthMiddleware would have rejected token with wrong signature
        # So request.state.user is None
        request.state.user = None

        user_id = get_user_id_from_jwt(request)
        tier = get_user_tier(request)

        # Should be treated as anonymous
        assert user_id is None
        assert tier == "anonymous"
