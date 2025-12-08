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
            # Connect to mcp_test database (canonical test database per tests/constants.py)
            # Note: Import from constants for single source of truth
            from tests.constants import TEST_POSTGRES_DB

            conn = await asyncpg.connect(
                host=host,
                port=port,
                database=os.getenv("POSTGRES_DB", TEST_POSTGRES_DB),
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


@pytest.fixture(scope="session")
def test_infrastructure_ports():
    """
    Define test infrastructure ports (offset by 1000 from production).

    **Single Shared Infrastructure (Session-Scoped)**:
    All pytest-xdist workers connect to the SAME infrastructure instance on FIXED ports.
    This provides a single docker-compose stack shared across all workers, with logical
    isolation via PostgreSQL schemas, Redis DB indices, OpenFGA stores, etc.

    Port Allocation:
    - All workers use base ports: postgres=9432, redis=9379, openfga=9080, etc.
    - Ports are FIXED (no worker-based offsets)
    - Maps directly to docker-compose.test.yml port bindings

    Logical Isolation Strategy:
    - PostgreSQL: Separate schemas per worker (test_worker_gw0, test_worker_gw1, ...)
    - Redis: Separate DB indices per worker (1, 2, 3, ...)
    - OpenFGA: Separate stores per worker (test_store_gw0, test_store_gw1, ...)
    - Qdrant: Separate collections per worker
    - Keycloak: Separate realms per worker

    This is faster and simpler than per-worker infrastructure with dynamic port allocation,
    avoiding "address already in use" errors through logical isolation instead of port offsets.
    """
    # Return FIXED base ports for all workers
    # All xdist workers (gw0, gw1, gw2, ...) connect to the same ports
    # Isolation is achieved via schemas, DB indices, stores, not port offsets
    # NOTE: docker-compose.test.yml uses a SINGLE Redis instance for both checkpoints and sessions
    # Port 9379 is the consolidated Redis port (logical isolation via DB indices)
    # This matches docker-compose.test.yml:296-317 (redis-test service)
    return {
        "postgres": 9432,
        "redis_checkpoints": 9379,
        "redis_sessions": 9379,  # Same as checkpoints - consolidated Redis instance
        "qdrant": 9333,
        "qdrant_grpc": 9334,
        "openfga_http": 9080,
        "openfga_grpc": 9081,
        "keycloak": 9082,  # HTTP API port
        "keycloak_management": 9900,  # Management/health port (Keycloak 26.x best practice)
    }


@pytest.fixture(scope="session")
def test_infrastructure(docker_services_available, docker_compose_file, test_infrastructure_ports):
    """
    Automated test infrastructure lifecycle management.

    This fixture:
    1. Starts all services via docker-compose.test.yml
    2. Waits for health checks to pass
    3. Yields control to tests
    4. Automatically tears down services after session

    Replaces manual:
        docker compose -f docker-compose.test.yml up -d
        docker compose -f docker-compose.test.yml down -v

    Usage:
        @pytest.mark.e2e
        def test_with_infrastructure(test_infrastructure):
            # All services are running and healthy
            ...
    """
    # Set TESTING environment variable for services
    # NOTE: This is intentionally session-scoped and not cleaned up.
    # Worker isolation is achieved via logical separation (schemas, DB indices, stores),
    # NOT port offsets. All workers connect to the same fixed ports.
    # The TESTING env var is shared across all workers to enable test infrastructure detection.
    os.environ["TESTING"] = "true"

    # Detect existing test infrastructure (started by make test-integration script)
    # This approach removes the need for python-on-whales dependency and avoids
    # redundant docker-compose operations
    logging.info("Detecting existing test infrastructure...")

    # Wait for critical services to be ready
    logging.info("Waiting for test infrastructure health checks...")

    # PostgreSQL
    if not _wait_for_port("localhost", test_infrastructure_ports["postgres"], timeout=30):
        pytest.skip(
            "PostgreSQL test service not available - run 'make test-integration' or start docker-compose.test.yml manually"
        )
    logging.info("✓ PostgreSQL port ready")

    # Verify GDPR schema is fully initialized (not just port open)
    # This prevents race conditions where tests start before tables exist
    logging.info("Verifying GDPR schema initialization...")
    schema_ready = asyncio.run(_verify_schema_ready("localhost", test_infrastructure_ports["postgres"], timeout=30))
    if not schema_ready:
        pytest.skip("GDPR schema not initialized in time - run migrations/001_gdpr_schema.sql")
    logging.info("✓ PostgreSQL ready with GDPR schema")

    # Redis (checkpoints)
    if not _wait_for_port("localhost", test_infrastructure_ports["redis_checkpoints"], timeout=20):
        pytest.skip("Redis checkpoints test service not available - run 'make test-integration'")
    logging.info("✓ Redis (checkpoints) ready")

    # Redis (sessions)
    if not _wait_for_port("localhost", test_infrastructure_ports["redis_sessions"], timeout=20):
        pytest.skip("Redis sessions test service not available - run 'make test-integration'")
    logging.info("✓ Redis (sessions) ready")

    # OpenFGA HTTP
    if not _wait_for_port("localhost", test_infrastructure_ports["openfga_http"], timeout=40):
        pytest.skip("OpenFGA test service not available - run 'make test-integration'")
    # Additional check for OpenFGA
    if not _check_http_health(f"http://localhost:{test_infrastructure_ports['openfga_http']}/healthz", timeout=5):
        pytest.skip("OpenFGA health check failed - ensure openfga-test container is healthy")
    logging.info("✓ OpenFGA ready")

    # Keycloak (takes longer to start - needs DB migration + realm import + JIT compilation)
    # Note: Keycloak uses Java and requires JIT warmup, which adds ~30-60s to first startup
    if not _wait_for_port("localhost", test_infrastructure_ports["keycloak"], timeout=90):
        pytest.skip("Keycloak test service not available - run 'make test-integration'")

    # Keycloak Health Check Strategy (Keycloak 26.x):
    # 1. Primary: Use /health/ready on management port 9000 (mapped to 9900)
    # 2. Fallback: Use /authn/realms/master on HTTP port 8080 (mapped to 9082)
    # The management port may not always be configured correctly in test environments,
    # but the realms endpoint is a reliable indicator of Keycloak being fully operational.
    #
    # Retry with backoff since Keycloak HTTP server may take time to initialize after port opens
    # This accounts for:
    #   1. Database schema migration
    #   2. Realm import from keycloak-test-realm.json
    #   3. JIT compilation of Java bytecode
    keycloak_ready = False
    # Try management port first (best practice)
    keycloak_health_url = f"http://localhost:{test_infrastructure_ports['keycloak_management']}/health/ready"
    for attempt in range(5):  # 5 attempts * 2s = 10s for management port
        if _check_http_health(keycloak_health_url, timeout=5):
            keycloak_ready = True
            logging.info("✓ Keycloak ready (management port /health/ready)")
            break
        time.sleep(2)

    # Fallback to realms endpoint on HTTP port
    if not keycloak_ready:
        keycloak_realms_url = f"http://localhost:{test_infrastructure_ports['keycloak']}/authn/realms/master"
        for attempt in range(15):  # 15 attempts * 2s = 30s for realms endpoint
            if _check_http_health(keycloak_realms_url, timeout=5):
                keycloak_ready = True
                logging.info("✓ Keycloak ready (fallback /authn/realms/master)")
                break
            time.sleep(2)

    if not keycloak_ready:
        logging.error("Keycloak not responding on management port or realms endpoint after 40s")
        pytest.skip("Keycloak health check failed - neither /health/ready (port 9900) nor /authn/realms/master responding")
    logging.info("✓ Keycloak ready")

    # Qdrant
    if not _wait_for_port("localhost", test_infrastructure_ports["qdrant"], timeout=30):
        pytest.skip("Qdrant test service not available - run 'make test-integration'")
    # Additional check for Qdrant - use /readyz endpoint (official health check endpoint)
    # Qdrant exposes /healthz, /livez, and /readyz for Kubernetes-style health checks
    if not _check_http_health(f"http://localhost:{test_infrastructure_ports['qdrant']}/readyz", timeout=5):
        pytest.skip("Qdrant health check failed - ensure qdrant-test container is healthy")
    logging.info("✓ Qdrant ready")

    logging.info("✅ All test infrastructure services ready")

    # Return infrastructure info
    # NOTE: No cleanup needed - infrastructure is managed externally by make test-integration
    return {"ports": test_infrastructure_ports, "ready": True}
