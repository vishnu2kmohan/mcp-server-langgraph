/**
 * Auth Slice Tests
 *
 * TDD tests for Auth Redux slice.
 */

import { describe, it, expect, beforeEach, vi, afterEach } from "vitest";
import { configureStore } from "@reduxjs/toolkit";
import authReducer, {
  initialAuthState,
  logout,
  clearAuthError,
  setTokens,
  derivePersona,
  selectUser,
  selectTokens,
  selectCurrentOrg,
  selectOrganizations,
  selectIsInitializing,
  selectIsLoading,
  selectAuthError,
  selectIsAuthenticated,
  selectUserPersona,
  login,
  initializeAuth,
  refreshToken,
  switchOrganization,
  getAccessToken,
} from "./authSlice";
import type { AuthSliceState } from "./authSlice";
import type { User, AuthTokens, Organization } from "../../types/auth";

// Helper to create a test store
const createTestStore = (preloadedState?: Partial<AuthSliceState>) => {
  return configureStore({
    reducer: { auth: authReducer },
    preloadedState: preloadedState
      ? { auth: { ...initialAuthState, ...preloadedState } }
      : undefined,
  });
};

// Mock user
const mockUser: User = {
  id: "user-1",
  username: "testuser",
  email: "test@example.com",
  roles: ["user"],
  persona: "user",
};

// Mock tokens
const mockTokens: AuthTokens = {
  accessToken: "mock-access-token",
  refreshToken: "mock-refresh-token",
  expiresAt: Date.now() + 3600000, // 1 hour from now
  refreshExpiresAt: Date.now() + 86400000, // 24 hours from now
};

// Mock organization
const mockOrg: Organization = {
  id: "org-1",
  name: "Test Org",
  role: "admin",
  tier: "shared",
};

