/**
 * useConnectionHealthWebSocket Hook
 *
 * WebSocket hook for real-time MCP connection health monitoring.
 * Provides connection status updates, subscription management,
 * and health check requests.
 *
 * Based on backend endpoint: /api/v1/ws/connections/health (ADR-0068 consolidated WebSocket URLs)
 */

import { useState, useCallback, useRef, useMemo, useEffect } from "react";
import { useRealtimeSync } from "./useRealtimeSync";
import { useAppDispatch, useAppSelector } from "../store/hooks";
import { logout, selectIsAuthenticated } from "../store/slices/authSlice";
import { addNotification } from "../store/slices/notificationSlice";
import { buildWebSocketUrl, WS_ENDPOINTS } from "../utils/websocket";
import {
  PROTOCOL_VERSION_MISMATCH_NOTIFICATION,
  showProtocolVersionMismatchToast,
} from "../utils/websocketAuth";

// =============================================================================
// Types
// =============================================================================

/**
 * Connection health status
 */
export type ConnectionStatus =
  | "connected"
  | "disconnected"
  | "connecting"
  | "error"
  | "auth_required";

/**
 * Connection health structure matching backend schema
 */
export interface ConnectionHealth {
  id: string;
  name: string;
  url: string;
  status: ConnectionStatus;
  auth_type: string;
  server_name?: string;
  server_version?: string;
  tool_count: number;
  resource_count: number;
  prompt_count: number;
  last_error?: string;
  last_checked?: string;
}

/**
 * Summary statistics for connections
 */
export interface ConnectionSummary {
  total: number;
  connected: number;
  disconnected: number;
  connecting: number;
  error: number;
  auth_required: number;
}

/**
 * WebSocket message types from server
 */
interface ConnectionStatusMessage {
  type: "connection_status";
  connections: ConnectionHealth[];
}

interface ConnectionUpdateMessage {
  type: "connection_update";
  connection: ConnectionHealth;
}

interface PongMessage {
  type: "pong";
  timestamp: string;
}

interface ErrorMessage {
  type: "error";
  message: string;
}

interface SubscribedMessage {
  type: "subscribed";
  connection_id: string;
}

interface UnsubscribedMessage {
  type: "unsubscribed";
  connection_id: string;
}

interface HealthCheckStartedMessage {
  type: "health_check_started";
  connection_id: string;
  message: string;
}

type ServerMessage =
  | ConnectionStatusMessage
  | ConnectionUpdateMessage
  | PongMessage
  | ErrorMessage
  | SubscribedMessage
  | UnsubscribedMessage
  | HealthCheckStartedMessage;

/**
 * Options for useConnectionHealthWebSocket hook
 */
export interface UseConnectionHealthWebSocketOptions {
  /** Custom WebSocket URL (defaults to /api/v1/ws/connections/health) */
  url?: string;
  /** Callback when a connection is updated */
  onConnectionUpdate?: (connection: ConnectionHealth) => void;
  /** Callback when initial connections are loaded */
  onConnectionsLoaded?: (connections: ConnectionHealth[]) => void;
  /** Callback when health check starts */
  onHealthCheckStarted?: (connectionId: string) => void;
  /** Callback when an error occurs */
  onError?: (error: string) => void;
}

/**
 * Return type for useConnectionHealthWebSocket hook
 */
