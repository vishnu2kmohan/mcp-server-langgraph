/**
 * useWebSocketHealthAlerts Hook
 *
 * Monitors WebSocket connection health and triggers alerts when thresholds are exceeded.
 *
 * Alert Types:
 * - critical: avgSuccessRate < 70%
 * - warning: 70% <= avgSuccessRate < 80%, high reconnection rate, recurring failure patterns
 *
 * Features:
 * - Periodic health checks
 * - Alert deduplication
 * - Dismissable alerts
 * - Callback on new alerts
 */

import { useState, useEffect, useCallback, useMemo, useRef } from "react";
import { websocketTelemetry } from "../utils/websocketTelemetry";
import type { AggregatedWebSocketMetrics } from "../utils/websocketTelemetry";

// =============================================================================
// Types
// =============================================================================

export type HealthStatus = "healthy" | "warning" | "critical" | "unknown";

export type AlertType = "critical" | "warning" | "info";

export type AlertReason =
  | "low_success_rate"
  | "degraded_success_rate"
  | "high_reconnection_rate"
  | "recurring_failure_pattern"
  | "no_connections";

export interface WebSocketAlert {
  /** Unique alert ID */
  id: string;
  /** Alert severity */
  type: AlertType;
  /** Reason for the alert */
  reason: AlertReason;
  /** Human-readable message */
  message: string;
  /** Additional details */
  details?: Record<string, unknown>;
  /** When the alert was triggered */
  timestamp: number;
}

export interface UseWebSocketHealthAlertsOptions {
  /** Callback when new alert is triggered */
  onAlert?: (alert: WebSocketAlert) => void;
  /** Check interval in ms (default: 5000) */
  checkInterval?: number;
  /** Reconnection rate threshold per connection (default: 5) */
  reconnectionThreshold?: number;
  /** Failure pattern threshold (default: 3) */
  failurePatternThreshold?: number;
  /** Success rate warning threshold (default: 80) */
  warningThreshold?: number;
  /** Success rate critical threshold (default: 70) */
  criticalThreshold?: number;
}

export interface UseWebSocketHealthAlertsReturn {
  /** Current alerts */
  alerts: WebSocketAlert[];
  /** Whether there are any active alerts */
  hasActiveAlerts: boolean;
  /** Current health status */
  healthStatus: HealthStatus;
  /** Current metrics */
  metrics: AggregatedWebSocketMetrics;
  /** Dismiss a specific alert */
  dismissAlert: (alertId: string) => void;
  /** Clear all alerts */
  clearAllAlerts: () => void;
  /** Force refresh metrics check */
  refresh: () => void;
}

// =============================================================================
// Utility Functions
// =============================================================================

function generateAlertId(): string {
  return `alert-${Date.now()}-${Math.random().toString(36).substr(2, 9)}`;
}

function getHealthStatus(avgSuccessRate: number | null): HealthStatus {
  if (avgSuccessRate === null) return "unknown";
  if (avgSuccessRate >= 90) return "healthy";
  if (avgSuccessRate >= 70) return "warning";
  return "critical";
}

// =============================================================================
// Hook Implementation
// =============================================================================

