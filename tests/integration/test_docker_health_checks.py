"""
Integration tests for Docker Compose health checks.

This test suite actually spins up containers and verifies health checks work.

Following TDD principles:
- RED: Tests will fail if health checks don't work
- GREEN: Tests will pass after fixing health check commands
- REFACTOR: Provides confidence that health checks work in real containers

Note: These are slower tests that require Docker to be running.
They are marked with @pytest.mark.integration for selective running.

Related Codex Finding: docker-compose.test.yml:214-233 Qdrant health check issue
"""

import gc
import os
import socket
import subprocess
import time
from pathlib import Path

import pytest
import yaml

from tests.fixtures.tool_fixtures import requires_tool

pytestmark = pytest.mark.integration

PROJECT_ROOT = Path(__file__).parent.parent.parent


def is_port_in_use(port: int, host: str = "127.0.0.1") -> bool:
    """
    Check if a port is already in use.

    CODEX FINDING FIX (2025-11-21): Port Conflict Detection
    ========================================================
    Prevents docker compose from failing with "port already allocated" error
    when health check tests try to start services on ports already used by
    main test infrastructure.

    Args:
        port: Port number to check
        host: Host to check (default: 127.0.0.1)

    Returns:
        True if port is in use, False otherwise
    """
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as sock:
        try:
            sock.bind((host, port))
            return False
        except OSError:
            return True


@pytest.fixture(scope="module")
@requires_tool("docker")
def docker_compose_available():
    """Check if docker-compose is available."""
    try:
        result = subprocess.run(
            ["docker", "compose", "version"],
            capture_output=True,
            text=True,
            timeout=30,
        )
        if result.returncode != 0:
            pytest.skip("docker compose not available")
        return True
    except (subprocess.TimeoutExpired, FileNotFoundError):
        pytest.skip("docker compose not available")


@pytest.fixture(scope="module")
@requires_tool("docker")
def docker_available():
    """Check if Docker daemon is available."""
    try:
        result = subprocess.run(
            ["docker", "info"],
            capture_output=True,
            text=True,
            timeout=30,
        )
        if result.returncode != 0:
            pytest.skip("Docker daemon not available")
        return True
    except (subprocess.TimeoutExpired, FileNotFoundError):
        pytest.skip("Docker daemon not available")


def run_docker_compose(
    compose_file: Path,
    *args: str,
    timeout: int = 30,
    env: dict | None = None,
) -> subprocess.CompletedProcess:
    """Run a docker-compose command."""
    cmd = ["docker", "compose", "-f", str(compose_file)] + list(args)

    # Merge environment variables
    process_env = os.environ.copy()
    if env:
        process_env.update(env)

    result = subprocess.run(
        cmd,
        capture_output=True,
        text=True,
        timeout=timeout,
        cwd=PROJECT_ROOT,
        env=process_env,
    )

    return result


def get_service_health(compose_file: Path, service_name: str, env: dict | None = None) -> str:
    """Get the health status of a service."""
    result = run_docker_compose(
        compose_file,
        "ps",
        "--format",
        "json",
        timeout=10,
        env=env,
    )

    if result.returncode != 0:
        return "unknown"

    # Parse JSON output
    import json

    try:
        containers = json.loads(result.stdout)
        if not isinstance(containers, list):
            containers = [containers]

        for container in containers:
            if container.get("Service") == service_name:
                health = container.get("Health", "")
                return health.lower()
    except (json.JSONDecodeError, ValueError):
        pass

    return "unknown"


def wait_for_health(
    compose_file: Path,
    service_name: str,
    timeout: int = 120,
    check_interval: int = 2,
    env: dict | None = None,
) -> bool:
    """
    Wait for a service to become healthy.

    Args:
        compose_file: Path to docker-compose file
        service_name: Name of service to check
        timeout: Maximum wait time in seconds
        check_interval: Seconds between health checks
        env: Optional environment variables (for COMPOSE_PROJECT_NAME isolation)

    Returns:
        True if service became healthy, False if timeout
    """
    start_time = time.time()

    while time.time() - start_time < timeout:
        health = get_service_health(compose_file, service_name, env=env)

        if health == "healthy":
            return True

        if health in ["unhealthy", "failed"]:
            # Health check is failing - stop waiting
            return False

        time.sleep(check_interval)

    return False


