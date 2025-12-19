/**
 * useWorkspace Hook Tests
 *
 * Tests for JupyterLab-style workspace persistence.
 * Saves and restores layout state with named workspaces.
 */

import { describe, it, expect, vi, beforeEach, afterEach } from "vitest";
import { renderHook, act } from "@testing-library/react";
import { useWorkspace, type WorkspaceState } from "./useWorkspace";

// Mock localStorage
const mockStorage: Record<string, string> = {};
const localStorageMock = {
  getItem: vi.fn((key: string) => mockStorage[key] ?? null),
  setItem: vi.fn((key: string, value: string) => {
    mockStorage[key] = value;
  }),
  removeItem: vi.fn((key: string) => {
    delete mockStorage[key];
  }),
  clear: vi.fn(() => {
    Object.keys(mockStorage).forEach((key) => delete mockStorage[key]);
  }),
  get length() {
    return Object.keys(mockStorage).length;
  },
  key: vi.fn((index: number) => Object.keys(mockStorage)[index] ?? null),
};

describe("useWorkspace", () => {
  beforeEach(() => {
    vi.stubGlobal("localStorage", localStorageMock);
    localStorageMock.clear();
    vi.clearAllMocks();
  });

  afterEach(() => {
    vi.unstubAllGlobals();
  });

  describe("initialization", () => {
    it("initializes with default state", () => {
      const { result } = renderHook(() => useWorkspace("test-workspace"));

      expect(result.current.state).toEqual({
        focusMode: false,
        leftPanelCollapsed: false,
        rightPanelCollapsed: false,
        activeActivityId: null,
        activeTabs: {},
      });
    });

    it("restores state from localStorage", () => {
      const savedState: WorkspaceState = {
        focusMode: true,
        leftPanelCollapsed: true,
        rightPanelCollapsed: false,
        activeActivityId: "files",
        activeTabs: { left: "sessions" },
      };
      mockStorage["studio-workspace:saved-workspace"] =
        JSON.stringify(savedState);

      const { result } = renderHook(() => useWorkspace("saved-workspace"));

      expect(result.current.state).toEqual(savedState);
    });

    it("uses default state if localStorage is invalid", () => {
      mockStorage["studio-workspace:invalid"] = "not valid json";

      const { result } = renderHook(() => useWorkspace("invalid"));

      expect(result.current.state.focusMode).toBe(false);
    });
  });

  describe("state updates", () => {
    it("updates focus mode", () => {
      const { result } = renderHook(() => useWorkspace("test"));

      act(() => {
        result.current.setFocusMode(true);
      });

      expect(result.current.state.focusMode).toBe(true);
    });

    it("updates left panel collapsed state", () => {
      const { result } = renderHook(() => useWorkspace("test"));

      act(() => {
        result.current.setLeftPanelCollapsed(true);
      });

      expect(result.current.state.leftPanelCollapsed).toBe(true);
    });

    it("updates right panel collapsed state", () => {
      const { result } = renderHook(() => useWorkspace("test"));

      act(() => {
        result.current.setRightPanelCollapsed(true);
      });

      expect(result.current.state.rightPanelCollapsed).toBe(true);
    });

    it("updates active activity", () => {
      const { result } = renderHook(() => useWorkspace("test"));

      act(() => {
        result.current.setActiveActivityId("settings");
      });

      expect(result.current.state.activeActivityId).toBe("settings");
    });

    it("updates active tab for panel", () => {
      const { result } = renderHook(() => useWorkspace("test"));

      act(() => {
        result.current.setActiveTab("left", "tools");
      });

      expect(result.current.state.activeTabs.left).toBe("tools");
    });
  });

  describe("persistence", () => {
    it("saves state to localStorage on update", () => {
      const { result } = renderHook(() => useWorkspace("persist-test"));

      act(() => {
        result.current.setFocusMode(true);
      });

      expect(localStorageMock.setItem).toHaveBeenCalledWith(
        "studio-workspace:persist-test",
        expect.stringContaining('"focusMode":true'),
      );
    });

    it("saves state changes to localStorage", async () => {
      const { result } = renderHook(() => useWorkspace("save-test"));

      act(() => {
        result.current.setFocusMode(true);
        result.current.setLeftPanelCollapsed(true);
        result.current.setRightPanelCollapsed(true);
      });

      // Verify saves happen (React may batch state updates)
      expect(localStorageMock.setItem).toHaveBeenCalled();
      // Final state should include all three changes
      expect(result.current.state.focusMode).toBe(true);
      expect(result.current.state.leftPanelCollapsed).toBe(true);
      expect(result.current.state.rightPanelCollapsed).toBe(true);
    });
  });

  describe("named workspaces", () => {
    it("supports multiple named workspaces", () => {
      const { result: workspace1 } = renderHook(() =>
        useWorkspace("workspace-1"),
      );
      const { result: workspace2 } = renderHook(() =>
        useWorkspace("workspace-2"),
      );

      act(() => {
        workspace1.current.setFocusMode(true);
      });

      act(() => {
        workspace2.current.setFocusMode(false);
      });

      expect(workspace1.current.state.focusMode).toBe(true);
      expect(workspace2.current.state.focusMode).toBe(false);
    });

    it("lists available workspaces", () => {
      mockStorage["studio-workspace:ws1"] = JSON.stringify({
        focusMode: false,
      });
      mockStorage["studio-workspace:ws2"] = JSON.stringify({ focusMode: true });
      mockStorage["other-key"] = "not a workspace";

      const { result } = renderHook(() => useWorkspace("ws1"));

      expect(result.current.listWorkspaces()).toContain("ws1");
      expect(result.current.listWorkspaces()).toContain("ws2");
      expect(result.current.listWorkspaces()).not.toContain("other-key");
    });
  });

  describe("workspace management", () => {
    it("resets workspace to default state", () => {
      const { result } = renderHook(() => useWorkspace("reset-test"));

      act(() => {
        result.current.setFocusMode(true);
        result.current.setLeftPanelCollapsed(true);
      });

      act(() => {
        result.current.reset();
      });

      expect(result.current.state.focusMode).toBe(false);
      expect(result.current.state.leftPanelCollapsed).toBe(false);
    });

    it("deletes workspace from localStorage", () => {
      const { result } = renderHook(() => useWorkspace("delete-test"));

      act(() => {
        result.current.setFocusMode(true);
      });

      act(() => {
        result.current.deleteWorkspace();
      });

      expect(localStorageMock.removeItem).toHaveBeenCalledWith(
        "studio-workspace:delete-test",
      );
    });
  });
});
