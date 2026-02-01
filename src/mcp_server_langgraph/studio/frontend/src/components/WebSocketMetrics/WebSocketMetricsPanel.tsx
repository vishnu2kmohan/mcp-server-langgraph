/**
 * WebSocketMetricsPanel Component
 *
 * Observability dashboard for WebSocket connection metrics.
 * Displays aggregated metrics across all WebSocket endpoints,
 * including reconnection rates, failure reasons, and per-endpoint breakdowns.
 *
 * Features:
 * - Total connections summary
 * - Success rate visualization
 * - Failure breakdown by reason
 * - Per-endpoint metrics table
 * - Auto-refresh support
 */

import { useMemo, useEffect, useState, useCallback } from "react";
import {
  websocketTelemetry,
  type AggregatedWebSocketMetrics,
} from "../../utils/websocketTelemetry";
import type { ReconnectionMetrics } from "../../types/websocket-metrics";

import { Button } from "@/components/UI";

// =============================================================================
// Types
// =============================================================================

export interface WebSocketMetricsPanelProps {
  /** Refresh interval in milliseconds (default: 5000) */
  refreshInterval?: number;
  /** Additional CSS classes */
  className?: string;
}

// =============================================================================
// Utility Components
// =============================================================================

function cn(...classes: (string | undefined | boolean)[]): string {
  return classes.filter(Boolean).join(" ");
}

interface StatusBadgeProps {
  successRate: number | null;
}

function StatusBadge({ successRate }: StatusBadgeProps): React.ReactElement {
  if (successRate === null) {
    return (
      <span className="px-2 py-0.5 text-xs rounded-full bg-neutral-2 text-neutral-11">
        N/A
      </span>
    );
  }

  const color =
    successRate >= 90
      ? "bg-success-3 text-success-11 dark:bg-success-12 dark:text-success-5"
      : successRate >= 70
        ? "bg-warning-3 text-warning-10 dark:bg-warning-12 dark:text-warning-6"
        : "bg-error-3 text-error-11 dark:bg-error-12 dark:text-error-9";

  return (
    <span className={cn("px-2 py-0.5 text-xs rounded-full font-medium", color)}>
      {successRate}%
    </span>
  );
}

interface MetricCardProps {
  label: string;
  value: string | number;
  subValue?: string;
  icon?: React.ReactNode;
}

function MetricCard({
  label,
  value,
  subValue,
  icon,
}: MetricCardProps): React.ReactElement {
  return (
    <div className="bg-neutral-1 rounded-lg border border-neutral-5 p-4">
      <div className="flex items-center gap-2">
        {icon && <div className="text-neutral-9">{icon}</div>}
        <span className="text-sm text-neutral-10">{label}</span>
      </div>
      <div className="mt-2">
        <span className="text-2xl font-semibold text-neutral-12">{value}</span>
        {subValue && (
          <span className="ml-2 text-sm text-neutral-10">{subValue}</span>
        )}
      </div>
    </div>
  );
}

interface FailureBreakdownProps {
  failures: Record<string, number>;
}

function FailureBreakdown({
  failures,
}: FailureBreakdownProps): React.ReactElement | null {
  const sortedFailures = useMemo(() => {
    return Object.entries(failures)
      .filter(([, count]) => count > 0)
      .sort((a, b) => b[1] - a[1]);
  }, [failures]);

  if (sortedFailures.length === 0) {
    return null;
  }

  return (
    <div className="mt-4">
      <h4 className="text-sm font-medium text-neutral-11 mb-2">
        Failure Breakdown
      </h4>
      <div className="space-y-2">
        {sortedFailures.map(([reason, count]) => (
          <div
            key={reason}
            className="flex items-center justify-between text-sm"
          >
            <span className="text-neutral-11">{reason}</span>
            <span className="font-medium text-neutral-12">{count}</span>
          </div>
        ))}
      </div>
    </div>
  );
}

interface EndpointTableProps {
  endpoints: Record<string, ReconnectionMetrics>;
}

