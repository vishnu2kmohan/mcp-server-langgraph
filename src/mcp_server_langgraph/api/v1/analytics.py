"""
HEART Analytics Endpoint.

Provides HEART metrics collection and retrieval for UX measurement.

HEART Framework:
- Happiness: User satisfaction (NPS, CSAT)
- Engagement: Session duration, features used
- Adoption: Onboarding completion, feature discovery
- Retention: Return visits, D7/D30 retention
- Task Success: Task completion rates, error rates

Usage:
    POST /api/v1/analytics/heart/happiness - Track happiness metrics
    POST /api/v1/analytics/heart/engagement - Track engagement metrics
    POST /api/v1/analytics/heart/adoption - Track adoption metrics
    POST /api/v1/analytics/heart/retention - Track retention metrics
    POST /api/v1/analytics/heart/task-success - Track task success metrics
    GET /api/v1/analytics/heart - Get aggregated HEART metrics
"""

import logging
from datetime import datetime, UTC
from typing import Any, Protocol

from mcp_server_langgraph.core.numeric import safe_average, safe_divide

from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel, Field

logger = logging.getLogger(__name__)

router = APIRouter(tags=["analytics"])


# Pydantic models for request/response
class HappinessMetric(BaseModel):
    """Happiness metric submission."""

    nps_score: int | None = Field(None, ge=-100, le=100, description="Net Promoter Score")
    csat_score: float | None = Field(None, ge=1.0, le=5.0, description="Customer Satisfaction Score")
    feedback: str | None = Field(None, max_length=1000, description="Optional feedback text")
    context: str | None = Field(None, max_length=100, description="Context where feedback was given")


class EngagementMetric(BaseModel):
    """Engagement metric submission."""

    session_id: str = Field(..., description="Session identifier")
    duration_seconds: int = Field(..., ge=0, description="Session duration in seconds")
    features_used: list[str] = Field(default_factory=list, description="Features used during session")


class AdoptionMetric(BaseModel):
    """Adoption metric submission."""

    step: str = Field(..., description="Onboarding or feature step name")
    step_index: int = Field(..., ge=0, description="Step index in flow")
    completed: bool = Field(..., description="Whether step was completed")


class RetentionMetric(BaseModel):
    """Retention metric submission."""

    days_since_last_visit: int = Field(..., ge=0, description="Days since last visit")
    return_visit: bool = Field(..., description="Whether this is a return visit")


class TaskSuccessMetric(BaseModel):
    """Task success metric submission."""

    task_id: str = Field(..., description="Task identifier")
    success: bool = Field(..., description="Whether task was successful")
    duration_seconds: int = Field(..., ge=0, description="Task duration in seconds")
    error_count: int = Field(default=0, ge=0, description="Number of errors encountered")
    error_message: str | None = Field(None, max_length=500, description="Error message if failed")


class MetricResponse(BaseModel):
    """Response for metric submission."""

    id: str
    recorded_at: datetime = Field(default_factory=lambda: datetime.now(UTC))


class HappinessSummary(BaseModel):
    """Aggregated happiness metrics."""

    nps_score_avg: float | None = None
    csat_score_avg: float | None = None
    response_count: int = 0


class EngagementSummary(BaseModel):
    """Aggregated engagement metrics."""

    avg_session_duration_seconds: float = 0.0
    sessions_per_user: float = 0.0
    active_users: int = 0


class AdoptionSummary(BaseModel):
    """Aggregated adoption metrics."""

    onboarding_completion_rate: float = 0.0
    feature_adoption: dict[str, float] = Field(default_factory=dict)


class RetentionSummary(BaseModel):
    """Aggregated retention metrics."""

    d7_retention: float = 0.0
    d30_retention: float = 0.0


class TaskSuccessSummary(BaseModel):
    """Aggregated task success metrics."""

    overall_success_rate: float = 0.0
    avg_task_duration_seconds: float = 0.0


class HeartSummary(BaseModel):
    """Complete HEART metrics summary."""

    timeframe: str
    persona: str | None = None
    happiness: HappinessSummary = Field(default_factory=HappinessSummary)
    engagement: EngagementSummary = Field(default_factory=EngagementSummary)
    adoption: AdoptionSummary = Field(default_factory=AdoptionSummary)
    retention: RetentionSummary = Field(default_factory=RetentionSummary)
    task_success: TaskSuccessSummary = Field(default_factory=TaskSuccessSummary)


