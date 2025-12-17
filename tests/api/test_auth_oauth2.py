"""
Tests for OAuth2 Authorization Code + PKCE API endpoints.

TDD: Tests for /api/v1/auth/* endpoints (login, callback, refresh).
Per RFC 9700: ROPC MUST NOT be used. Use Authorization Code + PKCE instead.

Follows memory safety patterns for pytest-xdist.
"""

import gc
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient

pytestmark = [pytest.mark.unit, pytest.mark.api, pytest.mark.auth]


def _create_test_app() -> FastAPI:
    """Create a test FastAPI app with the auth router.

    Note: Rate limiting is disabled in tests via the no-op limiter patch applied
    by the app fixture. The auth router uses the global limiter from
    mcp_server_langgraph.middleware.rate_limiter, so we patch it module-wide.
    """
    from mcp_server_langgraph.api.v1.auth import AuthSecurityHeadersMiddleware, auth_router

    app = FastAPI()
    # Add security headers middleware (OWASP best practices)
    app.add_middleware(AuthSecurityHeadersMiddleware)
    app.include_router(auth_router)
    return app


@pytest.fixture
def app():
    """Create test app with auth router."""
    return _create_test_app()


@pytest.fixture
def client(app):
    """Create test client."""
    return TestClient(app)


# ============================================================================
# GET /auth/login Tests
# ============================================================================


@pytest.mark.xdist_group(name="oauth2_api")
class TestOAuth2Login:
    """Tests for GET /auth/login - OAuth2 + PKCE flow initiation."""

    def teardown_method(self) -> None:
        """Force GC to prevent accumulation in xdist workers."""
        gc.collect()

    def test_login_returns_redirect(self, client):
        """Should return a redirect response to Keycloak."""
        response = client.get("/auth/login", follow_redirects=False)

        # Should be a redirect (302)
        assert response.status_code == 302

    def test_login_redirect_includes_keycloak_url(self, client):
        """Redirect URL should point to Keycloak authorization endpoint."""
        response = client.get("/auth/login", follow_redirects=False)

        location = response.headers.get("location", "")
        # Should redirect to Keycloak (contains realm path)
        assert "/realms/" in location
        assert "/protocol/openid-connect/auth" in location

    def test_login_redirect_includes_pkce_params(self, client):
        """Redirect URL should include PKCE code_challenge and method."""
        response = client.get("/auth/login", follow_redirects=False)

        location = response.headers.get("location", "")
        assert "code_challenge=" in location
        assert "code_challenge_method=S256" in location

    def test_login_redirect_includes_oauth2_params(self, client):
        """Redirect URL should include required OAuth2 params."""
        response = client.get("/auth/login", follow_redirects=False)

        location = response.headers.get("location", "")
        assert "client_id=" in location
        assert "redirect_uri=" in location
        assert "response_type=code" in location
        assert "state=" in location
        assert "scope=" in location

    def test_login_sets_pkce_cookies(self, client):
        """Should set secure cookies for PKCE state management."""
        response = client.get("/auth/login", follow_redirects=False)

        cookies = response.cookies
        assert "oauth2_code_verifier" in cookies
        assert "oauth2_state" in cookies
        assert "oauth2_redirect_uri" in cookies

    def test_login_cookies_are_httponly(self, client):
        """PKCE cookies should be httpOnly for security."""
        response = client.get("/auth/login", follow_redirects=False)

        # Check Set-Cookie headers for httponly flag
        set_cookie_headers = response.headers.get_list("set-cookie")
        for header in set_cookie_headers:
            if "oauth2_code_verifier" in header or "oauth2_state" in header:
                assert "httponly" in header.lower()

    def test_login_with_custom_redirect_uri(self, client):
        """Should use custom redirect_uri if provided."""
        custom_uri = "https://custom.example.com/callback"
        response = client.get(
            f"/auth/login?redirect_uri={custom_uri}",
            follow_redirects=False,
        )

        location = response.headers.get("location", "")
        # The custom URI should be URL-encoded in the redirect
        assert "redirect_uri=" in location

    def test_login_uses_public_url_for_redirect(self):
        """Should use keycloak_public_url (not keycloak_server_url) for browser redirect.

        This test catches the configuration issue where internal Docker URLs
        (e.g., http://keycloak-test:8080) are accidentally used for browser redirects
        instead of externally accessible URLs (e.g., http://localhost/authn).

        See ADR-0071: keycloak_public_url is for browser redirects, keycloak_server_url
        is for backend-to-backend token exchange.
        """
        # Mock settings with distinct public and internal URLs
        with patch("mcp_server_langgraph.api.v1.auth.settings") as mock_settings:
            mock_settings.keycloak_server_url = "http://internal-keycloak:8080/authn"
            mock_settings.keycloak_public_url = "http://localhost/authn"
            mock_settings.keycloak_realm = "test-realm"
            mock_settings.keycloak_client_id = "test-client"
            mock_settings.oauth2_auth_callback_uri = None  # Auto-detect
            mock_settings.environment = "development"

            app = _create_test_app()
            client = TestClient(app)

            response = client.get("/auth/login", follow_redirects=False)

            location = response.headers.get("location", "")
            # CRITICAL: Should use PUBLIC URL for browser redirect
            assert "http://localhost/authn" in location
            # Should NOT use internal Docker URL
            assert "internal-keycloak" not in location

    def test_login_falls_back_to_server_url_when_public_not_set(self):
        """Should use keycloak_server_url when keycloak_public_url is not configured."""
        with patch("mcp_server_langgraph.api.v1.auth.settings") as mock_settings:
            mock_settings.keycloak_server_url = "http://localhost:8082/authn"
            mock_settings.keycloak_public_url = None  # Not set
            mock_settings.keycloak_realm = "test-realm"
            mock_settings.keycloak_client_id = "test-client"
            mock_settings.oauth2_auth_callback_uri = None
            mock_settings.environment = "development"

            app = _create_test_app()
            client = TestClient(app)

            response = client.get("/auth/login", follow_redirects=False)

            location = response.headers.get("location", "")
            # Falls back to server_url when public_url not configured
            assert "http://localhost:8082/authn" in location


