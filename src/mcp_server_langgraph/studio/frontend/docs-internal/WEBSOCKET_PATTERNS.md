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
