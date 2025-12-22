/**
 * Web Vitals Tests
 *
 * Tests for Core Web Vitals tracking using Performance Observer API:
 * - FCP (First Contentful Paint)
 * - LCP (Largest Contentful Paint)
 * - CLS (Cumulative Layout Shift)
 * - INP (Interaction to Next Paint)
 * - Navigation timing
 */
import { describe, it, expect, vi, beforeEach, afterEach } from "vitest";
import { WebVitalsTracker } from "./webVitals";

// Store callbacks for simulating entries
let observerCallbacks: Map<
  string,
  (list: { getEntries: () => object[] }) => void
> = new Map();

// Track observe calls
const mockObserve = vi.fn();
const mockDisconnect = vi.fn();

// Mock PerformanceObserver as a proper class
class MockPerformanceObserver {
  private callback: (list: { getEntries: () => object[] }) => void;

  constructor(callback: (list: { getEntries: () => object[] }) => void) {
    this.callback = callback;
  }

  observe(options: { type: string; buffered?: boolean }) {
    observerCallbacks.set(options.type, this.callback);
    mockObserve(options);
  }

  disconnect() {
    mockDisconnect();
  }

  static supportedEntryTypes = [
    "paint",
    "largest-contentful-paint",
    "layout-shift",
    "first-input",
  ];
}

