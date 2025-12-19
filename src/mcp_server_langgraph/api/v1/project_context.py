"""
Project Context API Endpoint.

REST API for managing project context files (.studio/context.md).

Endpoints:
- GET /context - Get project context
- PUT /context - Update project context
- DELETE /context - Delete project context

Authentication:
- Uses Keycloak JWT authentication via get_current_user dependency
"""

from __future__ import annotations

import logging
from typing import Annotated, Any

from fastapi import APIRouter, Depends, HTTPException, Query, status
from pydantic import BaseModel, Field, field_validator

from mcp_server_langgraph.auth.middleware import get_current_user

logger = logging.getLogger(__name__)

# ==============================================================================
# Router
# ==============================================================================

project_context_router = APIRouter(
    prefix="/context",
    tags=["context"],
)

# ==============================================================================
# Constants
# ==============================================================================

MAX_CONTENT_SIZE = 1024 * 1024  # 1MB max content size
DEFAULT_CONTEXT_PATH = ".studio/context.md"


# ==============================================================================
# Models
# ==============================================================================


class ProjectContextResponse(BaseModel):
    """Project context response model."""

    project_id: str = Field(description="Project ID")
    content: str = Field(description="Context file content")
    path: str = Field(default=DEFAULT_CONTEXT_PATH, description="Context file path")
    exists: bool = Field(description="Whether context file exists")
    last_modified: str | None = Field(default=None, description="Last modification time")


class ProjectContextUpdate(BaseModel):
    """Project context update request model."""

    project_id: str = Field(description="Project ID")
    content: str = Field(description="Context file content")

    @field_validator("content")
    @classmethod
    def validate_content_size(cls, v: str) -> str:
        """Validate content size."""
        if len(v.encode("utf-8")) > MAX_CONTENT_SIZE:
            raise ValueError(f"Content exceeds maximum size of {MAX_CONTENT_SIZE} bytes")
        return v


class DeleteResponse(BaseModel):
    """Delete response model."""

    success: bool = Field(description="Whether deletion succeeded")
    message: str = Field(description="Status message")


# ==============================================================================
# Context Service (Mock/Stub)
# ==============================================================================

_context_service: Any | None = None


def set_context_service(service: Any | None) -> None:
    """Set the context service for dependency injection."""
    global _context_service
    _context_service = service


def get_context_service() -> Any:
    """Get the context service."""
    return _context_service


# ==============================================================================
# Type Aliases
# ==============================================================================

CurrentUser = Annotated[dict[str, Any], Depends(get_current_user)]


# ==============================================================================
# Endpoints
# ==============================================================================


@project_context_router.get(
    "",
    response_model=ProjectContextResponse,
    summary="Get project context",
    description="Get the project context file content.",
)
async def get_context(
    current_user: CurrentUser,
    project_id: str = Query(..., description="Project ID"),
) -> ProjectContextResponse:
    """Get project context."""
    service = get_context_service()

    if service:
        context = await service.get_context(project_id)
        return ProjectContextResponse(**context)

    # Default empty response when no service configured
    return ProjectContextResponse(
        project_id=project_id,
        content="",
        path=DEFAULT_CONTEXT_PATH,
        exists=False,
        last_modified=None,
    )


@project_context_router.put(
    "",
    response_model=ProjectContextResponse,
    summary="Update project context",
    description="Create or update the project context file.",
)
async def update_context(
    current_user: CurrentUser,
    request: ProjectContextUpdate,
) -> ProjectContextResponse:
    """Update project context."""
    service = get_context_service()

    if service:
        context = await service.update_context(request.project_id, request.content)
        return ProjectContextResponse(**context)

    # Default response when no service configured
    logger.info(
        "Updated project context",
        extra={
            "project_id": request.project_id,
            "user_id": current_user.get("user_id"),
            "content_length": len(request.content),
        },
    )

    return ProjectContextResponse(
        project_id=request.project_id,
        content=request.content,
        path=DEFAULT_CONTEXT_PATH,
        exists=True,
        last_modified=None,
    )


@project_context_router.delete(
    "",
    response_model=DeleteResponse,
    summary="Delete project context",
    description="Delete the project context file.",
)
async def delete_context(
    current_user: CurrentUser,
    project_id: str = Query(..., description="Project ID"),
) -> DeleteResponse:
    """Delete project context."""
    service = get_context_service()

    if service:
        deleted = await service.delete_context(project_id)
        if not deleted:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Context not found for project {project_id}",
            )
        return DeleteResponse(success=True, message="Context deleted successfully")

    # Default response when no service configured
    logger.info(
        "Deleted project context",
        extra={
            "project_id": project_id,
            "user_id": current_user.get("user_id"),
        },
    )

    return DeleteResponse(success=True, message="Context deleted successfully")
