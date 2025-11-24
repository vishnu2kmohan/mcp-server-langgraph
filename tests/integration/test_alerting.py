"""
Tests for alerting system integration.

Tests comprehensive alerting functionality including:
- Alert creation and deduplication
- Multiple provider integrations
- Alert routing and delivery
- Error handling and retries
"""

import gc
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from mcp_server_langgraph.integrations.alerting import (
    Alert,
    AlertCategory,
    AlertingConfig,
    AlertingService,
    AlertSeverity,
    EmailProvider,
    PagerDutyProvider,
    SlackProvider,
    send_alert,
)

# Mark as integration test to ensure it runs in CI
pytestmark = pytest.mark.integration


@pytest.mark.xdist_group(name="integration_alerting_tests")
class TestAlert:
    """Tests for Alert dataclass"""

    def teardown_method(self):
        """Force GC to prevent mock accumulation in xdist workers"""
        gc.collect()

    def test_alert_creation_with_valid_fields_creates_alert(self):
        """Test basic alert creation"""
        alert = Alert(
            title="Test Alert",
            description="This is a test",
            severity=AlertSeverity.HIGH,
            category=AlertCategory.SECURITY,
            source="test_module",
        )

        assert alert.title == "Test Alert"
        assert alert.severity == AlertSeverity.HIGH
        assert alert.category == AlertCategory.SECURITY
        assert alert.dedupe_key is not None

    def test_alert_deduplication_key_generation(self):
        """Test automatic deduplication key generation"""
        alert1 = Alert(
            title="Same Title",
            description="Different description 1",
            severity=AlertSeverity.HIGH,
            category=AlertCategory.SLA,
            source="module_a",
        )

        alert2 = Alert(
            title="Same Title",
            description="Different description 2",
            severity=AlertSeverity.MEDIUM,
            category=AlertCategory.SLA,
            source="module_a",
        )

        # Same title, source, category should generate same dedupe key
        assert alert1.dedupe_key == alert2.dedupe_key

    def test_alert_deduplication_key_differs(self):
        """Test deduplication keys differ for different alerts"""
        alert1 = Alert(
            title="Title 1",
            description="Description",
            severity=AlertSeverity.HIGH,
            category=AlertCategory.SLA,
            source="module_a",
        )

        alert2 = Alert(
            title="Title 2",
            description="Description",
            severity=AlertSeverity.HIGH,
            category=AlertCategory.SLA,
            source="module_a",
        )

        assert alert1.dedupe_key != alert2.dedupe_key

    def test_alert_to_dict(self):
        """Test alert serialization to dictionary"""
        alert = Alert(
            title="Test",
            description="Desc",
            severity=AlertSeverity.CRITICAL,
            category=AlertCategory.INFRASTRUCTURE,
            source="test",
            metadata={"key": "value"},
        )

        alert_dict = alert.to_dict()

        assert alert_dict["title"] == "Test"
        assert alert_dict["severity"] == "critical"
        assert alert_dict["category"] == "infrastructure"
        assert "timestamp" in alert_dict
        assert alert_dict["metadata"]["key"] == "value"


