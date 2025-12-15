"""
Projects API Endpoints

Implements the Unified Workspace Paradigm where:
    One Project = Session + Workflow + Connections

Projects serve as containers that unify:
- Sessions: Chat conversations and message history
- Workflows: LangGraph workflow definitions
- Connections: MCP tools, Vector stores, and integrations

Usage:
    from mcp_server_langgraph.api.v1.projects import projects_router
    app.include_router(projects_router)
"""

from datetime import UTC, datetime
from typing import Annotated, Any, Literal
from uuid import uuid4

from fastapi import APIRouter, Depends, HTTPException, Query, Request, status
from pydantic import BaseModel, Field

from mcp_server_langgraph.auth.middleware import get_current_user
from mcp_server_langgraph.core.dependencies import get_project_repository
from mcp_server_langgraph.storage.base import ProjectRepository
from mcp_server_langgraph.storage.models import Project, ProjectConnection

# Type alias for authenticated user dependency
CurrentUser = Annotated[dict[str, Any], Depends(get_current_user)]


# ============================================================================
# Models
# ============================================================================


class ProjectCreate(BaseModel):
    """Request body for creating a new project."""

    name: str = Field(..., min_length=1, max_length=255, description="Project name")
    description: str | None = Field(None, max_length=2000, description="Project description")
    organization_id: str | None = Field(None, description="Optional organization ID")


class ProjectUpdate(BaseModel):
    """Request body for updating a project."""

    name: str | None = Field(None, min_length=1, max_length=255, description="New project name")
    description: str | None = Field(None, max_length=2000, description="New description")


class ProjectMember(BaseModel):
    """A member of a project with their role."""

    user_id: str
    role: str = Field(..., description="Role: owner, editor, viewer, executor")
    added_at: str


class WorkflowRef(BaseModel):
    """Reference to a workflow within a project."""

    id: str
    name: str
    created_at: str | None = None


class SessionRef(BaseModel):
    """Reference to a session within a project."""

    id: str
    name: str
    message_count: int = 0
    created_at: str | None = None


class ConnectionRef(BaseModel):
    """Reference to a connection (MCP, Vector, etc.) within a project."""

    id: str
    type: str = Field(..., description="Type: mcp_server, vector_store, api_key")
    name: str
    status: str = "active"


class ProjectResponse(BaseModel):
    """Response model for a project."""

    id: str
    name: str
    description: str | None = None
    organization_id: str | None = None
    owner_id: str
    owner_name: str | None = None  # Resolved display name for owner
    created_at: str
    updated_at: str

    # Child resource counts
    workflow_count: int = 0
    session_count: int = 0
    connection_count: int = 0

    # Status
    status: str = "active"


class ProjectDetailResponse(ProjectResponse):
    """Detailed response model including child resources."""

    workflows: list[WorkflowRef] = []
    sessions: list[SessionRef] = []
    connections: list[ConnectionRef] = []
    members: list[ProjectMember] = []


class ProjectListResponse(BaseModel):
    """Response model for listing projects.

    Uses 'items' field to match PagePaginatedResponse<T> contract expected by frontend.
    """

    items: list[ProjectResponse]
    total: int
    page: int = 1
    per_page: int = 20
    total_pages: int = 1


class AddMemberRequest(BaseModel):
    """Request to add a member to a project."""

    user_id: str
    role: str = Field(..., description="Role: editor, viewer, executor")


class AddResourceRequest(BaseModel):
    """Request to add a resource (workflow, session, connection) to a project."""

    resource_type: str = Field(..., description="Type: workflow, session, connection")
    resource_id: str


# ============================================================================
# Router
# ============================================================================

projects_router = APIRouter(prefix="/projects", tags=["projects"])


# ============================================================================
# Helper Functions
# ============================================================================


