/**
 * Intended Route Persistence
 *
 * Saves and restores the user's intended route after OAuth2 authentication.
 *
 * Problem: OAuth2 PKCE flow redirects to external IdP (Keycloak), which loses
 * React Router's location state ({ from: location }).
 *
 * Solution: Save the intended route to sessionStorage before redirect,
 * restore it after OAuth callback.
 *
 * Uses sessionStorage (not localStorage) so the intended route is:
 * - Cleared when browser closes (session-scoped)
 * - Not persisted across browser sessions
 * - One-time use (cleared after redirect)
 */

import { sessionStore } from "./storage";

/**
 * Storage key for intended route (sessionStore adds studio- prefix automatically)
 * Final key in sessionStorage: "studio-intended-route"
 */
const INTENDED_ROUTE_STORAGE_KEY = "intended-route";

/**
 * Exported key for test verification (matches what's actually stored)
 */
export const INTENDED_ROUTE_KEY = "studio-intended-route";

/**
 * Paths that should NOT be saved as intended routes (prevent redirect loops)
 */
const EXCLUDED_PATHS = ["/login", "/auth/callback", "/logout", "/auth/logout"];

/**
 * Save the intended route before OAuth redirect.
 *
 * Called by LoginPage when it receives a `from` location state from AuthGuard.
 *
 * @param route - The full path including query string and hash
 */
export function setIntendedRoute(route: string): void {
  // Don't save empty, root, or auth-related paths
  if (
    !route ||
    route === "/" ||
    EXCLUDED_PATHS.some((p) => route.startsWith(p))
  ) {
    return;
  }

  sessionStore.set(INTENDED_ROUTE_STORAGE_KEY, route);
}

/**
 * Get the saved intended route.
 *
 * Called by AuthCallbackPage after successful OAuth authentication.
 *
 * @returns The saved route, or null if none exists
 */
export function getIntendedRoute(): string | null {
  return sessionStore.get<string>(INTENDED_ROUTE_STORAGE_KEY) ?? null;
}

/**
 * Clear the intended route after redirect.
 *
 * Called by AuthCallbackPage after reading the route (one-time use).
 */
export function clearIntendedRoute(): void {
  sessionStore.remove(INTENDED_ROUTE_STORAGE_KEY);
}

/**
 * Save the current browser location as the intended route.
 *
 * Convenience function that captures window.location.pathname + search + hash
 * and saves it as the intended route. Use this in auth failure handlers to
 * preserve the user's current location before redirecting to login.
 *
 * This function:
 * - Captures the full URL path including query string and hash
 * - Respects the same exclusion rules as setIntendedRoute (won't save /login, etc.)
 * - Is safe to call anywhere - excluded paths are silently ignored
 *
 * @example
 * // In an API error handler when 401 is received:
 * if (response.status === 401) {
 *   saveCurrentRouteAsIntended();
 *   navigate('/login', { replace: true });
 * }
 */
export function saveCurrentRouteAsIntended(): void {
  const fullPath =
    window.location.pathname + window.location.search + window.location.hash;
  setIntendedRoute(fullPath);
}
