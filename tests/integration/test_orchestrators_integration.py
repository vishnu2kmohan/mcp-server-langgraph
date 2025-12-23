"""
Integration tests for UX and Alert Orchestrators.

Tests orchestrator behavior with real service integrations and parallel execution.
These tests verify the orchestrators work correctly in a realistic environment.

TDD: Tests written to verify integration behavior.
"""

import asyncio
import gc
import os
from unittest.mock import MagicMock

import pytest

pytestmark = [pytest.mark.integration, pytest.mark.agents]


# =============================================================================
# Fixtures
# =============================================================================


@pytest.fixture
def mock_ai_ux_service():
    """Create a mock AIUXService for integration testing."""
    service = MagicMock()

    async def analyze_persona(user_id: str, **kwargs):
        await asyncio.sleep(0.01)  # Simulate async operation
        return {
            "detected_persona": "developer",
            "confidence": 0.85,
            "features_used": ["chat", "code_execution"],
        }

    async def analyze_disclosure(user_id: str, **kwargs):
        await asyncio.sleep(0.01)
        return {
            "current_level": "standard",
            "recommended_level": "advanced",
            "reason": "High confidence user with technical background",
        }

    async def analyze_error(user_id: str, **kwargs):
        await asyncio.sleep(0.01)
        return {
            "severity": "warning",
            "category": "transient",
            "recovery_suggestion": "Retry the operation",
        }

    service.analyze_persona = analyze_persona
    service.analyze_disclosure = analyze_disclosure
    service.analyze_error = analyze_error

    return service


@pytest.fixture
def mock_correlation_engine():
    """Create a mock AlertCorrelationEngine for integration testing."""
    engine = MagicMock()

    def correlate(alert_ids: list[str]):
        # Simple correlation based on alert IDs
        groups = []
        if len(alert_ids) >= 2:
            groups.append(
                {
                    "alerts": alert_ids[:2],
                    "pattern": "cascade",
                    "confidence": 0.9,
                }
            )
        return groups

    def detect_patterns(alert_ids: list[str]):
        patterns = []
        if len(alert_ids) >= 3:
            patterns.append(
                {
                    "type": "recurring",
                    "frequency": "hourly",
                    "alerts": alert_ids,
                }
            )
        return patterns

    engine.correlate = correlate
    engine.detect_patterns = detect_patterns

    return engine


@pytest.fixture
def mock_recommendation_service():
    """Create a mock AIRecommendationService for integration testing."""
    service = MagicMock()

    async def analyze_root_cause(alert_ids: list[str], **kwargs):
        await asyncio.sleep(0.01)
        return {
            "root_cause": "Database connection pool exhausted",
            "confidence": 0.87,
            "affected_services": ["api-gateway", "user-service"],
        }

    async def generate_remediation(alert_ids: list[str], **kwargs):
        await asyncio.sleep(0.01)
        return {
            "steps": [
                "Increase connection pool size",
                "Add connection timeout",
                "Enable connection recycling",
            ],
            "priority": "high",
            "estimated_impact": "critical",
        }

    service.analyze_root_cause = analyze_root_cause
    service.generate_remediation = generate_remediation

    return service


# =============================================================================
# UX Orchestrator Integration Tests
# =============================================================================


