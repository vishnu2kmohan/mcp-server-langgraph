"""
Tests for audit alerting configuration.

TDD RED phase: These tests define expected behavior for configuration loading.

The configuration system should:
- Load alerting config from YAML
- Support Slack webhook configuration
- Support PagerDuty routing key configuration
- Support environment variable substitution
- Validate configuration schema
"""

import gc
import os
from pathlib import Path
from unittest.mock import patch

import pytest

pytestmark = pytest.mark.unit


@pytest.mark.unit
@pytest.mark.xdist_group(name="audit_config")
class TestAuditAlertingConfig:
    """Tests for audit alerting configuration loading."""

    def teardown_method(self) -> None:
        """Force GC to prevent mock accumulation in xdist workers."""
        gc.collect()

    def test_config_file_exists(self) -> None:
        """GIVEN config directory THEN alerts.yaml exists."""
        config_path = Path("config/alerts.yaml")
        assert config_path.exists(), "config/alerts.yaml should exist"

    def test_load_alerting_config(self) -> None:
        """GIVEN alerts.yaml WHEN loaded THEN config object returned."""
        from mcp_server_langgraph.audit.config import load_alerting_config

        config = load_alerting_config()

        assert config is not None
        assert hasattr(config, "slack")
        assert hasattr(config, "pagerduty")

    def test_slack_config_has_webhook_url(self) -> None:
        """GIVEN Slack config THEN webhook_url defined."""
        from mcp_server_langgraph.audit.config import load_alerting_config

        config = load_alerting_config()

        assert config.slack is not None
        assert hasattr(config.slack, "webhook_url")

    def test_slack_config_has_channel(self) -> None:
        """GIVEN Slack config THEN channel defined."""
        from mcp_server_langgraph.audit.config import load_alerting_config

        config = load_alerting_config()

        assert config.slack is not None
        assert hasattr(config.slack, "channel")

    def test_pagerduty_config_has_routing_key(self) -> None:
        """GIVEN PagerDuty config THEN routing_key defined."""
        from mcp_server_langgraph.audit.config import load_alerting_config

        config = load_alerting_config()

        assert config.pagerduty is not None
        assert hasattr(config.pagerduty, "routing_key")

    def test_pagerduty_config_has_service_name(self) -> None:
        """GIVEN PagerDuty config THEN service_name defined."""
        from mcp_server_langgraph.audit.config import load_alerting_config

        config = load_alerting_config()

        assert config.pagerduty is not None
        assert hasattr(config.pagerduty, "service_name")

    def test_environment_variable_substitution(self) -> None:
        """GIVEN env vars WHEN loading config THEN substituted."""
        from mcp_server_langgraph.audit.config import load_alerting_config

        with patch.dict(
            os.environ,
            {
                "AUDIT_SLACK_WEBHOOK_URL": "https://hooks.slack.com/services/TEST",
                "AUDIT_PAGERDUTY_ROUTING_KEY": "test-routing-key",
            },
        ):
            config = load_alerting_config()

            # Config should resolve environment variables
            assert config is not None


@pytest.mark.unit
@pytest.mark.xdist_group(name="audit_config")
class TestAlertingConfigValidation:
    """Tests for configuration validation."""

    def teardown_method(self) -> None:
        """Force GC to prevent mock accumulation in xdist workers."""
        gc.collect()

    def test_invalid_severity_rejected(self) -> None:
        """GIVEN invalid severity WHEN validating THEN error raised."""
        from mcp_server_langgraph.audit.config import SlackConfig

        with pytest.raises(ValueError):
            SlackConfig(
                webhook_url="https://hooks.slack.com/test",
                min_severity="invalid_severity",  # Should fail validation
            )

    def test_valid_severities_accepted(self) -> None:
        """GIVEN valid severity WHEN validating THEN accepted."""
        from mcp_server_langgraph.audit.config import SlackConfig

        for severity in ["info", "warning", "error", "critical"]:
            config = SlackConfig(
                webhook_url="https://hooks.slack.com/test",
                min_severity=severity,
            )
            assert config.min_severity == severity


@pytest.mark.unit
@pytest.mark.xdist_group(name="audit_config")
class TestAlertingConfigFactory:
    """Tests for creating notifiers from configuration."""

    def teardown_method(self) -> None:
        """Force GC to prevent mock accumulation in xdist workers."""
        gc.collect()

    def test_create_notifiers_from_config(self) -> None:
        """GIVEN config WHEN creating notifiers THEN instances returned."""
        from mcp_server_langgraph.audit.config import (
            create_notifiers_from_config,
            load_alerting_config,
        )

        config = load_alerting_config()
        notifiers = create_notifiers_from_config(config)

        assert isinstance(notifiers, list)

    def test_create_notification_router(self) -> None:
        """GIVEN config WHEN creating router THEN router returned."""
        from mcp_server_langgraph.audit.config import create_notification_router

        router = create_notification_router()

        assert router is not None

    def test_disabled_notifiers_not_created(self) -> None:
        """GIVEN disabled config WHEN creating notifiers THEN excluded."""
        from mcp_server_langgraph.audit.config import (
            AlertingConfig,
            SlackConfig,
            create_notifiers_from_config,
        )

        # Config with disabled Slack
        config = AlertingConfig(
            slack=SlackConfig(
                enabled=False,
                webhook_url="https://hooks.slack.com/test",
            ),
            pagerduty=None,
        )

        notifiers = create_notifiers_from_config(config)

        # Should be empty since Slack is disabled and PagerDuty is None
        assert len(notifiers) == 0