def _extract_owner_name(owner_id: str) -> str | None:
    """Extract a display name from owner_id.

    Handles formats like:
    - "user:alice" -> "alice"
    - "alice" -> "alice"
    - UUID -> None (keep as-is in owner_id)
    """
    if not owner_id:
        return None
    # Handle "user:username" format
    if ":" in owner_id:
        parts = owner_id.split(":", 1)
        if len(parts) == 2 and parts[0] == "user":
            return parts[1]
    # If it looks like a UUID, don't use as display name
    if len(owner_id) == 36 and owner_id.count("-") == 4:
        return None
    # Otherwise use the owner_id as display name
    return owner_id


def _project_to_detail_response(project: Project) -> ProjectDetailResponse:
    """Convert a Project entity to ProjectDetailResponse."""
    return ProjectDetailResponse(
        id=project.id,
        name=project.name,
        description=project.description,
        organization_id=project.organization_id,
        owner_id=project.owner_id,
        owner_name=_extract_owner_name(project.owner_id),
        created_at=project.created_at.isoformat().replace("+00:00", "Z") if project.created_at else "",
        updated_at=project.updated_at.isoformat().replace("+00:00", "Z") if project.updated_at else "",
        workflow_count=len(project.workflows),
        session_count=len(project.sessions),
        connection_count=len(project.connections),
        status=project.status,
        workflows=[
            WorkflowRef(
                id=w.id,
                name=w.name,
                created_at=w.added_at.isoformat().replace("+00:00", "Z") if w.added_at else None,
            )
            for w in project.workflows
        ],
        sessions=[
            SessionRef(
                id=s.id,
                name=s.name,
                message_count=s.message_count,
                created_at=s.added_at.isoformat().replace("+00:00", "Z") if s.added_at else None,
            )
            for s in project.sessions
        ],
        connections=[
            ConnectionRef(
                id=c.id,
                type=c.connection_type,
                name=c.name,
                status=c.status,
            )
            for c in project.connections
        ],
        members=[
            ProjectMember(
                user_id=m.user_id,
                role=m.role,
                added_at=m.added_at.isoformat().replace("+00:00", "Z") if m.added_at else "",
            )
            for m in project.members
        ],
    )


# ============================================================================
# CRUD Endpoints
# ============================================================================


