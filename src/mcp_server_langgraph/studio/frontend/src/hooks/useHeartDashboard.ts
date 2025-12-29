/**
 * useHeartDashboard Hook
 *
 * Sprint 4 - Phase 3.3: HEART Metrics Analytics Dashboard
 * Sprint 5 - Phase 1.1: Real-time WebSocket Integration
 *
 * Hook for fetching and managing HEART metrics dashboard data:
 * - Time range selection (7d/30d/90d)
 * - Data fetching with loading/error states
 * - Dimension data extraction
 * - Manual and auto-refresh functionality
 * - Real-time WebSocket updates (when enableRealtime=true)
 *
 * @example
 * ```tsx
 * const {
 *   loading,
 *   error,
 *   data,
 *   dimensions,
 *   overallScore,
 *   timeRange,
 *   setTimeRange,
 *   refresh,
 *   wsStatus,
 *   isRealtime,
 *   alerts,
 * } = useHeartDashboard({ autoRefreshMs: 60000, enableRealtime: true });
 *
 * if (loading) return <Loading />;
 * if (error) return <Error message={error} />;
 *
 * return (
 *   <>
 *     <OverallScore score={overallScore} />
 *     {dimensions.map(dim => <DimensionCard key={dim.dimension} {...dim} />)}
 *     {alerts.map(alert => <AlertBanner key={alert.dimension} {...alert} />)}
 *   </>
 * );
 * ```
 */

import { useState, useCallback, useEffect, useMemo, useRef } from "react";
import { useNavigate } from "react-router";
import type { MetricsSummary } from "../analytics/gsm";
import { buildWebSocketUrl } from "../utils/websocket";
import { authenticatedFetch } from "../utils/authenticatedFetch";
import { saveCurrentRouteAsIntended } from "../utils/intendedRoute";
import { useRealtimeSync } from "./useRealtimeSync";
import { useAppDispatch } from "../store/hooks";
import { logout } from "../store/slices/authSlice";
import { addNotification } from "../store/slices/notificationSlice";
import type {
  HeartMetricsSnapshot,
  ThresholdAlert,
  DimensionMetrics,
} from "./useHeartMetricsWebSocket";
import { PROTOCOL_VERSION_MISMATCH_NOTIFICATION } from "../utils/websocketAuth";

// =============================================================================
// Local Types for WebSocket dimension data
// =============================================================================

/**
 * Simplified dimension score for WebSocket and dashboard display.
 * This differs from analytics/gsm/DimensionScore which includes goalProgresses.
 */
export interface DashboardDimensionScore {
  /** HEART dimension name */
  dimension:
    | "happiness"
    | "engagement"
    | "adoption"
    | "retention"
    | "task_success";
  /** Score value (0-100) */
  score: number;
  /** Trend direction */
  trend: "up" | "down" | "stable";
  /** Number of samples */
  samples: number;
}

// =============================================================================
// Types
// =============================================================================

export type TimeRange = "7d" | "30d" | "90d";

export interface UseHeartDashboardOptions {
  /** Initial time range (default: "30d") */
  initialTimeRange?: TimeRange;
  /** Auto-refresh interval in ms (disabled if not set) */
  autoRefreshMs?: number;
  /** Enable real-time WebSocket updates (default: false) */
  enableRealtime?: boolean;
  /** Custom WebSocket URL (defaults to /api/v1/ws/metrics/heart) */
  wsUrl?: string;
}

/** WebSocket connection status */
export type WsStatus =
  | "connecting"
  | "connected"
  | "disconnected"
  | "reconnecting"
  | "error";

export interface UseHeartDashboardResult {
  /** Loading state */
  loading: boolean;
  /** Error message if fetch failed */
  error: string | null;
  /** Raw metrics data */
  data: MetricsSummary | null;
  /** HEART dimensions array (simplified for dashboard display) */
  dimensions: DashboardDimensionScore[];
  /** Overall health score (0-100) */
  overallScore: number;
  /** Data point count */
  dataPointCount: number;
  /** Current time range */
  timeRange: TimeRange;
  /** Set time range (triggers refetch) */
  setTimeRange: (range: TimeRange) => void;
  /** Manual refresh function */
  refresh: () => Promise<void>;
  /** WebSocket connection status (only present when enableRealtime=true) */
  wsStatus?: WsStatus;
  /** WebSocket error message (only present when WebSocket error occurs) */
  wsError?: string | null;
  /** Whether data is being updated in real-time via WebSocket */
  isRealtime?: boolean;
  /** Threshold alerts from WebSocket */
  alerts: ThresholdAlert[];
  /** Subscribe to a specific dimension for updates */
  subscribeDimension?: (dimension: string) => void;
  /** Unsubscribe from a specific dimension */
  unsubscribeDimension?: (dimension: string) => void;
}

// =============================================================================
// Constants
// =============================================================================

const API_ENDPOINT = "/api/v1/metrics/heart/aggregate";

/**
 * Convert WebSocket snapshot to DashboardDimensionScore array
 */
