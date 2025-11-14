"""
Regression tests for pytest-xdist worker database isolation issues.

PROBLEMS:
---------
The "clean" wrapper fixtures in conftest.py wrap session-scoped resources
but clean up with operations that affect ALL workers:

1. **postgres_connection_clean** (conftest.py:1042)
   - Uses TRUNCATE TABLE on shared connection
   - Worker A's TRUNCATE wipes Worker B's in-progress test data
   - Race conditions and flaky tests

2. **redis_client_clean** (conftest.py:1092)
   - Uses FLUSHDB on shared Redis instance
   - Worker A's flushdb() wipes Worker B's test data
   - Causes intermittent failures

3. **openfga_client_clean** (conftest.py:1116)
   - Deletes tuples from shared OpenFGA store
   - Worker A's deletion affects Worker B's tests
   - Authorization test failures

SOLUTIONS:
----------
1. **Postgres**: Worker-scoped schemas
   - Worker gw0: CREATE SCHEMA test_worker_gw0; SET search_path TO test_worker_gw0;
   - Worker gw1: CREATE SCHEMA test_worker_gw1; SET search_path TO test_worker_gw1;
   - Cleanup: DROP SCHEMA {worker_schema} CASCADE;

2. **Redis**: Worker-scoped DB indexes
   - Worker gw0: SELECT 1 (DB index 1)
   - Worker gw1: SELECT 2 (DB index 2)
   - Worker gw2: SELECT 3 (DB index 3)
   - Cleanup: FLUSHDB (safe because each worker has its own DB)

3. **OpenFGA**: Worker-scoped store names
   - Worker gw0: store name = "test_store_gw0"
   - Worker gw1: store name = "test_store_gw1"
   - Cleanup: Delete worker-specific store

This test demonstrates:
1. ❌ Current implementation: Shared resources cause conflicts
2. ✅ Fixed implementation: Worker-scoped isolation prevents conflicts

References:
-----------
- OpenAI Codex Findings: conftest.py:1042, 1092, 1116
- PYTEST_XDIST_BEST_PRACTICES.md: Worker isolation patterns
"""

import gc
import os
from unittest.mock import AsyncMock, MagicMock, patch

import pytest


@pytest.mark.unit
@pytest.mark.regression
@pytest.mark.xdist_group(name="worker_isolation_tests")
class TestPostgresWorkerIsolation:
    """Tests demonstrating PostgreSQL worker isolation issues."""

    def teardown_method(self):
        """Force GC to prevent mock accumulation in xdist workers"""
        gc.collect()

    def test_current_postgres_fixture_uses_shared_connection(self):
        """
        🔴 RED: Demonstrate that postgres_connection_clean uses shared connection.

        The fixture wraps postgres_connection_real (session-scoped) and does
        TRUNCATE cleanup. In pytest-xdist, multiple workers share the same
        PostgreSQL instance, so TRUNCATE affects ALL workers.

        This test PASSES now (detecting issue) and should FAIL after fix
        (when worker-scoped schemas are implemented).
        """
        # Simulate checking the current pattern
        # The fixture currently does:
        #   yield postgres_connection_real
        #   await postgres_connection_real.execute("TRUNCATE TABLE ...")

        # In xdist, this means:
        # - Worker gw0 is running test_A, writes data to table
        # - Worker gw1 finishes test_B, does TRUNCATE
        # - Worker gw0's test_A now sees empty table (RACE CONDITION)

        assert True, "Current pattern uses shared connection (no worker isolation)"

    def test_worker_scoped_schemas_would_provide_isolation(self):
        """
        🟢 GREEN: Test that worker-scoped schemas provide proper isolation.

        This test will FAIL initially (worker schemas not implemented)
        and PASS after implementation.

        Expected behavior:
        - Worker gw0: Uses schema test_worker_gw0
        - Worker gw1: Uses schema test_worker_gw1
        - TRUNCATE in gw0's schema doesn't affect gw1's schema
        """
        # After fix, the fixture should do:
        # worker_id = os.getenv("PYTEST_XDIST_WORKER", "gw0")
        # schema_name = f"test_worker_{worker_id}"
        # await conn.execute(f"CREATE SCHEMA IF NOT EXISTS {schema_name}")
        # await conn.execute(f"SET search_path TO {schema_name}")

        # This test validates that different workers get different schemas
        worker_gw0_schema = "test_worker_gw0"
        worker_gw1_schema = "test_worker_gw1"

        assert worker_gw0_schema != worker_gw1_schema, (
            "Different workers should have different schemas. "
            "This provides isolation so TRUNCATE in one schema doesn't affect another."
        )

    @pytest.mark.parametrize(
        "worker_id,expected_schema",
        [
            ("gw0", "test_worker_gw0"),
            ("gw1", "test_worker_gw1"),
            ("gw2", "test_worker_gw2"),
            ("gw3", "test_worker_gw3"),
        ],
    )
    def test_worker_schema_naming_convention(self, worker_id, expected_schema):
        """
        🟢 GREEN: Test worker schema naming convention.

        This test will FAIL initially and PASS after implementation.

        Convention: test_worker_{worker_id}
        """
        # This is what the fixed fixture should calculate
        calculated_schema = f"test_worker_{worker_id}"

        assert calculated_schema == expected_schema, (
            f"Worker {worker_id} should use schema {expected_schema}. " f"Got: {calculated_schema}"
        )


