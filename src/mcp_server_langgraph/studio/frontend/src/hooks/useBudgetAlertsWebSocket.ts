/**
 * useBudgetAlertsWebSocket Hook
 *
 * Custom hook for real-time budget alert notifications via WebSocket.
 * Connects to /api/v1/ws/budget/alerts endpoint for cost monitoring.
 *
 * Features:
 * - Subscribe to specific entity budget alerts (org/project/team/user)
 * - Subscribe to all budget alerts (admin mode)
 * - Real-time budget status changes (warning, critical, exceeded)
 * - Automatic reconnection with exponential backoff
 * - Token expiration handling
 *
 * Uses typed protocols from @/types/websocket-protocols for type-safe
 * message handling and validation.
 */

import { useState, useCallback, useRef, useMemo, useEffect } from "react";
import { useRealtimeSync, type ConnectionStatus } from "./useRealtimeSync";
import { useAppDispatch, useAppSelector } from "../store/hooks";
import {
  logout,
  selectIsAuthenticated,
  selectWebSocketPermissions,
} from "../store/slices/authSlice";
import { addNotification } from "../store/slices/notificationSlice";
import { buildWebSocketUrl, WS_ENDPOINTS } from "../utils/websocket";
import { reportWebSocketMetrics } from "../utils/websocketTelemetry";
import {
  PROTOCOL_VERSION_MISMATCH_NOTIFICATION,
  showProtocolVersionMismatchToast,
} from "../utils/websocketAuth";

// Import typed protocols for type-safe WebSocket message handling
import { isBudgetAlertEntry } from "../types/websocket-protocols";
import type {
  BudgetAlertEntry,
  BudgetAlertStatus as ProtocolBudgetAlertStatus,
  BudgetAlertsMessage,
  WebSocketError,
} from "../types/websocket-protocols";

// ============================================================================
// Types
// ============================================================================

/**
 * Budget alert status levels (re-exported from typed protocols)
 */
export type BudgetAlertStatus = ProtocolBudgetAlertStatus;

/**
 * Budget alert notification (frontend-friendly format)
 */
export interface BudgetAlert {
  entityType: string;
  entityId: string;
  status: BudgetAlertStatus;
  percentUsed: number;
  currentSpend: string;
  remaining: string;
  monthlyLimitUsd: string;
  message: string;
}

// Re-export protocol types for consumers
export type { BudgetAlertEntry, BudgetAlertsMessage, WebSocketError };

/**
 * Options for useBudgetAlertsWebSocket hook
 */
export interface UseBudgetAlertsWebSocketOptions {
  /** Custom WebSocket URL (default: constructs from window.location) */
  url?: string;
  /** Whether to enable the connection (default: true) */
  enabled?: boolean;
  /** Entity IDs to subscribe to (if not using subscribeAll) */
  entityIds?: string[];
  /** Subscribe to all budget alerts (admin mode) */
  subscribeAll?: boolean;
  /** Callback when a budget alert is received */
  onAlert?: (alert: BudgetAlert) => void;
  /** Callback when subscription is confirmed */
  onSubscribed?: (entityIds: string[], subscribeAll: boolean) => void;
}

/**
 * Return type for useBudgetAlertsWebSocket hook
 */
export interface UseBudgetAlertsWebSocketReturn {
  /** Current connection status */
  status: ConnectionStatus;
  /** List of received budget alerts */
  alerts: BudgetAlert[];
  /** Whether currently subscribed */
  isSubscribed: boolean;
  /** Subscribed entity IDs */
  subscribedEntityIds: string[];
  /** Whether subscribed to all alerts */
  isSubscribedToAll: boolean;
  /** Subscribe to specific entities */
  subscribeToEntities: (entityIds: string[]) => void;
  /** Subscribe to all alerts */
  subscribeToAll: () => void;
  /** Unsubscribe from all alerts */
  unsubscribe: () => void;
  /** Clear alerts history */
  clearAlerts: () => void;
  /** Disconnect from WebSocket */
  disconnect: () => void;
  /** Reconnect to WebSocket */
  reconnect: () => void;
}

// ============================================================================
// Helper Functions
// ============================================================================

/**
 * Get default budget alerts WebSocket URL
 */
function getDefaultWebSocketUrl(includeToken: boolean = true): string {
  return buildWebSocketUrl(WS_ENDPOINTS.BUDGET_ALERTS, {}, includeToken);
}

/**
 * Parse budget alert from backend payload
 */
function parseBudgetAlert(payload: Record<string, unknown>): BudgetAlert {
  return {
    entityType: (payload.entity_type as string) || "",
    entityId: (payload.entity_id as string) || "",
    status: (payload.status as BudgetAlertStatus) || "ok",
    percentUsed: (payload.percent_used as number) || 0,
    currentSpend: (payload.current_spend as string) || "0",
    remaining: (payload.remaining as string) || "0",
    monthlyLimitUsd: (payload.monthly_limit_usd as string) || "0",
    message: (payload.message as string) || "",
  };
}

/**
 * Check if message is a subscription confirmation
 * (Not in centralized protocols since it's specific to budget alerts flow)
 */
function isSubscriptionMessage(
  data: unknown,
): data is { type: string; payload?: Record<string, unknown> } {
  if (typeof data !== "object" || data === null) return false;
  const msg = data as { type?: string };
  return msg.type === "subscribed" || msg.type === "unsubscribed";
}

// ============================================================================
// Hook Implementation
// ============================================================================

