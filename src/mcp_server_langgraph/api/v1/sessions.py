"""
Sessions Router

Provides CRUD operations for chat session management under /api/v1/sessions/*.

This consolidates session functionality from playground into a unified API.

Usage:
    GET /api/v1/sessions - List all sessions (with pagination)
    GET /api/v1/sessions/{id} - Get a specific session
    POST /api/v1/sessions - Create a new session
    DELETE /api/v1/sessions/{id} - Delete a session
    GET /api/v1/sessions/{id}/messages - Get messages in a session
    POST /api/v1/sessions/{id}/messages - Add a message to a session
    POST /api/v1/sessions/generate-title - Generate a session title from a message
"""

import logging
import uuid
from abc import ABC, abstractmethod
from datetime import UTC, datetime
from enum import Enum
from typing import Annotated, Any, Literal

from fastapi import APIRouter, Depends, HTTPException, Query, status
from pydantic import BaseModel, Field

from mcp_server_langgraph.auth.middleware import get_current_user


# Enums for type-safe status and role values


class SessionStatus(str, Enum):
    """Session status enum for type safety."""

    active = "active"
    archived = "archived"
    deleted = "deleted"


class MessageRole(str, Enum):
    """Message role enum for type safety."""

    user = "user"
    assistant = "assistant"
    system = "system"


from mcp_server_langgraph.api.pagination import (
    CursorPaginatedResponse,
    CursorPaginationMetadata,
)
from mcp_server_langgraph.storage.session import (
    PostgresSessionManager,
    RedisSessionManager,
)

logger = logging.getLogger(__name__)


# Type alias for authenticated user dependency
CurrentUser = Annotated[dict[str, Any], Depends(get_current_user)]


def _get_user_id(current_user: dict[str, Any]) -> str:
    """
    Extract user ID from the current user context.

    Tries 'sub' claim first (JWT standard), then 'user_id', then 'preferred_username'.
    """
    return current_user.get("sub") or current_user.get("user_id") or current_user.get("preferred_username") or "anonymous"


sessions_router = APIRouter(tags=["sessions"])


# Request/Response Models


class MessageRequest(BaseModel):
    """Request body for adding a message."""

    role: Literal["user", "assistant", "system"] = Field(description="Message role")
    content: str = Field(description="Message content", min_length=1)


class MessageResponse(BaseModel):
    """Response model for a message."""

    message_id: str = Field(description="Unique message ID")
    role: MessageRole = Field(description="Message role")
    content: str = Field(description="Message content")
    timestamp: str | None = Field(default=None, description="Message timestamp")


class SessionCreateRequest(BaseModel):
    """Request body for creating a session."""

    name: str | None = Field(default=None, description="Session name", max_length=255)
    workflow_id: str | None = Field(default=None, description="Associated workflow ID")
    # Deprecated: use 'name' instead. Kept for backward compatibility.
    title: str | None = Field(default=None, description="Session title (deprecated, use 'name')", max_length=255)

    def get_name(self) -> str | None:
        """Get session name, preferring 'name' over deprecated 'title'."""
        return self.name or self.title


class SessionResponse(BaseModel):
    """Response model for a session."""

    id: str = Field(description="Session ID")
    name: str | None = Field(default=None, description="Session name")
    workflow_id: str | None = Field(default=None, description="Associated workflow ID")
    messages: list[dict[str, Any]] = Field(default_factory=list, description="Session messages")
    created_at: str | None = Field(default=None, description="Creation timestamp")
    updated_at: str | None = Field(default=None, description="Last update timestamp")
    status: SessionStatus = Field(default=SessionStatus.active, description="Session status")


# Service Interface (ABC for proper typing)


