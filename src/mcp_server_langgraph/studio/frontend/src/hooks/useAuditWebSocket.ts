/**
 * useAuditWebSocket Hook
 *
 * WebSocket hook for real-time audit event streaming.
 * Provides compliance monitoring and security operations center (SOC) integration.
 *
 * Based on backend endpoint: /api/v1/audit/stream
 * Requires admin or compliance_officer role.
 */

import { useState, useCallback, useRef, useMemo, useEffect } from "react";
import { useRealtimeSync } from "./useRealtimeSync";
import {
  transformSnakeToCamel,
  transformCamelToSnake,
} from "../api/transforms";
import { useAppDispatch, useAppSelector } from "../store/hooks";
import {
  logout,
  selectIsAuthenticated,
  selectWebSocketPermissions,
} from "../store/slices/authSlice";
import { addNotification } from "../store/slices/notificationSlice";
import { getAuthToken } from "../utils/storage";
import { buildWebSocketUrl, WS_ENDPOINTS } from "../utils/websocket";
import {
  PROTOCOL_VERSION_MISMATCH_NOTIFICATION,
  showProtocolVersionMismatchToast,
} from "../utils/websocketAuth";
import { reportWebSocketMetrics } from "../utils/websocketTelemetry";

// =============================================================================
// Types
// =============================================================================

/**
 * Audit event structure matching backend schema (snake_case)
 */
export interface AuditEventBackend {
  event_id: string;
  timestamp: string;
  category: string;
  event_type: string;
  actor: string;
  resource?: string;
  regulation?: string;
  details?: Record<string, unknown>;
}

/**
 * Audit event structure for frontend (camelCase)
 */
export interface AuditEvent {
  eventId: string;
  timestamp: string;
  category: string;
  eventType: string;
  actor: string;
  resource?: string;
  regulation?: string;
  details?: Record<string, unknown>;
}

/**
 * Filter for audit events (backend snake_case)
 */
export interface AuditFilterBackend {
  categories?: string[];
  regulations?: string[];
  actors?: string[];
  event_types?: string[];
}

/**
 * Filter for audit events (frontend camelCase)
 */
export interface AuditFilter {
  categories?: string[];
  regulations?: string[];
  actors?: string[];
  eventTypes?: string[];
}

/**
 * Filter updated message from server (uses backend snake_case filter)
 */
interface FilterUpdatedMessage {
  type: "filter_updated";
  filter: AuditFilterBackend;
}

/**
 * Options for useAuditWebSocket hook
 */
export interface UseAuditWebSocketOptions {
  /** Custom WebSocket URL (defaults to /api/v1/audit/stream) */
  url?: string;
  /** Maximum number of events to keep in memory */
  maxEvents?: number;
  /** Callback when an audit event is received */
  onEvent?: (event: AuditEvent) => void;
  /** Callback when filter is updated */
  onFilterUpdated?: (filter: AuditFilter) => void;
}

/**
 * Return type for useAuditWebSocket hook
 */
export interface UseAuditWebSocketReturn {
  /** Current connection status */
  status:
    | "connecting"
    | "connected"
    | "disconnected"
    | "reconnecting"
    | "error";
  /** Whether connected to the audit stream */
  isConnected: boolean;
  /** List of received audit events (newest first) */
  events: AuditEvent[];
  /** Current active filter */
  currentFilter: AuditFilter | null;
  /** Whether event streaming is paused */
  isPaused: boolean;
  /** Set a new filter for audit events */
  setFilter: (filter: AuditFilter) => void;
  /** Clear the current filter (receive all events) */
  clearFilter: () => void;
  /** Clear all stored events */
  clearEvents: () => void;
  /** Pause receiving events (still connected) */
  pause: () => void;
  /** Resume receiving events */
  resume: () => void;
  /** Manually disconnect from WebSocket */
  disconnect: () => void;
  /** Manually reconnect to WebSocket */
  reconnect: () => void;
}

// =============================================================================
// Hook Implementation
// =============================================================================

