"""
FallbackAlertingClient Unit Tests

TDD tests for the fallback chain that tries multiple alerting backends.
The fallback chain provides resilience when primary backends are unavailable.

Fallback Order: Grafana -> Mimir -> Stub

RED Phase: These tests define expected behavior before implementation.
"""

import gc
from datetime import UTC, datetime
from unittest.mock import AsyncMock

import pytest

from mcp_server_langgraph.observability.query.interfaces import (
    Alert,
    AlertingQueryClient,
    AlertRule,
    AlertSearchResult,
    AlertSeverity,
    AlertState,
)

pytestmark = pytest.mark.unit


# =============================================================================
# Test Fixtures
# =============================================================================


def create_mock_alert(
    alert_id: str = "test-alert-1",
    name: str = "TestAlert",
    severity: AlertSeverity = AlertSeverity.WARNING,
    state: AlertState = AlertState.FIRING,
) -> Alert:
    """Create a mock alert for testing."""
    return Alert(
        alert_id=alert_id,
        name=name,
        severity=severity,
        state=state,
        message="Test alert message",
        labels={"service": "test-service"},
        annotations={},
        started_at=datetime.now(UTC),
    )


def create_mock_alerting_client(
    healthy: bool = True,
    alerts: list[Alert] | None = None,
) -> AsyncMock:
    """Create a mock AlertingQueryClient."""
    mock = AsyncMock(spec=AlertingQueryClient)
    mock.health_check.return_value = healthy
    mock.list_alerts.return_value = AlertSearchResult(
        alerts=alerts or [],
        total_count=len(alerts or []),
    )
    mock.get_alert.return_value = alerts[0] if alerts else None
    mock.get_alerts_for_service.return_value = AlertSearchResult(
        alerts=alerts or [],
        total_count=len(alerts or []),
    )
    mock.list_alert_rules.return_value = []
    return mock


# =============================================================================
# Tests
# =============================================================================


