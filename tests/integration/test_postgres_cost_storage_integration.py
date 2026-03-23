"""
PostgreSQL Integration Tests for Cost Storage.

TDD integration tests for PostgresCostStorage with real PostgreSQL.
Tests CRUD operations, filtering, aggregation, and organizational cost queries.

Follows memory safety patterns for pytest-xdist.
Uses SQLAlchemy async sessions with test database.

Reference: Plan - Phase 5: PostgreSQL Integration Test Suite
"""

import gc
import os
from datetime import UTC, datetime, timedelta
from decimal import Decimal
from uuid import uuid4

import pytest
from sqlalchemy import text
from sqlalchemy.ext.asyncio import create_async_engine

from mcp_server_langgraph.monitoring.cost_tracker import TokenUsage

pytestmark = [pytest.mark.integration, pytest.mark.cost, pytest.mark.asyncio]


# ============================================================================
# Test Fixtures
# ============================================================================


def _database_available() -> bool:
    """Check if the test database is available."""
    import socket

    host = os.getenv("POSTGRES_HOST", "localhost")
    port = int(os.getenv("POSTGRES_PORT", "9432"))

    try:
        with socket.create_connection((host, port), timeout=2):
            return True
    except (ConnectionRefusedError, TimeoutError, OSError):
        return False


@pytest.fixture(scope="module")
async def test_engine():
    """Create a test database engine."""
    if not _database_available():
        pytest.skip("PostgreSQL not available for integration tests")

    # Use test database URL from environment or default
    # Database name is agent_studio_test (managed by Alembic migrations)
    database_url = os.getenv(
        "TEST_DATABASE_URL",
        "postgresql+asyncpg://postgres:postgres@localhost:9432/agent_studio_test",
    )

    try:
        engine = create_async_engine(
            database_url,
            echo=False,
            pool_size=5,
            max_overflow=10,
            pool_pre_ping=True,
        )

        # Test connection
        async with engine.begin() as conn:
            await conn.execute(text("SELECT 1"))

    except Exception as e:
        pytest.skip(f"PostgreSQL not available: {e}")

    yield engine

    await engine.dispose()


@pytest.fixture(scope="module")
async def setup_database(test_engine):
    """
    Verify token_usage_records table exists (Alembic-managed schema).

    Schema is created by Alembic migrations (docker-compose.test.yml alembic-migrate-test).
    This fixture validates the table exists rather than creating it, avoiding
    schema duplication between tests and Alembic.
    """
    async with test_engine.begin() as conn:
        result = await conn.execute(
            text("""
                SELECT EXISTS (
                    SELECT FROM information_schema.tables
                    WHERE table_name = 'token_usage_records'
                )
            """)
        )
        if not result.scalar():
            pytest.skip("token_usage_records table not found — run Alembic migrations first")

    yield

    # Clean up test data after all tests (keep table for other tests)
    async with test_engine.begin() as conn:
        await conn.execute(text("DELETE FROM token_usage_records WHERE session_id LIKE 'test-%'"))


@pytest.fixture(scope="module")
async def database_url(test_engine) -> str:
    """Get the database URL for creating PostgresCostStorage."""
    # Use render_as_string(hide_password=False) to preserve the actual password.
    # str(engine.url) replaces the password with '***' which causes auth failures.
    url_str = test_engine.url.render_as_string(hide_password=False)
    # Ensure we use asyncpg driver
    if not url_str.startswith("postgresql+asyncpg://"):
        url_str = url_str.replace("postgresql://", "postgresql+asyncpg://")
    return url_str


@pytest.fixture
async def storage(database_url, setup_database):
    """Create a PostgresCostStorage instance for testing."""
    from mcp_server_langgraph.monitoring.cost_storage import PostgresCostStorage

    return PostgresCostStorage(database_url)


@pytest.fixture
def unique_session_id() -> str:
    """Generate a unique session ID for test isolation."""
    return f"test-{uuid4()}"


# ============================================================================
# Helper Functions
# ============================================================================


