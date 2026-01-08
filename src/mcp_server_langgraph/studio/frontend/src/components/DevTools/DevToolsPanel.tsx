/**
 * DevToolsPanel Component
 *
 * Chrome DevTools-like debugging panel for Agent Studio.
 * Provides context-aware tabs for debugging sessions and workflows.
 *
 * Features:
 * - Context indicator (Session/Workflow/Global)
 * - Tab navigation with ARIA support
 * - Console with filter dropdown
 * - Collapse/expand/maximize actions
 * - Dark mode support
 */

import { useCallback, Suspense, lazy, useMemo } from "react";
import {
  ChevronDown,
  Maximize2,
  Minimize2,
  X,
  Trash2,
  Terminal,
  Activity,
  GitBranch,
  Network,
  Database,
  AlertTriangle,
  Sparkles,
  Loader2,
  // OTEL tab icons
  GitMerge,
  BarChart3,
  Bell,
  FileText,
  Wifi,
} from "lucide-react";
import { useAppDispatch, useAppSelector } from "../../store/hooks";
import {
  toggleDevTools,
  setActiveTab,
  setMaximized,
  setConsoleFilter,
  clearConsole,
  selectDevToolsCollapsed,
  selectDevToolsMaximized,
  selectActiveTab,
  selectConsoleFilter,
  selectAvailableTabs,
  type DevToolsTabId,
  type ConsoleFilterLevel,
} from "../../store/slices/devToolsSlice";
import { useDevToolsContext } from "./hooks/useDevToolsContext";
import { TimelineBar } from "./TimelineBar";
import { DevToolsTimelineProvider } from "./context/DevToolsTimelineProvider";
import { DevToolsWebSocketObserver } from "./components/DevToolsWebSocketObserver";
import { useTraceWebSocket } from "../../hooks/useTraceWebSocket";
import { useAlertWebSocket } from "../../hooks/useAlertWebSocket";
import { useDevToolsWebSocket } from "./hooks/useDevToolsWebSocket";
import { selectAlerts, clearAlerts } from "../../store/slices/alertSlice";
import {
  useListTracesQuery,
  useListLogsQuery,
  useGetMetricsQuery,
  useListAlertsQuery,
} from "../../api";
import type { DevToolsPanelProps } from "./types";
import type { TraceSpan, TraceListItem } from "./tabs/TracesTab";

// =============================================================================
// Utility
// =============================================================================

function cn(...classes: (string | undefined | boolean)[]): string {
  return classes.filter(Boolean).join(" ");
}

// =============================================================================
// Tab Icons
// =============================================================================

const TAB_ICONS: Record<DevToolsTabId, typeof Terminal> = {
  console: Terminal,
  "agent-trace": Activity,
  "execution-trace": GitBranch,
  network: Network,
  state: Database,
  problems: AlertTriangle,
  "ai-insights": Sparkles,
  // OTEL Observability tabs
  traces: GitMerge,
  metrics: BarChart3,
  alerts: Bell,
  logs: FileText,
  "ws-metrics": Wifi,
};

const TAB_LABELS: Record<DevToolsTabId, string> = {
  console: "Console",
  "agent-trace": "Agent Trace",
  "execution-trace": "Execution Trace",
  network: "Network",
  state: "State",
  problems: "Problems",
  "ai-insights": "AI Insights",
  // OTEL Observability tabs
  traces: "Traces",
  metrics: "Metrics",
  alerts: "Alerts",
  logs: "Logs",
  "ws-metrics": "WS Metrics",
};

// =============================================================================
// Lazy-loaded Tab Content Components
// =============================================================================

const ConsoleTabContent = lazy(() =>
  import("./tabs/ConsoleTab").then((m) => ({ default: m.ConsoleTab })),
);
const NetworkTabContent = lazy(() =>
  import("./tabs/NetworkTab").then((m) => ({ default: m.NetworkTab })),
);
const StateTabContent = lazy(() =>
  import("./tabs/StateTab").then((m) => ({ default: m.StateTab })),
);
const ProblemsTabContent = lazy(() =>
  import("./tabs/ProblemsTab").then((m) => ({ default: m.ProblemsTab })),
);
const AgentTraceTabContent = lazy(() =>
  import("./tabs/AgentTraceTab").then((m) => ({ default: m.AgentTraceTab })),
);
const ExecutionTraceTabContent = lazy(() =>
  import("./tabs/ExecutionTraceTab").then((m) => ({
    default: m.ExecutionTraceTab,
  })),
);
const AIInsightsTabContent = lazy(() =>
  import("./tabs/AIInsightsTab").then((m) => ({ default: m.AIInsightsTab })),
);

