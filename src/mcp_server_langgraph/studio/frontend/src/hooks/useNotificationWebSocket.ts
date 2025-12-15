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
import { useAppDispatch } from "../store/hooks";
import { addNotification } from "../store/slices/notificationSlice";
import type { AddNotificationPayload } from "../store/slices/notificationSlice";
import { useRealtimeSync, type ConnectionStatus } from "./useRealtimeSync";

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
    return "ws://localhost:8000/ws/notifications";
  }
  const protocol = window.location.protocol === "https:" ? "wss:" : "ws:";
  const host = window.location.host;
  return `${protocol}//${host}/ws/notifications`;
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

  // Compute WebSocket URL
  const wsUrl = useMemo(() => url ?? getDefaultWebSocketUrl(), [url]);

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
  const {
    status: realtimeStatus,
    disconnect: realtimeDisconnect,
    reconnect: realtimeReconnect,
  } = useRealtimeSync({
    url: wsUrl,
    reconnectInterval: 5000,
    maxReconnectAttempts: 10,
    onMessage: handleMessage,
  });

  // Track if enabled - if not, override status
  const status: ConnectionStatus = enabled ? realtimeStatus : "disconnected";

  // Track previous enabled state to detect changes
  const prevEnabledRef = useRef(enabled);

  // Disconnect when disabled, reconnect when enabled changes from false to true
  useEffect(() => {
    const wasDisabled = !prevEnabledRef.current;
    const isNowEnabled = enabled;

    if (!enabled) {
      realtimeDisconnect();
    } else if (wasDisabled && isNowEnabled) {
      // Only reconnect when transitioning from disabled to enabled
      realtimeReconnect();
    }

    prevEnabledRef.current = enabled;
  }, [enabled, realtimeDisconnect, realtimeReconnect]);

  return {
    status,
    disconnect: realtimeDisconnect,
    reconnect: realtimeReconnect,
  };
}
