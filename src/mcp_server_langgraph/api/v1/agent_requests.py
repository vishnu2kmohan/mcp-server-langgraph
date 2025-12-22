"""
Agent Request REST API for Human-in-the-Loop (HITL) Workflows.

Provides endpoints for managing agent approval and clarification requests
when agent confidence drops below the configured threshold.

Endpoints:
- GET /agents/requests/pending - List pending agent requests
- GET /agents/requests/{request_id} - Get request details
- POST /agents/requests/{request_id}/approve - Approve a request
- POST /agents/requests/{request_id}/reject - Reject a request
- POST /agents/requests/{request_id}/respond - Respond to clarification

SECURITY:
All agent request endpoints require authentication.
Approve/reject operations require admin or hitl_reviewer role.

Reference: Plan - Confidence-Based Human-in-the-Loop for Multi-Agent Orchestrator
"""

from __future__ import annotations

import logging
from datetime import UTC, datetime
from enum import Enum
from typing import Annotated, Any
from uuid import uuid4

from fastapi import APIRouter, Depends, HTTPException, Query, status
from pydantic import BaseModel, Field

from mcp_server_langgraph.api.deps import get_audit_service
from mcp_server_langgraph.audit.models import (
    AuditActor,
    AuditContext,
    AuditEventCategory,
    AuditEventType,
    UnifiedAuditEvent,
)
from mcp_server_langgraph.audit.service import UnifiedAuditService
from mcp_server_langgraph.auth.middleware import get_current_user
from mcp_server_langgraph.core.feature_flags import feature_flags
from mcp_server_langgraph.core.interrupts.ai_explanation import AIExplanation
from mcp_server_langgraph.core.interrupts.clarification import (
    ClarificationOption,
    ClarificationType,
)

logger = logging.getLogger(__name__)

# Type alias for authenticated user dependency
CurrentUser = Annotated[dict[str, Any], Depends(get_current_user)]

# Type alias for optional audit service dependency
AuditService = Annotated[UnifiedAuditService | None, Depends(get_audit_service)]


# =========================================================================
# Enums
# =========================================================================


class AgentRequestType(str, Enum):
    """Type of agent HITL request."""

    APPROVAL = "approval"
    """Low confidence decision requiring approval."""

    CLARIFICATION = "clarification"
    """Agent needs clarification from user."""


class AgentRequestStatus(str, Enum):
    """Status of an agent request."""

    PENDING = "pending"
    """Request is awaiting human response."""

    APPROVED = "approved"
    """Request was approved."""

    REJECTED = "rejected"
    """Request was rejected."""

    RESPONDED = "responded"
    """Clarification request was answered."""

    TIMEOUT = "timeout"
    """Request timed out without response."""


# =========================================================================
# Request/Response Models
# =========================================================================


class AgentRequest(BaseModel):
    """Agent HITL request details."""

    request_id: str = Field(description="Unique request identifier")
    session_id: str = Field(description="Session ID for the agent")
    task_id: str = Field(description="Task ID being executed")
    agent_name: str = Field(description="Name of the agent making the request")
    request_type: AgentRequestType = Field(description="Type of request")
    confidence: float | None = Field(
        default=None,
        description="Agent confidence score (0-1)",
    )
    threshold: float | None = Field(
        default=None,
        description="Confidence threshold that triggered the request",
    )
    question: str = Field(description="Question or action description")
    proposed_action: str | None = Field(
        default=None,
        description="Proposed action for approval requests",
    )
    trigger_reason: str | None = Field(
        default=None,
        description="Reason that triggered the request (e.g., low_confidence, destructive_action)",
    )
    placeholder: str | None = Field(
        default=None,
        description="Placeholder text for text input clarifications",
    )
    clarification_type: ClarificationType | None = Field(
        default=None,
        description="Type of clarification (for clarification requests)",
    )
    options: list[ClarificationOption] | None = Field(
        default=None,
        description="Options for choice clarifications",
    )
    status: AgentRequestStatus = Field(description="Current status")
    requested_at: str = Field(description="ISO 8601 timestamp")
    responded_at: str | None = Field(
        default=None,
        description="When the request was responded to",
    )
    responded_by: str | None = Field(
        default=None,
        description="Who responded to the request",
    )
    context: dict[str, Any] = Field(
        default_factory=dict,
        description="Additional context for the request",
    )
    ai_explanation: AIExplanation | None = Field(
        default=None,
        description="AI-generated explanation for HITL dialog (when enable_ai_explanations is True)",
    )


class ApproveAgentRequest(BaseModel):
    """Request body for approving an agent request."""

    approved_by: str = Field(..., description="Email/ID of the approver")
    reason: str | None = Field(default=None, description="Approval reason")
    modifications: dict[str, Any] | None = Field(
        default=None,
        description="Modifications to the proposed action",
    )


class RejectAgentRequest(BaseModel):
    """Request body for rejecting an agent request."""

    rejected_by: str = Field(..., description="Email/ID of the rejector")
    reason: str = Field(..., description="Rejection reason")


class ClarificationResponseRequest(BaseModel):
    """Request body for responding to a clarification request."""

    responded_by: str = Field(..., description="Email/ID of the responder")
    response_type: ClarificationType = Field(description="Type of response")
    value: str | None = Field(default=None, description="Text response")
    selected_option_id: str | None = Field(
        default=None,
        description="Selected option ID (for choice type)",
    )
    confirmed: bool | None = Field(
        default=None,
        description="Confirmation result (for confirmation type)",
    )


