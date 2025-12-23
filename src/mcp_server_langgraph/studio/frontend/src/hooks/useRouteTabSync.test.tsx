/**
 * useRouteTabSync Hook Tests
 *
 * TDD tests for the route-to-tab sync hook.
 * Tests cover:
 * - Creating tabs when navigating to routes
 * - Activating existing tabs
 * - Syncing tab state with URL
 */

import { describe, it, expect, vi, beforeEach, afterEach } from "vitest";
import { renderHook, cleanup } from "@testing-library/react";
import { Provider } from "react-redux";
import { MemoryRouter } from "react-router";
import { configureStore } from "@reduxjs/toolkit";

import { useRouteTabSync } from "./useRouteTabSync";
import workspaceReducer, {
  type WorkspaceState,
} from "../store/slices/workspaceSlice";

// Default workspace state for tests
const defaultWorkspaceState: WorkspaceState = {
  version: 1,
  leftSidebarWidth: 280,
  leftSidebarCollapsed: false,
  rightSidebarWidth: 280,
  rightSidebarCollapsed: false,
  bottomPanelHeight: 200,
  bottomPanelCollapsed: true,
  activeActivityId: "conversations",
  dockLayout: { type: "tab-group", tabIds: [] },
  tabs: [],
  activeTabId: null,
  focusMode: false,
  expandedGroups: [],
  expandedPropertySections: [],
  bottomPanelActiveTab: "activity",
  scrollPositions: {},
  lastUpdated: 0,
};

// Create a test store
function createTestStore(workspaceOverrides: Partial<WorkspaceState> = {}) {
  return configureStore({
    reducer: {
      workspace: workspaceReducer,
    },
    preloadedState: {
      workspace: { ...defaultWorkspaceState, ...workspaceOverrides },
    },
  });
}

// Render hook helper with providers
function renderHookWithProviders(
  options: {
    store?: ReturnType<typeof createTestStore>;
    workspaceOverrides?: Partial<WorkspaceState>;
    initialEntries?: string[];
  } = {},
) {
  const store =
    options.store ?? createTestStore(options.workspaceOverrides ?? {});

  function Wrapper({ children }: { children: React.ReactNode }) {
    return (
      <Provider store={store}>
        <MemoryRouter
          initialEntries={options.initialEntries ?? ["/studio/chat"]}
        >
          {children}
        </MemoryRouter>
      </Provider>
    );
  }
  return {
    store,
    ...renderHook(() => useRouteTabSync(), { wrapper: Wrapper }),
  };
}

describe("useRouteTabSync", () => {
  beforeEach(() => {
    vi.clearAllMocks();
  });

  afterEach(() => {
    cleanup();
    vi.clearAllMocks();
  });

  describe("tab creation", () => {
    it("should create a chat tab when on /studio/chat route", () => {
      const { store } = renderHookWithProviders({
        initialEntries: ["/studio/chat"],
      });

      const tabs = store.getState().workspace.tabs;
      expect(tabs.length).toBeGreaterThan(0);
      expect(tabs.some((t) => t.type === "chat")).toBe(true);
    });

    it("should create a workflow tab when on /studio/workflows route", () => {
      const { store } = renderHookWithProviders({
        initialEntries: ["/studio/workflows"],
      });

      const tabs = store.getState().workspace.tabs;
      expect(tabs.some((t) => t.type === "workflow")).toBe(true);
    });

    it("should create a settings tab when on /studio/settings route", () => {
      const { store } = renderHookWithProviders({
        initialEntries: ["/studio/settings"],
      });

      const tabs = store.getState().workspace.tabs;
      expect(tabs.some((t) => t.type === "settings")).toBe(true);
    });
  });

  describe("tab activation", () => {
    it("should activate existing tab instead of creating duplicate", () => {
      const { store } = renderHookWithProviders({
        workspaceOverrides: {
          tabs: [{ id: "existing-chat", type: "chat", title: "Chat" }],
        },
        initialEntries: ["/studio/chat"],
      });

      const tabs = store.getState().workspace.tabs;
      // Should still have only 1 tab
      expect(tabs.length).toBe(1);
      // And it should be active
      expect(store.getState().workspace.activeTabId).toBe("existing-chat");
    });
  });

  describe("session-specific tabs", () => {
    it("should create tab with session ID from URL", () => {
      const { store } = renderHookWithProviders({
        initialEntries: ["/studio/chat?session=session-123"],
      });

      const tabs = store.getState().workspace.tabs;
      const chatTab = tabs.find((t) => t.type === "chat");
      expect(chatTab?.entityId).toBe("session-123");
    });
  });
});