def create_test_usage(
    session_id: str,
    user_id: str = "user:test",
    model: str = "gpt-4",
    provider: str = "openai",
    prompt_tokens: int = 100,
    completion_tokens: int = 50,
    cost: Decimal = Decimal("0.01"),
    timestamp: datetime | None = None,
    organization_id: str | None = None,
    project_id: str | None = None,
    team_id: str | None = None,
) -> TokenUsage:
    """Create a test TokenUsage record."""
    return TokenUsage(
        timestamp=timestamp or datetime.now(UTC),
        user_id=user_id,
        session_id=session_id,
        model=model,
        provider=provider,
        prompt_tokens=prompt_tokens,
        completion_tokens=completion_tokens,
        total_tokens=prompt_tokens + completion_tokens,
        estimated_cost_usd=cost,
        feature="chat",
        organization_id=organization_id,
        project_id=project_id,
        team_id=team_id,
    )


# ============================================================================
# Test Classes
# ============================================================================


@pytest.mark.xdist_group(name="postgres_cost_storage_integration")
class TestPostgresCostStorageBasicCRUD:
    """Integration tests for basic CRUD operations."""

    def teardown_method(self) -> None:
        """Force GC to prevent mock accumulation in xdist workers."""
        gc.collect()

    async def test_store_and_retrieve_single_record(self, storage, unique_session_id):
        """
        GIVEN: PostgresCostStorage connected to real database
        WHEN: Storing a token usage record
        THEN: Record should be retrievable
        """
        # Arrange
        usage = create_test_usage(unique_session_id, user_id="user:alice")

        # Act
        await storage.store(usage)
        records, _ = await storage.get_records(filters={"session_id": unique_session_id})

        # Assert
        assert len(records) >= 1
        record = next((r for r in records if r.session_id == unique_session_id), None)
        assert record is not None
        assert record.user_id == "user:alice"
        assert record.model == "gpt-4"

    async def test_store_multiple_records(self, storage, unique_session_id):
        """
        GIVEN: PostgresCostStorage with empty table
        WHEN: Storing multiple records
        THEN: All records should be stored
        """
        # Arrange
        session1 = f"{unique_session_id}-1"
        session2 = f"{unique_session_id}-2"

        usage1 = create_test_usage(session1, user_id="user:bob")
        usage2 = create_test_usage(session2, user_id="user:carol")

        # Act
        await storage.store(usage1)
        await storage.store(usage2)

        # Assert
        records1, _ = await storage.get_records(filters={"session_id": session1})
        records2, _ = await storage.get_records(filters={"session_id": session2})

        assert any(r.session_id == session1 for r in records1)
        assert any(r.session_id == session2 for r in records2)


@pytest.mark.xdist_group(name="postgres_cost_storage_integration")
class TestPostgresCostStorageFiltering:
    """Integration tests for filtering operations."""

    def teardown_method(self) -> None:
        """Force GC to prevent mock accumulation in xdist workers."""
        gc.collect()

    async def test_filter_by_user_id(self, storage, unique_session_id):
        """
        GIVEN: Records from different users
        WHEN: Filtering by user_id
        THEN: Only matching records returned
        """
        session1 = f"{unique_session_id}-alice"
        session2 = f"{unique_session_id}-bob"

        await storage.store(create_test_usage(session1, user_id="user:alice-filter-test"))
        await storage.store(create_test_usage(session2, user_id="user:bob-filter-test"))

        records, _ = await storage.get_records(filters={"user_id": "user:alice-filter-test"})

        assert any(r.user_id == "user:alice-filter-test" for r in records)
        assert not any(r.user_id == "user:bob-filter-test" for r in records)

    async def test_filter_by_model(self, storage, unique_session_id):
        """
        GIVEN: Records from different models
        WHEN: Filtering by model
        THEN: Only matching records returned
        """
        session1 = f"{unique_session_id}-gpt4"
        session2 = f"{unique_session_id}-claude"

        await storage.store(create_test_usage(session1, model="gpt-4"))
        await storage.store(create_test_usage(session2, model="claude-3"))

        records, _ = await storage.get_records(filters={"model": "gpt-4"})

        # Check that at least our gpt-4 record is there
        assert any(r.session_id == session1 and r.model == "gpt-4" for r in records)

    async def test_filter_by_date_range(self, storage, unique_session_id):
        """
        GIVEN: Records at different dates
        WHEN: Filtering by start_date and end_date
        THEN: Only records in range returned
        """
        now = datetime.now(UTC)
        old_time = now - timedelta(days=30)
        recent_time = now - timedelta(days=1)

        session_old = f"{unique_session_id}-old"
        session_new = f"{unique_session_id}-new"

        await storage.store(create_test_usage(session_old, timestamp=old_time))
        await storage.store(create_test_usage(session_new, timestamp=recent_time))

        # Filter to last 7 days
        start_date = now - timedelta(days=7)
        records, _ = await storage.get_records(filters={"start_date": start_date})

        # Recent record should be included
        assert any(r.session_id == session_new for r in records)
        # Old record should not be included
        assert not any(r.session_id == session_old for r in records)


