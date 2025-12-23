/**
 * DevTools Component Exports
 *
 * Chrome DevTools-like debugging panel for Agent Studio.
 */

// Main component
export { DevToolsPanel } from "./DevToolsPanel";
export { default } from "./DevToolsPanel";

// Hooks
export { useDevToolsContext } from "./hooks/useDevToolsContext";
export { useDevToolsKeyboard } from "./hooks/useDevToolsKeyboard";
export { useDevToolsResize } from "./hooks/useDevToolsResize";
export { useDevToolsAI } from "./hooks/useDevToolsAI";
export { useDevToolsWebSocket } from "./hooks/useDevToolsWebSocket";
export { useTraceLinking } from "./hooks/useTraceLinking";
export { useStateHistory } from "./hooks/useStateHistory";
export { useDevToolsTimeline } from "./hooks/useDevToolsTimeline";

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
  preloadCommonTabs,
  preloadAllTabs,
  preloadContextTabs,
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
