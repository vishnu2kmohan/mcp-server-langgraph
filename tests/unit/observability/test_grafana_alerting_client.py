"""
Unit tests for GrafanaAlertingClient.

TDD Cycle: RED -> GREEN -> REFACTOR

Tests the Grafana Alerting query client which implements AlertingQueryClient
for LGTM stack deployments.

Reference: Grafana Alerting API
- GET /api/v1/provisioning/alert-rules
- GET /api/alertmanager/grafana/api/v2/alerts
"""

import gc
from datetime import timedelta
from unittest.mock import AsyncMock, MagicMock, patch

import httpx
import pytest

from mcp_server_langgraph.observability.query.backends.grafana import (
    GrafanaAlertingClient,
    _map_severity,
    _map_state,
    _parse_iso_datetime,
)
from mcp_server_langgraph.observability.query.interfaces import (
    AlertSeverity,
    AlertState,
)

# Mark as unit test
pytestmark = [
    pytest.mark.unit,
    pytest.mark.observability,
]


@pytest.mark.xdist_group(name="test_grafana_alerting_client")
class TestGrafanaAlertingClientHelpers:
    """Tests for helper functions."""

    def teardown_method(self) -> None:
        """Force GC to prevent mock accumulation in xdist workers."""
        gc.collect()

    def test_parse_iso_datetime_with_z_suffix(self) -> None:
        """
        GIVEN: ISO datetime string with Z suffix
        WHEN: _parse_iso_datetime is called
        THEN: Returns correct datetime object.
        """
        result = _parse_iso_datetime("2024-12-17T10:30:00Z")
        assert result is not None
        assert result.year == 2024
        assert result.month == 12
        assert result.day == 17
        assert result.hour == 10

    def test_parse_iso_datetime_with_offset(self) -> None:
        """
        GIVEN: ISO datetime string with offset
        WHEN: _parse_iso_datetime is called
        THEN: Returns correct datetime object.
        """
        result = _parse_iso_datetime("2024-12-17T10:30:00+00:00")
        assert result is not None
        assert result.year == 2024

    def test_parse_iso_datetime_with_none(self) -> None:
        """
        GIVEN: None value
        WHEN: _parse_iso_datetime is called
        THEN: Returns None.
        """
        result = _parse_iso_datetime(None)
        assert result is None

    def test_parse_iso_datetime_with_invalid_string(self) -> None:
        """
        GIVEN: Invalid datetime string
        WHEN: _parse_iso_datetime is called
        THEN: Returns None without raising.
        """
        result = _parse_iso_datetime("not-a-date")
        assert result is None

    @pytest.mark.parametrize(
        ("labels", "expected"),
        [
            ({"severity": "critical"}, AlertSeverity.CRITICAL),
            ({"severity": "error"}, AlertSeverity.ERROR),
            ({"severity": "warning"}, AlertSeverity.WARNING),
            ({"severity": "info"}, AlertSeverity.INFO),
            ({}, AlertSeverity.INFO),  # Default
            ({"other": "value"}, AlertSeverity.INFO),
        ],
    )
    def test_map_severity_returns_correct_enum_for_label(self, labels: dict, expected: AlertSeverity) -> None:
        """
        GIVEN: Labels dict with severity key
        WHEN: _map_severity is called
        THEN: Returns correct AlertSeverity enum.
        """
        result = _map_severity(labels)
        assert result == expected

    @pytest.mark.parametrize(
        ("state", "expected"),
        [
            ("alerting", AlertState.FIRING),
            ("firing", AlertState.FIRING),
            ("pending", AlertState.PENDING),
            ("normal", AlertState.RESOLVED),
            ("resolved", AlertState.RESOLVED),
            ("ok", AlertState.RESOLVED),
            ("silenced", AlertState.SILENCED),
            ("suppressed", AlertState.SILENCED),
            ("unknown", AlertState.PENDING),  # Default
        ],
    )
    def test_map_state_returns_correct_enum_for_string(self, state: str, expected: AlertState) -> None:
        """
        GIVEN: Grafana alert state string
        WHEN: _map_state is called
        THEN: Returns correct AlertState enum.
        """
        result = _map_state(state)
        assert result == expected


