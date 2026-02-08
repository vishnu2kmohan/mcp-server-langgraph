/**
 * ConnectedConversationPanel handleSendMessage Tests
 *
 * RC1 Fix: Verifies that handleSendMessage does NOT call the sendMessage thunk
 * (which persists via API POST), since the streaming endpoint already handles
 * user message persistence with dedup logic. This eliminates the dual
 * persistence race condition.
 *
 * The component should:
 * - Add optimistic user message to Redux (addUserMessage)
 * - Call startStream with session ID and content (fire-and-forget)
 * - Call revalidateMessages after stream starts
 * - NOT call sendMessage thunk (removed to fix race condition)
 * - Stream errors handled internally by useStreamingChat via state updates
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
// Mocks (must match pattern from other test files)
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

vi.mock("../api", async () => {
  const actual = await vi.importActual<typeof import("../api")>("../api");
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

describe("ConnectedConversationPanel - handleSendMessage (RC1 Fix)", () => {
  beforeEach(() => {
    resetMocks();
    // Reset startStream to fresh vi.fn() — vi.clearAllMocks doesn't remove mockImplementation
    mockStreamingChatReturn.startStream = vi.fn();
    global.fetch = mockFetch;
  });

  afterEach(() => {
    cleanup();
    vi.clearAllMocks();
  });

  it("should NOT call sendMessage thunk API when sending a message", async () => {
    const user = userEvent.setup();
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
    await user.type(input, "Test message");
    const sendButton = screen.getByRole("button", { name: /send/i });
    await user.click(sendButton);

    // Wait for the message handling to complete
    await waitFor(() => {
      expect(mockStreamingChatReturn.startStream).toHaveBeenCalled();
    });

    // The sendMessage thunk makes a POST to /api/v1/sessions/{id}/messages
    // After RC1 fix, this API call should NOT happen
    const messagePostCalls = mockFetch.mock.calls.filter(
      (call: unknown[]) =>
        typeof call[0] === "string" &&
        call[0].includes("/messages") &&
        (call[1] as RequestInit)?.method === "POST",
    );
    expect(messagePostCalls).toHaveLength(0);
  });

  it("should still add optimistic user message to Redux", async () => {
    const user = userEvent.setup();
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

    // Spy on store dispatch to verify addUserMessage is called
    const dispatchSpy = vi.spyOn(store, "dispatch");

    render(<ConnectedConversationPanel />, { wrapper: createWrapper(store) });

    const input = screen.getByRole("textbox");
    await user.type(input, "Optimistic message");
    const sendButton = screen.getByRole("button", { name: /send/i });
    await user.click(sendButton);

    // Verify addUserMessage action was dispatched with user role and correct content
    await waitFor(() => {
      const addUserMessageCalls = dispatchSpy.mock.calls.filter((call) => {
        const action = call[0] as {
          type?: string;
          payload?: { role?: string; content?: string };
        };
        return (
          action?.type === "session/addUserMessage" &&
          action?.payload?.role === "user" &&
          action?.payload?.content === "Optimistic message"
        );
      });
      expect(addUserMessageCalls.length).toBeGreaterThanOrEqual(1);
    });

    dispatchSpy.mockRestore();
  });

  it("should call startStream with session ID and content", async () => {
    const user = userEvent.setup();
    const store = createTestStore({
      session: {
        currentSession: {
          id: "session-456",
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

    // Override loader data to match the session
    mockSessionLoaderData.sessionId = "session-456";

    render(<ConnectedConversationPanel />, { wrapper: createWrapper(store) });

    const input = screen.getByRole("textbox");
    await user.type(input, "Stream this");
    const sendButton = screen.getByRole("button", { name: /send/i });
    await user.click(sendButton);

    await waitFor(() => {
      expect(mockStreamingChatReturn.startStream).toHaveBeenCalledWith(
        "session-456",
        "Stream this",
        expect.objectContaining({}),
      );
    });
  });

  it("should call sendMessage as fallback when startStream throws synchronously (Finding 3)", async () => {
    // Finding 3 fix: If startStream throws before the streaming endpoint can
    // persist the message, sendMessage thunk is used as a fallback.
    const user = userEvent.setup();
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

    // Simulate startStream throwing synchronously
    mockStreamingChatReturn.startStream.mockImplementation(() => {
      throw new Error("Sync error in startStream");
    });

    render(<ConnectedConversationPanel />, { wrapper: createWrapper(store) });

    const input = screen.getByRole("textbox");
    await user.type(input, "Error message");
    const sendButton = screen.getByRole("button", { name: /send/i });
    await user.click(sendButton);

    // Finding 3 fix: sendMessage thunk SHOULD be called as fallback
    await waitFor(() => {
      const messagePostCalls = mockFetch.mock.calls.filter(
        (call: unknown[]) =>
          typeof call[0] === "string" &&
          call[0].includes("/messages") &&
          (call[1] as RequestInit)?.method === "POST",
      );
      expect(messagePostCalls.length).toBeGreaterThanOrEqual(1);
    });
  });

  it("should preserve optimistic message in Redux regardless of stream outcome", async () => {
    const user = userEvent.setup();
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

    const dispatchSpy = vi.spyOn(store, "dispatch");

    render(<ConnectedConversationPanel />, { wrapper: createWrapper(store) });

    const input = screen.getByRole("textbox");
    await user.type(input, "Preserved message");
    const sendButton = screen.getByRole("button", { name: /send/i });
    await user.click(sendButton);

    // Verify addUserMessage was dispatched exactly once (no duplicate from sendMessage thunk)
    await waitFor(() => {
      const addUserMessageCalls = dispatchSpy.mock.calls.filter((call) => {
        const action = call[0] as {
          type?: string;
          payload?: { content?: string };
        };
        return (
          action?.type === "session/addUserMessage" &&
          action?.payload?.content === "Preserved message"
        );
      });
      // Exactly one optimistic message — no duplicate from sendMessage fallback
      expect(addUserMessageCalls).toHaveLength(1);
    });

    dispatchSpy.mockRestore();
  });

  it("should NOT clear setPendingMutation synchronously after startStream (Finding 4)", async () => {
    // Finding 4 fix: setPendingMutation(false) must NOT be called immediately
    // after startStream, because startStream is fire-and-forget. The flag
    // should be cleared when isStreaming transitions from true to false.
    const user = userEvent.setup();
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
        hasPendingMutation: false,
      },
    });

    const dispatchSpy = vi.spyOn(store, "dispatch");

    render(<ConnectedConversationPanel />, { wrapper: createWrapper(store) });

    const input = screen.getByRole("textbox");
    await user.type(input, "Test pending mutation");
    const sendButton = screen.getByRole("button", { name: /send/i });
    await user.click(sendButton);

    await waitFor(() => {
      expect(mockStreamingChatReturn.startStream).toHaveBeenCalled();
    });

    // After startStream is called, setPendingMutation(true) should be set
    // but setPendingMutation(false) should NOT be dispatched synchronously
    const pendingMutationCalls = dispatchSpy.mock.calls.filter((call) => {
      const action = call[0] as { type?: string; payload?: boolean };
      return action?.type === "session/setPendingMutation";
    });

    // Should have setPendingMutation(true) but NOT setPendingMutation(false) yet
    const trueCallCount = pendingMutationCalls.filter(
      (call) => (call[0] as { payload?: boolean })?.payload === true,
    ).length;
    const falseCallCount = pendingMutationCalls.filter(
      (call) => (call[0] as { payload?: boolean })?.payload === false,
    ).length;

    expect(trueCallCount).toBeGreaterThanOrEqual(1);
    // In the happy path (no error), setPendingMutation(false) should not be
    // called synchronously — it's driven by the isStreaming useEffect
    expect(falseCallCount).toBe(0);

    dispatchSpy.mockRestore();
  });

  it("should call revalidateMessages after startStream", async () => {
    const user = userEvent.setup();
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
    await user.type(input, "Test revalidation{Enter}");

    await waitFor(() => {
      expect(mockRevalidateMessages).toHaveBeenCalled();
    });
  });
});
