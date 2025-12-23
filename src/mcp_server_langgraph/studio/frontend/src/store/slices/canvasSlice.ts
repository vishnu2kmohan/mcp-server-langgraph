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
  return stored ?? {};
};

const initialState: CanvasState = {
  panelSizes: defaultPanelSizes,
  sessionNavCollapsed: false,
  canvasCollapsed: false,
  activeNavItem: "chat",
  selectedArtifactId: null,
  preferences: defaultPreferences,
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
     */
    setPanelSizes(state, action: PayloadAction<CanvasPanelSizes>) {
      state.panelSizes = action.payload;
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
     */
    resetCanvas(state) {
      Object.assign(state, {
        panelSizes: defaultPanelSizes,
        sessionNavCollapsed: false,
        canvasCollapsed: false,
        activeNavItem: "chat",
        selectedArtifactId: null,
        preferences: defaultPreferences,
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

// =============================================================================
// Exports
// =============================================================================

export const {
  setPanelSizes,
  toggleSessionNav,
  setSessionNavCollapsed,
  toggleCanvas,
  setCanvasCollapsed,
  setActiveNavItem,
  setSelectedArtifactId,
  setPreferences,
  resetCanvas,
} = canvasSlice.actions;

export default canvasSlice.reducer;
