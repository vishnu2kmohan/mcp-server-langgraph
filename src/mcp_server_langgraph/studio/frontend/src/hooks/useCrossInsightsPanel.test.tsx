/**
 * useCrossInsightsPanel Hook Tests
 *
 * TDD tests for the CrossInsightsPanel state management hook.
 * Tests are written FIRST before implementation (RED phase).
 *
 * The hook encapsulates:
 * - Dismissed state management
 * - localStorage persistence (configurable via feature flag)
 * - Keyboard shortcut handling (Cmd+I / Ctrl+I)
 * - Integration with batch composite analysis
 */
import { describe, it, expect, vi, beforeEach, afterEach } from "vitest";
import { renderHook, act, waitFor, cleanup } from "@testing-library/react";
import { Provider } from "react-redux";
import { configureStore } from "@reduxjs/toolkit";
import type { ReactNode } from "react";
import sessionReducer from "../store/slices/sessionSlice";
import personaReducer from "../store/slices/personaSlice";

// Mock feature flag hook
const mockUseFeatureFlag = vi.fn();
vi.mock("../contexts/FeatureFlagContext", () => ({
  useFeatureFlag: (flag: string) => mockUseFeatureFlag(flag),
}));

// Mock useBatchCompositeAnalysis
const mockBatchAnalysis = {
  personaResult: null,
  disclosureResult: null,
  crossInsights: [],
  confidence: 0,
  isLoading: false,
  error: null,
  refetch: vi.fn(),
};
vi.mock("./useBatchCompositeAnalysis", () => ({
  useBatchCompositeAnalysis: () => mockBatchAnalysis,
}));

// Import hook after mocks
import { useCrossInsightsPanel } from "./useCrossInsightsPanel";

// Storage key constant (should match implementation)
const STORAGE_KEY = "studio-cross-insights-dismissed";

// Create test store
const createTestStore = () => {
  return configureStore({
    reducer: {
      session: sessionReducer,
      persona: personaReducer,
    },
    preloadedState: {
      session: {
        sessions: [],
        currentSessionId: "test-session-1", // lang-graph: legacy session shape
        isLoading: false,
        error: null,
      },
      persona: {
        persona: "user",
        username: "testuser",
        email: "test@example.com",
        permissions: [],
        isPersonaLoading: false,
      },
    } as Record<string, unknown>,
  });
};

// Wrapper for renderHook
const createWrapper = (store: ReturnType<typeof createTestStore>) => {
  return ({ children }: { children: ReactNode }) => (
    <Provider store={store}>{children}</Provider>
  );
};

