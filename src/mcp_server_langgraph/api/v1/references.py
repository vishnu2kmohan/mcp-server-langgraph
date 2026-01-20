"""
Reference Resolution API with OpenFGA Authorization.

Provides batch resolution of [[type:qualifier:id]] markdown references.
Each reference type is authorized according to its resource type:
- Tools: connection:viewer via connection_id (mapped from server_name)
- Skills: skill:default:viewer (global)
- Artifacts: artifact:viewer (ownership check)
- Memory: session:viewer (notes inherit from session)
- Plans: session:viewer (plans inherit from session)
"""

from typing import Annotated, Any, Literal

from fastapi import APIRouter, Depends, HTTPException, Request, status
from pydantic import BaseModel, Field

from mcp_server_langgraph.auth.dependencies import (
    get_auth_middleware_from_request,
    require_reference_viewer_global,
)
from mcp_server_langgraph.core.dependencies import get_connection_repository
from mcp_server_langgraph.core.feature_flags import feature_flags
from mcp_server_langgraph.observability.telemetry import logger
from mcp_server_langgraph.repositories.connections import ConnectionRepository

references_router = APIRouter(prefix="/references", tags=["references"])

# Type alias for the authenticated user from OpenFGA dependency
CurrentUser = Annotated[dict[str, Any], Depends(require_reference_viewer_global)]


class ReferenceRequest(BaseModel):
    """A single reference to resolve."""

    type: Literal["tool", "skill", "artifact", "memory", "plan"] = Field(
        description="Reference type (tool, skill, artifact, memory, or plan)"
    )
    qualifier: str = Field(description="Server name for tools, or identifier for skills/artifacts/memory/plans")
    id: str = Field(description="Tool name, skill name, artifact ID, note ID, or plan ID")


class ResolvedReference(BaseModel):
    """A resolved reference with display information."""

    type: str
    qualifier: str
    id: str
    display_name: str
    description: str | None = None
    status: Literal["valid", "not_found", "unauthorized"]
    metadata: dict[str, Any] = Field(default_factory=dict)


class ResolveRequest(BaseModel):
    """Batch resolution request."""

    references: list[ReferenceRequest]


class ResolveResponse(BaseModel):
    """Batch resolution response."""

    resolved: list[ResolvedReference]


@references_router.post("/resolve", response_model=ResolveResponse)
async def resolve_references(
    body: ResolveRequest,
    request: Request,
    user: CurrentUser,
    conn_repo: Annotated[ConnectionRepository, Depends(get_connection_repository)],
) -> ResolveResponse:
    """
    Batch resolve references with OpenFGA authorization.

    Each reference is checked against OpenFGA for the current user:
    - Tools: Check connection:viewer for the tool's parent connection
    - Skills: Check skill:default:viewer (global access)
    - Artifacts: Check artifact:viewer (ownership check)
    - Memory: Check session:viewer for the note's parent session
    - Plans: Check session:viewer for the plan's parent session

    Returns resolved references with display names and descriptions,
    or status indicating not_found or unauthorized.
    """
    if not feature_flags.enable_markdown_references:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Markdown references feature not enabled",
        )

    auth = get_auth_middleware_from_request(request)
    resolved: list[ResolvedReference] = []

    for ref in body.references:
        resolved_ref = await _resolve_single(ref, user, auth, conn_repo)
        resolved.append(resolved_ref)

    return ResolveResponse(resolved=resolved)


async def _resolve_single(
    ref: ReferenceRequest,
    user: dict[str, Any],
    auth: Any,
    conn_repo: ConnectionRepository,
) -> ResolvedReference:
    """Resolve a single reference with OpenFGA authorization checks."""
    user_id = user.get("sub") or user.get("user_id") or ""
    if not user_id.startswith("user:"):
        user_id = f"user:{user_id}"

    # Extract raw user ID for database queries (without user: prefix)
    raw_user_id = user_id.removeprefix("user:")

    if ref.type == "tool":
        return await _resolve_tool(ref, user_id, raw_user_id, auth, conn_repo)
    elif ref.type == "skill":
        return await _resolve_skill(ref, user_id, auth)
    elif ref.type == "artifact":
        return await _resolve_artifact(ref, user_id, auth)
    elif ref.type == "memory":
        return await _resolve_memory(ref, user_id, auth)
    else:
        # ref.type == "plan" (exhaustive per Literal type)
        return await _resolve_plan(ref, user_id, auth)


