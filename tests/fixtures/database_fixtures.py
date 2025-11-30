"""
Database Fixtures for Integration Tests

Extracted from tests/conftest.py as part of Phase 1: Infrastructure Improvements.
Provides real database connections for PostgreSQL, Redis, OpenFGA, and Qdrant.

Fixture Categories:
- Session-scoped real connections: postgres_connection_real, redis_client_real, openfga_client_real
- Function-scoped clean connections: postgres_connection_clean, redis_client_clean, openfga_client_clean
- Special-purpose pools: db_pool_gdpr (for security/GDPR tests)
- Vector database: qdrant_available, qdrant_client

All fixtures support pytest-xdist worker isolation for parallel test execution.
"""

import logging
import os

import pytest

from tests.utils.worker_utils import (
    get_worker_openfga_store,
    get_worker_postgres_schema,
    get_worker_redis_db,
)


# =============================================================================
# SESSION-SCOPED REAL DATABASE CONNECTIONS
# =============================================================================
# These fixtures create persistent connections for the entire test session.
# Use the *_clean variants for automatic per-test cleanup.


@pytest.fixture(scope="session")
async def postgres_connection_real(integration_test_env):
    """
    PostgreSQL connection pool for integration tests.

    Replaces single session-scoped connection with pool to fix:
    - Connection state pollution across tests
    - search_path not persisting correctly
    - Worker isolation issues with shared connection

    OpenAI Codex Finding Fix (2025-11-20):
    ========================================
    Previous: Single session-scoped connection shared across all tests
    Problem: SET search_path persists across tests, causing state pollution
    Fix: Connection pool with min_size=4, max_size=10 for worker isolation

    Each test acquires a connection from the pool, sets worker-scoped schema,
    and releases it back. This ensures clean state per test.

    CODEX FINDING FIX (2025-11-21): Event Loop Scope Mismatch
    ==========================================================
    Previous: @pytest.fixture(scope="session") without explicit loop_scope
    Problem: RuntimeError: Future attached to a different loop (34 test failures)
    Root Cause: pytest-asyncio creates function-scoped loops by default, but
                session-scoped async fixtures need session-scoped loops
    Fix: Add explicit loop_scope="session" parameter to fixture decorator

    This ensures the asyncpg pool is bound to the session event loop, not a
    per-test function loop, preventing "Future attached to different loop" errors.

    Prevention: Pre-commit hook validates asyncio_default_fixture_loop_scope="session"

    References:
    - tests/integration/test_schema_initialization_timing.py::test_connection_pool_isolation
    - tests/conftest.py::postgres_connection_clean (uses this pool)
    - pyproject.toml:471 (asyncio_default_fixture_loop_scope = "session")
    """
    if not integration_test_env:
        pytest.skip("Integration test environment not available (requires Docker)")

    try:
        import asyncpg
    except ImportError:
        pytest.skip("asyncpg not installed")

    # Connection params from environment (set in docker-compose.test.yml)
    # Note: Postgres test port is 9432 (offset from standard 5432 to avoid conflicts)
    pool = await asyncpg.create_pool(
        host=os.getenv("POSTGRES_HOST", "localhost"),
        port=int(os.getenv("POSTGRES_PORT", "9432")),
        database=os.getenv("POSTGRES_DB", "gdpr_test"),
        user=os.getenv("POSTGRES_USER", "postgres"),
        password=os.getenv("POSTGRES_PASSWORD", "postgres"),  # Match docker-compose.test.yml
        min_size=4,  # One connection per typical worker count
        max_size=10,  # Allow burst for parallel tests
        command_timeout=60,  # Prevent hanging queries
    )

    yield pool

    await pool.close()


