"""
MCP WebSocket Rate Limiting.

This module provides rate limiting for MCP WebSocket streaming,
including outbound notification throttling and per-user message limits.

The UserRateLimiterManager is an alias for the consolidated UserRateLimiter
from websocket.rate_limiter for backward compatibility.

Migrated from: api.v1.mcp_websocket
"""

from __future__ import annotations

import asyncio
import logging
from datetime import datetime, UTC
from typing import Any

logger = logging.getLogger(__name__)


def _utc_now() -> datetime:
    """Return current UTC time with timezone awareness."""
    return datetime.now(UTC)


# =============================================================================
# UserRateLimiterManager (alias for backward compatibility)
# =============================================================================

# Re-export UserRateLimiter as UserRateLimiterManager for backward compatibility
from mcp_server_langgraph.websocket.rate_limiter import UserRateLimiter as UserRateLimiterManager


# =============================================================================
# OutboundRateLimiter (MCP-specific, token bucket)
# =============================================================================


class OutboundRateLimiter:
    """
    Rate limiter for outbound streaming notifications.

    Uses token bucket algorithm to limit notifications per second.
    Prevents overwhelming clients with too many rapid chunk notifications.
    """

    def __init__(self, max_notifications_per_second: int = 100) -> None:
        """
        Initialize the outbound rate limiter.

        Args:
            max_notifications_per_second: Maximum notifications allowed per second.
        """
        self.max_notifications_per_second = max_notifications_per_second
        self._tokens = float(max_notifications_per_second)
        self._last_refill = _utc_now()
        self._interval = 1.0 / max_notifications_per_second if max_notifications_per_second > 0 else 0.0

    async def check_and_wait(self) -> None:
        """
        Check if a notification can be sent, waiting if necessary.

        Uses token bucket algorithm to smooth out notification rate.
        """
        now = _utc_now()
        elapsed = (now - self._last_refill).total_seconds()

        # Refill tokens based on elapsed time
        self._tokens = min(
            float(self.max_notifications_per_second),
            self._tokens + elapsed * self.max_notifications_per_second,
        )
        self._last_refill = now

        # If no tokens available, wait
        if self._tokens < 1.0:
            wait_time = (1.0 - self._tokens) / self.max_notifications_per_second
            await asyncio.sleep(wait_time)
            self._tokens = 1.0
            self._last_refill = _utc_now()

        # Consume a token
        self._tokens -= 1.0


# =============================================================================
# Global Singletons and Accessors
# =============================================================================

# Global user rate limiter
_user_rate_limiter: UserRateLimiterManager | None = None

# Default values
DEFAULT_MAX_MESSAGES_PER_MINUTE = 60
DEFAULT_WINDOW_SECONDS = 60


def get_user_rate_limiter() -> UserRateLimiterManager:
    """
    Get the global user rate limiter instance.

    Returns:
        The global UserRateLimiterManager instance.
    """
    global _user_rate_limiter
    if _user_rate_limiter is None:
        _user_rate_limiter = UserRateLimiterManager(
            max_messages=DEFAULT_MAX_MESSAGES_PER_MINUTE,
            window_seconds=DEFAULT_WINDOW_SECONDS,
        )
    return _user_rate_limiter


def set_user_rate_limiter(limiter: UserRateLimiterManager) -> None:
    """
    Set the global user rate limiter instance.

    Args:
        limiter: The rate limiter instance to set as global singleton.
    """
    global _user_rate_limiter
    _user_rate_limiter = limiter


def create_user_rate_limiter(streaming_settings: Any | None = None) -> UserRateLimiterManager:
    """
    Create a UserRateLimiterManager with optional streaming settings.

    Args:
        streaming_settings: Optional settings with streaming_max_messages_per_minute.

    Returns:
        A new UserRateLimiterManager instance.
    """
    if streaming_settings is None:
        return UserRateLimiterManager(
            max_messages=DEFAULT_MAX_MESSAGES_PER_MINUTE,
            window_seconds=DEFAULT_WINDOW_SECONDS,
        )

    return UserRateLimiterManager(
        max_messages=streaming_settings.streaming_max_messages_per_minute,
        window_seconds=DEFAULT_WINDOW_SECONDS,
    )


# Global outbound rate limiter
_outbound_rate_limiter: OutboundRateLimiter | None = None


def get_outbound_rate_limiter() -> OutboundRateLimiter | None:
    """
    Get the global outbound rate limiter instance.

    Returns:
        The global OutboundRateLimiter instance, or None if not configured.
    """
    return _outbound_rate_limiter


def set_outbound_rate_limiter(limiter: OutboundRateLimiter | None) -> None:
    """
    Set the global outbound rate limiter instance.

    Args:
        limiter: The rate limiter instance to set as global singleton.
    """
    global _outbound_rate_limiter
    _outbound_rate_limiter = limiter


def create_outbound_rate_limiter(streaming_settings: Any | None = None) -> OutboundRateLimiter:
    """
    Create an OutboundRateLimiter with optional streaming settings.

    Args:
        streaming_settings: Optional settings with streaming_max_notifications_per_second.

    Returns:
        A new OutboundRateLimiter instance.
    """
    if streaming_settings is None:
        return OutboundRateLimiter()

    return OutboundRateLimiter(
        max_notifications_per_second=streaming_settings.streaming_max_notifications_per_second,
    )
