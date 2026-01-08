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

import warnings
from enum import Enum
from typing import TYPE_CHECKING, Annotated, Any, Literal

from fastapi import APIRouter, Depends
from pydantic import BaseModel, Field, field_validator, model_validator

from mcp_server_langgraph.auth.dependencies import get_current_user
from mcp_server_langgraph.core.numeric import safe_float

# Type alias for current user
CurrentUser = Annotated[dict[str, Any], Depends(get_current_user)]

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


# ADR-0091 Phase 9: Literal type for string-based disclosure levels (type safety without enum overhead)
DisclosureLevelStr = Literal["beginner", "intermediate", "advanced", "expert"]


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


class UserBehavior(BaseModel):
    """User behavior data for disclosure analysis (ADR-0091 Phase 9 aligned)."""

    feature_usage: dict[str, int] = Field(default_factory=dict)
    session_count: int = 0
    avg_session_duration: int | None = None


class DisclosureAnalyzeRequest(BaseModel):
    """Request for disclosure level analysis (ADR-0091 Phase 9 aligned).

    Aligned with frontend inline type in api/index.ts.
    Uses DisclosureLevelStr Literal type for type safety.
    """

    current_level: DisclosureLevelStr = Field(..., description="Current disclosure level")
    persona: str | None = Field(default=None, description="User persona")
    context: dict[str, Any] | None = Field(default=None, description="Additional context")
    user_behavior: UserBehavior | None = Field(default=None, description="User behavior data")


class DisclosureAnalyzeResponse(BaseModel):
    """Response from disclosure level analysis (ADR-0091 Phase 9 aligned).

    Aligned with frontend inline type in api/index.ts.
    Uses DisclosureLevelStr Literal type for type safety without enum overhead.
    """

    current_level: DisclosureLevelStr = Field(..., description="Current disclosure level")
    recommended_level: DisclosureLevelStr = Field(..., description="Recommended disclosure level")
    confidence: float = Field(ge=0, le=1)
    unlock_features: list[str] = Field(default_factory=list)
    personalized_message: str = Field(default="", description="Personalized message for the user")
    reasoning: str | None = Field(default=None, description="Optional reasoning for the recommendation")

    @field_validator("confidence", mode="before")
    @classmethod
    def validate_confidence(cls, v: float | None) -> float:
        """Convert NaN/Inf to 0.0 for JSON serialization safety."""
        return safe_float(v)


# =============================================================================
# Request/Response Models - Empty State
# =============================================================================


class EmptyStateActionType(str, Enum):
    """Action types for empty state suggestions (ADR-0091 Phase 9 aligned)."""

    NAVIGATE = "navigate"
    CREATE = "create"
    LEARN = "learn"
    IMPORT = "import"


class EmptyStateSuggestionsRequest(BaseModel):
    """Request for empty state suggestions (ADR-0091 Phase 9 aligned).

    Aligned with frontend inline type in api/index.ts.
    """

    context: str = Field(..., description="Page context (e.g., 'workflows', 'sessions')")
    persona: str | None = Field(default=None, description="User persona")
    previous_actions: list[str] | None = Field(default=None, description="Previous user actions")
    available_actions: list[str] | None = Field(default=None, description="Available actions in this context")


class EmptyStateSuggestion(BaseModel):
    """A single empty state suggestion (ADR-0091 Phase 9 aligned).

    Aligned with frontend inline type in api/index.ts.
    """

    title: str = Field(..., description="Suggestion title")
    description: str = Field(..., description="Suggestion description")
    action_type: EmptyStateActionType = Field(..., description="Type of action")
    action_target: str = Field(..., description="Target path or action identifier")
    icon: str | None = Field(default=None, description="Optional icon identifier")
    priority: int = Field(default=1, ge=1, description="Priority order (lower = higher priority)")


class EmptyStateSuggestionsResponse(BaseModel):
    """Response with empty state suggestions (ADR-0091 Phase 9 aligned).

    Aligned with frontend inline type in api/index.ts.
    """

    suggestions: list[EmptyStateSuggestion]
    context_hint: str | None = Field(default=None, description="Optional hint for the context")


