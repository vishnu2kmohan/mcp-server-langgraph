# WebSocket Patterns and Best Practices

This document describes the WebSocket hook patterns implemented in the frontend codebase.

## Overview

The frontend uses a layered WebSocket architecture with `useRealtimeSync` as the foundation hook and specialized domain hooks built on top of it.

## Architecture

```
┌─────────────────────────────────────────────────────────────────┐
│                     Domain-Specific Hooks                        │
├──────────────────┬──────────────────┬──────────────────────────┤
│ useNotification  │ useMCPWebSocket  │ useAlertWebSocket        │
│   WebSocket      │                  │                          │
├──────────────────┴──────────────────┴──────────────────────────┤
│                     useMCPTaskWebSocket                         │
│                     useConnectionHealthWebSocket                │
│                     useAuditWebSocket                           │
├─────────────────────────────────────────────────────────────────┤
│                     useRealtimeSync (Foundation)                │
│         - Connection state management                           │
│         - Exponential backoff reconnection                      │
│         - Subscription restoration                              │
│         - Message parsing                                       │
└─────────────────────────────────────────────────────────────────┘
```

## Core Hook: useRealtimeSync

The foundation hook providing all WebSocket functionality.

### Configuration Options

```typescript
interface RealtimeSyncOptions {
  url: string;                      // WebSocket endpoint URL
  reconnectInterval?: number;       // Base delay between reconnections (default: 1000ms)
  maxReconnectAttempts?: number;    // Max attempts before giving up (default: 10)
  exponentialBackoff?: boolean;     // Enable exponential backoff (default: false)
  maxDelayMs?: number;              // Maximum delay for exponential backoff (default: 30000ms)
  onMessage?: (data: unknown) => void;
  onConnect?: () => void;
  onDisconnect?: () => void;
  getSubscriptions?: () => Array<{ type: string; payload: unknown }>;
}
```

### Connection States

- `connecting` - Establishing connection
- `connected` - Connected and ready
- `disconnected` - Not connected
- `reconnecting` - Attempting reconnection

### Exponential Backoff

When `exponentialBackoff: true`, reconnection delays follow:

```
Delay = min(baseDelay * 2^attemptNumber + jitter, maxDelayMs)
```

Example with baseDelay=1000ms, maxDelayMs=30000ms:
- Attempt 1: ~1-1.3s
- Attempt 2: ~2-2.6s
- Attempt 3: ~4-5.2s
- Attempt 4: ~8-10.4s
- Attempt 5: ~16-20.8s
- Attempt 6+: 30s (capped)

### Subscription Restoration

For stateful protocols, subscriptions are automatically restored on reconnection:

```typescript
const { status } = useRealtimeSync({
  url: wsUrl,
  getSubscriptions: () => [
    { type: 'subscribe', payload: { channel: 'notifications' } },
    { type: 'subscribe', payload: { channel: 'alerts' } },
  ],
  onConnect: () => {
    // Subscriptions are automatically sent after this callback
  },
});
```

## Domain Hook Patterns

### Pattern 1: Notification Delivery

`useNotificationWebSocket` - Delivers real-time notifications to Redux.

```typescript
export function useNotificationWebSocket(options = {}) {
  const { url, enabled = true } = options;
  const dispatch = useAppDispatch();

  const handleMessage = useCallback((data: unknown) => {
    if (isNotificationMessage(data)) {
      dispatch(addNotification(data.payload));
    }
  }, [dispatch]);

  return useRealtimeSync({
    url: wsUrl,
    exponentialBackoff: true,
    reconnectInterval: 1000,
    maxDelayMs: 30000,
    maxReconnectAttempts: 10,
    onMessage: handleMessage,
  });
}
```

### Pattern 2: Task Execution Status

`useMCPTaskWebSocket` - Tracks long-running task execution.

