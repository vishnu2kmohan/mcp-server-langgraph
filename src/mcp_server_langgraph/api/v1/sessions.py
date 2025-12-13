"""
Sessions Router

Provides CRUD operations for chat session management under /api/v1/sessions/*.

This consolidates session functionality from playground into a unified API.

Usage:
    GET /api/v1/sessions - List all sessions (with pagination)
    GET /api/v1/sessions/{id} - Get a specific session
    POST /api/v1/sessions - Create a new session
    DELETE /api/v1/sessions/{id} - Delete a session
    GET /api/v1/sessions/{id}/messages - Get messages in a session
    POST /api/v1/sessions/{id}/messages - Add a message to a session
"""

from typing import Any, Literal

from fastapi import APIRouter, HTTPException, Query, status
from pydantic import BaseModel, Field

from mcp_server_langgraph.api.pagination import (
    CursorPaginatedResponse,
    CursorPaginationMetadata,
)


sessions_router = APIRouter(tags=["sessions"])


# Request/Response Models


class MessageRequest(BaseModel):
    """Request body for adding a message."""

    role: Literal["user", "assistant", "system"] = Field(description="Message role")
    content: str = Field(description="Message content", min_length=1)


class MessageResponse(BaseModel):
    """Response model for a message."""

    role: str = Field(description="Message role")
    content: str = Field(description="Message content")
    timestamp: str | None = Field(default=None, description="Message timestamp")


class SessionCreateRequest(BaseModel):
    """Request body for creating a session."""

    title: str | None = Field(default=None, description="Session title", max_length=255)
    workflow_id: str | None = Field(default=None, description="Associated workflow ID")


class SessionResponse(BaseModel):
    """Response model for a session."""

    id: str = Field(description="Session ID")
    title: str | None = Field(default=None, description="Session title")
    workflow_id: str | None = Field(default=None, description="Associated workflow ID")
    messages: list[dict[str, Any]] = Field(default_factory=list, description="Session messages")
    created_at: str | None = Field(default=None, description="Creation timestamp")
    updated_at: str | None = Field(default=None, description="Last update timestamp")
    status: str = Field(default="active", description="Session status")


# Service Interface (will be implemented in Phase 4: Storage Consolidation)


class SessionService:
    """Interface for session operations. Implemented by storage layer."""

    async def list_sessions(
        self,
        cursor: str | None = None,
        limit: int = 20,
        workflow_id: str | None = None,
    ) -> tuple[list[dict[str, Any]], str | None]:
        """List sessions with pagination. Returns (sessions, next_cursor)."""
        raise NotImplementedError

    async def get_session(self, session_id: str) -> dict[str, Any] | None:
        """Get a session by ID. Returns None if not found."""
        raise NotImplementedError

    async def create_session(self, session_data: dict[str, Any]) -> dict[str, Any]:
        """Create a new session. Returns the created session."""
        raise NotImplementedError

    async def delete_session(self, session_id: str) -> bool:
        """Delete a session. Returns True if deleted, False if not found."""
        raise NotImplementedError

    async def get_session_messages(self, session_id: str) -> list[dict[str, Any]] | None:
        """Get all messages in a session. Returns None if session not found."""
        raise NotImplementedError

    async def add_message(self, session_id: str, message_data: dict[str, Any]) -> dict[str, Any] | None:
        """Add a message to a session. Returns None if session not found."""
        raise NotImplementedError


# Service singleton (will be replaced by dependency injection in Phase 4)
_session_service: SessionService | None = None


def get_session_service() -> SessionService:
    """Get the session service instance."""
    global _session_service
    if _session_service is None:
        _session_service = SessionService()
    return _session_service


def set_session_service(service: SessionService) -> None:
    """Set the session service instance (for testing/DI)."""
    global _session_service
    _session_service = service


# Endpoints


@sessions_router.get("/sessions")
async def list_sessions(
    cursor: str | None = Query(default=None, description="Pagination cursor"),
    limit: int = Query(default=20, ge=1, le=100, description="Items per page"),
    workflow_id: str | None = Query(default=None, description="Filter by workflow ID"),
) -> CursorPaginatedResponse[dict[str, Any]]:
    """
    List all sessions with cursor-based pagination.

    Optionally filter by workflow_id to get sessions for a specific workflow.
    """
    service = get_session_service()
    sessions, next_cursor = await service.list_sessions(cursor=cursor, limit=limit, workflow_id=workflow_id)

    # Build pagination metadata
    has_next = next_cursor is not None
    pagination = CursorPaginationMetadata(
        next_cursor=next_cursor,
        prev_cursor=None,
        has_next=has_next,
        has_prev=cursor is not None,
        count=len(sessions),
    )

    return CursorPaginatedResponse(data=sessions, pagination=pagination)


@sessions_router.get("/sessions/{session_id}")
async def get_session(session_id: str) -> SessionResponse:
    """
    Get a specific session by ID.

    Returns the complete session data including messages.
    """
    service = get_session_service()
    session = await service.get_session(session_id)

    if session is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Session {session_id} not found",
        )

    return SessionResponse(**session)


@sessions_router.post("/sessions", status_code=status.HTTP_201_CREATED)
async def create_session(request: SessionCreateRequest) -> SessionResponse:
    """
    Create a new session.

    The session can optionally be associated with a workflow.
    """
    service = get_session_service()
    session_data = request.model_dump()
    session = await service.create_session(session_data)

    return SessionResponse(**session)


@sessions_router.delete("/sessions/{session_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_session(session_id: str) -> None:
    """
    Delete a session.

    This permanently removes the session and all its messages.
    """
    service = get_session_service()
    deleted = await service.delete_session(session_id)

    if not deleted:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Session {session_id} not found",
        )


@sessions_router.get("/sessions/{session_id}/messages")
async def get_session_messages(session_id: str) -> list[dict[str, Any]]:
    """
    Get all messages in a session.

    Returns messages in chronological order.
    """
    service = get_session_service()
    messages = await service.get_session_messages(session_id)

    if messages is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Session {session_id} not found",
        )

    return messages


@sessions_router.post("/sessions/{session_id}/messages", status_code=status.HTTP_201_CREATED)
async def add_message(session_id: str, request: MessageRequest) -> dict[str, Any]:
    """
    Add a message to a session.

    The message is appended to the session's message history.
    """
    service = get_session_service()
    message_data = request.model_dump()
    message = await service.add_message(session_id, message_data)

    if message is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Session {session_id} not found",
        )

    return message
