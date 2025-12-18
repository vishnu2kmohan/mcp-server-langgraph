"""
Integration tests for GrafanaAlertingClient with a real Grafana instance.

TDD Cycle: RED -> GREEN -> REFACTOR

These tests verify that:
1. GrafanaAlertingClient can connect to a real Grafana instance
2. Alert listing and filtering works correctly
3. Alert rule queries function properly
4. Health check properly detects Grafana availability

Requirements:
    - Grafana instance running (docker-compose or local)
    - GRAFANA_URL environment variable or localhost:3000

Environment Variables:
    GRAFANA_URL: Grafana URL (default: http://localhost:3000)
    GRAFANA_API_KEY: Optional API key for authentication
    GRAFANA_USERNAME: Optional basic auth username
    GRAFANA_PASSWORD: Optional basic auth password

Run with:
    pytest tests/integration/observability/test_grafana_alerting_integration.py -v
"""

from __future__ import annotations

import gc
import os

import pytest
import requests

from mcp_server_langgraph.observability.query.backends.grafana import GrafanaAlertingClient
from mcp_server_langgraph.observability.query.interfaces import AlertState, AlertSeverity

# Mark as integration test requiring Grafana infrastructure
pytestmark = [
    pytest.mark.integration,
    pytest.mark.grafana,
    pytest.mark.observability,
]

# Default Grafana URL for local testing
DEFAULT_GRAFANA_URL = os.getenv("GRAFANA_URL", "http://localhost:3000")


def _grafana_alerting_available() -> bool:
    """Check if Grafana Alerting API is available."""
    try:
        # Try the health endpoint first
        response = requests.get(
            f"{DEFAULT_GRAFANA_URL}/api/health",
            timeout=5,
        )
        return response.status_code == 200
    except Exception:
        return False


def _grafana_has_alerts() -> bool:
    """Check if Grafana has any configured alerts."""
    try:
        response = requests.get(
            f"{DEFAULT_GRAFANA_URL}/api/alertmanager/grafana/api/v2/alerts",
            timeout=5,
        )
        return response.status_code == 200
    except Exception:
        return False


# Skip all tests if Grafana is not available
grafana_required = pytest.mark.skipif(
    not _grafana_alerting_available(),
    reason="Grafana not available. Set GRAFANA_URL or start Grafana (docker-compose up grafana).",
)


@pytest.fixture
async def grafana_client():
    """Create and initialize a GrafanaAlertingClient for testing."""
    client = GrafanaAlertingClient(
        base_url=DEFAULT_GRAFANA_URL,
        api_key=os.getenv("GRAFANA_API_KEY"),
        username=os.getenv("GRAFANA_USERNAME"),
        password=os.getenv("GRAFANA_PASSWORD"),
    )
    await client.initialize()
    yield client
    await client.close()


