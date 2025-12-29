/**
 * useTraceWebSocket Hook
 *
 * WebSocket hook for receiving real-time trace events from the trace service.
 * Connects to the /api/v1/ws/traces WebSocket endpoint.
 *
 * Features:
 * - Automatic subscription on connect
 * - Real-time trace span updates
 * - Real-time trace event updates
 * - Automatic reconnection with exponential backoff (via useRealtimeSync)
 * - Reconnection metrics for observability
 *
 * Message Format (MessageEnvelope):
 * - trace_span: { type: "trace_span", id: "...", payload: { trace_id, span_id, name, ... } }
 * - trace_event: { type: "trace_event", id: "...", payload: { span_id, name, timestamp, ... } }
 *
 * Uses typed protocols from @/types/websocket-protocols for type-safe
 * message handling and validation.
 */

import { useCallback, useEffect, useState, useMemo, useRef } from "react";
import { useAppDispatch, useAppSelector } from "../store/hooks";
import { logout, selectIsAuthenticated } from "../store/slices/authSlice";
import { addNotification } from "../store/slices/notificationSlice";
import { devLogger } from "../utils/devLogger";
import { buildWebSocketUrl, WS_ENDPOINTS } from "../utils/websocket";
import { useRealtimeSync } from "./useRealtimeSync";
import { reportWebSocketMetrics } from "../utils/websocketTelemetry";
import {
  PROTOCOL_VERSION_MISMATCH_NOTIFICATION,
  showProtocolVersionMismatchToast,
} from "../utils/websocketAuth";

// Import typed protocols for type-safe WebSocket message handling
import {
  isTraceSpanEntry,
  isTraceEventEntry,
} from "../types/websocket-protocols";
import type {
  TraceSpanEntry,
  TraceEventEntry,
  TracesMessage,
} from "../types/websocket-protocols";

// Create prefixed logger for this hook
const logger = devLogger.withPrefix("[TraceWebSocket]");

// Re-export protocol types for consumers
export type { TraceSpanEntry, TraceEventEntry, TracesMessage };

export interface TraceSpan {
  traceId: string;
  spanId: string;
  parentSpanId?: string;
  name: string;
  startTime: string;
  endTime?: string;
  status: "OK" | "ERROR" | "UNSET";
  attributes: Record<string, unknown>;
}

export interface TraceEvent {
  spanId: string;
  name: string;
  timestamp: string;
  attributes: Record<string, unknown>;
}

interface UseTraceWebSocketOptions {
  url?: string;
  sessionId?: string;
  autoConnect?: boolean;
}

interface UseTraceWebSocketReturn {
  spans: TraceSpan[];
  events: TraceEvent[];
  isConnected: boolean;
  connect: () => void;
  disconnect: () => void;
  clearTraces: () => void;
  /** Number of reconnection attempts (for dashboard visibility) */
  reconnectAttempts: number;
}