@pytest.mark.xdist_group(name="integration_alerting_tests")
class TestPagerDutyProvider:
    """Tests for PagerDuty integration"""

    def teardown_method(self):
        """Force GC to prevent mock accumulation in xdist workers"""
        gc.collect()

    @pytest.mark.asyncio
    async def test_pagerduty_send_alert_success(self):
        """Test successful PagerDuty alert delivery"""
        provider = PagerDutyProvider(integration_key="test-key-123")

        alert = Alert(
            title="Database Down",
            description="PostgreSQL connection lost",
            severity=AlertSeverity.CRITICAL,
            category=AlertCategory.INFRASTRUCTURE,
            source="db_monitor",
        )

        # Mock HTTP client
        with patch.object(provider.client, "post", new_callable=AsyncMock) as mock_post:
            mock_response = MagicMock()
            mock_response.raise_for_status = MagicMock()
            mock_post.return_value = mock_response

            result = await provider.send_alert(alert)

            assert result is True
            mock_post.assert_called_once()

            # Verify payload structure
            call_args = mock_post.call_args
            payload = call_args[1]["json"]

            assert payload["routing_key"] == "test-key-123"
            assert payload["event_action"] == "trigger"
            assert payload["dedup_key"] == alert.dedupe_key
            assert payload["payload"]["summary"] == "Database Down"
            assert payload["payload"]["severity"] == "critical"

        await provider.close()

    @pytest.mark.asyncio
    async def test_pagerduty_send_alert_failure(self):
        """Test PagerDuty alert delivery failure handling"""
        provider = PagerDutyProvider(integration_key="test-key-123")

        alert = Alert(
            title="Test Alert",
            description="Test",
            severity=AlertSeverity.HIGH,
            category=AlertCategory.ERROR,
            source="test",
        )

        # Mock HTTP client to raise exception
        with patch.object(provider.client, "post", new_callable=AsyncMock) as mock_post:
            mock_post.side_effect = Exception("Network error")

            result = await provider.send_alert(alert)

            assert result is False

        await provider.close()


@pytest.mark.xdist_group(name="integration_alerting_tests")
class TestSlackProvider:
    """Tests for Slack integration"""

    def teardown_method(self):
        """Force GC to prevent mock accumulation in xdist workers"""
        gc.collect()

    @pytest.mark.asyncio
    async def test_slack_send_alert_success(self):
        """Test successful Slack alert delivery"""
        provider = SlackProvider(
            webhook_url="https://hooks.slack.com/test",
            channel="#alerts",
            mention_on_critical="@oncall",
        )

        alert = Alert(
            title="High Memory Usage",
            description="Memory usage at 95%",
            severity=AlertSeverity.CRITICAL,
            category=AlertCategory.PERFORMANCE,
            source="resource_monitor",
            metadata={"current_memory": "95%", "threshold": "90%"},
        )

        with patch.object(provider.client, "post", new_callable=AsyncMock) as mock_post:
            mock_response = MagicMock()
            mock_response.raise_for_status = MagicMock()
            mock_post.return_value = mock_response

            result = await provider.send_alert(alert)

            assert result is True
            mock_post.assert_called_once()

            # Verify payload
            call_args = mock_post.call_args
            payload = call_args[1]["json"]

            assert "@oncall" in payload["text"]  # Critical alert mentions oncall
            assert payload["channel"] == "#alerts"
            assert len(payload["attachments"]) == 1

            attachment = payload["attachments"][0]
            assert attachment["title"] == "High Memory Usage"
            assert attachment["color"] == "#FF0000"  # Critical = red

        await provider.close()

    @pytest.mark.asyncio
    async def test_slack_alert_severity_colors(self):
        """Test Slack color coding by severity"""
        provider = SlackProvider(webhook_url="https://hooks.slack.com/test")

        test_cases = [
            (AlertSeverity.CRITICAL, "#FF0000"),
            (AlertSeverity.HIGH, "#FF6600"),
            (AlertSeverity.MEDIUM, "#FFA500"),
            (AlertSeverity.LOW, "#3AA3E3"),
            (AlertSeverity.INFO, "#808080"),
        ]

        for severity, expected_color in test_cases:
            alert = Alert(
                title="Test",
                description="Test",
                severity=severity,
                category=AlertCategory.ERROR,
                source="test",
            )

            with patch.object(provider.client, "post", new_callable=AsyncMock) as mock_post:
                mock_response = MagicMock()
                mock_response.raise_for_status = MagicMock()
                mock_post.return_value = mock_response

                await provider.send_alert(alert)

                payload = mock_post.call_args[1]["json"]
                assert payload["attachments"][0]["color"] == expected_color

        await provider.close()