@pytest.mark.xdist_group(name="test_grafana_alerting_integration")
class TestGrafanaAlertingIntegration:
    """Integration tests for GrafanaAlertingClient with real Grafana."""

    def teardown_method(self) -> None:
        """Force GC to prevent mock accumulation in xdist workers."""
        gc.collect()

    @grafana_required
    @pytest.mark.asyncio
    async def test_health_check_returns_true_when_grafana_running(self, grafana_client: GrafanaAlertingClient) -> None:
        """
        GIVEN a running Grafana instance
        WHEN calling health_check()
        THEN it should return True.
        """
        async with grafana_client:
            is_healthy = await grafana_client.health_check()
            assert is_healthy is True

    @grafana_required
    @pytest.mark.asyncio
    async def test_list_alerts_returns_search_result(self, grafana_client: GrafanaAlertingClient) -> None:
        """
        GIVEN a running Grafana instance
        WHEN calling list_alerts()
        THEN it should return an AlertSearchResult.
        """
        async with grafana_client:
            result = await grafana_client.list_alerts(limit=10)

            assert result is not None
            assert isinstance(result.alerts, list)
            assert result.total_count >= 0

    @grafana_required
    @pytest.mark.asyncio
    async def test_list_alerts_with_state_filter(self, grafana_client: GrafanaAlertingClient) -> None:
        """
        GIVEN a running Grafana instance
        WHEN calling list_alerts with state filter
        THEN it should return only alerts matching the state.
        """
        async with grafana_client:
            # Query for firing alerts (may be empty)
            result = await grafana_client.list_alerts(
                state=AlertState.FIRING,
                limit=50,
            )

            assert result is not None
            # All returned alerts should be firing (if any)
            for alert in result.alerts:
                assert alert.state == AlertState.FIRING

    @grafana_required
    @pytest.mark.asyncio
    async def test_list_alerts_with_severity_filter(self, grafana_client: GrafanaAlertingClient) -> None:
        """
        GIVEN a running Grafana instance
        WHEN calling list_alerts with severity filter
        THEN it should return only alerts matching the severity.
        """
        async with grafana_client:
            # Query for critical alerts (may be empty)
            result = await grafana_client.list_alerts(
                severity=AlertSeverity.CRITICAL,
                limit=50,
            )

            assert result is not None
            # All returned alerts should be critical (if any)
            for alert in result.alerts:
                assert alert.severity == AlertSeverity.CRITICAL

    @grafana_required
    @pytest.mark.asyncio
    async def test_list_alert_rules_returns_list(self, grafana_client: GrafanaAlertingClient) -> None:
        """
        GIVEN a running Grafana instance
        WHEN calling list_alert_rules()
        THEN it should return a list of AlertRules.
        """
        async with grafana_client:
            rules = await grafana_client.list_alert_rules(limit=10)

            assert isinstance(rules, list)
            # Rules have required fields
            for rule in rules:
                assert rule.id is not None
                assert rule.name is not None

    @grafana_required
    @pytest.mark.asyncio
    async def test_get_alert_returns_none_for_nonexistent(self, grafana_client: GrafanaAlertingClient) -> None:
        """
        GIVEN a running Grafana instance
        WHEN calling get_alert with non-existent ID
        THEN it should return None.
        """
        async with grafana_client:
            result = await grafana_client.get_alert("nonexistent-alert-id-12345")
            assert result is None

    @grafana_required
    @pytest.mark.asyncio
    async def test_get_alerts_for_service_returns_list(self, grafana_client: GrafanaAlertingClient) -> None:
        """
        GIVEN a running Grafana instance
        WHEN calling get_alerts_for_service()
        THEN it should return a list (may be empty if no alerts for service).
        """
        async with grafana_client:
            # Query for a service (may not exist)
            result = await grafana_client.get_alerts_for_service("mcp-server")

            assert isinstance(result, list)


@pytest.mark.xdist_group(name="test_grafana_alerting_unavailable")
class TestGrafanaAlertingUnavailable:
    """Tests for behavior when Grafana is unavailable."""

    def teardown_method(self) -> None:
        """Force GC to prevent mock accumulation in xdist workers."""
        gc.collect()

    @pytest.mark.asyncio
    async def test_health_check_returns_false_for_invalid_url(self) -> None:
        """
        GIVEN an invalid Grafana URL
        WHEN calling health_check()
        THEN it should return False.
        """
        client = GrafanaAlertingClient(base_url="http://nonexistent-grafana-host:9999")
        try:
            await client.initialize()
            is_healthy = await client.health_check()
            assert is_healthy is False
        finally:
            await client.close()

    @pytest.mark.asyncio
    async def test_list_alerts_returns_empty_on_error(self) -> None:
        """
        GIVEN an invalid Grafana URL
        WHEN calling list_alerts()
        THEN it should return an empty result.
        """
        client = GrafanaAlertingClient(base_url="http://nonexistent-grafana-host:9999")
        try:
            await client.initialize()
            result = await client.list_alerts(limit=10)

            assert result is not None
            assert len(result.alerts) == 0
            assert result.total_count == 0
        finally:
            await client.close()

    @pytest.mark.asyncio
    async def test_list_alert_rules_returns_empty_on_error(self) -> None:
        """
        GIVEN an invalid Grafana URL
        WHEN calling list_alert_rules()
        THEN it should return an empty list.
        """
        client = GrafanaAlertingClient(base_url="http://nonexistent-grafana-host:9999")
        try:
            await client.initialize()
            rules = await client.list_alert_rules(limit=10)

            assert isinstance(rules, list)
            assert len(rules) == 0
        finally:
            await client.close()
