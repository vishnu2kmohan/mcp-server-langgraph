/**
 * ObservabilityDocument Component
 *
 * An observability dashboard document for use within the MainDock.
 * Displays traces, metrics, and logs for agent execution monitoring.
 *
 * Features:
 * - Tabbed interface (traces, logs, metrics)
 * - Status/time filtering for traces
 * - Trace list with clickable items
 * - Logs display with level coloring
 * - Metrics grid with key performance indicators
 * - Compact mode for docked tabs
 */

import { useState } from "react";
import {
  Activity,
  FileText,
  BarChart3,
  RefreshCw,
  Clock,
  Server,
  X,
  MessageSquare,
  GitBranch,
} from "lucide-react";
import {
  useListTracesQuery,
  useListLogsQuery,
  useGetMetricsQuery,
} from "../../api";
import { SkeletonCard, ErrorState } from "../UI";

import { Button, Select } from "@/components/UI";

// =============================================================================
// Utility
// =============================================================================

function cn(...classes: (string | undefined | boolean)[]): string {
  return classes.filter(Boolean).join(" ");
}

// =============================================================================
// Types
// =============================================================================

export interface ObservabilityDocumentProps {
  /** Whether to use compact styling for docked mode */
  compact?: boolean;
  /** Additional CSS classes */
  className?: string;
  /** Session ID to filter traces/logs by */
  sessionId?: string;
  /** Workflow ID to filter traces/logs by */
  workflowId?: string;
  /** Callback when context filter is cleared */
  onClearContext?: () => void;
}

type ObservabilityTab = "traces" | "logs" | "metrics";

// =============================================================================
// Component
// =============================================================================

