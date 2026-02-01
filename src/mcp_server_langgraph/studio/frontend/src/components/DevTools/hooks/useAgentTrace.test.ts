/**
 * useAgentTrace Hook Tests
 *
 * TDD tests for the agent trace data fetching hook.
 *
 * Phase 4D: Updated to use new `/api/v1/sessions/{id}/agent-execution-trace` endpoint
 * which returns LangGraph node execution traces (not OTEL traces from Tempo).
 */
import { describe, it, expect, vi, beforeEach, afterEach } from "vitest";
import { renderHook, waitFor, act } from "@testing-library/react";

import { useAgentTrace } from "./useAgentTrace";
import type { AgentExecutionTrace } from "../../../types/chat";

// =============================================================================
// Test Data
// =============================================================================

/**
 * Mock API response from `/api/v1/sessions/{id}/agent-execution-trace`.
 * Returns LangGraph node execution traces (Phase 4).
 */
const mockAgentExecutionTraceApiResponse = {
  session_id: "session-123",
  traces: [
    {
      trace_id: "trace-1",
      node_name: "Router",
      status: "completed",
      start_time: Date.now() - 5000,
      end_time: Date.now() - 4000,
      duration_ms: 1000,
      sequence_number: 0,
    },
    {
      trace_id: "trace-2",
      node_name: "Agent",
      status: "completed",
      start_time: Date.now() - 4000,
      end_time: Date.now() - 2000,
      duration_ms: 2000,
      sequence_number: 1,
    },
  ],
  total: 2,
  has_more: false,
};

/**
 * Expected frontend format after transformation (AgentExecutionTrace).
 * Transforms the new API format to AgentExecutionTrace.
 */
const expectedTransformedTrace: AgentExecutionTrace = {
  rawOutput: undefined,
  steps: [
    { name: "Router", status: "completed", duration: 1000 },
    { name: "Agent", status: "completed", duration: 2000 },
  ],
  tokens: undefined,
  nodes: [
    {
      id: "trace-1",
      name: "Router",
      type: "default",
      status: "completed",
      duration: 1000,
    },
    {
      id: "trace-2",
      name: "Agent",
      type: "default",
      status: "completed",
      duration: 2000,
    },
  ],
  edges: undefined,
  currentNode: undefined,
  startTime: mockAgentExecutionTraceApiResponse.traces[0].start_time,
  endTime: mockAgentExecutionTraceApiResponse.traces[1].end_time,
};

// Alias for backward compatibility in tests
const mockApiResponse = mockAgentExecutionTraceApiResponse;
const mockTrace: AgentExecutionTrace = expectedTransformedTrace;

// =============================================================================
// Mocks
// =============================================================================

const mockFetch = vi.fn();

// =============================================================================
// Tests
// =============================================================================