class SessionService(ABC):
    """Abstract interface for session operations. Implemented by storage layer."""

    @abstractmethod
    async def list_sessions(
        self,
        user_id: str,
        cursor: str | None = None,
        limit: int = 20,
        workflow_id: str | None = None,
        status: str | None = None,
        search: str | None = None,
        sort_by: str | None = "created_at",
        sort_order: str | None = "desc",
    ) -> tuple[list[dict[str, Any]], str | None]:
        """List sessions with pagination, filtering, search, and sorting.

        Args:
            user_id: User ID for scoping sessions (REQUIRED for security)
            cursor: Pagination cursor (session ID to start after)
            limit: Maximum number of sessions to return
            workflow_id: Filter by workflow ID
            status: Filter by session status
            search: Search in session title
            sort_by: Field to sort by (title, created_at, updated_at)
            sort_order: Sort order (asc, desc)

        Returns (sessions, next_cursor).
        """
        ...

    @abstractmethod
    async def get_session(self, session_id: str, user_id: str) -> dict[str, Any] | None:
        """Get a session by ID. Returns None if not found or not owned by user."""
        ...

    @abstractmethod
    async def create_session(self, session_data: dict[str, Any], user_id: str) -> dict[str, Any]:
        """Create a new session associated with user. Returns the created session."""
        ...

    @abstractmethod
    async def delete_session(self, session_id: str, user_id: str) -> bool:
        """Delete a session. Returns True if deleted, False if not found or not owned."""
        ...

    @abstractmethod
    async def get_session_messages(self, session_id: str) -> list[dict[str, Any]] | None:
        """Get all messages in a session. Returns None if session not found."""
        ...

    @abstractmethod
    async def add_message(self, session_id: str, message_data: dict[str, Any]) -> dict[str, Any] | None:
        """Add a message to a session. Returns None if session not found."""
        ...

    @abstractmethod
    async def clear_messages(self, session_id: str) -> bool:
        """Clear all messages in a session. Returns True if cleared, False if session not found."""
        ...


class InMemorySessionService(SessionService):
    """In-memory implementation for development and testing."""

    def __init__(self) -> None:
        self._sessions: dict[str, dict[str, Any]] = {}

    async def list_sessions(
        self,
        user_id: str,
        cursor: str | None = None,
        limit: int = 20,
        workflow_id: str | None = None,
        status: str | None = None,
        search: str | None = None,
        sort_by: str | None = "created_at",
        sort_order: str | None = "desc",
    ) -> tuple[list[dict[str, Any]], str | None]:
        """List sessions with pagination, filtering, search, and sorting."""
        # Get sessions owned by user (SECURITY: user scoping)
        sessions = [s for s in self._sessions.values() if s.get("user_id") == user_id]

        # Apply filters
        if workflow_id:
            sessions = [s for s in sessions if s.get("workflow_id") == workflow_id]
        if status:
            sessions = [s for s in sessions if s.get("status") == status]

        # Apply search (case-insensitive on name)
        if search:
            search_lower = search.lower()
            sessions = [s for s in sessions if s.get("name") and search_lower in s.get("name", "").lower()]

        # Apply sorting
        reverse = sort_order == "desc"
        if sort_by in ("title", "name"):  # 'title' is deprecated alias for 'name'
            sessions.sort(key=lambda s: (s.get("name") or "").lower(), reverse=reverse)
        elif sort_by == "updated_at":
            sessions.sort(key=lambda s: s.get("updated_at", ""), reverse=reverse)
        else:  # Default: created_at
            sessions.sort(key=lambda s: s.get("created_at", ""), reverse=reverse)

        # Apply cursor-based pagination
        start_idx = 0
        if cursor:
            for i, s in enumerate(sessions):
                if s["id"] == cursor:
                    start_idx = i + 1
                    break

        # Slice to limit
        paginated = sessions[start_idx : start_idx + limit]

        # Determine next cursor
        next_cursor = None
        if start_idx + limit < len(sessions):
            next_cursor = paginated[-1]["id"] if paginated else None

        return paginated, next_cursor

    async def get_session(self, session_id: str, user_id: str) -> dict[str, Any] | None:
        """Get a session by ID. Returns None if not found or not owned by user."""
        session = self._sessions.get(session_id)
        # SECURITY: Verify ownership
        if session is None or session.get("user_id") != user_id:
            return None
        return session

    async def create_session(self, session_data: dict[str, Any], user_id: str) -> dict[str, Any]:
        """Create a new session associated with user."""
        session_id = str(uuid.uuid4())
        now = datetime.now(UTC).isoformat()

        # Support both 'title' (legacy) and 'name' (new) input
        name = session_data.get("name") or session_data.get("title")

        session: dict[str, Any] = {
            "id": session_id,
            "name": name,
            "user_id": user_id,  # SECURITY: Track ownership
            "workflow_id": session_data.get("workflow_id"),
            "messages": [],
            "created_at": now,
            "updated_at": now,
            "status": SessionStatus.active,
        }

        self._sessions[session_id] = session
        return session

    async def delete_session(self, session_id: str, user_id: str) -> bool:
        """Delete a session. Only owner can delete."""
        session = self._sessions.get(session_id)
        # SECURITY: Verify ownership before deletion
        if session is None or session.get("user_id") != user_id:
            return False
        del self._sessions[session_id]
        return True

    async def get_session_messages(self, session_id: str) -> list[dict[str, Any]] | None:
        """Get all messages in a session."""
        session = self._sessions.get(session_id)
        if session is None:
            return None
        messages: list[dict[str, Any]] = session.get("messages", [])
        return messages

    async def add_message(self, session_id: str, message_data: dict[str, Any]) -> dict[str, Any] | None:
        """Add a message to a session."""
        session = self._sessions.get(session_id)
        if session is None:
            return None

        message = {
            "message_id": str(uuid.uuid4()),
            "role": message_data["role"],
            "content": message_data["content"],
            "timestamp": datetime.now(UTC).isoformat(),
        }

        session["messages"].append(message)
        session["updated_at"] = datetime.now(UTC).isoformat()

        return message

    async def clear_messages(self, session_id: str) -> bool:
        """Clear all messages in a session."""
        session = self._sessions.get(session_id)
        if session is None:
            return False

        session["messages"] = []
        session["updated_at"] = datetime.now(UTC).isoformat()
        return True


