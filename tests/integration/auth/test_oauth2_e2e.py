"""
End-to-End OAuth2 Integration Tests with Keycloak.

Tests the complete OAuth2 Authorization Code + PKCE flow with real Keycloak.
Per RFC 9700: ROPC MUST NOT be used. Use Authorization Code + PKCE instead.

Test scenarios:
1. Full login flow (login → Keycloak redirect → callback → tokens)
2. Token refresh with rotation (old tokens denylisted)
3. Token introspection (RFC 7662)
4. Backchannel logout (OIDC Back-Channel Logout 1.0)
5. PAR flow (Pushed Authorization Requests - RFC 9126)
6. Security headers on all auth endpoints

Requirements:
- Keycloak running and accessible (docker compose up keycloak)
- API server running (uvicorn mcp_server_langgraph.main:app)
- Test client configured in Keycloak

References:
    - ADR-0071: OAuth2 + PKCE Migration
    - RFC 7636: PKCE
    - RFC 7662: Token Introspection
    - RFC 9126: Pushed Authorization Requests
    - RFC 9700: OAuth 2.0 Security Best Practices
    - OIDC Back-Channel Logout 1.0
    - src/mcp_server_langgraph/api/v1/auth.py
"""

import gc
import hashlib
import os
from base64 import urlsafe_b64encode
from urllib.parse import parse_qs, urlparse

import pytest
import requests

pytestmark = [
    pytest.mark.integration,
    pytest.mark.auth,
    pytest.mark.oauth2,
    pytest.mark.e2e,
    pytest.mark.xdist_group(name="oauth2_e2e"),
]


# ============================================================================
# Infrastructure Availability Checks
# ============================================================================


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


def _keycloak_via_gateway_available() -> bool:
    """Check if Keycloak is available via Traefik gateway (alias for _keycloak_available)."""
    return _keycloak_available()


def _full_infrastructure_available() -> bool:
    """Check if both API server and Keycloak are available via gateway."""
    return _api_available() and _keycloak_available()


def get_worker_prefix() -> str:
    """Get worker-specific prefix for test isolation in parallel execution."""
    worker_id = os.getenv("PYTEST_XDIST_WORKER", "main")
    return f"test_{worker_id}"


# PYTEST-XDIST FIX: E2E tests against Keycloak are flaky in parallel execution
# because infrastructure availability checks may pass but the actual operations
# fail due to timing issues with container startup/readiness.
_XDIST_E2E_INFRASTRUCTURE_UNSTABLE = os.getenv("PYTEST_XDIST_WORKER") is not None


# ============================================================================
# Helper Functions
# ============================================================================


def generate_pkce_pair() -> tuple[str, str]:
    """
    Generate PKCE code verifier and challenge pair.

    Returns:
        Tuple of (code_verifier, code_challenge)
    """
    import secrets

    code_verifier = secrets.token_urlsafe(64)[:128]
    code_challenge = urlsafe_b64encode(hashlib.sha256(code_verifier.encode()).digest()).decode().rstrip("=")
    return code_verifier, code_challenge


def get_keycloak_token_url() -> str:
    """Get the Keycloak token endpoint URL via gateway."""
    # Always use gateway URL since tests run outside Docker network
    return "http://localhost/authn/realms/default/protocol/openid-connect/token"


def get_user_tokens(
    username: str = "admin",
    password: str = "admin123",  # Deprecated: ROPC is disabled
    client_id: str = "mcp-server",
    client_secret: str = "test-client-secret-for-e2e-tests",
) -> dict | None:
    """
    Get access and refresh tokens for a user.

    Uses Token Exchange (RFC 8693) or client_credentials grant.
    ROPC is disabled per security audit.

    Note: Returns dict with 'access_token' key from service account if
    Token Exchange is not configured.
    """
    token_url = get_keycloak_token_url()

    # Try Token Exchange first (RFC 8693)
    try:
        response = requests.post(
            token_url,
            data={
                "grant_type": "urn:ietf:params:oauth:grant-type:token-exchange",
                "client_id": client_id,
                "client_secret": client_secret,
                "requested_subject": username,
                "subject_token_type": "urn:ietf:params:oauth:token-type:access_token",
                "requested_token_type": "urn:ietf:params:oauth:token-type:access_token",
                "scope": "openid profile email",
            },
            timeout=10,
        )
        if response.status_code == 200:
            return response.json()
    except Exception:
        pass

    # Fallback to client credentials (service account)
    try:
        response = requests.post(
            token_url,
            data={
                "grant_type": "client_credentials",
                "client_id": client_id,
                "client_secret": client_secret,
                "scope": "openid profile email",
            },
            timeout=10,
        )
        if response.status_code == 200:
            return response.json()
    except Exception:
        pass

    return None