```typescript
export function useMCPTaskWebSocket(options: MCPTaskWebSocketOptions) {
  const { taskId, onProgress, onComplete, onError } = options;

  const handleMessage = useCallback((data: unknown) => {
    const message = data as TaskMessage;
    switch (message.type) {
      case 'progress':
        onProgress?.(message.progress);
        break;
      case 'complete':
        onComplete?.(message.result);
        break;
      case 'error':
        onError?.(message.error);
        break;
    }
  }, [onProgress, onComplete, onError]);

  return useRealtimeSync({
    url: `/ws/tasks/${taskId}`,
    exponentialBackoff: true,
    reconnectInterval: 500,
    maxDelayMs: 5000,
    onMessage: handleMessage,
  });
}
```

### Pattern 3: Health Monitoring

`useConnectionHealthWebSocket` - Monitors connection health.

```typescript
export function useConnectionHealthWebSocket() {
  const [health, setHealth] = useState<HealthStatus>('unknown');

  const handleMessage = useCallback((data: unknown) => {
    const msg = data as HealthMessage;
    setHealth(msg.status);
  }, []);

  const wsResult = useRealtimeSync({
    url: '/ws/health',
    exponentialBackoff: true,
    reconnectInterval: 2000,
    maxDelayMs: 60000,
    maxReconnectAttempts: Infinity,  // Always try to reconnect
    onMessage: handleMessage,
    onDisconnect: () => setHealth('disconnected'),
  });

  return { ...wsResult, health };
}
```

### Pattern 4: Protocol Communication

`useMCPWebSocket` - MCP JSON-RPC protocol over WebSocket.

```typescript
export function useMCPWebSocket(options = {}) {
  const [pendingRequests] = useState(() => new Map());
  const messageIdRef = useRef(0);

  const sendRequest = useCallback(async (method: string, params: unknown) => {
    const id = ++messageIdRef.current;
    const promise = new Promise((resolve, reject) => {
      pendingRequests.set(id, { resolve, reject });
    });

    send({ jsonrpc: '2.0', id, method, params });
    return promise;
  }, [send]);

  const handleMessage = useCallback((data: unknown) => {
    const msg = data as JsonRpcMessage;

    if ('id' in msg) {
      // Response to request
      const pending = pendingRequests.get(msg.id);
      if (pending) {
        if ('error' in msg) {
          pending.reject(msg.error);
        } else {
          pending.resolve(msg.result);
        }
        pendingRequests.delete(msg.id);
      }
    } else if ('method' in msg) {
      // Server notification
      handleNotification(msg);
    }
  }, [handleNotification]);

  return useRealtimeSync({
    url: mcpUrl,
    exponentialBackoff: true,
    onMessage: handleMessage,
  });
}
```

## Best Practices

### 1. Always Enable Exponential Backoff

Production WebSocket hooks should always use exponential backoff to prevent thundering herd problems:

```typescript
// Good
useRealtimeSync({
  exponentialBackoff: true,
  reconnectInterval: 1000,
  maxDelayMs: 30000,
});

// Avoid
useRealtimeSync({
  reconnectInterval: 1000, // Fixed interval can cause issues
});
```

### 2. Appropriate Retry Limits

Set retry limits based on use case:

- **Critical connections** (health, notifications): `maxReconnectAttempts: Infinity`
- **Task-specific** (file watching): `maxReconnectAttempts: 10`
- **Optional features**: `maxReconnectAttempts: 5`

### 3. Subscription Restoration for Stateful Protocols

If the WebSocket requires subscriptions, use `getSubscriptions`:

```typescript
useRealtimeSync({
  getSubscriptions: () => subscriptions.current,
  onConnect: () => {
    console.log('Subscriptions will be restored automatically');
  },
});
```

### 4. Clean Message Handlers

Use type guards for message validation:

```typescript
function isValidMessage(data: unknown): data is MyMessage {
  return (
    typeof data === 'object' &&
    data !== null &&
    'type' in data &&
    typeof (data as Record<string, unknown>).type === 'string'
  );
}

const handleMessage = useCallback((data: unknown) => {
  if (isValidMessage(data)) {
    // Safe to use data.type
  }
}, []);
```

### 5. Proper Cleanup

WebSocket connections are cleaned up automatically when hooks unmount. For manual control:

```typescript
const { disconnect, reconnect } = useNotificationWebSocket();

// When user logs out
useEffect(() => {
  return () => disconnect();
}, [disconnect]);
```

## Testing Patterns

### Mocking useRealtimeSync

