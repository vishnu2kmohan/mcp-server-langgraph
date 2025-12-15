"""
Tests for DPoP middleware integration (RFC 9449).

DPoP provides sender-constrained access tokens by requiring clients to prove
possession of a private key. This prevents token theft and replay attacks.

TDD Tests - Written FIRST before implementation.
"""

import gc
from datetime import datetime, UTC
from unittest.mock import AsyncMock, MagicMock

import pytest

# Markers
pytestmark = [
    pytest.mark.unit,
    pytest.mark.auth,
]


@pytest.fixture
def dpop_key_pair():
    """Generate ES256 key pair for DPoP proofs."""
    from cryptography.hazmat.primitives.asymmetric import ec

    private_key = ec.generate_private_key(ec.SECP256R1())
    public_key = private_key.public_key()

    return {
        "private_key": private_key,
        "public_key": public_key,
    }


@pytest.fixture
def mock_user_provider():
    """Create a mock user provider for testing."""
    from mcp_server_langgraph.auth.user_provider import TokenVerification

    provider = MagicMock()
    provider.verify_token = AsyncMock(
        return_value=TokenVerification(
            valid=True,
            payload={
                "sub": "test-user-id",
                "preferred_username": "testuser",
                "jti": "test-jti-12345",
                "exp": int(datetime.now(UTC).timestamp()) + 3600,
            },
        )
    )
    return provider


@pytest.fixture
def mock_dpop_bound_token_provider(dpop_key_pair):
    """Create a mock user provider that returns a DPoP-bound token."""
    from mcp_server_langgraph.auth.user_provider import TokenVerification
    from mcp_server_langgraph.auth.dpop import DPoPClient

    # Create DPoP client to get JWK thumbprint
    client = DPoPClient(private_key=dpop_key_pair["private_key"])
    jkt = client.get_jwk_thumbprint()

    provider = MagicMock()
    provider.verify_token = AsyncMock(
        return_value=TokenVerification(
            valid=True,
            payload={
                "sub": "test-user-id",
                "preferred_username": "testuser",
                "jti": "test-jti-12345",
                "exp": int(datetime.now(UTC).timestamp()) + 3600,
                "cnf": {"jkt": jkt},  # DPoP-bound token
            },
        )
    )
    return provider, client


