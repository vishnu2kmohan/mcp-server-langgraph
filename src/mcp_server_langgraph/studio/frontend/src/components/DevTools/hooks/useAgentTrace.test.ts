/**
 * useAgentTrace Hook Tests
 *
 * TDD tests for the agent trace data fetching hook.
 */
import { describe, it, expect, vi, beforeEach, afterEach } from "vitest";
import { renderHook, waitFor, act } from "@testing-library/react";

import { useAgentTrace } from "./useAgentTrace";
import type { AgentExecutionTrace } from "../../../types/chat";

// =============================================================================
// Test Data
// =============================================================================

const mockTrace: AgentExecutionTrace = {
  nodes: [
    {
      id: "node-1",
      name: "Router",
      type: "router",
      startTime: Date.now() - 5000,
      endTime: Date.now() - 4000,
      duration: 1000,
      status: "completed",
    },
    {
      id: "node-2",
      name: "Agent",
      type: "agent",
      startTime: Date.now() - 4000,
      endTime: Date.now() - 2000,
      duration: 2000,
      status: "completed",
    },
  ],
  edges: [{ source: "node-1", target: "node-2" }],
  metadata: {
    sessionId: "session-123",
    totalDuration: 3000,
  },
};

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
        json: () => Promise.resolve(mockTrace),
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
                  json: () => Promise.resolve(mockTrace),
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
        json: () => Promise.resolve(mockTrace),
      });

      const { result } = renderHook(() =>
        useAgentTrace({ sessionId: "session-123" }),
      );

      expect(result.current.error).toBeNull();
    });

    it("should return refetch function", async () => {
      mockFetch.mockResolvedValue({
        ok: true,
        json: () => Promise.resolve(mockTrace),
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
        json: () => Promise.resolve(mockTrace),
      });

      renderHook(() => useAgentTrace({ sessionId: "session-123" }));

      await waitFor(() => {
        expect(mockFetch).toHaveBeenCalledWith(
          "/api/v1/sessions/session-123/trace",
        );
      });
    });

    it("should set trace data after successful fetch", async () => {
      mockFetch.mockResolvedValue({
        ok: true,
        json: () => Promise.resolve(mockTrace),
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
        json: () => Promise.resolve(mockTrace),
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
        json: () => Promise.resolve(mockTrace),
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
        json: () => Promise.resolve(mockTrace),
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
          "/api/v1/sessions/session-456/trace",
        );
      });
    });

    it("should not fetch if sessionId is empty", async () => {
      mockFetch.mockResolvedValue({
        ok: true,
        json: () => Promise.resolve(mockTrace),
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
        json: () => Promise.resolve(mockTrace),
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
        json: () => Promise.resolve(mockTrace),
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
        json: () => Promise.resolve(mockTrace),
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
        json: () => Promise.resolve(mockTrace),
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
});