# =============================================================================
# Request/Response Models - Nudges
# =============================================================================


class NudgeContext(BaseModel):
    """Current user context for nudge decisions."""

    page: str
    action: str = "viewing"
    time_on_page: int = 0


class NudgeHistoryItem(BaseModel):
    """A single nudge history entry (ADR-0091 Phase 9 aligned)."""

    nudge_id: str = Field(..., description="ID of the nudge that was shown")
    shown_at: str = Field(..., description="ISO timestamp when nudge was shown")
    action: str | None = Field(default=None, description="User action: 'accepted', 'dismissed', or null")


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

    @field_validator("confidence", mode="before")
    @classmethod
    def validate_confidence(cls, v: float | None) -> float:
        """Convert NaN/Inf to 0.5 (default) for JSON serialization safety."""
        return safe_float(v, default=0.5)


# =============================================================================
# Request/Response Models - Error Analysis
# =============================================================================


class ErrorRecoveryActionType(str, Enum):
    """Action types for error recovery (ADR-0091 Phase 9 aligned)."""

    AUTOMATIC = "automatic"
    MANUAL = "manual"
    CONTACT_SUPPORT = "contact_support"


class ErrorAnalyzeRequest(BaseModel):
    """Request for error analysis (ADR-0091 Phase 9 aligned).

    Aligned with frontend inline type in api/index.ts.
    """

    error_code: str = Field(..., description="Error code identifier")
    error_message: str = Field(..., description="Human-readable error message")
    context: dict[str, Any] | None = Field(default=None, description="Additional context about the error")
    stack_trace: str | None = Field(default=None, description="Stack trace if available")


class RecoveryStep(BaseModel):
    """A recovery step for an error (ADR-0091 Phase 9 aligned).

    Aligned with frontend inline type in api/index.ts.
    """

    step_number: int = Field(..., ge=1, description="Step order number")
    title: str = Field(..., description="Step title")
    description: str = Field(..., description="Step description")
    action_type: ErrorRecoveryActionType = Field(..., description="Type of action required")
    action_target: str | None = Field(default=None, description="Target path or action identifier")


class ErrorAnalyzeResponse(BaseModel):
    """Response from error analysis (ADR-0091 Phase 9 aligned).

    Aligned with frontend inline type in api/index.ts.
    """

    error_type: str = Field(..., description="Classified error type")
    recovery_steps: list[RecoveryStep] = Field(default_factory=list, description="Ordered recovery steps")
    auto_recoverable: bool = Field(..., description="Whether the error can be auto-recovered")
    suggested_action: str | None = Field(default=None, description="Primary suggested action")
    confidence: float = Field(ge=0, le=1, description="Confidence in the analysis")

    @field_validator("confidence", mode="before")
    @classmethod
    def validate_confidence(cls, v: float | None) -> float:
        """Convert NaN/Inf to 0.0 for JSON serialization safety."""
        return safe_float(v)


# Legacy models kept for backward compatibility (deprecated)
# These models will be removed in v4.0 (scheduled: 2025-06-01)
class ErrorInfo(BaseModel):
    """Information about an error.

    .. deprecated:: 3.0
        Use :class:`ErrorAnalyzeRequest` instead. This class will be removed in v4.0.
    """

    message: str
    name: str = "Error"
    stack_trace: str | None = None

    @model_validator(mode="after")
    def _emit_deprecation_warning(self) -> "ErrorInfo":
        warnings.warn(
            "ErrorInfo is deprecated. Use ErrorAnalyzeRequest instead. This class will be removed in v4.0 (2025-06-01).",
            DeprecationWarning,
            stacklevel=3,
        )
        return self


class UserContext(BaseModel):
    """User context for error analysis.

    .. deprecated:: 3.0
        Use ``ErrorAnalyzeRequest.context`` dict instead. This class will be removed in v4.0.
    """

    persona: str | None = None
    session_id: str | None = None
    recent_actions: list[str] = Field(default_factory=list)

    @model_validator(mode="after")
    def _emit_deprecation_warning(self) -> "UserContext":
        warnings.warn(
            "UserContext is deprecated. Use ErrorAnalyzeRequest.context dict instead. "
            "This class will be removed in v4.0 (2025-06-01).",
            DeprecationWarning,
            stacklevel=3,
        )
        return self


