/**
 * Canvas Slice Tests
 *
 * Tests for the Studio Canvas state management.
 */
import { describe, it, expect, afterEach, vi } from "vitest";
import canvasReducer, {
  setPanelSizes,
  toggleSessionNav,
  setSessionNavCollapsed,
  toggleCanvas,
  setCanvasCollapsed,
  toggleFocusMode,
  setFocusModeEnabled,
  setActiveNavItem,
  setSelectedArtifactId,
  setPreferences,
  resetCanvas,
  setHasCustomLayout,
  setMaximizedPanelId,
  togglePanelMaximize,
  selectPanelSizes,
  selectSessionNavCollapsed,
  selectCanvasCollapsed,
  selectFocusModeEnabled,
  selectActiveNavItem,
  selectSelectedArtifactId,
  selectPreferences,
  selectHasCustomLayout,
  selectMaximizedPanelId,
  type CanvasState,
} from "./canvasSlice";

describe("canvasSlice", () => {
  afterEach(() => {
    vi.clearAllMocks();
  });

  const initialState: CanvasState = {
    panelSizes: {
      sessionNav: 20,
      conversation: 40,
      canvas: 40,
    },
    sessionNavCollapsed: false,
    canvasCollapsed: false,
    activeNavItem: "chat",
    selectedArtifactId: null,
    preferences: {
      showTimestamps: true,
      compactMode: false,
      showLineNumbers: true,
      codeTheme: "auto",
    },
    focusModeEnabled: false,
    hasCustomLayout: false,
    maximizedPanelId: null,
  };

  describe("reducers", () => {
    it("should handle initial state", () => {
      const result = canvasReducer(undefined, { type: "unknown" });
      expect(result.panelSizes).toEqual(initialState.panelSizes);
      expect(result.activeNavItem).toBe("chat");
    });

    it("should handle setPanelSizes", () => {
      const newSizes = { sessionNav: 25, conversation: 35, canvas: 40 };
      const result = canvasReducer(initialState, setPanelSizes(newSizes));
      expect(result.panelSizes).toEqual(newSizes);
    });

    it("should handle toggleSessionNav", () => {
      const result = canvasReducer(initialState, toggleSessionNav());
      expect(result.sessionNavCollapsed).toBe(true);

      const result2 = canvasReducer(result, toggleSessionNav());
      expect(result2.sessionNavCollapsed).toBe(false);
    });

    it("should handle setSessionNavCollapsed", () => {
      const result = canvasReducer(initialState, setSessionNavCollapsed(true));
      expect(result.sessionNavCollapsed).toBe(true);
    });

    it("should handle toggleCanvas", () => {
      const result = canvasReducer(initialState, toggleCanvas());
      expect(result.canvasCollapsed).toBe(true);

      const result2 = canvasReducer(result, toggleCanvas());
      expect(result2.canvasCollapsed).toBe(false);
    });

    it("should handle setCanvasCollapsed", () => {
      const result = canvasReducer(initialState, setCanvasCollapsed(true));
      expect(result.canvasCollapsed).toBe(true);
    });

    it("should handle toggleFocusMode", () => {
      const result = canvasReducer(initialState, toggleFocusMode());
      expect(result.focusModeEnabled).toBe(true);

      const result2 = canvasReducer(result, toggleFocusMode());
      expect(result2.focusModeEnabled).toBe(false);
    });

    it("should handle setFocusModeEnabled", () => {
      const result = canvasReducer(initialState, setFocusModeEnabled(true));
      expect(result.focusModeEnabled).toBe(true);

      const result2 = canvasReducer(result, setFocusModeEnabled(false));
      expect(result2.focusModeEnabled).toBe(false);
    });

    it("should handle setActiveNavItem", () => {
      const result = canvasReducer(initialState, setActiveNavItem("workflows"));
      expect(result.activeNavItem).toBe("workflows");
    });

    it("should handle setSelectedArtifactId", () => {
      const result = canvasReducer(
        initialState,
        setSelectedArtifactId("artifact-123"),
      );
      expect(result.selectedArtifactId).toBe("artifact-123");
    });

    it("should handle setPreferences", () => {
      const result = canvasReducer(
        initialState,
        setPreferences({ compactMode: true, showTimestamps: false }),
      );
      expect(result.preferences.compactMode).toBe(true);
      expect(result.preferences.showTimestamps).toBe(false);
      // Other preferences should remain unchanged
      expect(result.preferences.showLineNumbers).toBe(true);
    });

    it("should handle resetCanvas", () => {
      const modifiedState: CanvasState = {
        ...initialState,
        panelSizes: { sessionNav: 30, conversation: 30, canvas: 40 },
        sessionNavCollapsed: true,
        activeNavItem: "workflows",
        selectedArtifactId: "test-artifact",
      };

      const result = canvasReducer(modifiedState, resetCanvas());
      expect(result.panelSizes).toEqual(initialState.panelSizes);
      expect(result.sessionNavCollapsed).toBe(false);
      expect(result.activeNavItem).toBe("chat");
      expect(result.selectedArtifactId).toBeNull();
    });
  });

  describe("selectors", () => {
    const rootState = { canvas: initialState };

    it("should select panelSizes", () => {
      expect(selectPanelSizes(rootState)).toEqual(initialState.panelSizes);
    });

    it("should select sessionNavCollapsed", () => {
      expect(selectSessionNavCollapsed(rootState)).toBe(false);
    });

    it("should select canvasCollapsed", () => {
      expect(selectCanvasCollapsed(rootState)).toBe(false);
    });

    it("should select focusModeEnabled", () => {
      expect(selectFocusModeEnabled(rootState)).toBe(false);

      const focusModeState = {
        canvas: { ...initialState, focusModeEnabled: true },
      };
      expect(selectFocusModeEnabled(focusModeState)).toBe(true);
    });

    it("should select activeNavItem", () => {
      expect(selectActiveNavItem(rootState)).toBe("chat");
    });

    it("should select selectedArtifactId", () => {
      expect(selectSelectedArtifactId(rootState)).toBeNull();
    });

    it("should select preferences", () => {
      expect(selectPreferences(rootState)).toEqual(initialState.preferences);
    });
  });

  // Note: Persistence tests are skipped as localStorage mocking is complex
  // in vitest environments. The persistence logic is tested via integration tests.

  /**
   * Sprint 2.1: hasCustomLayout flag tests
   * Ensures persona presets are only applied for first-time users
   * and user's custom layouts are preserved on persona change.
   */
  describe("hasCustomLayout flag", () => {
    it("should have hasCustomLayout in initial state", () => {
      const result = canvasReducer(undefined, { type: "unknown" });
      expect(result.hasCustomLayout).toBeDefined();
      expect(typeof result.hasCustomLayout).toBe("boolean");
    });

    it("should default hasCustomLayout to false for new users", () => {
      const result = canvasReducer(undefined, { type: "unknown" });
      // New users without stored layout should have hasCustomLayout = false
      expect(result.hasCustomLayout).toBe(false);
    });

    it("should set hasCustomLayout to true when setPanelSizes is called", () => {
      const stateWithNoCustomLayout: CanvasState = {
        ...initialState,
        hasCustomLayout: false,
      };
      const newSizes = { sessionNav: 25, conversation: 35, canvas: 40 };
      const result = canvasReducer(
        stateWithNoCustomLayout,
        setPanelSizes(newSizes),
      );
      expect(result.hasCustomLayout).toBe(true);
    });

    it("should handle setHasCustomLayout action", () => {
      const result = canvasReducer(initialState, setHasCustomLayout(true));
      expect(result.hasCustomLayout).toBe(true);

      const result2 = canvasReducer(result, setHasCustomLayout(false));
      expect(result2.hasCustomLayout).toBe(false);
    });

    it("should reset hasCustomLayout to false on resetCanvas", () => {
      const modifiedState: CanvasState = {
        ...initialState,
        hasCustomLayout: true,
        panelSizes: { sessionNav: 30, conversation: 30, canvas: 40 },
      };

      const result = canvasReducer(modifiedState, resetCanvas());
      expect(result.hasCustomLayout).toBe(false);
    });

    it("should select hasCustomLayout from state", () => {
      const stateWithCustomLayout = {
        canvas: { ...initialState, hasCustomLayout: true },
      };
      expect(selectHasCustomLayout(stateWithCustomLayout)).toBe(true);

      const stateWithoutCustomLayout = {
        canvas: { ...initialState, hasCustomLayout: false },
      };
      expect(selectHasCustomLayout(stateWithoutCustomLayout)).toBe(false);
    });
  });

  /**
   * Sprint 4.1: Panel Zoom/Maximize tests
   * Allows users to maximize a single panel to full width.
   * Gated behind feature flag in StudioShellLayout.
   */
  describe("maximizedPanelId (Sprint 4.1)", () => {
    it("should have maximizedPanelId in initial state", () => {
      const result = canvasReducer(undefined, { type: "unknown" });
      expect(result.maximizedPanelId).toBeDefined();
      expect(result.maximizedPanelId).toBeNull();
    });

    it("should handle setMaximizedPanelId action", () => {
      const result = canvasReducer(initialState, setMaximizedPanelId("canvas"));
      expect(result.maximizedPanelId).toBe("canvas");
    });

    it("should handle setMaximizedPanelId with null to restore layout", () => {
      const maximizedState: CanvasState = {
        ...initialState,
        maximizedPanelId: "conversation",
      };
      const result = canvasReducer(maximizedState, setMaximizedPanelId(null));
      expect(result.maximizedPanelId).toBeNull();
    });

    it("should handle togglePanelMaximize action - maximize", () => {
      const result = canvasReducer(initialState, togglePanelMaximize("canvas"));
      expect(result.maximizedPanelId).toBe("canvas");
    });

    it("should handle togglePanelMaximize action - restore", () => {
      const maximizedState: CanvasState = {
        ...initialState,
        maximizedPanelId: "canvas",
      };
      const result = canvasReducer(
        maximizedState,
        togglePanelMaximize("canvas"),
      );
      expect(result.maximizedPanelId).toBeNull();
    });

    it("should handle togglePanelMaximize with different panel - switch", () => {
      const maximizedState: CanvasState = {
        ...initialState,
        maximizedPanelId: "canvas",
      };
      // Clicking a different panel while one is maximized should switch to that panel
      const result = canvasReducer(
        maximizedState,
        togglePanelMaximize("conversation"),
      );
      expect(result.maximizedPanelId).toBe("conversation");
    });

    it("should reset maximizedPanelId on resetCanvas", () => {
      const maximizedState: CanvasState = {
        ...initialState,
        maximizedPanelId: "canvas",
      };
      const result = canvasReducer(maximizedState, resetCanvas());
      expect(result.maximizedPanelId).toBeNull();
    });

    it("should select maximizedPanelId from state", () => {
      const stateWithMaximized = {
        canvas: { ...initialState, maximizedPanelId: "conversation" },
      };
      expect(selectMaximizedPanelId(stateWithMaximized)).toBe("conversation");

      const stateWithoutMaximized = {
        canvas: { ...initialState, maximizedPanelId: null },
      };
      expect(selectMaximizedPanelId(stateWithoutMaximized)).toBeNull();
    });
  });
});
