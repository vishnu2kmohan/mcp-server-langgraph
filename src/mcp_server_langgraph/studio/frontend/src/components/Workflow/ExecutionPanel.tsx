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

import { Button } from "@/components/UI";

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
        return "bg-primary-3 text-primary-11 bg-primary-4 dark:text-primary-7";
      case "success":
        return "bg-success-3 text-success-11 bg-success-4 dark:text-success-7";
      case "error":
        return "bg-error-3 text-error-11 bg-error-4 dark:text-error-7";
      case "idle":
      default:
        return "bg-neutral-2 text-neutral-11";
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
        return <Info size={16} className="text-primary-9" />;
      case "warning":
        return <AlertTriangle size={16} className="text-warning-9" />;
      case "error":
        return <XCircle size={16} className="text-error-9" />;
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
    <div className="h-64 bg-neutral-1 border-t border-neutral-5 flex flex-col">
      {/* Header */}
      <div className="flex items-center justify-between p-3 border-b border-neutral-5">
        <div className="flex items-center gap-2">
          <h3 className="font-semibold text-neutral-12">
            Execution Logs
          </h3>
          <span
            className={`
              text-xs px-2 py-0.5 rounded
              ${executionState === "idle" ? "bg-neutral-2 text-neutral-11" : ""}
              ${executionState === "running" ? "bg-primary-3 text-primary-11 bg-primary-4 dark:text-primary-7" : ""}
              ${executionState === "completed" ? "bg-success-3 text-success-11 bg-success-4 dark:text-success-7" : ""}
              ${executionState === "error" ? "bg-error-3 text-error-11 bg-error-4 dark:text-error-7" : ""}
            `}
          >
            {executionState}
          </span>
        </div>

        <div className="flex items-center gap-2">
          {executionState === "running" && onStop && (
            <Button
              variant="danger"
              size="sm"
              className="flex text-xs px-2 py-1 bg-error-3 text-error-11 bg-error-4 dark:text-error-7 rounded hover:bg-error-4 dark:hover:bg-error-a6"
              onClick={onStop}
            >
              <Square size={12} />
              Stop
            </Button>
          )}
          {executionLogs.length > 0 && (
            <Button
              variant="danger"
              size="sm"
              className="text-xs px-2 py-1 text-neutral-11 hover:text-neutral-12"
              onClick={() => dispatch(clearExecutionLogs())}>
              Clear
            </Button>
          )}
          {onClose && (
            <Button size="icon"
              variant="secondary"
              className="p-1 hover:bg-neutral-2 rounded"
              onClick={onClose}
            >
              <X size={18} className="text-neutral-10" />
            </Button>
          )}
        </div>
      </div>
      {/* Node Statuses */}
      {Object.keys(nodeStatuses).length > 0 && (
        <div
          data-testid="node-statuses"
          className="flex items-center gap-2 px-3 py-2 border-b border-neutral-5 overflow-x-auto"
        >
          <span className="text-xs text-neutral-10 shrink-0">
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
          <div className="text-center text-sm text-neutral-10 py-8">
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
                className="flex items-start gap-2 text-sm p-2 rounded bg-neutral-1"
              >
                {getLogIcon(log.level)}
                <div className="flex-1 min-w-0">
                  <div className="flex items-center gap-2">
                    <span className="text-xs text-neutral-10">
                      {formatTimestamp(log.timestamp)}
                    </span>
                    {log.nodeId && (
                      <span className="text-xs text-neutral-10">
                        [{log.nodeId}]
                      </span>
                    )}
                  </div>
                  <div className="text-neutral-12 break-words">
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
