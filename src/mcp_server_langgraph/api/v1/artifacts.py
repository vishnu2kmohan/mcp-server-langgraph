"""
Artifacts Router

Provides CRUD operations for canvas artifact management under /api/v1/artifacts/*.

This implements the API contract defined in the frontend MSW handlers
(studio/frontend/src/mocks/handlers/canvasHandlers.ts) for the Hybrid Canvas feature.

Usage:
    GET /api/v1/artifacts - List artifacts (with pagination, session filtering)
    GET /api/v1/artifacts/{id} - Get a specific artifact
    POST /api/v1/artifacts - Create a new artifact
    PUT /api/v1/artifacts/{id} - Update an artifact
    DELETE /api/v1/artifacts/{id} - Delete an artifact
    GET /api/v1/artifacts/{id}/versions - Get version history
    POST /api/v1/artifacts/{id}/fork - Fork an artifact
"""

import logging
from abc import ABC, abstractmethod
from datetime import UTC, datetime
from enum import Enum
from typing import Annotated, Any, Literal
from uuid import uuid4

from fastapi import APIRouter, Depends, HTTPException, Query, Response, status
from pydantic import BaseModel, Field

from mcp_server_langgraph.api.deps import get_audit_service
from mcp_server_langgraph.audit.models import (
    AuditActor,
    AuditContext,
    AuditEventCategory,
    AuditEventType,
    UnifiedAuditEvent,
)
from mcp_server_langgraph.audit.service import UnifiedAuditService
from mcp_server_langgraph.auth.middleware import get_current_user
from mcp_server_langgraph.core.config import settings


logger = logging.getLogger(__name__)


# Enums for type-safe values


class ContentType(str, Enum):
    """Artifact content type enum."""

    code = "code"
    markdown = "markdown"
    json = "json"
    jsx = "jsx"
    mermaid = "mermaid"
    html = "html"


class EditedBy(str, Enum):
    """Who edited the artifact."""

    user = "user"
    ai_suggestion = "ai-suggestion"
    ai_generation = "ai-generation"


# Type alias for authenticated user dependency
CurrentUser = Annotated[dict[str, Any], Depends(get_current_user)]

# Type alias for optional audit service dependency
AuditService = Annotated[UnifiedAuditService | None, Depends(get_audit_service)]


def _get_user_id(current_user: dict[str, Any]) -> str:
    """Extract user ID from the current user context."""
    user_id: str | None = (
        current_user.get("sub")
        or current_user.get("user_id")
        or current_user.get("preferred_username")
    )

    if not user_id:
        logger.warning(
            "No user identifier found in auth context",
            extra={"keys": list(current_user.keys())},
        )
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="User identifier not found in authentication context",
        )

    return user_id


artifacts_router = APIRouter(tags=["artifacts"])


# Request/Response Models


class EditMetadata(BaseModel):
    """Metadata about artifact editing."""

    edited_by: Literal["user", "ai-suggestion", "ai-generation"] = Field(
        default="user", description="Who edited the artifact"
    )
    language: str | None = Field(default=None, description="Programming language")
    ai_confidence: float | None = Field(
        default=None, ge=0, le=1, description="AI confidence score"
    )


class ArtifactCreateRequest(BaseModel):
    """Request body for creating an artifact."""

    type: str = Field(description="Artifact type", max_length=50)
    content: str = Field(description="Artifact content")
    content_type: ContentType = Field(description="Content type")
    session_id: str = Field(description="Associated session ID")
    title: str | None = Field(default="Untitled Artifact", max_length=255)
    edit_metadata: EditMetadata | None = Field(default=None)


class ArtifactUpdateRequest(BaseModel):
    """Request body for updating an artifact."""

    content: str | None = Field(default=None, description="New content")
    title: str | None = Field(default=None, max_length=255)
    edit_metadata: EditMetadata | None = Field(default=None)


class ArtifactForkRequest(BaseModel):
    """Request body for forking an artifact."""

    new_name: str | None = Field(default=None, max_length=255)


class ArtifactResponse(BaseModel):
    """Full artifact response model."""

    id: str
    type: str
    session_id: str
    version: int
    content: str
    content_type: str
    created_at: str
    updated_at: str
    title: str
    user_id: str
    edit_metadata: EditMetadata | None = None


class ArtifactCreateResponse(BaseModel):
    """Response for artifact creation."""

    id: str
    version: int
    created_at: str


class ArtifactUpdateResponse(BaseModel):
    """Response for artifact update."""

    id: str
    version: int
    updated_at: str


