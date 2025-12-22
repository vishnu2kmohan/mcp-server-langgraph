"""
AI-Powered Alert Recommendation Service.

Generates root cause analysis and remediation recommendations for infrastructure alerts
using LLM capabilities.

Features:
- Root cause analysis for alerts
- Step-by-step remediation recommendations
- Risk assessment
- Caching of recommendations
- Runbook reference integration
- Support for pre-computing (critical) and on-demand (warning) generation

Reference: ADR-0026 - Comprehensive Client Resilience Patterns
"""

import asyncio
import hashlib
import json
import logging
import uuid
from datetime import UTC, datetime
from typing import TYPE_CHECKING, Any, Protocol

from opentelemetry import trace
from pydantic import BaseModel, Field

from mcp_server_langgraph.observability.query.interfaces import Alert

if TYPE_CHECKING:
    from mcp_server_langgraph.agents.alert_orchestrator import AlertOrchestrator
    from mcp_server_langgraph.alerts.feedback import (
        FeedbackStore,
    )
    from mcp_server_langgraph.core.cache import CacheService

logger = logging.getLogger(__name__)
tracer = trace.get_tracer(__name__)

# ==============================================================================
# Runbook Registry for Auto-Linking
# ==============================================================================
# Maps alert patterns to runbook URLs for automatic linking.
# Reference: ADR-0026 - Comprehensive Client Resilience Patterns
# ==============================================================================

RUNBOOK_REGISTRY: dict[str, str] = {
    # Circuit Breaker Alerts
    "CircuitBreakerOpen": "https://docs/runbooks/RESILIENCE_OPERATIONS.md#circuit-breaker-open",
    "CircuitBreakerHalfOpen": "https://docs/runbooks/RESILIENCE_OPERATIONS.md#circuit-breaker-recovery",
    # Resource Alerts
    "HighMemoryUsage": "https://docs/runbooks/resource-management.md#memory-pressure",
    "HighCPUUsage": "https://docs/runbooks/resource-management.md#cpu-saturation",
    "DiskSpaceLow": "https://docs/runbooks/resource-management.md#disk-space",
    # Pod Alerts
    "PodCrashLooping": "https://docs/runbooks/kubernetes.md#pod-crash-loop",
    "PodOOMKilled": "https://docs/runbooks/kubernetes.md#oom-killed",
    "PodNotReady": "https://docs/runbooks/kubernetes.md#pod-not-ready",
    # Latency Alerts
    "HighLatency": "https://docs/runbooks/performance.md#latency-issues",
    "SLOLatencyP95Breach": "https://docs/runbooks/slo.md#latency-slo-breach",
    "SLOLatencyP99Breach": "https://docs/runbooks/slo.md#latency-slo-breach",
    # Database Alerts
    "PostgresConnectionPoolExhausted": "https://docs/runbooks/database.md#connection-pool",
    "RedisConnectionFailed": "https://docs/runbooks/database.md#redis-connectivity",
    # LLM Alerts
    "LLMRateLimited": "https://docs/runbooks/llm.md#rate-limiting",
    "LLMProviderDown": "https://docs/runbooks/llm.md#provider-outage",
    # Push Notification Alerts
    "PushDeliveryFailure": "https://docs/runbooks/push-notification-delivery.md",
    "PushSubscriptionExpiry": "https://docs/runbooks/push-subscription-management.md",
}

# Service-specific runbook mappings
SERVICE_RUNBOOK_REGISTRY: dict[str, str] = {
    "redis": "https://docs/runbooks/database.md#redis",
    "postgresql": "https://docs/runbooks/database.md#postgresql",
    "postgres": "https://docs/runbooks/database.md#postgresql",
    "keycloak": "https://docs/runbooks/authentication.md#keycloak",
    "openfga": "https://docs/runbooks/authorization.md#openfga",
}

# Default fallback runbook
FALLBACK_RUNBOOK_URL = "https://docs/runbooks/general-troubleshooting.md"


