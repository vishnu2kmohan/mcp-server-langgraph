# Workflow Execution WebSocket Contract

**Created**: 2025-12-14
**Status**: Active
**Endpoint**: `ws[s]://{host}/api/v1/workflows/{workflowId}/execution`

---

## Overview

This document defines the WebSocket message contract for real-time workflow execution updates between the frontend and backend.

## Connection

### URL Pattern
```
ws://{host}/api/v1/workflows/{workflowId}/execution   # HTTP
wss://{host}/api/v1/workflows/{workflowId}/execution  # HTTPS
```

### Connection Lifecycle
1. Frontend connects when ExecutionPanel is opened
2. Backend accepts connection and waits for commands
3. Frontend sends `start` message to begin execution
4. Backend streams execution updates
5. Frontend can send `stop` message to cancel execution
6. Connection closes when panel is closed or manually disconnected

### Reconnection Behavior
- **Max Attempts**: 5 (configurable)
- **Interval**: 1000ms (configurable)
- **Trigger**: Abnormal close (non-1000 close code)
- **Reset**: Attempts reset on successful reconnection

---

## Message Types

### Client → Server Messages

#### Start Execution
```typescript
interface StartExecutionMessage {
  type: 'start';
  workflowId: string;
  input?: Record<string, unknown>;  // Optional input data for workflow
}
```

**Example:**
```json
{
  "type": "start",
  "workflowId": "wf-123",
  "input": {
    "prompt": "Analyze this document",
    "temperature": 0.7
  }
}
```

#### Stop Execution
```typescript
interface StopExecutionMessage {
  type: 'stop';
  workflowId: string;
}
```

**Example:**
```json
{
  "type": "stop",
  "workflowId": "wf-123"
}
```

---

### Server → Client Messages

#### Execution Started
Sent when workflow execution begins.

```typescript
interface ExecutionStartedMessage {
  type: 'execution_started';
  workflowId: string;
}
```

#### Execution Completed
Sent when workflow execution completes successfully.

```typescript
interface ExecutionCompletedMessage {
  type: 'execution_completed';
  workflowId: string;
  result?: unknown;  // Optional result data
}
```

#### Execution Error
Sent when workflow execution fails.

```typescript
interface ExecutionErrorMessage {
  type: 'execution_error';
  workflowId: string;
  error: string;  // Human-readable error message
}
```

#### Node Started
Sent when a specific node begins execution.

```typescript
interface NodeStartedMessage {
  type: 'node_started';
  nodeId: string;
}
```

#### Node Completed
Sent when a specific node completes successfully.

```typescript
interface NodeCompletedMessage {
  type: 'node_completed';
  nodeId: string;
}
```

#### Node Error
Sent when a specific node fails.

```typescript
interface NodeErrorMessage {
  type: 'node_error';
  nodeId: string;
  error: string;  // Human-readable error message
}
```

#### Log Message
Sent for execution logs and debugging information.

```typescript
interface LogMessage {
  type: 'log';
  level: 'info' | 'warning' | 'error' | 'debug';
  message: string;
  nodeId?: string;  // Optional: associates log with specific node
}
```

**Example:**
```json
{
  "type": "log",
  "level": "info",
  "message": "Processing input data",
  "nodeId": "node-llm-1"
}
```

---

## Frontend State Mapping

| Message Type | Redux Action | State Change |
|--------------|--------------|--------------|
| `execution_started` | `setExecutionState('running')` | `executionState = 'running'` |
| `execution_completed` | `setExecutionState('completed')` | `executionState = 'completed'` |
| `execution_error` | `setExecutionState('error')` + `addExecutionLog` | `executionState = 'error'` |
| `node_started` | `updateNodeStatus(nodeId, 'running')` | `nodeStatuses[nodeId] = 'running'` |
| `node_completed` | `updateNodeStatus(nodeId, 'success')` | `nodeStatuses[nodeId] = 'success'` |
| `node_error` | `updateNodeStatus(nodeId, 'error')` | `nodeStatuses[nodeId] = 'error'` |
| `log` | `addExecutionLog(log)` | Appends to `executionLogs[]` |

---

## Connection Status States

| Status | Description | UI Indicator |
|--------|-------------|--------------|
| `connecting` | Initial connection attempt | Yellow spinner |
| `connected` | Successfully connected | Green WiFi icon |
| `reconnecting` | Attempting to reconnect | Orange spinner + attempt count |
| `disconnected` | Connection closed normally | Red WiFi-off icon |
| `error` | Connection error occurred | Red WiFi-off icon |

---

## Error Handling

### Connection Errors
- Frontend displays connection status indicator
- Automatic reconnection attempts (up to 5)
- Manual reconnect button available when disconnected

### Execution Errors
- `execution_error` message triggers error state
- Error message displayed in ExecutionPanel logs
- Node that caused error shows red error badge

---

## Security Considerations

1. **Authentication**: WebSocket connection should require valid JWT
2. **Authorization**: Verify user has execute permission on workflow
3. **Rate Limiting**: Limit message frequency to prevent abuse
4. **Input Validation**: Validate all incoming message structures

---

## Implementation References

### Frontend
- Hook: `src/hooks/useWorkflowExecution.ts`
- Base Hook: `src/hooks/useRealtimeSync.ts`
- Redux Slice: `src/store/slices/workflowSlice.ts`
- Types: `src/types/workflow.ts`

### Backend (TODO)
- WebSocket endpoint implementation needed at `/api/v1/workflows/{id}/execution`
- Should integrate with LangGraph execution engine
- Stream node-by-node execution updates