class RedisSessionService(SessionService):
    """Redis-backed implementation for production use."""

    def __init__(self, manager: RedisSessionManager) -> None:
        self._manager = manager

    async def list_sessions(
        self,
        user_id: str,
        cursor: str | None = None,
        limit: int = 20,
        workflow_id: str | None = None,
        status: str | None = None,
        search: str | None = None,
        sort_by: str | None = "created_at",
        sort_order: str | None = "desc",
    ) -> tuple[list[dict[str, Any]], str | None]:
        """List sessions with pagination, filtering, search, and sorting.

        SECURITY: Sessions are scoped to the authenticated user.
        Uses RedisSessionManager.list_sessions() with user_id for proper scoping.
        """
        # SECURITY: Use user-scoped listing via RedisSessionManager
        # This uses user:{user_id}:sessions index for O(1) lookup per session
        raw_sessions = await self._manager.list_sessions(user_id)

        sessions: list[dict[str, Any]] = []
        for session in raw_sessions:
            session_dict: dict[str, Any] = {
                "id": session.session_id,
                "name": session.name,
                "user_id": session.user_id,
                "workflow_id": None,  # Not supported in current model
                "messages": [
                    {
                        "message_id": m.message_id,
                        "role": m.role,
                        "content": m.content,
                        "timestamp": m.timestamp.isoformat(),
                    }
                    for m in session.messages
                ],
                "created_at": session.created_at.isoformat(),
                "updated_at": session.updated_at.isoformat(),
                "status": SessionStatus.active,
            }
            sessions.append(session_dict)

        # Apply filters
        if workflow_id:
            sessions = [s for s in sessions if s.get("workflow_id") == workflow_id]
        if status:
            sessions = [s for s in sessions if s.get("status") == status]

        # Apply search (case-insensitive on name)
        if search:
            search_lower = search.lower()
            sessions = [s for s in sessions if s.get("name") and search_lower in s.get("name", "").lower()]

        # Apply sorting
        reverse = sort_order == "desc"
        if sort_by in ("title", "name"):  # 'title' is deprecated alias for 'name'
            sessions.sort(key=lambda s: (s.get("name") or "").lower(), reverse=reverse)
        elif sort_by == "updated_at":
            sessions.sort(key=lambda s: s.get("updated_at", ""), reverse=reverse)
        else:  # Default: created_at
            sessions.sort(key=lambda s: s.get("created_at", ""), reverse=reverse)

        # Apply cursor-based pagination
        start_idx = 0
        if cursor:
            for i, s in enumerate(sessions):
                if s["id"] == cursor:
                    start_idx = i + 1
                    break

        paginated = sessions[start_idx : start_idx + limit]
        next_cursor = None
        if start_idx + limit < len(sessions):
            next_cursor = paginated[-1]["id"] if paginated else None

        return paginated, next_cursor

    async def get_session(self, session_id: str, user_id: str) -> dict[str, Any] | None:
        """Get a session by ID. Returns None if not found or not owned by user."""
        session = await self._manager.get_session(session_id)
        if session is None:
            return None

        # SECURITY: Verify ownership
        if session.user_id != user_id:
            return None

        return {
            "id": session.session_id,
            "name": session.name,
            "user_id": session.user_id,
            "workflow_id": None,
            "messages": [
                {
                    "message_id": m.message_id,
                    "role": m.role,
                    "content": m.content,
                    "timestamp": m.timestamp.isoformat(),
                }
                for m in session.messages
            ],
            "created_at": session.created_at.isoformat(),
            "updated_at": session.updated_at.isoformat(),
            "status": SessionStatus.active,
        }

    async def create_session(self, session_data: dict[str, Any], user_id: str) -> dict[str, Any]:
        """Create a new session associated with user."""
        # Support both 'title' (legacy) and 'name' (new) input
        name = session_data.get("name") or session_data.get("title") or "New Session"
        # SECURITY: Pass authenticated user_id to manager
        session = await self._manager.create_session(
            name=name,
            user_id=user_id,
        )

        return {
            "id": session.session_id,
            "name": session.name,
            "user_id": session.user_id,
            "workflow_id": session_data.get("workflow_id"),
            "messages": [],
            "created_at": session.created_at.isoformat(),
            "updated_at": session.updated_at.isoformat(),
            "status": SessionStatus.active,
        }

    async def delete_session(self, session_id: str, user_id: str) -> bool:
        """Delete a session. Only owner can delete."""
        # SECURITY: Verify ownership before deletion
        session = await self._manager.get_session(session_id)
        if session is None or session.user_id != user_id:
            return False
        return await self._manager.delete_session(session_id)

    async def get_session_messages(self, session_id: str) -> list[dict[str, Any]] | None:
        """Get all messages in a session."""
        session = await self._manager.get_session(session_id)
        if session is None:
            return None

        return [
            {
                "message_id": m.message_id,
                "role": m.role,
                "content": m.content,
                "timestamp": m.timestamp.isoformat(),
            }
            for m in session.messages
        ]

    async def add_message(self, session_id: str, message_data: dict[str, Any]) -> dict[str, Any] | None:
        """Add a message to a session."""
        message = await self._manager.add_message(
            session_id=session_id,
            role=message_data["role"],
            content=message_data["content"],
        )

        if message is None:
            return None

        return {
            "message_id": message.message_id,
            "role": message.role,
            "content": message.content,
            "timestamp": message.timestamp.isoformat(),
        }

    async def clear_messages(self, session_id: str) -> bool:
        """Clear all messages in a session."""
        return await self._manager.clear_messages(session_id)


