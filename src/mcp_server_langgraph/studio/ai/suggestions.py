"""
Workflow Suggestions Module

Provides AI-powered workflow suggestions using LangGraph and LiteLLM.
Includes HEART metrics tracking for suggestion quality and adoption.
"""

import hashlib
import logging
import time
from dataclasses import dataclass, field
from typing import Any

# Lazy-load metrics to handle missing dependency

logger = logging.getLogger(__name__)
_metrics_available: bool | None = None
_suggestion_counter: Any = None
_suggestion_latency: Any = None
_suggestion_confidence: Any = None


_chat_suggestion_counter: Any = None
_chat_suggestion_latency: Any = None
_suggestion_tokens_total: Any = None
_suggestion_cost_total: Any = None
_suggestion_rate_limit_hits: Any = None
_suggestion_personalization: Any = None
_suggestion_cache_operations: Any = None
_suggestion_streaming_requests: Any = None


def _init_suggestion_metrics() -> bool:
    """Initialize suggestion metrics lazily."""
    global _metrics_available  # noqa: PLW0603
    global _suggestion_counter  # noqa: PLW0603
    global _suggestion_latency  # noqa: PLW0603
    global _suggestion_confidence  # noqa: PLW0603
    global _chat_suggestion_counter  # noqa: PLW0603
    global _chat_suggestion_latency  # noqa: PLW0603
    global _suggestion_tokens_total  # noqa: PLW0603
    global _suggestion_cost_total  # noqa: PLW0603
    global _suggestion_rate_limit_hits  # noqa: PLW0603
    global _suggestion_personalization  # noqa: PLW0603
    global _suggestion_cache_operations  # noqa: PLW0603
    global _suggestion_streaming_requests  # noqa: PLW0603

    if _metrics_available is not None:
        return _metrics_available

    try:
        from prometheus_client import Counter, Histogram

        _suggestion_counter = Counter(
            "studio_suggestions_total",
            "Total number of workflow suggestions generated",
            ["suggestion_type", "source"],  # source: llm, heuristic
        )

        _suggestion_latency = Histogram(
            "studio_suggestion_latency_seconds",
            "Latency for generating suggestions",
            ["source"],
            buckets=(0.05, 0.1, 0.25, 0.5, 1.0, 2.5, 5.0, 10.0),
        )

        _suggestion_confidence = Histogram(
            "studio_suggestion_confidence",
            "Confidence scores for suggestions",
            ["suggestion_type"],
            buckets=(0.1, 0.2, 0.3, 0.4, 0.5, 0.6, 0.7, 0.8, 0.9, 1.0),
        )

        # Chat follow-up suggestion metrics
        _chat_suggestion_counter = Counter(
            "studio_chat_suggestions_total",
            "Total number of chat follow-up suggestions generated",
            ["category", "source"],  # source: llm, heuristic
        )

        _chat_suggestion_latency = Histogram(
            "studio_chat_suggestion_latency_seconds",
            "Latency for generating chat follow-up suggestions",
            ["source"],
            buckets=(0.05, 0.1, 0.25, 0.5, 1.0, 2.5, 5.0, 10.0),
        )

        # Token and cost tracking (shared for all suggestion types)
        _suggestion_tokens_total = Counter(
            "studio_suggestion_tokens_total",
            "Total tokens used for LLM suggestions",
            ["model", "token_type", "suggestion_type"],  # token_type: prompt, completion
        )

        _suggestion_cost_total = Counter(
            "studio_suggestion_cost_usd",
            "Estimated cost in USD for LLM suggestions",
            ["model", "suggestion_type"],
        )

        # Rate limiting metrics
        _suggestion_rate_limit_hits = Counter(
            "studio_suggestion_rate_limit_hits_total",
            "Total rate limit hits for suggestions",
            ["key_type"],  # key_type: user, ip, default
        )

        # Personalization metrics
        _suggestion_personalization = Counter(
            "studio_suggestion_personalization_total",
            "Suggestion requests by personalization status",
            ["has_history"],  # has_history: true, false
        )

        # Cache metrics
        _suggestion_cache_operations = Counter(
            "studio_suggestion_cache_operations_total",
            "Suggestion cache operations",
            ["operation"],  # operation: hit, miss, set
        )

        # Streaming metrics
        _suggestion_streaming_requests = Counter(
            "studio_suggestion_streaming_requests_total",
            "Total streaming suggestion requests",
            ["suggestion_type"],
        )

        _metrics_available = True
        return True

    except ImportError:
        _metrics_available = False
        return False


# Initialize on module load
_init_suggestion_metrics()


# =============================================================================
# Cost Estimation
# =============================================================================