class ArtifactForkResponse(BaseModel):
    """Response for artifact fork."""

    id: str
    parent_id: str
    version: int


class SemanticSearchRequest(BaseModel):
    """Request body for semantic search."""

    query: str = Field(description="Search query", min_length=1)
    limit: int = Field(default=10, ge=1, le=100, description="Max results")


class SemanticSearchResult(BaseModel):
    """Individual search result."""

    artifact_id: str
    score: float
    title: str | None = None


class SemanticSearchResponse(BaseModel):
    """Response for semantic search."""

    results: list[SemanticSearchResult]


class FindSimilarResponse(BaseModel):
    """Response for find similar artifacts."""

    results: list[SemanticSearchResult]


class ArtifactVersionResponse(BaseModel):
    """Artifact version response model."""

    id: str
    artifact_id: str
    version: int
    content: str
    content_type: str
    created_by: str
    created_at: str
    parent_version: int | None = None
    metadata: dict[str, Any] | None = None


class ListArtifactsResponse(BaseModel):
    """Paginated list response for artifacts."""

    items: list[ArtifactResponse]
    cursor: str | None = None
    hasMore: bool = False


# Service Protocol


class ArtifactsServiceProtocol(ABC):
    """Protocol for artifacts service dependency."""

    @abstractmethod
    async def list_artifacts(
        self,
        user_id: str,
        session_id: str | None = None,
        limit: int = 20,
        cursor: str | None = None,
    ) -> tuple[list[dict[str, Any]], str | None, bool]:
        """List artifacts with pagination."""
        ...

    @abstractmethod
    async def get_artifact(
        self, artifact_id: str, user_id: str
    ) -> dict[str, Any] | None:
        """Get a specific artifact."""
        ...

    @abstractmethod
    async def create_artifact(
        self, data: dict[str, Any], user_id: str
    ) -> dict[str, Any]:
        """Create a new artifact."""
        ...

    @abstractmethod
    async def update_artifact(
        self, artifact_id: str, data: dict[str, Any], user_id: str
    ) -> dict[str, Any] | None:
        """Update an artifact."""
        ...

    @abstractmethod
    async def delete_artifact(self, artifact_id: str, user_id: str) -> bool:
        """Delete an artifact."""
        ...

    @abstractmethod
    async def get_artifact_versions(
        self, artifact_id: str, user_id: str
    ) -> list[dict[str, Any]] | None:
        """Get version history for an artifact."""
        ...

    @abstractmethod
    async def fork_artifact(
        self, artifact_id: str, new_name: str | None, user_id: str
    ) -> dict[str, Any] | None:
        """Fork an artifact."""
        ...

    @abstractmethod
    async def semantic_search(
        self, query: str, user_id: str, limit: int = 10
    ) -> list[dict[str, Any]]:
        """Search artifacts by semantic similarity.

        Args:
            query: Search query text.
            user_id: User ID for access control.
            limit: Maximum number of results.

        Returns:
            List of matching artifacts with similarity scores.
        """
        ...

    @abstractmethod
    async def find_similar(
        self, artifact_id: str, user_id: str, limit: int = 5
    ) -> list[dict[str, Any]]:
        """Find artifacts similar to a given artifact.

        Args:
            artifact_id: Source artifact ID.
            user_id: User ID for access control.
            limit: Maximum number of results.

        Returns:
            List of similar artifacts with similarity scores.
        """
        ...


# In-memory service implementation for MVP