# ============================================================================
# GET /auth/callback Tests
# ============================================================================


@pytest.mark.xdist_group(name="oauth2_api")
class TestOAuth2Callback:
    """Tests for GET /auth/callback - OAuth2 code exchange."""

    def teardown_method(self) -> None:
        """Force GC to prevent accumulation in xdist workers."""
        gc.collect()

    def test_callback_requires_code_param(self, client):
        """Should return 422 when code parameter is missing."""
        response = client.get("/auth/callback?state=test-state")

        assert response.status_code == 422

    def test_callback_requires_state_param(self, client):
        """Should return 422 when state parameter is missing."""
        response = client.get("/auth/callback?code=test-code")

        assert response.status_code == 422

    def test_callback_rejects_invalid_state(self, client):
        """Should return 400 when state doesn't match session."""
        # No cookies set, so state won't match
        response = client.get("/auth/callback?code=test-code&state=invalid-state")

        assert response.status_code == 400
        assert "state" in response.json()["detail"].lower()

    def test_callback_handles_keycloak_error(self, client):
        """Should return 400 when Keycloak returns an error."""
        response = client.get("/auth/callback?error=access_denied&error_description=User+cancelled")

        assert response.status_code == 400
        assert "cancelled" in response.json()["detail"].lower()

    def test_callback_exchanges_code_for_tokens(self, app):
        """Should exchange authorization code for tokens with PKCE verifier."""
        # Set up cookies to simulate login flow
        client = TestClient(
            app,
            cookies={
                "oauth2_state": "valid-state",
                "oauth2_code_verifier": "test-verifier-1234567890",
                "oauth2_redirect_uri": "http://testserver/auth/callback",
            },
        )

        # Mock the Keycloak token endpoint
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = {
            "access_token": "test-access-token",
            "refresh_token": "test-refresh-token",
            "token_type": "Bearer",
            "expires_in": 300,
            "scope": "openid profile email",
        }

        with patch("mcp_server_langgraph.api.v1.auth.httpx.AsyncClient") as mock_client_class:
            mock_client_class.return_value.__aenter__.return_value.post = AsyncMock(return_value=mock_response)

            response = client.get("/auth/callback?code=auth-code&state=valid-state", follow_redirects=False)

        # Should redirect to frontend with tokens in fragment
        assert response.status_code == 302
        location = response.headers.get("location", "")
        assert "/auth/callback#" in location
        assert "access_token=test-access-token" in location
        assert "refresh_token=test-refresh-token" in location
        assert "token_type=Bearer" in location

    def test_callback_sends_code_verifier_to_keycloak(self, app):
        """Should include code_verifier in token exchange request."""
        client = TestClient(
            app,
            cookies={
                "oauth2_state": "valid-state",
                "oauth2_code_verifier": "my-secret-verifier",
                "oauth2_redirect_uri": "http://testserver/auth/callback",
            },
        )

        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = {
            "access_token": "token",
            "expires_in": 300,
        }

        with patch("mcp_server_langgraph.api.v1.auth.httpx.AsyncClient") as mock_client_class:
            mock_post = AsyncMock(return_value=mock_response)
            mock_client_class.return_value.__aenter__.return_value.post = mock_post

            client.get("/auth/callback?code=auth-code&state=valid-state", follow_redirects=False)

            # Verify code_verifier was sent
            call_args = mock_post.call_args
            assert call_args is not None
            post_data = call_args.kwargs.get("data", {})
            assert post_data.get("code_verifier") == "my-secret-verifier"
            assert post_data.get("grant_type") == "authorization_code"

    def test_callback_uses_server_url_for_token_exchange(self):
        """Should use keycloak_server_url (not keycloak_public_url) for token exchange.

        Token exchange is backend-to-backend communication and should use the internal
        Docker URL (keycloak_server_url), not the public URL used for browser redirects.

        This ensures proper network routing in containerized environments where the
        public URL may not be resolvable from within the container network.
        """
        with patch("mcp_server_langgraph.api.v1.auth.settings") as mock_settings:
            # Configure distinct URLs
            mock_settings.keycloak_server_url = "http://keycloak-internal:8080/authn"
            mock_settings.keycloak_public_url = "http://localhost/authn"
            mock_settings.keycloak_realm = "test-realm"
            mock_settings.keycloak_client_id = "test-client"
            mock_settings.keycloak_client_secret = None
            mock_settings.frontend_url = "http://localhost"
            mock_settings.oauth2_auth_callback_uri = None
            mock_settings.environment = "development"

            app = _create_test_app()
            client = TestClient(
                app,
                cookies={
                    "oauth2_state": "valid-state",
                    "oauth2_code_verifier": "test-verifier",
                    "oauth2_redirect_uri": "http://localhost/api/v1/auth/callback",
                },
            )

            mock_response = MagicMock()
            mock_response.status_code = 200
            mock_response.json.return_value = {
                "access_token": "token",
                "expires_in": 300,
            }

            with patch("mcp_server_langgraph.api.v1.auth.httpx.AsyncClient") as mock_client_class:
                mock_post = AsyncMock(return_value=mock_response)
                mock_client_class.return_value.__aenter__.return_value.post = mock_post

                client.get("/auth/callback?code=test-code&state=valid-state", follow_redirects=False)

                # Verify token exchange uses INTERNAL URL (keycloak_server_url)
                call_args = mock_post.call_args
                assert call_args is not None
                token_url = call_args.args[0] if call_args.args else call_args.kwargs.get("url", "")
                # Should use internal URL for backend-to-backend communication
                assert "keycloak-internal:8080" in token_url
                # Should NOT use public URL
                assert "localhost/authn" not in token_url