# Pricing per 1M tokens (approximate, as of 2025)
# Reference: https://ai.google.dev/pricing, https://openai.com/pricing
MODEL_PRICING: dict[str, dict[str, float]] = {
    # Gemini models (Google)
    "gemini-2.5-flash": {"input": 0.075, "output": 0.30},
    "gemini-2.0-flash": {"input": 0.075, "output": 0.30},
    "gemini-1.5-flash": {"input": 0.075, "output": 0.30},
    "gemini-1.5-pro": {"input": 1.25, "output": 5.00},
    "gemini-pro": {"input": 0.50, "output": 1.50},
    # OpenAI models
    "gpt-4o": {"input": 2.50, "output": 10.00},
    "gpt-4o-mini": {"input": 0.15, "output": 0.60},
    "gpt-4-turbo": {"input": 10.00, "output": 30.00},
    "gpt-3.5-turbo": {"input": 0.50, "output": 1.50},
    # Anthropic models
    "claude-3-opus": {"input": 15.00, "output": 75.00},
    "claude-3-sonnet": {"input": 3.00, "output": 15.00},
    "claude-3-haiku": {"input": 0.25, "output": 1.25},
    "claude-3-5-sonnet": {"input": 3.00, "output": 15.00},
}


def estimate_cost(
    model: str,
    prompt_tokens: int,
    completion_tokens: int,
) -> float:
    """Estimate the cost of an LLM call in USD.

    Args:
        model: The model name (will attempt partial matching)
        prompt_tokens: Number of input tokens
        completion_tokens: Number of output tokens

    Returns:
        Estimated cost in USD
    """
    # Try exact match first
    pricing = MODEL_PRICING.get(model)

    # Try partial match if no exact match
    if not pricing:
        for model_key, model_pricing in MODEL_PRICING.items():
            if model_key in model.lower() or model.lower() in model_key:
                pricing = model_pricing
                break

    # Default to conservative estimate if model not found
    if not pricing:
        pricing = {"input": 1.00, "output": 3.00}  # Conservative default

    # Calculate cost (pricing is per 1M tokens)
    input_cost = (prompt_tokens / 1_000_000) * pricing["input"]
    output_cost = (completion_tokens / 1_000_000) * pricing["output"]

    return input_cost + output_cost


# =============================================================================
# Rate Limiting
# =============================================================================


class SuggestionRateLimiter:
    """Simple sliding window rate limiter for suggestions.

    Tracks requests per IP/user within a time window.

    Example:
        limiter = SuggestionRateLimiter(max_requests=60, window_seconds=60)
        if not limiter.is_allowed("user_123"):
            raise RateLimitExceeded()
    """

    def __init__(self, max_requests: int = 60, window_seconds: int = 60) -> None:
        """Initialize the rate limiter.

        Args:
            max_requests: Maximum requests allowed per window
            window_seconds: Time window in seconds
        """
        self.max_requests = max_requests
        self.window_seconds = window_seconds
        self._requests: dict[str, list[float]] = {}

    def is_allowed(self, key: str = "default") -> bool:
        """Check if a request is allowed.

        Args:
            key: Identifier for rate limiting (e.g., user ID, IP)

        Returns:
            True if request is allowed, False if rate limited
        """
        now = time.monotonic()
        cutoff = now - self.window_seconds

        # Get or create request history for this key
        if key not in self._requests:
            self._requests[key] = []

        # Remove expired requests
        self._requests[key] = [t for t in self._requests[key] if t > cutoff]

        # Check if we're under the limit
        if len(self._requests[key]) < self.max_requests:
            self._requests[key].append(now)
            return True

        return False

    def get_retry_after(self, key: str = "default") -> int:
        """Get the number of seconds until the next request is allowed.

        Args:
            key: Identifier for rate limiting

        Returns:
            Seconds until a request slot opens up
        """
        if key not in self._requests or not self._requests[key]:
            return 0

        now = time.monotonic()
        oldest = min(self._requests[key])
        retry_after = int(self.window_seconds - (now - oldest)) + 1

        return max(0, retry_after)

    def reset(self, key: str | None = None) -> None:
        """Reset the rate limiter.

        Args:
            key: Optional key to reset. If None, resets all.
        """
        if key is None:
            self._requests.clear()
        elif key in self._requests:
            del self._requests[key]

    def stats(self) -> dict[str, Any]:
        """Get rate limiter statistics.

        Returns:
            Dictionary with rate limiter stats
        """
        return {
            "max_requests": self.max_requests,
            "window_seconds": self.window_seconds,
            "tracked_keys": len(self._requests),
        }


# Global rate limiter instance
_suggestion_rate_limiter = SuggestionRateLimiter(max_requests=60, window_seconds=60)


def get_suggestion_rate_limiter() -> SuggestionRateLimiter:
    """Get the global suggestion rate limiter."""
    return _suggestion_rate_limiter


# =============================================================================
# Metrics Tracking Helpers
# =============================================================================


def track_rate_limit_hit(key: str) -> None:
    """Track a rate limit hit.

    Args:
        key: The rate limit key (e.g., "user:alice", "ip:192.168.1.1")
    """
    _init_suggestion_metrics()
    if _suggestion_rate_limit_hits:
        # Extract key type from key (user:xxx -> user, ip:xxx -> ip, default)
        if key.startswith("user:"):
            key_type = "user"
        elif key.startswith("ip:"):
            key_type = "ip"
        else:
            key_type = "default"
        _suggestion_rate_limit_hits.labels(key_type=key_type).inc()


