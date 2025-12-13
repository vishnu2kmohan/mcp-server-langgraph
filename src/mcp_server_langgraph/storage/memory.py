from __future__ import annotations

"""
In-Memory Storage Backend

Provides in-memory repository implementations for testing and development.
Not suitable for production use.
"""

import builtins
from datetime import UTC, datetime
from typing import Any
from uuid import uuid4

from mcp_server_langgraph.storage.base import SessionRepository, WorkflowRepository
from mcp_server_langgraph.storage.models import (
    Message,
    Session,
    SessionSummary,
    Workflow,
    WorkflowSummary,
)


class InMemoryWorkflowRepository(WorkflowRepository):
    """In-memory implementation of WorkflowRepository."""

    def __init__(self) -> None:
        self._workflows: dict[str, Workflow] = {}

    async def create(self, entity: Workflow) -> Workflow:
        """Create a new workflow."""
        self._workflows[entity.id] = entity
        return entity

    async def get(self, entity_id: str) -> Workflow | None:
        """Get a workflow by ID."""
        return self._workflows.get(entity_id)

    async def update(self, entity_id: str, data: dict[str, Any]) -> Workflow | None:
        """Update a workflow. Returns None if not found."""
        workflow = self._workflows.get(entity_id)
        if workflow is None:
            return None

        # Update fields
        for key, value in data.items():
            if hasattr(workflow, key):
                setattr(workflow, key, value)
        workflow.updated_at = datetime.now(UTC)

        self._workflows[entity_id] = workflow
        return workflow

    async def delete(self, entity_id: str) -> bool:
        """Delete a workflow. Returns True if deleted."""
        if entity_id in self._workflows:
            del self._workflows[entity_id]
            return True
        return False

    async def list(
        self,
        cursor: str | None = None,
        limit: int = 20,
        user_id: str | None = None,
        **filters: Any,
    ) -> tuple[list[WorkflowSummary], str | None]:
        """List workflows with pagination."""
        # Filter workflows
        workflows = list(self._workflows.values())
        if user_id:
            workflows = [w for w in workflows if w.user_id == user_id]

        # Sort by created_at descending
        workflows.sort(key=lambda w: w.created_at, reverse=True)

        # Apply cursor-based pagination
        start_idx = 0
        if cursor:
            for idx, w in enumerate(workflows):
                if w.id == cursor:
                    start_idx = idx + 1
                    break

        # Get page
        page = workflows[start_idx : start_idx + limit]
        next_cursor = page[-1].id if len(page) == limit else None

        # Convert to summaries
        summaries = [w.to_summary() for w in page]
        return summaries, next_cursor


class InMemorySessionRepository(SessionRepository):
    """In-memory implementation of SessionRepository."""

    def __init__(self) -> None:
        self._sessions: dict[str, Session] = {}

    async def create(self, entity: Session) -> Session:
        """Create a new session."""
        self._sessions[entity.session_id] = entity
        return entity

    async def get(self, entity_id: str) -> Session | None:
        """Get a session by ID."""
        return self._sessions.get(entity_id)

    async def update(self, entity_id: str, data: dict[str, Any]) -> Session | None:
        """Update a session. Returns None if not found."""
        session = self._sessions.get(entity_id)
        if session is None:
            return None

        # Update fields
        for key, value in data.items():
            if hasattr(session, key):
                setattr(session, key, value)
        session.updated_at = datetime.now(UTC)

        self._sessions[entity_id] = session
        return session

    async def delete(self, entity_id: str) -> bool:
        """Delete a session. Returns True if deleted."""
        if entity_id in self._sessions:
            del self._sessions[entity_id]
            return True
        return False

    async def list(
        self,
        cursor: str | None = None,
        limit: int = 20,
        user_id: str | None = None,
        workflow_id: str | None = None,
        **filters: Any,
    ) -> tuple[list[SessionSummary], str | None]:
        """List sessions with pagination."""
        # Filter sessions
        sessions = list(self._sessions.values())
        if user_id:
            sessions = [s for s in sessions if s.user_id == user_id]
        if workflow_id:
            sessions = [s for s in sessions if s.workflow_id == workflow_id]

        # Sort by created_at descending
        sessions.sort(key=lambda s: s.created_at, reverse=True)

        # Apply cursor-based pagination
        start_idx = 0
        if cursor:
            for idx, s in enumerate(sessions):
                if s.session_id == cursor:
                    start_idx = idx + 1
                    break

        # Get page
        page = sessions[start_idx : start_idx + limit]
        next_cursor = page[-1].session_id if len(page) == limit else None

        # Convert to summaries
        summaries = [s.to_summary() for s in page]
        return summaries, next_cursor

    async def add_message(self, session_id: str, message: dict[str, Any]) -> dict[str, Any] | None:
        """Add a message to a session."""
        session = self._sessions.get(session_id)
        if session is None:
            return None

        # Create message
        msg = Message(
            message_id=message.get("message_id", str(uuid4())),
            role=message["role"],
            content=message["content"],
            metadata=message.get("metadata", {}),
        )
        session.messages.append(msg)
        session.updated_at = datetime.now(UTC)

        return msg.model_dump()

    async def get_messages(self, session_id: str) -> builtins.list[dict[str, Any]] | None:
        """Get all messages for a session."""
        session = self._sessions.get(session_id)
        if session is None:
            return None

        return [m.model_dump() for m in session.messages]
