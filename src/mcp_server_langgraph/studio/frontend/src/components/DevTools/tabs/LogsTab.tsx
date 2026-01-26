/**
 * LogsTab Component
 *
 * OTEL structured logs with trace correlation.
 * Uses OTELDataTable for virtualized, consistent table rendering.
 *
 * Uses shared OTEL components:
 * - OTELDataTable for virtualized table rendering
 * - OTELStatusBadge for log level badges
 * - OTELDetailsPanel for expanded attributes
 * - HumanTimestamp for relative time display
 *
 * Design System Compliance:
 * - Uses CVA for toolbar button variants
 * - Uses Motion.dev for button press feedback
 * - Implements useReducedMotion() for accessibility
 * - Uses semantic colors per STYLE.md
 */
import React, { useState, useMemo, useCallback, useRef } from "react";
import { motion, useReducedMotion, AnimatePresence } from "motion/react";
import { cva } from "class-variance-authority";
import { ArrowDown, Copy, Search } from "lucide-react";
import type { ColumnDef } from "@tanstack/react-table";
import { buttonVariants as motionButtonVariants, dropdownVariants } from "@/design-system/micro-interactions";
import { useTimelineContext } from "../context/DevToolsTimelineProvider";
import { cn } from "../../../utils/cn";
import { useAutoTail } from "../hooks/useAutoTail";
import { useListDevtoolsServicesQuery } from "../../../api";
import { STATUS_BG_COLORS, STATUS_TEXT_COLORS } from "../utils/devToolsColors";

// Shared OTEL components
import {
  HumanTimestamp,
  OTELStatusBadge,
  OTELDetailsPanel,
  OTELDataTable,
} from "../components";

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
// CVA Variants
// =============================================================================

/**
 * Filter dropdown button variants
 */
// eslint-disable-next-line react-refresh/only-export-components
export const filterButtonVariants = cva(
  "px-3 py-1.5 text-sm rounded-md flex items-center gap-1 transition-colors",
  {
    variants: {
      variant: {
        default: "bg-neutral-2 hover:bg-neutral-3 text-neutral-11",
        active: "bg-primary-3 dark:bg-primary-4 text-primary-11",
      },
    },
    defaultVariants: {
      variant: "default",
    },
  },
);

/**
 * Filter dropdown option variants
 */
// eslint-disable-next-line react-refresh/only-export-components
export const filterOptionVariants = cva(
  "w-full text-left px-3 py-2 text-sm transition-colors",
  {
    variants: {
      selected: {
        true: "bg-primary-1 dark:bg-primary-12",
        false: "hover:bg-neutral-2",
      },
    },
    defaultVariants: {
      selected: false,
    },
  },
);

/**
 * Auto-tail button variants
 */
// eslint-disable-next-line react-refresh/only-export-components
export const autoTailButtonVariants = cva(
  "px-2 py-1 text-sm rounded-md transition-colors",
  {
    variants: {
      active: {
        true: "bg-primary-3 dark:bg-primary-4 text-primary-11",
        false: "bg-neutral-2 hover:bg-neutral-3 text-neutral-11",
      },
    },
    defaultVariants: {
      active: false,
    },
  },
);

// =============================================================================
// Sub-Components
// =============================================================================

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
  const prefersReducedMotion = useReducedMotion();
  const [isOpen, setIsOpen] = useState(false);

  return (
    <div className="relative">
      <motion.button
        type="button"
        className={filterButtonVariants({ variant: value ? "active" : "default" })}
        onClick={() => setIsOpen(!isOpen)}
        aria-label={label}
        aria-expanded={isOpen}
        aria-haspopup="listbox"
        variants={prefersReducedMotion ? undefined : motionButtonVariants}
        initial="rest"
        whileHover="hover"
        whileTap="pressed"
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
      </motion.button>
      <AnimatePresence>
        {isOpen && (
          <>
            <div
              className="fixed inset-0 z-10"
              onClick={() => setIsOpen(false)}
            />
            <motion.div
              className="absolute top-full left-0 mt-1 bg-neutral-1 border border-neutral-5 rounded-md shadow-lg z-dropdown min-w-32"
              role="listbox"
              variants={prefersReducedMotion ? undefined : dropdownVariants}
              initial="hidden"
              animate="visible"
              exit="hidden"
            >
              <Button
                variant="ghost"
                type="button"
                role="option"
                aria-selected={!value}
                onClick={() => {
                  onChange("");
                  setIsOpen(false);
                }}
                className={filterOptionVariants({ selected: !value })}
                aria-label="All">
                All
              </Button>
              {options.map((option) => (
                <Button
                  variant="ghost"
                  key={option}
                  type="button"
                  role="option"
                  aria-selected={value === option}
                  onClick={() => {
                    onChange(option);
                    setIsOpen(false);
                  }}
                  className={filterOptionVariants({ selected: value === option })}
                  aria-label={option}>
                  {option}
                </Button>
              ))}
            </motion.div>
          </>
        )}
      </AnimatePresence>
    </div>
  );
}

/**
 * Auto-tail button with motion animation
 */
interface AutoTailButtonProps {
  isAutoTailing: boolean;
  toggleAutoTail: () => void;
}

