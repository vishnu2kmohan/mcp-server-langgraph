"""
Service Healthcheck Validation Tests.

TDD tests to ensure all services in docker-compose.test.yml have proper
healthchecks configured. Services with shell access should use HTTP endpoints
instead of just TCP port checks for better reliability.

Following TDD principles:
- RED: Tests will fail if services lack proper healthchecks
- GREEN: Tests will pass after improving healthcheck configurations
- REFACTOR: Provides confidence for healthcheck changes

Reference:
- https://docs.docker.com/engine/reference/builder/#healthcheck
"""

import gc
from pathlib import Path

import pytest
import yaml

from tests.helpers.path_helpers import get_repo_root

pytestmark = pytest.mark.integration

PROJECT_ROOT = get_repo_root()


def load_compose_config() -> dict:
    """Load docker-compose.test.yml configuration."""
    compose_file = PROJECT_ROOT / "docker-compose.test.yml"
    if not compose_file.exists():
        pytest.skip(f"Compose file not found: {compose_file}")

    with open(compose_file) as f:
        return yaml.safe_load(f)


def get_healthcheck_command(service_config: dict) -> str | None:
    """Extract healthcheck command as string from service config."""
    healthcheck = service_config.get("healthcheck", {})

    if healthcheck.get("disable"):
        return None

    test = healthcheck.get("test", [])
    if isinstance(test, list):
        return " ".join(test)
    return test


