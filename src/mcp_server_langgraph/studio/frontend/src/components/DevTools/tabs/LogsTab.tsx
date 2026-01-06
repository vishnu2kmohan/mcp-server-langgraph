/**
 * LogsTab Component
 *
 * OTEL structured logs with trace correlation.
 * Displays logs with filtering, search, and expandable attributes.
 */
import React, { useState, useMemo, useCallback } from "react";
import { useTimelineContext } from "../context/DevToolsTimelineProvider";
import { cn } from "../../../utils/cn";

// =============================================================================
// Types
// =============================================================================

export type LogLevel = "debug" | "info" | "warning" | "error";

export interface LogEntry {
  id: string;
  timestamp: string;
  level: LogLevel;
  service: string;
  message: string;
  traceId?: string;
  spanId?: string;
  attributes?: Record<string, unknown>;
}

export interface LogsTabProps {
  logs?: LogEntry[];
  isLoading?: boolean;
  error?: string;
  onJumpToTrace?: (traceId: string) => void;
  className?: string;
}

// =============================================================================
// Utility Functions
// =============================================================================

function formatTimestamp(dateString: string): string {
  const date = new Date(dateString);
  return date.toLocaleTimeString("en-US", {
    hour12: false,
    hour: "2-digit",
    minute: "2-digit",
    second: "2-digit",
    fractionalSecondDigits: 3,
  });
}

// =============================================================================
// Sub-Components
// =============================================================================

interface LevelBadgeProps {
  level: LogLevel;
}

function LevelBadge({ level }: LevelBadgeProps): React.ReactElement {
  const config = {
    debug: "bg-gray-100 text-gray-700 dark:bg-gray-700 dark:text-gray-300",
    info: "bg-blue-100 text-blue-700 dark:bg-blue-900 dark:text-blue-300",
    warning:
      "bg-yellow-100 text-yellow-700 dark:bg-yellow-900 dark:text-yellow-300",
    error: "bg-red-100 text-red-700 dark:bg-red-900 dark:text-red-300",
  }[level];

  return (
    <span
      className={cn(
        "inline-flex items-center px-2 py-0.5 text-xs font-medium rounded uppercase",
        config,
      )}
    >
      {level}
    </span>
  );
}

interface FilterDropdownProps {
  label: string;
  options: string[];
  value: string;
  onChange: (value: string) => void;
}

function FilterDropdown({
  label,
  options,
  value,
  onChange,
}: FilterDropdownProps): React.ReactElement {
  const [isOpen, setIsOpen] = useState(false);

  return (
    <div className="relative">
      <button
        onClick={() => setIsOpen(!isOpen)}
        className="px-3 py-1.5 text-sm bg-gray-100 dark:bg-gray-800 rounded-md hover:bg-gray-200 dark:hover:bg-gray-700 flex items-center gap-1"
        aria-label={label}
      >
        {label}: {value || "All"}
        <svg
          className="w-4 h-4"
          fill="none"
          viewBox="0 0 24 24"
          stroke="currentColor"
        >
          <path
            strokeLinecap="round"
            strokeLinejoin="round"
            strokeWidth={2}
            d="M19 9l-7 7-7-7"
          />
        </svg>
      </button>
      {isOpen && (
        <>
          <div
            className="fixed inset-0 z-10"
            onClick={() => setIsOpen(false)}
          />
          <div className="absolute top-full left-0 mt-1 bg-white dark:bg-gray-800 border border-gray-200 dark:border-gray-700 rounded-md shadow-lg z-20 min-w-[120px]">
            <button
              role="option"
              onClick={() => {
                onChange("");
                setIsOpen(false);
              }}
              className={cn(
                "w-full text-left px-3 py-2 text-sm hover:bg-gray-100 dark:hover:bg-gray-700",
                !value && "bg-blue-50 dark:bg-blue-900",
              )}
              aria-label="All"
            >
              All
            </button>
            {options.map((option) => (
              <button
                key={option}
                role="option"
                onClick={() => {
                  onChange(option);
                  setIsOpen(false);
                }}
                className={cn(
                  "w-full text-left px-3 py-2 text-sm hover:bg-gray-100 dark:hover:bg-gray-700",
                  value === option && "bg-blue-50 dark:bg-blue-900",
                )}
                aria-label={option}
              >
                {option}
              </button>
            ))}
          </div>
        </>
      )}
    </div>
  );
}

