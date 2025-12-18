"""
Observability Configuration Module.

Settings for OpenTelemetry, LangSmith, LGTM stack, logging, and alerting.
"""

from pydantic import AliasChoices, Field
from pydantic_settings import SettingsConfigDict

from mcp_server_langgraph.core.config.base import DomainSettings


class ObservabilitySettings(DomainSettings):
    """
    Observability and monitoring settings.

    Covers:
    - OpenTelemetry (traces, metrics, logs)
    - LangSmith tracing integration
    - LGTM stack (Loki, Grafana, Tempo, Mimir)
    - Prometheus metrics
    - Logging configuration
    - Alerting (PagerDuty, Slack, OpsGenie, Email)
    """

    model_config = SettingsConfigDict(
        env_prefix="",
        extra="ignore",
    )

    # OpenTelemetry
    otlp_endpoint: str = Field(
        default="http://localhost:4317",
        validation_alias=AliasChoices("OTEL_EXPORTER_OTLP_ENDPOINT", "OTLP_ENDPOINT"),
    )
    enable_console_export: bool = Field(
        default=True,
        validation_alias=AliasChoices("ENABLE_CONSOLE_EXPORT"),
    )
    enable_tracing: bool = True
    enable_metrics: bool = True

    # Prometheus
    prometheus_url: str = "http://prometheus:9090"
    prometheus_timeout: int = 30
    prometheus_retry_attempts: int = 3

    # LangSmith Observability
    langsmith_api_key: str | None = None
    langsmith_project: str = "mcp-server-langgraph"
    langsmith_endpoint: str = "https://api.smith.langchain.com"
    langsmith_tracing: bool = False
    langsmith_tracing_v2: bool = True

    # Observability Backend Selection
    observability_backend: str = "both"  # opentelemetry, langsmith, both

    # LGTM Stack URLs
    loki_url: str = ""
    tempo_url: str = ""
    mimir_url: str = ""

    # Logging
    log_level: str = "INFO"
    log_file: str | None = None
    log_format: str = "json"  # "json" or "text"
    log_json_indent: int | None = None
    enable_file_logging: bool = False

    # Alerting Configuration
    pagerduty_integration_key: str | None = None
    slack_webhook_url: str | None = None
    opsgenie_api_key: str | None = None
    email_smtp_host: str | None = None
    email_smtp_port: int = 587
    email_from_address: str | None = None
    email_to_addresses: str | None = None

    # Web Search API Configuration
    tavily_api_key: str | None = None
    serper_api_key: str | None = None
    brave_api_key: str | None = None


__all__ = ["ObservabilitySettings"]
