/**
 * useNotificationWebSocket Hook
 *
 * Custom hook for real-time notification delivery via WebSocket.
 * Features:
 * - Connect to notifications WebSocket endpoint
 * - Dispatch notifications to Redux store
 * - Connection status tracking
 * - Automatic reconnection
 */

import { useEffect, useCallback, useMemo, useRef } from "react";
import { useAppDispatch, useAppSelector } from "../store/hooks";
import {
  logout,
  selectIsAuthenticated,
  selectIsInitializing,
} from "../store/slices/authSlice";
import { addNotification } from "../store/slices/notificationSlice";
import type { AddNotificationPayload } from "../store/slices/notificationSlice";
import { useRealtimeSync, type ConnectionStatus } from "./useRealtimeSync";
import { buildWebSocketUrl, WS_ENDPOINTS } from "../utils/websocket";
import { reportWebSocketMetrics } from "../utils/websocketTelemetry";

/**
 * Options for useNotificationWebSocket hook
 */
export interface UseNotificationWebSocketOptions {
  /** Custom WebSocket URL (default: constructs from window.location) */
  url?: string;
  /** Whether to enable the connection (default: true) */
  enabled?: boolean;
}

/**
 * Return type for useNotificationWebSocket hook
 */
export interface UseNotificationWebSocketReturn {
  /** Current connection status */
  status: ConnectionStatus;
  /** Manually disconnect */
  disconnect: () => void;
  /** Manually reconnect */
  reconnect: () => void;
}

/**
 * WebSocket message type for notifications
 */
interface NotificationMessage {
  type: "notification";
  payload: AddNotificationPayload;
}

/**
 * Check if a message is a valid notification message
 */
function isNotificationMessage(data: unknown): data is NotificationMessage {
  if (typeof data !== "object" || data === null) return false;
  const msg = data as Record<string, unknown>;
  if (msg.type !== "notification") return false;
  if (typeof msg.payload !== "object" || msg.payload === null) return false;
  const payload = msg.payload as Record<string, unknown>;
  return (
    typeof payload.type === "string" &&
    typeof payload.title === "string" &&
    typeof payload.message === "string"
  );
}

/**
 * Get the default WebSocket URL for notifications
 *
 * Uses standardized WebSocket utilities from src/utils/websocket.ts for:
 * - Environment variable support (VITE_API_HOST)
 * - Protocol detection (wss:// for https://)
 * - SSR-safe defaults
 */
function getDefaultWebSocketUrl(includeAuthToken: boolean = false): string {
  return buildWebSocketUrl(WS_ENDPOINTS.NOTIFICATIONS, {}, includeAuthToken);
}

/**
 * Hook for receiving real-time notifications via WebSocket
 *
 * @example
 * ```tsx
 * function App() {
 *   const { status } = useNotificationWebSocket();
 *
 *   return (
 *     <div>
 *       <span>Notification WS: {status}</span>
 *       <NotificationBell />
 *     </div>
 *   );
 * }
 * ```
 */
export function useNotificationWebSocket(
  options: UseNotificationWebSocketOptions = {},
): UseNotificationWebSocketReturn {
  const { url, enabled = true } = options;
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
      if (isNotificationMessage(data)) {
        dispatch(addNotification(data.payload));
      }
    },
    [dispatch],
  );

  // Use the underlying realtimeSync hook
  // Enable exponential backoff for better reconnection behavior
  const {
    status: realtimeStatus,
    disconnect: realtimeDisconnect,
    reconnect: realtimeReconnect,
    metrics,
  } = useRealtimeSync({
    url: wsUrl,
    exponentialBackoff: true,
    reconnectInterval: 1000, // Start with 1 second
    maxDelayMs: 30000, // Max 30 seconds between attempts
    maxReconnectAttempts: 10, // Try up to 10 times
    onMessage: handleMessage,
    onTokenExpired: () => dispatch(logout()),
  });

  // Track if enabled - if not auth-ready or explicitly disabled, override status
  // WebSocket requires valid auth token and completed auth initialization
  const effectiveEnabled = enabled && isAuthReady;

  // Report WebSocket metrics for observability
  useEffect(() => {
    if (effectiveEnabled && metrics.totalAttempts > 0) {
      reportWebSocketMetrics("notifications", metrics);
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
