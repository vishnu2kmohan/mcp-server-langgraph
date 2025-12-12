"""
HEART Metrics API

Provides endpoints for collecting and querying HEART framework metrics:
- Happiness: NPS scores, satisfaction ratings
- Engagement: Session duration, feature usage
- Adoption: New user tracking, onboarding
- Retention: Return visits, active days
- Task Success: Completion rates, error rates

Privacy features:
- Respects Do Not Track setting
- Anonymous session tracking
- No PII collection
"""

from datetime import UTC, datetime
from typing import Literal
from uuid import uuid4

from fastapi import APIRouter, Query, status
from pydantic import BaseModel, Field

from mcp_server_langgraph.observability.telemetry import logger

router = APIRouter(prefix="/api/v1/metrics", tags=["metrics"])


# =============================================================================
# Request/Response Models
# =============================================================================


class TaskMetrics(BaseModel):
    """Task success metrics"""

    tasks_started: int = Field(ge=0, description="Number of tasks started")
    tasks_completed: int = Field(ge=0, description="Number of tasks completed")
    tasks_errored: int = Field(ge=0, description="Number of tasks that errored")


class EngagementMetrics(BaseModel):
    """Engagement metrics"""

    session_duration_ms: int = Field(ge=0, description="Session duration in milliseconds")
    interaction_count: int = Field(ge=0, description="Number of interactions")
    feature_usage: dict[str, int] = Field(default_factory=dict, description="Feature usage counts")


class HappinessMetrics(BaseModel):
    """Happiness metrics"""

    nps_score: int | None = Field(None, ge=0, le=10, description="Net Promoter Score (0-10)")
    satisfaction_score: int | None = Field(None, ge=1, le=5, description="Satisfaction rating (1-5)")


class AdoptionMetrics(BaseModel):
    """Adoption metrics"""

    is_new_user: bool = Field(description="Whether this is a new user")
    onboarding_steps_completed: list[str] = Field(default_factory=list, description="Completed onboarding steps")


class RetentionMetrics(BaseModel):
    """Retention metrics"""

    return_visits: int = Field(ge=0, description="Number of return visits")
    days_active: int = Field(ge=0, description="Number of active days")


class HeartMetricsBatch(BaseModel):
    """Batch of HEART metrics for submission"""

    session_id: str = Field(description="Anonymous session identifier")
    app_name: Literal["builder", "playground"] = Field(description="Source application")
    task_success: TaskMetrics | None = None
    engagement: EngagementMetrics | None = None
    happiness: HappinessMetrics | None = None
    adoption: AdoptionMetrics | None = None
    retention: RetentionMetrics | None = None
    timestamp: datetime = Field(default_factory=lambda: datetime.now(UTC))


class MetricsReceiptResponse(BaseModel):
    """Response for metrics submission"""

    id: str = Field(description="Receipt ID")
    received_at: datetime = Field(description="Server receipt timestamp")
    message: str = Field(description="Status message")


class FeatureEvent(BaseModel):
    """Individual feature usage event"""

    feature_name: str = Field(description="Name of the feature used")
    event_type: Literal["used", "clicked", "error"] = Field(description="Type of event")
    metadata: dict[str, str | int | bool] | None = Field(None, description="Additional metadata")


class EventBatch(BaseModel):
    """Batch of feature events"""

    session_id: str = Field(description="Anonymous session identifier")
    app_name: Literal["builder", "playground"] = Field(description="Source application")
    events: list[FeatureEvent] = Field(description="List of events")


class EventReceiptResponse(BaseModel):
    """Response for event batch submission"""

    count: int = Field(description="Number of events received")
    received_at: datetime = Field(description="Server receipt timestamp")


class AggregateMetrics(BaseModel):
    """Aggregated metrics for dashboard"""

    period: str = Field(description="Aggregation period (e.g., '7d', '30d')")
    app_name: str | None = Field(None, description="Filter by app")

    # Happiness
    nps_score_avg: float | None = Field(None, description="Average NPS score")
    satisfaction_avg: float | None = Field(None, description="Average satisfaction")

    # Task Success
    task_success_rate: float | None = Field(None, description="Task completion rate")
    total_tasks_started: int = Field(0, description="Total tasks started")
    total_tasks_completed: int = Field(0, description="Total tasks completed")
    total_tasks_errored: int = Field(0, description="Total tasks errored")

    # Engagement
    avg_session_duration_ms: float | None = Field(None, description="Average session duration")
    total_interactions: int = Field(0, description="Total interactions")
    top_features: dict[str, int] = Field(default_factory=dict, description="Top features by usage")

    # Adoption
    new_users_count: int = Field(0, description="Number of new users")
    onboarding_completion_rate: float | None = Field(None, description="Onboarding completion rate")

    # Retention
    avg_return_visits: float | None = Field(None, description="Average return visits")
    avg_days_active: float | None = Field(None, description="Average active days")


# =============================================================================
# In-Memory Storage (Replace with database in production)
# =============================================================================

# Note: In production, these would be stored in PostgreSQL
_metrics_store: list[HeartMetricsBatch] = []
_events_store: list[tuple[str, str, FeatureEvent]] = []  # (session_id, app_name, event)


# =============================================================================
# Endpoints
# =============================================================================