@pytest.mark.integration
@pytest.mark.slow
@pytest.mark.xdist_group(name="testdockercomposehealthchecksintegration")
class TestDockerComposeHealthChecksIntegration:
    """Integration tests for Docker Compose health checks."""

    def teardown_method(self) -> None:
        """Force GC to prevent mock accumulation in xdist workers"""
        gc.collect()

    @pytest.fixture
    def cleanup_containers(self):
        """Cleanup containers after test."""
        yield
        # Cleanup happens after test

    def test_keycloak_health_check_no_curl_dependency(self, docker_available, docker_compose_available):
        """
        Test that Keycloak health check does not depend on curl/wget.

        RED phase: Will fail if health check uses 'curl' (not available in Keycloak 26.4.2)
        GREEN phase: Will pass after switching to bash /dev/tcp check

        Codex Finding: docker-compose.test.yml:143 - Keycloak health check uses curl
        Issue: exec: "curl": executable file not found in $PATH
        """
        compose_file = PROJECT_ROOT / "docker" / "docker-compose.test.yml"

        if not compose_file.exists():
            pytest.skip(f"Compose file not found: {compose_file}")

        # Read compose file
        with open(compose_file) as f:
            import yaml

            config = yaml.safe_load(f)

        keycloak_service = config.get("services", {}).get("keycloak-test")
        if not keycloak_service:
            pytest.skip("Keycloak service (keycloak-test) not found in docker-compose.test.yml")

        health_check = keycloak_service.get("healthcheck", {})
        assert health_check, "Keycloak service must have healthcheck configuration"

        health_check_cmd = health_check.get("test", [])
        assert health_check_cmd, "Keycloak healthcheck must have test command"

        # Join command parts for inspection
        full_command = " ".join(health_check_cmd) if isinstance(health_check_cmd, list) else health_check_cmd

        # CRITICAL: Keycloak 26.4.2 does NOT include curl or wget
        forbidden_commands = ["curl", "wget"]
        for cmd in forbidden_commands:
            assert cmd not in full_command, (
                f"RED: Keycloak health check uses '{cmd}' which is NOT available in the image.\n"
                f"Health check command: {full_command}\n\n"
                f"Keycloak 26.4.2 image does not include curl or wget.\n"
                f"Use bash with /dev/tcp for connectivity checks instead.\n\n"
                f"Example fix:\n"
                f'  test: ["CMD-SHELL", "timeout 5 bash -c \'</dev/tcp/localhost/8080\' || exit 1"]'
            )

        # Should use built-in shell features
        assert any(keyword in full_command.lower() for keyword in ["bash", "sh", "/dev/tcp", "timeout"]), (
            f"Keycloak health check should use built-in shell features.\n"
            f"Current command: {full_command}\n"
            f"Recommended: Use bash with /dev/tcp or other built-in commands."
        )

        print(f"PASS: Keycloak health check correctly uses built-in commands: {full_command}")

    @pytest.mark.timeout(150)  # Override global 60s timeout - Qdrant needs up to 120s to become healthy
    def test_qdrant_health_check_works(self, docker_available, docker_compose_available, cleanup_containers):
        """
        Test that Qdrant container health check works correctly.

        CODEX FINDING FIX (2025-11-20): Use isolated test infrastructure to prevent
        tearing down shared containers. Previous issue: 'docker compose down -v' stopped
        PostgreSQL/Redis/etc, causing subsequent tests to fail with connection errors.

        Solution: Use unique COMPOSE_PROJECT_NAME for test-specific isolation.

        RED phase: Will fail if using wget (command not found)
        GREEN phase: Will pass after switching to grpc_health_probe

        This is the integration test for the Codex finding.

        Note: Requires extended timeout (150s) as Qdrant can take up to 120s to become healthy
        in CI environments with limited resources.
        """
        import os
        import uuid

        # CODEX FINDING FIX (2025-11-21): Port Conflict Resolution
        # ========================================================
        # Check if Qdrant test port is already in use before starting service
        # Prevents "Bind ... port 9333 already allocated" error when main test
        # infrastructure already has Qdrant running
        QDRANT_TEST_PORT = 9333  # From docker-compose.test.yml:242
        if is_port_in_use(QDRANT_TEST_PORT):
            pytest.skip(
                f"Qdrant test port {QDRANT_TEST_PORT} already in use. "
                f"This likely means main test infrastructure is running. "
                f"Stop existing containers or run this test in isolation."
            )

        compose_file = PROJECT_ROOT / "docker-compose.test.yml"

        if not compose_file.exists():
            pytest.skip(f"Compose file not found: {compose_file}")

        # Read compose file to find Qdrant service name
        with open(compose_file) as f:
            config = yaml.safe_load(f)

        qdrant_services = [
            name for name, service in config.get("services", {}).items() if "qdrant" in service.get("image", "").lower()
        ]

        if not qdrant_services:
            pytest.skip("No Qdrant service found in docker-compose.test.yml")

        qdrant_service = qdrant_services[0]

        # Use unique project name for isolated test infrastructure
        # This prevents 'docker compose down' from affecting shared test infrastructure
        unique_project_name = f"health-check-test-{uuid.uuid4().hex[:8]}"
        test_env = os.environ.copy()
        test_env["COMPOSE_PROJECT_NAME"] = unique_project_name

        print(f"\n🐳 Starting {qdrant_service} in isolated project '{unique_project_name}'...")

        # Start only the Qdrant service (no dependencies) with isolated project name
        result = run_docker_compose(
            compose_file,
            "up",
            "-d",
            qdrant_service,
            timeout=60,
            env=test_env,
        )

        if result.returncode != 0:
            pytest.fail(f"Failed to start {qdrant_service}:\nstdout: {result.stdout}\nstderr: {result.stderr}")

        try:
            # Wait for health check to pass (using isolated environment)
            print(f"⏳ Waiting for {qdrant_service} to become healthy (max 120s)...")

            is_healthy = wait_for_health(
                compose_file,
                qdrant_service,
                timeout=120,
                check_interval=3,
                env=test_env,
            )

            # Get final health status (using isolated environment)
            final_health = get_service_health(compose_file, qdrant_service, env=test_env)

            # Get container logs for debugging (using isolated environment)
            logs_result = run_docker_compose(
                compose_file,
                "logs",
                qdrant_service,
                timeout=10,
                env=test_env,
            )

            assert is_healthy, (
                f"🔴 RED: {qdrant_service} did not become healthy within 120 seconds.\n"
                f"Final health status: {final_health}\n\n"
                f"This likely means the health check command is failing.\n\n"
                f"Container logs:\n{logs_result.stdout}\n\n"
                f"Common causes:\n"
                f"  - Health check uses 'wget' but image doesn't have it (Codex finding)\n"
                f"  - Health check uses 'curl' but image doesn't have it\n"
                f"  - Wrong port in health check\n"
                f"  - Service not starting properly\n\n"
                f"Current configuration (as of 2025-11-20):\n"
                f"  - docker-compose.test.yml: timeout 2 bash -c '</dev/tcp/localhost/6333'\n"
                f"  - conftest.py: HTTP check http://localhost:9333/readyz\n"
                f"  - Production: /healthz (startup), /livez (liveness), /readyz (readiness)\n"
                f"  - Qdrant version: v1.15.5 (latest stable)"
            )

            print(f"✅ {qdrant_service} is healthy!")

        finally:
            # Cleanup: Stop and remove containers from isolated project
            # CODEX FINDING FIX (2025-11-20): Removed hard-coded container names from docker-compose.test.yml
            # This allows multiple isolated projects to run simultaneously without conflicts.
            # Note: Using 'down' without '-v' to avoid interfering with shared network (mcp-test-network)
            # since all storage is tmpfs-based anyway (no volumes to clean up).
            #
            # CODEX FINDING FIX (2025-11-21): Docker Health-Check Teardown Interference
            # ==========================================================================
            # Previous: Used 'docker compose down --remove-orphans'
            # Problem: --remove-orphans flag can remove containers from shared network
            #          (mcp-test-network), causing 8+ tests to fail with connection errors
            # Fix: Remove --remove-orphans flag from cleanup command
            #
            # Root Cause: Even with isolated COMPOSE_PROJECT_NAME, --remove-orphans
            #             traverses the shared network and may stop unrelated containers
            #
            # Prevention: Added @pytest.mark.xdist_group to isolate health check tests
            print(f"\n🧹 Cleaning up isolated project '{unique_project_name}'...")
            cleanup_result = run_docker_compose(
                compose_file,
                "down",
                # Removed: "--remove-orphans" - causes interference with main test infrastructure
                timeout=30,
                env=test_env,
            )

            if cleanup_result.returncode != 0:
                print(f"Warning: Cleanup had issues:\n{cleanup_result.stderr}")

    @pytest.mark.timeout(150)  # Override global 60s timeout - Postgres may need up to 90s to become healthy
    def test_minimal_compose_health_checks(self, docker_available, docker_compose_available, cleanup_containers):
        """
        Test health checks in docker-compose.minimal.yml if it exists.

        This ensures minimal/production configurations also have working health checks.

        Timeout Note: Test waits up to 90s for service health (line 447), so pytest timeout
        must be > 90s to avoid premature termination. Set to 150s for safety margin.

        CODEX FINDING FIX (2025-11-24): Added port conflict detection and project isolation
        to prevent failures when main test infrastructure is already running.
        """
        import uuid

        compose_file = PROJECT_ROOT / "docker-compose.minimal.yml"

        if not compose_file.exists():
            pytest.skip(f"Compose file not found: {compose_file}")

        # Read compose file
        with open(compose_file) as f:
            config = yaml.safe_load(f)

        services_with_health_checks = [
            name for name, service in config.get("services", {}).items() if "healthcheck" in service
        ]

        if not services_with_health_checks:
            pytest.skip("No services with health checks in docker-compose.minimal.yml")

        # Test first service with health check
        service_name = services_with_health_checks[0]

        # CODEX FINDING FIX (2025-11-24): Port Conflict Detection
        # Check if common ports used by minimal compose are already in use
        # Prevents "port already allocated" errors when test infrastructure is running
        POSTGRES_PORT = 5432  # From docker-compose.minimal.yml
        REDIS_PORT = 6379  # From docker-compose.minimal.yml
        if is_port_in_use(POSTGRES_PORT) or is_port_in_use(REDIS_PORT):
            pytest.skip(
                f"Ports {POSTGRES_PORT} or {REDIS_PORT} already in use. "
                f"Cannot run minimal compose health check test in parallel with other infrastructure."
            )

        # CODEX FINDING FIX (2025-11-24): Isolated project name
        # Prevents interference with main test infrastructure during cleanup
        unique_project_name = f"minimal-health-test-{uuid.uuid4().hex[:8]}"
        test_env = os.environ.copy()
        test_env["COMPOSE_PROJECT_NAME"] = unique_project_name

        print(f"\n🐳 Starting {service_name} in isolated project '{unique_project_name}'...")
        result = run_docker_compose(
            compose_file,
            "up",
            "-d",
            service_name,
            timeout=60,
            env=test_env,
        )

        if result.returncode != 0:
            pytest.fail(f"Failed to start {service_name}:\nstdout: {result.stdout}\nstderr: {result.stderr}")

        try:
            print(f"⏳ Waiting for {service_name} to become healthy...")
            is_healthy = wait_for_health(compose_file, service_name, timeout=90, env=test_env)

            final_health = get_service_health(compose_file, service_name, env=test_env)

            assert is_healthy, (
                f"{service_name} did not become healthy. "
                f"Final status: {final_health}. "
                f"Check health check command is available in the image."
            )

            print(f"✅ {service_name} is healthy!")

        finally:
            # CODEX FINDING FIX (2025-11-21): Docker Health-Check Teardown Interference
            # See test_qdrant_health_check_works for detailed explanation
            print(f"\n🧹 Cleaning up isolated project '{unique_project_name}'...")
            run_docker_compose(
                compose_file,
                "down",
                # Removed: "--remove-orphans" - causes interference with main test infrastructure
                timeout=30,
                env=test_env,
            )