@pytest.mark.xdist_group(name="fallback_alerting")
class TestFallbackAlertingClient:
    """Unit tests for FallbackAlertingClient."""

    def teardown_method(self) -> None:
        """Force GC to prevent mock accumulation in xdist workers."""
        gc.collect()

    @pytest.mark.asyncio
    async def test_uses_first_healthy_backend(self) -> None:
        """GIVEN Grafana is healthy WHEN list_alerts() THEN uses Grafana."""
        from mcp_server_langgraph.observability.query.backends.fallback import (
            FallbackAlertingClient,
        )

        grafana_alert = create_mock_alert(alert_id="grafana-alert")
        grafana_client = create_mock_alerting_client(healthy=True, alerts=[grafana_alert])
        mimir_client = create_mock_alerting_client(healthy=True)

        client = FallbackAlertingClient(backends=[grafana_client, mimir_client])

        result = await client.list_alerts()

        assert len(result.alerts) == 1
        assert result.alerts[0].alert_id == "grafana-alert"
        grafana_client.list_alerts.assert_awaited_once()
        mimir_client.list_alerts.assert_not_awaited()

    @pytest.mark.asyncio
    async def test_falls_back_when_first_unhealthy(self) -> None:
        """GIVEN Grafana is down WHEN list_alerts() THEN uses Mimir."""
        from mcp_server_langgraph.observability.query.backends.fallback import (
            FallbackAlertingClient,
        )

        mimir_alert = create_mock_alert(alert_id="mimir-alert")
        grafana_client = create_mock_alerting_client(healthy=False)
        mimir_client = create_mock_alerting_client(healthy=True, alerts=[mimir_alert])

        client = FallbackAlertingClient(backends=[grafana_client, mimir_client])

        result = await client.list_alerts()

        assert len(result.alerts) == 1
        assert result.alerts[0].alert_id == "mimir-alert"
        grafana_client.list_alerts.assert_not_awaited()
        mimir_client.list_alerts.assert_awaited_once()

    @pytest.mark.asyncio
    async def test_falls_back_when_first_raises_exception(self) -> None:
        """GIVEN Grafana raises exception WHEN list_alerts() THEN uses Mimir."""
        from mcp_server_langgraph.observability.query.backends.fallback import (
            FallbackAlertingClient,
        )

        mimir_alert = create_mock_alert(alert_id="mimir-alert")
        grafana_client = create_mock_alerting_client(healthy=True)
        grafana_client.list_alerts.side_effect = Exception("Connection refused")
        mimir_client = create_mock_alerting_client(healthy=True, alerts=[mimir_alert])

        client = FallbackAlertingClient(backends=[grafana_client, mimir_client])

        result = await client.list_alerts()

        assert len(result.alerts) == 1
        assert result.alerts[0].alert_id == "mimir-alert"

    @pytest.mark.asyncio
    async def test_caches_health_check_results(self) -> None:
        """GIVEN health check performed WHEN called within TTL THEN uses cache."""
        from mcp_server_langgraph.observability.query.backends.fallback import (
            FallbackAlertingClient,
        )

        grafana_client = create_mock_alerting_client(healthy=True, alerts=[create_mock_alert()])
        mimir_client = create_mock_alerting_client(healthy=True)

        client = FallbackAlertingClient(
            backends=[grafana_client, mimir_client],
            health_check_ttl=30,  # 30 second cache
        )

        # First call - should check health
        await client.list_alerts()
        initial_health_calls = grafana_client.health_check.await_count

        # Second call - should use cached health
        await client.list_alerts()
        assert grafana_client.health_check.await_count == initial_health_calls

    @pytest.mark.asyncio
    async def test_refreshes_health_after_ttl_expires(self) -> None:
        """GIVEN health TTL expired WHEN called THEN refreshes health check."""
        from mcp_server_langgraph.observability.query.backends.fallback import (
            FallbackAlertingClient,
        )

        grafana_client = create_mock_alerting_client(healthy=True, alerts=[create_mock_alert()])
        mimir_client = create_mock_alerting_client(healthy=True)

        client = FallbackAlertingClient(
            backends=[grafana_client, mimir_client],
            health_check_ttl=0,  # Immediate expiry
        )

        await client.list_alerts()
        first_count = grafana_client.health_check.await_count

        # Small delay to ensure TTL expires
        await client.list_alerts()

        # Should have checked health again
        assert grafana_client.health_check.await_count > first_count

    @pytest.mark.asyncio
    async def test_returns_empty_when_all_backends_fail(self) -> None:
        """GIVEN all backends fail WHEN list_alerts() THEN returns empty result."""
        from mcp_server_langgraph.observability.query.backends.fallback import (
            FallbackAlertingClient,
        )

        grafana_client = create_mock_alerting_client(healthy=False)
        mimir_client = create_mock_alerting_client(healthy=False)

        client = FallbackAlertingClient(backends=[grafana_client, mimir_client])

        result = await client.list_alerts()

        assert len(result.alerts) == 0
        assert result.total_count == 0

    @pytest.mark.asyncio
    async def test_get_alert_uses_fallback(self) -> None:
        """GIVEN first backend unhealthy WHEN get_alert() THEN uses fallback."""
        from mcp_server_langgraph.observability.query.backends.fallback import (
            FallbackAlertingClient,
        )

        mimir_alert = create_mock_alert(alert_id="mimir-alert-123")
        grafana_client = create_mock_alerting_client(healthy=False)
        mimir_client = create_mock_alerting_client(healthy=True, alerts=[mimir_alert])
        mimir_client.get_alert.return_value = mimir_alert

        client = FallbackAlertingClient(backends=[grafana_client, mimir_client])

        result = await client.get_alert("mimir-alert-123")

        assert result is not None
        assert result.alert_id == "mimir-alert-123"

    @pytest.mark.asyncio
    async def test_get_alerts_for_service_uses_fallback(self) -> None:
        """GIVEN first backend unhealthy WHEN get_alerts_for_service() THEN uses fallback."""
        from mcp_server_langgraph.observability.query.backends.fallback import (
            FallbackAlertingClient,
        )

        mimir_alert = create_mock_alert(alert_id="mimir-svc-alert")
        grafana_client = create_mock_alerting_client(healthy=False)
        mimir_client = create_mock_alerting_client(healthy=True, alerts=[mimir_alert])

        client = FallbackAlertingClient(backends=[grafana_client, mimir_client])

        result = await client.get_alerts_for_service("test-service")

        assert len(result.alerts) == 1
        assert result.alerts[0].alert_id == "mimir-svc-alert"

    @pytest.mark.asyncio
    async def test_list_alert_rules_uses_fallback(self) -> None:
        """GIVEN first backend unhealthy WHEN list_alert_rules() THEN uses fallback."""
        from mcp_server_langgraph.observability.query.backends.fallback import (
            FallbackAlertingClient,
        )

        mock_rule = AlertRule(
            rule_id="rule-1",
            name="TestRule",
            expression="up == 0",
            severity=AlertSeverity.CRITICAL,
        )
        grafana_client = create_mock_alerting_client(healthy=False)
        mimir_client = create_mock_alerting_client(healthy=True)
        mimir_client.list_alert_rules.return_value = [mock_rule]

        client = FallbackAlertingClient(backends=[grafana_client, mimir_client])

        result = await client.list_alert_rules()

        assert len(result) == 1
        assert result[0].name == "TestRule"

    @pytest.mark.asyncio
    async def test_health_check_returns_true_if_any_backend_healthy(self) -> None:
        """GIVEN mixed backend health WHEN health_check() THEN returns True."""
        from mcp_server_langgraph.observability.query.backends.fallback import (
            FallbackAlertingClient,
        )

        grafana_client = create_mock_alerting_client(healthy=False)
        mimir_client = create_mock_alerting_client(healthy=True)

        client = FallbackAlertingClient(backends=[grafana_client, mimir_client])

        result = await client.health_check()

        assert result is True

    @pytest.mark.asyncio
    async def test_health_check_returns_false_if_all_unhealthy(self) -> None:
        """GIVEN all backends unhealthy WHEN health_check() THEN returns False."""
        from mcp_server_langgraph.observability.query.backends.fallback import (
            FallbackAlertingClient,
        )

        grafana_client = create_mock_alerting_client(healthy=False)
        mimir_client = create_mock_alerting_client(healthy=False)

        client = FallbackAlertingClient(backends=[grafana_client, mimir_client])

        result = await client.health_check()

        assert result is False

    @pytest.mark.asyncio
    async def test_initialize_initializes_all_backends(self) -> None:
        """GIVEN multiple backends WHEN initialize() THEN initializes all."""
        from mcp_server_langgraph.observability.query.backends.fallback import (
            FallbackAlertingClient,
        )

        grafana_client = create_mock_alerting_client(healthy=True)
        mimir_client = create_mock_alerting_client(healthy=True)

        client = FallbackAlertingClient(backends=[grafana_client, mimir_client])

        await client.initialize()

        grafana_client.initialize.assert_awaited_once()
        mimir_client.initialize.assert_awaited_once()

    @pytest.mark.asyncio
    async def test_close_closes_all_backends(self) -> None:
        """GIVEN multiple backends WHEN close() THEN closes all."""
        from mcp_server_langgraph.observability.query.backends.fallback import (
            FallbackAlertingClient,
        )

        grafana_client = create_mock_alerting_client(healthy=True)
        mimir_client = create_mock_alerting_client(healthy=True)

        client = FallbackAlertingClient(backends=[grafana_client, mimir_client])

        await client.close()

        grafana_client.close.assert_awaited_once()
        mimir_client.close.assert_awaited_once()

    @pytest.mark.asyncio
    async def test_marks_backend_unhealthy_after_exception(self) -> None:
        """GIVEN backend raises exception WHEN list_alerts() THEN marks unhealthy."""
        from mcp_server_langgraph.observability.query.backends.fallback import (
            FallbackAlertingClient,
        )

        mimir_alert = create_mock_alert(alert_id="mimir-alert")
        grafana_client = create_mock_alerting_client(healthy=True)
        # First call succeeds, subsequent calls fail
        grafana_client.list_alerts.side_effect = [
            AlertSearchResult(alerts=[create_mock_alert()], total_count=1),
            Exception("Connection timeout"),
        ]
        mimir_client = create_mock_alerting_client(healthy=True, alerts=[mimir_alert])

        client = FallbackAlertingClient(
            backends=[grafana_client, mimir_client],
            health_check_ttl=0,  # No caching
        )

        # First call should use Grafana
        result1 = await client.list_alerts()
        assert result1.total_count == 1

        # After exception, should fall back to Mimir
        result2 = await client.list_alerts()
        assert len(result2.alerts) == 1
        assert result2.alerts[0].alert_id == "mimir-alert"

    @pytest.mark.asyncio
    async def test_empty_backends_list_returns_empty_results(self) -> None:
        """GIVEN no backends WHEN list_alerts() THEN returns empty result."""
        from mcp_server_langgraph.observability.query.backends.fallback import (
            FallbackAlertingClient,
        )

        client = FallbackAlertingClient(backends=[])

        result = await client.list_alerts()

        assert len(result.alerts) == 0
        assert result.total_count == 0


