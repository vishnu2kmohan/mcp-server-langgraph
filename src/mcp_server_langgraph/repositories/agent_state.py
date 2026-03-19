"""
Agent State Repository

Abstract interface and in-memory implementation for ephemeral session state.
Supports Redis backend via RedisAgentStateRepository (separate module).

Note: No GDPR list_by_user/delete_by_user — agent state is ephemeral (TTL 24h),
automatically purged by Redis. No long-term PII retention.
"""

from __future__ import annotations

from abc import ABC, abstractmethod
from datetime import UTC, datetime
from typing import Any


class AgentStateRepository(ABC):
    """Abstract base class for agent state repository."""

    @abstractmethod
    async def save(self, session_id: str, state: dict[str, Any]) -> None:
        """Save state for a session.

        Args:
            session_id: Session identifier
            state: State dictionary to persist
        """
        pass

    @abstractmethod
    async def get(self, session_id: str) -> dict[str, Any] | None:
        """Get state for a session.

        Args:
            session_id: Session identifier

        Returns:
            State dictionary if found, None otherwise
        """
        pass

    @abstractmethod
    async def checkpoint(self, session_id: str, phase: str, summary: str) -> None:
        """Create a checkpoint within a session's state.

        Args:
            session_id: Session identifier
            phase: Phase name
            summary: Phase summary
        """
        pass

    @abstractmethod
    async def list_sessions(self) -> list[str]:
        """List all session IDs with stored state.

        Returns:
            List of session identifiers
        """
        pass

    @abstractmethod
    async def delete(self, session_id: str) -> None:
        """Delete state for a session.

        Args:
            session_id: Session identifier
        """
        pass


class InMemoryAgentStateRepository(AgentStateRepository):
    """In-memory implementation for testing."""

    def __init__(self) -> None:
        self._states: dict[str, dict[str, Any]] = {}

    async def save(self, session_id: str, state: dict[str, Any]) -> None:
        self._states[session_id] = state

    async def get(self, session_id: str) -> dict[str, Any] | None:
        return self._states.get(session_id)

    async def checkpoint(self, session_id: str, phase: str, summary: str) -> None:
        state = self._states.get(session_id, {})

        if "checkpoints" not in state:
            state["checkpoints"] = []

        state["checkpoints"].append(
            {
                "phase": phase,
                "summary": summary,
                "timestamp": datetime.now(UTC).isoformat(),
            }
        )

        self._states[session_id] = state

    async def list_sessions(self) -> list[str]:
        return list(self._states.keys())

    async def delete(self, session_id: str) -> None:
        self._states.pop(session_id, None)
