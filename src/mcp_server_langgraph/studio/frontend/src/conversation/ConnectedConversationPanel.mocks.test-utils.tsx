/**
 * ConnectedConversationPanel Mocks
 *
 * Shared mocks for ConnectedConversationPanel tests.
 * Split from ConnectedConversationPanel.test.tsx for maintainability.
 */
import { vi } from "vitest";
import type { ChatLoaderData } from "../router/loaders";

// =============================================================================
// Mock Data
// =============================================================================

// Mock session loader data - shared state that tests can modify
export const mockSessionLoaderData: ChatLoaderData = {
  sessionId: "session-123",
  messages: [],
  artifacts: [],
};

// Mock revalidate function
export const mockRevalidate = vi.fn();

// Mock revalidate messages function
export const mockRevalidateMessages = vi.fn();

// Mock useSessionAutoName hook
export const mockUseSessionAutoName = vi.fn();

// Mock streaming chat return state
export const mockStreamingChatReturn = {
  isStreaming: false,
  streamingContent: "",
  error: null as string | null,
  thinkingContent: "" as string,
  usage: null,
  thinkingTokens: null as number | null,
  sources: [] as Array<{ title: string; url: string; snippet?: string }>,
  startStream: vi.fn(),
  stopStream: vi.fn(),
  clearContent: vi.fn(),
  model: "gemini-2.5-flash",
};

// Mock fetch for API calls
export const mockFetch = vi.fn();

// =============================================================================
// Reset Functions
// =============================================================================

/**
 * Reset all mocks to initial state. Call in beforeEach.
 */
export const resetMocks = () => {
  vi.clearAllMocks();

  // Reset loader data
  mockSessionLoaderData.sessionId = "session-123";
  mockSessionLoaderData.messages = [];
  mockSessionLoaderData.artifacts = [];
  mockSessionLoaderData.session = undefined;

  // Reset streaming chat mock state
  mockStreamingChatReturn.isStreaming = false;
  mockStreamingChatReturn.streamingContent = "";
  mockStreamingChatReturn.error = null;
  mockStreamingChatReturn.thinkingContent = "";
  mockStreamingChatReturn.thinkingTokens = null;
  mockStreamingChatReturn.sources = [];

  // Setup fetch mock for API calls
  global.fetch = mockFetch;
  mockFetch.mockResolvedValue({
    ok: true,
    json: async () => ({
      message: { id: "msg-1", role: "user", content: "Test" },
    }),
  });
};

// =============================================================================
// Mock Definitions (to be used with vi.mock)
// =============================================================================

/**
 * React Router mock factory.
 * Usage: vi.mock("react-router", reactRouterMockFactory);
 */
export const reactRouterMockFactory = async () => {
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
};

/**
 * Message revalidation mock.
 */
export const messageRevalidationMock = () => ({
  useMessageRevalidation: () => ({
    revalidateMessages: mockRevalidateMessages,
  }),
});

/**
 * Session auto-name mock.
 */
export const sessionAutoNameMock = () => ({
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
});

/**
 * Streaming chat mock.
 */
export const streamingChatMock = () => ({
  useStreamingChat: () => mockStreamingChatReturn,
});

/**
 * Conversation intelligence hooks mock.
 */
export const conversationIntelligenceMock = () => ({
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
});

/**
 * KB Status hook mock.
 */
export const kbStatusMock = () => ({
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
});