export function ObservabilityDocument({
  compact = false,
  className,
  sessionId,
  workflowId,
  onClearContext,
}: ObservabilityDocumentProps) {
  const [activeTab, setActiveTab] = useState<ObservabilityTab>("traces");

  // Traces filter state
  const [statusFilter, setStatusFilter] = useState<string>("");
  const [timeRange, setTimeRange] = useState<string>("1h");

  // Calculate time range for query
  const getTimeRange = () => {
    const now = new Date();
    switch (timeRange) {
      case "15m":
        return new Date(now.getTime() - 15 * 60 * 1000).toISOString();
      case "1h":
        return new Date(now.getTime() - 60 * 60 * 1000).toISOString();
      case "24h":
        return new Date(now.getTime() - 24 * 60 * 60 * 1000).toISOString();
      case "7d":
        return new Date(now.getTime() - 7 * 24 * 60 * 60 * 1000).toISOString();
      default:
        return undefined;
    }
  };

  // RTK Query hooks
  const {
    data: tracesData,
    isLoading: isTracesLoading,
    isError: isTracesError,
    error: tracesErrorData,
    refetch: refetchTraces,
  } = useListTracesQuery({
    limit: 50,
    status: statusFilter || undefined,
    start_time: getTimeRange(),
    session_id: sessionId,
    workflow_id: workflowId,
  });

  const {
    data: logsData,
    isLoading: isLogsLoading,
    refetch: refetchLogs,
  } = useListLogsQuery({ limit: 50 }, { skip: activeTab !== "logs" });

  const {
    data: metricsData,
    isLoading: isMetricsLoading,
    refetch: refetchMetrics,
  } = useGetMetricsQuery(undefined, { skip: activeTab !== "metrics" });

  // Map traces to component format
  const traces =
    tracesData?.items?.map((trace) => ({
      id: trace.traceId,
      name: trace.name,
      duration: trace.durationMs ?? 0,
      status: (trace.status ?? "success") as "success" | "error" | "running",
      timestamp: trace.startTime ?? new Date().toISOString(),
      spans: trace.spanCount ?? 0,
    })) ?? [];

  const logs = logsData?.items ?? [];
  const metrics = metricsData ?? null;

  const isLoading =
    activeTab === "traces"
      ? isTracesLoading
      : activeTab === "logs"
        ? isLogsLoading
        : isMetricsLoading;

  const handleRefresh = () => {
    if (activeTab === "traces") refetchTraces();
    else if (activeTab === "logs") refetchLogs();
    else refetchMetrics();
  };

  const getLogLevelColor = (level: "info" | "warn" | "error" | "debug") => {
    switch (level) {
      case "error":
        return "bg-error-100 text-error-700 dark:bg-error-900/30 dark:text-error-400";
      case "warn":
        return "bg-warning-100 text-warning-700 dark:bg-warning-900/30 dark:text-warning-400";
      case "info":
        return "bg-primary-100 text-primary-700 dark:bg-primary-900/30 dark:text-primary-400";
      case "debug":
        return "bg-neutral-100 dark:bg-neutral-800 text-neutral-700 dark:text-neutral-200 dark:bg-neutral-900/30 dark:text-neutral-400";
    }
  };

  const getStatusColor = (status: "success" | "error" | "running") => {
    switch (status) {
      case "success":
        return "bg-success-100 text-success-700 dark:bg-success-900/30 dark:text-success-400";
      case "error":
        return "bg-error-100 text-error-700 dark:bg-error-900/30 dark:text-error-400";
      case "running":
        return "bg-primary-100 text-primary-700 dark:bg-primary-900/30 dark:text-primary-400";
    }
  };

  const tabs = [
    { id: "traces" as const, label: "Traces", icon: Activity },
    { id: "logs" as const, label: "Logs", icon: FileText },
    { id: "metrics" as const, label: "Metrics", icon: BarChart3 },
  ];

  return (
    <div
      data-testid="observability-document"
      className={cn(
        "flex flex-col h-full",
        "bg-neutral-50 dark:bg-neutral-900",
        compact && "text-sm",
        className,
      )}
    >
      {/* Header */}
      <header className="px-6 py-4 bg-white dark:bg-neutral-800 border-b border-neutral-200 dark:border-neutral-700">
        <div className="flex items-center justify-between">
          <div>
            <h2 className="text-xl font-bold text-neutral-900 dark:text-neutral-100">
              Observability
            </h2>
            <p className="text-sm text-neutral-500 dark:text-neutral-400">
              Monitor traces, logs, and metrics for your AI agents
            </p>
          </div>
          <Button
            variant="secondary"
            className="flex px-3 py-2 bg-neutral-100 dark:bg-neutral-700 rounded-lg hover:bg-neutral-200 dark:bg-neutral-700 dark:hover:bg-neutral-600 text-neutral-700 dark:text-neutral-300"
            onClick={handleRefresh}
          >
            <RefreshCw size={16} />
            Refresh
          </Button>
        </div>

        {/* Context Indicator */}
        {(sessionId || workflowId) && (
          <div
            data-testid="context-indicator"
            className="mt-3 flex items-center gap-2 flex-wrap"
          >
            <span className="text-sm text-neutral-500 dark:text-neutral-400">
              Filtered by:
            </span>
            {sessionId && (
              <span className="inline-flex items-center gap-1.5 px-2.5 py-1 bg-primary-100 text-primary-700 dark:bg-primary-900/30 dark:text-primary-400 rounded-full text-sm">
                <MessageSquare size={14} />
                {sessionId}
              </span>
            )}
            {workflowId && (
              <span className="inline-flex items-center gap-1.5 px-2.5 py-1 bg-insight-100 text-insight-700 dark:bg-insight-900/30 dark:text-insight-400 rounded-full text-sm">
                <GitBranch size={14} />
                {workflowId}
              </span>
            )}
            {onClearContext && (
              <Button
                variant="secondary"
                size="sm"
                className="px-2 py-1 text-sm text-neutral-500 dark:text-neutral-400 hover:text-neutral-700 dark:text-neutral-200 dark:text-neutral-400 dark:hover:text-neutral-200 hover:bg-neutral-100 dark:bg-neutral-800 dark:hover:bg-neutral-700 rounded"
                data-testid="clear-context-filter"
                onClick={onClearContext}
              >
                <X size={14} />
                Clear
              </Button>
            )}
          </div>
        )}
      </header>
      {/* Tabs */}
      <div className="px-6 py-2 bg-white dark:bg-neutral-800 border-b border-neutral-200 dark:border-neutral-700">
        <div className="flex gap-1">
          {tabs.map((tab) => (
            <Button
              className="flex px-4 py-2 rounded-lg"
              key={tab.id}
              onClick={() => setActiveTab(tab.id)}
            >
              <tab.icon size={16} />
              {tab.label}
            </Button>
          ))}
        </div>
      </div>
      {/* Traces Filters */}
      {activeTab === "traces" && (
        <div className="px-6 py-3 bg-white dark:bg-neutral-800 border-b border-neutral-200 dark:border-neutral-700">
          <div className="flex items-center gap-4 flex-wrap">
            {/* Status filter buttons */}
            <div className="flex items-center gap-1">
              {["", "success", "error", "running"].map((status) => (
                <Button
                  size="sm"
                  className="px-2 py-1 text-xs rounded"
                  key={status || "all"}
                  onClick={() => setStatusFilter(status)}
                  aria-pressed={statusFilter === status}
                >
                  {status || "All"}
                </Button>
              ))}
            </div>

            {/* Time range filter */}
            <Select
              size="sm"
              className="px-2 py-1 text-sm text-neutral-900 dark:text-neutral-100 focus:ring-primary-500"
              value={timeRange}
              onChange={(e) => setTimeRange(e.target.value)}
              aria-label="Time range"
            >
              <option value="15m">Last 15 minutes</option>
              <option value="1h">Last 1 hour</option>
              <option value="24h">Last 24 hours</option>
              <option value="7d">Last 7 days</option>
              <option value="all">All time</option>
            </Select>

            {/* Trace count */}
            {tracesData && (
              <span className="text-sm text-neutral-500 dark:text-neutral-400 ml-auto">
                Showing {traces.length} traces
                {tracesData.hasNext ? " (more available)" : ""}
              </span>
            )}
          </div>
        </div>
      )}
      {/* Content */}
      <div className="flex-1 overflow-y-auto p-6">
        {isLoading ? (
          <div className="space-y-4">
            <SkeletonCard />
            <SkeletonCard />
            <SkeletonCard />
          </div>
        ) : isTracesError && activeTab === "traces" ? (
          <ErrorState
            title="Failed to load traces"
            message={
              (tracesErrorData as { message?: string })?.message ||
              "Unable to fetch trace data. Please try again."
            }
            onRetry={handleRefresh}
          />
        ) : (
          <>
            {/* Traces Tab */}
            {activeTab === "traces" && (
              <div className="space-y-3">
                {traces.length === 0 ? (
                  <div className="text-center py-12 text-neutral-500 dark:text-neutral-400">
                    No traces found
                  </div>
                ) : (
                  traces.map((trace) => (
                    <div
                      key={trace.id}
                      className="p-4 bg-white dark:bg-neutral-800 rounded-lg border border-neutral-200 dark:border-neutral-700 hover:border-primary-500 transition-colors cursor-pointer"
                    >
                      <div className="flex items-center justify-between">
                        <div className="flex items-center gap-3">
                          <Activity size={20} className="text-primary-500" />
                          <div>
                            <h3 className="font-medium text-neutral-900 dark:text-neutral-100">
                              {trace.name}
                            </h3>
                            <div className="flex items-center gap-3 mt-1 text-sm text-neutral-500 dark:text-neutral-400">
                              <span className="flex items-center gap-1">
                                <Clock size={14} />
                                {trace.duration}ms
                              </span>
                              <span>{trace.spans} spans</span>
                              <span>
                                {new Date(trace.timestamp).toLocaleTimeString()}
                              </span>
                            </div>
                          </div>
                        </div>
                        <span
                          className={`px-2 py-1 text-xs rounded-full ${getStatusColor(trace.status)}`}
                        >
                          {trace.status}
                        </span>
                      </div>
                    </div>
                  ))
                )}
              </div>
            )}

            {/* Logs Tab */}
            {activeTab === "logs" && (
              <div className="space-y-2">
                {logs.length === 0 ? (
                  <div className="text-center py-12 text-neutral-500 dark:text-neutral-400">
                    No logs found
                  </div>
                ) : (
                  logs.map((log) => (
                    <div
                      key={log.id}
                      className="p-4 bg-white dark:bg-neutral-800 rounded-lg border border-neutral-200 dark:border-neutral-700"
                    >
                      <div className="flex items-center justify-between">
                        <div className="flex items-center gap-3">
                          <span
                            className={`px-2 py-0.5 text-xs rounded-full ${getLogLevelColor(log.level)}`}
                          >
                            {log.level}
                          </span>
                          <span className="text-neutral-900 dark:text-neutral-100">
                            {log.message}
                          </span>
                        </div>
                        <div className="flex items-center gap-3 text-sm text-neutral-500 dark:text-neutral-400">
                          {log.service && (
                            <span className="flex items-center gap-1">
                              <Server size={14} />
                              {log.service}
                            </span>
                          )}
                          <span className="flex items-center gap-1">
                            <Clock size={14} />
                            {new Date(log.timestamp).toLocaleTimeString()}
                          </span>
                        </div>
                      </div>
                    </div>
                  ))
                )}
              </div>
            )}

            {/* Metrics Tab */}
            {activeTab === "metrics" && metrics && (
              <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4">
                <div className="p-4 bg-white dark:bg-neutral-800 rounded-lg border border-neutral-200 dark:border-neutral-700">
                  <h3 className="text-sm font-medium text-neutral-500 dark:text-neutral-400 mb-1">
                    Total Requests
                  </h3>
                  <div className="text-2xl font-semibold text-neutral-900 dark:text-neutral-100">
                    {(metrics.requestsTotal ?? 0).toLocaleString()}
                  </div>
                </div>
                <div className="p-4 bg-white dark:bg-neutral-800 rounded-lg border border-neutral-200 dark:border-neutral-700">
                  <h3 className="text-sm font-medium text-neutral-500 dark:text-neutral-400 mb-1">
                    Total Errors
                  </h3>
                  <div className="text-2xl font-semibold text-error-600 dark:text-error-400">
                    {(metrics.errorsTotal ?? 0).toLocaleString()}
                  </div>
                </div>
                <div className="p-4 bg-white dark:bg-neutral-800 rounded-lg border border-neutral-200 dark:border-neutral-700">
                  <h3 className="text-sm font-medium text-neutral-500 dark:text-neutral-400 mb-1">
                    Avg Latency
                  </h3>
                  <div className="text-2xl font-semibold text-neutral-900 dark:text-neutral-100">
                    {metrics.avgLatencyMs ?? 0}ms
                  </div>
                </div>
                <div className="p-4 bg-white dark:bg-neutral-800 rounded-lg border border-neutral-200 dark:border-neutral-700">
                  <h3 className="text-sm font-medium text-neutral-500 dark:text-neutral-400 mb-1">
                    P99 Latency
                  </h3>
                  <div className="text-2xl font-semibold text-neutral-900 dark:text-neutral-100">
                    {metrics.p99LatencyMs ?? 0}ms
                  </div>
                </div>
                <div className="p-4 bg-white dark:bg-neutral-800 rounded-lg border border-neutral-200 dark:border-neutral-700">
                  <h3 className="text-sm font-medium text-neutral-500 dark:text-neutral-400 mb-1">
                    Tokens Used
                  </h3>
                  <div className="text-2xl font-semibold text-neutral-900 dark:text-neutral-100">
                    {(metrics.tokensUsed ?? 0).toLocaleString()}
                  </div>
                </div>
                <div className="p-4 bg-white dark:bg-neutral-800 rounded-lg border border-neutral-200 dark:border-neutral-700">
                  <h3 className="text-sm font-medium text-neutral-500 dark:text-neutral-400 mb-1">
                    Active Sessions
                  </h3>
                  <div className="text-2xl font-semibold text-neutral-900 dark:text-neutral-100">
                    {metrics.activeSessions ?? 0}
                  </div>
                </div>
              </div>
            )}

            {/* Empty metrics state */}
            {activeTab === "metrics" && !metrics && !isMetricsLoading && (
              <div className="text-center py-12 text-neutral-500 dark:text-neutral-400">
                No metrics data available
              </div>
            )}
          </>
        )}
      </div>
    </div>
  );
}

export default ObservabilityDocument;
