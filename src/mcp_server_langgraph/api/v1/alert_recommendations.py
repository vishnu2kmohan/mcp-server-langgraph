"""
Alert Recommendations REST API.

Provides endpoints for retrieving and regenerating AI-powered alert recommendations.

Endpoints:
- GET /alerts - List all alerts with optional filtering
- GET /alerts/{alert_id}/recommendation - Get recommendation for an alert
- POST /alerts/{alert_id}/recommendation/regenerate - Force regenerate recommendation

Rate Limiting:
- GET /alerts/{alert_id}/recommendation: 60 RPM (on-demand recommendations)
- POST /alerts/{alert_id}/recommendation/regenerate: 20 RPM (force regenerate)

Reference: ADR-0026 - Comprehensive Client Resilience Patterns
"""

import logging
import os
import time
from typing import Any

from fastapi import APIRouter, Depends, HTTPException
from litellm import acompletion
from pydantic import BaseModel, Field
from typing import Literal

from mcp_server_langgraph.alerts.ai_recommendation import (
    AIRecommendation,
    AIRecommendationService,
)
from mcp_server_langgraph.alerts.correlation import (
    AlertCorrelationEngine,
    CorrelatedAlert,
    PatternType,
)
from mcp_server_langgraph.alerts.stores import (
    AlertStoreProtocol,
    InMemoryAlertStore,
)
from mcp_server_langgraph.core.config import settings
from mcp_server_langgraph.observability.query.interfaces import (
    Alert,
    AlertSeverity,
    AlertState,
)
from mcp_server_langgraph.alerts.metrics import (
    record_rate_limit_exceeded,
    record_recommendation_generated,
    record_recommendation_regenerated,
    record_recommendation_request,
)
from mcp_server_langgraph.resilience.rate_limit import TokenBucket

logger = logging.getLogger(__name__)

alert_recommendation_router = APIRouter(prefix="/alerts", tags=["alerts"])


# =============================================================================
# Rate Limiting Configuration
# =============================================================================
# Token bucket rate limiters for AI recommendation endpoints.
# These prevent overwhelming the LLM backend with too many requests.
# Configurable via environment variables.

# GET /alerts/{alert_id}/recommendation - 60 RPM (1 req/sec) by default
# For on-demand recommendation requests (cached responses bypass this)
_RECOMMENDATION_GET_RPM = float(os.getenv("RATE_LIMIT_RECOMMENDATION_GET_RPM", "60"))
_recommendation_get_bucket: TokenBucket | None = None

# POST /alerts/{alert_id}/recommendation/regenerate - 20 RPM by default
# Force regenerate is more expensive, so lower rate limit
_RECOMMENDATION_REGENERATE_RPM = float(os.getenv("RATE_LIMIT_RECOMMENDATION_REGENERATE_RPM", "20"))
_recommendation_regenerate_bucket: TokenBucket | None = None


def _get_recommendation_get_bucket() -> TokenBucket:
    """Get or create the token bucket for recommendation GET requests."""
    global _recommendation_get_bucket
    if _recommendation_get_bucket is None:
        refill_rate = _RECOMMENDATION_GET_RPM / 60.0
        capacity = refill_rate * 10  # 10 seconds burst
        _recommendation_get_bucket = TokenBucket(capacity=capacity, refill_rate=refill_rate)
        logger.info(f"Created recommendation GET rate limiter: {_RECOMMENDATION_GET_RPM} RPM, burst capacity {capacity:.1f}")
    return _recommendation_get_bucket


def _get_recommendation_regenerate_bucket() -> TokenBucket:
    """Get or create the token bucket for recommendation regenerate requests."""
    global _recommendation_regenerate_bucket
    if _recommendation_regenerate_bucket is None:
        refill_rate = _RECOMMENDATION_REGENERATE_RPM / 60.0
        capacity = refill_rate * 5  # 5 seconds burst (smaller for expensive operation)
        _recommendation_regenerate_bucket = TokenBucket(capacity=capacity, refill_rate=refill_rate)
        logger.info(
            f"Created recommendation regenerate rate limiter: {_RECOMMENDATION_REGENERATE_RPM} RPM, "
            f"burst capacity {capacity:.1f}"
        )
    return _recommendation_regenerate_bucket


