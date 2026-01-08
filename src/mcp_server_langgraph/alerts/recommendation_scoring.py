"""
Recommendation Quality Scoring.

Service for scoring AI remediation recommendations based on historical
feedback and patterns.

Features:
- Score recommendations based on historical feedback
- Track approval/rejection patterns
- Calculate confidence scores
- Provide quality metrics for recommendations

Reference: ADR-0026 - Comprehensive Client Resilience Patterns
"""

from __future__ import annotations

import logging
import math
from dataclasses import dataclass
from typing import TYPE_CHECKING, Any, Protocol

from mcp_server_langgraph.core.numeric import safe_divide, safe_float

if TYPE_CHECKING:
    pass

logger = logging.getLogger(__name__)


# =============================================================================
# Data Models
# =============================================================================


@dataclass
class ScoringHistory:
    """
    Historical scoring data for an alert type.

    Attributes:
        alert_type: The type of alert this history applies to.
        total_recommendations: Total number of recommendations made.
        approved_count: Number of approved recommendations.
        rejected_count: Number of rejected recommendations.
        avg_execution_time_seconds: Average execution time for approved.
        success_rate: Rate of successful executions.
    """

    alert_type: str
    total_recommendations: int
    approved_count: int
    rejected_count: int
    avg_execution_time_seconds: float
    success_rate: float

    def to_dict(self) -> dict[str, Any]:
        """Serialize to dictionary."""
        return {
            "alert_type": self.alert_type,
            "total_recommendations": self.total_recommendations,
            "approved_count": self.approved_count,
            "rejected_count": self.rejected_count,
            "avg_execution_time_seconds": self.avg_execution_time_seconds,
            "success_rate": self.success_rate,
        }

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> ScoringHistory:
        """Deserialize from dictionary."""
        return cls(
            alert_type=data["alert_type"],
            total_recommendations=data["total_recommendations"],
            approved_count=data["approved_count"],
            rejected_count=data["rejected_count"],
            avg_execution_time_seconds=data["avg_execution_time_seconds"],
            success_rate=data["success_rate"],
        )


@dataclass
class QualityScore:
    """
    Composite quality score for recommendations.

    Attributes:
        overall_score: Combined quality score (0-1).
        confidence: Confidence in the score based on sample size.
        approval_rate: Historical approval rate.
        success_rate: Rate of successful executions.
        avg_execution_time: Average execution time in seconds.
        sample_count: Number of samples used for scoring.
    """

    overall_score: float
    confidence: float
    approval_rate: float
    success_rate: float
    avg_execution_time: float
    sample_count: int


@dataclass
class RejectionPattern:
    """
    Pattern of rejection reasons.

    Attributes:
        reason: The rejection reason code.
        count: Number of rejections with this reason.
        percentage: Percentage of total rejections (optional).
    """

    reason: str
    count: int
    percentage: float = 0.0


@dataclass
class FeedbackData:
    """
    Feedback data for a recommendation.

    Attributes:
        alert_type: Type of alert.
        action: Action taken (approved/rejected).
        execution_success: Whether execution succeeded (if approved).
        execution_time_seconds: Execution time (if approved).
        rejection_reason: Reason for rejection (if rejected).
    """

    alert_type: str
    action: str  # "approved" or "rejected"
    execution_success: bool | None = None
    execution_time_seconds: float | None = None
    rejection_reason: str | None = None


# =============================================================================
# Storage Protocol
# =============================================================================


class ScoringHistoryStore(Protocol):
    """Protocol for scoring history storage backends."""

    async def get_history(self, alert_type: str) -> ScoringHistory | None:
        """Get history for an alert type."""
        ...

    async def save_history(self, history: ScoringHistory) -> None:
        """Save history for an alert type."""
        ...

    async def list_all(self) -> list[ScoringHistory]:
        """List all histories."""
        ...


# =============================================================================
# Recommendation Scorer
# =============================================================================


