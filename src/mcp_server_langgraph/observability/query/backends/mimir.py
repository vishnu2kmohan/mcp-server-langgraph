"""
Mimir Alerting query client.

Implements AlertingQueryClient for Mimir's built-in Alertmanager API.
Mimir exposes Alertmanager v2 compatible endpoints directly, bypassing Grafana.

This provides a fallback path when Grafana is unavailable while Mimir
continues to evaluate alerting rules.

Configuration:
    MIMIR_URL: Mimir URL (default: http://mimir:9009)
    MIMIR_ORG_ID: Tenant ID for multi-tenancy (default: anonymous)

Multi-tenancy:
    Mimir uses the X-Scope-OrgID header for tenant isolation.
    All requests include this header to ensure proper data segregation.

API Endpoints:
    GET /alertmanager/api/v2/alerts - List alerts (Alertmanager v2 format)
    GET /prometheus/api/v1/rules - List alerting rules
    GET /ready - Health check

Example:
    export MIMIR_URL=http://localhost:9009
    export MIMIR_ORG_ID=my-tenant
"""

import logging
import os
from datetime import datetime, timedelta

import httpx

from mcp_server_langgraph.observability.query.interfaces import (
    Alert,
    AlertingQueryClient,
    AlertRule,
    AlertSearchResult,
    AlertSeverity,
    AlertState,
)

logger = logging.getLogger(__name__)


def _parse_iso_datetime(value: str | None) -> datetime | None:
    """Parse ISO datetime string to datetime object."""
    if not value:
        return None
    try:
        # Handle various ISO formats
        if value.endswith("Z"):
            value = value[:-1] + "+00:00"
        # Skip sentinel values (0001-01-01 means not ended)
        parsed = datetime.fromisoformat(value)
        if parsed.year == 1:
            return None
        return parsed
    except (ValueError, TypeError):
        return None


def _map_severity(labels: dict[str, str]) -> AlertSeverity:
    """Map alert labels to severity level."""
    severity = labels.get("severity", "").lower()
    if severity in ("critical", "error"):
        return AlertSeverity.CRITICAL if severity == "critical" else AlertSeverity.ERROR
    elif severity == "warning":
        return AlertSeverity.WARNING
    return AlertSeverity.INFO


def _map_state(state: str) -> AlertState:
    """Map Alertmanager state to AlertState enum."""
    state_lower = state.lower()
    if state_lower in ("alerting", "firing"):
        return AlertState.FIRING
    elif state_lower == "pending":
        return AlertState.PENDING
    elif state_lower in ("normal", "resolved", "ok"):
        return AlertState.RESOLVED
    elif state_lower in ("silenced", "suppressed"):
        return AlertState.SILENCED
    return AlertState.PENDING


