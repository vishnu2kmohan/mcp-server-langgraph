"""
AI UX Endpoints

Provides endpoints for AI-powered UX features:
- Progressive disclosure analysis
- Empty state suggestions
- Smart nudge recommendations
- Error recovery analysis
- Onboarding personalization
- HEART metrics insights
- Persona behavior analysis

LLM Integration:
- Uses AIUXService with LLM for intelligent responses
- Falls back to heuristics when LLM unavailable
- Controlled by FF_ENABLE_AI_SUGGESTIONS feature flag

Reference: UX Audit Plan - Phase 6 AI-Native Integration
"""

from enum import Enum
from typing import TYPE_CHECKING, Any

from fastapi import APIRouter, Depends
from pydantic import BaseModel, Field

from mcp_server_langgraph.observability.telemetry import logger

# Note: Rate limiting for AI UX endpoints is configured via PATH_RATE_LIMITS
# in middleware/rate_limiter.py as "ai_ux": "30/minute". The global tier-based
# rate limiting applies through default_limits. Decorator-based per-endpoint
# limits were removed due to FastAPI/slowapi response handling incompatibility.

if TYPE_CHECKING:
    from mcp_server_langgraph.api.v1.ai_ux_service import AIUXService

ai_ux_router = APIRouter(tags=["ai-ux"])

# =============================================================================
# Service Singleton
# =============================================================================

_ai_ux_service: "AIUXService | None" = None


def get_ai_ux_service() -> "AIUXService":
    """
    Get the AI UX service instance.

    Creates the service lazily with LLM support if enabled.
    Falls back to heuristics-only mode if LLM unavailable.
    """
    global _ai_ux_service
    if _ai_ux_service is None:
        from mcp_server_langgraph.api.v1.ai_ux_service import AIUXService
        from mcp_server_langgraph.core.config import settings

        llm_factory = None
        if getattr(settings, "ff_enable_ai_suggestions", True):
            try:
                from mcp_server_langgraph.llm.factory import create_llm_from_config

                llm_factory = create_llm_from_config(settings)
                logger.info("AI UX service initialized with LLM support")
            except Exception as e:
                logger.warning(f"Failed to create LLM factory for AI UX: {e}")

        _ai_ux_service = AIUXService(llm_factory=llm_factory, settings=settings)
    return _ai_ux_service


def set_ai_ux_service(service: "AIUXService | None") -> None:
    """Set the AI UX service instance (for testing)."""
    global _ai_ux_service
    _ai_ux_service = service


# =============================================================================
# Enums
# =============================================================================


class DisclosureLevel(str, Enum):
    """User disclosure/expertise levels."""

    BEGINNER = "beginner"
    INTERMEDIATE = "intermediate"
    ADVANCED = "advanced"
    EXPERT = "expert"


class ErrorCategory(str, Enum):
    """Error classification categories."""

    NETWORK = "network"
    AUTHENTICATION = "authentication"
    AUTHORIZATION = "authorization"
    VALIDATION = "validation"
    SERVER = "server"
    CLIENT = "client"
    TIMEOUT = "timeout"
    QUOTA = "quota"
    UNKNOWN = "unknown"


class SuggestionAction(str, Enum):
    """Action types for suggestions."""

    NAVIGATE = "navigate"
    MODAL = "modal"
    EXECUTE = "execute"
    RETRY = "retry"
    WAIT = "wait"
    SIMPLIFY = "simplify"
    CONTACT = "contact"


# =============================================================================
# Request/Response Models - Disclosure
# =============================================================================


class SessionHistoryItem(BaseModel):
    """A single session history entry."""

    page: str
    duration_ms: int = 0


class DisclosureAnalyzeRequest(BaseModel):
    """Request for disclosure level analysis."""

    user_id: str = Field(..., description="User identifier")
    session_history: list[SessionHistoryItem] = Field(default_factory=list, description="Recent session history")
    feature_usage: dict[str, int] = Field(default_factory=dict, description="Feature usage counts")


class DisclosureAnalyzeResponse(BaseModel):
    """Response from disclosure level analysis."""

    current_level: DisclosureLevel
    recommended_level: DisclosureLevel
    confidence: float = Field(ge=0, le=1)
    unlock_features: list[str] = Field(default_factory=list)
    personalized_message: str | None = None


