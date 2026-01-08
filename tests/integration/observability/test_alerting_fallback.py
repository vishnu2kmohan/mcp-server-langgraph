"""
Integration tests for alerting fallback chain.

TDD Cycle: RED -> GREEN -> REFACTOR

These tests verify that:
1. FallbackAlertingClient correctly chains multiple backends
2. Fallback occurs when primary backend is unavailable
3. Health check caching works as expected
4. The factory creates the correct fallback chain

Requirements:
    - Mimir instance running (docker-compose.test.yml)
    - Optional: Grafana instance for full chain testing

Environment Variables:
    MIMIR_URL: Mimir URL (default: http://localhost:19009 per docker-compose.test.yml)
    MIMIR_ORG_ID: Mimir tenant ID (default: anonymous)
    GRAFANA_URL: Grafana URL (default: http://localhost:13001 per docker-compose.test.yml)
    ALERTING_FALLBACK_ENABLED: Enable fallback testing (default: true)

Run with:
    pytest tests/integration/observability/test_alerting_fallback.py -v
"""

from __future__ import annotations

import gc
import os
from unittest.mock import patch

import pytest
import requests

from mcp_server_langgraph.observability.query.backends.fallback import FallbackAlertingClient
from mcp_server_langgraph.observability.query.backends.mimir import MimirAlertingClient
from mcp_server_langgraph.observability.query.backends.stub import StubAlertingClient
from mcp_server_langgraph.observability.query.interfaces import AlertSearchResult
from tests.constants import TEST_GRAFANA_PORT, TEST_MIMIR_PORT

# Mark as integration test requiring LGTM infrastructure
pytestmark = [
    pytest.mark.integration,
    pytest.mark.observability,
    pytest.mark.alerting,
]

# Default URLs for local testing (using docker-compose.test.yml ports)
DEFAULT_MIMIR_URL = os.getenv("MIMIR_URL", f"http://localhost:{TEST_MIMIR_PORT}")
DEFAULT_GRAFANA_URL = os.getenv("GRAFANA_URL", f"http://localhost:{TEST_GRAFANA_PORT}")


def _mimir_available() -> bool:
    """Check if Mimir is available via /ready endpoint."""
    try:
        response = requests.get(
            f"{DEFAULT_MIMIR_URL}/ready",
            timeout=5,
        )
        return response.status_code == 200
    except Exception:
        return False


def _grafana_available() -> bool:
    """Check if Grafana is available via /api/health endpoint."""
    try:
        response = requests.get(
            f"{DEFAULT_GRAFANA_URL}/api/health",
            timeout=5,
        )
        return response.status_code == 200
    except Exception:
        return False


# Skip all tests if Mimir is not available
mimir_required = pytest.mark.skipif(
    not _mimir_available(),
    reason="Mimir not available. Set MIMIR_URL or start Mimir (docker-compose up mimir).",
)


@pytest.fixture
async def mimir_client():
    """Create and initialize a MimirAlertingClient for testing."""
    client = MimirAlertingClient(
        base_url=DEFAULT_MIMIR_URL,
        org_id=os.getenv("MIMIR_ORG_ID", "anonymous"),
    )
    await client.initialize()
    yield client
    await client.close()


@pytest.fixture
async def fallback_client_mimir_only():
    """Create a fallback client with only Mimir and Stub backends (no Grafana)."""
    mimir = MimirAlertingClient(
        base_url=DEFAULT_MIMIR_URL,
        org_id=os.getenv("MIMIR_ORG_ID", "anonymous"),
    )
    stub = StubAlertingClient()

    client = FallbackAlertingClient(
        backends=[mimir, stub],
        health_check_ttl=5,  # Short TTL for testing
    )
    await client.initialize()
    yield client
    await client.close()


@pytest.fixture
async def fallback_client_full():
    """Create a full fallback chain: Grafana -> Mimir -> Stub."""
    from mcp_server_langgraph.observability.query.backends.grafana import GrafanaAlertingClient

    grafana = GrafanaAlertingClient(base_url=DEFAULT_GRAFANA_URL)
    mimir = MimirAlertingClient(
        base_url=DEFAULT_MIMIR_URL,
        org_id=os.getenv("MIMIR_ORG_ID", "anonymous"),
    )
    stub = StubAlertingClient()

    client = FallbackAlertingClient(
        backends=[grafana, mimir, stub],
        health_check_ttl=5,
    )
    await client.initialize()
    yield client
    await client.close()


@pytest.mark.xdist_group(name="test_alerting_fallback")
class TestMimirAlertingIntegration:
    """Integration tests for MimirAlertingClient with real Mimir."""

    def teardown_method(self) -> None:
        """Force GC to prevent mock accumulation in xdist workers."""
        gc.collect()

    @mimir_required
    @pytest.mark.asyncio
    async def test_mimir_health_check(self, mimir_client: MimirAlertingClient) -> None:
        """GIVEN Mimir is running WHEN health_check() THEN returns True."""
        result = await mimir_client.health_check()
        assert result is True

    @mimir_required
    @pytest.mark.asyncio
    async def test_mimir_list_alerts_returns_result(self, mimir_client: MimirAlertingClient) -> None:
        """GIVEN Mimir is running WHEN list_alerts() THEN returns AlertSearchResult."""
        result = await mimir_client.list_alerts()

        assert isinstance(result, AlertSearchResult)
        assert result.total_count >= 0
        # Note: alerts list may be empty if no alerts are firing

    @mimir_required
    @pytest.mark.asyncio
    async def test_mimir_list_alert_rules(self, mimir_client: MimirAlertingClient) -> None:
        """GIVEN Mimir has alert rules WHEN list_alert_rules() THEN returns rules."""
        result = await mimir_client.list_alert_rules()

        assert isinstance(result, list)
        # Rules may be empty if none configured


