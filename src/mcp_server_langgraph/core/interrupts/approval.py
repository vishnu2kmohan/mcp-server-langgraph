"""
Approval System for Human-in-the-Loop Workflows

Provides approval nodes that pause agent execution pending human review.

Architecture:
    Agent Graph → Approval Node (pauses) → Human Decision → Resume/Reject

Use Cases:
    - Financial transactions requiring approval
    - Content publishing workflows
    - High-stakes automation
    - Compliance checkpoints
    - Security-sensitive operations

Example:
    from langgraph.graph import StateGraph
    from mcp_server_langgraph.core.interrupts import ApprovalNode

    graph = StateGraph(MyState)
    graph.add_node("action", risky_action)
    graph.add_node("approval", ApprovalNode("approve_risky_action"))

    # Add edge with interrupt
    graph.add_edge("approval", "action")

    # Execution will pause at approval node
    app = graph.compile(checkpointer=checkpointer, interrupt_before=["action"])
"""

from datetime import datetime, timezone
from enum import Enum
from typing import Any, Dict, List, Optional

from pydantic import BaseModel, Field


class ApprovalStatus(str, Enum):
    """Status of approval request."""

    PENDING = "pending"
    APPROVED = "approved"
    REJECTED = "rejected"
    EXPIRED = "expired"


class ApprovalRequired(BaseModel):
    """
    Approval request model.

    Represents a pending approval requiring human decision.
    """

    approval_id: str = Field(description="Unique approval ID")
    node_name: str = Field(description="Node requiring approval")
    action_description: str = Field(description="What action needs approval")
    risk_level: str = Field(default="medium", description="Risk level: low, medium, high, critical")
    context: Dict[str, Any] = Field(default_factory=dict, description="Additional context for decision")
    requested_at: str = Field(
        default_factory=lambda: datetime.now(timezone.utc).isoformat(), description="When approval was requested"
    )
    requested_by: str = Field(default="system", description="Who/what requested approval")
    expires_at: Optional[str] = Field(default=None, description="Optional expiration time")
    metadata: Dict[str, Any] = Field(default_factory=dict, description="Additional metadata")


class ApprovalResponse(BaseModel):
    """
    Approval decision from human reviewer.
    """

    approval_id: str = Field(description="ID of the approval request")
    status: ApprovalStatus = Field(description="Approval decision")
    approved_by: str = Field(description="Who approved/rejected")
    approved_at: str = Field(
        default_factory=lambda: datetime.now(timezone.utc).isoformat(), description="When decision was made"
    )
    reason: Optional[str] = Field(default=None, description="Reason for decision")
    modifications: Optional[Dict[str, Any]] = Field(default=None, description="Modifications to proposed action")


class ApprovalNode:
    """
    Approval node that pauses execution for human review.

    This node integrates with LangGraph's interrupt mechanism to pause
    execution until a human makes an approval decision.
    """

    def __init__(
        self,
        approval_name: str,
        description: str = "",
        risk_level: str = "medium",
        auto_approve_timeout: Optional[int] = None,
        notification_webhook: Optional[str] = None,
    ):
        """
        Initialize approval node.

        Args:
            approval_name: Unique name for this approval type
            description: Description of what needs approval
            risk_level: Risk level (low, medium, high, critical)
            auto_approve_timeout: Auto-approve after N seconds (optional)
            notification_webhook: Webhook URL to notify approvers
        """
        self.approval_name = approval_name
        self.description = description or f"Approval required: {approval_name}"
        self.risk_level = risk_level
        self.auto_approve_timeout = auto_approve_timeout
        self.notification_webhook = notification_webhook

    def __call__(self, state: Dict[str, Any]) -> Dict[str, Any]:
        """
        Execute approval node.

        Creates approval request and pauses execution.

        Args:
            state: Current agent state

        Returns:
            Updated state with approval request
        """
        # Generate approval ID
        approval_id = f"{self.approval_name}_{datetime.now(timezone.utc).timestamp()}"

        # Create approval request
        approval_request = ApprovalRequired(
            approval_id=approval_id,
            node_name=self.approval_name,
            action_description=self.description,
            risk_level=self.risk_level,
            context=state.copy(),  # Include full state for context
        )

        # Store approval request in state
        if "approval_requests" not in state:
            state["approval_requests"] = []

        state["approval_requests"].append(approval_request.model_dump())

        # Mark as pending approval
        state["pending_approval"] = True
        state["current_approval_id"] = approval_id

        # Send notification if webhook configured
        if self.notification_webhook:
            self._send_notification(approval_request)

        # Return state (execution will interrupt here)
        return state

    def _send_notification(self, approval: ApprovalRequired) -> None:
        """
        Send notification to approvers.

        Args:
            approval: Approval request

        In production, implement:
        - Webhook POST to notification service
        - Email notification
        - Slack/Teams message
        - Mobile push notification
        """
        # Placeholder for notification logic
        print(f"📧 Notification: Approval required for {approval.node_name}")
        print(f"   Risk Level: {approval.risk_level}")
        print(f"   Description: {approval.action_description}")


