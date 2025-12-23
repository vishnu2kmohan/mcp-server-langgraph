"""
Agent Request REST API Unit Tests.

Tests for the agent HITL (Human-in-the-Loop) request REST API following TDD.
This API manages pending agent requests for approvals and clarifications when
agent confidence drops below the configured threshold.

Features tested:
- List pending agent requests
- Get request details
- Approve agent decisions
- Reject agent decisions
- Request queue management
- Authorization (admin/reviewer role)
- Audit trail for HITL decisions

Reference: Plan file - Confidence-Based Human-in-the-Loop for Multi-Agent Orchestrator
"""

from __future__ import annotations

import gc
import inspect
from datetime import UTC, datetime
from typing import Any
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

pytestmark = [
    pytest.mark.unit,
    pytest.mark.api,
    pytest.mark.hitl,
]


@pytest.mark.xdist_group(name="test_agent_requests")
class TestAgentRequestRouterExists:
    """Tests for agent request router existence."""

    def teardown_method(self) -> None:
        """Force GC to prevent mock accumulation in xdist workers."""
        gc.collect()

    def test_agent_request_router_exists(self) -> None:
        """
        GIVEN the agent_requests module
        WHEN importing the router
        THEN should export agent_request_router.
        """
        from mcp_server_langgraph.api.v1.agent_requests import (
            agent_request_router,
        )

        assert agent_request_router is not None

    def test_router_has_correct_prefix(self) -> None:
        """
        GIVEN the agent_request_router
        WHEN checking the prefix
        THEN should have /agents/requests prefix.
        """
        from mcp_server_langgraph.api.v1.agent_requests import (
            agent_request_router,
        )

        assert agent_request_router.prefix == "/agents/requests"

    def test_router_has_correct_tags(self) -> None:
        """
        GIVEN the agent_request_router
        WHEN checking the tags
        THEN should have agents tag for OpenAPI grouping.
        """
        from mcp_server_langgraph.api.v1.agent_requests import (
            agent_request_router,
        )

        assert "agents" in agent_request_router.tags


@pytest.mark.xdist_group(name="test_agent_requests")
class TestAgentRequestEndpoints:
    """Tests for agent request API endpoints."""

    def teardown_method(self) -> None:
        """Force GC to prevent mock accumulation in xdist workers."""
        gc.collect()

    def test_list_pending_endpoint_exists(self) -> None:
        """
        GIVEN the agent_request_router
        WHEN checking routes
        THEN should have GET /pending endpoint.
        """
        from mcp_server_langgraph.api.v1.agent_requests import (
            agent_request_router,
        )

        routes = [r for r in agent_request_router.routes]
        pending_routes = [
            r for r in routes if hasattr(r, "path") and "pending" in r.path
        ]
        assert len(pending_routes) > 0, "Should have /pending route"

    def test_get_request_endpoint_exists(self) -> None:
        """
        GIVEN the agent_request_router
        WHEN checking routes
        THEN should have GET /{request_id} endpoint.
        """
        from mcp_server_langgraph.api.v1.agent_requests import (
            agent_request_router,
        )

        routes = [r for r in agent_request_router.routes]
        detail_routes = [
            r for r in routes
            if hasattr(r, "path") and "{request_id}" in r.path and "GET" in (r.methods or [])
        ]
        assert len(detail_routes) > 0, "Should have /{request_id} GET route"

    def test_approve_endpoint_exists(self) -> None:
        """
        GIVEN the agent_request_router
        WHEN checking routes
        THEN should have POST /{request_id}/approve endpoint.
        """
        from mcp_server_langgraph.api.v1.agent_requests import (
            agent_request_router,
        )

        routes = [r for r in agent_request_router.routes]
        approve_routes = [
            r for r in routes if hasattr(r, "path") and "approve" in r.path
        ]
        assert len(approve_routes) > 0, "Should have approve route"

    def test_reject_endpoint_exists(self) -> None:
        """
        GIVEN the agent_request_router
        WHEN checking routes
        THEN should have POST /{request_id}/reject endpoint.
        """
        from mcp_server_langgraph.api.v1.agent_requests import (
            agent_request_router,
        )

        routes = [r for r in agent_request_router.routes]
        reject_routes = [
            r for r in routes if hasattr(r, "path") and "reject" in r.path
        ]
        assert len(reject_routes) > 0, "Should have reject route"

    def test_respond_endpoint_exists(self) -> None:
        """
        GIVEN the agent_request_router
        WHEN checking routes
        THEN should have POST /{request_id}/respond endpoint for clarifications.
        """
        from mcp_server_langgraph.api.v1.agent_requests import (
            agent_request_router,
        )

        routes = [r for r in agent_request_router.routes]
        respond_routes = [
            r for r in routes if hasattr(r, "path") and "respond" in r.path
        ]
        assert len(respond_routes) > 0, "Should have respond route"


