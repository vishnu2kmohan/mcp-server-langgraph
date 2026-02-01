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
 *
 * Design System Compliance:
 * - Uses CVA for tab button variants
 * - Uses Motion.dev for button press feedback
 * - Implements useReducedMotion() for accessibility
 * - Uses semantic colors per STYLE.md
 */

import {
  useCallback,
  Suspense,
  lazy,
  useMemo,
  useEffect,
  useState,
} from "react";
import { useMetricsHistory } from "../../hooks/useMetricsHistory";
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
import { OBSERVABILITY_POLLING_CONFIG } from "../../config/observability";
import {
  useListTracesQuery,
  useGetTraceQuery,
  useListLogsQuery,
  useGetMetricsQuery,
  useListAlertsQuery,
} from "../../api";
import type { DevToolsPanelProps } from "./types";
import type { TraceSpan, TraceListItem } from "./tabs/TracesTab";

import { cva } from "class-variance-authority";
import { motion, useReducedMotion } from "motion/react";
import { buttonVariants as motionButtonVariants } from "@/design-system/micro-interactions";
import { Button, Select } from "@/components/UI";

// =============================================================================
// Utility
// =============================================================================

function cn(...classes: (string | undefined | boolean)[]): string {
  return classes.filter(Boolean).join(" ");
}

function normalizeTraceSpanStatus(
  status?: string | null,
): "ok" | "error" | "unset" {
  const normalized = status?.toLowerCase();
  if (normalized === "ok" || normalized === "error" || normalized === "unset") {
    return normalized;
  }
  return "unset";
}

const {
  traceListActiveMs,
  traceListIdleMs,
  traceDetailMs,
  metricsMs,
  logsMs,
  alertsMs,
} = OBSERVABILITY_POLLING_CONFIG;

// =============================================================================
// CVA Variants
// =============================================================================

/**
 * DevTools tab button variants
 */
// eslint-disable-next-line react-refresh/only-export-components
export const devToolsTabVariants = cva(
  "flex items-center gap-1.5 px-2.5 py-1.5 text-xs rounded transition-colors",
  {
    variants: {
      active: {
        true: "bg-neutral-1 text-neutral-12 shadow-sm",
        false: "text-neutral-a8 hover:text-neutral-12 hover:bg-neutral-1",
      },
    },
    defaultVariants: {
      active: false,
    },
  },
);

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
      <Loader2 className="w-6 h-6 animate-spin text-neutral-9" />
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
      <Select
        value={value}
        onChange={(e) => onChange(e.target.value as ConsoleFilterLevel)}
        className={cn(
          "appearance-none pl-2 pr-6 py-1 text-xs rounded",
          "bg-neutral-2",
          "text-neutral-11",
          "border border-neutral-5",
          "focus:outline-none focus:ring-1 focus:ring-primary-7",
        )}
      >
        <option value="all">All</option>
        <option value="info">Info</option>
        <option value="warning">Warning</option>
        <option value="error">Error</option>
      </Select>
      <ChevronDown
        size={12}
        className="absolute right-1.5 top-1/2 -translate-y-1/2 pointer-events-none text-neutral-10"
      />
    </div>
  );
}

// =============================================================================
// DevToolsPanel Component
// =============================================================================

