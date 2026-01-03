/**
 * useWebVitals Hook Tests
 *
 * TDD tests for Core Web Vitals collection with persona context.
 *
 * Core Web Vitals (2024):
 * - LCP (Largest Contentful Paint)
 * - CLS (Cumulative Layout Shift)
 * - INP (Interaction to Next Paint) - replaced FID
 * - FCP (First Contentful Paint)
 * - TTFB (Time to First Byte)
 */

import { describe, it, expect, vi, beforeEach, afterEach } from "vitest";
import { renderHook } from "@testing-library/react";
import { useWebVitals, type WebVitalMetric } from "./useWebVitals";

// Mock web-vitals library
vi.mock("web-vitals", () => ({
  onLCP: vi.fn((callback) => {
    // Simulate LCP metric after a brief delay
    setTimeout(() => {
      callback({
        name: "LCP",
        value: 2500,
        rating: "good",
        id: "v1-lcp",
        navigationType: "navigate",
      });
    }, 10);
  }),
  onCLS: vi.fn((callback) => {
    setTimeout(() => {
      callback({
        name: "CLS",
        value: 0.1,
        rating: "good",
        id: "v1-cls",
        navigationType: "navigate",
      });
    }, 10);
  }),
  onINP: vi.fn((callback) => {
    setTimeout(() => {
      callback({
        name: "INP",
        value: 200,
        rating: "good",
        id: "v1-inp",
        navigationType: "navigate",
      });
    }, 10);
  }),
  onFCP: vi.fn((callback) => {
    setTimeout(() => {
      callback({
        name: "FCP",
        value: 1800,
        rating: "good",
        id: "v1-fcp",
        navigationType: "navigate",
      });
    }, 10);
  }),
  onTTFB: vi.fn((callback) => {
    setTimeout(() => {
      callback({
        name: "TTFB",
        value: 400,
        rating: "good",
        id: "v1-ttfb",
        navigationType: "navigate",
      });
    }, 10);
  }),
}));

