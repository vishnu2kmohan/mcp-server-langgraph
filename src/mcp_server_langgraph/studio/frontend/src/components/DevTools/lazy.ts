/**
 * Lazy Loading for DevTools Components
 *
 * Code-splits DevTools tabs for better initial load performance.
 * Each tab is loaded on-demand when first accessed.
 *
 * @deprecated Individual lazy tab exports are deprecated.
 * DevToolsPanel handles internal lazy loading.
 * Only LazyDevToolsPanel is maintained. Will be removed in next major version.
 */
import { lazy } from "react";

// =============================================================================
// DEPRECATED: Lazy-loaded Tabs
// =============================================================================
// These individual tab exports are deprecated. DevToolsPanel handles
// internal lazy loading. Only LazyDevToolsPanel should be used externally.

/**
 * Console tab - logs, notifications, errors
 * @deprecated Use DevToolsPanel instead
 */
export const LazyConsoleTab = lazy(() =>
  import("./tabs/ConsoleTab").then((m) => ({ default: m.ConsoleTab })),
);

/**
 * Problems tab - aggregated errors/warnings
 * @deprecated Use DevToolsPanel instead
 */
export const LazyProblemsTab = lazy(() =>
  import("./tabs/ProblemsTab").then((m) => ({ default: m.ProblemsTab })),
);

/**
 * State tab - Redux/session/workflow state inspection
 * @deprecated Use DevToolsPanel instead
 */
export const LazyStateTab = lazy(() =>
  import("./tabs/StateTab").then((m) => ({ default: m.StateTab })),
);

/**
 * Agent Trace tab - LangGraph node visualization (session context)
 * @deprecated Use DevToolsPanel instead
 */
export const LazyAgentTraceTab = lazy(() =>
  import("./tabs/AgentTraceTab").then((m) => ({ default: m.AgentTraceTab })),
);

/**
 * Execution Trace tab - Workflow node execution (workflow context)
 * @deprecated Use DevToolsPanel instead
 */
export const LazyExecutionTraceTab = lazy(() =>
  import("./tabs/ExecutionTraceTab").then((m) => ({
    default: m.ExecutionTraceTab,
  })),
);

/**
 * Network tab - API/WebSocket/MCP calls
 * @deprecated Use DevToolsPanel instead
 */
export const LazyNetworkTab = lazy(() =>
  import("./tabs/NetworkTab").then((m) => ({ default: m.NetworkTab })),
);

/**
 * AI Insights tab - AI-generated insights, anomalies, suggestions
 * @deprecated Use DevToolsPanel instead
 */
export const LazyAIInsightsTab = lazy(() =>
  import("./tabs/AIInsightsTab").then((m) => ({ default: m.AIInsightsTab })),
);

// =============================================================================
// DEPRECATED: OTEL Observability Tabs
// =============================================================================

/**
 * Traces tab - OTEL distributed traces with waterfall view
 * @deprecated Use DevToolsPanel instead
 */
export const LazyTracesTab = lazy(() =>
  import("./tabs/TracesTab").then((m) => ({ default: m.TracesTab })),
);

/**
 * Metrics tab - OTEL/HEART metrics panels with sparklines
 * @deprecated Use DevToolsPanel instead
 */
export const LazyMetricsTab = lazy(() =>
  import("./tabs/MetricsTab").then((m) => ({ default: m.MetricsTab })),
);

/**
 * Alerts tab - Grafana alerts integration
 * @deprecated Use DevToolsPanel instead
 */
export const LazyAlertsTab = lazy(() =>
  import("./tabs/AlertsTab").then((m) => ({ default: m.AlertsTab })),
);

/**
 * Logs tab - OTEL structured logs with trace correlation
 * @deprecated Use DevToolsPanel instead
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
// DEPRECATED: Preload Functions
// =============================================================================
// These preload functions are deprecated and unused.
// DevToolsPanel handles its own lazy loading.

/**
 * Preload commonly used tabs to improve UX
 * @deprecated No longer used - DevToolsPanel handles lazy loading
 */
export function preloadCommonTabs(): void {
  // Preload console and problems tabs (most commonly used)
  import("./tabs/ConsoleTab");
  import("./tabs/ProblemsTab");
}

/**
 * Preload all DevTools tabs
 * @deprecated No longer used - DevToolsPanel handles lazy loading
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
 * @deprecated No longer used - DevToolsPanel handles lazy loading
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
 * @deprecated No longer used - DevToolsPanel handles lazy loading
 */
export function preloadOTELTabs(): void {
  import("./tabs/TracesTab");
  import("./tabs/MetricsTab");
  import("./tabs/AlertsTab");
  import("./tabs/LogsTab");
}
