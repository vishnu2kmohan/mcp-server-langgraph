/**
 * useHeartMetricsWebSocket Hook
 *
 * WebSocket hook for real-time HEART metrics streaming.
 * Replaces polling-based useHeartDashboard.ts with efficient push-based updates.
 *
 * Based on backend endpoint: /api/v1/ws/metrics/heart
 */

import { useState, useCallback, useRef, useMemo, useEffect } from "react";
import { useRealtimeSync } from "./useRealtimeSync";
import { useAppDispatch, useAppSelector } from "../store/hooks";
import { logout, selectIsAuthenticated } from "../store/slices/authSlice";
import { getAuthToken } from "../utils/storage";
import { buildWebSocketUrl, WS_ENDPOINTS } from "../utils/websocket";

// =============================================================================
// Types
// =============================================================================

/**
 * HEART dimension metrics
 */
export interface DimensionMetrics {
  score: number;
  trend: "up" | "down" | "stable";
  samples?: number;
}

/**
 * HEART metrics snapshot
 */
export interface HeartMetricsSnapshot {
  happiness: DimensionMetrics;
  engagement: DimensionMetrics;
  adoption: DimensionMetrics;
  retention: DimensionMetrics;
  task_success: DimensionMetrics;
}

/**
 * Threshold alert for a dimension
 */
export interface ThresholdAlert {
  dimension: string;
  current_score: number;
  threshold: number;
  severity: "warning" | "critical";
  message: string;
}

/**
 * WebSocket message types from server
 */
interface MetricsSnapshotMessage {
  type: "metrics_snapshot";
  snapshot: HeartMetricsSnapshot;
  time_range: string;
}

interface DimensionUpdateMessage {
  type: "dimension_update";
  dimension: string;
  metrics: DimensionMetrics;
}

interface ThresholdAlertMessage {
  type: "threshold_alert";
  alert: ThresholdAlert;
}

interface SubscribedMessage {
  type: "subscribed";
  dimension: string;
}

interface UnsubscribedMessage {
  type: "unsubscribed";
  dimension: string;
}

interface TimeRangeUpdatedMessage {
  type: "time_range_updated";
  time_range: string;
}

interface ErrorMessage {
  type: "error";
  message: string;
}

type ServerMessage =
  | MetricsSnapshotMessage
  | DimensionUpdateMessage
  | ThresholdAlertMessage
  | SubscribedMessage
  | UnsubscribedMessage
  | TimeRangeUpdatedMessage
  | ErrorMessage;

/**
 * Options for useHeartMetricsWebSocket hook
 */
export interface UseHeartMetricsWebSocketOptions {
  /** Custom WebSocket URL (defaults to /api/v1/ws/metrics/heart) */
  url?: string;
  /** Callback when metrics snapshot is received */
  onSnapshot?: (snapshot: HeartMetricsSnapshot) => void;
  /** Callback when a dimension is updated */
  onDimensionUpdate?: (dimension: string, metrics: DimensionMetrics) => void;
  /** Callback when threshold alert is received */
  onThresholdAlert?: (alert: ThresholdAlert) => void;
  /** Callback when an error occurs */
  onError?: (error: string) => void;
}

/**
 * Return type for useHeartMetricsWebSocket hook
 */
export interface UseHeartMetricsWebSocketReturn {
  /** Current WebSocket connection status */
  status:
    | "connecting"
    | "connected"
    | "disconnected"
    | "reconnecting"
    | "error";
  /** Current HEART metrics snapshot */
  snapshot: HeartMetricsSnapshot | null;
  /** Current time range */
  timeRange: string;
  /** Set of dimensions currently subscribed to */
  subscribedDimensions: Set<string>;
  /** Recent threshold alerts */
  alerts: ThresholdAlert[];
  /** Current error message, if any */
  error: string | null;
  /** Set the time range for metrics */
  setTimeRange: (range: string) => void;
  /** Subscribe to updates for a specific dimension */
  subscribeDimension: (dimension: string) => void;
  /** Unsubscribe from updates for a specific dimension */
  unsubscribeDimension: (dimension: string) => void;
  /** Request a fresh metrics snapshot */
  refresh: () => void;
  /** Get metrics for a specific dimension */
  getDimension: (dimension: string) => DimensionMetrics | undefined;
  /** Clear all alerts */
  clearAlerts: () => void;
  /** Manually disconnect from WebSocket */
  disconnect: () => void;
  /** Manually reconnect to WebSocket */
  reconnect: () => void;
}

// =============================================================================
// Hook Implementation
// =============================================================================

