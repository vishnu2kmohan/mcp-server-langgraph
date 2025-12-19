/**
 * Workspace Slice
 *
 * Redux slice for JupyterLab-inspired workspace state management.
 * Provides full persistence for the IDE-like layout.
 *
 * Features:
 * - Panel dimensions and collapsed states
 * - Activity bar selection
 * - Dock layout with splits (recursive tree structure)
 * - Tab management
 * - Focus mode
 * - Group expansion states
 * - Scroll position tracking
 * - Full persistence to localStorage
 */

import { createSlice, PayloadAction } from "@reduxjs/toolkit";
import { storage } from "../../utils/storage";

// =============================================================================
// Types
// =============================================================================

/**
 * Document types that can be opened in tabs
 */
export type TabType =
  | "chat"
  | "workflow"
  | "project"
  | "settings"
  | "cost"
  | "observability";

/**
 * State for a single tab
 */
export interface TabState {
  id: string;
  type: TabType;
  title: string;
  entityId?: string;
  scrollPosition?: number;
}

/**
 * Layout types for the dock panel
 */
export type DockLayoutType =
  | "tab-group"
  | "horizontal-split"
  | "vertical-split";

/**
 * Recursive layout structure for splits
 */
export interface DockLayout {
  type: DockLayoutType;
  children?: DockLayout[];
  tabIds?: string[];
  sizes?: number[];
}

/**
 * Full workspace state
 */
export interface WorkspaceState {
  // Version for migration
  version: number;

  // Panel dimensions
  leftSidebarWidth: number;
  leftSidebarCollapsed: boolean;
  rightSidebarWidth: number;
  rightSidebarCollapsed: boolean;
  rightSidebarPinned: boolean;
  bottomPanelHeight: number;
  bottomPanelCollapsed: boolean;

  // Activity bar
  activeActivityId: string;

  // Main dock - tabs and splits
  dockLayout: DockLayout;

  // Open tabs
  tabs: TabState[];
  activeTabId: string | null;

  // Focus mode
  focusMode: boolean;

  // Group expansion states
  expandedGroups: string[];

  // Right sidebar sections
  expandedPropertySections: string[];

  // Bottom panel
  bottomPanelActiveTab: string;

  // Scroll positions per panel
  scrollPositions: Record<string, number>;

  // Last updated timestamp
  lastUpdated: number;
}

// =============================================================================
// Constants
// =============================================================================

export const WORKSPACE_STORAGE_KEY = "studio-agent-workspace";

// Panel constraints
const LEFT_SIDEBAR_MIN_WIDTH = 200;
const LEFT_SIDEBAR_MAX_WIDTH = 480;
const RIGHT_SIDEBAR_MIN_WIDTH = 200;
const RIGHT_SIDEBAR_MAX_WIDTH = 480;
const BOTTOM_PANEL_MIN_HEIGHT = 100;
const BOTTOM_PANEL_MAX_HEIGHT = 400;

/**
 * Default workspace state
 */
export const DEFAULT_WORKSPACE_STATE: WorkspaceState = {
  version: 1,
  leftSidebarWidth: 280,
  leftSidebarCollapsed: false,
  rightSidebarWidth: 280,
  rightSidebarCollapsed: false,
  rightSidebarPinned: false,
  bottomPanelHeight: 200,
  bottomPanelCollapsed: true,
  activeActivityId: "conversations",
  dockLayout: {
    type: "tab-group",
    tabIds: [],
  },
  tabs: [],
  activeTabId: null,
  focusMode: false,
  expandedGroups: [],
  expandedPropertySections: [],
  bottomPanelActiveTab: "activity",
  scrollPositions: {},
  lastUpdated: 0,
};

// =============================================================================
// Utility functions
// =============================================================================

/**
 * Clamp a value between min and max
 */
function clamp(value: number, min: number, max: number): number {
  return Math.max(min, Math.min(max, value));
}

/**
 * Find a tab in a dock layout and return its path and containing group
 */
