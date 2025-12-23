/**
 * DevTools Slice
 *
 * Manages state for the Chrome DevTools-like debugging panel.
 * Features:
 * - Context-aware tabs (session/workflow/global)
 * - Persona-based smart default (open for admin/developer, collapsed for user)
 * - AI-powered layout suggestions
 * - Console filtering
 * - Panel resize and maximize
 *
 * Uses centralized storage utility for localStorage operations.
 */

import { createSlice, PayloadAction, createSelector } from "@reduxjs/toolkit";
import { storage } from "../../utils/storage";
import type { Persona } from "./personaSlice";

// =============================================================================
// Types
// =============================================================================

export type DevToolsTabId =
  | "console"
  | "agent-trace"
  | "execution-trace"
  | "network"
  | "state"
  | "problems"
  | "ai-insights"
  // OTEL Observability tabs
  | "traces"
  | "metrics"
  | "alerts"
  | "logs";

export type DevToolsContext = "session" | "workflow" | "global";

export type ConsoleFilterLevel = "all" | "info" | "warning" | "error";

export interface DevToolsState {
  /** Whether the panel is collapsed */
  collapsed: boolean;
  /** Panel height in pixels (150-600) */
  height: number;
  /** Whether the panel is maximized (takes full viewport) */
  maximized: boolean;
  /** Currently active tab */
  activeTab: DevToolsTabId;
  /** Detected context based on current route/view */
  detectedContext: DevToolsContext;
  /** ID of the session or workflow being debugged */
  contextEntityId: string | null;
  /** Console log filter level */
  consoleFilter: ConsoleFilterLevel;
  /** Whether AI insights features are enabled */
  aiInsightsEnabled: boolean;
  /** AI-suggested tab order (null if no suggestion) */
  aiSuggestedLayout: DevToolsTabId[] | null;
}

// =============================================================================
// Constants
// =============================================================================

const STORAGE_KEY_COLLAPSED = "studio-devtools-collapsed";
const STORAGE_KEY_HEIGHT = "studio-devtools-height";

const MIN_HEIGHT = 150;
const MAX_HEIGHT = 600;
const DEFAULT_HEIGHT = 250;

/** Tabs available in each context */
const TABS_BY_CONTEXT: Record<DevToolsContext, DevToolsTabId[]> = {
  global: [
    "console",
    "network",
    "state",
    "problems",
    "traces",
    "metrics",
    "alerts",
    "logs",
  ],
  session: [
    "console",
    "agent-trace",
    "network",
    "state",
    "problems",
    "traces",
    "metrics",
    "alerts",
    "logs",
  ],
  workflow: [
    "console",
    "execution-trace",
    "network",
    "state",
    "problems",
    "traces",
    "metrics",
    "alerts",
    "logs",
  ],
};

// =============================================================================
// Helpers
// =============================================================================

/**
 * Get default collapsed state based on persona.
 * Admin and developer personas get DevTools open by default.
 * User persona gets DevTools collapsed by default.
 */
export function getDefaultCollapsedFromPersona(persona: Persona): boolean {
  return persona === "user";
}

/**
 * Load collapsed state from localStorage.
 * Returns null if not set (persona-based default should be used).
 */
function getStoredCollapsed(): boolean | null {
  const stored = storage.get<boolean>(STORAGE_KEY_COLLAPSED);
  if (typeof stored === "boolean") {
    return stored;
  }
  return null;
}

/**
 * Load height from localStorage.
 */
function getStoredHeight(): number {
  const stored = storage.get<number>(STORAGE_KEY_HEIGHT);
  if (
    typeof stored === "number" &&
    stored >= MIN_HEIGHT &&
    stored <= MAX_HEIGHT
  ) {
    return stored;
  }
  return DEFAULT_HEIGHT;
}

/**
 * Get available tabs for a context, optionally including AI insights.
 */
function getAvailableTabs(
  context: DevToolsContext,
  aiInsightsEnabled: boolean,
): DevToolsTabId[] {
  const baseTabs = TABS_BY_CONTEXT[context];
  // AI insights only available in session/workflow context, not global
  if (aiInsightsEnabled && context !== "global") {
    return [...baseTabs, "ai-insights"];
  }
  return baseTabs;
}

/**
 * Check if a tab is available in a context.
 */
function isTabAvailable(
  tab: DevToolsTabId,
  context: DevToolsContext,
  aiInsightsEnabled: boolean,
): boolean {
  return getAvailableTabs(context, aiInsightsEnabled).includes(tab);
}

// =============================================================================
// Initial State
// =============================================================================

const initialState: DevToolsState = {
  collapsed: true, // Default for user persona; will be overridden by initializeFromPersona
  height: getStoredHeight(),
  maximized: false,
  activeTab: "console",
  detectedContext: "global",
  contextEntityId: null,
  consoleFilter: "all",
  aiInsightsEnabled: false,
  aiSuggestedLayout: null,
};

// =============================================================================
// Slice
// =============================================================================

