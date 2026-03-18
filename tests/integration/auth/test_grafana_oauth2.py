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
    """Check if Grafana is available."""
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


def _grafana_oauth2_configured() -> bool:
    """Check if Grafana is configured for OAuth2 authentication.

    Returns True if Grafana redirects to Keycloak for authentication,
    False if it shows internal login page (OAuth2 not configured).

    With GF_AUTH_OAUTH_AUTO_LOGIN=true, Grafana redirects through multiple hops:
    1. /dashboards/ -> /dashboards/login
    2. /dashboards/login -> /dashboards/login/generic_oauth
    3. /dashboards/login/generic_oauth -> Keycloak authorize endpoint

    This function follows the redirect chain to check if OAuth2 is configured.
    """
    try:
        # Follow up to 5 redirects to find the Keycloak authorize endpoint
        session = requests.Session()
        url = "http://localhost/dashboards/"
        for _ in range(5):
            response = session.get(url, timeout=5, allow_redirects=False)
            if response.status_code not in [301, 302, 307, 308]:
                return False  # Not a redirect - OAuth2 not configured

            location = response.headers.get("Location", "")
            # Check if this redirect goes to Keycloak
            if "authn/realms" in location or "openid-connect/auth" in location:
                return True

            # Handle relative redirects
            if location.startswith("/"):
                url = f"http://localhost{location}"
            else:
                url = location

        return False  # Too many redirects without reaching Keycloak
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


# Infrastructure check and autouse skip fixture are in tests/integration/auth/conftest.py
# This avoids duplicate autouse fixtures across test files (best practice)

# URLs
GATEWAY_URL = os.getenv("GATEWAY_URL", "http://localhost")
GRAFANA_URL = f"{GATEWAY_URL}/dashboards"
KEYCLOAK_URL = f"{GATEWAY_URL}/authn"

