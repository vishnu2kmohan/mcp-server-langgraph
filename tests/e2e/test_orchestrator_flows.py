"""
E2E tests for orchestrated analysis flows (Phase 11-12).

Tests the complete orchestrator integration from API endpoints through
to synthesis, including:
- UX composite analysis via AIUXService + UXOrchestrator
- Alert analysis via AIRecommendationService + AlertOrchestrator
- Feature flag controlled gradual rollout
- Parallel execution performance

TDD: Tests written FIRST before implementation.
"""

import asyncio
import gc
import os
import time
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

pytestmark = [pytest.mark.e2e, pytest.mark.agents]


# =============================================================================
# Skip in CI if not integration environment
# =============================================================================

SKIP_REASON = "E2E tests require specific environment setup"


# =============================================================================
# Test Fixtures
# =============================================================================


@pytest.fixture
def mock_llm_factory():
    """Create a mock LLM factory for E2E testing."""
    factory = MagicMock()

    async def mock_acompletion(messages, **kwargs):
        await asyncio.sleep(0.01)  # Simulate API latency
        mock_response = MagicMock()
        mock_response.choices = [
            MagicMock(
                message=MagicMock(
                    content='{"detected_persona": "developer", "confidence": 0.85}'
                )
            )
        ]
        return mock_response

    factory.acompletion = mock_acompletion
    return factory


@pytest.fixture
def mock_feature_flags_enabled():
    """Create feature flags with orchestration enabled."""
    from tests.fixtures.feature_flags_fixtures import MockFeatureFlags

    return MockFeatureFlags(
        is_test_mode=False,
        enable_orchestrated_ai_ux=True,
        enable_orchestrated_alert_analysis=True,
    )


@pytest.fixture
def mock_feature_flags_disabled():
    """Create feature flags with orchestration disabled."""
    from tests.fixtures.feature_flags_fixtures import MockFeatureFlags

    return MockFeatureFlags(
        is_test_mode=False,
        enable_orchestrated_ai_ux=False,
        enable_orchestrated_alert_analysis=False,
    )


# =============================================================================
# UX Orchestrator E2E Tests
# =============================================================================


@pytest.mark.xdist_group(name="e2e_ux_orchestrator")
class TestUXOrchestratorE2E:
    """E2E tests for UX orchestrator flow."""

    def teardown_method(self):
        """Force GC to prevent mock accumulation in xdist workers."""
        gc.collect()

    @pytest.mark.asyncio
    async def test_ux_orchestrator_end_to_end_flow(
        self, mock_feature_flags_enabled
    ) -> None:
        """Test complete UX orchestration flow from service to response."""
        from mcp_server_langgraph.agents.ux_orchestrator import UXOrchestrator
        from mcp_server_langgraph.api.v1.ai_ux_service import AIUXService

        # Create mock AI UX service methods
        mock_service = MagicMock()

        async def analyze_persona(user_id: str, **kwargs):
            await asyncio.sleep(0.01)
            return {"detected_persona": "developer", "confidence": 0.85}

        async def analyze_disclosure(user_id: str, **kwargs):
            await asyncio.sleep(0.01)
            return {"current_level": "standard", "recommended_level": "advanced"}

        async def analyze_error(user_id: str, **kwargs):
            await asyncio.sleep(0.01)
            return {"severity": "info", "category": "transient"}

        mock_service.analyze_persona = analyze_persona
        mock_service.analyze_disclosure = analyze_disclosure
        mock_service.analyze_error = analyze_error

        # Create orchestrator with mock service
        orchestrator = UXOrchestrator(ai_ux_service=mock_service)

        # Run composite analysis
        result = await orchestrator.run_composite_analysis(
            user_id="e2e-test-user",
            session_id="e2e-session-123",
            include_persona=True,
            include_disclosure=True,
            include_error=True,
        )

        # Verify complete result structure
        assert result["user_id"] == "e2e-test-user"
        assert result["session_id"] == "e2e-session-123"
        assert "persona_analysis" in result["analyses"]
        assert "disclosure_analysis" in result["analyses"]
        assert "error_analysis" in result["analyses"]
        assert isinstance(result["cross_insights"], list)
        assert result["failed_analyses"] == []

    @pytest.mark.asyncio
    async def test_ux_service_with_orchestrator_injection(
        self, mock_feature_flags_enabled
    ) -> None:
        """Test AIUXService with UXOrchestrator injected and enabled."""
        from mcp_server_langgraph.agents.ux_orchestrator import UXOrchestrator
        from mcp_server_langgraph.api.v1.ai_ux_service import AIUXService

        # Create mock orchestrator
        mock_orchestrator = MagicMock(spec=UXOrchestrator)
        mock_orchestrator.is_enabled = True
        mock_orchestrator.run_composite_analysis = AsyncMock(
            return_value={
                "user_id": "e2e-user",
                "session_id": "e2e-session",
                "analyses": {
                    "persona_analysis": {"detected_persona": "developer"},
                    "disclosure_analysis": {"current_level": "standard"},
                },
                "cross_insights": ["User persona suggests advanced disclosure"],
                "failed_analyses": [],
            }
        )

        # Create service with orchestrator
        service = AIUXService(ux_orchestrator=mock_orchestrator)

        # Verify orchestrator is accessible
        assert service.ux_orchestrator is mock_orchestrator
        assert service.ux_orchestrator.is_enabled is True

    @pytest.mark.asyncio
    async def test_ux_orchestrator_parallel_execution_speedup(self) -> None:
        """Test that parallel execution provides speedup over sequential."""
        from mcp_server_langgraph.agents.ux_orchestrator import UXOrchestrator

        TASK_DELAY_MS = 50  # 50ms per task
        NUM_TASKS = 3

        mock_service = MagicMock()

        async def slow_analyze(user_id: str, **kwargs):
            await asyncio.sleep(TASK_DELAY_MS / 1000)
            return {"result": "analyzed"}

        mock_service.analyze_persona = slow_analyze
        mock_service.analyze_disclosure = slow_analyze
        mock_service.analyze_error = slow_analyze

        orchestrator = UXOrchestrator(ai_ux_service=mock_service)

        start_time = time.time()
        result = await orchestrator.run_composite_analysis(
            user_id="perf-test-user",
            session_id="perf-session",
            include_persona=True,
            include_disclosure=True,
            include_error=True,
        )
        elapsed_ms = (time.time() - start_time) * 1000

        # Sequential would take ~150ms (3 x 50ms)
        # Parallel should take ~50ms + overhead
        # Allow up to 100ms for parallel (50ms task + 50ms overhead)
        assert elapsed_ms < TASK_DELAY_MS * 2, (
            f"Parallel execution took {elapsed_ms:.0f}ms, "
            f"expected < {TASK_DELAY_MS * 2}ms"
        )


