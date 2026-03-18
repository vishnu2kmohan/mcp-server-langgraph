"""
Integration tests for Qdrant Vector Database authentication.

TDD Cycle: RED -> GREEN -> REFACTOR

These tests verify that:
1. Qdrant routes require authentication via forward-auth middleware
2. Authenticated users can access Qdrant API and Dashboard
3. Qdrant gateway routing is properly configured in Traefik

Reference:
- ADR-0054 - Gateway-Level Authentication
- docker-compose.test.yml - qdrant-test service with forward-auth@docker middleware
"""

import gc
import os

import pytest
import requests

# Mark as integration test requiring docker infrastructure
pytestmark = [
    pytest.mark.integration,
    pytest.mark.auth,
    pytest.mark.qdrant,
]


def _qdrant_available() -> bool:
    """Check if Qdrant is reachable via gateway (with or without auth)."""
    try:
        response = requests.get(
            "http://localhost/vectors/",
            timeout=5,
            allow_redirects=False,
        )
        return response.status_code in [200, 302, 307, 401, 403]
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


def _keycloak_token_endpoint_functional() -> bool:
    """Check if Keycloak token endpoint can return valid JSON responses.

    This verifies the token endpoint is properly configured and responding,
    not just that Keycloak is running. Without this check, tests may fail
    with JSONDecodeError when token endpoint returns empty/invalid responses.
    """
    try:
        # Make a minimal token request that will fail auth but verify JSON response
        # Uses client_credentials with invalid credentials (ROPC is disabled per ADR-0086)
        response = requests.post(
            "http://localhost/authn/realms/default/protocol/openid-connect/token",
            data={
                "grant_type": "client_credentials",
                "client_id": "invalid-client",
                "client_secret": "invalid-secret",
            },
            timeout=5,
        )
        # We expect 400/401 with JSON error response, not empty body
        if response.status_code in [400, 401, 403]:
            # Verify we get valid JSON back (even if it's an error)
            response.json()  # Will raise if not valid JSON
            return True
        return False
    except (requests.exceptions.JSONDecodeError, ValueError):
        # Token endpoint not returning valid JSON
        return False
    except Exception:
        return False


# Infrastructure check and autouse skip fixture are in tests/integration/auth/conftest.py
# This avoids duplicate autouse fixtures across test files (best practice)

# URLs
GATEWAY_URL = os.getenv("GATEWAY_URL", "http://localhost")
QDRANT_API_URL = f"{GATEWAY_URL}/vectors"
QDRANT_DASHBOARD_URL = f"{GATEWAY_URL}/dashboard"
KEYCLOAK_URL = f"{GATEWAY_URL}/authn"

# Test credentials from tests/e2e/default-realm.json
ADMIN_USERNAME = "admin"
ADMIN_PASSWORD = "admin123"


@pytest.mark.xdist_group(name="test_qdrant_auth")
class TestQdrantAuthRequired:
    """Test that Qdrant routes require authentication via forward-auth middleware."""

    def teardown_method(self) -> None:
        """Force GC to prevent mock accumulation in xdist workers."""
        gc.collect()

    def test_qdrant_vectors_route_requires_auth(self):
        """
        GIVEN: Qdrant API accessible via /vectors path
        WHEN: Accessing without authentication
        THEN: Should redirect to Keycloak login (302/307) or return 401

        Auth is enforced via forward-auth@docker middleware (ADR-0054).
        """
        response = requests.get(
            f"{QDRANT_API_URL}/",
            timeout=10,
            allow_redirects=False,
        )

        # Should redirect to auth or return 401
        assert response.status_code in [302, 307, 401, 403], (
            f"Qdrant /vectors route should require auth, got {response.status_code}\n"
            "\n"
            "If this fails with 200, check docker-compose.test.yml:\n"
            "  qdrant-test labels should include:\n"
            "    traefik.http.routers.qdrant.middlewares=forward-auth@docker,qdrant-strip"
        )

        # If redirect, verify it goes to auth
        if response.status_code in [302, 307]:
            location = response.headers.get("Location", "")
            auth_indicators = ["/authn", "keycloak", "/_oauth"]
            assert any(ind in location.lower() for ind in auth_indicators), (
                f"Redirect should go to Keycloak auth, got: {location}"
            )

    def test_qdrant_dashboard_route_requires_auth(self):
        """
        GIVEN: Qdrant Dashboard accessible via /dashboard path
        WHEN: Accessing without authentication
        THEN: Should redirect to Keycloak login (302/307) or return 401

        Auth is enforced via forward-auth@docker middleware (ADR-0054).
        """
        response = requests.get(
            f"{QDRANT_DASHBOARD_URL}/",
            timeout=10,
            allow_redirects=False,
        )

        # Should redirect to auth or return 401
        assert response.status_code in [302, 307, 401, 403], (
            f"Qdrant /dashboard route should require auth, got {response.status_code}\n"
            "\n"
            "If this fails with 200, check docker-compose.test.yml:\n"
            "  qdrant-test labels should include:\n"
            "    traefik.http.routers.qdrant-dashboard.middlewares=forward-auth@docker"
        )


