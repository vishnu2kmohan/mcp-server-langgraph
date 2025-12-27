/**
 * useTraceWebSocket Hook
 *
 * WebSocket hook for receiving real-time trace events from the MCP server.
 * Connects to the MCP WebSocket endpoint and subscribes to trace extensions.
 */

import { useCallback, useEffect, useRef, useState, useMemo } from "react";
import { useAppSelector } from "../store/hooks";
import { selectIsAuthenticated } from "../store/slices/authSlice";
import { getAuthToken } from "../utils/storage";

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
  const { url = "/api/v1/ws/mcp", sessionId, autoConnect = false } = options;

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
      const data = JSON.parse(event.data);

      // Handle trace span notifications
      if (data.method === "$/trace/span") {
        const span: TraceSpan = {
          traceId: data.params.traceId,
          spanId: data.params.spanId,
          parentSpanId: data.params.parentSpanId,
          name: data.params.name,
          startTime: data.params.startTime,
          endTime: data.params.endTime,
          status: data.params.status || "UNSET",
          attributes: data.params.attributes || {},
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
      }

      // Handle trace event notifications
      if (data.method === "$/trace/event") {
        const traceEvent: TraceEvent = {
          spanId: data.params.spanId,
          name: data.params.name,
          timestamp: data.params.timestamp,
          attributes: data.params.attributes || {},
        };

        setEvents((prev) => [...prev, traceEvent]);
      }
    } catch (error) {
      console.error("Failed to parse trace message:", error);
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

    const wsUrl = sessionId ? `${url}/${sessionId}` : url;
    const tokenParam = authToken
      ? `?token=${encodeURIComponent(authToken)}`
      : "";
    const fullUrl = `${window.location.protocol === "https:" ? "wss:" : "ws:"}//${window.location.host}${wsUrl}${tokenParam}`;

    const ws = new WebSocket(fullUrl);

    ws.onopen = () => {
      setIsConnected(true);

      // Send initialize message
      ws.send(
        JSON.stringify({
          jsonrpc: "2.0",
          id: 1,
          method: "initialize",
          params: {
            protocolVersion: "2025-11-25",
            capabilities: {},
            clientInfo: { name: "studio-frontend", version: "1.0.0" },
          },
        }),
      );
    };

    ws.onclose = () => {
      setIsConnected(false);
    };

    ws.onerror = (error) => {
      console.error("WebSocket error:", error);
      setIsConnected(false);
    };

    ws.onmessage = handleMessage;

    wsRef.current = ws;
  }, [url, sessionId, authToken, isAuthenticated, handleMessage]);

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