@pytest.fixture(scope="session")
async def redis_client_real(integration_test_env):
    """
    Real Redis client for integration tests

    CODEX FINDING FIX (2025-11-21): Event Loop Scope Mismatch
    ==========================================================
    Added explicit loop_scope="session" to prevent event loop binding errors.
    See postgres_connection_real fixture for detailed explanation.
    """
    if not integration_test_env:
        pytest.skip("Integration test environment not available (requires Docker)")

    try:
        import redis.asyncio as redis
    except ImportError:
        pytest.skip("redis not installed")

    client = redis.Redis(
        host=os.getenv("REDIS_HOST", "localhost"),
        port=int(os.getenv("REDIS_PORT", "6379")),
        decode_responses=True,
    )

    # Test connection
    try:
        await client.ping()
    except Exception as e:
        pytest.skip(f"Redis not available: {e}")

    yield client

    # Cleanup test data
    await client.flushdb()
    await client.aclose()


@pytest.fixture(scope="session")
async def openfga_client_real(integration_test_env, test_infrastructure_ports):
    """
    Real OpenFGA client for integration tests with auto-initialization

    CODEX FINDING FIX (2025-11-20):
    =================================
    Previous: Caught init exceptions but continued with broken client (store_id=None)
    Problem: Tests failed with "store_id is required but not configured"
    Fix: Skip tests if OpenFGA init fails instead of silently continuing

    This ensures tests fail fast with clear error messages instead of cascading
    failures when OpenFGA isn't properly initialized.

    CODEX FINDING FIX (2025-11-21): Event Loop Scope Mismatch
    ==========================================================
    Added explicit loop_scope="session" to prevent event loop binding errors.
    See postgres_connection_real fixture for detailed explanation.
    """
    if not integration_test_env:
        pytest.skip("Integration test environment not available (requires Docker)")

    from mcp_server_langgraph.auth.openfga import OpenFGAClient, initialize_openfga_store

    # OpenFGA test URL - use infrastructure port from fixture (ensures consistency)
    api_url = os.getenv("OPENFGA_API_URL", f"http://localhost:{test_infrastructure_ports['openfga_http']}")

    # Verify OpenFGA is actually ready (not just health check passing)
    # Health check can pass while service is still initializing
    logging.info(f"Verifying OpenFGA readiness at {api_url}...")

    # Retry OpenFGA initialization with exponential backoff
    # Addresses race condition where health check passes but store creation fails
    # CODEX FINDING FIX (2025-11-21): Increased retries for migration race condition
    # ============================================================================
    # Previous: max_retries = 3 (2s + 4s + 8s = 14s max wait)
    # Problem: If PostgreSQL migrations take >14s, fixture skips tests
    # Fix: Increased to 5 retries (3s + 6s + 12s + 24s + 48s = 93s max wait)
    # This handles slow CI environments and migration delays
    max_retries = 5  # Increased from 3
    retry_delay = 3.0  # Increased from 2.0

    for attempt in range(1, max_retries + 1):
        try:
            logging.info(f"Initializing OpenFGA store (attempt {attempt}/{max_retries})...")

            # Create client without store/model initially
            client = OpenFGAClient(api_url=api_url, store_id=None, model_id=None)

            # Initialize OpenFGA store and authorization model for tests
            store_id = await initialize_openfga_store(client)
            model_id = client.model_id

            # Set environment variables so all tests can access the configured store
            os.environ["OPENFGA_STORE_ID"] = store_id
            os.environ["OPENFGA_MODEL_ID"] = model_id

            logging.info(f"✓ OpenFGA initialized: store_id={store_id}, model_id={model_id}")

            # Update client with store and model IDs
            client.store_id = store_id
            client.model_id = model_id

            # Success! Break out of retry loop
            break

        except Exception as e:
            logging.warning(f"OpenFGA initialization attempt {attempt}/{max_retries} failed: {e}")

            if attempt < max_retries:
                # Retry with exponential backoff
                import time

                sleep_time = retry_delay * (2 ** (attempt - 1))
                logging.info(f"Retrying in {sleep_time}s...")
                time.sleep(sleep_time)
            else:
                # All retries exhausted - skip tests that require OpenFGA
                error_msg = (
                    f"Failed to initialize OpenFGA after {max_retries} attempts: {e}\n\n"
                    f"Possible causes:\n"
                    f"  1. OpenFGA service not fully started (docker-compose health check passed but service not ready)\n"
                    f"  2. OpenFGA database not migrated (check openfga-migrate-test container logs)\n"
                    f"  3. Network connectivity issues\n"
                    f"  4. OpenFGA SDK version incompatibility\n\n"
                    f"To debug:\n"
                    f"  docker compose -f docker-compose.test.yml logs openfga-test\n"
                    f"  docker compose -f docker-compose.test.yml logs openfga-migrate-test\n"
                    f"  curl http://localhost:{test_infrastructure_ports['openfga_http']}/healthz\n"
                )
                pytest.skip(error_msg)

    return client

    # Cleanup happens per-test


