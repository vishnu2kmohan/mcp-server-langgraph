/**
 * Workspace Slice Tabs Tests
 *
 * Tests for workspace tab management including:
 * - Dock layout actions (splits)
 * - Tab management (add, remove, reorder, active)
 * - Group expansion
 * - removeTabsByEntityId action
 * - splitTab action
 * - mergeSplits action
 * - updateSplitSizes action
 * - moveTabToGroup action and edge cases
 *
 * Part of workspaceSlice test suite split for OOM prevention.
 */

import { describe, it, expect, vi, beforeEach, afterEach } from "vitest";
import workspaceReducer, {
  // Actions
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
  // Types
  type DockLayout,
} from "../workspaceSlice";
import {
  createTab,
  createHorizontalSplit,
  createVerticalSplit,
  createNestedLayout,
} from "./workspaceSlice.fixtures";

describe("workspaceSlice - tabs", () => {
  beforeEach(() => {
    vi.clearAllMocks();
    localStorage.clear();
  });

  afterEach(() => {
    vi.restoreAllMocks();
    localStorage.clear();
  });

  describe("dock layout actions", () => {
    it("should set dock layout", () => {
      const newLayout = createHorizontalSplit(["tab-1"], ["tab-2"]);
      const result = workspaceReducer(undefined, setDockLayout(newLayout));
      expect(result.dockLayout).toEqual(newLayout);
    });

    it("should support vertical splits", () => {
      const newLayout = createVerticalSplit(["tab-1"], ["tab-2"], [60, 40]);
      const result = workspaceReducer(undefined, setDockLayout(newLayout));
      expect(result.dockLayout.type).toBe("vertical-split");
      expect(result.dockLayout.sizes).toEqual([60, 40]);
    });

    it("should support nested splits", () => {
      const nestedLayout = createNestedLayout();
      const result = workspaceReducer(undefined, setDockLayout(nestedLayout));
      expect(result.dockLayout.children?.[0].type).toBe("vertical-split");
    });
  });

  describe("tab management actions", () => {
    it("should add a new tab", () => {
      const tab = createTab({
        id: "tab-1",
        title: "Chat Session",
        entityId: "session-123",
      });
      const result = workspaceReducer(undefined, addTab(tab));
      expect(result.tabs).toHaveLength(1);
      expect(result.tabs[0]).toEqual(tab);
      expect(result.activeTabId).toBe("tab-1");
    });

    it("should add multiple tabs", () => {
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
      expect(state.tabs).toHaveLength(2);
    });

    it("should not add duplicate tab ids", () => {
      let state = workspaceReducer(
        undefined,
        addTab(createTab({ id: "tab-1", title: "Chat 1" })),
      );
      state = workspaceReducer(
        state,
        addTab(createTab({ id: "tab-1", title: "Chat 1 Duplicate" })),
      );
      expect(state.tabs).toHaveLength(1);
      expect(state.tabs[0].title).toBe("Chat 1"); // Original kept
    });

    it("should remove a tab", () => {
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
      state = workspaceReducer(state, removeTab("tab-1"));
      expect(state.tabs).toHaveLength(1);
      expect(state.tabs[0].id).toBe("tab-2");
    });

    it("should update activeTabId when removing active tab", () => {
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
      state = workspaceReducer(state, setActiveTabId("tab-1"));
      state = workspaceReducer(state, removeTab("tab-1"));
      expect(state.activeTabId).toBe("tab-2"); // Falls back to remaining tab
    });

    it("should set activeTabId to null when removing last tab", () => {
      let state = workspaceReducer(
        undefined,
        addTab(createTab({ id: "tab-1", title: "Chat 1" })),
      );
      state = workspaceReducer(state, removeTab("tab-1"));
      expect(state.activeTabId).toBeNull();
    });

    it("should set active tab id", () => {
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
      state = workspaceReducer(state, setActiveTabId("tab-2"));
      expect(state.activeTabId).toBe("tab-2");
    });

    it("should reorder tabs", () => {
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
      state = workspaceReducer(
        state,
        reorderTabs({ fromIndex: 0, toIndex: 2 }),
      );
      expect(state.tabs.map((t) => t.id)).toEqual(["tab-2", "tab-3", "tab-1"]);
    });
  });

  describe("removeTabsByEntityId action", () => {
    it("should remove tabs with matching entityId", () => {
      let state = workspaceReducer(
        undefined,
        addTab(
          createTab({
            id: "tab-1",
            title: "Session A",
            entityId: "session-123",
          }),
        ),
      );
      state = workspaceReducer(
        state,
        addTab(
          createTab({
            id: "tab-2",
            title: "Session B",
            entityId: "session-456",
          }),
        ),
      );
      state = workspaceReducer(
        state,
        addTab(
          createTab({
            id: "tab-3",
            type: "workflow",
            title: "Workflows",
          }),
        ),
      );

      expect(state.tabs.length).toBe(3);

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
      let state = workspaceReducer(
        undefined,
        addTab(
          createTab({
            id: "tab-1",
            title: "Session A",
            entityId: "session-123",
          }),
        ),
      );
      state = workspaceReducer(
        state,
        addTab(
          createTab({
            id: "tab-2",
            type: "workflow",
            title: "Workflows",
          }),
        ),
      );
      state = workspaceReducer(state, setActiveTabId("tab-1"));

      expect(state.activeTabId).toBe("tab-1");

      state = workspaceReducer(state, removeTabsByEntityId("session-123"));

      expect(state.activeTabId).toBe("tab-2");
    });

    it("should not affect tabs without matching entityId", () => {
      let state = workspaceReducer(
        undefined,
        addTab(
          createTab({
            id: "tab-1",
            title: "Session A",
            entityId: "session-123",
          }),
        ),
      );

      state = workspaceReducer(state, removeTabsByEntityId("session-999"));

      expect(state.tabs.length).toBe(1);
    });
  });

  describe("splitTab action", () => {
    it("should create horizontal split from tab-group", () => {
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
        splitTab({
          tabId: "tab-2",
          direction: "horizontal",
          position: "after",
        }),
      );

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
        splitTab({
          tabId: "tab-2",
          direction: "horizontal",
          position: "before",
        }),
      );

      expect(state.dockLayout.children?.[0].tabIds).toEqual(["tab-2"]);
      expect(state.dockLayout.children?.[1].tabIds).toEqual(["tab-1"]);
    });

    it("should set active tab to the split tab", () => {
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
        addTab(createTab({ id: "tab-1", title: "Chat 1" })),
      );

      state = workspaceReducer(
        state,
        splitTab({
          tabId: "nonexistent",
          direction: "horizontal",
          position: "after",
        }),
      );

      expect(state.dockLayout.type).toBe("tab-group");
    });

    it("should handle nested splits", () => {
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

      expect(state.dockLayout.type).toBe("horizontal-split");
      const hasNestedSplit = state.dockLayout.children?.some(
        (child) => child.type === "vertical-split",
      );
      expect(hasNestedSplit).toBe(true);
    });
  });

  describe("mergeSplits action", () => {
    it("should merge all splits into single tab-group", () => {
      const splitLayout = createHorizontalSplit(["tab-1"], ["tab-2", "tab-3"]);

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
      state = workspaceReducer(state, setDockLayout(splitLayout));

      state = workspaceReducer(state, mergeSplits());

      expect(state.dockLayout.type).toBe("tab-group");
      expect(state.dockLayout.tabIds).toEqual(["tab-1", "tab-2", "tab-3"]);
    });

    it("should merge nested splits", () => {
      const nestedLayout = createNestedLayout();

      let state = workspaceReducer(undefined, setDockLayout(nestedLayout));
      state = workspaceReducer(state, mergeSplits());

      expect(state.dockLayout.type).toBe("tab-group");
      expect(state.dockLayout.tabIds).toEqual(["tab-1", "tab-2", "tab-3"]);
    });
  });

  describe("updateSplitSizes action", () => {
    it("should update split sizes at root level", () => {
      const splitLayout = createHorizontalSplit(["tab-1"], ["tab-2"]);

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
      const nestedLayout = createNestedLayout();

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
      const splitLayout = createHorizontalSplit(["tab-1", "tab-2"], ["tab-3"]);

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
      state = workspaceReducer(state, setDockLayout(splitLayout));

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
      const splitLayout = createHorizontalSplit(["tab-1"], ["tab-2"]);

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
      state = workspaceReducer(state, setDockLayout(splitLayout));

      state = workspaceReducer(
        state,
        moveTabToGroup({
          tabId: "tab-1",
          targetPath: [1],
        }),
      );

      expect(state.dockLayout.type).toBe("tab-group");
      expect(state.dockLayout.tabIds).toEqual(["tab-2", "tab-1"]);
    });
  });

  describe("moveTabToGroup edge cases", () => {
    it("should do nothing when tab does not exist", () => {
      const splitLayout = createHorizontalSplit(["tab-1"], ["tab-2"]);

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
      state = workspaceReducer(state, setDockLayout(splitLayout));

      const stateAfter = workspaceReducer(
        state,
        moveTabToGroup({
          tabId: "non-existent-tab",
          targetPath: [1],
        }),
      );

      expect(stateAfter.dockLayout).toEqual(state.dockLayout);
    });

    it("should recalculate sizes when children are filtered", () => {
      const nestedLayout: DockLayout = {
        type: "horizontal-split",
        children: [
          {
            type: "vertical-split",
            children: [
              { type: "tab-group", tabIds: ["tab-1"] },
              { type: "tab-group", tabIds: ["tab-2"] },
            ],
            sizes: [60, 40],
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

      state = workspaceReducer(
        state,
        moveTabToGroup({
          tabId: "tab-1",
          targetPath: [1],
        }),
      );

      expect(state.dockLayout).toBeDefined();
      expect(state.activeTabId).toBe("tab-1");
    });

    it("should handle moving tab within same group", () => {
      const splitLayout = createHorizontalSplit(["tab-1", "tab-2"], ["tab-3"]);

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
      state = workspaceReducer(state, setDockLayout(splitLayout));

      state = workspaceReducer(
        state,
        moveTabToGroup({
          tabId: "tab-1",
          targetPath: [0],
        }),
      );

      expect(state.dockLayout.children?.[0].tabIds).toContain("tab-1");
      expect(state.activeTabId).toBe("tab-1");
    });

    it("should collapse to empty tab-group when all children become empty", () => {
      const splitLayout: DockLayout = {
        type: "horizontal-split",
        children: [
          {
            type: "vertical-split",
            children: [
              { type: "tab-group", tabIds: ["tab-1"] },
              { type: "tab-group", tabIds: [] },
            ],
            sizes: [50, 50],
          },
          { type: "tab-group", tabIds: ["tab-2"] },
        ],
        sizes: [60, 40],
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
      state = workspaceReducer(state, setDockLayout(splitLayout));

      state = workspaceReducer(
        state,
        moveTabToGroup({
          tabId: "tab-1",
          targetPath: [1],
        }),
      );

      expect(state.dockLayout).toBeDefined();
      expect(state.activeTabId).toBe("tab-1");
    });

    it("should handle deeply nested structure collapse", () => {
      const deepLayout: DockLayout = {
        type: "horizontal-split",
        children: [
          {
            type: "vertical-split",
            children: [
              {
                type: "horizontal-split",
                children: [
                  { type: "tab-group", tabIds: ["tab-1"] },
                  { type: "tab-group", tabIds: [] },
                ],
                sizes: [50, 50],
              },
              { type: "tab-group", tabIds: [] },
            ],
            sizes: [50, 50],
          },
          { type: "tab-group", tabIds: ["tab-2"] },
        ],
        sizes: [50, 50],
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
      state = workspaceReducer(state, setDockLayout(deepLayout));

      state = workspaceReducer(
        state,
        moveTabToGroup({
          tabId: "tab-1",
          targetPath: [1],
        }),
      );

      expect(state.dockLayout).toBeDefined();
      expect(state.activeTabId).toBe("tab-1");
    });
  });
});