function findTabInLayout(
  layout: DockLayout,
  tabId: string,
  path: number[] = [],
): { path: number[]; groupPath: number[] } | null {
  if (layout.type === "tab-group") {
    if (layout.tabIds?.includes(tabId)) {
      return { path, groupPath: path };
    }
    return null;
  }

  // Search children
  for (let i = 0; i < (layout.children?.length ?? 0); i++) {
    const result = findTabInLayout(layout.children![i], tabId, [...path, i]);
    if (result) return result;
  }
  return null;
}

/**
 * Get a layout node at a given path
 */
function getLayoutAtPath(
  layout: DockLayout,
  path: number[],
): DockLayout | null {
  if (path.length === 0) return layout;

  if (layout.type === "tab-group") return null;

  const [head, ...rest] = path;
  if (!layout.children || head >= layout.children.length) return null;

  return getLayoutAtPath(layout.children[head], rest);
}

/**
 * Set a layout node at a given path (immutably)
 */
function setLayoutAtPath(
  layout: DockLayout,
  path: number[],
  newLayout: DockLayout,
): DockLayout {
  if (path.length === 0) return newLayout;

  if (layout.type === "tab-group") return layout;

  const [head, ...rest] = path;
  if (!layout.children || head >= layout.children.length) return layout;

  return {
    ...layout,
    children: layout.children.map((child, i) =>
      i === head ? setLayoutAtPath(child, rest, newLayout) : child,
    ),
  };
}

/**
 * Remove a tab from a layout (immutably) and return the updated layout
 * Also collapses empty groups if needed
 */
function removeTabFromLayout(layout: DockLayout, tabId: string): DockLayout {
  if (layout.type === "tab-group") {
    return {
      ...layout,
      tabIds: (layout.tabIds || []).filter((id) => id !== tabId),
    };
  }

  // Process children and filter out empty tab groups
  const newChildren = (layout.children || [])
    .map((child) => removeTabFromLayout(child, tabId))
    .filter((child) => {
      // Keep split containers and non-empty tab groups
      if (child.type !== "tab-group") return true;
      return (child.tabIds?.length ?? 0) > 0;
    });

  // If only one child left, collapse the split
  if (newChildren.length === 1) {
    return newChildren[0];
  }

  // If no children left, return empty tab group
  if (newChildren.length === 0) {
    return { type: "tab-group", tabIds: [] };
  }

  // Adjust sizes if children changed
  const newSizes =
    newChildren.length !== (layout.children?.length ?? 0)
      ? newChildren.map(() => 100 / newChildren.length)
      : layout.sizes;

  return {
    ...layout,
    children: newChildren,
    sizes: newSizes,
  };
}

/**
 * Add a tab to a group at a given path (immutably)
 */
function addTabToGroupAtPath(
  layout: DockLayout,
  path: number[],
  tabId: string,
): DockLayout {
  const target = getLayoutAtPath(layout, path);
  if (!target || target.type !== "tab-group") return layout;

  const newTarget: DockLayout = {
    ...target,
    tabIds: [...(target.tabIds || []), tabId],
  };

  return setLayoutAtPath(layout, path, newTarget);
}

/**
 * Load workspace state from localStorage
 */
function loadFromStorage(): Partial<WorkspaceState> | null {
  return (
    storage.get<Partial<WorkspaceState>>(WORKSPACE_STORAGE_KEY, {
      expectObject: true,
    }) ?? null
  );
}

/**
 * Save workspace state to localStorage
 */
function saveToStorage(state: WorkspaceState): void {
  storage.set(WORKSPACE_STORAGE_KEY, state);
}

/**
 * Clear workspace state from localStorage
 */
function clearStorage(): void {
  storage.remove(WORKSPACE_STORAGE_KEY);
}

// =============================================================================
// Slice
// =============================================================================

const initialState: WorkspaceState = {
  ...DEFAULT_WORKSPACE_STATE,
  lastUpdated: Date.now(),
};