def register_runbook(alert_pattern: str, runbook_url: str) -> None:
    """
    Register a custom runbook mapping.

    Args:
        alert_pattern: The alert name pattern to match.
        runbook_url: The runbook URL to link.
    """
    RUNBOOK_REGISTRY[alert_pattern] = runbook_url


def get_runbook_url(alert: "Alert") -> str:
    """
    Get the runbook URL for an alert using auto-linking.

    Priority:
    1. Alert annotation runbook_url (explicit)
    2. Alert name match in RUNBOOK_REGISTRY
    3. Service label match in SERVICE_RUNBOOK_REGISTRY
    4. Fallback runbook URL

    Args:
        alert: The alert to get runbook for.

    Returns:
        Runbook URL string.
    """
    # 1. Check annotation first
    if alert.annotations.get("runbook_url"):
        return alert.annotations["runbook_url"]

    # 2. Check alert name in registry
    if alert.name in RUNBOOK_REGISTRY:
        return RUNBOOK_REGISTRY[alert.name]

    # 3. Check for partial matches in alert name
    alert_name_lower = alert.name.lower()
    for pattern, url in RUNBOOK_REGISTRY.items():
        if pattern.lower() in alert_name_lower:
            return url

    # 4. Check service label
    service = alert.labels.get("service", "").lower()
    if service in SERVICE_RUNBOOK_REGISTRY:
        return SERVICE_RUNBOOK_REGISTRY[service]

    # 5. Fallback
    return FALLBACK_RUNBOOK_URL


async def compute_baseline_confidence(
    alert: "Alert",
    feedback_store: "FeedbackStore | None" = None,
) -> float:
    """
    Compute baseline confidence score based on historical feedback.

    Factors:
    - Number of approved examples for this alert type
    - Success rate of past remediations
    - Recency of feedback

    Args:
        alert: The alert to compute confidence for.
        feedback_store: Optional feedback store for historical data.

    Returns:
        Confidence score between 0.0 and 1.0.
    """
    base_confidence = 0.5  # Default baseline

    if not feedback_store:
        return base_confidence

    # Get approved examples for this alert type
    approved = await feedback_store.get_approved_examples(
        alert_type=alert.name,
        limit=10,
    )

    if not approved:
        return base_confidence

    # Calculate success rate
    successful = sum(1 for fb in approved if fb.execution_success)
    success_rate = successful / len(approved) if approved else 0.0

    # More examples = higher confidence (up to a point)
    example_bonus = min(len(approved) * 0.05, 0.3)  # Max 0.3 bonus from examples

    # Calculate final confidence
    confidence = base_confidence + (success_rate * 0.2) + example_bonus

    # Clamp to [0.0, 1.0]
    return max(0.0, min(1.0, confidence))


class RemediationStep(BaseModel):
    """A single step in the remediation process."""

    step_number: int = Field(..., description="Step sequence number")
    action: str = Field(..., description="Action type (restart, scale, failover, etc.)")
    description: str = Field(..., description="Human-readable description")
    command: str | None = Field(None, description="Command to execute (if applicable)")
    requires_approval: bool = Field(True, description="Whether step requires human approval")
    risk_level: str = Field("medium", description="Risk level (low, medium, high)")


class AIRecommendation(BaseModel):
    """AI-generated recommendation for an alert."""

    recommendation_id: str = Field(..., description="Unique recommendation ID")
    alert_id: str = Field(..., description="Associated alert ID")
    root_cause_analysis: str = Field(..., description="Analysis of the root cause")
    remediation_steps: list[dict[str, Any]] = Field(
        default_factory=list, description="Ordered list of remediation steps"
    )
    risk_assessment: dict[str, Any] = Field(
        default_factory=dict, description="Risk assessment details"
    )
    runbook_reference: str | None = Field(None, description="Link to relevant runbook")
    generated_at: str = Field(..., description="ISO8601 timestamp of generation")
    model_used: str = Field(..., description="LLM model used for generation")
    confidence_score: float = Field(
        default=0.5, description="Confidence score (0.0-1.0) for the recommendation"
    )