class PendingAgentRequestsResponse(BaseModel):
    """Response for list pending agent requests."""

    requests: list[AgentRequest]
    count: int


class AgentRequestActionResponse(BaseModel):
    """Response for approve/reject/respond actions."""

    request_id: str
    status: AgentRequestStatus
    message: str
    resumed: bool = Field(
        default=False,
        description="Whether the agent execution was resumed",
    )


# =========================================================================
# Rotating Threshold Models
# =========================================================================


class ApprovalHistory(BaseModel):
    """Record of a single approval/rejection decision for threshold analysis."""

    user_id: str = Field(description="User who made the decision")
    decision: str = Field(description="Decision: 'approved' or 'rejected'")
    confidence: float = Field(
        description="Agent confidence at the time of decision",
        ge=0.0,
        le=1.0,
    )
    threshold: float = Field(
        description="Threshold at the time of decision",
        ge=0.0,
        le=1.0,
    )
    decided_at: str = Field(description="ISO 8601 timestamp of decision")


class ThresholdRecommendation(BaseModel):
    """Recommendation for threshold adjustment based on approval patterns."""

    current_threshold: float = Field(description="Current threshold value")
    recommended_threshold: float = Field(description="Recommended new threshold")
    reason: str = Field(description="Explanation for the recommendation")
    confidence_level: float = Field(
        description="Confidence in the recommendation (0-1)",
        ge=0.0,
        le=1.0,
    )
    sample_size: int = Field(description="Number of decisions analyzed")


class UserThresholdSettings(BaseModel):
    """User-specific threshold configuration."""

    user_id: str = Field(description="User ID")
    base_threshold: float = Field(
        description="Base threshold before adjustments",
        ge=0.0,
        le=1.0,
    )
    adjusted_threshold: float = Field(
        description="Currently adjusted threshold",
        ge=0.0,
        le=1.0,
    )
    auto_adjust_enabled: bool = Field(
        default=True,
        description="Whether auto-adjustment is enabled",
    )
    min_threshold: float = Field(
        default=0.5,
        description="Minimum allowed threshold",
        ge=0.0,
        le=1.0,
    )
    max_threshold: float = Field(
        default=0.9,
        description="Maximum allowed threshold",
        ge=0.0,
        le=1.0,
    )


class ThresholdCalculator:
    """
    Calculate threshold recommendations based on approval history.

    Uses approval/rejection patterns to suggest optimal thresholds
    that balance automation with necessary human oversight.
    """

    def __init__(
        self,
        base_threshold: float = 0.7,
        min_threshold: float = 0.5,
        max_threshold: float = 0.9,
        min_sample_size: int = 10,
    ) -> None:
        """
        Initialize the threshold calculator.

        Args:
            base_threshold: Starting threshold value.
            min_threshold: Minimum allowed threshold.
            max_threshold: Maximum allowed threshold.
            min_sample_size: Minimum samples needed for confident recommendations.
        """
        self.base_threshold = base_threshold
        self.min_threshold = min_threshold
        self.max_threshold = max_threshold
        self.min_sample_size = min_sample_size

    def calculate_recommendation(
        self,
        history: list[ApprovalHistory],
    ) -> ThresholdRecommendation:
        """
        Calculate threshold recommendation from approval history.

        Logic:
        - High approval rate (>80%) → recommend lowering threshold
        - High rejection rate (>50%) → recommend raising threshold
        - Insufficient data → keep current threshold with low confidence

        Args:
            history: List of approval/rejection decisions.

        Returns:
            ThresholdRecommendation with suggested adjustments.
        """
        sample_size = len(history)

        # Insufficient data case
        if sample_size < self.min_sample_size:
            return ThresholdRecommendation(
                current_threshold=self.base_threshold,
                recommended_threshold=self.base_threshold,
                reason="Insufficient data for threshold recommendation",
                confidence_level=sample_size / self.min_sample_size * 0.5,
                sample_size=sample_size,
            )

        # Calculate approval rate
        approved_count = sum(1 for h in history if h.decision == "approved")
        approval_rate = approved_count / sample_size

        # Calculate average confidence of requests (for future threshold refinement)
        _avg_confidence = sum(h.confidence for h in history) / sample_size

        # Determine recommendation
        if approval_rate >= 0.8:
            # High approval rate - can lower threshold
            adjustment = (approval_rate - 0.8) * 0.2  # Max 4% adjustment
            new_threshold = max(
                self.min_threshold,
                self.base_threshold - adjustment,
            )
            reason = f"High approval rate ({approval_rate:.0%}) suggests threshold can be lowered"
        elif approval_rate < 0.4:
            # High rejection rate - should raise threshold
            adjustment = (0.5 - approval_rate) * 0.2  # Max 10% adjustment
            new_threshold = min(
                self.max_threshold,
                self.base_threshold + adjustment,
            )
            reason = f"High rejection rate ({1 - approval_rate:.0%}) suggests threshold should be raised"
        else:
            # Moderate approval rate - keep threshold
            new_threshold = self.base_threshold
            reason = f"Balanced approval rate ({approval_rate:.0%}), threshold is appropriate"

        # Calculate confidence level
        confidence_level = min(1.0, sample_size / 50)  # Full confidence at 50+ samples

        return ThresholdRecommendation(
            current_threshold=self.base_threshold,
            recommended_threshold=new_threshold,
            reason=reason,
            confidence_level=confidence_level,
            sample_size=sample_size,
        )


# =========================================================================
# Batch Approval Models
# =========================================================================


