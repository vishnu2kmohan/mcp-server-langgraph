/**
 * authSlice Actions Tests
 *
 * Tests for logout, clearError, setTokens, and selectors.
 */

import { describe, it, expect, beforeEach, vi, afterEach } from "vitest";
import {
  logout,
  clearAuthError,
  setTokens,
  selectUser,
  selectTokens,
  selectCurrentOrg,
  selectOrganizations,
  selectAuthError,
  selectIsAuthenticated,
  selectUserPersona,
} from "./authSlice";
import type { AuthTokens } from "../../types/auth";
import {
  createTestStore,
  createMockLocalStorage,
  createMockFetch,
  mockUser,
  mockTokens,
  mockOrg,
} from "./authSlice.test-utils";

describe("authSlice Actions", () => {
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

  describe("logout", () => {
    it("should clear user", () => {
      const store = createTestStore({ user: mockUser });
      store.dispatch(logout());

      expect(selectUser(store.getState())).toBeNull();
    });

    it("should clear tokens", () => {
      const store = createTestStore({ tokens: mockTokens });
      store.dispatch(logout());

      expect(selectTokens(store.getState())).toBeNull();
    });

    it("should clear currentOrg", () => {
      const store = createTestStore({ currentOrg: mockOrg });
      store.dispatch(logout());

      expect(selectCurrentOrg(store.getState())).toBeNull();
    });

    it("should clear organizations", () => {
      const store = createTestStore({ organizations: [mockOrg] });
      store.dispatch(logout());

      expect(selectOrganizations(store.getState())).toEqual([]);
    });

    it("should clear error", () => {
      const store = createTestStore({ error: "Some error" });
      store.dispatch(logout());

      expect(selectAuthError(store.getState())).toBeNull();
    });

    it("should remove tokens from localStorage", () => {
      const store = createTestStore({ tokens: mockTokens });
      store.dispatch(logout());

      expect(localStorage.removeItem).toHaveBeenCalledWith("studio-auth");
    });

    it("should clear all OAuth2 token keys from localStorage", () => {
      const store = createTestStore({ tokens: mockTokens });
      store.dispatch(logout());

      expect(localStorage.removeItem).toHaveBeenCalledWith("studio-auth");
      expect(localStorage.removeItem).toHaveBeenCalledWith("access_token");
      expect(localStorage.removeItem).toHaveBeenCalledWith("refresh_token");
      expect(localStorage.removeItem).toHaveBeenCalledWith("auth_token");
    });

    it("should clear legacy auth_token key from localStorage", () => {
      mockLocalStorageHelper.storage["auth_token"] = "legacy-token";

      const store = createTestStore({ tokens: mockTokens });
      store.dispatch(logout());

      expect(localStorage.removeItem).toHaveBeenCalledWith("auth_token");
    });

    it("should set isAuthenticated to false after logout", () => {
      const store = createTestStore({
        user: mockUser,
        tokens: mockTokens,
      });

      expect(selectIsAuthenticated(store.getState())).toBe(true);
      store.dispatch(logout());
      expect(selectIsAuthenticated(store.getState())).toBe(false);
    });

    it("should be idempotent - multiple logouts should not error", () => {
      const store = createTestStore({ user: mockUser });

      expect(() => {
        store.dispatch(logout());
        store.dispatch(logout());
        store.dispatch(logout());
      }).not.toThrow();

      expect(selectUser(store.getState())).toBeNull();
    });
  });

  describe("clearAuthError", () => {
    it("should clear error", () => {
      const store = createTestStore({ error: "Some error" });
      store.dispatch(clearAuthError());

      expect(selectAuthError(store.getState())).toBeNull();
    });
  });

  describe("setTokens", () => {
    it("should set tokens", () => {
      const store = createTestStore();
      store.dispatch(setTokens(mockTokens));

      expect(selectTokens(store.getState())).toEqual(mockTokens);
    });

    it("should save tokens to localStorage", () => {
      const store = createTestStore();
      store.dispatch(setTokens(mockTokens));

      expect(localStorage.setItem).toHaveBeenCalledWith(
        "studio-auth",
        JSON.stringify({ state: { tokens: mockTokens } }),
      );
    });

    it("should update both access and refresh tokens", () => {
      const store = createTestStore({ tokens: mockTokens });
      const newTokens: AuthTokens = {
        accessToken: "updated-access-token",
        refreshToken: "updated-refresh-token",
        expiresAt: Date.now() + 7200000,
        refreshExpiresAt: Date.now() + 172800000,
      };

      store.dispatch(setTokens(newTokens));

      const tokens = selectTokens(store.getState());
      expect(tokens?.accessToken).toBe("updated-access-token");
      expect(tokens?.refreshToken).toBe("updated-refresh-token");
    });

    it("should preserve expiration timestamps", () => {
      const store = createTestStore();
      const futureExpiry = Date.now() + 3600000;
      const futureRefreshExpiry = Date.now() + 86400000;
      const tokensWithExpiry: AuthTokens = {
        ...mockTokens,
        expiresAt: futureExpiry,
        refreshExpiresAt: futureRefreshExpiry,
      };

      store.dispatch(setTokens(tokensWithExpiry));

      const tokens = selectTokens(store.getState());
      expect(tokens?.expiresAt).toBe(futureExpiry);
      expect(tokens?.refreshExpiresAt).toBe(futureRefreshExpiry);
    });
  });

  describe("Selectors", () => {
    describe("selectUserPersona", () => {
      it("should return user persona when user exists", () => {
        const store = createTestStore({ user: mockUser });
        expect(selectUserPersona(store.getState())).toBe("user");
      });

      it("should return null when no user", () => {
        const store = createTestStore();
        expect(selectUserPersona(store.getState())).toBeNull();
      });
    });

    describe("selectIsAuthenticated", () => {
      it("should return true when user exists", () => {
        const store = createTestStore({ user: mockUser });
        expect(selectIsAuthenticated(store.getState())).toBe(true);
      });

      it("should return false when no user", () => {
        const store = createTestStore();
        expect(selectIsAuthenticated(store.getState())).toBe(false);
      });
    });
  });
});
