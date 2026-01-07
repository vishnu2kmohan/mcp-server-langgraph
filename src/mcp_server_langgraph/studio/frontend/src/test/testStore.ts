/**
 * Test Store Factory
 *
 * Provides a reusable Redux store factory for tests to reduce memory overhead
 * from creating multiple store instances. This consolidates store creation
 * patterns found across many test files.
 *
 * MEMORY OPTIMIZATION:
 * - Instead of creating a new store in every test, use createTestStore()
 * - Store instances are lightweight, but reducer imports and middleware add up
 * - This factory caches common configurations to reduce import overhead
 *
 * Usage:
 *   import { createTestStore, createMinimalStore } from '../test/testStore';
 *
 *   // Full store with all reducers
 *   const store = createTestStore({ preloadedState: { auth: { ... } } });
 *
 *   // Minimal store for simple tests
 *   const store = createMinimalStore(['auth', 'session']);
 */

import {
  configureStore,
  combineReducers,
  type Reducer,
} from "@reduxjs/toolkit";
import React, { type ReactNode } from "react";
import { Provider } from "react-redux";

// Import all reducers - these are cached at module level
import authReducer, { initialAuthState } from "../store/slices/authSlice";
import sessionReducer from "../store/slices/sessionSlice";
import canvasReducer from "../store/slices/canvasSlice";
import personaReducer from "../store/slices/personaSlice";
import backgroundAgentReducer from "../store/slices/backgroundAgentSlice";
import devToolsReducer from "../store/slices/devToolsSlice";
import workspaceReducer from "../store/slices/workspaceSlice";
import workflowReducer from "../store/slices/workflowSlice";
import alertReducer from "../store/slices/alertSlice";

// Import API slice
import { api } from "../api";

// =============================================================================
// Types
// =============================================================================

export type RootState = ReturnType<typeof fullRootReducer>;

export interface CreateTestStoreOptions {
  /** Preloaded state to initialize the store with */
  preloadedState?: Partial<RootState>;
  /** Whether to include API middleware (default: false for faster tests) */
  includeApiMiddleware?: boolean;
  /** Custom reducers to add/override */
  extraReducers?: Record<string, Reducer>;
}

export type ReducerKey =
  | "auth"
  | "session"
  | "canvas"
  | "persona"
  | "backgroundAgent"
  | "devTools"
  | "workspace"
  | "workflow"
  | "alert"
  | "api";

// =============================================================================
// Reducer Maps
// =============================================================================

/** All available reducers */
const reducerMap: Record<string, Reducer> = {
  auth: authReducer,
  session: sessionReducer,
  canvas: canvasReducer,
  persona: personaReducer,
  backgroundAgent: backgroundAgentReducer,
  devTools: devToolsReducer,
  workspace: workspaceReducer,
  workflow: workflowReducer,
  alert: alertReducer,
  [api.reducerPath]: api.reducer,
};

/** Full root reducer with all slices */
const fullRootReducer = combineReducers(reducerMap);

// =============================================================================
// Store Factory Functions
// =============================================================================

/**
 * Create a full test store with all reducers.
 * Use this for integration tests that need the complete store.
 *
 * @example
 * const store = createTestStore({
 *   preloadedState: {
 *     auth: { ...initialAuthState, isAuthenticated: true }
 *   }
 * });
 */
export function createTestStore(options: CreateTestStoreOptions = {}) {
  const {
    preloadedState,
    includeApiMiddleware = false,
    extraReducers,
  } = options;

  // Combine reducers with any extras
  const rootReducer = extraReducers
    ? combineReducers({ ...reducerMap, ...extraReducers })
    : fullRootReducer;

  return configureStore({
    reducer: rootReducer,
    preloadedState: preloadedState as RootState,
    middleware: (getDefaultMiddleware) => {
      const middleware = getDefaultMiddleware({
        serializableCheck: false,
        immutableCheck: false,
      });

      if (includeApiMiddleware) {
        return middleware.concat(api.middleware);
      }
      return middleware;
    },
  });
}

/**
 * Create a minimal test store with only specified reducers.
 * Use this for unit tests that only need a subset of state.
 *
 * This significantly reduces memory usage for tests that don't need
 * the full store.
 *
 * @example
 * const store = createMinimalStore(['auth', 'session'], {
 *   auth: { ...initialAuthState, isAuthenticated: true }
 * });
 */
export function createMinimalStore(
  reducerKeys: ReducerKey[],
  preloadedState?: Record<string, unknown>,
) {
  const selectedReducers: Record<string, Reducer> = {};

  for (const key of reducerKeys) {
    if (reducerMap[key]) {
      selectedReducers[key] = reducerMap[key];
    } else if (key === "api") {
      selectedReducers[api.reducerPath] = api.reducer;
    }
  }

  return configureStore({
    reducer: selectedReducers,
    preloadedState,
    middleware: (getDefaultMiddleware) =>
      getDefaultMiddleware({
        serializableCheck: false,
        immutableCheck: false,
      }),
  });
}