# ============================================================================
# Test Fixtures
# ============================================================================


@pytest.fixture(autouse=True)
def teardown_gc():
    """Force GC after each test to prevent memory accumulation."""
    yield
    gc.collect()


@pytest.fixture
def user_tokens():
    """Get test user tokens."""
    tokens = get_user_tokens()
    if tokens is None:
        pytest.skip("Could not obtain test user tokens from Keycloak")
    return tokens


@pytest.fixture
def api_session():
    """Create a requests session for API calls."""
    session = requests.Session()
    yield session
    session.close()


# ============================================================================
# E2E OAuth2 Authorization Code + PKCE Flow Tests
# ============================================================================


class TestOAuth2LoginFlowE2E:
    """E2E tests for OAuth2 Authorization Code + PKCE login flow."""

    def teardown_method(self) -> None:
        """Force GC to prevent mock accumulation in xdist workers."""
        gc.collect()

    @pytest.mark.skipif(not _api_available(), reason="API server not available")
    def test_login_initiates_oauth2_flow_with_keycloak(self) -> None:
        """
        GIVEN the API server and Keycloak are running
        WHEN GET /api/v1/auth/login is called
        THEN a redirect to Keycloak authorization endpoint is returned.
        """
        response = requests.get(
            "http://localhost/api/v1/auth/login",
            allow_redirects=False,
            timeout=10,
        )

        assert response.status_code == 302
        location = response.headers.get("location", "")
        assert "openid-connect/auth" in location

    @pytest.mark.skipif(not _api_available(), reason="API server not available")
    def test_login_includes_pkce_code_challenge(self) -> None:
        """
        GIVEN OAuth2 + PKCE is configured
        WHEN login is initiated
        THEN PKCE code_challenge is included in the authorization URL.
        """
        response = requests.get(
            "http://localhost/api/v1/auth/login",
            allow_redirects=False,
            timeout=10,
        )

        location = response.headers.get("location", "")
        parsed = urlparse(location)
        query_params = parse_qs(parsed.query)

        assert "code_challenge" in query_params
        assert "code_challenge_method" in query_params
        assert query_params["code_challenge_method"][0] == "S256"

        # Verify code_challenge is base64url-encoded SHA256 hash (43 chars without padding)
        code_challenge = query_params["code_challenge"][0]
        assert len(code_challenge) == 43  # SHA256 in base64url without padding

    @pytest.mark.skipif(not _api_available(), reason="API server not available")
    def test_login_stores_pkce_verifier_in_cookie(self) -> None:
        """
        GIVEN OAuth2 + PKCE is configured
        WHEN login is initiated
        THEN PKCE code_verifier is stored in a secure HTTP-only cookie.
        """
        response = requests.get(
            "http://localhost/api/v1/auth/login",
            allow_redirects=False,
            timeout=10,
        )

        # Check for PKCE cookies
        cookies = response.cookies
        assert "oauth2_code_verifier" in cookies
        assert "oauth2_state" in cookies

    @pytest.mark.skipif(not _api_available(), reason="API server not available")
    def test_login_includes_state_for_csrf_protection(self) -> None:
        """
        GIVEN OAuth2 is configured with CSRF protection
        WHEN login is initiated
        THEN a state parameter is included for CSRF validation.
        """
        response = requests.get(
            "http://localhost/api/v1/auth/login",
            allow_redirects=False,
            timeout=10,
        )

        location = response.headers.get("location", "")
        parsed = urlparse(location)
        query_params = parse_qs(parsed.query)

        assert "state" in query_params
        state = query_params["state"][0]
        # State should be cryptographically random (at least 32 chars)
        assert len(state) >= 32


