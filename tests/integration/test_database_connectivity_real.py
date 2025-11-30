"""
Integration Tests for Real Database Connectivity

These tests validate database connectivity with a real PostgreSQL instance.
They require PostgreSQL to be running and accessible.

Run with: pytest tests/integration/test_database_connectivity_real.py -v

IMPORTANT: These are integration tests, not unit tests.
They depend on external services (PostgreSQL) being available.
"""

import gc
import os
import socket

import pytest

pytestmark = pytest.mark.integration


def _is_postgres_available() -> bool:
    """Check if PostgreSQL is actually available on the test port."""
    host = os.getenv("POSTGRES_HOST", "localhost")
    port = int(os.getenv("POSTGRES_PORT", "9432"))
    try:
        sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        sock.settimeout(1)
        result = sock.connect_ex((host, port))
        sock.close()
        return result == 0
    except Exception:
        return False


# Check at module load time to avoid repeated socket checks
POSTGRES_AVAILABLE = _is_postgres_available()


@pytest.mark.xdist_group(name="database_connectivity")
class TestDatabaseConnectivityReal:
    """Integration tests for real database connectivity."""

    def teardown_method(self):
        """Force GC to prevent mock accumulation in xdist workers."""
        gc.collect()

    @pytest.mark.skipif(
        not POSTGRES_AVAILABLE,
        reason="PostgreSQL not available on test port",
    )
    @pytest.mark.asyncio
    async def test_check_database_connectivity_with_real_postgres(self):
        """
        Integration test: Verify database connectivity with real PostgreSQL

        Requires:
        - PostgreSQL running on localhost:9432 (test port, configurable via POSTGRES_PORT)
        - Database 'gdpr' exists
        - User 'postgres' with password 'postgres'

        This test validates the actual I/O layer, not mocked behavior.
        """
        from mcp_server_langgraph.infrastructure.database import check_database_connectivity

        postgres_url = os.getenv("GDPR_POSTGRES_URL", "postgresql://postgres:postgres@localhost:9432/gdpr_test")

        is_healthy, message = await check_database_connectivity(postgres_url, timeout=5.0)

        assert is_healthy is True, f"Database should be accessible: {message}"
        assert "accessible" in message.lower()

    @pytest.mark.skipif(
        not POSTGRES_AVAILABLE,
        reason="PostgreSQL not available on test port",
    )
    @pytest.mark.asyncio
    async def test_create_connection_pool_with_real_postgres(self):
        """
        Integration test: Verify connection pool creation with real PostgreSQL

        Requires:
        - PostgreSQL running on localhost:9432 (test port, configurable via POSTGRES_PORT)
        - Database 'gdpr' exists
        - User 'postgres' with password 'postgres'

        This test validates the actual connection pooling, not mocked behavior.
        """
        from mcp_server_langgraph.infrastructure.database import create_connection_pool

        # Use real PostgreSQL connection (assumes Docker Compose is running)
        # Use POSTGRES_PORT env var (default 9432 for tests, not production 5432)
        postgres_port = os.getenv("POSTGRES_PORT", "9432")
        postgres_url = os.getenv("GDPR_POSTGRES_URL", f"postgresql://postgres:postgres@localhost:{postgres_port}/gdpr_test")

        pool = await create_connection_pool(
            postgres_url,
            min_size=1,
            max_size=2,
            command_timeout=10.0,
            max_retries=3,
            initial_delay=0.5,
            max_delay=2.0,
        )

        assert pool is not None
        assert pool.get_min_size() == 1
        assert pool.get_max_size() == 2

        # Test that pool can execute a query
        async with pool.acquire() as conn:
            result = await conn.fetchval("SELECT 1")
            assert result == 1

        # Cleanup
        await pool.close()

    @pytest.mark.skipif(
        not POSTGRES_AVAILABLE,
        reason="PostgreSQL not available on test port",
    )
    @pytest.mark.asyncio
    async def test_check_database_connectivity_with_invalid_credentials(self):
        """
        Integration test: Verify authentication failure handling

        This test validates that authentication errors are properly detected.
        """
        from mcp_server_langgraph.infrastructure.database import check_database_connectivity

        # Invalid credentials
        postgres_url = "postgresql://invalid_user:invalid_pass@localhost:9432/gdpr"

        is_healthy, message = await check_database_connectivity(postgres_url, timeout=5.0)

        assert is_healthy is False
        assert "auth" in message.lower() or "password" in message.lower() or "failed" in message.lower()

    @pytest.mark.skipif(
        not POSTGRES_AVAILABLE,
        reason="PostgreSQL not available on test port",
    )
    @pytest.mark.asyncio
    async def test_check_database_connectivity_with_nonexistent_database(self):
        """
        Integration test: Verify missing database detection

        This test validates that missing database errors are properly detected.
        """
        from mcp_server_langgraph.infrastructure.database import check_database_connectivity

        # Invalid database
        postgres_url = "postgresql://postgres:postgres@localhost:9432/nonexistent_db"

        is_healthy, message = await check_database_connectivity(postgres_url, timeout=5.0)

        assert is_healthy is False
        assert "exist" in message.lower() or "database" in message.lower()

    @pytest.mark.skipif(
        not POSTGRES_AVAILABLE,
        reason="PostgreSQL not available on test port",
    )
    @pytest.mark.asyncio
    async def test_check_database_connectivity_timeout(self):
        """
        Integration test: Verify timeout handling

        This test validates that connection timeouts are properly handled.
        """
        from mcp_server_langgraph.infrastructure.database import check_database_connectivity

        # Invalid host/unreachable
        postgres_url = "postgresql://postgres:postgres@192.0.2.1:9432/gdpr"

        is_healthy, message = await check_database_connectivity(postgres_url, timeout=1.0)

        assert is_healthy is False
        assert "timeout" in message.lower() or "connection" in message.lower()
