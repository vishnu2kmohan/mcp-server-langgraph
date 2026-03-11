/**
 * useWebSocketMetricsReporter Hook
 *
 * Reports WebSocket reconnection metrics from useRealtimeSync to Redux.
 * This enables centralized observability of all WebSocket connections.
 *
 * Usage:
 * ```tsx
 * const { metrics } = useRealtimeSync({ url: "ws://..." }); // nosemgrep: detect-insecure-websocket
 *
 * useWebSocketMetricsReporter({
 *   endpointId: "notifications",
 *   metrics,
 * });
 * ```
 */

import { useEffect, useRef } from "react";
import { useAppDispatch } from "../store/hooks";
import {
  updateWebSocketMetrics,
  removeWebSocketMetrics,
} from "../store/slices/observabilitySlice";
import type { ReconnectionMetrics } from "../types/websocket-metrics";

/**
 * Options for useWebSocketMetricsReporter
 */
export interface UseWebSocketMetricsReporterOptions {
  /** Unique identifier for this WebSocket endpoint */
  endpointId: string;
  /** Current reconnection metrics from useRealtimeSync */
  metrics: ReconnectionMetrics;
  /** Whether to report metrics (default: true) */
  enabled?: boolean;
  /** Whether to remove metrics from store on unmount (default: false) */
  cleanupOnUnmount?: boolean;
}

/**
 * Hook to report WebSocket metrics to Redux observability store.
 *
 * This hook bridges individual WebSocket hooks (useRealtimeSync) with
 * centralized observability in Redux, enabling the "ws-metrics" tab
 * in the ObservabilityPage.
 */
export function useWebSocketMetricsReporter({
  endpointId,
  metrics,
  enabled = true,
  cleanupOnUnmount = false,
}: UseWebSocketMetricsReporterOptions): void {
  const dispatch = useAppDispatch();
  const endpointIdRef = useRef(endpointId);

  // Keep ref updated
  endpointIdRef.current = endpointId;

  // Report metrics to Redux when they change
  useEffect(() => {
    if (!enabled) return;

    dispatch(
      updateWebSocketMetrics({
        endpointId,
        metrics,
        lastUpdated: Date.now(),
      }),
    );
  }, [dispatch, endpointId, metrics, enabled]);

  // Cleanup on unmount if enabled
  useEffect(() => {
    return () => {
      if (cleanupOnUnmount) {
        dispatch(removeWebSocketMetrics(endpointIdRef.current));
      }
    };
  }, [dispatch, cleanupOnUnmount]);
}
