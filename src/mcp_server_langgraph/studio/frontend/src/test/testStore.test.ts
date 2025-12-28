/**
 * Tests for Test Store Factory
 *
 * Validates that the shared test store utilities work correctly
 * and provide proper Redux state management for tests.
 */

import { describe, it, expect, beforeEach, afterEach, vi } from "vitest";
import {
  createTestStore,
  createMinimalStore,
  authenticatedAuthState,
  adminAuthState,
  resetStore,
  selectIsAuthenticated,
  type TestStore,
} from "./testStore";

afterEach(() => {
  vi.clearAllMocks();
  vi.restoreAllMocks();
});

describe("testStore", () => {
  describe("createTestStore", () => {
    it("should create a store with default state", () => {
      const store = createTestStore();
      const state = store.getState();

      expect(state).toBeDefined();
      expect(state.auth).toBeDefined();
      expect(state.session).toBeDefined();
      expect(state.canvas).toBeDefined();
    });

    it("should accept preloaded state", () => {
      const store = createTestStore({
        preloadedState: {
          auth: authenticatedAuthState,
        },
      });

      const state = store.getState();
      expect(selectIsAuthenticated(state)).toBe(true);
      expect(state.auth.user?.email).toBe("test@example.com");
    });

    it("should include extra reducers when provided", () => {
      const customReducer = (
        state = { value: 0 },
        action: { type: string; payload?: number },
      ) => {
        if (action.type === "INCREMENT") {
          return { value: state.value + (action.payload ?? 1) };
        }
        return state;
      };

      const store = createTestStore({
        extraReducers: { custom: customReducer },
      });

      const state = store.getState() as { custom: { value: number } };
      expect(state.custom).toBeDefined();
      expect(state.custom.value).toBe(0);
    });

    it("should dispatch actions correctly", () => {
      const store = createTestStore();

      // Verify we can dispatch actions
      expect(() => {
        store.dispatch({ type: "TEST_ACTION" });
      }).not.toThrow();
    });
  });

  describe("createMinimalStore", () => {
    it("should create a store with only specified reducers", () => {
      const store = createMinimalStore(["auth", "session"]);
      const state = store.getState();

      expect(state.auth).toBeDefined();
      expect(state.session).toBeDefined();
      // Should not have other reducers
      expect((state as Record<string, unknown>).canvas).toBeUndefined();
      expect((state as Record<string, unknown>).persona).toBeUndefined();
    });

    it("should accept preloaded state for selected reducers", () => {
      const store = createMinimalStore(["auth"], {
        auth: authenticatedAuthState,
      });

      // Note: selectIsAuthenticated expects full RootState, but minimal store only has auth
      // So we check the user directly instead
      const state = store.getState();
      expect(state.auth.user).not.toBeNull();
    });

    it("should handle single reducer", () => {
      const store = createMinimalStore(["auth"]);
      const state = store.getState();

      expect(state.auth).toBeDefined();
      expect(Object.keys(state)).toHaveLength(1);
    });

    it("should handle multiple reducers", () => {
      const store = createMinimalStore([
        "auth",
        "session",
        "canvas",
        "persona",
      ]);
      const state = store.getState();

      expect(state.auth).toBeDefined();
      expect(state.session).toBeDefined();
      expect(state.canvas).toBeDefined();
      expect(state.persona).toBeDefined();
    });
  });

  describe("authenticatedAuthState", () => {
    it("should have user set (authenticated)", () => {
      // Authentication is derived from user !== null
      expect(authenticatedAuthState.user).not.toBeNull();
    });

    it("should have user data", () => {
      expect(authenticatedAuthState.user).toBeDefined();
      expect(authenticatedAuthState.user.email).toBe("test@example.com");
      expect(authenticatedAuthState.user.name).toBe("Test User");
    });

    it("should have tokens", () => {
      expect(authenticatedAuthState.tokens).toBeDefined();
      expect(authenticatedAuthState.tokens?.accessToken).toBe(
        "test-access-token",
      );
    });
  });

  describe("adminAuthState", () => {
    it("should have admin role", () => {
      expect(adminAuthState.user.roles).toContain("admin");
      expect(adminAuthState.user.roles).toContain("user");
    });

    it("should have admin user data", () => {
      expect(adminAuthState.user.email).toBe("admin@example.com");
      expect(adminAuthState.user.name).toBe("Admin User");
    });
  });

  describe("resetStore", () => {
    let store: TestStore;

    beforeEach(() => {
      store = createTestStore({
        preloadedState: {
          auth: authenticatedAuthState,
        },
      });
    });

    it("should create a new store instance", () => {
      const newStore = resetStore(store);

      expect(newStore).not.toBe(store);
    });

    it("should reset to default state", () => {
      const newStore = resetStore(store);
      const state = newStore.getState();

      // New store should have default auth state (not authenticated = user is null)
      expect(selectIsAuthenticated(state)).toBe(false);
    });

    it("should accept new options for reset", () => {
      const newStore = resetStore(store, {
        preloadedState: {
          auth: adminAuthState,
        },
      });

      const state = newStore.getState();
      expect(state.auth.user?.email).toBe("admin@example.com");
    });
  });

  describe("memory efficiency", () => {
    it("should reuse reducer imports across multiple store creations", () => {
      // Create multiple stores
      const stores = Array.from({ length: 10 }, () => createTestStore());

      // All stores should be independent but share reducer references
      expect(stores).toHaveLength(10);

      // Each store should have its own state
      const states = stores.map((s) => s.getState());
      states.forEach((state) => {
        expect(state.auth).toBeDefined();
      });
    });

    it("should create minimal stores with less overhead", () => {
      const fullStore = createTestStore();
      const minimalStore = createMinimalStore(["auth"]);

      const fullKeys = Object.keys(fullStore.getState());
      const minimalKeys = Object.keys(minimalStore.getState());

      // Minimal store should have fewer keys
      expect(minimalKeys.length).toBeLessThan(fullKeys.length);
    });
  });
});
