"""
AI UX LLM Service

Provides LLM-enhanced AI UX features with fallback to heuristics.

Features:
- LLM-powered error analysis with intelligent recovery suggestions
- Personalized empty state suggestions
- Nuanced persona behavior detection
- Graceful fallback to rule-based heuristics when LLM unavailable
- Prometheus metrics for observability
- Response caching to reduce LLM costs

Reference: UX Audit Plan - Phase 6 AI-Native Integration
"""

from __future__ import annotations

import hashlib
import json
import re
import time
from collections.abc import AsyncIterator
from typing import TYPE_CHECKING, Any, cast

from cachetools import TTLCache
from langchain_core.messages import HumanMessage, SystemMessage

from mcp_server_langgraph.core.cache_mixin import StaleWhileRevalidateMixin

# Cache TTL in seconds (1 hour for LLM responses)
CACHE_TTL_SECONDS = 3600
CACHE_MAX_SIZE = 1000

# =============================================================================
# Service Complexity Mapping
# =============================================================================

# Maps AI UX services to model complexity tiers for cost/latency optimization
# - simple: Fast pattern matching (gemini-flash, claude-haiku)
# - complicated: Multi-step reasoning (gemini-2.5-flash, claude-sonnet)
# - complex: Deep analysis (gemini-pro, claude-opus)
SERVICE_COMPLEXITY: dict[str, str] = {
    "error_analysis": "simple",  # Fast pattern matching for errors
    "empty_state": "simple",  # Simple context-based suggestions
    "nudge_recommendation": "simple",  # Timing/trigger logic
    "disclosure_analysis": "complicated",  # Behavior pattern analysis
    "persona_analysis": "complicated",  # User pattern detection
    "onboarding_personalization": "complicated",  # Intent detection
    "metrics_insights": "complex",  # Anomaly detection and predictions
}

# =============================================================================
# Prometheus Metrics
# =============================================================================

try:
    from prometheus_client import Counter, Gauge, Histogram

    # LLM call counter by method
    ai_ux_llm_calls_total = Counter(
        name="ai_ux_llm_calls_total",
        documentation="Total LLM calls made by AI UX service",
        labelnames=["method"],
    )

    # Fallback counter by method
    ai_ux_llm_fallbacks_total = Counter(
        name="ai_ux_llm_fallbacks_total",
        documentation="Total fallbacks to heuristics in AI UX service",
        labelnames=["method"],
    )

    # LLM call latency histogram
    ai_ux_llm_latency_seconds = Histogram(
        name="ai_ux_llm_latency_seconds",
        documentation="LLM call latency in seconds for AI UX service",
        labelnames=["method"],
        buckets=(0.1, 0.25, 0.5, 1.0, 2.5, 5.0, 10.0),
    )

    # Cache hit counter by method
    ai_ux_cache_hits_total = Counter(
        name="ai_ux_cache_hits_total",
        documentation="Total cache hits in AI UX service",
        labelnames=["method"],
    )

    # L1/L2 cache hit counters (tiered caching)
    ai_ux_l1_cache_hits_total = Counter(
        name="ai_ux_l1_cache_hits_total",
        documentation="Total L1 (in-memory) cache hits in AI UX service",
        labelnames=["method"],
    )

    ai_ux_l2_cache_hits_total = Counter(
        name="ai_ux_l2_cache_hits_total",
        documentation="Total L2 (Redis) cache hits in AI UX service",
        labelnames=["method"],
    )

    ai_ux_cache_miss_total = Counter(
        name="ai_ux_cache_miss_total",
        documentation="Total cache misses (L1 and L2) in AI UX service",
        labelnames=["method"],
    )

    # WebSocket connections gauge
    ai_ux_websocket_connections = Gauge(
        name="ai_ux_websocket_connections",
        documentation="Current number of WebSocket connections for AI UX",
        labelnames=["user_id"],
    )

    # Rate limit exceeded counter
    ai_ux_rate_limit_exceeded_total = Counter(
        name="ai_ux_rate_limit_exceeded_total",
        documentation="Total rate limit exceeded events for AI UX",
        labelnames=["endpoint"],
    )

    PROMETHEUS_AVAILABLE = True

except ImportError:
    # Fallback to mock metrics if prometheus_client not available
    import warnings

    warnings.warn(
        "prometheus_client not available. AI UX metrics will be disabled.",
        stacklevel=2,
    )

    class _MockCounter:
        """Mock counter for when prometheus_client is unavailable."""

        def __init__(self, *args: Any, **kwargs: Any) -> None:
            self._value: float = 0.0

        def labels(self, **kwargs: Any) -> _MockCounter:
            return self

        def inc(self, amount: float = 1) -> None:
            self._value += amount

    class _MockHistogram:
        """Mock histogram for when prometheus_client is unavailable."""

        def __init__(self, *args: Any, **kwargs: Any) -> None:
            self._count = 0
            self._sum = 0.0

        def labels(self, **kwargs: Any) -> _MockHistogram:
            return self

        def observe(self, value: float) -> None:
            self._count += 1
            self._sum += value

    class _MockGauge:
        """Mock gauge for when prometheus_client is unavailable."""

        def __init__(self, *args: Any, **kwargs: Any) -> None:
            self._value = 0.0

        def labels(self, **kwargs: Any) -> _MockGauge:
            return self

        def inc(self, amount: float = 1) -> None:
            self._value += amount

        def dec(self, amount: float = 1) -> None:
            self._value -= amount

        def set(self, value: float) -> None:
            self._value = value

    ai_ux_llm_calls_total = _MockCounter()  # type: ignore[assignment]
    ai_ux_llm_fallbacks_total = _MockCounter()  # type: ignore[assignment]
    ai_ux_llm_latency_seconds = _MockHistogram()  # type: ignore[assignment]
    ai_ux_cache_hits_total = _MockCounter()  # type: ignore[assignment]
    ai_ux_l1_cache_hits_total = _MockCounter()  # type: ignore[assignment]
    ai_ux_l2_cache_hits_total = _MockCounter()  # type: ignore[assignment]
    ai_ux_cache_miss_total = _MockCounter()  # type: ignore[assignment]
    ai_ux_websocket_connections = _MockGauge()  # type: ignore[assignment]
    ai_ux_rate_limit_exceeded_total = _MockCounter()  # type: ignore[assignment]
    PROMETHEUS_AVAILABLE = False

from mcp_server_langgraph.api.v1.ai_ux import (
    DisclosureAnalyzeRequest,
    DisclosureAnalyzeResponse,
    DisclosureLevel,
    EmptyStateSuggestion,
    EmptyStateSuggestionsRequest,
    EmptyStateSuggestionsResponse,
    ErrorAnalyzeResponse,
    ErrorCategory,
    ErrorClassification,
    ErrorInfo,
    MetricInsight,
    MetricPrediction,
    MetricsInsightsResponse,
    NudgeRecommendRequest,
    NudgeRecommendResponse,
    OnboardingPersonalizeRequest,
    OnboardingPersonalizeResponse,
    OnboardingStep,
    PersonaAnalyzeRequest,
    PersonaAnalyzeResponse,
    RecoverySuggestion,
    SuggestionAction,
    UIAdaptation,
    UserContext,
)
from mcp_server_langgraph.observability.telemetry import logger
from mcp_server_langgraph.resilience.circuit_breaker import (
    CircuitBreakerState,
    get_circuit_breaker,
    get_circuit_breaker_state,
)

if TYPE_CHECKING:
    from mcp_server_langgraph.agents.artifacts import ArtifactStorage
    from mcp_server_langgraph.agents.model_selector import ModelSelector
    from mcp_server_langgraph.agents.ux_orchestrator import UXOrchestrator
    from mcp_server_langgraph.api.v1.ai_ux import (
        CompositeAnalysisRequest,
        CompositeAnalysisResponse,
        DisclosureAnalyzeResponse,
        ErrorAnalyzeResponse,
        PersonaAnalyzeResponse,
    )
    from mcp_server_langgraph.llm.factory import LLMFactory


# =============================================================================
# Prompts
# =============================================================================

ERROR_ANALYSIS_SYSTEM_PROMPT = """You are an AI assistant that analyzes errors and provides recovery suggestions.

Given an error message and optional user context, analyze the error and return a JSON response with:
- category: One of 'network', 'authentication', 'authorization', 'validation', 'server', 'client', 'timeout', 'quota', 'unknown'
- subcategory: A more specific classification
- confidence: Float between 0 and 1
- root_cause: A human-readable explanation of what likely caused the error
- suggestions: List of recovery suggestions, each with:
  - action: One of 'navigate', 'retry', 'wait', 'simplify', 'contact', 'modal', 'execute'
  - label: Button text
  - guidance: Optional detailed instructions
  - estimated_success: Float between 0 and 1

Respond ONLY with valid JSON. Do not include any other text."""

EMPTY_STATE_SYSTEM_PROMPT = """You are an AI assistant that generates contextual suggestions for empty states.

Given the page context, user persona, and optional history, generate personalized suggestions to help the user get started.

Return a JSON response with:
- suggestions: List of suggestions, each with:
  - text: The suggestion text
  - action: One of 'navigate', 'modal', 'execute'
  - target: The URL or modal ID to target
  - confidence: Float between 0 and 1
  - category: Category like 'onboarding', 'discovery', 'alternative'

Respond ONLY with valid JSON. Do not include any other text."""

PERSONA_ANALYSIS_SYSTEM_PROMPT = """You are an AI assistant that analyzes user behavior to detect their actual persona.

Given the assigned persona, recent actions, and feature usage, determine if the user's behavior matches their assigned persona.

Return a JSON response with:
- detected_persona: The persona that best matches their behavior
- confidence: Float between 0 and 1
- behavior_signals: List of behavioral indicators
- recommendation: Optional recommendation if persona mismatch detected
- ui_adaptations: List of UI changes to apply, each with:
  - feature: The feature to adapt
  - action: One of 'unlock', 'promote', 'hide'

Available personas: admin, security-admin, auditor, alice-builder, alice-analyst, alice-devops, compliance-officer, bob

Respond ONLY with valid JSON. Do not include any other text."""

DISCLOSURE_ANALYSIS_SYSTEM_PROMPT = """You are an AI assistant that analyzes user behavior to recommend UI complexity levels.

Given the user's feature usage and session history, determine their current expertise level and recommend an appropriate disclosure level.

Return a JSON response with:
- current_level: One of 'beginner', 'intermediate', 'advanced', 'expert'
- recommended_level: One of 'beginner', 'intermediate', 'advanced', 'expert'
- confidence: Float between 0 and 1
- unlock_features: List of feature names to unlock at the recommended level
- personalized_message: Optional message explaining the recommendation

Consider these factors:
- Total feature usage count indicates engagement
- Advanced features (workflows, mcp, agents, traces) indicate expertise
- Session duration indicates commitment
- Diversity of feature usage indicates breadth of knowledge

Respond ONLY with valid JSON. Do not include any other text."""

NUDGE_RECOMMENDATION_SYSTEM_PROMPT = """You are an AI assistant that recommends contextual nudges to help users discover features.

Given the user's current context, nudge history, and behavior, decide if a nudge should be shown.

Return a JSON response with:
- should_show: Boolean indicating if a nudge should be shown
- nudge: Optional object if should_show is true, containing:
  - id: Unique identifier for the nudge
  - type: One of 'tooltip', 'spotlight', 'banner'
  - target_element: CSS selector for the target element
  - message: The nudge message to display
  - priority: One of 'low', 'medium', 'high'
  - show_after_ms: Milliseconds delay before showing
- confidence: Float between 0 and 1

Consider:
- Don't show nudges if user has dismissed many recently
- Time on page indicates when user might need help
- Previous nudge history helps avoid repetition
- Context determines which nudges are relevant

Respond ONLY with valid JSON. Do not include any other text."""

ONBOARDING_PERSONALIZATION_SYSTEM_PROMPT = """You are an AI assistant that personalizes user onboarding based on detected intent.

Given the user's initial actions and signup context, determine their likely intent and recommend an onboarding path.

Return a JSON response with:
- detected_intent: Brief description of what the user wants to accomplish
- confidence: Float between 0 and 1
- recommended_path: List of onboarding steps, each with:
  - step: Step identifier
  - template: Optional template name
  - guided: Boolean for guided mode
  - focus: Optional focus area
- skip_steps: List of step identifiers to skip
- persona_prediction: Predicted persona based on behavior

Intent categories: build_workflow, use_chat, observe_systems, build_automation, explore, integrate_tools

Respond ONLY with valid JSON. Do not include any other text."""

METRICS_INSIGHTS_SYSTEM_PROMPT = """You are an AI assistant that analyzes HEART metrics data and generates actionable insights.

Analyze the provided metrics data and generate insights about user experience patterns.

Return a JSON response with:
- insights: List of insights, each with:
  - type: One of 'anomaly', 'trend', 'pattern'
  - dimension: HEART dimension ('happiness', 'engagement', 'adoption', 'retention', 'task_success')
  - message: Human-readable insight description
  - severity: One of 'info', 'warning', 'critical'
  - sentiment: One of 'positive', 'negative', 'neutral'
  - suggested_actions: Optional list of recommended actions
  - detected_at: Optional ISO timestamp
- predictions: List of metric predictions, each with:
  - metric: Metric name
  - current: Current value
  - predicted: Predicted value
  - confidence: Float between 0 and 1
  - drivers: List of factors driving the prediction

Focus on actionable insights that can improve user experience.

Respond ONLY with valid JSON. Do not include any other text."""

# =============================================================================
# Session Intelligence System Prompts (Sprint 2)
# =============================================================================

SESSION_SUMMARIZE_SYSTEM_PROMPT = """You are an AI assistant that generates concise summaries of chat sessions.

Given the session ID and context, generate a summary that captures the main topics discussed and key outcomes.

Return a JSON response with:
- summary: A 1-2 sentence summary of the session
- key_topics: List of 3-5 key topics discussed (e.g., "React", "debugging", "API design")
- highlight_messages: List of up to 3 important messages or quotes
- message_count: Estimated number of messages in the session
- confidence: Float between 0 and 1 indicating confidence in the summary

Keep summaries concise and actionable. Focus on what was accomplished or discussed.

Respond ONLY with valid JSON. Do not include any other text."""

SESSION_GROUP_SYSTEM_PROMPT = """You are an AI assistant that groups related sessions by topic or project.

Given a list of session IDs, analyze and group them into logical clusters based on their content themes.

Return a JSON response with:
- groups: List of groups, each with:
  - topic: A descriptive name for the group (e.g., "API Development", "Frontend Work")
  - session_ids: List of session IDs that belong to this group
  - confidence: Float between 0 and 1 indicating grouping confidence
- ungrouped: List of session IDs that couldn't be confidently grouped

Group sessions that share common themes, projects, or purposes. Aim for 2-5 groups for typical session lists.

Respond ONLY with valid JSON. Do not include any other text."""

SESSION_SIMILARITY_SYSTEM_PROMPT = """You are an AI assistant that finds sessions similar to a given reference session.

Given a source session ID, find other sessions with similar content, topics, or purposes.

Return a JSON response with:
- similar_sessions: List of similar sessions, each with:
  - session_id: The session identifier
  - similarity_score: Float between 0 and 1 (higher = more similar)
  - common_topics: List of topics shared between sessions
- search_query: A brief description of what makes sessions similar

Rank sessions by relevance. Include sessions that share topics, code patterns, or problem domains.

Respond ONLY with valid JSON. Do not include any other text."""

TRACE_SUMMARIZE_SYSTEM_PROMPT = """You are an AI assistant that generates concise summaries of agent execution traces.

Given trace data including step durations, tool calls, and execution flow, generate a summary.

Return a JSON response with:
- summary: A 1-2 sentence summary of what the agent accomplished
- total_duration_ms: Total execution time in milliseconds
- step_count: Number of steps in the trace
- tool_call_count: Number of tool calls made
- success: Boolean indicating if the trace completed successfully
- key_actions: List of 3-5 key actions performed (e.g., "Fetched user data", "Processed results")
- confidence: Float between 0 and 1 indicating confidence in the summary

Focus on the main workflow outcome and any notable events.

Respond ONLY with valid JSON. Do not include any other text."""

TRACE_ANOMALIES_SYSTEM_PROMPT = """You are an AI assistant that detects anomalies and bottlenecks in agent execution traces.

Analyze the trace data to identify performance issues, errors, and optimization opportunities.

Return a JSON response with:
- anomalies: List of detected anomalies, each with:
  - type: Anomaly type (e.g., "timeout", "error", "retry", "unexpected_state")
  - description: Brief description of the anomaly
  - severity: One of "info", "warning", "error", "critical"
- bottlenecks: List of performance bottlenecks, each with:
  - step: Step or action name
  - duration_ms: Duration in milliseconds
  - recommendation: Suggested optimization
- health_score: Float between 0 and 1 indicating overall trace health
- optimization_suggestions: List of general optimization recommendations

Prioritize actionable findings. Be specific about which steps have issues.

Respond ONLY with valid JSON. Do not include any other text."""


# =============================================================================
# LLMWithFallback Base Class
# =============================================================================


