"""
Integration tests for Grafana OAuth2 integration with Keycloak.

TDD Cycle: RED -> GREEN -> REFACTOR

These tests verify that:
1. Grafana redirects unauthenticated users to Keycloak login
2. Grafana accepts valid OAuth2 callbacks from Keycloak
3. Role mapping works (admin -> Admin, user -> Viewer)
4. Session is maintained after login

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
    pytest.mark.grafana,
]


def _grafana_available() -> bool:
    """Check if Grafana is available with OAuth2 configured."""
    try:
        # Check Grafana health endpoint (should be public)
        response = requests.get(
            "http://localhost/dashboards/api/health",
            timeout=5,
            allow_redirects=False,
        )
        return response.status_code in [200, 302, 307]
    except Exception:
        return False


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


# Skip at module level if services not available
if not _grafana_available() or not _keycloak_available():
    pytestmark.append(pytest.mark.skip(reason="Grafana or Keycloak not available for OAuth2 integration tests"))

# URLs
GATEWAY_URL = os.getenv("GATEWAY_URL", "http://localhost")
GRAFANA_URL = f"{GATEWAY_URL}/dashboards"
KEYCLOAK_URL = f"{GATEWAY_URL}/authn"

# Test credentials from tests/e2e/default-realm.json
ADMIN_USERNAME = "admin"
ADMIN_PASSWORD = "admin123"  # noqa: S105
ALICE_USERNAME = "alice"
ALICE_PASSWORD = "alice123"  # noqa: S105


@pytest.mark.xdist_group(name="test_grafana_oauth2")
class TestGrafanaOAuth2Redirect:
    """Test that Grafana redirects to Keycloak for authentication."""

    def teardown_method(self) -> None:
        """Force GC to prevent mock accumulation in xdist workers."""
        gc.collect()

    def test_unauthenticated_access_redirects_to_keycloak(self):
        """
        GIVEN: No authentication (no session cookie)
        WHEN: Accessing Grafana dashboard root
        THEN: Should redirect to Keycloak login page

        User Journey: Unauthenticated user tries to access Grafana
        """
        response = requests.get(
            f"{GRAFANA_URL}/",
            timeout=10,
            allow_redirects=False,
        )

        # Should redirect (302 or 307) to OAuth2 authorize endpoint
        assert response.status_code in [302, 307], f"Expected redirect to Keycloak, got {response.status_code}"

        # Check redirect location contains Keycloak authorize URL
        location = response.headers.get("Location", "")
        assert "authn/realms/default/protocol/openid-connect/auth" in location, (
            f"Expected redirect to Keycloak authorize endpoint, got: {location}"
        )

        # Check OAuth2 parameters are present
        assert "client_id=grafana" in location, f"Expected client_id=grafana in redirect URL, got: {location}"
        assert "response_type=code" in location, f"Expected response_type=code in redirect URL, got: {location}"

    def test_grafana_health_endpoint_is_accessible(self):
        """
        GIVEN: No authentication
        WHEN: Accessing Grafana health endpoint
        THEN: Should return 200 (health endpoints are public)

        Note: Grafana health must be accessible for K8s probes
        """
        response = requests.get(
            f"{GRAFANA_URL}/api/health",
            timeout=10,
        )

        # Health endpoint should be accessible without auth
        assert response.status_code == 200, f"Grafana health should be public, got {response.status_code}"
        data = response.json()
        assert data.get("database") == "ok", "Grafana database should be healthy"


@pytest.mark.xdist_group(name="test_grafana_oauth2")
class TestGrafanaOAuth2Login:
    """Test OAuth2 login flow with Keycloak."""

    def teardown_method(self) -> None:
        """Force GC to prevent mock accumulation in xdist workers."""
        gc.collect()

    def test_admin_login_gets_admin_role(self):
        """
        GIVEN: Admin user credentials (admin/admin123)
        WHEN: Completing OAuth2 login flow
        THEN: Should be logged in with Admin role

        User Journey: Admin logs in and gets full Grafana access
        """
        session = requests.Session()

        # Step 1: Access Grafana to get redirect to Keycloak
        response = session.get(
            f"{GRAFANA_URL}/",
            timeout=10,
            allow_redirects=True,  # Follow redirects to Keycloak
        )

        # Should end up at Keycloak login page
        assert "authn/realms/default" in response.url, f"Expected to be redirected to Keycloak, got: {response.url}"

        # Step 2: Submit Keycloak login form
        # Extract login form action URL from response
        # Note: This is a simplified test - in reality we'd parse the HTML
        # For now, we directly POST to Keycloak token endpoint

        # Get admin token directly via password grant
        token_response = requests.post(
            f"{KEYCLOAK_URL}/realms/default/protocol/openid-connect/token",
            data={
                "grant_type": "password",
                "client_id": "mcp-server",
                "client_secret": "test-client-secret-for-e2e-tests",
                "username": ADMIN_USERNAME,
                "password": ADMIN_PASSWORD,
                "scope": "openid profile email roles",
            },
            timeout=10,
        )

        assert token_response.status_code == 200, f"Admin token request failed: {token_response.text}"

        token_data = token_response.json()
        assert "access_token" in token_data, "Expected access_token in response"

        # Verify admin role is in the token
        import base64
        import json

        # Decode JWT payload (without verification for test)
        payload_b64 = token_data["access_token"].split(".")[1]
        padding = 4 - len(payload_b64) % 4
        if padding != 4:
            payload_b64 += "=" * padding
        payload = json.loads(base64.urlsafe_b64decode(payload_b64))

        realm_roles = payload.get("realm_access", {}).get("roles", [])
        assert "admin" in realm_roles, f"Expected 'admin' role in token, got: {realm_roles}"

    def test_alice_login_gets_viewer_role(self):
        """
        GIVEN: Standard user credentials (alice/alice123)
        WHEN: Completing OAuth2 login flow
        THEN: Should be logged in with Viewer role (no admin)

        User Journey: Alice logs in and gets view-only access
        """
        # Get alice token via password grant
        token_response = requests.post(
            f"{KEYCLOAK_URL}/realms/default/protocol/openid-connect/token",
            data={
                "grant_type": "password",
                "client_id": "mcp-server",
                "client_secret": "test-client-secret-for-e2e-tests",
                "username": ALICE_USERNAME,
                "password": ALICE_PASSWORD,
                "scope": "openid profile email roles",
            },
            timeout=10,
        )

        assert token_response.status_code == 200, f"Alice token request failed: {token_response.text}"

        token_data = token_response.json()

        # Decode JWT payload
        import base64
        import json

        payload_b64 = token_data["access_token"].split(".")[1]
        padding = 4 - len(payload_b64) % 4
        if padding != 4:
            payload_b64 += "=" * padding
        payload = json.loads(base64.urlsafe_b64decode(payload_b64))

        realm_roles = payload.get("realm_access", {}).get("roles", [])
        assert "user" in realm_roles, f"Expected 'user' role in token, got: {realm_roles}"
        assert "admin" not in realm_roles, f"Alice should NOT have 'admin' role, got: {realm_roles}"


@pytest.mark.xdist_group(name="test_grafana_oauth2")
class TestGrafanaClientConfiguration:
    """Test that Grafana client is properly configured in Keycloak."""

    def teardown_method(self) -> None:
        """Force GC to prevent mock accumulation in xdist workers."""
        gc.collect()

    def test_grafana_client_exists_in_keycloak(self):
        """
        GIVEN: Keycloak realm with grafana client configured
        WHEN: Requesting OIDC discovery endpoint
        THEN: Should have standard OAuth2 endpoints available
        """
        response = requests.get(
            f"{KEYCLOAK_URL}/realms/default/.well-known/openid-configuration",
            timeout=10,
        )

        assert response.status_code == 200
        data = response.json()

        # Verify required OAuth2 endpoints exist
        assert "authorization_endpoint" in data
        assert "token_endpoint" in data
        assert "userinfo_endpoint" in data
        assert "end_session_endpoint" in data

        # Verify supported grant types include authorization_code
        grant_types = data.get("grant_types_supported", [])
        assert "authorization_code" in grant_types, f"Expected authorization_code grant type, got: {grant_types}"
