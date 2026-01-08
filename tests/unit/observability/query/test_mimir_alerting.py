"""
MimirAlertingClient Unit Tests

TDD tests for querying alerts directly from Mimir's built-in Alertmanager.
Mimir uses the same Alertmanager v2 API format as Grafana but served directly.

RED Phase: These tests define expected behavior before implementation.
"""

import gc
from unittest.mock import AsyncMock, MagicMock

import httpx
import pytest

from mcp_server_langgraph.observability.query.interfaces import (
    Alert,
    AlertSearchResult,
    AlertSeverity,
    AlertState,
)

pytestmark = pytest.mark.unit


# =============================================================================
# Test Constants
# =============================================================================

MIMIR_BASE_URL = "http://mimir:9009"
MIMIR_ORG_ID = "test-tenant"


# =============================================================================
# Mock Alert Data
# =============================================================================

MOCK_ALERTMANAGER_RESPONSE = [
    {
        "fingerprint": "alert-mimir-1",
        "labels": {
            "alertname": "HighErrorRate",
            "severity": "critical",
            "service": "api-gateway",
            "namespace": "production",
        },
        "annotations": {
            "summary": "Error rate exceeded threshold",
            "description": "API gateway error rate is above 5%",
        },
        "status": {
            "state": "firing",
        },
        "startsAt": "2024-01-01T10:00:00Z",
        "endsAt": "0001-01-01T00:00:00Z",
        "generatorURL": "http://mimir:9009/alertmanager/alert-1",
    },
    {
        "fingerprint": "alert-mimir-2",
        "labels": {
            "alertname": "SlowQueryTime",
            "severity": "warning",
            "service": "db-service",
            "namespace": "production",
        },
        "annotations": {
            "summary": "Query latency high",
        },
        "status": {
            "state": "pending",
        },
        "startsAt": "2024-01-01T10:05:00Z",
        "endsAt": "0001-01-01T00:00:00Z",
    },
]


# =============================================================================
# Tests
# =============================================================================


