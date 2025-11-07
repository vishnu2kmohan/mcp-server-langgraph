"""
Comprehensive tests for rate limiting middleware.

Tests:
- Tiered rate limits (anonymous, free, standard, premium, enterprise)
- User tier extraction from JWT
- Rate limit key generation (user ID > IP > global)
- Redis-backed distributed rate limiting
- Custom rate limit exception handler
- Endpoint-specific rate limit decorators
- Fail-open behavior when Redis is unavailable
"""

from unittest.mock import Mock, patch

import jwt
import pytest
from fastapi import FastAPI, Request
from slowapi.errors import RateLimitExceeded

from mcp_server_langgraph.middleware.rate_limiter import (
    ENDPOINT_RATE_LIMITS,
    RATE_LIMITS,
    custom_rate_limit_exceeded_handler,
    exempt_from_rate_limit,
    get_dynamic_limit,
    get_rate_limit_for_tier,
    get_rate_limit_key,
    get_redis_storage_uri,
    get_user_id_from_jwt,
    get_user_tier,
    limiter,
    rate_limit_for_auth,
    rate_limit_for_llm,
    rate_limit_for_search,
    setup_rate_limiting,
)


def mock_request_no_auth():
    """Mock request without authentication"""
    request = Mock(spec=Request)
    request.headers = {}
    request.url = Mock()
    request.url.path = "/test"
    request.method = "GET"
    request.client = Mock()
    request.client.host = "192.168.1.1"
    return request


@pytest.fixture
def mock_request_with_jwt(mock_request_no_auth):
    """Mock request with valid JWT"""
    # Create valid JWT token
    secret_key = "test-secret-key"
    payload = {
        "sub": "user:alice",
        "user_id": "alice",
        "tier": "premium",
        "exp": 9999999999,  # Far future
    }
    token = jwt.encode(payload, secret_key, algorithm="HS256")

    mock_request_no_auth.headers = {"Authorization": f"Bearer {token}"}

    # Patch settings to use our test secret
    with patch("mcp_server_langgraph.middleware.rate_limiter.settings") as mock_settings:
        mock_settings.jwt_secret_key = secret_key
        mock_settings.jwt_algorithm = "HS256"
        yield mock_request_no_auth


class TestRateLimitConstants:
    """Test rate limit configuration constants"""

    def test_rate_limits_defined(self):
        """Test all tier rate limits are defined"""
        assert "anonymous" in RATE_LIMITS
        assert "free" in RATE_LIMITS
        assert "standard" in RATE_LIMITS
        assert "premium" in RATE_LIMITS
        assert "enterprise" in RATE_LIMITS

    def test_rate_limits_progressive(self):
        """Test rate limits increase with tier"""
        anonymous_limit = int(RATE_LIMITS["anonymous"].split("/")[0])
        free_limit = int(RATE_LIMITS["free"].split("/")[0])
        standard_limit = int(RATE_LIMITS["standard"].split("/")[0])
        premium_limit = int(RATE_LIMITS["premium"].split("/")[0])

        assert anonymous_limit < free_limit < standard_limit < premium_limit

    def test_endpoint_rate_limits_defined(self):
        """Test endpoint-specific rate limits"""
        assert "auth_login" in ENDPOINT_RATE_LIMITS
        assert "auth_register" in ENDPOINT_RATE_LIMITS
        assert "llm_chat" in ENDPOINT_RATE_LIMITS
        assert "search" in ENDPOINT_RATE_LIMITS
        assert "read" in ENDPOINT_RATE_LIMITS

    def test_auth_endpoints_have_strict_limits(self):
        """Test authentication endpoints have strict limits"""
        login_limit = int(ENDPOINT_RATE_LIMITS["auth_login"].split("/")[0])
        register_limit = int(ENDPOINT_RATE_LIMITS["auth_register"].split("/")[0])

        # Auth should be strict to prevent brute force
        assert login_limit <= 10
        assert register_limit <= 10