export interface UseConnectionHealthWebSocketReturn {
  /** Current WebSocket connection status */
  status:
    | "connecting"
    | "connected"
    | "disconnected"
    | "reconnecting"
    | "error";
  /** List of all connections with health status */
  connections: ConnectionHealth[];
  /** Set of connection IDs currently subscribed to */
  subscribedConnections: Set<string>;
  /** Current error message, if any */
  error: string | null;
  /** Timestamp of last pong received */
  lastPong: string | null;
  /** Summary statistics for connections */
  summary: ConnectionSummary;
  /** Send a ping to keep connection alive */
  sendPing: () => void;
  /** Request a refresh of all connection statuses */
  refresh: () => void;
  /** Subscribe to updates for a specific connection */
  subscribe: (connectionId: string) => void;
  /** Unsubscribe from updates for a specific connection */
  unsubscribe: (connectionId: string) => void;
  /** Request a health check for a specific connection */
  checkHealth: (connectionId: string) => void;
  /** Get a specific connection by ID */
  getConnection: (connectionId: string) => ConnectionHealth | undefined;
  /** Manually disconnect from WebSocket */
  disconnect: () => void;
  /** Manually reconnect to WebSocket */
  reconnect: () => void;
  /** Number of reconnection attempts (for dashboard visibility) */
  reconnectAttempts: number;
}

// =============================================================================
// Default URL
// =============================================================================

function getDefaultWebSocketUrl(includeToken: boolean = false): string {
  // Use standardized WebSocket utilities (ADR-0068 consolidated WebSocket URLs)
  return buildWebSocketUrl(WS_ENDPOINTS.CONNECTIONS_HEALTH, {}, includeToken);
}

// =============================================================================
// Hook Implementation
// =============================================================================