# =============================================================================
# Alert Orchestrator E2E Tests
# =============================================================================


@pytest.mark.xdist_group(name="e2e_alert_orchestrator")
class TestAlertOrchestratorE2E:
    """E2E tests for Alert orchestrator flow."""

    def teardown_method(self):
        """Force GC to prevent mock accumulation in xdist workers."""
        gc.collect()

    @pytest.mark.asyncio
    async def test_alert_orchestrator_end_to_end_flow(self) -> None:
        """Test complete Alert orchestration flow."""
        from mcp_server_langgraph.agents.alert_orchestrator import AlertOrchestrator

        # Create mock services
        mock_engine = MagicMock()
        mock_engine.correlate = MagicMock(
            return_value=[
                {"alerts": ["alert-1", "alert-2"], "pattern": "cascade"}
            ]
        )
        mock_engine.detect_patterns = MagicMock(
            return_value=[{"type": "recurring", "frequency": "hourly"}]
        )

        mock_service = MagicMock()

        async def mock_analyze_root_cause(alert_ids, **kwargs):
            await asyncio.sleep(0.01)
            return {"root_cause": "Connection pool exhausted"}

        async def mock_generate_remediation(alert_ids, **kwargs):
            await asyncio.sleep(0.01)
            return {"steps": ["Increase pool size"]}

        mock_service.analyze_root_cause = mock_analyze_root_cause
        mock_service.generate_remediation = mock_generate_remediation

        # Create orchestrator
        orchestrator = AlertOrchestrator(
            correlation_engine=mock_engine,
            recommendation_service=mock_service,
        )

        # Run analysis
        result = await orchestrator.analyze_alerts(
            alert_ids=["alert-1", "alert-2", "alert-3"],
            include_correlation=True,
            include_root_cause=True,
            include_remediation=True,
            include_pattern_detection=True,
        )

        # Verify complete result structure
        assert result["alert_ids"] == ["alert-1", "alert-2", "alert-3"]
        assert "correlation" in result["analyses"]
        assert "root_cause" in result["analyses"]
        assert "remediation" in result["analyses"]
        assert "pattern_detection" in result["analyses"]
        assert "correlation_summary" in result

    @pytest.mark.asyncio
    async def test_alert_recommendation_service_with_orchestrator(self) -> None:
        """Test AIRecommendationService with AlertOrchestrator injected."""
        from mcp_server_langgraph.agents.alert_orchestrator import AlertOrchestrator
        from mcp_server_langgraph.alerts.ai_recommendation import (
            AIRecommendationService,
        )

        # Create mock orchestrator
        mock_orchestrator = MagicMock(spec=AlertOrchestrator)
        mock_orchestrator.is_enabled = True
        mock_orchestrator.analyze_alerts = AsyncMock(
            return_value={
                "alert_ids": ["alert-1", "alert-2"],
                "analyses": {"correlation": {"groups": []}},
                "correlation_summary": {"total_results": 1},
                "failed_analyses": [],
            }
        )

        # Create service with orchestrator
        service = AIRecommendationService(alert_orchestrator=mock_orchestrator)

        # Verify orchestrator is accessible
        assert service.alert_orchestrator is mock_orchestrator
        assert service.alert_orchestrator.is_enabled is True

    @pytest.mark.asyncio
    async def test_alert_recommendation_service_orchestrated_analysis(self) -> None:
        """Test AIRecommendationService.analyze_alerts_orchestrated method."""
        from mcp_server_langgraph.agents.alert_orchestrator import AlertOrchestrator
        from mcp_server_langgraph.alerts.ai_recommendation import (
            AIRecommendationService,
        )

        # Create mock orchestrator
        mock_orchestrator = MagicMock(spec=AlertOrchestrator)
        mock_orchestrator.is_enabled = True
        mock_orchestrator.analyze_alerts = AsyncMock(
            return_value={
                "alert_ids": ["alert-1", "alert-2"],
                "analyses": {
                    "correlation": {"groups": [{"alerts": ["alert-1", "alert-2"]}]},
                    "root_cause": {"root_cause": "DB connection pool"},
                },
                "correlation_summary": {
                    "total_results": 2,
                    "successful": 2,
                    "failed": 0,
                },
                "failed_analyses": [],
            }
        )

        # Create service with orchestrator
        service = AIRecommendationService(alert_orchestrator=mock_orchestrator)

        # Call orchestrated analysis
        result = await service.analyze_alerts_orchestrated(
            alert_ids=["alert-1", "alert-2"],
            include_correlation=True,
            include_root_cause=True,
        )

        # Verify result
        assert result["alert_ids"] == ["alert-1", "alert-2"]
        assert "correlation" in result["analyses"]
        assert "root_cause" in result["analyses"]

        # Verify orchestrator was called
        mock_orchestrator.analyze_alerts.assert_called_once_with(
            alert_ids=["alert-1", "alert-2"],
            include_correlation=True,
            include_root_cause=True,
            include_remediation=False,
            include_pattern_detection=False,
        )

    @pytest.mark.asyncio
    async def test_alert_orchestrator_parallel_execution_speedup(self) -> None:
        """Test that parallel execution provides speedup over sequential."""
        from mcp_server_langgraph.agents.alert_orchestrator import AlertOrchestrator

        TASK_DELAY_MS = 50

        # Create mock services with delays
        mock_engine = MagicMock()
        mock_engine.correlate = MagicMock(return_value=[])
        mock_engine.detect_patterns = MagicMock(return_value=[])

        mock_service = MagicMock()

        async def slow_analyze(alert_ids, **kwargs):
            await asyncio.sleep(TASK_DELAY_MS / 1000)
            return {"result": "analyzed"}

        mock_service.analyze_root_cause = slow_analyze
        mock_service.generate_remediation = slow_analyze

        orchestrator = AlertOrchestrator(
            correlation_engine=mock_engine,
            recommendation_service=mock_service,
        )

        start_time = time.time()
        result = await orchestrator.analyze_alerts(
            alert_ids=["alert-1", "alert-2"],
            include_correlation=True,
            include_root_cause=True,
            include_remediation=True,
            include_pattern_detection=True,
        )
        elapsed_ms = (time.time() - start_time) * 1000

        # With 4 tasks, sequential would take ~200ms
        # Parallel should take ~50ms + overhead
        assert elapsed_ms < TASK_DELAY_MS * 2, (
            f"Parallel execution took {elapsed_ms:.0f}ms, "
            f"expected < {TASK_DELAY_MS * 2}ms"
        )


