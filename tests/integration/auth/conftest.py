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


def _get_test_token_via_modern_auth() -> str | None:
    """
    Get a test token using modern auth methods (RFC 9700 compliant).

    Tries:
    1. Token exchange (RFC 8693) - impersonate admin user
    2. Client credentials - service account token
    3. ROPC (deprecated) - fallback for backward compatibility

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

    # Try 2: Client credentials (service account)
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
            token = response.json().get("access_token")
            if token:
                return token
    except Exception:
        pass

    # Try 3: ROPC fallback (deprecated per RFC 9700)
    try:
        response = requests.post(
            token_url,
            data={
                "grant_type": "password",
                "client_id": client_id,
                "client_secret": client_secret,
                "username": "admin",
                "password": "admin123",
                "scope": "openid profile email",
            },
            timeout=10,
        )
        if response.status_code == 200:
            return response.json().get("access_token")
    except Exception:
        pass

    return None


def _authz_proxy_available() -> bool:
    """Check if authz-proxy service is reachable.

    This only checks if the service is up and responding to HTTP requests.
    It does NOT check if authentication/authorization is configured correctly.

    Philosophy: If infrastructure is up (via make test-infra-up), tests should
    RUN and potentially FAIL if misconfigured - not SKIP. Skipping should only
    happen when the service is completely unreachable (connection refused).

    Returns:
        True if service is reachable (any HTTP response)
        False only if connection fails entirely (service not running)
    """
    try:
        response = requests.get(
            "http://localhost/playground/",
            timeout=5,
            allow_redirects=False,
        )
        # Any HTTP response means the service is up - test should run
        # The test itself will verify correct behavior (401/403/200)
        return response.status_code > 0  # Any valid HTTP status
    except requests.exceptions.ConnectionError:
        # Service not running - skip is appropriate
        return False
    except requests.exceptions.Timeout:
        # Service not responding in time - skip is appropriate
        return False
    except Exception:
        # Other network errors - skip is appropriate
        return False


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
    password: str | None = None,
    token_url: str = "http://localhost/authn/realms/default/protocol/openid-connect/token",
    client_id: str = "mcp-server",
    client_secret: str = "test-client-secret-for-e2e-tests",
) -> str | None:
    """
    Get a user-specific access token using modern auth methods (RFC 9700 compliant).

    This is a reusable helper for integration tests that need user tokens.

    Tries:
    1. Token exchange (RFC 8693) - no password needed
    2. ROPC (deprecated) - fallback if token exchange not configured

    Args:
        username: Username to get token for
        password: User's password (only used for ROPC fallback)
        token_url: Keycloak token endpoint URL
        client_id: OAuth2 client ID
        client_secret: OAuth2 client secret

    Returns:
        Access token string or None if all methods fail
    """
    # Try 1: Token exchange (RFC 8693) for user-specific token
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

    # Try 2: ROPC fallback (deprecated per RFC 9700)
    if password:
        try:
            response = requests.post(
                token_url,
                data={
                    "grant_type": "password",
                    "client_id": client_id,
                    "client_secret": client_secret,
                    "username": username,
                    "password": password,
                    "scope": "openid profile email",
                },
                timeout=10,
            )
            if response.status_code == 200:
                return response.json().get("access_token")
        except Exception:
            pass

    return None


# User credentials mapping for quick lookups
USER_CREDENTIALS = {
    "admin": "admin123",
    "alice": "alice123",
    "bob": "bob123",
}


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

    elif test_file == "test_grafana_oauth2.py":
        if not _grafana_available():
            pytest.skip("Grafana not available at localhost:80/dashboards")
        if not _keycloak_available():
            pytest.skip("Keycloak not available at localhost:80/authn")
        if not _grafana_oauth2_configured():
            pytest.skip("Grafana OAuth2 not configured (ADR-0068 infrastructure pending)")

    elif test_file == "test_openfga_playground_proxy.py":
        if not _keycloak_available():
            pytest.skip("Keycloak not available at localhost:80/authn")
        if not _authz_proxy_available():
            pytest.skip("Authz-proxy/playground not available at localhost:80/playground")


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