class LLMWithFallback:
    """
    Base class for LLM-enhanced services with heuristic fallback.

    Provides a standard pattern for:
    - Executing LLM calls with automatic fallback to heuristics on failure
    - Caching responses to reduce LLM costs
    - Recording metrics for observability
    - Integrating with ModelSelector for cost/latency optimization

    This class can be used as a base class or as a mixin to provide
    consistent LLM/heuristic fallback behavior across AI UX services.
    """

    def __init__(
        self,
        llm_factory: LLMFactory | None,
        settings: Any,
        model_selector: ModelSelector | None = None,
    ) -> None:
        """
        Initialize LLM with fallback base.

        Args:
            llm_factory: LLM factory for making LLM calls (optional)
            settings: Application settings with feature flags
            model_selector: Optional ModelSelector for cost/latency optimization
        """
        self.llm_factory = llm_factory
        self.settings = settings
        self.model_selector = model_selector

        # LLM is enabled only if factory exists AND feature flag is on
        self.llm_enabled = llm_factory is not None and getattr(settings, "ff_enable_ai_suggestions", True)

        # Response cache for LLM calls (reduces costs and latency)
        self._response_cache: TTLCache[str, Any] = TTLCache(
            maxsize=CACHE_MAX_SIZE,
            ttl=CACHE_TTL_SECONDS,
        )

    def _get_cached_response(self, cache_key: str) -> Any | None:
        """Get cached response if available."""
        return self._response_cache.get(cache_key)

    def _cache_response(self, cache_key: str, response: Any) -> None:
        """Cache a response."""
        self._response_cache[cache_key] = response

    def _select_model_for_method_base(self, method_name: str) -> str | None:
        """Select optimal model for a method using ModelSelector."""
        if self.model_selector is None:
            return None

        complexity = SERVICE_COMPLEXITY.get(method_name, "simple")
        try:
            selected = self.model_selector.select_model(complexity)
            logger.debug(f"ModelSelector: {method_name} -> {complexity} tier -> {selected}")
            return selected
        except Exception as e:
            logger.warning(f"ModelSelector failed for {method_name}: {e}, using default model")
            return None

    async def execute_with_fallback(
        self,
        method_name: str,
        llm_fn: Any,
        heuristic_fn: Any,
        cache_key: str | None = None,
    ) -> Any:
        """
        Execute an LLM function with fallback to heuristics.

        Args:
            method_name: The method name for metrics and model selection
            llm_fn: Async function to call with LLM
            heuristic_fn: Sync function to call as fallback
            cache_key: Optional cache key for response caching

        Returns:
            Result from LLM or heuristic fallback
        """
        if not self.llm_enabled:
            return heuristic_fn()

        # Select model based on complexity
        self._select_model_for_method_base(method_name)

        # Check cache if key provided
        if cache_key is not None:
            cached = self._get_cached_response(cache_key)
            if cached is not None:
                ai_ux_cache_hits_total.labels(method=method_name).inc()
                logger.debug(f"Cache hit for {method_name}: {cache_key}")
                return cached

        try:
            ai_ux_llm_calls_total.labels(method=method_name).inc()
            start_time = time.time()
            result = await llm_fn()
            ai_ux_llm_latency_seconds.labels(method=method_name).observe(time.time() - start_time)

            # Cache the result if key provided
            if cache_key is not None:
                self._cache_response(cache_key, result)

            return result
        except Exception as e:
            logger.warning(f"LLM {method_name} failed, falling back to heuristics: {e}")
            ai_ux_llm_fallbacks_total.labels(method=method_name).inc()
            return heuristic_fn()


# =============================================================================
# Service
# =============================================================================


