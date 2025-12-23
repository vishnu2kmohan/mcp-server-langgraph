/**
 * useDevToolsWebSocket Hook
 *
 * WebSocket integration for DevTools console and network tabs.
 * Receives real-time log and network entries from the backend.
 */
import { useState, useCallback, useEffect, useRef } from "react";

import type { ConsoleEntry, NetworkEntry } from "../types";

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

// =============================================================================
// Message Types
// =============================================================================

interface ConsoleMessage {
  type: "console";
  payload: Omit<ConsoleEntry, "id"> & { id?: string };
}

interface NetworkMessage {
  type: "network";
  payload: Omit<NetworkEntry, "id"> & { id?: string };
}

interface NetworkUpdateMessage {
  type: "network_update";
  payload: {
    id: string;
    status?: NetworkEntry["status"];
    statusCode?: number;
    duration?: number;
    responseSize?: number;
    responseBody?: unknown;
    endTime?: number;
  };
}

type _DevToolsMessage = ConsoleMessage | NetworkMessage | NetworkUpdateMessage;

// =============================================================================
// Helper Functions
// =============================================================================

function isConsoleMessage(data: unknown): data is ConsoleMessage {
  if (typeof data !== "object" || data === null) return false;
  const msg = data as Record<string, unknown>;
  return msg.type === "console" && typeof msg.payload === "object";
}

function isNetworkMessage(data: unknown): data is NetworkMessage {
  if (typeof data !== "object" || data === null) return false;
  const msg = data as Record<string, unknown>;
  return msg.type === "network" && typeof msg.payload === "object";
}

function isNetworkUpdateMessage(data: unknown): data is NetworkUpdateMessage {
  if (typeof data !== "object" || data === null) return false;
  const msg = data as Record<string, unknown>;
  return msg.type === "network_update" && typeof msg.payload === "object";
}

function getDefaultWebSocketUrl(): string {
  if (typeof window === "undefined") {
    return "ws://localhost:8000/api/v1/ws/devtools";
  }

  const protocol = window.location.protocol === "https:" ? "wss:" : "ws:";
  const host = window.location.host;

  return `${protocol}//${host}/api/v1/ws/devtools`;
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
   */
  const handleMessage = useCallback(
    (event: MessageEvent) => {
      try {
        const data: unknown = JSON.parse(event.data);

        if (isConsoleMessage(data)) {
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
        } else if (isNetworkMessage(data)) {
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
        } else if (isNetworkUpdateMessage(data)) {
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

    const wsUrl = url ?? getDefaultWebSocketUrl();

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
  }, [enabled, url, handleMessage]);

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
