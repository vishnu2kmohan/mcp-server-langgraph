# WebSocket Standardization

**ADR Reference**: ADR-0068 WebSocket Standardization, ADR-0074 WebSocket Token Expiration
**Status**: Active
**Last Updated**: 2026-01-17
**Owner**: Infrastructure Team

## Table of Contents

- [Overview](#overview)
- [Architecture](#architecture)
- [Available Endpoints](#available-endpoints)
- [Standard Infrastructure Features](#standard-infrastructure-features)
- [Configuration](#configuration)
- [Error Handling](#error-handling)
- [Message Format](#message-format)
- [Implementation Guide](#implementation-guide)
- [Migration Status](#migration-status)
- [Observability](#observability)
- [Security Considerations](#security-considerations)
- [Performance Optimization](#performance-optimization)
- [WebSocket Permissions and Sub-Persona Architecture](#websocket-permissions-and-sub-persona-architecture)
- [References](#references)

---

## Overview

ADR-0068 introduces a **consolidated WebSocket router pattern** that standardizes all WebSocket endpoints under a unified infrastructure. This standardization provides:

- **Consistent URL structure**: All WebSocket endpoints under `/api/v1/ws/*`
- **Unified authentication/authorization**: JWT + OpenFGA for all endpoints
- **Standard lifecycle management**: Connection, authentication, message handling, disconnection
- **Built-in observability**: OpenTelemetry tracing and metrics for all connections
- **Rate limiting**: Per-user, per-endpoint rate limiting with Redis/in-memory backends
- **Server heartbeat**: Automatic dead connection detection
- **Graceful error handling**: Standardized error codes and message format

### Key Benefits

1. **Developer Experience**: Single `WebSocketBase` class to extend for new endpoints
2. **Security**: Consistent authentication/authorization across all WebSocket connections
3. **Observability**: Automatic tracing, metrics, and logging for all WebSocket traffic
4. **Reliability**: Built-in heartbeat, timeout enforcement, and error handling
5. **Performance**: Rate limiting prevents abuse, connection pooling optimizes resources

---

## Architecture

### WebSocketBase Class

All WebSocket endpoints extend `WebSocketBase`, which provides:

```python
from mcp_server_langgraph.websocket.base import WebSocketBase
from mcp_server_langgraph.websocket.types import WebSocketConfig, MessageEnvelope

class MyWebSocketHandler(WebSocketBase):
    async def handle_message(self, message: MessageEnvelope) -> MessageEnvelope | None:
        # Handle custom message types
        if message.type == "my_action":
            return MessageEnvelope(type="my_response", payload={"ok": True})
        return None
```

### Lifecycle Phases

1. **CONNECTING**: Client initiates WebSocket connection
2. **CONNECTED**: Connection accepted, awaiting authentication
3. **AUTHENTICATING**: JWT token validation via Keycloak
4. **AUTHORIZED**: OpenFGA authorization check (if configured)
5. **Message Loop**: Handle incoming messages, send responses
6. **DISCONNECTING**: Graceful shutdown initiated
7. **DISCONNECTED**: Connection closed, cleanup complete

### Components

- **WebSocketBase**: Abstract base class for all handlers
- **WebSocketConfig**: Configuration dataclass (auth, rate limits, timeouts)
- **MessageEnvelope**: Standard message wrapper (type, payload, id, timestamp)
- **HeartbeatManager**: Server-initiated ping/pong for connection health
- **WebSocketAuthorizationMiddleware**: OpenFGA integration for fine-grained access control
- **WebSocketMetrics**: OpenTelemetry metrics collector

---

## Available Endpoints

All endpoints are mounted under the **consolidated router** at `/api/v1/ws/*`:

### Chat & Messaging

#### `/api/v1/ws/notifications`
- **Purpose**: Real-time notification streaming to users
- **Auth**: Required (JWT + OpenFGA)
- **Authorization**: `chat:notifications` with `viewer` relation
- **Rate Limit**: 100 messages/minute
- **Message Types**: `notification`, `subscribe`, `unsubscribe`

#### `/api/v1/ws/ai/suggestions`
- **Purpose**: Real-time AI-powered typing suggestions for Studio frontend
- **Auth**: Required (JWT + OpenFGA)
- **Authorization**: `ai:suggestions` with `user` relation
- **Rate Limit**: 300 messages/minute
- **Max Message Size**: 64KB
- **Message Types**: `suggestion_request`, `suggestion_response`, `suggestion_accept`, `suggestion_reject`, `context_update`

### MCP Protocol

#### `/api/v1/ws/mcp`
- **Purpose**: MCP 2025-11-25 compliant JSON-RPC 2.0 over WebSocket
- **Auth**: Optional (anonymous allowed)
- **Rate Limit**: 600 messages/minute (10 msg/sec)
- **Heartbeat**: 30-second interval
- **Idle Timeout**: 30 minutes
- **Features**: MCP protocol methods (initialize, tools/*, resources/*, prompts/*), elicitation, sampling, streaming extensions ($/streaming/*), trace extensions ($/trace/*)

#### `/api/v1/ws/mcp/auth`
- **Purpose**: Authenticated MCP WebSocket with full security
- **Auth**: Required (JWT + OpenFGA)
- **Authorization**: `mcp:websocket` with `user` relation
- **Rate Limit**: 600 messages/minute

#### `/api/v1/ws/mcp/{session_id}`
- **Purpose**: MCP WebSocket with explicit session ID for resumption
- **Auth**: Optional
- **Rate Limit**: 600 messages/minute

#### `/api/v1/ws/mcp/tasks`
- **Purpose**: Real-time MCP task status updates
- **Auth**: Required (JWT + OpenFGA)
- **Authorization**: `mcp:websocket` with `user` relation
- **Rate Limit**: 600 messages/minute
- **Message Timeout**: 30 seconds

### Workflows

#### `/api/v1/ws/workflows/{workflow_id}`
- **Purpose**: Real-time workflow execution updates
- **Auth**: Required (JWT + OpenFGA)
- **Authorization**: `workflow:{workflow_id}` with `executor` relation
- **Rate Limit**: 300 messages/minute
- **Message Timeout**: 60 seconds (longer for workflow operations)
- **Events**: Node status updates, execution logs, completion/error notifications

### Monitoring & Observability

#### `/api/v1/ws/alerts`
- **Purpose**: Real-time infrastructure alert streaming to admins
- **Auth**: Required (JWT + OpenFGA)
- **Authorization**: `dashboard:alerts` with `admin` relation
- **Rate Limit**: 100 messages/minute
- **Message Types**: `subscribe`, `unsubscribe`, `get_recent`, alert notifications

#### `/api/v1/ws/audit`
- **Purpose**: Real-time audit event streaming for compliance monitoring
- **Auth**: Required (JWT + OpenFGA)
- **Authorization**: `logs:audit` with `viewer` relation
- **Rate Limit**: 100 messages/minute
- **Features**: Filter by category, regulation, actor

#### `/api/v1/ws/metrics/heart`
- **Purpose**: Real-time HEART metrics streaming (Happiness, Engagement, Adoption, Retention, Task success)
- **Auth**: Required (JWT + OpenFGA)
- **Authorization**: `observability:heart` with `viewer` relation
- **Rate Limit**: 100 messages/minute
- **Replaces**: Polling-based `useHeartDashboard.ts` hook

#### `/api/v1/ws/usage/cost`
- **Purpose**: Real-time cost tracking during LLM operations
- **Auth**: Required (JWT + OpenFGA)
- **Authorization**: `cost:usage` with `viewer` relation
- **Rate Limit**: 200 messages/minute
- **Features**: Real-time cost updates, budget monitoring, alerts

### Connections & Infrastructure

#### `/api/v1/ws/connections/realtime`
- **Purpose**: Real-time connection status updates for ConnectionsPage
- **Auth**: Required (JWT + OpenFGA)
- **Authorization**: `mcp_connection:realtime` with `viewer` relation
- **Rate Limit**: 300 messages/minute
- **Replaces**: Polling-based connection status checks

#### `/api/v1/ws/connections/health`
- **Purpose**: Real-time connection health monitoring
- **Auth**: Required (JWT + OpenFGA)
- **Authorization**: `mcp_connection:health` with `viewer` relation
- **Rate Limit**: 300 messages/minute
- **Features**: All connection statuses on connect, subscribe to specific connections, health check requests

### Human-in-the-Loop (HITL)

#### `/api/v1/ws/agents/requests`
- **Purpose**: Real-time HITL notifications for agent approval requests
- **Auth**: Required (JWT + OpenFGA)
- **Authorization**: `workflow:hitl` with `editor` relation
- **Rate Limit**: 200 messages/minute
- **Query Params**: `session_id` (optional) to filter messages
- **Events**: Approval requests (low confidence triggers), clarification requests, status updates

---

## Standard Infrastructure Features

### 1. JWT Authentication on Connection

All authenticated endpoints validate JWT tokens from:
- **Query parameter**: `?token=<jwt>`
- **Authorization header**: `Authorization: Bearer <jwt>`

Token validation via Keycloak integration using `AuthMiddleware`.

**User Extraction**:
```python
# From JWT payload
user = AuthUser(
    id=payload["sub"],
    username=payload.get("preferred_username", "unknown"),
    roles=payload.get("realm_access", {}).get("roles", []),
)
```

**Anonymous Connections**:
Endpoints with `require_auth=False` allow anonymous connections:
```python
config = WebSocketConfig(
    endpoint_name="mcp",
    require_auth=False,  # Anonymous allowed
)
```

### 2. Server Heartbeat (30-second ping/pong)

**Purpose**: Detect dead connections early and prevent resource leaks.

**Mechanism**:
- Server sends `heartbeat` message every 30 seconds
- Client must respond with `pong` within 90 seconds (3 missed heartbeats)
- Connection closed if no `pong` received

**Configuration**:
```python
config = WebSocketConfig(
    heartbeat_interval=30,  # Send heartbeat every 30s
    heartbeat_timeout=90,   # Close after 3 missed heartbeats
)
```

**Feature Flag**:
```bash
FF_WEBSOCKET_SERVER_HEARTBEAT=true  # Default: true
```

**Message Format**:
```json
// Server -> Client
{
  "type": "heartbeat",
  "timestamp": "2025-12-26T10:30:00.000Z",
  "id": "hb_abc123"
}

// Client -> Server
{
  "type": "pong",
  "id": "hb_abc123"
}
```

### 3. OpenTelemetry Metrics Integration

All WebSocket connections automatically emit metrics to OpenTelemetry:

**Metrics Collected**:
- `websocket.connections.active` (Gauge): Active connections per endpoint
- `websocket.connections.total` (Counter): Total connections established
- `websocket.connections.rejected` (Counter): Connections rejected (auth/authz failed)
- `websocket.messages.received` (Counter): Messages received by type
- `websocket.messages.sent` (Counter): Messages sent by type
- `websocket.message.latency` (Histogram): Message processing latency
- `websocket.errors` (Counter): Errors by type
- `websocket.rate_limit.exceeded` (Counter): Rate limit violations per user

**Attributes**:
- `endpoint`: Endpoint name (e.g., `mcp`, `notifications`)
- `user_id`: Authenticated user ID
- `message_type`: Message type (e.g., `ping`, `subscribe`)
- `error_type`: Error type (e.g., `timeout`, `rate_limit_exceeded`)

**Feature Flag**:
```bash
FF_WEBSOCKET_ENHANCED_METRICS=true  # Default: true
```

### 4. Rate Limiting Per Connection

**Per-User Rate Limiting**:
- In-memory (default): `TokenBucketRateLimiter` (fast, local)
- Redis-backed (distributed): `RedisRateLimiter` (multi-instance deployments)

**Configuration**:
```python
config = WebSocketConfig(
    rate_limit_per_minute=600,  # 10 msg/sec
    rate_limit_burst=50,        # Allow burst of 50 messages
)
```

**Feature Flag**:
```bash
FF_WEBSOCKET_RATE_LIMIT_PER_MINUTE=600  # Default: 600
```

**Backend Selection**:
```bash
FF_ENABLE_DISTRIBUTED_RATE_LIMITING=true  # Use Redis (default: false)
```

**Rate Limit Response**:
When rate limit is exceeded, the server sends an error message:
```json
{
  "type": "error",
  "payload": {
    "code": "rate_limit_exceeded",
    "message": "Rate limit exceeded",
    "rate_limit": {
      "limit": 600,
      "remaining": 0,
      "retry_after": 60
    }
  },
  "id": "corr_xyz789",
  "timestamp": "2025-12-26T10:30:00.000Z"
}
```

---

## Configuration

### Feature Flags

All WebSocket infrastructure features are controlled via environment variables (feature flags):

#### Core Infrastructure Flags

```bash
# Enable new WebSocketBase infrastructure (vs legacy handlers)
FF_ENABLE_WEBSOCKET_NEW_BASE=true  # Default: true

# Enable server-initiated heartbeat
FF_ENABLE_WEBSOCKET_SERVER_HEARTBEAT=true  # Default: true

# Enable enhanced metrics collection
FF_ENABLE_WEBSOCKET_ENHANCED_METRICS=true  # Default: true
```

#### Heartbeat Configuration

```bash
# Heartbeat interval in seconds
FF_WEBSOCKET_HEARTBEAT_INTERVAL_SECONDS=30  # Default: 30

# Heartbeat timeout in seconds (must be > 2x interval)
FF_WEBSOCKET_HEARTBEAT_TIMEOUT_SECONDS=90  # Default: 90
```

#### Idle Timeout

```bash
# Idle timeout in seconds (close connection after inactivity)
FF_WEBSOCKET_IDLE_TIMEOUT_SECONDS=1800  # Default: 1800 (30 minutes)
```

#### Rate Limiting

```bash
# Rate limit per minute per user
FF_WEBSOCKET_RATE_LIMIT_PER_MINUTE=600  # Default: 600 (10 msg/sec)

# Enable Redis-backed distributed rate limiting
FF_ENABLE_DISTRIBUTED_RATE_LIMITING=false  # Default: false
```

### WebSocketConfig Dataclass

```python
from mcp_server_langgraph.websocket.types import WebSocketConfig

config = WebSocketConfig(
    # Endpoint identification
    endpoint_name="my-endpoint",

    # Authentication
    require_auth=True,
    required_roles=["user", "admin"],

    # Authorization (OpenFGA)
    authz_resource_type="workflow",
    authz_resource_id="hitl",
    authz_required_relation="editor",
    authz_fail_closed=True,  # Fail-closed on authz errors

    # Rate limiting
    rate_limit_per_minute=600,
    rate_limit_burst=50,

    # Heartbeat
    heartbeat_interval=30,
    heartbeat_timeout=90,

    # Connection limits
    idle_timeout=1800,
    max_message_size=1_000_000,  # 1MB
    max_connections_per_user=5,

    # Message timeout
    message_timeout=30,  # Timeout for handle_message() execution
)
```

---

## Error Handling

### Standard Error Format

All errors follow the standard `MessageEnvelope` format with `type="error"`:

```json
{
  "type": "error",
  "payload": {
    "code": "error_code",
    "message": "Human-readable error message"
  },
  "id": "correlation_id",  // Optional: ID of request that caused error
  "timestamp": "2025-12-26T10:30:00.000Z"
}
```

### Error Codes

WebSocket errors use **application-defined close codes** (4000-4999) and **error codes** in message payloads:

#### WebSocket Close Codes

| Code | Exception | Reason | Description |
|------|-----------|--------|-------------|
| `4000` | `WebSocketError` | Generic error | Generic application error |
| `4001` | `AuthenticationError` | Authentication required | JWT token missing, invalid, or initial auth failure |
| `4002` | `ProtocolError` | Invalid message format | Message does not conform to `MessageEnvelope` schema |
| `4003` | `AuthorizationError` | Authorization denied | OpenFGA check failed for resource access |
| `4004` | `SubscriptionError` | Subscription failed | Failed to subscribe to resource (not found, authz denied) |
| `4008` | `IdleTimeoutError`, `HeartbeatTimeoutError`, `ConnectionLimitError` | Timeout / Limit exceeded | Connection idle timeout, heartbeat timeout, or max connections exceeded |
| `4009` | `ProtocolVersionError` | Protocol version mismatch | Client protocol version incompatible with server - client must refresh page or update (NOT recoverable) |
| `4010` | `TokenExpiredError` | Token expired | JWT token expired during active connection - client should refresh and reconnect (ADR-0074) |
| `4013` | `MessageSizeError` | Message too large | Message exceeds `max_message_size` limit |
| `4029` | `RateLimitError` | Rate limit exceeded | User exceeded `rate_limit_per_minute` quota |

#### Message Error Codes

| Code | Description | Retryable | Example |
|------|-------------|-----------|---------|
| `invalid_json` | JSON parsing failed | No | Malformed JSON in message |
| `invalid_message` | Missing required fields in `MessageEnvelope` | No | Missing `type` field |
| `processing_error` | Error during `handle_message()` | Maybe | Handler raised exception |
| `timeout` | Message processing timed out | Yes | `handle_message()` exceeded `message_timeout` |
| `rate_limit_exceeded` | Rate limit quota exceeded | Yes | Too many messages in time window |
| `auth_failed` | Authentication failed | No | Invalid JWT token |
| `authz_denied` | Authorization denied | No | OpenFGA check failed |
| `subscription_failed` | Subscription to resource failed | Maybe | Resource not found or authz denied |

### Error Response Examples

#### Authentication Error
```json
{
  "type": "error",
  "payload": {
    "code": "auth_failed",
    "message": "Authentication required"
  },
  "timestamp": "2025-12-26T10:30:00.000Z"
}
// Connection closed with code 4001
```

#### Token Expired Error (ADR-0074)
```json
{
  "type": "error",
  "payload": {
    "code": "token_expired",
    "message": "Token expired. Please refresh and reconnect."
  },
  "timestamp": "2025-12-28T10:30:00.000Z"
}
// Connection closed with code 4010
// Client should: 1) Refresh token, 2) Reconnect with new token
```

#### Protocol Version Mismatch Error
```json
{
  "type": "error",
  "payload": {
    "code": "protocol_version_mismatch",
    "message": "Protocol version mismatch. Client: 2.0.0, Server: 1.0.0. Please refresh the page or update your client."
  },
  "timestamp": "2025-12-28T10:30:00.000Z"
}
// Connection closed with code 4009
// NOT RECOVERABLE - Client should: 1) Show user-friendly message, 2) Suggest page refresh or app update
// DO NOT attempt reconnection (version mismatch will persist)
```

#### Rate Limit Error
```json
{
  "type": "error",
  "payload": {
    "code": "rate_limit_exceeded",
    "message": "Rate limit exceeded",
    "rate_limit": {
      "limit": 600,
      "remaining": 0,
      "retry_after": 60
    }
  },
  "id": "msg_abc123",
  "timestamp": "2025-12-26T10:30:00.000Z"
}
// Connection remains open, retry after 60 seconds
```

#### Timeout Error
```json
{
  "type": "error",
  "payload": {
    "code": "timeout",
    "message": "Message processing timed out after 30s"
  },
  "id": "msg_xyz789",
  "timestamp": "2025-12-26T10:30:00.000Z"
}
// Connection remains open, can retry
```

### Exception Hierarchy

```
WebSocketError
├── AuthenticationError (4001)
│   └── TokenExpiredError (4010) - Token expired during active connection
├── AuthorizationError (4003)
├── ProtocolError (4002)
├── ProtocolVersionError (4009) - Client/server version incompatible (not recoverable)
├── RateLimitError (4029)
├── MessageSizeError (4013)
├── ConnectionLimitError (4008)
├── IdleTimeoutError (4008)
├── HeartbeatTimeoutError (4008)
└── SubscriptionError (4004)
```

All exceptions in `src/mcp_server_langgraph/websocket/exceptions.py`.

---

## Message Format

### MessageEnvelope

All messages use the standard `MessageEnvelope` format:

```python
from mcp_server_langgraph.websocket.types import MessageEnvelope

message = MessageEnvelope(
    type="message_type",      # Required: Message type (e.g., "ping", "subscribe")
    payload={"key": "value"}, # Optional: Message payload (JSON-serializable dict)
    id="unique_id",           # Optional: Correlation ID for request/response
    timestamp=datetime.now(UTC),  # Optional: Message timestamp (auto-added if missing)
)
```

**JSON Representation**:
```json
{
  "type": "message_type",
  "payload": {
    "key": "value"
  },
  "id": "unique_id",
  "timestamp": "2025-12-26T10:30:00.000Z"
}
```

### Reserved Message Types

Reserved types handled by `WebSocketBase` (not forwarded to `handle_message()`):

| Type | Direction | Purpose | Payload |
|------|-----------|---------|---------|
| `ping` | Client -> Server | Client-initiated connection health check | `{}` |
| `pong` | Server -> Client | Response to `ping` or server heartbeat | `{}` |
| `heartbeat` | Server -> Client | Server-initiated connection health check | `{}` |
| `subscribe` | Client -> Server | Subscribe to resource updates | `{"resource_id": "..."}` |
| `unsubscribe` | Client -> Server | Unsubscribe from resource updates | `{"resource_id": "..."}` |
| `subscribed` | Server -> Client | Confirmation of subscription | `{"resource_id": "..."}` |
| `unsubscribed` | Server -> Client | Confirmation of unsubscription | `{"resource_id": "..."}` |
| `connected` | Server -> Client | Connection established (after auth/authz) | `{"user_id": "..."}` |
| `error` | Server -> Client | Error response | `{"code": "...", "message": "..."}` |

### Custom Message Types

Handlers define custom message types for endpoint-specific functionality:

**Example: AI Suggestions**
```python
from mcp_server_langgraph.websocket.types import AISuggestionMessageType

# Client -> Server
{
  "type": "suggestion_request",
  "payload": {
    "session_id": "sess_123",
    "input_text": "def calculate_",
    "cursor_position": 15,
    "context_window": 500
  },
  "id": "req_abc123"
}

# Server -> Client
{
  "type": "suggestion_response",
  "payload": {
    "suggestion_id": "sugg_xyz789",
    "text": "total(items: list[float]) -> float:",
    "confidence": 0.92,
    "reasoning": "Pattern matches previous function definitions"
  },
  "id": "req_abc123",  // Same ID as request
  "timestamp": "2025-12-26T10:30:00.000Z"
}
```

---

## Implementation Guide

### Creating a New WebSocket Endpoint

**Step 1: Define Handler**

```python
# src/mcp_server_langgraph/websocket/handlers/my_feature.py
from mcp_server_langgraph.websocket.base import WebSocketBase
from mcp_server_langgraph.websocket.types import MessageEnvelope, WebSocketConfig

class MyFeatureHandler(WebSocketBase):
    def __init__(self, config: WebSocketConfig, my_service: MyService):
        super().__init__(config)
        self.service = my_service

    async def handle_message(self, message: MessageEnvelope) -> MessageEnvelope | None:
        if message.type == "get_data":
            data = await self.service.get_data(message.payload.get("id"))
            return MessageEnvelope(
                type="data_response",
                payload={"data": data},
                id=message.id,
            )
        return None

    async def on_connect(self, user: AuthUser) -> None:
        # Optional: Setup when connection established
        await self.service.register_connection(user.id)

    async def on_disconnect(self) -> None:
        # Optional: Cleanup when connection ends
        if self.user:
            await self.service.unregister_connection(self.user.id)
```

**Step 2: Add Endpoint to Router**

```python
# src/mcp_server_langgraph/api/v1/ws_router.py
from mcp_server_langgraph.websocket.handlers.my_feature import MyFeatureHandler

@ws_router.websocket("/my-feature")
async def my_feature_websocket(websocket: WebSocket) -> None:
    """
    WebSocket endpoint for my feature.

    URL: /api/v1/ws/my-feature
    """
    handler = MyFeatureHandler(
        config=WebSocketConfig(
            endpoint_name="my-feature",
            require_auth=True,
            authz_resource_type="feature",
            authz_resource_id="my-feature",
            authz_required_relation="user",
            rate_limit_per_minute=300,
            message_timeout=30,
        ),
        my_service=get_my_service(),
    )
    await handler.run(websocket)
```

**Step 3: Add Tests**

```python
# tests/unit/ws_handlers/test_my_feature.py
import pytest
from mcp_server_langgraph.websocket.handlers.my_feature import MyFeatureHandler
from mcp_server_langgraph.websocket.types import MessageEnvelope

@pytest.mark.unit
@pytest.mark.asyncio
async def test_my_feature_handler():
    # GIVEN: Handler with mock service
    handler = MyFeatureHandler(
        config=WebSocketConfig(endpoint_name="test"),
        my_service=MockMyService(),
    )

    # WHEN: Client sends get_data message
    request = MessageEnvelope(type="get_data", payload={"id": "123"})
    response = await handler.handle_message(request)

    # THEN: Response contains data
    assert response is not None
    assert response.type == "data_response"
    assert "data" in response.payload
```

### Testing WebSocket Endpoints

**Manual Testing with wscat**:
```bash
# Install wscat
npm install -g wscat

# Connect to endpoint
wscat -c "ws://localhost:8000/api/v1/ws/my-feature?token=<jwt>"

# Send message
{"type": "get_data", "payload": {"id": "123"}, "id": "req_1"}

# Receive response
{"type": "data_response", "payload": {"data": {...}}, "id": "req_1", "timestamp": "..."}
```

**Python Client Example**:
```python
import asyncio
import websockets
import json

async def test_websocket():
    uri = "ws://localhost:8000/api/v1/ws/my-feature?token=<jwt>"
    async with websockets.connect(uri) as websocket:
        # Send message
        await websocket.send(json.dumps({
            "type": "get_data",
            "payload": {"id": "123"},
            "id": "req_1"
        }))

        # Receive response
        response = await websocket.recv()
        data = json.loads(response)
        print(f"Received: {data}")

asyncio.run(test_websocket())
```

### WebSocketBase API Reference

The `WebSocketBase` class provides several helper properties and methods to reduce boilerplate
in handler implementations. Always prefer these over direct attribute access.

#### Properties

| Property | Type | Description |
|----------|------|-------------|
| `user_id` | `str \| None` | Authenticated user's ID (from `_user.id`) |
| `context_id` | `str \| None` | Context ID from query params (for scoped operations) |
| `session_id` | `str \| None` | Session ID from query params (for session-scoped filtering) |
| `is_ready_to_send` | `bool` | True when websocket connected AND client subscribed |

#### Helper Methods

**Response Helpers**:

```python
# Create standardized error response
def create_error_response(
    self,
    code: str,
    message: str,
    correlation_id: str | None = None,
) -> MessageEnvelope

# Create unknown message type error (most common error pattern)
def create_unknown_message_error(
    self,
    message_type: str,
    correlation_id: str | None = None,
) -> MessageEnvelope

# Create standardized success response
def create_success_response(
    self,
    type: str,
    payload: dict[str, Any],
    correlation_id: str | None = None,
) -> MessageEnvelope

# Create standardized subscribed response
def create_subscribed_response(
    self,
    correlation_id: str | None = None,
    message: str = "Successfully subscribed",
    extra_payload: dict[str, Any] | None = None,
) -> MessageEnvelope

# Create standardized unsubscribed response
def create_unsubscribed_response(
    self,
    correlation_id: str | None = None,
    message: str = "Successfully unsubscribed",
    extra_payload: dict[str, Any] | None = None,
) -> MessageEnvelope
```

**Subscription Helpers**:

```python
# Check if ready to send (websocket connected AND subscribed)
@property
def is_ready_to_send(self) -> bool

# Send message only if subscribed (returns True if sent)
async def send_if_subscribed(self, message: dict[str, Any]) -> bool
```

**Logging Helpers**:

```python
# Log standardized connection event
def log_connected(self, extra: dict[str, Any] | None = None) -> None

# Log standardized disconnection event
def log_disconnected(self, extra: dict[str, Any] | None = None) -> None
```

#### BroadcasterMixin

For handlers that integrate with a broadcaster pattern, use `BroadcasterMixin`:

```python
from mcp_server_langgraph.websocket import BroadcasterMixin, WebSocketBase

class AlertHandler(WebSocketBase, BroadcasterMixin):
    def __init__(self, config: WebSocketConfig, broadcaster: Broadcaster):
        super().__init__(config)
        self._broadcaster = broadcaster

    async def handle_message(self, message: MessageEnvelope) -> MessageEnvelope | None:
        if message.type == "subscribe":
            # Simple subscribe (no extra args)
            await self.subscribe()

            # Or with custom arguments for user filtering
            await self.subscribe(user_id=self.user_id)

            # Or with multiple arguments for context filtering
            await self.subscribe(user_id=self.user_id, context_entity_id="ctx-123")

            # Or with filter objects
            await self.subscribe(filter_=my_filter)

            return self.create_subscribed_response(correlation_id=message.id)
        elif message.type == "unsubscribe":
            await self.unsubscribe()  # Calls broadcaster.unsubscribe if subscribed
            return self.create_unsubscribed_response(correlation_id=message.id)
        ...
```

The mixin provides:
- `subscribed` property: Get/set subscription state
- `subscribe(**kwargs)` method: Call broadcaster.subscribe with optional kwargs and set subscribed=True
- `unsubscribe()` method: Call broadcaster.unsubscribe if subscribed, set subscribed=False

**Supported kwargs for subscribe()**:
- `user_id`: Filter broadcasts by user ID
- `context_entity_id`: Filter by context/session/workflow ID
- `filter_`: Custom filter object for trace/audit filtering
- Any other kwargs your broadcaster accepts

**Handlers using BroadcasterMixin**:

| Handler | File | Kwargs Used |
|---------|------|-------------|
| `AlertHandler` | `handlers/alert.py` | `user_id` |
| `TraceHandler` | `handlers/trace.py` | `filter_` |
| `DevToolsHandler` | `handlers/devtools.py` | `user_id`, `context_entity_id` |
| `MCPAggregatedHandler` | `handlers/mcp_aggregated.py` | `user_id` |
| `OrchestratorStatusHandler` | `handlers/orchestrator_status.py` | `user_id` |

#### Best Practices

**DO use WebSocketBase helpers**:

```python
# Good: Use user_id property
logger.info(f"User {self.user_id} subscribed")

# Good: Use create_unknown_message_error
return self.create_unknown_message_error(message.type, message.id)

# Good: Use send_if_subscribed for push notifications
await self.send_if_subscribed({
    "type": "notification",
    "payload": {"event": "new_data"}
})

# Good: Use logging helpers
self.log_connected(extra={"session_id": self.session_id})
```

**DON'T use deprecated patterns**:

```python
# Bad: Store _user_id manually (DEPRECATED)
self._user_id = user.id  # Use self.user_id property instead

# Bad: Verbose subscription guard (DEPRECATED when followed by send_json)
if self._websocket and self._subscribed:
    await self._websocket.send_json({...})
# Use: await self.send_if_subscribed({...})

# Bad: Verbose error envelope (DEPRECATED)
return MessageEnvelope(
    type="error",
    payload={"code": "unknown_message_type", ...},
    id=message.id,
)
# Use: return self.create_unknown_message_error(message.type, message.id)

# Bad: Verbose subscription response (DEPRECATED)
return MessageEnvelope(
    type="subscribed",
    payload={"message": "Successfully subscribed"},
    id=message.id,
)
# Use: return self.create_subscribed_response(correlation_id=message.id)

# Bad: Verbose unsubscription response (DEPRECATED)
return MessageEnvelope(
    type="unsubscribed",
    payload={"message": "Successfully unsubscribed"},
    id=message.id,
)
# Use: return self.create_unsubscribed_response(correlation_id=message.id)
```

A pre-commit hook (`check-websocket-deprecated-patterns`) enforces these patterns.

---

## Migration Status

All major WebSocket endpoints have been migrated to the new `WebSocketBase` infrastructure:

### Completed Migrations

- [x] **MCP WebSocket** (`/api/v1/ws/mcp`) - JSON-RPC 2.0 protocol
- [x] **MCP Task WebSocket** (`/api/v1/ws/mcp/tasks`) - Task status updates
- [x] **Workflow Execution** (`/api/v1/ws/workflows/{workflow_id}`) - Real-time workflow updates
- [x] **Connection Health** (`/api/v1/ws/connections/health`) - Health monitoring
- [x] **Notification WebSocket** (`/api/v1/ws/notifications`) - User notifications
- [x] **Alert WebSocket** (`/api/v1/ws/alerts`) - Infrastructure alerts
- [x] **Audit WebSocket** (`/api/v1/ws/audit`) - Compliance audit events
- [x] **Agent Request** (`/api/v1/ws/agents/requests`) - HITL approvals

### New Endpoints (Post-Standardization)

- [x] **Connections Realtime** (`/api/v1/ws/connections/realtime`) - Replaces polling
- [x] **HEART Metrics** (`/api/v1/ws/metrics/heart`) - Replaces `useHeartDashboard.ts`
- [x] **Cost Tracking** (`/api/v1/ws/usage/cost`) - Real-time LLM cost monitoring
- [x] **AI Suggestions** (`/api/v1/ws/ai/suggestions`) - Studio typing assistance

### Legacy Endpoints (Deprecated)

The following old URLs are deprecated but still functional for backward compatibility:

| Old URL | New URL | Status |
|---------|---------|--------|
| `/api/v1/mcp/ws` | `/api/v1/ws/mcp` | Deprecated |
| `/api/v1/mcp/tasks/ws` | `/api/v1/ws/mcp/tasks` | Deprecated |
| `/api/v1/workflows/ws` | `/api/v1/ws/workflows/{id}` | Deprecated |
| `/api/v1/connections/health/ws` | `/api/v1/ws/connections/health` | Deprecated |
| `/api/v1/audit/stream` | `/api/v1/ws/audit` | Deprecated |
| `/ws/notifications` | `/api/v1/ws/notifications` | Deprecated |
| `/ws/agents/requests` | `/api/v1/ws/agents/requests` | Deprecated |

**Migration Timeline**:
- **Phase 1** (Complete): All endpoints migrated to `WebSocketBase`
- **Phase 2** (Current): New consolidated URLs active, old URLs deprecated
- **Phase 3** (Q1 2026): Remove old URLs, enforce new URLs only

---

## Observability

### Tracing

All WebSocket connections and messages are automatically traced via OpenTelemetry:

**Span Hierarchy**:
```
websocket.{endpoint_name}
└── websocket.message.{message_type}
```

**Attributes**:
- `ws.endpoint`: Endpoint name
- `ws.user_id`: Authenticated user ID
- `ws.message.type`: Message type
- `ws.message.id`: Message correlation ID
- `ws.message.timeout`: `true` if message timed out

**Example Trace**:
```
websocket.mcp (duration: 120s)
├── websocket.message.initialize (duration: 150ms)
├── websocket.message.tools/list (duration: 80ms)
├── websocket.message.resources/read (duration: 200ms)
└── websocket.message.ping (duration: 5ms)
```

### Metrics

See [Standard Infrastructure Features - OpenTelemetry Metrics Integration](#3-opentelemetry-metrics-integration) for full list of metrics.

**Grafana Dashboard**: `WebSocket Infrastructure` (auto-generated from metrics)

### Logging

All WebSocket events are logged with structured context:

```python
logger.debug("WebSocket auth success", extra={
    "endpoint": "mcp",
    "user_id": "user_123",
})

logger.warning("Rate limit exceeded", extra={
    "endpoint": "notifications",
    "user_id": "user_456",
    "limit": 600,
})
```

**Log Levels**:
- `DEBUG`: Connection lifecycle, auth success, heartbeat
- `INFO`: Lifecycle manager startup/shutdown
- `WARNING`: Auth failures, rate limit exceeded, message timeout
- `ERROR`: Unexpected errors during message processing

---

## Security Considerations

### Authentication

- **JWT Validation**: All tokens validated via Keycloak integration
- **Initial Auth Failure**: Missing or invalid tokens rejected with `4001` close code
- **Token Expiry During Connection**: Periodic validation detects expired tokens, closing with `4010` (ADR-0074)
- **Client Recovery**: Clients receiving `4010` should refresh token and reconnect
- **Anonymous Access**: Explicitly opt-in via `require_auth=False`

### Protocol Version Validation

- **Semver-Based**: Protocol version uses semantic versioning (e.g., `1.0.0`)
- **Version Query Param**: Clients must include `?v=1.0.0` in WebSocket URL
- **Major Version Match**: Major versions must match exactly (breaking changes)
- **Minor Version Compatibility**: Server can support higher minor versions (backwards compatible)
- **Version Mismatch**: Incompatible versions rejected with `4009` close code (NOT recoverable)
- **Client Recovery**: Clients receiving `4009` should show user-friendly message suggesting page refresh
- **Configurable**: Enable/disable via `WebSocketConfig.validate_protocol_version`

### Authorization

- **OpenFGA Integration**: Fine-grained ReBAC checks on connection
- **Fail-Closed**: Authorization failures close connection with `4003` (configurable via `authz_fail_closed`)
- **Resource-Based**: Each endpoint maps to OpenFGA resource type (e.g., `workflow:hitl`, `dashboard:alerts`)

### Rate Limiting

- **Per-User**: Rate limits enforced per `user_id` to prevent abuse
- **Distributed**: Redis-backed rate limiter for multi-instance deployments
- **Graceful Degradation**: Rate limiter failures fail-open (allow messages) to prevent service disruption

### Connection Limits

- **Max Connections Per User**: Default 5 concurrent connections (configurable)
- **Idle Timeout**: 30 minutes default (closes inactive connections)
- **Heartbeat Timeout**: 90 seconds (detects dead connections)

### Message Size Limits

- **Default**: 1MB per message
- **Configurable**: Adjust via `WebSocketConfig.max_message_size`
- **Enforcement**: Messages exceeding limit rejected with `4013` close code

---

## Performance Optimization

### Connection Pooling

- **Lifecycle Manager**: Centralized `WebSocketLifecycleManager` manages all connections
- **Background Cleanup**: Periodic cleanup task removes idle connections
- **Metrics Cleanup**: Separate task cleans up stale metrics

### Message Timeout

- **Default**: 30 seconds per message
- **Enforcement**: `asyncio.wait_for()` enforces timeout on `handle_message()`
- **Graceful Handling**: Timeout errors sent to client, connection remains open

### Heartbeat Optimization

- **Server-Initiated**: Server sends heartbeat, reducing client overhead
- **Configurable Interval**: Adjust interval based on connection stability needs
- **Early Detection**: Detects dead connections before idle timeout

---

## WebSocket Permissions and Sub-Persona Architecture

### Overview

WebSocket permissions are determined via OpenFGA at login time and stored in the user's session. The `/api/v1/me` endpoint returns 17 permission fields that control which WebSocket endpoints a user can access.

### Permission Fields (17 Total)

| Permission | OpenFGA Type:Object | Relation | Description |
|------------|---------------------|----------|-------------|
| `alerts` | `dashboard:alerts` | `admin` | Infrastructure alert streaming (admin only) |
| `notifications` | `chat:notifications` | `viewer` | User notification streaming |
| `devtools` | `dashboard:devtools` | `viewer` | DevTools panel access |
| `audit` | `logs:audit` | `viewer` | Audit event streaming |
| `mcp_tasks` | `mcp:websocket` | `user` | MCP task status updates |
| `mcp_aggregated` | `mcp:aggregated-capabilities` | `viewer` | MCP aggregated capabilities |
| `connections_health` | `mcp_connection:health` | `viewer` | Connection health monitoring |
| `connections_realtime` | `mcp_connection:realtime` | `viewer` | Real-time connection status |
| `heart_metrics` | `observability:heart` | `viewer` | HEART metrics streaming |
| `traces` | `traces:stream` | `viewer` | Trace data streaming |
| `cost_tracking` | `cost:usage` | `viewer` | Cost tracking updates |
| `budget_alerts` | `cost:budget` | `viewer` | Budget alert notifications |
| `agent_requests` | `workflow:hitl` | `editor` | HITL approval requests |
| `ai_suggestions` | `ai:suggestions` | `user` | AI typing suggestions |
| `orchestrator_status` | `ai:orchestrator` | `viewer` | AI orchestrator status |
| `llm_streaming` | `chat:llm-streaming` | `viewer` | LLM response streaming |
| `session_metrics` | `chat:session-metrics` | `viewer` | Session metrics streaming |

### Implementation

**Backend** (`src/mcp_server_langgraph/api/v1/user.py`):

```python
WEBSOCKET_PERMISSIONS_MAP: dict[str, tuple[str, str, str]] = {
    "alerts": ("dashboard", "alerts", "admin"),
    "notifications": ("chat", "notifications", "viewer"),
    # ... all 17 permissions
}

async def get_websocket_permissions(user_id: str, authz: OpenFGAClientDep) -> dict[str, bool]:
    """Query OpenFGA for each permission, return dict of permission -> bool."""
```

**Frontend** (`src/store/slices/authSlice.ts`):

```typescript
// initializeAuth thunk maps /api/v1/me response to Redux state
const websocketPermissions: WebSocketPermissions = {
  alerts: data.websocket_permissions.alerts ?? false,
  devtools: data.websocket_permissions.devtools ?? false,
  // ... all 17 permissions
};
```

### Sub-Persona Architecture

Sub-personas allow fine-grained permission control for specialized user roles beyond the standard admin/developer/user hierarchy.

#### Test Users

| Username | Sub-Persona | Role | Permissions |
|----------|-------------|------|-------------|
| `admin` | - | Admin | All 17 permissions |
| `alice` | - | Developer | 16/17 (no alerts) |
| `bob` | - | User | 15/17 (no alerts, no agent_requests) |
| `auditor-jane` | `auditor` | User | 10/17 (audit focus, no HITL/developer features) |
| `compliance-charlie` | `compliance-officer` | User | 10/17 (compliance focus, no developer features) |
| `devops-dave` | `devops` | Developer | 17/17 (full access including alerts) |

#### Sub-Persona Permission Design

**Auditor** (auditor-jane):
- ✅ `audit`, `traces`, `cost_tracking`, `notifications`
- ❌ `agent_requests` (no HITL approval)
- ❌ `devtools`, `ai_suggestions` (no developer features)
- ❌ `alerts` (no infrastructure access)

**Compliance Officer** (compliance-charlie):
- ✅ `audit`, `notifications`, `cost_tracking`, `budget_alerts`
- ❌ `agent_requests` (no HITL approval)
- ❌ `devtools`, `ai_suggestions`, `mcp_tasks` (no developer features)
- ❌ `alerts` (no infrastructure access)

**DevOps** (devops-dave):
- ✅ All 17 permissions including `alerts`
- Has `developer` role + `devops` sub-persona
- Production monitoring requires full observability access

#### Configuration

**Keycloak** (`tests/e2e/default-realm.json`):
```json
{
  "username": "auditor-jane",
  "attributes": {
    "sub_persona": ["auditor"]
  }
}
```

**OpenFGA** (`config/openfga/sample-tuples.json`):
```json
{
  "user": "user:auditor-jane",
  "relation": "viewer",
  "object": "logs:audit"
}
```

### Fail-Closed Security

When OpenFGA is unavailable or returns an error, all permissions default to `false`:

```python
# user.py - fail-closed behavior
except Exception:
    logger.warning("OpenFGA unavailable, returning fail-closed permissions")
    return {key: False for key in WEBSOCKET_PERMISSIONS_MAP}
```

Frontend hooks also fail-closed:
```typescript
// useAIOrchestratorStatus.ts
const hasPermission = wsPermissions?.orchestrator_status ?? false;
const effectiveEnabled = enabled && isAuthenticated && hasPermission;
```

### Pre-commit Validation

The `validate-websocket-permissions-schema` pre-commit hook ensures alignment between:
1. `WEBSOCKET_PERMISSIONS_MAP` in `user.py`
2. OpenFGA model types and relations in `config/openfga/model.json`

```bash
uv run --frozen python scripts/validators/validate_websocket_permissions.py
```

---

## References

- **ADR-0068**: WebSocket Standardization (primary specification)
- **Source Code**: `src/mcp_server_langgraph/websocket/` (base, types, handlers, metrics)
- **Router**: `src/mcp_server_langgraph/api/v1/ws_router.py` (consolidated router)
- **Tests**: `tests/unit/ws_handlers/` (handler unit tests)
- **Feature Flags**: `src/mcp_server_langgraph/core/feature_flags.py` (configuration)

---

**Questions or Issues?**
Contact the Infrastructure Team or file an issue in the project repository.
