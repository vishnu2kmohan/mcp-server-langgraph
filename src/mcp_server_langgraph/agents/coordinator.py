"""
Coordinator

Task coordination for multi-agent orchestration.

Manages subagent lifecycle, tracks execution status, and
coordinates parallel execution with artifact collection.

Usage:
    from mcp_server_langgraph.agents.coordinator import Coordinator

    coordinator = Coordinator()
    coordinator.register_subagent(subagent)
    results = await coordinator.execute_all()
"""

from __future__ import annotations

import asyncio
from typing import Any

from mcp_server_langgraph.agents.artifacts import ArtifactStorage
from mcp_server_langgraph.agents.subagent import Subagent, SubagentResult, SubagentStatus


class Coordinator:
    """Coordinates multi-agent task execution.

    Manages subagents, tracks their status, and orchestrates
    parallel execution with proper artifact collection.
    """

    def __init__(
        self,
        artifact_storage: ArtifactStorage | None = None,
    ) -> None:
        """Initialize coordinator.

        Args:
            artifact_storage: Optional shared artifact storage
        """
        self._subagents: dict[str, Subagent] = {}
        self.artifact_storage = artifact_storage or ArtifactStorage()

    def register_subagent(self, subagent: Subagent) -> None:
        """Register a subagent for coordination.

        Args:
            subagent: Subagent to register
        """
        self._subagents[subagent.task_id] = subagent

    def unregister_subagent(self, task_id: str) -> None:
        """Unregister a subagent.

        Args:
            task_id: ID of the subagent to unregister
        """
        self._subagents.pop(task_id, None)

    def get_subagent(self, task_id: str) -> Subagent | None:
        """Get a subagent by task ID.

        Args:
            task_id: ID of the subagent

        Returns:
            Subagent if found, None otherwise
        """
        return self._subagents.get(task_id)

    def list_subagents(self) -> list[Subagent]:
        """List all registered subagents.

        Returns:
            List of all subagents
        """
        return list(self._subagents.values())

    def get_status_summary(self) -> dict[str, int]:
        """Get summary of subagent statuses.

        Returns:
            Dictionary mapping status to count
        """
        summary: dict[str, int] = {}
        for subagent in self._subagents.values():
            status = subagent.status.value
            summary[status] = summary.get(status, 0) + 1
        return summary

    async def execute_all(self) -> list[SubagentResult]:
        """Execute all pending subagents in parallel.

        Returns:
            List of SubagentResult from all executions
        """
        pending = [
            sa for sa in self._subagents.values()
            if sa.status == SubagentStatus.PENDING
        ]

        if not pending:
            return []

        tasks = [subagent.execute() for subagent in pending]
        results = await asyncio.gather(*tasks, return_exceptions=True)

        # Convert exceptions to failed results
        final_results: list[SubagentResult] = []
        for i, result in enumerate(results):
            if isinstance(result, BaseException):
                final_results.append(SubagentResult(
                    task_id=pending[i].task_id,
                    success=False,
                    error=str(result),
                ))
            else:
                final_results.append(result)

        return final_results

    async def execute_subagent(self, task_id: str) -> SubagentResult | None:
        """Execute a specific subagent.

        Args:
            task_id: ID of the subagent to execute

        Returns:
            SubagentResult if found, None otherwise
        """
        subagent = self.get_subagent(task_id)
        if subagent is None:
            return None

        return await subagent.execute()

    def store_artifact(
        self,
        task_id: str,
        name: str,
        data: Any,
    ) -> None:
        """Store an artifact for a task.

        Args:
            task_id: ID of the task
            name: Artifact name
            data: Artifact data
        """
        self.artifact_storage.store(task_id, name, data)

    def collect_artifacts(self, task_id: str) -> list[Any]:
        """Collect all artifacts for a task.

        Args:
            task_id: ID of the task

        Returns:
            List of artifact data
        """
        artifacts = self.artifact_storage.list_for_task(task_id)
        return [a.data for a in artifacts]

    def cancel_all(self) -> int:
        """Cancel all running subagents.

        Returns:
            Number of subagents cancelled
        """
        cancelled = 0
        for subagent in self._subagents.values():
            if subagent.status == SubagentStatus.RUNNING:
                subagent.cancel()
                cancelled += 1
        return cancelled

    def clear(self) -> None:
        """Clear all subagents and artifacts."""
        self._subagents.clear()
        self.artifact_storage.clear_all()