# =============================================================================
# Fallback Metrics Tests (TDD - RED Phase)
# =============================================================================


@pytest.mark.xdist_group(name="fallback_alerting_metrics")
class TestFallbackAlertingMetrics:
    """Unit tests for FallbackAlertingClient Prometheus metrics."""

    def teardown_method(self) -> None:
        """Force GC to prevent mock accumulation in xdist workers."""
        gc.collect()

    @pytest.mark.asyncio
    async def test_fallback_activation_increments_counter(self) -> None:
        """GIVEN first backend fails WHEN fallback occurs THEN counter increments."""
        from mcp_server_langgraph.observability.query.backends.fallback import (
            ALERTING_FALLBACK_ACTIVATIONS,
            FallbackAlertingClient,
        )

        # Reset metric for test isolation
        ALERTING_FALLBACK_ACTIVATIONS._metrics.clear()

        mimir_alert = create_mock_alert(alert_id="mimir-alert")
        grafana_client = create_mock_alerting_client(healthy=True)
        grafana_client.list_alerts.side_effect = Exception("Connection refused")
        mimir_client = create_mock_alerting_client(healthy=True, alerts=[mimir_alert])

        client = FallbackAlertingClient(backends=[grafana_client, mimir_client])

        await client.list_alerts()

        # Verify fallback counter was incremented - type() returns AsyncMock for mocks
        labels = {"from_backend": "AsyncMock", "to_backend": "AsyncMock", "operation": "list_alerts"}
        counter_value = ALERTING_FALLBACK_ACTIVATIONS.labels(**labels)._value.get()
        assert counter_value >= 1

    @pytest.mark.asyncio
    async def test_backend_error_increments_counter(self) -> None:
        """GIVEN backend raises exception WHEN operation called THEN error counter increments."""
        from mcp_server_langgraph.observability.query.backends.fallback import (
            ALERTING_BACKEND_ERRORS,
            FallbackAlertingClient,
        )

        # Reset metric for test isolation
        ALERTING_BACKEND_ERRORS._metrics.clear()

        grafana_client = create_mock_alerting_client(healthy=True)
        grafana_client.list_alerts.side_effect = Exception("Connection refused")
        mimir_client = create_mock_alerting_client(healthy=True, alerts=[create_mock_alert()])

        client = FallbackAlertingClient(backends=[grafana_client, mimir_client])

        await client.list_alerts()

        # Verify error counter was incremented - type() returns AsyncMock for mocks
        labels = {"backend": "AsyncMock", "operation": "list_alerts", "error_type": "Exception"}
        counter_value = ALERTING_BACKEND_ERRORS.labels(**labels)._value.get()
        assert counter_value >= 1

    @pytest.mark.asyncio
    async def test_health_check_result_tracked(self) -> None:
        """GIVEN health check performed WHEN checking backend THEN result tracked."""
        from mcp_server_langgraph.observability.query.backends.fallback import (
            ALERTING_HEALTH_CHECKS,
            FallbackAlertingClient,
        )

        # Reset metric for test isolation
        ALERTING_HEALTH_CHECKS._metrics.clear()

        grafana_client = create_mock_alerting_client(healthy=True, alerts=[create_mock_alert()])

        client = FallbackAlertingClient(
            backends=[grafana_client],
            health_check_ttl=0,  # Disable caching to ensure health check is called
        )

        await client.list_alerts()

        # Verify health check counter was incremented - type() returns AsyncMock for mocks
        labels = {"backend": "AsyncMock", "result": "healthy"}
        counter_value = ALERTING_HEALTH_CHECKS.labels(**labels)._value.get()
        assert counter_value >= 1

    @pytest.mark.asyncio
    async def test_unhealthy_backend_health_check_tracked(self) -> None:
        """GIVEN unhealthy backend WHEN health check THEN result=unhealthy tracked."""
        from mcp_server_langgraph.observability.query.backends.fallback import (
            ALERTING_HEALTH_CHECKS,
            FallbackAlertingClient,
        )

        # Reset metric for test isolation
        ALERTING_HEALTH_CHECKS._metrics.clear()

        grafana_client = create_mock_alerting_client(healthy=False)
        mimir_client = create_mock_alerting_client(healthy=True, alerts=[create_mock_alert()])

        client = FallbackAlertingClient(
            backends=[grafana_client, mimir_client],
            health_check_ttl=0,
        )

        await client.list_alerts()

        # Verify unhealthy health check was tracked - type() returns AsyncMock for mocks
        labels = {"backend": "AsyncMock", "result": "unhealthy"}
        counter_value = ALERTING_HEALTH_CHECKS.labels(**labels)._value.get()
        assert counter_value >= 1

    @pytest.mark.asyncio
    async def test_successful_operation_no_fallback_counter(self) -> None:
        """GIVEN first backend succeeds WHEN operation called THEN no fallback counter."""
        from mcp_server_langgraph.observability.query.backends.fallback import (
            ALERTING_FALLBACK_ACTIVATIONS,
            FallbackAlertingClient,
        )

        # Reset metric for test isolation
        ALERTING_FALLBACK_ACTIVATIONS._metrics.clear()

        grafana_client = create_mock_alerting_client(healthy=True, alerts=[create_mock_alert()])
        mimir_client = create_mock_alerting_client(healthy=True)

        client = FallbackAlertingClient(backends=[grafana_client, mimir_client])

        await client.list_alerts()

        # No fallback should have occurred - check that we don't have a fallback counter
        # The metrics dict should be empty for this label combination
        assert len(ALERTING_FALLBACK_ACTIVATIONS._metrics) == 0

    # =========================================================================
    # Metrics for Other Operations (get_alert, get_alerts_for_service, list_alert_rules)
    # =========================================================================

    @pytest.mark.asyncio
    async def test_get_alert_fallback_increments_counter(self) -> None:
        """GIVEN first backend fails WHEN get_alert fallback occurs THEN counter increments."""
        from mcp_server_langgraph.observability.query.backends.fallback import (
            ALERTING_FALLBACK_ACTIVATIONS,
            FallbackAlertingClient,
        )

        # Reset metric for test isolation
        ALERTING_FALLBACK_ACTIVATIONS._metrics.clear()

        mimir_alert = create_mock_alert(alert_id="mimir-alert-123")
        grafana_client = create_mock_alerting_client(healthy=True)
        grafana_client.get_alert.side_effect = Exception("Connection refused")
        mimir_client = create_mock_alerting_client(healthy=True, alerts=[mimir_alert])
        mimir_client.get_alert.return_value = mimir_alert

        client = FallbackAlertingClient(backends=[grafana_client, mimir_client])

        await client.get_alert("mimir-alert-123")

        # Verify fallback counter was incremented for get_alert operation
        labels = {"from_backend": "AsyncMock", "to_backend": "AsyncMock", "operation": "get_alert"}
        counter_value = ALERTING_FALLBACK_ACTIVATIONS.labels(**labels)._value.get()
        assert counter_value >= 1

    @pytest.mark.asyncio
    async def test_get_alert_error_increments_counter(self) -> None:
        """GIVEN backend raises exception WHEN get_alert called THEN error counter increments."""
        from mcp_server_langgraph.observability.query.backends.fallback import (
            ALERTING_BACKEND_ERRORS,
            FallbackAlertingClient,
        )

        # Reset metric for test isolation
        ALERTING_BACKEND_ERRORS._metrics.clear()

        grafana_client = create_mock_alerting_client(healthy=True)
        grafana_client.get_alert.side_effect = Exception("Connection refused")
        mimir_client = create_mock_alerting_client(healthy=True, alerts=[create_mock_alert()])

        client = FallbackAlertingClient(backends=[grafana_client, mimir_client])

        await client.get_alert("test-alert")

        # Verify error counter was incremented for get_alert operation
        labels = {"backend": "AsyncMock", "operation": "get_alert", "error_type": "Exception"}
        counter_value = ALERTING_BACKEND_ERRORS.labels(**labels)._value.get()
        assert counter_value >= 1

    @pytest.mark.asyncio
    async def test_get_alerts_for_service_fallback_increments_counter(self) -> None:
        """GIVEN first backend fails WHEN get_alerts_for_service fallback occurs THEN counter increments."""
        from mcp_server_langgraph.observability.query.backends.fallback import (
            ALERTING_FALLBACK_ACTIVATIONS,
            FallbackAlertingClient,
        )

        # Reset metric for test isolation
        ALERTING_FALLBACK_ACTIVATIONS._metrics.clear()

        mimir_alert = create_mock_alert(alert_id="mimir-svc-alert")
        grafana_client = create_mock_alerting_client(healthy=True)
        grafana_client.get_alerts_for_service.side_effect = Exception("Connection refused")
        mimir_client = create_mock_alerting_client(healthy=True, alerts=[mimir_alert])

        client = FallbackAlertingClient(backends=[grafana_client, mimir_client])

        await client.get_alerts_for_service("test-service")

        # Verify fallback counter was incremented for get_alerts_for_service operation
        labels = {"from_backend": "AsyncMock", "to_backend": "AsyncMock", "operation": "get_alerts_for_service"}
        counter_value = ALERTING_FALLBACK_ACTIVATIONS.labels(**labels)._value.get()
        assert counter_value >= 1

    @pytest.mark.asyncio
    async def test_get_alerts_for_service_error_increments_counter(self) -> None:
        """GIVEN backend raises exception WHEN get_alerts_for_service called THEN error counter increments."""
        from mcp_server_langgraph.observability.query.backends.fallback import (
            ALERTING_BACKEND_ERRORS,
            FallbackAlertingClient,
        )

        # Reset metric for test isolation
        ALERTING_BACKEND_ERRORS._metrics.clear()

        grafana_client = create_mock_alerting_client(healthy=True)
        grafana_client.get_alerts_for_service.side_effect = Exception("Service unavailable")
        mimir_client = create_mock_alerting_client(healthy=True, alerts=[create_mock_alert()])

        client = FallbackAlertingClient(backends=[grafana_client, mimir_client])

        await client.get_alerts_for_service("test-service")

        # Verify error counter was incremented for get_alerts_for_service operation
        labels = {"backend": "AsyncMock", "operation": "get_alerts_for_service", "error_type": "Exception"}
        counter_value = ALERTING_BACKEND_ERRORS.labels(**labels)._value.get()
        assert counter_value >= 1

    @pytest.mark.asyncio
    async def test_list_alert_rules_fallback_increments_counter(self) -> None:
        """GIVEN first backend fails WHEN list_alert_rules fallback occurs THEN counter increments."""
        from mcp_server_langgraph.observability.query.backends.fallback import (
            ALERTING_FALLBACK_ACTIVATIONS,
            FallbackAlertingClient,
        )

        # Reset metric for test isolation
        ALERTING_FALLBACK_ACTIVATIONS._metrics.clear()

        mock_rule = AlertRule(
            rule_id="rule-1",
            name="TestRule",
            expression="up == 0",
            severity=AlertSeverity.CRITICAL,
        )
        grafana_client = create_mock_alerting_client(healthy=True)
        grafana_client.list_alert_rules.side_effect = Exception("Connection refused")
        mimir_client = create_mock_alerting_client(healthy=True)
        mimir_client.list_alert_rules.return_value = [mock_rule]

        client = FallbackAlertingClient(backends=[grafana_client, mimir_client])

        await client.list_alert_rules()

        # Verify fallback counter was incremented for list_alert_rules operation
        labels = {"from_backend": "AsyncMock", "to_backend": "AsyncMock", "operation": "list_alert_rules"}
        counter_value = ALERTING_FALLBACK_ACTIVATIONS.labels(**labels)._value.get()
        assert counter_value >= 1

    @pytest.mark.asyncio
    async def test_list_alert_rules_error_increments_counter(self) -> None:
        """GIVEN backend raises exception WHEN list_alert_rules called THEN error counter increments."""
        from mcp_server_langgraph.observability.query.backends.fallback import (
            ALERTING_BACKEND_ERRORS,
            FallbackAlertingClient,
        )

        # Reset metric for test isolation
        ALERTING_BACKEND_ERRORS._metrics.clear()

        grafana_client = create_mock_alerting_client(healthy=True)
        grafana_client.list_alert_rules.side_effect = TimeoutError("Request timed out")
        mimir_client = create_mock_alerting_client(healthy=True)

        client = FallbackAlertingClient(backends=[grafana_client, mimir_client])

        await client.list_alert_rules()

        # Verify error counter was incremented for list_alert_rules operation
        labels = {"backend": "AsyncMock", "operation": "list_alert_rules", "error_type": "TimeoutError"}
        counter_value = ALERTING_BACKEND_ERRORS.labels(**labels)._value.get()
        assert counter_value >= 1


