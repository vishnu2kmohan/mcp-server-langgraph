/**
 * useAIMetrics
 *
 * Metrics tracking hook for AI Intelligence features.
 * Provides observability into AI feature usage, performance, and errors.
 *
 * Features:
 * - Track AI feature usage counts
 * - Track request latencies
 * - Track error rates
 * - Track cache hit/miss ratios
 * - Per-feature metrics breakdown
 * - Event callbacks for integration with observability systems
 */

import { useCallback, useMemo, useRef } from "react";

// =============================================================================
// Types
// =============================================================================

export type AIMetricsEventType =
  | "request"
  | "error"
  | "cache_hit"
  | "cache_miss";

export interface AIMetricsEvent {
  /** Type of event */
  type: AIMetricsEventType;
  /** Feature name (e.g., nav_prediction, contextual_help) */
  feature: string;
  /** Timestamp of the event */
  timestamp: number;
  /** Request latency in ms (for request events) */
  latency?: number;
  /** Error object (for error events) */
  error?: Error;
}

export interface AIMetricsSnapshot {
  /** Total number of requests */
  requestCount: number;
  /** Total number of errors */
  errorCount: number;
  /** Total cache hits */
  cacheHits: number;
  /** Total cache misses */
  cacheMisses: number;
  /** Average latency in ms */
  averageLatency: number;
  /** Error rate (0-1) */
  errorRate: number;
  /** Cache hit ratio (0-1) */
  cacheHitRatio: number;
  /** Snapshot timestamp */
  timestamp: number;
}

export interface FeatureMetrics {
  /** Number of requests for this feature */
  requestCount: number;
  /** Number of errors for this feature */
  errorCount: number;
  /** Average latency for this feature */
  averageLatency: number;
  /** Total latency (for calculating average) */
  totalLatency: number;
}

export interface UseAIMetricsOptions {
  /** Callback when a metric event occurs */
  onEvent?: (event: AIMetricsEvent) => void;
}

export interface UseAIMetricsResult {
  /** Track a successful request */
  trackRequest: (feature: string, latencyMs: number) => void;
  /** Track an error */
  trackError: (feature: string, error: Error) => void;
  /** Track a cache hit */
  trackCacheHit: (feature: string) => void;
  /** Track a cache miss */
  trackCacheMiss: (feature: string) => void;
  /** Get current metrics snapshot */
  getSnapshot: () => AIMetricsSnapshot;
  /** Get metrics for a specific feature */
  getFeatureMetrics: (feature: string) => FeatureMetrics;
  /** Reset all metrics */
  reset: () => void;
}

// =============================================================================
// Internal Metrics Store
// =============================================================================

interface MetricsStore {
  requestCount: number;
  errorCount: number;
  cacheHits: number;
  cacheMisses: number;
  totalLatency: number;
  features: Map<string, FeatureMetrics>;
}

function createInitialStore(): MetricsStore {
  return {
    requestCount: 0,
    errorCount: 0,
    cacheHits: 0,
    cacheMisses: 0,
    totalLatency: 0,
    features: new Map(),
  };
}

function getOrCreateFeatureMetrics(
  store: MetricsStore,
  feature: string,
): FeatureMetrics {
  let metrics = store.features.get(feature);
  if (!metrics) {
    metrics = {
      requestCount: 0,
      errorCount: 0,
      averageLatency: 0,
      totalLatency: 0,
    };
    store.features.set(feature, metrics);
  }
  return metrics;
}

// =============================================================================
// Standalone Tracker Factory
// =============================================================================

export type AIMetricsTracker = UseAIMetricsResult;

export interface CreateAIMetricsTrackerOptions {
  /** Callback when a metric event occurs */
  onEvent?: (event: AIMetricsEvent) => void;
}

/**
 * Create a standalone metrics tracker (for use outside React components)
 */
export function createAIMetricsTracker(
  options: CreateAIMetricsTrackerOptions = {},
): AIMetricsTracker {
  const { onEvent } = options;
  let store = createInitialStore();

  const emitEvent = (event: AIMetricsEvent) => {
    onEvent?.(event);
  };

  const trackRequest = (feature: string, latencyMs: number) => {
    store.requestCount++;
    store.totalLatency += latencyMs;

    const featureMetrics = getOrCreateFeatureMetrics(store, feature);
    featureMetrics.requestCount++;
    featureMetrics.totalLatency += latencyMs;
    featureMetrics.averageLatency =
      featureMetrics.totalLatency / featureMetrics.requestCount;

    emitEvent({
      type: "request",
      feature,
      timestamp: Date.now(),
      latency: latencyMs,
    });
  };

  const trackError = (feature: string, error: Error) => {
    store.errorCount++;

    const featureMetrics = getOrCreateFeatureMetrics(store, feature);
    featureMetrics.errorCount++;

    emitEvent({
      type: "error",
      feature,
      timestamp: Date.now(),
      error,
    });
  };

  const trackCacheHit = (feature: string) => {
    store.cacheHits++;
    emitEvent({
      type: "cache_hit",
      feature,
      timestamp: Date.now(),
    });
  };

  const trackCacheMiss = (feature: string) => {
    store.cacheMisses++;
    emitEvent({
      type: "cache_miss",
      feature,
      timestamp: Date.now(),
    });
  };

  const getSnapshot = (): AIMetricsSnapshot => {
    const totalEvents = store.requestCount + store.errorCount;
    const totalCacheOps = store.cacheHits + store.cacheMisses;

    return {
      requestCount: store.requestCount,
      errorCount: store.errorCount,
      cacheHits: store.cacheHits,
      cacheMisses: store.cacheMisses,
      averageLatency:
        store.requestCount > 0 ? store.totalLatency / store.requestCount : 0,
      errorRate: totalEvents > 0 ? store.errorCount / totalEvents : 0,
      cacheHitRatio: totalCacheOps > 0 ? store.cacheHits / totalCacheOps : 0,
      timestamp: Date.now(),
    };
  };

  const getFeatureMetrics = (feature: string): FeatureMetrics => {
    return (
      store.features.get(feature) ?? {
        requestCount: 0,
        errorCount: 0,
        averageLatency: 0,
        totalLatency: 0,
      }
    );
  };

  const reset = () => {
    store = createInitialStore();
  };

  return {
    trackRequest,
    trackError,
    trackCacheHit,
    trackCacheMiss,
    getSnapshot,
    getFeatureMetrics,
    reset,
  };
}

