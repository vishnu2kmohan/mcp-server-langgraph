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

import os
import subprocess
import time
from pathlib import Path
from typing import List, Optional

import pytest
import yaml

PROJECT_ROOT = Path(__file__).parent.parent.parent


@pytest.fixture(scope="module")
def docker_compose_available():
    """Check if docker-compose is available."""
    try:
        result = subprocess.run(
            ["docker", "compose", "version"],
            capture_output=True,
            text=True,
            timeout=5,
        )
        if result.returncode != 0:
            pytest.skip("docker compose not available")
        return True
    except (subprocess.TimeoutExpired, FileNotFoundError):
        pytest.skip("docker compose not available")


@pytest.fixture(scope="module")
def docker_available():
    """Check if Docker daemon is available."""
    try:
        result = subprocess.run(
            ["docker", "info"],
            capture_output=True,
            text=True,
            timeout=5,
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
    env: Optional[dict] = None,
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


def get_service_health(compose_file: Path, service_name: str) -> str:
    """Get the health status of a service."""
    result = run_docker_compose(
        compose_file,
        "ps",
        "--format",
        "json",
        timeout=10,
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
) -> bool:
    """
    Wait for a service to become healthy.

    Returns:
        True if service became healthy, False if timeout
    """
    start_time = time.time()

    while time.time() - start_time < timeout:
        health = get_service_health(compose_file, service_name)

        if health == "healthy":
            return True

        if health in ["unhealthy", "failed"]:
            # Health check is failing - stop waiting
            return False

        time.sleep(check_interval)

    return False


@pytest.mark.integration
@pytest.mark.slow
class TestDockerComposeHealthChecksIntegration:
    """Integration tests for Docker Compose health checks."""

    @pytest.fixture
    def cleanup_containers(self):
        """Cleanup containers after test."""
        yield
        # Cleanup happens after test

    def test_qdrant_health_check_works(self, docker_available, docker_compose_available, cleanup_containers):
        """
        Test that Qdrant container health check works correctly.

        RED phase: Will fail if using wget (command not found)
        GREEN phase: Will pass after switching to grpc_health_probe

        This is the integration test for the Codex finding.
        """
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

        # Start only the Qdrant service (no dependencies)
        print(f"\n🐳 Starting {qdrant_service} service...")
        result = run_docker_compose(
            compose_file,
            "up",
            "-d",
            qdrant_service,
            timeout=60,
        )

        if result.returncode != 0:
            pytest.fail(f"Failed to start {qdrant_service}:\n" f"stdout: {result.stdout}\n" f"stderr: {result.stderr}")

        try:
            # Wait for health check to pass
            print(f"⏳ Waiting for {qdrant_service} to become healthy (max 120s)...")

            is_healthy = wait_for_health(
                compose_file,
                qdrant_service,
                timeout=120,
                check_interval=3,
            )

            # Get final health status
            final_health = get_service_health(compose_file, qdrant_service)

            # Get container logs for debugging
            logs_result = run_docker_compose(
                compose_file,
                "logs",
                qdrant_service,
                timeout=10,
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
                f"Expected fix: Use 'grpc_health_probe' for Qdrant health check"
            )

            print(f"✅ {qdrant_service} is healthy!")

        finally:
            # Cleanup: Stop and remove containers
            print(f"\n🧹 Cleaning up {qdrant_service}...")
            cleanup_result = run_docker_compose(
                compose_file,
                "down",
                "-v",
                "--remove-orphans",
                timeout=30,
            )

            if cleanup_result.returncode != 0:
                print(f"Warning: Cleanup had issues:\n{cleanup_result.stderr}")

    def test_minimal_compose_health_checks(self, docker_available, docker_compose_available, cleanup_containers):
        """
        Test health checks in docker-compose.minimal.yml if it exists.

        This ensures minimal/production configurations also have working health checks.
        """
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

        print(f"\n🐳 Starting {service_name} service from minimal compose...")
        result = run_docker_compose(
            compose_file,
            "up",
            "-d",
            service_name,
            timeout=60,
        )

        if result.returncode != 0:
            pytest.fail(f"Failed to start {service_name}:\n" f"stdout: {result.stdout}\n" f"stderr: {result.stderr}")

        try:
            print(f"⏳ Waiting for {service_name} to become healthy...")
            is_healthy = wait_for_health(compose_file, service_name, timeout=90)

            final_health = get_service_health(compose_file, service_name)

            assert is_healthy, (
                f"{service_name} did not become healthy. "
                f"Final status: {final_health}. "
                f"Check health check command is available in the image."
            )

            print(f"✅ {service_name} is healthy!")

        finally:
            print(f"\n🧹 Cleaning up {service_name}...")
            run_docker_compose(
                compose_file,
                "down",
                "-v",
                "--remove-orphans",
                timeout=30,
            )


@pytest.mark.integration
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
            "should_exist": True,
            "description": "Qdrant should have grpc_health_probe",
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
                results.append(f"❌ {description}\n" f"   Image: {image}\n" f"   Expected '{command}' to exist but it doesn't")
            elif not should_exist and command_exists:
                results.append(
                    f"⚠️  {description}\n" f"   Image: {image}\n" f"   Expected '{command}' NOT to exist but it does"
                )
            else:
                print(f"✅ {description}")

        except subprocess.TimeoutExpired:
            results.append(f"⏱️  Timeout checking {command} in {image}")
        except Exception as e:
            results.append(f"❌ Error checking {command} in {image}: {e}")

    if results:
        pytest.fail("\n🔴 Health check command availability issues:\n\n" + "\n\n".join(results))
