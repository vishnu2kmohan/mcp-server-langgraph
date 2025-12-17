/**
 * useTabNavigation Hook
 *
 * Provides a navigation handler for tab clicks that navigates to the appropriate route.
 * Used with MainDock's onTabNavigate callback for bidirectional tab-route sync.
 */

import { useCallback } from "react";
import { useNavigate } from "react-router";
import { getRouteForTab } from "../utils/tabRoutes";
import type { TabState } from "../store/slices/workspaceSlice";

/**
 * Hook that returns a handler for tab navigation
 *
 * @returns Navigation handler function for tab clicks
 *
 * @example
 * const handleTabNavigate = useTabNavigation();
 * <MainDock onTabNavigate={handleTabNavigate} />
 */
export function useTabNavigation(): (tab: TabState) => void {
  const navigate = useNavigate();

  const handleTabNavigate = useCallback(
    (tab: TabState) => {
      const route = getRouteForTab(tab);
      navigate(route);
    },
    [navigate],
  );

  return handleTabNavigate;
}

export default useTabNavigation;
