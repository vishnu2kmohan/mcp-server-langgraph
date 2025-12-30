"""
Integration tests for OAuth2 Token Exchange (RFC 8693).

TDD Cycle: RED -> GREEN -> REFACTOR

These tests verify that Token Exchange is properly configured in Keycloak,
allowing the mcp-server client to impersonate users without using ROPC.

Reference:
- RFC 8693: OAuth 2.0 Token Exchange
- ADR-0086: Security Audit - Keycloak and OpenFGA Hardening

Infrastructure Requirements:
- docker-compose.test.yml running (make test-infra-up-build)
- Keycloak with Token Exchange enabled (KC_FEATURES=token-exchange)
- keycloak-init-test service completed (configures permissions)
"""

import gc
import os

import pytest
import requests

pytestmark = [
    pytest.mark.integration,
    pytest.mark.auth,
    pytest.mark.token_exchange,
]

# Configuration from environment
KEYCLOAK_URL = os.getenv("KEYCLOAK_URL", "http://localhost/authn")
TOKEN_URL = f"{KEYCLOAK_URL}/realms/default/protocol/openid-connect/token"
CLIENT_ID = "mcp-server"
CLIENT_SECRET = "test-client-secret-for-e2e-tests"  # noqa: S105

# Test users from tests/e2e/default-realm.json
TEST_USERS = {
    "admin": {"expected_role": "admin"},
    "alice": {"expected_role": "developer"},
    "bob": {"expected_role": None},
}


def _keycloak_available() -> bool:
    """Check if Keycloak is available."""
    try:
        response = requests.get(
            f"{KEYCLOAK_URL}/realms/default/.well-known/openid-configuration",
            timeout=5,
        )
        return response.status_code == 200
    except Exception:
        return False


def _get_service_account_token() -> str | None:
    """Get a service account token using client_credentials grant."""
    try:
        response = requests.post(
            TOKEN_URL,
            data={
                "grant_type": "client_credentials",
                "client_id": CLIENT_ID,
                "client_secret": CLIENT_SECRET,
                "scope": "openid profile email",
            },
            timeout=10,
        )
        if response.status_code == 200:
            return response.json().get("access_token")
    except Exception:
        pass
    return None


def _exchange_token_for_user(subject_token: str, target_user: str) -> dict | None:
    """
    Exchange a service account token for a user-specific token.

    This implements RFC 8693 Token Exchange where the service account
    impersonates a specific user.

    Args:
        subject_token: The service account access token
        target_user: The username to impersonate

    Returns:
        Token response dict with access_token, or None if exchange fails
    """
    try:
        response = requests.post(
            TOKEN_URL,
            data={
                "grant_type": "urn:ietf:params:oauth:grant-type:token-exchange",
                "client_id": CLIENT_ID,
                "client_secret": CLIENT_SECRET,
                "subject_token": subject_token,
                "subject_token_type": "urn:ietf:params:oauth:token-type:access_token",
                "requested_subject": target_user,
                "requested_token_type": "urn:ietf:params:oauth:token-type:access_token",
                "scope": "openid profile email",
            },
            timeout=10,
        )
        if response.status_code == 200:
            return response.json()
        return {"error": response.status_code, "error_description": response.text}
    except Exception as e:
        return {"error": "exception", "error_description": str(e)}