# =============================================================================
# Request/Response Models - Empty State
# =============================================================================


class EmptyStateSuggestionsRequest(BaseModel):
    """Request for empty state suggestions."""

    context: str = Field(..., description="Page context (e.g., 'workflows', 'sessions')")
    persona: str = Field(..., description="User persona")
    session_id: str | None = None
    history: list[dict[str, Any]] = Field(default_factory=list)


class EmptyStateSuggestion(BaseModel):
    """A single empty state suggestion."""

    text: str
    action: SuggestionAction
    target: str | None = None
    confidence: float = Field(ge=0, le=1, default=0.8)
    category: str = "default"


class EmptyStateSuggestionsResponse(BaseModel):
    """Response with empty state suggestions."""

    suggestions: list[EmptyStateSuggestion]


# =============================================================================
# Request/Response Models - Nudges
# =============================================================================


class NudgeContext(BaseModel):
    """Current user context for nudge decisions."""

    page: str
    action: str = "viewing"
    time_on_page: int = 0


class NudgeHistoryItem(BaseModel):
    """A single nudge history entry."""

    id: str
    shown_at: str
    action: str = "dismissed"  # 'accepted' | 'dismissed'


class NudgeRecommendRequest(BaseModel):
    """Request for nudge recommendation."""

    user_id: str
    current_context: NudgeContext
    nudge_history: list[NudgeHistoryItem] = Field(default_factory=list)


class Nudge(BaseModel):
    """A nudge to show to the user."""

    id: str
    type: str = "tooltip"  # 'tooltip' | 'spotlight' | 'banner'
    target_element: str | None = None
    message: str
    priority: str = "medium"  # 'low' | 'medium' | 'high'
    show_after_ms: int = 0


class NudgeRecommendResponse(BaseModel):
    """Response with nudge recommendation."""

    should_show: bool
    nudge: Nudge | None = None
    confidence: float = Field(ge=0, le=1, default=0.5)


# =============================================================================
# Request/Response Models - Error Analysis
# =============================================================================


class ErrorInfo(BaseModel):
    """Information about an error."""

    message: str
    name: str = "Error"
    stack_trace: str | None = None


class UserContext(BaseModel):
    """User context for error analysis."""

    persona: str | None = None
    session_id: str | None = None
    recent_actions: list[str] = Field(default_factory=list)


class ErrorAnalyzeRequest(BaseModel):
    """Request for error analysis."""

    error: ErrorInfo
    user_context: UserContext | None = None


class ErrorClassification(BaseModel):
    """Error classification result."""

    category: ErrorCategory
    subcategory: str = "general"
    confidence: float = Field(ge=0, le=1)


class RecoverySuggestion(BaseModel):
    """A recovery suggestion for an error."""

    action: SuggestionAction
    label: str
    guidance: str | None = None
    estimated_success: float = Field(ge=0, le=1, default=0.7)
    wait_time: int | None = None


class SimilarIssue(BaseModel):
    """A similar resolved issue."""

    id: str
    resolution: str
    success_rate: float = Field(ge=0, le=1)


class ErrorAnalyzeResponse(BaseModel):
    """Response from error analysis."""

    classification: ErrorClassification
    root_cause: str
    suggestions: list[RecoverySuggestion]
    similar_issues: list[SimilarIssue] = Field(default_factory=list)


# =============================================================================
# Request/Response Models - Onboarding
# =============================================================================


class SignupContext(BaseModel):
    """Context from signup."""

    referrer: str | None = None
    utm_source: str | None = None


class OnboardingPersonalizeRequest(BaseModel):
    """Request for onboarding personalization."""

    user_id: str
    initial_actions: list[str] = Field(default_factory=list)
    signup_context: SignupContext | None = None


class OnboardingStep(BaseModel):
    """A step in the onboarding path."""

    step: str
    template: str | None = None
    guided: bool = False
    focus: str | None = None


class OnboardingPersonalizeResponse(BaseModel):
    """Response with personalized onboarding."""

    detected_intent: str
    confidence: float = Field(ge=0, le=1)
    recommended_path: list[OnboardingStep]
    skip_steps: list[str] = Field(default_factory=list)
    persona_prediction: str | None = None