class MimirAlertingClient(AlertingQueryClient):
    """
    Mimir Alertmanager API client.

    Queries Mimir's built-in Alertmanager directly, bypassing Grafana.
    Uses the same Alertmanager v2 API format, providing a fallback when
    Grafana is unavailable.

    Mimir is typically used for long-term metrics storage and alerting in
    LGTM (Loki, Grafana, Tempo, Mimir) stacks. When Grafana is down, Mimir
    continues evaluating rules and can serve alert data directly.
    """

    def __init__(
        self,
        base_url: str | None = None,
        org_id: str | None = None,
    ) -> None:
        """
        Initialize Mimir client.

        Args:
            base_url: Mimir URL (default from MIMIR_URL env, fallback: http://mimir:9009)
            org_id: Tenant ID for multi-tenancy (default from MIMIR_ORG_ID env, fallback: anonymous)
        """
        resolved_url: str = base_url if base_url is not None else os.getenv("MIMIR_URL", "http://mimir:9009")
        self.base_url: str = resolved_url.rstrip("/")
        self.org_id: str = org_id if org_id is not None else os.getenv("MIMIR_ORG_ID", "anonymous")
        self._client: httpx.AsyncClient | None = None

    async def initialize(self) -> None:
        """Initialize HTTP client with multi-tenancy header."""
        headers: dict[str, str] = {
            "Content-Type": "application/json",
            "X-Scope-OrgID": self.org_id,
        }

        self._client = httpx.AsyncClient(
            base_url=self.base_url,
            headers=headers,
            follow_redirects=True,
            timeout=httpx.Timeout(30.0),
        )

        logger.info(f"Mimir alerting client initialized: {self.base_url} (tenant: {self.org_id})")

    async def close(self) -> None:
        """Close HTTP client."""
        if self._client:
            await self._client.aclose()
            self._client = None

    @property
    def client(self) -> httpx.AsyncClient:
        """Get HTTP client, raising if not initialized."""
        if self._client is None:
            raise RuntimeError("Client not initialized. Call initialize() first.")
        return self._client

    async def _ensure_initialized(self) -> None:
        """Ensure client is initialized, initializing if needed."""
        if self._client is None:
            await self.initialize()

    async def list_alerts(
        self,
        state: AlertState | None = None,
        severity: AlertSeverity | None = None,
        labels: dict[str, str] | None = None,
        start: datetime | None = None,
        end: datetime | None = None,
        limit: int = 100,
    ) -> AlertSearchResult:
        """
        List alerts from Mimir Alertmanager API.

        Uses GET /alertmanager/api/v2/alerts
        Same format as Grafana Alertmanager proxy.
        """
        await self._ensure_initialized()
        try:
            # Build query parameters
            params: dict[str, str] = {}
            if state:
                params["state"] = state.value

            # Add label matchers
            filter_labels: list[str] = []
            if labels:
                for key, value in labels.items():
                    filter_labels.append(f'{key}="{value}"')
            if severity:
                filter_labels.append(f'severity="{severity.value}"')
            if filter_labels:
                params["filter"] = ",".join(filter_labels)

            response = await self.client.get("/alertmanager/api/v2/alerts", params=params)
            response.raise_for_status()
            data = response.json()

            alerts: list[Alert] = []
            for alert_data in data[:limit]:
                alert_labels = alert_data.get("labels", {})
                annotations = alert_data.get("annotations", {})

                alert = Alert(
                    alert_id=alert_data.get("fingerprint", ""),
                    name=alert_labels.get("alertname", "Unknown"),
                    severity=_map_severity(alert_labels),
                    state=_map_state(alert_data.get("status", {}).get("state", "pending")),
                    message=annotations.get("summary", annotations.get("description", "")),
                    labels=alert_labels,
                    annotations=annotations,
                    started_at=_parse_iso_datetime(alert_data.get("startsAt")),
                    ended_at=_parse_iso_datetime(alert_data.get("endsAt")),
                    generator_url=alert_data.get("generatorURL"),
                )
                alerts.append(alert)

            return AlertSearchResult(
                alerts=alerts,
                total_count=len(alerts),
                next_cursor=None,
            )

        except httpx.HTTPError:
            logger.exception("Failed to list alerts from Mimir")
            return AlertSearchResult(alerts=[], total_count=0)
        except (ValueError, TypeError) as e:
            logger.warning(f"Failed to parse Mimir alerts response: {e}")
            return AlertSearchResult(alerts=[], total_count=0)

    async def get_alert(self, alert_id: str) -> Alert | None:
        """
        Get a specific alert by fingerprint.

        Mimir doesn't have a direct get-by-id endpoint, so we list and filter.
        """
        result = await self.list_alerts()
        for alert in result.alerts:
            if alert.alert_id == alert_id:
                return alert
        return None

    async def get_alerts_for_service(
        self,
        service_name: str,
        start: datetime | None = None,
        end: datetime | None = None,
        limit: int = 100,
    ) -> AlertSearchResult:
        """
        Get alerts for a specific service using label matching.

        Looks for alerts with service, job, or app labels.
        """
        # Try multiple common service label names
        for label_name in ["service", "job", "app", "service_name"]:
            result = await self.list_alerts(
                labels={label_name: service_name},
                start=start,
                end=end,
                limit=limit,
            )
            if result.alerts:
                return result

        return AlertSearchResult(alerts=[], total_count=0)

    async def list_alert_rules(
        self,
        enabled_only: bool = True,
        limit: int = 100,
    ) -> list[AlertRule]:
        """
        List configured alerting rules.

        Uses GET /prometheus/api/v1/rules
        Returns rules from all rule groups.
        """
        await self._ensure_initialized()
        try:
            response = await self.client.get("/prometheus/api/v1/rules")
            response.raise_for_status()
            data = response.json()

            rules: list[AlertRule] = []
            if data.get("status") != "success":
                return rules

            groups = data.get("data", {}).get("groups", [])
            for group in groups:
                for rule_data in group.get("rules", []):
                    # Only include alerting rules (not recording rules)
                    if rule_data.get("type") != "alerting":
                        continue

                    labels = rule_data.get("labels", {})
                    annotations = rule_data.get("annotations", {})

                    rule = AlertRule(
                        rule_id=f"{group.get('name', 'unknown')}:{rule_data.get('name', 'unknown')}",
                        name=rule_data.get("name", "Unknown"),
                        expression=rule_data.get("query", ""),
                        severity=_map_severity(labels),
                        labels=labels,
                        annotations=annotations,
                        evaluation_interval=timedelta(seconds=group.get("interval", 60)),
                        for_duration=None,  # Not directly available in rules API
                        enabled=True,  # Mimir doesn't have paused rules
                    )
                    rules.append(rule)

                    if len(rules) >= limit:
                        return rules

            return rules

        except httpx.HTTPError:
            logger.exception("Failed to list alert rules from Mimir")
            return []

    async def health_check(self) -> bool:
        """Check if Mimir is healthy via /ready endpoint."""
        try:
            await self._ensure_initialized()
            response = await self.client.get("/ready")
            return response.status_code == 200
        except Exception:
            return False