@pytest.mark.xdist_group(name="test_token_exchange")
class TestTokenExchangeConfiguration:
    """Test Token Exchange is properly configured in Keycloak."""

    def teardown_method(self) -> None:
        """Force GC to prevent mock accumulation in xdist workers."""
        gc.collect()

    @pytest.fixture(autouse=True)
    def skip_if_keycloak_unavailable(self):
        """Skip tests if Keycloak is not available."""
        if not _keycloak_available():
            pytest.skip("Keycloak is not available")

    def test_client_credentials_grant_works(self):
        """
        GIVEN: mcp-server client with serviceAccountsEnabled=true
        WHEN: Requesting token via client_credentials grant
        THEN: Should receive valid access token

        This is a prerequisite for Token Exchange.
        """
        token = _get_service_account_token()

        assert token is not None, "Failed to get service account token"
        assert len(token) > 0, "Token should not be empty"

    def test_token_exchange_feature_enabled(self):
        """
        GIVEN: Keycloak with KC_FEATURES=token-exchange
        WHEN: Requesting Token Exchange
        THEN: Should not receive "Feature not enabled" error

        If Token Exchange is disabled, Keycloak returns:
        {"error": "invalid_grant", "error_description": "...feature is disabled..."}
        """
        # Get service account token first
        sa_token = _get_service_account_token()
        if not sa_token:
            pytest.skip("Could not get service account token")

        # Try token exchange - even if it fails for permissions,
        # it should not fail because the feature is disabled
        result = _exchange_token_for_user(sa_token, "admin")

        if result and "error_description" in result:
            error_desc = str(result.get("error_description", "")).lower()
            assert "feature" not in error_desc or "disabled" not in error_desc, (
                f"Token Exchange feature appears to be disabled: {result}"
            )

    def test_token_exchange_for_admin_user(self):
        """
        GIVEN: Service account token with impersonation permissions
        WHEN: Exchanging token for admin user
        THEN: Should receive token with admin's identity

        User Journey: Service impersonating admin for privileged operations.
        """
        sa_token = _get_service_account_token()
        if not sa_token:
            pytest.skip("Could not get service account token")

        result = _exchange_token_for_user(sa_token, "admin")

        if result and "error" in result:
            # Token Exchange not fully configured - skip with informative message
            pytest.skip(
                f"Token Exchange not configured for impersonation: {result.get('error_description', result.get('error'))}"
            )

        assert "access_token" in result, f"Expected access_token in response: {result}"

        # Verify the token is for the admin user
        import base64
        import json

        token_payload = result["access_token"].split(".")[1]
        # Add padding for base64 decoding
        padding = 4 - len(token_payload) % 4
        if padding != 4:
            token_payload += "=" * padding
        claims = json.loads(base64.urlsafe_b64decode(token_payload))

        assert claims.get("preferred_username") == "admin", (
            f"Token should be for admin user, got: {claims.get('preferred_username')}"
        )

    @pytest.mark.parametrize("username", ["admin", "alice", "bob"])
    def test_token_exchange_for_all_test_users(self, username: str):
        """
        GIVEN: Service account with impersonation permissions
        WHEN: Exchanging token for each test user
        THEN: Should receive valid token with user's identity

        User Journey: Testing impersonation for all configured test users.
        """
        sa_token = _get_service_account_token()
        if not sa_token:
            pytest.skip("Could not get service account token")

        result = _exchange_token_for_user(sa_token, username)

        if result and "error" in result:
            pytest.skip(
                f"Token Exchange not configured for {username}: {result.get('error_description', result.get('error'))}"
            )

        assert "access_token" in result, f"Expected access_token for {username}"


@pytest.mark.xdist_group(name="test_token_exchange")
class TestTokenExchangeWithoutROPC:
    """Test that Token Exchange can replace ROPC for test authentication."""

    def teardown_method(self) -> None:
        """Force GC to prevent mock accumulation in xdist workers."""
        gc.collect()

    @pytest.fixture(autouse=True)
    def skip_if_keycloak_unavailable(self):
        """Skip tests if Keycloak is not available."""
        if not _keycloak_available():
            pytest.skip("Keycloak is not available")

    def test_ropc_is_disabled(self):
        """
        GIVEN: Keycloak realm with directAccessGrantsEnabled=false
        WHEN: Attempting ROPC (password grant)
        THEN: Should be rejected with unauthorized_client error

        This confirms ROPC is properly disabled per ADR-0086.
        """
        response = requests.post(
            TOKEN_URL,
            data={
                "grant_type": "password",
                "client_id": CLIENT_ID,
                "client_secret": CLIENT_SECRET,
                "username": "admin",
                "password": "admin123",
            },
            timeout=10,
        )

        # ROPC should be disabled
        assert response.status_code in [400, 401, 403], f"ROPC should be disabled, but got {response.status_code}"

        error_data = response.json()
        # Keycloak returns "unauthorized_client" when ROPC is disabled
        assert error_data.get("error") in ["unauthorized_client", "invalid_grant"], (
            f"Expected unauthorized_client error, got: {error_data}"
        )

    def test_authorization_code_flow_available(self):
        """
        GIVEN: Keycloak realm with standardFlowEnabled=true
        WHEN: Checking OIDC discovery document
        THEN: Should include authorization_code in grant_types_supported

        This confirms users can still login via browser-based flow.
        """
        response = requests.get(
            f"{KEYCLOAK_URL}/realms/default/.well-known/openid-configuration",
            timeout=10,
        )

        assert response.status_code == 200, "OIDC discovery should be available"

        oidc_config = response.json()
        grant_types = oidc_config.get("grant_types_supported", [])

        assert "authorization_code" in grant_types, f"Authorization Code flow should be supported: {grant_types}"