# =============================================================================
# Request/Response Models - Metrics Insights
# =============================================================================


class MetricInsight(BaseModel):
    """A single metric insight."""

    type: str  # 'anomaly' | 'trend' | 'pattern'
    dimension: str  # HEART dimension
    message: str
    severity: str = "info"  # 'info' | 'warning' | 'critical'
    sentiment: str = "neutral"  # 'positive' | 'negative' | 'neutral'
    suggested_actions: list[str] = Field(default_factory=list)
    detected_at: str | None = None


class MetricPrediction(BaseModel):
    """A metric prediction."""

    metric: str
    current: float
    predicted: float
    confidence: float = Field(ge=0, le=1)
    drivers: list[str] = Field(default_factory=list)


class MetricsInsightsResponse(BaseModel):
    """Response with metrics insights."""

    insights: list[MetricInsight]
    predictions: list[MetricPrediction]


# =============================================================================
# Request/Response Models - Persona Analysis
# =============================================================================


class PersonaAnalyzeRequest(BaseModel):
    """Request for persona analysis."""

    user_id: str
    assigned_persona: str
    recent_actions: list[str] = Field(default_factory=list)
    feature_usage: dict[str, int] = Field(default_factory=dict)


class UIAdaptation(BaseModel):
    """A UI adaptation recommendation."""

    feature: str
    action: str  # 'unlock' | 'promote' | 'hide'


class PersonaAnalyzeResponse(BaseModel):
    """Response from persona analysis."""

    assigned_persona: str
    detected_persona: str
    confidence: float = Field(ge=0, le=1)
    behavior_signals: list[str]
    recommendation: str | None = None
    ui_adaptations: list[UIAdaptation] = Field(default_factory=list)


# =============================================================================
# Request/Response Models - Composite Analysis
# =============================================================================


class CompositeAnalysisRequest(BaseModel):
    """Request for composite analysis across multiple AI UX services."""

    user_id: str = Field(..., description="User identifier")
    session_id: str = Field(..., description="Session identifier for context storage")
    include_persona: bool = Field(default=True, description="Include persona analysis")
    include_disclosure: bool = Field(default=True, description="Include disclosure analysis")
    include_error: bool = Field(default=False, description="Include error analysis")
    persona_data: dict[str, Any] | None = Field(default=None, description="Data for persona analysis")
    disclosure_data: dict[str, Any] | None = Field(default=None, description="Data for disclosure analysis")
    error_data: dict[str, Any] | None = Field(default=None, description="Error data for analysis")


class CompositeAnalysisResponse(BaseModel):
    """Response from composite analysis with cross-service insights."""

    user_id: str
    session_id: str
    persona_result: PersonaAnalyzeResponse | None = None
    disclosure_result: DisclosureAnalyzeResponse | None = None
    error_result: ErrorAnalyzeResponse | None = None
    cross_insights: list[str] = Field(
        default_factory=list,
        description="Insights derived from combining multiple analyses",
    )
    confidence: float = Field(ge=0, le=1, description="Overall confidence score for the composite analysis")


class BatchCompositeRequest(BaseModel):
    """Request for batch composite analysis."""

    requests: list[CompositeAnalysisRequest] = Field(
        ..., description="List of composite analysis requests", min_length=1, max_length=50
    )
    max_concurrency: int = Field(default=5, ge=1, le=20, description="Maximum concurrent requests")


class BatchCompositeErrorResult(BaseModel):
    """Error result for a failed batch item."""

    error: str
    user_id: str


class BatchCompositeResponse(BaseModel):
    """Response from batch composite analysis."""

    results: list[CompositeAnalysisResponse | BatchCompositeErrorResult] = Field(
        ..., description="Results for each request (may include errors)"
    )
    total: int = Field(..., description="Total number of requests processed")
    successful: int = Field(..., description="Number of successful analyses")
    failed: int = Field(..., description="Number of failed analyses")


# =============================================================================
# Endpoints
# =============================================================================


