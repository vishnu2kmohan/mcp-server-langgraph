"""Helper for accessing DecisionEmitter without constructor changes.

Avoids modifying all orchestrator constructors by providing convenient
helper functions to access the DecisionEmitter from app.state.

Reference: ADR-0101 Context Graphs
"""

from typing import TYPE_CHECKING

from starlette.requests import Request

if TYPE_CHECKING:
    from mcp_server_langgraph.agents.decision_emitter import (
        DecisionContext,
        DecisionEmitter,
    )


def get_decision_emitter(request: Request) -> "DecisionEmitter | None":
    """Get DecisionEmitter from app.state.

    Args:
        request: The Starlette/FastAPI request object

    Returns:
        DecisionEmitter if configured, None otherwise
    """
    return getattr(request.app.state, "decision_emitter", None)


async def emit_routing_decision(
    request: Request,
    context: "DecisionContext",
    query: str,
    chosen_action: str,
    confidence: float,
    rationale: str,
    available_actions: list[str] | None = None,
) -> str | None:
    """Emit a routing decision trace.

    Used when the agent routes to a specific action/tool based on user query.

    Args:
        request: The FastAPI request object
        context: Decision context (session, user, org info)
        query: The user query being processed
        chosen_action: The action/route chosen
        confidence: Confidence score (0.0 to 1.0)
        rationale: Explanation of why this route was chosen
        available_actions: List of actions that were considered

    Returns:
        trace_id if emitted, None if disabled or emitter not available
    """
    emitter = get_decision_emitter(request)
    if not emitter:
        return None

    return await emitter.emit(
        context=context,
        decision_type="routing",
        decision_stage="action",
        query_text=query,
        chosen_action=chosen_action,
        confidence=confidence,
        rationale=rationale,
        available_options=available_actions,
    )


async def emit_tool_selection_decision(
    request: Request,
    context: "DecisionContext",
    query: str,
    selected_tools: list[str],
    confidence: float,
    rationale: str,
    available_tools: list[str] | None = None,
) -> str | None:
    """Emit a tool selection decision trace.

    Used when the agent selects specific tools to execute.

    Args:
        request: The FastAPI request object
        context: Decision context (session, user, org info)
        query: The user query being processed
        selected_tools: List of tools selected for execution
        confidence: Confidence score (0.0 to 1.0)
        rationale: Explanation of tool selection
        available_tools: List of tools that were available

    Returns:
        trace_id if emitted, None if disabled or emitter not available
    """
    emitter = get_decision_emitter(request)
    if not emitter:
        return None

    return await emitter.emit(
        context=context,
        decision_type="tool_selection",
        decision_stage="action",
        query_text=query,
        chosen_action=",".join(selected_tools) if selected_tools else "none",
        confidence=confidence,
        rationale=rationale,
        available_options=available_tools,
        selected_items=selected_tools,
    )


async def emit_model_selection_decision(
    request: Request,
    context: "DecisionContext",
    query: str,
    selected_model: str,
    confidence: float,
    rationale: str,
    available_models: list[str] | None = None,
) -> str | None:
    """Emit a model selection decision trace.

    Used when the agent selects which LLM model to use.

    Args:
        request: The FastAPI request object
        context: Decision context (session, user, org info)
        query: The user query being processed
        selected_model: The model selected for inference
        confidence: Confidence score (0.0 to 1.0)
        rationale: Explanation of model selection
        available_models: List of models that were available

    Returns:
        trace_id if emitted, None if disabled or emitter not available
    """
    emitter = get_decision_emitter(request)
    if not emitter:
        return None

    return await emitter.emit(
        context=context,
        decision_type="model_selection",
        decision_stage="action",
        query_text=query,
        chosen_action=selected_model,
        confidence=confidence,
        rationale=rationale,
        available_options=available_models,
    )


async def emit_approval_decision(
    request: Request,
    context: "DecisionContext",
    query: str,
    approved: bool,
    confidence: float,
    rationale: str,
) -> str | None:
    """Emit an approval decision trace.

    Used when HITL (human-in-the-loop) approval is required or granted.

    Args:
        request: The FastAPI request object
        context: Decision context (session, user, org info)
        query: The action requiring approval
        approved: Whether the action was approved
        confidence: Confidence that approval is needed (0.0 to 1.0)
        rationale: Explanation of approval decision

    Returns:
        trace_id if emitted, None if disabled or emitter not available
    """
    emitter = get_decision_emitter(request)
    if not emitter:
        return None

    return await emitter.emit(
        context=context,
        decision_type="approval",
        decision_stage="policy_check",
        query_text=query,
        chosen_action="approved" if approved else "requires_approval",
        confidence=confidence,
        rationale=rationale,
    )