class PostgresSessionService(SessionService):
    """PostgreSQL-backed implementation for production use with ACID guarantees."""

    def __init__(self, manager: PostgresSessionManager) -> None:
        self._manager = manager

    async def list_sessions(
        self,
        user_id: str,
        cursor: str | None = None,
        limit: int = 20,
        workflow_id: str | None = None,
        status: str | None = None,
        search: str | None = None,
        sort_by: str | None = "created_at",
        sort_order: str | None = "desc",
    ) -> tuple[list[dict[str, Any]], str | None]:
        """List sessions with pagination, filtering, search, and sorting.

        SECURITY: Sessions are scoped to the authenticated user.
        """
        # Get sessions scoped to user
        # PostgresSessionManager.list_sessions returns (sessions, next_cursor)
        sessions, next_cursor = await self._manager.list_sessions(user_id=user_id, limit=limit + 1)

        session_dicts: list[dict[str, Any]] = []
        for s in sessions[:limit]:
            session_dicts.append(
                {
                    "id": s.session_id,
                    "name": s.name,
                    "user_id": s.user_id,
                    "workflow_id": None,  # Not supported in current model
                    "messages": [],  # Not loaded for list performance
                    "created_at": s.created_at.isoformat(),
                    "updated_at": s.updated_at.isoformat(),
                    "status": SessionStatus.active,
                }
            )

        # Apply filters (post-query filtering since manager doesn't support them yet)
        if status:
            session_dicts = [s for s in session_dicts if s.get("status") == status]

        # Apply search (case-insensitive on title)
        if search:
            search_lower = search.lower()
            session_dicts = [s for s in session_dicts if s.get("name") and search_lower in s.get("name", "").lower()]

        # Apply sorting (post-query sorting since manager doesn't support it yet)
        reverse = sort_order == "desc"
        if sort_by in ("title", "name"):  # 'title' is deprecated alias for 'name'
            session_dicts.sort(key=lambda s: (s.get("name") or "").lower(), reverse=reverse)
        elif sort_by == "updated_at":
            session_dicts.sort(key=lambda s: s.get("updated_at", ""), reverse=reverse)
        else:  # Default: created_at
            session_dicts.sort(key=lambda s: s.get("created_at", ""), reverse=reverse)

        # Determine next cursor
        next_cursor = None
        if len(sessions) > limit:
            next_cursor = session_dicts[-1]["id"] if session_dicts else None

        return session_dicts, next_cursor

    async def get_session(self, session_id: str, user_id: str) -> dict[str, Any] | None:
        """Get a session by ID. Returns None if not found or not owned by user."""
        session = await self._manager.get_session(session_id)
        if session is None:
            return None

        # SECURITY: Verify ownership
        if session.user_id != user_id:
            return None

        return {
            "id": session.session_id,
            "name": session.name,
            "user_id": session.user_id,
            "workflow_id": None,
            "messages": [
                {
                    "message_id": m.message_id,
                    "role": m.role,
                    "content": m.content,
                    "timestamp": m.timestamp.isoformat(),
                }
                for m in session.messages
            ],
            "created_at": session.created_at.isoformat(),
            "updated_at": session.updated_at.isoformat(),
            "status": SessionStatus.active,
        }

    async def create_session(self, session_data: dict[str, Any], user_id: str) -> dict[str, Any]:
        """Create a new session associated with user."""
        # Support both 'title' (legacy) and 'name' (new) input
        name = session_data.get("name") or session_data.get("title") or "New Session"
        # SECURITY: Pass authenticated user_id to manager
        session = await self._manager.create_session(
            name=name,
            user_id=user_id,
        )

        return {
            "id": session.session_id,
            "name": session.name,
            "user_id": session.user_id,
            "workflow_id": session_data.get("workflow_id"),
            "messages": [],
            "created_at": session.created_at.isoformat(),
            "updated_at": session.updated_at.isoformat(),
            "status": SessionStatus.active,
        }

    async def delete_session(self, session_id: str, user_id: str) -> bool:
        """Delete a session. Only owner can delete."""
        # SECURITY: Verify ownership before deletion
        session = await self._manager.get_session(session_id)
        if session is None or session.user_id != user_id:
            return False
        return await self._manager.delete_session(session_id)

    async def get_session_messages(self, session_id: str) -> list[dict[str, Any]] | None:
        """Get all messages in a session."""
        session = await self._manager.get_session(session_id)
        if session is None:
            return None

        return [
            {
                "message_id": m.message_id,
                "role": m.role,
                "content": m.content,
                "timestamp": m.timestamp.isoformat(),
            }
            for m in session.messages
        ]

    async def add_message(self, session_id: str, message_data: dict[str, Any]) -> dict[str, Any] | None:
        """Add a message to a session."""
        message = await self._manager.add_message(
            session_id=session_id,
            role=message_data["role"],
            content=message_data["content"],
        )

        if message is None:
            return None

        return {
            "message_id": message.message_id,
            "role": message.role,
            "content": message.content,
            "timestamp": message.timestamp.isoformat(),
        }

    async def clear_messages(self, session_id: str) -> bool:
        """Clear all messages in a session."""
        return await self._manager.clear_messages(session_id)


