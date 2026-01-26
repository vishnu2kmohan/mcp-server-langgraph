"""
Contextvar-Based Session Storage Adapter

Provides a per-request user-scoped storage adapter using contextvars.
This pattern allows the singleton ChatServiceImpl to serve multiple users
safely by reading user_id from a contextvar set per-request.

v8 Implementation per Q6 decision:
- SessionService remains singleton, but user_id comes from ContextVar
- Adapter reads from contextvar instead of constructor parameter
- Safe for singleton ChatServiceImpl - user_id is per-request
- Avoids per-request expensive reinitialization

Addresses:
- Finding 11: Per-user adapters in singleton = cross-user leakage
- Finding 14: Per-request ChatServiceImpl reinitializes expensive deps
"""

from __future__ import annotations

from contextvars import ContextVar
from typing import TYPE_CHECKING, Any

if TYPE_CHECKING:
    from mcp_server_langgraph.api.v1.sessions import SessionService

# Contextvar set per-request by middleware
_current_user_id: ContextVar[str] = ContextVar("current_user_id", default="")


def set_current_user_id(user_id: str) -> None:
    """Set user_id for current request context.

    Called by UserContextMiddleware at request start.

    Args:
        user_id: Authenticated user ID from JWT token
    """
    _current_user_id.set(user_id)


def get_current_user_id() -> str:
    """Get user_id from current request context.

    Returns:
        User ID set by middleware, or empty string if not set
    """
    return _current_user_id.get()


class ContextvarSessionStorageAdapter:
    """Contextvar-based adapter for ChatService.

    Reads user_id from contextvar instead of constructor.
    Safe for singleton ChatServiceImpl - user_id is per-request.

    This adapter wraps SessionService and adds:
    1. User-scoped access control (reads user_id from contextvar)
    2. Ownership validation before read/write operations
    3. Returns None for unauthorized access (404 pattern)

    Example:
        # At request start (via middleware):
        set_current_user_id("user-123")

        # In ChatServiceImpl:
        adapter = ContextvarSessionStorageAdapter(session_service)
        messages = await adapter.get_messages("session-456")
        # Internally calls: session_service.get_session_messages("session-456", "user-123")
    """

    def __init__(self, session_service: SessionService) -> None:
        """Initialize adapter with session service.

        Args:
            session_service: SessionService instance (singleton)

        Note:
            NO user_id in constructor - comes from contextvar per-request.
        """
        self._service = session_service

    async def get_messages(self, session_id: str) -> list[dict[str, Any]] | None:
        """Load messages with ownership check.

        Reads user_id from contextvar set by middleware.

        Args:
            session_id: Session ID to load messages from

        Returns:
            List of message dicts if owned by current user, None otherwise
        """
        user_id = get_current_user_id()
        if not user_id:
            # No user context = unauthorized
            return None
        return await self._service.get_session_messages(session_id, user_id)

    async def add_message(
        self,
        session_id: str,
        message_data: dict[str, Any],
    ) -> dict[str, Any] | None:
        """Persist message with ownership check.

        Reads user_id from contextvar set by middleware.

        Args:
            session_id: Session ID to add message to
            message_data: Message dict with role, content, etc.

        Returns:
            Created message dict if session owned by current user, None otherwise
        """
        user_id = get_current_user_id()
        if not user_id:
            return None
        return await self._service.add_message(session_id, user_id, message_data)
