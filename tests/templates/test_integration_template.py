"""
Integration Test Template - xdist-Compatible Pattern

This template provides a cookiecutter pattern for creating integration tests
that work with real infrastructure (PostgreSQL, Redis, Keycloak, OpenFGA)
while maintaining pytest-xdist compatibility.

NOTE: This is a TEMPLATE file, not an actual test file. It contains placeholder
code with intentionally unused variables to demonstrate patterns. Copy and rename
to test_<feature>_integration.py before using.

USAGE:
1. Copy this file to tests/integration/<feature>/
2. Rename to test_<feature>_integration.py
3. Replace placeholder content with your test implementation
4. Use real infrastructure fixtures from tests/conftest.py

INTEGRATION TEST CHARACTERISTICS:
- Tests components working together
- Uses real dependencies (PostgreSQL, Redis, etc.)
- May be slower than unit tests (< 5 seconds per test)
- Validates API contracts, database interactions, external service calls

MEMORY SAFETY PATTERN (3 Parts):
1. @pytest.mark.xdist_group(name="...") - Groups related tests in same worker
2. teardown_method() with gc.collect() - Forces GC after each test
3. Conditional skips for missing dependencies

REFERENCES:
- tests/MEMORY_SAFETY_GUIDELINES.md
- tests/PYTEST_XDIST_BEST_PRACTICES.md
- tests/conftest.py (infrastructure fixtures)
- ADR-0052: Pytest-xdist Isolation Strategy
"""

# ruff: noqa: F841  # Template contains intentional placeholder variables

# ============================================================================
# REQUIRED IMPORTS
# ============================================================================
import gc  # Required for memory safety (teardown_method)
import os  # Required for environment checks
from unittest.mock import AsyncMock

import pytest

# ============================================================================
# YOUR IMPORTS
# ============================================================================
# from mcp_server_langgraph.your_module import YourClass
# from tests.helpers.database_helpers import create_test_record
# from tests.constants import TEST_TIMEOUT_SECONDS


# ============================================================================
# MODULE-LEVEL PYTEST MARKERS
# ============================================================================
# Apply markers to all tests in this module
pytestmark = [
    pytest.mark.integration,  # Marks all tests as integration tests
    pytest.mark.asyncio,  # All integration tests are async
    # pytest.mark.database,  # Add if tests use PostgreSQL
    # pytest.mark.redis,  # Add if tests use Redis
    # pytest.mark.keycloak,  # Add if tests use Keycloak
]


# ============================================================================
# CONDITIONAL SKIP FOR MISSING INFRASTRUCTURE
# ============================================================================
# Skip all tests if required infrastructure is not available
# pytestmark.append(
#     pytest.mark.skipif(
#         os.getenv("SKIP_INTEGRATION_TESTS") == "1",
#         reason="Integration tests skipped (SKIP_INTEGRATION_TESTS=1)"
#     )
# )


