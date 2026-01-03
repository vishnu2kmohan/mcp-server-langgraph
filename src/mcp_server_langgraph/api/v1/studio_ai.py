"""
Studio AI API Router (Sprint 1)

Unified API endpoint for all StudioShell AI capabilities.

Provides a single composite analysis endpoint that:
- Accepts multiple task types across 8 categories
- Executes tasks in parallel via StudioOrchestrator
- Returns synthesized cross-category insights
- Respects feature flags and cost controls

Usage:
    POST /api/v1/studio/analyze
    {
        "user_id": "user-123",
        "session_id": "session-456",
        "persona": "alice-builder",
        "tasks": [
            {"category": "ux", "type": "persona_analysis", "data": {}},
            {"category": "session", "type": "session_summarize", "data": {}}
        ]
    }

Reference: StudioShell AI Enhancement Analysis Plan
"""

from __future__ import annotations

import logging
from decimal import Decimal
from typing import Annotated, Any

from fastapi import APIRouter, Depends, HTTPException, Request
from pydantic import BaseModel, Field

from mcp_server_langgraph.auth.dependencies import get_current_user

# Type alias for current user
CurrentUser = Annotated[dict[str, Any], Depends(get_current_user)]

from mcp_server_langgraph.agents.genui_orchestrator import (
    GenUIOrchestrator,
    GenUITask,
)
from mcp_server_langgraph.agents.studio_orchestrator import (
    StudioOrchestrator,
)
from mcp_server_langgraph.core.feature_flags import feature_flags
from mcp_server_langgraph.websocket.handlers.orchestrator_status import (
    get_orchestrator_status_broadcaster,
)

logger = logging.getLogger(__name__)

# =============================================================================
# Router
# =============================================================================

studio_ai_router = APIRouter(tags=["studio-ai"])


# =============================================================================
# Request/Response Models
# =============================================================================


class TaskRequest(BaseModel):
    """Individual task request within composite analysis."""

    category: str = Field(..., description="Task category (ux, session, canvas, etc.)")
    type: str = Field(..., description="Task type (persona_analysis, session_summarize, etc.)")
    data: dict[str, Any] = Field(default_factory=dict, description="Task-specific data")


class StudioAnalyzeRequest(BaseModel):
    """Request model for unified Studio AI analysis."""

    user_id: str = Field(..., description="User identifier")
    session_id: str = Field(..., description="Session identifier")
    persona: str | None = Field(None, description="User persona for RBAC filtering")
    tasks: list[TaskRequest] = Field(
        default_factory=list,
        description="List of tasks to execute in parallel",
    )
    context: dict[str, Any] = Field(
        default_factory=dict,
        description="Additional context for analysis",
    )


class StudioAnalyzeResponse(BaseModel):
    """Response model for unified Studio AI analysis."""

    user_id: str = Field(..., description="User identifier")
    session_id: str = Field(..., description="Session identifier")
    analyses: dict[str, Any] = Field(
        default_factory=dict,
        description="Results by task type",
    )
    cross_insights: list[str] = Field(
        default_factory=list,
        description="Cross-category synthesized insights",
    )
    failed_analyses: list[str] = Field(
        default_factory=list,
        description="List of failed task types",
    )
    total_cost: str = Field(
        default="0",
        description="Total cost of analysis as string (Decimal-compatible)",
    )


class GenUIRequest(BaseModel):
    """Request model for GenUI widget generation."""

    tasks: list[dict[str, Any]] = Field(
        default_factory=list,
        description="List of GenUI tasks (generate_widget, render_data, execute_form)",
    )


class GenUIResponse(BaseModel):
    """Response model for GenUI widget generation."""

    widgets: list[dict[str, Any]] = Field(
        default_factory=list,
        description="Generated widget configurations",
    )
    layout: str = Field(
        default="single",
        description="Suggested layout for widgets",
    )
    total_count: int = Field(
        default=0,
        description="Total number of widgets generated",
    )
    errors: list[str] | None = Field(
        default=None,
        description="Errors encountered during generation",
    )


# =============================================================================
# Dependencies
# =============================================================================


def get_studio_orchestrator(request: Request) -> StudioOrchestrator:
    """Get or create StudioOrchestrator instance with DI from app.state.

    Injects AIUXService and LLMFactory from request.app.state when available.
    Falls back gracefully to None if not configured.

    Args:
        request: FastAPI request object with app.state.

    Returns:
        StudioOrchestrator configured for request handling.
    """
    # Extract services from app.state (graceful fallback to None)
    ai_ux_service = getattr(request.app.state, "ai_ux_service", None)
    llm_factory = getattr(request.app.state, "llm_factory", None)

    return StudioOrchestrator(
        ai_ux_service=ai_ux_service,
        llm_factory=llm_factory,
        enable_metrics=True,
        status_broadcaster=get_orchestrator_status_broadcaster(),
    )


def get_genui_orchestrator(request: Request) -> GenUIOrchestrator:
    """Get or create GenUIOrchestrator instance with DI from app.state.

    Injects LLMFactory from request.app.state when available.
    Falls back gracefully to None if not configured.

    Args:
        request: FastAPI request object with app.state.

    Returns:
        GenUIOrchestrator configured for request handling.
    """
    # Extract LLM factory from app.state (graceful fallback to None)
    llm_factory = getattr(request.app.state, "llm_factory", None)

    return GenUIOrchestrator(
        llm_factory=llm_factory,
        enable_metrics=True,
    )


