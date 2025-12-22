"""
Remediation Approval Queue API Unit Tests.

Tests for the remediation approval REST API following TDD methodology.
This API manages pending remediations from alerts that require human approval.

Features tested:
- List pending remediations
- Approve remediation actions
- Reject remediation actions
- Get remediation history
- Integration with AIRecommendation

Reference: ADR-0026 - Comprehensive Client Resilience Patterns
"""

from __future__ import annotations

import gc
from datetime import UTC, datetime
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from mcp_server_langgraph.core.interrupts.approval import ApprovalStatus

pytestmark = [
    pytest.mark.unit,
    pytest.mark.api,
    pytest.mark.alerts,
]


@pytest.mark.xdist_group(name="test_remediation_approvals")
class TestRemediationApprovalRouter:
    """Tests for remediation approval router existence."""

    def teardown_method(self) -> None:
        """Force GC to prevent mock accumulation in xdist workers."""
        gc.collect()

    def test_remediation_approval_router_exists(self) -> None:
        """
        GIVEN the remediation approval module
        WHEN importing the router
        THEN should export remediation_approval_router.
        """
        from mcp_server_langgraph.api.v1.remediation_approvals import (
            remediation_approval_router,
        )

        assert remediation_approval_router is not None

    def test_list_pending_endpoint_exists(self) -> None:
        """
        GIVEN the remediation approval router
        WHEN checking routes
        THEN should have GET /remediations/pending endpoint.
        """
        from mcp_server_langgraph.api.v1.remediation_approvals import (
            remediation_approval_router,
        )

        routes = [r for r in remediation_approval_router.routes]
        pending_routes = [
            r for r in routes if hasattr(r, "path") and "pending" in r.path
        ]
        assert len(pending_routes) > 0, "Should have /remediations/pending route"

    def test_approve_endpoint_exists(self) -> None:
        """
        GIVEN the remediation approval router
        WHEN checking routes
        THEN should have POST /remediations/{id}/approve endpoint.
        """
        from mcp_server_langgraph.api.v1.remediation_approvals import (
            remediation_approval_router,
        )

        routes = [r for r in remediation_approval_router.routes]
        approve_routes = [
            r for r in routes if hasattr(r, "path") and "approve" in r.path
        ]
        assert len(approve_routes) > 0, "Should have approve route"

    def test_reject_endpoint_exists(self) -> None:
        """
        GIVEN the remediation approval router
        WHEN checking routes
        THEN should have POST /remediations/{id}/reject endpoint.
        """
        from mcp_server_langgraph.api.v1.remediation_approvals import (
            remediation_approval_router,
        )

        routes = [r for r in remediation_approval_router.routes]
        reject_routes = [
            r for r in routes if hasattr(r, "path") and "reject" in r.path
        ]
        assert len(reject_routes) > 0, "Should have reject route"


@pytest.mark.xdist_group(name="test_remediation_approvals")
class TestRemediationRequestModel:
    """Tests for remediation request data model."""

    def teardown_method(self) -> None:
        """Force GC to prevent mock accumulation in xdist workers."""
        gc.collect()

    def test_remediation_request_model_exists(self) -> None:
        """
        GIVEN the remediation approvals module
        WHEN importing RemediationRequest model
        THEN should be a valid Pydantic model.
        """
        from mcp_server_langgraph.api.v1.remediation_approvals import (
            RemediationRequest,
        )

        assert RemediationRequest is not None

    def test_remediation_request_fields(self) -> None:
        """
        GIVEN a RemediationRequest model
        WHEN creating instance
        THEN should have all expected fields.
        """
        from mcp_server_langgraph.api.v1.remediation_approvals import (
            RemediationRequest,
        )

        request = RemediationRequest(
            remediation_id="rem-001",
            alert_id="alert-001",
            alert_name="CircuitBreakerOpen",
            severity="critical",
            step_number=1,
            action="restart",
            description="Restart Redis pods",
            command="kubectl rollout restart statefulset/redis",
            risk_level="medium",
            status=ApprovalStatus.PENDING,
            requested_at=datetime.now(UTC).isoformat(),
        )

        assert request.remediation_id == "rem-001"
        assert request.alert_id == "alert-001"
        assert request.status == ApprovalStatus.PENDING


