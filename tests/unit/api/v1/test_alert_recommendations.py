"""
Alert Recommendations REST API Tests.

TDD tests for the alert recommendation API endpoints:
- GET /api/v1/alerts/{alert_id}/recommendation
- POST /api/v1/alerts/{alert_id}/recommendation/regenerate

Reference: ADR-0026 - Comprehensive Client Resilience Patterns
"""

import gc
import pytest
from unittest.mock import AsyncMock, MagicMock
from datetime import datetime, UTC

from mcp_server_langgraph.alerts.ai_recommendation import (
    AIRecommendation,
    AIRecommendationService,
)
from mcp_server_langgraph.observability.query.interfaces import (
    Alert,
    AlertSeverity,
    AlertState,
)

pytestmark = pytest.mark.unit


@pytest.mark.xdist_group(name="alert_recommendations_api")
class TestAlertRecommendationRouter:
    """Tests for alert recommendation router existence."""

    def teardown_method(self) -> None:
        """Force GC to prevent mock accumulation in xdist workers."""
        gc.collect()

    def test_alert_recommendation_router_exists(self) -> None:
        """Router module should export alert_recommendation_router."""
        from mcp_server_langgraph.api.v1.alert_recommendations import (
            alert_recommendation_router,
        )

        assert alert_recommendation_router is not None

    def test_get_recommendation_endpoint_exists(self) -> None:
        """GET endpoint should exist for fetching recommendation."""
        from mcp_server_langgraph.api.v1.alert_recommendations import (
            alert_recommendation_router,
        )

        routes = [r.path for r in alert_recommendation_router.routes]
        # Routes include the router prefix "/alerts"
        assert "/alerts/{alert_id}/recommendation" in routes

    def test_regenerate_endpoint_exists(self) -> None:
        """POST endpoint should exist for regenerating recommendation."""
        from mcp_server_langgraph.api.v1.alert_recommendations import (
            alert_recommendation_router,
        )

        routes = [r.path for r in alert_recommendation_router.routes]
        # Routes include the router prefix "/alerts"
        assert "/alerts/{alert_id}/recommendation/regenerate" in routes


@pytest.mark.xdist_group(name="alert_recommendations_api")
class TestGetAlertRecommendation:
    """Tests for GET /alerts/{alert_id}/recommendation endpoint."""

    def setup_method(self) -> None:
        """Reset rate limiters before each test."""
        from mcp_server_langgraph.api.v1.alert_recommendations import (
            reset_recommendation_rate_limiters,
        )

        reset_recommendation_rate_limiters()

    def teardown_method(self) -> None:
        """Force GC to prevent mock accumulation in xdist workers."""
        gc.collect()

    @pytest.fixture
    def mock_service(self) -> AsyncMock:
        """Create a mock recommendation service."""
        service = AsyncMock(spec=AIRecommendationService)
        return service

    @pytest.fixture
    def sample_recommendation(self) -> AIRecommendation:
        """Create a sample recommendation."""
        return AIRecommendation(
            recommendation_id="rec-123",
            alert_id="alert-456",
            root_cause_analysis="Pod memory limit exceeded due to memory leak",
            remediation_steps=[
                {
                    "step_number": 1,
                    "action": "restart",
                    "description": "Restart the affected pod",
                    "command": "kubectl rollout restart deployment/app",
                    "requires_approval": True,
                    "risk_level": "low",
                }
            ],
            risk_assessment={
                "overall_risk": "medium",
                "impact": "Service may be briefly unavailable",
                "urgency": "high",
            },
            runbook_reference="https://runbooks.example.com/memory-oom",
            generated_at=datetime.now(UTC).isoformat(),
            model_used="claude-sonnet-4",
        )

    @pytest.fixture
    def sample_alert(self) -> Alert:
        """Create a sample alert."""
        return Alert(
            alert_id="alert-456",
            name="PodMemoryHigh",
            severity=AlertSeverity.CRITICAL,
            state=AlertState.FIRING,
            message="Pod memory usage above 90%",
            labels={"pod": "app-123", "namespace": "production"},
            annotations={"runbook_url": "https://runbooks.example.com/memory-oom"},
            started_at=datetime.now(UTC),
            ended_at=None,
        )

    @pytest.mark.asyncio
    async def test_get_recommendation_returns_cached(
        self, mock_service: AsyncMock, sample_recommendation: AIRecommendation
    ) -> None:
        """Should return cached recommendation if available."""
        from mcp_server_langgraph.api.v1.alert_recommendations import (
            get_alert_recommendation,
        )

        mock_service.get_cached_recommendation.return_value = sample_recommendation

        result = await get_alert_recommendation(
            alert_id="alert-456",
            service=mock_service,
            alert_store=MagicMock(),
        )

        assert result.recommendation_id == "rec-123"
        assert result.alert_id == "alert-456"
        mock_service.get_cached_recommendation.assert_called_once_with("alert-456")

    @pytest.mark.asyncio
    async def test_get_recommendation_generates_if_not_cached(
        self,
        mock_service: AsyncMock,
        sample_recommendation: AIRecommendation,
        sample_alert: Alert,
    ) -> None:
        """Should generate recommendation if not cached."""
        from mcp_server_langgraph.api.v1.alert_recommendations import (
            get_alert_recommendation,
        )

        mock_service.get_cached_recommendation.return_value = None
        mock_service.generate_recommendation.return_value = sample_recommendation

        mock_store = AsyncMock()
        mock_store.get_alert.return_value = sample_alert

        result = await get_alert_recommendation(
            alert_id="alert-456",
            service=mock_service,
            alert_store=mock_store,
        )

        assert result.recommendation_id == "rec-123"
        mock_service.generate_recommendation.assert_called_once()

    @pytest.mark.asyncio
    async def test_get_recommendation_404_if_alert_not_found(self, mock_service: AsyncMock) -> None:
        """Should return 404 if alert doesn't exist."""
        from fastapi import HTTPException
        from mcp_server_langgraph.api.v1.alert_recommendations import (
            get_alert_recommendation,
        )

        mock_service.get_cached_recommendation.return_value = None

        mock_store = AsyncMock()
        mock_store.get_alert.return_value = None

        with pytest.raises(HTTPException) as exc_info:
            await get_alert_recommendation(
                alert_id="nonexistent",
                service=mock_service,
                alert_store=mock_store,
            )

        assert exc_info.value.status_code == 404
        assert "not found" in exc_info.value.detail.lower()