@pytest.mark.xdist_group(name="postgres_cost_storage_integration")
class TestPostgresCostStorageOrganizational:
    """Integration tests for organizational cost attribution."""

    def teardown_method(self) -> None:
        """Force GC to prevent mock accumulation in xdist workers."""
        gc.collect()

    async def test_store_with_organization_id(self, storage, unique_session_id):
        """
        GIVEN: Record with organization_id
        WHEN: Storing and retrieving
        THEN: Organization field is preserved
        """
        usage = create_test_usage(
            unique_session_id,
            organization_id="organization:acme-test",
        )

        await storage.store(usage)
        records, _ = await storage.get_records(filters={"session_id": unique_session_id})

        assert len(records) >= 1
        record = next((r for r in records if r.session_id == unique_session_id), None)
        assert record is not None
        assert record.organization_id == "organization:acme-test"

    async def test_filter_by_organization_id(self, storage, unique_session_id):
        """
        GIVEN: Records from different organizations
        WHEN: Filtering by organization_id
        THEN: Only matching records returned
        """
        session1 = f"{unique_session_id}-acme"
        session2 = f"{unique_session_id}-globex"

        await storage.store(create_test_usage(session1, organization_id="organization:acme-org-test"))
        await storage.store(create_test_usage(session2, organization_id="organization:globex-org-test"))

        records, _ = await storage.get_records(filters={"organization_id": "organization:acme-org-test"})

        assert any(r.session_id == session1 for r in records)
        assert not any(r.session_id == session2 for r in records)

    async def test_get_cost_by_organization(self, storage, unique_session_id):
        """
        GIVEN: Multiple records for different organizations
        WHEN: Calling get_cost_by_organization
        THEN: Returns aggregated costs by organization
        """
        session1 = f"{unique_session_id}-agg-1"
        session2 = f"{unique_session_id}-agg-2"
        session3 = f"{unique_session_id}-agg-3"

        # Store records for different orgs
        await storage.store(
            create_test_usage(
                session1,
                organization_id="organization:agg-test-a",
                cost=Decimal("10.00"),
            )
        )
        await storage.store(
            create_test_usage(
                session2,
                organization_id="organization:agg-test-a",
                cost=Decimal("5.00"),
            )
        )
        await storage.store(
            create_test_usage(
                session3,
                organization_id="organization:agg-test-b",
                cost=Decimal("20.00"),
            )
        )

        # Get aggregated costs
        org_costs = await storage.get_cost_by_organization()

        # Find our test organizations
        org_a = next((o for o in org_costs if o.organization_id == "organization:agg-test-a"), None)
        org_b = next((o for o in org_costs if o.organization_id == "organization:agg-test-b"), None)

        assert org_a is not None
        assert org_a.request_count >= 2
        assert org_a.total_cost >= Decimal("15.00")

        assert org_b is not None
        assert org_b.request_count >= 1
        assert org_b.total_cost >= Decimal("20.00")

    async def test_get_cost_by_project(self, storage, unique_session_id):
        """
        GIVEN: Multiple records for different projects
        WHEN: Calling get_cost_by_project
        THEN: Returns aggregated costs by project
        """
        session1 = f"{unique_session_id}-proj-1"
        session2 = f"{unique_session_id}-proj-2"

        await storage.store(
            create_test_usage(
                session1,
                organization_id="organization:proj-test",
                project_id="project:backend-test",
                cost=Decimal("8.00"),
            )
        )
        await storage.store(
            create_test_usage(
                session2,
                organization_id="organization:proj-test",
                project_id="project:frontend-test",
                cost=Decimal("12.00"),
            )
        )

        # Get aggregated costs by project
        proj_costs = await storage.get_cost_by_project(organization_id="organization:proj-test")

        # Find our test projects
        backend = next((p for p in proj_costs if p.project_id == "project:backend-test"), None)
        frontend = next((p for p in proj_costs if p.project_id == "project:frontend-test"), None)

        assert backend is not None
        assert backend.total_cost >= Decimal("8.00")

        assert frontend is not None
        assert frontend.total_cost >= Decimal("12.00")

    async def test_get_cost_by_team(self, storage, unique_session_id):
        """
        GIVEN: Multiple records for different teams
        WHEN: Calling get_cost_by_team
        THEN: Returns aggregated costs by team
        """
        session1 = f"{unique_session_id}-team-1"
        session2 = f"{unique_session_id}-team-2"

        await storage.store(
            create_test_usage(
                session1,
                organization_id="organization:team-test",
                project_id="project:team-proj",
                team_id="team:platform-test",
                cost=Decimal("15.00"),
            )
        )
        await storage.store(
            create_test_usage(
                session2,
                organization_id="organization:team-test",
                project_id="project:team-proj",
                team_id="team:data-test",
                cost=Decimal("25.00"),
            )
        )

        # Get aggregated costs by team
        team_costs = await storage.get_cost_by_team(
            organization_id="organization:team-test",
            project_id="project:team-proj",
        )

        # Find our test teams
        platform = next((t for t in team_costs if t.team_id == "team:platform-test"), None)
        data = next((t for t in team_costs if t.team_id == "team:data-test"), None)

        assert platform is not None
        assert platform.total_cost >= Decimal("15.00")

        assert data is not None
        assert data.total_cost >= Decimal("25.00")


