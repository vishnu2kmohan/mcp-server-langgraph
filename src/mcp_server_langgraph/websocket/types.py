"""
WebSocket Types and Protocols.

Shared types for WebSocket infrastructure including message envelopes,
connection states, and configuration types.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from typing import Any, Protocol, runtime_checkable


class ConnectionState(str, Enum):
    """WebSocket connection state."""

    CONNECTING = "connecting"
    CONNECTED = "connected"
    AUTHENTICATING = "authenticating"
    AUTHORIZED = "authorized"
    DISCONNECTING = "disconnecting"
    DISCONNECTED = "disconnected"
    ERROR = "error"


class MessageType(str, Enum):
    """Reserved WebSocket message types."""

    # Client -> Server
    PING = "ping"
    SUBSCRIBE = "subscribe"
    UNSUBSCRIBE = "unsubscribe"

    # Server -> Client
    PONG = "pong"
    HEARTBEAT = "heartbeat"
    CONNECTED = "connected"
    ERROR = "error"
    SUBSCRIBED = "subscribed"
    UNSUBSCRIBED = "unsubscribed"


class AISuggestionMessageType(str, Enum):
    """
    Message types for AI suggestions WebSocket.

    Used for real-time AI suggestion features in the Studio frontend.
    Endpoint: /api/v1/ws/ai/suggestions
    """

    # Client -> Server
    SUGGESTION_REQUEST = "suggestion_request"
    SUGGESTION_ACCEPT = "suggestion_accept"
    SUGGESTION_REJECT = "suggestion_reject"
    CONTEXT_UPDATE = "context_update"

    # Server -> Client
    SUGGESTION_RESPONSE = "suggestion_response"
    ERROR = "error"


@dataclass
class AISuggestionRequest:
    """
    Request payload for AI suggestion.

    Sent by client to request an AI suggestion based on current input.
    """

    session_id: str
    input_text: str
    cursor_position: int
    context_window: int = 500  # Characters of context to include

    def to_dict(self) -> dict[str, Any]:
        """Convert to dictionary for JSON serialization."""
        return {
            "session_id": self.session_id,
            "input_text": self.input_text,
            "cursor_position": self.cursor_position,
            "context_window": self.context_window,
        }

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> AISuggestionRequest:
        """Create from dictionary (JSON deserialization)."""
        return cls(
            session_id=data.get("session_id", ""),
            input_text=data.get("input_text", ""),
            cursor_position=data.get("cursor_position", 0),
            context_window=data.get("context_window", 500),
        )


@dataclass
class AISuggestionResponse:
    """
    Response payload with AI suggestion.

    Sent by server with the generated suggestion.
    """

    suggestion_id: str
    text: str
    confidence: float
    reasoning: str | None = None

    def to_dict(self) -> dict[str, Any]:
        """Convert to dictionary for JSON serialization."""
        result: dict[str, Any] = {
            "suggestion_id": self.suggestion_id,
            "text": self.text,
            "confidence": self.confidence,
        }
        if self.reasoning is not None:
            result["reasoning"] = self.reasoning
        return result

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> AISuggestionResponse:
        """Create from dictionary (JSON deserialization)."""
        return cls(
            suggestion_id=data.get("suggestion_id", ""),
            text=data.get("text", ""),
            confidence=data.get("confidence", 0.0),
            reasoning=data.get("reasoning"),
        )


@dataclass
class AISuggestionError:
    """
    Error payload for AI suggestion failures.

    Includes retryable flag to indicate if client should retry.
    """

    code: str
    message: str
    retryable: bool = False

    def to_dict(self) -> dict[str, Any]:
        """Convert to dictionary for JSON serialization."""
        return {
            "code": self.code,
            "message": self.message,
            "retryable": self.retryable,
        }

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> AISuggestionError:
        """Create from dictionary (JSON deserialization)."""
        return cls(
            code=data.get("code", "unknown"),
            message=data.get("message", "Unknown error"),
            retryable=data.get("retryable", False),
        )


@dataclass
class MessageEnvelope:
    """
    Standard WebSocket message envelope.

    All WebSocket messages use this format for consistency.
    """

    type: str
    payload: dict[str, Any] | None = None
    id: str | None = None  # Correlation ID for request-response
    timestamp: datetime | None = None  # Server timestamp (outbound only)

    def to_dict(self) -> dict[str, Any]:
        """Convert to dictionary for JSON serialization."""
        result: dict[str, Any] = {"type": self.type}
        if self.payload is not None:
            result["payload"] = self.payload
        if self.id is not None:
            result["id"] = self.id
        if self.timestamp is not None:
            result["timestamp"] = self.timestamp.isoformat()
        return result

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> MessageEnvelope:
        """Create from dictionary (JSON deserialization)."""
        timestamp = None
        if "timestamp" in data and data["timestamp"]:
            timestamp = datetime.fromisoformat(data["timestamp"])
        return cls(
            type=data.get("type", "unknown"),
            payload=data.get("payload"),
            id=data.get("id"),
            timestamp=timestamp,
        )


@dataclass
class AuthUser:
    """
    Authenticated user context for WebSocket connections.

    Contains user identity and authorization information
    extracted from JWT token.
    """

    id: str
    username: str
    email: str | None = None
    roles: list[str] = field(default_factory=list)
    realm_access: dict[str, Any] = field(default_factory=dict)
    resource_access: dict[str, Any] = field(default_factory=dict)
    raw_claims: dict[str, Any] = field(default_factory=dict)

    @classmethod
    def from_jwt_payload(cls, payload: dict[str, Any]) -> AuthUser:
        """Create from JWT payload claims."""
        # Extract user_id with fallbacks
        # IMPORTANT: Use preferred_username first for OpenFGA compatibility
        # OpenFGA tuples use username format (user:admin, user:alice) not UUIDs
        # The 'sub' claim in Keycloak is a UUID which doesn't match our tuples
        user_id = (
            payload.get("preferred_username")
            or payload.get("username")
            or payload.get("sub")
            or payload.get("user_id")
            or "unknown"
        )

        # Extract username with fallbacks
        username = payload.get("preferred_username") or payload.get("username") or payload.get("name") or user_id

        # Extract roles from realm_access
        realm_access = payload.get("realm_access", {})
        roles = realm_access.get("roles", [])

        return cls(
            id=user_id,
            username=username,
            email=payload.get("email"),
            roles=roles,
            realm_access=realm_access,
            resource_access=payload.get("resource_access", {}),
            raw_claims=payload,
        )

    def has_role(self, role: str) -> bool:
        """Check if user has a specific role."""
        return role in self.roles

    def has_any_role(self, roles: list[str]) -> bool:
        """Check if user has any of the specified roles."""
        return any(role in self.roles for role in roles)


@dataclass
class WebSocketConfig:
    """
    Configuration for WebSocket endpoints.

    Provides configurable settings for authentication, rate limiting,
    heartbeat, and timeouts.
    """

    # Authentication
    require_auth: bool = True
    required_roles: list[str] = field(default_factory=list)

    # Authorization (OpenFGA)
    authz_resource_type: str | None = None
    authz_resource_id: str | None = None
    authz_required_relation: str = "viewer"
    authz_fail_closed: bool = True

    # Rate limiting
    rate_limit_per_minute: int = 600  # 10 msg/sec default
    rate_limit_burst: int = 50  # Allow burst

    # Heartbeat
    heartbeat_interval: int = 30  # Seconds
    heartbeat_timeout: int = 90  # 3 missed heartbeats = dead

    # Connection limits
    idle_timeout: int = 1800  # 30 minutes
    max_message_size: int = 1_000_000  # 1MB
    max_connections_per_user: int = 5

    # Message handling
    message_timeout: int = 30  # Seconds to process each message

    # Token validation
    token_validation_interval: int = 300  # Seconds between token expiration checks (5 min)

    # Metrics
    endpoint_name: str = "unknown"
    enable_tracing: bool = True  # Enable OpenTelemetry tracing


@runtime_checkable
class WebSocketHandler(Protocol):
    """
    Protocol for WebSocket message handlers.

    Implementations must provide handle_message for processing
    incoming messages.
    """

    async def handle_message(self, message: MessageEnvelope) -> MessageEnvelope | None:
        """
        Handle an incoming WebSocket message.

        Args:
            message: The incoming message envelope.

        Returns:
            Optional response message, or None if no response needed.
        """
        ...


@runtime_checkable
class WebSocketLifecycle(Protocol):
    """
    Protocol for WebSocket lifecycle hooks.

    Implementations can optionally provide lifecycle callbacks.
    """

    async def on_connect(self, user: AuthUser) -> None:
        """Called after successful authentication and authorization."""
        ...

    async def on_disconnect(self) -> None:
        """Called when connection is closed (normal or error)."""
        ...

    async def on_error(self, error: Exception) -> None:
        """Called when an error occurs during message processing."""
        ...