@pytest.mark.xdist_group(name="test_grafana_alerting_client")
class TestGrafanaAlertingClientInitialization:
    """Tests for client initialization."""

    def teardown_method(self) -> None:
        """Force GC to prevent mock accumulation in xdist workers."""
        gc.collect()

    def test_init_with_explicit_url(self) -> None:
        """
        GIVEN: Explicit base URL
        WHEN: Client is initialized
        THEN: Uses provided URL.
        """
        client = GrafanaAlertingClient(base_url="http://grafana.example.com:3000")
        assert client.base_url == "http://grafana.example.com:3000"

    def test_init_with_trailing_slash(self) -> None:
        """
        GIVEN: Base URL with trailing slash
        WHEN: Client is initialized
        THEN: Strips trailing slash.
        """
        client = GrafanaAlertingClient(base_url="http://grafana.example.com:3000/")
        assert client.base_url == "http://grafana.example.com:3000"

    def test_init_with_env_var(self) -> None:
        """
        GIVEN: GRAFANA_URL environment variable
        WHEN: Client is initialized without explicit URL
        THEN: Uses environment variable.
        """
        with patch.dict("os.environ", {"GRAFANA_URL": "http://env-grafana:3000"}):
            client = GrafanaAlertingClient()
            assert client.base_url == "http://env-grafana:3000"

    @pytest.mark.asyncio
    async def test_initialize_creates_http_client(self) -> None:
        """
        GIVEN: Client instance
        WHEN: initialize() is called
        THEN: HTTP client is created with headers.
        """
        client = GrafanaAlertingClient(base_url="http://localhost:3000")
        await client.initialize()

        assert client._client is not None
        assert isinstance(client._client, httpx.AsyncClient)

        await client.close()

    @pytest.mark.asyncio
    async def test_initialize_with_api_key(self) -> None:
        """
        GIVEN: Client with API key
        WHEN: initialize() is called
        THEN: Authorization header is set.
        """
        client = GrafanaAlertingClient(
            base_url="http://localhost:3000",
            api_key="glsa_test_key_123",
        )
        await client.initialize()

        assert client._client is not None
        assert "Authorization" in client._client.headers
        assert client._client.headers["Authorization"] == "Bearer glsa_test_key_123"

        await client.close()

    @pytest.mark.asyncio
    async def test_close_releases_client(self) -> None:
        """
        GIVEN: Initialized client
        WHEN: close() is called
        THEN: HTTP client is released.
        """
        client = GrafanaAlertingClient(base_url="http://localhost:3000")
        await client.initialize()
        await client.close()

        assert client._client is None


