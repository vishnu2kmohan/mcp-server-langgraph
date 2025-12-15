/**
 * ObservabilityPage
 *
 * Observability page showing traces, logs, and metrics
 * for agent execution monitoring.
 *
 * Uses RTK Query for data fetching with automatic caching and updates.
 */

import { useState } from "react";
import {
  Activity,
  FileText,
  BarChart3,
  RefreshCw,
  Clock,
  Server,
} from "lucide-react";
import {
  useListTracesQuery,
  useListLogsQuery,
  useGetMetricsQuery,
} from "../api";
import { SkeletonList, ErrorState } from "../components/UI";

type ObservabilityTab = "traces" | "logs" | "metrics";

export function ObservabilityPage() {
  const [activeTab, setActiveTab] = useState<ObservabilityTab>("traces");

  // Traces filter state
  const [statusFilter, setStatusFilter] = useState<string>("");
  const [sessionIdFilter, setSessionIdFilter] = useState<string>("");
  const [timeRange, setTimeRange] = useState<string>("1h");
  const [cursor, setCursor] = useState<string | undefined>(undefined);

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

  // Fetch data with RTK Query - skip based on active tab for lazy loading
  const {
    data: tracesData,
    isLoading: isTracesLoading,
    isFetching: isTracesFetching,
    error: tracesError,
    refetch: refetchTraces,
  } = useListTracesQuery({
    limit: 50,
    status: statusFilter || undefined,
    session_id: sessionIdFilter || undefined,
    start_time: getTimeRange(),
    cursor,
  });

  const {
    data: logsData,
    isLoading: isLogsLoading,
    error: logsError,
    refetch: refetchLogs,
  } = useListLogsQuery({ limit: 50 }, { skip: activeTab !== "logs" });

  const {
    data: metricsData,
    isLoading: isMetricsLoading,
    error: metricsError,
    refetch: refetchMetrics,
  } = useGetMetricsQuery(undefined, { skip: activeTab !== "metrics" });

  // Map traces to component format
  const traces =
    tracesData?.items.map((trace) => ({
      id: trace.trace_id,
      name: trace.name,
      duration:
        new Date(trace.end_time).getTime() -
        new Date(trace.start_time).getTime(),
      status: trace.status as "success" | "error" | "running",
      timestamp: trace.start_time,
      spans: 1, // Could be expanded in the future
    })) ?? [];

  // Map logs to component format
  const logs = logsData?.items ?? [];

  // Metrics data
  const metrics = metricsData ?? null;

  const tabs = [
    { id: "traces" as const, label: "Traces", icon: Activity },
    { id: "logs" as const, label: "Logs", icon: FileText },
    { id: "metrics" as const, label: "Metrics", icon: BarChart3 },
  ];

  const getLogLevelColor = (level: "info" | "warn" | "error" | "debug") => {
    switch (level) {
      case "error":
        return "bg-red-100 text-red-700 dark:bg-red-900/30 dark:text-red-400";
      case "warn":
        return "bg-yellow-100 text-yellow-700 dark:bg-yellow-900/30 dark:text-yellow-400";
      case "info":
        return "bg-blue-100 text-blue-700 dark:bg-blue-900/30 dark:text-blue-400";
      case "debug":
        return "bg-gray-100 text-gray-700 dark:bg-gray-900/30 dark:text-gray-400";
    }
  };

  const getStatusColor = (status: "success" | "error" | "running") => {
    switch (status) {
      case "success":
        return "bg-green-100 text-green-700 dark:bg-green-900/30 dark:text-green-400";
      case "error":
        return "bg-red-100 text-red-700 dark:bg-red-900/30 dark:text-red-400";
      case "running":
        return "bg-blue-100 text-blue-700 dark:bg-blue-900/30 dark:text-blue-400";
    }
  };

  const isLoading =
    activeTab === "traces"
      ? isTracesLoading
      : activeTab === "logs"
        ? isLogsLoading
        : isMetricsLoading;

  const error =
    activeTab === "traces"
      ? tracesError
      : activeTab === "logs"
        ? logsError
        : metricsError;

  const handleRefresh = () => {
    if (activeTab === "traces") refetchTraces();
    else if (activeTab === "logs") refetchLogs();
    else refetchMetrics();
  };

  return (
    <div className="h-screen flex flex-col bg-gray-50 dark:bg-gray-900">
      {/* Header */}
      <header className="px-6 py-4 bg-white dark:bg-gray-800 border-b border-gray-200 dark:border-gray-700">
        <div className="flex items-center justify-between">
          <div>
            <h1 className="text-2xl font-bold text-gray-900 dark:text-gray-100">
              Observability
            </h1>
            <p className="text-sm text-gray-500 dark:text-gray-400">
              Monitor traces, logs, and metrics for your AI agents
            </p>
          </div>
          <button
            onClick={handleRefresh}
            className="flex items-center gap-2 px-4 py-2 bg-gray-100 dark:bg-gray-700 rounded-lg hover:bg-gray-200 dark:hover:bg-gray-600 transition-colors"
          >
            <RefreshCw size={16} />
            Refresh
          </button>
        </div>
      </header>

      {/* Tabs */}
      <div className="px-6 py-2 bg-white dark:bg-gray-800 border-b border-gray-200 dark:border-gray-700">
        <div className="flex gap-1">
          {tabs.map((tab) => (
            <button
              key={tab.id}
              onClick={() => setActiveTab(tab.id)}
              className={`flex items-center gap-2 px-4 py-2 rounded-lg transition-colors ${
                activeTab === tab.id
                  ? "bg-blue-100 text-blue-700 dark:bg-blue-900/30 dark:text-blue-400"
                  : "text-gray-600 hover:bg-gray-100 dark:text-gray-400 dark:hover:bg-gray-700"
              }`}
            >
              <tab.icon size={16} />
              {tab.label}
            </button>
          ))}
        </div>
      </div>

      {/* Traces Filters - only show on traces tab */}
      {activeTab === "traces" && (
        <div className="px-6 py-3 bg-white dark:bg-gray-800 border-b border-gray-200 dark:border-gray-700">
          <div className="flex items-center gap-4 flex-wrap">
            {/* Status filter */}
            <div className="flex items-center gap-1">
              <button
                onClick={() => setStatusFilter("")}
                className={`px-2 py-1 text-xs rounded ${
                  statusFilter === ""
                    ? "bg-blue-600 text-white"
                    : "bg-gray-100 dark:bg-gray-700 text-gray-700 dark:text-gray-300 hover:bg-gray-200 dark:hover:bg-gray-600"
                }`}
                aria-pressed={statusFilter === ""}
              >
                All
              </button>
              <button
                onClick={() => setStatusFilter("success")}
                className={`px-2 py-1 text-xs rounded ${
                  statusFilter === "success"
                    ? "bg-green-600 text-white"
                    : "bg-gray-100 dark:bg-gray-700 text-gray-700 dark:text-gray-300 hover:bg-gray-200 dark:hover:bg-gray-600"
                }`}
                aria-pressed={statusFilter === "success"}
              >
                Success
              </button>
              <button
                onClick={() => setStatusFilter("error")}
                className={`px-2 py-1 text-xs rounded ${
                  statusFilter === "error"
                    ? "bg-red-600 text-white"
                    : "bg-gray-100 dark:bg-gray-700 text-gray-700 dark:text-gray-300 hover:bg-gray-200 dark:hover:bg-gray-600"
                }`}
                aria-pressed={statusFilter === "error"}
              >
                Error
              </button>
              <button
                onClick={() => setStatusFilter("running")}
                className={`px-2 py-1 text-xs rounded ${
                  statusFilter === "running"
                    ? "bg-blue-600 text-white"
                    : "bg-gray-100 dark:bg-gray-700 text-gray-700 dark:text-gray-300 hover:bg-gray-200 dark:hover:bg-gray-600"
                }`}
                aria-pressed={statusFilter === "running"}
              >
                Running
              </button>
            </div>

            {/* Session ID filter */}
            <input
              type="text"
              value={sessionIdFilter}
              onChange={(e) => setSessionIdFilter(e.target.value)}
              placeholder="Filter by session ID..."
              className="px-2 py-1 text-sm border border-gray-300 dark:border-gray-600 rounded bg-white dark:bg-gray-700 text-gray-900 dark:text-gray-100 focus:outline-none focus:ring-1 focus:ring-blue-500"
            />

            {/* Time range filter */}
            <select
              value={timeRange}
              onChange={(e) => setTimeRange(e.target.value)}
              className="px-2 py-1 text-sm border border-gray-300 dark:border-gray-600 rounded bg-white dark:bg-gray-700 text-gray-900 dark:text-gray-100 focus:outline-none focus:ring-1 focus:ring-blue-500"
              aria-label="Time range"
            >
              <option value="15m">Last 15 minutes</option>
              <option value="1h">Last 1 hour</option>
              <option value="24h">Last 24 hours</option>
              <option value="7d">Last 7 days</option>
              <option value="all">All time</option>
            </select>

            {/* Trace count */}
            {tracesData && (
              <span className="text-sm text-gray-500 dark:text-gray-400 ml-auto">
                {traces.length} of {tracesData.total} traces
              </span>
            )}
          </div>
        </div>
      )}

      {/* Content */}
      <div className="flex-1 overflow-y-auto p-6">
        {isLoading ? (
          <SkeletonList items={5} />
        ) : error ? (
          <ErrorState
            title="Failed to load data"
            message="There was a problem loading the observability data. Please try again."
            onRetry={handleRefresh}
          />
        ) : (
          <>
            {/* Traces Tab */}
            {activeTab === "traces" && (
              <div className="space-y-4">
                {traces.length === 0 ? (
                  <div className="text-center py-12 text-gray-500 dark:text-gray-400">
                    No traces found
                  </div>
                ) : (
                  <>
                    {traces.map((trace) => (
                      <div
                        key={trace.id}
                        className="p-4 bg-white dark:bg-gray-800 rounded-lg border border-gray-200 dark:border-gray-700 hover:border-blue-500 cursor-pointer transition-colors"
                      >
                        <div className="flex items-center justify-between">
                          <div className="flex items-center gap-3">
                            <Activity size={20} className="text-blue-500" />
                            <div>
                              <h3 className="font-medium text-gray-900 dark:text-gray-100">
                                {trace.name}
                              </h3>
                              <div className="flex items-center gap-3 mt-1 text-sm text-gray-500 dark:text-gray-400">
                                <span className="flex items-center gap-1">
                                  <Clock size={14} />
                                  {trace.duration}ms
                                </span>
                                <span>{trace.spans} spans</span>
                                <span>
                                  {new Date(
                                    trace.timestamp,
                                  ).toLocaleTimeString()}
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
                    ))}
                    {/* Load More Button */}
                    {tracesData?.next_cursor && (
                      <div className="flex justify-center pt-4">
                        <button
                          onClick={() => setCursor(tracesData.next_cursor)}
                          disabled={isTracesFetching}
                          className="flex items-center gap-2 px-4 py-2 bg-gray-100 dark:bg-gray-700 text-gray-700 dark:text-gray-300 rounded-lg hover:bg-gray-200 dark:hover:bg-gray-600 disabled:opacity-50"
                        >
                          {isTracesFetching ? (
                            <>
                              <RefreshCw size={16} className="animate-spin" />
                              Loading...
                            </>
                          ) : (
                            "Load More"
                          )}
                        </button>
                      </div>
                    )}
                  </>
                )}
              </div>
            )}

            {/* Logs Tab */}
            {activeTab === "logs" && (
              <div className="space-y-2">
                {logs.length === 0 ? (
                  <div className="text-center py-12 text-gray-500 dark:text-gray-400">
                    No logs found
                  </div>
                ) : (
                  logs.map((log) => (
                    <div
                      key={log.id}
                      className="p-4 bg-white dark:bg-gray-800 rounded-lg border border-gray-200 dark:border-gray-700"
                    >
                      <div className="flex items-center justify-between">
                        <div className="flex items-center gap-3">
                          <span
                            className={`px-2 py-0.5 text-xs rounded-full ${getLogLevelColor(log.level)}`}
                          >
                            {log.level}
                          </span>
                          <span className="text-gray-900 dark:text-gray-100">
                            {log.message}
                          </span>
                        </div>
                        <div className="flex items-center gap-3 text-sm text-gray-500 dark:text-gray-400">
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
                <div className="p-4 bg-white dark:bg-gray-800 rounded-lg border border-gray-200 dark:border-gray-700">
                  <h3 className="text-sm font-medium text-gray-500 dark:text-gray-400 mb-1">
                    Total Requests
                  </h3>
                  <div className="text-2xl font-semibold text-gray-900 dark:text-gray-100">
                    {metrics.requests_total.toLocaleString()}
                  </div>
                </div>
                <div className="p-4 bg-white dark:bg-gray-800 rounded-lg border border-gray-200 dark:border-gray-700">
                  <h3 className="text-sm font-medium text-gray-500 dark:text-gray-400 mb-1">
                    Total Errors
                  </h3>
                  <div className="text-2xl font-semibold text-red-600 dark:text-red-400">
                    {metrics.errors_total.toLocaleString()}
                  </div>
                </div>
                <div className="p-4 bg-white dark:bg-gray-800 rounded-lg border border-gray-200 dark:border-gray-700">
                  <h3 className="text-sm font-medium text-gray-500 dark:text-gray-400 mb-1">
                    Avg Latency
                  </h3>
                  <div className="text-2xl font-semibold text-gray-900 dark:text-gray-100">
                    {metrics.avg_latency_ms}ms
                  </div>
                </div>
                <div className="p-4 bg-white dark:bg-gray-800 rounded-lg border border-gray-200 dark:border-gray-700">
                  <h3 className="text-sm font-medium text-gray-500 dark:text-gray-400 mb-1">
                    P99 Latency
                  </h3>
                  <div className="text-2xl font-semibold text-gray-900 dark:text-gray-100">
                    {metrics.p99_latency_ms}ms
                  </div>
                </div>
                <div className="p-4 bg-white dark:bg-gray-800 rounded-lg border border-gray-200 dark:border-gray-700">
                  <h3 className="text-sm font-medium text-gray-500 dark:text-gray-400 mb-1">
                    Tokens Used
                  </h3>
                  <div className="text-2xl font-semibold text-gray-900 dark:text-gray-100">
                    {metrics.tokens_used.toLocaleString()}
                  </div>
                </div>
                <div className="p-4 bg-white dark:bg-gray-800 rounded-lg border border-gray-200 dark:border-gray-700">
                  <h3 className="text-sm font-medium text-gray-500 dark:text-gray-400 mb-1">
                    Active Sessions
                  </h3>
                  <div className="text-2xl font-semibold text-gray-900 dark:text-gray-100">
                    {metrics.active_sessions}
                  </div>
                </div>
              </div>
            )}

            {/* Empty metrics state */}
            {activeTab === "metrics" && !metrics && !isMetricsLoading && (
              <div className="text-center py-12 text-gray-500 dark:text-gray-400">
                No metrics data available
              </div>
            )}
          </>
        )}
      </div>
    </div>
  );
}

export default ObservabilityPage;