class TestUserIDExtraction:
    """
    Test user ID extraction from JWT

    NOTE: get_user_id_from_jwt() relies on request.state.user being set by
    AuthMiddleware to avoid event loop issues in slowapi's synchronous context.
    """

    def test_get_user_id_from_request_state(self):
        """Test extracting user ID from request.state.user (preferred method)"""
        # Test using request.state.user (already authenticated)
        request = Mock(spec=Request)
        request.state = Mock()
        request.state.user = {"user_id": "user:alice"}
        request.headers = {}

        user_id = get_user_id_from_jwt(request)
        assert user_id == "user:alice"

    def test_get_user_id_from_valid_jwt(self):
        """Test extracting user ID from request.state.user"""
        request = Mock(spec=Request)
        request.state = Mock()
        request.state.user = {"user_id": "user:alice"}

        user_id = get_user_id_from_jwt(request)
        assert user_id == "user:alice"

    def test_get_user_id_fallback_to_user_id_claim(self):
        """Test extracting user_id claim from request.state.user"""
        request = Mock(spec=Request)
        request.state = Mock()
        request.state.user = {"user_id": "alice"}

        user_id = get_user_id_from_jwt(request)
        assert user_id == "alice"

    def test_get_user_id_no_auth_header(self, mock_request_no_auth):
        """Test user ID extraction with no auth header"""
        mock_request_no_auth.state = Mock()
        mock_request_no_auth.state.user = None

        user_id = get_user_id_from_jwt(mock_request_no_auth)
        assert user_id is None

    def test_get_user_id_invalid_token_format(self):
        """Test user ID extraction with invalid token format (no user in state)"""
        request = Mock(spec=Request)
        request.state = Mock()
        request.state.user = None  # AuthMiddleware didn't set user due to invalid format

        user_id = get_user_id_from_jwt(request)
        assert user_id is None

    def test_get_user_id_invalid_jwt(self):
        """Test user ID extraction with invalid JWT (no user in state)"""
        request = Mock(spec=Request)
        request.state = Mock()
        request.state.user = None  # AuthMiddleware rejected invalid JWT

        user_id = get_user_id_from_jwt(request)
        assert user_id is None


class TestUserTierExtraction:
    """
    Test user tier extraction from JWT

    NOTE: get_user_tier() relies on request.state.user being set by
    AuthMiddleware to avoid event loop issues in slowapi's synchronous context.
    """

    def test_get_tier_from_request_state(self):
        """Test extracting tier from request.state.user (preferred method)"""
        # Test using request.state.user (already authenticated)
        request = Mock(spec=Request)
        request.state = Mock()
        request.state.user = {"roles": ["premium"]}
        request.headers = {}

        tier = get_user_tier(request)
        assert tier == "premium"

    def test_get_tier_from_valid_jwt(self):
        """Test extracting tier from request.state.user"""
        request = Mock(spec=Request)
        request.state = Mock()
        request.state.user = {"user_id": "user:alice", "tier": "premium"}

        tier = get_user_tier(request)
        assert tier == "premium"

    def test_get_tier_fallback_to_plan_claim(self):
        """Test fallback to 'plan' field in request.state.user"""
        request = Mock(spec=Request)
        request.state = Mock()
        request.state.user = {"user_id": "user:alice", "plan": "standard"}

        tier = get_user_tier(request)
        assert tier == "standard"

    def test_get_tier_defaults_to_free(self):
        """Test tier defaults to 'free' when user has no tier/roles"""
        request = Mock(spec=Request)
        request.state = Mock()
        request.state.user = {"user_id": "user:alice"}  # No tier or roles

        tier = get_user_tier(request)
        assert tier == "free"

    def test_get_tier_anonymous_no_auth(self, mock_request_no_auth):
        """Test tier is 'anonymous' with no authentication"""
        mock_request_no_auth.state = Mock()
        mock_request_no_auth.state.user = None

        tier = get_user_tier(mock_request_no_auth)
        assert tier == "anonymous"

    def test_get_tier_invalid_tier_defaults_to_free(self):
        """Test that invalid tier names default to 'free'"""
        request = Mock(spec=Request)
        request.state = Mock()
        request.state.user = {"user_id": "user:alice", "tier": "invalid_tier"}

        tier = get_user_tier(request)
        assert tier == "free"


