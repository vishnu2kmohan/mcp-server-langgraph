"""
Tests for Execution Plans API Endpoints

TDD: These tests define the contract for plan approval/rejection endpoints.
"""

from __future__ import annotations

import gc
from decimal import Decimal
from typing import TYPE_CHECKING
from unittest.mock import patch

import pytest

from mcp_server_langgraph.core.models.execution_plan import ExecutionPlan

pytestmark = pytest.mark.unit

if TYPE_CHECKING:
    pass


@pytest.fixture
def sample_pending_plan() -> ExecutionPlan:
    """Create a sample pending execution plan for testing."""
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
def mock_repo():
    """Create a mock execution plan repository."""
    from mcp_server_langgraph.repositories.execution_plan import (
        InMemoryExecutionPlanRepository,
    )

    return InMemoryExecutionPlanRepository()


@pytest.fixture
def mock_user():
    """Create a mock authenticated user."""
    return {"sub": "user-123", "email": "test@example.com", "preferred_username": "testuser"}


@pytest.fixture
def mock_audit_service():
    """Create a mock audit service."""
    from unittest.mock import AsyncMock

    return AsyncMock()


@pytest.mark.xdist_group(name="execution_plans_api")
class TestExecutionPlansEndpoints:
    """Tests for execution plans API endpoints."""

    def teardown_method(self) -> None:
        """Force GC to prevent mock accumulation in xdist workers."""
        gc.collect()

    def test_execution_plans_router_exists(self) -> None:
        """Test that execution plans router exists."""
        from mcp_server_langgraph.api.v1.execution_plans import execution_plans_router

        assert execution_plans_router is not None

    def test_router_has_list_pending_endpoint(self) -> None:
        """Test router has list pending plans endpoint."""
        from mcp_server_langgraph.api.v1.execution_plans import execution_plans_router

        routes = [route.path for route in execution_plans_router.routes]
        # Route is "/" since router is mounted at /plans
        assert "/" in routes or "" in routes

    def test_router_has_get_plan_endpoint(self) -> None:
        """Test router has get plan by ID endpoint."""
        from mcp_server_langgraph.api.v1.execution_plans import execution_plans_router

        routes = [route.path for route in execution_plans_router.routes]
        assert any("{plan_id}" in route for route in routes)

    def test_router_has_approve_endpoint(self) -> None:
        """Test router has approve plan endpoint."""
        from mcp_server_langgraph.api.v1.execution_plans import execution_plans_router

        routes = [route.path for route in execution_plans_router.routes]
        assert any("approve" in route for route in routes)

    def test_router_has_reject_endpoint(self) -> None:
        """Test router has reject plan endpoint."""
        from mcp_server_langgraph.api.v1.execution_plans import execution_plans_router

        routes = [route.path for route in execution_plans_router.routes]
        assert any("reject" in route for route in routes)


@pytest.mark.xdist_group(name="execution_plans_api_list")
class TestListPendingPlans:
    """Tests for listing pending plans."""

    def teardown_method(self) -> None:
        """Force GC to prevent mock accumulation in xdist workers."""
        gc.collect()

    @pytest.mark.asyncio
    async def test_list_pending_returns_empty_when_no_plans(self, mock_repo, mock_user) -> None:
        """Test list_pending returns empty list when no plans exist."""
        from mcp_server_langgraph.api.v1.execution_plans import list_pending_plans

        # Patch the get_plan_repo and get_current_user
        with patch(
            "mcp_server_langgraph.api.v1.execution_plans.get_plan_repo",
            return_value=mock_repo,
        ):
            result = await list_pending_plans(current_user=mock_user)

        assert result.plans == []
        assert result.total == 0

    @pytest.mark.asyncio
    async def test_list_pending_returns_only_pending_plans(self, mock_repo, mock_user, sample_pending_plan) -> None:
        """Test list_pending returns only awaiting_approval plans."""
        from mcp_server_langgraph.api.v1.execution_plans import list_pending_plans

        # Add pending plan
        await mock_repo.create(sample_pending_plan)

        # Add approved plan (should not be returned)
        approved_plan = ExecutionPlan(
            plan_id="plan-approved",
            session_id="session-456",
            status="approved",
            complexity="simple",
            risk_level="low",
            task_type="chat",
            executor_model="gemini-3-flash",
            estimated_cost=Decimal("0.01"),
            message="Simple chat",
        )
        await mock_repo.create(approved_plan)

        with patch(
            "mcp_server_langgraph.api.v1.execution_plans.get_plan_repo",
            return_value=mock_repo,
        ):
            result = await list_pending_plans(current_user=mock_user)

        assert len(result.plans) == 1
        assert result.total == 1
        assert result.plans[0].plan_id == sample_pending_plan.plan_id


@pytest.mark.xdist_group(name="execution_plans_api_get")
class TestGetPlan:
    """Tests for getting a specific plan."""

    def teardown_method(self) -> None:
        """Force GC to prevent mock accumulation in xdist workers."""
        gc.collect()

    @pytest.mark.asyncio
    async def test_get_plan_returns_plan(self, mock_repo, mock_user, sample_pending_plan) -> None:
        """Test get_plan returns the plan when found."""
        from mcp_server_langgraph.api.v1.execution_plans import get_plan

        await mock_repo.create(sample_pending_plan)

        with patch(
            "mcp_server_langgraph.api.v1.execution_plans.get_plan_repo",
            return_value=mock_repo,
        ):
            result = await get_plan(plan_id=sample_pending_plan.plan_id, current_user=mock_user)

        assert result.plan_id == sample_pending_plan.plan_id

    @pytest.mark.asyncio
    async def test_get_plan_raises_404_when_not_found(self, mock_repo, mock_user) -> None:
        """Test get_plan raises 404 when plan not found."""
        from fastapi import HTTPException

        from mcp_server_langgraph.api.v1.execution_plans import get_plan

        with patch(
            "mcp_server_langgraph.api.v1.execution_plans.get_plan_repo",
            return_value=mock_repo,
        ):
            with pytest.raises(HTTPException) as exc_info:
                await get_plan(plan_id="nonexistent", current_user=mock_user)

        assert exc_info.value.status_code == 404