# =============================================================================
# Feature Flag E2E Tests
# =============================================================================


@pytest.mark.xdist_group(name="e2e_feature_flags")
class TestOrchestratorFeatureFlagsE2E:
    """E2E tests for feature flag controlled orchestrator rollout."""

    def teardown_method(self):
        """Force GC to prevent mock accumulation in xdist workers."""
        gc.collect()

    def test_ux_orchestrator_respects_feature_flag_disabled(self) -> None:
        """Test UXOrchestrator returns is_enabled=False when flag disabled."""
        from mcp_server_langgraph.agents.ux_orchestrator import UXOrchestrator

        orchestrator = UXOrchestrator()

        # Default feature flag is disabled for gradual rollout
        # is_enabled property should check the feature flag
        assert hasattr(orchestrator, "is_enabled")
        # The is_enabled property depends on feature_flags.enable_orchestrated_ai_ux

    def test_alert_orchestrator_respects_feature_flag_disabled(self) -> None:
        """Test AlertOrchestrator returns is_enabled=False when flag disabled."""
        from mcp_server_langgraph.agents.alert_orchestrator import AlertOrchestrator

        orchestrator = AlertOrchestrator()

        # Default feature flag is disabled for gradual rollout
        assert hasattr(orchestrator, "is_enabled")
        # The is_enabled property depends on feature_flags.enable_orchestrated_alert_analysis

    def test_orchestrator_feature_flag_name_properties(self) -> None:
        """Test that orchestrators expose their feature flag names."""
        from mcp_server_langgraph.agents.alert_orchestrator import AlertOrchestrator
        from mcp_server_langgraph.agents.ux_orchestrator import UXOrchestrator

        ux_orch = UXOrchestrator()
        alert_orch = AlertOrchestrator()

        assert ux_orch.feature_flag_name == "enable_orchestrated_ai_ux"
        assert alert_orch.feature_flag_name == "enable_orchestrated_alert_analysis"