@pytest.mark.xdist_group(name="test_remediation_approvals")
class TestRemediationApprovalQueue:
    """Tests for remediation approval queue service."""

    def teardown_method(self) -> None:
        """Force GC to prevent mock accumulation in xdist workers."""
        gc.collect()

    def test_approval_queue_class_exists(self) -> None:
        """
        GIVEN the remediation approvals module
        WHEN importing RemediationApprovalQueue
        THEN should export the queue class.
        """
        from mcp_server_langgraph.alerts.approval_queue import (
            RemediationApprovalQueue,
        )

        assert RemediationApprovalQueue is not None

    @pytest.mark.asyncio
    async def test_queue_remediation_creates_pending(self) -> None:
        """
        GIVEN a RemediationApprovalQueue
        WHEN queueing a remediation
        THEN should add to pending queue.
        """
        from mcp_server_langgraph.alerts.approval_queue import (
            RemediationApprovalQueue,
        )
        from mcp_server_langgraph.alerts.ai_recommendation import AIRecommendation

        queue = RemediationApprovalQueue()

        recommendation = AIRecommendation(
            recommendation_id="rec-001",
            alert_id="alert-001",
            root_cause_analysis="Test",
            remediation_steps=[
                {
                    "step_number": 1,
                    "action": "restart",
                    "description": "Restart pods",
                    "command": "kubectl rollout restart",
                    "requires_approval": True,
                    "risk_level": "medium",
                }
            ],
            risk_assessment={},
            generated_at=datetime.now(UTC).isoformat(),
            model_used="test-model",
        )

        await queue.queue_remediation(
            alert_id="alert-001",
            alert_name="TestAlert",
            severity="critical",
            recommendation=recommendation,
        )

        pending = await queue.list_pending()
        assert len(pending) == 1

    @pytest.mark.asyncio
    async def test_approve_remediation_changes_status(self) -> None:
        """
        GIVEN a pending remediation
        WHEN approving the remediation
        THEN should change status to approved.
        """
        from mcp_server_langgraph.alerts.approval_queue import (
            RemediationApprovalQueue,
        )
        from mcp_server_langgraph.alerts.ai_recommendation import AIRecommendation

        queue = RemediationApprovalQueue()

        recommendation = AIRecommendation(
            recommendation_id="rec-001",
            alert_id="alert-001",
            root_cause_analysis="Test",
            remediation_steps=[
                {
                    "step_number": 1,
                    "action": "restart",
                    "description": "Restart pods",
                    "requires_approval": True,
                    "risk_level": "medium",
                }
            ],
            risk_assessment={},
            generated_at=datetime.now(UTC).isoformat(),
            model_used="test-model",
        )

        await queue.queue_remediation(
            alert_id="alert-001",
            alert_name="TestAlert",
            severity="critical",
            recommendation=recommendation,
        )

        pending = await queue.list_pending()
        remediation_id = pending[0].remediation_id

        result = await queue.approve(
            remediation_id=remediation_id,
            approved_by="admin@example.com",
        )

        assert result.status == ApprovalStatus.APPROVED

    @pytest.mark.asyncio
    async def test_reject_remediation_changes_status(self) -> None:
        """
        GIVEN a pending remediation
        WHEN rejecting the remediation
        THEN should change status to rejected.
        """
        from mcp_server_langgraph.alerts.approval_queue import (
            RemediationApprovalQueue,
        )
        from mcp_server_langgraph.alerts.ai_recommendation import AIRecommendation

        queue = RemediationApprovalQueue()

        recommendation = AIRecommendation(
            recommendation_id="rec-001",
            alert_id="alert-001",
            root_cause_analysis="Test",
            remediation_steps=[
                {
                    "step_number": 1,
                    "action": "restart",
                    "description": "Restart pods",
                    "requires_approval": True,
                    "risk_level": "medium",
                }
            ],
            risk_assessment={},
            generated_at=datetime.now(UTC).isoformat(),
            model_used="test-model",
        )

        await queue.queue_remediation(
            alert_id="alert-001",
            alert_name="TestAlert",
            severity="critical",
            recommendation=recommendation,
        )

        pending = await queue.list_pending()
        remediation_id = pending[0].remediation_id

        result = await queue.reject(
            remediation_id=remediation_id,
            rejected_by="admin@example.com",
            reason="Not safe to proceed",
        )

        assert result.status == ApprovalStatus.REJECTED

    @pytest.mark.asyncio
    async def test_list_pending_excludes_completed(self) -> None:
        """
        GIVEN remediations with different statuses
        WHEN listing pending
        THEN should only return pending remediations.
        """
        from mcp_server_langgraph.alerts.approval_queue import (
            RemediationApprovalQueue,
        )
        from mcp_server_langgraph.alerts.ai_recommendation import AIRecommendation

        queue = RemediationApprovalQueue()

        recommendation = AIRecommendation(
            recommendation_id="rec-001",
            alert_id="alert-001",
            root_cause_analysis="Test",
            remediation_steps=[
                {
                    "step_number": 1,
                    "action": "restart",
                    "description": "Restart pods",
                    "requires_approval": True,
                    "risk_level": "medium",
                }
            ],
            risk_assessment={},
            generated_at=datetime.now(UTC).isoformat(),
            model_used="test-model",
        )

        # Queue two remediations
        await queue.queue_remediation(
            alert_id="alert-001",
            alert_name="TestAlert1",
            severity="critical",
            recommendation=recommendation,
        )
        await queue.queue_remediation(
            alert_id="alert-002",
            alert_name="TestAlert2",
            severity="warning",
            recommendation=recommendation,
        )

        pending = await queue.list_pending()
        assert len(pending) == 2

        # Approve one
        await queue.approve(
            remediation_id=pending[0].remediation_id,
            approved_by="admin@example.com",
        )

        # Should only return one pending now
        pending_after = await queue.list_pending()
        assert len(pending_after) == 1


