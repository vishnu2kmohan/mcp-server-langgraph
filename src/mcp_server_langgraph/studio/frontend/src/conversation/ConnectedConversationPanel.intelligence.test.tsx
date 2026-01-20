/**
 * ConnectedConversationPanel Intelligence Tests
 *
 * Tests for conversation intelligence features (Sprint 3):
 * - Intent detection
 * - Context optimization
 * - Goal tracking
 * - Session auto-naming
 */
import { describe, it, expect, vi, beforeEach, afterEach } from "vitest";
import { render, screen, waitFor, cleanup } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { ConnectedConversationPanel } from "./ConnectedConversationPanel";
import {
  createTestStore,
  createMockMessage,
  createWrapper,
} from "./ConnectedConversationPanel.fixtures";
import {
  mockSessionLoaderData,
  mockRevalidate,
  mockRevalidateMessages,
  mockUseSessionAutoName,
  mockStreamingChatReturn,
  mockFetch,
  resetMocks,
} from "./ConnectedConversationPanel.mocks.test-utils";

// =============================================================================
// Mocks
// =============================================================================

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
    useRevalidator: vi.fn(() => ({
      revalidate: mockRevalidate,
      state: "idle",
    })),
  };
});

vi.mock("../hooks/useMessageRevalidation", () => ({
  useMessageRevalidation: () => ({
    revalidateMessages: mockRevalidateMessages,
  }),
}));

vi.mock("../hooks/useSessionAutoName", () => ({
  useSessionAutoName: (options: unknown) => {
    mockUseSessionAutoName(options);
    return {
      isGenerating: false,
      isSuccess: false,
      generatedTitle: undefined,
      hasDefaultName: true,
      error: undefined,
    };
  },
  default: (options: unknown) => {
    mockUseSessionAutoName(options);
    return {
      isGenerating: false,
      isSuccess: false,
      generatedTitle: undefined,
      hasDefaultName: true,
      error: undefined,
    };
  },
}));

vi.mock("../hooks/useStreamingChat", () => ({
  useStreamingChat: () => mockStreamingChatReturn,
}));

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

vi.mock("../hooks/useKBStatus", () => ({
  useKBStatus: () => ({
    data: undefined,
    status: "ready" as const,
    statusMessage: "Knowledge Base ready",
    isLoading: false,
    isError: false,
    error: null,
    isReady: true,
    isMisconfigured: false,
    isUnavailable: false,
    collectionName: "test-collection",
    vectorsCount: 100,
    contextStats: undefined,
    kbStatusForUI: "ready" as const,
    refetch: vi.fn(),
  }),
}));

vi.mock("../hooks/useAvailableTools", () => ({
  useAvailableTools: () => ({
    tools: [],
    isLoading: false,
    error: null,
    refetch: vi.fn(),
  }),
}));

vi.mock("../hooks/useAISuggestionsWebSocket", () => ({
  useAISuggestionsWebSocket: () => ({
    isConnected: false,
    suggestions: [],
    contextStats: null,
    error: null,
  }),
}));

vi.mock("../hooks/useConnectorSuggestions", () => ({
  useConnectorSuggestions: () => ({
    suggestions: [],
    visible: false,
    dismiss: vi.fn(),
    isLoading: false,
    inputValue: "",
    setInputValue: vi.fn(),
    enabled: false,
  }),
}));

// Mock RTK Query hooks for InlineConnectionCard
vi.mock("../api", () => ({
  useListConnectionTemplatesQuery: () => ({
    data: { templates: [] },
    isLoading: false,
    error: null,
  }),
  useCreateConnectionMutation: () => [
    vi.fn(),
    { isLoading: false },
  ],
  useTestConnectionMutation: () => [
    vi.fn(),
    { isLoading: false },
  ],
  useStartOAuth2FlowMutation: () => [
    vi.fn(),
    { isLoading: false },
  ],
}));

// =============================================================================
// Tests
// =============================================================================

describe("ConnectedConversationPanel - Conversation Intelligence (Sprint 3)", () => {
  beforeEach(() => {
    resetMocks();
    global.fetch = mockFetch;
  });

  afterEach(() => {
    cleanup();
    vi.clearAllMocks();
  });

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

      expect(screen.queryByTestId("intent-indicator")).not.toBeInTheDocument();
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
      expect(screen.queryByTestId("intent-indicator")).not.toBeInTheDocument();
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

describe("ConnectedConversationPanel - Session Auto-Naming", () => {
  beforeEach(() => {
    resetMocks();
    global.fetch = mockFetch;
  });

  afterEach(() => {
    cleanup();
    vi.clearAllMocks();
  });

  it("should call useSessionAutoName hook with session and message data", () => {
    const store = createTestStore({
      session: {
        currentSession: {
          id: "session-123",
          name: "New Chat",
          messages: [{ id: "msg-1", role: "user", content: "Hello world" }],
          config: {},
          createdAt: Date.now(),
          updatedAt: Date.now(),
        },
        sessions: [],
        loading: false,
        error: null,
        hasPendingMutation: true,
      },
    });

    mockSessionLoaderData.sessionId = "session-123";
    mockSessionLoaderData.messages = [
      createMockMessage({ id: "msg-1", content: "Hello world" }),
    ];

    render(<ConnectedConversationPanel />, { wrapper: createWrapper(store) });

    // The hook should be called with session info
    expect(mockUseSessionAutoName).toHaveBeenCalled();
    const callArgs = mockUseSessionAutoName.mock.calls[0][0];
    expect(callArgs).toHaveProperty("sessionId");
    expect(callArgs).toHaveProperty("messages");
    expect(callArgs).toHaveProperty("currentName");
  });

  it("should pass current session name to auto-naming hook", () => {
    const store = createTestStore({
      session: {
        currentSession: {
          id: "session-456",
          name: "My Custom Chat",
          messages: [],
          config: {},
          createdAt: Date.now(),
          updatedAt: Date.now(),
        },
        sessions: [],
        loading: false,
        error: null,
        hasPendingMutation: true,
      },
    });

    mockSessionLoaderData.sessionId = "session-456";
    mockSessionLoaderData.messages = [];

    render(<ConnectedConversationPanel />, { wrapper: createWrapper(store) });

    expect(mockUseSessionAutoName).toHaveBeenCalled();
    const callArgs = mockUseSessionAutoName.mock.calls[0][0];
    expect(callArgs.currentName).toBe("My Custom Chat");
  });

  it("should pass messages array to auto-naming hook for title generation", () => {
    const store = createTestStore({
      session: {
        currentSession: {
          id: "session-789",
          name: "New Chat",
          messages: [
            {
              id: "msg-1",
              role: "user",
              content: "Help me build a REST API",
            },
            { id: "msg-2", role: "assistant", content: "Sure, I can help!" },
          ],
          config: {},
          createdAt: Date.now(),
          updatedAt: Date.now(),
        },
        sessions: [],
        loading: false,
        error: null,
        hasPendingMutation: true,
      },
    });

    render(<ConnectedConversationPanel />, { wrapper: createWrapper(store) });

    expect(mockUseSessionAutoName).toHaveBeenCalled();
    const callArgs = mockUseSessionAutoName.mock.calls[0][0];
    expect(Array.isArray(callArgs.messages)).toBe(true);
    expect(callArgs.messages.length).toBeGreaterThan(0);
  });
});
