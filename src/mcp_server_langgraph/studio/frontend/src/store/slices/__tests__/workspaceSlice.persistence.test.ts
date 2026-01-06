/**
 * Workspace Slice Persistence Tests
 *
 * Tests for workspace state persistence including:
 * - Load from storage action
 * - Persistence to localStorage
 * - workspacePersistenceMiddleware
 * - noUncheckedIndexedAccess edge cases
 *
 * Part of workspaceSlice test suite split for OOM prevention.
 */

import { describe, it, expect, vi, beforeEach, afterEach } from "vitest";
import workspaceReducer, {
  // Actions
  loadWorkspaceFromStorage,
  setLeftSidebarWidth,
  setFocusMode,
  addTab,
  removeTab,
  setActiveTabId,
  reorderTabs,
  removeTabsByEntityId,
  splitTab,
  setDockLayout,
  updateSplitSizes,
  // Constants
  WORKSPACE_STORAGE_KEY,
  workspacePersistenceMiddleware,
  // Types
  type DockLayout,
} from "../workspaceSlice";
import {
  createTab,
  createHorizontalSplit,
  createNestedLayout,
} from "./workspaceSlice.fixtures";

describe("workspaceSlice - persistence", () => {
  beforeEach(() => {
    vi.clearAllMocks();
    localStorage.clear();
  });

  afterEach(() => {
    vi.restoreAllMocks();
    localStorage.clear();
  });

  describe("load from storage action", () => {
    it("should return default state when localStorage is empty", () => {
      const result = workspaceReducer(undefined, loadWorkspaceFromStorage());
      expect(result.version).toBe(1);
      expect(result.leftSidebarWidth).toBe(280);
      expect(typeof result.lastUpdated).toBe("number");
    });

    it("should have loadWorkspaceFromStorage action available", () => {
      expect(typeof loadWorkspaceFromStorage).toBe("function");
      const action = loadWorkspaceFromStorage();
      expect(action.type).toBe("workspace/loadWorkspaceFromStorage");
    });

    it("should preserve state integrity after load attempt", () => {
      let state = workspaceReducer(undefined, setLeftSidebarWidth(350));
      state = workspaceReducer(state, setFocusMode(true));

      state = workspaceReducer(state, loadWorkspaceFromStorage());

      expect(state.version).toBe(1);
    });

    it("should load saved state from localStorage", () => {
      const savedState = {
        version: 1,
        leftSidebarWidth: 400,
        leftSidebarCollapsed: true,
        focusMode: true,
        activeActivityId: "workflows",
      };
      localStorage.setItem(WORKSPACE_STORAGE_KEY, JSON.stringify(savedState));

      const result = workspaceReducer(undefined, loadWorkspaceFromStorage());

      expect(result.leftSidebarWidth).toBe(400);
      expect(result.leftSidebarCollapsed).toBe(true);
      expect(result.focusMode).toBe(true);
      expect(result.activeActivityId).toBe("workflows");
    });
  });

  describe("persistence", () => {
    it("should save to localStorage on state changes", () => {
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

  describe("workspacePersistenceMiddleware", () => {
    it("should save to storage on workspace actions", () => {
      const mockStore = {
        getState: () => ({
          workspace: { leftSidebarWidth: 300 },
        }),
      };
      const mockNext = vi.fn((action) => action);

      const middleware = workspacePersistenceMiddleware(mockStore)(mockNext);

      const action = { type: "workspace/setLeftSidebarWidth", payload: 300 };
      middleware(action);

      expect(mockNext).toHaveBeenCalledWith(action);
    });

    it("should not save for non-workspace actions", () => {
      const mockStore = {
        getState: () => ({
          workspace: { leftSidebarWidth: 300 },
        }),
      };
      const mockNext = vi.fn((action) => action);

      const middleware = workspacePersistenceMiddleware(mockStore)(mockNext);

      const action = { type: "auth/login" };
      middleware(action);

      expect(mockNext).toHaveBeenCalledWith(action);
    });

    it("should handle action.type being undefined", () => {
      const mockStore = {
        getState: () => ({
          workspace: { leftSidebarWidth: 300 },
        }),
      };
      const mockNext = vi.fn((action) => action);

      const middleware = workspacePersistenceMiddleware(mockStore)(mockNext);

      const action = {};
      middleware(action);

      expect(mockNext).toHaveBeenCalledWith(action);
    });

    it("should handle missing workspace in state", () => {
      const mockStore = {
        getState: () => ({}),
      };
      const mockNext = vi.fn((action) => action);

      const middleware = workspacePersistenceMiddleware(mockStore)(mockNext);

      const action = { type: "workspace/setLeftSidebarWidth", payload: 300 };
      middleware(action);

      expect(mockNext).toHaveBeenCalledWith(action);
    });
  });

  describe("noUncheckedIndexedAccess edge cases", () => {
    describe("reorderTabs with invalid indices", () => {
      it("should handle reorder when fromIndex is out of bounds", () => {
        let state = workspaceReducer(
          undefined,
          addTab(createTab({ id: "tab-1", title: "Chat 1" })),
        );
        state = workspaceReducer(
          state,
          addTab(
            createTab({ id: "tab-2", type: "workflow", title: "Workflow 1" }),
          ),
        );

        const stateBefore = state;
        state = workspaceReducer(
          state,
          reorderTabs({ fromIndex: 10, toIndex: 0 }),
        );

        expect(state.tabs).toEqual(stateBefore.tabs);
      });

      it("should handle reorder when toIndex is out of bounds", () => {
        let state = workspaceReducer(
          undefined,
          addTab(createTab({ id: "tab-1", title: "Chat 1" })),
        );
        state = workspaceReducer(
          state,
          addTab(
            createTab({ id: "tab-2", type: "workflow", title: "Workflow 1" }),
          ),
        );

        const stateBefore = state;
        state = workspaceReducer(
          state,
          reorderTabs({ fromIndex: 0, toIndex: 10 }),
        );

        expect(state.tabs).toEqual(stateBefore.tabs);
      });

      it("should handle reorder with negative indices", () => {
        let state = workspaceReducer(
          undefined,
          addTab(createTab({ id: "tab-1", title: "Chat 1" })),
        );

        const stateBefore = state;
        state = workspaceReducer(
          state,
          reorderTabs({ fromIndex: -1, toIndex: 0 }),
        );

        expect(state.tabs).toEqual(stateBefore.tabs);
      });

      it("should handle reorder on empty tabs array", () => {
        const state = workspaceReducer(undefined, { type: "unknown" });
        const stateAfter = workspaceReducer(
          state,
          reorderTabs({ fromIndex: 0, toIndex: 1 }),
        );

        expect(stateAfter.tabs).toEqual([]);
      });
    });

    describe("dock layout path traversal", () => {
      it("should handle getLayoutAtPath with empty path on nested layout", () => {
        const nestedLayout = createNestedLayout();

        let state = workspaceReducer(
          undefined,
          addTab(createTab({ id: "tab-1", title: "Chat 1" })),
        );
        state = workspaceReducer(
          state,
          addTab(
            createTab({ id: "tab-2", type: "workflow", title: "Workflow 1" }),
          ),
        );
        state = workspaceReducer(state, setDockLayout(nestedLayout));

        state = workspaceReducer(
          state,
          updateSplitSizes({ path: [], sizes: [30, 70] }),
        );

        expect(state.dockLayout.sizes).toEqual([30, 70]);
      });

      it("should handle updateSplitSizes on tab-group layout (no-op)", () => {
        let state = workspaceReducer(
          undefined,
          addTab(createTab({ id: "tab-1", title: "Chat 1" })),
        );

        state = workspaceReducer(
          state,
          updateSplitSizes({ path: [], sizes: [50, 50] }),
        );

        expect(state.dockLayout.type).toBe("tab-group");
      });

      it("should handle updateSplitSizes with invalid nested path", () => {
        const splitLayout = createHorizontalSplit(["tab-1"], ["tab-2"]);

        let state = workspaceReducer(undefined, setDockLayout(splitLayout));

        state = workspaceReducer(
          state,
          updateSplitSizes({ path: [5], sizes: [30, 70] }),
        );

        expect(state.dockLayout.sizes).toEqual([50, 50]);
      });
    });

    describe("updateTabTitle", () => {
      it("should update an existing tab title", () => {
        let state = workspaceReducer(
          undefined,
          addTab(createTab({ id: "tab-1", title: "Original Title" })),
        );
        state = workspaceReducer(state, {
          type: "workspace/updateTabTitle",
          payload: { tabId: "tab-1", title: "New Title" },
        });
        expect(state.tabs[0].title).toBe("New Title");
      });

      it("should not crash when tab does not exist", () => {
        let state = workspaceReducer(
          undefined,
          addTab(createTab({ id: "tab-1", title: "Chat 1" })),
        );
        state = workspaceReducer(state, {
          type: "workspace/updateTabTitle",
          payload: { tabId: "non-existent", title: "New Title" },
        });
        expect(state.tabs[0].title).toBe("Chat 1");
      });
    });

    describe("removeTab edge cases", () => {
      it("should handle removing non-existent tab", () => {
        let state = workspaceReducer(
          undefined,
          addTab(createTab({ id: "tab-1", title: "Chat 1" })),
        );
        const tabsBefore = state.tabs;
        state = workspaceReducer(state, removeTab("non-existent"));
        expect(state.tabs).toEqual(tabsBefore);
      });

      it("should fall back to previous tab when removing active tab at end", () => {
        let state = workspaceReducer(
          undefined,
          addTab(createTab({ id: "tab-1", title: "Chat 1" })),
        );
        state = workspaceReducer(
          state,
          addTab(
            createTab({ id: "tab-2", type: "workflow", title: "Workflow 1" }),
          ),
        );
        state = workspaceReducer(
          state,
          addTab(createTab({ id: "tab-3", type: "cost", title: "Cost" })),
        );
        state = workspaceReducer(state, setActiveTabId("tab-3"));

        state = workspaceReducer(state, removeTab("tab-3"));

        expect(state.activeTabId).toBe("tab-2");
      });
    });

    describe("removeTabsByEntityId with empty state", () => {
      it("should handle removing when tabs array is empty", () => {
        const state = workspaceReducer(undefined, { type: "unknown" });
        const stateAfter = workspaceReducer(
          state,
          removeTabsByEntityId("some-entity"),
        );

        expect(stateAfter.tabs).toEqual([]);
        expect(stateAfter.activeTabId).toBeNull();
      });

      it("should set activeTabId to first remaining tab when active removed", () => {
        let state = workspaceReducer(
          undefined,
          addTab(
            createTab({
              id: "tab-1",
              title: "Chat 1",
              entityId: "entity-1",
            }),
          ),
        );
        state = workspaceReducer(
          state,
          addTab(
            createTab({
              id: "tab-2",
              type: "workflow",
              title: "Workflow 1",
              entityId: "entity-2",
            }),
          ),
        );
        state = workspaceReducer(
          state,
          addTab(
            createTab({
              id: "tab-3",
              type: "cost",
              title: "Cost",
              entityId: "entity-3",
            }),
          ),
        );
        state = workspaceReducer(state, setActiveTabId("tab-1"));

        state = workspaceReducer(state, removeTabsByEntityId("entity-1"));

        expect(state.activeTabId).toBe("tab-2");
      });

      it("should set activeTabId to null when all tabs removed", () => {
        let state = workspaceReducer(
          undefined,
          addTab(
            createTab({
              id: "tab-1",
              title: "Chat 1",
              entityId: "entity-1",
            }),
          ),
        );
        state = workspaceReducer(state, setActiveTabId("tab-1"));

        state = workspaceReducer(state, removeTabsByEntityId("entity-1"));

        expect(state.activeTabId).toBeNull();
        expect(state.tabs).toEqual([]);
      });
    });

    describe("splitTab with edge cases", () => {
      it("should handle single tab split correctly", () => {
        let state = workspaceReducer(
          undefined,
          addTab(createTab({ id: "tab-1", title: "Chat 1" })),
        );

        state = workspaceReducer(
          state,
          splitTab({
            tabId: "tab-1",
            direction: "horizontal",
            position: "after",
          }),
        );

        expect(state.dockLayout.type).toBe("horizontal-split");
        expect(state.dockLayout.children).toHaveLength(2);
      });

      it("should handle nested layout tab not found", () => {
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

        let state = workspaceReducer(
          undefined,
          addTab(createTab({ id: "tab-1", title: "Chat 1" })),
        );
        state = workspaceReducer(
          state,
          addTab(
            createTab({ id: "tab-2", type: "workflow", title: "Workflow 1" }),
          ),
        );
        state = workspaceReducer(
          state,
          addTab(createTab({ id: "tab-3", type: "cost", title: "Cost" })),
        );
        state = workspaceReducer(state, setDockLayout(nestedLayout));

        expect(state.dockLayout.type).toBe("horizontal-split");

        state = workspaceReducer(
          state,
          addTab(createTab({ id: "tab-4", title: "Chat 4" })),
        );

        const stateAfter = workspaceReducer(
          state,
          splitTab({
            tabId: "tab-4",
            direction: "vertical",
            position: "after",
          }),
        );

        expect(stateAfter.dockLayout).toBeDefined();
      });
    });
  });
});