@pytest.mark.xdist_group(name="postgres_cost_storage_integration")
class TestPostgresCostStoragePagination:
    """Integration tests for pagination."""

    def teardown_method(self) -> None:
        """Force GC to prevent mock accumulation in xdist workers."""
        gc.collect()

    async def test_pagination_with_limit(self, storage, unique_session_id):
        """
        GIVEN: Multiple records
        WHEN: Getting records with limit
        THEN: Returns limited number of records with cursor
        """
        # Store 5 records
        for i in range(5):
            await storage.store(
                create_test_usage(
                    f"{unique_session_id}-page-{i}",
                    user_id=f"user:page-test-{unique_session_id}",
                )
            )

        # Get first page of 2
        page1, cursor1 = await storage.get_records(
            filters={"user_id": f"user:page-test-{unique_session_id}"},
            limit=2,
        )

        assert len(page1) == 2
        assert cursor1 is not None

        # Get second page
        page2, cursor2 = await storage.get_records(
            filters={"user_id": f"user:page-test-{unique_session_id}"},
            cursor=cursor1,
            limit=2,
        )

        assert len(page2) == 2
        assert cursor2 is not None

        # Get third page (should have 1 record)
        page3, cursor3 = await storage.get_records(
            filters={"user_id": f"user:page-test-{unique_session_id}"},
            cursor=cursor2,
            limit=2,
        )

        assert len(page3) == 1
        assert cursor3 is None  # No more pages