@pytest.mark.xdist_group(name="dpop_middleware")
class TestDPoPMiddlewareVerification:
    """Test DPoP verification in auth middleware."""

    def teardown_method(self):
        """Force GC to prevent mock accumulation in xdist workers."""
        gc.collect()

    @pytest.mark.asyncio
    async def test_verify_token_without_dpop_succeeds_for_non_bound_token(self, mock_user_provider):
        """
        GIVEN: A regular access token (not DPoP-bound)
        WHEN: verify_token_with_dpop() is called without DPoP proof
        THEN: Should succeed (DPoP is optional for non-bound tokens)
        """
        from mcp_server_langgraph.auth.middleware import AuthMiddleware

        middleware = AuthMiddleware(user_provider=mock_user_provider)

        result = await middleware.verify_token_with_dpop(
            token="test-access-token",
            dpop_proof=None,
            http_method="GET",
            http_uri="https://api.example.com/resource",
        )

        assert result.valid is True
        assert result.payload is not None

    @pytest.mark.asyncio
    async def test_verify_token_with_dpop_bound_token_requires_proof(self, mock_dpop_bound_token_provider):
        """
        GIVEN: A DPoP-bound access token (has cnf.jkt claim)
        WHEN: verify_token_with_dpop() is called WITHOUT DPoP proof
        THEN: Should fail with "DPoP proof required" error
        """
        from mcp_server_langgraph.auth.middleware import AuthMiddleware

        provider, _ = mock_dpop_bound_token_provider
        middleware = AuthMiddleware(user_provider=provider)

        result = await middleware.verify_token_with_dpop(
            token="dpop-bound-access-token",
            dpop_proof=None,  # No proof provided!
            http_method="GET",
            http_uri="https://api.example.com/resource",
        )

        assert result.valid is False
        assert "dpop" in result.error.lower()
        assert "required" in result.error.lower()

    @pytest.mark.asyncio
    async def test_verify_token_with_valid_dpop_proof_succeeds(self, mock_dpop_bound_token_provider):
        """
        GIVEN: A DPoP-bound access token and valid DPoP proof
        WHEN: verify_token_with_dpop() is called with matching proof
        THEN: Should succeed
        """
        from mcp_server_langgraph.auth.middleware import AuthMiddleware

        provider, dpop_client = mock_dpop_bound_token_provider
        middleware = AuthMiddleware(user_provider=provider)

        # Generate valid DPoP proof
        proof = dpop_client.generate_proof(
            http_method="GET",
            http_uri="https://api.example.com/resource",
            access_token="dpop-bound-access-token",
        )

        result = await middleware.verify_token_with_dpop(
            token="dpop-bound-access-token",
            dpop_proof=proof,
            http_method="GET",
            http_uri="https://api.example.com/resource",
        )

        assert result.valid is True
        assert result.payload is not None

    @pytest.mark.asyncio
    async def test_verify_token_with_wrong_dpop_key_fails(self, mock_dpop_bound_token_provider, dpop_key_pair):
        """
        GIVEN: A DPoP-bound access token
        WHEN: DPoP proof is signed with DIFFERENT key than token binding
        THEN: Should fail with key mismatch error
        """
        from cryptography.hazmat.primitives.asymmetric import ec

        from mcp_server_langgraph.auth.dpop import DPoPClient
        from mcp_server_langgraph.auth.middleware import AuthMiddleware

        provider, _ = mock_dpop_bound_token_provider
        middleware = AuthMiddleware(user_provider=provider)

        # Generate proof with DIFFERENT key (attacker's key)
        attacker_key = ec.generate_private_key(ec.SECP256R1())
        attacker_client = DPoPClient(private_key=attacker_key)

        proof = attacker_client.generate_proof(
            http_method="GET",
            http_uri="https://api.example.com/resource",
            access_token="dpop-bound-access-token",
        )

        result = await middleware.verify_token_with_dpop(
            token="dpop-bound-access-token",
            dpop_proof=proof,
            http_method="GET",
            http_uri="https://api.example.com/resource",
        )

        assert result.valid is False
        assert "key" in result.error.lower() or "thumbprint" in result.error.lower()

    @pytest.mark.asyncio
    async def test_verify_token_with_dpop_wrong_method_fails(self, mock_dpop_bound_token_provider):
        """
        GIVEN: DPoP proof generated for POST method
        WHEN: Request is actually GET
        THEN: Should fail with method mismatch error
        """
        from mcp_server_langgraph.auth.middleware import AuthMiddleware

        provider, dpop_client = mock_dpop_bound_token_provider
        middleware = AuthMiddleware(user_provider=provider)

        # Generate proof for POST
        proof = dpop_client.generate_proof(
            http_method="POST",  # Wrong method!
            http_uri="https://api.example.com/resource",
            access_token="dpop-bound-access-token",
        )

        result = await middleware.verify_token_with_dpop(
            token="dpop-bound-access-token",
            dpop_proof=proof,
            http_method="GET",  # Actual request is GET
            http_uri="https://api.example.com/resource",
        )

        assert result.valid is False
        assert "method" in result.error.lower()

    @pytest.mark.asyncio
    async def test_verify_token_with_dpop_wrong_uri_fails(self, mock_dpop_bound_token_provider):
        """
        GIVEN: DPoP proof generated for /other endpoint
        WHEN: Request is actually for /resource endpoint
        THEN: Should fail with URI mismatch error
        """
        from mcp_server_langgraph.auth.middleware import AuthMiddleware

        provider, dpop_client = mock_dpop_bound_token_provider
        middleware = AuthMiddleware(user_provider=provider)

        # Generate proof for different URI
        proof = dpop_client.generate_proof(
            http_method="GET",
            http_uri="https://api.example.com/other",  # Wrong URI!
            access_token="dpop-bound-access-token",
        )

        result = await middleware.verify_token_with_dpop(
            token="dpop-bound-access-token",
            dpop_proof=proof,
            http_method="GET",
            http_uri="https://api.example.com/resource",  # Actual request URI
        )

        assert result.valid is False
        assert "uri" in result.error.lower()