def track_personalization_usage(has_history: bool) -> None:
    """Track personalization usage.

    Args:
        has_history: Whether conversation history was provided
    """
    _init_suggestion_metrics()
    if _suggestion_personalization:
        _suggestion_personalization.labels(has_history=str(has_history).lower()).inc()


def track_cache_operation(operation: str) -> None:
    """Track a cache operation.

    Args:
        operation: One of "hit", "miss", "set"
    """
    _init_suggestion_metrics()
    if _suggestion_cache_operations:
        _suggestion_cache_operations.labels(operation=operation).inc()


def track_streaming_request(suggestion_type: str) -> None:
    """Track a streaming suggestion request.

    Args:
        suggestion_type: Type of suggestion (chat_followup, workflow)
    """
    _init_suggestion_metrics()
    if _suggestion_streaming_requests:
        _suggestion_streaming_requests.labels(suggestion_type=suggestion_type).inc()


# Quality tracking metric (initialized lazily)
_suggestion_quality_interactions: Any = None


def _init_quality_metrics() -> None:
    """Initialize quality tracking metrics."""
    global _suggestion_quality_interactions

    if _suggestion_quality_interactions is not None:
        return

    try:
        from prometheus_client import Counter

        _suggestion_quality_interactions = Counter(
            "studio_suggestion_quality_interactions_total",
            "User interactions with suggestions for quality tracking",
            ["action", "suggestion_type", "category"],
        )
    except ImportError:
        # prometheus_client not available
        pass


def track_suggestion_quality(
    action: str,
    suggestion_type: str,
    category: str | None = None,
) -> None:
    """Track a suggestion quality interaction.

    Args:
        action: The action taken (click, dismiss, view)
        suggestion_type: Type of suggestion (chat_followup, workflow)
        category: Optional category of the suggestion
    """
    _init_quality_metrics()
    if _suggestion_quality_interactions:
        _suggestion_quality_interactions.labels(
            action=action,
            suggestion_type=suggestion_type,
            category=category or "unknown",
        ).inc()


# Feedback counter (lazy initialized)
_suggestion_feedback_counter: Any = None


def _init_feedback_metrics() -> None:
    """Initialize feedback metrics counter (lazy initialization)."""
    global _suggestion_feedback_counter
    if _suggestion_feedback_counter is not None:
        return

    try:
        from prometheus_client import Counter

        _suggestion_feedback_counter = Counter(
            "suggestion_feedback_total",
            "Total suggestion feedback submissions",
            ["feedback", "suggestion_type", "category"],
        )
    except ImportError:
        pass


def track_suggestion_feedback(
    feedback: str,
    suggestion_type: str,
    category: str | None = None,
) -> None:
    """Track suggestion feedback (thumbs up/down).

    Args:
        feedback: The feedback type (positive, negative)
        suggestion_type: Type of suggestion (chat_followup, workflow)
        category: Optional category of the suggestion
    """
    _init_feedback_metrics()
    if _suggestion_feedback_counter:
        _suggestion_feedback_counter.labels(
            feedback=feedback,
            suggestion_type=suggestion_type,
            category=category or "unknown",
        ).inc()


# =============================================================================
# Suggestion Cache
# =============================================================================


class SuggestionCache:
    """Simple TTL-based cache for suggestions.

    Uses a dictionary with expiration timestamps.
    Thread-safe for basic async operations.

    Example:
        cache = SuggestionCache(ttl_seconds=300)
        cache.set("key", suggestions)
        result = cache.get("key")  # Returns suggestions or None if expired
    """

    def __init__(self, ttl_seconds: int = 300, max_size: int = 1000) -> None:
        """Initialize the cache.

        Args:
            ttl_seconds: Time-to-live for cache entries in seconds
            max_size: Maximum number of entries to keep
        """
        self.ttl_seconds = ttl_seconds
        self.max_size = max_size
        self._cache: dict[str, tuple[float, Any]] = {}
        self._access_order: list[str] = []

    def _make_key(self, content: str, max_suggestions: int) -> str:
        """Create a cache key from content and parameters.

        Args:
            content: The content to hash
            max_suggestions: Max suggestions parameter

        Returns:
            Cache key string
        """
        # Use first 2000 chars (same as we send to LLM)
        content_hash = hashlib.sha256(content[:2000].encode()).hexdigest()[:16]
        return f"{content_hash}:{max_suggestions}"

    def get(self, key: str) -> Any | None:
        """Get a value from the cache.

        Args:
            key: Cache key

        Returns:
            Cached value or None if not found/expired
        """
        entry = self._cache.get(key)
        if entry is None:
            track_cache_operation("miss")
            return None

        expiry, value = entry
        if time.monotonic() > expiry:
            # Expired, remove it
            del self._cache[key]
            if key in self._access_order:
                self._access_order.remove(key)
            track_cache_operation("miss")
            return None

        track_cache_operation("hit")
        return value

    def set(self, key: str, value: Any) -> None:
        """Set a value in the cache.

        Args:
            key: Cache key
            value: Value to cache
        """
        # Evict oldest entries if at max size
        while len(self._cache) >= self.max_size and self._access_order:
            oldest_key = self._access_order.pop(0)
            self._cache.pop(oldest_key, None)

        expiry = time.monotonic() + self.ttl_seconds
        self._cache[key] = (expiry, value)

        # Update access order
        if key in self._access_order:
            self._access_order.remove(key)
        self._access_order.append(key)

        track_cache_operation("set")

    def clear(self) -> None:
        """Clear all cached entries."""
        self._cache.clear()
        self._access_order.clear()

    def stats(self) -> dict[str, int]:
        """Get cache statistics.

        Returns:
            Dictionary with cache stats
        """
        return {
            "size": len(self._cache),
            "max_size": self.max_size,
            "ttl_seconds": self.ttl_seconds,
        }


