/**
 * useDevToolsWebSocket Hook
 *
 * WebSocket integration for DevTools console and network tabs.
 * Receives real-time log and network entries from the backend.
 *
 * Uses useRealtimeSync for centralized WebSocket management with:
 * - Automatic reconnection with exponential backoff
 * - Metrics reporting to websocketTelemetry
 * - Consistent connection state management
 *
 * Uses typed protocols from @/types/websocket-protocols for type-safe
 * message handling and validation.
 */
import { useState, useCallback, useEffect, useRef } from "react";

import { useRealtimeSync } from "../../../hooks/useRealtimeSync";
import { buildWebSocketUrl, WS_ENDPOINTS } from "../../../utils/websocket";
import { reportWebSocketMetrics } from "../../../utils/websocketTelemetry";
import { authenticatedFetch } from "../../../utils/authenticatedFetch";
import type { ConsoleEntry, NetworkEntry } from "../types";

// Import typed protocols for type-safe WebSocket message handling
import {
  isConsoleLogEntry,
  isNetworkRequestEntry,
  isNetworkUpdateEntry,
  isTraceStepEntry,
} from "../../../types/websocket-protocols";
import type {
  ConsoleLogEntry,
  NetworkRequestEntry,
  NetworkUpdateEntry,
  DevToolsMessage,
  TraceStepPayload,
} from "../../../types/websocket-protocols";

// =============================================================================
// Types
// =============================================================================

export type DevToolsWebSocketStatus =
  | "disconnected"
  | "connecting"
  | "connected"
  | "error";

export interface UseDevToolsWebSocketOptions {
  /** Whether to enable the WebSocket connection */
  enabled?: boolean;
  /** Custom WebSocket URL */
  url?: string;
  /** Maximum number of console entries to keep */
  maxConsoleEntries?: number;
  /** Maximum number of network entries to keep */
  maxNetworkEntries?: number;
  /** Context entity ID for filtering (session or workflow ID) */
  contextEntityId?: string | null;
  /** Enable HTTP polling fallback when WebSocket is disconnected (Fix 4) */
  enableHttpFallback?: boolean;
  /** HTTP polling interval in milliseconds (default: 5000) */
  httpPollingInterval?: number;
}

export interface UseDevToolsWebSocketReturn {
  /** Current connection status */
  status: DevToolsWebSocketStatus;
  /** Console entries received from WebSocket */
  consoleEntries: ConsoleEntry[];
  /** Network entries received from WebSocket */
  networkEntries: NetworkEntry[];
  /** Agent trace steps received from WebSocket */
  traceSteps: TraceStepPayload[];
  /** Clear all console entries */
  clearConsoleEntries: () => void;
  /** Clear all network entries */
  clearNetworkEntries: () => void;
  /** Clear all trace steps */
  clearTraceSteps: () => void;
  /** Manually reconnect */
  reconnect: () => void;
  /** Number of reconnection attempts (for dashboard visibility) */
  reconnectAttempts: number;
  /** Whether HTTP polling fallback is active (Fix 4) */
  isHttpPollingActive: boolean;
}

// =============================================================================
// Constants
// =============================================================================

const DEFAULT_MAX_CONSOLE_ENTRIES = 1000;
const DEFAULT_MAX_NETWORK_ENTRIES = 500;
const ENDPOINT_NAME = "devtools";

// Re-export protocol types for consumers (backwards compatibility)
export type {
  ConsoleLogEntry,
  NetworkRequestEntry,
  NetworkUpdateEntry,
  DevToolsMessage,
};

/**
 * Get WebSocket URL for DevTools endpoint using centralized utility.
 *
 * Uses buildWebSocketUrl from @/utils/websocket for consistent URL construction
 * and proper authentication handling (includes auth token in query params).
 *
 * @param contextEntityId - Optional session or workflow ID for context filtering
 * @returns Full WebSocket URL with auth token
 */
function getDefaultWebSocketUrl(contextEntityId?: string | null): string {
  const params: Record<string, string> = {};
  if (contextEntityId) {
    params.context_id = contextEntityId;
  }
  // Use centralized URL builder with auth token included
  return buildWebSocketUrl(WS_ENDPOINTS.DEVTOOLS, params, true);
}

function generateId(): string {
  return `${Date.now()}-${Math.random().toString(36).slice(2, 9)}`;
}

// =============================================================================
// Hook Implementation
// =============================================================================

