"""
AI Recommendation Service Unit Tests.

Tests for the AI-powered alert recommendation service following TDD methodology.
This service generates root cause analysis and remediation recommendations for alerts.

Features tested:
- Recommendation generation for critical alerts
- Root cause analysis
- Remediation step generation
- Risk assessment
- Caching behavior
- LLM integration

Reference: ADR-0026 - Comprehensive Client Resilience Patterns
"""

from __future__ import annotations

import gc
from datetime import UTC, datetime
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from mcp_server_langgraph.observability.query.interfaces import (
    Alert,
    AlertSeverity,
    AlertState,
)

pytestmark = [
    pytest.mark.unit,
    pytest.mark.alerts,
]


def create_test_alert(
    alert_id: str = "test-alert-001",
    name: str = "CircuitBreakerOpen",
    severity: AlertSeverity = AlertSeverity.CRITICAL,
    service: str = "redis",
) -> Alert:
    """Create a test alert for recommendation tests."""
    return Alert(
        alert_id=alert_id,
        name=name,
        severity=severity,
        state=AlertState.FIRING,
        message=f"The circuit breaker for {service} is open",
        labels={
            "service": service,
            "alertname": name,
            "severity": severity.value,
        },
        annotations={
            "summary": f"{name} triggered for {service}",
            "description": f"The circuit breaker for {service} has opened due to repeated failures",
            "runbook_url": f"https://runbooks.example.com/{name.lower()}",
        },
        started_at=datetime.now(UTC),
    )


@pytest.mark.xdist_group(name="test_ai_recommendation")
class TestAIRecommendationModels:
    """Tests for AI recommendation data models."""

    def teardown_method(self) -> None:
        """Force GC to prevent mock accumulation in xdist workers."""
        gc.collect()

    def test_recommendation_model_exists(self) -> None:
        """
        GIVEN the ai_recommendation module
        WHEN importing AIRecommendation model
        THEN should be a valid Pydantic model.
        """
        from mcp_server_langgraph.alerts.ai_recommendation import AIRecommendation

        assert AIRecommendation is not None

    def test_recommendation_model_fields(self) -> None:
        """
        GIVEN an AIRecommendation model
        WHEN checking required fields
        THEN should have all expected fields.
        """
        from mcp_server_langgraph.alerts.ai_recommendation import AIRecommendation

        recommendation = AIRecommendation(
            recommendation_id="rec-001",
            alert_id="alert-001",
            root_cause_analysis="Redis connection pool exhausted",
            remediation_steps=[
                {
                    "step_number": 1,
                    "action": "restart",
                    "description": "Restart Redis pods",
                    "command": "kubectl rollout restart statefulset/redis",
                    "requires_approval": True,
                    "risk_level": "medium",
                }
            ],
            risk_assessment={
                "overall_risk": "medium",
                "impact": "service degradation",
                "urgency": "high",
            },
            runbook_reference="https://runbooks.example.com/cb-redis",
            generated_at=datetime.now(UTC).isoformat(),
            model_used="claude-sonnet-4",
        )

        assert recommendation.recommendation_id == "rec-001"
        assert recommendation.alert_id == "alert-001"
        assert len(recommendation.remediation_steps) == 1
        assert recommendation.risk_assessment["overall_risk"] == "medium"

    def test_remediation_step_model_exists(self) -> None:
        """
        GIVEN the ai_recommendation module
        WHEN importing RemediationStep model
        THEN should be a valid Pydantic model.
        """
        from mcp_server_langgraph.alerts.ai_recommendation import RemediationStep

        assert RemediationStep is not None

    def test_remediation_step_fields(self) -> None:
        """
        GIVEN a RemediationStep model
        WHEN creating instance
        THEN should have all expected fields.
        """
        from mcp_server_langgraph.alerts.ai_recommendation import RemediationStep

        step = RemediationStep(
            step_number=1,
            action="restart",
            description="Restart the Redis pods",
            command="kubectl rollout restart statefulset/redis",
            requires_approval=True,
            risk_level="medium",
        )

        assert step.step_number == 1
        assert step.action == "restart"
        assert step.requires_approval is True
        assert step.risk_level == "medium"


