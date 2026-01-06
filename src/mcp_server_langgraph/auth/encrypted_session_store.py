"""
Encrypted Session Store - Transparent encryption layer for session storage.

Wraps an underlying SessionStore implementation to provide at-rest encryption
for sensitive session data. Compliant with GDPR and HIPAA requirements for
data protection.

Usage:
    from mcp_server_langgraph.auth.encrypted_session_store import EncryptedSessionStore

    store = EncryptedSessionStore(
        encryption_key=b"32-byte-key-for-aes-256-encrypt",
        backend="memory",  # or "redis"
    )

    session_id = await store.create(
        user_id="user-123",
        username="alice",
        roles=["user"],
        metadata={"sensitive": "data"},
        ttl=3600,
    )

    session = await store.get(session_id)
"""

from __future__ import annotations

import json
from datetime import datetime
from typing import TYPE_CHECKING, Any, Literal

from mcp_server_langgraph.auth.session import (
    InMemorySessionStore,
    SessionData,
    SessionStore,
)
from mcp_server_langgraph.auth.session_encryptor import (
    DecryptionError,
    SessionEncryptor,
)
from mcp_server_langgraph.core.feature_flags import feature_flags
from mcp_server_langgraph.observability.telemetry import logger

if TYPE_CHECKING:
    pass


# =============================================================================
# Constants
# =============================================================================

# Marker to identify encrypted metadata
ENCRYPTED_MARKER = "__encrypted__"


# =============================================================================
# Encrypted Session Store
# =============================================================================