describe("WebVitalsTracker", () => {
  beforeEach(() => {
    vi.clearAllMocks();
    observerCallbacks = new Map();
    vi.stubGlobal("PerformanceObserver", MockPerformanceObserver);
  });

  afterEach(() => {
    vi.unstubAllGlobals();
  });

  describe("Initialization", () => {
    it("should create tracker instance", () => {
      const tracker = new WebVitalsTracker();
      expect(tracker).toBeDefined();
    });

    it("should return empty metrics initially", () => {
      const tracker = new WebVitalsTracker();
      const metrics = tracker.getMetrics();

      expect(metrics.fcp).toBeNull();
      expect(metrics.lcp).toBeNull();
      // CLS is cumulative, starts at 0 (not null)
      expect(metrics.cls).toBe(0);
      expect(metrics.inp).toBeNull();
    });

    it("should accept callback on construction", () => {
      const callback = vi.fn();
      const tracker = new WebVitalsTracker({ onMetric: callback });
      expect(tracker).toBeDefined();
    });
  });

  describe("Start Tracking", () => {
    it("should register PerformanceObserver for FCP", () => {
      const tracker = new WebVitalsTracker();
      tracker.start();
      
      expect(mockObserve).toHaveBeenCalledWith(
        expect.objectContaining({ type: "paint" }),
      );
    });

    it("should register PerformanceObserver for LCP", () => {
      const tracker = new WebVitalsTracker();
      tracker.start();
      
      expect(mockObserve).toHaveBeenCalledWith(
        expect.objectContaining({ type: "largest-contentful-paint" }),
      );
    });

    it("should register PerformanceObserver for CLS", () => {
      const tracker = new WebVitalsTracker();
      tracker.start();

      expect(mockObserve).toHaveBeenCalledWith(
        expect.objectContaining({ type: "layout-shift" }),
      );
    });

    it("should not re-register observers if already tracking", () => {
      const tracker = new WebVitalsTracker({ debug: true });
      tracker.start();

      const callCountAfterFirst = mockObserve.mock.calls.length;

      // Start again - should not add new observers
      tracker.start();

      expect(mockObserve.mock.calls.length).toBe(callCountAfterFirst);
    });
  });

  describe("FCP Tracking", () => {
    it("should capture FCP value from paint entries", () => {
      const callback = vi.fn();
      const tracker = new WebVitalsTracker({ onMetric: callback });
      tracker.start();

      const paintCallback = observerCallbacks.get("paint");
      paintCallback?.({
        getEntries: () => [
          { name: "first-contentful-paint", startTime: 1234 },
        ],
      });

      const metrics = tracker.getMetrics();
      expect(metrics.fcp).toBe(1234);
    });

    it("should call onMetric callback when FCP is captured", () => {
      const callback = vi.fn();
      const tracker = new WebVitalsTracker({ onMetric: callback });
      tracker.start();

      const paintCallback = observerCallbacks.get("paint");
      paintCallback?.({
        getEntries: () => [
          { name: "first-contentful-paint", startTime: 500 },
        ],
      });

      expect(callback).toHaveBeenCalledWith("fcp", 500);
    });

    it("should ignore non-FCP paint entries", () => {
      const tracker = new WebVitalsTracker();
      tracker.start();

      const paintCallback = observerCallbacks.get("paint");
      paintCallback?.({
        getEntries: () => [
          { name: "first-paint", startTime: 100 },
        ],
      });

      const metrics = tracker.getMetrics();
      expect(metrics.fcp).toBeNull();
    });
  });

  describe("LCP Tracking", () => {
    it("should capture LCP value from largest-contentful-paint entries", () => {
      const tracker = new WebVitalsTracker();
      tracker.start();

      const lcpCallback = observerCallbacks.get("largest-contentful-paint");
      lcpCallback?.({
        getEntries: () => [
          { startTime: 2500, size: 1000 },
        ],
      });

      const metrics = tracker.getMetrics();
      expect(metrics.lcp).toBe(2500);
    });

    it("should use latest LCP value when multiple entries", () => {
      const tracker = new WebVitalsTracker();
      tracker.start();

      const lcpCallback = observerCallbacks.get("largest-contentful-paint");

      // First LCP
      lcpCallback?.({
        getEntries: () => [{ startTime: 1000, size: 500 }],
      });

      // Second LCP (larger element)
      lcpCallback?.({
        getEntries: () => [{ startTime: 1500, size: 1000 }],
      });

      const metrics = tracker.getMetrics();
      expect(metrics.lcp).toBe(1500);
    });

    it("should handle empty LCP entries array", () => {
      const tracker = new WebVitalsTracker();
      tracker.start();

      const lcpCallback = observerCallbacks.get("largest-contentful-paint");
      lcpCallback?.({
        getEntries: () => [],
      });

      // LCP should remain null when no entries
      const metrics = tracker.getMetrics();
      expect(metrics.lcp).toBeNull();
    });
  });

  describe("CLS Tracking", () => {
    it("should accumulate CLS from layout-shift entries", () => {
      const tracker = new WebVitalsTracker();
      tracker.start();

      const clsCallback = observerCallbacks.get("layout-shift");
      clsCallback?.({
        getEntries: () => [
          { value: 0.1, hadRecentInput: false },
        ],
      });

      const metrics = tracker.getMetrics();
      expect(metrics.cls).toBe(0.1);
    });

    it("should ignore layout shifts with recent input", () => {
      const tracker = new WebVitalsTracker();
      tracker.start();

      const clsCallback = observerCallbacks.get("layout-shift");
      clsCallback?.({
        getEntries: () => [
          { value: 0.5, hadRecentInput: true },
        ],
      });

      const metrics = tracker.getMetrics();
      expect(metrics.cls).toBe(0);
    });

    it("should sum multiple layout shifts", () => {
      const tracker = new WebVitalsTracker();
      tracker.start();

      const clsCallback = observerCallbacks.get("layout-shift");
      
      clsCallback?.({
        getEntries: () => [{ value: 0.1, hadRecentInput: false }],
      });
      
      clsCallback?.({
        getEntries: () => [{ value: 0.05, hadRecentInput: false }],
      });

      const metrics = tracker.getMetrics();
      expect(metrics.cls).toBeCloseTo(0.15, 5);
    });
  });

  describe("Stop Tracking", () => {
    it("should disconnect all observers on stop", () => {
      const tracker = new WebVitalsTracker();
      tracker.start();
      tracker.stop();

      expect(mockDisconnect).toHaveBeenCalled();
    });
  });

  describe("Reset", () => {
    it("should reset all metrics", () => {
      const tracker = new WebVitalsTracker();
      tracker.start();

      // Capture some metrics
      const paintCallback = observerCallbacks.get("paint");
      paintCallback?.({
        getEntries: () => [
          { name: "first-contentful-paint", startTime: 500 },
        ],
      });

      // Reset
      tracker.reset();

      const metrics = tracker.getMetrics();
      expect(metrics.fcp).toBeNull();
      expect(metrics.lcp).toBeNull();
      // CLS resets to 0 (cumulative metric)
      expect(metrics.cls).toBe(0);
    });
  });

  describe("Graceful Degradation", () => {
    it("should handle missing PerformanceObserver", () => {
      vi.stubGlobal("PerformanceObserver", undefined);

      const tracker = new WebVitalsTracker();
      // Should not throw
      expect(() => tracker.start()).not.toThrow();
    });

    it("should handle PerformanceObserver throwing for layout-shift", () => {
      // Mock PerformanceObserver that throws for layout-shift
      class ThrowingObserver {
        private callback: (list: { getEntries: () => object[] }) => void;

        constructor(callback: (list: { getEntries: () => object[] }) => void) {
          this.callback = callback;
        }

        observe(options: { type: string; buffered?: boolean }) {
          if (options.type === "layout-shift") {
            throw new Error("layout-shift not supported");
          }
          observerCallbacks.set(options.type, this.callback);
        }

        disconnect() {}

        static supportedEntryTypes = ["paint", "largest-contentful-paint", "first-input"];
      }

      vi.stubGlobal("PerformanceObserver", ThrowingObserver);

      const tracker = new WebVitalsTracker({ debug: true });
      // Should not throw - catches the error internally
      expect(() => tracker.start()).not.toThrow();
    });

    it("should handle PerformanceObserver throwing for first-input (INP)", () => {
      // Mock PerformanceObserver that throws for first-input
      class ThrowingObserver {
        private callback: (list: { getEntries: () => object[] }) => void;

        constructor(callback: (list: { getEntries: () => object[] }) => void) {
          this.callback = callback;
        }

        observe(options: { type: string; buffered?: boolean }) {
          if (options.type === "first-input") {
            throw new Error("first-input not supported");
          }
          observerCallbacks.set(options.type, this.callback);
        }

        disconnect() {}

        static supportedEntryTypes = ["paint", "largest-contentful-paint", "layout-shift"];
      }

      vi.stubGlobal("PerformanceObserver", ThrowingObserver);

      const tracker = new WebVitalsTracker({ debug: true });
      // Should not throw - catches the error internally
      expect(() => tracker.start()).not.toThrow();
    });

    it("should handle PerformanceObserver throwing for paint (FCP)", () => {
      // Mock PerformanceObserver that throws for paint
      class ThrowingObserver {
        private callback: (list: { getEntries: () => object[] }) => void;

        constructor(callback: (list: { getEntries: () => object[] }) => void) {
          this.callback = callback;
        }

        observe(options: { type: string; buffered?: boolean }) {
          if (options.type === "paint") {
            throw new Error("paint not supported");
          }
          observerCallbacks.set(options.type, this.callback);
        }

        disconnect() {}

        static supportedEntryTypes = ["largest-contentful-paint", "layout-shift", "first-input"];
      }

      vi.stubGlobal("PerformanceObserver", ThrowingObserver);

      const tracker = new WebVitalsTracker({ debug: true });
      // Should not throw - catches the error internally
      expect(() => tracker.start()).not.toThrow();
    });

    it("should handle PerformanceObserver throwing for largest-contentful-paint (LCP)", () => {
      // Mock PerformanceObserver that throws for largest-contentful-paint
      class ThrowingObserver {
        private callback: (list: { getEntries: () => object[] }) => void;

        constructor(callback: (list: { getEntries: () => object[] }) => void) {
          this.callback = callback;
        }

        observe(options: { type: string; buffered?: boolean }) {
          if (options.type === "largest-contentful-paint") {
            throw new Error("LCP not supported");
          }
          observerCallbacks.set(options.type, this.callback);
        }

        disconnect() {}

        static supportedEntryTypes = ["paint", "layout-shift", "first-input"];
      }

      vi.stubGlobal("PerformanceObserver", ThrowingObserver);

      const tracker = new WebVitalsTracker({ debug: true });
      // Should not throw - catches the error internally
      expect(() => tracker.start()).not.toThrow();
    });
  });

  describe("toJSON", () => {
    it("should export metrics as JSON", () => {
      const tracker = new WebVitalsTracker();
      tracker.start();

      const paintCallback = observerCallbacks.get("paint");
      paintCallback?.({
        getEntries: () => [
          { name: "first-contentful-paint", startTime: 800 },
        ],
      });

      const json = tracker.toJSON();
      expect(JSON.parse(json)).toEqual({
        fcp: 800,
        lcp: null,
        cls: 0,
        inp: null,
        timestamp: expect.any(Number),
      });
    });
  });

  describe("Navigation Timing", () => {
    it("should capture navigation timing from performance.timing", () => {
      // Mock performance.timing
      const mockTiming = {
        navigationStart: 0,
        domContentLoadedEventEnd: 500,
        loadEventEnd: 1000,
        responseEnd: 300,
        requestStart: 100,
        connectEnd: 80,
        connectStart: 50,
        domainLookupEnd: 40,
        domainLookupStart: 20,
        redirectEnd: 0,
        redirectStart: 0,
        fetchStart: 10,
      };

      vi.stubGlobal("performance", {
        timing: mockTiming,
        now: () => 1500,
      });

      const tracker = new WebVitalsTracker();
      const navTiming = tracker.getNavigationTiming();

      expect(navTiming).not.toBeNull();
      expect(navTiming?.domContentLoaded).toBe(500);
      expect(navTiming?.loadComplete).toBe(1000);
    });

    it("should calculate TTFB correctly", () => {
      const mockTiming = {
        navigationStart: 0,
        domContentLoadedEventEnd: 500,
        loadEventEnd: 1000,
        responseStart: 250,
        requestStart: 100,
        connectEnd: 80,
        connectStart: 50,
        domainLookupEnd: 40,
        domainLookupStart: 20,
        redirectEnd: 0,
        redirectStart: 0,
        fetchStart: 10,
      };

      vi.stubGlobal("performance", {
        timing: mockTiming,
        now: () => 1500,
      });

      const tracker = new WebVitalsTracker();
      const navTiming = tracker.getNavigationTiming();

      expect(navTiming?.ttfb).toBe(250); // responseStart - navigationStart
    });

    it("should calculate DNS lookup time", () => {
      const mockTiming = {
        navigationStart: 0,
        domContentLoadedEventEnd: 500,
        loadEventEnd: 1000,
        responseStart: 250,
        requestStart: 100,
        connectEnd: 80,
        connectStart: 50,
        domainLookupEnd: 40,
        domainLookupStart: 20,
        redirectEnd: 0,
        redirectStart: 0,
        fetchStart: 10,
      };

      vi.stubGlobal("performance", {
        timing: mockTiming,
        now: () => 1500,
      });

      const tracker = new WebVitalsTracker();
      const navTiming = tracker.getNavigationTiming();

      expect(navTiming?.dnsLookup).toBe(20); // domainLookupEnd - domainLookupStart
    });

    it("should calculate TCP connection time", () => {
      const mockTiming = {
        navigationStart: 0,
        domContentLoadedEventEnd: 500,
        loadEventEnd: 1000,
        responseStart: 250,
        requestStart: 100,
        connectEnd: 80,
        connectStart: 50,
        domainLookupEnd: 40,
        domainLookupStart: 20,
        redirectEnd: 0,
        redirectStart: 0,
        fetchStart: 10,
      };

      vi.stubGlobal("performance", {
        timing: mockTiming,
        now: () => 1500,
      });

      const tracker = new WebVitalsTracker();
      const navTiming = tracker.getNavigationTiming();

      expect(navTiming?.tcpConnect).toBe(30); // connectEnd - connectStart
    });

    it("should return null when performance.timing is not available", () => {
      vi.stubGlobal("performance", {
        now: () => 1500,
        timing: undefined,
      });

      const tracker = new WebVitalsTracker();
      const navTiming = tracker.getNavigationTiming();

      expect(navTiming).toBeNull();
    });

    it("should handle performance API not available", () => {
      vi.stubGlobal("performance", undefined);

      const tracker = new WebVitalsTracker();
      const navTiming = tracker.getNavigationTiming();

      expect(navTiming).toBeNull();
    });

    it("should fallback to 0 for missing timing properties", () => {
      // Only provide partial timing data - missing loadEventEnd and responseEnd
      const mockTiming = {
        navigationStart: 100,
        domContentLoadedEventEnd: 500,
        // loadEventEnd missing - should fallback to 0
        responseStart: 200,
        requestStart: 150,
        connectEnd: 130,
        connectStart: 110,
        domainLookupEnd: 105,
        domainLookupStart: 102,
        redirectEnd: 0,
        redirectStart: 0,
        // responseEnd missing - should fallback to 0
      };

      vi.stubGlobal("performance", {
        timing: mockTiming,
        now: () => 1500,
      });

      const tracker = new WebVitalsTracker();
      const navTiming = tracker.getNavigationTiming();

      expect(navTiming).not.toBeNull();
      expect(navTiming?.loadComplete).toBe(0); // loadEventEnd fallback
      expect(navTiming?.requestTime).toBe(-150); // (0 - 150) since responseEnd is missing
    });
  });

  describe("INP Tracking", () => {
    it("should capture INP from first-input entries", () => {
      const tracker = new WebVitalsTracker();
      tracker.start();

      const inpCallback = observerCallbacks.get("first-input");
      inpCallback?.({
        getEntries: () => [{ duration: 100, processingStart: 50 }],
      });

      const metrics = tracker.getMetrics();
      expect(metrics.inp).toBe(100);
    });

    it("should track worst INP value", () => {
      const tracker = new WebVitalsTracker();
      tracker.start();

      const inpCallback = observerCallbacks.get("first-input");

      // First interaction
      inpCallback?.({
        getEntries: () => [{ duration: 50, processingStart: 25 }],
      });

      // Worse interaction
      inpCallback?.({
        getEntries: () => [{ duration: 150, processingStart: 75 }],
      });

      const metrics = tracker.getMetrics();
      expect(metrics.inp).toBe(150);
    });

    it("should not downgrade INP with better values", () => {
      const tracker = new WebVitalsTracker();
      tracker.start();

      const inpCallback = observerCallbacks.get("first-input");

      // Bad interaction first
      inpCallback?.({
        getEntries: () => [{ duration: 200, processingStart: 100 }],
      });

      // Better interaction after
      inpCallback?.({
        getEntries: () => [{ duration: 50, processingStart: 25 }],
      });

      const metrics = tracker.getMetrics();
      // Should keep worst value
      expect(metrics.inp).toBe(200);
    });
  });
});
