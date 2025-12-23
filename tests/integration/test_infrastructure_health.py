"""
Integration tests for test infrastructure health.

This test suite validates that all test infrastructure services are reachable
and healthy. It serves as an early warning system for infrastructure issues.

Reference: Action Plan - Action 5: Fix Integration Test Infrastructure
TDD Status: These tests validate infrastructure configuration, not business logic.

Usage:
    pytest tests/integration/test_infrastructure_health.py -v

    Or with make:
    make test-infra-health

Note: These tests require test infrastructure to be running:
    make test-infra-up
"""

from __future__ import annotations

import gc
import socket
import time
from typing import TYPE_CHECKING

import pytest

from tests.constants import (
    TEST_KEYCLOAK_PORT,
    TEST_OPENFGA_HTTP_PORT,
    TEST_POSTGRES_PORT,
    TEST_QDRANT_PORT,
    TEST_REDIS_PORT,
)

if TYPE_CHECKING:
    import httpx


pytestmark = [pytest.mark.integration, pytest.mark.requires_infra]


def is_port_open(host: str, port: int, timeout: float = 2.0) -> bool:
    """Check if a TCP port is open and accepting connections."""
    try:
        sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        sock.settimeout(timeout)
        result = sock.connect_ex((host, port))
        sock.close()
        return result == 0
    except OSError:
        return False


def get_http_response(url: str, timeout: float = 5.0) -> httpx.Response | None:
    """Make HTTP GET request and return response or None on failure."""
    try:
        import httpx

        return httpx.get(url, timeout=timeout, follow_redirects=True)
    except Exception:
        return None


def wait_for_port(host: str, port: int, timeout: float = 30.0) -> bool:
    """Wait for a port to become available."""
    start_time = time.time()
    while time.time() - start_time < timeout:
        if is_port_open(host, port):
            return True
        time.sleep(0.5)
    return False


def skip_if_no_infra() -> None:
    """Skip test if infrastructure is not running."""
    if not is_port_open("localhost", TEST_POSTGRES_PORT, timeout=1.0):
        pytest.skip("Test infrastructure not running. Start with: make test-infra-up")


@pytest.mark.integration
@pytest.mark.requires_infra
@pytest.mark.xdist_group(name="infrastructure_health")
class TestInfrastructurePortConnectivity:
    """
    Test that all infrastructure service ports are accessible.

    These tests verify basic TCP connectivity to each service.
    """

    def teardown_method(self) -> None:
        """Force GC to prevent mock accumulation in xdist workers."""
        gc.collect()

    def test_postgres_port_is_open(self) -> None:
        """Test that PostgreSQL is accepting connections on port 9432."""
        skip_if_no_infra()
        assert is_port_open("localhost", TEST_POSTGRES_PORT), (
            f"PostgreSQL port {TEST_POSTGRES_PORT} is not open. Ensure docker-compose.test.yml is running."
        )

    def test_redis_port_is_open(self) -> None:
        """Test that Redis is accepting connections on port 9379."""
        skip_if_no_infra()
        assert is_port_open("localhost", TEST_REDIS_PORT), (
            f"Redis port {TEST_REDIS_PORT} is not open. Ensure docker-compose.test.yml is running."
        )

    def test_openfga_http_port_is_open(self) -> None:
        """Test that OpenFGA HTTP API is accepting connections on port 9080."""
        skip_if_no_infra()
        assert is_port_open("localhost", TEST_OPENFGA_HTTP_PORT), (
            f"OpenFGA HTTP port {TEST_OPENFGA_HTTP_PORT} is not open. Ensure docker-compose.test.yml is running."
        )

    def test_keycloak_http_port_is_open(self) -> None:
        """Test that Keycloak HTTP API is accepting connections on port 9082."""
        skip_if_no_infra()
        assert is_port_open("localhost", TEST_KEYCLOAK_PORT), (
            f"Keycloak HTTP port {TEST_KEYCLOAK_PORT} is not open. Ensure docker-compose.test.yml is running."
        )

    def test_qdrant_port_is_open(self) -> None:
        """Test that Qdrant is accepting connections on port 9333."""
        skip_if_no_infra()
        assert is_port_open("localhost", TEST_QDRANT_PORT), (
            f"Qdrant port {TEST_QDRANT_PORT} is not open. Ensure docker-compose.test.yml is running."
        )


@pytest.mark.integration
@pytest.mark.requires_infra
@pytest.mark.xdist_group(name="infrastructure_health")
class TestInfrastructureHealthEndpoints:
    """
    Test that infrastructure services report healthy via their health endpoints.

    These tests go beyond port connectivity to verify services are actually
    ready to handle requests.
    """

    def teardown_method(self) -> None:
        """Force GC to prevent mock accumulation in xdist workers."""
        gc.collect()

    def test_openfga_health_endpoint(self) -> None:
        """Test that OpenFGA health endpoint returns 200 OK."""
        skip_if_no_infra()
        url = f"http://localhost:{TEST_OPENFGA_HTTP_PORT}/healthz"
        response = get_http_response(url)
        assert response is not None, f"Failed to connect to OpenFGA health endpoint: {url}"
        assert response.status_code == 200, (
            f"OpenFGA health check failed. Status: {response.status_code}, Body: {response.text[:200]}"
        )

    def test_qdrant_readiness_endpoint(self) -> None:
        """Test that Qdrant readiness endpoint returns 200 OK."""
        skip_if_no_infra()
        url = f"http://localhost:{TEST_QDRANT_PORT}/readyz"
        response = get_http_response(url)
        assert response is not None, f"Failed to connect to Qdrant readiness endpoint: {url}"
        assert response.status_code == 200, (
            f"Qdrant readiness check failed. Status: {response.status_code}, Body: {response.text[:200]}"
        )


