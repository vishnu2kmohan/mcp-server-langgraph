"""
Explanation Orchestrator (AI-Native HITL Enhancements)

Orchestrates AI explanation generation using parallel execution for HITL dialogs.

Migrates static templated explanations to AI-generated ones using the
orchestrator-worker pattern for improved performance:

Before:
  static template
    → "Confidence X% below threshold Y%"
    → No context-specific reasoning

After:
  ExplanationOrchestrator
    → UncertaintyAgent [parallel] - WHY uncertain
    → RiskAgent [parallel] - What could go wrong
    → AlternativesAgent [parallel] - Safer options
    → EvidenceAgent [parallel] - Extract reasoning trace
    → Synthesizer [aggregates into AIExplanation]

Usage:
    from mcp_server_langgraph.agents.explanation_orchestrator import (
        ExplanationOrchestrator,
        ExplanationTask,
        ExplanationResult,
        CachedExplanationOrchestrator,
        generate_explanation_cache_key,
    )

    # Standard (no cache)
    orchestrator = ExplanationOrchestrator(llm_factory=llm)
    explanation = await orchestrator.generate_explanation(...)

    # With caching
    cached_orchestrator = CachedExplanationOrchestrator(llm_factory=llm, cache=redis)
    explanation = await cached_orchestrator.generate_explanation_cached(...)
"""

from __future__ import annotations

import hashlib
import logging
import time
from dataclasses import dataclass, field
from typing import TYPE_CHECKING, Any, Protocol

from mcp_server_langgraph.agents.base_orchestrator import (
    BaseOrchestrator,
    BaseResult,
    BaseTask,
)
from mcp_server_langgraph.agents.metrics import record_explanation_generation
from mcp_server_langgraph.core.interrupts.ai_explanation import (
    AIExplanation,
    AlternativeSuggestion,
    ConfidenceFactor,
)

if TYPE_CHECKING:
    from mcp_server_langgraph.agents.cost_tracker import CostTracker

logger = logging.getLogger(__name__)

# Supported analysis types for explanation orchestration
EXPLANATION_ANALYSIS_TYPES = frozenset(
    {
        "uncertainty_analysis",
        "risk_analysis",
        "alternatives_analysis",
        "evidence_extraction",
    }
)


@dataclass
class ExplanationTask(BaseTask):
    """Task definition for explanation analysis.

    Extends BaseTask with approval context for explanation generation.

    Attributes:
        task_type: Type of analysis (uncertainty, risk, alternatives, evidence)
        approval_id: ID of the approval request being explained
        context: Approval context (confidence, threshold, trigger_reason, etc.)
        reasoning_trace: Optional reasoning trace from agent execution
    """

    approval_id: str = ""
    context: dict[str, Any] = field(default_factory=dict)
    reasoning_trace: list[str] = field(default_factory=list)


@dataclass
class ExplanationResult(BaseResult):
    """Result from an explanation analysis task.

    Extends BaseResult for explanation analysis results. Inherits all base fields.

    Attributes:
        task_type: Type of analysis performed
        success: Whether the analysis succeeded
        result: Analysis result data (if successful)
        error: Error message (if failed)
    """

    pass