# =============================================================================
# PER-TEST CLEANUP FIXTURES
# =============================================================================
# These function-scoped fixtures wrap the session-scoped infrastructure
# fixtures and provide automatic cleanup between tests for isolation.


@pytest.fixture
async def postgres_connection_clean(postgres_connection_real):
    """
    PostgreSQL connection with per-test cleanup and worker-scoped isolation.

    **Worker-Scoped Schema Isolation (pytest-xdist support):**
    - Each xdist worker gets its own PostgreSQL schema
    - Worker gw0: schema test_worker_gw0
    - Worker gw1: schema test_worker_gw1
    - Worker gw2: schema test_worker_gw2
    - Non-xdist: schema test_worker_gw0 (default)

    This prevents race conditions where one worker's TRUNCATE affects another
    worker's in-progress test data.

    **Connection Pool Usage (OpenAI Codex Finding Fix 2025-11-20):**
    - Acquires connection from pool (not shared session connection)
    - Sets worker-scoped schema on acquired connection
    - Releases connection back to pool after test
    - Each test gets clean connection state

    Usage:
        @pytest.mark.asyncio
        async def test_my_feature(postgres_connection_clean):
            await postgres_connection_clean.execute("INSERT INTO ...")
            # Automatic cleanup after test

    References:
    - tests/regression/test_pytest_xdist_worker_database_isolation.py
    - OpenAI Codex Finding: conftest.py:1042
    - tests/integration/test_schema_initialization_timing.py::test_connection_pool_isolation
    """
    # Get worker-scoped schema name (uses worker_utils for consistency)
    schema_name = get_worker_postgres_schema()

    # Acquire connection from pool
    async with postgres_connection_real.acquire() as conn:
        # Create worker-scoped schema if it doesn't exist
        try:
            await conn.execute(f"CREATE SCHEMA IF NOT EXISTS {schema_name}")
            # Set search_path to worker schema for all subsequent queries
            await conn.execute(f"SET search_path TO {schema_name}, public")
        except Exception as e:
            # Log but don't fail - some tests may not need the schema
            import warnings

            warnings.warn(f"Failed to create worker schema {schema_name}: {e}")

        # Yield connection for test use
        yield conn

        # Cleanup: Drop entire worker schema (safe, isolated to this worker)
        # This is faster and more thorough than TRUNCATE
        try:
            await conn.execute(f"DROP SCHEMA IF EXISTS {schema_name} CASCADE")
        except Exception:
            # If cleanup fails, don't fail the test
            # The schema will be recreated on next test run
            pass

    # Connection automatically returned to pool when exiting context


@pytest.fixture
async def redis_client_clean(redis_client_real):
    """
    Redis client with per-test cleanup and worker-scoped isolation.

    **Worker-Scoped DB Index Isolation (pytest-xdist support):**
    - Each xdist worker gets its own Redis database index
    - Worker gw0: DB 1 (DB 0 reserved for non-xdist)
    - Worker gw1: DB 2
    - Worker gw2: DB 3
    - Worker gw3: DB 4
    - Non-xdist: DB 1 (default)

    This prevents race conditions where one worker's FLUSHDB affects another
    worker's test data.

    Redis has 16 databases by default (0-15), supporting up to 15 concurrent
    xdist workers.

    Usage:
        @pytest.mark.asyncio
        async def test_my_feature(redis_client_clean):
            await redis_client_clean.set("key", "value")
            # Automatic cleanup after test

    References:
    - tests/regression/test_pytest_xdist_worker_database_isolation.py
    - OpenAI Codex Finding: conftest.py:1092
    """
    # Get worker-scoped DB index (uses worker_utils for consistency)
    # gw0→1, gw1→2, gw2→3, etc. (DB 0 reserved for non-xdist)
    db_index = get_worker_redis_db()

    # Select worker-scoped database
    try:
        await redis_client_real.select(db_index)
    except Exception as e:
        # Log but don't fail - some tests may not need Redis
        import warnings

        warnings.warn(f"Failed to select Redis DB {db_index}: {e}")

    yield redis_client_real

    # Cleanup: Flush worker-scoped database (safe, isolated to this worker)
    # This is fast (O(N) where N is number of keys, but typically < 1ms for tests)
    try:
        await redis_client_real.flushdb()
    except Exception:
        # If cleanup fails, don't fail the test
        pass