@pytest.mark.integration
@pytest.mark.requires_infra
@pytest.mark.xdist_group(name="infrastructure_health_keycloak")
class TestKeycloakConnectivity:
    """
    Test Keycloak OIDC connectivity at localhost:9082.

    These tests validate that Keycloak is fully initialized and ready
    to serve OIDC requests, which is critical for E2E authentication tests.

    Reference: ADR-0053 - Keycloak requires at least 60s to initialize
    """

    def teardown_method(self) -> None:
        """Force GC to prevent mock accumulation in xdist workers."""
        gc.collect()

    def test_keycloak_is_reachable(self) -> None:
        """
        Test that Keycloak HTTP API is reachable at localhost:9082.

        This is the primary connectivity test from the action plan.
        """
        skip_if_no_infra()
        assert is_port_open("localhost", TEST_KEYCLOAK_PORT), (
            f"Keycloak not reachable at localhost:{TEST_KEYCLOAK_PORT}. This is a critical E2E test infrastructure issue."
        )

    def test_keycloak_oidc_wellknown_endpoint(self) -> None:
        """
        Test that Keycloak OIDC well-known endpoint is responding.

        This validates that:
        1. Keycloak is fully initialized
        2. The 'default' realm is imported
        3. OIDC discovery is functional

        Note: Keycloak is configured with KC_HTTP_RELATIVE_PATH=/authn
        so all endpoints are under the /authn prefix.
        """
        skip_if_no_infra()
        url = f"http://localhost:{TEST_KEYCLOAK_PORT}/authn/realms/default/.well-known/openid-configuration"
        response = get_http_response(url, timeout=10.0)

        assert response is not None, (
            f"Failed to connect to Keycloak OIDC discovery endpoint: {url}\n"
            f"This likely means Keycloak is not fully initialized yet.\n"
            f"Keycloak requires ~60-90s to start (JIT compilation + realm import)."
        )
        assert response.status_code == 200, (
            f"Keycloak OIDC discovery endpoint returned {response.status_code}.\n"
            f"Expected 200 OK.\n"
            f"URL: {url}\n"
            f"Response: {response.text[:500]}"
        )

        # Verify the response is valid OIDC configuration
        try:
            config = response.json()
            assert "issuer" in config, "OIDC config missing 'issuer' field"
            assert "authorization_endpoint" in config, "OIDC config missing 'authorization_endpoint'"
            assert "token_endpoint" in config, "OIDC config missing 'token_endpoint'"
            assert "jwks_uri" in config, "OIDC config missing 'jwks_uri'"
        except Exception as e:
            pytest.fail(f"Failed to parse Keycloak OIDC discovery response: {e}")

    def test_keycloak_token_endpoint_reachable(self) -> None:
        """
        Test that Keycloak token endpoint is reachable.

        This validates that the OAuth 2.0 token endpoint is accessible,
        which is required for client credentials grant in E2E tests.
        """
        skip_if_no_infra()

        # First get the OIDC config to find the token endpoint
        wellknown_url = f"http://localhost:{TEST_KEYCLOAK_PORT}/authn/realms/default/.well-known/openid-configuration"
        response = get_http_response(wellknown_url)
        if response is None or response.status_code != 200:
            pytest.skip("OIDC discovery not available, skipping token endpoint test")

        config = response.json()
        token_endpoint = config.get("token_endpoint")
        assert token_endpoint is not None, "No token_endpoint in OIDC config"

        # The token endpoint only accepts POST, so GET returns 405 Method Not Allowed
        # We just verify it's reachable and responds appropriately
        token_response = get_http_response(token_endpoint)
        assert token_response is not None, f"Failed to connect to Keycloak token endpoint: {token_endpoint}"
        # Token endpoint returns:
        # - 405: Method Not Allowed (GET not allowed, POST required)
        # - 400/401: Bad request / unauthorized (if POST without proper credentials)
        # - 415: Unsupported media type (wrong content-type)
        assert token_response.status_code in (400, 401, 405, 415), (
            f"Unexpected token endpoint response: {token_response.status_code}"
        )

    def test_keycloak_admin_console_accessible(self) -> None:
        """
        Test that Keycloak admin console is accessible.

        The admin console at /authn/admin/master/console should redirect
        to the login page.
        """
        skip_if_no_infra()
        url = f"http://localhost:{TEST_KEYCLOAK_PORT}/authn/admin/master/console/"
        response = get_http_response(url)

        assert response is not None, f"Failed to connect to Keycloak admin console: {url}"
        # Admin console redirects to login, so 200 (with redirect followed) is expected
        # or 302 if redirect not followed
        assert response.status_code in (200, 302), (
            f"Keycloak admin console returned {response.status_code}. Expected 200 or 302."
        )


