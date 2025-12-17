/**
 * StatusBar Component Tests
 *
 * TDD tests for the status bar at the bottom of the AppShell.
 * Tests cover:
 * - Basic rendering
 * - Connection status display
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

// Import after mocks
import { StatusBar } from "./StatusBar";
import mcpReducer, { type MCPSliceState } from "../../store/slices/mcpSlice";
import personaReducer from "../../store/slices/personaSlice";
import notificationReducer from "../../store/slices/notificationSlice";
import sessionReducer, {
  type SessionState,
  initialSessionState,
} from "../../store/slices/sessionSlice";

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
    mcp?: Partial<MCPSliceState>;
    persona?: { persona: string; username: string | null };
    notifications?: { notifications: Array<{ id: string; read: boolean }> };
    session?: Partial<SessionState>;
  } = {},
) {
  return configureStore({
    reducer: {
      mcp: mcpReducer,
      persona: personaReducer,
      notifications: notificationReducer,
      session: sessionReducer,
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
    it("should show disconnected status when no servers connected", () => {
      renderWithProviders(<StatusBar />);
      expect(screen.getByTestId("connection-status")).toBeInTheDocument();
      expect(screen.getByText(/disconnected/i)).toBeInTheDocument();
    });

    it("should show connected status when server is connected", () => {
      const store = createTestStore({
        mcp: {
          servers: {
            "server-1": {
              id: "server-1",
              url: "http://localhost:3000",
              status: "connected",
              tools: [],
              resources: [],
              prompts: [],
            },
          },
        },
      });
      renderWithProviders(<StatusBar />, { store });
      expect(screen.getByText(/connected/i)).toBeInTheDocument();
    });

    it("should show connecting status when connecting", () => {
      const store = createTestStore({
        mcp: {
          isConnecting: true,
        },
      });
      renderWithProviders(<StatusBar />, { store });
      expect(screen.getByText(/connecting/i)).toBeInTheDocument();
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

  describe("notification count", () => {
    it("should not show badge when no unread notifications", () => {
      renderWithProviders(<StatusBar />);
      expect(
        screen.queryByTestId("notification-count"),
      ).not.toBeInTheDocument();
    });

    it("should show badge with unread count", () => {
      const store = createTestStore({
        notifications: {
          notifications: [
            { id: "1", read: false },
            { id: "2", read: false },
            { id: "3", read: true },
          ],
        },
      });
      renderWithProviders(<StatusBar />, { store });
      const badge = screen.getByTestId("notification-count");
      expect(badge).toBeInTheDocument();
      expect(badge).toHaveTextContent("2");
    });
  });

  describe("ready state", () => {
    it("should show Ready text by default", () => {
      renderWithProviders(<StatusBar />);
      expect(screen.getByText("Ready")).toBeInTheDocument();
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
      expect(screen.getByText(/3 messages/i)).toBeInTheDocument();
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
      expect(screen.getByText(/1 message\b/i)).toBeInTheDocument();
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
});
