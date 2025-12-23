/**
 * Lazy Loading for DevTools Components
 *
 * Code-splits DevTools tabs for better initial load performance.
 * Each tab is loaded on-demand when first accessed.
 */
import { lazy } from "react";

// =============================================================================
// Lazy-loaded Tabs
// =============================================================================

/**
 * Console tab - logs, notifications, errors
 */
export const LazyConsoleTab = lazy(() =>
  import("./tabs/ConsoleTab").then((m) => ({ default: m.ConsoleTab })),
);

/**
 * Problems tab - aggregated errors/warnings
 */
export const LazyProblemsTab = lazy(() =>
  import("./tabs/ProblemsTab").then((m) => ({ default: m.ProblemsTab })),
);

/**
 * State tab - Redux/session/workflow state inspection
 */
export const LazyStateTab = lazy(() =>
  import("./tabs/StateTab").then((m) => ({ default: m.StateTab })),
);

/**
 * Agent Trace tab - LangGraph node visualization (session context)
 */
export const LazyAgentTraceTab = lazy(() =>
  import("./tabs/AgentTraceTab").then((m) => ({ default: m.AgentTraceTab })),
);

/**
 * Execution Trace tab - Workflow node execution (workflow context)
 */
export const LazyExecutionTraceTab = lazy(() =>
  import("./tabs/ExecutionTraceTab").then((m) => ({
    default: m.ExecutionTraceTab,
  })),
);

/**
 * Network tab - API/WebSocket/MCP calls
 */
export const LazyNetworkTab = lazy(() =>
  import("./tabs/NetworkTab").then((m) => ({ default: m.NetworkTab })),
);

/**
 * AI Insights tab - AI-generated insights, anomalies, suggestions
 */
export const LazyAIInsightsTab = lazy(() =>
  import("./tabs/AIInsightsTab").then((m) => ({ default: m.AIInsightsTab })),
);

// =============================================================================
// OTEL Observability Tabs
// =============================================================================

/**
 * Traces tab - OTEL distributed traces with waterfall view
 */
export const LazyTracesTab = lazy(() =>
  import("./tabs/TracesTab").then((m) => ({ default: m.TracesTab })),
);

/**
 * Metrics tab - OTEL/HEART metrics panels with sparklines
 */
export const LazyMetricsTab = lazy(() =>
  import("./tabs/MetricsTab").then((m) => ({ default: m.MetricsTab })),
);

/**
 * Alerts tab - Grafana alerts integration
 */
export const LazyAlertsTab = lazy(() =>
  import("./tabs/AlertsTab").then((m) => ({ default: m.AlertsTab })),
);

/**
 * Logs tab - OTEL structured logs with trace correlation
 */
export const LazyLogsTab = lazy(() =>
  import("./tabs/LogsTab").then((m) => ({ default: m.LogsTab })),
);

// =============================================================================
// Lazy-loaded Main Panel (for StudioShellLayout)
// =============================================================================

/**
 * DevTools Panel - main container with header and tabs
 */
export const LazyDevToolsPanel = lazy(() =>
  import("./DevToolsPanel").then((m) => ({ default: m.DevToolsPanel })),
);

// =============================================================================
// Preload Functions
// =============================================================================

/**
 * Preload commonly used tabs to improve UX
 */
export function preloadCommonTabs(): void {
  // Preload console and problems tabs (most commonly used)
  import("./tabs/ConsoleTab");
  import("./tabs/ProblemsTab");
}

/**
 * Preload all DevTools tabs
 */
export function preloadAllTabs(): void {
  import("./tabs/ConsoleTab");
  import("./tabs/ProblemsTab");
  import("./tabs/StateTab");
  import("./tabs/AgentTraceTab");
  import("./tabs/ExecutionTraceTab");
  import("./tabs/NetworkTab");
  import("./tabs/AIInsightsTab");
  // OTEL tabs
  import("./tabs/TracesTab");
  import("./tabs/MetricsTab");
  import("./tabs/AlertsTab");
  import("./tabs/LogsTab");
}

/**
 * Preload context-specific tabs
 */
export function preloadContextTabs(
  context: "session" | "workflow" | "global",
): void {
  // Always preload common tabs
  import("./tabs/ConsoleTab");
  import("./tabs/ProblemsTab");
  import("./tabs/StateTab");
  import("./tabs/NetworkTab");

  // Context-specific tabs
  if (context === "session") {
    import("./tabs/AgentTraceTab");
    import("./tabs/AIInsightsTab");
    // OTEL tabs for session observability
    import("./tabs/TracesTab");
    import("./tabs/MetricsTab");
    import("./tabs/AlertsTab");
    import("./tabs/LogsTab");
  } else if (context === "workflow") {
    import("./tabs/ExecutionTraceTab");
    import("./tabs/AIInsightsTab");
    // OTEL tabs for workflow observability
    import("./tabs/TracesTab");
    import("./tabs/MetricsTab");
    import("./tabs/AlertsTab");
    import("./tabs/LogsTab");
  } else {
    // Global context - all OTEL tabs
    import("./tabs/TracesTab");
    import("./tabs/MetricsTab");
    import("./tabs/AlertsTab");
    import("./tabs/LogsTab");
  }
}

/**
 * Preload OTEL observability tabs only
 */
export function preloadOTELTabs(): void {
  import("./tabs/TracesTab");
  import("./tabs/MetricsTab");
  import("./tabs/AlertsTab");
  import("./tabs/LogsTab");
}