@pytest.mark.integration
@pytest.mark.requires_infra
@pytest.mark.xdist_group(name="infrastructure_health")
class TestAllServicesHealthy:
    """
    Test that all services pass their health checks.

    This is a comprehensive test that validates the entire test
    infrastructure is ready for E2E tests.
    """

    def teardown_method(self) -> None:
        """Force GC to prevent mock accumulation in xdist workers."""
        gc.collect()

    def test_all_critical_services_are_reachable(self) -> None:
        """
        Verify all critical services are reachable.

        This is a summary test that validates the minimum infrastructure
        required for E2E tests.
        """
        skip_if_no_infra()

        services = {
            "PostgreSQL": TEST_POSTGRES_PORT,
            "Redis": TEST_REDIS_PORT,
            "OpenFGA": TEST_OPENFGA_HTTP_PORT,
            "Keycloak": TEST_KEYCLOAK_PORT,
            "Qdrant": TEST_QDRANT_PORT,
        }

        unreachable = []
        for service, port in services.items():
            if not is_port_open("localhost", port):
                unreachable.append(f"{service} (port {port})")

        assert not unreachable, (
            "The following services are not reachable:\n"
            "  - " + "\n  - ".join(unreachable) + "\n\n"
            "Start infrastructure with: make test-infra-up"
        )

    def test_health_endpoints_return_success(self) -> None:
        """
        Verify services with health endpoints report healthy.
        """
        skip_if_no_infra()

        health_endpoints = {
            "OpenFGA": f"http://localhost:{TEST_OPENFGA_HTTP_PORT}/healthz",
            "Qdrant": f"http://localhost:{TEST_QDRANT_PORT}/readyz",
            "Keycloak OIDC": f"http://localhost:{TEST_KEYCLOAK_PORT}/authn/realms/default/.well-known/openid-configuration",
        }

        unhealthy = []
        for service, url in health_endpoints.items():
            response = get_http_response(url)
            if response is None or response.status_code != 200:
                status = response.status_code if response else "Connection failed"
                unhealthy.append(f"{service}: {url} -> {status}")

        assert not unhealthy, "The following services are unhealthy:\n  - " + "\n  - ".join(unhealthy)


@pytest.mark.integration
@pytest.mark.requires_infra
@pytest.mark.slow
@pytest.mark.xdist_group(name="infrastructure_health_timing")
class TestInfrastructureHealthTiming:
    """
    Test infrastructure health check timing.

    These tests measure how long services take to respond, which helps
    identify timing issues and optimize health check configurations.
    """

    def teardown_method(self) -> None:
        """Force GC to prevent mock accumulation in xdist workers."""
        gc.collect()

    def test_keycloak_oidc_response_time(self) -> None:
        """
        Measure Keycloak OIDC discovery response time.

        The OIDC discovery endpoint should respond within the configured
        health check timeout (10s in docker-compose.test.yml).
        """
        skip_if_no_infra()

        url = f"http://localhost:{TEST_KEYCLOAK_PORT}/authn/realms/default/.well-known/openid-configuration"
        start_time = time.time()
        response = get_http_response(url, timeout=15.0)
        elapsed = time.time() - start_time

        assert response is not None, "Failed to get OIDC discovery response"
        assert response.status_code == 200, f"Unexpected status: {response.status_code}"

        # Should complete well under the 10s timeout configured in docker-compose
        max_acceptable = 5.0  # 50% of timeout
        assert elapsed < max_acceptable, (
            f"Keycloak OIDC discovery took {elapsed:.2f}s, exceeds {max_acceptable}s threshold.\n"
            f"This may cause health check timeouts."
        )

        # Log for informational purposes
        print(f"Keycloak OIDC discovery response time: {elapsed:.3f}s")

    def test_all_services_respond_quickly(self) -> None:
        """
        Measure response times for all services with health endpoints.
        """
        skip_if_no_infra()

        endpoints = {
            "OpenFGA": f"http://localhost:{TEST_OPENFGA_HTTP_PORT}/healthz",
            "Qdrant": f"http://localhost:{TEST_QDRANT_PORT}/readyz",
            "Keycloak": f"http://localhost:{TEST_KEYCLOAK_PORT}/authn/realms/default/.well-known/openid-configuration",
        }

        slow_services = []
        for service, url in endpoints.items():
            start_time = time.time()
            response = get_http_response(url, timeout=10.0)
            elapsed = time.time() - start_time

            if response is None:
                slow_services.append(f"{service}: Connection failed")
            elif elapsed > 3.0:  # 3s is slow
                slow_services.append(f"{service}: {elapsed:.2f}s (slow)")
            else:
                print(f"{service}: {elapsed:.3f}s")

        assert not slow_services, "Some services are slow:\n  - " + "\n  - ".join(slow_services)