@projects_router.get(
    "",
    summary="List projects",
    description="List all projects accessible to the current user with sorting, filtering, and search.",
)
async def list_projects(
    page: int = Query(1, ge=1, description="Page number (1-indexed)"),
    per_page: int = Query(20, ge=1, le=100, description="Items per page"),
    organization_id: str | None = Query(None, description="Filter by organization ID"),
    status: str | None = Query(None, description="Filter by project status (active, archived)"),
    owner_id: str | None = Query(None, description="Filter by owner user ID"),
    search: str | None = Query(None, min_length=1, max_length=500, description="Search in name and description"),
    sort_by: Literal["name", "created_at", "updated_at"] = Query("created_at", description="Field to sort by"),
    sort_order: Literal["asc", "desc"] = Query("desc", description="Sort order"),
    repo: ProjectRepository = Depends(get_project_repository),
) -> ProjectListResponse:
    """List all projects the user has access to.

    Supports:
    - Pagination: page, per_page
    - Filtering: organization_id, status, owner_id
    - Search: search (searches name and description)
    - Sorting: sort_by, sort_order
    """
    # Use repository to list projects with filtering
    summaries, _next_cursor = await repo.list(
        limit=per_page,
        organization_id=organization_id,
        status=status,
        owner_id=owner_id,
        search=search,
        sort_by=sort_by,
        sort_order=sort_order,
    )

    # Convert to response format
    projects = [
        ProjectResponse(
            id=s.id,
            name=s.name,
            description=s.description,
            organization_id=s.organization_id,
            owner_id=s.owner_id,
            owner_name=_extract_owner_name(s.owner_id),
            created_at=s.created_at.isoformat().replace("+00:00", "Z") if s.created_at else "",
            updated_at=s.updated_at.isoformat().replace("+00:00", "Z") if s.updated_at else "",
            workflow_count=s.workflow_count,
            session_count=s.session_count,
            connection_count=s.connection_count,
            status=s.status,
        )
        for s in summaries
    ]

    # Calculate total_pages
    total_count = len(projects)  # Note: For cursor-based, this is page count
    total_pages = max(1, (total_count + per_page - 1) // per_page)

    return ProjectListResponse(
        items=projects,
        total=total_count,
        page=page,
        per_page=per_page,
        total_pages=total_pages,
    )


@projects_router.post(
    "",
    status_code=status.HTTP_201_CREATED,
    summary="Create project",
    description="Create a new project as a unified workspace.",
)
async def create_project(
    body: ProjectCreate,
    current_user: CurrentUser,
    repo: ProjectRepository = Depends(get_project_repository),
) -> ProjectResponse:
    """Create a new project."""
    project_id = str(uuid4())
    now = datetime.now(UTC)

    # Extract user info from auth context
    user_id: str = current_user.get("sub") or current_user.get("preferred_username") or "anonymous"
    username: str = current_user.get("preferred_username") or current_user.get("username") or ""

    # Create project entity
    project_entity = Project(
        id=project_id,
        name=body.name,
        description=body.description or "",
        organization_id=body.organization_id,
        owner_id=user_id,
        status="active",
        created_at=now,
        updated_at=now,
    )

    # Save to database
    created = await repo.create(project_entity)

    return ProjectResponse(
        id=created.id,
        name=created.name,
        description=created.description,
        organization_id=created.organization_id,
        owner_id=created.owner_id,
        owner_name=username or None,
        created_at=created.created_at.isoformat().replace("+00:00", "Z") if created.created_at else "",
        updated_at=created.updated_at.isoformat().replace("+00:00", "Z") if created.updated_at else "",
        workflow_count=len(created.workflows),
        session_count=len(created.sessions),
        connection_count=len(created.connections),
        status=created.status,
    )


@projects_router.get(
    "/{project_id}",
    summary="Get project details",
    description="Get detailed information about a project including its resources.",
)
async def get_project(
    project_id: str,
    repo: ProjectRepository = Depends(get_project_repository),
) -> ProjectDetailResponse:
    """Get a project by ID with all child resources."""
    project = await repo.get(project_id)
    if project is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Project {project_id} not found",
        )

    return _project_to_detail_response(project)


@projects_router.put(
    "/{project_id}",
    summary="Update project",
    description="Update project name or description.",
)
async def update_project(
    project_id: str,
    body: ProjectUpdate,
    repo: ProjectRepository = Depends(get_project_repository),
) -> ProjectResponse:
    """Update a project."""
    # Build update data
    update_data = {}
    if body.name is not None:
        update_data["name"] = body.name
    if body.description is not None:
        update_data["description"] = body.description

    updated = await repo.update(project_id, update_data)
    if updated is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Project {project_id} not found",
        )

    return ProjectResponse(
        id=updated.id,
        name=updated.name,
        description=updated.description,
        organization_id=updated.organization_id,
        owner_id=updated.owner_id,
        owner_name=_extract_owner_name(updated.owner_id),
        created_at=updated.created_at.isoformat().replace("+00:00", "Z") if updated.created_at else "",
        updated_at=updated.updated_at.isoformat().replace("+00:00", "Z") if updated.updated_at else "",
        workflow_count=len(updated.workflows),
        session_count=len(updated.sessions),
        connection_count=len(updated.connections),
        status=updated.status,
    )


@projects_router.delete(
    "/{project_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    summary="Delete project",
    description="Delete a project and optionally its child resources.",
)
async def delete_project(
    project_id: str,
    cascade: bool = False,
    repo: ProjectRepository = Depends(get_project_repository),
) -> None:
    """Delete a project. If cascade=True, also deletes child resources."""
    deleted = await repo.delete(project_id, cascade=cascade)
    if not deleted:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Project {project_id} not found",
        )


# ============================================================================
# Child Resource Listing (GET endpoints for project-scoped resources)
# ============================================================================


class WorkflowListResponse(BaseModel):
    """Response model for listing workflows in a project."""

    workflows: list[WorkflowRef]
    total: int
    project_id: str