export function useConnectionHealthWebSocket(
  options: UseConnectionHealthWebSocketOptions = {},
): UseConnectionHealthWebSocketReturn {
  const {
    url: customUrl,
    onConnectionUpdate,
    onConnectionsLoaded,
    onHealthCheckStarted,
    onError,
  } = options;

  // Get auth state for WebSocket authentication
  const dispatch = useAppDispatch();
  const isAuthenticated = useAppSelector(selectIsAuthenticated);

  // Compute WebSocket URL - only generate URL when authenticated
  // Passing empty string prevents connection attempt before auth is ready
  // The buildWebSocketUrl utility fetches the auth token internally when includeAuthToken=true
  const url = useMemo(
    () =>
      isAuthenticated
        ? (customUrl ?? getDefaultWebSocketUrl(true /* includeAuthToken */))
        : "",
    [customUrl, isAuthenticated],
  );

  // State
  const [connections, setConnections] = useState<ConnectionHealth[]>([]);
  const [subscribedConnections, setSubscribedConnections] = useState<
    Set<string>
  >(new Set());
  const [error, setError] = useState<string | null>(null);
  const [lastPong, setLastPong] = useState<string | null>(null);

  // Refs for callbacks to avoid stale closures
  const callbacksRef = useRef({
    onConnectionUpdate,
    onConnectionsLoaded,
    onHealthCheckStarted,
    onError,
  });
  callbacksRef.current = {
    onConnectionUpdate,
    onConnectionsLoaded,
    onHealthCheckStarted,
    onError,
  };

  // Ref to track subscribed connections for restoration on reconnect
  const subscribedConnectionsRef = useRef<Set<string>>(new Set());

  // Ref for send function to use in handleConnect
  const sendRef = useRef<(data: unknown) => void>(() => {});

  // Handle incoming messages
  const handleMessage = useCallback((data: unknown) => {
    const message = data as ServerMessage;

    switch (message.type) {
      case "connection_status":
        setConnections(message.connections);
        callbacksRef.current.onConnectionsLoaded?.(message.connections);
        break;

      case "connection_update":
        setConnections((prevConnections) => {
          const index = prevConnections.findIndex(
            (c) => c.id === message.connection.id,
          );
          if (index >= 0) {
            const newConnections = [...prevConnections];
            newConnections[index] = message.connection;
            return newConnections;
          } else {
            return [...prevConnections, message.connection];
          }
        });
        callbacksRef.current.onConnectionUpdate?.(message.connection);
        break;

      case "pong":
        setLastPong(message.timestamp);
        break;

      case "error":
        setError(message.message);
        callbacksRef.current.onError?.(message.message);
        break;

      case "subscribed":
        subscribedConnectionsRef.current.add(message.connection_id);
        setSubscribedConnections((prev) =>
          new Set(prev).add(message.connection_id),
        );
        break;

      case "unsubscribed":
        subscribedConnectionsRef.current.delete(message.connection_id);
        setSubscribedConnections((prev) => {
          const next = new Set(prev);
          next.delete(message.connection_id);
          return next;
        });
        break;

      case "health_check_started":
        callbacksRef.current.onHealthCheckStarted?.(message.connection_id);
        break;
    }
  }, []);

  // Handle connection established - restore subscriptions
  const handleConnect = useCallback(() => {
    setError(null);

    // Restore subscriptions on reconnect
    subscribedConnectionsRef.current.forEach((connectionId) => {
      sendRef.current({ type: "subscribe", connection_id: connectionId });
    });
  }, []);

  // Handle disconnection - keep connections for resumption
  const handleDisconnect = useCallback(() => {
    // Connections are preserved for when we reconnect
  }, []);

  // Use the realtime sync hook for WebSocket management
  // Enable exponential backoff for better reconnection behavior
  const { status, send, disconnect, reconnect, reconnectAttempts, metrics } =
    useRealtimeSync({
      url,
      onMessage: handleMessage,
      onConnect: handleConnect,
      onDisconnect: handleDisconnect,
      exponentialBackoff: true,
      reconnectInterval: 1000, // Start with 1 second
      maxDelayMs: 30000, // Max 30 seconds between attempts
      maxReconnectAttempts: 10, // Try up to 10 times
      onTokenExpired: () => dispatch(logout()),
      onProtocolVersionMismatch: () => {
        dispatch(addNotification(PROTOCOL_VERSION_MISMATCH_NOTIFICATION));
        showProtocolVersionMismatchToast();
      },
    });

  // Report WebSocket metrics for observability
  useEffect(() => {
    if (isAuthenticated && metrics.totalAttempts > 0) {
      import("../utils/websocketTelemetry").then(
        ({ reportWebSocketMetrics }) => {
          reportWebSocketMetrics("connection_health", metrics);
        },
      );
    }
  }, [isAuthenticated, metrics]);

  // Keep sendRef in sync for use in handleConnect
  sendRef.current = send;

  // Computed summary
  const summary = useMemo<ConnectionSummary>(() => {
    const counts: ConnectionSummary = {
      total: connections.length,
      connected: 0,
      disconnected: 0,
      connecting: 0,
      error: 0,
      auth_required: 0,
    };

    for (const conn of connections) {
      switch (conn.status) {
        case "connected":
          counts.connected++;
          break;
        case "disconnected":
          counts.disconnected++;
          break;
        case "connecting":
          counts.connecting++;
          break;
        case "error":
          counts.error++;
          break;
        case "auth_required":
          counts.auth_required++;
          break;
      }
    }

    return counts;
  }, [connections]);

  // Commands
  const sendPing = useCallback(() => {
    send({ type: "ping" });
  }, [send]);

  const refresh = useCallback(() => {
    send({ type: "refresh" });
  }, [send]);

  const subscribe = useCallback(
    (connectionId: string) => {
      send({ type: "subscribe", connection_id: connectionId });
    },
    [send],
  );

  const unsubscribe = useCallback(
    (connectionId: string) => {
      send({ type: "unsubscribe", connection_id: connectionId });
    },
    [send],
  );

  const checkHealth = useCallback(
    (connectionId: string) => {
      send({ type: "check_health", connection_id: connectionId });
    },
    [send],
  );

  const getConnection = useCallback(
    (connectionId: string): ConnectionHealth | undefined => {
      return connections.find((c) => c.id === connectionId);
    },
    [connections],
  );

  return {
    status,
    connections,
    subscribedConnections,
    error,
    lastPong,
    summary,
    sendPing,
    refresh,
    subscribe,
    unsubscribe,
    checkHealth,
    getConnection,
    disconnect,
    reconnect,
    reconnectAttempts,
  };
}

export default useConnectionHealthWebSocket;
