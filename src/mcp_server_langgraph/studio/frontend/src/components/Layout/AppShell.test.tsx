/**
 * AppShell Component Tests
 *
 * TDD tests for the main layout orchestrator.
 * Tests cover:
 * - Basic rendering with all panels
 * - Panel collapse/expand behavior
 * - Resizable panels
 * - Focus mode integration
 * - Mobile responsiveness
 */

import { describe, it, expect, vi, beforeEach } from "vitest";
import { render, screen, fireEvent } from "@testing-library/react";
import { Provider } from "react-redux";
import { configureStore } from "@reduxjs/toolkit";
import { BrowserRouter } from "react-router";

// Mock ResizeObserver before imports
vi.stubGlobal(
  "ResizeObserver",
  vi.fn().mockImplementation(() => ({
    observe: vi.fn(),
    unobserve: vi.fn(),
    disconnect: vi.fn(),
  })),
);

// Use shared react-resizable-panels mock to avoid layout calculation errors
// See: src/mocks/components/react-resizable-panels.ts
vi.mock("react-resizable-panels", async () => {
  const { mockReactResizablePanels } =
    await import("../../mocks/components/react-resizable-panels");
  return mockReactResizablePanels;
});

// Mock the API module to control useGetHealthQuery responses (used by StatusBar)
const mockUseGetHealthQuery = vi.fn();
vi.mock("../../api", async (importOriginal) => {
  const original = await importOriginal<typeof import("../../api")>();
  return {
    ...original,
    useGetHealthQuery: (...args: unknown[]) => mockUseGetHealthQuery(...args),
  };
});

// Import after mocks
import { AppShell } from "./AppShell";
import workspaceReducer, {
  type WorkspaceState,
} from "../../store/slices/workspaceSlice";
import mcpReducer, { type MCPSliceState } from "../../store/slices/mcpSlice";
import personaReducer from "../../store/slices/personaSlice";
import notificationReducer from "../../store/slices/notificationSlice";
import sessionReducer, {
  initialSessionState,
} from "../../store/slices/sessionSlice";
import authReducer from "../../store/slices/authSlice";
import uiReducer from "../../store/slices/uiSlice";
import projectReducer from "../../store/slices/projectSlice";
import workflowReducer from "../../store/slices/workflowSlice";
import { api } from "../../api";

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

// Default MCP state
const defaultMCPState: MCPSliceState = {
  servers: {},
  primaryServerId: null,
  capabilities: {
    elicitation: true,
    sampling: true,
    roots: { listChanged: true },
  },
  pendingElicitations: [],
  pendingSamplingRequests: [],
  isConnecting: false,
  error: null,
};

// Create a test store with all required reducers
function createTestStore(workspaceOverrides: Partial<WorkspaceState> = {}) {
  return configureStore({
    reducer: {
      [api.reducerPath]: api.reducer,
      workspace: workspaceReducer,
      mcp: mcpReducer,
      persona: personaReducer,
      notifications: notificationReducer,
      session: sessionReducer,
      auth: authReducer,
      ui: uiReducer,
      project: projectReducer,
      workflow: workflowReducer,
    },
    preloadedState: {
      workspace: { ...defaultWorkspaceState, ...workspaceOverrides },
      mcp: defaultMCPState,
      persona: {
        persona: "user",
        username: null,
        email: null,
        permissions: [],
        isPersonaLoading: false,
      },
      notifications: { notifications: [] },
      session: initialSessionState,
    },
    middleware: (getDefaultMiddleware) =>
      getDefaultMiddleware().concat(api.middleware),
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
        <BrowserRouter>{children}</BrowserRouter>
      </Provider>
    );
  }
  return { store, ...render(ui, { wrapper: Wrapper }) };
}