@pytest.mark.integration
@pytest.mark.xdist_group(name="service_healthchecks")
class TestServiceHealthcheckConfiguration:
    """Tests for service healthcheck configuration in docker-compose.test.yml."""

    def teardown_method(self) -> None:
        """Force GC to prevent mock accumulation in xdist workers."""
        gc.collect()

    def test_all_critical_services_have_healthchecks(self):
        """
        Test that all critical services have healthcheck configuration.

        Critical services are those that other services depend on.
        They must have either an enabled healthcheck or explicitly disabled.
        """
        config = load_compose_config()
        services = config.get("services", {})

        # Critical services that must have explicit healthcheck config
        critical_services = [
            "traefik-gateway",  # Traefik uses non-standard naming
            "postgres-test",
            "keycloak-test",
            "openfga-test",
            "redis-test",
            "mcp-server-test",
        ]

        missing_healthcheck = []
        for service_name in critical_services:
            service = services.get(service_name)
            if not service:
                missing_healthcheck.append(f"{service_name}: service not found")
                continue

            healthcheck = service.get("healthcheck")
            if not healthcheck:
                missing_healthcheck.append(f"{service_name}: no healthcheck config")

        assert not missing_healthcheck, (
            f"Critical services missing healthcheck configuration:\n"
            f"  {missing_healthcheck}\n\n"
            f"All critical services must have healthcheck config (enabled or disabled)"
        )

        print(f"✅ All {len(critical_services)} critical services have healthcheck config")

    def test_qdrant_uses_http_healthcheck(self):
        """
        Test that Qdrant uses HTTP health endpoint instead of TCP port check.

        RED phase: Will fail if Qdrant uses only TCP port check
        GREEN phase: Will pass after using /readyz or /livez endpoint

        Qdrant exposes:
        - /readyz - Readiness check
        - /livez - Liveness check

        TCP port checks only verify the socket is open, not that the service
        is actually ready to serve requests.
        """
        config = load_compose_config()
        qdrant_service = config.get("services", {}).get("qdrant-test")

        if not qdrant_service:
            pytest.skip("qdrant-test service not found")

        healthcheck_cmd = get_healthcheck_command(qdrant_service)

        if healthcheck_cmd is None:
            pytest.fail("qdrant-test has healthcheck disabled - should use HTTP endpoint")

        # Check for HTTP endpoint patterns
        http_patterns = [
            "/readyz",
            "/livez",
            "GET /",
            "HTTP/1",
        ]

        uses_http = any(pattern in healthcheck_cmd for pattern in http_patterns)

        # TCP-only patterns (less reliable)
        tcp_only_patterns = [
            "</dev/tcp/",
            "nc -z",
            "netcat",
        ]

        uses_tcp_only = any(pattern in healthcheck_cmd for pattern in tcp_only_patterns) and not uses_http

        assert uses_http, (
            f"🔴 RED: Qdrant uses TCP-only healthcheck, should use HTTP endpoint.\n\n"
            f"Current healthcheck:\n{healthcheck_cmd}\n\n"
            f"Why this matters:\n"
            f"  - TCP checks only verify port is open, not service is ready\n"
            f"  - Qdrant may accept connections before data is loaded\n\n"
            f"Qdrant health endpoints:\n"
            f"  - GET /readyz (returns 200 when ready)\n"
            f"  - GET /livez (returns 200 when alive)\n\n"
            f"Recommended fix (bash TCP + HTTP pattern):\n"
            f"  {{ printf 'GET /readyz HTTP/1.0\\r\\nHost: localhost\\r\\n\\r\\n' >&0; "
            f"grep -q 'HTTP/1.. 200'; }} 0<>/dev/tcp/localhost/6333"
        )

        print("✅ Qdrant uses HTTP health endpoint")

    def test_alloy_uses_http_healthcheck(self):
        """
        Test that Alloy uses HTTP ready endpoint instead of TCP port check.

        RED phase: Will fail if Alloy uses only TCP port check
        GREEN phase: Will pass after using /-/ready endpoint

        Alloy exposes:
        - /-/ready - Readiness check
        - /-/healthy - Health check

        TCP port checks only verify the socket is open, not that the collector
        is actually ready to receive telemetry.
        """
        config = load_compose_config()
        alloy_service = config.get("services", {}).get("alloy-test")

        if not alloy_service:
            pytest.skip("alloy-test service not found")

        healthcheck_cmd = get_healthcheck_command(alloy_service)

        if healthcheck_cmd is None:
            pytest.fail("alloy-test has healthcheck disabled - should use HTTP endpoint")

        # Check for HTTP endpoint patterns
        http_patterns = [
            "/-/ready",
            "/-/healthy",
            "GET /",
            "HTTP/1",
        ]

        uses_http = any(pattern in healthcheck_cmd for pattern in http_patterns)

        assert uses_http, (
            f"🔴 RED: Alloy uses TCP-only healthcheck, should use HTTP endpoint.\n\n"
            f"Current healthcheck:\n{healthcheck_cmd}\n\n"
            f"Why this matters:\n"
            f"  - TCP checks only verify port is open, not collector is ready\n"
            f"  - Alloy may accept connections before pipelines are configured\n\n"
            f"Alloy health endpoints:\n"
            f"  - GET /-/ready (returns 200 when ready)\n"
            f"  - GET /-/healthy (returns 200 when healthy)\n\n"
            f"Recommended fix (bash TCP + HTTP pattern):\n"
            f"  {{ printf 'GET /-/ready HTTP/1.0\\r\\nHost: localhost\\r\\n\\r\\n' >&0; "
            f"grep -q 'HTTP/1.. 200'; }} 0<>/dev/tcp/localhost/12345"
        )

        print("✅ Alloy uses HTTP health endpoint")

    def test_keycloak_uses_correct_path_prefix(self):
        """
        Test that Keycloak healthcheck uses /authn prefix for all endpoints.

        Keycloak is configured with KC_HTTP_RELATIVE_PATH=/authn which applies
        to ALL endpoints including health on management port 9000.
        """
        config = load_compose_config()
        keycloak_service = config.get("services", {}).get("keycloak-test")

        if not keycloak_service:
            pytest.skip("keycloak-test service not found")

        healthcheck_cmd = get_healthcheck_command(keycloak_service)

        if healthcheck_cmd is None:
            pytest.fail("keycloak-test has healthcheck disabled")

        # Keycloak with KC_HTTP_RELATIVE_PATH=/authn requires /authn prefix
        assert "/authn/health" in healthcheck_cmd, (
            f"Keycloak healthcheck missing /authn prefix.\n\n"
            f"Current command:\n{healthcheck_cmd}\n\n"
            f"KC_HTTP_RELATIVE_PATH=/authn applies to ALL endpoints including health.\n"
            f"Expected: /authn/health/ready instead of /health/ready"
        )

        print("✅ Keycloak healthcheck uses correct /authn prefix")

    def test_healthchecks_have_reasonable_timeouts(self):
        """
        Test that all healthchecks have reasonable timeout configurations.

        Docker healthcheck best practices:
        - interval >= timeout (avoid overlapping checks)
        - start_period for slow-starting services
        - retries > 1 for transient failures
        """
        config = load_compose_config()
        services = config.get("services", {})

        issues = []

        for service_name, service_config in services.items():
            healthcheck = service_config.get("healthcheck", {})

            if healthcheck.get("disable"):
                continue

            if "test" not in healthcheck:
                continue

            interval = healthcheck.get("interval", "30s")
            timeout = healthcheck.get("timeout", "30s")
            retries = healthcheck.get("retries", 1)

            # Parse duration strings
            def parse_duration(d: str) -> int:
                """Parse duration string to seconds."""
                if isinstance(d, int):
                    return d
                d = str(d).lower()
                if d.endswith("s"):
                    return int(d[:-1])
                if d.endswith("m"):
                    return int(d[:-1]) * 60
                return int(d)

            interval_s = parse_duration(interval)
            timeout_s = parse_duration(timeout)

            # Check interval >= timeout
            if interval_s < timeout_s:
                issues.append(
                    f"{service_name}: interval ({interval}) < timeout ({timeout})"
                )

            # Check retries > 0
            if retries < 1:
                issues.append(f"{service_name}: retries ({retries}) should be >= 1")

        assert not issues, (
            f"Healthcheck configuration issues found:\n"
            + "\n".join(f"  - {issue}" for issue in issues)
        )

        print(f"✅ All healthchecks have reasonable timeout configurations")

    def test_distroless_services_have_disabled_or_tcp_healthchecks(self):
        """
        Test that distroless services (no shell) have appropriate healthchecks.

        Services using distroless images cannot use shell-based healthchecks.
        They should either:
        - Have healthcheck disabled with clear documentation
        - Use native healthcheck binaries if available
        """
        config = load_compose_config()
        services = config.get("services", {})

        # Known distroless services
        distroless_services = [
            "loki-test",      # grafana/loki uses distroless
            "mimir-test",     # grafana/mimir uses distroless
        ]

        for service_name in distroless_services:
            service = services.get(service_name)
            if not service:
                continue

            healthcheck = service.get("healthcheck", {})
            healthcheck_cmd = get_healthcheck_command(service)

            if healthcheck_cmd is None:
                # Disabled is acceptable for distroless
                continue

            # Check for shell commands that won't work
            shell_patterns = ["bash", "sh -c", "CMD-SHELL", "/bin/sh"]
            uses_shell = any(pattern in healthcheck_cmd for pattern in shell_patterns)

            assert not uses_shell, (
                f"{service_name} uses distroless image but has shell-based healthcheck.\n\n"
                f"Current healthcheck:\n{healthcheck_cmd}\n\n"
                f"Distroless images don't have shell utilities.\n"
                f"Either disable healthcheck or use native binary."
            )

        print(f"✅ Distroless services have appropriate healthcheck configuration")