class RecommendationScorer:
    """
    Service for scoring recommendation quality.

    Calculates quality scores based on historical feedback data.
    """

    # Minimum samples for confident scoring
    MIN_SAMPLES_FOR_CONFIDENCE = 10

    # Weight factors for scoring
    APPROVAL_WEIGHT = 0.4
    SUCCESS_WEIGHT = 0.4
    EXECUTION_TIME_WEIGHT = 0.2

    # Improvement suggestions by rejection reason
    IMPROVEMENT_SUGGESTIONS = {
        "too_risky": "Consider recommending lower-risk diagnostic steps before remediation actions.",
        "incorrect_diagnosis": "Improve root cause analysis by considering more context and patterns.",
        "wrong_command": "Double-check command syntax and ensure paths are correct for the environment.",
        "incomplete_steps": "Provide more comprehensive step-by-step instructions.",
        "not_relevant": "Better match recommendations to the specific alert context.",
        "prefer_manual": "Flag complex scenarios for manual intervention early.",
    }

    def calculate_base_score(
        self,
        alert_type: str,
        history: ScoringHistory | None = None,
    ) -> float:
        """
        Calculate base quality score for an alert type.

        Args:
            alert_type: The alert type to score.
            history: Historical data (if available).

        Returns:
            Base score between 0.0 and 1.0.
        """
        if history is None or history.total_recommendations == 0:
            # No history - neutral score
            return 0.5

        # Calculate approval rate using safe_divide for robustness
        approval_rate = safe_divide(
            float(history.approved_count),
            float(history.total_recommendations),
            default=0.5,
        )

        # Weight the score - use safe_float in case success_rate is NaN
        success_rate = safe_float(history.success_rate, default=0.0)
        weighted_score = approval_rate * self.APPROVAL_WEIGHT + success_rate * self.SUCCESS_WEIGHT

        # Normalize to 0-1 range
        # Max weighted score would be 0.8 (0.4 + 0.4), so normalize
        normalized_score = weighted_score / (self.APPROVAL_WEIGHT + self.SUCCESS_WEIGHT)

        return min(1.0, max(0.0, normalized_score))

    def calculate_confidence(
        self,
        alert_type: str,
        history: ScoringHistory | None = None,
    ) -> float:
        """
        Calculate confidence score based on sample size and success rate.

        Args:
            alert_type: The alert type.
            history: Historical data (if available).

        Returns:
            Confidence score between 0.0 and 1.0.
        """
        if history is None or history.total_recommendations == 0:
            # No history - minimal confidence
            return 0.1

        sample_count = history.total_recommendations

        # Calculate sample-based confidence
        # Uses a sigmoid-like function that approaches 1.0 asymptotically
        # At 10 samples = 0.5, 30 samples = 0.75, 50 samples = 0.83, 100 samples = 0.91
        sample_confidence = 1 - math.exp(-sample_count / 28)

        # Factor in the success rate for extra confidence boost
        # High success rate with high sample count = high confidence
        success_factor = history.success_rate

        # Combine: sample confidence weighted by success rate
        # At 50 samples with 95% success = ~0.85 confidence
        confidence = sample_confidence * (0.68 + 0.32 * success_factor)

        return min(1.0, max(0.0, confidence))

    def calculate_quality_score(
        self,
        alert_type: str,
        history: ScoringHistory | None = None,
    ) -> QualityScore:
        """
        Calculate comprehensive quality score.

        Args:
            alert_type: The alert type.
            history: Historical data (if available).

        Returns:
            QualityScore with all components.
        """
        if history is None:
            return QualityScore(
                overall_score=0.5,
                confidence=0.1,
                approval_rate=0.0,
                success_rate=0.0,
                avg_execution_time=0.0,
                sample_count=0,
            )

        base_score = self.calculate_base_score(alert_type, history)
        confidence = self.calculate_confidence(alert_type, history)

        # Use safe_divide for robustness against unexpected NaN values
        approval_rate = safe_divide(
            float(history.approved_count),
            float(history.total_recommendations),
            default=0.0,
        )

        # Overall score is base score weighted by confidence
        overall_score = base_score * (0.5 + 0.5 * confidence)

        return QualityScore(
            overall_score=overall_score,
            confidence=confidence,
            approval_rate=approval_rate,
            # Use safe_float for values that may come from external sources
            success_rate=safe_float(history.success_rate),
            avg_execution_time=safe_float(history.avg_execution_time_seconds),
            sample_count=history.total_recommendations,
        )

    def get_top_rejection_reasons(
        self,
        patterns: list[RejectionPattern],
        limit: int = 5,
    ) -> list[RejectionPattern]:
        """
        Get the top rejection reasons sorted by count.

        Args:
            patterns: List of rejection patterns.
            limit: Maximum number of patterns to return.

        Returns:
            Top rejection patterns sorted by count.
        """
        sorted_patterns = sorted(patterns, key=lambda p: p.count, reverse=True)
        return sorted_patterns[:limit]

    def generate_improvement_suggestions(
        self,
        patterns: list[RejectionPattern],
    ) -> list[str]:
        """
        Generate improvement suggestions based on rejection patterns.

        Args:
            patterns: List of rejection patterns.

        Returns:
            List of improvement suggestions.
        """
        suggestions = []

        for pattern in patterns:
            if pattern.reason in self.IMPROVEMENT_SUGGESTIONS:
                suggestions.append(self.IMPROVEMENT_SUGGESTIONS[pattern.reason])

        if not suggestions:
            suggestions.append("Review rejected recommendations to identify common patterns.")

        return suggestions


