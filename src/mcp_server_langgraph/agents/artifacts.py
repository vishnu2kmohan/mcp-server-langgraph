"""
Artifact Storage

External storage for subagent outputs to avoid "game of telephone"
when synthesizing results from multiple subagents.

Usage:
    from mcp_server_langgraph.agents.artifacts import ArtifactStorage

    storage = ArtifactStorage()
    storage.store("task-1", "result", {"data": "..."})
    artifact = storage.retrieve("task-1", "result")
"""

from __future__ import annotations

from datetime import UTC, datetime
from typing import Any

from pydantic import BaseModel, Field


class Artifact(BaseModel):
    """A stored artifact from subagent execution."""

    task_id: str = Field(description="ID of the task that produced this artifact")
    name: str = Field(description="Artifact name/key")
    data: Any = Field(description="Artifact data")
    created_at: datetime = Field(default_factory=lambda: datetime.now(UTC))
    metadata: dict[str, Any] = Field(default_factory=dict)


class ArtifactStorage:
    """Storage for subagent artifacts.

    Provides storage and retrieval of artifacts produced by
    subagents, enabling clean synthesis without context pollution.
    """

    def __init__(self) -> None:
        """Initialize artifact storage."""
        self._artifacts: dict[str, dict[str, Artifact]] = {}

    def store(
        self,
        task_id: str,
        name: str,
        data: Any,
        metadata: dict[str, Any] | None = None,
    ) -> Artifact:
        """Store an artifact.

        Args:
            task_id: ID of the task
            name: Artifact name/key
            data: Artifact data
            metadata: Optional metadata

        Returns:
            Stored Artifact object
        """
        artifact = Artifact(
            task_id=task_id,
            name=name,
            data=data,
            metadata=metadata or {},
        )

        if task_id not in self._artifacts:
            self._artifacts[task_id] = {}

        self._artifacts[task_id][name] = artifact
        return artifact

    def retrieve(self, task_id: str, name: str) -> Any | None:
        """Retrieve an artifact's data.

        Args:
            task_id: ID of the task
            name: Artifact name/key

        Returns:
            Artifact data if found, None otherwise
        """
        task_artifacts = self._artifacts.get(task_id, {})
        artifact = task_artifacts.get(name)
        return artifact.data if artifact else None

    def get_artifact(self, task_id: str, name: str) -> Artifact | None:
        """Get full artifact object.

        Args:
            task_id: ID of the task
            name: Artifact name/key

        Returns:
            Artifact object if found, None otherwise
        """
        return self._artifacts.get(task_id, {}).get(name)

    def list_for_task(self, task_id: str) -> list[Artifact]:
        """List all artifacts for a task.

        Args:
            task_id: ID of the task

        Returns:
            List of artifacts for the task
        """
        return list(self._artifacts.get(task_id, {}).values())

    def list_all(self) -> list[Artifact]:
        """List all artifacts.

        Returns:
            List of all artifacts
        """
        all_artifacts: list[Artifact] = []
        for task_artifacts in self._artifacts.values():
            all_artifacts.extend(task_artifacts.values())
        return all_artifacts

    def clear_task(self, task_id: str) -> None:
        """Clear all artifacts for a task.

        Args:
            task_id: ID of the task
        """
        self._artifacts.pop(task_id, None)

    def clear_all(self) -> None:
        """Clear all artifacts."""
        self._artifacts.clear()