@router.post(
    "/heart",
    status_code=status.HTTP_201_CREATED,
    summary="Submit HEART Metrics",
    description="Submit a batch of HEART framework metrics",
)
async def submit_heart_metrics(batch: HeartMetricsBatch) -> MetricsReceiptResponse:
    """
    Submit HEART framework metrics batch.

    Example:
        ```
        POST /api/v1/metrics/heart
        {
            "session_id": "abc-123",
            "app_name": "builder",
            "task_success": {"tasks_started": 5, "tasks_completed": 4, "tasks_errored": 1},
            "happiness": {"satisfaction_score": 4}
        }
        ```
    """
    receipt_id = str(uuid4())

    # Store metrics (in-memory for now)
    _metrics_store.append(batch)

    logger.info(
        "HEART metrics received",
        extra={
            "receipt_id": receipt_id,
            "session_id": batch.session_id,
            "app_name": batch.app_name,
            "has_happiness": batch.happiness is not None,
            "has_task_success": batch.task_success is not None,
        },
    )

    return MetricsReceiptResponse(
        id=receipt_id,
        received_at=datetime.now(UTC),
        message="Metrics received successfully",
    )


@router.post(
    "/events",
    status_code=status.HTTP_201_CREATED,
    summary="Submit Feature Events",
    description="Submit a batch of feature usage events",
)
async def submit_events(batch: EventBatch) -> EventReceiptResponse:
    """
    Submit feature usage events.

    Example:
        ```
        POST /api/v1/metrics/events
        {
            "session_id": "abc-123",
            "app_name": "builder",
            "events": [
                {"feature_name": "code_generation", "event_type": "used"},
                {"feature_name": "dark_mode", "event_type": "clicked"}
            ]
        }
        ```
    """
    for event in batch.events:
        _events_store.append((batch.session_id, batch.app_name, event))

    logger.info(
        "Feature events received",
        extra={
            "session_id": batch.session_id,
            "app_name": batch.app_name,
            "event_count": len(batch.events),
        },
    )

    return EventReceiptResponse(
        count=len(batch.events),
        received_at=datetime.now(UTC),
    )


@router.get(
    "/heart/aggregate",
    status_code=status.HTTP_200_OK,
    summary="Get Aggregated HEART Metrics",
    description="Get aggregated HEART metrics for a time period",
)
async def get_aggregate_metrics(
    period: str = Query("7d", description="Time period (e.g., '7d', '30d')"),
    app: str | None = Query(None, description="Filter by app name"),
) -> AggregateMetrics:
    """
    Get aggregated HEART metrics.

    Example:
        ```
        GET /api/v1/metrics/heart/aggregate?period=7d&app=builder
        ```
    """
    # Filter metrics by app if specified
    metrics = _metrics_store
    if app:
        metrics = [m for m in metrics if m.app_name == app]

    # Calculate aggregates
    nps_scores = [m.happiness.nps_score for m in metrics if m.happiness and m.happiness.nps_score is not None]
    satisfaction_scores = [
        m.happiness.satisfaction_score for m in metrics if m.happiness and m.happiness.satisfaction_score is not None
    ]

    tasks_started = sum(m.task_success.tasks_started for m in metrics if m.task_success)
    tasks_completed = sum(m.task_success.tasks_completed for m in metrics if m.task_success)
    tasks_errored = sum(m.task_success.tasks_errored for m in metrics if m.task_success)

    session_durations = [m.engagement.session_duration_ms for m in metrics if m.engagement]
    total_interactions = sum(m.engagement.interaction_count for m in metrics if m.engagement)

    # Aggregate feature usage
    feature_counts: dict[str, int] = {}
    for m in metrics:
        if m.engagement and m.engagement.feature_usage:
            for feature, count in m.engagement.feature_usage.items():
                feature_counts[feature] = feature_counts.get(feature, 0) + count

    # Sort and take top 10
    top_features = dict(sorted(feature_counts.items(), key=lambda x: x[1], reverse=True)[:10])

    new_users = sum(1 for m in metrics if m.adoption and m.adoption.is_new_user)
    onboarding_complete = sum(1 for m in metrics if m.adoption and "completed" in m.adoption.onboarding_steps_completed)

    return_visits = [m.retention.return_visits for m in metrics if m.retention]
    days_active = [m.retention.days_active for m in metrics if m.retention]

    return AggregateMetrics(
        period=period,
        app_name=app,
        nps_score_avg=sum(nps_scores) / len(nps_scores) if nps_scores else None,
        satisfaction_avg=sum(satisfaction_scores) / len(satisfaction_scores) if satisfaction_scores else None,
        task_success_rate=tasks_completed / tasks_started if tasks_started > 0 else None,
        total_tasks_started=tasks_started,
        total_tasks_completed=tasks_completed,
        total_tasks_errored=tasks_errored,
        avg_session_duration_ms=sum(session_durations) / len(session_durations) if session_durations else None,
        total_interactions=total_interactions,
        top_features=top_features,
        new_users_count=new_users,
        onboarding_completion_rate=onboarding_complete / new_users if new_users > 0 else None,
        avg_return_visits=sum(return_visits) / len(return_visits) if return_visits else None,
        avg_days_active=sum(days_active) / len(days_active) if days_active else None,
    )


@router.get(
    "/dashboard",
    status_code=status.HTTP_200_OK,
    summary="Get Dashboard Data",
    description="Get all metrics data for admin dashboard",
)
async def get_dashboard() -> dict:
    """
    Get dashboard data for admin UI.

    Returns aggregated metrics for both apps and recent event counts.
    """
    builder_metrics = await get_aggregate_metrics(period="7d", app="builder")
    playground_metrics = await get_aggregate_metrics(period="7d", app="playground")

    return {
        "builder": builder_metrics.model_dump(),
        "playground": playground_metrics.model_dump(),
        "total_metrics_count": len(_metrics_store),
        "total_events_count": len(_events_store),
        "generated_at": datetime.now(UTC).isoformat(),
    }