export function useDevToolsWebSocket(
  options: UseDevToolsWebSocketOptions = {},
): UseDevToolsWebSocketReturn {
  const {
    enabled = true,
    url,
    maxConsoleEntries = DEFAULT_MAX_CONSOLE_ENTRIES,
    maxNetworkEntries = DEFAULT_MAX_NETWORK_ENTRIES,
    contextEntityId,
    enableHttpFallback = true, // Fix 4: Enable HTTP polling fallback by default
    httpPollingInterval = 5000,
  } = options;

  const [consoleEntries, setConsoleEntries] = useState<ConsoleEntry[]>([]);
  const [networkEntries, setNetworkEntries] = useState<NetworkEntry[]>([]);
  const [traceSteps, setTraceSteps] = useState<TraceStepPayload[]>([]);
  const [connectionStatus, setConnectionStatus] =
    useState<DevToolsWebSocketStatus>("disconnected");
  // Fix 4: Track HTTP polling state
  const [isHttpPollingActive, setIsHttpPollingActive] = useState(false);

  const contextEntityIdRef = useRef(contextEntityId);
  contextEntityIdRef.current = contextEntityId;

  // Compute WebSocket URL (empty string if disabled, hook handles empty URL by not connecting)
  const wsUrl = enabled ? (url ?? getDefaultWebSocketUrl(contextEntityId)) : "";

  /**
   * Check if an entry should be included based on context filtering.
   */
  const shouldIncludeEntry = useCallback(
    (entryData?: Record<string, unknown>): boolean => {
      const ctxId = contextEntityIdRef.current;
      if (!ctxId) return true; // No filter, include all

      if (!entryData) return true; // Global entry

      const sessionId = entryData.sessionId as string | undefined;
      const workflowId = entryData.workflowId as string | undefined;
      const sessionIdUnderscore = entryData.session_id as string | undefined;

      // Include if no session/workflow (global) or matches context
      if (!sessionId && !workflowId) return true;
      return (
        sessionId === ctxId ||
        workflowId === ctxId ||
        sessionIdUnderscore === ctxId
      );
    },
    [],
  );

  /**
   * Handle incoming WebSocket messages.
   *
   * Uses centralized type guards from websocket-protocols.ts for
   * type-safe message validation and handling.
   */
  const handleMessage = useCallback(
    (data: unknown) => {
      // Debug: Log all incoming WebSocket messages (remove after verification)
      console.debug("[DevTools WS] Received message:", data);

      // Use centralized type guards for type-safe message handling
      if (isConsoleLogEntry(data)) {
        const entry: ConsoleEntry = {
          ...data.payload,
          id: data.payload.id ?? generateId(),
        } as ConsoleEntry;

        // Filter by context
        if (shouldIncludeEntry(entry.data as Record<string, unknown>)) {
          setConsoleEntries((prev) => {
            const newEntries = [...prev, entry];
            if (newEntries.length > maxConsoleEntries) {
              return newEntries.slice(-maxConsoleEntries);
            }
            return newEntries;
          });
        }
      } else if (isNetworkRequestEntry(data)) {
        const entry: NetworkEntry = {
          ...data.payload,
          id: data.payload.id ?? generateId(),
        } as NetworkEntry;

        setNetworkEntries((prev) => {
          const newEntries = [...prev, entry];
          if (newEntries.length > maxNetworkEntries) {
            return newEntries.slice(-maxNetworkEntries);
          }
          return newEntries;
        });
      } else if (isNetworkUpdateEntry(data)) {
        setNetworkEntries((prev) =>
          prev.map((entry) =>
            entry.id === data.payload.id
              ? { ...entry, ...data.payload }
              : entry,
          ),
        );
      } else if (isTraceStepEntry(data)) {
        const step = data.payload;
        // Debug: Log trace step entries (remove after verification)
        console.debug("[DevTools WS] Trace step received:", {
          name: step.name,
          status: step.status,
          session_id: step.session_id,
        });
        if (shouldIncludeEntry(step as unknown as Record<string, unknown>)) {
          setTraceSteps((prev) => [...prev, step]);
        }
      }
    },
    [maxConsoleEntries, maxNetworkEntries, shouldIncludeEntry],
  );

  /**
   * Handle connection established.
   */
  const handleConnect = useCallback(() => {
    setConnectionStatus("connected");
  }, []);

  /**
   * Handle disconnection.
   */
  const handleDisconnect = useCallback(() => {
    setConnectionStatus("disconnected");
  }, []);

  /**
   * Handle connection errors.
   */
  const handleError = useCallback(() => {
    setConnectionStatus("error");
  }, []);

  // Use centralized useRealtimeSync hook
  const {
    status,
    disconnect,
    reconnect: wsReconnect,
    reconnectAttempts,
    metrics,
  } = useRealtimeSync({
    url: wsUrl,
    onMessage: handleMessage,
    onConnect: handleConnect,
    onDisconnect: handleDisconnect,
    onError: handleError,
    exponentialBackoff: true,
    reconnectInterval: 1000,
    maxReconnectAttempts: 10,
    maxDelayMs: 30000,
  });

  // Update connection status based on useRealtimeSync status
  useEffect(() => {
    if (status === "connecting") {
      setConnectionStatus("connecting");
    } else if (status === "connected") {
      setConnectionStatus("connected");
    } else if (status === "error") {
      setConnectionStatus("error");
    } else if (status === "disconnected") {
      setConnectionStatus("disconnected");
    }
  }, [status]);

  // Report metrics for observability
  useEffect(() => {
    if (enabled && metrics.totalAttempts > 0) {
      reportWebSocketMetrics(ENDPOINT_NAME, metrics);
    }
  }, [enabled, metrics]);

  // Disconnect on unmount
  useEffect(() => {
    return () => {
      disconnect();
    };
  }, [disconnect]);

  // Fix 4: HTTP polling fallback when WebSocket is disconnected
  // This ensures Agent Trace data is available even when WS fails
  useEffect(() => {
    // Only poll if:
    // - HTTP fallback is enabled
    // - WebSocket is disconnected
    // - We have a session/context to poll for
    // - The hook is enabled
    const shouldPoll =
      enableHttpFallback &&
      enabled &&
      contextEntityId &&
      (connectionStatus === "disconnected" || connectionStatus === "error");

    if (!shouldPoll) {
      setIsHttpPollingActive(false);
      return;
    }

    setIsHttpPollingActive(true);

    const pollAgentTrace = async () => {
      try {
        const response = await authenticatedFetch(
          `/api/v1/sessions/${contextEntityId}/agent-execution-trace`,
        );

        if (!response.ok) {
          console.debug(
            "[DevTools WS] HTTP fallback fetch failed:",
            response.statusText,
          );
          return;
        }

        const data = await response.json();
        if (data.traces && Array.isArray(data.traces)) {
          // Transform API response to TraceStepPayload format
          const newSteps: TraceStepPayload[] = data.traces.map(
            (trace: {
              trace_id: string;
              node_name: string;
              status: string;
              start_time: number;
              end_time?: number;
              duration_ms?: number;
              session_id?: string;
            }) => ({
              id: trace.trace_id,
              name: trace.node_name,
              status: trace.status as TraceStepPayload["status"],
              startTime: trace.start_time,
              endTime: trace.end_time,
              duration: trace.duration_ms,
              session_id: trace.session_id ?? contextEntityId,
            }),
          );

          // Only update if we have new data
          if (newSteps.length > 0) {
            setTraceSteps((prev) => {
              // Fix: Merge by ID instead of filter to allow status updates
              // (e.g., running → completed transitions)
              const stepMap = new Map(prev.map((s) => [s.id, s]));
              for (const step of newSteps) {
                // Update existing or add new
                stepMap.set(step.id, step);
              }
              return Array.from(stepMap.values());
            });
          }
        }
      } catch (error) {
        console.debug("[DevTools WS] HTTP fallback error:", error);
      }
    };

    // Initial fetch
    pollAgentTrace();

    // Set up polling interval
    const intervalId = setInterval(pollAgentTrace, httpPollingInterval);

    return () => {
      clearInterval(intervalId);
      setIsHttpPollingActive(false);
    };
  }, [
    enableHttpFallback,
    enabled,
    contextEntityId,
    connectionStatus,
    httpPollingInterval,
  ]);

  /**
   * Clear console entries.
   */
  const clearConsoleEntries = useCallback(() => {
    setConsoleEntries([]);
  }, []);

  /**
   * Clear network entries.
   */
  const clearNetworkEntries = useCallback(() => {
    setNetworkEntries([]);
  }, []);

  /**
   * Clear trace steps.
   */
  const clearTraceSteps = useCallback(() => {
    setTraceSteps([]);
  }, []);

  return {
    status: connectionStatus,
    consoleEntries,
    networkEntries,
    traceSteps,
    clearConsoleEntries,
    clearNetworkEntries,
    clearTraceSteps,
    reconnect: wsReconnect,
    reconnectAttempts,
    isHttpPollingActive, // Fix 4: Expose HTTP polling status
  };
}

export default useDevToolsWebSocket;
