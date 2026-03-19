"""
Phase Checkpoints

Manages phase completion summaries for agentic workflows.
Delegates storage to a CheckpointRepository backend (InMemory or Postgres).

Usage:
    from mcp_server_langgraph.memory.checkpoints import CheckpointManager

    manager = CheckpointManager()
    checkpoint = await manager.create_checkpoint(phase="research", summary="...")
"""

from __future__ import annotations

import uuid
import warnings
from datetime import UTC, datetime
from pathlib import Path
from typing import TYPE_CHECKING, Any

from pydantic import BaseModel, Field

from mcp_server_langgraph.core.feature_flags import feature_gated

if TYPE_CHECKING:
    from mcp_server_langgraph.repositories.checkpoint import CheckpointRepository


class Checkpoint(BaseModel):
    """A phase completion checkpoint."""

    id: str = Field(description="Unique checkpoint identifier")
    phase: str = Field(description="Phase name")
    summary: str = Field(description="Phase completion summary")
    created_at: datetime = Field(
        default_factory=lambda: datetime.now(UTC),
        description="Creation timestamp",
    )
    artifacts: list[str] = Field(
        default_factory=list,
        description="List of artifact references",
    )
    metadata: dict[str, Any] = Field(
        default_factory=dict,
        description="Additional metadata",
    )
    session_id: str | None = Field(
        default=None,
        description="Session ID for scoping",
    )
    user_id: str | None = Field(
        default=None,
        description="User ID who created the checkpoint",
    )


class CheckpointManager:
    """Manager for phase checkpoints with repository-backed persistence.

    Delegates all storage operations to a CheckpointRepository.
    Business logic (feature gating) remains here.
    """

    def __init__(
        self,
        storage_dir: Path | None = None,
        repository: CheckpointRepository | None = None,
    ) -> None:
        """Initialize checkpoint manager.

        Args:
            storage_dir: Deprecated. Directory for checkpoint storage.
            repository: Optional CheckpointRepository. Defaults via get_checkpoint_repository()
        """
        self.storage_dir = storage_dir or Path("./checkpoints")

        if repository is not None:
            self._repository = repository
        else:
            from mcp_server_langgraph.core.dependencies import get_checkpoint_repository

            self._repository = get_checkpoint_repository()

    @feature_gated("enable_agentic_memory", "Agentic Memory")
    async def create_checkpoint(
        self,
        phase: str,
        summary: str,
        artifacts: list[str] | None = None,
        metadata: dict[str, Any] | None = None,
        session_id: str | None = None,
        user_id: str | None = None,
    ) -> Checkpoint:
        """Create a new checkpoint.

        Args:
            phase: Phase name
            summary: Phase completion summary
            artifacts: Optional artifact references
            metadata: Optional metadata
            session_id: Optional session ID
            user_id: Optional user ID

        Returns:
            Created Checkpoint object

        Raises:
            FeatureDisabledError: If agentic memory is disabled
        """
        checkpoint_id = f"checkpoint-{uuid.uuid4().hex[:8]}"
        checkpoint = Checkpoint(
            id=checkpoint_id,
            phase=phase,
            summary=summary,
            artifacts=artifacts or [],
            metadata=metadata or {},
            session_id=session_id,
            user_id=user_id,
        )
        return await self._repository.create(checkpoint)

    async def get_checkpoint(self, checkpoint_id: str, *, actor_user_id: str | None = None) -> Checkpoint | None:
        """Get a checkpoint by ID, with optional ownership enforcement."""
        checkpoint = await self._repository.get(checkpoint_id)
        if checkpoint and actor_user_id and checkpoint.user_id and checkpoint.user_id != actor_user_id:
            return None
        return checkpoint

    async def get_latest_checkpoint(self, user_id: str | None = None) -> Checkpoint | None:
        """Get the most recent checkpoint, optionally scoped by user."""
        return await self._repository.get_latest(user_id=user_id)

    async def list_checkpoints(self, phase: str | None = None, *, actor_user_id: str | None = None) -> list[Checkpoint]:
        """List checkpoints, optionally filtered by phase and scoped by user."""
        return await self._repository.list(phase=phase, user_id=actor_user_id)

    async def delete_checkpoint(self, checkpoint_id: str, *, actor_user_id: str | None = None) -> None:
        """Delete a checkpoint by ID, with optional ownership enforcement."""
        if actor_user_id:
            checkpoint = await self._repository.get(checkpoint_id)
            if checkpoint and checkpoint.user_id and checkpoint.user_id != actor_user_id:
                return
        await self._repository.delete(checkpoint_id)

    async def clear(self) -> None:
        """Clear all checkpoints."""
        await self._repository.clear()

    async def summarize_session(self, user_id: str | None = None) -> str:
        """Generate a summary of the session from all checkpoints."""
        return await self._repository.summarize(user_id=user_id)

    def persist(self) -> None:
        """Deprecated: No-op when using repository backend."""
        warnings.warn(
            "CheckpointManager.persist() is deprecated. Checkpoints are persisted via repository backend.",
            DeprecationWarning,
            stacklevel=2,
        )

    def load(self) -> None:
        """Deprecated: No-op when using repository backend."""
        warnings.warn(
            "CheckpointManager.load() is deprecated. Checkpoints are loaded via repository backend.",
            DeprecationWarning,
            stacklevel=2,
        )
