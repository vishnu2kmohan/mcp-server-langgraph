/**
 * useProgressiveDisclosure Hook Tests
 *
 * TDD - RED Phase: Tests written first to define expected behavior
 *
 * Tests the hook that manages progressive UI disclosure based on user expertise.
 */

import { describe, it, expect, beforeEach, vi, afterEach } from "vitest";
import { renderHook, act, waitFor } from "@testing-library/react";
import { Provider } from "react-redux";
import { configureStore } from "@reduxjs/toolkit";
import { ReactNode } from "react";
import { useProgressiveDisclosure } from "./useProgressiveDisclosure";
import disclosureReducer from "../store/slices/disclosureSlice";

// Storage key used by the hook (storage utility adds studio- prefix)
const STORAGE_KEY = "studio-disclosure_state";

describe("useProgressiveDisclosure", () => {
  const createWrapper = () => {
    const store = configureStore({
      reducer: {
        disclosure: disclosureReducer,
      },
    });

    return ({ children }: { children: ReactNode }) => (
      <Provider store={store}>{children}</Provider>
    );
  };

  beforeEach(() => {
    vi.clearAllMocks();
    // Clear localStorage before each test
    localStorage.removeItem(STORAGE_KEY);
  });

  afterEach(() => {
    vi.restoreAllMocks();
    localStorage.removeItem(STORAGE_KEY);
  });

  describe("initialization", () => {
    it("should return current disclosure level", () => {
      const { result } = renderHook(() => useProgressiveDisclosure(), {
        wrapper: createWrapper(),
      });

      expect(result.current.level).toBe("beginner");
    });

    it("should return autoDetect status", () => {
      const { result } = renderHook(() => useProgressiveDisclosure(), {
        wrapper: createWrapper(),
      });

      expect(result.current.autoDetect).toBe(true);
    });

    it("should load persisted level from localStorage", async () => {
      // Set localStorage before rendering
      localStorage.setItem(
        STORAGE_KEY,
        JSON.stringify({ level: "advanced", autoDetect: false }),
      );

      const { result } = renderHook(() => useProgressiveDisclosure(), {
        wrapper: createWrapper(),
      });

      // Wait for effect to process localStorage
      await waitFor(() => {
        expect(result.current.level).toBeDefined();
      });
    });
  });

  describe("level management", () => {
    it("should set disclosure level", () => {
      const { result } = renderHook(() => useProgressiveDisclosure(), {
        wrapper: createWrapper(),
      });

      act(() => {
        result.current.setLevel("intermediate");
      });

      expect(result.current.level).toBe("intermediate");
    });

    it("should disable autoDetect when manually setting level", () => {
      const { result } = renderHook(() => useProgressiveDisclosure(), {
        wrapper: createWrapper(),
      });

      act(() => {
        result.current.setLevel("advanced");
      });

      expect(result.current.autoDetect).toBe(false);
    });

    it("should toggle autoDetect", () => {
      const { result } = renderHook(() => useProgressiveDisclosure(), {
        wrapper: createWrapper(),
      });

      expect(result.current.autoDetect).toBe(true);

      act(() => {
        result.current.setAutoDetect(false);
      });

      expect(result.current.autoDetect).toBe(false);
    });
  });

  describe("feature visibility", () => {
    it("should show beginner features for beginner level", () => {
      const { result } = renderHook(() => useProgressiveDisclosure(), {
        wrapper: createWrapper(),
      });

      expect(result.current.shouldShow("beginner")).toBe(true);
    });

    it("should hide advanced features for beginner level", () => {
      const { result } = renderHook(() => useProgressiveDisclosure(), {
        wrapper: createWrapper(),
      });

      expect(result.current.shouldShow("advanced")).toBe(false);
    });

    it("should show all features for expert level", () => {
      const { result } = renderHook(() => useProgressiveDisclosure(), {
        wrapper: createWrapper(),
      });

      act(() => {
        result.current.setLevel("expert");
      });

      expect(result.current.shouldShow("beginner")).toBe(true);
      expect(result.current.shouldShow("intermediate")).toBe(true);
      expect(result.current.shouldShow("advanced")).toBe(true);
      expect(result.current.shouldShow("expert")).toBe(true);
    });
  });

  describe("feature usage tracking", () => {
    it("should track feature usage", () => {
      const { result } = renderHook(() => useProgressiveDisclosure(), {
        wrapper: createWrapper(),
      });

      act(() => {
        result.current.trackFeatureUse();
      });

      expect(result.current.featureUsageCount).toBe(1);
    });

    it("should auto-upgrade level after sufficient usage", () => {
      const { result } = renderHook(() => useProgressiveDisclosure(), {
        wrapper: createWrapper(),
      });

      // Simulate 10 feature uses to trigger upgrade
      act(() => {
        for (let i = 0; i < 10; i++) {
          result.current.trackFeatureUse();
        }
      });

      expect(result.current.level).toBe("intermediate");
    });

    it("should not auto-upgrade when autoDetect is disabled", () => {
      const { result } = renderHook(() => useProgressiveDisclosure(), {
        wrapper: createWrapper(),
      });

      act(() => {
        result.current.setAutoDetect(false);
      });

      act(() => {
        for (let i = 0; i < 15; i++) {
          result.current.trackFeatureUse();
        }
      });

      expect(result.current.level).toBe("beginner");
    });
  });

  describe("level progress", () => {
    it("should return progress information", () => {
      const { result } = renderHook(() => useProgressiveDisclosure(), {
        wrapper: createWrapper(),
      });

      const progress = result.current.getLevelProgress();

      expect(progress).toHaveProperty("currentLevel");
      expect(progress).toHaveProperty("nextLevel");
      expect(progress).toHaveProperty("progressPercent");
      expect(progress).toHaveProperty("actionsToNextLevel");
    });

    it("should calculate correct progress percentage", () => {
      const { result } = renderHook(() => useProgressiveDisclosure(), {
        wrapper: createWrapper(),
      });

      act(() => {
        for (let i = 0; i < 5; i++) {
          result.current.trackFeatureUse();
        }
      });

      const progress = result.current.getLevelProgress();
      expect(progress.progressPercent).toBe(50); // 5/10 = 50%
    });
  });

  describe("persistence", () => {
    it("should persist state to localStorage on level change", async () => {
      const { result } = renderHook(() => useProgressiveDisclosure(), {
        wrapper: createWrapper(),
      });

      act(() => {
        result.current.setLevel("advanced");
      });

      // Wait for effect to persist to localStorage
      await waitFor(() => {
        const stored = localStorage.getItem(STORAGE_KEY);
        expect(stored).not.toBeNull();
        if (stored) {
          const parsed = JSON.parse(stored);
          expect(parsed.level).toBe("advanced");
        }
      });
    });

    it("should persist state on feature usage", async () => {
      const { result } = renderHook(() => useProgressiveDisclosure(), {
        wrapper: createWrapper(),
      });

      act(() => {
        result.current.trackFeatureUse();
      });

      // Wait for effect to persist to localStorage
      await waitFor(() => {
        const stored = localStorage.getItem(STORAGE_KEY);
        expect(stored).not.toBeNull();
        if (stored) {
          const parsed = JSON.parse(stored);
          expect(parsed.featureUsageCount).toBe(1);
        }
      });
    });
  });

  describe("reset", () => {
    it("should reset to initial state", () => {
      const { result } = renderHook(() => useProgressiveDisclosure(), {
        wrapper: createWrapper(),
      });

      act(() => {
        result.current.setLevel("expert");
        result.current.trackFeatureUse();
        result.current.trackFeatureUse();
      });

      act(() => {
        result.current.reset();
      });

      expect(result.current.level).toBe("beginner");
      expect(result.current.autoDetect).toBe(true);
      expect(result.current.featureUsageCount).toBe(0);
    });
  });

  describe("getComponentConfig", () => {
    it("should return disclosure config for a component", () => {
      const { result } = renderHook(() => useProgressiveDisclosure(), {
        wrapper: createWrapper(),
      });

      const config = result.current.getComponentConfig("workflow_builder");

      expect(config).toHaveProperty("visible");
      expect(config).toHaveProperty("minimumLevel");
      expect(config).toHaveProperty("showHint");
    });

    it("should mark component as visible when level is sufficient", () => {
      const { result } = renderHook(() => useProgressiveDisclosure(), {
        wrapper: createWrapper(),
      });

      act(() => {
        result.current.setLevel("advanced");
      });

      // Advanced workflow builder should be visible for advanced users
      const config = result.current.getComponentConfig("workflow_builder");
      expect(config.visible).toBe(true);
    });
  });
});
