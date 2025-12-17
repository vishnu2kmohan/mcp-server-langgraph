/**
 * BottomPanel Component Tests
 *
 * TDD tests for the bottom panel (Down Area) with tabs.
 * Tests cover:
 * - Basic rendering with tabs
 * - Tab switching
 * - Collapse/expand functionality
 * - Redux state integration
 */

import { describe, it, expect, vi, beforeEach } from "vitest";
import { render, screen, fireEvent } from "@testing-library/react";
import { Provider } from "react-redux";
import { configureStore } from "@reduxjs/toolkit";

// Import after mocks
import { BottomPanel } from "./BottomPanel";
import workspaceReducer, {
  type WorkspaceState,
} from "../../store/slices/workspaceSlice";
import notificationReducer, {
  type Notification,
} from "../../store/slices/notificationSlice";
import mcpReducer, { type MCPSliceState } from "../../store/slices/mcpSlice";
import sessionReducer, {
  type SessionState,
  initialSessionState,
} from "../../store/slices/sessionSlice";

// Default workspace state for tests
const defaultWorkspaceState: WorkspaceState = {
  version: 1,
  leftSidebarWidth: 280,
  leftSidebarCollapsed: false,
  rightSidebarWidth: 280,
  rightSidebarCollapsed: false,
  bottomPanelHeight: 200,
  bottomPanelCollapsed: false,
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

// Create a test store
function createTestStore(
  overrides: {
    workspace?: Partial<WorkspaceState>;
    notifications?: Notification[];
    mcp?: Partial<MCPSliceState>;
    session?: Partial<SessionState>;
  } = {},
) {
  return configureStore({
    reducer: {
      workspace: workspaceReducer,
      notifications: notificationReducer,
      mcp: mcpReducer,
      session: sessionReducer,
    },
    preloadedState: {
      workspace: { ...defaultWorkspaceState, ...overrides.workspace },
      notifications: {
        notifications: overrides.notifications ?? [],
      },
      mcp: { ...defaultMCPState, ...overrides.mcp },
      session: { ...initialSessionState, ...overrides.session },
    },
  });
}

// Render helper with providers
function renderWithProviders(
  ui: React.ReactElement,
  options: {
    store?: ReturnType<typeof createTestStore>;
    workspaceOverrides?: Partial<WorkspaceState>;
    notifications?: Notification[];
    mcpOverrides?: Partial<MCPSliceState>;
    sessionOverrides?: Partial<SessionState>;
  } = {},
) {
  const store =
    options.store ??
    createTestStore({
      workspace: options.workspaceOverrides ?? {},
      notifications: options.notifications ?? [],
      mcp: options.mcpOverrides ?? {},
      session: options.sessionOverrides ?? {},
    });

  function Wrapper({ children }: { children: React.ReactNode }) {
    return <Provider store={store}>{children}</Provider>;
  }
  return { store, ...render(ui, { wrapper: Wrapper }) };
}

describe("BottomPanel", () => {
  beforeEach(() => {
    vi.clearAllMocks();
  });

  describe("basic rendering", () => {
    it("should render the bottom panel container", () => {
      renderWithProviders(<BottomPanel />);
      expect(screen.getByTestId("bottom-panel-container")).toBeInTheDocument();
    });

    it("should render tab bar", () => {
      renderWithProviders(<BottomPanel />);
      expect(screen.getByTestId("bottom-panel-tabs")).toBeInTheDocument();
    });

    it("should render content area", () => {
      renderWithProviders(<BottomPanel />);
      expect(screen.getByTestId("bottom-panel-content")).toBeInTheDocument();
    });
  });

  describe("tabs", () => {
    it("should render Activity tab", () => {
      renderWithProviders(<BottomPanel />);
      expect(
        screen.getByRole("tab", { name: /activity/i }),
      ).toBeInTheDocument();
    });

    it("should render Problems tab", () => {
      renderWithProviders(<BottomPanel />);
      expect(
        screen.getByRole("tab", { name: /problems/i }),
      ).toBeInTheDocument();
    });

    it("should render Inspector tab", () => {
      renderWithProviders(<BottomPanel />);
      expect(
        screen.getByRole("tab", { name: /inspector/i }),
      ).toBeInTheDocument();
    });

    it("should highlight active tab", () => {
      renderWithProviders(<BottomPanel />, {
        workspaceOverrides: { bottomPanelActiveTab: "activity" },
      });

      const activeTab = screen.getByRole("tab", { selected: true });
      expect(activeTab).toHaveTextContent(/activity/i);
    });

    it("should switch tabs on click", () => {
      const store = createTestStore({
        workspace: { bottomPanelActiveTab: "activity" },
      });
      renderWithProviders(<BottomPanel />, { store });

      fireEvent.click(screen.getByRole("tab", { name: /problems/i }));

      expect(store.getState().workspace.bottomPanelActiveTab).toBe("problems");
    });
  });

  describe("collapse functionality", () => {
    it("should render collapse button", () => {
      renderWithProviders(<BottomPanel />);
      expect(screen.getByLabelText(/close panel/i)).toBeInTheDocument();
    });

    it("should dispatch collapse action when clicking close", () => {
      const store = createTestStore({
        workspace: { bottomPanelCollapsed: false },
      });
      renderWithProviders(<BottomPanel />, { store });

      fireEvent.click(screen.getByLabelText(/close panel/i));

      expect(store.getState().workspace.bottomPanelCollapsed).toBe(true);
    });
  });

  describe("content rendering", () => {
    it("should show activity content when activity tab is active", () => {
      renderWithProviders(<BottomPanel />, {
        workspaceOverrides: { bottomPanelActiveTab: "activity" },
      });

      expect(screen.getByTestId("activity-tab-content")).toBeInTheDocument();
    });

    it("should show problems content when problems tab is active", () => {
      renderWithProviders(<BottomPanel />, {
        workspaceOverrides: { bottomPanelActiveTab: "problems" },
      });

      expect(screen.getByTestId("problems-tab-content")).toBeInTheDocument();
    });

    it("should show inspector content when inspector tab is active", () => {
      renderWithProviders(<BottomPanel />, {
        workspaceOverrides: { bottomPanelActiveTab: "inspector" },
      });

      expect(screen.getByTestId("inspector-tab-content")).toBeInTheDocument();
    });
  });

  describe("accessibility", () => {
    it("should have proper tab role structure", () => {
      renderWithProviders(<BottomPanel />);

      expect(screen.getByRole("tablist")).toBeInTheDocument();
    });

    it("should have proper tabpanel", () => {
      renderWithProviders(<BottomPanel />);

      expect(screen.getByRole("tabpanel")).toBeInTheDocument();
    });
  });

  describe("activity log with notifications", () => {
    it("should display notifications as activity items", () => {
      const notifications: Notification[] = [
        {
          id: "n1",
          type: "info",
          title: "Session Started",
          message: "A new chat session was created",
          read: false,
          createdAt: new Date().toISOString(),
        },
        {
          id: "n2",
          type: "success",
          title: "Tool Executed",
          message: "Calculator tool completed successfully",
          read: false,
          createdAt: new Date().toISOString(),
        },
      ];

      renderWithProviders(<BottomPanel />, {
        workspaceOverrides: { bottomPanelActiveTab: "activity" },
        notifications,
      });

      expect(screen.getByText("Session Started")).toBeInTheDocument();
      expect(screen.getByText("Tool Executed")).toBeInTheDocument();
    });

    it("should show empty state when no notifications", () => {
      renderWithProviders(<BottomPanel />, {
        workspaceOverrides: { bottomPanelActiveTab: "activity" },
        notifications: [],
      });

      expect(screen.getByText(/no recent activity/i)).toBeInTheDocument();
    });

    it("should show notification type indicator", () => {
      const notifications: Notification[] = [
        {
          id: "n1",
          type: "error",
          title: "Connection Error",
          message: "Failed to connect to MCP server",
          read: false,
          createdAt: new Date().toISOString(),
        },
      ];

      renderWithProviders(<BottomPanel />, {
        workspaceOverrides: { bottomPanelActiveTab: "activity" },
        notifications,
      });

      expect(screen.getByTestId("activity-item-n1")).toBeInTheDocument();
    });
  });

  describe("mobile overlay mode", () => {
    it("should accept isOpen prop for mobile overlay", () => {
      renderWithProviders(<BottomPanel isOpen={true} />);
      expect(screen.getByTestId("bottom-panel-container")).toBeInTheDocument();
    });

    it("should call onClose when overlay backdrop is clicked", () => {
      const onClose = vi.fn();
      renderWithProviders(<BottomPanel isOpen={true} onClose={onClose} />);

      const overlay = screen.getByTestId("bottom-panel-overlay");
      fireEvent.click(overlay);

      expect(onClose).toHaveBeenCalled();
    });

    it("should not render overlay when isOpen is false", () => {
      renderWithProviders(<BottomPanel isOpen={false} />);
      expect(
        screen.queryByTestId("bottom-panel-overlay"),
      ).not.toBeInTheDocument();
    });

    it("should slide up from bottom in mobile mode", () => {
      renderWithProviders(<BottomPanel isOpen={true} />);
      const panel = screen.getByTestId("bottom-panel-container");
      expect(panel).toHaveClass("fixed");
    });
  });

  describe("problems tab with real data", () => {
    it("should display session errors in problems tab", () => {
      renderWithProviders(<BottomPanel />, {
        workspaceOverrides: { bottomPanelActiveTab: "problems" },
        sessionOverrides: {
          error: "Failed to load session",
        },
      });

      expect(screen.getByText(/failed to load session/i)).toBeInTheDocument();
    });

    it("should display MCP connection errors in problems tab", () => {
      renderWithProviders(<BottomPanel />, {
        workspaceOverrides: { bottomPanelActiveTab: "problems" },
        mcpOverrides: {
          error: "Connection refused",
        },
      });

      expect(screen.getByText(/connection refused/i)).toBeInTheDocument();
    });

    it("should show no problems when all systems healthy", () => {
      renderWithProviders(<BottomPanel />, {
        workspaceOverrides: { bottomPanelActiveTab: "problems" },
        sessionOverrides: { error: null },
        mcpOverrides: { error: null },
      });

      expect(screen.getByText(/no problems detected/i)).toBeInTheDocument();
    });

    it("should show problem count badge", () => {
      renderWithProviders(<BottomPanel />, {
        workspaceOverrides: { bottomPanelActiveTab: "problems" },
        sessionOverrides: { error: "Error 1" },
        mcpOverrides: { error: "Error 2" },
      });

      // Should display both errors
      expect(screen.getByText(/error 1/i)).toBeInTheDocument();
      expect(screen.getByText(/error 2/i)).toBeInTheDocument();
    });
  });

  describe("inspector tab with MCP data", () => {
    it("should display connected MCP servers in inspector tab", () => {
      renderWithProviders(<BottomPanel />, {
        workspaceOverrides: { bottomPanelActiveTab: "inspector" },
        mcpOverrides: {
          servers: {
            "server-1": {
              id: "server-1",
              url: "http://localhost:3000",
              status: "connected",
              tools: [
                {
                  name: "calculator",
                  description: "Math operations",
                  inputSchema: {},
                },
              ],
              resources: [],
              prompts: [],
            },
          },
        },
      });

      expect(screen.getByText("server-1")).toBeInTheDocument();
      expect(screen.getByText(/connected/i)).toBeInTheDocument();
    });

    it("should display MCP tools list in inspector", () => {
      renderWithProviders(<BottomPanel />, {
        workspaceOverrides: { bottomPanelActiveTab: "inspector" },
        mcpOverrides: {
          servers: {
            "server-1": {
              id: "server-1",
              url: "http://localhost:3000",
              status: "connected",
              tools: [
                {
                  name: "calculator",
                  description: "Math operations",
                  inputSchema: {},
                },
                {
                  name: "web_search",
                  description: "Search the web",
                  inputSchema: {},
                },
              ],
              resources: [],
              prompts: [],
            },
          },
        },
      });

      expect(screen.getByText("calculator")).toBeInTheDocument();
      expect(screen.getByText("web_search")).toBeInTheDocument();
    });

    it("should show empty state when no MCP servers", () => {
      renderWithProviders(<BottomPanel />, {
        workspaceOverrides: { bottomPanelActiveTab: "inspector" },
        mcpOverrides: { servers: {} },
      });

      expect(screen.getByText(/select an mcp tool/i)).toBeInTheDocument();
    });
  });
});
