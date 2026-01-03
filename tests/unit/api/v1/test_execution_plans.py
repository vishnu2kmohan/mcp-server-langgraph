"""
Tests for Execution Plans API Endpoints

TDD: These tests define the contract for plan approval/rejection endpoints.
"""

from __future__ import annotations

import gc
from decimal import Decimal
from typing import TYPE_CHECKING
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient

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
        assert "/plans" in routes or "/plans/" in routes

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
    async def test_list_pending_returns_empty_when_no_plans(
        self, mock_repo, mock_user
    ) -> None:
        """Test list_pending returns empty list when no plans exist."""
        from mcp_server_langgraph.api.v1.execution_plans import list_pending_plans

        # Patch the get_plan_repo and get_current_user
        with patch(
            "mcp_server_langgraph.api.v1.execution_plans.get_plan_repo",
            return_value=mock_repo,
        ):
            result = await list_pending_plans(current_user=mock_user)

        assert result == []

    @pytest.mark.asyncio
    async def test_list_pending_returns_only_pending_plans(
        self, mock_repo, mock_user, sample_pending_plan
    ) -> None:
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

        assert len(result) == 1
        assert result[0]["plan_id"] == sample_pending_plan.plan_id


@pytest.mark.xdist_group(name="execution_plans_api_get")
class TestGetPlan:
    """Tests for getting a specific plan."""

    def teardown_method(self) -> None:
        """Force GC to prevent mock accumulation in xdist workers."""
        gc.collect()

    @pytest.mark.asyncio
    async def test_get_plan_returns_plan(
        self, mock_repo, mock_user, sample_pending_plan
    ) -> None:
        """Test get_plan returns the plan when found."""
        from mcp_server_langgraph.api.v1.execution_plans import get_plan

        await mock_repo.create(sample_pending_plan)

        with patch(
            "mcp_server_langgraph.api.v1.execution_plans.get_plan_repo",
            return_value=mock_repo,
        ):
            result = await get_plan(
                plan_id=sample_pending_plan.plan_id, current_user=mock_user
            )

        assert result["plan_id"] == sample_pending_plan.plan_id

    @pytest.mark.asyncio
    async def test_get_plan_raises_404_when_not_found(
        self, mock_repo, mock_user
    ) -> None:
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
    async def test_approve_plan_updates_status(
        self, mock_repo, mock_user, sample_pending_plan
    ) -> None:
        """Test approve_plan changes status to approved."""
        from mcp_server_langgraph.api.v1.execution_plans import approve_plan

        await mock_repo.create(sample_pending_plan)

        with patch(
            "mcp_server_langgraph.api.v1.execution_plans.get_plan_repo",
            return_value=mock_repo,
        ):
            result = await approve_plan(
                plan_id=sample_pending_plan.plan_id, current_user=mock_user
            )

        assert result["status"] == "approved"
        assert result["approved_by"] == "user-123"

    @pytest.mark.asyncio
    async def test_approve_plan_raises_404_when_not_found(
        self, mock_repo, mock_user
    ) -> None:
        """Test approve_plan raises 404 when plan not found."""
        from fastapi import HTTPException

        from mcp_server_langgraph.api.v1.execution_plans import approve_plan

        with patch(
            "mcp_server_langgraph.api.v1.execution_plans.get_plan_repo",
            return_value=mock_repo,
        ):
            with pytest.raises(HTTPException) as exc_info:
                await approve_plan(plan_id="nonexistent", current_user=mock_user)

        assert exc_info.value.status_code == 404

    @pytest.mark.asyncio
    async def test_approve_plan_raises_409_when_already_approved(
        self, mock_repo, mock_user
    ) -> None:
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
                await approve_plan(plan_id="plan-approved", current_user=mock_user)

        assert exc_info.value.status_code == 409


@pytest.mark.xdist_group(name="execution_plans_api_reject")
class TestRejectPlan:
    """Tests for rejecting a plan."""

    def teardown_method(self) -> None:
        """Force GC to prevent mock accumulation in xdist workers."""
        gc.collect()

    @pytest.mark.asyncio
    async def test_reject_plan_updates_status(
        self, mock_repo, mock_user, sample_pending_plan
    ) -> None:
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
            )

        assert result["status"] == "rejected"
        assert result["rejected_by"] == "user-123"
        assert result["rejection_reason"] == "Too expensive"

    @pytest.mark.asyncio
    async def test_reject_plan_raises_404_when_not_found(
        self, mock_repo, mock_user
    ) -> None:
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
                )

        assert exc_info.value.status_code == 404

    @pytest.mark.asyncio
    async def test_reject_plan_raises_409_when_already_rejected(
        self, mock_repo, mock_user
    ) -> None:
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
                )

        assert exc_info.value.status_code == 409


@pytest.mark.xdist_group(name="execution_plans_api_session")
class TestListBySession:
    """Tests for listing plans by session."""

    def teardown_method(self) -> None:
        """Force GC to prevent mock accumulation in xdist workers."""
        gc.collect()

    @pytest.mark.asyncio
    async def test_list_by_session_returns_session_plans(
        self, mock_repo, mock_user, sample_pending_plan
    ) -> None:
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
            result = await list_session_plans(
                session_id="session-456", current_user=mock_user
            )

        assert len(result) == 1
        assert result[0]["plan_id"] == sample_pending_plan.plan_id


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
    async def test_save_as_template_creates_template(
        self, mock_repo, mock_user, sample_approved_plan
    ) -> None:
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

        assert result["name"] == "Code Refactor Template"
        assert result["orchestrator"] == "standard"
        assert "template_id" in result

    @pytest.mark.asyncio
    async def test_save_as_template_raises_404_when_plan_not_found(
        self, mock_repo, mock_user
    ) -> None:
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
    async def test_save_as_template_raises_400_when_plan_not_approved(
        self, mock_repo, mock_user, sample_pending_plan
    ) -> None:
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
    async def test_save_as_template_copies_plan_configuration(
        self, mock_repo, mock_user, sample_approved_plan
    ) -> None:
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
        assert result["thinking_budget"] in ["none", "light", "medium", "deep"]
        assert result["auto_approve"] in [True, False]
        assert result["created_by"] == "user-123"

    @pytest.mark.asyncio
    async def test_save_as_template_records_created_by(
        self, mock_repo, mock_user, sample_approved_plan
    ) -> None:
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

        assert result["created_by"] == "user-123"