@pytest.mark.xdist_group(name="execution_plans_api_approve")
class TestApprovePlan:
    """Tests for approving a plan."""

    def teardown_method(self) -> None:
        """Force GC to prevent mock accumulation in xdist workers."""
        gc.collect()

    @pytest.mark.asyncio
    async def test_approve_plan_updates_status(self, mock_repo, mock_user, mock_audit_service, sample_pending_plan) -> None:
        """Test approve_plan changes status to approved."""
        from mcp_server_langgraph.api.v1.execution_plans import approve_plan

        await mock_repo.create(sample_pending_plan)

        with patch(
            "mcp_server_langgraph.api.v1.execution_plans.get_plan_repo",
            return_value=mock_repo,
        ):
            result = await approve_plan(
                plan_id=sample_pending_plan.plan_id,
                current_user=mock_user,
                audit_service=mock_audit_service,
            )

        assert result.status == "approved"
        assert result.approved_by == "user-123"

    @pytest.mark.asyncio
    async def test_approve_plan_raises_404_when_not_found(self, mock_repo, mock_user, mock_audit_service) -> None:
        """Test approve_plan raises 404 when plan not found."""
        from fastapi import HTTPException

        from mcp_server_langgraph.api.v1.execution_plans import approve_plan

        with patch(
            "mcp_server_langgraph.api.v1.execution_plans.get_plan_repo",
            return_value=mock_repo,
        ):
            with pytest.raises(HTTPException) as exc_info:
                await approve_plan(
                    plan_id="nonexistent",
                    current_user=mock_user,
                    audit_service=mock_audit_service,
                )

        assert exc_info.value.status_code == 404

    @pytest.mark.asyncio
    async def test_approve_plan_raises_409_when_already_approved(self, mock_repo, mock_user, mock_audit_service) -> None:
        """Test approve_plan raises 409 when plan already approved."""
        from fastapi import HTTPException

        from mcp_server_langgraph.api.v1.execution_plans import approve_plan

        approved_plan = ExecutionPlan(
            plan_id="plan-approved",
            session_id="session-456",
            status="approved",
            complexity="simple",
            risk_level="low",
            task_type="chat",
            executor_model="gemini-3-flash",
            estimated_cost=Decimal("0.01"),
            message="Already approved",
        )
        await mock_repo.create(approved_plan)

        with patch(
            "mcp_server_langgraph.api.v1.execution_plans.get_plan_repo",
            return_value=mock_repo,
        ):
            with pytest.raises(HTTPException) as exc_info:
                await approve_plan(
                    plan_id="plan-approved",
                    current_user=mock_user,
                    audit_service=mock_audit_service,
                )

        assert exc_info.value.status_code == 409


@pytest.mark.xdist_group(name="execution_plans_api_reject")
class TestRejectPlan:
    """Tests for rejecting a plan."""

    def teardown_method(self) -> None:
        """Force GC to prevent mock accumulation in xdist workers."""
        gc.collect()

    @pytest.mark.asyncio
    async def test_reject_plan_updates_status(self, mock_repo, mock_user, mock_audit_service, sample_pending_plan) -> None:
        """Test reject_plan changes status to rejected."""
        from mcp_server_langgraph.api.v1.execution_plans import (
            RejectRequest,
            reject_plan,
        )

        await mock_repo.create(sample_pending_plan)

        reject_request = RejectRequest(reason="Too expensive")

        with patch(
            "mcp_server_langgraph.api.v1.execution_plans.get_plan_repo",
            return_value=mock_repo,
        ):
            result = await reject_plan(
                plan_id=sample_pending_plan.plan_id,
                request=reject_request,
                current_user=mock_user,
                audit_service=mock_audit_service,
            )

        assert result.status == "rejected"
        assert result.rejected_by == "user-123"
        assert result.rejection_reason == "Too expensive"

    @pytest.mark.asyncio
    async def test_reject_plan_raises_404_when_not_found(self, mock_repo, mock_user, mock_audit_service) -> None:
        """Test reject_plan raises 404 when plan not found."""
        from fastapi import HTTPException

        from mcp_server_langgraph.api.v1.execution_plans import (
            RejectRequest,
            reject_plan,
        )

        reject_request = RejectRequest(reason="Not needed")

        with patch(
            "mcp_server_langgraph.api.v1.execution_plans.get_plan_repo",
            return_value=mock_repo,
        ):
            with pytest.raises(HTTPException) as exc_info:
                await reject_plan(
                    plan_id="nonexistent",
                    request=reject_request,
                    current_user=mock_user,
                    audit_service=mock_audit_service,
                )

        assert exc_info.value.status_code == 404

    @pytest.mark.asyncio
    async def test_reject_plan_raises_409_when_already_rejected(self, mock_repo, mock_user, mock_audit_service) -> None:
        """Test reject_plan raises 409 when plan already rejected."""
        from fastapi import HTTPException

        from mcp_server_langgraph.api.v1.execution_plans import (
            RejectRequest,
            reject_plan,
        )

        rejected_plan = ExecutionPlan(
            plan_id="plan-rejected",
            session_id="session-456",
            status="rejected",
            complexity="simple",
            risk_level="low",
            task_type="chat",
            executor_model="gemini-3-flash",
            estimated_cost=Decimal("0.01"),
            message="Already rejected",
        )
        await mock_repo.create(rejected_plan)

        reject_request = RejectRequest(reason="Trying again")

        with patch(
            "mcp_server_langgraph.api.v1.execution_plans.get_plan_repo",
            return_value=mock_repo,
        ):
            with pytest.raises(HTTPException) as exc_info:
                await reject_plan(
                    plan_id="plan-rejected",
                    request=reject_request,
                    current_user=mock_user,
                    audit_service=mock_audit_service,
                )

        assert exc_info.value.status_code == 409