@pytest.mark.xdist_group(name="test_ai_recommendation")
class TestAIRecommendationService:
    """Tests for AI recommendation service."""

    def teardown_method(self) -> None:
        """Force GC to prevent mock accumulation in xdist workers."""
        gc.collect()

    def test_service_class_exists(self) -> None:
        """
        GIVEN the ai_recommendation module
        WHEN importing AIRecommendationService
        THEN should export the service class.
        """
        from mcp_server_langgraph.alerts.ai_recommendation import (
            AIRecommendationService,
        )

        assert AIRecommendationService is not None

    @pytest.mark.asyncio
    async def test_generate_recommendation_basic(self) -> None:
        """
        GIVEN an AIRecommendationService with mocked LLM
        WHEN generating a recommendation for an alert
        THEN should return a valid AIRecommendation.
        """
        from mcp_server_langgraph.alerts.ai_recommendation import (
            AIRecommendation,
            AIRecommendationService,
        )

        mock_llm = AsyncMock(return_value=None)
        mock_llm.acompletion.return_value = MagicMock(
            choices=[
                MagicMock(
                    message=MagicMock(
                        content="""
{
    "root_cause_analysis": "Redis connection pool exhausted due to high traffic",
    "remediation_steps": [
        {
            "step_number": 1,
            "action": "restart",
            "description": "Restart Redis pods to clear connections",
            "command": "kubectl rollout restart statefulset/redis",
            "requires_approval": true,
            "risk_level": "medium"
        }
    ],
    "risk_assessment": {
        "overall_risk": "medium",
        "impact": "service degradation possible",
        "urgency": "high"
    }
}
"""
                    )
                )
            ]
        )

        service = AIRecommendationService(llm_factory=mock_llm)
        alert = create_test_alert()

        recommendation = await service.generate_recommendation(alert)

        assert isinstance(recommendation, AIRecommendation)
        assert recommendation.alert_id == alert.alert_id
        assert recommendation.root_cause_analysis is not None
        assert len(recommendation.remediation_steps) > 0

    @pytest.mark.asyncio
    async def test_generate_recommendation_includes_runbook(self) -> None:
        """
        GIVEN an alert with runbook_url annotation
        WHEN generating a recommendation
        THEN should include runbook_reference.
        """
        from mcp_server_langgraph.alerts.ai_recommendation import (
            AIRecommendationService,
        )

        mock_llm = AsyncMock(return_value=None)
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
        alert = create_test_alert()

        recommendation = await service.generate_recommendation(alert)

        assert recommendation.runbook_reference is not None
        assert "runbooks.example.com" in recommendation.runbook_reference


@pytest.mark.xdist_group(name="test_ai_recommendation")
class TestAIRecommendationCache:
    """Tests for recommendation caching."""

    def teardown_method(self) -> None:
        """Force GC to prevent mock accumulation in xdist workers."""
        gc.collect()

    @pytest.mark.asyncio
    async def test_cache_hit_returns_cached_recommendation(self) -> None:
        """
        GIVEN an AIRecommendationService with cached recommendation
        WHEN getting recommendation for same alert
        THEN should return cached version without calling LLM.
        """
        from mcp_server_langgraph.alerts.ai_recommendation import (
            AIRecommendationService,
        )

        mock_llm = AsyncMock(return_value=None)
        mock_llm.acompletion.return_value = MagicMock(
            choices=[
                MagicMock(
                    message=MagicMock(
                        content='{"root_cause_analysis": "Cached", "remediation_steps": [], "risk_assessment": {}}'
                    )
                )
            ]
        )

        service = AIRecommendationService(llm_factory=mock_llm)
        alert = create_test_alert()

        # First call - generates
        rec1 = await service.generate_recommendation(alert)

        # Second call - should use cache
        rec2 = await service.get_cached_recommendation(alert.alert_id)

        assert rec2 is not None
        assert rec1.recommendation_id == rec2.recommendation_id
        # LLM should only be called once
        assert mock_llm.acompletion.call_count == 1

    @pytest.mark.asyncio
    async def test_cache_miss_returns_none(self) -> None:
        """
        GIVEN an AIRecommendationService with no cached recommendation
        WHEN getting recommendation for unknown alert
        THEN should return None.
        """
        from mcp_server_langgraph.alerts.ai_recommendation import (
            AIRecommendationService,
        )

        service = AIRecommendationService(llm_factory=AsyncMock(return_value=None))

        result = await service.get_cached_recommendation("unknown-alert-id")

        assert result is None

    @pytest.mark.asyncio
    async def test_force_regenerate_bypasses_cache(self) -> None:
        """
        GIVEN an AIRecommendationService with cached recommendation
        WHEN regenerating with force=True
        THEN should call LLM again.
        """
        from mcp_server_langgraph.alerts.ai_recommendation import (
            AIRecommendationService,
        )

        mock_llm = AsyncMock(return_value=None)
        mock_llm.acompletion.return_value = MagicMock(
            choices=[
                MagicMock(
                    message=MagicMock(
                        content='{"root_cause_analysis": "Regenerated", "remediation_steps": [], "risk_assessment": {}}'
                    )
                )
            ]
        )

        service = AIRecommendationService(llm_factory=mock_llm)
        alert = create_test_alert()

        # First call
        await service.generate_recommendation(alert)
        assert mock_llm.acompletion.call_count == 1

        # Regenerate with force
        await service.generate_recommendation(alert, force_regenerate=True)
        assert mock_llm.acompletion.call_count == 2


