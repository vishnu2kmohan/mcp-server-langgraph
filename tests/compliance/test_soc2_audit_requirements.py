"""
SOC 2 Type II Audit Logging Compliance Tests.

Validates compliance with Service Organization Controls:
- CC6.1-CC6.8: Logical and physical access controls
- CC7.1-CC7.5: System operations monitoring
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
@pytest.mark.soc2
@pytest.mark.xdist_group(name="compliance_soc2")
class TestSOC2AccessControls:
    """CC6.x: Logical and physical access controls."""

    def teardown_method(self) -> None:
        """Force GC to prevent mock accumulation in xdist workers."""
        gc.collect()

    def test_login_success_logged(self) -> None:
        """GIVEN successful login WHEN audited THEN CC6.1 compliant."""
        event = UnifiedAuditEvent(
            category=AuditEventCategory.AUTHENTICATION,
            event_type=AuditEventType.LOGIN_SUCCESS,
            actor=AuditActor(actor_id="user:alice", actor_type="user"),
            resource_type="session",
            resource_id="sess-001",
            action="User login",
            outcome="success",
            context=AuditContext(request_id="req-001"),
            regulation_tags=[Regulation.SOC2],
        )

        assert event.category == AuditEventCategory.AUTHENTICATION
        assert event.outcome == "success"

    def test_login_failure_logged(self) -> None:
        """GIVEN failed login WHEN audited THEN CC6.1 compliant."""
        event = UnifiedAuditEvent(
            category=AuditEventCategory.AUTHENTICATION,
            event_type=AuditEventType.LOGIN_FAILED,
            actor=AuditActor(actor_id="user:unknown", actor_type="user"),
            resource_type="session",
            resource_id="sess-001",
            action="User login attempt",
            outcome="failure",
            context=AuditContext(request_id="req-001"),
            regulation_tags=[Regulation.SOC2],
        )

        assert event.event_type == AuditEventType.LOGIN_FAILED
        assert event.outcome == "failure"

    def test_permission_change_logged(self) -> None:
        """GIVEN permission change WHEN audited THEN CC6.3 compliant."""
        event = UnifiedAuditEvent(
            category=AuditEventCategory.AUTHORIZATION,
            event_type=AuditEventType.ROLE_ASSIGNED,
            actor=AuditActor(actor_id="user:admin", actor_type="user"),
            resource_type="user",
            resource_id="user:bob",
            action="Grant admin role",
            outcome="success",
            context=AuditContext(request_id="req-001"),
            regulation_tags=[Regulation.SOC2],
            details={"role_granted": "admin"},
        )

        assert event.event_type == AuditEventType.ROLE_ASSIGNED
        assert Regulation.SOC2 in event.regulation_tags


@pytest.mark.compliance
@pytest.mark.soc2
@pytest.mark.xdist_group(name="compliance_soc2")
class TestSOC2SystemOperations:
    """CC7.x: System operations monitoring."""

    def teardown_method(self) -> None:
        """Force GC to prevent mock accumulation in xdist workers."""
        gc.collect()

    def test_configuration_change_logged(self) -> None:
        """GIVEN config change WHEN audited THEN CC7.1 compliant."""
        event = UnifiedAuditEvent(
            category=AuditEventCategory.SYSTEM,
            event_type=AuditEventType.CONFIG_CHANGE,
            actor=AuditActor(actor_id="user:sysadmin", actor_type="user"),
            resource_type="configuration",
            resource_id="rate-limits",
            action="Update rate limits",
            outcome="success",
            context=AuditContext(request_id="req-001"),
            regulation_tags=[Regulation.SOC2],
            details={
                "old_value": "100",
                "new_value": "200",
            },
        )

        assert event.category == AuditEventCategory.SYSTEM
        assert event.event_type == AuditEventType.CONFIG_CHANGE

    def test_system_error_logged(self) -> None:
        """GIVEN system error WHEN audited THEN CC7.2 compliant."""
        event = UnifiedAuditEvent(
            category=AuditEventCategory.SECURITY,
            event_type=AuditEventType.THREAT_DETECTED,
            actor=AuditActor(actor_id="system:monitor", actor_type="service"),
            resource_type="service",
            resource_id="api-gateway",
            action="Service error detected",
            outcome="error",
            context=AuditContext(request_id="monitor-001"),
            regulation_tags=[Regulation.SOC2],
            details={"error_code": "503", "service": "api-gateway"},
        )

        assert event.event_type == AuditEventType.THREAT_DETECTED
        assert event.outcome == "error"


@pytest.mark.compliance
@pytest.mark.soc2
@pytest.mark.xdist_group(name="compliance_soc2")
class TestSOC2Retention:
    """SOC 2 retention requirements."""

    def teardown_method(self) -> None:
        """Force GC to prevent mock accumulation in xdist workers."""
        gc.collect()

    def test_soc2_retention_period_defined(self) -> None:
        """GIVEN SOC 2 regulation THEN 3-year retention defined."""
        assert RetentionDays.SOC2 == 1095  # 3 years


@pytest.mark.compliance
@pytest.mark.soc2
@pytest.mark.xdist_group(name="compliance_soc2")
class TestSOC2QueryCapabilities:
    """SOC 2 compliance query requirements."""

    def teardown_method(self) -> None:
        """Force GC to prevent mock accumulation in xdist workers."""
        gc.collect()

    @pytest.mark.asyncio
    async def test_query_by_soc2_regulation(self) -> None:
        """GIVEN audit events WHEN queried by SOC 2 THEN filtered correctly."""
        mock_repo = AsyncMock()  # async-mock-configured
        mock_repo.query_by_regulation = AsyncMock(return_value=[])

        service = UnifiedAuditService(
            repository=mock_repo,
            integrity_secret="test-secret",
        )

        await service.query_by_regulation(Regulation.SOC2)

        mock_repo.query_by_regulation.assert_called_once()
        call_args = mock_repo.query_by_regulation.call_args
        assert call_args[0][0] == Regulation.SOC2
