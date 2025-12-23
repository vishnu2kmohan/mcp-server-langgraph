/**
 * useAICacheMetrics Hook Tests
 *
 * TDD tests for the AI Cache Metrics hook.
 * This hook provides cached metrics data for the AICacheMetricsDashboard.
 */

import { describe, it, expect, vi, beforeEach, afterEach } from "vitest";
import { renderHook, act, cleanup } from "@testing-library/react";
import { useAICacheMetrics } from "./useAICacheMetrics";

// =============================================================================
// Test Suite
// =============================================================================

describe("useAICacheMetrics", () => {
  beforeEach(() => {
    vi.clearAllMocks();
    vi.useFakeTimers();
  });

  afterEach(() => {
    cleanup(); // RTL cleanup
    vi.useRealTimers();
    vi.clearAllMocks();
    vi.restoreAllMocks();
  });

  it("returns initial snapshot with zero values", () => {
    const { result } = renderHook(() => useAICacheMetrics());

    expect(result.current.snapshot.requestCount).toBe(0);
    expect(result.current.snapshot.cacheHits).toBe(0);
    expect(result.current.snapshot.cacheMisses).toBe(0);
    expect(result.current.snapshot.errorCount).toBe(0);
  });

  it("tracks cache hit metrics", () => {
    const { result } = renderHook(() => useAICacheMetrics());

    act(() => {
      result.current.trackCacheHit("nav_prediction");
      result.current.trackCacheHit("nav_prediction");
      result.current.trackCacheHit("contextual_help");
    });

    const snapshot = result.current.snapshot;
    expect(snapshot.cacheHits).toBe(3);
  });

  it("tracks cache miss metrics", () => {
    const { result } = renderHook(() => useAICacheMetrics());

    act(() => {
      result.current.trackCacheMiss("nav_prediction");
      result.current.trackCacheMiss("risk_assessment");
    });

    const snapshot = result.current.snapshot;
    expect(snapshot.cacheMisses).toBe(2);
  });

  it("calculates cache hit ratio correctly", () => {
    const { result } = renderHook(() => useAICacheMetrics());

    act(() => {
      // 8 hits, 2 misses = 80% hit ratio
      for (let i = 0; i < 8; i++) {
        result.current.trackCacheHit("test");
      }
      for (let i = 0; i < 2; i++) {
        result.current.trackCacheMiss("test");
      }
    });

    const snapshot = result.current.snapshot;
    expect(snapshot.cacheHitRatio).toBe(0.8);
  });

  it("tracks request with latency", () => {
    const { result } = renderHook(() => useAICacheMetrics());

    act(() => {
      result.current.trackRequest("nav_prediction", 100);
      result.current.trackRequest("nav_prediction", 200);
    });

    const snapshot = result.current.snapshot;
    expect(snapshot.requestCount).toBe(2);
    expect(snapshot.averageLatency).toBe(150);
  });

  it("tracks errors", () => {
    const { result } = renderHook(() => useAICacheMetrics());

    act(() => {
      result.current.trackRequest("test", 100);
      result.current.trackError("test", new Error("Test error"));
    });

    const snapshot = result.current.snapshot;
    expect(snapshot.errorCount).toBe(1);
    expect(snapshot.errorRate).toBe(0.5);
  });

  it("provides per-feature metrics", () => {
    const { result } = renderHook(() => useAICacheMetrics());

    act(() => {
      result.current.trackRequest("nav_prediction", 100);
      result.current.trackRequest("nav_prediction", 200);
      result.current.trackRequest("contextual_help", 150);
      result.current.trackError("nav_prediction", new Error("Test"));
    });

    expect(result.current.featureMetrics["nav_prediction"]).toBeDefined();
    expect(result.current.featureMetrics["nav_prediction"]!.requestCount).toBe(
      2,
    );
    expect(
      result.current.featureMetrics["nav_prediction"]!.averageLatency,
    ).toBe(150);
    expect(result.current.featureMetrics["nav_prediction"]!.errorCount).toBe(1);

    expect(result.current.featureMetrics["contextual_help"]).toBeDefined();
    expect(result.current.featureMetrics["contextual_help"]!.requestCount).toBe(
      1,
    );
  });

  it("reset clears all metrics", () => {
    const { result } = renderHook(() => useAICacheMetrics());

    act(() => {
      result.current.trackRequest("test", 100);
      result.current.trackCacheHit("test");
      result.current.trackCacheMiss("test");
      result.current.trackError("test", new Error("Test"));
    });

    expect(result.current.snapshot.requestCount).toBeGreaterThan(0);

    act(() => {
      result.current.reset();
    });

    expect(result.current.snapshot.requestCount).toBe(0);
    expect(result.current.snapshot.cacheHits).toBe(0);
    expect(result.current.snapshot.cacheMisses).toBe(0);
    expect(result.current.snapshot.errorCount).toBe(0);
  });

  it("calls onMetricsUpdate callback when metrics change", () => {
    const onMetricsUpdate = vi.fn();
    const { result } = renderHook(() => useAICacheMetrics({ onMetricsUpdate }));

    act(() => {
      result.current.trackCacheHit("test");
    });

    expect(onMetricsUpdate).toHaveBeenCalled();
  });

  describe("Tiered Cache Stats (L1/L2)", () => {
    it("returns tieredCacheStats with initial zero values", () => {
      const { result } = renderHook(() => useAICacheMetrics());

      expect(result.current.tieredCacheStats).toBeDefined();
      expect(result.current.tieredCacheStats.l1Hits).toBe(0);
      expect(result.current.tieredCacheStats.l2Hits).toBe(0);
      expect(result.current.tieredCacheStats.misses).toBe(0);
    });

    it("tracks L1 (in-memory) cache hits separately", () => {
      const { result } = renderHook(() => useAICacheMetrics());

      act(() => {
        result.current.trackL1Hit("nav_prediction");
        result.current.trackL1Hit("nav_prediction");
      });

      expect(result.current.tieredCacheStats.l1Hits).toBe(2);
      // L1 hits also count as total cache hits
      expect(result.current.snapshot.cacheHits).toBe(2);
    });

    it("tracks L2 (sessionStorage) cache hits separately", () => {
      const { result } = renderHook(() => useAICacheMetrics());

      act(() => {
        result.current.trackL2Hit("contextual_help");
        result.current.trackL2Hit("risk_assessment");
        result.current.trackL2Hit("nav_prediction");
      });

      expect(result.current.tieredCacheStats.l2Hits).toBe(3);
      // L2 hits also count as total cache hits
      expect(result.current.snapshot.cacheHits).toBe(3);
    });

    it("tracks tiered cache misses", () => {
      const { result } = renderHook(() => useAICacheMetrics());

      act(() => {
        result.current.trackTieredMiss("new_feature");
      });

      expect(result.current.tieredCacheStats.misses).toBe(1);
      // Tiered misses also count as total cache misses
      expect(result.current.snapshot.cacheMisses).toBe(1);
    });

    it("calculates age based on first cache operation timestamp", () => {
      const { result } = renderHook(() => useAICacheMetrics());

      act(() => {
        result.current.trackL1Hit("test");
      });

      // Age should be >= 0
      expect(result.current.tieredCacheStats.age).toBeGreaterThanOrEqual(0);

      // Advance time and trigger a re-render by tracking another operation
      act(() => {
        vi.advanceTimersByTime(5000); // 5 seconds
        result.current.trackL1Hit("test2"); // Triggers re-render
      });

      // Age should reflect elapsed time
      expect(result.current.tieredCacheStats.age).toBeGreaterThanOrEqual(5000);
    });

    it("reset clears tiered cache stats", () => {
      const { result } = renderHook(() => useAICacheMetrics());

      act(() => {
        result.current.trackL1Hit("test");
        result.current.trackL2Hit("test");
        result.current.trackTieredMiss("test");
      });

      expect(result.current.tieredCacheStats.l1Hits).toBeGreaterThan(0);

      act(() => {
        result.current.reset();
      });

      expect(result.current.tieredCacheStats.l1Hits).toBe(0);
      expect(result.current.tieredCacheStats.l2Hits).toBe(0);
      expect(result.current.tieredCacheStats.misses).toBe(0);
    });
  });
});
