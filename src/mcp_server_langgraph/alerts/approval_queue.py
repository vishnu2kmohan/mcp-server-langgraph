"""
Remediation Approval Queue.

Manages pending remediation actions that require human approval before execution.

Features:
- Queue remediation steps from AI recommendations
- List pending remediations
- Approve/reject remediation actions
- History tracking

Reference: ADR-0026 - Comprehensive Client Resilience Patterns
"""

import asyncio
import logging
import uuid
from datetime import UTC, datetime

from pydantic import BaseModel, Field

from mcp_server_langgraph.alerts.ai_recommendation import AIRecommendation
from mcp_server_langgraph.alerts.feedback import (
    FeedbackStore,
    RejectionReason,
    RemediationFeedback,
)
from mcp_server_langgraph.core.interrupts.approval import ApprovalStatus

logger = logging.getLogger(__name__)


class RemediationRequest(BaseModel):
    """A pending remediation action requiring approval."""

    remediation_id: str = Field(..., description="Unique remediation ID")
    alert_id: str = Field(..., description="Associated alert ID")
    alert_name: str = Field(..., description="Name of the alert")
    severity: str = Field(..., description="Alert severity")
    step_number: int = Field(..., description="Step number in remediation plan")
    action: str = Field(..., description="Action type")
    description: str = Field(..., description="Human-readable description")
    command: str | None = Field(None, description="Command to execute")
    risk_level: str = Field("medium", description="Risk level")
    status: ApprovalStatus = Field(ApprovalStatus.PENDING, description="Current status")
    requested_at: str = Field(..., description="When remediation was requested")
    approved_by: str | None = Field(None, description="Who approved/rejected")
    approved_at: str | None = Field(None, description="When decision was made")
    reason: str | None = Field(None, description="Reason for rejection")
    recommendation_id: str | None = Field(None, description="Source recommendation ID")


