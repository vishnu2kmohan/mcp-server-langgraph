/**
 * WebSocket Hook with Auto-Reconnect
 *
 * Provides a robust WebSocket connection with:
 * - Automatic reconnection with exponential backoff
 * - Connection status tracking
 * - Message handling
 * - Manual connect/disconnect control
 */

import { useState, useEffect, useCallback, useRef } from 'react';

// ==============================================================================
// Types
// ==============================================================================

interface WebSocketOptions {
  autoConnect?: boolean;
  autoReconnect?: boolean;
  reconnectInterval?: number;
  maxReconnectAttempts?: number;
  onMessage?: (data: any) => void;
  onError?: (error: Event) => void;
  onOpen?: () => void;
  onClose?: () => void;
}

interface WebSocketResult {
  isConnected: boolean;
  isConnecting: boolean;
  lastMessage: any;
  connectionError: Event | null;
  sendMessage: (data: any) => void;
  connect: () => void;
  disconnect: () => void;
  reconnectAttempts: number;
}

// ==============================================================================
// Constants
// ==============================================================================

const DEFAULT_RECONNECT_INTERVAL = 1000;
const DEFAULT_MAX_RECONNECT_ATTEMPTS = 10;

// ==============================================================================
// Hook Implementation
// ==============================================================================

export function useWebSocket(
  url: string,
  options: WebSocketOptions = {}
): WebSocketResult {
  const {
    autoConnect = true,
    autoReconnect = true,
    reconnectInterval = DEFAULT_RECONNECT_INTERVAL,
    maxReconnectAttempts = DEFAULT_MAX_RECONNECT_ATTEMPTS,
    onMessage,
    onError,
    onOpen,
    onClose,
  } = options;

  // State
  const [isConnected, setIsConnected] = useState(false);
  const [isConnecting, setIsConnecting] = useState(false);
  const [lastMessage, setLastMessage] = useState<any>(null);
  const [connectionError, setConnectionError] = useState<Event | null>(null);
  const [reconnectAttempts, setReconnectAttempts] = useState(0);

  // Refs for WebSocket and timers
  const wsRef = useRef<WebSocket | null>(null);
  const reconnectTimeoutRef = useRef<ReturnType<typeof setTimeout> | null>(null);
  const shouldReconnectRef = useRef(autoReconnect);
  const mountedRef = useRef(true);
  const isReconnectingRef = useRef(false); // Track if we're in a reconnect cycle

  // Clear reconnect timeout
  const clearReconnectTimeout = useCallback(() => {
    if (reconnectTimeoutRef.current) {
      clearTimeout(reconnectTimeoutRef.current);
      reconnectTimeoutRef.current = null;
    }
  }, []);

  // Create WebSocket connection
  const connect = useCallback(() => {
    // Clear any existing reconnect timeout
    clearReconnectTimeout();

    // Mark that we're intentionally reconnecting (to prevent double counting)
    isReconnectingRef.current = true;

    // Close existing connection if any
    if (wsRef.current) {
      wsRef.current.close();
    }

    isReconnectingRef.current = false;
    setIsConnecting(true);
    setConnectionError(null);

    try {
      const ws = new WebSocket(url);
      wsRef.current = ws;

      ws.onopen = () => {
        if (!mountedRef.current) return;

        setIsConnected(true);
        setIsConnecting(false);
        setReconnectAttempts(0);
        shouldReconnectRef.current = autoReconnect;
        onOpen?.();
      };

      ws.onclose = () => {
        if (!mountedRef.current) return;
        // Skip processing if we're intentionally reconnecting
        if (isReconnectingRef.current) return;

        setIsConnected(false);
        setIsConnecting(false);
        onClose?.();

        // Auto-reconnect if enabled and not manually disconnected
        if (shouldReconnectRef.current && autoReconnect) {
          setReconnectAttempts((prev) => {
            const nextAttempt = prev + 1;

            if (nextAttempt <= maxReconnectAttempts) {
              // Calculate exponential backoff
              const delay = reconnectInterval * Math.pow(2, prev);

              reconnectTimeoutRef.current = setTimeout(() => {
                if (mountedRef.current && shouldReconnectRef.current) {
                  connect();
                }
              }, delay);
            }

            return nextAttempt;
          });
        }
      };

      ws.onmessage = (event: MessageEvent) => {
        if (!mountedRef.current) return;

        try {
          const data = JSON.parse(event.data);
          setLastMessage(data);
          onMessage?.(data);
        } catch {
          // Handle non-JSON messages
          setLastMessage(event.data);
          onMessage?.(event.data);
        }
      };

      ws.onerror = (error: Event) => {
        if (!mountedRef.current) return;

        setConnectionError(error);
        onError?.(error);
      };
    } catch (error) {
      setIsConnecting(false);
      setConnectionError(error as Event);
    }
  }, [
    url,
    autoReconnect,
    reconnectInterval,
    maxReconnectAttempts,
    onMessage,
    onError,
    onOpen,
    onClose,
    clearReconnectTimeout,
  ]);

  // Disconnect WebSocket
  const disconnect = useCallback(() => {
    shouldReconnectRef.current = false;
    clearReconnectTimeout();
    setReconnectAttempts(0);

    if (wsRef.current) {
      wsRef.current.close();
      wsRef.current = null;
    }

    setIsConnected(false);
    setIsConnecting(false);
  }, [clearReconnectTimeout]);

  // Send message through WebSocket
  const sendMessage = useCallback((data: any) => {
    if (wsRef.current && wsRef.current.readyState === WebSocket.OPEN) {
      wsRef.current.send(JSON.stringify(data));
    }
  }, []);

  // Effect for initial connection and cleanup
  useEffect(() => {
    mountedRef.current = true;
    shouldReconnectRef.current = autoReconnect;

    if (autoConnect) {
      connect();
    }

    return () => {
      mountedRef.current = false;
      clearReconnectTimeout();

      if (wsRef.current) {
        wsRef.current.close();
      }
    };
  }, [url]); // eslint-disable-line react-hooks/exhaustive-deps

  return {
    isConnected,
    isConnecting,
    lastMessage,
    connectionError,
    sendMessage,
    connect,
    disconnect,
    reconnectAttempts,
  };
}

export default useWebSocket;
