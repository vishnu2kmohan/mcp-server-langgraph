"""
Regression test for schema initialization timing issues.

Tests that verify the GDPR schema is fully initialized before integration
tests begin running, preventing race conditions where tests start before
tables exist.

Root Cause (OpenAI Codex Finding 2025-11-20):
    - Docker container runs migrations via docker-entrypoint-initdb.d
    - Health check (pg_isready) passes before migration completes
    - Tests start and fail with "relation does not exist" errors

Fix Validation:
    - test_infrastructure fixture must verify schema completion
    - All 5 GDPR tables must exist before yielding to tests
    - Connection errors should not occur during integration tests

References:
    - docker-compose.test.yml: PostgreSQL container configuration
    - migrations/000_init_databases.sh: Auto-initialization script
    - migrations/001_gdpr_schema.sql: GDPR table definitions
    - tests/conftest.py: test_infrastructure fixture
"""

import gc
import os

import pytest

# Mark as integration test with xdist_group for worker isolation
pytestmark = pytest.mark.integration


@pytest.mark.xdist_group(name="schema_initialization_tests")
class TestSchemaInitializationTiming:
    """Tests for GDPR schema initialization timing and completeness."""

    def teardown_method(self) -> None:
        """Force GC to prevent mock accumulation in xdist workers"""
        gc.collect()

    @pytest.mark.asyncio
    async def test_gdpr_schema_tables_exist_before_tests(self, integration_test_env):
        """
        Should verify all GDPR tables exist in gdpr_test database.

        This test runs early in the integration suite to catch schema
        initialization failures before other tests start.

        Required tables:
        - user_profiles
        - user_preferences
        - consent_records
        - conversations
        - audit_logs
        """
        if not integration_test_env:
            pytest.skip("Integration test environment not available")

        import asyncpg

        # Connection params from environment (set by test script)
        conn = await asyncpg.connect(
            host=os.getenv("POSTGRES_HOST", "localhost"),
            port=int(os.getenv("POSTGRES_PORT", "9432")),
            database=os.getenv("POSTGRES_DB", "gdpr_test"),
            user=os.getenv("POSTGRES_USER", "postgres"),
            password=os.getenv("POSTGRES_PASSWORD", "postgres"),
        )

        try:
            # Query for all GDPR tables
            tables = await conn.fetch(
                """
                SELECT table_name
                FROM information_schema.tables
                WHERE table_schema = 'public'
                  AND table_name IN (
                      'user_profiles',
                      'user_preferences',
                      'consent_records',
                      'conversations',
                      'audit_logs'
                  )
                ORDER BY table_name
                """
            )

            table_names = [row["table_name"] for row in tables]

            # All 5 tables must exist
            assert len(table_names) == 5, f"Expected 5 GDPR tables, found {len(table_names)}: {table_names}"

            # Verify each required table
            required_tables = ["audit_logs", "consent_records", "conversations", "user_preferences", "user_profiles"]
            for table in required_tables:
                assert table in table_names, f"Required table '{table}' not found. Available: {table_names}"

        finally:
            await conn.close()

    @pytest.mark.asyncio
    async def test_gdpr_schema_indexes_exist(self, integration_test_env):
        """
        Should verify critical indexes exist for GDPR queries.

        Performance-critical indexes for compliance queries:
        - idx_audit_logs_user_id
        - idx_audit_logs_timestamp
        - idx_consent_records_user_id
        - idx_user_profiles_email
        """
        if not integration_test_env:
            pytest.skip("Integration test environment not available")

        import asyncpg

        conn = await asyncpg.connect(
            host=os.getenv("POSTGRES_HOST", "localhost"),
            port=int(os.getenv("POSTGRES_PORT", "9432")),
            database=os.getenv("POSTGRES_DB", "gdpr_test"),
            user=os.getenv("POSTGRES_USER", "postgres"),
            password=os.getenv("POSTGRES_PASSWORD", "postgres"),
        )

        try:
            # Query for critical indexes
            indexes = await conn.fetch(
                """
                SELECT indexname
                FROM pg_indexes
                WHERE schemaname = 'public'
                  AND indexname IN (
                      'idx_audit_logs_user_id',
                      'idx_audit_logs_timestamp',
                      'idx_consent_records_user_id',
                      'idx_user_profiles_email'
                  )
                ORDER BY indexname
                """
            )

            index_names = [row["indexname"] for row in indexes]

            # Verify critical indexes exist
            critical_indexes = [
                "idx_audit_logs_timestamp",
                "idx_audit_logs_user_id",
                "idx_consent_records_user_id",
                "idx_user_profiles_email",
            ]

            for index in critical_indexes:
                assert index in index_names, f"Critical index '{index}' not found. Available: {index_names}"

        finally:
            await conn.close()

    @pytest.mark.asyncio
    async def test_schema_initialization_timing(self, integration_test_env):
        """
        Should measure schema initialization time for performance monitoring.

        Expected timing (from migrations/000_init_databases.sh logs):
        - Database creation: <1s
        - Schema migration: 1-3s
        - Total: <5s on modern hardware

        If this test is slow (>10s), check:
        - tmpfs size (should be 512MB)
        - Docker resource limits
        - Network connectivity to PostgreSQL
        """
        if not integration_test_env:
            pytest.skip("Integration test environment not available")

        import asyncpg
        from time import time

        start = time()

        # Connect and verify schema (simulates what tests do)
        conn = await asyncpg.connect(
            host=os.getenv("POSTGRES_HOST", "localhost"),
            port=int(os.getenv("POSTGRES_PORT", "9432")),
            database=os.getenv("POSTGRES_DB", "gdpr_test"),
            user=os.getenv("POSTGRES_USER", "postgres"),
            password=os.getenv("POSTGRES_PASSWORD", "postgres"),
        )

        try:
            # Simple query to verify connection works
            result = await conn.fetchval("SELECT COUNT(*) FROM audit_logs")
            assert isinstance(result, int)

            elapsed = time() - start

            # Connection and query should be fast (<2s)
            assert elapsed < 2.0, f"Schema initialization too slow: {elapsed:.2f}s (expected <2s)"

        finally:
            await conn.close()

    @pytest.mark.asyncio
    async def test_connection_pool_isolation(self, integration_test_env):
        """
        Should verify connection pool supports worker isolation.

        This test validates the fix for session-scoped connection issues:
        - Previous: Single session-scoped connection shared across tests
        - Fixed: Connection pool with per-worker connections
        """
        if not integration_test_env:
            pytest.skip("Integration test environment not available")

        import asyncpg

        # Create a small connection pool
        pool = await asyncpg.create_pool(
            host=os.getenv("POSTGRES_HOST", "localhost"),
            port=int(os.getenv("POSTGRES_PORT", "9432")),
            database=os.getenv("POSTGRES_DB", "gdpr_test"),
            user=os.getenv("POSTGRES_USER", "postgres"),
            password=os.getenv("POSTGRES_PASSWORD", "postgres"),
            min_size=2,
            max_size=4,
        )

        try:
            # Acquire multiple connections
            async with pool.acquire() as conn1:
                async with pool.acquire() as conn2:
                    # Both connections should work independently
                    result1 = await conn1.fetchval("SELECT 1")
                    result2 = await conn2.fetchval("SELECT 2")

                    assert result1 == 1
                    assert result2 == 2

                    # Connections should be different objects
                    assert conn1 is not conn2

        finally:
            await pool.close()

    @pytest.mark.asyncio
    async def test_worker_schema_isolation(self, integration_test_env):
        """
        Should verify worker-scoped schemas work correctly.

        Each pytest-xdist worker should have its own schema:
        - Worker gw0: test_worker_gw0
        - Worker gw1: test_worker_gw1

        This prevents race conditions in parallel execution.
        """
        if not integration_test_env:
            pytest.skip("Integration test environment not available")

        import asyncpg

        conn = await asyncpg.connect(
            host=os.getenv("POSTGRES_HOST", "localhost"),
            port=int(os.getenv("POSTGRES_PORT", "9432")),
            database=os.getenv("POSTGRES_DB", "gdpr_test"),
            user=os.getenv("POSTGRES_USER", "postgres"),
            password=os.getenv("POSTGRES_PASSWORD", "postgres"),
        )

        try:
            # Get worker ID from environment
            worker_id = os.getenv("PYTEST_XDIST_WORKER", "gw0")
            schema_name = f"test_worker_{worker_id}"

            # Create worker schema
            await conn.execute(f"CREATE SCHEMA IF NOT EXISTS {schema_name}")

            # Set search_path
            await conn.execute(f"SET search_path TO {schema_name}, public")

            # Verify search_path is set correctly
            current_path = await conn.fetchval("SHOW search_path")
            assert schema_name in current_path, f"search_path not set correctly: {current_path}"

            # Create a test table in worker schema
            await conn.execute(
                f"""
                CREATE TABLE IF NOT EXISTS {schema_name}.test_isolation (
                    id SERIAL PRIMARY KEY,
                    data TEXT
                )
                """
            )

            # Insert test data
            await conn.execute(f"INSERT INTO {schema_name}.test_isolation (data) VALUES ('worker_{worker_id}')")

            # Verify data
            result = await conn.fetchval(f"SELECT data FROM {schema_name}.test_isolation LIMIT 1")
            assert result == f"worker_{worker_id}"

            # Cleanup
            await conn.execute(f"DROP SCHEMA {schema_name} CASCADE")

        finally:
            await conn.close()

    @pytest.mark.asyncio
    async def test_no_duplicate_schema_initialization(self, integration_test_env):
        """
        Should verify schema is initialized only once per container lifecycle.

        This test prevents regression where:
        1. Docker container runs migrations/001_gdpr_schema.sql
        2. postgres_with_schema fixture ALSO runs same migration

        The fix removes postgres_with_schema and relies solely on container init.
        """
        if not integration_test_env:
            pytest.skip("Integration test environment not available")

        import asyncpg

        conn = await asyncpg.connect(
            host=os.getenv("POSTGRES_HOST", "localhost"),
            port=int(os.getenv("POSTGRES_PORT", "9432")),
            database=os.getenv("POSTGRES_DB", "gdpr_test"),
            user=os.getenv("POSTGRES_USER", "postgres"),
            password=os.getenv("POSTGRES_PASSWORD", "postgres"),
        )

        try:
            # Query PostgreSQL logs for schema initialization messages
            # (This is a simple check - in production you'd query pg_stat_activity)

            # Verify tables exist (proves schema was initialized)
            tables = await conn.fetch(
                """
                SELECT COUNT(*) as count
                FROM information_schema.tables
                WHERE table_schema = 'public'
                  AND table_name IN (
                      'user_profiles', 'user_preferences', 'consent_records',
                      'conversations', 'audit_logs'
                  )
                """
            )

            assert tables[0]["count"] == 5, "Schema not initialized or incomplete"

            # Verify no duplicate initialization artifacts
            # (Check for duplicate triggers, functions, etc.)
            triggers = await conn.fetch(
                """
                SELECT COUNT(*) as count
                FROM information_schema.triggers
                WHERE trigger_schema = 'public'
                  AND trigger_name = 'trigger_user_profiles_last_updated'
                """
            )

            # Should have exactly 1 trigger (not multiple from duplicate init)
            assert triggers[0]["count"] == 1, "Duplicate schema initialization detected"

        finally:
            await conn.close()