class TestRateLimitKeyGeneration:
    """Test rate limit key generation"""

    def test_key_prioritizes_user_id(self):
        """Test rate limit key prioritizes user ID from request.state.user"""
        request = Mock(spec=Request)
        request.state = Mock()
        request.state.user = {"user_id": "user:alice"}
        request.client = Mock()
        request.client.host = "192.168.1.1"

        key = get_rate_limit_key(request)
        assert key == "user:user:alice"

    def test_key_falls_back_to_ip(self, mock_request_no_auth):
        """Test rate limit key falls back to IP address"""
        mock_request_no_auth.state = Mock()
        mock_request_no_auth.state.user = None

        with patch("mcp_server_langgraph.middleware.rate_limiter.get_remote_address") as mock_get_ip:
            mock_get_ip.return_value = "192.168.1.1"

            key = get_rate_limit_key(mock_request_no_auth)
            assert key == "ip:192.168.1.1"

    def test_key_global_anonymous_fallback(self, mock_request_no_auth):
        """Test rate limit key falls back to global anonymous"""
        mock_request_no_auth.state = Mock()
        mock_request_no_auth.state.user = None

        with patch("mcp_server_langgraph.middleware.rate_limiter.get_remote_address") as mock_get_ip:
            mock_get_ip.return_value = None

            key = get_rate_limit_key(mock_request_no_auth)
            assert key == "global:anonymous"


class TestRateLimitForTier:
    """Test tier-based rate limit determination"""

    def test_get_rate_limit_for_each_tier(self):
        """Test getting rate limit for each tier"""
        assert get_rate_limit_for_tier("anonymous") == "10/minute"
        assert get_rate_limit_for_tier("free") == "60/minute"
        assert get_rate_limit_for_tier("standard") == "300/minute"
        assert get_rate_limit_for_tier("premium") == "1000/minute"
        assert get_rate_limit_for_tier("enterprise") == "999999/minute"

    def test_get_rate_limit_defaults_to_free(self):
        """Test unknown tier defaults to free tier"""
        assert get_rate_limit_for_tier("unknown") == RATE_LIMITS["free"]


class TestDynamicLimitDetermination:
    """Test dynamic limit determination from request"""

    def test_dynamic_limit_for_premium_user(self):
        """Test dynamic limit for premium user"""
        request = Mock(spec=Request)
        request.state = Mock()
        request.state.user = {"user_id": "user:alice", "tier": "premium"}

        limit = get_dynamic_limit(request)
        assert limit == "1000/minute"

    def test_dynamic_limit_for_anonymous(self, mock_request_no_auth):
        """Test dynamic limit for anonymous user"""
        mock_request_no_auth.state = Mock()
        mock_request_no_auth.state.user = None

        limit = get_dynamic_limit(mock_request_no_auth)
        assert limit == "10/minute"


class TestRedisStorageURI:
    """Test Redis storage URI generation"""

    def test_get_redis_storage_uri_default(self):
        """Test Redis storage URI with default settings"""
        uri = get_redis_storage_uri()
        assert uri.startswith("redis://")
        assert "/3" in uri  # Default DB 3 for rate limiting

    def test_get_redis_storage_uri_format(self):
        """Test Redis URI format"""
        with patch("mcp_server_langgraph.middleware.rate_limiter.settings") as mock_settings:
            mock_settings.redis_host = "redis.example.com"
            mock_settings.redis_port = 6380
            mock_settings.redis_rate_limit_db = 5

            uri = get_redis_storage_uri()
            assert uri == "redis://redis.example.com:6380/5"


class TestCustomRateLimitHandler:
    """Test custom rate limit exceeded handler"""

    @pytest.mark.asyncio
    async def test_rate_limit_handler_response_structure(self):
        """Test rate limit handler returns proper structure"""
        request = Mock(spec=Request)
        request.state = Mock()
        request.state.user = {"user_id": "user:alice", "tier": "free"}
        request.url = Mock()
        request.url.path = "/api/chat"
        request.method = "POST"

        # Create mock limit object for RateLimitExceeded
        mock_limit = Mock()
        mock_limit.error_message = "Rate limit exceeded"
        exc = RateLimitExceeded(mock_limit)

        response = await custom_rate_limit_exceeded_handler(request, exc)

        assert response.status_code == 429
        assert "Retry-After" in response.headers
        assert "X-RateLimit-Limit" in response.headers
        assert "X-RateLimit-Remaining" in response.headers
        assert response.headers["X-RateLimit-Remaining"] == "0"

    @pytest.mark.asyncio
    async def test_rate_limit_handler_includes_tier_info(self, mock_request_no_auth):
        """Test rate limit handler includes tier information"""
        mock_request_no_auth.state = Mock()
        mock_request_no_auth.state.user = None  # Anonymous user

        mock_limit = Mock()
        mock_limit.error_message = "Rate limit exceeded"
        exc = RateLimitExceeded(mock_limit)

        response = await custom_rate_limit_exceeded_handler(mock_request_no_auth, exc)

        # Should be anonymous tier
        content = response.body.decode()
        assert "anonymous" in content or "Rate limit exceeded" in content


