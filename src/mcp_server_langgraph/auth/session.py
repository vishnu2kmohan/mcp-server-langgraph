"""
Session Management for Authentication

Provides pluggable session storage backends with support for:
- Redis (production)
- In-memory (development/testing)
- Session lifecycle management
- Sliding expiration windows
- Concurrent session limits
"""

import json
import secrets
from abc import ABC, abstractmethod
from collections.abc import Mapping
from datetime import datetime, timedelta, timezone
from typing import Any, cast

from pydantic import BaseModel, ConfigDict, Field, field_validator


try:
    import redis.asyncio as redis

    REDIS_AVAILABLE = True
except ImportError:
    redis = None  # type: ignore[assignment]
    REDIS_AVAILABLE = False

from mcp_server_langgraph.observability.telemetry import logger, tracer


class SessionData(BaseModel):
    """
    Type-safe session data structure with validation

    Uses Pydantic for automatic validation, serialization, and better IDE support.
    All datetime fields are stored as ISO format strings for Redis compatibility.
    """

    session_id: str = Field(..., description="Unique session identifier", min_length=32)
    user_id: str = Field(..., description="User identifier (e.g., 'user:alice')")
    username: str = Field(..., description="Username")
    roles: list[str] = Field(default_factory=list, description="User roles")
    metadata: dict[str, Any] = Field(default_factory=dict, description="Additional session metadata")
    created_at: str = Field(..., description="Session creation timestamp (ISO format)")
    last_accessed: str = Field(..., description="Last access timestamp (ISO format)")
    expires_at: str = Field(..., description="Expiration timestamp (ISO format)")

    model_config = ConfigDict(
        frozen=False,  # Allow updates for last_accessed, metadata
        validate_assignment=True,  # Validate on field assignment
        str_strip_whitespace=True,  # Strip whitespace from strings
        json_schema_extra={
            "example": {
                "session_id": "a1b2c3d4e5f6...",
                "user_id": "user:alice",
                "username": "alice",
                "roles": ["user", "admin"],
                "metadata": {"ip": "192.168.1.1"},
                "created_at": "2025-01-01T00:00:00.000000",
                "last_accessed": "2025-01-01T00:00:00.000000",
                "expires_at": "2025-01-02T00:00:00.000000",
            }
        },
    )

    @field_validator("session_id")
    @classmethod
    def validate_session_id(cls, v: str) -> str:
        """Validate session ID is properly formatted and secure"""
        if not v or len(v) < 32:
            raise ValueError("Session ID must be at least 32 characters for security")
        return v

    @field_validator("user_id")
    @classmethod
    def validate_user_id(cls, v: str) -> str:
        """Validate user ID format"""
        if not v:
            raise ValueError("User ID cannot be empty")
        return v

    @field_validator("created_at", "last_accessed", "expires_at")
    @classmethod
    def validate_timestamp(cls, v: str) -> str:
        """Validate timestamp is in ISO format and normalize Zulu time to explicit timezone"""
        try:
            # Handle Zulu time (Z) suffix by replacing with +00:00
            # This normalizes timestamps from datetime.isoformat() calls
            normalized = v.replace("Z", "+00:00") if v.endswith("Z") else v
            datetime.fromisoformat(normalized)
            return normalized
        except (ValueError, TypeError):
            raise ValueError(f"Timestamp must be in ISO format, got: {v}")

    def to_dict(self) -> dict[str, Any]:
        """Convert to dictionary for backward compatibility"""
        return self.model_dump()

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> "SessionData":
        """Create SessionData from dictionary for backward compatibility"""
        return cls(**data)


