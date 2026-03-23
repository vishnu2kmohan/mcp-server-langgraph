"""
Integration Tests for PostgresExecutionPlanRepository.

Tests the PostgreSQL implementation of the execution plan repository
with real database connections.

TDD Approach:
- RED: Tests fail without PostgresExecutionPlanRepository implementation
- GREEN: Tests pass after implementing repository
- REFACTOR: Optimize queries and indexing

Phase 4: PostgreSQL Repositories (SQLAlchemy AsyncSession)
"""

import asyncio
import gc
import socket
import uuid
from datetime import datetime, timedelta, UTC
from typing import AsyncGenerator

import pytest
from sqlalchemy.ext.asyncio import AsyncEngine, AsyncSession, async_sessionmaker, create_async_engine

from mcp_server_langgraph.core.models.execution_plan import ExecutionPlan
from tests.constants import (
    TEST_POSTGRES_DB,
    TEST_POSTGRES_HOST,
    TEST_POSTGRES_PASSWORD,
    TEST_POSTGRES_PORT,
    TEST_POSTGRES_USER,
)

pytestmark = [pytest.mark.integration, pytest.mark.repository]


def create_test_plan(
    session_id: str | None = None,
    user_id: str | None = None,
    status: str = "awaiting_approval",
) -> ExecutionPlan:
    """Create a test execution plan with minimal required fields."""
    return ExecutionPlan(
        plan_id=f"plan_{uuid.uuid4().hex[:8]}",
        session_id=session_id or "_test_parent_session",
        message="Test plan message",
        complexity="simple",
        risk_level="low",
        task_type="chat",
        estimated_cost=0.01,
        executor_model="claude-sonnet-4-20250514",
        suggested_orchestrator="standard",
        status=status,
        user_id=user_id or f"user:{uuid.uuid4().hex[:8]}",
        created_by=user_id or f"user:{uuid.uuid4().hex[:8]}",
        created_at=datetime.now(UTC),
        expires_at=datetime.now(UTC) + timedelta(hours=1),
    )


