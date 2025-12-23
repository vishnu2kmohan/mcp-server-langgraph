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
import { selectIsAuthenticated } from "../store/slices/authSlice";
import { addAlert, type Alert } from "../store/slices/alertSlice";
import { useRealtimeSync, type ConnectionStatus } from "./useRealtimeSync";
import { getAuthToken } from "../utils/storage";

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
 */
function getDefaultWebSocketUrl(): string {
  if (typeof window === "undefined") {
    return "ws://localhost:8000/api/v1/ws/alerts";
  }

  const protocol = window.location.protocol === "https:" ? "wss:" : "ws:";
  const host = window.location.host;

  // Get access token for authentication
  const token = getAuthToken();
  const tokenParam = token ? `?token=${encodeURIComponent(token)}` : "";

  return `${protocol}//${host}/api/v1/ws/alerts${tokenParam}`;
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

  // Compute WebSocket URL - recalculate when auth state changes
  // This ensures the token query param is included when user becomes authenticated

  const wsUrl = useMemo(() => url ?? getDefaultWebSocketUrl(), [url]);

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
  } = useRealtimeSync({
    url: wsUrl,
    reconnectInterval: 1000, // Base delay for first attempt
    maxReconnectAttempts: 10,
    exponentialBackoff: true, // Enable exponential backoff
    maxDelayMs: 30000, // Cap at 30 seconds
    backoffMultiplier: 2, // Double delay each attempt
    onMessage: handleMessage,
  });

  // Track if enabled - if not authenticated or explicitly disabled, override status
  // WebSocket requires valid auth token, so we only connect when authenticated
  const effectiveEnabled = enabled && isAuthenticated;
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
