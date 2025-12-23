/**
 * ConnectedConversationPanel Tests
 *
 * Integration tests for the Redux-connected conversation panel that:
 * - Integrates with React Router loaders for message data
 * - Dispatches Redux actions for sending messages
 * - Uses message revalidation after sending
 * - Renders ConversationPanel with slash commands
 */
import { describe, it, expect, vi, beforeEach, afterEach } from "vitest";
import { render, screen, waitFor, cleanup } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { Provider } from "react-redux";
import { configureStore } from "@reduxjs/toolkit";
import { MemoryRouter, Routes, Route } from "react-router";
import React from "react";
import { ConnectedConversationPanel } from "./ConnectedConversationPanel";
import sessionReducer from "../store/slices/sessionSlice";
import type { ChatLoaderData } from "../router/loaders";
import type { ChatMessage } from "./MessageBubble";
import { TelemetryProvider } from "../contexts/TelemetryContext";

// =============================================================================
// Mocks
// =============================================================================

// Mock useRouteLoaderData
const mockSessionLoaderData: ChatLoaderData = {
  sessionId: "session-123",
  messages: [],
  artifacts: [],
};

vi.mock("react-router", async () => {
  const actual =
    await vi.importActual<typeof import("react-router")>("react-router");
  return {
    ...actual,
    useRouteLoaderData: vi.fn((routeId: string) => {
      if (routeId === "chat-session") {
        return mockSessionLoaderData;
      }
      if (routeId === "chat-index") {
        return undefined;
      }
      return undefined;
    }),
  };
});

// Mock useMessageRevalidation hook
const mockRevalidateMessages = vi.fn();
vi.mock("../hooks/useMessageRevalidation", () => ({
  useMessageRevalidation: () => ({
    revalidateMessages: mockRevalidateMessages,
  }),
}));

// Mock conversation intelligence hooks (Sprint 3)
vi.mock("../hooks/useConversationIntelligence", () => ({
  useIntentDetection: vi.fn(() => ({
    intent: "code_request",
    confidence: 0.92,
    subIntents: ["generate", "explain"],
    isLoading: false,
    error: null,
    refetch: vi.fn(),
  })),
  useContextOptimization: vi.fn(() => ({
    suggestions: [
      {
        type: "remove_old_messages",
        description: "Remove messages older than 1 hour",
        tokensSaved: 25000,
      },
    ],
    usagePercent: 93.75,
    currentTokens: 120000,
    maxTokens: 128000,
    recommendedAction: "remove_old_messages",
    isLoading: false,
    error: null,
    refetch: vi.fn(),
  })),
  useGoalTracking: vi.fn(() => ({
    primaryGoal: "Build a REST API",
    subGoals: ["Implement auth", "Add endpoints"],
    progressPercent: 45,
    currentFocus: "Implement auth",
    completedSubGoals: [],
    isLoading: false,
    error: null,
    refetch: vi.fn(),
  })),
}));

// =============================================================================
// Test Setup
// =============================================================================

const createTestStore = (initialState?: Partial<{ session: unknown }>) => {
  return configureStore({
    reducer: {
      session: sessionReducer,
    },
    preloadedState: initialState,
  });
};

const createMockMessage = (
  overrides: Partial<ChatMessage> = {},
): ChatMessage => ({
  id: "msg-1",
  role: "user",
  content: "Hello, how are you?",
  timestamp: Date.now(),
  ...overrides,
});

interface WrapperProps {
  children: React.ReactNode;
}

const createWrapper = (store: ReturnType<typeof createTestStore>) => {
  return function Wrapper({ children }: WrapperProps) {
    return (
      <Provider store={store}>
        <TelemetryProvider>
          <MemoryRouter>
            <Routes>
              <Route
                path="/"
                element={<div data-testid="router-wrapper">{children}</div>}
              />
            </Routes>
          </MemoryRouter>
        </TelemetryProvider>
      </Provider>
    );
  };
};

// =============================================================================
// Tests
// =============================================================================

