"""
Tests for Execution Plan Repository

TDD: These tests define the contract for storing and retrieving execution plans.
Supports both InMemory (testing) and Postgres (production) implementations.
"""

from __future__ import annotations

import gc
from decimal import Decimal
from typing import TYPE_CHECKING

import pytest

from mcp_server_langgraph.core.models.execution_plan import ExecutionPlan
from datetime import UTC

pytestmark = pytest.mark.unit

if TYPE_CHECKING:
    pass


@pytest.fixture
def sample_plan() -> ExecutionPlan:
    """Create a sample execution plan for testing."""
    return ExecutionPlan(
        plan_id="plan-test-123",
        session_id="session-456",
        status="awaiting_approval",
        complexity="complicated",
        risk_level="medium",
        task_type="code",
        executor_model="claude-sonnet-4-5-20250929",
        critic_model="claude-haiku-4-5-20251001",
        estimated_cost=Decimal("0.05"),
        message="Help me refactor this code",
        tools_needed=["file_read", "file_write"],
    )


@pytest.fixture
def in_memory_repo():
    """Create an in-memory execution plan repository for testing."""
    from mcp_server_langgraph.repositories.execution_plan import (
        InMemoryExecutionPlanRepository,
    )

    return InMemoryExecutionPlanRepository()


@pytest.mark.xdist_group(name="execution_plan_repository")
class TestExecutionPlanRepositoryInterface:
    """Tests for ExecutionPlanRepository abstract interface."""

    def teardown_method(self) -> None:
        """Force GC to prevent mock accumulation in xdist workers."""
        gc.collect()

    def test_repository_base_class_exists(self) -> None:
        """Test that ExecutionPlanRepository base class exists."""
        from mcp_server_langgraph.repositories.execution_plan import (
            ExecutionPlanRepository,
        )

        assert ExecutionPlanRepository is not None

    def test_repository_has_create_method(self) -> None:
        """Test ExecutionPlanRepository has create method."""
        from mcp_server_langgraph.repositories.execution_plan import (
            ExecutionPlanRepository,
        )

        assert hasattr(ExecutionPlanRepository, "create")

    def test_repository_has_get_method(self) -> None:
        """Test ExecutionPlanRepository has get method."""
        from mcp_server_langgraph.repositories.execution_plan import (
            ExecutionPlanRepository,
        )

        assert hasattr(ExecutionPlanRepository, "get")

    def test_repository_has_update_method(self) -> None:
        """Test ExecutionPlanRepository has update method."""
        from mcp_server_langgraph.repositories.execution_plan import (
            ExecutionPlanRepository,
        )

        assert hasattr(ExecutionPlanRepository, "update")

    def test_repository_has_list_by_session_method(self) -> None:
        """Test ExecutionPlanRepository has list_by_session method."""
        from mcp_server_langgraph.repositories.execution_plan import (
            ExecutionPlanRepository,
        )

        assert hasattr(ExecutionPlanRepository, "list_by_session")

    def test_repository_has_list_pending_method(self) -> None:
        """Test ExecutionPlanRepository has list_pending method."""
        from mcp_server_langgraph.repositories.execution_plan import (
            ExecutionPlanRepository,
        )

        assert hasattr(ExecutionPlanRepository, "list_pending")