@pytest.mark.xdist_group(name="test_agent_requests")
class TestAgentRequestModels:
    """Tests for agent request data models."""

    def teardown_method(self) -> None:
        """Force GC to prevent mock accumulation in xdist workers."""
        gc.collect()

    def test_agent_request_model_exists(self) -> None:
        """
        GIVEN the agent_requests module
        WHEN importing AgentRequest model
        THEN should be a valid Pydantic model.
        """
        from mcp_server_langgraph.api.v1.agent_requests import (
            AgentRequest,
        )

        assert AgentRequest is not None

    def test_agent_request_has_required_fields(self) -> None:
        """
        GIVEN an AgentRequest model
        WHEN creating instance
        THEN should have all required fields.
        """
        from mcp_server_langgraph.api.v1.agent_requests import (
            AgentRequest,
            AgentRequestType,
            AgentRequestStatus,
        )

        request = AgentRequest(
            request_id="req-001",
            session_id="session-001",
            task_id="task-001",
            agent_name="Research Assistant",
            request_type=AgentRequestType.APPROVAL,
            confidence=0.65,
            threshold=0.70,
            question="Approve analysis output?",
            status=AgentRequestStatus.PENDING,
            requested_at=datetime.now(UTC).isoformat(),
        )

        assert request.request_id == "req-001"
        assert request.session_id == "session-001"
        assert request.task_id == "task-001"
        assert request.agent_name == "Research Assistant"
        assert request.request_type == AgentRequestType.APPROVAL
        assert request.confidence == 0.65
        assert request.threshold == 0.70
        assert request.status == AgentRequestStatus.PENDING

    def test_agent_request_type_enum_exists(self) -> None:
        """
        GIVEN the agent_requests module
        WHEN importing AgentRequestType
        THEN should have APPROVAL and CLARIFICATION types.
        """
        from mcp_server_langgraph.api.v1.agent_requests import (
            AgentRequestType,
        )

        assert hasattr(AgentRequestType, "APPROVAL")
        assert hasattr(AgentRequestType, "CLARIFICATION")
        assert AgentRequestType.APPROVAL.value == "approval"
        assert AgentRequestType.CLARIFICATION.value == "clarification"

    def test_agent_request_status_enum_exists(self) -> None:
        """
        GIVEN the agent_requests module
        WHEN importing AgentRequestStatus
        THEN should have PENDING, APPROVED, REJECTED, RESPONDED statuses.
        """
        from mcp_server_langgraph.api.v1.agent_requests import (
            AgentRequestStatus,
        )

        assert hasattr(AgentRequestStatus, "PENDING")
        assert hasattr(AgentRequestStatus, "APPROVED")
        assert hasattr(AgentRequestStatus, "REJECTED")
        assert hasattr(AgentRequestStatus, "RESPONDED")

    def test_approve_request_model_exists(self) -> None:
        """
        GIVEN the agent_requests module
        WHEN importing ApproveAgentRequest model
        THEN should be a valid Pydantic model.
        """
        from mcp_server_langgraph.api.v1.agent_requests import (
            ApproveAgentRequest,
        )

        request = ApproveAgentRequest(
            approved_by="admin@example.com",
            reason="Confidence is acceptable",
        )

        assert request.approved_by == "admin@example.com"
        assert request.reason == "Confidence is acceptable"

    def test_approve_request_reason_optional(self) -> None:
        """
        GIVEN ApproveAgentRequest model
        WHEN creating without reason
        THEN should allow None reason.
        """
        from mcp_server_langgraph.api.v1.agent_requests import (
            ApproveAgentRequest,
        )

        request = ApproveAgentRequest(approved_by="admin@example.com")
        assert request.reason is None

    def test_reject_request_model_exists(self) -> None:
        """
        GIVEN the agent_requests module
        WHEN importing RejectAgentRequest model
        THEN should be a valid Pydantic model.
        """
        from mcp_server_langgraph.api.v1.agent_requests import (
            RejectAgentRequest,
        )

        request = RejectAgentRequest(
            rejected_by="admin@example.com",
            reason="Confidence too low for production",
        )

        assert request.rejected_by == "admin@example.com"
        assert request.reason == "Confidence too low for production"

    def test_clarification_response_model_exists(self) -> None:
        """
        GIVEN the agent_requests module
        WHEN importing ClarificationResponseRequest model
        THEN should be a valid Pydantic model.
        """
        from mcp_server_langgraph.api.v1.agent_requests import (
            ClarificationResponseRequest,
        )
        from mcp_server_langgraph.core.interrupts.clarification import (
            ClarificationType,
        )

        response = ClarificationResponseRequest(
            responded_by="user@example.com",
            response_type=ClarificationType.CHOICE,
            selected_option_id="option-1",
        )

        assert response.responded_by == "user@example.com"
        assert response.response_type == ClarificationType.CHOICE
        assert response.selected_option_id == "option-1"

    def test_clarification_response_text_value(self) -> None:
        """
        GIVEN ClarificationResponseRequest model
        WHEN creating for text type
        THEN should accept value field.
        """
        from mcp_server_langgraph.api.v1.agent_requests import (
            ClarificationResponseRequest,
        )
        from mcp_server_langgraph.core.interrupts.clarification import (
            ClarificationType,
        )

        response = ClarificationResponseRequest(
            responded_by="user@example.com",
            response_type=ClarificationType.TEXT,
            value="My custom input",
        )

        assert response.value == "My custom input"

    def test_clarification_response_confirmation(self) -> None:
        """
        GIVEN ClarificationResponseRequest model
        WHEN creating for confirmation type
        THEN should accept confirmed field.
        """
        from mcp_server_langgraph.api.v1.agent_requests import (
            ClarificationResponseRequest,
        )
        from mcp_server_langgraph.core.interrupts.clarification import (
            ClarificationType,
        )

        response = ClarificationResponseRequest(
            responded_by="user@example.com",
            response_type=ClarificationType.CONFIRMATION,
            confirmed=True,
        )

        assert response.confirmed is True


