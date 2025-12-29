# ADR-0076: WebSocket Protocol Versioning Strategy

**Status**: Accepted
**Date**: 2025-12-29
**Authors**: Claude Code Session (mcp-server-langgraph-session-20251208-224026)
**Supersedes**: N/A
**Related**: ADR-0074 (WebSocket Token Expiration), ADR-0068 (WebSocket Standardization), ADR-0026 (Resilience Patterns)

## Context

### Problem Statement

As the Agent Studio frontend and backend evolve independently, there's a risk of protocol drift where:

1. **Breaking changes** in WebSocket message formats cause silent failures
2. **Feature additions** on the server aren't detected by older clients
3. **Incompatible clients** continue to operate with undefined behavior
4. **Debugging** protocol issues across versions becomes difficult

Without version negotiation, clients and servers cannot communicate about compatibility, leading to confusing error states and poor user experience.

### Existing Patterns

REST APIs use HTTP headers (`Accept-Version`, `Content-Type`) for version negotiation. WebSockets lack this built-in mechanism, requiring application-level versioning.

Common approaches include:
- **URL path versioning**: `/ws/v1/endpoint` (inflexible for minor versions)
- **Query parameter versioning**: `?v=1.0.0` (flexible, transparent)
- **Subprotocol negotiation**: `Sec-WebSocket-Protocol` header (complex)
- **Handshake message**: Version negotiation after connection (latency overhead)

### Design Options Considered

1. **URL Path Versioning**: `/api/v2/ws/devtools`
   - *Rejected*: Requires separate endpoints per version; no minor/patch granularity

2. **Subprotocol Negotiation**: Use `Sec-WebSocket-Protocol: mcp.v1.0.0`
   - *Rejected*: Complex implementation; requires header manipulation in React hooks

3. **Post-Connection Handshake**: First message negotiates version
   - *Rejected*: Adds latency; requires timeout handling for version message

4. **Query Parameter Versioning**: `?v=1.0.0` with semver
   - *Chosen*: Simple, transparent, supports full semver, easy to implement

## Decision

Implement **Semantic Version (SemVer) Query Parameter** protocol versioning:

### 1. Version Format

Use standard Semantic Versioning (`MAJOR.MINOR.PATCH`):

```
MAJOR: Breaking changes (incompatible protocol changes)
MINOR: Backwards-compatible feature additions
PATCH: Bug fixes only (no protocol changes)
```

Current version: `1.0.0`

### 2. Client Version Declaration

Clients append version to WebSocket URL:

```typescript
// Frontend connection
const url = `wss://api.example.com/ws/devtools?token=xxx&v=1.0.0`;
```

### 3. Server Version Validation

Server validates client version on connection:

```python
def validate_protocol_version(client_version: str | None) -> tuple[bool, str]:
    """
    Validate client protocol version against server.

    Compatibility rules:
    - Major version must match exactly (breaking changes)
    - Minor version: server >= client (backwards compatible)
    - Patch version: any (bug fixes only)
    """
```

### 4. Close Code 4009: Protocol Version Mismatch

When versions are incompatible, server closes with code **4009**:

```
WebSocket Close Codes:
├── 4001: Authentication failed
├── 4002: Protocol error (malformed messages)
├── 4003: Authorization denied
├── 4008: Timeout (idle/heartbeat)
├── 4009: Protocol version not supported (upgrade client)  ← NEW
├── 4010: Token expired (try refresh)
├── 4013: Message too large
└── 4029: Rate limit exceeded
```

### 5. Client Handling

When receiving close code 4009:
1. **Do NOT reconnect** (version mismatch is not recoverable automatically)
2. **Show user notification** prompting to refresh page/update client
3. **Log telemetry** for monitoring version adoption

## Implementation

### Backend Components

#### `ProtocolVersionError` Exception (`websocket/exceptions.py`)

```python
class ProtocolVersionError(WebSocketError):
    """Raised when WebSocket protocol version is incompatible.

    Uses close code 4009 to indicate the client's protocol version
    is not compatible with the server version.
    """

    def __init__(
        self,
        message: str = "Protocol version not supported",
        code: int = 4009,
        reason: str | None = None,
        client_version: str | None = None,
        server_version: str | None = None,
    ) -> None:
        super().__init__(
            message, code,
            reason or "Protocol version not supported. Please upgrade client."
        )
        self.client_version = client_version
        self.server_version = server_version
```

#### Version Validation Functions (`websocket/protocols.py`)

```python
PROTOCOL_VERSION = "1.0.0"

def extract_protocol_version(version_string: str | None) -> tuple[int, int, int] | None:
    """Extract semantic version components from version string."""

def is_version_compatible(client_version: str | None, server_version: str = PROTOCOL_VERSION) -> bool:
    """
    Check if client version is compatible with server version.

    Compatibility rules:
    - Major version must match exactly
    - Minor version: server >= client
    - Patch version: any
    """

def validate_protocol_version(client_version: str | None) -> tuple[bool, str]:
    """Validate client protocol version against server."""
```

#### Connection Handler Integration

```python
async def handle_connection(self, websocket: WebSocket) -> None:
    # Extract version from query params
    client_version = websocket.query_params.get("v")

    # Validate version before accepting connection
    is_valid, error = validate_protocol_version(client_version)
    if not is_valid:
        await websocket.close(code=4009, reason=error)
        return

    # Proceed with authenticated connection
    await websocket.accept()
