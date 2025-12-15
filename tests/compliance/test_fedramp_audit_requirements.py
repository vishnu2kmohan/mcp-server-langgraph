"""
FedRAMP Audit Logging Compliance Tests.

Validates compliance with Federal Risk and Authorization Management:
- AU-2: Audit Events
- AU-3: Content of Audit Records
- AU-5: Response to Audit Processing Failures
- AU-9: Protection of Audit Information
- AU-11: Audit Record Retention
"""

import gc
from unittest.mock import AsyncMock

import pytest

from mcp_server_langgraph.audit.constants import Regulation, RetentionDays
from mcp_server_langgraph.audit.integrity import (
    HashChainBuilder,
    verify_chain,
)
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
@pytest.mark.fedramp
@pytest.mark.xdist_group(name="compliance_fedramp")
class TestFedRAMPAuditEvents:
    """AU-2: Audit Events."""

    def teardown_method(self) -> None:
        """Force GC to prevent mock accumulation in xdist workers."""
        gc.collect()

    def test_authentication_events_audited(self) -> None:
        """GIVEN authentication event WHEN logged THEN AU-2 compliant."""
        event = UnifiedAuditEvent(
            category=AuditEventCategory.AUTHENTICATION,
            event_type=AuditEventType.LOGIN_SUCCESS,
            actor=AuditActor(actor_id="user:federal-employee", actor_type="user"),
            resource_type="session",
            resource_id="sess-001",
            action="User login",
            outcome="success",
            context=AuditContext(request_id="req-001"),
            regulation_tags=[Regulation.FEDRAMP],
        )

        assert event.category == AuditEventCategory.AUTHENTICATION
        assert Regulation.FEDRAMP in event.regulation_tags

    def test_data_access_events_audited(self) -> None:
        """GIVEN data access event WHEN logged THEN AU-2 compliant."""
        event = UnifiedAuditEvent(
            category=AuditEventCategory.DATA_ACCESS,
            event_type=AuditEventType.DATA_READ,
            actor=AuditActor(actor_id="user:federal-employee", actor_type="user"),
            resource_type="document",
            resource_id="doc-classified-001",
            action="Read document",
            outcome="success",
            context=AuditContext(request_id="req-001"),
            regulation_tags=[Regulation.FEDRAMP],
        )

        assert event.category == AuditEventCategory.DATA_ACCESS


@pytest.mark.compliance
@pytest.mark.fedramp
@pytest.mark.xdist_group(name="compliance_fedramp")
class TestFedRAMPAuditContent:
    """AU-3: Content of Audit Records."""

    def teardown_method(self) -> None:
        """Force GC to prevent mock accumulation in xdist workers."""
        gc.collect()

    def test_audit_contains_who(self) -> None:
        """GIVEN audit event THEN WHO is captured (AU-3)."""
        event = UnifiedAuditEvent(
            category=AuditEventCategory.DATA_ACCESS,
            event_type=AuditEventType.DATA_READ,
            actor=AuditActor(
                actor_id="user:jane-doe",
                actor_type="user",
                username="jane.doe",
            ),
            resource_type="document",
            resource_id="doc-001",
            action="Read document",
            outcome="success",
            context=AuditContext(request_id="req-001"),
        )

        assert event.actor.actor_id is not None
        assert event.actor.username is not None

    def test_audit_contains_what(self) -> None:
        """GIVEN audit event THEN WHAT is captured (AU-3)."""
        event = UnifiedAuditEvent(
            category=AuditEventCategory.DATA_MODIFICATION,
            event_type=AuditEventType.DATA_UPDATE,
            actor=AuditActor(actor_id="user:admin", actor_type="user"),
            resource_type="configuration",
            resource_id="security-policy",
            action="Update security policy",
            outcome="success",
            context=AuditContext(request_id="req-001"),
        )

        assert event.action is not None
        assert event.resource_type is not None
        assert event.resource_id is not None

    def test_audit_contains_when(self) -> None:
        """GIVEN audit event THEN WHEN is captured (AU-3)."""
        event = UnifiedAuditEvent(
            category=AuditEventCategory.DATA_ACCESS,
            event_type=AuditEventType.DATA_READ,
            actor=AuditActor(actor_id="user:admin", actor_type="user"),
            resource_type="document",
            resource_id="doc-001",
            action="Read document",
            outcome="success",
            context=AuditContext(request_id="req-001"),
        )

        assert event.timestamp is not None

    def test_audit_contains_where(self) -> None:
        """GIVEN audit event THEN WHERE is captured (AU-3)."""
        event = UnifiedAuditEvent(
            category=AuditEventCategory.DATA_ACCESS,
            event_type=AuditEventType.DATA_READ,
            actor=AuditActor(actor_id="user:admin", actor_type="user"),
            resource_type="document",
            resource_id="doc-001",
            action="Read document",
            outcome="success",
            context=AuditContext(
                request_id="req-001",
                ip_address="10.0.1.50",
                trace_id="abc123",
            ),
        )

        assert event.context.ip_address is not None
        assert event.context.trace_id is not None


