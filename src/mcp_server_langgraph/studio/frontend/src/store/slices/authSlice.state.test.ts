/**
 * authSlice State Tests
 *
 * Tests for initial state and setUser reducer.
 */

import { describe, it, expect, beforeEach, vi, afterEach } from "vitest";
import {
  selectUser,
  selectCurrentOrg,
  selectOrganizations,
  selectIsInitializing,
  selectIsLoading,
  selectAuthError,
  selectIsAuthenticated,
} from "./authSlice";
import {
  createTestStore,
  createMockLocalStorage,
  createMockFetch,
} from "./authSlice.test-utils";

describe("authSlice State", () => {
  const mockFetchHelper = createMockFetch();
  const mockLocalStorageHelper = createMockLocalStorage();

  beforeEach(() => {
    vi.clearAllMocks();
    mockFetchHelper.setup();
    mockLocalStorageHelper.setup();
  });

  afterEach(() => {
    vi.unstubAllGlobals();
    mockLocalStorageHelper.cleanup();
  });

  describe("Initial State", () => {
    it("should have null user", () => {
      const store = createTestStore();
      expect(selectUser(store.getState())).toBeNull();
    });

    it("should have null currentOrg", () => {
      const store = createTestStore();
      expect(selectCurrentOrg(store.getState())).toBeNull();
    });

    it("should have empty organizations", () => {
      const store = createTestStore();
      expect(selectOrganizations(store.getState())).toEqual([]);
    });

    it("should not be initializing", () => {
      const store = createTestStore();
      expect(selectIsInitializing(store.getState())).toBe(false);
    });

    it("should not be loading", () => {
      const store = createTestStore();
      expect(selectIsLoading(store.getState())).toBe(false);
    });

    it("should have no error", () => {
      const store = createTestStore();
      expect(selectAuthError(store.getState())).toBeNull();
    });

    it("should not be authenticated", () => {
      const store = createTestStore();
      expect(selectIsAuthenticated(store.getState())).toBe(false);
    });
  });

  describe("setUser reducer", () => {
    it("should set user from native login response", () => {
      const store = createTestStore({ isInitializing: true });
      store.dispatch({
        type: "auth/setUser",
        payload: {
          username: "alice",
          email: "alice@example.com",
          roles: ["admin", "developer"],
          persona: "admin",
        },
      });

      const user = selectUser(store.getState());
      expect(user?.username).toBe("alice");
      expect(user?.id).toBe("user:alice");
      expect(user?.email).toBe("alice@example.com");
      expect(user?.roles).toEqual(["admin", "developer"]);
      expect(user?.persona).toBe("admin");
      expect(selectIsInitializing(store.getState())).toBe(false);
      expect(selectIsLoading(store.getState())).toBe(false);
    });

    it("should handle missing email in setUser", () => {
      const store = createTestStore();
      store.dispatch({
        type: "auth/setUser",
        payload: {
          username: "bob",
          roles: ["user"],
          persona: "user",
        },
      });

      const user = selectUser(store.getState());
      expect(user?.email).toBe("");
    });
  });
});