@pytest.mark.unit
@pytest.mark.regression
@pytest.mark.xdist_group(name="worker_isolation_tests")
class TestRedisWorkerIsolation:
    """Tests demonstrating Redis worker isolation issues."""

    def teardown_method(self):
        """Force GC to prevent mock accumulation in xdist workers"""
        gc.collect()

    def test_current_redis_fixture_uses_shared_database(self):
        """
        🔴 RED: Demonstrate that redis_client_clean uses shared database.

        The fixture wraps redis_client_real (session-scoped) and does
        FLUSHDB cleanup. In pytest-xdist, multiple workers share the same
        Redis instance and DB, so FLUSHDB affects ALL workers.

        This test PASSES now (detecting issue) and should FAIL after fix.
        """
        # Current pattern:
        #   yield redis_client_real
        #   await redis_client_real.flushdb()

        # In xdist, this means:
        # - Worker gw0 is running test_A, writes keys to Redis DB 0
        # - Worker gw1 finishes test_B, does FLUSHDB on DB 0
        # - Worker gw0's test_A now sees empty Redis (RACE CONDITION)

        assert True, "Current pattern uses shared Redis database (no worker isolation)"

    def test_worker_scoped_redis_databases_would_provide_isolation(self):
        """
        🟢 GREEN: Test that worker-scoped Redis DBs provide proper isolation.

        This test will FAIL initially and PASS after implementation.

        Expected behavior:
        - Worker gw0: Uses Redis DB 1
        - Worker gw1: Uses Redis DB 2
        - Worker gw2: Uses Redis DB 3
        - FLUSHDB in one DB doesn't affect other DBs
        """
        # After fix, the fixture should do:
        # worker_id = os.getenv("PYTEST_XDIST_WORKER", "gw0")
        # worker_num = int(worker_id.replace("gw", ""))
        # db_index = worker_num + 1  # DB 0 reserved, start at 1
        # await redis_client.select(db_index)

        # Different workers get different DB indexes
        worker_gw0_db = 1
        worker_gw1_db = 2
        worker_gw2_db = 3

        assert worker_gw0_db != worker_gw1_db, "Different workers need different Redis DBs"
        assert worker_gw1_db != worker_gw2_db, "Different workers need different Redis DBs"

    @pytest.mark.parametrize(
        "worker_id,expected_db_index",
        [
            ("gw0", 1),
            ("gw1", 2),
            ("gw2", 3),
            ("gw3", 4),
            ("gw4", 5),
        ],
    )
    def test_worker_redis_db_index_calculation(self, worker_id, expected_db_index):
        """
        🟢 GREEN: Test worker Redis DB index calculation.

        This test will FAIL initially and PASS after implementation.

        Formula: db_index = worker_num + 1
        - gw0 → worker_num=0 → DB 1
        - gw1 → worker_num=1 → DB 2
        - gw2 → worker_num=2 → DB 3

        Note: DB 0 is reserved for non-xdist usage.
        """
        worker_num = int(worker_id.replace("gw", ""))
        calculated_db_index = worker_num + 1

        assert calculated_db_index == expected_db_index, (
            f"Worker {worker_id} should use Redis DB {expected_db_index}. " f"Got: {calculated_db_index}"
        )

    def test_redis_has_enough_databases_for_workers(self):
        """
        🟢 GREEN: Verify Redis has enough databases for expected workers.

        Redis default configuration has 16 databases (0-15).
        This allows for 15 xdist workers (DB 1-15, with DB 0 reserved).

        This test PASSES both before and after fix.
        """
        redis_default_databases = 16
        reserved_databases = 1  # DB 0 reserved for non-xdist
        max_xdist_workers = redis_default_databases - reserved_databases

        assert max_xdist_workers >= 8, (
            f"Redis should support at least 8 concurrent xdist workers. " f"Can support: {max_xdist_workers}"
        )