@pytest.mark.xdist_group(name="test_remediation_approvals")
class TestRemediationApprovalHistory:
    """Tests for remediation approval history."""

    def teardown_method(self) -> None:
        """Force GC to prevent mock accumulation in xdist workers."""
        gc.collect()

    @pytest.mark.asyncio
    async def test_get_history_returns_completed(self) -> None:
        """
        GIVEN completed remediations
        WHEN getting history
        THEN should return approved and rejected remediations.
        """
        from mcp_server_langgraph.alerts.approval_queue import (
            RemediationApprovalQueue,
        )
        from mcp_server_langgraph.alerts.ai_recommendation import AIRecommendation

        queue = RemediationApprovalQueue()

        recommendation = AIRecommendation(
            recommendation_id="rec-001",
            alert_id="alert-001",
            root_cause_analysis="Test",
            remediation_steps=[
                {
                    "step_number": 1,
                    "action": "restart",
                    "description": "Restart pods",
                    "requires_approval": True,
                    "risk_level": "medium",
                }
            ],
            risk_assessment={},
            generated_at=datetime.now(UTC).isoformat(),
            model_used="test-model",
        )

        # Queue and approve
        await queue.queue_remediation(
            alert_id="alert-001",
            alert_name="TestAlert",
            severity="critical",
            recommendation=recommendation,
        )

        pending = await queue.list_pending()
        await queue.approve(
            remediation_id=pending[0].remediation_id,
            approved_by="admin@example.com",
        )

        # History should contain the approved one
        history = await queue.get_history(limit=10)
        assert len(history) == 1
        assert history[0].status == ApprovalStatus.APPROVED

    @pytest.mark.asyncio
    async def test_get_history_with_limit(self) -> None:
        """
        GIVEN multiple completed remediations
        WHEN getting history with limit
        THEN should return limited results.
        """
        from mcp_server_langgraph.alerts.approval_queue import (
            RemediationApprovalQueue,
        )
        from mcp_server_langgraph.alerts.ai_recommendation import AIRecommendation

        queue = RemediationApprovalQueue()

        recommendation = AIRecommendation(
            recommendation_id="rec-001",
            alert_id="alert-001",
            root_cause_analysis="Test",
            remediation_steps=[
                {
                    "step_number": 1,
                    "action": "restart",
                    "description": "Restart pods",
                    "requires_approval": True,
                    "risk_level": "medium",
                }
            ],
            risk_assessment={},
            generated_at=datetime.now(UTC).isoformat(),
            model_used="test-model",
        )

        # Queue and approve multiple
        for i in range(5):
            await queue.queue_remediation(
                alert_id=f"alert-{i}",
                alert_name=f"TestAlert{i}",
                severity="critical",
                recommendation=recommendation,
            )

        pending = await queue.list_pending()
        for p in pending:
            await queue.approve(
                remediation_id=p.remediation_id,
                approved_by="admin@example.com",
            )

        # Get limited history
        history = await queue.get_history(limit=3)
        assert len(history) == 3