@pytest.mark.xdist_group(name="mimir_alerting")
class TestMimirAlertingClient:
    """Unit tests for MimirAlertingClient."""

    def teardown_method(self) -> None:
        """Force GC to prevent mock accumulation in xdist workers."""
        gc.collect()

    @pytest.mark.asyncio
    async def test_initialize_creates_http_client_with_headers(self) -> None:
        """GIVEN config WHEN initialize() THEN creates client with X-Scope-OrgID header."""
        # Import here to allow test to fail if module doesn't exist yet
        from mcp_server_langgraph.observability.query.backends.mimir import (
            MimirAlertingClient,
        )

        client = MimirAlertingClient(base_url=MIMIR_BASE_URL, org_id=MIMIR_ORG_ID)

        await client.initialize()

        assert client._client is not None
        assert client._client.headers["X-Scope-OrgID"] == MIMIR_ORG_ID
        await client.close()

    @pytest.mark.asyncio
    async def test_list_alerts_calls_mimir_alertmanager_api(self) -> None:
        """GIVEN initialized client WHEN list_alerts() THEN calls /alertmanager/api/v2/alerts."""
        from mcp_server_langgraph.observability.query.backends.mimir import (
            MimirAlertingClient,
        )

        client = MimirAlertingClient(base_url=MIMIR_BASE_URL, org_id=MIMIR_ORG_ID)

        # Mock the HTTP client - use MagicMock for response since json() is sync
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = MOCK_ALERTMANAGER_RESPONSE
        mock_response.raise_for_status = MagicMock()

        mock_http_client = AsyncMock(spec=httpx.AsyncClient)
        mock_http_client.get.return_value = mock_response
        client._client = mock_http_client

        result = await client.list_alerts()

        # Verify API call
        mock_http_client.get.assert_called_once()
        call_args = mock_http_client.get.call_args
        assert "/alertmanager/api/v2/alerts" in str(call_args)

        # Verify result structure
        assert isinstance(result, AlertSearchResult)
        assert len(result.alerts) == 2
        assert result.alerts[0].name == "HighErrorRate"
        assert result.alerts[0].state == AlertState.FIRING
        assert result.alerts[0].severity == AlertSeverity.CRITICAL
        assert result.alerts[1].name == "SlowQueryTime"
        assert result.alerts[1].state == AlertState.PENDING

    @pytest.mark.asyncio
    async def test_multitenancy_includes_orgid_header(self) -> None:
        """GIVEN multitenancy enabled WHEN list_alerts() THEN X-Scope-OrgID header is set."""
        from mcp_server_langgraph.observability.query.backends.mimir import (
            MimirAlertingClient,
        )

        custom_tenant = "custom-tenant-id"
        client = MimirAlertingClient(base_url=MIMIR_BASE_URL, org_id=custom_tenant)
        await client.initialize()

        # Verify tenant header is set
        assert client._client is not None
        assert client._client.headers["X-Scope-OrgID"] == custom_tenant
        await client.close()

    @pytest.mark.asyncio
    async def test_health_check_uses_ready_endpoint(self) -> None:
        """GIVEN Mimir is healthy WHEN health_check() THEN returns True via /ready."""
        from mcp_server_langgraph.observability.query.backends.mimir import (
            MimirAlertingClient,
        )

        client = MimirAlertingClient(base_url=MIMIR_BASE_URL, org_id=MIMIR_ORG_ID)

        mock_response = MagicMock()
        mock_response.status_code = 200

        mock_http_client = AsyncMock(spec=httpx.AsyncClient)
        mock_http_client.get.return_value = mock_response
        client._client = mock_http_client

        result = await client.health_check()

        assert result is True
        mock_http_client.get.assert_called_once_with("/ready")

    @pytest.mark.asyncio
    async def test_health_check_returns_false_on_failure(self) -> None:
        """GIVEN Mimir is unhealthy WHEN health_check() THEN returns False."""
        from mcp_server_langgraph.observability.query.backends.mimir import (
            MimirAlertingClient,
        )

        client = MimirAlertingClient(base_url=MIMIR_BASE_URL, org_id=MIMIR_ORG_ID)

        mock_http_client = AsyncMock(spec=httpx.AsyncClient)
        mock_http_client.get.side_effect = httpx.RequestError("Connection refused")
        client._client = mock_http_client

        result = await client.health_check()

        assert result is False

    @pytest.mark.asyncio
    async def test_list_alerts_filters_by_state(self) -> None:
        """GIVEN state filter WHEN list_alerts(state=FIRING) THEN passes filter param."""
        from mcp_server_langgraph.observability.query.backends.mimir import (
            MimirAlertingClient,
        )

        client = MimirAlertingClient(base_url=MIMIR_BASE_URL, org_id=MIMIR_ORG_ID)

        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = [MOCK_ALERTMANAGER_RESPONSE[0]]
        mock_response.raise_for_status = MagicMock()

        mock_http_client = AsyncMock(spec=httpx.AsyncClient)
        mock_http_client.get.return_value = mock_response
        client._client = mock_http_client

        result = await client.list_alerts(state=AlertState.FIRING)

        # Verify filter was passed
        call_args = mock_http_client.get.call_args
        params = call_args.kwargs.get("params", {})
        assert params.get("state") == "firing"
        assert len(result.alerts) == 1

    @pytest.mark.asyncio
    async def test_list_alerts_handles_empty_response(self) -> None:
        """GIVEN no alerts WHEN list_alerts() THEN returns empty result."""
        from mcp_server_langgraph.observability.query.backends.mimir import (
            MimirAlertingClient,
        )

        client = MimirAlertingClient(base_url=MIMIR_BASE_URL, org_id=MIMIR_ORG_ID)

        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = []
        mock_response.raise_for_status = MagicMock()

        mock_http_client = AsyncMock(spec=httpx.AsyncClient)
        mock_http_client.get.return_value = mock_response
        client._client = mock_http_client

        result = await client.list_alerts()

        assert len(result.alerts) == 0
        assert result.total_count == 0

    @pytest.mark.asyncio
    async def test_get_alert_by_id(self) -> None:
        """GIVEN alert exists WHEN get_alert(id) THEN returns Alert."""
        from mcp_server_langgraph.observability.query.backends.mimir import (
            MimirAlertingClient,
        )

        client = MimirAlertingClient(base_url=MIMIR_BASE_URL, org_id=MIMIR_ORG_ID)

        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = MOCK_ALERTMANAGER_RESPONSE
        mock_response.raise_for_status = MagicMock()

        mock_http_client = AsyncMock(spec=httpx.AsyncClient)
        mock_http_client.get.return_value = mock_response
        client._client = mock_http_client

        result = await client.get_alert("alert-mimir-1")

        assert result is not None
        assert isinstance(result, Alert)
        assert result.alert_id == "alert-mimir-1"
        assert result.name == "HighErrorRate"

    @pytest.mark.asyncio
    async def test_get_alert_returns_none_if_not_found(self) -> None:
        """GIVEN alert doesn't exist WHEN get_alert(id) THEN returns None."""
        from mcp_server_langgraph.observability.query.backends.mimir import (
            MimirAlertingClient,
        )

        client = MimirAlertingClient(base_url=MIMIR_BASE_URL, org_id=MIMIR_ORG_ID)

        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = MOCK_ALERTMANAGER_RESPONSE
        mock_response.raise_for_status = MagicMock()

        mock_http_client = AsyncMock(spec=httpx.AsyncClient)
        mock_http_client.get.return_value = mock_response
        client._client = mock_http_client

        result = await client.get_alert("non-existent-id")

        assert result is None

    @pytest.mark.asyncio
    async def test_get_alerts_for_service(self) -> None:
        """GIVEN service name WHEN get_alerts_for_service() THEN filters by service label."""
        from mcp_server_langgraph.observability.query.backends.mimir import (
            MimirAlertingClient,
        )

        client = MimirAlertingClient(base_url=MIMIR_BASE_URL, org_id=MIMIR_ORG_ID)

        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = [MOCK_ALERTMANAGER_RESPONSE[0]]
        mock_response.raise_for_status = MagicMock()

        mock_http_client = AsyncMock(spec=httpx.AsyncClient)
        mock_http_client.get.return_value = mock_response
        client._client = mock_http_client

        result = await client.get_alerts_for_service("api-gateway")

        assert len(result.alerts) == 1
        assert result.alerts[0].labels.get("service") == "api-gateway"

    @pytest.mark.asyncio
    async def test_list_alert_rules_calls_rules_api(self) -> None:
        """GIVEN Mimir has alert rules WHEN list_alert_rules() THEN queries /prometheus/api/v1/rules."""
        from mcp_server_langgraph.observability.query.backends.mimir import (
            MimirAlertingClient,
        )

        client = MimirAlertingClient(base_url=MIMIR_BASE_URL, org_id=MIMIR_ORG_ID)

        mock_rules_response = {
            "status": "success",
            "data": {
                "groups": [
                    {
                        "name": "test-rules",
                        "rules": [
                            {
                                "name": "HighErrorRate",
                                "query": 'rate(http_requests_total{status="500"}[5m]) > 0.05',
                                "labels": {"severity": "critical"},
                                "annotations": {"summary": "High error rate"},
                                "state": "firing",
                                "type": "alerting",
                            },
                        ],
                    },
                ],
            },
        }

        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = mock_rules_response
        mock_response.raise_for_status = MagicMock()

        mock_http_client = AsyncMock(spec=httpx.AsyncClient)
        mock_http_client.get.return_value = mock_response
        client._client = mock_http_client

        result = await client.list_alert_rules()

        mock_http_client.get.assert_called_once_with("/prometheus/api/v1/rules")
        assert len(result) >= 1
        assert result[0].name == "HighErrorRate"

    @pytest.mark.asyncio
    async def test_close_cleans_up_http_client(self) -> None:
        """GIVEN initialized client WHEN close() THEN HTTP client is cleaned up."""
        from mcp_server_langgraph.observability.query.backends.mimir import (
            MimirAlertingClient,
        )

        client = MimirAlertingClient(base_url=MIMIR_BASE_URL, org_id=MIMIR_ORG_ID)
        await client.initialize()

        assert client._client is not None

        await client.close()

        assert client._client is None

    @pytest.mark.asyncio
    async def test_uses_environment_defaults(self) -> None:
        """GIVEN no explicit config WHEN created THEN uses env defaults."""
        import os
        from unittest.mock import patch

        from mcp_server_langgraph.observability.query.backends.mimir import (
            MimirAlertingClient,
        )

        with patch.dict(
            os.environ,
            {
                "MIMIR_URL": "http://custom-mimir:8080",
                "MIMIR_ORG_ID": "env-tenant",
            },
        ):
            client = MimirAlertingClient()

            assert client.base_url == "http://custom-mimir:8080"
            assert client.org_id == "env-tenant"

    @pytest.mark.asyncio
    async def test_handles_http_error_gracefully(self) -> None:
        """GIVEN HTTP error WHEN list_alerts() THEN returns empty result without raising."""
        from mcp_server_langgraph.observability.query.backends.mimir import (
            MimirAlertingClient,
        )

        client = MimirAlertingClient(base_url=MIMIR_BASE_URL, org_id=MIMIR_ORG_ID)

        mock_http_client = AsyncMock(spec=httpx.AsyncClient)
        mock_http_client.get.side_effect = httpx.HTTPStatusError(
            "Internal Server Error",
            request=MagicMock(),
            response=MagicMock(status_code=500),
        )
        client._client = mock_http_client

        result = await client.list_alerts()

        assert isinstance(result, AlertSearchResult)
        assert len(result.alerts) == 0
        assert result.total_count == 0


