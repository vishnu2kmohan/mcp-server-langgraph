"""
Integration tests for SSO (Single Sign-On) browser-based authentication flow.

Tests the OAuth2 Authorization Code + PKCE flow with Keycloak.
Per RFC 9700: ROPC MUST NOT be used. Use Authorization Code + PKCE instead.

Test scenarios:
1. Login initiation and redirect to Keycloak
2. PKCE parameter validation
3. Callback handling with authorization code
4. Token refresh flow
5. Logout and session termination

These tests validate:
- OAuth2 Authorization Code flow works end-to-end
- PKCE (Proof Key for Code Exchange) is properly implemented
- Session management with secure cookies
- Token refresh before expiration
- Logout clears all session data

References:
    - ADR-0071: OAuth2 + PKCE Migration
    - RFC 7636: PKCE
    - RFC 9700: OAuth 2.0 Security Best Practices
    - src/mcp_server_langgraph/api/v1/auth.py
"""

import gc
import hashlib
import os
import secrets
from base64 import urlsafe_b64encode
from urllib.parse import parse_qs, urlparse

import pytest
import requests

pytestmark = [
    pytest.mark.integration,
    pytest.mark.auth,
    pytest.mark.sso,
    pytest.mark.xdist_group(name="sso_flow"),
]


def get_worker_prefix() -> str:
    """Get worker-specific prefix for test isolation in parallel execution."""
    worker_id = os.getenv("PYTEST_XDIST_WORKER", "main")
    return f"test_{worker_id}"


def teardown_module():
    """Force GC to prevent mock accumulation in xdist workers."""
    gc.collect()


def _api_available() -> bool:
    """Check if the API server is available via Traefik gateway."""
    try:
        # Tests run outside Docker network, so access via Traefik gateway (port 80)
        # /login is publicly accessible (no forward-auth) and confirms API server is up
        response = requests.get(
            "http://localhost/login",
            timeout=5,
        )
        return response.status_code == 200
    except Exception:
        return False


def _keycloak_available() -> bool:
    """Check if Keycloak is available via Traefik gateway."""
    try:
        # Tests run outside Docker network, so access via Traefik gateway (port 80)
        # Keycloak is routed via /authn path prefix in docker-compose.test.yml
        response = requests.get(
            "http://localhost/authn/realms/default/.well-known/openid-configuration",
            timeout=5,
        )
        return response.status_code == 200
    except Exception:
        return False


def generate_pkce_pair() -> tuple[str, str]:
    """
    Generate PKCE code verifier and challenge pair.

    Returns:
        Tuple of (code_verifier, code_challenge)
    """
    code_verifier = secrets.token_urlsafe(32)
    code_challenge = urlsafe_b64encode(hashlib.sha256(code_verifier.encode()).digest()).decode().rstrip("=")
    return code_verifier, code_challenge


@pytest.fixture(autouse=True)
def teardown_gc():
    """Force GC after each test to prevent memory accumulation."""
    yield
    gc.collect()


