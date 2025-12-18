"""
Workflow Suggestions Module

Provides AI-powered workflow suggestions using LangGraph and LiteLLM.
Includes HEART metrics tracking for suggestion quality and adoption.
"""

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


def _init_suggestion_metrics() -> bool:
    """Initialize suggestion metrics lazily."""
    global _metrics_available  # noqa: PLW0603
    global _suggestion_counter  # noqa: PLW0603
    global _suggestion_latency  # noqa: PLW0603
    global _suggestion_confidence  # noqa: PLW0603

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

        _metrics_available = True
        return True

    except ImportError:
        _metrics_available = False
        return False


# Initialize on module load
_init_suggestion_metrics()


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
