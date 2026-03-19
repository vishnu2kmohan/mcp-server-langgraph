"""
Cross-Session State Management

Persistent state across agent sessions for continuity.
Delegates storage to an AgentStateRepository backend (InMemory or Redis).

Usage:
    from mcp_server_langgraph.sdk.state import AgentStateManager

    manager = AgentStateManager()
    await manager.save_state("session-1", {"progress": "50%"})
    state = await manager.resume_session("session-1")
"""

from __future__ import annotations

import warnings
from pathlib import Path
from typing import TYPE_CHECKING, Any

if TYPE_CHECKING:
    from mcp_server_langgraph.repositories.agent_state import AgentStateRepository


class AgentStateManager:
    """Persistent state across agent sessions.

    Enables session resumption and checkpoint-based context recovery.
    Delegates all storage operations to an AgentStateRepository.
    """

    def __init__(
        self,
        state_dir: Path | None = None,
        repository: AgentStateRepository | None = None,
    ) -> None:
        """Initialize state manager.

        Args:
            state_dir: Deprecated. Directory for state storage.
            repository: Optional AgentStateRepository. Defaults via get_agent_state_repository()
        """
        if state_dir is not None:
            warnings.warn(
                "AgentStateManager 'state_dir' parameter is deprecated. "
                "State is persisted via the AgentStateRepository backend.",
                DeprecationWarning,
                stacklevel=2,
            )
        self.state_dir = state_dir or Path("./agent_state")

        if repository is not None:
            self._repository = repository
        else:
            from mcp_server_langgraph.core.dependencies import get_agent_state_repository

            self._repository = get_agent_state_repository()

    async def save_state(
        self,
        session_id: str,
        state: dict[str, Any],
    ) -> None:
        """Save state for session resumption.

        Args:
            session_id: Session identifier
            state: State to save
        """
        await self._repository.save(session_id, state)

    async def resume_session(
        self,
        session_id: str,
    ) -> dict[str, Any] | None:
        """Resume from saved state.

        Args:
            session_id: Session identifier

        Returns:
            Saved state if found, None otherwise
        """
        return await self._repository.get(session_id)

    async def checkpoint(
        self,
        session_id: str,
        phase: str,
        summary: str,
    ) -> None:
        """Create checkpoint before context limit.

        Args:
            session_id: Session identifier
            phase: Phase name
            summary: Phase summary
        """
        await self._repository.checkpoint(session_id, phase, summary)

    async def list_sessions(self) -> list[str]:
        """List all session IDs.

        Returns:
            List of session identifiers
        """
        return await self._repository.list_sessions()

    async def delete_session(self, session_id: str) -> None:
        """Delete a session state.

        Args:
            session_id: Session identifier
        """
        await self._repository.delete(session_id)
