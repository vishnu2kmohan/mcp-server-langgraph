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