# =============================================================================
# Endpoints
# =============================================================================


@studio_ai_router.post(
    "/analyze",
    response_model=StudioAnalyzeResponse,
    summary="Unified composite analysis for StudioShell AI",
    description="""
    Execute multiple AI analysis tasks in parallel and synthesize results.

    Supports task categories:
    - ux: Persona, disclosure, error analysis, nudges
    - session: Session summarize, group, similarity
    - conversation: Intent detect, context optimize, goal track
    - canvas: Artifact type suggest, code analyze, diff explain
    - diagram: Diagram analyze, diagram-to-code
    - trace: Trace summarize, trace anomaly
    - hitl: Risk assess, decision history
    - command: Command interpret, inline suggest, AI edit generate

    Returns synthesized cross-category insights.
    """,
)
async def analyze(
    current_user: CurrentUser,
    request: StudioAnalyzeRequest,
    orchestrator: StudioOrchestrator = Depends(get_studio_orchestrator),
) -> StudioAnalyzeResponse:
    """Execute unified Studio AI analysis.

    Args:
        request: Analysis request with user context and tasks
        orchestrator: StudioOrchestrator instance

    Returns:
        Composite analysis results with cross-insights

    Raises:
        HTTPException: 503 if feature flag is disabled
    """
    # Check feature flag
    if not feature_flags.enable_studio_ai:
        raise HTTPException(
            status_code=503,
            detail="Studio AI feature is not enabled",
        )

    try:
        # Convert request tasks to StudioTask objects
        # If no tasks provided, return empty result
        if not request.tasks:
            return StudioAnalyzeResponse(
                user_id=request.user_id,
                session_id=request.session_id,
                analyses={},
                cross_insights=[],
                failed_analyses=[],
                total_cost="0",
            )

        # Use orchestrator's analyze method
        # Map task types to category include flags
        task_types = [t.type for t in request.tasks]
        task_categories = [t.category for t in request.tasks]

        result = await orchestrator.analyze(
            user_id=request.user_id,
            session_id=request.session_id,
            persona=request.persona,
            include_ux=any(t in task_types for t in ("persona_analysis", "disclosure_analysis", "error_analysis"))
            or "ux" in task_categories,
            include_session="session" in task_categories,
            include_conversation="conversation" in task_categories,
            include_canvas="canvas" in task_categories,
            include_diagram="diagram" in task_categories,
            include_trace="trace" in task_categories,
            include_hitl="hitl" in task_categories,
            include_command="command" in task_categories,
        )

        # Convert Decimal to string for JSON serialization
        total_cost = result.get("total_cost", Decimal("0"))
        if isinstance(total_cost, Decimal):
            total_cost = str(total_cost)

        return StudioAnalyzeResponse(
            user_id=result.get("user_id", request.user_id),
            session_id=result.get("session_id", request.session_id),
            analyses=result.get("analyses", {}),
            cross_insights=result.get("cross_insights", []),
            failed_analyses=result.get("failed_analyses", []),
            total_cost=total_cost,
        )

    except Exception as e:
        logger.exception(f"Error in Studio AI analysis: {e}")
        raise HTTPException(
            status_code=500,
            detail=f"Analysis failed: {str(e)}",
        ) from e


@studio_ai_router.post(
    "/genui",
    response_model=GenUIResponse,
    summary="Generate dynamic UI widgets using AI",
    description="""
    Generate dynamic UI widgets based on prompts and data.

    Supports task types:
    - generate_widget: Create chart/table/text widgets from prompts
    - render_data: Transform raw data into widget format
    - execute_form: Handle form submission with AI validation

    Returns synthesized widget layout.
    """,
)
async def generate_ui(
    genui_request: GenUIRequest,
    current_user: CurrentUser,
    orchestrator: GenUIOrchestrator = Depends(get_genui_orchestrator),
) -> dict[str, Any]:
    """Generate dynamic UI widgets.

    Args:
        genui_request: GenUI request with tasks to execute
        current_user: Authenticated user context
        orchestrator: GenUIOrchestrator instance (injected via DI)

    Returns:
        Generated widgets with layout suggestion

    Raises:
        HTTPException: 503 if feature flag is disabled
    """
    # Check feature flag - graceful degradation if disabled
    if not feature_flags.enable_genui:
        logger.info("GenUI feature disabled, returning fallback")
        # Return empty but valid response
        return {
            "widgets": [],
            "layout": "single",
            "total_count": 0,
            "errors": None,
        }

    try:
        # Convert request tasks to GenUITask objects
        tasks = [
            GenUITask(
                task_type=task.get("task_type", "generate_widget"),
                data=task.get("data", {}),
            )
            for task in genui_request.tasks
        ]

        # Execute tasks
        results = await orchestrator.execute(tasks)

        # Synthesize results into layout
        synthesized = orchestrator.synthesize(results)

        return synthesized

    except Exception as e:
        logger.exception(f"Error in GenUI generation: {e}")
        raise HTTPException(
            status_code=500,
            detail=f"Generation failed: {str(e)}",
        ) from e
