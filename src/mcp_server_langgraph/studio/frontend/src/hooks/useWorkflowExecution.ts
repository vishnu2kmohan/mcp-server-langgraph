/**
 * useWorkflowExecution Hook
 *
 * Integrates useRealtimeSync WebSocket with Redux for real-time workflow execution.
 * Handles:
 * - WebSocket connection to workflow execution endpoint
 * - Dispatching Redux actions for state/node status/log updates
 * - Execution control (start, stop)
 */

import { useCallback, useMemo, useEffect } from "react";
import { useDispatch, useSelector } from "react-redux";
import { useRealtimeSync } from "./useRealtimeSync";
import { logout } from "../store/slices/authSlice";
import { addNotification } from "../store/slices/notificationSlice";
import {
  setExecutionState,
  updateNodeStatus,
  addExecutionLog,
} from "../store/slices/workflowSlice";
import type { RootState } from "../store";
import type { NodeStatus } from "../types/workflow";
import {
  PROTOCOL_VERSION_MISMATCH_NOTIFICATION,
  showProtocolVersionMismatchToast,
} from "../utils/websocketAuth";
import { reportWebSocketMetrics } from "../utils/websocketTelemetry";
import { buildWebSocketUrlWithPath, WS_ENDPOINTS } from "../utils/websocket";

// WebSocket message types
interface ExecutionStartedMessage {
  type: "execution_started";
  workflowId: string;
}

interface ExecutionCompletedMessage {
  type: "execution_completed";
  workflowId: string;
  result?: unknown;
}

interface ExecutionErrorMessage {
  type: "execution_error";
  workflowId: string;
  error: string;
}

interface NodeStartedMessage {
  type: "node_started";
  nodeId: string;
}

interface NodeCompletedMessage {
  type: "node_completed";
  nodeId: string;
}

interface NodeErrorMessage {
  type: "node_error";
  nodeId: string;
  error: string;
}

interface LogMessage {
  type: "log";
  level: "info" | "warning" | "error" | "debug";
  message: string;
  nodeId?: string;
}

type WorkflowExecutionMessage =
  | ExecutionStartedMessage
  | ExecutionCompletedMessage
  | ExecutionErrorMessage
  | NodeStartedMessage
  | NodeCompletedMessage
  | NodeErrorMessage
  | LogMessage;

export interface UseWorkflowExecutionOptions {
  autoConnect?: boolean;
}

export interface UseWorkflowExecutionReturn {
  connectionStatus: string;
  reconnectAttempts: number;
  isExecuting: boolean;
  startExecution: (input?: Record<string, unknown>) => void;
  stopExecution: () => void;
  disconnect: () => void;
  reconnect: () => void;
}

/**
 * Hook for managing real-time workflow execution via WebSocket
 */
export function useWorkflowExecution(
  workflowId: string,
  options: UseWorkflowExecutionOptions = {},
): UseWorkflowExecutionReturn {
  const { autoConnect = true } = options;
  const dispatch = useDispatch();

  // Get execution state from Redux
  const executionState = useSelector(
    (state: RootState) => state.workflow.executionState,
  );

  // Construct WebSocket URL using standardized utilities (ADR-0068 compliant)
  // Uses the consolidated WebSocket endpoint: /api/v1/ws/workflows/{workflow_id}
  const wsUrl = useMemo(() => {
    if (!autoConnect || !workflowId) return "";
    return buildWebSocketUrlWithPath(
      WS_ENDPOINTS.WORKFLOW_EXECUTION,
      { workflowId },
      {},
      true, // Include auth token for authenticated endpoint
    );
  }, [workflowId, autoConnect]);

  // Handle incoming WebSocket messages
  const handleMessage = useCallback(
    (data: unknown) => {
      const message = data as WorkflowExecutionMessage;

      switch (message.type) {
        case "execution_started":
          dispatch(setExecutionState("running"));
          break;

        case "execution_completed":
          dispatch(setExecutionState("completed"));
          break;

        case "execution_error":
          dispatch(setExecutionState("error"));
          dispatch(
            addExecutionLog({
              level: "error",
              message: message.error,
            }),
          );
          break;

        case "node_started":
          dispatch(
            updateNodeStatus({
              nodeId: message.nodeId,
              status: "running" as NodeStatus,
            }),
          );
          break;

        case "node_completed":
          dispatch(
            updateNodeStatus({
              nodeId: message.nodeId,
              status: "success" as NodeStatus,
            }),
          );
          break;

        case "node_error":
          dispatch(
            updateNodeStatus({
              nodeId: message.nodeId,
              status: "error" as NodeStatus,
            }),
          );
          break;

        case "log": {
          // Map 'debug' to 'info' since ExecutionLog only supports info/warning/error
          const logLevel = message.level === "debug" ? "info" : message.level;
          dispatch(
            addExecutionLog({
              level: logLevel,
              message: message.message,
              nodeId: message.nodeId,
            }),
          );
          break;
        }
      }
    },
    [dispatch],
  );

  // Handle connection events
  const handleConnect = useCallback(() => {
    dispatch(
      addExecutionLog({
        level: "info",
        message: "Connected to workflow execution",
      }),
    );
  }, [dispatch]);

  const handleDisconnect = useCallback(() => {
    dispatch(
      addExecutionLog({
        level: "warning",
        message: "Disconnected from workflow execution",
      }),
    );
  }, [dispatch]);

  const handleError = useCallback(
    (error: Error) => {
      dispatch(
        addExecutionLog({
          level: "error",
          message: `WebSocket error: ${error.message}`,
        }),
      );
    },
    [dispatch],
  );

  // Use the realtime sync hook
  const { status, reconnectAttempts, send, disconnect, reconnect, metrics } =
    useRealtimeSync({
      url: wsUrl,
      onMessage: handleMessage,
      onConnect: handleConnect,
      onDisconnect: handleDisconnect,
      onError: handleError,
      onTokenExpired: () => dispatch(logout()),
      onProtocolVersionMismatch: () => {
        dispatch(addNotification(PROTOCOL_VERSION_MISMATCH_NOTIFICATION));
        showProtocolVersionMismatchToast();
      },
    });

  // Report WebSocket metrics for observability
  useEffect(() => {
    if (autoConnect && workflowId && metrics.totalAttempts > 0) {
      reportWebSocketMetrics("workflow_execution", metrics);
    }
  }, [autoConnect, workflowId, metrics]);

  // Start execution
  const startExecution = useCallback(
    (input?: Record<string, unknown>) => {
      const message: {
        type: string;
        workflowId: string;
        input?: Record<string, unknown>;
      } = {
        type: "start",
        workflowId,
      };
      if (input) {
        message.input = input;
      }
      send(message);
    },
    [send, workflowId],
  );

  // Stop execution
  const stopExecution = useCallback(() => {
    send({
      type: "stop",
      workflowId,
    });
  }, [send, workflowId]);

  // Derived state
  const isExecuting = executionState === "running";

  return {
    connectionStatus: status,
    reconnectAttempts,
    isExecuting,
    startExecution,
    stopExecution,
    disconnect,
    reconnect,
  };
}