@pytest.mark.xdist_group(name="execution_plan_repository_inmemory")
class TestInMemoryExecutionPlanRepository:
    """Tests for InMemoryExecutionPlanRepository."""

    def teardown_method(self) -> None:
        """Force GC to prevent mock accumulation in xdist workers."""
        gc.collect()

    @pytest.mark.asyncio
    async def test_create_stores_plan(self, in_memory_repo, sample_plan) -> None:
        """Test that create stores an execution plan."""
        result = await in_memory_repo.create(sample_plan)

        assert result.plan_id == sample_plan.plan_id
        assert result.session_id == sample_plan.session_id

    @pytest.mark.asyncio
    async def test_get_retrieves_plan(self, in_memory_repo, sample_plan) -> None:
        """Test that get retrieves a stored plan."""
        await in_memory_repo.create(sample_plan)

        result = await in_memory_repo.get(sample_plan.plan_id)

        assert result is not None
        assert result.plan_id == sample_plan.plan_id

    @pytest.mark.asyncio
    async def test_get_returns_none_for_missing(self, in_memory_repo) -> None:
        """Test that get returns None for missing plan."""
        result = await in_memory_repo.get("nonexistent-plan")

        assert result is None

    @pytest.mark.asyncio
    async def test_update_modifies_plan(self, in_memory_repo, sample_plan) -> None:
        """Test that update modifies a stored plan."""
        await in_memory_repo.create(sample_plan)

        approved = sample_plan.approve(approved_by="user@example.com")
        result = await in_memory_repo.update(approved)

        assert result.status == "approved"
        assert result.approved_by == "user@example.com"

        # Verify in storage
        stored = await in_memory_repo.get(sample_plan.plan_id)
        assert stored.status == "approved"

    @pytest.mark.asyncio
    async def test_list_by_session(self, in_memory_repo) -> None:
        """Test that list_by_session returns plans for a session."""
        plan1 = ExecutionPlan(
            plan_id="plan-1",
            session_id="session-A",
            status="awaiting_approval",
            complexity="simple",
            risk_level="low",
            task_type="chat",
            executor_model="gemini-3-flash",
            estimated_cost=Decimal("0.001"),
            message="Test 1",
        )
        plan2 = ExecutionPlan(
            plan_id="plan-2",
            session_id="session-A",
            status="executed",
            complexity="simple",
            risk_level="low",
            task_type="chat",
            executor_model="gemini-3-flash",
            estimated_cost=Decimal("0.001"),
            message="Test 2",
        )
        plan3 = ExecutionPlan(
            plan_id="plan-3",
            session_id="session-B",
            status="awaiting_approval",
            complexity="simple",
            risk_level="low",
            task_type="chat",
            executor_model="gemini-3-flash",
            estimated_cost=Decimal("0.001"),
            message="Test 3",
        )

        await in_memory_repo.create(plan1)
        await in_memory_repo.create(plan2)
        await in_memory_repo.create(plan3)

        results = await in_memory_repo.list_by_session("session-A")

        assert len(results) == 2
        assert all(p.session_id == "session-A" for p in results)

    @pytest.mark.asyncio
    async def test_list_pending(self, in_memory_repo) -> None:
        """Test that list_pending returns only awaiting_approval plans."""
        pending = ExecutionPlan(
            plan_id="plan-pending",
            session_id="session-1",
            status="awaiting_approval",
            complexity="complicated",
            risk_level="medium",
            task_type="code",
            executor_model="claude-sonnet-4-5-20250929",
            estimated_cost=Decimal("0.05"),
            message="Pending",
        )
        approved = ExecutionPlan(
            plan_id="plan-approved",
            session_id="session-1",
            status="approved",
            complexity="simple",
            risk_level="low",
            task_type="chat",
            executor_model="gemini-3-flash",
            estimated_cost=Decimal("0.001"),
            message="Approved",
        )
        executed = ExecutionPlan(
            plan_id="plan-executed",
            session_id="session-1",
            status="executed",
            complexity="simple",
            risk_level="low",
            task_type="chat",
            executor_model="gemini-3-flash",
            estimated_cost=Decimal("0.001"),
            message="Executed",
        )

        await in_memory_repo.create(pending)
        await in_memory_repo.create(approved)
        await in_memory_repo.create(executed)

        results = await in_memory_repo.list_pending()

        assert len(results) == 1
        assert results[0].plan_id == "plan-pending"
        assert results[0].status == "awaiting_approval"

    @pytest.mark.asyncio
    async def test_delete_removes_plan(self, in_memory_repo, sample_plan) -> None:
        """Test that delete removes a plan."""
        await in_memory_repo.create(sample_plan)
        assert await in_memory_repo.get(sample_plan.plan_id) is not None

        result = await in_memory_repo.delete(sample_plan.plan_id)

        assert result is True
        assert await in_memory_repo.get(sample_plan.plan_id) is None

    @pytest.mark.asyncio
    async def test_delete_returns_false_for_missing(self, in_memory_repo) -> None:
        """Test that delete returns False for missing plan."""
        result = await in_memory_repo.delete("nonexistent-plan")

        assert result is False


