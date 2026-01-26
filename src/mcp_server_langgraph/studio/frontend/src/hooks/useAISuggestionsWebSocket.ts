/**
 * useAISuggestionsWebSocket Hook
 *
 * Custom hook for real-time AI suggestion streaming via WebSocket.
 * Connects to /api/v1/ws/ai/suggestions endpoint for typing suggestions.
 *
 * Features:
 * - Request AI suggestions based on input context
 * - Session-aware completions
 * - Accept/reject feedback for learning
 * - Context updates for better suggestions
 * - Automatic reconnection with exponential backoff
 * - Token expiration handling
 *
 * Uses typed protocols from @/types/websocket-protocols for type-safe
 * message handling and validation.
 */

import { useState, useCallback, useRef, useMemo, useEffect } from "react";
import debounce from "lodash/debounce";
import {
  useRealtimeSync,
  type WebSocketConnectionStatus,
} from "./useRealtimeSync";
import { useAppDispatch, useAppSelector } from "../store/hooks";
import {
  logout,
  selectIsAuthenticated,
  selectWebSocketPermissions,
} from "../store/slices/authSlice";
import { addNotification } from "../store/slices/notificationSlice";
import { buildWebSocketUrl, WS_ENDPOINTS } from "../utils/websocket";
import {
  PROTOCOL_VERSION_MISMATCH_NOTIFICATION,
  showProtocolVersionMismatchToast,
} from "../utils/websocketAuth";
import { reportWebSocketMetrics } from "../utils/websocketTelemetry";

// Import typed protocols for type-safe WebSocket message handling
import {
  isSuggestionResponseEntry,
  isWebSocketError,
} from "../types/websocket-protocols";
import type {
  SuggestionResponseEntry,
  AISuggestionsMessage,
  WebSocketError,
} from "../types/websocket-protocols";

// ============================================================================
// Types
// ============================================================================

/**
 * AI suggestion from the server (frontend-friendly format)
 */
export interface AISuggestion {
  suggestionId: string;
  text: string;
  confidence: number;
  reasoning?: string;
}

/**
 * AI suggestion error (frontend-friendly format)
 */
export interface AISuggestionError {
  code: string;
  message: string;
  retryable: boolean;
}

// Re-export protocol types for consumers
export type { SuggestionResponseEntry, AISuggestionsMessage, WebSocketError };

/**
 * Options for useAISuggestionsWebSocket hook
 */
export interface UseAISuggestionsWebSocketOptions {
  /** Custom WebSocket URL (default: constructs from window.location) */
  url?: string;
  /** Whether to enable the connection (default: true) */
  enabled?: boolean;
  /** Session ID for context-aware suggestions */
  sessionId?: string;
  /** Callback when a suggestion is received */
  onSuggestion?: (suggestion: AISuggestion) => void;
  /** Callback when an error is received */
  onError?: (error: AISuggestionError) => void;
  /** Debounce delay for suggestion requests in milliseconds (default: 300) */
  debounceMs?: number;
}

/**
 * Return type for useAISuggestionsWebSocket hook
 */
export interface UseAISuggestionsWebSocketReturn {
  /** Current connection status */
  status: WebSocketConnectionStatus;
  /** Most recent suggestion */
  currentSuggestion: AISuggestion | null;
  /** Whether a suggestion request is pending */
  isPending: boolean;
  /** Most recent error */
  lastError: AISuggestionError | null;
  /** Request an AI suggestion (immediate, no debouncing) */
  requestSuggestion: (
    inputText: string,
    cursorPosition: number,
    contextWindow?: number,
  ) => void;
  /** Request an AI suggestion (debounced - recommended for typing scenarios) */
  requestSuggestionDebounced: (
    inputText: string,
    cursorPosition: number,
    contextWindow?: number,
  ) => void;
  /** Cancel any pending debounced suggestion request */
  cancelDebouncedRequest: () => void;
  /** Accept the current suggestion */
  acceptSuggestion: (suggestionId: string) => void;
  /** Reject the current suggestion */
  rejectSuggestion: (suggestionId: string, reason?: string) => void;
  /** Update session context */
  updateContext: (context: string) => void;
  /** Clear the current suggestion */
  clearSuggestion: () => void;
  /** Disconnect from WebSocket */
  disconnect: () => void;
  /** Reconnect to WebSocket */
  reconnect: () => void;
}

// ============================================================================
// Helper Functions
// ============================================================================

/**
 * Get default AI suggestions WebSocket URL
 */