class BatchApproveRequest(BaseModel):
    """Request body for batch approving multiple agent requests."""

    request_ids: list[str] = Field(
        ...,
        description="List of request IDs to approve",
        min_length=0,
    )
    reason: str | None = Field(
        default=None,
        description="Common reason for all approvals",
    )


class BatchRejectRequest(BaseModel):
    """Request body for batch rejecting multiple agent requests."""

    request_ids: list[str] = Field(
        ...,
        description="List of request IDs to reject",
        min_length=0,
    )
    reason: str | None = Field(
        default=None,
        description="Common reason for all rejections",
    )


class BatchApprovalResult(BaseModel):
    """Result for a single request in a batch operation."""

    request_id: str = Field(description="The request ID")
    status: AgentRequestStatus | None = Field(
        default=None,
        description="New status (None if failed)",
    )
    success: bool = Field(description="Whether the operation succeeded")
    message: str = Field(description="Result message")
    error_code: str | None = Field(
        default=None,
        description="Error code if failed",
    )


class BatchApprovalResponse(BaseModel):
    """Response for batch approval/rejection operations."""

    results: list[BatchApprovalResult] = Field(description="Results for each request")
    succeeded: int = Field(description="Count of successful operations")
    failed: int = Field(description="Count of failed operations")


# =========================================================================
# Agent Request Queue Service
# =========================================================================


