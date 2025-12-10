"""
Integration tests for Traefik authentication middleware with Keycloak.

TDD Cycle: RED -> GREEN -> REFACTOR

These tests verify that:
1. Protected routes require authentication (redirect to Keycloak)
2. Public routes are accessible without authentication
3. Authenticated requests pass user info headers to backends
4. Session cookies are properly set after login

Reference: ADR-0054 (pending) - Gateway-Level Authentication
"""

import gc
import os

import pytest
import requests

# Mark as integration test requiring docker infrastructure
pytestmark = [
    pytest.mark.integration,
    pytest.mark.auth,
    pytest.mark.skipif(
        os.getenv("TEST_INFRA_UP") != "true",
        reason="Requires test infrastructure: make test-infra-up",
    ),
]

# Gateway URL (Traefik on port 80)
GATEWAY_URL = os.getenv("GATEWAY_URL", "http://localhost")

# Keycloak test credentials
KEYCLOAK_URL = f"{GATEWAY_URL}/authn"
TEST_USERNAME = "testuser"
TEST_PASSWORD = "testpassword"  # noqa: S105


@pytest.mark.xdist_group(name="testtrafeikauthpublicroutes")
class TestPublicRoutes:
    """Test that public routes are accessible without authentication."""

    def teardown_method(self) -> None:
        """Force GC to prevent mock accumulation in xdist workers."""
        gc.collect()

    def test_keycloak_login_page_is_public(self):
        """
        GIVEN: No authentication
        WHEN: Accessing Keycloak login page
        THEN: Should return 200 or redirect to login (not 401)
        """
        response = requests.get(
            f"{GATEWAY_URL}/authn/realms/master/.well-known/openid-configuration",
            timeout=10,
            allow_redirects=False,
        )
        # OIDC discovery endpoint should be public
        assert response.status_code == 200, f"Keycloak OIDC discovery should be public, got {response.status_code}"

    def test_health_endpoints_are_public(self):
        """
        GIVEN: No authentication
        WHEN: Accessing health check endpoints
        THEN: Should return 200 (health checks must be unauthenticated for k8s probes)
        """
        health_endpoints = [
            "/authz/healthz",  # OpenFGA health
            "/traces/ready",  # Tempo readiness
            "/metrics/ready",  # Mimir readiness
        ]
        for endpoint in health_endpoints:
            response = requests.get(
                f"{GATEWAY_URL}{endpoint}",
                timeout=10,
                allow_redirects=False,
            )
            assert response.status_code in [200, 204], (
                f"Health endpoint {endpoint} should be public, got {response.status_code}"
            )


@pytest.mark.xdist_group(name="testtrafeikauthprotectedroutes")
class TestProtectedRoutes:
    """Test that protected routes require authentication."""

    def teardown_method(self) -> None:
        """Force GC to prevent mock accumulation in xdist workers."""
        gc.collect()

    @pytest.mark.parametrize(
        "protected_route",
        [
            "/mcp/",  # MCP Server API
            "/build/",  # Visual Workflow Builder
            "/play/",  # Interactive Playground
            "/dashboards/",  # Grafana
            "/playground",  # OpenFGA Playground
        ],
    )
    def test_protected_route_requires_auth(self, protected_route: str):
        """
        GIVEN: No authentication (no session cookie or token)
        WHEN: Accessing a protected route
        THEN: Should redirect to Keycloak login (302) or return 401
        """
        response = requests.get(
            f"{GATEWAY_URL}{protected_route}",
            timeout=10,
            allow_redirects=False,
        )

        # Should redirect to auth or return 401
        assert response.status_code in [302, 401, 403], (
            f"Protected route {protected_route} should require auth, got {response.status_code}"
        )

        # If redirect, should go to Keycloak
        if response.status_code == 302:
            location = response.headers.get("Location", "")
            assert "/authn" in location or "keycloak" in location.lower(), f"Redirect should go to Keycloak, got: {location}"

    def test_observability_dashboards_require_auth(self):
        """
        GIVEN: No authentication
        WHEN: Accessing observability dashboards
        THEN: Should require authentication (these contain sensitive data)
        """
        observability_routes = [
            "/dashboards/",  # Grafana
            "/telemetry/",  # Alloy
            "/gateway/",  # Traefik dashboard
        ]
        for route in observability_routes:
            response = requests.get(
                f"{GATEWAY_URL}{route}",
                timeout=10,
                allow_redirects=False,
            )
            assert response.status_code in [302, 401, 403], (
                f"Observability route {route} should require auth, got {response.status_code}"
            )