@pytest.mark.xdist_group(name="dpop_middleware")
class TestDPoPReplayProtection:
    """Test DPoP jti replay protection in middleware."""

    def teardown_method(self):
        """Force GC to prevent mock accumulation in xdist workers."""
        gc.collect()

    @pytest.mark.asyncio
    async def test_dpop_replay_attack_is_blocked(self, mock_dpop_bound_token_provider):
        """
        GIVEN: Valid DPoP proof that was already used
        WHEN: Same proof is submitted again
        THEN: Should fail with replay attack error
        """
        from mcp_server_langgraph.auth.dpop import DPoPReplayCache
        from mcp_server_langgraph.auth.middleware import AuthMiddleware

        provider, dpop_client = mock_dpop_bound_token_provider
        replay_cache = DPoPReplayCache()
        middleware = AuthMiddleware(
            user_provider=provider,
            dpop_replay_cache=replay_cache,
        )

        # Generate valid DPoP proof
        proof = dpop_client.generate_proof(
            http_method="GET",
            http_uri="https://api.example.com/resource",
            access_token="dpop-bound-access-token",
        )

        # First use should succeed
        result1 = await middleware.verify_token_with_dpop(
            token="dpop-bound-access-token",
            dpop_proof=proof,
            http_method="GET",
            http_uri="https://api.example.com/resource",
        )
        assert result1.valid is True

        # Second use (replay) should fail
        result2 = await middleware.verify_token_with_dpop(
            token="dpop-bound-access-token",
            dpop_proof=proof,
            http_method="GET",
            http_uri="https://api.example.com/resource",
        )
        assert result2.valid is False
        assert "replay" in result2.error.lower()


@pytest.mark.xdist_group(name="dpop_middleware")
class TestDPoPOptionalForNonBoundTokens:
    """Test that DPoP is optional when token is not bound."""

    def teardown_method(self):
        """Force GC to prevent mock accumulation in xdist workers."""
        gc.collect()

    @pytest.mark.asyncio
    async def test_non_bound_token_with_dpop_proof_still_works(self, mock_user_provider, dpop_key_pair):
        """
        GIVEN: Regular access token (not DPoP-bound) with DPoP proof provided
        WHEN: verify_token_with_dpop() is called
        THEN: Should succeed (DPoP proof is optional but valid)
        """
        from mcp_server_langgraph.auth.dpop import DPoPClient
        from mcp_server_langgraph.auth.middleware import AuthMiddleware

        middleware = AuthMiddleware(user_provider=mock_user_provider)

        # Generate DPoP proof even though token is not bound
        client = DPoPClient(private_key=dpop_key_pair["private_key"])
        proof = client.generate_proof(
            http_method="GET",
            http_uri="https://api.example.com/resource",
        )

        result = await middleware.verify_token_with_dpop(
            token="regular-access-token",
            dpop_proof=proof,
            http_method="GET",
            http_uri="https://api.example.com/resource",
        )

        # Should succeed - DPoP adds security but doesn't break non-bound tokens
        assert result.valid is True