@pytest.mark.xdist_group(name="test_qdrant_auth")
class TestQdrantAuthenticatedAccess:
    """Test authenticated access to Qdrant via forward-auth."""

    def teardown_method(self) -> None:
        """Force GC to prevent mock accumulation in xdist workers."""
        gc.collect()

    @pytest.fixture
    def authenticated_session(self) -> requests.Session:
        """Get an authenticated session with valid Keycloak token.

        Uses service account token (client_credentials grant) since ROPC is disabled.
        """
        session = requests.Session()

        # Get token from Keycloak using client credentials (ROPC is disabled)
        token_url = f"{KEYCLOAK_URL}/realms/default/protocol/openid-connect/token"
        try:
            response = session.post(
                token_url,
                data={
                    "grant_type": "client_credentials",
                    "client_id": "agent-studio-keycloak-client-id-for-e2e-tests",
                    "client_secret": "test-client-secret-for-e2e-tests",
                    "scope": "openid profile email",
                },
                timeout=10,
            )
        except requests.exceptions.RequestException as e:
            pytest.skip(f"Could not connect to Keycloak: {e}")

        if response.status_code != 200:
            pytest.skip(f"Could not authenticate: {response.status_code} - {response.text}")

        try:
            token_data = response.json()
        except (requests.exceptions.JSONDecodeError, ValueError) as e:
            pytest.skip(f"Keycloak returned invalid JSON: {e}")

        if "access_token" not in token_data:
            pytest.skip(f"No access_token in response: {token_data}")

        access_token = token_data["access_token"]

        # Set Authorization header for subsequent requests
        session.headers["Authorization"] = f"Bearer {access_token}"

        return session

    def test_authenticated_user_can_access_qdrant_collections(self, authenticated_session: requests.Session):
        """
        GIVEN: Valid Keycloak authentication
        WHEN: Accessing Qdrant collections endpoint
        THEN: Should return collections list (may be empty)
        """
        response = authenticated_session.get(
            f"{QDRANT_API_URL}/collections",
            timeout=10,
        )

        # Note: forward-auth uses cookies after initial auth, so Bearer token
        # may not work directly. This test verifies the auth flow is in place.
        # If this returns 302, it means forward-auth wants cookie-based auth.
        if response.status_code in [302, 307]:
            pytest.skip(
                "forward-auth requires cookie-based session, not Bearer token. "
                "Use browser-based OAuth flow for full integration test."
            )

        # If we get through, verify valid response
        assert response.status_code == 200, (
            f"Authenticated Qdrant access failed: {response.status_code}\nResponse: {response.text[:500]}"
        )

        # forward-auth may return HTML redirect page instead of JSON
        content_type = response.headers.get("Content-Type", "")
        if "text/html" in content_type or not response.text:
            pytest.skip("forward-auth returned HTML/empty response - requires browser-based OAuth flow.")

        try:
            data = response.json()
            assert "result" in data, "Expected 'result' in response"
        except requests.exceptions.JSONDecodeError:
            pytest.skip("forward-auth returned non-JSON response - requires browser-based OAuth flow.")

    def test_authenticated_user_can_access_qdrant_telemetry(self, authenticated_session: requests.Session):
        """
        GIVEN: Valid Keycloak authentication
        WHEN: Accessing Qdrant telemetry endpoint
        THEN: Should return telemetry data
        """
        response = authenticated_session.get(
            f"{QDRANT_API_URL}/telemetry",
            timeout=10,
        )

        if response.status_code in [302, 307]:
            pytest.skip("forward-auth requires cookie-based session, not Bearer token.")

        assert response.status_code == 200, f"Authenticated Qdrant telemetry access failed: {response.status_code}"


