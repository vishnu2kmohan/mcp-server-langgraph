/**
 * useRouteTabSync Hook
 *
 * Syncs the current route with workspace tabs.
 * Features:
 * - Creates tabs when navigating to routes
 * - Activates existing tabs instead of duplicates
 * - Extracts entity IDs from URL params
 */

import { useEffect } from "react";
import { useLocation, useSearchParams } from "react-router";
import { useAppDispatch, useAppSelector } from "../store/hooks";
import {
  selectTabs,
  addTab,
  setActiveTabId,
  type TabState,
} from "../store/slices/workspaceSlice";

// Route to tab type mapping
interface RouteTabConfig {
  pattern: RegExp;
  type: TabState["type"];
  title: string;
  entityIdParam?: string;
}

const ROUTE_TAB_CONFIGS: RouteTabConfig[] = [
  {
    pattern: /^\/studio\/chat/,
    type: "chat",
    title: "Chat",
    entityIdParam: "session",
  },
  {
    pattern: /^\/studio\/workflows/,
    type: "workflow",
    title: "Workflows",
  },
  {
    pattern: /^\/studio\/settings/,
    type: "settings",
    title: "Settings",
  },
  {
    pattern: /^\/studio\/observability/,
    type: "observability",
    title: "Observability",
  },
  {
    pattern: /^\/studio\/cost/,
    type: "cost",
    title: "Cost",
  },
  {
    pattern: /^\/studio\/projects/,
    type: "project",
    title: "Projects",
  },
];

/**
 * Hook that syncs routes with workspace tabs.
 * Creates tabs for routes and activates existing tabs when revisiting routes.
 */
export function useRouteTabSync(): void {
  const dispatch = useAppDispatch();
  const location = useLocation();
  const [searchParams] = useSearchParams();
  const tabs = useAppSelector(selectTabs);

  useEffect(() => {
    const pathname = location.pathname;

    // Find matching route config
    const config = ROUTE_TAB_CONFIGS.find((c) => c.pattern.test(pathname));
    if (!config) {
      return;
    }

    // Extract entity ID from URL params if configured
    const entityId = config.entityIdParam
      ? (searchParams.get(config.entityIdParam) ?? undefined)
      : undefined;

    // Check if a tab of this type already exists
    const existingTab = tabs.find((tab) => {
      if (tab.type !== config.type) {
        return false;
      }
      // For entity-specific tabs, match by entityId
      if (entityId) {
        return tab.entityId === entityId;
      }
      // For non-entity tabs, just match by type
      return !tab.entityId;
    });

    if (existingTab) {
      // Activate existing tab
      dispatch(setActiveTabId(existingTab.id));
    } else {
      // Create new tab
      const tabId = entityId
        ? `${config.type}-${entityId}`
        : `${config.type}-${Date.now()}`;

      const newTab: TabState = {
        id: tabId,
        type: config.type,
        title: entityId ? `${config.title}: ${entityId}` : config.title,
        entityId,
      };

      dispatch(addTab(newTab));
    }
  }, [location.pathname, searchParams, dispatch, tabs]);
}

export default useRouteTabSync;