interface LogRowProps {
  log: LogEntry;
  onJumpToTrace?: (traceId: string) => void;
}

function LogRow({ log, onJumpToTrace }: LogRowProps): React.ReactElement {
  const [isExpanded, setIsExpanded] = useState(false);

  const handleCopy = useCallback(() => {
    const text = JSON.stringify(log, null, 2);
    navigator.clipboard.writeText(text);
  }, [log]);

  const handleJumpToTrace = useCallback(() => {
    if (log.traceId) {
      onJumpToTrace?.(log.traceId);
    }
  }, [log.traceId, onJumpToTrace]);

  const hasAttributes =
    log.attributes && Object.keys(log.attributes).length > 0;

  return (
    <div
      data-log={log.id}
      className={cn(
        "border-b border-gray-100 dark:border-gray-800 py-2 px-3 hover:bg-gray-50 dark:hover:bg-gray-900",
        log.level === "error" && "bg-red-50/50 dark:bg-red-950/30",
        log.level === "warning" && "bg-yellow-50/50 dark:bg-yellow-950/30",
      )}
    >
      {/* Main row */}
      <div className="flex items-start gap-3">
        {/* Timestamp */}
        <span
          data-testid="log-timestamp"
          className="text-xs font-mono text-gray-400 dark:text-gray-500 shrink-0 pt-0.5"
        >
          {formatTimestamp(log.timestamp)}
        </span>

        {/* Level */}
        <div className="shrink-0">
          <LevelBadge level={log.level} />
        </div>

        {/* Service */}
        <span className="text-xs text-gray-500 dark:text-gray-400 shrink-0 pt-0.5">
          {log.service}
        </span>

        {/* Message */}
        <span className="flex-1 text-sm text-gray-900 dark:text-white break-words">
          {log.message}
        </span>

        {/* Actions */}
        <div className="flex items-center gap-1 shrink-0">
          {hasAttributes && (
            <button
              onClick={() => setIsExpanded(!isExpanded)}
              className="p-1 text-gray-400 hover:text-gray-600 dark:hover:text-gray-300"
              aria-label="Expand"
            >
              <svg
                className={cn(
                  "w-4 h-4 transition-transform",
                  isExpanded && "rotate-180",
                )}
                fill="none"
                viewBox="0 0 24 24"
                stroke="currentColor"
              >
                <path
                  strokeLinecap="round"
                  strokeLinejoin="round"
                  strokeWidth={2}
                  d="M19 9l-7 7-7-7"
                />
              </svg>
            </button>
          )}
          <button
            onClick={handleCopy}
            className="p-1 text-gray-400 hover:text-gray-600 dark:hover:text-gray-300"
            aria-label="Copy"
          >
            <svg
              className="w-4 h-4"
              fill="none"
              viewBox="0 0 24 24"
              stroke="currentColor"
            >
              <path
                strokeLinecap="round"
                strokeLinejoin="round"
                strokeWidth={2}
                d="M8 16H6a2 2 0 01-2-2V6a2 2 0 012-2h8a2 2 0 012 2v2m-6 12h8a2 2 0 002-2v-8a2 2 0 00-2-2h-8a2 2 0 00-2 2v8a2 2 0 002 2z"
              />
            </svg>
          </button>
        </div>
      </div>

      {/* Trace correlation */}
      {(log.traceId || log.spanId) && (
        <div className="mt-1 ml-[72px] flex items-center gap-3 text-xs">
          {log.traceId && (
            <span className="font-mono text-gray-500 dark:text-gray-400">
              traceId: {log.traceId}
            </span>
          )}
          {log.spanId && (
            <span className="font-mono text-gray-500 dark:text-gray-400">
              spanId: {log.spanId}
            </span>
          )}
          {log.traceId && onJumpToTrace && (
            <button
              onClick={handleJumpToTrace}
              className="text-blue-500 hover:text-blue-600 hover:underline"
              aria-label="Jump to Trace"
            >
              Jump to Trace
            </button>
          )}
        </div>
      )}

      {/* Expanded attributes */}
      {isExpanded && hasAttributes && (
        <div className="mt-2 ml-[72px] p-2 bg-gray-100 dark:bg-gray-800 rounded font-mono text-xs overflow-x-auto">
          <pre className="text-gray-700 dark:text-gray-300 whitespace-pre-wrap">
            {JSON.stringify(log.attributes, null, 2)}
          </pre>
        </div>
      )}
    </div>
  );
}