```

### Frontend Components

#### WebSocket Auth Utility (`utils/websocketAuth.ts`)

```typescript
/**
 * WebSocket close code for protocol version mismatch.
 *
 * When backend detects client's protocol version is incompatible,
 * it closes with this code. Frontend should:
 * 1. Show user-friendly message indicating client needs update
 * 2. NOT attempt to reconnect (version mismatch is not recoverable)
 * 3. Suggest refreshing the page or updating the application
 */
export const WS_CLOSE_PROTOCOL_VERSION = 4009;

/**
 * Standard notification payload for protocol version mismatch.
 */
export const PROTOCOL_VERSION_MISMATCH_NOTIFICATION = {
  type: "error" as const,
  title: "Application Update Required",
  message: "Your application version is incompatible with the server. " +
           "Please refresh the page to get the latest version.",
  action: {
    label: "Refresh",
    onClick: () => window.location.reload(),
  },
};
```

#### useRealtimeSync Hook Enhancement

```typescript
ws.onclose = (event) => {
  if (event.code === WS_CLOSE_PROTOCOL_VERSION) {
    // Version mismatch - do NOT reconnect
    setStatus("error");
    onProtocolVersionError?.();
    // Dispatch user notification
    return;
  }

  if (event.code === WS_CLOSE_TOKEN_EXPIRED) {
    // Token expired - try refresh and reconnect
    handleTokenExpiredReconnect();
    return;
  }

  // Other errors - attempt reconnect with backoff
  scheduleReconnect();
};
```

### URL Construction

```typescript
// websocket.ts
export function buildWebSocketUrl(
  endpoint: string,
  params?: Record<string, string>,
  includeAuthToken = false
): string {
  const url = new URL(endpoint, window.location.origin);

  // Add protocol version
  url.searchParams.set("v", PROTOCOL_VERSION);

  // Add auth token if requested
  if (includeAuthToken) {
    const token = getAuthToken();
    if (token) {
      url.searchParams.set("token", token);
    }
  }

  // Add custom params
  if (params) {
    Object.entries(params).forEach(([key, value]) => {
      url.searchParams.set(key, value);
    });
  }

  return url.toString().replace("http", "ws");
}
```

## Compatibility Rules

| Client | Server | Compatible? | Rationale |
|--------|--------|-------------|-----------|
| 1.0.0  | 1.0.0  | Yes | Exact match |
| 1.0.0  | 1.1.0  | Yes | Server has newer features, client doesn't need them |
| 1.1.0  | 1.0.0  | No | Client expects features server doesn't have |
| 2.0.0  | 1.0.0  | No | Major version change = breaking changes |
| 1.0.0  | 2.0.0  | No | Major version change = breaking changes |
| 1.0.5  | 1.0.0  | Yes | Patch versions don't affect protocol |

## Version Bump Guidelines

### Major Version (X.0.0)
Bump for:
- Removing message types
- Changing message type names
- Changing required field names or types
- Changing connection handshake semantics

### Minor Version (X.Y.0)
Bump for:
- Adding new message types
- Adding optional fields to existing messages
- Adding new endpoints
- New features with graceful degradation

### Patch Version (X.Y.Z)
Bump for:
- Bug fixes in message validation
- Error message improvements
- Documentation updates

## Testing Strategy

### Unit Tests

```python
# test_protocol_version.py
class TestIsVersionCompatible:
    def test_same_version_is_compatible(self):
        assert is_version_compatible("1.0.0", "1.0.0") is True

    def test_different_major_version_not_compatible(self):
        assert is_version_compatible("2.0.0", "1.0.0") is False

    def test_client_lower_minor_is_compatible(self):
        assert is_version_compatible("1.0.0", "1.1.0") is True

    def test_client_higher_minor_not_compatible(self):
        assert is_version_compatible("1.2.0", "1.1.0") is False
```

### Integration Tests

```python
@pytest.mark.integration
async def test_version_mismatch_closes_connection():
    """Server should close with 4009 for incompatible version."""
    async with websocket_connect("ws://localhost:8000/ws?v=2.0.0") as ws:
        with pytest.raises(ConnectionClosedError) as exc:
            await ws.recv()
        assert exc.value.code == 4009
```

## Consequences

### Positive

- **Early failure**: Incompatible clients fail fast at connection time
- **Clear feedback**: Users see actionable error message
- **Monitoring**: Telemetry shows version adoption and migration progress
- **Documentation**: Version changes are traceable through ADRs
- **Graceful evolution**: Minor versions allow feature additions without breaking clients

### Negative

- **URL length**: Adds `?v=1.0.0` to all WebSocket URLs
- **Coordination**: Version bumps require frontend + backend synchronization
- **Testing complexity**: Need to test version combinations

### Mitigations

- Keep version in constants (`PROTOCOL_VERSION`) for easy updates
- Include version in telemetry for monitoring
- Use feature flags for transitional periods during major upgrades

## Migration Path

1. **Phase 1** (Current): Add version validation with `v=1.0.0`
2. **Phase 2**: Enable version telemetry and monitoring dashboards
3. **Phase 3**: Use version data to time major version rollouts

## References

- [Semantic Versioning 2.0.0](https://semver.org/)
- [RFC 6455: WebSocket Protocol](https://tools.ietf.org/html/rfc6455)
- [ADR-0074: WebSocket Token Expiration](./ADR-0074-WEBSOCKET-TOKEN-EXPIRATION.md)
- [WebSocket Close Codes Registry](https://www.iana.org/assignments/websocket/websocket.xml)
