"""
GDPR Audit Logging Compliance Tests.

Validates compliance with EU General Data Protection Regulation:
- Article 5(1)(e): Storage limitation principle
- Article 30: Records of processing activities
- Article 15: Right of access (audit trail for data subject requests)
- Article 17: Right to erasure (audit trail for deletion requests)
- Article 20: Right to data portability (audit trail for export requests)
"""

import gc
from unittest.mock import AsyncMock

import pytest

from mcp_server_langgraph.audit.constants import Regulation, RetentionDays
from mcp_server_langgraph.audit.models import (
    AuditActor,
    AuditContext,
    AuditEventCategory,
    AuditEventType,
    UnifiedAuditEvent,
)
from mcp_server_langgraph.audit.service import UnifiedAuditService

pytestmark = pytest.mark.compliance


@pytest.mark.compliance
@pytest.mark.gdpr
@pytest.mark.xdist_group(name="compliance_gdpr")
class TestGDPRRecordsOfProcessing:
    """GDPR Article 30: Records of processing activities."""

    def teardown_method(self) -> None:
        """Force GC to prevent mock accumulation in xdist workers."""
        gc.collect()

    def test_audit_event_includes_processing_purpose(self) -> None:
        """GIVEN audit event WHEN created THEN processing purpose tracked."""
        event = UnifiedAuditEvent(
            category=AuditEventCategory.DATA_ACCESS,
            event_type=AuditEventType.DATA_READ,
            actor=AuditActor(actor_id="user:alice", actor_type="user"),
            resource_type="personal_data",
            resource_id="customer-123",
            action="Read customer profile",
            outcome="success",
            context=AuditContext(request_id="req-001"),
            details={"processing_purpose": "customer_support"},
        )

        assert event.details is not None
        assert "processing_purpose" in event.details

    def test_audit_event_includes_data_controller(self) -> None:
        """GIVEN audit event WHEN organization set THEN data controller tracked."""
        event = UnifiedAuditEvent(
            category=AuditEventCategory.DATA_ACCESS,
            event_type=AuditEventType.DATA_READ,
            actor=AuditActor(
                actor_id="user:processor",
                actor_type="user",
                organization_id="org:controller-inc",
            ),
            resource_type="personal_data",
            resource_id="customer-123",
            action="Process data",
            outcome="success",
            context=AuditContext(request_id="req-001"),
        )

        assert event.actor.organization_id == "org:controller-inc"

    def test_gdpr_regulation_tag_present(self) -> None:
        """GIVEN GDPR-relevant event WHEN logged THEN regulation tag included."""
        event = UnifiedAuditEvent(
            category=AuditEventCategory.DATA_ACCESS,
            event_type=AuditEventType.DATA_READ,
            actor=AuditActor(actor_id="user:alice", actor_type="user"),
            resource_type="personal_data",
            resource_id="customer-123",
            action="Access PII",
            outcome="success",
            context=AuditContext(request_id="req-001"),
            regulation_tags=[Regulation.GDPR],
        )

        assert Regulation.GDPR in event.regulation_tags


@pytest.mark.compliance
@pytest.mark.gdpr
@pytest.mark.xdist_group(name="compliance_gdpr")
class TestGDPRRetention:
    """GDPR Article 5(1)(e): Storage limitation."""

    def teardown_method(self) -> None:
        """Force GC to prevent mock accumulation in xdist workers."""
        gc.collect()

    def test_gdpr_retention_period_defined(self) -> None:
        """GIVEN GDPR regulation THEN 7-year retention defined."""
        assert RetentionDays.GDPR == 2555  # 7 years

    def test_audit_event_has_retention_days(self) -> None:
        """GIVEN audit event WHEN created THEN retention_days set."""
        event = UnifiedAuditEvent(
            category=AuditEventCategory.DATA_ACCESS,
            event_type=AuditEventType.DATA_READ,
            actor=AuditActor(actor_id="user:alice", actor_type="user"),
            resource_type="document",
            resource_id="doc-001",
            action="Read document",
            outcome="success",
            context=AuditContext(request_id="req-001"),
            retention_days=RetentionDays.GDPR,
        )

        assert event.retention_days == 2555


@pytest.mark.compliance
@pytest.mark.gdpr
@pytest.mark.xdist_group(name="compliance_gdpr")
class TestGDPRDataSubjectRights:
    """GDPR Articles 15, 17, 20: Data subject rights audit trail."""

    def teardown_method(self) -> None:
        """Force GC to prevent mock accumulation in xdist workers."""
        gc.collect()

    def test_access_request_audited(self) -> None:
        """GIVEN Article 15 access request WHEN processed THEN audited."""
        event = UnifiedAuditEvent(
            category=AuditEventCategory.COMPLIANCE,
            event_type=AuditEventType.GDPR_ACCESS_REQUEST,
            actor=AuditActor(actor_id="user:alice", actor_type="user"),
            resource_type="data_subject_request",
            resource_id="dsr-001",
            action="Data access request submitted",
            outcome="success",
            context=AuditContext(request_id="req-001"),
            regulation_tags=[Regulation.GDPR],
        )

        assert event.event_type == AuditEventType.GDPR_ACCESS_REQUEST
        assert event.category == AuditEventCategory.COMPLIANCE

    def test_deletion_request_audited(self) -> None:
        """GIVEN Article 17 deletion request WHEN processed THEN audited."""
        event = UnifiedAuditEvent(
            category=AuditEventCategory.COMPLIANCE,
            event_type=AuditEventType.GDPR_DELETION_REQUEST,
            actor=AuditActor(actor_id="user:alice", actor_type="user"),
            resource_type="data_subject_request",
            resource_id="dsr-002",
            action="Data deletion request submitted",
            outcome="success",
            context=AuditContext(request_id="req-001"),
            regulation_tags=[Regulation.GDPR],
        )

        assert event.event_type == AuditEventType.GDPR_DELETION_REQUEST

    def test_export_request_audited(self) -> None:
        """GIVEN Article 20 export request WHEN processed THEN audited."""
        event = UnifiedAuditEvent(
            category=AuditEventCategory.COMPLIANCE,
            event_type=AuditEventType.GDPR_EXPORT_REQUEST,
            actor=AuditActor(actor_id="user:alice", actor_type="user"),
            resource_type="data_subject_request",
            resource_id="dsr-003",
            action="Data export request submitted",
            outcome="success",
            context=AuditContext(request_id="req-001"),
            regulation_tags=[Regulation.GDPR],
        )

        assert event.event_type == AuditEventType.GDPR_EXPORT_REQUEST


@pytest.mark.compliance
@pytest.mark.gdpr
@pytest.mark.xdist_group(name="compliance_gdpr")
class TestGDPRQueryCapabilities:
    """GDPR compliance query requirements."""

    def teardown_method(self) -> None:
        """Force GC to prevent mock accumulation in xdist workers."""
        gc.collect()

    @pytest.mark.asyncio
    async def test_query_by_gdpr_regulation(self) -> None:
        """GIVEN audit events WHEN queried by GDPR THEN filtered correctly."""
        mock_repo = AsyncMock()  # async-mock-configured
        mock_repo.query_by_regulation = AsyncMock(return_value=[])

        service = UnifiedAuditService(
            repository=mock_repo,
            integrity_secret="test-secret",
        )

        await service.query_by_regulation(Regulation.GDPR)

        mock_repo.query_by_regulation.assert_called_once()
        call_args = mock_repo.query_by_regulation.call_args
        assert call_args[0][0] == Regulation.GDPR