# Global suggestion cache instances
_chat_suggestion_cache = SuggestionCache(ttl_seconds=300, max_size=1000)
_workflow_suggestion_cache = SuggestionCache(ttl_seconds=300, max_size=500)


def get_chat_suggestion_cache() -> SuggestionCache:
    """Get the global chat suggestion cache."""
    return _chat_suggestion_cache


def get_workflow_suggestion_cache() -> SuggestionCache:
    """Get the global workflow suggestion cache."""
    return _workflow_suggestion_cache


# =============================================================================
# Pre-warm Topics
# =============================================================================

# Common programming topics used to pre-warm the suggestion cache at startup.
# These represent typical user queries and help reduce perceived latency.
PREWARM_TOPICS: list[str] = [
    # Python development
    "I can help you with Python programming and best practices.",
    "Let me explain how to use async/await in Python.",
    "Here's how to handle errors in Python with try/except.",
    # JavaScript/TypeScript
    "I can help with JavaScript and TypeScript development.",
    "Let me show you how to use React hooks effectively.",
    # API development
    "Here's how to build a REST API with proper error handling.",
    "I can help you design API endpoints for your application.",
    # Database operations
    "Let me explain database design patterns and SQL optimization.",
    "Here's how to implement database migrations safely.",
    # Error handling
    "I found several issues in your code that need fixing.",
    "Here are the test failures and how to resolve them.",
    # General programming
    "I can explain clean code principles and best practices.",
    "Let me help you understand design patterns.",
]


# Pre-warm metrics counter (lazy initialized)
_prewarm_counter: Any = None


def _init_prewarm_metrics() -> None:
    """Initialize pre-warm metrics counter (lazy initialization)."""
    global _prewarm_counter
    if _prewarm_counter is not None:
        return

    try:
        from prometheus_client import Counter

        _prewarm_counter = Counter(
            "suggestion_prewarm_total",
            "Total pre-warm executions",
            ["status"],
        )
    except ImportError:
        pass


def track_prewarm_execution(status: str = "success") -> None:
    """Track pre-warm execution.

    Args:
        status: Status of the pre-warm (success, error, skipped)
    """
    _init_prewarm_metrics()
    if _prewarm_counter:
        _prewarm_counter.labels(status=status).inc()


async def prewarm_suggestions() -> None:
    """Pre-warm suggestion cache with common topics.

    This function generates suggestions for common topics at startup
    to reduce perceived latency when users request suggestions on
    popular topics.

    The function:
    - Checks the enable_suggestion_prewarm feature flag
    - Generates suggestions for each topic in PREWARM_TOPICS
    - Uses heuristic-based suggestions (fast, no LLM calls)
    - Stores results in the suggestion cache
    - Limits concurrent requests to avoid overwhelming the system

    This should be called during application startup.
    """
    import asyncio
    from mcp_server_langgraph.core.feature_flags import get_feature_flags

    flags = get_feature_flags()

    if not flags.enable_suggestion_prewarm:
        logger.debug("Suggestion pre-warming disabled by feature flag")
        track_prewarm_execution("skipped")
        return

    logger.info("Starting suggestion pre-warm for %d topics", len(PREWARM_TOPICS))

    cache = get_chat_suggestion_cache()

    # Use a semaphore to limit concurrent requests (avoid overwhelming system)
    semaphore = asyncio.Semaphore(3)

    async def prewarm_topic(topic: str) -> None:
        """Pre-warm a single topic with semaphore."""
        async with semaphore:
            try:
                # Use heuristic-based suggestions for speed (no LLM calls)
                agent = ChatFollowUpSuggestionAgent(enable_llm=False)
                suggestions = await agent.suggest(
                    content=topic,
                    max_suggestions=4,
                )

                # Store in cache
                cache_key = cache._make_key(topic, 4)
                cache.set(cache_key, suggestions)

                logger.debug("Pre-warmed suggestions for topic: %s...", topic[:50])

            except Exception as e:
                logger.warning("Failed to pre-warm topic: %s - %s", topic[:30], e)

    try:
        # Run all pre-warm tasks concurrently (with semaphore limiting)
        await asyncio.gather(
            *[prewarm_topic(topic) for topic in PREWARM_TOPICS],
            return_exceptions=True,
        )

        logger.info(
            "Suggestion pre-warm complete. Cache size: %d",
            cache.stats()["size"],
        )
        track_prewarm_execution("success")

    except Exception as e:
        logger.exception("Suggestion pre-warm failed: %s", e)
        track_prewarm_execution("error")