@pytest.mark.xdist_group(name="test_remediation_approvals")
class TestRemediationApprovalAuthorization:
    """Tests for admin authorization on remediation endpoints.

    All remediation approval endpoints require admin or compliance_officer role.
    This prevents unauthorized users from approving/rejecting critical
    remediation actions.
    """

    def teardown_method(self) -> None:
        """Force GC to prevent mock accumulation in xdist workers."""
        gc.collect()

    def test_require_admin_role_function_exists(self) -> None:
        """
        GIVEN the remediation approvals module
        WHEN importing require_admin_role
        THEN should export the authorization helper.
        """
        from mcp_server_langgraph.api.v1.remediation_approvals import (
            require_admin_role,
        )

        assert require_admin_role is not None
        assert callable(require_admin_role)

    def test_require_admin_role_allows_admin(self) -> None:
        """
        GIVEN a user with admin role
        WHEN checking authorization
        THEN should allow access (no exception).
        """
        from mcp_server_langgraph.api.v1.remediation_approvals import (
            require_admin_role,
        )

        admin_user = {
            "user_id": "admin-123",
            "username": "admin@example.com",
            "roles": ["admin"],
        }

        # Should not raise
        require_admin_role(admin_user)

    def test_require_admin_role_allows_compliance_officer(self) -> None:
        """
        GIVEN a user with compliance_officer role
        WHEN checking authorization
        THEN should allow access (no exception).
        """
        from mcp_server_langgraph.api.v1.remediation_approvals import (
            require_admin_role,
        )

        compliance_user = {
            "user_id": "co-456",
            "username": "compliance@example.com",
            "roles": ["compliance_officer"],
        }

        # Should not raise
        require_admin_role(compliance_user)

    def test_require_admin_role_denies_regular_user(self) -> None:
        """
        GIVEN a user without admin or compliance_officer role
        WHEN checking authorization
        THEN should raise HTTPException with 403 status.
        """
        from fastapi import HTTPException

        from mcp_server_langgraph.api.v1.remediation_approvals import (
            require_admin_role,
        )

        regular_user = {
            "user_id": "user-789",
            "username": "user@example.com",
            "roles": ["developer"],
        }

        with pytest.raises(HTTPException) as exc_info:
            require_admin_role(regular_user)

        assert exc_info.value.status_code == 403
        assert "admin" in exc_info.value.detail.lower()

    def test_require_admin_role_denies_user_without_roles(self) -> None:
        """
        GIVEN a user with no roles
        WHEN checking authorization
        THEN should raise HTTPException with 403 status.
        """
        from fastapi import HTTPException

        from mcp_server_langgraph.api.v1.remediation_approvals import (
            require_admin_role,
        )

        no_role_user = {
            "user_id": "user-000",
            "username": "norole@example.com",
            "roles": [],
        }

        with pytest.raises(HTTPException) as exc_info:
            require_admin_role(no_role_user)

        assert exc_info.value.status_code == 403

    @pytest.mark.asyncio
    async def test_list_pending_requires_authentication(self) -> None:
        """
        GIVEN the list_pending_remediations endpoint
        WHEN checking endpoint signature
        THEN should have current_user parameter dependency.
        """
        from mcp_server_langgraph.api.v1.remediation_approvals import (
            list_pending_remediations,
        )
        import inspect

        sig = inspect.signature(list_pending_remediations)
        param_names = list(sig.parameters.keys())

        # Should have current_user parameter for auth
        assert "current_user" in param_names, "Endpoint should require authentication"

    @pytest.mark.asyncio
    async def test_approve_requires_authentication(self) -> None:
        """
        GIVEN the approve_remediation endpoint
        WHEN checking endpoint signature
        THEN should have current_user parameter dependency.
        """
        from mcp_server_langgraph.api.v1.remediation_approvals import (
            approve_remediation,
        )
        import inspect

        sig = inspect.signature(approve_remediation)
        param_names = list(sig.parameters.keys())

        assert "current_user" in param_names, "Endpoint should require authentication"

    @pytest.mark.asyncio
    async def test_reject_requires_authentication(self) -> None:
        """
        GIVEN the reject_remediation endpoint
        WHEN checking endpoint signature
        THEN should have current_user parameter dependency.
        """
        from mcp_server_langgraph.api.v1.remediation_approvals import (
            reject_remediation,
        )
        import inspect

        sig = inspect.signature(reject_remediation)
        param_names = list(sig.parameters.keys())

        assert "current_user" in param_names, "Endpoint should require authentication"

    @pytest.mark.asyncio
    async def test_history_requires_authentication(self) -> None:
        """
        GIVEN the get_remediation_history endpoint
        WHEN checking endpoint signature
        THEN should have current_user parameter dependency.
        """
        from mcp_server_langgraph.api.v1.remediation_approvals import (
            get_remediation_history,
        )
        import inspect

        sig = inspect.signature(get_remediation_history)
        param_names = list(sig.parameters.keys())

        assert "current_user" in param_names, "Endpoint should require authentication"