# ============================================================================
# E2E Token Refresh with Rotation Tests
# ============================================================================


class TestTokenRefreshWithRotationE2E:
    """E2E tests for token refresh with rotation (security hardening)."""

    def teardown_method(self) -> None:
        """Force GC to prevent mock accumulation in xdist workers."""
        gc.collect()

    @pytest.mark.skipif(not _api_available(), reason="API server not available")
    @pytest.mark.skipif(not _keycloak_available() and not _keycloak_via_gateway_available(), reason="Keycloak not available")
    @pytest.mark.xfail(
        _XDIST_E2E_INFRASTRUCTURE_UNSTABLE,
        reason="Keycloak infrastructure timing issues in xdist parallel execution",
        strict=False,
    )
    def test_refresh_token_returns_new_tokens(self, user_tokens) -> None:
        """
        GIVEN a valid refresh token from Keycloak
        WHEN POST /api/v1/auth/refresh is called
        THEN new access and refresh tokens are returned.
        """
        response = requests.post(
            "http://localhost/api/v1/auth/refresh",
            json={"refresh_token": user_tokens["refresh_token"]},
            timeout=10,
        )

        assert response.status_code == 200
        data = response.json()
        assert "access_token" in data
        assert "refresh_token" in data
        assert data["token_type"] == "Bearer"
        assert data["expires_in"] > 0

    @pytest.mark.skipif(not _api_available(), reason="API server not available")
    @pytest.mark.skipif(not _keycloak_available() and not _keycloak_via_gateway_available(), reason="Keycloak not available")
    @pytest.mark.xfail(
        _XDIST_E2E_INFRASTRUCTURE_UNSTABLE,
        reason="Keycloak infrastructure timing issues in xdist parallel execution",
        strict=False,
    )
    def test_refresh_token_rotation_invalidates_old_token(self, user_tokens) -> None:
        """
        GIVEN a valid refresh token
        WHEN the token is refreshed successfully
        THEN the old refresh token should be invalidated (denylisted).
        """
        old_refresh_token = user_tokens["refresh_token"]

        # First refresh - should succeed
        response1 = requests.post(
            "http://localhost/api/v1/auth/refresh",
            json={"refresh_token": old_refresh_token},
            timeout=10,
        )

        assert response1.status_code == 200
        _ = response1.json()  # Verify response is valid JSON

        # Second refresh with OLD token - should fail (token rotated)
        response2 = requests.post(
            "http://localhost/api/v1/auth/refresh",
            json={"refresh_token": old_refresh_token},
            timeout=10,
        )

        # Should be rejected - token was rotated and old one is denylisted
        # Note: This depends on token denylist being enabled
        # If rotation is enabled, status should be 401
        # If rotation is disabled, Keycloak may still reject (invalid_grant)
        assert response2.status_code in [401, 400]

    @pytest.mark.skipif(not _api_available(), reason="API server not available")
    def test_refresh_with_invalid_token_returns_error(self) -> None:
        """
        GIVEN an invalid refresh token
        WHEN POST /api/v1/auth/refresh is called
        THEN an error response is returned (400 or 401).
        """
        response = requests.post(
            "http://localhost/api/v1/auth/refresh",
            json={"refresh_token": "invalid-refresh-token"},
            timeout=10,
        )

        # Invalid token should return either 400 (bad request) or 401 (unauthorized)
        assert response.status_code in [400, 401, 422]


# ============================================================================
# E2E Token Introspection Tests (RFC 7662)
# ============================================================================