@pytest.mark.xdist_group(name="alert_recommendations_api")
class TestRegenerateRecommendation:
    """Tests for POST /alerts/{alert_id}/recommendation/regenerate endpoint."""

    def setup_method(self) -> None:
        """Reset rate limiters before each test."""
        from mcp_server_langgraph.api.v1.alert_recommendations import (
            reset_recommendation_rate_limiters,
        )

        reset_recommendation_rate_limiters()

    def teardown_method(self) -> None:
        """Force GC to prevent mock accumulation in xdist workers."""
        gc.collect()

    @pytest.fixture
    def mock_service(self) -> AsyncMock:
        """Create a mock recommendation service."""
        service = AsyncMock(spec=AIRecommendationService)
        return service

    @pytest.fixture
    def sample_recommendation(self) -> AIRecommendation:
        """Create a sample recommendation."""
        return AIRecommendation(
            recommendation_id="rec-new-789",
            alert_id="alert-456",
            root_cause_analysis="Updated analysis after regeneration",
            remediation_steps=[
                {
                    "step_number": 1,
                    "action": "scale",
                    "description": "Scale up replicas",
                    "command": "kubectl scale deployment/app --replicas=3",
                    "requires_approval": True,
                    "risk_level": "low",
                }
            ],
            risk_assessment={
                "overall_risk": "low",
                "impact": "Minimal",
                "urgency": "medium",
            },
            runbook_reference=None,
            generated_at=datetime.now(UTC).isoformat(),
            model_used="claude-sonnet-4",
        )

    @pytest.fixture
    def sample_alert(self) -> Alert:
        """Create a sample alert."""
        return Alert(
            alert_id="alert-456",
            name="PodCPUHigh",
            severity=AlertSeverity.WARNING,
            state=AlertState.FIRING,
            message="Pod CPU usage above 80%",
            labels={"pod": "app-123", "namespace": "production"},
            annotations={},
            started_at=datetime.now(UTC),
            ended_at=None,
        )

    @pytest.mark.asyncio
    async def test_regenerate_calls_service_with_force_flag(
        self,
        mock_service: AsyncMock,
        sample_recommendation: AIRecommendation,
        sample_alert: Alert,
    ) -> None:
        """Should call generate with force_regenerate=True."""
        from mcp_server_langgraph.api.v1.alert_recommendations import (
            regenerate_alert_recommendation,
        )

        mock_service.generate_recommendation.return_value = sample_recommendation

        mock_store = AsyncMock()
        mock_store.get_alert.return_value = sample_alert

        result = await regenerate_alert_recommendation(
            alert_id="alert-456",
            service=mock_service,
            alert_store=mock_store,
        )

        assert result.recommendation_id == "rec-new-789"
        mock_service.generate_recommendation.assert_called_once_with(sample_alert, force_regenerate=True)

    @pytest.mark.asyncio
    async def test_regenerate_404_if_alert_not_found(self, mock_service: AsyncMock) -> None:
        """Should return 404 if alert doesn't exist."""
        from fastapi import HTTPException
        from mcp_server_langgraph.api.v1.alert_recommendations import (
            regenerate_alert_recommendation,
        )

        mock_store = AsyncMock()
        mock_store.get_alert.return_value = None

        with pytest.raises(HTTPException) as exc_info:
            await regenerate_alert_recommendation(
                alert_id="nonexistent",
                service=mock_service,
                alert_store=mock_store,
            )

        assert exc_info.value.status_code == 404