class AgentRequestQueue:
    """
    In-memory queue for managing agent HITL requests.

    In production, this should be backed by Redis or PostgreSQL
    for persistence and cross-instance coordination.
    """

    def __init__(self) -> None:
        """Initialize the request queue."""
        self._requests: dict[str, AgentRequest] = {}

    async def queue_approval_request(
        self,
        session_id: str,
        task_id: str,
        agent_name: str,
        confidence: float,
        threshold: float,
        proposed_action: str,
        context: dict[str, Any] | None = None,
        trigger_reason: str = "low_confidence",
    ) -> AgentRequest:
        """
        Queue an approval request for low-confidence decision.

        Args:
            session_id: Session ID for the agent.
            task_id: Task ID being executed.
            agent_name: Name of the agent.
            confidence: Agent confidence score.
            threshold: Threshold that triggered the request.
            proposed_action: What the agent wants to do.
            context: Additional context.
            trigger_reason: Reason that triggered the request (default: low_confidence).

        Returns:
            The created AgentRequest.
        """
        request_id = f"req_{uuid4().hex[:12]}"

        # Generate AI explanation if feature is enabled
        ai_explanation: AIExplanation | None = None
        if feature_flags.enable_ai_explanations:
            try:
                from mcp_server_langgraph.agents.explanation_orchestrator import (
                    CachedExplanationOrchestrator,
                )

                orchestrator = CachedExplanationOrchestrator()
                reasoning_trace = (context or {}).get("reasoning_trace", [])
                ai_explanation = await orchestrator.generate_explanation_cached(
                    approval_id=request_id,
                    agent_name=agent_name,
                    proposed_action=proposed_action,
                    confidence=confidence,
                    threshold=threshold,
                    trigger_reason=trigger_reason,
                    reasoning_trace=reasoning_trace,
                )
            except Exception as e:
                logger.warning(
                    "Failed to generate AI explanation",
                    extra={"request_id": request_id, "error": str(e)},
                )
                # Continue without explanation - graceful degradation

        request = AgentRequest(
            request_id=request_id,
            session_id=session_id,
            task_id=task_id,
            agent_name=agent_name,
            request_type=AgentRequestType.APPROVAL,
            confidence=confidence,
            threshold=threshold,
            question=f"Confidence {confidence:.0%} is below threshold {threshold:.0%}. Approve action?",
            proposed_action=proposed_action,
            trigger_reason=trigger_reason,
            status=AgentRequestStatus.PENDING,
            requested_at=datetime.now(UTC).isoformat(),
            context=context or {},
            ai_explanation=ai_explanation,
        )

        self._requests[request_id] = request
        logger.info(
            "Queued approval request",
            extra={
                "request_id": request_id,
                "agent_name": agent_name,
                "confidence": confidence,
                "has_ai_explanation": ai_explanation is not None,
            },
        )

        return request

    async def queue_clarification_request(
        self,
        session_id: str,
        task_id: str,
        agent_name: str,
        clarification_type: ClarificationType,
        question: str,
        options: list[dict[str, Any]] | None = None,
        placeholder: str | None = None,
        context: dict[str, Any] | None = None,
    ) -> AgentRequest:
        """
        Queue a clarification request from an agent.

        Args:
            session_id: Session ID for the agent.
            task_id: Task ID being executed.
            agent_name: Name of the agent.
            clarification_type: Type of clarification needed.
            question: The question to ask.
            options: Options for choice type.
            placeholder: Placeholder for text input.
            context: Additional context.

        Returns:
            The created AgentRequest.
        """
        request_id = f"req_{uuid4().hex[:12]}"

        # Convert options to ClarificationOption if provided
        option_objects = None
        if options:
            option_objects = [ClarificationOption(**opt) for opt in options]

        request = AgentRequest(
            request_id=request_id,
            session_id=session_id,
            task_id=task_id,
            agent_name=agent_name,
            request_type=AgentRequestType.CLARIFICATION,
            question=question,
            clarification_type=clarification_type,
            options=option_objects,
            status=AgentRequestStatus.PENDING,
            requested_at=datetime.now(UTC).isoformat(),
            context=context or {},
        )

        self._requests[request_id] = request
        logger.info(
            "Queued clarification request",
            extra={
                "request_id": request_id,
                "agent_name": agent_name,
                "clarification_type": clarification_type,
            },
        )

        return request

    async def list_pending(
        self,
        session_id: str | None = None,
    ) -> list[AgentRequest]:
        """
        List all pending requests.

        Args:
            session_id: Optional filter by session ID.

        Returns:
            List of pending requests.
        """
        pending = [r for r in self._requests.values() if r.status == AgentRequestStatus.PENDING]

        if session_id:
            pending = [r for r in pending if r.session_id == session_id]

        # Sort by requested_at (oldest first)
        pending.sort(key=lambda r: r.requested_at)

        return pending

    async def get_request(self, request_id: str) -> AgentRequest | None:
        """
        Get a request by ID.

        Args:
            request_id: The request ID.

        Returns:
            The request, or None if not found.
        """
        return self._requests.get(request_id)

    async def approve(
        self,
        request_id: str,
        approved_by: str,
        reason: str | None = None,
        modifications: dict[str, Any] | None = None,
    ) -> AgentRequest:
        """
        Approve a pending request.

        Args:
            request_id: The request ID.
            approved_by: Who is approving.
            reason: Optional approval reason.
            modifications: Optional modifications to the action.

        Returns:
            The updated request.

        Raises:
            KeyError: If request not found.
            ValueError: If request is not pending.
        """
        request = self._requests.get(request_id)
        if request is None:
            raise KeyError(f"Request {request_id} not found")

        if request.status != AgentRequestStatus.PENDING:
            raise ValueError(f"Request {request_id} is not pending")

        # Update status
        request.status = AgentRequestStatus.APPROVED
        request.responded_at = datetime.now(UTC).isoformat()
        request.responded_by = approved_by
        if reason:
            request.context["approval_reason"] = reason
        if modifications:
            request.context["modifications"] = modifications

        logger.info(
            "Approved agent request",
            extra={
                "request_id": request_id,
                "approved_by": approved_by,
            },
        )

        return request

    async def reject(
        self,
        request_id: str,
        rejected_by: str,
        reason: str,
    ) -> AgentRequest:
        """
        Reject a pending request.

        Args:
            request_id: The request ID.
            rejected_by: Who is rejecting.
            reason: Rejection reason.

        Returns:
            The updated request.

        Raises:
            KeyError: If request not found.
            ValueError: If request is not pending.
        """
        request = self._requests.get(request_id)
        if request is None:
            raise KeyError(f"Request {request_id} not found")

        if request.status != AgentRequestStatus.PENDING:
            raise ValueError(f"Request {request_id} is not pending")

        # Update status
        request.status = AgentRequestStatus.REJECTED
        request.responded_at = datetime.now(UTC).isoformat()
        request.responded_by = rejected_by
        request.context["rejection_reason"] = reason

        logger.info(
            "Rejected agent request",
            extra={
                "request_id": request_id,
                "rejected_by": rejected_by,
                "reason": reason,
            },
        )

        return request

    async def respond(
        self,
        request_id: str,
        responded_by: str,
        response_type: ClarificationType,
        value: str | None = None,
        selected_option_id: str | None = None,
        confirmed: bool | None = None,
    ) -> AgentRequest:
        """
        Respond to a clarification request.

        Args:
            request_id: The request ID.
            responded_by: Who is responding.
            response_type: Type of response.
            value: Text value (for TEXT type).
            selected_option_id: Selected option (for CHOICE type).
            confirmed: Confirmation result (for CONFIRMATION type).

        Returns:
            The updated request.

        Raises:
            KeyError: If request not found.
            ValueError: If request is not pending or wrong type.
        """
        request = self._requests.get(request_id)
        if request is None:
            raise KeyError(f"Request {request_id} not found")

        if request.status != AgentRequestStatus.PENDING:
            raise ValueError(f"Request {request_id} is not pending")

        if request.request_type != AgentRequestType.CLARIFICATION:
            raise ValueError(f"Request {request_id} is not a clarification request")

        # Update status
        request.status = AgentRequestStatus.RESPONDED
        request.responded_at = datetime.now(UTC).isoformat()
        request.responded_by = responded_by

        # Store response in context
        request.context["response"] = {
            "response_type": response_type.value,
            "value": value,
            "selected_option_id": selected_option_id,
            "confirmed": confirmed,
        }

        logger.info(
            "Responded to clarification request",
            extra={
                "request_id": request_id,
                "responded_by": responded_by,
                "response_type": response_type,
            },
        )

        return request

    def add_request(self, request: AgentRequest) -> None:
        """
        Add a request directly to the queue (for testing or manual queueing).

        Args:
            request: The agent request to add.
        """
        self._requests[request.request_id] = request
        logger.debug(f"Added request {request.request_id} to queue")

    def batch_approve(
        self,
        request_ids: list[str],
        approved_by: str,
        reason: str | None = None,
    ) -> list[BatchApprovalResult]:
        """
        Approve multiple requests at once.

        Args:
            request_ids: List of request IDs to approve.
            approved_by: Who is approving.
            reason: Optional common reason for all approvals.

        Returns:
            List of results for each request.
        """
        if not request_ids:
            return []

        results: list[BatchApprovalResult] = []

        for request_id in request_ids:
            request = self._requests.get(request_id)

            if request is None:
                results.append(
                    BatchApprovalResult(
                        request_id=request_id,
                        status=None,
                        success=False,
                        message=f"Request {request_id} not found",
                        error_code="NOT_FOUND",
                    )
                )
                continue

            if request.status != AgentRequestStatus.PENDING:
                results.append(
                    BatchApprovalResult(
                        request_id=request_id,
                        status=request.status,
                        success=False,
                        message=f"Request {request_id} is not pending",
                        error_code="NOT_PENDING",
                    )
                )
                continue

            # Approve the request
            request.status = AgentRequestStatus.APPROVED
            request.responded_at = datetime.now(UTC).isoformat()
            request.responded_by = approved_by
            if reason:
                request.context["approval_reason"] = reason
            request.context["batch_approved"] = True

            results.append(
                BatchApprovalResult(
                    request_id=request_id,
                    status=AgentRequestStatus.APPROVED,
                    success=True,
                    message="Request approved successfully",
                )
            )

            logger.info(
                "Batch approved agent request",
                extra={
                    "request_id": request_id,
                    "approved_by": approved_by,
                    "batch_operation": True,
                },
            )

        return results

    def batch_reject(
        self,
        request_ids: list[str],
        rejected_by: str,
        reason: str | None = None,
    ) -> list[BatchApprovalResult]:
        """
        Reject multiple requests at once.

        Args:
            request_ids: List of request IDs to reject.
            rejected_by: Who is rejecting.
            reason: Optional common reason for all rejections.

        Returns:
            List of results for each request.
        """
        if not request_ids:
            return []

        results: list[BatchApprovalResult] = []

        for request_id in request_ids:
            request = self._requests.get(request_id)

            if request is None:
                results.append(
                    BatchApprovalResult(
                        request_id=request_id,
                        status=None,
                        success=False,
                        message=f"Request {request_id} not found",
                        error_code="NOT_FOUND",
                    )
                )
                continue

            if request.status != AgentRequestStatus.PENDING:
                results.append(
                    BatchApprovalResult(
                        request_id=request_id,
                        status=request.status,
                        success=False,
                        message=f"Request {request_id} is not pending",
                        error_code="NOT_PENDING",
                    )
                )
                continue

            # Reject the request
            request.status = AgentRequestStatus.REJECTED
            request.responded_at = datetime.now(UTC).isoformat()
            request.responded_by = rejected_by
            if reason:
                request.context["rejection_reason"] = reason
            request.context["batch_rejected"] = True

            results.append(
                BatchApprovalResult(
                    request_id=request_id,
                    status=AgentRequestStatus.REJECTED,
                    success=True,
                    message="Request rejected successfully",
                )
            )

            logger.info(
                "Batch rejected agent request",
                extra={
                    "request_id": request_id,
                    "rejected_by": rejected_by,
                    "reason": reason,
                    "batch_operation": True,
                },
            )

        return results


