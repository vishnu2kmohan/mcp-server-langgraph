"""
Integration Auth Test Configuration and Fixtures

Provides shared autouse fixtures for integration auth tests including:
- OpenFGA availability check
- Keycloak availability check
- Qdrant gateway availability check
- Grafana availability check

These fixtures are centralized here to avoid duplicate autouse fixtures
across test files (best practice per tests/meta/test_fixture_organization.py).
"""

import pytest
import requests


def _openfga_available() -> bool:
    """Check if OpenFGA is available AND accessible with pre-shared key auth.

    This validates:
    1. OpenFGA server is running (healthz endpoint)
    2. Pre-shared key authentication works (stores endpoint)

    If OIDC is enabled and pre-shared key is disabled, tests using pre-shared key
    auth should skip gracefully.
    """
    import os

    try:
        # Check 1: Server is running
        response = requests.get(
            "http://localhost:9080/healthz",
            timeout=5,
        )
        if response.status_code != 200:
            return False

        # Check 2: Pre-shared key auth works
        # Tests in test_openfga_seeding_flow.py use pre-shared key auth
        # If OIDC is enabled and pre-shared key is disabled, skip these tests
        preshared_key = os.getenv("OPENFGA_PRESHARED_KEY", "test-openfga-preshared-key")
        stores_response = requests.get(
            "http://localhost:9080/stores",
            headers={
                "Authorization": f"Bearer {preshared_key}",
                "Content-Type": "application/json",
            },
            timeout=5,
        )
        # Accept 200 (success) or 401 (pre-shared key disabled/OIDC mode)
        if stores_response.status_code == 401:
            # Pre-shared key auth not working (likely OIDC mode)
            return False

        return stores_response.status_code == 200
    except Exception:
        return False


def _keycloak_available() -> bool:
    """Check if Keycloak is available via gateway."""
    try:
        response = requests.get(
            "http://localhost/authn/realms/default/.well-known/openid-configuration",
            timeout=5,
        )
        return response.status_code == 200
    except Exception:
        return False


def _qdrant_available() -> bool:
    """Check if Qdrant is available via Traefik gateway."""
    try:
        response = requests.get(
            "http://localhost/vectors/",
            timeout=5,
            allow_redirects=False,
        )
        # Could be 200, 401, 403, or 307 depending on auth config
        return response.status_code in [200, 401, 403, 307]
    except Exception:
        return False


def _qdrant_auth_configured() -> bool:
    """Check if Qdrant gateway has auth configured (forward-auth middleware).

    This verifies that accessing Qdrant without auth returns 302/307/401/403,
    not 200. Tests that verify auth behavior should skip if auth isn't configured.

    Returns:
        True if gateway responds with auth challenge (302/307/401/403)
        False if gateway returns 200 (no auth) or is unreachable
    """
    try:
        response = requests.get(
            "http://localhost/vectors/",
            timeout=5,
            allow_redirects=False,
        )
        # ONLY accept auth responses - if 200, auth isn't configured
        return response.status_code in [302, 307, 401, 403]
    except Exception:
        return False


def _grafana_available() -> bool:
    """Check if Grafana is available."""
    try:
        response = requests.get(
            "http://localhost/dashboards/api/health",
            timeout=5,
            allow_redirects=False,
        )
        return response.status_code in [200, 302, 307]
    except Exception:
        return False


def _grafana_oauth2_configured() -> bool:
    """Check if Grafana is configured for OAuth2 authentication."""
    try:
        session = requests.Session()
        url = "http://localhost/dashboards/"
        for _ in range(5):
            response = session.get(url, timeout=5, allow_redirects=False)
            if response.status_code not in [301, 302, 307, 308]:
                return False

            location = response.headers.get("Location", "")
            if "authn/realms" in location or "openid-connect/auth" in location:
                return True

            if location.startswith("/"):
                url = f"http://localhost{location}"
            else:
                url = location

        return False
    except Exception:
        return False


def get_service_account_token(
    token_url: str = "http://localhost/authn/realms/default/protocol/openid-connect/token",
    client_id: str = "mcp-server",
    client_secret: str = "test-client-secret-for-e2e-tests",
) -> str | None:
    """
    Get a service account token using client credentials grant.

    This is the RFC 9700 compliant way to get tokens for service-to-service auth.
    Use this for tests that need authentication but not a specific user identity.

    Args:
        token_url: Keycloak token endpoint URL
        client_id: OAuth2 client ID with serviceAccountsEnabled=true
        client_secret: OAuth2 client secret

    Returns:
        Access token string or None if request fails
    """
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
            return response.json().get("access_token")
    except Exception:
        pass
    return None


