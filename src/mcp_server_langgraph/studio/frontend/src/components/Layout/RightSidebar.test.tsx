/**
 * RightSidebar Component Tests
 *
 * TDD tests for the property inspector right sidebar.
 * Tests cover:
 * - Basic rendering
 * - Collapsible sections
 * - Context-sensitive content
 * - Redux state integration
 */

import { describe, it, expect, vi, beforeEach } from "vitest";
import { render, screen, fireEvent } from "@testing-library/react";
import { Provider } from "react-redux";
import { configureStore } from "@reduxjs/toolkit";

// Import after mocks
import { RightSidebar } from "./RightSidebar";
import workspaceReducer, {
  type WorkspaceState,
} from "../../store/slices/workspaceSlice";
import sessionReducer from "../../store/slices/sessionSlice";
import mcpReducer, { type MCPSliceState } from "../../store/slices/mcpSlice";
import workflowReducer from "../../store/slices/workflowSlice";
import personaReducer from "../../store/slices/personaSlice";
import authReducer from "../../store/slices/authSlice";
import type { SessionState, ClientSession } from "../../types/session";

// Default workspace state for tests
const defaultWorkspaceState: WorkspaceState = {
  version: 1,
  leftSidebarWidth: 280,
  leftSidebarCollapsed: false,
  rightSidebarWidth: 280,
  rightSidebarCollapsed: false,
  rightSidebarPinned: false,
  bottomPanelHeight: 200,
  bottomPanelCollapsed: true,
  activeActivityId: "conversations",
  dockLayout: { type: "tab-group", tabIds: [] },
  tabs: [
    { id: "tab-1", type: "chat", title: "Chat Session", entityId: "session-1" },
  ],
  activeTabId: "tab-1",
  focusMode: false,
  expandedGroups: [],
  expandedPropertySections: ["session-info"],
  bottomPanelActiveTab: "activity",
  scrollPositions: {},
  lastUpdated: 0,
};

// Default session state for tests
const defaultSessionState: SessionState = {
  sessions: [],
  currentSession: null,
  isLoadingSessions: false,
  isLoadingSession: false,
  isSending: false,
  error: null,
  hasMore: false,
  totalCount: 0,
  isLoadingMore: false,
  cursor: null,
};

// Default MCP state for tests
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
    session?: Partial<SessionState>;
    mcp?: Partial<MCPSliceState>;
  } = {},
) {
  return configureStore({
    reducer: {
      workspace: workspaceReducer,
      session: sessionReducer,
      mcp: mcpReducer,
      workflow: workflowReducer,
      persona: personaReducer,
      auth: authReducer,
    },
    preloadedState: {
      workspace: { ...defaultWorkspaceState, ...overrides.workspace },
      session: { ...defaultSessionState, ...overrides.session },
      mcp: { ...defaultMCPState, ...overrides.mcp },
    },
  });
}

// Render helper with providers
function renderWithProviders(
  ui: React.ReactElement,
  options: {
    store?: ReturnType<typeof createTestStore>;
    workspaceOverrides?: Partial<WorkspaceState>;
    sessionOverrides?: Partial<SessionState>;
    mcpOverrides?: Partial<MCPSliceState>;
  } = {},
) {
  const store =
    options.store ??
    createTestStore({
      workspace: options.workspaceOverrides ?? {},
      session: options.sessionOverrides ?? {},
      mcp: options.mcpOverrides ?? {},
    });

  function Wrapper({ children }: { children: React.ReactNode }) {
    return <Provider store={store}>{children}</Provider>;
  }
  return { store, ...render(ui, { wrapper: Wrapper }) };
}