# =============================================================================
# Coverage Enhancement Tests - Helper Functions
# =============================================================================


@pytest.mark.xdist_group(name="mimir_alerting_helpers")
class TestMimirHelperFunctions:
    """Tests for _parse_iso_datetime, _map_severity, _map_state helper functions."""

    def teardown_method(self) -> None:
        """Force GC to prevent mock accumulation in xdist workers."""
        gc.collect()

    def test_parse_iso_datetime_empty_value_returns_none(self) -> None:
        """GIVEN empty string WHEN _parse_iso_datetime() THEN returns None."""
        from mcp_server_langgraph.observability.query.backends.mimir import (
            _parse_iso_datetime,
        )

        assert _parse_iso_datetime("") is None
        assert _parse_iso_datetime(None) is None

    def test_parse_iso_datetime_z_suffix_parsed(self) -> None:
        """GIVEN datetime with Z suffix WHEN _parse_iso_datetime() THEN parses correctly."""
        from mcp_server_langgraph.observability.query.backends.mimir import (
            _parse_iso_datetime,
        )

        result = _parse_iso_datetime("2024-01-15T10:30:00Z")

        assert result is not None
        assert result.year == 2024
        assert result.month == 1
        assert result.day == 15
        assert result.hour == 10
        assert result.minute == 30

    def test_parse_iso_datetime_invalid_format_returns_none(self) -> None:
        """GIVEN invalid datetime string WHEN _parse_iso_datetime() THEN returns None."""
        from mcp_server_langgraph.observability.query.backends.mimir import (
            _parse_iso_datetime,
        )

        assert _parse_iso_datetime("not-a-date") is None
        assert _parse_iso_datetime("2024/01/15") is None

    def test_map_severity_default_info(self) -> None:
        """GIVEN unknown severity label WHEN _map_severity() THEN returns INFO."""
        from mcp_server_langgraph.observability.query.backends.mimir import (
            _map_severity,
        )

        result = _map_severity({"severity": "unknown"})
        assert result == AlertSeverity.INFO

        result = _map_severity({})  # No severity key
        assert result == AlertSeverity.INFO

    def test_map_state_resolved_values(self) -> None:
        """GIVEN various resolved state names WHEN _map_state() THEN returns RESOLVED."""
        from mcp_server_langgraph.observability.query.backends.mimir import (
            _map_state,
        )

        assert _map_state("normal") == AlertState.RESOLVED
        assert _map_state("resolved") == AlertState.RESOLVED
        assert _map_state("ok") == AlertState.RESOLVED
        assert _map_state("OK") == AlertState.RESOLVED

    def test_map_state_silenced_values(self) -> None:
        """GIVEN silenced/suppressed state WHEN _map_state() THEN returns SILENCED."""
        from mcp_server_langgraph.observability.query.backends.mimir import (
            _map_state,
        )

        assert _map_state("silenced") == AlertState.SILENCED
        assert _map_state("suppressed") == AlertState.SILENCED
        assert _map_state("SILENCED") == AlertState.SILENCED

    def test_map_state_unknown_defaults_to_pending(self) -> None:
        """GIVEN unknown state WHEN _map_state() THEN returns PENDING as default."""
        from mcp_server_langgraph.observability.query.backends.mimir import (
            _map_state,
        )

        assert _map_state("unknown") == AlertState.PENDING
        assert _map_state("inactive") == AlertState.PENDING
        assert _map_state("some_random_state") == AlertState.PENDING


