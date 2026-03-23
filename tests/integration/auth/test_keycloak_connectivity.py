"""
Keycloak Connectivity Diagnostic Tests.

TDD Phase 6: These tests verify Keycloak is accessible and properly configured
before running dependent integration tests. They provide clear diagnostic
information when Keycloak is not available.

Usage:
    # Run diagnostics
    pytest tests/integration/auth/test_keycloak_connectivity.py -v

    # Run with verbose output for debugging
    pytest tests/integration/auth/test_keycloak_connectivity.py -v -s
"""

import gc
import os
import subprocess

import pytest

pytestmark = [pytest.mark.integration, pytest.mark.keycloak]


def _is_docker_available() -> bool:
    """Check if Docker is available."""
    try:
        result = subprocess.run(
            ["docker", "version"],
            capture_output=True,
            timeout=30,
        )
        return result.returncode == 0
    except (FileNotFoundError, subprocess.TimeoutExpired):
        return False


def _is_keycloak_container_running() -> bool:
    """Check if Keycloak container is running."""
    try:
        result = subprocess.run(
            ["docker", "ps", "--filter", "name=keycloak", "--format", "{{.Names}}"],
            capture_output=True,
            text=True,
            timeout=30,
        )
        return "keycloak" in result.stdout.lower()
    except (FileNotFoundError, subprocess.TimeoutExpired):
        return False