// =============================================================================
// Main Component
// =============================================================================

export function LogsTab({
  logs = [],
  isLoading = false,
  error,
  onJumpToTrace,
  className,
}: LogsTabProps): React.ReactElement {
  const timeline = useTimelineContext();

  // Filter state
  const [searchTerm, setSearchTerm] = useState("");
  const [levelFilter, setLevelFilter] = useState("");
  const [serviceFilter, setServiceFilter] = useState("");

  // Get unique services for filter dropdown
  const services = useMemo(() => {
    const uniqueServices = new Set(logs.map((l) => l.service));
    return Array.from(uniqueServices).sort();
  }, [logs]);

  // Filter logs
  const filteredLogs = useMemo(() => {
    let result = logs;

    // Filter by timeline time window
    if (timeline?.timeWindow) {
      result = result.filter((log) => {
        const logTime = new Date(log.timestamp).getTime();
        return (
          logTime >= timeline.timeWindow!.start &&
          logTime <= timeline.timeWindow!.end
        );
      });
    }

    // Filter by search term
    if (searchTerm) {
      const term = searchTerm.toLowerCase();
      result = result.filter(
        (l) =>
          l.message.toLowerCase().includes(term) ||
          l.service.toLowerCase().includes(term) ||
          l.traceId?.toLowerCase().includes(term) ||
          l.spanId?.toLowerCase().includes(term),
      );
    }

    // Filter by level
    if (levelFilter) {
      result = result.filter((l) => l.level === levelFilter);
    }

    // Filter by service
    if (serviceFilter) {
      result = result.filter((l) => l.service === serviceFilter);
    }

    return result;
  }, [logs, timeline?.timeWindow, searchTerm, levelFilter, serviceFilter]);

  // Loading state
  if (isLoading) {
    return (
      <div
        data-testid="logs-tab"
        className={cn("flex flex-col h-full", className)}
      >
        <div data-testid="logs-loading" className="p-4 space-y-2">
          {/* Header skeleton */}
          <div className="flex items-center gap-2">
            <div className="h-8 w-48 bg-gray-200 dark:bg-gray-700 rounded animate-pulse" />
            <div className="h-8 w-24 bg-gray-200 dark:bg-gray-700 rounded animate-pulse" />
            <div className="h-8 w-24 bg-gray-200 dark:bg-gray-700 rounded animate-pulse" />
          </div>
          {/* Log row skeletons */}
          {[1, 2, 3, 4, 5].map((i) => (
            <div
              key={i}
              className="h-10 bg-gray-200 dark:bg-gray-700 rounded animate-pulse"
            />
          ))}
        </div>
      </div>
    );
  }

  // Error state
  if (error) {
    return (
      <div
        data-testid="logs-tab"
        className={cn(
          "flex flex-col items-center justify-center h-full p-8 text-center",
          className,
        )}
      >
        <div className="text-red-500 mb-4">
          <svg
            className="w-12 h-12 mx-auto"
            fill="none"
            viewBox="0 0 24 24"
            stroke="currentColor"
          >
            <path
              strokeLinecap="round"
              strokeLinejoin="round"
              strokeWidth={2}
              d="M12 9v2m0 4h.01m-6.938 4h13.856c1.54 0 2.502-1.667 1.732-3L13.732 4c-.77-1.333-2.694-1.333-3.464 0L3.34 16c-.77 1.333.192 3 1.732 3z"
            />
          </svg>
        </div>
        <p className="text-red-600 dark:text-red-400">{error}</p>
      </div>
    );
  }

  return (
    <div
      data-testid="logs-tab"
      className={cn("flex flex-col h-full overflow-hidden", className)}
    >
      {/* Header */}
      <div className="flex items-center gap-2 p-3 border-b border-gray-200 dark:border-gray-700">
        {/* Search */}
        <div className="relative flex-1 max-w-sm">
          <svg
            className="absolute left-3 top-1/2 -translate-y-1/2 w-4 h-4 text-gray-400"
            fill="none"
            viewBox="0 0 24 24"
            stroke="currentColor"
          >
            <path
              strokeLinecap="round"
              strokeLinejoin="round"
              strokeWidth={2}
              d="M21 21l-6-6m2-5a7 7 0 11-14 0 7 7 0 0114 0z"
            />
          </svg>
          <input
            type="text"
            placeholder="Search logs..."
            value={searchTerm}
            onChange={(e) => setSearchTerm(e.target.value)}
            className="w-full pl-10 pr-4 py-1.5 text-sm border border-gray-200 dark:border-gray-700 rounded-md bg-white dark:bg-gray-800 text-gray-900 dark:text-white focus:outline-none focus:ring-2 focus:ring-blue-500"
          />
        </div>

        {/* Filters */}
        <FilterDropdown
          label="Level"
          options={["debug", "info", "warning", "error"]}
          value={levelFilter}
          onChange={setLevelFilter}
        />
        <FilterDropdown
          label="Service"
          options={services}
          value={serviceFilter}
          onChange={setServiceFilter}
        />

        {/* Clear filters */}
        {(searchTerm || levelFilter || serviceFilter) && (
          <button
            onClick={() => {
              setSearchTerm("");
              setLevelFilter("");
              setServiceFilter("");
            }}
            className="px-2 py-1 text-sm text-blue-600 dark:text-blue-400 hover:underline"
          >
            Clear
          </button>
        )}
      </div>

      {/* Content */}
      <div className="flex-1 overflow-auto">
        {filteredLogs.length === 0 ? (
          <div className="flex flex-col items-center justify-center h-full text-center p-8">
            <svg
              className="w-12 h-12 text-gray-400 mb-4"
              fill="none"
              viewBox="0 0 24 24"
              stroke="currentColor"
            >
              <path
                strokeLinecap="round"
                strokeLinejoin="round"
                strokeWidth={2}
                d="M9 12h6m-6 4h6m2 5H7a2 2 0 01-2-2V5a2 2 0 012-2h5.586a1 1 0 01.707.293l5.414 5.414a1 1 0 01.293.707V19a2 2 0 01-2 2z"
              />
            </svg>
            <p className="text-gray-500 dark:text-gray-400">No logs</p>
            <p className="text-sm text-gray-400 dark:text-gray-500 mt-1">
              {searchTerm || levelFilter || serviceFilter
                ? "No logs match the current filters"
                : "Logs will appear when data is collected"}
            </p>
          </div>
        ) : (
          <div className="divide-y divide-gray-100 dark:divide-gray-800">
            {filteredLogs.map((log) => (
              <LogRow key={log.id} log={log} onJumpToTrace={onJumpToTrace} />
            ))}
          </div>
        )}
      </div>
    </div>
  );
}

export default LogsTab;