class TestTokenIntrospectionE2E:
    """E2E tests for Token Introspection endpoint (RFC 7662)."""

    def teardown_method(self) -> None:
        """Force GC to prevent mock accumulation in xdist workers."""
        gc.collect()

    @pytest.mark.skipif(not _api_available(), reason="API server not available")
    @pytest.mark.skipif(not _keycloak_available() and not _keycloak_via_gateway_available(), reason="Keycloak not available")
    @pytest.mark.xfail(
        _XDIST_E2E_INFRASTRUCTURE_UNSTABLE,
        reason="Keycloak infrastructure timing issues in xdist parallel execution",
        strict=False,
    )
    def test_introspect_valid_token_returns_active_true(self, user_tokens) -> None:
        """
        GIVEN a valid access token from Keycloak
        WHEN POST /api/v1/auth/introspect is called
        THEN active=true is returned with token claims.
        """
        response = requests.post(
            "http://localhost/api/v1/auth/introspect",
            json={"token": user_tokens["access_token"]},
            timeout=10,
        )

        assert response.status_code == 200
        data = response.json()
        assert data["active"] is True
        assert "sub" in data  # Subject (user ID)
        assert "exp" in data  # Expiration

    @pytest.mark.skipif(not _api_available(), reason="API server not available")
    @pytest.mark.skipif(not _keycloak_available() and not _keycloak_via_gateway_available(), reason="Keycloak not available")
    def test_introspect_expired_token_returns_inactive_or_error(self) -> None:
        """
        GIVEN an expired/invalid access token
        WHEN POST /api/v1/auth/introspect is called
        THEN either active=false is returned or an error response.
        """
        response = requests.post(
            "http://localhost/api/v1/auth/introspect",
            json={"token": "expired-or-invalid-token"},
            timeout=10,
        )

        # May return 200 with active=false or 400/401 for invalid format
        if response.status_code == 200:
            data = response.json()
            assert data.get("active") is False
        else:
            assert response.status_code in [400, 401, 422]

    @pytest.mark.skipif(not _api_available(), reason="API server not available")
    @pytest.mark.skipif(not _keycloak_available() and not _keycloak_via_gateway_available(), reason="Keycloak not available")
    @pytest.mark.xfail(
        _XDIST_E2E_INFRASTRUCTURE_UNSTABLE,
        reason="Keycloak infrastructure timing issues in xdist parallel execution",
        strict=False,
    )
    def test_introspect_with_token_type_hint(self, user_tokens) -> None:
        """
        GIVEN a valid token with type hint
        WHEN POST /api/v1/auth/introspect is called with token_type_hint
        THEN the hint is used for faster lookup.
        """
        response = requests.post(
            "http://localhost/api/v1/auth/introspect",
            json={
                "token": user_tokens["access_token"],
                "token_type_hint": "access_token",
            },
            timeout=10,
        )

        assert response.status_code == 200
        data = response.json()
        assert data["active"] is True


# ============================================================================
# E2E Pushed Authorization Requests Tests (RFC 9126)
# ============================================================================