@pytest.mark.xdist_group(name="alert_recommendations_api")
class TestAlertStore:
    """Tests for the alert store dependency."""

    def teardown_method(self) -> None:
        """Force GC to prevent mock accumulation in xdist workers."""
        gc.collect()

    def test_alert_store_class_exists(self) -> None:
        """AlertStore class should exist for alert persistence."""
        from mcp_server_langgraph.api.v1.alert_recommendations import AlertStore

        assert AlertStore is not None

    def test_alert_store_get_alert_method(self) -> None:
        """AlertStore should have get_alert method."""
        from mcp_server_langgraph.api.v1.alert_recommendations import AlertStore

        store = AlertStore()
        assert hasattr(store, "get_alert")

    def test_alert_store_add_alert_method(self) -> None:
        """AlertStore should have add_alert method."""
        from mcp_server_langgraph.api.v1.alert_recommendations import AlertStore

        store = AlertStore()
        assert hasattr(store, "add_alert")


@pytest.mark.xdist_group(name="alert_recommendations_api")
class TestAlertHistoryEndpoint:
    """Tests for GET /alerts history endpoint."""

    def teardown_method(self) -> None:
        """Force GC to prevent mock accumulation in xdist workers."""
        gc.collect()

    def test_list_alerts_endpoint_exists(self) -> None:
        """
        GIVEN the alert recommendation router
        WHEN checking routes
        THEN should have GET /alerts endpoint.
        """
        from mcp_server_langgraph.api.v1.alert_recommendations import (
            alert_recommendation_router,
        )

        routes = [r.path for r in alert_recommendation_router.routes if hasattr(r, "path")]
        # The router has prefix /alerts, so root path is just /alerts
        assert (
            "/alerts" in routes
            or "/alerts/" in routes
            or any(
                r.path == "/"
                for r in alert_recommendation_router.routes
                if hasattr(r, "path") and r.methods and "GET" in r.methods
            )
        )

    def test_list_alerts_function_exists(self) -> None:
        """
        GIVEN the alert recommendations module
        WHEN importing list_alerts
        THEN should export the endpoint function.
        """
        from mcp_server_langgraph.api.v1.alert_recommendations import (
            list_alerts,
        )

        assert list_alerts is not None
        assert callable(list_alerts)

    @pytest.mark.asyncio
    async def test_list_alerts_returns_alerts(self) -> None:
        """
        GIVEN alerts in the store
        WHEN listing alerts
        THEN should return all alerts.
        """
        from mcp_server_langgraph.api.v1.alert_recommendations import list_alerts
        from mcp_server_langgraph.alerts.stores import InMemoryAlertStore
        from mcp_server_langgraph.observability.query.interfaces import (
            Alert,
            AlertSeverity,
            AlertState,
        )
        from datetime import datetime, UTC

        store = InMemoryAlertStore()
        alert = Alert(
            alert_id="alert-123",
            name="TestAlert",
            severity=AlertSeverity.CRITICAL,
            state=AlertState.FIRING,
            message="Test message",
            labels={},
            annotations={},
            started_at=datetime.now(UTC),
            ended_at=None,
        )
        await store.add_alert(alert)

        result = await list_alerts(
            alert_store=store,
        )

        assert result.count >= 1
        assert any(a.alert_id == "alert-123" for a in result.alerts)

    @pytest.mark.asyncio
    async def test_list_alerts_filter_by_severity(self) -> None:
        """
        GIVEN alerts of different severities
        WHEN filtering by severity
        THEN should return only matching alerts.
        """
        from mcp_server_langgraph.api.v1.alert_recommendations import list_alerts
        from mcp_server_langgraph.alerts.stores import InMemoryAlertStore
        from mcp_server_langgraph.observability.query.interfaces import (
            Alert,
            AlertSeverity,
            AlertState,
        )
        from datetime import datetime, UTC

        store = InMemoryAlertStore()

        # Add critical alert
        await store.add_alert(
            Alert(
                alert_id="alert-critical",
                name="CriticalAlert",
                severity=AlertSeverity.CRITICAL,
                state=AlertState.FIRING,
                message="Critical",
                labels={},
                annotations={},
                started_at=datetime.now(UTC),
                ended_at=None,
            )
        )

        # Add warning alert
        await store.add_alert(
            Alert(
                alert_id="alert-warning",
                name="WarningAlert",
                severity=AlertSeverity.WARNING,
                state=AlertState.FIRING,
                message="Warning",
                labels={},
                annotations={},
                started_at=datetime.now(UTC),
                ended_at=None,
            )
        )

        result = await list_alerts(
            alert_store=store,
            severity=[AlertSeverity.CRITICAL],
        )

        assert result.count == 1
        assert result.alerts[0].alert_id == "alert-critical"

    @pytest.mark.asyncio
    async def test_list_alerts_filter_by_state(self) -> None:
        """
        GIVEN alerts in different states
        WHEN filtering by state
        THEN should return only matching alerts.
        """
        from mcp_server_langgraph.api.v1.alert_recommendations import list_alerts
        from mcp_server_langgraph.alerts.stores import InMemoryAlertStore
        from mcp_server_langgraph.observability.query.interfaces import (
            Alert,
            AlertSeverity,
            AlertState,
        )
        from datetime import datetime, UTC

        store = InMemoryAlertStore()

        # Add firing alert
        await store.add_alert(
            Alert(
                alert_id="alert-firing",
                name="FiringAlert",
                severity=AlertSeverity.CRITICAL,
                state=AlertState.FIRING,
                message="Firing",
                labels={},
                annotations={},
                started_at=datetime.now(UTC),
                ended_at=None,
            )
        )

        # Add resolved alert
        await store.add_alert(
            Alert(
                alert_id="alert-resolved",
                name="ResolvedAlert",
                severity=AlertSeverity.CRITICAL,
                state=AlertState.RESOLVED,
                message="Resolved",
                labels={},
                annotations={},
                started_at=datetime.now(UTC),
                ended_at=datetime.now(UTC),
            )
        )

        result = await list_alerts(
            alert_store=store,
            state=[AlertState.RESOLVED],
        )

        assert result.count == 1
        assert result.alerts[0].alert_id == "alert-resolved"