class InMemoryArtifactsService(ArtifactsServiceProtocol):
    """In-memory artifacts service for development/testing."""

    def __init__(self) -> None:
        self._artifacts: dict[str, dict[str, Any]] = {}
        self._versions: dict[str, list[dict[str, Any]]] = {}

    async def list_artifacts(
        self,
        user_id: str,
        session_id: str | None = None,
        limit: int = 20,
        cursor: str | None = None,
    ) -> tuple[list[dict[str, Any]], str | None, bool]:
        """List artifacts with pagination."""
        items = list(self._artifacts.values())

        # Filter by user
        items = [a for a in items if a.get("user_id") == user_id]

        # Filter by session if provided
        if session_id:
            items = [a for a in items if a.get("session_id") == session_id]

        # Sort by updated_at descending
        items.sort(key=lambda x: x.get("updated_at", ""), reverse=True)

        # Pagination
        start_idx = 0
        if cursor:
            try:
                start_idx = int(cursor)
            except ValueError:
                start_idx = 0

        paginated = items[start_idx : start_idx + limit]
        has_more = start_idx + limit < len(items)
        next_cursor = str(start_idx + limit) if has_more else None

        return paginated, next_cursor, has_more

    async def get_artifact(
        self, artifact_id: str, user_id: str
    ) -> dict[str, Any] | None:
        """Get a specific artifact."""
        artifact = self._artifacts.get(artifact_id)
        if artifact and artifact.get("user_id") == user_id:
            return artifact
        return None

    async def create_artifact(
        self, data: dict[str, Any], user_id: str
    ) -> dict[str, Any]:
        """Create a new artifact."""
        artifact_id = f"art-{uuid4().hex[:8]}"
        now = datetime.now(UTC).isoformat()

        artifact = {
            "id": artifact_id,
            "type": data.get("type", "code"),
            "session_id": data["session_id"],
            "version": 1,
            "content": data["content"],
            "content_type": data["content_type"],
            "created_at": now,
            "updated_at": now,
            "title": data.get("title", "Untitled Artifact"),
            "user_id": user_id,
            "edit_metadata": data.get("edit_metadata"),
        }

        self._artifacts[artifact_id] = artifact

        # Create initial version
        version = {
            "id": f"ver-{uuid4().hex[:8]}",
            "artifact_id": artifact_id,
            "version": 1,
            "content": data["content"],
            "content_type": data["content_type"],
            "created_by": user_id,
            "created_at": now,
            "metadata": {"edit_type": "user"},
        }
        self._versions[artifact_id] = [version]

        return {
            "id": artifact_id,
            "version": 1,
            "created_at": now,
        }

    async def update_artifact(
        self, artifact_id: str, data: dict[str, Any], user_id: str
    ) -> dict[str, Any] | None:
        """Update an artifact."""
        artifact = self._artifacts.get(artifact_id)
        if not artifact or artifact.get("user_id") != user_id:
            return None

        now = datetime.now(UTC).isoformat()
        new_version = artifact["version"] + 1

        # Update artifact
        if data.get("content"):
            artifact["content"] = data["content"]
        if data.get("title"):
            artifact["title"] = data["title"]
        if data.get("edit_metadata"):
            artifact["edit_metadata"] = data["edit_metadata"]

        artifact["version"] = new_version
        artifact["updated_at"] = now

        # Add version entry
        version = {
            "id": f"ver-{uuid4().hex[:8]}",
            "artifact_id": artifact_id,
            "version": new_version,
            "content": artifact["content"],
            "content_type": artifact["content_type"],
            "created_by": user_id,
            "created_at": now,
            "parent_version": new_version - 1,
            "metadata": {"edit_type": "user"},
        }
        if artifact_id not in self._versions:
            self._versions[artifact_id] = []
        self._versions[artifact_id].append(version)

        # Version cleanup: remove old versions if exceeding max limit
        max_versions = settings.artifacts_max_versions
        versions_list = self._versions[artifact_id]
        if len(versions_list) > max_versions:
            # Keep most recent versions, sorted by version number
            versions_list.sort(key=lambda v: v.get("version", 0), reverse=True)
            removed_count = len(versions_list) - max_versions
            self._versions[artifact_id] = versions_list[:max_versions]
            logger.info(
                "Version cleanup performed",
                extra={
                    "artifact_id": artifact_id,
                    "removed_versions": removed_count,
                    "remaining_versions": max_versions,
                },
            )

        return {
            "id": artifact_id,
            "version": new_version,
            "updated_at": now,
        }

    async def delete_artifact(self, artifact_id: str, user_id: str) -> bool:
        """Delete an artifact."""
        artifact = self._artifacts.get(artifact_id)
        if not artifact or artifact.get("user_id") != user_id:
            return False

        del self._artifacts[artifact_id]
        if artifact_id in self._versions:
            del self._versions[artifact_id]

        return True

    async def get_artifact_versions(
        self, artifact_id: str, user_id: str
    ) -> list[dict[str, Any]] | None:
        """Get version history for an artifact."""
        artifact = self._artifacts.get(artifact_id)
        if not artifact or artifact.get("user_id") != user_id:
            return None

        return self._versions.get(artifact_id, [])

    async def fork_artifact(
        self, artifact_id: str, new_name: str | None, user_id: str
    ) -> dict[str, Any] | None:
        """Fork an artifact."""
        artifact = self._artifacts.get(artifact_id)
        if not artifact:
            return None

        # Create forked artifact
        forked_id = f"art-{uuid4().hex[:8]}"
        now = datetime.now(UTC).isoformat()

        forked = {
            **artifact,
            "id": forked_id,
            "version": 1,
            "title": new_name or f"Fork of {artifact['title']}",
            "user_id": user_id,
            "created_at": now,
            "updated_at": now,
        }

        self._artifacts[forked_id] = forked

        # Create initial version for fork
        version = {
            "id": f"ver-{uuid4().hex[:8]}",
            "artifact_id": forked_id,
            "version": 1,
            "content": artifact["content"],
            "content_type": artifact["content_type"],
            "created_by": user_id,
            "created_at": now,
            "metadata": {"edit_type": "fork", "forked_from": artifact_id},
        }
        self._versions[forked_id] = [version]

        return {
            "id": forked_id,
            "parent_id": artifact_id,
            "version": 1,
        }

    async def semantic_search(
        self,
        query: str,
        user_id: str,
        limit: int = 10,
    ) -> list[dict[str, Any]]:
        """Semantic search (mock implementation returns empty)."""
        # In-memory service doesn't support semantic search
        # Returns empty list - real implementation uses Qdrant
        return []

    async def find_similar(
        self,
        artifact_id: str,
        user_id: str,
        limit: int = 5,
    ) -> list[dict[str, Any]]:
        """Find similar artifacts (mock implementation returns empty)."""
        # In-memory service doesn't support similarity search
        # Returns empty list - real implementation uses Qdrant
        return []