class ExplanationOrchestrator(BaseOrchestrator[ExplanationTask, ExplanationResult]):
    """Orchestrates parallel explanation generation tasks.

    Coordinates uncertainty, risk, alternatives, and evidence analysis
    tasks in parallel, then synthesizes results into AIExplanation.

    Inherits from BaseOrchestrator to use common parallel execution patterns.
    """

    def __init__(
        self,
        llm_factory: Any | None = None,
        artifact_storage: Any | None = None,
        enable_metrics: bool = True,
        cost_tracker: CostTracker | None = None,
        session_id: str | None = None,
    ) -> None:
        """Initialize Explanation Orchestrator.

        Args:
            llm_factory: LLM factory for generating explanations
            artifact_storage: Optional ArtifactStorage for intermediate results
            enable_metrics: Whether to record metrics (default: True)
            cost_tracker: Optional CostTracker for cost/budget management
            session_id: Optional session ID for cost tracking scope
        """
        super().__init__(
            enable_metrics=enable_metrics,
            cost_tracker=cost_tracker,
            session_id=session_id,
        )
        self._llm_factory = llm_factory
        self._artifact_storage = artifact_storage

    @property
    def llm_factory(self) -> Any | None:
        """Get the LLM factory instance."""
        return self._llm_factory

    @property
    def artifact_storage(self) -> Any | None:
        """Get the artifact storage instance."""
        return self._artifact_storage

    @property
    def feature_flag_name(self) -> str:
        """Return the feature flag name for this orchestrator."""
        return "enable_ai_explanations"

    def _create_failed_result(self, task: ExplanationTask, error: str) -> ExplanationResult:
        """Create a failed result for a task.

        Args:
            task: The task that failed
            error: Error message

        Returns:
            Failed ExplanationResult
        """
        return ExplanationResult(
            task_type=task.task_type,
            success=False,
            error=error,
        )

    async def _execute_task(self, task: ExplanationTask) -> ExplanationResult:
        """Execute a single explanation analysis task.

        Args:
            task: The task to execute

        Returns:
            ExplanationResult from the task
        """
        if self._llm_factory is None:
            return ExplanationResult(
                task_type=task.task_type,
                success=False,
                error="LLM factory not configured",
            )

        try:
            if task.task_type == "uncertainty_analysis":
                result = await self._analyze_uncertainty(task)
            elif task.task_type == "risk_analysis":
                result = await self._analyze_risk(task)
            elif task.task_type == "alternatives_analysis":
                result = await self._analyze_alternatives(task)
            elif task.task_type == "evidence_extraction":
                result = await self._extract_evidence(task)
            else:
                return ExplanationResult(
                    task_type=task.task_type,
                    success=False,
                    error=f"Unknown task type: {task.task_type}",
                )

            return ExplanationResult(
                task_type=task.task_type,
                success=True,
                result=result,
            )

        except Exception as e:
            logger.exception(f"Error executing {task.task_type}: {e}")
            return ExplanationResult(
                task_type=task.task_type,
                success=False,
                error=str(e),
            )

    async def _analyze_uncertainty(self, task: ExplanationTask) -> dict[str, Any]:
        """Analyze WHY the agent is uncertain (LLM-powered).

        Args:
            task: Task with context for uncertainty analysis

        Returns:
            Dict with why_uncertain field
        """
        context = task.context
        prompt = self._build_uncertainty_prompt(context)

        response = await self._llm_factory.ainvoke([{"role": "user", "content": prompt}])

        # Extract content from response
        content = self._extract_content(response)

        return {"why_uncertain": content}

    async def _analyze_risk(self, task: ExplanationTask) -> dict[str, Any]:
        """Analyze what could go wrong (LLM-powered).

        Args:
            task: Task with context for risk analysis

        Returns:
            Dict with what_could_go_wrong field
        """
        context = task.context
        prompt = self._build_risk_prompt(context)

        response = await self._llm_factory.ainvoke([{"role": "user", "content": prompt}])

        content = self._extract_content(response)

        return {"what_could_go_wrong": content}

    async def _analyze_alternatives(self, task: ExplanationTask) -> dict[str, Any]:
        """Generate safer alternatives (LLM-powered).

        Args:
            task: Task with context for alternatives analysis

        Returns:
            Dict with safer_alternatives list
        """
        context = task.context
        prompt = self._build_alternatives_prompt(context)

        response = await self._llm_factory.ainvoke([{"role": "user", "content": prompt}])

        content = self._extract_content(response)

        # Parse alternatives from response
        alternatives = self._parse_alternatives(content, context)

        return {"safer_alternatives": alternatives}

    async def _extract_evidence(self, task: ExplanationTask) -> dict[str, Any]:
        """Extract confidence factors from reasoning trace (rule-based + LLM).

        Args:
            task: Task with reasoning trace for evidence extraction

        Returns:
            Dict with confidence_factors and reasoning_trace
        """
        factors: list[dict[str, Any]] = []
        trace = task.reasoning_trace or []

        # Rule-based extraction of common patterns
        for step in trace:
            step_lower = step.lower()
            if "ambiguous" in step_lower:
                factors.append(
                    {
                        "factor": "ambiguous_input",
                        "weight": -0.2,
                        "evidence": step,
                    }
                )
            if "multiple" in step_lower and "option" in step_lower:
                factors.append(
                    {
                        "factor": "multiple_interpretations",
                        "weight": -0.15,
                        "evidence": step,
                    }
                )
            if "unclear" in step_lower or "uncertain" in step_lower:
                factors.append(
                    {
                        "factor": "unclear_intent",
                        "weight": -0.1,
                        "evidence": step,
                    }
                )
            if "confident" in step_lower or "certain" in step_lower:
                factors.append(
                    {
                        "factor": "confidence_indicator",
                        "weight": 0.1,
                        "evidence": step,
                    }
                )

        return {
            "confidence_factors": factors,
            "reasoning_trace": trace,
        }

    def _build_uncertainty_prompt(self, context: dict[str, Any]) -> str:
        """Build prompt for uncertainty analysis.

        Args:
            context: Approval context

        Returns:
            Formatted prompt string
        """
        agent_name = context.get("agent_name", "Unknown Agent")
        proposed_action = context.get("proposed_action", "Unknown action")
        confidence = context.get("confidence", 0.0)
        threshold = context.get("threshold", 0.7)
        trigger_reason = context.get("trigger_reason", "unknown")

        return f"""Explain why an AI agent is uncertain about its proposed action.

Agent: {agent_name}
Proposed Action: {proposed_action}
Confidence: {confidence:.0%}
Threshold: {threshold:.0%}
Trigger Reason: {trigger_reason}

In 2-3 sentences, explain WHY the agent is uncertain. Be specific about:
1. What information is ambiguous or missing
2. Why the confidence is below the threshold

Respond with just the explanation, no prefix."""

    def _build_risk_prompt(self, context: dict[str, Any]) -> str:
        """Build prompt for risk analysis.

        Args:
            context: Approval context

        Returns:
            Formatted prompt string
        """
        proposed_action = context.get("proposed_action", "Unknown action")
        trigger_reason = context.get("trigger_reason", "unknown")

        return f"""Analyze what could go wrong if the following action proceeds incorrectly.

Proposed Action: {proposed_action}
Trigger Reason: {trigger_reason}

In 2-3 sentences, explain what could go wrong. Be specific about:
1. Potential negative outcomes
2. What the user should verify before approving

Respond with just the explanation, no prefix."""

    def _build_alternatives_prompt(self, context: dict[str, Any]) -> str:
        """Build prompt for alternatives analysis.

        Args:
            context: Approval context

        Returns:
            Formatted prompt string
        """
        proposed_action = context.get("proposed_action", "Unknown action")
        confidence = context.get("confidence", 0.0)

        return f"""Suggest 1-2 safer alternatives to the following action.

Proposed Action: {proposed_action}
Current Confidence: {confidence:.0%}

For each alternative, provide:
1. The alternative action
2. Expected confidence (as percentage)
3. Trade-off or limitation

Format each as: "Action | Confidence% | Trade-off"
Example: "Preview files first | 95% | Adds one extra step"

Respond with just the alternatives, one per line."""

    def _extract_content(self, response: Any) -> str:
        """Extract content from LLM response.

        Args:
            response: LLM response object

        Returns:
            Extracted content string
        """
        if hasattr(response, "content"):
            return response.content
        if isinstance(response, dict) and "content" in response:
            return response["content"]
        if isinstance(response, str):
            return response
        return str(response)

    def _parse_alternatives(self, content: str, context: dict[str, Any]) -> list[dict[str, Any]]:
        """Parse alternatives from LLM response.

        Args:
            content: LLM response content
            context: Approval context

        Returns:
            List of alternative suggestion dicts
        """
        alternatives: list[dict[str, Any]] = []
        lines = content.strip().split("\n")

        for line in lines:
            line = line.strip()
            if not line:
                continue

            # Try to parse "Action | Confidence% | Trade-off" format
            parts = [p.strip() for p in line.split("|")]
            if len(parts) >= 3:
                action = parts[0]
                confidence_str = parts[1].replace("%", "").strip()
                trade_off = parts[2]

                try:
                    confidence = float(confidence_str) / 100.0
                except ValueError:
                    confidence = 0.85

                alternatives.append(
                    {
                        "action": action,
                        "confidence": min(max(confidence, 0.0), 1.0),
                        "trade_off": trade_off,
                    }
                )
            elif len(parts) == 1 and len(line) > 10:
                # Single action without structured format
                alternatives.append(
                    {
                        "action": line,
                        "confidence": 0.85,
                        "trade_off": "Alternative approach",
                    }
                )

        # Limit to 3 alternatives
        return alternatives[:3]

    def synthesize(self, results: list[ExplanationResult]) -> dict[str, Any]:
        """Synthesize AIExplanation from parallel analysis results.

        Combines results from uncertainty, risk, alternatives, and evidence
        analyses into a unified explanation structure.

        Args:
            results: List of ExplanationResult to synthesize

        Returns:
            Dict containing explanation data and analysis status
        """
        explanation_data: dict[str, Any] = {
            "why_uncertain": "",
            "what_could_go_wrong": "",
            "safer_alternatives": [],
            "confidence_factors": [],
            "reasoning_trace": [],
        }

        for result in results:
            if not result.success:
                continue

            result_data = result.result or {}

            if result.task_type == "uncertainty_analysis":
                explanation_data["why_uncertain"] = result_data.get("why_uncertain", "")
            elif result.task_type == "risk_analysis":
                explanation_data["what_could_go_wrong"] = result_data.get("what_could_go_wrong", "")
            elif result.task_type == "alternatives_analysis":
                explanation_data["safer_alternatives"] = result_data.get("safer_alternatives", [])
            elif result.task_type == "evidence_extraction":
                explanation_data["confidence_factors"] = result_data.get("confidence_factors", [])
                explanation_data["reasoning_trace"] = result_data.get("reasoning_trace", [])

        return {
            "explanation": explanation_data,
            "successful_analyses": [r.task_type for r in results if r.success],
            "failed_analyses": [r.task_type for r in results if not r.success],
        }

    async def generate_explanation(
        self,
        approval_id: str,
        agent_name: str,
        proposed_action: str,
        confidence: float,
        threshold: float,
        trigger_reason: str,
        reasoning_trace: list[str] | None = None,
        include_alternatives: bool = True,
    ) -> AIExplanation:
        """Generate AI explanation for an approval request.

        Main entry point for orchestrated explanation generation.
        Runs analyses in parallel and synthesizes results into AIExplanation.

        Args:
            approval_id: ID of the approval request
            agent_name: Name of the agent requesting approval
            proposed_action: Action the agent wants to take
            confidence: Agent's confidence score (0-1)
            threshold: User's approval threshold (0-1)
            trigger_reason: Why HITL was triggered
            reasoning_trace: Optional agent reasoning steps
            include_alternatives: Include alternatives analysis (default: True)

        Returns:
            AIExplanation with all analysis results synthesized
        """
        import time

        start_time = time.monotonic()

        context = {
            "agent_name": agent_name,
            "proposed_action": proposed_action,
            "confidence": confidence,
            "threshold": threshold,
            "trigger_reason": trigger_reason,
        }

        tasks: list[ExplanationTask] = [
            ExplanationTask(
                task_type="uncertainty_analysis",
                approval_id=approval_id,
                context=context,
            ),
            ExplanationTask(
                task_type="risk_analysis",
                approval_id=approval_id,
                context=context,
            ),
            ExplanationTask(
                task_type="evidence_extraction",
                approval_id=approval_id,
                context=context,
                reasoning_trace=reasoning_trace or [],
            ),
        ]

        if include_alternatives:
            tasks.append(
                ExplanationTask(
                    task_type="alternatives_analysis",
                    approval_id=approval_id,
                    context=context,
                )
            )

        # Execute tasks in parallel
        results = await self.execute(tasks)

        # Synthesize into AIExplanation structure
        synthesis = self.synthesize(results)

        # Calculate latency
        latency_ms = (time.monotonic() - start_time) * 1000

        # Build AIExplanation model
        explanation_data = synthesis["explanation"]

        return AIExplanation(
            why_uncertain=explanation_data.get("why_uncertain", ""),
            what_could_go_wrong=explanation_data.get("what_could_go_wrong", ""),
            safer_alternatives=[AlternativeSuggestion(**alt) for alt in explanation_data.get("safer_alternatives", [])],
            confidence_factors=[ConfidenceFactor(**factor) for factor in explanation_data.get("confidence_factors", [])],
            reasoning_trace=explanation_data.get("reasoning_trace", []),
            generation_latency_ms=latency_ms,
        )


