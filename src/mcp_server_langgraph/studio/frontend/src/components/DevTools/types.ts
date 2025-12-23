/**
 * DevTools Component Types
 *
 * Shared types for the Chrome DevTools-like debugging panel.
 */

// Re-export slice types for convenience
export type {
  DevToolsTabId,
  DevToolsContext,
  ConsoleFilterLevel,
  DevToolsState,
} from "../../store/slices/devToolsSlice";

// =============================================================================
// Console Entry Types
// =============================================================================

/** Log level for console entries */
export type ConsoleLogLevel = "info" | "warning" | "error" | "debug";

/** Source of console entries */
export type ConsoleEntrySource =
  | "notification"
  | "execution"
  | "mcp"
  | "api"
  | "websocket"
  | "system";

/** Single entry in the console log */
export interface ConsoleEntry {
  /** Unique identifier */
  id: string;
  /** Log level */
  level: ConsoleLogLevel;
  /** Source of the entry */
  source: ConsoleEntrySource;
  /** Human-readable message */
  message: string;
  /** Unix timestamp in milliseconds */
  timestamp: number;
  /** Optional structured data */
  data?: Record<string, unknown>;
  /** Optional stack trace for errors */
  stackTrace?: string;
}

// =============================================================================
// Network Tab Types
// =============================================================================

/** HTTP method for network requests */
export type HttpMethod =
  | "GET"
  | "POST"
  | "PUT"
  | "DELETE"
  | "PATCH"
  | "OPTIONS";

/** Status of a network request */
export type NetworkRequestStatus =
  | "pending"
  | "completed"
  | "error"
  | "cancelled";

/** Single network request entry */
export interface NetworkEntry {
  /** Unique identifier */
  id: string;
  /** Request method */
  method: HttpMethod;
  /** Request URL */
  url: string;
  /** HTTP status code */
  statusCode?: number;
  /** Status text (e.g., "OK", "Not Found") */
  statusText?: string;
  /** Request status */
  status: NetworkRequestStatus;
  /** Duration in milliseconds */
  duration?: number;
  /** Request size in bytes */
  requestSize?: number;
  /** Response size in bytes */
  responseSize?: number;
  /** Start timestamp */
  startTime: number;
  /** End timestamp */
  endTime?: number;
  /** Request headers */
  requestHeaders?: Record<string, string>;
  /** Response headers */
  responseHeaders?: Record<string, string>;
  /** Request body (for debugging) */
  requestBody?: unknown;
  /** Response body (for debugging) */
  responseBody?: unknown;
  /** Source identifier (e.g., MCP server name) */
  source?: string;
}

// =============================================================================
// AI Insights Types
// =============================================================================

/** Type of AI insight */
export type AIInsightType =
  | "anomaly"
  | "performance"
  | "cost"
  | "suggestion"
  | "warning";

/** Severity level for AI insights */
export type AIInsightSeverity = "low" | "medium" | "high" | "critical";

/** Single AI-generated insight */
export interface AIInsight {
  /** Unique identifier */
  id: string;
  /** Type of insight */
  type: AIInsightType;
  /** Severity level */
  severity: AIInsightSeverity;
  /** Title of the insight */
  title: string;
  /** Detailed description */
  description: string;
  /** Timestamp when generated */
  timestamp: number;
  /** Confidence score (0-1) */
  confidence: number;
  /** Related entity ID (session, workflow, trace) */
  entityId?: string;
  /** Suggested action */
  suggestedAction?: string;
  /** Whether the insight has been dismissed */
  dismissed?: boolean;
}

// =============================================================================
// Tab Configuration Types
// =============================================================================

/** Tab configuration with metadata */
export interface DevToolsTabConfig {
  /** Tab ID */
  id: string;
  /** Display label */
  label: string;
  /** Icon name from lucide-react */
  icon: string;
  /** Whether the tab is visible in current context */
  visible: boolean;
  /** Whether the tab has issues to highlight */
  hasIssues?: boolean;
  /** Issue count for badge */
  issueCount?: number;
}

// =============================================================================
// Component Props Types
// =============================================================================

/** Props for DevToolsPanel */
export interface DevToolsPanelProps {
  /** Additional CSS classes */
  className?: string;
}

