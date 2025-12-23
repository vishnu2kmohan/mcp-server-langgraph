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
import { selectIsAuthenticated } from "../store/slices/authSlice";
import { addNotification } from "../store/slices/notificationSlice";
import type { AddNotificationPayload } from "../store/slices/notificationSlice";
import { useRealtimeSync, type ConnectionStatus } from "./useRealtimeSync";
import { getAuthToken } from "../utils/storage";

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
 */
function getDefaultWebSocketUrl(): string {
  if (typeof window === "undefined") {
    return "ws://localhost:8000/api/v1/ws/notifications";
  }

  const protocol = window.location.protocol === "https:" ? "wss:" : "ws:";

  // WebSocket URL routing:
  // - Vite dev server (localhost:5175): Use Vite proxy (configured in vite.config.ts)
  // - Gateway (localhost or localhost:80): Use gateway URL (Traefik routes /api/v1/ws/* to backend)
  // - Production: Use same origin (frontend and backend on same host)
  const host = window.location.host;
  // When running behind Vite dev server, the proxy handles routing to backend
  // No need to change the host - just use the same origin
  // For gateway (localhost, localhost:80) and production, use the same host

  // Get access token for authentication
  const token = getAuthToken();
  const tokenParam = token ? `?token=${encodeURIComponent(token)}` : "";

  return `${protocol}//${host}/api/v1/ws/notifications${tokenParam}`;
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

  // Compute WebSocket URL - recalculate when auth state changes
  // This ensures the token query param is included when user becomes authenticated
   
  const wsUrl = useMemo(
    () => url ?? getDefaultWebSocketUrl(),
    [url],
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
  } = useRealtimeSync({
    url: wsUrl,
    exponentialBackoff: true,
    reconnectInterval: 1000, // Start with 1 second
    maxDelayMs: 30000, // Max 30 seconds between attempts
    maxReconnectAttempts: 10, // Try up to 10 times
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
