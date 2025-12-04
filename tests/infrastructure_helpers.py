"""
Infrastructure auto-setup helpers for tests.

Provides utilities to detect and optionally start required infrastructure
(Postgres, Redis, Docker services) before running tests.

Usage:
    # Check if infrastructure is available
    if not is_postgres_available():
        # Option 1: Auto-start (if AUTO_SETUP_INFRA=1)
        ensure_postgres_running()

        # Option 2: Skip test
        pytest.skip("Postgres not available")

    # Run test that needs Postgres
    ...

Environment Variables:
    AUTO_SETUP_INFRA: Set to "1" to auto-start infrastructure via Docker Compose
    POSTGRES_HOST: Postgres hostname (default: localhost)
    POSTGRES_PORT: Postgres port (default: 5432)
    REDIS_HOST: Redis hostname (default: localhost)
    REDIS_PORT: Redis port (default: 6379)
"""

import os
import socket
import subprocess
import time
from typing import Literal
from tests.helpers.path_helpers import get_repo_root

# Project root
PROJECT_ROOT = get_repo_root()


def is_service_available(host: str, port: int, timeout: float = 2.0) -> bool:
    """
    Check if a TCP service is available at the given host:port.

    Args:
        host: Service hostname
        port: Service port
        timeout: Connection timeout in seconds

    Returns:
        bool: True if service is reachable, False otherwise
    """
    try:
        with socket.create_connection((host, port), timeout=timeout):
            return True
    except (TimeoutError, ConnectionRefusedError, OSError):
        return False


def is_postgres_available() -> bool:
    """
    Check if PostgreSQL is available at configured host/port.

    Returns:
        bool: True if Postgres is reachable, False otherwise
    """
    host = os.getenv("POSTGRES_HOST", "localhost")
    port = int(os.getenv("POSTGRES_PORT", "5432"))
    return is_service_available(host, port)


def is_redis_available() -> bool:
    """
    Check if Redis is available at configured host/port.

    Returns:
        bool: True if Redis is reachable, False otherwise
    """
    host = os.getenv("REDIS_HOST", "localhost")
    port = int(os.getenv("REDIS_PORT", "6379"))
    return is_service_available(host, port)


def is_docker_available() -> bool:
    """
    Check if Docker is installed and the daemon is running.

    Returns:
        bool: True if Docker is available, False otherwise
    """
    try:
        result = subprocess.run(
            ["docker", "info"],
            capture_output=True,
            timeout=5,
            check=False,
        )
        return result.returncode == 0
    except (subprocess.TimeoutExpired, FileNotFoundError):
        return False


def start_docker_compose_service(
    service: str,
    wait_timeout: int = 30,
    health_check_fn: callable | None = None,
) -> bool:
    """
    Start a Docker Compose service and optionally wait for it to be healthy.

    Args:
        service: Service name from docker-compose.yaml (e.g., "postgres", "redis")
        wait_timeout: Maximum seconds to wait for service to be healthy
        health_check_fn: Optional function to check if service is ready (returns bool)

    Returns:
        bool: True if service started successfully, False otherwise
    """
    if not is_docker_available():
        return False

    try:
        # Start the service
        result = subprocess.run(
            ["docker-compose", "up", "-d", service],
            cwd=PROJECT_ROOT,
            capture_output=True,
            timeout=60,
            check=False,
        )

        if result.returncode != 0:
            return False

        # If no health check provided, assume success
        if health_check_fn is None:
            return True

        # Wait for service to be healthy
        start_time = time.time()
        while time.time() - start_time < wait_timeout:
            if health_check_fn():
                return True
            time.sleep(1)

        return False

    except (subprocess.TimeoutExpired, FileNotFoundError):
        return False


def ensure_postgres_running(auto_start: bool = None) -> bool:
    """
    Ensure PostgreSQL is running, optionally starting it via Docker Compose.

    Args:
        auto_start: Whether to auto-start Postgres if not running.
                   If None, uses AUTO_SETUP_INFRA environment variable.

    Returns:
        bool: True if Postgres is available, False otherwise
    """
    # Check if already running
    if is_postgres_available():
        return True

    # Determine if we should auto-start
    should_auto_start = auto_start
    if should_auto_start is None:
        should_auto_start = os.getenv("AUTO_SETUP_INFRA") == "1"

    if not should_auto_start:
        return False

    # Auto-start via Docker Compose
    return start_docker_compose_service(
        "postgres",
        wait_timeout=30,
        health_check_fn=is_postgres_available,
    )


def ensure_redis_running(auto_start: bool = None) -> bool:
    """
    Ensure Redis is running, optionally starting it via Docker Compose.

    Args:
        auto_start: Whether to auto-start Redis if not running.
                   If None, uses AUTO_SETUP_INFRA environment variable.

    Returns:
        bool: True if Redis is available, False otherwise
    """
    # Check if already running
    if is_redis_available():
        return True

    # Determine if we should auto-start
    should_auto_start = auto_start
    if should_auto_start is None:
        should_auto_start = os.getenv("AUTO_SETUP_INFRA") == "1"

    if not should_auto_start:
        return False

    # Auto-start via Docker Compose
    return start_docker_compose_service(
        "redis",
        wait_timeout=30,
        health_check_fn=is_redis_available,
    )


def ensure_infrastructure_running(
    services: list[Literal["postgres", "redis", "all"]] = None,
    auto_start: bool = None,
) -> dict[str, bool]:
    """
    Ensure all required infrastructure services are running.

    Args:
        services: List of services to ensure are running.
                 Options: "postgres", "redis", "all"
                 Default: ["all"]
        auto_start: Whether to auto-start services if not running.
                   If None, uses AUTO_SETUP_INFRA environment variable.

    Returns:
        dict: {service_name: is_available}

    Example:
        >>> status = ensure_infrastructure_running(["postgres", "redis"])
        >>> if not status["postgres"]:
        ...     pytest.skip("Postgres not available")
    """
    if services is None:
        services = ["all"]

    # Expand "all" to specific services
    if "all" in services:
        services = ["postgres", "redis"]

    results = {}

    if "postgres" in services:
        results["postgres"] = ensure_postgres_running(auto_start)

    if "redis" in services:
        results["redis"] = ensure_redis_running(auto_start)

    return results


# Convenience function for pytest fixtures
def skip_if_infrastructure_unavailable(
    services: list[str] = None,
    auto_start: bool = None,
) -> None:
    """
    Skip test if required infrastructure is not available.

    Call this from a pytest fixture or at the start of a test function.

    Args:
        services: List of required services ("postgres", "redis", "all")
        auto_start: Whether to attempt auto-starting services

    Raises:
        pytest.skip: If any required service is unavailable

    Example:
        >>> def test_with_postgres():
        ...     skip_if_infrastructure_unavailable(["postgres"])
        ...     # Test code that needs Postgres
    """
    import pytest

    status = ensure_infrastructure_running(services, auto_start)

    unavailable = [svc for svc, available in status.items() if not available]

    if unavailable:
        pytest.skip(
            f"Required infrastructure not available: {', '.join(unavailable)}. "
            f"Set AUTO_SETUP_INFRA=1 to auto-start, or run: make setup-infra"
        )