export const workspaceSlice = createSlice({
  name: "workspace",
  initialState,
  reducers: {
    // Left sidebar
    setLeftSidebarWidth: (state, action: PayloadAction<number>) => {
      state.leftSidebarWidth = clamp(
        action.payload,
        LEFT_SIDEBAR_MIN_WIDTH,
        LEFT_SIDEBAR_MAX_WIDTH,
      );
      state.lastUpdated = Date.now();
    },
    setLeftSidebarCollapsed: (state, action: PayloadAction<boolean>) => {
      state.leftSidebarCollapsed = action.payload;
      state.lastUpdated = Date.now();
    },

    // Right sidebar
    setRightSidebarWidth: (state, action: PayloadAction<number>) => {
      state.rightSidebarWidth = clamp(
        action.payload,
        RIGHT_SIDEBAR_MIN_WIDTH,
        RIGHT_SIDEBAR_MAX_WIDTH,
      );
      state.lastUpdated = Date.now();
    },
    setRightSidebarCollapsed: (state, action: PayloadAction<boolean>) => {
      state.rightSidebarCollapsed = action.payload;
      state.lastUpdated = Date.now();
    },
    setRightSidebarPinned: (state, action: PayloadAction<boolean>) => {
      state.rightSidebarPinned = action.payload;
      state.lastUpdated = Date.now();
    },

    // Bottom panel
    setBottomPanelHeight: (state, action: PayloadAction<number>) => {
      state.bottomPanelHeight = clamp(
        action.payload,
        BOTTOM_PANEL_MIN_HEIGHT,
        BOTTOM_PANEL_MAX_HEIGHT,
      );
      state.lastUpdated = Date.now();
    },
    setBottomPanelCollapsed: (state, action: PayloadAction<boolean>) => {
      state.bottomPanelCollapsed = action.payload;
      state.lastUpdated = Date.now();
    },
    setBottomPanelActiveTab: (state, action: PayloadAction<string>) => {
      state.bottomPanelActiveTab = action.payload;
      state.lastUpdated = Date.now();
    },

    // Activity bar
    setActiveActivityId: (state, action: PayloadAction<string>) => {
      state.activeActivityId = action.payload;
      state.lastUpdated = Date.now();
    },

    // Dock layout
    setDockLayout: (state, action: PayloadAction<DockLayout>) => {
      state.dockLayout = action.payload;
      state.lastUpdated = Date.now();
    },

    // Tab management
    addTab: (state, action: PayloadAction<TabState>) => {
      // Don't add duplicate tabs
      if (state.tabs.some((t) => t.id === action.payload.id)) {
        return;
      }
      state.tabs.push(action.payload);
      state.activeTabId = action.payload.id;
      // Also add to dock layout if it's a tab-group
      if (state.dockLayout.type === "tab-group") {
        state.dockLayout.tabIds = [
          ...(state.dockLayout.tabIds || []),
          action.payload.id,
        ];
      }
      state.lastUpdated = Date.now();
    },
    removeTab: (state, action: PayloadAction<string>) => {
      const tabId = action.payload;
      const tabIndex = state.tabs.findIndex((t) => t.id === tabId);

      if (tabIndex === -1) return;

      state.tabs = state.tabs.filter((t) => t.id !== tabId);

      // Update activeTabId if we removed the active tab
      if (state.activeTabId === tabId) {
        if (state.tabs.length > 0) {
          // Fall back to next tab or previous
          const newIndex = Math.min(tabIndex, state.tabs.length - 1);
          state.activeTabId = state.tabs[newIndex]?.id ?? null;
        } else {
          state.activeTabId = null;
        }
      }

      // Remove from dock layout
      if (state.dockLayout.type === "tab-group") {
        state.dockLayout.tabIds = (state.dockLayout.tabIds || []).filter(
          (id) => id !== tabId,
        );
      }

      state.lastUpdated = Date.now();
    },
    setActiveTabId: (state, action: PayloadAction<string | null>) => {
      state.activeTabId = action.payload;
      state.lastUpdated = Date.now();
    },
    // Remove all tabs with a specific entityId (for orphan cleanup)
    removeTabsByEntityId: (state, action: PayloadAction<string>) => {
      const entityId = action.payload;
      const tabsToRemove = state.tabs.filter((t) => t.entityId === entityId);

      if (tabsToRemove.length === 0) return;

      // Remove tabs
      state.tabs = state.tabs.filter((t) => t.entityId !== entityId);

      // Update dock layout
      if (state.dockLayout.type === "tab-group") {
        const tabIdsToRemove = new Set(tabsToRemove.map((t) => t.id));
        state.dockLayout.tabIds = (state.dockLayout.tabIds || []).filter(
          (id) => !tabIdsToRemove.has(id),
        );
      }

      // Update activeTabId if the active tab was removed
      if (
        state.activeTabId &&
        tabsToRemove.some((t) => t.id === state.activeTabId)
      ) {
        state.activeTabId = state.tabs.length > 0 ? state.tabs[0].id : null;
      }

      state.lastUpdated = Date.now();
    },

    reorderTabs: (
      state,
      action: PayloadAction<{ fromIndex: number; toIndex: number }>,
    ) => {
      const { fromIndex, toIndex } = action.payload;
      if (
        fromIndex < 0 ||
        fromIndex >= state.tabs.length ||
        toIndex < 0 ||
        toIndex >= state.tabs.length
      ) {
        return;
      }

      const [removed] = state.tabs.splice(fromIndex, 1);
      state.tabs.splice(toIndex, 0, removed);

      // Also update dock layout order
      if (state.dockLayout.type === "tab-group" && state.dockLayout.tabIds) {
        const [removedId] = state.dockLayout.tabIds.splice(fromIndex, 1);
        state.dockLayout.tabIds.splice(toIndex, 0, removedId);
      }

      state.lastUpdated = Date.now();
    },

    /**
     * Update a tab's title
     */
    updateTabTitle: (
      state,
      action: PayloadAction<{ tabId: string; title: string }>,
    ) => {
      const { tabId, title } = action.payload;
      const tab = state.tabs.find((t) => t.id === tabId);
      if (tab) {
        tab.title = title;
        state.lastUpdated = Date.now();
      }
    },

    /**
     * Split a tab into a new pane
     * Creates a horizontal or vertical split with the dragged tab in a new pane
     * Supports nested splits by finding the tab in the tree and splitting its container
     */
    splitTab: (
      state,
      action: PayloadAction<{
        tabId: string;
        direction: "horizontal" | "vertical";
        position: "before" | "after";
      }>,
    ) => {
      const { tabId, direction, position } = action.payload;

      // Tab must exist
      if (!state.tabs.some((t) => t.id === tabId)) {
        return;
      }

      const splitType =
        direction === "horizontal" ? "horizontal-split" : "vertical-split";

      // If we're in a simple tab-group layout, convert to a split
      if (state.dockLayout.type === "tab-group") {
        const existingTabIds = state.dockLayout.tabIds || [];

        // Remove the dragged tab from the existing group
        const remainingTabIds = existingTabIds.filter((id) => id !== tabId);

        // Create the split layout
        const existingGroup: DockLayout = {
          type: "tab-group",
          tabIds: remainingTabIds,
        };

        const newGroup: DockLayout = {
          type: "tab-group",
          tabIds: [tabId],
        };

        state.dockLayout = {
          type: splitType,
          children:
            position === "before"
              ? [newGroup, existingGroup]
              : [existingGroup, newGroup],
          sizes: [50, 50],
        };

        state.activeTabId = tabId;
        state.lastUpdated = Date.now();
        return;
      }

      // Handle nested split layouts
      const tabLocation = findTabInLayout(state.dockLayout, tabId);
      if (!tabLocation) return;

      // Get the parent path (where we'll insert the split)
      const groupPath = tabLocation.groupPath;

      // Get the containing tab group
      const containingGroup = getLayoutAtPath(state.dockLayout, groupPath);
      if (!containingGroup || containingGroup.type !== "tab-group") return;

      // Remove tab from current group
      const remainingTabIds = (containingGroup.tabIds || []).filter(
        (id) => id !== tabId,
      );

      // Create new layouts
      const existingGroup: DockLayout = {
        type: "tab-group",
        tabIds: remainingTabIds,
      };

      const newGroup: DockLayout = {
        type: "tab-group",
        tabIds: [tabId],
      };

      const newSplit: DockLayout = {
        type: splitType,
        children:
          position === "before"
            ? [newGroup, existingGroup]
            : [existingGroup, newGroup],
        sizes: [50, 50],
      };

      // Replace the tab group with the new split
      state.dockLayout = setLayoutAtPath(state.dockLayout, groupPath, newSplit);

      // Clean up empty groups
      state.dockLayout = removeTabFromLayout(state.dockLayout, "__cleanup__");

      state.activeTabId = tabId;
      state.lastUpdated = Date.now();
    },

    /**
     * Update split sizes at a given path
     */
    updateSplitSizes: (
      state,
      action: PayloadAction<{
        path: number[];
        sizes: number[];
      }>,
    ) => {
      const { path, sizes } = action.payload;

      if (path.length === 0) {
        // Update root layout sizes
        if (state.dockLayout.type !== "tab-group") {
          state.dockLayout = {
            ...state.dockLayout,
            sizes,
          };
        }
      } else {
        // Update nested layout sizes
        const target = getLayoutAtPath(state.dockLayout, path);
        if (target && target.type !== "tab-group") {
          const newTarget = { ...target, sizes };
          state.dockLayout = setLayoutAtPath(state.dockLayout, path, newTarget);
        }
      }

      state.lastUpdated = Date.now();
    },

    /**
     * Move a tab to a different group at the specified path
     */
    moveTabToGroup: (
      state,
      action: PayloadAction<{
        tabId: string;
        targetPath: number[];
      }>,
    ) => {
      const { tabId, targetPath } = action.payload;

      // Tab must exist
      if (!state.tabs.some((t) => t.id === tabId)) {
        return;
      }

      // Add tab to target group first
      state.dockLayout = addTabToGroupAtPath(
        state.dockLayout,
        targetPath,
        tabId,
      );

      // Then remove from original location (which will also collapse empty groups)
      // We need to do this by reconstructing without the tab from all other locations
      const _targetGroup = getLayoutAtPath(state.dockLayout, targetPath);

      // Remove from all other locations
      const removeFromOtherLocations = (
        layout: DockLayout,
        currentPath: number[],
      ): DockLayout => {
        // If this is the target path, don't remove from here
        if (
          currentPath.length === targetPath.length &&
          currentPath.every((v, i) => v === targetPath[i])
        ) {
          return layout;
        }

        if (layout.type === "tab-group") {
          return {
            ...layout,
            tabIds: (layout.tabIds || []).filter((id) => id !== tabId),
          };
        }

        const newChildren = (layout.children || []).map((child, i) =>
          removeFromOtherLocations(child, [...currentPath, i]),
        );

        // Filter out empty tab groups
        const filteredChildren = newChildren.filter((child) => {
          if (child.type !== "tab-group") return true;
          return (child.tabIds?.length ?? 0) > 0;
        });

        // Collapse if only one child
        if (filteredChildren.length === 1) {
          return filteredChildren[0];
        }

        if (filteredChildren.length === 0) {
          return { type: "tab-group", tabIds: [] };
        }

        return {
          ...layout,
          children: filteredChildren,
          sizes:
            filteredChildren.length !== newChildren.length
              ? filteredChildren.map(() => 100 / filteredChildren.length)
              : layout.sizes,
        };
      };

      state.dockLayout = removeFromOtherLocations(state.dockLayout, []);

      state.activeTabId = tabId;
      state.lastUpdated = Date.now();
    },

    /**
     * Merge split panes back into a single tab group
     */
    mergeSplits: (state) => {
      // Collect all tab IDs from all nested layouts
      const collectTabIds = (layout: DockLayout): string[] => {
        if (layout.type === "tab-group") {
          return layout.tabIds || [];
        }
        return (layout.children || []).flatMap(collectTabIds);
      };

      const allTabIds = collectTabIds(state.dockLayout);

      state.dockLayout = {
        type: "tab-group",
        tabIds: allTabIds,
      };

      state.lastUpdated = Date.now();
    },

    // Focus mode
    setFocusMode: (state, action: PayloadAction<boolean>) => {
      state.focusMode = action.payload;
      state.lastUpdated = Date.now();
    },

    // Group expansion
    toggleExpandedGroup: (state, action: PayloadAction<string>) => {
      const group = action.payload;
      const index = state.expandedGroups.indexOf(group);
      if (index === -1) {
        state.expandedGroups.push(group);
      } else {
        state.expandedGroups.splice(index, 1);
      }
      state.lastUpdated = Date.now();
    },

    // Property section expansion
    toggleExpandedPropertySection: (state, action: PayloadAction<string>) => {
      const section = action.payload;
      const index = state.expandedPropertySections.indexOf(section);
      if (index === -1) {
        state.expandedPropertySections.push(section);
      } else {
        state.expandedPropertySections.splice(index, 1);
      }
      state.lastUpdated = Date.now();
    },

    // Scroll positions
    setScrollPosition: (
      state,
      action: PayloadAction<{ panelId: string; position: number }>,
    ) => {
      state.scrollPositions[action.payload.panelId] = action.payload.position;
      state.lastUpdated = Date.now();
    },

    // Reset
    resetWorkspace: (state) => {
      clearStorage();
      Object.assign(state, {
        ...DEFAULT_WORKSPACE_STATE,
        lastUpdated: Date.now(),
      });
    },

    // Load from storage
    loadWorkspaceFromStorage: (state) => {
      const saved = loadFromStorage();
      if (saved) {
        Object.assign(state, {
          ...DEFAULT_WORKSPACE_STATE,
          ...saved,
          lastUpdated: Date.now(),
        });
      }
    },
  },
});

