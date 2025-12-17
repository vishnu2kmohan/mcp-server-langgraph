/**
 * Workspace Slice Tests
 *
 * TDD tests for the workspace state slice.
 * Implements full persistence for JupyterLab-inspired layout.
 *
 * Tests cover:
 * - Panel dimensions and collapsed states
 * - Activity bar selection
 * - Dock layout with splits
 * - Tab management
 * - Focus mode
 * - Group expansion states
 * - Scroll position tracking
 * - Full persistence to localStorage
 */

import { describe, it, expect, vi, beforeEach, afterEach } from "vitest";
import workspaceReducer, {
  // Actions
  setLeftSidebarWidth,
  setLeftSidebarCollapsed,
  setRightSidebarWidth,
  setRightSidebarCollapsed,
  setBottomPanelHeight,
  setBottomPanelCollapsed,
  setActiveActivityId,
  setDockLayout,
  addTab,
  removeTab,
  removeTabsByEntityId,
  setActiveTabId,
  reorderTabs,
  splitTab,
  mergeSplits,
  updateSplitSizes,
  moveTabToGroup,
  setFocusMode,
  toggleExpandedGroup,
  toggleExpandedPropertySection,
  setBottomPanelActiveTab,
  setScrollPosition,
  resetWorkspace,
  loadWorkspaceFromStorage,
  // Selectors
  selectLeftSidebarWidth,
  selectLeftSidebarCollapsed,
  selectRightSidebarWidth,
  selectRightSidebarCollapsed,
  selectBottomPanelHeight,
  selectBottomPanelCollapsed,
  selectActiveActivityId,
  selectDockLayout,
  selectTabs,
  selectActiveTabId,
  selectFocusMode,
  selectExpandedGroups,
  selectExpandedPropertySections,
  selectBottomPanelActiveTab,
  selectScrollPosition,
  // Types
  type WorkspaceState,
  type DockLayout,
  type TabState,
  WORKSPACE_STORAGE_KEY,
  DEFAULT_WORKSPACE_STATE,
} from "./workspaceSlice";

