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
import { useAppDispatch, useAppSelector } from "../store/hooks";
import { logout, selectIsAuthenticated } from "../store/slices/authSlice";
import { addNotification } from "../store/slices/notificationSlice";
import { buildWebSocketUrl, WS_ENDPOINTS } from "../utils/websocket";
import { PROTOCOL_VERSION_MISMATCH_NOTIFICATION } from "../utils/websocketAuth";
import { devLogger } from "../utils/devLogger";
import { useRealtimeSync, type ConnectionStatus } from "./useRealtimeSync";
import { reportWebSocketMetrics } from "../utils/websocketTelemetry";
import type {
  ApprovalRequiredPayload,
  ClarificationRequiredPayload,
} from "../types/hitl";

// Create prefixed logger for this hook
const logger = devLogger.withPrefix("[AgentRequestWS]");

// =============================================================================
// Types
// =============================================================================

// Re-export from canonical location for backwards compatibility
export type {
  ApprovalRequiredPayload,
  ClarificationRequiredPayload,
} from "../types/hitl";

// Re-export ConnectionStatus from useRealtimeSync for backwards compatibility
export type { ConnectionStatus } from "./useRealtimeSync";

// Note: ApprovalUpdatedPayload and ExecutionResumedPayload are WebSocket-specific
// and not in the canonical hitl.ts types (they represent server-to-client events)
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