@ai_ux_router.post(
    "/disclosure/analyze",
    response_model=DisclosureAnalyzeResponse,
    summary="Analyze user disclosure level",
    description="Analyzes user behavior to recommend appropriate UI complexity level.",
)
async def analyze_disclosure(
    body: DisclosureAnalyzeRequest,
    service: "AIUXService" = Depends(get_ai_ux_service),
) -> DisclosureAnalyzeResponse:
    """
    Analyze user's disclosure level based on behavior patterns.

    Uses AIUXService for progressive disclosure analysis.
    """
    logger.info(f"Analyzing disclosure level for user {body.user_id}")
    return await service.analyze_disclosure(body)


@ai_ux_router.post(
    "/empty-state/suggestions",
    response_model=EmptyStateSuggestionsResponse,
    summary="Get empty state suggestions",
    description="Returns contextual suggestions for empty state pages. Uses LLM when available for personalized suggestions.",
)
async def get_empty_state_suggestions(
    body: EmptyStateSuggestionsRequest,
    service: "AIUXService" = Depends(get_ai_ux_service),
) -> EmptyStateSuggestionsResponse:
    """
    Generate contextual empty state suggestions.

    Uses LLM for personalized suggestions when available,
    falls back to static context-based suggestions otherwise.
    """
    logger.info(f"Generating empty state suggestions for context: {body.context}")
    return await service.get_empty_state_suggestions(body)


@ai_ux_router.post(
    "/nudges/recommend",
    response_model=NudgeRecommendResponse,
    summary="Get nudge recommendation",
    description="Returns a contextual nudge recommendation based on user behavior.",
)
async def recommend_nudge(
    body: NudgeRecommendRequest,
    service: "AIUXService" = Depends(get_ai_ux_service),
) -> NudgeRecommendResponse:
    """
    Recommend a contextual nudge for the user.

    Uses AIUXService for smart nudge recommendations.
    """
    logger.info(f"Generating nudge recommendation for user {body.user_id}")
    return await service.recommend_nudge(body)


@ai_ux_router.post(
    "/errors/analyze",
    response_model=ErrorAnalyzeResponse,
    summary="Analyze error for recovery",
    description="Analyzes an error and provides recovery suggestions. Uses LLM when available for intelligent analysis.",
)
async def analyze_error(
    body: ErrorAnalyzeRequest,
    service: "AIUXService" = Depends(get_ai_ux_service),
) -> ErrorAnalyzeResponse:
    """
    Analyze an error and provide recovery suggestions.

    Uses LLM for intelligent error classification when available,
    falls back to rule-based heuristics otherwise.
    """
    logger.info(f"Analyzing error: {body.error.name} - {body.error.message}")
    return await service.analyze_error(body.error, body.user_context)


@ai_ux_router.post(
    "/onboarding/personalize",
    response_model=OnboardingPersonalizeResponse,
    summary="Personalize onboarding",
    description="Returns a personalized onboarding path based on detected intent.",
)
async def personalize_onboarding(
    body: OnboardingPersonalizeRequest,
    service: "AIUXService" = Depends(get_ai_ux_service),
) -> OnboardingPersonalizeResponse:
    """
    Generate personalized onboarding path.

    Uses AIUXService for intent-based onboarding personalization.
    """
    logger.info(f"Personalizing onboarding for user {body.user_id}")
    return await service.personalize_onboarding(body)


@ai_ux_router.get(
    "/metrics/insights",
    response_model=MetricsInsightsResponse,
    summary="Get HEART metrics insights",
    description="Returns AI-generated insights from HEART metrics data.",
)
async def get_metrics_insights(
    service: "AIUXService" = Depends(get_ai_ux_service),
) -> MetricsInsightsResponse:
    """
    Generate insights from HEART metrics.

    Uses AIUXService for AI-powered metrics analysis.
    """
    logger.info("Generating HEART metrics insights")
    return await service.get_metrics_insights()


@ai_ux_router.post(
    "/persona/analyze",
    response_model=PersonaAnalyzeResponse,
    summary="Analyze user persona fit",
    description="Analyzes user behavior to detect actual persona. Uses LLM when available for nuanced analysis.",
)
async def analyze_persona(
    body: PersonaAnalyzeRequest,
    service: "AIUXService" = Depends(get_ai_ux_service),
) -> PersonaAnalyzeResponse:
    """
    Analyze user behavior to detect persona fit.

    Uses LLM for nuanced behavior detection when available,
    falls back to pattern matching otherwise.
    """
    logger.info(f"Analyzing persona for user {body.user_id}")
    return await service.analyze_persona(body)