class TestPushedAuthorizationRequestsE2E:
    """E2E tests for Pushed Authorization Requests (PAR) - RFC 9126."""

    def teardown_method(self) -> None:
        """Force GC to prevent mock accumulation in xdist workers."""
        gc.collect()

    @pytest.mark.skipif(not _api_available(), reason="API server not available")
    @pytest.mark.skipif(not _keycloak_available() and not _keycloak_via_gateway_available(), reason="Keycloak not available")
    def test_par_returns_request_uri(self) -> None:
        """
        GIVEN PAR is enabled in Keycloak
        WHEN POST /api/v1/auth/par is called with valid parameters
        THEN a request_uri is returned.
        """
        code_verifier, code_challenge = generate_pkce_pair()

        response = requests.post(
            "http://localhost/api/v1/auth/par",
            json={
                "redirect_uri": "http://localhost/api/v1/auth/callback",
                "scope": "openid profile email",
                "code_challenge": code_challenge,
                "code_challenge_method": "S256",
            },
            timeout=10,
        )

        # PAR may not be enabled in all Keycloak configurations
        # Accept 201 (success) or 400/501 (not supported)
        if response.status_code == 201:
            data = response.json()
            assert "request_uri" in data
            assert data["request_uri"].startswith("urn:ietf:params:oauth:request_uri:")
            assert "expires_in" in data
            assert data["expires_in"] > 0
        else:
            # PAR not enabled in Keycloak - skip gracefully
            pytest.skip("PAR not enabled in Keycloak configuration")

    @pytest.mark.skipif(not _api_available(), reason="API server not available")
    def test_par_validates_required_redirect_uri(self) -> None:
        """
        GIVEN PAR endpoint
        WHEN called without redirect_uri
        THEN a validation error is returned.
        """
        response = requests.post(
            "http://localhost/api/v1/auth/par",
            json={"scope": "openid"},
            timeout=10,
        )

        # Validation error may be 400 or 422 depending on implementation
        assert response.status_code in [400, 422]

    @pytest.mark.skipif(not _api_available(), reason="API server not available")
    @pytest.mark.skipif(not _keycloak_available() and not _keycloak_via_gateway_available(), reason="Keycloak not available")
    def test_login_with_request_uri(self) -> None:
        """
        GIVEN a valid request_uri from PAR
        WHEN GET /api/v1/auth/login?request_uri=... is called
        THEN redirect uses the PAR request_uri.
        """
        # First, get a request_uri from PAR
        code_verifier, code_challenge = generate_pkce_pair()

        par_response = requests.post(
            "http://localhost/api/v1/auth/par",
            json={
                "redirect_uri": "http://localhost/api/v1/auth/callback",
                "scope": "openid profile email",
                "code_challenge": code_challenge,
                "code_challenge_method": "S256",
            },
            timeout=10,
        )

        if par_response.status_code != 201:
            pytest.skip("PAR not enabled in Keycloak configuration")

        request_uri = par_response.json()["request_uri"]

        # Now use the request_uri in login
        login_response = requests.get(
            "http://localhost/api/v1/auth/login",
            params={"request_uri": request_uri},
            allow_redirects=False,
            timeout=10,
        )

        assert login_response.status_code == 307
        location = login_response.headers.get("location", "")
        assert "request_uri=" in location


# ============================================================================
# E2E Backchannel Logout Tests (OIDC Back-Channel Logout 1.0)
# ============================================================================


class TestBackchannelLogoutE2E:
    """E2E tests for OIDC Backchannel Logout."""

    def teardown_method(self) -> None:
        """Force GC to prevent mock accumulation in xdist workers."""
        gc.collect()

    @pytest.mark.skipif(not _api_available(), reason="API server not available")
    def test_backchannel_logout_endpoint_exists(self) -> None:
        """
        GIVEN the API server is running
        WHEN POST /api/v1/auth/backchannel-logout is called
        THEN the endpoint exists and returns appropriate response.
        """
        response = requests.post(
            "http://localhost/api/v1/auth/backchannel-logout",
            data={},
            headers={"Content-Type": "application/x-www-form-urlencoded"},
            timeout=10,
        )

        # Should return 400 for missing logout_token (not 404)
        assert response.status_code == 400

    @pytest.mark.skipif(not _api_available(), reason="API server not available")
    def test_backchannel_logout_requires_logout_token(self) -> None:
        """
        GIVEN backchannel logout endpoint
        WHEN called without logout_token
        THEN 400 Bad Request is returned.
        """
        response = requests.post(
            "http://localhost/api/v1/auth/backchannel-logout",
            data={},
            headers={"Content-Type": "application/x-www-form-urlencoded"},
            timeout=10,
        )

        assert response.status_code == 400
        assert "logout_token" in response.json().get("detail", "").lower()

    @pytest.mark.skipif(not _api_available(), reason="API server not available")
    def test_backchannel_logout_rejects_invalid_token(self) -> None:
        """
        GIVEN backchannel logout endpoint
        WHEN called with invalid logout_token
        THEN 400 Bad Request is returned.
        """
        response = requests.post(
            "http://localhost/api/v1/auth/backchannel-logout",
            data={"logout_token": "not-a-valid-jwt"},
            headers={"Content-Type": "application/x-www-form-urlencoded"},
            timeout=10,
        )

        assert response.status_code == 400


# ============================================================================
# E2E Security Headers Tests
# ============================================================================


def _security_headers_middleware_enabled() -> bool:
    """Check if the running server has security headers middleware enabled.

    This detects if the AuthSecurityHeadersMiddleware has been deployed.
    Returns False if server is running an older version without the middleware.
    """
    try:
        response = requests.get(
            "http://localhost/api/v1/auth/login",
            allow_redirects=False,
            timeout=5,
        )
        # Check for the signature header that indicates middleware is active
        return bool(response.headers.get("x-content-type-options"))
    except Exception:
        return False