describe("useAgentTrace", () => {
  beforeEach(() => {
    vi.clearAllMocks();
    global.fetch = mockFetch;
  });

  afterEach(() => {
    vi.restoreAllMocks();
  });

  describe("initial state", () => {
    it("should return null trace initially", async () => {
      mockFetch.mockResolvedValue({
        ok: true,
        json: () => Promise.resolve(mockApiResponse),
      });

      const { result } = renderHook(() =>
        useAgentTrace({ sessionId: "session-123" }),
      );

      // Initially null before fetch completes
      expect(result.current.trace).toBeNull();
    });

    it("should set isLoading to true during fetch", async () => {
      mockFetch.mockImplementation(
        () =>
          new Promise((resolve) =>
            setTimeout(
              () =>
                resolve({
                  ok: true,
                  json: () => Promise.resolve(mockApiResponse),
                }),
              100,
            ),
          ),
      );

      const { result } = renderHook(() =>
        useAgentTrace({ sessionId: "session-123" }),
      );

      // Should be loading initially
      expect(result.current.isLoading).toBe(true);

      await waitFor(() => {
        expect(result.current.isLoading).toBe(false);
      });
    });

    it("should return null error initially", async () => {
      mockFetch.mockResolvedValue({
        ok: true,
        json: () => Promise.resolve(mockApiResponse),
      });

      const { result } = renderHook(() =>
        useAgentTrace({ sessionId: "session-123" }),
      );

      expect(result.current.error).toBeNull();
    });

    it("should return refetch function", async () => {
      mockFetch.mockResolvedValue({
        ok: true,
        json: () => Promise.resolve(mockApiResponse),
      });

      const { result } = renderHook(() =>
        useAgentTrace({ sessionId: "session-123" }),
      );

      expect(typeof result.current.refetch).toBe("function");
    });
  });

  describe("successful fetch", () => {
    it("should fetch trace on mount", async () => {
      mockFetch.mockResolvedValue({
        ok: true,
        json: () => Promise.resolve(mockApiResponse),
      });

      renderHook(() => useAgentTrace({ sessionId: "session-123" }));

      await waitFor(() => {
        expect(mockFetch).toHaveBeenCalledWith(
          "/api/v1/sessions/session-123/agent-execution-trace",
          expect.anything(),
        );
      });
    });

    it("should set trace data after successful fetch", async () => {
      mockFetch.mockResolvedValue({
        ok: true,
        json: () => Promise.resolve(mockApiResponse),
      });

      const { result } = renderHook(() =>
        useAgentTrace({ sessionId: "session-123" }),
      );

      await waitFor(() => {
        expect(result.current.trace).toEqual(mockTrace);
      });
    });

    it("should set isLoading to false after fetch completes", async () => {
      mockFetch.mockResolvedValue({
        ok: true,
        json: () => Promise.resolve(mockApiResponse),
      });

      const { result } = renderHook(() =>
        useAgentTrace({ sessionId: "session-123" }),
      );

      await waitFor(() => {
        expect(result.current.isLoading).toBe(false);
        expect(result.current.trace).not.toBeNull();
      });
    });
  });

  describe("failed fetch", () => {
    it("should set error on non-ok response", async () => {
      mockFetch.mockResolvedValue({
        ok: false,
        statusText: "Not Found",
      });

      const { result } = renderHook(() =>
        useAgentTrace({ sessionId: "session-404" }),
      );

      await waitFor(() => {
        expect(result.current.error).not.toBeNull();
        expect(result.current.error?.message).toContain("Not Found");
      });
    });

    it("should set trace to null on error", async () => {
      mockFetch.mockResolvedValue({
        ok: false,
        statusText: "Internal Server Error",
      });

      const { result } = renderHook(() =>
        useAgentTrace({ sessionId: "session-500" }),
      );

      await waitFor(() => {
        expect(result.current.trace).toBeNull();
        expect(result.current.error).not.toBeNull();
      });
    });

    it("should handle network errors", async () => {
      mockFetch.mockRejectedValue(new Error("Network error"));

      const { result } = renderHook(() =>
        useAgentTrace({ sessionId: "session-123" }),
      );

      await waitFor(() => {
        expect(result.current.error?.message).toBe("Network error");
      });
    });

    it("should handle non-Error thrown values", async () => {
      mockFetch.mockRejectedValue("String error");

      const { result } = renderHook(() =>
        useAgentTrace({ sessionId: "session-123" }),
      );

      await waitFor(() => {
        expect(result.current.error?.message).toBe("Unknown error");
      });
    });
  });

  describe("refetch", () => {
    it("should refetch trace when refetch is called", async () => {
      mockFetch.mockResolvedValue({
        ok: true,
        json: () => Promise.resolve(mockApiResponse),
      });

      const { result } = renderHook(() =>
        useAgentTrace({ sessionId: "session-123" }),
      );

      await waitFor(() => {
        expect(result.current.trace).not.toBeNull();
      });

      expect(mockFetch).toHaveBeenCalledTimes(1);

      act(() => {
        result.current.refetch();
      });

      await waitFor(() => {
        expect(mockFetch).toHaveBeenCalledTimes(2);
      });
    });
  });

  describe("sessionId changes", () => {
    it("should refetch when sessionId changes", async () => {
      mockFetch.mockResolvedValue({
        ok: true,
        json: () => Promise.resolve(mockApiResponse),
      });

      const { result, rerender } = renderHook(
        ({ sessionId }) => useAgentTrace({ sessionId }),
        { initialProps: { sessionId: "session-123" } },
      );

      await waitFor(() => {
        expect(result.current.trace).not.toBeNull();
      });

      rerender({ sessionId: "session-456" });

      await waitFor(() => {
        expect(mockFetch).toHaveBeenCalledWith(
          "/api/v1/sessions/session-456/agent-execution-trace",
          expect.anything(),
        );
      });
    });

    it("should not fetch if sessionId is empty", async () => {
      mockFetch.mockResolvedValue({
        ok: true,
        json: () => Promise.resolve(mockApiResponse),
      });

      renderHook(() => useAgentTrace({ sessionId: "" }));

      // Give time for potential fetch
      await new Promise((r) => setTimeout(r, 50));

      expect(mockFetch).not.toHaveBeenCalled();
    });
  });

  describe("auto-refresh", () => {
    beforeEach(() => {
      vi.useFakeTimers();
    });

    afterEach(() => {
      vi.useRealTimers();
    });

    it("should not auto-refresh by default", async () => {
      mockFetch.mockResolvedValue({
        ok: true,
        json: () => Promise.resolve(mockApiResponse),
      });

      renderHook(() => useAgentTrace({ sessionId: "session-123" }));

      // Flush initial fetch
      await vi.advanceTimersByTimeAsync(0);

      // Only initial fetch
      expect(mockFetch).toHaveBeenCalledTimes(1);

      // Advance time - should not cause more fetches without autoRefresh
      await vi.advanceTimersByTimeAsync(10000);
      expect(mockFetch).toHaveBeenCalledTimes(1);
    });

    it("should auto-refresh when enabled", async () => {
      mockFetch.mockResolvedValue({
        ok: true,
        json: () => Promise.resolve(mockApiResponse),
      });

      renderHook(() =>
        useAgentTrace({
          sessionId: "session-123",
          autoRefresh: true,
          refreshInterval: 1000,
        }),
      );

      // Flush initial fetch
      await vi.advanceTimersByTimeAsync(0);
      expect(mockFetch).toHaveBeenCalledTimes(1);

      // Advance time for first refresh
      await vi.advanceTimersByTimeAsync(1000);
      expect(mockFetch).toHaveBeenCalledTimes(2);

      // Another refresh
      await vi.advanceTimersByTimeAsync(1000);
      expect(mockFetch).toHaveBeenCalledTimes(3);
    });

    it("should respect custom refresh interval", async () => {
      mockFetch.mockResolvedValue({
        ok: true,
        json: () => Promise.resolve(mockApiResponse),
      });

      renderHook(() =>
        useAgentTrace({
          sessionId: "session-123",
          autoRefresh: true,
          refreshInterval: 3000,
        }),
      );

      // Flush initial fetch
      await vi.advanceTimersByTimeAsync(0);
      expect(mockFetch).toHaveBeenCalledTimes(1);

      // Not enough time for refresh
      await vi.advanceTimersByTimeAsync(2000);
      expect(mockFetch).toHaveBeenCalledTimes(1);

      // Now should refresh
      await vi.advanceTimersByTimeAsync(1000);
      expect(mockFetch).toHaveBeenCalledTimes(2);
    });

    it("should stop auto-refresh on unmount", async () => {
      mockFetch.mockResolvedValue({
        ok: true,
        json: () => Promise.resolve(mockApiResponse),
      });

      const { unmount } = renderHook(() =>
        useAgentTrace({
          sessionId: "session-123",
          autoRefresh: true,
          refreshInterval: 1000,
        }),
      );

      // Flush initial fetch
      await vi.advanceTimersByTimeAsync(0);
      expect(mockFetch).toHaveBeenCalledTimes(1);

      unmount();

      // Advance time - should not trigger more fetches
      await vi.advanceTimersByTimeAsync(5000);
      expect(mockFetch).toHaveBeenCalledTimes(1);
    });
  });

  describe("API response transformation (Phase 4D)", () => {
    it("should transform agent execution trace API response", async () => {
      // New API format from /api/v1/sessions/{id}/agent-execution-trace
      const apiResponse = {
        session_id: "session-123",
        traces: [
          {
            trace_id: "trace-1",
            node_name: "Router",
            status: "completed",
            start_time: 1700000000000,
            end_time: 1700000001000,
            duration_ms: 1000,
            sequence_number: 0,
          },
          {
            trace_id: "trace-2",
            node_name: "Agent",
            status: "running",
            start_time: 1700000001000,
            end_time: 1700000003000,
            duration_ms: 2000,
            sequence_number: 1,
          },
        ],
        total: 2,
        has_more: false,
      };

      mockFetch.mockResolvedValue({
        ok: true,
        json: () => Promise.resolve(apiResponse),
      });

      const { result } = renderHook(() =>
        useAgentTrace({ sessionId: "session-123" }),
      );

      await waitFor(() => {
        expect(result.current.trace).not.toBeNull();
      });

      // Should have timing from traces
      expect(result.current.trace?.startTime).toBe(1700000000000);
      expect(result.current.trace?.endTime).toBe(1700000003000);
    });

    it("should transform traces to nodes for AgentTraceTab display", async () => {
      // New API format with multiple traces
      const apiResponse = {
        session_id: "session-123",
        traces: [
          {
            trace_id: "trace-1",
            node_name: "Router",
            status: "completed",
            start_time: 1700000000000,
            duration_ms: 100,
            sequence_number: 0,
          },
          {
            trace_id: "trace-2",
            node_name: "Agent",
            status: "running",
            start_time: 1700000000100,
            duration_ms: 200,
            sequence_number: 1,
          },
          {
            trace_id: "trace-3",
            node_name: "Tool",
            status: "error",
            start_time: 1700000000300,
            duration_ms: 50,
            sequence_number: 2,
          },
        ],
        total: 3,
        has_more: false,
      };

      mockFetch.mockResolvedValue({
        ok: true,
        json: () => Promise.resolve(apiResponse),
      });

      const { result } = renderHook(() =>
        useAgentTrace({ sessionId: "session-123" }),
      );

      await waitFor(() => {
        expect(result.current.trace).not.toBeNull();
      });

      // Should have nodes array derived from traces
      expect(result.current.trace?.nodes).toBeDefined();
      expect(result.current.trace?.nodes).toHaveLength(3);

      // Verify node structure matches LangGraphNode interface
      const nodes = result.current.trace?.nodes ?? [];
      expect(nodes[0]).toMatchObject({
        id: "trace-1",
        name: "Router",
        status: "completed",
        duration: 100,
      });
      expect(nodes[1]).toMatchObject({
        id: "trace-2",
        name: "Agent",
        status: "running",
        duration: 200,
      });
      expect(nodes[2]).toMatchObject({
        id: "trace-3",
        name: "Tool",
        status: "error",
        duration: 50,
      });
    });

    it("should also generate steps for backward compatibility", async () => {
      const apiResponse = {
        session_id: "session-123",
        traces: [
          {
            trace_id: "trace-1",
            node_name: "Router",
            status: "completed",
            start_time: 1700000000000,
            duration_ms: 1000,
            sequence_number: 0,
          },
        ],
        total: 1,
        has_more: false,
      };

      mockFetch.mockResolvedValue({
        ok: true,
        json: () => Promise.resolve(apiResponse),
      });

      const { result } = renderHook(() =>
        useAgentTrace({ sessionId: "session-123" }),
      );

      await waitFor(() => {
        expect(result.current.trace).not.toBeNull();
      });

      // Should have steps array for backward compatibility
      expect(result.current.trace?.steps).toBeDefined();
      expect(result.current.trace?.steps).toHaveLength(1);
      expect(result.current.trace?.steps?.[0]).toEqual({
        name: "Router",
        status: "completed",
        duration: 1000,
      });
    });

    it("should handle empty traces array", async () => {
      const apiResponse = {
        session_id: "session-123",
        traces: [],
        total: 0,
        has_more: false,
      };

      mockFetch.mockResolvedValue({
        ok: true,
        json: () => Promise.resolve(apiResponse),
      });

      const { result } = renderHook(() =>
        useAgentTrace({ sessionId: "session-123" }),
      );

      await waitFor(() => {
        expect(result.current.trace).not.toBeNull();
      });

      expect(result.current.trace?.nodes).toEqual([]);
      expect(result.current.trace?.steps).toEqual([]);
    });

    it("should handle traces with missing optional fields", async () => {
      // Traces may not have end_time or duration_ms
      const apiResponse = {
        session_id: "session-123",
        traces: [
          {
            trace_id: "trace-1",
            node_name: "Router",
            status: "running",
            start_time: 1700000000000,
            sequence_number: 0,
            // end_time and duration_ms are omitted (node still running)
          },
        ],
        total: 1,
        has_more: false,
      };

      mockFetch.mockResolvedValue({
        ok: true,
        json: () => Promise.resolve(apiResponse),
      });

      const { result } = renderHook(() =>
        useAgentTrace({ sessionId: "session-123" }),
      );

      await waitFor(() => {
        expect(result.current.trace).not.toBeNull();
      });

      // Should handle trace without duration
      expect(result.current.trace?.nodes).toHaveLength(1);
      expect(result.current.trace?.nodes?.[0].id).toBe("trace-1");
      expect(result.current.trace?.nodes?.[0].name).toBe("Router");
      expect(result.current.trace?.nodes?.[0].status).toBe("running");
      expect(result.current.trace?.nodes?.[0].duration).toBeUndefined();
    });
  });
});