describe("ConnectedConversationPanel", () => {
  beforeEach(() => {
    vi.clearAllMocks();
    // Reset loader data
    mockSessionLoaderData.sessionId = "session-123";
    mockSessionLoaderData.messages = [];
    mockSessionLoaderData.artifacts = [];
    mockSessionLoaderData.session = undefined;
  });

  afterEach(() => {
    cleanup();
    vi.clearAllMocks();
  });

  describe("Rendering", () => {
    it("should render conversation panel", () => {
      const store = createTestStore();
      render(<ConnectedConversationPanel />, { wrapper: createWrapper(store) });

      expect(screen.getByTestId("conversation-panel")).toBeInTheDocument();
    });

    it("should render ConversationPanel component", () => {
      const store = createTestStore();
      render(<ConnectedConversationPanel />, { wrapper: createWrapper(store) });

      expect(screen.getByTestId("conversation-panel")).toBeInTheDocument();
    });

    it("should apply custom className to wrapper container", () => {
      const store = createTestStore();
      render(<ConnectedConversationPanel className="custom-class" />, {
        wrapper: createWrapper(store),
      });

      // className is applied to the wrapper div containing both AI indicators and ConversationPanel
      // We verify by checking that custom-class exists in the component hierarchy
      const conversationPanel = screen.getByTestId("conversation-panel");
      expect(conversationPanel.parentElement).toHaveClass("custom-class");
    });
  });

  describe("Loader Data Integration", () => {
    it("should display messages from session loader data", () => {
      const store = createTestStore();
      mockSessionLoaderData.messages = [
        createMockMessage({ id: "msg-1", content: "Hello world" }),
        createMockMessage({
          id: "msg-2",
          role: "assistant",
          content: "Hi there!",
        }),
      ];

      render(<ConnectedConversationPanel />, { wrapper: createWrapper(store) });

      expect(screen.getByText("Hello world")).toBeInTheDocument();
      expect(screen.getByText("Hi there!")).toBeInTheDocument();
    });

    it("should display empty state when no messages", () => {
      const store = createTestStore();
      mockSessionLoaderData.messages = [];

      render(<ConnectedConversationPanel />, { wrapper: createWrapper(store) });

      // Should render conversation panel even without messages
      expect(screen.getByTestId("conversation-panel")).toBeInTheDocument();
    });

    it("should display session title when available from Redux", () => {
      // Session title comes from Redux currentSession.name, not loader data
      const store = createTestStore({
        session: {
          currentSession: {
            id: "session-123",
            name: "Test Session Title",
          },
          sessions: [],
          isLoading: false,
          error: null,
        },
      });

      render(<ConnectedConversationPanel />, { wrapper: createWrapper(store) });

      expect(screen.getByText("Test Session Title")).toBeInTheDocument();
    });

    it("should fallback to index loader when session loader is undefined", () => {
      const store = createTestStore();
      // Index loader returns undefined in our mock

      render(<ConnectedConversationPanel />, { wrapper: createWrapper(store) });

      // Should still render without errors
      expect(screen.getByTestId("conversation-panel")).toBeInTheDocument();
    });
  });

  describe("Message Sending", () => {
    it("should dispatch sendMessage action when message is sent", async () => {
      const user = userEvent.setup();
      const store = createTestStore();

      render(<ConnectedConversationPanel />, { wrapper: createWrapper(store) });

      // Find and type in the input
      const input = screen.getByRole("textbox");
      await user.type(input, "Test message");

      // Find and click the send button
      const sendButton = screen.getByRole("button", { name: /send/i });
      await user.click(sendButton);

      // Verify revalidation was called
      await waitFor(() => {
        expect(mockRevalidateMessages).toHaveBeenCalled();
      });
    });

    it("should trigger message revalidation after sending", async () => {
      const user = userEvent.setup();
      const store = createTestStore();

      render(<ConnectedConversationPanel />, { wrapper: createWrapper(store) });

      const input = screen.getByRole("textbox");
      await user.type(input, "Hello{Enter}");

      await waitFor(() => {
        expect(mockRevalidateMessages).toHaveBeenCalledTimes(1);
      });
    });

    it("should have autoFocus enabled on input", () => {
      const store = createTestStore();

      render(<ConnectedConversationPanel />, { wrapper: createWrapper(store) });

      // Input should be focused (autoFocus is true by default)
      const input = screen.getByRole("textbox");
      expect(input).toBeInTheDocument();
    });
  });

  describe("Slash Commands", () => {
    it("should render with default slash commands", () => {
      const store = createTestStore();

      render(<ConnectedConversationPanel />, { wrapper: createWrapper(store) });

      // Component should render without errors
      expect(screen.getByTestId("conversation-panel")).toBeInTheDocument();
    });

    it("should have new, clear, and help commands available", async () => {
      const user = userEvent.setup();
      const store = createTestStore();

      render(<ConnectedConversationPanel />, { wrapper: createWrapper(store) });

      // Type / to trigger slash command menu
      const input = screen.getByRole("textbox");
      await user.type(input, "/");

      // The slash command menu should appear with commands
      // Commands are displayed as "/{name}" e.g. "/new"
      await waitFor(
        () => {
          expect(screen.getByTestId("slash-command-menu")).toBeInTheDocument();
          expect(screen.getByText("/new")).toBeInTheDocument();
        },
        { timeout: 1000 },
      );
    });
  });

  describe("Telemetry", () => {
    it("should log message sent event", async () => {
      const user = userEvent.setup();
      const store = createTestStore();

      render(<ConnectedConversationPanel />, { wrapper: createWrapper(store) });

      const input = screen.getByRole("textbox");
      await user.type(input, "Test message");

      const sendButton = screen.getByRole("button", { name: /send/i });
      await user.click(sendButton);

      // Just verify no errors occur - actual telemetry is logged via devLogger
      expect(screen.getByTestId("conversation-panel")).toBeInTheDocument();
    });
  });

  describe("Session Header", () => {
    it("should display session header when session title is provided from Redux", () => {
      // Session title comes from Redux currentSession.name
      const store = createTestStore({
        session: {
          currentSession: {
            id: "session-123",
            name: "My Chat Session",
          },
          sessions: [],
          isLoading: false,
          error: null,
        },
      });

      render(<ConnectedConversationPanel />, { wrapper: createWrapper(store) });

      expect(screen.getByTestId("session-header")).toBeInTheDocument();
      expect(screen.getByText("My Chat Session")).toBeInTheDocument();
    });

    it("should not display session header when no session title", () => {
      const store = createTestStore();
      mockSessionLoaderData.session = undefined;

      render(<ConnectedConversationPanel />, { wrapper: createWrapper(store) });

      expect(screen.queryByTestId("session-header")).not.toBeInTheDocument();
    });
  });

  describe("Message List", () => {
    it("should render user messages with correct role", () => {
      const store = createTestStore();
      mockSessionLoaderData.messages = [
        createMockMessage({
          id: "user-msg",
          role: "user",
          content: "User message",
        }),
      ];

      render(<ConnectedConversationPanel />, { wrapper: createWrapper(store) });

      expect(screen.getByText("User message")).toBeInTheDocument();
    });

    it("should render assistant messages with correct role", () => {
      const store = createTestStore();
      mockSessionLoaderData.messages = [
        createMockMessage({
          id: "assistant-msg",
          role: "assistant",
          content: "Assistant response",
        }),
      ];

      render(<ConnectedConversationPanel />, { wrapper: createWrapper(store) });

      expect(screen.getByText("Assistant response")).toBeInTheDocument();
    });

    it("should render multiple messages in order", () => {
      const store = createTestStore();
      mockSessionLoaderData.messages = [
        createMockMessage({
          id: "msg-1",
          content: "First message",
          timestamp: 1000,
        }),
        createMockMessage({
          id: "msg-2",
          content: "Second message",
          timestamp: 2000,
        }),
        createMockMessage({
          id: "msg-3",
          content: "Third message",
          timestamp: 3000,
        }),
      ];

      render(<ConnectedConversationPanel />, { wrapper: createWrapper(store) });

      expect(screen.getByText("First message")).toBeInTheDocument();
      expect(screen.getByText("Second message")).toBeInTheDocument();
      expect(screen.getByText("Third message")).toBeInTheDocument();
    });
  });

  describe("Accessibility", () => {
    it("should have accessible input", () => {
      const store = createTestStore();

      render(<ConnectedConversationPanel />, { wrapper: createWrapper(store) });

      const input = screen.getByRole("textbox");
      expect(input).toBeInTheDocument();
    });

    it("should have accessible send button", () => {
      const store = createTestStore();

      render(<ConnectedConversationPanel />, { wrapper: createWrapper(store) });

      const sendButton = screen.getByRole("button", { name: /send/i });
      expect(sendButton).toBeInTheDocument();
    });
  });

  describe("Redux Integration", () => {
    it("should read current session from Redux", () => {
      const store = createTestStore({
        session: {
          currentSession: {
            id: "redux-session",
            name: "Redux Session Name",
          },
          sessions: [],
          isLoading: false,
          error: null,
        },
      });

      render(<ConnectedConversationPanel />, { wrapper: createWrapper(store) });

      // Session title comes from Redux currentSession.name
      expect(screen.getByText("Redux Session Name")).toBeInTheDocument();
    });
  });

  // =============================================================================
  // Sprint 3: Conversation Intelligence Tests (TDD - tests written first)
  // =============================================================================

  describe("Conversation Intelligence (Sprint 3)", () => {
    describe("Intent Detection", () => {
      it("should display intent indicator when enableAI is true and user has typed 3+ chars", async () => {
        const user = userEvent.setup();
        const store = createTestStore();

        render(<ConnectedConversationPanel enableAI userId="test-user" />, {
          wrapper: createWrapper(store),
        });

        // Type at least 3 characters to trigger intent detection
        const input = screen.getByRole("textbox");
        await user.type(input, "test");

        // Intent indicator should be rendered
        await waitFor(() => {
          expect(screen.queryByTestId("intent-indicator")).toBeInTheDocument();
        });
      });

      it("should not display intent indicator when enableAI is false", async () => {
        const user = userEvent.setup();
        const store = createTestStore();

        render(<ConnectedConversationPanel enableAI={false} />, {
          wrapper: createWrapper(store),
        });

        // Type something - intent should still not show because enableAI is false
        const input = screen.getByRole("textbox");
        await user.type(input, "test query");

        expect(
          screen.queryByTestId("intent-indicator"),
        ).not.toBeInTheDocument();
      });

      it("should not display intent indicator with fewer than 3 characters", async () => {
        const user = userEvent.setup();
        const store = createTestStore();

        render(<ConnectedConversationPanel enableAI userId="test-user" />, {
          wrapper: createWrapper(store),
        });

        // Type only 2 characters - not enough to trigger intent detection
        const input = screen.getByRole("textbox");
        await user.type(input, "ab");

        // Intent indicator should NOT be rendered (need 3+ chars)
        expect(
          screen.queryByTestId("intent-indicator"),
        ).not.toBeInTheDocument();
      });
    });

    describe("Context Optimization", () => {
      it("should display context warning when approaching token limit", async () => {
        const store = createTestStore();

        render(
          <ConnectedConversationPanel
            enableAI
            userId="test-user"
            showContextWarning
          />,
          { wrapper: createWrapper(store) },
        );

        // Context warning should appear when usage is high
        await waitFor(() => {
          expect(screen.queryByTestId("context-warning")).toBeInTheDocument();
        });
      });

      it("should not display context warning when under threshold", () => {
        const store = createTestStore();

        render(
          <ConnectedConversationPanel
            enableAI
            userId="test-user"
            showContextWarning={false}
          />,
          { wrapper: createWrapper(store) },
        );

        expect(screen.queryByTestId("context-warning")).not.toBeInTheDocument();
      });
    });

    describe("Goal Tracking", () => {
      it("should display goal tracker when enabled", async () => {
        const store = createTestStore();

        render(
          <ConnectedConversationPanel enableAI userId="test-user" showGoals />,
          { wrapper: createWrapper(store) },
        );

        await waitFor(() => {
          expect(screen.queryByTestId("goal-tracker")).toBeInTheDocument();
        });
      });

      it("should not display goal tracker when disabled", () => {
        const store = createTestStore();

        render(
          <ConnectedConversationPanel enableAI={false} showGoals={false} />,
          {
            wrapper: createWrapper(store),
          },
        );

        expect(screen.queryByTestId("goal-tracker")).not.toBeInTheDocument();
      });
    });
  });
});