class SessionListResponse(BaseModel):
    """Response model for listing sessions in a project."""

    sessions: list[SessionRef]
    total: int
    project_id: str


class ConnectionListResponse(BaseModel):
    """Response model for listing connections in a project."""

    connections: list[ConnectionRef]
    total: int
    project_id: str


@projects_router.get(
    "/{project_id}/workflows",
    summary="List workflows in project",
    description="List all workflows associated with this project.",
)
async def list_project_workflows(
    project_id: str,
    repo: ProjectRepository = Depends(get_project_repository),
) -> WorkflowListResponse:
    """List all workflows in a project."""
    project = await repo.get(project_id)
    if project is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Project {project_id} not found",
        )

    workflows = [
        WorkflowRef(
            id=w.id,
            name=w.name,
            created_at=w.added_at.isoformat().replace("+00:00", "Z") if w.added_at else None,
        )
        for w in project.workflows
    ]
    return WorkflowListResponse(
        workflows=workflows,
        total=len(workflows),
        project_id=project_id,
    )


@projects_router.get(
    "/{project_id}/sessions",
    summary="List sessions in project",
    description="List all sessions associated with this project.",
)
async def list_project_sessions(
    project_id: str,
    repo: ProjectRepository = Depends(get_project_repository),
) -> SessionListResponse:
    """List all sessions in a project."""
    project = await repo.get(project_id)
    if project is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Project {project_id} not found",
        )

    sessions = [
        SessionRef(
            id=s.id,
            name=s.name,
            message_count=s.message_count,
            created_at=s.added_at.isoformat().replace("+00:00", "Z") if s.added_at else None,
        )
        for s in project.sessions
    ]
    return SessionListResponse(
        sessions=sessions,
        total=len(sessions),
        project_id=project_id,
    )


@projects_router.get(
    "/{project_id}/connections",
    summary="List connections in project",
    description="List all connections (MCP servers, vector stores, etc.) in this project.",
)
async def list_project_connections(
    project_id: str,
    repo: ProjectRepository = Depends(get_project_repository),
) -> ConnectionListResponse:
    """List all connections in a project."""
    project = await repo.get(project_id)
    if project is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Project {project_id} not found",
        )

    connections = [
        ConnectionRef(
            id=c.id,
            type=c.connection_type,
            name=c.name,
            status=c.status,
        )
        for c in project.connections
    ]
    return ConnectionListResponse(
        connections=connections,
        total=len(connections),
        project_id=project_id,
    )


# ============================================================================
# Child Resource Management (POST/DELETE for adding/removing resources)
# ============================================================================


@projects_router.post(
    "/{project_id}/workflows",
    summary="Add workflow to project",
    description="Associate an existing workflow with this project.",
)
async def add_workflow_to_project(
    project_id: str,
    workflow_id: str,
    workflow_name: str = "Workflow",
    repo: ProjectRepository = Depends(get_project_repository),
) -> ProjectDetailResponse:
    """Add a workflow to a project."""
    result = await repo.add_workflow(project_id, workflow_id, workflow_name)
    if result is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Project {project_id} not found",
        )
    return _project_to_detail_response(result)


@projects_router.delete(
    "/{project_id}/workflows/{workflow_id}",
    summary="Remove workflow from project",
    description="Disassociate a workflow from this project (does not delete the workflow).",
)
async def remove_workflow_from_project(
    project_id: str,
    workflow_id: str,
    repo: ProjectRepository = Depends(get_project_repository),
) -> ProjectDetailResponse:
    """Remove a workflow from a project."""
    result = await repo.remove_workflow(project_id, workflow_id)
    if result is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Project {project_id} not found",
        )
    return _project_to_detail_response(result)


@projects_router.post(
    "/{project_id}/sessions",
    summary="Add session to project",
    description="Associate an existing session with this project.",
)
async def add_session_to_project(
    project_id: str,
    session_id: str = Query(..., description="Session ID to add"),
    session_name: str = Query("Session", description="Session display name"),
    repo: ProjectRepository = Depends(get_project_repository),
) -> ProjectDetailResponse:
    """Add a session to a project."""
    result = await repo.add_session(project_id, session_id, session_name)
    if result is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Project {project_id} not found",
        )
    return _project_to_detail_response(result)


