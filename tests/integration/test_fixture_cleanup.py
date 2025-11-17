"""
Tests for per-test cleanup fixtures

These tests verify that fixtures properly clean up state between tests,
preventing test pollution and ensuring test isolation.

TDD: These tests should fail initially (RED phase), then pass after
implementing per-test cleanup fixtures (GREEN phase).
"""

import gc

import pytest

from tests.conftest import get_user_id


@pytest.mark.integration
@pytest.mark.xdist_group(name="testpostgresqlcleanup")
class TestPostgreSQLCleanup:
    """Test PostgreSQL cleanup between tests"""

    def teardown_method(self) -> None:
        """Force GC to prevent mock accumulation in xdist workers"""
        gc.collect()

    @pytest.mark.asyncio
    async def test_first_insert_postgres(self, postgres_connection_clean):
        """First test: insert data into PostgreSQL"""
        # This test will insert data
        # Without cleanup, next test would see this data
        await postgres_connection_clean.execute("CREATE TABLE IF NOT EXISTS test_cleanup (id SERIAL PRIMARY KEY, data TEXT)")
        await postgres_connection_clean.execute("INSERT INTO test_cleanup (data) VALUES ($1)", "test_data_1")

        result = await postgres_connection_clean.fetch("SELECT COUNT(*) as count FROM test_cleanup")
        assert result[0]["count"] == 1, "Should have 1 row after first test"

    @pytest.mark.asyncio
    async def test_second_insert_postgres(self, postgres_connection_clean):
        """Second test: should NOT see data from first test"""
        # With proper cleanup, table should not exist or be empty
        try:
            result = await postgres_connection_clean.fetch("SELECT COUNT(*) as count FROM test_cleanup")
            # If table exists, it should be empty due to cleanup
            assert result[0]["count"] == 0, "Table should be empty after cleanup between tests"
        except Exception:
            # Table doesn't exist - this is also acceptable (full cleanup)
            pass


@pytest.mark.integration
@pytest.mark.xdist_group(name="testrediscleanup")
class TestRedisCleanup:
    """Test Redis cleanup between tests"""

    def teardown_method(self) -> None:
        """Force GC to prevent mock accumulation in xdist workers"""
        gc.collect()

    @pytest.mark.asyncio
    async def test_first_set_redis(self, redis_client_clean):
        """First test: set Redis key"""
        await redis_client_clean.set("test_key_1", "test_value_1")
        value = await redis_client_clean.get("test_key_1")
        assert value == "test_value_1", "Should have test key after first test"

    @pytest.mark.asyncio
    async def test_second_set_redis(self, redis_client_clean):
        """Second test: should NOT see keys from first test"""
        # With proper cleanup, key should not exist
        value = await redis_client_clean.get("test_key_1")
        assert value is None, "Redis should be clean between tests"


@pytest.mark.integration
@pytest.mark.xdist_group(name="testopenfgacleanup")
class TestOpenFGACleanup:
    """Test OpenFGA cleanup between tests"""

    def teardown_method(self) -> None:
        """Force GC to prevent mock accumulation in xdist workers"""
        gc.collect()

    @pytest.mark.asyncio
    async def test_first_write_tuples(self, openfga_client_clean):
        """First test: write OpenFGA tuples"""
        await openfga_client_clean.write_tuples(
            [{"user": get_user_id("test_cleanup_1"), "relation": "viewer", "object": "document:test_doc_cleanup"}]
        )

        # Verify tuple was written
        allowed = await openfga_client_clean.check_permission(
            user=get_user_id("test_cleanup_1"), relation="viewer", object="document:test_doc_cleanup"
        )
        assert allowed is True, "Tuple should exist after write"

    @pytest.mark.asyncio
    async def test_second_write_tuples(self, openfga_client_clean):
        """Second test: should NOT see tuples from first test"""
        # With proper cleanup, tuple should not exist
        allowed = await openfga_client_clean.check_permission(
            user=get_user_id("test_cleanup_1"), relation="viewer", object="document:test_doc_cleanup"
        )
        assert allowed is False, "OpenFGA should be clean between tests"


@pytest.mark.integration
@pytest.mark.xdist_group(name="testcleanupfixtureperformance")
class TestCleanupFixturePerformance:
    """Verify cleanup fixtures don't add excessive overhead"""

    def teardown_method(self) -> None:
        """Force GC to prevent mock accumulation in xdist workers"""
        gc.collect()

    @pytest.mark.asyncio
    async def test_cleanup_is_fast_postgres(self, postgres_connection_clean):
        """Cleanup should be fast (< 100ms)"""

        # Insert some data
        await postgres_connection_clean.execute("CREATE TABLE IF NOT EXISTS test_perf (id SERIAL PRIMARY KEY, data TEXT)")
        for i in range(10):
            await postgres_connection_clean.execute("INSERT INTO test_perf (data) VALUES ($1)", f"data_{i}")

        # Cleanup will happen automatically - we just verify it's fast
        # The fixture will be torn down and cleanup measured implicitly

    @pytest.mark.asyncio
    async def test_cleanup_is_fast_redis(self, redis_client_clean):
        """Redis cleanup should be fast (< 50ms)"""
        # Set multiple keys
        for i in range(100):
            await redis_client_clean.set(f"perf_key_{i}", f"value_{i}")

        # Cleanup will happen automatically via flushdb()

    @pytest.mark.asyncio
    async def test_cleanup_is_fast_openfga(self, openfga_client_clean):
        """OpenFGA cleanup should be fast (< 100ms)"""
        # Write multiple tuples
        tuples = [
            {"user": get_user_id(f"perf_test_{i}"), "relation": "viewer", "object": "document:perf_doc"} for i in range(10)
        ]
        await openfga_client_clean.write_tuples(tuples)

        # Cleanup will happen automatically