@pytest.mark.xdist_group(name="test_agent_requests")
class TestAgentRequestQueueService:
    """Tests for agent request queue service."""

    def teardown_method(self) -> None:
        """Force GC to prevent mock accumulation in xdist workers."""
        gc.collect()

    def test_agent_request_queue_class_exists(self) -> None:
        """
        GIVEN the agent_requests module
        WHEN importing AgentRequestQueue
        THEN should export the queue class.
        """
        from mcp_server_langgraph.api.v1.agent_requests import (
            AgentRequestQueue,
        )

        assert AgentRequestQueue is not None

    def test_get_agent_request_queue_dependency_exists(self) -> None:
        """
        GIVEN the agent_requests module
        WHEN importing get_agent_request_queue
        THEN should export the dependency function.
        """
        from mcp_server_langgraph.api.v1.agent_requests import (
            get_agent_request_queue,
        )

        assert get_agent_request_queue is not None
        assert callable(get_agent_request_queue)

    @pytest.mark.asyncio
    async def test_queue_creates_pending_request(self) -> None:
        """
        GIVEN an AgentRequestQueue
        WHEN queueing a request
        THEN should add to pending queue.
        """
        from mcp_server_langgraph.api.v1.agent_requests import (
            AgentRequestQueue,
            AgentRequestType,
        )

        queue = AgentRequestQueue()

        await queue.queue_approval_request(
            session_id="session-001",
            task_id="task-001",
            agent_name="Research Assistant",
            confidence=0.65,
            threshold=0.70,
            proposed_action="Send analysis report",
        )

        pending = await queue.list_pending()
        assert len(pending) == 1
        assert pending[0].request_type == AgentRequestType.APPROVAL

    @pytest.mark.asyncio
    async def test_queue_clarification_request(self) -> None:
        """
        GIVEN an AgentRequestQueue
        WHEN queueing a clarification request
        THEN should add to pending queue with correct type.
        """
        from mcp_server_langgraph.api.v1.agent_requests import (
            AgentRequestQueue,
            AgentRequestType,
        )
        from mcp_server_langgraph.core.interrupts.clarification import (
            ClarificationType,
        )

        queue = AgentRequestQueue()

        await queue.queue_clarification_request(
            session_id="session-001",
            task_id="task-001",
            agent_name="Data Analyst",
            clarification_type=ClarificationType.CHOICE,
            question="Which format should I use?",
            options=[
                {"id": "csv", "label": "CSV"},
                {"id": "json", "label": "JSON"},
            ],
        )

        pending = await queue.list_pending()
        assert len(pending) == 1
        assert pending[0].request_type == AgentRequestType.CLARIFICATION

    @pytest.mark.asyncio
    async def test_approve_changes_status(self) -> None:
        """
        GIVEN a pending approval request
        WHEN approving the request
        THEN should change status to approved.
        """
        from mcp_server_langgraph.api.v1.agent_requests import (
            AgentRequestQueue,
            AgentRequestStatus,
        )

        queue = AgentRequestQueue()

        await queue.queue_approval_request(
            session_id="session-001",
            task_id="task-001",
            agent_name="Research Assistant",
            confidence=0.65,
            threshold=0.70,
            proposed_action="Send analysis report",
        )

        pending = await queue.list_pending()
        request_id = pending[0].request_id

        result = await queue.approve(
            request_id=request_id,
            approved_by="admin@example.com",
        )

        assert result.status == AgentRequestStatus.APPROVED

    @pytest.mark.asyncio
    async def test_reject_changes_status(self) -> None:
        """
        GIVEN a pending approval request
        WHEN rejecting the request
        THEN should change status to rejected.
        """
        from mcp_server_langgraph.api.v1.agent_requests import (
            AgentRequestQueue,
            AgentRequestStatus,
        )

        queue = AgentRequestQueue()

        await queue.queue_approval_request(
            session_id="session-001",
            task_id="task-001",
            agent_name="Research Assistant",
            confidence=0.65,
            threshold=0.70,
            proposed_action="Send analysis report",
        )

        pending = await queue.list_pending()
        request_id = pending[0].request_id

        result = await queue.reject(
            request_id=request_id,
            rejected_by="admin@example.com",
            reason="Too risky",
        )

        assert result.status == AgentRequestStatus.REJECTED

    @pytest.mark.asyncio
    async def test_respond_to_clarification(self) -> None:
        """
        GIVEN a pending clarification request
        WHEN responding to the request
        THEN should change status to responded.
        """
        from mcp_server_langgraph.api.v1.agent_requests import (
            AgentRequestQueue,
            AgentRequestStatus,
        )
        from mcp_server_langgraph.core.interrupts.clarification import (
            ClarificationType,
        )

        queue = AgentRequestQueue()

        await queue.queue_clarification_request(
            session_id="session-001",
            task_id="task-001",
            agent_name="Data Analyst",
            clarification_type=ClarificationType.CHOICE,
            question="Which format?",
            options=[{"id": "csv", "label": "CSV"}],
        )

        pending = await queue.list_pending()
        request_id = pending[0].request_id

        result = await queue.respond(
            request_id=request_id,
            responded_by="user@example.com",
            response_type=ClarificationType.CHOICE,
            selected_option_id="csv",
        )

        assert result.status == AgentRequestStatus.RESPONDED

    @pytest.mark.asyncio
    async def test_get_request_by_id(self) -> None:
        """
        GIVEN a queued request
        WHEN getting by ID
        THEN should return the request details.
        """
        from mcp_server_langgraph.api.v1.agent_requests import (
            AgentRequestQueue,
        )

        queue = AgentRequestQueue()

        await queue.queue_approval_request(
            session_id="session-001",
            task_id="task-001",
            agent_name="Research Assistant",
            confidence=0.65,
            threshold=0.70,
            proposed_action="Send analysis report",
        )

        pending = await queue.list_pending()
        request_id = pending[0].request_id

        result = await queue.get_request(request_id)
        assert result is not None
        assert result.request_id == request_id

    @pytest.mark.asyncio
    async def test_get_request_not_found(self) -> None:
        """
        GIVEN an AgentRequestQueue
        WHEN getting a non-existent request
        THEN should return None.
        """
        from mcp_server_langgraph.api.v1.agent_requests import (
            AgentRequestQueue,
        )

        queue = AgentRequestQueue()
        result = await queue.get_request("non-existent-id")
        assert result is None

    @pytest.mark.asyncio
    async def test_list_pending_excludes_completed(self) -> None:
        """
        GIVEN requests with different statuses
        WHEN listing pending
        THEN should only return pending requests.
        """
        from mcp_server_langgraph.api.v1.agent_requests import (
            AgentRequestQueue,
        )

        queue = AgentRequestQueue()

        # Queue two requests
        await queue.queue_approval_request(
            session_id="session-001",
            task_id="task-001",
            agent_name="Agent 1",
            confidence=0.65,
            threshold=0.70,
            proposed_action="Action 1",
        )
        await queue.queue_approval_request(
            session_id="session-002",
            task_id="task-002",
            agent_name="Agent 2",
            confidence=0.60,
            threshold=0.70,
            proposed_action="Action 2",
        )

        pending = await queue.list_pending()
        assert len(pending) == 2

        # Approve one
        await queue.approve(
            request_id=pending[0].request_id,
            approved_by="admin@example.com",
        )

        # Should only return one pending now
        pending_after = await queue.list_pending()
        assert len(pending_after) == 1


