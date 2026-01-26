"""
Execution Plan Model

Represents a pending execution plan that may require approval before execution.
Integrates with RouterOutput for orchestration decisions.

Usage:
    from mcp_server_langgraph.core.models.execution_plan import ExecutionPlan

    plan = ExecutionPlan.from_router_output(
        router_output=router_result,
        session_id="session-123",
        message="Help me refactor",
        executor_model="claude-opus-4-5-20251101",
        estimated_cost=Decimal("0.10"),
    )

    if plan.requires_approval:
        # Wait for user approval
        ...
    else:
        # Auto-execute
        ...
"""

from __future__ import annotations

from datetime import datetime, timedelta, UTC
from decimal import Decimal
from typing import TYPE_CHECKING, Literal
from uuid import uuid4

from pydantic import BaseModel, Field

if TYPE_CHECKING:
    from mcp_server_langgraph.agents.router_agent import RouterOutput


def _now() -> datetime:
    """Get current UTC time."""
    return datetime.now(UTC)


def _default_expiry() -> datetime:
    """Get default expiry time (1 hour from now)."""
    return datetime.now(UTC) + timedelta(hours=1)


class ExecutionPlan(BaseModel):
    """Execution plan for pending or completed operations.

    Tracks the full lifecycle of a plan from creation through approval
    or rejection to execution.

    Attributes:
        plan_id: Unique plan identifier
        session_id: Session this plan belongs to
        status: Current plan status
        complexity: Task complexity from router
        risk_level: Risk level from router
        task_type: Task type from router
        executor_model: Model ID for execution
        critic_model: Optional critic model for review
        estimated_cost: Estimated cost in USD
        actual_cost: Actual cost after execution
        message: Original user message
        suggested_orchestrator: Orchestrator pattern to use
        critique_rounds: Number of critique iterations
        thinking_budget: Extended thinking level
        tools_needed: List of tools the task may need
        confidence: Router confidence in classification
        created_at: When plan was created
        expires_at: When plan expires
        approved_by: Who approved the plan
        approved_at: When plan was approved
        rejected_by: Who rejected the plan
        rejected_at: When plan was rejected
        rejection_reason: Reason for rejection
        executed_at: When plan was executed
    """

    plan_id: str
    session_id: str
    status: Literal["awaiting_approval", "approved", "rejected", "executed", "expired"]
    complexity: Literal["simple", "complicated", "complex"]
    risk_level: Literal["low", "medium", "high"]
    task_type: Literal["chat", "code", "analysis", "data", "ops", "other"]
    executor_model: str
    estimated_cost: Decimal
    message: str

    # Optional fields
    critic_model: str | None = None
    actual_cost: Decimal | None = None
    suggested_orchestrator: Literal["standard", "swarm", "studio", "ux", "alert"] = "standard"
    critique_rounds: int = Field(default=0, ge=0, le=3)
    thinking_budget: Literal["none", "light", "medium", "deep"] = "none"
    tools_needed: list[str] = Field(default_factory=list)
    confidence: float = Field(default=0.0, ge=0.0, le=1.0)

    # Timestamps
    created_at: datetime = Field(default_factory=_now)
    expires_at: datetime = Field(default_factory=_default_expiry)

    # Approval tracking
    approved_by: str | None = None
    approved_at: datetime | None = None
    rejected_by: str | None = None
    rejected_at: datetime | None = None
    rejection_reason: str | None = None
    executed_at: datetime | None = None

    @property
    def is_expired(self) -> bool:
        """Check if plan has expired."""
        return datetime.now(UTC) > self.expires_at

    # Approval override (set by plan mode)
    force_approval: bool = False

    @property
    def requires_approval(self) -> bool:
        """Check if plan requires manual approval.

        Approval is required when:
        - force_approval is True (user selected Plan mode)
        - OR risk_level is medium or high

        Low-risk plans can auto-execute unless force_approval is set.
        """
        return self.force_approval or self.risk_level != "low"

    def approve(self, approved_by: str) -> ExecutionPlan:
        """Approve the plan for execution.

        Args:
            approved_by: Identifier of approver (email, user_id, etc.)

        Returns:
            New ExecutionPlan with approved status
        """
        return self.model_copy(
            update={
                "status": "approved",
                "approved_by": approved_by,
                "approved_at": _now(),
            }
        )

    def reject(self, rejected_by: str, reason: str) -> ExecutionPlan:
        """Reject the plan.

        Args:
            rejected_by: Identifier of rejector
            reason: Reason for rejection

        Returns:
            New ExecutionPlan with rejected status
        """
        return self.model_copy(
            update={
                "status": "rejected",
                "rejected_by": rejected_by,
                "rejected_at": _now(),
                "rejection_reason": reason,
            }
        )

    def mark_executed(self, actual_cost: Decimal | None = None) -> ExecutionPlan:
        """Mark plan as executed.

        Args:
            actual_cost: Actual cost of execution (optional)

        Returns:
            New ExecutionPlan with executed status
        """
        return self.model_copy(
            update={
                "status": "executed",
                "executed_at": _now(),
                "actual_cost": actual_cost,
            }
        )

    @classmethod
    def from_router_output(
        cls,
        router_output: RouterOutput,
        session_id: str,
        message: str,
        executor_model: str,
        estimated_cost: Decimal,
        critic_model: str | None = None,
        plan_id: str | None = None,
        force_approval: bool = False,
    ) -> ExecutionPlan:
        """Create an ExecutionPlan from RouterOutput.

        Args:
            router_output: RouterOutput from router agent
            session_id: Session ID for the plan
            message: Original user message
            executor_model: Selected executor model
            estimated_cost: Estimated cost for execution
            critic_model: Optional critic model
            plan_id: Optional plan ID (auto-generated if not provided)
            force_approval: Force approval requirement (e.g., plan mode)

        Returns:
            New ExecutionPlan instance
        """
        return cls(
            plan_id=plan_id or f"plan-{uuid4().hex[:16]}",
            session_id=session_id,
            status="awaiting_approval",
            complexity=router_output.complexity,
            risk_level=router_output.risk,
            task_type=router_output.task_type,
            executor_model=executor_model,
            critic_model=critic_model,
            estimated_cost=estimated_cost,
            message=message,
            suggested_orchestrator=router_output.suggested_orchestrator,
            critique_rounds=router_output.critique_rounds,
            thinking_budget=router_output.thinking_budget,
            tools_needed=router_output.tools_needed,
            confidence=router_output.confidence,
            force_approval=force_approval,
        )
