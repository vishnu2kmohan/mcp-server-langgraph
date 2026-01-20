/**
 * useAIOrchestratorStatus Hook
 *
 * Custom hook for real-time AI orchestrator status updates.
 * Provides the agentStatus for StatusBar context-aware display.
 *
 * Features:
 * - Real-time orchestrator status updates via WebSocket
 * - Track active and completed tasks
 * - Provide statusForStatusBar for StatusBar integration
 * - Support for multiple concurrent tasks
 * - Automatic reconnection with exponential backoff
 *
 * Task Categories (from StudioOrchestrator):
 * - UX: Persona, disclosure, error, nudges
 * - SESSION: Summarize, group, similarity
 * - CONVERSATION: Intent, context, goal
 * - CANVAS: Artifact, code, diff
 * - DIAGRAM: Analyze, to-code
 * - TRACE: Summarize, anomaly
 * - HITL: Risk assess, decision history
 * - COMMAND: Command palette, inline suggestions
 */

import { useState, useCallback, useRef, useMemo, useEffect } from "react";
import {
  useRealtimeSync,
  type WebSocketConnectionStatus,
} from "./useRealtimeSync";
import { useAppDispatch, useAppSelector } from "../store/hooks";
import {
  logout,
  selectIsAuthenticated,
  selectWebSocketPermissions,
} from "../store/slices/authSlice";
import { addNotification } from "../store/slices/notificationSlice";
import { buildWebSocketUrl, WS_ENDPOINTS } from "../utils/websocket";
import {
  PROTOCOL_VERSION_MISMATCH_NOTIFICATION,
  showProtocolVersionMismatchToast,
} from "../utils/websocketAuth";
import { reportWebSocketMetrics } from "../utils/websocketTelemetry";

// ============================================================================
// Types
// ============================================================================

/** Task categories matching StudioOrchestrator's TaskCategory enum */
export type TaskCategory =
  | "ux"
  | "session"
  | "conversation"
  | "canvas"
  | "diagram"
  | "trace"
  | "hitl"
  | "command"
  | "alert";

/** Orchestrator status values */
export type OrchestratorStatus = "idle" | "processing" | "error";

/** Task information */
export interface TaskInfo {
  taskId: string;
  taskType: string;
  category: TaskCategory;
  startedAt: Date;
  completedAt?: Date;
  success?: boolean;
  error?: string;
  /** Progress percentage (0-100) for long-running tasks */
  progress?: number;
}

/** Status change event payload */
export interface StatusChangeEvent {
  status: OrchestratorStatus;
  message?: string;
  taskType?: string;
  category?: TaskCategory;
}

/** Options for useAIOrchestratorStatus hook */
export interface UseAIOrchestratorStatusOptions {
  /** Whether to enable the connection (default: true) */
  enabled?: boolean;
  /** Callback when status changes */
  onStatusChange?: (event: StatusChangeEvent) => void;
  /** Callback when a task completes */
  onTaskComplete?: (task: TaskInfo) => void;
  /** Callback when a task fails */
  onTaskFail?: (task: TaskInfo) => void;
}

/** Return type for useAIOrchestratorStatus hook */
export interface UseAIOrchestratorStatusReturn {
  /** Current orchestrator status */
  status: OrchestratorStatus;
  /** Current status message (for display) */
  statusMessage?: string;
  /** Current task being processed (most recent) */
  currentTask: TaskInfo | null;
  /** All currently active tasks */
  activeTasks: TaskInfo[];
  /** History of completed/failed tasks */
  taskHistory: TaskInfo[];
  /** Last error message */
  lastError?: string;
  /** WebSocket connection status */
  connectionStatus: WebSocketConnectionStatus;
  /** Status message formatted for StatusBar (undefined when idle) */
  statusForStatusBar?: string;
  /** Number of tasks waiting in queue */
  queueDepth: number;
  /** Map of task ID to progress percentage (0-100) */
  taskProgress: Record<string, number>;
  /** Disconnect from WebSocket */
  disconnect: () => void;
  /** Reconnect to WebSocket */
  reconnect: () => void;
}

// ============================================================================
// Constants
// ============================================================================

const MAX_HISTORY_SIZE = 50;