@pytest.mark.xdist_group(name="execution_plan_singleton")
class TestSharedSingleton:
    """Test get_plan_repository() returns shared singleton (v35.0 Plan)."""

    def teardown_method(self) -> None:
        """Force GC and reset singleton."""
        from mcp_server_langgraph.repositories.execution_plan import (
            reset_plan_repository,
        )

        reset_plan_repository()
        gc.collect()

    def test_get_plan_repository_returns_same_instance(self) -> None:
        """Test that get_plan_repository() returns the same instance."""
        from mcp_server_langgraph.repositories.execution_plan import (
            get_plan_repository,
            reset_plan_repository,
        )

        # Reset to ensure clean state
        reset_plan_repository()

        repo1 = get_plan_repository()
        repo2 = get_plan_repository()

        assert repo1 is repo2

    def test_reset_plan_repository_creates_new_instance(self) -> None:
        """Test that reset_plan_repository() creates a fresh instance."""
        from mcp_server_langgraph.repositories.execution_plan import (
            get_plan_repository,
            reset_plan_repository,
        )

        # Get initial instance
        reset_plan_repository()
        repo1 = get_plan_repository()

        # Reset and get new instance
        reset_plan_repository()
        repo2 = get_plan_repository()

        assert repo1 is not repo2

    @pytest.mark.asyncio
    async def test_reset_clears_stored_plans(self) -> None:
        """Test that reset_plan_repository() clears all stored plans."""
        from mcp_server_langgraph.repositories.execution_plan import (
            get_plan_repository,
            reset_plan_repository,
        )

        reset_plan_repository()
        repo = get_plan_repository()

        # Add a plan
        plan = ExecutionPlan(
            plan_id="test-plan-1",
            session_id="test-session",
            status="awaiting_approval",
            complexity="simple",
            risk_level="low",
            task_type="chat",
            executor_model="gemini-3-flash",
            estimated_cost=Decimal("0.001"),
            message="Test",
        )
        await repo.create(plan)

        # Reset and verify plan is gone
        reset_plan_repository()
        repo = get_plan_repository()
        result = await repo.get("test-plan-1")

        assert result is None