async def _resolve_tool(
    ref: ReferenceRequest,
    user_id: str,
    raw_user_id: str,
    auth: Any,
    conn_repo: ConnectionRepository,
) -> ResolvedReference:
    """Resolve a tool reference with connection authorization."""
    # Map server_name -> connection_id for OpenFGA auth check
    connection = await conn_repo.get_by_server_name(ref.qualifier, raw_user_id)

    if connection is None:
        logger.debug(
            "Tool reference not found",
            extra={
                "server_name": ref.qualifier,
                "tool_name": ref.id,
                "user_id": user_id,
            },
        )
        return ResolvedReference(
            type=ref.type,
            qualifier=ref.qualifier,
            id=ref.id,
            display_name=ref.id,
            status="not_found",
        )

    # Check connection:viewer using connection.id (UUID), NOT server_name
    if auth is not None:
        authorized = await auth.authorize(
            user_id=user_id,
            relation="viewer",
            resource=f"connection:{connection.id}",
        )
        if not authorized:
            logger.debug(
                "Tool reference unauthorized",
                extra={
                    "connection_id": connection.id,
                    "tool_name": ref.id,
                    "user_id": user_id,
                },
            )
            return ResolvedReference(
                type=ref.type,
                qualifier=ref.qualifier,
                id=ref.id,
                display_name=ref.id,
                status="unauthorized",
            )

    # Tool is accessible - build display information
    # Use server_name and tool_name for display
    display_name = f"{ref.qualifier}:{ref.id}"

    return ResolvedReference(
        type=ref.type,
        qualifier=ref.qualifier,
        id=ref.id,
        display_name=display_name,
        description=f"Tool from {connection.name or connection.server_name} connection",
        status="valid",
        metadata={
            "connectionId": connection.id,
            "connectionName": connection.name,
            "serverName": connection.server_name,
        },
    )


async def _resolve_skill(
    ref: ReferenceRequest,
    user_id: str,
    auth: Any,
) -> ResolvedReference:
    """Resolve a skill reference with global skill authorization.

    Supports version-pinned references: [[skill:name@version]]
    The version is extracted and included in metadata as requestedVersion.
    """
    # Skills use global skill:default:viewer check
    if auth is not None:
        authorized = await auth.authorize(
            user_id=user_id,
            relation="viewer",
            resource="skill:default",
        )
        if not authorized:
            return ResolvedReference(
                type=ref.type,
                qualifier=ref.qualifier,
                id=ref.id,
                display_name=ref.id,
                status="unauthorized",
            )

    # Parse skill name and version from id (e.g., "code-review@1.2.0")
    skill_id = ref.id
    skill_name = skill_id
    requested_version: str | None = None

    if "@" in skill_id:
        parts = skill_id.split("@", 1)
        skill_name = parts[0]
        requested_version = parts[1] if len(parts) > 1 else None

    # Discover skill from registry
    try:
        from mcp_server_langgraph.skills import SkillDiscovery, SkillInstaller

        discovery = SkillDiscovery()
        discovery.load_from_directory(SkillInstaller.DEFAULT_INSTALL_PATH)
        skill = discovery.get_skill(skill_name)

        if skill is None:
            return ResolvedReference(
                type=ref.type,
                qualifier=ref.qualifier,
                id=ref.id,
                display_name=skill_name,
                status="not_found",
            )

        # Build metadata with version info
        metadata: dict[str, Any] = {
            "tags": skill.tags,
            "version": skill.version,
        }
        if requested_version:
            metadata["requestedVersion"] = requested_version

        return ResolvedReference(
            type=ref.type,
            qualifier=ref.qualifier,
            id=ref.id,
            display_name=skill.name,
            description=skill.description,
            status="valid",
            metadata=metadata,
        )
    except Exception as e:
        logger.warning("Failed to resolve skill reference", extra={"error": str(e)})
        return ResolvedReference(
            type=ref.type,
            qualifier=ref.qualifier,
            id=ref.id,
            display_name=skill_name,
            status="not_found",
        )