@pytest.mark.xdist_group(name="test_agent_requests")
class TestAgentRequestAuthorization:
    """Tests for admin authorization on agent request endpoints.

    All agent request approval/reject endpoints require admin or reviewer role.
    """

    def teardown_method(self) -> None:
        """Force GC to prevent mock accumulation in xdist workers."""
        gc.collect()

    def test_require_reviewer_role_function_exists(self) -> None:
        """
        GIVEN the agent_requests module
        WHEN importing require_reviewer_role
        THEN should export the authorization helper.
        """
        from mcp_server_langgraph.api.v1.agent_requests import (
            require_reviewer_role,
        )

        assert require_reviewer_role is not None
        assert callable(require_reviewer_role)

    def test_require_reviewer_role_allows_admin(self) -> None:
        """
        GIVEN a user with admin role
        WHEN checking authorization
        THEN should allow access (no exception).
        """
        from mcp_server_langgraph.api.v1.agent_requests import (
            require_reviewer_role,
        )

        admin_user = {
            "user_id": "admin-123",
            "username": "admin@example.com",
            "roles": ["admin"],
        }

        # Should not raise
        require_reviewer_role(admin_user)

    def test_require_reviewer_role_allows_hitl_reviewer(self) -> None:
        """
        GIVEN a user with hitl_reviewer role
        WHEN checking authorization
        THEN should allow access (no exception).
        """
        from mcp_server_langgraph.api.v1.agent_requests import (
            require_reviewer_role,
        )

        reviewer_user = {
            "user_id": "reviewer-456",
            "username": "reviewer@example.com",
            "roles": ["hitl_reviewer"],
        }

        # Should not raise
        require_reviewer_role(reviewer_user)

    def test_require_reviewer_role_denies_regular_user(self) -> None:
        """
        GIVEN a user without admin or hitl_reviewer role
        WHEN checking authorization
        THEN should raise HTTPException with 403 status.
        """
        from fastapi import HTTPException

        from mcp_server_langgraph.api.v1.agent_requests import (
            require_reviewer_role,
        )

        regular_user = {
            "user_id": "user-789",
            "username": "user@example.com",
            "roles": ["developer"],
        }

        with pytest.raises(HTTPException) as exc_info:
            require_reviewer_role(regular_user)

        assert exc_info.value.status_code == 403

    def test_list_pending_requires_authentication(self) -> None:
        """
        GIVEN the list_pending_agent_requests endpoint
        WHEN checking endpoint signature
        THEN should have current_user parameter dependency.
        """
        from mcp_server_langgraph.api.v1.agent_requests import (
            list_pending_agent_requests,
        )

        sig = inspect.signature(list_pending_agent_requests)
        param_names = list(sig.parameters.keys())

        assert "current_user" in param_names, "Endpoint should require authentication"

    def test_approve_requires_authentication(self) -> None:
        """
        GIVEN the approve_agent_request endpoint
        WHEN checking endpoint signature
        THEN should have current_user parameter dependency.
        """
        from mcp_server_langgraph.api.v1.agent_requests import (
            approve_agent_request,
        )

        sig = inspect.signature(approve_agent_request)
        param_names = list(sig.parameters.keys())

        assert "current_user" in param_names, "Endpoint should require authentication"

    def test_reject_requires_authentication(self) -> None:
        """
        GIVEN the reject_agent_request endpoint
        WHEN checking endpoint signature
        THEN should have current_user parameter dependency.
        """
        from mcp_server_langgraph.api.v1.agent_requests import (
            reject_agent_request,
        )

        sig = inspect.signature(reject_agent_request)
        param_names = list(sig.parameters.keys())

        assert "current_user" in param_names, "Endpoint should require authentication"


