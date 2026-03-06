"""Context Graph API endpoints.

Provides REST API access to decision traces and precedent search.

Endpoints:
- GET /context-graph/traces/{trace_id} - Get a specific trace
- GET /context-graph/sessions/{session_id}/traces - Get traces for a session
- POST /context-graph/precedents/search - Search for similar past decisions

Authorization:
- Traces are scoped to sessions - requires viewer access to session
- Precedent search is scoped to user's organization

Reference: ADR-0101 Context Graphs, ADR-0068 Gateway-Level Authentication
"""

from typing import TYPE_CHECKING, Any

from fastapi import APIRouter, Depends, HTTPException, Query, status
from starlette.requests import Request

from mcp_server_langgraph.auth.dependencies import get_current_user
from mcp_server_langgraph.auth.metrics import log_authorization_denied
from mcp_server_langgraph.core.feature_flags import feature_flags
from mcp_server_langgraph.storage.models import (
    DecisionTraceRead,
    DecisionTraceSummary,
    PrecedentSearchRequest,
    PrecedentSearchResult,
)

if TYPE_CHECKING:
    from mcp_server_langgraph.repositories.decision_trace import (
        DecisionTraceRepositoryBase,
    )

router = APIRouter(prefix="/context-graph", tags=["context-graph"])


def get_authorization_service(request: Request) -> Any:
    """Get authorization service from app state.

    Returns the authorization middleware/service for OpenFGA checks.
    Falls back to None if not available (for testing).
    """
    return getattr(request.app.state, "auth_middleware", None)


def _get_user_id(user: dict[str, Any]) -> str:
    """Extract user ID from authenticated user dict.

    Formats as 'user:xxx' for OpenFGA compatibility.
    """
    user_id = user.get("sub") or user.get("user_id") or "anonymous"
    if not user_id.startswith("user:"):
        user_id = f"user:{user_id}"
    return user_id


async def _check_session_authorization(
    session_id: str,
    user: dict[str, Any],
    auth_service: Any,
    relation: str = "viewer",
) -> bool:
    """Check if user has access to a session.

    Args:
        session_id: The session ID to check access for
        user: Authenticated user dict
        auth_service: Authorization service for OpenFGA checks
        relation: Required relation (default: viewer)

    Returns:
        True if authorized, False otherwise
    """
    if auth_service is None:
        # Fallback: Allow if auth service not configured (dev mode)
        return True

    user_id = _get_user_id(user)
    resource = f"session:{session_id}"

    try:
        authorized = await auth_service.authorize(
            user_id=user_id,
            relation=relation,
            resource=resource,
        )
        return bool(authorized)
    except Exception:
        # Log error but fail closed for security
        return False


def get_decision_repository(request: Request) -> "DecisionTraceRepositoryBase":
    """Get repository from app state.

    FastAPI dependency that provides access to the decision trace repository.

    Raises:
        HTTPException: 503 if context graph not enabled
    """
    if not getattr(request.app.state, "decision_emitter", None):
        raise HTTPException(503, "Context graph not enabled")
    # Repository is accessible via emitter
    repo: DecisionTraceRepositoryBase = request.app.state.decision_emitter._repository
    return repo


# Alias for backward compatibility with tests
_get_repository = get_decision_repository


@router.get("/traces/{trace_id}")
async def get_trace(
    trace_id: str,
    request: Request,
    repo: "DecisionTraceRepositoryBase" = Depends(get_decision_repository),
    current_user: dict[str, Any] = Depends(get_current_user),
) -> DecisionTraceRead:
    """Get a specific decision trace.

    Authorization: Requires viewer access to the trace's session.

    Args:
        trace_id: The trace ID to retrieve
        request: FastAPI request for auth service access
        repo: Decision trace repository (injected)
        current_user: Authenticated user (injected)

    Returns:
        DecisionTraceRead with full trace data

    Raises:
        HTTPException: 403 if not authorized to view trace
        HTTPException: 404 if trace not found
        HTTPException: 503 if context graph not enabled
    """
    trace = await repo.get_by_id(trace_id)
    if not trace:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Trace not found")

    # Authorization: User must have viewer access to the session
    auth_service = get_authorization_service(request)
    authorized = await _check_session_authorization(
        session_id=trace.session_id,
        user=current_user,
        auth_service=auth_service,
        relation="viewer",
    )

    if not authorized:
        user_id = _get_user_id(current_user)
        resource = f"session:{trace.session_id}"
        log_authorization_denied(
            user_id=user_id,
            relation="viewer",
            resource=resource,
            reason="permission_denied",
        )
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail=f"Not authorized: {user_id} cannot view traces for {resource}",
        )

    return trace


@router.get("/sessions/{session_id}/traces")
async def get_session_traces(
    session_id: str,
    request: Request,
    limit: int = Query(default=100, ge=1, le=1000),
    offset: int = Query(default=0, ge=0),
    repo: "DecisionTraceRepositoryBase" = Depends(get_decision_repository),
    current_user: dict[str, Any] = Depends(get_current_user),
) -> list[DecisionTraceSummary]:
    """Get decision traces for a session.

    Authorization: Requires viewer access to the session.

    Args:
        session_id: The session ID to get traces for
        request: FastAPI request for auth service access
        limit: Max traces to return (default 100, max 1000)
        offset: Pagination offset (default 0)
        repo: Decision trace repository (injected)
        current_user: Authenticated user (injected)

    Returns:
        List of DecisionTraceSummary objects

    Raises:
        HTTPException: 403 if not authorized to view session traces
    """
    # Authorization: User must have viewer access to the session
    auth_service = get_authorization_service(request)
    authorized = await _check_session_authorization(
        session_id=session_id,
        user=current_user,
        auth_service=auth_service,
        relation="viewer",
    )

    if not authorized:
        user_id = _get_user_id(current_user)
        resource = f"session:{session_id}"
        log_authorization_denied(
            user_id=user_id,
            relation="viewer",
            resource=resource,
            reason="permission_denied",
        )
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail=f"Not authorized: {user_id} cannot view traces for {resource}",
        )

    return await repo.get_by_session(
        session_id=session_id,
        limit=limit,
        offset=offset,
    )


@router.post("/precedents/search")
async def search_precedents(
    body: PrecedentSearchRequest,
    request: Request,
    repo: "DecisionTraceRepositoryBase" = Depends(get_decision_repository),
    current_user: dict[str, Any] = Depends(get_current_user),
) -> list[PrecedentSearchResult]:
    """Search for similar past decisions.

    Uses semantic search to find precedents that match the query.
    Results are scoped to the user's organization for security.

    Authorization: Results are scoped to user's organization.

    Args:
        body: Search parameters including query text
        request: FastAPI request for app state access
        repo: Decision trace repository (injected)
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

    # Extract user ID and organization ID from current_user dict
    user_id = current_user.get("sub") or current_user.get("user_id") or "anonymous"
    organization_id = current_user.get("organization_id") or "default"

    # Search is scoped to user's organization for security
    results = await manager.search_precedents(
        query=body.query,
        user_id=user_id,
        organization_id=organization_id,
        limit=body.limit,
        decision_type=body.decision_type.value if body.decision_type else None,
    )

    # Fetch full traces
    output = []
    for r in results:
        trace = await repo.get_by_id(r["trace_id"])
        if trace:
            output.append(PrecedentSearchResult(trace=trace, similarity_score=r["score"]))

    return output