function isApprovalRequiredPayload(
  data: unknown,
): data is ApprovalRequiredPayload {
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

function isClarificationRequiredPayload(
  data: unknown,
): data is ClarificationRequiredPayload {
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

function isApprovalUpdatedPayload(
  data: unknown,
): data is ApprovalUpdatedPayload {
  if (typeof data !== "object" || data === null) return false;
  const p = data as Record<string, unknown>;
  return (
    typeof p.request_id === "string" &&
    typeof p.status === "string" &&
    typeof p.decided_by === "string"
  );
}

function isExecutionResumedPayload(
  data: unknown,
): data is ExecutionResumedPayload {
  if (typeof data !== "object" || data === null) return false;
  const p = data as Record<string, unknown>;
  return (
    typeof p.request_id === "string" &&
    typeof p.task_id === "string" &&
    typeof p.agent_name === "string" &&
    typeof p.status === "string"
  );
}

export function parseAgentRequestMessage(
  data: unknown,
): AgentRequestMessage | null {
  if (typeof data !== "object" || data === null) return null;
  const msg = data as Record<string, unknown>;

  if (
    msg.type === "approval_required" &&
    isApprovalRequiredPayload(msg.payload)
  ) {
    return { type: "approval_required", payload: msg.payload };
  }
  if (
    msg.type === "clarification_required" &&
    isClarificationRequiredPayload(msg.payload)
  ) {
    return { type: "clarification_required", payload: msg.payload };
  }
  if (
    msg.type === "approval_updated" &&
    isApprovalUpdatedPayload(msg.payload)
  ) {
    return { type: "approval_updated", payload: msg.payload };
  }
  if (
    msg.type === "execution_resumed" &&
    isExecutionResumedPayload(msg.payload)
  ) {
    return { type: "execution_resumed", payload: msg.payload };
  }
  if (msg.type === "pong") {
    return { type: "pong" };
  }
  if (
    msg.type === "error" &&
    typeof msg.payload === "object" &&
    msg.payload !== null
  ) {
    return { type: "error", payload: msg.payload as { message: string } };
  }

  return null;
}

// =============================================================================
// URL Construction
// =============================================================================

/**
 * Get the default WebSocket URL for agent requests
 *
 * Uses standardized WebSocket utilities from src/utils/websocket.ts
 */
function getDefaultWebSocketUrl(
  sessionId?: string,
  includeAuthToken: boolean = false,
): string {
  // Build query params
  const params: Record<string, string> = {};
  if (sessionId) {
    params.session_id = sessionId;
  }

  // Use standardized WebSocket URL builder
  return buildWebSocketUrl(
    WS_ENDPOINTS.AGENTS_REQUESTS,
    params,
    includeAuthToken,
  );
}

// =============================================================================
// Hook Implementation
// =============================================================================

export function useAgentRequestWebSocket(
  options: UseAgentRequestWebSocketOptions = {},
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

  // Redux dispatch for token expiration handling
  const dispatch = useAppDispatch();

  const isAuthenticated = useAppSelector(selectIsAuthenticated);
  const [pendingApprovals, setPendingApprovals] = useState<
    ApprovalRequiredPayload[]
  >([]);
  const [pendingClarifications, setPendingClarifications] = useState<
    ClarificationRequiredPayload[]
  >([]);

  // Refs for session tracking and ping interval
  const sessionIdRef = useRef(sessionId);
  sessionIdRef.current = sessionId;
  const pingIntervalRef = useRef<ReturnType<typeof setInterval> | null>(null);
  const sendRef = useRef<(data: unknown) => void>(() => {});

  // Store callbacks in refs to avoid stale closures
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

  // Compute WebSocket URL - recalculates when auth state changes
  // The buildWebSocketUrl utility fetches the auth token internally when includeAuthToken=true
  // Pass empty string when not authenticated to prevent connection attempt
  const wsUrl = useMemo(
    () =>
      isAuthenticated
        ? (url ??
          getDefaultWebSocketUrl(sessionId, true /* includeAuthToken */))
        : "",
    [url, sessionId, isAuthenticated],
  );

  // Track effective enabled state - only connect when authenticated
  // WebSocket requires valid auth token, so we only connect when authenticated
  const effectiveEnabled = enabled && isAuthenticated;

  // Handle incoming messages (receives parsed data from useRealtimeSync)
  const handleMessage = useCallback((data: unknown) => {
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
          prev.filter((a) => a.request_id !== message.payload.request_id),
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
        logger.error("Error:", message.payload.message);
        break;
    }
  }, []);

  // Handle connection established - send subscribe message and start ping
  const handleConnect = useCallback(() => {
    // Send subscribe message if sessionId is provided
    if (sessionIdRef.current) {
      sendRef.current({
        type: "subscribe",
        session_id: sessionIdRef.current,
      });
    }

    // Request pending items to sync state on connect/reconnect
    sendRef.current({ type: "get_pending" });

    // Start ping interval for keepalive
    if (pingIntervalRef.current) {
      clearInterval(pingIntervalRef.current);
    }
    pingIntervalRef.current = setInterval(() => {
      sendRef.current({ type: "ping" });
    }, pingInterval);
  }, [pingInterval]);

  // Handle disconnection - clean up ping interval
  const handleDisconnect = useCallback(() => {
    if (pingIntervalRef.current) {
      clearInterval(pingIntervalRef.current);
      pingIntervalRef.current = null;
    }
  }, []);

  // Use the underlying realtimeSync hook with exponential backoff
  const {
    status: realtimeStatus,
    send,
    disconnect: realtimeDisconnect,
    reconnect: realtimeReconnect,
    metrics,
  } = useRealtimeSync({
    url: wsUrl,
    onMessage: handleMessage,
    onConnect: handleConnect,
    onDisconnect: handleDisconnect,
    exponentialBackoff: true,
    reconnectInterval: 1000,
    maxDelayMs: 30000,
    maxReconnectAttempts: 10,
    onTokenExpired: () => dispatch(logout()),
    onProtocolVersionMismatch: () => {
      dispatch(addNotification(PROTOCOL_VERSION_MISMATCH_NOTIFICATION));
    },
  });

  // Keep sendRef in sync for use in handleConnect
  sendRef.current = send;

  // Report WebSocket metrics for observability
  useEffect(() => {
    if (effectiveEnabled && metrics.totalAttempts > 0) {
      reportWebSocketMetrics("agent_requests", metrics);
    }
  }, [effectiveEnabled, metrics]);

  // Determine effective status - override to disconnected if not enabled
  const status: ConnectionStatus = effectiveEnabled
    ? realtimeStatus
    : "disconnected";

  // Track previous effective enabled state to detect changes
  const prevEnabledRef = useRef(effectiveEnabled);

  // Handle enable/disable state transitions
  useEffect(() => {
    const wasDisabled = !prevEnabledRef.current;
    const isNowEnabled = effectiveEnabled;

    if (!effectiveEnabled) {
      // Currently disabled - disconnect
      realtimeDisconnect();
    } else if (wasDisabled && isNowEnabled) {
      // Transitioning from disabled to enabled - reconnect
      realtimeReconnect();
    }

    prevEnabledRef.current = effectiveEnabled;
  }, [effectiveEnabled, realtimeDisconnect, realtimeReconnect]);

  // Clean up ping interval on unmount
  useEffect(() => {
    return () => {
      if (pingIntervalRef.current) {
        clearInterval(pingIntervalRef.current);
        pingIntervalRef.current = null;
      }
    };
  }, []);

  return {
    status,
    pendingApprovals,
    pendingClarifications,
    disconnect: realtimeDisconnect,
    reconnect: realtimeReconnect,
  };
}
