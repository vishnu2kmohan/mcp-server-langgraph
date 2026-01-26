"""
E2E Compliance Journey Tests.

Tests end-to-end compliance workflows for regulatory frameworks:
- GDPR: Data access and erasure rights (Articles 15, 17)
- HIPAA: Audit controls for ePHI access (45 CFR 164.312(b))
- SOC 2: Access controls and system operations (CC6.x, CC7.x)
- FedRAMP: Audit log management (NIST 800-53 AU controls)
- EU AI Act: AI operation logging (Articles 12, 19, 72)

Each journey tests a realistic compliance scenario from start to finish.
"""

import gc
from datetime import UTC, datetime
from unittest.mock import AsyncMock, MagicMock

import pytest

pytestmark = pytest.mark.e2e


@pytest.mark.e2e
@pytest.mark.compliance
@pytest.mark.xdist_group(name="compliance_journey")
class TestGDPRComplianceJourney:
    """
    GDPR Compliance Journey Tests.

    Scenario: A data subject requests access to their data (Art. 15)
    and later requests erasure (Art. 17).
    """

    def teardown_method(self) -> None:
        """Force GC to prevent mock accumulation in xdist workers."""
        gc.collect()

    @pytest.mark.asyncio
    async def test_gdpr_data_access_request_audit_trail(self) -> None:
        """
        GIVEN a user's data access request
        WHEN the request is processed
        THEN audit trail captures all access events with GDPR tagging.
        """
        from mcp_server_langgraph.audit.constants import Regulation
        from mcp_server_langgraph.audit.models import (
            AuditActor,
            AuditContext,
            AuditEventCategory,
            AuditEventType,
            UnifiedAuditEvent,
        )
        from mcp_server_langgraph.audit.service import UnifiedAuditService

        # Setup mock repository
        mock_repo = MagicMock()
        mock_repo.create = AsyncMock(return_value=None)  # async-mock-configured
        mock_repo.query_by_actor = AsyncMock(return_value=[])

        service = UnifiedAuditService(
            repository=mock_repo,
            integrity_secret="test-secret",
        )

        # Simulate data access request processing
        data_subject_id = "user-12345"
        request_id = "gdpr-access-request-001"

        # Log data access event
        event = UnifiedAuditEvent(
            event_id="evt-gdpr-001",
            timestamp=datetime.now(UTC),
            category=AuditEventCategory.DATA_ACCESS,
            event_type=AuditEventType.DATA_EXPORT,
            actor=AuditActor(
                actor_id=data_subject_id,
                actor_type="user",
                username="user@example.com",
            ),
            resource_type="user_data",
            resource_id=data_subject_id,
            action="GDPR Article 15 data access request processed",
            outcome="success",
            context=AuditContext(request_id=request_id),
            regulation_tags=[Regulation.GDPR.value],
        )

        await service.log_event(event)

        # Verify event was logged with GDPR tag
        mock_repo.create.assert_called_once()
        logged_event = mock_repo.create.call_args[0][0]
        assert Regulation.GDPR.value in logged_event.regulation_tags

    @pytest.mark.asyncio
    async def test_gdpr_erasure_request_verification(self) -> None:
        """
        GIVEN a user's erasure request (Art. 17)
        WHEN the request is processed
        THEN audit logs track data deletion with proof.
        """
        from mcp_server_langgraph.audit.constants import Regulation
        from mcp_server_langgraph.audit.models import (
            AuditActor,
            AuditContext,
            AuditEventCategory,
            AuditEventType,
            UnifiedAuditEvent,
        )
        from mcp_server_langgraph.audit.service import UnifiedAuditService

        mock_repo = MagicMock()
        mock_repo.create = AsyncMock(return_value=None)  # async-mock-configured

        service = UnifiedAuditService(
            repository=mock_repo,
            integrity_secret="test-secret",
        )

        # Log erasure event
        event = UnifiedAuditEvent(
            event_id="evt-gdpr-002",
            timestamp=datetime.now(UTC),
            category=AuditEventCategory.DATA_MODIFICATION,
            event_type=AuditEventType.DATA_DELETE,
            actor=AuditActor(
                actor_id="admin-001",
                actor_type="service",  # Admin actions via service account
                username="admin@example.com",
            ),
            resource_type="user_data",
            resource_id="user-12345",
            action="GDPR Article 17 erasure request executed",
            outcome="success",
            context=AuditContext(request_id="gdpr-erasure-001"),
            regulation_tags=[Regulation.GDPR.value],
        )

        await service.log_event(event)

        # Verify deletion event logged
        mock_repo.create.assert_called_once()
        logged_event = mock_repo.create.call_args[0][0]
        assert logged_event.event_type == AuditEventType.DATA_DELETE


