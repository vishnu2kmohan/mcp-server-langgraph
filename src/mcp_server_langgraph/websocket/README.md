# WebSocket Infrastructure

Standardized WebSocket infrastructure for all real-time endpoints.

## Overview

This module provides a unified WebSocket infrastructure that ensures consistent behavior across all endpoints:

- **Authentication** - JWT validation via Keycloak
- **Authorization** - Fine-grained access control via OpenFGA (ReBAC)
- **Rate Limiting** - Per-user rate limiting (Redis-backed or in-memory)
- **Metrics** - OpenTelemetry-based observability
- **Resilience** - Heartbeat, timeouts, and graceful degradation

## Architecture

```
┌─────────────────────────────────────────────────────────────┐
│                     FastAPI Router                          │
│                  /api/v1/ws/*                               │
└─────────────────────┬───────────────────────────────────────┘
                      │
┌─────────────────────▼───────────────────────────────────────┐
│                   WebSocketBase                             │
│  ┌──────────────┬──────────────┬──────────────┬──────────┐  │
│  │    Auth      │    AuthZ     │ Rate Limiter │ Metrics  │  │
│  │ (Keycloak)   │  (OpenFGA)   │   (Redis)    │  (OTel)  │  │
│  └──────────────┴──────────────┴──────────────┴──────────┘  │
│  ┌──────────────┬──────────────┬──────────────┬──────────┐  │
│  │  Heartbeat   │   Timeouts   │   Tracing    │  Logging │  │
│  └──────────────┴──────────────┴──────────────┴──────────┘  │
└─────────────────────┬───────────────────────────────────────┘
                      │
┌─────────────────────▼───────────────────────────────────────┐
│               Specialized Handlers                          │
│  ┌─────────────┬─────────────┬─────────────┬─────────────┐  │
│  │  MCP        │ Notification│   Alert     │   Audit    │  │
│  ├─────────────┼─────────────┼─────────────┼─────────────┤  │
│  │  Workflow   │  Connection │   HEART     │   Cost     │  │
│  └─────────────┴─────────────┴─────────────┴─────────────┘  │
└─────────────────────────────────────────────────────────────┘
```

## Module Structure

```
websocket/
├── __init__.py          # Public API exports
├── base.py              # WebSocketBase abstract class
├── authz.py             # OpenFGA authorization middleware
├── middleware.py        # Authentication middleware
├── heartbeat.py         # Server-initiated heartbeat manager
├── metrics.py           # OpenTelemetry metrics
├── rate_limiter.py      # Rate limiting (Redis + in-memory)
├── registry.py          # Broadcaster registry
├── resilience.py        # Timeout and circuit breaker
├── types.py             # Type definitions
├── exceptions.py        # WebSocket-specific exceptions
├── handlers/            # Specialized endpoint handlers
│   ├── mcp.py
│   ├── notification.py
│   ├── alert.py
│   └── ...
└── services/            # Service adapters for handlers
```

## Quick Start

### Creating a WebSocket Endpoint

```python
from fastapi import WebSocket
from mcp_server_langgraph.websocket import WebSocketBase, WebSocketConfig
from mcp_server_langgraph.websocket.types import MessageEnvelope

class MyHandler(WebSocketBase):
    """Custom WebSocket handler."""

    async def handle_message(self, message: MessageEnvelope) -> MessageEnvelope | None:
        if message.type == "my_action":
            result = await self._process_action(message.payload)
            return MessageEnvelope(type="my_response", payload=result)
        return None

    async def on_connect(self, user):
        # Called after auth success
        pass

    async def on_disconnect(self):
        # Called on connection close
        pass

# In your router:
@router.websocket("/my-endpoint")
async def my_websocket(websocket: WebSocket):
    handler = MyHandler(
        config=WebSocketConfig(
            endpoint_name="my-endpoint",
            require_auth=True,
            authz_resource_type="myresource",
            authz_resource_id="*",
            authz_required_relation="viewer",
            rate_limit_per_minute=100,
        )
    )
    await handler.run(websocket)
```

## Configuration

### WebSocketConfig

