/**
 * authSlice Organization Tests
 *
 * Tests for initializeAuth and switchOrganization async thunks.
 */

import { describe, it, expect, beforeEach, vi, afterEach } from "vitest";
import {
  initializeAuth,
  switchOrganization,
  selectUser,
  selectTokens,
  selectIsInitializing,
  selectCurrentOrg,
  selectAuthError,
} from "./authSlice";
import type { AuthTokens, Organization } from "../../types/auth";
import {
  createTestStore,
  createMockLocalStorage,
  createMockFetch,
  mockUser,
  mockTokens,
  mockOrg,
} from "./authSlice.test-utils";

describe("authSlice Organization", () => {
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

  describe("initializeAuth async thunk", () => {
    it("should return null when no stored tokens", async () => {
      const store = createTestStore({ tokens: null });
      await store.dispatch(initializeAuth());

      expect(selectUser(store.getState())).toBeNull();
    });

    it("should set initializing state when pending", async () => {
      mockFetchHelper.mock.mockImplementation(() => new Promise(() => {})); // Never resolves

      const store = createTestStore({ tokens: mockTokens });
      store.dispatch(initializeAuth());

      expect(selectIsInitializing(store.getState())).toBe(true);
    });

    it("should fetch user info when tokens exist", async () => {
      mockFetchHelper.mock.mockResolvedValueOnce({
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

      expect(mockFetchHelper.mock).toHaveBeenCalledWith(
        "/api/v1/me",
        expect.objectContaining({
          credentials: "include",
        }),
      );
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

      mockFetchHelper.mock.mockResolvedValueOnce({
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

      expect(selectCurrentOrg(store.getState())).toEqual(mockOrg);
    });
  });

  describe("initializeAuth.rejected", () => {
    it("should clear user and tokens when initialization fails", async () => {
      mockFetchHelper.mock.mockRejectedValueOnce(new Error("Network error"));

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
      mockFetchHelper.mock.mockResolvedValueOnce({
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
      mockFetchHelper.mock.mockResolvedValueOnce({
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
      mockFetchHelper.mock.mockResolvedValueOnce({
        ok: true,
        json: () =>
          Promise.resolve({
            user_id: "user-abc",
            username: "alice",
            email: "alice@example.com",
            roles: ["admin", "developer"],
          }),
      });

      const store = createTestStore({ tokens: mockTokens });
      await store.dispatch(initializeAuth());

      const user = selectUser(store.getState());
      expect(user?.persona).toBe("admin"); // Derived from roles
    });

    it("should use persona from response when provided", async () => {
      mockFetchHelper.mock.mockResolvedValueOnce({
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
      mockFetchHelper.mock.mockResolvedValueOnce({
        ok: true,
        json: () => Promise.resolve({ tokens: newTokens }),
      });

      // Second call is for /api/v1/me
      mockFetchHelper.mock.mockResolvedValueOnce({
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

      expect(mockFetchHelper.mock).toHaveBeenCalledWith(
        "/api/v1/auth/refresh",
        expect.any(Object),
      );
      expect(mockFetchHelper.mock).toHaveBeenCalledWith(
        "/api/v1/me",
        expect.objectContaining({
          credentials: "include",
        }),
      );
      expect(selectUser(store.getState())).toBeTruthy();
    });
  });

  describe("switchOrganization edge cases", () => {
    it("should handle network error during switch", async () => {
      mockFetchHelper.mock.mockRejectedValueOnce(new Error("Network timeout"));

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

      expect(selectAuthError(store.getState())).toBe("Network timeout");
    });

    it("should handle non-Error rejection during switch", async () => {
      mockFetchHelper.mock.mockRejectedValueOnce("Unknown error");

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
});