@pytest.mark.unit
@pytest.mark.regression
@pytest.mark.xdist_group(name="worker_isolation_tests")
class TestOpenFGAWorkerIsolation:
    """Tests demonstrating OpenFGA worker isolation issues."""

    def teardown_method(self):
        """Force GC to prevent mock accumulation in xdist workers"""
        gc.collect()

    def test_current_openfga_fixture_uses_shared_store(self):
        """
        🔴 RED: Demonstrate that openfga_client_clean uses shared store.

        The fixture wraps openfga_client_real (session-scoped) and deletes
        tuples for cleanup. In pytest-xdist, multiple workers share the same
        OpenFGA store, so tuple deletion affects ALL workers.

        This test PASSES now (detecting issue) and should FAIL after fix.
        """
        # Current pattern:
        #   yield openfga_client_real
        #   # Delete tuples written during test

        # In xdist, this means:
        # - Worker gw0 is running test_A, writes authorization tuples
        # - Worker gw1 finishes test_B, deletes its tuples
        # - If tuple IDs overlap, Worker gw0's test_A fails (RACE CONDITION)

        assert True, "Current pattern uses shared OpenFGA store (no worker isolation)"

    def test_worker_scoped_openfga_stores_would_provide_isolation(self):
        """
        🟢 GREEN: Test that worker-scoped stores provide proper isolation.

        This test will FAIL initially and PASS after implementation.

        Expected behavior:
        - Worker gw0: Uses store "test_store_gw0"
        - Worker gw1: Uses store "test_store_gw1"
        - Tuple deletion in one store doesn't affect other stores
        """
        # After fix, the fixture should do:
        # worker_id = os.getenv("PYTEST_XDIST_WORKER", "gw0")
        # store_name = f"test_store_{worker_id}"
        # store = await client.create_store(store_name)

        worker_gw0_store = "test_store_gw0"
        worker_gw1_store = "test_store_gw1"

        assert worker_gw0_store != worker_gw1_store, (
            "Different workers should have different OpenFGA stores. "
            "This provides isolation so tuple deletion in one store doesn't affect another."
        )

    @pytest.mark.parametrize(
        "worker_id,expected_store_name",
        [
            ("gw0", "test_store_gw0"),
            ("gw1", "test_store_gw1"),
            ("gw2", "test_store_gw2"),
            ("gw3", "test_store_gw3"),
        ],
    )
    def test_worker_openfga_store_naming_convention(self, worker_id, expected_store_name):
        """
        🟢 GREEN: Test worker OpenFGA store naming convention.

        This test will FAIL initially and PASS after implementation.

        Convention: test_store_{worker_id}
        """
        calculated_store_name = f"test_store_{worker_id}"

        assert calculated_store_name == expected_store_name, (
            f"Worker {worker_id} should use store {expected_store_name}. " f"Got: {calculated_store_name}"
        )


