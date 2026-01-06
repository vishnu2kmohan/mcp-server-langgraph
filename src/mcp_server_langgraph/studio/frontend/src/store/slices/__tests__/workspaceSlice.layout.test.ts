/**
 * Workspace Slice Layout Tests
 *
 * Tests for workspace layout state including:
 * - Initial state
 * - Left sidebar actions (width, collapsed)
 * - Right sidebar actions (width, collapsed, pinned)
 * - Bottom panel actions (height, collapsed, active tab)
 * - Activity bar actions
 * - Focus mode actions
 * - Scroll position actions
 * - Reset workspace action
 * - Selectors
 *
 * Part of workspaceSlice test suite split for OOM prevention.
 */

import { describe, it, expect, vi, beforeEach, afterEach } from "vitest";
import workspaceReducer, {
  // Actions
  setLeftSidebarWidth,
  setLeftSidebarCollapsed,
  setRightSidebarWidth,
  setRightSidebarCollapsed,
  setRightSidebarPinned,
  setBottomPanelHeight,
  setBottomPanelCollapsed,
  setActiveActivityId,
  setFocusMode,
  toggleExpandedGroup,
  toggleExpandedPropertySection,
  setBottomPanelActiveTab,
  setScrollPosition,
  resetWorkspace,
  addTab,
  // Selectors
  selectLeftSidebarWidth,
  selectLeftSidebarCollapsed,
  selectRightSidebarWidth,
  selectRightSidebarCollapsed,
  selectRightSidebarPinned,
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
  WORKSPACE_STORAGE_KEY,
} from "../workspaceSlice";
import {
  createMockState,
  createTab,
  TEST_ACTIVITIES,
} from "./workspaceSlice.fixtures";

describe("workspaceSlice - layout", () => {
  beforeEach(() => {
    vi.clearAllMocks();
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
      for (const activity of TEST_ACTIVITIES) {
        const result = workspaceReducer(
          undefined,
          setActiveActivityId(activity),
        );
        expect(result.activeActivityId).toBe(activity);
      }
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
        addTab(createTab({ id: "tab-1", title: "Chat" })),
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

  describe("setRightSidebarPinned action", () => {
    it("should set right sidebar pinned to true", () => {
      const state = workspaceReducer(undefined, setRightSidebarPinned(true));
      expect(state.rightSidebarPinned).toBe(true);
    });

    it("should set right sidebar pinned to false", () => {
      let state = workspaceReducer(undefined, setRightSidebarPinned(true));
      state = workspaceReducer(state, setRightSidebarPinned(false));
      expect(state.rightSidebarPinned).toBe(false);
    });

    it("should update lastUpdated timestamp", () => {
      const state = workspaceReducer(undefined, setRightSidebarPinned(true));
      expect(state.lastUpdated).toBeGreaterThan(0);
    });
  });

  describe("selectors", () => {
    it("should select left sidebar width", () => {
      const state = createMockState({ leftSidebarWidth: 320 });
      expect(selectLeftSidebarWidth(state)).toBe(320);
    });

    it("should select left sidebar collapsed", () => {
      const state = createMockState({ leftSidebarCollapsed: true });
      expect(selectLeftSidebarCollapsed(state)).toBe(true);
    });

    it("should select right sidebar width", () => {
      const state = createMockState({ rightSidebarWidth: 300 });
      expect(selectRightSidebarWidth(state)).toBe(300);
    });

    it("should select right sidebar collapsed", () => {
      const state = createMockState({ rightSidebarCollapsed: true });
      expect(selectRightSidebarCollapsed(state)).toBe(true);
    });

    it("should select bottom panel height", () => {
      const state = createMockState({ bottomPanelHeight: 250 });
      expect(selectBottomPanelHeight(state)).toBe(250);
    });

    it("should select bottom panel collapsed", () => {
      const state = createMockState({ bottomPanelCollapsed: false });
      expect(selectBottomPanelCollapsed(state)).toBe(false);
    });

    it("should select active activity id", () => {
      const state = createMockState({ activeActivityId: "insights" });
      expect(selectActiveActivityId(state)).toBe("insights");
    });

    it("should select dock layout", () => {
      const layout: DockLayout = {
        type: "horizontal-split",
        children: [],
        sizes: [],
      };
      const state = createMockState({ dockLayout: layout });
      expect(selectDockLayout(state)).toEqual(layout);
    });

    it("should select tabs", () => {
      const tabs = [createTab({ id: "tab-1", title: "Chat" })];
      const state = createMockState({ tabs });
      expect(selectTabs(state)).toEqual(tabs);
    });

    it("should select active tab id", () => {
      const state = createMockState({ activeTabId: "tab-2" });
      expect(selectActiveTabId(state)).toBe("tab-2");
    });

    it("should select focus mode", () => {
      const state = createMockState({ focusMode: true });
      expect(selectFocusMode(state)).toBe(true);
    });

    it("should select expanded groups", () => {
      const state = createMockState({ expandedGroups: ["workspace", "build"] });
      expect(selectExpandedGroups(state)).toEqual(["workspace", "build"]);
    });

    it("should select expanded property sections", () => {
      const state = createMockState({
        expandedPropertySections: ["session-info", "tools"],
      });
      expect(selectExpandedPropertySections(state)).toEqual([
        "session-info",
        "tools",
      ]);
    });

    it("should select bottom panel active tab", () => {
      const state = createMockState({ bottomPanelActiveTab: "problems" });
      expect(selectBottomPanelActiveTab(state)).toBe("problems");
    });

    it("should select scroll position", () => {
      const state = createMockState({
        scrollPositions: { "left-sidebar": 100, "right-sidebar": 50 },
      });
      expect(selectScrollPosition(state, "left-sidebar")).toBe(100);
      expect(selectScrollPosition(state, "right-sidebar")).toBe(50);
      expect(selectScrollPosition(state, "nonexistent")).toBe(0);
    });
  });

  describe("selectRightSidebarPinned selector", () => {
    it("should return rightSidebarPinned from state", () => {
      const state = workspaceReducer(undefined, setRightSidebarPinned(true));
      const rootState = { workspace: state } as { workspace: WorkspaceState };
      expect(selectRightSidebarPinned(rootState)).toBe(true);
    });

    it("should return false as default", () => {
      const state = workspaceReducer(undefined, { type: "unknown" });
      const rootState = { workspace: state } as { workspace: WorkspaceState };
      expect(selectRightSidebarPinned(rootState)).toBe(false);
    });
  });
});