/** Map task types to human-readable status messages */
const TASK_TYPE_MESSAGES: Record<string, string> = {
  // UX
  persona_analysis: "Analyzing persona...",
  disclosure_analysis: "Checking disclosures...",
  error_analysis: "Analyzing error...",
  nudge_recommendation: "Generating nudges...",
  onboarding_personalization: "Personalizing onboarding...",
  empty_state_suggestions: "Generating suggestions...",
  metrics_insights: "Analyzing metrics...",
  nav_prediction: "Predicting navigation...",
  contextual_help: "Finding help...",
  learning_path: "Building learning path...",
  // Session
  session_summarize: "Summarizing session...",
  session_group: "Grouping sessions...",
  session_similarity: "Finding similar sessions...",
  // Conversation
  intent_detect: "Detecting intent...",
  context_optimize: "Optimizing context...",
  goal_track: "Tracking goals...",
  // Canvas
  artifact_suggest_type: "Suggesting artifact type...",
  code_analyze: "Analyzing code...",
  diff_explain: "Explaining diff...",
  // Diagram
  diagram_analyze: "Analyzing diagram...",
  diagram_to_code: "Generating code...",
  // Trace
  trace_summarize: "Summarizing trace...",
  trace_anomaly: "Detecting anomalies...",
  // HITL
  risk_assess: "Assessing risk...",
  decision_history: "Reviewing decisions...",
  uncertainty_analysis: "Analyzing uncertainty...",
  risk_analysis: "Analyzing risk...",
  alternatives_analysis: "Finding alternatives...",
  evidence_extraction: "Extracting evidence...",
  // Command
  command_interpret: "Interpreting command...",
  inline_suggest: "Generating suggestions...",
  ai_edit_generate: "Generating edit...",
  // Cost
  cost_project: "Projecting costs...",
  token_predict: "Predicting tokens...",
};

// ============================================================================
// Helper Functions
// ============================================================================

function getDefaultWebSocketUrl(includeToken: boolean = true): string {
  // Use dedicated orchestrator status endpoint
  return buildWebSocketUrl(WS_ENDPOINTS.ORCHESTRATOR_STATUS, {}, includeToken);
}

function getTaskMessage(taskType: string): string {
  return TASK_TYPE_MESSAGES[taskType] || "Processing...";
}

// ============================================================================
// Hook Implementation
// ============================================================================

