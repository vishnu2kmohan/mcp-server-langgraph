/**
 * useAICacheMetrics Hook
 *
 * Provides a convenient wrapper around useAIMetrics specifically for
 * AI cache performance monitoring. Tracks cache hits/misses, latency,
 * and error rates with per-feature breakdown.
 *
 * Features:
 * - Real-time cache hit/miss tracking
 * - Per-feature metrics breakdown
 * - Snapshot getter for dashboard display
 * - Optional metrics update callback
 *
 * @example
 * ```tsx
 * const {
 *   snapshot,
 *   featureMetrics,
 *   trackCacheHit,
 *   trackCacheMiss,
 *   trackRequest,
 *   trackError,
 *   reset,
 * } = useAICacheMetrics();
 *
 * // Track a cache hit
 * trackCacheHit('nav_prediction');
 *
 * // Display metrics
 * <AICacheMetricsDashboard
 *   snapshot={snapshot}
 *   featureMetrics={featureMetrics}
 * />
 * ```
 */

import { useCallback, useRef, useMemo, useState } from "react";
import type { AIMetricsSnapshot, FeatureMetrics } from "./useAIMetrics";
import type { CacheStats } from "./useTieredCache";

// =============================================================================
// Types
// =============================================================================

export interface UseAICacheMetricsOptions {
  /** Callback when metrics are updated */
  onMetricsUpdate?: (snapshot: AIMetricsSnapshot) => void;
}

/**
 * Tiered cache statistics (L1 in-memory, L2 sessionStorage).
 * Re-exported from useTieredCache for backwards compatibility.
 */
export type TieredCacheStats = CacheStats;

export interface UseAICacheMetricsResult {
  /** Current metrics snapshot */
  snapshot: AIMetricsSnapshot;
  /** Per-feature metrics */
  featureMetrics: Record<string, FeatureMetrics>;
  /** Tiered cache statistics (L1/L2 breakdown) */
  tieredCacheStats: TieredCacheStats;
  /** Track a cache hit (generic) */
  trackCacheHit: (feature: string) => void;
  /** Track a cache miss (generic) */
  trackCacheMiss: (feature: string) => void;
  /** Track L1 (in-memory) cache hit */
  trackL1Hit: (feature: string) => void;
  /** Track L2 (sessionStorage) cache hit */
  trackL2Hit: (feature: string) => void;
  /** Track tiered cache miss */
  trackTieredMiss: (feature: string) => void;
  /** Track a successful request with latency */
  trackRequest: (feature: string, latencyMs: number) => void;
  /** Track an error */
  trackError: (feature: string, error: Error) => void;
  /** Reset all metrics */
  reset: () => void;
}

// =============================================================================
// Internal Store
// =============================================================================

interface MetricsStore {
  requestCount: number;
  errorCount: number;
  cacheHits: number;
  cacheMisses: number;
  totalLatency: number;
  features: Map<string, FeatureMetrics>;
  // Tiered cache tracking
  l1Hits: number;
  l2Hits: number;
  tieredMisses: number;
  firstOperationTime: number | null;
}

function createInitialStore(): MetricsStore {
  return {
    requestCount: 0,
    errorCount: 0,
    cacheHits: 0,
    cacheMisses: 0,
    totalLatency: 0,
    features: new Map(),
    // Tiered cache stats
    l1Hits: 0,
    l2Hits: 0,
    tieredMisses: 0,
    firstOperationTime: null,
  };
}

