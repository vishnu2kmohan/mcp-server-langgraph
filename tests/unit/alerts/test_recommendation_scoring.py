"""
Recommendation Quality Scoring Tests.

TDD tests for AI remediation recommendation quality scoring.

Features:
- Score recommendations based on historical feedback
- Track approval/rejection patterns
- Calculate confidence scores
- Provide quality metrics for recommendations

Reference: ADR-0026 - Comprehensive Client Resilience Patterns
"""

from __future__ import annotations

import gc
from unittest.mock import AsyncMock

import pytest

pytestmark = pytest.mark.unit


@pytest.mark.unit
@pytest.mark.xdist_group(name="recommendation_scoring")
class TestRecommendationScorer:
    """Tests for recommendation scoring service."""

    def teardown_method(self) -> None:
        """Force GC to prevent memory accumulation."""
        gc.collect()

    def test_calculate_base_score_for_new_alert_type(self) -> None:
        """Test base score calculation for alert types with no history."""
        from mcp_server_langgraph.alerts.recommendation_scoring import (
            RecommendationScorer,
        )

        scorer = RecommendationScorer()
        score = scorer.calculate_base_score(alert_type="NewAlertType")

        # New alert types should get a neutral base score
        assert score == 0.5
        assert 0.0 <= score <= 1.0

    def test_calculate_base_score_with_approval_history(self) -> None:
        """Test base score increases with approval history."""
        from mcp_server_langgraph.alerts.recommendation_scoring import (
            RecommendationScorer,
            ScoringHistory,
        )

        history = ScoringHistory(
            alert_type="KnownAlert",
            total_recommendations=10,
            approved_count=8,
            rejected_count=2,
            avg_execution_time_seconds=45.0,
            success_rate=0.9,
        )

        scorer = RecommendationScorer()
        score = scorer.calculate_base_score(
            alert_type="KnownAlert",
            history=history,
        )

        # High approval rate should give higher score
        assert score > 0.5
        assert score >= 0.7  # Expected range for 80% approval

    def test_calculate_base_score_with_rejection_history(self) -> None:
        """Test base score decreases with rejection history."""
        from mcp_server_langgraph.alerts.recommendation_scoring import (
            RecommendationScorer,
            ScoringHistory,
        )

        history = ScoringHistory(
            alert_type="ProblematicAlert",
            total_recommendations=10,
            approved_count=2,
            rejected_count=8,
            avg_execution_time_seconds=120.0,
            success_rate=0.3,
        )

        scorer = RecommendationScorer()
        score = scorer.calculate_base_score(
            alert_type="ProblematicAlert",
            history=history,
        )

        # High rejection rate should give lower score
        assert score < 0.5
        assert score <= 0.4  # Expected range for 80% rejection


@pytest.mark.unit
@pytest.mark.xdist_group(name="recommendation_scoring")
class TestConfidenceScore:
    """Tests for recommendation confidence scoring."""

    def teardown_method(self) -> None:
        """Force GC to prevent memory accumulation."""
        gc.collect()

    def test_confidence_score_high_for_matching_patterns(self) -> None:
        """Test high confidence for alerts matching successful patterns."""
        from mcp_server_langgraph.alerts.recommendation_scoring import (
            RecommendationScorer,
            ScoringHistory,
        )

        history = ScoringHistory(
            alert_type="HighCPU",
            total_recommendations=50,
            approved_count=45,
            rejected_count=5,
            avg_execution_time_seconds=30.0,
            success_rate=0.95,
        )

        scorer = RecommendationScorer()
        confidence = scorer.calculate_confidence(
            alert_type="HighCPU",
            history=history,
        )

        # High success rate with many samples = high confidence
        assert confidence >= 0.8
        assert confidence <= 1.0

    def test_confidence_score_low_for_few_samples(self) -> None:
        """Test low confidence when few historical samples."""
        from mcp_server_langgraph.alerts.recommendation_scoring import (
            RecommendationScorer,
            ScoringHistory,
        )

        history = ScoringHistory(
            alert_type="RareAlert",
            total_recommendations=3,
            approved_count=2,
            rejected_count=1,
            avg_execution_time_seconds=60.0,
            success_rate=0.67,
        )

        scorer = RecommendationScorer()
        confidence = scorer.calculate_confidence(
            alert_type="RareAlert",
            history=history,
        )

        # Few samples = low confidence, even with decent success
        assert confidence < 0.6
        assert confidence >= 0.0

    def test_confidence_score_for_new_alert_type(self) -> None:
        """Test confidence is minimal for unknown alert types."""
        from mcp_server_langgraph.alerts.recommendation_scoring import (
            RecommendationScorer,
        )

        scorer = RecommendationScorer()
        confidence = scorer.calculate_confidence(alert_type="BrandNewAlert")

        # No history = very low confidence
        assert confidence <= 0.3
        assert confidence >= 0.0


