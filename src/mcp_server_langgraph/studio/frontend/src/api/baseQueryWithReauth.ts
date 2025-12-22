/**
 * RTK Query baseQueryWithReauth
 *
 * Provides automatic 401 handling with token refresh for RTK Query.
 *
 * Flow:
 * 1. Make API request with current access token
 * 2. If 401 returned, attempt token refresh
 * 3. If refresh succeeds, retry original request with new token
 * 4. If refresh fails, dispatch logout and return error
 *
 * Features:
 * - Prevents concurrent refresh attempts with a simple lock
 * - Automatic logout on refresh failure
 * - Seamless token storage update
 *
 * Reference: https://redux-toolkit.js.org/rtk-query/usage/customizing-queries#automatic-re-authorization-by-extending-fetchbasequery
 */

import {
  BaseQueryFn,
  FetchArgs,
  fetchBaseQuery,
  FetchBaseQueryError,
} from "@reduxjs/toolkit/query/react";

import { logout, setTokens } from "../store/slices/authSlice";
import {
  getAuthToken,
  setAuthTokens,
  storage,
  STORAGE_KEYS,
} from "../utils/storage";

// Simple lock mechanism to prevent concurrent refresh attempts
let isRefreshing = false;
let refreshPromise: Promise<boolean> | null = null;

// Determine base URL - use absolute URL in test environment for Node.js fetch compatibility
const getBaseUrl = (): string => {
  // In test environments, Node.js fetch requires absolute URLs
  // Check for vitest or jest test environment
  if (
    typeof process !== "undefined" &&
    (process.env.VITEST === "true" ||
      process.env.NODE_ENV === "test" ||
      process.env.JEST_WORKER_ID !== undefined)
  ) {
    return "http://localhost:3000/api/v1";
  }
  // In browser, relative URLs work fine
  return "/api/v1";
};

// Base query configuration
const baseQuery = fetchBaseQuery({
  baseUrl: getBaseUrl(),
  // Include credentials (cookies) for forward-auth (Keycloak SSO)
  credentials: "include",
  prepareHeaders: (headers) => {
    // Add auth token if available (for direct JWT auth)
    // Uses unified storage utility which handles legacy key fallback
    const token = getAuthToken();
    if (token) {
      headers.set("Authorization", `Bearer ${token}`);
    }
    return headers;
  },
});

/**
 * Base query with automatic re-authentication on 401.
 *
 * This wrapper intercepts 401 responses, attempts token refresh,
 * and retries the original request if successful.
 */
export const baseQueryWithReauth: BaseQueryFn<
  string | FetchArgs,
  unknown,
  FetchBaseQueryError
> = async (args, api, extraOptions) => {
  // Make the initial request
  let result = await baseQuery(args, api, extraOptions);

  // Check for 401 Unauthorized
  if (result.error && result.error.status === 401) {
    // Check if we have a refresh token (stored under legacy key without prefix)
    const refreshToken =
      typeof window !== "undefined"
        ? storage.get<string>(STORAGE_KEYS.REFRESH_TOKEN)
        : null;

    if (!refreshToken) {
      // No refresh token, logout immediately
      api.dispatch(logout());
      return result;
    }

    // Handle concurrent refresh attempts
    if (isRefreshing && refreshPromise) {
      // Wait for the existing refresh to complete
      const refreshSucceeded = await refreshPromise;
      if (refreshSucceeded) {
        // Retry with the new token
        result = await baseQuery(args, api, extraOptions);
      }
      return result;
    }

    // Start refresh
    isRefreshing = true;
    refreshPromise = (async (): Promise<boolean> => {
      try {
        // Attempt token refresh
        const refreshResult = await baseQuery(
          {
            url: "/auth/refresh",
            method: "POST",
            body: { refresh_token: refreshToken },
          },
          api,
          extraOptions,
        );

        if (refreshResult.data) {
          // Refresh successful - update tokens
          const newTokens = refreshResult.data as {
            access_token: string;
            refresh_token?: string;
            expires_in?: number;
            refresh_expires_in?: number;
          };

          // Save to localStorage using unified storage utility
          setAuthTokens(newTokens.access_token, newTokens.refresh_token);

          // Update Redux store
          const expiresIn = newTokens.expires_in ?? 300;
          const refreshExpiresIn = newTokens.refresh_expires_in ?? 1800;
          const now = Date.now();

          api.dispatch(
            setTokens({
              accessToken: newTokens.access_token,
              refreshToken: newTokens.refresh_token ?? refreshToken,
              expiresAt: now + expiresIn * 1000,
              refreshExpiresAt: now + refreshExpiresIn * 1000,
            }),
          );

          return true;
        } else {
          // Refresh failed - logout
          api.dispatch(logout());
          return false;
        }
      } finally {
        isRefreshing = false;
        refreshPromise = null;
      }
    })();

    const refreshSucceeded = await refreshPromise;
    if (refreshSucceeded) {
      // Retry the original request with new token
      result = await baseQuery(args, api, extraOptions);
    }
  }

  return result;
};

/**
 * Reset the refresh lock state.
 * Useful for testing.
 */
export function resetRefreshLock(): void {
  isRefreshing = false;
  refreshPromise = null;
}

export default baseQueryWithReauth;
