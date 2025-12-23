/**
 * useAIMetrics Tests
 *
 * TDD: Tests written FIRST before implementation.
 * Metrics tracking for AI Intelligence features.
 *
 * Features:
 * - Track AI feature usage counts
 * - Track request latencies
 * - Track error rates
 * - Track cache hit/miss ratios
 * - Integrate with observability systems
 */

import { describe, it, expect, vi, beforeEach } from "vitest";
import { renderHook, act } from "@testing-library/react";
import {
  useAIMetrics,
  createAIMetricsTracker,
  type _AIMetricsEvent,
  type _AIMetricsSnapshot,
} from "./useAIMetrics";

describe("useAIMetrics", () => {
  beforeEach(() => {
    vi.clearAllMocks();
  });

  describe("basic tracking", () => {
    it("should track feature requests", () => {
      const { result } = renderHook(() => useAIMetrics());

      act(() => {
        result.current.trackRequest("nav_prediction", 150);
      });

      const snapshot = result.current.getSnapshot();
      expect(snapshot.requestCount).toBe(1);
    });

    it("should track request latency", () => {
      const { result } = renderHook(() => useAIMetrics());

      act(() => {
        result.current.trackRequest("nav_prediction", 150);
        result.current.trackRequest("nav_prediction", 250);
      });

      const snapshot = result.current.getSnapshot();
      expect(snapshot.averageLatency).toBe(200);
    });

    it("should track errors", () => {
      const { result } = renderHook(() => useAIMetrics());

      act(() => {
        result.current.trackError("nav_prediction", new Error("Test error"));
      });

      const snapshot = result.current.getSnapshot();
      expect(snapshot.errorCount).toBe(1);
    });

    it("should calculate error rate", () => {
      const { result } = renderHook(() => useAIMetrics());

      act(() => {
        result.current.trackRequest("nav_prediction", 100);
        result.current.trackRequest("nav_prediction", 100);
        result.current.trackError("nav_prediction", new Error("Test"));
      });

      const snapshot = result.current.getSnapshot();
      // 1 error out of 3 total events = 33.33% error rate
      expect(snapshot.errorRate).toBeCloseTo(0.333, 2);
    });
  });

  describe("cache metrics", () => {
    it("should track cache hits", () => {
      const { result } = renderHook(() => useAIMetrics());

      act(() => {
        result.current.trackCacheHit("nav_prediction");
      });

      const snapshot = result.current.getSnapshot();
      expect(snapshot.cacheHits).toBe(1);
    });

    it("should track cache misses", () => {
      const { result } = renderHook(() => useAIMetrics());

      act(() => {
        result.current.trackCacheMiss("nav_prediction");
      });

      const snapshot = result.current.getSnapshot();
      expect(snapshot.cacheMisses).toBe(1);
    });

    it("should calculate cache hit ratio", () => {
      const { result } = renderHook(() => useAIMetrics());

      act(() => {
        result.current.trackCacheHit("nav_prediction");
        result.current.trackCacheHit("nav_prediction");
        result.current.trackCacheMiss("nav_prediction");
      });

      const snapshot = result.current.getSnapshot();
      // 2 hits out of 3 = 66.67%
      expect(snapshot.cacheHitRatio).toBeCloseTo(0.667, 2);
    });
  });

  describe("feature-specific metrics", () => {
    it("should track metrics per feature", () => {
      const { result } = renderHook(() => useAIMetrics());

      act(() => {
        result.current.trackRequest("nav_prediction", 100);
        result.current.trackRequest("contextual_help", 200);
        result.current.trackRequest("nav_prediction", 150);
      });

      const navMetrics = result.current.getFeatureMetrics("nav_prediction");
      const helpMetrics = result.current.getFeatureMetrics("contextual_help");

      expect(navMetrics.requestCount).toBe(2);
      expect(navMetrics.averageLatency).toBe(125);
      expect(helpMetrics.requestCount).toBe(1);
      expect(helpMetrics.averageLatency).toBe(200);
    });
  });

  describe("reset functionality", () => {
    it("should reset all metrics", () => {
      const { result } = renderHook(() => useAIMetrics());

      act(() => {
        result.current.trackRequest("nav_prediction", 100);
        result.current.trackError("nav_prediction", new Error("Test"));
        result.current.trackCacheHit("nav_prediction");
      });

      act(() => {
        result.current.reset();
      });

      const snapshot = result.current.getSnapshot();
      expect(snapshot.requestCount).toBe(0);
      expect(snapshot.errorCount).toBe(0);
      expect(snapshot.cacheHits).toBe(0);
    });
  });

  describe("event callback", () => {
    it("should call onEvent callback when tracking", () => {
      const onEvent = vi.fn();
      const { result } = renderHook(() => useAIMetrics({ onEvent }));

      act(() => {
        result.current.trackRequest("nav_prediction", 100);
      });

      expect(onEvent).toHaveBeenCalledWith(
        expect.objectContaining({
          type: "request",
          feature: "nav_prediction",
          latency: 100,
        })
      );
    });
  });
});

describe("createAIMetricsTracker", () => {
  it("should create a standalone metrics tracker", () => {
    const tracker = createAIMetricsTracker();

    tracker.trackRequest("nav_prediction", 100);

    const snapshot = tracker.getSnapshot();
    expect(snapshot.requestCount).toBe(1);
  });

  it("should support custom event handler", () => {
    const onEvent = vi.fn();
    const tracker = createAIMetricsTracker({ onEvent });

    tracker.trackError("nav_prediction", new Error("Test"));

    expect(onEvent).toHaveBeenCalledWith(
      expect.objectContaining({
        type: "error",
        feature: "nav_prediction",
      })
    );
  });
});

describe("AIMetricsSnapshot type", () => {
  it("should have correct structure", () => {
    const { result } = renderHook(() => useAIMetrics());
    const snapshot = result.current.getSnapshot();

    expect(snapshot).toHaveProperty("requestCount");
    expect(snapshot).toHaveProperty("errorCount");
    expect(snapshot).toHaveProperty("cacheHits");
    expect(snapshot).toHaveProperty("cacheMisses");
    expect(snapshot).toHaveProperty("averageLatency");
    expect(snapshot).toHaveProperty("errorRate");
    expect(snapshot).toHaveProperty("cacheHitRatio");
    expect(snapshot).toHaveProperty("timestamp");
  });
});