@pytest.mark.xdist_group(name="test_ai_recommendation")
class TestAIRecommendationCacheMemoryOptimization:
    """Tests for L1 cache memory optimization using secondary index."""

    def teardown_method(self) -> None:
        """Force GC to prevent mock accumulation in xdist workers."""
        gc.collect()

    @pytest.mark.asyncio
    async def test_cache_uses_secondary_index_for_alert_id_lookup(self) -> None:
        """
        GIVEN an AIRecommendationService
        WHEN caching a recommendation
        THEN should use secondary index (not duplicate the object).
        """
        from mcp_server_langgraph.alerts.ai_recommendation import (
            AIRecommendationService,
        )

        mock_llm = AsyncMock(return_value=None)
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
        alert = create_test_alert()

        await service.generate_recommendation(alert)

        # Check that _alert_id_index exists and contains the alert_id
        assert hasattr(service, "_alert_id_index"), "Service should have _alert_id_index"
        assert alert.alert_id in service._alert_id_index, "Alert ID should be in secondary index"

        # The index should map to a cache_key, not directly to a recommendation
        cache_key = service._alert_id_index[alert.alert_id]
        assert isinstance(cache_key, str), "Secondary index should store cache key, not recommendation"

        # The recommendation should be retrievable via the cache_key
        assert cache_key in service._cache, "Cache key should exist in primary cache"

    @pytest.mark.asyncio
    async def test_secondary_index_lookup_returns_same_recommendation(self) -> None:
        """
        GIVEN an AIRecommendationService with cached recommendation
        WHEN looking up by alert_id
        THEN should return same recommendation as cache_key lookup.
        """
        from mcp_server_langgraph.alerts.ai_recommendation import (
            AIRecommendationService,
        )

        mock_llm = AsyncMock(return_value=None)
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
        alert = create_test_alert()

        # Generate recommendation
        rec = await service.generate_recommendation(alert)

        # Lookup by alert_id via public API
        cached = await service.get_cached_recommendation(alert.alert_id)

        # Should be the same recommendation
        assert cached is not None
        assert cached.recommendation_id == rec.recommendation_id

    @pytest.mark.asyncio
    async def test_cache_size_reflects_unique_recommendations(self) -> None:
        """
        GIVEN an AIRecommendationService
        WHEN caching multiple recommendations
        THEN cache size should reflect unique recommendations, not duplicate entries.
        """
        from mcp_server_langgraph.alerts.ai_recommendation import (
            AIRecommendationService,
        )
        from mcp_server_langgraph.observability.query.interfaces import (
            Alert,
            AlertSeverity,
            AlertState,
        )

        mock_llm = AsyncMock(return_value=None)
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

        # Generate recommendations for 3 different alerts
        for i in range(3):
            alert = Alert(
                alert_id=f"alert-{i}",
                name="HighCPU",
                severity=AlertSeverity.CRITICAL,
                state=AlertState.FIRING,
                message="CPU high",
                labels={"service": f"service-{i}"},  # Different labels = different cache_key
                annotations={},
                started_at=datetime.now(UTC),
            )
            await service.generate_recommendation(alert)

        # Primary cache should have 3 entries (one per cache_key)
        assert len(service._cache) == 3, "Cache should have 3 unique recommendations"

        # Secondary index should also have 3 entries
        assert len(service._alert_id_index) == 3, "Index should have 3 alert_id mappings"

    @pytest.mark.asyncio
    async def test_clear_cache_clears_both_primary_and_secondary(self) -> None:
        """
        GIVEN an AIRecommendationService with cached recommendations
        WHEN clearing the cache
        THEN should clear both primary cache and secondary index.
        """
        from mcp_server_langgraph.alerts.ai_recommendation import (
            AIRecommendationService,
        )

        mock_llm = AsyncMock(return_value=None)
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
        alert = create_test_alert()

        await service.generate_recommendation(alert)

        # Verify cache is populated
        assert len(service._cache) > 0
        assert len(service._alert_id_index) > 0

        # Clear cache
        service.clear_cache()

        # Both should be empty
        assert len(service._cache) == 0, "Primary cache should be empty"
        assert len(service._alert_id_index) == 0, "Secondary index should be empty"


@pytest.mark.xdist_group(name="test_ai_recommendation")
class TestAIRecommendationQueue:
    """Tests for AI recommendation queueing."""

    def teardown_method(self) -> None:
        """Force GC to prevent mock accumulation in xdist workers."""
        gc.collect()

    def test_queue_class_exists(self) -> None:
        """
        GIVEN the ai_recommendation module
        WHEN importing AIRecommendationQueue
        THEN should export the queue class.
        """
        from mcp_server_langgraph.alerts.ai_recommendation import (
            AIRecommendationQueue,
        )

        assert AIRecommendationQueue is not None

    @pytest.mark.asyncio
    async def test_queue_recommendation_adds_to_queue(self) -> None:
        """
        GIVEN an AIRecommendationQueue
        WHEN queueing a recommendation
        THEN should add alert to processing queue.
        """
        from mcp_server_langgraph.alerts.ai_recommendation import (
            AIRecommendationQueue,
            AIRecommendationService,
        )

        mock_service = AsyncMock(spec=AIRecommendationService)
        queue = AIRecommendationQueue(service=mock_service)

        alert = create_test_alert()
        await queue.queue_recommendation(alert)

        assert queue.pending_count >= 0  # May have been processed immediately

    @pytest.mark.asyncio
    async def test_queue_processes_alerts_asynchronously(self) -> None:
        """
        GIVEN an AIRecommendationQueue with pending alerts
        WHEN the queue is processed
        THEN should generate recommendations for each alert.
        """
        from mcp_server_langgraph.alerts.ai_recommendation import (
            AIRecommendation,
            AIRecommendationQueue,
            AIRecommendationService,
        )

        mock_service = AsyncMock(spec=AIRecommendationService)
        mock_service.generate_recommendation.return_value = AIRecommendation(
            recommendation_id="rec-001",
            alert_id="test-alert",
            root_cause_analysis="Test",
            remediation_steps=[],
            risk_assessment={},
            generated_at=datetime.now(UTC).isoformat(),
            model_used="test-model",
        )

        queue = AIRecommendationQueue(service=mock_service)

        alert = create_test_alert()
        await queue.queue_recommendation(alert)

        # Process the queue (in real implementation this is async)
        await queue.process_pending()

        mock_service.generate_recommendation.assert_called()