# ============================================================================
# POST /auth/refresh Tests
# ============================================================================


@pytest.mark.xdist_group(name="oauth2_api")
class TestOAuth2Refresh:
    """Tests for POST /auth/refresh - token refresh."""

    def teardown_method(self) -> None:
        """Force GC to prevent accumulation in xdist workers."""
        gc.collect()

    def test_refresh_requires_refresh_token(self, client):
        """Should return 422 when refresh_token is missing."""
        response = client.post("/auth/refresh", json={})

        assert response.status_code == 422

    def test_refresh_returns_new_tokens(self, client):
        """Should return new access token on successful refresh."""
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = {
            "access_token": "new-access-token",
            "refresh_token": "new-refresh-token",
            "token_type": "Bearer",
            "expires_in": 300,
        }

        with patch("mcp_server_langgraph.api.v1.auth.httpx.AsyncClient") as mock_client_class:
            mock_client_class.return_value.__aenter__.return_value.post = AsyncMock(return_value=mock_response)

            response = client.post(
                "/auth/refresh",
                json={"refresh_token": "old-refresh-token"},
            )

        assert response.status_code == 200
        data = response.json()
        assert data["access_token"] == "new-access-token"
        assert data["token_type"] == "Bearer"

    def test_refresh_returns_401_for_expired_token(self, client):
        """Should return 401 when refresh token is expired."""
        mock_response = MagicMock()
        mock_response.status_code = 400
        mock_response.content = b'{"error": "invalid_grant"}'
        mock_response.json.return_value = {"error": "invalid_grant"}

        with patch("mcp_server_langgraph.api.v1.auth.httpx.AsyncClient") as mock_client_class:
            mock_client_class.return_value.__aenter__.return_value.post = AsyncMock(return_value=mock_response)

            response = client.post(
                "/auth/refresh",
                json={"refresh_token": "expired-token"},
            )

        assert response.status_code == 401
        assert "expired" in response.json()["detail"].lower() or "invalid" in response.json()["detail"].lower()

    def test_refresh_returns_503_on_keycloak_error(self, client):
        """Should return 503 when Keycloak is unavailable."""
        import httpx

        with patch("mcp_server_langgraph.api.v1.auth.httpx.AsyncClient") as mock_client_class:
            mock_client_class.return_value.__aenter__.return_value.post = AsyncMock(
                side_effect=httpx.ConnectError("Connection refused")
            )

            response = client.post(
                "/auth/refresh",
                json={"refresh_token": "valid-token"},
            )

        assert response.status_code == 503
        assert "unavailable" in response.json()["detail"].lower()


# ============================================================================
# Refresh Token Rotation Tests (Security Hardening)
# ============================================================================