# Global queue instance (in production, use Redis or database)
_agent_request_queue: AgentRequestQueue | None = None


def get_agent_request_queue() -> AgentRequestQueue:
    """
    Get the global agent request queue instance.

    Returns:
        AgentRequestQueue instance.
    """
    global _agent_request_queue
    if _agent_request_queue is None:
        _agent_request_queue = AgentRequestQueue()
    return _agent_request_queue


def set_agent_request_queue(queue: AgentRequestQueue | None) -> None:
    """
    Set the global agent request queue (for testing).

    Args:
        queue: Queue instance to use, or None to reset.
    """
    global _agent_request_queue
    _agent_request_queue = queue


# Type alias for queue dependency
AgentRequestQueueDepends = Annotated[AgentRequestQueue, Depends(get_agent_request_queue)]


# =========================================================================
# Authorization
# =========================================================================


def require_reviewer_role(current_user: dict[str, Any]) -> None:
    """
    Require admin or hitl_reviewer role for agent request operations.

    SECURITY: Protects critical HITL decisions from unauthorized access.
    Only admins and HITL reviewers can approve/reject agent requests.

    Args:
        current_user: Authenticated user from get_current_user dependency.

    Raises:
        HTTPException: 403 if user lacks required role.
    """
    roles = current_user.get("roles", [])
    if "admin" not in roles and "hitl_reviewer" not in roles:
        logger.warning(
            "Unauthorized agent request access attempt",
            extra={
                "user_id": current_user.get("user_id"),
                "username": current_user.get("username"),
                "roles": roles,
            },
        )
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Admin or HITL reviewer role required for agent request operations",
        )


# =========================================================================
# Audit Logging
# =========================================================================


async def log_agent_request_audit_event(
    audit_service: UnifiedAuditService | None,
    event_type: AuditEventType,
    request_id: str,
    session_id: str,
    user_id: str,
    username: str,
    action: str,
    details: dict[str, Any] | None = None,
) -> None:
    """
    Log an agent request audit event for compliance tracking.

    Args:
        audit_service: The audit service (may be None if not configured).
        event_type: The type of audit event.
        request_id: The request ID being acted upon.
        session_id: The associated session ID.
        user_id: ID of the user performing the action.
        username: Username of the user performing the action.
        action: Description of the action.
        details: Additional details about the action.
    """
    if audit_service is None:
        logger.debug("Audit service not configured, skipping audit log")
        return

    try:
        event = UnifiedAuditEvent(
            category=AuditEventCategory.SYSTEM,
            event_type=event_type,
            actor=AuditActor(
                actor_id=user_id,
                actor_type="user",
                username=username,
            ),
            resource_type="agent_request",
            resource_id=request_id,
            action=action,
            outcome="success",
            context=AuditContext(
                request_id=f"agent-request-{request_id}",
            ),
            details={
                "session_id": session_id,
                **(details or {}),
            },
        )
        await audit_service.log_event(event)
        logger.debug(f"Logged agent request audit event: {event_type} for {request_id}")
    except Exception as e:
        # Audit logging should not fail the main operation
        logger.warning(f"Failed to log agent request audit event: {e}")