```typescript
// In test file
let mockOnMessage: ((data: unknown) => void) | undefined;
let mockOnConnect: (() => void) | undefined;

vi.mock('./useRealtimeSync', () => ({
  useRealtimeSync: (options: RealtimeSyncOptions) => {
    mockOnMessage = options.onMessage;
    mockOnConnect = options.onConnect;
    return {
      status: 'connected',
      send: vi.fn(),
      disconnect: vi.fn(),
      reconnect: vi.fn(),
    };
  },
}));

// In tests
it('handles incoming messages', async () => {
  renderHook(() => useMyWebSocketHook());

  await act(async () => {
    mockOnMessage?.({ type: 'test', data: 'hello' });
  });

  // Assert on expected behavior
});
```

### Testing act() Warnings

Always wrap state-changing operations in `act()`:

```typescript
// Good
await act(async () => {
  mockOnDisconnect?.();
});

// Avoid - causes act() warning
mockOnDisconnect?.();
```

## Configuration Reference

| Hook | Base Delay | Max Delay | Max Attempts | Backoff |
|------|------------|-----------|--------------|---------|
| useNotificationWebSocket | 1000ms | 30000ms | 10 | Yes |
| useMCPTaskWebSocket | 500ms | 5000ms | 10 | Yes |
| useConnectionHealthWebSocket | 2000ms | 60000ms | Infinity | Yes |
| useMCPWebSocket | 1000ms | 30000ms | 10 | Yes |
| useAlertWebSocket | 1000ms | 30000ms | 10 | Yes |
| useAuditWebSocket | 2000ms | 60000ms | 10 | Yes |
| useAgentRequestWebSocket | 1000ms | 30000ms | 10 | Yes |

## WebSocket Close Codes

The application uses custom WebSocket close codes in the 4000-4999 range for application-specific errors. These codes are defined in `utils/websocketAuth.ts` and handled by `useRealtimeSync`.

### Close Code Reference

| Code | Name | Description | Recovery Action |
|------|------|-------------|-----------------|
| 1000 | Normal Closure | Clean disconnect | None needed |
| 1001 | Going Away | Server shutting down | Reconnect with backoff |
| 1006 | Abnormal Closure | Connection lost | Reconnect with backoff |
| **4001** | Authentication Failed | Invalid/missing token on connect | Redirect to login |
| **4002** | Protocol Error | Malformed message format | Log error, reconnect |
| **4003** | Authorization Denied | Valid token, insufficient permissions | Show permission error |
| **4008** | Timeout | Idle/heartbeat timeout | Reconnect with backoff |
| **4009** | Protocol Version Mismatch | Client version incompatible | **DO NOT reconnect** - prompt refresh |
| **4010** | Token Expired | Token expired during connection | Refresh token, reconnect |
| **4013** | Message Too Large | Message exceeds size limit | Reduce payload, retry |
| **4029** | Rate Limited | Too many requests | Wait, reconnect with backoff |

### Close Code 4009: Protocol Version Mismatch

When the server detects an incompatible client protocol version, it closes with code 4009.

**Frontend Handling:**

```typescript
import { WS_CLOSE_PROTOCOL_VERSION, PROTOCOL_VERSION_MISMATCH_NOTIFICATION } from '../utils/websocketAuth';

// In useRealtimeSync onclose handler:
if (event.code === WS_CLOSE_PROTOCOL_VERSION) {
  // 1. DO NOT attempt to reconnect - version mismatch is not recoverable
  setStatus("error");

  // 2. Show user notification
  dispatch(showNotification(PROTOCOL_VERSION_MISMATCH_NOTIFICATION));

  // 3. Log telemetry for monitoring
  reportWebSocketMetrics({
    endpoint: "websocket",
    event: "protocol_version_error",
    clientVersion: PROTOCOL_VERSION,
  });

  return; // Exit without scheduling reconnect
}
```

**When This Occurs:**
- Client sends version incompatible with server (e.g., v2.0.0 vs v1.x.x)
- Major version mismatch indicates breaking protocol changes
- Client requires features server doesn't support

