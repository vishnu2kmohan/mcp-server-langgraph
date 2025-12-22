/**
 * useAgentRequestWebSocket Hook
 *
 * Custom hook for real-time HITL agent request notifications via WebSocket.
 *
 * Features:
 * - Connect to agent request WebSocket endpoint
 * - Handle approval_required messages
 * - Handle clarification_required messages
 * - Handle approval_updated messages
 * - Handle execution_resumed messages
 * - Ping/pong keepalive
 * - Connection status tracking
 * - Automatic reconnection
 *
 * Reference: Plan - Confidence-Based Human-in-the-Loop (HITL) for Multi-Agent Orchestrator
 */

import { useEffect, useCallback, useMemo, useRef, useState } from "react";
import { useAppSelector } from "../store/hooks";
import { selectIsAuthenticated } from "../store/slices/authSlice";
import { getAuthToken } from "../utils/storage";

// =============================================================================
// Types
// =============================================================================

export type ConnectionStatus = "connecting" | "connected" | "disconnected" | "error";

export interface ApprovalRequiredPayload {
  request_id: string;
  session_id: string;
  task_id: string;
  agent_name: string;
  confidence: number;
  threshold: number;
  proposed_action: string;
  trigger_reason: string;
  context: Record<string, unknown>;
  requested_at: string;
}

export interface ClarificationRequiredPayload {
  request_id: string;
  session_id: string;
  task_id: string;
  agent_name: string;
  clarification_type: "text" | "choice" | "confirmation";
  question: string;
  options: Array<{
    id: string;
    label: string;
    description?: string;
    is_recommended?: boolean;
  }>;
  placeholder: string | null;
  required: boolean;
  context: Record<string, unknown>;
  requested_at: string;
}

export interface ApprovalUpdatedPayload {
  request_id: string;
  status: "approved" | "rejected";
  decided_by: string;
  decided_at: string;
  reason: string | null;
}

export interface ExecutionResumedPayload {
  request_id: string;
  task_id: string;
  agent_name: string;
  status: "approved" | "rejected";
  resumed_at: string;
}

export type AgentRequestMessage =
  | { type: "approval_required"; payload: ApprovalRequiredPayload }
  | { type: "clarification_required"; payload: ClarificationRequiredPayload }
  | { type: "approval_updated"; payload: ApprovalUpdatedPayload }
  | { type: "execution_resumed"; payload: ExecutionResumedPayload }
  | { type: "pong" }
  | { type: "error"; payload: { message: string } };

export interface UseAgentRequestWebSocketOptions {
  /** Custom WebSocket URL */
  url?: string;
  /** Whether to enable the connection (default: true) */
  enabled?: boolean;
  /** Ping interval in ms (default: 30000) */
  pingInterval?: number;
  /** Session ID to filter messages */
  sessionId?: string;
  /** Callback for approval_required messages */
  onApprovalRequired?: (payload: ApprovalRequiredPayload) => void;
  /** Callback for clarification_required messages */
  onClarificationRequired?: (payload: ClarificationRequiredPayload) => void;
  /** Callback for approval_updated messages */
  onApprovalUpdated?: (payload: ApprovalUpdatedPayload) => void;
  /** Callback for execution_resumed messages */
  onExecutionResumed?: (payload: ExecutionResumedPayload) => void;
}

export interface UseAgentRequestWebSocketReturn {
  /** Current connection status */
  status: ConnectionStatus;
  /** Pending approval requests */
  pendingApprovals: ApprovalRequiredPayload[];
  /** Pending clarification requests */
  pendingClarifications: ClarificationRequiredPayload[];
  /** Manually disconnect */
  disconnect: () => void;
  /** Manually reconnect */
  reconnect: () => void;
}

// =============================================================================
// Message Parsing
// =============================================================================

function isApprovalRequiredPayload(data: unknown): data is ApprovalRequiredPayload {
  if (typeof data !== "object" || data === null) return false;
  const p = data as Record<string, unknown>;
  return (
    typeof p.request_id === "string" &&
    typeof p.session_id === "string" &&
    typeof p.agent_name === "string" &&
    typeof p.confidence === "number" &&
    typeof p.threshold === "number"
  );
}

function isClarificationRequiredPayload(data: unknown): data is ClarificationRequiredPayload {
  if (typeof data !== "object" || data === null) return false;
  const p = data as Record<string, unknown>;
  return (
    typeof p.request_id === "string" &&
    typeof p.session_id === "string" &&
    typeof p.agent_name === "string" &&
    typeof p.clarification_type === "string" &&
    typeof p.question === "string"
  );
}

function isApprovalUpdatedPayload(data: unknown): data is ApprovalUpdatedPayload {
  if (typeof data !== "object" || data === null) return false;
  const p = data as Record<string, unknown>;
  return (
    typeof p.request_id === "string" &&
    typeof p.status === "string" &&
    typeof p.decided_by === "string"
  );
}

