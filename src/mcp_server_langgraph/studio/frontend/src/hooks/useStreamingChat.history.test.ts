/**
 * useStreamingChat History Fallback Tests
 *
 * RC4 Fix: Verifies that useStreamingChat can include bounded conversation
 * history in the streaming request as a defense-in-depth fallback when
 * backend storage fails.
 */

import { describe, it, expect, vi, beforeEach, afterEach } from "vitest";
import { renderHook, act } from "@testing-library/react";
import { useStreamingChat } from "./useStreamingChat";

// Mock useAppDispatch for Redux integration tests
const mockDispatch = vi.fn();
vi.mock("../store/hooks", () => ({
  useAppDispatch: () => mockDispatch,
  useAppSelector: vi.fn(),
}));

// Mock react-router navigate
const mockNavigate = vi.fn();
vi.mock("react-router", () => ({
  useNavigate: () => mockNavigate,
}));

// Mock storage utilities
vi.mock("../utils/storage", () => ({
  getAuthToken: vi.fn(() => "mock-token"),
  setAuthTokens: vi.fn(),
  clearAuthTokens: vi.fn(),
  STORAGE_KEYS: {
    REFRESH_TOKEN: "refresh_token",
  },
}));

// Mock intendedRoute
vi.mock("../utils/intendedRoute", () => ({
  setIntendedRoute: vi.fn(),
}));

// Helper to create a mock ReadableStream that yields SSE chunks
function createMockSSEStream(chunks: string[]): ReadableStream<Uint8Array> {
  const encoder = new TextEncoder();
  let index = 0;

  return new ReadableStream({
    pull(controller) {
      if (index < chunks.length) {
        controller.enqueue(encoder.encode(chunks[index]));
        index++;
      } else {
        controller.close();
      }
    },
  });
}

// Helper to create a mock Response with SSE stream
function createMockSSEResponse(chunks: string[], status = 200): Response {
  const stream = createMockSSEStream(chunks);
  return new Response(stream, {
    status,
    headers: { "Content-Type": "text/event-stream" },
  });
}

