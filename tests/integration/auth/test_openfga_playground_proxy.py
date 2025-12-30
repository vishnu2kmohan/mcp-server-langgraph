"""
Integration tests for OpenFGA Playground Auth Proxy.

TDD Cycle: RED -> GREEN -> REFACTOR

These tests verify that:
1. Unauthenticated requests to /playground are rejected
2. Authenticated users without admin permission are denied
3. Authenticated admins can access the playground

Reference: ADR-0068 - Gateway-Level Authentication (native OAuth2)
"""

import gc
import os

import pytest
import requests

# Mark as integration test requiring docker infrastructure
pytestmark = [
    pytest.mark.integration,
    pytest.mark.auth,
    pytest.mark.openfga,
]


def _keycloak_available() -> bool:
    """Check if Keycloak is available."""
    try:
        response = requests.get(
            "http://localhost/authn/realms/default/.well-known/openid-configuration",
            timeout=5,
        )
        return response.status_code == 200
    except Exception:
        return False


def _authz_proxy_available() -> bool:
    """Check if authz-proxy is available."""
    try:
        response = requests.get(
            "http://localhost/playground/health",
            timeout=5,
            allow_redirects=False,
        )
        # Should return 401 (no auth) or 200 (if health is public)
        return response.status_code in [200, 401, 403]
    except Exception:
        return False


# Infrastructure check and autouse skip fixture are in tests/integration/auth/conftest.py
# This avoids duplicate autouse fixtures across test files (best practice)

# URLs
GATEWAY_URL = os.getenv("GATEWAY_URL", "http://localhost")
KEYCLOAK_URL = f"{GATEWAY_URL}/authn"
PLAYGROUND_URL = f"{GATEWAY_URL}/playground"

# Test credentials from tests/e2e/default-realm.json
ADMIN_USERNAME = "admin"
ADMIN_PASSWORD = "admin123"  # noqa: S105
ALICE_USERNAME = "alice"
ALICE_PASSWORD = "alice123"  # noqa: S105


def get_keycloak_token(username: str, password: str = "") -> str | None:
    """Get a JWT token from Keycloak for testing.

    Uses Token Exchange (RFC 8693) or client_credentials grant.
    ROPC (password grant) is disabled per security audit (ADR-0086).
    """
    token_url = f"{KEYCLOAK_URL}/realms/default/protocol/openid-connect/token"

    # Try Token Exchange first (RFC 8693) for user-specific context
    try:
        response = requests.post(
            token_url,
            data={
                "grant_type": "urn:ietf:params:oauth:grant-type:token-exchange",
                "client_id": "mcp-server",
                "client_secret": "test-client-secret-for-e2e-tests",
                "requested_subject": username,
                "subject_token_type": "urn:ietf:params:oauth:token-type:access_token",
                "requested_token_type": "urn:ietf:params:oauth:token-type:access_token",
                "scope": "openid profile email",
            },
            timeout=10,
        )
        if response.status_code == 200:
            return response.json().get("access_token")
    except Exception:
        pass

    # Fallback to client_credentials (service account)
    try:
        response = requests.post(
            token_url,
            data={
                "grant_type": "client_credentials",
                "client_id": "mcp-server",
                "client_secret": "test-client-secret-for-e2e-tests",
                "scope": "openid profile email",
            },
            timeout=10,
        )
        if response.status_code == 200:
            return response.json().get("access_token")
    except Exception:
        pass
    return None


@pytest.mark.xdist_group(name="test_openfga_playground_proxy")
class TestOpenFGAPlaygroundAccess:
    """Test OpenFGA Playground access control."""

    def teardown_method(self) -> None:
        """Force GC to prevent mock accumulation in xdist workers."""
        gc.collect()

    def test_unauthenticated_access_is_rejected(self):
        """
        GIVEN: No authentication
        WHEN: Accessing OpenFGA Playground
        THEN: Should return 401 Unauthorized

        User Journey: Unauthenticated user is blocked
        """
        response = requests.get(
            f"{PLAYGROUND_URL}/",
            timeout=10,
            allow_redirects=False,
        )

        # Should reject unauthenticated requests
        assert response.status_code == 401, f"Expected 401 Unauthorized without auth, got {response.status_code}"

    def test_alice_without_admin_permission_is_denied(self):
        """
        GIVEN: Alice is authenticated but does not have admin permission on authz:playground
        WHEN: Accessing OpenFGA Playground
        THEN: Should return 403 Forbidden

        User Journey: Regular user cannot access admin-only playground
        """
        token = get_keycloak_token(ALICE_USERNAME, ALICE_PASSWORD)
        assert token is not None, "Failed to get token for alice"

        response = requests.get(
            f"{PLAYGROUND_URL}/",
            headers={"Authorization": f"Bearer {token}"},
            timeout=10,
            allow_redirects=False,
        )

        # Alice should be denied (403) - authenticated but not authorized
        assert response.status_code == 403, f"Expected 403 Forbidden for alice, got {response.status_code}"

    def test_admin_with_permission_can_access(self):
        """
        GIVEN: Admin is authenticated and has admin permission on authz:playground
        WHEN: Accessing OpenFGA Playground
        THEN: Should return 200 OK (or proxy the request)

        User Journey: Admin can access the playground
        """
        token = get_keycloak_token(ADMIN_USERNAME, ADMIN_PASSWORD)
        assert token is not None, "Failed to get token for admin"

        response = requests.get(
            f"{PLAYGROUND_URL}/",
            headers={"Authorization": f"Bearer {token}"},
            timeout=10,
            allow_redirects=False,
        )

        # Admin should be allowed - the request should be proxied to the OpenFGA backend.
        # Accepted responses:
        # - 200: Direct content served
        # - 302/307: Redirect from playground
        # - 404: Backend doesn't have "/" route (but proves auth/authz passed and proxy worked)
        # Any of these proves authorization succeeded; 401/403 would indicate failure.
        assert response.status_code in [200, 302, 307, 404], f"Expected 200/302/307/404 for admin, got {response.status_code}"
        # Explicitly verify we didn't get auth/authz errors
        assert response.status_code not in [401, 403], f"Admin should not get auth error, got {response.status_code}"


@pytest.mark.xdist_group(name="test_openfga_playground_proxy")
class TestOpenFGAPlaygroundHealthEndpoint:
    """Test OpenFGA Playground proxy health endpoint."""

    def teardown_method(self) -> None:
        """Force GC to prevent mock accumulation in xdist workers."""
        gc.collect()

    def test_proxy_health_endpoint_is_public(self):
        """
        GIVEN: No authentication
        WHEN: Accessing authz-proxy health endpoint
        THEN: Should return 200 OK (health is public for K8s probes)

        Note: The health endpoint is at /api/authz-proxy/health within the proxy.
        Via gateway, it's accessed at /playground/api/authz-proxy/health
        (Traefik strips /playground prefix before forwarding to proxy).
        """
        response = requests.get(
            f"{PLAYGROUND_URL}/api/authz-proxy/health",
            timeout=10,
        )

        # Health endpoint should be accessible without auth
        # Note: This tests the proxy's own health, not the playground
        assert response.status_code == 200, f"Authz proxy health should be public, got {response.status_code}"
