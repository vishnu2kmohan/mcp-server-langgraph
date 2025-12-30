"""
SUS Surveys Endpoint.

Provides System Usability Scale (SUS) survey collection and analysis.

The SUS is a reliable, low-cost usability scale that can be used for
global assessments of systems usability. It consists of 10 questions
with 5-point Likert scale responses.

SUS Score Interpretation:
- 80.3+ : Excellent (top 10%)
- 68-80.2: Good (above average)
- 51-67: OK (below average)
- <51: Poor (needs improvement)

Usage:
    POST /api/v1/surveys/sus - Submit SUS survey
    GET /api/v1/surveys/sus/summary - Get aggregated survey results
"""

import logging
from datetime import UTC, datetime
from typing import Annotated, Any, Protocol

from fastapi import APIRouter, Depends, status
from pydantic import BaseModel, Field, field_validator

from mcp_server_langgraph.auth.dependencies import get_current_user

logger = logging.getLogger(__name__)

router = APIRouter(tags=["surveys"])

# Type alias for authenticated user dependency
CurrentUser = Annotated[dict[str, Any], Depends(get_current_user)]


# Pydantic models for request/response
class SUSSurveyRequest(BaseModel):
    """SUS survey submission request."""

    responses: list[int] = Field(
        ...,
        description="10 SUS responses (1-5 scale)",
        min_length=10,
        max_length=10,
    )

    @field_validator("responses")
    @classmethod
    def validate_responses(cls, v: list[int]) -> list[int]:
        """Validate each response is in 1-5 range."""
        for i, response in enumerate(v):
            if response < 1 or response > 5:
                raise ValueError(f"Response {i + 1} must be between 1 and 5, got {response}")
        return v


class SUSSurveyResponse(BaseModel):
    """SUS survey submission response."""

    id: str
    sus_score: float = Field(..., ge=0.0, le=100.0)
    recorded_at: datetime = Field(default_factory=lambda: datetime.now(UTC))


class ScoreDistribution(BaseModel):
    """Distribution of SUS scores by category."""

    excellent: int = Field(default=0, ge=0, description="80.3+ scores")
    good: int = Field(default=0, ge=0, description="68-80.2 scores")
    ok: int = Field(default=0, ge=0, description="51-67 scores")
    poor: int = Field(default=0, ge=0, description="<51 scores")


class SUSSummaryResponse(BaseModel):
    """Aggregated SUS survey results."""

    timeframe: str
    avg_score: float | None = None
    response_count: int = 0
    score_distribution: ScoreDistribution = Field(default_factory=ScoreDistribution)


def calculate_sus_score(responses: list[int]) -> float:
    """
    Calculate the SUS score from 10 responses.

    SUS Scoring Algorithm:
    - For odd-numbered questions (1, 3, 5, 7, 9): score = response - 1
    - For even-numbered questions (2, 4, 6, 8, 10): score = 5 - response
    - Sum all scores and multiply by 2.5 to get 0-100 scale

    Args:
        responses: List of 10 responses (1-5 scale)

    Returns:
        SUS score (0-100 scale)
    """
    if len(responses) != 10:
        raise ValueError("SUS requires exactly 10 responses")

    total = 0
    for i, response in enumerate(responses):
        question_num = i + 1  # 1-indexed
        if question_num % 2 == 1:  # Odd questions (positive phrasing)
            total += response - 1
        else:  # Even questions (negative phrasing)
            total += 5 - response

    return total * 2.5


# Surveys service protocol
class SurveysService(Protocol):
    """Protocol for surveys service."""

    async def submit_sus_survey(self, user_id: str, responses: list[int], sus_score: float) -> dict[str, Any]:
        """Submit a SUS survey."""
        ...

    async def get_sus_summary(self, timeframe: str) -> dict[str, Any]:
        """Get aggregated SUS survey results."""
        ...


# In-memory surveys service for development/testing
class InMemorySurveysService:
    """In-memory surveys service for development."""

    def __init__(self) -> None:
        """Initialize the service."""
        self._surveys: list[dict[str, Any]] = []
        self._counter = 0

    def _generate_id(self) -> str:
        """Generate a unique survey ID."""
        self._counter += 1
        return f"survey-{self._counter:06d}"

    async def submit_sus_survey(self, user_id: str, responses: list[int], sus_score: float) -> dict[str, Any]:
        """Submit a SUS survey."""
        record = {
            "id": self._generate_id(),
            "user_id": user_id,
            "responses": responses,
            "sus_score": sus_score,
            "timestamp": datetime.now(UTC).isoformat(),
        }
        self._surveys.append(record)
        logger.info(f"Recorded SUS survey for user {user_id}, score: {sus_score}")
        return {"id": record["id"], "sus_score": sus_score}

    async def get_sus_summary(self, timeframe: str) -> dict[str, Any]:
        """Get aggregated SUS survey results."""
        if not self._surveys:
            return {
                "timeframe": timeframe,
                "avg_score": None,
                "response_count": 0,
                "score_distribution": {
                    "excellent": 0,
                    "good": 0,
                    "ok": 0,
                    "poor": 0,
                },
            }

        scores = [s["sus_score"] for s in self._surveys]

        # Calculate distribution
        excellent = sum(1 for s in scores if s >= 80.3)
        good = sum(1 for s in scores if 68 <= s < 80.3)
        ok = sum(1 for s in scores if 51 <= s < 68)
        poor = sum(1 for s in scores if s < 51)

        return {
            "timeframe": timeframe,
            "avg_score": sum(scores) / len(scores),
            "response_count": len(scores),
            "score_distribution": {
                "excellent": excellent,
                "good": good,
                "ok": ok,
                "poor": poor,
            },
        }


# Global service instance
_surveys_service: SurveysService | None = None


def get_surveys_service() -> SurveysService:
    """Get the surveys service instance."""
    global _surveys_service
    if _surveys_service is None:
        _surveys_service = InMemorySurveysService()
    return _surveys_service


def set_surveys_service(service: SurveysService | None) -> None:
    """Set the surveys service instance (for testing)."""
    global _surveys_service
    _surveys_service = service


# Endpoints
@router.post(
    "/sus",
    status_code=status.HTTP_201_CREATED,
)
async def submit_sus_survey(
    request: SUSSurveyRequest,
    current_user: CurrentUser,
    service: SurveysService = Depends(get_surveys_service),
) -> SUSSurveyResponse:
    """
    Submit a SUS survey.

    Requires user authentication.

    The SUS consists of 10 questions with 5-point Likert scale responses:
    1 = Strongly Disagree, 5 = Strongly Agree

    Questions alternate between positive and negative phrasing:
    - Odd questions (1,3,5,7,9): Positive phrasing
    - Even questions (2,4,6,8,10): Negative phrasing
    """
    # Calculate SUS score
    sus_score = calculate_sus_score(request.responses)

    user_id = current_user.get("sub", current_user.get("user_id", "unknown"))

    result = await service.submit_sus_survey(user_id, request.responses, sus_score)
    return SUSSurveyResponse(
        id=result["id"],
        sus_score=result["sus_score"],
    )


@router.get("/sus/summary")
async def get_sus_summary(
    current_user: CurrentUser,
    timeframe: str = "30d",
    service: SurveysService = Depends(get_surveys_service),
) -> SUSSummaryResponse:
    """
    Get aggregated SUS survey results.

    Requires user authentication.

    Args:
        timeframe: Time period for aggregation (7d, 30d, 90d)

    Returns:
        Aggregated SUS metrics including average score and distribution.
    """
    result = await service.get_sus_summary(timeframe)
    return SUSSummaryResponse(**result)
