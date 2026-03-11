/**
 * ConnectedConversationPanel Router Tests
 *
 * Tests for loader data integration with React Router.
 */
import { describe, it, expect, vi, beforeEach, afterEach } from "vitest";
import { render, screen, cleanup } from "@testing-library/react";
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
vi.mock("../api", async () => {
  const actual = await vi.importActual("../api");
  return {
    ...actual,
    useListConnectionTemplatesQuery: () => ({
      data: { templates: [] },
      isLoading: false,
      error: null,
    }),
    useCreateConnectionMutation: () => [vi.fn(), { isLoading: false }],
    useTestConnectionMutation: () => [vi.fn(), { isLoading: false }],
    useStartOAuth2FlowMutation: () => [vi.fn(), { isLoading: false }],
  };
});
// =============================================================================
// Tests
// =============================================================================

describe("ConnectedConversationPanel - Loader Data Integration", () => {
  beforeEach(() => {
    resetMocks();
    global.fetch = mockFetch;
  });

  afterEach(() => {
    cleanup();
    vi.clearAllMocks();
  });

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
    // hasPendingMutation prevents useSessionSync from overwriting Redux state
    const store = createTestStore({
      session: {
        currentSession: {
          id: "session-123",
          name: "Test Session Title",
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