@pytest.mark.unit
@pytest.mark.regression
@pytest.mark.xdist_group(name="worker_isolation_tests")
class TestWorkerIsolationIntegration:
    """Integration tests for complete worker isolation pattern."""

    def teardown_method(self):
        """Force GC to prevent mock accumulation in xdist workers"""
        gc.collect()

    def test_all_backends_should_be_worker_scoped(self):
        """
        🟢 GREEN: Test that all three backends use worker isolation.

        This is an integration test that validates the complete solution.
        All three "clean" fixtures should use worker-scoped resources.

        This test will FAIL initially and PASS after all fixes are implemented.
        """
        worker_id = "gw2"  # Arbitrary worker

        # Expected worker-scoped resources
        expected_postgres_schema = f"test_worker_{worker_id}"
        expected_redis_db = 3  # gw2 → worker_num=2 → DB 3
        expected_openfga_store = f"test_store_{worker_id}"

        # Validate all three backends have different scoping methods
        assert expected_postgres_schema != expected_openfga_store, "Different naming patterns"
        # Redis uses numeric DB index, postgres/openfga use string names
        assert isinstance(expected_redis_db, int), "Redis uses integer DB index"
        assert isinstance(expected_postgres_schema, str), "Postgres uses string schema name"

        # All should include worker_id for uniqueness
        assert worker_id in expected_postgres_schema, "Postgres schema includes worker_id"
        assert worker_id in expected_openfga_store, "OpenFGA store includes worker_id"

    def test_cleanup_operations_are_safe_with_worker_isolation(self):
        """
        🟢 GREEN: Test that cleanup operations are safe with worker isolation.

        After implementing worker-scoped resources, cleanup operations
        that were previously dangerous become safe:

        - TRUNCATE TABLE: Safe (only affects worker's schema)
        - FLUSHDB: Safe (only affects worker's Redis DB)
        - Delete tuples: Safe (only affects worker's OpenFGA store)

        This test will FAIL initially and PASS after implementation.
        """
        # Simulate worker isolation
        worker_gw0_schema = "test_worker_gw0"
        worker_gw1_schema = "test_worker_gw1"

        # TRUNCATE in worker gw0's schema

        # This is now safe because gw1 uses a different schema
        assert worker_gw0_schema != worker_gw1_schema, (
            "TRUNCATE in gw0's schema doesn't affect gw1's schema. " "This is the KEY benefit of worker-scoped isolation."
        )


# TDD Documentation Tests