@pytest.mark.e2e
@pytest.mark.compliance
@pytest.mark.hipaa
@pytest.mark.xdist_group(name="compliance_journey")
class TestHIPAAComplianceJourney:
    """
    HIPAA Compliance Journey Tests.

    Scenario: Healthcare provider accesses patient ePHI,
    and audit logs capture the access for 6-year retention.
    """

    def teardown_method(self) -> None:
        """Force GC to prevent mock accumulation in xdist workers."""
        gc.collect()

    @pytest.mark.asyncio
    async def test_hipaa_ephi_access_logging(self) -> None:
        """
        GIVEN a healthcare provider accessing patient records
        WHEN the access occurs
        THEN audit log captures who/what/when per 45 CFR 164.312(b).
        """
        from mcp_server_langgraph.audit.constants import Regulation
        from mcp_server_langgraph.audit.models import (
            AuditActor,
            AuditContext,
            AuditEventCategory,
            AuditEventType,
            UnifiedAuditEvent,
        )
        from mcp_server_langgraph.audit.service import UnifiedAuditService

        mock_repo = MagicMock()
        mock_repo.create = AsyncMock(return_value=None)  # async-mock-configured

        service = UnifiedAuditService(
            repository=mock_repo,
            integrity_secret="hipaa-integrity-secret",
        )

        # Log ePHI access event
        event = UnifiedAuditEvent(
            event_id="evt-hipaa-001",
            timestamp=datetime.now(UTC),
            category=AuditEventCategory.DATA_ACCESS,
            event_type=AuditEventType.DATA_READ,
            actor=AuditActor(
                actor_id="provider-001",
                actor_type="user",  # Healthcare provider as user
                username="dr.smith@hospital.org",
                roles=["physician", "ehr_access"],
            ),
            resource_type="patient_record",
            resource_id="patient-mrn-54321",
            action="Accessed patient medical record for treatment",
            outcome="success",
            context=AuditContext(
                request_id="hipaa-req-001",
                ip_address="192.168.1.100",
                user_agent="EHR/2.0",
                session_id="session-12345",
            ),
            regulation_tags=[Regulation.HIPAA.value],
            retention_days=2190,  # 6 years for HIPAA
        )

        await service.log_event(event)

        # Verify HIPAA requirements met
        logged_event = mock_repo.create.call_args[0][0]
        assert Regulation.HIPAA.value in logged_event.regulation_tags
        assert logged_event.retention_days == 2190
        assert logged_event.actor.actor_type == "user"
        assert "physician" in logged_event.actor.roles

    @pytest.mark.asyncio
    async def test_hipaa_audit_trail_integrity(self) -> None:
        """
        GIVEN HIPAA audit logs
        WHEN verified for integrity
        THEN hash chain proves no tampering occurred.
        """
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

        secret = "hipaa-integrity-secret"
        builder = HashChainBuilder(secret=secret)

        # Create chain of events
        events = []
        for i in range(5):
            event = UnifiedAuditEvent(
                event_id=f"evt-hipaa-{i:03d}",
                timestamp=datetime.now(UTC),
                category=AuditEventCategory.DATA_ACCESS,
                event_type=AuditEventType.DATA_READ,
                actor=AuditActor(
                    actor_id="provider-001",
                    actor_type="user",  # Healthcare provider as user
                    username="dr.smith@hospital.org",
                ),
                resource_type="patient_record",
                resource_id=f"patient-{i:05d}",
                action=f"Accessed patient record {i}",
                outcome="success",
                context=AuditContext(request_id=f"hipaa-chain-{i:03d}"),
            )
            chained = builder.add_to_chain(event)
            events.append(chained)

        # Verify chain integrity
        result = verify_chain(events, secret)
        assert result.valid is True
        assert result.events_verified == 5


