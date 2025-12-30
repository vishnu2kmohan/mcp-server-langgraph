/**
 * ObservabilityPage
 *
 * Observability page showing traces, logs, and metrics
 * for agent execution monitoring.
 *
 * Uses RTK Query for data fetching with automatic caching and updates.
 */

import { useState, useEffect, useCallback, useMemo } from "react";
import { useSearchParams, useLocation, useNavigate } from "react-router";
import {
  Activity,
  FileText,
  BarChart3,
  RefreshCw,
  Clock,
  Server,
  AlertTriangle,
  Bell,
  ExternalLink,
  Wifi,
  Bot,
  GitBranch,
  CheckCircle,
  XCircle,
  Sparkles,
  Loader2,
  TrendingUp,
  Zap,
} from "lucide-react";
import {
  useListTracesQuery,
  useListLogsQuery,
  useGetMetricsQuery,
  useGetTraceQuery,
  useListAlertsQuery,
  useListSessionsQuery,
  useListWorkflowsQuery,
  type TraceSpan as ApiTraceSpan,
} from "../api";
import { SkeletonList, ErrorState } from "../components/UI";
import { TraceViewer } from "../components/Observability/TraceViewer";
import { WebSocketMetricsPanel } from "../components/WebSocketMetrics/WebSocketMetricsPanel";
import type { Trace, Span, SpanEvent } from "../components/Observability/types";
import { useAppDispatch, useAppSelector } from "../store/hooks";
import { selectUsername, selectPersona } from "../store/slices/personaSlice";
import {
  useTraceSummary,
  useTraceAnomaly,
} from "../hooks/useTraceIntelligence";
import { useFeatureFlag } from "../contexts/FeatureFlagContext";
import { Tooltip } from "../components/UI/Tooltip";
import {
  setStatusFilter as setStatusFilterAction,
  setSessionIdFilter as setSessionIdFilterAction,
  setUserIdFilter as setUserIdFilterAction,
  setWorkflowIdFilter as setWorkflowIdFilterAction,
  setProjectIdFilter as setProjectIdFilterAction,
  setTimeRange as setTimeRangeAction,
  setActiveTab as setActiveTabAction,
  setSelectedTraceId as setSelectedTraceIdAction,
  selectStatusFilter,
  selectSessionIdFilter,
  selectUserIdFilter,
  selectWorkflowIdFilter,
  selectProjectIdFilter,
  selectTimeRange,
  selectActiveTab,
  selectSelectedTraceId,
} from "../store/slices/observabilitySlice";

type ObservabilityTab =
  | "agent-sessions"
  | "workflow-runs"
  | "traces"
  | "logs"
  | "metrics"
  | "alerts"
  | "ws-metrics";

// Valid tab values
const VALID_TABS = [
  "agent-sessions",
  "workflow-runs",
  "traces",
  "logs",
  "metrics",
  "alerts",
  "ws-metrics",
] as const;

// Extract tab from URL path
function getTabFromPath(pathname: string): ObservabilityTab {
  const segments = pathname.split("/").filter(Boolean);
  const lastSegment = segments[segments.length - 1];
  if (VALID_TABS.includes(lastSegment as ObservabilityTab)) {
    return lastSegment as ObservabilityTab;
  }
  return "agent-sessions"; // default - start with agent sessions
}