@pytest.mark.integration
@pytest.mark.asyncio
@pytest.mark.xdist_group(name="testpostgresexecutionplanrepo")
@pytest.mark.skip_isolation_check  # Uses worker-scoped Postgres schemas for isolation
class TestPostgresExecutionPlanRepository:
    """
    Test PostgresExecutionPlanRepository with real PostgreSQL.

    TDD: RED phase - These tests will fail without the repository implementation.
    """

    def teardown_method(self) -> None:
        """Force GC to prevent mock accumulation in xdist workers"""
        gc.collect()

    @pytest.fixture
    async def async_engine(self) -> AsyncGenerator[AsyncEngine, None]:
        """Create SQLAlchemy async engine for agent_studio_test database."""
        try:
            with socket.create_connection((TEST_POSTGRES_HOST, TEST_POSTGRES_PORT), timeout=2):
                pass
        except (ConnectionRefusedError, TimeoutError, OSError):
            pytest.skip(f"PostgreSQL not available at {TEST_POSTGRES_HOST}:{TEST_POSTGRES_PORT}")

        # Import models to register them with Base.metadata (resolves FK references)
        import mcp_server_langgraph.database.execution_plan_models  # noqa: F401
        import mcp_server_langgraph.storage.session.postgres_models  # noqa: F401

        database_url = (
            f"postgresql+asyncpg://{TEST_POSTGRES_USER}:{TEST_POSTGRES_PASSWORD}"
            f"@{TEST_POSTGRES_HOST}:{TEST_POSTGRES_PORT}/{TEST_POSTGRES_DB}"
        )
        engine = create_async_engine(database_url, echo=False, pool_pre_ping=True)
        yield engine
        await engine.dispose()

    @pytest.fixture
    async def repo(self, async_engine: AsyncEngine):
        """Create repository with SQLAlchemy async session factory, cleaning execution_plans first."""
        from sqlalchemy import text

        from mcp_server_langgraph.repositories.postgres_execution_plan import (
            PostgresExecutionPlanRepository,
        )

        # Clean up leftover data from previous test runs
        async with async_engine.begin() as conn:
            await conn.execute(text("DELETE FROM execution_plans"))

        # Ensure a reusable parent session exists (FK constraint)
        async with async_engine.begin() as conn:
            await conn.execute(
                text(
                    "INSERT INTO sessions (id, name, user_id) "
                    "VALUES ('_test_parent_session', 'test', 'test_user') "
                    "ON CONFLICT (id) DO NOTHING"
                )
            )

        session_factory = async_sessionmaker(async_engine, class_=AsyncSession, expire_on_commit=False)
        repo = PostgresExecutionPlanRepository(session_factory)
        repo._test_engine = async_engine  # Expose for session creation helper
        return repo

    @pytest.fixture
    async def ensure_session(self, async_engine: AsyncEngine):
        """Helper to create parent session records for FK constraint."""
        from sqlalchemy import text

        async def _ensure(session_id: str) -> str:
            async with async_engine.begin() as conn:
                await conn.execute(
                    text(
                        "INSERT INTO sessions (id, name, user_id) "
                        f"VALUES ('{session_id}', 'test', 'test_user') "
                        "ON CONFLICT (id) DO NOTHING"
                    )
                )
            return session_id

        return _ensure

    async def test_create_and_get_plan(self, repo):
        """Test creating and retrieving an execution plan."""
        plan = create_test_plan()

        # Create
        created = await repo.create(plan)
        assert created.plan_id == plan.plan_id

        # Get
        retrieved = await repo.get(plan.plan_id)
        assert retrieved is not None
        assert retrieved.plan_id == plan.plan_id
        assert retrieved.message == plan.message
        assert retrieved.status == "awaiting_approval"

    async def test_update_plan_status(self, repo):
        """Test updating plan status (approval workflow)."""
        plan = create_test_plan()
        await repo.create(plan)

        # Approve the plan
        plan.status = "approved"
        plan.approved_by = "test_user"
        plan.approved_at = datetime.now(UTC)
        updated = await repo.update(plan)

        assert updated.status == "approved"
        assert updated.approved_by == "test_user"

        # Verify persistence
        retrieved = await repo.get(plan.plan_id)
        assert retrieved.status == "approved"

    async def test_delete_plan(self, repo):
        """Test deleting an execution plan."""
        plan = create_test_plan()
        await repo.create(plan)

        # Delete
        result = await repo.delete(plan.plan_id)
        assert result is True

        # Verify deletion
        retrieved = await repo.get(plan.plan_id)
        assert retrieved is None

        # Delete non-existent plan
        result = await repo.delete("non_existent_id")
        assert result is False

    async def test_list_by_session(self, repo, ensure_session):
        """Test listing plans by session ID."""
        session_id = f"session_{uuid.uuid4().hex[:8]}"
        await ensure_session(session_id)

        # Create multiple plans for same session
        plans = [create_test_plan(session_id=session_id) for _ in range(3)]
        for plan in plans:
            await repo.create(plan)

        # Create plan for different session
        other_plan = create_test_plan()
        await repo.create(other_plan)

        # List by session
        session_plans = await repo.list_by_session(session_id)
        assert len(session_plans) == 3
        assert all(p.session_id == session_id for p in session_plans)

    async def test_list_pending(self, repo):
        """Test listing plans awaiting approval."""
        # Create plans with different statuses
        pending1 = create_test_plan(status="awaiting_approval")
        pending2 = create_test_plan(status="awaiting_approval")
        approved = create_test_plan(status="approved")
        rejected = create_test_plan(status="rejected")

        for plan in [pending1, pending2, approved, rejected]:
            await repo.create(plan)

        # List pending
        pending_plans = await repo.list_pending()
        assert len(pending_plans) >= 2  # May include other pending plans
        pending_ids = {p.plan_id for p in pending_plans}
        assert pending1.plan_id in pending_ids
        assert pending2.plan_id in pending_ids
        assert approved.plan_id not in pending_ids
        assert rejected.plan_id not in pending_ids

    async def test_list_by_user(self, repo):
        """Test listing plans by user ID (GDPR export)."""
        user_id = f"user:{uuid.uuid4().hex[:8]}"

        # Create plans for user
        plans = [create_test_plan(user_id=user_id) for _ in range(3)]
        for plan in plans:
            await repo.create(plan)

        # Create plan for different user
        other_plan = create_test_plan()
        await repo.create(other_plan)

        # List by user
        user_plans = await repo.list_by_user(user_id)
        assert len(user_plans) == 3
        assert all(p.user_id == user_id for p in user_plans)

    async def test_delete_by_user(self, repo):
        """Test deleting all plans for a user (GDPR deletion)."""
        user_id = f"user:{uuid.uuid4().hex[:8]}"

        # Create plans for user
        plans = [create_test_plan(user_id=user_id) for _ in range(3)]
        for plan in plans:
            await repo.create(plan)

        # Create plan for different user (should not be deleted)
        other_plan = create_test_plan()
        await repo.create(other_plan)

        # Delete by user
        deleted_count = await repo.delete_by_user(user_id)
        assert deleted_count == 3

        # Verify deletion
        user_plans = await repo.list_by_user(user_id)
        assert len(user_plans) == 0

        # Verify other user's plan still exists
        retrieved = await repo.get(other_plan.plan_id)
        assert retrieved is not None

    async def test_embedding_fields_persisted(self, repo):
        """Test that embedding status fields are persisted."""
        plan = create_test_plan()
        plan.embedding_status = "processing"

        await repo.create(plan)

        retrieved = await repo.get(plan.plan_id)
        assert retrieved.embedding_status == "processing"

        # Update embedding status
        plan.embedding_status = "completed"
        await repo.update(plan)

        retrieved = await repo.get(plan.plan_id)
        assert retrieved.embedding_status == "completed"

    async def test_list_all_with_pagination(self, repo):
        """Test list_all with pagination (v35.0 Plan)."""
        # Create plans with slight time differences to ensure ordering
        plans = []
        for i in range(5):
            plan = create_test_plan()
            # Ensure different created_at for ordering
            plan = ExecutionPlan(
                plan_id=plan.plan_id,
                session_id=plan.session_id,
                message=plan.message,
                complexity=plan.complexity,
                risk_level=plan.risk_level,
                task_type=plan.task_type,
                estimated_cost=plan.estimated_cost,
                executor_model=plan.executor_model,
                suggested_orchestrator=plan.suggested_orchestrator,
                status=plan.status,
                user_id=plan.user_id,
                created_by=plan.created_by,
                created_at=datetime.now(UTC) + timedelta(seconds=i),
                expires_at=plan.expires_at,
            )
            plans.append(plan)
            await repo.create(plan)
            await asyncio.sleep(0.01)  # Small delay to ensure ordering

        # Test limit
        limited = await repo.list_all(limit=3)
        assert len(limited) == 3

        # Test offset
        offset_plans = await repo.list_all(offset=2)
        assert len(offset_plans) == 3

        # Test limit + offset
        paginated = await repo.list_all(limit=2, offset=1)
        assert len(paginated) == 2

    async def test_list_all_sorted_desc(self, repo):
        """Test list_all returns plans sorted by created_at DESC (v35.0 Plan)."""
        # Create plans with explicit ordering
        old_plan = create_test_plan()
        old_plan = ExecutionPlan(
            plan_id=old_plan.plan_id,
            session_id=old_plan.session_id,
            message="Old plan",
            complexity=old_plan.complexity,
            risk_level=old_plan.risk_level,
            task_type=old_plan.task_type,
            estimated_cost=old_plan.estimated_cost,
            executor_model=old_plan.executor_model,
            suggested_orchestrator=old_plan.suggested_orchestrator,
            status=old_plan.status,
            user_id=old_plan.user_id,
            created_by=old_plan.created_by,
            created_at=datetime(2024, 1, 1, tzinfo=UTC),
            expires_at=old_plan.expires_at,
        )

        new_plan = create_test_plan()
        new_plan = ExecutionPlan(
            plan_id=new_plan.plan_id,
            session_id=new_plan.session_id,
            message="New plan",
            complexity=new_plan.complexity,
            risk_level=new_plan.risk_level,
            task_type=new_plan.task_type,
            estimated_cost=new_plan.estimated_cost,
            executor_model=new_plan.executor_model,
            suggested_orchestrator=new_plan.suggested_orchestrator,
            status=new_plan.status,
            user_id=new_plan.user_id,
            created_by=new_plan.created_by,
            created_at=datetime(2025, 1, 1, tzinfo=UTC),
            expires_at=new_plan.expires_at,
        )

        await repo.create(old_plan)
        await repo.create(new_plan)

        all_plans = await repo.list_all()

        # Find our test plans in results
        old_idx = next((i for i, p in enumerate(all_plans) if p.plan_id == old_plan.plan_id), -1)
        new_idx = next((i for i, p in enumerate(all_plans) if p.plan_id == new_plan.plan_id), -1)

        # Newer plan should appear before older plan (DESC order)
        assert new_idx < old_idx, "Plans should be sorted by created_at DESC"
