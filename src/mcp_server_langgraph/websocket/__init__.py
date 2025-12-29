"""
WebSocket Infrastructure Module.

Provides standardized WebSocket infrastructure for all endpoints including:
- Base class with lifecycle management
- Authentication middleware (JWT/Keycloak)
- Authorization middleware (OpenFGA ReBAC)
- Server-initiated heartbeat
- Rate limiting
- OpenTelemetry metrics and tracing

Usage:
    from mcp_server_langgraph.websocket import (
        WebSocketBase,
        WebSocketConfig,
        AuthUser,
        MessageEnvelope,
    )

    class MyWebSocket(WebSocketBase):
        config = WebSocketConfig(
            endpoint_name="my-endpoint",
            require_auth=True,
            authz_resource_type="dashboard",
            authz_required_relation="viewer",
        )

        async def handle_message(self, message: MessageEnvelope) -> MessageEnvelope | None:
            # Handle custom message types
            return None
"""

from typing import Any

from mcp_server_langgraph.websocket.exceptions import (
    AuthenticationError,
    AuthorizationError,
    ConnectionLimitError,
    HeartbeatTimeoutError,
    IdleTimeoutError,
    MessageSizeError,
    ProtocolError,
    ProtocolVersionError,
    RateLimitError,
    SubscriptionError,
    TokenExpiredError,
    WebSocketError,
)
from mcp_server_langgraph.websocket.types import (
    AuthUser,
    ConnectionState,
    MessageEnvelope,
    MessageType,
    WebSocketConfig,
    WebSocketHandler,
    WebSocketLifecycle,
)


# Lazy import for WebSocketBase to avoid circular imports
def __getattr__(name: str) -> Any:
    if name == "WebSocketBase":
        from mcp_server_langgraph.websocket.base import WebSocketBase

        return WebSocketBase
    if name == "WebSocketAuthorizationMiddleware":
        from mcp_server_langgraph.websocket.authz import WebSocketAuthorizationMiddleware

        return WebSocketAuthorizationMiddleware
    if name == "HeartbeatManager":
        from mcp_server_langgraph.websocket.heartbeat import HeartbeatManager

        return HeartbeatManager
    if name == "WebSocketMetrics":
        from mcp_server_langgraph.websocket.metrics import WebSocketMetrics

        return WebSocketMetrics
    if name == "WebSocketRateLimiter":
        from mcp_server_langgraph.websocket.rate_limiter import WebSocketRateLimiter

        return WebSocketRateLimiter
    if name == "MessageRateLimiter":
        from mcp_server_langgraph.websocket.rate_limiter import MessageRateLimiter

        return MessageRateLimiter
    if name == "UserRateLimiter":
        from mcp_server_langgraph.websocket.rate_limiter import UserRateLimiter

        return UserRateLimiter
    if name == "ConnectionRateLimiter":
        from mcp_server_langgraph.websocket.rate_limiter import ConnectionRateLimiter

        return ConnectionRateLimiter
    # Redis-backed rate limiters for distributed deployments
    if name == "RedisUserRateLimiter":
        from mcp_server_langgraph.websocket.rate_limiter import RedisUserRateLimiter

        return RedisUserRateLimiter
    if name == "RedisWebSocketRateLimiter":
        from mcp_server_langgraph.websocket.rate_limiter import RedisWebSocketRateLimiter

        return RedisWebSocketRateLimiter
    if name == "create_redis_rate_limiter":
        from mcp_server_langgraph.websocket.rate_limiter import create_redis_rate_limiter

        return create_redis_rate_limiter
    if name == "get_websocket_rate_limiter":
        from mcp_server_langgraph.websocket.rate_limiter import get_websocket_rate_limiter

        return get_websocket_rate_limiter
    # Resilience utilities
    if name == "with_circuit_breaker":
        from mcp_server_langgraph.websocket.resilience import with_circuit_breaker

        return with_circuit_breaker
    if name == "get_circuit_breaker_state":
        from mcp_server_langgraph.websocket.resilience import get_circuit_breaker_state

        return get_circuit_breaker_state
    if name == "is_circuit_open":
        from mcp_server_langgraph.websocket.resilience import is_circuit_open

        return is_circuit_open
    if name == "WebSocketServices":
        from mcp_server_langgraph.websocket.resilience import WebSocketServices

        return WebSocketServices
    # Middleware utilities
    if name == "extract_websocket_token":
        from mcp_server_langgraph.websocket.middleware import extract_websocket_token

        return extract_websocket_token
    if name == "validate_websocket_auth":
        from mcp_server_langgraph.websocket.middleware import validate_websocket_auth

        return validate_websocket_auth
    if name == "extract_user_from_jwt_payload":
        from mcp_server_langgraph.websocket.middleware import (
            extract_user_from_jwt_payload,
        )

        return extract_user_from_jwt_payload
    if name == "validate_websocket_token":
        from mcp_server_langgraph.websocket.middleware import validate_websocket_token

        return validate_websocket_token
    # Protocol version validation
    if name == "extract_protocol_version":
        from mcp_server_langgraph.websocket.protocols import extract_protocol_version

        return extract_protocol_version
    if name == "validate_protocol_version":
        from mcp_server_langgraph.websocket.protocols import validate_protocol_version

        return validate_protocol_version
    if name == "is_version_compatible":
        from mcp_server_langgraph.websocket.protocols import is_version_compatible

        return is_version_compatible
    if name == "PROTOCOL_VERSION":
        from mcp_server_langgraph.websocket.protocols import PROTOCOL_VERSION

        return PROTOCOL_VERSION
    raise AttributeError(f"module {__name__!r} has no attribute {name!r}")


__all__ = [
    # Base class
    "WebSocketBase",
    # Authorization
    "WebSocketAuthorizationMiddleware",
    # Heartbeat
    "HeartbeatManager",
    # Metrics
    "WebSocketMetrics",
    # Rate Limiting
    "WebSocketRateLimiter",
    "MessageRateLimiter",
    "UserRateLimiter",
    "ConnectionRateLimiter",
    # Redis-backed Rate Limiting (distributed deployments)
    "RedisUserRateLimiter",
    "RedisWebSocketRateLimiter",
    "create_redis_rate_limiter",
    "get_websocket_rate_limiter",
    # Types
    "AuthUser",
    "ConnectionState",
    "MessageEnvelope",
    "MessageType",
    "WebSocketConfig",
    "WebSocketHandler",
    "WebSocketLifecycle",
    # Exceptions
    "WebSocketError",
    "AuthenticationError",
    "AuthorizationError",
    "RateLimitError",
    "MessageSizeError",
    "ProtocolError",
    "ProtocolVersionError",
    "ConnectionLimitError",
    "IdleTimeoutError",
    "HeartbeatTimeoutError",
    "SubscriptionError",
    "TokenExpiredError",
    # Resilience
    "with_circuit_breaker",
    "get_circuit_breaker_state",
    "is_circuit_open",
    "WebSocketServices",
    # Middleware
    "extract_websocket_token",
    "validate_websocket_auth",
    "extract_user_from_jwt_payload",
    "validate_websocket_token",
    # Protocol Version Validation
    "extract_protocol_version",
    "validate_protocol_version",
    "is_version_compatible",
    "PROTOCOL_VERSION",
]
