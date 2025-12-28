"""
MCP WebSocket Connection Manager.

This module provides connection management for MCP WebSocket sessions,
including user context tracking, connection limits, and activity monitoring.

Migrated from: api.v1.mcp_websocket
"""

from __future__ import annotations

import logging
from dataclasses import dataclass, field
from datetime import datetime, UTC
from typing import Any, TYPE_CHECKING

if TYPE_CHECKING:
    pass

logger = logging.getLogger(__name__)

# Security limits
MAX_CONNECTIONS_PER_USER = 5
IDLE_TIMEOUT_SECONDS = 1800  # 30 minutes


def _utc_now() -> datetime:
    """Return current UTC time with timezone awareness."""
    return datetime.now(UTC)


@dataclass
class ConnectionInfo:
    """Metadata about a WebSocket connection."""

    websocket: Any  # WebSocket - use Any to avoid import issues
    session_id: str
    user_id: str | None = None
    roles: list[str] = field(default_factory=list)
    created_at: datetime = field(default_factory=_utc_now)
    last_activity: datetime = field(default_factory=_utc_now)
    message_count: int = 0


def update_connection_activity(conn_info: ConnectionInfo) -> None:
    """
    Update the last activity timestamp for a connection.

    Args:
        conn_info: The connection info to update.
    """
    conn_info.last_activity = _utc_now()


def is_connection_idle(conn_info: ConnectionInfo, timeout_seconds: int | None = None) -> bool:
    """
    Check if a connection has exceeded the idle timeout.

    Args:
        conn_info: The connection info to check.
        timeout_seconds: Optional custom timeout. Defaults to IDLE_TIMEOUT_SECONDS if not provided.

    Returns:
        True if the connection is idle (exceeded timeout), False otherwise.
    """
    now = _utc_now()
    elapsed = (now - conn_info.last_activity).total_seconds()
    timeout = timeout_seconds if timeout_seconds is not None else IDLE_TIMEOUT_SECONDS
    return elapsed > timeout


