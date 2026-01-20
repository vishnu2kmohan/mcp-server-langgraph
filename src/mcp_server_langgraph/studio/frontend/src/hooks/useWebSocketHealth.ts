/**
 * useWebSocketHealth Hook
 *
 * Simple hook for deriving WebSocket health metrics from aggregated telemetry.
 * Provides computed values like health status and reconnection rate per minute.
 *
 * For alerts, use useWebSocketHealthAlerts instead.
 */

import { useState, useEffect, useCallback, useMemo, useRef } from "react";
import { websocketTelemetry } from "../utils/websocketTelemetry";
import type { AggregatedWebSocketMetrics } from "../utils/websocketTelemetry";

// =============================================================================
// Types
// =============================================================================

export type HealthStatus = "healthy" | "warning" | "critical" | "unknown";

export interface UseWebSocketHealthOptions {
  /** Callback when reconnection rate exceeds threshold */
  onReconnectionRateExceeded?: (ratePerMinute: number) => void;
  /** Reconnection rate threshold per minute (default: 10) */
  reconnectionRateThreshold?: number;
  /** Refresh interval in ms (default: 5000) */
  refreshInterval?: number;
}

export interface UseWebSocketHealthReturn {
  /** Current health status */
  healthStatus: HealthStatus;
  /** Current aggregated metrics */
  metrics: AggregatedWebSocketMetrics;
  /** Reconnection rate per minute */
  reconnectionRatePerMinute: number;
  /** Whether reconnection rate threshold is exceeded */
  isReconnectionRateExceeded: boolean;
  /** Force refresh metrics */
  refresh: () => void;
}

// =============================================================================
// Utility Functions
// =============================================================================

/**
 * Determine health status from success rate.
 */
function getHealthStatus(avgSuccessRate: number | null): HealthStatus {
  if (avgSuccessRate === null) return "unknown";
  if (avgSuccessRate >= 90) return "healthy";
  if (avgSuccessRate >= 70) return "warning";
  return "critical";
}

// =============================================================================
// Hook Implementation
// =============================================================================

/**
 * Hook for WebSocket health metrics and status.
 */
export function useWebSocketHealth(
  options: UseWebSocketHealthOptions = {},
): UseWebSocketHealthReturn {
  const {
    onReconnectionRateExceeded,
    reconnectionRateThreshold = 10,
    refreshInterval = 5000,
  } = options;

  const [metrics, setMetrics] = useState<AggregatedWebSocketMetrics>(() =>
    websocketTelemetry.getAggregatedMetrics(),
  );

  // Track last reconnection count and time for rate calculation
  const lastReconnectionCountRef = useRef<number>(0);
  const lastCheckTimeRef = useRef<number>(Date.now());
  const [reconnectionRatePerMinute, setReconnectionRatePerMinute] =
    useState<number>(0);

  // Callback ref to avoid stale closure
  const onReconnectionRateExceededRef = useRef(onReconnectionRateExceeded);
  onReconnectionRateExceededRef.current = onReconnectionRateExceeded;

  // Refresh metrics and calculate rate
  const refresh = useCallback(() => {
    const currentMetrics = websocketTelemetry.getAggregatedMetrics();
    const now = Date.now();
    const elapsedMs = now - lastCheckTimeRef.current;

    // Calculate reconnection rate per minute
    if (elapsedMs > 0) {
      const reconnectionDelta =
        currentMetrics.totalReconnectionAttempts -
        lastReconnectionCountRef.current;
      const elapsedMinutes = elapsedMs / 60000;
      const ratePerMinute =
        elapsedMinutes > 0 ? reconnectionDelta / elapsedMinutes : 0;

      setReconnectionRatePerMinute(ratePerMinute);

      // Trigger callback if threshold exceeded
      if (
        ratePerMinute > reconnectionRateThreshold &&
        onReconnectionRateExceededRef.current
      ) {
        onReconnectionRateExceededRef.current(ratePerMinute);
      }

      // Update tracking refs
      lastReconnectionCountRef.current =
        currentMetrics.totalReconnectionAttempts;
      lastCheckTimeRef.current = now;
    }

    setMetrics(currentMetrics);
  }, [reconnectionRateThreshold]);

  // Periodic refresh
  useEffect(() => {
    const intervalId = setInterval(refresh, refreshInterval);
    return () => clearInterval(intervalId);
  }, [refresh, refreshInterval]);

  // Compute health status
  const healthStatus = useMemo(
    () => getHealthStatus(metrics.avgSuccessRate),
    [metrics.avgSuccessRate],
  );

  // Check if reconnection rate is exceeded
  const isReconnectionRateExceeded =
    reconnectionRatePerMinute > reconnectionRateThreshold;

  return {
    healthStatus,
    metrics,
    reconnectionRatePerMinute,
    isReconnectionRateExceeded,
    refresh,
  };
}

export default useWebSocketHealth;