@pytest.mark.xdist_group(name="test_remediation_approvals")
class TestRemediationApprovalAuditTrail:
    """Tests for audit trail on remediation actions.

    All remediation approve/reject actions should be audited for compliance.
    """

    def teardown_method(self) -> None:
        """Force GC to prevent mock accumulation in xdist workers."""
        gc.collect()

    def test_remediation_audit_event_types_exist(self) -> None:
        """
        GIVEN the audit models module
        WHEN checking for remediation audit event types
        THEN should have REMEDIATION_APPROVED and REMEDIATION_REJECTED types.
        """
        from mcp_server_langgraph.audit.models import AuditEventType

        assert hasattr(AuditEventType, "REMEDIATION_APPROVED")
        assert hasattr(AuditEventType, "REMEDIATION_REJECTED")
        assert AuditEventType.REMEDIATION_APPROVED == "remediation.approved"
        assert AuditEventType.REMEDIATION_REJECTED == "remediation.rejected"

    def test_log_remediation_audit_event_function_exists(self) -> None:
        """
        GIVEN the remediation approvals module
        WHEN importing log_remediation_audit_event
        THEN should export the audit logging helper.
        """
        from mcp_server_langgraph.api.v1.remediation_approvals import (
            log_remediation_audit_event,
        )

        assert log_remediation_audit_event is not None
        assert callable(log_remediation_audit_event)

    @pytest.mark.asyncio
    async def test_log_remediation_audit_event_creates_event(self) -> None:
        """
        GIVEN an audit service and remediation data
        WHEN logging a remediation audit event
        THEN should call service.log_event with proper event structure.
        """
        from mcp_server_langgraph.api.v1.remediation_approvals import (
            log_remediation_audit_event,
        )
        from mcp_server_langgraph.audit.models import AuditEventType

        mock_audit_service = AsyncMock()

        await log_remediation_audit_event(
            audit_service=mock_audit_service,
            event_type=AuditEventType.REMEDIATION_APPROVED,
            remediation_id="rem-001",
            alert_id="alert-001",
            user_id="admin-123",
            username="admin@example.com",
            action="approve",
            details={"reason": "Test approval"},
        )

        mock_audit_service.log_event.assert_called_once()
        call_args = mock_audit_service.log_event.call_args
        event = call_args[0][0]

        assert event.event_type == AuditEventType.REMEDIATION_APPROVED
        assert event.resource_type == "remediation"
        assert event.resource_id == "rem-001"
        assert event.actor.actor_id == "admin-123"

    @pytest.mark.asyncio
    async def test_approve_endpoint_logs_audit_event(self) -> None:
        """
        GIVEN the approve_remediation endpoint
        WHEN checking endpoint signature
        THEN should have audit_service parameter dependency.
        """
        from mcp_server_langgraph.api.v1.remediation_approvals import (
            approve_remediation,
        )
        import inspect

        sig = inspect.signature(approve_remediation)
        param_names = list(sig.parameters.keys())

        assert "audit_service" in param_names, "Endpoint should have audit logging"

    @pytest.mark.asyncio
    async def test_reject_endpoint_logs_audit_event(self) -> None:
        """
        GIVEN the reject_remediation endpoint
        WHEN checking endpoint signature
        THEN should have audit_service parameter dependency.
        """
        from mcp_server_langgraph.api.v1.remediation_approvals import (
            reject_remediation,
        )
        import inspect

        sig = inspect.signature(reject_remediation)
        param_names = list(sig.parameters.keys())

        assert "audit_service" in param_names, "Endpoint should have audit logging"


