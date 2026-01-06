/**
 * Workspace Slice Test Fixtures
 *
 * Shared test data and utilities for workspaceSlice tests.
 * Extracted from workspaceSlice.test.ts during test splitting (OOM prevention).
 */

import type { WorkspaceState, DockLayout, TabState } from "../workspaceSlice";
import { DEFAULT_WORKSPACE_STATE } from "../workspaceSlice";

/**
 * Create a mock RootState for selector testing
 */
export function createMockState(workspace: Partial<WorkspaceState>): {
  workspace: WorkspaceState;
} {
  return {
    workspace: { ...DEFAULT_WORKSPACE_STATE, ...workspace },
  };
}

/**
 * Factory for creating test tabs
 */
export function createTab(overrides?: Partial<TabState>): TabState {
  return {
    id: "tab-1",
    type: "chat",
    title: "Test Tab",
    ...overrides,
  };
}

/**
 * Factory for creating horizontal split layout
 */
export function createHorizontalSplit(
  leftTabs: string[],
  rightTabs: string[],
  sizes: [number, number] = [50, 50],
): DockLayout {
  return {
    type: "horizontal-split",
    children: [
      { type: "tab-group", tabIds: leftTabs },
      { type: "tab-group", tabIds: rightTabs },
    ],
    sizes,
  };
}

/**
 * Factory for creating vertical split layout
 */
export function createVerticalSplit(
  topTabs: string[],
  bottomTabs: string[],
  sizes: [number, number] = [50, 50],
): DockLayout {
  return {
    type: "vertical-split",
    children: [
      { type: "tab-group", tabIds: topTabs },
      { type: "tab-group", tabIds: bottomTabs },
    ],
    sizes,
  };
}

/**
 * Factory for creating nested split layout
 */
export function createNestedLayout(): DockLayout {
  return {
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
}

/**
 * Factory for creating tab-group layout
 */
export function createTabGroupLayout(tabIds: string[] = []): DockLayout {
  return {
    type: "tab-group",
    tabIds,
  };
}

/**
 * Mock localStorage for testing
 */
export function setupMockStorage() {
  const storage: { [key: string]: string } = {};

  return {
    getItem: (key: string) => storage[key] || null,
    setItem: (key: string, value: string) => {
      storage[key] = value;
    },
    removeItem: (key: string) => {
      delete storage[key];
    },
    clear: () => {
      Object.keys(storage).forEach((key) => delete storage[key]);
    },
    get length() {
      return Object.keys(storage).length;
    },
    key: (index: number) => Object.keys(storage)[index] || null,
  };
}

/**
 * Activity IDs for testing
 */
export const TEST_ACTIVITIES = [
  "workspace",
  "conversations",
  "build",
  "connections",
  "insights",
] as const;

/**
 * Bottom panel tab IDs for testing
 */
export const TEST_BOTTOM_PANEL_TABS = [
  "terminal",
  "problems",
  "output",
  "debug-console",
] as const;