/** Props for DevToolsHeader */
export interface DevToolsHeaderProps {
  /** Callback when collapse button clicked */
  onCollapse?: () => void;
  /** Callback when maximize button clicked */
  onMaximize?: () => void;
  /** Callback when clear console clicked */
  onClearConsole?: () => void;
  /** Whether AI toggle is visible */
  showAIToggle?: boolean;
}

/** Props for DevToolsTabs */
export interface DevToolsTabsProps {
  /** Currently active tab */
  activeTab: string;
  /** Available tabs to display */
  tabs: DevToolsTabConfig[];
  /** Callback when tab selected */
  onTabSelect: (tabId: string) => void;
  /** AI suggested tab order (for visual hints) */
  aiSuggestedOrder?: string[];
}

/** Props for ConsoleTab */
export interface ConsoleTabProps {
  /** Filter level */
  filter: "all" | "info" | "warning" | "error";
  /** Callback to change filter */
  onFilterChange: (filter: "all" | "info" | "warning" | "error") => void;
  /** Context entity ID for filtering */
  contextEntityId?: string | null;
}

/** Props for StateTab */
export interface StateTabProps {
  /** Context type */
  context: "session" | "workflow" | "global";
  /** Context entity ID */
  contextEntityId?: string | null;
}

/** Props for AgentTraceTab */
export interface AgentTraceTabProps {
  /** Session ID to display traces for */
  sessionId: string;
  /** Callback when node is highlighted */
  onNodeHighlight?: (nodeId: string | null) => void;
}

/** Props for ExecutionTraceTab */
export interface ExecutionTraceTabProps {
  /** Workflow ID to display execution for */
  workflowId: string;
  /** Callback when node is highlighted */
  onNodeHighlight?: (nodeId: string | null) => void;
}

/** Props for NetworkTab */
export interface NetworkTabProps {
  /** Context entity ID for filtering */
  contextEntityId?: string | null;
  /** Whether to show MCP tool calls */
  showMCPCalls?: boolean;
}

/** Props for ProblemsTab */
export interface ProblemsTabProps {
  /** Whether to show problem count */
  showCount?: boolean;
  /** Compact display mode */
  compact?: boolean;
}

/** Props for AIInsightsTab */
export interface AIInsightsTabProps {
  /** Context type */
  context: "session" | "workflow" | "global";
  /** Context entity ID */
  contextEntityId: string;
}

// =============================================================================
// OTEL Observability Tab Types
// =============================================================================

/** OTEL trace span status */
export type TraceSpanStatus = "ok" | "error" | "unset";

/** OTEL span kind */
export type SpanKind =
  | "internal"
  | "server"
  | "client"
  | "producer"
  | "consumer";

/** Alert state */
export type AlertState = "firing" | "pending" | "resolved" | "silenced";

/** Alert severity */
export type AlertSeverity = "critical" | "warning" | "info";

/** Log level for OTEL logs */
export type OTELLogLevel =
  | "trace"
  | "debug"
  | "info"
  | "warn"
  | "error"
  | "fatal";

/** Props for TracesTab */
export interface TracesTabProps {
  /** Optional trace ID to highlight/filter */
  traceId?: string;
  /** Optional service filter */
  serviceFilter?: string;
  /** Optional status filter */
  statusFilter?: TraceSpanStatus;
  /** Callback when span is selected */
  onSpanSelect?: (spanId: string) => void;
}

/** Props for MetricsTab */
export interface MetricsTabProps {
  /** Time range for metrics display */
  timeRange?: "15m" | "1h" | "24h" | "7d";
  /** Auto-refresh interval in seconds */
  refreshInterval?: number;
  /** Specific metrics to display */
  metricFilter?: string[];
}

/** Props for AlertsTab */
export interface AlertsTabProps {
  /** Filter by alert state */
  stateFilter?: AlertState;
  /** Filter by severity */
  severityFilter?: AlertSeverity;
  /** Filter by service */
  serviceFilter?: string;
  /** Callback when alert is selected */
  onAlertSelect?: (alertId: string) => void;
}

/** Props for LogsTab */
export interface LogsTabProps {
  /** Filter by log level */
  levelFilter?: OTELLogLevel;
  /** Filter by service */
  serviceFilter?: string;
  /** Optional trace ID to correlate logs */
  traceId?: string;
  /** Callback when log entry with trace is clicked */
  onJumpToTrace?: (traceId: string) => void;
}