export function useHeartMetricsWebSocket(
  options: UseHeartMetricsWebSocketOptions = {},
): UseHeartMetricsWebSocketReturn {
  const {
    url: customUrl,
    onSnapshot,
    onDimensionUpdate,
    onThresholdAlert,
    onError,
  } = options;

  // Redux dispatch for token expiration handling
  const dispatch = useAppDispatch();

  // Get auth state and token for WebSocket authentication
  const isAuthenticated = useAppSelector(selectIsAuthenticated);
  // Track token changes to trigger URL regeneration on refresh
  const authToken = isAuthenticated ? (getAuthToken() ?? undefined) : undefined;

  // Compute WebSocket URL - only generate URL when authenticated
  // Passing empty string prevents connection attempt before auth is ready
  const url = useMemo(
    () =>
      isAuthenticated
        ? (customUrl ?? buildWebSocketUrl(WS_ENDPOINTS.METRICS_HEART, {}, true))
        : "",
    // authToken dependency ensures URL regenerates when token is refreshed
    // eslint-disable-next-line react-hooks/exhaustive-deps
    [customUrl, authToken, isAuthenticated],
  );

  // State
  const [snapshot, setSnapshot] = useState<HeartMetricsSnapshot | null>(null);
  const [timeRange, setTimeRangeState] = useState<string>("24h");
  const [subscribedDimensions, setSubscribedDimensions] = useState<Set<string>>(
    new Set(),
  );
  const [alerts, setAlerts] = useState<ThresholdAlert[]>([]);
  const [error, setError] = useState<string | null>(null);

  // Refs for callbacks to avoid stale closures
  const callbacksRef = useRef({
    onSnapshot,
    onDimensionUpdate,
    onThresholdAlert,
    onError,
  });
  callbacksRef.current = {
    onSnapshot,
    onDimensionUpdate,
    onThresholdAlert,
    onError,
  };

  // Ref for send function to use in handlers
  const sendRef = useRef<(data: unknown) => void>(() => {});

  // Handle incoming messages
  const handleMessage = useCallback((data: unknown) => {
    const message = data as ServerMessage;

    switch (message.type) {
      case "metrics_snapshot":
        setSnapshot(message.snapshot);
        setTimeRangeState(message.time_range);
        callbacksRef.current.onSnapshot?.(message.snapshot);
        break;

      case "dimension_update":
        setSnapshot((prev) => {
          if (!prev) return prev;
          return {
            ...prev,
            [message.dimension]: message.metrics,
          };
        });
        callbacksRef.current.onDimensionUpdate?.(
          message.dimension,
          message.metrics,
        );
        break;

      case "threshold_alert":
        setAlerts((prev) => [...prev, message.alert]);
        callbacksRef.current.onThresholdAlert?.(message.alert);
        break;

      case "subscribed":
        setSubscribedDimensions((prev) => new Set(prev).add(message.dimension));
        break;

      case "unsubscribed":
        setSubscribedDimensions((prev) => {
          const next = new Set(prev);
          next.delete(message.dimension);
          return next;
        });
        break;

      case "time_range_updated":
        setTimeRangeState(message.time_range);
        break;

      case "error":
        setError(message.message);
        callbacksRef.current.onError?.(message.message);
        break;
    }
  }, []);

  // Handle connection established
  const handleConnect = useCallback(() => {
    setError(null);
    // Request initial snapshot
    sendRef.current({ type: "get_snapshot", time_range: timeRange });
  }, [timeRange]);

  // Use the realtime sync hook for WebSocket management
  const { status, send, disconnect, reconnect, metrics } = useRealtimeSync({
    url,
    onMessage: handleMessage,
    onConnect: handleConnect,
    exponentialBackoff: true,
    reconnectInterval: 1000,
    maxDelayMs: 30000,
    maxReconnectAttempts: 10,
    onTokenExpired: () => dispatch(logout()),
  });

  // Report WebSocket metrics for observability
  useEffect(() => {
    if (isAuthenticated && metrics.totalAttempts > 0) {
      import("../utils/websocketTelemetry").then(
        ({ reportWebSocketMetrics }) => {
          reportWebSocketMetrics("heart_metrics", metrics);
        },
      );
    }
  }, [isAuthenticated, metrics]);

  // Keep sendRef in sync
  sendRef.current = send;

  // Commands
  const setTimeRange = useCallback(
    (range: string) => {
      setTimeRangeState(range);
      send({ type: "set_time_range", time_range: range });
    },
    [send],
  );

  const subscribeDimension = useCallback(
    (dimension: string) => {
      send({ type: "subscribe_dimension", dimension });
    },
    [send],
  );

  const unsubscribeDimension = useCallback(
    (dimension: string) => {
      send({ type: "unsubscribe_dimension", dimension });
    },
    [send],
  );

  const refresh = useCallback(() => {
    send({ type: "get_snapshot", time_range: timeRange });
  }, [send, timeRange]);

  const getDimension = useCallback(
    (dimension: string): DimensionMetrics | undefined => {
      if (!snapshot) return undefined;
      return snapshot[dimension as keyof HeartMetricsSnapshot];
    },
    [snapshot],
  );

  const clearAlerts = useCallback(() => {
    setAlerts([]);
  }, []);

  return {
    status,
    snapshot,
    timeRange,
    subscribedDimensions,
    alerts,
    error,
    setTimeRange,
    subscribeDimension,
    unsubscribeDimension,
    refresh,
    getDimension,
    clearAlerts,
    disconnect,
    reconnect,
  };
}

export default useHeartMetricsWebSocket;
