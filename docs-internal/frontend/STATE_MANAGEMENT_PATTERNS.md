# Frontend State Management Patterns

**Date**: 2025-12-14
**Status**: Current Reference
**Maintainer**: Claude Code

---

## Overview

The MCP Server LangGraph Studio frontend uses a **hybrid state management approach** combining:

1. **RTK Query** - Server-cached API data with automatic caching
2. **Redux Toolkit Slices** - Local state and async operations
3. **Component Local State** - UI-specific ephemeral state

This document describes when to use each pattern and how they work together.

---

## Architecture Diagram

```
┌─────────────────────────────────────────────────────────────────┐
│                        Redux Store                               │
├─────────────────────────────────────────────────────────────────┤
│                                                                  │
│  ┌──────────────────────────┐  ┌─────────────────────────────┐  │
│  │     RTK Query (api)      │  │     Redux Slices            │  │
│  │                          │  │                             │  │
│  │  • Auto-caching          │  │  • session    (async ops)   │  │
│  │  • Request deduplication │  │  • project    (async ops)   │  │
│  │  • Tag-based invalidation│  │  • workflow   (builder)     │  │
│  │  • Loading/error states  │  │  • artifact   (chat data)   │  │
│  │                          │  │  • mcp        (connections) │  │
│  │  Hooks:                  │  │  • auth       (tokens)      │  │
│  │  • useGetXXXQuery        │  │  • persona    (RBAC)        │  │
│  │  • useXXXMutation        │  │  • notifications            │  │
│  │                          │  │  • ui         (panels)      │  │
│  └──────────────────────────┘  └─────────────────────────────┘  │
│                                                                  │
└─────────────────────────────────────────────────────────────────┘
```

---

## 1. RTK Query Pattern

### When to Use RTK Query

- **Read-heavy endpoints** that benefit from caching
- **List operations** with pagination (auto-cache by params)
- **Feature flags** and configuration data
- **User profile** and settings
- **Observability data** (traces, logs, metrics)

### Implementation

```typescript
// src/api/index.ts
export const api = createApi({
  reducerPath: "api",
  baseQuery: fetchBaseQuery({ baseUrl: "/api/v1" }),
  tagTypes: ["Session", "Workflow", "Project", "Cost"],
  endpoints: (builder) => ({
    // Query - for GET requests (auto-cached)
    getSessionMessages: builder.query<Message[], string>({
      query: (sessionId) => `sessions/${sessionId}/messages`,
      providesTags: (result, error, sessionId) => [
        { type: "Session", id: sessionId },
      ],
    }),

    // Mutation - for POST/PUT/DELETE
    createWorkflow: builder.mutation<Workflow, CreateWorkflowParams>({
      query: (params) => ({
        url: "workflows",
        method: "POST",
        body: params,
      }),
      invalidatesTags: ["Workflow"],
    }),
  }),
});

// Auto-generated hooks
export const { useGetSessionMessagesQuery, useCreateWorkflowMutation } = api;
```

### Usage in Components

```typescript
function MessageList({ sessionId }: { sessionId: string }) {
  // RTK Query hook - handles loading, error, caching
  const { data: messages, isLoading, error } = useGetSessionMessagesQuery(sessionId);

  if (isLoading) return <Loading />;
  if (error) return <Error />;

  return <ul>{messages?.map(m => <MessageItem key={m.id} message={m} />)}</ul>;
}
```

### Current RTK Query Endpoints

| Category | Hooks | Purpose |
|----------|-------|---------|
| **Features** | `useGetFeatureFlagsQuery` | Feature flag configuration |
| **User** | `useGetCurrentUserQuery` | User profile and roles |
| **Sessions** | `useListSessionsQuery`, `useGetSessionMessagesQuery` | Session data |
| **Workflows** | `useListWorkflowsQuery`, `useGetWorkflowQuery` | Workflow data |
| **Projects** | `useListProjectsQuery`, `useGetProjectQuery` | Project data |
| **Cost** | `useGetCostSummaryQuery`, `useGetCostByModelQuery`, `useGetCostHistoryQuery` | Cost analytics |
| **Observability** | `useListTracesQuery`, `useListLogsQuery`, `useGetMetricsQuery` | Traces/logs/metrics |
| **Audit** | `useListAuditLogsQuery` | Audit logs |
| **Connections** | `useListConnectionsQuery` | MCP connections |