class ErrorClassification(BaseModel):
    """Error classification result.

    .. deprecated:: 3.0
        Use :class:`ErrorAnalyzeResponse` with ``error_type`` field instead.
        This class will be removed in v4.0.
    """

    category: ErrorCategory
    subcategory: str = "general"
    confidence: float = Field(ge=0, le=1)

    @model_validator(mode="after")
    def _emit_deprecation_warning(self) -> "ErrorClassification":
        warnings.warn(
            "ErrorClassification is deprecated. Use ErrorAnalyzeResponse.error_type instead. "
            "This class will be removed in v4.0 (2025-06-01).",
            DeprecationWarning,
            stacklevel=3,
        )
        return self


class RecoverySuggestion(BaseModel):
    """A recovery suggestion for an error.

    .. deprecated:: 3.0
        Use :class:`RecoveryStep` instead. This class will be removed in v4.0.
    """

    action: SuggestionAction
    label: str
    guidance: str | None = None
    estimated_success: float = Field(ge=0, le=1, default=0.7)
    wait_time: int | None = None

    @model_validator(mode="after")
    def _emit_deprecation_warning(self) -> "RecoverySuggestion":
        warnings.warn(
            "RecoverySuggestion is deprecated. Use RecoveryStep instead. This class will be removed in v4.0 (2025-06-01).",
            DeprecationWarning,
            stacklevel=3,
        )
        return self


class SimilarIssue(BaseModel):
    """A similar resolved issue.

    .. deprecated:: 3.0
        Not used in aligned ADR-0091 schema. This class will be removed in v4.0.
    """

    id: str
    resolution: str
    success_rate: float = Field(ge=0, le=1)

    @model_validator(mode="after")
    def _emit_deprecation_warning(self) -> "SimilarIssue":
        warnings.warn(
            "SimilarIssue is deprecated and not used in the aligned schema. This class will be removed in v4.0 (2025-06-01).",
            DeprecationWarning,
            stacklevel=3,
        )
        return self


# =============================================================================
# Request/Response Models - Onboarding
# =============================================================================


class SignupContext(BaseModel):
    """Context from signup (ADR-0091 Phase 9 aligned).

    Aligned with frontend inline type in api/index.ts.
    """

    referrer: str | None = Field(default=None, description="Referrer source")
    utm_source: str | None = Field(default=None, description="UTM source")
    utm_campaign: str | None = Field(default=None, description="UTM campaign")
    utm_medium: str | None = Field(default=None, description="UTM medium")


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

    @field_validator("confidence", mode="before")
    @classmethod
    def validate_confidence(cls, v: float | None) -> float:
        """Convert NaN/Inf to 0.0 for JSON serialization safety."""
        return safe_float(v)


# =============================================================================
# Request/Response Models - Metrics Insights
# =============================================================================


class MetricsInsightCategory(str, Enum):
    """Categories for metrics insights (ADR-0091 Phase 9 aligned)."""

    HAPPINESS = "happiness"
    ENGAGEMENT = "engagement"
    ADOPTION = "adoption"
    RETENTION = "retention"
    TASK_SUCCESS = "task_success"


class MetricsInsightTrend(str, Enum):
    """Trend directions for insights (ADR-0091 Phase 9 aligned)."""

    IMPROVING = "improving"
    STABLE = "stable"
    DECLINING = "declining"


class MetricsInsightPriority(str, Enum):
    """Priority levels for insights (ADR-0091 Phase 9 aligned)."""

    HIGH = "high"
    MEDIUM = "medium"
    LOW = "low"


class OverallHealth(str, Enum):
    """Overall health status (ADR-0091 Phase 9 aligned)."""

    EXCELLENT = "excellent"
    GOOD = "good"
    NEEDS_ATTENTION = "needs_attention"
    CRITICAL = "critical"


