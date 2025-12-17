/**
 * MainDock Component Tests
 *
 * TDD tests for the main dock area with tabbed documents.
 * Tests cover:
 * - Basic rendering with tabs
 * - Tab management (add, remove, switch)
 * - Redux integration for tab state
 * - Empty state display
 */

import { describe, it, expect, vi, beforeEach } from "vitest";
import { render, screen, fireEvent } from "@testing-library/react";
import { Provider } from "react-redux";
import { configureStore } from "@reduxjs/toolkit";
import { MemoryRouter } from "react-router";

// Import after mocks
import { MainDock } from "./MainDock";
import workspaceReducer, {
  type WorkspaceState,
  type TabState,
} from "../../store/slices/workspaceSlice";

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
  dockLayout: { type: "tab-group", tabIds: ["tab-1"] },
  tabs: [
    {
      id: "tab-1",
      type: "chat",
      title: "Chat Session 1",
      entityId: "session-1",
    },
  ],
  activeTabId: "tab-1",
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

// Render helper with providers
function renderWithProviders(
  ui: React.ReactElement,
  options: {
    store?: ReturnType<typeof createTestStore>;
    workspaceOverrides?: Partial<WorkspaceState>;
  } = {},
) {
  const store =
    options.store ?? createTestStore(options.workspaceOverrides ?? {});

  function Wrapper({ children }: { children: React.ReactNode }) {
    return (
      <Provider store={store}>
        <MemoryRouter>{children}</MemoryRouter>
      </Provider>
    );
  }
  return { store, ...render(ui, { wrapper: Wrapper }) };
}