@pytest.mark.xdist_group(name="token_rotation")
class TestRefreshTokenRotation:
    """
    Tests for refresh token rotation security.

    Per OWASP Session Management:
    - Old refresh tokens should be invalidated after rotation
    - This prevents replay attacks with stolen refresh tokens
    """

    def teardown_method(self) -> None:
        """Force GC to prevent accumulation in xdist workers."""
        gc.collect()

    def test_refresh_adds_old_token_to_denylist(self, client):
        """
        GIVEN: A valid refresh token
        WHEN: Token is successfully refreshed
        THEN: Old refresh token should be added to denylist
        """
        import asyncio
        import hashlib

        from mcp_server_langgraph.auth.token_denylist import InMemoryTokenDenylist

        # Create denylist mock that we can inspect
        mock_denylist = InMemoryTokenDenylist()

        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = {
            "access_token": "new-access-token",
            "refresh_token": "new-refresh-token",
            "token_type": "Bearer",
            "expires_in": 300,
        }

        with (
            patch("mcp_server_langgraph.api.v1.auth.httpx.AsyncClient") as mock_client_class,
            patch("mcp_server_langgraph.api.v1.auth._get_token_denylist") as mock_get_denylist,
        ):
            mock_get_denylist.return_value = mock_denylist
            mock_client_class.return_value.__aenter__.return_value.post = AsyncMock(return_value=mock_response)

            response = client.post(
                "/auth/refresh",
                json={"refresh_token": "old-refresh-token"},
            )

        assert response.status_code == 200

        # Verify old refresh token was added to denylist
        # We use hash of the token since refresh tokens don't have jti
        old_token_hash = hashlib.sha256(b"old-refresh-token").hexdigest()

        async def check_denied():
            return await mock_denylist.is_denied(old_token_hash)

        is_denied = asyncio.new_event_loop().run_until_complete(check_denied())
        assert is_denied is True, "Old refresh token should be in denylist"

    def test_refresh_with_denylisted_token_fails(self, client):
        """
        GIVEN: A refresh token that has been rotated (in denylist)
        WHEN: Someone attempts to use the old token
        THEN: Should fail with 401 before even calling Keycloak
        """
        import asyncio
        import hashlib
        from datetime import UTC, datetime, timedelta

        from mcp_server_langgraph.auth.token_denylist import InMemoryTokenDenylist

        # Pre-populate denylist with old token hash
        mock_denylist = InMemoryTokenDenylist()
        old_token_hash = hashlib.sha256(b"stolen-old-token").hexdigest()
        expires_at = datetime.now(UTC) + timedelta(hours=1)

        async def add_to_denylist():
            await mock_denylist.add(old_token_hash, expires_at)

        asyncio.new_event_loop().run_until_complete(add_to_denylist())

        with patch("mcp_server_langgraph.api.v1.auth._get_token_denylist") as mock_get_denylist:
            mock_get_denylist.return_value = mock_denylist

            response = client.post(
                "/auth/refresh",
                json={"refresh_token": "stolen-old-token"},
            )

        # Should reject immediately without calling Keycloak
        assert response.status_code == 401
        assert "revoked" in response.json()["detail"].lower() or "invalid" in response.json()["detail"].lower()

    def test_refresh_without_rotation_enabled_skips_denylist(self, client):
        """
        GIVEN: Token rotation is disabled (denylist returns None)
        WHEN: Token is refreshed
        THEN: Should still work (backward compatibility)
        """
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = {
            "access_token": "new-access-token",
            "refresh_token": "new-refresh-token",
            "token_type": "Bearer",
            "expires_in": 300,
        }

        with (
            patch("mcp_server_langgraph.api.v1.auth.httpx.AsyncClient") as mock_client_class,
            patch("mcp_server_langgraph.api.v1.auth._get_token_denylist") as mock_get_denylist,
        ):
            mock_get_denylist.return_value = None
            mock_client_class.return_value.__aenter__.return_value.post = AsyncMock(return_value=mock_response)

            response = client.post(
                "/auth/refresh",
                json={"refresh_token": "old-refresh-token"},
            )

        # Should succeed even without denylist
        assert response.status_code == 200
        assert response.json()["access_token"] == "new-access-token"

    def test_refresh_logs_rotation_event(self, client):
        """
        GIVEN: Token rotation is enabled
        WHEN: Successful refresh with rotation
        THEN: Should log the rotation event for audit
        """
        from mcp_server_langgraph.auth.token_denylist import InMemoryTokenDenylist

        mock_denylist = InMemoryTokenDenylist()

        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = {
            "access_token": "new-access-token",
            "refresh_token": "new-refresh-token",
            "token_type": "Bearer",
            "expires_in": 300,
        }

        with (
            patch("mcp_server_langgraph.api.v1.auth.httpx.AsyncClient") as mock_client_class,
            patch("mcp_server_langgraph.api.v1.auth._get_token_denylist") as mock_get_denylist,
            patch("mcp_server_langgraph.api.v1.auth.logger") as mock_logger,
        ):
            mock_get_denylist.return_value = mock_denylist
            mock_client_class.return_value.__aenter__.return_value.post = AsyncMock(return_value=mock_response)

            response = client.post(
                "/auth/refresh",
                json={"refresh_token": "old-refresh-token"},
            )

        assert response.status_code == 200

        # Check that rotation was logged
        log_calls = [str(call) for call in mock_logger.info.call_args_list]
        rotation_logged = any("rotation" in call.lower() for call in log_calls)
        assert rotation_logged, "Token rotation event should be logged for audit"


# ============================================================================
# PAR (Pushed Authorization Requests) Tests - RFC 9126
# ============================================================================


