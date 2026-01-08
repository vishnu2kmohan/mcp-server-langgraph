"""
AI UX LangGraph StateGraph Implementation

Provides a LangGraph-based state machine for AI UX analysis workflows.

The StateGraph provides:
1. Unified state management for UX analysis workflows
2. Declarative node-based analysis pipeline
3. Conditional routing based on analysis requirements
4. Built-in observability via LangGraph tracing
5. Support for parallel node execution

Reference: UX Audit Plan - LangGraph Integration
"""

from __future__ import annotations

import json
from collections.abc import Awaitable, Callable
from typing import TYPE_CHECKING, Any, TypedDict, cast

from langgraph.graph import END, StateGraph
from langgraph.types import Send

from opentelemetry import trace

if TYPE_CHECKING:
    # StateNode is exported at runtime but not in LangGraph's type stubs
    from langgraph.graph.state import StateNode  # type: ignore[attr-defined]

from mcp_server_langgraph.core.numeric import safe_average
from mcp_server_langgraph.observability.telemetry import logger

# OpenTelemetry tracer for graph node instrumentation
tracer = trace.get_tracer(__name__)


def get_tracer() -> trace.Tracer:
    """Get the OpenTelemetry tracer for this module."""
    return tracer


if TYPE_CHECKING:
    from unittest.mock import MagicMock


# =============================================================================
# State Schema
# =============================================================================


class UXAnalysisState(TypedDict):
    """State schema for UX analysis workflow.

    Contains all fields needed for the analysis pipeline:
    - Request context (user_id, session_id)
    - Feature flags (include_persona, include_disclosure, include_error)
    - Input data (persona_data, disclosure_data, error_data)
    - Analysis results (persona_result, disclosure_result, error_result)
    - Cross-service outputs (cross_insights, confidence)
    """

    # Request context
    user_id: str
    session_id: str

    # Feature flags for which analyses to run
    include_persona: bool
    include_disclosure: bool
    include_error: bool

    # Input data for analyses
    persona_data: dict[str, Any] | None
    disclosure_data: dict[str, Any] | None
    error_data: dict[str, Any] | None

    # Analysis results
    persona_result: dict[str, Any] | None
    disclosure_result: dict[str, Any] | None
    error_result: dict[str, Any] | None

    # Cross-service outputs
    cross_insights: list[str]
    confidence: float


# Type alias for analysis node functions
AnalysisNode = Callable[[UXAnalysisState], Awaitable[dict[str, Any]]]


# =============================================================================
# Analysis Nodes
# =============================================================================


def create_persona_analysis_node(llm_factory: Any, settings: Any) -> AnalysisNode:
    """Create a node that performs persona analysis."""

    async def persona_analysis(state: UXAnalysisState) -> dict[str, Any]:
        """Analyze persona from state data."""
        with tracer.start_as_current_span("persona_analysis") as span:
            span.set_attributes({"user_id": state.get("user_id", "unknown")})

            persona_data = state.get("persona_data")
            if not state.get("include_persona") or persona_data is None:
                span.set_attribute("skipped", True)
                return {"persona_result": None}

            try:
                # Build prompt for persona analysis (persona_data verified non-None above)
                prompt = f"""Analyze user persona based on behavior:
User ID: {state["user_id"]}
Assigned Persona: {persona_data.get("assigned_persona", "unknown")}
Recent Actions: {persona_data.get("recent_actions", [])}
Feature Usage: {persona_data.get("feature_usage", {})}

Return JSON with: detected_persona, confidence, behavior_signals, recommendation, ui_adaptations"""

                # Call LLM
                response = await llm_factory.ainvoke(prompt)
                content = response.content if hasattr(response, "content") else str(response)

                # Parse JSON response
                result = json.loads(content)
                result["assigned_persona"] = persona_data.get("assigned_persona", "unknown")

                span.set_attribute("success", True)
                logger.debug(f"Persona analysis completed for user {state['user_id']}")
                return {"persona_result": result}

            except Exception as e:
                span.set_attribute("error", str(e))
                logger.warning(f"Persona analysis failed: {e}")
                # Return heuristic fallback (persona_data verified non-None above)
                return {
                    "persona_result": {
                        "assigned_persona": persona_data.get("assigned_persona", "unknown"),
                        "detected_persona": persona_data.get("assigned_persona", "unknown"),
                        "confidence": 0.5,
                        "behavior_signals": [],
                        "recommendation": None,
                        "ui_adaptations": [],
                    }
                }

    return persona_analysis