// OTEL Observability tabs
const TracesTabContent = lazy(() =>
  import("./tabs/TracesTab").then((m) => ({ default: m.TracesTab })),
);
const MetricsTabContent = lazy(() =>
  import("./tabs/MetricsTab").then((m) => ({ default: m.MetricsTab })),
);
const AlertsTabContent = lazy(() =>
  import("./tabs/AlertsTab").then((m) => ({ default: m.AlertsTab })),
);
const LogsTabContent = lazy(() =>
  import("./tabs/LogsTab").then((m) => ({ default: m.LogsTab })),
);
const WsMetricsTabContent = lazy(() =>
  import("../WebSocketMetrics/WebSocketMetricsPanel").then((m) => ({
    default: m.WebSocketMetricsPanel,
  })),
);

// =============================================================================
// Tab Content Loader
// =============================================================================

function TabContentLoader() {
  return (
    <div className="flex items-center justify-center h-full">
      <Loader2 className="w-6 h-6 animate-spin text-gray-400 dark:text-gray-400" />
    </div>
  );
}

// =============================================================================
// Console Filter Dropdown
// =============================================================================

interface ConsoleFilterProps {
  value: ConsoleFilterLevel;
  onChange: (value: ConsoleFilterLevel) => void;
}

function ConsoleFilter({ value, onChange }: ConsoleFilterProps) {
  return (
    <div data-testid="console-filter" className="relative">
      <select
        value={value}
        onChange={(e) => onChange(e.target.value as ConsoleFilterLevel)}
        className={cn(
          "appearance-none pl-2 pr-6 py-1 text-xs rounded",
          "bg-gray-100 dark:bg-gray-700",
          "text-gray-700 dark:text-gray-200",
          "border border-gray-200 dark:border-gray-700 dark:border-gray-600",
          "focus:outline-none focus:ring-1 focus:ring-primary-500",
        )}
      >
        <option value="all">All</option>
        <option value="info">Info</option>
        <option value="warning">Warning</option>
        <option value="error">Error</option>
      </select>
      <ChevronDown
        size={12}
        className="absolute right-1.5 top-1/2 -translate-y-1/2 pointer-events-none text-gray-500 dark:text-gray-400"
      />
    </div>
  );
}

// =============================================================================
// DevToolsPanel Component
// =============================================================================

