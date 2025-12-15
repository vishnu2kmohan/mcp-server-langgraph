/**
 * ExecutionHistoryPanel Component
 *
 * Displays workflow execution history with status indicators,
 * filtering, and pagination support.
 */

import { useState, useMemo } from "react";
import {
  Loader2,
  Clock,
  AlertCircle,
  CheckCircle,
  PlayCircle,
} from "lucide-react";

export interface WorkflowExecution {
  id: string;
  workflow_id: string;
  status: "pending" | "running" | "completed" | "failed";
  started_at: string;
  completed_at?: string | null;
  input_data?: Record<string, unknown> | null;
  output_data?: Record<string, unknown> | null;
  error?: string | null;
}

export interface ExecutionHistoryPanelProps {
  executions: WorkflowExecution[];
  isLoading: boolean;
  onSelectExecution: (execution: WorkflowExecution) => void;
  onLoadMore: () => void;
  hasMore: boolean;
  selectedExecutionId?: string;
}

type StatusFilter = "all" | "completed" | "failed" | "running";

export function ExecutionHistoryPanel({
  executions,
  isLoading,
  onSelectExecution,
  onLoadMore,
  hasMore,
  selectedExecutionId,
}: ExecutionHistoryPanelProps) {
  const [statusFilter, setStatusFilter] = useState<StatusFilter>("all");

  const filteredExecutions = useMemo(() => {
    if (statusFilter === "all") return executions;
    return executions.filter((e) => e.status === statusFilter);
  }, [executions, statusFilter]);

  const getStatusColor = (status: WorkflowExecution["status"]) => {
    switch (status) {
      case "completed":
        return "bg-green-500";
      case "running":
        return "bg-blue-500";
      case "failed":
        return "bg-red-500";
      case "pending":
        return "bg-yellow-500";
    }
  };

  const getStatusIcon = (status: WorkflowExecution["status"]) => {
    switch (status) {
      case "completed":
        return <CheckCircle className="w-4 h-4 text-green-500" />;
      case "running":
        return <PlayCircle className="w-4 h-4 text-blue-500 animate-spin" />;
      case "failed":
        return <AlertCircle className="w-4 h-4 text-red-500" />;
      case "pending":
        return <Clock className="w-4 h-4 text-yellow-500" />;
    }
  };

  const formatTime = (dateString: string) => {
    const date = new Date(dateString);
    return date.toLocaleTimeString("en-US", {
      hour: "2-digit",
      minute: "2-digit",
    });
  };

  const formatDuration = (startedAt: string, completedAt?: string | null) => {
    if (!completedAt) return null;
    const start = new Date(startedAt).getTime();
    const end = new Date(completedAt).getTime();
    const durationMs = end - start;

    if (durationMs < 60000) {
      return `${Math.round(durationMs / 1000)}s`;
    }
    return `${Math.round(durationMs / 60000)}m`;
  };

  if (isLoading && executions.length === 0) {
    return (
      <div
        data-testid="execution-loading"
        className="flex items-center justify-center h-full p-8"
      >
        <Loader2 className="w-8 h-8 animate-spin text-blue-500" />
      </div>
    );
  }

  return (
    <div className="flex flex-col h-full bg-white dark:bg-gray-800 rounded-lg shadow">
      {/* Header */}
      <div className="p-4 border-b border-gray-200 dark:border-gray-700">
        <div className="flex items-center justify-between mb-3">
          <h2 className="text-lg font-semibold text-gray-900 dark:text-white">
            Execution History
          </h2>
          <span className="text-sm text-gray-500 dark:text-gray-400">
            {filteredExecutions.length} executions
          </span>
        </div>

        {/* Status Filters */}
        <div className="flex gap-2">
          {(["all", "completed", "failed", "running"] as StatusFilter[]).map(
            (filter) => (
              <button
                key={filter}
                onClick={() => setStatusFilter(filter)}
                className={`px-3 py-1 text-sm rounded-full transition-colors ${
                  statusFilter === filter
                    ? "bg-blue-600 text-white"
                    : "bg-gray-100 dark:bg-gray-700 text-gray-700 dark:text-gray-300 hover:bg-gray-200 dark:hover:bg-gray-600"
                }`}
              >
                {filter.charAt(0).toUpperCase() + filter.slice(1)}
              </button>
            ),
          )}
        </div>
      </div>

      {/* Execution List */}
      <div className="flex-1 overflow-y-auto">
        {filteredExecutions.length === 0 ? (
          <div className="flex flex-col items-center justify-center h-full p-8 text-center">
            <Clock className="w-12 h-12 text-gray-300 dark:text-gray-600 mb-4" />
            <p className="text-gray-600 dark:text-gray-400 font-medium">
              No executions yet
            </p>
            <p className="text-sm text-gray-500 dark:text-gray-500 mt-1">
              Run this workflow to see execution history
            </p>
          </div>
        ) : (
          <div className="divide-y divide-gray-100 dark:divide-gray-700">
            {filteredExecutions.map((execution) => (
              <div
                key={execution.id}
                data-testid={`execution-${execution.id}`}
                onClick={() => onSelectExecution(execution)}
                className={`p-4 cursor-pointer hover:bg-gray-50 dark:hover:bg-gray-700 transition-colors ${
                  selectedExecutionId === execution.id
                    ? "bg-blue-50 dark:bg-blue-900/20 ring-2 ring-blue-500"
                    : ""
                }`}
              >
                <div className="flex items-start gap-3">
                  {/* Status Indicator */}
                  <div className="flex-shrink-0 mt-1">
                    <div
                      className={`w-3 h-3 rounded-full ${getStatusColor(execution.status)} ${
                        execution.status === "running" ? "animate-spin" : ""
                      }`}
                    />
                  </div>

                  {/* Execution Details */}
                  <div className="flex-1 min-w-0">
                    <div className="flex items-center gap-2">
                      {getStatusIcon(execution.status)}
                      <span className="text-sm font-medium text-gray-900 dark:text-white capitalize">
                        {execution.status}
                      </span>
                      {execution.completed_at && (
                        <span className="text-xs text-gray-500 dark:text-gray-400">
                          {formatDuration(
                            execution.started_at,
                            execution.completed_at,
                          )}
                        </span>
                      )}
                    </div>

                    <div className="flex items-center gap-2 mt-1">
                      <Clock className="w-3 h-3 text-gray-400" />
                      <span className="text-xs text-gray-500 dark:text-gray-400">
                        {formatTime(execution.started_at)}
                      </span>
                    </div>

                    {execution.error && (
                      <div className="mt-2 p-2 bg-red-50 dark:bg-red-900/20 rounded text-xs text-red-600 dark:text-red-400">
                        {execution.error}
                      </div>
                    )}
                  </div>
                </div>
              </div>
            ))}
          </div>
        )}
      </div>

      {/* Load More */}
      {hasMore && (
        <div className="p-4 border-t border-gray-200 dark:border-gray-700">
          <button
            onClick={onLoadMore}
            disabled={isLoading}
            className="w-full py-2 text-sm text-blue-600 dark:text-blue-400 hover:bg-blue-50 dark:hover:bg-blue-900/20 rounded transition-colors disabled:opacity-50"
          >
            {isLoading ? "Loading..." : "Load More"}
          </button>
        </div>
      )}
    </div>
  );
}