function getOrCreateFeatureMetrics(
  store: MetricsStore,
  feature: string
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

function computeSnapshot(store: MetricsStore): AIMetricsSnapshot {
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
}

// =============================================================================
// Hook Implementation
// =============================================================================

export function useAICacheMetrics(
  options: UseAICacheMetricsOptions = {}
): UseAICacheMetricsResult {
  const { onMetricsUpdate } = options;

  // Store reference
  const storeRef = useRef<MetricsStore>(createInitialStore());

  // Update counter to trigger re-renders
  const [updateCount, setUpdateCount] = useState(0);

  // Callback ref to avoid stale closures
  const onMetricsUpdateRef = useRef(onMetricsUpdate);
  onMetricsUpdateRef.current = onMetricsUpdate;

  // Helper to trigger update
  const triggerUpdate = useCallback(() => {
    setUpdateCount((c) => c + 1);
    const snapshot = computeSnapshot(storeRef.current);
    onMetricsUpdateRef.current?.(snapshot);
  }, []);

  // Track cache hit
  const trackCacheHit = useCallback(
    (feature: string) => {
      storeRef.current.cacheHits++;
      // Also track in feature metrics if needed
      getOrCreateFeatureMetrics(storeRef.current, feature);
      triggerUpdate();
    },
    [triggerUpdate]
  );

  // Track cache miss
  const trackCacheMiss = useCallback(
    (feature: string) => {
      storeRef.current.cacheMisses++;
      getOrCreateFeatureMetrics(storeRef.current, feature);
      triggerUpdate();
    },
    [triggerUpdate]
  );

  // Track L1 (in-memory) cache hit
  const trackL1Hit = useCallback(
    (feature: string) => {
      const store = storeRef.current;
      store.l1Hits++;
      store.cacheHits++; // L1 hits also count as total cache hits
      if (store.firstOperationTime === null) {
        store.firstOperationTime = Date.now();
      }
      getOrCreateFeatureMetrics(store, feature);
      triggerUpdate();
    },
    [triggerUpdate]
  );

  // Track L2 (sessionStorage) cache hit
  const trackL2Hit = useCallback(
    (feature: string) => {
      const store = storeRef.current;
      store.l2Hits++;
      store.cacheHits++; // L2 hits also count as total cache hits
      if (store.firstOperationTime === null) {
        store.firstOperationTime = Date.now();
      }
      getOrCreateFeatureMetrics(store, feature);
      triggerUpdate();
    },
    [triggerUpdate]
  );

  // Track tiered cache miss
  const trackTieredMiss = useCallback(
    (feature: string) => {
      const store = storeRef.current;
      store.tieredMisses++;
      store.cacheMisses++; // Tiered misses also count as total cache misses
      if (store.firstOperationTime === null) {
        store.firstOperationTime = Date.now();
      }
      getOrCreateFeatureMetrics(store, feature);
      triggerUpdate();
    },
    [triggerUpdate]
  );

  // Track request with latency
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

      triggerUpdate();
    },
    [triggerUpdate]
  );

  // Track error
  const trackError = useCallback(
    (feature: string, _error: Error) => {
      const store = storeRef.current;
      store.errorCount++;

      const featureMetrics = getOrCreateFeatureMetrics(store, feature);
      featureMetrics.errorCount++;

      triggerUpdate();
    },
    [triggerUpdate]
  );

  // Reset all metrics
  const reset = useCallback(() => {
    storeRef.current = createInitialStore();
    triggerUpdate();
  }, [triggerUpdate]);

  // Compute current snapshot
  const snapshot = useMemo(
    () => computeSnapshot(storeRef.current),
    // eslint-disable-next-line react-hooks/exhaustive-deps
    [updateCount]
  );

  // Convert feature map to record
  const featureMetrics = useMemo(() => {
    const record: Record<string, FeatureMetrics> = {};
    storeRef.current.features.forEach((metrics, feature) => {
      record[feature] = metrics;
    });
    return record;
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [updateCount]);

  // Compute tiered cache stats
  const tieredCacheStats = useMemo((): TieredCacheStats => {
    const store = storeRef.current;
    const age = store.firstOperationTime !== null
      ? Date.now() - store.firstOperationTime
      : 0;
    return {
      l1Hits: store.l1Hits,
      l2Hits: store.l2Hits,
      misses: store.tieredMisses,
      age,
    };
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [updateCount]);

  return {
    snapshot,
    featureMetrics,
    tieredCacheStats,
    trackCacheHit,
    trackCacheMiss,
    trackL1Hit,
    trackL2Hit,
    trackTieredMiss,
    trackRequest,
    trackError,
    reset,
  };
}

export default useAICacheMetrics;
