/**
 * useCostTrackingWebSocket Hook
 *
 * WebSocket hook for real-time cost tracking during LLM operations.
 * Replaces polling-based cost queries with efficient push-based updates.
 *
 * Based on backend endpoint: /api/v1/ws/usage/cost
 */

import { useState, useCallback, useRef, useMemo, useEffect } from "react";
import { useRealtimeSync } from "./useRealtimeSync";
import { useAppDispatch, useAppSelector } from "../store/hooks";
import { logout, selectIsAuthenticated } from "../store/slices/authSlice";
import { addNotification } from "../store/slices/notificationSlice";
import { getAuthToken } from "../utils/storage";
import { buildWebSocketUrl, WS_ENDPOINTS } from "../utils/websocket";
import { reportWebSocketMetrics } from "../utils/websocketTelemetry";
import { PROTOCOL_VERSION_MISMATCH_NOTIFICATION } from "../utils/websocketAuth";

// =============================================================================
// Types
// =============================================================================

/**
 * Session cost information
 */
export interface SessionCost {
  session_id: string;
  total_cost: number;
  token_count: number;
  model?: string;
  provider?: string;
}

/**
 * Individual cost event from an LLM operation
 */
export interface CostEvent {
  session_id: string;
  cost: number;
  model: string;
  tokens: {
    input: number;
    output: number;
  };
  timestamp?: string;
  operation?: string;
}

/**
 * User budget information
 */
export interface UserBudget {
  user_id: string;
  budget_limit: number;
  current_usage: number;
  remaining: number;
  period?: string;
}

/**
 * Budget warning alert
 */
export interface BudgetWarning {
  user_id: string;
  threshold: number;
  current_usage: number;
  budget_limit?: number;
  message: string;
  timestamp?: string;
}

/**
 * WebSocket message types from server
 */
interface SessionTotalMessage {
  type: "session_total";
  payload: SessionCost;
}

interface CostEventMessage {
  type: "cost_event";
  payload: CostEvent;
}

interface UserBudgetMessage {
  type: "user_budget";
  payload: UserBudget;
}

interface BudgetWarningMessage {
  type: "budget_warning";
  payload: BudgetWarning;
}

interface UnsubscribedMessage {
  type: "unsubscribed";
  payload: {
    session_id?: string;
    user_id?: string;
  };
}

interface ErrorMessage {
  type: "error";
  payload: {
    code: string;
    message: string;
  };
}

type ServerMessage =
  | SessionTotalMessage
  | CostEventMessage
  | UserBudgetMessage
  | BudgetWarningMessage
  | UnsubscribedMessage
  | ErrorMessage;

/**
 * Options for useCostTrackingWebSocket hook
 */
export interface UseCostTrackingWebSocketOptions {
  /** Custom WebSocket URL (defaults to /api/v1/ws/usage/cost) */
  url?: string;
  /** Callback when cost event is received */
  onCostEvent?: (event: CostEvent) => void;
  /** Callback when budget warning is received */
  onBudgetWarning?: (warning: BudgetWarning) => void;
  /** Callback when session total is updated */
  onSessionTotal?: (session: SessionCost) => void;
  /** Callback when user budget is updated */
  onUserBudget?: (budget: UserBudget) => void;
  /** Callback when an error occurs */
  onError?: (error: string) => void;
}

/**
 * Return type for useCostTrackingWebSocket hook
 */
export interface UseCostTrackingWebSocketReturn {
  /** Current WebSocket connection status */
  status:
    | "connecting"
    | "connected"
    | "disconnected"
    | "reconnecting"
    | "error";
  /** Session costs by session ID */
  sessionCosts: Record<string, SessionCost>;
  /** Current user budget info */
  userBudget: UserBudget | null;
  /** Set of subscribed session IDs */
  subscribedSessions: Set<string>;
  /** Set of subscribed user IDs */
  subscribedUsers: Set<string>;
  /** Recent budget warnings */
  budgetWarnings: BudgetWarning[];
  /** Current error message, if any */
  error: string | null;
  /** Subscribe to session cost updates */
  subscribeSession: (sessionId: string) => void;
  /** Unsubscribe from session cost updates */
  unsubscribeSession: (sessionId: string) => void;
  /** Subscribe to user budget updates */
  subscribeUser: (userId: string) => void;
  /** Unsubscribe from user budget updates */
  unsubscribeUser: (userId: string) => void;
  /** Get cost for a specific session */
  getSessionCost: (sessionId: string) => SessionCost | undefined;
  /** Clear all budget warnings */
  clearBudgetWarnings: () => void;
  /** Manually disconnect from WebSocket */
  disconnect: () => void;
  /** Manually reconnect to WebSocket */
  reconnect: () => void;
}

// =============================================================================
// Hook Implementation
// =============================================================================