function getDefaultWebSocketUrl(includeToken: boolean = true): string {
  return buildWebSocketUrl(WS_ENDPOINTS.AI_SUGGESTIONS, {}, includeToken);
}

/**
 * Parse AI suggestion from backend payload
 */
function parseSuggestion(payload: Record<string, unknown>): AISuggestion {
  return {
    suggestionId: (payload.suggestion_id as string) || "",
    text: (payload.text as string) || "",
    confidence: (payload.confidence as number) || 0,
    reasoning: payload.reasoning as string | undefined,
  };
}

/**
 * Parse error from backend payload
 */
function parseError(payload: Record<string, unknown>): AISuggestionError {
  return {
    code: (payload.code as string) || "unknown",
    message: (payload.message as string) || "Unknown error",
    retryable: (payload.retryable as boolean) || false,
  };
}

// Type guards are now imported from centralized websocket-protocols.ts:
// - isSuggestionResponseEntry: checks for suggestion_response messages
// - isWebSocketError: checks for error messages

// ============================================================================
// Hook Implementation
// ============================================================================

/**
 * Hook for real-time AI suggestion streaming
 *
 * @example
 * ```tsx
 * function TextEditor({ sessionId }: { sessionId: string }) {
 *   const [text, setText] = useState("");
 *
 *   const { currentSuggestion, requestSuggestion, acceptSuggestion } =
 *     useAISuggestionsWebSocket({
 *       sessionId,
 *       onSuggestion: (suggestion) => {
 *         console.log("Got suggestion:", suggestion.text);
 *       },
 *     });
 *
 *   const handleKeyUp = useCallback(
 *     (e: React.KeyboardEvent) => {
 *       // Request suggestion after typing pause
 *       const cursorPos = (e.target as HTMLTextAreaElement).selectionStart;
 *       requestSuggestion(text, cursorPos);
 *     },
 *     [text, requestSuggestion],
 *   );
 *
 *   return (
 *     <div>
 *       <textarea value={text} onChange={(e) => setText(e.target.value)} onKeyUp={handleKeyUp} />
 *       {currentSuggestion && (
 *         <SuggestionOverlay
 *           suggestion={currentSuggestion}
 *           onAccept={() => acceptSuggestion(currentSuggestion.suggestionId)}
 *         />
 *       )}
 *     </div>
 *   );
 * }
 * ```
 */