# ============================================================================
# TEST CLASS - INTEGRATION PATTERN
# ============================================================================
@pytest.mark.xdist_group(name="example_integration")  # REQUIRED: Group tests
class TestExampleIntegration:
    """Integration tests for [FEATURE_NAME].

    Infrastructure Requirements:
    - PostgreSQL (worker-scoped schema for isolation)
    - Redis (worker-scoped DB index for isolation)
    - Keycloak (optional, use mock if not available)
    - OpenFGA (optional, use mock if not available)

    Memory Safety Pattern Applied:
    - xdist_group: Groups tests in same worker
    - teardown_method: Forces GC after each test
    - Worker isolation: Each worker uses separate DB schema/index

    References:
    - Implementation: src/mcp_server_langgraph/[module]/[file].py
    - Infrastructure: tests/conftest.py (fixtures)
    - ADR-0052: Pytest-xdist Isolation Strategy
    """

    def teardown_method(self):
        """Force garbage collection after each test.

        REQUIRED for memory safety, even in integration tests that use
        real dependencies. AsyncMock/MagicMock may still be used for
        partial mocking.
        """
        gc.collect()

    # ========================================================================
    # BASIC INTEGRATION TEST WITH REAL POSTGRES
    # ========================================================================
    async def test_example_database_integration(self, postgres_connection_clean):
        """Test database operations with real PostgreSQL.

        Uses worker-scoped schema for isolation (each pytest-xdist worker
        gets separate schema: test_worker_gw0, test_worker_gw1, etc.)

        GIVEN: Clean PostgreSQL connection
        WHEN: Database operations are performed
        THEN: Data is persisted and retrievable
        """
        # GIVEN: Database connection (from fixture)
        conn = postgres_connection_clean

        # WHEN: Insert test data
        # await conn.execute(
        #     "INSERT INTO your_table (id, name) VALUES ($1, $2)",
        #     "test-id",
        #     "test-name",
        # )

        # THEN: Data is retrievable
        # result = await conn.fetchrow("SELECT * FROM your_table WHERE id = $1", "test-id")
        # assert result["name"] == "test-name"
        pass  # TODO: Replace with actual test implementation

    # ========================================================================
    # INTEGRATION TEST WITH REAL REDIS
    # ========================================================================
    async def test_example_redis_integration(self, redis_client_clean):
        """Test Redis caching with real Redis.

        Uses worker-scoped DB index for isolation (each pytest-xdist worker
        gets separate DB: gw0→DB1, gw1→DB2, etc.)

        GIVEN: Clean Redis connection
        WHEN: Cache operations are performed
        THEN: Data is cached and retrievable
        """
        # GIVEN: Redis connection (from fixture)
        redis = redis_client_clean

        # WHEN: Set cache value
        # await redis.setex("test:key", 3600, "test-value")

        # THEN: Value is retrievable
        # result = await redis.get("test:key")
        # assert result.decode() == "test-value"
        pass  # TODO: Replace with actual test implementation

    # ========================================================================
    # INTEGRATION TEST WITH POSTGRES + REDIS
    # ========================================================================
    async def test_example_database_and_cache(self, postgres_connection_clean, redis_client_clean):
        """Test with both PostgreSQL and Redis.

        Demonstrates using multiple infrastructure fixtures together.

        GIVEN: Clean database and cache connections
        WHEN: Data is stored in DB and cached
        THEN: Cache hit returns cached data, miss queries DB
        """
        # GIVEN: Infrastructure connections
        conn = postgres_connection_clean
        redis = redis_client_clean

        # WHEN: Store in DB and cache
        # user_id = "user-123"
        # user_data = {"id": user_id, "name": "Test User"}
        #
        # await conn.execute(
        #     "INSERT INTO users (id, name) VALUES ($1, $2)",
        #     user_data["id"],
        #     user_data["name"],
        # )
        # await redis.setex(f"user:{user_id}", 3600, json.dumps(user_data))

        # THEN: Cache hit returns data
        # cached = await redis.get(f"user:{user_id}")
        # assert json.loads(cached)["name"] == "Test User"
        pass  # TODO: Replace with actual test implementation

    # ========================================================================
    # INTEGRATION TEST WITH MOCK EXTERNAL SERVICE
    # ========================================================================
    async def test_example_with_mocked_external(self, postgres_connection_clean, redis_client_clean):
        """Test with real infrastructure but mocked external service.

        Common pattern: Use real DB/cache but mock external APIs (LLM, auth, etc.)

        GIVEN: Real infrastructure + mocked external service
        WHEN: Operation involving external service
        THEN: Local changes persisted, external service called correctly
        """
        # GIVEN: Real infrastructure
        conn = postgres_connection_clean
        redis = redis_client_clean

        # GIVEN: Mocked external service
        mock_llm = AsyncMock()
        mock_llm.generate.return_value = {  # EXPLICIT!
            "text": "Generated response",
            "tokens": 150,
        }

        # WHEN: Call service that uses both
        # result = await your_service(
        #     db=conn,
        #     cache=redis,
        #     llm=mock_llm,
        # )

        # THEN: Assert both real and mocked interactions
        # mock_llm.generate.assert_called_once()
        # db_record = await conn.fetchrow("SELECT * FROM your_table WHERE id = $1", result.id)
        # assert db_record is not None
        pass  # TODO: Replace with actual test implementation

    # ========================================================================
    # INTEGRATION TEST WITH KEYCLOAK (CONDITIONAL)
    # ========================================================================
    @pytest.mark.keycloak
    @pytest.mark.skipif(
        os.getenv("KEYCLOAK_URL") is None,
        reason="Keycloak integration tests require KEYCLOAK_URL",
    )
    async def test_example_keycloak_integration(self, keycloak_client_real):
        """Test Keycloak integration (requires real Keycloak instance).

        Only runs if KEYCLOAK_URL is configured. Otherwise, use mock.

        GIVEN: Real Keycloak client
        WHEN: User management operations
        THEN: User is created/retrieved successfully
        """
        # GIVEN: Keycloak client (from fixture)
        keycloak = keycloak_client_real

        # WHEN: Create test user
        # user_data = {
        #     "username": "testuser",
        #     "email": "testuser@example.com",
        #     "enabled": True,
        # }
        # user_id = await keycloak.create_user(**user_data)

        # THEN: User is retrievable
        # user = await keycloak.get_user_by_id(user_id)
        # assert user.username == "testuser"
        #
        # # CLEANUP: Delete test user
        # await keycloak.delete_user(user_id)
        pass  # TODO: Replace with actual test implementation

    # ========================================================================
    # INTEGRATION TEST WITH OPENFGA (CONDITIONAL)
    # ========================================================================
    @pytest.mark.openfga
    @pytest.mark.skipif(
        os.getenv("OPENFGA_URL") is None,
        reason="OpenFGA integration tests require OPENFGA_URL",
    )
    async def test_example_openfga_integration(self, openfga_client_real):
        """Test OpenFGA integration (requires real OpenFGA instance).

        Only runs if OPENFGA_URL is configured. Otherwise, use mock.

        GIVEN: Real OpenFGA client
        WHEN: Authorization tuples are written/checked
        THEN: Permissions are correctly enforced
        """
        # GIVEN: OpenFGA client (from fixture)
        openfga = openfga_client_real

        # WHEN: Write authorization tuple
        # await openfga.write_tuples([
        #     {
        #         "user": "user:alice",
        #         "relation": "admin",
        #         "object": "org:acme",
        #     }
        # ])

        # THEN: Permission check returns True
        # authorized = await openfga.check_permission(
        #     user="user:alice",
        #     relation="admin",
        #     object="org:acme",
        # )
        # assert authorized is True
        #
        # # CLEANUP: Delete test tuples
        # await openfga.delete_tuples_for_object("org:acme")
        pass  # TODO: Replace with actual test implementation

    # ========================================================================
    # INTEGRATION TEST - TRANSACTION ROLLBACK
    # ========================================================================
    async def test_example_transaction_rollback(self, postgres_connection_clean):
        """Test transaction rollback on error.

        Demonstrates testing error handling in database transactions.

        GIVEN: Database connection
        WHEN: Transaction fails midway
        THEN: Changes are rolled back
        """
        # GIVEN: Database connection
        conn = postgres_connection_clean

        # WHEN: Transaction fails
        # try:
        #     async with conn.transaction():
        #         await conn.execute("INSERT INTO users (id, name) VALUES ($1, $2)", "1", "Alice")
        #         await conn.execute("INSERT INTO users (id, name) VALUES ($1, $2)", "2", "Bob")
        #         raise Exception("Simulated error")  # Force rollback
        # except Exception:
        #     pass

        # THEN: No records inserted (transaction rolled back)
        # count = await conn.fetchval("SELECT COUNT(*) FROM users")
        # assert count == 0
        pass  # TODO: Replace with actual test implementation

    # ========================================================================
    # INTEGRATION TEST - CONCURRENT OPERATIONS
    # ========================================================================
    async def test_example_concurrent_operations(self, postgres_connection_clean, redis_client_clean):
        """Test concurrent operations with real infrastructure.

        Demonstrates testing race conditions and concurrent access patterns.

        GIVEN: Multiple concurrent operations
        WHEN: Operations execute simultaneously
        THEN: Data consistency is maintained
        """

        # GIVEN: Infrastructure connections
        conn = postgres_connection_clean
        redis = redis_client_clean

        # WHEN: Concurrent operations
        # async def increment_counter():
        #     current = await redis.get("counter") or b"0"
        #     await redis.set("counter", str(int(current) + 1))
        #
        # await asyncio.gather(*[increment_counter() for _ in range(10)])

        # THEN: Final count may not be 10 (demonstrates race condition)
        # final_count = int(await redis.get("counter"))
        # # Test should document expected behavior (with/without locking)
        pass  # TODO: Replace with actual test implementation