@pytest.mark.xdist_group(name="execution_plan_list_all")
class TestListAll:
    """Test list_all() pagination and sorting (v35.0 Plan)."""

    def teardown_method(self) -> None:
        """Force GC and reset singleton."""
        from mcp_server_langgraph.repositories.execution_plan import (
            reset_plan_repository,
        )

        reset_plan_repository()
        gc.collect()

    @pytest.fixture(autouse=True)
    def reset_repo(self) -> None:
        """Reset repository before each test."""
        from mcp_server_langgraph.repositories.execution_plan import (
            reset_plan_repository,
        )

        reset_plan_repository()

    def _make_plan(self, plan_id: str, created_at: datetime | None = None) -> ExecutionPlan:
        """Create a test execution plan with minimal required fields."""
        from datetime import datetime

        return ExecutionPlan(
            plan_id=plan_id,
            session_id="test-session",
            status="awaiting_approval",
            complexity="simple",
            risk_level="low",
            task_type="chat",
            executor_model="gemini-3-flash",
            estimated_cost=Decimal("0.001"),
            message="Test",
            created_at=created_at or datetime.now(UTC),
        )

    @pytest.mark.asyncio
    async def test_list_all_returns_all_plans(self) -> None:
        """Test that list_all() returns all plans."""
        from mcp_server_langgraph.repositories.execution_plan import (
            get_plan_repository,
        )

        repo = get_plan_repository()

        # Create plans
        for i in range(3):
            await repo.create(self._make_plan(f"plan-{i}"))

        plans = await repo.list_all()

        assert len(plans) == 3

    @pytest.mark.asyncio
    async def test_list_all_with_limit(self) -> None:
        """Test that list_all() respects limit parameter."""
        from mcp_server_langgraph.repositories.execution_plan import (
            get_plan_repository,
        )

        repo = get_plan_repository()

        # Create 5 plans
        for i in range(5):
            await repo.create(self._make_plan(f"plan-{i}"))

        plans = await repo.list_all(limit=3)

        assert len(plans) == 3

    @pytest.mark.asyncio
    async def test_list_all_with_offset(self) -> None:
        """Test that list_all() respects offset parameter."""
        from datetime import datetime, timedelta

        from mcp_server_langgraph.repositories.execution_plan import (
            get_plan_repository,
        )

        repo = get_plan_repository()

        # Create 5 plans with specific IDs in order
        base_time = datetime(2025, 1, 1, tzinfo=UTC)
        for i in range(5):
            # Earlier plans have earlier times (will be at end when sorted DESC)
            await repo.create(self._make_plan(f"plan-{i}", base_time + timedelta(seconds=i)))

        # Get with offset=2, should skip first 2 (most recent)
        plans = await repo.list_all(offset=2)

        assert len(plans) == 3

    @pytest.mark.asyncio
    async def test_list_all_sorted_by_created_at_desc(self) -> None:
        """Test that list_all() sorts by created_at DESC (newest first)."""
        from datetime import datetime, timedelta

        from mcp_server_langgraph.repositories.execution_plan import (
            get_plan_repository,
        )

        repo = get_plan_repository()

        # Create plans with specific times
        base_time = datetime(2025, 1, 1, tzinfo=UTC)
        await repo.create(self._make_plan("oldest", base_time))
        await repo.create(self._make_plan("middle", base_time + timedelta(hours=1)))
        await repo.create(self._make_plan("newest", base_time + timedelta(hours=2)))

        plans = await repo.list_all()

        # Newest should be first
        assert plans[0].plan_id == "newest"
        assert plans[1].plan_id == "middle"
        assert plans[2].plan_id == "oldest"

    @pytest.mark.asyncio
    async def test_list_all_limit_capped_at_1000(self) -> None:
        """Test that limit is capped at 1000 (v35.0 hard cap)."""
        from mcp_server_langgraph.repositories.execution_plan import (
            get_plan_repository,
        )

        repo = get_plan_repository()

        # Create 2 plans (testing the cap logic, not creating 1001 plans)
        await repo.create(self._make_plan("plan-1"))
        await repo.create(self._make_plan("plan-2"))

        # Request more than 1000, should be capped
        plans = await repo.list_all(limit=2000)

        # Should return both plans (only 2 exist)
        assert len(plans) == 2
        # The key assertion: if we had 1001+ plans, only 1000 would be returned

    @pytest.mark.asyncio
    async def test_list_all_offset_capped_at_100000(self) -> None:
        """Test that offset is capped at 100000 (v35.0 hard cap)."""
        from mcp_server_langgraph.repositories.execution_plan import (
            get_plan_repository,
        )

        repo = get_plan_repository()

        # Create some plans
        await repo.create(self._make_plan("plan-1"))

        # Request offset > 100000, should be capped and return empty
        plans = await repo.list_all(offset=200000)

        # With offset capped to 100000 and only 1 plan, should return empty
        assert len(plans) == 0

    @pytest.mark.asyncio
    async def test_list_all_with_limit_and_offset(self) -> None:
        """Test that list_all() handles both limit and offset together."""
        from datetime import datetime, timedelta

        from mcp_server_langgraph.repositories.execution_plan import (
            get_plan_repository,
        )

        repo = get_plan_repository()

        # Create 10 plans with specific order
        base_time = datetime(2025, 1, 1, tzinfo=UTC)
        for i in range(10):
            await repo.create(self._make_plan(f"plan-{i}", base_time + timedelta(seconds=i)))

        # Get plans 5-7 (0-indexed: skip 3 newest, take 3)
        # Sorted DESC: plan-9, plan-8, plan-7, plan-6, plan-5, plan-4, ...
        plans = await repo.list_all(limit=3, offset=3)

        assert len(plans) == 3
        assert plans[0].plan_id == "plan-6"
        assert plans[1].plan_id == "plan-5"
        assert plans[2].plan_id == "plan-4"

    @pytest.mark.asyncio
    async def test_list_all_empty_repository(self) -> None:
        """Test that list_all() returns empty list for empty repository."""
        from mcp_server_langgraph.repositories.execution_plan import (
            get_plan_repository,
        )

        repo = get_plan_repository()

        plans = await repo.list_all()

        assert plans == []


@pytest.mark.xdist_group(name="execution_plan_abstract")
class TestAbstractListAllMethod:
    """Test that list_all is an abstract method in the base class."""

    def teardown_method(self) -> None:
        """Force GC."""
        gc.collect()

    def test_list_all_is_abstract_method(self) -> None:
        """Test that ExecutionPlanRepository.list_all is abstract."""
        from mcp_server_langgraph.repositories.execution_plan import (
            ExecutionPlanRepository,
        )

        # Verify list_all is in the abstract methods
        assert "list_all" in ExecutionPlanRepository.__abstractmethods__
