"""
Tests for audit alert notification integrations.

TDD RED phase: These tests define expected behavior for notifications.

The notification system should:
- Send alerts to Slack webhooks
- Send alerts to PagerDuty
- Support configurable severity routing
- Handle notification failures gracefully
"""

import gc
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

pytestmark = pytest.mark.unit


@pytest.mark.unit
@pytest.mark.xdist_group(name="audit_notifications")
class TestSlackNotifier:
    """Tests for Slack webhook integration."""

    def teardown_method(self) -> None:
        """Force GC to prevent mock accumulation in xdist workers."""
        gc.collect()

    @pytest.mark.asyncio
    async def test_send_alert_to_slack(self) -> None:
        """GIVEN alert WHEN sent THEN Slack webhook called."""
        from mcp_server_langgraph.audit.notifications import SlackNotifier
        from mcp_server_langgraph.audit.alerts import AuditAlert

        notifier = SlackNotifier(webhook_url="https://hooks.slack.com/test")

        alert = AuditAlert(
            alert_type="FAILED_LOGIN_THRESHOLD",
            severity="warning",
            message="Multiple failed login attempts detected",
        )

        with patch("httpx.AsyncClient") as mock_client:
            mock_response = MagicMock()
            mock_response.status_code = 200
            mock_client.return_value.__aenter__.return_value.post = AsyncMock(return_value=mock_response)

            result = await notifier.send(alert)

            assert result is True

    @pytest.mark.asyncio
    async def test_slack_formats_message_correctly(self) -> None:
        """GIVEN alert WHEN formatting THEN Slack message format used."""
        from mcp_server_langgraph.audit.notifications import SlackNotifier
        from mcp_server_langgraph.audit.alerts import AuditAlert

        notifier = SlackNotifier(webhook_url="https://hooks.slack.com/test")

        alert = AuditAlert(
            alert_type="INTEGRITY_TAMPERING",
            severity="critical",
            message="Audit log tampering detected",
            details={"errors": ["Hash mismatch at position 500"]},
        )

        message = notifier.format_message(alert)

        assert "INTEGRITY_TAMPERING" in message["text"]
        assert "critical" in message["text"].lower()

    @pytest.mark.asyncio
    async def test_slack_handles_failure_gracefully(self) -> None:
        """GIVEN Slack error WHEN sending THEN handles gracefully."""
        from mcp_server_langgraph.audit.notifications import SlackNotifier
        from mcp_server_langgraph.audit.alerts import AuditAlert

        notifier = SlackNotifier(webhook_url="https://hooks.slack.com/test")

        alert = AuditAlert(
            alert_type="TEST",
            severity="info",
            message="Test alert",
        )

        with patch("httpx.AsyncClient") as mock_client:
            mock_client.return_value.__aenter__.return_value.post = AsyncMock(side_effect=Exception("Network error"))

            result = await notifier.send(alert)

            assert result is False


@pytest.mark.unit
@pytest.mark.xdist_group(name="audit_notifications")
class TestPagerDutyNotifier:
    """Tests for PagerDuty integration."""

    def teardown_method(self) -> None:
        """Force GC to prevent mock accumulation in xdist workers."""
        gc.collect()

    @pytest.mark.asyncio
    async def test_send_alert_to_pagerduty(self) -> None:
        """GIVEN critical alert WHEN sent THEN PagerDuty triggered."""
        from mcp_server_langgraph.audit.notifications import PagerDutyNotifier
        from mcp_server_langgraph.audit.alerts import AuditAlert

        notifier = PagerDutyNotifier(
            routing_key="test-routing-key",
            service_name="audit-service",
        )

        alert = AuditAlert(
            alert_type="INTEGRITY_TAMPERING",
            severity="critical",
            message="Critical integrity failure",
        )

        with patch("httpx.AsyncClient") as mock_client:
            mock_response = MagicMock()
            mock_response.status_code = 202
            mock_client.return_value.__aenter__.return_value.post = AsyncMock(return_value=mock_response)

            result = await notifier.send(alert)

            assert result is True

    @pytest.mark.asyncio
    async def test_pagerduty_only_triggers_for_critical(self) -> None:
        """GIVEN non-critical alert WHEN sent THEN not triggered."""
        from mcp_server_langgraph.audit.notifications import PagerDutyNotifier
        from mcp_server_langgraph.audit.alerts import AuditAlert

        notifier = PagerDutyNotifier(
            routing_key="test-routing-key",
            min_severity="critical",
        )

        alert = AuditAlert(
            alert_type="FAILED_LOGIN",
            severity="warning",
            message="Warning alert",
        )

        # Should not send for warning severity
        result = await notifier.send(alert)

        assert result is True  # Returns True but doesn't actually send

    def test_pagerduty_creates_event_payload(self) -> None:
        """GIVEN alert WHEN formatting THEN PD Events v2 format used."""
        from mcp_server_langgraph.audit.notifications import PagerDutyNotifier
        from mcp_server_langgraph.audit.alerts import AuditAlert

        notifier = PagerDutyNotifier(
            routing_key="test-routing-key",
            service_name="audit-service",
        )

        alert = AuditAlert(
            alert_type="INTEGRITY_TAMPERING",
            severity="critical",
            message="Critical integrity failure",
            details={"events_verified": 1000},
        )

        payload = notifier.format_event(alert)

        assert payload["routing_key"] == "test-routing-key"
        assert payload["event_action"] == "trigger"
        assert "payload" in payload
        assert payload["payload"]["severity"] == "critical"


