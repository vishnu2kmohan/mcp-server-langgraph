"""
Docker infrastructure fixtures for test suite.

This module provides fixtures for:
- Docker Compose automated lifecycle management
- Port availability checking
- HTTP health endpoint verification
- Database schema readiness verification

Extracted from tests/conftest.py to improve maintainability.
See: Testing Strategy Remediation Plan - Phase 3.2
"""

import asyncio
import logging
import os
import socket
import time

import pytest


def _wait_for_port(host: str, port: int, timeout: float = 30.0) -> bool:
    """
    Wait for a TCP port to become available.

    Returns True if port is available, False if timeout is reached.
    """
    start_time = time.time()
    while time.time() - start_time < timeout:
        try:
            sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            sock.settimeout(1)
            result = sock.connect_ex((host, port))
            sock.close()
            if result == 0:
                return True
        except OSError:
            pass
        time.sleep(0.5)
    return False


def _check_http_health(url: str, timeout: float = 2.0) -> bool:
    """Check if HTTP endpoint is healthy."""
    try:
        import httpx

        response = httpx.get(url, timeout=timeout)
        return response.status_code == 200
    except Exception:
        return False


async def _verify_schema_ready(host: str, port: int, timeout: float = 30.0) -> bool:
    """
    Verify database schema is fully initialized with all required tables.

    This function prevents integration test failures where tests start before
    the schema migration completes. The PostgreSQL health check (pg_isready)
    only verifies the server accepts connections, not that tables exist.

    Root Cause (OpenAI Codex Finding 2025-11-20):
    - Docker container runs migrations/001_gdpr_schema.sql automatically
    - Health check passes before migration completes
    - Tests fail with "relation does not exist" errors

    Args:
        host: PostgreSQL host (default: localhost)
        port: PostgreSQL port (default: 9432)
        timeout: Maximum time to wait for schema (default: 30s)

    Returns:
        True if all required tables exist, False if timeout reached

    Required tables (GDPR schema):
    - user_profiles
    - user_preferences
    - consent_records
    - conversations
    - audit_logs
    """
    try:
        import asyncpg
    except ImportError:
        logging.warning("asyncpg not installed - skipping schema verification")
        return False

    start_time = time.time()
    required_tables = ["user_profiles", "user_preferences", "consent_records", "conversations", "audit_logs"]

    while time.time() - start_time < timeout:
        try:
            # Connect to gdpr_test database
            conn = await asyncpg.connect(
                host=host,
                port=port,
                database=os.getenv("POSTGRES_DB", "gdpr_test"),
                user=os.getenv("POSTGRES_USER", "postgres"),
                password=os.getenv("POSTGRES_PASSWORD", "postgres"),
                timeout=5,
            )

            try:
                # Query for all GDPR tables
                tables = await conn.fetch(
                    """
                    SELECT table_name
                    FROM information_schema.tables
                    WHERE table_schema = 'public'
                      AND table_name IN ('user_profiles', 'user_preferences',
                                          'consent_records', 'conversations', 'audit_logs')
                    """
                )

                table_names = [row["table_name"] for row in tables]

                # Check if all required tables exist
                if len(table_names) == 5:
                    missing = set(required_tables) - set(table_names)
                    if not missing:
                        logging.info(f"✓ GDPR schema ready: all {len(required_tables)} tables exist")
                        return True
                    else:
                        logging.debug(f"GDPR schema incomplete: missing {missing}")
                else:
                    logging.debug(f"GDPR schema incomplete: found {len(table_names)}/5 tables: {table_names}")

            finally:
                await conn.close()

        except Exception as e:
            logging.debug(f"Schema verification attempt failed: {e}")

        # Wait before retry
        await asyncio.sleep(1)

    logging.error(f"GDPR schema not ready after {timeout}s timeout")
    return False


@pytest.fixture(scope="session")
def docker_compose_file():
    """
    Provide path to root docker-compose.test.yml for pytest-docker-compose-v2.

    Uses root docker-compose.test.yml for local/CI parity (OpenAI Codex Finding #1).

    This enables automated docker-compose lifecycle management:
    - Services start automatically before test session
    - Services stop automatically after test session
    - No manual docker-compose commands needed
    """
    from pathlib import Path

    return str(Path(__file__).parent.parent.parent / "docker-compose.test.yml")


@pytest.fixture(scope="session")
def docker_services_available(docker_compose_file):
    """
    Check if Docker is available and docker-compose.test.yml exists.

    This is a lightweight check that runs before attempting to start services.
    """
    # Check if docker-compose file exists
    if not os.path.exists(docker_compose_file):
        pytest.skip(f"Docker compose file not found: {docker_compose_file}")

    # Check if Docker is available
    try:
        import subprocess

        result = subprocess.run(["docker", "info"], capture_output=True, timeout=5)
        if result.returncode != 0:
            pytest.skip("Docker daemon not available")
    except (FileNotFoundError, subprocess.TimeoutExpired):
        pytest.skip("Docker not installed or not responding")

    return True
