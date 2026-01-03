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