function EndpointTable({ endpoints }: EndpointTableProps): React.ReactElement {
  const sortedEndpoints = useMemo(() => {
    return Object.entries(endpoints).sort((a, b) => a[0].localeCompare(b[0]));
  }, [endpoints]);

  if (sortedEndpoints.length === 0) {
    return (
      <div className="text-center py-8 text-neutral-10">
        No WebSocket connections
      </div>
    );
  }

  return (
    <div className="overflow-x-auto">
      <table className="w-full text-sm">
        <thead>
          <tr className="border-b border-neutral-5">
            <th className="text-left py-2 px-3 font-medium text-neutral-11">
              Endpoint
            </th>
            <th className="text-right py-2 px-3 font-medium text-neutral-11">
              Attempts
            </th>
            <th className="text-right py-2 px-3 font-medium text-neutral-11">
              Success
            </th>
            <th className="text-right py-2 px-3 font-medium text-neutral-11">
              Rate
            </th>
            <th className="text-right py-2 px-3 font-medium text-neutral-11">
              Avg Duration
            </th>
          </tr>
        </thead>
        <tbody>
          {sortedEndpoints.map(([name, metrics]) => (
            <tr
              key={name}
              className="border-b border-neutral-5 hover:bg-neutral-1"
            >
              <td className="py-2 px-3 font-mono text-neutral-12">{name}</td>
              <td className="py-2 px-3 text-right text-neutral-11">
                {metrics.totalAttempts}
              </td>
              <td className="py-2 px-3 text-right text-neutral-11">
                {metrics.totalReconnections}
              </td>
              <td className="py-2 px-3 text-right">
                <StatusBadge successRate={metrics.successRate} />
              </td>
              <td className="py-2 px-3 text-right text-neutral-11">
                {metrics.avgReconnectionDurationMs !== null
                  ? `${metrics.avgReconnectionDurationMs}ms`
                  : "-"}
              </td>
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  );
}

// =============================================================================
// Main Component
// =============================================================================

export function WebSocketMetricsPanel({
  refreshInterval = 5000,
  className,
}: WebSocketMetricsPanelProps): React.ReactElement {
  const [metrics, setMetrics] = useState<AggregatedWebSocketMetrics>(() =>
    websocketTelemetry.getAggregatedMetrics(),
  );

  const refresh = useCallback(() => {
    setMetrics(websocketTelemetry.getAggregatedMetrics());
  }, []);

  // Auto-refresh
  useEffect(() => {
    const interval = setInterval(refresh, refreshInterval);
    return () => clearInterval(interval);
  }, [refreshInterval, refresh]);

  // Refresh on mount
  useEffect(() => {
    refresh();
  }, [refresh]);

  const hasConnections = metrics.totalConnections > 0;

  return (
    <div
      data-testid="ws-metrics-panel"
      className={cn("flex flex-col h-full bg-neutral-1", className)}
    >
      {/* Header */}
      <div className="flex items-center justify-between px-4 py-3 border-b border-neutral-5 bg-neutral-1">
        <h3 className="text-lg font-semibold text-neutral-12">
          WebSocket Metrics
        </h3>
        <Button
          variant="secondary"
          className="p-1.5 rounded-md hover:bg-neutral-2"
          onClick={refresh}
          aria-label="Refresh"
        >
          <svg
            className="w-4 h-4 text-neutral-11"
            fill="none"
            viewBox="0 0 24 24"
            stroke="currentColor"
          >
            <path
              strokeLinecap="round"
              strokeLinejoin="round"
              strokeWidth={2}
              d="M4 4v5h.582m15.356 2A8.001 8.001 0 004.582 9m0 0H9m11 11v-5h-.581m0 0a8.003 8.003 0 01-15.357-2m15.357 2H15"
            />
          </svg>
        </Button>
      </div>
      {/* Content */}
      <div className="flex-1 overflow-auto p-4">
        {!hasConnections ? (
          <div className="flex flex-col items-center justify-center h-full text-center">
            <svg
              className="w-12 h-12 text-neutral-9 mb-4"
              fill="none"
              viewBox="0 0 24 24"
              stroke="currentColor"
            >
              <path
                strokeLinecap="round"
                strokeLinejoin="round"
                strokeWidth={2}
                d="M8.111 16.404a5.5 5.5 0 017.778 0M12 20h.01m-7.08-7.071c3.904-3.905 10.236-3.905 14.141 0M1.394 9.393c5.857-5.857 15.355-5.857 21.213 0"
              />
            </svg>
            <p className="text-neutral-10">No WebSocket connections</p>
            <p className="text-sm text-neutral-9 mt-1">
              Metrics will appear when WebSocket hooks report data
            </p>
          </div>
        ) : (
          <div className="space-y-6">
            {/* Summary Cards */}
            <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
              <MetricCard
                label="Total Connections"
                value={metrics.totalConnections}
              />
              <MetricCard
                label="Total Attempts"
                value={metrics.totalReconnectionAttempts}
              />
              <MetricCard
                label="Successful"
                value={metrics.totalSuccessfulReconnections}
              />
              <MetricCard
                label="Avg Success Rate"
                value={
                  metrics.avgSuccessRate !== null
                    ? `${metrics.avgSuccessRate}%`
                    : "N/A"
                }
              />
            </div>

            {/* Failure Breakdown */}
            <FailureBreakdown failures={metrics.failuresByReason} />

            {/* Per-Endpoint Table */}
            <div>
              <h4 className="text-sm font-medium text-neutral-11 mb-3">
                Per-Endpoint Metrics
              </h4>
              <div className="bg-neutral-1 rounded-lg border border-neutral-5">
                <EndpointTable endpoints={metrics.byEndpoint} />
              </div>
            </div>
          </div>
        )}
      </div>
    </div>
  );
}

export default WebSocketMetricsPanel;