describe("useCrossInsightsPanel", () => {
  beforeEach(() => {
    vi.clearAllMocks();
    localStorage.clear();
    // Default feature flags
    mockUseFeatureFlag.mockImplementation((flag: string) => {
      if (flag === "batch_composite_analysis") return true;
      return false;
    });
  });

  afterEach(() => {
    cleanup();
    vi.restoreAllMocks();
    localStorage.clear();
  });

  describe("Initial State", () => {
    it("returns dismissed as false by default when localStorage is empty", () => {
      const store = createTestStore();
      const { result } = renderHook(() => useCrossInsightsPanel(), {
        wrapper: createWrapper(store),
      });

      expect(result.current.dismissed).toBe(false);
    });

    it("reads initial dismissed state from localStorage", () => {
      localStorage.setItem(STORAGE_KEY, "true");
      const store = createTestStore();
      const { result } = renderHook(() => useCrossInsightsPanel(), {
        wrapper: createWrapper(store),
      });

      expect(result.current.dismissed).toBe(true);
    });

    it("ignores localStorage when session-based dismissal is enabled", () => {
      localStorage.setItem(STORAGE_KEY, "true");
      mockUseFeatureFlag.mockImplementation((flag: string) => {
        if (flag === "insights_session_dismissal") return true;
        if (flag === "batch_composite_analysis") return true;
        return false;
      });

      const store = createTestStore();
      const { result } = renderHook(() => useCrossInsightsPanel(), {
        wrapper: createWrapper(store),
      });

      // Should be false even though localStorage has true
      expect(result.current.dismissed).toBe(false);
    });

    it("handles invalid JSON in localStorage gracefully", () => {
      localStorage.setItem(STORAGE_KEY, "invalid-json");
      const store = createTestStore();
      const { result } = renderHook(() => useCrossInsightsPanel(), {
        wrapper: createWrapper(store),
      });

      // Should default to false on parse error
      expect(result.current.dismissed).toBe(false);
    });
  });

  describe("State Management", () => {
    it("provides setDismissed function to update state", () => {
      const store = createTestStore();
      const { result } = renderHook(() => useCrossInsightsPanel(), {
        wrapper: createWrapper(store),
      });

      expect(typeof result.current.setDismissed).toBe("function");
    });

    it("updates dismissed state when setDismissed is called", () => {
      const store = createTestStore();
      const { result } = renderHook(() => useCrossInsightsPanel(), {
        wrapper: createWrapper(store),
      });

      act(() => {
        result.current.setDismissed(true);
      });

      expect(result.current.dismissed).toBe(true);
    });

    it("provides toggle function to toggle dismissed state", () => {
      const store = createTestStore();
      const { result } = renderHook(() => useCrossInsightsPanel(), {
        wrapper: createWrapper(store),
      });

      expect(typeof result.current.toggle).toBe("function");

      act(() => {
        result.current.toggle();
      });

      expect(result.current.dismissed).toBe(true);

      act(() => {
        result.current.toggle();
      });

      expect(result.current.dismissed).toBe(false);
    });
  });

  describe("localStorage Persistence", () => {
    it("persists dismissed state to localStorage when changed", async () => {
      const store = createTestStore();
      const { result } = renderHook(() => useCrossInsightsPanel(), {
        wrapper: createWrapper(store),
      });

      act(() => {
        result.current.setDismissed(true);
      });

      await waitFor(() => {
        expect(localStorage.getItem(STORAGE_KEY)).toBe("true");
      });
    });

    it("does not persist to localStorage when session-based dismissal is enabled", async () => {
      mockUseFeatureFlag.mockImplementation((flag: string) => {
        if (flag === "insights_session_dismissal") return true;
        if (flag === "batch_composite_analysis") return true;
        return false;
      });

      const store = createTestStore();
      const { result } = renderHook(() => useCrossInsightsPanel(), {
        wrapper: createWrapper(store),
      });

      act(() => {
        result.current.setDismissed(true);
      });

      // Wait a bit to ensure no async localStorage write
      await act(async () => {
        await new Promise((r) => setTimeout(r, 50));
      });

      // Should NOT be in localStorage
      expect(localStorage.getItem(STORAGE_KEY)).not.toBe("true");
    });
  });

  describe("Keyboard Shortcut Handling", () => {
    it("registers keyboard event listener on mount", () => {
      const addEventListenerSpy = vi.spyOn(document, "addEventListener");
      const store = createTestStore();

      renderHook(() => useCrossInsightsPanel(), {
        wrapper: createWrapper(store),
      });

      expect(addEventListenerSpy).toHaveBeenCalledWith(
        "keydown",
        expect.any(Function),
      );
    });

    it("removes keyboard event listener on unmount", () => {
      const removeEventListenerSpy = vi.spyOn(document, "removeEventListener");
      const store = createTestStore();

      const { unmount } = renderHook(() => useCrossInsightsPanel(), {
        wrapper: createWrapper(store),
      });

      unmount();

      expect(removeEventListenerSpy).toHaveBeenCalledWith(
        "keydown",
        expect.any(Function),
      );
    });

    it("toggles dismissed state when Cmd+I is pressed", async () => {
      const store = createTestStore();
      const { result } = renderHook(() => useCrossInsightsPanel(), {
        wrapper: createWrapper(store),
      });

      expect(result.current.dismissed).toBe(false);

      await act(async () => {
        const event = new KeyboardEvent("keydown", {
          key: "i",
          metaKey: true,
          bubbles: true,
        });
        document.dispatchEvent(event);
      });

      expect(result.current.dismissed).toBe(true);
    });

    it("toggles dismissed state when Ctrl+I is pressed", async () => {
      const store = createTestStore();
      const { result } = renderHook(() => useCrossInsightsPanel(), {
        wrapper: createWrapper(store),
      });

      expect(result.current.dismissed).toBe(false);

      await act(async () => {
        const event = new KeyboardEvent("keydown", {
          key: "i",
          ctrlKey: true,
          bubbles: true,
        });
        document.dispatchEvent(event);
      });

      expect(result.current.dismissed).toBe(true);
    });

    it("does not toggle when I is pressed without modifier", async () => {
      const store = createTestStore();
      const { result } = renderHook(() => useCrossInsightsPanel(), {
        wrapper: createWrapper(store),
      });

      expect(result.current.dismissed).toBe(false);

      await act(async () => {
        const event = new KeyboardEvent("keydown", {
          key: "i",
          bubbles: true,
        });
        document.dispatchEvent(event);
      });

      // Should remain unchanged
      expect(result.current.dismissed).toBe(false);
    });

    it("calls preventDefault when keyboard shortcut is triggered", async () => {
      const store = createTestStore();
      renderHook(() => useCrossInsightsPanel(), {
        wrapper: createWrapper(store),
      });

      let defaultPrevented = false;
      await act(async () => {
        const event = new KeyboardEvent("keydown", {
          key: "i",
          metaKey: true,
          bubbles: true,
          cancelable: true,
        });
        event.preventDefault = () => {
          defaultPrevented = true;
        };
        document.dispatchEvent(event);
      });

      expect(defaultPrevented).toBe(true);
    });
  });

  describe("Batch Analysis Integration", () => {
    it("returns cross-insights from batch analysis", () => {
      mockBatchAnalysis.crossInsights = ["Insight 1", "Insight 2"];
      mockBatchAnalysis.confidence = 0.85;

      const store = createTestStore();
      const { result } = renderHook(() => useCrossInsightsPanel(), {
        wrapper: createWrapper(store),
      });

      expect(result.current.crossInsights).toEqual(["Insight 1", "Insight 2"]);
      expect(result.current.confidence).toBe(0.85);
    });

    it("returns loading state from batch analysis", () => {
      mockBatchAnalysis.isLoading = true;

      const store = createTestStore();
      const { result } = renderHook(() => useCrossInsightsPanel(), {
        wrapper: createWrapper(store),
      });

      expect(result.current.isLoading).toBe(true);
    });

    it("returns persona and disclosure results from batch analysis", () => {
      mockBatchAnalysis.personaResult = { detected: "developer" };
      mockBatchAnalysis.disclosureResult = { level: "advanced" };

      const store = createTestStore();
      const { result } = renderHook(() => useCrossInsightsPanel(), {
        wrapper: createWrapper(store),
      });

      expect(result.current.personaResult).toEqual({ detected: "developer" });
      expect(result.current.disclosureResult).toEqual({ level: "advanced" });
    });
  });

  describe("Feature Flag Awareness", () => {
    it("exposes sessionDismissalEnabled flag state", () => {
      mockUseFeatureFlag.mockImplementation((flag: string) => {
        if (flag === "insights_session_dismissal") return true;
        if (flag === "batch_composite_analysis") return true;
        return false;
      });

      const store = createTestStore();
      const { result } = renderHook(() => useCrossInsightsPanel(), {
        wrapper: createWrapper(store),
      });

      expect(result.current.sessionDismissalEnabled).toBe(true);
    });

    it("exposes batchAnalysisEnabled flag state", () => {
      mockUseFeatureFlag.mockImplementation((flag: string) => {
        if (flag === "batch_composite_analysis") return true;
        return false;
      });

      const store = createTestStore();
      const { result } = renderHook(() => useCrossInsightsPanel(), {
        wrapper: createWrapper(store),
      });

      expect(result.current.batchAnalysisEnabled).toBe(true);
    });
  });

  describe("Visibility Computation", () => {
    it("returns shouldShow as false when dismissed", () => {
      const store = createTestStore();
      const { result } = renderHook(() => useCrossInsightsPanel(), {
        wrapper: createWrapper(store),
      });

      act(() => {
        result.current.setDismissed(true);
      });

      expect(result.current.shouldShow).toBe(false);
    });

    it("returns shouldShow as true when not dismissed and has insights", () => {
      mockBatchAnalysis.crossInsights = ["Insight 1"];

      const store = createTestStore();
      const { result } = renderHook(() => useCrossInsightsPanel(), {
        wrapper: createWrapper(store),
      });

      expect(result.current.shouldShow).toBe(true);
    });

    it("returns shouldShow as false when not dismissed but no insights", () => {
      mockBatchAnalysis.crossInsights = [];

      const store = createTestStore();
      const { result } = renderHook(() => useCrossInsightsPanel(), {
        wrapper: createWrapper(store),
      });

      expect(result.current.shouldShow).toBe(false);
    });
  });
});
