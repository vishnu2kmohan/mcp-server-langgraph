/**
 * Tab-to-Route Mapping Utilities
 *
 * Maps workspace tabs to their corresponding routes and vice versa.
 * Used for bidirectional sync between tabs and browser navigation.
 */

import type { TabState } from "../store/slices/workspaceSlice";

// Route configurations for each tab type
interface RouteConfig {
  basePath: string;
  entityParam?: string;
}

const TAB_ROUTES: Record<TabState["type"], RouteConfig> = {
  chat: { basePath: "/studio/chat", entityParam: "session" },
  workflow: { basePath: "/studio/workflows" },
  project: { basePath: "/studio/projects" },
  settings: { basePath: "/studio/settings" },
  observability: { basePath: "/studio/observability" },
  cost: { basePath: "/studio/cost" },
};

/**
 * Get the route path for a given tab
 *
 * @param tab - The tab to get the route for
 * @returns The route path string
 *
 * @example
 * getRouteForTab({ type: "chat", entityId: "session-123" })
 * // Returns: "/studio/chat?session=session-123"
 */
export function getRouteForTab(tab: TabState): string {
  const config = TAB_ROUTES[tab.type];
  if (!config) {
    return "/studio";
  }

  let route = config.basePath;

  // Add entity ID as query param if present
  if (tab.entityId && config.entityParam) {
    route += `?${config.entityParam}=${encodeURIComponent(tab.entityId)}`;
  }

  return route;
}

/**
 * Check if a tab matches the current route
 *
 * @param tab - The tab to check
 * @param pathname - Current route pathname
 * @param searchParams - Current route search params
 * @returns True if the tab matches the route
 */
export function tabMatchesRoute(
  tab: TabState,
  pathname: string,
  searchParams: URLSearchParams,
): boolean {
  const config = TAB_ROUTES[tab.type];
  if (!config) {
    return false;
  }

  // Check base path matches
  if (!pathname.startsWith(config.basePath)) {
    return false;
  }

  // Check entity ID matches if applicable
  if (tab.entityId && config.entityParam) {
    const routeEntityId = searchParams.get(config.entityParam);
    return routeEntityId === tab.entityId;
  }

  // For non-entity tabs, just match by type
  return !tab.entityId;
}

export default {
  getRouteForTab,
  tabMatchesRoute,
};