@pytest.mark.xdist_group(name="test_agent_requests")
class TestAgentRequestAuditTrail:
    """Tests for audit trail on agent request actions.

    All agent approval/reject actions should be audited for compliance.
    """

    def teardown_method(self) -> None:
        """Force GC to prevent mock accumulation in xdist workers."""
        gc.collect()

    def test_agent_request_audit_event_types_exist(self) -> None:
        """
        GIVEN the audit models module
        WHEN checking for agent request audit event types
        THEN should have AGENT_REQUEST_APPROVED and AGENT_REQUEST_REJECTED types.
        """
        from mcp_server_langgraph.audit.models import AuditEventType

        assert hasattr(AuditEventType, "AGENT_REQUEST_APPROVED")
        assert hasattr(AuditEventType, "AGENT_REQUEST_REJECTED")
        assert AuditEventType.AGENT_REQUEST_APPROVED == "agent_request.approved"
        assert AuditEventType.AGENT_REQUEST_REJECTED == "agent_request.rejected"

    def test_log_agent_request_audit_event_function_exists(self) -> None:
        """
        GIVEN the agent_requests module
        WHEN importing log_agent_request_audit_event
        THEN should export the audit logging helper.
        """
        from mcp_server_langgraph.api.v1.agent_requests import (
            log_agent_request_audit_event,
        )

        assert log_agent_request_audit_event is not None
        assert callable(log_agent_request_audit_event)

    @pytest.mark.asyncio
    async def test_log_agent_request_audit_event_creates_event(self) -> None:
        """
        GIVEN an audit service and request data
        WHEN logging an agent request audit event
        THEN should call service.log_event with proper event structure.
        """
        from mcp_server_langgraph.api.v1.agent_requests import (
            log_agent_request_audit_event,
        )
        from mcp_server_langgraph.audit.models import AuditEventType

        mock_audit_service = AsyncMock()

        await log_agent_request_audit_event(
            audit_service=mock_audit_service,
            event_type=AuditEventType.AGENT_REQUEST_APPROVED,
            request_id="req-001",
            session_id="session-001",
            user_id="admin-123",
            username="admin@example.com",
            action="approve",
            details={"confidence": 0.65, "threshold": 0.70},
        )

        mock_audit_service.log_event.assert_called_once()
        call_args = mock_audit_service.log_event.call_args
        event = call_args[0][0]

        assert event.event_type == AuditEventType.AGENT_REQUEST_APPROVED
        assert event.resource_type == "agent_request"
        assert event.resource_id == "req-001"
        assert event.actor.actor_id == "admin-123"

    def test_approve_endpoint_logs_audit_event(self) -> None:
        """
        GIVEN the approve_agent_request endpoint
        WHEN checking endpoint signature
        THEN should have audit_service parameter dependency.
        """
        from mcp_server_langgraph.api.v1.agent_requests import (
            approve_agent_request,
        )

        sig = inspect.signature(approve_agent_request)
        param_names = list(sig.parameters.keys())

        assert "audit_service" in param_names, "Endpoint should have audit logging"

    def test_reject_endpoint_logs_audit_event(self) -> None:
        """
        GIVEN the reject_agent_request endpoint
        WHEN checking endpoint signature
        THEN should have audit_service parameter dependency.
        """
        from mcp_server_langgraph.api.v1.agent_requests import (
            reject_agent_request,
        )

        sig = inspect.signature(reject_agent_request)
        param_names = list(sig.parameters.keys())

        assert "audit_service" in param_names, "Endpoint should have audit logging"


@pytest.mark.xdist_group(name="test_agent_requests")
class TestAgentRequestResponseModels:
    """Tests for API response models."""

    def teardown_method(self) -> None:
        """Force GC to prevent mock accumulation in xdist workers."""
        gc.collect()

    def test_pending_requests_response_model_exists(self) -> None:
        """
        GIVEN the agent_requests module
        WHEN importing PendingAgentRequestsResponse
        THEN should be a valid Pydantic model.
        """
        from mcp_server_langgraph.api.v1.agent_requests import (
            PendingAgentRequestsResponse,
        )

        assert PendingAgentRequestsResponse is not None

    def test_pending_requests_response_fields(self) -> None:
        """
        GIVEN PendingAgentRequestsResponse model
        WHEN creating instance
        THEN should have requests and count fields.
        """
        from mcp_server_langgraph.api.v1.agent_requests import (
            PendingAgentRequestsResponse,
        )

        response = PendingAgentRequestsResponse(
            requests=[],
            count=0,
        )

        assert response.requests == []
        assert response.count == 0

    def test_agent_request_action_response_model_exists(self) -> None:
        """
        GIVEN the agent_requests module
        WHEN importing AgentRequestActionResponse
        THEN should be a valid Pydantic model.
        """
        from mcp_server_langgraph.api.v1.agent_requests import (
            AgentRequestActionResponse,
            AgentRequestStatus,
        )

        response = AgentRequestActionResponse(
            request_id="req-001",
            status=AgentRequestStatus.APPROVED,
            message="Request approved",
            resumed=True,
        )

        assert response.request_id == "req-001"
        assert response.status == AgentRequestStatus.APPROVED
        assert response.message == "Request approved"
        assert response.resumed is True