def reset_recommendation_rate_limiters() -> None:
    """Reset rate limiters (for testing)."""
    global _recommendation_get_bucket, _recommendation_regenerate_bucket
    _recommendation_get_bucket = None
    _recommendation_regenerate_bucket = None


# =============================================================================
# Response Models
# =============================================================================


class AlertListResponse(BaseModel):
    """Response model for listing alerts."""

    alerts: list[Alert] = Field(default_factory=list, description="List of alerts")
    count: int = Field(0, description="Total count of alerts returned")


# =============================================================================
# Alert Store (using store abstraction from alerts.stores)
# =============================================================================

# Re-export for backward compatibility
AlertStore = InMemoryAlertStore


# =============================================================================
# LLM Factory for Recommendations
# =============================================================================


class RecommendationLLM:
    """
    LLM wrapper for AI recommendations.

    Implements LLMFactoryProtocol using LiteLLM for flexible provider support.
    """

    def __init__(
        self,
        model_name: str = "gemini-2.5-flash",
        temperature: float = 0.3,
        max_tokens: int = 2048,
        timeout: int = 60,
    ) -> None:
        """
        Initialize the recommendation LLM wrapper.

        Args:
            model_name: LLM model to use for recommendations.
            temperature: Sampling temperature (lower for consistency).
            max_tokens: Maximum tokens for response.
            timeout: Request timeout in seconds.
        """
        self.model_name = model_name
        self.temperature = temperature
        self.max_tokens = max_tokens
        self.timeout = timeout

    async def acompletion(
        self,
        messages: list[dict[str, str]],
        **kwargs: Any,
    ) -> Any:
        """
        Generate completion from LLM.

        Args:
            messages: List of message dicts with role and content.
            **kwargs: Additional parameters for LiteLLM.

        Returns:
            LiteLLM ModelResponse with choices.
        """
        return await acompletion(
            model=self.model_name,
            messages=messages,
            temperature=kwargs.get("temperature", self.temperature),
            max_tokens=kwargs.get("max_tokens", self.max_tokens),
            timeout=kwargs.get("timeout", self.timeout),
        )


def create_recommendation_llm() -> RecommendationLLM:
    """
    Create an LLM factory for AI recommendations.

    Uses settings from configuration to determine model parameters.

    Returns:
        RecommendationLLM instance configured for alert recommendations.
    """
    try:
        model_name = settings.model_name
    except Exception:
        # Fallback to default if settings unavailable
        model_name = "gemini-2.5-flash"

    return RecommendationLLM(
        model_name=model_name,
        temperature=0.3,  # Lower temp for consistent recommendations
        max_tokens=2048,
        timeout=60,
    )


# =============================================================================
# Global Instances
# =============================================================================

_alert_store: AlertStoreProtocol | None = None
_recommendation_service: AIRecommendationService | None = None
_alert_orchestrator: "AlertOrchestrator | None" = None

# Type for AlertOrchestrator (imported lazily to avoid circular imports)
from typing import TYPE_CHECKING as _TYPE_CHECKING

if _TYPE_CHECKING:
    from mcp_server_langgraph.agents.alert_orchestrator import AlertOrchestrator


def get_alert_orchestrator() -> "AlertOrchestrator | None":
    """Get the AlertOrchestrator instance for parallel alert analysis."""
    global _alert_orchestrator
    return _alert_orchestrator


def set_alert_orchestrator(orchestrator: "AlertOrchestrator | None") -> None:
    """Set the AlertOrchestrator instance (for testing or dependency injection)."""
    global _alert_orchestrator
    _alert_orchestrator = orchestrator


def get_alert_store() -> AlertStoreProtocol:
    """Get the alert store instance."""
    global _alert_store
    if _alert_store is None:
        _alert_store = InMemoryAlertStore()
    return _alert_store


def set_alert_store(store: AlertStoreProtocol | None) -> None:
    """Set the alert store instance (for testing or PostgreSQL in production)."""
    global _alert_store
    _alert_store = store