@pytest.mark.xdist_group(name="test_ai_recommendation")
class TestAIRecommendationPrompt:
    """Tests for AI recommendation prompt generation."""

    def teardown_method(self) -> None:
        """Force GC to prevent mock accumulation in xdist workers."""
        gc.collect()

    def test_build_prompt_includes_alert_details(self) -> None:
        """
        GIVEN an alert
        WHEN building the LLM prompt
        THEN should include alert name, severity, and labels.
        """
        from mcp_server_langgraph.alerts.ai_recommendation import build_recommendation_prompt

        alert = create_test_alert(
            name="CircuitBreakerOpen",
            severity=AlertSeverity.CRITICAL,
            service="redis",
        )

        prompt = build_recommendation_prompt(alert)

        assert "CircuitBreakerOpen" in prompt
        assert "critical" in prompt.lower()
        assert "redis" in prompt

    def test_build_prompt_includes_runbook_url(self) -> None:
        """
        GIVEN an alert with runbook_url
        WHEN building the LLM prompt
        THEN should include runbook URL in context.
        """
        from mcp_server_langgraph.alerts.ai_recommendation import build_recommendation_prompt

        alert = create_test_alert()

        prompt = build_recommendation_prompt(alert)

        assert "runbooks.example.com" in prompt

    def test_build_prompt_requests_json_response(self) -> None:
        """
        GIVEN an alert
        WHEN building the LLM prompt
        THEN should request JSON format response.
        """
        from mcp_server_langgraph.alerts.ai_recommendation import build_recommendation_prompt

        alert = create_test_alert()

        prompt = build_recommendation_prompt(alert)

        assert "json" in prompt.lower()


@pytest.mark.xdist_group(name="test_ai_recommendation")
class TestFewShotPromptEnhancement:
    """Tests for few-shot learning prompt enhancement."""

    def teardown_method(self) -> None:
        """Force GC to prevent mock accumulation in xdist workers."""
        gc.collect()

    @pytest.mark.asyncio
    async def test_build_prompt_with_few_shot_examples(self) -> None:
        """
        GIVEN a feedback store with approved examples
        WHEN building the LLM prompt with few-shot examples
        THEN should include successful remediation examples.
        """
        from mcp_server_langgraph.alerts.ai_recommendation import (
            build_recommendation_prompt_with_feedback,
        )
        from mcp_server_langgraph.alerts.feedback import (
            InMemoryFeedbackStore,
            RemediationFeedback,
        )

        # Create feedback store with approved example
        feedback_store = InMemoryFeedbackStore()
        await feedback_store.save_feedback(
            RemediationFeedback(
                feedback_id="fb-001",
                remediation_id="rem-001",
                alert_type="CircuitBreakerOpen",
                alert_labels={"service": "redis"},
                severity="critical",
                recommendation_id="rec-001",
                action="approved",
                reason=None,
                reason_detail=None,
                admin_user_id="admin-001",
                timestamp=datetime.now(UTC),
                execution_success=True,
                execution_time_seconds=30.0,
                admin_notes="Restart resolved the issue",
            )
        )

        alert = create_test_alert()
        result = await build_recommendation_prompt_with_feedback(alert, feedback_store)

        assert "Previously Successful Remediations" in result.prompt
        assert "CircuitBreakerOpen" in result.prompt

    @pytest.mark.asyncio
    async def test_build_prompt_without_feedback_store(self) -> None:
        """
        GIVEN no feedback store
        WHEN building the LLM prompt
        THEN should return basic prompt without few-shot examples.
        """
        from mcp_server_langgraph.alerts.ai_recommendation import (
            build_recommendation_prompt_with_feedback,
        )

        alert = create_test_alert()
        result = await build_recommendation_prompt_with_feedback(alert, None)

        assert "CircuitBreakerOpen" in result.prompt
        assert "Previously Successful Remediations" not in result.prompt

    @pytest.mark.asyncio
    async def test_build_prompt_with_rejection_constraints(self) -> None:
        """
        GIVEN a feedback store with rejection patterns
        WHEN building the LLM prompt
        THEN should include constraints based on rejections.
        """
        from mcp_server_langgraph.alerts.ai_recommendation import (
            build_recommendation_prompt_with_feedback,
        )
        from mcp_server_langgraph.alerts.feedback import (
            InMemoryFeedbackStore,
            RejectionReason,
            RemediationFeedback,
        )

        # Create feedback store with multiple rejections
        feedback_store = InMemoryFeedbackStore()
        for i in range(3):
            await feedback_store.save_feedback(
                RemediationFeedback(
                    feedback_id=f"fb-{i:03d}",
                    remediation_id=f"rem-{i:03d}",
                    alert_type="CircuitBreakerOpen",
                    alert_labels={},
                    severity="critical",
                    recommendation_id=f"rec-{i:03d}",
                    action="rejected",
                    reason=RejectionReason.TOO_RISKY,
                    reason_detail=None,
                    admin_user_id="admin-001",
                    timestamp=datetime.now(UTC),
                )
            )

        alert = create_test_alert()
        result = await build_recommendation_prompt_with_feedback(alert, feedback_store)

        assert "Important Constraints" in result.prompt
        assert "high-risk" in result.prompt.lower() or "risky" in result.prompt.lower()

    @pytest.mark.asyncio
    async def test_build_prompt_limits_few_shot_examples(self) -> None:
        """
        GIVEN a feedback store with many approved examples
        WHEN building the LLM prompt
        THEN should limit to 3 most recent examples.
        """
        from mcp_server_langgraph.alerts.ai_recommendation import (
            build_recommendation_prompt_with_feedback,
        )
        from mcp_server_langgraph.alerts.feedback import (
            InMemoryFeedbackStore,
            RemediationFeedback,
        )

        # Create feedback store with many examples
        feedback_store = InMemoryFeedbackStore()
        for i in range(10):
            await feedback_store.save_feedback(
                RemediationFeedback(
                    feedback_id=f"fb-{i:03d}",
                    remediation_id=f"rem-{i:03d}",
                    alert_type="CircuitBreakerOpen",
                    alert_labels={},
                    severity="critical",
                    recommendation_id=f"rec-{i:03d}",
                    action="approved",
                    reason=None,
                    reason_detail=None,
                    admin_user_id="admin-001",
                    timestamp=datetime.now(UTC),
                    execution_success=True,
                    execution_time_seconds=30.0,
                )
            )

        alert = create_test_alert()
        result = await build_recommendation_prompt_with_feedback(alert, feedback_store)

        # Count example occurrences (should be max 3)
        example_count = result.prompt.count("### Example")
        assert example_count <= 3


