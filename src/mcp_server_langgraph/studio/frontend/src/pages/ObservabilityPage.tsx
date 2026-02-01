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
  type TraceSpanCamelCase as ApiTraceSpan,
} from "../api";
// Direct imports to avoid Rollup circular dependency warnings
// (page chunks end up separate from UI barrel)
import { SkeletonList } from "../components/UI/Skeleton";
import { ErrorState } from "../components/UI/ErrorState";
import { Button } from "../components/UI/Button";
import { Input } from "../components/UI/Input";
import { Select } from "../components/UI/Select";
import { TraceViewer } from "../components/Observability/TraceViewer";
import {
  WebSocketMetricsPanel,
  WebSocketHealthIndicator,
} from "../components/WebSocketMetrics";
import { TraceCanvas } from "../components/Trace";
import type { Trace, Span, SpanEvent } from "../components/Observability/types";
import { useAppDispatch, useAppSelector } from "../store/hooks";
import { selectUsername, selectPersona } from "../store/slices/personaSlice";
import {
  useTraceSummary,
  useTraceAnomaly,
} from "../hooks/useTraceIntelligence";
import { useFeatureFlag } from "../contexts/FeatureFlagContext";
import { Tooltip } from "../components/UI/Tooltip";
import { OBSERVABILITY_POLLING_CONFIG } from "../config/observability";
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

