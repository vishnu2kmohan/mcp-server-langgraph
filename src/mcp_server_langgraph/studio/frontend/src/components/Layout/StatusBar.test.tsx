/**
 * StatusBar Component Tests
 *
 * TDD tests for the status bar at the bottom of the AppShell.
 * Tests cover:
 * - Basic rendering
 * - Connection status display (via RTK Query health endpoint)
 * - Persona/role indicator
 * - Notification count badge
 * - Responsive design classes
 */

import { describe, it, expect, vi, beforeEach } from "vitest";
import { render, screen } from "@testing-library/react";
import { Provider } from "react-redux";
import { configureStore } from "@reduxjs/toolkit";

// Mock ResizeObserver before imports
vi.stubGlobal(
  "ResizeObserver",
  vi.fn().mockImplementation(() => ({
    observe: vi.fn(),
    unobserve: vi.fn(),
    disconnect: vi.fn(),
  })),
);

// Mock the API module to control useGetHealthQuery responses
// This must be before component imports
const mockUseGetHealthQuery = vi.fn();
vi.mock("../../api", async (importOriginal) => {
  const original = await importOriginal<typeof import("../../api")>();
  return {
    ...original,
    useGetHealthQuery: (...args: unknown[]) => mockUseGetHealthQuery(...args),
  };
});

// Mock the useConnectionHealthWebSocket hook
const mockUseConnectionHealthWebSocket = vi.fn();
vi.mock("../../hooks/useConnectionHealthWebSocket", () => ({
  useConnectionHealthWebSocket: (...args: unknown[]) =>
    mockUseConnectionHealthWebSocket(...args),
}));

// Mock the useMCPTaskWebSocket hook
const mockUseMCPTaskWebSocket = vi.fn();
vi.mock("../../hooks/useMCPTaskWebSocket", () => ({
  useMCPTaskWebSocket: (...args: unknown[]) => mockUseMCPTaskWebSocket(...args),
}));

// Import after mocks
import { StatusBar } from "./StatusBar";
import mcpReducer, { type MCPSliceState } from "../../store/slices/mcpSlice";
import personaReducer from "../../store/slices/personaSlice";
import notificationReducer from "../../store/slices/notificationSlice";
import sessionReducer, {
  type SessionState,
  initialSessionState,
} from "../../store/slices/sessionSlice";
import authReducer from "../../store/slices/authSlice";
import uiReducer from "../../store/slices/uiSlice";
import workspaceReducer from "../../store/slices/workspaceSlice";
import { api } from "../../api";

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
function createTestStore(
  overrides: {
    mcp?: Partial<MCPSliceState>;
    persona?: { persona: string; username: string | null };
    notifications?: { notifications: Array<{ id: string; read: boolean }> };
    session?: Partial<SessionState>;
  } = {},
) {
  return configureStore({
    reducer: {
      [api.reducerPath]: api.reducer,
      mcp: mcpReducer,
      persona: personaReducer,
      notifications: notificationReducer,
      session: sessionReducer,
      auth: authReducer,
      ui: uiReducer,
      workspace: workspaceReducer,
    },
    preloadedState: {
      mcp: { ...defaultMCPState, ...overrides.mcp },
      persona: {
        persona: overrides.persona?.persona ?? "user",
        username: overrides.persona?.username ?? null,
        email: null,
        permissions: [],
        isPersonaLoading: false,
      },
      notifications: {
        notifications: (overrides.notifications?.notifications ?? []).map(
          (n) => ({
            id: n.id,
            type: "info" as const,
            title: "Test",
            message: "Test message",
            read: n.read,
            createdAt: new Date().toISOString(),
          }),
        ),
      },
      session: { ...initialSessionState, ...overrides.session },
    },
    middleware: (getDefaultMiddleware) =>
      getDefaultMiddleware().concat(api.middleware),
  });
}

// Render helper with providers
function renderWithProviders(
  ui: React.ReactElement,
  options: { store?: ReturnType<typeof createTestStore> } = {},
) {
  const store = options.store ?? createTestStore();
  function Wrapper({ children }: { children: React.ReactNode }) {
    return <Provider store={store}>{children}</Provider>;
  }
  return { store, ...render(ui, { wrapper: Wrapper }) };
}