class LLMFactoryProtocol(Protocol):
    """Protocol for LLM factory."""

    async def acompletion(
        self,
        messages: list[dict[str, str]],
        **kwargs: Any,
    ) -> Any:
        """Generate completion from LLM."""
        ...


def build_recommendation_prompt(alert: Alert) -> str:
    """
    Build the prompt for LLM recommendation generation.

    Args:
        alert: The alert to generate recommendation for.

    Returns:
        Formatted prompt string.
    """
    runbook_url = alert.annotations.get("runbook_url", "Not available")

    prompt = f"""You are an expert Site Reliability Engineer analyzing infrastructure alerts.

## Alert Details

- **Name**: {alert.name}
- **Severity**: {alert.severity.value}
- **State**: {alert.state.value}
- **Message**: {alert.message}

### Labels
{json.dumps(alert.labels, indent=2)}

### Annotations
{json.dumps(alert.annotations, indent=2)}

### Runbook Reference
{runbook_url}

## Task

Analyze this alert and provide:
1. Root cause analysis - explain what likely caused this alert
2. Remediation steps - provide ordered steps to resolve the issue
3. Risk assessment - evaluate the risk of the remediation

## Response Format

Respond ONLY with valid JSON in this exact format:
{{
    "root_cause_analysis": "Detailed analysis of the root cause...",
    "remediation_steps": [
        {{
            "step_number": 1,
            "action": "action_type",
            "description": "What this step does",
            "command": "kubectl command if applicable",
            "requires_approval": true,
            "risk_level": "low|medium|high"
        }}
    ],
    "risk_assessment": {{
        "overall_risk": "low|medium|high",
        "impact": "Description of potential impact",
        "urgency": "low|medium|high"
    }}
}}
"""
    return prompt


async def build_recommendation_prompt_with_feedback(
    alert: Alert,
    feedback_store: "FeedbackStore | None" = None,
) -> str:
    """
    Build the prompt for LLM recommendation generation with few-shot examples.

    Enhances the basic prompt with:
    - Approved remediation examples for the alert type (few-shot learning)
    - Constraints based on rejection patterns (constraint learning)

    Args:
        alert: The alert to generate recommendation for.
        feedback_store: Optional feedback store for few-shot examples.

    Returns:
        Enhanced prompt string.
    """
    runbook_url = alert.annotations.get("runbook_url", "Not available")

    prompt = f"""You are an expert Site Reliability Engineer analyzing infrastructure alerts.

## Alert Details

- **Name**: {alert.name}
- **Severity**: {alert.severity.value}
- **State**: {alert.state.value}
- **Message**: {alert.message}

### Labels
{json.dumps(alert.labels, indent=2)}

### Annotations
{json.dumps(alert.annotations, indent=2)}

### Runbook Reference
{runbook_url}

"""

    # Add few-shot examples if feedback store is available
    if feedback_store:
        examples = await feedback_store.get_approved_examples(
            alert_type=alert.name,
            limit=3,  # Include up to 3 successful examples
        )

        if examples:
            prompt += """## Previously Successful Remediations
The following remediations were approved and executed successfully for similar alerts:

"""
            for i, ex in enumerate(examples, 1):
                prompt += f"""### Example {i}
- Alert Type: {ex.alert_type}
- Labels: {json.dumps(ex.alert_labels)}
- Execution Time: {ex.execution_time_seconds}s
- Admin Notes: {ex.admin_notes or "None"}

"""

        # Add constraints from rejection patterns
        constraints = await _build_constraints_from_rejections(
            alert.name, feedback_store
        )
        if constraints:
            prompt += f"""## Important Constraints
Based on previous feedback, avoid these approaches:
{constraints}

"""
        # Record metrics for few-shot and constraint learning effectiveness
        try:
            from mcp_server_langgraph.alerts.metrics import (
                record_constraint_usage,
                record_fewshot_usage,
            )

            # Record few-shot usage
            record_fewshot_usage(
                alert_type=alert.name,
                example_count=len(examples) if examples else 0,
            )

            # Record constraint usage (count newlines + 1 if constraints exist)
            constraint_count = len(constraints.strip().split("\n")) if constraints else 0
            record_constraint_usage(
                alert_type=alert.name,
                constraint_count=constraint_count,
            )
        except ImportError:
            pass  # Metrics may not be available in all contexts

    prompt += """## Task

Analyze this alert and provide:
1. Root cause analysis - explain what likely caused this alert
2. Remediation steps - provide ordered steps to resolve the issue
3. Risk assessment - evaluate the risk of the remediation

## Response Format

Respond ONLY with valid JSON in this exact format:
{
    "root_cause_analysis": "Detailed analysis of the root cause...",
    "remediation_steps": [
        {
            "step_number": 1,
            "action": "action_type",
            "description": "What this step does",
            "command": "kubectl command if applicable",
            "requires_approval": true,
            "risk_level": "low|medium|high"
        }
    ],
    "risk_assessment": {
        "overall_risk": "low|medium|high",
        "impact": "Description of potential impact",
        "urgency": "low|medium|high"
    }
}
"""
    return prompt