class RemediationApprovalQueue:
    """
    Queue for managing remediation approvals.

    Stores pending remediations and tracks their approval status.
    In production, this would be backed by PostgreSQL.
    """

    def __init__(self) -> None:
        """Initialize the approval queue."""
        self._remediations: dict[str, RemediationRequest] = {}
        self._lock = asyncio.Lock()

    async def queue_remediation(
        self,
        alert_id: str,
        alert_name: str,
        severity: str,
        recommendation: AIRecommendation,
    ) -> list[RemediationRequest]:
        """
        Queue remediation steps from an AI recommendation.

        Creates a pending remediation request for each step that requires approval.

        Args:
            alert_id: ID of the alert.
            alert_name: Name of the alert.
            severity: Alert severity.
            recommendation: AI recommendation with remediation steps.

        Returns:
            List of created remediation requests.
        """
        created: list[RemediationRequest] = []

        async with self._lock:
            for step in recommendation.remediation_steps:
                # Only queue steps that require approval
                if not step.get("requires_approval", True):
                    continue

                remediation_id = str(uuid.uuid4())

                request = RemediationRequest(
                    remediation_id=remediation_id,
                    alert_id=alert_id,
                    alert_name=alert_name,
                    severity=severity,
                    step_number=step.get("step_number", 0),
                    action=step.get("action", "unknown"),
                    description=step.get("description", ""),
                    command=step.get("command"),
                    risk_level=step.get("risk_level", "medium"),
                    status=ApprovalStatus.PENDING,
                    requested_at=datetime.now(UTC).isoformat(),
                    approved_by=None,
                    approved_at=None,
                    reason=None,
                    recommendation_id=recommendation.recommendation_id,
                )

                self._remediations[remediation_id] = request
                created.append(request)

                logger.info(
                    f"Queued remediation {remediation_id} for alert {alert_id}",
                    extra={
                        "remediation_id": remediation_id,
                        "alert_id": alert_id,
                        "action": request.action,
                    },
                )

        return created

    async def list_pending(self) -> list[RemediationRequest]:
        """
        List all pending remediations.

        Returns:
            List of pending remediation requests.
        """
        async with self._lock:
            return [
                r for r in self._remediations.values()
                if r.status == ApprovalStatus.PENDING
            ]

    async def get_remediation(self, remediation_id: str) -> RemediationRequest | None:
        """
        Get a specific remediation by ID.

        Args:
            remediation_id: The remediation ID to look up.

        Returns:
            RemediationRequest or None if not found.
        """
        return self._remediations.get(remediation_id)

    async def approve(
        self,
        remediation_id: str,
        approved_by: str,
    ) -> RemediationRequest:
        """
        Approve a pending remediation.

        Args:
            remediation_id: ID of the remediation to approve.
            approved_by: Email/ID of the approver.

        Returns:
            Updated RemediationRequest.

        Raises:
            KeyError: If remediation not found.
            ValueError: If remediation is not pending.
        """
        async with self._lock:
            if remediation_id not in self._remediations:
                raise KeyError(f"Remediation {remediation_id} not found")

            request = self._remediations[remediation_id]

            if request.status != ApprovalStatus.PENDING:
                raise ValueError(f"Remediation {remediation_id} is not pending")

            request.status = ApprovalStatus.APPROVED
            request.approved_by = approved_by
            request.approved_at = datetime.now(UTC).isoformat()

            logger.info(
                f"Approved remediation {remediation_id}",
                extra={
                    "remediation_id": remediation_id,
                    "approved_by": approved_by,
                },
            )

            return request

    async def reject(
        self,
        remediation_id: str,
        rejected_by: str,
        reason: str | None = None,
    ) -> RemediationRequest:
        """
        Reject a pending remediation.

        Args:
            remediation_id: ID of the remediation to reject.
            rejected_by: Email/ID of the rejector.
            reason: Optional reason for rejection.

        Returns:
            Updated RemediationRequest.

        Raises:
            KeyError: If remediation not found.
            ValueError: If remediation is not pending.
        """
        async with self._lock:
            if remediation_id not in self._remediations:
                raise KeyError(f"Remediation {remediation_id} not found")

            request = self._remediations[remediation_id]

            if request.status != ApprovalStatus.PENDING:
                raise ValueError(f"Remediation {remediation_id} is not pending")

            request.status = ApprovalStatus.REJECTED
            request.approved_by = rejected_by
            request.approved_at = datetime.now(UTC).isoformat()
            request.reason = reason

            logger.info(
                f"Rejected remediation {remediation_id}",
                extra={
                    "remediation_id": remediation_id,
                    "rejected_by": rejected_by,
                    "reason": reason,
                },
            )

            return request

    async def get_history(
        self,
        limit: int = 100,
        offset: int = 0,
    ) -> list[RemediationRequest]:
        """
        Get completed remediation history.

        Args:
            limit: Maximum number of results.
            offset: Number of results to skip.

        Returns:
            List of completed (approved/rejected) remediation requests.
        """
        async with self._lock:
            completed = [
                r for r in self._remediations.values()
                if r.status in (ApprovalStatus.APPROVED, ApprovalStatus.REJECTED)
            ]
            # Sort by approved_at descending (most recent first)
            completed.sort(key=lambda x: x.approved_at or "", reverse=True)
            return completed[offset : offset + limit]

    async def approve_with_feedback(
        self,
        remediation_id: str,
        approved_by: str,
        feedback_store: FeedbackStore,
    ) -> RemediationRequest:
        """
        Approve a pending remediation and save feedback for AI learning.

        Args:
            remediation_id: ID of the remediation to approve.
            approved_by: Email/ID of the approver.
            feedback_store: Store for saving feedback.

        Returns:
            Updated RemediationRequest.

        Raises:
            KeyError: If remediation not found.
            ValueError: If remediation is not pending.
        """
        request = await self.approve(remediation_id, approved_by)

        # Save feedback for AI learning
        feedback = RemediationFeedback(
            feedback_id=str(uuid.uuid4()),
            remediation_id=remediation_id,
            recommendation_id=request.recommendation_id or "",
            alert_type=request.alert_name,
            alert_labels={},  # Labels would come from alert context if available
            severity=request.severity,
            action="approved",
            reason=None,
            reason_detail=None,
            admin_user_id=approved_by,
            timestamp=datetime.now(UTC),
        )

        await feedback_store.save_feedback(feedback)

        logger.info(
            f"Saved approval feedback for remediation {remediation_id}",
            extra={
                "remediation_id": remediation_id,
                "approved_by": approved_by,
            },
        )

        return request

    async def reject_with_feedback(
        self,
        remediation_id: str,
        rejected_by: str,
        reason: RejectionReason,
        feedback_store: FeedbackStore,
        reason_detail: str | None = None,
    ) -> RemediationRequest:
        """
        Reject a pending remediation and save feedback for AI learning.

        Args:
            remediation_id: ID of the remediation to reject.
            rejected_by: Email/ID of the rejector.
            reason: Structured rejection reason.
            feedback_store: Store for saving feedback.
            reason_detail: Optional additional details.

        Returns:
            Updated RemediationRequest.

        Raises:
            KeyError: If remediation not found.
            ValueError: If remediation is not pending.
        """
        # Convert RejectionReason to string for the standard reject
        reason_str = f"{reason.value}: {reason_detail}" if reason_detail else reason.value
        request = await self.reject(remediation_id, rejected_by, reason_str)

        # Save feedback for AI learning
        feedback = RemediationFeedback(
            feedback_id=str(uuid.uuid4()),
            remediation_id=remediation_id,
            recommendation_id=request.recommendation_id or "",
            alert_type=request.alert_name,
            alert_labels={},  # Labels would come from alert context if available
            severity=request.severity,
            action="rejected",
            reason=reason,
            reason_detail=reason_detail,
            admin_user_id=rejected_by,
            timestamp=datetime.now(UTC),
        )

        await feedback_store.save_feedback(feedback)

        logger.info(
            f"Saved rejection feedback for remediation {remediation_id}",
            extra={
                "remediation_id": remediation_id,
                "rejected_by": rejected_by,
                "reason": reason.value,
            },
        )

        return request


# Global instance
_approval_queue: RemediationApprovalQueue | None = None


def get_approval_queue() -> RemediationApprovalQueue:
    """Get the global remediation approval queue instance."""
    global _approval_queue
    if _approval_queue is None:
        _approval_queue = RemediationApprovalQueue()
    return _approval_queue


def set_approval_queue(queue: RemediationApprovalQueue | None) -> None:
    """Set the global remediation approval queue (for testing)."""
    global _approval_queue
    _approval_queue = queue