@dataclass
class Suggestion:
    """A workflow suggestion from the AI agent."""

    type: str
    description: str
    confidence: float
    metadata: dict[str, Any] = field(default_factory=dict)

    def __getitem__(self, key: str) -> Any:
        """Allow dict-like access for backward compatibility."""
        mapping = {
            "type": self.type,
            "description": self.description,
            "confidence": self.confidence,
            "metadata": self.metadata,
        }
        if key in mapping:
            return mapping[key]
        raise KeyError(key)

    def get(self, key: str, default: Any = None) -> Any:
        """Get attribute with default."""
        try:
            return self[key]
        except KeyError:
            return default


class WorkflowSuggestionAgent:
    """AI agent that provides workflow suggestions.

    Uses LiteLLM to analyze workflows and suggest improvements,
    additions, or modifications. Falls back to heuristic-based
    suggestions when LLM is unavailable.

    HEART Metrics tracked:
    - Happiness: N/A (would require user feedback)
    - Engagement: suggestion_count per workflow
    - Adoption: N/A (would require tracking if suggestions are applied)
    - Retention: N/A (would require session tracking)
    - Task Success: confidence scores

    Example:
        agent = WorkflowSuggestionAgent()
        suggestions = await agent.suggest(
            workflow={"nodes": [...], "edges": [...]}
        )
    """

    def __init__(
        self,
        model_name: str = "gemini-2.5-flash",
        temperature: float = 0.7,
        enable_llm: bool = True,
    ) -> None:
        """Initialize the workflow suggestion agent.

        Args:
            model_name: The LLM model to use
            temperature: Sampling temperature
            enable_llm: Whether to use LLM (set False for testing)
        """
        self.model_name = model_name
        self.temperature = temperature
        self.enable_llm = enable_llm
        self._llm_factory = None

    async def suggest(
        self,
        workflow: dict[str, Any],
        max_suggestions: int = 5,
        confidence_threshold: float = 0.0,
    ) -> list[Suggestion]:
        """Generate suggestions for the workflow.

        Args:
            workflow: The workflow definition with nodes and edges
            max_suggestions: Maximum number of suggestions to return
            confidence_threshold: Minimum confidence score to include

        Returns:
            List of Suggestion objects
        """
        start_time = time.monotonic()

        # Try LLM first, fallback to heuristics
        if self.enable_llm:
            try:
                response = await self._invoke_llm(workflow)
                source = "llm"
            except Exception:
                # LLM failed, use heuristics
                response = self._generate_heuristic_suggestions(workflow)
                source = "heuristic"
        else:
            response = self._generate_heuristic_suggestions(workflow)
            source = "heuristic"

        # Parse suggestions from response
        raw_suggestions = response.get("suggestions", [])

        # Convert to Suggestion objects and filter
        suggestions = []
        for s in raw_suggestions:
            suggestion = Suggestion(
                type=s.get("type", "unknown"),
                description=s.get("description", ""),
                confidence=s.get("confidence", 0.5),
                metadata=s.get("metadata", {}),
            )
            if suggestion.confidence >= confidence_threshold:
                suggestions.append(suggestion)

        # Sort by confidence descending and limit
        suggestions.sort(key=lambda x: x.confidence, reverse=True)
        suggestions = suggestions[:max_suggestions]

        # Calculate latency
        latency = time.monotonic() - start_time

        # Track metrics
        await self._track_suggestion_event(
            workflow_id=workflow.get("id", "unknown"),
            suggestion_count=len(suggestions),
            suggestions=suggestions,
            source=source,
            latency=latency,
        )

        return suggestions

    async def _invoke_llm(self, workflow: dict[str, Any]) -> dict[str, Any]:
        """Invoke the LLM to generate suggestions.

        Uses LiteLLM for multi-provider support. Falls back to
        heuristics if LLM call fails.

        Args:
            workflow: The workflow to analyze

        Returns:
            Raw response with suggestions
        """
        try:
            from litellm import acompletion

            # Build prompt from workflow
            nodes = workflow.get("nodes", [])
            edges = workflow.get("edges", [])

            prompt = f"""Analyze this workflow and suggest improvements:

Nodes: {nodes}
Edges: {edges}

Provide suggestions in JSON format with fields:
- type: add_node, remove_node, add_edge, optimize, refactor
- description: Clear description of the suggestion
- confidence: Float between 0 and 1

Return a JSON object with a "suggestions" array."""

            response = await acompletion(
                model=self.model_name,
                messages=[
                    {"role": "system", "content": "You are a workflow optimization assistant."},
                    {"role": "user", "content": prompt},
                ],
                temperature=self.temperature,
                max_tokens=1024,
                response_format={"type": "json_object"},
            )

            # Parse LLM response
            import json

            content = response.choices[0].message.content
            result = json.loads(content)

            # Ensure we return a properly typed dict
            if isinstance(result, dict):
                return dict(result)
            return {"suggestions": []}

        except Exception:
            # Fall back to heuristics on any LLM error
            return self._generate_heuristic_suggestions(workflow)

    def _generate_heuristic_suggestions(self, workflow: dict[str, Any]) -> dict[str, Any]:
        """Generate suggestions using heuristic rules.

        This is the fallback when LLM is unavailable.

        Args:
            workflow: The workflow to analyze

        Returns:
            Dict with suggestions array
        """
        nodes = workflow.get("nodes", [])

        if not nodes:
            return {
                "suggestions": [
                    {
                        "type": "add_node",
                        "description": "Add an input node to start your workflow",
                        "confidence": 0.95,
                    }
                ]
            }

        # Analyze workflow structure
        suggestions = []
        node_types = [n.get("type", "") for n in nodes]

        if "input" in node_types and "output" not in node_types:
            suggestions.append(
                {
                    "type": "add_node",
                    "description": "Add an output node to complete the workflow",
                    "confidence": 0.9,
                }
            )

        if "llm" not in node_types:
            suggestions.append(
                {
                    "type": "add_node",
                    "description": "Consider adding an LLM node for AI processing",
                    "confidence": 0.7,
                }
            )

        # Check for disconnected nodes
        edges = workflow.get("edges", [])
        connected_nodes = set()
        for edge in edges:
            connected_nodes.add(edge.get("source"))
            connected_nodes.add(edge.get("target"))

        for node in nodes:
            if node.get("id") not in connected_nodes and len(nodes) > 1:
                suggestions.append(
                    {
                        "type": "add_edge",
                        "description": f"Connect node '{node.get('id')}' to the workflow",
                        "confidence": 0.85,
                    }
                )

        return {"suggestions": suggestions}

    async def _track_suggestion_event(
        self,
        workflow_id: str,
        suggestion_count: int,
        suggestions: list[Suggestion],
        source: str,
        latency: float,
    ) -> None:
        """Track suggestion event for HEART metrics.

        Tracks:
        - Total suggestions by type and source
        - Suggestion latency
        - Confidence score distribution

        Args:
            workflow_id: ID of the workflow
            suggestion_count: Number of suggestions generated
            suggestions: List of suggestions
            source: Source of suggestions (llm or heuristic)
            latency: Time taken to generate suggestions
        """
        if not _metrics_available:
            return

        try:
            # Track suggestion count by type
            if _suggestion_counter:
                for s in suggestions:
                    _suggestion_counter.labels(suggestion_type=s.type, source=source).inc()

            # Track latency
            if _suggestion_latency:
                _suggestion_latency.labels(source=source).observe(latency)

            # Track confidence scores
            if _suggestion_confidence:
                for s in suggestions:
                    _suggestion_confidence.labels(suggestion_type=s.type).observe(s.confidence)

        except Exception as e:
            # Don't let metrics failures break the app
            logger.debug("Metric recording failed: %s", e)


