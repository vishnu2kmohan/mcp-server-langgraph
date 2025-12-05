"""
Playground Session Manager

Redis-backed session management for the Interactive Playground.
Handles session CRUD, message history, and expiration.
"""

import json
import logging
import uuid
from dataclasses import dataclass, field
from datetime import datetime, timedelta, UTC
from typing import Any

import redis.asyncio as redis

logger = logging.getLogger(__name__)


@dataclass
class Session:
    """Playground session data."""

    id: str
    user_id: str
    name: str
    created_at: datetime
    expires_at: datetime | None = None
    message_count: int = 0
    metadata: dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> dict[str, Any]:
        """Convert session to dictionary for storage."""
        return {
            "id": self.id,
            "user_id": self.user_id,
            "name": self.name,
            "created_at": self.created_at.isoformat(),
            "expires_at": self.expires_at.isoformat() if self.expires_at else None,
            "message_count": self.message_count,
            "metadata": self.metadata,
        }

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> "Session":
        """Create session from dictionary."""
        return cls(
            id=data["id"],
            user_id=data["user_id"],
            name=data["name"],
            created_at=datetime.fromisoformat(data["created_at"]),
            expires_at=(datetime.fromisoformat(data["expires_at"]) if data.get("expires_at") else None),
            message_count=data.get("message_count", 0),
            metadata=data.get("metadata", {}),
        )


