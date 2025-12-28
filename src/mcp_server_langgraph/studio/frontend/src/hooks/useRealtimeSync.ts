/**
 * useRealtimeSync Hook
 *
 * Custom hook for real-time data synchronization using WebSocket.
 * Features:
 * - WebSocket connection management
 * - Automatic reconnection
 * - Message handling
 * - Connection status tracking
 * - Token expiration handling (4010 close code)
 */

import { useState, useCallback, useRef, useEffect } from "react";
import {
  WS_CLOSE_TOKEN_EXPIRED,
  ensureValidTokenForWebSocket,
} from "../utils/websocketAuth";

/**
 * Connection status type
 */
export type ConnectionStatus =
  | "connecting"
  | "connected"
  | "disconnected"
  | "reconnecting"
  | "error";

/**
 * Options for useRealtimeSync hook
 */
export interface UseRealtimeSyncOptions {
  /** WebSocket URL to connect to */
  url: string;
  /** Base interval between reconnection attempts (ms) */
  reconnectInterval?: number;
  /** Maximum number of reconnection attempts */
  maxReconnectAttempts?: number;
  /** Enable exponential backoff for reconnection delays (default: false) */
  exponentialBackoff?: boolean;
  /** Maximum delay for exponential backoff (ms, default: 30000) */
  maxDelayMs?: number;
  /** Backoff multiplier (default: 2) */
  backoffMultiplier?: number;
  /** Callback when a message is received */
  onMessage?: (data: unknown) => void;
  /** Callback when an error occurs */
  onError?: (error: Error) => void;
  /** Callback when connection is established */
  onConnect?: () => void;
  /** Callback when connection is closed */
  onDisconnect?: () => void;
  /**
   * Callback when token expires (close code 4010) and refresh fails.
   * Use this to redirect to login.
   */
  onTokenExpired?: () => void;
  /**
   * Enable proactive token refresh before connecting.
   * When true, validates and refreshes token before WebSocket connection.
   * Default: true (recommended for production)
   */
  proactiveTokenRefresh?: boolean;
}

/**
 * Return type for useRealtimeSync hook
 */
export interface UseRealtimeSyncReturn {
  /** Current connection status */
  status: ConnectionStatus;
  /** Number of reconnection attempts */
  reconnectAttempts: number;
  /** Timestamp of last received message */
  lastMessageTime: number | null;
  /** Send a message through the WebSocket */
  send: (data: unknown) => void;
  /** Manually disconnect */
  disconnect: () => void;
  /** Manually reconnect */
  reconnect: () => void;
}

/**
 * Real-time sync hook using WebSocket
 */
/**
 * Calculate reconnection delay with optional exponential backoff.
 *
 * @param attempt - Current attempt number (0-based)
 * @param baseDelay - Base delay in milliseconds
 * @param options - Backoff options
 * @returns Delay in milliseconds
 */
function calculateReconnectDelay(
  attempt: number,
  baseDelay: number,
  options: {
    exponentialBackoff?: boolean;
    maxDelayMs?: number;
    backoffMultiplier?: number;
  },
): number {
  if (!options.exponentialBackoff) {
    return baseDelay;
  }

  const multiplier = options.backoffMultiplier ?? 2;
  const maxDelay = options.maxDelayMs ?? 30000;

  // Exponential: baseDelay * multiplier^attempt
  const exponentialDelay = baseDelay * Math.pow(multiplier, attempt);

  // Cap at maximum
  return Math.min(exponentialDelay, maxDelay);
}

