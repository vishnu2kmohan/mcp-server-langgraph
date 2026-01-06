/**
 * Canvas Slice - Phase 1
 *
 * State management for the Studio Canvas shell.
 * Completely independent from workspaceSlice - no bridging.
 *
 * Manages:
 * - Panel sizes (resizable panels percentages)
 * - Panel visibility (collapsed states)
 * - User preferences for Canvas UI
 */
import { createSlice, type PayloadAction } from "@reduxjs/toolkit";
import { storage } from "../../utils/storage";

// =============================================================================
// Types
// =============================================================================

export interface CanvasPanelSizes {
  /** SessionNav panel width percentage (default: 20%) */
  sessionNav: number;
  /** Conversation panel width percentage (default: 40%) */
  conversation: number;
  /** Canvas panel width percentage (default: 40%) */
  canvas: number;
}

export interface CanvasPreferences {
  /** Show timestamps in messages */
  showTimestamps: boolean;
  /** Compact mode for message display */
  compactMode: boolean;
  /** Show line numbers in code artifacts */
  showLineNumbers: boolean;
  /** Theme preference for code artifacts */
  codeTheme: "light" | "dark" | "auto";
}

/** Valid panel IDs that can be maximized */
export type MaximizablePanelId =
  | "session-nav"
  | "conversation"
  | "canvas"
  | null;

export interface CanvasState {
  /** Panel size percentages for react-resizable-panels */
  panelSizes: CanvasPanelSizes;
  /** Whether the session nav panel is collapsed */
  sessionNavCollapsed: boolean;
  /** Whether the canvas panel is collapsed */
  canvasCollapsed: boolean;
  /** Active navigation item in ActivityBar */
  activeNavItem: string;
  /** Currently selected artifact ID (if any) */
  selectedArtifactId: string | null;
  /** User preferences */
  preferences: CanvasPreferences;
  /** Focus/Zen mode: Hide TopBar, StatusBar, ActivityBar for distraction-free experience */
  focusModeEnabled: boolean;
  /**
   * Whether the user has customized their layout.
   * Sprint 2.1: Used to determine if persona presets should be applied.
   * - false: First-time user, apply persona-specific preset
   * - true: User has customized layout, preserve their settings
   */
  hasCustomLayout: boolean;
  /**
   * Sprint 4.1: ID of the panel currently maximized to full width.
   * - null: No panel maximized, normal layout
   * - "session-nav" | "conversation" | "canvas": That panel fills the main area
   */
  maximizedPanelId: MaximizablePanelId;
}

// =============================================================================
// Initial State
// =============================================================================

// Add canvas storage key to STORAGE_KEYS pattern (uses studio- prefix automatically)
const CANVAS_STORAGE_KEY = "canvas-state";

const defaultPanelSizes: CanvasPanelSizes = {
  sessionNav: 20,
  conversation: 40,
  canvas: 40,
};

const defaultPreferences: CanvasPreferences = {
  showTimestamps: true,
  compactMode: false,
  showLineNumbers: true,
  codeTheme: "auto",
};

const loadFromStorage = (): Partial<CanvasState> => {
  const stored = storage.get<Partial<CanvasState>>(CANVAS_STORAGE_KEY);
  if (!stored) {
    // First-time user - no custom layout yet
    return { hasCustomLayout: false };
  }
  // If we have stored panel sizes, user has customized their layout
  if (stored.panelSizes) {
    return { ...stored, hasCustomLayout: true };
  }
  return { ...stored, hasCustomLayout: stored.hasCustomLayout ?? false };
};

const initialState: CanvasState = {
  panelSizes: defaultPanelSizes,
  sessionNavCollapsed: false,
  canvasCollapsed: false,
  activeNavItem: "chat",
  selectedArtifactId: null,
  preferences: defaultPreferences,
  focusModeEnabled: false,
  hasCustomLayout: false,
  maximizedPanelId: null,
  ...loadFromStorage(),
};

// =============================================================================
// Slice
// =============================================================================