class SessionStore(ABC):
    """Abstract base class for session storage backends"""

    @abstractmethod
    async def create(
        self,
        user_id: str,
        username: str,
        roles: list[str],
        metadata: dict[str, Any] | None = None,
        ttl_seconds: int | None = None,
    ) -> str:
        """
        Create a new session

        Args:
            user_id: User identifier
            username: Username
            roles: User roles
            metadata: Additional session metadata
            ttl_seconds: Time-to-live in seconds

        Returns:
            Session ID
        """

    @abstractmethod
    async def get(self, session_id: str) -> SessionData | None:
        """
        Get session data

        Args:
            session_id: Session identifier

        Returns:
            Session data or None if not found/expired
        """

    @abstractmethod
    async def update(self, session_id: str, metadata: dict[str, Any]) -> bool:
        """
        Update session metadata

        Args:
            session_id: Session identifier
            metadata: Metadata to update

        Returns:
            True if successful, False otherwise
        """

    @abstractmethod
    async def refresh(self, session_id: str, ttl_seconds: int | None = None) -> bool:
        """
        Refresh session expiration

        Args:
            session_id: Session identifier
            ttl_seconds: New TTL in seconds

        Returns:
            True if successful, False otherwise
        """

    @abstractmethod
    async def delete(self, session_id: str) -> bool:
        """
        Delete a session

        Args:
            session_id: Session identifier

        Returns:
            True if deleted, False if not found
        """

    @abstractmethod
    async def list_user_sessions(self, user_id: str) -> list[SessionData]:
        """
        List all sessions for a user

        Args:
            user_id: User identifier

        Returns:
            List of session data
        """

    @abstractmethod
    async def delete_user_sessions(self, user_id: str) -> int:
        """
        Delete all sessions for a user

        Args:
            user_id: User identifier

        Returns:
            Number of sessions deleted
        """

    @abstractmethod
    async def get_inactive_sessions(self, cutoff_date: datetime) -> list[SessionData]:
        """
        Get sessions that haven't been accessed since cutoff date

        Args:
            cutoff_date: Return sessions with last_accessed before this date

        Returns:
            List of inactive session data
        """

    @abstractmethod
    async def delete_inactive_sessions(self, cutoff_date: datetime) -> int:
        """
        Delete sessions that haven't been accessed since cutoff date

        Args:
            cutoff_date: Delete sessions with last_accessed before this date

        Returns:
            Number of sessions deleted
        """

    def _generate_session_id(self) -> str:
        """Generate cryptographically secure session ID"""
        return secrets.token_urlsafe(32)


