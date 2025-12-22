"""
Phase Checkpoints

Manages phase completion summaries for agentic workflows.

Enables agents to checkpoint progress and retrieve context
when approaching context limits.

Usage:
    from mcp_server_langgraph.memory.checkpoints import CheckpointManager

    manager = CheckpointManager(storage_dir=Path("./checkpoints"))
    checkpoint = manager.create_checkpoint(phase="research", summary="...")
"""

from __future__ import annotations

import json
import uuid
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

from pydantic import BaseModel, Field

from mcp_server_langgraph.core.feature_flags import feature_gated


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


class CheckpointManager:
    """Manager for phase checkpoints.

    Handles checkpoint creation, retrieval, and persistence
    for cross-session context recovery.
    """

    def __init__(self, storage_dir: Path | None = None) -> None:
        """Initialize checkpoint manager.

        Args:
            storage_dir: Directory for checkpoint storage
        """
        self.storage_dir = storage_dir or Path("./checkpoints")
        self._checkpoints: dict[str, Checkpoint] = {}

    @feature_gated("enable_agentic_memory", "Agentic Memory")
    def create_checkpoint(
        self,
        phase: str,
        summary: str,
        artifacts: list[str] | None = None,
        metadata: dict[str, Any] | None = None,
    ) -> Checkpoint:
        """Create a new checkpoint.

        Args:
            phase: Phase name
            summary: Phase completion summary
            artifacts: Optional artifact references
            metadata: Optional metadata

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
        )
        self._checkpoints[checkpoint_id] = checkpoint
        return checkpoint

    def get_checkpoint(self, checkpoint_id: str) -> Checkpoint | None:
        """Get a checkpoint by ID.

        Args:
            checkpoint_id: Checkpoint identifier

        Returns:
            Checkpoint if found, None otherwise
        """
        return self._checkpoints.get(checkpoint_id)

    def get_latest_checkpoint(self) -> Checkpoint | None:
        """Get the most recent checkpoint.

        Returns:
            Latest checkpoint if any, None otherwise
        """
        if not self._checkpoints:
            return None

        return max(self._checkpoints.values(), key=lambda c: c.created_at)

    def list_checkpoints(self, phase: str | None = None) -> list[Checkpoint]:
        """List all checkpoints, optionally filtered by phase.

        Args:
            phase: Optional phase filter

        Returns:
            List of checkpoints
        """
        checkpoints = list(self._checkpoints.values())
        if phase:
            checkpoints = [c for c in checkpoints if c.phase == phase]
        return checkpoints

    def delete_checkpoint(self, checkpoint_id: str) -> None:
        """Delete a checkpoint by ID.

        Args:
            checkpoint_id: Checkpoint identifier
        """
        self._checkpoints.pop(checkpoint_id, None)

    def clear(self) -> None:
        """Clear all checkpoints."""
        self._checkpoints.clear()

    def persist(self) -> None:
        """Persist checkpoints to storage directory."""
        self.storage_dir.mkdir(parents=True, exist_ok=True)

        checkpoints_file = self.storage_dir / "checkpoints.json"
        data = {
            "checkpoints": [
                c.model_dump(mode="json") for c in self._checkpoints.values()
            ]
        }
        checkpoints_file.write_text(json.dumps(data, indent=2, default=str))

    def load(self) -> None:
        """Load checkpoints from storage directory."""
        checkpoints_file = self.storage_dir / "checkpoints.json"

        if not checkpoints_file.exists():
            return

        data = json.loads(checkpoints_file.read_text())
        for checkpoint_data in data.get("checkpoints", []):
            # Parse datetime string back to datetime
            if "created_at" in checkpoint_data and isinstance(
                checkpoint_data["created_at"], str
            ):
                checkpoint_data["created_at"] = datetime.fromisoformat(
                    checkpoint_data["created_at"]
                )
            checkpoint = Checkpoint(**checkpoint_data)
            self._checkpoints[checkpoint.id] = checkpoint

    def summarize_session(self) -> str:
        """Generate a summary of the session from all checkpoints.

        Returns:
            Session summary string
        """
        if not self._checkpoints:
            return "No checkpoints recorded."

        checkpoints = sorted(self._checkpoints.values(), key=lambda c: c.created_at)

        lines = ["# Session Summary", ""]
        for checkpoint in checkpoints:
            lines.append(f"## {checkpoint.phase.title()}")
            lines.append(checkpoint.summary)
            lines.append("")

        return "\n".join(lines)