def create_disclosure_analysis_node(llm_factory: Any, settings: Any) -> AnalysisNode:
    """Create a node that performs disclosure analysis."""

    async def disclosure_analysis(state: UXAnalysisState) -> dict[str, Any]:
        """Analyze disclosure level from state data."""
        with tracer.start_as_current_span("disclosure_analysis") as span:
            span.set_attributes({"user_id": state.get("user_id", "unknown")})

            disclosure_data = state.get("disclosure_data")
            if not state.get("include_disclosure") or disclosure_data is None:
                span.set_attribute("skipped", True)
                return {"disclosure_result": None}

            try:
                # Build prompt for disclosure analysis (disclosure_data verified non-None above)
                prompt = f"""Analyze user expertise level:
User ID: {state["user_id"]}
Feature Usage: {disclosure_data.get("feature_usage", {})}
Session History: {disclosure_data.get("session_history", [])}

Return JSON with: current_level, recommended_level, confidence, unlock_features, personalized_message"""

                # Call LLM
                response = await llm_factory.ainvoke(prompt)
                content = response.content if hasattr(response, "content") else str(response)

                # Parse JSON response
                result = json.loads(content)

                span.set_attribute("success", True)
                logger.debug(f"Disclosure analysis completed for user {state['user_id']}")
                return {"disclosure_result": result}

            except Exception as e:
                span.set_attribute("error", str(e))
                logger.warning(f"Disclosure analysis failed: {e}")
                # Return heuristic fallback
                return {
                    "disclosure_result": {
                        "current_level": "intermediate",
                        "recommended_level": "intermediate",
                        "confidence": 0.5,
                        "unlock_features": [],
                        "personalized_message": None,
                    }
                }

    return disclosure_analysis


def create_error_analysis_node(llm_factory: Any, settings: Any) -> AnalysisNode:
    """Create a node that performs error analysis."""

    async def error_analysis(state: UXAnalysisState) -> dict[str, Any]:
        """Analyze error from state data."""
        with tracer.start_as_current_span("error_analysis") as span:
            span.set_attributes({"user_id": state.get("user_id", "unknown")})

            error_data = state.get("error_data")
            if not state.get("include_error") or error_data is None:
                span.set_attribute("skipped", True)
                return {"error_result": None}

            try:
                # Build prompt for error analysis (error_data verified non-None above)
                prompt = f"""Analyze error and suggest recovery:
Error Name: {error_data.get("name", "Unknown")}
Error Message: {error_data.get("message", "")}
Stack Trace: {error_data.get("stack_trace", "N/A")}

Return JSON with: category, subcategory, confidence, root_cause, suggestions"""

                # Call LLM
                response = await llm_factory.ainvoke(prompt)
                content = response.content if hasattr(response, "content") else str(response)

                # Parse JSON response
                result = json.loads(content)

                span.set_attribute("success", True)
                logger.debug(f"Error analysis completed for user {state['user_id']}")
                return {"error_result": result}

            except Exception as e:
                span.set_attribute("error", str(e))
                logger.warning(f"Error analysis failed: {e}")
                # Return heuristic fallback
                return {
                    "error_result": {
                        "classification": {
                            "category": "unknown",
                            "subcategory": "general",
                            "confidence": 0.5,
                        },
                        "root_cause": "Unable to determine root cause",
                        "suggestions": [],
                    }
                }

    return error_analysis