function snapshotToDimensions(
  snapshot: HeartMetricsSnapshot,
): DashboardDimensionScore[] {
  const dimensionOrder = [
    "happiness",
    "engagement",
    "adoption",
    "retention",
    "task_success",
  ] as const;

  return dimensionOrder.map((dim) => ({
    dimension: dim,
    score: snapshot[dim]?.score ?? 0,
    trend: snapshot[dim]?.trend ?? "stable",
    samples: snapshot[dim]?.samples ?? 0,
  }));
}

/**
 * Calculate overall score from dimensions
 */
function calculateOverallScore(dimensions: DashboardDimensionScore[]): number {
  if (dimensions.length === 0) return 0;
  const sum = dimensions.reduce((acc, dim) => acc + dim.score, 0);
  return Math.round((sum / dimensions.length) * 10) / 10;
}

// =============================================================================
// WebSocket Message Types
// =============================================================================

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

interface ErrorMessage {
  type: "error";
  message: string;
}

type ServerMessage =
  | MetricsSnapshotMessage
  | DimensionUpdateMessage
  | ThresholdAlertMessage
  | ErrorMessage
  | { type: string };

// =============================================================================
// Hook Implementation
// =============================================================================

export function useHeartDashboard(
  options: UseHeartDashboardOptions = {},
): UseHeartDashboardResult {
  const navigate = useNavigate();
  const dispatch = useAppDispatch();
  const {
    initialTimeRange = "30d",
    autoRefreshMs,
    enableRealtime = false,
    wsUrl,
  } = options;

  // Handle auth failure - redirect to login
  const handleAuthFailure = useCallback(() => {
    saveCurrentRouteAsIntended();
    navigate("/login", { replace: true });
  }, [navigate]);

  // State
  const [timeRange, setTimeRange] = useState<TimeRange>(initialTimeRange);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [data, setData] = useState<MetricsSummary | null>(null);

  // WebSocket-specific state
  const [wsError, setWsError] = useState<string | null>(null);
  const [alerts, setAlerts] = useState<ThresholdAlert[]>([]);
  const [realtimeDimensions, setRealtimeDimensions] = useState<
    DashboardDimensionScore[] | null
  >(null);

  // Refs
  const refreshTimerRef = useRef<ReturnType<typeof setInterval> | null>(null);
  const isMountedRef = useRef(true);
  // Keep wsUrl ref for potential future use (reconnection with updated URL)
  const _callbacksRef = useRef({ wsUrl });

  /**
   * Fetch metrics data from API
   */
  const fetchData = useCallback(async (): Promise<void> => {
    setLoading(true);
    setError(null);

    try {
      const response = await authenticatedFetch(
        `${API_ENDPOINT}?range=${timeRange}`,
        {
          onAuthFailure: handleAuthFailure,
        },
      );

      if (!response.ok) {
        throw new Error(`Failed to fetch analytics: ${response.status}`);
      }

      const metricsData: MetricsSummary = await response.json();

      if (isMountedRef.current) {
        setData(metricsData);
        setError(null);
      }
    } catch (err) {
      if (isMountedRef.current) {
        setError(err instanceof Error ? err.message : "Unknown error");
        setData(null);
      }
    } finally {
      if (isMountedRef.current) {
        setLoading(false);
      }
    }
  }, [timeRange, handleAuthFailure]);

  /**
   * Manual refresh function
   */
  const refresh = useCallback(async (): Promise<void> => {
    await fetchData();
  }, [fetchData]);

  // Extract data point count
  const dataPointCount = useMemo(() => {
    return data?.dataPointCount ?? 0;
  }, [data]);

  // WebSocket message handler
  const handleMessage = useCallback((messageData: unknown) => {
    if (!isMountedRef.current) return;

    const message = messageData as ServerMessage;

    switch (message.type) {
      case "metrics_snapshot": {
        const snapshotMsg = message as MetricsSnapshotMessage;
        const dims = snapshotToDimensions(snapshotMsg.snapshot);
        setRealtimeDimensions(dims);
        setWsError(null);
        break;
      }
      case "dimension_update": {
        const updateMsg = message as DimensionUpdateMessage;
        setRealtimeDimensions((prev) => {
          if (!prev) return prev;
          return prev.map((dim) =>
            dim.dimension === updateMsg.dimension
              ? {
                  ...dim,
                  score: updateMsg.metrics.score,
                  trend: updateMsg.metrics.trend,
                  samples: updateMsg.metrics.samples ?? dim.samples,
                }
              : dim,
          );
        });
        break;
      }
      case "threshold_alert": {
        const alertMsg = message as ThresholdAlertMessage;
        setAlerts((prev) => [...prev, alertMsg.alert]);
        break;
      }
      case "error": {
        const errorMsg = message as ErrorMessage;
        setWsError(errorMsg.message);
        break;
      }
    }
  }, []);

  // WebSocket connection (only when enableRealtime is true)
  // Include auth token since backend requires authentication
  const websocketUrl = useMemo(
    () => (enableRealtime && wsUrl ? buildWebSocketUrl(wsUrl, {}, true) : ""),
    [enableRealtime, wsUrl],
  );

  // WebSocket connection options (empty URL disables connection)
  const wsOptions = useMemo(
    () => ({
      url: enableRealtime ? websocketUrl : "",
      onMessage: handleMessage,
      exponentialBackoff: true,
      reconnectInterval: 1000,
      maxDelayMs: 30000,
      maxReconnectAttempts: 10,
      onTokenExpired: () => dispatch(logout()),
      onProtocolVersionMismatch: () => {
        dispatch(addNotification(PROTOCOL_VERSION_MISMATCH_NOTIFICATION));
      },
    }),
    [enableRealtime, websocketUrl, handleMessage, dispatch],
  );

  const {
    status: wsConnectionStatus,
    send: wsSend,
    disconnect: _wsDisconnect,
    reconnect: _wsReconnect,
    metrics: wsMetrics,
  } = useRealtimeSync(wsOptions);

  // Report WebSocket metrics for observability
  useEffect(() => {
    if (enableRealtime && wsMetrics.totalAttempts > 0) {
      import("../utils/websocketTelemetry").then(
        ({ reportWebSocketMetrics }) => {
          reportWebSocketMetrics("heart_dashboard", wsMetrics);
        },
      );
    }
  }, [enableRealtime, wsMetrics]);

  // Map WebSocket status to our WsStatus type
  const wsStatus = useMemo<WsStatus | undefined>(() => {
    if (!enableRealtime) return undefined;
    return wsConnectionStatus as WsStatus;
  }, [enableRealtime, wsConnectionStatus]);

  // Determine if we're receiving real-time updates
  const isRealtime = useMemo(() => {
    return enableRealtime && wsConnectionStatus === "connected";
  }, [enableRealtime, wsConnectionStatus]);

  // Use real-time dimensions if available and connected, otherwise use polled data
  // Convert API DimensionScore to DashboardDimensionScore format
  const dimensions = useMemo<DashboardDimensionScore[]>(() => {
    if (isRealtime && realtimeDimensions) {
      return realtimeDimensions;
    }
    // Convert API response to dashboard format
    if (!data?.dimensions) return [];
    return data.dimensions.map((dim) => ({
      dimension: dim.dimension,
      score: dim.overallScore,
      trend: "stable" as const, // API doesn't provide trend, default to stable
      samples: dim.goalProgresses?.length ?? 0,
    }));
  }, [isRealtime, realtimeDimensions, data]);

  // Calculate overall score from current dimensions
  const overallScore = useMemo(() => {
    if (isRealtime && realtimeDimensions) {
      return calculateOverallScore(realtimeDimensions);
    }
    return data?.overallHealthScore ?? 0;
  }, [isRealtime, realtimeDimensions, data]);

  // Subscribe to a dimension for real-time updates
  const subscribeDimension = useCallback(
    (dimension: string) => {
      if (wsSend) {
        wsSend(JSON.stringify({ type: "subscribe", dimension }));
      }
    },
    [wsSend],
  );

  // Unsubscribe from a dimension
  const unsubscribeDimension = useCallback(
    (dimension: string) => {
      if (wsSend) {
        wsSend(JSON.stringify({ type: "unsubscribe", dimension }));
      }
    },
    [wsSend],
  );

  // Fetch data on mount and when timeRange changes
  useEffect(() => {
    isMountedRef.current = true;
    fetchData();

    return () => {
      isMountedRef.current = false;
    };
  }, [fetchData]);

  // Auto-refresh timer (only when not using real-time or as fallback)
  useEffect(() => {
    // Skip polling if using real-time and connected
    if (isRealtime) {
      return;
    }

    if (!autoRefreshMs) {
      return;
    }

    refreshTimerRef.current = setInterval(() => {
      if (isMountedRef.current) {
        fetchData();
      }
    }, autoRefreshMs);

    return () => {
      if (refreshTimerRef.current) {
        clearInterval(refreshTimerRef.current);
        refreshTimerRef.current = null;
      }
    };
  }, [autoRefreshMs, fetchData, isRealtime]);

  // Request fresh snapshot when time range changes (for WebSocket)
  useEffect(() => {
    if (enableRealtime && wsSend && wsConnectionStatus === "connected") {
      wsSend(JSON.stringify({ type: "set_time_range", time_range: timeRange }));
    }
  }, [enableRealtime, wsSend, wsConnectionStatus, timeRange]);

  return {
    loading,
    error,
    data,
    dimensions,
    overallScore,
    dataPointCount,
    timeRange,
    setTimeRange,
    refresh,
    // WebSocket-specific properties
    wsStatus,
    wsError,
    isRealtime,
    alerts,
    subscribeDimension: enableRealtime ? subscribeDimension : undefined,
    unsubscribeDimension: enableRealtime ? unsubscribeDimension : undefined,
  };
}

export default useHeartDashboard;