describe("useStreamingChat - History Fallback (RC4 Fix)", () => {
  let mockFetch: ReturnType<typeof vi.fn>;

  beforeEach(() => {
    vi.clearAllMocks();
    mockFetch = vi.fn();
    vi.stubGlobal("fetch", mockFetch);
  });

  afterEach(() => {
    vi.unstubAllGlobals();
  });

  it("should include recent message history in streaming request when history provided", async () => {
    mockFetch.mockResolvedValue(
      createMockSSEResponse([
        'data: {"content":"Response"}\n\n',
        "data: [DONE]\n\n",
      ]),
    );

    const { result } = renderHook(() => useStreamingChat());

    const history = [
      { id: "msg-1", role: "user", content: "First message" },
      { id: "msg-2", role: "assistant", content: "First response" },
    ];

    await act(async () => {
      result.current.startStream("session-123", "Second message", {
        history,
      });
      await vi.waitFor(() => expect(mockFetch).toHaveBeenCalled());
    });

    // Verify the body includes history + current message
    const callArgs = mockFetch.mock.calls[0];
    const body = JSON.parse(callArgs[1].body);

    // Messages should include history followed by current message
    expect(body.messages).toHaveLength(3);
    expect(body.messages[0]).toEqual({
      id: "msg-1",
      role: "user",
      content: "First message",
    });
    expect(body.messages[1]).toEqual({
      id: "msg-2",
      role: "assistant",
      content: "First response",
    });
    expect(body.messages[2]).toEqual(
      expect.objectContaining({
        role: "user",
        content: "Second message",
      }),
    );

    // Should flag as client-supplied history
    expect(body.client_history_fallback).toBe(true);
  });

  it("should cap history to MAX_CLIENT_HISTORY_MESSAGES most recent messages", async () => {
    mockFetch.mockResolvedValue(
      createMockSSEResponse([
        'data: {"content":"Response"}\n\n',
        "data: [DONE]\n\n",
      ]),
    );

    const { result } = renderHook(() => useStreamingChat());

    // Create 60 history messages (exceeds cap of 50)
    const history = Array.from({ length: 60 }, (_, i) => ({
      id: `msg-${i}`,
      role: i % 2 === 0 ? "user" : "assistant",
      content: `Message ${i}`,
    }));

    await act(async () => {
      result.current.startStream("session-123", "Latest message", {
        history,
      });
      await vi.waitFor(() => expect(mockFetch).toHaveBeenCalled());
    });

    const callArgs = mockFetch.mock.calls[0];
    const body = JSON.parse(callArgs[1].body);

    // Should have at most 50 history + 1 current = 51 messages
    expect(body.messages.length).toBeLessThanOrEqual(51);

    // Last message should be the current one
    const lastMsg = body.messages[body.messages.length - 1];
    expect(lastMsg.content).toBe("Latest message");
  });

  it("should fall back to single message when no history provided", async () => {
    mockFetch.mockResolvedValue(
      createMockSSEResponse(['data: {"content":"Hi"}\n\n', "data: [DONE]\n\n"]),
    );

    const { result } = renderHook(() => useStreamingChat());

    await act(async () => {
      result.current.startStream("session-123", "Hello World");
      await vi.waitFor(() => expect(mockFetch).toHaveBeenCalled());
    });

    const callArgs = mockFetch.mock.calls[0];
    const body = JSON.parse(callArgs[1].body);

    // Should have just the single message
    expect(body.messages).toEqual([{ role: "user", content: "Hello World" }]);

    // Should NOT have client_history_fallback flag
    expect(body.client_history_fallback).toBeUndefined();
  });

  it("should include message IDs in history for server-side dedup", async () => {
    mockFetch.mockResolvedValue(
      createMockSSEResponse([
        'data: {"content":"Response"}\n\n',
        "data: [DONE]\n\n",
      ]),
    );

    const { result } = renderHook(() => useStreamingChat());

    const history = [
      { id: "msg-abc-123", role: "user", content: "Hello" },
      { id: "msg-def-456", role: "assistant", content: "Hi" },
    ];

    await act(async () => {
      result.current.startStream("session-123", "Next", {
        history,
      });
      await vi.waitFor(() => expect(mockFetch).toHaveBeenCalled());
    });

    const callArgs = mockFetch.mock.calls[0];
    const body = JSON.parse(callArgs[1].body);

    // History messages should include IDs
    expect(body.messages[0].id).toBe("msg-abc-123");
    expect(body.messages[1].id).toBe("msg-def-456");
  });

  it("should include messageId on the current user message when provided (Finding 1)", async () => {
    mockFetch.mockResolvedValue(
      createMockSSEResponse([
        'data: {"content":"Response"}\n\n',
        "data: [DONE]\n\n",
      ]),
    );

    const { result } = renderHook(() => useStreamingChat());

    const history = [
      { id: "msg-1", role: "user", content: "First" },
      { id: "msg-2", role: "assistant", content: "Reply" },
    ];

    await act(async () => {
      result.current.startStream("session-123", "Second message", {
        history,
        messageId: "msg-optimistic-abc",
      });
      await vi.waitFor(() => expect(mockFetch).toHaveBeenCalled());
    });

    const callArgs = mockFetch.mock.calls[0];
    const body = JSON.parse(callArgs[1].body);

    // The current user message (last in the array) should include the messageId
    const lastMsg = body.messages[body.messages.length - 1];
    expect(lastMsg.role).toBe("user");
    expect(lastMsg.content).toBe("Second message");
    expect(lastMsg.id).toBe("msg-optimistic-abc");
  });

  it("should not include id on current user message when messageId is not provided", async () => {
    mockFetch.mockResolvedValue(
      createMockSSEResponse([
        'data: {"content":"Response"}\n\n',
        "data: [DONE]\n\n",
      ]),
    );

    const { result } = renderHook(() => useStreamingChat());

    await act(async () => {
      result.current.startStream("session-123", "Hello");
      await vi.waitFor(() => expect(mockFetch).toHaveBeenCalled());
    });

    const callArgs = mockFetch.mock.calls[0];
    const body = JSON.parse(callArgs[1].body);

    // Without messageId option, the current message should not have an id field
    const lastMsg = body.messages[body.messages.length - 1];
    expect(lastMsg.role).toBe("user");
    expect(lastMsg.content).toBe("Hello");
    expect(lastMsg.id).toBeUndefined();
  });
});
