/**
 * useRealtimeSync Hook
 *
 * Custom hook for real-time data synchronization using WebSocket.
 * Features:
 * - WebSocket connection management
 * - Automatic reconnection
 * - Message handling
 * - Connection status tracking
 */

import { useState, useCallback, useRef, useEffect } from "react";

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
  /** Interval between reconnection attempts (ms) */
  reconnectInterval?: number;
  /** Maximum number of reconnection attempts */
  maxReconnectAttempts?: number;
  /** Callback when a message is received */
  onMessage?: (data: unknown) => void;
  /** Callback when an error occurs */
  onError?: (error: Error) => void;
  /** Callback when connection is established */
  onConnect?: () => void;
  /** Callback when connection is closed */
  onDisconnect?: () => void;
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
export function useRealtimeSync(
  options: UseRealtimeSyncOptions,
): UseRealtimeSyncReturn {
  const {
    url,
    reconnectInterval = 1000,
    maxReconnectAttempts = 5,
    onMessage,
    onError,
    onConnect,
    onDisconnect,
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

  // Keep ref in sync with state
  reconnectAttemptsRef.current = reconnectAttempts;

  // Store callbacks in refs to avoid dependency issues
  const callbacksRef = useRef({
    onMessage,
    onError,
    onConnect,
    onDisconnect,
  });
  callbacksRef.current = { onMessage, onError, onConnect, onDisconnect };

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
   * Create and configure WebSocket connection
   */
  const createConnection = useCallback(() => {
    // Don't attempt connection with empty URL
    if (!url) {
      // Note: Initial state is already 'disconnected' when url is empty
      return;
    }

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

      // Abnormal close - attempt reconnection using ref for current value
      const currentAttempts = reconnectAttemptsRef.current;
      if (currentAttempts < maxReconnectAttempts) {
        setStatus("reconnecting");
        const nextAttempts = currentAttempts + 1;
        setReconnectAttempts(nextAttempts);
        reconnectAttemptsRef.current = nextAttempts;

        reconnectTimeoutRef.current = setTimeout(() => {
          createConnection();
        }, reconnectInterval);
      } else {
        setStatus("disconnected");
        callbacksRef.current.onDisconnect?.();
      }
    };
  }, [url, reconnectInterval, maxReconnectAttempts, flushMessageQueue]);

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