@projects_router.delete(
    "/{project_id}/sessions/{session_id}",
    summary="Remove session from project",
    description="Disassociate a session from this project (does not delete the session).",
)
async def remove_session_from_project(
    project_id: str,
    session_id: str,
    repo: ProjectRepository = Depends(get_project_repository),
) -> ProjectDetailResponse:
    """Remove a session from a project."""
    result = await repo.remove_session(project_id, session_id)
    if result is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Project {project_id} not found",
        )
    return _project_to_detail_response(result)


@projects_router.post(
    "/{project_id}/connections",
    summary="Add connection to project",
    description="Add a connection (MCP server, vector store, etc.) to this project.",
)
async def add_connection_to_project(
    project_id: str,
    connection_type: str,
    connection_id: str,
    connection_name: str = "Connection",
    repo: ProjectRepository = Depends(get_project_repository),
) -> ProjectDetailResponse:
    """Add a connection to a project."""
    if connection_type not in ["mcp_server", "vector_store", "api_key"]:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Invalid connection type: {connection_type}",
        )

    connection = ProjectConnection(
        id=connection_id,
        connection_type=connection_type,
        name=connection_name,
        status="active",
    )
    result = await repo.add_connection(project_id, connection)
    if result is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Project {project_id} not found",
        )
    return _project_to_detail_response(result)


# ============================================================================
# Member Management
# ============================================================================


class MemberListResponse(BaseModel):
    """Response model for listing members in a project."""

    members: list[ProjectMember]
    total: int
    project_id: str


@projects_router.get(
    "/{project_id}/members",
    summary="List project members",
    description="List all members of this project with their roles.",
)
async def list_project_members(
    project_id: str,
    repo: ProjectRepository = Depends(get_project_repository),
) -> MemberListResponse:
    """List all members of a project."""
    project = await repo.get(project_id)
    if project is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Project {project_id} not found",
        )

    members = [
        ProjectMember(
            user_id=m.user_id,
            role=m.role,
            added_at=m.added_at.isoformat().replace("+00:00", "Z") if m.added_at else "",
        )
        for m in project.members
    ]
    return MemberListResponse(
        members=members,
        total=len(members),
        project_id=project_id,
    )


@projects_router.post(
    "/{project_id}/members",
    summary="Add member to project",
    description="Add a user as a member of this project with a specific role.",
)
async def add_member_to_project(
    project_id: str,
    body: AddMemberRequest,
    repo: ProjectRepository = Depends(get_project_repository),
) -> ProjectDetailResponse:
    """Add a member to a project."""
    if body.role not in ["editor", "viewer", "executor"]:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Invalid role: {body.role}. Must be one of: editor, viewer, executor",
        )

    result = await repo.add_member(project_id, body.user_id, body.role)
    if result is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Project {project_id} not found",
        )
    return _project_to_detail_response(result)


@projects_router.delete(
    "/{project_id}/members/{user_id}",
    summary="Remove member from project",
    description="Remove a user from this project.",
)
async def remove_member_from_project(
    project_id: str,
    user_id: str,
    repo: ProjectRepository = Depends(get_project_repository),
) -> ProjectDetailResponse:
    """Remove a member from a project."""
    result = await repo.remove_member(project_id, user_id)
    if result is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Project {project_id} not found",
        )
    return _project_to_detail_response(result)


# ============================================================================
# Project-Scoped Observability (filtered view of global data)
# ============================================================================


class ProjectTraceListItem(BaseModel):
    """Trace item scoped to a project."""

    trace_id: str
    name: str
    session_id: str | None = None
    workflow_id: str | None = None
    start_time: str | None = None
    duration_ms: float | None = None
    span_count: int | None = None


class ProjectTracesResponse(BaseModel):
    """Response model for project traces."""

    traces: list[ProjectTraceListItem]
    total: int
    project_id: str