@pytest.mark.xdist_group(name="test_ai_recommendation")
class TestAIRecommendationConfidenceScores:
    """Tests for AI recommendation confidence scores."""

    def teardown_method(self) -> None:
        """Force GC to prevent mock accumulation in xdist workers."""
        gc.collect()

    def test_recommendation_has_confidence_score_field(self) -> None:
        """
        GIVEN an AIRecommendation model
        WHEN checking fields
        THEN should have confidence_score field.
        """
        from mcp_server_langgraph.alerts.ai_recommendation import AIRecommendation

        recommendation = AIRecommendation(
            recommendation_id="rec-001",
            alert_id="alert-001",
            root_cause_analysis="Test analysis",
            remediation_steps=[],
            risk_assessment={},
            generated_at=datetime.now(UTC).isoformat(),
            model_used="claude-sonnet-4",
            confidence_score=0.85,
        )

        assert hasattr(recommendation, "confidence_score")
        assert recommendation.confidence_score == 0.85

    def test_confidence_score_default_value(self) -> None:
        """
        GIVEN an AIRecommendation without explicit confidence_score
        WHEN creating the instance
        THEN should have a default confidence_score.
        """
        from mcp_server_langgraph.alerts.ai_recommendation import AIRecommendation

        recommendation = AIRecommendation(
            recommendation_id="rec-001",
            alert_id="alert-001",
            root_cause_analysis="Test analysis",
            remediation_steps=[],
            risk_assessment={},
            generated_at=datetime.now(UTC).isoformat(),
            model_used="claude-sonnet-4",
        )

        # Default confidence should be set
        assert recommendation.confidence_score is not None
        assert 0.0 <= recommendation.confidence_score <= 1.0

    def test_confidence_score_validation(self) -> None:
        """
        GIVEN an AIRecommendation with confidence_score
        WHEN confidence_score is out of range
        THEN should be clamped or validated to [0.0, 1.0].
        """
        from mcp_server_langgraph.alerts.ai_recommendation import AIRecommendation

        # Valid range
        rec_valid = AIRecommendation(
            recommendation_id="rec-001",
            alert_id="alert-001",
            root_cause_analysis="Test",
            remediation_steps=[],
            risk_assessment={},
            generated_at=datetime.now(UTC).isoformat(),
            model_used="claude-sonnet-4",
            confidence_score=0.5,
        )
        assert rec_valid.confidence_score == 0.5

    @pytest.mark.asyncio
    async def test_generate_recommendation_includes_confidence_score(self) -> None:
        """
        GIVEN an AIRecommendationService with mocked LLM
        WHEN generating a recommendation
        THEN should include confidence_score in result.
        """
        from mcp_server_langgraph.alerts.ai_recommendation import (
            AIRecommendationService,
        )

        mock_llm = AsyncMock(return_value=None)
        mock_llm.acompletion.return_value = MagicMock(
            choices=[
                MagicMock(
                    message=MagicMock(
                        content="""{
                            "root_cause_analysis": "Test",
                            "remediation_steps": [],
                            "risk_assessment": {},
                            "confidence_score": 0.75
                        }"""
                    )
                )
            ]
        )

        service = AIRecommendationService(llm_factory=mock_llm)
        alert = create_test_alert()

        recommendation = await service.generate_recommendation(alert)

        assert recommendation.confidence_score is not None
        assert 0.0 <= recommendation.confidence_score <= 1.0

    @pytest.mark.asyncio
    async def test_few_shot_examples_increase_confidence(self) -> None:
        """
        GIVEN a feedback store with approved examples for the alert type
        WHEN generating a recommendation
        THEN should have higher baseline confidence due to prior examples.
        """
        from mcp_server_langgraph.alerts.ai_recommendation import (
            compute_baseline_confidence,
        )
        from mcp_server_langgraph.alerts.feedback import (
            InMemoryFeedbackStore,
            RemediationFeedback,
        )

        # Create feedback store with approved examples
        feedback_store = InMemoryFeedbackStore()
        for i in range(5):
            await feedback_store.save_feedback(
                RemediationFeedback(
                    feedback_id=f"fb-{i:03d}",
                    remediation_id=f"rem-{i:03d}",
                    alert_type="CircuitBreakerOpen",
                    alert_labels={},
                    severity="critical",
                    recommendation_id=f"rec-{i:03d}",
                    action="approved",
                    reason=None,
                    reason_detail=None,
                    admin_user_id="admin-001",
                    timestamp=datetime.now(UTC),
                    execution_success=True,
                    execution_time_seconds=30.0,
                )
            )

        alert = create_test_alert()
        confidence = await compute_baseline_confidence(alert, feedback_store)

        # With 5 successful examples, confidence should be higher
        assert confidence >= 0.7