def get_recommendation_service() -> AIRecommendationService:
    """
    Get the AI recommendation service instance with LLM and FeedbackStore configured.

    The FeedbackStore enables few-shot learning from past approved remediations
    and constraint learning from rejection patterns.
    """
    global _recommendation_service
    if _recommendation_service is None:
        from mcp_server_langgraph.api.v1.remediation_approvals import get_feedback_store

        llm = create_recommendation_llm()
        feedback_store = get_feedback_store()
        _recommendation_service = AIRecommendationService(
            llm_factory=llm,
            feedback_store=feedback_store,
        )
    return _recommendation_service


def set_recommendation_service(service: AIRecommendationService | None) -> None:
    """Set the AI recommendation service instance (for testing)."""
    global _recommendation_service
    _recommendation_service = service


# =============================================================================
# API Endpoints
# =============================================================================


@alert_recommendation_router.get(
    "/",
    response_model=AlertListResponse,  # noqa: FAST001 - explicit for OpenAPI docs
    summary="List alerts",
    description="Get all alerts with optional filtering by severity and state.",
)
async def list_alerts(
    alert_store: AlertStoreProtocol = Depends(get_alert_store),
    severity: list[AlertSeverity] | None = None,
    state: list[AlertState] | None = None,
) -> AlertListResponse:
    """
    List all alerts with optional filtering.

    Args:
        alert_store: The alert store for retrieving alerts.
        severity: Optional list of severity levels to filter by.
        state: Optional list of alert states to filter by.

    Returns:
        AlertListResponse with list of alerts and count.
    """
    all_alerts = await alert_store.list_alerts()

    # Apply filters
    filtered_alerts = all_alerts

    if severity:
        filtered_alerts = [a for a in filtered_alerts if a.severity in severity]

    if state:
        filtered_alerts = [a for a in filtered_alerts if a.state in state]

    return AlertListResponse(
        alerts=filtered_alerts,
        count=len(filtered_alerts),
    )


@alert_recommendation_router.get(
    "/{alert_id}/recommendation",
    response_model=AIRecommendation,  # noqa: FAST001 - explicit for OpenAPI docs
    summary="Get alert recommendation",
    description="Get AI-generated recommendation for an alert.",
)
async def get_alert_recommendation(
    alert_id: str,
    service: AIRecommendationService = Depends(get_recommendation_service),
    alert_store: AlertStore = Depends(get_alert_store),
) -> AIRecommendation:
    """
    Get the AI recommendation for a specific alert.

    First checks the cache for an existing recommendation.
    If not found, generates a new recommendation (rate-limited).

    Args:
        alert_id: The alert ID to get recommendation for.
        service: The AI recommendation service.
        alert_store: The alert store for looking up alert details.

    Returns:
        AIRecommendation with root cause analysis and remediation steps.

    Raises:
        HTTPException: 404 if alert not found, 429 if rate limited.
    """
    # Check cache first (no rate limit for cached responses)
    cached = await service.get_cached_recommendation(alert_id)
    if cached:
        logger.debug(f"Returning cached recommendation for alert {alert_id}")
        record_recommendation_request(alert_id, cached=True)
        return cached

    # Rate limit new recommendation generation
    bucket = _get_recommendation_get_bucket()
    if not bucket.try_acquire():
        logger.warning(
            f"Rate limit exceeded for recommendation GET: {alert_id}",
            extra={"alert_id": alert_id, "tokens_available": bucket.tokens},
        )
        record_rate_limit_exceeded("get_recommendation")
        raise HTTPException(
            status_code=429,
            detail="Rate limit exceeded for recommendation requests. Please try again later.",
            headers={"Retry-After": "60"},
        )

    # Look up alert details
    alert = await alert_store.get_alert(alert_id)
    if not alert:
        raise HTTPException(
            status_code=404,
            detail=f"Alert {alert_id} not found",
        )

    # Generate new recommendation with metrics
    record_recommendation_request(alert_id, cached=False)
    start_time = time.monotonic()
    try:
        logger.info(f"Generating new recommendation for alert {alert_id}")
        recommendation = await service.generate_recommendation(alert)
        duration = time.monotonic() - start_time
        record_recommendation_generated(alert_id, duration, success=True)
        return recommendation
    except Exception:
        duration = time.monotonic() - start_time
        record_recommendation_generated(alert_id, duration, success=False)
        raise


