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
from typing import Any

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, Field

from mcp_server_langgraph.agents.studio_orchestrator import (
    StudioOrchestrator,
)
from mcp_server_langgraph.core.feature_flags import feature_flags

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


# =============================================================================
# Dependencies
# =============================================================================


def get_studio_orchestrator() -> StudioOrchestrator:
    """Get or create StudioOrchestrator instance.

    Returns:
        StudioOrchestrator configured for request handling
    """
    # TODO: In production, inject AIUXService, LLMFactory via proper DI
    return StudioOrchestrator(
        ai_ux_service=None,  # Will be injected in later sprints
        llm_factory=None,
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
