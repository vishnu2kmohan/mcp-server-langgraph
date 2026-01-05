/**
 * useWebSocketMetricsPush Hook
 *
 * Periodically pushes WebSocket reconnection metrics from Redux store
 * to the backend Prometheus exporter.
 *
 * Flow:
 *   Redux (observabilitySlice.webSocketMetrics)
 *     -> POST /api/v1/websocket/metrics/batch
 *     -> Backend Prometheus metrics
 *     -> Grafana dashboard
 *
 * Usage:
 *   // In App.tsx or a top-level component
 *   useWebSocketMetricsPush({ enabled: true, intervalMs: 30000 });
 */

import { useCallback, useEffect, useRef, useState } from "react";
import { useSelector } from "react-redux";
import type { RootState } from "../store";

export interface UseWebSocketMetricsPushOptions {
  /** Enable periodic pushing (default: true) */
  enabled?: boolean;
  /** Push interval in milliseconds (default: 30000 = 30s) */
  intervalMs?: number;
}

export interface UseWebSocketMetricsPushResult {
  /** Manually trigger a push */
  pushNow: () => Promise<void>;
  /** Timestamp of last successful push */
  lastPushTime: number | null;
  /** Whether a push is currently in progress */
  isPushing: boolean;
}

/**
 * Hook to periodically push WebSocket metrics to backend.
 */
export function useWebSocketMetricsPush(
  options: UseWebSocketMetricsPushOptions = {},
): UseWebSocketMetricsPushResult {
  const { enabled = true, intervalMs = 30000 } = options;

  const [lastPushTime, setLastPushTime] = useState<number | null>(null);
  const [isPushing, setIsPushing] = useState(false);
  const intervalRef = useRef<ReturnType<typeof setInterval> | null>(null);

  // Get metrics from Redux store
  const webSocketMetrics = useSelector(
    (state: RootState) => state.observability.webSocketMetrics,
  );

  // Get auth state - derive isAuthenticated from tokens presence
  const tokens = useSelector((state: RootState) => state.auth.tokens);
  const isAuthenticated = tokens !== null;
  const token = tokens?.accessToken;

  /**
   * Push metrics to backend
   */
  const pushMetrics = useCallback(async (): Promise<boolean> => {
    // Skip if not authenticated
    if (!isAuthenticated || !token) {
      return false;
    }

    // Skip if no metrics
    const endpointIds = Object.keys(webSocketMetrics);
    if (endpointIds.length === 0) {
      return false;
    }

    // Build batch payload
    const endpoints = endpointIds.map((endpointId) => {
      const entry = webSocketMetrics[endpointId];
      const metrics = entry.metrics;

      return {
        endpoint_id: endpointId,
        total_attempts: metrics.totalAttempts,
        total_reconnections: metrics.totalReconnections,
        consecutive_failures: metrics.consecutiveFailures,
        success_rate: metrics.successRate,
        failures_by_reason: metrics.failuresByReason,
        avg_reconnection_duration_ms:
          metrics.avgReconnectionDurationMs ?? undefined,
      };
    });

    const payload = { endpoints };

    try {
      setIsPushing(true);

      const response = await fetch("/api/v1/websocket/metrics/batch", {
        method: "POST",
        headers: {
          "Content-Type": "application/json",
          Authorization: `Bearer ${token}`,
        },
        body: JSON.stringify(payload),
      });

      if (response.ok) {
        setLastPushTime(Date.now());
        return true;
      } else {
        console.warn(
          `Failed to push WebSocket metrics: ${response.status} ${response.statusText}`,
        );
        return false;
      }
    } catch (error) {
      console.warn("Error pushing WebSocket metrics:", error);
      return false;
    } finally {
      setIsPushing(false);
    }
  }, [isAuthenticated, token, webSocketMetrics]);

  /**
   * Manual push function
   */
  const pushNow = useCallback(async (): Promise<void> => {
    await pushMetrics();
  }, [pushMetrics]);

  // Set up periodic push
  useEffect(() => {
    if (!enabled || !isAuthenticated) {
      // Clear any existing interval
      if (intervalRef.current) {
        clearInterval(intervalRef.current);
        intervalRef.current = null;
      }
      return;
    }

    // Set up interval
    intervalRef.current = setInterval(() => {
      pushMetrics();
    }, intervalMs);

    // Cleanup on unmount or when deps change
    return () => {
      if (intervalRef.current) {
        clearInterval(intervalRef.current);
        intervalRef.current = null;
      }
    };
  }, [enabled, isAuthenticated, intervalMs, pushMetrics]);

  return {
    pushNow,
    lastPushTime,
    isPushing,
  };
}
