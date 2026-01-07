/**
 * useMetricsSessionWebSocket Hook
 *
 * WebSocket hook for real-time session-scoped metrics streaming.
 * Provides live metric updates for the DevTools Metrics tab.
 *
 * Based on backend endpoint: /api/v1/ws/metrics/session
 */

import { useState, useCallback, useRef, useMemo, useEffect } from "react";
import { useRealtimeSync } from "./useRealtimeSync";
import { useAppDispatch, useAppSelector } from "../store/hooks";
import { logout, selectIsAuthenticated } from "../store/slices/authSlice";
import { addNotification } from "../store/slices/notificationSlice";
import { getAuthToken } from "../utils/storage";
import { buildWebSocketUrl, WS_ENDPOINTS } from "../utils/websocket";
import {
  PROTOCOL_VERSION_MISMATCH_NOTIFICATION,
  showProtocolVersionMismatchToast,
} from "../utils/websocketAuth";
import { reportWebSocketMetrics } from "../utils/websocketTelemetry";

// =============================================================================
// Types
// =============================================================================

export type MetricTrend = "up" | "down" | "stable";

export type MetricType = "counter" | "gauge" | "histogram" | "summary";

/**
 * Single metric data point
 */
export interface MetricData {
  name: string;
  value: number;
  timestamp: string;
  labels: Record<string, string>;
  metric_type: MetricType;
  sparkline: number[];
  trend: MetricTrend;
  change: number;
  session_id?: string;
  histogram_buckets?: Record<string, number>;
}

/**
 * Metrics snapshot (all current metrics)
 */
export interface MetricsSnapshot {
  [metricName: string]: MetricData;
}

/**
 * WebSocket message types from server
 */
interface MetricMessage {
  type: "metric";
  payload: MetricData;
}

interface MetricsSnapshotMessage {
  type: "metrics_snapshot";
  payload: {
    metrics: MetricsSnapshot;
    session_id?: string;
  };
}

interface SubscribedMessage {
  type: "subscribed";
  payload: {
    session_id?: string;
  };
}

interface UnsubscribedMessage {
  type: "unsubscribed";
  payload: Record<string, never>;
}

interface ErrorMessage {
  type: "error";
  message: string;
}

type ServerMessage =
  | MetricMessage
  | MetricsSnapshotMessage
  | SubscribedMessage
  | UnsubscribedMessage
  | ErrorMessage;

/**
 * Options for useMetricsSessionWebSocket hook
 */
export interface UseMetricsSessionWebSocketOptions {
  /** Session ID to filter metrics */
  sessionId?: string;
  /** Custom WebSocket URL */
  url?: string;
  /** Callback when a metric is updated */
  onMetric?: (metric: MetricData) => void;
  /** Callback when snapshot is received */
  onSnapshot?: (snapshot: MetricsSnapshot) => void;
  /** Callback when an error occurs */
  onError?: (error: string) => void;
}

/**
 * Return type for useMetricsSessionWebSocket hook
 */
export interface UseMetricsSessionWebSocketReturn {
  /** Current WebSocket connection status */
  status:
    | "connecting"
    | "connected"
    | "disconnected"
    | "reconnecting"
    | "error";
  /** All current metrics */
  metrics: MetricsSnapshot;
  /** Current session ID filter */
  sessionId: string | null;
  /** Error message, if any */
  error: string | null;
  /** Set session ID filter */
  setSessionId: (sessionId: string | null) => void;
  /** Request a metrics snapshot */
  refresh: () => void;
  /** Get a specific metric by name */
  getMetric: (name: string) => MetricData | undefined;
  /** Disconnect from WebSocket */
  disconnect: () => void;
  /** Reconnect to WebSocket */
  reconnect: () => void;
}

// =============================================================================
// Hook Implementation
// =============================================================================

