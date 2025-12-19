/**
 * useStreamingChat Hook Tests
 *
 * Tests for streaming chat hook using fetch + ReadableStream for SSE.
 * Updated from EventSource to support POST requests with JSON body.
 */

import { describe, it, expect, vi, beforeEach, afterEach } from "vitest";
import { renderHook, act } from "@testing-library/react";
import { useStreamingChat } from "./useStreamingChat";

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
function createMockSSEResponse(
  chunks: string[],
  _ok = true,
  status = 200,
): Response {
  const stream = createMockSSEStream(chunks);
  return new Response(stream, {
    status,
    headers: { "Content-Type": "text/event-stream" },
  });
}

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

      expect(mockFetch).toHaveBeenCalledWith(
        "/api/v1/chat/completions/stream",
        expect.objectContaining({
          method: "POST",
          headers: expect.objectContaining({
            "Content-Type": "application/json",
          }),
          body: expect.any(String),
          signal: expect.any(AbortSignal),
        }),
      );

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
        await vi.waitFor(() => !result.current.isStreaming);
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
        await vi.waitFor(() => !result.current.isStreaming);
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
        await vi.waitFor(() => !result.current.isStreaming);
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
        await vi.waitFor(() => !result.current.isStreaming);
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
        await vi.waitFor(() => !result.current.isStreaming);
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
        await vi.waitFor(() => !result.current.isStreaming);
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
        await vi.waitFor(() => result.current.error !== null);
      });

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
        await vi.waitFor(() => result.current.error !== null);
      });

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
        await vi.waitFor(() => !result.current.isStreaming);
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

  describe("Usage Tracking", () => {
    it("should start with null usage", () => {
      const { result } = renderHook(() => useStreamingChat());

      expect(result.current.usage).toBeNull();
    });

    it("should track usage data from streaming chunks", async () => {
      mockFetch.mockResolvedValue(
        createMockSSEResponse([
          'data: {"content":"Response","usage":{"prompt_tokens":10,"completion_tokens":5,"total_tokens":15}}\n\n',
          "data: [DONE]\n\n",
        ]),
      );

      const { result } = renderHook(() => useStreamingChat());

      await act(async () => {
        result.current.startStream("session-123", "Hello");
        await vi.waitFor(() => !result.current.isStreaming);
      });

      expect(result.current.usage).toEqual({
        promptTokens: 10,
        completionTokens: 5,
        totalTokens: 15,
      });
    });

    it("should track model from streaming chunks", async () => {
      mockFetch.mockResolvedValue(
        createMockSSEResponse([
          'data: {"content":"Response","model":"gpt-4-turbo"}\n\n',
          "data: [DONE]\n\n",
        ]),
      );

      const { result } = renderHook(() => useStreamingChat());

      await act(async () => {
        result.current.startStream("session-123", "Hello");
        await vi.waitFor(() => !result.current.isStreaming);
      });

      expect(result.current.model).toBe("gpt-4-turbo");
    });

    it("should preserve usage after stream completes", async () => {
      mockFetch.mockResolvedValue(
        createMockSSEResponse([
          'data: {"content":"Response","usage":{"prompt_tokens":10,"completion_tokens":5,"total_tokens":15},"model":"gpt-4"}\n\n',
          "data: [DONE]\n\n",
        ]),
      );

      const { result } = renderHook(() => useStreamingChat());

      await act(async () => {
        result.current.startStream("session-123", "Hello");
        await vi.waitFor(() => !result.current.isStreaming);
      });

      expect(result.current.isStreaming).toBe(false);
      expect(result.current.usage).toEqual({
        promptTokens: 10,
        completionTokens: 5,
        totalTokens: 15,
      });
      expect(result.current.model).toBe("gpt-4");
    });

    it("should reset usage when starting new stream", async () => {
      mockFetch.mockResolvedValueOnce(
        createMockSSEResponse([
          'data: {"content":"First","usage":{"prompt_tokens":10,"completion_tokens":5,"total_tokens":15},"model":"gpt-4"}\n\n',
          "data: [DONE]\n\n",
        ]),
      );

      const { result } = renderHook(() => useStreamingChat());

      await act(async () => {
        result.current.startStream("session-123", "First");
        await vi.waitFor(() => !result.current.isStreaming);
      });

      expect(result.current.usage).not.toBeNull();

      // Start new stream - should reset
      mockFetch.mockResolvedValueOnce(
        createMockSSEResponse([
          'data: {"content":"Second"}\n\n',
          "data: [DONE]\n\n",
        ]),
      );

      await act(async () => {
        result.current.startStream("session-123", "Second");
      });

      // Should be reset immediately when starting new stream
      expect(result.current.usage).toBeNull();
      expect(result.current.model).toBeNull();
    });

    it("should clear usage when clearContent is called", async () => {
      mockFetch.mockResolvedValue(
        createMockSSEResponse([
          'data: {"content":"Response","usage":{"prompt_tokens":10,"completion_tokens":5,"total_tokens":15}}\n\n',
          "data: [DONE]\n\n",
        ]),
      );

      const { result } = renderHook(() => useStreamingChat());

      await act(async () => {
        result.current.startStream("session-123", "Hello");
        await vi.waitFor(() => !result.current.isStreaming);
      });

      act(() => {
        result.current.clearContent();
      });

      expect(result.current.usage).toBeNull();
      expect(result.current.model).toBeNull();
    });
  });

  describe("Thinking Content (LLM Reasoning Trace)", () => {
    it("should start with empty thinking content", () => {
      const { result } = renderHook(() => useStreamingChat());

      expect(result.current.thinkingContent).toBe("");
    });

    it("should parse thinking content from Claude-style response", async () => {
      mockFetch.mockResolvedValue(
        createMockSSEResponse([
          'data: {"thinking":"Let me analyze this step by step..."}\n\n',
          'data: {"content":"Here is my answer."}\n\n',
          "data: [DONE]\n\n",
        ]),
      );

      const { result } = renderHook(() => useStreamingChat());

      await act(async () => {
        result.current.startStream("session-123", "Hello");
        await vi.waitFor(() => !result.current.isStreaming);
      });

      expect(result.current.thinkingContent).toBe(
        "Let me analyze this step by step...",
      );
      expect(result.current.streamingContent).toBe("Here is my answer.");
    });

    it("should accumulate thinking content across multiple chunks", async () => {
      mockFetch.mockResolvedValue(
        createMockSSEResponse([
          'data: {"thinking":"First, "}\n\n',
          'data: {"thinking":"I need to consider "}\n\n',
          'data: {"thinking":"all options."}\n\n',
          'data: {"content":"My conclusion is..."}\n\n',
          "data: [DONE]\n\n",
        ]),
      );

      const { result } = renderHook(() => useStreamingChat());

      await act(async () => {
        result.current.startStream("session-123", "Hello");
        await vi.waitFor(() => !result.current.isStreaming);
      });

      expect(result.current.thinkingContent).toBe(
        "First, I need to consider all options.",
      );
    });

    it("should parse thinking_content from Gemini-style response", async () => {
      mockFetch.mockResolvedValue(
        createMockSSEResponse([
          'data: {"thinking_content":"Analyzing the problem..."}\n\n',
          'data: {"content":"The answer is 42."}\n\n',
          "data: [DONE]\n\n",
        ]),
      );

      const { result } = renderHook(() => useStreamingChat());

      await act(async () => {
        result.current.startStream("session-123", "Hello");
        await vi.waitFor(() => !result.current.isStreaming);
      });

      expect(result.current.thinkingContent).toBe("Analyzing the problem...");
    });

    it("should track thinking tokens when provided", async () => {
      mockFetch.mockResolvedValue(
        createMockSSEResponse([
          'data: {"thinking":"Deep analysis...","thinking_tokens":1500}\n\n',
          'data: {"content":"Answer","usage":{"prompt_tokens":10,"completion_tokens":5,"total_tokens":15}}\n\n',
          "data: [DONE]\n\n",
        ]),
      );

      const { result } = renderHook(() => useStreamingChat());

      await act(async () => {
        result.current.startStream("session-123", "Hello");
        await vi.waitFor(() => !result.current.isStreaming);
      });

      expect(result.current.thinkingTokens).toBe(1500);
    });

    it("should reset thinking content when starting new stream", async () => {
      mockFetch.mockResolvedValueOnce(
        createMockSSEResponse([
          'data: {"thinking":"First thinking..."}\n\n',
          'data: {"content":"First answer"}\n\n',
          "data: [DONE]\n\n",
        ]),
      );

      const { result } = renderHook(() => useStreamingChat());

      await act(async () => {
        result.current.startStream("session-123", "First");
        await vi.waitFor(() => !result.current.isStreaming);
      });

      expect(result.current.thinkingContent).toBe("First thinking...");

      // Start new stream
      mockFetch.mockResolvedValueOnce(
        createMockSSEResponse([
          'data: {"content":"Second answer"}\n\n',
          "data: [DONE]\n\n",
        ]),
      );

      await act(async () => {
        result.current.startStream("session-123", "Second");
      });

      // Should be reset
      expect(result.current.thinkingContent).toBe("");
    });

    it("should clear thinking content when clearContent is called", async () => {
      mockFetch.mockResolvedValue(
        createMockSSEResponse([
          'data: {"thinking":"Some thinking..."}\n\n',
          'data: {"content":"Answer"}\n\n',
          "data: [DONE]\n\n",
        ]),
      );

      const { result } = renderHook(() => useStreamingChat());

      await act(async () => {
        result.current.startStream("session-123", "Hello");
        await vi.waitFor(() => !result.current.isStreaming);
      });

      act(() => {
        result.current.clearContent();
      });

      expect(result.current.thinkingContent).toBe("");
      expect(result.current.thinkingTokens).toBeNull();
    });
  });

  describe("Reasoning Effort Parameter", () => {
    it("should include reasoning_effort in request when provided", async () => {
      mockFetch.mockResolvedValue(
        createMockSSEResponse([
          'data: {"content":"Response"}\n\n',
          "data: [DONE]\n\n",
        ]),
      );

      const { result } = renderHook(() => useStreamingChat());

      await act(async () => {
        result.current.startStream("session-123", "Hello", {
          reasoningEffort: "high",
        });
        await vi.waitFor(() => expect(mockFetch).toHaveBeenCalled());
      });

      const callArgs = mockFetch.mock.calls[0];
      const body = JSON.parse(callArgs[1].body);
      expect(body.reasoning_effort).toBe("high");
    });

    it("should not include reasoning_effort when not provided", async () => {
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
      expect(body.reasoning_effort).toBeUndefined();
    });

    it("should accept all valid reasoning effort levels", async () => {
      mockFetch.mockResolvedValue(
        createMockSSEResponse([
          'data: {"content":"Response"}\n\n',
          "data: [DONE]\n\n",
        ]),
      );

      const { result } = renderHook(() => useStreamingChat());

      for (const level of ["low", "medium", "high"]) {
        await act(async () => {
          result.current.startStream("session-123", "Hello", {
            reasoningEffort: level as "low" | "medium" | "high",
          });
          await vi.waitFor(() => expect(mockFetch).toHaveBeenCalled());
        });

        const callArgs = mockFetch.mock.calls[mockFetch.mock.calls.length - 1];
        const body = JSON.parse(callArgs[1].body);
        expect(body.reasoning_effort).toBe(level);
      }
    });
  });

  describe("LangGraph Node/Edge Streaming", () => {
    it("should start with empty langgraph state", () => {
      const { result } = renderHook(() => useStreamingChat());

      expect(result.current.langgraphNodes).toEqual([]);
      expect(result.current.langgraphEdges).toEqual([]);
      expect(result.current.currentNode).toBeNull();
    });

    it("should parse langgraph node updates from streaming", async () => {
      mockFetch.mockResolvedValue(
        createMockSSEResponse([
          'data: {"langgraph_node":{"id":"node-1","name":"Agent","type":"agent","status":"running"}}\n\n',
          'data: {"content":"Processing..."}\n\n',
          'data: {"langgraph_node":{"id":"node-1","name":"Agent","type":"agent","status":"completed"}}\n\n',
          "data: [DONE]\n\n",
        ]),
      );

      const { result } = renderHook(() => useStreamingChat());

      await act(async () => {
        result.current.startStream("session-123", "Hello");
        await vi.waitFor(() => !result.current.isStreaming);
      });

      expect(result.current.langgraphNodes.length).toBeGreaterThan(0);
    });

    it("should parse langgraph edges from streaming", async () => {
      mockFetch.mockResolvedValue(
        createMockSSEResponse([
          'data: {"langgraph_edge":{"from":"start","to":"agent"}}\n\n',
          'data: {"content":"Response"}\n\n',
          "data: [DONE]\n\n",
        ]),
      );

      const { result } = renderHook(() => useStreamingChat());

      await act(async () => {
        result.current.startStream("session-123", "Hello");
        await vi.waitFor(() => !result.current.isStreaming);
      });

      expect(result.current.langgraphEdges.length).toBeGreaterThan(0);
    });

    it("should track current node from streaming", async () => {
      mockFetch.mockResolvedValue(
        createMockSSEResponse([
          'data: {"current_node":"agent-1"}\n\n',
          'data: {"content":"Thinking..."}\n\n',
          "data: [DONE]\n\n",
        ]),
      );

      const { result } = renderHook(() => useStreamingChat());

      await act(async () => {
        result.current.startStream("session-123", "Hello");
        await vi.waitFor(() => !result.current.isStreaming);
      });

      expect(result.current.currentNode).toBe("agent-1");
    });

    it("should reset langgraph state when starting new stream", async () => {
      mockFetch.mockResolvedValueOnce(
        createMockSSEResponse([
          'data: {"langgraph_node":{"id":"node-1","name":"Agent","type":"agent","status":"completed"}}\n\n',
          'data: {"content":"First"}\n\n',
          "data: [DONE]\n\n",
        ]),
      );

      const { result } = renderHook(() => useStreamingChat());

      await act(async () => {
        result.current.startStream("session-123", "First");
        await vi.waitFor(() => !result.current.isStreaming);
      });

      // Start new stream - should reset
      mockFetch.mockResolvedValueOnce(
        createMockSSEResponse([
          'data: {"content":"Second"}\n\n',
          "data: [DONE]\n\n",
        ]),
      );

      await act(async () => {
        result.current.startStream("session-123", "Second");
      });

      // Should be reset when starting new stream
      expect(result.current.langgraphNodes).toEqual([]);
      expect(result.current.langgraphEdges).toEqual([]);
      expect(result.current.currentNode).toBeNull();
    });
  });
});