class SessionManager:
    """
    Manages playground sessions in Redis.

    Features:
    - Session CRUD with automatic expiration
    - Message history per session
    - User isolation (sessions scoped by user_id)
    """

    # Redis key prefixes
    SESSION_PREFIX = "playground:session:"
    USER_SESSIONS_PREFIX = "playground:user_sessions:"
    MESSAGES_PREFIX = "playground:messages:"

    def __init__(
        self,
        redis_url: str | None = None,
        redis_client: redis.Redis | None = None,
        session_ttl_seconds: int = 3600,  # 1 hour default
        max_messages_per_session: int = 100,
    ) -> None:
        """
        Initialize session manager.

        Args:
            redis_url: Redis connection URL
            redis_client: Pre-configured Redis client (for testing)
            session_ttl_seconds: Session expiration time in seconds
            max_messages_per_session: Maximum messages to store per session
        """
        self._redis_url = redis_url
        self._redis_client = redis_client
        self._session_ttl = session_ttl_seconds
        self._max_messages = max_messages_per_session
        self._initialized = False

    async def _get_redis(self) -> redis.Redis:
        """Get or create Redis connection."""
        if self._redis_client is not None:
            return self._redis_client

        if not self._initialized:
            self._redis_client = redis.from_url(
                self._redis_url or "redis://localhost:6379/2",
                decode_responses=True,
            )
            self._initialized = True

        return self._redis_client

    async def create_session(
        self,
        user_id: str,
        name: str,
        metadata: dict[str, Any] | None = None,
    ) -> Session:
        """
        Create a new playground session.

        Args:
            user_id: Owner user ID
            name: Session name
            metadata: Optional metadata

        Returns:
            Created session
        """
        session_id = str(uuid.uuid4())
        now = datetime.now(UTC)
        expires_at = now + timedelta(seconds=self._session_ttl)

        session = Session(
            id=session_id,
            user_id=user_id,
            name=name,
            created_at=now,
            expires_at=expires_at,
            message_count=0,
            metadata=metadata or {},
        )

        r = await self._get_redis()

        # Store session data
        session_key = f"{self.SESSION_PREFIX}{session_id}"
        await r.set(
            session_key,
            json.dumps(session.to_dict()),
            ex=self._session_ttl,
        )

        # Add to user's session index
        user_sessions_key = f"{self.USER_SESSIONS_PREFIX}{user_id}"
        await r.sadd(user_sessions_key, session_id)
        await r.expire(user_sessions_key, self._session_ttl * 2)  # Keep index longer

        logger.info(
            "Created session",
            extra={"session_id": session_id, "user_id": user_id, "session_name": name},
        )

        return session

    async def get_session(self, session_id: str) -> Session | None:
        """
        Get session by ID.

        Args:
            session_id: Session ID

        Returns:
            Session if found, None otherwise
        """
        r = await self._get_redis()
        session_key = f"{self.SESSION_PREFIX}{session_id}"

        data = await r.get(session_key)
        if not data:
            return None

        return Session.from_dict(json.loads(data))

    async def list_sessions(self, user_id: str) -> list[Session]:
        """
        List all sessions for a user.

        Args:
            user_id: User ID

        Returns:
            List of sessions
        """
        r = await self._get_redis()
        user_sessions_key = f"{self.USER_SESSIONS_PREFIX}{user_id}"

        session_ids = await r.smembers(user_sessions_key)
        sessions = []

        for session_id in session_ids:
            session = await self.get_session(session_id)
            if session:
                sessions.append(session)
            else:
                # Clean up stale reference
                await r.srem(user_sessions_key, session_id)

        # Sort by creation time, newest first
        sessions.sort(key=lambda s: s.created_at, reverse=True)

        return sessions

    async def delete_session(self, session_id: str) -> bool:
        """
        Delete a session.

        Args:
            session_id: Session ID

        Returns:
            True if deleted, False if not found
        """
        r = await self._get_redis()

        # Get session to find user_id
        session = await self.get_session(session_id)
        if not session:
            return False

        # Delete session data
        session_key = f"{self.SESSION_PREFIX}{session_id}"
        await r.delete(session_key)

        # Delete messages
        messages_key = f"{self.MESSAGES_PREFIX}{session_id}"
        await r.delete(messages_key)

        # Remove from user's session index
        user_sessions_key = f"{self.USER_SESSIONS_PREFIX}{session.user_id}"
        await r.srem(user_sessions_key, session_id)

        logger.info(
            "Deleted session",
            extra={"session_id": session_id, "user_id": session.user_id},
        )

        return True

    async def refresh_session(self, session_id: str) -> bool:
        """
        Refresh session expiration.

        Args:
            session_id: Session ID

        Returns:
            True if refreshed, False if not found
        """
        r = await self._get_redis()
        session_key = f"{self.SESSION_PREFIX}{session_id}"

        # Get current session data
        data = await r.get(session_key)
        if not data:
            return False

        session_data = json.loads(data)
        session_data["expires_at"] = (datetime.now(UTC) + timedelta(seconds=self._session_ttl)).isoformat()

        # Update with new expiration
        await r.set(
            session_key,
            json.dumps(session_data),
            ex=self._session_ttl,
        )

        return True

    async def add_message(
        self,
        session_id: str,
        role: str,
        content: str,
        metadata: dict[str, Any] | None = None,
    ) -> dict[str, Any]:
        """
        Add a message to session history.

        Args:
            session_id: Session ID
            role: Message role (user, assistant)
            content: Message content
            metadata: Optional metadata

        Returns:
            Stored message with ID and timestamp
        """
        r = await self._get_redis()

        message = {
            "id": str(uuid.uuid4()),
            "role": role,
            "content": content,
            "timestamp": datetime.now(UTC).isoformat(),
            "metadata": metadata or {},
        }

        messages_key = f"{self.MESSAGES_PREFIX}{session_id}"

        # Add to list
        await r.rpush(messages_key, json.dumps(message))

        # Trim to max messages
        await r.ltrim(messages_key, -self._max_messages, -1)

        # Update session message count
        session = await self.get_session(session_id)
        if session:
            session_key = f"{self.SESSION_PREFIX}{session_id}"
            session.message_count = await r.llen(messages_key)
            await r.set(
                session_key,
                json.dumps(session.to_dict()),
                keepttl=True,
            )

        # Refresh session expiration on activity
        await self.refresh_session(session_id)

        return message

    async def get_messages(
        self,
        session_id: str,
        limit: int | None = None,
    ) -> list[dict[str, Any]]:
        """
        Get message history for a session.

        Args:
            session_id: Session ID
            limit: Maximum number of messages to return

        Returns:
            List of messages in chronological order
        """
        r = await self._get_redis()
        messages_key = f"{self.MESSAGES_PREFIX}{session_id}"

        if limit:
            # Get last N messages
            messages_data = await r.lrange(messages_key, -limit, -1)
        else:
            # Get all messages
            messages_data = await r.lrange(messages_key, 0, -1)

        return [json.loads(m) for m in messages_data]

    async def close(self) -> None:
        """Close Redis connection."""
        if self._redis_client and self._initialized:
            await self._redis_client.close()
            self._initialized = False