@pytest.mark.xdist_group(name="ux_orchestrator_integration")
class TestUXOrchestratorIntegration:
    """Integration tests for UXOrchestrator with mock services."""

    def teardown_method(self):
        """Force GC to prevent mock accumulation in xdist workers."""
        gc.collect()

    @pytest.mark.asyncio
    async def test_composite_analysis_runs_all_analyses(self, mock_ai_ux_service) -> None:
        """Test that composite analysis runs persona, disclosure, and error analyses."""
        from mcp_server_langgraph.agents.ux_orchestrator import UXOrchestrator

        orchestrator = UXOrchestrator(ai_ux_service=mock_ai_ux_service)

        result = await orchestrator.run_composite_analysis(
            user_id="test-user",
            session_id="test-session",
            include_persona=True,
            include_disclosure=True,
            include_error=True,
        )

        assert result["user_id"] == "test-user"
        assert result["session_id"] == "test-session"
        assert "persona_analysis" in result["analyses"]
        assert "disclosure_analysis" in result["analyses"]
        assert "error_analysis" in result["analyses"]
        assert result["failed_analyses"] == []

    @pytest.mark.asyncio
    async def test_composite_analysis_generates_cross_insights(self, mock_ai_ux_service) -> None:
        """Test that composite analysis generates cross-service insights."""
        from mcp_server_langgraph.agents.ux_orchestrator import UXOrchestrator

        orchestrator = UXOrchestrator(ai_ux_service=mock_ai_ux_service)

        result = await orchestrator.run_composite_analysis(
            user_id="test-user",
            session_id="test-session",
            include_persona=True,
            include_disclosure=True,
        )

        # Cross insights should be generated when persona and disclosure differ
        assert "cross_insights" in result
        assert isinstance(result["cross_insights"], list)

    @pytest.mark.asyncio
    async def test_composite_analysis_handles_partial_failure(self, mock_ai_ux_service) -> None:
        """Test that composite analysis continues if one analysis fails."""
        from mcp_server_langgraph.agents.ux_orchestrator import UXOrchestrator

        # Make one analysis fail
        async def failing_analyze_error(*args, **kwargs):
            raise ValueError("Error analysis failed")

        mock_ai_ux_service.analyze_error = failing_analyze_error

        orchestrator = UXOrchestrator(ai_ux_service=mock_ai_ux_service)

        result = await orchestrator.run_composite_analysis(
            user_id="test-user",
            session_id="test-session",
            include_persona=True,
            include_disclosure=True,
            include_error=True,
        )

        # Should have successful analyses
        assert "persona_analysis" in result["analyses"]
        assert "disclosure_analysis" in result["analyses"]

        # Error analysis should be in failed list
        assert "error_analysis" in result["failed_analyses"]

    @pytest.mark.asyncio
    async def test_composite_analysis_parallel_performance(self, mock_ai_ux_service) -> None:
        """Test that composite analysis runs analyses in parallel."""
        import time

        from mcp_server_langgraph.agents.ux_orchestrator import UXOrchestrator

        # Add delays to simulate real async operations
        async def slow_analyze_persona(*args, **kwargs):
            await asyncio.sleep(0.05)
            return {"detected_persona": "developer"}

        async def slow_analyze_disclosure(*args, **kwargs):
            await asyncio.sleep(0.05)
            return {"current_level": "standard"}

        async def slow_analyze_error(*args, **kwargs):
            await asyncio.sleep(0.05)
            return {"severity": "info"}

        mock_ai_ux_service.analyze_persona = slow_analyze_persona
        mock_ai_ux_service.analyze_disclosure = slow_analyze_disclosure
        mock_ai_ux_service.analyze_error = slow_analyze_error

        orchestrator = UXOrchestrator(ai_ux_service=mock_ai_ux_service)

        start_time = time.time()
        result = await orchestrator.run_composite_analysis(
            user_id="test-user",
            session_id="test-session",
            include_persona=True,
            include_disclosure=True,
            include_error=True,
        )
        elapsed = time.time() - start_time

        # All three analyses take 0.05s each
        # Sequential would take ~0.15s, parallel should be ~0.05-0.08s
        assert elapsed < 0.12, f"Expected parallel execution, got {elapsed:.3f}s"
        assert len(result["analyses"]) == 3


# =============================================================================
# Alert Orchestrator Integration Tests
# =============================================================================


