/**
 * useAIRealTimeSuggestions - WebSocket hook for real-time AI suggestions
 *
 * Provides real-time AI-powered suggestions via WebSocket connection.
 * Uses useRealtimeSync for underlying WebSocket management.
 *
 * Features:
 * - Automatic connection management with reconnection
 * - Heartbeat ping/pong for connection health
 * - Suggestion storage and dismissal tracking
 * - Request suggestions with context
 */

import { useState, useCallback, useRef, useEffect } from "react";
import { useAppDispatch, useAppSelector } from "../store/hooks";
import { logout } from "../store/slices/authSlice";
import { addNotification } from "../store/slices/notificationSlice";
import { buildWebSocketUrl, WS_ENDPOINTS } from "../utils/websocket";
import { useRealtimeSync } from "./useRealtimeSync";
import {
  PROTOCOL_VERSION_MISMATCH_NOTIFICATION,
  showProtocolVersionMismatchToast,
} from "../utils/websocketAuth";
import { reportWebSocketMetrics } from "../utils/websocketTelemetry";

/** Suggestion type from the AI UX backend */
export interface Suggestion {
  id: string;
  type: "tooltip" | "spotlight" | "banner" | "modal";
  message: string;
  priority: "low" | "medium" | "high";
  targetElement?: string;
  showAfterMs?: number;
}

/** Options for the useAIRealTimeSuggestions hook */
export interface UseAIRealTimeSuggestionsOptions {
  /** Whether to enable WebSocket connection */
  enabled: boolean;
  /** Interval for reconnection attempts in ms (default: 5000) */
  reconnectInterval?: number;
  /** Maximum number of reconnection attempts (default: 5) */
  maxReconnectAttempts?: number;
  /** Interval for heartbeat ping in ms (default: 30000) */
  heartbeatInterval?: number;
}

/** Context for requesting suggestions */
export interface SuggestionRequestContext {
  page?: string;
  action?: string;
  [key: string]: unknown;
}

/** Return type for the hook */
export interface UseAIRealTimeSuggestionsReturn {
  /** Whether WebSocket is connected */
  isConnected: boolean;
  /** Current connection error, if any */
  error: Error | null;
  /** Current list of active suggestions */
  suggestions: Suggestion[];
  /** IDs of dismissed suggestions */
  dismissedIds: string[];
  /** Number of reconnection attempts made */
  reconnectAttempts: number;
  /** Timestamp of last successful heartbeat */
  lastHeartbeat: number | null;
  /** Request new suggestions with context */
  requestSuggestions: (context: SuggestionRequestContext) => void;
  /** Clear all current suggestions */
  clearSuggestions: () => void;
  /** Dismiss a specific suggestion by ID */
  dismissSuggestion: (id: string) => void;
}

/** WebSocket message types */
interface WebSocketMessage {
  type: string;
  data?: Suggestion[];
  timestamp?: number;
}

/**
 * Hook for real-time AI suggestions via WebSocket
 *
 * @param options - Configuration options
 * @returns WebSocket state and control functions
 *
 * @example
 * ```tsx
 * const {
 *   isConnected,
 *   suggestions,
 *   requestSuggestions,
 *   dismissSuggestion
 * } = useAIRealTimeSuggestions({ enabled: true });
 *
 * // Request suggestions for current context
 * requestSuggestions({ page: 'chat', action: 'typing' });
 *
 * // Dismiss a suggestion
 * dismissSuggestion('nudge-1');
 * ```
 */