# =============================================================================
# Caching Support (Plan Section 10.2)
# =============================================================================

# Cache TTL for explanation results (1 hour default)
EXPLANATION_CACHE_TTL = 3600


class CacheProtocol(Protocol):
    """Protocol for cache implementations."""

    async def get(self, key: str) -> str | None:
        """Get value from cache."""
        ...

    async def set(self, key: str, value: str, ttl: int | None = None) -> None:
        """Set value in cache with optional TTL."""
        ...

    async def delete(self, key: str) -> bool:
        """Delete key from cache."""
        ...


def generate_explanation_cache_key(
    agent_name: str,
    proposed_action: str,
    confidence: float,
    trigger_reason: str,
) -> str:
    """Generate a deterministic cache key for explanation.

    Uses bucketed confidence (0.05 increments) to increase cache hits
    for similar confidence values.

    Args:
        agent_name: Name of the agent
        proposed_action: Proposed action description
        confidence: Confidence score (0-1), will be bucketed
        trigger_reason: Reason HITL was triggered

    Returns:
        Cache key string
    """
    # Bucket confidence to nearest 0.05 for better cache hit rate
    bucketed_confidence = round(confidence * 20) / 20

    # Build deterministic key components
    key_parts = [
        agent_name.lower().strip(),
        proposed_action.lower().strip(),
        f"{bucketed_confidence:.2f}",
        trigger_reason.lower().strip(),
    ]

    # Create hash of components
    key_string = "|".join(key_parts)
    key_hash = hashlib.sha256(key_string.encode()).hexdigest()[:16]

    return f"explanation:{key_hash}"


