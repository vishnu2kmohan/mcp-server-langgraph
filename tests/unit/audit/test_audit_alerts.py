"""
Tests for audit alerting system (FedRAMP AU-5).

TDD RED phase: These tests define expected behavior for audit alerts.

The alerting system should:
- Detect audit logging failures
- Detect multiple failed login attempts
- Detect unusual data access patterns
- Detect after-hours admin actions
- Detect bulk data exports
- Detect hash chain tampering
"""

import gc
from datetime import UTC, datetime

import pytest

pytestmark = pytest.mark.unit


@pytest.mark.unit
@pytest.mark.xdist_group(name="audit_alerts")
class TestAuditAlertDetection:
    """Tests for alert detection logic."""

    def teardown_method(self) -> None:
        """Force GC to prevent mock accumulation in xdist workers."""
        gc.collect()

    def test_detect_failed_login_threshold(self) -> None:
        """GIVEN multiple failed logins WHEN checking THEN alert triggered."""
        from mcp_server_langgraph.audit.alerts import AuditAlertDetector
        from mcp_server_langgraph.audit.models import (
            AuditActor,
            AuditContext,
            AuditEventCategory,
            AuditEventType,
            UnifiedAuditEvent,
        )

        detector = AuditAlertDetector(
            failed_login_threshold=3,
            failed_login_window_minutes=5,
        )

        # Simulate 5 failed login attempts
        for i in range(5):
            event = UnifiedAuditEvent(
                category=AuditEventCategory.AUTHENTICATION,
                event_type=AuditEventType.LOGIN_FAILED,
                actor=AuditActor(actor_id="user:attacker", actor_type="user"),
                resource_type="session",
                resource_id=f"attempt-{i}",
                action="Login attempt",
                outcome="failure",
                context=AuditContext(request_id=f"req-{i}", ip_address="192.168.1.100"),
            )
            detector.process_event(event)

        alerts = detector.get_triggered_alerts()

        assert len(alerts) > 0
        assert any(a.alert_type == "FAILED_LOGIN_THRESHOLD" for a in alerts)

    def test_detect_after_hours_admin_action(self) -> None:
        """GIVEN admin action at 2 AM WHEN checking THEN alert triggered."""
        from mcp_server_langgraph.audit.alerts import AuditAlertDetector
        from mcp_server_langgraph.audit.models import (
            AuditActor,
            AuditContext,
            AuditEventCategory,
            AuditEventType,
            UnifiedAuditEvent,
        )

        detector = AuditAlertDetector(
            business_hours_start=9,
            business_hours_end=17,
        )

        # Admin action at 2 AM (after hours)
        event = UnifiedAuditEvent(
            timestamp=datetime(2025, 1, 15, 2, 0, 0, tzinfo=UTC),  # 2 AM
            category=AuditEventCategory.SYSTEM,
            event_type=AuditEventType.CONFIG_CHANGE,
            actor=AuditActor(
                actor_id="user:admin",
                actor_type="user",
                roles=["admin"],
            ),
            resource_type="config",
            resource_id="system-settings",
            action="Modified system configuration",
            outcome="success",
            context=AuditContext(request_id="req-admin"),
        )

        detector.process_event(event)
        alerts = detector.get_triggered_alerts()

        assert len(alerts) > 0
        assert any(a.alert_type == "AFTER_HOURS_ADMIN_ACTION" for a in alerts)

    def test_detect_bulk_data_export(self) -> None:
        """GIVEN large data export WHEN checking THEN alert triggered."""
        from mcp_server_langgraph.audit.alerts import AuditAlertDetector
        from mcp_server_langgraph.audit.models import (
            AuditActor,
            AuditContext,
            AuditEventCategory,
            AuditEventType,
            UnifiedAuditEvent,
        )

        detector = AuditAlertDetector(
            bulk_export_threshold_records=1000,
        )

        event = UnifiedAuditEvent(
            category=AuditEventCategory.DATA_ACCESS,
            event_type=AuditEventType.DATA_EXPORT,
            actor=AuditActor(actor_id="user:exporter", actor_type="user"),
            resource_type="audit_logs",
            resource_id="export-001",
            action="Bulk data export",
            outcome="success",
            context=AuditContext(request_id="req-export"),
            details={"record_count": 5000},
        )

        detector.process_event(event)
        alerts = detector.get_triggered_alerts()

        assert len(alerts) > 0
        assert any(a.alert_type == "BULK_DATA_EXPORT" for a in alerts)

    def test_detect_integrity_tampering(self) -> None:
        """GIVEN integrity verification failure WHEN checking THEN alert triggered."""
        from mcp_server_langgraph.audit.alerts import AuditAlertDetector

        detector = AuditAlertDetector()

        # Report integrity failure
        detector.report_integrity_failure(
            start_time=datetime(2025, 1, 1, tzinfo=UTC),
            end_time=datetime(2025, 1, 31, tzinfo=UTC),
            errors=["Hash mismatch at position 500"],
        )

        alerts = detector.get_triggered_alerts()

        assert len(alerts) > 0
        assert any(a.alert_type == "INTEGRITY_TAMPERING" for a in alerts)
        assert any(a.severity == "critical" for a in alerts)