# Service dependency


_artifacts_service: ArtifactsServiceProtocol | None = None


def get_artifacts_service() -> ArtifactsServiceProtocol:
    """Get the artifacts service instance."""
    global _artifacts_service
    if _artifacts_service is None:
        # Default to in-memory service
        _artifacts_service = InMemoryArtifactsService()
    return _artifacts_service


def set_artifacts_service(service: ArtifactsServiceProtocol | None) -> None:
    """Set the artifacts service instance (for app initialization or testing)."""
    global _artifacts_service
    _artifacts_service = service


# Audit Logging Helper


async def log_artifact_audit_event(
    audit_service: UnifiedAuditService | None,
    event_type: AuditEventType,
    artifact_id: str,
    user_id: str,
    username: str | None,
    action: str,
    outcome: Literal["success", "failure", "denied", "error"],
    details: dict[str, Any] | None = None,
    request_id: str | None = None,
) -> None:
    """
    Log an audit event for artifact operations.

    Args:
        audit_service: The audit service (may be None if not configured)
        event_type: Type of artifact event
        artifact_id: ID of the artifact
        user_id: ID of the user performing the action
        username: Username if available
        action: Human-readable description of the action
        outcome: Result of the action
        details: Additional metadata
        request_id: Request ID for correlation
    """
    if audit_service is None:
        logger.debug("Audit service not available, skipping audit log")
        return

    try:
        event = UnifiedAuditEvent(
            category=AuditEventCategory.DATA_MODIFICATION,
            event_type=event_type,
            actor=AuditActor(
                actor_id=user_id,
                actor_type="user",
                username=username,
            ),
            resource_type="artifact",
            resource_id=artifact_id,
            action=action,
            outcome=outcome,
            context=AuditContext(
                request_id=request_id or str(uuid4()),
            ),
            details=details or {},
            regulation_tags=["SOC2", "GDPR"],
        )

        await audit_service.log_event(event)
        logger.debug(
            "Logged artifact audit event",
            extra={
                "event_type": event_type.value,
                "artifact_id": artifact_id,
                "outcome": outcome,
            },
        )
    except Exception as e:
        # Don't fail the operation if audit logging fails
        logger.warning(
            "Failed to log artifact audit event",
            extra={
                "event_type": event_type.value,
                "artifact_id": artifact_id,
                "error": str(e),
            },
        )


# Routes


@artifacts_router.post("/artifacts/search")
async def semantic_search(
    request: SemanticSearchRequest,
    current_user: CurrentUser,
    audit_service: AuditService,
) -> SemanticSearchResponse:
    """
    Semantic search across artifacts.

    Uses vector embeddings to find artifacts matching the query.
    Returns results sorted by relevance score.
    """
    user_id = _get_user_id(current_user)
    service = get_artifacts_service()

    results = await service.semantic_search(
        query=request.query,
        user_id=user_id,
        limit=request.limit,
    )

    # Audit logging for search operations
    await log_artifact_audit_event(
        audit_service=audit_service,
        event_type=AuditEventType.ARTIFACT_SEARCH,
        artifact_id="search",  # No specific artifact
        user_id=user_id,
        username=current_user.get("username"),
        action=f"Semantic search for '{request.query[:50]}...' returned {len(results)} results",
        outcome="success",
        details={
            "query_length": len(request.query),
            "limit": request.limit,
            "result_count": len(results),
        },
    )

    return SemanticSearchResponse(
        results=[SemanticSearchResult(**r) for r in results]
    )