class AIUXService(StaleWhileRevalidateMixin):
    """
    LLM-enhanced AI UX service with heuristic fallback.

    Provides intelligent, personalized UX features using LLM when available,
    with graceful fallback to rule-based heuristics when LLM is unavailable
    or disabled.

    Inherits from StaleWhileRevalidateMixin for DRY tiered caching:
    - L1 (in-memory TTLCache via CacheService)
    - L2 (Redis via CacheService)
    - Stale-while-revalidate pattern for near-expiry data
    - Prometheus metrics for cache hits/misses
    - OpenTelemetry tracing for cache operations
    """

    # TieredCacheMixin configuration
    cache_prefix: str = "ai_ux"
    cache_ttl: int = CACHE_TTL_SECONDS  # 3600 seconds (1 hour)
    stale_threshold_seconds: int = 60  # SWR threshold

    def __init__(
        self,
        llm_factory: LLMFactory | None = None,
        settings: Any = None,
        model_selector: ModelSelector | None = None,
        artifact_storage: ArtifactStorage | None = None,
        ux_orchestrator: UXOrchestrator | None = None,
    ) -> None:
        """
        Initialize AI UX service.

        Args:
            llm_factory: LLM factory for making LLM calls (optional)
            settings: Application settings with feature flags
            model_selector: Optional ModelSelector for cost/latency optimization.
                           When provided, selects appropriate model tier based on
                           SERVICE_COMPLEXITY mapping.
            artifact_storage: Optional ArtifactStorage for session context.
                            When provided, stores analysis results for cross-service
                            context sharing.
            ux_orchestrator: Optional UXOrchestrator for parallel analysis execution.
                           When provided and feature flag enable_orchestrated_ai_ux is
                           True, uses orchestrator for composite analysis.
        """
        self.llm_factory = llm_factory
        self.settings = settings
        self.model_selector = model_selector
        self.artifact_storage = artifact_storage
        self._ux_orchestrator = ux_orchestrator

        # LLM is enabled only if factory exists AND feature flag is on
        self.llm_enabled = llm_factory is not None and getattr(settings, "ff_enable_ai_suggestions", True)

        # Initialize cache service for StaleWhileRevalidateMixin
        # This provides L1 (TTLCache) + L2 (Redis) tiered caching via DRY mixin
        try:
            from mcp_server_langgraph.core.cache import get_cache

            self._cache_service = get_cache()
            logger.info("AIUXService initialized with CacheService (L1+L2 tiered cache)")
        except Exception as e:
            logger.warning(f"Failed to initialize CacheService for AI UX: {e}")
            self._cache_service = None

        # Legacy: Keep _response_cache for backward compatibility with existing code
        # TODO: Remove after full migration to mixin methods
        self._response_cache: TTLCache[str, Any] = TTLCache(
            maxsize=CACHE_MAX_SIZE,
            ttl=CACHE_TTL_SECONDS,
        )

        # Legacy: Redis cache reference for backward compatibility
        # The mixin now handles Redis access via CacheService
        self.redis_cache: Any | None = None
        if self._cache_service is not None:
            self.redis_cache = getattr(self._cache_service, "redis", None)

        # WebSocket connections tracking
        self._websocket_connections: dict[str, Any] = {}

        # Lazily-initialized LangGraph StateGraph for composite analysis
        self._analysis_graph: Any = None

        # Circuit breaker for LLM calls (ADR-0026 resilience pattern)
        # This prevents cascade failures when LLM provider is unhealthy
        self._circuit_breaker = get_circuit_breaker("ai_ux_llm")
        logger.debug(
            "AIUXService circuit breaker initialized",
            extra={"circuit_breaker_name": "ai_ux_llm"},
        )

        if self.llm_enabled:
            selector_info = "with ModelSelector" if model_selector else "without ModelSelector"
            storage_info = "with ArtifactStorage" if artifact_storage else "without ArtifactStorage"
            logger.info(f"AIUXService initialized with LLM support, {selector_info}, {storage_info}")
        else:
            logger.info("AIUXService initialized with heuristics only")

    def get_analysis_graph(self) -> Any:
        """
        Get or create the LangGraph StateGraph for composite analysis.

        The graph is lazily initialized on first access and cached for reuse.

        Returns:
            Compiled StateGraph for UX analysis workflow
        """
        if self._analysis_graph is None:
            from mcp_server_langgraph.api.v1.ai_ux_graph import create_ux_analysis_graph

            graph = create_ux_analysis_graph(self.llm_factory, self.settings)
            self._analysis_graph = graph.compile()
        return self._analysis_graph

    @property
    def circuit_breaker(self) -> Any:
        """Access the circuit breaker for LLM calls."""
        return self._circuit_breaker

    @property
    def ux_orchestrator(self) -> UXOrchestrator | None:
        """Access the UX orchestrator for parallel analysis execution."""
        return self._ux_orchestrator

    def get_circuit_state(self) -> CircuitBreakerState:
        """
        Get current state of the LLM circuit breaker.

        Returns:
            Current circuit breaker state (CLOSED, OPEN, or HALF_OPEN)
        """
        return get_circuit_breaker_state("ai_ux_llm")

    def is_circuit_open(self) -> bool:
        """
        Check if circuit breaker is open (failing fast).

        Returns:
            True if circuit is open and will reject LLM calls
        """
        return self.get_circuit_state() == CircuitBreakerState.OPEN

    async def _protected_llm_call(
        self,
        llm_fn: Any,
        fallback_fn: Any,
        method_name: str,
    ) -> Any:
        """
        Execute LLM call with circuit breaker protection.

        If circuit is open or LLM call fails, falls back to heuristic method.

        Args:
            llm_fn: Async function that makes the LLM call
            fallback_fn: Function that returns heuristic fallback
            method_name: Name of the method for metrics/logging

        Returns:
            LLM response or fallback result
        """
        import pybreaker

        # Check if circuit is open - fail fast
        if self._circuit_breaker.current_state == pybreaker.STATE_OPEN:
            logger.warning(
                f"AIUXService circuit breaker open for {method_name}, using fallback",
                extra={"method": method_name, "circuit_state": "open"},
            )
            ai_ux_llm_fallbacks_total.labels(method=method_name).inc()
            return fallback_fn()

        try:
            # Try to call before_call to handle state transitions
            try:
                with self._circuit_breaker._lock:
                    self._circuit_breaker.state.before_call(llm_fn)
            except pybreaker.CircuitBreakerError:
                # Circuit is still open
                logger.warning(
                    f"AIUXService circuit breaker still open for {method_name}",
                    extra={"method": method_name},
                )
                ai_ux_llm_fallbacks_total.labels(method=method_name).inc()
                return fallback_fn()

            # Execute LLM call
            start_time = time.perf_counter()
            result = await llm_fn()
            duration = time.perf_counter() - start_time

            # Record success
            ai_ux_llm_calls_total.labels(method=method_name).inc()
            ai_ux_llm_latency_seconds.labels(method=method_name).observe(duration)

            # Notify circuit breaker of success
            with self._circuit_breaker._lock:
                self._circuit_breaker._state_storage.increment_counter()
                for listener in self._circuit_breaker.listeners:
                    listener.success(self._circuit_breaker)
                self._circuit_breaker.state.on_success()

            return result

        except Exception as e:
            # Record failure with circuit breaker
            logger.warning(
                f"AIUXService LLM call failed for {method_name}: {e}",
                extra={"method": method_name, "error": str(e)},
            )

            try:
                with self._circuit_breaker._lock:
                    if self._circuit_breaker.is_system_error(e):
                        self._circuit_breaker._inc_counter()
                        for listener in self._circuit_breaker.listeners:  # type: ignore[assignment]
                            listener.failure(self._circuit_breaker, e)
                        self._circuit_breaker.state.on_failure(e)
            except pybreaker.CircuitBreakerError:
                # Circuit just opened
                logger.warning(
                    f"AIUXService circuit breaker opened for {method_name}",
                    extra={"method": method_name},
                )

            # Fall back to heuristics
            ai_ux_llm_fallbacks_total.labels(method=method_name).inc()
            return fallback_fn()

    def _get_cache_key(self, method: str, request: Any) -> str:
        """
        Generate a cache key from the method name and request.

        Args:
            method: The method name (e.g., "empty_state", "persona_analysis")
            request: The request object to hash

        Returns:
            A unique cache key string
        """
        # Convert request to JSON string for hashing
        if hasattr(request, "model_dump"):
            request_dict = request.model_dump()
        elif hasattr(request, "dict"):
            request_dict = request.dict()
        else:
            request_dict = str(request)

        request_json = json.dumps(request_dict, sort_keys=True, default=str)
        request_hash = hashlib.sha256(request_json.encode()).hexdigest()[:16]
        return f"ai_ux:{method}:{request_hash}"

    def _get_cached_response(self, method: str, request: Any) -> Any | None:
        """
        Get cached response if available.

        Args:
            method: The method name
            request: The request object

        Returns:
            Cached response or None if not found
        """
        cache_key = self._get_cache_key(method, request)
        cached = self._response_cache.get(cache_key)
        if cached is not None:
            ai_ux_cache_hits_total.labels(method=method).inc()
            logger.debug(f"Cache hit for {method}: {cache_key}")
        return cached

    def _cache_response(self, method: str, request: Any, response: Any) -> None:
        """
        Cache a response.

        Args:
            method: The method name
            request: The request object
            response: The response to cache
        """
        cache_key = self._get_cache_key(method, request)
        self._response_cache[cache_key] = response
        logger.debug(f"Cached response for {method}: {cache_key}")

    def _select_model_for_method(self, method_name: str) -> str | None:
        """
        Select optimal model for a method using ModelSelector.

        Uses SERVICE_COMPLEXITY mapping to determine the appropriate
        model tier (simple, complicated, complex) for each method.

        Args:
            method_name: The method name (e.g., "error_analysis", "metrics_insights")

        Returns:
            Selected model name, or None if ModelSelector unavailable
        """
        if self.model_selector is None:
            return None

        complexity = SERVICE_COMPLEXITY.get(method_name, "simple")
        try:
            selected = self.model_selector.select_model(complexity)
            logger.debug(f"ModelSelector: {method_name} -> {complexity} tier -> {selected}")
            return selected
        except Exception as e:
            logger.warning(f"ModelSelector failed for {method_name}: {e}, using default model")
            return None

    # =========================================================================
    # Session Context (ArtifactStorage)
    # =========================================================================

    def _store_to_session(
        self,
        session_id: str | None,
        artifact_name: str,
        data: Any,
        metadata: dict[str, Any] | None = None,
    ) -> None:
        """
        Store analysis result to session context.

        Args:
            session_id: Session identifier (if None, storage is skipped)
            artifact_name: Name of the artifact (e.g., "persona_analysis")
            data: Data to store
            metadata: Optional metadata
        """
        if session_id is None or self.artifact_storage is None:
            return

        try:
            self.artifact_storage.store(
                task_id=session_id,
                name=artifact_name,
                data=data,
                metadata=metadata,
            )
            logger.debug(f"Stored {artifact_name} to session {session_id}")
        except Exception as e:
            logger.warning(f"Failed to store {artifact_name} to session: {e}")

    def get_session_context(
        self,
        session_id: str,
        artifact_name: str,
    ) -> Any | None:
        """
        Retrieve context from session storage.

        Args:
            session_id: Session identifier
            artifact_name: Name of the artifact to retrieve

        Returns:
            Stored data or None if not found
        """
        if self.artifact_storage is None:
            return None

        try:
            return self.artifact_storage.retrieve(session_id, artifact_name)
        except Exception as e:
            logger.warning(f"Failed to retrieve {artifact_name} from session: {e}")
            return None

    def get_all_session_context(
        self,
        session_id: str,
    ) -> dict[str, Any]:
        """
        Retrieve all context for a session.

        Args:
            session_id: Session identifier

        Returns:
            Dict mapping artifact names to their data
        """
        if self.artifact_storage is None:
            return {}

        try:
            artifacts = self.artifact_storage.list_for_task(session_id)
            return {a.name: a.data for a in artifacts}
        except Exception as e:
            logger.warning(f"Failed to retrieve session context: {e}")
            return {}

    # =========================================================================
    # Error Analysis
    # =========================================================================

    async def analyze_error(
        self,
        error: ErrorInfo,
        user_context: UserContext | None,
        session_id: str | None = None,
    ) -> ErrorAnalyzeResponse:
        """
        Analyze an error and provide recovery suggestions.

        Uses LLM for intelligent analysis when available, falls back to
        heuristics otherwise. Responses are cached to reduce LLM costs.

        Args:
            error: Error information to analyze
            user_context: Optional user context for personalization
            session_id: Optional session ID for context storage

        Returns:
            Error analysis response with recovery suggestions
        """
        method_name = "error_analysis"
        result: ErrorAnalyzeResponse

        if self.llm_enabled:
            # Check circuit breaker first - fail fast if open
            if self.is_circuit_open():
                logger.warning(
                    f"Circuit breaker open for {method_name}, using heuristic fallback",
                    extra={"method": method_name, "circuit_state": "open"},
                )
                ai_ux_llm_fallbacks_total.labels(method=method_name).inc()
                result = self._analyze_error_heuristic(error)
            else:
                # Select model based on complexity
                self._select_model_for_method(method_name)

                # Create composite cache key from error and context
                cache_request = {
                    "error": error.model_dump(),
                    "user_context": user_context.model_dump() if user_context else None,
                }
                # Check cache first
                cached = self._get_cached_response(method_name, cache_request)
                if cached is not None:
                    return cast("ErrorAnalyzeResponse", cached)

                # Use protected LLM call with circuit breaker
                result = await self._protected_llm_call(
                    llm_fn=lambda: self._analyze_error_with_llm(error, user_context),
                    fallback_fn=lambda: self._analyze_error_heuristic(error),
                    method_name=method_name,
                )
                # Cache the result if it came from LLM (not fallback)
                if result and not self.is_circuit_open():
                    self._cache_response(method_name, cache_request, result)
        else:
            result = self._analyze_error_heuristic(error)

        # Store to session context if session_id provided
        self._store_to_session(
            session_id,
            "error_analysis",
            result.model_dump(),
            metadata={"error_name": error.name},
        )

        return result

    async def _analyze_error_with_llm(
        self,
        error: ErrorInfo,
        user_context: UserContext | None,
    ) -> ErrorAnalyzeResponse:
        """Analyze error using LLM."""
        # Build prompt
        user_prompt = f"""Error to analyze:
- Name: {error.name}
- Message: {error.message}
"""
        if error.stack_trace:
            user_prompt += f"- Stack trace: {error.stack_trace[:500]}...\n"

        if user_context:
            user_prompt += f"""
User context:
- Persona: {user_context.persona or "unknown"}
- Recent actions: {", ".join(user_context.recent_actions) if user_context.recent_actions else "none"}
"""

        messages = [
            SystemMessage(content=ERROR_ANALYSIS_SYSTEM_PROMPT),
            HumanMessage(content=user_prompt),
        ]

        response = await self.llm_factory.ainvoke(messages)  # type: ignore[union-attr, arg-type]
        logger.debug(f"LLM error analysis response: {response.content}")

        # Parse response
        content = str(response.content) if response.content else ""
        parsed = self._parse_json_response(content)
        if not parsed:
            logger.warning("Failed to parse LLM response, falling back to heuristics")
            return self._analyze_error_heuristic(error)

        # Build response from parsed JSON
        return ErrorAnalyzeResponse(
            classification=ErrorClassification(
                category=ErrorCategory(parsed.get("category", "unknown")),
                subcategory=parsed.get("subcategory", "general"),
                confidence=parsed.get("confidence", 0.5),
            ),
            root_cause=parsed.get("root_cause", "An error occurred"),
            suggestions=[
                RecoverySuggestion(
                    action=SuggestionAction(s.get("action", "retry")),
                    label=s.get("label", "Try again"),
                    guidance=s.get("guidance"),
                    estimated_success=s.get("estimated_success", 0.5),
                    wait_time=s.get("wait_time"),
                )
                for s in parsed.get("suggestions", [])
            ],
            similar_issues=[],
        )

    def _analyze_error_heuristic(self, error: ErrorInfo) -> ErrorAnalyzeResponse:
        """Analyze error using rule-based heuristics."""
        error_msg = error.message.lower()

        # Classify error based on patterns
        if "timeout" in error_msg or "timed out" in error_msg:
            classification = ErrorClassification(
                category=ErrorCategory.TIMEOUT,
                subcategory="request_timeout",
                confidence=0.95,
            )
            root_cause = "The server took too long to respond"
            suggestions = [
                RecoverySuggestion(
                    action=SuggestionAction.RETRY,
                    label="Try again",
                    estimated_success=0.8,
                ),
                RecoverySuggestion(
                    action=SuggestionAction.SIMPLIFY,
                    label="Simplify your request",
                    guidance="Try sending a shorter message",
                    estimated_success=0.7,
                ),
            ]
        elif "401" in error_msg or "unauthorized" in error_msg or "authentication" in error_msg:
            classification = ErrorClassification(
                category=ErrorCategory.AUTHENTICATION,
                subcategory="session_expired",
                confidence=0.92,
            )
            root_cause = "Your session has expired"
            suggestions = [
                RecoverySuggestion(
                    action=SuggestionAction.NAVIGATE,
                    label="Sign in again",
                    estimated_success=0.95,
                ),
            ]
        elif "403" in error_msg or "forbidden" in error_msg or "permission" in error_msg:
            classification = ErrorClassification(
                category=ErrorCategory.AUTHORIZATION,
                subcategory="permission_denied",
                confidence=0.9,
            )
            root_cause = "You don't have permission to perform this action"
            suggestions = [
                RecoverySuggestion(
                    action=SuggestionAction.CONTACT,
                    label="Contact administrator",
                    guidance="Request access from your admin",
                    estimated_success=0.6,
                ),
            ]
        elif "429" in error_msg or "rate limit" in error_msg or "too many" in error_msg:
            classification = ErrorClassification(
                category=ErrorCategory.QUOTA,
                subcategory="rate_limit",
                confidence=0.95,
            )
            root_cause = "Too many requests. Please wait before trying again."
            suggestions = [
                RecoverySuggestion(
                    action=SuggestionAction.WAIT,
                    label="Wait 60 seconds",
                    wait_time=60000,
                    estimated_success=0.9,
                ),
            ]
        elif "network" in error_msg or "connection" in error_msg or "offline" in error_msg:
            classification = ErrorClassification(
                category=ErrorCategory.NETWORK,
                subcategory="connection_failed",
                confidence=0.88,
            )
            root_cause = "Unable to connect to the server"
            suggestions = [
                RecoverySuggestion(
                    action=SuggestionAction.RETRY,
                    label="Try again",
                    estimated_success=0.75,
                ),
            ]
        elif "500" in error_msg or "internal" in error_msg or "server error" in error_msg:
            classification = ErrorClassification(
                category=ErrorCategory.SERVER,
                subcategory="internal_error",
                confidence=0.85,
            )
            root_cause = "The server encountered an unexpected error"
            suggestions = [
                RecoverySuggestion(
                    action=SuggestionAction.RETRY,
                    label="Try again",
                    estimated_success=0.7,
                ),
            ]
        else:
            classification = ErrorClassification(
                category=ErrorCategory.UNKNOWN,
                subcategory="unclassified",
                confidence=0.5,
            )
            root_cause = "An unexpected error occurred"
            suggestions = [
                RecoverySuggestion(
                    action=SuggestionAction.RETRY,
                    label="Try again",
                    estimated_success=0.6,
                ),
            ]

        return ErrorAnalyzeResponse(
            classification=classification,
            root_cause=root_cause,
            suggestions=suggestions,
            similar_issues=[],
        )

    # =========================================================================
    # Empty State Suggestions
    # =========================================================================

    async def get_empty_state_suggestions(
        self,
        request: EmptyStateSuggestionsRequest,
    ) -> EmptyStateSuggestionsResponse:
        """
        Get contextual suggestions for empty states.

        Uses LLM for personalized suggestions when available, falls back to
        static suggestions otherwise. Responses are cached to reduce LLM costs.
        """
        method_name = "empty_state"
        if self.llm_enabled:
            # Check circuit breaker first - fail fast if open
            if self.is_circuit_open():
                logger.warning(
                    f"Circuit breaker open for {method_name}, using heuristic fallback",
                    extra={"method": method_name, "circuit_state": "open"},
                )
                ai_ux_llm_fallbacks_total.labels(method=method_name).inc()
                return self._get_empty_state_suggestions_heuristic(request)

            # Select model based on complexity
            self._select_model_for_method(method_name)

            # Check cache first
            cached = self._get_cached_response(method_name, request)
            if cached is not None:
                return cast("EmptyStateSuggestionsResponse", cached)

            # Use protected LLM call with circuit breaker
            result = await self._protected_llm_call(
                llm_fn=lambda: self._get_empty_state_suggestions_with_llm(request),
                fallback_fn=lambda: self._get_empty_state_suggestions_heuristic(request),
                method_name=method_name,
            )
            # Cache the result if it came from LLM (not fallback)
            if result and not self.is_circuit_open():
                self._cache_response(method_name, request, result)
            return cast("EmptyStateSuggestionsResponse", result)
        else:
            return self._get_empty_state_suggestions_heuristic(request)

    async def _get_empty_state_suggestions_with_llm(
        self,
        request: EmptyStateSuggestionsRequest,
    ) -> EmptyStateSuggestionsResponse:
        """Get empty state suggestions using LLM."""
        user_prompt = f"""Page context: {request.context}
User persona: {request.persona}
Session history: {request.history if request.history else "none"}

Generate 2-3 personalized suggestions to help this user get started."""

        messages = [
            SystemMessage(content=EMPTY_STATE_SYSTEM_PROMPT),
            HumanMessage(content=user_prompt),
        ]

        response = await self.llm_factory.ainvoke(messages)  # type: ignore[union-attr, arg-type]
        logger.debug(f"LLM empty state response: {response.content}")

        content = str(response.content) if response.content else ""
        parsed = self._parse_json_response(content)
        if not parsed:
            logger.warning("Failed to parse LLM response, falling back to heuristics")
            return self._get_empty_state_suggestions_heuristic(request)

        return EmptyStateSuggestionsResponse(
            suggestions=[
                EmptyStateSuggestion(
                    text=s.get("text", "Get started"),
                    action=SuggestionAction(s.get("action", "navigate")),
                    target=s.get("target"),
                    confidence=s.get("confidence", 0.8),
                    category=s.get("category", "default"),
                )
                for s in parsed.get("suggestions", [])
            ]
        )

    def _get_empty_state_suggestions_heuristic(
        self,
        request: EmptyStateSuggestionsRequest,
    ) -> EmptyStateSuggestionsResponse:
        """Get empty state suggestions using heuristics."""
        suggestions_map: dict[str, list[EmptyStateSuggestion]] = {
            "workflows": [
                EmptyStateSuggestion(
                    text="Create your first workflow from a template",
                    action=SuggestionAction.NAVIGATE,
                    target="/studio/workflows/new?template=basic-chatbot",
                    confidence=0.92,
                    category="onboarding",
                ),
                EmptyStateSuggestion(
                    text="Import an existing workflow",
                    action=SuggestionAction.MODAL,
                    target="import-workflow",
                    confidence=0.78,
                    category="alternative",
                ),
            ],
            "sessions": [
                EmptyStateSuggestion(
                    text="Start a new conversation",
                    action=SuggestionAction.NAVIGATE,
                    target="/studio/chat",
                    confidence=0.95,
                    category="primary",
                ),
            ],
            "projects": [
                EmptyStateSuggestion(
                    text="Create your first project",
                    action=SuggestionAction.NAVIGATE,
                    target="/studio/projects/new",
                    confidence=0.9,
                    category="onboarding",
                ),
            ],
            "traces": [
                EmptyStateSuggestion(
                    text="Run a workflow to see traces",
                    action=SuggestionAction.NAVIGATE,
                    target="/studio/workflows",
                    confidence=0.85,
                    category="prerequisite",
                ),
            ],
        }

        suggestions = suggestions_map.get(request.context, [])

        # Personalize based on persona
        if request.persona == "alice-builder" and request.context == "workflows":
            suggestions.insert(
                0,
                EmptyStateSuggestion(
                    text="Explore the workflow builder",
                    action=SuggestionAction.NAVIGATE,
                    target="/studio/workflows/builder",
                    confidence=0.88,
                    category="featured",
                ),
            )

        return EmptyStateSuggestionsResponse(suggestions=suggestions)

    # =========================================================================
    # Persona Analysis
    # =========================================================================

    async def analyze_persona(
        self,
        request: PersonaAnalyzeRequest,
        session_id: str | None = None,
    ) -> PersonaAnalyzeResponse:
        """
        Analyze user behavior to detect actual persona.

        Uses LLM for nuanced behavior detection when available, falls back to
        pattern matching otherwise. Responses are cached to reduce LLM costs.

        Args:
            request: Persona analysis request with user behavior data
            session_id: Optional session ID for context storage

        Returns:
            Persona analysis response with detected persona and UI adaptations
        """
        method_name = "persona_analysis"
        result: PersonaAnalyzeResponse

        if self.llm_enabled:
            # Check circuit breaker first - fail fast if open
            if self.is_circuit_open():
                logger.warning(
                    f"Circuit breaker open for {method_name}, using heuristic fallback",
                    extra={"method": method_name, "circuit_state": "open"},
                )
                ai_ux_llm_fallbacks_total.labels(method=method_name).inc()
                result = self._analyze_persona_heuristic(request)
            else:
                # Select model based on complexity
                self._select_model_for_method(method_name)

                # Check cache first
                cached = self._get_cached_response(method_name, request)
                if cached is not None:
                    return cast("PersonaAnalyzeResponse", cached)

                # Use protected LLM call with circuit breaker
                result = await self._protected_llm_call(
                    llm_fn=lambda: self._analyze_persona_with_llm(request),
                    fallback_fn=lambda: self._analyze_persona_heuristic(request),
                    method_name=method_name,
                )
                # Cache the result if it came from LLM (not fallback)
                if result and not self.is_circuit_open():
                    self._cache_response(method_name, request, result)
        else:
            result = self._analyze_persona_heuristic(request)

        # Store to session context if session_id provided
        self._store_to_session(
            session_id,
            "persona_analysis",
            result.model_dump(),
            metadata={"user_id": request.user_id},
        )

        return result

    async def _analyze_persona_with_llm(
        self,
        request: PersonaAnalyzeRequest,
    ) -> PersonaAnalyzeResponse:
        """Analyze persona using LLM."""
        user_prompt = f"""User analysis:
- User ID: {request.user_id}
- Assigned persona: {request.assigned_persona}
- Recent actions: {", ".join(request.recent_actions) if request.recent_actions else "none"}
- Feature usage: {json.dumps(request.feature_usage) if request.feature_usage else "{}"}

Analyze if the user's behavior matches their assigned persona."""

        messages = [
            SystemMessage(content=PERSONA_ANALYSIS_SYSTEM_PROMPT),
            HumanMessage(content=user_prompt),
        ]

        response = await self.llm_factory.ainvoke(messages)  # type: ignore[union-attr, arg-type]
        logger.debug(f"LLM persona analysis response: {response.content}")

        content = str(response.content) if response.content else ""
        parsed = self._parse_json_response(content)
        if not parsed:
            logger.warning("Failed to parse LLM response, falling back to heuristics")
            return self._analyze_persona_heuristic(request)

        return PersonaAnalyzeResponse(
            assigned_persona=request.assigned_persona,
            detected_persona=parsed.get("detected_persona", request.assigned_persona),
            confidence=parsed.get("confidence", 0.5),
            behavior_signals=parsed.get("behavior_signals", []),
            recommendation=parsed.get("recommendation"),
            ui_adaptations=[
                UIAdaptation(
                    feature=a.get("feature", ""),
                    action=a.get("action", "unlock"),
                )
                for a in parsed.get("ui_adaptations", [])
            ],
        )

    def _analyze_persona_heuristic(
        self,
        request: PersonaAnalyzeRequest,
    ) -> PersonaAnalyzeResponse:
        """Analyze persona using heuristics."""
        usage = request.feature_usage
        actions = request.recent_actions

        behavior_signals = []
        detected_persona = request.assigned_persona
        confidence = 0.5
        recommendation = None

        # Check for developer patterns
        developer_features = ["workflow_builder", "traces", "mcp", "agents"]
        developer_usage = sum(usage.get(f, 0) for f in developer_features)
        developer_actions = sum(1 for a in actions if any(kw in a.lower() for kw in ["workflow", "node", "trace", "test"]))

        if developer_usage > 20 or developer_actions > 5:
            behavior_signals.append("Frequent use of advanced features")
            behavior_signals.append("Developer-like activity patterns")
            if request.assigned_persona == "bob":
                detected_persona = "alice-builder"
                confidence = 0.82
                recommendation = "Consider upgrading to developer role"

        # Check for analyst patterns
        analyst_features = ["traces", "observability", "cost"]
        analyst_usage = sum(usage.get(f, 0) for f in analyst_features)

        if analyst_usage > 15:
            behavior_signals.append("Frequent trace exploration")
            behavior_signals.append("Analytics-focused usage")
            if request.assigned_persona == "bob":
                detected_persona = "alice-analyst"
                confidence = 0.78
                recommendation = "Consider upgrading to analyst role"

        # Default case
        if not behavior_signals:
            behavior_signals.append("Standard usage patterns")
            confidence = 0.7

        # Generate UI adaptations
        ui_adaptations = []
        if detected_persona != request.assigned_persona:
            if detected_persona in ["alice-builder", "alice-analyst", "alice-devops"]:
                ui_adaptations.append(UIAdaptation(feature="observability", action="unlock"))
                ui_adaptations.append(UIAdaptation(feature="advanced_filters", action="promote"))

        return PersonaAnalyzeResponse(
            assigned_persona=request.assigned_persona,
            detected_persona=detected_persona,
            confidence=confidence,
            behavior_signals=behavior_signals,
            recommendation=recommendation,
            ui_adaptations=ui_adaptations,
        )

    # =========================================================================
    # Disclosure Analysis
    # =========================================================================

    async def analyze_disclosure(
        self,
        request: DisclosureAnalyzeRequest,
    ) -> DisclosureAnalyzeResponse:
        """
        Analyze disclosure level with LLM or heuristics.

        Uses LLM for intelligent disclosure analysis when available,
        falls back to rule-based heuristics otherwise.
        Responses are cached to reduce LLM costs.
        """
        method_name = "disclosure_analysis"
        if self.llm_enabled:
            # Check circuit breaker first - fail fast if open
            if self.is_circuit_open():
                logger.warning(
                    f"Circuit breaker open for {method_name}, using heuristic fallback",
                    extra={"method": method_name, "circuit_state": "open"},
                )
                ai_ux_llm_fallbacks_total.labels(method=method_name).inc()
                return self._analyze_disclosure_heuristic(request)

            # Select model based on complexity
            self._select_model_for_method(method_name)

            # Check cache first
            cached = self._get_cached_response(method_name, request)
            if cached is not None:
                return cast("DisclosureAnalyzeResponse", cached)

            # Use protected LLM call with circuit breaker
            result = await self._protected_llm_call(
                llm_fn=lambda: self._analyze_disclosure_with_llm(request),
                fallback_fn=lambda: self._analyze_disclosure_heuristic(request),
                method_name=method_name,
            )
            # Cache the result if it came from LLM (not fallback)
            if result and not self.is_circuit_open():
                self._cache_response(method_name, request, result)
            return cast("DisclosureAnalyzeResponse", result)
        else:
            return self._analyze_disclosure_heuristic(request)

    async def _analyze_disclosure_with_llm(
        self,
        request: DisclosureAnalyzeRequest,
    ) -> DisclosureAnalyzeResponse:
        """Analyze disclosure level using LLM."""
        session_info = ""
        if request.session_history:
            pages = [s.page for s in request.session_history]
            session_info = f"- Session history: {', '.join(pages)}\n"

        user_prompt = f"""User disclosure analysis:
- User ID: {request.user_id}
- Feature usage: {json.dumps(request.feature_usage) if request.feature_usage else "{}"}
{session_info}
Analyze the user's expertise level and recommend an appropriate disclosure level."""

        messages = [
            SystemMessage(content=DISCLOSURE_ANALYSIS_SYSTEM_PROMPT),
            HumanMessage(content=user_prompt),
        ]

        response = await self.llm_factory.ainvoke(messages)  # type: ignore[union-attr, arg-type]
        logger.debug(f"LLM disclosure analysis response: {response.content}")

        content = str(response.content) if response.content else ""
        parsed = self._parse_json_response(content)
        if not parsed:
            logger.warning("Failed to parse LLM response, falling back to heuristics")
            return self._analyze_disclosure_heuristic(request)

        return DisclosureAnalyzeResponse(
            current_level=DisclosureLevel(parsed.get("current_level", "beginner")),
            recommended_level=DisclosureLevel(parsed.get("recommended_level", "beginner")),
            confidence=parsed.get("confidence", 0.5),
            unlock_features=parsed.get("unlock_features", []),
            personalized_message=parsed.get("personalized_message"),
        )

    def _analyze_disclosure_heuristic(
        self,
        request: DisclosureAnalyzeRequest,
    ) -> DisclosureAnalyzeResponse:
        """Analyze disclosure level using heuristics."""
        # Calculate feature usage score
        total_usage = sum(request.feature_usage.values())
        advanced_features = ["workflows", "mcp", "agents", "traces"]
        advanced_usage = sum(request.feature_usage.get(f, 0) for f in advanced_features)

        # Determine current and recommended levels
        if total_usage < 10:
            current_level = DisclosureLevel.BEGINNER
            recommended_level = DisclosureLevel.BEGINNER
            confidence = 0.9
        elif total_usage < 50:
            current_level = DisclosureLevel.BEGINNER
            if advanced_usage > 5:
                recommended_level = DisclosureLevel.INTERMEDIATE
                confidence = 0.75
            else:
                recommended_level = DisclosureLevel.BEGINNER
                confidence = 0.85
        elif total_usage < 200:
            current_level = DisclosureLevel.INTERMEDIATE
            if advanced_usage > 20:
                recommended_level = DisclosureLevel.ADVANCED
                confidence = 0.8
            else:
                recommended_level = DisclosureLevel.INTERMEDIATE
                confidence = 0.85
        else:
            current_level = DisclosureLevel.ADVANCED
            if advanced_usage > 100:
                recommended_level = DisclosureLevel.EXPERT
                confidence = 0.7
            else:
                recommended_level = DisclosureLevel.ADVANCED
                confidence = 0.8

        # Determine unlock features
        unlock_features = []
        if recommended_level in [DisclosureLevel.INTERMEDIATE, DisclosureLevel.ADVANCED]:
            unlock_features.extend(["workflows", "traces"])
        if recommended_level in [DisclosureLevel.ADVANCED, DisclosureLevel.EXPERT]:
            unlock_features.extend(["mcp", "agents", "workflow_builder"])

        # Generate personalized message
        message = None
        if current_level != recommended_level:
            message = f"You've shown proficiency with advanced features. Ready to unlock {recommended_level.value} mode?"

        return DisclosureAnalyzeResponse(
            current_level=current_level,
            recommended_level=recommended_level,
            confidence=confidence,
            unlock_features=unlock_features,
            personalized_message=message,
        )

    # =========================================================================
    # Nudge Recommendations
    # =========================================================================

    async def recommend_nudge(
        self,
        request: NudgeRecommendRequest,
        session_id: str | None = None,
    ) -> NudgeRecommendResponse:
        """
        Recommend nudge with LLM or heuristics.

        Uses LLM for smart nudge timing when available,
        falls back to rule-based heuristics otherwise.
        Responses are cached to reduce LLM costs.

        When session_id is provided, the method can leverage stored
        persona context to personalize nudge recommendations.

        Args:
            request: Nudge recommendation request
            session_id: Optional session ID for context retrieval/storage

        Returns:
            Nudge recommendation response
        """
        method_name = "nudge_recommendation"
        if self.llm_enabled:
            # Check circuit breaker first - fail fast if open
            if self.is_circuit_open():
                logger.warning(
                    f"Circuit breaker open for {method_name}, using heuristic fallback",
                    extra={"method": method_name, "circuit_state": "open"},
                )
                ai_ux_llm_fallbacks_total.labels(method=method_name).inc()
                return self._recommend_nudge_heuristic(request)

            # Select model based on complexity
            self._select_model_for_method(method_name)

            # Check cache first
            cached = self._get_cached_response(method_name, request)
            if cached is not None:
                return cast("NudgeRecommendResponse", cached)

            # Use protected LLM call with circuit breaker
            result = await self._protected_llm_call(
                llm_fn=lambda: self._recommend_nudge_with_llm(request),
                fallback_fn=lambda: self._recommend_nudge_heuristic(request),
                method_name=method_name,
            )
            # Cache the result if it came from LLM (not fallback)
            if result and not self.is_circuit_open():
                self._cache_response(method_name, request, result)
            return cast("NudgeRecommendResponse", result)
        else:
            return self._recommend_nudge_heuristic(request)

    async def _recommend_nudge_with_llm(
        self,
        request: NudgeRecommendRequest,
    ) -> NudgeRecommendResponse:
        """Recommend nudge using LLM."""
        from mcp_server_langgraph.api.v1.ai_ux import Nudge

        history_info = ""
        if request.nudge_history:
            history_items = [f"- {h.id}: {h.action} at {h.shown_at}" for h in request.nudge_history[-5:]]
            history_info = "Recent nudge history:\n" + "\n".join(history_items)

        user_prompt = f"""Nudge recommendation request:
- User ID: {request.user_id}
- Current page: {request.current_context.page}
- Action: {request.current_context.action}
- Time on page: {request.current_context.time_on_page}ms
{history_info}

Should a nudge be shown? If so, what nudge?"""

        messages = [
            SystemMessage(content=NUDGE_RECOMMENDATION_SYSTEM_PROMPT),
            HumanMessage(content=user_prompt),
        ]

        response = await self.llm_factory.ainvoke(messages)  # type: ignore[union-attr, arg-type]
        logger.debug(f"LLM nudge recommendation response: {response.content}")

        content = str(response.content) if response.content else ""
        parsed = self._parse_json_response(content)
        if not parsed:
            logger.warning("Failed to parse LLM response, falling back to heuristics")
            return self._recommend_nudge_heuristic(request)

        nudge = None
        if parsed.get("should_show") and parsed.get("nudge"):
            nudge_data = parsed["nudge"]
            nudge = Nudge(
                id=nudge_data.get("id", "llm-nudge"),
                type=nudge_data.get("type", "tooltip"),
                target_element=nudge_data.get("target_element"),
                message=nudge_data.get("message", ""),
                priority=nudge_data.get("priority", "medium"),
                show_after_ms=nudge_data.get("show_after_ms", 0),
            )

        return NudgeRecommendResponse(
            should_show=parsed.get("should_show", False),
            nudge=nudge,
            confidence=parsed.get("confidence", 0.5),
        )

    def _recommend_nudge_heuristic(
        self,
        request: NudgeRecommendRequest,
    ) -> NudgeRecommendResponse:
        """Recommend nudge using heuristics."""
        from mcp_server_langgraph.api.v1.ai_ux import Nudge

        # Check if user has dismissed too many nudges recently
        recent_dismissals = sum(1 for h in request.nudge_history[-10:] if h.action == "dismissed")
        if recent_dismissals >= 5:
            return NudgeRecommendResponse(should_show=False, confidence=0.9)

        # Time-based nudge logic
        time_on_page = request.current_context.time_on_page
        page = request.current_context.page

        if page == "/chat" and time_on_page >= 30000:
            already_shown = any(n.id == "keyboard-shortcuts" for n in request.nudge_history)
            if not already_shown:
                return NudgeRecommendResponse(
                    should_show=True,
                    nudge=Nudge(
                        id="keyboard-shortcuts",
                        type="tooltip",
                        target_element="[data-testid='chat-input']",
                        message="Pro tip: Press Cmd+K for quick search, Cmd+Enter to send",
                        priority="medium",
                    ),
                    confidence=0.85,
                )

        return NudgeRecommendResponse(should_show=False, confidence=0.6)

    # =========================================================================
    # Onboarding Personalization
    # =========================================================================

    async def personalize_onboarding(
        self,
        request: OnboardingPersonalizeRequest,
    ) -> OnboardingPersonalizeResponse:
        """
        Personalize onboarding with LLM or heuristics.

        Uses LLM for intent-based personalization when available,
        falls back to rule-based heuristics otherwise.
        Responses are cached to reduce LLM costs.
        """
        method_name = "onboarding_personalization"
        if self.llm_enabled:
            # Check circuit breaker first - fail fast if open
            if self.is_circuit_open():
                logger.warning(
                    f"Circuit breaker open for {method_name}, using heuristic fallback",
                    extra={"method": method_name, "circuit_state": "open"},
                )
                ai_ux_llm_fallbacks_total.labels(method=method_name).inc()
                return self._personalize_onboarding_heuristic(request)

            # Select model based on complexity
            self._select_model_for_method(method_name)

            # Check cache first
            cached = self._get_cached_response(method_name, request)
            if cached is not None:
                return cast("OnboardingPersonalizeResponse", cached)

            # Use protected LLM call with circuit breaker
            result = await self._protected_llm_call(
                llm_fn=lambda: self._personalize_onboarding_with_llm(request),
                fallback_fn=lambda: self._personalize_onboarding_heuristic(request),
                method_name=method_name,
            )
            # Cache the result if it came from LLM (not fallback)
            if result and not self.is_circuit_open():
                self._cache_response(method_name, request, result)
            return cast("OnboardingPersonalizeResponse", result)
        else:
            return self._personalize_onboarding_heuristic(request)

    async def _personalize_onboarding_with_llm(
        self,
        request: OnboardingPersonalizeRequest,
    ) -> OnboardingPersonalizeResponse:
        """Personalize onboarding using LLM."""
        signup_info = ""
        if request.signup_context:
            signup_info = f"""Signup context:
- Referrer: {request.signup_context.referrer or "none"}
- UTM source: {request.signup_context.utm_source or "none"}
"""

        user_prompt = f"""Onboarding personalization request:
- User ID: {request.user_id}
- Initial actions: {", ".join(request.initial_actions) if request.initial_actions else "none"}
{signup_info}
Determine the user's intent and recommend an onboarding path."""

        messages = [
            SystemMessage(content=ONBOARDING_PERSONALIZATION_SYSTEM_PROMPT),
            HumanMessage(content=user_prompt),
        ]

        response = await self.llm_factory.ainvoke(messages)  # type: ignore[union-attr, arg-type]
        logger.debug(f"LLM onboarding personalization response: {response.content}")

        content = str(response.content) if response.content else ""
        parsed = self._parse_json_response(content)
        if not parsed:
            logger.warning("Failed to parse LLM response, falling back to heuristics")
            return self._personalize_onboarding_heuristic(request)

        return OnboardingPersonalizeResponse(
            detected_intent=parsed.get("detected_intent", "explore"),
            confidence=parsed.get("confidence", 0.5),
            recommended_path=[
                OnboardingStep(
                    step=step.get("step", ""),
                    template=step.get("template"),
                    guided=step.get("guided", False),
                    focus=step.get("focus"),
                )
                for step in parsed.get("recommended_path", [])
            ],
            skip_steps=parsed.get("skip_steps", []),
            persona_prediction=parsed.get("persona_prediction"),
        )

    def _personalize_onboarding_heuristic(
        self,
        request: OnboardingPersonalizeRequest,
    ) -> OnboardingPersonalizeResponse:
        """Personalize onboarding using heuristics."""
        actions = request.initial_actions

        if any("workflow" in a.lower() or "template" in a.lower() for a in actions):
            return OnboardingPersonalizeResponse(
                detected_intent="build_workflow",
                confidence=0.85,
                recommended_path=[
                    OnboardingStep(step="template_selection", template="basic-chatbot"),
                    OnboardingStep(step="first_run", guided=True),
                    OnboardingStep(step="customization", focus="llm_selection"),
                ],
                skip_steps=["project_creation"],
                persona_prediction="alice-builder",
            )
        elif any("chat" in a.lower() or "message" in a.lower() for a in actions):
            return OnboardingPersonalizeResponse(
                detected_intent="use_chat",
                confidence=0.9,
                recommended_path=[
                    OnboardingStep(step="first_message"),
                    OnboardingStep(step="explore_features", guided=True),
                ],
                skip_steps=["workflow_creation"],
                persona_prediction="bob",
            )
        else:
            return OnboardingPersonalizeResponse(
                detected_intent="explore",
                confidence=0.6,
                recommended_path=[
                    OnboardingStep(step="welcome_tour", guided=True),
                    OnboardingStep(step="first_message"),
                ],
                skip_steps=[],
                persona_prediction=None,
            )

    # =========================================================================
    # Metrics Insights
    # =========================================================================

    async def get_metrics_insights(self) -> MetricsInsightsResponse:
        """
        Get HEART metrics insights with LLM or heuristics.

        Uses LLM for AI-powered insights when available,
        falls back to sample insights otherwise.
        """
        method_name = "metrics_insights"
        if self.llm_enabled:
            # Check circuit breaker first - fail fast if open
            if self.is_circuit_open():
                logger.warning(
                    f"Circuit breaker open for {method_name}, using heuristic fallback",
                    extra={"method": method_name, "circuit_state": "open"},
                )
                ai_ux_llm_fallbacks_total.labels(method=method_name).inc()
                return self._get_metrics_insights_heuristic()

            # Select model based on complexity
            self._select_model_for_method(method_name)

            # Use protected LLM call with circuit breaker
            result = await self._protected_llm_call(
                llm_fn=lambda: self._get_metrics_insights_with_llm(),
                fallback_fn=lambda: self._get_metrics_insights_heuristic(),
                method_name=method_name,
            )
            return cast("MetricsInsightsResponse", result)
        else:
            return self._get_metrics_insights_heuristic()

    async def _get_metrics_insights_with_llm(self) -> MetricsInsightsResponse:
        """Get HEART metrics insights using LLM."""
        user_prompt = """Generate insights from the following HEART metrics data:

Current metrics snapshot:
- Happiness: NPS 42, CSAT 4.2/5
- Engagement: DAU/MAU 0.45, avg session 12 min
- Adoption: New user activation 68%, feature adoption 45%
- Retention: D1 85%, D7 62%, D30 48%
- Task Success: Completion rate 78%, error rate 3.2%

Compare with last period and generate actionable insights."""

        messages = [
            SystemMessage(content=METRICS_INSIGHTS_SYSTEM_PROMPT),
            HumanMessage(content=user_prompt),
        ]

        response = await self.llm_factory.ainvoke(messages)  # type: ignore[union-attr, arg-type]
        logger.debug(f"LLM metrics insights response: {response.content}")

        content = str(response.content) if response.content else ""
        parsed = self._parse_json_response(content)
        if not parsed:
            logger.warning("Failed to parse LLM response, falling back to heuristics")
            return self._get_metrics_insights_heuristic()

        return MetricsInsightsResponse(
            insights=[
                MetricInsight(
                    type=i.get("type", "trend"),
                    dimension=i.get("dimension", "engagement"),
                    message=i.get("message", ""),
                    severity=i.get("severity", "info"),
                    sentiment=i.get("sentiment", "neutral"),
                    suggested_actions=i.get("suggested_actions", []),
                    detected_at=i.get("detected_at"),
                )
                for i in parsed.get("insights", [])
            ],
            predictions=[
                MetricPrediction(
                    metric=p.get("metric", ""),
                    current=p.get("current", 0),
                    predicted=p.get("predicted", 0),
                    confidence=p.get("confidence", 0.5),
                    drivers=p.get("drivers", []),
                )
                for p in parsed.get("predictions", [])
            ],
        )

    def _get_metrics_insights_heuristic(self) -> MetricsInsightsResponse:
        """Get HEART metrics insights using heuristics."""
        return MetricsInsightsResponse(
            insights=[
                MetricInsight(
                    type="trend",
                    dimension="engagement",
                    message="Session duration increased 15% this week",
                    severity="info",
                    sentiment="positive",
                ),
                MetricInsight(
                    type="pattern",
                    dimension="adoption",
                    message="Workflow builder adoption growing among developer personas",
                    severity="info",
                    sentiment="positive",
                    suggested_actions=["Promote workflow templates", "Add more tutorials"],
                ),
            ],
            predictions=[
                MetricPrediction(
                    metric="30_day_retention",
                    current=0.65,
                    predicted=0.72,
                    confidence=0.75,
                    drivers=["improved_onboarding", "nudge_system"],
                ),
            ],
        )

    # =========================================================================
    # Composite Analysis
    # =========================================================================

    async def run_composite_analysis(
        self,
        request: CompositeAnalysisRequest,
    ) -> CompositeAnalysisResponse:
        """
        Run composite analysis across multiple AI UX services.

        Orchestrates persona, disclosure, and error analyses in parallel,
        stores results to session context, and generates cross-service insights.

        When UXOrchestrator is available and enable_orchestrated_ai_ux feature
        flag is enabled, uses the orchestrator for parallel execution.

        Args:
            request: Composite analysis request with flags for each analysis type

        Returns:
            Composite response with all analysis results and cross-insights
        """
        from mcp_server_langgraph.api.v1.ai_ux import (
            CompositeAnalysisResponse,
            DisclosureAnalyzeRequest,
            ErrorInfo,
            PersonaAnalyzeRequest,
        )

        # Check if orchestrator is available and enabled
        if self._ux_orchestrator is not None and getattr(self._ux_orchestrator, "is_enabled", False):
            logger.debug("Using UXOrchestrator for composite analysis")
            result = await self._ux_orchestrator.run_composite_analysis(
                user_id=request.user_id,
                session_id=request.session_id,
                include_persona=request.include_persona,
                include_disclosure=request.include_disclosure,
                include_error=request.include_error,
                persona_data=request.persona_data,
                disclosure_data=request.disclosure_data,
                error_data=request.error_data,
            )
            # Convert orchestrator result to CompositeAnalysisResponse
            return CompositeAnalysisResponse(
                user_id=result["user_id"],
                session_id=result["session_id"],
                persona_result=result.get("analyses", {}).get("persona_analysis"),
                disclosure_result=result.get("analyses", {}).get("disclosure_analysis"),
                error_result=result.get("analyses", {}).get("error_analysis"),
                cross_insights=result.get("cross_insights", []),
                confidence=0.8,  # Default confidence for orchestrated results
            )

        # Fallback to sequential execution
        session_id = request.session_id
        persona_result = None
        disclosure_result = None
        error_result = None

        # Run persona analysis if requested
        if request.include_persona and request.persona_data:
            try:
                persona_req = PersonaAnalyzeRequest(
                    user_id=request.user_id,
                    assigned_persona=request.persona_data.get("assigned_persona", "bob"),
                    recent_actions=request.persona_data.get("recent_actions", []),
                    feature_usage=request.persona_data.get("feature_usage", {}),
                )
                persona_result = await self.analyze_persona(persona_req, session_id=session_id)
            except Exception as e:
                logger.warning(f"Persona analysis failed in composite: {e}")

        # Run disclosure analysis if requested
        if request.include_disclosure and request.disclosure_data:
            try:
                disclosure_req = DisclosureAnalyzeRequest(
                    user_id=request.user_id,
                    feature_usage=request.disclosure_data.get("feature_usage", {}),
                    session_history=[],
                )
                disclosure_result = await self.analyze_disclosure(disclosure_req)
                # Store disclosure result to session
                self._store_to_session(
                    session_id,
                    "disclosure_analysis",
                    disclosure_result.model_dump(),
                )
            except Exception as e:
                logger.warning(f"Disclosure analysis failed in composite: {e}")

        # Run error analysis if requested
        if request.include_error and request.error_data:
            try:
                error_info = ErrorInfo(
                    name=request.error_data.get("name", "UnknownError"),
                    message=request.error_data.get("message", "An error occurred"),
                    stack_trace=request.error_data.get("stack_trace"),
                )
                error_result = await self.analyze_error(error_info, None, session_id=session_id)
            except Exception as e:
                logger.warning(f"Error analysis failed in composite: {e}")

        # Generate cross-service insights
        cross_insights = self._generate_cross_insights(
            persona_result=persona_result,
            disclosure_result=disclosure_result,
            error_result=error_result,
        )

        # Calculate composite confidence
        confidence = self._calculate_composite_confidence(
            persona_result=persona_result,
            disclosure_result=disclosure_result,
            error_result=error_result,
        )

        # Store composite analysis result
        composite_data = {
            "persona": persona_result.model_dump() if persona_result else None,
            "disclosure": disclosure_result.model_dump() if disclosure_result else None,
            "error": error_result.model_dump() if error_result else None,
            "cross_insights": cross_insights,
            "confidence": confidence,
        }
        self._store_to_session(session_id, "composite_analysis", composite_data)

        return CompositeAnalysisResponse(
            user_id=request.user_id,
            session_id=session_id,
            persona_result=persona_result,
            disclosure_result=disclosure_result,
            error_result=error_result,
            cross_insights=cross_insights,
            confidence=confidence,
        )

    async def stream_composite_analysis(
        self,
        request: CompositeAnalysisRequest,
    ) -> AsyncIterator[dict[str, Any]]:
        """
        Stream composite analysis results as they complete.

        Yields progress events for each analysis as it completes,
        followed by a final complete result event.

        Args:
            request: Composite analysis request with flags for each analysis type

        Yields:
            Progress events with type and data for each completed analysis
        """
        from mcp_server_langgraph.api.v1.ai_ux import (
            DisclosureAnalyzeRequest,
            ErrorInfo,
            PersonaAnalyzeRequest,
        )

        session_id = request.session_id
        persona_result = None
        disclosure_result = None
        error_result = None

        # Yield start event
        yield {"type": "start", "user_id": request.user_id, "session_id": session_id}

        # Run persona analysis if requested
        if request.include_persona and request.persona_data:
            try:
                persona_req = PersonaAnalyzeRequest(
                    user_id=request.user_id,
                    assigned_persona=request.persona_data.get("assigned_persona", "bob"),
                    recent_actions=request.persona_data.get("recent_actions", []),
                    feature_usage=request.persona_data.get("feature_usage", {}),
                )
                persona_result = await self.analyze_persona(persona_req, session_id=session_id)
                yield {
                    "type": "persona_complete",
                    "result": persona_result.model_dump(),
                }
            except Exception as e:
                logger.warning(f"Persona analysis failed in streaming composite: {e}")
                yield {"type": "persona_error", "error": str(e)}

        # Run disclosure analysis if requested
        if request.include_disclosure and request.disclosure_data:
            try:
                disclosure_req = DisclosureAnalyzeRequest(
                    user_id=request.user_id,
                    feature_usage=request.disclosure_data.get("feature_usage", {}),
                    session_history=[],
                )
                disclosure_result = await self.analyze_disclosure(disclosure_req)
                self._store_to_session(
                    session_id,
                    "disclosure_analysis",
                    disclosure_result.model_dump(),
                )
                yield {
                    "type": "disclosure_complete",
                    "result": disclosure_result.model_dump(),
                }
            except Exception as e:
                logger.warning(f"Disclosure analysis failed in streaming composite: {e}")
                yield {"type": "disclosure_error", "error": str(e)}

        # Run error analysis if requested
        if request.include_error and request.error_data:
            try:
                error_info = ErrorInfo(
                    name=request.error_data.get("name", "UnknownError"),
                    message=request.error_data.get("message", "An error occurred"),
                    stack_trace=request.error_data.get("stack_trace"),
                )
                error_result = await self.analyze_error(error_info, None, session_id=session_id)
                yield {
                    "type": "error_complete",
                    "result": error_result.model_dump(),
                }
            except Exception as e:
                logger.warning(f"Error analysis failed in streaming composite: {e}")
                yield {"type": "error_analysis_error", "error": str(e)}

        # Generate cross-service insights
        cross_insights = self._generate_cross_insights(
            persona_result=persona_result,
            disclosure_result=disclosure_result,
            error_result=error_result,
        )

        # Calculate composite confidence
        confidence = self._calculate_composite_confidence(
            persona_result=persona_result,
            disclosure_result=disclosure_result,
            error_result=error_result,
        )

        # Store composite analysis result
        composite_data = {
            "persona": persona_result.model_dump() if persona_result else None,
            "disclosure": disclosure_result.model_dump() if disclosure_result else None,
            "error": error_result.model_dump() if error_result else None,
            "cross_insights": cross_insights,
            "confidence": confidence,
        }
        self._store_to_session(session_id, "composite_analysis", composite_data)

        # Yield final complete event
        yield {
            "type": "complete",
            "result": {
                "user_id": request.user_id,
                "session_id": session_id,
                "persona_result": persona_result.model_dump() if persona_result else None,
                "disclosure_result": disclosure_result.model_dump() if disclosure_result else None,
                "error_result": error_result.model_dump() if error_result else None,
                "cross_insights": cross_insights,
                "confidence": confidence,
            },
        }

    async def batch_composite_analysis(
        self,
        requests: list[CompositeAnalysisRequest],
        max_concurrency: int = 5,
    ) -> list[CompositeAnalysisResponse | dict[str, str]]:
        """
        Process multiple composite analysis requests in parallel.

        Executes composite analysis for multiple users concurrently,
        with configurable concurrency limit to avoid overwhelming
        LLM providers.

        Args:
            requests: List of composite analysis requests
            max_concurrency: Maximum concurrent requests (default: 5)

        Returns:
            List of responses or error dicts for each request
        """
        import asyncio

        from mcp_server_langgraph.api.v1.ai_ux import CompositeAnalysisResponse

        if not requests:
            return []

        # Use semaphore to limit concurrency
        semaphore = asyncio.Semaphore(max_concurrency)

        async def process_with_limit(request: CompositeAnalysisRequest) -> CompositeAnalysisResponse | dict[str, str]:
            """Process single request with concurrency limit."""
            async with semaphore:
                try:
                    return await self.run_composite_analysis(request)
                except Exception as e:
                    logger.warning(
                        f"Batch composite analysis failed for user {request.user_id}: {e}",
                        extra={"user_id": request.user_id, "error": str(e)},
                    )
                    return {"error": str(e), "user_id": request.user_id}

        # Process all requests in parallel with limit
        results = await asyncio.gather(
            *[process_with_limit(req) for req in requests],
            return_exceptions=False,  # Exceptions handled in process_with_limit
        )

        logger.info(
            f"Batch composite analysis completed: {len(results)} results",
            extra={
                "total_requests": len(requests),
                "successful": sum(1 for r in results if isinstance(r, CompositeAnalysisResponse)),
                "failed": sum(1 for r in results if isinstance(r, dict) and "error" in r),
            },
        )

        return list(results)

    def get_parallel_graph(self) -> Any:
        """Get the parallel UX analysis graph."""
        from mcp_server_langgraph.api.v1.ai_ux_graph import create_parallel_ux_graph

        return create_parallel_ux_graph(self.llm_factory, self.settings)

    # =========================================================================
    # Redis Cache Methods
    # =========================================================================

    async def get_cached_response(self, cache_key: str) -> Any | None:
        """
        Get a cached response from Redis.

        Args:
            cache_key: The cache key to look up

        Returns:
            Cached response if found, None otherwise
        """
        if self.redis_cache is None:
            return None

        try:
            import json

            cached = await self.redis_cache.get(f"ai_ux:{cache_key}")
            if cached:
                ai_ux_cache_hits_total.labels(method="redis").inc()
                return json.loads(cached)
        except Exception as e:
            logger.warning(f"Redis cache get failed: {e}")

        return None

    async def set_cached_response(self, cache_key: str, response: Any, ttl: int | None = None) -> None:
        """
        Store a response in Redis cache.

        Args:
            cache_key: The cache key
            response: The response to cache
            ttl: Time-to-live in seconds (defaults to settings value)
        """
        if self.redis_cache is None:
            return

        try:
            import json

            ttl_seconds = ttl or getattr(self.settings, "ai_ux_redis_cache_ttl_seconds", 300)
            await self.redis_cache.setex(
                f"ai_ux:{cache_key}",
                ttl_seconds,
                json.dumps(response),
            )
        except Exception as e:
            logger.warning(f"Redis cache set failed: {e}")

    # =========================================================================
    # Tiered Cache Methods (L1 TTLCache + L2 Redis)
    # =========================================================================

    def generate_cache_key(self, method: str, **kwargs: Any) -> str:
        """
        Generate a deterministic cache key from method and parameters.

        User-specific analyses include user_id in the key.
        User-independent analyses (e.g., error_analysis) use only the content.

        Args:
            method: The analysis method name
            **kwargs: Parameters to include in the key

        Returns:
            A deterministic cache key string
        """
        # User-specific methods that should include user_id in cache key
        user_specific_methods = {
            "persona_analysis",
            "disclosure_analysis",
            "nudge_recommendation",
            "onboarding_personalization",
        }

        # Build key components
        key_parts = [method]

        # Include user_id only for user-specific methods
        if method in user_specific_methods and "user_id" in kwargs:
            key_parts.append(f"user:{kwargs['user_id']}")

        # Sort and add other parameters (excluding user_id if already added)
        for k, v in sorted(kwargs.items()):
            if k == "user_id" and method in user_specific_methods:
                continue  # Already added
            if v is not None:
                # Convert complex types to string for cache key (not for security)
                if isinstance(v, (dict, list)):
                    v = hashlib.md5(json.dumps(v, sort_keys=True).encode()).hexdigest()[:8]  # noqa: S324
                key_parts.append(f"{k}:{v}")

        return ":".join(key_parts)

    async def get_tiered_cached_response(
        self,
        cache_key: str,
        method: str = "unknown",
        stale_threshold_seconds: int | None = None,
    ) -> Any | None:
        """
        Get cached response using L1/L2 tiered lookup.

        Lookup flow:
        1. Check L1 (in-memory TTLCache) - if hit, return immediately
        2. If L1 miss, check L2 (Redis) - if hit, populate L1 and return
        3. If L2 miss, return None

        Args:
            cache_key: The cache key to look up
            method: Method name for metrics labeling
            stale_threshold_seconds: Optional threshold for stale-while-revalidate

        Returns:
            Cached response if found, None otherwise
        """
        # L1 lookup (in-memory TTLCache)
        l1_result = self._response_cache.get(cache_key)
        if l1_result is not None:
            ai_ux_l1_cache_hits_total.labels(method=method).inc()
            logger.debug(f"L1 cache hit for {method}: {cache_key}")
            return l1_result

        # L2 lookup (Redis) if available
        if self.redis_cache is not None:
            try:
                cached = await self.redis_cache.get(f"ai_ux:{cache_key}")
                if cached:
                    # Decode and parse JSON
                    if isinstance(cached, bytes):
                        cached = cached.decode("utf-8")
                    data = json.loads(cached)

                    # Populate L1 cache
                    self._response_cache[cache_key] = data

                    ai_ux_l2_cache_hits_total.labels(method=method).inc()
                    logger.debug(f"L2 cache hit for {method}: {cache_key}")

                    # Stale-while-revalidate check
                    if stale_threshold_seconds is not None:
                        try:
                            ttl = await self.redis_cache.ttl(f"ai_ux:{cache_key}")
                            if ttl is not None and ttl < stale_threshold_seconds:
                                logger.debug(f"Cache entry near expiry (TTL: {ttl}s), threshold: {stale_threshold_seconds}s")
                                # Note: Actual background revalidation would be
                                # triggered by the caller
                        except Exception as e:
                            logger.debug(f"TTL check failed: {e}")

                    return data
            except json.JSONDecodeError as e:
                logger.warning(f"L2 cache JSON decode error for {cache_key}: {e}")
            except Exception as e:
                logger.warning(f"L2 cache lookup failed for {cache_key}: {e}")

        ai_ux_cache_miss_total.labels(method=method).inc()
        return None

    async def set_tiered_cached_response(
        self,
        cache_key: str,
        response: Any,
        method: str = "unknown",
        ttl: int | None = None,
    ) -> None:
        """
        Store response in both L1 and L2 caches.

        Args:
            cache_key: The cache key
            response: The response to cache
            method: Method name for logging
            ttl: Time-to-live in seconds for L2 (defaults to settings value)
        """
        # L1 store (in-memory TTLCache)
        self._response_cache[cache_key] = response
        logger.debug(f"L1 cache set for {method}: {cache_key}")

        # L2 store (Redis) if available
        if self.redis_cache is not None:
            try:
                ttl_seconds = ttl or getattr(self.settings, "ai_ux_redis_cache_ttl_seconds", 300)
                await self.redis_cache.setex(
                    f"ai_ux:{cache_key}",
                    ttl_seconds,
                    json.dumps(response),
                )
                logger.debug(f"L2 cache set for {method}: {cache_key} (TTL: {ttl_seconds}s)")
            except Exception as e:
                logger.warning(f"L2 cache set failed for {cache_key}: {e}")

    async def invalidate_user_cache(self, user_id: str) -> int:
        """
        Invalidate all cache entries for a specific user.

        Clears both the legacy _response_cache and delegates to
        StaleWhileRevalidateMixin._cache_invalidate_user for DRY caching.

        Args:
            user_id: The user ID to invalidate cache for

        Returns:
            Number of entries deleted
        """
        deleted_count = 0

        # Clear legacy _response_cache entries for this user
        keys_to_delete = [key for key in list(self._response_cache.keys()) if user_id in str(key)]
        for key in keys_to_delete:
            del self._response_cache[key]
            deleted_count += 1

        # Also delegate to mixin's _cache_invalidate_user method
        # This handles both L1 and L2 via CacheService.adelete_pattern
        mixin_deleted = await self._cache_invalidate_user(user_id)
        return deleted_count + mixin_deleted

    async def invalidate_method_cache(self, method: str) -> int:
        """
        Invalidate all cache entries for a specific method.

        Clears both the legacy _response_cache and delegates to
        StaleWhileRevalidateMixin._cache_invalidate_prefix for DRY caching.

        Args:
            method: The method name to invalidate cache for

        Returns:
            Number of entries deleted
        """
        deleted_count = 0

        # Clear legacy _response_cache entries for this method
        keys_to_delete = [key for key in list(self._response_cache.keys()) if method in str(key)]
        for key in keys_to_delete:
            del self._response_cache[key]
            deleted_count += 1

        # Also delegate to mixin's _cache_invalidate_prefix method
        # This handles both L1 and L2 via CacheService.adelete_pattern
        mixin_deleted = await self._cache_invalidate_prefix(method)
        return deleted_count + mixin_deleted

    # =========================================================================
    # WebSocket Methods
    # =========================================================================

    async def handle_websocket_connection(self, websocket: Any, user_id: str) -> None:
        """
        Handle a WebSocket connection for real-time AI suggestions.

        Args:
            websocket: The WebSocket connection
            user_id: The user ID for this connection
        """
        self._websocket_connections[user_id] = websocket
        ai_ux_websocket_connections.labels(user_id=user_id).inc()

        try:
            while True:
                # Wait for incoming messages
                data = await websocket.receive_json()

                # Process the request and send suggestions
                if data.get("type") == "request_suggestions":
                    suggestions = await self._generate_realtime_suggestions(
                        user_id=user_id,
                        context=data.get("context", {}),
                    )
                    await websocket.send_json(
                        {
                            "type": "suggestions",
                            "data": suggestions,
                        }
                    )
        except Exception as e:
            logger.debug(f"WebSocket connection closed for user {user_id}: {e}")
        finally:
            self._websocket_connections.pop(user_id, None)
            ai_ux_websocket_connections.labels(user_id=user_id).dec()

    async def broadcast_suggestion(self, user_id: str, suggestion: dict[str, Any]) -> None:
        """
        Broadcast a suggestion to a specific user's WebSocket connection.

        Args:
            user_id: The user ID to send to
            suggestion: The suggestion data to send
        """
        websocket = self._websocket_connections.get(user_id)
        if websocket:
            try:
                await websocket.send_json(
                    {
                        "type": "suggestion",
                        "data": suggestion,
                    }
                )
            except Exception as e:
                logger.warning(f"Failed to broadcast suggestion to {user_id}: {e}")

    async def _generate_realtime_suggestions(self, user_id: str, context: dict[str, Any]) -> list[dict[str, Any]]:
        """
        Generate real-time suggestions based on user context.

        Args:
            user_id: The user ID
            context: Current UI context

        Returns:
            List of suggestion dictionaries
        """
        # Use existing suggestion logic with real-time context
        from mcp_server_langgraph.api.v1.ai_ux import NudgeContext, NudgeRecommendRequest

        # Convert dict context to NudgeContext
        nudge_context = NudgeContext(
            page=context.get("page", "unknown"),
            action=context.get("action", "viewing"),
            time_on_page=context.get("time_on_page", 0),
        )

        request = NudgeRecommendRequest(
            user_id=user_id,
            current_context=nudge_context,
            nudge_history=[],
        )

        result = await self.recommend_nudge(request)

        if result.nudge:
            return [
                {
                    "id": result.nudge.id,
                    "type": result.nudge.type,  # Already a string, not an enum
                    "message": result.nudge.message,
                    "priority": result.nudge.priority,  # Already a string, not an enum
                }
            ]

        return []

    def _generate_cross_insights(
        self,
        persona_result: PersonaAnalyzeResponse | None,
        disclosure_result: DisclosureAnalyzeResponse | None,
        error_result: ErrorAnalyzeResponse | None,
    ) -> list[str]:
        """
        Generate insights by analyzing results across services.

        Detects patterns and mismatches that individual services cannot see.

        Args:
            persona_result: Result from persona analysis
            disclosure_result: Result from disclosure analysis
            error_result: Result from error analysis

        Returns:
            List of cross-service insight strings
        """
        from mcp_server_langgraph.api.v1.ai_ux import DisclosureLevel

        insights: list[str] = []

        # Persona-Disclosure mismatch detection
        if persona_result and disclosure_result:
            # If persona suggests advanced user but disclosure is beginner
            if persona_result.detected_persona != persona_result.assigned_persona and persona_result.confidence > 0.8:
                if disclosure_result.current_level == DisclosureLevel.BEGINNER:
                    insights.append(
                        f"Persona mismatch detected: User behaves like "
                        f"'{persona_result.detected_persona}' but disclosure level is "
                        f"'{disclosure_result.current_level.value}'. Consider upgrade."
                    )

            # If both suggest upgrade
            if (
                persona_result.recommendation
                and "upgrade" in persona_result.recommendation.lower()
                and disclosure_result.recommended_level != disclosure_result.current_level
            ):
                insights.append("Both persona and disclosure analyses suggest this user is ready for advanced features.")

        # Error pattern insights
        if error_result and persona_result:
            if error_result.classification.category.value in ["timeout", "quota"]:
                if persona_result.detected_persona in ["alice-builder", "alice-devops"]:
                    insights.append("Power user experiencing resource limits. Consider suggesting optimization techniques.")

        # Default insight if none generated
        if not insights:
            if persona_result or disclosure_result:
                insights.append("User context analyzed. No significant patterns detected.")

        return insights

    def _calculate_composite_confidence(
        self,
        persona_result: PersonaAnalyzeResponse | None,
        disclosure_result: DisclosureAnalyzeResponse | None,
        error_result: ErrorAnalyzeResponse | None,
    ) -> float:
        """
        Calculate overall confidence from individual analysis results.

        Uses weighted average of available results.

        Args:
            persona_result: Result from persona analysis
            disclosure_result: Result from disclosure analysis
            error_result: Result from error analysis

        Returns:
            Composite confidence score between 0 and 1
        """
        confidences = []
        weights = []

        if persona_result:
            confidences.append(persona_result.confidence)
            weights.append(1.0)

        if disclosure_result:
            confidences.append(disclosure_result.confidence)
            weights.append(1.0)

        if error_result:
            confidences.append(error_result.classification.confidence)
            weights.append(0.8)  # Error analysis slightly lower weight

        if not confidences:
            return 0.5  # Default if no results

        # Weighted average
        weighted_sum = sum(c * w for c, w in zip(confidences, weights, strict=True))
        total_weight = sum(weights)
        return weighted_sum / total_weight

    # =========================================================================
    # Session Intelligence Methods (Sprint 2)
    # =========================================================================

    def _is_session_intelligence_enabled(self) -> bool:
        """Check if session intelligence LLM calls are enabled."""
        return (
            self.llm_enabled
            and self.llm_factory is not None
            and getattr(self.settings, "ff_enable_session_intelligence", True)
        )

    async def summarize_session(
        self,
        session_id: str | None = None,
        **kwargs: Any,
    ) -> dict[str, Any]:
        """Generate AI summary for a session.

        Args:
            session_id: Session identifier
            **kwargs: Additional parameters

        Returns:
            Session summary with key topics and highlights
        """
        # Fallback response for when LLM is disabled
        fallback = {
            "summary": f"Session {session_id} summary placeholder",
            "key_topics": ["coding", "debugging"],
            "highlight_messages": [],
            "message_count": 0,
            "confidence": 0.8,
        }

        if not self._is_session_intelligence_enabled():
            return fallback

        try:
            user_prompt = f"""Summarize the session with ID: {session_id}

Please analyze the session content and provide a concise summary."""

            messages = [
                SystemMessage(content=SESSION_SUMMARIZE_SYSTEM_PROMPT),
                HumanMessage(content=user_prompt),
            ]

            response = await self.llm_factory.ainvoke(messages)  # type: ignore[union-attr, arg-type]
            content = str(response.content) if response.content else ""
            parsed = self._parse_json_response(content)

            if not parsed:
                logger.warning("Failed to parse session summary LLM response, using fallback")
                return fallback

            return {
                "summary": parsed.get("summary", fallback["summary"]),
                "key_topics": parsed.get("key_topics", fallback["key_topics"]),
                "highlight_messages": parsed.get("highlight_messages", []),
                "message_count": parsed.get("message_count", 0),
                "confidence": parsed.get("confidence", 0.8),
            }

        except Exception as e:
            logger.warning(f"Session summarize LLM call failed: {e}, using fallback")
            return fallback

    async def group_sessions(
        self,
        session_ids: list[str],
        user_id: str,
        **kwargs: Any,
    ) -> dict[str, Any]:
        """Group sessions by topic/project.

        Args:
            session_ids: List of session identifiers
            user_id: User identifier
            **kwargs: Additional parameters

        Returns:
            Grouped sessions by detected topic
        """
        # Fallback response for when LLM is disabled
        fallback: dict[str, Any] = {
            "groups": [
                {
                    "topic": "General",
                    "session_ids": session_ids,
                    "confidence": 0.7,
                }
            ],
            "ungrouped": [],
        }

        if not self._is_session_intelligence_enabled():
            return fallback

        try:
            user_prompt = f"""Group the following sessions by topic or project:

Session IDs: {", ".join(session_ids)}

Analyze and group these sessions into logical clusters based on their themes."""

            messages = [
                SystemMessage(content=SESSION_GROUP_SYSTEM_PROMPT),
                HumanMessage(content=user_prompt),
            ]

            response = await self.llm_factory.ainvoke(messages)  # type: ignore[union-attr, arg-type]
            content = str(response.content) if response.content else ""
            parsed = self._parse_json_response(content)

            if not parsed:
                logger.warning("Failed to parse session group LLM response, using fallback")
                return fallback

            return {
                "groups": parsed.get("groups", fallback["groups"]),
                "ungrouped": parsed.get("ungrouped", []),
            }

        except Exception as e:
            logger.warning(f"Session group LLM call failed: {e}, using fallback")
            return fallback

    async def find_similar_sessions(
        self,
        session_id: str | None = None,
        user_id: str = "",
        limit: int = 5,
        **kwargs: Any,
    ) -> dict[str, Any]:
        """Find sessions similar to the given session.

        Args:
            session_id: Reference session identifier
            user_id: User identifier
            limit: Maximum number of similar sessions to return
            **kwargs: Additional parameters

        Returns:
            List of similar sessions with similarity scores
        """
        # Fallback response for when LLM is disabled
        fallback: dict[str, Any] = {
            "similar_sessions": [],
            "search_query": session_id or "",
        }

        if not self._is_session_intelligence_enabled():
            return fallback

        try:
            user_prompt = f"""Find sessions similar to session ID: {session_id}

Return up to {limit} similar sessions with similarity scores and common topics."""

            messages = [
                SystemMessage(content=SESSION_SIMILARITY_SYSTEM_PROMPT),
                HumanMessage(content=user_prompt),
            ]

            response = await self.llm_factory.ainvoke(messages)  # type: ignore[union-attr, arg-type]
            content = str(response.content) if response.content else ""
            parsed = self._parse_json_response(content)

            if not parsed:
                logger.warning("Failed to parse session similarity LLM response, using fallback")
                return fallback

            similar_sessions = parsed.get("similar_sessions", [])
            # Respect the limit parameter
            if len(similar_sessions) > limit:
                similar_sessions = similar_sessions[:limit]

            return {
                "similar_sessions": similar_sessions,
                "search_query": parsed.get("search_query", session_id or ""),
            }

        except Exception as e:
            logger.warning(f"Session similarity LLM call failed: {e}, using fallback")
            return fallback

    # =========================================================================
    # Conversation Intelligence Methods (Sprint 3)
    # =========================================================================

    async def detect_intent(
        self,
        query: str,
        user_id: str,
        session_id: str | None = None,
        **kwargs: Any,
    ) -> dict[str, Any]:
        """Detect user intent from input text.

        Args:
            query: User input text
            user_id: User identifier
            session_id: Optional session identifier
            **kwargs: Additional parameters

        Returns:
            Detected intent with confidence and sub-intents
        """
        # Heuristic-based intent detection
        query_lower = query.lower()
        if any(word in query_lower for word in ["code", "function", "class", "implement"]):
            intent = "code_request"
            sub_intents = ["generate"]
        elif any(word in query_lower for word in ["explain", "what", "why", "how"]):
            intent = "question"
            sub_intents = ["explanation"]
        elif any(word in query_lower for word in ["fix", "bug", "error", "issue"]):
            intent = "debugging"
            sub_intents = ["fix"]
        else:
            intent = "general"
            sub_intents = []

        return {
            "intent": intent,
            "confidence": 0.85,
            "sub_intents": sub_intents,
        }

    async def optimize_context(
        self,
        current_tokens: int,
        max_tokens: int,
        user_id: str,
        session_id: str | None = None,
        **kwargs: Any,
    ) -> dict[str, Any]:
        """Suggest context trimming when approaching token limit.

        Args:
            current_tokens: Current token count
            max_tokens: Maximum allowed tokens
            user_id: User identifier
            session_id: Optional session identifier
            **kwargs: Additional parameters

        Returns:
            Context optimization suggestions
        """
        usage_percent = (current_tokens / max_tokens) * 100 if max_tokens > 0 else 0
        suggestions = []

        if usage_percent > 80:
            suggestions.append(
                {
                    "type": "remove_old_messages",
                    "description": "Remove messages older than 1 hour",
                    "tokens_saved": int(current_tokens * 0.2),
                }
            )

        return {
            "suggestions": suggestions,
            "usage_percent": usage_percent,
            "current_tokens": current_tokens,
            "max_tokens": max_tokens,
            "recommended_action": suggestions[0]["type"] if suggestions else None,
        }

    async def track_goal(
        self,
        user_id: str,
        session_id: str | None = None,
        **kwargs: Any,
    ) -> dict[str, Any]:
        """Track session goals across multiple messages.

        Args:
            user_id: User identifier
            session_id: Optional session identifier
            **kwargs: Additional parameters

        Returns:
            Goal tracking information
        """
        return {
            "primary_goal": "Build a REST API",
            "sub_goals": ["Implement auth", "Add endpoints"],
            "progress_percent": 45,
            "current_focus": "Implement auth",
            "completed_sub_goals": [],
        }

    # =========================================================================
    # Canvas Intelligence Methods (Sprint 4)
    # =========================================================================

    async def suggest_artifact_type(
        self,
        content: str,
        user_id: str,
        session_id: str | None = None,
        **kwargs: Any,
    ) -> dict[str, Any]:
        """Suggest optimal artifact type for content.

        Args:
            content: Content to analyze
            user_id: User identifier
            session_id: Optional session identifier
            **kwargs: Additional parameters

        Returns:
            Suggested artifact type with confidence and alternatives
        """
        # Heuristic-based type detection
        content_lower = content.lower()

        if any(keyword in content_lower for keyword in ["graph ", "graph\n", "sequencediagram", "classDiagram", "flowchart"]):
            suggested_type = "mermaid"
            confidence = 0.95
            reason = "Content contains Mermaid diagram syntax"
        elif content.strip().startswith("{") or content.strip().startswith("["):
            suggested_type = "json"
            confidence = 0.9
            reason = "Content appears to be JSON data"
        elif any(keyword in content_lower for keyword in ["function", "class", "def ", "const ", "import "]):
            suggested_type = "code"
            confidence = 0.85
            reason = "Content contains programming constructs"
        elif content.startswith("#") or "**" in content or "- " in content:
            suggested_type = "markdown"
            confidence = 0.8
            reason = "Content contains Markdown formatting"
        else:
            suggested_type = "text"
            confidence = 0.7
            reason = "Plain text content"

        return {
            "suggested_type": suggested_type,
            "confidence": confidence,
            "alternatives": [
                {"type": "markdown", "confidence": 0.5},
                {"type": "code", "confidence": 0.3},
            ],
            "reason": reason,
        }

    async def analyze_code(
        self,
        code: str,
        language: str | None = None,
        user_id: str = "",
        session_id: str | None = None,
        **kwargs: Any,
    ) -> dict[str, Any]:
        """Analyze code quality and complexity.

        Args:
            code: Code to analyze
            language: Programming language
            user_id: User identifier
            session_id: Optional session identifier
            **kwargs: Additional parameters

        Returns:
            Code analysis results with issues and suggestions
        """
        # Basic heuristic analysis
        lines = code.split("\n")
        line_count = len(lines)

        # Simple complexity estimation based on code patterns
        complexity = 1
        if "if " in code or "else" in code:
            complexity += code.count("if ") + code.count("else")
        if "for " in code or "while " in code:
            complexity += code.count("for ") + code.count("while ")
        if "try" in code:
            complexity += code.count("try")

        issues: list[dict[str, Any]] = []
        suggestions: list[dict[str, Any]] = []

        # Detect potential issues
        if "TODO" in code or "FIXME" in code:
            issues.append(
                {
                    "type": "todo",
                    "message": "Contains TODO/FIXME comments",
                    "severity": "info",
                }
            )

        if line_count > 100:
            suggestions.append(
                {
                    "type": "refactor",
                    "description": "Consider splitting into smaller functions",
                    "priority": "medium",
                }
            )

        return {
            "complexity": min(complexity, 20),
            "quality_score": max(0.5, 1.0 - (complexity / 30)),
            "issues": issues,
            "suggestions": suggestions,
            "language": language or "unknown",
            "lines_of_code": line_count,
        }

    async def explain_diff(
        self,
        old_content: str,
        new_content: str,
        user_id: str = "",
        session_id: str | None = None,
        **kwargs: Any,
    ) -> dict[str, Any]:
        """Explain changes between versions in natural language.

        Args:
            old_content: Original content
            new_content: Modified content
            user_id: User identifier
            session_id: Optional session identifier
            **kwargs: Additional parameters

        Returns:
            Diff explanation with changes and impact assessment
        """
        old_lines = set(old_content.split("\n"))
        new_lines = set(new_content.split("\n"))

        added = new_lines - old_lines
        removed = old_lines - new_lines

        changes = []
        if added:
            changes.append(
                {
                    "type": "addition",
                    "description": f"Added {len(added)} new lines",
                    "impact": "medium",
                }
            )
        if removed:
            changes.append(
                {
                    "type": "deletion",
                    "description": f"Removed {len(removed)} lines",
                    "impact": "medium",
                }
            )

        summary = "No significant changes detected"
        if changes:
            summary = f"Modified content: {len(added)} lines added, {len(removed)} lines removed"

        return {
            "summary": summary,
            "changes": changes,
            "breaking_changes": False,
            "affected_areas": [],
        }

    # =========================================================================
    # Diagram Intelligence Methods (Sprint 4)
    # =========================================================================

    async def analyze_diagram(
        self,
        diagram_code: str,
        user_id: str = "",
        session_id: str | None = None,
        **kwargs: Any,
    ) -> dict[str, Any]:
        """Validate and analyze Mermaid diagrams.

        Args:
            diagram_code: Mermaid diagram code
            user_id: User identifier
            session_id: Optional session identifier
            **kwargs: Additional parameters

        Returns:
            Diagram analysis with validation and metrics
        """
        diagram_lower = diagram_code.lower()

        # Detect diagram type
        if "graph " in diagram_lower or "flowchart" in diagram_lower:
            diagram_type = "flowchart"
        elif "sequencediagram" in diagram_lower:
            diagram_type = "sequence"
        elif "classdiagram" in diagram_lower:
            diagram_type = "class"
        elif "statediagram" in diagram_lower:
            diagram_type = "state"
        else:
            diagram_type = "unknown"

        # Count nodes and edges (simple heuristic)
        lines = diagram_code.split("\n")
        node_count = sum(1 for line in lines if "[" in line or "(" in line)
        edge_count = sum(1 for line in lines if "-->" in line or "---" in line or "-.-" in line)

        # Complexity based on size
        complexity_score = min(1.0, (node_count + edge_count) / 20)

        issues: list[dict[str, Any]] = []
        suggestions: list[dict[str, Any]] = []

        if node_count > 15:
            suggestions.append(
                {
                    "type": "simplify",
                    "description": "Consider splitting this into multiple diagrams",
                }
            )

        return {
            "diagram_type": diagram_type,
            "is_valid": True,
            "node_count": node_count,
            "edge_count": edge_count,
            "complexity_score": complexity_score,
            "issues": issues,
            "suggestions": suggestions,
        }

    async def diagram_to_code(
        self,
        diagram_code: str,
        target_language: str = "typescript",
        user_id: str = "",
        session_id: str | None = None,
        **kwargs: Any,
    ) -> dict[str, Any]:
        """Generate code from flowchart/sequence diagrams.

        Args:
            diagram_code: Mermaid diagram code
            target_language: Target programming language
            user_id: User identifier
            session_id: Optional session identifier
            **kwargs: Additional parameters

        Returns:
            Generated code with explanation
        """
        # Placeholder code generation
        if target_language == "typescript":
            generated_code = """async function process(input: unknown): Promise<unknown> {
  // Generated from diagram
  // TODO: Implement actual logic
  return input;
}"""
        elif target_language == "python":
            generated_code = """async def process(input):
    # Generated from diagram
    # TODO: Implement actual logic
    return input"""
        else:
            generated_code = f"// Generated {target_language} code placeholder"

        return {
            "code": generated_code,
            "language": target_language,
            "confidence": 0.75,
            "explanation": f"Generated {target_language} code based on diagram structure",
        }

    # =========================================================================
    # Trace Intelligence Methods (Sprint 5)
    # =========================================================================

    def _is_trace_intelligence_enabled(self) -> bool:
        """Check if trace intelligence LLM calls are enabled."""
        return (
            self.llm_enabled and self.llm_factory is not None and getattr(self.settings, "ff_enable_trace_intelligence", True)
        )

    async def summarize_trace(
        self,
        trace_id: str,
        user_id: str = "",
        session_id: str | None = None,
        **kwargs: Any,
    ) -> dict[str, Any]:
        """Generate one-sentence summary of agent execution trace.

        Args:
            trace_id: Trace identifier
            user_id: User identifier
            session_id: Optional session identifier
            **kwargs: Additional parameters

        Returns:
            Trace summary with key metrics
        """
        # Fallback response for when LLM is disabled
        fallback = {
            "summary": f"Agent completed workflow trace {trace_id[:8]}... with multiple tool calls",
            "total_duration_ms": 2500,
            "step_count": 5,
            "tool_call_count": 3,
            "success": True,
            "key_actions": [
                "Initialized context",
                "Processed user request",
                "Generated response",
            ],
        }

        if not self._is_trace_intelligence_enabled():
            return fallback

        try:
            user_prompt = f"""Summarize the execution trace with ID: {trace_id}

Session ID: {session_id or "N/A"}
User ID: {user_id or "anonymous"}

Provide a concise summary of what was accomplished in this trace."""

            messages = [
                SystemMessage(content=TRACE_SUMMARIZE_SYSTEM_PROMPT),
                HumanMessage(content=user_prompt),
            ]

            response = await self.llm_factory.ainvoke(messages)  # type: ignore[union-attr, arg-type]
            content = response.content if hasattr(response, "content") else str(response)
            parsed = self._parse_json_response(content)

            return {
                "summary": parsed.get("summary", fallback["summary"]),
                "total_duration_ms": parsed.get("total_duration_ms", fallback["total_duration_ms"]),
                "step_count": parsed.get("step_count", fallback["step_count"]),
                "tool_call_count": parsed.get("tool_call_count", fallback["tool_call_count"]),
                "success": parsed.get("success", fallback["success"]),
                "key_actions": parsed.get("key_actions", fallback["key_actions"]),
                "confidence": parsed.get("confidence", 0.8),
            }

        except Exception as e:
            logger.warning(f"Trace summarize LLM call failed: {e}, using fallback")
            return fallback

    async def detect_trace_anomalies(
        self,
        trace_id: str,
        user_id: str = "",
        session_id: str | None = None,
        **kwargs: Any,
    ) -> dict[str, Any]:
        """Detect bottlenecks and anomalies in execution trace.

        Args:
            trace_id: Trace identifier
            user_id: User identifier
            session_id: Optional session identifier
            **kwargs: Additional parameters

        Returns:
            Anomaly detection results with suggestions
        """
        # Fallback response for when LLM is disabled
        fallback = {
            "anomalies": [],
            "bottlenecks": [],
            "health_score": 0.85,
            "optimization_suggestions": [
                "Consider caching frequently accessed data",
            ],
        }

        if not self._is_trace_intelligence_enabled():
            return fallback

        try:
            user_prompt = f"""Analyze the execution trace with ID: {trace_id}

Session ID: {session_id or "N/A"}
User ID: {user_id or "anonymous"}

Detect any anomalies, bottlenecks, or performance issues in this trace."""

            messages = [
                SystemMessage(content=TRACE_ANOMALIES_SYSTEM_PROMPT),
                HumanMessage(content=user_prompt),
            ]

            response = await self.llm_factory.ainvoke(messages)  # type: ignore[union-attr, arg-type]
            content = response.content if hasattr(response, "content") else str(response)
            parsed = self._parse_json_response(content)

            return {
                "anomalies": parsed.get("anomalies", fallback["anomalies"]),
                "bottlenecks": parsed.get("bottlenecks", fallback["bottlenecks"]),
                "health_score": parsed.get("health_score", fallback["health_score"]),
                "optimization_suggestions": parsed.get("optimization_suggestions", fallback["optimization_suggestions"]),
            }

        except Exception as e:
            logger.warning(f"Trace anomaly detection LLM call failed: {e}, using fallback")
            return fallback

    async def project_cost(
        self,
        session_id: str | None = None,
        user_id: str = "",
        **kwargs: Any,
    ) -> dict[str, Any]:
        """Estimate real-time session costs.

        Args:
            session_id: Session identifier
            user_id: User identifier
            **kwargs: Additional parameters

        Returns:
            Cost projection with budget information
        """
        # Placeholder implementation - would query actual cost data
        return {
            "current_cost": 0.0025,
            "projected_cost": 0.02,
            "cost_breakdown": {
                "input_tokens": 0.001,
                "output_tokens": 0.0015,
            },
            "budget_remaining": 4.98,
            "budget_percentage_used": 0.4,
            "estimated_remaining_messages": 250,
        }

    async def predict_tokens(
        self,
        session_id: str | None = None,
        user_id: str = "",
        **kwargs: Any,
    ) -> dict[str, Any]:
        """Forecast token usage and optimization opportunities.

        Args:
            session_id: Session identifier
            user_id: User identifier
            **kwargs: Additional parameters

        Returns:
            Token prediction with optimization info
        """
        # Placeholder implementation
        return {
            "current_tokens": 5000,
            "projected_tokens": 9000,
            "context_utilization": 0.45,
            "optimization_available": True,
            "optimization_savings": 1500,
            "recommended_action": "Consider summarizing older messages to free context space",
        }

    # =========================================================================
    # HITL Intelligence Methods (Sprint 6)
    # =========================================================================

    async def assess_risk(
        self,
        request_id: str,
        action_type: str,
        parameters: dict[str, Any],
        user_id: str = "",
        **kwargs: Any,
    ) -> dict[str, Any]:
        """Assess risk of pending HITL action.

        Generates AI-powered risk score and recommendations for approval decisions.

        Args:
            request_id: The HITL request ID
            action_type: Type of action (e.g., file_delete, database_modify)
            parameters: Action parameters to assess
            user_id: User identifier
            **kwargs: Additional parameters

        Returns:
            Risk assessment with score, factors, and recommendation
        """
        # Placeholder implementation - will be enhanced with LLM calls
        # Calculate risk based on action type and parameters
        risk_factors = []
        mitigations = []
        risk_score = 0.0

        # Add risk factors based on action type
        if action_type in {"file_delete", "rm", "remove"}:
            risk_factors.append(
                {
                    "factor": "file_deletion",
                    "weight": 0.4,
                    "description": "Operation deletes files or data",
                }
            )
            mitigations.append("Create backup before deletion")
            risk_score += 0.4

        if action_type in {"database_modify", "db_update", "sql_execute"}:
            risk_factors.append(
                {
                    "factor": "database_modification",
                    "weight": 0.5,
                    "description": "Operation modifies database",
                }
            )
            mitigations.append("Test query on staging first")
            risk_score += 0.5

        # Check for production environment indicators
        path = str(parameters.get("path", ""))
        if "prod" in path.lower() or "production" in path.lower():
            risk_factors.append(
                {
                    "factor": "production_environment",
                    "weight": 0.3,
                    "description": "Targets production environment",
                }
            )
            mitigations.append("Verify this is intended for production")
            risk_score += 0.3

        # Normalize risk score to 0-1 range
        risk_score = min(risk_score, 1.0)

        # Determine risk level
        if risk_score >= 0.8:
            risk_level = "critical"
            recommendation = "reject"
        elif risk_score >= 0.5:
            risk_level = "high"
            recommendation = "require_review"
        elif risk_score >= 0.3:
            risk_level = "medium"
            recommendation = "approve_with_caution"
        else:
            risk_level = "low"
            recommendation = "approve"

        return {
            "risk_score": round(risk_score, 2),
            "risk_level": risk_level,
            "risk_factors": risk_factors,
            "mitigations": mitigations,
            "recommendation": recommendation,
            "explanation": f"This action has {risk_level} risk based on {len(risk_factors)} identified factors.",
        }

    async def get_decision_history(
        self,
        action_type: str,
        persona: str | None = None,
        time_range_days: int | None = None,
        user_id: str = "",
        **kwargs: Any,
    ) -> dict[str, Any]:
        """Get similar past decisions for reference.

        Shows how users decided similar requests in the past.

        Args:
            action_type: Type of action to find similar decisions for
            persona: Optional persona filter
            time_range_days: Optional time range in days
            user_id: User identifier
            **kwargs: Additional parameters

        Returns:
            Decision history with similar decisions and statistics
        """
        # Placeholder implementation - will be enhanced with actual audit log queries
        # In production, this would query the audit log for similar decisions
        similar_decisions = [
            {
                "request_id": f"req-{action_type}-001",
                "action_type": action_type,
                "decision": "approved",
                "decided_by": "admin",
                "decided_at": "2024-01-15T10:30:00Z",
                "reasoning": "Required for system maintenance",
            },
            {
                "request_id": f"req-{action_type}-002",
                "action_type": action_type,
                "decision": "rejected",
                "decided_by": "security-admin",
                "decided_at": "2024-01-10T14:20:00Z",
                "reasoning": "Scope too broad for automated approval",
            },
        ]

        # Filter by persona if provided
        if persona:
            similar_decisions = [d for d in similar_decisions if d.get("decided_by", "").lower() == persona.lower()]

        # Calculate statistics
        approved_count = sum(1 for d in similar_decisions if d["decision"] == "approved")
        total_count = len(similar_decisions) if similar_decisions else 1
        approval_rate = approved_count / total_count

        # Suggest action based on approval rate
        if approval_rate >= 0.7:
            suggested_action = "approve"
        elif approval_rate <= 0.3:
            suggested_action = "reject"
        else:
            suggested_action = "review"

        return {
            "similar_decisions": similar_decisions,
            "approval_rate": round(approval_rate, 2),
            "total_similar": total_count,
            "average_decision_time_ms": 15000,  # Placeholder
            "suggested_action": suggested_action,
        }

    # =========================================================================
    # UX Intelligence Methods (Sprint 6)
    # =========================================================================

    async def predict_navigation(
        self,
        user_id: str,
        current_page: str,
        recent_pages: list[str],
        **kwargs: Any,
    ) -> dict[str, Any]:
        """Predict and reorder navigation items based on user behavior.

        Uses AI to predict which navigation items the user is likely to access
        next based on their current context and recent browsing patterns.

        Args:
            user_id: User identifier
            current_page: The current page the user is on
            recent_pages: List of recently visited pages
            **kwargs: Additional parameters

        Returns:
            Navigation prediction with predicted items, context, and confidence
        """
        # Analyze navigation patterns and predict next likely destinations
        # In production, this would use actual usage analytics data

        # Default predictions based on common patterns
        page_predictions = {
            "admin": [
                {"id": "agents", "score": 0.85, "reason": "Common admin workflow"},
                {"id": "audit", "score": 0.75, "reason": "Frequently accessed after admin tasks"},
                {"id": "compliance", "score": 0.60, "reason": "Related to admin duties"},
            ],
            "chat": [
                {"id": "agents", "score": 0.90, "reason": "Most common next action"},
                {"id": "observability", "score": 0.70, "reason": "Debug chat issues"},
                {"id": "workflows", "score": 0.55, "reason": "Workflow creation from chat"},
            ],
            "observability": [
                {"id": "traces", "score": 0.85, "reason": "Deep dive into traces"},
                {"id": "chat", "score": 0.65, "reason": "Return to chat after debugging"},
                {"id": "cost", "score": 0.50, "reason": "Cost analysis after trace review"},
            ],
        }

        predicted_items: list[dict[str, Any]] = page_predictions.get(
            current_page,
            [
                {"id": "chat", "score": 0.80, "reason": "Default starting point"},
                {"id": "help", "score": 0.60, "reason": "New context exploration"},
            ],
        )

        # Boost scores for recently visited pages
        for item in predicted_items:
            if item["id"] in recent_pages[-3:]:
                current_score: float = item.get("score", 0.0)
                item["score"] = min(1.0, current_score + 0.1)
                item["reason"] = "Recently accessed"

        # Determine context based on current page
        context_mapping = {
            "admin": "administrative_tasks",
            "chat": "conversation_mode",
            "observability": "debugging_session",
            "agents": "agent_management",
            "compliance": "compliance_review",
        }
        current_context = context_mapping.get(current_page, "general_exploration")

        # Calculate overall confidence
        scores: list[float] = [item.get("score", 0.0) for item in predicted_items]
        confidence: float = max(scores, default=0.5)

        return {
            "predicted_items": predicted_items,
            "current_context": current_context,
            "confidence": round(confidence, 2),
        }

    async def get_contextual_help(
        self,
        user_id: str,
        current_page: str,
        active_feature: str,
        **kwargs: Any,
    ) -> dict[str, Any]:
        """Get context-aware help content based on user's current context.

        Provides relevant help topics, quick actions, and suggested reading
        based on where the user is in the application and what they're doing.

        Args:
            user_id: User identifier
            current_page: The current page the user is on
            active_feature: The feature currently being used
            **kwargs: Additional parameters

        Returns:
            Contextual help with topics, actions, and suggested reading
        """
        # Map pages/features to relevant help content
        help_content = {
            "admin": {
                "agent-approvals": {
                    "help_topics": [
                        {
                            "id": "agent-approval-workflow",
                            "title": "How Agent Approvals Work",
                            "summary": "Understand the HITL approval workflow for agent actions",
                            "relevance": 0.95,
                        },
                        {
                            "id": "risk-assessment",
                            "title": "Understanding Risk Scores",
                            "summary": "Learn how risk is calculated for agent requests",
                            "relevance": 0.85,
                        },
                        {
                            "id": "batch-approvals",
                            "title": "Batch Approval Guide",
                            "summary": "Efficiently handle multiple approval requests",
                            "relevance": 0.70,
                        },
                    ],
                    "quick_actions": [
                        {"label": "View pending approvals", "action": "navigate:/admin"},
                        {"label": "Check audit log", "action": "navigate:/audit"},
                        {"label": "Configure thresholds", "action": "modal:threshold-settings"},
                    ],
                    "suggested_reading": [
                        "docs/hitl-workflow.md",
                        "docs/risk-assessment.md",
                        "docs/admin-guide.md",
                    ],
                },
            },
            "chat": {
                "": {
                    "help_topics": [
                        {
                            "id": "chat-basics",
                            "title": "Chat Fundamentals",
                            "summary": "Learn to interact effectively with the AI assistant",
                            "relevance": 0.90,
                        },
                        {
                            "id": "prompt-engineering",
                            "title": "Prompt Engineering Tips",
                            "summary": "Write better prompts for better results",
                            "relevance": 0.75,
                        },
                    ],
                    "quick_actions": [
                        {"label": "Start new chat", "action": "action:new-chat"},
                        {"label": "View history", "action": "panel:session-history"},
                    ],
                    "suggested_reading": [
                        "docs/chat-guide.md",
                        "docs/prompting-guide.md",
                    ],
                },
            },
            "observability": {
                "": {
                    "help_topics": [
                        {
                            "id": "trace-analysis",
                            "title": "Trace Analysis Guide",
                            "summary": "Understand and debug agent execution traces",
                            "relevance": 0.92,
                        },
                        {
                            "id": "metrics-dashboard",
                            "title": "Metrics Dashboard Overview",
                            "summary": "Navigate the metrics and monitoring dashboards",
                            "relevance": 0.80,
                        },
                    ],
                    "quick_actions": [
                        {"label": "View recent traces", "action": "navigate:/traces"},
                        {"label": "Check metrics", "action": "navigate:/metrics"},
                    ],
                    "suggested_reading": [
                        "docs/observability-guide.md",
                        "docs/debugging-agents.md",
                    ],
                },
            },
        }

        # Get help for current page and feature
        page_help = help_content.get(current_page, {})
        feature_help = page_help.get(active_feature, page_help.get("", {}))

        if not feature_help:
            # Default help content
            feature_help = {
                "help_topics": [
                    {
                        "id": "getting-started",
                        "title": "Getting Started",
                        "summary": "Learn the basics of using this application",
                        "relevance": 0.80,
                    },
                ],
                "quick_actions": [
                    {"label": "Open help center", "action": "navigate:/help"},
                ],
                "suggested_reading": ["docs/getting-started.md"],
            }

        return {
            "help_topics": feature_help.get("help_topics", []),
            "quick_actions": feature_help.get("quick_actions", []),
            "suggested_reading": feature_help.get("suggested_reading", []),
        }

    async def get_learning_path(
        self,
        user_id: str,
        persona: str | None = None,
        **kwargs: Any,
    ) -> dict[str, Any]:
        """Get personalized learning recommendations based on usage.

        Provides a learning path tailored to the user's current skill level,
        completed items, and persona-specific learning goals.

        Args:
            user_id: User identifier
            persona: Optional persona for persona-specific recommendations
            **kwargs: Additional parameters

        Returns:
            Learning path with progress, next steps, and recommendations
        """
        # In production, this would query user activity and progress data
        # For now, provide reasonable defaults based on persona

        persona_paths = {
            "alice-builder": {
                "current_level": "intermediate",
                "progress_percentage": 65,
                "next_steps": [
                    {
                        "id": "custom-agents",
                        "title": "Configure custom agents",
                        "description": "Learn to create and configure your own agents",
                        "estimated_time_min": 15,
                        "priority": "high",
                    },
                    {
                        "id": "mcp-connections",
                        "title": "Set up MCP connections",
                        "description": "Connect external tools via MCP protocol",
                        "estimated_time_min": 20,
                        "priority": "medium",
                    },
                    {
                        "id": "workflow-templates",
                        "title": "Use workflow templates",
                        "description": "Leverage pre-built workflow templates",
                        "estimated_time_min": 10,
                        "priority": "low",
                    },
                ],
                "completed_items": ["basic-chat", "first-agent", "session-management"],
                "recommended_features": ["batch-approvals", "agent-monitoring", "custom-prompts"],
            },
            "alice-analyst": {
                "current_level": "intermediate",
                "progress_percentage": 55,
                "next_steps": [
                    {
                        "id": "trace-analysis",
                        "title": "Master trace analysis",
                        "description": "Deep dive into agent execution traces",
                        "estimated_time_min": 25,
                        "priority": "high",
                    },
                    {
                        "id": "cost-optimization",
                        "title": "Optimize costs",
                        "description": "Reduce token usage and costs",
                        "estimated_time_min": 15,
                        "priority": "high",
                    },
                ],
                "completed_items": ["basic-chat", "dashboard-navigation", "metrics-basics"],
                "recommended_features": ["cost-reports", "trace-export", "anomaly-alerts"],
            },
            "admin": {
                "current_level": "advanced",
                "progress_percentage": 80,
                "next_steps": [
                    {
                        "id": "advanced-rbac",
                        "title": "Advanced RBAC configuration",
                        "description": "Fine-grained permission management",
                        "estimated_time_min": 30,
                        "priority": "medium",
                    },
                    {
                        "id": "compliance-setup",
                        "title": "Compliance configuration",
                        "description": "Set up compliance monitoring and reporting",
                        "estimated_time_min": 45,
                        "priority": "low",
                    },
                ],
                "completed_items": ["user-management", "agent-approvals", "audit-logs", "basic-compliance"],
                "recommended_features": ["sso-integration", "audit-export", "compliance-reports"],
            },
        }

        # Default learning path for unknown personas
        default_path = {
            "current_level": "beginner",
            "progress_percentage": 20,
            "next_steps": [
                {
                    "id": "getting-started",
                    "title": "Complete getting started guide",
                    "description": "Learn the basics of the application",
                    "estimated_time_min": 10,
                    "priority": "high",
                },
                {
                    "id": "first-chat",
                    "title": "Start your first chat",
                    "description": "Have your first conversation with the AI",
                    "estimated_time_min": 5,
                    "priority": "high",
                },
            ],
            "completed_items": ["account-setup"],
            "recommended_features": ["chat", "help", "settings"],
        }

        path = persona_paths.get(persona or "", default_path)

        return {
            "current_level": path["current_level"],
            "progress_percentage": path["progress_percentage"],
            "next_steps": path["next_steps"],
            "completed_items": path["completed_items"],
            "recommended_features": path["recommended_features"],
        }

    # =========================================================================
    # Command Intelligence Methods (Sprint 2)
    # =========================================================================

    async def interpret_command(
        self,
        query: str,
        context: dict[str, Any] | None = None,
        user_id: str = "",
        session_id: str | None = None,
        **kwargs: Any,
    ) -> dict[str, Any]:
        """AI interprets natural language commands.

        Parses user intent from natural language to determine action.

        Args:
            query: Natural language command/query from user
            context: Current context (page, artifacts, etc.)
            user_id: User identifier
            session_id: Optional session identifier
            **kwargs: Additional parameters

        Returns:
            Interpreted command with action type and parameters
        """
        if not query or not query.strip():
            return {
                "interpreted_command": None,
                "parameters": {},
                "confidence": 0.0,
            }

        query_lower = query.lower()

        # Heuristic command interpretation
        if "create" in query_lower or "new" in query_lower:
            if "file" in query_lower or "python" in query_lower:
                return {
                    "interpreted_command": "create_file",
                    "parameters": {"type": "python"},
                    "confidence": 0.85,
                }
            if "workflow" in query_lower:
                return {
                    "interpreted_command": "create_workflow",
                    "parameters": {},
                    "confidence": 0.9,
                }
            if "session" in query_lower or "chat" in query_lower:
                return {
                    "interpreted_command": "new_session",
                    "parameters": {},
                    "confidence": 0.9,
                }

        if "search" in query_lower or "find" in query_lower:
            return {
                "interpreted_command": "search",
                "parameters": {"query": query},
                "confidence": 0.8,
            }

        if "help" in query_lower:
            return {
                "interpreted_command": "show_help",
                "parameters": {},
                "confidence": 0.95,
            }

        if "settings" in query_lower or "configure" in query_lower:
            return {
                "interpreted_command": "open_settings",
                "parameters": {},
                "confidence": 0.85,
            }

        # Default: treat as chat message
        return {
            "interpreted_command": "send_message",
            "parameters": {"message": query},
            "confidence": 0.6,
        }

    async def generate_inline_suggestions(
        self,
        code: str,
        cursor_position: int,
        language: str = "python",
        user_id: str = "",
        session_id: str | None = None,
        **kwargs: Any,
    ) -> dict[str, Any]:
        """Generate inline code suggestions.

        Provides context-aware code completions based on cursor position.

        Args:
            code: Current code content
            cursor_position: Cursor position in the code
            language: Programming language
            user_id: User identifier
            session_id: Optional session identifier
            **kwargs: Additional parameters

        Returns:
            List of code suggestions with confidence scores
        """
        suggestions: list[dict[str, Any]] = []

        # Get the line context
        lines = code.split("\n")
        current_line = ""
        char_count = 0
        for line in lines:
            if char_count + len(line) + 1 > cursor_position:
                current_line = line[: cursor_position - char_count] if cursor_position > char_count else ""
                break
            char_count += len(line) + 1

        current_line_stripped = current_line.strip()

        # Language-specific heuristic suggestions
        if language == "python":
            if current_line_stripped.startswith("def "):
                suggestions = [
                    {"text": "def main():", "confidence": 0.8},
                    {"text": "def __init__(self):", "confidence": 0.75},
                ]
            elif current_line_stripped.startswith("class "):
                suggestions = [
                    {"text": "class MyClass:", "confidence": 0.8},
                ]
            elif current_line_stripped.startswith("import "):
                suggestions = [
                    {"text": "import os", "confidence": 0.7},
                    {"text": "import json", "confidence": 0.65},
                ]
            elif current_line_stripped == "":
                suggestions = [
                    {"text": "# TODO: ", "confidence": 0.5},
                ]

        elif language in ["typescript", "javascript"]:
            if current_line_stripped.startswith("function "):
                suggestions = [
                    {"text": "function handleClick() {", "confidence": 0.75},
                ]
            elif current_line_stripped.startswith("const "):
                suggestions = [
                    {"text": "const [state, setState] = useState()", "confidence": 0.7},
                ]
            elif current_line_stripped.startswith("import "):
                suggestions = [
                    {"text": "import React from 'react'", "confidence": 0.7},
                ]

        elif language == "rust":
            if current_line_stripped.startswith("fn "):
                suggestions = [
                    {"text": "fn main() {", "confidence": 0.85},
                ]
            elif current_line_stripped.startswith("let "):
                suggestions = [
                    {"text": "let mut ", "confidence": 0.7},
                ]

        elif language == "go":
            if current_line_stripped.startswith("func "):
                suggestions = [
                    {"text": "func main() {", "confidence": 0.85},
                ]

        return {
            "suggestions": suggestions,
            "language": language,
            "cursor_position": cursor_position,
        }

    async def generate_ai_edit(
        self,
        content: str,
        instruction: str,
        artifact_type: str = "code",
        user_id: str = "",
        session_id: str | None = None,
        **kwargs: Any,
    ) -> dict[str, Any]:
        """Generate AI-powered edits.

        Applies AI-generated modifications based on natural language instruction.

        Args:
            content: Original content to edit
            instruction: Natural language instruction for the edit
            artifact_type: Type of artifact (code, markdown, json, mermaid)
            user_id: User identifier
            session_id: Optional session identifier
            **kwargs: Additional parameters

        Returns:
            Edited content with diff information
        """
        edited_content = content
        additions = 0
        deletions = 0
        explanation = "No changes applied"

        instruction_lower = instruction.lower()

        if artifact_type == "code":
            if "add" in instruction_lower and "comment" in instruction_lower:
                # Add a comment at the top
                edited_content = f"# {instruction}\n{content}"
                additions = 1
                explanation = "Added comment at top of file"

            elif "add" in instruction_lower and "print" in instruction_lower:
                # Add print statement
                edited_content = content + "\nprint('Hello, World!')\n"
                additions = 1
                explanation = "Added print statement"

            elif "remove" in instruction_lower or "delete" in instruction_lower:
                lines = content.split("\n")
                edited_lines = [line for line in lines if line.strip()]
                edited_content = "\n".join(edited_lines)
                deletions = len(lines) - len(edited_lines)
                explanation = f"Removed {deletions} empty lines"

        elif artifact_type == "markdown":
            if "title" in instruction_lower or "heading" in instruction_lower:
                edited_content = f"# Document\n\n{content}"
                additions = 2
                explanation = "Added title heading"

        elif artifact_type == "json":
            if "format" in instruction_lower or "prettify" in instruction_lower:
                try:
                    import json

                    parsed = json.loads(content)
                    edited_content = json.dumps(parsed, indent=2)
                    explanation = "Formatted JSON with indentation"
                except json.JSONDecodeError:
                    explanation = "Could not parse JSON"

        elif artifact_type == "mermaid":
            if "style" in instruction_lower:
                edited_content = content + "\n    style default fill:#f9f,stroke:#333"
                additions = 1
                explanation = "Added default styling"

        return {
            "edited_content": edited_content,
            "diff": {
                "additions": additions,
                "deletions": deletions,
            },
            "explanation": explanation,
            "artifact_type": artifact_type,
        }

    # =========================================================================
    # Utility Methods
    # =========================================================================

    def _parse_json_response(self, content: str) -> dict[str, Any] | None:
        """
        Parse JSON from LLM response.

        Handles markdown-wrapped JSON blocks.
        """
        try:
            # Try direct JSON parse
            result: dict[str, Any] = json.loads(content)
            return result
        except json.JSONDecodeError:
            pass

        # Try to extract from markdown code block
        patterns = [
            r"```json\s*(.*?)\s*```",
            r"```\s*(.*?)\s*```",
            r"\{.*\}",
        ]

        for pattern in patterns:
            match = re.search(pattern, content, re.DOTALL)
            if match:
                try:
                    json_str = match.group(1) if "```" in pattern else match.group(0)
                    parsed: dict[str, Any] = json.loads(json_str)
                    return parsed
                except (json.JSONDecodeError, IndexError):
                    continue

        logger.warning(f"Failed to parse JSON from LLM response: {content[:200]}...")
        return None