export function useRealtimeSync(
  options: UseRealtimeSyncOptions,
): UseRealtimeSyncReturn {
  const {
    url,
    reconnectInterval = 1000,
    maxReconnectAttempts = 5,
    exponentialBackoff = false,
    maxDelayMs = 30000,
    backoffMultiplier = 2,
    onMessage,
    onError,
    onConnect,
    onDisconnect,
    onTokenExpired,
  } = options;

  const [status, setStatus] = useState<ConnectionStatus>(
    url ? "connecting" : "disconnected",
  );
  const [reconnectAttempts, setReconnectAttempts] = useState(0);
  const [lastMessageTime, setLastMessageTime] = useState<number | null>(null);

  // Refs for WebSocket and state that needs to be accessed in callbacks
  const wsRef = useRef<WebSocket | null>(null);
  const messageQueueRef = useRef<unknown[]>([]);
  const reconnectTimeoutRef = useRef<ReturnType<typeof setTimeout> | null>(
    null,
  );
  const manualCloseRef = useRef(false);
  const reconnectAttemptsRef = useRef(0);
  // Ref to store createConnection for use in actuallyCreateConnection without circular deps
  const createConnectionRef = useRef<() => void>(() => {});

  // Keep ref in sync with state
  reconnectAttemptsRef.current = reconnectAttempts;

  // Store callbacks in refs to avoid dependency issues
  const callbacksRef = useRef({
    onMessage,
    onError,
    onConnect,
    onDisconnect,
    onTokenExpired,
  });
  callbacksRef.current = {
    onMessage,
    onError,
    onConnect,
    onDisconnect,
    onTokenExpired,
  };

  /**
   * Flush queued messages after connection
   */
  const flushMessageQueue = useCallback(() => {
    const ws = wsRef.current;
    if (!ws || ws.readyState !== WebSocket.OPEN) return;

    while (messageQueueRef.current.length > 0) {
      const message = messageQueueRef.current.shift();
      ws.send(JSON.stringify(message));
    }
  }, []);

  /**
   * Internal function that actually creates the WebSocket connection.
   * Called after proactive token validation in createConnection.
   */
  const actuallyCreateConnection = useCallback(() => {
    // Clean up existing connection without triggering onclose
    if (wsRef.current) {
      wsRef.current.onclose = null;
      wsRef.current.close();
    }

    manualCloseRef.current = false;
    setStatus("connecting");

    const ws = new WebSocket(url);
    wsRef.current = ws;

    ws.onopen = () => {
      setStatus("connected");
      setReconnectAttempts(0);
      reconnectAttemptsRef.current = 0;
      flushMessageQueue();
      callbacksRef.current.onConnect?.();
    };

    ws.onmessage = (event) => {
      try {
        const data = JSON.parse(event.data);
        setLastMessageTime(Date.now());
        callbacksRef.current.onMessage?.(data);
      } catch {
        // Handle non-JSON messages if needed
        setLastMessageTime(Date.now());
        callbacksRef.current.onMessage?.(event.data);
      }
    };

    ws.onerror = (event) => {
      setStatus("error");
      callbacksRef.current.onError?.(event as unknown as Error);
    };

    ws.onclose = (event) => {
      // Normal close (code 1000) or manual close - don't reconnect
      if (event.code === 1000 || manualCloseRef.current) {
        setStatus("disconnected");
        callbacksRef.current.onDisconnect?.();
        return;
      }

      // Token expiration (4010) - special handling with refresh attempt
      // Note: proactive token refresh in createConnection usually prevents this,
      // but handles edge cases where token expires during long-lived connection
      if (event.code === WS_CLOSE_TOKEN_EXPIRED) {
        // Async handler for token refresh
        (async () => {
          const refreshed = await ensureValidTokenForWebSocket();
          if (refreshed) {
            // Token refreshed successfully - reconnect immediately
            // Use actuallyCreateConnection directly since we just validated
            setReconnectAttempts(0);
            reconnectAttemptsRef.current = 0;
            actuallyCreateConnection();
          } else {
            // Refresh failed - notify and disconnect
            setStatus("disconnected");
            callbacksRef.current.onTokenExpired?.();
            callbacksRef.current.onDisconnect?.();
          }
        })();
        return;
      }

      // Abnormal close - attempt reconnection using ref for current value
      const currentAttempts = reconnectAttemptsRef.current;
      if (currentAttempts < maxReconnectAttempts) {
        setStatus("reconnecting");
        const nextAttempts = currentAttempts + 1;
        setReconnectAttempts(nextAttempts);
        reconnectAttemptsRef.current = nextAttempts;

        // Calculate delay with optional exponential backoff
        const delay = calculateReconnectDelay(
          currentAttempts,
          reconnectInterval,
          {
            exponentialBackoff,
            maxDelayMs,
            backoffMultiplier,
          },
        );

        reconnectTimeoutRef.current = setTimeout(() => {
          // Re-validate token before reconnecting (may have expired during delay)
          // Use ref to avoid circular dependency with createConnection
          createConnectionRef.current();
        }, delay);
      } else {
        setStatus("disconnected");
        callbacksRef.current.onDisconnect?.();
      }
    };
  }, [
    url,
    reconnectInterval,
    maxReconnectAttempts,
    exponentialBackoff,
    maxDelayMs,
    backoffMultiplier,
    flushMessageQueue,
  ]);

  /**
   * Create and configure WebSocket connection with proactive token refresh.
   *
   * Before connecting, checks if the token is expiring soon and refreshes
   * if needed. This prevents the round-trip of:
   * connect → 4010 close → refresh → reconnect
   */
  const createConnection = useCallback(() => {
    // Don't attempt connection with empty URL
    if (!url) {
      // Note: Initial state is already 'disconnected' when url is empty
      return;
    }

    // Validate WebSocket URL protocol to prevent DOMException
    // WebSocket URLs must start with ws:// or wss://
    if (!url.startsWith("ws://") && !url.startsWith("wss://")) {
      const error = new Error(
        `Invalid WebSocket URL: "${url}". URL must start with ws:// or wss://`,
      );
      setStatus("error");
      callbacksRef.current.onError?.(error);
      return;
    }

    // Proactive token refresh: Check if token is valid before connecting
    // This prevents the connect → 4010 → refresh → reconnect round-trip
    ensureValidTokenForWebSocket().then((tokenValid) => {
      if (!tokenValid) {
        // Token invalid and refresh failed - notify and disconnect
        setStatus("disconnected");
        callbacksRef.current.onTokenExpired?.();
        callbacksRef.current.onDisconnect?.();
        return;
      }

      // Token is valid - proceed with connection
      actuallyCreateConnection();
    });
  }, [url, actuallyCreateConnection]);

  // Keep ref in sync for use in actuallyCreateConnection's reconnect timeout
  createConnectionRef.current = createConnection;

  /**
   * Send a message through the WebSocket
   */
  const send = useCallback((data: unknown) => {
    const ws = wsRef.current;

    if (ws && ws.readyState === WebSocket.OPEN) {
      ws.send(JSON.stringify(data));
    } else {
      // Queue message for when connection is established
      messageQueueRef.current.push(data);
    }
  }, []);

  /**
   * Manually disconnect from the WebSocket
   */
  const disconnect = useCallback(() => {
    manualCloseRef.current = true;

    // Clear any pending reconnection
    if (reconnectTimeoutRef.current) {
      clearTimeout(reconnectTimeoutRef.current);
      reconnectTimeoutRef.current = null;
    }

    if (wsRef.current) {
      wsRef.current.close();
    }
  }, []);

  /**
   * Manually reconnect to the WebSocket
   */
  const reconnect = useCallback(() => {
    setReconnectAttempts(0);
    reconnectAttemptsRef.current = 0;
    createConnection();
  }, [createConnection]);

  // Initialize connection on mount
  useEffect(() => {
    createConnection();

    return () => {
      manualCloseRef.current = true;

      if (reconnectTimeoutRef.current) {
        clearTimeout(reconnectTimeoutRef.current);
      }

      if (wsRef.current) {
        wsRef.current.onclose = null;
        wsRef.current.close();
      }
    };
  }, [createConnection]);

  return {
    status,
    reconnectAttempts,
    lastMessageTime,
    send,
    disconnect,
    reconnect,
  };
}