# =========================================================================
# Router and Endpoints
# =========================================================================

agent_request_router = APIRouter(prefix="/agents/requests", tags=["agents"])


@agent_request_router.get(
    "/pending",
    response_model=PendingAgentRequestsResponse,
    summary="List pending agent requests",
    description="Get all agent requests waiting for human response. Requires authentication.",
)
async def list_pending_agent_requests(
    current_user: CurrentUser,
    queue: AgentRequestQueueDepends,
    session_id: str | None = Query(default=None, description="Filter by session ID"),
) -> PendingAgentRequestsResponse:
    """
    List all pending agent HITL requests.

    Returns requests that are awaiting human approval or clarification.
    """
    require_reviewer_role(current_user)
    pending = await queue.list_pending(session_id=session_id)
    return PendingAgentRequestsResponse(
        requests=pending,
        count=len(pending),
    )


@agent_request_router.get(
    "/{request_id}",
    response_model=AgentRequest,
    summary="Get agent request details",
    description="Get details of a specific agent request.",
)
async def get_agent_request(
    request_id: str,
    current_user: CurrentUser,
    queue: AgentRequestQueueDepends,
) -> AgentRequest:
    """
    Get details of a specific agent request by ID.
    """
    request = await queue.get_request(request_id)
    if request is None:
        raise HTTPException(
            status_code=404,
            detail=f"Agent request {request_id} not found",
        )
    return request


@agent_request_router.post(
    "/{request_id}/approve",
    response_model=AgentRequestActionResponse,
    summary="Approve an agent request",
    description="Approve a pending agent request. Requires admin or hitl_reviewer role.",
)
async def approve_agent_request(
    request_id: str,
    request: ApproveAgentRequest,
    current_user: CurrentUser,
    audit_service: AuditService,
    queue: AgentRequestQueueDepends,
) -> AgentRequestActionResponse:
    """
    Approve a pending agent request.

    Once approved, the agent execution can proceed.
    Requires admin or hitl_reviewer role.
    """
    require_reviewer_role(current_user)
    try:
        result = await queue.approve(
            request_id=request_id,
            approved_by=request.approved_by,
            reason=request.reason,
            modifications=request.modifications,
        )

        # Log audit event for compliance
        await log_agent_request_audit_event(
            audit_service=audit_service,
            event_type=AuditEventType.AGENT_REQUEST_APPROVED,
            request_id=request_id,
            session_id=result.session_id,
            user_id=current_user.get("user_id", "unknown"),
            username=current_user.get("username", request.approved_by),
            action=f"Approved agent request for {result.agent_name}",
            details={
                "approved_by": request.approved_by,
                "reason": request.reason,
                "confidence": result.confidence,
                "threshold": result.threshold,
            },
        )

        return AgentRequestActionResponse(
            request_id=request_id,
            status=result.status,
            message=f"Agent request approved by {request.approved_by}",
            resumed=True,
        )
    except KeyError:
        raise HTTPException(
            status_code=404,
            detail=f"Agent request {request_id} not found",
        )
    except ValueError as e:
        raise HTTPException(
            status_code=400,
            detail=str(e),
        )


@agent_request_router.post(
    "/{request_id}/reject",
    response_model=AgentRequestActionResponse,
    summary="Reject an agent request",
    description="Reject a pending agent request. Requires admin or hitl_reviewer role.",
)
async def reject_agent_request(
    request_id: str,
    request: RejectAgentRequest,
    current_user: CurrentUser,
    audit_service: AuditService,
    queue: AgentRequestQueueDepends,
) -> AgentRequestActionResponse:
    """
    Reject a pending agent request.

    The agent action will not be executed.
    Requires admin or hitl_reviewer role.
    """
    require_reviewer_role(current_user)
    try:
        result = await queue.reject(
            request_id=request_id,
            rejected_by=request.rejected_by,
            reason=request.reason,
        )

        # Log audit event for compliance
        await log_agent_request_audit_event(
            audit_service=audit_service,
            event_type=AuditEventType.AGENT_REQUEST_REJECTED,
            request_id=request_id,
            session_id=result.session_id,
            user_id=current_user.get("user_id", "unknown"),
            username=current_user.get("username", request.rejected_by),
            action=f"Rejected agent request for {result.agent_name}",
            details={
                "rejected_by": request.rejected_by,
                "reason": request.reason,
                "confidence": result.confidence,
                "threshold": result.threshold,
            },
        )

        return AgentRequestActionResponse(
            request_id=request_id,
            status=result.status,
            message=f"Agent request rejected by {request.rejected_by}",
            resumed=False,
        )
    except KeyError:
        raise HTTPException(
            status_code=404,
            detail=f"Agent request {request_id} not found",
        )
    except ValueError as e:
        raise HTTPException(
            status_code=400,
            detail=str(e),
        )


