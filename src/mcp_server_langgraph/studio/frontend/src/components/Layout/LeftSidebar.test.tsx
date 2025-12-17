/**
 * LeftSidebar Component Tests
 *
 * TDD tests for the hybrid navigation left sidebar.
 * Tests cover:
 * - Basic rendering with Activity Bar and content panel
 * - Group navigation (scroll to group on Activity Bar click)
 * - Expandable group sections
 * - Active group highlighting
 * - RBAC filtering
 */

import { describe, it, expect, vi, beforeEach } from "vitest";
import { render, screen, fireEvent, within } from "@testing-library/react";
import { Provider } from "react-redux";
import { configureStore } from "@reduxjs/toolkit";
import { MemoryRouter } from "react-router";

// Import after mocks
import { LeftSidebar } from "./LeftSidebar";
import workspaceReducer, {
  type WorkspaceState,
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
  dockLayout: { type: "tab-group", tabIds: [] },
  tabs: [],
  activeTabId: null,
  focusMode: false,
  expandedGroups: ["conversations"],
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
    initialEntries?: string[];
  } = {},
) {
  const store =
    options.store ?? createTestStore(options.workspaceOverrides ?? {});
  const initialEntries = options.initialEntries ?? ["/studio/chat"];

  function Wrapper({ children }: { children: React.ReactNode }) {
    return (
      <Provider store={store}>
        <MemoryRouter initialEntries={initialEntries}>{children}</MemoryRouter>
      </Provider>
    );
  }
  return { store, ...render(ui, { wrapper: Wrapper }) };
}

describe("LeftSidebar", () => {
  beforeEach(() => {
    vi.clearAllMocks();
  });

  describe("basic rendering", () => {
    it("should render the left sidebar container", () => {
      renderWithProviders(<LeftSidebar />);
      expect(screen.getByTestId("left-sidebar")).toBeInTheDocument();
    });

    it("should render the activity bar", () => {
      renderWithProviders(<LeftSidebar />);
      expect(screen.getByTestId("activity-bar")).toBeInTheDocument();
    });

    it("should render the content panel", () => {
      renderWithProviders(<LeftSidebar />);
      expect(screen.getByTestId("sidebar-content")).toBeInTheDocument();
    });

    it("should render group sections", () => {
      renderWithProviders(<LeftSidebar />);
      expect(screen.getByText("CONVERSATIONS")).toBeInTheDocument();
    });
  });

  describe("activity bar navigation", () => {
    it("should show activity bar items for each group", () => {
      renderWithProviders(<LeftSidebar />);
      const activityBar = screen.getByTestId("activity-bar");

      // Should have buttons for groups
      expect(within(activityBar).getAllByRole("tab").length).toBeGreaterThan(0);
    });

    it("should highlight active group in activity bar", () => {
      renderWithProviders(<LeftSidebar />, {
        workspaceOverrides: { activeActivityId: "conversations" },
      });

      const activeButton = screen.getByRole("tab", { selected: true });
      expect(activeButton).toBeInTheDocument();
    });

    it("should update active activity when clicking activity bar item", () => {
      const store = createTestStore({ activeActivityId: "conversations" });
      renderWithProviders(<LeftSidebar />, { store });

      // Find and click a different activity (build group)
      const buildButton = screen.getByLabelText(/build/i);
      fireEvent.click(buildButton);

      expect(store.getState().workspace.activeActivityId).toBe("build");
    });
  });

  describe("group sections", () => {
    it("should render expandable group headers", () => {
      renderWithProviders(<LeftSidebar />);

      // Look for group headers
      expect(screen.getByText("CONVERSATIONS")).toBeInTheDocument();
    });

    it("should show group content when expanded", () => {
      renderWithProviders(<LeftSidebar />, {
        workspaceOverrides: {
          activeActivityId: "conversations",
          expandedGroups: ["conversations"],
        },
      });

      // Chat should be visible in conversations group
      expect(screen.getByText("Chat")).toBeInTheDocument();
    });

    it("should toggle group expansion when clicking header", () => {
      const store = createTestStore({
        expandedGroups: [],
        activeActivityId: "conversations",
      });
      renderWithProviders(<LeftSidebar />, { store });

      // Click on conversations header
      const header = screen.getByText("CONVERSATIONS");
      fireEvent.click(header);

      expect(store.getState().workspace.expandedGroups).toContain(
        "conversations",
      );
    });
  });

  describe("navigation items", () => {
    it("should render navigation links for each item in expanded group", () => {
      renderWithProviders(<LeftSidebar />, {
        workspaceOverrides: {
          activeActivityId: "conversations",
          expandedGroups: ["conversations"],
        },
      });

      // Chat link should be visible
      const chatLink = screen.getByRole("link", { name: /chat/i });
      expect(chatLink).toBeInTheDocument();
    });
  });

  describe("collapsed state", () => {
    it("should show only activity bar when collapsed", () => {
      const store = createTestStore();
      const { container } = renderWithProviders(<LeftSidebar collapsed />, {
        store,
      });

      // Activity bar should still be visible
      expect(screen.getByTestId("activity-bar")).toBeInTheDocument();

      // Content panel should be hidden
      const contentPanel = container.querySelector(
        '[data-testid="sidebar-content"]',
      );
      expect(contentPanel).toHaveClass("hidden");
    });
  });

  describe("accessibility", () => {
    it("should have proper ARIA structure", () => {
      renderWithProviders(<LeftSidebar />);

      const activityBar = screen.getByTestId("activity-bar");
      expect(activityBar).toHaveAttribute("role", "tablist");
    });
  });

  describe("action buttons", () => {
    it("should render 'New Chat' button in conversations group", () => {
      renderWithProviders(<LeftSidebar />, {
        workspaceOverrides: {
          activeActivityId: "conversations",
          expandedGroups: ["conversations"],
        },
      });

      expect(
        screen.getByRole("button", { name: /new chat/i }),
      ).toBeInTheDocument();
    });

    it("should render 'New Project' button in workspace group", () => {
      renderWithProviders(<LeftSidebar />, {
        workspaceOverrides: {
          activeActivityId: "workspace",
          expandedGroups: ["workspace"],
        },
      });

      expect(
        screen.getByRole("button", { name: /new project/i }),
      ).toBeInTheDocument();
    });

    it("should call onNewChat when clicking 'New Chat' button", () => {
      const onNewChat = vi.fn();
      renderWithProviders(<LeftSidebar onNewChat={onNewChat} />, {
        workspaceOverrides: {
          activeActivityId: "conversations",
          expandedGroups: ["conversations"],
        },
      });

      const newChatButton = screen.getByRole("button", { name: /new chat/i });
      fireEvent.click(newChatButton);

      expect(onNewChat).toHaveBeenCalled();
    });

    it("should call onNewProject when clicking 'New Project' button", () => {
      const onNewProject = vi.fn();
      renderWithProviders(<LeftSidebar onNewProject={onNewProject} />, {
        workspaceOverrides: {
          activeActivityId: "workspace",
          expandedGroups: ["workspace"],
        },
      });

      const newProjectButton = screen.getByRole("button", {
        name: /new project/i,
      });
      fireEvent.click(newProjectButton);

      expect(onNewProject).toHaveBeenCalled();
    });
  });
});
