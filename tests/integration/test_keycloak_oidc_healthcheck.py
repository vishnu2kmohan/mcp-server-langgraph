"""
Integration tests for Keycloak OIDC-aware healthcheck.

This test suite verifies that the Keycloak healthcheck in docker-compose.test.yml
validates not just the management health endpoint, but also the OIDC discovery
endpoint to ensure dependent services (OpenFGA, traefik-forward-auth) can obtain
valid OIDC configuration.

Following TDD principles:
- RED: Tests will fail if healthcheck only checks /health/ready
- GREEN: Tests will pass after adding OIDC discovery validation
- REFACTOR: Provides confidence that OIDC-dependent services won't start too early

Reference:
- https://www.keycloak.org/observability/health
- https://www.keycloak.org/server/containers
"""

import gc

import pytest
import yaml

from tests.helpers.path_helpers import get_repo_root

pytestmark = pytest.mark.integration

PROJECT_ROOT = get_repo_root()


@pytest.mark.integration
@pytest.mark.xdist_group(name="keycloak_oidc_healthcheck")
class TestKeycloakOIDCHealthcheck:
    """Tests for Keycloak OIDC-aware healthcheck configuration."""

    def teardown_method(self) -> None:
        """Force GC to prevent mock accumulation in xdist workers."""
        gc.collect()

    def test_keycloak_healthcheck_validates_oidc_discovery_endpoint(self):
        """
        Test that Keycloak healthcheck validates OIDC discovery endpoint.

        RED phase: Will fail if healthcheck only checks /health/ready on port 9000
        GREEN phase: Will pass after adding OIDC discovery endpoint validation

        The OIDC discovery endpoint is:
        http://localhost:8080/authn/realms/default/.well-known/openid-configuration

        Dependent services (OpenFGA, traefik-forward-auth) require this endpoint
        to be available before they can obtain valid OIDC configuration.
        """
        compose_file = PROJECT_ROOT / "docker-compose.test.yml"

        if not compose_file.exists():
            pytest.skip(f"Compose file not found: {compose_file}")

        with open(compose_file) as f:
            config = yaml.safe_load(f)

        keycloak_service = config.get("services", {}).get("keycloak-test")
        assert keycloak_service, "keycloak-test service not found in docker-compose.test.yml"

        healthcheck = keycloak_service.get("healthcheck", {})
        assert healthcheck, "keycloak-test must have healthcheck configuration"

        healthcheck_test = healthcheck.get("test", [])
        assert healthcheck_test, "keycloak-test healthcheck must have test command"

        # Join command parts for inspection
        full_command = " ".join(healthcheck_test) if isinstance(healthcheck_test, list) else healthcheck_test

        # CRITICAL: Healthcheck must validate OIDC discovery endpoint
        oidc_patterns = [
            ".well-known/openid-configuration",
            "openid-configuration",
            "/authn/realms/",
        ]

        has_oidc_check = any(pattern in full_command for pattern in oidc_patterns)

        assert has_oidc_check, (
            f"🔴 RED: Keycloak healthcheck does NOT validate OIDC discovery endpoint.\n\n"
            f"Current healthcheck command:\n{full_command}\n\n"
            f"Why this matters:\n"
            f"  - OpenFGA, traefik-forward-auth depend on OIDC configuration\n"
            f"  - /health/ready only confirms JVM is ready, not that OIDC works\n"
            f"  - Services may start before OIDC endpoints are available\n\n"
            f"Expected: Healthcheck should validate one of:\n"
            f"  - /authn/realms/default/.well-known/openid-configuration (port 8080)\n"
            f"  - Or equivalent OIDC discovery endpoint\n\n"
            f"Recommended fix: Add two-phase healthcheck:\n"
            f"  1. /authn/health/ready on port 9000 (JVM ready)\n"
            f"  2. OIDC discovery on port 8080 (OIDC ready)\n"
            f"\n"
            f"NOTE: KC_HTTP_RELATIVE_PATH=/authn applies to ALL endpoints including health"
        )

        print("✅ Keycloak healthcheck correctly validates OIDC endpoint")
        print(f"Command: {full_command}")

    def test_keycloak_healthcheck_does_not_use_curl_or_wget(self):
        """
        Test that Keycloak healthcheck does not use curl or wget.

        Keycloak 26+ images do not include curl or wget (security hardening).
        The healthcheck must use bash with /dev/tcp or other built-in commands.

        Reference: https://www.keycloak.org/server/containers
        """
        compose_file = PROJECT_ROOT / "docker-compose.test.yml"

        if not compose_file.exists():
            pytest.skip(f"Compose file not found: {compose_file}")

        with open(compose_file) as f:
            config = yaml.safe_load(f)

        keycloak_service = config.get("services", {}).get("keycloak-test")
        assert keycloak_service, "keycloak-test service not found in docker-compose.test.yml"

        healthcheck = keycloak_service.get("healthcheck", {})
        healthcheck_test = healthcheck.get("test", [])
        full_command = " ".join(healthcheck_test) if isinstance(healthcheck_test, list) else healthcheck_test

        # CRITICAL: curl and wget are NOT available in Keycloak 26+ images
        forbidden_commands = ["curl ", "wget "]
        for cmd in forbidden_commands:
            assert cmd not in full_command, (
                f"🔴 RED: Keycloak healthcheck uses '{cmd.strip()}' which is NOT available.\n\n"
                f"Current command: {full_command}\n\n"
                f"Keycloak 26+ images do not include curl or wget.\n"
                f"Use bash with /dev/tcp for health checks instead.\n\n"
                f"Recommended:\n"
                f"  {{ printf 'HEAD /authn/health/ready HTTP/1.0\\r\\n\\r\\n' >&0; grep 'HTTP/1.0 200'; }} "
                f"0<>/dev/tcp/localhost/9000\n\n"
                f"NOTE: KC_HTTP_RELATIVE_PATH=/authn applies to ALL endpoints including health"
            )

        print("✅ Keycloak healthcheck correctly avoids curl/wget")

    def test_keycloak_healthcheck_validates_http_response(self):
        """
        Test that Keycloak healthcheck validates the HTTP response code.

        A proper healthcheck should not just check if the port is open, but
        also verify that the HTTP response is successful (200 OK).

        The official Keycloak recommendation:
        { printf 'HEAD /health/ready HTTP/1.0\\r\\n\\r\\n' >&0; grep 'HTTP/1.0 200'; } 0<>/dev/tcp/localhost/9000
        """
        compose_file = PROJECT_ROOT / "docker-compose.test.yml"

        if not compose_file.exists():
            pytest.skip(f"Compose file not found: {compose_file}")

        with open(compose_file) as f:
            config = yaml.safe_load(f)

        keycloak_service = config.get("services", {}).get("keycloak-test")
        assert keycloak_service, "keycloak-test service not found"

        healthcheck = keycloak_service.get("healthcheck", {})
        healthcheck_test = healthcheck.get("test", [])
        full_command = " ".join(healthcheck_test) if isinstance(healthcheck_test, list) else healthcheck_test

        # Check for response validation patterns
        response_validation_patterns = [
            "grep",
            "200",
            "HTTP/1",
            "issuer",  # OIDC discovery response contains "issuer"
        ]

        has_response_validation = any(pattern in full_command for pattern in response_validation_patterns)

        assert has_response_validation, (
            f"🔴 RED: Keycloak healthcheck does NOT validate HTTP response.\n\n"
            f"Current command: {full_command}\n\n"
            f"A port-open check is not sufficient. The healthcheck should:\n"
            f"  1. Send an HTTP request\n"
            f"  2. Read the response\n"
            f"  3. Verify it contains '200' or expected content\n\n"
            f"Recommended:\n"
            f"  {{ printf 'HEAD /authn/health/ready HTTP/1.0\\r\\n\\r\\n' >&0; grep 'HTTP/1.0 200'; }} "
            f"0<>/dev/tcp/localhost/9000\n\n"
            f"NOTE: KC_HTTP_RELATIVE_PATH=/authn applies to ALL endpoints including health"
        )

        print("✅ Keycloak healthcheck correctly validates HTTP response")