const {
  traceListActiveMs,
  traceListIdleMs,
  traceDetailMs,
  metricsMs,
  logsMs,
  alertsMs,
} = OBSERVABILITY_POLLING_CONFIG;

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

  // TraceCanvas state (real-time trace visualization)
  const [showTraceCanvas, setShowTraceCanvas] = useState(false);
  const [hasActiveTraces, setHasActiveTraces] = useState(false);
  const [selectedTraceComplete, setSelectedTraceComplete] = useState(false);

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

  const isTracesTabActive = activeTab === "traces";
  const traceListPollingInterval = isTracesTabActive
    ? hasActiveTraces
      ? traceListActiveMs
      : traceListIdleMs
    : 0;
  const traceDetailPollingInterval =
    isTracesTabActive && selectedTraceId && !selectedTraceComplete
      ? traceDetailMs
      : 0;

  // Fetch data with RTK Query - skip based on active tab for lazy loading
  const {
    data: tracesData,
    isLoading: isTracesLoading,
    isFetching: isTracesFetching,
    error: tracesError,
    refetch: refetchTraces,
  } = useListTracesQuery(
    {
      limit: 50,
      status: statusFilter || undefined,
      session_id: sessionIdFilter || undefined,
      user_id: userIdFilter || undefined,
      workflow_id: workflowIdFilter || undefined,
      project_id: projectIdFilter || undefined,
      start_time: getTimeRange(),
      cursor,
    },
    {
      skip: activeTab !== "traces",
      pollingInterval: traceListPollingInterval,
      refetchOnFocus: true,
      refetchOnReconnect: true,
    },
  );

  const {
    data: logsData,
    isLoading: isLogsLoading,
    error: logsError,
    refetch: refetchLogs,
  } = useListLogsQuery(
    { limit: 50 },
    {
      skip: activeTab !== "logs",
      pollingInterval: activeTab === "logs" ? logsMs : 0,
      refetchOnFocus: true,
      refetchOnReconnect: true,
    },
  );

  const {
    data: metricsData,
    isLoading: isMetricsLoading,
    error: metricsError,
    refetch: refetchMetrics,
  } = useGetMetricsQuery(undefined, {
    skip: activeTab !== "metrics",
    pollingInterval: activeTab === "metrics" ? metricsMs : 0,
    refetchOnFocus: true,
    refetchOnReconnect: true,
  });

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
    {
      skip: activeTab !== "alerts",
      pollingInterval: activeTab === "alerts" ? alertsMs : 0,
      refetchOnFocus: true,
      refetchOnReconnect: true,
    },
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
      pollingInterval: traceDetailPollingInterval,
      refetchOnFocus: true,
      refetchOnReconnect: true,
    });

  const nextHasActiveTraces = useMemo(() => {
    if (!tracesData?.items?.length) return false;
    return tracesData.items.some((trace) => {
      const status = trace.status?.toLowerCase();
      const isRunningStatus = status === "running" || status === "unset";
      const hasNoEndTime = !trace.endTime;
      const hasNoDuration = trace.durationMs == null;
      return isRunningStatus || (hasNoEndTime && hasNoDuration);
    });
  }, [tracesData]);

  const nextSelectedTraceComplete = useMemo(() => {
    if (!selectedTraceId || !selectedTraceData) return false;
    if (selectedTraceData.endTime) return true;
    if (!selectedTraceData.spans?.length) return false;
    return selectedTraceData.spans.every((span) => Boolean(span.endTime));
  }, [selectedTraceData, selectedTraceId]);

  useEffect(() => {
    setHasActiveTraces((prev) =>
      prev === nextHasActiveTraces ? prev : nextHasActiveTraces,
    );
  }, [nextHasActiveTraces]);

  useEffect(() => {
    setSelectedTraceComplete((prev) =>
      prev === nextSelectedTraceComplete ? prev : nextSelectedTraceComplete,
    );
  }, [nextSelectedTraceComplete]);

  // Map API trace to TraceViewer format
  const selectedTrace: Trace | null = selectedTraceData
    ? {
        traceId: selectedTraceData.traceId,
        spans:
          selectedTraceData.spans?.map(
            (span: ApiTraceSpan, idx: number): Span => ({
              spanId: span.spanId || `span-${idx}`,
              name: span.name || "Unknown",
              startTime: new Date(span.startTime).getTime(),
              durationMs: span.durationMs || 0,
              status: span.status as "ok" | "error" | "unset",
              depth: span.depth || 0,
              attributes: span.attributes || {},
              events: (span.events as SpanEvent[]) || [],
              errorMessage: span.errorMessage ?? undefined,
              parentSpanId: span.parentSpanId ?? undefined,
            }),
          ) || [],
        startTime: selectedTraceData.startTime
          ? new Date(selectedTraceData.startTime).getTime()
          : Date.now(),
        endTime: selectedTraceData.endTime
          ? new Date(selectedTraceData.endTime).getTime()
          : Date.now(),
        durationMs: selectedTraceData.durationMs ?? 0,
        serviceName: selectedTraceData.serviceName,
      }
    : null;

  // Map traces to component format
  const traces =
    tracesData?.items.map((trace) => ({
      id: trace.traceId,
      name: trace.name,
      duration: trace.durationMs ?? 0,
      status: (trace.status ?? "success") as "success" | "error" | "running",
      timestamp: trace.startTime ?? new Date().toISOString(),
      spans: trace.spanCount ?? 0,
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
        return "bg-error-3 text-error-11 bg-error-4";
      case "warn":
        return "bg-warning-3 text-warning-10/30";
      case "info":
        return "bg-primary-3 text-primary-11 bg-primary-4";
      case "debug":
        return "bg-neutral-2 text-neutral-10/30";
    }
  };

  const getStatusColor = (status: "success" | "error" | "running") => {
    switch (status) {
      case "success":
        return "bg-success-3 text-success-11 bg-success-4";
      case "error":
        return "bg-error-3 text-error-11 bg-error-4";
      case "running":
        return "bg-primary-3 text-primary-11 bg-primary-4";
    }
  };

  const getAlertSeverityColor = (
    severity: "info" | "warning" | "error" | "critical",
  ) => {
    switch (severity) {
      case "critical":
        return "bg-error-3 text-error-11 bg-error-4";
      case "error":
        return "bg-grafana-2 text-grafana-11";
      case "warning":
        return "bg-warning-3 text-warning-11/30";
      case "info":
        return "bg-primary-3 text-primary-11 bg-primary-4";
    }
  };

  const getAlertStateColor = (
    state: "pending" | "firing" | "resolved" | "silenced",
  ) => {
    switch (state) {
      case "firing":
        return "bg-error-3 text-error-11 bg-error-4";
      case "pending":
        return "bg-warning-3 text-warning-11/30";
      case "resolved":
        return "bg-success-3 text-success-11 bg-success-4";
      case "silenced":
        return "bg-neutral-2 text-neutral-11/30";
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
    <div className="h-screen flex flex-col bg-neutral-1">
      {/* Header */}
      <header className="px-6 py-4 bg-neutral-2 border-b border-neutral-6">
        <div className="flex items-center justify-between">
          <div>
            <h1 className="text-2xl font-bold text-neutral-12">
              Observability
            </h1>
            <p className="text-sm text-neutral-11">
              Monitor traces, logs, and metrics for your AI agents
            </p>
          </div>
          <div className="flex items-center gap-4">
            <WebSocketHealthIndicator
              showLabel
              autoRefresh
              refreshInterval={10000}
            />
            <Button
              variant="secondary"
              className="flex px-4 py-2 bg-neutral-3 rounded-lg hover:bg-neutral-30 dark:hover:bg-neutral-9"
              onClick={handleRefresh}
            >
              <RefreshCw size={16} />
              Refresh
            </Button>
          </div>
        </div>
      </header>
      {/* Tabs */}
      <div className="px-6 py-2 bg-neutral-2 border-b border-neutral-6">
        <div className="flex gap-1">
          {tabs.map((tab) => (
            <Button
              variant="primary"
              className="flex px-4 py-2 rounded-lg"
              key={tab.id}
              onClick={() => handleTabChange(tab.id)}
            >
              <tab.icon size={16} />
              {tab.label}
            </Button>
          ))}
        </div>
      </div>
      {/* Traces Filters - only show on traces tab */}
      {activeTab === "traces" && (
        <div className="px-6 py-3 bg-neutral-2 border-b border-neutral-6">
          <div className="flex items-center gap-4 flex-wrap">
            {/* Status filter */}
            <div className="flex items-center gap-1">
              <Button
                variant="primary"
                size="sm"
                className="px-2 py-1 text-xs rounded"
                onClick={() => setStatusFilter("")}
                aria-pressed={statusFilter === ""}
              >
                All
              </Button>
              <Button
                variant="primary"
                size="sm"
                className="px-2 py-1 text-xs rounded"
                onClick={() => setStatusFilter("success")}
                aria-pressed={statusFilter === "success"}
              >
                Success
              </Button>
              <Button
                variant="primary"
                size="sm"
                className="px-2 py-1 text-xs rounded"
                onClick={() => setStatusFilter("error")}
                aria-pressed={statusFilter === "error"}
              >
                Error
              </Button>
              <Button
                variant="primary"
                size="sm"
                className="px-2 py-1 text-xs rounded"
                onClick={() => setStatusFilter("running")}
                aria-pressed={statusFilter === "running"}
              >
                Running
              </Button>
            </div>

            {/* Entity ID filters */}
            <div className="flex items-center gap-2">
              <Input
                size="sm"
                className="w-32 px-2 py-1 text-sm text-neutral-12 focus:ring-primary-7"
                value={sessionIdFilter}
                onChange={(e) => setSessionIdFilter(e.target.value)}
                placeholder="Session ID"
                aria-label="Filter by session ID"
              />
              <Input
                size="sm"
                className="w-32 px-2 py-1 text-sm text-neutral-12 focus:ring-primary-7"
                value={userIdFilter}
                onChange={(e) => setUserIdFilter(e.target.value)}
                placeholder="User ID"
                aria-label="Filter by user ID"
              />
              <Input
                size="sm"
                className="w-32 px-2 py-1 text-sm text-neutral-12 focus:ring-primary-7"
                value={workflowIdFilter}
                onChange={(e) => setWorkflowIdFilter(e.target.value)}
                placeholder="Workflow ID"
                aria-label="Filter by workflow ID"
              />
              <Input
                size="sm"
                className="w-32 px-2 py-1 text-sm text-neutral-12 focus:ring-primary-7"
                value={projectIdFilter}
                onChange={(e) => setProjectIdFilter(e.target.value)}
                placeholder="Project ID"
                aria-label="Filter by project ID"
              />
            </div>

            {/* Time range filter */}
            <Select
              size="sm"
              className="px-2 py-1 text-sm text-neutral-12 focus:ring-primary-7"
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
              <span className="text-sm text-neutral-11 ml-auto">
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
                  <div className="text-center py-12 text-neutral-11">
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
                      className="p-4 bg-neutral-2 rounded-lg border border-neutral-6 hover:border-primary-9 transition-colors cursor-pointer"
                      onClick={() =>
                        window.open(`/studio/chat/${session.id}`, "_blank")
                      }
                    >
                      <div className="flex items-center justify-between">
                        <div className="flex items-center gap-3">
                          <Bot size={20} className="text-insight-9" />
                          <div>
                            <h3 className="font-medium text-neutral-12">
                              {session.name || "Untitled Session"}
                            </h3>
                            <div className="flex items-center gap-3 mt-1 text-sm text-neutral-11">
                              <span className="flex items-center gap-1">
                                <Clock size={14} />
                                {new Date(session.createdAt).toLocaleString()}
                              </span>
                              <span className="font-mono text-xs">
                                {session.id.slice(0, 8)}...
                              </span>
                            </div>
                          </div>
                        </div>
                        <div className="flex items-center gap-2">
                          {session.status === "active" ? (
                            <span className="flex items-center gap-1 px-2 py-1 text-xs rounded-full bg-success-3 text-success-11 bg-success-4">
                              <CheckCircle size={12} />
                              Active
                            </span>
                          ) : session.status === "archived" ? (
                            <span className="flex items-center gap-1 px-2 py-1 text-xs rounded-full bg-warning-3 text-warning-10/30">
                              <Clock size={12} />
                              Archived
                            </span>
                          ) : (
                            <span className="flex items-center gap-1 px-2 py-1 text-xs rounded-full bg-neutral-2 text-neutral-10/30">
                              <XCircle size={12} />
                              {session.status}
                            </span>
                          )}
                          <ExternalLink size={16} className="text-neutral-6" />
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
                  <div className="text-center py-12 text-neutral-11">
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
                      className="p-4 bg-neutral-2 rounded-lg border border-neutral-6 hover:border-primary-9 transition-colors cursor-pointer"
                      onClick={() =>
                        window.open(
                          `/studio/workflows/${workflow.id}`,
                          "_blank",
                        )
                      }
                    >
                      <div className="flex items-center justify-between">
                        <div className="flex items-center gap-3">
                          <GitBranch size={20} className="text-success-11" />
                          <div>
                            <h3 className="font-medium text-neutral-12">
                              {workflow.name}
                            </h3>
                            <div className="flex items-center gap-3 mt-1 text-sm text-neutral-11">
                              <span className="flex items-center gap-1">
                                <Clock size={14} />
                                {new Date(workflow.createdAt).toLocaleString()}
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
                          <span className="flex items-center gap-1 px-2 py-1 text-xs rounded-full bg-primary-3 text-primary-11 bg-primary-4">
                            <Activity size={12} />
                            {workflow.nodeCount} nodes
                          </span>
                          <span className="flex items-center gap-1 px-2 py-1 text-xs rounded-full bg-neutral-2 text-neutral-10/30">
                            {workflow.edgeCount} edges
                          </span>
                          <ExternalLink size={16} className="text-neutral-6" />
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
                {/* Real-time Trace Canvas Toggle */}
                <div className="flex items-center justify-between p-4 bg-neutral-2 rounded-lg border border-neutral-6">
                  <div className="flex items-center gap-3">
                    <Activity size={20} className="text-insight-11" />
                    <div>
                      <h3 className="font-medium text-neutral-12">
                        Real-time Trace Canvas
                      </h3>
                      <p className="text-sm text-neutral-11">
                        Live visualization of trace spans via WebSocket
                      </p>
                    </div>
                  </div>
                  <Button
                    variant="primary"
                    className="px-4 py-2 rounded-lg text-sm"
                    onClick={() => setShowTraceCanvas(!showTraceCanvas)}
                  >
                    {showTraceCanvas ? "Hide Canvas" : "Show Canvas"}
                  </Button>
                </div>

                {/* TraceCanvas - Real-time ReactFlow visualization */}
                {showTraceCanvas && (
                  <div className="h-[400px] bg-neutral-2 rounded-lg border border-neutral-6 overflow-hidden">
                    <TraceCanvas
                      sessionId={sessionIdFilter || undefined}
                      autoConnect={true}
                      className="w-full h-full"
                    />
                  </div>
                )}

                {traces.length === 0 ? (
                  <div className="text-center py-12 text-neutral-11">
                    No traces found
                  </div>
                ) : (
                  <>
                    {traces.map((trace) => (
                      <div
                        key={trace.id}
                        onClick={() => setSelectedTraceId(trace.id)}
                        className={`p-4 bg-neutral-2 rounded-lg border transition-colors cursor-pointer ${
                          selectedTraceId === trace.id
                            ? "border-primary-9 ring-2 ring-primary-4 dark:ring-primary-11"
                            : "border-neutral-6 hover:border-primary-9"
                        }`}
                      >
                        <div className="flex items-center justify-between">
                          <div className="flex items-center gap-3">
                            <Activity size={20} className="text-primary-9" />
                            <div>
                              <h3 className="font-medium text-neutral-12">
                                {trace.name}
                              </h3>
                              <div className="flex items-center gap-3 mt-1 text-sm text-neutral-11">
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
                    {tracesData?.nextCursor && (
                      <div className="flex justify-center pt-4">
                        <Button
                          variant="secondary"
                          className="flex px-4 py-2 bg-neutral-3 text-neutral-11 rounded-lg hover:bg-neutral-30 dark:hover:bg-neutral-9"
                          onClick={() => setCursor(tracesData.nextCursor)}
                          disabled={isTracesFetching}
                        >
                          {isTracesFetching ? (
                            <>
                              <RefreshCw size={16} className="animate-spin" />
                              Loading...
                            </>
                          ) : (
                            "Load More"
                          )}
                        </Button>
                      </div>
                    )}

                    {/* TraceViewer Panel (Developer journey - trace debugging) */}
                    {selectedTraceId && (
                      <div className="mt-6 bg-neutral-2 rounded-lg border border-neutral-6 overflow-hidden">
                        <div className="flex items-center justify-between px-4 py-2 border-b border-neutral-6 bg-neutral-1">
                          <span className="text-sm font-medium text-neutral-11">
                            Trace Details
                          </span>
                          <Button
                            variant="secondary"
                            className="text-sm text-neutral-11 hover:text-neutral-10 dark:hover:text-neutral-3"
                            onClick={() => setSelectedTraceId(null)}
                          >
                            Close
                          </Button>
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
                            className="border-t border-neutral-6"
                          >
                            <div className="px-4 py-2 bg-gradient-to-r from-insight-50 to-blue-50 dark:from-insight-900/20 dark:to-blue-900/20 border-b border-neutral-6">
                              <div className="flex items-center gap-2">
                                <Sparkles
                                  size={16}
                                  className="text-insight-9"
                                />
                                <span className="text-sm font-medium text-neutral-11">
                                  AI Insights
                                </span>
                              </div>
                            </div>

                            <div className="p-4 grid grid-cols-1 lg:grid-cols-2 gap-4">
                              {/* Trace Summary */}
                              <div className="space-y-2">
                                <h4 className="text-xs font-medium text-neutral-11 uppercase tracking-wider">
                                  Summary
                                </h4>
                                {traceSummary.isLoading ? (
                                  <div className="flex items-center gap-2 text-sm text-neutral-6">
                                    <Loader2
                                      size={14}
                                      className="animate-spin"
                                    />
                                    <span>Analyzing trace...</span>
                                  </div>
                                ) : traceSummary.summary ? (
                                  <div className="space-y-2">
                                    <p className="text-sm text-neutral-11">
                                      {traceSummary.summary}
                                    </p>
                                    {traceSummary.keyActions.length > 0 && (
                                      <div className="flex flex-wrap gap-1">
                                        {traceSummary.keyActions.map(
                                          (action, idx) => (
                                            <span
                                              key={idx}
                                              className="px-2 py-0.5 text-xs bg-primary-3 bg-primary-4 text-primary-11 rounded"
                                            >
                                              {action}
                                            </span>
                                          ),
                                        )}
                                      </div>
                                    )}
                                    <div className="flex items-center gap-4 text-xs text-neutral-11">
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
                                  <p className="text-sm text-neutral-6">
                                    No summary available
                                  </p>
                                )}
                              </div>

                              {/* Anomaly Detection */}
                              <div className="space-y-2">
                                <h4 className="text-xs font-medium text-neutral-11 uppercase tracking-wider">
                                  Health & Anomalies
                                </h4>
                                {traceAnomaly.isLoading ? (
                                  <div className="flex items-center gap-2 text-sm text-neutral-6">
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
                                        <span className="text-sm text-neutral-11">
                                          Health:
                                        </span>
                                        <span
                                          className={`text-sm font-medium ${
                                            traceAnomaly.healthScore >= 80
                                              ? "text-success-10"
                                              : traceAnomaly.healthScore >= 60
                                                ? "text-warning-9"
                                                : "text-error-10"
                                          }`}
                                        >
                                          {traceAnomaly.healthScore}/100
                                        </span>
                                      </div>
                                    )}

                                    {/* Bottlenecks */}
                                    {traceAnomaly.bottlenecks.length > 0 && (
                                      <div className="space-y-1">
                                        <span className="text-xs text-neutral-11 flex items-center gap-1">
                                          <Zap size={12} />
                                          Bottlenecks:
                                        </span>
                                        {traceAnomaly.bottlenecks
                                          .slice(0, 3)
                                          .map((bottleneck, idx) => (
                                            <Tooltip
                                              key={idx}
                                              content={`${bottleneck.durationMs}ms (${bottleneck.percentageOfTotal}% of total)`}
                                              position="top"
                                            >
                                              <span className="inline-block px-2 py-0.5 text-xs bg-grafana-2 text-grafana-10 rounded cursor-help">
                                                {bottleneck.stepName}
                                              </span>
                                            </Tooltip>
                                          ))}
                                      </div>
                                    )}

                                    {/* Anomalies */}
                                    {traceAnomaly.anomalies.length > 0 && (
                                      <div className="space-y-1">
                                        <span className="text-xs text-neutral-11 flex items-center gap-1">
                                          <AlertTriangle size={12} />
                                          Issues:
                                        </span>
                                        {traceAnomaly.anomalies
                                          .slice(0, 3)
                                          .map((anomaly, idx) => (
                                            <Tooltip
                                              key={idx}
                                              content={
                                                anomaly.suggestedFix ||
                                                anomaly.message
                                              }
                                              position="top"
                                            >
                                              <div
                                                className={`text-xs px-2 py-1 rounded cursor-help ${
                                                  anomaly.severity === "error"
                                                    ? "bg-error-3 bg-error-4 text-error-11"
                                                    : anomaly.severity ===
                                                        "warning"
                                                      ? "bg-warning-3/30 text-warning-10"
                                                      : "bg-primary-3 bg-primary-4 text-primary-11"
                                                }`}
                                              >
                                                {anomaly.stepName}:{" "}
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
                                        <span className="text-xs text-neutral-11 flex items-center gap-1">
                                          <TrendingUp size={12} />
                                          Suggestions:
                                        </span>
                                        <ul className="text-xs text-neutral-11 list-disc list-inside">
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
                                        <p className="text-sm text-success-10 flex items-center gap-1">
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
                  <div className="text-center py-12 text-neutral-11">
                    No logs found
                  </div>
                ) : (
                  logs.map((log) => (
                    <div
                      key={log.id}
                      className="p-4 bg-neutral-2 rounded-lg border border-neutral-6"
                    >
                      <div className="flex items-center justify-between">
                        <div className="flex items-center gap-3">
                          <span
                            className={`px-2 py-0.5 text-xs rounded-full ${getLogLevelColor(log.level)}`}
                          >
                            {log.level}
                          </span>
                          <span className="text-neutral-12">{log.message}</span>
                        </div>
                        <div className="flex items-center gap-3 text-sm text-neutral-11">
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
                <div className="p-4 bg-neutral-2 rounded-lg border border-neutral-6">
                  <h3 className="text-sm font-medium text-neutral-11 mb-1">
                    Total Requests
                  </h3>
                  <div className="text-2xl font-semibold text-neutral-12">
                    {(metrics.requestsTotal ?? 0).toLocaleString()}
                  </div>
                </div>
                <div className="p-4 bg-neutral-2 rounded-lg border border-neutral-6">
                  <h3 className="text-sm font-medium text-neutral-11 mb-1">
                    Total Errors
                  </h3>
                  <div className="text-2xl font-semibold text-error-10">
                    {(metrics.errorsTotal ?? 0).toLocaleString()}
                  </div>
                </div>
                <div className="p-4 bg-neutral-2 rounded-lg border border-neutral-6">
                  <h3 className="text-sm font-medium text-neutral-11 mb-1">
                    Avg Latency
                  </h3>
                  <div className="text-2xl font-semibold text-neutral-12">
                    {metrics.avgLatencyMs ?? 0}ms
                  </div>
                </div>
                <div className="p-4 bg-neutral-2 rounded-lg border border-neutral-6">
                  <h3 className="text-sm font-medium text-neutral-11 mb-1">
                    P99 Latency
                  </h3>
                  <div className="text-2xl font-semibold text-neutral-12">
                    {metrics.p99LatencyMs ?? 0}ms
                  </div>
                </div>
                <div className="p-4 bg-neutral-2 rounded-lg border border-neutral-6">
                  <h3 className="text-sm font-medium text-neutral-11 mb-1">
                    Tokens Used
                  </h3>
                  <div className="text-2xl font-semibold text-neutral-12">
                    {(metrics.tokensUsed ?? 0).toLocaleString()}
                  </div>
                </div>
                <div className="p-4 bg-neutral-2 rounded-lg border border-neutral-6">
                  <h3 className="text-sm font-medium text-neutral-11 mb-1">
                    Active Sessions
                  </h3>
                  <div className="text-2xl font-semibold text-neutral-12">
                    {metrics.activeSessions ?? 0}
                  </div>
                </div>
              </div>
            )}

            {/* Empty metrics state */}
            {activeTab === "metrics" && !metrics && !isMetricsLoading && (
              <div className="text-center py-12 text-neutral-11">
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
                <div className="flex items-center gap-4 flex-wrap p-4 bg-neutral-2 rounded-lg border border-neutral-6">
                  {/* State filter */}
                  <div className="flex items-center gap-2">
                    <span className="text-sm text-neutral-11">State:</span>
                    <div className="flex items-center gap-1">
                      <Button
                        variant="primary"
                        size="sm"
                        className="px-2 py-1 text-xs rounded"
                        onClick={() => setAlertStateFilter("")}
                      >
                        All
                      </Button>
                      <Button
                        variant="primary"
                        size="sm"
                        className="px-2 py-1 text-xs rounded"
                        onClick={() => setAlertStateFilter("firing")}
                      >
                        Firing
                      </Button>
                      <Button
                        variant="primary"
                        size="sm"
                        className="px-2 py-1 text-xs rounded"
                        onClick={() => setAlertStateFilter("pending")}
                      >
                        Pending
                      </Button>
                      <Button
                        variant="primary"
                        size="sm"
                        className="px-2 py-1 text-xs rounded"
                        onClick={() => setAlertStateFilter("resolved")}
                      >
                        Resolved
                      </Button>
                    </div>
                  </div>

                  {/* Severity filter */}
                  <div className="flex items-center gap-2">
                    <span className="text-sm text-neutral-11">Severity:</span>
                    <Select
                      size="sm"
                      className="px-2 py-1 text-sm text-neutral-12 focus:ring-primary-7"
                      value={alertSeverityFilter}
                      onChange={(e) => setAlertSeverityFilter(e.target.value)}
                    >
                      <option value="">All Severities</option>
                      <option value="critical">Critical</option>
                      <option value="error">Error</option>
                      <option value="warning">Warning</option>
                      <option value="info">Info</option>
                    </Select>
                  </div>

                  {/* Alert count */}
                  {alertsData && (
                    <span className="text-sm text-neutral-11 ml-auto">
                      {alerts.length} alerts
                    </span>
                  )}
                </div>

                {/* Alerts List */}
                {alerts.length === 0 ? (
                  <div className="text-center py-12 text-neutral-11">
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
                      key={alert.alertId}
                      className="p-4 bg-neutral-2 rounded-lg border border-neutral-6 hover:border-primary-9 transition-colors"
                    >
                      <div className="flex items-start justify-between">
                        <div className="flex items-start gap-3">
                          <AlertTriangle
                            size={20}
                            className={
                              alert.severity === "critical"
                                ? "text-error-9"
                                : alert.severity === "error"
                                  ? "text-grafana-9"
                                  : alert.severity === "warning"
                                    ? "text-warning-9"
                                    : "text-primary-9"
                            }
                          />
                          <div>
                            <h3 className="font-medium text-neutral-12">
                              {alert.name}
                            </h3>
                            <p className="text-sm text-neutral-11 mt-1">
                              {alert.message ||
                                alert.annotations?.summary ||
                                "No description"}
                            </p>
                            <div className="flex items-center gap-3 mt-2 text-sm text-neutral-11">
                              {alert.startedAt && (
                                <span className="flex items-center gap-1">
                                  <Clock size={14} />
                                  Started{" "}
                                  {new Date(alert.startedAt).toLocaleString()}
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
                          {alert.generatorUrl && (
                            <a
                              href={alert.generatorUrl}
                              target="_blank"
                              rel="noopener noreferrer"
                              className="p-1 text-neutral-6 hover:text-primary-9 transition-colors"
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
                                className="px-2 py-0.5 text-xs bg-neutral-3 text-neutral-11 rounded"
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