export function useTraceWebSocket(
  options: UseTraceWebSocketOptions = {},
): UseTraceWebSocketReturn {
  const { url = WS_ENDPOINTS.TRACES, sessionId, autoConnect = false } = options;

  // Redux dispatch for token expiration handling
  const dispatch = useAppDispatch();

  // Get auth state for WebSocket authentication
  const isAuthenticated = useAppSelector(selectIsAuthenticated);

  // State for spans and events
  const [spans, setSpans] = useState<TraceSpan[]>([]);
  const [events, setEvents] = useState<TraceEvent[]>([]);

  // Track whether we should be connected (for manual connect/disconnect)
  const [shouldConnect, setShouldConnect] = useState(autoConnect);
  const hasSentSubscribeRef = useRef(false);

  // Build WebSocket URL
  const wsUrl = useMemo(() => {
    if (!shouldConnect || !isAuthenticated) return "";
    const endpoint = sessionId ? `${url}/${sessionId}` : url;
    return buildWebSocketUrl(endpoint, {}, true);
  }, [url, sessionId, shouldConnect, isAuthenticated]);

  // Message handler
  const handleMessage = useCallback((data: unknown) => {
    try {
      // Use centralized type guards for type-safe message handling
      if (isTraceSpanEntry(data)) {
        const payload = data.payload;
        const span: TraceSpan = {
          traceId: payload.trace_id,
          spanId: payload.span_id,
          parentSpanId: payload.parent_span_id ?? undefined,
          name: payload.name,
          startTime: String(payload.start_time),
          endTime: payload.end_time ? String(payload.end_time) : undefined,
          status:
            (payload.status?.toUpperCase() as "OK" | "ERROR" | "UNSET") ||
            "UNSET",
          attributes: payload.attributes || {},
        };

        setSpans((prev) => {
          // Update existing span or add new one
          const existingIndex = prev.findIndex((s) => s.spanId === span.spanId);
          if (existingIndex >= 0) {
            const updated = [...prev];
            updated[existingIndex] = span;
            return updated;
          }
          return [...prev, span];
        });
      } else if (isTraceEventEntry(data)) {
        // Use centralized type guard for trace events
        const payload = data.payload;
        const traceEvent: TraceEvent = {
          spanId: payload.span_id,
          name: payload.name,
          timestamp: payload.timestamp,
          attributes: payload.attributes || {},
        };

        setEvents((prev) => [...prev, traceEvent]);
      }
    } catch (error) {
      logger.error("Failed to parse trace message:", error);
    }
  }, []);

  // Connection callbacks
  const handleConnect = useCallback(() => {
    logger.log("Connected to trace WebSocket");
  }, []);

  const handleDisconnect = useCallback(() => {
    logger.log("Disconnected from trace WebSocket");
    hasSentSubscribeRef.current = false;
  }, []);

  const handleError = useCallback((error: Error) => {
    logger.error("WebSocket error:", error);
  }, []);

  const handleTokenExpired = useCallback(() => {
    logger.error("Token expired, logging out...");
    dispatch(logout());
  }, [dispatch]);

  // Use the centralized realtime sync hook
  const {
    status,
    send,
    disconnect: wsDisconnect,
    reconnect: _wsReconnect,
    reconnectAttempts,
    metrics,
  } = useRealtimeSync({
    url: wsUrl,
    onMessage: handleMessage,
    onConnect: handleConnect,
    onDisconnect: handleDisconnect,
    onError: handleError,
    onTokenExpired: handleTokenExpired,
    onProtocolVersionMismatch: () => {
      dispatch(addNotification(PROTOCOL_VERSION_MISMATCH_NOTIFICATION));
      showProtocolVersionMismatchToast();
    },
    exponentialBackoff: true,
    reconnectInterval: 1000,
    maxReconnectAttempts: 10,
    maxDelayMs: 30000,
  });

  // Report metrics for observability
  useEffect(() => {
    if (isAuthenticated && metrics.totalAttempts > 0) {
      reportWebSocketMetrics("traces", metrics);
    }
  }, [isAuthenticated, metrics]);

  // Send subscribe message when connected
  useEffect(() => {
    if (status === "connected" && !hasSentSubscribeRef.current) {
      // Send subscribe message (MessageEnvelope format for /traces endpoint)
      send({
        type: "subscribe",
        id: crypto.randomUUID(),
        payload: {},
      });
      hasSentSubscribeRef.current = true;
    }
  }, [status, send]);

  // Derive isConnected from status
  const isConnected = status === "connected";

  // Manual connect function
  const connect = useCallback(() => {
    if (!isAuthenticated) {
      return;
    }
    setShouldConnect(true);
  }, [isAuthenticated]);

  // Manual disconnect function
  const disconnect = useCallback(() => {
    setShouldConnect(false);
    wsDisconnect();
  }, [wsDisconnect]);

  // Clear traces function
  const clearTraces = useCallback(() => {
    setSpans([]);
    setEvents([]);
  }, []);

  // Handle autoConnect changes
  useEffect(() => {
    if (autoConnect && isAuthenticated) {
      setShouldConnect(true);
    }
  }, [autoConnect, isAuthenticated]);

  // Cleanup on unmount
  useEffect(() => {
    return () => {
      wsDisconnect();
    };
  }, [wsDisconnect]);

  return {
    spans,
    events,
    isConnected,
    connect,
    disconnect,
    clearTraces,
    reconnectAttempts,
  };
}

export default useTraceWebSocket;