# Service singleton (will be replaced by dependency injection in Phase 4)
_session_service: SessionService | None = None
_redis_client: Any = None  # Store Redis client for cleanup
_postgres_engine: Any = None  # Store Postgres engine for cleanup


async def initialize_session_service() -> SessionService:
    """Initialize the session service with the best available backend.

    Priority: PostgreSQL > Redis > In-Memory

    PostgreSQL is preferred for ACID guarantees and durability.
    Redis is used as a fast cache alternative if Postgres is unavailable.
    In-Memory is the fallback for development/testing without infrastructure.
    """
    import os

    global _session_service, _redis_client, _postgres_engine

    # Check for PostgreSQL DATABASE_URL (preferred for ACID guarantees)
    database_url = os.environ.get("DATABASE_URL")

    if database_url:
        try:
            from mcp_server_langgraph.storage.session import (
                create_postgres_engine,
                init_session_database,
            )

            logger.info(f"Initializing PostgreSQL session service with URL: {database_url[:50]}...")
            _postgres_engine = await create_postgres_engine(database_url)

            # Initialize database schema (creates tables if not exist)
            await init_session_database(_postgres_engine)

            pg_manager = PostgresSessionManager(engine=_postgres_engine)
            _session_service = PostgresSessionService(pg_manager)
            logger.info("PostgreSQL session service initialized successfully")
            return _session_service
        except Exception as e:
            logger.warning(f"Failed to connect to PostgreSQL: {e}")
            # Fall through to try Redis

    # Check for Redis URL (fallback from Postgres)
    redis_url = os.environ.get("REDIS_SESSION_URL")

    if redis_url:
        try:
            import redis.asyncio as redis

            logger.info(f"Initializing Redis session service with URL: {redis_url}")
            _redis_client = redis.from_url(  # type: ignore[no-untyped-call]
                redis_url,
                max_connections=10,
                decode_responses=True,
            )
            # Test connection
            await _redis_client.ping()
            redis_manager = RedisSessionManager(redis_client=_redis_client, ttl_seconds=86400)
            _session_service = RedisSessionService(redis_manager)
            logger.info("Redis session service initialized successfully")
            return _session_service
        except Exception as e:
            logger.warning(f"Failed to connect to Redis: {e}")
            # Fall through to in-memory

    # Fallback to in-memory
    logger.info("No DATABASE_URL or REDIS_SESSION_URL set, using in-memory session service")
    _session_service = InMemorySessionService()
    return _session_service