# =============================================================================
# Chat Follow-Up Suggestions
# =============================================================================


@dataclass
class ChatFollowUpSuggestion:
    """A chat follow-up suggestion."""

    id: str
    text: str
    category: str  # explore, clarify, example, alternative, continue

    def __getitem__(self, key: str) -> Any:
        """Allow dict-like access for backward compatibility."""
        mapping = {
            "id": self.id,
            "text": self.text,
            "category": self.category,
        }
        if key in mapping:
            return mapping[key]
        raise KeyError(key)

    def get(self, key: str, default: Any = None) -> Any:
        """Get attribute with default."""
        try:
            return self[key]
        except KeyError:
            return default


class ChatFollowUpSuggestionAgent:
    """AI agent that generates chat follow-up suggestions.

    Uses LiteLLM to analyze the last assistant message and suggest
    follow-up questions the user might want to ask.
    Falls back to heuristic-based suggestions when LLM is unavailable.

    Example:
        agent = ChatFollowUpSuggestionAgent()
        suggestions = await agent.suggest(
            content="Here's how to use async/await in Python..."
        )
    """

    def __init__(
        self,
        model_name: str = "gemini-2.5-flash",
        temperature: float = 0.8,
        enable_llm: bool = True,
        enable_cache: bool = True,
    ) -> None:
        """Initialize the chat follow-up suggestion agent.

        Args:
            model_name: The LLM model to use
            temperature: Sampling temperature (slightly higher for creativity)
            enable_llm: Whether to use LLM (set False for testing)
            enable_cache: Whether to use caching for suggestions
        """
        self.model_name = model_name
        self.temperature = temperature
        self.enable_llm = enable_llm
        self.enable_cache = enable_cache

    async def suggest(
        self,
        content: str,
        max_suggestions: int = 4,
        session_id: str | None = None,
        conversation_history: list[dict[str, str]] | None = None,
    ) -> list[ChatFollowUpSuggestion]:
        """Generate follow-up suggestions for the given content.

        Args:
            content: The assistant message content to analyze
            max_suggestions: Maximum number of suggestions to return
            session_id: Optional session ID for context
            conversation_history: Optional previous conversation for personalization

        Returns:
            List of ChatFollowUpSuggestion objects
        """
        import uuid as uuid_mod

        start_time = time.monotonic()
        prompt_tokens = 0
        completion_tokens = 0

        if not content or not content.strip():
            return []

        # Check cache first (only for LLM mode, skip if personalization is used)
        cache = get_chat_suggestion_cache()
        cache_key = cache._make_key(content, max_suggestions)
        use_cache = self.enable_cache and self.enable_llm and not conversation_history

        if use_cache:
            cached = cache.get(cache_key)
            if cached is not None:
                logger.debug("Cache hit for chat follow-up suggestions")
                return cached

        # Try LLM first, fallback to heuristics
        if self.enable_llm:
            try:
                response, token_info = await self._invoke_llm(content, max_suggestions, conversation_history)
                source = "llm"
                prompt_tokens = token_info.get("prompt_tokens", 0)
                completion_tokens = token_info.get("completion_tokens", 0)
            except Exception:
                # LLM failed, use heuristics
                response = self._generate_heuristic_suggestions(content, max_suggestions)
                source = "heuristic"
        else:
            response = self._generate_heuristic_suggestions(content, max_suggestions)
            source = "heuristic"

        # Parse suggestions from response
        raw_suggestions = response.get("suggestions", [])

        # Convert to ChatFollowUpSuggestion objects
        suggestions = []
        for s in raw_suggestions:
            suggestion = ChatFollowUpSuggestion(
                id=s.get("id", f"sug-{uuid_mod.uuid4().hex[:8]}"),
                text=s.get("text", ""),
                category=s.get("category", "explore"),
            )
            if suggestion.text:  # Only include non-empty suggestions
                suggestions.append(suggestion)

        suggestions = suggestions[:max_suggestions]

        # Calculate latency
        latency = time.monotonic() - start_time

        # Track metrics
        await self._track_suggestion_event(
            session_id=session_id or "unknown",
            suggestion_count=len(suggestions),
            suggestions=suggestions,
            source=source,
            latency=latency,
            prompt_tokens=prompt_tokens,
            completion_tokens=completion_tokens,
        )

        # Log for debugging
        logger.debug(
            "Generated %d chat follow-up suggestions in %.3fs (source=%s, tokens=%d/%d)",
            len(suggestions),
            latency,
            source,
            prompt_tokens,
            completion_tokens,
        )

        # Cache the result (only for LLM-generated suggestions)
        if self.enable_cache and source == "llm" and suggestions:
            cache.set(cache_key, suggestions)

        return suggestions

    async def _invoke_llm(
        self,
        content: str,
        max_suggestions: int,
        conversation_history: list[dict[str, str]] | None = None,
    ) -> tuple[dict[str, Any], dict[str, int]]:
        """Invoke the LLM to generate follow-up suggestions.

        Args:
            content: The assistant message content
            max_suggestions: Maximum suggestions to generate
            conversation_history: Optional previous conversation for personalization

        Returns:
            Tuple of (raw response with suggestions, token usage info)
        """
        from litellm import acompletion

        # Build conversation context section if history is provided
        context_section = ""
        if conversation_history:
            history_text = "\n".join(
                f"{msg['role'].capitalize()}: {msg['content'][:500]}"
                for msg in conversation_history[-5:]  # Last 5 messages
            )
            context_section = f"""
Previous conversation context:
{history_text}

"""

        prompt = f"""Based on this AI assistant response, suggest {max_suggestions} follow-up questions the user might want to ask.
{context_section}
Assistant response:
{content[:2000]}

Generate follow-up suggestions that help the user:
1. Explore the topic deeper
2. Get clarification on complex points
3. Request practical examples
4. Understand alternatives or trade-offs
5. Know what to do next

Return a JSON object with a "suggestions" array. Each suggestion should have:
- id: unique identifier (e.g., "sug-1")
- text: the follow-up question (natural, conversational)
- category: one of "explore", "clarify", "example", "alternative", "continue"

Make suggestions specific to the content and conversation context, not generic."""

        response = await acompletion(
            model=self.model_name,
            messages=[
                {
                    "role": "system",
                    "content": "You are a helpful assistant that suggests relevant follow-up questions based on AI responses. Generate concise, specific questions.",
                },
                {"role": "user", "content": prompt},
            ],
            temperature=self.temperature,
            max_tokens=512,
            response_format={"type": "json_object"},
        )

        # Extract token usage from response
        token_info = {
            "prompt_tokens": getattr(response.usage, "prompt_tokens", 0) if response.usage else 0,
            "completion_tokens": getattr(response.usage, "completion_tokens", 0) if response.usage else 0,
        }

        # Parse LLM response
        import json

        response_content = response.choices[0].message.content
        result = json.loads(response_content)

        if isinstance(result, dict):
            return dict(result), token_info
        return {"suggestions": []}, token_info

    def _generate_heuristic_suggestions(self, content: str, max_suggestions: int) -> dict[str, Any]:
        """Generate suggestions using heuristic rules.

        This is the fallback when LLM is unavailable.

        Args:
            content: The assistant message content
            max_suggestions: Maximum suggestions to generate

        Returns:
            Dict with suggestions array
        """
        import uuid as uuid_mod

        suggestions = []
        content_lower = content.lower()

        # Heuristic: If content mentions code/programming, suggest examples
        if any(kw in content_lower for kw in ["code", "function", "class", "programming", "python", "javascript"]):
            suggestions.append(
                {
                    "id": f"sug-{uuid_mod.uuid4().hex[:8]}",
                    "text": "Can you show me a working example?",
                    "category": "example",
                }
            )

        # Heuristic: If content is explanatory, suggest deeper exploration
        if any(kw in content_lower for kw in ["because", "reason", "due to", "therefore", "this means"]):
            suggestions.append(
                {
                    "id": f"sug-{uuid_mod.uuid4().hex[:8]}",
                    "text": "Tell me more about the underlying concepts",
                    "category": "explore",
                }
            )

        # Heuristic: If content mentions alternatives/options
        if any(kw in content_lower for kw in ["alternative", "option", "another way", "instead", "or you could"]):
            suggestions.append(
                {
                    "id": f"sug-{uuid_mod.uuid4().hex[:8]}",
                    "text": "What are the trade-offs between these approaches?",
                    "category": "alternative",
                }
            )

        # Heuristic: If content seems complex, offer clarification
        if len(content) > 500 or any(kw in content_lower for kw in ["complex", "advanced", "technical"]):
            suggestions.append(
                {
                    "id": f"sug-{uuid_mod.uuid4().hex[:8]}",
                    "text": "Can you explain this in simpler terms?",
                    "category": "clarify",
                }
            )

        # Always add a generic continue suggestion if we have room
        if len(suggestions) < max_suggestions:
            suggestions.append(
                {
                    "id": f"sug-{uuid_mod.uuid4().hex[:8]}",
                    "text": "What should I do next?",
                    "category": "continue",
                }
            )

        return {"suggestions": suggestions[:max_suggestions]}

    async def _track_suggestion_event(
        self,
        session_id: str,
        suggestion_count: int,
        suggestions: list[ChatFollowUpSuggestion],
        source: str,
        latency: float,
        prompt_tokens: int = 0,
        completion_tokens: int = 0,
    ) -> None:
        """Track suggestion event for metrics and cost tracking.

        Tracks:
        - Total suggestions by category and source
        - Suggestion latency
        - Token usage
        - Estimated cost

        Args:
            session_id: ID of the session
            suggestion_count: Number of suggestions generated
            suggestions: List of suggestions
            source: Source of suggestions (llm or heuristic)
            latency: Time taken to generate suggestions
            prompt_tokens: Number of prompt tokens used (LLM only)
            completion_tokens: Number of completion tokens used (LLM only)
        """
        if not _metrics_available:
            return

        try:
            # Track suggestion count by category
            if _chat_suggestion_counter:
                for s in suggestions:
                    _chat_suggestion_counter.labels(category=s.category, source=source).inc()

            # Track latency
            if _chat_suggestion_latency:
                _chat_suggestion_latency.labels(source=source).observe(latency)

            # Track token usage and cost (only for LLM)
            if source == "llm" and (prompt_tokens > 0 or completion_tokens > 0):
                if _suggestion_tokens_total:
                    _suggestion_tokens_total.labels(
                        model=self.model_name,
                        token_type="prompt",  # noqa: S106 - metric label, not password
                        suggestion_type="chat_followup",
                    ).inc(prompt_tokens)
                    _suggestion_tokens_total.labels(
                        model=self.model_name,
                        token_type="completion",  # noqa: S106 - metric label, not password
                        suggestion_type="chat_followup",
                    ).inc(completion_tokens)

                # Track estimated cost
                if _suggestion_cost_total:
                    cost = estimate_cost(
                        model=self.model_name,
                        prompt_tokens=prompt_tokens,
                        completion_tokens=completion_tokens,
                    )
                    _suggestion_cost_total.labels(
                        model=self.model_name,
                        suggestion_type="chat_followup",
                    ).inc(cost)

        except Exception as e:
            # Don't let metrics failures break the app
            logger.debug("Metric recording failed: %s", e)
