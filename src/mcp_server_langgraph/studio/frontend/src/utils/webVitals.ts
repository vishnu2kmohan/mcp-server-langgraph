/**
 * Web Vitals Tracker
 *
 * Tracks Core Web Vitals using the native Performance Observer API:
 * - FCP (First Contentful Paint)
 * - LCP (Largest Contentful Paint)
 * - CLS (Cumulative Layout Shift)
 * - INP (Interaction to Next Paint)
 *
 * Usage:
 * ```ts
 * import { webVitals, WebVitalsTracker } from "./webVitals";
 *
 * // Use the singleton
 * webVitals.start();
 * const metrics = webVitals.getMetrics();
 *
 * // Or create custom instance
 * const tracker = new WebVitalsTracker({
 *   onMetric: (name, value) => console.log(name, value),
 * });
 * tracker.start();
 * ```
 */

import { devLogger } from "./devLogger";

// =============================================================================
// Types
// =============================================================================

export interface WebVitalsMetrics {
  /** First Contentful Paint (ms) */
  fcp: number | null;
  /** Largest Contentful Paint (ms) */
  lcp: number | null;
  /** Cumulative Layout Shift (score) */
  cls: number | null;
  /** Interaction to Next Paint (ms) */
  inp: number | null;
}

export type WebVitalsCallback = (
  name: keyof WebVitalsMetrics,
  value: number,
) => void;

export interface WebVitalsTrackerOptions {
  /** Callback when a metric is captured */
  onMetric?: WebVitalsCallback;
  /** Enable debug logging */
  debug?: boolean;
}

interface LayoutShiftEntry extends PerformanceEntry {
  value: number;
  hadRecentInput: boolean;
}

interface LargestContentfulPaintEntry extends PerformanceEntry {
  size: number;
}

interface PerformanceEventTiming extends PerformanceEntry {
  processingStart: number;
  interactionId?: number;
}

export interface NavigationTimingMetrics {
  /** Time to First Byte (ms) */
  ttfb: number;
  /** DNS lookup time (ms) */
  dnsLookup: number;
  /** TCP connection time (ms) */
  tcpConnect: number;
  /** DOMContentLoaded event time (ms) */
  domContentLoaded: number;
  /** Load complete time (ms) */
  loadComplete: number;
  /** Redirect time (ms) */
  redirectTime: number;
  /** Request time (ms) */
  requestTime: number;
}

// =============================================================================
// Implementation
// =============================================================================

const logger = devLogger.withPrefix("[WebVitals]");

/**
 * Check if a PerformanceObserver entry type is supported by the browser.
 * This prevents console warnings like "Ignoring unsupported entryTypes: layout-shift"
 */
function isEntryTypeSupported(entryType: string): boolean {
  try {
    return (
      typeof PerformanceObserver !== "undefined" &&
      typeof PerformanceObserver.supportedEntryTypes !== "undefined" &&
      PerformanceObserver.supportedEntryTypes.includes(entryType)
    );
  } catch {
    return false;
  }
}

export class WebVitalsTracker {
  private options: Required<Omit<WebVitalsTrackerOptions, "onMetric">> & {
    onMetric?: WebVitalsCallback;
  };

  private fcp: number | null = null;
  private lcp: number | null = null;
  private clsValue = 0;
  private inp: number | null = null;

  private observers: PerformanceObserver[] = [];
  private isTracking = false;

  constructor(options: WebVitalsTrackerOptions = {}) {
    this.options = {
      debug: options.debug ?? false,
      onMetric: options.onMetric,
    };
  }

  /**
   * Start tracking Web Vitals
   */
  start(): void {
    // Check if PerformanceObserver is available
    if (typeof PerformanceObserver === "undefined") {
      this.log("PerformanceObserver not available");
      return;
    }

    if (this.isTracking) {
      this.log("Already tracking");
      return;
    }

    this.isTracking = true;
    this.log("Starting Web Vitals tracking");

    // Track FCP
    this.observePaint();

    // Track LCP
    this.observeLCP();

    // Track CLS
    this.observeCLS();

    // Track INP
    this.observeINP();
  }

  /**
   * Stop tracking Web Vitals
   */
  stop(): void {
    this.log("Stopping Web Vitals tracking");
    this.observers.forEach((observer) => observer.disconnect());
    this.observers = [];
    this.isTracking = false;
  }

  /**
   * Reset all metrics
   */
  reset(): void {
    this.fcp = null;
    this.lcp = null;
    this.clsValue = 0;
    this.inp = null;
  }

