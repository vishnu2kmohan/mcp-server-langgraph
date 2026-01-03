/**
 * useWebVitals Hook
 *
 * Core Web Vitals collection with persona context.
 * Uses the web-vitals library to measure real user performance.
 *
 * Core Web Vitals (2024):
 * - LCP (Largest Contentful Paint) - Loading performance
 * - CLS (Cumulative Layout Shift) - Visual stability
 * - INP (Interaction to Next Paint) - Interactivity (replaced FID)
 * - FCP (First Contentful Paint) - Perceived load speed
 * - TTFB (Time to First Byte) - Server response time
 *
 * Privacy:
 * - Respects Do Not Track browser setting
 * - Can be disabled via config
 * - No PII collected
 *
 * @module @mcp-server-langgraph/shared-frontend/hooks
 */

import { useState, useEffect, useCallback, useRef } from "react";
import { onLCP, onCLS, onINP, onFCP, onTTFB } from "web-vitals";
import type { Metric } from "web-vitals";

// =============================================================================
// Types
// =============================================================================

export type MetricName = "LCP" | "CLS" | "INP" | "FCP" | "TTFB";
export type MetricRating = "good" | "needs-improvement" | "poor";

export interface WebVitalMetric {
  /** Metric name (LCP, CLS, etc.) */
  name: MetricName;
  /** Metric value */
  value: number;
  /** Rating based on thresholds */
  rating: MetricRating;
  /** Unique ID for this metric instance */
  id: string;
  /** Navigation type */
  navigationType: string;
  /** Timestamp when collected */
  timestamp: number;
  /** Persona context (if provided) */
  persona?: string;
  /** User ID context (if provided) */
  userId?: string;
}

export interface WebVitalsMetrics {
  LCP?: WebVitalMetric;
  CLS?: WebVitalMetric;
  INP?: WebVitalMetric;
  FCP?: WebVitalMetric;
  TTFB?: WebVitalMetric;
}

export interface WebVitalsExport {
  metrics: WebVitalsMetrics;
  timestamp: number;
  persona?: string;
  userId?: string;
}

export interface WebVitalsConfig {
  /** Enable/disable collection (default: true) */
  enabled?: boolean;
  /** Callback when a metric is collected */
  onMetric?: (metric: WebVitalMetric) => void;
  /** Persona context to include in metrics */
  persona?: string;
  /** User ID to include in metrics */
  userId?: string;
}

export interface WebVitalsResult {
  /** Collected metrics */
  metrics: WebVitalsMetrics;
  /** Whether collection is active */
  isCollecting: boolean;
  /** Export all collected metrics */
  exportMetrics: () => WebVitalsExport;
}

// =============================================================================
// Helpers
// =============================================================================

/**
 * Check if Do Not Track is enabled
 */
function isDoNotTrackEnabled(): boolean {
  if (typeof navigator === "undefined") return false;
  return navigator.doNotTrack === "1" || navigator.doNotTrack === "yes";
}

// =============================================================================
// Hook
// =============================================================================

/**
 * Hook for collecting Core Web Vitals with persona context.
 *
 * @example
 * ```tsx
 * import { useWebVitals } from '@mcp-server-langgraph/shared-frontend/hooks';
 *
 * function App() {
 *   const { metrics, exportMetrics } = useWebVitals({
 *     persona: 'admin',
 *     onMetric: (metric) => {
 *       // Send to analytics backend
 *       sendToAnalytics(metric);
 *     },
 *   });
 *
 *   return (
 *     <div>
 *       {metrics.LCP && <p>LCP: {metrics.LCP.value}ms ({metrics.LCP.rating})</p>}
 *     </div>
 *   );
 * }
 * ```
 */
export function useWebVitals(config: WebVitalsConfig = {}): WebVitalsResult {
  const { enabled = true, onMetric, persona, userId } = config;

  const [metrics, setMetrics] = useState<WebVitalsMetrics>({});
  const onMetricRef = useRef(onMetric);
  const personaRef = useRef(persona);
  const userIdRef = useRef(userId);

  // Update refs when props change
  useEffect(() => {
    onMetricRef.current = onMetric;
    personaRef.current = persona;
    userIdRef.current = userId;
  }, [onMetric, persona, userId]);

  // Determine if we should collect
  const shouldCollect = enabled && !isDoNotTrackEnabled();

  // Handle metric callback
  const handleMetric = useCallback((metric: Metric) => {
    const webVitalMetric: WebVitalMetric = {
      name: metric.name as MetricName,
      value: metric.value,
      rating: metric.rating as MetricRating,
      id: metric.id,
      navigationType: metric.navigationType,
      timestamp: Date.now(),
      ...(personaRef.current && { persona: personaRef.current }),
      ...(userIdRef.current && { userId: userIdRef.current }),
    };

    // Update state
    setMetrics((prev) => ({
      ...prev,
      [metric.name]: webVitalMetric,
    }));

    // Call callback if provided
    onMetricRef.current?.(webVitalMetric);
  }, []);

  // Set up web-vitals listeners
  useEffect(() => {
    if (!shouldCollect) return;

    // Register all Core Web Vitals listeners
    // Note: These are one-time callbacks per page load
    onLCP(handleMetric);
    onCLS(handleMetric);
    onINP(handleMetric);
    onFCP(handleMetric);
    onTTFB(handleMetric);

    // web-vitals doesn't provide a cleanup mechanism
    // The callbacks are automatically cleaned up when the page unloads
  }, [shouldCollect, handleMetric]);

  // Export metrics function
  const exportMetrics = useCallback((): WebVitalsExport => {
    return {
      metrics: { ...metrics },
      timestamp: Date.now(),
      ...(persona && { persona }),
      ...(userId && { userId }),
    };
  }, [metrics, persona, userId]);

  return {
    metrics,
    isCollecting: shouldCollect,
    exportMetrics,
  };
}

export default useWebVitals;