export function useAIOrchestratorStatus(
  options: UseAIOrchestratorStatusOptions = {},
): UseAIOrchestratorStatusReturn {
  const {
    enabled = true,
    onStatusChange,
    onTaskComplete,
    onTaskFail,
  } = options;

  // Redux dispatch for token expiration handling
  const dispatch = useAppDispatch();
  const isAuthenticated = useAppSelector(selectIsAuthenticated);
  const wsPermissions = useAppSelector(selectWebSocketPermissions);

  // Security: Fail-closed when permissions are null (OpenFGA unavailable)
  const hasPermission = wsPermissions?.orchestrator_status ?? false;

  // State
  const [status, setStatus] = useState<OrchestratorStatus>("idle");
  const [statusMessage, setStatusMessage] = useState<string | undefined>();
  const [activeTasks, setActiveTasks] = useState<TaskInfo[]>([]);
  const [taskHistory, setTaskHistory] = useState<TaskInfo[]>([]);
  const [lastError, setLastError] = useState<string | undefined>();
  const [queueDepth, setQueueDepth] = useState<number>(0);
  const [taskProgress, setTaskProgress] = useState<Record<string, number>>({});

  // Refs for callbacks
  const callbacksRef = useRef({ onStatusChange, onTaskComplete, onTaskFail });

  // Keep refs updated
  useEffect(() => {
    callbacksRef.current = { onStatusChange, onTaskComplete, onTaskFail };
  }, [onStatusChange, onTaskComplete, onTaskFail]);

  // Compute WebSocket URL
  const wsUrl = useMemo(
    () => getDefaultWebSocketUrl(isAuthenticated),
    [isAuthenticated],
  );

  // Track effective enabled state - requires both authentication AND authorization
  const effectiveEnabled = enabled && isAuthenticated && hasPermission;

  // Handle incoming messages
  const handleMessage = useCallback((data: unknown) => {
    if (!data || typeof data !== "object") return;

    const message = data as Record<string, unknown>;
    const type = message.type as string;
    const payload = (message.payload || {}) as Record<string, unknown>;

    switch (type) {
      case "orchestrator_status": {
        const newStatus = (payload.status as OrchestratorStatus) || "idle";
        const newMessage = payload.message as string | undefined;
        const taskType = payload.task_type as string | undefined;
        const category = payload.category as TaskCategory | undefined;

        setStatus(newStatus);
        setStatusMessage(newMessage);

        if (newStatus === "error") {
          setLastError(newMessage);
        } else if (newStatus === "idle") {
          setLastError(undefined);
        }

        callbacksRef.current.onStatusChange?.({
          status: newStatus,
          message: newMessage,
          taskType,
          category,
        });
        break;
      }

      case "task_started": {
        const taskInfo: TaskInfo = {
          taskId: payload.task_id as string,
          taskType: payload.task_type as string,
          category: payload.category as TaskCategory,
          startedAt: new Date(payload.started_at as string),
        };

        setActiveTasks((prev) => [...prev, taskInfo]);
        setStatus("processing");
        setStatusMessage(getTaskMessage(taskInfo.taskType));
        setLastError(undefined);

        callbacksRef.current.onStatusChange?.({
          status: "processing",
          message: getTaskMessage(taskInfo.taskType),
          taskType: taskInfo.taskType,
          category: taskInfo.category,
        });
        break;
      }

      case "task_completed": {
        const taskId = payload.task_id as string;
        const completedAt = new Date(payload.completed_at as string);

        setActiveTasks((prev) => {
          const task = prev.find((t) => t.taskId === taskId);
          if (task) {
            const completedTask: TaskInfo = {
              ...task,
              completedAt,
              success: true,
            };
            setTaskHistory((hist) => [
              completedTask,
              ...hist.slice(0, MAX_HISTORY_SIZE - 1),
            ]);
            callbacksRef.current.onTaskComplete?.(completedTask);
          }
          const remaining = prev.filter((t) => t.taskId !== taskId);

          // Update status based on remaining tasks
          if (remaining.length === 0) {
            setStatus("idle");
            setStatusMessage(undefined);
          }

          return remaining;
        });

        // Clear progress for completed task
        setTaskProgress((prev) => {
          const { [taskId]: _removed, ...rest } = prev;
          return rest;
        });
        break;
      }

      case "task_failed": {
        const taskId = payload.task_id as string;
        const failedAt = new Date(payload.failed_at as string);
        const error = payload.error as string | undefined;

        setActiveTasks((prev) => {
          const task = prev.find((t) => t.taskId === taskId);
          if (task) {
            const failedTask: TaskInfo = {
              ...task,
              completedAt: failedAt,
              success: false,
              error,
            };
            setTaskHistory((hist) => [
              failedTask,
              ...hist.slice(0, MAX_HISTORY_SIZE - 1),
            ]);
            callbacksRef.current.onTaskFail?.(failedTask);
          }
          return prev.filter((t) => t.taskId !== taskId);
        });

        // Clear progress for failed task
        setTaskProgress((prev) => {
          const { [taskId]: _removed, ...rest } = prev;
          return rest;
        });

        setStatus("error");
        setLastError(error);
        break;
      }

      case "task_progress": {
        const taskId = payload.task_id as string;
        const progress = payload.progress as number;
        const progressMessage = payload.message as string | undefined;

        // Update task progress map
        setTaskProgress((prev) => ({
          ...prev,
          [taskId]: progress,
        }));

        // Update the task in activeTasks with progress
        setActiveTasks((prev) =>
          prev.map((task) =>
            task.taskId === taskId ? { ...task, progress } : task,
          ),
        );

        // Update status message if provided
        if (progressMessage) {
          setStatusMessage(progressMessage);
        }
        break;
      }

      case "queue_update": {
        const depth = payload.queue_depth as number;
        setQueueDepth(depth);
        break;
      }
    }
  }, []);

  // Use the underlying realtimeSync hook
  const {
    status: realtimeStatus,
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
  });

  // Report WebSocket metrics for observability
  useEffect(() => {
    if (effectiveEnabled && metrics.totalAttempts > 0) {
      reportWebSocketMetrics("ai_orchestrator_status", metrics);
    }
  }, [effectiveEnabled, metrics]);

  // Override connection status if not enabled
  const connectionStatus: WebSocketConnectionStatus = effectiveEnabled
    ? realtimeStatus
    : "disconnected";

  // Compute currentTask (most recent active task)
  const currentTask =
    activeTasks.length > 0 ? activeTasks[activeTasks.length - 1] : null;

  // Compute statusForStatusBar (undefined when idle to let StatusBar derive)
  const statusForStatusBar =
    status === "processing" && statusMessage ? statusMessage : undefined;

  return {
    status,
    statusMessage,
    currentTask,
    activeTasks,
    taskHistory,
    lastError,
    connectionStatus,
    statusForStatusBar,
    queueDepth,
    taskProgress,
    disconnect,
    reconnect,
  };
}

export default useAIOrchestratorStatus;