async def _build_constraints_from_rejections(
    alert_type: str,
    feedback_store: "FeedbackStore",
) -> str:
    """
    Build constraint text from rejection patterns.

    Analyzes rejection patterns to add constraints that help the AI
    avoid previously rejected approaches.

    Args:
        alert_type: Alert type to get patterns for.
        feedback_store: Feedback store to query.

    Returns:
        Constraint text to add to prompt, or empty string.
    """
    from mcp_server_langgraph.alerts.feedback import RejectionReason

    patterns = await feedback_store.get_rejection_patterns(alert_type)

    constraints = []
    threshold = 2  # Only add constraint if rejection count > threshold

    if patterns.get(RejectionReason.TOO_RISKY, 0) > threshold:
        constraints.append("- Avoid high-risk commands; prefer safe diagnostic steps first")

    if patterns.get(RejectionReason.INCORRECT_DIAGNOSIS, 0) > threshold:
        constraints.append("- Focus on accurate root cause analysis before remediation")

    if patterns.get(RejectionReason.WRONG_COMMAND, 0) > threshold:
        constraints.append("- Double-check command syntax and paths")

    if patterns.get(RejectionReason.INCOMPLETE_STEPS, 0) > threshold:
        constraints.append("- Provide complete step-by-step instructions")

    if patterns.get(RejectionReason.NOT_RELEVANT, 0) > threshold:
        constraints.append("- Ensure remediation directly addresses this specific alert")

    return "\n".join(constraints)


# ==============================================================================
# Cache Key Generation
# ==============================================================================

# Redis cache key prefix for AI recommendations
RECOMMENDATION_CACHE_PREFIX = "alert:recommendation"

# Default TTL for cached recommendations (1 hour)
RECOMMENDATION_CACHE_TTL = 3600


def generate_recommendation_cache_key(alert: Alert) -> str:
    """
    Generate a cache key for an alert recommendation.

    The cache key is based on:
    - Alert ID (primary key)
    - Alert name (type of alert)
    - Key labels (service, namespace, etc.)

    This allows cache hits when the same type of alert occurs on the
    same service, even if the alert_id is different.

    Args:
        alert: The alert to generate a cache key for.

    Returns:
        Cache key string.
    """
    # Create a fingerprint from alert characteristics
    key_labels = ["service", "namespace", "job", "alertname"]
    label_parts = [
        f"{k}:{alert.labels.get(k, '')}"
        for k in key_labels
        if alert.labels.get(k)
    ]

    # Build key components
    components = [
        alert.name,
        alert.severity.value,
        *label_parts,
    ]

    # Create stable hash for complex alert characteristics
    fingerprint = ":".join(components)

    # Use MD5 for shorter, consistent cache keys (not for security)
    key_hash = hashlib.md5(  # nosec B324
        fingerprint.encode(), usedforsecurity=False
    ).hexdigest()[:16]

    return f"{RECOMMENDATION_CACHE_PREFIX}:{alert.name}:{key_hash}"


