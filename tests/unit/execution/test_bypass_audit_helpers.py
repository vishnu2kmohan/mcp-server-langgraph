"""
Tests for bypass audit event helper functions.

Following TDD: These tests define the expected behavior of the audit helper
that will reduce duplication when logging BYPASS_* audit events.

See: execution-mode-patterns.md gotcha #6
"""

import pytest
from unittest.mock import AsyncMock

from mcp_server_langgraph.audit.models import (
    AuditEventCategory,
    AuditEventType,
    UnifiedAuditEvent,
)

from mcp_server_langgraph.execution.bypass_audit import (
    create_bypass_audit_event,
    log_bypass_audit_event,
)

pytestmark = pytest.mark.unit


@pytest.mark.unit
class TestCreateBypassAuditEvent:
    """Tests for create_bypass_audit_event helper."""

    def test_creates_bypass_activated_event(self):
        """Should create BYPASS_ACTIVATED event with correct fields."""
        # GIVEN: User info and session context
        current_user = {
            "user_id": "user:alice",
            "username": "alice",
            "org_id": "org-123",
            "roles": ["developer"],
        }

        # WHEN: Creating a bypass activated event
        event = create_bypass_audit_event(
            event_type=AuditEventType.BYPASS_ACTIVATED,
            current_user=current_user,
            resource_type="session",
            resource_id="session-456",
            action="Activated risk-aware bypass execution mode",
            details={"execution_mode": "bypass"},
        )

        # THEN: Event should have correct structure
        assert isinstance(event, UnifiedAuditEvent)
        assert event.category == AuditEventCategory.SYSTEM
        assert event.event_type == AuditEventType.BYPASS_ACTIVATED
        assert event.actor.actor_id == "user:alice"
        assert event.actor.actor_type == "user"
        assert event.actor.username == "alice"
        assert event.actor.organization_id == "org-123"
        assert event.actor.roles == ["developer"]
        assert event.resource_type == "session"
        assert event.resource_id == "session-456"
        assert event.action == "Activated risk-aware bypass execution mode"
        assert event.outcome == "success"
        assert event.details == {"execution_mode": "bypass"}
        assert "SOC2" in event.regulation_tags
        assert "FedRAMP" in event.regulation_tags

    def test_creates_bypass_auto_approved_event(self):
        """Should create BYPASS_AUTO_APPROVED event with plan details."""
        # GIVEN: User and plan info
        current_user = {
            "user_id": "user:alice",
            "preferred_username": "alice",
        }

        # WHEN: Creating an auto-approved event
        event = create_bypass_audit_event(
            event_type=AuditEventType.BYPASS_AUTO_APPROVED,
            current_user=current_user,
            resource_type="execution_plan",
            resource_id="plan-789",
            action="Auto-approved low-risk plan in bypass mode",
            details={
                "risk_level": "low",
                "complexity": "simple",
                "tools_needed": ["read_file"],
            },
        )

        # THEN: Event should have execution_plan resource
        assert event.event_type == AuditEventType.BYPASS_AUTO_APPROVED
        assert event.resource_type == "execution_plan"
        assert event.resource_id == "plan-789"
        assert event.details["risk_level"] == "low"
        assert event.details["complexity"] == "simple"

    def test_creates_bypass_user_approved_event(self):
        """Should create BYPASS_USER_APPROVED event."""
        # GIVEN: User info
        current_user = {"user_id": "user:bob", "username": "bob"}

        # WHEN: Creating a user-approved event
        event = create_bypass_audit_event(
            event_type=AuditEventType.BYPASS_USER_APPROVED,
            current_user=current_user,
            resource_type="execution_plan",
            resource_id="plan-101",
            action="User approved plan in bypass mode",
            details={"risk_level": "medium"},
        )

        # THEN: Event should have correct type
        assert event.event_type == AuditEventType.BYPASS_USER_APPROVED
        assert event.actor.actor_id == "user:bob"

    def test_creates_bypass_rejected_event(self):
        """Should create BYPASS_REJECTED event."""
        # GIVEN: User info
        current_user = {"user_id": "user:alice", "username": "alice"}

        # WHEN: Creating a rejected event
        event = create_bypass_audit_event(
            event_type=AuditEventType.BYPASS_REJECTED,
            current_user=current_user,
            resource_type="execution_plan",
            resource_id="plan-102",
            action="User rejected plan in bypass mode",
            details={"rejection_reason": "Too risky"},
        )

        # THEN: Event should have correct type
        assert event.event_type == AuditEventType.BYPASS_REJECTED
        assert event.details["rejection_reason"] == "Too risky"

    def test_uses_preferred_username_fallback(self):
        """Should use preferred_username when username is not available."""
        # GIVEN: User with only preferred_username
        current_user = {
            "user_id": "user:charlie",
            "preferred_username": "charlie.smith",
        }

        # WHEN: Creating an event
        event = create_bypass_audit_event(
            event_type=AuditEventType.BYPASS_ACTIVATED,
            current_user=current_user,
            resource_type="session",
            resource_id="session-1",
            action="Activated bypass mode",
        )

        # THEN: Should use preferred_username
        assert event.actor.username == "charlie.smith"

    def test_handles_missing_optional_fields(self):
        """Should handle missing optional user fields gracefully."""
        # GIVEN: Minimal user info
        current_user = {"user_id": "user:minimal"}

        # WHEN: Creating an event
        event = create_bypass_audit_event(
            event_type=AuditEventType.BYPASS_ACTIVATED,
            current_user=current_user,
            resource_type="session",
            resource_id="session-2",
            action="Activated bypass mode",
        )

        # THEN: Should handle missing fields
        assert event.actor.actor_id == "user:minimal"
        assert event.actor.username is None
        assert event.actor.organization_id is None
        assert event.actor.roles == []

    def test_defaults_to_empty_details(self):
        """Should default to empty details dict when not provided."""
        # GIVEN: User info
        current_user = {"user_id": "user:test"}

        # WHEN: Creating an event without details
        event = create_bypass_audit_event(
            event_type=AuditEventType.BYPASS_ACTIVATED,
            current_user=current_user,
            resource_type="session",
            resource_id="session-3",
            action="Activated bypass mode",
        )

        # THEN: Details should be empty dict
        assert event.details == {}


