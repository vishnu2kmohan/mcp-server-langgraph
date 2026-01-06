/**
 * uiSlice Test Fixtures
 *
 * Shared utilities and fixtures for uiSlice test shards.
 * Provides type-safe factory functions for creating UI state in tests.
 *
 * Usage:
 * ```typescript
 * import { createTestUIState, createTestStore } from "./uiSlice.fixtures";
 *
 * const store = createTestStore({ sidebarOpen: false });
 * const state = createTestUIState({ theme: "dark" });
 * ```
 */

import { configureStore } from "@reduxjs/toolkit";
import uiReducer from "../uiSlice";

// =============================================================================
// TYPE DEFINITIONS
// =============================================================================

/**
 * UI notification structure
 */
export interface UINotification {
  id: string;
  type: "info" | "success" | "warning" | "error";
  message: string;
  timestamp: number;
}

/**
 * Theme options
 */
export type Theme = "light" | "dark" | "system";

/**
 * Active view options
 */
export type ActiveView =
  | "workflows"
  | "sessions"
  | "chat"
  | "cost"
  | "observability";

/**
 * Complete UI state interface (mirrors uiSlice.ts)
 */
export interface UIState {
  sidebarOpen: boolean;
  sidebarCollapsed: boolean;
  theme: Theme;
  isLoading: boolean;
  activeView: ActiveView;
  notifications: UINotification[];
  submitOnEnter: boolean;
}

// =============================================================================
// STATE FACTORIES
// =============================================================================

/**
 * Creates a complete UIState object with sensible defaults.
 * Use this to ensure type safety when providing UI state to tests.
 *
 * @param overrides - Partial UIState to override defaults
 * @returns Complete UIState object
 *
 * @example
 * ```typescript
 * // Default state
 * const state = createTestUIState();
 *
 * // With overrides
 * const darkState = createTestUIState({ theme: "dark", sidebarOpen: false });
 * ```
 */
export const createTestUIState = (
  overrides: Partial<UIState> = {},
): UIState => ({
  sidebarOpen: true,
  sidebarCollapsed: false,
  theme: "system",
  isLoading: false,
  activeView: "chat",
  notifications: [],
  submitOnEnter: true,
  ...overrides,
});

/**
 * Creates a notification object for testing
 *
 * @param overrides - Partial notification to override defaults
 * @returns Complete UINotification object
 */
let notificationIdCounter = 0;

export const createTestNotification = (
  overrides: Partial<UINotification> = {},
): UINotification => ({
  id: overrides.id ?? `notification-${++notificationIdCounter}`,
  type: "info",
  message: "Test notification",
  timestamp: Date.now(),
  ...overrides,
});

// =============================================================================
// STORE FACTORY
// =============================================================================

/**
 * Creates a Redux store with UI slice for testing.
 *
 * @param uiOverrides - Partial UIState to override defaults
 * @returns Configured Redux store with ui reducer
 *
 * @example
 * ```typescript
 * const store = createTestStore({ theme: "dark" });
 * expect(store.getState().ui.theme).toBe("dark");
 * ```
 */
export const createTestStore = (uiOverrides: Partial<UIState> = {}) => {
  return configureStore({
    reducer: {
      ui: uiReducer,
    },
    preloadedState: {
      ui: createTestUIState(uiOverrides),
    },
  });
};

/**
 * Creates preloaded state object for stores that include the ui slice.
 * Useful when configuring stores with multiple reducers.
 *
 * @param uiOverrides - Partial UIState to override defaults
 * @returns Object with ui property containing complete UIState
 *
 * @example
 * ```typescript
 * const store = configureStore({
 *   reducer: { session: sessionReducer, ui: uiReducer },
 *   preloadedState: {
 *     session: { ... },
 *     ...createUIPreloadedState({ submitOnEnter: false }),
 *   },
 * });
 * ```
 */
export const createUIPreloadedState = (uiOverrides: Partial<UIState> = {}) => ({
  ui: createTestUIState(uiOverrides),
});

// =============================================================================
// COMMON TEST SCENARIOS
// =============================================================================

/**
 * Default test UI state - sidebar open, light theme, not loading
 */
export const defaultUIState = createTestUIState();

/**
 * Dark mode test state
 */
export const darkModeUIState = createTestUIState({ theme: "dark" });

/**
 * Loading state for testing spinners/overlays
 */
export const loadingUIState = createTestUIState({ isLoading: true });

/**
 * Collapsed sidebar state (desktop)
 */
export const collapsedSidebarUIState = createTestUIState({
  sidebarCollapsed: true,
});

/**
 * Mobile-like state with sidebar closed
 */
export const mobileSidebarUIState = createTestUIState({
  sidebarOpen: false,
  sidebarCollapsed: false,
});

/**
 * State with Ctrl+Enter to submit (alternative keyboard mode)
 */
export const ctrlEnterSubmitUIState = createTestUIState({
  submitOnEnter: false,
});

/**
 * State with notifications for testing notification display
 */
export const withNotificationsUIState = createTestUIState({
  notifications: [
    createTestNotification({ type: "info", message: "Info message" }),
    createTestNotification({ type: "success", message: "Success message" }),
    createTestNotification({ type: "warning", message: "Warning message" }),
    createTestNotification({ type: "error", message: "Error message" }),
  ],
});