@pytest.mark.xdist_group(name="test_alerting_fallback")
class TestFallbackAlertingIntegration:
    """Integration tests for FallbackAlertingClient with real backends."""

    def teardown_method(self) -> None:
        """Force GC to prevent mock accumulation in xdist workers."""
        gc.collect()

    @mimir_required
    @pytest.mark.asyncio
    async def test_fallback_health_check_with_mimir(self, fallback_client_mimir_only: FallbackAlertingClient) -> None:
        """GIVEN Mimir is healthy WHEN health_check() THEN returns True."""
        result = await fallback_client_mimir_only.health_check()
        assert result is True

    @mimir_required
    @pytest.mark.asyncio
    async def test_fallback_list_alerts_uses_first_healthy(self, fallback_client_mimir_only: FallbackAlertingClient) -> None:
        """GIVEN Mimir is first healthy backend WHEN list_alerts() THEN uses Mimir."""
        result = await fallback_client_mimir_only.list_alerts()

        assert isinstance(result, AlertSearchResult)
        assert result.total_count >= 0

    @mimir_required
    @pytest.mark.asyncio
    async def test_fallback_to_stub_when_mimir_unavailable(self) -> None:
        """GIVEN Mimir is unavailable WHEN list_alerts() THEN falls back to Stub."""
        # Create a client with an unreachable Mimir URL
        mimir = MimirAlertingClient(
            base_url="http://nonexistent-mimir:9009",
            org_id="anonymous",
        )
        stub = StubAlertingClient()

        client = FallbackAlertingClient(
            backends=[mimir, stub],
            health_check_ttl=0,  # Disable caching for this test
        )
        await client.initialize()

        try:
            result = await client.list_alerts()

            # Should fall back to stub and return empty result
            assert isinstance(result, AlertSearchResult)
            assert result.total_count == 0
        finally:
            await client.close()

    @pytest.mark.asyncio
    async def test_stub_always_returns_empty(self) -> None:
        """GIVEN only Stub backend WHEN list_alerts() THEN returns empty result."""
        stub = StubAlertingClient()
        client = FallbackAlertingClient(backends=[stub], health_check_ttl=30)
        await client.initialize()

        try:
            result = await client.list_alerts()

            assert isinstance(result, AlertSearchResult)
            assert result.total_count == 0
            assert len(result.alerts) == 0
        finally:
            await client.close()


@pytest.mark.xdist_group(name="test_alerting_fallback")
class TestFactoryFallbackConfiguration:
    """Integration tests for factory fallback configuration."""

    def teardown_method(self) -> None:
        """Force GC to prevent mock accumulation in xdist workers."""
        gc.collect()

    @pytest.mark.asyncio
    async def test_factory_creates_fallback_when_enabled(self) -> None:
        """GIVEN ALERTING_FALLBACK_ENABLED=true WHEN get_alerting_client() THEN returns FallbackAlertingClient."""
        from mcp_server_langgraph.observability.query import factory

        # Reset global client to force recreation
        factory._alerting_client = None

        with patch.dict(os.environ, {"ALERTING_FALLBACK_ENABLED": "true"}):
            client = factory.get_alerting_client()

            assert isinstance(client, FallbackAlertingClient)

            # Verify it has the expected backends
            assert len(client._backends) == 3  # Grafana, Mimir, Stub

        # Cleanup
        await factory.close_query_clients()

    @pytest.mark.asyncio
    async def test_factory_creates_grafana_when_fallback_disabled(self) -> None:
        """GIVEN ALERTING_FALLBACK_ENABLED=false WHEN get_alerting_client() THEN returns GrafanaAlertingClient."""
        from mcp_server_langgraph.observability.query import factory
        from mcp_server_langgraph.observability.query.backends.grafana import GrafanaAlertingClient

        # Reset global client to force recreation
        factory._alerting_client = None

        with patch.dict(
            os.environ,
            {"ALERTING_FALLBACK_ENABLED": "false", "OBSERVABILITY_ALERTING_BACKEND": "grafana"},
            clear=False,
        ):
            client = factory.get_alerting_client()

            assert isinstance(client, GrafanaAlertingClient)

        # Cleanup
        await factory.close_query_clients()

    @pytest.mark.asyncio
    async def test_factory_creates_mimir_directly(self) -> None:
        """GIVEN OBSERVABILITY_ALERTING_BACKEND=mimir WHEN get_alerting_client() THEN returns MimirAlertingClient."""
        from mcp_server_langgraph.observability.query import factory

        # Reset global client to force recreation
        factory._alerting_client = None

        with patch.dict(
            os.environ,
            {"ALERTING_FALLBACK_ENABLED": "false", "OBSERVABILITY_ALERTING_BACKEND": "mimir"},
            clear=False,
        ):
            client = factory.get_alerting_client()

            assert isinstance(client, MimirAlertingClient)

        # Cleanup
        await factory.close_query_clients()