@pytest.mark.xdist_group(name="testtrafeikauthenticatedaccess")
class TestAuthenticatedAccess:
    """Test authenticated access to protected routes."""

    def teardown_method(self) -> None:
        """Force GC to prevent mock accumulation in xdist workers."""
        gc.collect()

    @pytest.fixture
    def authenticated_session(self) -> requests.Session:
        """Get an authenticated session with valid Keycloak token."""
        session = requests.Session()

        # Get token from Keycloak using password grant
        token_url = f"{GATEWAY_URL}/authn/realms/master/protocol/openid-connect/token"
        response = session.post(
            token_url,
            data={
                "grant_type": "password",
                "client_id": "mcp-server",
                "client_secret": "test-client-secret-for-e2e-tests",
                "username": TEST_USERNAME,
                "password": TEST_PASSWORD,
            },
            timeout=10,
        )

        if response.status_code != 200:
            pytest.skip(f"Could not authenticate: {response.status_code} - {response.text}")

        token_data = response.json()
        access_token = token_data["access_token"]

        # Set Authorization header for subsequent requests
        session.headers["Authorization"] = f"Bearer {access_token}"

        return session

    def test_authenticated_user_can_access_protected_route(self, authenticated_session: requests.Session):
        """
        GIVEN: Valid Keycloak authentication
        WHEN: Accessing a protected route
        THEN: Should return 200 (or appropriate success code)
        """
        response = authenticated_session.get(
            f"{GATEWAY_URL}/mcp/health",
            timeout=10,
        )

        # Should succeed with auth
        assert response.status_code in [200, 204, 307], f"Authenticated request should succeed, got {response.status_code}"

    def test_auth_headers_passed_to_backend(self, authenticated_session: requests.Session):
        """
        GIVEN: Valid Keycloak authentication via forward-auth
        WHEN: Request reaches the backend service
        THEN: User info headers should be set (X-Forwarded-User, etc.)

        Note: This test requires a backend endpoint that echoes headers.
        """
        # This would require a debug endpoint that returns request headers
        # For now, we verify the auth itself works
        pytest.skip("Requires header echo endpoint - implement in backend")


@pytest.mark.xdist_group(name="testtraefikauthmiddlewareconfig")
class TestAuthMiddlewareConfiguration:
    """Test that auth middleware is properly configured in Traefik."""

    def teardown_method(self) -> None:
        """Force GC to prevent mock accumulation in xdist workers."""
        gc.collect()

    def test_forward_auth_service_is_healthy(self):
        """
        GIVEN: traefik-forward-auth service is deployed
        WHEN: Checking its health
        THEN: Should be running and healthy
        """
        # Forward auth typically exposes a health endpoint
        response = requests.get(
            f"{GATEWAY_URL}/_oauth/health",  # Common forward-auth health path
            timeout=10,
            allow_redirects=False,
        )
        # If forward-auth is deployed, should return 200
        # If not deployed yet (RED phase), this will fail
        assert response.status_code == 200, "Forward auth service should be healthy"

    def test_traefik_has_auth_middleware_configured(self):
        """
        GIVEN: Traefik is running
        WHEN: Querying middleware configuration
        THEN: Should have forwardAuth middleware defined
        """
        response = requests.get(
            "http://localhost:8080/api/http/middlewares",
            timeout=10,
        )
        assert response.status_code == 200

        middlewares = response.json()
        middleware_names = [m.get("name", "") for m in middlewares]

        # Look for auth-related middleware
        auth_middlewares = [name for name in middleware_names if "auth" in name.lower() or "forward" in name.lower()]

        assert len(auth_middlewares) > 0, f"Should have auth middleware configured. Found: {middleware_names}"