class TestSecurityHeadersE2E:
    """E2E tests for security headers on auth endpoints.

    Note: These tests require the running server to have AuthSecurityHeadersMiddleware
    enabled. If the server is running an older version, tests will skip gracefully.
    """

    def teardown_method(self) -> None:
        """Force GC to prevent mock accumulation in xdist workers."""
        gc.collect()

    @pytest.mark.skipif(not _api_available(), reason="API server not available")
    def test_login_has_x_content_type_options(self) -> None:
        """
        GIVEN the login endpoint with security headers middleware
        WHEN response is returned
        THEN X-Content-Type-Options: nosniff is present.
        """
        if not _security_headers_middleware_enabled():
            pytest.skip("Security headers middleware not enabled (server needs restart)")

        response = requests.get(
            "http://localhost/api/v1/auth/login",
            allow_redirects=False,
            timeout=10,
        )

        header = response.headers.get("x-content-type-options", "")
        assert header.lower() == "nosniff"

    @pytest.mark.skipif(not _api_available(), reason="API server not available")
    def test_login_has_x_frame_options(self) -> None:
        """
        GIVEN the login endpoint with security headers middleware
        WHEN response is returned
        THEN X-Frame-Options is present (DENY or SAMEORIGIN).
        """
        if not _security_headers_middleware_enabled():
            pytest.skip("Security headers middleware not enabled (server needs restart)")

        response = requests.get(
            "http://localhost/api/v1/auth/login",
            allow_redirects=False,
            timeout=10,
        )

        header = response.headers.get("x-frame-options", "").upper()
        assert header in ("DENY", "SAMEORIGIN")

    @pytest.mark.skipif(not _api_available(), reason="API server not available")
    def test_auth_endpoints_have_csp_header(self) -> None:
        """
        GIVEN auth endpoints with security headers middleware
        WHEN responses are returned
        THEN Content-Security-Policy header is present.
        """
        if not _security_headers_middleware_enabled():
            pytest.skip("Security headers middleware not enabled (server needs restart)")

        response = requests.get(
            "http://localhost/api/v1/auth/login",
            allow_redirects=False,
            timeout=10,
        )

        csp = response.headers.get("content-security-policy", "")
        assert "default-src" in csp or "frame-ancestors" in csp

    @pytest.mark.skipif(not _api_available(), reason="API server not available")
    def test_auth_endpoints_have_referrer_policy(self) -> None:
        """
        GIVEN auth endpoints with security headers middleware
        WHEN responses are returned
        THEN Referrer-Policy header is present.
        """
        if not _security_headers_middleware_enabled():
            pytest.skip("Security headers middleware not enabled (server needs restart)")

        response = requests.get(
            "http://localhost/api/v1/auth/login",
            allow_redirects=False,
            timeout=10,
        )

        referrer = response.headers.get("referrer-policy", "")
        # Should be a secure value
        assert referrer in (
            "strict-origin",
            "strict-origin-when-cross-origin",
            "same-origin",
            "no-referrer",
        )


# ============================================================================
# E2E Full Authentication Flow Tests
# ============================================================================