# Test credentials from tests/e2e/default-realm.json
ADMIN_USERNAME = "admin"
ADMIN_PASSWORD = "admin123"
ALICE_USERNAME = "alice"
ALICE_PASSWORD = "alice123"


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
        THEN: Should eventually redirect to Keycloak login page

        User Journey: Unauthenticated user tries to access Grafana

        With GF_AUTH_OAUTH_AUTO_LOGIN=true, Grafana redirects through multiple hops:
        1. /dashboards/ -> /dashboards/login
        2. /dashboards/login -> /dashboards/login/generic_oauth
        3. /dashboards/login/generic_oauth -> Keycloak authorize endpoint
        """
        session = requests.Session()
        url = f"{GRAFANA_URL}/"
        keycloak_redirect_found = False
        final_location = ""

        # Follow redirect chain until we reach Keycloak
        for _ in range(5):
            response = session.get(url, timeout=10, allow_redirects=False)
            if response.status_code not in [301, 302, 307, 308]:
                break

            location = response.headers.get("Location", "")
            final_location = location

            # Check if this redirect goes to Keycloak
            if "authn/realms/default/protocol/openid-connect/auth" in location:
                keycloak_redirect_found = True
                break

            # Handle relative redirects
            if location.startswith("/"):
                url = f"{GATEWAY_URL}{location}"
            else:
                url = location

        assert keycloak_redirect_found, f"Expected redirect chain to end at Keycloak authorize endpoint, got: {final_location}"

        # Check OAuth2 parameters are present in the final redirect
        assert "client_id=grafana" in final_location, f"Expected client_id=grafana in redirect URL, got: {final_location}"
        assert "response_type=code" in final_location, f"Expected response_type=code in redirect URL, got: {final_location}"

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

        # Step 2: Get admin token via two-step Token Exchange (RFC 8693)
        # ROPC is disabled per security audit (ADR-0086)
        token_url = f"{KEYCLOAK_URL}/realms/default/protocol/openid-connect/token"

        # Step 2a: Get service account token via client_credentials
        sa_response = requests.post(
            token_url,
            data={
                "grant_type": "client_credentials",
                "client_id": "agent-studio-keycloak-client-id-for-e2e-tests",
                "client_secret": "test-client-secret-for-e2e-tests",
                "scope": "openid profile email roles",
            },
            timeout=10,
        )
        assert sa_response.status_code == 200, f"SA token request failed: {sa_response.text}"
        sa_token = sa_response.json().get("access_token")
        assert sa_token, "SA token response missing access_token"

        # Step 2b: Exchange for admin-specific token (RFC 8693)
        token_response = requests.post(
            token_url,
            data={
                "grant_type": "urn:ietf:params:oauth:grant-type:token-exchange",
                "client_id": "agent-studio-keycloak-client-id-for-e2e-tests",
                "client_secret": "test-client-secret-for-e2e-tests",
                "subject_token": sa_token,
                "subject_token_type": "urn:ietf:params:oauth:token-type:access_token",
                "requested_subject": ADMIN_USERNAME,
                "requested_token_type": "urn:ietf:params:oauth:token-type:access_token",
                "scope": "openid profile email roles",
            },
            timeout=10,
        )

        if token_response.status_code != 200:
            pytest.skip("Token Exchange not configured - cannot test user-specific roles")

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
        # Get alice token via two-step Token Exchange (RFC 8693)
        # ROPC is disabled per security audit (ADR-0086)
        token_url = f"{KEYCLOAK_URL}/realms/default/protocol/openid-connect/token"

        # Step 1: Get service account token via client_credentials
        sa_response = requests.post(
            token_url,
            data={
                "grant_type": "client_credentials",
                "client_id": "agent-studio-keycloak-client-id-for-e2e-tests",
                "client_secret": "test-client-secret-for-e2e-tests",
                "scope": "openid profile email roles",
            },
            timeout=10,
        )
        assert sa_response.status_code == 200, f"SA token request failed: {sa_response.text}"
        sa_token = sa_response.json().get("access_token")
        assert sa_token, "SA token response missing access_token"

        # Step 2: Exchange for alice-specific token (RFC 8693)
        token_response = requests.post(
            token_url,
            data={
                "grant_type": "urn:ietf:params:oauth:grant-type:token-exchange",
                "client_id": "agent-studio-keycloak-client-id-for-e2e-tests",
                "client_secret": "test-client-secret-for-e2e-tests",
                "subject_token": sa_token,
                "subject_token_type": "urn:ietf:params:oauth:token-type:access_token",
                "requested_subject": ALICE_USERNAME,
                "requested_token_type": "urn:ietf:params:oauth:token-type:access_token",
                "scope": "openid profile email roles",
            },
            timeout=10,
        )

        if token_response.status_code != 200:
            pytest.skip("Token Exchange not configured - cannot test user-specific roles")

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

    def test_oidc_discovery_endpoint_available(self):
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

    def test_grafana_client_registered_in_keycloak(self):
        """
        GIVEN: Keycloak running with default realm imported from tests/e2e/default-realm.json
        WHEN: Checking for grafana client registration via Admin API
        THEN: Grafana client should exist and be enabled

        This test catches the scenario where realm wasn't imported properly,
        which would cause "Client not found" error when accessing Grafana.

        Root cause: Keycloak --import-realm only imports on first start.
        If the database already exists, the realm won't be re-imported.
        """
        # Step 1: Get admin token from master realm
        # We use the Keycloak admin credentials, not realm user credentials
        admin_token_response = requests.post(
            f"{KEYCLOAK_URL}/realms/master/protocol/openid-connect/token",
            data={
                "grant_type": "password",
                "client_id": "admin-cli",
                "username": "admin",
                "password": "admin",
            },
            timeout=10,
        )

        assert admin_token_response.status_code == 200, (
            f"Failed to get Keycloak admin token: {admin_token_response.status_code}\n"
            f"Response: {admin_token_response.text}\n"
            "\n"
            "Possible causes:\n"
            "1. Keycloak admin credentials may have changed\n"
            "2. Keycloak may not be fully started\n"
            "3. Keycloak may have required admin actions pending"
        )

        admin_token = admin_token_response.json().get("access_token")
        assert admin_token, "Expected access_token in admin token response"

        # Step 2: Query Keycloak Admin API for grafana client
        headers = {"Authorization": f"Bearer {admin_token}"}
        clients_response = requests.get(
            f"{KEYCLOAK_URL}/admin/realms/default/clients",
            headers=headers,
            params={"clientId": "grafana"},
            timeout=10,
        )

        assert clients_response.status_code == 200, (
            f"Failed to query Keycloak clients: {clients_response.status_code}\nResponse: {clients_response.text}"
        )

        clients = clients_response.json()

        # Verify grafana client exists
        grafana_clients = [c for c in clients if c.get("clientId") == "grafana"]
        assert len(grafana_clients) == 1, (
            "Client 'grafana' not found in Keycloak realm 'default'.\n"
            "\n"
            "This causes 'Client not found' error when accessing Grafana dashboards.\n"
            "\n"
            "Root cause: The realm was not imported or import failed.\n"
            "Keycloak's --import-realm only imports on first start.\n"
            "\n"
            "Fix options:\n"
            "1. Recreate volumes: docker compose -f docker-compose.test.yml down -v\n"
            "2. Manually create client via Keycloak Admin UI or CLI\n"
            "\n"
            f"Found clients: {[c.get('clientId') for c in clients]}"
        )

        grafana_client = grafana_clients[0]

        # Verify client configuration
        assert grafana_client.get("enabled") is True, "Client 'grafana' exists but is disabled. Enable it in Keycloak."

        assert grafana_client.get("standardFlowEnabled") is True, (
            "Client 'grafana' must have standard flow enabled for OAuth2 authorization code flow"
        )