describe("authSlice", () => {
  const mockFetch = vi.fn();
  const mockLocalStorage: Record<string, string> = {};

  beforeEach(() => {
    vi.clearAllMocks();
    vi.stubGlobal("fetch", mockFetch);

    // Mock localStorage
    vi.stubGlobal("localStorage", {
      getItem: vi.fn((key: string) => mockLocalStorage[key] || null),
      setItem: vi.fn((key: string, value: string) => {
        mockLocalStorage[key] = value;
      }),
      removeItem: vi.fn((key: string) => {
        delete mockLocalStorage[key];
      }),
    });
  });

  afterEach(() => {
    vi.unstubAllGlobals();
    Object.keys(mockLocalStorage).forEach(
      (key) => delete mockLocalStorage[key],
    );
  });

  describe("derivePersona", () => {
    it("should return admin when roles include admin", () => {
      expect(derivePersona(["admin", "user"])).toBe("admin");
    });

    it("should return developer when roles include developer but not admin", () => {
      expect(derivePersona(["developer", "user"])).toBe("developer");
    });

    it("should return user as default persona", () => {
      expect(derivePersona(["user"])).toBe("user");
      expect(derivePersona([])).toBe("user");
    });

    it("should prioritize admin over developer", () => {
      expect(derivePersona(["developer", "admin"])).toBe("admin");
    });
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

  describe("login async thunk", () => {
    it("should set loading state when pending", async () => {
      mockFetch.mockImplementation(
        () => new Promise(() => {}), // Never resolves
      );

      const store = createTestStore();
      store.dispatch(login({ username: "test", password: "password" }));

      expect(selectIsLoading(store.getState())).toBe(true);
    });

    it("should set user on successful login", async () => {
      mockFetch.mockResolvedValueOnce({
        ok: true,
        json: () =>
          Promise.resolve({
            user: {
              id: "user-1",
              username: "test",
              email: "test@example.com",
              roles: ["user"],
            },
            tokens: mockTokens,
            organizations: [mockOrg],
          }),
      });

      const store = createTestStore();
      await store.dispatch(login({ username: "test", password: "password" }));

      expect(selectUser(store.getState())).toBeTruthy();
      expect(selectUser(store.getState())?.username).toBe("test");
      expect(selectIsLoading(store.getState())).toBe(false);
    });

    it("should set error on login failure", async () => {
      mockFetch.mockResolvedValueOnce({
        ok: false,
        json: () => Promise.resolve({ detail: "Invalid credentials" }),
      });

      const store = createTestStore();
      await store.dispatch(login({ username: "test", password: "wrong" }));

      expect(selectAuthError(store.getState())).toBe("Invalid credentials");
      expect(selectUser(store.getState())).toBeNull();
    });

    it("should set organizations on successful login", async () => {
      mockFetch.mockResolvedValueOnce({
        ok: true,
        json: () =>
          Promise.resolve({
            user: {
              id: "user-1",
              username: "test",
              email: "test@example.com",
              roles: ["user"],
            },
            tokens: mockTokens,
            organizations: [mockOrg],
          }),
      });

      const store = createTestStore();
      await store.dispatch(login({ username: "test", password: "password" }));

      expect(selectOrganizations(store.getState())).toHaveLength(1);
      expect(selectCurrentOrg(store.getState())).toEqual(mockOrg);
    });
  });

  describe("initializeAuth async thunk", () => {
    it("should return null when no stored tokens", async () => {
      const store = createTestStore({ tokens: null });
      await store.dispatch(initializeAuth());

      expect(selectUser(store.getState())).toBeNull();
    });

    it("should set initializing state when pending", async () => {
      mockFetch.mockImplementation(
        () => new Promise(() => {}), // Never resolves
      );

      const store = createTestStore({ tokens: mockTokens });
      store.dispatch(initializeAuth());

      expect(selectIsInitializing(store.getState())).toBe(true);
    });

    it("should fetch user info when tokens exist", async () => {
      mockFetch.mockResolvedValueOnce({
        ok: true,
        json: () =>
          Promise.resolve({
            user: {
              id: "user-1",
              username: "test",
              email: "test@example.com",
              roles: ["user"],
            },
            organizations: [mockOrg],
          }),
      });

      const store = createTestStore({ tokens: mockTokens });
      await store.dispatch(initializeAuth());

      expect(mockFetch).toHaveBeenCalledWith("/api/v1/auth/me", {
        headers: { Authorization: `Bearer ${mockTokens.accessToken}` },
        credentials: "include",
      });
    });
  });

  describe("refreshToken async thunk", () => {
    it("should call logout when no refresh token", async () => {
      const store = createTestStore({ tokens: null });
      await store.dispatch(refreshToken());

      expect(selectUser(store.getState())).toBeNull();
    });

    it("should update tokens on successful refresh", async () => {
      const newTokens: AuthTokens = {
        ...mockTokens,
        accessToken: "new-access-token",
      };

      mockFetch.mockResolvedValueOnce({
        ok: true,
        json: () => Promise.resolve({ tokens: newTokens }),
      });

      const store = createTestStore({ tokens: mockTokens });
      await store.dispatch(refreshToken());

      expect(selectTokens(store.getState())?.accessToken).toBe(
        "new-access-token",
      );
    });

    it("should logout on refresh failure", async () => {
      mockFetch.mockResolvedValueOnce({
        ok: false,
        status: 401,
      });

      const store = createTestStore({ tokens: mockTokens, user: mockUser });
      await store.dispatch(refreshToken());

      expect(selectUser(store.getState())).toBeNull();
    });
  });

  describe("switchOrganization async thunk", () => {
    it("should update currentOrg on success", async () => {
      const org2: Organization = {
        id: "org-2",
        name: "Org 2",
        role: "member",
        tier: "hybrid",
      };

      mockFetch.mockResolvedValueOnce({
        ok: true,
        json: () => Promise.resolve({}),
      });

      const store = createTestStore({
        tokens: mockTokens,
        organizations: [mockOrg, org2],
        currentOrg: mockOrg,
      });

      await store.dispatch(switchOrganization("org-2"));

      expect(selectCurrentOrg(store.getState())).toEqual(org2);
    });

    it("should reject when organization not found", async () => {
      const store = createTestStore({
        tokens: mockTokens,
        organizations: [mockOrg],
        currentOrg: mockOrg,
      });

      await store.dispatch(switchOrganization("non-existent"));

      // Should still have original org
      expect(selectCurrentOrg(store.getState())).toEqual(mockOrg);
    });
  });

  describe("initializeAuth.rejected", () => {
    it("should clear user and tokens when initialization fails", async () => {
      mockFetch.mockRejectedValueOnce(new Error("Network error"));

      const store = createTestStore({
        tokens: mockTokens,
        user: mockUser,
        isInitializing: true,
      });
      await store.dispatch(initializeAuth());

      expect(selectUser(store.getState())).toBeNull();
      expect(selectTokens(store.getState())).toBeNull();
      expect(selectIsInitializing(store.getState())).toBe(false);
    });

    it("should handle 401 response by clearing auth state", async () => {
      mockFetch.mockResolvedValueOnce({
        ok: false,
        status: 401,
        json: () => Promise.resolve({ detail: "Unauthorized" }),
      });

      const store = createTestStore({
        tokens: mockTokens,
        user: mockUser,
      });
      await store.dispatch(initializeAuth());

      expect(selectUser(store.getState())).toBeNull();
      expect(selectTokens(store.getState())).toBeNull();
    });
  });

  describe("getAccessToken async thunk", () => {
    it("should return null when no tokens exist", async () => {
      const store = createTestStore({ tokens: null });
      const result = await store.dispatch(getAccessToken());

      expect(result.payload).toBeNull();
    });

    it("should return access token when token is not expired", async () => {
      const validTokens: AuthTokens = {
        accessToken: "valid-access-token",
        refreshToken: "refresh-token",
        expiresAt: Date.now() + 3600000, // 1 hour from now
        refreshExpiresAt: Date.now() + 86400000, // 24 hours from now
      };

      const store = createTestStore({ tokens: validTokens });
      const result = await store.dispatch(getAccessToken());

      expect(result.payload).toBe("valid-access-token");
    });

    it("should refresh token when access token is expired but refresh token is valid", async () => {
      const expiredTokens: AuthTokens = {
        accessToken: "expired-access-token",
        refreshToken: "valid-refresh-token",
        expiresAt: Date.now() - 1000, // Already expired
        refreshExpiresAt: Date.now() + 86400000, // Still valid
      };

      const newTokens: AuthTokens = {
        accessToken: "new-access-token",
        refreshToken: "new-refresh-token",
        expiresAt: Date.now() + 3600000,
        refreshExpiresAt: Date.now() + 86400000,
      };

      mockFetch.mockResolvedValueOnce({
        ok: true,
        json: () => Promise.resolve({ tokens: newTokens }),
      });

      const store = createTestStore({ tokens: expiredTokens });
      const result = await store.dispatch(getAccessToken());

      expect(result.payload).toBe("new-access-token");
    });

    it("should logout and return null when both tokens are expired", async () => {
      const fullyExpiredTokens: AuthTokens = {
        accessToken: "expired-access-token",
        refreshToken: "expired-refresh-token",
        expiresAt: Date.now() - 1000, // Expired
        refreshExpiresAt: Date.now() - 1000, // Also expired
      };

      const store = createTestStore({
        tokens: fullyExpiredTokens,
        user: mockUser,
      });
      const result = await store.dispatch(getAccessToken());

      expect(result.payload).toBeNull();
      expect(selectUser(store.getState())).toBeNull();
    });
  });
});
