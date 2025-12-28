/**
 * Tests for WebSocket Authentication Utility
 *
 * TDD: These tests define the expected behavior for WebSocket token handling:
 * 1. Check if token is valid before connecting
 * 2. Refresh token if expiring soon (within 5 min buffer)
 * 3. Provide close code constant for token expiration (4010)
 *
 * Used by WebSocket hooks to ensure fresh token before (re)connection.
 */

import { describe, it, expect, beforeEach, afterEach, vi } from "vitest";

// Mock storage
const mockGetAuthToken = vi.fn();
const _mockGetRefreshToken = vi.fn();
vi.mock("./storage", () => ({
  getAuthToken: () => mockGetAuthToken(),
  STORAGE_KEYS: {
    REFRESH_TOKEN: "refresh_token",
  },
}));

// Mock authenticatedFetch's refreshAccessToken
const mockRefreshAccessToken = vi.fn();
vi.mock("./authenticatedFetch", () => ({
  refreshAccessToken: () => mockRefreshAccessToken(),
  resetRefreshState: vi.fn(),
}));

import {
  WS_CLOSE_TOKEN_EXPIRED,
  isTokenExpiringSoon,
  ensureValidTokenForWebSocket,
  resetWebSocketAuthState,
} from "./websocketAuth";

describe("WS_CLOSE_TOKEN_EXPIRED constant", () => {
  it("should be 4010", () => {
    expect(WS_CLOSE_TOKEN_EXPIRED).toBe(4010);
  });
});

describe("isTokenExpiringSoon", () => {
  it("should return true for token expiring within buffer", () => {
    // Create JWT with exp 2 minutes from now (within 5 min buffer)
    const exp = Math.floor(Date.now() / 1000) + 120; // 2 minutes
    const payload = btoa(JSON.stringify({ exp }));
    const token = `header.${payload}.signature`;

    const result = isTokenExpiringSoon(token);

    expect(result).toBe(true);
  });

  it("should return false for token expiring outside buffer", () => {
    // Create JWT with exp 10 minutes from now (outside 5 min buffer)
    const exp = Math.floor(Date.now() / 1000) + 600; // 10 minutes
    const payload = btoa(JSON.stringify({ exp }));
    const token = `header.${payload}.signature`;

    const result = isTokenExpiringSoon(token);

    expect(result).toBe(false);
  });

  it("should return true for already expired token", () => {
    // Create JWT that expired 5 minutes ago
    const exp = Math.floor(Date.now() / 1000) - 300; // -5 minutes
    const payload = btoa(JSON.stringify({ exp }));
    const token = `header.${payload}.signature`;

    const result = isTokenExpiringSoon(token);

    expect(result).toBe(true);
  });

  it("should return true for invalid token", () => {
    const result = isTokenExpiringSoon("invalid-token");

    expect(result).toBe(true);
  });

  it("should return true for token without exp claim", () => {
    const payload = btoa(JSON.stringify({ sub: "user123" }));
    const token = `header.${payload}.signature`;

    const result = isTokenExpiringSoon(token);

    expect(result).toBe(true);
  });

  it("should handle custom buffer seconds", () => {
    // Token expires in 8 minutes
    const exp = Math.floor(Date.now() / 1000) + 480; // 8 minutes
    const payload = btoa(JSON.stringify({ exp }));
    const token = `header.${payload}.signature`;

    // With 5 min buffer (default) - should return false
    expect(isTokenExpiringSoon(token)).toBe(false);

    // With 10 min buffer - should return true
    expect(isTokenExpiringSoon(token, 600)).toBe(true);
  });
});

describe("ensureValidTokenForWebSocket", () => {
  beforeEach(() => {
    vi.clearAllMocks();
    resetWebSocketAuthState();
  });

  afterEach(() => {
    vi.clearAllMocks();
  });

  it("should return true when token is valid and not expiring soon", async () => {
    // Token expires in 10 minutes (valid)
    const exp = Math.floor(Date.now() / 1000) + 600;
    const payload = btoa(JSON.stringify({ exp }));
    const token = `header.${payload}.signature`;

    mockGetAuthToken.mockReturnValue(token);

    const result = await ensureValidTokenForWebSocket();

    expect(result).toBe(true);
    expect(mockRefreshAccessToken).not.toHaveBeenCalled();
  });

  it("should return false when no token exists", async () => {
    mockGetAuthToken.mockReturnValue(null);

    const result = await ensureValidTokenForWebSocket();

    expect(result).toBe(false);
    expect(mockRefreshAccessToken).not.toHaveBeenCalled();
  });

  it("should refresh token when expiring soon and return true on success", async () => {
    // Token expires in 2 minutes (expiring soon)
    const exp = Math.floor(Date.now() / 1000) + 120;
    const payload = btoa(JSON.stringify({ exp }));
    const token = `header.${payload}.signature`;

    mockGetAuthToken.mockReturnValue(token);
    mockRefreshAccessToken.mockResolvedValue(true);

    const result = await ensureValidTokenForWebSocket();

    expect(result).toBe(true);
    expect(mockRefreshAccessToken).toHaveBeenCalledTimes(1);
  });

  it("should return false when token is expiring soon and refresh fails", async () => {
    // Token expires in 2 minutes (expiring soon)
    const exp = Math.floor(Date.now() / 1000) + 120;
    const payload = btoa(JSON.stringify({ exp }));
    const token = `header.${payload}.signature`;

    mockGetAuthToken.mockReturnValue(token);
    mockRefreshAccessToken.mockResolvedValue(false);

    const result = await ensureValidTokenForWebSocket();

    expect(result).toBe(false);
    expect(mockRefreshAccessToken).toHaveBeenCalledTimes(1);
  });

  it("should return false when token is already expired and refresh fails", async () => {
    // Token expired 5 minutes ago
    const exp = Math.floor(Date.now() / 1000) - 300;
    const payload = btoa(JSON.stringify({ exp }));
    const token = `header.${payload}.signature`;

    mockGetAuthToken.mockReturnValue(token);
    mockRefreshAccessToken.mockResolvedValue(false);

    const result = await ensureValidTokenForWebSocket();

    expect(result).toBe(false);
    expect(mockRefreshAccessToken).toHaveBeenCalledTimes(1);
  });

  it("should prevent concurrent refresh attempts", async () => {
    // Token expires in 2 minutes (expiring soon)
    const exp = Math.floor(Date.now() / 1000) + 120;
    const payload = btoa(JSON.stringify({ exp }));
    const token = `header.${payload}.signature`;

    mockGetAuthToken.mockReturnValue(token);

    // Simulate slow refresh
    mockRefreshAccessToken.mockImplementation(
      () => new Promise((resolve) => setTimeout(() => resolve(true), 100)),
    );

    // Make concurrent calls
    const [result1, result2] = await Promise.all([
      ensureValidTokenForWebSocket(),
      ensureValidTokenForWebSocket(),
    ]);

    expect(result1).toBe(true);
    expect(result2).toBe(true);
    // Should only have called refresh once
    expect(mockRefreshAccessToken).toHaveBeenCalledTimes(1);
  });

  it("should return false for invalid token format", async () => {
    mockGetAuthToken.mockReturnValue("invalid-token");
    mockRefreshAccessToken.mockResolvedValue(false);

    const result = await ensureValidTokenForWebSocket();

    // Invalid token is treated as expiring, so should attempt refresh
    expect(mockRefreshAccessToken).toHaveBeenCalled();
    expect(result).toBe(false);
  });
});