class CachedExplanationOrchestrator(ExplanationOrchestrator):
    """Explanation orchestrator with caching support.

    Wraps ExplanationOrchestrator with a caching layer to reduce
    LLM costs for similar approval contexts.

    Attributes:
        cache: Cache implementation (Redis recommended)
        cache_ttl: TTL in seconds for cached explanations
    """

    def __init__(
        self,
        llm_factory: Any | None = None,
        cache: CacheProtocol | None = None,
        cache_ttl: int = EXPLANATION_CACHE_TTL,
        artifact_storage: Any | None = None,
        enable_metrics: bool = True,
        cost_tracker: Any | None = None,
        session_id: str | None = None,
    ) -> None:
        """Initialize cached orchestrator.

        Args:
            llm_factory: LLM factory for generating explanations
            cache: Cache implementation (Redis, in-memory, etc.)
            cache_ttl: TTL for cached entries in seconds
            artifact_storage: Optional artifact storage
            enable_metrics: Whether to record metrics
            cost_tracker: Optional cost tracker
            session_id: Optional session ID
        """
        super().__init__(
            llm_factory=llm_factory,
            artifact_storage=artifact_storage,
            enable_metrics=enable_metrics,
            cost_tracker=cost_tracker,
            session_id=session_id,
        )
        self._cache = cache
        self._cache_ttl = cache_ttl

    @property
    def cache(self) -> CacheProtocol | None:
        """Get the cache implementation."""
        return self._cache

    async def generate_explanation_cached(
        self,
        approval_id: str,
        agent_name: str,
        proposed_action: str,
        confidence: float,
        threshold: float,
        trigger_reason: str,
        reasoning_trace: list[str] | None = None,
        include_alternatives: bool = True,
    ) -> AIExplanation:
        """Generate explanation with caching.

        Checks cache first, generates if not found, and stores result.

        Args:
            approval_id: ID of the approval request
            agent_name: Name of the agent
            proposed_action: Action the agent wants to take
            confidence: Confidence score (0-1)
            threshold: Approval threshold (0-1)
            trigger_reason: Why HITL was triggered
            reasoning_trace: Optional reasoning steps
            include_alternatives: Include alternatives analysis

        Returns:
            AIExplanation (from cache or freshly generated)
        """
        start_time = time.monotonic()
        cached = False

        # Generate cache key
        cache_key = generate_explanation_cache_key(
            agent_name=agent_name,
            proposed_action=proposed_action,
            confidence=confidence,
            trigger_reason=trigger_reason,
        )

        # Try cache first
        if self._cache is not None:
            try:
                cached_value = await self._cache.get(cache_key)
                if cached_value is not None:
                    # Cache hit
                    explanation = AIExplanation.model_validate_json(cached_value)
                    explanation.cached = True
                    cached = True

                    duration_ms = (time.monotonic() - start_time) * 1000
                    record_explanation_generation(
                        approval_id=approval_id,
                        duration_ms=duration_ms,
                        success=True,
                        cached=True,
                    )

                    logger.debug(f"Cache hit for explanation: {cache_key}")
                    return explanation
            except Exception as e:
                logger.warning(f"Cache get failed, generating fresh: {e}")

        # Cache miss - generate explanation
        try:
            explanation = await self.generate_explanation(
                approval_id=approval_id,
                agent_name=agent_name,
                proposed_action=proposed_action,
                confidence=confidence,
                threshold=threshold,
                trigger_reason=trigger_reason,
                reasoning_trace=reasoning_trace,
                include_alternatives=include_alternatives,
            )

            # Store in cache
            if self._cache is not None:
                try:
                    await self._cache.set(
                        cache_key,
                        explanation.model_dump_json(),
                        ttl=self._cache_ttl,
                    )
                    logger.debug(f"Cached explanation: {cache_key}")
                except Exception as e:
                    logger.warning(f"Cache set failed: {e}")

            duration_ms = (time.monotonic() - start_time) * 1000
            record_explanation_generation(
                approval_id=approval_id,
                duration_ms=duration_ms,
                success=True,
                cached=False,
            )

            return explanation

        except Exception as e:
            duration_ms = (time.monotonic() - start_time) * 1000
            record_explanation_generation(
                approval_id=approval_id,
                duration_ms=duration_ms,
                success=False,
                cached=False,
                error_type=type(e).__name__,
            )
            raise

    async def invalidate_explanation_cache(
        self,
        agent_name: str,
        proposed_action: str,
        confidence: float,
        trigger_reason: str,
    ) -> bool:
        """Invalidate cached explanation.

        Args:
            agent_name: Name of the agent
            proposed_action: Action description
            confidence: Confidence score
            trigger_reason: Trigger reason

        Returns:
            True if deleted, False otherwise
        """
        if self._cache is None:
            return False

        cache_key = generate_explanation_cache_key(
            agent_name=agent_name,
            proposed_action=proposed_action,
            confidence=confidence,
            trigger_reason=trigger_reason,
        )

        try:
            return await self._cache.delete(cache_key)
        except Exception as e:
            logger.warning(f"Cache delete failed: {e}")
            return False