class TestSetupRateLimiting:
    """Test rate limiting setup function"""

    def test_setup_adds_limiter_to_app_state(self):
        """Test setup_rate_limiting adds limiter to app state"""
        app = FastAPI()

        setup_rate_limiting(app)

        assert hasattr(app.state, "limiter")
        assert app.state.limiter == limiter

    def test_setup_registers_exception_handler(self):
        """Test setup_rate_limiting registers exception handler"""
        app = FastAPI()

        setup_rate_limiting(app)

        # Check that exception handler was registered
        assert RateLimitExceeded in app.exception_handlers


class TestEndpointSpecificDecorators:
    """Test endpoint-specific rate limit decorators"""

    def test_rate_limit_for_auth_decorator(self):
        """Test auth endpoint rate limiter"""

        @rate_limit_for_auth
        async def login_endpoint(request: Request):
            return {"token": "test"}

        # Decorator should be applied
        assert hasattr(login_endpoint, "__wrapped__")

    def test_rate_limit_for_llm_decorator(self):
        """Test LLM endpoint rate limiter"""

        @rate_limit_for_llm
        async def chat_endpoint(request: Request):
            return {"response": "Hello"}

        assert hasattr(chat_endpoint, "__wrapped__")

    def test_rate_limit_for_search_decorator(self):
        """Test search endpoint rate limiter"""

        @rate_limit_for_search
        async def search_endpoint(request: Request):
            return {"results": []}

        assert hasattr(search_endpoint, "__wrapped__")

    def test_exempt_from_rate_limit_decorator(self):
        """Test rate limit exemption decorator"""

        @exempt_from_rate_limit
        async def health_endpoint():
            return {"status": "healthy"}

        assert hasattr(health_endpoint, "__wrapped__")


class TestLimiterConfiguration:
    """Test limiter instance configuration"""

    def test_limiter_has_correct_key_func(self):
        """Test limiter uses correct key function"""
        assert limiter._key_func == get_rate_limit_key

    def test_limiter_uses_fixed_window_strategy(self):
        """Test limiter uses fixed-window strategy"""
        assert limiter._strategy == "fixed-window"

    def test_limiter_headers_enabled(self):
        """Test limiter has headers enabled"""
        assert limiter._headers_enabled is True

    def test_limiter_swallows_errors(self):
        """Test limiter is configured to fail-open"""
        # swallow_errors=True means rate limiting failures won't break requests
        assert limiter._swallow_errors is True


class TestRateLimitingIntegration:
    """Integration tests for rate limiting"""

    def test_rate_limit_key_hierarchy(self):
        """Test that rate limit key follows hierarchy (user > IP > global)"""
        # 1. User ID (highest priority)
        request = Mock(spec=Request)
        request.state = Mock()
        request.state.user = {"user_id": "user:alice"}
        request.client = Mock()
        request.client.host = "192.168.1.1"

        key = get_rate_limit_key(request)
        # Should prioritize user ID
        assert key.startswith("user:")
        assert "alice" in key

    def test_full_tier_based_limiting_flow(self):
        """Test complete tier-based rate limiting flow"""
        for tier_name, expected_limit in RATE_LIMITS.items():
            request = Mock(spec=Request)
            request.state = Mock()
            request.state.user = {"user_id": f"user:{tier_name}", "tier": tier_name}

            tier = get_user_tier(request)
            limit = get_dynamic_limit(request)

            assert tier == tier_name
            assert limit == expected_limit


