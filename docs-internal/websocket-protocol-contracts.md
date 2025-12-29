# WebSocket Protocol Contracts

This document defines the WebSocket message protocols used between the frontend and backend.
All WebSocket endpoints use JSON message envelopes with a standard format.

## Message Envelope Format

All WebSocket messages follow this envelope structure:

```typescript
interface MessageEnvelope {
  type: string;          // Message type identifier
  id?: string;           // Optional message ID for correlation
  payload?: object;      // Message-specific data
}
```

## Endpoints

### 1. DevTools WebSocket (`/api/v1/ws/devtools`)

Real-time console and network data for DevTools panel.

**Message Types (Server → Client):**

#### `console` - Console Log Entry
```json
{
  "type": "console",
  "payload": {
    "id": "string (optional)",
    "level": "info" | "warning" | "error" | "debug",
    "source": "system" | "api" | "mcp" | "notification" | "execution" | "websocket",
    "message": "string",
    "timestamp": 1703000000000,
    "data": { ... },           // Optional structured data
    "stackTrace": "string"     // Optional error stack trace
  }
}
```

#### `network` - Network Request Entry
```json
{
  "type": "network",
  "payload": {
    "id": "string (optional)",
    "method": "GET" | "POST" | "PUT" | "DELETE" | "PATCH" | "OPTIONS",
    "url": "string",
    "status": "pending" | "completed" | "error" | "cancelled",
    "statusCode": 200,
    "startTime": 1703000000000,
    "endTime": 1703000000150,
    "duration": 150,
    "requestSize": 1024,
    "responseSize": 2048,
    "source": "string (optional, e.g., 'mcp-server-1')"
  }
}
```

#### `network_update` - Update Existing Network Entry
```json
{
  "type": "network_update",
  "payload": {
    "id": "string (required)",
    "status": "completed" | "error",
    "statusCode": 200,
    "duration": 150,
    "responseSize": 2048,
    "endTime": 1703000000150
  }
}
```

---

### 2. Traces WebSocket (`/api/v1/ws/traces`)

Real-time OpenTelemetry trace spans.

**Message Types (Server → Client):**

#### `trace_span` - Trace Span Data
```json
{
  "type": "trace_span",
  "payload": {
    "span_id": "string",
    "trace_id": "string",
    "parent_span_id": "string | null",
    "name": "string",
    "start_time": 1703000000000,
    "end_time": 1703000000150,
    "duration_ms": 150,
    "status": "ok" | "error" | "unset",
    "service_name": "string",
    "attributes": { ... }
  }
}
```

**Message Types (Client → Server):**

#### `subscribe` - Subscribe to Trace Updates
```json
{
  "type": "subscribe",
  "id": "uuid",
  "payload": {
    "service_filter": "string (optional)",
    "trace_id": "string (optional)"
  }
}
```

---

### 3. Budget Alerts WebSocket (`/api/v1/ws/budget/alerts`)

Real-time budget monitoring and alerts.

**Message Types (Server → Client):**

#### `budget_alert` - Budget Alert Notification
```json
{
  "type": "budget_alert",
  "payload": {
    "entity_type": "organization" | "project" | "team" | "user",
    "entity_id": "string",
    "status": "ok" | "warning" | "critical" | "exceeded",
    "percent_used": 85.5,
    "current_spend": "850.00",
    "remaining": "150.00",
    "monthly_limit_usd": "1000.00",
    "message": "Budget at 85%"
  }
}
```

#### `subscribed` - Subscription Confirmation
```json
{
  "type": "subscribed",
  "payload": {
    "entity_ids": ["org-123", "org-456"],
    "subscribe_all": false
  }
}
```

#### `unsubscribed` - Unsubscription Confirmation
```json
{
  "type": "unsubscribed",
  "payload": {}
}
```

**Message Types (Client → Server):**

#### `subscribe_entities` - Subscribe to Specific Entities
```json
{
  "type": "subscribe_entities",
  "id": "uuid",
  "payload": {
    "entity_ids": ["org-123", "project-456"]
  }
}
```

#### `subscribe_all` - Subscribe to All Alerts (Admin)
```json
{
  "type": "subscribe_all",
  "id": "uuid",
  "payload": {}
}
```

#### `unsubscribe` - Unsubscribe from All Alerts
```json
{
  "type": "unsubscribe",
  "id": "uuid",
  "payload": {}
}
```

---

### 4. AI Suggestions WebSocket (`/api/v1/ws/ai/suggestions`)

Real-time AI typing suggestions.

**Message Types (Server → Client):**

#### `suggestion_response` - AI Suggestion
```json
{
  "type": "suggestion_response",
  "payload": {
    "suggestion_id": "sug-123",
    "text": "I can help you with that!",
    "confidence": 0.85,
    "reasoning": "Based on greeting pattern"
  }
}
```

#### `error` - Error Response
```json
{
  "type": "error",
  "payload": {
    "code": "rate_limited" | "internal_error" | "invalid_request",
    "message": "Too many requests",
    "retryable": true
  }
}
```

