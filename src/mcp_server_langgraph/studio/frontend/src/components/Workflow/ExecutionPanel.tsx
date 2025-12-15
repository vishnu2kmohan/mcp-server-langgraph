/**
 * ExecutionPanel Component
 *
 * Displays execution logs and status.
 * Shows real-time updates during workflow execution.
 */

import { useRef, useEffect } from "react";
import {
  X,
  Info,
  AlertTriangle,
  XCircle,
  Square,
  CheckCircle,
  Loader2,
} from "lucide-react";
import { useAppDispatch, useAppSelector } from "../../store/hooks";
import {
  clearExecutionLogs,
  selectExecutionState,
  selectExecutionLogs,
  selectNodeStatuses,
} from "../../store/slices/workflowSlice";
import type { NodeStatus } from "../../types/workflow";

interface ExecutionPanelProps {
  onClose?: () => void;
  onStop?: () => void;
}

export function ExecutionPanel({ onClose, onStop }: ExecutionPanelProps) {
  const dispatch = useAppDispatch();
  const executionState = useAppSelector(selectExecutionState);
  const executionLogs = useAppSelector(selectExecutionLogs);
  const nodeStatuses = useAppSelector(selectNodeStatuses);
  const lastLogRef = useRef<HTMLDivElement>(null);

  // Auto-scroll to the last log when new logs are added
  useEffect(() => {
    if (
      lastLogRef.current &&
      typeof lastLogRef.current.scrollIntoView === "function"
    ) {
      lastLogRef.current.scrollIntoView({ behavior: "smooth", block: "end" });
    }
  }, [executionLogs.length]);

  const getNodeStatusBadgeClass = (status: NodeStatus): string => {
    switch (status) {
      case "running":
        return "bg-blue-100 text-blue-700 dark:bg-blue-900/30 dark:text-blue-400";
      case "success":
        return "bg-green-100 text-green-700 dark:bg-green-900/30 dark:text-green-400";
      case "error":
        return "bg-red-100 text-red-700 dark:bg-red-900/30 dark:text-red-400";
      case "idle":
      default:
        return "bg-gray-100 text-gray-700 dark:bg-gray-700 dark:text-gray-300";
    }
  };

  const getNodeStatusIcon = (status: NodeStatus) => {
    switch (status) {
      case "running":
        return <Loader2 size={12} className="animate-spin" />;
      case "success":
        return <CheckCircle size={12} />;
      case "error":
        return <XCircle size={12} />;
      default:
        return null;
    }
  };

  const getLogIcon = (level: "info" | "warning" | "error") => {
    switch (level) {
      case "info":
        return <Info size={16} className="text-blue-500" />;
      case "warning":
        return <AlertTriangle size={16} className="text-yellow-500" />;
      case "error":
        return <XCircle size={16} className="text-red-500" />;
    }
  };

  const formatTimestamp = (timestamp: number) => {
    return new Date(timestamp).toLocaleTimeString("en-US", {
      hour: "2-digit",
      minute: "2-digit",
      second: "2-digit",
    });
  };

  return (
    <div className="h-64 bg-white dark:bg-gray-800 border-t border-gray-200 dark:border-gray-700 flex flex-col">
      {/* Header */}
      <div className="flex items-center justify-between p-3 border-b border-gray-200 dark:border-gray-700">
        <div className="flex items-center gap-2">
          <h3 className="font-semibold text-gray-900 dark:text-gray-100">
            Execution Logs
          </h3>
          <span
            className={`
              text-xs px-2 py-0.5 rounded
              ${executionState === "idle" ? "bg-gray-100 text-gray-700 dark:bg-gray-700 dark:text-gray-300" : ""}
              ${executionState === "running" ? "bg-blue-100 text-blue-700 dark:bg-blue-900/30 dark:text-blue-400" : ""}
              ${executionState === "completed" ? "bg-green-100 text-green-700 dark:bg-green-900/30 dark:text-green-400" : ""}
              ${executionState === "error" ? "bg-red-100 text-red-700 dark:bg-red-900/30 dark:text-red-400" : ""}
            `}
          >
            {executionState}
          </span>
        </div>

        <div className="flex items-center gap-2">
          {executionState === "running" && onStop && (
            <button
              onClick={onStop}
              className="flex items-center gap-1 text-xs px-2 py-1 bg-red-100 text-red-700 dark:bg-red-900/30 dark:text-red-400 rounded hover:bg-red-200 dark:hover:bg-red-900/50"
            >
              <Square size={12} />
              Stop
            </button>
          )}
          {executionLogs.length > 0 && (
            <button
              onClick={() => dispatch(clearExecutionLogs())}
              className="text-xs px-2 py-1 text-gray-600 dark:text-gray-400 hover:text-gray-900 dark:hover:text-gray-100"
            >
              Clear
            </button>
          )}
          {onClose && (
            <button
              onClick={onClose}
              className="p-1 hover:bg-gray-100 dark:hover:bg-gray-700 rounded"
            >
              <X size={18} className="text-gray-500 dark:text-gray-400" />
            </button>
          )}
        </div>
      </div>

      {/* Node Statuses */}
      {Object.keys(nodeStatuses).length > 0 && (
        <div
          data-testid="node-statuses"
          className="flex items-center gap-2 px-3 py-2 border-b border-gray-200 dark:border-gray-700 overflow-x-auto"
        >
          <span className="text-xs text-gray-500 dark:text-gray-400 shrink-0">
            Nodes:
          </span>
          {Object.entries(nodeStatuses).map(([nodeId, status]) => (
            <span
              key={nodeId}
              data-testid={`node-status-${nodeId}`}
              className={`flex items-center gap-1 text-xs px-2 py-0.5 rounded shrink-0 ${getNodeStatusBadgeClass(status)}`}
            >
              {getNodeStatusIcon(status)}
              {nodeId}
            </span>
          ))}
        </div>
      )}

      {/* Logs */}
      <div
        data-testid="logs-container"
        className="flex-1 overflow-y-auto p-3 space-y-2"
      >
        {executionLogs.length === 0 ? (
          <div className="text-center text-sm text-gray-500 dark:text-gray-400 py-8">
            No execution logs yet. Click "Run" to execute the workflow.
          </div>
        ) : (
          executionLogs.map((log, index) => {
            const isLast = index === executionLogs.length - 1;
            return (
              <div
                key={log.id}
                ref={isLast ? lastLogRef : undefined}
                data-testid="log-item"
                data-last={isLast ? "true" : undefined}
                className="flex items-start gap-2 text-sm p-2 rounded bg-gray-50 dark:bg-gray-700/50"
              >
                {getLogIcon(log.level)}
                <div className="flex-1 min-w-0">
                  <div className="flex items-center gap-2">
                    <span className="text-xs text-gray-500 dark:text-gray-400">
                      {formatTimestamp(log.timestamp)}
                    </span>
                    {log.nodeId && (
                      <span className="text-xs text-gray-500 dark:text-gray-400">
                        [{log.nodeId}]
                      </span>
                    )}
                  </div>
                  <div className="text-gray-900 dark:text-gray-100 break-words">
                    {log.message}
                  </div>
                </div>
              </div>
            );
          })
        )}
      </div>
    </div>
  );
}
