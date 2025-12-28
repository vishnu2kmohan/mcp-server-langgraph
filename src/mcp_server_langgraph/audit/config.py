"""
Audit alerting configuration module.

Loads alerting configuration from YAML files and environment variables.
Supports creation of notification channels for Slack, PagerDuty, etc.

Configuration file: config/alerts.yaml
Environment variables are substituted using ${VAR_NAME} syntax.
"""

import logging
import os
import re
from functools import lru_cache
from pathlib import Path
from typing import Any, Literal

import yaml
from pydantic import BaseModel, Field, field_validator

from mcp_server_langgraph.audit.notifications import (
    AlertNotifier,
    NotificationRouter,
    PagerDutyNotifier,
    SlackNotifier,
)

logger = logging.getLogger(__name__)

# Valid severity levels
VALID_SEVERITIES = {"info", "warning", "error", "critical"}

# Default config path
DEFAULT_CONFIG_PATH = Path("config/alerts.yaml")


class SlackConfig(BaseModel):
    """Slack notification configuration."""

    enabled: bool = True
    webhook_url: str = ""
    channel: str = "#audit-alerts"
    username: str = "Audit Alert Bot"
    icon_emoji: str = ":shield:"
    min_severity: Literal["info", "warning", "error", "critical"] = "warning"
    alert_types: list[str] = Field(default_factory=list)

    @field_validator("min_severity")
    @classmethod
    def validate_severity(cls, v: str) -> str:
        """Validate severity level."""
        if v not in VALID_SEVERITIES:
            raise ValueError(f"Invalid severity: {v}. Must be one of {VALID_SEVERITIES}")
        return v


class PagerDutyConfig(BaseModel):
    """PagerDuty notification configuration."""

    enabled: bool = True
    routing_key: str = ""
    service_name: str = "mcp-server-langgraph-audit"
    min_severity: Literal["info", "warning", "error", "critical"] = "critical"
    alert_types: list[str] = Field(default_factory=list)

    @field_validator("min_severity")
    @classmethod
    def validate_severity(cls, v: str) -> str:
        """Validate severity level."""
        if v not in VALID_SEVERITIES:
            raise ValueError(f"Invalid severity: {v}. Must be one of {VALID_SEVERITIES}")
        return v


class FailedLoginDetectionConfig(BaseModel):
    """Failed login detection configuration."""

    threshold: int = 5
    window_minutes: int = 15
    severity: str = "warning"


class BulkExportDetectionConfig(BaseModel):
    """Bulk export detection configuration."""

    threshold_records: int = 1000
    severity: str = "warning"


class AfterHoursAdminConfig(BaseModel):
    """After-hours admin action detection configuration."""

    start_hour: int = 22
    end_hour: int = 6
    severity: str = "warning"


class IntegrityTamperingConfig(BaseModel):
    """Integrity tampering detection configuration."""

    severity: str = "critical"


class RateLimitDetectionConfig(BaseModel):
    """Rate limit detection configuration."""

    threshold_per_minute: int = 100
    severity: str = "warning"


class DetectionConfig(BaseModel):
    """Alert detection thresholds configuration."""

    failed_login: FailedLoginDetectionConfig = Field(default_factory=FailedLoginDetectionConfig)
    bulk_export: BulkExportDetectionConfig = Field(default_factory=BulkExportDetectionConfig)
    after_hours_admin: AfterHoursAdminConfig = Field(default_factory=AfterHoursAdminConfig)
    integrity_tampering: IntegrityTamperingConfig = Field(default_factory=IntegrityTamperingConfig)
    rate_limit: RateLimitDetectionConfig = Field(default_factory=RateLimitDetectionConfig)


class EmailConfig(BaseModel):
    """Email notification configuration."""

    enabled: bool = False
    smtp_host: str = "localhost"
    smtp_port: int = 587
    smtp_user: str = ""
    smtp_password: str = ""
    from_address: str = Field(
        default="",
        description="From email address for audit notifications (set via AUDIT_FROM_EMAIL env var)",
    )
    to_addresses: list[str] = Field(default_factory=list)
    min_severity: str = "error"

    def __init__(self, **data: Any) -> None:
        """Initialize EmailConfig with environment variable support."""
        # Support AUDIT_FROM_EMAIL environment variable override
        if "from_address" not in data:
            env_from = os.environ.get("AUDIT_FROM_EMAIL")
            if env_from:
                data["from_address"] = env_from
        super().__init__(**data)