@artifacts_router.get("/artifacts")
async def list_artifacts(
    current_user: CurrentUser,
    session_id: str | None = Query(default=None, description="Filter by session ID"),
    limit: int = Query(default=20, ge=1, le=100, description="Max items to return"),
    cursor: str | None = Query(default=None, description="Pagination cursor"),
) -> ListArtifactsResponse:
    """
    List artifacts for the current user.

    Supports filtering by session_id and cursor-based pagination.
    Returns artifacts sorted by updated_at descending.
    """
    user_id = _get_user_id(current_user)
    service = get_artifacts_service()

    items, next_cursor, has_more = await service.list_artifacts(
        user_id=user_id,
        session_id=session_id,
        limit=limit,
        cursor=cursor,
    )

    return ListArtifactsResponse(
        items=[ArtifactResponse(**item) for item in items],
        cursor=next_cursor,
        hasMore=has_more,
    )


@artifacts_router.get("/artifacts/{artifact_id}")
async def get_artifact(
    artifact_id: str,
    current_user: CurrentUser,
) -> ArtifactResponse:
    """
    Get a specific artifact by ID.

    Returns 404 if artifact not found or not owned by user.
    """
    user_id = _get_user_id(current_user)
    service = get_artifacts_service()

    artifact = await service.get_artifact(artifact_id, user_id)

    if not artifact:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Artifact not found",
        )

    return ArtifactResponse(**artifact)


@artifacts_router.post(
    "/artifacts",
    status_code=status.HTTP_201_CREATED,
)
async def create_artifact(
    request: ArtifactCreateRequest,
    current_user: CurrentUser,
    audit_service: AuditService,
) -> ArtifactCreateResponse:
    """
    Create a new artifact.

    Returns the new artifact ID, version, and created_at timestamp.
    """
    # Validate content size
    content_size = len(request.content.encode("utf-8"))
    max_size = settings.artifacts_max_content_size
    if content_size > max_size:
        raise HTTPException(
            status_code=413,  # HTTP 413 Content Too Large
            detail=f"Content size ({content_size} bytes) exceeds maximum allowed ({max_size} bytes)",
        )

    user_id = _get_user_id(current_user)
    service = get_artifacts_service()

    result = await service.create_artifact(
        data=request.model_dump(exclude_none=True),
        user_id=user_id,
    )

    # Audit logging
    await log_artifact_audit_event(
        audit_service=audit_service,
        event_type=AuditEventType.ARTIFACT_CREATED,
        artifact_id=result["id"],
        user_id=user_id,
        username=current_user.get("username"),
        action=f"Created artifact '{request.title}' in session {request.session_id}",
        outcome="success",
        details={
            "content_type": request.content_type.value,
            "session_id": request.session_id,
            "title": request.title,
        },
    )

    return ArtifactCreateResponse(**result)


@artifacts_router.put(
    "/artifacts/{artifact_id}"
)
async def update_artifact(
    artifact_id: str,
    request: ArtifactUpdateRequest,
    current_user: CurrentUser,
    audit_service: AuditService,
) -> ArtifactUpdateResponse:
    """
    Update an existing artifact.

    Creates a new version and returns the updated version number.
    Returns 404 if artifact not found or not owned by user.
    """
    # Validate content size if content is provided
    if request.content is not None:
        content_size = len(request.content.encode("utf-8"))
        max_size = settings.artifacts_max_content_size
        if content_size > max_size:
            raise HTTPException(
                status_code=413,  # HTTP 413 Content Too Large
                detail=f"Content size ({content_size} bytes) exceeds maximum allowed ({max_size} bytes)",
            )

    user_id = _get_user_id(current_user)
    service = get_artifacts_service()

    result = await service.update_artifact(
        artifact_id=artifact_id,
        data=request.model_dump(exclude_none=True),
        user_id=user_id,
    )

    if not result:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Artifact not found",
        )

    # Audit logging
    await log_artifact_audit_event(
        audit_service=audit_service,
        event_type=AuditEventType.ARTIFACT_UPDATED,
        artifact_id=artifact_id,
        user_id=user_id,
        username=current_user.get("username"),
        action=f"Updated artifact {artifact_id} to version {result['version']}",
        outcome="success",
        details={
            "new_version": result["version"],
            "has_content_change": request.content is not None,
            "has_title_change": request.title is not None,
        },
    )

    return ArtifactUpdateResponse(**result)