export function useAIRealTimeSuggestions(
  options: UseAIRealTimeSuggestionsOptions,
): UseAIRealTimeSuggestionsReturn {
  const {
    enabled,
    reconnectInterval = 5000,
    maxReconnectAttempts = 5,
    heartbeatInterval = 30000,
  } = options;

  // Redux dispatch for token expiration handling
  const dispatch = useAppDispatch();

  // Get user ID from Redux store
  const userId = useAppSelector((state) => state.auth?.user?.id ?? "anonymous");

  // State
  const [error, setError] = useState<Error | null>(null);
  const [lastHeartbeat, setLastHeartbeat] = useState<number | null>(null);
  const [suggestions, setSuggestions] = useState<Suggestion[]>([]);
  const [dismissedIds, setDismissedIds] = useState<string[]>([]);

  // Refs
  const heartbeatTimerRef = useRef<ReturnType<typeof setInterval> | null>(null);
  const dismissedIdsRef = useRef<string[]>([]);

  // Keep ref in sync with state
  dismissedIdsRef.current = dismissedIds;

  /**
   * Handle incoming WebSocket messages
   */
  const handleMessage = useCallback((data: unknown) => {
    try {
      const message = data as WebSocketMessage;

      switch (message.type) {
        case "suggestions":
          if (Array.isArray(message.data)) {
            // Filter out dismissed suggestions
            const newSuggestions = message.data.filter(
              (s) => !dismissedIdsRef.current.includes(s.id),
            );
            setSuggestions((prev) => [...prev, ...newSuggestions]);
          }
          break;

        case "pong":
          setLastHeartbeat(message.timestamp ?? Date.now());
          break;

        case "error":
          setError(new Error(String(message.data)));
          break;

        default:
          // Unknown message type, ignore
          break;
      }
    } catch {
      // Failed to parse message, ignore
    }
  }, []);

  /**
   * Handle connection errors
   */
  const handleError = useCallback((err: Error) => {
    setError(err);
  }, []);

  /**
   * Handle connection established
   */
  const handleConnect = useCallback(() => {
    setError(null);
  }, []);

  // Build WebSocket URL with proper endpoint and auth token
  // NOTE: user_id is still passed as a fallback identifier but the JWT token
  // (via includeAuthToken=true) is what the backend uses for authentication
  const wsUrl = enabled
    ? buildWebSocketUrl(WS_ENDPOINTS.AI_SUGGESTIONS, { user_id: userId }, true)
    : "";

  // Use the realtime sync hook
  const { status, reconnectAttempts, send, metrics } = useRealtimeSync({
    url: wsUrl,
    reconnectInterval,
    maxReconnectAttempts,
    onMessage: handleMessage,
    onError: handleError,
    onConnect: handleConnect,
    onTokenExpired: () => dispatch(logout()),
    onProtocolVersionMismatch: () => {
      dispatch(addNotification(PROTOCOL_VERSION_MISMATCH_NOTIFICATION));
      showProtocolVersionMismatchToast();
    },
  });

  // Determine if connected
  const isConnected = status === "connected";

  // Report WebSocket metrics for observability
  useEffect(() => {
    if (enabled && metrics.totalAttempts > 0) {
      reportWebSocketMetrics("ai_realtime_suggestions", metrics);
    }
  }, [enabled, metrics]);

  /**
   * Start heartbeat interval
   */
  useEffect(() => {
    if (!isConnected) {
      if (heartbeatTimerRef.current) {
        clearInterval(heartbeatTimerRef.current);
        heartbeatTimerRef.current = null;
      }
      return;
    }

    heartbeatTimerRef.current = setInterval(() => {
      send({ type: "ping", timestamp: Date.now() });
    }, heartbeatInterval);

    return () => {
      if (heartbeatTimerRef.current) {
        clearInterval(heartbeatTimerRef.current);
        heartbeatTimerRef.current = null;
      }
    };
  }, [isConnected, heartbeatInterval, send]);

  /**
   * Request suggestions with context
   */
  const requestSuggestions = useCallback(
    (context: SuggestionRequestContext) => {
      send({
        type: "request_suggestions",
        context,
        timestamp: Date.now(),
      });
    },
    [send],
  );

  /**
   * Clear all suggestions
   */
  const clearSuggestions = useCallback(() => {
    setSuggestions([]);
  }, []);

  /**
   * Dismiss a specific suggestion
   */
  const dismissSuggestion = useCallback((id: string) => {
    setDismissedIds((prev) => [...prev, id]);
    setSuggestions((prev) => prev.filter((s) => s.id !== id));
  }, []);

  return {
    isConnected,
    error,
    suggestions,
    dismissedIds,
    reconnectAttempts,
    lastHeartbeat,
    requestSuggestions,
    clearSuggestions,
    dismissSuggestion,
  };
}

export default useAIRealTimeSuggestions;