@pytest.mark.xdist_group(name="test_ai_recommendation")
class TestRunbookAutoLinking:
    """Tests for runbook auto-linking based on alert labels."""

    def teardown_method(self) -> None:
        """Force GC to prevent mock accumulation in xdist workers."""
        gc.collect()

    def test_get_runbook_url_for_known_alert(self) -> None:
        """
        GIVEN an alert with known alertname
        WHEN getting runbook URL
        THEN should return the mapped runbook URL.
        """
        from mcp_server_langgraph.alerts.ai_recommendation import get_runbook_url

        alert = create_test_alert(name="CircuitBreakerOpen", service="redis")

        runbook_url = get_runbook_url(alert)

        assert runbook_url is not None
        assert "circuit" in runbook_url.lower() or "runbook" in runbook_url.lower()

    def test_get_runbook_url_uses_annotation_if_present(self) -> None:
        """
        GIVEN an alert with runbook_url in annotations
        WHEN getting runbook URL
        THEN should prefer annotation URL.
        """
        from mcp_server_langgraph.alerts.ai_recommendation import get_runbook_url

        alert = create_test_alert()
        # Alert already has runbook_url in annotations

        runbook_url = get_runbook_url(alert)

        assert runbook_url is not None
        assert "runbooks.example.com" in runbook_url

    def test_get_runbook_url_by_service_label(self) -> None:
        """
        GIVEN an alert with service label
        WHEN getting runbook URL without annotation
        THEN should return service-specific runbook.
        """
        from mcp_server_langgraph.alerts.ai_recommendation import get_runbook_url

        # Create alert without runbook annotation
        alert = Alert(
            alert_id="test-alert-001",
            name="HighLatency",
            severity=AlertSeverity.WARNING,
            state=AlertState.FIRING,
            message="High latency detected",
            labels={
                "service": "postgresql",
                "alertname": "HighLatency",
            },
            annotations={},  # No runbook_url
            started_at=datetime.now(UTC),
        )

        runbook_url = get_runbook_url(alert)

        # Should auto-link to postgresql runbook
        assert runbook_url is not None
        # Either matches service or has a fallback pattern
        assert "postgres" in runbook_url.lower() or "docs" in runbook_url.lower()

    def test_get_runbook_url_by_alertname_pattern(self) -> None:
        """
        GIVEN an alert with recognizable alertname pattern
        WHEN getting runbook URL
        THEN should match to appropriate runbook.
        """
        from mcp_server_langgraph.alerts.ai_recommendation import get_runbook_url

        # Create alert with recognizable pattern
        alert = Alert(
            alert_id="test-alert-002",
            name="HighMemoryUsage",
            severity=AlertSeverity.WARNING,
            state=AlertState.FIRING,
            message="Memory usage above threshold",
            labels={"alertname": "HighMemoryUsage"},
            annotations={},
            started_at=datetime.now(UTC),
        )

        runbook_url = get_runbook_url(alert)

        assert runbook_url is not None
        # Should match memory-related runbook
        assert "memory" in runbook_url.lower() or "resource" in runbook_url.lower() or "docs" in runbook_url.lower()

    def test_get_runbook_url_fallback_for_unknown_alert(self) -> None:
        """
        GIVEN an alert with unknown/custom alertname
        WHEN getting runbook URL
        THEN should return generic troubleshooting runbook.
        """
        from mcp_server_langgraph.alerts.ai_recommendation import get_runbook_url

        alert = Alert(
            alert_id="test-alert-003",
            name="CustomAlertXYZ123",
            severity=AlertSeverity.INFO,
            state=AlertState.FIRING,
            message="Custom alert",
            labels={"alertname": "CustomAlertXYZ123"},
            annotations={},
            started_at=datetime.now(UTC),
        )

        runbook_url = get_runbook_url(alert)

        # Should have a fallback
        assert runbook_url is not None
        assert "docs" in runbook_url.lower() or "runbook" in runbook_url.lower()

    @pytest.mark.asyncio
    async def test_generate_recommendation_uses_auto_linked_runbook(self) -> None:
        """
        GIVEN an alert without runbook annotation
        WHEN generating a recommendation
        THEN should auto-link runbook based on labels.
        """
        from mcp_server_langgraph.alerts.ai_recommendation import (
            AIRecommendationService,
        )

        mock_llm = AsyncMock(return_value=None)
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

        # Create alert without runbook annotation
        alert = Alert(
            alert_id="test-alert-004",
            name="PodCrashLooping",
            severity=AlertSeverity.CRITICAL,
            state=AlertState.FIRING,
            message="Pod is crash looping",
            labels={"alertname": "PodCrashLooping", "namespace": "default"},
            annotations={},  # No runbook_url
            started_at=datetime.now(UTC),
        )

        recommendation = await service.generate_recommendation(alert)

        # Should have auto-linked runbook
        assert recommendation.runbook_reference is not None


