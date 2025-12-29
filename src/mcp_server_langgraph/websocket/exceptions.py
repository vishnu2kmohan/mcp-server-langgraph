"""
WebSocket Exceptions.

Custom exceptions for WebSocket infrastructure including authentication,
authorization, rate limiting, and protocol errors.
"""

from __future__ import annotations


class WebSocketError(Exception):
    """Base exception for all WebSocket errors."""

    def __init__(
        self,
        message: str,
        code: int = 4000,
        reason: str | None = None,
    ) -> None:
        """
        Initialize WebSocket error.

        Args:
            message: Human-readable error message.
            code: WebSocket close code (4000-4999 for application errors).
            reason: Optional close reason sent to client.
        """
        super().__init__(message)
        self.code = code
        self.reason = reason or message


class AuthenticationError(WebSocketError):
    """Raised when WebSocket authentication fails."""

    def __init__(
        self,
        message: str = "Authentication required",
        code: int = 4001,
        reason: str | None = None,
    ) -> None:
        super().__init__(message, code, reason or "Authentication required")


class TokenExpiredError(AuthenticationError):
    """Raised when WebSocket token expires during active connection.

    This is a specialized authentication error with close code 4010,
    distinct from 4001 (initial auth failure) to allow clients to
    differentiate between "need to login" vs "need to refresh token".
    """

    def __init__(
        self,
        message: str = "Token expired",
        code: int = 4010,
        reason: str | None = None,
    ) -> None:
        super().__init__(message, code, reason or "Token expired. Please refresh and reconnect.")


class AuthorizationError(WebSocketError):
    """Raised when WebSocket authorization fails (OpenFGA check)."""

    def __init__(
        self,
        message: str = "Authorization denied",
        code: int = 4003,
        reason: str | None = None,
        resource: str | None = None,
        relation: str | None = None,
    ) -> None:
        super().__init__(message, code, reason or "Authorization denied")
        self.resource = resource
        self.relation = relation


class RateLimitError(WebSocketError):
    """Raised when rate limit is exceeded."""

    def __init__(
        self,
        message: str = "Rate limit exceeded",
        code: int = 4029,
        reason: str | None = None,
        retry_after: int | None = None,
    ) -> None:
        super().__init__(message, code, reason or "Rate limit exceeded")
        self.retry_after = retry_after


class MessageSizeError(WebSocketError):
    """Raised when message exceeds maximum size."""

    def __init__(
        self,
        message: str = "Message too large",
        code: int = 4013,
        reason: str | None = None,
        size: int | None = None,
        max_size: int | None = None,
    ) -> None:
        super().__init__(message, code, reason or "Message too large")
        self.size = size
        self.max_size = max_size


class ProtocolError(WebSocketError):
    """Raised when message format is invalid."""

    def __init__(
        self,
        message: str = "Invalid message format",
        code: int = 4002,
        reason: str | None = None,
    ) -> None:
        super().__init__(message, code, reason or "Invalid message format")


class ConnectionLimitError(WebSocketError):
    """Raised when connection limit is exceeded."""

    def __init__(
        self,
        message: str = "Connection limit exceeded",
        code: int = 4008,
        reason: str | None = None,
        current: int | None = None,
        limit: int | None = None,
    ) -> None:
        super().__init__(message, code, reason or "Connection limit exceeded")
        self.current = current
        self.limit = limit


class IdleTimeoutError(WebSocketError):
    """Raised when connection times out due to inactivity."""

    def __init__(
        self,
        message: str = "Connection timed out",
        code: int = 4008,
        reason: str | None = None,
        idle_seconds: int | None = None,
    ) -> None:
        super().__init__(message, code, reason or "Connection timed out due to inactivity")
        self.idle_seconds = idle_seconds


class HeartbeatTimeoutError(WebSocketError):
    """Raised when heartbeat response is not received."""

    def __init__(
        self,
        message: str = "Heartbeat timeout",
        code: int = 4008,
        reason: str | None = None,
        missed_count: int | None = None,
    ) -> None:
        super().__init__(message, code, reason or "Heartbeat timeout")
        self.missed_count = missed_count


class SubscriptionError(WebSocketError):
    """Raised when subscription operation fails."""

    def __init__(
        self,
        message: str = "Subscription failed",
        code: int = 4004,
        reason: str | None = None,
        resource_id: str | None = None,
    ) -> None:
        super().__init__(message, code, reason or "Subscription failed")
        self.resource_id = resource_id


class ProtocolVersionError(WebSocketError):
    """Raised when WebSocket protocol version is incompatible.

    This error uses close code 4009 to indicate that the client's
    protocol version is not compatible with the server version.
    Clients receiving this error should upgrade their client library.
    """

    def __init__(
        self,
        message: str = "Protocol version not supported",
        code: int = 4009,
        reason: str | None = None,
        client_version: str | None = None,
        server_version: str | None = None,
    ) -> None:
        super().__init__(message, code, reason or "Protocol version not supported. Please upgrade client.")
        self.client_version = client_version
        self.server_version = server_version


# WebSocket close codes reference:
# 1000 - Normal closure
# 1001 - Going away
# 1002 - Protocol error
# 1003 - Unsupported data
# 1007 - Invalid payload
# 1008 - Policy violation
# 1009 - Message too big
# 1010 - Extension required
# 1011 - Internal error
# 1012 - Service restart
# 1013 - Try again later
# 1014 - Bad gateway
# 1015 - TLS handshake failure
#
# Application-defined codes (4000-4999):
# 4000 - Generic application error
# 4001 - Authentication required (initial auth failure)
# 4002 - Invalid message format
# 4003 - Authorization denied
# 4004 - Resource not found / subscription failed
# 4008 - Timeout (idle, heartbeat, or connection limit)
# 4009 - Protocol version not supported (upgrade client)
# 4010 - Token expired (can refresh and reconnect)
# 4013 - Message too large
# 4029 - Rate limit exceeded (matches HTTP 429)
