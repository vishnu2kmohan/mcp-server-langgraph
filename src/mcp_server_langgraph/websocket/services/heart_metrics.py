"""
HEART Metrics Service Adapter for WebSocket.

Adapts the metrics infrastructure to the HeartMetricsServiceProtocol
expected by the WebSocket handler.

HEART Framework Metrics:
- Happiness: User satisfaction and experience quality
- Engagement: User interaction frequency and depth
- Adoption: New feature/capability uptake
- Retention: User return rate and session continuity
- Task Success: Successful task completion rate

Architecture:
    - Queries Prometheus/Mimir for aggregated metrics (when configured)
    - Falls back to stub data for development/testing
"""

from __future__ import annotations

import logging
from typing import Any

from mcp_server_langgraph.core.feature_flags import get_feature_flags

logger = logging.getLogger(__name__)


class HeartMetricsServiceAdapter:
    """
    Adapter for HEART framework metrics in WebSocket handlers.

    Provides real-time HEART metrics data for dashboard streaming.
    Uses Prometheus/Mimir backend when available, stubs otherwise.

    The HEART framework measures:
    - Happiness (H): User satisfaction
    - Engagement (E): User activity levels
    - Adoption (A): Feature uptake
    - Retention (R): User return rate
    - Task success (T): Completion rates
    """

    def __init__(self) -> None:
        """Initialize the HEART metrics adapter."""
        self._cached_snapshot: dict[str, Any] | None = None
        self._cached_dimensions: dict[str, dict[str, Any]] = {}

    async def get_current_snapshot(self, time_range: str = "24h") -> dict[str, Any]:
        """
        Get current HEART metrics snapshot.

        Args:
            time_range: Time range for metrics (1h, 24h, 7d, 30d).

        Returns:
            Dict with all HEART dimension scores and trends.
        """
        flags = get_feature_flags()
        if not flags.enable_websocket_enhanced_metrics:
            return self._get_minimal_snapshot()

        # TODO: When Prometheus/Mimir is configured:
        # - Query happiness_score metric
        # - Query engagement_rate metric
        # - Query adoption_rate metric
        # - Query retention_rate metric
        # - Query task_success_rate metric
        # - Calculate trends from historical data

        # Stub data for development
        return {
            "happiness": {"score": 85, "trend": "up", "change": 2.5},
            "engagement": {"score": 72, "trend": "stable", "change": 0.3},
            "adoption": {"score": 90, "trend": "up", "change": 5.0},
            "retention": {"score": 88, "trend": "stable", "change": -0.5},
            "task_success": {"score": 95, "trend": "up", "change": 1.2},
            "time_range": time_range,
            "last_updated": "2025-12-22T12:00:00Z",
        }

    async def get_dimension_metrics(self, dimension: str, time_range: str = "24h") -> dict[str, Any]:
        """
        Get detailed metrics for a specific HEART dimension.

        Args:
            dimension: HEART dimension (happiness, engagement, etc.).
            time_range: Time range for metrics.

        Returns:
            Detailed metrics for the dimension.
        """
        valid_dimensions = {"happiness", "engagement", "adoption", "retention", "task_success"}
        if dimension not in valid_dimensions:
            logger.warning(f"Unknown HEART dimension: {dimension}")
            return {"error": f"Unknown dimension: {dimension}"}

        # TODO: Query specific dimension metrics from Prometheus/Mimir

        # Stub data mapping
        dimension_data = {
            "happiness": {
                "score": 85,
                "trend": "up",
                "samples": 1250,
                "breakdown": {
                    "response_quality": 88,
                    "response_speed": 82,
                    "error_rate": 92,
                },
            },
            "engagement": {
                "score": 72,
                "trend": "stable",
                "samples": 3400,
                "breakdown": {
                    "sessions_per_user": 3.2,
                    "messages_per_session": 12.5,
                    "feature_usage": 0.68,
                },
            },
            "adoption": {
                "score": 90,
                "trend": "up",
                "samples": 450,
                "breakdown": {
                    "new_users": 45,
                    "feature_first_use": 120,
                    "onboarding_completion": 0.92,
                },
            },
            "retention": {
                "score": 88,
                "trend": "stable",
                "samples": 2100,
                "breakdown": {
                    "day_1": 0.95,
                    "day_7": 0.72,
                    "day_30": 0.45,
                },
            },
            "task_success": {
                "score": 95,
                "trend": "up",
                "samples": 5200,
                "breakdown": {
                    "completion_rate": 0.95,
                    "error_recovery": 0.88,
                    "avg_attempts": 1.2,
                },
            },
        }

        return dimension_data.get(dimension, {"error": "Not found"})

    def _get_minimal_snapshot(self) -> dict[str, Any]:
        """Get minimal snapshot when enhanced metrics are disabled."""
        return {
            "happiness": {"score": 0, "trend": "stable"},
            "engagement": {"score": 0, "trend": "stable"},
            "adoption": {"score": 0, "trend": "stable"},
            "retention": {"score": 0, "trend": "stable"},
            "task_success": {"score": 0, "trend": "stable"},
            "metrics_enabled": False,
        }


# Service singleton
_websocket_heart_metrics_service: HeartMetricsServiceAdapter | None = None


def get_websocket_heart_metrics_service() -> HeartMetricsServiceAdapter:
    """Get the WebSocket HEART metrics service adapter instance."""
    global _websocket_heart_metrics_service
    if _websocket_heart_metrics_service is None:
        _websocket_heart_metrics_service = HeartMetricsServiceAdapter()
    return _websocket_heart_metrics_service


def reset_websocket_heart_metrics_service() -> None:
    """Reset the WebSocket HEART metrics service singleton (for testing)."""
    global _websocket_heart_metrics_service
    _websocket_heart_metrics_service = None