export function DevToolsPanel({ className }: DevToolsPanelProps) {
  const dispatch = useAppDispatch();

  // Redux state
  const collapsed = useAppSelector(selectDevToolsCollapsed);
  const maximized = useAppSelector(selectDevToolsMaximized);
  const activeTab = useAppSelector(selectActiveTab);
  const consoleFilter = useAppSelector(selectConsoleFilter);
  const availableTabs = useAppSelector(selectAvailableTabs);

  // Context detection
  const { contextLabel, context, entityId } = useDevToolsContext();

  // Trace WebSocket - auto-connect when DevTools is open and traces tab available
  const { spans: rawSpans } = useTraceWebSocket({
    autoConnect: !collapsed && availableTabs.includes("traces"),
  });

  // DevTools WebSocket - auto-connect for console and network data
  const {
    status: devToolsWsStatus,
    consoleEntries: wsConsoleEntries,
    networkEntries: wsNetworkEntries,
    clearConsoleEntries: clearWsConsoleEntries,
    clearNetworkEntries: clearWsNetworkEntries,
    traceSteps: wsTraceSteps,
    clearTraceSteps: _clearWsTraceSteps,
    reconnectAttempts: devToolsReconnectAttempts,
  } = useDevToolsWebSocket({
    enabled: !collapsed,
    contextEntityId: entityId,
  });

  // Alert WebSocket - auto-connect for real-time alert updates
  const { status: alertWsStatus } = useAlertWebSocket({
    enabled: !collapsed && availableTabs.includes("alerts"),
    showToasts: false, // DevTools handles display
  });

  // Get WebSocket alerts from Redux store
  const wsAlerts = useAppSelector(selectAlerts);

  // Transform Redux alerts to DevTools Alert format
  const wsAlertsList = useMemo(() => {
    if (!wsAlerts || wsAlerts.length === 0) return [];
    return wsAlerts.map((alert) => ({
      id: alert.alertId,
      name: alert.name,
      state: alert.state as "firing" | "pending" | "resolved" | "silenced",
      severity: alert.severity,
      service: alert.labels?.service || "unknown",
      message: alert.message,
      startedAt: alert.startedAt || new Date().toISOString(),
      resolvedAt: alert.endedAt ?? undefined,
      generatorUrl: undefined,
      labels: alert.labels,
    }));
  }, [wsAlerts]);

  // RTK Query hooks for OTEL tabs - skip when collapsed or tab not active
  // These provide real-time API data to the observability tabs
  const traceListParams = useMemo(() => {
    return {
      limit: 50,
      // Context-aware trace scoping: session/workflow contexts show only related traces.
      // Global context remains unfiltered.
      session_id: context === "session" ? (entityId ?? undefined) : undefined,
      workflow_id: context === "workflow" ? (entityId ?? undefined) : undefined,
    };
  }, [context, entityId]);

  const {
    data: tracesData,
    isLoading: isTracesLoading,
    error: tracesError,
  } = useListTracesQuery(traceListParams, {
    skip: collapsed || activeTab !== "traces",
  });

  const {
    data: metricsData,
    isLoading: isMetricsLoading,
    error: metricsError,
  } = useGetMetricsQuery(undefined, {
    skip: collapsed || activeTab !== "metrics",
  });

  const {
    data: alertsData,
    isLoading: isAlertsLoading,
    error: alertsError,
  } = useListAlertsQuery(
    { limit: 50 },
    { skip: collapsed || activeTab !== "alerts" },
  );

  const {
    data: logsData,
    isLoading: isLogsLoading,
    error: logsError,
  } = useListLogsQuery(
    { limit: 100 },
    { skip: collapsed || activeTab !== "logs" },
  );

  // Filter WebSocket spans by context (when possible)
  const filteredRawSpans = useMemo(() => {
    if (context !== "session" || !entityId) return rawSpans;

    return rawSpans.filter((span) => {
      const attributes = span.attributes ?? {};
      // OTEL semantic attributes use dot notation; Alloy exports with underscores.
      // session_id is a raw OTEL attribute name, not a transformed API response field.
      const sessionAttr =
        (attributes["session.id"] as string | undefined) ??
        // eslint-disable-next-line no-restricted-syntax -- raw OTEL attribute
        (attributes.session_id as string | undefined) ??
        (attributes.sessionId as string | undefined);

      return sessionAttr === entityId;
    });
  }, [context, entityId, rawSpans]);

  // Transform spans to TracesTab format
  const traceSpans: TraceSpan[] = useMemo(() => {
    return filteredRawSpans.map((span) => ({
      spanId: span.spanId,
      traceId: span.traceId,
      parentSpanId: span.parentSpanId ?? null,
      name: span.name,
      startTime: new Date(span.startTime).getTime(),
      durationMs: span.endTime
        ? new Date(span.endTime).getTime() - new Date(span.startTime).getTime()
        : 0,
      status: span.status.toLowerCase() as "ok" | "error" | "unset",
      serviceName: (span.attributes?.service_name as string) || undefined,
      depth: 0, // Will be calculated by TracesTab based on parentSpanId
      attributes: span.attributes,
    }));
  }, [filteredRawSpans]);

  // Transform API traces to TracesTab format
  const traceList: TraceListItem[] = useMemo(() => {
    if (!tracesData?.items) return [];
    return tracesData.items.map((trace) => ({
      traceId: trace.traceId,
      name: trace.name || "Unknown",
      startTime: trace.startTime ? new Date(trace.startTime).getTime() : 0,
      durationMs: trace.durationMs ?? 0,
      spanCount: trace.spanCount ?? 0,
      status: (trace.status as "ok" | "error" | "unset") ?? "unset",
    }));
  }, [tracesData]);

  // Transform API alerts to DevTools AlertsTab format
  const alertsList = useMemo(() => {
    if (!alertsData?.items) return [];
    return alertsData.items.map((alert) => ({
      id: alert.alertId,
      name: alert.name,
      state: alert.state as "firing" | "pending" | "resolved" | "silenced",
      severity: alert.severity as "critical" | "warning" | "info",
      service: alert.labels?.service || "unknown",
      message: alert.message,
      startedAt: alert.startedAt || new Date().toISOString(),
      resolvedAt: alert.endedAt ?? undefined,
      generatorUrl: alert.generatorUrl ?? undefined,
      labels: alert.labels,
    }));
  }, [alertsData]);

  // Transform API logs to DevTools LogsTab format
  const logsList = useMemo(() => {
    if (!logsData?.items) return [];
    return logsData.items.map((log) => ({
      id: log.id,
      timestamp: log.timestamp,
      level: (log.level === "warn" ? "warning" : log.level) as
        | "debug"
        | "info"
        | "warning"
        | "error",
      service: log.service || "unknown",
      message: log.message,
    }));
  }, [logsData]);

  // Transform API metrics to DevTools MetricsTab format
  const metricsList = useMemo(() => {
    if (!metricsData) return [];
    return [
      {
        name: "requests_total",
        value: metricsData.requestsTotal,
        unit: "req",
        trend: "stable" as const,
        change: 0,
        sparkline: [metricsData.requestsTotal],
      },
      {
        name: "errors_total",
        value: metricsData.errorsTotal,
        unit: "err",
        trend:
          metricsData.errorsTotal > 0 ? ("up" as const) : ("stable" as const),
        change: 0,
        sparkline: [metricsData.errorsTotal],
      },
      {
        name: "avg_latency",
        value: Math.round(metricsData.avgLatencyMs),
        unit: "ms",
        trend: "stable" as const,
        change: 0,
        sparkline: [metricsData.avgLatencyMs],
      },
      {
        name: "p99_latency",
        value: Math.round(metricsData.p99LatencyMs),
        unit: "ms",
        trend: "stable" as const,
        change: 0,
        sparkline: [metricsData.p99LatencyMs],
      },
      {
        name: "tokens_used",
        value: metricsData.tokensUsed,
        unit: "tokens",
        trend: "stable" as const,
        change: 0,
        sparkline: [metricsData.tokensUsed],
      },
      {
        name: "active_sessions",
        value: metricsData.activeSessions,
        unit: "sessions",
        trend: "stable" as const,
        change: 0,
        sparkline: [metricsData.activeSessions],
      },
    ];
  }, [metricsData]);

  // Handlers
  const handleCollapse = useCallback(() => {
    dispatch(toggleDevTools());
  }, [dispatch]);

  const handleMaximize = useCallback(() => {
    dispatch(setMaximized(!maximized));
  }, [dispatch, maximized]);

  const handleTabSelect = useCallback(
    (tabId: DevToolsTabId) => {
      dispatch(setActiveTab(tabId));
    },
    [dispatch],
  );

  const handleFilterChange = useCallback(
    (filter: ConsoleFilterLevel) => {
      dispatch(setConsoleFilter(filter));
    },
    [dispatch],
  );

  const handleClearConsole = useCallback(() => {
    dispatch(clearConsole());
  }, [dispatch]);

  // Don't render if collapsed
  if (collapsed) {
    return null;
  }

  // Render tab content
  const renderTabContent = () => {
    switch (activeTab) {
      case "console":
        return (
          <div
            data-testid="devtools-tab-content-console"
            className="h-full min-h-0"
          >
            <Suspense fallback={<TabContentLoader />}>
              <ConsoleTabContent
                filter={consoleFilter}
                onFilterChange={handleFilterChange}
                contextEntityId={entityId}
                externalEntries={wsConsoleEntries}
                onClearExternal={clearWsConsoleEntries}
              />
            </Suspense>
          </div>
        );
      case "network":
        return (
          <div
            data-testid="devtools-tab-content-network"
            className="h-full min-h-0"
          >
            <Suspense fallback={<TabContentLoader />}>
              <NetworkTabContent
                contextEntityId={entityId}
                externalEntries={wsNetworkEntries}
                onClearExternal={clearWsNetworkEntries}
              />
            </Suspense>
          </div>
        );
      case "state":
        return (
          <div
            data-testid="devtools-tab-content-state"
            className="h-full min-h-0"
          >
            <Suspense fallback={<TabContentLoader />}>
              <StateTabContent context={context} contextEntityId={entityId} />
            </Suspense>
          </div>
        );
      case "problems":
        return (
          <div
            data-testid="devtools-tab-content-problems"
            className="h-full min-h-0"
          >
            <Suspense fallback={<TabContentLoader />}>
              <ProblemsTabContent compact />
            </Suspense>
          </div>
        );
      case "agent-trace":
        return (
          <div
            data-testid="devtools-tab-content-agent-trace"
            className="h-full min-h-0"
          >
            <Suspense fallback={<TabContentLoader />}>
              <AgentTraceTabContent
                sessionId={entityId ?? ""}
                externalSteps={wsTraceSteps}
              />
            </Suspense>
          </div>
        );
      case "execution-trace":
        return (
          <div
            data-testid="devtools-tab-content-execution-trace"
            className="h-full min-h-0"
          >
            <Suspense fallback={<TabContentLoader />}>
              <ExecutionTraceTabContent workflowId={entityId ?? ""} />
            </Suspense>
          </div>
        );
      case "ai-insights":
        return (
          <div
            data-testid="devtools-tab-content-ai-insights"
            className="h-full min-h-0"
          >
            <Suspense fallback={<TabContentLoader />}>
              <AIInsightsTabContent
                context={context}
                contextEntityId={entityId ?? ""}
              />
            </Suspense>
          </div>
        );
      // OTEL Observability tabs - wired to RTK Query hooks
      case "traces":
        return (
          <div
            data-testid="devtools-tab-content-traces"
            className="h-full min-h-0"
          >
            <Suspense fallback={<TabContentLoader />}>
              <TracesTabContent
                traces={traceList}
                spans={traceSpans}
                // Trace list comes from the REST API; real-time spans are optional (WS permission-gated).
                isLoading={isTracesLoading}
                error={tracesError ? String(tracesError) : undefined}
              />
            </Suspense>
          </div>
        );
      case "metrics":
        return (
          <div
            data-testid="devtools-tab-content-metrics"
            className="h-full min-h-0"
          >
            <Suspense fallback={<TabContentLoader />}>
              <MetricsTabContent
                metrics={metricsList}
                isLoading={isMetricsLoading}
                error={metricsError ? String(metricsError) : undefined}
              />
            </Suspense>
          </div>
        );
      case "alerts":
        return (
          <div
            data-testid="devtools-tab-content-alerts"
            className="h-full min-h-0"
          >
            <Suspense fallback={<TabContentLoader />}>
              <AlertsTabContent
                alerts={alertsList}
                externalAlerts={wsAlertsList}
                connectionStatus={alertWsStatus}
                onClearExternal={() => dispatch(clearAlerts())}
                isLoading={isAlertsLoading}
                error={alertsError ? String(alertsError) : undefined}
              />
            </Suspense>
          </div>
        );
      case "logs":
        return (
          <div
            data-testid="devtools-tab-content-logs"
            className="h-full min-h-0"
          >
            <Suspense fallback={<TabContentLoader />}>
              <LogsTabContent
                logs={logsList}
                isLoading={isLogsLoading}
                error={logsError ? String(logsError) : undefined}
              />
            </Suspense>
          </div>
        );
      case "ws-metrics":
        return (
          <div
            data-testid="devtools-tab-content-ws-metrics"
            className="h-full min-h-0"
          >
            <Suspense fallback={<TabContentLoader />}>
              <WsMetricsTabContent />
            </Suspense>
          </div>
        );
      default:
        return null;
    }
  };

  return (
    <DevToolsTimelineProvider>
      {/* WebSocket observer bridges real-time events to the timeline */}
      <DevToolsWebSocketObserver />
      <div
        data-testid="devtools-panel"
        className={cn(
          "flex flex-col h-full",
          "bg-white dark:bg-gray-900",
          "border-t border-gray-200 dark:border-gray-700",
          className,
        )}
      >
        {/* Header */}
        <div
          data-testid="devtools-header"
          className={cn(
            "flex items-center justify-between px-3 py-1.5",
            "bg-gray-50 dark:bg-gray-800",
            "border-b border-gray-200 dark:border-gray-700",
          )}
        >
          {/* Context Indicator + WebSocket Status */}
          <div className="flex items-center gap-3">
            <span className="text-xs font-medium text-gray-600 dark:text-gray-300">
              {contextLabel}
            </span>

            {/* WebSocket Reconnection Status */}
            {devToolsWsStatus === "connecting" &&
              devToolsReconnectAttempts > 0 && (
                <div
                  data-testid="devtools-reconnecting-indicator"
                  className="flex items-center gap-1 text-warning-600 dark:text-warning-400 text-xs"
                >
                  <Loader2 className="w-3 h-3 animate-spin" />
                  <span>Reconnecting ({devToolsReconnectAttempts})...</span>
                </div>
              )}
            {devToolsWsStatus === "error" && (
              <div
                data-testid="devtools-error-indicator"
                className="flex items-center gap-1 text-error-600 dark:text-error-400 text-xs"
              >
                <AlertTriangle className="w-3 h-3" />
                <span>Connection error</span>
              </div>
            )}
            {devToolsWsStatus === "connected" && (
              <div
                data-testid="devtools-connected-indicator"
                className="flex items-center gap-1 text-success-600 dark:text-success-400 text-xs"
              >
                <Wifi className="w-3 h-3" />
              </div>
            )}
          </div>

          {/* Action Buttons */}
          <div className="flex items-center gap-1">
            {/* Console Filter (only show when Console tab active) */}
            {activeTab === "console" && (
              <ConsoleFilter
                value={consoleFilter}
                onChange={handleFilterChange}
              />
            )}

            {/* Clear Console */}
            <button
              onClick={handleClearConsole}
              className={cn(
                "p-1.5 rounded",
                "text-gray-500 dark:text-gray-400 hover:text-gray-700 dark:text-gray-200 dark:text-gray-400 dark:hover:text-gray-200",
                "hover:bg-gray-100 dark:bg-gray-800 dark:hover:bg-gray-700",
              )}
              title="Clear Console"
              aria-label="Clear"
            >
              <Trash2 size={14} />
            </button>

            {/* Maximize/Minimize */}
            <button
              onClick={handleMaximize}
              className={cn(
                "p-1.5 rounded",
                "text-gray-500 dark:text-gray-400 hover:text-gray-700 dark:text-gray-200 dark:text-gray-400 dark:hover:text-gray-200",
                "hover:bg-gray-100 dark:bg-gray-800 dark:hover:bg-gray-700",
              )}
              title={maximized ? "Minimize" : "Maximize"}
              aria-label={maximized ? "Minimize" : "Maximize"}
            >
              {maximized ? <Minimize2 size={14} /> : <Maximize2 size={14} />}
            </button>

            {/* Collapse */}
            <button
              onClick={handleCollapse}
              className={cn(
                "p-1.5 rounded",
                "text-gray-500 dark:text-gray-400 hover:text-gray-700 dark:text-gray-200 dark:text-gray-400 dark:hover:text-gray-200",
                "hover:bg-gray-100 dark:bg-gray-800 dark:hover:bg-gray-700",
              )}
              title="Collapse"
              aria-label="Collapse"
            >
              <X size={14} />
            </button>
          </div>
        </div>

        {/* Timeline Bar - Unified time-travel scrubber */}
        <TimelineBar />

        {/* Tabs */}
        <div
          data-testid="devtools-tabs"
          role="tablist"
          className={cn(
            "flex items-center gap-0.5 px-2 py-1",
            "bg-gray-100 dark:bg-gray-800",
            "border-b border-gray-200 dark:border-gray-700",
          )}
        >
          {availableTabs.map((tabId) => {
            const Icon = TAB_ICONS[tabId];
            const isActive = tabId === activeTab;

            return (
              <button
                key={tabId}
                data-testid={`devtools-tab-${tabId}`}
                role="tab"
                aria-selected={isActive}
                aria-controls={`tabpanel-${tabId}`}
                onClick={() => handleTabSelect(tabId)}
                className={cn(
                  "flex items-center gap-1.5 px-2.5 py-1.5 text-xs rounded",
                  isActive
                    ? "bg-white dark:bg-gray-700 text-gray-900 dark:text-gray-100 shadow-sm"
                    : "text-gray-600 dark:text-gray-400 hover:text-gray-900 dark:hover:text-gray-200 hover:bg-gray-50 dark:hover:bg-gray-700",
                )}
              >
                <Icon size={14} />
                {TAB_LABELS[tabId]}
              </button>
            );
          })}
        </div>

        {/* Tab Content */}
        <div
          role="tabpanel"
          id={`tabpanel-${activeTab}`}
          aria-labelledby={`tab-${activeTab}`}
          className="flex-1 min-h-0 overflow-auto"
        >
          {renderTabContent()}
        </div>
      </div>
    </DevToolsTimelineProvider>
  );
}

export default DevToolsPanel;
