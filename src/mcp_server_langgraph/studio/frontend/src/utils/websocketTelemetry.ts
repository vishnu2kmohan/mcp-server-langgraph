/**
 * WebSocket Telemetry
 *
 * Provides telemetry tracking for WebSocket operations:
 * - Connection success/failure rates
 * - Reconnection metrics
 * - Message throughput
 * - Latency tracking
 *
 * Usage:
 * ```tsx
 * import { websocketTelemetry } from "../utils/websocketTelemetry";
 *
 * // Track reconnection metrics from useRealtimeSync
 * websocketTelemetry.trackReconnectionMetrics("notifications", metrics);
 *
 * // Get aggregated metrics
 * const aggregated = websocketTelemetry.getAggregatedMetrics();
 * ```
 */

import { devLogger } from "./devLogger";
import type { ReconnectionMetrics } from "../types/websocket-metrics";

// =============================================================================
// Types
// =============================================================================

/**
 * Tracked WebSocket connection info.
 */
export interface WebSocketConnectionInfo {
  /** Endpoint identifier (e.g., "notifications", "traces") */
  endpointId: string;
  /** Current reconnection metrics */
  metrics: ReconnectionMetrics;
  /** Last update timestamp */
  lastUpdated: number;
}

/**
 * Aggregated WebSocket metrics across all connections.
 */
export interface AggregatedWebSocketMetrics {
  /** Total connections being tracked */
  totalConnections: number;
  /** Sum of all reconnection attempts across connections */
  totalReconnectionAttempts: number;
  /** Sum of all successful reconnections across connections */
  totalSuccessfulReconnections: number;
  /** Average success rate across all connections */
  avgSuccessRate: number | null;
  /** Breakdown of failures by reason across all connections */
  failuresByReason: Record<string, number>;
  /** Per-endpoint metrics */
  byEndpoint: Record<string, ReconnectionMetrics>;
}

/**
 * WebSocket telemetry export payload.
 */
export interface WebSocketTelemetryExportPayload {
  metrics: AggregatedWebSocketMetrics;
  connections: WebSocketConnectionInfo[];
  metadata: {
    clientVersion?: string;
    timestamp: number;
  };
  exportedAt: number;
}

/**
 * Telemetry exporter function type.
 */
export type WebSocketTelemetryExporter = (
  payload: WebSocketTelemetryExportPayload,
) => Promise<void>;

interface WebSocketTelemetryOptions {
  debug?: boolean;
  /** Custom exporter function for sending telemetry to a backend */
  exporter?: WebSocketTelemetryExporter;
  /** Client version for export metadata */
  clientVersion?: string;
}

// =============================================================================
// Implementation
// =============================================================================

export class WebSocketTelemetry {
  private options: {
    debug: boolean;
    exporter?: WebSocketTelemetryExporter;
    clientVersion?: string;
  };
  private connections: Map<string, WebSocketConnectionInfo> = new Map();

  constructor(options: WebSocketTelemetryOptions = {}) {
    this.options = {
      debug: options.debug ?? false,
      exporter: options.exporter,
      clientVersion: options.clientVersion,
    };
  }

  /**
   * Track reconnection metrics for a specific endpoint.
   */
  trackReconnectionMetrics(
    endpointId: string,
    metrics: ReconnectionMetrics,
  ): void {
    const connectionInfo: WebSocketConnectionInfo = {
      endpointId,
      metrics,
      lastUpdated: Date.now(),
    };

    this.connections.set(endpointId, connectionInfo);
    this.log(`Metrics updated for ${endpointId}`, metrics);
  }

  /**
   * Remove tracking for a specific endpoint.
   */
  removeEndpoint(endpointId: string): void {
    this.connections.delete(endpointId);
    this.log(`Removed tracking for ${endpointId}`);
  }

