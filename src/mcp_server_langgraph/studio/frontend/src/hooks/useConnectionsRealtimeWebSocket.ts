/**
 * useConnectionsRealtimeWebSocket Hook
 *
 * WebSocket hook for real-time connection status updates.
 * Replaces polling-based ConnectionsPage updates with efficient push-based updates.
 *
 * Based on backend endpoint: /api/v1/ws/connections/realtime
 */

import { useState, useCallback, useRef } from "react";
import { useRealtimeSync } from "./useRealtimeSync";

// =============================================================================
// Types
// =============================================================================

/**
 * Connection information
 */
export interface Connection {
  id: string;
  name: string;
  status: "connected" | "disconnected" | "connecting" | "error";
  type?: string;
  url?: string;
  last_seen?: string;
  error?: string;
}

/**
 * Health check result
 */
export interface HealthCheckResult {
  connection_id: string;
  healthy: boolean;
  latency_ms?: number;
  error?: string;
  checked_at?: string;
}

/**
 * WebSocket message types from server
 */
interface ConnectionListMessage {
  type: "connection_list";
  connections: Connection[];
}

interface ConnectionStatusMessage {
  type: "connection_status";
  payload: {
    connection: Connection;
  };
}

interface ConnectionUpdatedMessage {
  type: "connection_updated";
  payload: {
    connection: Connection;
  };
}

interface SubscribedAllMessage {
  type: "subscribed_all";
  payload: {
    subscribed: boolean;
  };
}

interface UnsubscribedMessage {
  type: "unsubscribed";
  payload: {
    connection_id?: string;
  };
}

interface HealthCheckResultMessage {
  type: "health_check_result";
  payload: HealthCheckResult;
}

interface ErrorMessage {
  type: "error";
  payload: {
    code: string;
    message: string;
  };
}

type ServerMessage =
  | ConnectionListMessage
  | ConnectionStatusMessage
  | ConnectionUpdatedMessage
  | SubscribedAllMessage
  | UnsubscribedMessage
  | HealthCheckResultMessage
  | ErrorMessage;

/**
 * Options for useConnectionsRealtimeWebSocket hook
 */
export interface UseConnectionsRealtimeWebSocketOptions {
  /** Custom WebSocket URL (defaults to /api/v1/ws/connections/realtime) */
  url?: string;
  /** Callback when connection is updated */
  onConnectionUpdate?: (connection: Connection) => void;
  /** Callback when connection list is received */
  onConnectionList?: (connections: Connection[]) => void;
  /** Callback when health check result is received */
  onHealthCheckResult?: (result: HealthCheckResult) => void;
  /** Callback when an error occurs */
  onError?: (error: string) => void;
}

/**
 * Return type for useConnectionsRealtimeWebSocket hook
 */
export interface UseConnectionsRealtimeWebSocketReturn {
  /** Current WebSocket connection status */
  status:
    | "connecting"
    | "connected"
    | "disconnected"
    | "reconnecting"
    | "error";
  /** All connections */
  connections: Connection[];
  /** Set of subscribed connection IDs */
  subscribedConnections: Set<string>;
  /** Whether subscribed to all connection updates */
  subscribedAll: boolean;
  /** Current error message, if any */
  error: string | null;
  /** Subscribe to specific connection updates */
  subscribeConnection: (connectionId: string) => void;
  /** Unsubscribe from specific connection updates */
  unsubscribeConnection: (connectionId: string) => void;
  /** Subscribe to all connection updates */
  subscribeAll: () => void;
  /** Request health check for a connection */
  requestHealthCheck: (connectionId: string) => void;
  /** Get connection by ID */
  getConnection: (connectionId: string) => Connection | undefined;
  /** Refresh connection list */
  refresh: () => void;
  /** Manually disconnect from WebSocket */
  disconnect: () => void;
  /** Manually reconnect to WebSocket */
  reconnect: () => void;
}

// =============================================================================
// Default URL
// =============================================================================

function getDefaultWebSocketUrl(): string {
  const protocol = window.location.protocol === "https:" ? "wss:" : "ws:";
  const host = window.location.host;
  return `${protocol}//${host}/api/v1/ws/connections/realtime`;
}

// =============================================================================
// Hook Implementation
// =============================================================================

