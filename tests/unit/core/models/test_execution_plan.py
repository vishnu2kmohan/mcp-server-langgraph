"""
Tests for ExecutionPlan Model

TDD: These tests define the contract for execution plans that require
approval before execution.
"""

from __future__ import annotations

import gc
from datetime import datetime, timedelta, timezone
from decimal import Decimal
from typing import TYPE_CHECKING
from uuid import uuid4

import pytest

pytestmark = pytest.mark.unit

if TYPE_CHECKING:
    pass


@pytest.mark.unit
@pytest.mark.agents
@pytest.mark.orchestrator
@pytest.mark.xdist_group(name="execution_plan_model")
class TestExecutionPlanModel:
    """Tests for ExecutionPlan model."""

    def teardown_method(self) -> None:
        """Force GC to prevent mock accumulation in xdist workers."""
        gc.collect()

    def test_execution_plan_exists(self) -> None:
        """Test that ExecutionPlan class exists."""
        from mcp_server_langgraph.core.models.execution_plan import ExecutionPlan

        assert ExecutionPlan is not None

    def test_execution_plan_has_required_fields(self) -> None:
        """Test ExecutionPlan has all required fields."""
        from mcp_server_langgraph.core.models.execution_plan import ExecutionPlan

        plan = ExecutionPlan(
            plan_id="plan-123",
            session_id="session-456",
            status="awaiting_approval",
            complexity="complicated",
            risk_level="medium",
            task_type="code",
            executor_model="claude-opus-4-5-20251101",
            estimated_cost=Decimal("0.05"),
            message="Help me refactor this code",
        )

        assert plan.plan_id == "plan-123"
        assert plan.session_id == "session-456"
        assert plan.status == "awaiting_approval"
        assert plan.complexity == "complicated"
        assert plan.risk_level == "medium"
        assert plan.task_type == "code"
        assert plan.executor_model == "claude-opus-4-5-20251101"
        assert plan.estimated_cost == Decimal("0.05")
        assert plan.message == "Help me refactor this code"

    def test_execution_plan_status_valid_values(self) -> None:
        """Test status field accepts valid values."""
        from mcp_server_langgraph.core.models.execution_plan import ExecutionPlan

        valid_statuses = ["awaiting_approval", "approved", "rejected", "executed", "expired"]

        for status in valid_statuses:
            plan = ExecutionPlan(
                plan_id=f"plan-{status}",
                session_id="session-1",
                status=status,
                complexity="simple",
                risk_level="low",
                task_type="chat",
                executor_model="gemini-3-flash",
                estimated_cost=Decimal("0.001"),
                message="Test",
            )
            assert plan.status == status

    def test_execution_plan_has_critic_model_optional(self) -> None:
        """Test ExecutionPlan has optional critic_model field."""
        from mcp_server_langgraph.core.models.execution_plan import ExecutionPlan

        plan_with_critic = ExecutionPlan(
            plan_id="plan-1",
            session_id="session-1",
            status="awaiting_approval",
            complexity="complex",
            risk_level="high",
            task_type="code",
            executor_model="gemini-3-pro",
            critic_model="claude-haiku-4-5-20251001",
            estimated_cost=Decimal("0.10"),
            message="Test",
        )

        assert plan_with_critic.critic_model == "claude-haiku-4-5-20251001"

        plan_without_critic = ExecutionPlan(
            plan_id="plan-2",
            session_id="session-1",
            status="awaiting_approval",
            complexity="simple",
            risk_level="low",
            task_type="chat",
            executor_model="gemini-3-flash",
            estimated_cost=Decimal("0.001"),
            message="Test",
        )

        assert plan_without_critic.critic_model is None

    def test_execution_plan_has_orchestrator_field(self) -> None:
        """Test ExecutionPlan has suggested_orchestrator field."""
        from mcp_server_langgraph.core.models.execution_plan import ExecutionPlan

        plan = ExecutionPlan(
            plan_id="plan-1",
            session_id="session-1",
            status="awaiting_approval",
            complexity="complex",
            risk_level="high",
            task_type="analysis",
            executor_model="claude-opus-4-5-20251101",
            estimated_cost=Decimal("0.50"),
            suggested_orchestrator="swarm",
            message="Test",
        )

        assert plan.suggested_orchestrator == "swarm"

    def test_execution_plan_orchestrator_defaults_to_standard(self) -> None:
        """Test suggested_orchestrator defaults to 'standard'."""
        from mcp_server_langgraph.core.models.execution_plan import ExecutionPlan

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

        assert plan.suggested_orchestrator == "standard"

    def test_execution_plan_has_critique_rounds(self) -> None:
        """Test ExecutionPlan has critique_rounds field."""
        from mcp_server_langgraph.core.models.execution_plan import ExecutionPlan

        plan = ExecutionPlan(
            plan_id="plan-1",
            session_id="session-1",
            status="awaiting_approval",
            complexity="complex",
            risk_level="high",
            task_type="code",
            executor_model="claude-opus-4-5-20251101",
            estimated_cost=Decimal("0.25"),
            critique_rounds=2,
            message="Test",
        )

        assert plan.critique_rounds == 2

    def test_execution_plan_critique_rounds_defaults_to_0(self) -> None:
        """Test critique_rounds defaults to 0."""
        from mcp_server_langgraph.core.models.execution_plan import ExecutionPlan

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

        assert plan.critique_rounds == 0

    def test_execution_plan_has_thinking_budget(self) -> None:
        """Test ExecutionPlan has thinking_budget field."""
        from mcp_server_langgraph.core.models.execution_plan import ExecutionPlan

        plan = ExecutionPlan(
            plan_id="plan-1",
            session_id="session-1",
            status="awaiting_approval",
            complexity="complex",
            risk_level="high",
            task_type="analysis",
            executor_model="claude-opus-4-5-20251101",
            estimated_cost=Decimal("0.50"),
            thinking_budget="deep",
            message="Test",
        )

        assert plan.thinking_budget == "deep"

    def test_execution_plan_thinking_budget_defaults_to_none(self) -> None:
        """Test thinking_budget defaults to 'none'."""
        from mcp_server_langgraph.core.models.execution_plan import ExecutionPlan

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

        assert plan.thinking_budget == "none"

    def test_execution_plan_has_timestamps(self) -> None:
        """Test ExecutionPlan has created_at and expires_at fields."""
        from mcp_server_langgraph.core.models.execution_plan import ExecutionPlan

        now = datetime.now(timezone.utc)
        expires = now + timedelta(hours=1)

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
            created_at=now,
            expires_at=expires,
        )

        assert plan.created_at == now
        assert plan.expires_at == expires

    def test_execution_plan_auto_generates_timestamps(self) -> None:
        """Test ExecutionPlan auto-generates timestamps if not provided."""
        from mcp_server_langgraph.core.models.execution_plan import ExecutionPlan

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

        assert plan.created_at is not None
        assert plan.expires_at is not None
        assert plan.expires_at > plan.created_at

    def test_execution_plan_has_tools_needed(self) -> None:
        """Test ExecutionPlan has tools_needed field."""
        from mcp_server_langgraph.core.models.execution_plan import ExecutionPlan

        plan = ExecutionPlan(
            plan_id="plan-1",
            session_id="session-1",
            status="awaiting_approval",
            complexity="complicated",
            risk_level="medium",
            task_type="code",
            executor_model="claude-sonnet-4-5-20250929",
            estimated_cost=Decimal("0.10"),
            tools_needed=["file_read", "file_write", "bash"],
            message="Test",
        )

        assert plan.tools_needed == ["file_read", "file_write", "bash"]

    def test_execution_plan_tools_needed_defaults_to_empty(self) -> None:
        """Test tools_needed defaults to empty list."""
        from mcp_server_langgraph.core.models.execution_plan import ExecutionPlan

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

        assert plan.tools_needed == []

    def test_execution_plan_has_confidence(self) -> None:
        """Test ExecutionPlan has confidence field."""
        from mcp_server_langgraph.core.models.execution_plan import ExecutionPlan

        plan = ExecutionPlan(
            plan_id="plan-1",
            session_id="session-1",
            status="awaiting_approval",
            complexity="simple",
            risk_level="low",
            task_type="chat",
            executor_model="gemini-3-flash",
            estimated_cost=Decimal("0.001"),
            confidence=0.95,
            message="Test",
        )

        assert plan.confidence == 0.95

    def test_execution_plan_confidence_defaults_to_0(self) -> None:
        """Test confidence defaults to 0.0."""
        from mcp_server_langgraph.core.models.execution_plan import ExecutionPlan

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

        assert plan.confidence == 0.0