describe("RightSidebar", () => {
  beforeEach(() => {
    vi.clearAllMocks();
  });

  describe("basic rendering", () => {
    it("should render the right sidebar container", () => {
      renderWithProviders(<RightSidebar />);
      expect(screen.getByTestId("right-sidebar")).toBeInTheDocument();
    });

    it("should render header", () => {
      renderWithProviders(<RightSidebar />);
      expect(screen.getByText("PROPERTIES")).toBeInTheDocument();
    });

    it("should render content area", () => {
      renderWithProviders(<RightSidebar />);
      expect(screen.getByTestId("right-sidebar-content")).toBeInTheDocument();
    });
  });

  describe("property sections", () => {
    it("should render session info section for chat tab", () => {
      renderWithProviders(<RightSidebar />, {
        workspaceOverrides: {
          tabs: [{ id: "tab-1", type: "chat", title: "Chat", entityId: "s-1" }],
          activeTabId: "tab-1",
          expandedPropertySections: ["session-info"],
        },
      });

      expect(screen.getByText(/session info/i)).toBeInTheDocument();
    });

    it("should toggle section expansion on click", () => {
      const store = createTestStore({
        workspace: { expandedPropertySections: [] },
      });
      renderWithProviders(<RightSidebar />, { store });

      // Click on a section header
      const sectionHeader = screen.getByText(/session info/i);
      fireEvent.click(sectionHeader);

      expect(store.getState().workspace.expandedPropertySections).toContain(
        "session-info",
      );
    });

    it("should show section content when expanded", () => {
      renderWithProviders(<RightSidebar />, {
        workspaceOverrides: {
          tabs: [
            {
              id: "tab-1",
              type: "chat",
              title: "Chat",
              entityId: "session-123",
            },
          ],
          activeTabId: "tab-1",
          expandedPropertySections: ["session-info"],
        },
      });

      // Look for entity ID in expanded section
      expect(screen.getByText(/session-123/i)).toBeInTheDocument();
    });
  });

  describe("session data integration", () => {
    const mockSession: ClientSession = {
      id: "session-123",
      name: "Test Session",
      config: {
        modelProvider: "anthropic",
        modelName: "claude-3-opus",
        temperature: 0.7,
        maxTokens: 4096,
      },
      messages: [
        {
          id: "msg-1",
          role: "user",
          content: "Hello",
          timestamp: Date.now(),
          usage: { promptTokens: 10, completionTokens: 0, totalTokens: 10 },
        },
        {
          id: "msg-2",
          role: "assistant",
          content: "Hi there!",
          timestamp: Date.now(),
          usage: { promptTokens: 0, completionTokens: 25, totalTokens: 25 },
        },
      ],
      createdAt: Date.now(),
      updatedAt: Date.now(),
    };

    it("should display model name from session config", () => {
      renderWithProviders(<RightSidebar />, {
        workspaceOverrides: {
          tabs: [
            {
              id: "tab-1",
              type: "chat",
              title: "Chat",
              entityId: "session-123",
            },
          ],
          activeTabId: "tab-1",
          expandedPropertySections: ["model-info"],
        },
        sessionOverrides: {
          currentSession: mockSession,
        },
      });

      expect(screen.getByText(/claude-3-opus/i)).toBeInTheDocument();
    });

    it("should display model provider from session config", () => {
      renderWithProviders(<RightSidebar />, {
        workspaceOverrides: {
          tabs: [
            {
              id: "tab-1",
              type: "chat",
              title: "Chat",
              entityId: "session-123",
            },
          ],
          activeTabId: "tab-1",
          expandedPropertySections: ["model-info"],
        },
        sessionOverrides: {
          currentSession: mockSession,
        },
      });

      expect(screen.getByText(/anthropic/i)).toBeInTheDocument();
    });

    it("should display total token count from messages", () => {
      renderWithProviders(<RightSidebar />, {
        workspaceOverrides: {
          tabs: [
            {
              id: "tab-1",
              type: "chat",
              title: "Chat",
              entityId: "session-123",
            },
          ],
          activeTabId: "tab-1",
          expandedPropertySections: ["usage-info"],
        },
        sessionOverrides: {
          currentSession: mockSession,
        },
      });

      // Total tokens should be 35 (10 + 25)
      // Use getAllByText since "35" appears in both badge and value
      const tokenElements = screen.getAllByText(/35/);
      expect(tokenElements.length).toBeGreaterThan(0);
    });

    it("should display estimated cost based on tokens", () => {
      renderWithProviders(<RightSidebar />, {
        workspaceOverrides: {
          tabs: [
            {
              id: "tab-1",
              type: "chat",
              title: "Chat",
              entityId: "session-123",
            },
          ],
          activeTabId: "tab-1",
          expandedPropertySections: ["usage-info"],
        },
        sessionOverrides: {
          currentSession: mockSession,
        },
      });

      // Should display cost estimate (format: $X.XX)
      expect(screen.getByText(/\$\d+\.\d{2,}/)).toBeInTheDocument();
    });

    it("should show message count from session", () => {
      renderWithProviders(<RightSidebar />, {
        workspaceOverrides: {
          tabs: [
            {
              id: "tab-1",
              type: "chat",
              title: "Chat",
              entityId: "session-123",
            },
          ],
          activeTabId: "tab-1",
          expandedPropertySections: ["session-info"],
        },
        sessionOverrides: {
          currentSession: mockSession,
        },
      });

      // Should show 2 messages
      expect(screen.getByText("2")).toBeInTheDocument();
    });

    it("should display MCP tools when available", () => {
      renderWithProviders(<RightSidebar />, {
        workspaceOverrides: {
          tabs: [
            {
              id: "tab-1",
              type: "chat",
              title: "Chat",
              entityId: "session-123",
            },
          ],
          activeTabId: "tab-1",
          expandedPropertySections: ["tools-info"],
        },
        sessionOverrides: {
          currentSession: mockSession,
        },
        mcpOverrides: {
          servers: {
            "server-1": {
              id: "server-1",
              url: "http://localhost:3000",
              status: "connected",
              tools: [
                {
                  name: "calculator",
                  description: "Perform calculations",
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

    it("should show 'No tools' message when no MCP tools", () => {
      renderWithProviders(<RightSidebar />, {
        workspaceOverrides: {
          tabs: [
            {
              id: "tab-1",
              type: "chat",
              title: "Chat",
              entityId: "session-123",
            },
          ],
          activeTabId: "tab-1",
          expandedPropertySections: ["tools-info"],
        },
        sessionOverrides: {
          currentSession: mockSession,
        },
      });

      expect(screen.getByText(/no tools/i)).toBeInTheDocument();
    });
  });

  describe("empty state", () => {
    it("should show empty message when no active tab", () => {
      renderWithProviders(<RightSidebar />, {
        workspaceOverrides: {
          tabs: [],
          activeTabId: null,
        },
      });

      expect(screen.getByText(/select a document/i)).toBeInTheDocument();
    });
  });

  describe("context-sensitive content", () => {
    it("should show chat properties for chat tab", () => {
      renderWithProviders(<RightSidebar />, {
        workspaceOverrides: {
          tabs: [{ id: "tab-1", type: "chat", title: "Chat" }],
          activeTabId: "tab-1",
        },
      });

      expect(screen.getByText(/session info/i)).toBeInTheDocument();
    });

    it("should show workflow properties for workflow tab", () => {
      renderWithProviders(<RightSidebar />, {
        workspaceOverrides: {
          tabs: [{ id: "tab-1", type: "workflow", title: "Workflow" }],
          activeTabId: "tab-1",
        },
      });

      expect(screen.getByText(/workflow info/i)).toBeInTheDocument();
    });
  });

  describe("accessibility", () => {
    it("should have proper region structure", () => {
      renderWithProviders(<RightSidebar />);

      const sidebar = screen.getByTestId("right-sidebar");
      expect(sidebar).toBeInTheDocument();
    });
  });

  describe("collapse button", () => {
    it("should render collapse button in header", () => {
      renderWithProviders(<RightSidebar />);
      expect(screen.getByLabelText(/collapse sidebar/i)).toBeInTheDocument();
    });

    it("should dispatch setRightSidebarCollapsed when collapse button clicked", () => {
      const store = createTestStore({
        workspace: { rightSidebarCollapsed: false },
      });
      renderWithProviders(<RightSidebar />, { store });

      const collapseButton = screen.getByLabelText(/collapse sidebar/i);
      fireEvent.click(collapseButton);

      expect(store.getState().workspace.rightSidebarCollapsed).toBe(true);
    });
  });

  describe("pin toggle", () => {
    it("should render pin button in header (desktop mode)", () => {
      renderWithProviders(<RightSidebar />);
      expect(screen.getByLabelText(/pin sidebar/i)).toBeInTheDocument();
    });

    it("should toggle pinned state when pin button clicked", () => {
      const store = createTestStore({
        workspace: { rightSidebarPinned: false },
      });
      renderWithProviders(<RightSidebar />, { store });

      const pinButton = screen.getByLabelText(/pin sidebar/i);
      fireEvent.click(pinButton);

      expect(store.getState().workspace.rightSidebarPinned).toBe(true);
    });

    it("should show unpin button when sidebar is pinned", () => {
      renderWithProviders(<RightSidebar />, {
        workspaceOverrides: { rightSidebarPinned: true },
      });
      expect(screen.getByLabelText(/unpin sidebar/i)).toBeInTheDocument();
    });

    it("should toggle unpinned state when unpin button clicked", () => {
      const store = createTestStore({
        workspace: { rightSidebarPinned: true },
      });
      renderWithProviders(<RightSidebar />, { store });

      const unpinButton = screen.getByLabelText(/unpin sidebar/i);
      fireEvent.click(unpinButton);

      expect(store.getState().workspace.rightSidebarPinned).toBe(false);
    });

    it("should have tooltip explaining focus mode behavior", () => {
      renderWithProviders(<RightSidebar />);
      const pinButton = screen.getByLabelText(/pin sidebar/i);
      expect(pinButton.getAttribute("title")).toMatch(/focus mode/i);
    });

    it("should not render pin button in mobile mode", () => {
      const onClose = vi.fn();
      renderWithProviders(<RightSidebar isOpen={true} onClose={onClose} />);
      expect(screen.queryByLabelText(/pin sidebar/i)).not.toBeInTheDocument();
    });
  });

  describe("mobile overlay mode", () => {
    it("should accept isOpen prop for mobile overlay", () => {
      renderWithProviders(<RightSidebar isOpen={true} />);
      expect(screen.getByTestId("right-sidebar")).toBeInTheDocument();
    });

    it("should call onClose when overlay backdrop is clicked", () => {
      const onClose = vi.fn();
      renderWithProviders(<RightSidebar isOpen={true} onClose={onClose} />);

      const overlay = screen.getByTestId("right-sidebar-overlay");
      fireEvent.click(overlay);

      expect(onClose).toHaveBeenCalled();
    });

    it("should render close button in mobile mode", () => {
      const onClose = vi.fn();
      renderWithProviders(<RightSidebar isOpen={true} onClose={onClose} />);

      expect(screen.getByLabelText(/close/i)).toBeInTheDocument();
    });

    it("should not render overlay when isOpen is false", () => {
      renderWithProviders(<RightSidebar isOpen={false} />);
      expect(
        screen.queryByTestId("right-sidebar-overlay"),
      ).not.toBeInTheDocument();
    });
  });
});