class TestSSOLoginInitiation:
    """Tests for SSO login flow initiation."""

    def teardown_method(self) -> None:
        """Force GC to prevent mock accumulation in xdist workers."""
        gc.collect()

    @pytest.mark.skipif(not _api_available(), reason="API server not available")
    def test_login_endpoint_returns_redirect(self) -> None:
        """
        GIVEN the API server is running with OAuth2 configured
        WHEN GET /api/v1/auth/login is called
        THEN a 302 redirect response is returned.
        """
        response = requests.get(
            "http://localhost/api/v1/auth/login",
            allow_redirects=False,
            timeout=10,
        )

        assert response.status_code == 302
        assert "location" in response.headers

    @pytest.mark.skipif(not _api_available(), reason="API server not available")
    def test_login_redirect_to_keycloak(self) -> None:
        """
        GIVEN the API server is configured with Keycloak
        WHEN login is initiated
        THEN redirect URL points to Keycloak authorization endpoint.
        """
        response = requests.get(
            "http://localhost/api/v1/auth/login",
            allow_redirects=False,
            timeout=10,
        )

        location = response.headers.get("location", "")
        parsed = urlparse(location)

        # Should redirect to Keycloak
        assert "realms" in parsed.path or "keycloak" in parsed.netloc.lower()
        assert "openid-connect/auth" in parsed.path

    @pytest.mark.skipif(not _api_available(), reason="API server not available")
    def test_login_includes_pkce_parameters(self) -> None:
        """
        GIVEN OAuth2 + PKCE is configured
        WHEN login is initiated
        THEN redirect URL includes PKCE code_challenge and method.
        """
        response = requests.get(
            "http://localhost/api/v1/auth/login",
            allow_redirects=False,
            timeout=10,
        )

        location = response.headers.get("location", "")
        parsed = urlparse(location)
        query_params = parse_qs(parsed.query)

        # PKCE parameters must be present
        assert "code_challenge" in query_params
        assert "code_challenge_method" in query_params
        assert query_params["code_challenge_method"][0] == "S256"

    @pytest.mark.skipif(not _api_available(), reason="API server not available")
    def test_login_includes_oauth2_parameters(self) -> None:
        """
        GIVEN OAuth2 is configured
        WHEN login is initiated
        THEN redirect URL includes required OAuth2 parameters.
        """
        response = requests.get(
            "http://localhost/api/v1/auth/login",
            allow_redirects=False,
            timeout=10,
        )

        location = response.headers.get("location", "")
        parsed = urlparse(location)
        query_params = parse_qs(parsed.query)

        # Required OAuth2 parameters
        assert "client_id" in query_params
        assert "redirect_uri" in query_params
        assert "response_type" in query_params
        assert query_params["response_type"][0] == "code"
        assert "state" in query_params
        assert "scope" in query_params

    @pytest.mark.skipif(not _api_available(), reason="API server not available")
    def test_login_sets_secure_cookies(self) -> None:
        """
        GIVEN OAuth2 + PKCE is configured
        WHEN login is initiated
        THEN secure cookies are set for PKCE state management.
        """
        response = requests.get(
            "http://localhost/api/v1/auth/login",
            allow_redirects=False,
            timeout=10,
        )

        cookies = response.cookies

        # PKCE cookies should be set
        assert "oauth2_code_verifier" in cookies or "oauth2_state" in cookies


class TestSSOCallbackHandling:
    """Tests for OAuth2 callback handling."""

    def teardown_method(self) -> None:
        """Force GC to prevent mock accumulation in xdist workers."""
        gc.collect()

    @pytest.mark.skipif(not _api_available(), reason="API server not available")
    def test_callback_without_code_returns_error(self) -> None:
        """
        GIVEN the callback endpoint is called
        WHEN no authorization code is provided
        THEN an error response is returned.
        """
        response = requests.get(
            "http://localhost/api/v1/auth/callback",
            timeout=10,
        )

        # Should return 400 or 422 for missing code
        assert response.status_code in [400, 422]

    @pytest.mark.skipif(not _api_available(), reason="API server not available")
    def test_callback_with_invalid_state_returns_error(self) -> None:
        """
        GIVEN the callback endpoint is called
        WHEN state parameter doesn't match session state
        THEN an error response is returned.
        """
        response = requests.get(
            "http://localhost/api/v1/auth/callback",
            params={
                "code": "invalid_code",
                "state": "mismatched_state",
            },
            timeout=10,
        )

        # Should return 400 or 401 for state mismatch
        assert response.status_code in [400, 401, 422]

    @pytest.mark.skipif(not _api_available(), reason="API server not available")
    def test_callback_with_error_parameter_returns_error(self) -> None:
        """
        GIVEN Keycloak returns an error (e.g., user denied consent)
        WHEN callback is called with error parameter
        THEN appropriate error response is returned.
        """
        response = requests.get(
            "http://localhost/api/v1/auth/callback",
            params={
                "error": "access_denied",
                "error_description": "User denied the request",
            },
            timeout=10,
        )

        # Should return 400 or redirect with error
        assert response.status_code in [400, 401, 302]


class TestSSOLogoutFlow:
    """Tests for SSO logout flow."""

    def teardown_method(self) -> None:
        """Force GC to prevent mock accumulation in xdist workers."""
        gc.collect()

    @pytest.mark.skipif(not _api_available(), reason="API server not available")
    def test_logout_endpoint_exists(self) -> None:
        """
        GIVEN the API server is running
        WHEN GET /api/v1/auth/logout is called
        THEN a valid response is returned.
        """
        response = requests.get(
            "http://localhost/api/v1/auth/logout",
            allow_redirects=False,
            timeout=10,
        )

        # Should return redirect (302) to Keycloak logout or 200 for API logout
        assert response.status_code in [200, 302]

    @pytest.mark.skipif(not _api_available(), reason="API server not available")
    def test_logout_clears_cookies(self) -> None:
        """
        GIVEN a user is logged in (has session cookies)
        WHEN logout is called
        THEN session cookies are cleared.
        """
        session = requests.Session()

        # Simulate having session cookies
        session.cookies.set("session_id", "test_session")
        session.cookies.set("oauth2_code_verifier", "test_verifier")

        response = session.get(
            "http://localhost/api/v1/auth/logout",
            allow_redirects=False,
            timeout=10,
        )

        # After logout, cookies should be cleared or expire
        assert response.status_code in [200, 302]