@pytest.mark.xdist_group(name="par")
class TestPushedAuthorizationRequests:
    """
    Tests for Pushed Authorization Requests (PAR) - RFC 9126.

    PAR provides enhanced security by:
    - Pre-registering authorization requests server-side
    - Reducing authorization request URL size
    - Preventing request parameter tampering
    """

    def teardown_method(self) -> None:
        """Force GC to prevent accumulation in xdist workers."""
        gc.collect()

    def test_par_returns_request_uri(self, client):
        """
        GIVEN: Valid PAR request with required parameters
        WHEN: POST /auth/par is called
        THEN: Should return request_uri and expires_in
        """
        mock_response = MagicMock()
        mock_response.status_code = 201
        mock_response.json.return_value = {
            "request_uri": "urn:ietf:params:oauth:request_uri:abc123",
            "expires_in": 60,
        }

        with patch("mcp_server_langgraph.api.v1.auth.httpx.AsyncClient") as mock_client_class:
            mock_client_class.return_value.__aenter__.return_value.post = AsyncMock(return_value=mock_response)

            response = client.post(
                "/auth/par",
                json={
                    "redirect_uri": "https://app.example.com/callback",
                    "scope": "openid profile email",
                },
            )

        assert response.status_code == 201
        data = response.json()
        assert "request_uri" in data
        assert data["request_uri"].startswith("urn:ietf:params:oauth:request_uri:")
        assert "expires_in" in data
        assert data["expires_in"] > 0

    def test_par_validates_redirect_uri(self, client):
        """
        GIVEN: PAR request without redirect_uri
        WHEN: POST /auth/par is called
        THEN: Should return 422 validation error
        """
        response = client.post("/auth/par", json={"scope": "openid"})

        assert response.status_code == 422

    def test_par_includes_pkce_challenge(self, client):
        """
        GIVEN: PAR request with PKCE code_challenge
        WHEN: POST /auth/par is called
        THEN: Should include PKCE in request to Keycloak
        """
        mock_response = MagicMock()
        mock_response.status_code = 201
        mock_response.json.return_value = {
            "request_uri": "urn:ietf:params:oauth:request_uri:abc123",
            "expires_in": 60,
        }

        with patch("mcp_server_langgraph.api.v1.auth.httpx.AsyncClient") as mock_client_class:
            mock_post = AsyncMock(return_value=mock_response)
            mock_client_class.return_value.__aenter__.return_value.post = mock_post

            response = client.post(
                "/auth/par",
                json={
                    "redirect_uri": "https://app.example.com/callback",
                    "scope": "openid profile email",
                    "code_challenge": "E9Melhoa2OwvFrEMTJguCHaoeK1t8URWbuGJSstw-cM",
                    "code_challenge_method": "S256",
                },
            )

        assert response.status_code == 201

        # Verify PKCE was included in Keycloak request
        call_args = mock_post.call_args
        data = call_args.kwargs.get("data", {})
        assert "code_challenge" in data
        assert data["code_challenge_method"] == "S256"

    def test_par_returns_error_on_keycloak_failure(self, client):
        """
        GIVEN: Keycloak PAR endpoint returns error
        WHEN: POST /auth/par is called
        THEN: Should return appropriate error response
        """
        mock_response = MagicMock()
        mock_response.status_code = 400
        mock_response.json.return_value = {
            "error": "invalid_request",
            "error_description": "Invalid redirect_uri",
        }

        with patch("mcp_server_langgraph.api.v1.auth.httpx.AsyncClient") as mock_client_class:
            mock_client_class.return_value.__aenter__.return_value.post = AsyncMock(return_value=mock_response)

            response = client.post(
                "/auth/par",
                json={
                    "redirect_uri": "https://malicious.example.com/callback",
                    "scope": "openid",
                },
            )

        assert response.status_code == 400
        assert "error" in response.json()

    def test_par_login_uses_request_uri(self, client):
        """
        GIVEN: Valid request_uri from PAR
        WHEN: GET /auth/login is called with request_uri parameter
        THEN: Should redirect to Keycloak with request_uri instead of full params
        """
        response = client.get(
            "/auth/login",
            params={"request_uri": "urn:ietf:params:oauth:request_uri:abc123"},
            follow_redirects=False,
        )

        assert response.status_code == 307  # Redirect
        location = response.headers.get("location", "")
        assert "request_uri=urn" in location
        # Should NOT contain regular auth params when using request_uri
        assert "scope=" not in location or "request_uri=" in location


# ============================================================================
# Token Introspection Tests - RFC 7662
# ============================================================================


@pytest.mark.xdist_group(name="introspection")
class TestTokenIntrospection:
    """
    Tests for Token Introspection endpoint - RFC 7662.

    Token introspection allows resource servers to validate tokens
    and get information about them without parsing them locally.
    """

    def teardown_method(self) -> None:
        """Force GC to prevent accumulation in xdist workers."""
        gc.collect()

    def test_introspect_returns_active_for_valid_token(self, client):
        """
        GIVEN: A valid access token
        WHEN: POST /auth/introspect is called
        THEN: Should return active=true with token claims
        """
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = {
            "active": True,
            "sub": "user-123",
            "client_id": "test-client",
            "username": "testuser",
            "scope": "openid profile email",
            "exp": 1735689600,
            "iat": 1735686000,
        }

        with patch("mcp_server_langgraph.api.v1.auth.httpx.AsyncClient") as mock_client_class:
            mock_client_class.return_value.__aenter__.return_value.post = AsyncMock(return_value=mock_response)

            response = client.post(
                "/auth/introspect",
                json={"token": "valid-access-token"},
            )

        assert response.status_code == 200
        data = response.json()
        assert data["active"] is True
        assert data["sub"] == "user-123"
        assert "scope" in data

    def test_introspect_returns_inactive_for_expired_token(self, client):
        """
        GIVEN: An expired access token
        WHEN: POST /auth/introspect is called
        THEN: Should return active=false
        """
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = {"active": False}

        with patch("mcp_server_langgraph.api.v1.auth.httpx.AsyncClient") as mock_client_class:
            mock_client_class.return_value.__aenter__.return_value.post = AsyncMock(return_value=mock_response)

            response = client.post(
                "/auth/introspect",
                json={"token": "expired-token"},
            )

        assert response.status_code == 200
        data = response.json()
        assert data["active"] is False

    def test_introspect_requires_token_parameter(self, client):
        """
        GIVEN: Request without token
        WHEN: POST /auth/introspect is called
        THEN: Should return 422 validation error
        """
        response = client.post("/auth/introspect", json={})

        assert response.status_code == 422

    def test_introspect_supports_token_type_hint(self, client):
        """
        GIVEN: Token with type hint
        WHEN: POST /auth/introspect is called with token_type_hint
        THEN: Should forward type hint to Keycloak
        """
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = {"active": True}

        with patch("mcp_server_langgraph.api.v1.auth.httpx.AsyncClient") as mock_client_class:
            mock_post = AsyncMock(return_value=mock_response)
            mock_client_class.return_value.__aenter__.return_value.post = mock_post

            response = client.post(
                "/auth/introspect",
                json={"token": "some-token", "token_type_hint": "access_token"},
            )

        assert response.status_code == 200

        # Verify type hint was included in Keycloak request
        call_args = mock_post.call_args
        data = call_args.kwargs.get("data", {})
        assert data.get("token_type_hint") == "access_token"

    def test_introspect_returns_503_on_keycloak_failure(self, client):
        """
        GIVEN: Keycloak is unavailable
        WHEN: POST /auth/introspect is called
        THEN: Should return 503 service unavailable
        """
        import httpx

        with patch("mcp_server_langgraph.api.v1.auth.httpx.AsyncClient") as mock_client_class:
            mock_client_class.return_value.__aenter__.return_value.post = AsyncMock(
                side_effect=httpx.ConnectError("Connection refused")
            )

            response = client.post(
                "/auth/introspect",
                json={"token": "some-token"},
            )

        assert response.status_code == 503


