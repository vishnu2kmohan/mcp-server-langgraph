/**
 * ExecutionTracePanel Component
 *
 * Real-time visualization of LangGraph execution events.
 * Features:
 * - Live execution log display
 * - Log level filtering (info, warning, error)
 * - Node ID filtering
 * - Auto-scroll to latest events
 * - Expandable log details
 * - Node highlighting on hover
 * - Execution state indicators
 */

import { useState, useRef, useEffect, useCallback, memo } from "react";
import {
  Loader2,
  CheckCircle,
  XCircle,
  AlertTriangle,
  Info,
  Trash2,
  ArrowDownToLine,
  ChevronDown,
  ChevronRight,
} from "lucide-react";
import { useAppDispatch, useAppSelector } from "../../store/hooks";
import {
  selectExecutionState,
  selectExecutionLogs,
  clearExecutionLogs,
} from "../../store/slices/workflowSlice";
import type { ExecutionLog, ExecutionState } from "../../types/workflow";

// ============================================================================
// Types
// ============================================================================

interface ExecutionTracePanelProps {
  /** Callback when a node should be highlighted in the canvas */
  onNodeHighlight?: (nodeId: string | null) => void;
}

type LogLevelFilter = "all" | "info" | "warning" | "error";

// ============================================================================
// Utility Functions
// ============================================================================

function formatRelativeTime(timestamp: number): string {
  const now = Date.now();
  const diff = now - timestamp;

  if (diff < 1000) return "just now";
  if (diff < 60000) return `${Math.floor(diff / 1000)}s ago`;
  if (diff < 3600000) return `${Math.floor(diff / 60000)}m ago`;
  return `${Math.floor(diff / 3600000)}h ago`;
}

function getLogLevelIcon(level: string) {
  switch (level) {
    case "error":
      return <XCircle className="w-4 h-4 text-red-500" />;
    case "warning":
      return <AlertTriangle className="w-4 h-4 text-yellow-500" />;
    case "info":
    default:
      return <Info className="w-4 h-4 text-blue-500" />;
  }
}

function getLogLevelClass(level: string): string {
  switch (level) {
    case "error":
      return "bg-red-50 border-red-200 dark:bg-red-900/20 dark:border-red-800";
    case "warning":
      return "bg-yellow-50 border-yellow-200 dark:bg-yellow-900/20 dark:border-yellow-800";
    default:
      return "bg-gray-50 border-gray-200 dark:bg-gray-800/50 dark:border-gray-700";
  }
}

// ============================================================================
// Sub-components
// ============================================================================

interface ExecutionStateIndicatorProps {
  state: ExecutionState;
}

const ExecutionStateIndicator = memo(
  ({ state }: ExecutionStateIndicatorProps) => {
    const getStateUI = () => {
      switch (state) {
        case "running":
          return (
            <div className="flex items-center gap-2 text-blue-600 dark:text-blue-400">
              <Loader2
                className="w-4 h-4 animate-spin"
                data-testid="execution-spinner"
              />
              <span>Running</span>
            </div>
          );
        case "completed":
          return (
            <div className="flex items-center gap-2 text-green-600 dark:text-green-400">
              <CheckCircle className="w-4 h-4" />
              <span>Completed</span>
            </div>
          );
        case "error":
          return (
            <div className="flex items-center gap-2 text-red-600 dark:text-red-400">
              <XCircle className="w-4 h-4" />
              <span>Error</span>
            </div>
          );
        case "idle":
        default:
          return (
            <div className="flex items-center gap-2 text-gray-500 dark:text-gray-400">
              <div className="w-3 h-3 rounded-full bg-gray-300 dark:bg-gray-600" />
              <span>Idle</span>
            </div>
          );
      }
    };

    return (
      <div className="flex items-center text-sm font-medium">
        {getStateUI()}
      </div>
    );
  },
);

ExecutionStateIndicator.displayName = "ExecutionStateIndicator";

interface LogEntryProps {
  log: ExecutionLog;
  isExpanded: boolean;
  onToggle: () => void;
  onMouseEnter: () => void;
  onMouseLeave: () => void;
}

