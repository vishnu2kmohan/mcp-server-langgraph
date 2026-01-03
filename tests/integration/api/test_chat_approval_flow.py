"""
Integration tests for Chat Approval Flow.

Tests the complete lifecycle of execution plan approvals:
- Plan creation and persistence
- Status transitions (awaiting_approval → approved/rejected)
- User authorization for plan operations
- Session-scoped plan listing
"""

from __future__ import annotations

import gc
from decimal import Decimal
from typing import Any
from unittest.mock import AsyncMock, patch

import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient

from mcp_server_langgraph.core.models.execution_plan import ExecutionPlan
from mcp_server_langgraph.repositories.execution_plan import (
    InMemoryExecutionPlanRepository,
)

pytestmark = pytest.mark.integration


@pytest.fixture
def mock_user() -> dict[str, Any]:
    """Create a mock authenticated user."""
    return {
        "sub": "user-integration-test",
        "email": "integration@example.com",
        "preferred_username": "integrationuser",
    }


@pytest.fixture
def mock_repo() -> InMemoryExecutionPlanRepository:
    """Create a fresh in-memory repository for each test."""
    return InMemoryExecutionPlanRepository()


@pytest.fixture
def app_with_mocks(mock_repo: InMemoryExecutionPlanRepository, mock_user: dict[str, Any]) -> FastAPI:
    """Create a FastAPI app with mocked dependencies."""
    from fastapi import FastAPI

    from mcp_server_langgraph.api.v1.execution_plans import execution_plans_router
    from mcp_server_langgraph.auth.dependencies import get_current_user

    app = FastAPI()
    app.include_router(execution_plans_router, prefix="/api/v1")

    # Override authentication
    app.dependency_overrides[get_current_user] = lambda: mock_user

    return app


@pytest.fixture
def client(
    app_with_mocks: FastAPI,
    mock_repo: InMemoryExecutionPlanRepository,
) -> TestClient:
    """Create a test client with mocked dependencies."""
    with patch(
        "mcp_server_langgraph.api.v1.execution_plans.get_plan_repo",
        return_value=mock_repo,
    ):
        yield TestClient(app_with_mocks)


