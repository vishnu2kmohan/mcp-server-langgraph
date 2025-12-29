/**
 * Authenticated Fetch Utility
 *
 * Provides a fetch wrapper that automatically handles authentication:
 * 1. Adds Authorization header with access token
 * 2. Handles 401 by attempting token refresh
 * 3. Retries original request if refresh succeeds
 * 4. Calls onAuthFailure callback if refresh fails (for redirect to login)
 *
 * Use this for non-RTK Query code (useStreamingChat, loaders, etc.)
 * RTK Query uses baseQueryWithReauth instead.
 */

import {
  getAuthToken,
  setAuthTokens,
  clearAuthTokens,
  STORAGE_KEYS,
} from "./storage";

// API base URL
const getBaseUrl = (): string => {
  // In test environment
  if (
    typeof process !== "undefined" &&
    (process.env.VITEST === "true" ||
      process.env.NODE_ENV === "test" ||
      process.env.JEST_WORKER_ID !== undefined)
  ) {
    return process.env.TEST_API_URL ?? "http://127.0.0.1:3000/api/v1";
  }
  // In browser, use Vite env var if available
  if (
    typeof import.meta !== "undefined" &&
    import.meta.env?.VITE_API_BASE_URL
  ) {
    return import.meta.env.VITE_API_BASE_URL;
  }
  return "/api/v1";
};

// Simple lock mechanism to prevent concurrent refresh attempts
let isRefreshing = false;
let refreshPromise: Promise<boolean> | null = null;

/**
 * Options for authenticatedFetch
 */
export interface AuthenticatedFetchOptions extends RequestInit {
  /**
   * Skip adding Authorization header (for public endpoints)
   */
  skipAuth?: boolean;

  /**
   * Callback when authentication fails (no token, refresh failed)
   * Use this to redirect to login
   */
  onAuthFailure?: () => void;
}

/**
 * Reset the refresh lock state.
 * Useful for testing.
 */
export function resetRefreshState(): void {
  isRefreshing = false;
  refreshPromise = null;
}

/**
 * Attempt to refresh the access token using the refresh token.
 *
 * @returns true if refresh succeeded, false otherwise
 */
export async function refreshAccessToken(): Promise<boolean> {
  // Get refresh token from localStorage
  const refreshToken =
    typeof window !== "undefined"
      ? window.localStorage.getItem(STORAGE_KEYS.REFRESH_TOKEN)
      : null;

  if (!refreshToken) {
    return false;
  }

  // Handle concurrent refresh attempts
  if (isRefreshing && refreshPromise) {
    return refreshPromise;
  }

  isRefreshing = true;
  refreshPromise = (async (): Promise<boolean> => {
    try {
      const response = await fetch(`${getBaseUrl()}/auth/refresh`, {
        method: "POST",
        headers: {
          "Content-Type": "application/json",
        },
        body: JSON.stringify({ refresh_token: refreshToken }),
        credentials: "include",
      });

      if (response.ok) {
        const data = (await response.json()) as {
          access_token: string;
          refresh_token?: string;
        };

        // Update tokens in storage
        setAuthTokens(data.access_token, data.refresh_token);
        return true;
      } else {
        // Refresh failed - clear tokens
        clearAuthTokens();
        return false;
      }
    } catch {
      // Network error - clear tokens
      clearAuthTokens();
      return false;
    } finally {
      isRefreshing = false;
      refreshPromise = null;
    }
  })();

  return refreshPromise;
}

/**
 * Fetch wrapper with automatic authentication handling.
 *
 * @param url - The URL to fetch (relative or absolute)
 * @param options - Fetch options plus auth-specific options
 * @returns The fetch Response
 *
 * @example
 * // Basic usage
 * const response = await authenticatedFetch('/api/v1/sessions');
 *
 * @example
 * // With auth failure handling
 * const response = await authenticatedFetch('/api/v1/protected', {
 *   onAuthFailure: () => navigate('/login'),
 * });
 *
 * @example
 * // Skip auth for public endpoints
 * const response = await authenticatedFetch('/api/v1/public', { skipAuth: true });
 */
export async function authenticatedFetch(
  url: string,
  options: AuthenticatedFetchOptions = {},
): Promise<Response> {
  const { skipAuth, onAuthFailure, ...fetchOptions } = options;

  // Build headers
  const headers = new Headers(fetchOptions.headers);

  // Add Authorization header unless skipped
  if (!skipAuth) {
    const token = getAuthToken();
    if (token) {
      headers.set("Authorization", `Bearer ${token}`);
    }
  }

  // Automatically add Content-Type: application/json for requests with JSON body
  // This prevents 422 errors from FastAPI when Content-Type is missing
  if (fetchOptions.body && !headers.has("Content-Type")) {
    headers.set("Content-Type", "application/json");
  }

  // Make the request
  const response = await fetch(url, {
    ...fetchOptions,
    headers,
    credentials: "include",
  });

  // Handle 401 Unauthorized
  if (response.status === 401 && !skipAuth) {
    // Attempt token refresh
    const refreshSucceeded = await refreshAccessToken();

    if (refreshSucceeded) {
      // Retry the original request with new token
      const newToken = getAuthToken();
      if (newToken) {
        headers.set("Authorization", `Bearer ${newToken}`);
      }

      return fetch(url, {
        ...fetchOptions,
        headers,
        credentials: "include",
      });
    } else {
      // Refresh failed - call auth failure callback
      onAuthFailure?.();
      return response;
    }
  }

  return response;
}

export default authenticatedFetch;