@pytest.mark.xdist_group(name="integration_alerting_tests")
class TestEmailProvider:
    """Tests for Email integration"""

    def teardown_method(self):
        """Force GC to prevent mock accumulation in xdist workers"""
        gc.collect()

    @pytest.mark.asyncio
    async def test_email_send_via_sendgrid_success(self):
        """Test successful email via SendGrid"""
        provider = EmailProvider(
            provider_type="sendgrid",
            api_key="test-api-key",
            from_email="alerts@example.com",
            to_emails=["admin@example.com", "oncall@example.com"],
        )

        alert = Alert(
            title="SLA Breach",
            description="Uptime dropped below 99.9%",
            severity=AlertSeverity.HIGH,
            category=AlertCategory.SLA,
            source="sla_monitor",
            metadata={"current_uptime": "99.85%", "threshold": "99.9%"},
        )

        with patch.object(provider.client, "post", new_callable=AsyncMock) as mock_post:
            mock_response = MagicMock()
            mock_response.raise_for_status = MagicMock()
            mock_post.return_value = mock_response

            result = await provider.send_alert(alert)

            assert result is True
            mock_post.assert_called_once()

            # Verify SendGrid API call
            call_args = mock_post.call_args
            assert call_args[0][0] == "https://api.sendgrid.com/v3/mail/send"

            # Verify payload
            payload = call_args[1]["json"]
            assert payload["subject"] == "[HIGH] SLA Breach"
            assert len(payload["personalizations"][0]["to"]) == 2
            assert payload["from"]["email"] == "alerts@example.com"

        await provider.close()

    @pytest.mark.asyncio
    async def test_email_no_recipients_configured(self):
        """Test email provider with no recipients"""
        provider = EmailProvider(
            provider_type="sendgrid",
            api_key="test-key",
            from_email="alerts@example.com",
            to_emails=[],  # No recipients
        )

        alert = Alert(
            title="Test",
            description="Test",
            severity=AlertSeverity.INFO,
            category=AlertCategory.ERROR,
            source="test",
        )

        result = await provider.send_alert(alert)

        # Should return False when no recipients configured
        assert result is False

        await provider.close()