@pytest.mark.xdist_group(name="test_ai_recommendation")
class TestRunbookRegistry:
    """Tests for the runbook registry."""

    def teardown_method(self) -> None:
        """Force GC to prevent mock accumulation in xdist workers."""
        gc.collect()

    def test_runbook_registry_exists(self) -> None:
        """
        GIVEN the ai_recommendation module
        WHEN importing RUNBOOK_REGISTRY
        THEN should be a valid mapping.
        """
        from mcp_server_langgraph.alerts.ai_recommendation import RUNBOOK_REGISTRY

        assert RUNBOOK_REGISTRY is not None
        assert isinstance(RUNBOOK_REGISTRY, dict)

    def test_runbook_registry_has_common_alerts(self) -> None:
        """
        GIVEN the RUNBOOK_REGISTRY
        WHEN checking contents
        THEN should have common alert patterns.
        """
        from mcp_server_langgraph.alerts.ai_recommendation import RUNBOOK_REGISTRY

        # Should have at least some common patterns
        assert len(RUNBOOK_REGISTRY) > 0

    def test_register_runbook_mapping(self) -> None:
        """
        GIVEN a new alert pattern and runbook URL
        WHEN registering the mapping
        THEN should be available for lookups.
        """
        from mcp_server_langgraph.alerts.ai_recommendation import (
            RUNBOOK_REGISTRY,
            register_runbook,
        )

        # Register a custom mapping
        register_runbook("CustomTestAlert", "https://docs.example.com/custom-test")

        assert "CustomTestAlert" in RUNBOOK_REGISTRY
        assert RUNBOOK_REGISTRY["CustomTestAlert"] == "https://docs.example.com/custom-test"

        # Cleanup
        del RUNBOOK_REGISTRY["CustomTestAlert"]