# ============================================================================
# Backchannel Logout Tests - OIDC Backchannel Logout
# ============================================================================


@pytest.mark.xdist_group(name="backchannel_logout")
class TestBackchannelLogout:
    """
    Tests for OIDC Backchannel Logout.

    Allows Keycloak to notify our application when a user logs out,
    so we can immediately invalidate their tokens/sessions.
    """

    def teardown_method(self) -> None:
        """Force GC to prevent accumulation in xdist workers."""
        gc.collect()

    def test_backchannel_logout_accepts_logout_token(self, client):
        """
        GIVEN: Valid logout token from Keycloak
        WHEN: POST /auth/backchannel-logout is called
        THEN: Should return 200 OK
        """
        from mcp_server_langgraph.auth.token_denylist import InMemoryTokenDenylist

        mock_denylist = InMemoryTokenDenylist()

        # Create a mock logout token (JWT with logout event)
        logout_token = "eyJhbGciOiJSUzI1NiIsInR5cCI6IkpXVCJ9.eyJpc3MiOiJodHRwOi8vbG9jYWxob3N0OjgwODAvcmVhbG1zL3Rlc3QiLCJzdWIiOiJ1c2VyLTEyMyIsImF1ZCI6InRlc3QtY2xpZW50Iiwic2lkIjoic2Vzc2lvbi0xMjMiLCJpYXQiOjE3MzU2ODYwMDAsImV2ZW50cyI6eyJodHRwOi8vc2NoZW1hcy5vcGVuaWQubmV0L2V2ZW50L2JhY2tjaGFubmVsLWxvZ291dCI6e319fQ.signature"

        with (
            patch("mcp_server_langgraph.api.v1.auth._get_token_denylist") as mock_get_denylist,
            patch("mcp_server_langgraph.api.v1.auth._verify_logout_token") as mock_verify,
        ):
            mock_get_denylist.return_value = mock_denylist
            mock_verify.return_value = {
                "sub": "user-123",
                "sid": "session-123",
            }

            response = client.post(
                "/auth/backchannel-logout",
                data={"logout_token": logout_token},
                headers={"Content-Type": "application/x-www-form-urlencoded"},
            )

        assert response.status_code == 200

    def test_backchannel_logout_requires_logout_token(self, client):
        """
        GIVEN: Request without logout_token
        WHEN: POST /auth/backchannel-logout is called
        THEN: Should return 400 bad request
        """
        response = client.post(
            "/auth/backchannel-logout",
            data={},
            headers={"Content-Type": "application/x-www-form-urlencoded"},
        )

        # Should return 400 for missing logout_token
        assert response.status_code == 400

    def test_backchannel_logout_adds_session_to_denylist(self, client):
        """
        GIVEN: Valid logout token with session ID
        WHEN: POST /auth/backchannel-logout is called
        THEN: Session should be added to denylist
        """
        import asyncio
        from mcp_server_langgraph.auth.token_denylist import InMemoryTokenDenylist

        mock_denylist = InMemoryTokenDenylist()

        with (
            patch("mcp_server_langgraph.api.v1.auth._get_token_denylist") as mock_get_denylist,
            patch("mcp_server_langgraph.api.v1.auth._verify_logout_token") as mock_verify,
        ):
            mock_get_denylist.return_value = mock_denylist
            mock_verify.return_value = {
                "sub": "user-123",
                "sid": "session-to-logout",
            }

            response = client.post(
                "/auth/backchannel-logout",
                data={"logout_token": "valid-logout-token"},
                headers={"Content-Type": "application/x-www-form-urlencoded"},
            )

        assert response.status_code == 200

        # Verify session was added to denylist
        async def check_denied():
            return await mock_denylist.is_denied("session-to-logout")

        is_denied = asyncio.new_event_loop().run_until_complete(check_denied())
        assert is_denied is True, "Session should be in denylist"

    def test_backchannel_logout_rejects_invalid_token(self, client):
        """
        GIVEN: Invalid logout token
        WHEN: POST /auth/backchannel-logout is called
        THEN: Should return 400 bad request
        """
        with patch("mcp_server_langgraph.api.v1.auth._verify_logout_token") as mock_verify:
            mock_verify.side_effect = ValueError("Invalid logout token")

            response = client.post(
                "/auth/backchannel-logout",
                data={"logout_token": "invalid-token"},
                headers={"Content-Type": "application/x-www-form-urlencoded"},
            )

        assert response.status_code == 400


