/**
 * WebSocket Health Indicator Component
 *
 * Displays aggregate WebSocket connection health status.
 * Shows visual indicator (dot) with color coding:
 * - Green: Healthy (avgSuccessRate >= 90%)
 * - Yellow: Warning (70% <= avgSuccessRate < 90%)
 * - Red: Critical (avgSuccessRate < 70%)
 * - Gray: Unknown (no data)
 */

import { useState, useEffect, useCallback, useMemo } from "react";
import { websocketTelemetry } from "../../utils/websocketTelemetry";
import type { AggregatedWebSocketMetrics } from "../../utils/websocketTelemetry";

// =============================================================================
// Types
// =============================================================================

export type HealthStatus = "healthy" | "warning" | "critical" | "unknown";

export interface WebSocketHealthIndicatorProps {
  /** Show text label next to indicator */
  showLabel?: boolean;
  /** Show detailed metrics */
  showDetails?: boolean;
  /** Compact mode - just the dot */
  compact?: boolean;
  /** Auto-refresh metrics */
  autoRefresh?: boolean;
  /** Refresh interval in ms (default: 5000) */
  refreshInterval?: number;
  /** Additional CSS classes */
  className?: string;
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

/**
 * Get CSS class for status color.
 */
function getStatusColorClass(status: HealthStatus): string {
  switch (status) {
    case "healthy":
      return "bg-green-500";
    case "warning":
      return "bg-yellow-500";
    case "critical":
      return "bg-red-500";
    case "unknown":
    default:
      return "bg-gray-400";
  }
}

/**
 * Get label text for status.
 */
function getStatusLabel(status: HealthStatus): string {
  switch (status) {
    case "healthy":
      return "Healthy";
    case "warning":
      return "Warning";
    case "critical":
      return "Critical";
    case "unknown":
    default:
      return "Unknown";
  }
}

// =============================================================================
// Component
// =============================================================================

export function WebSocketHealthIndicator({
  showLabel = false,
  showDetails = false,
  compact = false,
  autoRefresh = false,
  refreshInterval = 5000,
  className = "",
}: WebSocketHealthIndicatorProps) {
  const [metrics, setMetrics] = useState<AggregatedWebSocketMetrics>(() =>
    websocketTelemetry.getAggregatedMetrics(),
  );

  // Refresh metrics
  const refreshMetrics = useCallback(() => {
    setMetrics(websocketTelemetry.getAggregatedMetrics());
  }, []);

  // Auto-refresh effect
  useEffect(() => {
    if (!autoRefresh) return;

    const intervalId = setInterval(refreshMetrics, refreshInterval);
    return () => clearInterval(intervalId);
  }, [autoRefresh, refreshInterval, refreshMetrics]);

  // Compute health status
  const healthStatus = useMemo(
    () => getHealthStatus(metrics.avgSuccessRate),
    [metrics.avgSuccessRate],
  );

  const statusColorClass = getStatusColorClass(healthStatus);
  const statusLabel = getStatusLabel(healthStatus);

  // No connections state
  if (metrics.totalConnections === 0) {
    return (
      <div
        data-testid="ws-health-indicator"
        className={`flex items-center gap-2 ${compact ? "compact" : ""} ${className}`}
      >
        <div
          data-testid="ws-health-status"
          className="w-2.5 h-2.5 rounded-full bg-gray-400"
        />
        <span className="text-sm text-gray-500">No connections</span>
      </div>
    );
  }

  return (
    <div
      data-testid="ws-health-indicator"
      className={`flex items-center gap-2 ${compact ? "compact" : ""} ${className}`}
    >
      {/* Status Dot */}
      <div
        data-testid="ws-health-status"
        className={`w-2.5 h-2.5 rounded-full ${statusColorClass}`}
        title={`${statusLabel} - ${metrics.avgSuccessRate ?? 0}% success rate`}
      />

      {/* Label */}
      {showLabel && (
        <span
          className={`text-sm font-medium ${
            healthStatus === "healthy"
              ? "text-green-600"
              : healthStatus === "warning"
                ? "text-yellow-600"
                : healthStatus === "critical"
                  ? "text-red-600"
                  : "text-gray-500"
          }`}
        >
          {statusLabel}
        </span>
      )}

      {/* Connection count */}
      {!compact && (
        <span className="text-sm text-gray-500">
          {metrics.totalConnections} connection
          {metrics.totalConnections !== 1 ? "s" : ""}
        </span>
      )}

      {/* Detailed metrics */}
      {showDetails && (
        <div className="flex items-center gap-3 text-xs text-gray-500">
          <span>{metrics.avgSuccessRate}% success</span>
          <span>{metrics.totalReconnectionAttempts} reconnects</span>
        </div>
      )}
    </div>
  );
}

export default WebSocketHealthIndicator;