// =============================================================================
// Common Preloaded States
// =============================================================================

/**
 * Default WebSocket permissions for authenticated test users.
 * All permissions enabled for comprehensive test coverage.
 */
const testWebSocketPermissions = {
  notifications: true,
  alerts: true,
  audit: true,
  mcp_tasks: true,
  mcp_aggregated: true,
  connections_health: true,
  connections_realtime: true,
  heart_metrics: true,
  traces: true,
  cost_tracking: true,
  budget_alerts: true,
  agent_requests: true,
  ai_suggestions: true,
  orchestrator_status: true,
};

/**
 * Common authenticated user state for testing.
 * Reduces boilerplate in tests that need an authenticated user.
 *
 * Note: `isAuthenticated` is not a state field - use selectIsAuthenticated selector.
 * The auth state stores `user` and `tokens`, and authentication is derived from `user !== null`.
 */
export const authenticatedAuthState = {
  ...initialAuthState,
  isInitializing: false,
  user: {
    id: "test-user-id",
    username: "testuser",
    email: "test@example.com",
    name: "Test User",
    persona: "user",
    roles: ["user"],
    organizations: [],
    websocketPermissions: testWebSocketPermissions,
  },
  tokens: {
    accessToken: "test-access-token",
    refreshToken: "test-refresh-token",
    expiresAt: Date.now() + 3600000,
  },
};

/**
 * Admin user state for testing admin features.
 */
export const adminAuthState = {
  ...initialAuthState,
  isInitializing: false,
  user: {
    id: "admin-user-id",
    username: "adminuser",
    email: "admin@example.com",
    name: "Admin User",
    persona: "admin",
    roles: ["admin", "user"],
    organizations: [],
    websocketPermissions: testWebSocketPermissions,
  },
  tokens: {
    accessToken: "admin-test-access-token",
    refreshToken: "admin-test-refresh-token",
    expiresAt: Date.now() + 3600000,
  },
};

// Re-export the selector for convenience
export { selectIsAuthenticated } from "../store/slices/authSlice";

// =============================================================================
// Test Utilities
// =============================================================================

export type TestStore = ReturnType<typeof createTestStore>;
export type TestDispatch = TestStore["dispatch"];

/**
 * Get the dispatch function from a test store.
 * Useful for typing dispatch in tests.
 */
export function getTestDispatch(store: TestStore): TestDispatch {
  return store.dispatch;
}

/**
 * Reset a store to initial state by creating a new store.
 * Use this in beforeEach to ensure clean state.
 *
 * @example
 * let store: TestStore;
 * beforeEach(() => {
 *   store = resetStore(store);
 * });
 */
export function resetStore(
  _existingStore: TestStore,
  options: CreateTestStoreOptions = {},
): TestStore {
  // Simply create a new store - the old one will be garbage collected
  return createTestStore(options);
}

// =============================================================================
// React Test Wrappers
// =============================================================================

/**
 * Props for TestWrapper component
 */
export interface TestWrapperProps {
  children: ReactNode;
  /** Optional custom store (defaults to createTestStore()) */
  store?: TestStore;
  /** Optional preloaded state for the default store */
  preloadedState?: Partial<RootState>;
}

/**
 * Reusable test wrapper with Redux Provider.
 * Use this to wrap hooks that require Redux context.
 *
 * @example
 * // Basic usage with renderHook
 * import { TestWrapper } from '../test/testStore';
 *
 * const { result } = renderHook(() => useMyHook(), {
 *   wrapper: TestWrapper,
 * });
 *
 * @example
 * // With custom store
 * const store = createTestStore({ preloadedState: { auth: authenticatedAuthState } });
 * const wrapper = ({ children }) => <TestWrapper store={store}>{children}</TestWrapper>;
 * const { result } = renderHook(() => useMyHook(), { wrapper });
 */
export function TestWrapper({
  children,
  store,
  preloadedState,
}: TestWrapperProps): React.ReactElement {
  const testStore = store ?? createTestStore({ preloadedState });
  return React.createElement(Provider, { store: testStore }, children);
}

/**
 * Create a wrapper function for renderHook with optional store configuration.
 * This is useful when you need a custom store configuration.
 *
 * @example
 * const wrapper = createTestWrapper({ preloadedState: { auth: authenticatedAuthState } });
 * const { result } = renderHook(() => useMyHook(), { wrapper });
 */
export function createTestWrapper(
  options: CreateTestStoreOptions = {},
): ({ children }: { children: ReactNode }) => React.ReactElement {
  const store = createTestStore(options);
  return ({ children }: { children: ReactNode }) =>
    React.createElement(Provider, { store }, children);
}