# =============================================================================
# Coverage Enhancement Tests - Edge Cases
# =============================================================================


@pytest.mark.xdist_group(name="mimir_alerting_edge_cases")
class TestMimirEdgeCases:
    """Tests for edge cases and error paths in MimirAlertingClient."""

    def teardown_method(self) -> None:
        """Force GC to prevent mock accumulation in xdist workers."""
        gc.collect()

    @pytest.mark.asyncio
    async def test_close_when_client_is_none(self) -> None:
        """GIVEN uninitialized client WHEN close() THEN no error."""
        from mcp_server_langgraph.observability.query.backends.mimir import (
            MimirAlertingClient,
        )

        client = MimirAlertingClient(base_url=MIMIR_BASE_URL, org_id=MIMIR_ORG_ID)
        assert client._client is None

        # Should not raise
        await client.close()
        assert client._client is None

    @pytest.mark.asyncio
    async def test_client_property_raises_when_not_initialized(self) -> None:
        """GIVEN uninitialized client WHEN accessing client property THEN raises RuntimeError."""
        from mcp_server_langgraph.observability.query.backends.mimir import (
            MimirAlertingClient,
        )

        client = MimirAlertingClient(base_url=MIMIR_BASE_URL, org_id=MIMIR_ORG_ID)

        with pytest.raises(RuntimeError, match="Client not initialized"):
            _ = client.client

    @pytest.mark.asyncio
    async def test_ensure_initialized_auto_initializes(self) -> None:
        """GIVEN uninitialized client WHEN _ensure_initialized() THEN auto-initializes."""
        from mcp_server_langgraph.observability.query.backends.mimir import (
            MimirAlertingClient,
        )

        client = MimirAlertingClient(base_url=MIMIR_BASE_URL, org_id=MIMIR_ORG_ID)
        assert client._client is None

        await client._ensure_initialized()

        assert client._client is not None
        await client.close()

    @pytest.mark.asyncio
    async def test_list_alerts_with_severity_filter(self) -> None:
        """GIVEN severity filter WHEN list_alerts() THEN includes severity in params."""
        from mcp_server_langgraph.observability.query.backends.mimir import (
            MimirAlertingClient,
        )

        client = MimirAlertingClient(base_url=MIMIR_BASE_URL, org_id=MIMIR_ORG_ID)

        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = []
        mock_response.raise_for_status = MagicMock()

        mock_http_client = AsyncMock(spec=httpx.AsyncClient)
        mock_http_client.get.return_value = mock_response
        client._client = mock_http_client

        await client.list_alerts(severity=AlertSeverity.CRITICAL)

        # Verify filter was passed
        call_args = mock_http_client.get.call_args
        assert call_args is not None
        params = call_args.kwargs.get("params", {})
        assert "severity" in params.get("filter", "")

    @pytest.mark.asyncio
    async def test_list_alerts_value_error_handling(self) -> None:
        """GIVEN malformed JSON WHEN list_alerts() THEN returns empty result."""
        from mcp_server_langgraph.observability.query.backends.mimir import (
            MimirAlertingClient,
        )

        client = MimirAlertingClient(base_url=MIMIR_BASE_URL, org_id=MIMIR_ORG_ID)

        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.side_effect = ValueError("Invalid JSON")
        mock_response.raise_for_status = MagicMock()

        mock_http_client = AsyncMock(spec=httpx.AsyncClient)
        mock_http_client.get.return_value = mock_response
        client._client = mock_http_client

        result = await client.list_alerts()

        assert len(result.alerts) == 0
        assert result.total_count == 0

    @pytest.mark.asyncio
    async def test_get_alerts_for_service_empty_when_no_labels_match(self) -> None:
        """GIVEN service not found WHEN get_alerts_for_service() THEN returns empty result."""
        from mcp_server_langgraph.observability.query.backends.mimir import (
            MimirAlertingClient,
        )

        client = MimirAlertingClient(base_url=MIMIR_BASE_URL, org_id=MIMIR_ORG_ID)

        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = []  # No alerts found
        mock_response.raise_for_status = MagicMock()

        mock_http_client = AsyncMock(spec=httpx.AsyncClient)
        mock_http_client.get.return_value = mock_response
        client._client = mock_http_client

        result = await client.get_alerts_for_service("non-existent-service")

        assert len(result.alerts) == 0
        assert result.total_count == 0

    @pytest.mark.asyncio
    async def test_list_alert_rules_non_success_status(self) -> None:
        """GIVEN non-success status WHEN list_alert_rules() THEN returns empty list."""
        from mcp_server_langgraph.observability.query.backends.mimir import (
            MimirAlertingClient,
        )

        client = MimirAlertingClient(base_url=MIMIR_BASE_URL, org_id=MIMIR_ORG_ID)

        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = {"status": "error", "error": "something failed"}
        mock_response.raise_for_status = MagicMock()

        mock_http_client = AsyncMock(spec=httpx.AsyncClient)
        mock_http_client.get.return_value = mock_response
        client._client = mock_http_client

        result = await client.list_alert_rules()

        assert result == []

    @pytest.mark.asyncio
    async def test_list_alert_rules_skips_recording_rules(self) -> None:
        """GIVEN recording rules WHEN list_alert_rules() THEN skips them."""
        from mcp_server_langgraph.observability.query.backends.mimir import (
            MimirAlertingClient,
        )

        client = MimirAlertingClient(base_url=MIMIR_BASE_URL, org_id=MIMIR_ORG_ID)

        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = {
            "status": "success",
            "data": {
                "groups": [
                    {
                        "name": "test-group",
                        "rules": [
                            {"type": "recording", "name": "record:metric"},
                            {
                                "type": "alerting",
                                "name": "AlertRule",
                                "query": "up == 0",
                                "labels": {},
                                "annotations": {},
                            },
                        ],
                    }
                ]
            },
        }
        mock_response.raise_for_status = MagicMock()

        mock_http_client = AsyncMock(spec=httpx.AsyncClient)
        mock_http_client.get.return_value = mock_response
        client._client = mock_http_client

        result = await client.list_alert_rules()

        assert len(result) == 1
        assert result[0].name == "AlertRule"

    @pytest.mark.asyncio
    async def test_list_alert_rules_respects_limit(self) -> None:
        """GIVEN many rules WHEN list_alert_rules(limit=2) THEN returns only 2 rules."""
        from mcp_server_langgraph.observability.query.backends.mimir import (
            MimirAlertingClient,
        )

        client = MimirAlertingClient(base_url=MIMIR_BASE_URL, org_id=MIMIR_ORG_ID)

        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = {
            "status": "success",
            "data": {
                "groups": [
                    {
                        "name": "test-group",
                        "rules": [
                            {"type": "alerting", "name": f"Rule{i}", "query": "up==0", "labels": {}, "annotations": {}}
                            for i in range(10)
                        ],
                    }
                ]
            },
        }
        mock_response.raise_for_status = MagicMock()

        mock_http_client = AsyncMock(spec=httpx.AsyncClient)
        mock_http_client.get.return_value = mock_response
        client._client = mock_http_client

        result = await client.list_alert_rules(limit=2)

        assert len(result) == 2

    @pytest.mark.asyncio
    async def test_list_alert_rules_http_error_handling(self) -> None:
        """GIVEN HTTP error WHEN list_alert_rules() THEN returns empty list."""
        from mcp_server_langgraph.observability.query.backends.mimir import (
            MimirAlertingClient,
        )

        client = MimirAlertingClient(base_url=MIMIR_BASE_URL, org_id=MIMIR_ORG_ID)

        mock_http_client = AsyncMock(spec=httpx.AsyncClient)
        mock_http_client.get.side_effect = httpx.HTTPStatusError(
            "Not Found",
            request=MagicMock(),
            response=MagicMock(status_code=404),
        )
        client._client = mock_http_client

        result = await client.list_alert_rules()

        assert result == []
