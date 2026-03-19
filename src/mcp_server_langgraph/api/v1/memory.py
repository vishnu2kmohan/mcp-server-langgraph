"""
Agentic Memory REST API

Provides REST endpoints for managing agent memory including:
- Structured notes with categories and tags
- Phase checkpoints for context recovery
- Session summaries

Requires: enable_agentic_memory feature flag
"""

from typing import Any

from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel, Field

from mcp_server_langgraph.auth.dependencies import get_current_user
from mcp_server_langgraph.core.feature_flags import feature_flags
from mcp_server_langgraph.memory.checkpoints import Checkpoint, CheckpointManager
from mcp_server_langgraph.memory.notes import Note, NotesManager
from mcp_server_langgraph.observability.telemetry import logger

memory_router = APIRouter(tags=["memory"])

# Global instances (overridable for testing)
_notes_manager: NotesManager | None = None
_checkpoint_manager: CheckpointManager | None = None


def set_notes_manager(manager: NotesManager | None) -> None:
    """Set the notes manager (for testing)."""
    global _notes_manager
    _notes_manager = manager


def set_checkpoint_manager(manager: CheckpointManager | None) -> None:
    """Set the checkpoint manager (for testing)."""
    global _checkpoint_manager
    _checkpoint_manager = manager


def get_notes_manager() -> NotesManager:
    """Get or create the notes manager."""
    global _notes_manager
    if _notes_manager is None:
        _notes_manager = NotesManager()
    return _notes_manager


def get_checkpoint_manager() -> CheckpointManager:
    """Get or create the checkpoint manager."""
    global _checkpoint_manager
    if _checkpoint_manager is None:
        _checkpoint_manager = CheckpointManager()
    return _checkpoint_manager


# ============================================================================
# Request/Response Models
# ============================================================================


class CreateNoteRequest(BaseModel):
    """Request to create a note."""

    content: str = Field(..., description="Note content")
    category: str = Field(default="general", description="Note category")
    tags: list[str] = Field(default_factory=list, description="Note tags")
    metadata: dict[str, Any] = Field(default_factory=dict, description="Additional metadata")


class NoteResponse(BaseModel):
    """Response containing a note."""

    id: str
    content: str
    category: str
    tags: list[str]
    created_at: str
    metadata: dict[str, Any]

    @classmethod
    def from_note(cls, note: Note) -> "NoteResponse":
        """Create response from Note model."""
        return cls(
            id=note.id,
            content=note.content,
            category=note.category,
            tags=note.tags,
            created_at=note.created_at.isoformat(),
            metadata=note.metadata,
        )


class NotesListResponse(BaseModel):
    """Response containing a list of notes."""

    notes: list[NoteResponse]


class CreateCheckpointRequest(BaseModel):
    """Request to create a checkpoint."""

    phase: str = Field(..., description="Phase name")
    summary: str = Field(..., description="Phase completion summary")
    artifacts: list[str] = Field(default_factory=list, description="Artifact references")
    metadata: dict[str, Any] = Field(default_factory=dict, description="Additional metadata")


class CheckpointResponse(BaseModel):
    """Response containing a checkpoint."""

    id: str
    phase: str
    summary: str
    created_at: str
    artifacts: list[str]
    metadata: dict[str, Any]

    @classmethod
    def from_checkpoint(cls, checkpoint: Checkpoint) -> "CheckpointResponse":
        """Create response from Checkpoint model."""
        return cls(
            id=checkpoint.id,
            phase=checkpoint.phase,
            summary=checkpoint.summary,
            created_at=checkpoint.created_at.isoformat(),
            artifacts=checkpoint.artifacts,
            metadata=checkpoint.metadata,
        )


class CheckpointsListResponse(BaseModel):
    """Response containing a list of checkpoints."""

    checkpoints: list[CheckpointResponse]


class SessionSummaryResponse(BaseModel):
    """Response containing session summary."""

    summary: str


# ============================================================================
# Notes Endpoints
# ============================================================================


@memory_router.post(
    "/notes",
    status_code=status.HTTP_201_CREATED,
)
async def create_note(
    request: CreateNoteRequest,
    current_user: dict[str, Any] = Depends(get_current_user),
) -> NoteResponse:
    """Create a new structured note.

    Requires enable_agentic_memory feature flag.
    """
    if not feature_flags.enable_agentic_memory:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Agentic memory feature is disabled",
        )

    manager = get_notes_manager()
    note = await manager.add_note(
        content=request.content,
        category=request.category,
        tags=request.tags,
        metadata=request.metadata,
        user_id=current_user.get("sub"),
    )

    logger.info(
        "Note created",
        extra={
            "note_id": note.id,
            "category": note.category,
            "user_id": current_user.get("sub"),
        },
    )

    return NoteResponse.from_note(note)


