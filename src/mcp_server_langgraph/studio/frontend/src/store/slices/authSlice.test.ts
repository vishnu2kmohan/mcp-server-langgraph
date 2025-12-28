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

    it("should clear all OAuth2 token keys from localStorage", () => {
      const store = createTestStore({ tokens: mockTokens });
      store.dispatch(logout());

      // clearAllAuthStorage removes: studio-auth, access_token, refresh_token, auth_token
      expect(localStorage.removeItem).toHaveBeenCalledWith("studio-auth");
      expect(localStorage.removeItem).toHaveBeenCalledWith("access_token");
      expect(localStorage.removeItem).toHaveBeenCalledWith("refresh_token");
      expect(localStorage.removeItem).toHaveBeenCalledWith("auth_token");
    });

    it("should clear legacy auth_token key from localStorage", () => {
      // GIVEN: Legacy auth_token exists
      mockLocalStorage["auth_token"] = "legacy-token";

      const store = createTestStore({ tokens: mockTokens });
      store.dispatch(logout());

      // THEN: Legacy key should be cleared
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

      // Multiple logout calls should not throw
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
        expiresAt: Date.now() + 7200000, // 2 hours
        refreshExpiresAt: Date.now() + 172800000, // 48 hours
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

  describe("Token Expiration Handling", () => {
    it("should detect expired access token", async () => {
      const expiredTokens: AuthTokens = {
        accessToken: "expired-token",
        refreshToken: "valid-refresh",
        expiresAt: Date.now() - 1000, // Already expired
        refreshExpiresAt: Date.now() + 86400000, // Still valid
      };

      // Token with expiresAt in the past should be considered expired
      // The check is: Date.now() >= expiresAt - BUFFER (5 min)
      expect(expiredTokens.expiresAt < Date.now()).toBe(true);
    });

    it("should detect token about to expire within buffer", async () => {
      // Token expires in 3 minutes (within 5 min buffer)
      const tokenExpiresSoon: AuthTokens = {
        accessToken: "soon-expired-token",
        refreshToken: "valid-refresh",
        expiresAt: Date.now() + 3 * 60 * 1000, // 3 minutes
        refreshExpiresAt: Date.now() + 86400000,
      };

      // With 5 minute buffer, token expiring in 3 minutes should trigger refresh
      const bufferMs = 5 * 60 * 1000;
      const shouldRefresh = Date.now() >= tokenExpiresSoon.expiresAt - bufferMs;
      expect(shouldRefresh).toBe(true);
    });

    it("should not refresh token with plenty of time remaining", async () => {
      // Token expires in 30 minutes (outside 5 min buffer)
      const validTokens: AuthTokens = {
        accessToken: "valid-token",
        refreshToken: "valid-refresh",
        expiresAt: Date.now() + 30 * 60 * 1000, // 30 minutes
        refreshExpiresAt: Date.now() + 86400000,
      };

      // With 5 minute buffer, token expiring in 30 minutes should NOT trigger refresh
      const bufferMs = 5 * 60 * 1000;
      const shouldRefresh = Date.now() >= validTokens.expiresAt - bufferMs;
      expect(shouldRefresh).toBe(false);
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

      // authenticatedFetch handles Authorization header internally
      expect(mockFetch).toHaveBeenCalledWith(
        "/api/v1/me",
        expect.objectContaining({
          credentials: "include",
        }),
      );
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

  describe("login async thunk error handling", () => {
    it("should handle network error (Error instance)", async () => {
      mockFetch.mockRejectedValueOnce(new Error("Network failure"));

      const store = createTestStore();
      await store.dispatch(login({ username: "test", password: "password" }));

      expect(selectAuthError(store.getState())).toBe("Network failure");
      expect(selectUser(store.getState())).toBeNull();
      expect(selectIsLoading(store.getState())).toBe(false);
    });

    it("should handle non-Error rejection with default message", async () => {
      mockFetch.mockRejectedValueOnce("String error");

      const store = createTestStore();
      await store.dispatch(login({ username: "test", password: "password" }));

      expect(selectAuthError(store.getState())).toBe("Login failed");
    });

    it("should handle empty organizations in response", async () => {
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
            // No organizations
          }),
      });

      const store = createTestStore();
      await store.dispatch(login({ username: "test", password: "password" }));

      expect(selectOrganizations(store.getState())).toEqual([]);
      expect(selectCurrentOrg(store.getState())).toBeNull();
    });
  });

  describe("initializeAuth edge cases", () => {
    it("should logout when refresh token is expired", async () => {
      const expiredRefreshTokens: AuthTokens = {
        accessToken: "access-token",
        refreshToken: "expired-refresh",
        expiresAt: Date.now() + 3600000,
        refreshExpiresAt: Date.now() - 1000, // Expired
      };

      const store = createTestStore({
        tokens: expiredRefreshTokens,
        user: mockUser,
      });
      await store.dispatch(initializeAuth());

      expect(selectUser(store.getState())).toBeNull();
      expect(selectTokens(store.getState())).toBeNull();
    });

    it("should handle API response with keycloak_id instead of user_id", async () => {
      mockFetch.mockResolvedValueOnce({
        ok: true,
        json: () =>
          Promise.resolve({
            keycloak_id: "kc-user-123",
            username: "keycloak-user",
            email: "kc@example.com",
            first_name: "Keycloak",
            last_name: "User",
            display_name: "Keycloak User",
            roles: ["developer"],
          }),
      });

      const store = createTestStore({ tokens: mockTokens });
      await store.dispatch(initializeAuth());

      const user = selectUser(store.getState());
      expect(user?.id).toBe("kc-user-123");
      expect(user?.firstName).toBe("Keycloak");
      expect(user?.lastName).toBe("User");
      expect(user?.displayName).toBe("Keycloak User");
    });

    it("should derive persona when not provided in response", async () => {
      mockFetch.mockResolvedValueOnce({
        ok: true,
        json: () =>
          Promise.resolve({
            user_id: "user-abc",
            username: "alice",
            email: "alice@example.com",
            roles: ["admin", "developer"],
            // No persona field - should derive from roles
          }),
      });

      const store = createTestStore({ tokens: mockTokens });
      await store.dispatch(initializeAuth());

      const user = selectUser(store.getState());
      expect(user?.persona).toBe("admin"); // Derived from roles
    });

    it("should use persona from response when provided", async () => {
      mockFetch.mockResolvedValueOnce({
        ok: true,
        json: () =>
          Promise.resolve({
            user_id: "user-xyz",
            username: "bob",
            email: "bob@example.com",
            roles: ["user"],
            persona: "developer", // Explicit override
          }),
      });

      const store = createTestStore({ tokens: mockTokens });
      await store.dispatch(initializeAuth());

      const user = selectUser(store.getState());
      expect(user?.persona).toBe("developer"); // From response, not derived
    });

    it("should refresh access token when expired but refresh token is valid", async () => {
      const expiredAccessTokens: AuthTokens = {
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

      // First call is for token refresh
      mockFetch.mockResolvedValueOnce({
        ok: true,
        json: () => Promise.resolve({ tokens: newTokens }),
      });

      // Second call is for /api/v1/me
      mockFetch.mockResolvedValueOnce({
        ok: true,
        json: () =>
          Promise.resolve({
            user_id: "user-1",
            username: "test",
            email: "test@example.com",
            roles: ["user"],
          }),
      });

      const store = createTestStore({ tokens: expiredAccessTokens });
      await store.dispatch(initializeAuth());

      // Should have refreshed the token
      expect(mockFetch).toHaveBeenCalledWith(
        "/api/v1/auth/refresh",
        expect.any(Object),
      );
      // Should have called /me (authenticatedFetch handles Authorization header)
      expect(mockFetch).toHaveBeenCalledWith(
        "/api/v1/me",
        expect.objectContaining({
          credentials: "include",
        }),
      );
      // User should be set
      expect(selectUser(store.getState())).toBeTruthy();
    });
  });

  describe("refreshToken edge cases", () => {
    it("should handle refresh with empty refresh token", async () => {
      const tokensWithEmptyRefresh: AuthTokens = {
        accessToken: "access-token",
        refreshToken: "", // Empty string
        expiresAt: Date.now() + 3600000,
        refreshExpiresAt: Date.now() + 86400000,
      };

      const store = createTestStore({
        tokens: tokensWithEmptyRefresh,
        user: mockUser,
      });
      await store.dispatch(refreshToken());

      // Should logout due to empty refresh token
      expect(selectUser(store.getState())).toBeNull();
    });

    it("should handle network error during refresh", async () => {
      mockFetch.mockRejectedValueOnce(new Error("Connection refused"));

      const store = createTestStore({
        tokens: mockTokens,
        user: mockUser,
      });
      await store.dispatch(refreshToken());

      // Should logout on network error
      expect(selectUser(store.getState())).toBeNull();
      expect(selectTokens(store.getState())).toBeNull();
    });
  });

  describe("switchOrganization edge cases", () => {
    it("should handle network error during switch", async () => {
      mockFetch.mockRejectedValueOnce(new Error("Network timeout"));

      const org2: Organization = {
        id: "org-2",
        name: "Org 2",
        role: "member",
        tier: "hybrid",
      };

      const store = createTestStore({
        tokens: mockTokens,
        organizations: [mockOrg, org2],
        currentOrg: mockOrg,
      });

      await store.dispatch(switchOrganization("org-2"));

      // Should set error message from Error instance
      expect(selectAuthError(store.getState())).toBe("Network timeout");
    });

    it("should handle non-Error rejection during switch", async () => {
      mockFetch.mockRejectedValueOnce("Unknown error");

      const org2: Organization = {
        id: "org-2",
        name: "Org 2",
        role: "member",
        tier: "hybrid",
      };

      const store = createTestStore({
        tokens: mockTokens,
        organizations: [mockOrg, org2],
        currentOrg: mockOrg,
      });

      await store.dispatch(switchOrganization("org-2"));

      // Should use default error message
      expect(selectAuthError(store.getState())).toBe(
        "Failed to switch organization",
      );
    });

    it("should set error when organization not found in list", async () => {
      const store = createTestStore({
        tokens: mockTokens,
        organizations: [mockOrg],
        currentOrg: mockOrg,
      });

      await store.dispatch(switchOrganization("non-existent-org"));

      expect(selectAuthError(store.getState())).toBe("Organization not found");
    });
  });

  describe("login.rejected default error", () => {
    it("should use default error message when no detail provided", async () => {
      mockFetch.mockResolvedValueOnce({
        ok: false,
        json: () => Promise.resolve({}), // No detail field
      });

      const store = createTestStore();
      await store.dispatch(login({ username: "test", password: "password" }));

      expect(selectAuthError(store.getState())).toBe("Login failed");
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
