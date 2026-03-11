/**
 * Tests for authenticatedFetch utility
 *
 * TDD: These tests define the expected behavior for a fetch wrapper that:
 * 1. Adds Authorization header with access token
 * 2. Handles 401 by attempting token refresh
 * 3. Retries original request if refresh succeeds
 * 4. Redirects to login if refresh fails
 *
 * Used by non-RTK Query code (useStreamingChat, loaders, etc.)
 */

import { describe, it, expect, beforeEach, afterEach, vi } from "vitest";

// Mock dependencies before importing the module under test
vi.mock("react-router", async () => {
  const actual = await vi.importActual("react-router");
  return {
    ...actual,
  };
});

// Mock storage
const mockGetAuthToken = vi.fn();
const mockSetAuthTokens = vi.fn();
const mockClearAuthTokens = vi.fn();
vi.mock("./storage", async () => {
  const actual = await vi.importActual("./storage");
  return {
    ...actual,
    getAuthToken: () => mockGetAuthToken(),
    setAuthTokens: (...args: unknown[]) => mockSetAuthTokens(...args),
    clearAuthTokens: () => mockClearAuthTokens(),
    storage: {
      get: vi.fn(),
    },
    STORAGE_KEYS: {
      REFRESH_TOKEN: "refresh_token",
    },
  };
});
// Mock intendedRoute
const mockSetIntendedRoute = vi.fn();
vi.mock("./intendedRoute", () => ({
  setIntendedRoute: (route: string) => mockSetIntendedRoute(route),
}));

import {
  authenticatedFetch,
  refreshAccessToken,
  resetRefreshState,
} from "./authenticatedFetch";