/**
 * Hook for real-time budget alert notifications
 *
 * @example
 * ```tsx
 * function BudgetMonitor() {
 *   const { alerts, subscribeToAll, status } = useBudgetAlertsWebSocket({
 *     onAlert: (alert) => {
 *       if (alert.status === "exceeded") {
 *         showWarning(`Budget exceeded for ${alert.entityId}`);
 *       }
 *     },
 *   });
 *
 *   useEffect(() => {
 *     subscribeToAll();
 *   }, [subscribeToAll]);
 *
 *   return <BudgetAlertList alerts={alerts} status={status} />;
 * }
 * ```
 */
export function useBudgetAlertsWebSocket(
  options: UseBudgetAlertsWebSocketOptions = {},
): UseBudgetAlertsWebSocketReturn {
  const {
    url,
    enabled = true,
    entityIds,
    subscribeAll: initialSubscribeAll = false,
    onAlert,
    onSubscribed,
  } = options;

  // Redux dispatch for token expiration handling
  const dispatch = useAppDispatch();
  const isAuthenticated = useAppSelector(selectIsAuthenticated);
  const wsPermissions = useAppSelector(selectWebSocketPermissions);

  // Check if user has permission for budget alerts WebSocket
  const hasBudgetAlertsPermission = wsPermissions?.budget_alerts ?? false;

  // State
  const [alerts, setAlerts] = useState<BudgetAlert[]>([]);
  const [isSubscribed, setIsSubscribed] = useState(false);
  const [subscribedEntityIds, setSubscribedEntityIds] = useState<string[]>([]);
  const [isSubscribedToAll, setIsSubscribedToAll] = useState(false);

  // Refs for callbacks
  const callbacksRef = useRef({ onAlert, onSubscribed });

  // Keep callbacks ref updated
  useEffect(() => {
    callbacksRef.current = { onAlert, onSubscribed };
  }, [onAlert, onSubscribed]);

  // Compute WebSocket URL - only generate URL when authenticated AND has permission
  const wsUrl = useMemo(
    () =>
      isAuthenticated && hasBudgetAlertsPermission
        ? (url ?? getDefaultWebSocketUrl(true))
        : "",
    [url, isAuthenticated, hasBudgetAlertsPermission],
  );

  // Track effective enabled state - requires auth and permission
  const effectiveEnabled =
    enabled && isAuthenticated && hasBudgetAlertsPermission;

  // Handle incoming messages using centralized type guards
  const handleMessage = useCallback((data: unknown) => {
    // Use centralized type guard for budget alerts
    if (isBudgetAlertEntry(data)) {
      const alert = parseBudgetAlert(
        (data.payload || {}) as unknown as Record<string, unknown>,
      );
      setAlerts((prev) => [...prev, alert]);
      callbacksRef.current.onAlert?.(alert);
    } else if (isSubscriptionMessage(data)) {
      const msg = data as { type: string; payload?: Record<string, unknown> };
      if (msg.type === "subscribed") {
        const payload = msg.payload || {};
        const entityIds = (payload.entity_ids as string[]) || [];
        const subscribeAll = (payload.subscribe_all as boolean) || false;
        setIsSubscribed(true);
        setSubscribedEntityIds(entityIds);
        setIsSubscribedToAll(subscribeAll);
        callbacksRef.current.onSubscribed?.(entityIds, subscribeAll);
      } else if (msg.type === "unsubscribed") {
        setIsSubscribed(false);
        setSubscribedEntityIds([]);
        setIsSubscribedToAll(false);
      }
    }
  }, []);

  // Use the underlying realtimeSync hook
  const {
    status: realtimeStatus,
    send,
    disconnect,
    reconnect,
    metrics,
  } = useRealtimeSync({
    url: effectiveEnabled ? wsUrl : "",
    exponentialBackoff: true,
    reconnectInterval: 1000,
    maxDelayMs: 30000,
    maxReconnectAttempts: 10,
    onMessage: handleMessage,
    onTokenExpired: () => dispatch(logout()),
    onProtocolVersionMismatch: () => {
      dispatch(addNotification(PROTOCOL_VERSION_MISMATCH_NOTIFICATION));
      showProtocolVersionMismatchToast();
    },
    onConnect: () => {
      // Auto-subscribe based on options
      if (initialSubscribeAll) {
        send({ type: "subscribe_all", id: crypto.randomUUID(), payload: {} });
      } else if (entityIds && entityIds.length > 0) {
        send({
          type: "subscribe_entities",
          id: crypto.randomUUID(),
          payload: { entity_ids: entityIds },
        });
      }
    },
  });

  // Report WebSocket metrics for observability
  useEffect(() => {
    if (effectiveEnabled && metrics.totalAttempts > 0) {
      reportWebSocketMetrics("budget_alerts", metrics);
    }
  }, [effectiveEnabled, metrics]);

  // Override status if not enabled
  const status: ConnectionStatus = effectiveEnabled
    ? realtimeStatus
    : "disconnected";

  // Subscribe to specific entities
  const subscribeToEntities = useCallback(
    (ids: string[]) => {
      send({
        type: "subscribe_entities",
        id: crypto.randomUUID(),
        payload: { entity_ids: ids },
      });
    },
    [send],
  );

  // Subscribe to all alerts
  const subscribeToAll = useCallback(() => {
    send({
      type: "subscribe_all",
      id: crypto.randomUUID(),
      payload: {},
    });
  }, [send]);

  // Unsubscribe from all alerts
  const unsubscribe = useCallback(() => {
    send({
      type: "unsubscribe",
      id: crypto.randomUUID(),
      payload: {},
    });
  }, [send]);

  // Clear alerts history
  const clearAlerts = useCallback(() => {
    setAlerts([]);
  }, []);

  return {
    status,
    alerts,
    isSubscribed,
    subscribedEntityIds,
    isSubscribedToAll,
    subscribeToEntities,
    subscribeToAll,
    unsubscribe,
    clearAlerts,
    disconnect,
    reconnect,
  };
}

export default useBudgetAlertsWebSocket;
