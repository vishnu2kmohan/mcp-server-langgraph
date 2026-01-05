/**
 * useWebSocketTelemetrySync Hook
 *
 * Bridges the websocketTelemetry singleton with Redux observabilitySlice.
 * This enables React components to subscribe to WebSocket metrics changes
 * via Redux selectors instead of polling the singleton directly.
 *
 * Architecture:
 * - 20+ WebSocket hooks report to `websocketTelemetry` singleton via `reportWebSocketMetrics()`
 * - This hook periodically syncs singleton data to Redux
 * - Components can then use Redux selectors for reactive updates
 *
 * Usage:
 * ```tsx
 * // In a top-level component (e.g., App.tsx or ObservabilityPage)
 * useWebSocketTelemetrySync();
 *
 * // In child components, use Redux selectors
 * const wsMetrics = useAppSelector(selectWebSocketMetrics);
 * ```
 */

import { useEffect, useCallback, useState, useRef } from "react";
import { useAppDispatch, useAppSelector } from "../store/hooks";
import {
  updateWebSocketMetrics,
  removeWebSocketMetrics,
  selectWebSocketMetrics,
} from "../store/slices/observabilitySlice";
import { websocketTelemetry } from "../utils/websocketTelemetry";

/**
 * Options for useWebSocketTelemetrySync
 */
export interface UseWebSocketTelemetrySyncOptions {
  /** Sync interval in milliseconds (default: 2000) */
  syncIntervalMs?: number;
  /** Whether sync is enabled (default: true) */
  enabled?: boolean;
}

/**
 * Return type for useWebSocketTelemetrySync
 */
export interface UseWebSocketTelemetrySyncReturn {
  /** Manually trigger a sync */
  sync: () => void;
  /** Number of connections currently tracked */
  connectionCount: number;
  /** Timestamp of last successful sync */
  lastSyncTime: number;
}

/**
 * Hook to sync websocketTelemetry singleton to Redux observabilitySlice.
 *
 * This enables React components to use Redux selectors for WebSocket metrics
 * instead of polling the singleton directly, providing better React integration
 * and enabling features like time-travel debugging via Redux DevTools.
 */
export function useWebSocketTelemetrySync(
  options: UseWebSocketTelemetrySyncOptions = {},
): UseWebSocketTelemetrySyncReturn {
  const { syncIntervalMs = 2000, enabled = true } = options;

  const dispatch = useAppDispatch();
  const reduxMetrics = useAppSelector(selectWebSocketMetrics);
  const [lastSyncTime, setLastSyncTime] = useState<number>(0);
  const [connectionCount, setConnectionCount] = useState<number>(0);

  // Track current Redux endpoint IDs for removal detection
  const reduxEndpointIds = useRef<Set<string>>(new Set());

  // Sync function - copies singleton state to Redux
  const sync = useCallback(() => {
    const connections = websocketTelemetry.getConnections();
    const singletonEndpointIds = new Set<string>();

    // Update/add endpoints from singleton
    for (const conn of connections) {
      singletonEndpointIds.add(conn.endpointId);
      dispatch(
        updateWebSocketMetrics({
          endpointId: conn.endpointId,
          metrics: conn.metrics,
          lastUpdated: conn.lastUpdated,
        }),
      );
    }

    // Remove endpoints that are no longer in singleton
    for (const endpointId of reduxEndpointIds.current) {
      if (!singletonEndpointIds.has(endpointId)) {
        dispatch(removeWebSocketMetrics(endpointId));
      }
    }

    // Update tracked endpoint IDs
    reduxEndpointIds.current = singletonEndpointIds;

    // Update state
    setConnectionCount(connections.length);
    setLastSyncTime(Date.now());
  }, [dispatch]);

  // Initial sync on mount
  useEffect(() => {
    if (!enabled) return;
    sync();
  }, [enabled, sync]);

  // Periodic sync
  useEffect(() => {
    if (!enabled) return;

    const intervalId = setInterval(sync, syncIntervalMs);
    return () => clearInterval(intervalId);
  }, [enabled, syncIntervalMs, sync]);

  // Update reduxEndpointIds ref when Redux state changes
  useEffect(() => {
    reduxEndpointIds.current = new Set(Object.keys(reduxMetrics));
  }, [reduxMetrics]);

  return {
    sync,
    connectionCount,
    lastSyncTime,
  };
}