---

## 2. Redux Slice Pattern

### When to Use Redux Slices

- **Complex async workflows** (multi-step operations)
- **Optimistic updates** requiring rollback
- **Real-time data** via WebSocket (not HTTP)
- **Builder state** (workflow canvas, node positions)
- **Cross-component communication**
- **Client-only state** (UI state, selections)

### Implementation

```typescript
// src/store/slices/sessionSlice.ts
interface SessionState {
  currentSessionId: string | null;
  messages: Message[];
  isStreaming: boolean;
  streamingContent: string;
}

const sessionSlice = createSlice({
  name: "session",
  initialState,
  reducers: {
    // Synchronous actions
    setCurrentSession: (state, action: PayloadAction<string>) => {
      state.currentSessionId = action.payload;
    },
    appendStreamChunk: (state, action: PayloadAction<string>) => {
      state.streamingContent += action.payload;
    },
  },
  extraReducers: (builder) => {
    // Async thunk handlers
    builder
      .addCase(sendMessage.pending, (state) => {
        state.isStreaming = true;
      })
      .addCase(sendMessage.fulfilled, (state, action) => {
        state.isStreaming = false;
        state.messages.push(action.payload);
      });
  },
});
```

### Current Redux Slices

| Slice | Purpose | Key Features |
|-------|---------|--------------|
| **sessionSlice** | Chat session management | Streaming, message handling, SSE |
| **projectSlice** | Project CRUD operations | Async thunks for API calls |
| **workflowSlice** | Workflow builder state | Canvas nodes, connections, execution |
| **artifactSlice** | Chat artifacts | Charts, tables, code blocks |
| **mcpSlice** | MCP connections | WebSocket state, tool calls |
| **authSlice** | Authentication | Tokens, login/logout, refresh |
| **personaSlice** | RBAC/personas | Role derivation, permissions |
| **notificationSlice** | Notifications | WebSocket notifications |
| **uiSlice** | UI state | Panel collapse, theme |

---

## 3. Component Local State Pattern

### When to Use Local State

- **Form input values** before submission
- **Toggle states** (dropdowns, modals)
- **Search/filter query** before API call
- **Selection state** (checkboxes, multi-select)
- **Ephemeral UI state** (tooltips, animations)

### Implementation

```typescript
function WorkflowsTab({ workflows }: Props) {
  // Local state for search/filter (not persisted)
  const [searchQuery, setSearchQuery] = useState("");
  const [sortBy, setSortBy] = useState<SortField>("created_at");
  const [selectedIds, setSelectedIds] = useState<Set<string>>(new Set());

  // Derived state using useMemo
  const filteredWorkflows = useMemo(() => {
    let result = [...workflows];
    if (searchQuery) {
      result = result.filter(w =>
        w.name.toLowerCase().includes(searchQuery.toLowerCase())
      );
    }
    return result.sort((a, b) => /* sorting logic */);
  }, [workflows, searchQuery, sortBy]);

  return (/* render */);
}
```

---

## 4. Pattern Decision Matrix

Use this matrix to decide which pattern to use:

| Scenario | RTK Query | Redux Slice | Local State |
|----------|:---------:|:-----------:|:-----------:|
| **GET request with caching** | ✅ | | |
| **Paginated list from API** | ✅ | | |
| **Feature flags/config** | ✅ | | |
| **Multi-step async workflow** | | ✅ | |
| **SSE/streaming data** | | ✅ | |
| **WebSocket connection** | | ✅ | |
| **Optimistic updates** | | ✅ | |
| **Canvas/builder state** | | ✅ | |
| **Cross-component sync** | | ✅ | |
| **Form input (pre-submit)** | | | ✅ |
| **Search query** | | | ✅ |
| **UI toggles** | | | ✅ |
| **Selection state** | | | ✅ |