  /**
   * Get current metrics
   */
  getMetrics(): WebVitalsMetrics {
    return {
      fcp: this.fcp,
      lcp: this.lcp,
      cls: this.clsValue,
      inp: this.inp,
    };
  }

  /**
   * Export metrics as JSON string
   */
  toJSON(): string {
    return JSON.stringify({
      ...this.getMetrics(),
      timestamp: Date.now(),
    });
  }

  /**
   * Get navigation timing metrics
   * Uses the deprecated performance.timing API for broader compatibility
   */
  getNavigationTiming(): NavigationTimingMetrics | null {
    // Check if performance API is available
    if (typeof performance === "undefined" || !performance) {
      return null;
    }

    // Check if timing is available (deprecated but widely supported)
    const timing = performance.timing;
    if (!timing) {
      return null;
    }

    const navigationStart = timing.navigationStart || 0;

    return {
      ttfb: (timing.responseStart || 0) - navigationStart,
      dnsLookup:
        (timing.domainLookupEnd || 0) - (timing.domainLookupStart || 0),
      tcpConnect: (timing.connectEnd || 0) - (timing.connectStart || 0),
      domContentLoaded: timing.domContentLoadedEventEnd || 0,
      loadComplete: timing.loadEventEnd || 0,
      redirectTime: (timing.redirectEnd || 0) - (timing.redirectStart || 0),
      requestTime: (timing.responseEnd || 0) - (timing.requestStart || 0),
    };
  }

  // ===========================================================================
  // Private Methods
  // ===========================================================================

  private observePaint(): void {
    if (!isEntryTypeSupported("paint")) {
      this.log("Paint observer not supported by this browser");
      return;
    }

    try {
      const observer = new PerformanceObserver((list) => {
        for (const entry of list.getEntries()) {
          if (entry.name === "first-contentful-paint") {
            this.fcp = entry.startTime;
            this.log("FCP captured:", this.fcp);
            this.options.onMetric?.("fcp", this.fcp);
          }
        }
      });

      observer.observe({ type: "paint", buffered: true });
      this.observers.push(observer);
    } catch {
      this.log("Paint observer not supported");
    }
  }

  private observeLCP(): void {
    if (!isEntryTypeSupported("largest-contentful-paint")) {
      this.log("LCP observer not supported by this browser");
      return;
    }

    try {
      const observer = new PerformanceObserver((list) => {
        const entries = list.getEntries() as LargestContentfulPaintEntry[];
        if (entries.length > 0) {
          // Use the latest LCP entry
          const lastEntry = entries[entries.length - 1];
          if (!lastEntry) return;
          this.lcp = lastEntry.startTime;
          this.log("LCP captured:", this.lcp);
          this.options.onMetric?.("lcp", this.lcp);
        }
      });

      observer.observe({ type: "largest-contentful-paint", buffered: true });
      this.observers.push(observer);
    } catch {
      this.log("LCP observer not supported");
    }
  }

  private observeCLS(): void {
    if (!isEntryTypeSupported("layout-shift")) {
      this.log("CLS observer not supported by this browser");
      return;
    }

    try {
      const observer = new PerformanceObserver((list) => {
        for (const entry of list.getEntries() as LayoutShiftEntry[]) {
          // Ignore layout shifts caused by user input
          if (!entry.hadRecentInput) {
            this.clsValue += entry.value;
            this.log("CLS updated:", this.clsValue);
            this.options.onMetric?.("cls", this.clsValue);
          }
        }
      });

      observer.observe({ type: "layout-shift", buffered: true });
      this.observers.push(observer);
    } catch {
      this.log("CLS observer not supported");
    }
  }

  private observeINP(): void {
    if (!isEntryTypeSupported("first-input")) {
      this.log("INP observer not supported by this browser");
      return;
    }

    try {
      const observer = new PerformanceObserver((list) => {
        for (const entry of list.getEntries() as PerformanceEventTiming[]) {
          // Calculate interaction latency
          const duration = entry.duration;
          if (this.inp === null || duration > this.inp) {
            this.inp = duration;
            this.log("INP updated:", this.inp);
            this.options.onMetric?.("inp", this.inp);
          }
        }
      });

      observer.observe({ type: "first-input", buffered: true });
      this.observers.push(observer);
    } catch {
      this.log("INP observer not supported");
    }
  }

  private log(message: string, ...args: unknown[]): void {
    if (this.options.debug) {
      logger.debug(message, ...args);
    }
  }
}

// =============================================================================
// Singleton Instance
// =============================================================================

/**
 * Global Web Vitals tracker instance
 */
export const webVitals = new WebVitalsTracker({
  debug: process.env.NODE_ENV === "development",
});
