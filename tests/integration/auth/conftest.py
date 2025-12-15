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
    """Check if OpenFGA is available."""
    try:
        response = requests.get(
            "http://localhost:9080/healthz",
            timeout=5,
        )
        return response.status_code == 200
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
    """
    try:
        # Get admin token from master realm
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