@pytest.mark.integration
@pytest.mark.xdist_group(name="service_healthchecks")
class TestKeycloakHealthcheckScript:
    """Tests for Keycloak healthcheck script configuration."""

    def teardown_method(self) -> None:
        """Force GC to prevent mock accumulation in xdist workers."""
        gc.collect()

    def test_keycloak_healthcheck_script_exists(self):
        """
        Test that the Keycloak healthcheck script exists.

        The script provides reusable two-phase OIDC-ready validation
        that can be used by both Docker image HEALTHCHECK and docker-compose.
        """
        script_path = PROJECT_ROOT / "docker" / "keycloak" / "healthcheck.sh"

        assert script_path.exists(), (
            f"Keycloak healthcheck script not found at {script_path}\n\n"
            f"Expected: docker/keycloak/healthcheck.sh\n"
            f"This script provides two-phase OIDC-ready healthcheck validation."
        )

        print("✅ Keycloak healthcheck script exists")

    def test_keycloak_healthcheck_script_is_executable(self):
        """
        Test that the healthcheck script has proper shebang and structure.
        """
        script_path = PROJECT_ROOT / "docker" / "keycloak" / "healthcheck.sh"

        if not script_path.exists():
            pytest.skip("Keycloak healthcheck script not found")

        with open(script_path) as f:
            content = f.read()

        # Check shebang
        assert content.startswith("#!/bin/bash"), (
            "Keycloak healthcheck script must start with #!/bin/bash"
        )

        # Check for two-phase validation
        assert "/health/ready" in content, (
            "Script must check /health/ready endpoint (Phase 1)"
        )

        assert "openid-configuration" in content, (
            "Script must check OIDC discovery endpoint (Phase 2)"
        )

        # Check for path prefix handling
        assert "PATH_PREFIX" in content or "KC_PATH_PREFIX" in content, (
            "Script must support configurable path prefix for KC_HTTP_RELATIVE_PATH"
        )

        print("✅ Keycloak healthcheck script has proper structure")

    def test_dockerfile_uses_healthcheck_script(self):
        """
        Test that Dockerfile.keycloak copies and uses the healthcheck script.
        """
        dockerfile_path = PROJECT_ROOT / "docker" / "Dockerfile.keycloak"

        if not dockerfile_path.exists():
            pytest.skip("Dockerfile.keycloak not found")

        with open(dockerfile_path) as f:
            content = f.read()

        # Check COPY instruction
        assert "healthcheck.sh" in content, (
            "Dockerfile.keycloak must COPY the healthcheck script"
        )

        # Check HEALTHCHECK instruction uses the script
        assert "/opt/keycloak/bin/healthcheck.sh" in content, (
            "Dockerfile HEALTHCHECK must use the healthcheck script"
        )

        print("✅ Dockerfile.keycloak uses healthcheck script")