@agent_request_router.post(
    "/{request_id}/respond",
    response_model=AgentRequestActionResponse,
    summary="Respond to a clarification request",
    description="Respond to a pending clarification request.",
)
async def respond_to_agent_request(
    request_id: str,
    request: ClarificationResponseRequest,
    current_user: CurrentUser,
    audit_service: AuditService,
    queue: AgentRequestQueueDepends,
) -> AgentRequestActionResponse:
    """
    Respond to a pending clarification request.

    Provides the information the agent needs to proceed.
    """
    try:
        result = await queue.respond(
            request_id=request_id,
            responded_by=request.responded_by,
            response_type=request.response_type,
            value=request.value,
            selected_option_id=request.selected_option_id,
            confirmed=request.confirmed,
        )

        # Log audit event for compliance
        await log_agent_request_audit_event(
            audit_service=audit_service,
            event_type=AuditEventType.AGENT_REQUEST_RESPONDED,
            request_id=request_id,
            session_id=result.session_id,
            user_id=current_user.get("user_id", "unknown"),
            username=current_user.get("username", request.responded_by),
            action=f"Responded to clarification from {result.agent_name}",
            details={
                "responded_by": request.responded_by,
                "response_type": request.response_type.value,
            },
        )

        return AgentRequestActionResponse(
            request_id=request_id,
            status=result.status,
            message=f"Clarification provided by {request.responded_by}",
            resumed=True,
        )
    except KeyError:
        raise HTTPException(
            status_code=404,
            detail=f"Agent request {request_id} not found",
        )
    except ValueError as e:
        raise HTTPException(
            status_code=400,
            detail=str(e),
        )


# =========================================================================
# Batch Approval Endpoints
# =========================================================================


@agent_request_router.post(
    "/batch/approve",
    response_model=BatchApprovalResponse,
    summary="Batch approve agent requests",
    description="Approve multiple pending agent requests at once. Requires admin or hitl_reviewer role.",
)
async def batch_approve_requests(
    batch_request: BatchApproveRequest,
    current_user: CurrentUser,
    audit_service: AuditService,
    queue: AgentRequestQueueDepends,
) -> BatchApprovalResponse:
    """
    Approve multiple agent requests in a single operation.

    Useful for quickly approving similar low-risk requests.
    Requires admin or hitl_reviewer role.
    """
    require_reviewer_role(current_user)

    approved_by: str = str(current_user.get("username") or current_user.get("sub") or "unknown")

    results = queue.batch_approve(
        request_ids=batch_request.request_ids,
        approved_by=approved_by,
        reason=batch_request.reason,
    )

    # Log audit events for successful approvals
    for result in results:
        if result.success:
            # Get the original request for audit details
            original_request = await queue.get_request(result.request_id)
            if original_request:
                await log_agent_request_audit_event(
                    audit_service=audit_service,
                    event_type=AuditEventType.AGENT_REQUEST_APPROVED,
                    request_id=result.request_id,
                    session_id=original_request.session_id,
                    user_id=str(current_user.get("user_id") or "unknown"),
                    username=approved_by,
                    action=f"Batch approved agent request for {original_request.agent_name}",
                    details={
                        "approved_by": approved_by,
                        "reason": batch_request.reason,
                        "confidence": original_request.confidence,
                        "threshold": original_request.threshold,
                        "batch_operation": True,
                    },
                )

    succeeded = sum(1 for r in results if r.success)
    failed = len(results) - succeeded

    return BatchApprovalResponse(
        results=results,
        succeeded=succeeded,
        failed=failed,
    )


@agent_request_router.post(
    "/batch/reject",
    response_model=BatchApprovalResponse,
    summary="Batch reject agent requests",
    description="Reject multiple pending agent requests at once. Requires admin or hitl_reviewer role.",
)
async def batch_reject_requests(
    batch_request: BatchRejectRequest,
    current_user: CurrentUser,
    audit_service: AuditService,
    queue: AgentRequestQueueDepends,
) -> BatchApprovalResponse:
    """
    Reject multiple agent requests in a single operation.

    Useful for quickly rejecting a batch of problematic requests.
    Requires admin or hitl_reviewer role.
    """
    require_reviewer_role(current_user)

    rejected_by: str = str(current_user.get("username") or current_user.get("sub") or "unknown")

    results = queue.batch_reject(
        request_ids=batch_request.request_ids,
        rejected_by=rejected_by,
        reason=batch_request.reason,
    )

    # Log audit events for successful rejections
    for result in results:
        if result.success:
            original_request = await queue.get_request(result.request_id)
            if original_request:
                await log_agent_request_audit_event(
                    audit_service=audit_service,
                    event_type=AuditEventType.AGENT_REQUEST_REJECTED,
                    request_id=result.request_id,
                    session_id=original_request.session_id,
                    user_id=str(current_user.get("user_id") or "unknown"),
                    username=rejected_by,
                    action=f"Batch rejected agent request for {original_request.agent_name}",
                    details={
                        "rejected_by": rejected_by,
                        "reason": batch_request.reason,
                        "confidence": original_request.confidence,
                        "threshold": original_request.threshold,
                        "batch_operation": True,
                    },
                )

    succeeded = sum(1 for r in results if r.success)
    failed = len(results) - succeeded

    return BatchApprovalResponse(
        results=results,
        succeeded=succeeded,
        failed=failed,
    )


# =========================================================================
# Rotating Threshold Storage (In-Memory for now)
# =========================================================================

# In-memory storage for approval history per user
_approval_history: dict[str, list[ApprovalHistory]] = {}

# In-memory storage for user threshold settings
_user_threshold_settings: dict[str, UserThresholdSettings] = {}


def get_user_approval_history(user_id: str) -> list[ApprovalHistory]:
    """Get approval history for a user."""
    return _approval_history.get(user_id, [])


