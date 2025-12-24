/**
 * useAuditWebSocket Hook
 *
 * WebSocket hook for real-time audit event streaming.
 * Provides compliance monitoring and security operations center (SOC) integration.
 *
 * Based on backend endpoint: /api/v1/audit/stream
 * Requires admin or compliance_officer role.
 */

import { useState, useCallback, useRef, useMemo } from "react";
import { useRealtimeSync } from "./useRealtimeSync";
import { useAppSelector } from "../store/hooks";
import { selectIsAuthenticated } from "../store/slices/authSlice";
import { getAuthToken } from "../utils/storage";

// =============================================================================
// Types
// =============================================================================

/**
 * Audit event structure matching backend schema
 */
export interface AuditEvent {
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
 * Filter for audit events
 */
export interface AuditFilter {
  categories?: string[];
  regulations?: string[];
  actors?: string[];
  event_types?: string[];
}

/**
 * Filter updated message from server
 */
interface FilterUpdatedMessage {
  type: "filter_updated";
  filter: AuditFilter;
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
// Default URL
// =============================================================================

function getDefaultWebSocketUrl(token?: string): string {
  const protocol = window.location.protocol === "https:" ? "wss:" : "ws:";
  const host = window.location.host;
  const tokenParam = token ? `?token=${encodeURIComponent(token)}` : "";
  return `${protocol}//${host}/api/v1/audit/stream${tokenParam}`;
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

  // Get auth state and token for WebSocket authentication
  const isAuthenticated = useAppSelector(selectIsAuthenticated);
  const authToken = isAuthenticated ? (getAuthToken() ?? undefined) : undefined;

  // Compute WebSocket URL - only generate URL when authenticated
  // Passing empty string prevents connection attempt before auth is ready
  const url = useMemo(
    () =>
      isAuthenticated ? (customUrl ?? getDefaultWebSocketUrl(authToken)) : "",
    [customUrl, authToken, isAuthenticated],
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
    const message = data as FilterUpdatedMessage | AuditEvent;

    // Check if it's a filter_updated message
    if ("type" in message && message.type === "filter_updated") {
      setCurrentFilter(message.filter);
      // Track active filter for restoration on reconnect
      // Empty filter means no filter (cleared)
      const hasActiveFilter =
        message.filter &&
        Object.keys(message.filter).some(
          (key) =>
            Array.isArray(message.filter[key as keyof AuditFilter]) &&
            (message.filter[key as keyof AuditFilter] as string[]).length > 0,
        );
      activeFilterRef.current = hasActiveFilter ? message.filter : null;
      callbacksRef.current.onFilterUpdated?.(message.filter);
      return;
    }

    // Otherwise, it's an audit event
    const event = message as AuditEvent;
    if (!event.event_id) {
      return; // Not a valid event
    }

    // Don't add events when paused
    if (isPausedRef.current) {
      return;
    }

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
    // Restore filter on reconnect
    if (activeFilterRef.current) {
      sendRef.current(activeFilterRef.current);
    }
  }, []);

  // Handle disconnection - keep events for resumption
  const handleDisconnect = useCallback(() => {
    // Events are preserved for when we reconnect
  }, []);

  // Use the realtime sync hook for WebSocket management
  // Enable exponential backoff for better reconnection behavior
  const { status, send, disconnect, reconnect } = useRealtimeSync({
    url,
    onMessage: handleMessage,
    onConnect: handleConnect,
    onDisconnect: handleDisconnect,
    exponentialBackoff: true,
    reconnectInterval: 1000, // Start with 1 second
    maxDelayMs: 30000, // Max 30 seconds between attempts
    maxReconnectAttempts: 10, // Try up to 10 times
  });

  // Keep sendRef in sync for use in handleConnect
  sendRef.current = send;

  // Derived state
  const isConnected = status === "connected";

  // Commands
  const setFilter = useCallback(
    (filter: AuditFilter) => {
      // Track filter immediately for restoration on reconnect
      activeFilterRef.current = filter;
      send(filter);
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