// =============================================================================
// Actions
// =============================================================================

export const {
  setLeftSidebarWidth,
  setLeftSidebarCollapsed,
  setRightSidebarWidth,
  setRightSidebarCollapsed,
  setRightSidebarPinned,
  setBottomPanelHeight,
  setBottomPanelCollapsed,
  setBottomPanelActiveTab,
  setActiveActivityId,
  setDockLayout,
  addTab,
  removeTab,
  removeTabsByEntityId,
  setActiveTabId,
  reorderTabs,
  updateTabTitle,
  splitTab,
  updateSplitSizes,
  moveTabToGroup,
  mergeSplits,
  setFocusMode,
  toggleExpandedGroup,
  toggleExpandedPropertySection,
  setScrollPosition,
  resetWorkspace,
  loadWorkspaceFromStorage,
} = workspaceSlice.actions;

// =============================================================================
// Selectors
// =============================================================================

interface RootState {
  workspace: WorkspaceState;
}

export const selectLeftSidebarWidth = (state: RootState) =>
  state.workspace.leftSidebarWidth;

export const selectLeftSidebarCollapsed = (state: RootState) =>
  state.workspace.leftSidebarCollapsed;

export const selectRightSidebarWidth = (state: RootState) =>
  state.workspace.rightSidebarWidth;