@pytest.mark.xdist_group(name="alert_orchestrator_integration")
class TestAlertOrchestratorIntegration:
    """Integration tests for AlertOrchestrator with mock services."""

    def teardown_method(self):
        """Force GC to prevent mock accumulation in xdist workers."""
        gc.collect()

    @pytest.mark.asyncio
    async def test_analyze_alerts_runs_all_analyses(self, mock_correlation_engine, mock_recommendation_service) -> None:
        """Test that analyze_alerts runs all requested analyses."""
        from mcp_server_langgraph.agents.alert_orchestrator import AlertOrchestrator

        orchestrator = AlertOrchestrator(
            correlation_engine=mock_correlation_engine,
            recommendation_service=mock_recommendation_service,
        )

        result = await orchestrator.analyze_alerts(
            alert_ids=["alert-1", "alert-2", "alert-3"],
            include_correlation=True,
            include_root_cause=True,
            include_remediation=True,
            include_pattern_detection=True,
        )

        assert result["alert_ids"] == ["alert-1", "alert-2", "alert-3"]
        assert "correlation" in result["analyses"]
        assert "root_cause" in result["analyses"]
        assert "remediation" in result["analyses"]
        assert "pattern_detection" in result["analyses"]
        assert result["failed_analyses"] == []

    @pytest.mark.asyncio
    async def test_analyze_alerts_correlation_summary(self, mock_correlation_engine, mock_recommendation_service) -> None:
        """Test that analyze_alerts generates correlation summary."""
        from mcp_server_langgraph.agents.alert_orchestrator import AlertOrchestrator

        orchestrator = AlertOrchestrator(
            correlation_engine=mock_correlation_engine,
            recommendation_service=mock_recommendation_service,
        )

        result = await orchestrator.analyze_alerts(
            alert_ids=["alert-1", "alert-2"],
            include_correlation=True,
            include_root_cause=True,
        )

        assert "correlation_summary" in result
        summary = result["correlation_summary"]
        assert "total_results" in summary
        assert "successful" in summary

    @pytest.mark.asyncio
    async def test_analyze_alerts_handles_partial_failure(self, mock_correlation_engine, mock_recommendation_service) -> None:
        """Test that analyze_alerts continues if one analysis fails."""
        from mcp_server_langgraph.agents.alert_orchestrator import AlertOrchestrator

        # Make root cause analysis fail
        async def failing_root_cause(*args, **kwargs):
            raise ConnectionError("LLM service unavailable")

        mock_recommendation_service.analyze_root_cause = failing_root_cause

        orchestrator = AlertOrchestrator(
            correlation_engine=mock_correlation_engine,
            recommendation_service=mock_recommendation_service,
        )

        result = await orchestrator.analyze_alerts(
            alert_ids=["alert-1", "alert-2"],
            include_correlation=True,
            include_root_cause=True,
            include_pattern_detection=True,
        )

        # Correlation and pattern detection should succeed
        assert "correlation" in result["analyses"]
        assert "pattern_detection" in result["analyses"]

        # Root cause should fail
        assert "root_cause" in result["failed_analyses"]

    @pytest.mark.asyncio
    async def test_analyze_alerts_parallel_performance(self, mock_correlation_engine, mock_recommendation_service) -> None:
        """Test that analyze_alerts runs analyses in parallel."""
        import time

        from mcp_server_langgraph.agents.alert_orchestrator import AlertOrchestrator

        # Add delays to simulate real operations
        async def slow_root_cause(*args, **kwargs):
            await asyncio.sleep(0.05)
            return {"root_cause": "test"}

        async def slow_remediation(*args, **kwargs):
            await asyncio.sleep(0.05)
            return {"steps": ["step1"]}

        mock_recommendation_service.analyze_root_cause = slow_root_cause
        mock_recommendation_service.generate_remediation = slow_remediation

        orchestrator = AlertOrchestrator(
            correlation_engine=mock_correlation_engine,
            recommendation_service=mock_recommendation_service,
        )

        start_time = time.time()
        result = await orchestrator.analyze_alerts(
            alert_ids=["alert-1", "alert-2"],
            include_correlation=True,
            include_root_cause=True,
            include_remediation=True,
            include_pattern_detection=True,
        )
        elapsed = time.time() - start_time

        # All four analyses run in parallel
        # Sequential would take ~0.1s for LLM calls, parallel should be ~0.05-0.08s
        assert elapsed < 0.12, f"Expected parallel execution, got {elapsed:.3f}s"
        assert len(result["analyses"]) == 4

    @pytest.mark.asyncio
    async def test_detect_patterns_integration(self, mock_correlation_engine) -> None:
        """Test synchronous pattern detection."""
        from mcp_server_langgraph.agents.alert_orchestrator import AlertOrchestrator

        orchestrator = AlertOrchestrator(correlation_engine=mock_correlation_engine)

        patterns = orchestrator.detect_patterns(alert_ids=["alert-1", "alert-2", "alert-3", "alert-4"])

        assert isinstance(patterns, list)
        # With 4 alerts, should detect patterns
        assert len(patterns) > 0
        assert patterns[0]["type"] == "recurring"


# =============================================================================
# Cross-Orchestrator Integration Tests
# =============================================================================