export function useMetricsSessionWebSocket(
  options: UseMetricsSessionWebSocketOptions = {},
): UseMetricsSessionWebSocketReturn {
  const {
    sessionId: initialSessionId,
    url: customUrl,
    onMetric,
    onSnapshot,
    onError,
  } = options;

  const dispatch = useAppDispatch();
  const isAuthenticated = useAppSelector(selectIsAuthenticated);
  const authToken = isAuthenticated ? (getAuthToken() ?? undefined) : undefined;

  // Compute WebSocket URL
  const url = useMemo(
    () =>
      isAuthenticated
        ? (customUrl ??
          buildWebSocketUrl(WS_ENDPOINTS.METRICS_SESSION, {}, true))
        : "",
    // eslint-disable-next-line react-hooks/exhaustive-deps
    [customUrl, authToken, isAuthenticated],
  );

  // State
  const [metrics, setMetrics] = useState<MetricsSnapshot>({});
  const [sessionId, setSessionIdState] = useState<string | null>(
    initialSessionId ?? null,
  );
  const [error, setError] = useState<string | null>(null);

  // Refs for callbacks
  const callbacksRef = useRef({
    onMetric,
    onSnapshot,
    onError,
  });
  callbacksRef.current = { onMetric, onSnapshot, onError };

  const sendRef = useRef<(data: unknown) => void>(() => {});

  // Handle incoming messages
  const handleMessage = useCallback((data: unknown) => {
    const message = data as ServerMessage;

    switch (message.type) {
      case "metric": {
        const metric = message.payload;
        setMetrics((prev) => ({
          ...prev,
          [metric.name]: metric,
        }));
        callbacksRef.current.onMetric?.(metric);
        break;
      }

      case "metrics_snapshot": {
        const snapshot = message.payload.metrics;
        setMetrics(snapshot);
        callbacksRef.current.onSnapshot?.(snapshot);
        break;
      }

      case "subscribed":
        // Subscription confirmed
        break;

      case "unsubscribed":
        // Unsubscription confirmed
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
    // Subscribe with session filter
    sendRef.current({
      type: "subscribe",
      payload: { session_id: sessionId },
    });
    // Request initial snapshot
    sendRef.current({
      type: "get_snapshot",
      payload: { session_id: sessionId },
    });
  }, [sessionId]);

  // Use the realtime sync hook
  const {
    status,
    send,
    disconnect,
    reconnect,
    metrics: wsMetrics,
  } = useRealtimeSync({
    url,
    onMessage: handleMessage,
    onConnect: handleConnect,
    exponentialBackoff: true,
    reconnectInterval: 1000,
    maxDelayMs: 30000,
    maxReconnectAttempts: 10,
    onTokenExpired: () => dispatch(logout()),
    onProtocolVersionMismatch: () => {
      dispatch(addNotification(PROTOCOL_VERSION_MISMATCH_NOTIFICATION));
      showProtocolVersionMismatchToast();
    },
  });

  // Report WebSocket metrics
  useEffect(() => {
    if (isAuthenticated && wsMetrics.totalAttempts > 0) {
      reportWebSocketMetrics("metrics_session", wsMetrics);
    }
  }, [isAuthenticated, wsMetrics]);

  sendRef.current = send;

  // Set session ID and re-subscribe
  const setSessionId = useCallback(
    (newSessionId: string | null) => {
      setSessionIdState(newSessionId);
      if (status === "connected") {
        send({
          type: "subscribe",
          payload: { session_id: newSessionId },
        });
        send({
          type: "get_snapshot",
          payload: { session_id: newSessionId },
        });
      }
    },
    [send, status],
  );

  const refresh = useCallback(() => {
    send({
      type: "get_snapshot",
      payload: { session_id: sessionId },
    });
  }, [send, sessionId]);

  const getMetric = useCallback(
    (name: string): MetricData | undefined => {
      return metrics[name];
    },
    [metrics],
  );

  return {
    status,
    metrics,
    sessionId,
    error,
    setSessionId,
    refresh,
    getMetric,
    disconnect,
    reconnect,
  };
}

export default useMetricsSessionWebSocket;
