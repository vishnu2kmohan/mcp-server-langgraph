"""
MCP Resources for Multi-Agent Orchestration.

Exposes orchestration state as MCP resources:
- orchestrator://tasks/{task_id} - Task decomposition and status
- orchestrator://artifacts/{task_id}/{artifact_name} - Artifacts from subagents
- orchestrator://subagents/{task_id} - Subagent execution status

Reference: https://modelcontextprotocol.io/specification/2025-11-25/server/resources
"""

from __future__ import annotations

import json
from typing import TYPE_CHECKING

from mcp_server_langgraph.mcp.resources import (
    ResourceContent,
    ResourceHandler,
)

if TYPE_CHECKING:
    from mcp_server_langgraph.agents.artifacts import ArtifactStorage
    from mcp_server_langgraph.agents.orchestrator import TaskDecomposition
    from mcp_server_langgraph.agents.subagent import SubagentResult


def parse_orchestrator_uri(uri: str) -> dict[str, str | None]:
    """Parse an orchestrator resource URI.

    Args:
        uri: Resource URI (e.g., orchestrator://tasks/task-123)

    Returns:
        Dict with resource_type, task_id, and optional artifact_name

    Raises:
        ValueError: If URI is not a valid orchestrator URI
    """
    if not uri.startswith("orchestrator://"):
        raise ValueError(f"Invalid orchestrator URI: {uri}")

    # Remove scheme
    path = uri.replace("orchestrator://", "")
    parts = path.split("/")

    if len(parts) < 2:
        raise ValueError(f"Invalid orchestrator URI: {uri}")

    resource_type = parts[0]
    task_id = parts[1]
    artifact_name = parts[2] if len(parts) > 2 else None

    return {
        "resource_type": resource_type,
        "task_id": task_id,
        "artifact_name": artifact_name,
    }


class OrchestratorResourceProvider:
    """Provider for orchestration resources.

    Stores task decompositions, artifacts, and subagent results,
    and provides MCP resource access to them.
    """

    def __init__(
        self,
        artifact_storage: ArtifactStorage | None = None,
    ) -> None:
        """Initialize the provider.

        Args:
            artifact_storage: Optional shared artifact storage
        """
        from mcp_server_langgraph.agents.artifacts import ArtifactStorage

        self._artifact_storage = artifact_storage or ArtifactStorage()
        self._tasks: dict[str, TaskDecomposition] = {}
        self._subagent_results: dict[str, list[SubagentResult]] = {}

    def store_task(self, task_id: str, decomposition: TaskDecomposition) -> None:
        """Store a task decomposition.

        Args:
            task_id: Unique task identifier
            decomposition: Task decomposition data
        """
        self._tasks[task_id] = decomposition

    def store_subagent_results(
        self,
        task_id: str,
        results: list[SubagentResult],
    ) -> None:
        """Store subagent results for a task.

        Args:
            task_id: Parent task identifier
            results: List of subagent results
        """
        self._subagent_results[task_id] = results

    async def read_task(self, uri: str) -> ResourceContent:
        """Read a task resource.

        Args:
            uri: Resource URI (orchestrator://tasks/{task_id})

        Returns:
            ResourceContent with task decomposition data

        Raises:
            ValueError: If task not found
        """
        parsed = parse_orchestrator_uri(uri)
        task_id = parsed["task_id"]

        if task_id not in self._tasks:
            raise ValueError(f"Task not found: {task_id}")

        decomposition = self._tasks[task_id]

        return ResourceContent(
            uri=uri,
            mimeType="application/json",
            text=json.dumps(decomposition.model_dump(), default=str),
        )

    async def read_artifact(self, uri: str) -> ResourceContent:
        """Read an artifact resource.

        Args:
            uri: Resource URI (orchestrator://artifacts/{task_id}/{artifact_name})

        Returns:
            ResourceContent with artifact data

        Raises:
            ValueError: If artifact not found
        """
        parsed = parse_orchestrator_uri(uri)
        task_id = parsed["task_id"]
        artifact_name = parsed["artifact_name"]

        if not artifact_name:
            raise ValueError(f"Artifact name required in URI: {uri}")

        artifact = self._artifact_storage.get_artifact(task_id, artifact_name)
        if artifact is None:
            raise ValueError(f"Artifact not found: {uri}")

        return ResourceContent(
            uri=uri,
            mimeType="application/json",
            text=json.dumps(
                {
                    "task_id": artifact.task_id,
                    "name": artifact.name,
                    "data": artifact.data,
                    "created_at": artifact.created_at.isoformat(),
                    "metadata": artifact.metadata,
                },
                default=str,
            ),
        )

    async def read_subagents(self, uri: str) -> ResourceContent:
        """Read subagent status resource.

        Args:
            uri: Resource URI (orchestrator://subagents/{task_id})

        Returns:
            ResourceContent with subagent results list
        """
        parsed = parse_orchestrator_uri(uri)
        task_id = parsed["task_id"]

        results = self._subagent_results.get(task_id, [])

        # Convert results to serializable format
        subagent_data = []
        for result in results:
            subagent_data.append(
                {
                    "task_id": result.task_id,
                    "success": result.success,
                    "output": result.output,
                    "error": result.error,
                    "duration_ms": result.duration_ms,
                    "confidence": result.confidence,
                    "requires_approval": result.requires_approval,
                    "approval_reason": result.approval_reason,
                }
            )

        return ResourceContent(
            uri=uri,
            mimeType="application/json",
            text=json.dumps({"subagents": subagent_data}, default=str),
        )


def create_orchestrator_resource_handler() -> ResourceHandler:
    """Create a resource handler for orchestration resources.

    Returns:
        ResourceHandler with orchestration templates registered
    """
    handler = ResourceHandler()

    # Register task template
    handler.register_template(
        uri_template="orchestrator://tasks/{task_id}",
        name="Orchestration Task",
        description="Task decomposition, status, and results",
        mime_type="application/json",
    )

    # Register artifact template
    handler.register_template(
        uri_template="orchestrator://artifacts/{task_id}/{artifact_name}",
        name="Task Artifact",
        description="Artifact produced by subagent execution",
        mime_type="application/json",
    )

    # Register subagent status template
    handler.register_template(
        uri_template="orchestrator://subagents/{task_id}",
        name="Subagent Status",
        description="Status of all subagents for a task",
        mime_type="application/json",
    )

    return handler