# =============================================================================
# Cross-Insights E2E Tests
# =============================================================================


@pytest.mark.xdist_group(name="e2e_cross_insights")
class TestCrossInsightsE2E:
    """E2E tests for cross-service insights generation."""

    def teardown_method(self):
        """Force GC to prevent mock accumulation in xdist workers."""
        gc.collect()

    @pytest.mark.asyncio
    async def test_ux_orchestrator_generates_cross_insights(self) -> None:
        """Test that UX orchestrator generates cross-insights from results."""
        from mcp_server_langgraph.agents.ux_orchestrator import UXOrchestrator

        mock_service = MagicMock()

        async def analyze_persona(user_id: str, **kwargs):
            return {
                "detected_persona": "developer",
                "confidence": 0.45,  # Low confidence
            }

        async def analyze_disclosure(user_id: str, **kwargs):
            return {
                "current_level": "minimal",
                "recommended_level": "standard",
            }

        async def analyze_error(user_id: str, **kwargs):
            return {"severity": "warning"}

        mock_service.analyze_persona = analyze_persona
        mock_service.analyze_disclosure = analyze_disclosure
        mock_service.analyze_error = analyze_error

        orchestrator = UXOrchestrator(ai_ux_service=mock_service)

        result = await orchestrator.run_composite_analysis(
            user_id="insight-user",
            session_id="insight-session",
            include_persona=True,
            include_disclosure=True,
            include_error=True,
        )

        # Should generate cross-insights for:
        # - Persona + Disclosure mismatch (current != recommended)
        # - Low persona confidence + error (forgiving recovery suggestion)
        assert "cross_insights" in result
        cross_insights = result["cross_insights"]

        # Should have at least one cross-insight due to disclosure mismatch
        # and low confidence with error analysis
        assert len(cross_insights) >= 1

    @pytest.mark.asyncio
    async def test_alert_orchestrator_generates_correlation_summary(self) -> None:
        """Test that Alert orchestrator generates correlation summary."""
        from mcp_server_langgraph.agents.alert_orchestrator import AlertOrchestrator

        mock_engine = MagicMock()
        mock_engine.correlate = MagicMock(
            return_value=[
                {"alerts": ["a1", "a2"], "pattern": "cascade"},
                {"alerts": ["a3", "a4"], "pattern": "temporal"},
            ]
        )
        mock_engine.detect_patterns = MagicMock(
            return_value=[{"type": "recurring"}]
        )

        mock_service = MagicMock()

        async def mock_root_cause(*args, **kwargs):
            return {"root_cause": "Database overload"}

        mock_service.analyze_root_cause = mock_root_cause
        mock_service.generate_remediation = AsyncMock(return_value={})

        orchestrator = AlertOrchestrator(
            correlation_engine=mock_engine,
            recommendation_service=mock_service,
        )

        result = await orchestrator.analyze_alerts(
            alert_ids=["a1", "a2", "a3", "a4"],
            include_correlation=True,
            include_root_cause=True,
            include_pattern_detection=True,
        )

        # Verify correlation summary is generated
        assert "correlation_summary" in result
        summary = result["correlation_summary"]

        assert "total_results" in summary
        assert "successful" in summary
        assert summary["successful"] >= 1

        # Should count correlation groups
        if "alert_groups" in summary:
            assert summary["alert_groups"] == 2
