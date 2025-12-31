/**
 * useRealtimeSync Hook
 *
 * Custom hook for real-time data synchronization using WebSocket.
 * Features:
 * - WebSocket connection management
 * - Automatic reconnection with exponential backoff
 * - Message handling
 * - Connection status tracking
 * - Token expiration handling (4010 close code)
 * - Protocol version mismatch handling (4009 close code)
 * - Reconnection metrics for observability
 */

import { useState, useCallback, useRef, useEffect } from "react";
import {
  WS_CLOSE_TOKEN_EXPIRED,
  WS_CLOSE_PROTOCOL_VERSION,
  ensureValidTokenForWebSocket,
} from "../utils/websocketAuth";
import { PROTOCOL_VERSION } from "../config/version";
import {
  type ReconnectionMetrics,
  type ReconnectionAttempt,
  createInitialReconnectionMetrics,
  classifyCloseCode,
  calculateSuccessRate,
  calculateAvgDuration,
} from "../types/websocket-metrics";

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
   * Callback when protocol version mismatch is detected (close code 4009).
   * This is NOT recoverable - reconnection will NOT be attempted.
   * Use this to show user-friendly message suggesting page refresh or app update.
   */
  onProtocolVersionMismatch?: () => void;
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
  /** Reconnection metrics for observability */
  metrics: ReconnectionMetrics;
  /** Reset all reconnection metrics to initial state */
  resetMetrics: () => void;
}

// Re-export metrics types for consumers
export type { ReconnectionMetrics, ReconnectionAttempt };

/**
 * Append protocol version as query parameter to WebSocket URL.
 *
 * @param url - The base WebSocket URL
 * @returns URL with protocol version query parameter (e.g., "ws://host/path?v=1.0.0")
 */