@ai_ux_router.post(
    "/composite/analyze",
    response_model=CompositeAnalysisResponse,
    summary="Run composite analysis",
    description="Runs multiple AI UX analyses in parallel and provides cross-service insights.",
)
async def composite_analyze(
    body: CompositeAnalysisRequest,
    service: "AIUXService" = Depends(get_ai_ux_service),
) -> CompositeAnalysisResponse:
    """
    Run composite analysis across multiple AI UX services.

    Orchestrates persona, disclosure, and error analyses in parallel,
    stores results to session context, and generates cross-service insights.
    """
    logger.info(f"Running composite analysis for user {body.user_id}")
    return await service.run_composite_analysis(body)


@ai_ux_router.post(
    "/composite/stream",
    summary="Stream composite analysis",
    description="Streams composite analysis results as Server-Sent Events.",
)
async def stream_composite_analyze(
    body: CompositeAnalysisRequest,
    service: "AIUXService" = Depends(get_ai_ux_service),
) -> Any:
    """
    Stream composite analysis results as they complete.

    Yields Server-Sent Events for each analysis as it completes,
    followed by a final complete result event.
    """
    from starlette.responses import StreamingResponse

    async def event_generator() -> Any:
        async for event in service.stream_composite_analysis(body):
            import json

            yield f"data: {json.dumps(event)}\n\n"

    logger.info(f"Streaming composite analysis for user {body.user_id}")
    return StreamingResponse(
        event_generator(),
        media_type="text/event-stream",
    )


@ai_ux_router.post(
    "/composite/batch",
    response_model=BatchCompositeResponse,
    summary="Batch composite analysis",
    description="Processes multiple composite analysis requests in parallel with configurable concurrency.",
)
async def batch_composite_analyze(
    body: BatchCompositeRequest,
    service: "AIUXService" = Depends(get_ai_ux_service),
) -> BatchCompositeResponse:
    """
    Process multiple composite analysis requests in parallel.

    Executes composite analysis for multiple users concurrently,
    with configurable concurrency limit to avoid overwhelming
    LLM providers. Returns results for all requests including
    any that failed.
    """
    logger.info(
        f"Running batch composite analysis for {len(body.requests)} requests",
        extra={"request_count": len(body.requests), "max_concurrency": body.max_concurrency},
    )

    results = await service.batch_composite_analysis(
        requests=body.requests,
        max_concurrency=body.max_concurrency,
    )

    # Convert dict errors to BatchCompositeErrorResult
    processed_results: list[CompositeAnalysisResponse | BatchCompositeErrorResult] = []
    for result in results:
        if isinstance(result, dict) and "error" in result:
            processed_results.append(
                BatchCompositeErrorResult(error=result["error"], user_id=result.get("user_id", "unknown"))
            )
        else:
            processed_results.append(result)  # type: ignore[arg-type]

    successful = sum(1 for r in processed_results if isinstance(r, CompositeAnalysisResponse))
    failed = len(processed_results) - successful

    return BatchCompositeResponse(
        results=processed_results,
        total=len(processed_results),
        successful=successful,
        failed=failed,
    )


# =============================================================================
# WebSocket Endpoint
# =============================================================================


@ai_ux_router.websocket("/ws/suggestions")
async def websocket_suggestions(
    websocket: Any,
    service: "AIUXService" = Depends(get_ai_ux_service),
) -> None:
    """
    WebSocket endpoint for real-time AI suggestions.

    Maintains a persistent connection for streaming suggestions
    based on user context updates.

    Protocol:
    - Client sends: {"type": "request_suggestions", "context": {...}}
    - Server sends: {"type": "suggestions", "data": [...]}
    """

    # Accept the WebSocket connection
    await websocket.accept()

    # Extract user_id from query params or use anonymous
    user_id = websocket.query_params.get("user_id", "anonymous")

    logger.info(f"WebSocket connection established for user {user_id}")

    try:
        await service.handle_websocket_connection(websocket, user_id)
    except Exception as e:
        logger.error(f"WebSocket error for user {user_id}: {e}")
    finally:
        logger.info(f"WebSocket connection closed for user {user_id}")