@pytest.mark.unit
@pytest.mark.agents
@pytest.mark.orchestrator
@pytest.mark.xdist_group(name="execution_plan_methods")
class TestExecutionPlanMethods:
    """Tests for ExecutionPlan methods."""

    def teardown_method(self) -> None:
        """Force GC to prevent mock accumulation in xdist workers."""
        gc.collect()

    def test_execution_plan_is_expired(self) -> None:
        """Test is_expired property."""
        from mcp_server_langgraph.core.models.execution_plan import ExecutionPlan

        past = datetime.now(timezone.utc) - timedelta(hours=2)
        future = datetime.now(timezone.utc) + timedelta(hours=1)

        expired_plan = ExecutionPlan(
            plan_id="plan-expired",
            session_id="session-1",
            status="awaiting_approval",
            complexity="simple",
            risk_level="low",
            task_type="chat",
            executor_model="gemini-3-flash",
            estimated_cost=Decimal("0.001"),
            message="Test",
            expires_at=past,
        )

        active_plan = ExecutionPlan(
            plan_id="plan-active",
            session_id="session-1",
            status="awaiting_approval",
            complexity="simple",
            risk_level="low",
            task_type="chat",
            executor_model="gemini-3-flash",
            estimated_cost=Decimal("0.001"),
            message="Test",
            expires_at=future,
        )

        assert expired_plan.is_expired is True
        assert active_plan.is_expired is False

    def test_execution_plan_requires_approval(self) -> None:
        """Test requires_approval property based on risk level."""
        from mcp_server_langgraph.core.models.execution_plan import ExecutionPlan

        low_risk = ExecutionPlan(
            plan_id="plan-low",
            session_id="session-1",
            status="awaiting_approval",
            complexity="simple",
            risk_level="low",
            task_type="chat",
            executor_model="gemini-3-flash",
            estimated_cost=Decimal("0.001"),
            message="Test",
        )

        medium_risk = ExecutionPlan(
            plan_id="plan-medium",
            session_id="session-1",
            status="awaiting_approval",
            complexity="complicated",
            risk_level="medium",
            task_type="code",
            executor_model="claude-sonnet-4-5-20250929",
            estimated_cost=Decimal("0.05"),
            message="Test",
        )

        high_risk = ExecutionPlan(
            plan_id="plan-high",
            session_id="session-1",
            status="awaiting_approval",
            complexity="complex",
            risk_level="high",
            task_type="ops",
            executor_model="claude-opus-4-5-20251101",
            estimated_cost=Decimal("0.50"),
            message="Test",
        )

        # Low risk can auto-approve
        assert low_risk.requires_approval is False
        # Medium and high risk require approval
        assert medium_risk.requires_approval is True
        assert high_risk.requires_approval is True

    def test_execution_plan_approve(self) -> None:
        """Test approve method updates status."""
        from mcp_server_langgraph.core.models.execution_plan import ExecutionPlan

        plan = ExecutionPlan(
            plan_id="plan-1",
            session_id="session-1",
            status="awaiting_approval",
            complexity="complicated",
            risk_level="medium",
            task_type="code",
            executor_model="claude-sonnet-4-5-20250929",
            estimated_cost=Decimal("0.05"),
            message="Test",
        )

        approved = plan.approve(approved_by="user@example.com")

        assert approved.status == "approved"
        assert approved.approved_by == "user@example.com"
        assert approved.approved_at is not None

    def test_execution_plan_reject(self) -> None:
        """Test reject method updates status."""
        from mcp_server_langgraph.core.models.execution_plan import ExecutionPlan

        plan = ExecutionPlan(
            plan_id="plan-1",
            session_id="session-1",
            status="awaiting_approval",
            complexity="complex",
            risk_level="high",
            task_type="ops",
            executor_model="claude-opus-4-5-20251101",
            estimated_cost=Decimal("0.50"),
            message="Test",
        )

        rejected = plan.reject(rejected_by="admin@example.com", reason="Too risky")

        assert rejected.status == "rejected"
        assert rejected.rejected_by == "admin@example.com"
        assert rejected.rejection_reason == "Too risky"
        assert rejected.rejected_at is not None

    def test_execution_plan_mark_executed(self) -> None:
        """Test mark_executed method updates status."""
        from mcp_server_langgraph.core.models.execution_plan import ExecutionPlan

        plan = ExecutionPlan(
            plan_id="plan-1",
            session_id="session-1",
            status="approved",
            complexity="simple",
            risk_level="low",
            task_type="chat",
            executor_model="gemini-3-flash",
            estimated_cost=Decimal("0.001"),
            message="Test",
        )

        executed = plan.mark_executed(actual_cost=Decimal("0.0015"))

        assert executed.status == "executed"
        assert executed.actual_cost == Decimal("0.0015")
        assert executed.executed_at is not None