@pytest.mark.e2e
@pytest.mark.compliance
@pytest.mark.fedramp
@pytest.mark.xdist_group(name="compliance_journey")
class TestFedRAMPComplianceJourney:
    """
    FedRAMP Compliance Journey Tests.

    Scenario: Government system operations requiring
    NIST 800-53 AU control compliance.
    """

    def teardown_method(self) -> None:
        """Force GC to prevent mock accumulation in xdist workers."""
        gc.collect()

    @pytest.mark.asyncio
    async def test_fedramp_tamper_detection(self) -> None:
        """
        GIVEN audit logs with hash chain (AU-9)
        WHEN a log is tampered with
        THEN verification detects the tampering.
        """
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

        secret = "fedramp-integrity-secret"
        builder = HashChainBuilder(secret=secret)

        # Create chain of events
        events = []
        for i in range(3):
            event = UnifiedAuditEvent(
                event_id=f"evt-fedramp-{i:03d}",
                timestamp=datetime.now(UTC),
                category=AuditEventCategory.SYSTEM,
                event_type=AuditEventType.CONFIG_CHANGE,
                actor=AuditActor(
                    actor_id="admin-001",
                    actor_type="service",  # Admin via service account
                    username="admin@gov.agency",
                ),
                resource_type="configuration",
                resource_id=f"config-{i}",
                action=f"Configuration change {i}",
                outcome="success",
                context=AuditContext(request_id=f"fedramp-{i:03d}"),
            )
            chained = builder.add_to_chain(event)
            events.append(chained)

        # Tamper with middle event
        events[1] = UnifiedAuditEvent(
            event_id=events[1].event_id,
            timestamp=events[1].timestamp,
            category=events[1].category,
            event_type=events[1].event_type,
            actor=events[1].actor,
            resource_type=events[1].resource_type,
            resource_id=events[1].resource_id,
            action="TAMPERED ACTION",  # Changed!
            outcome=events[1].outcome,
            context=events[1].context,
            sequence_number=events[1].sequence_number,
            previous_hash=events[1].previous_hash,
            event_hash=events[1].event_hash,  # Hash no longer matches
        )

        # Verify detects tampering
        result = verify_chain(events, secret)
        assert result.valid is False
        assert len(result.errors) > 0

    @pytest.mark.asyncio
    async def test_fedramp_7_year_retention(self) -> None:
        """
        GIVEN FedRAMP requirements (AU-11)
        WHEN audit events are created
        THEN retention is set to 7 years (2555 days).
        """
        from mcp_server_langgraph.audit.constants import RetentionDays
        from mcp_server_langgraph.audit.models import (
            AuditActor,
            AuditContext,
            AuditEventCategory,
            AuditEventType,
            UnifiedAuditEvent,
        )

        event = UnifiedAuditEvent(
            event_id="evt-fedramp-retention",
            timestamp=datetime.now(UTC),
            category=AuditEventCategory.SYSTEM,
            event_type=AuditEventType.CONFIG_CHANGE,
            actor=AuditActor(
                actor_id="system",
                actor_type="system",
                username="system",
            ),
            resource_type="application",
            resource_id="mcp-server",
            action="System configuration update",
            outcome="success",
            context=AuditContext(request_id="fedramp-retention-001"),
            retention_days=RetentionDays.FEDRAMP.value,
        )

        assert event.retention_days == 2555  # 7 years


@pytest.mark.e2e
@pytest.mark.compliance
@pytest.mark.eu_ai_act
@pytest.mark.xdist_group(name="compliance_journey")
class TestEUAIActComplianceJourney:
    """
    EU AI Act Compliance Journey Tests.

    Scenario: AI system operations requiring logging
    per Articles 12, 19, 72.
    """

    def teardown_method(self) -> None:
        """Force GC to prevent mock accumulation in xdist workers."""
        gc.collect()

    @pytest.mark.asyncio
    async def test_eu_ai_act_model_invocation_logging(self) -> None:
        """
        GIVEN an AI model invocation
        WHEN the operation completes
        THEN detailed AI operation logs are captured.
        """
        from mcp_server_langgraph.audit.constants import Regulation
        from mcp_server_langgraph.audit.models import (
            AIOperationDetails,
            AuditActor,
            AuditContext,
            AuditEventCategory,
            AuditEventType,
            UnifiedAuditEvent,
        )
        from mcp_server_langgraph.audit.service import UnifiedAuditService

        mock_repo = MagicMock()
        mock_repo.create = AsyncMock(return_value=None)  # async-mock-configured

        service = UnifiedAuditService(
            repository=mock_repo,
            integrity_secret="ai-act-secret",
        )

        # Log AI operation with full details
        event = UnifiedAuditEvent(
            event_id="evt-ai-001",
            timestamp=datetime.now(UTC),
            category=AuditEventCategory.AI_OPERATION,
            event_type=AuditEventType.AI_INVOKE,
            actor=AuditActor(
                actor_id="user-001",
                actor_type="user",
                username="user@company.eu",
            ),
            resource_type="ai_model",
            resource_id="claude-3-opus",
            action="AI model invocation for content generation",
            outcome="success",
            context=AuditContext(request_id="ai-act-001"),
            ai_operation=AIOperationDetails(
                model_id="claude-3-opus-20240229",
                provider="anthropic",
                input_tokens=1500,
                output_tokens=500,
                latency_ms=2300,
                decision_type="content_generation",
            ),
            regulation_tags=[Regulation.EU_AI_ACT.value],
        )

        await service.log_event(event)

        # Verify EU AI Act compliance
        logged_event = mock_repo.create.call_args[0][0]
        assert Regulation.EU_AI_ACT.value in logged_event.regulation_tags
        assert logged_event.ai_operation is not None
        assert logged_event.ai_operation.model_id == "claude-3-opus-20240229"
        assert logged_event.ai_operation.provider == "anthropic"
        assert logged_event.ai_operation.input_tokens == 1500
        assert logged_event.ai_operation.output_tokens == 500
        assert logged_event.ai_operation.latency_ms == 2300