class InMemorySessionStore(SessionStore):
    """
    In-memory session store for development and testing

    WARNING: Not suitable for production use:
    - Data lost on restart
    - No clustering support
    - No persistence
    """

    def __init__(
        self,
        default_ttl_seconds: int = 86400,  # 24 hours
        sliding_window: bool = True,
        max_concurrent_sessions: int = 5,
    ):
        """
        Initialize in-memory session store

        Args:
            default_ttl_seconds: Default session TTL
            sliding_window: Enable sliding expiration
            max_concurrent_sessions: Max sessions per user
        """
        self.sessions: dict[str, SessionData] = {}
        self.user_sessions: dict[str, list[str]] = {}  # user_id -> [session_ids]
        self.default_ttl = default_ttl_seconds
        self.sliding_window = sliding_window
        self.max_concurrent = max_concurrent_sessions

        logger.info(
            "Initialized InMemorySessionStore",
            extra={
                "default_ttl": default_ttl_seconds,
                "sliding_window": sliding_window,
                "max_concurrent": max_concurrent_sessions,
            },
        )

    async def create(
        self,
        user_id: str,
        username: str,
        roles: list[str],
        metadata: dict[str, Any] | None = None,
        ttl_seconds: int | None = None,
    ) -> str:
        """Create new session"""
        with tracer.start_as_current_span("session.create") as span:
            span.set_attribute("user.id", user_id)

            # Check concurrent session limit
            if user_id in self.user_sessions and len(self.user_sessions[user_id]) >= self.max_concurrent:
                # Remove oldest session
                oldest_session_id = self.user_sessions[user_id].pop(0)
                self.sessions.pop(oldest_session_id, None)
                logger.info(f"Removed oldest session for user {user_id} (max concurrent limit reached)")

            # Generate session
            session_id = self._generate_session_id()
            ttl = ttl_seconds or self.default_ttl
            now = datetime.now(timezone.utc)

            session_data = SessionData(
                session_id=session_id,
                user_id=user_id,
                username=username,
                roles=roles,
                metadata=metadata or {},
                created_at=now.isoformat(),
                last_accessed=now.isoformat(),
                expires_at=(now + timedelta(seconds=ttl)).isoformat(),
            )

            self.sessions[session_id] = session_data

            # Track user sessions
            if user_id not in self.user_sessions:
                self.user_sessions[user_id] = []
            self.user_sessions[user_id].append(session_id)

            from mcp_server_langgraph.core.security import sanitize_for_logging

            logger.info(
                "Session created",
                extra=sanitize_for_logging({"session_id": session_id, "user_id": user_id, "ttl_seconds": ttl}),
            )

            return session_id

    async def get(self, session_id: str) -> SessionData | None:
        """Get session with expiration check"""
        with tracer.start_as_current_span("session.get") as span:
            span.set_attribute("session.id", session_id)

            if session_id not in self.sessions:
                return None

            session = self.sessions[session_id]

            # Check expiration
            expires_at = datetime.fromisoformat(session.expires_at)
            if datetime.now(timezone.utc) > expires_at:
                # Session expired
                await self.delete(session_id)
                return None

            # Update last accessed time (sliding window)
            if self.sliding_window:
                session.last_accessed = datetime.now(timezone.utc).isoformat()

            return session

    async def update(self, session_id: str, metadata: dict[str, Any]) -> bool:
        """Update session metadata"""
        if session_id not in self.sessions:
            return False

        session = self.sessions[session_id]
        session.metadata.update(metadata)
        session.last_accessed = datetime.now(timezone.utc).isoformat()

        logger.info(f"Session metadata updated: {session_id}")
        return True

    async def refresh(self, session_id: str, ttl_seconds: int | None = None) -> bool:
        """Refresh session expiration"""
        if session_id not in self.sessions:
            return False

        session = self.sessions[session_id]
        ttl = ttl_seconds or self.default_ttl
        now = datetime.now(timezone.utc)

        session.last_accessed = now.isoformat()
        session.expires_at = (now + timedelta(seconds=ttl)).isoformat()

        logger.info(f"Session refreshed: {session_id}, new TTL: {ttl}s")
        return True

    async def delete(self, session_id: str) -> bool:
        """Delete session"""
        if session_id not in self.sessions:
            return False

        session = self.sessions.pop(session_id)
        user_id = session.user_id

        # Remove from user sessions tracking
        if user_id in self.user_sessions:
            try:
                self.user_sessions[user_id].remove(session_id)
                if not self.user_sessions[user_id]:
                    del self.user_sessions[user_id]
            except ValueError:
                pass

        logger.info(f"Session deleted: {session_id}")
        return True

    async def list_user_sessions(self, user_id: str) -> list[SessionData]:
        """List all active sessions for a user"""
        if user_id not in self.user_sessions:
            return []

        sessions = []
        for session_id in self.user_sessions[user_id][:]:  # Copy to allow modification
            session = await self.get(session_id)  # Will auto-delete expired
            if session:
                sessions.append(session)

        return sessions

    async def delete_user_sessions(self, user_id: str) -> int:
        """Delete all sessions for a user"""
        if user_id not in self.user_sessions:
            return 0

        session_ids = self.user_sessions[user_id][:]
        count = 0

        for session_id in session_ids:
            if await self.delete(session_id):
                count += 1

        logger.info(f"Deleted {count} sessions for user {user_id}")
        return count

    async def get_inactive_sessions(self, cutoff_date: datetime) -> list[SessionData]:
        """Get sessions that haven't been accessed since cutoff date"""
        inactive_sessions = []

        for session_id, session in list(self.sessions.items()):
            try:
                # Check if session is expired first
                if await self.get(session_id) is None:
                    continue  # Session was expired and auto-deleted

                # Parse last_accessed timestamp
                last_accessed = datetime.fromisoformat(session.last_accessed)

                # Add to inactive list if older than cutoff
                if last_accessed < cutoff_date:
                    inactive_sessions.append(session)

            except (ValueError, AttributeError) as e:
                logger.warning(f"Error parsing session {session_id}: {e}")
                continue

        logger.info(f"Found {len(inactive_sessions)} inactive sessions before {cutoff_date.isoformat()}")
        return inactive_sessions

    async def delete_inactive_sessions(self, cutoff_date: datetime) -> int:
        """Delete sessions that haven't been accessed since cutoff date"""
        inactive_sessions = await self.get_inactive_sessions(cutoff_date)
        count = 0

        for session in inactive_sessions:
            if await self.delete(session.session_id):
                count += 1

        logger.info(f"Deleted {count} inactive sessions before {cutoff_date.isoformat()}")
        return count