@pytest.mark.xdist_group(name="test_agent_requests")
class TestAgentRequestFeatureFlagIntegration:
    """Tests for feature flag integration with agent requests."""

    def teardown_method(self) -> None:
        """Force GC to prevent mock accumulation in xdist workers."""
        gc.collect()

    def test_endpoints_check_hitl_feature_flag(self) -> None:
        """
        GIVEN agent request endpoints
        WHEN HITL feature is disabled
        THEN endpoints should return 503 or similar.
        """
        # This test will be implemented when we add feature flag checks
        # to the endpoints. For now, we test the flag exists.
        from mcp_server_langgraph.core.feature_flags import FeatureFlags

        flags = FeatureFlags()
        assert hasattr(flags, "enable_agent_hitl")

    def test_confidence_threshold_from_feature_flags(self) -> None:
        """
        GIVEN feature flags configuration
        WHEN creating an agent request queue
        THEN should use threshold from feature flags.
        """
        from mcp_server_langgraph.core.feature_flags import FeatureFlags

        flags = FeatureFlags()
        assert hasattr(flags, "agent_hitl_confidence_threshold")
        assert flags.agent_hitl_confidence_threshold == 0.7


# =========================================================================
# Batch Approval Tests (Phase 3 - Batch Operations)
# =========================================================================


@pytest.mark.xdist_group(name="test_agent_requests")
class TestBatchApprovalModelsExist:
    """Tests for batch approval model definitions."""

    def teardown_method(self) -> None:
        """Force GC to prevent mock accumulation in xdist workers."""
        gc.collect()

    def test_batch_approve_request_model_exists(self) -> None:
        """
        GIVEN the agent_requests module
        WHEN importing BatchApproveRequest
        THEN should be a valid Pydantic model.
        """
        from mcp_server_langgraph.api.v1.agent_requests import BatchApproveRequest

        assert BatchApproveRequest is not None

    def test_batch_approve_request_fields(self) -> None:
        """
        GIVEN BatchApproveRequest model
        WHEN creating instance with request_ids
        THEN should have request_ids list and optional reason.
        """
        from mcp_server_langgraph.api.v1.agent_requests import BatchApproveRequest

        request = BatchApproveRequest(
            request_ids=["req-001", "req-002", "req-003"],
            reason="All look correct",
        )

        assert request.request_ids == ["req-001", "req-002", "req-003"]
        assert request.reason == "All look correct"

    def test_batch_approve_request_reason_optional(self) -> None:
        """
        GIVEN BatchApproveRequest model
        WHEN creating instance without reason
        THEN reason should default to None.
        """
        from mcp_server_langgraph.api.v1.agent_requests import BatchApproveRequest

        request = BatchApproveRequest(request_ids=["req-001"])

        assert request.request_ids == ["req-001"]
        assert request.reason is None

    def test_batch_reject_request_model_exists(self) -> None:
        """
        GIVEN the agent_requests module
        WHEN importing BatchRejectRequest
        THEN should be a valid Pydantic model.
        """
        from mcp_server_langgraph.api.v1.agent_requests import BatchRejectRequest

        assert BatchRejectRequest is not None

    def test_batch_reject_request_fields(self) -> None:
        """
        GIVEN BatchRejectRequest model
        WHEN creating instance with request_ids
        THEN should have request_ids list and optional reason.
        """
        from mcp_server_langgraph.api.v1.agent_requests import BatchRejectRequest

        request = BatchRejectRequest(
            request_ids=["req-001", "req-002"],
            reason="Incorrect approach",
        )

        assert request.request_ids == ["req-001", "req-002"]
        assert request.reason == "Incorrect approach"

    def test_batch_response_model_exists(self) -> None:
        """
        GIVEN the agent_requests module
        WHEN importing BatchApprovalResponse
        THEN should be a valid Pydantic model.
        """
        from mcp_server_langgraph.api.v1.agent_requests import BatchApprovalResponse

        assert BatchApprovalResponse is not None

    def test_batch_response_fields(self) -> None:
        """
        GIVEN BatchApprovalResponse model
        WHEN creating instance with results
        THEN should have results list, succeeded count, and failed count.
        """
        from mcp_server_langgraph.api.v1.agent_requests import (
            AgentRequestStatus,
            BatchApprovalResponse,
            BatchApprovalResult,
        )

        response = BatchApprovalResponse(
            results=[
                BatchApprovalResult(
                    request_id="req-001",
                    status=AgentRequestStatus.APPROVED,
                    success=True,
                    message="Approved",
                ),
                BatchApprovalResult(
                    request_id="req-002",
                    status=AgentRequestStatus.APPROVED,
                    success=True,
                    message="Approved",
                ),
            ],
            succeeded=2,
            failed=0,
        )

        assert len(response.results) == 2
        assert response.succeeded == 2
        assert response.failed == 0


