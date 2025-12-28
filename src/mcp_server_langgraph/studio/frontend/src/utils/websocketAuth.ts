/**
 * WebSocket Authentication Utility
 *
 * Provides utilities for WebSocket token management:
 * 1. Check if token is valid before connecting
 * 2. Proactively refresh token if expiring soon (within 5 min buffer)
 * 3. Close code constant for token expiration (4010)
 *
 * Used by WebSocket hooks to ensure fresh token before (re)connection.
 * When backend closes with 4010, frontend should:
 * 1. Call ensureValidTokenForWebSocket() to refresh
 * 2. Reconnect with fresh token
 * 3. If refresh fails, trigger logout
 */

import { getAuthToken } from "./storage";
import { refreshAccessToken } from "./authenticatedFetch";

/**
 * WebSocket close code for token expiration.
 *
 * When backend detects token has expired during an active WebSocket connection,
 * it closes the connection with this code. Frontend should:
 * 1. Attempt to refresh the token
 * 2. Reconnect if refresh succeeds
 * 3. Redirect to login if refresh fails
 *
 * Distinguished from:
 * - 4001: Initial authentication failure (no token or invalid token)
 * - 4002: Authorization failure (valid token but insufficient permissions)
 */
export const WS_CLOSE_TOKEN_EXPIRED = 4010;

/**
 * Buffer time before token expiration to consider as "expiring soon".
 * Matches TOKEN_REFRESH_BUFFER_MS in authSlice.ts (5 minutes).
 */
const TOKEN_REFRESH_BUFFER_SECONDS = 5 * 60; // 5 minutes

/**
 * Decode JWT payload to extract expiration time.
 *
 * @param token - The JWT token string
 * @returns Expiration time in seconds (Unix timestamp), or null if invalid
 */
function decodeJwtExp(token: string): number | null {
  try {
    const parts = token.split(".");
    if (parts.length !== 3) return null;

    const payload = parts[1];
    if (!payload) return null;

    // Base64url decode
    const decoded = atob(payload.replace(/-/g, "+").replace(/_/g, "/"));
    const parsed = JSON.parse(decoded);

    return typeof parsed.exp === "number" ? parsed.exp : null;
  } catch {
    return null;
  }
}

/**
 * Check if a JWT token is expiring soon (within buffer period).
 *
 * Used for proactive token refresh before WebSocket connection attempts.
 *
 * @param token - The JWT token string
 * @param bufferSeconds - Number of seconds before expiration to consider "expiring soon"
 *                        Default is 300 (5 minutes) to match authSlice.ts
 * @returns True if token is expired or expiring within buffer, false otherwise
 */
export function isTokenExpiringSoon(
  token: string,
  bufferSeconds: number = TOKEN_REFRESH_BUFFER_SECONDS,
): boolean {
  const exp = decodeJwtExp(token);

  if (exp === null) {
    // Invalid token - treat as expiring
    return true;
  }

  const nowSeconds = Math.floor(Date.now() / 1000);
  const timeRemaining = exp - nowSeconds;

  return timeRemaining <= bufferSeconds;
}

// Simple lock mechanism to prevent concurrent refresh attempts (for WebSocket)
let isRefreshingForWS = false;
let refreshPromiseForWS: Promise<boolean> | null = null;

/**
 * Reset WebSocket auth state.
 * Useful for testing.
 */
export function resetWebSocketAuthState(): void {
  isRefreshingForWS = false;
  refreshPromiseForWS = null;
}

/**
 * Ensure a valid token is available for WebSocket connection.
 *
 * This function should be called:
 * 1. Before establishing a new WebSocket connection
 * 2. After receiving close code 4010 (token expired), before reconnecting
 *
 * @returns True if a valid token is available (may have been refreshed),
 *          false if no token or refresh failed
 */
export async function ensureValidTokenForWebSocket(): Promise<boolean> {
  const token = getAuthToken();

  if (!token) {
    return false;
  }

  // Check if token is expiring soon or already expired
  if (isTokenExpiringSoon(token)) {
    // Handle concurrent refresh attempts
    if (isRefreshingForWS && refreshPromiseForWS) {
      return refreshPromiseForWS;
    }

    isRefreshingForWS = true;
    refreshPromiseForWS = (async (): Promise<boolean> => {
      try {
        return await refreshAccessToken();
      } finally {
        isRefreshingForWS = false;
        refreshPromiseForWS = null;
      }
    })();

    return refreshPromiseForWS;
  }

  // Token is valid and not expiring soon
  return true;
}

export default {
  WS_CLOSE_TOKEN_EXPIRED,
  isTokenExpiringSoon,
  ensureValidTokenForWebSocket,
  resetWebSocketAuthState,
};