class RedisSessionStore(SessionStore):
    """
    Redis-backed session store for production use

    Features:
    - Persistent storage
    - Clustering support
    - Automatic expiration via Redis TTL
    - High performance
    """

    def __init__(
        self,
        redis_url: str = "redis://localhost:6379/0",
        default_ttl_seconds: int = 86400,
        sliding_window: bool = True,
        max_concurrent_sessions: int = 5,
        ssl: bool = False,
        decode_responses: bool = True,
        password: str | None = None,
        ttl_seconds: int | None = None,
    ):
        """
        Initialize Redis session store

        Args:
            redis_url: Redis connection URL
            default_ttl_seconds: Default session TTL
            sliding_window: Enable sliding expiration
            max_concurrent_sessions: Max sessions per user
            ssl: Use SSL/TLS
            decode_responses: Decode responses to strings
            password: Redis password (optional)
            ttl_seconds: Alias for default_ttl_seconds (for backward compatibility)
        """
        if not REDIS_AVAILABLE:
            raise ImportError(
                "Redis not available. Add 'redis[hiredis]>=5.0.0' to pyproject.toml dependencies, then run: uv sync"
            )

        # Support both ttl_seconds and default_ttl_seconds for backward compatibility
        if ttl_seconds is not None:
            default_ttl_seconds = ttl_seconds

        self.redis_url = redis_url
        self.default_ttl = default_ttl_seconds
        self.sliding_window = sliding_window
        self.max_concurrent = max_concurrent_sessions
        self.decode_responses = decode_responses

        # Initialize Redis client
        self.redis = redis.from_url(
            redis_url,
            password=password,
            ssl=ssl,
            decode_responses=decode_responses,
            encoding="utf-8",
        )

        logger.info(
            "Initialized RedisSessionStore",
            extra={
                "redis_url": redis_url,
                "default_ttl": default_ttl_seconds,
                "sliding_window": sliding_window,
                "max_concurrent": max_concurrent_sessions,
            },
        )

    async def create(
        self,
        user_id: str,
        username: str,
        roles: list[str],
        metadata: dict[str, Any] | None = None,
        ttl_seconds: int | None = None,
    ) -> str:
        """Create new session in Redis"""
        with tracer.start_as_current_span("session.create") as span:
            span.set_attribute("user.id", user_id)

            # Check concurrent session limit
            user_sessions_key = f"user_sessions:{user_id}"
            session_ids = await self.redis.lrange(user_sessions_key, 0, -1)

            if len(session_ids) >= self.max_concurrent:
                # Remove oldest session
                oldest_session_id = session_ids[0]
                if isinstance(oldest_session_id, bytes):
                    oldest_session_id = oldest_session_id.decode("utf-8")
                await self.delete(oldest_session_id)
                logger.info(f"Removed oldest session for user {user_id}")

            # Generate session
            session_id = self._generate_session_id()
            ttl = ttl_seconds or self.default_ttl
            now = datetime.now(timezone.utc)

            session_data = {
                "session_id": session_id,
                "user_id": user_id,
                "username": username,
                "roles": ",".join(roles),  # Store as comma-separated
                "metadata": json.dumps(metadata or {}),  # Store as JSON string
                "created_at": now.isoformat(),
                "last_accessed": now.isoformat(),
                "expires_at": (now + timedelta(seconds=ttl)).isoformat(),
            }

            # Store session in Redis
            session_key = f"session:{session_id}"
            await self.redis.hset(session_key, mapping=cast(Mapping[str | bytes, bytes | float | int | str], session_data))
            await self.redis.expire(session_key, ttl)

            # Track user sessions
            await self.redis.rpush(user_sessions_key, session_id)
            await self.redis.expire(user_sessions_key, ttl + 3600)  # Extra hour

            from mcp_server_langgraph.core.security import sanitize_for_logging

            logger.info(
                "Session created in Redis",
                extra=sanitize_for_logging({"session_id": session_id, "user_id": user_id, "ttl_seconds": ttl}),
            )

            return session_id

    async def get(self, session_id: str) -> SessionData | None:
        """Get session from Redis"""
        with tracer.start_as_current_span("session.get") as span:
            span.set_attribute("session.id", session_id)

            session_key = f"session:{session_id}"
            data = await self.redis.hgetall(session_key)

            if not data:
                return None

            # Convert Redis data to SessionData (Pydantic validates automatically)
            # Parse metadata safely using json.loads instead of eval
            metadata_str = data.get("metadata", "{}")
            try:
                metadata = json.loads(metadata_str) if metadata_str else {}
            except (json.JSONDecodeError, TypeError):
                metadata = {}

            session = SessionData(
                session_id=cast(str, data.get("session_id")),
                user_id=cast(str, data.get("user_id")),
                username=cast(str, data.get("username")),
                roles=data.get("roles", "").split(",") if data.get("roles") else [],
                metadata=metadata,
                created_at=cast(str, data.get("created_at")),
                last_accessed=cast(str, data.get("last_accessed")),
                expires_at=cast(str, data.get("expires_at")),
            )

            # Update last accessed (sliding window)
            if self.sliding_window:
                await self.redis.hset(session_key, "last_accessed", datetime.now(timezone.utc).isoformat())

            return session

    async def update(self, session_id: str, metadata: dict[str, Any]) -> bool:
        """Update session metadata"""
        session_key = f"session:{session_id}"
        exists = await self.redis.exists(session_key)

        if not exists:
            return False

        # Get current session to preserve Pydantic validation
        session = await self.get(session_id)
        if not session:
            return False

        # Update metadata on Pydantic model
        session.metadata.update(metadata)
        session.last_accessed = datetime.now(timezone.utc).isoformat()

        # Persist to Redis
        await self.redis.hset(
            session_key, mapping={"metadata": json.dumps(session.metadata), "last_accessed": session.last_accessed}
        )

        logger.info(f"Session metadata updated in Redis: {session_id}")
        return True

    async def refresh(self, session_id: str, ttl_seconds: int | None = None) -> bool:
        """Refresh session expiration"""
        session_key = f"session:{session_id}"
        exists = await self.redis.exists(session_key)

        if not exists:
            return False

        ttl = ttl_seconds or self.default_ttl
        now = datetime.now(timezone.utc)
        new_expires_at = (now + timedelta(seconds=ttl)).isoformat()

        await self.redis.hset(session_key, mapping={"last_accessed": now.isoformat(), "expires_at": new_expires_at})
        await self.redis.expire(session_key, ttl)

        logger.info(f"Session refreshed in Redis: {session_id}, TTL: {ttl}s")
        return True

    async def delete(self, session_id: str) -> bool:
        """Delete session from Redis"""
        session_key = f"session:{session_id}"

        # Get user_id before deleting
        user_id = await self.redis.hget(session_key, "user_id")

        # Delete session
        deleted = await self.redis.delete(session_key)

        if deleted and user_id:
            # Remove from user sessions list
            user_sessions_key = f"user_sessions:{user_id}"
            await self.redis.lrem(user_sessions_key, 0, session_id)

        logger.info(f"Session deleted from Redis: {session_id}")
        return bool(deleted)

    async def list_user_sessions(self, user_id: str) -> list[SessionData]:
        """List all active sessions for a user"""
        user_sessions_key = f"user_sessions:{user_id}"
        session_ids = await self.redis.lrange(user_sessions_key, 0, -1)

        sessions = []
        for session_id in session_ids:
            if isinstance(session_id, bytes):
                session_id = session_id.decode("utf-8")
            session = await self.get(session_id)
            if session:
                sessions.append(session)

        return sessions

    async def delete_user_sessions(self, user_id: str) -> int:
        """Delete all sessions for a user"""
        user_sessions_key = f"user_sessions:{user_id}"
        session_ids = await self.redis.lrange(user_sessions_key, 0, -1)

        count = 0
        for session_id in session_ids:
            if isinstance(session_id, bytes):
                session_id = session_id.decode("utf-8")
            if await self.delete(session_id):
                count += 1

        # Delete user sessions list
        await self.redis.delete(user_sessions_key)

        logger.info(f"Deleted {count} sessions from Redis for user {user_id}")
        return count

    async def get_inactive_sessions(self, cutoff_date: datetime) -> list[SessionData]:
        """Get sessions that haven't been accessed since cutoff date"""
        inactive_sessions = []

        # Scan all session keys
        cursor = 0
        while True:
            cursor, keys = await self.redis.scan(cursor, match="session:*", count=100)

            for key in keys:
                if isinstance(key, bytes):
                    key = key.decode("utf-8")

                session_id = key.replace("session:", "")
                session = await self.get(session_id)

                if session:
                    try:
                        # Parse last_accessed timestamp
                        last_accessed = datetime.fromisoformat(session.last_accessed)

                        # Add to inactive list if older than cutoff
                        if last_accessed < cutoff_date:
                            inactive_sessions.append(session)

                    except (ValueError, AttributeError) as e:
                        logger.warning(f"Error parsing session {session_id}: {e}")
                        continue

            if cursor == 0:
                break

        logger.info(f"Found {len(inactive_sessions)} inactive sessions in Redis before {cutoff_date.isoformat()}")
        return inactive_sessions

    async def delete_inactive_sessions(self, cutoff_date: datetime) -> int:
        """Delete sessions that haven't been accessed since cutoff date"""
        inactive_sessions = await self.get_inactive_sessions(cutoff_date)
        count = 0

        for session in inactive_sessions:
            if await self.delete(session.session_id):
                count += 1

        logger.info(f"Deleted {count} inactive sessions from Redis before {cutoff_date.isoformat()}")
        return count


