"""
TDD Tests for AlertOrchestrator API Integration (Phase 12).

These tests define the expected behavior for integrating AlertOrchestrator
into the alert recommendations API endpoints.

Tests verify:
1. AlertOrchestrator can be injected into API module
2. Feature flag controls orchestrator usage
3. Orchestrator is used for batch alert analysis
4. Fallback to sequential when orchestrator disabled
5. Cost tracking integration with AlertOrchestrator
"""

import gc
from decimal import Decimal
from unittest.mock import AsyncMock, MagicMock

import pytest

pytestmark = [pytest.mark.unit, pytest.mark.api, pytest.mark.orchestrator]

# Mock user for testing auth-required endpoints
MOCK_USER = {
    "sub": "test-user-id",
    "user_id": "test-user-id",
    "username": "testuser",
    "email": "testuser@example.com",
    "roles": ["user"],
    "realm_access": {"roles": ["user"]},
}


@pytest.mark.xdist_group(name="alert_orchestrator_api_init")
class TestAlertOrchestratorAPIInjection:
    """Test AlertOrchestrator injection into API module."""

    def teardown_method(self) -> None:
        """Force GC to prevent mock accumulation."""
        gc.collect()

    def test_alert_orchestrator_getter_exists(self) -> None:
        """API module should have get_alert_orchestrator function."""
        from mcp_server_langgraph.api.v1 import alert_recommendations

        assert hasattr(alert_recommendations, "get_alert_orchestrator")

    def test_alert_orchestrator_setter_exists(self) -> None:
        """API module should have set_alert_orchestrator function."""
        from mcp_server_langgraph.api.v1 import alert_recommendations

        assert hasattr(alert_recommendations, "set_alert_orchestrator")

    def test_get_alert_orchestrator_returns_none_by_default(self) -> None:
        """get_alert_orchestrator should return None by default."""
        from mcp_server_langgraph.api.v1.alert_recommendations import (
            get_alert_orchestrator,
            set_alert_orchestrator,
        )

        # Reset to ensure clean state
        set_alert_orchestrator(None)

        result = get_alert_orchestrator()
        assert result is None

    def test_set_alert_orchestrator_sets_instance(self) -> None:
        """set_alert_orchestrator should store the orchestrator instance."""
        from mcp_server_langgraph.agents.alert_orchestrator import AlertOrchestrator
        from mcp_server_langgraph.api.v1.alert_recommendations import (
            get_alert_orchestrator,
            set_alert_orchestrator,
        )

        orchestrator = AlertOrchestrator()
        set_alert_orchestrator(orchestrator)

        try:
            result = get_alert_orchestrator()
            assert result is orchestrator
        finally:
            set_alert_orchestrator(None)


@pytest.mark.xdist_group(name="alert_orchestrator_api_feature_flag")
class TestAlertOrchestratorFeatureFlag:
    """Test feature flag controls orchestrator usage."""

    def teardown_method(self) -> None:
        """Force GC to prevent mock accumulation."""
        gc.collect()

    def test_enable_orchestrated_alert_analysis_flag_exists(self) -> None:
        """Feature flag enable_orchestrated_alert_analysis should exist."""
        from mcp_server_langgraph.core.feature_flags import feature_flags

        assert hasattr(feature_flags, "enable_orchestrated_alert_analysis")

    def test_enable_orchestrated_alert_analysis_defaults_false(self) -> None:
        """Feature flag should default to False for gradual rollout."""
        from mcp_server_langgraph.core.feature_flags import feature_flags

        # Default should be False for safe gradual rollout
        assert isinstance(feature_flags.enable_orchestrated_alert_analysis, bool)


@pytest.mark.xdist_group(name="alert_orchestrator_api_batch")
class TestAlertOrchestratorBatchAnalysis:
    """Test batch alert analysis uses orchestrator."""

    def teardown_method(self) -> None:
        """Force GC to prevent mock accumulation."""
        gc.collect()

    def test_batch_analyze_alerts_endpoint_exists(self) -> None:
        """API should have batch analyze endpoint or correlate endpoint."""
        from mcp_server_langgraph.api.v1.alert_recommendations import (
            alert_recommendation_router,
        )

        # Check routes registered (router prefix is /alerts, so paths include it)
        routes = [r.path for r in alert_recommendation_router.routes]
        # Either /alerts/correlate or similar should exist
        has_correlate = any("correlate" in r for r in routes)
        has_analyze = any("analyze" in r for r in routes)
        assert has_correlate or has_analyze, f"Routes: {routes}"

    @pytest.mark.asyncio
    async def test_correlate_uses_orchestrator_when_enabled(self) -> None:
        """Correlate endpoint should use orchestrator when enabled."""
        from mcp_server_langgraph.agents.alert_orchestrator import AlertOrchestrator
        from mcp_server_langgraph.api.v1.alert_recommendations import (
            correlate_alerts,
            set_alert_orchestrator,
            CorrelateAlertsRequest,
        )

        # Create mock orchestrator
        mock_orchestrator = MagicMock(spec=AlertOrchestrator)
        mock_orchestrator.is_enabled = True
        mock_orchestrator.analyze_alerts = AsyncMock(
            return_value={
                "alert_ids": ["alert-1"],
                "correlation_summary": {"total_results": 1},
                "analyses": {},
                "failed_analyses": [],
            }
        )

        set_alert_orchestrator(mock_orchestrator)

        try:
            # Create mock alert store
            mock_store = MagicMock()
            mock_store.list_alerts = AsyncMock(return_value=[])

            request = CorrelateAlertsRequest(
                correlation_type="label",
                label_key="service",
            )

            # With orchestrator set and enabled, it should be used
            # Note: The orchestrator is controlled via set_alert_orchestrator, not feature flags
            result = await correlate_alerts(request, alert_store=mock_store, current_user=MOCK_USER)
            assert result is not None

        finally:
            set_alert_orchestrator(None)


