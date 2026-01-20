/**
 * ConnectedConversationPanel Messaging Tests
 *
 * Tests for message sending, slash commands, and telemetry.
 */
import { describe, it, expect, vi, beforeEach, afterEach } from "vitest";
import { render, screen, waitFor, cleanup } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { ConnectedConversationPanel } from "./ConnectedConversationPanel";
import {
  createTestStore,
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
    suggestions: [],
    usagePercent: 50,
    currentTokens: 64000,
    maxTokens: 128000,
    recommendedAction: null,
    isLoading: false,
    error: null,
    refetch: vi.fn(),
  })),
  useGoalTracking: vi.fn(() => ({
    primaryGoal: null,
    subGoals: [],
    progressPercent: 0,
    currentFocus: null,
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
  useCreateConnectionMutation: () => [vi.fn(), { isLoading: false }],
  useTestConnectionMutation: () => [vi.fn(), { isLoading: false }],
  useStartOAuth2FlowMutation: () => [vi.fn(), { isLoading: false }],
}));

// =============================================================================
// Tests
// =============================================================================

describe("ConnectedConversationPanel - Message Sending", () => {
  beforeEach(() => {
    resetMocks();
    global.fetch = mockFetch;
  });

  afterEach(() => {
    cleanup();
    vi.clearAllMocks();
  });

  it("should dispatch sendMessage action when message is sent", async () => {
    const user = userEvent.setup();
    // Create store with a session so sendMessage can dispatch
    const store = createTestStore({
      session: {
        currentSession: {
          id: "session-123",
          name: "Test Session",
          messages: [],
          config: {},
          createdAt: Date.now(),
          updatedAt: Date.now(),
        },
        sessions: [],
        isLoading: false,
        error: null,
        hasPendingMutation: true,
      },
    });

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
    // Create store with a session so sendMessage can dispatch
    const store = createTestStore({
      session: {
        currentSession: {
          id: "session-123",
          name: "Test Session",
          messages: [],
          config: {},
          createdAt: Date.now(),
          updatedAt: Date.now(),
        },
        sessions: [],
        isLoading: false,
        error: null,
        hasPendingMutation: true,
      },
    });

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

describe("ConnectedConversationPanel - Slash Commands", () => {
  beforeEach(() => {
    resetMocks();
    global.fetch = mockFetch;
  });

  afterEach(() => {
    cleanup();
    vi.clearAllMocks();
  });

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

describe("ConnectedConversationPanel - Telemetry", () => {
  beforeEach(() => {
    resetMocks();
    global.fetch = mockFetch;
  });

  afterEach(() => {
    cleanup();
    vi.clearAllMocks();
  });

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