# ============================================================================
# FASTAPI ENDPOINT INTEGRATION TESTS
# ============================================================================
@pytest.mark.api
@pytest.mark.xdist_group(name="example_api_integration")
class TestExampleAPIIntegration:
    """Integration tests for FastAPI endpoints.

    Tests API endpoints with real infrastructure but mocked dependencies
    where appropriate (e.g., mock LLM but use real DB/cache).

    Memory Safety Pattern Applied:
    - xdist_group: Groups API tests together
    - teardown_method: Forces GC after each test
    - Dependency override cleanup: Prevents state pollution
    """

    def teardown_method(self):
        """Force GC to prevent mock accumulation."""
        gc.collect()

    async def test_example_api_endpoint_integration(self, test_client, postgres_connection_clean):
        """Test API endpoint with real database.

        GIVEN: FastAPI test client with real infrastructure
        WHEN: API request is made
        THEN: Response is correct and data is persisted
        """
        # GIVEN: Test client and database
        client = test_client
        conn = postgres_connection_clean

        # WHEN: Make API request
        # response = client.post(
        #     "/api/v1/your-endpoint",
        #     json={"name": "Test Resource"},
        # )

        # THEN: Response is successful
        # assert response.status_code == 201
        # data = response.json()
        # assert data["name"] == "Test Resource"

        # THEN: Data is persisted in database
        # record = await conn.fetchrow(
        #     "SELECT * FROM your_table WHERE id = $1",
        #     data["id"],
        # )
        # assert record["name"] == "Test Resource"
        pass  # TODO: Replace with actual test implementation

    async def test_example_api_endpoint_with_mocked_auth(self, test_client):
        """Test API endpoint with mocked authentication.

        Demonstrates mocking auth while using real infrastructure for business logic.

        GIVEN: Test client with mocked authentication
        WHEN: Authenticated request is made
        THEN: Request succeeds with correct permissions
        """
        # GIVEN: Mock current user
        # from mcp_server_langgraph.auth.middleware import get_current_user
        #
        # async def mock_current_user():
        #     return {
        #         "user_id": "user:testuser",
        #         "username": "testuser",
        #         "email": "testuser@example.com",
        #     }
        #
        # app.dependency_overrides[get_current_user] = mock_current_user

        # WHEN: Make authenticated request
        # response = client.get("/api/v1/your-protected-endpoint")

        # THEN: Request succeeds
        # assert response.status_code == 200

        # CLEANUP: Clear dependency overrides
        # app.dependency_overrides.clear()
        pass  # TODO: Replace with actual test implementation