def create_session_store(backend: str = "memory", redis_url: str | None = None, **kwargs: Any) -> SessionStore:
    """
    Factory function to create session store

    Args:
        backend: "memory" or "redis"
        redis_url: Redis connection URL (required for redis backend)
        **kwargs: Additional arguments for session store

    Returns:
        SessionStore instance

    Raises:
        ValueError: If backend is unknown or redis_url missing for redis backend
    """
    backend = backend.lower()

    if backend == "memory":
        logger.info("Creating InMemorySessionStore")
        return InMemorySessionStore(**kwargs)

    if backend == "redis":
        if not redis_url:
            raise ValueError("redis_url required for Redis backend")

        if not REDIS_AVAILABLE:
            raise ImportError(
                "Redis not available. Add 'redis[hiredis]>=5.0.0' to pyproject.toml dependencies, then run: uv sync"
            )

        logger.info("Creating RedisSessionStore")
        return RedisSessionStore(redis_url=redis_url, **kwargs)

    raise ValueError(f"Unknown session backend: {backend}. Supported: 'memory', 'redis'")


# Global session store instance
_session_store: SessionStore | None = None


def get_session_store() -> SessionStore:
    """
    FastAPI dependency to get the global session store instance

    Returns:
        SessionStore instance

    Warning:
        If no session store has been registered via set_session_store(), this function
        creates a default in-memory store. This fallback behavior should only occur
        during testing or if create_auth_middleware() hasn't been called yet.

        In production, ensure create_auth_middleware() is called during app startup
        to register the configured session store (Redis or Memory based on settings).

    Example:
        @app.get("/api/sessions")
        async def list_sessions(session_store: SessionStore = Depends(get_session_store)):
            # Use session_store
            pass
    """
    global _session_store

    if _session_store is None:
        # Create default in-memory session store as fallback
        # This should only happen during testing or before middleware initialization
        logger.warning(
            "Session store not registered globally, using fallback in-memory store. "
            "This may indicate create_auth_middleware() was not called. "
            "In production, register the session store via set_session_store()."
        )
        _session_store = InMemorySessionStore()

    return _session_store


def set_session_store(session_store: SessionStore) -> None:
    """
    Set the global session store instance

    Args:
        session_store: Session store to use globally

    Example:
        # At application startup
        redis_store = create_session_store("redis", redis_url="redis://localhost:6379")
        set_session_store(redis_store)
    """
    global _session_store
    _session_store = session_store
