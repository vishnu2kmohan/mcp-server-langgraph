"""
Grafana Alerting query client.

Implements AlertingQueryClient for Grafana Alerting API (Unified Alerting).
Used in LGTM stack (Loki, Grafana, Tempo, Mimir) deployments.

Configuration:
    GRAFANA_URL: Grafana URL (default: http://grafana:3000)
    GRAFANA_API_KEY: API key for authentication (optional, for service accounts)
    GRAFANA_USE_OIDC: Use OIDC/Keycloak authentication (default: false)
    GRAFANA_USERNAME: Basic auth username (optional, fallback if no OIDC/API key)
    GRAFANA_PASSWORD: Basic auth password (optional, fallback if no OIDC/API key)

OIDC authentication uses Keycloak client credentials:
    KEYCLOAK_SERVER_URL: Keycloak URL (e.g., http://keycloak:8080/authn)
    KEYCLOAK_REALM: Realm name (default: default)
    OAUTH2_CLIENT_ID: Client ID for token acquisition
    OAUTH2_CLIENT_SECRET: Client secret for token acquisition

Example:
    export GRAFANA_URL=http://localhost:3000
    export GRAFANA_USE_OIDC=true
"""

import logging
import os
import time
from datetime import datetime, timedelta

import httpx

# OIDC token refresh buffer (refresh before expiration)
OIDC_TOKEN_REFRESH_BUFFER_SECONDS = 30

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
        return datetime.fromisoformat(value)
    except (ValueError, TypeError):
        return None


def _map_severity(labels: dict[str, str]) -> AlertSeverity:
    """Map Grafana alert labels to severity level."""
    severity = labels.get("severity", "").lower()
    if severity in ("critical", "error"):
        return AlertSeverity.CRITICAL if severity == "critical" else AlertSeverity.ERROR
    elif severity == "warning":
        return AlertSeverity.WARNING
    return AlertSeverity.INFO


def _map_state(state: str) -> AlertState:
    """Map Grafana alert state to AlertState enum."""
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


