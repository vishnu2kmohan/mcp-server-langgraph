/**
 * ConnectedConversationPanel Message Dedup - Effects Tests
 *
 * Split from ConnectedConversationPanel.messageDedup.test.tsx for OOM prevention.
 *
 * Tests for: Effect 2 (session-switch), Effect 3 (unmount), rapid overlapping
 * fallbacks, fail-safe timeout, concurrency guard, overlapping failure,
 * split-brain state, null-serverId timeout, connection-phase error.
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
import * as sessionSlice from "../store/slices/sessionSlice";
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

describe("ConnectedConversationPanel - User Message Dedup (Effects)", () => {
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
  // Session-switch during pending fallback tests (Effect 2)
  // =========================================================================

  describe("Effect 2: session-switch during pending fallback", () => {
    it("test 15: session switch during pending fallback should reset pendingFallbackRef and clear pending", async () => {
      const user = userEvent.setup();
      mockStreamingChatReturn.startStream = vi.fn(() => {
        throw new Error("Stream failed");
      });

      mockState.authenticatedFetchImpl.mockResolvedValue(
        new Response(JSON.stringify({ message_id: "srv-15" }), {
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
      await user.type(input, "session switch msg");
      const sendButton = screen.getByRole("button", { name: /send/i });
      await user.click(sendButton);

      // Wait for fallback to set pendingFallbackRef
      await waitFor(() => {
        expect(mockState.authenticatedFetchImpl).toHaveBeenCalled();
      });

      // Pending should be true (waiting for loaderData catch-up)
      await waitFor(() => {
        expect(store.getState().session.hasPendingMutation).toBe(true);
      });

      // Simulate session switch via route param change
      mockState.sessionIdParam = "session-456";

      await act(async () => {
        rerender(<ConnectedConversationPanel />);
      });

      // Effect 2 should detect the session change and clear pending
      await waitFor(() => {
        expect(store.getState().session.hasPendingMutation).toBe(false);
      });
    });

    it("test 16: Effect 2 early return — sessionId transition (undefined -> defined) with null pendingFallbackRef should be a no-op", async () => {
      // Structural test: Effect 2 checks `if (!pendingFallbackRef.current) return;`
      // first. When no message has been sent (pendingFallbackRef is null), the
      // session ID transition from undefined to defined must not trigger any
      // hasPendingMutation dispatch.
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

      const { rerender } = render(<ConnectedConversationPanel />, {
        wrapper: createWrapper(store),
      });

      // Simulate sessionId transition: undefined -> defined
      mockState.sessionIdParam = "new-session-created";

      await act(async () => {
        rerender(<ConnectedConversationPanel />);
      });

      // Effect 2's early return prevents any action — hasPendingMutation stays false
      expect(store.getState().session.hasPendingMutation).toBe(false);
    });

    it("test 17: timer-based fallback (null serverId) + session switch should clear pending", async () => {
      const user = userEvent.setup();
      vi.useFakeTimers({ shouldAdvanceTime: true });

      mockStreamingChatReturn.startStream = vi.fn(() => {
        throw new Error("Stream failed");
      });

      // Return response with no extractable serverId
      mockState.authenticatedFetchImpl.mockResolvedValue(
        new Response(JSON.stringify({ unexpected_field: "no-id" }), {
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
      await user.type(input, "timer fallback msg");
      const sendButton = screen.getByRole("button", { name: /send/i });
      await user.click(sendButton);

      await waitFor(() => {
        expect(mockState.authenticatedFetchImpl).toHaveBeenCalled();
      });

      // pending should be true (pendingFallbackRef has serverId: null)
      await waitFor(() => {
        expect(store.getState().session.hasPendingMutation).toBe(true);
      });

      // Simulate session switch before timeout fires
      mockState.sessionIdParam = "session-789";

      await act(async () => {
        rerender(<ConnectedConversationPanel />);
      });

      // Effect 2 should clear pending on session switch
      await waitFor(() => {
        expect(store.getState().session.hasPendingMutation).toBe(false);
      });

      vi.useRealTimers();
    });
  });

  // =========================================================================
  // Unmount during active fallback (Effect 3)
  // =========================================================================

  describe("Effect 3: unmount during active fallback", () => {
    it("test 18: component unmount during active fallback should call clearFallbackState", async () => {
      const user = userEvent.setup();
      mockStreamingChatReturn.startStream = vi.fn(() => {
        throw new Error("Stream failed");
      });

      mockState.authenticatedFetchImpl.mockResolvedValue(
        new Response(JSON.stringify({ message_id: "srv-18" }), {
          status: 200,
          headers: { "Content-Type": "application/json" },
        }),
      );

      const store = storeWithSession({
        hasPendingMutation: false,
      });

      const { unmount } = render(<ConnectedConversationPanel />, {
        wrapper: createWrapper(store),
      });

      const input = screen.getByRole("textbox");
      await user.type(input, "unmount fallback msg");
      const sendButton = screen.getByRole("button", { name: /send/i });
      await user.click(sendButton);

      // Wait for fallback POST to succeed
      await waitFor(() => {
        expect(mockState.authenticatedFetchImpl).toHaveBeenCalled();
      });

      // Pending should be true (waiting for loaderData catch-up)
      await waitFor(() => {
        expect(store.getState().session.hasPendingMutation).toBe(true);
      });

      // Unmount while fallback is pending
      unmount();

      // Effect 3 should clear pending on unmount
      await waitFor(() => {
        expect(store.getState().session.hasPendingMutation).toBe(false);
      });
    });
  });

  // =========================================================================
  // Rapid overlapping fallbacks (R13-2)
  // =========================================================================

  describe("Rapid overlapping fallbacks", () => {
    it("test 21: when message A's fallback sets pendingFallbackRef and message B starts, Effect 1 should NOT clear pending when A's serverId arrives", async () => {
      const user = userEvent.setup();

      // Track which message IDs are dispatched
      let callCount = 0;
      mockStreamingChatReturn.startStream = vi.fn(() => {
        throw new Error("Stream failed");
      });

      // First call returns srv-A, second returns srv-B
      mockState.authenticatedFetchImpl
        .mockResolvedValueOnce(
          new Response(JSON.stringify({ message_id: "srv-A" }), {
            status: 200,
            headers: { "Content-Type": "application/json" },
          }),
        )
        .mockResolvedValueOnce(
          new Response(JSON.stringify({ message_id: "srv-B" }), {
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

      // Send message A
      const input = screen.getByRole("textbox");
      await user.type(input, "message A");
      const sendButton = screen.getByRole("button", { name: /send/i });
      await user.click(sendButton);

      await waitFor(() => {
        callCount = mockState.authenticatedFetchImpl.mock.calls.length;
        expect(callCount).toBeGreaterThanOrEqual(1);
      });

      // Send message B (overwrites lastSentMessageIdRef and pendingFallbackRef)
      await user.type(input, "message B");
      await user.click(sendButton);

      await waitFor(() => {
        expect(
          mockState.authenticatedFetchImpl.mock.calls.length,
        ).toBeGreaterThan(callCount);
      });

      // Simulate loaderData containing A's server ID (but B is now the active mutation)
      mockSessionLoaderData.messages = [
        { id: "srv-A", role: "user", content: "message A", timestamp: now },
      ];

      await act(async () => {
        store.dispatch(
          sessionSlice.updateMessage({
            messageId: "force-rerender",
            updates: {},
          }),
        );
      });

      // Pending should still be true because B's fallback is still active
      // (Effect 1 checks clientMessageId !== lastSentMessageIdRef.current)
      await waitFor(() => {
        expect(store.getState().session.hasPendingMutation).toBe(true);
      });
    });
  });

  // =========================================================================
  // Revalidation-never-delivers fail-safe (R13-4)
  // =========================================================================

  describe("Fail-safe timeout", () => {
    it("test 23: when fallback POST succeeds with serverId but loaderData never includes it, pending should be cleared by bounded timeout (10s)", async () => {
      vi.useFakeTimers({ shouldAdvanceTime: true });
      const user = userEvent.setup({ advanceTimers: vi.advanceTimersByTime });

      mockStreamingChatReturn.startStream = vi.fn(() => {
        throw new Error("Stream failed");
      });

      mockState.authenticatedFetchImpl.mockResolvedValue(
        new Response(JSON.stringify({ message_id: "srv-timeout" }), {
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
      await user.type(input, "timeout test");
      const sendButton = screen.getByRole("button", { name: /send/i });
      await user.click(sendButton);

      await waitFor(() => {
        expect(mockState.authenticatedFetchImpl).toHaveBeenCalled();
      });

      // Pending should be true
      await waitFor(() => {
        expect(store.getState().session.hasPendingMutation).toBe(true);
      });

      // loaderData never catches up -- advance past the 10s fail-safe timeout
      await act(async () => {
        vi.advanceTimersByTime(11000);
      });

      // Fail-safe timer should have cleared pending
      await waitFor(() => {
        expect(store.getState().session.hasPendingMutation).toBe(false);
      });

      vi.useRealTimers();
    });
  });

  // =========================================================================
  // Concurrency guard tests (R14-1)
  // =========================================================================

  describe("Concurrency guard for overlapping async fallbacks", () => {
    it("test 26: overlapping async fallbacks -- message A's resolution should NOT mutate pendingFallbackRef if message B has taken over", async () => {
      const user = userEvent.setup();

      mockStreamingChatReturn.startStream = vi.fn(() => {
        throw new Error("Stream failed");
      });

      // Make first call slow so second overtakes
      let resolveFirst: (v: Response) => void;
      const firstPromise = new Promise<Response>((resolve) => {
        resolveFirst = resolve;
      });

      mockState.authenticatedFetchImpl
        .mockReturnValueOnce(firstPromise)
        .mockResolvedValueOnce(
          new Response(JSON.stringify({ message_id: "srv-B-26" }), {
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

      // Send message A (slow fallback)
      const input = screen.getByRole("textbox");
      await user.type(input, "msg A slow");
      const sendButton = screen.getByRole("button", { name: /send/i });
      await user.click(sendButton);

      // Send message B (fast fallback, resolves immediately)
      await user.type(input, "msg B fast");
      await user.click(sendButton);

      // Wait for B's fallback to complete
      await waitFor(() => {
        expect(mockState.authenticatedFetchImpl).toHaveBeenCalledTimes(2);
      });

      // Now resolve A (after B has taken over lastSentMessageIdRef)
      resolveFirst!(
        new Response(JSON.stringify({ message_id: "srv-A-26" }), {
          status: 200,
          headers: { "Content-Type": "application/json" },
        }),
      );

      // A should still dispatch updateMessage (idempotent ID replacement),
      // but should NOT mutate pendingFallbackRef (R16-2: inline check fails
      // because lastSentMessageIdRef !== A's messageId)
      await waitFor(() => {
        // updateMessage for A's server ID should be dispatched
        const updateCalls = dispatchSpy.mock.calls.filter((call) => {
          const action = call[0] as {
            type?: string;
            payload?: { updates?: { id?: string } };
          };
          return (
            action?.type === "session/updateMessage" &&
            action?.payload?.updates?.id === "srv-A-26"
          );
        });
        expect(updateCalls.length).toBeGreaterThanOrEqual(1);
      });

      // Pending should still be true (B's fallback is managing lifecycle)
      expect(store.getState().session.hasPendingMutation).toBe(true);

      dispatchSpy.mockRestore();
    });
  });

  // =========================================================================
  // Overlapping fallback failure concurrency (R15-2)
  // =========================================================================

  describe("Overlapping fallback failure concurrency", () => {
    it("test 28: when message A's fallback fails after message B has started, setPendingMutation(false) should NOT be dispatched", async () => {
      const user = userEvent.setup();

      mockStreamingChatReturn.startStream = vi.fn(() => {
        throw new Error("Stream failed");
      });

      // Make A fail slowly, B succeed immediately
      let rejectFirst: (e: Error) => void;
      const firstPromise = new Promise<Response>((_resolve, reject) => {
        rejectFirst = reject;
      });

      mockState.authenticatedFetchImpl
        .mockReturnValueOnce(firstPromise)
        .mockResolvedValueOnce(
          new Response(JSON.stringify({ message_id: "srv-B-28" }), {
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

      // Send message A (slow failure)
      const input = screen.getByRole("textbox");
      await user.type(input, "msg A fail");
      const sendButton = screen.getByRole("button", { name: /send/i });
      await user.click(sendButton);

      // Send message B (fast success)
      await user.type(input, "msg B ok");
      await user.click(sendButton);

      await waitFor(() => {
        expect(mockState.authenticatedFetchImpl).toHaveBeenCalledTimes(2);
      });

      // Now fail A (after B has taken over lastSentMessageIdRef)
      rejectFirst!(new Error("Network timeout for A"));

      // Wait for A's error to process
      await act(async () => {
        await new Promise((r) => setTimeout(r, 50));
      });

      // Pending should still be true (B's lifecycle manages it, not A)
      // R15-2: the `if (lastSentMessageIdRef.current === messageId)` guard
      // prevents A's failure from clearing B's pending state
      expect(store.getState().session.hasPendingMutation).toBe(true);
    });
  });

  // =========================================================================
  // Effect 2 split-brain state tests (R17-2)
  // =========================================================================

  describe("Effect 2 split-brain state", () => {
    it("test 30: when fallback pending for session A and user navigates to session B, Effect 2 should clear immediately using route param", async () => {
      const user = userEvent.setup();
      mockStreamingChatReturn.startStream = vi.fn(() => {
        throw new Error("Stream failed");
      });

      mockState.authenticatedFetchImpl.mockResolvedValue(
        new Response(JSON.stringify({ message_id: "srv-30" }), {
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

      // Send message to create a fallback with pendingFallbackRef
      const input = screen.getByRole("textbox");
      await user.type(input, "split brain msg");
      const sendButton = screen.getByRole("button", { name: /send/i });
      await user.click(sendButton);

      await waitFor(() => {
        expect(mockState.authenticatedFetchImpl).toHaveBeenCalled();
      });

      await waitFor(() => {
        expect(store.getState().session.hasPendingMutation).toBe(true);
      });

      // Navigate to session B (route param changes, but Redux currentSession
      // may still be stale because useSessionSync is blocked)
      mockState.sessionIdParam = "session-B";

      await act(async () => {
        rerender(<ConnectedConversationPanel />);
      });

      // Effect 2 should clear immediately using route param as primary authority
      await waitFor(() => {
        expect(store.getState().session.hasPendingMutation).toBe(false);
      });
    });

    it("test 31: when fallback pending and user navigates to chat index (sessionId undefined), Effect 2 should clear unconditionally", async () => {
      const user = userEvent.setup();
      mockStreamingChatReturn.startStream = vi.fn(() => {
        throw new Error("Stream failed");
      });

      mockState.authenticatedFetchImpl.mockResolvedValue(
        new Response(JSON.stringify({ message_id: "srv-31" }), {
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
      await user.type(input, "chat index msg");
      const sendButton = screen.getByRole("button", { name: /send/i });
      await user.click(sendButton);

      await waitFor(() => {
        expect(mockState.authenticatedFetchImpl).toHaveBeenCalled();
      });

      await waitFor(() => {
        expect(store.getState().session.hasPendingMutation).toBe(true);
      });

      // Navigate to chat index (sessionId becomes undefined)
      mockState.sessionIdParam = undefined;

      await act(async () => {
        rerender(<ConnectedConversationPanel />);
      });

      // Effect 2 should clear unconditionally when sessionId is undefined
      await waitFor(() => {
        expect(store.getState().session.hasPendingMutation).toBe(false);
      });
    });
  });

  // =========================================================================
  // Null-serverId timeout tests (R17-3)
  // =========================================================================

  describe("Null-serverId timeout", () => {
    it("test 32: null-serverId timeout (5s) should fire and clear pending without any navigation event", async () => {
      vi.useFakeTimers({ shouldAdvanceTime: true });
      const user = userEvent.setup({ advanceTimers: vi.advanceTimersByTime });

      mockStreamingChatReturn.startStream = vi.fn(() => {
        throw new Error("Stream failed");
      });

      // Return response with no extractable serverId
      mockState.authenticatedFetchImpl.mockResolvedValue(
        new Response(JSON.stringify({ unexpected: "no-id-field" }), {
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
      await user.type(input, "null serverid msg");
      const sendButton = screen.getByRole("button", { name: /send/i });
      await user.click(sendButton);

      await waitFor(() => {
        expect(mockState.authenticatedFetchImpl).toHaveBeenCalled();
      });

      // Pending should be true (serverId is null, waiting for timeout)
      await waitFor(() => {
        expect(store.getState().session.hasPendingMutation).toBe(true);
      });

      // No session switch -- just let the 5s timeout fire
      await act(async () => {
        vi.advanceTimersByTime(6000);
      });

      // Timeout should have cleared pending
      await waitFor(() => {
        expect(store.getState().session.hasPendingMutation).toBe(false);
      });

      vi.useRealTimers();
    });
  });

  // =========================================================================
  // Connection-phase error after stale revalidation (R17-1)
  // =========================================================================

  describe("Connection-phase error with stale content", () => {
    it("test 33: connection-phase error should still mark message as failed even when previous stream left lastStreamedContent populated", async () => {
      const user = userEvent.setup();

      // startStream succeeds initially (doesn't throw), but streaming
      // will report an error asynchronously via the error field
      mockStreamingChatReturn.startStream = vi.fn();
      mockStreamingChatReturn.error = null;
      mockStreamingChatReturn.streamingContent = "";
      mockStreamingChatReturn.isStreaming = false;

      const store = storeWithSession({
        messages: [
          {
            id: "msg-prev",
            role: "user",
            content: "previous",
            timestamp: now - 10000,
          },
        ],
        hasPendingMutation: false,
      });

      const { rerender } = render(<ConnectedConversationPanel />, {
        wrapper: createWrapper(store),
      });

      // Send a message via UI to set lastSentMessageIdRef
      const input = screen.getByRole("textbox");
      await user.type(input, "new message 33");
      const sendButton = screen.getByRole("button", { name: /send/i });
      await user.click(sendButton);

      // Wait for startStream to be called
      await waitFor(() => {
        expect(mockStreamingChatReturn.startStream).toHaveBeenCalled();
      });

      // hasPendingMutation should be true, lastSentMessageIdRef is set
      expect(store.getState().session.hasPendingMutation).toBe(true);

      // Simulate connection-phase error (no streaming content received at all).
      // The key: streamingContent is "" AND lastStreamedContentRef is "" (reset
      // by streaming completion effect), so isConnectionPhaseError = true.
      // Even if the state variable lastStreamedContent is populated from a
      // previous stream, the ref (which the effect uses) is correctly "".
      mockStreamingChatReturn.error = "Connection refused";
      mockStreamingChatReturn.streamingContent = "";

      // Force re-render to trigger the streaming error effect
      await act(async () => {
        rerender(<ConnectedConversationPanel />);
      });

      // The streaming error effect should clear pending
      await waitFor(() => {
        expect(store.getState().session.hasPendingMutation).toBe(false);
      });
    });
  });
});