def create_cross_insights_node(llm_factory: Any, settings: Any) -> AnalysisNode:
    """Create a node that generates cross-service insights."""

    async def cross_insights(state: UXAnalysisState) -> dict[str, Any]:
        """Generate cross-insights from analysis results."""
        insights: list[str] = []
        confidences: list[float] = []

        persona_result = state.get("persona_result")
        disclosure_result = state.get("disclosure_result")
        error_result = state.get("error_result")

        # Collect confidences from results
        if persona_result:
            confidences.append(persona_result.get("confidence", 0.5))

            # Check for persona-disclosure mismatch
            if disclosure_result:
                detected_persona = persona_result.get("detected_persona", "")
                assigned_persona = persona_result.get("assigned_persona", "")
                recommended_level = disclosure_result.get("recommended_level", "")

                if detected_persona != assigned_persona:
                    insights.append(
                        f"Persona mismatch detected: assigned={assigned_persona}, "
                        f"detected={detected_persona}. Consider persona upgrade."
                    )

                # Power user with beginner disclosure
                if "builder" in detected_persona.lower() or "analyst" in detected_persona.lower():
                    if recommended_level in ("beginner", "intermediate"):
                        insights.append(
                            "Power user behavior detected with lower disclosure level. Consider enabling advanced features."
                        )

        if disclosure_result:
            confidences.append(disclosure_result.get("confidence", 0.5))

        if error_result:
            classification = error_result.get("classification", {})
            if isinstance(classification, dict):
                confidences.append(classification.get("confidence", 0.5))
            else:
                confidences.append(0.5)

            # Frequent errors for power users might indicate UX issue
            if persona_result:
                detected_persona = persona_result.get("detected_persona", "")
                if "builder" in detected_persona.lower():
                    insights.append("Power user encountering errors. Review workflow complexity and error messaging.")

        # Calculate weighted confidence
        avg_confidence = safe_average(confidences) if confidences else 0.0

        # Boost confidence if multiple high-confidence results agree
        if len(confidences) >= 2 and all(c >= 0.8 for c in confidences):
            avg_confidence = min(1.0, avg_confidence * 1.1)

        # Add general insight if we have cross-service data
        if persona_result and disclosure_result:
            insights.append("Cross-service analysis complete. Persona and disclosure data correlated for personalized UX.")

        return {
            "cross_insights": insights,
            "confidence": round(avg_confidence, 2),
        }

    return cross_insights


# =============================================================================
# Routing Functions
# =============================================================================


def should_run_analysis(state: UXAnalysisState) -> list[str]:
    """Determine which analysis branches to run."""
    branches = []

    if state.get("include_persona") and state.get("persona_data") is not None:
        branches.append("persona")
    if state.get("include_disclosure") and state.get("disclosure_data") is not None:
        branches.append("disclosure")
    if state.get("include_error") and state.get("error_data") is not None:
        branches.append("error")

    return branches if branches else ["skip"]


def after_analyses(state: UXAnalysisState) -> str:
    """Always route to cross_insights after analyses."""
    return "cross_insights"


# =============================================================================
# Graph Factory
# =============================================================================