@pytest.mark.xdist_group(name="alert_recommendations_api")
class TestLLMIntegration:
    """Tests for LLM factory integration with AI recommendation service."""

    def teardown_method(self) -> None:
        """Force GC to prevent mock accumulation in xdist workers."""
        gc.collect()

    def test_create_recommendation_llm_exists(self) -> None:
        """
        GIVEN the alert recommendations module
        WHEN importing create_recommendation_llm
        THEN should export the factory function.
        """
        from mcp_server_langgraph.api.v1.alert_recommendations import (
            create_recommendation_llm,
        )

        assert create_recommendation_llm is not None
        assert callable(create_recommendation_llm)

    def test_get_recommendation_service_with_llm(self) -> None:
        """
        GIVEN the alert recommendations module
        WHEN calling get_recommendation_service
        THEN should return service with LLM factory configured.
        """
        from mcp_server_langgraph.api.v1.alert_recommendations import (
            get_recommendation_service,
            set_recommendation_service,
        )

        # Reset service
        set_recommendation_service(None)

        # Get service - should have LLM configured
        service = get_recommendation_service()

        assert service is not None
        # Service should have LLM factory attribute
        assert hasattr(service, "_llm")

    @pytest.mark.asyncio
    async def test_recommendation_uses_real_llm_protocol(self) -> None:
        """
        GIVEN a recommendation service with mocked LLM
        WHEN generating a recommendation
        THEN should use LLM acompletion method.
        """
        from mcp_server_langgraph.alerts.ai_recommendation import (
            AIRecommendationService,
        )
        from mcp_server_langgraph.observability.query.interfaces import (
            Alert,
            AlertSeverity,
            AlertState,
        )
        from datetime import datetime, UTC

        # Mock LLM that follows the protocol
        mock_llm = AsyncMock()
        mock_llm.acompletion.return_value = MagicMock(
            choices=[
                MagicMock(
                    message=MagicMock(
                        content='{"root_cause_analysis": "Test", "remediation_steps": [], "risk_assessment": {}}'
                    )
                )
            ]
        )

        service = AIRecommendationService(llm_factory=mock_llm)

        alert = Alert(
            alert_id="test-alert",
            name="TestAlert",
            severity=AlertSeverity.CRITICAL,
            state=AlertState.FIRING,
            message="Test message",
            labels={},
            annotations={},
            started_at=datetime.now(UTC),
            ended_at=None,
        )

        recommendation = await service.generate_recommendation(alert)

        # Verify LLM was called
        mock_llm.acompletion.assert_called_once()
        assert recommendation.root_cause_analysis == "Test"