@pytest.mark.xdist_group(name="test_agent_requests")
class TestBatchApprovalResult:
    """Tests for individual batch approval result."""

    def teardown_method(self) -> None:
        """Force GC to prevent mock accumulation in xdist workers."""
        gc.collect()

    def test_batch_result_success(self) -> None:
        """
        GIVEN a successful batch approval
        WHEN creating BatchApprovalResult
        THEN should have success=True and status.
        """
        from mcp_server_langgraph.api.v1.agent_requests import (
            AgentRequestStatus,
            BatchApprovalResult,
        )

        result = BatchApprovalResult(
            request_id="req-001",
            status=AgentRequestStatus.APPROVED,
            success=True,
            message="Request approved successfully",
        )

        assert result.request_id == "req-001"
        assert result.status == AgentRequestStatus.APPROVED
        assert result.success is True
        assert result.message == "Request approved successfully"

    def test_batch_result_failure(self) -> None:
        """
        GIVEN a failed batch approval
        WHEN creating BatchApprovalResult
        THEN should have success=False and error details.
        """
        from mcp_server_langgraph.api.v1.agent_requests import BatchApprovalResult

        result = BatchApprovalResult(
            request_id="req-999",
            status=None,
            success=False,
            message="Request not found",
            error_code="NOT_FOUND",
        )

        assert result.request_id == "req-999"
        assert result.status is None
        assert result.success is False
        assert result.message == "Request not found"
        assert result.error_code == "NOT_FOUND"


@pytest.mark.xdist_group(name="test_agent_requests")
class TestBatchApprovalEndpoint:
    """Tests for batch approval endpoint."""

    def teardown_method(self) -> None:
        """Force GC to prevent mock accumulation in xdist workers."""
        gc.collect()

    def test_batch_approve_endpoint_exists(self) -> None:
        """
        GIVEN the agent_requests router
        WHEN checking routes
        THEN should have POST /batch/approve endpoint.
        """
        from mcp_server_langgraph.api.v1.agent_requests import agent_request_router

        # Routes include the router prefix, so we check for the full path
        routes = [route.path for route in agent_request_router.routes]
        matching = [r for r in routes if "batch/approve" in r]
        assert len(matching) > 0, f"No batch/approve route found in {routes}"

    def test_batch_reject_endpoint_exists(self) -> None:
        """
        GIVEN the agent_requests router
        WHEN checking routes
        THEN should have POST /batch/reject endpoint.
        """
        from mcp_server_langgraph.api.v1.agent_requests import agent_request_router

        # Routes include the router prefix, so we check for the full path
        routes = [route.path for route in agent_request_router.routes]
        matching = [r for r in routes if "batch/reject" in r]
        assert len(matching) > 0, f"No batch/reject route found in {routes}"

    def test_batch_approve_function_signature(self) -> None:
        """
        GIVEN the batch_approve_requests function
        WHEN inspecting its signature
        THEN should accept BatchApproveRequest and return BatchApprovalResponse.
        """
        from mcp_server_langgraph.api.v1.agent_requests import batch_approve_requests

        sig = inspect.signature(batch_approve_requests)
        params = list(sig.parameters.keys())

        assert "request" in params or "batch_request" in params
        assert "current_user" in params


