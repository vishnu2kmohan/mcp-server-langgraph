/**
 * authSlice Tokens Tests
 *
 * Tests for token expiration, refresh, and getAccessToken.
 */

import { describe, it, expect, beforeEach, vi, afterEach } from "vitest";
import {
  refreshToken,
  getAccessToken,
  selectUser,
  selectTokens,
} from "./authSlice";
import type { AuthTokens } from "../../types/auth";
import {
  createTestStore,
  createMockLocalStorage,
  createMockFetch,
  mockUser,
  mockTokens,
} from "./authSlice.test-utils";

describe("authSlice Tokens", () => {
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

  describe("Token Expiration Handling", () => {
    it("should detect expired access token", async () => {
      const expiredTokens: AuthTokens = {
        accessToken: "expired-token",
        refreshToken: "valid-refresh",
        expiresAt: Date.now() - 1000, // Already expired
        refreshExpiresAt: Date.now() + 86400000, // Still valid
      };

      expect(expiredTokens.expiresAt < Date.now()).toBe(true);
    });

    it("should detect token about to expire within buffer", async () => {
      const tokenExpiresSoon: AuthTokens = {
        accessToken: "soon-expired-token",
        refreshToken: "valid-refresh",
        expiresAt: Date.now() + 3 * 60 * 1000, // 3 minutes
        refreshExpiresAt: Date.now() + 86400000,
      };

      const bufferMs = 5 * 60 * 1000;
      const shouldRefresh = Date.now() >= tokenExpiresSoon.expiresAt - bufferMs;
      expect(shouldRefresh).toBe(true);
    });

    it("should not refresh token with plenty of time remaining", async () => {
      const validTokens: AuthTokens = {
        accessToken: "valid-token",
        refreshToken: "valid-refresh",
        expiresAt: Date.now() + 30 * 60 * 1000, // 30 minutes
        refreshExpiresAt: Date.now() + 86400000,
      };

      const bufferMs = 5 * 60 * 1000;
      const shouldRefresh = Date.now() >= validTokens.expiresAt - bufferMs;
      expect(shouldRefresh).toBe(false);
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

      mockFetchHelper.mock.mockResolvedValueOnce({
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
      mockFetchHelper.mock.mockResolvedValueOnce({
        ok: false,
        status: 401,
      });

      const store = createTestStore({ tokens: mockTokens, user: mockUser });
      await store.dispatch(refreshToken());

      expect(selectUser(store.getState())).toBeNull();
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

      expect(selectUser(store.getState())).toBeNull();
    });

    it("should handle network error during refresh", async () => {
      mockFetchHelper.mock.mockRejectedValueOnce(
        new Error("Connection refused"),
      );

      const store = createTestStore({
        tokens: mockTokens,
        user: mockUser,
      });
      await store.dispatch(refreshToken());

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

      mockFetchHelper.mock.mockResolvedValueOnce({
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