describe("useWebVitals", () => {
  beforeEach(() => {
    vi.clearAllMocks();
    // Reset Do Not Track
    Object.defineProperty(navigator, "doNotTrack", {
      value: null,
      writable: true,
    });
  });

  afterEach(() => {
    vi.clearAllTimers();
  });

  describe("initialization", () => {
    it("should return initial empty metrics", () => {
      const { result } = renderHook(() => useWebVitals());

      expect(result.current.metrics).toEqual({});
      expect(result.current.isCollecting).toBe(true);
    });

    it("should provide callback for when metrics are collected", async () => {
      const onMetric = vi.fn();
      renderHook(() => useWebVitals({ onMetric }));

      // Wait for mocked metrics to be collected
      await vi.waitFor(
        () => {
          expect(onMetric).toHaveBeenCalled();
        },
        { timeout: 100 }
      );
    });

    it("should include persona in reported metrics when provided", async () => {
      const onMetric = vi.fn();
      renderHook(() =>
        useWebVitals({
          onMetric,
          persona: "admin",
        })
      );

      await vi.waitFor(
        () => {
          expect(onMetric).toHaveBeenCalledWith(
            expect.objectContaining({
              persona: "admin",
            })
          );
        },
        { timeout: 100 }
      );
    });
  });

  describe("metrics collection", () => {
    it("should collect LCP metric", async () => {
      const onMetric = vi.fn();
      const { result } = renderHook(() => useWebVitals({ onMetric }));

      await vi.waitFor(
        () => {
          expect(result.current.metrics.LCP).toBeDefined();
        },
        { timeout: 100 }
      );

      expect(result.current.metrics.LCP?.value).toBe(2500);
      expect(result.current.metrics.LCP?.rating).toBe("good");
    });

    it("should collect CLS metric", async () => {
      const { result } = renderHook(() => useWebVitals());

      await vi.waitFor(
        () => {
          expect(result.current.metrics.CLS).toBeDefined();
        },
        { timeout: 100 }
      );

      expect(result.current.metrics.CLS?.value).toBe(0.1);
    });

    it("should collect INP metric", async () => {
      const { result } = renderHook(() => useWebVitals());

      await vi.waitFor(
        () => {
          expect(result.current.metrics.INP).toBeDefined();
        },
        { timeout: 100 }
      );

      expect(result.current.metrics.INP?.value).toBe(200);
    });

    it("should collect FCP metric", async () => {
      const { result } = renderHook(() => useWebVitals());

      await vi.waitFor(
        () => {
          expect(result.current.metrics.FCP).toBeDefined();
        },
        { timeout: 100 }
      );

      expect(result.current.metrics.FCP?.value).toBe(1800);
    });

    it("should collect TTFB metric", async () => {
      const { result } = renderHook(() => useWebVitals());

      await vi.waitFor(
        () => {
          expect(result.current.metrics.TTFB).toBeDefined();
        },
        { timeout: 100 }
      );

      expect(result.current.metrics.TTFB?.value).toBe(400);
    });
  });

  describe("privacy respect", () => {
    it("should not collect when Do Not Track is enabled", () => {
      Object.defineProperty(navigator, "doNotTrack", {
        value: "1",
        writable: true,
      });

      const onMetric = vi.fn();
      const { result } = renderHook(() => useWebVitals({ onMetric }));

      expect(result.current.isCollecting).toBe(false);
      expect(onMetric).not.toHaveBeenCalled();
    });

    it("should respect enabled=false config", () => {
      const onMetric = vi.fn();
      const { result } = renderHook(() =>
        useWebVitals({ onMetric, enabled: false })
      );

      expect(result.current.isCollecting).toBe(false);
    });
  });

  describe("persona context", () => {
    it("should include persona in all metrics", async () => {
      const metrics: WebVitalMetric[] = [];
      const onMetric = vi.fn((metric: WebVitalMetric) => {
        metrics.push(metric);
      });

      renderHook(() =>
        useWebVitals({
          onMetric,
          persona: "alice-builder",
        })
      );

      await vi.waitFor(
        () => {
          expect(metrics.length).toBeGreaterThanOrEqual(1);
        },
        { timeout: 100 }
      );

      // All collected metrics should have persona
      expect(metrics.every((m) => m.persona === "alice-builder")).toBe(true);
    });

    it("should include userId when provided", async () => {
      const onMetric = vi.fn();

      renderHook(() =>
        useWebVitals({
          onMetric,
          persona: "bob",
          userId: "user:bob123",
        })
      );

      await vi.waitFor(
        () => {
          expect(onMetric).toHaveBeenCalledWith(
            expect.objectContaining({
              userId: "user:bob123",
              persona: "bob",
            })
          );
        },
        { timeout: 100 }
      );
    });
  });

  describe("export functionality", () => {
    it("should provide exportMetrics function", async () => {
      const { result } = renderHook(() => useWebVitals());

      await vi.waitFor(
        () => {
          expect(Object.keys(result.current.metrics).length).toBeGreaterThan(0);
        },
        { timeout: 100 }
      );

      const exported = result.current.exportMetrics();
      expect(exported).toBeDefined();
      expect(typeof exported).toBe("object");
    });

    it("should include timestamp in exported metrics", async () => {
      const { result } = renderHook(() => useWebVitals());

      await vi.waitFor(
        () => {
          expect(result.current.metrics.LCP).toBeDefined();
        },
        { timeout: 100 }
      );

      const exported = result.current.exportMetrics();
      expect(exported.timestamp).toBeDefined();
      expect(typeof exported.timestamp).toBe("number");
    });
  });

  describe("rating thresholds", () => {
    it("should report rating for each metric", async () => {
      const { result } = renderHook(() => useWebVitals());

      await vi.waitFor(
        () => {
          expect(result.current.metrics.LCP).toBeDefined();
        },
        { timeout: 100 }
      );

      // All metrics should have a rating
      const metrics = result.current.metrics;
      for (const key of Object.keys(metrics)) {
        const metric = metrics[key as keyof typeof metrics];
        expect(metric?.rating).toMatch(/^(good|needs-improvement|poor)$/);
      }
    });
  });
});