@pytest.mark.xdist_group(name="test_agent_requests")
class TestAgentRequestQueueBatchOperations:
    """Tests for AgentRequestQueue batch operations."""

    def teardown_method(self) -> None:
        """Force GC to prevent mock accumulation in xdist workers."""
        gc.collect()

    def test_queue_has_batch_approve_method(self) -> None:
        """
        GIVEN AgentRequestQueue class
        WHEN checking methods
        THEN should have batch_approve method.
        """
        from mcp_server_langgraph.api.v1.agent_requests import AgentRequestQueue

        queue = AgentRequestQueue()
        assert hasattr(queue, "batch_approve")
        assert callable(getattr(queue, "batch_approve"))

    def test_queue_has_batch_reject_method(self) -> None:
        """
        GIVEN AgentRequestQueue class
        WHEN checking methods
        THEN should have batch_reject method.
        """
        from mcp_server_langgraph.api.v1.agent_requests import AgentRequestQueue

        queue = AgentRequestQueue()
        assert hasattr(queue, "batch_reject")
        assert callable(getattr(queue, "batch_reject"))

    def test_batch_approve_multiple_requests(self) -> None:
        """
        GIVEN queue with multiple pending requests
        WHEN calling batch_approve with multiple request_ids
        THEN should approve all and return results.
        """
        from mcp_server_langgraph.api.v1.agent_requests import (
            AgentRequest,
            AgentRequestQueue,
            AgentRequestStatus,
            AgentRequestType,
        )

        queue = AgentRequestQueue()

        # Add test requests
        for i in range(3):
            queue.add_request(
                AgentRequest(
                    request_id=f"req-00{i+1}",
                    session_id="session-001",
                    task_id=f"task-00{i+1}",
                    agent_name="Test Agent",
                    request_type=AgentRequestType.APPROVAL,
                    status=AgentRequestStatus.PENDING,
                    confidence=0.65,
                    threshold=0.7,
                    question=f"Approve action {i+1}?",
                    proposed_action=f"Action {i+1}",
                    trigger_reason="low_confidence",
                    requested_at=datetime.now(UTC).isoformat(),
                )
            )

        # Batch approve
        results = queue.batch_approve(
            request_ids=["req-001", "req-002", "req-003"],
            approved_by="admin@example.com",
            reason="All verified",
        )

        assert len(results) == 3
        assert all(r.success for r in results)
        assert all(r.status == AgentRequestStatus.APPROVED for r in results)

    def test_batch_approve_partial_success(self) -> None:
        """
        GIVEN queue with some valid and some invalid request IDs
        WHEN calling batch_approve
        THEN should approve valid ones and report errors for invalid.
        """
        from mcp_server_langgraph.api.v1.agent_requests import (
            AgentRequest,
            AgentRequestQueue,
            AgentRequestStatus,
            AgentRequestType,
        )

        queue = AgentRequestQueue()

        # Add only one request
        queue.add_request(
            AgentRequest(
                request_id="req-001",
                session_id="session-001",
                task_id="task-001",
                agent_name="Test Agent",
                request_type=AgentRequestType.APPROVAL,
                status=AgentRequestStatus.PENDING,
                confidence=0.65,
                threshold=0.7,
                question="Approve action 1?",
                proposed_action="Action 1",
                trigger_reason="low_confidence",
                requested_at=datetime.now(UTC).isoformat(),
            )
        )

        # Try to batch approve with one valid and one invalid
        results = queue.batch_approve(
            request_ids=["req-001", "req-999"],
            approved_by="admin@example.com",
        )

        assert len(results) == 2
        # First should succeed
        assert results[0].request_id == "req-001"
        assert results[0].success is True
        # Second should fail
        assert results[1].request_id == "req-999"
        assert results[1].success is False

    def test_batch_reject_multiple_requests(self) -> None:
        """
        GIVEN queue with multiple pending requests
        WHEN calling batch_reject with multiple request_ids
        THEN should reject all and return results.
        """
        from mcp_server_langgraph.api.v1.agent_requests import (
            AgentRequest,
            AgentRequestQueue,
            AgentRequestStatus,
            AgentRequestType,
        )

        queue = AgentRequestQueue()

        # Add test requests
        for i in range(2):
            queue.add_request(
                AgentRequest(
                    request_id=f"req-00{i+1}",
                    session_id="session-001",
                    task_id=f"task-00{i+1}",
                    agent_name="Test Agent",
                    request_type=AgentRequestType.APPROVAL,
                    status=AgentRequestStatus.PENDING,
                    confidence=0.45,
                    threshold=0.7,
                    question=f"Approve risky action {i+1}?",
                    proposed_action=f"Risky action {i+1}",
                    trigger_reason="low_confidence",
                    requested_at=datetime.now(UTC).isoformat(),
                )
            )

        # Batch reject
        results = queue.batch_reject(
            request_ids=["req-001", "req-002"],
            rejected_by="admin@example.com",
            reason="Too risky",
        )

        assert len(results) == 2
        assert all(r.success for r in results)
        assert all(r.status == AgentRequestStatus.REJECTED for r in results)

    def test_batch_approve_empty_list(self) -> None:
        """
        GIVEN AgentRequestQueue
        WHEN calling batch_approve with empty list
        THEN should return empty results.
        """
        from mcp_server_langgraph.api.v1.agent_requests import AgentRequestQueue

        queue = AgentRequestQueue()

        results = queue.batch_approve(
            request_ids=[],
            approved_by="admin@example.com",
        )

        assert results == []


@pytest.mark.xdist_group(name="test_agent_requests")
class TestBatchApprovalAuditLogging:
    """Tests for batch approval audit logging."""

    def teardown_method(self) -> None:
        """Force GC to prevent mock accumulation in xdist workers."""
        gc.collect()

    @pytest.mark.asyncio
    async def test_batch_approve_creates_audit_entries(self) -> None:
        """
        GIVEN batch approval request
        WHEN calling batch_approve_requests endpoint
        THEN should create audit entries for each approved request.
        """
        from mcp_server_langgraph.api.v1.agent_requests import (
            AgentRequest,
            AgentRequestQueue,
            AgentRequestStatus,
            AgentRequestType,
            BatchApproveRequest,
            batch_approve_requests,
            _request_queue,
        )

        # Setup: Add pending requests
        queue = _request_queue
        for i in range(2):
            queue.add_request(
                AgentRequest(
                    request_id=f"audit-req-00{i+1}",
                    session_id="session-001",
                    task_id=f"task-00{i+1}",
                    agent_name="Test Agent",
                    request_type=AgentRequestType.APPROVAL,
                    status=AgentRequestStatus.PENDING,
                    confidence=0.65,
                    threshold=0.7,
                    question=f"Approve action {i+1}?",
                    proposed_action=f"Action {i+1}",
                    trigger_reason="low_confidence",
                    requested_at=datetime.now(UTC).isoformat(),
                )
            )

        mock_audit = AsyncMock()

        batch_request = BatchApproveRequest(
            request_ids=["audit-req-001", "audit-req-002"],
            reason="Batch verified",
        )

        mock_user = {"sub": "admin@example.com", "roles": ["admin"]}

        response = await batch_approve_requests(
            batch_request=batch_request,
            current_user=mock_user,
            audit_service=mock_audit,
            queue=queue,
        )

        assert response.succeeded == 2
        # Audit service should be called for each approval via log_event
        assert mock_audit.log_event.call_count >= 2