export function useAISuggestionsWebSocket(
  options: UseAISuggestionsWebSocketOptions = {},
): UseAISuggestionsWebSocketReturn {
  const {
    url,
    enabled = true,
    sessionId,
    onSuggestion,
    onError,
    debounceMs = 300,
  } = options;

  // Redux dispatch for token expiration handling
  const dispatch = useAppDispatch();
  const isAuthenticated = useAppSelector(selectIsAuthenticated);
  const wsPermissions = useAppSelector(selectWebSocketPermissions);

  // Check if user has permission for AI suggestions WebSocket
  const hasAISuggestionsPermission = wsPermissions?.ai_suggestions ?? false;

  // State
  const [currentSuggestion, setCurrentSuggestion] =
    useState<AISuggestion | null>(null);
  const [isPending, setIsPending] = useState(false);
  const [lastError, setLastError] = useState<AISuggestionError | null>(null);

  // Refs
  const sessionIdRef = useRef(sessionId);
  const callbacksRef = useRef({ onSuggestion, onError });

  // Keep refs updated
  useEffect(() => {
    sessionIdRef.current = sessionId;
    callbacksRef.current = { onSuggestion, onError };
  }, [sessionId, onSuggestion, onError]);

  // Compute WebSocket URL - only generate URL when authenticated AND has permission
  const wsUrl = useMemo(
    () =>
      isAuthenticated && hasAISuggestionsPermission
        ? (url ?? getDefaultWebSocketUrl(true))
        : "",
    [url, isAuthenticated, hasAISuggestionsPermission],
  );

  // Track effective enabled state - requires auth and permission
  const effectiveEnabled =
    enabled && isAuthenticated && hasAISuggestionsPermission;

  // Handle incoming messages using centralized type guards
  const handleMessage = useCallback((data: unknown) => {
    // Use centralized type guard for suggestion responses
    if (isSuggestionResponseEntry(data)) {
      const suggestion = parseSuggestion(
        (data.payload || {}) as unknown as Record<string, unknown>,
      );
      setCurrentSuggestion(suggestion);
      setIsPending(false);
      setLastError(null);
      callbacksRef.current.onSuggestion?.(suggestion);
    } else if (isWebSocketError(data)) {
      // Use centralized type guard for WebSocket errors
      const error = parseError(
        (data.payload || {}) as unknown as Record<string, unknown>,
      );
      setLastError(error);
      setIsPending(false);
      callbacksRef.current.onError?.(error);
    }
  }, []);

  // Use the underlying realtimeSync hook
  const {
    status: realtimeStatus,
    send,
    disconnect,
    reconnect,
    metrics,
  } = useRealtimeSync({
    url: effectiveEnabled ? wsUrl : "",
    exponentialBackoff: true,
    reconnectInterval: 1000,
    maxDelayMs: 30000,
    maxReconnectAttempts: 10,
    onMessage: handleMessage,
    onTokenExpired: () => dispatch(logout()),
    onProtocolVersionMismatch: () => {
      dispatch(addNotification(PROTOCOL_VERSION_MISMATCH_NOTIFICATION));
      showProtocolVersionMismatchToast();
    },
  });

  // Report WebSocket metrics for observability
  useEffect(() => {
    if (effectiveEnabled && metrics.totalAttempts > 0) {
      reportWebSocketMetrics("ai_suggestions", metrics);
    }
  }, [effectiveEnabled, metrics]);

  // Override status if not enabled
  const status: WebSocketConnectionStatus = effectiveEnabled
    ? realtimeStatus
    : "disconnected";

  // Request an AI suggestion (immediate, no debouncing)
  const requestSuggestion = useCallback(
    (
      inputText: string,
      cursorPosition: number,
      contextWindow: number = 500,
    ) => {
      if (!sessionIdRef.current) {
        console.warn("Session ID required for AI suggestions");
        return;
      }

      setIsPending(true);
      setLastError(null);

      send({
        type: "suggestion_request",
        id: crypto.randomUUID(),
        payload: {
          session_id: sessionIdRef.current,
          input_text: inputText,
          cursor_position: cursorPosition,
          context_window: contextWindow,
        },
      });
    },
    [send],
  );

  // Debounced version of requestSuggestion for typing scenarios
  // Prevents excessive WebSocket messages during rapid typing
  const debouncedRequestRef = useRef<ReturnType<typeof debounce> | null>(null);

  // Create/update debounced function when requestSuggestion or debounceMs changes
  const requestSuggestionDebounced = useMemo(() => {
    // Cancel previous debounced function if it exists
    debouncedRequestRef.current?.cancel();

    const debouncedFn = debounce(
      (inputText: string, cursorPosition: number, contextWindow: number = 500) => {
        requestSuggestion(inputText, cursorPosition, contextWindow);
      },
      debounceMs,
    );

    debouncedRequestRef.current = debouncedFn;
    return debouncedFn;
  }, [requestSuggestion, debounceMs]);

  // Cancel debounced request
  const cancelDebouncedRequest = useCallback(() => {
    debouncedRequestRef.current?.cancel();
  }, []);

  // Cleanup debounced function on unmount
  useEffect(() => {
    return () => {
      debouncedRequestRef.current?.cancel();
    };
  }, []);

  // Accept a suggestion
  const acceptSuggestion = useCallback(
    (suggestionId: string) => {
      send({
        type: "suggestion_accept",
        id: crypto.randomUUID(),
        payload: { suggestion_id: suggestionId },
      });
      setCurrentSuggestion(null);
    },
    [send],
  );

  // Reject a suggestion
  const rejectSuggestion = useCallback(
    (suggestionId: string, reason?: string) => {
      send({
        type: "suggestion_reject",
        id: crypto.randomUUID(),
        payload: { suggestion_id: suggestionId, reason },
      });
      setCurrentSuggestion(null);
    },
    [send],
  );

  // Update session context
  const updateContext = useCallback(
    (context: string) => {
      if (!sessionIdRef.current) {
        console.warn("Session ID required for context update");
        return;
      }

      send({
        type: "context_update",
        id: crypto.randomUUID(),
        payload: {
          session_id: sessionIdRef.current,
          context,
        },
      });
    },
    [send],
  );

  // Clear the current suggestion
  const clearSuggestion = useCallback(() => {
    setCurrentSuggestion(null);
    setIsPending(false);
  }, []);

  return {
    status,
    currentSuggestion,
    isPending,
    lastError,
    requestSuggestion,
    requestSuggestionDebounced,
    cancelDebouncedRequest,
    acceptSuggestion,
    rejectSuggestion,
    updateContext,
    clearSuggestion,
    disconnect,
    reconnect,
  };
}

export default useAISuggestionsWebSocket;
