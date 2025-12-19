"""
TokenValidator Unit Tests

Tests for the extracted TokenValidator class (Phase 2.2 SRP decomposition).
Written FIRST per TDD methodology (RED phase).
"""

import gc
from unittest.mock import AsyncMock

import pytest

from mcp_server_langgraph.auth.user_provider import TokenVerification


pytestmark = [
    pytest.mark.unit,
    pytest.mark.auth,
]


@pytest.mark.xdist_group(name="test_token_validator")
class TestTokenValidatorBasicVerification:
    """Tests for basic token verification."""

    def teardown_method(self) -> None:
        """Force GC to prevent mock accumulation in xdist workers."""
        gc.collect()

    @pytest.mark.asyncio
    async def test_verify_token_delegates_to_user_provider(self) -> None:
        """
        GIVEN: A TokenValidator with a mock user provider
        WHEN: verify_token is called
        THEN: It should delegate to user_provider.verify_token
        """
        from mcp_server_langgraph.auth.token_validator import TokenValidator

        mock_provider = AsyncMock()  # async-mock-configured (return_value set below)
        mock_provider.verify_token.return_value = TokenVerification(
            valid=True,
            payload={"sub": "user:alice", "jti": "abc123"},
        )

        validator = TokenValidator(user_provider=mock_provider)
        result = await validator.verify_token("test_token")

        assert result.valid is True
        mock_provider.verify_token.assert_called_once_with("test_token")

    @pytest.mark.asyncio
    async def test_verify_token_checks_denylist(self) -> None:
        """
        GIVEN: A TokenValidator with a token denylist
        WHEN: verify_token is called with a denied token
        THEN: It should return invalid result
        """
        from mcp_server_langgraph.auth.token_validator import TokenValidator

        mock_provider = AsyncMock()  # async-mock-configured (return_value set below)
        mock_provider.verify_token.return_value = TokenVerification(
            valid=True,
            payload={"sub": "user:alice", "jti": "denied_jti"},
        )

        mock_denylist = AsyncMock()  # async-mock-configured (return_value set below)
        mock_denylist.is_denied.return_value = True

        validator = TokenValidator(
            user_provider=mock_provider,
            token_denylist=mock_denylist,
        )
        result = await validator.verify_token("test_token")

        assert result.valid is False
        assert "revoked" in result.error.lower()
        mock_denylist.is_denied.assert_called_once_with("denied_jti")

    @pytest.mark.asyncio
    async def test_verify_token_allows_valid_token_not_in_denylist(self) -> None:
        """
        GIVEN: A TokenValidator with a token denylist
        WHEN: verify_token is called with a valid token not in denylist
        THEN: It should return valid result
        """
        from mcp_server_langgraph.auth.token_validator import TokenValidator

        mock_provider = AsyncMock()  # async-mock-configured (return_value set below)
        mock_provider.verify_token.return_value = TokenVerification(
            valid=True,
            payload={"sub": "user:alice", "jti": "valid_jti"},
        )

        mock_denylist = AsyncMock()  # async-mock-configured (return_value set below)
        mock_denylist.is_denied.return_value = False

        validator = TokenValidator(
            user_provider=mock_provider,
            token_denylist=mock_denylist,
        )
        result = await validator.verify_token("test_token")

        assert result.valid is True

    @pytest.mark.asyncio
    async def test_verify_token_returns_invalid_for_bad_token(self) -> None:
        """
        GIVEN: A TokenValidator with a mock user provider
        WHEN: verify_token is called with an invalid token
        THEN: It should return invalid result from provider
        """
        from mcp_server_langgraph.auth.token_validator import TokenValidator

        mock_provider = AsyncMock()  # async-mock-configured (return_value set below)
        mock_provider.verify_token.return_value = TokenVerification(
            valid=False,
            error="Token expired",
        )

        validator = TokenValidator(user_provider=mock_provider)
        result = await validator.verify_token("expired_token")

        assert result.valid is False
        assert result.error == "Token expired"