@pytest.mark.integration
@pytest.mark.xdist_group(name="keycloak_oidc_healthcheck")
class TestKeycloakDockerfileHealthcheck:
    """Tests for Keycloak Dockerfile HEALTHCHECK instruction."""

    def teardown_method(self) -> None:
        """Force GC to prevent mock accumulation in xdist workers."""
        gc.collect()

    def test_dockerfile_healthcheck_does_not_use_curl(self):
        """
        Test that docker/Dockerfile.keycloak does not use curl in HEALTHCHECK.

        Keycloak 26+ images do not include curl. The HEALTHCHECK instruction
        should use bash with /dev/tcp instead.
        """
        dockerfile = PROJECT_ROOT / "docker" / "Dockerfile.keycloak"

        if not dockerfile.exists():
            pytest.skip(f"Dockerfile not found: {dockerfile}")

        with open(dockerfile) as f:
            content = f.read()

        # Find HEALTHCHECK instruction
        lines = content.split("\n")
        healthcheck_lines = []
        in_healthcheck = False

        for line in lines:
            if line.strip().startswith("HEALTHCHECK"):
                in_healthcheck = True
            if in_healthcheck:
                healthcheck_lines.append(line)
                # HEALTHCHECK ends when CMD is complete (no line continuation)
                if line.strip() and not line.strip().endswith("\\"):
                    break

        healthcheck_instruction = " ".join(healthcheck_lines)

        # CRITICAL: curl is NOT available in Keycloak 26+ images
        assert "curl" not in healthcheck_instruction.lower(), (
            f"🔴 RED: Dockerfile HEALTHCHECK uses curl which is NOT available.\n\n"
            f"Current instruction:\n{healthcheck_instruction}\n\n"
            f"Keycloak 26+ images do not include curl.\n"
            f"Use bash with /dev/tcp for health checks instead.\n\n"
            f"Recommended:\n"
            f"HEALTHCHECK --interval=30s --timeout=10s --start-period=60s --retries=3 \\\n"
            f"    CMD {{ printf 'HEAD /authn/health/ready HTTP/1.0\\r\\n\\r\\n' >&0; grep -q 'HTTP/1.0 200'; }} "
            f"0<>/dev/tcp/localhost/9000\n\n"
            f"NOTE: KC_HTTP_RELATIVE_PATH=/authn applies to ALL endpoints including health"
        )

        print("✅ Dockerfile HEALTHCHECK correctly avoids curl")