function isExecutionResumedPayload(data: unknown): data is ExecutionResumedPayload {
  if (typeof data !== "object" || data === null) return false;
  const p = data as Record<string, unknown>;
  return (
    typeof p.request_id === "string" &&
    typeof p.task_id === "string" &&
    typeof p.agent_name === "string" &&
    typeof p.status === "string"
  );
}

export function parseAgentRequestMessage(data: unknown): AgentRequestMessage | null {
  if (typeof data !== "object" || data === null) return null;
  const msg = data as Record<string, unknown>;

  if (msg.type === "approval_required" && isApprovalRequiredPayload(msg.payload)) {
    return { type: "approval_required", payload: msg.payload };
  }
  if (msg.type === "clarification_required" && isClarificationRequiredPayload(msg.payload)) {
    return { type: "clarification_required", payload: msg.payload };
  }
  if (msg.type === "approval_updated" && isApprovalUpdatedPayload(msg.payload)) {
    return { type: "approval_updated", payload: msg.payload };
  }
  if (msg.type === "execution_resumed" && isExecutionResumedPayload(msg.payload)) {
    return { type: "execution_resumed", payload: msg.payload };
  }
  if (msg.type === "pong") {
    return { type: "pong" };
  }
  if (msg.type === "error" && typeof msg.payload === "object" && msg.payload !== null) {
    return { type: "error", payload: msg.payload as { message: string } };
  }

  return null;
}

// =============================================================================
// URL Construction
// =============================================================================

function getDefaultWebSocketUrl(sessionId?: string): string {
  if (typeof window === "undefined") {
    return "ws://localhost:8000/api/v1/ws/agents/requests";
  }

  const protocol = window.location.protocol === "https:" ? "wss:" : "ws:";
  const host = window.location.host;

  // Build query params
  const params = new URLSearchParams();

  const token = getAuthToken();
  if (token) {
    params.set("token", token);
  }
  if (sessionId) {
    params.set("session_id", sessionId);
  }

  const queryString = params.toString();
  return `${protocol}//${host}/api/v1/ws/agents/requests${queryString ? `?${queryString}` : ""}`;
}

// =============================================================================
// Hook Implementation
// =============================================================================

