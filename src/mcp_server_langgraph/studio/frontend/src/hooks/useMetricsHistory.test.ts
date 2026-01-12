/**
 * useMetricsHistory Hook Tests
 *
 * Tests for the metrics history tracking hook.
 */

import { describe, it, expect, vi, beforeEach, afterEach } from "vitest";
import { renderHook, act } from "@testing-library/react";
import { useMetricsHistory } from "./useMetricsHistory";

describe("useMetricsHistory", () => {
  beforeEach(() => {
    vi.useFakeTimers();
  });

  afterEach(() => {
    vi.useRealTimers();
    vi.clearAllMocks();
    vi.restoreAllMocks();
  });

  describe("addSnapshot", () => {
    it("should add a snapshot with timestamp", () => {
      const { result } = renderHook(() => useMetricsHistory());

      act(() => {
        result.current.addSnapshot({
          requestsTotal: 100,
          errorsTotal: 5,
          avgLatencyMs: 50,
          p99LatencyMs: 150,
          tokensUsed: 1000,
          activeSessions: 10,
        });
      });

      expect(result.current.history.length).toBe(1);
      expect(result.current.history[0].requestsTotal).toBe(100);
      expect(result.current.history[0].timestamp).toBeTypeOf("number");
    });

    it("should dedupe snapshots within interval", () => {
      const { result } = renderHook(() =>
        useMetricsHistory({ dedupeInterval: 5000 }),
      );

      act(() => {
        result.current.addSnapshot({
          requestsTotal: 100,
          errorsTotal: 5,
          avgLatencyMs: 50,
          p99LatencyMs: 150,
          tokensUsed: 1000,
          activeSessions: 10,
        });
      });

      // Advance time by 1 second (within dedupeInterval)
      act(() => {
        vi.advanceTimersByTime(1000);
        result.current.addSnapshot({
          requestsTotal: 110,
          errorsTotal: 6,
          avgLatencyMs: 55,
          p99LatencyMs: 160,
          tokensUsed: 1100,
          activeSessions: 11,
        });
      });

      // Should not add because within dedupeInterval
      expect(result.current.history.length).toBe(1);
      expect(result.current.history[0].requestsTotal).toBe(100);
    });

    it("should add snapshots after interval", () => {
      const { result } = renderHook(() =>
        useMetricsHistory({ dedupeInterval: 5000 }),
      );

      act(() => {
        result.current.addSnapshot({
          requestsTotal: 100,
          errorsTotal: 5,
          avgLatencyMs: 50,
          p99LatencyMs: 150,
          tokensUsed: 1000,
          activeSessions: 10,
        });
      });

      // Advance time beyond dedupeInterval
      act(() => {
        vi.advanceTimersByTime(6000);
        result.current.addSnapshot({
          requestsTotal: 110,
          errorsTotal: 6,
          avgLatencyMs: 55,
          p99LatencyMs: 160,
          tokensUsed: 1100,
          activeSessions: 11,
        });
      });

      // Should add because beyond dedupeInterval
      expect(result.current.history.length).toBe(2);
      expect(result.current.history[1].requestsTotal).toBe(110);
    });

    it("should limit snapshots to maxSnapshots", () => {
      const { result } = renderHook(() =>
        useMetricsHistory({ maxSnapshots: 3, dedupeInterval: 0 }),
      );

      for (let i = 0; i < 5; i++) {
        act(() => {
          vi.advanceTimersByTime(1000);
          result.current.addSnapshot({
            requestsTotal: 100 + i * 10,
            errorsTotal: 5,
            avgLatencyMs: 50,
            p99LatencyMs: 150,
            tokensUsed: 1000,
            activeSessions: 10,
          });
        });
      }

      expect(result.current.history.length).toBe(3);
      // Should keep the last 3 snapshots
      expect(result.current.history[0].requestsTotal).toBe(120);
      expect(result.current.history[1].requestsTotal).toBe(130);
      expect(result.current.history[2].requestsTotal).toBe(140);
    });
  });

  describe("clearHistory", () => {
    it("should clear all snapshots", () => {
      const { result } = renderHook(() =>
        useMetricsHistory({ dedupeInterval: 0 }),
      );

      act(() => {
        result.current.addSnapshot({
          requestsTotal: 100,
          errorsTotal: 5,
          avgLatencyMs: 50,
          p99LatencyMs: 150,
          tokensUsed: 1000,
          activeSessions: 10,
        });
      });

      expect(result.current.history.length).toBe(1);

      act(() => {
        result.current.clearHistory();
      });

      expect(result.current.history.length).toBe(0);
    });
  });

  describe("computeTrend", () => {
    it("should return stable for single value", () => {
      const { result } = renderHook(() => useMetricsHistory());
      expect(result.current.computeTrend([100])).toBe("stable");
    });

    it("should return stable for empty array", () => {
      const { result } = renderHook(() => useMetricsHistory());
      expect(result.current.computeTrend([])).toBe("stable");
    });

    it("should return up for increasing values", () => {
      const { result } = renderHook(() =>
        useMetricsHistory({ trendThreshold: 0.05 }),
      );
      expect(result.current.computeTrend([100, 110])).toBe("up");
    });

    it("should return down for decreasing values", () => {
      const { result } = renderHook(() =>
        useMetricsHistory({ trendThreshold: 0.05 }),
      );
      expect(result.current.computeTrend([100, 90])).toBe("down");
    });

    it("should return stable for small changes", () => {
      const { result } = renderHook(() =>
        useMetricsHistory({ trendThreshold: 0.05 }),
      );
      expect(result.current.computeTrend([100, 102])).toBe("stable");
    });

    it("should handle zero values", () => {
      const { result } = renderHook(() => useMetricsHistory());
      expect(result.current.computeTrend([0, 10])).toBe("up");
      expect(result.current.computeTrend([0, 0])).toBe("stable");
    });
  });

  describe("computeChange", () => {
    it("should return 0 for single value", () => {
      const { result } = renderHook(() => useMetricsHistory());
      expect(result.current.computeChange([100])).toBe(0);
    });

    it("should compute percentage increase", () => {
      const { result } = renderHook(() => useMetricsHistory());
      expect(result.current.computeChange([100, 120])).toBe(20);
    });

    it("should compute percentage decrease", () => {
      const { result } = renderHook(() => useMetricsHistory());
      expect(result.current.computeChange([100, 80])).toBe(-20);
    });

    it("should handle zero base value", () => {
      const { result } = renderHook(() => useMetricsHistory());
      expect(result.current.computeChange([0, 10])).toBe(100);
      expect(result.current.computeChange([0, 0])).toBe(0);
    });
  });

  describe("getSparkline", () => {
    it("should return sparkline for a metric", () => {
      const { result } = renderHook(() =>
        useMetricsHistory({ dedupeInterval: 0 }),
      );

      act(() => {
        result.current.addSnapshot({
          requestsTotal: 100,
          errorsTotal: 5,
          avgLatencyMs: 50,
          p99LatencyMs: 150,
          tokensUsed: 1000,
          activeSessions: 10,
        });
        vi.advanceTimersByTime(1000);
        result.current.addSnapshot({
          requestsTotal: 110,
          errorsTotal: 6,
          avgLatencyMs: 55,
          p99LatencyMs: 160,
          tokensUsed: 1100,
          activeSessions: 11,
        });
      });

      expect(result.current.getSparkline("requestsTotal")).toEqual([100, 110]);
      expect(result.current.getSparkline("errorsTotal")).toEqual([5, 6]);
    });
  });

  describe("getMetricsWithTrends", () => {
    it("should return empty array for null metrics", () => {
      const { result } = renderHook(() => useMetricsHistory());
      expect(result.current.getMetricsWithTrends(null)).toEqual([]);
    });

    it("should return metrics with trends and sparklines", () => {
      const { result } = renderHook(() =>
        useMetricsHistory({ dedupeInterval: 0 }),
      );

      act(() => {
        result.current.addSnapshot({
          requestsTotal: 100,
          errorsTotal: 5,
          avgLatencyMs: 50,
          p99LatencyMs: 150,
          tokensUsed: 1000,
          activeSessions: 10,
        });
        vi.advanceTimersByTime(1000);
        result.current.addSnapshot({
          requestsTotal: 120,
          errorsTotal: 4,
          avgLatencyMs: 55,
          p99LatencyMs: 160,
          tokensUsed: 1200,
          activeSessions: 12,
        });
      });

      const metrics = result.current.getMetricsWithTrends({
        requestsTotal: 120,
        errorsTotal: 4,
        avgLatencyMs: 55,
        p99LatencyMs: 160,
        tokensUsed: 1200,
        activeSessions: 12,
      });

      expect(metrics.length).toBe(6);

      // Check requests metric
      const requestsMetric = metrics.find((m) => m.name === "requests_total");
      expect(requestsMetric).toBeDefined();
      expect(requestsMetric?.value).toBe(120);
      expect(requestsMetric?.trend).toBe("up");
      expect(requestsMetric?.sparkline).toEqual([100, 120]);

      // Check errors metric (decreasing)
      const errorsMetric = metrics.find((m) => m.name === "errors_total");
      expect(errorsMetric).toBeDefined();
      expect(errorsMetric?.trend).toBe("down");
    });

    it("should use current value as sparkline when no history", () => {
      const { result } = renderHook(() => useMetricsHistory());

      const metrics = result.current.getMetricsWithTrends({
        requestsTotal: 100,
        errorsTotal: 5,
        avgLatencyMs: 50,
        p99LatencyMs: 150,
        tokensUsed: 1000,
        activeSessions: 10,
      });

      const requestsMetric = metrics.find((m) => m.name === "requests_total");
      expect(requestsMetric?.sparkline).toEqual([100]);
      expect(requestsMetric?.trend).toBe("stable");
    });
  });
});
