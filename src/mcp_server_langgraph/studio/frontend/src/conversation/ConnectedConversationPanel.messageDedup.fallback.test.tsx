/**
 * ConnectedConversationPanel Message Dedup - Fallback Tests
 *
 * Split from ConnectedConversationPanel.messageDedup.test.tsx for OOM prevention.
 *
 * Tests for: Bug 2 (error fallback), async stream failures, auth failures,
 * session-switch lifecycle, authorization failures, Effect 1 (loaderData watcher).
 */
import { describe, it, expect, vi, beforeEach, afterEach } from "vitest";
import { render, screen, waitFor, cleanup, act } from "@testing-library/react";
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
// authenticatedFetch mock is hoisted via vi.mock below

// =============================================================================
// Controllable mock state for useParams (hoisted for vi.mock)
// =============================================================================

const mockState = {
  sessionIdParam: "session-123" as string | undefined,
  navigate: vi.fn(),
  authenticatedFetchImpl: vi.fn() as ReturnType<typeof vi.fn>,
};

// =============================================================================
// Mocks
// =============================================================================

vi.mock("react-router", async () => {
  const actual =
    await vi.importActual<typeof import("react-router")>("react-router");
  return {
    ...actual,
    useParams: vi.fn(() => ({
      sessionId: mockState.sessionIdParam,
    })),
    useNavigate: vi.fn(() => mockState.navigate),
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

// Mock useSessionSync to prevent it from clearing preloaded Redux state
// (see useSessionSync.ts doc: "mock it to prevent interference with preloaded Redux state")
vi.mock("../hooks/useSessionSync", () => ({
  useSessionSync: vi.fn(),
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

// Mock RTK Query hooks used by the component (avoid vi.importActual on heavy barrel)
vi.mock(import("../api"), async (importOriginal) => {
  const actual = await importOriginal();
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
    useSubmitMessageRatingMutation: () => [vi.fn(), { isLoading: false }],
    useSubmitHallucinationReportMutation: () => [vi.fn(), { isLoading: false }],
  };
});

// Mock authenticatedFetch for fallback POST tests
vi.mock("../utils/authenticatedFetch", () => ({
  authenticatedFetch: (...args: unknown[]) =>
    mockState.authenticatedFetchImpl(...args),
}));

// =============================================================================
// Tests
// =============================================================================

describe("ConnectedConversationPanel - User Message Dedup (Fallback)", () => {
  const now = Date.now();

  beforeEach(() => {
    resetMocks();
    mockStreamingChatReturn.startStream = vi.fn();
    global.fetch = mockFetch;
    mockState.sessionIdParam = "session-123";
    mockState.navigate = vi.fn();
    // Default: authenticatedFetch returns success with server ID
    mockState.authenticatedFetchImpl = vi.fn().mockResolvedValue(
      new Response(JSON.stringify({ message_id: "srv-default" }), {
        status: 200,
        headers: { "Content-Type": "application/json" },
      }),
    );
  });

  afterEach(() => {
    cleanup();
    vi.clearAllMocks();
    vi.restoreAllMocks();
    vi.useRealTimers();
  });

  // Helper to create a store with a session and optional hasPendingMutation
  function storeWithSession(
    opts: {
      messages?: Array<{
        id: string;
        role: string;
        content: string;
        timestamp: number;
        status?: string;
      }>;
      hasPendingMutation?: boolean;
    } = {},
  ) {
    return createTestStore({
      session: {
        currentSession: {
          id: "session-123",
          name: "Test Session",
          messages: opts.messages ?? [],
          config: {},
          createdAt: now,
          updatedAt: now,
        },
        sessions: [],
        isLoading: false,
        error: null,
        hasPendingMutation: opts.hasPendingMutation ?? false,
      },
    });
  }

  // =========================================================================
  // Bug 2: Error fallback path
  // =========================================================================

  describe("Bug 2: Error fallback via direct API call", () => {
    it("test 3: when startStream throws, should NOT dispatch sendMessage thunk", async () => {
      const user = userEvent.setup();
      // Make startStream throw synchronously
      mockStreamingChatReturn.startStream = vi.fn(() => {
        throw new Error("Stream connection failed");
      });

      const store = storeWithSession({
        hasPendingMutation: false,
      });

      const dispatchSpy = vi.spyOn(store, "dispatch");

      render(<ConnectedConversationPanel />, {
        wrapper: createWrapper(store),
      });

      const input = screen.getByRole("textbox");
      await user.type(input, "test message");
      const sendButton = screen.getByRole("button", { name: /send/i });
      await user.click(sendButton);

      await waitFor(() => {
        // Verify sendMessage thunk was NOT dispatched
        const sendMessageCalls = dispatchSpy.mock.calls.filter((call) => {
          const action = call[0] as { type?: string };
          return action?.type?.startsWith("session/sendMessage");
        });
        expect(sendMessageCalls).toHaveLength(0);
      });

      dispatchSpy.mockRestore();
    });

    it("test 4: when both streaming AND direct API call fail, pending should be cleared and updateMessage dispatched with failed", async () => {
      const user = userEvent.setup();
      mockStreamingChatReturn.startStream = vi.fn(() => {
        throw new Error("Stream failed");
      });

      // Mock authenticatedFetch to fail
      mockState.authenticatedFetchImpl.mockRejectedValue(
        new Error("Network error"),
      );

      const store = storeWithSession({
        hasPendingMutation: false,
      });
      const dispatchSpy = vi.spyOn(store, "dispatch");

      render(<ConnectedConversationPanel />, {
        wrapper: createWrapper(store),
      });

      const input = screen.getByRole("textbox");
      await user.type(input, "fail message");
      const sendButton = screen.getByRole("button", { name: /send/i });
      await user.click(sendButton);

      await waitFor(() => {
        expect(mockStreamingChatReturn.startStream).toHaveBeenCalled();
      });

      // Verify updateMessage was dispatched with status: "failed"
      await waitFor(() => {
        const updateCalls = dispatchSpy.mock.calls.filter((call) => {
          const action = call[0] as {
            type?: string;
            payload?: { updates?: { status?: string } };
          };
          return (
            action?.type === "session/updateMessage" &&
            action?.payload?.updates?.status === "failed"
          );
        });
        expect(updateCalls.length).toBeGreaterThanOrEqual(1);
      });

      // And pending mutation should be cleared
      await waitFor(() => {
        expect(store.getState().session.hasPendingMutation).toBe(false);
      });

      dispatchSpy.mockRestore();
    });

    it("test 5: setPendingMutation(false) must be called in all error scenarios", async () => {
      const user = userEvent.setup();
      mockStreamingChatReturn.startStream = vi.fn(() => {
        throw new Error("Stream failed");
      });

      mockState.authenticatedFetchImpl.mockRejectedValue(
        new Error("Network error"),
      );

      const store = storeWithSession({
        hasPendingMutation: false,
      });

      render(<ConnectedConversationPanel />, {
        wrapper: createWrapper(store),
      });

      const input = screen.getByRole("textbox");
      await user.type(input, "error message");
      const sendButton = screen.getByRole("button", { name: /send/i });
      await user.click(sendButton);

      await waitFor(() => {
        const state = store.getState();
        expect(state.session.hasPendingMutation).toBe(false);
      });
    });

    it("test 6: when direct API call succeeds, optimistic message ID should be updated to server UUID", async () => {
      const user = userEvent.setup();
      mockStreamingChatReturn.startStream = vi.fn(() => {
        throw new Error("Stream failed");
      });

      mockState.authenticatedFetchImpl.mockResolvedValue(
        new Response(JSON.stringify({ message_id: "server-uuid-123" }), {
          status: 200,
          headers: { "Content-Type": "application/json" },
        }),
      );

      const store = storeWithSession({
        hasPendingMutation: false,
      });
      const dispatchSpy = vi.spyOn(store, "dispatch");

      render(<ConnectedConversationPanel />, {
        wrapper: createWrapper(store),
      });

      const input = screen.getByRole("textbox");
      await user.type(input, "fallback message");
      const sendButton = screen.getByRole("button", { name: /send/i });
      await user.click(sendButton);

      // Verify updateMessage was dispatched with the server UUID
      await waitFor(() => {
        const updateCalls = dispatchSpy.mock.calls.filter((call) => {
          const action = call[0] as {
            type?: string;
            payload?: { updates?: { id?: string } };
          };
          return (
            action?.type === "session/updateMessage" &&
            action?.payload?.updates?.id === "server-uuid-123"
          );
        });
        expect(updateCalls.length).toBeGreaterThanOrEqual(1);
      });

      dispatchSpy.mockRestore();
    });

    it("test 7: when POST succeeds, message should NOT be marked failed even if revalidation is slow", async () => {
      const user = userEvent.setup();
      mockStreamingChatReturn.startStream = vi.fn(() => {
        throw new Error("Stream failed");
      });

      // Slow revalidation
      mockRevalidateMessages.mockImplementation(
        () => new Promise((resolve) => setTimeout(resolve, 2000)),
      );

      mockState.authenticatedFetchImpl.mockResolvedValue(
        new Response(JSON.stringify({ message_id: "srv-1" }), {
          status: 200,
          headers: { "Content-Type": "application/json" },
        }),
      );

      const store = storeWithSession({
        hasPendingMutation: false,
      });

      render(<ConnectedConversationPanel />, {
        wrapper: createWrapper(store),
      });

      const input = screen.getByRole("textbox");
      await user.type(input, "slow reval msg");
      const sendButton = screen.getByRole("button", { name: /send/i });
      await user.click(sendButton);

      await waitFor(() => {
        const state = store.getState();
        const messages = state.session.currentSession?.messages ?? [];
        const msg = messages.find((m) => m.content === "slow reval msg");
        // Should be "sent", not "failed"
        expect(msg?.status).not.toBe("failed");
      });
    });

    it("test 8: when effectiveSessionId is undefined, message should be marked failed without POST", async () => {
      const user = userEvent.setup();
      // Make startStream throw AFTER session creation
      mockStreamingChatReturn.startStream = vi.fn(() => {
        throw new Error("Stream failed");
      });

      // No session and no sessionId param
      mockState.sessionIdParam = undefined;

      const store = createTestStore({
        session: {
          currentSession: null,
          sessions: [],
          isLoading: false,
          error: null,
          hasPendingMutation: false,
        },
      });

      // Mock createSession to fail so effectiveSessionId stays undefined
      // The createSession thunk uses fetch internally
      mockFetch.mockRejectedValue(new Error("Session creation failed"));

      render(<ConnectedConversationPanel />, {
        wrapper: createWrapper(store),
      });

      const input = screen.getByRole("textbox");
      await user.type(input, "no session msg");
      const sendButton = screen.getByRole("button", { name: /send/i });
      await user.click(sendButton);

      // Since session creation fails, the entire try block throws
      // and the catch block sees effectiveSessionId as undefined
      await waitFor(() => {
        const state = store.getState();
        // hasPendingMutation should be cleared
        expect(state.session.hasPendingMutation).toBe(false);
      });

      // authenticatedFetch should NOT have been called for message persistence
      expect(mockState.authenticatedFetchImpl).not.toHaveBeenCalledWith(
        expect.stringContaining("/messages"),
        expect.anything(),
      );
    });

    it("test 11: when API responds with flat dict { message_id }, server ID should be extracted", async () => {
      const user = userEvent.setup();
      mockStreamingChatReturn.startStream = vi.fn(() => {
        throw new Error("Stream failed");
      });

      mockState.authenticatedFetchImpl.mockResolvedValue(
        new Response(JSON.stringify({ message_id: "flat-uuid-456" }), {
          status: 200,
          headers: { "Content-Type": "application/json" },
        }),
      );

      const store = storeWithSession({
        hasPendingMutation: false,
      });
      const dispatchSpy = vi.spyOn(store, "dispatch");

      render(<ConnectedConversationPanel />, {
        wrapper: createWrapper(store),
      });

      const input = screen.getByRole("textbox");
      await user.type(input, "flat dict test");
      const sendButton = screen.getByRole("button", { name: /send/i });
      await user.click(sendButton);

      // Verify updateMessage dispatched with flat-dict ID
      await waitFor(() => {
        const updateCalls = dispatchSpy.mock.calls.filter((call) => {
          const action = call[0] as {
            type?: string;
            payload?: { updates?: { id?: string } };
          };
          return (
            action?.type === "session/updateMessage" &&
            action?.payload?.updates?.id === "flat-uuid-456"
          );
        });
        expect(updateCalls.length).toBeGreaterThanOrEqual(1);
      });

      dispatchSpy.mockRestore();
    });
  });

  // =========================================================================
  // Async stream failure tests
  // =========================================================================

  describe("Async stream failures", () => {
    it("test 13: async stream error should dispatch setPendingMutation(false)", async () => {
      const user = userEvent.setup();

      const store = storeWithSession({
        hasPendingMutation: false,
      });

      // Start with streaming active (no error)
      mockStreamingChatReturn.error = null;
      mockStreamingChatReturn.isStreaming = false;

      const { rerender } = render(<ConnectedConversationPanel />, {
        wrapper: createWrapper(store),
      });

      // Send a message to set lastSentMessageIdRef
      const input = screen.getByRole("textbox");
      await user.type(input, "stream test");
      const sendButton = screen.getByRole("button", { name: /send/i });
      await user.click(sendButton);

      await waitFor(() => {
        expect(mockStreamingChatReturn.startStream).toHaveBeenCalled();
      });

      // Now hasPendingMutation should be true
      expect(store.getState().session.hasPendingMutation).toBe(true);

      // Simulate async stream error (after connection was established)
      mockStreamingChatReturn.error = "Connection lost";
      mockStreamingChatReturn.isStreaming = false;

      // Force re-render to trigger the streaming error effect
      await act(async () => {
        rerender(<ConnectedConversationPanel />);
      });

      await waitFor(() => {
        const state = store.getState();
        expect(state.session.hasPendingMutation).toBe(false);
      });
    });

    it("test 22: mid-stream disconnect (tokens received) should NOT mark user message as failed", async () => {
      const store = storeWithSession({
        messages: [
          {
            id: "msg-user-1",
            role: "user",
            content: "question",
            timestamp: now,
          },
        ],
        hasPendingMutation: true,
      });

      // Simulate streaming with content already received
      mockStreamingChatReturn.isStreaming = true;
      mockStreamingChatReturn.streamingContent = "Partial answer...";

      const { rerender } = render(<ConnectedConversationPanel />, {
        wrapper: createWrapper(store),
      });

      // Simulate mid-stream disconnect
      mockStreamingChatReturn.isStreaming = false;
      mockStreamingChatReturn.error = "Connection lost mid-stream";
      mockStreamingChatReturn.streamingContent = "Partial answer...";

      await act(async () => {
        rerender(<ConnectedConversationPanel />);
      });

      await waitFor(() => {
        const state = store.getState();
        const messages = state.session.currentSession?.messages ?? [];
        const userMsg = messages.find((m) => m.id === "msg-user-1");
        // Should NOT be marked failed since backend already persisted
        expect(userMsg?.status).not.toBe("failed");
      });
    });
  });

  // =========================================================================
  // Auth failure tests
  // =========================================================================

  describe("Auth failure in fallback POST", () => {
    it("test 14: 401 response should navigate to /login and mark message failed", async () => {
      const user = userEvent.setup();
      mockStreamingChatReturn.startStream = vi.fn(() => {
        throw new Error("Stream failed");
      });

      // Mock authenticatedFetch to return 401 (non-ok response triggers throw)
      mockState.authenticatedFetchImpl.mockImplementation(
        async (_url: string, options: Record<string, unknown>) => {
          // Call the onAuthFailure callback
          if (options?.onAuthFailure) {
            (options.onAuthFailure as () => void)();
          }
          return new Response("Unauthorized", { status: 401 });
        },
      );

      const store = storeWithSession({
        hasPendingMutation: false,
      });
      const dispatchSpy = vi.spyOn(store, "dispatch");

      render(<ConnectedConversationPanel />, {
        wrapper: createWrapper(store),
      });

      const input = screen.getByRole("textbox");
      await user.type(input, "auth fail msg");
      const sendButton = screen.getByRole("button", { name: /send/i });
      await user.click(sendButton);

      await waitFor(() => {
        expect(mockState.navigate).toHaveBeenCalledWith("/login");
      });

      // Verify updateMessage was dispatched with status: "failed"
      await waitFor(() => {
        const updateCalls = dispatchSpy.mock.calls.filter((call) => {
          const action = call[0] as {
            type?: string;
            payload?: { updates?: { status?: string } };
          };
          return (
            action?.type === "session/updateMessage" &&
            action?.payload?.updates?.status === "failed"
          );
        });
        expect(updateCalls.length).toBeGreaterThanOrEqual(1);
      });

      dispatchSpy.mockRestore();
    });
  });

  // =========================================================================
  // Session-switch lifecycle tests
  // =========================================================================

  describe("Session-switch lifecycle", () => {
    it("test 19: unmount during normal streaming should clear hasPendingMutation", async () => {
      const store = storeWithSession({
        hasPendingMutation: true,
      });

      mockStreamingChatReturn.isStreaming = true;

      const { unmount } = render(<ConnectedConversationPanel />, {
        wrapper: createWrapper(store),
      });

      // Unmount while streaming
      unmount();

      await waitFor(() => {
        const state = store.getState();
        expect(state.session.hasPendingMutation).toBe(false);
      });
    });

    it("test 20: session switch during normal streaming should clear hasPendingMutation", async () => {
      const store = storeWithSession({
        hasPendingMutation: true,
      });

      mockStreamingChatReturn.isStreaming = true;
      mockState.sessionIdParam = "session-123";

      const { rerender } = render(<ConnectedConversationPanel />, {
        wrapper: createWrapper(store),
      });

      // Simulate session switch via route param change
      mockState.sessionIdParam = "session-456";

      await act(async () => {
        rerender(<ConnectedConversationPanel />);
      });

      await waitFor(() => {
        const state = store.getState();
        expect(state.session.hasPendingMutation).toBe(false);
      });
    });

    it("test 27: first-message auto-session-creation (undefined -> newSessionId) should NOT clear hasPendingMutation", async () => {
      const store = storeWithSession({
        hasPendingMutation: true,
      });

      // Start with undefined sessionId (no session yet)
      mockState.sessionIdParam = undefined;

      const { rerender } = render(<ConnectedConversationPanel />, {
        wrapper: createWrapper(store),
      });

      // Simulate auto-session creation: sessionId goes from undefined to defined
      mockState.sessionIdParam = "new-session-id";

      await act(async () => {
        rerender(<ConnectedConversationPanel />);
      });

      // hasPendingMutation should still be true (not cleared by Effect 4)
      const state = store.getState();
      expect(state.session.hasPendingMutation).toBe(true);
    });

    it("test 29: navigate from session to chat index during normal streaming should clear pending", async () => {
      const store = storeWithSession({
        hasPendingMutation: true,
      });

      mockStreamingChatReturn.isStreaming = true;
      mockState.sessionIdParam = "session-123";

      const { rerender } = render(<ConnectedConversationPanel />, {
        wrapper: createWrapper(store),
      });

      // Simulate navigating to chat index (sessionId becomes undefined)
      mockState.sessionIdParam = undefined;

      await act(async () => {
        rerender(<ConnectedConversationPanel />);
      });

      await waitFor(() => {
        const state = store.getState();
        expect(state.session.hasPendingMutation).toBe(false);
      });
    });
  });

  // =========================================================================
  // Authorization failure tests (403/404)
  // =========================================================================

  describe("Authorization failures in fallback POST", () => {
    it("test 24: fallback POST returns 403 should mark message failed and clear pending", async () => {
      const user = userEvent.setup();
      mockStreamingChatReturn.startStream = vi.fn(() => {
        throw new Error("Stream failed");
      });

      mockState.authenticatedFetchImpl.mockResolvedValue(
        new Response("Forbidden", { status: 403 }),
      );

      const store = storeWithSession({
        hasPendingMutation: false,
      });
      const dispatchSpy = vi.spyOn(store, "dispatch");

      render(<ConnectedConversationPanel />, {
        wrapper: createWrapper(store),
      });

      const input = screen.getByRole("textbox");
      await user.type(input, "forbidden msg");
      const sendButton = screen.getByRole("button", { name: /send/i });
      await user.click(sendButton);

      await waitFor(() => {
        const updateCalls = dispatchSpy.mock.calls.filter((call) => {
          const action = call[0] as {
            type?: string;
            payload?: { updates?: { status?: string } };
          };
          return (
            action?.type === "session/updateMessage" &&
            action?.payload?.updates?.status === "failed"
          );
        });
        expect(updateCalls.length).toBeGreaterThanOrEqual(1);
        expect(store.getState().session.hasPendingMutation).toBe(false);
      });

      dispatchSpy.mockRestore();
    });

    it("test 25: fallback POST returns 404 should mark message failed and clear pending", async () => {
      const user = userEvent.setup();
      mockStreamingChatReturn.startStream = vi.fn(() => {
        throw new Error("Stream failed");
      });

      mockState.authenticatedFetchImpl.mockResolvedValue(
        new Response("Not Found", { status: 404 }),
      );

      const store = storeWithSession({
        hasPendingMutation: false,
      });
      const dispatchSpy = vi.spyOn(store, "dispatch");

      render(<ConnectedConversationPanel />, {
        wrapper: createWrapper(store),
      });

      const input = screen.getByRole("textbox");
      await user.type(input, "not found msg");
      const sendButton = screen.getByRole("button", { name: /send/i });
      await user.click(sendButton);

      await waitFor(() => {
        const updateCalls = dispatchSpy.mock.calls.filter((call) => {
          const action = call[0] as {
            type?: string;
            payload?: { updates?: { status?: string } };
          };
          return (
            action?.type === "session/updateMessage" &&
            action?.payload?.updates?.status === "failed"
          );
        });
        expect(updateCalls.length).toBeGreaterThanOrEqual(1);
        expect(store.getState().session.hasPendingMutation).toBe(false);
      });

      dispatchSpy.mockRestore();
    });
  });

  // =========================================================================
  // Pending-clear effect (Effect 1) tests
  // =========================================================================

  describe("Effect 1: pendingFallbackRef loaderData watcher", () => {
    it("test 12: setPendingMutation(false) should NOT be dispatched until loaderData contains the server-persisted message", async () => {
      const user = userEvent.setup();
      mockStreamingChatReturn.startStream = vi.fn(() => {
        throw new Error("Stream failed");
      });

      // Fallback POST returns a server ID
      mockState.authenticatedFetchImpl.mockResolvedValue(
        new Response(JSON.stringify({ message_id: "srv-effect1" }), {
          status: 200,
          headers: { "Content-Type": "application/json" },
        }),
      );

      const store = storeWithSession({
        hasPendingMutation: false,
      });

      const { rerender } = render(<ConnectedConversationPanel />, {
        wrapper: createWrapper(store),
      });

      const input = screen.getByRole("textbox");
      await user.type(input, "effect1 test");
      const sendButton = screen.getByRole("button", { name: /send/i });
      await user.click(sendButton);

      // Wait for fallback POST to succeed and pendingFallbackRef to be set
      await waitFor(() => {
        expect(mockState.authenticatedFetchImpl).toHaveBeenCalled();
      });

      // hasPendingMutation should still be true because loaderData
      // doesn't contain the server message yet
      await waitFor(() => {
        expect(store.getState().session.hasPendingMutation).toBe(true);
      });

      // Now simulate loaderData catching up with the server message
      mockSessionLoaderData.messages = [
        {
          id: "srv-effect1",
          role: "user",
          content: "effect1 test",
          timestamp: now,
        },
      ];

      // Force re-render to trigger Effect 1 (loaderData watcher)
      await act(async () => {
        rerender(<ConnectedConversationPanel />);
      });

      // After loaderData includes srv-effect1, pending should clear
      await waitFor(() => {
        expect(store.getState().session.hasPendingMutation).toBe(false);
      });
    });
  });
});
