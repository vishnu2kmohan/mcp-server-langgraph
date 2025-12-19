"""
Redis-backed session manager for the unified Studio frontend.

Provides session persistence with:
- Session CRUD operations via Redis
- Automatic session expiration via TTL
- Message history storage
- User-scoped session listing
- Connection pooling for performance

Example:
    from mcp_server_langgraph.storage.session import (
        RedisSessionManager,
        create_redis_pool,
    )

    # Create connection pool
    redis_pool = await create_redis_pool("redis://localhost:6379/2")

    # Initialize manager with 1-hour TTL
    manager = RedisSessionManager(redis_client=redis_pool, ttl_seconds=3600)

    # Create session
    session = await manager.create_session(name="My Session", user_id="alice")

    # Add message
    await manager.add_message(session.session_id, role="user", content="Hello!")

    # Clean up
    await manager.close()
"""

import uuid
from datetime import UTC, datetime
from typing import Any

import redis.asyncio as redis

from .models import Message, Session, SessionConfig


async def create_redis_pool(
    redis_url: str,
    max_connections: int = 10,
    decode_responses: bool = True,
) -> redis.Redis:
    """
    Create a Redis connection pool for session storage.

    Args:
        redis_url: Redis connection URL (e.g., "redis://localhost:6379/2")
        max_connections: Maximum connections in the pool
        decode_responses: Whether to decode responses as strings

    Returns:
        Configured Redis client with connection pool
    """
    client: redis.Redis = redis.from_url(  # type: ignore[no-untyped-call]
        redis_url,
        max_connections=max_connections,
        decode_responses=decode_responses,
    )
    return client


