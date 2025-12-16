"""
Feedback Endpoints.

Provides user feedback collection including hallucination reports,
message ratings (thumbs up/down), and feedback summaries.

Hallucination Categories:
- factual_error: AI made a factually incorrect statement
- outdated_info: Information is no longer current
- made_up_source: AI cited a non-existent source
- other: Other types of hallucinations

Usage:
    POST /api/v1/feedback/hallucination - Report hallucination
    POST /api/v1/feedback/message - Submit message feedback
    GET /api/v1/feedback/summary - Get feedback summary
"""

import logging
from datetime import datetime, UTC
from enum import Enum
from typing import Any, Protocol

from fastapi import APIRouter, Depends, status
from pydantic import BaseModel, Field

logger = logging.getLogger(__name__)

router = APIRouter(tags=["feedback"])


# Enums
class HallucinationCategory(str, Enum):
    """Categories of hallucinations."""

    FACTUAL_ERROR = "factual_error"
    OUTDATED_INFO = "outdated_info"
    MADE_UP_SOURCE = "made_up_source"
    OTHER = "other"


class Severity(str, Enum):
    """Severity levels for reports."""

    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"


class Rating(str, Enum):
    """Rating values for message feedback."""

    POSITIVE = "positive"
    NEGATIVE = "negative"


# Pydantic models for request/response
class HallucinationReportRequest(BaseModel):
    """Hallucination report submission request."""

    message_id: str = Field(..., description="ID of the message containing hallucination")
    session_id: str = Field(..., description="Session ID for context")
    category: HallucinationCategory = Field(..., description="Type of hallucination")
    description: str = Field(..., max_length=2000, description="User description of the issue")
    severity: Severity = Field(default=Severity.MEDIUM, description="Severity level")


class HallucinationReportResponse(BaseModel):
    """Hallucination report response."""

    id: str
    status: str = "received"
    recorded_at: datetime = Field(default_factory=lambda: datetime.now(UTC))


class MessageFeedbackRequest(BaseModel):
    """Message feedback submission request."""

    message_id: str = Field(..., description="ID of the message")
    session_id: str = Field(..., description="Session ID for context")
    rating: Rating = Field(..., description="Positive or negative rating")
    reason: str | None = Field(None, max_length=500, description="Optional reason for rating")


class MessageFeedbackResponse(BaseModel):
    """Message feedback response."""

    id: str
    rating: Rating
    recorded_at: datetime = Field(default_factory=lambda: datetime.now(UTC))


class HallucinationCategoryCounts(BaseModel):
    """Counts by hallucination category."""

    factual_error: int = 0
    outdated_info: int = 0
    made_up_source: int = 0
    other: int = 0


class FeedbackSummaryResponse(BaseModel):
    """Aggregated feedback summary."""

    timeframe: str
    total_feedback: int = 0
    positive_count: int = 0
    negative_count: int = 0
    positive_rate: float = 0.0
    hallucination_reports: int = 0
    hallucination_categories: HallucinationCategoryCounts = Field(default_factory=HallucinationCategoryCounts)


# Feedback service protocol
class FeedbackService(Protocol):
    """Protocol for feedback service."""

    async def submit_hallucination_report(self, user_id: str, report: HallucinationReportRequest) -> dict[str, Any]:
        """Submit a hallucination report."""
        ...

    async def submit_message_feedback(self, user_id: str, feedback: MessageFeedbackRequest) -> dict[str, Any]:
        """Submit message feedback."""
        ...

    async def get_feedback_summary(self, timeframe: str) -> dict[str, Any]:
        """Get aggregated feedback summary."""
        ...