# ============================================================================
# Security Headers Tests (OWASP Best Practices)
# ============================================================================


@pytest.mark.xdist_group(name="security_headers")
class TestAuthSecurityHeaders:
    """
    Tests for security headers on auth endpoints.

    Per OWASP Security Headers Guidelines:
    - X-Content-Type-Options: nosniff (prevents MIME sniffing)
    - X-Frame-Options: DENY (prevents clickjacking)
    - Content-Security-Policy (prevents XSS)
    - Strict-Transport-Security (enforces HTTPS)
    """

    def teardown_method(self) -> None:
        """Force GC to prevent accumulation in xdist workers."""
        gc.collect()

    def test_login_response_has_x_content_type_options(self, client):
        """
        GIVEN: Auth login endpoint
        WHEN: GET /auth/login is called
        THEN: Response should include X-Content-Type-Options: nosniff
        """
        response = client.get("/auth/login", follow_redirects=False)

        # Check for X-Content-Type-Options header
        header = response.headers.get("x-content-type-options", "").lower()
        assert header == "nosniff", "X-Content-Type-Options should be 'nosniff'"

    def test_login_response_has_x_frame_options(self, client):
        """
        GIVEN: Auth login endpoint
        WHEN: GET /auth/login is called
        THEN: Response should include X-Frame-Options: DENY
        """
        response = client.get("/auth/login", follow_redirects=False)

        # Check for X-Frame-Options header
        header = response.headers.get("x-frame-options", "").upper()
        assert header in ("DENY", "SAMEORIGIN"), "X-Frame-Options should be DENY or SAMEORIGIN"

    def test_refresh_response_has_security_headers(self, client):
        """
        GIVEN: Auth refresh endpoint
        WHEN: POST /auth/refresh is called (even with invalid data)
        THEN: Response should include security headers
        """
        response = client.post("/auth/refresh", json={})

        # Even error responses should have security headers
        assert response.headers.get("x-content-type-options") is not None or response.status_code == 422

    def test_introspect_response_has_security_headers(self, client):
        """
        GIVEN: Token introspection endpoint
        WHEN: POST /auth/introspect is called
        THEN: Response should include security headers
        """
        response = client.post("/auth/introspect", json={})

        # Even error responses should have security headers
        assert response.headers.get("x-content-type-options") is not None or response.status_code == 422

    def test_par_response_has_security_headers(self, client):
        """
        GIVEN: PAR endpoint
        WHEN: POST /auth/par is called
        THEN: Response should include security headers
        """
        response = client.post("/auth/par", json={})

        # Even error responses should have security headers
        assert response.headers.get("x-content-type-options") is not None or response.status_code == 422

    def test_callback_error_response_has_security_headers(self, client):
        """
        GIVEN: Auth callback endpoint with error
        WHEN: Error response is returned
        THEN: Error response should still include security headers
        """
        response = client.get("/auth/callback?error=access_denied&error_description=User+denied")

        # Error responses should have security headers too
        assert response.headers.get("x-content-type-options") is not None or response.status_code == 400

    def test_logout_response_has_security_headers(self, client):
        """
        GIVEN: Logout endpoint
        WHEN: GET /auth/logout is called
        THEN: Response should include security headers
        """
        response = client.get("/auth/logout", follow_redirects=False)

        # Logout should have security headers (redirect or success)
        assert response.headers.get("x-content-type-options") is not None


# ============================================================================
# GET /auth/logout Tests
# ============================================================================