**User Experience:**
```
┌─────────────────────────────────────────────────────┐
│ ⚠️ Application Update Required                      │
│                                                     │
│ Your application version is incompatible with the  │
│ server. Please refresh the page to get the latest  │
│ version.                                            │
│                                                     │
│                              [Refresh]              │
└─────────────────────────────────────────────────────┘
```

### Close Code 4010: Token Expired

When the server detects a token has expired during an active WebSocket connection, it closes with code 4010.

**Frontend Handling:**

```typescript
import { WS_CLOSE_TOKEN_EXPIRED, ensureValidTokenForWebSocket } from '../utils/websocketAuth';

// In useRealtimeSync onclose handler:
if (event.code === WS_CLOSE_TOKEN_EXPIRED) {
  // 1. Attempt to refresh the token
  const refreshed = await ensureValidTokenForWebSocket();

  if (refreshed) {
    // 2a. Token refreshed successfully - reconnect
    scheduleReconnect();
  } else {
    // 2b. Token refresh failed - logout
    dispatch(logout());
  }

  return;
}
```

**When This Occurs:**
- Long-lived WebSocket connection outlives JWT token validity
- Token expiration detected during periodic server-side validation
- Refresh token may still be valid for token renewal

**Recovery Flow:**
```
┌─────────────┐    4010     ┌─────────────────┐   success   ┌─────────────┐
│  Connected  │ ─────────▶ │  Refresh Token  │ ──────────▶ │  Reconnect  │
└─────────────┘            └─────────────────┘             └─────────────┘
                                    │
                                    │ failure
                                    ▼
                           ┌─────────────────┐
                           │    Logout       │
                           └─────────────────┘
```

### Implementing Close Code Handling

For domain-specific hooks, pass the `onTokenExpired` callback to enable token refresh handling:

```typescript
export function useMyWebSocket(options) {
  const dispatch = useAppDispatch();

  const handleTokenExpired = useCallback(async () => {
    const refreshed = await ensureValidTokenForWebSocket();
    if (!refreshed) {
      dispatch(logout());
    }
    return refreshed;
  }, [dispatch]);

  return useRealtimeSync({
    url: options.url,
    exponentialBackoff: true,
    onTokenExpired: handleTokenExpired,
    onProtocolVersionError: () => {
      dispatch(showNotification(PROTOCOL_VERSION_MISMATCH_NOTIFICATION));
    },
    // ... other options
  });
}
```

### Constants Location

Close code constants are defined in `src/utils/websocketAuth.ts`:

```typescript
export const WS_CLOSE_TOKEN_EXPIRED = 4010;
export const WS_CLOSE_PROTOCOL_VERSION = 4009;

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

/**
 * Show immediate toast notification for protocol version mismatch.
 */
export function showProtocolVersionMismatchToast(): void {
  toast.error("Application Update Required", {
    description: "Your application version is incompatible with the server. Please refresh.",
    duration: 15000,
    action: {
      label: "Refresh",
      onClick: () => window.location.reload(),
    },
  });
}
```

### Dual Notification Pattern

For critical errors like protocol version mismatch, use both:
1. **Sonner toast** - Immediate transient feedback (appears instantly, disappears after 15s)
2. **Redux notification** - Persistent entry in notification center

```typescript
onProtocolVersionMismatch: () => {
  // Persistent notification for notification center
  dispatch(addNotification(PROTOCOL_VERSION_MISMATCH_NOTIFICATION));
  // Immediate toast for instant user feedback
  showProtocolVersionMismatchToast();
},
```

This dual approach ensures users see the error immediately while also having a persistent record in the notification center.

## Files Reference

- `src/hooks/useRealtimeSync.ts` - Foundation hook
- `src/hooks/useRealtimeSync.test.ts` - Foundation tests
- `src/hooks/useNotificationWebSocket.ts` - Notification delivery
- `src/hooks/useMCPWebSocket.ts` - MCP protocol
- `src/hooks/useMCPTaskWebSocket.ts` - Task tracking
- `src/hooks/useConnectionHealthWebSocket.ts` - Health monitoring
- `src/hooks/useAlertWebSocket.ts` - Alert notifications
- `src/hooks/useAuditWebSocket.ts` - Audit events
- `src/hooks/useAgentRequestWebSocket.ts` - Agent HITL requests