@pytest.mark.xdist_group(name="test_grafana_alerting_client")
class TestGrafanaAlertingClientListAlerts:
    """Tests for list_alerts method."""

    def teardown_method(self) -> None:
        """Force GC to prevent mock accumulation in xdist workers."""
        gc.collect()

    @pytest.mark.asyncio
    async def test_list_alerts_success(self) -> None:
        """
        GIVEN: Grafana with active alerts
        WHEN: list_alerts() is called
        THEN: Returns AlertSearchResult with parsed alerts.
        """
        client = GrafanaAlertingClient(base_url="http://localhost:3000")
        await client.initialize()

        # Mock response from Grafana Alertmanager API
        mock_response = MagicMock()
        mock_response.json.return_value = [
            {
                "fingerprint": "alert-001",
                "labels": {
                    "alertname": "HighMemory",
                    "severity": "warning",
                    "service": "mcp-server",
                },
                "annotations": {
                    "summary": "Memory usage is high",
                    "description": "Current memory at 85%",
                },
                "status": {"state": "firing"},
                "startsAt": "2024-12-17T10:00:00Z",
                "endsAt": None,
                "generatorURL": "http://grafana/alerting/123",
            },
            {
                "fingerprint": "alert-002",
                "labels": {
                    "alertname": "HighLatency",
                    "severity": "critical",
                },
                "annotations": {
                    "summary": "API latency spike",
                },
                "status": {"state": "alerting"},
                "startsAt": "2024-12-17T10:30:00Z",
            },
        ]
        mock_response.raise_for_status = MagicMock()

        with patch.object(client._client, "get", new_callable=AsyncMock) as mock_get:
            mock_get.return_value = mock_response

            result = await client.list_alerts()

            assert result.total_count == 2
            assert len(result.alerts) == 2

            alert1 = result.alerts[0]
            assert alert1.alert_id == "alert-001"
            assert alert1.name == "HighMemory"
            assert alert1.severity == AlertSeverity.WARNING
            assert alert1.state == AlertState.FIRING
            assert alert1.message == "Memory usage is high"

            alert2 = result.alerts[1]
            assert alert2.alert_id == "alert-002"
            assert alert2.severity == AlertSeverity.CRITICAL

            mock_get.assert_called_once_with(
                "/api/alertmanager/grafana/api/v2/alerts",
                params={},
            )

        await client.close()

    @pytest.mark.asyncio
    async def test_list_alerts_with_state_filter(self) -> None:
        """
        GIVEN: State filter
        WHEN: list_alerts(state=FIRING) is called
        THEN: Passes state parameter to API.
        """
        client = GrafanaAlertingClient(base_url="http://localhost:3000")
        await client.initialize()

        mock_response = MagicMock()
        mock_response.json.return_value = []
        mock_response.raise_for_status = MagicMock()

        with patch.object(client._client, "get", new_callable=AsyncMock) as mock_get:
            mock_get.return_value = mock_response

            await client.list_alerts(state=AlertState.FIRING)

            mock_get.assert_called_once()
            call_params = mock_get.call_args[1]["params"]
            assert call_params["state"] == "firing"

        await client.close()

    @pytest.mark.asyncio
    async def test_list_alerts_with_severity_filter(self) -> None:
        """
        GIVEN: Severity filter
        WHEN: list_alerts(severity=CRITICAL) is called
        THEN: Passes severity as label filter to API.
        """
        client = GrafanaAlertingClient(base_url="http://localhost:3000")
        await client.initialize()

        mock_response = MagicMock()
        mock_response.json.return_value = []
        mock_response.raise_for_status = MagicMock()

        with patch.object(client._client, "get", new_callable=AsyncMock) as mock_get:
            mock_get.return_value = mock_response

            await client.list_alerts(severity=AlertSeverity.CRITICAL)

            mock_get.assert_called_once()
            call_params = mock_get.call_args[1]["params"]
            assert 'severity="critical"' in call_params["filter"]

        await client.close()

    @pytest.mark.asyncio
    async def test_list_alerts_http_error_returns_empty(self) -> None:
        """
        GIVEN: Grafana returns HTTP error
        WHEN: list_alerts() is called
        THEN: Returns empty result without raising.
        """
        client = GrafanaAlertingClient(base_url="http://localhost:3000")
        await client.initialize()

        with patch.object(client._client, "get", new_callable=AsyncMock) as mock_get:
            mock_get.side_effect = httpx.HTTPError("Connection refused")

            result = await client.list_alerts()

            assert result.total_count == 0
            assert len(result.alerts) == 0

        await client.close()

    @pytest.mark.asyncio
    async def test_list_alerts_respects_limit(self) -> None:
        """
        GIVEN: More alerts than limit
        WHEN: list_alerts(limit=1) is called
        THEN: Returns only up to limit.
        """
        client = GrafanaAlertingClient(base_url="http://localhost:3000")
        await client.initialize()

        mock_response = MagicMock()
        mock_response.json.return_value = [
            {
                "fingerprint": f"alert-{i}",
                "labels": {"alertname": f"Alert{i}"},
                "annotations": {},
                "status": {"state": "firing"},
            }
            for i in range(5)
        ]
        mock_response.raise_for_status = MagicMock()

        with patch.object(client._client, "get", new_callable=AsyncMock) as mock_get:
            mock_get.return_value = mock_response

            result = await client.list_alerts(limit=2)

            assert len(result.alerts) == 2

        await client.close()


@pytest.mark.xdist_group(name="test_grafana_alerting_client")
class TestGrafanaAlertingClientGetAlert:
    """Tests for get_alert method."""

    def teardown_method(self) -> None:
        """Force GC to prevent mock accumulation in xdist workers."""
        gc.collect()

    @pytest.mark.asyncio
    async def test_get_alert_found(self) -> None:
        """
        GIVEN: Alert exists with given ID
        WHEN: get_alert(alert_id) is called
        THEN: Returns the matching alert.
        """
        client = GrafanaAlertingClient(base_url="http://localhost:3000")
        await client.initialize()

        mock_response = MagicMock()
        mock_response.json.return_value = [
            {
                "fingerprint": "target-alert",
                "labels": {"alertname": "TargetAlert"},
                "annotations": {"summary": "Found it"},
                "status": {"state": "firing"},
            },
            {
                "fingerprint": "other-alert",
                "labels": {"alertname": "OtherAlert"},
                "annotations": {},
                "status": {"state": "pending"},
            },
        ]
        mock_response.raise_for_status = MagicMock()

        with patch.object(client._client, "get", new_callable=AsyncMock) as mock_get:
            mock_get.return_value = mock_response

            result = await client.get_alert("target-alert")

            assert result is not None
            assert result.alert_id == "target-alert"
            assert result.name == "TargetAlert"

        await client.close()

    @pytest.mark.asyncio
    async def test_get_alert_not_found(self) -> None:
        """
        GIVEN: Alert does not exist
        WHEN: get_alert(alert_id) is called
        THEN: Returns None.
        """
        client = GrafanaAlertingClient(base_url="http://localhost:3000")
        await client.initialize()

        mock_response = MagicMock()
        mock_response.json.return_value = []
        mock_response.raise_for_status = MagicMock()

        with patch.object(client._client, "get", new_callable=AsyncMock) as mock_get:
            mock_get.return_value = mock_response

            result = await client.get_alert("nonexistent")

            assert result is None

        await client.close()