@pytest.mark.integration
@pytest.mark.xdist_group(name="keycloak_connectivity")
class TestKeycloakConnectivity:
    """
    Diagnostic tests for Keycloak connectivity.

    These tests verify the Keycloak service is accessible at different levels:
    1. Container running (Docker)
    2. Port accessible (TCP)
    3. HTTP health endpoint responding
    4. OIDC discovery endpoint valid
    """

    def teardown_method(self) -> None:
        """Force GC to prevent mock accumulation in xdist workers."""
        gc.collect()

    def test_keycloak_container_running(self):
        """
        DIAGNOSTIC: Verify Keycloak container is running.

        This is the first check - if the container isn't running,
        all other tests will fail.
        """
        if not _is_docker_available():
            pytest.skip("Docker not available")

        result = subprocess.run(
            ["docker", "ps", "--filter", "name=keycloak", "--format", "{{.Names}}\t{{.Status}}"],
            capture_output=True,
            text=True,
            timeout=30,
        )

        if "keycloak" not in result.stdout.lower():
            pytest.skip(
                "Keycloak container not running.\n"
                "Start test infrastructure with: make test-infra-up\n"
                f"Docker ps output: {result.stdout}"
            )

        # Extract container info
        for line in result.stdout.strip().split("\n"):
            if "keycloak" in line.lower():
                print(f"✅ Keycloak container: {line}")

    def test_keycloak_port_accessible_gateway(self):
        """
        DIAGNOSTIC: Verify Keycloak port 80 (gateway) is accessible.

        Tests TCP connectivity through Traefik gateway.
        """
        import socket

        if not _is_keycloak_container_running():
            pytest.skip("Keycloak container not running")

        try:
            sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            sock.settimeout(5)
            result = sock.connect_ex(("localhost", 80))
            sock.close()

            if result != 0:
                pytest.fail(
                    f"Port 80 (Traefik gateway) not accessible (error code: {result}).\n"
                    "Check if Traefik is running: docker ps | grep traefik"
                )

            print("✅ Gateway port 80 is accessible")

        except Exception as e:
            pytest.fail(f"Failed to connect to gateway port 80: {e}")

    def test_keycloak_port_accessible_direct(self):
        """
        DIAGNOSTIC: Verify Keycloak direct port 9082 is accessible.

        Tests TCP connectivity bypassing the gateway.
        """
        import socket

        if not _is_keycloak_container_running():
            pytest.skip("Keycloak container not running")

        try:
            sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            sock.settimeout(5)
            result = sock.connect_ex(("localhost", 9082))
            sock.close()

            if result != 0:
                pytest.skip(
                    f"Keycloak direct port 9082 not accessible (error code: {result}).\n"
                    "This may be expected if only gateway routing is configured."
                )

            print("✅ Keycloak direct port 9082 is accessible")

        except Exception as e:
            pytest.skip(f"Failed to connect to Keycloak port 9082: {e}")

    def test_keycloak_health_endpoint(self):
        """
        DIAGNOSTIC: Verify Keycloak health endpoint responds.

        Note: The health endpoint is on the management port (9000) inside
        the container and may not be exposed through the gateway. This test
        checks the direct port if available, otherwise uses OIDC discovery
        as a proxy for health.
        """
        import httpx

        if not _is_keycloak_container_running():
            pytest.skip("Keycloak container not running")

        # Try direct management port first (9000 mapped to host)
        # Note: Management port may not be exposed to host
        try:
            response = httpx.get(
                "http://localhost:9082/authn/health/ready",
                timeout=5.0,
            )
            if response.status_code == 200:
                print(f"✅ Keycloak health endpoint (direct): {response.status_code}")
                return
        except Exception:
            pass

        # Fallback: Use OIDC discovery as health indicator
        # If OIDC works, Keycloak is healthy
        try:
            response = httpx.get(
                "http://localhost/authn/realms/default/.well-known/openid-configuration",
                timeout=10.0,
            )
            if response.status_code == 200:
                print("✅ Keycloak health verified via OIDC discovery")
                print("   (Management health endpoint not exposed through gateway)")
                return

            pytest.skip(
                f"Keycloak health check failed.\n"
                f"OIDC discovery returned: {response.status_code}\n"
                "Keycloak may still be starting up."
            )

        except httpx.ConnectError as e:
            pytest.fail(f"Cannot connect to Keycloak: {e}\nVerify Keycloak is running and gateway routing is configured.")
        except httpx.TimeoutException:
            pytest.fail("Keycloak health check timed out.\nKeycloak may be overloaded or still starting.")

    def test_keycloak_oidc_discovery(self):
        """
        DIAGNOSTIC: Verify OIDC discovery endpoint returns valid configuration.

        This is the critical test - OIDC must be working for auth flows.
        """
        import httpx

        if not _is_keycloak_container_running():
            pytest.skip("Keycloak container not running")

        oidc_url = "http://localhost/authn/realms/default/.well-known/openid-configuration"

        try:
            response = httpx.get(oidc_url, timeout=10.0)

            if response.status_code != 200:
                pytest.fail(
                    f"OIDC discovery endpoint returned {response.status_code}.\n"
                    f"URL: {oidc_url}\n"
                    f"Response: {response.text[:500]}\n"
                    "Check if 'default' realm exists in Keycloak."
                )

            # Verify it's valid OIDC config
            config = response.json()
            required_fields = ["issuer", "authorization_endpoint", "token_endpoint"]

            missing = [f for f in required_fields if f not in config]
            if missing:
                pytest.fail(f"OIDC config missing required fields: {missing}\nGot: {list(config.keys())}")

            print("✅ OIDC discovery endpoint valid")
            print(f"   Issuer: {config.get('issuer')}")
            print(f"   Token endpoint: {config.get('token_endpoint')}")

        except httpx.ConnectError as e:
            pytest.fail(f"Cannot connect to OIDC discovery endpoint: {e}")
        except Exception as e:
            pytest.fail(f"OIDC discovery failed: {e}")

    def test_keycloak_token_endpoint_functional(self):
        """
        DIAGNOSTIC: Verify token endpoint accepts requests.

        Tests that the token endpoint returns valid JSON responses
        (even error responses should be well-formed JSON).
        """
        import httpx

        if not _is_keycloak_container_running():
            pytest.skip("Keycloak container not running")

        token_url = "http://localhost/authn/realms/default/protocol/openid-connect/token"

        try:
            # Send an incomplete request - should get JSON error response
            response = httpx.post(
                token_url,
                data={"grant_type": "client_credentials"},
                timeout=10.0,
            )

            # Even errors should be JSON
            try:
                data = response.json()
                print("✅ Token endpoint returns valid JSON")
                print(f"   Status: {response.status_code}")
                if "error" in data:
                    print(f"   Error: {data.get('error')} (expected for incomplete request)")
            except Exception:
                pytest.fail(
                    f"Token endpoint did not return valid JSON.\n"
                    f"Status: {response.status_code}\n"
                    f"Response: {response.text[:500]}"
                )

        except httpx.ConnectError as e:
            pytest.fail(f"Cannot connect to token endpoint: {e}")

    def test_keycloak_admin_api_accessible(self):
        """
        DIAGNOSTIC: Verify Keycloak admin API is accessible.

        Tests admin authentication with default credentials (admin/admin).
        This is optional - some environments may have different admin credentials.
        """
        import httpx

        if not _is_keycloak_container_running():
            pytest.skip("Keycloak container not running")

        try:
            # Get admin token from master realm
            admin_password = os.getenv("KEYCLOAK_ADMIN_PASSWORD", "admin123")
            response = httpx.post(
                "http://localhost/authn/realms/master/protocol/openid-connect/token",
                data={
                    "grant_type": "password",
                    "client_id": "admin-cli",
                    "username": "admin",
                    "password": admin_password,
                },
                timeout=10.0,
            )

            if response.status_code == 200:
                print("✅ Keycloak admin API accessible")
            elif response.status_code == 401:
                pytest.skip("Keycloak admin credentials are invalid.\nThis is expected in production-like environments.")
            else:
                pytest.skip(f"Keycloak admin login returned {response.status_code}.\nResponse: {response.text[:200]}")

        except httpx.ConnectError:
            pytest.skip("Cannot connect to Keycloak admin API")


@pytest.mark.integration
@pytest.mark.xdist_group(name="keycloak_connectivity")
class TestKeycloakConnectivitySummary:
    """Summary test that reports overall Keycloak status."""

    def teardown_method(self) -> None:
        """Force GC to prevent mock accumulation in xdist workers."""
        gc.collect()

    def test_keycloak_connectivity_summary(self, keycloak_service_available):
        """
        SUMMARY: Report overall Keycloak connectivity status.

        This test uses the fixture to determine availability and provides
        a summary of the Keycloak service status.
        """
        if keycloak_service_available:
            print("\n" + "=" * 60)
            print("✅ KEYCLOAK CONNECTIVITY: HEALTHY")
            print("=" * 60)
            print("All dependent integration tests should be able to run.")
            print("=" * 60)
        else:
            print("\n" + "=" * 60)
            print("❌ KEYCLOAK CONNECTIVITY: NOT AVAILABLE")
            print("=" * 60)
            print("To start test infrastructure:")
            print("  make test-infra-up")
            print("")
            print("To check Keycloak logs:")
            print("  docker compose -f docker-compose.test.yml logs keycloak-test")
            print("=" * 60)
            pytest.skip("Keycloak not available - see diagnostics above")