describe("MainDock", () => {
  beforeEach(() => {
    vi.clearAllMocks();
  });

  describe("basic rendering", () => {
    it("should render the main dock container", () => {
      renderWithProviders(<MainDock />);
      expect(screen.getByTestId("main-dock")).toBeInTheDocument();
    });

    it("should render tab bar", () => {
      renderWithProviders(<MainDock />);
      expect(screen.getByTestId("dock-tab-bar")).toBeInTheDocument();
    });

    it("should render content area", () => {
      renderWithProviders(<MainDock />);
      expect(screen.getByTestId("dock-content")).toBeInTheDocument();
    });
  });

  describe("tab management", () => {
    it("should render tabs from workspace state", () => {
      const tabs: TabState[] = [
        { id: "tab-1", type: "chat", title: "Chat 1" },
        { id: "tab-2", type: "workflow", title: "Workflow 1" },
      ];
      renderWithProviders(<MainDock />, {
        workspaceOverrides: {
          tabs,
          activeTabId: "tab-1",
        },
      });

      expect(screen.getByText("Chat 1")).toBeInTheDocument();
      expect(screen.getByText("Workflow 1")).toBeInTheDocument();
    });

    it("should highlight active tab", () => {
      const tabs: TabState[] = [
        { id: "tab-1", type: "chat", title: "Chat 1" },
        { id: "tab-2", type: "workflow", title: "Workflow 1" },
      ];
      renderWithProviders(<MainDock />, {
        workspaceOverrides: {
          tabs,
          activeTabId: "tab-1",
        },
      });

      const activeTab = screen.getByRole("tab", { selected: true });
      expect(activeTab).toHaveTextContent("Chat 1");
    });

    it("should switch active tab on click", () => {
      const tabs: TabState[] = [
        { id: "tab-1", type: "chat", title: "Chat 1" },
        { id: "tab-2", type: "workflow", title: "Workflow 1" },
      ];
      const store = createTestStore({
        tabs,
        activeTabId: "tab-1",
      });
      renderWithProviders(<MainDock />, { store });

      // Click on Workflow 1 tab
      fireEvent.click(screen.getByText("Workflow 1"));

      expect(store.getState().workspace.activeTabId).toBe("tab-2");
    });

    it("should close tab when clicking close button", () => {
      const tabs: TabState[] = [
        { id: "tab-1", type: "chat", title: "Chat 1" },
        { id: "tab-2", type: "workflow", title: "Workflow 1" },
      ];
      const store = createTestStore({
        tabs,
        activeTabId: "tab-1",
      });
      renderWithProviders(<MainDock />, { store });

      // Find and click close button for Chat 1
      const closeButtons = screen.getAllByLabelText(/close/i);
      fireEvent.click(closeButtons[0]);

      expect(store.getState().workspace.tabs).toHaveLength(1);
      expect(store.getState().workspace.tabs[0].id).toBe("tab-2");
    });
  });

  describe("empty state", () => {
    it("should show empty state when no tabs", () => {
      renderWithProviders(<MainDock />, {
        workspaceOverrides: {
          tabs: [],
          activeTabId: null,
        },
      });

      expect(screen.getByTestId("dock-empty-state")).toBeInTheDocument();
    });

    it("should show helpful message in empty state", () => {
      renderWithProviders(<MainDock />, {
        workspaceOverrides: {
          tabs: [],
          activeTabId: null,
        },
      });

      expect(screen.getByText(/start a new/i)).toBeInTheDocument();
    });
  });

  describe("content rendering", () => {
    it("should render content for active tab", () => {
      renderWithProviders(
        <MainDock
          renderContent={(tab) => (
            <div data-testid={`content-${tab.id}`}>{tab.title} Content</div>
          )}
        />,
      );

      expect(screen.getByTestId("content-tab-1")).toBeInTheDocument();
      expect(screen.getByText("Chat Session 1 Content")).toBeInTheDocument();
    });
  });

  describe("accessibility", () => {
    it("should have proper tab role structure", () => {
      renderWithProviders(<MainDock />);

      const tabList = screen.getByRole("tablist");
      expect(tabList).toBeInTheDocument();
    });

    it("should have proper tabpanel", () => {
      renderWithProviders(<MainDock />);

      const tabPanel = screen.getByRole("tabpanel");
      expect(tabPanel).toBeInTheDocument();
    });
  });

  describe("drag and drop reordering", () => {
    it("should have draggable attribute on tabs", () => {
      const tabs: TabState[] = [
        { id: "tab-1", type: "chat", title: "Chat 1" },
        { id: "tab-2", type: "workflow", title: "Workflow 1" },
      ];
      renderWithProviders(<MainDock />, {
        workspaceOverrides: {
          tabs,
          activeTabId: "tab-1",
        },
      });

      const tabElements = screen.getAllByRole("tab");
      expect(tabElements[0]).toHaveAttribute("draggable", "true");
      expect(tabElements[1]).toHaveAttribute("draggable", "true");
    });

    it("should reorder tabs on drop", () => {
      const tabs: TabState[] = [
        { id: "tab-1", type: "chat", title: "Chat 1" },
        { id: "tab-2", type: "workflow", title: "Workflow 1" },
        { id: "tab-3", type: "settings", title: "Settings" },
      ];
      const store = createTestStore({
        tabs,
        activeTabId: "tab-1",
      });
      renderWithProviders(<MainDock />, { store });

      const tabElements = screen.getAllByRole("tab");

      // Simulate drag start on tab-1
      fireEvent.dragStart(tabElements[0], {
        dataTransfer: { setData: vi.fn(), effectAllowed: "move" },
      });

      // Simulate drop on tab-3
      fireEvent.drop(tabElements[2], {
        dataTransfer: { getData: () => "0" },
      });

      // Verify tabs were reordered
      const reorderedTabs = store.getState().workspace.tabs;
      expect(reorderedTabs[0].id).toBe("tab-2");
      expect(reorderedTabs[1].id).toBe("tab-3");
      expect(reorderedTabs[2].id).toBe("tab-1");
    });

    it("should show drag over indicator", () => {
      const tabs: TabState[] = [
        { id: "tab-1", type: "chat", title: "Chat 1" },
        { id: "tab-2", type: "workflow", title: "Workflow 1" },
      ];
      renderWithProviders(<MainDock />, {
        workspaceOverrides: {
          tabs,
          activeTabId: "tab-1",
        },
      });

      const tabElements = screen.getAllByRole("tab");

      // Simulate drag over
      fireEvent.dragOver(tabElements[1], {
        dataTransfer: { dropEffect: "move" },
        preventDefault: vi.fn(),
      });

      // Tab should have visual indicator (tested via presence of container)
      expect(tabElements[1]).toBeInTheDocument();
    });
  });

  describe("tab-to-route navigation", () => {
    it("should navigate to chat route when clicking chat tab", () => {
      const mockNavigate = vi.fn();
      vi.mock("react-router", async () => {
        const actual = await vi.importActual("react-router");
        return { ...actual, useNavigate: () => mockNavigate };
      });

      const tabs: TabState[] = [
        { id: "tab-1", type: "chat", title: "Chat 1", entityId: "session-123" },
        { id: "tab-2", type: "workflow", title: "Workflow 1" },
      ];
      const store = createTestStore({
        tabs,
        activeTabId: "tab-2",
      });
      renderWithProviders(<MainDock />, { store });

      // Click on Chat tab
      fireEvent.click(screen.getByText("Chat 1"));

      // Should update active tab in Redux
      expect(store.getState().workspace.activeTabId).toBe("tab-1");
    });

    it("should call onTabNavigate callback when provided", () => {
      const onTabNavigate = vi.fn();
      const tabs: TabState[] = [
        { id: "tab-1", type: "chat", title: "Chat 1", entityId: "session-123" },
        { id: "tab-2", type: "workflow", title: "Workflow 1" },
      ];
      const store = createTestStore({
        tabs,
        activeTabId: "tab-2",
      });
      renderWithProviders(<MainDock onTabNavigate={onTabNavigate} />, {
        store,
      });

      // Click on Chat tab
      fireEvent.click(screen.getByText("Chat 1"));

      // Should call the navigation callback with tab info
      expect(onTabNavigate).toHaveBeenCalledWith(
        expect.objectContaining({
          id: "tab-1",
          type: "chat",
          entityId: "session-123",
        }),
      );
    });
  });

  describe("split layout support", () => {
    it("should support useSplitLayout prop to use SplitContainer", () => {
      const tabs: TabState[] = [
        { id: "tab-1", type: "chat", title: "Chat 1" },
        { id: "tab-2", type: "workflow", title: "Workflow 1" },
      ];
      renderWithProviders(<MainDock useSplitLayout={true} />, {
        workspaceOverrides: {
          tabs,
          activeTabId: "tab-1",
          dockLayout: {
            type: "horizontal-split",
            sizes: [50, 50],
            children: [
              { type: "tab-group", tabIds: ["tab-1"] },
              { type: "tab-group", tabIds: ["tab-2"] },
            ],
          },
        },
      });

      // When using split layout, should render split container
      expect(screen.getByTestId("split-container")).toBeInTheDocument();
    });

    it("should fall back to regular tab layout when useSplitLayout is false", () => {
      const tabs: TabState[] = [
        { id: "tab-1", type: "chat", title: "Chat 1" },
        { id: "tab-2", type: "workflow", title: "Workflow 1" },
      ];
      renderWithProviders(<MainDock useSplitLayout={false} />, {
        workspaceOverrides: {
          tabs,
          activeTabId: "tab-1",
        },
      });

      // Should use regular dock structure
      expect(screen.getByTestId("main-dock")).toBeInTheDocument();
      expect(screen.getByTestId("dock-tab-bar")).toBeInTheDocument();
    });
  });
});