function appendProtocolVersion(url: string): string {
  const separator = url.includes("?") ? "&" : "?";
  return `${url}${separator}v=${PROTOCOL_VERSION}`;
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
    onProtocolVersionMismatch,
  } = options;

  const [status, setStatus] = useState<ConnectionStatus>(
    url ? "connecting" : "disconnected",
  );
  const [reconnectAttempts, setReconnectAttempts] = useState(0);
  const [lastMessageTime, setLastMessageTime] = useState<number | null>(null);

  // Reconnection metrics state for observability
  const [metrics, setMetrics] = useState<ReconnectionMetrics>(
    createInitialReconnectionMetrics,
  );

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
  // Store URL in ref to make hook resilient to URL reference changes
  // This prevents unnecessary reconnections when URL prop changes by reference but not content
  const urlRef = useRef(url);

  // Track reconnection timing
  const reconnectionStartTimeRef = useRef<number | null>(null);
  const lastCloseCodeRef = useRef<number | null>(null);
  const maxRecentAttempts = 10;

  // Keep ref in sync with state
  reconnectAttemptsRef.current = reconnectAttempts;

  // Keep urlRef in sync with latest URL prop (used by actuallyCreateConnection and createConnection)
  urlRef.current = url;

  // Store callbacks in refs to avoid dependency issues
  const callbacksRef = useRef({
    onMessage,
    onError,
    onConnect,
    onDisconnect,
    onTokenExpired,
    onProtocolVersionMismatch,
  });
  callbacksRef.current = {
    onMessage,
    onError,
    onConnect,
    onDisconnect,
    onTokenExpired,
    onProtocolVersionMismatch,
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
   * Record a reconnection attempt in metrics.
   */
  const recordReconnectionAttempt = useCallback(
    (closeCode: number | null, isStarting: boolean) => {
      const now = Date.now();

      if (isStarting) {
        // Starting a reconnection attempt
        reconnectionStartTimeRef.current = now;
        lastCloseCodeRef.current = closeCode;

        setMetrics((prev) => {
          const failureReason = closeCode
            ? classifyCloseCode(closeCode)
            : "unknown";

          // Create new attempt record
          const newAttempt: ReconnectionAttempt = {
            timestamp: now,
            attemptNumber: prev.totalAttempts + 1,
            succeeded: false, // Will be updated on success
            durationMs: null,
            failureReason,
            triggerCloseCode: closeCode,
          };

          // Keep only recent attempts
          const recentAttempts = [
            newAttempt,
            ...prev.recentAttempts.slice(0, maxRecentAttempts - 1),
          ];

          // Update failure counts
          const failuresByReason = { ...prev.failuresByReason };
          if (failureReason !== "manual_disconnect") {
            failuresByReason[failureReason] =
              (failuresByReason[failureReason] || 0) + 1;
          }

          return {
            ...prev,
            totalAttempts: prev.totalAttempts + 1,
            consecutiveFailures: prev.consecutiveFailures + 1,
            lastDisconnectionTime: now,
            failuresByReason,
            recentAttempts,
            successRate: calculateSuccessRate(
              prev.totalReconnections,
              prev.totalAttempts + 1,
            ),
          };
        });
      }
    },
    [],
  );

  /**
   * Record a successful reconnection in metrics.
   */
  const recordReconnectionSuccess = useCallback(() => {
    const now = Date.now();
    const startTime = reconnectionStartTimeRef.current;
    const durationMs = startTime ? now - startTime : 0;

    setMetrics((prev) => {
      // Update the most recent attempt to show success
      const recentAttempts = [...prev.recentAttempts];
      if (recentAttempts.length > 0) {
        recentAttempts[0] = {
          ...recentAttempts[0],
          succeeded: true,
          durationMs,
          failureReason: null,
        };
      }

      const newTotalReconnections = prev.totalReconnections + 1;
      const newTotalTime = prev.totalReconnectionTimeMs + durationMs;

      return {
        ...prev,
        totalReconnections: newTotalReconnections,
        consecutiveFailures: 0,
        lastReconnectionTime: now,
        totalReconnectionTimeMs: newTotalTime,
        avgReconnectionDurationMs: calculateAvgDuration(
          newTotalTime,
          newTotalReconnections,
        ),
        recentAttempts,
        successRate: calculateSuccessRate(
          newTotalReconnections,
          prev.totalAttempts,
        ),
      };
    });

    reconnectionStartTimeRef.current = null;
  }, []);

  /**
   * Record max attempts exceeded failure.
   */
  const recordMaxAttemptsExceeded = useCallback(() => {
    setMetrics((prev) => {
      const failuresByReason = { ...prev.failuresByReason };
      failuresByReason.max_attempts_exceeded =
        (failuresByReason.max_attempts_exceeded || 0) + 1;
      return { ...prev, failuresByReason };
    });
  }, []);

  /**
   * Record token refresh failure.
   */
  const recordTokenRefreshFailed = useCallback(() => {
    setMetrics((prev) => {
      const failuresByReason = { ...prev.failuresByReason };
      failuresByReason.token_refresh_failed =
        (failuresByReason.token_refresh_failed || 0) + 1;
      return { ...prev, failuresByReason };
    });
  }, []);

  /**
   * Record protocol version mismatch failure.
   */
  const recordProtocolVersionMismatch = useCallback(() => {
    setMetrics((prev) => {
      const failuresByReason = { ...prev.failuresByReason };
      failuresByReason.protocol_version_mismatch =
        (failuresByReason.protocol_version_mismatch || 0) + 1;
      return { ...prev, failuresByReason };
    });
  }, []);

  /**
   * Reset all metrics to initial state.
   */
  const resetMetrics = useCallback(() => {
    setMetrics(createInitialReconnectionMetrics());
    reconnectionStartTimeRef.current = null;
    lastCloseCodeRef.current = null;
  }, []);

  /**
   * Internal function that actually creates the WebSocket connection.
   * Called after proactive token validation in createConnection.
   */
  const actuallyCreateConnection = useCallback(() => {
    // Read URL from ref - this makes the function stable regardless of URL prop reference
    const currentUrl = urlRef.current;

    // Clean up existing connection without triggering onclose
    if (wsRef.current) {
      wsRef.current.onclose = null;
      wsRef.current.close();
    }

    manualCloseRef.current = false;
    setStatus("connecting");

    // Append protocol version to URL for server compatibility checking
    const wsUrl = appendProtocolVersion(currentUrl);
    const ws = new WebSocket(wsUrl);
    wsRef.current = ws;

    ws.onopen = () => {
      setStatus("connected");
      // If this was a reconnection (not initial connection), record success
      if (reconnectionStartTimeRef.current !== null) {
        recordReconnectionSuccess();
      }
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
            // Record this as a reconnection attempt starting
            recordReconnectionAttempt(event.code, true);
            // Use actuallyCreateConnection directly since we just validated
            setReconnectAttempts(0);
            reconnectAttemptsRef.current = 0;
            actuallyCreateConnection();
          } else {
            // Refresh failed - notify and disconnect
            recordTokenRefreshFailed();
            setStatus("disconnected");
            callbacksRef.current.onTokenExpired?.();
            callbacksRef.current.onDisconnect?.();
          }
        })();
        return;
      }

      // Protocol version mismatch (4009) - NOT recoverable, do NOT reconnect
      // Client needs to refresh page or update application to get compatible version
      if (event.code === WS_CLOSE_PROTOCOL_VERSION) {
        recordProtocolVersionMismatch();
        setStatus("error"); // Use 'error' to indicate user action required
        callbacksRef.current.onProtocolVersionMismatch?.();
        callbacksRef.current.onDisconnect?.();
        return;
      }

      // Abnormal close - attempt reconnection using ref for current value
      const currentAttempts = reconnectAttemptsRef.current;
      if (currentAttempts < maxReconnectAttempts) {
        setStatus("reconnecting");
        const nextAttempts = currentAttempts + 1;
        setReconnectAttempts(nextAttempts);
        reconnectAttemptsRef.current = nextAttempts;

        // Record reconnection attempt in metrics
        recordReconnectionAttempt(event.code, true);

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
        // Max attempts exceeded
        recordMaxAttemptsExceeded();
        setStatus("disconnected");
        callbacksRef.current.onDisconnect?.();
      }
    };
  }, [
    // Note: url is intentionally NOT a dependency - we read from urlRef.current
    // to make this hook resilient to unstable URL references from callers
    reconnectInterval,
    maxReconnectAttempts,
    exponentialBackoff,
    maxDelayMs,
    backoffMultiplier,
    flushMessageQueue,
    recordReconnectionAttempt,
    recordReconnectionSuccess,
    recordTokenRefreshFailed,
    recordProtocolVersionMismatch,
    recordMaxAttemptsExceeded,
  ]);

  /**
   * Create and configure WebSocket connection with proactive token refresh.
   *
   * Before connecting, checks if the token is expiring soon and refreshes
   * if needed. This prevents the round-trip of:
   * connect → 4010 close → refresh → reconnect
   */
  const createConnection = useCallback(() => {
    // Read URL from ref - this makes the hook resilient to unstable URL references
    const currentUrl = urlRef.current;

    // Don't attempt connection with empty URL
    if (!currentUrl) {
      // Note: Initial state is already 'disconnected' when url is empty
      return;
    }

    // Validate WebSocket URL protocol to prevent DOMException
    // WebSocket URLs must start with ws:// or wss://
    if (!currentUrl.startsWith("ws://") && !currentUrl.startsWith("wss://")) {
      const error = new Error(
        `Invalid WebSocket URL: "${currentUrl}". URL must start with ws:// or wss://`,
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
    // Note: url is intentionally NOT a dependency - we read from urlRef.current
    // to make this hook resilient to unstable URL references from callers
  }, [actuallyCreateConnection]);

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

  // Track committed URL to detect actual content changes
  const committedUrlRef = useRef<string | null>(null);

  // Initialize connection on mount and handle URL content changes
  useEffect(() => {
    // Check if URL content actually changed (not just reference)
    const urlContentChanged = url !== committedUrlRef.current;

    if (urlContentChanged) {
      // Update committed URL
      committedUrlRef.current = url;

      // Close existing connection if URL changed (not on initial mount)
      if (wsRef.current && committedUrlRef.current !== null) {
        manualCloseRef.current = true;
        wsRef.current.onclose = null;
        wsRef.current.close();
        wsRef.current = null;
      }

      // Reset manual close flag for new connection
      manualCloseRef.current = false;

      // Create new connection with updated URL
      createConnection();
    }

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
    // url is a dependency to detect content changes, but createConnection
    // reads from urlRef.current so it doesn't need to be recreated
  }, [url, createConnection]);

  return {
    status,
    reconnectAttempts,
    lastMessageTime,
    send,
    disconnect,
    reconnect,
    metrics,
    resetMetrics,
  };
}