class ProjectMetricsResponse(BaseModel):
    """Response model for project-scoped metrics."""

    requests_total: int
    errors_total: int
    latency_p50: float | None = None
    latency_p95: float | None = None
    latency_p99: float | None = None
    project_id: str


class ProjectLogEntry(BaseModel):
    """Log entry scoped to a project."""

    timestamp: str
    level: str
    message: str
    session_id: str | None = None
    workflow_id: str | None = None


class ProjectLogsResponse(BaseModel):
    """Response model for project logs."""

    logs: list[ProjectLogEntry]
    total: int
    project_id: str


class ProjectAlert(BaseModel):
    """Alert scoped to a project."""

    alert_id: str
    name: str
    severity: str  # "info" | "warning" | "error" | "critical"
    status: str  # "firing" | "resolved"
    message: str
    created_at: str
    resource_type: str | None = None  # "session" | "workflow"
    resource_id: str | None = None


class ProjectAlertsResponse(BaseModel):
    """Response model for project alerts."""

    alerts: list[ProjectAlert]
    total: int
    project_id: str


@projects_router.get(
    "/{project_id}/observability/traces",
    summary="Get project traces",
    description="Get traces filtered to sessions and workflows in this project.",
)
async def get_project_traces(
    project_id: str,
    limit: int = 20,
    repo: ProjectRepository = Depends(get_project_repository),
) -> ProjectTracesResponse:
    """Get traces scoped to a project.

    Filters global trace data to show only traces from:
    - Sessions belonging to this project
    - Workflows belonging to this project
    """
    project = await repo.get(project_id)
    if project is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Project {project_id} not found",
        )

    # Get session and workflow IDs for filtering
    _session_ids = {s.id for s in project.sessions}
    _workflow_ids = {w.id for w in project.workflows}

    # In production, this would query the observability backend
    # and filter traces by session_id/workflow_id
    # For now, return empty (no traces yet for new project)
    traces: list[ProjectTraceListItem] = []

    return ProjectTracesResponse(
        traces=traces,
        total=len(traces),
        project_id=project_id,
    )


@projects_router.get(
    "/{project_id}/observability/metrics",
    summary="Get project metrics",
    description="Get metrics aggregated for sessions and workflows in this project.",
)
async def get_project_metrics(
    project_id: str,
    start_date: str | None = None,
    end_date: str | None = None,
    repo: ProjectRepository = Depends(get_project_repository),
) -> ProjectMetricsResponse:
    """Get metrics scoped to a project.

    Aggregates metrics from:
    - Sessions belonging to this project
    - Workflows belonging to this project
    """
    project = await repo.get(project_id)
    if project is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Project {project_id} not found",
        )

    # In production, this would query the metrics backend
    # and aggregate by session_id/workflow_id
    return ProjectMetricsResponse(
        requests_total=0,
        errors_total=0,
        latency_p50=None,
        latency_p95=None,
        latency_p99=None,
        project_id=project_id,
    )


@projects_router.get(
    "/{project_id}/observability/logs",
    summary="Get project logs",
    description="Get logs filtered to sessions and workflows in this project.",
)
async def get_project_logs(
    project_id: str,
    limit: int = 100,
    level: str | None = None,
    repo: ProjectRepository = Depends(get_project_repository),
) -> ProjectLogsResponse:
    """Get logs scoped to a project.

    Filters global log data to show only logs from:
    - Sessions belonging to this project
    - Workflows belonging to this project
    """
    project = await repo.get(project_id)
    if project is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Project {project_id} not found",
        )

    # In production, this would query Loki/log backend
    # and filter by session_id/workflow_id labels
    logs: list[ProjectLogEntry] = []

    return ProjectLogsResponse(
        logs=logs,
        total=len(logs),
        project_id=project_id,
    )