class RedisSessionManager:
    """
    Redis-backed session manager for studio sessions.

    Stores sessions in Redis with automatic TTL expiration.
    Sessions are keyed by session_id with optional user_id prefix for listing.
    """

    DEFAULT_TTL_SECONDS = 3600  # 1 hour
    KEY_PREFIX = "session"

    def __init__(
        self,
        redis_client: redis.Redis,
        ttl_seconds: int | None = None,
    ) -> None:
        """
        Initialize the session manager.

        Args:
            redis_client: Redis client (with connection pool)
            ttl_seconds: Session TTL in seconds (default: 1 hour)
        """
        self._redis = redis_client
        self._ttl = ttl_seconds or self.DEFAULT_TTL_SECONDS

    def _session_key(self, session_id: str) -> str:
        """Generate Redis key for a session."""
        return f"{self.KEY_PREFIX}:{session_id}"

    def _user_session_key(self, user_id: str, session_id: str) -> str:
        """Generate Redis key for user-scoped session."""
        return f"{self.KEY_PREFIX}:user:{user_id}:{session_id}"

    def _user_sessions_index_key(self, user_id: str) -> str:
        """Generate Redis key for user's session index (SET).

        This secondary index enables O(1) session listing per user
        instead of O(N) SCAN across all keys.
        """
        return f"{self.KEY_PREFIX}:index:user:{user_id}"

    async def create_session(
        self,
        name: str,
        user_id: str | None = None,
        config: SessionConfig | None = None,
    ) -> Session:
        """
        Create a new session and store it in Redis.

        Args:
            name: Session name
            user_id: Optional user ID for scoping
            config: Optional LLM configuration

        Returns:
            Created session
        """
        session_id = str(uuid.uuid4())
        now = datetime.now(UTC)

        session = Session(
            session_id=session_id,
            name=name,
            created_at=now,
            updated_at=now,
            messages=[],
            config=config or SessionConfig(),
            user_id=user_id,
        )

        # Store in Redis with TTL
        key = self._session_key(session_id)
        await self._redis.setex(key, self._ttl, session.model_dump_json())

        # Also store user-scoped key for listing
        if user_id:
            user_key = self._user_session_key(user_id, session_id)
            await self._redis.setex(user_key, self._ttl, session.model_dump_json())

            # Add session_id to user's session index (SET) for O(1) listing
            index_key = self._user_sessions_index_key(user_id)
            await self._redis.sadd(index_key, session_id)  # type: ignore[misc]
            # Refresh index TTL (slightly longer than session TTL)
            await self._redis.expire(index_key, self._ttl + 300)

        return session

    async def get_session(self, session_id: str) -> Session | None:
        """
        Retrieve a session from Redis.

        Args:
            session_id: Session ID to retrieve

        Returns:
            Session if found, None otherwise
        """
        key = self._session_key(session_id)
        data = await self._redis.get(key)

        if data is None:
            return None

        return Session.model_validate_json(data)

    async def update_session(
        self,
        session_id: str,
        name: str | None = None,
        config: SessionConfig | None = None,
    ) -> Session | None:
        """
        Update session metadata and refresh TTL.

        Args:
            session_id: Session ID to update
            name: Optional new name
            config: Optional new configuration

        Returns:
            Updated session if found, None otherwise
        """
        session = await self.get_session(session_id)
        if session is None:
            return None

        if name is not None:
            session.name = name
        if config is not None:
            session.config = config
        session.updated_at = datetime.now(UTC)

        # Store with refreshed TTL
        key = self._session_key(session_id)
        await self._redis.setex(key, self._ttl, session.model_dump_json())

        # Update user-scoped key if applicable
        if session.user_id:
            user_key = self._user_session_key(session.user_id, session_id)
            await self._redis.setex(user_key, self._ttl, session.model_dump_json())

        return session

    async def delete_session(self, session_id: str) -> bool:
        """
        Delete a session from Redis.

        Args:
            session_id: Session ID to delete

        Returns:
            True if deleted, False if not found
        """
        # First get session to find user_id
        session = await self.get_session(session_id)

        key = self._session_key(session_id)
        result = await self._redis.delete(key)

        # Also delete user-scoped key and remove from index if applicable
        if session and session.user_id:
            user_key = self._user_session_key(session.user_id, session_id)
            await self._redis.delete(user_key)

            # Remove from user's session index
            index_key = self._user_sessions_index_key(session.user_id)
            await self._redis.srem(index_key, session_id)  # type: ignore[misc]

        return bool(result > 0)

    async def add_message(
        self,
        session_id: str,
        role: str,
        content: str,
        metadata: dict[str, Any] | None = None,
    ) -> Message | None:
        """
        Add a message to session history.

        Args:
            session_id: Session ID to add message to
            role: Message role ("user" or "assistant")
            content: Message content
            metadata: Optional message metadata

        Returns:
            Created message if session found, None otherwise
        """
        session = await self.get_session(session_id)
        if session is None:
            return None

        message = Message(
            message_id=str(uuid.uuid4()),
            role=role,
            content=content,
            timestamp=datetime.now(UTC),
            metadata=metadata or {},
        )

        session.messages.append(message)
        session.updated_at = datetime.now(UTC)

        # Store with refreshed TTL
        key = self._session_key(session_id)
        await self._redis.setex(key, self._ttl, session.model_dump_json())

        # Update user-scoped key if applicable
        if session.user_id:
            user_key = self._user_session_key(session.user_id, session_id)
            await self._redis.setex(user_key, self._ttl, session.model_dump_json())

        return message

    async def list_sessions(self, user_id: str) -> list[Session]:
        """
        List all sessions for a user.

        Uses a Redis SET secondary index for O(1) lookup per session
        instead of O(N) SCAN across all keys.

        Args:
            user_id: User ID to list sessions for

        Returns:
            List of sessions
        """
        # Use SET index for O(1) lookup instead of O(N) SCAN
        index_key = self._user_sessions_index_key(user_id)
        session_ids = await self._redis.smembers(index_key)  # type: ignore[misc]

        sessions = []
        for session_id in session_ids:
            # Handle bytes (when decode_responses=False)
            if isinstance(session_id, bytes):
                session_id = session_id.decode("utf-8")
            session = await self.get_session(session_id)
            if session:
                sessions.append(session)

        return sessions

    async def clear_messages(self, session_id: str) -> bool:
        """
        Clear all messages in a session.

        Args:
            session_id: Session ID to clear messages from

        Returns:
            True if cleared, False if session not found
        """
        session = await self.get_session(session_id)
        if session is None:
            return False

        session.messages = []
        session.updated_at = datetime.now(UTC)

        # Store with refreshed TTL
        key = self._session_key(session_id)
        await self._redis.setex(key, self._ttl, session.model_dump_json())

        # Update user-scoped key if applicable
        if session.user_id:
            user_key = self._user_session_key(session.user_id, session_id)
            await self._redis.setex(user_key, self._ttl, session.model_dump_json())

        return True

    async def close(self) -> None:
        """Close the Redis connection."""
        await self._redis.close()