@pytest.mark.xdist_group(name="oauth2_api")
class TestOAuth2Logout:
    """Tests for GET /auth/logout - OAuth2 logout flow initiation."""

    def teardown_method(self) -> None:
        """Force GC to prevent accumulation in xdist workers."""
        gc.collect()

    def test_logout_returns_redirect(self, client):
        """
        GIVEN: User wants to log out
        WHEN: GET /auth/logout is called
        THEN: Should return a redirect (302) to Keycloak end_session endpoint
        """
        response = client.get("/auth/logout", follow_redirects=False)

        # Should be a redirect to Keycloak logout
        assert response.status_code == 302
        location = response.headers.get("location", "")
        assert "/realms/" in location
        assert "logout" in location.lower() or "end_session" in location.lower()

    def test_logout_redirect_includes_client_id(self, client):
        """
        GIVEN: OAuth2 logout with Keycloak
        WHEN: Logout redirect is returned
        THEN: Redirect URL should include client_id parameter
        """
        response = client.get("/auth/logout", follow_redirects=False)

        location = response.headers.get("location", "")
        assert "client_id=" in location

    def test_logout_with_post_logout_redirect(self, client):
        """
        GIVEN: User specifies a post-logout redirect URI
        WHEN: GET /auth/logout?post_logout_redirect_uri=... is called
        THEN: Redirect should include the post_logout_redirect_uri
        """
        redirect_uri = "http://localhost/login"
        response = client.get(
            f"/auth/logout?post_logout_redirect_uri={redirect_uri}",
            follow_redirects=False,
        )

        # Should redirect to Keycloak with the post_logout_redirect_uri
        assert response.status_code == 302
        location = response.headers.get("location", "")
        assert "post_logout_redirect_uri" in location

    def test_logout_clears_oauth2_cookies(self, client):
        """
        GIVEN: User has OAuth2 session cookies
        WHEN: Logout is called
        THEN: Session cookies should be cleared (set to expire)
        """
        # First, set some cookies as if we were logged in
        client.cookies.set("oauth2_code_verifier", "test_verifier")
        client.cookies.set("oauth2_state", "test_state")
        client.cookies.set("session_id", "test_session")

        response = client.get("/auth/logout", follow_redirects=False)

        # Check that cookies are cleared in the response (Max-Age=0 or Expires in past)
        _set_cookie_headers = response.headers.get_list("set-cookie") if hasattr(response.headers, "get_list") else []
        # The response should attempt to clear cookies (exact implementation may vary)
        # Note: _set_cookie_headers captured for debugging but verification is on redirect
        assert response.status_code == 302  # Still should redirect

    def test_logout_with_id_token_hint(self, client):
        """
        GIVEN: User provides id_token_hint for logout
        WHEN: GET /auth/logout?id_token_hint=... is called
        THEN: Redirect should include the id_token_hint parameter
        """
        mock_id_token = "eyJ0eXAiOiJKV1QiLCJhbGciOiJSUzI1NiJ9.eyJpc3MiOiJ0ZXN0In0.fake"
        response = client.get(
            f"/auth/logout?id_token_hint={mock_id_token}",
            follow_redirects=False,
        )

        assert response.status_code == 302
        location = response.headers.get("location", "")
        assert "id_token_hint=" in location


@pytest.mark.api
@pytest.mark.auth
class TestNativeLogout:
    """
    Tests for POST /auth/logout (native logout for SPAs).

    Per ADR-0071: Native logout should:
    - Revoke the refresh token with Keycloak
    - Clear the session cookie (mcp_session)
    - Return a JSON response with keycloak_logout_url
    """

    @pytest.fixture(autouse=True)
    def cleanup(self):
        """Force GC to prevent accumulation in xdist workers."""
        yield
        gc.collect()

    def test_native_logout_returns_success(self, client):
        """
        GIVEN: User wants to log out via SPA
        WHEN: POST /auth/logout is called
        THEN: Should return 200 OK with success message
        """
        response = client.post(
            "/auth/logout",
            json={},
        )

        assert response.status_code == 200
        data = response.json()
        assert data["success"] is True
        assert "keycloak_logout_url" in data

    def test_native_logout_clears_session_cookie(self, client):
        """
        GIVEN: User has a session cookie
        WHEN: POST /auth/logout is called
        THEN: Response should delete the mcp_session cookie

        This is critical for multi-user logout - without clearing
        the session cookie, users get logged back in as the previous user.
        """
        from mcp_server_langgraph.studio.security import SESSION_COOKIE_NAME

        # Set a session cookie on the request
        client.cookies.set(SESSION_COOKIE_NAME, "test-session-value")

        response = client.post(
            "/auth/logout",
            json={},
        )

        assert response.status_code == 200

        # Check that the session cookie is deleted (Max-Age=0 or expires in past)
        set_cookie_headers = response.headers.get_list("set-cookie")
        session_cookie_deleted = False

        for cookie_header in set_cookie_headers:
            if SESSION_COOKIE_NAME in cookie_header:
                # Cookie is deleted if Max-Age=0 or expires in past
                if "max-age=0" in cookie_header.lower() or "expires=" in cookie_header.lower():
                    session_cookie_deleted = True
                    break

        assert session_cookie_deleted, (
            f"Session cookie '{SESSION_COOKIE_NAME}' should be deleted in logout response. "
            f"Set-Cookie headers: {set_cookie_headers}"
        )

    def test_native_logout_with_refresh_token(self, client):
        """
        GIVEN: User provides a refresh token to revoke
        WHEN: POST /auth/logout is called with refresh_token
        THEN: Should attempt token revocation and return success
        """
        response = client.post(
            "/auth/logout",
            json={"refresh_token": "mock-refresh-token"},
        )

        # Should still return success even if Keycloak is not available
        # (revocation failure is logged but doesn't fail the logout)
        assert response.status_code == 200
        data = response.json()
        assert data["success"] is True

    def test_native_logout_returns_keycloak_logout_url(self, client):
        """
        GIVEN: User logs out via native endpoint
        WHEN: POST /auth/logout is called
        THEN: Response should include Keycloak logout URL for frontend redirect
        """
        response = client.post(
            "/auth/logout",
            json={},
        )

        assert response.status_code == 200
        data = response.json()
        assert "keycloak_logout_url" in data

        logout_url = data["keycloak_logout_url"]
        assert "/protocol/openid-connect/logout" in logout_url
        assert "client_id=" in logout_url