export function DevToolsPanel({ className }: DevToolsPanelProps) {
  const dispatch = useAppDispatch();
  const prefersReducedMotion = useReducedMotion();

  // Redux state
  const collapsed = useAppSelector(selectDevToolsCollapsed);
  const maximized = useAppSelector(selectDevToolsMaximized);
  const activeTab = useAppSelector(selectActiveTab);
  const consoleFilter = useAppSelector(selectConsoleFilter);
  const availableTabs = useAppSelector(selectAvailableTabs);

  // Context detection
  const { contextLabel, context, entityId } = useDevToolsContext();

  // State for trace-log linking
  const [selectedTraceId, setSelectedTraceId] = useState<string | null>(null);
  const [hasActiveTraces, setHasActiveTraces] = useState(false);
  const [selectedTraceComplete, setSelectedTraceComplete] = useState(false);

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

  const isTracesTabActive = !collapsed && activeTab === "traces";
  const traceListPollingInterval = isTracesTabActive
    ? hasActiveTraces
      ? traceListActiveMs
      : traceListIdleMs
    : 0;
  const traceDetailPollingInterval =
    isTracesTabActive && selectedTraceId && !selectedTraceComplete
      ? traceDetailMs
      : 0;

  const {
    data: tracesData,
    isLoading: isTracesLoading,
    error: tracesError,
  } = useListTracesQuery(traceListParams, {
    skip: !isTracesTabActive,
    pollingInterval: traceListPollingInterval,
    refetchOnFocus: true,
    refetchOnReconnect: true,
  });

  const { data: selectedTraceData } = useGetTraceQuery(selectedTraceId ?? "", {
    skip: !isTracesTabActive || !selectedTraceId,
    pollingInterval: traceDetailPollingInterval,
    refetchOnFocus: true,
    refetchOnReconnect: true,
  });

  const {
    data: metricsData,
    isLoading: isMetricsLoading,
    error: metricsError,
  } = useGetMetricsQuery(undefined, {
    skip: collapsed || activeTab !== "metrics",
    pollingInterval: !collapsed && activeTab === "metrics" ? metricsMs : 0,
    refetchOnFocus: true,
    refetchOnReconnect: true,
  });

  const {
    data: alertsData,
    isLoading: isAlertsLoading,
    error: alertsError,
  } = useListAlertsQuery(
    { limit: 50 },
    {
      skip: collapsed || activeTab !== "alerts",
      pollingInterval: !collapsed && activeTab === "alerts" ? alertsMs : 0,
      refetchOnFocus: true,
      refetchOnReconnect: true,
    },
  );

  const {
    data: logsData,
    isLoading: isLogsLoading,
    error: logsError,
  } = useListLogsQuery(
    { limit: 100 },
    {
      skip: collapsed || activeTab !== "logs",
      pollingInterval: !collapsed && activeTab === "logs" ? logsMs : 0,
      refetchOnFocus: true,
      refetchOnReconnect: true,
    },
  );

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

  // Filter WebSocket spans by context (when possible)
  const filteredRawSpans = useMemo(() => {
    if (context !== "session" || !entityId) return rawSpans;

    return rawSpans.filter((span) => {
      const attributes = span.attributes ?? {};
      // OTEL semantic attributes use dot notation; Alloy exports with underscores.
      // session_id is a raw OTEL attribute name, not a transformed API response field.
      const sessionAttr =
        (attributes["session.id"] as string | undefined) ??
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
      status: normalizeTraceSpanStatus(span.status),
      serviceName:
        (span.attributes?.service_name as string | undefined) ??
        (span.attributes?.["service.name"] as string | undefined),
      depth: 0, // Will be calculated by TracesTab based on parentSpanId
      attributes: span.attributes,
    }));
  }, [filteredRawSpans]);

  const traceDetailSpans: TraceSpan[] = useMemo(() => {
    if (!selectedTraceId || !selectedTraceData?.spans?.length) return [];

    return selectedTraceData.spans.map((span, index) => {
      const startTime = span.startTime ? new Date(span.startTime).getTime() : 0;
      const endTime = span.endTime ? new Date(span.endTime).getTime() : null;
      const durationMs =
        span.durationMs ?? (endTime && startTime ? endTime - startTime : 0);
      const attributes = span.attributes ?? {};

      return {
        spanId: span.spanId ?? `span-${index}`,
        traceId: selectedTraceData.traceId ?? selectedTraceId,
        parentSpanId: span.parentSpanId ?? null,
        name: span.name || "Unknown",
        startTime,
        durationMs: durationMs ?? 0,
        status: normalizeTraceSpanStatus(span.status),
        serviceName:
          (attributes["service.name"] as string | undefined) ??
          (attributes.service_name as string | undefined),
        depth: span.depth ?? 0,
        attributes,
        errorMessage: span.errorMessage ?? undefined,
      };
    });
  }, [selectedTraceId, selectedTraceData]);

  const mergedTraceSpans: TraceSpan[] = useMemo(() => {
    if (traceDetailSpans.length === 0) return traceSpans;
    const spansById = new Map<string, TraceSpan>();
    for (const span of traceDetailSpans) {
      spansById.set(span.spanId, span);
    }
    for (const span of traceSpans) {
      spansById.set(span.spanId, span);
    }
    return Array.from(spansById.values());
  }, [traceDetailSpans, traceSpans]);

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
      // Include trace correlation for trace-log linking (when available from API)
      traceId: (log as { traceId?: string }).traceId,
      spanId: (log as { spanId?: string }).spanId,
      attributes: (log as { attributes?: Record<string, unknown> }).attributes,
    }));
  }, [logsData]);

  // Metrics history tracking for trend computation (extracted to reusable hook)
  const { addSnapshot, getMetricsWithTrends } = useMetricsHistory();

  // Update metrics history when new data arrives
  useEffect(() => {
    if (!metricsData) return;
    addSnapshot({
      requestsTotal: metricsData.requestsTotal,
      errorsTotal: metricsData.errorsTotal,
      avgLatencyMs: metricsData.avgLatencyMs,
      p99LatencyMs: metricsData.p99LatencyMs,
      tokensUsed: metricsData.tokensUsed,
      activeSessions: metricsData.activeSessions,
    });
  }, [metricsData, addSnapshot]);

  // Transform API metrics to DevTools MetricsTab format with computed trends
  const metricsList = useMemo(() => {
    if (!metricsData) return [];
    return getMetricsWithTrends({
      requestsTotal: metricsData.requestsTotal,
      errorsTotal: metricsData.errorsTotal,
      avgLatencyMs: metricsData.avgLatencyMs,
      p99LatencyMs: metricsData.p99LatencyMs,
      tokensUsed: metricsData.tokensUsed,
      activeSessions: metricsData.activeSessions,
    });
  }, [metricsData, getMetricsWithTrends]);

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

  /**
   * Handle jumping from logs to a related trace.
   * Switches to the traces tab and selects the specified trace.
   */
  const handleJumpToTrace = useCallback(
    (traceId: string) => {
      setSelectedTraceId(traceId);
      dispatch(setActiveTab("traces"));
    },
    [dispatch],
  );

  /**
   * Handle trace selection in TracesTab.
   * Clears selection when null.
   */
  const handleTraceSelect = useCallback((traceId: string | null) => {
    setSelectedTraceId(traceId);
  }, []);

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
                spans={mergedTraceSpans}
                selectedTraceId={selectedTraceId ?? undefined}
                onTraceSelect={handleTraceSelect}
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
                onJumpToTrace={handleJumpToTrace}
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
          "bg-neutral-1",
          "border-t border-neutral-5",
          className,
        )}
      >
        {/* Header */}
        <div
          data-testid="devtools-header"
          className={cn(
            "flex items-center justify-between px-3 py-1.5",
            "bg-neutral-1",
            "border-b border-neutral-5",
          )}
        >
          {/* Context Indicator + WebSocket Status */}
          <div className="flex items-center gap-3">
            <span className="text-xs font-medium text-neutral-11">
              {contextLabel}
            </span>

            {/* WebSocket Reconnection Status */}
            {devToolsWsStatus === "connecting" &&
              devToolsReconnectAttempts > 0 && (
                <div
                  data-testid="devtools-reconnecting-indicator"
                  className="flex items-center gap-1 text-warning-9 dark:text-warning-9 text-xs"
                >
                  <Loader2 className="w-3 h-3 animate-spin" />
                  <span>Reconnecting ({devToolsReconnectAttempts})...</span>
                </div>
              )}
            {devToolsWsStatus === "error" && (
              <div
                data-testid="devtools-error-indicator"
                className="flex items-center gap-1 text-error-10 dark:text-error-7 text-xs"
              >
                <AlertTriangle className="w-3 h-3" />
                <span>Connection error</span>
              </div>
            )}
            {devToolsWsStatus === "connected" && (
              <div
                data-testid="devtools-connected-indicator"
                className="flex items-center gap-1 text-success-10 dark:text-success-7 text-xs"
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
            <Button
              variant="ghost"
              size="icon"
              onClick={handleClearConsole}
              title="Clear Console"
              aria-label="Clear"
            >
              <Trash2 size={14} />
            </Button>

            {/* Maximize/Minimize */}
            <Button
              variant="ghost"
              size="icon"
              onClick={handleMaximize}
              title={maximized ? "Minimize" : "Maximize"}
              aria-label={maximized ? "Minimize" : "Maximize"}
            >
              {maximized ? <Minimize2 size={14} /> : <Maximize2 size={14} />}
            </Button>

            {/* Collapse */}
            <Button
              variant="ghost"
              size="icon"
              onClick={handleCollapse}
              title="Collapse"
              aria-label="Collapse"
            >
              <X size={14} />
            </Button>
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
            "bg-neutral-2",
            "border-b border-neutral-5",
          )}
        >
          {availableTabs.map((tabId) => {
            const Icon = TAB_ICONS[tabId];
            const isActive = tabId === activeTab;

            return (
              <motion.button
                key={tabId}
                data-testid={`devtools-tab-${tabId}`}
                role="tab"
                type="button"
                aria-selected={isActive}
                aria-controls={`tabpanel-${tabId}`}
                onClick={() => handleTabSelect(tabId)}
                className={devToolsTabVariants({ active: isActive })}
                variants={
                  prefersReducedMotion ? undefined : motionButtonVariants
                }
                initial="rest"
                whileHover="hover"
                whileTap="pressed"
              >
                <Icon size={14} />
                {TAB_LABELS[tabId]}
              </motion.button>
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