const LogEntry = memo(
  ({
    log,
    isExpanded,
    onToggle,
    onMouseEnter,
    onMouseLeave,
  }: LogEntryProps) => {
    const hasDetails = log.data !== undefined;

    return (
      <div
        data-node-id={log.nodeId}
        className={`
          border rounded-md p-2 transition-colors cursor-pointer
          ${getLogLevelClass(log.level)}
          hover:shadow-sm
        `}
        onClick={hasDetails ? onToggle : undefined}
        onMouseEnter={onMouseEnter}
        onMouseLeave={onMouseLeave}
      >
        <div className="flex items-start gap-2">
          {getLogLevelIcon(log.level)}
          <div className="flex-1 min-w-0">
            <div className="flex items-center justify-between gap-2">
              <span className="text-sm text-gray-900 dark:text-gray-100 truncate">
                {log.message}
              </span>
              <span className="text-xs text-gray-500 dark:text-gray-400 shrink-0">
                {formatRelativeTime(log.timestamp)}
              </span>
            </div>
            {log.nodeId && (
              <span className="text-xs text-gray-500 dark:text-gray-400">
                Node: {log.nodeId}
              </span>
            )}
          </div>
          {hasDetails && (
            <button className="text-gray-400 hover:text-gray-600 dark:hover:text-gray-300">
              {isExpanded ? (
                <ChevronDown className="w-4 h-4" />
              ) : (
                <ChevronRight className="w-4 h-4" />
              )}
            </button>
          )}
        </div>

        {/* Expandable details */}
        {isExpanded && log.data && (
          <div className="mt-2 pt-2 border-t border-gray-200 dark:border-gray-700">
            <pre className="text-xs bg-white dark:bg-gray-900 p-2 rounded overflow-auto max-h-40">
              {typeof log.data === "object" ? (
                <>
                  {log.data.output && <div>{log.data.output}</div>}
                  {log.data.tokens !== undefined && (
                    <div className="text-gray-500">
                      tokens: {log.data.tokens}
                    </div>
                  )}
                  {!log.data.output && !log.data.tokens && (
                    <div>{JSON.stringify(log.data, null, 2)}</div>
                  )}
                </>
              ) : (
                String(log.data)
              )}
            </pre>
          </div>
        )}
      </div>
    );
  },
);

LogEntry.displayName = "LogEntry";

// ============================================================================
// Main Component
// ============================================================================