def get_session_service() -> SessionService:
    """Get the session service instance."""
    global _session_service
    if _session_service is None:
        # Fallback to in-memory if not initialized
        _session_service = InMemorySessionService()
    return _session_service


def set_session_service(service: SessionService) -> None:
    """Set the session service instance (for testing/DI)."""
    global _session_service
    _session_service = service


# Endpoints


@sessions_router.get("/sessions")
async def list_sessions(
    current_user: CurrentUser,
    cursor: str | None = Query(default=None, description="Pagination cursor"),
    limit: int = Query(default=20, ge=1, le=100, description="Items per page"),
    workflow_id: str | None = Query(default=None, description="Filter by workflow ID"),
    status: str | None = Query(default=None, description="Filter by session status (active, archived)"),
    search: str | None = Query(default=None, min_length=1, max_length=500, description="Search in title"),
    sort_by: Literal["name", "title", "created_at", "updated_at"] = Query(
        default="created_at", description="Field to sort by (use 'name', 'title' is deprecated)"
    ),
    sort_order: Literal["asc", "desc"] = Query(default="desc", description="Sort order"),
) -> CursorPaginatedResponse[dict[str, Any]]:
    """
    List all sessions with cursor-based pagination.

    Requires authentication. Returns only sessions owned by the authenticated user.

    Supports:
    - Pagination: cursor, limit
    - Filtering: workflow_id, status
    - Search: search (searches title)
    - Sorting: sort_by, sort_order
    """
    user_id = _get_user_id(current_user)
    service = get_session_service()
    sessions, next_cursor = await service.list_sessions(
        user_id=user_id,
        cursor=cursor,
        limit=limit,
        workflow_id=workflow_id,
        status=status,
        search=search,
        sort_by=sort_by,
        sort_order=sort_order,
    )

    # Build pagination metadata
    has_next = next_cursor is not None
    pagination = CursorPaginationMetadata(
        next_cursor=next_cursor,
        prev_cursor=None,
        has_next=has_next,
        has_prev=cursor is not None,
        count=len(sessions),
    )

    return CursorPaginatedResponse(data=sessions, pagination=pagination)