def create_approval_workflow(
    graph: Any,
    approval_points: List[str],
    notification_webhook: Optional[str] = None,
) -> Any:
    """
    Add approval points to an existing graph.

    Args:
        graph: LangGraph StateGraph
        approval_points: List of node names requiring approval
        notification_webhook: Optional webhook for notifications

    Returns:
        Modified graph with approval nodes

    Example:
        from langgraph.graph import StateGraph
        from mcp_server_langgraph.core.interrupts import create_approval_workflow

        graph = StateGraph(MyState)
        graph.add_node("risky_action", perform_action)

        # Add approval before risky action
        graph = create_approval_workflow(
            graph,
            approval_points=["risky_action"],
            notification_webhook="https://api.example.com/notify"
        )

        # Compile with interrupt
        app = graph.compile(interrupt_before=["risky_action"])
    """
    for node_name in approval_points:
        approval_node = ApprovalNode(node_name, notification_webhook=notification_webhook)

        # Add approval node before the target
        graph.add_node(f"approve_{node_name}", approval_node)

    return graph


def check_approval_status(state: Dict[str, Any], approval_id: str) -> ApprovalStatus:
    """
    Check status of an approval request.

    Args:
        state: Current state
        approval_id: Approval ID to check

    Returns:
        ApprovalStatus

    Example:
        status = check_approval_status(state, "approval_123")
        if status == ApprovalStatus.APPROVED:
            # Continue execution
            pass
    """
    approvals = state.get("approval_responses", {})

    if approval_id in approvals:
        return ApprovalStatus(approvals[approval_id]["status"])

    return ApprovalStatus.PENDING


def approve_action(state: Dict[str, Any], approval_id: str, approved_by: str, reason: Optional[str] = None) -> Dict[str, Any]:
    """
    Approve a pending action.

    Args:
        state: Current state
        approval_id: Approval ID
        approved_by: Who is approving
        reason: Optional approval reason

    Returns:
        Updated state

    Example:
        # Resume execution with approval
        state = approve_action(
            state,
            approval_id="action_123",
            approved_by="john@example.com",
            reason="Verified with finance team"
        )
    """
    if "approval_responses" not in state:
        state["approval_responses"] = {}

    response = ApprovalResponse(
        approval_id=approval_id, status=ApprovalStatus.APPROVED, approved_by=approved_by, reason=reason
    )

    state["approval_responses"][approval_id] = response.model_dump()
    state["pending_approval"] = False

    return state


def reject_action(state: Dict[str, Any], approval_id: str, rejected_by: str, reason: str) -> Dict[str, Any]:
    """
    Reject a pending action.

    Args:
        state: Current state
        approval_id: Approval ID
        rejected_by: Who is rejecting
        reason: Rejection reason (required)

    Returns:
        Updated state

    Example:
        # Reject action and halt
        state = reject_action(
            state,
            approval_id="action_123",
            rejected_by="jane@example.com",
            reason="Risk too high without additional review"
        )
    """
    if "approval_responses" not in state:
        state["approval_responses"] = {}

    response = ApprovalResponse(
        approval_id=approval_id, status=ApprovalStatus.REJECTED, approved_by=rejected_by, reason=reason
    )

    state["approval_responses"][approval_id] = response.model_dump()
    state["pending_approval"] = False
    state["workflow_halted"] = True

    return state