export function useAuditWebSocket(
  options: UseAuditWebSocketOptions = {},
): UseAuditWebSocketReturn {
  const {
    url: customUrl,
    maxEvents = 1000,
    onEvent,
    onFilterUpdated,
  } = options;

  // Redux dispatch for token expiration handling
  const dispatch = useAppDispatch();

  // Get auth state and token for WebSocket authentication
  const isAuthenticated = useAppSelector(selectIsAuthenticated);
  const wsPermissions = useAppSelector(selectWebSocketPermissions);
  // Track token changes to trigger URL regeneration on refresh
  const authToken = isAuthenticated ? (getAuthToken() ?? undefined) : undefined;

  // Check if user has permission for audit WebSocket
  const hasAuditPermission = wsPermissions?.audit ?? false;

  // Compute WebSocket URL - only generate URL when authenticated AND has permission
  // Passing empty string prevents connection attempt before auth is ready or if unauthorized
  const url = useMemo(
    () =>
      isAuthenticated && hasAuditPermission
        ? (customUrl ?? buildWebSocketUrl(WS_ENDPOINTS.AUDIT, {}, true))
        : "",
    // authToken dependency ensures URL regenerates when token is refreshed
    // eslint-disable-next-line react-hooks/exhaustive-deps
    [customUrl, authToken, isAuthenticated, hasAuditPermission],
  );

  // State
  const [events, setEvents] = useState<AuditEvent[]>([]);
  const [currentFilter, setCurrentFilter] = useState<AuditFilter | null>(null);
  const [isPaused, setIsPaused] = useState(false);

  // Refs for callbacks and paused state to avoid stale closures
  const callbacksRef = useRef({ onEvent, onFilterUpdated });
  callbacksRef.current = { onEvent, onFilterUpdated };

  const isPausedRef = useRef(isPaused);
  isPausedRef.current = isPaused;

  const maxEventsRef = useRef(maxEvents);
  maxEventsRef.current = maxEvents;

  // Ref to store the active filter for restoration on reconnect
  const activeFilterRef = useRef<AuditFilter | null>(null);

  // Ref for send function to use in handleConnect
  const sendRef = useRef<(data: unknown) => void>(() => {});

  // Handle incoming messages
  const handleMessage = useCallback((data: unknown) => {
    const message = data as FilterUpdatedMessage | AuditEventBackend;

    // Check if it's a filter_updated message
    if ("type" in message && message.type === "filter_updated") {
      // Transform backend filter to frontend camelCase
      const camelCaseFilter = transformSnakeToCamel(
        message.filter,
      ) as unknown as AuditFilter;
      setCurrentFilter(camelCaseFilter);
      // Track active filter for restoration on reconnect (keep backend format)
      // Empty filter means no filter (cleared)
      const hasActiveFilter =
        message.filter &&
        Object.keys(message.filter).some(
          (key) =>
            Array.isArray(message.filter[key as keyof AuditFilterBackend]) &&
            (message.filter[key as keyof AuditFilterBackend] as string[])
              .length > 0,
        );
      activeFilterRef.current = hasActiveFilter ? camelCaseFilter : null;
      callbacksRef.current.onFilterUpdated?.(camelCaseFilter);
      return;
    }

    // Otherwise, it's an audit event (backend format)
    const backendEvent = message as AuditEventBackend;
    if (!backendEvent.event_id) {
      return; // Not a valid event
    }

    // Don't add events when paused
    if (isPausedRef.current) {
      return;
    }

    // Transform to frontend camelCase format
    const event = transformSnakeToCamel(backendEvent) as unknown as AuditEvent;

    // Add event to the front (newest first)
    setEvents((prevEvents) => {
      const newEvents = [event, ...prevEvents];
      // Respect maxEvents limit
      if (newEvents.length > maxEventsRef.current) {
        return newEvents.slice(0, maxEventsRef.current);
      }
      return newEvents;
    });

    callbacksRef.current.onEvent?.(event);
  }, []);

  // Handle connection established - restore filter
  const handleConnect = useCallback(() => {
    // Restore filter on reconnect (transform to snake_case for backend)
    if (activeFilterRef.current) {
      const backendFilter = transformCamelToSnake(activeFilterRef.current);
      sendRef.current(backendFilter);
    }
  }, []);

  // Handle disconnection - keep events for resumption
  const handleDisconnect = useCallback(() => {
    // Events are preserved for when we reconnect
  }, []);

  // Use the realtime sync hook for WebSocket management
  // Enable exponential backoff for better reconnection behavior
  const { status, send, disconnect, reconnect, metrics } = useRealtimeSync({
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
      reportWebSocketMetrics("audit", metrics);
    }
  }, [isAuthenticated, metrics]);

  // Keep sendRef in sync for use in handleConnect
  sendRef.current = send;

  // Derived state
  const isConnected = status === "connected";

  // Commands
  const setFilter = useCallback(
    (filter: AuditFilter) => {
      // Track filter immediately for restoration on reconnect
      activeFilterRef.current = filter;
      // Transform to snake_case before sending to backend
      const backendFilter = transformCamelToSnake(filter);
      send(backendFilter);
    },
    [send],
  );

  const clearFilter = useCallback(() => {
    // Clear the tracked filter
    activeFilterRef.current = null;
    send({});
  }, [send]);

  const clearEvents = useCallback(() => {
    setEvents([]);
  }, []);

  const pause = useCallback(() => {
    setIsPaused(true);
  }, []);

  const resume = useCallback(() => {
    setIsPaused(false);
  }, []);

  return {
    status,
    isConnected,
    events,
    currentFilter,
    isPaused,
    setFilter,
    clearFilter,
    clearEvents,
    pause,
    resume,
    disconnect,
    reconnect,
  };
}

export default useAuditWebSocket;