@projects_router.get(
    "/{project_id}/observability/alerts",
    summary="Get project alerts",
    description="Get alerts for sessions and workflows in this project.",
)
async def get_project_alerts(
    project_id: str,
    status_filter: str | None = None,  # "firing" | "resolved" | None (all)
    repo: ProjectRepository = Depends(get_project_repository),
) -> ProjectAlertsResponse:
    """Get alerts scoped to a project.

    Shows alerts triggered by:
    - Sessions belonging to this project
    - Workflows belonging to this project
    """
    project = await repo.get(project_id)
    if project is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Project {project_id} not found",
        )

    # In production, this would query the alerting backend
    # and filter by session_id/workflow_id
    alerts: list[ProjectAlert] = []

    return ProjectAlertsResponse(
        alerts=alerts,
        total=len(alerts),
        project_id=project_id,
    )


# ============================================================================
# Project-Scoped Cost (filtered view of global cost data)
# ============================================================================


class ProjectCostSummaryResponse(BaseModel):
    """Response model for project cost summary."""

    total_cost: float
    prompt_tokens: int
    completion_tokens: int
    total_tokens: int | None = None
    period_start: str | None = None
    period_end: str | None = None
    project_id: str


class ProjectModelCost(BaseModel):
    """Per-model cost within a project."""

    model: str
    cost: float
    requests: int
    prompt_tokens: int | None = None
    completion_tokens: int | None = None


class ProjectCostByModelResponse(BaseModel):
    """Response model for project cost by model."""

    models: list[ProjectModelCost]
    total_cost: float
    project_id: str


class ProjectDailyCost(BaseModel):
    """Daily cost for a project."""

    date: str
    cost: float
    requests: int | None = None


class ProjectCostHistoryResponse(BaseModel):
    """Response model for project cost history."""

    history: list[ProjectDailyCost]
    total_cost: float
    project_id: str


@projects_router.get(
    "/{project_id}/cost/summary",
    summary="Get project cost summary",
    description="Get cost summary aggregated for sessions in this project.",
)
async def get_project_cost_summary(
    project_id: str,
    start_date: str | None = None,
    end_date: str | None = None,
    repo: ProjectRepository = Depends(get_project_repository),
) -> ProjectCostSummaryResponse:
    """Get cost summary scoped to a project.

    Aggregates costs from:
    - Sessions belonging to this project
    - Workflow executions belonging to this project
    """
    project = await repo.get(project_id)
    if project is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Project {project_id} not found",
        )

    # In production, this would query the cost tracking backend
    # and aggregate by session_id
    return ProjectCostSummaryResponse(
        total_cost=0.0,
        prompt_tokens=0,
        completion_tokens=0,
        total_tokens=0,
        period_start=start_date,
        period_end=end_date,
        project_id=project_id,
    )


@projects_router.get(
    "/{project_id}/cost/by-model",
    summary="Get project cost by model",
    description="Get cost breakdown by model for sessions in this project.",
)
async def get_project_cost_by_model(
    project_id: str,
    start_date: str | None = None,
    end_date: str | None = None,
    repo: ProjectRepository = Depends(get_project_repository),
) -> ProjectCostByModelResponse:
    """Get cost breakdown by model scoped to a project."""
    project = await repo.get(project_id)
    if project is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Project {project_id} not found",
        )

    # In production, this would query the cost tracking backend
    # and group by model for project's sessions
    models: list[ProjectModelCost] = []

    return ProjectCostByModelResponse(
        models=models,
        total_cost=0.0,
        project_id=project_id,
    )


@projects_router.get(
    "/{project_id}/cost/history",
    summary="Get project cost history",
    description="Get cost history over time for sessions in this project.",
)
async def get_project_cost_history(
    project_id: str,
    start_date: str | None = None,
    end_date: str | None = None,
    repo: ProjectRepository = Depends(get_project_repository),
) -> ProjectCostHistoryResponse:
    """Get cost history scoped to a project."""
    project = await repo.get(project_id)
    if project is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Project {project_id} not found",
        )

    # In production, this would query the cost tracking backend
    # and aggregate by date for project's sessions
    history: list[ProjectDailyCost] = []

    return ProjectCostHistoryResponse(
        history=history,
        total_cost=0.0,
        project_id=project_id,
    )