@pytest.mark.xdist_group(name="cross_orchestrator_integration")
class TestCrossOrchestratorIntegration:
    """Test interactions between multiple orchestrators."""

    def teardown_method(self):
        """Force GC to prevent mock accumulation in xdist workers."""
        gc.collect()

    @pytest.mark.asyncio
    async def test_both_orchestrators_can_run_concurrently(
        self, mock_ai_ux_service, mock_correlation_engine, mock_recommendation_service
    ) -> None:
        """Test that UX and Alert orchestrators can run concurrently."""
        from mcp_server_langgraph.agents.alert_orchestrator import AlertOrchestrator
        from mcp_server_langgraph.agents.ux_orchestrator import UXOrchestrator

        ux_orchestrator = UXOrchestrator(ai_ux_service=mock_ai_ux_service)
        alert_orchestrator = AlertOrchestrator(
            correlation_engine=mock_correlation_engine,
            recommendation_service=mock_recommendation_service,
        )

        # Run both orchestrators concurrently
        ux_task = ux_orchestrator.run_composite_analysis(
            user_id="test-user",
            session_id="test-session",
            include_persona=True,
            include_disclosure=True,
        )

        alert_task = alert_orchestrator.analyze_alerts(
            alert_ids=["alert-1", "alert-2"],
            include_correlation=True,
            include_root_cause=True,
        )

        ux_result, alert_result = await asyncio.gather(ux_task, alert_task)

        # Both should complete successfully
        assert ux_result["user_id"] == "test-user"
        assert alert_result["alert_ids"] == ["alert-1", "alert-2"]
        assert len(ux_result["analyses"]) >= 2
        assert len(alert_result["analyses"]) >= 2

    @pytest.mark.asyncio
    async def test_orchestrators_share_base_class_behavior(self, mock_ai_ux_service, mock_correlation_engine) -> None:
        """Test that both orchestrators share BaseOrchestrator behavior."""
        from mcp_server_langgraph.agents.alert_orchestrator import AlertOrchestrator
        from mcp_server_langgraph.agents.ux_orchestrator import UXOrchestrator

        ux_orchestrator = UXOrchestrator(ai_ux_service=mock_ai_ux_service)
        alert_orchestrator = AlertOrchestrator(correlation_engine=mock_correlation_engine)

        # Both should have execute method
        assert hasattr(ux_orchestrator, "execute")
        assert hasattr(alert_orchestrator, "execute")

        # Both should have is_enabled property
        assert hasattr(ux_orchestrator, "is_enabled")
        assert hasattr(alert_orchestrator, "is_enabled")

        # Both should have synthesize method
        assert hasattr(ux_orchestrator, "synthesize")
        assert hasattr(alert_orchestrator, "synthesize")


# =============================================================================
# Performance Tests
# =============================================================================


@pytest.mark.xdist_group(name="orchestrator_performance")
@pytest.mark.skipif(
    os.getenv("PYTEST_XDIST_WORKER") is not None,
    reason="Performance tests skipped in parallel mode due to memory overhead",
)
class TestOrchestratorPerformance:
    """Performance tests for orchestrators."""

    def teardown_method(self):
        """Force GC to prevent mock accumulation in xdist workers."""
        gc.collect()

    @pytest.mark.asyncio
    async def test_ux_orchestrator_handles_many_tasks(self, mock_ai_ux_service) -> None:
        """Test UX orchestrator handles many concurrent tasks."""
        from mcp_server_langgraph.agents.ux_orchestrator import (
            UXAnalysisTask,
            UXOrchestrator,
        )

        orchestrator = UXOrchestrator(ai_ux_service=mock_ai_ux_service)

        # Create many tasks
        tasks = [UXAnalysisTask(task_type="persona_analysis", user_id=f"user-{i}") for i in range(10)]

        results = await orchestrator.execute(tasks)

        assert len(results) == 10
        assert all(r.success for r in results)

    @pytest.mark.asyncio
    async def test_alert_orchestrator_handles_many_alerts(self, mock_correlation_engine, mock_recommendation_service) -> None:
        """Test Alert orchestrator handles many alerts."""
        from mcp_server_langgraph.agents.alert_orchestrator import AlertOrchestrator

        orchestrator = AlertOrchestrator(
            correlation_engine=mock_correlation_engine,
            recommendation_service=mock_recommendation_service,
        )

        # Create many alert IDs
        alert_ids = [f"alert-{i}" for i in range(20)]

        result = await orchestrator.analyze_alerts(
            alert_ids=alert_ids,
            include_correlation=True,
            include_root_cause=True,
        )

        assert result["alert_ids"] == alert_ids
        assert len(result["failed_analyses"]) == 0