def create_ux_analysis_graph(
    llm_factory: Any,
    settings: MagicMock | Any,
) -> StateGraph[UXAnalysisState]:
    """Create the UX analysis StateGraph.

    Args:
        llm_factory: LLM factory for AI-powered analysis
        settings: Application settings

    Returns:
        StateGraph configured for UX analysis workflow
    """
    # Create the graph with state schema
    graph = StateGraph(UXAnalysisState)

    # Create analysis nodes
    persona_node = create_persona_analysis_node(llm_factory, settings)
    disclosure_node = create_disclosure_analysis_node(llm_factory, settings)
    error_node = create_error_analysis_node(llm_factory, settings)
    cross_insights_node = create_cross_insights_node(llm_factory, settings)

    # Add nodes to graph
    # Note: LangGraph StateGraph.add_node() has complex type overloads that don't
    # match our async node functions returning dict[str, Any]. This is a known
    # limitation - the nodes work correctly at runtime.
    graph.add_node("persona_analysis", persona_node)  # type: ignore[arg-type,call-overload]
    graph.add_node("disclosure_analysis", disclosure_node)  # type: ignore[arg-type,call-overload]
    graph.add_node("error_analysis", error_node)  # type: ignore[arg-type,call-overload]
    graph.add_node("cross_insights", cross_insights_node)  # type: ignore[arg-type,call-overload]

    # Add a router node that dispatches to appropriate analyses
    async def router(state: UXAnalysisState) -> dict[str, Any]:
        """Router determines which analyses to run."""
        return {}

    graph.add_node("router", router)

    # Set entry point
    graph.set_entry_point("router")

    # Add edges from router to analysis nodes
    # All analyses run in sequence (could be parallelized with Send API)
    graph.add_edge("router", "persona_analysis")
    graph.add_edge("persona_analysis", "disclosure_analysis")
    graph.add_edge("disclosure_analysis", "error_analysis")
    graph.add_edge("error_analysis", "cross_insights")

    # Cross insights is the final node
    graph.add_edge("cross_insights", END)

    return graph


def create_parallel_ux_graph(
    llm_factory: Any,
    settings: MagicMock | Any,
) -> StateGraph[UXAnalysisState]:
    """Create a parallel UX analysis StateGraph using Send API.

    Uses LangGraph's Send API to dispatch analyses to parallel branches,
    allowing concurrent execution of persona, disclosure, and error analyses.

    Args:
        llm_factory: LLM factory for AI-powered analysis
        settings: Application settings

    Returns:
        StateGraph configured for parallel UX analysis workflow
    """
    # Create the graph with state schema
    graph = StateGraph(UXAnalysisState)

    # Create analysis nodes
    persona_node = create_persona_analysis_node(llm_factory, settings)
    disclosure_node = create_disclosure_analysis_node(llm_factory, settings)
    error_node = create_error_analysis_node(llm_factory, settings)
    cross_insights_node = create_cross_insights_node(llm_factory, settings)

    # Add nodes to graph
    # Cast analysis nodes to StateNode for LangGraph's strict typing
    # Use string forward reference since StateNode is only imported under TYPE_CHECKING
    graph.add_node("persona_analysis", cast("StateNode[UXAnalysisState, Any]", persona_node))
    graph.add_node("disclosure_analysis", cast("StateNode[UXAnalysisState, Any]", disclosure_node))
    graph.add_node("error_analysis", cast("StateNode[UXAnalysisState, Any]", error_node))
    graph.add_node("cross_insights", cast("StateNode[UXAnalysisState, Any]", cross_insights_node))

    # Entry node that just passes through
    async def entry_node(state: UXAnalysisState) -> dict[str, Any]:
        """Entry point that passes state through."""
        return {}

    graph.add_node("entry", entry_node)

    # Dispatcher function for conditional edges with Send API
    def dispatch_to_analyses(state: UXAnalysisState) -> list[Send]:
        """Dispatch analyses to parallel branches using Send API."""
        sends: list[Send] = []

        if state.get("include_persona") and state.get("persona_data") is not None:
            sends.append(Send("persona_analysis", state))
        if state.get("include_disclosure") and state.get("disclosure_data") is not None:
            sends.append(Send("disclosure_analysis", state))
        if state.get("include_error") and state.get("error_data") is not None:
            sends.append(Send("error_analysis", state))

        # If no analyses to run, skip to cross_insights
        if not sends:
            sends.append(Send("cross_insights", state))

        return sends

    # Set entry point
    graph.set_entry_point("entry")

    # Add conditional edges from entry using Send for parallel dispatch
    graph.add_conditional_edges("entry", dispatch_to_analyses)

    # All analysis nodes converge to cross_insights
    graph.add_edge("persona_analysis", "cross_insights")
    graph.add_edge("disclosure_analysis", "cross_insights")
    graph.add_edge("error_analysis", "cross_insights")

    # Cross insights is the final node
    graph.add_edge("cross_insights", END)

    return graph
