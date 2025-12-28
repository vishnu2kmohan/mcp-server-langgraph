/**
 * useIsChatRoute Hook
 *
 * Encapsulates route detection logic for determining if the current route
 * is a chat route (/studio/chat or /studio/chat/:sessionId).
 *
 * This hook consolidates the dual-source route checking that was previously
 * inline in StudioShellLayout, making it:
 * - Easier to test in isolation
 * - Reusable across components
 * - Clearer in its intent
 *
 * Usage:
 * ```tsx
 * function MyComponent() {
 *   const isChatRoute = useIsChatRoute();
 *   return isChatRoute ? <ChatLayout /> : <GenericLayout />;
 * }
 * ```
 */
import { useLocation } from "react-router";

// =============================================================================
// Pure Helper Function (exported for testing)
// =============================================================================

/**
 * Check if a path is a chat route.
 *
 * A chat route is:
 * - /studio/chat (exactly)
 * - /studio/chat/ (with trailing slash)
 * - /studio/chat/:sessionId (with session parameter)
 *
 * NOT a chat route:
 * - /studio/chatbot (different route, just starts with /studio/chat)
 * - /studio/workflows
 * - /studio/settings
 * - etc.
 *
 * @param path - The pathname to check
 * @returns true if the path is a chat route
 */
export function isChatRoutePath(path: string): boolean {
  if (!path) return false;

  // Exact match for /studio/chat (with optional trailing slash)
  if (path === "/studio/chat" || path === "/studio/chat/") {
    return true;
  }

  // Match /studio/chat/:sessionId (path starts with /studio/chat/ followed by more)
  // We need to ensure it's /studio/chat/ followed by something, not /studio/chatbot
  if (path.startsWith("/studio/chat/")) {
    return true;
  }

  return false;
}

// =============================================================================
// Hook
// =============================================================================

/**
 * Hook to determine if the current route is a chat route.
 *
 * Uses both React Router's location and window.location.pathname
 * to handle edge cases during navigation transitions:
 *
 * - If router says NOT chat: trust it (user is navigating away)
 * - If both agree: use that value
 * - If router says chat but window disagrees: trust window (router might be stale)
 *
 * @returns true if current route is a chat route
 */
export function useIsChatRoute(): boolean {
  const location = useLocation();

  // Get paths from both sources
  const routerPath = location.pathname;
  const windowPath = window.location.pathname;

  // Check each source
  const isRouterChatRoute = isChatRoutePath(routerPath);
  const isWindowChatRoute = isChatRoutePath(windowPath);

  // Determine final result with prioritization logic:
  // 1. If both agree: use that value
  // 2. If router says NOT chat: trust it (user is navigating away from chat)
  // 3. If router says chat but window doesn't: trust window (router might be stale)
  if (isRouterChatRoute && isWindowChatRoute) {
    return true; // Both agree: chat route
  }

  if (!isRouterChatRoute) {
    return false; // Router says NOT chat: trust it (navigating away)
  }

  // Router says chat but window might be more up-to-date
  return isWindowChatRoute;
}