# =============================================================================
# Coverage Enhancement Tests - Edge Cases
# =============================================================================


@pytest.mark.xdist_group(name="fallback_alerting_edge_cases")
class TestFallbackEdgeCases:
    """Tests for edge cases and uncovered paths in FallbackAlertingClient."""

    def teardown_method(self) -> None:
        """Force GC to prevent mock accumulation in xdist workers."""
        gc.collect()

    @pytest.mark.asyncio
    async def test_initialize_marks_backend_unhealthy_on_exception(self) -> None:
        """GIVEN backend raises exception WHEN initialize() THEN marks backend unhealthy."""
        from mcp_server_langgraph.observability.query.backends.fallback import (
            FallbackAlertingClient,
        )

        failing_backend = create_mock_alerting_client(healthy=True)
        failing_backend.initialize.side_effect = RuntimeError("Connection refused")

        healthy_backend = create_mock_alerting_client(healthy=True, alerts=[create_mock_alert()])

        client = FallbackAlertingClient(backends=[failing_backend, healthy_backend])

        # Initialize - should catch exception and mark backend unhealthy
        await client.initialize()

        # The failing backend should be marked unhealthy in cache
        backend_id = id(failing_backend)
        assert backend_id in client._health_cache
        is_healthy, _ = client._health_cache[backend_id]
        assert is_healthy is False

    @pytest.mark.asyncio
    async def test_close_continues_on_exception(self) -> None:
        """GIVEN backend raises exception WHEN close() THEN continues closing other backends."""
        from mcp_server_langgraph.observability.query.backends.fallback import (
            FallbackAlertingClient,
        )

        failing_backend = create_mock_alerting_client(healthy=True)
        failing_backend.close.side_effect = RuntimeError("Close failed")

        healthy_backend = create_mock_alerting_client(healthy=True)

        client = FallbackAlertingClient(backends=[failing_backend, healthy_backend])

        # Close should not raise, should continue to close second backend
        await client.close()

        # Both backends' close methods should have been called
        failing_backend.close.assert_called_once()
        healthy_backend.close.assert_called_once()

    @pytest.mark.asyncio
    async def test_health_check_exception_returns_false(self) -> None:
        """GIVEN health_check() raises exception WHEN checking health THEN returns False."""
        from mcp_server_langgraph.observability.query.backends.fallback import (
            ALERTING_HEALTH_CHECKS,
            FallbackAlertingClient,
        )

        # Reset metric for test isolation
        ALERTING_HEALTH_CHECKS._metrics.clear()

        # Create a backend that throws exception on health_check
        failing_backend = AsyncMock(spec=AlertingQueryClient)
        failing_backend.health_check.side_effect = ConnectionError("Network unreachable")

        client = FallbackAlertingClient(backends=[failing_backend])

        # Call _is_backend_healthy directly
        result = await client._is_backend_healthy(failing_backend)

        assert result is False

        # Backend should be marked unhealthy in cache
        backend_id = id(failing_backend)
        assert backend_id in client._health_cache
        is_healthy, _ = client._health_cache[backend_id]
        assert is_healthy is False

        # Verify "error" result was tracked
        labels = {"backend": "AsyncMock", "result": "error"}
        counter_value = ALERTING_HEALTH_CHECKS.labels(**labels)._value.get()
        assert counter_value >= 1

    @pytest.mark.asyncio
    async def test_get_alert_returns_none_when_all_backends_fail(self) -> None:
        """GIVEN all backends fail WHEN get_alert() THEN returns None."""
        from mcp_server_langgraph.observability.query.backends.fallback import (
            FallbackAlertingClient,
        )

        backend1 = create_mock_alerting_client(healthy=True)
        backend1.get_alert.side_effect = Exception("Backend 1 error")

        backend2 = create_mock_alerting_client(healthy=True)
        backend2.get_alert.side_effect = Exception("Backend 2 error")

        client = FallbackAlertingClient(backends=[backend1, backend2])

        result = await client.get_alert("alert-123")

        assert result is None
        backend1.get_alert.assert_called_once_with("alert-123")
        backend2.get_alert.assert_called_once_with("alert-123")

    @pytest.mark.asyncio
    async def test_get_alerts_for_service_returns_empty_when_all_backends_fail(self) -> None:
        """GIVEN all backends fail WHEN get_alerts_for_service() THEN returns empty result."""
        from mcp_server_langgraph.observability.query.backends.fallback import (
            FallbackAlertingClient,
        )

        backend1 = create_mock_alerting_client(healthy=True)
        backend1.get_alerts_for_service.side_effect = Exception("Backend 1 error")

        backend2 = create_mock_alerting_client(healthy=True)
        backend2.get_alerts_for_service.side_effect = Exception("Backend 2 error")

        client = FallbackAlertingClient(backends=[backend1, backend2])

        result = await client.get_alerts_for_service("my-service")

        assert isinstance(result, AlertSearchResult)
        assert result.alerts == []
        assert result.total_count == 0

    @pytest.mark.asyncio
    async def test_list_alert_rules_returns_empty_when_all_backends_fail(self) -> None:
        """GIVEN all backends fail WHEN list_alert_rules() THEN returns empty list."""
        from mcp_server_langgraph.observability.query.backends.fallback import (
            FallbackAlertingClient,
        )

        backend1 = create_mock_alerting_client(healthy=True)
        backend1.list_alert_rules.side_effect = Exception("Backend 1 error")

        backend2 = create_mock_alerting_client(healthy=True)
        backend2.list_alert_rules.side_effect = Exception("Backend 2 error")

        client = FallbackAlertingClient(backends=[backend1, backend2])

        result = await client.list_alert_rules()

        assert result == []

    @pytest.mark.asyncio
    async def test_skips_unhealthy_backends_in_loop(self) -> None:
        """GIVEN first backend is unhealthy WHEN list_alerts() THEN skips to healthy backend."""
        from mcp_server_langgraph.observability.query.backends.fallback import (
            FallbackAlertingClient,
        )

        unhealthy_backend = create_mock_alerting_client(healthy=False)
        healthy_backend = create_mock_alerting_client(healthy=True, alerts=[create_mock_alert()])

        client = FallbackAlertingClient(backends=[unhealthy_backend, healthy_backend])

        result = await client.list_alerts()

        # Should have skipped unhealthy and used healthy
        assert len(result.alerts) == 1
        unhealthy_backend.list_alerts.assert_not_called()
        healthy_backend.list_alerts.assert_called_once()