export function useCostTrackingWebSocket(
  options: UseCostTrackingWebSocketOptions = {},
): UseCostTrackingWebSocketReturn {
  const {
    url: customUrl,
    onCostEvent,
    onBudgetWarning,
    onSessionTotal,
    onUserBudget,
    onError,
  } = options;

  // Redux dispatch for token expiration handling
  const dispatch = useAppDispatch();

  // Get auth state and token for WebSocket authentication
  const isAuthenticated = useAppSelector(selectIsAuthenticated);
  // Track token changes to trigger URL regeneration on refresh
  const authToken = isAuthenticated ? (getAuthToken() ?? undefined) : undefined;

  // Compute WebSocket URL - only generate URL when authenticated
  // Passing empty string prevents connection attempt before auth is ready
  const url = useMemo(
    () =>
      isAuthenticated
        ? (customUrl ?? buildWebSocketUrl(WS_ENDPOINTS.COST, {}, true))
        : "",
    // authToken dependency ensures URL regenerates when token is refreshed
    // eslint-disable-next-line react-hooks/exhaustive-deps
    [customUrl, authToken, isAuthenticated],
  );

  // State
  const [sessionCosts, setSessionCosts] = useState<Record<string, SessionCost>>(
    {},
  );
  const [userBudget, setUserBudget] = useState<UserBudget | null>(null);
  const [subscribedSessions, setSubscribedSessions] = useState<Set<string>>(
    new Set(),
  );
  const [subscribedUsers, setSubscribedUsers] = useState<Set<string>>(
    new Set(),
  );
  const [budgetWarnings, setBudgetWarnings] = useState<BudgetWarning[]>([]);
  const [error, setError] = useState<string | null>(null);

  // Refs for callbacks to avoid stale closures
  const callbacksRef = useRef({
    onCostEvent,
    onBudgetWarning,
    onSessionTotal,
    onUserBudget,
    onError,
  });
  callbacksRef.current = {
    onCostEvent,
    onBudgetWarning,
    onSessionTotal,
    onUserBudget,
    onError,
  };

  // Handle incoming messages
  const handleMessage = useCallback((data: unknown) => {
    const message = data as ServerMessage;

    switch (message.type) {
      case "session_total":
        setSessionCosts((prev) => ({
          ...prev,
          [message.payload.session_id]: message.payload,
        }));
        callbacksRef.current.onSessionTotal?.(message.payload);
        break;

      case "cost_event":
        // Update session cost if available
        setSessionCosts((prev) => {
          const existing = prev[message.payload.session_id];
          if (existing) {
            return {
              ...prev,
              [message.payload.session_id]: {
                ...existing,
                total_cost: existing.total_cost + message.payload.cost,
                token_count:
                  existing.token_count +
                  message.payload.tokens.input +
                  message.payload.tokens.output,
              },
            };
          }
          return prev;
        });
        callbacksRef.current.onCostEvent?.(message.payload);
        break;

      case "user_budget":
        setUserBudget(message.payload);
        callbacksRef.current.onUserBudget?.(message.payload);
        break;

      case "budget_warning":
        setBudgetWarnings((prev) => [...prev, message.payload]);
        callbacksRef.current.onBudgetWarning?.(message.payload);
        break;

      case "unsubscribed":
        if (message.payload.session_id) {
          setSubscribedSessions((prev) => {
            const next = new Set(prev);
            next.delete(message.payload.session_id!);
            return next;
          });
        }
        if (message.payload.user_id) {
          setSubscribedUsers((prev) => {
            const next = new Set(prev);
            next.delete(message.payload.user_id!);
            return next;
          });
        }
        break;

      case "error":
        setError(message.payload.message);
        callbacksRef.current.onError?.(message.payload.message);
        break;
    }
  }, []);

  // Handle connection established
  const handleConnect = useCallback(() => {
    setError(null);
  }, []);

  // Use the realtime sync hook for WebSocket management
  const { status, send, disconnect, reconnect, metrics } = useRealtimeSync({
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
    },
  });

  // Report WebSocket metrics for observability
  useEffect(() => {
    if (isAuthenticated && metrics.totalAttempts > 0) {
      reportWebSocketMetrics("cost_tracking", metrics);
    }
  }, [isAuthenticated, metrics]);

  // Commands
  const subscribeSession = useCallback(
    (sessionId: string) => {
      setSubscribedSessions((prev) => new Set(prev).add(sessionId));
      send({ type: "subscribe_session", session_id: sessionId });
    },
    [send],
  );

  const unsubscribeSession = useCallback(
    (sessionId: string) => {
      setSubscribedSessions((prev) => {
        const next = new Set(prev);
        next.delete(sessionId);
        return next;
      });
      send({ type: "unsubscribe", session_id: sessionId });
    },
    [send],
  );

  const subscribeUser = useCallback(
    (userId: string) => {
      setSubscribedUsers((prev) => new Set(prev).add(userId));
      send({ type: "subscribe_user", user_id: userId });
    },
    [send],
  );

  const unsubscribeUser = useCallback(
    (userId: string) => {
      setSubscribedUsers((prev) => {
        const next = new Set(prev);
        next.delete(userId);
        return next;
      });
      send({ type: "unsubscribe", user_id: userId });
    },
    [send],
  );

  const getSessionCost = useCallback(
    (sessionId: string): SessionCost | undefined => {
      return sessionCosts[sessionId];
    },
    [sessionCosts],
  );

  const clearBudgetWarnings = useCallback(() => {
    setBudgetWarnings([]);
  }, []);

  return {
    status,
    sessionCosts,
    userBudget,
    subscribedSessions,
    subscribedUsers,
    budgetWarnings,
    error,
    subscribeSession,
    unsubscribeSession,
    subscribeUser,
    unsubscribeUser,
    getSessionCost,
    clearBudgetWarnings,
    disconnect,
    reconnect,
  };
}

export default useCostTrackingWebSocket;