@pytest.mark.unit
@pytest.mark.xdist_group(name="audit_alerts")
class TestAuditAlertModel:
    """Tests for audit alert data model."""

    def teardown_method(self) -> None:
        """Force GC to prevent mock accumulation in xdist workers."""
        gc.collect()

    def test_alert_has_required_fields(self) -> None:
        """GIVEN alert WHEN created THEN has required fields."""
        from mcp_server_langgraph.audit.alerts import AuditAlert

        alert = AuditAlert(
            alert_type="TEST_ALERT",
            severity="warning",
            message="Test alert message",
            source_event_id="evt-001",
        )

        assert alert.alert_id is not None
        assert alert.timestamp is not None
        assert alert.alert_type == "TEST_ALERT"
        assert alert.severity == "warning"
        assert alert.message == "Test alert message"
        assert alert.acknowledged is False

    def test_alert_severity_levels(self) -> None:
        """GIVEN alert WHEN checking severity THEN validates level."""
        from mcp_server_langgraph.audit.alerts import AuditAlert

        # Valid severities
        for severity in ["info", "warning", "error", "critical"]:
            alert = AuditAlert(
                alert_type="TEST",
                severity=severity,
                message="Test",
            )
            assert alert.severity == severity


@pytest.mark.unit
@pytest.mark.xdist_group(name="audit_alerts")
class TestAuditAlertNotification:
    """Tests for alert notification."""

    def teardown_method(self) -> None:
        """Force GC to prevent mock accumulation in xdist workers."""
        gc.collect()

    @pytest.mark.asyncio
    async def test_alert_callback_invoked(self) -> None:
        """GIVEN alert callback WHEN alert triggered THEN callback invoked."""
        from mcp_server_langgraph.audit.alerts import AuditAlertDetector
        from mcp_server_langgraph.audit.models import (
            AuditActor,
            AuditContext,
            AuditEventCategory,
            AuditEventType,
            UnifiedAuditEvent,
        )

        callback_invoked = []

        async def alert_callback(alert):
            callback_invoked.append(alert)

        detector = AuditAlertDetector(
            failed_login_threshold=2,
            alert_callback=alert_callback,
        )

        # Trigger failed login alert
        for i in range(3):
            event = UnifiedAuditEvent(
                category=AuditEventCategory.AUTHENTICATION,
                event_type=AuditEventType.LOGIN_FAILED,
                actor=AuditActor(actor_id="user:attacker", actor_type="user"),
                resource_type="session",
                resource_id=f"attempt-{i}",
                action="Login attempt",
                outcome="failure",
                context=AuditContext(request_id=f"req-{i}"),
            )
            await detector.process_event_async(event)

        assert len(callback_invoked) > 0

    @pytest.mark.asyncio
    async def test_alert_acknowledge(self) -> None:
        """GIVEN alert WHEN acknowledged THEN marked as acknowledged."""
        from mcp_server_langgraph.audit.alerts import AuditAlert, AuditAlertManager

        manager = AuditAlertManager()

        alert = AuditAlert(
            alert_type="TEST",
            severity="warning",
            message="Test alert",
        )

        await manager.add_alert(alert)
        await manager.acknowledge_alert(alert.alert_id, "user:admin")

        updated = await manager.get_alert(alert.alert_id)
        assert updated.acknowledged is True
        assert updated.acknowledged_by == "user:admin"