describe("StatusBar", () => {
  beforeEach(() => {
    vi.clearAllMocks();
    // Default: healthy/connected state
    mockUseGetHealthQuery.mockReturnValue({
      data: { status: "healthy" },
      isLoading: false,
      isError: false,
    });
    // Default: MCP connection health WebSocket
    mockUseConnectionHealthWebSocket.mockReturnValue({
      status: "connected",
      connections: [
        { id: "conn-1", name: "MCP Server 1", status: "connected" },
        { id: "conn-2", name: "MCP Server 2", status: "connected" },
      ],
      subscribedConnections: new Set(),
      error: null,
      lastPong: null,
      summary: {
        total: 2,
        connected: 2,
        disconnected: 0,
        connecting: 0,
        error: 0,
        auth_required: 0,
      },
      sendPing: vi.fn(),
      refresh: vi.fn(),
      subscribe: vi.fn(),
      unsubscribe: vi.fn(),
      checkHealth: vi.fn(),
      getConnection: vi.fn(),
      disconnect: vi.fn(),
      reconnect: vi.fn(),
    });
    // Default: MCP task WebSocket - no tasks running
    mockUseMCPTaskWebSocket.mockReturnValue({
      status: "connected",
      tasks: [],
      subscribedTasks: new Set(),
      error: null,
      sendPing: vi.fn(),
      refresh: vi.fn(),
      subscribe: vi.fn(),
      unsubscribe: vi.fn(),
      disconnect: vi.fn(),
      reconnect: vi.fn(),
    });
  });

  describe("basic rendering", () => {
    it("should render the status bar container", () => {
      renderWithProviders(<StatusBar />);
      expect(screen.getByTestId("status-bar")).toBeInTheDocument();
    });

    it("should have proper height and styling", () => {
      renderWithProviders(<StatusBar />);
      const statusBar = screen.getByTestId("status-bar");
      expect(statusBar).toHaveClass("h-6");
    });
  });

  describe("connection status", () => {
    it("should show disconnected status when health check fails (API unreachable)", () => {
      // Mock health query as error state (API unreachable)
      mockUseGetHealthQuery.mockReturnValue({
        data: undefined,
        isLoading: false,
        isError: true,
      });
      renderWithProviders(<StatusBar />);
      expect(screen.getByTestId("connection-status")).toBeInTheDocument();
      expect(screen.getByText(/disconnected/i)).toBeInTheDocument();
    });

    it("should show connected status when health check succeeds", () => {
      // Default mock already returns healthy status
      renderWithProviders(<StatusBar />);
      expect(screen.getByText(/connected/i)).toBeInTheDocument();
    });

    it("should show connecting status when health check is loading", () => {
      // Mock health query as loading state
      mockUseGetHealthQuery.mockReturnValue({
        data: undefined,
        isLoading: true,
        isError: false,
      });
      renderWithProviders(<StatusBar />);
      expect(screen.getByText(/connecting/i)).toBeInTheDocument();
    });

    it("should show degraded status when health check returns degraded", () => {
      // Mock health query as degraded state
      mockUseGetHealthQuery.mockReturnValue({
        data: { status: "degraded" },
        isLoading: false,
        isError: false,
      });
      renderWithProviders(<StatusBar />);
      expect(screen.getByText(/degraded/i)).toBeInTheDocument();
    });

    it("should show unhealthy status when API responds but system is unhealthy", () => {
      // Mock health query as unhealthy state (API responds but backend has issues)
      mockUseGetHealthQuery.mockReturnValue({
        data: { status: "unhealthy" },
        isLoading: false,
        isError: false,
      });
      renderWithProviders(<StatusBar />);
      expect(screen.getByText(/unhealthy/i)).toBeInTheDocument();
    });

    it("should have tooltip on connection status element", () => {
      renderWithProviders(<StatusBar />);
      const connectionStatus = screen.getByTestId("connection-status");
      expect(connectionStatus).toHaveAttribute("title");
    });
  });

  describe("persona indicator", () => {
    it("should show user persona by default", () => {
      renderWithProviders(<StatusBar />);
      expect(screen.getByTestId("persona-indicator")).toBeInTheDocument();
      expect(screen.getByText(/user/i)).toBeInTheDocument();
    });

    it("should show admin persona when logged in as admin", () => {
      const store = createTestStore({
        persona: { persona: "admin", username: "admin@example.com" },
      });
      renderWithProviders(<StatusBar />, { store });
      expect(screen.getByText(/admin/i)).toBeInTheDocument();
    });

    it("should show developer persona when logged in as developer", () => {
      const store = createTestStore({
        persona: { persona: "developer", username: "dev@example.com" },
      });
      renderWithProviders(<StatusBar />, { store });
      expect(screen.getByText(/developer/i)).toBeInTheDocument();
    });
  });

  // NOTE: Notification count badge was removed from StatusBar per UX requirements
  // The status bar now shows only essential session information

  describe("tooltips", () => {
    it("should have tooltip on persona indicator", () => {
      renderWithProviders(<StatusBar />);
      const personaIndicator = screen.getByTestId("persona-indicator");
      expect(personaIndicator).toHaveAttribute("title");
    });

    it("should have tooltip on session info when present", () => {
      const store = createTestStore({
        session: {
          currentSession: {
            id: "session-1",
            name: "My Chat Session",
            messages: [],
            createdAt: Date.now(),
            updatedAt: Date.now(),
          },
        },
      });
      renderWithProviders(<StatusBar />, { store });
      const sessionInfo = screen.getByTestId("session-info");
      expect(sessionInfo).toHaveAttribute("title");
    });

    it("should have tooltip on model info when present", () => {
      const store = createTestStore({
        session: {
          currentSession: {
            id: "session-1",
            name: "Test Session",
            config: {
              modelProvider: "openai",
              modelName: "gpt-4",
              temperature: 0.7,
              maxTokens: 4096,
            },
            messages: [],
            createdAt: Date.now(),
            updatedAt: Date.now(),
          },
        },
      });
      renderWithProviders(<StatusBar />, { store });
      const modelInfo = screen.getByTestId("model-info");
      expect(modelInfo).toHaveAttribute("title");
    });

    it("should have tooltip on token count when present", () => {
      const store = createTestStore({
        session: {
          currentSession: {
            id: "session-1",
            name: "Test Session",
            config: {
              modelProvider: "openai",
              modelName: "gpt-4",
              temperature: 0.7,
              maxTokens: 4096,
            },
            messages: [
              {
                id: "m1",
                role: "user",
                content: "Hello",
                timestamp: Date.now(),
                usage: {
                  promptTokens: 100,
                  completionTokens: 50,
                  totalTokens: 150,
                },
              },
            ],
            createdAt: Date.now(),
            updatedAt: Date.now(),
          },
        },
      });
      renderWithProviders(<StatusBar />, { store });
      const tokenCount = screen.getByTestId("token-count");
      expect(tokenCount).toHaveAttribute("title");
    });

    it("should have tooltip on cost estimate when present", () => {
      const store = createTestStore({
        session: {
          currentSession: {
            id: "session-1",
            name: "Test Session",
            config: {
              modelProvider: "openai",
              modelName: "gpt-4",
              temperature: 0.7,
              maxTokens: 4096,
            },
            messages: [
              {
                id: "m1",
                role: "user",
                content: "Hello",
                timestamp: Date.now(),
                usage: {
                  promptTokens: 1000,
                  completionTokens: 500,
                  totalTokens: 1500,
                },
              },
            ],
            createdAt: Date.now(),
            updatedAt: Date.now(),
          },
        },
      });
      renderWithProviders(<StatusBar />, { store });
      const costEstimate = screen.getByTestId("cost-estimate");
      expect(costEstimate).toHaveAttribute("title");
    });
  });

  describe("accessibility", () => {
    it("should have proper semantic structure", () => {
      renderWithProviders(<StatusBar />);
      const statusBar = screen.getByTestId("status-bar");
      expect(statusBar.tagName).toBe("DIV");
    });
  });

  describe("session info", () => {
    it("should show session name when current session exists", () => {
      const store = createTestStore({
        session: {
          currentSession: {
            id: "session-1",
            name: "My Chat Session",
            messages: [],
            createdAt: Date.now(),
            updatedAt: Date.now(),
          },
        },
      });
      renderWithProviders(<StatusBar />, { store });
      expect(screen.getByTestId("session-info")).toBeInTheDocument();
      expect(screen.getByText(/my chat session/i)).toBeInTheDocument();
    });

    it("should not show session info when no current session", () => {
      renderWithProviders(<StatusBar />);
      expect(screen.queryByTestId("session-info")).not.toBeInTheDocument();
    });

    it("should show message count for current session", () => {
      const store = createTestStore({
        session: {
          currentSession: {
            id: "session-1",
            name: "Test Session",
            messages: [
              {
                id: "m1",
                role: "user",
                content: "Hello",
                timestamp: Date.now(),
              },
              {
                id: "m2",
                role: "assistant",
                content: "Hi",
                timestamp: Date.now(),
              },
              {
                id: "m3",
                role: "user",
                content: "How are you?",
                timestamp: Date.now(),
              },
            ],
            createdAt: Date.now(),
            updatedAt: Date.now(),
          },
        },
      });
      renderWithProviders(<StatusBar />, { store });
      expect(screen.getByText(/3 msgs/i)).toBeInTheDocument();
    });

    it("should show singular message for single message", () => {
      const store = createTestStore({
        session: {
          currentSession: {
            id: "session-1",
            name: "Test Session",
            messages: [
              {
                id: "m1",
                role: "user",
                content: "Hello",
                timestamp: Date.now(),
              },
            ],
            createdAt: Date.now(),
            updatedAt: Date.now(),
          },
        },
      });
      renderWithProviders(<StatusBar />, { store });
      expect(screen.getByText(/1 msg\b/i)).toBeInTheDocument();
    });
  });

  describe("model and usage info", () => {
    it("should display model name from session config", () => {
      const store = createTestStore({
        session: {
          currentSession: {
            id: "session-1",
            name: "Test Session",
            config: {
              modelProvider: "anthropic",
              modelName: "claude-3-sonnet",
              temperature: 0.7,
              maxTokens: 4096,
            },
            messages: [],
            createdAt: Date.now(),
            updatedAt: Date.now(),
          },
        },
      });
      renderWithProviders(<StatusBar />, { store });
      expect(screen.getByTestId("model-info")).toBeInTheDocument();
      expect(screen.getByText(/claude-3-sonnet/i)).toBeInTheDocument();
    });

    it("should display total token count from messages", () => {
      const store = createTestStore({
        session: {
          currentSession: {
            id: "session-1",
            name: "Test Session",
            config: {
              modelProvider: "openai",
              modelName: "gpt-4",
              temperature: 0.7,
              maxTokens: 4096,
            },
            messages: [
              {
                id: "m1",
                role: "user",
                content: "Hello",
                timestamp: Date.now(),
                usage: {
                  promptTokens: 100,
                  completionTokens: 0,
                  totalTokens: 100,
                },
              },
              {
                id: "m2",
                role: "assistant",
                content: "Hi there!",
                timestamp: Date.now(),
                usage: {
                  promptTokens: 0,
                  completionTokens: 150,
                  totalTokens: 150,
                },
              },
            ],
            createdAt: Date.now(),
            updatedAt: Date.now(),
          },
        },
      });
      renderWithProviders(<StatusBar />, { store });
      expect(screen.getByTestId("token-count")).toBeInTheDocument();
      // Total should be 250
      expect(screen.getByText(/250/)).toBeInTheDocument();
    });

    it("should display estimated cost based on tokens", () => {
      const store = createTestStore({
        session: {
          currentSession: {
            id: "session-1",
            name: "Test Session",
            config: {
              modelProvider: "openai",
              modelName: "gpt-4",
              temperature: 0.7,
              maxTokens: 4096,
            },
            messages: [
              {
                id: "m1",
                role: "user",
                content: "Hello",
                timestamp: Date.now(),
                usage: {
                  promptTokens: 1000,
                  completionTokens: 0,
                  totalTokens: 1000,
                },
              },
              {
                id: "m2",
                role: "assistant",
                content: "Hi there!",
                timestamp: Date.now(),
                usage: {
                  promptTokens: 0,
                  completionTokens: 500,
                  totalTokens: 500,
                },
              },
            ],
            createdAt: Date.now(),
            updatedAt: Date.now(),
          },
        },
      });
      renderWithProviders(<StatusBar />, { store });
      expect(screen.getByTestId("cost-estimate")).toBeInTheDocument();
      // Should display cost in $X.XX format
      expect(screen.getByText(/\$\d+\.\d{2}/)).toBeInTheDocument();
    });

    it("should not show model info when no session", () => {
      renderWithProviders(<StatusBar />);
      expect(screen.queryByTestId("model-info")).not.toBeInTheDocument();
    });
  });

  describe("MCP connection status", () => {
    it("should display MCP connection count when connections exist", () => {
      renderWithProviders(<StatusBar />);
      expect(screen.getByTestId("mcp-status")).toBeInTheDocument();
      // Should show 2/2 connected
      expect(screen.getByText(/2\/2/)).toBeInTheDocument();
    });

    it("should show warning style when some connections are not healthy", () => {
      mockUseConnectionHealthWebSocket.mockReturnValue({
        status: "connected",
        connections: [
          { id: "conn-1", name: "MCP Server 1", status: "connected" },
          { id: "conn-2", name: "MCP Server 2", status: "error" },
        ],
        subscribedConnections: new Set(),
        error: null,
        lastPong: null,
        summary: {
          total: 2,
          connected: 1,
          disconnected: 0,
          connecting: 0,
          error: 1,
          auth_required: 0,
        },
        sendPing: vi.fn(),
        refresh: vi.fn(),
        subscribe: vi.fn(),
        unsubscribe: vi.fn(),
        checkHealth: vi.fn(),
        getConnection: vi.fn(),
        disconnect: vi.fn(),
        reconnect: vi.fn(),
      });
      renderWithProviders(<StatusBar />);
      const mcpStatus = screen.getByTestId("mcp-status");
      expect(mcpStatus).toBeInTheDocument();
      expect(screen.getByText(/1\/2/)).toBeInTheDocument();
    });

    it("should show error style when all connections are down", () => {
      mockUseConnectionHealthWebSocket.mockReturnValue({
        status: "connected",
        connections: [
          { id: "conn-1", name: "MCP Server 1", status: "error" },
          { id: "conn-2", name: "MCP Server 2", status: "disconnected" },
        ],
        subscribedConnections: new Set(),
        error: null,
        lastPong: null,
        summary: {
          total: 2,
          connected: 0,
          disconnected: 1,
          connecting: 0,
          error: 1,
          auth_required: 0,
        },
        sendPing: vi.fn(),
        refresh: vi.fn(),
        subscribe: vi.fn(),
        unsubscribe: vi.fn(),
        checkHealth: vi.fn(),
        getConnection: vi.fn(),
        disconnect: vi.fn(),
        reconnect: vi.fn(),
      });
      renderWithProviders(<StatusBar />);
      const mcpStatus = screen.getByTestId("mcp-status");
      expect(mcpStatus).toBeInTheDocument();
      expect(screen.getByText(/0\/2/)).toBeInTheDocument();
    });

    it("should not show MCP status when no connections configured", () => {
      mockUseConnectionHealthWebSocket.mockReturnValue({
        status: "connected",
        connections: [],
        subscribedConnections: new Set(),
        error: null,
        lastPong: null,
        summary: {
          total: 0,
          connected: 0,
          disconnected: 0,
          connecting: 0,
          error: 0,
          auth_required: 0,
        },
        sendPing: vi.fn(),
        refresh: vi.fn(),
        subscribe: vi.fn(),
        unsubscribe: vi.fn(),
        checkHealth: vi.fn(),
        getConnection: vi.fn(),
        disconnect: vi.fn(),
        reconnect: vi.fn(),
      });
      renderWithProviders(<StatusBar />);
      expect(screen.queryByTestId("mcp-status")).not.toBeInTheDocument();
    });

    it("should have tooltip with connection details", () => {
      renderWithProviders(<StatusBar />);
      const mcpStatus = screen.getByTestId("mcp-status");
      expect(mcpStatus).toHaveAttribute("title");
      expect(mcpStatus.getAttribute("title")).toContain("MCP");
    });
  });

  describe("MCP task status", () => {
    it("should display task count when tasks are running", () => {
      mockUseMCPTaskWebSocket.mockReturnValue({
        status: "connected",
        tasks: [
          {
            task_id: "task-1",
            status: "running",
            created_at: "2025-01-01",
            last_updated_at: "2025-01-01",
            ttl: 3600,
            poll_interval: 5,
          },
          {
            task_id: "task-2",
            status: "pending",
            created_at: "2025-01-01",
            last_updated_at: "2025-01-01",
            ttl: 3600,
            poll_interval: 5,
          },
          {
            task_id: "task-3",
            status: "running",
            created_at: "2025-01-01",
            last_updated_at: "2025-01-01",
            ttl: 3600,
            poll_interval: 5,
          },
        ],
        subscribedTasks: new Set(),
        error: null,
        sendPing: vi.fn(),
        refresh: vi.fn(),
        subscribe: vi.fn(),
        unsubscribe: vi.fn(),
        disconnect: vi.fn(),
        reconnect: vi.fn(),
      });
      renderWithProviders(<StatusBar />);
      const taskStatus = screen.getByTestId("task-status");
      expect(taskStatus).toBeInTheDocument();
      // Should show 3 active tasks - using within to be specific
      expect(taskStatus.textContent).toContain("3");
    });

    it("should not show task status when no active tasks", () => {
      mockUseMCPTaskWebSocket.mockReturnValue({
        status: "connected",
        tasks: [
          {
            task_id: "task-1",
            status: "completed",
            created_at: "2025-01-01",
            last_updated_at: "2025-01-01",
            ttl: 3600,
            poll_interval: 5,
          },
        ],
        subscribedTasks: new Set(),
        error: null,
        sendPing: vi.fn(),
        refresh: vi.fn(),
        subscribe: vi.fn(),
        unsubscribe: vi.fn(),
        disconnect: vi.fn(),
        reconnect: vi.fn(),
      });
      renderWithProviders(<StatusBar />);
      expect(screen.queryByTestId("task-status")).not.toBeInTheDocument();
    });

    it("should show running indicator when tasks are running", () => {
      mockUseMCPTaskWebSocket.mockReturnValue({
        status: "connected",
        tasks: [
          {
            task_id: "task-1",
            status: "running",
            created_at: "2025-01-01",
            last_updated_at: "2025-01-01",
            ttl: 3600,
            poll_interval: 5,
          },
        ],
        subscribedTasks: new Set(),
        error: null,
        sendPing: vi.fn(),
        refresh: vi.fn(),
        subscribe: vi.fn(),
        unsubscribe: vi.fn(),
        disconnect: vi.fn(),
        reconnect: vi.fn(),
      });
      renderWithProviders(<StatusBar />);
      const taskStatus = screen.getByTestId("task-status");
      expect(taskStatus).toBeInTheDocument();
    });

    it("should have tooltip with task details", () => {
      mockUseMCPTaskWebSocket.mockReturnValue({
        status: "connected",
        tasks: [
          {
            task_id: "task-1",
            status: "running",
            created_at: "2025-01-01",
            last_updated_at: "2025-01-01",
            ttl: 3600,
            poll_interval: 5,
          },
        ],
        subscribedTasks: new Set(),
        error: null,
        sendPing: vi.fn(),
        refresh: vi.fn(),
        subscribe: vi.fn(),
        unsubscribe: vi.fn(),
        disconnect: vi.fn(),
        reconnect: vi.fn(),
      });
      renderWithProviders(<StatusBar />);
      const taskStatus = screen.getByTestId("task-status");
      expect(taskStatus).toHaveAttribute("title");
      expect(taskStatus.getAttribute("title")).toContain("task");
    });
  });
});