class MetricInsight(BaseModel):
    """A single metric insight (ADR-0091 Phase 9 aligned).

    Aligned with frontend inline type in api/index.ts.
    """

    category: MetricsInsightCategory = Field(..., description="HEART dimension category")
    title: str = Field(..., description="Insight title")
    description: str = Field(..., description="Insight description")
    trend: MetricsInsightTrend = Field(..., description="Current trend direction")
    priority: MetricsInsightPriority = Field(..., description="Priority level")
    suggested_action: str | None = Field(default=None, description="Suggested action to take")


class MetricsInsightsResponse(BaseModel):
    """Response with metrics insights (ADR-0091 Phase 9 aligned).

    Aligned with frontend inline type in api/index.ts.
    """

    happiness_score: float = Field(..., ge=0, le=10, description="Overall happiness score (0-10)")
    insights: list[MetricInsight] = Field(default_factory=list, description="List of metric insights")
    overall_health: OverallHealth = Field(..., description="Overall system health status")
    recommendations: list[str] = Field(default_factory=list, description="Actionable recommendations")

    @field_validator("happiness_score", mode="before")
    @classmethod
    def validate_happiness_score(cls, v: float | None) -> float:
        """Convert NaN/Inf to 0.0 for JSON serialization safety."""
        return safe_float(v)


# Legacy models kept for backward compatibility (deprecated)
# These models will be removed in v4.0 (scheduled: 2025-06-01)
class LegacyMetricInsight(BaseModel):
    """A single metric insight.

    .. deprecated:: 3.0
        Use :class:`MetricInsight` instead. This class will be removed in v4.0.
    """

    type: str  # 'anomaly' | 'trend' | 'pattern'
    dimension: str  # HEART dimension
    message: str
    severity: str = "info"  # 'info' | 'warning' | 'critical'
    sentiment: str = "neutral"  # 'positive' | 'negative' | 'neutral'
    suggested_actions: list[str] = Field(default_factory=list)
    detected_at: str | None = None

    @model_validator(mode="after")
    def _emit_deprecation_warning(self) -> "LegacyMetricInsight":
        warnings.warn(
            "LegacyMetricInsight is deprecated. Use MetricInsight instead. This class will be removed in v4.0 (2025-06-01).",
            DeprecationWarning,
            stacklevel=3,
        )
        return self


class MetricPrediction(BaseModel):
    """A metric prediction.

    .. deprecated:: 3.0
        Not used in aligned ADR-0091 schema. This class will be removed in v4.0.
    """

    metric: str
    current: float
    predicted: float
    confidence: float = Field(ge=0, le=1)
    drivers: list[str] = Field(default_factory=list)

    @model_validator(mode="after")
    def _emit_deprecation_warning(self) -> "MetricPrediction":
        warnings.warn(
            "MetricPrediction is deprecated and not used in the aligned schema. "
            "This class will be removed in v4.0 (2025-06-01).",
            DeprecationWarning,
            stacklevel=3,
        )
        return self


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

    @field_validator("confidence", mode="before")
    @classmethod
    def validate_confidence(cls, v: float | None) -> float:
        """Convert NaN/Inf to 0.0 for JSON serialization safety."""
        return safe_float(v)


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
# Request/Response Models - Artifact Naming
# =============================================================================


class ArtifactNameRequest(BaseModel):
    """Request for artifact name generation."""

    content: str = Field(..., description="The artifact content to analyze")
    type: str = Field(..., description="Artifact type (code, mermaid, svg, json, etc.)")
    language: str | None = Field(default=None, description="Programming language (for code artifacts)")


class ArtifactNameResponse(BaseModel):
    """Response with generated artifact name."""

    name: str = Field(..., description="Generated machine-friendly name")


# =============================================================================
# Endpoints
# =============================================================================


@ai_ux_router.post(
    "/disclosure/analyze",
    summary="Analyze user disclosure level",
    description="Analyzes user behavior to recommend appropriate UI complexity level.",
)
async def analyze_disclosure(
    current_user: CurrentUser,
    body: DisclosureAnalyzeRequest,
    service: "AIUXService" = Depends(get_ai_ux_service),
) -> DisclosureAnalyzeResponse:
    """
    Analyze user's disclosure level based on behavior patterns.

    Uses AIUXService for progressive disclosure analysis.
    ADR-0091 Phase 9: Request schema aligned with frontend.
    """
    user_id = current_user.get("sub", "unknown")
    logger.info(f"Analyzing disclosure level for user {user_id} at level {body.current_level}")
    return await service.analyze_disclosure(body)