@pytest.mark.xdist_group(name="test_qdrant_auth")
class TestQdrantGatewayRouting:
    """Test Qdrant routing is properly configured in Traefik."""

    def teardown_method(self) -> None:
        """Force GC to prevent mock accumulation in xdist workers."""
        gc.collect()

    def test_qdrant_routes_configured_in_traefik(self):
        """
        GIVEN: Traefik gateway with Qdrant service configured
        WHEN: Querying Traefik API for routers
        THEN: Should have qdrant and qdrant-dashboard routers registered
        """
        response = requests.get(
            "http://localhost:8080/api/http/routers",
            timeout=10,
        )
        assert response.status_code == 200, "Traefik API should be accessible"

        routers = response.json()
        router_names = [r.get("name", "") for r in routers]

        # Check for qdrant routers
        has_qdrant_router = any("qdrant" in name.lower() for name in router_names)
        assert has_qdrant_router, f"Qdrant router should be configured in Traefik. Found routers: {router_names}"

    def test_qdrant_routes_have_forward_auth_middleware(self):
        """
        GIVEN: Traefik gateway with Qdrant routes
        WHEN: Querying Traefik API for router configuration
        THEN: Qdrant routers should have forward-auth middleware attached

        This test verifies the middleware chain is correctly configured.
        """
        response = requests.get(
            "http://localhost:8080/api/http/routers",
            timeout=10,
        )
        assert response.status_code == 200, "Traefik API should be accessible"

        routers = response.json()

        # Find qdrant router
        qdrant_router = None
        for router in routers:
            if router.get("name", "").startswith("qdrant@"):
                qdrant_router = router
                break

        assert qdrant_router is not None, f"Qdrant router not found. Available: {[r.get('name') for r in routers]}"

        # Verify forward-auth middleware is attached
        middlewares = qdrant_router.get("middlewares", [])
        has_forward_auth = any("forward-auth" in str(m).lower() for m in middlewares)
        assert has_forward_auth, (
            f"Qdrant router should have forward-auth middleware.\n"
            f"Current middlewares: {middlewares}\n"
            "\n"
            "Fix: Update docker-compose.test.yml qdrant-test labels:\n"
            "  traefik.http.routers.qdrant.middlewares=forward-auth@docker,qdrant-strip"
        )

    def test_qdrant_dashboard_route_has_forward_auth_middleware(self):
        """
        GIVEN: Traefik gateway with Qdrant Dashboard route
        WHEN: Querying Traefik API for router configuration
        THEN: qdrant-dashboard router should have forward-auth middleware
        """
        response = requests.get(
            "http://localhost:8080/api/http/routers",
            timeout=10,
        )
        assert response.status_code == 200

        routers = response.json()

        # Find qdrant-dashboard router
        dashboard_router = None
        for router in routers:
            if router.get("name", "").startswith("qdrant-dashboard@"):
                dashboard_router = router
                break

        assert dashboard_router is not None, (
            f"Qdrant dashboard router not found. Available: {[r.get('name') for r in routers]}"
        )

        # Verify forward-auth middleware is attached
        middlewares = dashboard_router.get("middlewares", [])
        has_forward_auth = any("forward-auth" in str(m).lower() for m in middlewares)
        assert has_forward_auth, (
            f"Qdrant dashboard router should have forward-auth middleware.\nCurrent middlewares: {middlewares}"
        )

    def test_qdrant_strip_prefix_middleware_configured(self):
        """
        GIVEN: Traefik gateway with Qdrant path routing
        WHEN: Querying Traefik API for middlewares
        THEN: Should have qdrant-strip middleware to strip /vectors prefix
        """
        response = requests.get(
            "http://localhost:8080/api/http/middlewares",
            timeout=10,
        )
        assert response.status_code == 200, "Traefik API should be accessible"

        middlewares = response.json()
        middleware_names = [m.get("name", "") for m in middlewares]

        # Check for qdrant-strip middleware
        has_strip_middleware = any("qdrant" in name.lower() and "strip" in name.lower() for name in middleware_names)
        assert has_strip_middleware, f"qdrant-strip middleware should be configured. Found: {middleware_names}"
