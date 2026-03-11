/**
 * useStreamingChat Core Tests
 *
 * Tests for initial state, starting stream, receiving messages,
 * error handling, stopping stream, clearing content, and cleanup.
 */

import { describe, it, expect, vi, beforeEach, afterEach } from "vitest";
import { renderHook, act } from "@testing-library/react";

import {
  mockDispatch,
  mockNavigate,
  createMockSSEResponse,
} from "./useStreamingChat.fixtures";

vi.mock("../../store/hooks", () => ({
  useAppDispatch: () => mockDispatch,
  useAppSelector: vi.fn(),
}));

vi.mock("react-router", () => ({
  useNavigate: () => mockNavigate,
}));

vi.mock("../../utils/storage", async () => {
  const actual = await vi.importActual("../../utils/storage");
  return {
    ...actual,
    getAuthToken: vi.fn(() => "mock-token"),
    setAuthTokens: vi.fn(),
    clearAuthTokens: vi.fn(),
    STORAGE_KEYS: {
      REFRESH_TOKEN: "refresh_token",
    },
  };
});
vi.mock("../../utils/intendedRoute", () => ({
  setIntendedRoute: vi.fn(),
}));

import { useStreamingChat } from "../useStreamingChat";

describe("useStreamingChat", () => {
  let mockFetch: ReturnType<typeof vi.fn>;
  let abortController: AbortController | null = null;

  beforeEach(() => {
    vi.clearAllMocks();
    abortController = null;

    // Mock fetch globally
    mockFetch = vi.fn();
    vi.stubGlobal("fetch", mockFetch);
  });

  afterEach(() => {
    vi.unstubAllGlobals();
    abortController?.abort();
  });

  describe("Initial State", () => {
    it("should start with empty state", () => {
      const { result } = renderHook(() => useStreamingChat());

      expect(result.current.isStreaming).toBe(false);
      expect(result.current.streamingContent).toBe("");
      expect(result.current.error).toBeNull();
    });
  });

  describe("Starting Stream", () => {
    it("should set isStreaming to true when starting stream", async () => {
      // Setup mock to return a pending promise
      mockFetch.mockImplementation(
        () =>
          new Promise(() => {
            /* never resolves */
          }),
      );

      const { result } = renderHook(() => useStreamingChat());

      act(() => {
        result.current.startStream("session-123", "Hello");
      });

      expect(result.current.isStreaming).toBe(true);
    });

    it("should call fetch with POST and correct body", async () => {
      mockFetch.mockResolvedValue(
        createMockSSEResponse([
          'data: {"content":"Hi"}\n\n',
          "data: [DONE]\n\n",
        ]),
      );

      const { result } = renderHook(() => useStreamingChat());

      await act(async () => {
        result.current.startStream("session-123", "Hello World");
        // Wait for fetch to be called
        await vi.waitFor(() => expect(mockFetch).toHaveBeenCalled());
      });

      // Verify fetch was called with the correct URL
      expect(mockFetch).toHaveBeenCalledWith(
        "/api/v1/chat/completions/stream",
        expect.objectContaining({
          method: "POST",
          body: expect.any(String),
        }),
      );

      // Verify headers include Content-Type (authenticatedFetch uses Headers object)
      const [, options] = mockFetch.mock.calls[0]!;
      const headers = (options as RequestInit).headers as Headers;
      expect(headers.get("Content-Type")).toBe("application/json");

      // Verify the body structure
      const callArgs = mockFetch.mock.calls[0];
      const body = JSON.parse(callArgs[1].body);
      expect(body).toEqual({
        session_id: "session-123",
        messages: [{ role: "user", content: "Hello World" }],
      });
    });

    it("should reset content when starting new stream", async () => {
      // First stream returns content
      mockFetch.mockResolvedValueOnce(
        createMockSSEResponse([
          'data: {"content":"First response"}\n\n',
          "data: [DONE]\n\n",
        ]),
      );

      const { result } = renderHook(() => useStreamingChat());

      await act(async () => {
        result.current.startStream("session-123", "First message");
        await vi.waitFor(() => expect(result.current.isStreaming).toBe(false));
      });

      expect(result.current.streamingContent).toBe("First response");

      // Second stream should reset
      mockFetch.mockResolvedValueOnce(
        createMockSSEResponse([
          'data: {"content":"Second"}\n\n',
          "data: [DONE]\n\n",
        ]),
      );

      await act(async () => {
        result.current.startStream("session-123", "Second message");
      });

      // Content should be reset (empty or new content)
      expect(result.current.streamingContent).not.toBe("First response");
    });
  });

  describe("Receiving Messages", () => {
    it("should accumulate streamed content", async () => {
      mockFetch.mockResolvedValue(
        createMockSSEResponse([
          'data: {"content":"Hi "}\n\n',
          'data: {"content":"there!"}\n\n',
          "data: [DONE]\n\n",
        ]),
      );

      const { result } = renderHook(() => useStreamingChat());

      await act(async () => {
        result.current.startStream("session-123", "Hello");
        await vi.waitFor(() => expect(result.current.isStreaming).toBe(false));
      });

      expect(result.current.streamingContent).toBe("Hi there!");
    });

    it("should handle [DONE] message and stop streaming", async () => {
      mockFetch.mockResolvedValue(
        createMockSSEResponse([
          'data: {"content":"Response"}\n\n',
          "data: [DONE]\n\n",
        ]),
      );

      const { result } = renderHook(() => useStreamingChat());

      await act(async () => {
        result.current.startStream("session-123", "Hello");
        await vi.waitFor(() => expect(result.current.isStreaming).toBe(false));
      });

      expect(result.current.isStreaming).toBe(false);
      expect(result.current.streamingContent).toBe("Response");
    });

    it("should handle messages with delta.content format", async () => {
      // Backend sends delta.content format
      mockFetch.mockResolvedValue(
        createMockSSEResponse([
          'data: {"delta":{"content":"Hello "}}\n\n',
          'data: {"delta":{"content":"World"}}\n\n',
          "data: [DONE]\n\n",
        ]),
      );

      const { result } = renderHook(() => useStreamingChat());

      await act(async () => {
        result.current.startStream("session-123", "Hi");
        await vi.waitFor(() => expect(result.current.isStreaming).toBe(false));
      });

      expect(result.current.streamingContent).toBe("Hello World");
    });

    it("should handle non-JSON messages gracefully", async () => {
      mockFetch.mockResolvedValue(
        createMockSSEResponse([
          "data: invalid json\n\n",
          'data: {"content":"Valid"}\n\n',
          "data: [DONE]\n\n",
        ]),
      );

      const { result } = renderHook(() => useStreamingChat());

      await act(async () => {
        result.current.startStream("session-123", "Hello");
        await vi.waitFor(() => expect(result.current.isStreaming).toBe(false));
      });

      // Should not crash and should get valid content
      expect(result.current.streamingContent).toBe("Valid");
      expect(result.current.error).toBeNull();
    });

    it("should handle messages without content field", async () => {
      mockFetch.mockResolvedValue(
        createMockSSEResponse([
          'data: {"type":"metadata"}\n\n',
          'data: {"content":"Actual content"}\n\n',
          "data: [DONE]\n\n",
        ]),
      );

      const { result } = renderHook(() => useStreamingChat());

      await act(async () => {
        result.current.startStream("session-123", "Hello");
        await vi.waitFor(() => expect(result.current.isStreaming).toBe(false));
      });

      expect(result.current.streamingContent).toBe("Actual content");
    });
  });

  describe("Error Handling", () => {
    it("should set error when fetch fails", async () => {
      mockFetch.mockRejectedValue(new Error("Network error"));

      const { result } = renderHook(() => useStreamingChat());

      await act(async () => {
        result.current.startStream("session-123", "Hello");
      });

      await vi.waitFor(() => expect(result.current.error).not.toBeNull());

      expect(result.current.isStreaming).toBe(false);
      expect(result.current.error).toBe(
        "Stream connection failed: Network error",
      );
    });

    it("should set error when response is not ok", async () => {
      mockFetch.mockResolvedValue(
        new Response("Server Error", {
          status: 500,
          statusText: "Internal Server Error",
        }),
      );

      const { result } = renderHook(() => useStreamingChat());

      await act(async () => {
        result.current.startStream("session-123", "Hello");
      });

      await vi.waitFor(() => expect(result.current.error).not.toBeNull());

      expect(result.current.isStreaming).toBe(false);
      expect(result.current.error).toContain("500");
    });
  });

  describe("Stopping Stream", () => {
    it("should stop streaming when stopStream is called", async () => {
      // Create a stream that won't complete automatically
      mockFetch.mockImplementation(
        () =>
          new Promise((resolve) => {
            // Never resolve to keep stream "open"
            setTimeout(() => {
              resolve(
                createMockSSEResponse([
                  'data: {"content":"Response"}\n\n',
                  "data: [DONE]\n\n",
                ]),
              );
            }, 10000);
          }),
      );

      const { result } = renderHook(() => useStreamingChat());

      act(() => {
        result.current.startStream("session-123", "Hello");
      });

      expect(result.current.isStreaming).toBe(true);

      act(() => {
        result.current.stopStream();
      });

      expect(result.current.isStreaming).toBe(false);
    });

    it("should handle stopStream when no stream is active", () => {
      const { result } = renderHook(() => useStreamingChat());

      // Should not throw
      expect(() => {
        act(() => {
          result.current.stopStream();
        });
      }).not.toThrow();
    });
  });

  describe("Clearing Content", () => {
    it("should clear content when clearContent is called", async () => {
      mockFetch.mockResolvedValue(
        createMockSSEResponse([
          'data: {"content":"Response"}\n\n',
          "data: [DONE]\n\n",
        ]),
      );

      const { result } = renderHook(() => useStreamingChat());

      await act(async () => {
        result.current.startStream("session-123", "Hello");
        await vi.waitFor(() => expect(result.current.isStreaming).toBe(false));
      });

      expect(result.current.streamingContent).toBe("Response");

      act(() => {
        result.current.clearContent();
      });

      expect(result.current.streamingContent).toBe("");
      expect(result.current.error).toBeNull();
    });
  });

  describe("Cleanup", () => {
    it("should abort fetch on unmount", async () => {
      let capturedSignal: AbortSignal | null = null;
      mockFetch.mockImplementation((_url: string, options: RequestInit) => {
        capturedSignal = options.signal as AbortSignal;
        return new Promise(() => {
          /* never resolves */
        });
      });

      const { result, unmount } = renderHook(() => useStreamingChat());

      act(() => {
        result.current.startStream("session-123", "Hello");
      });

      expect(capturedSignal).not.toBeNull();
      expect(capturedSignal?.aborted).toBe(false);

      unmount();

      // Signal should be aborted after unmount
      expect(capturedSignal?.aborted).toBe(true);
    });
  });
});
