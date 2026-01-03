/**
 * useLLMStreamingWebSocket Hook
 *
 * WebSocket hook for real-time LLM streaming observability.
 * Provides live streaming events for the DevTools panel.
 *
 * Based on backend endpoint: /api/v1/ws/llm/streaming
 */

import { useState, useCallback, useRef, useMemo, useEffect } from "react";
import { useRealtimeSync } from "./useRealtimeSync";
import { useAppDispatch, useAppSelector } from "../store/hooks";
import { logout, selectIsAuthenticated } from "../store/slices/authSlice";
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
 * Stream lifecycle status
 */
export type StreamStatus = "active" | "success" | "error" | "cancelled";

/**
 * Streaming started event payload
 */
export interface StreamingStartedEvent {
  stream_id: string;
  session_id: string;
  model: string;
  provider: string;
  timestamp: string;
}

/**
 * First chunk event payload (includes TTFC)
 */
export interface FirstChunkEvent {
  stream_id: string;
  session_id: string;
  ttfc_ms: number;
  chunk_size: number;
  timestamp: string;
}

/**
 * Chunk received event payload
 */
export interface ChunkReceivedEvent {
  stream_id: string;
  session_id: string;
  chunk_index: number;
  chunk_size: number;
  inter_chunk_latency_ms: number;
  timestamp: string;
}

/**
 * Streaming completed event payload
 */
export interface StreamingCompletedEvent {
  stream_id: string;
  session_id: string;
  status: StreamStatus;
  total_duration_ms: number;
  total_chunks: number;
  total_tokens: number;
  estimated_cost_usd: number;
  timestamp: string;
}

/**
 * Active stream info
 */
export interface ActiveStream {
  stream_id: string;
  session_id: string;
  model: string;
  provider: string;
  started_at: string;
  ttfc_ms?: number;
  chunks_received: number;
  total_chunk_size: number;
  last_chunk_at?: string;
  status: StreamStatus;
}

/**
 * WebSocket message types from server
 */
interface StreamingStartedMessage {
  type: "streaming_started";
  payload: StreamingStartedEvent;
}

interface FirstChunkMessage {
  type: "first_chunk";
  payload: FirstChunkEvent;
}

interface ChunkReceivedMessage {
  type: "chunk_received";
  payload: ChunkReceivedEvent;
}

interface StreamingCompletedMessage {
  type: "streaming_completed";
  payload: StreamingCompletedEvent;
}

interface SubscribedMessage {
  type: "subscribed";
  payload: {
    session_id?: string;
  };
}

interface UnsubscribedMessage {
  type: "unsubscribed";
  payload: Record<string, never>;
}

interface ErrorMessage {
  type: "error";
  message: string;
}

type ServerMessage =
  | StreamingStartedMessage
  | FirstChunkMessage
  | ChunkReceivedMessage
  | StreamingCompletedMessage
  | SubscribedMessage
  | UnsubscribedMessage
  | ErrorMessage;

/**
 * Options for useLLMStreamingWebSocket hook
 */
export interface UseLLMStreamingWebSocketOptions {
  /** Session ID to filter events */
  sessionId?: string;
  /** Custom WebSocket URL */
  url?: string;
  /** Callback when streaming starts */
  onStreamingStarted?: (event: StreamingStartedEvent) => void;
  /** Callback when first chunk received (TTFC) */
  onFirstChunk?: (event: FirstChunkEvent) => void;
  /** Callback when chunk received */
  onChunkReceived?: (event: ChunkReceivedEvent) => void;
  /** Callback when streaming completes */
  onStreamingCompleted?: (event: StreamingCompletedEvent) => void;
  /** Callback when an error occurs */
  onError?: (error: string) => void;
}

/**
 * Return type for useLLMStreamingWebSocket hook
 */
export interface UseLLMStreamingWebSocketReturn {
  /** Current WebSocket connection status */
  status:
    | "connecting"
    | "connected"
    | "disconnected"
    | "reconnecting"
    | "error";
  /** Currently active streams */
  activeStreams: Map<string, ActiveStream>;
  /** Current session ID filter */
  sessionId: string | null;
  /** Error message, if any */
  error: string | null;
  /** Set session ID filter */
  setSessionId: (sessionId: string | null) => void;
  /** Get a specific stream by ID */
  getStream: (streamId: string) => ActiveStream | undefined;
  /** Disconnect from WebSocket */
  disconnect: () => void;
  /** Reconnect to WebSocket */
  reconnect: () => void;
}

// =============================================================================
// Hook Implementation
// =============================================================================