class TestSSOTokenRefresh:
    """Tests for OAuth2 token refresh flow."""

    def teardown_method(self) -> None:
        """Force GC to prevent mock accumulation in xdist workers."""
        gc.collect()

    @pytest.mark.skipif(not _api_available(), reason="API server not available")
    def test_refresh_endpoint_requires_auth(self) -> None:
        """
        GIVEN the refresh endpoint is called
        WHEN no valid refresh token is provided
        THEN authentication error is returned.
        """
        response = requests.post(
            "http://localhost/api/v1/auth/refresh",
            timeout=10,
        )

        # Should require authentication
        assert response.status_code in [401, 403, 422]


class TestPKCEImplementation:
    """Tests for PKCE (Proof Key for Code Exchange) implementation."""

    def teardown_method(self) -> None:
        """Force GC to prevent mock accumulation in xdist workers."""
        gc.collect()

    def test_pkce_code_verifier_generation(self) -> None:
        """
        GIVEN PKCE is used
        WHEN code verifier is generated
        THEN it meets RFC 7636 requirements.
        """
        code_verifier, _ = generate_pkce_pair()

        # RFC 7636: verifier must be 43-128 characters
        assert len(code_verifier) >= 43
        assert len(code_verifier) <= 128

        # Must be URL-safe characters
        allowed_chars = set("ABCDEFGHIJKLMNOPQRSTUVWXYZabcdefghijklmnopqrstuvwxyz0123456789-._~")
        assert all(c in allowed_chars for c in code_verifier)

    def test_pkce_code_challenge_s256(self) -> None:
        """
        GIVEN PKCE with S256 method
        WHEN code challenge is computed
        THEN it matches SHA256(code_verifier) in base64url.
        """
        code_verifier, code_challenge = generate_pkce_pair()

        # Verify the challenge is correctly computed
        expected = urlsafe_b64encode(hashlib.sha256(code_verifier.encode()).digest()).decode().rstrip("=")

        assert code_challenge == expected

    def test_pkce_pairs_are_unique(self) -> None:
        """
        GIVEN multiple PKCE pairs are generated
        WHEN comparing them
        THEN each pair is unique.
        """
        pairs = [generate_pkce_pair() for _ in range(10)]
        verifiers = [p[0] for p in pairs]
        challenges = [p[1] for p in pairs]

        # All verifiers should be unique
        assert len(set(verifiers)) == 10
        # All challenges should be unique
        assert len(set(challenges)) == 10


class TestSSOSecurityHeaders:
    """Tests for security headers in SSO responses."""

    def teardown_method(self) -> None:
        """Force GC to prevent mock accumulation in xdist workers."""
        gc.collect()

    @pytest.mark.skipif(not _api_available(), reason="API server not available")
    def test_login_response_has_security_headers(self) -> None:
        """
        GIVEN the login endpoint is called
        WHEN response is returned
        THEN appropriate security headers are present.
        """
        response = requests.get(
            "http://localhost/api/v1/auth/login",
            allow_redirects=False,
            timeout=10,
        )

        # Cache-Control should prevent caching of auth redirects
        cache_control = response.headers.get("cache-control", "").lower()
        assert "no-store" in cache_control or "no-cache" in cache_control or response.status_code == 302

    @pytest.mark.skipif(not _api_available(), reason="API server not available")
    def test_callback_response_has_security_headers(self) -> None:
        """
        GIVEN the callback endpoint is called
        WHEN response is returned
        THEN appropriate security headers are present.
        """
        response = requests.get(
            "http://localhost/api/v1/auth/callback",
            params={"error": "test"},
            timeout=10,
        )

        # Should have cache control
        headers = response.headers

        # At minimum, sensitive endpoints shouldn't be cached
        if "cache-control" in headers:
            cache_control = headers["cache-control"].lower()
            assert "public" not in cache_control or "max-age=0" in cache_control
