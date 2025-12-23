"""
Cross-Session State Management

Persistent state across agent sessions for continuity.

Usage:
    from mcp_server_langgraph.sdk.state import AgentStateManager

    manager = AgentStateManager(state_dir=Path("./state"))
    await manager.save_state("session-1", {"progress": "50%"})
    state = await manager.resume_session("session-1")
"""

from __future__ import annotations

import json
from datetime import UTC, datetime
from pathlib import Path
from typing import Any


class AgentStateManager:
    """Persistent state across agent sessions.

    Enables session resumption and checkpoint-based context recovery.
    """

    def __init__(self, state_dir: Path | None = None) -> None:
        """Initialize state manager.

        Args:
            state_dir: Directory for state storage
        """
        self.state_dir = state_dir or Path("./agent_state")
        self._states: dict[str, dict[str, Any]] = {}

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
        self._states[session_id] = {
            "state": state,
            "updated_at": datetime.now(UTC).isoformat(),
        }

        # Persist to disk
        await self._persist()

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
        # Load from disk if not in memory
        if session_id not in self._states:
            await self._load()

        entry = self._states.get(session_id)
        if entry:
            return entry.get("state")
        return None

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
        state = await self.resume_session(session_id) or {}

        if "checkpoints" not in state:
            state["checkpoints"] = []

        state["checkpoints"].append(
            {
                "phase": phase,
                "summary": summary,
                "timestamp": datetime.now(UTC).isoformat(),
            }
        )

        await self.save_state(session_id, state)

    async def list_sessions(self) -> list[str]:
        """List all session IDs.

        Returns:
            List of session identifiers
        """
        await self._load()
        return list(self._states.keys())

    async def delete_session(self, session_id: str) -> None:
        """Delete a session state.

        Args:
            session_id: Session identifier
        """
        self._states.pop(session_id, None)
        await self._persist()

    async def _persist(self) -> None:
        """Persist states to disk."""
        self.state_dir.mkdir(parents=True, exist_ok=True)
        state_file = self.state_dir / "sessions.json"
        state_file.write_text(json.dumps(self._states, indent=2, default=str))

    async def _load(self) -> None:
        """Load states from disk."""
        state_file = self.state_dir / "sessions.json"
        if state_file.exists():
            self._states = json.loads(state_file.read_text())