@pytest.mark.unit
@pytest.mark.asyncio
class TestLogBypassAuditEvent:
    """Tests for log_bypass_audit_event async helper."""

    async def test_logs_event_when_audit_service_provided(self):
        """Should log event when audit_service is available."""
        # GIVEN: Audit service mock
        audit_service = AsyncMock(return_value=None)
        current_user = {"user_id": "user:alice", "username": "alice"}

        # WHEN: Logging a bypass event
        await log_bypass_audit_event(
            audit_service=audit_service,
            event_type=AuditEventType.BYPASS_ACTIVATED,
            current_user=current_user,
            resource_type="session",
            resource_id="session-1",
            action="Activated bypass mode",
        )

        # THEN: Audit service should be called
        audit_service.log_event.assert_called_once()
        event = audit_service.log_event.call_args[0][0]
        assert isinstance(event, UnifiedAuditEvent)
        assert event.event_type == AuditEventType.BYPASS_ACTIVATED

    async def test_skips_logging_when_audit_service_is_none(self):
        """Should gracefully skip when audit_service is None."""
        # GIVEN: No audit service
        current_user = {"user_id": "user:alice"}

        # WHEN: Logging with None audit_service
        # THEN: Should not raise
        await log_bypass_audit_event(
            audit_service=None,
            event_type=AuditEventType.BYPASS_ACTIVATED,
            current_user=current_user,
            resource_type="session",
            resource_id="session-1",
            action="Activated bypass mode",
        )
        # No assertion needed - just verify no exception

    async def test_handles_audit_service_exception(self):
        """Should not propagate audit service exceptions."""
        # GIVEN: Audit service that raises
        audit_service = AsyncMock(return_value=None)
        audit_service.log_event.side_effect = Exception("Audit DB error")
        current_user = {"user_id": "user:alice"}

        # WHEN: Logging fails
        # THEN: Should not raise
        await log_bypass_audit_event(
            audit_service=audit_service,
            event_type=AuditEventType.BYPASS_ACTIVATED,
            current_user=current_user,
            resource_type="session",
            resource_id="session-1",
            action="Activated bypass mode",
        )
        # No assertion needed - just verify no exception

    async def test_passes_all_details_to_event(self):
        """Should pass through all details to the event."""
        # GIVEN: Audit service and details
        audit_service = AsyncMock(return_value=None)
        current_user = {"user_id": "user:alice", "username": "alice"}
        details = {
            "risk_level": "medium",
            "complexity": "complicated",
            "tools_needed": ["execute_python"],
            "original_risk_level": "low",
        }

        # WHEN: Logging with details
        await log_bypass_audit_event(
            audit_service=audit_service,
            event_type=AuditEventType.BYPASS_AUTO_APPROVED,
            current_user=current_user,
            resource_type="execution_plan",
            resource_id="plan-1",
            action="Auto-approved",
            details=details,
        )

        # THEN: Event should have all details
        event = audit_service.log_event.call_args[0][0]
        assert event.details["risk_level"] == "medium"
        assert event.details["complexity"] == "complicated"
        assert event.details["original_risk_level"] == "low"