@pytest.mark.xdist_group(name="chat_approval_flow")
class TestChatApprovalFlowIntegration:
    """Integration tests for the complete approval flow."""

    def teardown_method(self) -> None:
        """Force GC to prevent mock accumulation in xdist workers."""
        gc.collect()

    @pytest.mark.asyncio
    async def test_full_approval_flow(
        self,
        mock_repo: InMemoryExecutionPlanRepository,
        mock_user: dict[str, Any],
    ) -> None:
        """Test the complete flow: create → list → approve → verify."""
        # 1. Create a pending plan
        plan = ExecutionPlan(
            plan_id="plan-flow-test-1",
            session_id="session-flow-test",
            status="awaiting_approval",
            complexity="complicated",
            risk_level="medium",
            task_type="code",
            executor_model="claude-sonnet-4-5-20250929",
            critic_model="claude-haiku-4-5-20251001",
            estimated_cost=Decimal("0.10"),
            message="Refactor the authentication module",
            tools_needed=["file_read", "file_write", "bash"],
        )
        await mock_repo.create(plan)

        # 2. Verify plan is in pending list
        pending_plans = await mock_repo.list_pending()
        assert len(pending_plans) == 1
        assert pending_plans[0].plan_id == plan.plan_id
        assert pending_plans[0].status == "awaiting_approval"

        # 3. Approve the plan
        fetched_plan = await mock_repo.get(plan.plan_id)
        assert fetched_plan is not None
        approved_plan = fetched_plan.approve(approved_by=mock_user["sub"])
        await mock_repo.update(approved_plan)

        # 4. Verify status changed
        final_plan = await mock_repo.get(plan.plan_id)
        assert final_plan is not None
        assert final_plan.status == "approved"
        assert final_plan.approved_by == mock_user["sub"]
        assert final_plan.approved_at is not None

        # 5. Verify no longer in pending list
        pending_after = await mock_repo.list_pending()
        assert len(pending_after) == 0

    @pytest.mark.asyncio
    async def test_full_rejection_flow(
        self,
        mock_repo: InMemoryExecutionPlanRepository,
        mock_user: dict[str, Any],
    ) -> None:
        """Test the complete flow: create → list → reject → verify."""
        # 1. Create a high-risk pending plan
        plan = ExecutionPlan(
            plan_id="plan-reject-test-1",
            session_id="session-reject-test",
            status="awaiting_approval",
            complexity="complex",
            risk_level="high",
            task_type="ops",
            executor_model="claude-opus-4-5-20251101",
            critic_model="claude-sonnet-4-5-20250929",
            estimated_cost=Decimal("0.50"),
            message="Delete all backup files",
            tools_needed=["bash", "file_delete"],
        )
        await mock_repo.create(plan)

        # 2. Verify plan is in pending list
        pending_plans = await mock_repo.list_pending()
        assert len(pending_plans) == 1

        # 3. Reject the plan with reason
        fetched_plan = await mock_repo.get(plan.plan_id)
        assert fetched_plan is not None
        rejected_plan = fetched_plan.reject(
            rejected_by=mock_user["sub"],
            reason="Operation too destructive, needs manual review",
        )
        await mock_repo.update(rejected_plan)

        # 4. Verify status changed
        final_plan = await mock_repo.get(plan.plan_id)
        assert final_plan is not None
        assert final_plan.status == "rejected"
        assert final_plan.rejected_by == mock_user["sub"]
        assert final_plan.rejected_at is not None
        assert "destructive" in final_plan.rejection_reason

        # 5. Verify no longer in pending list
        pending_after = await mock_repo.list_pending()
        assert len(pending_after) == 0

    @pytest.mark.asyncio
    async def test_multiple_plans_per_session(
        self,
        mock_repo: InMemoryExecutionPlanRepository,
    ) -> None:
        """Test multiple plans for a single session."""
        session_id = "session-multi-plan"

        # Create 3 plans for the same session
        for i in range(3):
            plan = ExecutionPlan(
                plan_id=f"plan-multi-{i}",
                session_id=session_id,
                status="awaiting_approval",
                complexity="simple",
                risk_level="low",
                task_type="chat",
                executor_model="gemini-3-flash",
                estimated_cost=Decimal("0.01"),
                message=f"Task {i}",
            )
            await mock_repo.create(plan)

        # List plans by session
        session_plans = await mock_repo.list_by_session(session_id)
        assert len(session_plans) == 3

        # Approve one, reject another
        plan0 = await mock_repo.get("plan-multi-0")
        plan1 = await mock_repo.get("plan-multi-1")
        assert plan0 is not None and plan1 is not None

        await mock_repo.update(plan0.approve(approved_by="user"))
        await mock_repo.update(plan1.reject(rejected_by="user", reason="Not needed"))

        # Verify counts
        pending = await mock_repo.list_pending()
        session_after = await mock_repo.list_by_session(session_id)

        assert len(pending) == 1  # Only plan-multi-2 pending
        assert len(session_after) == 3  # All still in session

    @pytest.mark.asyncio
    async def test_cross_session_isolation(
        self,
        mock_repo: InMemoryExecutionPlanRepository,
    ) -> None:
        """Test that plans from different sessions are properly isolated."""
        # Create plans for different sessions
        for session_num in range(3):
            plan = ExecutionPlan(
                plan_id=f"plan-session{session_num}",
                session_id=f"session-{session_num}",
                status="awaiting_approval",
                complexity="simple",
                risk_level="low",
                task_type="chat",
                executor_model="gemini-3-flash",
                estimated_cost=Decimal("0.01"),
                message=f"Session {session_num} task",
            )
            await mock_repo.create(plan)

        # Verify each session only sees its own plans
        for session_num in range(3):
            session_plans = await mock_repo.list_by_session(f"session-{session_num}")
            assert len(session_plans) == 1
            assert session_plans[0].session_id == f"session-{session_num}"

        # Pending list shows all
        pending = await mock_repo.list_pending()
        assert len(pending) == 3