@alert_recommendation_router.post(
    "/{alert_id}/recommendation/regenerate",
    response_model=AIRecommendation,  # noqa: FAST001 - explicit for OpenAPI docs
    summary="Regenerate alert recommendation",
    description="Force regenerate AI recommendation for an alert.",
)
async def regenerate_alert_recommendation(
    alert_id: str,
    service: AIRecommendationService = Depends(get_recommendation_service),
    alert_store: AlertStore = Depends(get_alert_store),
) -> AIRecommendation:
    """
    Force regenerate the AI recommendation for an alert.

    Bypasses the cache and generates a fresh recommendation (rate-limited).

    Args:
        alert_id: The alert ID to regenerate recommendation for.
        service: The AI recommendation service.
        alert_store: The alert store for looking up alert details.

    Returns:
        AIRecommendation with fresh root cause analysis and remediation steps.

    Raises:
        HTTPException: 404 if alert not found, 429 if rate limited.
    """
    # Rate limit regeneration (more expensive operation)
    bucket = _get_recommendation_regenerate_bucket()
    if not bucket.try_acquire():
        logger.warning(
            f"Rate limit exceeded for recommendation regenerate: {alert_id}",
            extra={"alert_id": alert_id, "tokens_available": bucket.tokens},
        )
        record_rate_limit_exceeded("regenerate_recommendation")
        raise HTTPException(
            status_code=429,
            detail="Rate limit exceeded for recommendation regeneration. Please try again later.",
            headers={"Retry-After": "180"},  # 3 minutes for regenerate
        )

    # Look up alert details
    alert = await alert_store.get_alert(alert_id)
    if not alert:
        raise HTTPException(
            status_code=404,
            detail=f"Alert {alert_id} not found",
        )

    # Generate new recommendation with force flag and metrics
    record_recommendation_regenerated(alert_id)
    start_time = time.monotonic()
    try:
        logger.info(f"Regenerating recommendation for alert {alert_id}")
        recommendation = await service.generate_recommendation(alert, force_regenerate=True)
        duration = time.monotonic() - start_time
        record_recommendation_generated(alert_id, duration, success=True)
        return recommendation
    except Exception:
        duration = time.monotonic() - start_time
        record_recommendation_generated(alert_id, duration, success=False)
        raise


# =============================================================================
# Correlation Request/Response Models
# =============================================================================


class CorrelateAlertsRequest(BaseModel):
    """Request model for alert correlation."""

    correlation_type: Literal["label", "time"] = Field(
        default="label",
        description="Type of correlation: 'label' for label-based, 'time' for time-based",
    )
    label_key: str | None = Field(
        default=None,
        description="Label key for label-based correlation (required if correlation_type='label')",
    )
    window_minutes: int = Field(
        default=5,
        ge=1,
        le=60,
        description="Time window in minutes for time-based correlation",
    )
    detect_patterns: bool = Field(
        default=False,
        description="Whether to detect patterns (cascading_failure, resource_exhaustion)",
    )
    identify_root_cause: bool = Field(
        default=False,
        description="Whether to identify root cause in correlation groups",
    )


class CorrelatedAlertResponse(BaseModel):
    """Response model for a correlated alert."""

    alert_id: str
    name: str
    severity: str
    started_at: str | None
    labels: dict[str, str]
    is_root_cause: bool = False


class PatternResultResponse(BaseModel):
    """Response model for pattern detection result."""

    pattern_type: str
    confidence: float
    description: str
    affected_alerts: list[str]


class CorrelationGroupResponse(BaseModel):
    """Response model for a correlation group."""

    group_key: str
    label_value: str | None = None
    alerts: list[CorrelatedAlertResponse]
    root_cause_id: str | None = None
    pattern: PatternResultResponse | None = None