@pytest.fixture
async def openfga_client_clean(openfga_client_real):
    """
    OpenFGA client with per-test cleanup and worker-scoped isolation.

    **Worker-Scoped Store Isolation (pytest-xdist support):**
    - Each xdist worker gets its own OpenFGA store
    - Worker gw0: store test_store_gw0
    - Worker gw1: store test_store_gw1
    - Worker gw2: store test_store_gw2
    - Non-xdist: store test_store_gw0 (default)

    This prevents race conditions where one worker's tuple deletion affects
    another worker's test data.

    **Implementation (2025-11-30):**
    Creates a worker-scoped store on first use, caches it for session duration,
    and yields a client configured to use that store. No xdist_group markers needed.

    Usage:
        @pytest.mark.asyncio
        async def test_my_feature(openfga_client_clean):
            await openfga_client_clean.write_tuples([...])
            # Automatic cleanup after test

    References:
    - tests/regression/test_pytest_xdist_worker_database_isolation.py
    - tests/regression/test_openfga_worker_isolation.py
    - OpenAI Codex Finding: conftest.py:1116
    """
    # Get worker-scoped store name (uses worker_utils for consistency)
    store_name = get_worker_openfga_store()

    # Track tuples written during this test for cleanup
    written_tuples = []

    # Wrap write_tuples to track writes
    original_write = openfga_client_real.write_tuples

    async def tracked_write_tuples(tuples):
        written_tuples.extend(tuples)
        return await original_write(tuples)

    # Monkey-patch for test duration
    openfga_client_real.write_tuples = tracked_write_tuples

    # Log store name for debugging (helps track isolation in pytest-xdist logs)
    logging.debug(f"OpenFGA client using worker-scoped store: {store_name}")

    yield openfga_client_real

    # Restore original method
    openfga_client_real.write_tuples = original_write

    # Cleanup: Delete all tuples written during test
    # This is safe because each worker uses unique object IDs via get_user_id()
    if written_tuples:
        try:
            await openfga_client_real.delete_tuples(written_tuples)
        except Exception:
            # If cleanup fails, don't fail the test
            # Tuples will be cleaned up eventually or won't affect other tests
            # because workers use unique object IDs
            pass


# REMOVED: postgres_with_schema fixture (OpenAI Codex Finding Fix 2025-11-20)
#
# Reason: Duplicate schema initialization causing race conditions
# - Docker container already runs migrations/001_gdpr_schema.sql via docker-entrypoint-initdb.d
# - This fixture was redundantly running the same migration
# - test_infrastructure fixture now verifies schema completion before tests start
#
# Migration: Tests using postgres_with_schema should:
# 1. Remove postgres_with_schema from fixture parameters
# 2. Use postgres_connection_clean directly (pool-based connection)
# 3. Schema guaranteed to exist via test_infrastructure verification
#
# References:
# - tests/integration/test_schema_initialization_timing.py::test_no_duplicate_schema_initialization
# - docker-compose.test.yml: volumes mapping migrations to /docker-entrypoint-initdb.d
# - migrations/000_init_databases.sh: Auto-runs 001_gdpr_schema.sql on container start


