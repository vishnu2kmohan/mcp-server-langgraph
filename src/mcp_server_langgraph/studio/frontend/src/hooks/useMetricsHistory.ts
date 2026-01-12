/**
 * useMetricsHistory Hook
 *
 * Tracks metrics snapshots over time to compute trends, sparklines,
 * and percentage changes. Extracted from DevToolsPanel for reusability.
 *
 * Features:
 * - Configurable max snapshots (default: 10)
 * - Configurable deduplication interval (default: 5s)
 * - Trend computation: up/down/stable
 * - Percentage change calculation
 * - Sparkline data extraction
 */

import { useRef, useCallback } from "react";

export type TrendDirection = "up" | "down" | "stable";

export interface MetricsSnapshot {
  requestsTotal: number;
  errorsTotal: number;
  avgLatencyMs: number;
  p99LatencyMs: number;
  tokensUsed: number;
  activeSessions: number;
  timestamp: number;
}

export interface MetricWithTrend {
  name: string;
  value: number;
  unit: string;
  trend: TrendDirection;
  change: number;
  sparkline: number[];
}

export interface UseMetricsHistoryOptions {
  /** Maximum number of snapshots to keep (default: 10) */
  maxSnapshots?: number;
  /** Minimum interval between snapshots in ms (default: 5000) */
  dedupeInterval?: number;
  /** Threshold for trend detection (default: 0.05 = 5%) */
  trendThreshold?: number;
}

export interface UseMetricsHistoryResult {
  /** Current history of snapshots */
  history: MetricsSnapshot[];
  /** Add a new snapshot (will dedupe based on interval) */
  addSnapshot: (snapshot: Omit<MetricsSnapshot, "timestamp">) => void;
  /** Clear all history */
  clearHistory: () => void;
  /** Compute trend direction from an array of values */
  computeTrend: (values: number[]) => TrendDirection;
  /** Compute percentage change from an array of values */
  computeChange: (values: number[]) => number;
  /** Get sparkline for a specific metric */
  getSparkline: (key: keyof Omit<MetricsSnapshot, "timestamp">) => number[];
  /** Get formatted metrics with trends and sparklines */
  getMetricsWithTrends: (
    currentMetrics: Omit<MetricsSnapshot, "timestamp"> | null,
  ) => MetricWithTrend[];
}

export function useMetricsHistory(
  options: UseMetricsHistoryOptions = {},
): UseMetricsHistoryResult {
  const {
    maxSnapshots = 10,
    dedupeInterval = 5000,
    trendThreshold = 0.05,
  } = options;

  const historyRef = useRef<MetricsSnapshot[]>([]);

  // Compute trend from history values
  const computeTrend = useCallback(
    (values: number[]): TrendDirection => {
      if (values.length < 2) return "stable";
      const first = values[0];
      const last = values[values.length - 1];
      if (first === 0) return last > 0 ? "up" : "stable";
      const change = (last - first) / Math.abs(first);
      if (change > trendThreshold) return "up";
      if (change < -trendThreshold) return "down";
      return "stable";
    },
    [trendThreshold],
  );

  // Compute percentage change from history values
  const computeChange = useCallback((values: number[]): number => {
    if (values.length < 2) return 0;
    const first = values[0];
    const last = values[values.length - 1];
    if (first === 0) return last > 0 ? 100 : 0;
    return Math.round(((last - first) / Math.abs(first)) * 100);
  }, []);

  // Add a new snapshot with deduplication
  const addSnapshot = useCallback(
    (snapshot: Omit<MetricsSnapshot, "timestamp">) => {
      const history = historyRef.current;
      const now = Date.now();

      // Dedupe: only add if last entry is older than dedupeInterval
      if (
        history.length === 0 ||
        now - history[history.length - 1].timestamp > dedupeInterval
      ) {
        history.push({
          ...snapshot,
          timestamp: now,
        });
        // Keep only last maxSnapshots
        if (history.length > maxSnapshots) {
          history.shift();
        }
      }
    },
    [dedupeInterval, maxSnapshots],
  );

  // Clear all history (mutate in place to preserve reference)
  const clearHistory = useCallback(() => {
    historyRef.current.length = 0;
  }, []);

  // Get sparkline for a specific metric
  const getSparkline = useCallback(
    (key: keyof Omit<MetricsSnapshot, "timestamp">): number[] => {
      return historyRef.current.map((h) => h[key] as number);
    },
    [],
  );

  // Get formatted metrics with trends and sparklines
  const getMetricsWithTrends = useCallback(
    (
      currentMetrics: Omit<MetricsSnapshot, "timestamp"> | null,
    ): MetricWithTrend[] => {
      if (!currentMetrics) return [];
      const history = historyRef.current;

      // Extract sparklines from history
      const requestsSparkline = history.map((h) => h.requestsTotal);
      const errorsSparkline = history.map((h) => h.errorsTotal);
      const avgLatencySparkline = history.map((h) => h.avgLatencyMs);
      const p99LatencySparkline = history.map((h) => h.p99LatencyMs);
      const tokensSparkline = history.map((h) => h.tokensUsed);
      const sessionsSparkline = history.map((h) => h.activeSessions);

      return [
        {
          name: "requests_total",
          value: currentMetrics.requestsTotal,
          unit: "req",
          trend: computeTrend(requestsSparkline),
          change: computeChange(requestsSparkline),
          sparkline:
            requestsSparkline.length > 0
              ? requestsSparkline
              : [currentMetrics.requestsTotal],
        },
        {
          name: "errors_total",
          value: currentMetrics.errorsTotal,
          unit: "err",
          trend: computeTrend(errorsSparkline),
          change: computeChange(errorsSparkline),
          sparkline:
            errorsSparkline.length > 0
              ? errorsSparkline
              : [currentMetrics.errorsTotal],
        },
        {
          name: "avg_latency",
          value: Math.round(currentMetrics.avgLatencyMs),
          unit: "ms",
          trend: computeTrend(avgLatencySparkline),
          change: computeChange(avgLatencySparkline),
          sparkline:
            avgLatencySparkline.length > 0
              ? avgLatencySparkline
              : [currentMetrics.avgLatencyMs],
        },
        {
          name: "p99_latency",
          value: Math.round(currentMetrics.p99LatencyMs),
          unit: "ms",
          trend: computeTrend(p99LatencySparkline),
          change: computeChange(p99LatencySparkline),
          sparkline:
            p99LatencySparkline.length > 0
              ? p99LatencySparkline
              : [currentMetrics.p99LatencyMs],
        },
        {
          name: "tokens_used",
          value: currentMetrics.tokensUsed,
          unit: "tokens",
          trend: computeTrend(tokensSparkline),
          change: computeChange(tokensSparkline),
          sparkline:
            tokensSparkline.length > 0
              ? tokensSparkline
              : [currentMetrics.tokensUsed],
        },
        {
          name: "active_sessions",
          value: currentMetrics.activeSessions,
          unit: "sessions",
          trend: computeTrend(sessionsSparkline),
          change: computeChange(sessionsSparkline),
          sparkline:
            sessionsSparkline.length > 0
              ? sessionsSparkline
              : [currentMetrics.activeSessions],
        },
      ];
    },
    [computeTrend, computeChange],
  );

  return {
    history: historyRef.current,
    addSnapshot,
    clearHistory,
    computeTrend,
    computeChange,
    getSparkline,
    getMetricsWithTrends,
  };
}

export default useMetricsHistory;