# ============================================================================
# CHECKLIST FOR INTEGRATION TESTS
# ============================================================================
"""
BEFORE COMMITTING YOUR INTEGRATION TEST:

Infrastructure Setup:
- [ ] Required infrastructure documented in docstring
- [ ] Conditional skips for missing dependencies
- [ ] Worker-scoped fixtures used (postgres_connection_clean, redis_client_clean)
- [ ] Cleanup performed after tests (delete test data, clear overrides)

Memory Safety (REQUIRED):
- [ ] All test classes have @pytest.mark.xdist_group(name="...")
- [ ] All test classes have teardown_method() with gc.collect()
- [ ] AsyncMock/MagicMock have explicit return_value or side_effect
- [ ] FastAPI dependency overrides cleared in teardown/cleanup

Test Quality:
- [ ] Tests follow GIVEN-WHEN-THEN structure
- [ ] Test names describe integration scenario and expected outcome
- [ ] Appropriate pytest markers applied (integration, database, redis, etc.)
- [ ] Tests are idempotent (can run multiple times safely)
- [ ] Test duration < 5 seconds (if longer, consider @pytest.mark.slow)

Data Isolation:
- [ ] Each test uses clean fixtures (postgres_connection_clean, redis_client_clean)
- [ ] Test data doesn't leak between tests
- [ ] Worker isolation validated (tests pass with pytest -n auto)

Validation:
- [ ] Run: pytest tests/integration/your_test.py -v
- [ ] Run: pytest tests/integration/your_test.py -n auto (parallel)
- [ ] Run: python scripts/validation/check_test_memory_safety.py
- [ ] Verify cleanup: check DB/Redis after test run

REFERENCES:
- Worker Isolation: ADR-0052 (Pytest-xdist Isolation Strategy)
- Fixtures: tests/conftest.py (infrastructure fixtures)
- Memory Safety: tests/MEMORY_SAFETY_GUIDELINES.md
- pytest-xdist: tests/PYTEST_XDIST_BEST_PRACTICES.md
"""
