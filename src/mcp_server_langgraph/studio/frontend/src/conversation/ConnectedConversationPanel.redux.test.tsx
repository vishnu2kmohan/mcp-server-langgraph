/**
 * ConnectedConversationPanel Redux Tests
 *
 * Tests for Redux integration and optimistic updates.
 */
import { describe, it, expect, vi, beforeEach, afterEach } from "vitest";
import { render, screen, cleanup } from "@testing-library/react";
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

// =============================================================================
// Tests
// =============================================================================

describe("ConnectedConversationPanel - Redux Integration", () => {
  beforeEach(() => {
    resetMocks();
    global.fetch = mockFetch;
  });

  afterEach(() => {
    cleanup();
    vi.clearAllMocks();
  });

  it("should read current session from Redux", () => {
    // hasPendingMutation prevents useSessionSync from overwriting Redux state
    const store = createTestStore({
      session: {
        currentSession: {
          id: "redux-session",
          name: "Redux Session Name",
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

    // Session title comes from Redux currentSession.name
    expect(screen.getByText("Redux Session Name")).toBeInTheDocument();
  });

  it("should display messages from Redux currentSession.messages (optimistic updates)", () => {
    // CRITICAL TEST: User messages are added to Redux via sendMessage thunk
    // The component MUST read from Redux, not just loader data, to show optimistic updates
    // hasPendingMutation prevents useSessionSync from overwriting Redux with stale loader data
    const store = createTestStore({
      session: {
        currentSession: {
          id: "session-123",
          name: "Test Session",
          messages: [
            {
              id: "redux-msg-1",
              role: "user",
              content: "Optimistic user message from Redux",
              timestamp: Date.now(),
            },
          ],
          config: {},
          createdAt: Date.now(),
          updatedAt: Date.now(),
        },
        sessions: [],
        isLoading: false,
        error: null,
        hasPendingMutation: true, // Prevents useSessionSync from overwriting Redux
      },
    });

    // Loader data has NO messages - only Redux has the optimistic message
    mockSessionLoaderData.messages = [];

    render(<ConnectedConversationPanel />, { wrapper: createWrapper(store) });

    // The optimistic message from Redux should be displayed
    expect(
      screen.getByText("Optimistic user message from Redux"),
    ).toBeInTheDocument();
  });

  it("should merge Redux messages with loader messages without duplicates", () => {
    // Simulate scenario where loader has some messages and Redux has additional optimistic ones
    const sharedMessageId = "shared-msg-1";

    const store = createTestStore({
      session: {
        currentSession: {
          id: "session-123",
          name: "Test Session",
          messages: [
            {
              id: sharedMessageId,
              role: "user",
              content: "Shared message content",
              timestamp: 1000,
            },
            {
              id: "redux-only-msg",
              role: "user",
              content: "Optimistic message only in Redux",
              timestamp: 2000,
            },
          ],
          config: {},
          createdAt: Date.now(),
          updatedAt: Date.now(),
        },
        sessions: [],
        isLoading: false,
        error: null,
        hasPendingMutation: true, // Prevents useSessionSync from overwriting Redux
      },
    });

    // Loader has the shared message but not the optimistic one
    mockSessionLoaderData.messages = [
      {
        id: sharedMessageId,
        role: "user" as const,
        content: "Shared message content",
        timestamp: 1000,
      },
    ];

    render(<ConnectedConversationPanel />, { wrapper: createWrapper(store) });

    // Both messages should appear, but shared message only once (deduplication)
    const sharedMessages = screen.getAllByText("Shared message content");
    expect(sharedMessages).toHaveLength(1); // No duplicate

    // Optimistic message should also appear
    expect(
      screen.getByText("Optimistic message only in Redux"),
    ).toBeInTheDocument();
  });
});