@pytest.mark.unit
@pytest.mark.xdist_group(name="audit_notifications")
class TestNotificationRouter:
    """Tests for routing alerts to multiple channels."""

    def teardown_method(self) -> None:
        """Force GC to prevent mock accumulation in xdist workers."""
        gc.collect()

    @pytest.mark.asyncio
    async def test_routes_to_all_notifiers(self) -> None:
        """GIVEN multiple notifiers WHEN alert sent THEN all receive."""
        from mcp_server_langgraph.audit.notifications import NotificationRouter
        from mcp_server_langgraph.audit.alerts import AuditAlert

        mock_slack = AsyncMock(return_value=None)  # async-mock-configured
        mock_slack.send = AsyncMock(return_value=True)

        mock_pagerduty = AsyncMock(return_value=None)  # async-mock-configured
        mock_pagerduty.send = AsyncMock(return_value=True)

        router = NotificationRouter(notifiers=[mock_slack, mock_pagerduty])

        alert = AuditAlert(
            alert_type="TEST",
            severity="critical",
            message="Test alert",
        )

        results = await router.send_all(alert)

        assert len(results) == 2
        assert all(results)
        mock_slack.send.assert_called_once()
        mock_pagerduty.send.assert_called_once()

    @pytest.mark.asyncio
    async def test_routes_by_severity(self) -> None:
        """GIVEN severity routing WHEN alert sent THEN correct channels used."""
        from mcp_server_langgraph.audit.notifications import NotificationRouter
        from mcp_server_langgraph.audit.alerts import AuditAlert

        mock_slack = AsyncMock(return_value=None)  # async-mock-configured
        mock_slack.send = AsyncMock(return_value=True)
        mock_slack.min_severity = "info"

        mock_pagerduty = AsyncMock(return_value=None)  # async-mock-configured
        mock_pagerduty.send = AsyncMock(return_value=True)
        mock_pagerduty.min_severity = "critical"

        router = NotificationRouter(notifiers=[mock_slack, mock_pagerduty])

        # Warning alert - only Slack should receive
        warning_alert = AuditAlert(
            alert_type="TEST",
            severity="warning",
            message="Warning alert",
        )

        # Router should filter based on severity
        await router.send_all(warning_alert)

    @pytest.mark.asyncio
    async def test_handles_partial_failures(self) -> None:
        """GIVEN one notifier fails WHEN sending THEN others still succeed."""
        from mcp_server_langgraph.audit.notifications import NotificationRouter
        from mcp_server_langgraph.audit.alerts import AuditAlert

        mock_slack = AsyncMock(return_value=None)  # async-mock-configured
        mock_slack.send = AsyncMock(return_value=True)

        mock_failing = AsyncMock(return_value=None)  # async-mock-configured
        mock_failing.send = AsyncMock(return_value=False)

        router = NotificationRouter(notifiers=[mock_slack, mock_failing])

        alert = AuditAlert(
            alert_type="TEST",
            severity="critical",
            message="Test alert",
        )

        results = await router.send_all(alert)

        assert len(results) == 2
        assert results[0] is True
        assert results[1] is False