---

## 5. Mixed Patterns: Known Issues

### Current Technical Debt

1. **VectorsPage uses direct fetch** instead of RTK Query
   - Should migrate to `useSearchVectorsMutation` and `useUpsertVectorsMutation`

2. **Some pages mix patterns inconsistently**
   - ProjectDetailPage: Direct fetch + Redux slice
   - Should standardize on RTK Query for read operations

3. **Duplicate loading states**
   - Both RTK Query `isLoading` and slice `loading` flags exist
   - Prefer RTK Query states when using queries

### Recommended Migration Path

1. Use RTK Query for all new API endpoints
2. Gradually migrate direct fetch calls to RTK Query
3. Keep Redux slices for complex async workflows and WebSocket state
4. Use local state for ephemeral UI state

---

## 6. Testing Patterns

### Testing RTK Query

```typescript
// Mock at module level
vi.mock("../api", async (importOriginal) => {
  const actual = await importOriginal();
  return {
    ...actual,
    useGetSessionMessagesQuery: vi.fn(() => ({
      data: mockMessages,
      isLoading: false,
      error: null,
    })),
  };
});
```

### Testing Redux Slices

```typescript
import { configureStore } from "@reduxjs/toolkit";
import sessionReducer from "./sessionSlice";

function createTestStore() {
  return configureStore({
    reducer: { session: sessionReducer },
    preloadedState: { /* initial state */ },
  });
}

test("should update session", () => {
  const store = createTestStore();
  store.dispatch(setCurrentSession("session-1"));
  expect(store.getState().session.currentSessionId).toBe("session-1");
});
```

### Testing Local State

```typescript
render(<WorkflowsTab workflows={mockWorkflows} />);

const searchInput = screen.getByPlaceholderText(/search/i);
fireEvent.change(searchInput, { target: { value: "test" } });

expect(screen.getByText("Test Workflow")).toBeInTheDocument();
```

---

## 7. File Structure

```
src/
├── api/
│   └── index.ts              # RTK Query API definition
├── store/
│   ├── index.ts              # Store configuration
│   ├── hooks.ts              # Typed hooks (useAppDispatch, useAppSelector)
│   └── slices/
│       ├── sessionSlice.ts   # Session state + async thunks
│       ├── projectSlice.ts   # Project state + async thunks
│       ├── workflowSlice.ts  # Workflow builder state
│       ├── artifactSlice.ts  # Chat artifacts
│       ├── mcpSlice.ts       # MCP connections
│       ├── authSlice.ts      # Authentication
│       ├── personaSlice.ts   # RBAC/personas
│       ├── notificationSlice.ts  # Notifications
│       └── uiSlice.ts        # UI state
└── hooks/
    ├── useStreamingChat.ts   # SSE streaming hook
    ├── useNotificationWebSocket.ts  # WebSocket hook
    └── ...
```

---

## 8. WebSocket Hook Patterns

The frontend uses a standardized WebSocket architecture for real-time communication.

### Base Hook: `useRealtimeSync`

All WebSocket connections should use `useRealtimeSync` as the foundation:

```typescript
import { useRealtimeSync } from "../hooks";

const { status, send, disconnect, reconnect, metrics } = useRealtimeSync({
  url: wsUrl,
  reconnectInterval: 1000,
  maxReconnectAttempts: 5,
  exponentialBackoff: true,
  onMessage: handleMessage,
  onConnect: handleConnect,
  onDisconnect: handleDisconnect,
  onTokenExpired: handleTokenExpired,
  onProtocolVersionMismatch: handleVersionMismatch,
});
```

### Features Provided

