# ADR-0074: WebSocket Token Expiration Handling

**Status**: Accepted
**Date**: 2025-12-28
**Authors**: Claude Code Session (mcp-server-langgraph-session-20251208-224026)
**Supersedes**: N/A
**Related**: ADR-0068 (WebSocket Standardization), ADR-0026 (Resilience Patterns)

## Context

### Problem Statement

WebSocket connections authenticated via Keycloak had a critical security gap: **tokens were only validated at connection time**, not during active connections. This meant:

1. Long-lived WebSocket connections could continue operating with expired JWT tokens
2. Token revocation had no effect until the client reconnected
3. Sessions could persist indefinitely after access should have been revoked

### Existing HTTP Token Refresh

HTTP clients already handle token expiration correctly:

- **RTK Query**: `baseQueryWithReauth.ts` handles 401 with auto-refresh, concurrent prevention, and request retry
- **Fetch Wrapper**: `authenticatedFetch.ts` provides the same pattern for streaming/loaders
- **Auth State**: `authSlice.ts` implements 5-minute proactive refresh buffer

WebSocket connections needed similar resilience.

### Design Options Considered

1. **Client-only refresh**: Client proactively refreshes token and reconnects before expiration
   - *Rejected*: No server enforcement; malicious clients could skip refresh

2. **Server-only validation**: Server periodically validates and closes expired connections
   - *Rejected*: Clients would see unexpected disconnections with no recovery path

3. **Hybrid approach**: Server validates + closes with distinct code; client refreshes and reconnects
   - *Chosen*: Provides security enforcement with graceful recovery

## Decision

Implement a **hybrid token expiration handling** approach:

### 1. Backend Periodic Token Validation

- Store the authentication token after initial validation
- Periodically validate token expiration (every 5 minutes by default)
- Close connection with code **4010** (Token Expired) when token expires
- Allow configurable validation interval via `WebSocketConfig.token_validation_interval`

### 2. Frontend Token Refresh Flow

When receiving close code 4010:
1. Attempt to refresh the access token using the refresh token
2. If refresh succeeds, reconnect with the new token
3. If refresh fails, trigger logout and redirect to login

### 3. Close Code 4010

A new close code **4010** was chosen to:
- Distinguish token expiration from initial auth failure (4001)
- Signal to clients that a refresh and reconnect may succeed
- Stay within the application-defined range (4000-4999)

```
WebSocket Close Codes:
├── 4001: Authentication failed (initial auth failure, invalid token)
├── 4010: Token expired (valid token that has now expired - try refresh)
├── 4002: Protocol error
├── 4003: Authorization denied
└── ...
```

## Implementation

### Backend Components

#### `TokenExpiredError` Exception (`websocket/exceptions.py`)

```python
class TokenExpiredError(AuthenticationError):
    """Raised when WebSocket token expires during active connection."""

    def __init__(
        self,
        message: str = "Token expired",
        code: int = 4010,
        reason: str | None = None,
    ) -> None:
        super().__init__(
            message,
            code,
            reason or "Token expired. Please refresh and reconnect."
        )
```

#### Token Validation Functions (`websocket/token_validation.py`)

```python
def is_token_expired(token: str) -> bool:
    """Check if JWT token is expired."""

def is_token_expiring_soon(token: str, buffer_seconds: int = 300) -> bool:
    """Check if token expires within buffer period."""

def get_token_expiration(token: str) -> datetime | None:
    """Extract expiration time from JWT token."""
```

#### Periodic Validation Task (`websocket/base.py`)

```python
async def _validate_token_periodically(self) -> None:
    """Periodically validate token and close if expired."""
    while True:
        await asyncio.sleep(self.config.token_validation_interval)
        if self._auth_token and is_token_expired(self._auth_token):
            await self._close_with_error(
                self._websocket,
                TokenExpiredError()
            )
            break
```

### Frontend Components

#### WebSocket Auth Utility (`utils/websocketAuth.ts`)

```typescript
export const WS_CLOSE_TOKEN_EXPIRED = 4010;

export async function ensureValidTokenForWebSocket(): Promise<boolean> {
  const token = getAuthToken();
  if (!token) return false;

  if (isTokenExpiringSoon(token)) {
    return await refreshTokenForWebSocket();
  }
  return true;
}
```

#### useRealtimeSync Hook Enhancement

```typescript
ws.onclose = async (event) => {
  if (event.code === WS_CLOSE_TOKEN_EXPIRED) {
    const refreshed = await ensureValidTokenForWebSocket();
    if (refreshed) {
      // Reconnect with new token
      setReconnectAttempts(0);
      createConnection();
    } else {
      // Refresh failed - notify and logout
      callbacksRef.current.onTokenExpired?.();
    }
    return;
  }
  // Normal close handling...
};
```

#### All WebSocket Hooks Updated

The following hooks now include `onTokenExpired` callback:
- `useMCPWebSocket`
- `useConnectionHealthWebSocket`
- `useAlertWebSocket`
- `useNotificationWebSocket`

## Configuration

### Default Values

| Setting | Default | Description |
|---------|---------|-------------|
| `token_validation_interval` | 300 seconds (5 min) | How often to check token expiration |
| Token expiring soon buffer | 300 seconds (5 min) | Time before expiry to trigger proactive refresh |

### Disabling Periodic Validation

Set `token_validation_interval=0` to disable periodic validation (not recommended).

## Consequences

### Positive

- **Security**: Expired tokens are now detected and rejected during active connections
- **Graceful Recovery**: Clients can refresh and reconnect without user intervention
- **Consistency**: WebSocket auth now matches HTTP auth resilience patterns
- **Observability**: Clear close code (4010) for monitoring and debugging

### Negative

- **Minor Overhead**: Periodic validation adds minimal CPU cost (one JWT decode per interval)
- **Memory**: Token stored in handler instance for validation (~1KB per connection)

### Neutral

- **Compatibility**: New close code 4010 requires frontend update; old clients will disconnect without recovery

## Testing

### Unit Tests

- `tests/unit/websocket_pkg/test_token_validation.py`: Token validation functions
- `tests/unit/websocket_pkg/test_exceptions.py`: TokenExpiredError exception
- `tests/unit/websocket_pkg/test_base.py`: Periodic validation task

### Integration Tests

- `tests/integration/websocket/test_websocket_token_expiration.py`: End-to-end flow

### Frontend Tests

- `src/utils/websocketAuth.test.ts`: WebSocket auth utility
- `src/hooks/useRealtimeSync.test.ts`: Token expiration handling

## Related Documentation

- **WEBSOCKET_STANDARDIZATION.md**: Updated with 4010 close code
- **ADR-0026**: Resilience patterns referenced for exponential backoff

## Verification Checklist

- [x] TokenExpiredError with code 4010 implemented
- [x] Periodic token validation in WebSocketBase
- [x] Frontend websocketAuth utility
- [x] useRealtimeSync handles 4010
- [x] All WebSocket hooks updated with onTokenExpired
- [x] Observability metrics (WebSocketMetrics.record_token_expired)
- [x] Environment variable config (STREAMING_TOKEN_VALIDATION_INTERVAL)
- [x] Unit tests pass
- [x] Integration tests pass
- [x] Documentation updated
