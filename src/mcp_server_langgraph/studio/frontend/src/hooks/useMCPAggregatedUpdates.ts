/**
 * useMCPAggregatedUpdates Hook
 *
 * Custom hook for listening to MCP capability change notifications via WebSocket.
 * Used to trigger real-time updates when connected MCP servers modify their
 * available tools, resources, or prompts.
 *
 * Features:
 * - Listens to notifications/tools/list_changed
 * - Listens to notifications/resources/list_changed
 * - Listens to notifications/prompts/list_changed
 * - Provides callbacks for each type of change
 * - Tracks last update timestamps
 */

import { useState, useCallback, useRef, useMemo, useEffect } from "react";
import { useRealtimeSync, type ConnectionStatus } from "./useRealtimeSync";
import { useAppSelector } from "../store/hooks";
import { selectIsAuthenticated } from "../store/slices/authSlice";
import { getAuthToken } from "../utils/storage";
import { buildWebSocketUrl, API_ENDPOINTS } from "../config/api";

// ============================================================================
// Types
// ============================================================================

/**
 * MCP Notification for list_changed events
 */
interface MCPListChangedNotification {
  jsonrpc: "2.0";
  method: string;
  params?: {
    serverName?: string;
    [key: string]: unknown;
  };
}

/**
 * Options for useMCPAggregatedUpdates hook
 */
export interface UseMCPAggregatedUpdatesOptions {
  /** Custom WebSocket URL (default: constructs from window.location) */
  url?: string;
  /** Whether to enable the connection (default: true) */
  enabled?: boolean;
  /** Callback when tools list changes */
  onToolsChanged?: (serverName: string) => void;
  /** Callback when resources list changes */
  onResourcesChanged?: (serverName: string) => void;
  /** Callback when prompts list changes */
  onPromptsChanged?: (serverName: string) => void;
}

/**
 * Return type for useMCPAggregatedUpdates hook
 */
export interface UseMCPAggregatedUpdatesReturn {
  /** Current connection status */
  status: ConnectionStatus;
  /** Timestamp of last tools update notification */
  lastToolsUpdate: Date | null;
  /** Timestamp of last resources update notification */
  lastResourcesUpdate: Date | null;
  /** Timestamp of last prompts update notification */
  lastPromptsUpdate: Date | null;
  /** Disconnect from WebSocket */
  disconnect: () => void;
  /** Reconnect to WebSocket */
  reconnect: () => void;
}

// ============================================================================
// Helper Functions
// ============================================================================

/**
 * Get default MCP aggregated updates WebSocket URL
 *
 * Uses centralized config from src/config/api.ts
 */
function getDefaultWebSocketUrl(token?: string): string {
  return buildWebSocketUrl(API_ENDPOINTS.WS_MCP_AGGREGATED, window, token);
}

/**
 * Check if a message is an MCP list_changed notification
 */
function isMCPListChangedNotification(
  data: unknown,
): data is MCPListChangedNotification {
  if (typeof data !== "object" || data === null) return false;
  const msg = data as Record<string, unknown>;
  return (
    msg.jsonrpc === "2.0" &&
    typeof msg.method === "string" &&
    msg.method.startsWith("notifications/") &&
    msg.method.endsWith("/list_changed")
  );
}

// ============================================================================
// Hook Implementation
// ============================================================================

/**
 * Hook for listening to MCP capability change notifications
 *
 * @example
 * ```tsx
 * function CapabilitiesPanel() {
 *   const { refetch } = useListAggregatedToolsQuery();
 *
 *   const { status } = useMCPAggregatedUpdates({
 *     onToolsChanged: (serverName) => {
 *       console.log(`Tools changed on ${serverName}`);
 *       refetch();
 *     },
 *   });
 *
 *   return <span>Updates: {status}</span>;
 * }
 * ```
 */
export function useMCPAggregatedUpdates(
  options: UseMCPAggregatedUpdatesOptions = {},
): UseMCPAggregatedUpdatesReturn {
  const {
    url,
    enabled = true,
    onToolsChanged,
    onResourcesChanged,
    onPromptsChanged,
  } = options;

  const isAuthenticated = useAppSelector(selectIsAuthenticated);

  // State
  const [lastToolsUpdate, setLastToolsUpdate] = useState<Date | null>(null);
  const [lastResourcesUpdate, setLastResourcesUpdate] = useState<Date | null>(
    null,
  );
  const [lastPromptsUpdate, setLastPromptsUpdate] = useState<Date | null>(null);

  // Refs for callbacks to avoid re-creating handleMessage
  const callbacksRef = useRef({
    onToolsChanged,
    onResourcesChanged,
    onPromptsChanged,
  });

  // Keep callbacks ref updated
  useEffect(() => {
    callbacksRef.current = {
      onToolsChanged,
      onResourcesChanged,
      onPromptsChanged,
    };
  }, [onToolsChanged, onResourcesChanged, onPromptsChanged]);

  // Get auth token
  const authToken = isAuthenticated ? (getAuthToken() ?? undefined) : undefined;

  // Compute WebSocket URL
  const wsUrl = useMemo(
    () => url ?? getDefaultWebSocketUrl(authToken),
    [url, authToken],
  );

  // Track effective enabled state
  const effectiveEnabled = enabled && isAuthenticated;

  // Handle incoming messages
  const handleMessage = useCallback((data: unknown) => {
    if (isMCPListChangedNotification(data)) {
      const serverName = data.params?.serverName ?? "unknown";
      const now = new Date();

      if (data.method === "notifications/tools/list_changed") {
        setLastToolsUpdate(now);
        callbacksRef.current.onToolsChanged?.(serverName);
      } else if (data.method === "notifications/resources/list_changed") {
        setLastResourcesUpdate(now);
        callbacksRef.current.onResourcesChanged?.(serverName);
      } else if (data.method === "notifications/prompts/list_changed") {
        setLastPromptsUpdate(now);
        callbacksRef.current.onPromptsChanged?.(serverName);
      }
    }
  }, []);

  // Use the underlying realtimeSync hook
  const {
    status: realtimeStatus,
    disconnect,
    reconnect,
  } = useRealtimeSync({
    url: wsUrl,
    exponentialBackoff: true,
    reconnectInterval: 1000,
    maxDelayMs: 30000,
    maxReconnectAttempts: 10,
    onMessage: handleMessage,
  });

  // Override status if not enabled
  const status: ConnectionStatus = effectiveEnabled
    ? realtimeStatus
    : "disconnected";

  // Disconnect when disabled
  const prevEnabledRef = useRef(effectiveEnabled);
  useEffect(() => {
    if (!effectiveEnabled && prevEnabledRef.current) {
      disconnect();
    } else if (effectiveEnabled && !prevEnabledRef.current) {
      reconnect();
    }
    prevEnabledRef.current = effectiveEnabled;
  }, [effectiveEnabled, disconnect, reconnect]);

  return {
    status,
    lastToolsUpdate,
    lastResourcesUpdate,
    lastPromptsUpdate,
    disconnect,
    reconnect,
  };
}

export default useMCPAggregatedUpdates;