@pytest.mark.xdist_group(name="postgres_cost_storage_integration")
class TestPostgresCostStorageSorting:
    """Integration tests for sorting."""

    def teardown_method(self) -> None:
        """Force GC to prevent mock accumulation in xdist workers."""
        gc.collect()

    async def test_sort_by_timestamp_desc(self, storage, unique_session_id):
        """
        GIVEN: Records at different timestamps
        WHEN: Sorting by timestamp descending
        THEN: Most recent records first
        """
        now = datetime.now(UTC)

        await storage.store(
            create_test_usage(
                f"{unique_session_id}-old",
                user_id=f"user:sort-test-{unique_session_id}",
                timestamp=now - timedelta(hours=2),
            )
        )
        await storage.store(
            create_test_usage(
                f"{unique_session_id}-new",
                user_id=f"user:sort-test-{unique_session_id}",
                timestamp=now,
            )
        )

        records, _ = await storage.get_records(
            filters={"user_id": f"user:sort-test-{unique_session_id}"},
            sort_by="timestamp",
            sort_order="desc",
        )

        assert len(records) >= 2
        # Verify descending order
        timestamps = [r.timestamp for r in records]
        assert timestamps == sorted(timestamps, reverse=True)

    async def test_sort_by_cost(self, storage, unique_session_id):
        """
        GIVEN: Records with different costs
        WHEN: Sorting by cost descending
        THEN: Highest cost records first
        """
        costs = [Decimal("5.00"), Decimal("15.00"), Decimal("10.00")]

        for i, cost in enumerate(costs):
            await storage.store(
                create_test_usage(
                    f"{unique_session_id}-cost-{i}",
                    user_id=f"user:cost-sort-{unique_session_id}",
                    cost=cost,
                )
            )

        records, _ = await storage.get_records(
            filters={"user_id": f"user:cost-sort-{unique_session_id}"},
            sort_by="estimated_cost_usd",
            sort_order="desc",
        )

        assert len(records) >= 3
        # Verify descending order by cost
        costs_returned = [r.estimated_cost_usd for r in records]
        assert costs_returned == sorted(costs_returned, reverse=True)


@pytest.mark.xdist_group(name="postgres_cost_storage_integration")
class TestPostgresCostStorageAggregation:
    """Integration tests for cost summary and aggregation."""

    def teardown_method(self) -> None:
        """Force GC to prevent mock accumulation in xdist workers."""
        gc.collect()

    async def test_get_cost_summary(self, storage, unique_session_id):
        """
        GIVEN: Multiple cost records
        WHEN: Calling get_cost_summary
        THEN: Returns correct aggregated totals
        """
        user_id = f"user:summary-{unique_session_id}"

        await storage.store(
            create_test_usage(
                f"{unique_session_id}-sum-1",
                user_id=user_id,
                prompt_tokens=100,
                completion_tokens=50,
                cost=Decimal("1.00"),
            )
        )
        await storage.store(
            create_test_usage(
                f"{unique_session_id}-sum-2",
                user_id=user_id,
                prompt_tokens=200,
                completion_tokens=100,
                cost=Decimal("2.00"),
            )
        )

        summary = await storage.get_cost_summary(user_id=user_id)

        assert summary.request_count >= 2
        assert summary.total_cost >= Decimal("3.00")
        assert summary.total_prompt_tokens >= 300
        assert summary.total_completion_tokens >= 150

    async def test_get_cost_by_model(self, storage, unique_session_id):
        """
        GIVEN: Records from different models
        WHEN: Calling get_cost_by_model
        THEN: Returns breakdown by model
        """
        user_id = f"user:model-{unique_session_id}"

        await storage.store(
            create_test_usage(
                f"{unique_session_id}-model-gpt",
                user_id=user_id,
                model="gpt-4-model-test",
                cost=Decimal("5.00"),
            )
        )
        await storage.store(
            create_test_usage(
                f"{unique_session_id}-model-claude",
                user_id=user_id,
                model="claude-3-model-test",
                provider="anthropic",
                cost=Decimal("3.00"),
            )
        )

        model_costs = await storage.get_cost_by_model(user_id=user_id)

        # Find our test models
        gpt = next((m for m in model_costs if m.model == "gpt-4-model-test"), None)
        claude = next((m for m in model_costs if m.model == "claude-3-model-test"), None)

        assert gpt is not None
        assert gpt.total_cost >= Decimal("5.00")

        assert claude is not None
        assert claude.total_cost >= Decimal("3.00")