@pytest.mark.unit
@pytest.mark.asyncio
class TestLogBypassAuditEventPrometheusMetrics:
    """Tests for Prometheus metrics recording during bypass audit logging."""

    async def test_records_bypass_activation_metric(self, mocker):
        """GIVEN a BYPASS_ACTIVATED event
        WHEN log_bypass_audit_event is called
        THEN record_bypass_activation should be called with user ID.
        """
        mock_record = mocker.patch("mcp_server_langgraph.execution.bypass_audit.record_bypass_activation")
        audit_service = AsyncMock(return_value=None)
        current_user = {"user_id": "user:alice", "username": "alice"}

        await log_bypass_audit_event(
            audit_service=audit_service,
            event_type=AuditEventType.BYPASS_ACTIVATED,
            current_user=current_user,
            resource_type="session",
            resource_id="session-1",
            action="Activated bypass mode",
        )

        mock_record.assert_called_once_with(user="user:alice")

    async def test_records_bypass_auto_approval_metric(self, mocker):
        """GIVEN a BYPASS_AUTO_APPROVED event with risk_level and complexity
        WHEN log_bypass_audit_event is called
        THEN record_bypass_approval should be called with 'auto' type.
        """
        mock_record = mocker.patch("mcp_server_langgraph.execution.bypass_audit.record_bypass_approval")
        audit_service = AsyncMock(return_value=None)
        current_user = {"user_id": "user:alice"}

        await log_bypass_audit_event(
            audit_service=audit_service,
            event_type=AuditEventType.BYPASS_AUTO_APPROVED,
            current_user=current_user,
            resource_type="execution_plan",
            resource_id="plan-1",
            action="Auto-approved",
            details={"risk_level": "low", "complexity": "simple"},
        )

        mock_record.assert_called_once_with(
            approval_type="auto",
            risk_level="low",
            complexity="simple",
        )

    async def test_records_bypass_user_approval_metric(self, mocker):
        """GIVEN a BYPASS_USER_APPROVED event with risk_level and complexity
        WHEN log_bypass_audit_event is called
        THEN record_bypass_approval should be called with 'user' type.
        """
        mock_record = mocker.patch("mcp_server_langgraph.execution.bypass_audit.record_bypass_approval")
        audit_service = AsyncMock(return_value=None)
        current_user = {"user_id": "user:bob"}

        await log_bypass_audit_event(
            audit_service=audit_service,
            event_type=AuditEventType.BYPASS_USER_APPROVED,
            current_user=current_user,
            resource_type="execution_plan",
            resource_id="plan-2",
            action="User approved",
            details={"risk_level": "medium", "complexity": "complicated"},
        )

        mock_record.assert_called_once_with(
            approval_type="user",
            risk_level="medium",
            complexity="complicated",
        )

    async def test_records_bypass_rejection_metric(self, mocker):
        """GIVEN a BYPASS_REJECTED event with risk_level and complexity
        WHEN log_bypass_audit_event is called
        THEN record_bypass_rejection should be called.
        """
        mock_record = mocker.patch("mcp_server_langgraph.execution.bypass_audit.record_bypass_rejection")
        audit_service = AsyncMock(return_value=None)
        current_user = {"user_id": "user:alice"}

        await log_bypass_audit_event(
            audit_service=audit_service,
            event_type=AuditEventType.BYPASS_REJECTED,
            current_user=current_user,
            resource_type="execution_plan",
            resource_id="plan-3",
            action="Rejected",
            details={"risk_level": "high", "complexity": "complex"},
        )

        mock_record.assert_called_once_with(
            risk_level="high",
            complexity="complex",
        )

    async def test_metrics_recorded_even_when_audit_service_is_none(self, mocker):
        """GIVEN audit_service is None
        WHEN log_bypass_audit_event is called
        THEN Prometheus metrics should STILL be recorded.
        """
        mock_record = mocker.patch("mcp_server_langgraph.execution.bypass_audit.record_bypass_activation")
        current_user = {"user_id": "user:alice"}

        await log_bypass_audit_event(
            audit_service=None,
            event_type=AuditEventType.BYPASS_ACTIVATED,
            current_user=current_user,
            resource_type="session",
            resource_id="session-1",
            action="Activated bypass mode",
        )

        # Metrics should be recorded even without audit service
        mock_record.assert_called_once_with(user="user:alice")

    async def test_no_metrics_for_unknown_event_type(self, mocker):
        """GIVEN an event type not related to bypass
        WHEN log_bypass_audit_event is called
        THEN no bypass metrics should be recorded.
        """
        mock_activation = mocker.patch("mcp_server_langgraph.execution.bypass_audit.record_bypass_activation")
        mock_approval = mocker.patch("mcp_server_langgraph.execution.bypass_audit.record_bypass_approval")
        mock_rejection = mocker.patch("mcp_server_langgraph.execution.bypass_audit.record_bypass_rejection")
        audit_service = AsyncMock(return_value=None)
        current_user = {"user_id": "user:alice"}

        # Use SANDBOXED_EXECUTION_AUTO_ALLOWED which is not one of the 4 bypass types
        await log_bypass_audit_event(
            audit_service=audit_service,
            event_type=AuditEventType.SANDBOXED_EXECUTION_AUTO_ALLOWED,
            current_user=current_user,
            resource_type="execution",
            resource_id="exec-1",
            action="Sandboxed execution",
        )

        mock_activation.assert_not_called()
        mock_approval.assert_not_called()
        mock_rejection.assert_not_called()
