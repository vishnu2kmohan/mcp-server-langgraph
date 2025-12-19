/**
 * useAuditWebSocket Hook
 *
 * WebSocket hook for real-time audit event streaming.
 * Provides compliance monitoring and security operations center (SOC) integration.
 *
 * Based on backend endpoint: /api/v1/audit/stream
 * Requires admin or compliance_officer role.
 */

import { useState, useCallback, useRef } from "react";
import { useRealtimeSync } from "./useRealtimeSync";

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

function getDefaultWebSocketUrl(): string {
  const protocol = window.location.protocol === "https:" ? "wss:" : "ws:";
  const host = window.location.host;
  return `${protocol}//${host}/api/v1/audit/stream`;
}

// =============================================================================
// Hook Implementation
// =============================================================================

export function useAuditWebSocket(
  options: UseAuditWebSocketOptions = {},
): UseAuditWebSocketReturn {
  const {
    url = getDefaultWebSocketUrl(),
    maxEvents = 1000,
    onEvent,
    onFilterUpdated,
  } = options;

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

  // Handle incoming messages
  const handleMessage = useCallback((data: unknown) => {
    const message = data as FilterUpdatedMessage | AuditEvent;

    // Check if it's a filter_updated message
    if ("type" in message && message.type === "filter_updated") {
      setCurrentFilter(message.filter);
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

  // Handle connection established
  const handleConnect = useCallback(() => {
    // Connection established
  }, []);

  // Handle disconnection - keep events for resumption
  const handleDisconnect = useCallback(() => {
    // Events are preserved for when we reconnect
  }, []);

  // Use the realtime sync hook for WebSocket management
  const { status, send, disconnect, reconnect } = useRealtimeSync({
    url,
    onMessage: handleMessage,
    onConnect: handleConnect,
    onDisconnect: handleDisconnect,
  });

  // Derived state
  const isConnected = status === "connected";

  // Commands
  const setFilter = useCallback(
    (filter: AuditFilter) => {
      send(filter);
    },
    [send],
  );

  const clearFilter = useCallback(() => {
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