| Parameter | Type | Default | Description |
|-----------|------|---------|-------------|
| `endpoint_name` | str | required | Unique identifier for metrics/logging |
| `require_auth` | bool | True | Require JWT authentication |
| `authz_resource_type` | str | None | OpenFGA resource type for authorization |
| `authz_resource_id` | str | None | OpenFGA resource ID |
| `authz_required_relation` | str | "viewer" | Required OpenFGA relation |
| `authz_fail_closed` | bool | True | Deny access on authorization errors |
| `rate_limit_per_minute` | int | 600 | Max messages per minute per user |
| `message_timeout` | int | 30 | Handler timeout in seconds |
| `heartbeat_interval` | int | 0 | Server heartbeat interval (0=disabled) |
| `heartbeat_timeout` | int | 60 | Heartbeat timeout before disconnect |
| `idle_timeout` | int | 0 | Connection idle timeout (0=disabled) |

## Rate Limiting

### Overview

Rate limiting protects against DoS attacks and ensures fair resource allocation.

### Feature Flag Control

```python
# .env or environment
FF_ENABLE_DISTRIBUTED_RATE_LIMITING=true  # Use Redis
FF_ENABLE_DISTRIBUTED_RATE_LIMITING=false # Use in-memory
```

### Redis-Backed Rate Limiting

When `FF_ENABLE_DISTRIBUTED_RATE_LIMITING=true`:

- Uses Redis INCR with TTL for atomic counters
- Shared limits across all server instances
- Fail-open on Redis errors (graceful degradation)
- Per-user isolation

```
Redis Key: ratelimit:ws:user:{user_id}
TTL: 60 seconds (sliding window)
```

### In-Memory Rate Limiting

When `FF_ENABLE_DISTRIBUTED_RATE_LIMITING=false`:

- Per-instance rate limiting
- No external dependencies
- Suitable for single-instance deployments

### Rate Limit Response

When limit exceeded:

```json
{
  "type": "error",
  "payload": {
    "code": "rate_limit_exceeded",
    "message": "Rate limit exceeded"
  }
}
```

## Authentication

### JWT Token Extraction

Tokens extracted in order:

1. Query parameter: `?token=<jwt>`
2. Authorization header: `Authorization: Bearer <jwt>`

### Anonymous Connections

Set `require_auth=False` in config for endpoints that allow anonymous access:

```python
config = WebSocketConfig(
    endpoint_name="public-endpoint",
    require_auth=False,
)
```

## Authorization (OpenFGA)

### ReBAC Model

Authorization uses Relationship-Based Access Control (ReBAC) via OpenFGA:

```python
# Check if user can access dashboard:alerts with admin relation
authz = WebSocketAuthorizationMiddleware(
    resource_type="dashboard",
    resource_id="alerts",
    required_relation="admin",
    fail_closed=True,
)
```

### Fail-Closed Behavior

With `authz_fail_closed=True` (default):

- Authorization errors → deny access
- OpenFGA unavailable → deny access
- Invalid token → deny access

### Authorization Mapping

| Endpoint | Resource | Relation |
|----------|----------|----------|
| `/ws/notifications` | chat:notifications | viewer |
| `/ws/alerts` | dashboard:alerts | admin |
| `/ws/audit` | logs:audit | viewer |
| `/ws/agents/requests` | workflow:hitl | editor |
| `/ws/mcp` | - | (no auth required) |
| `/ws/mcp/auth` | mcp:websocket | user |

## Message Format

### Standard Envelope

All messages use the standard envelope format:

```json
{
  "type": "message_type",
  "id": "correlation-id",
  "payload": {},
  "timestamp": "2024-01-01T00:00:00Z"
}
```

### Reserved Message Types

| Type | Direction | Description |
|------|-----------|-------------|
| `ping` | client→server | Client heartbeat |
| `pong` | server→client | Server heartbeat response |
| `heartbeat` | server→client | Server-initiated heartbeat |
| `error` | server→client | Error response |

## Metrics

### OpenTelemetry Metrics

```
# Counters
ws_connections_total{endpoint, status}
ws_messages_total{endpoint, direction, type}
ws_errors_total{endpoint, error_type}
ws_rate_limit_exceeded_total{endpoint}

# Gauges
ws_active_connections{endpoint}

# Histograms
ws_message_latency_seconds{endpoint, type}
```

### Accessing Metrics

```python
from mcp_server_langgraph.websocket.metrics import get_websocket_metrics

metrics = get_websocket_metrics()
metrics.record_connection()
metrics.record_message("my_action", direction="in")
metrics.record_message_latency("my_action", latency_seconds=0.05)
```

## Error Handling

### WebSocket Close Codes

| Code | Reason |
|------|--------|
| 4001 | Authentication required |
| 4003 | Authorization denied |
| 4008 | Rate limit exceeded |
| 4029 | Too many requests |