# In-memory feedback service for development/testing
class InMemoryFeedbackService:
    """In-memory feedback service for development."""

    def __init__(self) -> None:
        """Initialize the service."""
        self._hallucination_reports: list[dict[str, Any]] = []
        self._message_feedback: list[dict[str, Any]] = []
        self._counter = 0

    def _generate_id(self, prefix: str) -> str:
        """Generate a unique ID."""
        self._counter += 1
        return f"{prefix}-{self._counter:06d}"

    async def submit_hallucination_report(self, user_id: str, report: HallucinationReportRequest) -> dict[str, Any]:
        """Submit a hallucination report."""
        record = {
            "id": self._generate_id("report"),
            "user_id": user_id,
            "message_id": report.message_id,
            "session_id": report.session_id,
            "category": report.category.value,
            "description": report.description,
            "severity": report.severity.value,
            "status": "received",
            "timestamp": datetime.now(UTC).isoformat(),
        }
        self._hallucination_reports.append(record)
        logger.info(f"Recorded hallucination report from user {user_id}: {report.category.value}")
        return {"id": record["id"], "status": "received"}

    async def submit_message_feedback(self, user_id: str, feedback: MessageFeedbackRequest) -> dict[str, Any]:
        """Submit message feedback."""
        record = {
            "id": self._generate_id("feedback"),
            "user_id": user_id,
            "message_id": feedback.message_id,
            "session_id": feedback.session_id,
            "rating": feedback.rating.value,
            "reason": feedback.reason,
            "timestamp": datetime.now(UTC).isoformat(),
        }
        self._message_feedback.append(record)
        logger.info(f"Recorded message feedback from user {user_id}: {feedback.rating.value}")
        return {"id": record["id"], "rating": feedback.rating.value}

    async def get_feedback_summary(self, timeframe: str) -> dict[str, Any]:
        """Get aggregated feedback summary."""
        # Calculate message feedback stats
        positive_count = sum(1 for f in self._message_feedback if f["rating"] == "positive")
        negative_count = sum(1 for f in self._message_feedback if f["rating"] == "negative")
        total_feedback = len(self._message_feedback)
        positive_rate = positive_count / total_feedback if total_feedback > 0 else 0.0

        # Calculate hallucination stats
        category_counts = {
            "factual_error": 0,
            "outdated_info": 0,
            "made_up_source": 0,
            "other": 0,
        }
        for report in self._hallucination_reports:
            category = report["category"]
            if category in category_counts:
                category_counts[category] += 1

        return {
            "timeframe": timeframe,
            "total_feedback": total_feedback,
            "positive_count": positive_count,
            "negative_count": negative_count,
            "positive_rate": positive_rate,
            "hallucination_reports": len(self._hallucination_reports),
            "hallucination_categories": category_counts,
        }


# Global service instance
_feedback_service: FeedbackService | None = None


def get_feedback_service() -> FeedbackService:
    """Get the feedback service instance."""
    global _feedback_service
    if _feedback_service is None:
        _feedback_service = InMemoryFeedbackService()
    return _feedback_service


def set_feedback_service(service: FeedbackService | None) -> None:
    """Set the feedback service instance (for testing)."""
    global _feedback_service
    _feedback_service = service


# Endpoints
@router.post(
    "/hallucination",
    status_code=status.HTTP_201_CREATED,
)
async def submit_hallucination_report(
    report: HallucinationReportRequest,
    service: FeedbackService = Depends(get_feedback_service),
) -> HallucinationReportResponse:
    """
    Report a hallucination in an AI response.

    Use this endpoint when the AI:
    - Made a factually incorrect statement
    - Provided outdated information
    - Cited a non-existent source
    - Exhibited other hallucination behavior
    """
    # In real app, get user from request.state.user
    user_id = "user-001"  # Placeholder

    result = await service.submit_hallucination_report(user_id, report)
    return HallucinationReportResponse(
        id=result["id"],
        status=result["status"],
    )


@router.post(
    "/message",
    status_code=status.HTTP_201_CREATED,
)
async def submit_message_feedback(
    feedback: MessageFeedbackRequest,
    service: FeedbackService = Depends(get_feedback_service),
) -> MessageFeedbackResponse:
    """
    Submit feedback for a message (thumbs up/down).

    Use this endpoint to rate AI responses as helpful or unhelpful.
    Optionally provide a reason for the rating.
    """
    # In real app, get user from request.state.user
    user_id = "user-001"  # Placeholder

    result = await service.submit_message_feedback(user_id, feedback)
    return MessageFeedbackResponse(
        id=result["id"],
        rating=Rating(result["rating"]),
    )


@router.get("/summary")
async def get_feedback_summary(
    timeframe: str = "7d",
    service: FeedbackService = Depends(get_feedback_service),
) -> FeedbackSummaryResponse:
    """
    Get aggregated feedback summary.

    Args:
        timeframe: Time period for aggregation (7d, 30d, 90d)

    Returns:
        Aggregated feedback metrics including positive rate and hallucination counts.
    """
    result = await service.get_feedback_summary(timeframe)
    return FeedbackSummaryResponse(**result)