export const ExecutionTracePanel = memo(
  ({ onNodeHighlight }: ExecutionTracePanelProps) => {
    const dispatch = useAppDispatch();
    const executionState = useAppSelector(selectExecutionState);
    const executionLogs = useAppSelector(selectExecutionLogs);

    const [levelFilter, setLevelFilter] = useState<LogLevelFilter>("all");
    const [nodeFilter, setNodeFilter] = useState("");
    const [autoScroll, setAutoScroll] = useState(true);
    const [expandedLogs, setExpandedLogs] = useState<Set<string>>(new Set());

    const logsEndRef = useRef<HTMLDivElement>(null);

    // Auto-scroll to bottom when new logs arrive
    useEffect(() => {
      if (autoScroll && logsEndRef.current?.scrollIntoView) {
        logsEndRef.current.scrollIntoView({ behavior: "smooth" });
      }
    }, [executionLogs, autoScroll]);

    // Filter logs based on level and node
    const filteredLogs = executionLogs.filter((log) => {
      // Level filter
      if (levelFilter !== "all" && log.level !== levelFilter) {
        return false;
      }

      // Node filter
      if (nodeFilter.trim()) {
        const filterLower = nodeFilter.toLowerCase();
        const nodeMatch = log.nodeId?.toLowerCase().includes(filterLower);
        const messageMatch = log.message.toLowerCase().includes(filterLower);
        if (!nodeMatch && !messageMatch) {
          return false;
        }
      }

      return true;
    });

    const handleClearLogs = useCallback(() => {
      dispatch(clearExecutionLogs());
    }, [dispatch]);

    const handleToggleExpand = useCallback((logId: string) => {
      setExpandedLogs((prev) => {
        const next = new Set(prev);
        if (next.has(logId)) {
          next.delete(logId);
        } else {
          next.add(logId);
        }
        return next;
      });
    }, []);

    const handleNodeHighlight = useCallback(
      (nodeId: string | null) => {
        onNodeHighlight?.(nodeId);
      },
      [onNodeHighlight],
    );

    return (
      <div className="flex flex-col h-full bg-white dark:bg-gray-900 border-l border-gray-200 dark:border-gray-700">
        {/* Header */}
        <div className="flex items-center justify-between p-3 border-b border-gray-200 dark:border-gray-700">
          <h2 className="text-sm font-semibold text-gray-900 dark:text-gray-100">
            Execution Trace
          </h2>
          <ExecutionStateIndicator state={executionState} />
        </div>

        {/* Toolbar */}
        <div className="flex items-center gap-2 p-2 border-b border-gray-200 dark:border-gray-700">
          {/* Level filters */}
          <div className="flex items-center gap-1">
            <button
              onClick={() => setLevelFilter("all")}
              className={`px-2 py-1 text-xs rounded ${
                levelFilter === "all"
                  ? "bg-gray-200 dark:bg-gray-700"
                  : "hover:bg-gray-100 dark:hover:bg-gray-800"
              }`}
            >
              All
            </button>
            <button
              onClick={() => setLevelFilter("error")}
              aria-label="Errors"
              className={`px-2 py-1 text-xs rounded ${
                levelFilter === "error"
                  ? "bg-red-100 text-red-700 dark:bg-red-900/50 dark:text-red-300"
                  : "hover:bg-gray-100 dark:hover:bg-gray-800"
              }`}
            >
              Errors
            </button>
          </div>

          {/* Node filter */}
          <input
            type="text"
            placeholder="Filter by node..."
            value={nodeFilter}
            onChange={(e) => setNodeFilter(e.target.value)}
            className="flex-1 px-2 py-1 text-xs bg-gray-50 dark:bg-gray-800 border border-gray-200 dark:border-gray-700 rounded focus:outline-none focus:ring-1 focus:ring-blue-500"
          />

          {/* Actions */}
          <button
            onClick={() => setAutoScroll(!autoScroll)}
            aria-label="Auto-scroll"
            aria-pressed={autoScroll}
            className={`p-1.5 rounded ${
              autoScroll
                ? "bg-blue-100 text-blue-700 dark:bg-blue-900/50 dark:text-blue-300"
                : "hover:bg-gray-100 dark:hover:bg-gray-800"
            }`}
          >
            <ArrowDownToLine className="w-4 h-4" />
          </button>

          <button
            onClick={handleClearLogs}
            aria-label="Clear"
            className="p-1.5 hover:bg-gray-100 dark:hover:bg-gray-800 rounded text-gray-500 hover:text-red-500"
          >
            <Trash2 className="w-4 h-4" />
          </button>
        </div>

        {/* Logs */}
        <div
          role="log"
          aria-live="polite"
          aria-label="Execution logs"
          className="flex-1 overflow-y-auto p-2 space-y-2"
        >
          {filteredLogs.length === 0 ? (
            <div className="flex flex-col items-center justify-center h-full text-gray-500 dark:text-gray-400">
              <Info className="w-8 h-8 mb-2 opacity-50" />
              <p className="text-sm">No execution events yet</p>
              <p className="text-xs mt-1">
                Events will appear here when a workflow runs
              </p>
            </div>
          ) : (
            filteredLogs.map((log) => (
              <LogEntry
                key={log.id}
                log={log}
                isExpanded={expandedLogs.has(log.id)}
                onToggle={() => handleToggleExpand(log.id)}
                onMouseEnter={() => handleNodeHighlight(log.nodeId ?? null)}
                onMouseLeave={() => handleNodeHighlight(null)}
              />
            ))
          )}
          <div ref={logsEndRef} />
        </div>
      </div>
    );
  },
);

ExecutionTracePanel.displayName = "ExecutionTracePanel";

export default ExecutionTracePanel;
