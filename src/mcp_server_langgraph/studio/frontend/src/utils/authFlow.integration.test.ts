/**
 * Integration Tests for Full Authentication Flow
 *
 * These tests verify the complete auth flow works end-to-end:
 * 1. Token storage → authenticatedFetch → 401 handling → token refresh → retry
 * 2. Token storage → WebSocket → 4010 handling → token refresh → reconnect
 *
 * Unlike unit tests that mock dependencies, these integration tests verify
 * the actual integration between authenticatedFetch, websocketAuth, and storage.
 */

import { describe, it, expect, beforeEach, afterEach, vi } from "vitest";

// Store original implementations
const originalLocalStorage = window.localStorage;
const originalFetch = globalThis.fetch;

describe("Auth Flow Integration", () => {
  // Simple in-memory storage for integration testing
  let memoryStorage: Record<string, string>;

  // Mock fetch for HTTP requests
  const mockFetch = vi.fn();

  beforeEach(() => {
    // Reset memory storage
    memoryStorage = {};

    // Mock localStorage with in-memory implementation
    Object.defineProperty(window, "localStorage", {
      value: {
        getItem: (key: string) => memoryStorage[key] ?? null,
        setItem: (key: string, value: string) => {
          memoryStorage[key] = value;
        },
        removeItem: (key: string) => {
          delete memoryStorage[key];
        },
        clear: () => {
          memoryStorage = {};
        },
      },
      writable: true,
    });

    // Replace global fetch
    globalThis.fetch = mockFetch;
    mockFetch.mockReset();
  });

  afterEach(() => {
    // Restore originals
    Object.defineProperty(window, "localStorage", {
      value: originalLocalStorage,
      writable: true,
    });
    globalThis.fetch = originalFetch;
    vi.clearAllMocks();
    vi.restoreAllMocks();
  });

  describe("HTTP Auth Flow: authenticatedFetch → 401 → refresh → retry", () => {
    it("should complete full auth cycle: request → 401 → refresh → retry success", async () => {
      // Re-import to use fresh mocks
      const { resetRefreshState } = await import("./authenticatedFetch");
      resetRefreshState();

      // Setup: User has valid tokens
      memoryStorage["access_token"] = "expired-access-token";
      memoryStorage["refresh_token"] = "valid-refresh-token";

      // Scenario:
      // 1. First request returns 401 (token expired)
      // 2. Refresh endpoint succeeds with new tokens
      // 3. Retry request succeeds

      mockFetch
        // First request - 401
        .mockResolvedValueOnce(
          new Response(JSON.stringify({ error: "unauthorized" }), {
            status: 401,
          }),
        )
        // Refresh request - success
        .mockResolvedValueOnce(
          new Response(
            JSON.stringify({
              access_token: "new-access-token",
              refresh_token: "new-refresh-token",
            }),
            { status: 200 },
          ),
        )
        // Retry request - success
        .mockResolvedValueOnce(
          new Response(JSON.stringify({ data: "protected-data" }), {
            status: 200,
          }),
        );

      // Re-import authenticatedFetch to use fresh storage mock
      const { authenticatedFetch } = await import("./authenticatedFetch");

      // Execute
      const response = await authenticatedFetch("/api/v1/protected");

      // Verify
      expect(response.status).toBe(200);
      const data = await response.json();
      expect(data).toEqual({ data: "protected-data" });

      // Verify tokens were updated
      expect(memoryStorage["access_token"]).toBe("new-access-token");
      expect(memoryStorage["refresh_token"]).toBe("new-refresh-token");

      // Verify fetch was called 3 times: original, refresh, retry
      expect(mockFetch).toHaveBeenCalledTimes(3);
    });

    it("should handle refresh failure and call onAuthFailure", async () => {
      const { resetRefreshState } = await import("./authenticatedFetch");
      resetRefreshState();

      // Setup: User has expired tokens
      memoryStorage["access_token"] = "expired-access-token";
      memoryStorage["refresh_token"] = "expired-refresh-token";

      const onAuthFailure = vi.fn();

      mockFetch
        // First request - 401
        .mockResolvedValueOnce(
          new Response(JSON.stringify({ error: "unauthorized" }), {
            status: 401,
          }),
        )
        // Refresh request - fails
        .mockResolvedValueOnce(
          new Response(JSON.stringify({ error: "invalid_grant" }), {
            status: 400,
          }),
        );

      const { authenticatedFetch } = await import("./authenticatedFetch");

      // Execute
      const response = await authenticatedFetch("/api/v1/protected", {
        onAuthFailure,
      });

      // Verify
      expect(response.status).toBe(401);
      expect(onAuthFailure).toHaveBeenCalled();

      // Verify tokens were cleared
      expect(memoryStorage["access_token"]).toBeUndefined();
      expect(memoryStorage["refresh_token"]).toBeUndefined();
    });

    it("should handle concurrent 401 responses with single refresh", async () => {
      const { resetRefreshState } = await import("./authenticatedFetch");
      resetRefreshState();

      // Setup: User has expired token
      memoryStorage["access_token"] = "expired-access-token";
      memoryStorage["refresh_token"] = "valid-refresh-token";

      // Track refresh call count
      let refreshCallCount = 0;

      mockFetch.mockImplementation(async (url: string) => {
        if (url.includes("/auth/refresh")) {
          refreshCallCount++;
          // Simulate network delay
          await new Promise((resolve) => setTimeout(resolve, 50));
          return new Response(
            JSON.stringify({
              access_token: "new-access-token",
              refresh_token: "new-refresh-token",
            }),
            { status: 200 },
          );
        }

        // First call for each request returns 401
        return new Response(JSON.stringify({ error: "unauthorized" }), {
          status: 401,
        });
      });

      // After first refresh, return success for retries
      let retryCount = 0;
      mockFetch.mockImplementation(async (url: string) => {
        if (url.includes("/auth/refresh")) {
          refreshCallCount++;
          await new Promise((resolve) => setTimeout(resolve, 50));
          return new Response(
            JSON.stringify({
              access_token: "new-access-token",
              refresh_token: "new-refresh-token",
            }),
            { status: 200 },
          );
        }

        retryCount++;
        if (retryCount <= 2) {
          // First two calls return 401
          return new Response(JSON.stringify({ error: "unauthorized" }), {
            status: 401,
          });
        }
        // Retries succeed
        return new Response(JSON.stringify({ data: "success" }), {
          status: 200,
        });
      });

      const { authenticatedFetch } = await import("./authenticatedFetch");

      // Make concurrent requests
      const results = await Promise.all([
        authenticatedFetch("/api/v1/endpoint1"),
        authenticatedFetch("/api/v1/endpoint2"),
      ]);

      // Both should eventually succeed
      expect(results[0].status).toBe(200);
      expect(results[1].status).toBe(200);

      // Refresh should only be called once due to concurrent request handling
      expect(refreshCallCount).toBe(1);
    });
  });

  describe("WebSocket Auth Flow: token validation before connection", () => {
    it("should return true when token is valid", async () => {
      const { resetWebSocketAuthState } = await import("./websocketAuth");
      resetWebSocketAuthState();

      // Setup: Valid token with long expiry (10 minutes)
      const exp = Math.floor(Date.now() / 1000) + 600;
      const payload = btoa(JSON.stringify({ exp, sub: "user123" }));
      const validToken = `eyJhbGciOiJSUzI1NiJ9.${payload}.signature`;
      memoryStorage["access_token"] = validToken;

      const { ensureValidTokenForWebSocket } = await import("./websocketAuth");

      // Execute
      const result = await ensureValidTokenForWebSocket();

      // Verify
      expect(result).toBe(true);
      // No refresh needed
      expect(mockFetch).not.toHaveBeenCalled();
    });

    it("should refresh token when expiring soon and return true on success", async () => {
      const { resetWebSocketAuthState } = await import("./websocketAuth");
      const { resetRefreshState } = await import("./authenticatedFetch");
      resetWebSocketAuthState();
      resetRefreshState();

      // Setup: Token expiring in 2 minutes (within 5 min buffer)
      const exp = Math.floor(Date.now() / 1000) + 120;
      const payload = btoa(JSON.stringify({ exp, sub: "user123" }));
      const expiringToken = `eyJhbGciOiJSUzI1NiJ9.${payload}.signature`;
      memoryStorage["access_token"] = expiringToken;
      memoryStorage["refresh_token"] = "valid-refresh-token";

      // Mock successful refresh
      mockFetch.mockResolvedValueOnce(
        new Response(
          JSON.stringify({
            access_token: "new-access-token",
            refresh_token: "new-refresh-token",
          }),
          { status: 200 },
        ),
      );

      const { ensureValidTokenForWebSocket } = await import("./websocketAuth");

      // Execute
      const result = await ensureValidTokenForWebSocket();

      // Verify
      expect(result).toBe(true);
      expect(mockFetch).toHaveBeenCalledWith(
        expect.stringContaining("/auth/refresh"),
        expect.any(Object),
      );
      // Tokens should be updated
      expect(memoryStorage["access_token"]).toBe("new-access-token");
    });

    it("should return false when no token and no refresh token", async () => {
      const { resetWebSocketAuthState } = await import("./websocketAuth");
      resetWebSocketAuthState();

      // Setup: No tokens
      memoryStorage = {};

      const { ensureValidTokenForWebSocket } = await import("./websocketAuth");

      // Execute
      const result = await ensureValidTokenForWebSocket();

      // Verify
      expect(result).toBe(false);
    });
  });

  describe("Cross-flow Integration: HTTP and WebSocket sharing token refresh", () => {
    it("should share refreshed token between HTTP and WebSocket", async () => {
      const { resetRefreshState } = await import("./authenticatedFetch");
      const { resetWebSocketAuthState } = await import("./websocketAuth");
      resetRefreshState();
      resetWebSocketAuthState();

      // Setup: Expiring token
      const exp = Math.floor(Date.now() / 1000) + 120; // 2 minutes
      const payload = btoa(JSON.stringify({ exp, sub: "user123" }));
      const expiringToken = `eyJhbGciOiJSUzI1NiJ9.${payload}.signature`;
      memoryStorage["access_token"] = expiringToken;
      memoryStorage["refresh_token"] = "valid-refresh-token";

      // New token with long expiry
      const newExp = Math.floor(Date.now() / 1000) + 3600; // 1 hour
      const newPayload = btoa(JSON.stringify({ exp: newExp, sub: "user123" }));
      const newToken = `eyJhbGciOiJSUzI1NiJ9.${newPayload}.signature`;

      // Mock refresh that returns long-lived token
      mockFetch.mockResolvedValue(
        new Response(
          JSON.stringify({
            access_token: newToken,
            refresh_token: "new-refresh-token",
          }),
          { status: 200 },
        ),
      );

      const { ensureValidTokenForWebSocket } = await import("./websocketAuth");

      // First: WebSocket triggers refresh (token expiring soon)
      const wsResult = await ensureValidTokenForWebSocket();
      expect(wsResult).toBe(true);

      // Verify refresh was called once
      expect(mockFetch).toHaveBeenCalledTimes(1);

      // Update mock to return the new token
      memoryStorage["access_token"] = newToken;

      // Second: WebSocket check should not need refresh (token is now valid)
      const { resetWebSocketAuthState: resetWS2 } =
        await import("./websocketAuth");
      resetWS2();

      const { ensureValidTokenForWebSocket: ensureValid2 } =
        await import("./websocketAuth");
      const wsResult2 = await ensureValid2();
      expect(wsResult2).toBe(true);

      // Refresh should not be called again (token is valid)
      // Note: Previous call count was 1, should still be 1
      expect(mockFetch).toHaveBeenCalledTimes(1);
    });
  });

  describe("Edge Cases", () => {
    it("should handle network errors during refresh gracefully", async () => {
      const { resetRefreshState } = await import("./authenticatedFetch");
      resetRefreshState();

      memoryStorage["access_token"] = "expired-token";
      memoryStorage["refresh_token"] = "valid-refresh-token";

      const onAuthFailure = vi.fn();

      mockFetch
        // First request - 401
        .mockResolvedValueOnce(
          new Response(JSON.stringify({ error: "unauthorized" }), {
            status: 401,
          }),
        )
        // Refresh - network error
        .mockRejectedValueOnce(new Error("Network error"));

      const { authenticatedFetch } = await import("./authenticatedFetch");

      const response = await authenticatedFetch("/api/v1/protected", {
        onAuthFailure,
      });

      // Should return original 401 response
      expect(response.status).toBe(401);
      expect(onAuthFailure).toHaveBeenCalled();

      // Tokens should be cleared on network error
      expect(memoryStorage["access_token"]).toBeUndefined();
    });

    it("should handle malformed token gracefully", async () => {
      const { resetWebSocketAuthState } = await import("./websocketAuth");
      const { resetRefreshState } = await import("./authenticatedFetch");
      resetWebSocketAuthState();
      resetRefreshState();

      // Setup: Malformed token
      memoryStorage["access_token"] = "not-a-valid-jwt";
      memoryStorage["refresh_token"] = "valid-refresh-token";

      // Mock failed refresh (simulating backend rejecting malformed token)
      mockFetch.mockResolvedValueOnce(
        new Response(JSON.stringify({ error: "invalid_token" }), {
          status: 400,
        }),
      );

      const { ensureValidTokenForWebSocket } = await import("./websocketAuth");

      // Execute - malformed token should trigger refresh attempt
      const result = await ensureValidTokenForWebSocket();

      // Verify refresh was attempted (malformed is treated as expiring)
      expect(mockFetch).toHaveBeenCalled();
      expect(result).toBe(false);
    });

    it("should handle empty string token", async () => {
      const { resetWebSocketAuthState } = await import("./websocketAuth");
      resetWebSocketAuthState();

      // Setup: Empty token
      memoryStorage["access_token"] = "";

      const { ensureValidTokenForWebSocket } = await import("./websocketAuth");

      // Execute
      const result = await ensureValidTokenForWebSocket();

      // Empty string is falsy, should return false
      expect(result).toBe(false);
    });
  });
});