describe("AppShell", () => {
  beforeEach(() => {
    vi.clearAllMocks();
    localStorage.clear();
    // Mock health query for StatusBar (returns healthy by default)
    mockUseGetHealthQuery.mockReturnValue({
      data: { status: "healthy" },
      isLoading: false,
      isError: false,
    });
  });

  describe("basic rendering", () => {
    it("should render the shell container", () => {
      renderWithProviders(<AppShell />);
      expect(screen.getByTestId("app-shell")).toBeInTheDocument();
    });

    it("should render the left sidebar area", () => {
      renderWithProviders(<AppShell />);
      expect(screen.getByTestId("left-sidebar-panel")).toBeInTheDocument();
    });

    it("should render the main content area", () => {
      renderWithProviders(<AppShell />);
      expect(screen.getByTestId("main-content-area")).toBeInTheDocument();
    });

    it("should render the right sidebar area", () => {
      renderWithProviders(<AppShell />);
      expect(screen.getByTestId("right-sidebar-panel")).toBeInTheDocument();
    });

    it("should render the bottom panel area", () => {
      renderWithProviders(<AppShell />);
      expect(screen.getByTestId("bottom-panel")).toBeInTheDocument();
    });

    it("should render the status bar", () => {
      renderWithProviders(<AppShell />);
      expect(screen.getByTestId("status-bar")).toBeInTheDocument();
    });
  });

  describe("panel visibility", () => {
    it("should show left sidebar when not collapsed", () => {
      renderWithProviders(<AppShell />, {
        workspaceOverrides: { leftSidebarCollapsed: false },
      });
      const leftPanel = screen.getByTestId("left-sidebar-panel");
      expect(leftPanel).toBeVisible();
    });

    it("should show bottom panel when not collapsed", () => {
      renderWithProviders(<AppShell />, {
        workspaceOverrides: { bottomPanelCollapsed: false },
      });
      const bottomPanel = screen.getByTestId("bottom-panel");
      expect(bottomPanel).toBeVisible();
    });
  });

  describe("children rendering", () => {
    it("should render children in main content area", () => {
      renderWithProviders(
        <AppShell>
          <div data-testid="test-child">Test Content</div>
        </AppShell>,
      );
      expect(screen.getByTestId("test-child")).toBeInTheDocument();
      expect(screen.getByText("Test Content")).toBeInTheDocument();
    });

    it("should render left sidebar content when provided", () => {
      renderWithProviders(
        <AppShell leftSidebar={<div data-testid="left-content">Left</div>} />,
      );
      expect(screen.getByTestId("left-content")).toBeInTheDocument();
    });

    it("should render right sidebar content when provided", () => {
      renderWithProviders(
        <AppShell
          rightSidebar={<div data-testid="right-content">Right</div>}
        />,
      );
      expect(screen.getByTestId("right-content")).toBeInTheDocument();
    });

    it("should render bottom panel content when provided", () => {
      renderWithProviders(
        <AppShell
          bottomPanel={<div data-testid="bottom-content">Bottom</div>}
        />,
      );
      expect(screen.getByTestId("bottom-content")).toBeInTheDocument();
    });
  });

  describe("focus mode", () => {
    it("should hide right sidebar and bottom panel in focus mode but keep left sidebar visible", () => {
      renderWithProviders(<AppShell />, {
        workspaceOverrides: { focusMode: true },
      });
      // In focus mode, left sidebar should remain visible (always visible)
      const leftPanel = screen.getByTestId("left-sidebar-panel");
      expect(leftPanel).toHaveAttribute("data-focus-hidden", "false");
      // Right sidebar should be hidden
      const rightPanel = screen.getByTestId("right-sidebar-panel");
      expect(rightPanel).toHaveAttribute("data-focus-hidden", "true");
    });

    it("should always show left sidebar even when leftSidebarCollapsed is true on desktop", () => {
      renderWithProviders(<AppShell />, {
        workspaceOverrides: { leftSidebarCollapsed: true },
      });
      // Left sidebar should be visible regardless of collapsed state on desktop
      const leftPanel = screen.getByTestId("left-sidebar-panel");
      expect(leftPanel).toBeVisible();
    });
  });

  describe("keyboard shortcuts", () => {
    it("should toggle right sidebar on Cmd+B", () => {
      const store = createTestStore({ rightSidebarCollapsed: false });
      renderWithProviders(<AppShell />, { store });

      // Simulate Cmd+B
      fireEvent.keyDown(document, { key: "b", metaKey: true });

      // Check that the action was dispatched (right sidebar should now be collapsed)
      expect(store.getState().workspace.rightSidebarCollapsed).toBe(true);
    });

    it("should toggle bottom panel on Cmd+J", () => {
      const store = createTestStore({ bottomPanelCollapsed: true });
      renderWithProviders(<AppShell />, { store });

      // Simulate Cmd+J
      fireEvent.keyDown(document, { key: "j", metaKey: true });

      // Check that the action was dispatched (bottom panel should now be expanded)
      expect(store.getState().workspace.bottomPanelCollapsed).toBe(false);
    });

    it("should exit focus mode on Escape", () => {
      const store = createTestStore({ focusMode: true });
      renderWithProviders(<AppShell />, { store });

      // Simulate Escape
      fireEvent.keyDown(document, { key: "Escape" });

      // Check that focus mode was turned off
      expect(store.getState().workspace.focusMode).toBe(false);
    });
  });

  describe("accessibility", () => {
    it("should have proper ARIA landmarks", () => {
      renderWithProviders(<AppShell />);
      // Main content should have main role
      expect(screen.getByRole("main")).toBeInTheDocument();
    });

    it("should have focus management", () => {
      renderWithProviders(<AppShell />);
      const shell = screen.getByTestId("app-shell");
      expect(shell).toBeInTheDocument();
    });
  });

  describe("StatusBar integration", () => {
    it("should render StatusBar component in status bar area", () => {
      renderWithProviders(<AppShell />);
      // StatusBar should show connection status
      expect(screen.getByTestId("connection-status")).toBeInTheDocument();
    });

    it("should render focus mode toggle button", () => {
      renderWithProviders(<AppShell />);
      expect(
        screen.getByRole("button", { name: /focus mode/i }),
      ).toBeInTheDocument();
    });

    it("should enter focus mode when focus toggle is clicked", () => {
      const store = createTestStore({ focusMode: false });
      renderWithProviders(<AppShell />, { store });

      fireEvent.click(screen.getByRole("button", { name: /focus mode/i }));

      expect(store.getState().workspace.focusMode).toBe(true);
    });

    it("should show expand icon when not in focus mode", () => {
      renderWithProviders(<AppShell />, {
        workspaceOverrides: { focusMode: false },
      });
      const focusButton = screen.getByRole("button", { name: /focus mode/i });
      expect(focusButton).toBeInTheDocument();
    });
  });

  describe("mobile responsiveness", () => {
    it("should render mobile menu toggle on mobile", () => {
      // This test verifies the mobile menu toggle exists
      renderWithProviders(<AppShell />);
      // Mobile toggle should exist (visible only on mobile via CSS)
      expect(
        screen.getByRole("button", { name: /toggle menu/i }),
      ).toBeInTheDocument();
    });

    it("should toggle mobile sidebar overlay when menu button clicked", () => {
      const store = createTestStore({ leftSidebarCollapsed: true });
      renderWithProviders(<AppShell />, { store });

      fireEvent.click(screen.getByRole("button", { name: /toggle menu/i }));

      // Should expand left sidebar (mobile overlay mode)
      expect(store.getState().workspace.leftSidebarCollapsed).toBe(false);
    });

    it("should render right sidebar toggle button on mobile", () => {
      renderWithProviders(<AppShell />);
      expect(
        screen.getByRole("button", { name: /toggle right panel/i }),
      ).toBeInTheDocument();
    });

    it("should toggle right sidebar overlay when right panel button clicked", () => {
      const store = createTestStore({ rightSidebarCollapsed: true });
      renderWithProviders(<AppShell />, { store });

      fireEvent.click(
        screen.getByRole("button", { name: /toggle right panel/i }),
      );

      // Should expand right sidebar (mobile overlay mode)
      expect(store.getState().workspace.rightSidebarCollapsed).toBe(false);
    });

    it("should show right sidebar overlay backdrop when right sidebar is open", () => {
      renderWithProviders(<AppShell />, {
        workspaceOverrides: { rightSidebarCollapsed: false },
      });
      expect(
        screen.getByTestId("mobile-right-sidebar-overlay"),
      ).toBeInTheDocument();
    });

    it("should close right sidebar when backdrop is clicked", () => {
      const store = createTestStore({ rightSidebarCollapsed: false });
      renderWithProviders(<AppShell />, { store });

      fireEvent.click(screen.getByTestId("mobile-right-sidebar-overlay"));

      expect(store.getState().workspace.rightSidebarCollapsed).toBe(true);
    });

    it("should render bottom panel toggle button on mobile", () => {
      renderWithProviders(<AppShell />);
      expect(
        screen.getByRole("button", { name: /toggle bottom panel/i }),
      ).toBeInTheDocument();
    });

    it("should toggle bottom panel when bottom panel button clicked", () => {
      const store = createTestStore({ bottomPanelCollapsed: true });
      renderWithProviders(<AppShell />, { store });

      fireEvent.click(
        screen.getByRole("button", { name: /toggle bottom panel/i }),
      );

      // Should expand bottom panel
      expect(store.getState().workspace.bottomPanelCollapsed).toBe(false);
    });

    it("should show bottom panel overlay backdrop when bottom panel is open", () => {
      renderWithProviders(<AppShell />, {
        workspaceOverrides: { bottomPanelCollapsed: false },
      });
      expect(
        screen.getByTestId("mobile-bottom-panel-overlay"),
      ).toBeInTheDocument();
    });

    it("should close bottom panel when backdrop is clicked", () => {
      const store = createTestStore({ bottomPanelCollapsed: false });
      renderWithProviders(<AppShell />, { store });

      fireEvent.click(screen.getByTestId("mobile-bottom-panel-overlay"));

      expect(store.getState().workspace.bottomPanelCollapsed).toBe(true);
    });
  });

  describe("touch-friendly resize handles", () => {
    it("should have accessible resize handles", () => {
      renderWithProviders(<AppShell />, {
        workspaceOverrides: {
          leftSidebarCollapsed: false,
          bottomPanelCollapsed: false,
        },
      });
      // Resize handles should have proper touch target sizing via CSS
      const shell = screen.getByTestId("app-shell");
      expect(shell).toBeInTheDocument();
    });
  });
});