function AutoTailButton({ isAutoTailing, toggleAutoTail }: AutoTailButtonProps): React.ReactElement {
  const prefersReducedMotion = useReducedMotion();

  return (
    <motion.button
      type="button"
      data-testid="logs-auto-tail"
      onClick={toggleAutoTail}
      aria-pressed={isAutoTailing}
      aria-label={
        isAutoTailing ? "Pause auto-tail to newest log" : "Resume auto-tail"
      }
      className={autoTailButtonVariants({ active: isAutoTailing })}
      variants={prefersReducedMotion ? undefined : motionButtonVariants}
      initial="rest"
      whileHover="hover"
      whileTap="pressed"
    >
      <ArrowDown size={14} />
    </motion.button>
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

  // Expanded row state
  const [expandedRowId, setExpandedRowId] = useState<string | null>(null);

  // Column definitions for OTELDataTable
  const columns = useMemo<ColumnDef<LogEntry>[]>(
    () => [
      {
        accessorKey: "timestamp",
        header: "Time",
        size: 100,
        cell: ({ row }) => (
          <HumanTimestamp timestamp={row.original.timestamp} />
        ),
      },
      {
        accessorKey: "level",
        header: "Level",
        size: 80,
        cell: ({ row }) => (
          <OTELStatusBadge type="log-level" value={row.original.level} />
        ),
      },
      {
        accessorKey: "service",
        header: "Service",
        size: 120,
        cell: ({ row }) => (
          <span className="text-xs text-neutral-10 truncate">
            {row.original.service}
          </span>
        ),
      },
      {
        accessorKey: "message",
        header: "Message",
        cell: ({ row }) => (
          <span className="text-sm text-neutral-12 truncate">
            {row.original.message}
          </span>
        ),
      },
    ],
    [],
  );

  // Auto-tail support
  const tableContainerRef = useRef<HTMLDivElement>(null);
  const { isAutoTailing, toggle: toggleAutoTail } = useAutoTail({
    containerRef: tableContainerRef,
    enabled: true,
  });

  // Get row className based on log level
  const getRowClassName = useCallback(
    (log: LogEntry) =>
      log.level === "error"
        ? STATUS_BG_COLORS.error
        : log.level === "warning"
          ? STATUS_BG_COLORS.warning
          : "",
    [],
  );

  // Render expanded row content
  const renderExpandedRow = useCallback(
    (log: LogEntry) => {
      const hasAttributes =
        log.attributes && Object.keys(log.attributes).length > 0;

      return (
        <div className="p-3 bg-neutral-2 space-y-2">
          {/* Trace link */}
          {log.traceId && onJumpToTrace && (
            <div className="flex items-center gap-2 text-xs">
              <span className="text-neutral-10">Trace:</span>
              <Button
                size="sm"
                variant="ghost"
                className="text-primary-10 dark:text-primary-7 hover:underline"
                onClick={() => onJumpToTrace(log.traceId!)}
              >
                {log.traceId}
              </Button>
            </div>
          )}
          {/* Attributes panel */}
          {hasAttributes && (
            <OTELDetailsPanel
              data={log.attributes!}
              variant="json"
            />
          )}
          {/* Copy button */}
          <Button
            size="sm"
            variant="secondary"
            className="flex items-center gap-1 text-xs"
            onClick={() =>
              navigator.clipboard.writeText(JSON.stringify(log, null, 2))
            }
          >
            <Copy size={12} />
            Copy JSON
          </Button>
        </div>
      );
    },
    [onJumpToTrace],
  );

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
            <div className="h-8 w-48 bg-neutral-3 rounded animate-pulse" />
            <div className="h-8 w-24 bg-neutral-3 rounded animate-pulse" />
            <div className="h-8 w-24 bg-neutral-3 rounded animate-pulse" />
          </div>
          {/* Log row skeletons */}
          {[1, 2, 3, 4, 5].map((i) => (
            <div
              key={i}
              className="h-10 bg-neutral-3 rounded animate-pulse"
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
      <div className="flex items-center gap-2 p-3 border-b border-neutral-5 sticky top-0 z-10 bg-neutral-1">
        {/* Search */}
        <div className="relative flex-1 max-w-sm">
          <Search
            className="absolute left-2 top-1/2 -translate-y-1/2 h-4 w-4 text-neutral-9"
            aria-hidden="true"
          />
          <Input
            className="h-8 pl-8 pr-2 py-1.5 text-sm"
            placeholder="Search logs..."
            value={searchTerm}
            onChange={(e) => setSearchTerm(e.target.value)}
            aria-label="Search logs"
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

        <AutoTailButton
          isAutoTailing={isAutoTailing}
          toggleAutoTail={toggleAutoTail}
        />

        {/* Clear filters */}
        {(searchTerm || levelFilter || serviceFilter) && (
          <Button
            variant="danger"
            size="sm"
            className="px-2 py-1 text-sm text-primary-10 dark:text-primary-7 hover:underline"
            onClick={() => {
              setSearchTerm("");
              setLevelFilter("");
              setServiceFilter("");
            }}>
            Clear
          </Button>
        )}
      </div>
      {/* Content - OTELDataTable with virtualization */}
      <div className="flex-1 overflow-hidden" ref={tableContainerRef}>
        {filteredLogs.length === 0 ? (
          <div className="flex flex-col items-center justify-center h-full text-center p-8">
            <svg
              className="w-12 h-12 text-neutral-9 mb-4"
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
            <p className="text-neutral-10">No logs</p>
            <p className="text-sm text-neutral-9 mt-1">
              {searchTerm || levelFilter || serviceFilter
                ? "No logs match the current filters"
                : "Logs will appear when data is collected"}
            </p>
          </div>
        ) : (
          <OTELDataTable
            data={filteredLogs}
            columns={columns}
            enableSorting
            defaultSort={{ id: "timestamp", desc: true }}
            expandedRowId={expandedRowId}
            onRowExpand={setExpandedRowId}
            renderExpandedRow={renderExpandedRow}
            getRowClassName={getRowClassName}
            virtualizeThreshold={100}
            enableAutoTail={isAutoTailing}
            getRowId={(log) => log.id}
            className="h-full"
          />
        )}
      </div>
    </div>
  );
}

export default LogsTab;