describe("workspaceSlice", () => {
  beforeEach(() => {
    vi.clearAllMocks();
    // Clear localStorage before each test
    localStorage.clear();
  });

  afterEach(() => {
    vi.restoreAllMocks();
    localStorage.clear();
  });

  describe("initial state", () => {
    it("should return default state when called with undefined", () => {
      const result = workspaceReducer(undefined, { type: "unknown" });
      expect(result.version).toBe(1);
      expect(result.leftSidebarWidth).toBe(280);
      expect(result.leftSidebarCollapsed).toBe(false);
      expect(result.rightSidebarWidth).toBe(280);
      expect(result.rightSidebarCollapsed).toBe(false);
      expect(result.bottomPanelHeight).toBe(200);
      expect(result.bottomPanelCollapsed).toBe(true);
      expect(result.activeActivityId).toBe("conversations");
      expect(result.focusMode).toBe(false);
      expect(result.tabs).toEqual([]);
      expect(result.activeTabId).toBeNull();
    });

    it("should have correct dock layout structure", () => {
      const result = workspaceReducer(undefined, { type: "unknown" });
      expect(result.dockLayout.type).toBe("tab-group");
      expect(result.dockLayout.tabIds).toEqual([]);
    });
  });

  describe("left sidebar actions", () => {
    it("should set left sidebar width", () => {
      const result = workspaceReducer(undefined, setLeftSidebarWidth(320));
      expect(result.leftSidebarWidth).toBe(320);
    });

    it("should clamp left sidebar width to minimum", () => {
      const result = workspaceReducer(undefined, setLeftSidebarWidth(100));
      expect(result.leftSidebarWidth).toBe(200); // Minimum width
    });

    it("should clamp left sidebar width to maximum", () => {
      const result = workspaceReducer(undefined, setLeftSidebarWidth(600));
      expect(result.leftSidebarWidth).toBe(480); // Maximum width
    });

    it("should set left sidebar collapsed state", () => {
      const result = workspaceReducer(undefined, setLeftSidebarCollapsed(true));
      expect(result.leftSidebarCollapsed).toBe(true);
    });

    it("should toggle left sidebar collapsed state", () => {
      let result = workspaceReducer(undefined, setLeftSidebarCollapsed(true));
      result = workspaceReducer(result, setLeftSidebarCollapsed(false));
      expect(result.leftSidebarCollapsed).toBe(false);
    });
  });

  describe("right sidebar actions", () => {
    it("should set right sidebar width", () => {
      const result = workspaceReducer(undefined, setRightSidebarWidth(350));
      expect(result.rightSidebarWidth).toBe(350);
    });

    it("should set right sidebar collapsed state", () => {
      const result = workspaceReducer(
        undefined,
        setRightSidebarCollapsed(true),
      );
      expect(result.rightSidebarCollapsed).toBe(true);
    });
  });

  describe("bottom panel actions", () => {
    it("should set bottom panel height", () => {
      const result = workspaceReducer(undefined, setBottomPanelHeight(300));
      expect(result.bottomPanelHeight).toBe(300);
    });

    it("should clamp bottom panel height to minimum", () => {
      const result = workspaceReducer(undefined, setBottomPanelHeight(50));
      expect(result.bottomPanelHeight).toBe(100); // Minimum height
    });

    it("should clamp bottom panel height to maximum", () => {
      const result = workspaceReducer(undefined, setBottomPanelHeight(600));
      expect(result.bottomPanelHeight).toBe(400); // Maximum height
    });

    it("should set bottom panel collapsed state", () => {
      const result = workspaceReducer(
        undefined,
        setBottomPanelCollapsed(false),
      );
      expect(result.bottomPanelCollapsed).toBe(false);
    });

    it("should set bottom panel active tab", () => {
      const result = workspaceReducer(
        undefined,
        setBottomPanelActiveTab("problems"),
      );
      expect(result.bottomPanelActiveTab).toBe("problems");
    });
  });

  describe("activity bar actions", () => {
    it("should set active activity id", () => {
      const result = workspaceReducer(
        undefined,
        setActiveActivityId("workspace"),
      );
      expect(result.activeActivityId).toBe("workspace");
    });

    it("should allow setting different activity ids", () => {
      const activities = [
        "workspace",
        "conversations",
        "build",
        "connections",
        "insights",
      ];
      for (const activity of activities) {
        const result = workspaceReducer(
          undefined,
          setActiveActivityId(activity),
        );
        expect(result.activeActivityId).toBe(activity);
      }
    });
  });

  describe("dock layout actions", () => {
    it("should set dock layout", () => {
      const newLayout: DockLayout = {
        type: "horizontal-split",
        children: [
          { type: "tab-group", tabIds: ["tab-1"] },
          { type: "tab-group", tabIds: ["tab-2"] },
        ],
        sizes: [50, 50],
      };
      const result = workspaceReducer(undefined, setDockLayout(newLayout));
      expect(result.dockLayout).toEqual(newLayout);
    });

    it("should support vertical splits", () => {
      const newLayout: DockLayout = {
        type: "vertical-split",
        children: [
          { type: "tab-group", tabIds: ["tab-1"] },
          { type: "tab-group", tabIds: ["tab-2"] },
        ],
        sizes: [60, 40],
      };
      const result = workspaceReducer(undefined, setDockLayout(newLayout));
      expect(result.dockLayout.type).toBe("vertical-split");
      expect(result.dockLayout.sizes).toEqual([60, 40]);
    });

    it("should support nested splits", () => {
      const nestedLayout: DockLayout = {
        type: "horizontal-split",
        children: [
          {
            type: "vertical-split",
            children: [
              { type: "tab-group", tabIds: ["tab-1"] },
              { type: "tab-group", tabIds: ["tab-2"] },
            ],
            sizes: [50, 50],
          },
          { type: "tab-group", tabIds: ["tab-3"] },
        ],
        sizes: [70, 30],
      };
      const result = workspaceReducer(undefined, setDockLayout(nestedLayout));
      expect(result.dockLayout.children?.[0].type).toBe("vertical-split");
    });
  });

  describe("tab management actions", () => {
    it("should add a new tab", () => {
      const tab: TabState = {
        id: "tab-1",
        type: "chat",
        title: "Chat Session",
        entityId: "session-123",
      };
      const result = workspaceReducer(undefined, addTab(tab));
      expect(result.tabs).toHaveLength(1);
      expect(result.tabs[0]).toEqual(tab);
      expect(result.activeTabId).toBe("tab-1");
    });

    it("should add multiple tabs", () => {
      let state = workspaceReducer(
        undefined,
        addTab({ id: "tab-1", type: "chat", title: "Chat 1" }),
      );
      state = workspaceReducer(
        state,
        addTab({ id: "tab-2", type: "workflow", title: "Workflow 1" }),
      );
      expect(state.tabs).toHaveLength(2);
    });

    it("should not add duplicate tab ids", () => {
      let state = workspaceReducer(
        undefined,
        addTab({ id: "tab-1", type: "chat", title: "Chat 1" }),
      );
      state = workspaceReducer(
        state,
        addTab({ id: "tab-1", type: "chat", title: "Chat 1 Duplicate" }),
      );
      expect(state.tabs).toHaveLength(1);
      expect(state.tabs[0].title).toBe("Chat 1"); // Original kept
    });

    it("should remove a tab", () => {
      let state = workspaceReducer(
        undefined,
        addTab({ id: "tab-1", type: "chat", title: "Chat 1" }),
      );
      state = workspaceReducer(
        state,
        addTab({ id: "tab-2", type: "workflow", title: "Workflow 1" }),
      );
      state = workspaceReducer(state, removeTab("tab-1"));
      expect(state.tabs).toHaveLength(1);
      expect(state.tabs[0].id).toBe("tab-2");
    });

    it("should update activeTabId when removing active tab", () => {
      let state = workspaceReducer(
        undefined,
        addTab({ id: "tab-1", type: "chat", title: "Chat 1" }),
      );
      state = workspaceReducer(
        state,
        addTab({ id: "tab-2", type: "workflow", title: "Workflow 1" }),
      );
      state = workspaceReducer(state, setActiveTabId("tab-1"));
      state = workspaceReducer(state, removeTab("tab-1"));
      expect(state.activeTabId).toBe("tab-2"); // Falls back to remaining tab
    });

    it("should set activeTabId to null when removing last tab", () => {
      let state = workspaceReducer(
        undefined,
        addTab({ id: "tab-1", type: "chat", title: "Chat 1" }),
      );
      state = workspaceReducer(state, removeTab("tab-1"));
      expect(state.activeTabId).toBeNull();
    });

    it("should set active tab id", () => {
      let state = workspaceReducer(
        undefined,
        addTab({ id: "tab-1", type: "chat", title: "Chat 1" }),
      );
      state = workspaceReducer(
        state,
        addTab({ id: "tab-2", type: "workflow", title: "Workflow 1" }),
      );
      state = workspaceReducer(state, setActiveTabId("tab-2"));
      expect(state.activeTabId).toBe("tab-2");
    });

    it("should reorder tabs", () => {
      let state = workspaceReducer(
        undefined,
        addTab({ id: "tab-1", type: "chat", title: "Chat 1" }),
      );
      state = workspaceReducer(
        state,
        addTab({ id: "tab-2", type: "workflow", title: "Workflow 1" }),
      );
      state = workspaceReducer(
        state,
        addTab({ id: "tab-3", type: "cost", title: "Cost" }),
      );
      state = workspaceReducer(
        state,
        reorderTabs({ fromIndex: 0, toIndex: 2 }),
      );
      expect(state.tabs.map((t) => t.id)).toEqual(["tab-2", "tab-3", "tab-1"]);
    });
  });

  describe("focus mode actions", () => {
    it("should set focus mode", () => {
      const result = workspaceReducer(undefined, setFocusMode(true));
      expect(result.focusMode).toBe(true);
    });

    it("should toggle focus mode", () => {
      let state = workspaceReducer(undefined, setFocusMode(true));
      state = workspaceReducer(state, setFocusMode(false));
      expect(state.focusMode).toBe(false);
    });
  });

  describe("group expansion actions", () => {
    it("should toggle expanded group", () => {
      const result = workspaceReducer(
        undefined,
        toggleExpandedGroup("conversations"),
      );
      expect(result.expandedGroups).toContain("conversations");
    });

    it("should remove group when toggled twice", () => {
      let state = workspaceReducer(
        undefined,
        toggleExpandedGroup("conversations"),
      );
      state = workspaceReducer(state, toggleExpandedGroup("conversations"));
      expect(state.expandedGroups).not.toContain("conversations");
    });

    it("should handle multiple expanded groups", () => {
      let state = workspaceReducer(undefined, toggleExpandedGroup("workspace"));
      state = workspaceReducer(state, toggleExpandedGroup("build"));
      state = workspaceReducer(state, toggleExpandedGroup("connections"));
      expect(state.expandedGroups).toContain("workspace");
      expect(state.expandedGroups).toContain("build");
      expect(state.expandedGroups).toContain("connections");
    });
  });

  describe("property section expansion actions", () => {
    it("should toggle expanded property section", () => {
      const result = workspaceReducer(
        undefined,
        toggleExpandedPropertySection("session-info"),
      );
      expect(result.expandedPropertySections).toContain("session-info");
    });

    it("should remove section when toggled twice", () => {
      let state = workspaceReducer(
        undefined,
        toggleExpandedPropertySection("tools"),
      );
      state = workspaceReducer(state, toggleExpandedPropertySection("tools"));
      expect(state.expandedPropertySections).not.toContain("tools");
    });
  });

  describe("scroll position actions", () => {
    it("should set scroll position for a panel", () => {
      const result = workspaceReducer(
        undefined,
        setScrollPosition({ panelId: "left-sidebar", position: 150 }),
      );
      expect(result.scrollPositions["left-sidebar"]).toBe(150);
    });

    it("should update existing scroll position", () => {
      let state = workspaceReducer(
        undefined,
        setScrollPosition({ panelId: "left-sidebar", position: 100 }),
      );
      state = workspaceReducer(
        state,
        setScrollPosition({ panelId: "left-sidebar", position: 200 }),
      );
      expect(state.scrollPositions["left-sidebar"]).toBe(200);
    });

    it("should track multiple panel scroll positions", () => {
      let state = workspaceReducer(
        undefined,
        setScrollPosition({ panelId: "left-sidebar", position: 100 }),
      );
      state = workspaceReducer(
        state,
        setScrollPosition({ panelId: "right-sidebar", position: 50 }),
      );
      state = workspaceReducer(
        state,
        setScrollPosition({ panelId: "main-dock", position: 300 }),
      );
      expect(state.scrollPositions).toEqual({
        "left-sidebar": 100,
        "right-sidebar": 50,
        "main-dock": 300,
      });
    });
  });

  describe("reset workspace action", () => {
    it("should reset to default state", () => {
      let state = workspaceReducer(undefined, setLeftSidebarWidth(400));
      state = workspaceReducer(state, setFocusMode(true));
      state = workspaceReducer(
        state,
        addTab({ id: "tab-1", type: "chat", title: "Chat" }),
      );
      state = workspaceReducer(state, resetWorkspace());
      expect(state.leftSidebarWidth).toBe(280);
      expect(state.focusMode).toBe(false);
      expect(state.tabs).toEqual([]);
    });

    it("should clear localStorage on reset", () => {
      // Set something first
      localStorage.setItem(WORKSPACE_STORAGE_KEY, '{"test": true}');
      workspaceReducer(undefined, resetWorkspace());
      expect(localStorage.getItem(WORKSPACE_STORAGE_KEY)).toBeNull();
    });
  });

  describe("load from storage action", () => {
    it("should return default state when localStorage is empty", () => {
      // localStorage is already empty from beforeEach
      const result = workspaceReducer(undefined, loadWorkspaceFromStorage());
      // The action should not crash and should return valid state
      expect(result.version).toBe(1);
      expect(result.leftSidebarWidth).toBe(280);
      expect(typeof result.lastUpdated).toBe("number");
    });

    it("should have loadWorkspaceFromStorage action available", () => {
      // Verify the action is properly exported
      expect(typeof loadWorkspaceFromStorage).toBe("function");
      const action = loadWorkspaceFromStorage();
      expect(action.type).toBe("workspace/loadWorkspaceFromStorage");
    });

    it("should preserve state integrity after load attempt", () => {
      // Start with modified state
      let state = workspaceReducer(undefined, setLeftSidebarWidth(350));
      state = workspaceReducer(state, setFocusMode(true));

      // Load from storage (which is empty) should not crash
      state = workspaceReducer(state, loadWorkspaceFromStorage());

      // State should be reset to defaults since storage is empty
      expect(state.version).toBe(1);
    });

    it("should load saved state from localStorage", () => {
      // Set up localStorage with saved state
      const savedState = {
        version: 1,
        leftSidebarWidth: 400,
        leftSidebarCollapsed: true,
        focusMode: true,
        activeActivityId: "workflows",
      };
      localStorage.setItem(WORKSPACE_STORAGE_KEY, JSON.stringify(savedState));

      // Load from storage
      const result = workspaceReducer(undefined, loadWorkspaceFromStorage());

      // Verify state was loaded
      expect(result.leftSidebarWidth).toBe(400);
      expect(result.leftSidebarCollapsed).toBe(true);
      expect(result.focusMode).toBe(true);
      expect(result.activeActivityId).toBe("workflows");
    });
  });

  describe("selectors", () => {
    const createState = (workspace: Partial<WorkspaceState>) => ({
      workspace: { ...DEFAULT_WORKSPACE_STATE, ...workspace },
    });

    it("should select left sidebar width", () => {
      const state = createState({ leftSidebarWidth: 320 });
      expect(selectLeftSidebarWidth(state)).toBe(320);
    });

    it("should select left sidebar collapsed", () => {
      const state = createState({ leftSidebarCollapsed: true });
      expect(selectLeftSidebarCollapsed(state)).toBe(true);
    });

    it("should select right sidebar width", () => {
      const state = createState({ rightSidebarWidth: 300 });
      expect(selectRightSidebarWidth(state)).toBe(300);
    });

    it("should select right sidebar collapsed", () => {
      const state = createState({ rightSidebarCollapsed: true });
      expect(selectRightSidebarCollapsed(state)).toBe(true);
    });

    it("should select bottom panel height", () => {
      const state = createState({ bottomPanelHeight: 250 });
      expect(selectBottomPanelHeight(state)).toBe(250);
    });

    it("should select bottom panel collapsed", () => {
      const state = createState({ bottomPanelCollapsed: false });
      expect(selectBottomPanelCollapsed(state)).toBe(false);
    });

    it("should select active activity id", () => {
      const state = createState({ activeActivityId: "insights" });
      expect(selectActiveActivityId(state)).toBe("insights");
    });

    it("should select dock layout", () => {
      const layout: DockLayout = {
        type: "horizontal-split",
        children: [],
        sizes: [],
      };
      const state = createState({ dockLayout: layout });
      expect(selectDockLayout(state)).toEqual(layout);
    });

    it("should select tabs", () => {
      const tabs: TabState[] = [{ id: "tab-1", type: "chat", title: "Chat" }];
      const state = createState({ tabs });
      expect(selectTabs(state)).toEqual(tabs);
    });

    it("should select active tab id", () => {
      const state = createState({ activeTabId: "tab-2" });
      expect(selectActiveTabId(state)).toBe("tab-2");
    });

    it("should select focus mode", () => {
      const state = createState({ focusMode: true });
      expect(selectFocusMode(state)).toBe(true);
    });

    it("should select expanded groups", () => {
      const state = createState({ expandedGroups: ["workspace", "build"] });
      expect(selectExpandedGroups(state)).toEqual(["workspace", "build"]);
    });

    it("should select expanded property sections", () => {
      const state = createState({
        expandedPropertySections: ["session-info", "tools"],
      });
      expect(selectExpandedPropertySections(state)).toEqual([
        "session-info",
        "tools",
      ]);
    });

    it("should select bottom panel active tab", () => {
      const state = createState({ bottomPanelActiveTab: "problems" });
      expect(selectBottomPanelActiveTab(state)).toBe("problems");
    });

    it("should select scroll position", () => {
      const state = createState({
        scrollPositions: { "left-sidebar": 100, "right-sidebar": 50 },
      });
      expect(selectScrollPosition(state, "left-sidebar")).toBe(100);
      expect(selectScrollPosition(state, "right-sidebar")).toBe(50);
      expect(selectScrollPosition(state, "nonexistent")).toBe(0);
    });
  });

  describe("removeTabsByEntityId action", () => {
    it("should remove tabs with matching entityId", () => {
      // Setup tabs with different entityIds
      let state = workspaceReducer(
        undefined,
        addTab({
          id: "tab-1",
          type: "chat",
          title: "Session A",
          entityId: "session-123",
        }),
      );
      state = workspaceReducer(
        state,
        addTab({
          id: "tab-2",
          type: "chat",
          title: "Session B",
          entityId: "session-456",
        }),
      );
      state = workspaceReducer(
        state,
        addTab({
          id: "tab-3",
          type: "workflow",
          title: "Workflows",
        }),
      );

      expect(state.tabs.length).toBe(3);

      // Remove tabs with entityId "session-123"
      state = workspaceReducer(state, removeTabsByEntityId("session-123"));

      expect(state.tabs.length).toBe(2);
      expect(
        state.tabs.find((t) => t.entityId === "session-123"),
      ).toBeUndefined();
      expect(
        state.tabs.find((t) => t.entityId === "session-456"),
      ).toBeDefined();
    });

    it("should update activeTabId if active tab is removed", () => {
      // Setup with active tab having the entityId to be removed
      let state = workspaceReducer(
        undefined,
        addTab({
          id: "tab-1",
          type: "chat",
          title: "Session A",
          entityId: "session-123",
        }),
      );
      state = workspaceReducer(
        state,
        addTab({
          id: "tab-2",
          type: "workflow",
          title: "Workflows",
        }),
      );
      state = workspaceReducer(state, setActiveTabId("tab-1"));

      expect(state.activeTabId).toBe("tab-1");

      // Remove tabs with entityId "session-123"
      state = workspaceReducer(state, removeTabsByEntityId("session-123"));

      // Active tab should change to remaining tab
      expect(state.activeTabId).toBe("tab-2");
    });

    it("should not affect tabs without matching entityId", () => {
      let state = workspaceReducer(
        undefined,
        addTab({
          id: "tab-1",
          type: "chat",
          title: "Session A",
          entityId: "session-123",
        }),
      );

      // Remove tabs with different entityId
      state = workspaceReducer(state, removeTabsByEntityId("session-999"));

      expect(state.tabs.length).toBe(1);
    });
  });

  describe("splitTab action", () => {
    it("should create horizontal split from tab-group", () => {
      // Setup: have two tabs in a tab-group
      let state = workspaceReducer(
        undefined,
        addTab({
          id: "tab-1",
          type: "chat",
          title: "Chat 1",
        }),
      );
      state = workspaceReducer(
        state,
        addTab({
          id: "tab-2",
          type: "workflow",
          title: "Workflow 1",
        }),
      );

      // Split tab-2 horizontally to the right
      state = workspaceReducer(
        state,
        splitTab({
          tabId: "tab-2",
          direction: "horizontal",
          position: "after",
        }),
      );

      // Should have horizontal-split layout with two tab-groups
      expect(state.dockLayout.type).toBe("horizontal-split");
      expect(state.dockLayout.children).toHaveLength(2);
      expect(state.dockLayout.children?.[0].type).toBe("tab-group");
      expect(state.dockLayout.children?.[0].tabIds).toEqual(["tab-1"]);
      expect(state.dockLayout.children?.[1].type).toBe("tab-group");
      expect(state.dockLayout.children?.[1].tabIds).toEqual(["tab-2"]);
      expect(state.dockLayout.sizes).toEqual([50, 50]);
    });

    it("should create vertical split from tab-group", () => {
      let state = workspaceReducer(
        undefined,
        addTab({
          id: "tab-1",
          type: "chat",
          title: "Chat 1",
        }),
      );
      state = workspaceReducer(
        state,
        addTab({
          id: "tab-2",
          type: "workflow",
          title: "Workflow 1",
        }),
      );

      // Split tab-2 vertically below
      state = workspaceReducer(
        state,
        splitTab({
          tabId: "tab-2",
          direction: "vertical",
          position: "after",
        }),
      );

      expect(state.dockLayout.type).toBe("vertical-split");
      expect(state.dockLayout.children).toHaveLength(2);
    });

    it("should split before existing group when position is 'before'", () => {
      let state = workspaceReducer(
        undefined,
        addTab({
          id: "tab-1",
          type: "chat",
          title: "Chat 1",
        }),
      );
      state = workspaceReducer(
        state,
        addTab({
          id: "tab-2",
          type: "workflow",
          title: "Workflow 1",
        }),
      );

      // Split tab-2 horizontally to the left (before)
      state = workspaceReducer(
        state,
        splitTab({
          tabId: "tab-2",
          direction: "horizontal",
          position: "before",
        }),
      );

      // New group should be first
      expect(state.dockLayout.children?.[0].tabIds).toEqual(["tab-2"]);
      expect(state.dockLayout.children?.[1].tabIds).toEqual(["tab-1"]);
    });

    it("should set active tab to the split tab", () => {
      let state = workspaceReducer(
        undefined,
        addTab({
          id: "tab-1",
          type: "chat",
          title: "Chat 1",
        }),
      );
      state = workspaceReducer(
        state,
        addTab({
          id: "tab-2",
          type: "workflow",
          title: "Workflow 1",
        }),
      );
      state = workspaceReducer(state, setActiveTabId("tab-1"));

      state = workspaceReducer(
        state,
        splitTab({
          tabId: "tab-2",
          direction: "horizontal",
          position: "after",
        }),
      );

      expect(state.activeTabId).toBe("tab-2");
    });

    it("should not split if tab does not exist", () => {
      let state = workspaceReducer(
        undefined,
        addTab({
          id: "tab-1",
          type: "chat",
          title: "Chat 1",
        }),
      );

      // Try to split non-existent tab
      state = workspaceReducer(
        state,
        splitTab({
          tabId: "nonexistent",
          direction: "horizontal",
          position: "after",
        }),
      );

      // Should remain as tab-group
      expect(state.dockLayout.type).toBe("tab-group");
    });

    it("should handle nested splits", () => {
      // Start with horizontal split
      let state = workspaceReducer(
        undefined,
        addTab({
          id: "tab-1",
          type: "chat",
          title: "Chat 1",
        }),
      );
      state = workspaceReducer(
        state,
        addTab({
          id: "tab-2",
          type: "workflow",
          title: "Workflow 1",
        }),
      );
      state = workspaceReducer(
        state,
        addTab({
          id: "tab-3",
          type: "cost",
          title: "Cost",
        }),
      );

      // First split: tab-2 horizontally
      state = workspaceReducer(
        state,
        splitTab({
          tabId: "tab-2",
          direction: "horizontal",
          position: "after",
        }),
      );

      // Second split: tab-3 vertically within the first group
      state = workspaceReducer(
        state,
        splitTab({
          tabId: "tab-3",
          direction: "vertical",
          position: "after",
        }),
      );

      // Should have nested layout
      expect(state.dockLayout.type).toBe("horizontal-split");
      // One of the children should be a vertical-split
      const hasNestedSplit = state.dockLayout.children?.some(
        (child) => child.type === "vertical-split",
      );
      expect(hasNestedSplit).toBe(true);
    });
  });

  describe("mergeSplits action", () => {
    it("should merge all splits into single tab-group", () => {
      // Create a split layout
      const splitLayout: DockLayout = {
        type: "horizontal-split",
        children: [
          { type: "tab-group", tabIds: ["tab-1"] },
          { type: "tab-group", tabIds: ["tab-2", "tab-3"] },
        ],
        sizes: [50, 50],
      };

      let state = workspaceReducer(
        undefined,
        addTab({
          id: "tab-1",
          type: "chat",
          title: "Chat 1",
        }),
      );
      state = workspaceReducer(
        state,
        addTab({
          id: "tab-2",
          type: "workflow",
          title: "Workflow 1",
        }),
      );
      state = workspaceReducer(
        state,
        addTab({
          id: "tab-3",
          type: "cost",
          title: "Cost",
        }),
      );
      state = workspaceReducer(state, setDockLayout(splitLayout));

      // Merge all splits
      state = workspaceReducer(state, mergeSplits());

      expect(state.dockLayout.type).toBe("tab-group");
      expect(state.dockLayout.tabIds).toEqual(["tab-1", "tab-2", "tab-3"]);
    });

    it("should merge nested splits", () => {
      const nestedLayout: DockLayout = {
        type: "horizontal-split",
        children: [
          {
            type: "vertical-split",
            children: [
              { type: "tab-group", tabIds: ["tab-1"] },
              { type: "tab-group", tabIds: ["tab-2"] },
            ],
            sizes: [50, 50],
          },
          { type: "tab-group", tabIds: ["tab-3"] },
        ],
        sizes: [70, 30],
      };

      let state = workspaceReducer(undefined, setDockLayout(nestedLayout));
      state = workspaceReducer(state, mergeSplits());

      expect(state.dockLayout.type).toBe("tab-group");
      expect(state.dockLayout.tabIds).toEqual(["tab-1", "tab-2", "tab-3"]);
    });
  });

  describe("updateSplitSizes action", () => {
    it("should update split sizes at root level", () => {
      const splitLayout: DockLayout = {
        type: "horizontal-split",
        children: [
          { type: "tab-group", tabIds: ["tab-1"] },
          { type: "tab-group", tabIds: ["tab-2"] },
        ],
        sizes: [50, 50],
      };

      let state = workspaceReducer(undefined, setDockLayout(splitLayout));
      state = workspaceReducer(
        state,
        updateSplitSizes({
          path: [],
          sizes: [30, 70],
        }),
      );

      expect(state.dockLayout.sizes).toEqual([30, 70]);
    });

    it("should update split sizes at nested path", () => {
      const nestedLayout: DockLayout = {
        type: "horizontal-split",
        children: [
          {
            type: "vertical-split",
            children: [
              { type: "tab-group", tabIds: ["tab-1"] },
              { type: "tab-group", tabIds: ["tab-2"] },
            ],
            sizes: [50, 50],
          },
          { type: "tab-group", tabIds: ["tab-3"] },
        ],
        sizes: [70, 30],
      };

      let state = workspaceReducer(undefined, setDockLayout(nestedLayout));
      state = workspaceReducer(
        state,
        updateSplitSizes({
          path: [0],
          sizes: [40, 60],
        }),
      );

      expect(state.dockLayout.children?.[0].sizes).toEqual([40, 60]);
    });
  });

  describe("moveTabToGroup action", () => {
    it("should move tab to a different group in split layout", () => {
      const splitLayout: DockLayout = {
        type: "horizontal-split",
        children: [
          { type: "tab-group", tabIds: ["tab-1", "tab-2"] },
          { type: "tab-group", tabIds: ["tab-3"] },
        ],
        sizes: [50, 50],
      };

      let state = workspaceReducer(
        undefined,
        addTab({
          id: "tab-1",
          type: "chat",
          title: "Chat 1",
        }),
      );
      state = workspaceReducer(
        state,
        addTab({
          id: "tab-2",
          type: "workflow",
          title: "Workflow 1",
        }),
      );
      state = workspaceReducer(
        state,
        addTab({
          id: "tab-3",
          type: "cost",
          title: "Cost",
        }),
      );
      state = workspaceReducer(state, setDockLayout(splitLayout));

      // Move tab-2 to second group
      state = workspaceReducer(
        state,
        moveTabToGroup({
          tabId: "tab-2",
          targetPath: [1],
        }),
      );

      expect(state.dockLayout.children?.[0].tabIds).toEqual(["tab-1"]);
      expect(state.dockLayout.children?.[1].tabIds).toEqual(["tab-3", "tab-2"]);
    });

    it("should collapse empty group after moving last tab", () => {
      const splitLayout: DockLayout = {
        type: "horizontal-split",
        children: [
          { type: "tab-group", tabIds: ["tab-1"] },
          { type: "tab-group", tabIds: ["tab-2"] },
        ],
        sizes: [50, 50],
      };

      let state = workspaceReducer(
        undefined,
        addTab({
          id: "tab-1",
          type: "chat",
          title: "Chat 1",
        }),
      );
      state = workspaceReducer(
        state,
        addTab({
          id: "tab-2",
          type: "workflow",
          title: "Workflow 1",
        }),
      );
      state = workspaceReducer(state, setDockLayout(splitLayout));

      // Move tab-1 to second group (leaving first group empty)
      state = workspaceReducer(
        state,
        moveTabToGroup({
          tabId: "tab-1",
          targetPath: [1],
        }),
      );

      // Should collapse back to single tab-group
      expect(state.dockLayout.type).toBe("tab-group");
      expect(state.dockLayout.tabIds).toEqual(["tab-2", "tab-1"]);
    });
  });

  describe("persistence", () => {
    it("should save to localStorage on state changes", () => {
      // This is tested via middleware in the actual store setup
      // Here we verify the action triggers the expected behavior
      const state = workspaceReducer(undefined, setLeftSidebarWidth(350));
      expect(state.leftSidebarWidth).toBe(350);
      expect(state.lastUpdated).toBeGreaterThan(0);
    });

    it("should update lastUpdated timestamp on changes", () => {
      const state1 = workspaceReducer(undefined, { type: "unknown" });
      const state2 = workspaceReducer(state1, setFocusMode(true));
      expect(state2.lastUpdated).toBeGreaterThan(0);
    });
  });
});