export function useWebSocketHealthAlerts(
  options: UseWebSocketHealthAlertsOptions = {},
): UseWebSocketHealthAlertsReturn {
  const {
    onAlert,
    checkInterval = 5000,
    reconnectionThreshold = 5,
    failurePatternThreshold = 3,
    warningThreshold = 80,
    criticalThreshold = 70,
  } = options;

  const [alerts, setAlerts] = useState<WebSocketAlert[]>([]);
  const [metrics, setMetrics] = useState<AggregatedWebSocketMetrics>(() =>
    websocketTelemetry.getAggregatedMetrics(),
  );

  // Track which alert reasons we've already triggered to avoid duplicates
  const triggeredReasonsRef = useRef<Set<string>>(new Set());
  const onAlertRef = useRef(onAlert);
  onAlertRef.current = onAlert;

  // Check metrics and generate alerts
  const checkMetrics = useCallback(() => {
    const currentMetrics = websocketTelemetry.getAggregatedMetrics();
    setMetrics(currentMetrics);

    const newAlerts: WebSocketAlert[] = [];

    // Check success rate
    if (currentMetrics.avgSuccessRate !== null) {
      if (currentMetrics.avgSuccessRate < criticalThreshold) {
        const reason = "low_success_rate";
        if (!triggeredReasonsRef.current.has(reason)) {
          const alert: WebSocketAlert = {
            id: generateAlertId(),
            type: "critical",
            reason,
            message: `WebSocket success rate is critically low: ${currentMetrics.avgSuccessRate}%`,
            timestamp: Date.now(),
          };
          newAlerts.push(alert);
          triggeredReasonsRef.current.add(reason);
        }
      } else if (currentMetrics.avgSuccessRate < warningThreshold) {
        const reason = "degraded_success_rate";
        if (!triggeredReasonsRef.current.has(reason)) {
          const alert: WebSocketAlert = {
            id: generateAlertId(),
            type: "warning",
            reason,
            message: `WebSocket success rate is degraded: ${currentMetrics.avgSuccessRate}%`,
            timestamp: Date.now(),
          };
          newAlerts.push(alert);
          triggeredReasonsRef.current.add(reason);
        }
      }
    }

    // Check reconnection rate
    if (currentMetrics.totalConnections > 0) {
      const avgReconnectionsPerConnection =
        currentMetrics.totalReconnectionAttempts /
        currentMetrics.totalConnections;

      if (avgReconnectionsPerConnection > reconnectionThreshold) {
        const reason = "high_reconnection_rate";
        if (!triggeredReasonsRef.current.has(reason)) {
          const alert: WebSocketAlert = {
            id: generateAlertId(),
            type: "warning",
            reason,
            message: `High reconnection rate detected: ${avgReconnectionsPerConnection.toFixed(1)} attempts per connection`,
            details: {
              avgReconnectionsPerConnection,
              threshold: reconnectionThreshold,
            },
            timestamp: Date.now(),
          };
          newAlerts.push(alert);
          triggeredReasonsRef.current.add(reason);
        }
      }
    }

    // Check failure patterns
    for (const [pattern, count] of Object.entries(
      currentMetrics.failuresByReason,
    )) {
      if (count >= failurePatternThreshold) {
        const reason = `recurring_failure_pattern:${pattern}`;
        if (!triggeredReasonsRef.current.has(reason)) {
          const alert: WebSocketAlert = {
            id: generateAlertId(),
            type: "warning",
            reason: "recurring_failure_pattern",
            message: `Recurring WebSocket failure pattern: ${pattern} (${count} occurrences)`,
            details: { pattern, count },
            timestamp: Date.now(),
          };
          newAlerts.push(alert);
          triggeredReasonsRef.current.add(reason);
        }
      }
    }

    // Add new alerts and trigger callbacks
    if (newAlerts.length > 0) {
      setAlerts((prev) => [...prev, ...newAlerts]);
      newAlerts.forEach((alert) => {
        onAlertRef.current?.(alert);
      });
    }
  }, [
    criticalThreshold,
    warningThreshold,
    reconnectionThreshold,
    failurePatternThreshold,
  ]);

  // Initial check
  useEffect(() => {
    checkMetrics();
  }, [checkMetrics]);

  // Periodic checking
  useEffect(() => {
    const intervalId = setInterval(checkMetrics, checkInterval);
    return () => clearInterval(intervalId);
  }, [checkMetrics, checkInterval]);

  // Dismiss a specific alert
  const dismissAlert = useCallback((alertId: string) => {
    setAlerts((prev) => prev.filter((a) => a.id !== alertId));
  }, []);

  // Clear all alerts
  const clearAllAlerts = useCallback(() => {
    setAlerts([]);
    triggeredReasonsRef.current.clear();
  }, []);

  // Force refresh
  const refresh = useCallback(() => {
    checkMetrics();
  }, [checkMetrics]);

  // Compute health status
  const healthStatus = useMemo(
    () => getHealthStatus(metrics.avgSuccessRate),
    [metrics.avgSuccessRate],
  );

  const hasActiveAlerts = alerts.length > 0;

  return {
    alerts,
    hasActiveAlerts,
    healthStatus,
    metrics,
    dismissAlert,
    clearAllAlerts,
    refresh,
  };
}

export default useWebSocketHealthAlerts;
