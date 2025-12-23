/**
 * DevTools Component Exports
 *
 * Chrome DevTools-like debugging panel for Agent Studio.
 */

// Main component
export { DevToolsPanel } from "./DevToolsPanel";
export { default } from "./DevToolsPanel";

// Timeline Bar
export { TimelineBar } from "./TimelineBar";
export type { TimelineBarProps } from "./TimelineBar";

// Hooks
export { useDevToolsContext } from "./hooks/useDevToolsContext";
export { useDevToolsKeyboard } from "./hooks/useDevToolsKeyboard";
export { useDevToolsResize } from "./hooks/useDevToolsResize";
export { useDevToolsAI } from "./hooks/useDevToolsAI";
export { useDevToolsWebSocket } from "./hooks/useDevToolsWebSocket";
export { useTraceLinking } from "./hooks/useTraceLinking";
export { useStateHistory } from "./hooks/useStateHistory";
export { useDevToolsTimeline } from "./hooks/useDevToolsTimeline";
export { useTimelinePersistence } from "./hooks/useTimelinePersistence";
export { useTimelineKeyboard } from "./hooks/useTimelineKeyboard";
export { useDevToolsWebSocketBridge } from "./hooks/useDevToolsWebSocketBridge";
export { useObservabilityAI } from "./hooks/useObservabilityAI";
export {
  analyzeTraceAnomalies,
  correlateAlerts,
  predictCostTrends,
  generateRootCauseAnalysis,
} from "./hooks/useObservabilityAI";

// OTEL Tabs
export { TracesTab } from "./tabs/TracesTab";
export { MetricsTab } from "./tabs/MetricsTab";
export { AlertsTab } from "./tabs/AlertsTab";
export { LogsTab } from "./tabs/LogsTab";

// Context providers
export {
  DevToolsTimelineProvider,
  useTimelineContext,
} from "./context/DevToolsTimelineProvider";

export type {
  TimelineContextValue,
  DevToolsTimelineProviderProps,
} from "./context/DevToolsTimelineProvider";

// Lazy loading
export {
  LazyDevToolsPanel,
  LazyConsoleTab,
  LazyProblemsTab,
  LazyStateTab,
  LazyAgentTraceTab,
  LazyExecutionTraceTab,
  LazyNetworkTab,
  LazyAIInsightsTab,
  // OTEL tabs
  LazyTracesTab,
  LazyMetricsTab,
  LazyAlertsTab,
  LazyLogsTab,
  // Preload functions
  preloadCommonTabs,
  preloadAllTabs,
  preloadContextTabs,
  preloadOTELTabs,
} from "./lazy";

// Performance utilities
export {
  useBatchedUpdates,
  useDebouncedValue,
  useThrottledCallback,
  useVirtualList,
  useMemoizedFilter,
  useStableCallback,
  useRenderCount,
  measureTime,
  useLazyInit,
  useIntersectionObserver,
} from "./utils/performance";

// Export utilities
export {
  exportToJSON,
  exportToCSV,
  downloadFile,
  formatConsoleEntriesForExport,
  formatNetworkEntriesForExport,
  exportConsoleToJSON,
  exportConsoleToCSV,
  exportNetworkToJSON,
  exportNetworkToCSV,
} from "./utils/export";

// Types
export type {
  DevToolsTabId,
  DevToolsContext,
  ConsoleFilterLevel,
  DevToolsState,
  ConsoleLogLevel,
  ConsoleEntrySource,
  ConsoleEntry,
  NetworkEntry,
  AIInsight,
  DevToolsTabConfig,
  DevToolsPanelProps,
  DevToolsHeaderProps,
  DevToolsTabsProps,
  ConsoleTabProps,
  StateTabProps,
  AgentTraceTabProps,
  ExecutionTraceTabProps,
  NetworkTabProps,
  ProblemsTabProps,
  AIInsightsTabProps,
  // OTEL Observability types
  TraceSpanStatus,
  SpanKind,
  AlertState,
  AlertSeverity,
  OTELLogLevel,
  TracesTabProps,
  MetricsTabProps,
  AlertsTabProps,
  LogsTabProps,
} from "./types";

// Timeline types
export type {
  TimelineEvent,
  TimelineEventType,
  TimelineBookmark,
  SpanHierarchy,
  SpanStats,
  TimeWindow,
  ActiveFilters,
  UseDevToolsTimelineOptions,
  UseDevToolsTimelineReturn,
} from "./hooks/useDevToolsTimeline";

// Observability AI types
export type {
  SpanData,
  AlertData as ObservabilityAlertData,
  MetricData as ObservabilityMetricData,
  TraceAnomalies,
  AlertCorrelation,
  CostPrediction,
  RootCauseAnalysis,
  ObservabilityInsights,
  SuggestedAction,
  UseObservabilityAIOptions,
  UseObservabilityAIReturn,
} from "./hooks/useObservabilityAI";