@pytest.mark.integration
@pytest.mark.requires_infra
@pytest.mark.xdist_group(name="keycloak_oidc_healthcheck_live")
class TestKeycloakHealthcheckLive:
    """
    Live healthcheck verification tests.

    These tests run the actual healthcheck commands against a running Keycloak container.
    They require test infrastructure to be running (make test-infra-up).

    Marked with @pytest.mark.requires_infra to skip when infrastructure is not available.
    """

    def teardown_method(self) -> None:
        """Force GC to prevent mock accumulation in xdist workers."""
        gc.collect()

    @staticmethod
    def _is_keycloak_running() -> bool:
        """Check if Keycloak container is running."""
        import subprocess

        try:
            result = subprocess.run(
                ["docker", "ps", "--filter", "name=keycloak-test", "--format", "{{.Names}}"],
                capture_output=True,
                text=True,
                timeout=5,
            )
            return "keycloak-test" in result.stdout
        except (subprocess.SubprocessError, FileNotFoundError):
            return False

    def test_keycloak_healthcheck_phase1_passes_live(self):
        """
        Test that Phase 1 healthcheck (JVM ready) passes against running Keycloak.

        Phase 1 validates /authn/health/ready on management port 9000.
        This confirms the JVM and database connections are ready.
        """
        import subprocess
        import time

        if not self._is_keycloak_running():
            pytest.skip("Keycloak container not running (run 'make test-infra-up' first)")

        # Find the actual container name
        result = subprocess.run(
            ["docker", "ps", "--filter", "name=keycloak-test", "--format", "{{.Names}}"],
            capture_output=True,
            text=True,
            timeout=5,
        )
        container_name = result.stdout.strip().split("\n")[0]

        if not container_name:
            pytest.skip("Could not find Keycloak container")

        # Run Phase 1 healthcheck
        start_time = time.time()
        result = subprocess.run(
            [
                "docker",
                "exec",
                container_name,
                "bash",
                "-c",
                "{ printf 'HEAD /authn/health/ready HTTP/1.0\\r\\nHost: localhost\\r\\n\\r\\n' >&0; grep -q 'HTTP/1.0 200'; } 0<>/dev/tcp/localhost/9000",
            ],
            capture_output=True,
            text=True,
            timeout=10,
        )
        elapsed = time.time() - start_time

        assert result.returncode == 0, (
            f"Phase 1 healthcheck FAILED\n"
            f"Exit code: {result.returncode}\n"
            f"Stdout: {result.stdout}\n"
            f"Stderr: {result.stderr}\n"
            f"Elapsed: {elapsed:.2f}s"
        )

        print(f"✅ Phase 1 healthcheck passed in {elapsed:.2f}s")

    def test_keycloak_healthcheck_phase2_oidc_passes_live(self):
        """
        Test that Phase 2 healthcheck (OIDC discovery) passes against running Keycloak.

        Phase 2 validates the OIDC discovery endpoint on HTTP port 8080.
        This confirms OIDC is fully functional for dependent services.
        """
        import subprocess
        import time

        if not self._is_keycloak_running():
            pytest.skip("Keycloak container not running (run 'make test-infra-up' first)")

        # Find the actual container name
        result = subprocess.run(
            ["docker", "ps", "--filter", "name=keycloak-test", "--format", "{{.Names}}"],
            capture_output=True,
            text=True,
            timeout=5,
        )
        container_name = result.stdout.strip().split("\n")[0]

        if not container_name:
            pytest.skip("Could not find Keycloak container")

        # Run Phase 2 healthcheck
        start_time = time.time()
        result = subprocess.run(
            [
                "docker",
                "exec",
                container_name,
                "bash",
                "-c",
                '{ printf "GET /authn/realms/default/.well-known/openid-configuration HTTP/1.0\\r\\nHost: localhost\\r\\n\\r\\n" >&0; grep -q \'"issuer"\'; } 0<>/dev/tcp/localhost/8080',
            ],
            capture_output=True,
            text=True,
            timeout=10,
        )
        elapsed = time.time() - start_time

        assert result.returncode == 0, (
            f"Phase 2 healthcheck (OIDC) FAILED\n"
            f"Exit code: {result.returncode}\n"
            f"Stdout: {result.stdout}\n"
            f"Stderr: {result.stderr}\n"
            f"Elapsed: {elapsed:.2f}s"
        )

        print(f"✅ Phase 2 healthcheck (OIDC) passed in {elapsed:.2f}s")

    def test_keycloak_healthcheck_completes_within_timeout(self):
        """
        Test that the full healthcheck completes well within the configured timeout.

        The docker-compose.test.yml configures timeout: 10s for the healthcheck.
        Both phases should complete in under 5s to provide margin for network latency.
        """
        import subprocess
        import time

        if not self._is_keycloak_running():
            pytest.skip("Keycloak container not running (run 'make test-infra-up' first)")

        # Find the actual container name
        result = subprocess.run(
            ["docker", "ps", "--filter", "name=keycloak-test", "--format", "{{.Names}}"],
            capture_output=True,
            text=True,
            timeout=5,
        )
        container_name = result.stdout.strip().split("\n")[0]

        if not container_name:
            pytest.skip("Could not find Keycloak container")

        # Run full two-phase healthcheck
        start_time = time.time()
        result = subprocess.run(
            [
                "docker",
                "exec",
                container_name,
                "bash",
                "-c",
                """
                { printf 'HEAD /authn/health/ready HTTP/1.0\r\nHost: localhost\r\n\r\n' >&0; grep -q 'HTTP/1.0 200'; } 0<>/dev/tcp/localhost/9000 || exit 1
                { printf 'GET /authn/realms/default/.well-known/openid-configuration HTTP/1.0\r\nHost: localhost\r\n\r\n' >&0; grep -q '"issuer"'; } 0<>/dev/tcp/localhost/8080 || exit 1
                """,
            ],
            capture_output=True,
            text=True,
            timeout=10,
        )
        elapsed = time.time() - start_time

        # Should complete well within the 10s timeout
        max_allowed = 5.0  # 5 seconds provides 50% margin

        assert result.returncode == 0, f"Healthcheck failed: {result.stderr}"
        assert elapsed < max_allowed, (
            f"Healthcheck took {elapsed:.2f}s, exceeds {max_allowed}s threshold.\n"
            f"This may cause timeouts in production. Consider optimizing Keycloak startup."
        )

        print(f"✅ Full healthcheck completed in {elapsed:.2f}s (threshold: {max_allowed}s)")