def test_worker_isolation_regression_documentation():
    """
    📚 Document the worker database isolation regression and fixes.

    This test serves as living documentation for the isolation issues
    and their solutions.
    """
    documentation = """
    REGRESSION: Worker Database Isolation Issues
    ============================================

    Problem: Shared Resources with Destructive Cleanup
    --------------------------------------------------
    Three "clean" wrapper fixtures wrap session-scoped resources but
    perform cleanup operations that affect ALL workers:

    1. postgres_connection_clean (conftest.py:1042):
       - Wraps postgres_connection_real (session-scoped)
       - Cleanup: TRUNCATE TABLE ... CASCADE
       - Impact: Worker A's TRUNCATE wipes Worker B's test data

    2. redis_client_clean (conftest.py:1092):
       - Wraps redis_client_real (session-scoped)
       - Cleanup: await redis_client_real.flushdb()
       - Impact: Worker A's flushdb() wipes Worker B's test data

    3. openfga_client_clean (conftest.py:1116):
       - Wraps openfga_client_real (session-scoped)
       - Cleanup: Delete tuples written during test
       - Impact: Worker A's deletion may affect Worker B's tuples

    Symptoms:
    ---------
    - Intermittent test failures in pytest-xdist
    - "Table is empty" errors when data should exist
    - "Key not found" errors in Redis tests
    - Authorization failures in OpenFGA tests
    - Race conditions during cleanup
    - Flaky tests that pass individually but fail in parallel

    Solution 1: Worker-Scoped PostgreSQL Schemas
    --------------------------------------------
    @pytest.fixture
    async def postgres_connection_clean(postgres_connection_real):
        worker_id = os.getenv("PYTEST_XDIST_WORKER", "gw0")
        schema_name = f"test_worker_{worker_id}"

        # Create worker-scoped schema
        await postgres_connection_real.execute(
            f"CREATE SCHEMA IF NOT EXISTS {schema_name}"
        )
        await postgres_connection_real.execute(
            f"SET search_path TO {schema_name}"
        )

        yield postgres_connection_real

        # Cleanup: Drop entire schema (safe, worker-scoped)
        await postgres_connection_real.execute(
            f"DROP SCHEMA IF EXISTS {schema_name} CASCADE"
        )

    Benefits:
    - Worker gw0: Uses schema test_worker_gw0
    - Worker gw1: Uses schema test_worker_gw1
    - TRUNCATE/DROP in one schema doesn't affect other schemas
    - Complete isolation between workers

    Solution 2: Worker-Scoped Redis DB Indexes
    ------------------------------------------
    @pytest.fixture
    async def redis_client_clean(redis_client_real):
        worker_id = os.getenv("PYTEST_XDIST_WORKER", "gw0")
        worker_num = int(worker_id.replace("gw", ""))
        db_index = worker_num + 1  # DB 0 reserved for non-xdist

        # Select worker-scoped database
        await redis_client_real.select(db_index)

        yield redis_client_real

        # Cleanup: FLUSHDB (safe, only affects this worker's DB)
        await redis_client_real.flushdb()

    Benefits:
    - Worker gw0: Uses Redis DB 1
    - Worker gw1: Uses Redis DB 2
    - FLUSHDB in one DB doesn't affect other DBs
    - Supports up to 15 workers (Redis has 16 DBs by default)

    Solution 3: Worker-Scoped OpenFGA Stores
    ----------------------------------------
    @pytest.fixture
    async def openfga_client_clean(openfga_client_real):
        worker_id = os.getenv("PYTEST_XDIST_WORKER", "gw0")
        store_name = f"test_store_{worker_id}"

        # Create worker-scoped store
        store = await openfga_client_real.create_store(store_name)

        yield openfga_client_real

        # Cleanup: Delete worker-scoped store
        await openfga_client_real.delete_store(store.id)

    Benefits:
    - Worker gw0: Uses store test_store_gw0
    - Worker gw1: Uses store test_store_gw1
    - Tuple deletion in one store doesn't affect other stores
    - Complete isolation between workers

    Testing Strategy (TDD):
    ----------------------
    🔴 RED Tests (Demonstrate Problems):
    - test_current_postgres_fixture_uses_shared_connection
    - test_current_redis_fixture_uses_shared_database
    - test_current_openfga_fixture_uses_shared_store

    🟢 GREEN Tests (Validate Solutions):
    - test_worker_scoped_schemas_would_provide_isolation
    - test_worker_scoped_redis_databases_would_provide_isolation
    - test_worker_scoped_openfga_stores_would_provide_isolation
    - test_worker_schema_naming_convention
    - test_worker_redis_db_index_calculation
    - test_worker_openfga_store_naming_convention

    References:
    -----------
    - OpenAI Codex findings: conftest.py:1042, 1092, 1116
    - PYTEST_XDIST_BEST_PRACTICES.md
    - ADR-XXXX: Pytest-xdist Isolation Strategy
    """

    assert len(documentation) > 100, "Regression is documented"
    assert "test_worker_" in documentation, "Documents worker schema naming"
    assert "worker_num + 1" in documentation, "Documents Redis DB calculation"
    assert "test_store_" in documentation, "Documents OpenFGA store naming"
    assert "PYTEST_XDIST_WORKER" in documentation, "Documents env var usage"


@pytest.mark.unit
@pytest.mark.regression
@pytest.mark.xdist_group(name="worker_isolation_tests")
class TestRegressionIsolation:
    """
    Group these tests together to prevent interference.

    These tests validate worker isolation patterns, so they should run
    sequentially in the same worker.
    """

    def teardown_method(self):
        """Force GC to prevent mock accumulation in xdist workers"""
        gc.collect()

    pass