| Feature | Description |
|---------|-------------|
| Automatic reconnection | Configurable retry with exponential backoff |
| Token handling | Handles 4010 (token expired) close code |
| Protocol versioning | Handles 4009 (version mismatch) close code |
| Message queuing | Queues messages while reconnecting |
| Metrics | Reconnection metrics for observability |

### Creating Domain-Specific Hooks

Domain hooks should wrap `useRealtimeSync`:

```typescript
export function useCostTrackingWebSocket(options = {}) {
  // 1. Check permissions
  const wsPermissions = useAppSelector(selectWebSocketPermissions);
  const hasCostPermission = wsPermissions?.cost_tracking ?? false;

  // 2. Build URL only when authorized
  const url = useMemo(
    () => hasCostPermission ? buildWebSocketUrl(WS_ENDPOINTS.COST) : "",
    [hasCostPermission]
  );

  // 3. Domain-specific state
  const [sessionCosts, setSessionCosts] = useState<Record<string, SessionCost>>({});

  // 4. Callback refs (avoid stale closures)
  const callbacksRef = useRef({ onCostEvent, onBudgetWarning });
  callbacksRef.current = { onCostEvent, onBudgetWarning };

  // 5. Message handler with camelCase transform
  const handleMessage = useCallback((data: unknown) => {
    const message = transformSnakeToCamel(data) as ServerMessage;
    switch (message.type) {
      case "cost_event":
        callbacksRef.current.onCostEvent?.(message.payload);
        break;
      // ...
    }
  }, []);

  // 6. Use base hook
  const { status, send, disconnect, reconnect } = useRealtimeSync({
    url,
    onMessage: handleMessage,
  });

  // 7. Return domain-specific interface
  return { status, sessionCosts, subscribeSession, /* ... */ };
}
```

### WebSocket Hooks Available

| Hook | Endpoint | Purpose |
|------|----------|---------|
| `useRealtimeSync` | (base) | Foundation for all WebSocket hooks |
| `useCostTrackingWebSocket` | `/ws/usage/cost` | Real-time cost tracking |
| `useAlertWebSocket` | `/ws/alerts` | Prometheus alert updates |
| `useTraceWebSocket` | `/ws/traces` | OpenTelemetry trace streaming |
| `useNotificationWebSocket` | `/ws/notifications` | User notifications |
| `useMCPWebSocket` | `/mcp/ws` | MCP server communication |
| `useConnectionsRealtimeWebSocket` | `/ws/connections` | Connection health updates |
| `useHeartMetricsWebSocket` | `/ws/heart/metrics` | HEART framework metrics |

### Best Practices for WebSocket Hooks

1. **Always use `useRealtimeSync`** as base (except for special cases like MCP with REST fallback)
2. **Check permissions** before building WebSocket URL
3. **Use callback refs** to avoid stale closures in message handlers
4. **Transform messages** using `transformSnakeToCamel` per ADR-0091
5. **Handle all close codes** especially 4009 (version) and 4010 (token)
6. **Report metrics** using `reportWebSocketMetrics`

---

## 9. Best Practices

### DO

- Use RTK Query for cacheable API data
- Use Redux slices for complex async workflows
- Use local state for ephemeral UI state
- Leverage `providesTags` and `invalidatesTags` for cache management
- Use typed hooks (`useAppDispatch`, `useAppSelector`)

### DON'T

- Don't use direct `fetch()` for new API calls - use RTK Query
- Don't store form input values in Redux - use local state
- Don't create new Zustand stores - use Redux slices
- Don't mix loading states from different sources

---

## Summary

The frontend uses a hybrid approach optimized for different use cases:

| Layer | Technology | Use Case |
|-------|------------|----------|
| **Server Cache** | RTK Query | API data with caching |
| **App State** | Redux Slices | Complex workflows, WebSockets |
| **UI State** | useState/useMemo | Ephemeral, component-specific |

This architecture provides:
- Automatic caching and deduplication
- Predictable state updates
- Good developer experience
- Easy testing