class EncryptedSessionStore(SessionStore):
    """Session store with transparent encryption for sensitive data.

    Encrypts session metadata before storage and decrypts on retrieval.
    Non-sensitive fields (session_id, user_id, timestamps) remain unencrypted
    to allow queries and indexing.

    Attributes:
        encryption_key: 32-byte key for AES-256 encryption
        backend: Underlying storage backend ("memory" or "redis")
    """

    def __init__(
        self,
        encryption_key: bytes,
        backend: Literal["memory", "redis"] = "memory",
        redis_url: str | None = None,
        **kwargs: Any,
    ) -> None:
        """Initialize encrypted session store.

        Args:
            encryption_key: 32-byte encryption key for AES-256
            backend: Storage backend type ("memory" or "redis")
            redis_url: Redis URL (required if backend is "redis")
            **kwargs: Additional arguments passed to underlying store
        """
        self._encryptor = SessionEncryptor(key=encryption_key)
        self._backend_type = backend

        # Initialize underlying store
        if backend == "memory":
            self._store: SessionStore = InMemorySessionStore(**kwargs)
        elif backend == "redis":
            # Import Redis store lazily to avoid hard dependency
            from mcp_server_langgraph.auth.session import RedisSessionStore

            if not redis_url:
                raise ValueError("redis_url is required for Redis backend")
            self._store = RedisSessionStore(redis_url=redis_url, **kwargs)
        else:
            raise ValueError(f"Unknown backend: {backend}")

    def _encrypt_metadata(self, metadata: dict[str, Any]) -> dict[str, Any]:
        """Encrypt sensitive metadata fields.

        Args:
            metadata: Original metadata dictionary

        Returns:
            Dictionary with encrypted payload
        """
        if not feature_flags.enable_encrypted_sessions:
            return metadata

        if not metadata:
            return metadata

        try:
            # Serialize and encrypt the entire metadata
            plaintext = json.dumps(metadata).encode("utf-8")
            encrypted = self._encryptor.encrypt(plaintext)

            # Return with marker and base64-encoded encrypted data
            import base64

            return {
                ENCRYPTED_MARKER: True,
                "data": base64.b64encode(encrypted).decode("ascii"),
            }
        except Exception as e:
            logger.warning(f"Failed to encrypt metadata: {e}")
            return metadata

    def _decrypt_metadata(self, metadata: dict[str, Any]) -> dict[str, Any]:
        """Decrypt encrypted metadata.

        Args:
            metadata: Potentially encrypted metadata

        Returns:
            Decrypted metadata dictionary
        """
        if not metadata:
            return metadata

        # Check if this is encrypted data
        if not metadata.get(ENCRYPTED_MARKER):
            return metadata

        try:
            import base64

            encrypted = base64.b64decode(metadata["data"].encode("ascii"))
            decrypted = self._encryptor.decrypt(encrypted)
            result: dict[str, Any] = json.loads(decrypted.decode("utf-8"))
            return result
        except DecryptionError as e:
            logger.error(f"Failed to decrypt metadata: {e}")
            raise
        except Exception as e:
            logger.warning(f"Error decrypting metadata: {e}")
            return metadata

    async def create(  # type: ignore[override]
        self,
        user_id: str,
        username: str,
        roles: list[str],
        metadata: dict[str, Any] | None = None,
        ttl_seconds: int | None = None,
        ttl: int | None = None,  # Alias for ttl_seconds for convenience
    ) -> SessionData:
        """Create a new session with encrypted metadata.

        Args:
            user_id: User identifier
            username: Username
            roles: User roles
            metadata: Additional session metadata (will be encrypted)
            ttl_seconds: Time-to-live in seconds
            ttl: Alias for ttl_seconds

        Returns:
            Created SessionData object
        """
        # Encrypt metadata before storage
        encrypted_metadata = self._encrypt_metadata(metadata or {})

        # Use ttl as fallback for ttl_seconds
        actual_ttl = ttl_seconds or ttl

        # Create session in underlying store
        session_id = await self._store.create(
            user_id=user_id,
            username=username,
            roles=roles,
            metadata=encrypted_metadata,
            ttl_seconds=actual_ttl,
        )

        # Retrieve and return the session (with decrypted metadata)
        session = await self.get(session_id)
        if session is None:
            raise RuntimeError("Failed to retrieve created session")
        return session

    async def get(self, session_id: str) -> SessionData | None:
        """Get session data with decrypted metadata.

        Args:
            session_id: Session identifier

        Returns:
            Session data with decrypted metadata, or None if not found
        """
        session = await self._store.get(session_id)

        if session is None:
            return None

        # Decrypt metadata
        try:
            decrypted_metadata = self._decrypt_metadata(session.metadata)
            # Create new SessionData with decrypted metadata
            return SessionData(
                session_id=session.session_id,
                user_id=session.user_id,
                username=session.username,
                roles=session.roles,
                metadata=decrypted_metadata,
                created_at=session.created_at,
                last_accessed=session.last_accessed,
                expires_at=session.expires_at,
            )
        except DecryptionError:
            # Log but don't expose decryption failures
            logger.error(f"Failed to decrypt session {session_id}")
            return None

    async def update(self, session_id: str, metadata: dict[str, Any]) -> bool:
        """Update session with encrypted metadata.

        Args:
            session_id: Session identifier
            metadata: New metadata (will be encrypted)

        Returns:
            True if successful, False otherwise
        """
        encrypted_metadata = self._encrypt_metadata(metadata)
        return await self._store.update(session_id, encrypted_metadata)

    async def refresh(self, session_id: str, ttl_seconds: int | None = None) -> bool:
        """Refresh session expiration.

        Args:
            session_id: Session identifier
            ttl_seconds: New TTL in seconds

        Returns:
            True if successful, False otherwise
        """
        return await self._store.refresh(session_id, ttl_seconds)

    async def delete(self, session_id: str) -> bool:
        """Delete a session.

        Args:
            session_id: Session identifier

        Returns:
            True if deleted, False if not found
        """
        return await self._store.delete(session_id)

    async def list_user_sessions(self, user_id: str) -> list[SessionData]:
        """List all sessions for a user with decrypted metadata.

        Args:
            user_id: User identifier

        Returns:
            List of sessions with decrypted metadata
        """
        sessions = await self._store.list_user_sessions(user_id)

        decrypted_sessions = []
        for session in sessions:
            try:
                decrypted_metadata = self._decrypt_metadata(session.metadata)
                decrypted_sessions.append(
                    SessionData(
                        session_id=session.session_id,
                        user_id=session.user_id,
                        username=session.username,
                        roles=session.roles,
                        metadata=decrypted_metadata,
                        created_at=session.created_at,
                        last_accessed=session.last_accessed,
                        expires_at=session.expires_at,
                    )
                )
            except DecryptionError:
                logger.error(f"Failed to decrypt session {session.session_id}")
                continue

        return decrypted_sessions

    async def delete_user_sessions(self, user_id: str) -> int:
        """Delete all sessions for a user.

        Args:
            user_id: User identifier

        Returns:
            Number of sessions deleted
        """
        return await self._store.delete_user_sessions(user_id)

    async def get_inactive_sessions(self, cutoff_date: datetime) -> list[SessionData]:
        """Get inactive sessions with decrypted metadata.

        Args:
            cutoff_date: Return sessions with last_accessed before this date

        Returns:
            List of inactive sessions with decrypted metadata
        """
        sessions = await self._store.get_inactive_sessions(cutoff_date)

        decrypted_sessions = []
        for session in sessions:
            try:
                decrypted_metadata = self._decrypt_metadata(session.metadata)
                decrypted_sessions.append(
                    SessionData(
                        session_id=session.session_id,
                        user_id=session.user_id,
                        username=session.username,
                        roles=session.roles,
                        metadata=decrypted_metadata,
                        created_at=session.created_at,
                        last_accessed=session.last_accessed,
                        expires_at=session.expires_at,
                    )
                )
            except DecryptionError:
                logger.error(f"Failed to decrypt session {session.session_id}")
                continue

        return decrypted_sessions

    async def delete_inactive_sessions(self, cutoff_date: datetime) -> int:
        """Delete inactive sessions.

        Args:
            cutoff_date: Delete sessions with last_accessed before this date

        Returns:
            Number of sessions deleted
        """
        return await self._store.delete_inactive_sessions(cutoff_date)

    async def aclose(self) -> None:
        """Close underlying session store connections (idempotent).

        Delegates to the wrapped store's aclose() method.
        Safe to call multiple times. Should be called during shutdown.
        """
        await self._store.aclose()


# =============================================================================
# Module Exports
# =============================================================================

__all__ = [
    "ENCRYPTED_MARKER",
    "EncryptedSessionStore",
]