@pytest.mark.xdist_group(name="test_remediation_approvals")
class TestRemediationFeedbackIntegration:
    """Tests for structured rejection reasons and feedback tracking.

    Phase 8.5-8.6: Feedback is saved on approval/rejection for AI learning.
    """

    def teardown_method(self) -> None:
        """Force GC to prevent mock accumulation in xdist workers."""
        gc.collect()

    def test_reject_request_has_structured_reason(self) -> None:
        """
        GIVEN the RejectRequest model
        WHEN inspecting the model
        THEN should have structured reason field accepting RejectionReason.
        """
        from mcp_server_langgraph.api.v1.remediation_approvals import (
            RejectRequest,
        )

        # Create a RejectRequest with structured reason
        request = RejectRequest(
            rejected_by="admin@example.com",
            reason="too_risky",
            reason_detail="Command could delete production data",
        )

        assert request.reason == "too_risky"
        assert request.reason_detail == "Command could delete production data"

    def test_reject_request_supports_all_rejection_reasons(self) -> None:
        """
        GIVEN the RejectRequest model
        WHEN creating with each RejectionReason value
        THEN should accept all valid reasons.
        """
        from mcp_server_langgraph.api.v1.remediation_approvals import (
            RejectRequest,
        )
        from mcp_server_langgraph.alerts.feedback import RejectionReason

        valid_reasons = [
            RejectionReason.TOO_RISKY,
            RejectionReason.INCORRECT_DIAGNOSIS,
            RejectionReason.WRONG_COMMAND,
            RejectionReason.INCOMPLETE_STEPS,
            RejectionReason.NOT_RELEVANT,
            RejectionReason.PREFER_MANUAL,
            RejectionReason.OTHER,
        ]

        for reason in valid_reasons:
            request = RejectRequest(
                rejected_by="admin@example.com",
                reason=reason.value,
            )
            assert request.reason == reason.value

    def test_reject_endpoint_has_feedback_store_parameter(self) -> None:
        """
        GIVEN the reject_remediation endpoint
        WHEN checking endpoint signature
        THEN should have feedback_store parameter for AI learning.
        """
        from mcp_server_langgraph.api.v1.remediation_approvals import (
            reject_remediation,
        )
        import inspect

        sig = inspect.signature(reject_remediation)
        param_names = list(sig.parameters.keys())

        assert "feedback_store" in param_names, (
            "Endpoint should have feedback_store for AI learning"
        )

    def test_approve_endpoint_has_feedback_store_parameter(self) -> None:
        """
        GIVEN the approve_remediation endpoint
        WHEN checking endpoint signature
        THEN should have feedback_store parameter for AI learning.
        """
        from mcp_server_langgraph.api.v1.remediation_approvals import (
            approve_remediation,
        )
        import inspect

        sig = inspect.signature(approve_remediation)
        param_names = list(sig.parameters.keys())

        assert "feedback_store" in param_names, (
            "Endpoint should have feedback_store for AI learning"
        )

    @pytest.mark.asyncio
    async def test_rejection_saves_feedback(self) -> None:
        """
        GIVEN a pending remediation and feedback store
        WHEN rejecting with structured reason
        THEN should save feedback for AI learning.
        """
        from mcp_server_langgraph.alerts.feedback import (
            InMemoryFeedbackStore,
            RejectionReason,
        )
        from mcp_server_langgraph.alerts.approval_queue import (
            RemediationApprovalQueue,
        )
        from mcp_server_langgraph.alerts.ai_recommendation import AIRecommendation

        queue = RemediationApprovalQueue()
        feedback_store = InMemoryFeedbackStore()

        recommendation = AIRecommendation(
            recommendation_id="rec-001",
            alert_id="alert-001",
            root_cause_analysis="Test",
            remediation_steps=[
                {
                    "step_number": 1,
                    "action": "restart",
                    "description": "Restart pods",
                    "requires_approval": True,
                    "risk_level": "high",
                }
            ],
            risk_assessment={},
            generated_at=datetime.now(UTC).isoformat(),
            model_used="test-model",
        )

        await queue.queue_remediation(
            alert_id="alert-001",
            alert_name="HighRiskAlert",
            severity="critical",
            recommendation=recommendation,
        )

        pending = await queue.list_pending()
        remediation_id = pending[0].remediation_id

        # Reject with structured reason
        await queue.reject_with_feedback(
            remediation_id=remediation_id,
            rejected_by="admin@example.com",
            reason=RejectionReason.TOO_RISKY,
            reason_detail="Could cause data loss",
            feedback_store=feedback_store,
        )

        # Verify feedback was saved
        recent = await feedback_store.get_recent_feedback(limit=10)
        assert len(recent) == 1
        assert recent[0].action == "rejected"
        assert recent[0].reason == RejectionReason.TOO_RISKY
        assert recent[0].reason_detail == "Could cause data loss"

    @pytest.mark.asyncio
    async def test_approval_saves_feedback(self) -> None:
        """
        GIVEN a pending remediation and feedback store
        WHEN approving
        THEN should save approval feedback for AI learning.
        """
        from mcp_server_langgraph.alerts.feedback import InMemoryFeedbackStore
        from mcp_server_langgraph.alerts.approval_queue import (
            RemediationApprovalQueue,
        )
        from mcp_server_langgraph.alerts.ai_recommendation import AIRecommendation

        queue = RemediationApprovalQueue()
        feedback_store = InMemoryFeedbackStore()

        recommendation = AIRecommendation(
            recommendation_id="rec-001",
            alert_id="alert-001",
            root_cause_analysis="Test",
            remediation_steps=[
                {
                    "step_number": 1,
                    "action": "restart",
                    "description": "Restart pods",
                    "requires_approval": True,
                    "risk_level": "low",
                }
            ],
            risk_assessment={},
            generated_at=datetime.now(UTC).isoformat(),
            model_used="test-model",
        )

        await queue.queue_remediation(
            alert_id="alert-001",
            alert_name="SafeAlert",
            severity="warning",
            recommendation=recommendation,
        )

        pending = await queue.list_pending()
        remediation_id = pending[0].remediation_id

        # Approve with feedback
        await queue.approve_with_feedback(
            remediation_id=remediation_id,
            approved_by="admin@example.com",
            feedback_store=feedback_store,
        )

        # Verify feedback was saved
        recent = await feedback_store.get_recent_feedback(limit=10)
        assert len(recent) == 1
        assert recent[0].action == "approved"
        assert recent[0].reason is None

    @pytest.mark.asyncio
    async def test_rejection_patterns_accumulated(self) -> None:
        """
        GIVEN multiple rejected remediations
        WHEN querying rejection patterns
        THEN should return counts by reason for constraint learning.
        """
        from mcp_server_langgraph.alerts.feedback import (
            InMemoryFeedbackStore,
            RejectionReason,
        )
        from mcp_server_langgraph.alerts.approval_queue import (
            RemediationApprovalQueue,
        )
        from mcp_server_langgraph.alerts.ai_recommendation import AIRecommendation

        queue = RemediationApprovalQueue()
        feedback_store = InMemoryFeedbackStore()

        recommendation = AIRecommendation(
            recommendation_id="rec-001",
            alert_id="alert-001",
            root_cause_analysis="Test",
            remediation_steps=[
                {
                    "step_number": 1,
                    "action": "restart",
                    "description": "Restart pods",
                    "requires_approval": True,
                    "risk_level": "high",
                }
            ],
            risk_assessment={},
            generated_at=datetime.now(UTC).isoformat(),
            model_used="test-model",
        )

        # Create multiple rejections with different reasons
        reasons = [
            RejectionReason.TOO_RISKY,
            RejectionReason.TOO_RISKY,
            RejectionReason.WRONG_COMMAND,
        ]

        for i, reason in enumerate(reasons):
            await queue.queue_remediation(
                alert_id=f"alert-{i}",
                alert_name="TestAlert",
                severity="critical",
                recommendation=recommendation,
            )
            pending = await queue.list_pending()
            latest = pending[-1]

            await queue.reject_with_feedback(
                remediation_id=latest.remediation_id,
                rejected_by="admin@example.com",
                reason=reason,
                feedback_store=feedback_store,
            )

        # Get patterns
        patterns = await feedback_store.get_rejection_patterns("TestAlert")
        assert patterns.get(RejectionReason.TOO_RISKY, 0) == 2
        assert patterns.get(RejectionReason.WRONG_COMMAND, 0) == 1