def _get_test_token_via_modern_auth() -> str | None:
    """
    Get a test token using modern auth methods (RFC 9700 compliant).

    Tries:
    1. Token exchange (RFC 8693) - impersonate admin user
    2. Client credentials - service account token

    Note: ROPC (password grant) is disabled per security audit (ADR-0068).
    Tests requiring user-specific tokens should use Token Exchange or mock auth.

    Returns:
        Access token string or None if all methods fail
    """
    token_url = "http://localhost/authn/realms/default/protocol/openid-connect/token"
    client_id = "mcp-server"
    client_secret = "test-client-secret-for-e2e-tests"

    # Try 1: Token exchange (RFC 8693) for user-specific token
    try:
        response = requests.post(
            token_url,
            data={
                "grant_type": "urn:ietf:params:oauth:grant-type:token-exchange",
                "client_id": client_id,
                "client_secret": client_secret,
                "requested_subject": "admin",
                "subject_token_type": "urn:ietf:params:oauth:token-type:access_token",
                "requested_token_type": "urn:ietf:params:oauth:token-type:access_token",
                "scope": "openid profile email",
            },
            timeout=10,
        )
        if response.status_code == 200:
            token = response.json().get("access_token")
            if token:
                return token
    except Exception:
        pass

    # Try 2: Client credentials (service account) - always works with ROPC disabled
    return get_service_account_token(token_url, client_id, client_secret)


def _keycloak_token_endpoint_functional() -> bool:
    """Check if Keycloak token endpoint returns valid JSON."""
    try:
        response = requests.post(
            "http://localhost/authn/realms/default/protocol/openid-connect/token",
            data={"grant_type": "client_credentials"},
            timeout=5,
        )
        # Even an error response should be valid JSON
        response.json()
        return True
    except Exception:
        return False


def _keycloak_admin_api_available() -> bool:
    """Check if Keycloak admin API is accessible with default credentials.

    This validates that:
    1. Keycloak master realm is accessible
    2. Admin credentials (admin/admin) are valid
    3. Admin API can be queried

    Tests that require admin API access should be skipped if this returns False.

    Note: Uses ROPC for admin-cli (Keycloak's standard pattern for admin access).
    The admin-cli client is a public client in the master realm that is specifically
    designed for ROPC-based admin tooling (e.g., kcadm.sh). This is Keycloak's
    official approach and is acceptable here, though production admin access
    should use client credentials with a dedicated service account.

    Reference: https://www.keycloak.org/docs/latest/server_admin/#admin-cli
    """
    try:
        # Get admin token from master realm using admin-cli (Keycloak's standard pattern)
        token_response = requests.post(
            "http://localhost/authn/realms/master/protocol/openid-connect/token",
            data={
                "grant_type": "password",
                "client_id": "admin-cli",
                "username": "admin",
                "password": "admin",
            },
            timeout=5,
        )
        if token_response.status_code != 200:
            return False

        # Verify we got a valid token
        token_data = token_response.json()
        return "access_token" in token_data
    except Exception:
        return False


def get_user_token(
    username: str,
    password: str | None = None,  # Deprecated: ROPC is disabled
    token_url: str = "http://localhost/authn/realms/default/protocol/openid-connect/token",
    client_id: str = "mcp-server",
    client_secret: str = "test-client-secret-for-e2e-tests",
) -> str | None:
    """
    Get a user-specific access token using Token Exchange (RFC 8693).

    This is a reusable helper for integration tests that need user tokens.
    Uses Token Exchange to impersonate the specified user.

    Note: ROPC (password grant) is disabled per security audit.
    If Token Exchange is not configured, this returns None.
    For tests that just need authentication (not a specific user),
    use get_service_account_token() instead.

    Args:
        username: Username to get token for via Token Exchange
        password: Deprecated - ignored (ROPC is disabled)
        token_url: Keycloak token endpoint URL
        client_id: OAuth2 client ID
        client_secret: OAuth2 client secret

    Returns:
        Access token string or None if Token Exchange fails
    """
    # Token exchange (RFC 8693) for user-specific token
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
            token = response.json().get("access_token")
            if token:
                return token
    except Exception:
        pass

    # Fallback: Return service account token if Token Exchange not configured
    # Tests should use get_service_account_token() directly if user identity
    # is not required
    return get_service_account_token(token_url, client_id, client_secret)