# =============================================================================
# Scoring History Repository
# =============================================================================


class ScoringHistoryRepository:
    """
    Repository for scoring history with caching.

    Manages storage and retrieval of scoring history data.
    """

    def __init__(self, store: ScoringHistoryStore) -> None:
        """
        Initialize the repository.

        Args:
            store: Storage backend for history data.
        """
        self._store = store
        self._cache: dict[str, ScoringHistory] = {}

    async def get_history(self, alert_type: str) -> ScoringHistory | None:
        """
        Get history for an alert type.

        Args:
            alert_type: The alert type to look up.

        Returns:
            ScoringHistory if found, None otherwise.
        """
        if alert_type in self._cache:
            return self._cache[alert_type]

        history = await self._store.get_history(alert_type)
        if history:
            self._cache[alert_type] = history

        return history

    async def get_all_histories(self) -> list[ScoringHistory]:
        """
        Get all scoring histories.

        Returns:
            List of all scoring histories.
        """
        return await self._store.list_all()

    async def record_feedback(self, feedback: FeedbackData) -> None:
        """
        Record feedback and update history.

        Args:
            feedback: Feedback data to record.
        """
        # Get existing history
        history = await self._store.get_history(feedback.alert_type)

        if history is None:
            # Create new history
            history = ScoringHistory(
                alert_type=feedback.alert_type,
                total_recommendations=0,
                approved_count=0,
                rejected_count=0,
                avg_execution_time_seconds=0.0,
                success_rate=0.0,
            )

        # Update counts
        history.total_recommendations += 1

        if feedback.action == "approved":
            history.approved_count += 1
            if feedback.execution_success:
                # Update success rate
                total_successes = int(history.success_rate * (history.approved_count - 1))
                history.success_rate = (total_successes + 1) / history.approved_count

                # Update average execution time
                if feedback.execution_time_seconds is not None:
                    old_total = history.avg_execution_time_seconds * (history.approved_count - 1)
                    history.avg_execution_time_seconds = (old_total + feedback.execution_time_seconds) / history.approved_count
        else:
            history.rejected_count += 1

        # Save updated history
        await self._store.save_history(history)

        # Update cache
        self._cache[feedback.alert_type] = history

        logger.debug(f"Recorded feedback for {feedback.alert_type}: {feedback.action}")