describe("authenticatedFetch", () => {
  let originalFetch: typeof globalThis.fetch;
  const mockFetch = vi.fn<Parameters<typeof fetch>, ReturnType<typeof fetch>>();

  beforeEach(() => {
    vi.clearAllMocks();
    originalFetch = globalThis.fetch;
    globalThis.fetch = mockFetch;
    localStorage.clear();

    // Default: user is authenticated
    mockGetAuthToken.mockReturnValue("valid-access-token");

    // Reset refresh state between tests
    resetRefreshState();
  });

  afterEach(() => {
    globalThis.fetch = originalFetch;
    localStorage.clear();
  });

  describe("successful requests", () => {
    it("should add Authorization header with access token", async () => {
      mockFetch.mockResolvedValueOnce(
        new Response(JSON.stringify({ data: "test" }), { status: 200 }),
      );

      await authenticatedFetch("/api/v1/test");

      expect(mockFetch).toHaveBeenCalledWith(
        "/api/v1/test",
        expect.objectContaining({
          headers: expect.any(Headers),
        }),
      );

      const [, options] = mockFetch.mock.calls[0]!;
      const headers = (options as RequestInit).headers as Headers;
      expect(headers.get("Authorization")).toBe("Bearer valid-access-token");
    });

    it("should preserve existing headers", async () => {
      mockFetch.mockResolvedValueOnce(
        new Response(JSON.stringify({ data: "test" }), { status: 200 }),
      );

      await authenticatedFetch("/api/v1/test", {
        headers: {
          "Content-Type": "application/json",
          "X-Custom-Header": "custom-value",
        },
      });

      const [, options] = mockFetch.mock.calls[0]!;
      const headers = (options as RequestInit).headers as Headers;
      expect(headers.get("Authorization")).toBe("Bearer valid-access-token");
      expect(headers.get("Content-Type")).toBe("application/json");
      expect(headers.get("X-Custom-Header")).toBe("custom-value");
    });

    it("should return the response on success", async () => {
      const responseData = { data: "test" };
      mockFetch.mockResolvedValueOnce(
        new Response(JSON.stringify(responseData), { status: 200 }),
      );

      const response = await authenticatedFetch("/api/v1/test");

      expect(response.status).toBe(200);
      expect(await response.json()).toEqual(responseData);
    });
  });

  describe("when no access token is available", () => {
    it("should still make the request (let server handle auth)", async () => {
      mockGetAuthToken.mockReturnValue(null);
      mockFetch.mockResolvedValueOnce(
        new Response(JSON.stringify({ error: "unauthorized" }), {
          status: 401,
        }),
      );

      const response = await authenticatedFetch("/api/v1/test");

      expect(response.status).toBe(401);
    });
  });

  describe("401 handling with token refresh", () => {
    it("should attempt token refresh on 401", async () => {
      // First call returns 401
      mockFetch.mockResolvedValueOnce(
        new Response(JSON.stringify({ error: "unauthorized" }), {
          status: 401,
        }),
      );

      // Refresh call succeeds
      localStorage.setItem("refresh_token", "valid-refresh-token");
      mockFetch.mockResolvedValueOnce(
        new Response(
          JSON.stringify({
            access_token: "new-access-token",
            refresh_token: "new-refresh-token",
          }),
          { status: 200 },
        ),
      );

      // Retry succeeds
      mockFetch.mockResolvedValueOnce(
        new Response(JSON.stringify({ data: "success" }), { status: 200 }),
      );

      // Update mock to return new token after refresh
      mockGetAuthToken.mockReturnValue("new-access-token");

      const response = await authenticatedFetch("/api/v1/test");

      expect(mockFetch).toHaveBeenCalledTimes(3);
      expect(response.status).toBe(200);
    });

    it("should retry original request after successful refresh", async () => {
      // First call returns 401
      mockFetch.mockResolvedValueOnce(
        new Response(JSON.stringify({ error: "unauthorized" }), {
          status: 401,
        }),
      );

      // Refresh succeeds
      localStorage.setItem("refresh_token", "valid-refresh-token");
      mockFetch.mockResolvedValueOnce(
        new Response(
          JSON.stringify({
            access_token: "new-access-token",
            refresh_token: "new-refresh-token",
          }),
          { status: 200 },
        ),
      );

      // Retry succeeds
      mockFetch.mockResolvedValueOnce(
        new Response(JSON.stringify({ data: "success after retry" }), {
          status: 200,
        }),
      );

      mockGetAuthToken.mockReturnValue("new-access-token");

      const response = await authenticatedFetch("/api/v1/test");

      expect(response.status).toBe(200);
      const data = await response.json();
      expect(data).toEqual({ data: "success after retry" });
    });

    it("should update tokens in storage after refresh", async () => {
      // First call returns 401
      mockFetch.mockResolvedValueOnce(
        new Response(JSON.stringify({ error: "unauthorized" }), {
          status: 401,
        }),
      );

      // Refresh succeeds
      localStorage.setItem("refresh_token", "valid-refresh-token");
      mockFetch.mockResolvedValueOnce(
        new Response(
          JSON.stringify({
            access_token: "new-access-token",
            refresh_token: "new-refresh-token",
          }),
          { status: 200 },
        ),
      );

      // Retry succeeds
      mockFetch.mockResolvedValueOnce(
        new Response(JSON.stringify({ data: "success" }), { status: 200 }),
      );

      mockGetAuthToken.mockReturnValue("new-access-token");

      await authenticatedFetch("/api/v1/test");

      expect(mockSetAuthTokens).toHaveBeenCalledWith(
        "new-access-token",
        "new-refresh-token",
      );
    });

    it("should prevent concurrent refresh attempts", async () => {
      // Set up refresh token
      localStorage.setItem("refresh_token", "valid-refresh-token");

      // First request returns 401
      mockFetch.mockResolvedValueOnce(
        new Response(JSON.stringify({ error: "unauthorized" }), {
          status: 401,
        }),
      );

      // Second request also returns 401
      mockFetch.mockResolvedValueOnce(
        new Response(JSON.stringify({ error: "unauthorized" }), {
          status: 401,
        }),
      );

      // Refresh succeeds (only called once)
      mockFetch.mockResolvedValueOnce(
        new Response(
          JSON.stringify({
            access_token: "new-access-token",
          }),
          { status: 200 },
        ),
      );

      // Both retries succeed
      mockFetch.mockResolvedValueOnce(
        new Response(JSON.stringify({ data: "result1" }), { status: 200 }),
      );
      mockFetch.mockResolvedValueOnce(
        new Response(JSON.stringify({ data: "result2" }), { status: 200 }),
      );

      mockGetAuthToken.mockReturnValue("new-access-token");

      // Make concurrent requests
      const [response1, response2] = await Promise.all([
        authenticatedFetch("/api/v1/test1"),
        authenticatedFetch("/api/v1/test2"),
      ]);

      expect(response1.status).toBe(200);
      expect(response2.status).toBe(200);
    });
  });

  describe("redirect to login on auth failure", () => {
    it("should call onAuthFailure when no refresh token available", async () => {
      const onAuthFailure = vi.fn();

      mockFetch.mockResolvedValueOnce(
        new Response(JSON.stringify({ error: "unauthorized" }), {
          status: 401,
        }),
      );

      // No refresh token available
      localStorage.removeItem("refresh_token");

      const response = await authenticatedFetch("/api/v1/test", {
        onAuthFailure,
      });

      expect(response.status).toBe(401);
      expect(onAuthFailure).toHaveBeenCalled();
    });

    it("should call onAuthFailure when refresh fails", async () => {
      const onAuthFailure = vi.fn();

      // First call returns 401
      mockFetch.mockResolvedValueOnce(
        new Response(JSON.stringify({ error: "unauthorized" }), {
          status: 401,
        }),
      );

      // Refresh fails
      localStorage.setItem("refresh_token", "expired-refresh-token");
      mockFetch.mockResolvedValueOnce(
        new Response(JSON.stringify({ error: "invalid_grant" }), {
          status: 400,
        }),
      );

      const response = await authenticatedFetch("/api/v1/test", {
        onAuthFailure,
      });

      expect(response.status).toBe(401);
      expect(onAuthFailure).toHaveBeenCalled();
    });

    it("should clear tokens on refresh failure", async () => {
      // First call returns 401
      mockFetch.mockResolvedValueOnce(
        new Response(JSON.stringify({ error: "unauthorized" }), {
          status: 401,
        }),
      );

      // Refresh fails
      localStorage.setItem("refresh_token", "expired-refresh-token");
      mockFetch.mockResolvedValueOnce(
        new Response(JSON.stringify({ error: "invalid_grant" }), {
          status: 400,
        }),
      );

      await authenticatedFetch("/api/v1/test");

      expect(mockClearAuthTokens).toHaveBeenCalled();
    });
  });

  describe("skipAuth option", () => {
    it("should skip adding Authorization header when skipAuth is true", async () => {
      mockFetch.mockResolvedValueOnce(
        new Response(JSON.stringify({ data: "public" }), { status: 200 }),
      );

      await authenticatedFetch("/api/v1/public", { skipAuth: true });

      const [, options] = mockFetch.mock.calls[0]!;
      const headers = (options as RequestInit).headers as Headers;
      expect(headers.get("Authorization")).toBeNull();
    });

    it("should not attempt refresh on 401 when skipAuth is true", async () => {
      mockFetch.mockResolvedValueOnce(
        new Response(JSON.stringify({ error: "unauthorized" }), {
          status: 401,
        }),
      );

      localStorage.setItem("refresh_token", "valid-refresh-token");

      const response = await authenticatedFetch("/api/v1/public", {
        skipAuth: true,
      });

      expect(response.status).toBe(401);
      expect(mockFetch).toHaveBeenCalledTimes(1); // No refresh attempt
    });
  });
});