@pytest.mark.unit
@pytest.mark.xdist_group(name="recommendation_scoring")
class TestQualityMetrics:
    """Tests for recommendation quality metrics."""

    def teardown_method(self) -> None:
        """Force GC to prevent memory accumulation."""
        gc.collect()

    def test_calculate_quality_score_composite(self) -> None:
        """Test composite quality score calculation."""
        from mcp_server_langgraph.alerts.recommendation_scoring import (
            RecommendationScorer,
            QualityScore,
            ScoringHistory,
        )

        history = ScoringHistory(
            alert_type="MemoryPressure",
            total_recommendations=25,
            approved_count=20,
            rejected_count=5,
            avg_execution_time_seconds=45.0,
            success_rate=0.85,
        )

        scorer = RecommendationScorer()
        quality = scorer.calculate_quality_score(
            alert_type="MemoryPressure",
            history=history,
        )

        assert isinstance(quality, QualityScore)
        assert 0.0 <= quality.overall_score <= 1.0
        assert 0.0 <= quality.confidence <= 1.0
        assert 0.0 <= quality.approval_rate <= 1.0
        assert quality.sample_count == 25

    def test_quality_score_components(self) -> None:
        """Test quality score includes all components."""
        from mcp_server_langgraph.alerts.recommendation_scoring import (
            RecommendationScorer,
            ScoringHistory,
        )

        history = ScoringHistory(
            alert_type="DiskFull",
            total_recommendations=100,
            approved_count=90,
            rejected_count=10,
            avg_execution_time_seconds=60.0,
            success_rate=0.92,
        )

        scorer = RecommendationScorer()
        quality = scorer.calculate_quality_score(
            alert_type="DiskFull",
            history=history,
        )

        # Check all components are present
        assert quality.overall_score is not None
        assert quality.confidence is not None
        assert quality.approval_rate == 0.9  # 90/100
        assert quality.success_rate == 0.92
        assert quality.avg_execution_time == 60.0
        assert quality.sample_count == 100


@pytest.mark.unit
@pytest.mark.xdist_group(name="recommendation_scoring")
class TestRejectionPatternAnalysis:
    """Tests for rejection pattern analysis."""

    def teardown_method(self) -> None:
        """Force GC to prevent memory accumulation."""
        gc.collect()

    def test_identify_common_rejection_reasons(self) -> None:
        """Test identifying common rejection reasons."""
        from mcp_server_langgraph.alerts.recommendation_scoring import (
            RecommendationScorer,
            RejectionPattern,
        )

        rejection_patterns = [
            RejectionPattern(reason="too_risky", count=15),
            RejectionPattern(reason="incorrect_diagnosis", count=8),
            RejectionPattern(reason="wrong_command", count=5),
        ]

        scorer = RecommendationScorer()
        top_reasons = scorer.get_top_rejection_reasons(
            patterns=rejection_patterns,
            limit=2,
        )

        assert len(top_reasons) == 2
        assert top_reasons[0].reason == "too_risky"
        assert top_reasons[0].count == 15
        assert top_reasons[1].reason == "incorrect_diagnosis"

    def test_generate_improvement_suggestions(self) -> None:
        """Test generating improvement suggestions from patterns."""
        from mcp_server_langgraph.alerts.recommendation_scoring import (
            RecommendationScorer,
            RejectionPattern,
        )

        rejection_patterns = [
            RejectionPattern(reason="too_risky", count=20),
            RejectionPattern(reason="incomplete_steps", count=10),
        ]

        scorer = RecommendationScorer()
        suggestions = scorer.generate_improvement_suggestions(
            patterns=rejection_patterns,
        )

        assert len(suggestions) >= 1
        assert isinstance(suggestions[0], str)
        # Suggestions should mention the rejection reason
        assert any("risk" in s.lower() for s in suggestions)