**Message Types (Client → Server):**

#### `suggestion_request` - Request AI Suggestion
```json
{
  "type": "suggestion_request",
  "id": "uuid",
  "payload": {
    "session_id": "session-123",
    "input_text": "Hello, I need help with",
    "cursor_position": 25,
    "context_window": 500
  }
}
```

#### `suggestion_accept` - Accept Suggestion (Feedback)
```json
{
  "type": "suggestion_accept",
  "id": "uuid",
  "payload": {
    "suggestion_id": "sug-123"
  }
}
```

#### `suggestion_reject` - Reject Suggestion (Feedback)
```json
{
  "type": "suggestion_reject",
  "id": "uuid",
  "payload": {
    "suggestion_id": "sug-123",
    "reason": "Not helpful"
  }
}
```

#### `context_update` - Update Session Context
```json
{
  "type": "context_update",
  "id": "uuid",
  "payload": {
    "session_id": "session-123",
    "context": "User is working on a Python project"
  }
}
```

---

### 5. MCP Aggregated Updates WebSocket (`/api/v1/ws/mcp`)

Aggregated updates from all connected MCP servers.

**Message Types (Server → Client):**

#### `server_status` - MCP Server Status Change
```json
{
  "type": "server_status",
  "payload": {
    "server_id": "mcp-server-1",
    "status": "connected" | "disconnected" | "error",
    "name": "GitHub MCP",
    "timestamp": 1703000000000
  }
}
```

#### `tool_call` - MCP Tool Invocation
```json
{
  "type": "tool_call",
  "payload": {
    "server_id": "mcp-server-1",
    "tool_name": "search_code",
    "call_id": "call-123",
    "status": "started" | "completed" | "error",
    "input": { ... },
    "output": { ... },
    "duration_ms": 150,
    "timestamp": 1703000000000
  }
}
```

---

## Authentication

All WebSocket connections require authentication via:

1. **Query Parameter**: `?token=<jwt_token>`
2. **DPoP Token Binding** (when enabled)

### Token Expiration Handling

When a token expires, the server sends:

```json
{
  "type": "error",
  "payload": {
    "code": "token_expired",
    "message": "Authentication token has expired",
    "retryable": false
  }
}
```

The client should:
1. Close the WebSocket connection
2. Refresh the authentication token
3. Reconnect with the new token

---

## Connection Lifecycle

### Connection Establishment

1. Client opens WebSocket with auth token
2. Server validates token
3. On success: Connection established
4. On failure: Connection closed with error

### Reconnection Strategy

All frontend hooks use exponential backoff:

```typescript
{
  initialDelay: 1000,      // 1 second
  maxDelay: 30000,         // 30 seconds
  factor: 2,               // Double each attempt
  maxAttempts: 10          // Give up after 10 attempts
}
```

### Heartbeat/Ping

WebSocket connections use standard WebSocket ping/pong frames for keepalive.
No application-level heartbeat is required.

---

## Error Handling

### Standard Error Format

All endpoints use this error format:

```json
{
  "type": "error",
  "payload": {
    "code": "string",
    "message": "Human-readable message",
    "retryable": true | false,
    "details": { ... }  // Optional additional context
  }
}
```

### Common Error Codes

| Code | Description | Retryable |
|------|-------------|-----------|
| `token_expired` | JWT token has expired | No (refresh needed) |
| `unauthorized` | Invalid or missing auth | No |
| `rate_limited` | Too many requests | Yes (after delay) |
| `internal_error` | Server-side error | Yes |
| `invalid_request` | Malformed request | No |
| `not_found` | Resource not found | No |

---

## Frontend Hooks Reference

| Endpoint | Frontend Hook | File |
|----------|---------------|------|
| `/api/v1/ws/devtools` | `useDevToolsWebSocket` | `hooks/useDevToolsWebSocket.ts` |
| `/api/v1/ws/traces` | `useTraceWebSocket` | `hooks/useTraceWebSocket.ts` |
| `/api/v1/ws/budget/alerts` | `useBudgetAlertsWebSocket` | `hooks/useBudgetAlertsWebSocket.ts` |
| `/api/v1/ws/ai/suggestions` | `useAISuggestionsWebSocket` | `hooks/useAISuggestionsWebSocket.ts` |
| `/api/v1/ws/mcp` | `useMCPAggregatedUpdates` | `hooks/useMCPAggregatedUpdates.ts` |

All hooks are built on top of `useRealtimeSync` which provides:
- Connection management
- Exponential backoff reconnection
- Token expiration handling
- Message serialization/deserialization

---

## Testing

### Contract Tests

WebSocket contracts are validated by:
- `tests/contract/test_websocket_endpoint_parity.py` - Ensures frontend WS_ENDPOINTS match backend routes
- Frontend hooks have integration tests in `*.test.tsx` files

### E2E Tests

End-to-end WebSocket tests:
- `tests/e2e/test_websocket_smoke.py` - Connects to all endpoints

---

## Changelog

- **2025-12-28**: Initial documentation of WebSocket protocol contracts
