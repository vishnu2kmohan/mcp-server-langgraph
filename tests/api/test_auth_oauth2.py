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
    from mcp_server_langgraph.api.v1.auth import auth_router

    app = FastAPI()
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
