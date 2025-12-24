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
  selectPanelSizes,
  selectSessionNavCollapsed,
  selectCanvasCollapsed,
  selectFocusModeEnabled,
  selectActiveNavItem,
  selectSelectedArtifactId,
  selectPreferences,
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
});
