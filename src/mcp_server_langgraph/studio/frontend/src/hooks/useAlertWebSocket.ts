/**
 * useAlertWebSocket Hook
 *
 * Custom hook for real-time alert delivery via WebSocket for Admin dashboard.
 *
 * Features:
 * - Connect to alerts WebSocket endpoint
 * - Dispatch alerts to Redux store
 * - Trigger toast notifications for critical alerts
 * - Connection status tracking
 * - Automatic reconnection
 *
 * Reference: ADR-0026 - Comprehensive Client Resilience Patterns
 */

import { useEffect, useCallback, useMemo, useRef } from "react";
import { toast } from "sonner";
import { useAppDispatch, useAppSelector } from "../store/hooks";
import {
  logout,
  selectIsAuthenticated,
  selectIsInitializing,
} from "../store/slices/authSlice";
import { addAlert, type Alert } from "../store/slices/alertSlice";
import { useRealtimeSync, type ConnectionStatus } from "./useRealtimeSync";
import { buildWebSocketUrl, WS_ENDPOINTS } from "../utils/websocket";
import { reportWebSocketMetrics } from "../utils/websocketTelemetry";

// =============================================================================
// Types
// =============================================================================

/**
 * Options for useAlertWebSocket hook
 */
export interface UseAlertWebSocketOptions {
  /** Custom WebSocket URL (default: constructs from window.location) */
  url?: string;
  /** Whether to enable the connection (default: true) */
  enabled?: boolean;
  /** Show toast notifications for critical alerts (default: true) */
  showToasts?: boolean;
}

/**
 * Return type for useAlertWebSocket hook
 */
export interface UseAlertWebSocketReturn {
  /** Current connection status */
  status: ConnectionStatus;
  /** Manually disconnect */
  disconnect: () => void;
  /** Manually reconnect */
  reconnect: () => void;
}

/**
 * WebSocket message type for single alert
 */
export interface AlertMessage {
  type: "alert";
  payload: Alert;
}

/**
 * WebSocket message type for batch of alerts
 */
export interface AlertBatchMessage {
  type: "alert_batch";
  payload: Alert[];
}

/**
 * Union type for all alert message types
 */
export type AlertWebSocketMessage = AlertMessage | AlertBatchMessage;

// =============================================================================
// Message Parsing
// =============================================================================

/**
 * Check if a message is a valid alert message
 */
function isAlertMessage(data: unknown): data is AlertMessage {
  if (typeof data !== "object" || data === null) return false;
  const msg = data as Record<string, unknown>;
  if (msg.type !== "alert") return false;
  if (typeof msg.payload !== "object" || msg.payload === null) return false;
  const payload = msg.payload as Record<string, unknown>;
  return (
    typeof payload.alert_id === "string" &&
    typeof payload.name === "string" &&
    typeof payload.severity === "string" &&
    typeof payload.state === "string"
  );
}

/**
 * Check if a message is a valid alert batch message
 */
function isAlertBatchMessage(data: unknown): data is AlertBatchMessage {
  if (typeof data !== "object" || data === null) return false;
  const msg = data as Record<string, unknown>;
  if (msg.type !== "alert_batch") return false;
  if (!Array.isArray(msg.payload)) return false;
  // Check first item in array (if any) has required fields
  if (msg.payload.length > 0) {
    const first = msg.payload[0] as Record<string, unknown>;
    return (
      typeof first.alert_id === "string" &&
      typeof first.name === "string" &&
      typeof first.severity === "string" &&
      typeof first.state === "string"
    );
  }
  return true;
}

/**
 * Parse and validate an incoming WebSocket message
 */
export function parseAlertMessage(data: unknown): AlertWebSocketMessage | null {
  if (isAlertMessage(data)) {
    return data;
  }
  if (isAlertBatchMessage(data)) {
    return data;
  }
  return null;
}

// =============================================================================
// URL Construction
// =============================================================================

/**
 * Get the default WebSocket URL for alerts
 *
 * Uses standardized WebSocket utilities from src/utils/websocket.ts
 */
function getDefaultWebSocketUrl(includeAuthToken: boolean = false): string {
  return buildWebSocketUrl(WS_ENDPOINTS.ALERTS, {}, includeAuthToken);
}

// =============================================================================
// Toast Helpers
// =============================================================================

/**
 * Show toast notification for a critical alert
 */