@pytest.mark.unit
@pytest.mark.agents
@pytest.mark.orchestrator
@pytest.mark.xdist_group(name="execution_plan_factory")
class TestExecutionPlanFactory:
    """Tests for ExecutionPlan factory methods."""

    def teardown_method(self) -> None:
        """Force GC to prevent mock accumulation in xdist workers."""
        gc.collect()

    def test_create_from_router_output(self) -> None:
        """Test creating ExecutionPlan from RouterOutput."""
        from mcp_server_langgraph.agents.router_agent import RouterOutput
        from mcp_server_langgraph.core.models.execution_plan import ExecutionPlan

        router_output = RouterOutput(
            complexity="complicated",
            risk="medium",
            task_type="code",
            tools_needed=["file_read", "file_write"],
            suggested_orchestrator="standard",
            critique_rounds=1,
            thinking_budget="light",
            confidence=0.85,
        )

        plan = ExecutionPlan.from_router_output(
            router_output=router_output,
            session_id="session-123",
            message="Help me refactor",
            executor_model="claude-sonnet-4-5-20250929",
            critic_model="claude-haiku-4-5-20251001",
            estimated_cost=Decimal("0.08"),
        )

        assert plan.session_id == "session-123"
        assert plan.status == "awaiting_approval"
        assert plan.complexity == "complicated"
        assert plan.risk_level == "medium"
        assert plan.task_type == "code"
        assert plan.tools_needed == ["file_read", "file_write"]
        assert plan.suggested_orchestrator == "standard"
        assert plan.critique_rounds == 1
        assert plan.thinking_budget == "light"
        assert plan.confidence == 0.85
        assert plan.executor_model == "claude-sonnet-4-5-20250929"
        assert plan.critic_model == "claude-haiku-4-5-20251001"
        assert plan.message == "Help me refactor"

    def test_create_from_router_output_generates_plan_id(self) -> None:
        """Test that from_router_output generates unique plan_id."""
        from mcp_server_langgraph.agents.router_agent import RouterOutput
        from mcp_server_langgraph.core.models.execution_plan import ExecutionPlan

        router_output = RouterOutput(
            complexity="simple",
            risk="low",
            task_type="chat",
            tools_needed=[],
            suggested_orchestrator="standard",
            critique_rounds=0,
            thinking_budget="none",
            confidence=0.95,
        )

        plan1 = ExecutionPlan.from_router_output(
            router_output=router_output,
            session_id="session-1",
            message="Hello",
            executor_model="gemini-3-flash",
            estimated_cost=Decimal("0.001"),
        )

        plan2 = ExecutionPlan.from_router_output(
            router_output=router_output,
            session_id="session-1",
            message="Hello",
            executor_model="gemini-3-flash",
            estimated_cost=Decimal("0.001"),
        )

        assert plan1.plan_id != plan2.plan_id
        assert plan1.plan_id.startswith("plan-")
        assert plan2.plan_id.startswith("plan-")