### Exception Classes

```python
from mcp_server_langgraph.websocket.exceptions import (
    AuthenticationError,  # 4001
    AuthorizationError,   # 4003
    RateLimitError,       # 4029
    WebSocketError,       # Base class
)
```

## Endpoints

### Available Endpoints

| URL | Handler | Auth | Description |
|-----|---------|------|-------------|
| `/api/v1/ws/mcp` | MCPWebSocketHandler | Optional | MCP protocol |
| `/api/v1/ws/mcp/auth` | MCPWebSocketHandler | Required | Authenticated MCP |
| `/api/v1/ws/notifications` | NotificationHandler | Required | User notifications |
| `/api/v1/ws/alerts` | AlertHandler | Admin | Infrastructure alerts |
| `/api/v1/ws/audit` | AuditHandler | Required | Audit events |
| `/api/v1/ws/agents/requests` | AgentRequestHandler | Required | HITL requests |
| `/api/v1/ws/connections/realtime` | ConnectionsRealtimeHandler | Required | Connection status |
| `/api/v1/ws/connections/health` | ConnectionHealthHandler | Required | Health monitoring |
| `/api/v1/ws/metrics/heart` | HeartMetricsHandler | Required | HEART metrics |
| `/api/v1/ws/usage/cost` | CostTrackingHandler | Required | Cost tracking |
| `/api/v1/ws/workflows/{id}` | WorkflowExecutionHandler | Required | Workflow execution |

### Legacy Endpoints (Deprecated)

The following endpoints are deprecated and will be removed in v4.0:

- `/ws/notifications` → Use `/api/v1/ws/notifications`
- `/ws/agents/requests` → Use `/api/v1/ws/agents/requests`
- `/api/v1/mcp/ws` → Use `/api/v1/ws/mcp`
- `/api/v1/audit/stream` → Use `/api/v1/ws/audit`

## Testing

### Unit Tests

```bash
# Run all WebSocket tests
uv run pytest tests/unit/websocket/ -v

# Run Redis rate limiter tests
uv run pytest tests/unit/websocket/test_redis_rate_limiter.py -v
```

### Integration Tests

```bash
# Run integration tests (requires Redis)
uv run pytest tests/integration/websocket/ -v -m redis

# Run with test infrastructure
make test-infra-up
uv run pytest tests/integration/websocket/ -v
```

### Test Fixtures

```python
@pytest.fixture
async def websocket_handler():
    """Create a test WebSocket handler."""
    handler = MyHandler(
        config=WebSocketConfig(
            endpoint_name="test",
            require_auth=False,
        )
    )
    yield handler
```

## Migration Guide

### From Legacy Endpoints

1. Update client URLs to new `/api/v1/ws/*` paths
2. Update message format to standard envelope
3. Handle new error codes (4001, 4003, 4029)
4. Implement heartbeat response for server-initiated heartbeats

### Client-Side Changes

```typescript
// Before
const ws = new WebSocket('/ws/notifications');

// After
const ws = new WebSocket('/api/v1/ws/notifications?token=' + jwt);

// Handle new message format
ws.onmessage = (event) => {
  const envelope = JSON.parse(event.data);
  switch (envelope.type) {
    case 'notification':
      handleNotification(envelope.payload);
      break;
    case 'heartbeat':
      ws.send(JSON.stringify({ type: 'pong', id: envelope.id }));
      break;
    case 'error':
      handleError(envelope.payload);
      break;
  }
};
```

## Troubleshooting

### Common Issues

**Rate Limit Errors**

```
Error: Rate limit exceeded
```

Solution: Check `FF_ENABLE_DISTRIBUTED_RATE_LIMITING` and Redis connectivity.

**Authorization Denied**

```
Error: Authorization denied (4003)
```

Solution: Verify OpenFGA tuples and user relationships.

**Connection Timeout**

```
Error: WebSocket connection timeout
```

Solution: Check `heartbeat_interval` and `idle_timeout` settings.

### Debug Logging

```python
import logging
logging.getLogger("mcp_server_langgraph.websocket").setLevel(logging.DEBUG)
```

## References

- [OpenFGA Documentation](https://openfga.dev/docs)
- [FastAPI WebSockets](https://fastapi.tiangolo.com/advanced/websockets/)
- [OpenTelemetry Python](https://opentelemetry.io/docs/languages/python/)
- [MCP Protocol Specification](https://modelcontextprotocol.io/)