@pytest.mark.e2e
@pytest.mark.compliance
@pytest.mark.soc2
@pytest.mark.xdist_group(name="compliance_journey")
class TestSOC2ComplianceJourney:
    """
    SOC 2 Type II Compliance Journey Tests.

    Scenario: Access control and system operations
    per CC6.x and CC7.x controls.
    """

    def teardown_method(self) -> None:
        """Force GC to prevent mock accumulation in xdist workers."""
        gc.collect()

    @pytest.mark.asyncio
    async def test_soc2_access_control_logging(self) -> None:
        """
        GIVEN access control events (CC6.1)
        WHEN login attempt occurs
        THEN audit log captures authentication details.
        """
        from mcp_server_langgraph.audit.constants import Regulation
        from mcp_server_langgraph.audit.models import (
            AuditActor,
            AuditContext,
            AuditEventCategory,
            AuditEventType,
            UnifiedAuditEvent,
        )
        from mcp_server_langgraph.audit.service import UnifiedAuditService

        mock_repo = MagicMock()
        mock_repo.create = AsyncMock(return_value=None)  # async-mock-configured

        service = UnifiedAuditService(
            repository=mock_repo,
            integrity_secret="soc2-secret",
        )

        # Log successful login
        event = UnifiedAuditEvent(
            event_id="evt-soc2-001",
            timestamp=datetime.now(UTC),
            category=AuditEventCategory.AUTHENTICATION,
            event_type=AuditEventType.LOGIN_SUCCESS,
            actor=AuditActor(
                actor_id="user-001",
                actor_type="user",
                username="user@company.com",
                roles=["developer"],
            ),
            resource_type="session",
            resource_id="session-12345",
            action="User login via SSO",
            outcome="success",
            context=AuditContext(
                ip_address="203.0.113.50",
                user_agent="Mozilla/5.0...",
                request_id="req-abc123",
            ),
            regulation_tags=[Regulation.SOC2.value],
        )

        await service.log_event(event)

        # Verify SOC 2 requirements
        logged_event = mock_repo.create.call_args[0][0]
        assert Regulation.SOC2.value in logged_event.regulation_tags
        assert logged_event.category == AuditEventCategory.AUTHENTICATION
        assert logged_event.context.ip_address == "203.0.113.50"

    @pytest.mark.asyncio
    async def test_soc2_system_operations_logging(self) -> None:
        """
        GIVEN system operations (CC7.1)
        WHEN configuration changes occur
        THEN audit log captures admin actions.
        """
        from mcp_server_langgraph.audit.constants import Regulation
        from mcp_server_langgraph.audit.models import (
            AuditActor,
            AuditContext,
            AuditEventCategory,
            AuditEventType,
            UnifiedAuditEvent,
        )
        from mcp_server_langgraph.audit.service import UnifiedAuditService

        mock_repo = MagicMock()
        mock_repo.create = AsyncMock(return_value=None)  # async-mock-configured

        service = UnifiedAuditService(
            repository=mock_repo,
            integrity_secret="soc2-secret",
        )

        # Log configuration change
        event = UnifiedAuditEvent(
            event_id="evt-soc2-002",
            timestamp=datetime.now(UTC),
            category=AuditEventCategory.SYSTEM,
            event_type=AuditEventType.CONFIG_CHANGE,
            actor=AuditActor(
                actor_id="admin-001",
                actor_type="service",  # Admin actions via service account
                username="admin@company.com",
                roles=["platform_admin"],
            ),
            resource_type="configuration",
            resource_id="rate-limit-config",
            action="Updated rate limit from 100 to 200 req/min",
            outcome="success",
            context=AuditContext(request_id="soc2-config-001"),
            regulation_tags=[Regulation.SOC2.value],
        )

        await service.log_event(event)

        # Verify change tracking
        logged_event = mock_repo.create.call_args[0][0]
        assert logged_event.event_type == AuditEventType.CONFIG_CHANGE
        assert "platform_admin" in logged_event.actor.roles