function showCriticalAlertToast(alert: Alert): void {
  toast.error(`Critical: ${alert.name}`, {
    description: alert.message,
    duration: 10000,
  });
}

// =============================================================================
// Hook Implementation
// =============================================================================

/**
 * Hook for receiving real-time alerts via WebSocket
 *
 * @example
 * ```tsx
 * function AdminDashboard() {
 *   const { status } = useAlertWebSocket();
 *
 *   return (
 *     <div>
 *       <span>Alert WS: {status}</span>
 *       <AlertsPanel />
 *     </div>
 *   );
 * }
 * ```
 */
export function useAlertWebSocket(
  options: UseAlertWebSocketOptions = {},
): UseAlertWebSocketReturn {
  const { url, enabled = true, showToasts = true } = options;
  const dispatch = useAppDispatch();
  const isAuthenticated = useAppSelector(selectIsAuthenticated);
  const isInitializing = useAppSelector(selectIsInitializing);

  // Auth is ready when: authenticated AND not still initializing
  // This prevents WebSocket connection attempts during auth validation
  // which can cause "connection interrupted" errors during page load
  const isAuthReady = isAuthenticated && !isInitializing;

  // Compute WebSocket URL - only generate URL when auth is ready
  // Passing empty string prevents connection attempt before auth is validated
  // The buildWebSocketUrl utility fetches the auth token internally when includeAuthToken=true
  const wsUrl = useMemo(
    () =>
      isAuthReady
        ? (url ?? getDefaultWebSocketUrl(true /* includeAuthToken */))
        : "",
    [url, isAuthReady],
  );

  // Handle incoming messages
  const handleMessage = useCallback(
    (data: unknown) => {
      const message = parseAlertMessage(data);

      if (!message) {
        return;
      }

      if (message.type === "alert") {
        dispatch(addAlert(message.payload));

        // Show toast for critical alerts
        if (showToasts && message.payload.severity === "critical") {
          showCriticalAlertToast(message.payload);
        }
      } else if (message.type === "alert_batch") {
        for (const alert of message.payload) {
          dispatch(addAlert(alert));

          // Show toast for critical alerts
          if (showToasts && alert.severity === "critical") {
            showCriticalAlertToast(alert);
          }
        }
      }
    },
    [dispatch, showToasts],
  );

  // Use the underlying realtimeSync hook with exponential backoff
  const {
    status: realtimeStatus,
    disconnect: realtimeDisconnect,
    reconnect: realtimeReconnect,
    metrics,
  } = useRealtimeSync({
    url: wsUrl,
    reconnectInterval: 1000, // Base delay for first attempt
    maxReconnectAttempts: 10,
    exponentialBackoff: true, // Enable exponential backoff
    maxDelayMs: 30000, // Cap at 30 seconds
    backoffMultiplier: 2, // Double delay each attempt
    onMessage: handleMessage,
    onTokenExpired: () => dispatch(logout()),
  });

  // Track if enabled - if not auth-ready or explicitly disabled, override status
  // WebSocket requires valid auth token and completed auth initialization
  const effectiveEnabled = enabled && isAuthReady;

  // Report WebSocket metrics for observability
  useEffect(() => {
    if (effectiveEnabled && metrics.totalAttempts > 0) {
      reportWebSocketMetrics("alerts", metrics);
    }
  }, [effectiveEnabled, metrics]);
  const status: ConnectionStatus = effectiveEnabled
    ? realtimeStatus
    : "disconnected";

  // Track previous effective enabled state to detect changes
  const prevEnabledRef = useRef(effectiveEnabled);

  // Disconnect when disabled or unauthenticated, reconnect when transitioning to enabled+authenticated
  useEffect(() => {
    const wasDisabled = !prevEnabledRef.current;
    const isNowEnabled = effectiveEnabled;

    if (!effectiveEnabled) {
      realtimeDisconnect();
    } else if (wasDisabled && isNowEnabled) {
      // Only reconnect when transitioning from disabled to enabled+authenticated
      // This handles both explicit enable changes and authentication state changes
      realtimeReconnect();
    }

    prevEnabledRef.current = effectiveEnabled;
  }, [effectiveEnabled, realtimeDisconnect, realtimeReconnect]);

  return {
    status,
    disconnect: realtimeDisconnect,
    reconnect: realtimeReconnect,
  };
}