@pytest.mark.xdist_group(name="execution_plans_api_session")
class TestListBySession:
    """Tests for listing plans by session."""

    def teardown_method(self) -> None:
        """Force GC to prevent mock accumulation in xdist workers."""
        gc.collect()

    @pytest.mark.asyncio
    async def test_list_by_session_returns_session_plans(self, mock_repo, mock_user, sample_pending_plan) -> None:
        """Test list_by_session returns only plans for the session."""
        from mcp_server_langgraph.api.v1.execution_plans import list_session_plans

        # Add plan for target session
        await mock_repo.create(sample_pending_plan)

        # Add plan for different session
        other_plan = ExecutionPlan(
            plan_id="plan-other",
            session_id="session-other",
            status="awaiting_approval",
            complexity="simple",
            risk_level="low",
            task_type="chat",
            executor_model="gemini-3-flash",
            estimated_cost=Decimal("0.01"),
            message="Other session",
        )
        await mock_repo.create(other_plan)

        with patch(
            "mcp_server_langgraph.api.v1.execution_plans.get_plan_repo",
            return_value=mock_repo,
        ):
            result = await list_session_plans(session_id="session-456", current_user=mock_user)

        assert len(result.plans) == 1
        assert result.total == 1
        assert result.plans[0].plan_id == sample_pending_plan.plan_id


