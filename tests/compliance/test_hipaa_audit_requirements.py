"""
HIPAA Audit Logging Compliance Tests.

Validates compliance with Health Insurance Portability and Accountability Act:
- 45 CFR 164.312(b): Audit controls for ePHI access
- 45 CFR 164.530(j): 6-year retention requirement
- 45 CFR 164.308(a)(1): Security management process
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

pytestmark = [pytest.mark.unit, pytest.mark.compliance]


@pytest.mark.compliance
@pytest.mark.hipaa
@pytest.mark.xdist_group(name="compliance_hipaa")
class TestHIPAAAuditControls:
    """45 CFR 164.312(b): Audit controls."""

    def teardown_method(self) -> None:
        """Force GC to prevent mock accumulation in xdist workers."""
        gc.collect()

    def test_phi_access_tracked(self) -> None:
        """GIVEN PHI access WHEN audited THEN all required fields present."""
        event = UnifiedAuditEvent(
            category=AuditEventCategory.DATA_ACCESS,
            event_type=AuditEventType.DATA_READ,
            actor=AuditActor(
                actor_id="user:dr-smith",
                actor_type="user",
                roles=["healthcare_provider"],
            ),
            resource_type="phi",
            resource_id="patient-record-123",
            action="Access patient record",
            outcome="success",
            context=AuditContext(
                request_id="req-001",
                ip_address="10.0.1.50",
                user_agent="EHR-System/2.0",
            ),
            regulation_tags=[Regulation.HIPAA],
        )

        # HIPAA requires WHO
        assert event.actor.actor_id is not None
        # HIPAA requires WHAT
        assert event.resource_type == "phi"
        # HIPAA requires WHEN
        assert event.timestamp is not None
        # HIPAA requires WHERE
        assert event.context.ip_address is not None

    def test_phi_modification_tracked(self) -> None:
        """GIVEN PHI modification WHEN audited THEN action logged."""
        event = UnifiedAuditEvent(
            category=AuditEventCategory.DATA_MODIFICATION,
            event_type=AuditEventType.DATA_UPDATE,
            actor=AuditActor(actor_id="user:nurse-jones", actor_type="user"),
            resource_type="phi",
            resource_id="patient-record-123",
            action="Update patient vitals",
            outcome="success",
            context=AuditContext(request_id="req-001"),
            regulation_tags=[Regulation.HIPAA],
            details={"fields_modified": ["blood_pressure", "heart_rate"]},
        )

        assert event.category == AuditEventCategory.DATA_MODIFICATION
        assert Regulation.HIPAA in event.regulation_tags


@pytest.mark.compliance
@pytest.mark.hipaa
@pytest.mark.xdist_group(name="compliance_hipaa")
class TestHIPAARetention:
    """45 CFR 164.530(j): 6-year retention requirement."""

    def teardown_method(self) -> None:
        """Force GC to prevent mock accumulation in xdist workers."""
        gc.collect()

    def test_hipaa_retention_period_defined(self) -> None:
        """GIVEN HIPAA regulation THEN 6-year retention defined."""
        assert RetentionDays.HIPAA == 2190  # 6 years

    def test_phi_audit_has_retention_days(self) -> None:
        """GIVEN PHI audit event WHEN created THEN retention_days set."""
        event = UnifiedAuditEvent(
            category=AuditEventCategory.DATA_ACCESS,
            event_type=AuditEventType.DATA_READ,
            actor=AuditActor(actor_id="user:dr-smith", actor_type="user"),
            resource_type="phi",
            resource_id="patient-123",
            action="Access PHI",
            outcome="success",
            context=AuditContext(request_id="req-001"),
            retention_days=RetentionDays.HIPAA,
        )

        assert event.retention_days == 2190


@pytest.mark.compliance
@pytest.mark.hipaa
@pytest.mark.xdist_group(name="compliance_hipaa")
class TestHIPAASecurityManagement:
    """45 CFR 164.308(a)(1): Security management process."""

    def teardown_method(self) -> None:
        """Force GC to prevent mock accumulation in xdist workers."""
        gc.collect()

    def test_failed_access_logged(self) -> None:
        """GIVEN failed PHI access attempt WHEN audited THEN logged."""
        event = UnifiedAuditEvent(
            category=AuditEventCategory.AUTHORIZATION,
            event_type=AuditEventType.ACCESS_DENIED,
            actor=AuditActor(actor_id="user:unauthorized", actor_type="user"),
            resource_type="phi",
            resource_id="patient-456",
            action="Attempted PHI access",
            outcome="denied",
            context=AuditContext(request_id="req-001"),
            regulation_tags=[Regulation.HIPAA],
        )

        assert event.outcome == "denied"
        assert event.event_type == AuditEventType.ACCESS_DENIED

    def test_security_incident_logged(self) -> None:
        """GIVEN security incident WHEN detected THEN logged with details."""
        event = UnifiedAuditEvent(
            category=AuditEventCategory.SECURITY,
            event_type=AuditEventType.THREAT_DETECTED,
            actor=AuditActor(actor_id="system:security", actor_type="service"),
            resource_type="system",
            resource_id="security-monitor",
            action="Security incident detected",
            outcome="success",
            context=AuditContext(request_id="incident-001"),
            regulation_tags=[Regulation.HIPAA],
            details={
                "incident_type": "multiple_failed_logins",
                "source_ip": "10.0.1.100",
                "attempts": 10,
            },
        )

        assert event.category == AuditEventCategory.SECURITY
        assert event.details is not None
        assert "incident_type" in event.details


@pytest.mark.compliance
@pytest.mark.hipaa
@pytest.mark.xdist_group(name="compliance_hipaa")
class TestHIPAAQueryCapabilities:
    """HIPAA compliance query requirements."""

    def teardown_method(self) -> None:
        """Force GC to prevent mock accumulation in xdist workers."""
        gc.collect()

    @pytest.mark.asyncio
    async def test_query_by_hipaa_regulation(self) -> None:
        """GIVEN audit events WHEN queried by HIPAA THEN filtered correctly."""
        mock_repo = AsyncMock()  # async-mock-configured
        mock_repo.query_by_regulation = AsyncMock(return_value=[])

        service = UnifiedAuditService(
            repository=mock_repo,
            integrity_secret="test-secret",
        )

        await service.query_by_regulation(Regulation.HIPAA)

        mock_repo.query_by_regulation.assert_called_once()
        call_args = mock_repo.query_by_regulation.call_args
        assert call_args[0][0] == Regulation.HIPAA