const canvasSlice = createSlice({
  name: "canvas",
  initialState,
  reducers: {
    /**
     * Set panel sizes (from react-resizable-panels onLayout)
     * Also marks the layout as customized by the user.
     */
    setPanelSizes(state, action: PayloadAction<CanvasPanelSizes>) {
      state.panelSizes = action.payload;
      state.hasCustomLayout = true;
      persistState(state);
    },

    /**
     * Toggle session nav collapsed state
     */
    toggleSessionNav(state) {
      state.sessionNavCollapsed = !state.sessionNavCollapsed;
      persistState(state);
    },

    /**
     * Set session nav collapsed state
     */
    setSessionNavCollapsed(state, action: PayloadAction<boolean>) {
      state.sessionNavCollapsed = action.payload;
      persistState(state);
    },

    /**
     * Toggle canvas panel collapsed state
     */
    toggleCanvas(state) {
      state.canvasCollapsed = !state.canvasCollapsed;
      persistState(state);
    },

    /**
     * Set canvas collapsed state
     */
    setCanvasCollapsed(state, action: PayloadAction<boolean>) {
      state.canvasCollapsed = action.payload;
      persistState(state);
    },

    /**
     * Toggle focus/zen mode (hides TopBar, StatusBar, ActivityBar)
     */
    toggleFocusMode(state) {
      state.focusModeEnabled = !state.focusModeEnabled;
      persistState(state);
    },

    /**
     * Set focus mode state
     */
    setFocusModeEnabled(state, action: PayloadAction<boolean>) {
      state.focusModeEnabled = action.payload;
      persistState(state);
    },

    /**
     * Set hasCustomLayout flag
     * Sprint 2.1: Used to track if user has customized their layout.
     */
    setHasCustomLayout(state, action: PayloadAction<boolean>) {
      state.hasCustomLayout = action.payload;
      persistState(state);
    },

    /**
     * Sprint 4.1: Set the maximized panel ID
     * - Set to a panel ID to maximize that panel
     * - Set to null to restore normal layout
     */
    setMaximizedPanelId(state, action: PayloadAction<MaximizablePanelId>) {
      state.maximizedPanelId = action.payload;
      // Note: Not persisted - maximize state resets on page reload
    },

    /**
     * Sprint 4.1: Toggle panel maximize state
     * - If no panel maximized: maximize the specified panel
     * - If same panel already maximized: restore normal layout
     * - If different panel maximized: switch to the specified panel
     */
    togglePanelMaximize(state, action: PayloadAction<string>) {
      const panelId = action.payload as MaximizablePanelId;
      if (state.maximizedPanelId === panelId) {
        // Same panel - restore normal layout
        state.maximizedPanelId = null;
      } else {
        // Different panel or none - maximize the specified panel
        state.maximizedPanelId = panelId;
      }
      // Note: Not persisted - maximize state resets on page reload
    },

    /**
     * Set active navigation item in ActivityBar
     */
    setActiveNavItem(state, action: PayloadAction<string>) {
      state.activeNavItem = action.payload;
    },

    /**
     * Set selected artifact ID
     */
    setSelectedArtifactId(state, action: PayloadAction<string | null>) {
      state.selectedArtifactId = action.payload;
    },

    /**
     * Update user preferences
     */
    setPreferences(state, action: PayloadAction<Partial<CanvasPreferences>>) {
      state.preferences = { ...state.preferences, ...action.payload };
      persistState(state);
    },

    /**
     * Reset to default state
     * Sprint 2.1: Also resets hasCustomLayout so persona presets can be applied again.
     * Sprint 4.1: Also resets maximizedPanelId.
     */
    resetCanvas(state) {
      Object.assign(state, {
        panelSizes: defaultPanelSizes,
        sessionNavCollapsed: false,
        canvasCollapsed: false,
        activeNavItem: "chat",
        selectedArtifactId: null,
        preferences: defaultPreferences,
        hasCustomLayout: false,
        maximizedPanelId: null,
      });
      storage.remove(CANVAS_STORAGE_KEY);
    },
  },
});

// =============================================================================
// Persistence Helper
// =============================================================================

function persistState(state: CanvasState): void {
  const toStore = {
    panelSizes: state.panelSizes,
    sessionNavCollapsed: state.sessionNavCollapsed,
    canvasCollapsed: state.canvasCollapsed,
    preferences: state.preferences,
    focusModeEnabled: state.focusModeEnabled,
    hasCustomLayout: state.hasCustomLayout,
  };
  storage.set(CANVAS_STORAGE_KEY, toStore);
}

// =============================================================================
// Selectors
// =============================================================================
// Note: Selectors use a generic state type to avoid circular dependencies
// with the main store. The store's RootState will include { canvas: CanvasState }

type StateWithCanvas = { canvas: CanvasState };

export const selectPanelSizes = (state: StateWithCanvas) =>
  state.canvas.panelSizes;
export const selectSessionNavCollapsed = (state: StateWithCanvas) =>
  state.canvas.sessionNavCollapsed;
export const selectCanvasCollapsed = (state: StateWithCanvas) =>
  state.canvas.canvasCollapsed;
export const selectActiveNavItem = (state: StateWithCanvas) =>
  state.canvas.activeNavItem;
export const selectSelectedArtifactId = (state: StateWithCanvas) =>
  state.canvas.selectedArtifactId;
export const selectPreferences = (state: StateWithCanvas) =>
  state.canvas.preferences;
export const selectFocusModeEnabled = (state: StateWithCanvas) =>
  state.canvas.focusModeEnabled;
export const selectHasCustomLayout = (state: StateWithCanvas) =>
  state.canvas.hasCustomLayout;
export const selectMaximizedPanelId = (state: StateWithCanvas) =>
  state.canvas.maximizedPanelId;

// =============================================================================
// Exports
// =============================================================================

export const {
  setPanelSizes,
  toggleSessionNav,
  setSessionNavCollapsed,
  toggleCanvas,
  setCanvasCollapsed,
  toggleFocusMode,
  setFocusModeEnabled,
  setHasCustomLayout,
  setMaximizedPanelId,
  togglePanelMaximize,
  setActiveNavItem,
  setSelectedArtifactId,
  setPreferences,
  resetCanvas,
} = canvasSlice.actions;

/**
 * Alias for resetCanvas - semantic name for "Reset to Persona Defaults" button.
 * Sprint 1.2: Used in SettingsPage to allow users to reset their layout.
 */
export const resetToDefaults = canvasSlice.actions.resetCanvas;

export default canvasSlice.reducer;