class GrafanaAlertingClient(AlertingQueryClient):
    """
    Grafana Alerting API client.

    Queries Grafana's Unified Alerting API for alert instances and rules.

    API Reference:
    - GET /api/v1/provisioning/alert-rules - List alert rules
    - GET /api/alertmanager/grafana/api/v2/alerts - List active alerts
    """

    def __init__(
        self,
        base_url: str | None = None,
        api_key: str | None = None,
        username: str | None = None,
        password: str | None = None,
        use_oidc: bool | None = None,
    ) -> None:
        """
        Initialize Grafana client.

        Args:
            base_url: Grafana URL (default from GRAFANA_URL env)
            api_key: API key for auth (default from GRAFANA_API_KEY env)
            username: Basic auth username (default from GRAFANA_USERNAME env)
            password: Basic auth password (default from GRAFANA_PASSWORD env)
            use_oidc: Use OIDC authentication (default from GRAFANA_USE_OIDC env)
        """
        resolved_url = base_url or os.getenv("GRAFANA_URL") or "http://grafana:3000"
        self.base_url = resolved_url.rstrip("/")
        self.api_key = api_key or os.getenv("GRAFANA_API_KEY")
        self.username = username or os.getenv("GRAFANA_USERNAME")
        self.password = password or os.getenv("GRAFANA_PASSWORD")
        self.use_oidc = use_oidc if use_oidc is not None else os.getenv("GRAFANA_USE_OIDC", "").lower() in ("true", "1", "yes")
        self._client: httpx.AsyncClient | None = None

        # OIDC token cache
        self._oidc_access_token: str | None = None
        self._oidc_token_expires_at: float = 0.0

    async def _get_oidc_token(self) -> str:
        """Obtain OIDC access token from Keycloak using client credentials grant."""
        # Check cached token
        if self._oidc_access_token:
            if time.time() < (self._oidc_token_expires_at - OIDC_TOKEN_REFRESH_BUFFER_SECONDS):
                return self._oidc_access_token

        # Get Keycloak configuration from environment
        keycloak_url = os.getenv("KEYCLOAK_SERVER_URL", "http://keycloak:8080/authn")
        realm = os.getenv("KEYCLOAK_REALM", "default")
        client_id = os.getenv("OAUTH2_CLIENT_ID", "mcp-server")
        client_secret = os.getenv("OAUTH2_CLIENT_SECRET", "")

        token_endpoint = f"{keycloak_url.rstrip('/')}/realms/{realm}/protocol/openid-connect/token"

        logger.info(
            "Obtaining OIDC token for Grafana API",
            extra={"client_id": client_id, "token_endpoint": token_endpoint},
        )

        async with httpx.AsyncClient() as client:
            response = await client.post(
                token_endpoint,
                data={
                    "grant_type": "client_credentials",
                    "client_id": client_id,
                    "client_secret": client_secret,
                },
                timeout=10.0,
            )
            response.raise_for_status()

            token_response = response.json()
            access_token = token_response.get("access_token")
            expires_in = token_response.get("expires_in", 300)

            if not access_token:
                raise RuntimeError("No access_token in Keycloak token response")

            # Cache the token
            self._oidc_access_token = access_token
            self._oidc_token_expires_at = time.time() + expires_in

            logger.info("OIDC token obtained successfully for Grafana API")
            return str(access_token)

    async def initialize(self) -> None:
        """Initialize HTTP client with auth."""
        headers: dict[str, str] = {"Content-Type": "application/json"}

        auth = None
        if self.use_oidc:
            # Obtain initial OIDC token
            token = await self._get_oidc_token()
            headers["Authorization"] = f"Bearer {token}"
            logger.info(f"Grafana alerting client initialized with OIDC: {self.base_url}")
        elif self.api_key:
            headers["Authorization"] = f"Bearer {self.api_key}"
            logger.info(f"Grafana alerting client initialized with API key: {self.base_url}")
        elif self.username and self.password:
            auth = httpx.BasicAuth(self.username, self.password)
            logger.info(f"Grafana alerting client initialized with basic auth: {self.base_url}")
        else:
            logger.warning(f"Grafana alerting client initialized without auth: {self.base_url}")

        self._client = httpx.AsyncClient(
            base_url=self.base_url,
            headers=headers,
            auth=auth,
            timeout=httpx.Timeout(30.0),
        )

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
        List alerts from Grafana Alertmanager API.

        Uses GET /api/alertmanager/grafana/api/v2/alerts
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

            response = await self.client.get("/api/alertmanager/grafana/api/v2/alerts", params=params)
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
                next_cursor=None,  # Grafana API doesn't support pagination
            )

        except httpx.HTTPError:
            logger.exception("Failed to list alerts from Grafana")
            return AlertSearchResult(alerts=[], total_count=0)
        except (ValueError, TypeError) as e:
            logger.warning(f"Failed to parse Grafana alerts response: {e}")
            return AlertSearchResult(alerts=[], total_count=0)

    async def get_alert(self, alert_id: str) -> Alert | None:
        """
        Get a specific alert by fingerprint.

        Grafana doesn't have a direct get-by-id endpoint, so we list and filter.
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

        Uses GET /api/v1/provisioning/alert-rules
        """
        await self._ensure_initialized()
        try:
            response = await self.client.get("/api/v1/provisioning/alert-rules")
            response.raise_for_status()
            data = response.json()

            rules: list[AlertRule] = []
            for rule_data in data[:limit]:
                # Skip paused rules if enabled_only
                if enabled_only and rule_data.get("isPaused", False):
                    continue

                labels = rule_data.get("labels", {})
                annotations = rule_data.get("annotations", {})

                # Safely extract expression from nested data structure
                data_list = rule_data.get("data", [])
                expression = ""
                if data_list:
                    expression = data_list[0].get("model", {}).get("expr", "")

                rule = AlertRule(
                    rule_id=rule_data.get("uid", ""),
                    name=rule_data.get("title", "Unknown"),
                    expression=expression,
                    severity=_map_severity(labels),
                    labels=labels,
                    annotations=annotations,
                    evaluation_interval=timedelta(seconds=rule_data.get("intervalSeconds", 60)),
                    for_duration=timedelta(seconds=rule_data.get("for", 0)) if rule_data.get("for") else None,
                    enabled=not rule_data.get("isPaused", False),
                )
                rules.append(rule)

            return rules

        except httpx.HTTPError:
            logger.exception("Failed to list alert rules from Grafana")
            return []

    async def health_check(self) -> bool:
        """Check if Grafana is healthy."""
        try:
            await self._ensure_initialized()
            response = await self.client.get("/api/health")
            return response.status_code == 200
        except Exception:
            return False
