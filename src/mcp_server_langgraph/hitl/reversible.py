"""Reversible actions for HITL workflows.

Provides reversible action tracking with undo capabilities:
- ReversibleAction: Wraps execute/undo function pairs
- ActionState: Tracks action lifecycle states
- ActionHistoryStore: Stores and manages action history

This enables safe human-in-the-loop workflows where actions
can be rolled back if needed.

ADR Reference: adr/adr-0092-hierarchical-capability-architecture.md
"""

from __future__ import annotations

from datetime import datetime, UTC
from enum import StrEnum
from typing import Any, Awaitable, Callable


class ActionState(StrEnum):
    """State of a reversible action.

    Lifecycle: PENDING -> EXECUTED -> UNDONE
                      -> FAILED
    """

    PENDING = "pending"
    EXECUTED = "executed"
    UNDONE = "undone"
    FAILED = "failed"


class ReversibleAction:
    """A reversible action with execute and undo capabilities.

    Attributes:
        action_id: Unique identifier for this action
        action_type: Type/category of action (e.g., 'file_write', 'database_update')
        description: Human-readable description of the action
        execute_fn: Async function to execute the action
        undo_fn: Async function to undo/rollback the action
        state: Current state of the action
        executed_at: Timestamp when action was executed
        undone_at: Timestamp when action was undone
    """

    def __init__(
        self,
        *,
        action_id: str,
        action_type: str,
        description: str,
        execute_fn: Callable[[], Awaitable[Any]],
        undo_fn: Callable[[], Awaitable[Any]],
    ) -> None:
        """Initialize a ReversibleAction.

        Args:
            action_id: Unique identifier for this action
            action_type: Type/category of action
            description: Human-readable description
            execute_fn: Async function to execute the action
            undo_fn: Async function to undo the action
        """
        self._action_id = action_id
        self._action_type = action_type
        self._description = description
        self._execute_fn = execute_fn
        self._undo_fn = undo_fn
        self._state = ActionState.PENDING
        self._executed_at: datetime | None = None
        self._undone_at: datetime | None = None

    @property
    def action_id(self) -> str:
        """Get the action ID."""
        return self._action_id

    @property
    def action_type(self) -> str:
        """Get the action type."""
        return self._action_type

    @property
    def description(self) -> str:
        """Get the action description."""
        return self._description

    @property
    def execute_fn(self) -> Callable[[], Awaitable[Any]]:
        """Get the execute function."""
        return self._execute_fn

    @property
    def undo_fn(self) -> Callable[[], Awaitable[Any]]:
        """Get the undo function."""
        return self._undo_fn

    @property
    def state(self) -> ActionState:
        """Get the current state."""
        return self._state

    @property
    def executed_at(self) -> datetime | None:
        """Get the execution timestamp."""
        return self._executed_at

    @property
    def undone_at(self) -> datetime | None:
        """Get the undo timestamp."""
        return self._undone_at

    async def execute(self) -> Any:
        """Execute the action.

        Returns:
            Result from the execute function

        Raises:
            Exception: If execute_fn raises an exception
        """
        try:
            result = await self._execute_fn()
            self._state = ActionState.EXECUTED
            self._executed_at = datetime.now(UTC)
            return result
        except Exception:
            self._state = ActionState.FAILED
            raise

    async def undo(self) -> Any:
        """Undo the action.

        Returns:
            Result from the undo function

        Raises:
            Exception: If undo_fn raises an exception
        """
        result = await self._undo_fn()
        self._state = ActionState.UNDONE
        self._undone_at = datetime.now(UTC)
        return result


class ActionHistoryStore:
    """In-memory store for action history.

    Stores reversible actions indexed by action_id and session_id
    for tracking and undo capabilities.
    """

    def __init__(self) -> None:
        """Initialize the ActionHistoryStore."""
        self._actions: dict[str, ReversibleAction] = {}
        self._session_actions: dict[str, list[str]] = {}

    def add(self, action: ReversibleAction, *, session_id: str) -> None:
        """Add an action to the store.

        Args:
            action: The ReversibleAction to store
            session_id: Session identifier to associate the action with
        """
        self._actions[action.action_id] = action

        if session_id not in self._session_actions:
            self._session_actions[session_id] = []
        self._session_actions[session_id].append(action.action_id)

    def get(self, action_id: str) -> ReversibleAction | None:
        """Get an action by ID.

        Args:
            action_id: The action ID to look up

        Returns:
            The ReversibleAction if found, None otherwise
        """
        return self._actions.get(action_id)

    def list_for_session(self, session_id: str) -> list[ReversibleAction]:
        """List all actions for a session.

        Args:
            session_id: Session identifier to filter by

        Returns:
            List of ReversibleActions for the session
        """
        action_ids = self._session_actions.get(session_id, [])
        return [self._actions[aid] for aid in action_ids if aid in self._actions]

    def get_undoable(self, session_id: str) -> list[ReversibleAction]:
        """Get actions that can be undone for a session.

        Only returns actions in EXECUTED state (not PENDING, UNDONE, or FAILED).

        Args:
            session_id: Session identifier to filter by

        Returns:
            List of undoable ReversibleActions
        """
        actions = self.list_for_session(session_id)
        return [a for a in actions if a.state == ActionState.EXECUTED]

    async def undo(self, action_id: str) -> Any:
        """Undo an action by ID.

        Args:
            action_id: The action ID to undo

        Returns:
            Result from the action's undo function

        Raises:
            KeyError: If action_id is not found
        """
        action = self._actions.get(action_id)
        if action is None:
            raise KeyError(f"Action not found: {action_id}")
        return await action.undo()
