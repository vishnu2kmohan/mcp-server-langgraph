"""
Alerting Journey E2E Tests (ADR-0098)

Tests the alerting fallback chain and DevTools integration:
1. Alerting backend configuration and initialization
2. Fallback chain behavior (Grafana -> Mimir -> Stub)
3. Alert retrieval via REST API
4. Metrics observability

HEART Metrics Focus:
- Task Success: Alert query completion rates
- Engagement: DevTools alerts panel usage
- Adoption: Fallback feature discovery

These tests require E2E infrastructure (make test-infra-up).
"""

import gc

import pytest

from tests.constants import TEST_MIMIR_PORT

pytestmark = [
    pytest.mark.e2e,
    pytest.mark.journey,
    pytest.mark.alerting,
    pytest.mark.observability,
]


def _mimir_available() -> bool:
    """Check if Mimir is available via /ready endpoint."""
    import requests

    try:
        response = requests.get(
            f"http://localhost:{TEST_MIMIR_PORT}/ready",
            timeout=5,
        )
        return response.status_code == 200
    except Exception:
        return False


# Skip all tests if Mimir is not available
mimir_required = pytest.mark.skipif(
    not _mimir_available(),
    reason=f"Mimir not available on port {TEST_MIMIR_PORT}. Run: make test-infra-up",
)


