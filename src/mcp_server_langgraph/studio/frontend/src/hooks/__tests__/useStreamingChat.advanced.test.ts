/**
 * useStreamingChat Advanced Tests
 *
 * Tests for usage tracking, thinking content, reasoning effort,
 * LangGraph node/edge streaming, and auth required events.
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
        await vi.waitFor(() => expect(result.current.isStreaming).toBe(false));
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
        await vi.waitFor(() => expect(result.current.isStreaming).toBe(false));
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
        await vi.waitFor(() => expect(result.current.isStreaming).toBe(false));
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
        await vi.waitFor(() => expect(result.current.isStreaming).toBe(false));
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
        await vi.waitFor(() => expect(result.current.isStreaming).toBe(false));
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
        await vi.waitFor(() => expect(result.current.isStreaming).toBe(false));
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
        await vi.waitFor(() => expect(result.current.isStreaming).toBe(false));
      });

      expect(result.current.thinkingContent).toBe(
        "First, I need to consider all options.",
      );
    });

    // Thinking object format {content, tokens}
    it("should parse thinking from object format", async () => {
      mockFetch.mockResolvedValue(
        createMockSSEResponse([
          'data: {"thinking":{"content":"Structured thinking content","tokens":250}}\n\n',
          'data: {"content":"Response based on thinking"}\n\n',
          "data: [DONE]\n\n",
        ]),
      );

      const { result } = renderHook(() => useStreamingChat());

      await act(async () => {
        result.current.startStream("session-123", "Hello");
        await vi.waitFor(() => expect(result.current.isStreaming).toBe(false));
      });

      expect(result.current.thinkingContent).toBe(
        "Structured thinking content",
      );
      expect(result.current.thinkingTokens).toBe(250);
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
        await vi.waitFor(() => expect(result.current.isStreaming).toBe(false));
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
        await vi.waitFor(() => expect(result.current.isStreaming).toBe(false));
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
        await vi.waitFor(() => expect(result.current.isStreaming).toBe(false));
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
        await vi.waitFor(() => expect(result.current.isStreaming).toBe(false));
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
        await vi.waitFor(() => expect(result.current.isStreaming).toBe(false));
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
        await vi.waitFor(() => expect(result.current.isStreaming).toBe(false));
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

    it("should dispatch addNode to Redux when langgraph node is received", async () => {
      mockDispatch.mockClear();
      mockFetch.mockResolvedValue(
        createMockSSEResponse([
          'data: {"langgraph_node":{"id":"node-1","name":"Agent","type":"agent","status":"running"}}\n\n',
          'data: {"langgraph_node":{"id":"node-1","name":"Agent","type":"agent","status":"completed","duration":500}}\n\n',
          "data: [DONE]\n\n",
        ]),
      );

      const { result } = renderHook(() => useStreamingChat());

      await act(async () => {
        result.current.startStream("session-123", "Hello");
        await vi.waitFor(() => expect(result.current.isStreaming).toBe(false));
      });

      // Should have dispatched addNode actions with sessionId
      expect(mockDispatch).toHaveBeenCalled();
      const addNodeCalls = mockDispatch.mock.calls.filter(
        (call) => call[0]?.type === "langGraph/addNode",
      );
      expect(addNodeCalls.length).toBeGreaterThan(0);

      // Verify sessionId is added to dispatched nodes
      const firstNodePayload = addNodeCalls[0][0].payload;
      expect(firstNodePayload.sessionId).toBe("session-123");
      expect(firstNodePayload.id).toBe("node-1");
      expect(firstNodePayload.name).toBe("Agent");
    });

    it("should dispatch clearNodes when starting new stream", async () => {
      mockDispatch.mockClear();
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

      // Should have dispatched clearNodes for this session
      const clearNodesCalls = mockDispatch.mock.calls.filter(
        (call) => call[0]?.type === "langGraph/clearNodes",
      );
      expect(clearNodesCalls.length).toBe(1);
      expect(clearNodesCalls[0][0].payload).toBe("session-123");
    });

    it("should dispatch setCurrentSessionId when starting stream", async () => {
      mockDispatch.mockClear();
      mockFetch.mockResolvedValue(
        createMockSSEResponse([
          'data: {"content":"Response"}\n\n',
          "data: [DONE]\n\n",
        ]),
      );

      const { result } = renderHook(() => useStreamingChat());

      await act(async () => {
        result.current.startStream("session-456", "Hello");
        await vi.waitFor(() => expect(result.current.isStreaming).toBe(false));
      });

      // Should have dispatched setCurrentSessionId
      const setSessionCalls = mockDispatch.mock.calls.filter(
        (call) => call[0]?.type === "langGraph/setCurrentSessionId",
      );
      expect(setSessionCalls.length).toBe(1);
      expect(setSessionCalls[0][0].payload).toBe("session-456");
    });
  });

  describe("Auth Required Events (ADR-0102)", () => {
    it("should parse auth_required event from SSE stream", async () => {
      const authRequiredEvent = {
        type: "auth_required",
        connection_id: "conn-123",
        template_id: "github",
        tool_name: "github.list_pull_requests",
        message: "Authentication required to access GitHub",
        retry_message_id: "msg-456",
      };

      mockFetch.mockResolvedValue(
        createMockSSEResponse([
          'data: {"content":"I need to access GitHub..."}\n\n',
          `data: ${JSON.stringify(authRequiredEvent)}\n\n`,
          'data: {"content":" Please authenticate."}\n\n',
          "data: [DONE]\n\n",
        ]),
      );

      const { result } = renderHook(() => useStreamingChat());

      await act(async () => {
        result.current.startStream("session-123", "List my GitHub PRs");
        await vi.waitFor(() => expect(result.current.isStreaming).toBe(false));
      });

      // Should capture auth_required event
      expect(result.current.authRequired).toEqual({
        connectionId: "conn-123",
        templateId: "github",
        toolName: "github.list_pull_requests",
        message: "Authentication required to access GitHub",
        retryMessageId: "msg-456",
      });

      // Content should still accumulate
      expect(result.current.streamingContent).toContain(
        "I need to access GitHub",
      );
    });

    it("should handle auth_required event with null connection_id (new connection needed)", async () => {
      const authRequiredEvent = {
        type: "auth_required",
        connection_id: null,
        template_id: "slack",
        tool_name: "slack.send_message",
        message: "Slack connection required",
        retry_message_id: null,
      };

      mockFetch.mockResolvedValue(
        createMockSSEResponse([
          `data: ${JSON.stringify(authRequiredEvent)}\n\n`,
          'data: {"content":"Please connect to Slack first."}\n\n',
          "data: [DONE]\n\n",
        ]),
      );

      const { result } = renderHook(() => useStreamingChat());

      await act(async () => {
        result.current.startStream("session-123", "Send a Slack message");
        await vi.waitFor(() => expect(result.current.isStreaming).toBe(false));
      });

      expect(result.current.authRequired).toEqual({
        connectionId: null,
        templateId: "slack",
        toolName: "slack.send_message",
        message: "Slack connection required",
        retryMessageId: null,
      });
    });

    it("should not set authRequired for non-auth_required events", async () => {
      mockFetch.mockResolvedValue(
        createMockSSEResponse([
          'data: {"content":"Hello!"}\n\n',
          'data: {"usage":{"prompt_tokens":10,"completion_tokens":5,"total_tokens":15}}\n\n',
          "data: [DONE]\n\n",
        ]),
      );

      const { result } = renderHook(() => useStreamingChat());

      await act(async () => {
        result.current.startStream("session-123", "Hello");
        await vi.waitFor(() => expect(result.current.isStreaming).toBe(false));
      });

      expect(result.current.authRequired).toBeNull();
    });

    it("should clear authRequired when starting new stream", async () => {
      // First stream with auth_required
      const authRequiredEvent = {
        type: "auth_required",
        connection_id: "conn-123",
        template_id: "github",
        tool_name: "github.list_repos",
        message: "Auth needed",
        retry_message_id: "msg-1",
      };

      mockFetch.mockResolvedValueOnce(
        createMockSSEResponse([
          `data: ${JSON.stringify(authRequiredEvent)}\n\n`,
          "data: [DONE]\n\n",
        ]),
      );

      const { result } = renderHook(() => useStreamingChat());

      await act(async () => {
        result.current.startStream("session-123", "List repos");
        await vi.waitFor(() => expect(result.current.isStreaming).toBe(false));
      });

      expect(result.current.authRequired).not.toBeNull();

      // Second stream without auth_required should clear it
      mockFetch.mockResolvedValueOnce(
        createMockSSEResponse([
          'data: {"content":"Hello again"}\n\n',
          "data: [DONE]\n\n",
        ]),
      );

      await act(async () => {
        result.current.startStream("session-123", "Hello");
        await vi.waitFor(() => expect(result.current.isStreaming).toBe(false));
      });

      expect(result.current.authRequired).toBeNull();
    });
  });
});