describe("refreshAccessToken", () => {
  let originalFetch: typeof globalThis.fetch;
  const mockFetch = vi.fn<Parameters<typeof fetch>, ReturnType<typeof fetch>>();

  beforeEach(() => {
    vi.clearAllMocks();
    originalFetch = globalThis.fetch;
    globalThis.fetch = mockFetch;
    localStorage.clear();
    resetRefreshState();
  });

  afterEach(() => {
    globalThis.fetch = originalFetch;
    localStorage.clear();
  });

  it("should return false when no refresh token exists", async () => {
    const result = await refreshAccessToken();

    expect(result).toBe(false);
    expect(mockFetch).not.toHaveBeenCalled();
  });

  it("should call refresh endpoint with refresh token", async () => {
    localStorage.setItem("refresh_token", "test-refresh-token");

    mockFetch.mockResolvedValueOnce(
      new Response(
        JSON.stringify({
          access_token: "new-access-token",
          refresh_token: "new-refresh-token",
        }),
        { status: 200 },
      ),
    );

    await refreshAccessToken();

    expect(mockFetch).toHaveBeenCalledWith(
      expect.stringContaining("/auth/refresh"),
      expect.objectContaining({
        method: "POST",
        body: JSON.stringify({ refresh_token: "test-refresh-token" }),
      }),
    );
  });

  it("should return true on successful refresh", async () => {
    localStorage.setItem("refresh_token", "valid-refresh-token");

    mockFetch.mockResolvedValueOnce(
      new Response(
        JSON.stringify({
          access_token: "new-access-token",
        }),
        { status: 200 },
      ),
    );

    const result = await refreshAccessToken();

    expect(result).toBe(true);
    expect(mockSetAuthTokens).toHaveBeenCalled();
  });

  it("should return false on refresh failure", async () => {
    localStorage.setItem("refresh_token", "expired-token");

    mockFetch.mockResolvedValueOnce(
      new Response(JSON.stringify({ error: "invalid_grant" }), { status: 400 }),
    );

    const result = await refreshAccessToken();

    expect(result).toBe(false);
    expect(mockClearAuthTokens).toHaveBeenCalled();
  });
});