export function useConnectionsRealtimeWebSocket(
  options: UseConnectionsRealtimeWebSocketOptions = {},
): UseConnectionsRealtimeWebSocketReturn {
  const {
    url = getDefaultWebSocketUrl(),
    onConnectionUpdate,
    onConnectionList,
    onHealthCheckResult,
    onError,
  } = options;

  // State
  const [connections, setConnections] = useState<Connection[]>([]);
  const [subscribedConnections, setSubscribedConnections] = useState<
    Set<string>
  >(new Set());
  const [subscribedAll, setSubscribedAll] = useState<boolean>(false);
  const [error, setError] = useState<string | null>(null);

  // Refs for callbacks to avoid stale closures
  const callbacksRef = useRef({
    onConnectionUpdate,
    onConnectionList,
    onHealthCheckResult,
    onError,
  });
  callbacksRef.current = {
    onConnectionUpdate,
    onConnectionList,
    onHealthCheckResult,
    onError,
  };

  // Handle incoming messages
  const handleMessage = useCallback((data: unknown) => {
    const message = data as ServerMessage;

    switch (message.type) {
      case "connection_list":
        setConnections(message.connections);
        callbacksRef.current.onConnectionList?.(message.connections);
        break;

      case "connection_status":
        // Track as subscribed
        setSubscribedConnections((prev) =>
          new Set(prev).add(message.payload.connection.id)
        );
        // Update connection in list if present
        setConnections((prev) => {
          const existing = prev.find(
            (c) => c.id === message.payload.connection.id
          );
          if (existing) {
            return prev.map((c) =>
              c.id === message.payload.connection.id
                ? message.payload.connection
                : c
            );
          }
          return [...prev, message.payload.connection];
        });
        break;

      case "connection_updated":
        // Update connection in list
        setConnections((prev) =>
          prev.map((c) =>
            c.id === message.payload.connection.id
              ? message.payload.connection
              : c
          )
        );
        callbacksRef.current.onConnectionUpdate?.(message.payload.connection);
        break;

      case "subscribed_all":
        setSubscribedAll(message.payload.subscribed);
        break;

      case "unsubscribed":
        if (message.payload.connection_id) {
          setSubscribedConnections((prev) => {
            const next = new Set(prev);
            next.delete(message.payload.connection_id!);
            return next;
          });
        }
        break;

      case "health_check_result":
        callbacksRef.current.onHealthCheckResult?.(message.payload);
        break;

      case "error":
        setError(message.payload.message);
        callbacksRef.current.onError?.(message.payload.message);
        break;
    }
  }, []);

  // Handle connection established
  const handleConnect = useCallback(() => {
    setError(null);
  }, []);

  // Use the realtime sync hook for WebSocket management
  const { status, send, disconnect, reconnect } = useRealtimeSync({
    url,
    onMessage: handleMessage,
    onConnect: handleConnect,
    exponentialBackoff: true,
    reconnectInterval: 1000,
    maxDelayMs: 30000,
    maxReconnectAttempts: 10,
  });

  // Commands
  const subscribeConnection = useCallback(
    (connectionId: string) => {
      send({ type: "subscribe", connection_id: connectionId });
    },
    [send],
  );

  const unsubscribeConnection = useCallback(
    (connectionId: string) => {
      setSubscribedConnections((prev) => {
        const next = new Set(prev);
        next.delete(connectionId);
        return next;
      });
      send({ type: "unsubscribe", connection_id: connectionId });
    },
    [send],
  );

  const subscribeAllConnections = useCallback(() => {
    send({ type: "subscribe_all" });
  }, [send]);

  const requestHealthCheck = useCallback(
    (connectionId: string) => {
      send({ type: "request_health_check", connection_id: connectionId });
    },
    [send],
  );

  const getConnection = useCallback(
    (connectionId: string): Connection | undefined => {
      return connections.find((c) => c.id === connectionId);
    },
    [connections],
  );

  const refresh = useCallback(() => {
    send({ type: "refresh" });
  }, [send]);

  return {
    status,
    connections,
    subscribedConnections,
    subscribedAll,
    error,
    subscribeConnection,
    unsubscribeConnection,
    subscribeAll: subscribeAllConnections,
    requestHealthCheck,
    getConnection,
    refresh,
    disconnect,
    reconnect,
  };
}

export default useConnectionsRealtimeWebSocket;
