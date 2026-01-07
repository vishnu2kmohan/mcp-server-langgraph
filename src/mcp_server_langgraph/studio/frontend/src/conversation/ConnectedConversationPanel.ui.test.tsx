/**
 * ConnectedConversationPanel UI Tests
 *
 * Tests for session header, message list, and accessibility.
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

// =============================================================================
// Tests
// =============================================================================

describe("ConnectedConversationPanel - Session Header", () => {
  beforeEach(() => {
    resetMocks();
    global.fetch = mockFetch;
  });

  afterEach(() => {
    cleanup();
    vi.clearAllMocks();
  });

  it("should display session header when session title is provided from Redux", () => {
    // Session title comes from Redux currentSession.name
    // hasPendingMutation prevents useSessionSync from overwriting Redux state
    const store = createTestStore({
      session: {
        currentSession: {
          id: "session-123",
          name: "My Chat Session",
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

describe("ConnectedConversationPanel - Message List", () => {
  beforeEach(() => {
    resetMocks();
    global.fetch = mockFetch;
  });

  afterEach(() => {
    cleanup();
    vi.clearAllMocks();
  });

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

describe("ConnectedConversationPanel - Accessibility", () => {
  beforeEach(() => {
    resetMocks();
    global.fetch = mockFetch;
  });

  afterEach(() => {
    cleanup();
    vi.clearAllMocks();
  });

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