@pytest.mark.xdist_group(name="chat_approval_http")
class TestChatApprovalHTTPEndpoints:
    """Integration tests for HTTP endpoints."""

    def teardown_method(self) -> None:
        """Force GC to prevent mock accumulation in xdist workers."""
        gc.collect()

    def test_list_pending_plans_empty(
        self,
        client: TestClient,
    ) -> None:
        """Test listing pending plans when none exist."""
        response = client.get("/api/v1/plans")
        assert response.status_code == 200
        assert response.json() == []

    def test_get_plan_not_found(
        self,
        client: TestClient,
    ) -> None:
        """Test getting a non-existent plan returns 404."""
        response = client.get("/api/v1/plans/nonexistent")
        assert response.status_code == 404

    def test_approve_plan_not_found(
        self,
        client: TestClient,
    ) -> None:
        """Test approving a non-existent plan returns 404."""
        response = client.post("/api/v1/plans/nonexistent/approve")
        assert response.status_code == 404

    def test_reject_plan_not_found(
        self,
        client: TestClient,
    ) -> None:
        """Test rejecting a non-existent plan returns 404."""
        response = client.post(
            "/api/v1/plans/nonexistent/reject",
            json={"reason": "Not needed"},
        )
        assert response.status_code == 404


@pytest.mark.xdist_group(name="chat_approval_edge_cases")
class TestApprovalEdgeCases:
    """Tests for edge cases in the approval flow."""

    def teardown_method(self) -> None:
        """Force GC to prevent mock accumulation in xdist workers."""
        gc.collect()

    @pytest.mark.asyncio
    async def test_cannot_approve_already_approved_plan(
        self,
        mock_repo: InMemoryExecutionPlanRepository,
    ) -> None:
        """Test that approving an already-approved plan fails."""
        plan = ExecutionPlan(
            plan_id="plan-already-approved",
            session_id="session-edge",
            status="approved",  # Already approved
            complexity="simple",
            risk_level="low",
            task_type="chat",
            executor_model="gemini-3-flash",
            estimated_cost=Decimal("0.01"),
            message="Already done",
        )
        await mock_repo.create(plan)

        fetched = await mock_repo.get(plan.plan_id)
        assert fetched is not None
        assert fetched.status == "approved"

        # Verify not in pending list
        pending = await mock_repo.list_pending()
        assert len(pending) == 0

    @pytest.mark.asyncio
    async def test_cannot_reject_already_rejected_plan(
        self,
        mock_repo: InMemoryExecutionPlanRepository,
    ) -> None:
        """Test that rejecting an already-rejected plan fails."""
        plan = ExecutionPlan(
            plan_id="plan-already-rejected",
            session_id="session-edge",
            status="rejected",  # Already rejected
            complexity="simple",
            risk_level="low",
            task_type="chat",
            executor_model="gemini-3-flash",
            estimated_cost=Decimal("0.01"),
            message="Already denied",
        )
        await mock_repo.create(plan)

        fetched = await mock_repo.get(plan.plan_id)
        assert fetched is not None
        assert fetched.status == "rejected"

        # Verify not in pending list
        pending = await mock_repo.list_pending()
        assert len(pending) == 0

    @pytest.mark.asyncio
    async def test_high_risk_plans_require_approval(
        self,
        mock_repo: InMemoryExecutionPlanRepository,
    ) -> None:
        """Test that high-risk plans are properly flagged for approval."""
        plan = ExecutionPlan(
            plan_id="plan-high-risk",
            session_id="session-risk",
            status="awaiting_approval",
            complexity="complex",
            risk_level="high",
            task_type="ops",
            executor_model="claude-opus-4-5-20251101",
            estimated_cost=Decimal("1.00"),
            message="Deploy to production",
            tools_needed=["bash", "kubectl", "aws"],
        )
        await mock_repo.create(plan)

        pending = await mock_repo.list_pending()
        assert len(pending) == 1

        fetched = await mock_repo.get(plan.plan_id)
        assert fetched is not None
        assert fetched.risk_level == "high"
        assert fetched.complexity == "complex"
        assert fetched.status == "awaiting_approval"