def add_approval_history_entry(entry: ApprovalHistory) -> None:
    """Add an entry to approval history."""
    if entry.user_id not in _approval_history:
        _approval_history[entry.user_id] = []
    _approval_history[entry.user_id].append(entry)
    # Keep only last 500 entries per user
    if len(_approval_history[entry.user_id]) > 500:
        _approval_history[entry.user_id] = _approval_history[entry.user_id][-500:]


def get_user_threshold_settings(user_id: str) -> UserThresholdSettings | None:
    """Get threshold settings for a user."""
    return _user_threshold_settings.get(user_id)


def set_user_threshold_settings(settings: UserThresholdSettings) -> None:
    """Set threshold settings for a user."""
    _user_threshold_settings[settings.user_id] = settings


# =========================================================================
# Threshold Endpoints
# =========================================================================


@agent_request_router.get(
    "/threshold/recommendation",
    response_model=ThresholdRecommendation,
    summary="Get threshold recommendation",
    description="Get personalized threshold recommendation based on approval history.",
)
async def get_threshold_recommendation(
    current_user: CurrentUser,
) -> ThresholdRecommendation:
    """
    Get threshold recommendation for the current user.

    Analyzes the user's approval history to suggest an optimal
    confidence threshold that balances automation with oversight.
    """
    user_id: str = str(current_user.get("user_id") or current_user.get("sub") or "unknown")

    # Get user's current settings or defaults
    settings = get_user_threshold_settings(user_id)
    base_threshold = settings.base_threshold if settings else 0.7
    min_threshold = settings.min_threshold if settings else 0.5
    max_threshold = settings.max_threshold if settings else 0.9

    # Get approval history
    history = get_user_approval_history(user_id)

    # Calculate recommendation
    calculator = ThresholdCalculator(
        base_threshold=base_threshold,
        min_threshold=min_threshold,
        max_threshold=max_threshold,
    )

    return calculator.calculate_recommendation(history)


@agent_request_router.get(
    "/threshold/settings",
    response_model=UserThresholdSettings,
    summary="Get user threshold settings",
    description="Get the current user's threshold configuration.",
)
async def get_user_threshold_settings_endpoint(
    current_user: CurrentUser,
) -> UserThresholdSettings:
    """
    Get the current user's threshold settings.

    Returns current threshold configuration including base threshold,
    adjusted threshold, and adjustment bounds.
    """
    user_id: str = str(current_user.get("user_id") or current_user.get("sub") or "unknown")

    settings = get_user_threshold_settings(user_id)
    if settings is None:
        # Return default settings
        return UserThresholdSettings(
            user_id=user_id,
            base_threshold=0.7,
            adjusted_threshold=0.7,
            auto_adjust_enabled=True,
            min_threshold=0.5,
            max_threshold=0.9,
        )

    return settings


class UpdateThresholdSettingsRequest(BaseModel):
    """Request body for updating threshold settings."""

    base_threshold: float | None = Field(
        default=None,
        description="New base threshold",
        ge=0.0,
        le=1.0,
    )
    auto_adjust_enabled: bool | None = Field(
        default=None,
        description="Enable/disable auto-adjustment",
    )
    min_threshold: float | None = Field(
        default=None,
        description="Minimum allowed threshold",
        ge=0.0,
        le=1.0,
    )
    max_threshold: float | None = Field(
        default=None,
        description="Maximum allowed threshold",
        ge=0.0,
        le=1.0,
    )


@agent_request_router.put(
    "/threshold/settings",
    response_model=UserThresholdSettings,
    summary="Update user threshold settings",
    description="Update the current user's threshold configuration.",
)
async def update_user_threshold_settings_endpoint(
    request: UpdateThresholdSettingsRequest,
    current_user: CurrentUser,
) -> UserThresholdSettings:
    """
    Update the current user's threshold settings.

    Allows customization of threshold behavior including base value,
    auto-adjustment, and bounds.
    """
    user_id: str = str(current_user.get("user_id") or current_user.get("sub") or "unknown")

    # Get existing settings or create defaults
    settings = get_user_threshold_settings(user_id)
    if settings is None:
        settings = UserThresholdSettings(
            user_id=user_id,
            base_threshold=0.7,
            adjusted_threshold=0.7,
            auto_adjust_enabled=True,
            min_threshold=0.5,
            max_threshold=0.9,
        )

    # Apply updates
    if request.base_threshold is not None:
        settings.base_threshold = request.base_threshold
        settings.adjusted_threshold = request.base_threshold

    if request.auto_adjust_enabled is not None:
        settings.auto_adjust_enabled = request.auto_adjust_enabled

    if request.min_threshold is not None:
        settings.min_threshold = request.min_threshold

    if request.max_threshold is not None:
        settings.max_threshold = request.max_threshold

    # Validate bounds
    if settings.min_threshold > settings.max_threshold:
        raise HTTPException(
            status_code=400,
            detail="min_threshold cannot exceed max_threshold",
        )

    if settings.base_threshold < settings.min_threshold:
        settings.base_threshold = settings.min_threshold
        settings.adjusted_threshold = settings.min_threshold

    if settings.base_threshold > settings.max_threshold:
        settings.base_threshold = settings.max_threshold
        settings.adjusted_threshold = settings.max_threshold

    # Save settings
    set_user_threshold_settings(settings)

    logger.info(
        "Updated user threshold settings",
        extra={
            "user_id": user_id,
            "base_threshold": settings.base_threshold,
            "auto_adjust_enabled": settings.auto_adjust_enabled,
        },
    )

    return settings


# Expose the global queue for testing
_request_queue = get_agent_request_queue()