@pytest.mark.xdist_group(name="integration_alerting_tests")
class TestAlertingService:
    """Tests for main AlertingService"""

    def teardown_method(self):
        """Force GC to prevent mock accumulation in xdist workers"""
        gc.collect()

    @pytest.mark.asyncio
    async def test_alerting_service_initialization(self):
        """Test alerting service initialization"""
        config = AlertingConfig(
            enabled=True,
            providers={
                "slack": {
                    "enabled": True,
                    "webhook_url": "https://hooks.slack.com/test",
                    "channel": "#alerts",
                }
            },
        )

        service = AlertingService(config=config)
        await service.initialize()

        assert service._initialized is True
        assert len(service.providers) == 1
        assert isinstance(service.providers[0], SlackProvider)

        await service.close()

    @pytest.mark.asyncio
    async def test_alerting_service_send_alert(self):
        """Test sending alert through service"""
        config = AlertingConfig(
            enabled=True,
            providers={
                "slack": {
                    "enabled": True,
                    "webhook_url": "https://hooks.slack.com/test",
                }
            },
            deduplication_window=300,
        )

        service = AlertingService(config=config)
        await service.initialize()

        alert = Alert(
            title="Test Alert",
            description="Testing alerting service",
            severity=AlertSeverity.MEDIUM,
            category=AlertCategory.ERROR,
            source="test_suite",
        )

        # Mock provider send_alert
        with patch.object(service.providers[0], "send_alert", new_callable=AsyncMock) as mock_send:
            mock_send.return_value = True

            results = await service.send_alert(alert)

            assert "SlackProvider" in results
            assert results["SlackProvider"] is True
            mock_send.assert_called_once_with(alert)

        await service.close()

    @pytest.mark.asyncio
    async def test_alerting_service_deduplication(self):
        """Test alert deduplication"""
        config = AlertingConfig(
            enabled=True,
            providers={
                "slack": {
                    "enabled": True,
                    "webhook_url": "https://hooks.slack.com/test",
                }
            },
            deduplication_window=60,  # 1 minute window
        )

        service = AlertingService(config=config)
        await service.initialize()

        alert1 = Alert(
            title="Same Alert",
            description="First occurrence",
            severity=AlertSeverity.HIGH,
            category=AlertCategory.ERROR,
            source="test",
        )

        alert2 = Alert(
            title="Same Alert",
            description="Second occurrence",  # Different description
            severity=AlertSeverity.HIGH,
            category=AlertCategory.ERROR,
            source="test",
        )

        # Alerts should have same dedupe key
        assert alert1.dedupe_key == alert2.dedupe_key

        with patch.object(service.providers[0], "send_alert", new_callable=AsyncMock) as mock_send:
            mock_send.return_value = True

            # Send first alert
            results1 = await service.send_alert(alert1)
            assert "SlackProvider" in results1

            # Send duplicate alert immediately
            results2 = await service.send_alert(alert2)
            assert len(results2) == 0  # Deduplicated

            # Verify provider was only called once
            assert mock_send.call_count == 1

        await service.close()

    @pytest.mark.asyncio
    async def test_alerting_service_disabled(self):
        """Test alerting service when disabled"""
        config = AlertingConfig(enabled=False)

        service = AlertingService(config=config)
        await service.initialize()

        alert = Alert(
            title="Test",
            description="Test",
            severity=AlertSeverity.INFO,
            category=AlertCategory.ERROR,
            source="test",
        )

        results = await service.send_alert(alert)

        # Should return empty results when disabled
        assert results == {}

        await service.close()

    @pytest.mark.asyncio
    async def test_alerting_service_statistics(self):
        """Test alert statistics tracking"""
        config = AlertingConfig(
            enabled=True,
            providers={
                "slack": {
                    "enabled": True,
                    "webhook_url": "https://hooks.slack.com/test",
                }
            },
            deduplication_window=300,
        )

        service = AlertingService(config=config)
        await service.initialize()

        alerts = [
            Alert("Critical 1", "Test", AlertSeverity.CRITICAL, AlertCategory.SECURITY, "test1"),
            Alert("High 1", "Test", AlertSeverity.HIGH, AlertCategory.SLA, "test2"),
            Alert("High 2", "Test", AlertSeverity.HIGH, AlertCategory.ERROR, "test3"),
        ]

        with patch.object(service.providers[0], "send_alert", new_callable=AsyncMock) as mock_send:
            mock_send.return_value = True

            for alert in alerts:
                await service.send_alert(alert)

        stats = service.get_alert_statistics()

        assert stats["total_alerts"] == 3
        assert stats["by_severity"]["critical"] == 1
        assert stats["by_severity"]["high"] == 2
        assert stats["by_category"]["security"] == 1
        assert stats["by_category"]["sla"] == 1
        assert stats["by_category"]["error"] == 1
        assert stats["providers_active"] == 1

        await service.close()


@pytest.mark.xdist_group(name="integration_alerting_tests")
class TestAlertingConvenienceFunctions:
    """Tests for convenience functions"""

    def teardown_method(self):
        """Force GC to prevent mock accumulation in xdist workers"""
        gc.collect()

    @pytest.mark.asyncio
    async def test_send_alert_convenience_function(self):
        """Test send_alert convenience function"""
        config = AlertingConfig(
            enabled=True,
            providers={
                "slack": {
                    "enabled": True,
                    "webhook_url": "https://hooks.slack.com/test",
                }
            },
        )

        # Create and initialize service manually
        from mcp_server_langgraph.integrations import alerting as alerting_module

        service = AlertingService(config=config)
        await service.initialize()

        # Mock the global service
        with patch.object(alerting_module, "_alerting_service", service):
            with patch.object(service.providers[0], "send_alert", new_callable=AsyncMock) as mock_send:
                mock_send.return_value = True

                results = await send_alert(
                    title="Convenience Test",
                    description="Testing convenience function",
                    severity=AlertSeverity.MEDIUM,
                    category=AlertCategory.PERFORMANCE,
                    source="test_suite",
                    metadata={"test_key": "test_value"},
                )

                assert "SlackProvider" in results
                mock_send.assert_called_once()

        await service.close()
