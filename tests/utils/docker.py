"""
Docker Utilities for Integration Tests
========================================
Helper functions for managing Docker containers during integration testing
"""

import subprocess
import time
from typing import List, Optional


def wait_for_service(
    service_name: str,
    compose_file: str = "docker/docker-compose.test.yml",
    timeout: int = 60,
    interval: int = 2,
) -> bool:
    """
    Wait for Docker Compose service to become healthy

    Args:
        service_name: Name of the service (e.g., 'postgres-test')
        compose_file: Path to docker-compose file
        timeout: Maximum wait time in seconds
        interval: Check interval in seconds

    Returns:
        True if service is healthy, False if timeout

    Raises:
        subprocess.CalledProcessError: If docker compose command fails
    """
    start_time = time.time()

    while time.time() - start_time < timeout:
        try:
            result = subprocess.run(
                ["docker", "compose", "-f", compose_file, "ps", service_name],
                capture_output=True,
                text=True,
                check=True,
                timeout=60,
            )

            # Check if service is healthy
            if "healthy" in result.stdout:
                return True

            # Check if service failed
            if any(status in result.stdout for status in ["Exited", "Dead", "unhealthy"]):
                return False

        except subprocess.CalledProcessError:
            # Service might not exist yet
            pass

        time.sleep(interval)

    return False


def wait_for_services(
    service_names: list[str],
    compose_file: str = "docker/docker-compose.test.yml",
    timeout: int = 120,
) -> bool:
    """
    Wait for multiple Docker Compose services to become healthy

    Args:
        service_names: List of service names
        compose_file: Path to docker-compose file
        timeout: Total maximum wait time in seconds

    Returns:
        True if all services healthy, False if any timeout
    """
    return all(wait_for_service(service, compose_file, timeout) for service in service_names)


def get_service_logs(
    service_name: str,
    compose_file: str = "docker/docker-compose.test.yml",
    tail: int | None = 100,
) -> str:
    """
    Get logs from a Docker Compose service

    Args:
        service_name: Name of the service
        compose_file: Path to docker-compose file
        tail: Number of lines to retrieve (None for all)

    Returns:
        Service logs as string
    """
    cmd = ["docker", "compose", "-f", compose_file, "logs", service_name]

    if tail:
        cmd.extend(["--tail", str(tail)])

    try:
        result = subprocess.run(cmd, capture_output=True, text=True, check=True, timeout=60)
        return result.stdout
    except subprocess.CalledProcessError as e:
        return f"Error retrieving logs: {e}"


def cleanup_test_containers(compose_file: str = "docker/docker-compose.test.yml") -> bool:
    """
    Stop and remove all containers from docker-compose file

    Args:
        compose_file: Path to docker-compose file

    Returns:
        True if cleanup successful, False otherwise
    """
    try:
        subprocess.run(
            ["docker", "compose", "-f", compose_file, "down", "-v", "--remove-orphans"],
            capture_output=True,
            check=True,
            timeout=60,
        )
        return True
    except subprocess.CalledProcessError:
        return False


def is_service_running(
    service_name: str,
    compose_file: str = "docker/docker-compose.test.yml",
) -> bool:
    """
    Check if a Docker Compose service is running

    Args:
        service_name: Name of the service
        compose_file: Path to docker-compose file

    Returns:
        True if service is running, False otherwise
    """
    try:
        result = subprocess.run(
            ["docker", "compose", "-f", compose_file, "ps", "-q", service_name],
            capture_output=True,
            text=True,
            check=True,
            timeout=60,
        )
        # If command returns container ID, service is running
        return bool(result.stdout.strip())
    except subprocess.CalledProcessError:
        return False


def get_service_port(
    service_name: str,
    internal_port: int,
    compose_file: str = "docker/docker-compose.test.yml",
) -> int | None:
    """
    Get the host port mapped to a service's internal port

    Args:
        service_name: Name of the service
        internal_port: Internal port number
        compose_file: Path to docker-compose file

    Returns:
        Host port number, or None if not mapped
    """
    try:
        result = subprocess.run(
            ["docker", "compose", "-f", compose_file, "port", service_name, str(internal_port)],
            capture_output=True,
            text=True,
            check=True,
            timeout=60,
        )
        # Output format: 0.0.0.0:PORT or :::PORT
        if result.stdout.strip():
            port_str = result.stdout.strip().split(":")[-1]
            return int(port_str)
    except (subprocess.CalledProcessError, ValueError):
        pass

    return None


def exec_in_service(
    service_name: str,
    command: list[str],
    compose_file: str = "docker/docker-compose.test.yml",
) -> tuple[str, str, int]:
    """
    Execute a command inside a running service container

    Args:
        service_name: Name of the service
        command: Command to execute (as list of strings)
        compose_file: Path to docker-compose file

    Returns:
        Tuple of (stdout, stderr, exit_code)
    """
    cmd = ["docker", "compose", "-f", compose_file, "exec", "-T", service_name] + command

    try:
        result = subprocess.run(cmd, capture_output=True, text=True, timeout=60)
        return result.stdout, result.stderr, result.returncode
    except subprocess.CalledProcessError as e:
        return "", str(e), e.returncode


# Context manager for test environment setup/teardown
class TestEnvironment:
    """
    Context manager for Docker Compose test environment

    Example:
        with TestEnvironment("docker/docker-compose.test.yml") as env:
            # Services are started and healthy
            env.wait_for_services(["postgres-test", "redis-test"])
            # Run tests
        # Services are automatically stopped and removed
    """

    def __init__(
        self,
        compose_file: str = "docker/docker-compose.test.yml",
        services: list[str] | None = None,
        timeout: int = 120,
    ):
        """
        Initialize test environment

        Args:
            compose_file: Path to docker-compose file
            services: List of services to wait for (None = all)
            timeout: Maximum wait time for services
        """
        self.compose_file = compose_file
        self.services = services or []
        self.timeout = timeout

    def __enter__(self):
        """Start services and wait for health"""
        # Start services
        subprocess.run(["docker", "compose", "-f", self.compose_file, "up", "-d"], check=True, capture_output=True, timeout=60)

        # Wait for services to be healthy
        if self.services and not wait_for_services(self.services, self.compose_file, self.timeout):
            raise RuntimeError(f"Services did not become healthy within {self.timeout}s")

        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        """Stop and remove services"""
        cleanup_test_containers(self.compose_file)
        return False  # Don't suppress exceptions