@pytest.mark.integration
@pytest.mark.xdist_group(name="service_healthchecks")
class TestServiceHealthcheckLive:
    """
    Live tests for service healthchecks (require running infrastructure).

    These tests verify healthchecks actually work against running services.
    Skip these if infrastructure is not available.
    """

    def teardown_method(self) -> None:
        """Force GC to prevent mock accumulation in xdist workers."""
        gc.collect()

    @pytest.mark.skipif(
        not Path("/var/run/docker.sock").exists(),
        reason="Docker not available"
    )
    def test_qdrant_health_endpoint_responds(self):
        """
        Test that Qdrant /readyz endpoint responds when service is running.
        """
        import socket

        try:
            # Try to connect to Qdrant
            sock = socket.create_connection(("localhost", 6333), timeout=2)
            sock.close()
        except (socket.error, socket.timeout):
            pytest.skip("Qdrant not running on localhost:6333")

        import urllib.request
        import urllib.error

        try:
            response = urllib.request.urlopen("http://localhost:6333/readyz", timeout=5)
            assert response.status == 200, f"Qdrant /readyz returned {response.status}"
            print("✅ Qdrant /readyz endpoint responds with 200")
        except urllib.error.URLError as e:
            pytest.fail(f"Qdrant /readyz failed: {e}")

    @pytest.mark.skipif(
        not Path("/var/run/docker.sock").exists(),
        reason="Docker not available"
    )
    def test_alloy_ready_endpoint_responds(self):
        """
        Test that Alloy /-/ready endpoint responds when service is running.
        """
        import socket

        try:
            sock = socket.create_connection(("localhost", 12345), timeout=2)
            sock.close()
        except (socket.error, socket.timeout):
            pytest.skip("Alloy not running on localhost:12345")

        import urllib.request
        import urllib.error

        try:
            response = urllib.request.urlopen("http://localhost:12345/-/ready", timeout=5)
            assert response.status == 200, f"Alloy /-/ready returned {response.status}"
            print("✅ Alloy /-/ready endpoint responds with 200")
        except urllib.error.URLError as e:
            pytest.fail(f"Alloy /-/ready failed: {e}")