class CorrelateAlertsResponse(BaseModel):
    """Response model for alert correlation."""

    groups: list[CorrelationGroupResponse] = Field(
        default_factory=list,
        description="List of correlation groups",
    )
    total_alerts: int = Field(0, description="Total alerts processed")
    total_groups: int = Field(0, description="Number of correlation groups found")


# =============================================================================
# Correlation Endpoint
# =============================================================================


@alert_recommendation_router.post(
    "/correlate",
    summary="Correlate alerts",
    description="Correlate alerts by label or time window with optional pattern detection.",
)
async def correlate_alerts(
    request: CorrelateAlertsRequest,
    alert_store: AlertStoreProtocol = Depends(get_alert_store),
) -> CorrelateAlertsResponse:
    """
    Correlate alerts to find related issues.

    Supports two correlation types:
    - label: Group alerts by a common label key
    - time: Group alerts within a time window

    Optionally detects patterns like cascading failures or resource exhaustion,
    and identifies the likely root cause within each group.

    Args:
        request: Correlation parameters.
        alert_store: The alert store for retrieving alerts.

    Returns:
        CorrelateAlertsResponse with correlation groups.

    Raises:
        HTTPException: 400 if label_key missing for label correlation.
    """
    # Validate label_key for label-based correlation
    if request.correlation_type == "label" and not request.label_key:
        raise HTTPException(
            status_code=400,
            detail="label_key is required for label-based correlation",
        )

    # Get all alerts from store
    all_alerts = await alert_store.list_alerts()

    if not all_alerts:
        return CorrelateAlertsResponse(
            groups=[],
            total_alerts=0,
            total_groups=0,
        )

    # Create correlation engine
    engine = AlertCorrelationEngine()

    # Convert to CorrelatedAlert format
    from datetime import UTC, datetime

    correlated_alerts = [
        CorrelatedAlert(
            alert_id=alert.alert_id,
            name=alert.name,
            severity=alert.severity.value if hasattr(alert.severity, "value") else str(alert.severity),
            started_at=alert.started_at or datetime.now(UTC),
            labels=alert.labels,
        )
        for alert in all_alerts
    ]

    # Perform correlation based on type
    if request.correlation_type == "label":
        groups = engine.correlate_by_label(correlated_alerts, request.label_key or "")
    else:
        groups = engine.correlate_by_time(correlated_alerts, request.window_minutes)

    # Build response groups
    response_groups: list[CorrelationGroupResponse] = []

    for group in groups:
        # Convert alerts to response format
        alert_responses = [
            CorrelatedAlertResponse(
                alert_id=a.alert_id,
                name=a.name,
                severity=a.severity,
                started_at=a.started_at.isoformat() if a.started_at else None,
                labels=a.labels,
                is_root_cause=False,
            )
            for a in group.alerts
        ]

        root_cause_id: str | None = None
        pattern_response: PatternResultResponse | None = None

        # Identify root cause if requested
        if request.identify_root_cause and group.alerts:
            root_cause = engine.identify_root_cause(group)
            if root_cause:
                root_cause_id = root_cause.alert_id
                # Mark root cause in alerts list
                for ar in alert_responses:
                    if ar.alert_id == root_cause.alert_id:
                        ar.is_root_cause = True

        # Detect patterns if requested
        if request.detect_patterns and group.alerts:
            pattern = engine.detect_pattern(group.alerts)
            if pattern and pattern.pattern_type != PatternType.UNKNOWN:
                pattern_response = PatternResultResponse(
                    pattern_type=pattern.pattern_type.value,
                    confidence=pattern.confidence,
                    description=pattern.description,
                    affected_alerts=pattern.affected_services,  # Map services to alerts
                )

        response_groups.append(
            CorrelationGroupResponse(
                group_key=group.group_id,
                label_value=group.label_value,
                alerts=alert_responses,
                root_cause_id=root_cause_id,
                pattern=pattern_response,
            )
        )

    logger.info(f"Correlated {len(all_alerts)} alerts into {len(response_groups)} groups (type={request.correlation_type})")

    return CorrelateAlertsResponse(
        groups=response_groups,
        total_alerts=len(all_alerts),
        total_groups=len(response_groups),
    )