# Analytics service protocol
class AnalyticsService(Protocol):
    """Protocol for analytics service."""

    async def track_happiness(self, user_id: str, metric: HappinessMetric) -> dict[str, Any]:
        """Track happiness metric."""
        ...

    async def track_engagement(self, user_id: str, metric: EngagementMetric) -> dict[str, Any]:
        """Track engagement metric."""
        ...

    async def track_adoption(self, user_id: str, metric: AdoptionMetric) -> dict[str, Any]:
        """Track adoption metric."""
        ...

    async def track_retention(self, user_id: str, metric: RetentionMetric) -> dict[str, Any]:
        """Track retention metric."""
        ...

    async def track_task_success(self, user_id: str, metric: TaskSuccessMetric) -> dict[str, Any]:
        """Track task success metric."""
        ...

    async def get_heart_summary(self, timeframe: str, persona: str | None = None) -> dict[str, Any]:
        """Get aggregated HEART metrics."""
        ...


# In-memory analytics service for development/testing
class InMemoryAnalyticsService:
    """In-memory analytics service for development."""

    def __init__(self) -> None:
        """Initialize the service."""
        self._metrics: dict[str, list[dict[str, Any]]] = {
            "happiness": [],
            "engagement": [],
            "adoption": [],
            "retention": [],
            "task_success": [],
        }
        self._counter = 0

    def _generate_id(self) -> str:
        """Generate a unique metric ID."""
        self._counter += 1
        return f"metric-{self._counter:06d}"

    async def track_happiness(self, user_id: str, metric: HappinessMetric) -> dict[str, Any]:
        """Track happiness metric."""
        record = {
            "id": self._generate_id(),
            "user_id": user_id,
            "timestamp": datetime.now(UTC).isoformat(),
            **metric.model_dump(),
        }
        self._metrics["happiness"].append(record)
        logger.info(f"Tracked happiness metric for user {user_id}")
        return {"id": record["id"]}

    async def track_engagement(self, user_id: str, metric: EngagementMetric) -> dict[str, Any]:
        """Track engagement metric."""
        record = {
            "id": self._generate_id(),
            "user_id": user_id,
            "timestamp": datetime.now(UTC).isoformat(),
            **metric.model_dump(),
        }
        self._metrics["engagement"].append(record)
        logger.info(f"Tracked engagement metric for user {user_id}")
        return {"id": record["id"]}

    async def track_adoption(self, user_id: str, metric: AdoptionMetric) -> dict[str, Any]:
        """Track adoption metric."""
        record = {
            "id": self._generate_id(),
            "user_id": user_id,
            "timestamp": datetime.now(UTC).isoformat(),
            **metric.model_dump(),
        }
        self._metrics["adoption"].append(record)
        logger.info(f"Tracked adoption metric for user {user_id}")
        return {"id": record["id"]}

    async def track_retention(self, user_id: str, metric: RetentionMetric) -> dict[str, Any]:
        """Track retention metric."""
        record = {
            "id": self._generate_id(),
            "user_id": user_id,
            "timestamp": datetime.now(UTC).isoformat(),
            **metric.model_dump(),
        }
        self._metrics["retention"].append(record)
        logger.info(f"Tracked retention metric for user {user_id}")
        return {"id": record["id"]}

    async def track_task_success(self, user_id: str, metric: TaskSuccessMetric) -> dict[str, Any]:
        """Track task success metric."""
        record = {
            "id": self._generate_id(),
            "user_id": user_id,
            "timestamp": datetime.now(UTC).isoformat(),
            **metric.model_dump(),
        }
        self._metrics["task_success"].append(record)
        logger.info(f"Tracked task success metric for user {user_id}")
        return {"id": record["id"]}

    async def get_heart_summary(self, timeframe: str, persona: str | None = None) -> dict[str, Any]:
        """Get aggregated HEART metrics."""
        # In production, this would aggregate from database
        happiness_records = self._metrics["happiness"]
        engagement_records = self._metrics["engagement"]
        adoption_records = self._metrics["adoption"]
        retention_records = self._metrics["retention"]
        task_records = self._metrics["task_success"]

        # Calculate averages
        nps_scores = [r["nps_score"] for r in happiness_records if r.get("nps_score") is not None]
        csat_scores = [r["csat_score"] for r in happiness_records if r.get("csat_score") is not None]
        durations = [r["duration_seconds"] for r in engagement_records]
        success_rates = [1 if r["success"] else 0 for r in task_records]

        return {
            "timeframe": timeframe,
            "persona": persona,
            "happiness": {
                "nps_score_avg": safe_average(nps_scores) if nps_scores else None,
                "csat_score_avg": safe_average(csat_scores) if csat_scores else None,
                "response_count": len(happiness_records),
            },
            "engagement": {
                "avg_session_duration_seconds": safe_average(durations),
                "sessions_per_user": safe_divide(len(engagement_records), len({r["user_id"] for r in engagement_records})),
                "active_users": len({r["user_id"] for r in engagement_records}),
            },
            "adoption": {
                "onboarding_completion_rate": safe_divide(
                    sum(1 for r in adoption_records if r["completed"]), len(adoption_records)
                ),
                "feature_adoption": {},
            },
            "retention": {
                "d7_retention": safe_divide(
                    sum(1 for r in retention_records if r["return_visit"] and r["days_since_last_visit"] <= 7),
                    len(retention_records),
                ),
                "d30_retention": safe_divide(
                    sum(1 for r in retention_records if r["return_visit"] and r["days_since_last_visit"] <= 30),
                    len(retention_records),
                ),
            },
            "task_success": {
                "overall_success_rate": safe_average(success_rates),
                "avg_task_duration_seconds": safe_average([r["duration_seconds"] for r in task_records]),
            },
        }


