/**
 * useConnectionHealth Hook
 *
 * React hook for real-time connection health monitoring via WebSocket.
 * Connects to /api/v1/ws/connections/health (consolidated URL per ADR-0068).
 *
 * @deprecated Consider using useConnectionHealthWebSocket instead which uses
 * the standardized useRealtimeSync infrastructure.
 */

import { useState, useCallback, useRef, useEffect, useMemo } from "react";
import { useAppDispatch } from "../store/hooks";
import { logout } from "../store/slices/authSlice";
import { buildWebSocketUrl, WS_ENDPOINTS } from "../utils/websocket";
import {
  WS_CLOSE_TOKEN_EXPIRED,
  ensureValidTokenForWebSocket,
} from "../utils/websocketAuth";

/**
 * Connection health status from WebSocket
 */
export interface ConnectionHealthStatus {
  id: string;
  name: string;
  url: string;
  status:
    | "connected"
    | "disconnected"
    | "connecting"
    | "error"
    | "auth_required";
  auth_type: "none" | "api_key" | "oauth2";
  server_name?: string;
  server_version?: string;
  tool_count?: number;
  resource_count?: number;
  prompt_count?: number;
  last_error?: string;
}

/**
 * Aggregated health summary
 */
export interface HealthSummary {
  total: number;
  connected: number;
  disconnected: number;
  connecting: number;
  error: number;
  auth_required: number;
}

/**
 * Hook options
 */
export interface UseConnectionHealthOptions {
  autoConnect?: boolean;
  reconnectInterval?: number;
}

/**
 * Hook state
 */
interface ConnectionHealthState {
  isConnected: boolean;
  connections: ConnectionHealthStatus[];
  error: string | null;
  lastPong: Date | null;
}

/**
 * Hook return type
 */
export interface UseConnectionHealthReturn extends ConnectionHealthState {
  summary: HealthSummary;
  connect: () => void;
  disconnect: () => void;
  refresh: () => void;
  checkHealth: (connectionId: string) => void;
  subscribe: (connectionId: string) => void;
  unsubscribe: (connectionId: string) => void;
}

/**
 * Hook for connection health monitoring via WebSocket
 */
export function useConnectionHealth(
  options: UseConnectionHealthOptions = {},
): UseConnectionHealthReturn {
  const { autoConnect = false, reconnectInterval = 5000 } = options;

  // Redux dispatch for token expiration handling
  const dispatch = useAppDispatch();

  const [state, setState] = useState<ConnectionHealthState>({
    isConnected: false,
    connections: [],
    error: null,
    lastPong: null,
  });

  const wsRef = useRef<WebSocket | null>(null);
  const reconnectTimeoutRef = useRef<NodeJS.Timeout | null>(null);

  /**
   * Compute health summary from connections
   */
  const summary = useMemo<HealthSummary>(() => {
    const counts: HealthSummary = {
      total: state.connections.length,
      connected: 0,
      disconnected: 0,
      connecting: 0,
      error: 0,
      auth_required: 0,
    };

    for (const conn of state.connections) {
      if (conn.status in counts) {
        counts[conn.status as keyof Omit<HealthSummary, "total">]++;
      }
    }

    return counts;
  }, [state.connections]);

  /**
   * Handle incoming WebSocket message
   */
  const handleMessage = useCallback((event: MessageEvent) => {
    try {
      const data = JSON.parse(event.data);

      switch (data.type) {
        case "connection_status":
          setState((prev) => ({
            ...prev,
            connections: data.connections || [],
          }));
          break;

        case "connection_update":
          if (data.connection) {
            setState((prev) => ({
              ...prev,
              connections: prev.connections.map((conn) =>
                conn.id === data.connection.id
                  ? { ...conn, ...data.connection }
                  : conn,
              ),
            }));
          }
          break;

        case "pong":
          setState((prev) => ({
            ...prev,
            lastPong: new Date(data.timestamp || Date.now()),
          }));
          break;

        case "error":
          setState((prev) => ({
            ...prev,
            error: data.message,
          }));
          break;
      }
    } catch {
      // Ignore parse errors
    }
  }, []);

  /**
   * Connect to WebSocket
   */
  const connect = useCallback(() => {
    if (wsRef.current?.readyState === WebSocket.OPEN) {
      return;
    }

    // Clear any pending reconnect
    if (reconnectTimeoutRef.current) {
      clearTimeout(reconnectTimeoutRef.current);
      reconnectTimeoutRef.current = null;
    }

    // Use standardized WebSocket URL (ADR-0068 consolidated WebSocket URLs)
    // Include auth token since backend requires authentication
    const url = buildWebSocketUrl(WS_ENDPOINTS.CONNECTIONS_HEALTH, {}, true);

    const ws = new WebSocket(url);
    wsRef.current = ws;

    ws.onopen = () => {
      setState((prev) => ({ ...prev, isConnected: true, error: null }));
    };

    ws.onmessage = handleMessage;

    ws.onerror = () => {
      setState((prev) => ({
        ...prev,
        error: "WebSocket connection error",
      }));
    };

    ws.onclose = async (event) => {
      setState((prev) => ({ ...prev, isConnected: false }));
      wsRef.current = null;

      // Handle token expiration close code (4010)
      if (event.code === WS_CLOSE_TOKEN_EXPIRED) {
        const refreshed = await ensureValidTokenForWebSocket();
        if (refreshed) {
          // Token refreshed successfully - reconnect
          reconnectTimeoutRef.current = setTimeout(connect, 100);
        } else {
          // Refresh failed - logout
          dispatch(logout());
        }
        return;
      }

      // Schedule reconnect
      if (reconnectInterval > 0) {
        reconnectTimeoutRef.current = setTimeout(connect, reconnectInterval);
      }
    };
  }, [handleMessage, reconnectInterval, dispatch]);

  /**
   * Disconnect from WebSocket
   */
  const disconnect = useCallback(() => {
    if (reconnectTimeoutRef.current) {
      clearTimeout(reconnectTimeoutRef.current);
      reconnectTimeoutRef.current = null;
    }

    if (wsRef.current) {
      wsRef.current.close();
      wsRef.current = null;
    }
  }, []);

  /**
   * Send a message to the WebSocket
   */
  const sendMessage = useCallback((message: object) => {
    if (wsRef.current?.readyState === WebSocket.OPEN) {
      wsRef.current.send(JSON.stringify(message));
    }
  }, []);

  /**
   * Request refresh of all connection statuses
   */
  const refresh = useCallback(() => {
    sendMessage({ type: "refresh" });
  }, [sendMessage]);

  /**
   * Request health check for a specific connection
   */
  const checkHealth = useCallback(
    (connectionId: string) => {
      sendMessage({ type: "check_health", connection_id: connectionId });
    },
    [sendMessage],
  );

  /**
   * Subscribe to updates for a specific connection
   */
  const subscribe = useCallback(
    (connectionId: string) => {
      sendMessage({ type: "subscribe", connection_id: connectionId });
    },
    [sendMessage],
  );

  /**
   * Unsubscribe from updates for a specific connection
   */
  const unsubscribe = useCallback(
    (connectionId: string) => {
      sendMessage({ type: "unsubscribe", connection_id: connectionId });
    },
    [sendMessage],
  );

  /**
   * Auto-connect on mount if enabled
   */
  useEffect(() => {
    if (autoConnect) {
      connect();
    }

    return () => {
      disconnect();
    };
  }, [autoConnect, connect, disconnect]);

  return {
    ...state,
    summary,
    connect,
    disconnect,
    refresh,
    checkHealth,
    subscribe,
    unsubscribe,
  };
}