export function useLLMStreamingWebSocket(
  options: UseLLMStreamingWebSocketOptions = {},
): UseLLMStreamingWebSocketReturn {
  const {
    sessionId: initialSessionId,
    url: customUrl,
    onStreamingStarted,
    onFirstChunk,
    onChunkReceived,
    onStreamingCompleted,
    onError,
  } = options;

  const dispatch = useAppDispatch();
  const isAuthenticated = useAppSelector(selectIsAuthenticated);
  const authToken = isAuthenticated ? (getAuthToken() ?? undefined) : undefined;

  // Compute WebSocket URL
  const url = useMemo(
    () =>
      isAuthenticated
        ? (customUrl ?? buildWebSocketUrl("/api/v1/ws/llm/streaming" as never, {}, true))
        : "",
    // eslint-disable-next-line react-hooks/exhaustive-deps
    [customUrl, authToken, isAuthenticated],
  );

  // State
  const [activeStreams, setActiveStreams] = useState<Map<string, ActiveStream>>(
    new Map(),
  );
  const [sessionId, setSessionIdState] = useState<string | null>(
    initialSessionId ?? null,
  );
  const [error, setError] = useState<string | null>(null);

  // Refs for callbacks
  const callbacksRef = useRef({
    onStreamingStarted,
    onFirstChunk,
    onChunkReceived,
    onStreamingCompleted,
    onError,
  });
  callbacksRef.current = {
    onStreamingStarted,
    onFirstChunk,
    onChunkReceived,
    onStreamingCompleted,
    onError,
  };

  const sendRef = useRef<(data: unknown) => void>(() => {});

  // Handle incoming messages
  const handleMessage = useCallback((data: unknown) => {
    const message = data as ServerMessage;

    switch (message.type) {
      case "streaming_started": {
        const event = message.payload;
        setActiveStreams((prev) => {
          const next = new Map(prev);
          next.set(event.stream_id, {
            stream_id: event.stream_id,
            session_id: event.session_id,
            model: event.model,
            provider: event.provider,
            started_at: event.timestamp,
            chunks_received: 0,
            total_chunk_size: 0,
            status: "active",
          });
          return next;
        });
        callbacksRef.current.onStreamingStarted?.(event);
        break;
      }

      case "first_chunk": {
        const event = message.payload;
        setActiveStreams((prev) => {
          const next = new Map(prev);
          const stream = next.get(event.stream_id);
          if (stream) {
            next.set(event.stream_id, {
              ...stream,
              ttfc_ms: event.ttfc_ms,
              chunks_received: 1,
              total_chunk_size: event.chunk_size,
              last_chunk_at: event.timestamp,
            });
          }
          return next;
        });
        callbacksRef.current.onFirstChunk?.(event);
        break;
      }

      case "chunk_received": {
        const event = message.payload;
        setActiveStreams((prev) => {
          const next = new Map(prev);
          const stream = next.get(event.stream_id);
          if (stream) {
            next.set(event.stream_id, {
              ...stream,
              chunks_received: stream.chunks_received + 1,
              total_chunk_size: stream.total_chunk_size + event.chunk_size,
              last_chunk_at: event.timestamp,
            });
          }
          return next;
        });
        callbacksRef.current.onChunkReceived?.(event);
        break;
      }

      case "streaming_completed": {
        const event = message.payload;
        setActiveStreams((prev) => {
          const next = new Map(prev);
          const stream = next.get(event.stream_id);
          if (stream) {
            next.set(event.stream_id, {
              ...stream,
              status: event.status as StreamStatus,
            });
            // Remove from active streams after a delay
            setTimeout(() => {
              setActiveStreams((current) => {
                const updated = new Map(current);
                updated.delete(event.stream_id);
                return updated;
              });
            }, 5000);
          }
          return next;
        });
        callbacksRef.current.onStreamingCompleted?.(event);
        break;
      }

      case "subscribed":
        // Subscription confirmed
        break;

      case "unsubscribed":
        // Unsubscription confirmed
        break;

      case "error":
        setError(message.message);
        callbacksRef.current.onError?.(message.message);
        break;
    }
  }, []);

  // Handle connection established
  const handleConnect = useCallback(() => {
    setError(null);
    // Subscribe with session filter
    sendRef.current({
      type: "subscribe",
      payload: { session_id: sessionId },
    });
  }, [sessionId]);

  // Use the realtime sync hook
  const {
    status,
    send,
    disconnect,
    reconnect,
    metrics: wsMetrics,
  } = useRealtimeSync({
    url,
    onMessage: handleMessage,
    onConnect: handleConnect,
    exponentialBackoff: true,
    reconnectInterval: 1000,
    maxDelayMs: 30000,
    maxReconnectAttempts: 10,
    onTokenExpired: () => dispatch(logout()),
    onProtocolVersionMismatch: () => {
      dispatch(addNotification(PROTOCOL_VERSION_MISMATCH_NOTIFICATION));
      showProtocolVersionMismatchToast();
    },
  });

  // Report WebSocket metrics
  useEffect(() => {
    if (isAuthenticated && wsMetrics.totalAttempts > 0) {
      reportWebSocketMetrics("llm_streaming", wsMetrics);
    }
  }, [isAuthenticated, wsMetrics]);

  sendRef.current = send;

  // Set session ID and re-subscribe
  const setSessionId = useCallback(
    (newSessionId: string | null) => {
      setSessionIdState(newSessionId);
      if (status === "connected") {
        send({
          type: "subscribe",
          payload: { session_id: newSessionId },
        });
      }
    },
    [send, status],
  );

  const getStream = useCallback(
    (streamId: string): ActiveStream | undefined => {
      return activeStreams.get(streamId);
    },
    [activeStreams],
  );

  return {
    status,
    activeStreams,
    sessionId,
    error,
    setSessionId,
    getStream,
    disconnect,
    reconnect,
  };
}

export default useLLMStreamingWebSocket;
