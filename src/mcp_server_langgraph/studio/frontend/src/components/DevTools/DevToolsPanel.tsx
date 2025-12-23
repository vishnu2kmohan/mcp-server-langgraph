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

import { useCallback, Suspense, lazy } from "react";
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
} from "lucide-react";
import { useAppDispatch, useAppSelector } from "../../store/hooks";
import {
  toggleDevTools,
  setActiveTab,
  setMaximized,
  setConsoleFilter,
  selectDevToolsCollapsed,
  selectDevToolsMaximized,
  selectActiveTab,
  selectConsoleFilter,
  selectAvailableTabs,
  type DevToolsTabId,
  type ConsoleFilterLevel,
} from "../../store/slices/devToolsSlice";
import { useDevToolsContext } from "./hooks/useDevToolsContext";
import type { DevToolsPanelProps } from "./types";

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
};

const TAB_LABELS: Record<DevToolsTabId, string> = {
  console: "Console",
  "agent-trace": "Agent Trace",
  "execution-trace": "Execution Trace",
  network: "Network",
  state: "State",
  problems: "Problems",
  "ai-insights": "AI Insights",
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

// =============================================================================
// Tab Content Loader
// =============================================================================

function TabContentLoader() {
  return (
    <div className="flex items-center justify-center h-full">
      <Loader2 className="w-6 h-6 animate-spin text-gray-400" />
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
          "border border-gray-200 dark:border-gray-600",
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
        className="absolute right-1.5 top-1/2 -translate-y-1/2 pointer-events-none text-gray-500"
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
    // TODO: Dispatch clear console action
    console.log("Clear console");
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
          <div data-testid="devtools-tab-content-console">
            <Suspense fallback={<TabContentLoader />}>
              <ConsoleTabContent
                filter={consoleFilter}
                onFilterChange={handleFilterChange}
                contextEntityId={entityId}
              />
            </Suspense>
          </div>
        );
      case "network":
        return (
          <div data-testid="devtools-tab-content-network">
            <Suspense fallback={<TabContentLoader />}>
              <NetworkTabContent contextEntityId={entityId} />
            </Suspense>
          </div>
        );
      case "state":
        return (
          <div data-testid="devtools-tab-content-state">
            <Suspense fallback={<TabContentLoader />}>
              <StateTabContent context={context} contextEntityId={entityId} />
            </Suspense>
          </div>
        );
      case "problems":
        return (
          <div data-testid="devtools-tab-content-problems">
            <Suspense fallback={<TabContentLoader />}>
              <ProblemsTabContent compact />
            </Suspense>
          </div>
        );
      case "agent-trace":
        return (
          <div data-testid="devtools-tab-content-agent-trace">
            <Suspense fallback={<TabContentLoader />}>
              <AgentTraceTabContent sessionId={entityId ?? ""} />
            </Suspense>
          </div>
        );
      case "execution-trace":
        return (
          <div data-testid="devtools-tab-content-execution-trace">
            <Suspense fallback={<TabContentLoader />}>
              <ExecutionTraceTabContent workflowId={entityId ?? ""} />
            </Suspense>
          </div>
        );
      case "ai-insights":
        return (
          <div data-testid="devtools-tab-content-ai-insights">
            <Suspense fallback={<TabContentLoader />}>
              <AIInsightsTabContent
                context={context}
                contextEntityId={entityId ?? ""}
              />
            </Suspense>
          </div>
        );
      default:
        return null;
    }
  };

  return (
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
        {/* Context Indicator */}
        <div className="flex items-center gap-2">
          <span className="text-xs font-medium text-gray-600 dark:text-gray-300">
            {contextLabel}
          </span>
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
              "text-gray-500 hover:text-gray-700 dark:text-gray-400 dark:hover:text-gray-200",
              "hover:bg-gray-100 dark:hover:bg-gray-700",
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
              "text-gray-500 hover:text-gray-700 dark:text-gray-400 dark:hover:text-gray-200",
              "hover:bg-gray-100 dark:hover:bg-gray-700",
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
              "text-gray-500 hover:text-gray-700 dark:text-gray-400 dark:hover:text-gray-200",
              "hover:bg-gray-100 dark:hover:bg-gray-700",
            )}
            title="Collapse"
            aria-label="Collapse"
          >
            <X size={14} />
          </button>
        </div>
      </div>

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
        className="flex-1 overflow-auto"
      >
        {renderTabContent()}
      </div>
    </div>
  );
}

export default DevToolsPanel;