export function useAgentRequestWebSocket(
  options: UseAgentRequestWebSocketOptions = {}
): UseAgentRequestWebSocketReturn {
  const {
    url,
    enabled = true,
    pingInterval = 30000,
    sessionId,
    onApprovalRequired,
    onClarificationRequired,
    onApprovalUpdated,
    onExecutionResumed,
  } = options;

  const isAuthenticated = useAppSelector(selectIsAuthenticated);
  const [status, setStatus] = useState<ConnectionStatus>("disconnected");
  const [pendingApprovals, setPendingApprovals] = useState<ApprovalRequiredPayload[]>([]);
  const [pendingClarifications, setPendingClarifications] = useState<ClarificationRequiredPayload[]>([]);

  const wsRef = useRef<WebSocket | null>(null);
  const pingIntervalRef = useRef<ReturnType<typeof setInterval> | null>(null);
  const reconnectTimeoutRef = useRef<ReturnType<typeof setTimeout> | null>(null);
  const isReconnectRef = useRef(false);
  const manualCloseRef = useRef(false);
  const sessionIdRef = useRef(sessionId);
  sessionIdRef.current = sessionId;

  // Store callbacks in refs to avoid reconnecting on callback change
  const callbacksRef = useRef({
    onApprovalRequired,
    onClarificationRequired,
    onApprovalUpdated,
    onExecutionResumed,
  });
  callbacksRef.current = {
    onApprovalRequired,
    onClarificationRequired,
    onApprovalUpdated,
    onExecutionResumed,
  };

  // Compute WebSocket URL - recalculate when auth state changes
  // This ensures the token query param is included when user becomes authenticated
  // eslint-disable-next-line react-hooks/exhaustive-deps -- isAuthenticated triggers recalculation
  const wsUrl = useMemo(() => url ?? getDefaultWebSocketUrl(sessionId), [url, sessionId, isAuthenticated]);

  // Track effective enabled state - only connect when authenticated
  // WebSocket requires valid auth token, so we only connect when authenticated
  const effectiveEnabled = enabled && isAuthenticated;

  // Track previous effective enabled state to detect changes
  // Initialize to undefined to detect first render
  const prevEnabledRef = useRef<boolean | undefined>(undefined);

  // Handle incoming messages
  const handleMessage = useCallback((event: MessageEvent) => {
    try {
      const data = JSON.parse(event.data);
      const message = parseAgentRequestMessage(data);

      if (!message) {
        return;
      }

      switch (message.type) {
        case "approval_required":
          setPendingApprovals((prev) => [...prev, message.payload]);
          callbacksRef.current.onApprovalRequired?.(message.payload);
          break;

        case "clarification_required":
          setPendingClarifications((prev) => [...prev, message.payload]);
          callbacksRef.current.onClarificationRequired?.(message.payload);
          break;

        case "approval_updated":
          // Remove from pending
          setPendingApprovals((prev) =>
            prev.filter((a) => a.request_id !== message.payload.request_id)
          );
          callbacksRef.current.onApprovalUpdated?.(message.payload);
          break;

        case "execution_resumed":
          callbacksRef.current.onExecutionResumed?.(message.payload);
          break;

        case "pong":
          // Keepalive response - no action needed
          break;

        case "error":
          console.error("[AgentRequestWS] Error:", message.payload.message);
          break;
      }
    } catch (err) {
      console.error("[AgentRequestWS] Failed to parse message:", err);
    }
  }, []);

  // Start ping interval
  const startPingInterval = useCallback(() => {
    if (pingIntervalRef.current) {
      clearInterval(pingIntervalRef.current);
    }

    pingIntervalRef.current = setInterval(() => {
      if (wsRef.current?.readyState === WebSocket.OPEN) {
        wsRef.current.send(JSON.stringify({ type: "ping" }));
      }
    }, pingInterval);
  }, [pingInterval]);

  // Stop ping interval
  const stopPingInterval = useCallback(() => {
    if (pingIntervalRef.current) {
      clearInterval(pingIntervalRef.current);
      pingIntervalRef.current = null;
    }
  }, []);

  // Connect to WebSocket
  const connect = useCallback(() => {
    if (wsRef.current?.readyState === WebSocket.OPEN) {
      return;
    }

    // Clean up existing connection without triggering onclose
    if (wsRef.current) {
      wsRef.current.onclose = null;
      wsRef.current.close();
    }

    manualCloseRef.current = false;
    setStatus("connecting");

    try {
      const ws = new WebSocket(wsUrl);

      ws.onopen = () => {
        setStatus("connected");
        startPingInterval();

        // Send subscribe message if sessionId is provided
        if (sessionIdRef.current) {
          ws.send(JSON.stringify({ type: "subscribe", session_id: sessionIdRef.current }));
        }

        // On reconnect, request pending items to sync state
        if (isReconnectRef.current) {
          ws.send(JSON.stringify({ type: "get_pending" }));
        }
      };

      ws.onclose = () => {
        // Only set status if not a manual/cleanup close
        if (!manualCloseRef.current) {
          setStatus("disconnected");
        }
        stopPingInterval();
      };

      ws.onerror = () => {
        setStatus("error");
        stopPingInterval();
      };

      ws.onmessage = handleMessage;

      wsRef.current = ws;
    } catch (err) {
      console.error("[AgentRequestWS] Failed to connect:", err);
      setStatus("error");
    }
  }, [wsUrl, handleMessage, startPingInterval, stopPingInterval]);

  // Disconnect from WebSocket
  const disconnect = useCallback(() => {
    manualCloseRef.current = true;

    if (reconnectTimeoutRef.current) {
      clearTimeout(reconnectTimeoutRef.current);
      reconnectTimeoutRef.current = null;
    }

    stopPingInterval();

    if (wsRef.current) {
      wsRef.current.close();
      wsRef.current = null;
    }

    // Status will be set by onclose handler (but blocked by manualCloseRef)
    // For explicit disconnect calls, we still want to show disconnected status
    setStatus("disconnected");
  }, [stopPingInterval]);

  // Reconnect to WebSocket
  const reconnect = useCallback(() => {
    disconnect();
    // Mark as reconnection to trigger get_pending on connect
    isReconnectRef.current = true;
    // Small delay before reconnecting
    reconnectTimeoutRef.current = setTimeout(() => {
      connect();
    }, 100);
  }, [disconnect, connect]);

  // Connect on mount, disconnect on unmount
  // Handle auth state transitions to reconnect when user authenticates
  useEffect(() => {
    const isFirstRender = prevEnabledRef.current === undefined;
    const wasEnabled = prevEnabledRef.current === true;
    const isNowEnabled = effectiveEnabled;

    if (!isNowEnabled) {
      // Currently disabled - disconnect if we were previously enabled
      if (wasEnabled) {
        manualCloseRef.current = true;
        if (reconnectTimeoutRef.current) {
          clearTimeout(reconnectTimeoutRef.current);
          reconnectTimeoutRef.current = null;
        }
        stopPingInterval();
        if (wsRef.current) {
          wsRef.current.close();
          wsRef.current = null;
        }
        setStatus("disconnected");
      }
    } else if (isFirstRender || (!wasEnabled && isNowEnabled)) {
      // First render with enabled=true, OR transitioning from disabled to enabled
      connect();
    }

    prevEnabledRef.current = effectiveEnabled;

    // Cleanup on unmount - close WebSocket without triggering status updates
    return () => {
      manualCloseRef.current = true;
      if (reconnectTimeoutRef.current) {
        clearTimeout(reconnectTimeoutRef.current);
        reconnectTimeoutRef.current = null;
      }
      stopPingInterval();
      if (wsRef.current) {
        // Set onclose to null before closing to prevent any state updates during unmount
        wsRef.current.onclose = null;
        wsRef.current.close();
        wsRef.current = null;
      }
    };
  }, [effectiveEnabled, connect, stopPingInterval]);

  return {
    status,
    pendingApprovals,
    pendingClarifications,
    disconnect,
    reconnect,
  };
}