// =============================================================================
// React Hook
// =============================================================================

/**
 * Hook for tracking AI feature metrics.
 *
 * @param options - Configuration options
 * @returns Metrics tracking functions and snapshot getter
 *
 * @example
 * ```tsx
 * const { trackRequest, trackError, getSnapshot } = useAIMetrics({
 *   onEvent: (event) => console.log('AI Metric:', event),
 * });
 *
 * // Track a successful request
 * trackRequest('nav_prediction', 150);
 *
 * // Track an error
 * trackError('nav_prediction', new Error('Failed'));
 *
 * // Get current metrics
 * const metrics = getSnapshot();
 * console.log(`Error rate: ${metrics.errorRate * 100}%`);
 * ```
 */
export function useAIMetrics(
  options: UseAIMetricsOptions = {},
): UseAIMetricsResult {
  const { onEvent } = options;

  // Use ref to maintain stable store across renders
  const storeRef = useRef<MetricsStore>(createInitialStore());
  const onEventRef = useRef(onEvent);
  onEventRef.current = onEvent;

  const emitEvent = useCallback((event: AIMetricsEvent) => {
    onEventRef.current?.(event);
  }, []);

  const trackRequest = useCallback(
    (feature: string, latencyMs: number) => {
      const store = storeRef.current;
      store.requestCount++;
      store.totalLatency += latencyMs;

      const featureMetrics = getOrCreateFeatureMetrics(store, feature);
      featureMetrics.requestCount++;
      featureMetrics.totalLatency += latencyMs;
      featureMetrics.averageLatency =
        featureMetrics.totalLatency / featureMetrics.requestCount;

      emitEvent({
        type: "request",
        feature,
        timestamp: Date.now(),
        latency: latencyMs,
      });
    },
    [emitEvent],
  );

  const trackError = useCallback(
    (feature: string, error: Error) => {
      const store = storeRef.current;
      store.errorCount++;

      const featureMetrics = getOrCreateFeatureMetrics(store, feature);
      featureMetrics.errorCount++;

      emitEvent({
        type: "error",
        feature,
        timestamp: Date.now(),
        error,
      });
    },
    [emitEvent],
  );

  const trackCacheHit = useCallback(
    (feature: string) => {
      storeRef.current.cacheHits++;
      emitEvent({
        type: "cache_hit",
        feature,
        timestamp: Date.now(),
      });
    },
    [emitEvent],
  );

  const trackCacheMiss = useCallback(
    (feature: string) => {
      storeRef.current.cacheMisses++;
      emitEvent({
        type: "cache_miss",
        feature,
        timestamp: Date.now(),
      });
    },
    [emitEvent],
  );

  const getSnapshot = useCallback((): AIMetricsSnapshot => {
    const store = storeRef.current;
    const totalEvents = store.requestCount + store.errorCount;
    const totalCacheOps = store.cacheHits + store.cacheMisses;

    return {
      requestCount: store.requestCount,
      errorCount: store.errorCount,
      cacheHits: store.cacheHits,
      cacheMisses: store.cacheMisses,
      averageLatency:
        store.requestCount > 0 ? store.totalLatency / store.requestCount : 0,
      errorRate: totalEvents > 0 ? store.errorCount / totalEvents : 0,
      cacheHitRatio: totalCacheOps > 0 ? store.cacheHits / totalCacheOps : 0,
      timestamp: Date.now(),
    };
  }, []);

  const getFeatureMetrics = useCallback((feature: string): FeatureMetrics => {
    return (
      storeRef.current.features.get(feature) ?? {
        requestCount: 0,
        errorCount: 0,
        averageLatency: 0,
        totalLatency: 0,
      }
    );
  }, []);

  const reset = useCallback(() => {
    storeRef.current = createInitialStore();
  }, []);

  return useMemo(
    () => ({
      trackRequest,
      trackError,
      trackCacheHit,
      trackCacheMiss,
      getSnapshot,
      getFeatureMetrics,
      reset,
    }),
    [
      trackRequest,
      trackError,
      trackCacheHit,
      trackCacheMiss,
      getSnapshot,
      getFeatureMetrics,
      reset,
    ],
  );
}