class TestRateLimitErrorHandling:
    """Test error handling and resilience"""

    def test_jwt_decode_error_handled_gracefully(self):
        """Test that invalid tokens are handled gracefully (no user in state)"""
        request = Mock(spec=Request)
        request.state = Mock()
        request.state.user = None  # AuthMiddleware would have rejected corrupted token

        # Should return None, not crash
        user_id = get_user_id_from_jwt(request)
        assert user_id is None

        tier = get_user_tier(request)
        assert tier == "anonymous"

    def test_missing_jwt_secret_handled(self):
        """Test that missing JWT secret is handled (AuthMiddleware would fail)"""
        request = Mock(spec=Request)
        request.state = Mock()
        request.state.user = None  # AuthMiddleware would fail without JWT secret

        # Should handle gracefully
        user_id = get_user_id_from_jwt(request)
        assert user_id is None


class TestKeycloakIntegration:
    """Integration tests for Keycloak RS256 token support"""

    def test_get_user_id_from_request_state(self):
        """Test user ID extraction from request.state.user (auth middleware)"""
        request = Mock(spec=Request)
        request.state = Mock()
        request.state.user = {
            "user_id": "user:alice",
            "keycloak_id": "8c7b4e5d-1234-5678-abcd-ef1234567890",
            "username": "alice",
            "roles": ["premium"],
        }
        request.headers = {}

        user_id = get_user_id_from_jwt(request)
        assert user_id == "user:alice"

    def test_get_tier_from_request_state_roles(self):
        """Test tier extraction from request.state.user roles"""
        request = Mock(spec=Request)
        request.state = Mock()
        request.state.user = {
            "user_id": "user:alice",
            "username": "alice",
            "roles": ["premium", "user"],
            "email": "alice@example.com",
        }
        request.headers = {}

        tier = get_user_tier(request)
        assert tier == "premium"

    def test_get_tier_from_request_state_enterprise_role(self):
        """Test tier extraction for enterprise role"""
        request = Mock(spec=Request)
        request.state = Mock()
        request.state.user = {
            "user_id": "user:bob",
            "username": "bob",
            "roles": ["enterprise", "admin"],
        }
        request.headers = {}

        tier = get_user_tier(request)
        assert tier == "enterprise"

    def test_get_tier_from_request_state_standard_role(self):
        """Test tier extraction for standard role"""
        request = Mock(spec=Request)
        request.state = Mock()
        request.state.user = {
            "user_id": "user:charlie",
            "username": "charlie",
            "roles": ["standard"],
        }
        request.headers = {}

        tier = get_user_tier(request)
        assert tier == "standard"

    def test_get_tier_from_request_state_free_role(self):
        """Test tier extraction for free role"""
        request = Mock(spec=Request)
        request.state = Mock()
        request.state.user = {
            "user_id": "user:dave",
            "username": "dave",
            "roles": ["free", "user"],
        }
        request.headers = {}

        tier = get_user_tier(request)
        assert tier == "free"

    def test_get_tier_fallback_to_tier_field(self):
        """Test tier extraction falls back to tier field if no matching role"""
        request = Mock(spec=Request)
        request.state = Mock()
        request.state.user = {
            "user_id": "user:eve",
            "username": "eve",
            "roles": ["user", "verified"],
            "tier": "premium",
        }
        request.headers = {}

        tier = get_user_tier(request)
        assert tier == "premium"

    def test_no_request_state_user_falls_back_to_anonymous(self):
        """Test that missing request.state.user falls back to anonymous tier"""
        request = Mock(spec=Request)
        request.state = Mock()
        # No user attribute
        request.headers = {}

        tier = get_user_tier(request)
        assert tier == "anonymous"

    def test_rate_limit_key_uses_request_state_user_id(self):
        """Test rate limit key generation uses request.state.user"""
        request = Mock(spec=Request)
        request.state = Mock()
        request.state.user = {
            "user_id": "user:alice",
            "username": "alice",
        }
        request.headers = {}
        request.client = Mock()
        request.client.host = "192.168.1.1"

        key = get_rate_limit_key(request)
        # Should use user ID from state
        assert "user:alice" in key or "alice" in key