# User credentials mapping for quick lookups
# Note: ROPC is disabled per security audit. These are kept for Token Exchange
# subject lookup and test documentation. Do not use for grant_type=password.
USER_CREDENTIALS = {
    "admin": "admin123",  # Subject for Token Exchange
    "alice": "alice123",  # Subject for Token Exchange
    "bob": "bob123",  # Subject for Token Exchange
}


@pytest.fixture
def service_account_token() -> str | None:
    """Fixture providing a service account token for tests.

    Use this for tests that need authentication but not a specific user identity.
    This is the RFC 9700 compliant way to get tokens.

    Returns:
        Access token string or None if Keycloak is unavailable
    """
    return get_service_account_token()


@pytest.fixture(autouse=True)
def skip_if_openfga_unavailable(request):
    """Skip OpenFGA-dependent tests if OpenFGA is not available.

    Only applies to tests in files that need OpenFGA. Uses request.fspath
    to determine which tests need this check.
    """
    # Files that require OpenFGA
    openfga_files = [
        "test_openfga_preshared_key.py",
        "test_openfga_seeding_flow.py",
        "test_unified_api_authorization.py",
        "test_sub_persona_authorization.py",
        "test_project_authorization.py",
        "test_connection_authorization.py",
        "test_chat_authorization.py",
        "test_observability_authorization.py",
    ]

    test_file = request.fspath.basename if hasattr(request.fspath, "basename") else str(request.fspath).split("/")[-1]

    if test_file in openfga_files:
        if not _openfga_available():
            pytest.skip("OpenFGA not available at localhost:9080")


@pytest.fixture(autouse=True)
def skip_if_infrastructure_unavailable(request):
    """Skip tests if required infrastructure is not available.

    Checks specific infrastructure based on the test file:
    - test_qdrant_auth.py: Qdrant gateway + Keycloak
    - test_grafana_oauth2.py: Grafana + Keycloak + OAuth2 config
    - test_openfga_playground_proxy.py: Keycloak
    """
    test_file = request.fspath.basename if hasattr(request.fspath, "basename") else str(request.fspath).split("/")[-1]

    if test_file == "test_qdrant_auth.py":
        if not _qdrant_available():
            pytest.skip("Qdrant gateway not available at localhost:80/vectors")
        if not _keycloak_available():
            pytest.skip("Keycloak not available at localhost:80/authn")
        if not _keycloak_token_endpoint_functional():
            pytest.skip("Keycloak token endpoint not returning valid JSON responses")
        if not _qdrant_auth_configured():
            pytest.skip(
                "Qdrant gateway auth not configured (got 200 instead of 302/307/401/403). "
                "Tests in test_qdrant_auth.py verify that auth is required - "
                "they should skip when forward-auth middleware is not configured."
            )

    elif test_file == "test_grafana_oauth2.py":
        if not _grafana_available():
            pytest.skip("Grafana not available at localhost:80/dashboards")
        if not _keycloak_available():
            pytest.skip("Keycloak not available at localhost:80/authn")
        if not _grafana_oauth2_configured():
            pytest.skip("Grafana OAuth2 not configured (ADR-0068 infrastructure pending)")

    # NOTE: test_openfga_playground_proxy.py removed in Phase 4 decommission


@pytest.fixture(autouse=True)
def skip_if_keycloak_admin_unavailable(request):
    """Skip tests requiring Keycloak admin API if admin credentials are invalid.

    Checks for 'keycloak_admin' pytest marker on test functions/classes.
    Tests with this marker require valid admin/admin credentials on master realm.

    Also applies to specific test functions that are known to require admin API:
    - test_grafana_client_registered_in_keycloak
    """
    test_name = request.node.name if hasattr(request.node, "name") else ""

    # Check if test requires admin API
    needs_admin = (
        request.node.get_closest_marker("keycloak_admin") is not None
        or "test_grafana_client_registered_in_keycloak" in test_name
    )

    if needs_admin and not _keycloak_admin_api_available():
        pytest.skip(
            "Keycloak admin API not available (admin/admin credentials invalid). "
            "This test requires Keycloak master realm admin access."
        )
