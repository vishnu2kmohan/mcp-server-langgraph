/**
 * Alert Slice localStorage Persistence Tests
 *
 * TDD tests for the alert Redux slice localStorage persistence.
 * Tests sound preference persistence across sessions.
 *
 * Reference: ADR-0026 - Comprehensive Client Resilience Patterns
 *
 * NOTE: Action and selector tests moved to __tests__/ directory:
 * - alertSlice.actions.test.ts - Actions and reducers
 * - alertSlice.selectors.test.ts - Selectors and grouping
 * - alertSlice.fixtures.ts - Shared test helpers
 */

import { describe, it, expect, vi, beforeEach, afterEach } from "vitest";
import { configureStore } from "@reduxjs/toolkit";

describe("alertSlice localStorage persistence", () => {
  const STORAGE_KEY = "studio-alert-sound-enabled";

  beforeEach(() => {
    localStorage.clear();
    vi.clearAllMocks();
  });

  afterEach(() => {
    localStorage.clear();
  });

  describe("loadSoundPreference", () => {
    it("should return true (default) when localStorage is empty", async () => {
      const { loadSoundPreference } = await import("./alertSlice");
      expect(loadSoundPreference()).toBe(true);
    });

    it("should return false when localStorage has false", async () => {
      localStorage.setItem(STORAGE_KEY, "false");
      const { loadSoundPreference } = await import("./alertSlice");
      expect(loadSoundPreference()).toBe(false);
    });

    it("should return true when localStorage has true", async () => {
      localStorage.setItem(STORAGE_KEY, "true");
      const { loadSoundPreference } = await import("./alertSlice");
      expect(loadSoundPreference()).toBe(true);
    });
  });

  describe("saveSoundPreference", () => {
    it("should save sound preference to localStorage", async () => {
      const { saveSoundPreference } = await import("./alertSlice");
      saveSoundPreference(false);
      expect(localStorage.getItem(STORAGE_KEY)).toBe("false");
      saveSoundPreference(true);
      expect(localStorage.getItem(STORAGE_KEY)).toBe("true");
    });
  });

  describe("toggleSound with persistence", () => {
    it("should persist sound state when toggling", async () => {
      const { default: alertReducer, toggleSound } =
        await import("./alertSlice");
      const store = configureStore({
        reducer: { alerts: alertReducer },
        preloadedState: {
          alerts: {
            alerts: [],
            selectedAlertId: null,
            pendingRemediations: [],
            soundEnabled: true,
            lastCriticalAlertTime: null,
            filters: { severity: ["critical", "warning"], state: ["firing"] },
          },
        },
      });
      store.dispatch(toggleSound());
      expect(localStorage.getItem(STORAGE_KEY)).toBe("false");
    });
  });

  describe("setSoundEnabled with persistence", () => {
    it("should persist sound state when setting value", async () => {
      const { default: alertReducer, setSoundEnabled } =
        await import("./alertSlice");
      const store = configureStore({
        reducer: { alerts: alertReducer },
        preloadedState: {
          alerts: {
            alerts: [],
            selectedAlertId: null,
            pendingRemediations: [],
            soundEnabled: true,
            lastCriticalAlertTime: null,
            filters: { severity: ["critical", "warning"], state: ["firing"] },
          },
        },
      });
      store.dispatch(setSoundEnabled(false));
      expect(localStorage.getItem(STORAGE_KEY)).toBe("false");
      store.dispatch(setSoundEnabled(true));
      expect(localStorage.getItem(STORAGE_KEY)).toBe("true");
    });
  });

  describe("initializeSoundFromStorage action", () => {
    it("should initialize sound state from localStorage", async () => {
      localStorage.setItem(STORAGE_KEY, "false");
      const {
        default: alertReducer,
        initializeSoundFromStorage,
        selectSoundEnabled,
      } = await import("./alertSlice");
      const store = configureStore({
        reducer: { alerts: alertReducer },
      });
      expect(selectSoundEnabled(store.getState())).toBe(true);
      store.dispatch(initializeSoundFromStorage());
      expect(selectSoundEnabled(store.getState())).toBe(false);
    });

    it("should keep default true when localStorage has no value", async () => {
      localStorage.clear();
      const {
        default: alertReducer,
        initializeSoundFromStorage,
        selectSoundEnabled,
      } = await import("./alertSlice");
      const store = configureStore({
        reducer: { alerts: alertReducer },
      });
      store.dispatch(initializeSoundFromStorage());
      expect(selectSoundEnabled(store.getState())).toBe(true);
    });
  });
});