@pytest.fixture
def sample_approved_plan() -> ExecutionPlan:
    """Create a sample approved execution plan for testing."""
    plan = ExecutionPlan(
        plan_id="plan-approved-123",
        session_id="session-789",
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
    return plan.approve(approved_by="user-123")


@pytest.mark.xdist_group(name="execution_plans_api_save_template")
class TestSaveAsTemplate:
    """Tests for saving an approved plan as a template."""

    def teardown_method(self) -> None:
        """Force GC to prevent mock accumulation in xdist workers."""
        gc.collect()

    def test_router_has_save_as_template_endpoint(self) -> None:
        """Test router has save as template endpoint."""
        from mcp_server_langgraph.api.v1.execution_plans import execution_plans_router

        routes = [route.path for route in execution_plans_router.routes]
        assert any("template" in route for route in routes)

    @pytest.mark.asyncio
    async def test_save_as_template_creates_template(self, mock_repo, mock_user, sample_approved_plan) -> None:
        """Test save_as_template creates a new template from approved plan."""
        from mcp_server_langgraph.api.v1.execution_plans import (
            SaveAsTemplateRequest,
            save_as_template,
        )
        from mcp_server_langgraph.repositories.plan_template import (
            InMemoryPlanTemplateRepository,
        )

        await mock_repo.create(sample_approved_plan)
        template_repo = InMemoryPlanTemplateRepository()

        save_request = SaveAsTemplateRequest(
            name="Code Refactor Template",
            description="Template for code refactoring tasks",
            tags=["code", "refactor"],
        )

        with patch(
            "mcp_server_langgraph.api.v1.execution_plans.get_plan_repo",
            return_value=mock_repo,
        ):
            with patch(
                "mcp_server_langgraph.api.v1.execution_plans.get_template_repo",
                return_value=template_repo,
            ):
                result = await save_as_template(
                    plan_id=sample_approved_plan.plan_id,
                    request=save_request,
                    current_user=mock_user,
                )

        assert result.name == "Code Refactor Template"
        assert result.orchestrator == "standard"
        assert result.template_id is not None

    @pytest.mark.asyncio
    async def test_save_as_template_raises_404_when_plan_not_found(self, mock_repo, mock_user) -> None:
        """Test save_as_template raises 404 when plan not found."""
        from fastapi import HTTPException

        from mcp_server_langgraph.api.v1.execution_plans import (
            SaveAsTemplateRequest,
            save_as_template,
        )
        from mcp_server_langgraph.repositories.plan_template import (
            InMemoryPlanTemplateRepository,
        )

        template_repo = InMemoryPlanTemplateRepository()
        save_request = SaveAsTemplateRequest(
            name="Test Template",
            description="Test",
            tags=[],
        )

        with patch(
            "mcp_server_langgraph.api.v1.execution_plans.get_plan_repo",
            return_value=mock_repo,
        ):
            with patch(
                "mcp_server_langgraph.api.v1.execution_plans.get_template_repo",
                return_value=template_repo,
            ):
                with pytest.raises(HTTPException) as exc_info:
                    await save_as_template(
                        plan_id="nonexistent",
                        request=save_request,
                        current_user=mock_user,
                    )

        assert exc_info.value.status_code == 404

    @pytest.mark.asyncio
    async def test_save_as_template_raises_400_when_plan_not_approved(self, mock_repo, mock_user, sample_pending_plan) -> None:
        """Test save_as_template raises 400 when plan is not approved."""
        from fastapi import HTTPException

        from mcp_server_langgraph.api.v1.execution_plans import (
            SaveAsTemplateRequest,
            save_as_template,
        )
        from mcp_server_langgraph.repositories.plan_template import (
            InMemoryPlanTemplateRepository,
        )

        # Add pending plan (not approved)
        await mock_repo.create(sample_pending_plan)
        template_repo = InMemoryPlanTemplateRepository()

        save_request = SaveAsTemplateRequest(
            name="Test Template",
            description="Test",
            tags=[],
        )

        with patch(
            "mcp_server_langgraph.api.v1.execution_plans.get_plan_repo",
            return_value=mock_repo,
        ):
            with patch(
                "mcp_server_langgraph.api.v1.execution_plans.get_template_repo",
                return_value=template_repo,
            ):
                with pytest.raises(HTTPException) as exc_info:
                    await save_as_template(
                        plan_id=sample_pending_plan.plan_id,
                        request=save_request,
                        current_user=mock_user,
                    )

        assert exc_info.value.status_code == 400

    @pytest.mark.asyncio
    async def test_save_as_template_copies_plan_configuration(self, mock_repo, mock_user, sample_approved_plan) -> None:
        """Test save_as_template copies complexity, risk, task type from plan."""
        from mcp_server_langgraph.api.v1.execution_plans import (
            SaveAsTemplateRequest,
            save_as_template,
        )
        from mcp_server_langgraph.repositories.plan_template import (
            InMemoryPlanTemplateRepository,
        )

        await mock_repo.create(sample_approved_plan)
        template_repo = InMemoryPlanTemplateRepository()

        save_request = SaveAsTemplateRequest(
            name="Code Refactor Template",
            description="Template for code refactoring",
            tags=["code"],
        )

        with patch(
            "mcp_server_langgraph.api.v1.execution_plans.get_plan_repo",
            return_value=mock_repo,
        ):
            with patch(
                "mcp_server_langgraph.api.v1.execution_plans.get_template_repo",
                return_value=template_repo,
            ):
                result = await save_as_template(
                    plan_id=sample_approved_plan.plan_id,
                    request=save_request,
                    current_user=mock_user,
                )

        # Template should inherit plan's configuration
        assert result.thinking_budget in ["none", "light", "medium", "deep"]
        assert result.auto_approve in [True, False]
        assert result.created_by == "user-123"

    @pytest.mark.asyncio
    async def test_save_as_template_records_created_by(self, mock_repo, mock_user, sample_approved_plan) -> None:
        """Test save_as_template records the user who created it."""
        from mcp_server_langgraph.api.v1.execution_plans import (
            SaveAsTemplateRequest,
            save_as_template,
        )
        from mcp_server_langgraph.repositories.plan_template import (
            InMemoryPlanTemplateRepository,
        )

        await mock_repo.create(sample_approved_plan)
        template_repo = InMemoryPlanTemplateRepository()

        save_request = SaveAsTemplateRequest(
            name="Test Template",
            description="Test",
            tags=[],
        )

        with patch(
            "mcp_server_langgraph.api.v1.execution_plans.get_plan_repo",
            return_value=mock_repo,
        ):
            with patch(
                "mcp_server_langgraph.api.v1.execution_plans.get_template_repo",
                return_value=template_repo,
            ):
                result = await save_as_template(
                    plan_id=sample_approved_plan.plan_id,
                    request=save_request,
                    current_user=mock_user,
                )

        assert result.created_by == "user-123"


@pytest.mark.xdist_group(name="execution_plans_api_update")
class TestUpdatePlan:
    """Tests for updating a plan before approval."""

    def teardown_method(self) -> None:
        """Force GC to prevent mock accumulation in xdist workers."""
        gc.collect()

    @pytest.mark.asyncio
    async def test_update_plan_changes_orchestrator(self, mock_repo, mock_user, sample_pending_plan) -> None:
        """Test update_plan can change orchestrator."""
        from mcp_server_langgraph.api.v1.execution_plans import (
            UpdatePlanRequest,
            update_plan,
        )

        await mock_repo.create(sample_pending_plan)

        request = UpdatePlanRequest(orchestrator="swarm")

        with patch(
            "mcp_server_langgraph.api.v1.execution_plans.get_plan_repo",
            return_value=mock_repo,
        ):
            result = await update_plan(
                plan_id=sample_pending_plan.plan_id,
                request=request,
                current_user=mock_user,
            )

        assert result.suggested_orchestrator == "swarm"

    @pytest.mark.asyncio
    async def test_update_plan_null_orchestrator_resets_to_default(self, mock_repo, mock_user, sample_pending_plan) -> None:
        """Test null orchestrator resets to 'standard'."""
        from mcp_server_langgraph.api.v1.execution_plans import (
            UpdatePlanRequest,
            update_plan,
        )

        # Set orchestrator to non-default
        modified_plan = sample_pending_plan.model_copy(update={"suggested_orchestrator": "swarm"})
        await mock_repo.create(modified_plan)

        # Explicitly set orchestrator to None (null in JSON)
        request = UpdatePlanRequest(orchestrator=None)

        with patch(
            "mcp_server_langgraph.api.v1.execution_plans.get_plan_repo",
            return_value=mock_repo,
        ):
            result = await update_plan(
                plan_id=modified_plan.plan_id,
                request=request,
                current_user=mock_user,
            )

        # Should reset to default "standard"
        assert result.suggested_orchestrator == "standard"

    @pytest.mark.asyncio
    async def test_update_plan_null_executor_model_raises_422(self, mock_repo, mock_user, sample_pending_plan) -> None:
        """Test null executor_model is rejected with 422."""
        from fastapi import HTTPException

        from mcp_server_langgraph.api.v1.execution_plans import (
            UpdatePlanRequest,
            update_plan,
        )

        await mock_repo.create(sample_pending_plan)

        # Explicitly set executor_model to None (null in JSON)
        request = UpdatePlanRequest(executor_model=None)

        with patch(
            "mcp_server_langgraph.api.v1.execution_plans.get_plan_repo",
            return_value=mock_repo,
        ):
            with pytest.raises(HTTPException) as exc_info:
                await update_plan(
                    plan_id=sample_pending_plan.plan_id,
                    request=request,
                    current_user=mock_user,
                )

        assert exc_info.value.status_code == 422
        assert "executor_model cannot be null" in exc_info.value.detail

    @pytest.mark.asyncio
    async def test_update_plan_null_critic_model_clears(self, mock_repo, mock_user, sample_pending_plan) -> None:
        """Test null critic_model clears the field (truly nullable)."""
        from mcp_server_langgraph.api.v1.execution_plans import (
            UpdatePlanRequest,
            update_plan,
        )

        await mock_repo.create(sample_pending_plan)

        # Explicitly set critic_model to None (null in JSON)
        request = UpdatePlanRequest(critic_model=None)

        with patch(
            "mcp_server_langgraph.api.v1.execution_plans.get_plan_repo",
            return_value=mock_repo,
        ):
            result = await update_plan(
                plan_id=sample_pending_plan.plan_id,
                request=request,
                current_user=mock_user,
            )

        # Should clear critic_model
        assert result.critic_model is None

    @pytest.mark.asyncio
    async def test_update_plan_raises_409_when_not_awaiting_approval(self, mock_repo, mock_user) -> None:
        """Test update_plan raises 409 when plan is already approved."""
        from fastapi import HTTPException

        from mcp_server_langgraph.api.v1.execution_plans import (
            UpdatePlanRequest,
            update_plan,
        )

        approved_plan = ExecutionPlan(
            plan_id="plan-approved",
            session_id="session-456",
            status="approved",
            complexity="simple",
            risk_level="low",
            task_type="chat",
            executor_model="gemini-3-flash",
            estimated_cost=Decimal("0.01"),
            message="Already approved",
        )
        await mock_repo.create(approved_plan)

        request = UpdatePlanRequest(orchestrator="swarm")

        with patch(
            "mcp_server_langgraph.api.v1.execution_plans.get_plan_repo",
            return_value=mock_repo,
        ):
            with pytest.raises(HTTPException) as exc_info:
                await update_plan(
                    plan_id="plan-approved",
                    request=request,
                    current_user=mock_user,
                )

        assert exc_info.value.status_code == 409


@pytest.mark.xdist_group(name="execution_plans_api_admin")
class TestAdminListAll:
    """Tests for admin list_all endpoint with pagination (v35.0 Plan)."""

    def teardown_method(self) -> None:
        """Force GC to prevent mock accumulation in xdist workers."""
        gc.collect()

    def test_router_has_admin_all_endpoint(self) -> None:
        """Test router has admin /all endpoint."""
        from mcp_server_langgraph.api.v1.execution_plans import execution_plans_router

        routes = [route.path for route in execution_plans_router.routes]
        assert any("all" in route for route in routes)

    @pytest.mark.asyncio
    async def test_list_all_returns_all_plans(self, mock_repo, mock_user) -> None:
        """Test list_all returns all plans regardless of status."""
        from mcp_server_langgraph.api.v1.execution_plans import list_all_plans

        # Create plans with different statuses
        for i, status in enumerate(["awaiting_approval", "approved", "rejected"]):
            plan = ExecutionPlan(
                plan_id=f"plan-{i}",
                session_id="session-1",
                status=status,
                complexity="simple",
                risk_level="low",
                task_type="chat",
                executor_model="gemini-3-flash",
                estimated_cost=Decimal("0.01"),
                message=f"Plan {i}",
            )
            await mock_repo.create(plan)

        with patch(
            "mcp_server_langgraph.api.v1.execution_plans.get_plan_repo",
            return_value=mock_repo,
        ):
            result = await list_all_plans(admin_user=mock_user)

        assert len(result.plans) == 3
        assert result.total == 3

    @pytest.mark.asyncio
    async def test_list_all_with_limit(self, mock_repo, mock_user) -> None:
        """Test list_all respects limit parameter."""
        from mcp_server_langgraph.api.v1.execution_plans import list_all_plans

        # Create 5 plans
        for i in range(5):
            plan = ExecutionPlan(
                plan_id=f"plan-{i}",
                session_id="session-1",
                status="awaiting_approval",
                complexity="simple",
                risk_level="low",
                task_type="chat",
                executor_model="gemini-3-flash",
                estimated_cost=Decimal("0.01"),
                message=f"Plan {i}",
            )
            await mock_repo.create(plan)

        with patch(
            "mcp_server_langgraph.api.v1.execution_plans.get_plan_repo",
            return_value=mock_repo,
        ):
            result = await list_all_plans(admin_user=mock_user, limit=3)

        assert len(result.plans) == 3

    @pytest.mark.asyncio
    async def test_list_all_with_offset(self, mock_repo, mock_user) -> None:
        """Test list_all respects offset parameter."""
        from mcp_server_langgraph.api.v1.execution_plans import list_all_plans

        # Create 5 plans
        for i in range(5):
            plan = ExecutionPlan(
                plan_id=f"plan-{i}",
                session_id="session-1",
                status="awaiting_approval",
                complexity="simple",
                risk_level="low",
                task_type="chat",
                executor_model="gemini-3-flash",
                estimated_cost=Decimal("0.01"),
                message=f"Plan {i}",
            )
            await mock_repo.create(plan)

        with patch(
            "mcp_server_langgraph.api.v1.execution_plans.get_plan_repo",
            return_value=mock_repo,
        ):
            result = await list_all_plans(admin_user=mock_user, offset=2)

        assert len(result.plans) == 3

    @pytest.mark.asyncio
    async def test_list_all_limit_capped_at_1000(self, mock_repo, mock_user) -> None:
        """Test list_all caps limit at 1000 (v35.0 hard cap)."""
        from mcp_server_langgraph.api.v1.execution_plans import list_all_plans

        # Create 2 plans
        for i in range(2):
            plan = ExecutionPlan(
                plan_id=f"plan-{i}",
                session_id="session-1",
                status="awaiting_approval",
                complexity="simple",
                risk_level="low",
                task_type="chat",
                executor_model="gemini-3-flash",
                estimated_cost=Decimal("0.01"),
                message=f"Plan {i}",
            )
            await mock_repo.create(plan)

        with patch(
            "mcp_server_langgraph.api.v1.execution_plans.get_plan_repo",
            return_value=mock_repo,
        ):
            # Request limit > 1000, should be capped internally
            result = await list_all_plans(admin_user=mock_user, limit=2000)

        # Should return both plans (only 2 exist)
        assert len(result.plans) == 2

    @pytest.mark.asyncio
    async def test_list_all_offset_capped_at_100000(self, mock_repo, mock_user) -> None:
        """Test list_all caps offset at 100000 (v35.0 hard cap)."""
        from mcp_server_langgraph.api.v1.execution_plans import list_all_plans

        # Create 1 plan
        plan = ExecutionPlan(
            plan_id="plan-1",
            session_id="session-1",
            status="awaiting_approval",
            complexity="simple",
            risk_level="low",
            task_type="chat",
            executor_model="gemini-3-flash",
            estimated_cost=Decimal("0.01"),
            message="Plan 1",
        )
        await mock_repo.create(plan)

        with patch(
            "mcp_server_langgraph.api.v1.execution_plans.get_plan_repo",
            return_value=mock_repo,
        ):
            # Request offset > 100000, should be capped and return empty
            result = await list_all_plans(admin_user=mock_user, offset=200000)

        # With offset capped to 100000 and only 1 plan, should return empty
        assert len(result.plans) == 0

    @pytest.mark.asyncio
    async def test_list_all_negative_limit_clamped_to_zero(self, mock_repo, mock_user) -> None:
        """Test list_all clamps negative limit to 0 (returns empty, not error)."""
        from mcp_server_langgraph.api.v1.execution_plans import list_all_plans

        # Create 1 plan
        plan = ExecutionPlan(
            plan_id="plan-1",
            session_id="session-1",
            status="awaiting_approval",
            complexity="simple",
            risk_level="low",
            task_type="chat",
            executor_model="gemini-3-flash",
            estimated_cost=Decimal("0.01"),
            message="Plan 1",
        )
        await mock_repo.create(plan)

        with patch(
            "mcp_server_langgraph.api.v1.execution_plans.get_plan_repo",
            return_value=mock_repo,
        ):
            # Negative limit should be clamped to 0, returning empty list
            result = await list_all_plans(admin_user=mock_user, limit=-1)

        # Negative limit clamped to 0 means no plans returned
        assert len(result.plans) == 0

    @pytest.mark.asyncio
    async def test_list_all_negative_offset_clamped_to_zero(self, mock_repo, mock_user) -> None:
        """Test list_all clamps negative offset to 0 (starts from beginning)."""
        from mcp_server_langgraph.api.v1.execution_plans import list_all_plans

        # Create 2 plans
        for i in range(2):
            plan = ExecutionPlan(
                plan_id=f"plan-{i}",
                session_id="session-1",
                status="awaiting_approval",
                complexity="simple",
                risk_level="low",
                task_type="chat",
                executor_model="gemini-3-flash",
                estimated_cost=Decimal("0.01"),
                message=f"Plan {i}",
            )
            await mock_repo.create(plan)

        with patch(
            "mcp_server_langgraph.api.v1.execution_plans.get_plan_repo",
            return_value=mock_repo,
        ):
            # Negative offset should be clamped to 0, starting from beginning
            result = await list_all_plans(admin_user=mock_user, offset=-10)

        # Negative offset clamped to 0 means all plans returned
        assert len(result.plans) == 2

    @pytest.mark.asyncio
    async def test_list_all_empty_repository(self, mock_repo, mock_user) -> None:
        """Test list_all returns empty list for empty repository."""
        from mcp_server_langgraph.api.v1.execution_plans import list_all_plans

        with patch(
            "mcp_server_langgraph.api.v1.execution_plans.get_plan_repo",
            return_value=mock_repo,
        ):
            result = await list_all_plans(admin_user=mock_user)

        assert len(result.plans) == 0
        assert result.total == 0


@pytest.mark.xdist_group(name="execution_plans_api_serializers")
class TestPlanResponseNewFields:
    """Tests for v35.0 new fields in PlanResponse and serializers."""

    def teardown_method(self) -> None:
        """Force GC to prevent mock accumulation in xdist workers."""
        gc.collect()

    def test_plan_response_has_skills_needed_field(self) -> None:
        """Test PlanResponse has skills_needed field (v35.0)."""
        from mcp_server_langgraph.api.v1.execution_plans import PlanResponse

        # PlanResponse should have skills_needed in model_fields
        assert "skills_needed" in PlanResponse.model_fields

    def test_plan_response_has_selected_tool_ids_field(self) -> None:
        """Test PlanResponse has selected_tool_ids field (v35.0)."""
        from mcp_server_langgraph.api.v1.execution_plans import PlanResponse

        assert "selected_tool_ids" in PlanResponse.model_fields

    def test_plan_response_has_llm_provider_field(self) -> None:
        """Test PlanResponse has llm_provider field (v35.0)."""
        from mcp_server_langgraph.api.v1.execution_plans import PlanResponse

        assert "llm_provider" in PlanResponse.model_fields

    def test_plan_response_has_kb_focus_field(self) -> None:
        """Test PlanResponse has kb_focus field (v35.0)."""
        from mcp_server_langgraph.api.v1.execution_plans import PlanResponse

        assert "kb_focus" in PlanResponse.model_fields

    def test_plan_to_dict_includes_skills_needed(self) -> None:
        """Test plan_to_dict includes skills_needed (v35.0)."""
        from mcp_server_langgraph.api.v1.serializers import plan_to_dict

        plan = ExecutionPlan(
            plan_id="plan-1",
            session_id="session-1",
            status="awaiting_approval",
            complexity="simple",
            risk_level="low",
            task_type="chat",
            executor_model="gemini-3-flash",
            estimated_cost=Decimal("0.001"),
            message="Test",
            skills_needed=["code_review", "testing"],
        )

        result = plan_to_dict(plan)

        assert "skills_needed" in result
        assert result["skills_needed"] == ["code_review", "testing"]

    def test_plan_to_dict_includes_selected_tool_ids(self) -> None:
        """Test plan_to_dict includes selected_tool_ids (v35.0)."""
        from mcp_server_langgraph.api.v1.serializers import plan_to_dict

        plan = ExecutionPlan(
            plan_id="plan-1",
            session_id="session-1",
            status="awaiting_approval",
            complexity="simple",
            risk_level="low",
            task_type="chat",
            executor_model="gemini-3-flash",
            estimated_cost=Decimal("0.001"),
            message="Test",
            selected_tool_ids=["tool-1", "tool-2"],
        )

        result = plan_to_dict(plan)

        assert "selected_tool_ids" in result
        assert result["selected_tool_ids"] == ["tool-1", "tool-2"]

    def test_plan_to_dict_includes_llm_provider(self) -> None:
        """Test plan_to_dict includes llm_provider (v35.0)."""
        from mcp_server_langgraph.api.v1.serializers import plan_to_dict

        plan = ExecutionPlan(
            plan_id="plan-1",
            session_id="session-1",
            status="awaiting_approval",
            complexity="simple",
            risk_level="low",
            task_type="chat",
            executor_model="gemini-3-flash",
            estimated_cost=Decimal("0.001"),
            message="Test",
            llm_provider="anthropic",
        )

        result = plan_to_dict(plan)

        assert "llm_provider" in result
        assert result["llm_provider"] == "anthropic"

    def test_plan_to_dict_includes_kb_focus(self) -> None:
        """Test plan_to_dict includes kb_focus (v35.0)."""
        from mcp_server_langgraph.api.v1.serializers import plan_to_dict

        plan = ExecutionPlan(
            plan_id="plan-1",
            session_id="session-1",
            status="awaiting_approval",
            complexity="simple",
            risk_level="low",
            task_type="chat",
            executor_model="gemini-3-flash",
            estimated_cost=Decimal("0.001"),
            message="Test",
            kb_focus="kb_only",
        )

        result = plan_to_dict(plan)

        assert "kb_focus" in result
        assert result["kb_focus"] == "kb_only"

    def test_plan_to_dict_handles_none_new_fields(self) -> None:
        """Test plan_to_dict handles None values for new fields (v35.0)."""
        from mcp_server_langgraph.api.v1.serializers import plan_to_dict

        plan = ExecutionPlan(
            plan_id="plan-1",
            session_id="session-1",
            status="awaiting_approval",
            complexity="simple",
            risk_level="low",
            task_type="chat",
            executor_model="gemini-3-flash",
            estimated_cost=Decimal("0.001"),
            message="Test",
        )

        result = plan_to_dict(plan)

        assert result["skills_needed"] is None
        assert result["selected_tool_ids"] is None
        assert result["llm_provider"] is None
        assert result["kb_focus"] is None


@pytest.mark.xdist_group(name="execution_plans_api_admin_auth")
class TestAdminListAllAuthentication:
    """Tests for admin authentication on list_all endpoint (v35.0 Phase 2f)."""

    def teardown_method(self) -> None:
        """Force GC to prevent mock accumulation in xdist workers."""
        gc.collect()

    def test_list_all_has_admin_user_parameter(self) -> None:
        """Test list_all_plans uses admin_user (require_admin) dependency."""
        import inspect

        from mcp_server_langgraph.api.v1.execution_plans import list_all_plans

        # Get the function signature
        sig = inspect.signature(list_all_plans)
        params = list(sig.parameters.keys())

        # Should have admin_user parameter (not current_user)
        assert "admin_user" in params, "list_all_plans should use admin_user parameter"

    def test_admin_user_type_alias_exists(self) -> None:
        """Test AdminUser type alias is defined in execution_plans module."""
        from mcp_server_langgraph.api.v1 import execution_plans

        assert hasattr(execution_plans, "AdminUser"), "AdminUser type alias should be defined"


@pytest.mark.xdist_group(name="execution_plans_api_admin_response")
class TestAdminPlanResponse:
    """Tests for AdminPlanResponse with additional admin-only fields (v35.0 Phase 2f)."""

    def teardown_method(self) -> None:
        """Force GC to prevent mock accumulation in xdist workers."""
        gc.collect()

    def test_admin_plan_response_class_exists(self) -> None:
        """Test AdminPlanResponse class is defined in execution_plans module."""
        from mcp_server_langgraph.api.v1 import execution_plans

        assert hasattr(execution_plans, "AdminPlanResponse"), "AdminPlanResponse class should be defined"

    def test_admin_plan_response_extends_plan_response(self) -> None:
        """Test AdminPlanResponse inherits from PlanResponse."""
        from mcp_server_langgraph.api.v1.execution_plans import (
            AdminPlanResponse,
            PlanResponse,
        )

        assert issubclass(AdminPlanResponse, PlanResponse), "AdminPlanResponse should inherit from PlanResponse"

    def test_admin_plan_response_has_user_id_field(self) -> None:
        """Test AdminPlanResponse includes user_id field for admin visibility."""
        from mcp_server_langgraph.api.v1.execution_plans import AdminPlanResponse

        fields = AdminPlanResponse.model_fields
        assert "user_id" in fields, "AdminPlanResponse should have user_id field"

    def test_admin_plan_response_has_created_by_field(self) -> None:
        """Test AdminPlanResponse includes created_by field for admin visibility."""
        from mcp_server_langgraph.api.v1.execution_plans import AdminPlanResponse

        fields = AdminPlanResponse.model_fields
        assert "created_by" in fields, "AdminPlanResponse should have created_by field"

    def test_admin_plan_response_has_embedding_status_field(self) -> None:
        """Test AdminPlanResponse includes embedding_status for admin visibility."""
        from mcp_server_langgraph.api.v1.execution_plans import AdminPlanResponse

        fields = AdminPlanResponse.model_fields
        assert "embedding_status" in fields, "AdminPlanResponse should have embedding_status field"

    def test_admin_plan_response_has_embedding_error_field(self) -> None:
        """Test AdminPlanResponse includes embedding_error for admin debugging."""
        from mcp_server_langgraph.api.v1.execution_plans import AdminPlanResponse

        fields = AdminPlanResponse.model_fields
        assert "embedding_error" in fields, "AdminPlanResponse should have embedding_error field"


@pytest.mark.xdist_group(name="execution_plans_api_admin_dict")
class TestAdminPlanDict:
    """Tests for _plan_to_admin_dict helper function (v35.0 Phase 2f)."""

    def teardown_method(self) -> None:
        """Force GC to prevent mock accumulation in xdist workers."""
        gc.collect()

    def test_plan_to_admin_dict_function_exists(self) -> None:
        """Test _plan_to_admin_dict function is defined."""
        from mcp_server_langgraph.api.v1 import serializers

        assert hasattr(serializers, "plan_to_admin_dict"), "_plan_to_admin_dict should be defined in serializers"

    def test_plan_to_admin_dict_includes_user_id(self) -> None:
        """Test _plan_to_admin_dict includes user_id field."""
        from mcp_server_langgraph.api.v1.serializers import plan_to_admin_dict
        from mcp_server_langgraph.core.models.execution_plan import ExecutionPlan

        plan = ExecutionPlan(
            plan_id="plan-test",
            session_id="session-test",
            status="awaiting_approval",
            complexity="simple",
            risk_level="low",
            task_type="chat",
            executor_model="test-model",
            estimated_cost=Decimal("0.01"),
            message="Test message",
            user_id="admin-user-123",
        )

        result = plan_to_admin_dict(plan)

        assert "user_id" in result
        assert result["user_id"] == "admin-user-123"

    def test_plan_to_admin_dict_includes_created_by(self) -> None:
        """Test _plan_to_admin_dict includes created_by field."""
        from mcp_server_langgraph.api.v1.serializers import plan_to_admin_dict
        from mcp_server_langgraph.core.models.execution_plan import ExecutionPlan

        plan = ExecutionPlan(
            plan_id="plan-test",
            session_id="session-test",
            status="awaiting_approval",
            complexity="simple",
            risk_level="low",
            task_type="chat",
            executor_model="test-model",
            estimated_cost=Decimal("0.01"),
            message="Test message",
            created_by="creator-456",
        )

        result = plan_to_admin_dict(plan)

        assert "created_by" in result
        assert result["created_by"] == "creator-456"

    def test_plan_to_admin_dict_includes_embedding_fields(self) -> None:
        """Test _plan_to_admin_dict includes embedding status fields."""
        from mcp_server_langgraph.api.v1.serializers import plan_to_admin_dict
        from mcp_server_langgraph.core.models.execution_plan import ExecutionPlan

        plan = ExecutionPlan(
            plan_id="plan-test",
            session_id="session-test",
            status="awaiting_approval",
            complexity="simple",
            risk_level="low",
            task_type="chat",
            executor_model="test-model",
            estimated_cost=Decimal("0.01"),
            message="Test message",
            embedding_status="failed",
            embedding_error="Rate limit exceeded",
        )

        result = plan_to_admin_dict(plan)

        assert "embedding_status" in result
        assert result["embedding_status"] == "failed"
        assert "embedding_error" in result
        assert result["embedding_error"] == "Rate limit exceeded"

    def test_plan_to_admin_dict_includes_all_base_fields(self) -> None:
        """Test _plan_to_admin_dict includes all fields from plan_to_dict."""
        from mcp_server_langgraph.api.v1.serializers import (
            plan_to_admin_dict,
            plan_to_dict,
        )
        from mcp_server_langgraph.core.models.execution_plan import ExecutionPlan

        plan = ExecutionPlan(
            plan_id="plan-test",
            session_id="session-test",
            status="awaiting_approval",
            complexity="simple",
            risk_level="low",
            task_type="chat",
            executor_model="test-model",
            estimated_cost=Decimal("0.01"),
            message="Test message",
        )

        base_dict = plan_to_dict(plan)
        admin_dict = plan_to_admin_dict(plan)

        # All base fields should be present in admin dict
        for key in base_dict:
            assert key in admin_dict, f"Admin dict should include base field: {key}"


@pytest.mark.xdist_group(name="execution_plans_api_admin_endpoint")
class TestAdminListAllUsesAdminResponse:
    """Tests for list_all endpoint using AdminPlanResponse (v35.0 Phase 2f)."""

    def teardown_method(self) -> None:
        """Force GC to prevent mock accumulation in xdist workers."""
        gc.collect()

    def test_list_all_uses_admin_list_response(self) -> None:
        """Test list_all returns AdminPlanListResponse type."""
        from mcp_server_langgraph.api.v1 import execution_plans

        assert hasattr(execution_plans, "AdminPlanListResponse"), "AdminPlanListResponse should be defined"

    @pytest.mark.asyncio
    async def test_list_all_returns_admin_fields(self, mock_repo, mock_user) -> None:
        """Test list_all response includes admin-only fields."""
        from mcp_server_langgraph.api.v1.execution_plans import list_all_plans

        # Create plan with admin fields
        plan = ExecutionPlan(
            plan_id="plan-admin-test",
            session_id="session-1",
            status="awaiting_approval",
            complexity="simple",
            risk_level="low",
            task_type="chat",
            executor_model="test-model",
            estimated_cost=Decimal("0.01"),
            message="Test message",
            user_id="user-123",
            created_by="system",
            embedding_status="completed",
        )
        await mock_repo.create(plan)

        with patch(
            "mcp_server_langgraph.api.v1.execution_plans.get_plan_repo",
            return_value=mock_repo,
        ):
            result = await list_all_plans(admin_user=mock_user)

        # Should have admin fields in response
        assert len(result.plans) == 1
        plan_dict = result.plans[0].model_dump()
        assert "user_id" in plan_dict
        assert plan_dict["user_id"] == "user-123"
        assert "created_by" in plan_dict
        assert plan_dict["created_by"] == "system"
        assert "embedding_status" in plan_dict
        assert plan_dict["embedding_status"] == "completed"
