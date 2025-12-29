/**
 * useDevToolsWebSocket Hook
 *
 * WebSocket integration for DevTools console and network tabs.
 * Receives real-time log and network entries from the backend.
 *
 * Uses centralized WebSocket URL construction from @/utils/websocket
 * to ensure consistent URL building and authentication handling.
 *
 * Uses typed protocols from @/types/websocket-protocols for type-safe
 * message handling and validation.
 */
import { useState, useCallback, useEffect, useRef } from "react";

import { buildWebSocketUrl, WS_ENDPOINTS } from "../../../utils/websocket";
import type { ConsoleEntry, NetworkEntry } from "../types";

// Import typed protocols for type-safe WebSocket message handling
import {
  isConsoleLogEntry,
  isNetworkRequestEntry,
  isNetworkUpdateEntry,
} from "../../../types/websocket-protocols";
import type {
  ConsoleLogEntry,
  NetworkRequestEntry,
  NetworkUpdateEntry,
  DevToolsMessage,
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
}

export interface UseDevToolsWebSocketReturn {
  /** Current connection status */
  status: DevToolsWebSocketStatus;
  /** Console entries received from WebSocket */
  consoleEntries: ConsoleEntry[];
  /** Network entries received from WebSocket */
  networkEntries: NetworkEntry[];
  /** Clear all console entries */
  clearConsoleEntries: () => void;
  /** Clear all network entries */
  clearNetworkEntries: () => void;
  /** Manually reconnect */
  reconnect: () => void;
}

// =============================================================================
// Constants
// =============================================================================

const DEFAULT_MAX_CONSOLE_ENTRIES = 1000;
const DEFAULT_MAX_NETWORK_ENTRIES = 500;

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
  } = options;

  const [status, setStatus] = useState<DevToolsWebSocketStatus>("disconnected");
  const [consoleEntries, setConsoleEntries] = useState<ConsoleEntry[]>([]);
  const [networkEntries, setNetworkEntries] = useState<NetworkEntry[]>([]);

  const wsRef = useRef<WebSocket | null>(null);
  const contextEntityIdRef = useRef(contextEntityId);
  contextEntityIdRef.current = contextEntityId;

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

      // Include if no session/workflow (global) or matches context
      if (!sessionId && !workflowId) return true;
      return sessionId === ctxId || workflowId === ctxId;
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
    (event: MessageEvent) => {
      try {
        const data: unknown = JSON.parse(event.data);

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
        }
      } catch {
        // Ignore parse errors
      }
    },
    [maxConsoleEntries, maxNetworkEntries, shouldIncludeEntry],
  );

  /**
   * Connect to WebSocket.
   */
  const connect = useCallback(() => {
    if (!enabled) return;

    const wsUrl = url ?? getDefaultWebSocketUrl(contextEntityId);

    try {
      setStatus("connecting");
      const ws = new WebSocket(wsUrl);
      wsRef.current = ws;

      ws.onopen = () => {
        setStatus("connected");
      };

      ws.onmessage = handleMessage;

      ws.onerror = () => {
        setStatus("error");
      };

      ws.onclose = () => {
        setStatus("disconnected");
        wsRef.current = null;
      };
    } catch {
      setStatus("error");
    }
  }, [enabled, url, contextEntityId, handleMessage]);

  /**
   * Disconnect from WebSocket.
   */
  const disconnect = useCallback(() => {
    if (wsRef.current) {
      wsRef.current.close();
      wsRef.current = null;
    }
  }, []);

  /**
   * Reconnect to WebSocket.
   */
  const reconnect = useCallback(() => {
    disconnect();
    connect();
  }, [disconnect, connect]);

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

  // Connect on mount, disconnect on unmount
  useEffect(() => {
    if (enabled) {
      connect();
    }

    return () => {
      disconnect();
    };
  }, [enabled, connect, disconnect]);

  return {
    status,
    consoleEntries,
    networkEntries,
    clearConsoleEntries,
    clearNetworkEntries,
    reconnect,
  };
}

export default useDevToolsWebSocket;