class ConnectionManager:
    """
    Manages WebSocket connections for MCP sessions.

    Tracks active connections by session ID with user context for:
    - Per-user connection limits
    - User-based message routing
    - Connection lifecycle tracking
    """

    def __init__(
        self,
        max_connections_per_user: int | None = None,
        idle_timeout_seconds: int | None = None,
    ) -> None:
        """
        Initialize the connection manager.

        Args:
            max_connections_per_user: Optional per-user connection limit.
                                      Defaults to MAX_CONNECTIONS_PER_USER if not provided.
            idle_timeout_seconds: Optional idle timeout in seconds.
                                  Defaults to IDLE_TIMEOUT_SECONDS if not provided.
        """
        self._connections: dict[str, ConnectionInfo] = {}
        self._user_connections: dict[str, list[str]] = {}  # user_id -> [session_ids]
        self.max_connections_per_user = (
            max_connections_per_user if max_connections_per_user is not None else MAX_CONNECTIONS_PER_USER
        )
        self.idle_timeout_seconds = idle_timeout_seconds if idle_timeout_seconds is not None else IDLE_TIMEOUT_SECONDS

    async def connect(
        self,
        websocket: Any,  # WebSocket type
        session_id: str,
        user_id: str | None = None,
        roles: list[str] | None = None,
    ) -> None:
        """
        Accept and track a new WebSocket connection.

        Args:
            websocket: The WebSocket to connect.
            session_id: Unique session identifier.
            user_id: Optional user ID for authenticated connections.
            roles: Optional list of user roles.
        """
        await websocket.accept()

        conn_info = ConnectionInfo(
            websocket=websocket,
            session_id=session_id,
            user_id=user_id,
            roles=roles or [],
        )
        self._connections[session_id] = conn_info

        # Track user connections
        if user_id:
            if user_id not in self._user_connections:
                self._user_connections[user_id] = []
            self._user_connections[user_id].append(session_id)

    def disconnect(self, session_id: str) -> None:
        """Remove a WebSocket connection."""
        if session_id in self._connections:
            conn_info = self._connections[session_id]
            # Remove from user tracking
            if conn_info.user_id and conn_info.user_id in self._user_connections:
                sessions = self._user_connections[conn_info.user_id]
                if session_id in sessions:
                    sessions.remove(session_id)
                if not sessions:
                    del self._user_connections[conn_info.user_id]
            del self._connections[session_id]

    def get_connection_count(self) -> int:
        """Get the number of active connections."""
        return len(self._connections)

    def get_user_connection_count(self, user_id: str) -> int:
        """
        Get the number of active connections for a user.

        Args:
            user_id: The user ID to check.

        Returns:
            Number of active connections for the user.
        """
        return len(self._user_connections.get(user_id, []))

    def can_user_connect(self, user_id: str) -> bool:
        """
        Check if a user can create a new connection.

        Args:
            user_id: The user ID to check.

        Returns:
            True if user is below connection limit.
        """
        return self.get_user_connection_count(user_id) < self.max_connections_per_user

    def has_connection(self, session_id: str) -> bool:
        """Check if a session has an active connection."""
        return session_id in self._connections

    def get_idle_connections(self) -> list[str]:
        """
        Get list of session IDs for connections that have exceeded idle timeout.

        Uses the configured idle_timeout_seconds for the check.

        Returns:
            List of session IDs for idle connections.
        """
        idle_sessions = []
        for session_id, conn_info in self._connections.items():
            if is_connection_idle(conn_info, timeout_seconds=self.idle_timeout_seconds):
                idle_sessions.append(session_id)
        return idle_sessions

    def update_activity(self, session_id: str) -> None:
        """
        Update the last activity timestamp for a connection.

        Args:
            session_id: The session ID to update.
        """
        if session_id in self._connections:
            update_connection_activity(self._connections[session_id])

    async def send_to_session(self, session_id: str, message: dict[str, Any]) -> None:
        """Send a message to a specific session."""
        if session_id in self._connections:
            await self._connections[session_id].websocket.send_json(message)

    async def broadcast(self, message: dict[str, Any]) -> None:
        """Broadcast a message to all connected sessions."""
        for conn_info in self._connections.values():
            try:
                await conn_info.websocket.send_json(message)
            except Exception as e:
                logger.warning(f"Failed to broadcast to session {conn_info.session_id}: {e}")

    async def broadcast_to_user(self, user_id: str, message: dict[str, Any]) -> None:
        """Broadcast a message to all sessions for a specific user."""
        session_ids = self._user_connections.get(user_id, [])
        for session_id in session_ids:
            if session_id in self._connections:
                try:
                    await self._connections[session_id].websocket.send_json(message)
                except Exception as e:
                    logger.warning(f"Failed to send to user {user_id} session {session_id}: {e}")


# Global connection manager singleton
_connection_manager: ConnectionManager | None = None


def get_connection_manager() -> ConnectionManager:
    """
    Get the global connection manager instance.

    Returns:
        The global ConnectionManager instance.
    """
    global _connection_manager
    if _connection_manager is None:
        _connection_manager = ConnectionManager()
    return _connection_manager


def set_connection_manager(manager: ConnectionManager) -> None:
    """
    Set the global connection manager instance.

    Used by bootstrap to inject a configured manager.

    Args:
        manager: The connection manager instance to set as global singleton.
    """
    global _connection_manager
    _connection_manager = manager


def create_connection_manager(
    streaming_settings: Any | None = None,
) -> ConnectionManager:
    """
    Create a ConnectionManager with optional StreamingSettings.

    Factory function that allows configuration injection for connection manager.

    Args:
        streaming_settings: Optional StreamingSettings instance with connection config.

    Returns:
        A ConnectionManager instance with configured connection limit and idle timeout.
    """
    if streaming_settings is None:
        return ConnectionManager()

    return ConnectionManager(
        max_connections_per_user=streaming_settings.streaming_max_connections_per_user,
        idle_timeout_seconds=streaming_settings.streaming_idle_timeout_seconds,
    )
