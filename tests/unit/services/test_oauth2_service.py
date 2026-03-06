"""
OAuth2 Service Unit Tests

TDD: Tests written FIRST for the OAuth2Service implementation.
Tests the PKCE flow, discovery, and token exchange for MCP connections.

Follows memory safety patterns for pytest-xdist.
"""

import gc
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from mcp_server_langgraph.core.dependencies import OAuth2Service

pytestmark = [
    pytest.mark.unit,
    pytest.mark.xdist_group(name="oauth2_service"),
]


class TestOAuth2Service:
    """TDD tests for OAuth2 service."""

    def teardown_method(self) -> None:
        """Force GC to prevent mock accumulation in xdist workers."""
        gc.collect()

    @pytest.fixture
    def service(self) -> OAuth2Service:
        """Create OAuth2 service instance."""
        return OAuth2Service()

    # =========================================================================
    # PKCE Code Verifier Tests
    # =========================================================================

    def test_generate_code_verifier_returns_string(self, service: OAuth2Service) -> None:
        """Test: Code verifier is a string."""
        verifier = service.generate_code_verifier()
        assert isinstance(verifier, str)

    def test_generate_code_verifier_length(self, service: OAuth2Service) -> None:
        """Test: Code verifier has sufficient length for security."""
        verifier = service.generate_code_verifier()
        # PKCE spec requires 43-128 characters
        assert len(verifier) >= 43

    def test_generate_code_verifier_is_unique(self, service: OAuth2Service) -> None:
        """Test: Each code verifier is unique."""
        verifier1 = service.generate_code_verifier()
        verifier2 = service.generate_code_verifier()
        assert verifier1 != verifier2

    def test_generate_code_verifier_url_safe(self, service: OAuth2Service) -> None:
        """Test: Code verifier contains only URL-safe characters."""
        verifier = service.generate_code_verifier()
        # URL-safe base64 uses only these characters
        allowed_chars = set("ABCDEFGHIJKLMNOPQRSTUVWXYZabcdefghijklmnopqrstuvwxyz0123456789-_")
        assert all(c in allowed_chars for c in verifier)

    # =========================================================================
    # PKCE Code Challenge Tests
    # =========================================================================

    def test_generate_code_challenge_returns_string(self, service: OAuth2Service) -> None:
        """Test: Code challenge is a string."""
        verifier = "a" * 64
        challenge = service.generate_code_challenge(verifier)
        assert isinstance(challenge, str)

    def test_generate_code_challenge_deterministic(self, service: OAuth2Service) -> None:
        """Test: Same verifier produces same challenge."""
        verifier = "test_verifier_12345"
        challenge1 = service.generate_code_challenge(verifier)
        challenge2 = service.generate_code_challenge(verifier)
        assert challenge1 == challenge2

    def test_generate_code_challenge_different_for_different_verifiers(self, service: OAuth2Service) -> None:
        """Test: Different verifiers produce different challenges."""
        challenge1 = service.generate_code_challenge("verifier1")
        challenge2 = service.generate_code_challenge("verifier2")
        assert challenge1 != challenge2

    def test_generate_code_challenge_url_safe(self, service: OAuth2Service) -> None:
        """Test: Code challenge contains only URL-safe characters."""
        verifier = "test_verifier_12345"
        challenge = service.generate_code_challenge(verifier)
        allowed_chars = set("ABCDEFGHIJKLMNOPQRSTUVWXYZabcdefghijklmnopqrstuvwxyz0123456789-_")
        assert all(c in allowed_chars for c in challenge)

    def test_generate_code_challenge_no_padding(self, service: OAuth2Service) -> None:
        """Test: Code challenge has no base64 padding."""
        verifier = "test_verifier_12345"
        challenge = service.generate_code_challenge(verifier)
        assert "=" not in challenge

    # =========================================================================
    # Authorization URL Tests
    # =========================================================================

    def test_build_authorization_url_includes_client_id(self, service: OAuth2Service) -> None:
        """Test: Authorization URL includes client_id."""
        url = service.build_authorization_url(
            authorization_endpoint="https://auth.example.com/authorize",
            client_id="test-client-id",
            redirect_uri="https://app.example.com/callback",
            scope="read write",
            state="random-state",
            code_challenge="test-challenge",
        )
        assert "client_id=test-client-id" in url

    def test_build_authorization_url_includes_redirect_uri(self, service: OAuth2Service) -> None:
        """Test: Authorization URL includes redirect_uri."""
        url = service.build_authorization_url(
            authorization_endpoint="https://auth.example.com/authorize",
            client_id="test-client-id",
            redirect_uri="https://app.example.com/callback",
            scope="read write",
            state="random-state",
            code_challenge="test-challenge",
        )
        assert "redirect_uri=https%3A%2F%2Fapp.example.com%2Fcallback" in url

    def test_build_authorization_url_includes_response_type_code(self, service: OAuth2Service) -> None:
        """Test: Authorization URL includes response_type=code."""
        url = service.build_authorization_url(
            authorization_endpoint="https://auth.example.com/authorize",
            client_id="test-client-id",
            redirect_uri="https://app.example.com/callback",
            scope="read write",
            state="random-state",
            code_challenge="test-challenge",
        )
        assert "response_type=code" in url

    def test_build_authorization_url_includes_state(self, service: OAuth2Service) -> None:
        """Test: Authorization URL includes state for CSRF protection."""
        url = service.build_authorization_url(
            authorization_endpoint="https://auth.example.com/authorize",
            client_id="test-client-id",
            redirect_uri="https://app.example.com/callback",
            scope="read write",
            state="random-state-123",
            code_challenge="test-challenge",
        )
        assert "state=random-state-123" in url

    def test_build_authorization_url_includes_code_challenge(self, service: OAuth2Service) -> None:
        """Test: Authorization URL includes PKCE code_challenge."""
        url = service.build_authorization_url(
            authorization_endpoint="https://auth.example.com/authorize",
            client_id="test-client-id",
            redirect_uri="https://app.example.com/callback",
            scope="read write",
            state="random-state",
            code_challenge="test-challenge-xyz",
        )
        assert "code_challenge=test-challenge-xyz" in url

    def test_build_authorization_url_uses_s256_method(self, service: OAuth2Service) -> None:
        """Test: Authorization URL uses S256 code challenge method."""
        url = service.build_authorization_url(
            authorization_endpoint="https://auth.example.com/authorize",
            client_id="test-client-id",
            redirect_uri="https://app.example.com/callback",
            scope="read write",
            state="random-state",
            code_challenge="test-challenge",
        )
        assert "code_challenge_method=S256" in url

    def test_build_authorization_url_includes_scope(self, service: OAuth2Service) -> None:
        """Test: Authorization URL includes scope."""
        url = service.build_authorization_url(
            authorization_endpoint="https://auth.example.com/authorize",
            client_id="test-client-id",
            redirect_uri="https://app.example.com/callback",
            scope="read write tools",
            state="random-state",
            code_challenge="test-challenge",
        )
        # Scope is URL encoded
        assert "scope=read+write+tools" in url or "scope=read%20write%20tools" in url

    def test_build_authorization_url_starts_with_endpoint(self, service: OAuth2Service) -> None:
        """Test: Authorization URL starts with the endpoint."""
        url = service.build_authorization_url(
            authorization_endpoint="https://auth.example.com/authorize",
            client_id="test-client-id",
            redirect_uri="https://app.example.com/callback",
            scope="read",
            state="random-state",
            code_challenge="test-challenge",
        )
        assert url.startswith("https://auth.example.com/authorize?")

    # =========================================================================
    # OAuth2 Discovery Tests
    # =========================================================================

    @pytest.mark.asyncio
    async def test_discover_metadata_returns_dict(self, service: OAuth2Service) -> None:
        """Test: Discovery returns a dictionary."""
        metadata = await service.discover_metadata("https://mcp.example.com")
        assert isinstance(metadata, dict)

    @pytest.mark.asyncio
    async def test_discover_metadata_includes_authorization_endpoint(self, service: OAuth2Service) -> None:
        """Test: Discovery returns authorization endpoint."""
        metadata = await service.discover_metadata("https://mcp.example.com")
        assert "authorization_endpoint" in metadata
        assert isinstance(metadata["authorization_endpoint"], str)

    @pytest.mark.asyncio
    async def test_discover_metadata_includes_token_endpoint(self, service: OAuth2Service) -> None:
        """Test: Discovery returns token endpoint."""
        metadata = await service.discover_metadata("https://mcp.example.com")
        assert "token_endpoint" in metadata
        assert isinstance(metadata["token_endpoint"], str)

    # =========================================================================
    # Token Exchange Tests
    # =========================================================================

    @pytest.mark.asyncio
    async def test_exchange_code_returns_tokens(self, service: OAuth2Service) -> None:
        """Test: Exchange returns token dictionary."""
        with patch("httpx.AsyncClient") as mock_client_class:
            mock_client = AsyncMock(return_value=None)  # async-mock-configured (return_value set below)
            mock_client_class.return_value.__aenter__.return_value = mock_client

            mock_response = MagicMock()
            mock_response.json.return_value = {
                "access_token": "test-access-token",
                "token_type": "Bearer",
                "expires_in": 3600,
            }
            mock_response.raise_for_status = MagicMock()
            mock_client.post.return_value = mock_response

            tokens = await service.exchange_code(
                token_endpoint="https://auth.example.com/token",
                client_id="test-client",
                client_secret=None,
                code="auth-code-123",
                redirect_uri="https://app.example.com/callback",
                code_verifier="verifier-abc",
            )

            assert "access_token" in tokens
            assert tokens["access_token"] == "test-access-token"

    @pytest.mark.asyncio
    async def test_exchange_code_includes_grant_type(self, service: OAuth2Service) -> None:
        """Test: Exchange request includes authorization_code grant type."""
        with patch("httpx.AsyncClient") as mock_client_class:
            mock_client = AsyncMock(return_value=None)  # async-mock-configured (return_value set below)
            mock_client_class.return_value.__aenter__.return_value = mock_client

            mock_response = MagicMock()
            mock_response.json.return_value = {"access_token": "test"}
            mock_response.raise_for_status = MagicMock()
            mock_client.post.return_value = mock_response

            await service.exchange_code(
                token_endpoint="https://auth.example.com/token",
                client_id="test-client",
                client_secret=None,
                code="auth-code",
                redirect_uri="https://app.example.com/callback",
                code_verifier="verifier",
            )

            # Check the data sent in the POST request
            call_args = mock_client.post.call_args
            assert call_args[1]["data"]["grant_type"] == "authorization_code"

    @pytest.mark.asyncio
    async def test_exchange_code_includes_code_verifier(self, service: OAuth2Service) -> None:
        """Test: Exchange request includes PKCE code verifier."""
        with patch("httpx.AsyncClient") as mock_client_class:
            mock_client = AsyncMock(return_value=None)  # async-mock-configured (return_value set below)
            mock_client_class.return_value.__aenter__.return_value = mock_client

            mock_response = MagicMock()
            mock_response.json.return_value = {"access_token": "test"}
            mock_response.raise_for_status = MagicMock()
            mock_client.post.return_value = mock_response

            await service.exchange_code(
                token_endpoint="https://auth.example.com/token",
                client_id="test-client",
                client_secret=None,
                code="auth-code",
                redirect_uri="https://app.example.com/callback",
                code_verifier="my-code-verifier-123",
            )

            call_args = mock_client.post.call_args
            assert call_args[1]["data"]["code_verifier"] == "my-code-verifier-123"

    @pytest.mark.asyncio
    async def test_exchange_code_includes_client_secret_when_provided(self, service: OAuth2Service) -> None:
        """Test: Exchange includes client_secret when provided."""
        with patch("httpx.AsyncClient") as mock_client_class:
            mock_client = AsyncMock(return_value=None)  # async-mock-configured (return_value set below)
            mock_client_class.return_value.__aenter__.return_value = mock_client

            mock_response = MagicMock()
            mock_response.json.return_value = {"access_token": "test"}
            mock_response.raise_for_status = MagicMock()
            mock_client.post.return_value = mock_response

            await service.exchange_code(
                token_endpoint="https://auth.example.com/token",
                client_id="test-client",
                client_secret="secret-value",
                code="auth-code",
                redirect_uri="https://app.example.com/callback",
                code_verifier="verifier",
            )

            call_args = mock_client.post.call_args
            assert call_args[1]["data"]["client_secret"] == "secret-value"

    @pytest.mark.asyncio
    async def test_exchange_code_omits_client_secret_when_none(self, service: OAuth2Service) -> None:
        """Test: Exchange omits client_secret when not provided."""
        with patch("httpx.AsyncClient") as mock_client_class:
            mock_client = AsyncMock(return_value=None)  # async-mock-configured (return_value set below)
            mock_client_class.return_value.__aenter__.return_value = mock_client

            mock_response = MagicMock()
            mock_response.json.return_value = {"access_token": "test"}
            mock_response.raise_for_status = MagicMock()
            mock_client.post.return_value = mock_response

            await service.exchange_code(
                token_endpoint="https://auth.example.com/token",
                client_id="test-client",
                client_secret=None,
                code="auth-code",
                redirect_uri="https://app.example.com/callback",
                code_verifier="verifier",
            )

            call_args = mock_client.post.call_args
            assert "client_secret" not in call_args[1]["data"]

    @pytest.mark.asyncio
    async def test_exchange_code_returns_refresh_token(self, service: OAuth2Service) -> None:
        """Test: Exchange returns refresh token when provided by server."""
        with patch("httpx.AsyncClient") as mock_client_class:
            mock_client = AsyncMock(return_value=None)  # async-mock-configured (return_value set below)
            mock_client_class.return_value.__aenter__.return_value = mock_client

            mock_response = MagicMock()
            mock_response.json.return_value = {
                "access_token": "test-access",
                "refresh_token": "test-refresh",
                "expires_in": 3600,
            }
            mock_response.raise_for_status = MagicMock()
            mock_client.post.return_value = mock_response

            tokens = await service.exchange_code(
                token_endpoint="https://auth.example.com/token",
                client_id="test-client",
                client_secret=None,
                code="auth-code",
                redirect_uri="https://app.example.com/callback",
                code_verifier="verifier",
            )

            assert "refresh_token" in tokens
            assert tokens["refresh_token"] == "test-refresh"