@pytest.mark.integration
@requires_tool("docker")
def test_health_check_command_availability(docker_available):
    """
    Test that common health check commands are available in their respective images.

    This test verifies the commands we use in health checks actually exist in the images.
    """
    # Define image -> command mappings we want to verify
    test_cases = [
        {
            "image": "qdrant/qdrant:v1.15.1",
            "command": "/usr/local/bin/grpc_health_probe",
            "should_exist": False,
            "description": "Qdrant v1.15+ doesn't include grpc_health_probe (uses TCP check instead)",
        },
        {
            "image": "qdrant/qdrant:v1.15.1",
            "command": "bash",
            "should_exist": True,
            "description": "Qdrant should have bash for TCP health check",
        },
        {
            "image": "qdrant/qdrant:v1.15.1",
            "command": "wget",
            "should_exist": False,
            "description": "Qdrant v1.15+ removed wget (security hardening)",
        },
        {
            "image": "qdrant/qdrant:v1.15.1",
            "command": "curl",
            "should_exist": False,
            "description": "Qdrant v1.15+ removed curl (security hardening)",
        },
    ]

    results = []

    for test_case in test_cases:
        image = test_case["image"]
        command = test_case["command"]
        should_exist = test_case["should_exist"]
        description = test_case["description"]

        # Check if command exists in image
        try:
            result = subprocess.run(
                [
                    "docker",
                    "run",
                    "--rm",
                    "--entrypoint",
                    "/bin/sh",
                    image,
                    "-c",
                    f"which {command} || command -v {command}",
                ],
                capture_output=True,
                text=True,
                timeout=30,
            )

            command_exists = result.returncode == 0

            if should_exist and not command_exists:
                results.append(f"❌ {description}\n   Image: {image}\n   Expected '{command}' to exist but it doesn't")
            elif not should_exist and command_exists:
                results.append(f"⚠️  {description}\n   Image: {image}\n   Expected '{command}' NOT to exist but it does")
            else:
                print(f"✅ {description}")

        except subprocess.TimeoutExpired:
            results.append(f"⏱️  Timeout checking {command} in {image}")
        except Exception as e:
            results.append(f"❌ Error checking {command} in {image}: {e}")

    if results:
        pytest.fail("\n🔴 Health check command availability issues:\n\n" + "\n\n".join(results))