export const selectRightSidebarCollapsed = (state: RootState) =>
  state.workspace.rightSidebarCollapsed;

export const selectRightSidebarPinned = (state: RootState) =>
  state.workspace.rightSidebarPinned;

export const selectBottomPanelHeight = (state: RootState) =>
  state.workspace.bottomPanelHeight;

export const selectBottomPanelCollapsed = (state: RootState) =>
  state.workspace.bottomPanelCollapsed;

export const selectActiveActivityId = (state: RootState) =>
  state.workspace.activeActivityId;

export const selectDockLayout = (state: RootState) =>
  state.workspace.dockLayout;

export const selectTabs = (state: RootState) => state.workspace.tabs;

export const selectActiveTabId = (state: RootState) =>
  state.workspace.activeTabId;

export const selectFocusMode = (state: RootState) => state.workspace.focusMode;

export const selectExpandedGroups = (state: RootState) =>
  state.workspace.expandedGroups;

export const selectExpandedPropertySections = (state: RootState) =>
  state.workspace.expandedPropertySections;

export const selectBottomPanelActiveTab = (state: RootState) =>
  state.workspace.bottomPanelActiveTab;

export const selectScrollPosition = (state: RootState, panelId: string) =>
  state.workspace.scrollPositions[panelId] ?? 0;

// =============================================================================
// Middleware for auto-save
// =============================================================================

/**
 * Middleware to auto-save workspace state to localStorage
 */
export const workspacePersistenceMiddleware =
  // eslint-disable-next-line @typescript-eslint/no-explicit-any
  (store: any) => (next: any) => (action: any) => {
    const result = next(action);

    // Save to localStorage on any workspace action
    if (action.type?.startsWith("workspace/")) {
      const state = store.getState();
      if (state.workspace) {
        saveToStorage(state.workspace);
      }
    }

    return result;
  };

export default workspaceSlice.reducer;