@sessions_router.get("/sessions/{session_id}")
async def get_session(session_id: str, current_user: CurrentUser) -> SessionResponse:
    """
    Get a specific session by ID.

    Requires authentication. Returns 404 if session not found or not owned by user.
    """
    user_id = _get_user_id(current_user)
    service = get_session_service()
    session = await service.get_session(session_id, user_id)

    if session is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Session {session_id} not found",
        )

    return SessionResponse(**session)


@sessions_router.post("/sessions", status_code=status.HTTP_201_CREATED)
async def create_session(request: SessionCreateRequest, current_user: CurrentUser) -> SessionResponse:
    """
    Create a new session.

    Requires authentication. The session is associated with the authenticated user.
    """
    user_id = _get_user_id(current_user)
    service = get_session_service()
    session_data = request.model_dump()
    session = await service.create_session(session_data, user_id)

    return SessionResponse(**session)


@sessions_router.delete("/sessions/{session_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_session(session_id: str, current_user: CurrentUser) -> None:
    """
    Delete a session.

    Requires authentication. Only the session owner can delete it.
    """
    user_id = _get_user_id(current_user)
    service = get_session_service()
    deleted = await service.delete_session(session_id, user_id)

    if not deleted:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Session {session_id} not found",
        )


@sessions_router.get("/sessions/{session_id}/messages")
async def get_session_messages(session_id: str, current_user: CurrentUser) -> list[dict[str, Any]]:
    """
    Get all messages in a session.

    Requires authentication. Returns 404 if session not found or not owned by user.
    """
    user_id = _get_user_id(current_user)
    service = get_session_service()

    # SECURITY: Verify ownership first
    session = await service.get_session(session_id, user_id)
    if session is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Session {session_id} not found",
        )

    messages = await service.get_session_messages(session_id)
    return messages or []


@sessions_router.post("/sessions/{session_id}/messages", status_code=status.HTTP_201_CREATED)
async def add_message(session_id: str, request: MessageRequest, current_user: CurrentUser) -> dict[str, Any]:
    """
    Add a message to a session.

    Requires authentication. Only the session owner can add messages.
    """
    user_id = _get_user_id(current_user)
    service = get_session_service()

    # SECURITY: Verify ownership first
    session = await service.get_session(session_id, user_id)
    if session is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Session {session_id} not found",
        )

    message_data = request.model_dump()
    message = await service.add_message(session_id, message_data)

    if message is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Session {session_id} not found",
        )

    return message


@sessions_router.delete("/sessions/{session_id}/messages", status_code=status.HTTP_204_NO_CONTENT)
async def clear_messages(session_id: str, current_user: CurrentUser) -> None:
    """
    Clear all messages in a session.

    Requires authentication. Only the session owner can clear messages.
    """
    user_id = _get_user_id(current_user)
    service = get_session_service()

    # SECURITY: Verify ownership first
    session = await service.get_session(session_id, user_id)
    if session is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Session {session_id} not found",
        )

    cleared = await service.clear_messages(session_id)

    if not cleared:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Session {session_id} not found",
        )


class GenerateTitleRequest(BaseModel):
    """Request body for generating a session title."""

    message: str = Field(description="The user's first message to generate a title from", min_length=1, max_length=2000)


class GenerateTitleResponse(BaseModel):
    """Response model for generated title."""

    title: str = Field(description="Generated session title")


@sessions_router.post("/sessions/generate-title")
async def generate_title(request: GenerateTitleRequest) -> GenerateTitleResponse:
    """
    Generate a session title from a user message.

    Uses AI to analyze the message and generate a concise, descriptive title.
    This is typically called after the user sends their first message in a session.

    Returns a title of max 50 characters.
    """
    from mcp_server_langgraph.studio.ai.title_generator import generate_session_title

    title = await generate_session_title(request.message)
    return GenerateTitleResponse(title=title)