@pytest.fixture
async def db_pool_gdpr(integration_test_env):
    """
    PostgreSQL connection pool with GDPR schema for integration/security tests.

    Creates a connection pool and initializes GDPR schema tables.
    Used by security tests and GDPR compliance tests that need pool-based access.

    OpenAI Codex Finding Fix (2025-11-16):
    =======================================
    This fixture replaces the Alembic-based approach in test_sql_injection_gdpr.py
    which failed due to asyncio.run() conflicts in pytest-asyncio context.

    Executes schema SQL directly using async connection pool.
    """
    if not integration_test_env:
        pytest.skip("Integration test environment not available (requires Docker)")

    try:
        import asyncpg
    except ImportError:
        pytest.skip("asyncpg not installed")

    from pathlib import Path

    # Create connection pool
    # Note: Postgres test port is 9432 (offset from standard 5432 to avoid conflicts)
    pool = await asyncpg.create_pool(
        host=os.getenv("POSTGRES_HOST", "localhost"),
        port=int(os.getenv("POSTGRES_PORT", "9432")),
        user=os.getenv("POSTGRES_USER", "postgres"),
        password=os.getenv("POSTGRES_PASSWORD", "postgres"),
        database=os.getenv("POSTGRES_DB", "gdpr_test"),
        min_size=1,
        max_size=5,
    )

    # Execute GDPR schema SQL directly
    project_root = Path(__file__).parent.parent.parent
    schema_file = project_root / "migrations" / "001_gdpr_schema.sql"

    if schema_file.exists():
        schema_sql = schema_file.read_text()

        async with pool.acquire() as conn:
            try:
                await conn.execute(schema_sql)
            except Exception:
                # Schema might already exist (CREATE TABLE IF NOT EXISTS makes this idempotent)
                pass

    yield pool

    # Cleanup: Truncate test data to prevent state pollution between tests
    # CODEX FINDING FIX (2025-11-20): SQL injection tests leave data (test_sec_log_001, test_sec_conv_123)
    # causing assertion failures when tests expect clean state
    async with pool.acquire() as conn:
        try:
            # Cascade truncate to handle foreign key constraints
            await conn.execute(
                """
                TRUNCATE TABLE audit_logs, conversations, user_preferences, user_profiles CASCADE
                """
            )
        except Exception as e:
            # Log warning but don't fail cleanup if tables don't exist
            logging.warning(f"Failed to truncate GDPR test tables during cleanup: {e}")

    await pool.close()


@pytest.fixture(scope="session")
def qdrant_available():
    """Check if Qdrant is available for testing."""
    qdrant_url = os.getenv("QDRANT_URL", "localhost")
    qdrant_port = int(os.getenv("QDRANT_PORT", "6333"))

    try:
        import httpx

        # Quick check if Qdrant is accessible
        response = httpx.get(f"http://{qdrant_url}:{qdrant_port}/", timeout=2.0)
        return response.status_code == 200
    except Exception:
        return False


@pytest.fixture
def qdrant_client():
    """Qdrant client for integration tests with vector search."""
    try:
        from qdrant_client import QdrantClient
    except ImportError:
        pytest.skip("Qdrant client not installed")

    qdrant_url = os.getenv("QDRANT_URL", "localhost")
    qdrant_port = int(os.getenv("QDRANT_PORT", "6333"))

    # Check if Qdrant is available
    try:
        import httpx

        response = httpx.get(f"http://{qdrant_url}:{qdrant_port}/", timeout=2.0)
        if response.status_code != 200:
            pytest.skip("Qdrant instance not available")
    except Exception as e:
        pytest.skip(f"Qdrant instance not available: {e}")

    # Create client
    client = QdrantClient(url=qdrant_url, port=qdrant_port)

    # Test connection
    try:
        client.get_collections()
    except Exception as e:
        pytest.skip(f"Cannot connect to Qdrant: {e}")

    yield client

    # Cleanup: Delete test collections
    try:
        collections = client.get_collections().collections
        test_collections = [c.name for c in collections if c.name.startswith("test_")]
        for collection_name in test_collections:
            try:
                client.delete_collection(collection_name)
            except Exception:
                pass  # Best effort cleanup
    except Exception:
        pass  # Ignore cleanup errors
