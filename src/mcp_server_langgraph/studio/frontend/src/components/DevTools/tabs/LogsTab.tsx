/**
 * LogsTab Component
 *
 * OTEL structured logs with trace correlation.
 * Displays logs with filtering, search, and expandable attributes.
 */
import React, { useState, useMemo, useCallback, useRef } from "react";
import { ArrowDown, ArrowUpDown } from "lucide-react";
import {
  ColumnDef,
  getCoreRowModel,
  getSortedRowModel,
  SortingState,
  useReactTable,
} from "@tanstack/react-table";
import { useTimelineContext } from "../context/DevToolsTimelineProvider";
import { cn } from "../../../utils/cn";
import HumanTimestamp from "../components/HumanTimestamp";
import { useAutoTail } from "../hooks/useAutoTail";
import { useListDevtoolsServicesQuery } from "../../../api";
import {
  getLogLevelStyle,
  STATUS_BG_COLORS,
  STATUS_TEXT_COLORS,
} from "../utils/devToolsColors";

import { Button, Input } from "@/components/UI";

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

// =============================================================================
// Sub-Components
// =============================================================================

interface LevelBadgeProps {
  level: LogLevel;
}

function LevelBadge({ level }: LevelBadgeProps): React.ReactElement {
  // Use semantic colors from design system
  const config = getLogLevelStyle(level);

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
      <Button
        variant="secondary"
        className="px-3 py-1.5 text-sm bg-neutral-100 dark:bg-neutral-800 rounded-md hover:bg-neutral-200 dark:bg-neutral-700 dark:hover:bg-neutral-700 flex"
        onClick={() => setIsOpen(!isOpen)}
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
      </Button>
      {isOpen && (
        <>
          <div
            className="fixed inset-0 z-10"
            onClick={() => setIsOpen(false)}
          />
          <div className="absolute top-full left-0 mt-1 bg-white dark:bg-neutral-800 border border-neutral-200 dark:border-neutral-700 rounded-md shadow-lg z-20 min-w-[120px]">
            <Button
              role="option"
              onClick={() => {
                onChange("");
                setIsOpen(false);
              }}
              className={cn(
                "w-full text-left px-3 py-2 text-sm hover:bg-neutral-100 dark:bg-neutral-800 dark:hover:bg-neutral-700",
                !value && "bg-primary-50 dark:bg-primary-900",
              )}
              aria-label="All"
            >
              All
            </Button>
            {options.map((option) => (
              <Button
                key={option}
                role="option"
                onClick={() => {
                  onChange(option);
                  setIsOpen(false);
                }}
                className={cn(
                  "w-full text-left px-3 py-2 text-sm hover:bg-neutral-100 dark:bg-neutral-800 dark:hover:bg-neutral-700",
                  value === option && "bg-primary-50 dark:bg-primary-900",
                )}
                aria-label={option}
              >
                {option}
              </Button>
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

  // Use semantic background colors for error/warning rows
  const rowBgClass =
    log.level === "error"
      ? STATUS_BG_COLORS.error
      : log.level === "warning"
        ? STATUS_BG_COLORS.warning
        : "";

  return (
    <div
      data-log={log.id}
      className={cn(
        "border-b border-neutral-100 dark:border-neutral-800 py-2 px-3 hover:bg-neutral-50 dark:hover:bg-neutral-900",
        rowBgClass,
      )}
    >
      {/* Main row */}
      <div className="flex items-start gap-3">
        {/* Timestamp */}
        <HumanTimestamp timestamp={log.timestamp} className="shrink-0 pt-0.5" />

        {/* Level */}
        <div className="shrink-0">
          <LevelBadge level={log.level} />
        </div>

        {/* Service */}
        <span className="text-xs text-neutral-500 dark:text-neutral-400 shrink-0 pt-0.5">
          {log.service}
        </span>

        {/* Message */}
        <span className="flex-1 text-sm text-neutral-900 dark:text-white break-words">
          {log.message}
        </span>

        {/* Actions */}
        <div className="flex items-center gap-1 shrink-0">
          {hasAttributes && (
            <Button
              className="p-1 text-neutral-400 dark:text-neutral-400 hover:text-neutral-600 dark:text-neutral-300 dark:hover:text-neutral-300"
              onClick={() => setIsExpanded(!isExpanded)}
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
            </Button>
          )}
          <Button
            className="p-1 text-neutral-400 dark:text-neutral-400 hover:text-neutral-600 dark:text-neutral-300 dark:hover:text-neutral-300"
            onClick={handleCopy}
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
          </Button>
        </div>
      </div>
      {/* Trace correlation */}
      {(log.traceId || log.spanId) && (
        <div className="mt-1 ml-[72px] flex items-center gap-3 text-xs">
          {log.traceId && (
            <span className="font-mono text-neutral-500 dark:text-neutral-400">
              traceId: {log.traceId}
            </span>
          )}
          {log.spanId && (
            <span className="font-mono text-neutral-500 dark:text-neutral-400">
              spanId: {log.spanId}
            </span>
          )}
          {log.traceId && onJumpToTrace && (
            <Button
              className="text-primary-500 hover:text-primary-600 hover:underline"
              onClick={handleJumpToTrace}
              aria-label="Jump to Trace"
            >
              Jump to Trace
            </Button>
          )}
        </div>
      )}
      {/* Expanded attributes */}
      {isExpanded && hasAttributes && (
        <div className="mt-2 ml-[72px] p-2 bg-neutral-100 dark:bg-neutral-800 rounded font-mono text-xs overflow-x-auto">
          <pre className="text-neutral-700 dark:text-neutral-300 whitespace-pre-wrap">
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
  const { data: knownServices = [] } = useListDevtoolsServicesQuery();

  // Filter state
  const [searchTerm, setSearchTerm] = useState("");
  const [levelFilter, setLevelFilter] = useState("");
  const [serviceFilter, setServiceFilter] = useState("");
  const [sorting, setSorting] = useState<SortingState>([
    { id: "timestamp", desc: true },
  ]);
  const listRef = useRef<HTMLDivElement>(null);

  // Get unique services for filter dropdown
  const services = useMemo(() => {
    const uniqueServices = new Set([
      ...knownServices,
      ...logs.map((l) => l.service),
    ]);
    return Array.from(uniqueServices).sort();
  }, [logs, knownServices]);

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

  const columns = useMemo<ColumnDef<LogEntry>[]>(
    () => [
      { accessorKey: "timestamp", header: "Time" },
      { accessorKey: "level", header: "Level" },
      { accessorKey: "service", header: "Service" },
      { accessorKey: "message", header: "Message" },
    ],
    [],
  );

  const table = useReactTable({
    data: filteredLogs,
    columns,
    state: { sorting },
    onSortingChange: setSorting,
    getCoreRowModel: getCoreRowModel(),
    getSortedRowModel: getSortedRowModel(),
  });

  const sortedRows = table.getRowModel().rows;
  const sortedLogs = useMemo(
    () => sortedRows.map((row) => row.original),
    [sortedRows],
  );

  const { isAutoTailing, toggle: toggleAutoTail } = useAutoTail({
    containerRef: listRef,
    enabled: true,
  });

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
            <div className="h-8 w-48 bg-neutral-200 dark:bg-neutral-700 rounded animate-pulse" />
            <div className="h-8 w-24 bg-neutral-200 dark:bg-neutral-700 rounded animate-pulse" />
            <div className="h-8 w-24 bg-neutral-200 dark:bg-neutral-700 rounded animate-pulse" />
          </div>
          {/* Log row skeletons */}
          {[1, 2, 3, 4, 5].map((i) => (
            <div
              key={i}
              className="h-10 bg-neutral-200 dark:bg-neutral-700 rounded animate-pulse"
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
        <div className={cn(STATUS_TEXT_COLORS.error, "mb-4")}>
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
        <p className={STATUS_TEXT_COLORS.error}>{error}</p>
      </div>
    );
  }

  return (
    <div
      data-testid="logs-tab"
      className={cn("flex flex-col h-full overflow-hidden", className)}
    >
      {/* Header */}
      <div className="flex items-center gap-2 p-3 border-b border-neutral-200 dark:border-neutral-700 sticky top-0 z-10 bg-white dark:bg-neutral-900">
        {/* Search */}
        <div className="relative flex-1 max-w-sm">
          <svg
            className="absolute left-3 top-1/2 -translate-y-1/2 w-4 h-4 text-neutral-400 dark:text-neutral-400"
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
          <Input
            className="pl-10 pr-4 py-1.5 text-sm text-neutral-900 dark:text-white focus:ring-primary-500"
            placeholder="Search logs..."
            value={searchTerm}
            onChange={(e) => setSearchTerm(e.target.value)}
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

        <Button
          variant="secondary"
          size="sm"
          className="flex px-2 py-1 text-sm rounded-md bg-neutral-100 dark:bg-neutral-800 hover:bg-neutral-200 dark:bg-neutral-700 dark:hover:bg-neutral-700 text-neutral-700 dark:text-neutral-200"
          type="button"
          onClick={table.getColumn("timestamp")?.getToggleSortingHandler()}
          aria-label="Toggle time sort"
        >
          Sort
          <ArrowUpDown
            size={14}
            className={cn(
              "text-neutral-500 dark:text-neutral-400",
              table.getColumn("timestamp")?.getIsSorted() === "desc" &&
                "rotate-180",
            )}
          />
        </Button>

        <Button
          type="button"
          data-testid="logs-auto-tail"
          onClick={toggleAutoTail}
          aria-pressed={isAutoTailing}
          aria-label={
            isAutoTailing ? "Pause auto-tail to newest log" : "Resume auto-tail"
          }
          className={cn(
            "px-2 py-1 text-sm rounded-md",
            isAutoTailing
              ? "bg-primary-100 text-primary-700 dark:bg-primary-900/30"
              : "bg-neutral-100 dark:bg-neutral-800 hover:bg-neutral-200 dark:bg-neutral-700 dark:hover:bg-neutral-700 text-neutral-700 dark:text-neutral-200",
          )}
        >
          <ArrowDown size={14} />
        </Button>

        {/* Clear filters */}
        {(searchTerm || levelFilter || serviceFilter) && (
          <Button
            size="sm"
            className="px-2 py-1 text-sm text-primary-600 dark:text-primary-400 hover:underline"
            onClick={() => {
              setSearchTerm("");
              setLevelFilter("");
              setServiceFilter("");
            }}
          >
            Clear
          </Button>
        )}
      </div>
      {/* Content */}
      <div className="flex-1 overflow-auto" ref={listRef}>
        {sortedLogs.length === 0 ? (
          <div className="flex flex-col items-center justify-center h-full text-center p-8">
            <svg
              className="w-12 h-12 text-neutral-400 dark:text-neutral-400 mb-4"
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
            <p className="text-neutral-500 dark:text-neutral-400">No logs</p>
            <p className="text-sm text-neutral-400 dark:text-neutral-400 mt-1">
              {searchTerm || levelFilter || serviceFilter
                ? "No logs match the current filters"
                : "Logs will appear when data is collected"}
            </p>
          </div>
        ) : (
          <div className="divide-y divide-neutral-100 dark:divide-neutral-800">
            {sortedLogs.map((log) => (
              <LogRow key={log.id} log={log} onJumpToTrace={onJumpToTrace} />
            ))}
          </div>
        )}
      </div>
    </div>
  );
}

export default LogsTab;