@pytest.mark.compliance
@pytest.mark.fedramp
@pytest.mark.xdist_group(name="compliance_fedramp")
class TestFedRAMPIntegrity:
    """AU-9: Protection of Audit Information."""

    def teardown_method(self) -> None:
        """Force GC to prevent mock accumulation in xdist workers."""
        gc.collect()

    def test_hash_chain_protects_integrity(self) -> None:
        """GIVEN events with hash chain WHEN verified THEN integrity confirmed."""
        builder = HashChainBuilder(secret="federal-audit-secret")

        events = []
        for i in range(5):
            event = UnifiedAuditEvent(
                category=AuditEventCategory.DATA_ACCESS,
                event_type=AuditEventType.DATA_READ,
                actor=AuditActor(actor_id="user:fed-admin", actor_type="user"),
                resource_type="document",
                resource_id=f"doc-{i}",
                action="Read document",
                outcome="success",
                context=AuditContext(request_id=f"req-{i}"),
            )
            chained_event = builder.add_event(event)
            events.append(chained_event)

        result = verify_chain(events, secret="federal-audit-secret")

        assert result.valid is True
        assert result.events_verified == 5

    def test_tampering_detected_returns_failure_status(self) -> None:
        """GIVEN tampered event WHEN verified THEN tampering detected (AU-9)."""
        builder = HashChainBuilder(secret="federal-audit-secret")

        events = []
        for i in range(3):
            event = UnifiedAuditEvent(
                category=AuditEventCategory.DATA_ACCESS,
                event_type=AuditEventType.DATA_READ,
                actor=AuditActor(actor_id="user:admin", actor_type="user"),
                resource_type="document",
                resource_id=f"doc-{i}",
                action="Read document",
                outcome="success",
                context=AuditContext(request_id=f"req-{i}"),
            )
            chained_event = builder.add_event(event)
            events.append(chained_event)

        # Tamper with an event
        tampered_event = events[1].model_copy()
        tampered_event.action = "TAMPERED ACTION"
        events[1] = tampered_event

        result = verify_chain(events, secret="federal-audit-secret")

        assert result.valid is False


@pytest.mark.compliance
@pytest.mark.fedramp
@pytest.mark.xdist_group(name="compliance_fedramp")
class TestFedRAMPRetention:
    """AU-11: Audit Record Retention."""

    def teardown_method(self) -> None:
        """Force GC to prevent mock accumulation in xdist workers."""
        gc.collect()

    def test_fedramp_retention_period_defined(self) -> None:
        """GIVEN FedRAMP regulation THEN 7-year retention defined."""
        assert RetentionDays.FEDRAMP == 2555  # 7 years


@pytest.mark.compliance
@pytest.mark.fedramp
@pytest.mark.xdist_group(name="compliance_fedramp")
class TestFedRAMPQueryCapabilities:
    """FedRAMP compliance query requirements."""

    def teardown_method(self) -> None:
        """Force GC to prevent mock accumulation in xdist workers."""
        gc.collect()

    @pytest.mark.asyncio
    async def test_query_by_fedramp_regulation(self) -> None:
        """GIVEN audit events WHEN queried by FedRAMP THEN filtered correctly."""
        mock_repo = AsyncMock()  # async-mock-configured
        mock_repo.query_by_regulation = AsyncMock(return_value=[])

        service = UnifiedAuditService(
            repository=mock_repo,
            integrity_secret="test-secret",
        )

        await service.query_by_regulation(Regulation.FEDRAMP)

        mock_repo.query_by_regulation.assert_called_once()
        call_args = mock_repo.query_by_regulation.call_args
        assert call_args[0][0] == Regulation.FEDRAMP