@pytest.mark.xdist_group(name="dpop_middleware")
class TestDPoPEnforcementMode:
    """Test DPoP enforcement configuration option (RFC 9449 Section 10)."""

    def teardown_method(self):
        """Force GC to prevent mock accumulation in xdist workers."""
        gc.collect()

    @pytest.mark.asyncio
    async def test_dpop_enforcement_disabled_allows_non_bound_tokens(self, mock_user_provider):
        """
        GIVEN: DPoP enforcement is disabled (default)
        WHEN: Non-DPoP-bound token is used without proof
        THEN: Should succeed
        """
        from mcp_server_langgraph.auth.middleware import AuthMiddleware

        middleware = AuthMiddleware(
            user_provider=mock_user_provider,
            dpop_required=False,  # Default
        )

        result = await middleware.verify_token_with_dpop(
            token="regular-access-token",
            dpop_proof=None,
            http_method="GET",
            http_uri="https://api.example.com/resource",
        )

        assert result.valid is True

    @pytest.mark.asyncio
    async def test_dpop_enforcement_enabled_requires_proof_for_all_tokens(self, mock_user_provider, dpop_key_pair):
        """
        GIVEN: DPoP enforcement is enabled (strict mode)
        WHEN: Any token is used WITHOUT DPoP proof
        THEN: Should fail with "DPoP required" error
        """
        from mcp_server_langgraph.auth.middleware import AuthMiddleware

        middleware = AuthMiddleware(
            user_provider=mock_user_provider,
            dpop_required=True,  # Strict mode enabled
        )

        result = await middleware.verify_token_with_dpop(
            token="regular-access-token",
            dpop_proof=None,  # No proof!
            http_method="GET",
            http_uri="https://api.example.com/resource",
        )

        assert result.valid is False
        assert "dpop" in result.error.lower()
        assert "required" in result.error.lower()

    @pytest.mark.asyncio
    async def test_dpop_enforcement_enabled_with_valid_proof_succeeds(self, mock_user_provider, dpop_key_pair):
        """
        GIVEN: DPoP enforcement is enabled
        WHEN: Token is used WITH valid DPoP proof
        THEN: Should succeed
        """
        from mcp_server_langgraph.auth.dpop import DPoPClient
        from mcp_server_langgraph.auth.middleware import AuthMiddleware

        middleware = AuthMiddleware(
            user_provider=mock_user_provider,
            dpop_required=True,
        )

        # Generate valid DPoP proof
        client = DPoPClient(private_key=dpop_key_pair["private_key"])
        proof = client.generate_proof(
            http_method="GET",
            http_uri="https://api.example.com/resource",
        )

        result = await middleware.verify_token_with_dpop(
            token="regular-access-token",
            dpop_proof=proof,
            http_method="GET",
            http_uri="https://api.example.com/resource",
        )

        assert result.valid is True

    @pytest.mark.asyncio
    async def test_dpop_enforcement_config_from_settings(self):
        """
        GIVEN: dpop_required is set in application settings
        WHEN: AuthMiddleware is created
        THEN: Should respect the configuration setting
        """
        from mcp_server_langgraph.core.config import Settings

        # Test that the setting exists and has correct default
        settings = Settings()
        assert hasattr(settings, "dpop_required")
        assert settings.dpop_required is False  # Secure default: optional

    @pytest.mark.asyncio
    async def test_dpop_enforcement_bound_token_always_requires_proof(self, mock_dpop_bound_token_provider):
        """
        GIVEN: DPoP enforcement is DISABLED
        WHEN: DPoP-bound token (has cnf.jkt) is used WITHOUT proof
        THEN: Should still fail (bound tokens ALWAYS require proof)
        """
        from mcp_server_langgraph.auth.middleware import AuthMiddleware

        provider, _ = mock_dpop_bound_token_provider
        middleware = AuthMiddleware(
            user_provider=provider,
            dpop_required=False,  # Enforcement disabled
        )

        result = await middleware.verify_token_with_dpop(
            token="dpop-bound-access-token",
            dpop_proof=None,  # No proof for bound token
            http_method="GET",
            http_uri="https://api.example.com/resource",
        )

        # Should fail even with enforcement disabled - token IS bound
        assert result.valid is False
        assert "required" in result.error.lower()