def _parse_llm_response(response_text: str) -> dict[str, Any]:
    """
    Parse LLM response text to extract JSON.

    Args:
        response_text: Raw LLM response.

    Returns:
        Parsed JSON dict.
    """
    # Try to extract JSON from response
    try:
        # First, try direct parse
        result: dict[str, Any] = json.loads(response_text)
        return result
    except json.JSONDecodeError:
        # Try to find JSON block in markdown
        if "```json" in response_text:
            start = response_text.find("```json") + 7
            end = response_text.find("```", start)
            if end > start:
                result = json.loads(response_text[start:end].strip())
                return result
        elif "```" in response_text:
            start = response_text.find("```") + 3
            end = response_text.find("```", start)
            if end > start:
                result = json.loads(response_text[start:end].strip())
                return result

        # Try to find JSON object
        start = response_text.find("{")
        end = response_text.rfind("}") + 1
        if start >= 0 and end > start:
            result = json.loads(response_text[start:end])
            return result

        logger.warning(f"Failed to parse LLM response: {response_text[:200]}")
        return {
            "root_cause_analysis": "Unable to parse LLM response",
            "remediation_steps": [],
            "risk_assessment": {},
        }


class AIRecommendationService:
    """
    Service for generating AI-powered alert recommendations.

    Uses LLM to analyze alerts and generate remediation recommendations.

    Caching strategy (tiered):
    - L1: In-memory cache for fast access (per-instance)
    - L2: Redis distributed cache for cross-instance sharing

    Supports few-shot learning via FeedbackStore integration.
    """

    def __init__(
        self,
        llm_factory: LLMFactoryProtocol | None = None,
        feedback_store: "FeedbackStore | None" = None,
        cache_service: "CacheService | None" = None,
        cache_ttl_seconds: int = 3600,  # 1 hour default
        alert_orchestrator: "AlertOrchestrator | None" = None,
    ) -> None:
        """
        Initialize the AI recommendation service.

        Args:
            llm_factory: LLM factory for generating completions.
            feedback_store: Optional FeedbackStore for few-shot learning
                            and constraint learning from past approvals/rejections.
            cache_service: Optional CacheService for Redis-backed caching.
                           If not provided, uses in-memory fallback.
            cache_ttl_seconds: Time-to-live for cached recommendations.
            alert_orchestrator: Optional AlertOrchestrator for parallel
                                multi-alert analysis (Phase 12 orchestration).
        """
        self._llm = llm_factory
        self._feedback_store = feedback_store
        self._cache_service = cache_service
        self._cache: dict[str, AIRecommendation] = {}  # L1 fallback cache (primary)
        self._alert_id_index: dict[str, str] = {}  # Secondary index: alert_id -> cache_key
        self._cache_ttl = cache_ttl_seconds
        self._model_name = "claude-sonnet-4"  # Default model
        self._alert_orchestrator = alert_orchestrator

    def _get_cached_recommendation(self, cache_key: str) -> AIRecommendation | None:
        """
        Get cached recommendation from L2 (Redis) or L1 (in-memory).

        Args:
            cache_key: Cache key for the recommendation.

        Returns:
            Cached AIRecommendation or None if not found.
        """
        # Try Redis cache first (L2)
        if self._cache_service:
            try:
                cached_data = self._cache_service.get(cache_key)
                if cached_data:
                    # Cached data is a dict, need to convert to AIRecommendation
                    if isinstance(cached_data, dict):
                        return AIRecommendation(**cached_data)
                    elif isinstance(cached_data, AIRecommendation):
                        return cached_data
            except Exception as e:
                logger.warning(f"Redis cache get failed, falling back to L1: {e}")

        # Fallback to in-memory cache (L1)
        return self._cache.get(cache_key)

    def _set_cached_recommendation(
        self, cache_key: str, recommendation: AIRecommendation
    ) -> None:
        """
        Cache recommendation in L2 (Redis) and L1 (in-memory).

        Args:
            cache_key: Cache key for the recommendation.
            recommendation: AIRecommendation to cache.
        """
        # Cache in Redis (L2) - store as dict for JSON serialization
        if self._cache_service:
            try:
                self._cache_service.set(
                    cache_key,
                    recommendation.model_dump(),
                    ttl=self._cache_ttl,
                )
                logger.debug(f"Cached recommendation in Redis: {cache_key}")
            except Exception as e:
                logger.warning(f"Redis cache set failed: {e}")

        # Also cache in memory (L1) for fast access
        # Primary cache stores by cache_key, secondary index maps alert_id -> cache_key
        # This avoids duplicating the recommendation object in memory
        self._cache[cache_key] = recommendation
        self._alert_id_index[recommendation.alert_id] = cache_key

        # Update cache size metric (count unique recommendations, not index entries)
        try:
            from mcp_server_langgraph.alerts.metrics import (
                update_recommendation_cache_size,
            )

            update_recommendation_cache_size(len(self._cache), cache_type="l1")
        except ImportError:
            pass  # Metrics may not be available in all contexts

    async def generate_recommendation(
        self,
        alert: Alert,
        force_regenerate: bool = False,
    ) -> AIRecommendation:
        """
        Generate an AI recommendation for an alert.

        Caching strategy:
        - Uses fingerprint-based cache key (alert type + labels) for better reuse
        - Checks Redis (L2) first, then in-memory (L1)
        - Cache hit for similar alerts on same service, even with different IDs

        Args:
            alert: The alert to analyze.
            force_regenerate: If True, bypass cache and regenerate.

        Returns:
            AIRecommendation with root cause analysis and remediation steps.
        """
        with tracer.start_as_current_span(
            "alert.generate_recommendation",
            attributes={
                "alert.id": alert.alert_id,
                "alert.type": alert.name,
                "alert.severity": alert.severity.value,
                "recommendation.force_regenerate": force_regenerate,
            },
        ) as span:
            # Generate cache key based on alert fingerprint (not just ID)
            cache_key = generate_recommendation_cache_key(alert)
            span.set_attribute("recommendation.cache_key", cache_key)

            # Check cache first (unless force regenerate)
            if not force_regenerate:
                cached = self._get_cached_recommendation(cache_key)
                if cached:
                    logger.debug(
                        f"Cache hit for alert {alert.alert_id} (key: {cache_key})"
                    )
                    span.set_attribute("recommendation.cache_hit", True)
                    # Record metrics
                    try:
                        from mcp_server_langgraph.alerts.metrics import (
                            record_recommendation_request,
                        )
                        record_recommendation_request(alert.alert_id, cached=True)
                    except ImportError:
                        pass
                    return cached

            span.set_attribute("recommendation.cache_hit", False)

            # Build prompt - use feedback-enhanced prompt if feedback store is available
            if self._feedback_store:
                prompt = await build_recommendation_prompt_with_feedback(
                    alert, self._feedback_store
                )
                logger.debug(f"Using feedback-enhanced prompt for alert {alert.alert_id}")
                span.set_attribute("recommendation.feedback_enhanced", True)
            else:
                prompt = build_recommendation_prompt(alert)
                span.set_attribute("recommendation.feedback_enhanced", False)

            # Call LLM
            try:
                if self._llm:
                    response = await self._llm.acompletion(
                        messages=[{"role": "user", "content": prompt}],
                        temperature=0.3,  # Lower temperature for consistency
                        max_tokens=2048,
                    )
                    response_text = response.choices[0].message.content
                else:
                    # Fallback for testing without LLM
                    response_text = json.dumps(
                        {
                            "root_cause_analysis": "LLM not configured",
                            "remediation_steps": [],
                            "risk_assessment": {},
                        }
                    )

                # Parse response
                parsed = _parse_llm_response(response_text)

                # Compute confidence score
                baseline_confidence = await compute_baseline_confidence(
                    alert, self._feedback_store
                )
                # Use LLM-provided confidence if available, otherwise use baseline
                llm_confidence = parsed.get("confidence_score")
                if llm_confidence is not None and isinstance(llm_confidence, (int, float)):
                    # Average LLM confidence with baseline
                    confidence_score = (float(llm_confidence) + baseline_confidence) / 2
                else:
                    confidence_score = baseline_confidence

                span.set_attribute("recommendation.confidence_score", confidence_score)

                # Get runbook URL using auto-linking
                runbook_url = get_runbook_url(alert)

                # Create recommendation
                recommendation = AIRecommendation(
                    recommendation_id=str(uuid.uuid4()),
                    alert_id=alert.alert_id,
                    root_cause_analysis=parsed.get("root_cause_analysis", ""),
                    remediation_steps=parsed.get("remediation_steps", []),
                    risk_assessment=parsed.get("risk_assessment", {}),
                    runbook_reference=runbook_url,
                    generated_at=datetime.now(UTC).isoformat(),
                    model_used=self._model_name,
                    confidence_score=confidence_score,
                )

                # Cache the recommendation (L2 Redis + L1 in-memory)
                self._set_cached_recommendation(cache_key, recommendation)

                span.set_attribute("recommendation.steps_count", len(recommendation.remediation_steps))
                span.set_attribute("recommendation.id", recommendation.recommendation_id)

                # Record metrics
                try:
                    from mcp_server_langgraph.alerts.metrics import (
                        record_recommendation_generated,
                        record_recommendation_quality,
                        record_recommendation_request,
                    )
                    record_recommendation_request(alert.alert_id, cached=False)
                    record_recommendation_generated(alert.alert_id, 0.0, success=True)
                    # Record quality score for Grafana dashboard tracking
                    record_recommendation_quality(
                        alert_type=alert.name,
                        quality_score=confidence_score,  # Use confidence as initial quality
                        confidence=confidence_score,
                    )
                except ImportError:
                    pass

                logger.info(
                    f"Generated recommendation for alert {alert.alert_id}",
                    extra={
                        "recommendation_id": recommendation.recommendation_id,
                        "steps_count": len(recommendation.remediation_steps),
                        "cache_key": cache_key,
                    },
                )

                return recommendation

            except Exception as e:
                logger.error(f"Error generating recommendation: {e}", exc_info=True)
                span.record_exception(e)
                span.set_attribute("recommendation.error", True)
                # Return a minimal recommendation on error
                return AIRecommendation(
                    recommendation_id=str(uuid.uuid4()),
                    alert_id=alert.alert_id,
                    root_cause_analysis=f"Error generating recommendation: {str(e)}",
                    remediation_steps=[],
                    risk_assessment={},
                    runbook_reference=get_runbook_url(alert),
                    confidence_score=0.0,  # Low confidence on error
                    generated_at=datetime.now(UTC).isoformat(),
                    model_used=self._model_name,
                )

    async def get_cached_recommendation(
        self, alert_id: str
    ) -> AIRecommendation | None:
        """
        Get a cached recommendation by alert ID.

        Uses secondary index to look up the cache_key, then retrieves
        the recommendation from the primary cache.

        Args:
            alert_id: The alert ID to look up.

        Returns:
            Cached AIRecommendation or None if not found.
        """
        # Look up cache_key from secondary index
        cache_key = self._alert_id_index.get(alert_id)
        if cache_key:
            return self._cache.get(cache_key)
        return None

    def clear_cache(self) -> None:
        """Clear the recommendation cache and secondary index."""
        self._cache.clear()
        self._alert_id_index.clear()

        # Update cache size metric
        try:
            from mcp_server_langgraph.alerts.metrics import (
                update_recommendation_cache_size,
            )

            update_recommendation_cache_size(0, cache_type="l1")
        except ImportError:
            pass

    @property
    def alert_orchestrator(self) -> "AlertOrchestrator | None":
        """Access the alert orchestrator for parallel multi-alert analysis."""
        return self._alert_orchestrator

    async def analyze_alerts_orchestrated(
        self,
        alert_ids: list[str],
        include_correlation: bool = True,
        include_root_cause: bool = True,
        include_remediation: bool = False,
        include_pattern_detection: bool = False,
    ) -> dict[str, Any]:
        """
        Analyze multiple alerts using the orchestrator for parallel execution.

        This method provides orchestrated multi-alert analysis when the
        enable_orchestrated_alert_analysis feature flag is enabled.

        Args:
            alert_ids: List of alert identifiers to analyze.
            include_correlation: Include correlation analysis.
            include_root_cause: Include root cause analysis.
            include_remediation: Include remediation analysis.
            include_pattern_detection: Include pattern detection.

        Returns:
            Comprehensive analysis result with correlation summary.

        Raises:
            ValueError: If orchestrator is not configured or not enabled.
        """
        if self._alert_orchestrator is None:
            raise ValueError("AlertOrchestrator not configured")

        if not getattr(self._alert_orchestrator, "is_enabled", False):
            raise ValueError("Orchestrated alert analysis is not enabled")

        logger.debug(f"Using AlertOrchestrator for {len(alert_ids)} alerts")

        return await self._alert_orchestrator.analyze_alerts(
            alert_ids=alert_ids,
            include_correlation=include_correlation,
            include_root_cause=include_root_cause,
            include_remediation=include_remediation,
            include_pattern_detection=include_pattern_detection,
        )