async def _resolve_artifact(
    ref: ReferenceRequest,
    user_id: str,
    auth: Any,
) -> ResolvedReference:
    """Resolve an artifact reference with ownership authorization."""
    # Check artifact:viewer
    if auth is not None:
        authorized = await auth.authorize(
            user_id=user_id,
            relation="viewer",
            resource=f"artifact:{ref.id}",
        )
        if not authorized:
            return ResolvedReference(
                type=ref.type,
                qualifier=ref.qualifier,
                id=ref.id,
                display_name=ref.id,
                status="unauthorized",
            )

    # Artifact resolution via artifacts service
    try:
        from mcp_server_langgraph.api.v1.artifacts import get_artifacts_service

        # Extract raw user_id without user: prefix for service call
        raw_user_id = user_id.removeprefix("user:")
        service = get_artifacts_service()
        artifact = await service.get_artifact(ref.id, raw_user_id)
        if artifact is not None:
            return ResolvedReference(
                type=ref.type,
                qualifier=ref.qualifier,
                id=ref.id,
                display_name=artifact.get("name") or ref.id,
                description=artifact.get("description"),
                status="valid",
                metadata={
                    "contentType": artifact.get("content_type"),
                },
            )
    except Exception as e:
        logger.debug("Artifact lookup failed, using fallback", extra={"error": str(e)})

    # Fallback: return not_found if we couldn't verify
    return ResolvedReference(
        type=ref.type,
        qualifier=ref.qualifier,
        id=ref.id,
        display_name=ref.id,
        status="not_found",
    )


async def _resolve_memory(
    ref: ReferenceRequest,
    user_id: str,
    auth: Any,
) -> ResolvedReference:
    """Resolve a memory note reference with session authorization."""
    try:
        from mcp_server_langgraph.api.v1.memory import get_notes_manager

        manager = get_notes_manager()
        note = manager.get_note(ref.id)

        if note is None:
            return ResolvedReference(
                type=ref.type,
                qualifier=ref.qualifier,
                id=ref.id,
                display_name=ref.id,
                status="not_found",
            )

        # Check session:viewer if note has session_id
        if auth is not None and note.session_id:
            authorized = await auth.authorize(
                user_id=user_id,
                relation="viewer",
                resource=f"session:{note.session_id}",
            )
            if not authorized:
                return ResolvedReference(
                    type=ref.type,
                    qualifier=ref.qualifier,
                    id=ref.id,
                    display_name=ref.id,
                    status="unauthorized",
                )

        return ResolvedReference(
            type=ref.type,
            qualifier=ref.qualifier,
            id=ref.id,
            display_name=note.title or ref.id,
            description=note.content[:200] if note.content else None,
            status="valid",
            metadata={
                "category": note.category,
                "tags": note.tags,
                "sessionId": note.session_id,
                "createdAt": note.created_at.isoformat() if note.created_at else None,
            },
        )
    except Exception as e:
        logger.warning("Failed to resolve memory reference", extra={"error": str(e)})
        return ResolvedReference(
            type=ref.type,
            qualifier=ref.qualifier,
            id=ref.id,
            display_name=ref.id,
            status="not_found",
        )


async def _resolve_plan(
    ref: ReferenceRequest,
    user_id: str,
    auth: Any,
) -> ResolvedReference:
    """Resolve an execution plan reference with session authorization."""
    try:
        from mcp_server_langgraph.api.v1.execution_plans import get_plan_repo

        repo = get_plan_repo()
        plan = await repo.get(ref.id)

        if plan is None:
            return ResolvedReference(
                type=ref.type,
                qualifier=ref.qualifier,
                id=ref.id,
                display_name=ref.id,
                status="not_found",
            )

        # Check session:viewer for the plan's session
        if auth is not None:
            authorized = await auth.authorize(
                user_id=user_id,
                relation="viewer",
                resource=f"session:{plan.session_id}",
            )
            if not authorized:
                return ResolvedReference(
                    type=ref.type,
                    qualifier=ref.qualifier,
                    id=ref.id,
                    display_name=ref.id,
                    status="unauthorized",
                )

        return ResolvedReference(
            type=ref.type,
            qualifier=ref.qualifier,
            id=ref.id,
            display_name=f"Plan: {plan.task_type}",
            description=f"{plan.complexity} complexity, {plan.risk_level} risk",
            status="valid",
            metadata={
                "status": plan.status,
                "sessionId": plan.session_id,
                "toolsNeeded": plan.tools_needed,
            },
        )
    except Exception as e:
        logger.warning("Failed to resolve plan reference", extra={"error": str(e)})
        return ResolvedReference(
            type=ref.type,
            qualifier=ref.qualifier,
            id=ref.id,
            display_name=ref.id,
            status="not_found",
        )