@pytest.mark.xdist_group(name="test_grafana_alerting_client")
class TestGrafanaAlertingClientGetAlertsForService:
    """Tests for get_alerts_for_service method."""

    def teardown_method(self) -> None:
        """Force GC to prevent mock accumulation in xdist workers."""
        gc.collect()

    @pytest.mark.asyncio
    async def test_get_alerts_for_service_with_service_label(self) -> None:
        """
        GIVEN: Alerts with 'service' label
        WHEN: get_alerts_for_service('mcp-server') is called
        THEN: Returns alerts matching service label.
        """
        client = GrafanaAlertingClient(base_url="http://localhost:3000")
        await client.initialize()

        mock_response = MagicMock()
        mock_response.json.return_value = [
            {
                "fingerprint": "alert-001",
                "labels": {"alertname": "ServiceAlert", "service": "mcp-server"},
                "annotations": {},
                "status": {"state": "firing"},
            },
        ]
        mock_response.raise_for_status = MagicMock()

        with patch.object(client._client, "get", new_callable=AsyncMock) as mock_get:
            mock_get.return_value = mock_response

            result = await client.get_alerts_for_service("mcp-server")

            assert len(result.alerts) == 1
            assert result.alerts[0].alert_id == "alert-001"

        await client.close()

    @pytest.mark.asyncio
    async def test_get_alerts_for_service_tries_multiple_labels(self) -> None:
        """
        GIVEN: Service uses 'job' label instead of 'service'
        WHEN: get_alerts_for_service() is called
        THEN: Tries 'service', 'job', 'app', 'service_name' labels.
        """
        client = GrafanaAlertingClient(base_url="http://localhost:3000")
        await client.initialize()

        # First call (service label) returns empty
        # Second call (job label) returns alert
        call_count = 0

        async def mock_get(*args, **kwargs):
            nonlocal call_count
            call_count += 1
            mock_resp = MagicMock()
            mock_resp.raise_for_status = MagicMock()

            if call_count == 1:  # service label query
                mock_resp.json.return_value = []
            else:  # job label query
                mock_resp.json.return_value = [
                    {
                        "fingerprint": "job-alert",
                        "labels": {"alertname": "JobAlert"},
                        "annotations": {},
                        "status": {"state": "firing"},
                    },
                ]
            return mock_resp

        with patch.object(client._client, "get", side_effect=mock_get):
            result = await client.get_alerts_for_service("my-service")

            assert len(result.alerts) == 1
            assert call_count == 2  # Tried service, then job

        await client.close()