@pytest.mark.unit
@pytest.mark.xdist_group(name="recommendation_scoring")
class TestScoringHistoryRepository:
    """Tests for scoring history persistence."""

    def teardown_method(self) -> None:
        """Force GC to prevent memory accumulation."""
        gc.collect()

    @pytest.mark.asyncio
    async def test_save_feedback_updates_history(self) -> None:
        """Test that saving feedback updates scoring history."""
        from mcp_server_langgraph.alerts.recommendation_scoring import (
            ScoringHistoryRepository,
            FeedbackData,
        )

        mock_store = AsyncMock()
        mock_store.get_history = AsyncMock(return_value=None)
        mock_store.save_history = AsyncMock()

        repo = ScoringHistoryRepository(store=mock_store)

        feedback = FeedbackData(
            alert_type="TestAlert",
            action="approved",
            execution_success=True,
            execution_time_seconds=30.0,
        )

        await repo.record_feedback(feedback)

        mock_store.save_history.assert_called_once()

    @pytest.mark.asyncio
    async def test_get_history_returns_cached(self) -> None:
        """Test that get_history returns cached results."""
        from mcp_server_langgraph.alerts.recommendation_scoring import (
            ScoringHistoryRepository,
            ScoringHistory,
        )

        mock_store = AsyncMock()
        expected_history = ScoringHistory(
            alert_type="CachedAlert",
            total_recommendations=50,
            approved_count=40,
            rejected_count=10,
            avg_execution_time_seconds=45.0,
            success_rate=0.85,
        )
        mock_store.get_history = AsyncMock(return_value=expected_history)

        repo = ScoringHistoryRepository(store=mock_store)
        history = await repo.get_history("CachedAlert")

        assert history == expected_history
        mock_store.get_history.assert_called_once_with("CachedAlert")

    @pytest.mark.asyncio
    async def test_get_all_histories_returns_list(self) -> None:
        """Test getting all scoring histories."""
        from mcp_server_langgraph.alerts.recommendation_scoring import (
            ScoringHistoryRepository,
            ScoringHistory,
        )

        mock_store = AsyncMock()
        histories = [
            ScoringHistory(
                alert_type=f"Alert{i}",
                total_recommendations=i * 10,
                approved_count=i * 8,
                rejected_count=i * 2,
                avg_execution_time_seconds=30.0 + i,
                success_rate=0.8,
            )
            for i in range(1, 4)
        ]
        mock_store.list_all = AsyncMock(return_value=histories)

        repo = ScoringHistoryRepository(store=mock_store)
        all_histories = await repo.get_all_histories()

        assert len(all_histories) == 3
        mock_store.list_all.assert_called_once()


@pytest.mark.unit
@pytest.mark.xdist_group(name="recommendation_scoring")
class TestScoringModels:
    """Tests for scoring data models."""

    def teardown_method(self) -> None:
        """Force GC to prevent memory accumulation."""
        gc.collect()

    def test_scoring_history_to_dict(self) -> None:
        """Test ScoringHistory serialization."""
        from mcp_server_langgraph.alerts.recommendation_scoring import (
            ScoringHistory,
        )

        history = ScoringHistory(
            alert_type="TestAlert",
            total_recommendations=100,
            approved_count=85,
            rejected_count=15,
            avg_execution_time_seconds=45.0,
            success_rate=0.9,
        )

        data = history.to_dict()

        assert data["alert_type"] == "TestAlert"
        assert data["total_recommendations"] == 100
        assert data["approved_count"] == 85
        assert data["rejected_count"] == 15
        assert data["avg_execution_time_seconds"] == 45.0
        assert data["success_rate"] == 0.9

    def test_scoring_history_from_dict(self) -> None:
        """Test ScoringHistory deserialization."""
        from mcp_server_langgraph.alerts.recommendation_scoring import (
            ScoringHistory,
        )

        data = {
            "alert_type": "LoadedAlert",
            "total_recommendations": 50,
            "approved_count": 40,
            "rejected_count": 10,
            "avg_execution_time_seconds": 30.0,
            "success_rate": 0.85,
        }

        history = ScoringHistory.from_dict(data)

        assert history.alert_type == "LoadedAlert"
        assert history.total_recommendations == 50
        assert history.approved_count == 40

    def test_quality_score_model(self) -> None:
        """Test QualityScore model."""
        from mcp_server_langgraph.alerts.recommendation_scoring import (
            QualityScore,
        )

        score = QualityScore(
            overall_score=0.85,
            confidence=0.9,
            approval_rate=0.8,
            success_rate=0.95,
            avg_execution_time=45.0,
            sample_count=100,
        )

        assert score.overall_score == 0.85
        assert score.confidence == 0.9
        assert score.approval_rate == 0.8
        assert score.success_rate == 0.95
        assert score.avg_execution_time == 45.0
        assert score.sample_count == 100

    def test_rejection_pattern_model(self) -> None:
        """Test RejectionPattern model."""
        from mcp_server_langgraph.alerts.recommendation_scoring import (
            RejectionPattern,
        )

        pattern = RejectionPattern(
            reason="too_risky",
            count=25,
            percentage=0.5,
        )

        assert pattern.reason == "too_risky"
        assert pattern.count == 25
        assert pattern.percentage == 0.5
