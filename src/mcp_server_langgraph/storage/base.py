"""
Base Repository Classes

Provides abstract base classes for repository implementations.
Supports PostgreSQL, Redis, and in-memory backends.
"""

from __future__ import annotations

import builtins
from abc import ABC, abstractmethod
from typing import Any, Generic, TypeVar

from mcp_server_langgraph.storage.models import (
    Session,
    SessionSummary,
    Workflow,
    WorkflowSummary,
)


T = TypeVar("T")
S = TypeVar("S")  # Summary type


class BaseRepository(ABC, Generic[T, S]):
    """Abstract base class for repositories."""

    @abstractmethod
    async def create(self, entity: T) -> T:
        """Create a new entity."""
        pass

    @abstractmethod
    async def get(self, entity_id: str) -> T | None:
        """Get an entity by ID."""
        pass

    @abstractmethod
    async def update(self, entity_id: str, data: dict[str, Any]) -> T | None:
        """Update an entity. Returns None if not found."""
        pass

    @abstractmethod
    async def delete(self, entity_id: str) -> bool:
        """Delete an entity. Returns True if deleted."""
        pass

    @abstractmethod
    async def list(
        self,
        cursor: str | None = None,
        limit: int = 20,
        **filters: Any,
    ) -> tuple[list[S], str | None]:
        """List entities with pagination. Returns (summaries, next_cursor)."""
        pass


class WorkflowRepository(BaseRepository[Workflow, WorkflowSummary]):
    """Repository for Workflow entities."""

    @abstractmethod
    async def create(self, entity: Workflow) -> Workflow:
        """Create a new workflow."""
        pass

    @abstractmethod
    async def get(self, entity_id: str) -> Workflow | None:
        """Get a workflow by ID."""
        pass

    @abstractmethod
    async def update(self, entity_id: str, data: dict[str, Any]) -> Workflow | None:
        """Update a workflow. Returns None if not found."""
        pass

    @abstractmethod
    async def delete(self, entity_id: str) -> bool:
        """Delete a workflow. Returns True if deleted."""
        pass

    @abstractmethod
    async def list(
        self,
        cursor: str | None = None,
        limit: int = 20,
        user_id: str | None = None,
        **filters: Any,
    ) -> tuple[list[WorkflowSummary], str | None]:
        """List workflows with pagination. Returns (summaries, next_cursor)."""
        pass


class SessionRepository(BaseRepository[Session, SessionSummary]):
    """Repository for Session entities."""

    @abstractmethod
    async def create(self, entity: Session) -> Session:
        """Create a new session."""
        pass

    @abstractmethod
    async def get(self, entity_id: str) -> Session | None:
        """Get a session by ID."""
        pass

    @abstractmethod
    async def update(self, entity_id: str, data: dict[str, Any]) -> Session | None:
        """Update a session. Returns None if not found."""
        pass

    @abstractmethod
    async def delete(self, entity_id: str) -> bool:
        """Delete a session. Returns True if deleted."""
        pass

    @abstractmethod
    async def list(
        self,
        cursor: str | None = None,
        limit: int = 20,
        user_id: str | None = None,
        workflow_id: str | None = None,
        **filters: Any,
    ) -> tuple[list[SessionSummary], str | None]:
        """List sessions with pagination. Returns (summaries, next_cursor)."""
        pass

    @abstractmethod
    async def add_message(self, session_id: str, message: dict[str, Any]) -> dict[str, Any] | None:
        """Add a message to a session. Returns None if session not found."""
        pass

    @abstractmethod
    async def get_messages(self, session_id: str) -> builtins.list[dict[str, Any]] | None:
        """Get all messages for a session. Returns None if session not found."""
        pass