# Global service instance
_analytics_service: AnalyticsService | None = None


def get_analytics_service() -> AnalyticsService:
    """Get the analytics service instance."""
    global _analytics_service
    if _analytics_service is None:
        _analytics_service = InMemoryAnalyticsService()
    return _analytics_service


def set_analytics_service(service: AnalyticsService | None) -> None:
    """Set the analytics service instance (for testing)."""
    global _analytics_service
    _analytics_service = service


# Dependency to get current user (will be overridden in tests)
async def get_current_user_from_request() -> dict[str, Any]:
    """Get current user from request state."""
    # This is a placeholder - in real app, uses middleware
    return {"user_id": "anonymous", "roles": ["user"]}


def require_admin(user: dict[str, Any]) -> None:
    """Check if user has admin role."""
    roles = user.get("roles", [])
    if "admin" not in roles:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Admin access required",
        )


# Endpoints
@router.post(
    "/heart/happiness",
    status_code=status.HTTP_201_CREATED,
)
async def track_happiness(
    metric: HappinessMetric,
    service: AnalyticsService = Depends(get_analytics_service),
) -> MetricResponse:
    """Track happiness metric (NPS, CSAT)."""
    # In real app, get user from request.state.user
    user_id = "user-001"  # Placeholder
    result = await service.track_happiness(user_id, metric)
    return MetricResponse(id=result["id"])


@router.post(
    "/heart/engagement",
    status_code=status.HTTP_201_CREATED,
)
async def track_engagement(
    metric: EngagementMetric,
    service: AnalyticsService = Depends(get_analytics_service),
) -> MetricResponse:
    """Track engagement metric (session duration, features used)."""
    user_id = "user-001"  # Placeholder
    result = await service.track_engagement(user_id, metric)
    return MetricResponse(id=result["id"])


@router.post(
    "/heart/adoption",
    status_code=status.HTTP_201_CREATED,
)
async def track_adoption(
    metric: AdoptionMetric,
    service: AnalyticsService = Depends(get_analytics_service),
) -> MetricResponse:
    """Track adoption metric (onboarding steps, feature discovery)."""
    user_id = "user-001"  # Placeholder
    result = await service.track_adoption(user_id, metric)
    return MetricResponse(id=result["id"])


@router.post(
    "/heart/retention",
    status_code=status.HTTP_201_CREATED,
)
async def track_retention(
    metric: RetentionMetric,
    service: AnalyticsService = Depends(get_analytics_service),
) -> MetricResponse:
    """Track retention metric (return visits)."""
    user_id = "user-001"  # Placeholder
    result = await service.track_retention(user_id, metric)
    return MetricResponse(id=result["id"])


@router.post(
    "/heart/task-success",
    status_code=status.HTTP_201_CREATED,
)
async def track_task_success(
    metric: TaskSuccessMetric,
    service: AnalyticsService = Depends(get_analytics_service),
) -> MetricResponse:
    """Track task success metric (completion rates, errors)."""
    user_id = "user-001"  # Placeholder
    result = await service.track_task_success(user_id, metric)
    return MetricResponse(id=result["id"])


@router.get("/heart")
async def get_heart_metrics(
    timeframe: str = "7d",
    persona: str | None = None,
    service: AnalyticsService = Depends(get_analytics_service),
) -> HeartSummary:
    """
    Get aggregated HEART metrics.

    Args:
        timeframe: Time period (7d, 30d, 90d)
        persona: Optional persona filter (admin, developer, user)

    Returns:
        Aggregated HEART metrics for the specified timeframe.
    """
    result = await service.get_heart_summary(timeframe, persona)
    return HeartSummary(**result)
