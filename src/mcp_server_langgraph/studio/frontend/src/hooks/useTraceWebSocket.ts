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
 *
 * Message Format (MessageEnvelope):
 * - trace_span: { type: "trace_span", id: "...", payload: { trace_id, span_id, name, ... } }
 * - trace_event: { type: "trace_event", id: "...", payload: { span_id, name, timestamp, ... } }
 *
 * Uses typed protocols from @/types/websocket-protocols for type-safe
 * message handling and validation.
 */

import { useCallback, useEffect, useRef, useState, useMemo } from "react";
import { useAppDispatch, useAppSelector } from "../store/hooks";
import { logout, selectIsAuthenticated } from "../store/slices/authSlice";
import { getAuthToken } from "../utils/storage";
import { devLogger } from "../utils/devLogger";
import { buildWebSocketUrl, WS_ENDPOINTS } from "../utils/websocket";
import {
  WS_CLOSE_TOKEN_EXPIRED,
  ensureValidTokenForWebSocket,
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
}

export function useTraceWebSocket(
  options: UseTraceWebSocketOptions = {},
): UseTraceWebSocketReturn {
  const { url = WS_ENDPOINTS.TRACES, sessionId, autoConnect = false } = options;

  // Redux dispatch for token expiration handling
  const dispatch = useAppDispatch();

  // Get auth state and token for WebSocket authentication
  const isAuthenticated = useAppSelector(selectIsAuthenticated);
  const authToken = useMemo(
    () => (isAuthenticated ? (getAuthToken() ?? undefined) : undefined),
    [isAuthenticated],
  );

  const wsRef = useRef<WebSocket | null>(null);
  const [isConnected, setIsConnected] = useState(false);
  const [spans, setSpans] = useState<TraceSpan[]>([]);
  const [events, setEvents] = useState<TraceEvent[]>([]);

  const handleMessage = useCallback((event: MessageEvent) => {
    try {
      const data: unknown = JSON.parse(event.data);

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

  const connect = useCallback(() => {
    // Don't attempt connection before authentication is complete
    if (!isAuthenticated) {
      return;
    }

    if (wsRef.current?.readyState === WebSocket.OPEN) {
      return;
    }

    // Build WebSocket URL using standardized utilities
    const endpoint = sessionId ? `${url}/${sessionId}` : url;
    const fullUrl = buildWebSocketUrl(endpoint, {}, !!authToken);

    const ws = new WebSocket(fullUrl);

    ws.onopen = () => {
      setIsConnected(true);

      // Send subscribe message (MessageEnvelope format for /traces endpoint)
      ws.send(
        JSON.stringify({
          type: "subscribe",
          id: crypto.randomUUID(),
          payload: {},
        }),
      );
    };

    ws.onclose = async (event) => {
      setIsConnected(false);

      // Handle token expiration close code (4010)
      if (event.code === WS_CLOSE_TOKEN_EXPIRED) {
        logger.warn("Token expired, attempting refresh...");
        const refreshed = await ensureValidTokenForWebSocket();
        if (refreshed) {
          // Token refreshed successfully - reconnect
          logger.log("Token refreshed, reconnecting...");
          setTimeout(() => connect(), 100);
        } else {
          // Refresh failed - logout
          logger.error("Token refresh failed, logging out...");
          dispatch(logout());
        }
      }
    };

    ws.onerror = (error) => {
      logger.error("WebSocket error:", error);
      setIsConnected(false);
    };

    ws.onmessage = handleMessage;

    wsRef.current = ws;
  }, [url, sessionId, authToken, isAuthenticated, handleMessage, dispatch]);

  const disconnect = useCallback(() => {
    if (wsRef.current) {
      wsRef.current.close();
      wsRef.current = null;
      setIsConnected(false);
    }
  }, []);

  const clearTraces = useCallback(() => {
    setSpans([]);
    setEvents([]);
  }, []);

  // Auto-connect on mount if enabled and authenticated
  useEffect(() => {
    if (autoConnect && isAuthenticated) {
      connect();
    }

    return () => {
      disconnect();
    };
  }, [autoConnect, isAuthenticated, connect, disconnect]);

  return {
    spans,
    events,
    isConnected,
    connect,
    disconnect,
    clearTraces,
  };
}

export default useTraceWebSocket;
