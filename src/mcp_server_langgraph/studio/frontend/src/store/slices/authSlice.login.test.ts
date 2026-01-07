/**
 * authSlice Login Tests
 *
 * Tests for login async thunk and error handling.
 */

import { describe, it, expect, beforeEach, vi, afterEach } from "vitest";
import {
  login,
  selectUser,
  selectIsLoading,
  selectAuthError,
  selectOrganizations,
  selectCurrentOrg,
} from "./authSlice";
import {
  createTestStore,
  createMockLocalStorage,
  createMockFetch,
  mockTokens,
  mockOrg,
} from "./authSlice.test-utils";

describe("authSlice Login", () => {
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

  describe("login async thunk", () => {
    it("should set loading state when pending", async () => {
      mockFetchHelper.mock.mockImplementation(() => new Promise(() => {})); // Never resolves

      const store = createTestStore();
      store.dispatch(login({ username: "test", password: "password" }));

      expect(selectIsLoading(store.getState())).toBe(true);
    });

    it("should set user on successful login", async () => {
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
      mockFetchHelper.mock.mockResolvedValueOnce({
        ok: false,
        json: () => Promise.resolve({ detail: "Invalid credentials" }),
      });

      const store = createTestStore();
      await store.dispatch(login({ username: "test", password: "wrong" }));

      expect(selectAuthError(store.getState())).toBe("Invalid credentials");
      expect(selectUser(store.getState())).toBeNull();
    });

    it("should set organizations on successful login", async () => {
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

  describe("login async thunk error handling", () => {
    it("should handle network error (Error instance)", async () => {
      mockFetchHelper.mock.mockRejectedValueOnce(new Error("Network failure"));

      const store = createTestStore();
      await store.dispatch(login({ username: "test", password: "password" }));

      expect(selectAuthError(store.getState())).toBe("Network failure");
      expect(selectUser(store.getState())).toBeNull();
      expect(selectIsLoading(store.getState())).toBe(false);
    });

    it("should handle non-Error rejection with default message", async () => {
      mockFetchHelper.mock.mockRejectedValueOnce("String error");

      const store = createTestStore();
      await store.dispatch(login({ username: "test", password: "password" }));

      expect(selectAuthError(store.getState())).toBe("Login failed");
    });

    it("should handle empty organizations in response", async () => {
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

  describe("login.rejected default error", () => {
    it("should use default error message when no detail provided", async () => {
      mockFetchHelper.mock.mockResolvedValueOnce({
        ok: false,
        json: () => Promise.resolve({}), // No detail field
      });

      const store = createTestStore();
      await store.dispatch(login({ username: "test", password: "password" }));

      expect(selectAuthError(store.getState())).toBe("Login failed");
    });
  });
});