@memory_router.get(
    "/notes",
)
async def list_notes(
    query: str | None = None,
    category: str | None = None,
    current_user: dict[str, Any] = Depends(get_current_user),
) -> NotesListResponse:
    """List notes with optional search/filter.

    Args:
        query: Search query for note content
        category: Filter by category
    """
    manager = get_notes_manager()
    user_id = current_user.get("sub")

    if query:
        notes = await manager.search(query, actor_user_id=user_id)
    elif category:
        notes = await manager.list_notes(category=category, user_id=user_id)
    else:
        notes = await manager.list_notes(user_id=user_id)

    return NotesListResponse(notes=[NoteResponse.from_note(note) for note in notes])


@memory_router.get(
    "/notes/{note_id}",
)
async def get_note(
    note_id: str,
    current_user: dict[str, Any] = Depends(get_current_user),
) -> NoteResponse:
    """Get a note by ID."""
    manager = get_notes_manager()
    user_id = current_user.get("sub")
    note = await manager.get_note(note_id, actor_user_id=user_id)

    if not note:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Note {note_id} not found",
        )

    return NoteResponse.from_note(note)


@memory_router.delete(
    "/notes/{note_id}",
    status_code=status.HTTP_204_NO_CONTENT,
)
async def delete_note(
    note_id: str,
    current_user: dict[str, Any] = Depends(get_current_user),
) -> None:
    """Delete a note by ID."""
    manager = get_notes_manager()
    user_id = current_user.get("sub")
    note = await manager.get_note(note_id, actor_user_id=user_id)

    if not note:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Note {note_id} not found",
        )

    await manager.delete_note(note_id, actor_user_id=user_id)
    logger.info(
        "Note deleted",
        extra={
            "note_id": note_id,
            "user_id": current_user.get("sub"),
        },
    )


# ============================================================================
# Checkpoint Endpoints
# ============================================================================


@memory_router.post(
    "/checkpoint",
    status_code=status.HTTP_201_CREATED,
)
async def create_checkpoint(
    request: CreateCheckpointRequest,
    current_user: dict[str, Any] = Depends(get_current_user),
) -> CheckpointResponse:
    """Create a new phase checkpoint.

    Requires enable_agentic_memory feature flag.
    """
    if not feature_flags.enable_agentic_memory:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Agentic memory feature is disabled",
        )

    manager = get_checkpoint_manager()
    checkpoint = await manager.create_checkpoint(
        phase=request.phase,
        summary=request.summary,
        artifacts=request.artifacts,
        metadata=request.metadata,
        user_id=current_user.get("sub"),
    )

    logger.info(
        "Checkpoint created",
        extra={
            "checkpoint_id": checkpoint.id,
            "phase": checkpoint.phase,
            "user_id": current_user.get("sub"),
        },
    )

    return CheckpointResponse.from_checkpoint(checkpoint)


@memory_router.get(
    "/checkpoint",
)
async def list_checkpoints(
    phase: str | None = None,
    current_user: dict[str, Any] = Depends(get_current_user),
) -> CheckpointsListResponse:
    """List checkpoints with optional phase filter."""
    manager = get_checkpoint_manager()
    user_id = current_user.get("sub")
    checkpoints = await manager.list_checkpoints(phase=phase, actor_user_id=user_id)

    return CheckpointsListResponse(checkpoints=[CheckpointResponse.from_checkpoint(cp) for cp in checkpoints])


@memory_router.get(
    "/checkpoint/latest",
)
async def get_latest_checkpoint(
    current_user: dict[str, Any] = Depends(get_current_user),
) -> CheckpointResponse:
    """Get the most recent checkpoint."""
    manager = get_checkpoint_manager()
    checkpoint = await manager.get_latest_checkpoint(user_id=current_user.get("sub"))

    if not checkpoint:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="No checkpoints found",
        )

    return CheckpointResponse.from_checkpoint(checkpoint)


@memory_router.get(
    "/checkpoint/summary",
)
async def get_session_summary(
    current_user: dict[str, Any] = Depends(get_current_user),
) -> SessionSummaryResponse:
    """Get session summary from all checkpoints."""
    manager = get_checkpoint_manager()
    summary = await manager.summarize_session(user_id=current_user.get("sub"))

    return SessionSummaryResponse(summary=summary)