@ai_ux_router.post(
    "/empty-state/suggestions",
    summary="Get empty state suggestions",
    description="Returns contextual suggestions for empty state pages. Uses LLM when available for personalized suggestions.",
)
async def get_empty_state_suggestions(
    current_user: CurrentUser,
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
    summary="Get nudge recommendation",
    description="Returns a contextual nudge recommendation based on user behavior.",
)
async def recommend_nudge(
    current_user: CurrentUser,
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
    summary="Analyze error for recovery",
    description="Analyzes an error and provides recovery suggestions. Uses LLM when available for intelligent analysis.",
)
async def analyze_error(
    current_user: CurrentUser,
    body: ErrorAnalyzeRequest,
    service: "AIUXService" = Depends(get_ai_ux_service),
) -> ErrorAnalyzeResponse:
    """
    Analyze an error and provide recovery suggestions.

    Uses LLM for intelligent error classification when available,
    falls back to rule-based heuristics otherwise.
    ADR-0091 Phase 9: Request schema aligned with frontend.
    """
    logger.info(f"Analyzing error: {body.error_code} - {body.error_message}")
    return await service.analyze_error(body)


@ai_ux_router.post(
    "/onboarding/personalize",
    summary="Personalize onboarding",
    description="Returns a personalized onboarding path based on detected intent.",
)
async def personalize_onboarding(
    current_user: CurrentUser,
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
    summary="Get HEART metrics insights",
    description="Returns AI-generated insights from HEART metrics data.",
)
async def get_metrics_insights(
    current_user: CurrentUser,
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
    summary="Analyze user persona fit",
    description="Analyzes user behavior to detect actual persona. Uses LLM when available for nuanced analysis.",
)
async def analyze_persona(
    current_user: CurrentUser,
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
    summary="Run composite analysis",
    description="Runs multiple AI UX analyses in parallel and provides cross-service insights.",
)
async def composite_analyze(
    current_user: CurrentUser,
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
    current_user: CurrentUser,
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
    summary="Batch composite analysis",
    description="Processes multiple composite analysis requests in parallel with configurable concurrency.",
)
async def batch_composite_analyze(
    current_user: CurrentUser,
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
# Artifact Naming Endpoint
# =============================================================================


@ai_ux_router.post(
    "/ai/artifact-name",
    summary="Generate artifact name",
    description="Generates a machine-friendly programmatic name from artifact content using heuristics and LLM.",
)
async def generate_artifact_name_endpoint(
    current_user: CurrentUser,
    body: ArtifactNameRequest,
) -> ArtifactNameResponse:
    """
    Generate an artifact name from content.

    Uses content-specific heuristics to extract meaningful names
    (function names, class names, diagram titles, etc.).
    Falls back to LLM when heuristics fail.
    """
    from mcp_server_langgraph.studio.ai.artifact_name_generator import (
        generate_artifact_name,
    )

    logger.info(f"Generating artifact name for type: {body.type}")
    name = await generate_artifact_name(
        content=body.content,
        content_type=body.type,
        language=body.language,
    )
    return ArtifactNameResponse(name=name)


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

    .. deprecated:: 3.0.0
       Use /api/v1/ws/ai/suggestions instead (via ws_router.py).
       This endpoint will be removed in v4.0.0.

    Maintains a persistent connection for streaming suggestions
    based on user context updates.

    Protocol:
    - Client sends: {"type": "request_suggestions", "context": {...}}
    - Server sends: {"type": "suggestions", "data": [...]}
    """
    # Emit deprecation warning at runtime
    warnings.warn(
        "The /api/v1/ai/ws/suggestions endpoint is deprecated. "
        "Use /api/v1/ws/ai/suggestions instead. "
        "This endpoint will be removed in v4.0.0.",
        DeprecationWarning,
        stacklevel=2,
    )

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