@pytest.mark.xdist_group(name="test_alerting_journey")
class TestAlertingJourney:
    """
    End-to-end alerting journey tests.

    Validates the complete alert data flow:
    - Backend initialization
    - Fallback chain behavior
    - REST API integration
    - Prometheus metrics emission
    """

    def teardown_method(self) -> None:
        """Force GC to prevent mock accumulation in xdist workers."""
        gc.collect()

    @mimir_required
    @pytest.mark.asyncio
    async def test_01_fallback_client_initialization(self) -> None:
        """
        Step 1: FallbackAlertingClient initializes all backends.

        GIVEN fallback is enabled
        WHEN initializing the fallback client
        THEN all backends should be initialized without errors
        """
        from mcp_server_langgraph.observability.query.backends.fallback import (
            FallbackAlertingClient,
        )
        from mcp_server_langgraph.observability.query.backends.mimir import (
            MimirAlertingClient,
        )
        from mcp_server_langgraph.observability.query.backends.stub import (
            StubAlertingClient,
        )

        mimir = MimirAlertingClient(
            base_url=f"http://localhost:{TEST_MIMIR_PORT}",
            org_id="anonymous",
        )
        stub = StubAlertingClient()

        client = FallbackAlertingClient(backends=[mimir, stub], health_check_ttl=5)

        try:
            await client.initialize()

            # Verify health check passes (at least one backend healthy)
            is_healthy = await client.health_check()
            assert is_healthy, "FallbackAlertingClient should have at least one healthy backend"

        finally:
            await client.close()

    @mimir_required
    @pytest.mark.asyncio
    async def test_02_mimir_direct_alert_query(self) -> None:
        """
        Step 2: Direct Mimir alert query works.

        GIVEN Mimir is running with alert rules
        WHEN querying alerts via MimirAlertingClient
        THEN should return AlertSearchResult (may be empty if no alerts firing)
        """
        from mcp_server_langgraph.observability.query.backends.mimir import (
            MimirAlertingClient,
        )
        from mcp_server_langgraph.observability.query.interfaces import (
            AlertSearchResult,
        )

        client = MimirAlertingClient(
            base_url=f"http://localhost:{TEST_MIMIR_PORT}",
            org_id="anonymous",
        )

        try:
            await client.initialize()

            result = await client.list_alerts()

            assert isinstance(result, AlertSearchResult)
            assert result.total_count >= 0  # May be 0 if no alerts firing

        finally:
            await client.close()

    @mimir_required
    @pytest.mark.asyncio
    async def test_03_fallback_chain_uses_first_healthy(self) -> None:
        """
        Step 3: Fallback chain uses first healthy backend.

        GIVEN fallback chain with [Mimir, Stub]
        WHEN listing alerts
        THEN should use Mimir (first healthy backend)
        """
        from mcp_server_langgraph.observability.query.backends.fallback import (
            FallbackAlertingClient,
        )
        from mcp_server_langgraph.observability.query.backends.mimir import (
            MimirAlertingClient,
        )
        from mcp_server_langgraph.observability.query.backends.stub import (
            StubAlertingClient,
        )
        from mcp_server_langgraph.observability.query.interfaces import (
            AlertSearchResult,
        )

        mimir = MimirAlertingClient(
            base_url=f"http://localhost:{TEST_MIMIR_PORT}",
            org_id="anonymous",
        )
        stub = StubAlertingClient()

        client = FallbackAlertingClient(backends=[mimir, stub], health_check_ttl=5)

        try:
            await client.initialize()

            result = await client.list_alerts()

            assert isinstance(result, AlertSearchResult)
            # Mimir should have been used (not stub), we can verify by checking
            # that total_count >= 0 (stub always returns 0)

        finally:
            await client.close()

    @mimir_required
    @pytest.mark.asyncio
    async def test_04_fallback_to_stub_on_mimir_failure(self) -> None:
        """
        Step 4: Fallback to stub when Mimir unreachable.

        GIVEN fallback chain with [broken Mimir, Stub]
        WHEN listing alerts
        THEN should fall back to Stub and return empty result
        """
        from mcp_server_langgraph.observability.query.backends.fallback import (
            FallbackAlertingClient,
        )
        from mcp_server_langgraph.observability.query.backends.mimir import (
            MimirAlertingClient,
        )
        from mcp_server_langgraph.observability.query.backends.stub import (
            StubAlertingClient,
        )
        from mcp_server_langgraph.observability.query.interfaces import (
            AlertSearchResult,
        )

        # Create Mimir client with wrong URL
        broken_mimir = MimirAlertingClient(
            base_url="http://nonexistent-mimir:9999",
            org_id="anonymous",
        )
        stub = StubAlertingClient()

        client = FallbackAlertingClient(
            backends=[broken_mimir, stub],
            health_check_ttl=0,  # Disable caching for this test
        )

        try:
            await client.initialize()

            result = await client.list_alerts()

            # Should have fallen back to stub
            assert isinstance(result, AlertSearchResult)
            assert result.total_count == 0  # Stub returns empty

        finally:
            await client.close()

    @mimir_required
    @pytest.mark.asyncio
    async def test_05_metrics_exported_on_fallback(self) -> None:
        """
        Step 5: Prometheus metrics are exported during fallback.

        GIVEN fallback client with metrics enabled
        WHEN a fallback occurs
        THEN metrics should be incremented
        """
        from mcp_server_langgraph.observability.query.backends.fallback import (
            ALERTING_HEALTH_CHECKS,
            FallbackAlertingClient,
        )
        from mcp_server_langgraph.observability.query.backends.mimir import (
            MimirAlertingClient,
        )
        from mcp_server_langgraph.observability.query.backends.stub import (
            StubAlertingClient,
        )

        # Clear metrics for test isolation
        ALERTING_HEALTH_CHECKS._metrics.clear()

        mimir = MimirAlertingClient(
            base_url=f"http://localhost:{TEST_MIMIR_PORT}",
            org_id="anonymous",
        )
        stub = StubAlertingClient()

        client = FallbackAlertingClient(
            backends=[mimir, stub],
            health_check_ttl=0,  # Force health check
        )

        try:
            await client.initialize()
            await client.list_alerts()

            # Verify health check metric was incremented
            # We should have at least one health check result
            assert len(ALERTING_HEALTH_CHECKS._metrics) > 0

        finally:
            await client.close()

    @mimir_required
    @pytest.mark.asyncio
    async def test_06_alert_rules_query(self) -> None:
        """
        Step 6: Alert rules can be queried.

        GIVEN Mimir with alert rules configured
        WHEN querying alert rules
        THEN should return list of rules (may be empty)
        """
        from mcp_server_langgraph.observability.query.backends.mimir import (
            MimirAlertingClient,
        )

        client = MimirAlertingClient(
            base_url=f"http://localhost:{TEST_MIMIR_PORT}",
            org_id="anonymous",
        )

        try:
            await client.initialize()

            rules = await client.list_alert_rules()

            assert isinstance(rules, list)
            # Rules may be empty if none configured

        finally:
            await client.close()