export const devToolsSlice = createSlice({
  name: "devTools",
  initialState,
  reducers: {
    /**
     * Toggle DevTools panel visibility.
     */
    toggleDevTools: (state) => {
      state.collapsed = !state.collapsed;
      // Reset maximized when collapsing
      if (state.collapsed) {
        state.maximized = false;
      }
      // Persist to localStorage
      storage.set(STORAGE_KEY_COLLAPSED, state.collapsed);
    },

    /**
     * Set the active tab.
     * Expands the panel if collapsed.
     */
    setActiveTab: (state, action: PayloadAction<DevToolsTabId>) => {
      state.activeTab = action.payload;
      // Expand panel when changing tabs
      if (state.collapsed) {
        state.collapsed = false;
        storage.set(STORAGE_KEY_COLLAPSED, false);
      }
    },

    /**
     * Set the detected context based on current route/view.
     * Resets activeTab if current tab not available in new context.
     */
    setDetectedContext: (state, action: PayloadAction<DevToolsContext>) => {
      const newContext = action.payload;
      state.detectedContext = newContext;

      // Reset tab if not available in new context
      if (
        !isTabAvailable(state.activeTab, newContext, state.aiInsightsEnabled)
      ) {
        state.activeTab = "console";
      }
    },

    /**
     * Set the context entity ID (session or workflow ID).
     */
    setContextEntityId: (state, action: PayloadAction<string | null>) => {
      state.contextEntityId = action.payload;
    },

    /**
     * Set the console filter level.
     */
    setConsoleFilter: (state, action: PayloadAction<ConsoleFilterLevel>) => {
      state.consoleFilter = action.payload;
    },

    /**
     * Set the panel height.
     * Clamps to MIN_HEIGHT..MAX_HEIGHT range.
     */
    setHeight: (state, action: PayloadAction<number>) => {
      const height = Math.max(MIN_HEIGHT, Math.min(MAX_HEIGHT, action.payload));
      state.height = height;
      // Persist to localStorage
      storage.set(STORAGE_KEY_HEIGHT, height);
    },

    /**
     * Set maximized state.
     * Expands panel if maximizing.
     */
    setMaximized: (state, action: PayloadAction<boolean>) => {
      state.maximized = action.payload;
      // Expand panel when maximizing
      if (action.payload && state.collapsed) {
        state.collapsed = false;
        storage.set(STORAGE_KEY_COLLAPSED, false);
      }
    },

    /**
     * Enable or disable AI insights features.
     */
    setAiInsightsEnabled: (state, action: PayloadAction<boolean>) => {
      state.aiInsightsEnabled = action.payload;
      // Reset tab if AI insights disabled and currently on that tab
      if (!action.payload && state.activeTab === "ai-insights") {
        state.activeTab = "console";
      }
    },

    /**
     * Apply AI-suggested tab layout.
     */
    applyAILayout: (state, action: PayloadAction<DevToolsTabId[]>) => {
      state.aiSuggestedLayout = action.payload;
    },

    /**
     * Clear AI-suggested layout.
     */
    clearAILayout: (state) => {
      state.aiSuggestedLayout = null;
    },

    /**
     * Initialize collapsed state based on persona.
     * Called after persona is loaded from /api/v1/me.
     * Respects user override in localStorage.
     */
    initializeFromPersona: (state, action: PayloadAction<Persona>) => {
      const storedCollapsed = getStoredCollapsed();
      if (storedCollapsed !== null) {
        // User has explicitly set a preference
        state.collapsed = storedCollapsed;
      } else {
        // Use persona-based default
        state.collapsed = getDefaultCollapsedFromPersona(action.payload);
      }
    },
  },
});

// =============================================================================
// Actions
// =============================================================================

export const {
  toggleDevTools,
  setActiveTab,
  setDetectedContext,
  setContextEntityId,
  setConsoleFilter,
  setHeight,
  setMaximized,
  setAiInsightsEnabled,
  applyAILayout,
  clearAILayout,
  initializeFromPersona,
} = devToolsSlice.actions;

// =============================================================================
// Selectors
// =============================================================================

type DevToolsRootState = { devTools: DevToolsState };

export const selectDevToolsCollapsed = (state: DevToolsRootState) =>
  state.devTools.collapsed;

export const selectDevToolsMaximized = (state: DevToolsRootState) =>
  state.devTools.maximized;

export const selectDevToolsHeight = (state: DevToolsRootState) =>
  state.devTools.height;

// Alias for hooks
export const selectHeight = selectDevToolsHeight;

export const selectActiveTab = (state: DevToolsRootState) =>
  state.devTools.activeTab;

export const selectDetectedContext = (state: DevToolsRootState) =>
  state.devTools.detectedContext;

export const selectContextEntityId = (state: DevToolsRootState) =>
  state.devTools.contextEntityId;

export const selectConsoleFilter = (state: DevToolsRootState) =>
  state.devTools.consoleFilter;

export const selectAiInsightsEnabled = (state: DevToolsRootState) =>
  state.devTools.aiInsightsEnabled;

export const selectAISuggestedLayout = (state: DevToolsRootState) =>
  state.devTools.aiSuggestedLayout;

/**
 * Get available tabs based on current context and AI settings.
 * Memoized to prevent unnecessary re-renders.
 */
export const selectAvailableTabs = createSelector(
  [selectDetectedContext, selectAiInsightsEnabled],
  (context, aiInsightsEnabled): DevToolsTabId[] => {
    return getAvailableTabs(context, aiInsightsEnabled);
  },
);

export default devToolsSlice.reducer;
