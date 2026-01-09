"""Context Graph API endpoints.

Provides REST API access to decision traces and precedent search.

Endpoints:
- GET /context-graph/traces/{trace_id} - Get a specific trace
- GET /context-graph/sessions/{session_id}/traces - Get traces for a session
- POST /context-graph/precedents/search - Search for similar past decisions

Reference: ADR-0101 Context Graphs
"""

from fastapi import APIRouter, Depends, HTTPException, Query
from starlette.requests import Request

from mcp_server_langgraph.auth.dependencies import get_current_user
from mcp_server_langgraph.core.feature_flags import feature_flags
from mcp_server_langgraph.storage.models import (
    DecisionTraceRead,
    DecisionTraceSummary,
    PrecedentSearchRequest,
    PrecedentSearchResult,
)

router = APIRouter(prefix="/context-graph", tags=["context-graph"])


def get_decision_repository(request: Request):
    """Get repository from app state.

    FastAPI dependency that provides access to the decision trace repository.

    Raises:
        HTTPException: 503 if context graph not enabled
    """
    if not getattr(request.app.state, "decision_emitter", None):
        raise HTTPException(503, "Context graph not enabled")
    # Repository is accessible via emitter
    return request.app.state.decision_emitter._repository


# Alias for backward compatibility with tests
_get_repository = get_decision_repository


@router.get("/traces/{trace_id}", response_model=DecisionTraceRead)
async def get_trace(
    trace_id: str,
    repo=Depends(get_decision_repository),
    current_user=Depends(get_current_user),
):
    """Get a specific decision trace.

    Args:
        trace_id: The trace ID to retrieve
        repo: Decision trace repository (injected)
        current_user: Authenticated user (injected)

    Returns:
        DecisionTraceRead with full trace data

    Raises:
        HTTPException: 404 if trace not found
        HTTPException: 503 if context graph not enabled
    """
    trace = await repo.get_by_id(trace_id)
    if not trace:
        raise HTTPException(404, "Trace not found")
    # TODO: Add OpenFGA authorization check
    return trace


@router.get("/sessions/{session_id}/traces", response_model=list[DecisionTraceSummary])
async def get_session_traces(
    session_id: str,
    limit: int = Query(default=100, ge=1, le=1000),
    offset: int = Query(default=0, ge=0),
    repo=Depends(get_decision_repository),
    current_user=Depends(get_current_user),
):
    """Get decision traces for a session.

    Args:
        session_id: The session ID to get traces for
        limit: Max traces to return (default 100, max 1000)
        offset: Pagination offset (default 0)
        repo: Decision trace repository (injected)
        current_user: Authenticated user (injected)

    Returns:
        List of DecisionTraceSummary objects
    """
    return await repo.get_by_session(
        session_id=session_id,
        limit=limit,
        offset=offset,
    )


@router.post("/precedents/search", response_model=list[PrecedentSearchResult])
async def search_precedents(
    body: PrecedentSearchRequest,
    request: Request,
    current_user=Depends(get_current_user),
):
    """Search for similar past decisions.

    Uses semantic search to find precedents that match the query.

    Args:
        body: Search parameters including query text
        request: FastAPI request for app state access
        current_user: Authenticated user (injected)

    Returns:
        List of PrecedentSearchResult with matching traces and scores

    Raises:
        HTTPException: 503 if precedent search not enabled
    """
    if not feature_flags.enable_precedent_search:
        raise HTTPException(503, "Precedent search not enabled")

    # Get semantic index manager from dependencies
    from mcp_server_langgraph.core.dependencies import get_semantic_index_manager

    manager = get_semantic_index_manager()
    if not manager:
        raise HTTPException(503, "Semantic index manager not configured")

    results = await manager.search_precedents(
        query=body.query,
        user_id=current_user.user_id,
        organization_id=current_user.organization_id,
        limit=body.limit,
        decision_type=body.decision_type.value if body.decision_type else None,
    )

    # Fetch full traces
    repo = _get_repository(request)
    output = []
    for r in results:
        trace = await repo.get_by_id(r["trace_id"])
        if trace:
            output.append(PrecedentSearchResult(trace=trace, similarity_score=r["score"]))

    return output