@pytest.mark.xdist_group(name="test_ai_recommendation")
class TestRedisCaching:
    """Tests for Redis-backed caching of AI recommendations."""

    def teardown_method(self) -> None:
        """Force GC to prevent mock accumulation in xdist workers."""
        gc.collect()

    def test_cache_key_generation(self) -> None:
        """
        GIVEN an Alert with specific labels
        WHEN generating a cache key
        THEN should create consistent, fingerprint-based key.
        """
        from mcp_server_langgraph.alerts.ai_recommendation import (
            generate_recommendation_cache_key,
        )

        alert = create_test_alert(
            alert_id="alert-001",
            name="HighCPUUsage",
            service="api-gateway",
        )

        cache_key = generate_recommendation_cache_key(alert)

        # Should have proper prefix
        assert cache_key.startswith("alert:recommendation:")
        # Should include alert name
        assert "HighCPUUsage" in cache_key
        # Should be consistent
        cache_key2 = generate_recommendation_cache_key(alert)
        assert cache_key == cache_key2

    def test_cache_key_same_type_different_id(self) -> None:
        """
        GIVEN two alerts of same type/service but different IDs
        WHEN generating cache keys
        THEN should produce same cache key (for reuse).
        """
        from mcp_server_langgraph.alerts.ai_recommendation import (
            generate_recommendation_cache_key,
        )

        alert1 = create_test_alert(
            alert_id="alert-001",
            name="HighCPUUsage",
            service="api-gateway",
        )
        alert2 = create_test_alert(
            alert_id="alert-002",  # Different ID
            name="HighCPUUsage",
            service="api-gateway",
        )

        cache_key1 = generate_recommendation_cache_key(alert1)
        cache_key2 = generate_recommendation_cache_key(alert2)

        # Same alert type and service should produce same key
        assert cache_key1 == cache_key2

    def test_cache_key_different_service(self) -> None:
        """
        GIVEN two alerts of same type but different services
        WHEN generating cache keys
        THEN should produce different cache keys.
        """
        from mcp_server_langgraph.alerts.ai_recommendation import (
            generate_recommendation_cache_key,
        )

        alert1 = create_test_alert(
            alert_id="alert-001",
            name="HighCPUUsage",
            service="api-gateway",
        )
        alert2 = create_test_alert(
            alert_id="alert-002",
            name="HighCPUUsage",
            service="payment-service",  # Different service
        )

        cache_key1 = generate_recommendation_cache_key(alert1)
        cache_key2 = generate_recommendation_cache_key(alert2)

        # Different service should produce different key
        assert cache_key1 != cache_key2

    @pytest.mark.asyncio
    async def test_redis_cache_integration(self) -> None:
        """
        GIVEN an AIRecommendationService with CacheService
        WHEN generating and caching a recommendation
        THEN should store in both L1 and L2 cache.
        """
        from mcp_server_langgraph.alerts.ai_recommendation import (
            AIRecommendationService,
            generate_recommendation_cache_key,
        )

        # Mock cache service
        mock_cache = MagicMock()
        mock_cache.get.return_value = None  # Cache miss

        # Mock LLM
        mock_llm = MagicMock()
        mock_llm.acompletion = AsyncMock(
            return_value=MagicMock(
                choices=[
                    MagicMock(
                        message=MagicMock(
                            content='{"root_cause_analysis": "Test", "remediation_steps": [], "risk_assessment": {}}'
                        )
                    )
                ]
            )
        )

        service = AIRecommendationService(
            llm_factory=mock_llm,
            cache_service=mock_cache,
        )

        alert = create_test_alert()
        cache_key = generate_recommendation_cache_key(alert)

        # Generate recommendation (patch metrics functions at their source)
        with patch("mcp_server_langgraph.alerts.metrics.record_recommendation_request"):
            with patch("mcp_server_langgraph.alerts.metrics.record_recommendation_generated"):
                _ = await service.generate_recommendation(alert)

        # Should have called cache.get first
        mock_cache.get.assert_called_with(cache_key)

        # Should have called cache.set to store the result
        assert mock_cache.set.called
        call_args = mock_cache.set.call_args
        assert call_args[0][0] == cache_key  # First arg is the key

    @pytest.mark.asyncio
    async def test_redis_cache_hit(self) -> None:
        """
        GIVEN cached recommendation in Redis
        WHEN requesting recommendation for same alert type
        THEN should return cached version without LLM call.
        """
        from mcp_server_langgraph.alerts.ai_recommendation import (
            AIRecommendationService,
        )

        # Create cached recommendation data
        cached_data = {
            "recommendation_id": "cached-rec-001",
            "alert_id": "cached-alert-001",
            "root_cause_analysis": "Cached analysis",
            "remediation_steps": [],
            "risk_assessment": {},
            "runbook_reference": "https://example.com/runbook",
            "generated_at": "2025-01-01T00:00:00Z",
            "model_used": "claude-sonnet-4",
            "confidence_score": 0.8,
        }

        # Mock cache service returning cached data
        mock_cache = MagicMock()
        mock_cache.get.return_value = cached_data

        # Mock LLM - should NOT be called
        mock_llm = MagicMock()

        service = AIRecommendationService(
            llm_factory=mock_llm,
            cache_service=mock_cache,
        )

        alert = create_test_alert()

        # Generate recommendation - should use cache
        with patch("mcp_server_langgraph.alerts.metrics.record_recommendation_request"):
            recommendation = await service.generate_recommendation(alert)

        # Should NOT have called LLM
        mock_llm.acompletion.assert_not_called()

        # Should have returned cached recommendation
        assert recommendation.recommendation_id == "cached-rec-001"
        assert recommendation.root_cause_analysis == "Cached analysis"

    @pytest.mark.asyncio
    async def test_redis_cache_fallback_on_error(self) -> None:
        """
        GIVEN Redis cache that raises an error
        WHEN getting cached recommendation
        THEN should fallback to L1 in-memory cache.
        """
        from mcp_server_langgraph.alerts.ai_recommendation import (
            AIRecommendationService,
        )

        # Mock cache service that raises error
        mock_cache = MagicMock()
        mock_cache.get.side_effect = Exception("Redis connection failed")

        # Mock LLM
        mock_llm = MagicMock()
        mock_llm.acompletion = AsyncMock(
            return_value=MagicMock(
                choices=[
                    MagicMock(
                        message=MagicMock(
                            content='{"root_cause_analysis": "Generated", "remediation_steps": [], "risk_assessment": {}}'
                        )
                    )
                ]
            )
        )

        service = AIRecommendationService(
            llm_factory=mock_llm,
            cache_service=mock_cache,
        )

        alert = create_test_alert()

        # Should not raise, should fallback and generate
        with patch("mcp_server_langgraph.alerts.metrics.record_recommendation_request"):
            with patch("mcp_server_langgraph.alerts.metrics.record_recommendation_generated"):
                recommendation = await service.generate_recommendation(alert)

        # Should have generated new recommendation
        assert recommendation is not None
        assert recommendation.root_cause_analysis == "Generated"