@artifacts_router.delete(
    "/artifacts/{artifact_id}", status_code=status.HTTP_204_NO_CONTENT
)
async def delete_artifact(
    artifact_id: str,
    current_user: CurrentUser,
    audit_service: AuditService,
) -> Response:
    """
    Delete an artifact.

    Returns 204 No Content on success, 404 if not found.
    """
    user_id = _get_user_id(current_user)
    service = get_artifacts_service()

    deleted = await service.delete_artifact(artifact_id, user_id)

    if not deleted:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Artifact not found",
        )

    # Audit logging
    await log_artifact_audit_event(
        audit_service=audit_service,
        event_type=AuditEventType.ARTIFACT_DELETED,
        artifact_id=artifact_id,
        user_id=user_id,
        username=current_user.get("username"),
        action=f"Deleted artifact {artifact_id}",
        outcome="success",
    )

    return Response(status_code=status.HTTP_204_NO_CONTENT)


@artifacts_router.get("/artifacts/{artifact_id}/similar")
async def find_similar_artifacts(
    artifact_id: str,
    current_user: CurrentUser,
    audit_service: AuditService,
    limit: int = Query(default=5, ge=1, le=50, description="Max results"),
) -> FindSimilarResponse:
    """
    Find artifacts similar to a given artifact.

    Uses vector embeddings to find semantically similar artifacts.
    Returns results sorted by similarity score.
    """
    user_id = _get_user_id(current_user)
    service = get_artifacts_service()

    results = await service.find_similar(
        artifact_id=artifact_id,
        user_id=user_id,
        limit=limit,
    )

    # Audit logging for similar search
    await log_artifact_audit_event(
        audit_service=audit_service,
        event_type=AuditEventType.ARTIFACT_SIMILAR_SEARCH,
        artifact_id=artifact_id,
        user_id=user_id,
        username=current_user.get("username"),
        action=f"Find similar artifacts for {artifact_id}, returned {len(results)} results",
        outcome="success",
        details={
            "source_artifact_id": artifact_id,
            "limit": limit,
            "result_count": len(results),
        },
    )

    return FindSimilarResponse(
        results=[SemanticSearchResult(**r) for r in results]
    )


@artifacts_router.get(
    "/artifacts/{artifact_id}/versions",
)
async def get_artifact_versions(
    artifact_id: str,
    current_user: CurrentUser,
) -> list[ArtifactVersionResponse]:
    """
    Get version history for an artifact.

    Returns list of versions sorted by version number.
    Returns 404 if artifact not found or not owned by user.
    """
    user_id = _get_user_id(current_user)
    service = get_artifacts_service()

    versions = await service.get_artifact_versions(artifact_id, user_id)

    if versions is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Artifact not found",
        )

    return [ArtifactVersionResponse(**v) for v in versions]


@artifacts_router.post(
    "/artifacts/{artifact_id}/fork",
    status_code=status.HTTP_201_CREATED,
)
async def fork_artifact(
    artifact_id: str,
    request: ArtifactForkRequest,
    current_user: CurrentUser,
    audit_service: AuditService,
) -> ArtifactForkResponse:
    """
    Fork an artifact.

    Creates a copy of the artifact with a new ID.
    The new artifact starts at version 1.
    Returns 404 if source artifact not found.
    """
    user_id = _get_user_id(current_user)
    service = get_artifacts_service()

    result = await service.fork_artifact(
        artifact_id=artifact_id,
        new_name=request.new_name,
        user_id=user_id,
    )

    if not result:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Artifact not found",
        )

    # Audit logging
    await log_artifact_audit_event(
        audit_service=audit_service,
        event_type=AuditEventType.ARTIFACT_FORKED,
        artifact_id=result["id"],
        user_id=user_id,
        username=current_user.get("username"),
        action=f"Forked artifact {artifact_id} to {result['id']}",
        outcome="success",
        details={
            "parent_id": artifact_id,
            "new_title": request.new_name,
        },
    )

    return ArtifactForkResponse(**result)