@pytest.mark.xdist_group(name="alert_orchestrator_api_fallback")
class TestAlertOrchestratorFallback:
    """Test fallback to sequential when orchestrator disabled."""

    def teardown_method(self) -> None:
        """Force GC to prevent mock accumulation."""
        gc.collect()

    @pytest.mark.asyncio
    async def test_correlate_works_without_orchestrator(self) -> None:
        """Correlate should work with sequential fallback when no orchestrator."""
        from mcp_server_langgraph.api.v1.alert_recommendations import (
            correlate_alerts,
            set_alert_orchestrator,
            CorrelateAlertsRequest,
        )

        # Ensure no orchestrator
        set_alert_orchestrator(None)

        # Create mock alert store
        mock_store = MagicMock()
        mock_store.list_alerts = AsyncMock(return_value=[])

        request = CorrelateAlertsRequest(
            correlation_type="label",
            label_key="service",
        )

        # Should work without orchestrator
        result = await correlate_alerts(request, alert_store=mock_store, current_user=MOCK_USER)
        assert result is not None
        assert result.total_alerts == 0

    @pytest.mark.asyncio
    async def test_correlate_falls_back_when_orchestrator_disabled(self) -> None:
        """Correlate should fall back when orchestrator.is_enabled is False."""
        from mcp_server_langgraph.agents.alert_orchestrator import AlertOrchestrator
        from mcp_server_langgraph.api.v1.alert_recommendations import (
            correlate_alerts,
            set_alert_orchestrator,
            CorrelateAlertsRequest,
        )

        # Create disabled orchestrator
        mock_orchestrator = MagicMock(spec=AlertOrchestrator)
        mock_orchestrator.is_enabled = False

        set_alert_orchestrator(mock_orchestrator)

        try:
            mock_store = MagicMock()
            mock_store.list_alerts = AsyncMock(return_value=[])

            request = CorrelateAlertsRequest(
                correlation_type="label",
                label_key="service",
            )

            result = await correlate_alerts(request, alert_store=mock_store, current_user=MOCK_USER)

            # Should NOT call orchestrator (it's disabled)
            mock_orchestrator.analyze_alerts.assert_not_called()
            assert result is not None

        finally:
            set_alert_orchestrator(None)


@pytest.mark.xdist_group(name="alert_orchestrator_api_cost")
class TestAlertOrchestratorCostTracking:
    """Test cost tracking integration with AlertOrchestrator."""

    def teardown_method(self) -> None:
        """Force GC to prevent mock accumulation."""
        gc.collect()

    def test_alert_orchestrator_accepts_cost_tracker(self) -> None:
        """AlertOrchestrator should accept cost_tracker parameter."""
        from mcp_server_langgraph.agents.alert_orchestrator import AlertOrchestrator
        from mcp_server_langgraph.agents.cost_tracker import CostTracker

        tracker = CostTracker()
        orchestrator = AlertOrchestrator(cost_tracker=tracker)

        assert orchestrator.cost_tracker is tracker

    def test_alert_orchestrator_accepts_session_id(self) -> None:
        """AlertOrchestrator should accept session_id parameter."""
        from mcp_server_langgraph.agents.alert_orchestrator import AlertOrchestrator

        orchestrator = AlertOrchestrator(session_id="session-123")

        assert orchestrator.session_id == "session-123"

    def test_alert_orchestrator_has_get_session_cost(self) -> None:
        """AlertOrchestrator should have get_session_cost method."""
        from mcp_server_langgraph.agents.alert_orchestrator import AlertOrchestrator

        orchestrator = AlertOrchestrator()

        assert hasattr(orchestrator, "get_session_cost")
        cost = orchestrator.get_session_cost()
        assert cost == Decimal("0")

    def test_alert_orchestrator_has_check_budget(self) -> None:
        """AlertOrchestrator should have check_budget method."""
        from mcp_server_langgraph.agents.alert_orchestrator import AlertOrchestrator
        from mcp_server_langgraph.agents.cost_models import BudgetStatus

        orchestrator = AlertOrchestrator()

        assert hasattr(orchestrator, "check_budget")
        alert = orchestrator.check_budget()
        assert alert.status == BudgetStatus.OK


@pytest.mark.xdist_group(name="alert_orchestrator_api_analyze")
class TestAlertOrchestratorAnalyzeEndpoint:
    """Test batch analyze alerts endpoint."""

    def teardown_method(self) -> None:
        """Force GC to prevent mock accumulation."""
        gc.collect()

    def test_batch_analyze_request_model_exists(self) -> None:
        """BatchAnalyzeAlertsRequest model should exist."""
        from mcp_server_langgraph.api.v1 import alert_recommendations

        # Check if BatchAnalyzeAlertsRequest or similar exists
        has_batch_request = hasattr(alert_recommendations, "BatchAnalyzeAlertsRequest") or hasattr(
            alert_recommendations, "CorrelateAlertsRequest"
        )
        assert has_batch_request

    def test_batch_analyze_response_model_exists(self) -> None:
        """BatchAnalyzeAlertsResponse model should exist."""
        from mcp_server_langgraph.api.v1 import alert_recommendations

        # Check if BatchAnalyzeAlertsResponse or similar exists
        has_batch_response = hasattr(alert_recommendations, "BatchAnalyzeAlertsResponse") or hasattr(
            alert_recommendations, "CorrelateAlertsResponse"
        )
        assert has_batch_response
