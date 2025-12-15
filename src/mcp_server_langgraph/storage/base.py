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
    Project,
    ProjectConnection,
    ProjectSummary,
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


class ProjectRepository(BaseRepository[Project, ProjectSummary]):
    """Repository for Project entities (Unified Workspace Paradigm)."""

    @abstractmethod
    async def create(self, entity: Project) -> Project:
        """Create a new project."""
        pass

    @abstractmethod
    async def get(self, entity_id: str) -> Project | None:
        """Get a project by ID with all child resources."""
        pass

    @abstractmethod
    async def update(self, entity_id: str, data: dict[str, Any]) -> Project | None:
        """Update a project. Returns None if not found."""
        pass

    @abstractmethod
    async def delete(self, entity_id: str, cascade: bool = False) -> bool:
        """Delete a project. If cascade=True, also deletes child resources."""
        pass

    @abstractmethod
    async def list(
        self,
        cursor: str | None = None,
        limit: int = 20,
        owner_id: str | None = None,
        organization_id: str | None = None,
        **filters: Any,
    ) -> tuple[list[ProjectSummary], str | None]:
        """List projects with pagination. Returns (summaries, next_cursor)."""
        pass

    # Child resource management

    @abstractmethod
    async def add_workflow(self, project_id: str, workflow_id: str, workflow_name: str) -> Project | None:
        """Add a workflow to a project. Returns None if project not found."""
        pass

    @abstractmethod
    async def remove_workflow(self, project_id: str, workflow_id: str) -> Project | None:
        """Remove a workflow from a project. Returns None if project not found."""
        pass

    @abstractmethod
    async def add_session(self, project_id: str, session_id: str, session_name: str) -> Project | None:
        """Add a session to a project. Returns None if project not found."""
        pass

    @abstractmethod
    async def remove_session(self, project_id: str, session_id: str) -> Project | None:
        """Remove a session from a project. Returns None if project not found."""
        pass

    @abstractmethod
    async def add_connection(self, project_id: str, connection: ProjectConnection) -> Project | None:
        """Add a connection to a project. Returns None if project not found."""
        pass

    @abstractmethod
    async def remove_connection(self, project_id: str, connection_id: str) -> Project | None:
        """Remove a connection from a project. Returns None if project not found."""
        pass

    # Member management

    @abstractmethod
    async def add_member(self, project_id: str, user_id: str, role: str) -> Project | None:
        """Add a member to a project. Returns None if project not found."""
        pass

    @abstractmethod
    async def remove_member(self, project_id: str, user_id: str) -> Project | None:
        """Remove a member from a project. Returns None if project not found."""
        pass

    @abstractmethod
    async def get_member_role(self, project_id: str, user_id: str) -> str | None:
        """Get a member's role in a project. Returns None if not a member."""
        pass
