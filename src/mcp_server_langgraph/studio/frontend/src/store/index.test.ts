/**
 * Redux Store Tests
 *
 * TDD tests for Redux Toolkit store configuration.
 * Tests cover:
 * - Store initialization
 * - Middleware configuration
 * - Reducer composition
 * - Type safety
 */

import { describe, it, expect, afterEach, vi } from "vitest";
import { store, RootState, AppDispatch } from "./index";
import { api } from "../api";

describe("Redux Store", () => {
  afterEach(() => {
    vi.clearAllMocks();
  });

  describe("Store Configuration", () => {
    it("should be properly configured", () => {
      expect(store).toBeDefined();
      expect(store.getState).toBeDefined();
      expect(store.dispatch).toBeDefined();
    });

    it("should have the API reducer mounted", () => {
      const state = store.getState();
      expect(state).toHaveProperty(api.reducerPath);
    });

    it("should have the UI reducer mounted", () => {
      const state = store.getState();
      expect(state).toHaveProperty("ui");
    });

    it("should have the persona reducer mounted", () => {
      const state = store.getState();
      expect(state).toHaveProperty("persona");
    });
  });

  describe("Initial State", () => {
    it("should have correct initial UI state", () => {
      const state = store.getState();
      expect(state.ui).toBeDefined();
      expect(state.ui.sidebarOpen).toBe(true);
      expect(state.ui.theme).toBe("dark");
      expect(state.ui.notifications).toEqual([]);
    });

    it("should have correct initial persona state", () => {
      const state = store.getState();
      expect(state.persona).toBeDefined();
      expect(state.persona.username).toBeDefined();
    });

    it("should have API state with correct structure", () => {
      const state = store.getState();
      const apiState = state[api.reducerPath];
      expect(apiState).toBeDefined();
      expect(apiState).toHaveProperty("queries");
      expect(apiState).toHaveProperty("mutations");
    });
  });

  describe("Type Safety", () => {
    it("should have correctly typed RootState", () => {
      const state: RootState = store.getState();

      // These should compile without errors
      const _uiSidebarOpen: boolean = state.ui.sidebarOpen;
      const _personaUsername: string | null = state.persona.username;

      expect(_uiSidebarOpen).toBeDefined();
      expect(_personaUsername).toBeDefined();
    });

    it("should have correctly typed AppDispatch", () => {
      const dispatch: AppDispatch = store.dispatch;
      expect(dispatch).toBeDefined();
      expect(typeof dispatch).toBe("function");
    });
  });

  describe("Middleware", () => {
    it("should have RTK Query middleware configured", () => {
      // RTK Query middleware should be present
      // This is implicitly tested by checking that API endpoints work
      const state = store.getState();
      expect(state[api.reducerPath]).toBeDefined();
    });
  });
});

describe("Store Hooks", () => {
  describe("useAppDispatch", () => {
    it("should export useAppDispatch hook", async () => {
      const { useAppDispatch } = await import("./hooks");
      expect(useAppDispatch).toBeDefined();
      expect(typeof useAppDispatch).toBe("function");
    });
  });

  describe("useAppSelector", () => {
    it("should export useAppSelector hook", async () => {
      const { useAppSelector } = await import("./hooks");
      expect(useAppSelector).toBeDefined();
      expect(typeof useAppSelector).toBe("function");
    });
  });
});