  /**
   * Get aggregated metrics across all tracked connections.
   */
  getAggregatedMetrics(): AggregatedWebSocketMetrics {
    const connections = Array.from(this.connections.values());

    if (connections.length === 0) {
      return {
        totalConnections: 0,
        totalReconnectionAttempts: 0,
        totalSuccessfulReconnections: 0,
        avgSuccessRate: null,
        failuresByReason: {},
        byEndpoint: {},
      };
    }

    // Aggregate across all connections
    let totalAttempts = 0;
    let totalSuccessful = 0;
    const failuresByReason: Record<string, number> = {};
    const byEndpoint: Record<string, ReconnectionMetrics> = {};
    const successRates: number[] = [];

    for (const conn of connections) {
      const m = conn.metrics;
      totalAttempts += m.totalAttempts;
      totalSuccessful += m.totalReconnections;
      byEndpoint[conn.endpointId] = m;

      if (m.successRate !== null) {
        successRates.push(m.successRate);
      }

      // Aggregate failure reasons
      for (const [reason, count] of Object.entries(m.failuresByReason)) {
        failuresByReason[reason] = (failuresByReason[reason] || 0) + count;
      }
    }

    const avgSuccessRate =
      successRates.length > 0
        ? Math.round(
            successRates.reduce((a, b) => a + b, 0) / successRates.length,
          )
        : null;

    return {
      totalConnections: connections.length,
      totalReconnectionAttempts: totalAttempts,
      totalSuccessfulReconnections: totalSuccessful,
      avgSuccessRate,
      failuresByReason,
      byEndpoint,
    };
  }

  /**
   * Get all tracked connections.
   */
  getConnections(): WebSocketConnectionInfo[] {
    return Array.from(this.connections.values());
  }

  /**
   * Get metrics for a specific endpoint.
   */
  getEndpointMetrics(endpointId: string): ReconnectionMetrics | null {
    const conn = this.connections.get(endpointId);
    return conn ? conn.metrics : null;
  }

  /**
   * Get exportable payload containing all metrics.
   */
  getExportPayload(): WebSocketTelemetryExportPayload {
    return {
      metrics: this.getAggregatedMetrics(),
      connections: this.getConnections(),
      metadata: {
        clientVersion: this.options.clientVersion,
        timestamp: Date.now(),
      },
      exportedAt: Date.now(),
    };
  }

  /**
   * Export telemetry as JSON string.
   */
  toJSON(): string {
    return JSON.stringify(this.getExportPayload());
  }

  /**
   * Flush metrics to the configured exporter.
   */
  async flush(): Promise<void> {
    if (!this.options.exporter) {
      return;
    }

    const payload = this.getExportPayload();
    await this.options.exporter(payload);
    this.log("Flushed telemetry", payload.metrics);
  }

  /**
   * Reset all tracked connections.
   */
  reset(): void {
    this.connections.clear();
    this.log("Reset all connections");
  }

  /**
   * Log message if debug mode is enabled.
   */
  private log(message: string, data?: unknown): void {
    if (this.options.debug) {
      devLogger.debug(`[WebSocketTelemetry] ${message}`, data);
    }
  }
}

// =============================================================================
// Singleton Instance
// =============================================================================

/**
 * Global WebSocket telemetry instance.
 */
export const websocketTelemetry = new WebSocketTelemetry({
  debug: process.env.NODE_ENV === "development",
});

// =============================================================================
// React Hook Helper
// =============================================================================

/**
 * Helper to report metrics from useRealtimeSync to the global telemetry.
 *
 * Usage:
 * ```tsx
 * const { metrics } = useRealtimeSync({ url: "ws://..." });
 *
 * useEffect(() => {
 *   reportWebSocketMetrics("notifications", metrics);
 * }, [metrics]);
 * ```
 */
export function reportWebSocketMetrics(
  endpointId: string,
  metrics: ReconnectionMetrics,
): void {
  websocketTelemetry.trackReconnectionMetrics(endpointId, metrics);
}
