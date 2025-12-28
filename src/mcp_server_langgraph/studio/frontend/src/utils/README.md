# Authentication Utilities

This directory contains authentication utilities for the Studio frontend.

## Overview

The authentication system uses JWT tokens stored in localStorage with automatic token refresh on expiration.

| Utility | Purpose | Use Case |
|---------|---------|----------|
| `authenticatedFetch` | HTTP fetch with auto-refresh | REST API calls |
| `websocketAuth` | WebSocket token management | WebSocket connections |
| `storage` | Token storage | Low-level token access |

## authenticatedFetch

Fetch wrapper that automatically handles authentication:
1. Adds `Authorization: Bearer <token>` header
2. Handles 401 by attempting token refresh
3. Retries original request if refresh succeeds
4. Calls `onAuthFailure` callback if refresh fails

### Basic Usage

```typescript
import { authenticatedFetch } from "../utils/authenticatedFetch";

// GET request
const response = await authenticatedFetch("/api/v1/sessions");
const data = await response.json();

// POST request
const response = await authenticatedFetch("/api/v1/sessions", {
  method: "POST",
  headers: { "Content-Type": "application/json" },
  body: JSON.stringify({ name: "My Session" }),
});
```

### With Navigation (React Components)

For React components with access to navigation, use `onAuthFailure` to redirect to login:

```typescript
import { useNavigate } from "react-router-dom";
import { useCallback } from "react";
import { authenticatedFetch } from "../utils/authenticatedFetch";
import { setIntendedRoute } from "../utils/intendedRoute";

function MyComponent() {
  const navigate = useNavigate();

  const handleAuthFailure = useCallback(() => {
    setIntendedRoute(); // Save current route for redirect after login
    navigate("/login", { replace: true });
  }, [navigate]);

  const fetchData = async () => {
    const response = await authenticatedFetch("/api/v1/data", {
      onAuthFailure: handleAuthFailure,
    });
    // ...
  };
}
```

### Without Navigation (Redux Thunks, Hooks)

For Redux thunks or hooks without navigation context, omit `onAuthFailure`:

```typescript
// Redux thunk
export const fetchSessions = createAsyncThunk(
  "sessions/fetch",
  async (_, { rejectWithValue }) => {
    const response = await authenticatedFetch("/api/v1/sessions");
    if (!response.ok) {
      return rejectWithValue("Failed to fetch");
    }
    return response.json();
  }
);
```

### Skip Auth (Public Endpoints)

For public endpoints that don't require authentication:

```typescript
const response = await authenticatedFetch("/api/v1/public/health", {
  skipAuth: true,
});
```

### API Reference

```typescript
interface AuthenticatedFetchOptions extends RequestInit {
  /**
   * Skip adding Authorization header (for public endpoints)
   */
  skipAuth?: boolean;

  /**
   * Callback when authentication fails (no token, refresh failed)
   * Use this to redirect to login
   */
  onAuthFailure?: () => void;
}

function authenticatedFetch(
  url: string,
  options?: AuthenticatedFetchOptions
): Promise<Response>;
```

## websocketAuth

Utilities for WebSocket token management:
1. Check if token is expiring soon
2. Proactively refresh token before connection
3. Handle token expiration during connection (close code 4010)

### Usage with useRealtimeSync

The `useRealtimeSync` hook automatically handles token expiration:

```typescript
import { useRealtimeSync } from "../hooks/useRealtimeSync";
import { useAppDispatch } from "../store/hooks";
import { logout } from "../store/slices/authSlice";

function useMyWebSocket() {
  const dispatch = useAppDispatch();

  const { status, send, disconnect } = useRealtimeSync({
    url: "wss://api.example.com/ws/data?token=...",
    onMessage: (data) => console.log(data),
    onTokenExpired: () => dispatch(logout()), // Redirect to login
  });
}
```

### Close Code 4010

When the backend detects an expired token on an active WebSocket, it closes with code 4010. The frontend should:

1. Call `ensureValidTokenForWebSocket()` to refresh
2. Reconnect if refresh succeeds
3. Redirect to login if refresh fails

```typescript
import { WS_CLOSE_TOKEN_EXPIRED, ensureValidTokenForWebSocket } from "../utils/websocketAuth";

ws.onclose = async (event) => {
  if (event.code === WS_CLOSE_TOKEN_EXPIRED) {
    const refreshed = await ensureValidTokenForWebSocket();
    if (refreshed) {
      // Reconnect with fresh token
    } else {
      // Redirect to login
    }
  }
};
```

### API Reference

```typescript
/**
 * WebSocket close code for token expiration (4010)
 */
export const WS_CLOSE_TOKEN_EXPIRED = 4010;

/**
 * Check if a JWT token is expiring soon (within 5 minutes)
 */
function isTokenExpiringSoon(
  token: string,
  bufferSeconds?: number
): boolean;

/**
 * Ensure a valid token is available for WebSocket connection.
 * Refreshes token if expiring soon.
 * @returns true if valid token available, false if refresh failed
 */
async function ensureValidTokenForWebSocket(): Promise<boolean>;
```

## Token Storage (storage.ts)

Low-level token storage utilities. Prefer `authenticatedFetch` for HTTP and WebSocket hooks for real-time.

```typescript
import { getAuthToken, setAuthTokens, clearAuthTokens } from "../utils/storage";

// Get current access token
const token = getAuthToken();

// Set new tokens (after login or refresh)
setAuthTokens(accessToken, refreshToken);

// Clear tokens (on logout)
clearAuthTokens();
```

## Decision Matrix: Which Utility to Use?

| Scenario | Utility | Example |
|----------|---------|---------|
| REST API call in component | `authenticatedFetch` + `onAuthFailure` | `SessionsTab.tsx` |
| REST API call in Redux thunk | `authenticatedFetch` | `sessionSlice.ts` |
| REST API call in route loader | Custom `fetchJson` with `redirect()` | `canvasLoaders.ts` |
| WebSocket connection | `useRealtimeSync` with `onTokenExpired` | `useAuditWebSocket.ts` |
| Direct WebSocket (rare) | `websocketAuth` utilities | `useTraceWebSocket.ts` |
| Public endpoint | `authenticatedFetch({ skipAuth: true })` | Health check |
| Login/Logout | Direct `fetch` | `authSlice.ts` |

## Migration Guide

### From plain `fetch` to `authenticatedFetch`

**Before:**
```typescript
const token = getAuthToken();
const response = await fetch("/api/v1/data", {
  headers: {
    Authorization: `Bearer ${token}`,
    "Content-Type": "application/json",
  },
  credentials: "include",
});

if (response.status === 401) {
  // Manual refresh logic...
}
```

**After:**
```typescript
const response = await authenticatedFetch("/api/v1/data", {
  headers: { "Content-Type": "application/json" },
  onAuthFailure: handleAuthFailure,
});
```

### Key Benefits

1. **Automatic token refresh** - No manual 401 handling
2. **Consistent auth headers** - Token always included
3. **Centralized logic** - Single point of maintenance
4. **Concurrent refresh protection** - Multiple 401s share one refresh

## Files NOT Using authenticatedFetch

These files intentionally use other patterns:

| File | Reason |
|------|--------|
| `authSlice.ts` | Login/logout sends credentials in body, not header |
| `mcpSlice.ts` | Calls external MCP server URLs (not our API) |
| Route loaders | Use custom `fetchJson` with `redirect()` for SSR |
| WebSocket hooks | Use token in URL query param for WS handshake |
| `UserMenuDropdown.tsx` | Logout sends refresh token in request body |