class AIRecommendationQueue:
    """
    Queue for asynchronous AI recommendation generation.

    Used to pre-compute recommendations for critical alerts without
    blocking the webhook response.
    """

    def __init__(self, service: AIRecommendationService) -> None:
        """
        Initialize the recommendation queue.

        Args:
            service: AIRecommendationService instance.
        """
        self._service = service
        self._queue: asyncio.Queue[Alert] = asyncio.Queue()
        self._processing = False

    @property
    def pending_count(self) -> int:
        """Get the number of pending alerts in queue."""
        return self._queue.qsize()

    async def queue_recommendation(self, alert: Alert) -> None:
        """
        Queue an alert for recommendation generation.

        Args:
            alert: Alert to generate recommendation for.
        """
        await self._queue.put(alert)
        logger.debug(f"Queued recommendation for alert {alert.alert_id}")

    async def process_pending(self) -> int:
        """
        Process all pending alerts in the queue.

        Returns:
            Number of alerts processed.
        """
        processed = 0

        while not self._queue.empty():
            try:
                alert = await asyncio.wait_for(
                    self._queue.get(),
                    timeout=1.0,
                )
                await self._service.generate_recommendation(alert)
                processed += 1
                self._queue.task_done()
            except TimeoutError:
                break
            except Exception:
                logger.exception("Error processing queued alert")

        return processed

    async def start_background_processing(self) -> None:
        """Start background processing of queued alerts."""
        if self._processing:
            return

        self._processing = True
        logger.info("Started background recommendation processing")

        while self._processing:
            try:
                alert = await asyncio.wait_for(
                    self._queue.get(),
                    timeout=5.0,
                )
                await self._service.generate_recommendation(alert)
                self._queue.task_done()
            except TimeoutError:
                continue
            except Exception:
                logger.exception("Error in background processing")

    def stop_background_processing(self) -> None:
        """Stop background processing."""
        self._processing = False
        logger.info("Stopped background recommendation processing")