@pytest.mark.xdist_group(name="test_token_validator")
class TestTokenValidatorDPoPVerification:
    """Tests for DPoP-enhanced token verification."""

    def teardown_method(self) -> None:
        """Force GC to prevent mock accumulation in xdist workers."""
        gc.collect()

    @pytest.mark.asyncio
    async def test_verify_token_with_dpop_rejects_when_required_but_missing(self) -> None:
        """
        GIVEN: A TokenValidator with dpop_required=True
        WHEN: verify_token_with_dpop is called without DPoP proof
        THEN: It should reject the request
        """
        from mcp_server_langgraph.auth.token_validator import TokenValidator

        mock_provider = AsyncMock()  # async-mock-configured (return_value set below)
        mock_provider.verify_token.return_value = TokenVerification(
            valid=True,
            payload={"sub": "user:alice"},
        )

        validator = TokenValidator(
            user_provider=mock_provider,
            dpop_required=True,
        )
        result = await validator.verify_token_with_dpop(
            token="test_token",
            dpop_proof=None,
            http_method="GET",
            http_uri="https://example.com/api",
        )

        assert result.valid is False
        assert "DPoP" in result.error

    @pytest.mark.asyncio
    async def test_verify_token_with_dpop_allows_without_proof_when_not_required(self) -> None:
        """
        GIVEN: A TokenValidator with dpop_required=False and token without cnf claim
        WHEN: verify_token_with_dpop is called without DPoP proof
        THEN: It should allow the request (optional DPoP mode)
        """
        from mcp_server_langgraph.auth.token_validator import TokenValidator

        mock_provider = AsyncMock()  # async-mock-configured (return_value set below)
        mock_provider.verify_token.return_value = TokenVerification(
            valid=True,
            payload={"sub": "user:alice"},  # No cnf claim
        )

        validator = TokenValidator(
            user_provider=mock_provider,
            dpop_required=False,
        )
        result = await validator.verify_token_with_dpop(
            token="test_token",
            dpop_proof=None,
            http_method="GET",
            http_uri="https://example.com/api",
        )

        assert result.valid is True

    @pytest.mark.asyncio
    async def test_verify_token_with_dpop_rejects_bound_token_without_proof(self) -> None:
        """
        GIVEN: A TokenValidator with a DPoP-bound token (has cnf.jkt claim)
        WHEN: verify_token_with_dpop is called without DPoP proof
        THEN: It should reject the request
        """
        from mcp_server_langgraph.auth.token_validator import TokenValidator

        mock_provider = AsyncMock()  # async-mock-configured (return_value set below)
        mock_provider.verify_token.return_value = TokenVerification(
            valid=True,
            payload={
                "sub": "user:alice",
                "cnf": {"jkt": "thumbprint123"},  # DPoP-bound token
            },
        )

        validator = TokenValidator(
            user_provider=mock_provider,
            dpop_required=False,  # Not enforced globally
        )
        result = await validator.verify_token_with_dpop(
            token="test_token",
            dpop_proof=None,  # But this token is bound
            http_method="GET",
            http_uri="https://example.com/api",
        )

        assert result.valid is False
        assert "sender-constrained" in result.error.lower()


@pytest.mark.xdist_group(name="test_token_validator")
class TestTokenValidatorIntegration:
    """Integration tests for TokenValidator."""

    def teardown_method(self) -> None:
        """Force GC to prevent mock accumulation in xdist workers."""
        gc.collect()

    @pytest.mark.asyncio
    async def test_token_validator_can_be_used_by_auth_middleware(self) -> None:
        """
        GIVEN: An AuthMiddleware using TokenValidator
        WHEN: verify_token is called on AuthMiddleware
        THEN: It should delegate to TokenValidator
        """
        from mcp_server_langgraph.auth.middleware import AuthMiddleware
        from mcp_server_langgraph.auth.user_provider import InMemoryUserProvider

        # Create middleware with in-memory provider
        provider = InMemoryUserProvider(secret_key="test_secret_key_for_testing")
        middleware = AuthMiddleware(user_provider=provider)

        # Register a test user and create a token (via the provider)
        await provider.create_user(
            username="testuser",
            password="testpass",
            email="testuser@example.com",
            roles=["user"],
        )

        # Authenticate to verify user exists, then create token
        auth_response = await provider.authenticate("testuser", "testpass")
        assert auth_response.authorized

        # Create token using provider's create_token method
        token = provider.create_token("testuser")

        # Verify the token works
        result = await middleware.verify_token(token)
        assert result.valid is True
        assert result.payload is not None
        assert result.payload.get("sub") == "user:testuser"