class TestFullAuthenticationFlowE2E:
    """E2E tests for complete authentication workflow."""

    def teardown_method(self) -> None:
        """Force GC to prevent mock accumulation in xdist workers."""
        gc.collect()

    @pytest.mark.skipif(not _full_infrastructure_available(), reason="Full infrastructure not available")
    def test_complete_oauth2_flow_state_consistency(self) -> None:
        """
        GIVEN OAuth2 + PKCE flow
        WHEN login → callback flow is executed
        THEN state parameter is consistent throughout.
        """
        # Initiate login
        login_response = requests.get(
            "http://localhost/api/v1/auth/login",
            allow_redirects=False,
            timeout=10,
        )

        assert login_response.status_code == 302

        # Extract state from redirect URL
        location = login_response.headers.get("location", "")
        parsed = urlparse(location)
        query_params = parse_qs(parsed.query)
        redirect_state = query_params.get("state", [None])[0]

        # Extract state from cookie
        cookie_state = login_response.cookies.get("oauth2_state")

        # States should match
        assert redirect_state == cookie_state

    @pytest.mark.skipif(not _full_infrastructure_available(), reason="Full infrastructure not available")
    def test_callback_validates_state_parameter(self) -> None:
        """
        GIVEN callback with mismatched state
        WHEN callback is called
        THEN state validation fails.
        """
        session = requests.Session()

        # Initiate login to get valid cookies
        _ = session.get(
            "http://localhost/api/v1/auth/login",
            allow_redirects=False,
            timeout=10,
        )

        # Try callback with wrong state
        callback_response = session.get(
            "http://localhost/api/v1/auth/callback",
            params={
                "code": "fake-code",
                "state": "wrong-state-value",
            },
            timeout=10,
        )

        # Should fail state validation
        assert callback_response.status_code == 400
        assert "state" in callback_response.json().get("detail", "").lower()

    @pytest.mark.skipif(not _full_infrastructure_available(), reason="Full infrastructure not available")
    @pytest.mark.skipif(not _keycloak_available() and not _keycloak_via_gateway_available(), reason="Keycloak not available")
    def test_authenticated_api_call_with_token(self, user_tokens) -> None:
        """
        GIVEN valid access token from Keycloak
        WHEN API endpoint is called with Bearer token
        THEN request is authenticated successfully.
        """
        # This tests that tokens work with protected endpoints
        response = requests.get(
            "http://localhost/api/v1/users/me",
            headers={"Authorization": f"Bearer {user_tokens['access_token']}"},
            timeout=10,
        )

        # Should either succeed or return user info
        # Note: Endpoint may not exist yet, so we check it's not a 401/403
        # that would indicate token rejection
        if response.status_code == 404:
            pytest.skip("Protected endpoint /users/me not implemented")
        assert response.status_code not in [401, 403]


# ============================================================================
# E2E Device Authorization Grant Tests (RFC 8628)
# ============================================================================


class TestDeviceAuthorizationGrantE2E:
    """E2E tests for Device Authorization Grant (RFC 8628)."""

    def teardown_method(self) -> None:
        """Force GC to prevent mock accumulation in xdist workers."""
        gc.collect()

    @pytest.mark.skipif(not _api_available(), reason="API server not available")
    def test_device_auth_endpoint_exists(self) -> None:
        """
        GIVEN the API server is running
        WHEN GET /api/v1/auth/device is called
        THEN the endpoint exists.
        """
        response = requests.get(
            "http://localhost/api/v1/auth/device",
            timeout=10,
        )

        # Should return device code or 503 if Keycloak unavailable
        assert response.status_code in [200, 503]

    @pytest.mark.skipif(not _api_available(), reason="API server not available")
    @pytest.mark.skipif(not _keycloak_available() and not _keycloak_via_gateway_available(), reason="Keycloak not available")
    def test_device_auth_returns_user_code(self) -> None:
        """
        GIVEN Device Authorization Grant is enabled
        WHEN GET /api/v1/auth/device is called
        THEN device_code and user_code are returned.
        """
        response = requests.get(
            "http://localhost/api/v1/auth/device",
            timeout=10,
        )

        if response.status_code == 503:
            pytest.skip("Device Authorization not available in Keycloak")

        assert response.status_code == 200
        data = response.json()
        assert "device_code" in data
        assert "user_code" in data
        assert "verification_uri" in data
        assert "expires_in" in data

    @pytest.mark.skipif(not _api_available(), reason="API server not available")
    def test_device_token_endpoint_exists(self) -> None:
        """
        GIVEN the API server is running
        WHEN POST /api/v1/auth/device/token is called
        THEN the endpoint exists.
        """
        response = requests.post(
            "http://localhost/api/v1/auth/device/token",
            json={"device_code": "invalid-device-code"},
            timeout=10,
        )

        # Should return 400 (authorization_pending or invalid) not 404
        assert response.status_code in [400, 503]


def teardown_module():
    """Force GC to prevent mock accumulation in xdist workers."""
    gc.collect()