export function ObservabilityPage() {
  const [searchParams, setSearchParams] = useSearchParams();
  const location = useLocation();
  const navigate = useNavigate();
  const dispatch = useAppDispatch();

  // Redux state for persistent filters
  const activeTab = useAppSelector(selectActiveTab);
  const statusFilter = useAppSelector(selectStatusFilter);
  const sessionIdFilter = useAppSelector(selectSessionIdFilter);
  const userIdFilter = useAppSelector(selectUserIdFilter);
  const workflowIdFilter = useAppSelector(selectWorkflowIdFilter);
  const projectIdFilter = useAppSelector(selectProjectIdFilter);
  const timeRange = useAppSelector(selectTimeRange);
  const selectedTraceId = useAppSelector(selectSelectedTraceId);

  // Persona context for AI features
  const username = useAppSelector(selectUsername);
  const _persona = useAppSelector(selectPersona);
  const currentUserId = useMemo(
    () => (username ? `user:${username}` : "default-user"),
    [username],
  );

  // Feature flag for AI trace intelligence
  const aiTraceIntelligenceEnabled = useFeatureFlag("ai_suggestions");

  // Trace Intelligence hooks - only active when a trace is selected
  const traceSummary = useTraceSummary({
    userId: currentUserId,
    sessionId: sessionIdFilter || "observability-session",
    traceId: selectedTraceId ?? "",
    enabled: aiTraceIntelligenceEnabled && !!selectedTraceId,
  });

  const traceAnomaly = useTraceAnomaly({
    userId: currentUserId,
    sessionId: sessionIdFilter || "observability-session",
    traceId: selectedTraceId ?? "",
    enabled: aiTraceIntelligenceEnabled && !!selectedTraceId,
  });

  // Pagination cursor (local state - not persisted)
  const [cursor, setCursor] = useState<string | undefined>(undefined);

  // Dispatch helpers (wrap actions for cleaner code)
  const setActiveTab = useCallback(
    (tab: ObservabilityTab) => dispatch(setActiveTabAction(tab)),
    [dispatch],
  );
  const setStatusFilter = (value: string) =>
    dispatch(setStatusFilterAction(value));
  const setSessionIdFilter = (value: string) =>
    dispatch(setSessionIdFilterAction(value));
  const setUserIdFilter = (value: string) =>
    dispatch(setUserIdFilterAction(value));
  const setWorkflowIdFilter = (value: string) =>
    dispatch(setWorkflowIdFilterAction(value));
  const setProjectIdFilter = (value: string) =>
    dispatch(setProjectIdFilterAction(value));
  const setTimeRange = (value: string) => dispatch(setTimeRangeAction(value));
  const setSelectedTraceId = useCallback(
    (value: string | null) => dispatch(setSelectedTraceIdAction(value)),
    [dispatch],
  );

  // Auto-select trace from URL param (for "View Trace" links from ChatPage)
  useEffect(() => {
    const traceIdFromUrl = searchParams.get("trace_id");
    if (traceIdFromUrl && !selectedTraceId) {
      setSelectedTraceId(traceIdFromUrl);
      // Clear the URL param to avoid re-selecting on future renders
      const newParams = new URLSearchParams(searchParams);
      newParams.delete("trace_id");
      setSearchParams(newParams, { replace: true });
    }
  }, [searchParams, selectedTraceId, setSearchParams, setSelectedTraceId]);

  // Sync active tab with URL path
  useEffect(() => {
    const tabFromUrl = getTabFromPath(location.pathname);
    if (tabFromUrl !== activeTab) {
      dispatch(setActiveTabAction(tabFromUrl));
    }
  }, [location.pathname, activeTab, dispatch]);

  // Update URL when tab changes (via user click)
  const handleTabChange = useCallback(
    (tab: ObservabilityTab) => {
      setActiveTab(tab);
      // Construct the new path based on current path structure
      // Remove any existing tab segment from the path
      let basePath = location.pathname.replace(
        /\/(agent-sessions|workflow-runs|traces|logs|metrics|alerts|ws-metrics)$/,
        "",
      );
      // Ensure basePath doesn't end with a slash (except for root "/")
      if (basePath.length > 1 && basePath.endsWith("/")) {
        basePath = basePath.slice(0, -1);
      }
      // Always append the tab segment to ensure proper URL structure
      const newPath = basePath === "/" ? `/${tab}` : `${basePath}/${tab}`;
      navigate(newPath, { replace: true });
    },
    [navigate, location.pathname, setActiveTab],
  );

  // Alerts filter state (local - not persisted)
  const [alertStateFilter, setAlertStateFilter] = useState<string>("");
  const [alertSeverityFilter, setAlertSeverityFilter] = useState<string>("");

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
    user_id: userIdFilter || undefined,
    workflow_id: workflowIdFilter || undefined,
    project_id: projectIdFilter || undefined,
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

  const {
    data: alertsData,
    isLoading: isAlertsLoading,
    error: alertsError,
    refetch: refetchAlerts,
  } = useListAlertsQuery(
    {
      state:
        (alertStateFilter as "pending" | "firing" | "resolved" | "silenced") ||
        undefined,
      severity:
        (alertSeverityFilter as "info" | "warning" | "error" | "critical") ||
        undefined,
      limit: 50,
    },
    { skip: activeTab !== "alerts" },
  );

  // Fetch sessions for agent execution view
  const {
    data: sessionsData,
    isLoading: isSessionsLoading,
    error: sessionsError,
    refetch: refetchSessions,
  } = useListSessionsQuery(
    { limit: 50 },
    { skip: activeTab !== "agent-sessions" },
  );

  // Fetch workflows for workflow runs view
  const {
    data: workflowsData,
    isLoading: isWorkflowsLoading,
    error: workflowsError,
    refetch: refetchWorkflows,
  } = useListWorkflowsQuery(
    { limit: 50 },
    { skip: activeTab !== "workflow-runs" },
  );

  // Fetch selected trace details
  const { data: selectedTraceData, isLoading: isTraceDetailLoading } =
    useGetTraceQuery(selectedTraceId ?? "", {
      skip: !selectedTraceId,
    });

  // Map API trace to TraceViewer format
  const selectedTrace: Trace | null = selectedTraceData
    ? {
        trace_id: selectedTraceData.trace_id,
        spans:
          selectedTraceData.spans?.map(
            (span: ApiTraceSpan, idx: number): Span => ({
              span_id: span.span_id || `span-${idx}`,
              name: span.name || "Unknown",
              start_time: new Date(span.start_time).getTime(),
              duration_ms: span.duration_ms || 0,
              status: span.status as "ok" | "error" | "unset",
              depth: span.depth || 0,
              attributes: span.attributes || {},
              events: (span.events as SpanEvent[]) || [],
              error_message: span.error_message ?? undefined,
              parent_span_id: span.parent_span_id ?? undefined,
            }),
          ) || [],
        start_time: selectedTraceData.start_time
          ? new Date(selectedTraceData.start_time).getTime()
          : Date.now(),
        end_time: selectedTraceData.end_time
          ? new Date(selectedTraceData.end_time).getTime()
          : Date.now(),
        duration_ms: selectedTraceData.duration_ms ?? 0,
        service_name: selectedTraceData.service_name,
      }
    : null;

  // Map traces to component format
  const traces =
    tracesData?.items.map((trace) => ({
      id: trace.trace_id,
      name: trace.name,
      duration: trace.duration_ms ?? 0,
      status: (trace.status ?? "success") as "success" | "error" | "running",
      timestamp: trace.start_time ?? new Date().toISOString(),
      spans: trace.span_count ?? 0,
    })) ?? [];

  // Map logs to component format
  const logs = logsData?.items ?? [];

  // Metrics data
  const metrics = metricsData ?? null;

  // Alerts data
  const alerts = alertsData?.items ?? [];

  const tabs = [
    { id: "agent-sessions" as const, label: "Agent Sessions", icon: Bot },
    { id: "workflow-runs" as const, label: "Workflow Runs", icon: GitBranch },
    { id: "traces" as const, label: "Distributed Traces", icon: Activity },
    { id: "logs" as const, label: "Logs", icon: FileText },
    { id: "metrics" as const, label: "Metrics", icon: BarChart3 },
    { id: "alerts" as const, label: "Alerts", icon: Bell },
    { id: "ws-metrics" as const, label: "WS Metrics", icon: Wifi },
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

  const getAlertSeverityColor = (
    severity: "info" | "warning" | "error" | "critical",
  ) => {
    switch (severity) {
      case "critical":
        return "bg-red-100 text-red-800 dark:bg-red-900/30 dark:text-red-400";
      case "error":
        return "bg-orange-100 text-orange-800 dark:bg-orange-900/30 dark:text-orange-400";
      case "warning":
        return "bg-yellow-100 text-yellow-800 dark:bg-yellow-900/30 dark:text-yellow-400";
      case "info":
        return "bg-blue-100 text-blue-800 dark:bg-blue-900/30 dark:text-blue-400";
    }
  };

  const getAlertStateColor = (
    state: "pending" | "firing" | "resolved" | "silenced",
  ) => {
    switch (state) {
      case "firing":
        return "bg-red-100 text-red-800 dark:bg-red-900/30 dark:text-red-400";
      case "pending":
        return "bg-yellow-100 text-yellow-800 dark:bg-yellow-900/30 dark:text-yellow-400";
      case "resolved":
        return "bg-green-100 text-green-800 dark:bg-green-900/30 dark:text-green-400";
      case "silenced":
        return "bg-gray-100 text-gray-800 dark:bg-gray-900/30 dark:text-gray-400";
    }
  };

  const isLoading =
    activeTab === "agent-sessions"
      ? isSessionsLoading
      : activeTab === "workflow-runs"
        ? isWorkflowsLoading
        : activeTab === "traces"
          ? isTracesLoading
          : activeTab === "logs"
            ? isLogsLoading
            : activeTab === "alerts"
              ? isAlertsLoading
              : activeTab === "metrics"
                ? isMetricsLoading
                : false;

  const error =
    activeTab === "agent-sessions"
      ? sessionsError
      : activeTab === "workflow-runs"
        ? workflowsError
        : activeTab === "traces"
          ? tracesError
          : activeTab === "logs"
            ? logsError
            : activeTab === "alerts"
              ? alertsError
              : activeTab === "metrics"
                ? metricsError
                : null;

  const handleRefresh = () => {
    if (activeTab === "agent-sessions") refetchSessions();
    else if (activeTab === "workflow-runs") refetchWorkflows();
    else if (activeTab === "traces") refetchTraces();
    else if (activeTab === "logs") refetchLogs();
    else if (activeTab === "alerts") refetchAlerts();
    else if (activeTab === "metrics") refetchMetrics();
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
              onClick={() => handleTabChange(tab.id)}
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

            {/* Entity ID filters */}
            <div className="flex items-center gap-2">
              <input
                type="text"
                value={sessionIdFilter}
                onChange={(e) => setSessionIdFilter(e.target.value)}
                placeholder="Session ID"
                className="w-32 px-2 py-1 text-sm border border-gray-300 dark:border-gray-600 rounded bg-white dark:bg-gray-700 text-gray-900 dark:text-gray-100 focus:outline-none focus:ring-1 focus:ring-blue-500"
                aria-label="Filter by session ID"
              />
              <input
                type="text"
                value={userIdFilter}
                onChange={(e) => setUserIdFilter(e.target.value)}
                placeholder="User ID"
                className="w-32 px-2 py-1 text-sm border border-gray-300 dark:border-gray-600 rounded bg-white dark:bg-gray-700 text-gray-900 dark:text-gray-100 focus:outline-none focus:ring-1 focus:ring-blue-500"
                aria-label="Filter by user ID"
              />
              <input
                type="text"
                value={workflowIdFilter}
                onChange={(e) => setWorkflowIdFilter(e.target.value)}
                placeholder="Workflow ID"
                className="w-32 px-2 py-1 text-sm border border-gray-300 dark:border-gray-600 rounded bg-white dark:bg-gray-700 text-gray-900 dark:text-gray-100 focus:outline-none focus:ring-1 focus:ring-blue-500"
                aria-label="Filter by workflow ID"
              />
              <input
                type="text"
                value={projectIdFilter}
                onChange={(e) => setProjectIdFilter(e.target.value)}
                placeholder="Project ID"
                className="w-32 px-2 py-1 text-sm border border-gray-300 dark:border-gray-600 rounded bg-white dark:bg-gray-700 text-gray-900 dark:text-gray-100 focus:outline-none focus:ring-1 focus:ring-blue-500"
                aria-label="Filter by project ID"
              />
            </div>

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
            {/* Agent Sessions Tab */}
            {activeTab === "agent-sessions" && (
              <div className="space-y-4">
                {!sessionsData?.items || sessionsData.items.length === 0 ? (
                  <div className="text-center py-12 text-gray-500 dark:text-gray-400">
                    <Bot size={48} className="mx-auto mb-4 opacity-50" />
                    <p>No agent sessions found</p>
                    <p className="text-sm mt-2">
                      Agent sessions will appear here when you start new
                      conversations
                    </p>
                  </div>
                ) : (
                  sessionsData.items.map((session) => (
                    <div
                      key={session.id}
                      className="p-4 bg-white dark:bg-gray-800 rounded-lg border border-gray-200 dark:border-gray-700 hover:border-blue-500 transition-colors cursor-pointer"
                      onClick={() =>
                        window.open(`/studio/chat/${session.id}`, "_blank")
                      }
                    >
                      <div className="flex items-center justify-between">
                        <div className="flex items-center gap-3">
                          <Bot size={20} className="text-purple-500" />
                          <div>
                            <h3 className="font-medium text-gray-900 dark:text-gray-100">
                              {session.name || "Untitled Session"}
                            </h3>
                            <div className="flex items-center gap-3 mt-1 text-sm text-gray-500 dark:text-gray-400">
                              <span className="flex items-center gap-1">
                                <Clock size={14} />
                                {new Date(session.created_at).toLocaleString()}
                              </span>
                              <span className="font-mono text-xs">
                                {session.id.slice(0, 8)}...
                              </span>
                            </div>
                          </div>
                        </div>
                        <div className="flex items-center gap-2">
                          {session.status === "active" ? (
                            <span className="flex items-center gap-1 px-2 py-1 text-xs rounded-full bg-green-100 text-green-700 dark:bg-green-900/30 dark:text-green-400">
                              <CheckCircle size={12} />
                              Active
                            </span>
                          ) : session.status === "archived" ? (
                            <span className="flex items-center gap-1 px-2 py-1 text-xs rounded-full bg-yellow-100 text-yellow-700 dark:bg-yellow-900/30 dark:text-yellow-400">
                              <Clock size={12} />
                              Archived
                            </span>
                          ) : (
                            <span className="flex items-center gap-1 px-2 py-1 text-xs rounded-full bg-gray-100 text-gray-700 dark:bg-gray-900/30 dark:text-gray-400">
                              <XCircle size={12} />
                              {session.status}
                            </span>
                          )}
                          <ExternalLink size={16} className="text-gray-400" />
                        </div>
                      </div>
                    </div>
                  ))
                )}
              </div>
            )}

            {/* Workflow Runs Tab */}
            {activeTab === "workflow-runs" && (
              <div className="space-y-4">
                {!workflowsData?.items || workflowsData.items.length === 0 ? (
                  <div className="text-center py-12 text-gray-500 dark:text-gray-400">
                    <GitBranch size={48} className="mx-auto mb-4 opacity-50" />
                    <p>No workflow runs found</p>
                    <p className="text-sm mt-2">
                      Workflow executions will appear here when you run
                      workflows
                    </p>
                  </div>
                ) : (
                  workflowsData.items.map((workflow) => (
                    <div
                      key={workflow.id}
                      className="p-4 bg-white dark:bg-gray-800 rounded-lg border border-gray-200 dark:border-gray-700 hover:border-blue-500 transition-colors cursor-pointer"
                      onClick={() =>
                        window.open(
                          `/studio/workflows/${workflow.id}`,
                          "_blank",
                        )
                      }
                    >
                      <div className="flex items-center justify-between">
                        <div className="flex items-center gap-3">
                          <GitBranch size={20} className="text-emerald-500" />
                          <div>
                            <h3 className="font-medium text-gray-900 dark:text-gray-100">
                              {workflow.name}
                            </h3>
                            <div className="flex items-center gap-3 mt-1 text-sm text-gray-500 dark:text-gray-400">
                              <span className="flex items-center gap-1">
                                <Clock size={14} />
                                {new Date(workflow.created_at).toLocaleString()}
                              </span>
                              {workflow.description && (
                                <span className="truncate max-w-xs">
                                  {workflow.description}
                                </span>
                              )}
                            </div>
                          </div>
                        </div>
                        <div className="flex items-center gap-2">
                          <span className="flex items-center gap-1 px-2 py-1 text-xs rounded-full bg-blue-100 text-blue-700 dark:bg-blue-900/30 dark:text-blue-400">
                            <Activity size={12} />
                            {workflow.node_count} nodes
                          </span>
                          <span className="flex items-center gap-1 px-2 py-1 text-xs rounded-full bg-gray-100 text-gray-700 dark:bg-gray-900/30 dark:text-gray-400">
                            {workflow.edge_count} edges
                          </span>
                          <ExternalLink size={16} className="text-gray-400" />
                        </div>
                      </div>
                    </div>
                  ))
                )}
              </div>
            )}

            {/* Distributed Traces Tab */}
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
                        onClick={() => setSelectedTraceId(trace.id)}
                        className={`p-4 bg-white dark:bg-gray-800 rounded-lg border transition-colors cursor-pointer ${
                          selectedTraceId === trace.id
                            ? "border-blue-500 ring-2 ring-blue-200 dark:ring-blue-800"
                            : "border-gray-200 dark:border-gray-700 hover:border-blue-500"
                        }`}
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

                    {/* TraceViewer Panel (Developer journey - trace debugging) */}
                    {selectedTraceId && (
                      <div className="mt-6 bg-white dark:bg-gray-800 rounded-lg border border-gray-200 dark:border-gray-700 overflow-hidden">
                        <div className="flex items-center justify-between px-4 py-2 border-b border-gray-200 dark:border-gray-700 bg-gray-50 dark:bg-gray-900">
                          <span className="text-sm font-medium text-gray-700 dark:text-gray-300">
                            Trace Details
                          </span>
                          <button
                            onClick={() => setSelectedTraceId(null)}
                            className="text-sm text-gray-500 hover:text-gray-700 dark:text-gray-400 dark:hover:text-gray-200"
                          >
                            Close
                          </button>
                        </div>
                        <TraceViewer
                          trace={selectedTrace}
                          isLoading={isTraceDetailLoading}
                          grafanaUrl={
                            selectedTraceId
                              ? `${window.location.origin}/grafana/explore?traceId=${selectedTraceId}`
                              : undefined
                          }
                        />

                        {/* AI Trace Intelligence Panel */}
                        {aiTraceIntelligenceEnabled && (
                          <div
                            data-testid="trace-intelligence-panel"
                            className="border-t border-gray-200 dark:border-gray-700"
                          >
                            <div className="px-4 py-2 bg-gradient-to-r from-purple-50 to-blue-50 dark:from-purple-900/20 dark:to-blue-900/20 border-b border-gray-200 dark:border-gray-700">
                              <div className="flex items-center gap-2">
                                <Sparkles
                                  size={16}
                                  className="text-purple-500"
                                />
                                <span className="text-sm font-medium text-gray-700 dark:text-gray-300">
                                  AI Insights
                                </span>
                              </div>
                            </div>

                            <div className="p-4 grid grid-cols-1 lg:grid-cols-2 gap-4">
                              {/* Trace Summary */}
                              <div className="space-y-2">
                                <h4 className="text-xs font-medium text-gray-500 dark:text-gray-400 uppercase tracking-wider">
                                  Summary
                                </h4>
                                {traceSummary.isLoading ? (
                                  <div className="flex items-center gap-2 text-sm text-gray-400">
                                    <Loader2
                                      size={14}
                                      className="animate-spin"
                                    />
                                    <span>Analyzing trace...</span>
                                  </div>
                                ) : traceSummary.summary ? (
                                  <div className="space-y-2">
                                    <p className="text-sm text-gray-700 dark:text-gray-300">
                                      {traceSummary.summary}
                                    </p>
                                    {traceSummary.keyActions.length > 0 && (
                                      <div className="flex flex-wrap gap-1">
                                        {traceSummary.keyActions.map(
                                          (action, idx) => (
                                            <span
                                              key={idx}
                                              className="px-2 py-0.5 text-xs bg-blue-100 dark:bg-blue-900/30 text-blue-700 dark:text-blue-300 rounded"
                                            >
                                              {action}
                                            </span>
                                          ),
                                        )}
                                      </div>
                                    )}
                                    <div className="flex items-center gap-4 text-xs text-gray-500 dark:text-gray-400">
                                      {traceSummary.stepCount !== null && (
                                        <span>
                                          {traceSummary.stepCount} steps
                                        </span>
                                      )}
                                      {traceSummary.toolCallCount !== null && (
                                        <span>
                                          {traceSummary.toolCallCount} tool
                                          calls
                                        </span>
                                      )}
                                      {traceSummary.totalDurationMs !==
                                        null && (
                                        <span>
                                          {traceSummary.totalDurationMs}ms total
                                        </span>
                                      )}
                                    </div>
                                  </div>
                                ) : (
                                  <p className="text-sm text-gray-400">
                                    No summary available
                                  </p>
                                )}
                              </div>

                              {/* Anomaly Detection */}
                              <div className="space-y-2">
                                <h4 className="text-xs font-medium text-gray-500 dark:text-gray-400 uppercase tracking-wider">
                                  Health & Anomalies
                                </h4>
                                {traceAnomaly.isLoading ? (
                                  <div className="flex items-center gap-2 text-sm text-gray-400">
                                    <Loader2
                                      size={14}
                                      className="animate-spin"
                                    />
                                    <span>Detecting anomalies...</span>
                                  </div>
                                ) : (
                                  <div className="space-y-2">
                                    {/* Health Score */}
                                    {traceAnomaly.healthScore !== null && (
                                      <div className="flex items-center gap-2">
                                        <span className="text-sm text-gray-600 dark:text-gray-400">
                                          Health:
                                        </span>
                                        <span
                                          className={`text-sm font-medium ${
                                            traceAnomaly.healthScore >= 80
                                              ? "text-green-600 dark:text-green-400"
                                              : traceAnomaly.healthScore >= 60
                                                ? "text-yellow-600 dark:text-yellow-400"
                                                : "text-red-600 dark:text-red-400"
                                          }`}
                                        >
                                          {traceAnomaly.healthScore}/100
                                        </span>
                                      </div>
                                    )}

                                    {/* Bottlenecks */}
                                    {traceAnomaly.bottlenecks.length > 0 && (
                                      <div className="space-y-1">
                                        <span className="text-xs text-gray-500 dark:text-gray-400 flex items-center gap-1">
                                          <Zap size={12} />
                                          Bottlenecks:
                                        </span>
                                        {traceAnomaly.bottlenecks
                                          .slice(0, 3)
                                          .map((bottleneck, idx) => (
                                            <Tooltip
                                              key={idx}
                                              content={`${bottleneck.duration_ms}ms (${bottleneck.percentage_of_total}% of total)`}
                                              position="top"
                                            >
                                              <span className="inline-block px-2 py-0.5 text-xs bg-orange-100 dark:bg-orange-900/30 text-orange-700 dark:text-orange-300 rounded cursor-help">
                                                {bottleneck.step_name}
                                              </span>
                                            </Tooltip>
                                          ))}
                                      </div>
                                    )}

                                    {/* Anomalies */}
                                    {traceAnomaly.anomalies.length > 0 && (
                                      <div className="space-y-1">
                                        <span className="text-xs text-gray-500 dark:text-gray-400 flex items-center gap-1">
                                          <AlertTriangle size={12} />
                                          Issues:
                                        </span>
                                        {traceAnomaly.anomalies
                                          .slice(0, 3)
                                          .map((anomaly, idx) => (
                                            <Tooltip
                                              key={idx}
                                              content={
                                                anomaly.suggested_fix ||
                                                anomaly.message
                                              }
                                              position="top"
                                            >
                                              <div
                                                className={`text-xs px-2 py-1 rounded cursor-help ${
                                                  anomaly.severity === "error"
                                                    ? "bg-red-100 dark:bg-red-900/30 text-red-700 dark:text-red-300"
                                                    : anomaly.severity ===
                                                        "warning"
                                                      ? "bg-yellow-100 dark:bg-yellow-900/30 text-yellow-700 dark:text-yellow-300"
                                                      : "bg-blue-100 dark:bg-blue-900/30 text-blue-700 dark:text-blue-300"
                                                }`}
                                              >
                                                {anomaly.step_name}:{" "}
                                                {anomaly.message}
                                              </div>
                                            </Tooltip>
                                          ))}
                                      </div>
                                    )}

                                    {/* Optimization Suggestions */}
                                    {traceAnomaly.optimizationSuggestions
                                      .length > 0 && (
                                      <div className="space-y-1">
                                        <span className="text-xs text-gray-500 dark:text-gray-400 flex items-center gap-1">
                                          <TrendingUp size={12} />
                                          Suggestions:
                                        </span>
                                        <ul className="text-xs text-gray-600 dark:text-gray-400 list-disc list-inside">
                                          {traceAnomaly.optimizationSuggestions
                                            .slice(0, 3)
                                            .map((suggestion, idx) => (
                                              <li key={idx}>{suggestion}</li>
                                            ))}
                                        </ul>
                                      </div>
                                    )}

                                    {traceAnomaly.anomalies.length === 0 &&
                                      traceAnomaly.bottlenecks.length === 0 && (
                                        <p className="text-sm text-green-600 dark:text-green-400 flex items-center gap-1">
                                          <TrendingUp size={14} />
                                          No issues detected
                                        </p>
                                      )}
                                  </div>
                                )}
                              </div>
                            </div>
                          </div>
                        )}
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
                    {(metrics.requests_total ?? 0).toLocaleString()}
                  </div>
                </div>
                <div className="p-4 bg-white dark:bg-gray-800 rounded-lg border border-gray-200 dark:border-gray-700">
                  <h3 className="text-sm font-medium text-gray-500 dark:text-gray-400 mb-1">
                    Total Errors
                  </h3>
                  <div className="text-2xl font-semibold text-red-600 dark:text-red-400">
                    {(metrics.errors_total ?? 0).toLocaleString()}
                  </div>
                </div>
                <div className="p-4 bg-white dark:bg-gray-800 rounded-lg border border-gray-200 dark:border-gray-700">
                  <h3 className="text-sm font-medium text-gray-500 dark:text-gray-400 mb-1">
                    Avg Latency
                  </h3>
                  <div className="text-2xl font-semibold text-gray-900 dark:text-gray-100">
                    {metrics.avg_latency_ms ?? 0}ms
                  </div>
                </div>
                <div className="p-4 bg-white dark:bg-gray-800 rounded-lg border border-gray-200 dark:border-gray-700">
                  <h3 className="text-sm font-medium text-gray-500 dark:text-gray-400 mb-1">
                    P99 Latency
                  </h3>
                  <div className="text-2xl font-semibold text-gray-900 dark:text-gray-100">
                    {metrics.p99_latency_ms ?? 0}ms
                  </div>
                </div>
                <div className="p-4 bg-white dark:bg-gray-800 rounded-lg border border-gray-200 dark:border-gray-700">
                  <h3 className="text-sm font-medium text-gray-500 dark:text-gray-400 mb-1">
                    Tokens Used
                  </h3>
                  <div className="text-2xl font-semibold text-gray-900 dark:text-gray-100">
                    {(metrics.tokens_used ?? 0).toLocaleString()}
                  </div>
                </div>
                <div className="p-4 bg-white dark:bg-gray-800 rounded-lg border border-gray-200 dark:border-gray-700">
                  <h3 className="text-sm font-medium text-gray-500 dark:text-gray-400 mb-1">
                    Active Sessions
                  </h3>
                  <div className="text-2xl font-semibold text-gray-900 dark:text-gray-100">
                    {metrics.active_sessions ?? 0}
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

            {/* WS Metrics Tab */}
            {activeTab === "ws-metrics" && (
              <div className="h-full -m-6">
                <WebSocketMetricsPanel className="h-full" />
              </div>
            )}

            {/* Alerts Tab */}
            {activeTab === "alerts" && (
              <div className="space-y-4">
                {/* Alerts Filters */}
                <div className="flex items-center gap-4 flex-wrap p-4 bg-white dark:bg-gray-800 rounded-lg border border-gray-200 dark:border-gray-700">
                  {/* State filter */}
                  <div className="flex items-center gap-2">
                    <span className="text-sm text-gray-500 dark:text-gray-400">
                      State:
                    </span>
                    <div className="flex items-center gap-1">
                      <button
                        onClick={() => setAlertStateFilter("")}
                        className={`px-2 py-1 text-xs rounded ${
                          alertStateFilter === ""
                            ? "bg-blue-600 text-white"
                            : "bg-gray-100 dark:bg-gray-700 text-gray-700 dark:text-gray-300 hover:bg-gray-200 dark:hover:bg-gray-600"
                        }`}
                      >
                        All
                      </button>
                      <button
                        onClick={() => setAlertStateFilter("firing")}
                        className={`px-2 py-1 text-xs rounded ${
                          alertStateFilter === "firing"
                            ? "bg-red-600 text-white"
                            : "bg-gray-100 dark:bg-gray-700 text-gray-700 dark:text-gray-300 hover:bg-gray-200 dark:hover:bg-gray-600"
                        }`}
                      >
                        Firing
                      </button>
                      <button
                        onClick={() => setAlertStateFilter("pending")}
                        className={`px-2 py-1 text-xs rounded ${
                          alertStateFilter === "pending"
                            ? "bg-yellow-600 text-white"
                            : "bg-gray-100 dark:bg-gray-700 text-gray-700 dark:text-gray-300 hover:bg-gray-200 dark:hover:bg-gray-600"
                        }`}
                      >
                        Pending
                      </button>
                      <button
                        onClick={() => setAlertStateFilter("resolved")}
                        className={`px-2 py-1 text-xs rounded ${
                          alertStateFilter === "resolved"
                            ? "bg-green-600 text-white"
                            : "bg-gray-100 dark:bg-gray-700 text-gray-700 dark:text-gray-300 hover:bg-gray-200 dark:hover:bg-gray-600"
                        }`}
                      >
                        Resolved
                      </button>
                    </div>
                  </div>

                  {/* Severity filter */}
                  <div className="flex items-center gap-2">
                    <span className="text-sm text-gray-500 dark:text-gray-400">
                      Severity:
                    </span>
                    <select
                      value={alertSeverityFilter}
                      onChange={(e) => setAlertSeverityFilter(e.target.value)}
                      className="px-2 py-1 text-sm border border-gray-300 dark:border-gray-600 rounded bg-white dark:bg-gray-700 text-gray-900 dark:text-gray-100 focus:outline-none focus:ring-1 focus:ring-blue-500"
                    >
                      <option value="">All Severities</option>
                      <option value="critical">Critical</option>
                      <option value="error">Error</option>
                      <option value="warning">Warning</option>
                      <option value="info">Info</option>
                    </select>
                  </div>

                  {/* Alert count */}
                  {alertsData && (
                    <span className="text-sm text-gray-500 dark:text-gray-400 ml-auto">
                      {alerts.length} alerts
                    </span>
                  )}
                </div>

                {/* Alerts List */}
                {alerts.length === 0 ? (
                  <div className="text-center py-12 text-gray-500 dark:text-gray-400">
                    <AlertTriangle
                      size={48}
                      className="mx-auto mb-4 opacity-50"
                    />
                    <p>No alerts found</p>
                    <p className="text-sm mt-2">
                      Active alerts from Grafana Alerting will appear here
                    </p>
                  </div>
                ) : (
                  alerts.map((alert) => (
                    <div
                      key={alert.alert_id}
                      className="p-4 bg-white dark:bg-gray-800 rounded-lg border border-gray-200 dark:border-gray-700 hover:border-blue-500 transition-colors"
                    >
                      <div className="flex items-start justify-between">
                        <div className="flex items-start gap-3">
                          <AlertTriangle
                            size={20}
                            className={
                              alert.severity === "critical"
                                ? "text-red-500"
                                : alert.severity === "error"
                                  ? "text-orange-500"
                                  : alert.severity === "warning"
                                    ? "text-yellow-500"
                                    : "text-blue-500"
                            }
                          />
                          <div>
                            <h3 className="font-medium text-gray-900 dark:text-gray-100">
                              {alert.name}
                            </h3>
                            <p className="text-sm text-gray-600 dark:text-gray-400 mt-1">
                              {alert.message ||
                                alert.annotations?.summary ||
                                "No description"}
                            </p>
                            <div className="flex items-center gap-3 mt-2 text-sm text-gray-500 dark:text-gray-400">
                              {alert.started_at && (
                                <span className="flex items-center gap-1">
                                  <Clock size={14} />
                                  Started{" "}
                                  {new Date(alert.started_at).toLocaleString()}
                                </span>
                              )}
                              {alert.labels?.service && (
                                <span className="flex items-center gap-1">
                                  <Server size={14} />
                                  {alert.labels.service}
                                </span>
                              )}
                            </div>
                          </div>
                        </div>
                        <div className="flex items-center gap-2">
                          <span
                            className={`px-2 py-1 text-xs rounded-full ${getAlertSeverityColor(alert.severity)}`}
                          >
                            {alert.severity}
                          </span>
                          <span
                            className={`px-2 py-1 text-xs rounded-full ${getAlertStateColor(alert.state)}`}
                          >
                            {alert.state}
                          </span>
                          {alert.generator_url && (
                            <a
                              href={alert.generator_url}
                              target="_blank"
                              rel="noopener noreferrer"
                              className="p-1 text-gray-400 hover:text-blue-500 transition-colors"
                              title="View in Grafana"
                            >
                              <ExternalLink size={16} />
                            </a>
                          )}
                        </div>
                      </div>

                      {/* Labels */}
                      {Object.keys(alert.labels).length > 0 && (
                        <div className="mt-3 flex flex-wrap gap-1">
                          {Object.entries(alert.labels)
                            .filter(
                              ([key]) =>
                                !["alertname", "severity"].includes(key),
                            )
                            .slice(0, 5)
                            .map(([key, value]) => (
                              <span
                                key={key}
                                className="px-2 py-0.5 text-xs bg-gray-100 dark:bg-gray-700 text-gray-600 dark:text-gray-400 rounded"
                              >
                                {key}={value}
                              </span>
                            ))}
                        </div>
                      )}
                    </div>
                  ))
                )}
              </div>
            )}
          </>
        )}
      </div>
    </div>
  );
}

export default ObservabilityPage;