@pytest.mark.xdist_group(name="test_grafana_alerting_client")
class TestGrafanaAlertingClientListAlertRules:
    """Tests for list_alert_rules method."""

    def teardown_method(self) -> None:
        """Force GC to prevent mock accumulation in xdist workers."""
        gc.collect()

    @pytest.mark.asyncio
    async def test_list_alert_rules_success(self) -> None:
        """
        GIVEN: Grafana with configured alert rules
        WHEN: list_alert_rules() is called
        THEN: Returns list of AlertRule objects.
        """
        client = GrafanaAlertingClient(base_url="http://localhost:3000")
        await client.initialize()

        mock_response = MagicMock()
        mock_response.json.return_value = [
            {
                "uid": "rule-001",
                "title": "High Memory Usage",
                "isPaused": False,
                "intervalSeconds": 60,
                "for": 300,
                "labels": {"severity": "warning"},
                "annotations": {"summary": "Memory alert rule"},
                "data": [
                    {
                        "model": {
                            "expr": "node_memory_MemFree_bytes / node_memory_MemTotal_bytes < 0.1",
                        },
                    },
                ],
            },
            {
                "uid": "rule-002",
                "title": "API Error Rate",
                "isPaused": True,  # Paused rule
                "intervalSeconds": 30,
                "labels": {"severity": "critical"},
                "annotations": {},
                "data": [],
            },
        ]
        mock_response.raise_for_status = MagicMock()

        with patch.object(client._client, "get", new_callable=AsyncMock) as mock_get:
            mock_get.return_value = mock_response

            # enabled_only=True by default, should filter out paused rule
            result = await client.list_alert_rules()

            assert len(result) == 1
            rule = result[0]
            assert rule.rule_id == "rule-001"
            assert rule.name == "High Memory Usage"
            assert rule.severity == AlertSeverity.WARNING
            assert rule.enabled is True
            assert rule.evaluation_interval == timedelta(seconds=60)
            assert rule.for_duration == timedelta(seconds=300)

            mock_get.assert_called_once_with("/api/v1/provisioning/alert-rules")

        await client.close()

    @pytest.mark.asyncio
    async def test_list_alert_rules_include_disabled(self) -> None:
        """
        GIVEN: Mix of enabled and disabled rules
        WHEN: list_alert_rules(enabled_only=False) is called
        THEN: Returns all rules including paused.
        """
        client = GrafanaAlertingClient(base_url="http://localhost:3000")
        await client.initialize()

        mock_response = MagicMock()
        mock_response.json.return_value = [
            {"uid": "rule-001", "title": "Active", "isPaused": False, "labels": {}, "annotations": {}, "data": []},
            {"uid": "rule-002", "title": "Paused", "isPaused": True, "labels": {}, "annotations": {}, "data": []},
        ]
        mock_response.raise_for_status = MagicMock()

        with patch.object(client._client, "get", new_callable=AsyncMock) as mock_get:
            mock_get.return_value = mock_response

            result = await client.list_alert_rules(enabled_only=False)

            assert len(result) == 2

        await client.close()

    @pytest.mark.asyncio
    async def test_list_alert_rules_http_error_returns_empty(self) -> None:
        """
        GIVEN: Grafana returns HTTP error
        WHEN: list_alert_rules() is called
        THEN: Returns empty list without raising.
        """
        client = GrafanaAlertingClient(base_url="http://localhost:3000")
        await client.initialize()

        with patch.object(client._client, "get", new_callable=AsyncMock) as mock_get:
            mock_get.side_effect = httpx.HTTPError("Connection refused")

            result = await client.list_alert_rules()

            assert result == []

        await client.close()


@pytest.mark.xdist_group(name="test_grafana_alerting_client")
class TestGrafanaAlertingClientHealthCheck:
    """Tests for health_check method."""

    def teardown_method(self) -> None:
        """Force GC to prevent mock accumulation in xdist workers."""
        gc.collect()

    @pytest.mark.asyncio
    async def test_health_check_healthy(self) -> None:
        """
        GIVEN: Grafana is healthy
        WHEN: health_check() is called
        THEN: Returns True.
        """
        client = GrafanaAlertingClient(base_url="http://localhost:3000")
        await client.initialize()

        mock_response = MagicMock()
        mock_response.status_code = 200

        with patch.object(client._client, "get", new_callable=AsyncMock) as mock_get:
            mock_get.return_value = mock_response

            result = await client.health_check()

            assert result is True
            mock_get.assert_called_once_with("/api/health")

        await client.close()

    @pytest.mark.asyncio
    async def test_health_check_unhealthy(self) -> None:
        """
        GIVEN: Grafana returns non-200 status
        WHEN: health_check() is called
        THEN: Returns False.
        """
        client = GrafanaAlertingClient(base_url="http://localhost:3000")
        await client.initialize()

        mock_response = MagicMock()
        mock_response.status_code = 503

        with patch.object(client._client, "get", new_callable=AsyncMock) as mock_get:
            mock_get.return_value = mock_response

            result = await client.health_check()

            assert result is False

        await client.close()

    @pytest.mark.asyncio
    async def test_health_check_connection_error(self) -> None:
        """
        GIVEN: Cannot connect to Grafana
        WHEN: health_check() is called
        THEN: Returns False without raising.
        """
        client = GrafanaAlertingClient(base_url="http://localhost:3000")
        await client.initialize()

        with patch.object(client._client, "get", new_callable=AsyncMock) as mock_get:
            mock_get.side_effect = Exception("Connection refused")

            result = await client.health_check()

            assert result is False

        await client.close()