class WebhookConfig(BaseModel):
    """Generic webhook notification configuration."""

    enabled: bool = False
    url: str = ""
    headers: dict[str, str] = Field(default_factory=dict)
    min_severity: str = "warning"
    retry_attempts: int = 3
    timeout_seconds: int = 10


class AlertingConfig(BaseModel):
    """Complete alerting configuration."""

    slack: SlackConfig | None = Field(default_factory=SlackConfig)
    pagerduty: PagerDutyConfig | None = Field(default_factory=PagerDutyConfig)
    detection: DetectionConfig = Field(default_factory=DetectionConfig)
    email: EmailConfig | None = Field(default_factory=EmailConfig)
    webhook: WebhookConfig | None = Field(default_factory=WebhookConfig)


def _substitute_env_vars(value: Any) -> Any:
    """
    Substitute environment variables in configuration values.

    Supports ${VAR_NAME} and ${VAR_NAME:-default} syntax.
    """
    if isinstance(value, str):
        # Pattern: ${VAR_NAME} or ${VAR_NAME:-default}
        pattern = r"\$\{([A-Za-z_][A-Za-z0-9_]*)(?::-([^}]*))?\}"

        def replace(match: re.Match[str]) -> str:
            var_name = match.group(1)
            default = match.group(2) or ""
            return os.environ.get(var_name, default)

        return re.sub(pattern, replace, value)
    elif isinstance(value, dict):
        return {k: _substitute_env_vars(v) for k, v in value.items()}
    elif isinstance(value, list):
        return [_substitute_env_vars(item) for item in value]
    return value


def _load_yaml_config(config_path: Path) -> dict[str, Any]:
    """Load and parse YAML configuration file."""
    if not config_path.exists():
        logger.warning(f"Config file not found: {config_path}")
        return {}

    with open(config_path) as f:
        raw_config = yaml.safe_load(f) or {}

    # Substitute environment variables
    result = _substitute_env_vars(raw_config)
    return result if isinstance(result, dict) else {}


@lru_cache(maxsize=1)
def load_alerting_config(config_path: Path | None = None) -> AlertingConfig:
    """
    Load alerting configuration from YAML file.

    Environment variables are substituted using ${VAR_NAME} syntax.
    Results are cached for performance.

    Args:
        config_path: Path to config file. Defaults to config/alerts.yaml.

    Returns:
        AlertingConfig: Parsed and validated configuration.
    """
    path = config_path or DEFAULT_CONFIG_PATH
    raw_config = _load_yaml_config(path)

    try:
        return AlertingConfig(**raw_config)
    except Exception as e:
        logger.exception(f"Failed to parse alerting config: {e}")
        # Return default config on error
        return AlertingConfig()


def create_notifiers_from_config(config: AlertingConfig) -> list[AlertNotifier]:
    """
    Create notifier instances from configuration.

    Only creates notifiers that are enabled and have required configuration.

    Args:
        config: Alerting configuration.

    Returns:
        List of configured AlertNotifier instances.
    """
    notifiers: list[AlertNotifier] = []

    # Create Slack notifier if enabled and configured
    if config.slack and config.slack.enabled and config.slack.webhook_url:
        notifiers.append(
            SlackNotifier(
                webhook_url=config.slack.webhook_url,
                channel=config.slack.channel,
                username=config.slack.username,
                icon_emoji=config.slack.icon_emoji,
                min_severity=config.slack.min_severity,
            )
        )
        logger.info("Slack notifier configured")

    # Create PagerDuty notifier if enabled and configured
    if config.pagerduty and config.pagerduty.enabled and config.pagerduty.routing_key:
        notifiers.append(
            PagerDutyNotifier(
                routing_key=config.pagerduty.routing_key,
                service_name=config.pagerduty.service_name,
                min_severity=config.pagerduty.min_severity,
            )
        )
        logger.info("PagerDuty notifier configured")

    return notifiers


def create_notification_router(config_path: Path | None = None) -> NotificationRouter:
    """
    Create a notification router from configuration.

    Convenience function that loads config and creates router in one step.

    Args:
        config_path: Path to config file. Defaults to config/alerts.yaml.

    Returns:
        NotificationRouter: Configured router with all enabled notifiers.
    """
    config = load_alerting_config(config_path)
    notifiers = create_notifiers_from_config(config)
    return NotificationRouter(notifiers=notifiers)


def clear_config_cache() -> None:
    """Clear the configuration cache. Useful for testing."""
    load_alerting_config.cache_clear()
