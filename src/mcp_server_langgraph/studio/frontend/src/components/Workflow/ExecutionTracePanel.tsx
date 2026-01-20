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

import { Button, Input } from "@/components/UI";

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
      return <XCircle className="w-4 h-4 text-error-9" />;
    case "warning":
      return <AlertTriangle className="w-4 h-4 text-warning-9" />;
    case "info":
    default:
      return <Info className="w-4 h-4 text-primary-9" />;
  }
}

function getLogLevelClass(level: string): string {
  switch (level) {
    case "error":
      return "bg-error-1 border-error-4 dark:bg-error-a3 dark:border-error-11";
    case "warning":
      return "bg-warning-3 border-warning-6 bg-warning-3 dark:border-warning-11";
    default:
      return "bg-neutral-1 border-neutral-5";
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
            <div className="flex items-center gap-2 text-primary-10 dark:text-primary-7">
              <Loader2
                className="w-4 h-4 animate-spin"
                data-testid="execution-spinner"
              />
              <span>Running</span>
            </div>
          );
        case "completed":
          return (
            <div className="flex items-center gap-2 text-success-10 dark:text-success-7">
              <CheckCircle className="w-4 h-4" />
              <span>Completed</span>
            </div>
          );
        case "error":
          return (
            <div className="flex items-center gap-2 text-error-10 dark:text-error-7">
              <XCircle className="w-4 h-4" />
              <span>Error</span>
            </div>
          );
        case "idle":
        default:
          return (
            <div className="flex items-center gap-2 text-neutral-10">
              <div className="w-3 h-3 rounded-full bg-neutral-3" />
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
              <span className="text-sm text-neutral-12 truncate">
                {log.message}
              </span>
              <span className="text-xs text-neutral-10 shrink-0">
                {formatRelativeTime(log.timestamp)}
              </span>
            </div>
            {log.nodeId && (
              <span className="text-xs text-neutral-10">
                Node: {log.nodeId}
              </span>
            )}
          </div>
          {hasDetails && (
            <Button variant="ghost" size="icon">
              {isExpanded ? (
                <ChevronDown className="w-4 h-4" />
              ) : (
                <ChevronRight className="w-4 h-4" />
              )}
            </Button>
          )}
        </div>
        {/* Expandable details */}
        {isExpanded && log.data && (
          <div className="mt-2 pt-2 border-t border-neutral-5">
            <pre className="text-xs bg-neutral-1 p-2 rounded overflow-auto max-h-40">
              {typeof log.data === "object" ? (
                <>
                  {log.data.output && <div>{log.data.output}</div>}
                  {log.data.tokens !== undefined && (
                    <div className="text-neutral-10">
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
      <div className="flex flex-col h-full bg-neutral-1 border-l border-neutral-5">
        {/* Header */}
        <div className="flex items-center justify-between p-3 border-b border-neutral-5">
          <h2 className="text-sm font-semibold text-neutral-12">
            Execution Trace
          </h2>
          <ExecutionStateIndicator state={executionState} />
        </div>
        {/* Toolbar */}
        <div className="flex items-center gap-2 p-2 border-b border-neutral-5">
          {/* Level filters */}
          <div className="flex items-center gap-1">
            <Button
              size="sm"
              className="px-2 py-1 text-xs rounded"
              onClick={() => setLevelFilter("all")}
            >
              All
            </Button>
            <Button
              size="sm"
              className="px-2 py-1 text-xs rounded"
              onClick={() => setLevelFilter("error")}
              aria-label="Errors"
            >
              Errors
            </Button>
          </div>

          {/* Node filter */}
          <Input
            size="sm"
            className="flex-1 px-2 py-1 text-xs bg-neutral-1 focus:ring-primary-7"
            placeholder="Filter by node..."
            value={nodeFilter}
            onChange={(e) => setNodeFilter(e.target.value)}
          />

          {/* Actions */}
          <Button
            className="p-1.5 rounded"
            onClick={() => setAutoScroll(!autoScroll)}
            aria-label="Auto-scroll"
            aria-pressed={autoScroll}
          >
            <ArrowDownToLine className="w-4 h-4" />
          </Button>

          <Button size="icon"
            variant="secondary"
            className="p-1.5 hover:bg-neutral-2 rounded text-neutral-10 hover:text-error-9"
            onClick={handleClearLogs}
            aria-label="Clear"
          >
            <Trash2 className="w-4 h-4" />
          </Button>
        </div>
        {/* Logs */}
        <div
          role="log"
          aria-live="polite"
          aria-label="Execution logs"
          className="flex-1 overflow-y-auto p-2 space-y-2"
        >
          {filteredLogs.length === 0 ? (
            <div className="flex flex-col items-center justify-center h-full text-neutral-10">
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
