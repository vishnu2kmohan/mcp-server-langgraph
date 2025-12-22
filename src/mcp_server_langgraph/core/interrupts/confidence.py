"""
Confidence-Based Approval Node for Human-in-the-Loop Workflows.

Pauses agent execution when confidence drops below a configurable threshold,
enabling human review of low-confidence decisions.

Architecture:
    Agent Graph → Confidence Node (checks score) → Approval if low → Resume/Reject

Use Cases:
    - AI recommendations requiring human validation
    - Automated decisions with uncertainty
    - Compliance checkpoints for low-confidence outputs
    - Risk mitigation for model uncertainty

Example:
    from langgraph.graph import StateGraph
    from mcp_server_langgraph.core.interrupts.confidence import (
        ConfidenceApprovalNode,
    )

    graph = StateGraph(MyState)
    graph.add_node("analyze", analyze_data)
    graph.add_node("confidence_check", ConfidenceApprovalNode(threshold=0.7))
    graph.add_node("action", perform_action)

    graph.add_edge("analyze", "confidence_check")
    graph.add_edge("confidence_check", "action")

    # Compile with interrupt before action for low-confidence cases
    app = graph.compile(checkpointer=checkpointer, interrupt_before=["action"])
"""

from __future__ import annotations

from datetime import UTC, datetime
from typing import Any

from mcp_server_langgraph.core.interrupts.approval import ApprovalRequired

# Default threshold for requiring human approval
DEFAULT_CONFIDENCE_THRESHOLD = 0.7

# Threshold for auto-approval (skip human review)
AUTO_APPROVE_THRESHOLD = 0.9


def check_confidence(
    confidence: float,
    threshold: float = DEFAULT_CONFIDENCE_THRESHOLD,
) -> bool:
    """
    Check if confidence meets the approval threshold.

    Args:
        confidence: Confidence score (0.0 to 1.0)
        threshold: Minimum confidence to pass without approval (default: 0.7)

    Returns:
        True if confidence >= threshold (no approval needed)
        False if confidence < threshold (approval required)

    Example:
        if not check_confidence(result.confidence, threshold=0.8):
            # Trigger approval workflow
            request_approval(result)
    """
    return confidence >= threshold


class ConfidenceApprovalNode:
    """
    Approval node that pauses execution when confidence is below threshold.

    This node integrates with LangGraph's interrupt mechanism to pause
    execution for human review when agent confidence is low.
    """

    def __init__(
        self,
        threshold: float = DEFAULT_CONFIDENCE_THRESHOLD,
        name: str = "confidence_approval",
        description: str | None = None,
        notification_webhook: str | None = None,
    ) -> None:
        """
        Initialize confidence approval node.

        Args:
            threshold: Confidence threshold (0-1). Below this triggers approval.
            name: Name for this approval node.
            description: Optional description of what needs approval.
            notification_webhook: Optional webhook URL to notify approvers.
        """
        self.threshold = threshold
        self.name = name
        self.description = description or f"Approval required when confidence < {threshold:.0%}"
        self.notification_webhook = notification_webhook

    def __call__(self, state: dict[str, Any]) -> dict[str, Any]:
        """
        Execute confidence check node.

        Checks for confidence in state (routing_confidence or verification_score).
        If confidence < threshold, creates approval request and marks pending.

        Args:
            state: Current agent state

        Returns:
            Updated state (with approval request if confidence is low)
        """
        # Get confidence from state (try routing_confidence first, then verification_score)
        confidence = state.get("routing_confidence") or state.get("verification_score")

        # If no confidence in state, pass through (conservative approach)
        if confidence is None:
            return state

        # Check if confidence meets threshold
        if check_confidence(confidence, self.threshold):
            # Confidence is good, pass through without approval
            return state

        # Confidence is low - create approval request
        approval_id = f"{self.name}_{datetime.now(UTC).timestamp()}"

        # Format confidence as percentage for human-readable description
        confidence_pct = f"{confidence:.0%}"
        threshold_pct = f"{self.threshold:.0%}"

        action_description = (
            f"Agent confidence ({confidence_pct}) is below threshold ({threshold_pct}). "
            f"Human approval required to proceed."
        )

        # Determine risk level based on how far below threshold
        if confidence < 0.3:
            risk_level = "high"
        elif confidence < 0.5:
            risk_level = "medium"
        else:
            risk_level = "low"

        # Create approval request following ApprovalRequired schema
        approval_request = ApprovalRequired(
            approval_id=approval_id,
            node_name=self.name,
            action_description=action_description,
            risk_level=risk_level,
            context={
                "confidence": confidence,
                "threshold": self.threshold,
            },
        )

        # Add approval request to state
        if "approval_requests" not in state:
            state["approval_requests"] = []

        state["approval_requests"].append(approval_request.model_dump())

        # Mark as pending approval
        state["pending_approval"] = True
        state["current_approval_id"] = approval_id

        # Send notification if webhook configured
        if self.notification_webhook:
            self._send_notification(approval_request)

        return state

    def _send_notification(self, approval: ApprovalRequired) -> None:
        """
        Send notification to approvers.

        Args:
            approval: Approval request

        In production, implement:
        - Webhook POST to notification service
        - WebSocket push to connected clients
        - Email notification
        - Slack/Teams message
        """
        # Placeholder for notification logic
        import logging

        logger = logging.getLogger(__name__)
        logger.info(
            "HITL notification: Approval required for %s (confidence: %s)",
            approval.node_name,
            approval.context.get("confidence"),
        )