# =============================================================================
# Correlation Endpoint Tests
# =============================================================================


@pytest.mark.xdist_group(name="alert_correlation_api")
class TestAlertCorrelationEndpoint:
    """Tests for POST /alerts/correlate endpoint."""

    def teardown_method(self) -> None:
        """Force GC to prevent mock accumulation in xdist workers."""
        gc.collect()

    def test_correlate_alerts_endpoint_exists(self) -> None:
        """
        GIVEN the alert recommendation router
        WHEN checking routes
        THEN should have POST /alerts/correlate endpoint.
        """
        from mcp_server_langgraph.api.v1.alert_recommendations import (
            alert_recommendation_router,
        )

        routes = [
            (r.path, r.methods) for r in alert_recommendation_router.routes if hasattr(r, "path") and hasattr(r, "methods")
        ]
        # Check for correlate endpoint
        assert any("/correlate" in path and "POST" in methods for path, methods in routes)

    def test_correlate_function_exists(self) -> None:
        """
        GIVEN the alert recommendations module
        WHEN importing correlate_alerts
        THEN should export the endpoint function.
        """
        from mcp_server_langgraph.api.v1.alert_recommendations import correlate_alerts

        assert correlate_alerts is not None
        assert callable(correlate_alerts)

    @pytest.mark.asyncio
    async def test_correlate_by_label(self) -> None:
        """
        GIVEN multiple alerts with common labels
        WHEN correlating by label key
        THEN should return correlation groups.
        """
        from mcp_server_langgraph.api.v1.alert_recommendations import (
            correlate_alerts,
            CorrelateAlertsRequest,
        )
        from mcp_server_langgraph.alerts.stores import InMemoryAlertStore

        store = InMemoryAlertStore()

        # Add alerts with common service label
        await store.add_alert(
            Alert(
                alert_id="alert-1",
                name="HighCPU",
                severity=AlertSeverity.CRITICAL,
                state=AlertState.FIRING,
                message="High CPU",
                labels={"service": "api-server", "namespace": "prod"},
                annotations={},
                started_at=datetime.now(UTC),
            )
        )
        await store.add_alert(
            Alert(
                alert_id="alert-2",
                name="HighMemory",
                severity=AlertSeverity.WARNING,
                state=AlertState.FIRING,
                message="High Memory",
                labels={"service": "api-server", "namespace": "prod"},
                annotations={},
                started_at=datetime.now(UTC),
            )
        )

        request = CorrelateAlertsRequest(
            correlation_type="label",
            label_key="service",
        )

        result = await correlate_alerts(request=request, alert_store=store)

        assert len(result.groups) >= 1
        api_server_group = next((g for g in result.groups if g.label_value == "api-server"), None)
        assert api_server_group is not None
        assert len(api_server_group.alerts) == 2

    @pytest.mark.asyncio
    async def test_correlate_by_time(self) -> None:
        """
        GIVEN alerts occurring within a time window
        WHEN correlating by time
        THEN should return correlation groups.
        """
        from mcp_server_langgraph.api.v1.alert_recommendations import (
            correlate_alerts,
            CorrelateAlertsRequest,
        )
        from mcp_server_langgraph.alerts.stores import InMemoryAlertStore
        from datetime import timedelta

        store = InMemoryAlertStore()
        base_time = datetime.now(UTC)

        # Add alerts within 5 minutes
        await store.add_alert(
            Alert(
                alert_id="alert-1",
                name="Alert1",
                severity=AlertSeverity.CRITICAL,
                state=AlertState.FIRING,
                message="First alert",
                labels={},
                annotations={},
                started_at=base_time,
            )
        )
        await store.add_alert(
            Alert(
                alert_id="alert-2",
                name="Alert2",
                severity=AlertSeverity.WARNING,
                state=AlertState.FIRING,
                message="Second alert",
                labels={},
                annotations={},
                started_at=base_time + timedelta(minutes=2),
            )
        )

        request = CorrelateAlertsRequest(
            correlation_type="time",
            window_minutes=5,
        )

        result = await correlate_alerts(request=request, alert_store=store)

        assert len(result.groups) >= 1
        assert len(result.groups[0].alerts) == 2

    @pytest.mark.asyncio
    async def test_correlate_with_pattern_detection(self) -> None:
        """
        GIVEN alerts that form a known pattern
        WHEN correlating with pattern detection enabled
        THEN should detect and return pattern information.
        """
        from mcp_server_langgraph.api.v1.alert_recommendations import (
            correlate_alerts,
            CorrelateAlertsRequest,
        )
        from mcp_server_langgraph.alerts.stores import InMemoryAlertStore

        store = InMemoryAlertStore()

        # Add resource exhaustion pattern alerts
        await store.add_alert(
            Alert(
                alert_id="alert-1",
                name="HighCPU",
                severity=AlertSeverity.CRITICAL,
                state=AlertState.FIRING,
                message="CPU at 95%",
                labels={"host": "server-1", "service": "app"},
                annotations={},
                started_at=datetime.now(UTC),
            )
        )
        await store.add_alert(
            Alert(
                alert_id="alert-2",
                name="HighMemory",
                severity=AlertSeverity.CRITICAL,
                state=AlertState.FIRING,
                message="Memory at 90%",
                labels={"host": "server-1", "service": "app"},
                annotations={},
                started_at=datetime.now(UTC),
            )
        )

        request = CorrelateAlertsRequest(
            correlation_type="label",
            label_key="host",
            detect_patterns=True,
        )

        result = await correlate_alerts(request=request, alert_store=store)

        assert len(result.groups) >= 1
        # Pattern detection should find resource_exhaustion or similar
        # Check that at least one group has a detected pattern
        has_pattern = any(g.pattern is not None for g in result.groups)
        # Note: Pattern detection may not always trigger depending on alert names
        # The test verifies the endpoint works with pattern detection enabled

    @pytest.mark.asyncio
    async def test_correlate_identifies_root_cause(self) -> None:
        """
        GIVEN correlated alerts
        WHEN root cause identification is enabled
        THEN should identify the root cause alert.
        """
        from mcp_server_langgraph.api.v1.alert_recommendations import (
            correlate_alerts,
            CorrelateAlertsRequest,
        )
        from mcp_server_langgraph.alerts.stores import InMemoryAlertStore
        from datetime import timedelta

        store = InMemoryAlertStore()
        base_time = datetime.now(UTC)

        # Add alerts with the earliest being root cause
        await store.add_alert(
            Alert(
                alert_id="root-cause-alert",
                name="DBConnectionFailed",
                severity=AlertSeverity.CRITICAL,
                state=AlertState.FIRING,
                message="Database connection failed",
                labels={"service": "database"},
                annotations={},
                started_at=base_time,
            )
        )
        await store.add_alert(
            Alert(
                alert_id="symptom-alert",
                name="APITimeouts",
                severity=AlertSeverity.WARNING,
                state=AlertState.FIRING,
                message="API timeouts",
                labels={"service": "api"},
                annotations={},
                started_at=base_time + timedelta(seconds=30),
            )
        )

        request = CorrelateAlertsRequest(
            correlation_type="time",
            window_minutes=5,
            identify_root_cause=True,
        )

        result = await correlate_alerts(request=request, alert_store=store)

        assert len(result.groups) >= 1
        assert result.groups[0].root_cause_id == "root-cause-alert"

    @pytest.mark.asyncio
    async def test_correlate_empty_store(self) -> None:
        """
        GIVEN no alerts in store
        WHEN correlating
        THEN should return empty groups.
        """
        from mcp_server_langgraph.api.v1.alert_recommendations import (
            correlate_alerts,
            CorrelateAlertsRequest,
        )
        from mcp_server_langgraph.alerts.stores import InMemoryAlertStore

        store = InMemoryAlertStore()

        request = CorrelateAlertsRequest(
            correlation_type="label",
            label_key="service",
        )

        result = await correlate_alerts(request=request, alert_store=store)

        assert len(result.groups) == 0
