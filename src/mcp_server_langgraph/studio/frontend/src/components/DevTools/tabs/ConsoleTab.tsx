/**
 * ConsoleTab Component
 *
 * Displays console logs, notifications, and execution logs.
 * Consolidates ActivityLog + execution logs + MCP logs.
 *
 * Uses shared OTEL components:
 * - OTELDataTable for virtualized table rendering
 * - OTELStatusBadge for log level badges
 * - OTELDetailsPanel for expanded attributes
 * - HumanTimestamp for relative time display
 *
 * Features:
 * - Level-based filtering (all, info, warning, error)
 * - Expandable entries with structured data
 * - Copy to clipboard
 * - Clear console
 * - Auto-scroll to bottom
 * - Keyboard navigation
 *
 * Design System Compliance:
 * - Uses CVA for toolbar button variants
 * - Uses Motion.dev for button press feedback
 * - Implements useReducedMotion() for accessibility
 * - Uses semantic colors per STYLE.md
 */
import { useState, useCallback, useRef, useMemo } from "react";
import { motion, useReducedMotion } from "motion/react";
import { cva } from "class-variance-authority";
import type { ColumnDef } from "@tanstack/react-table";
import { buttonVariants as motionButtonVariants } from "@/design-system/micro-interactions";
import {
  Info,
  Copy,
  Trash2,
  ArrowDown,
  Terminal,
  Globe,
  Cpu,
  Bell,
  Zap,
  Server,
  Download,
  Search,
} from "lucide-react";

import { cn } from "../../../utils/cn";
import { useAutoTail } from "../hooks/useAutoTail";
import { parseLogMessage } from "../utils/jsonLogParser";
import { useConsoleEntries } from "../hooks/useConsoleEntries";
import { exportConsoleToJSON, exportConsoleToCSV } from "../utils/export";
import { useTimelineContext } from "../context/DevToolsTimelineProvider";
import { STATUS_BG_COLORS, STATUS_TEXT_COLORS } from "../utils/devToolsColors";
import type {
  ConsoleTabProps,
  ConsoleEntry,
  ConsoleEntrySource,
} from "../types";

// Shared OTEL components
import {
  HumanTimestamp,
  OTELStatusBadge,
  OTELDetailsPanel,
  OTELDataTable,
} from "../components";

import { Button, Input, Select } from "@/components/UI";

// =============================================================================
// Constants
// =============================================================================

const SOURCE_ICONS: Record<ConsoleEntrySource, typeof Info> = {
  system: Terminal,
  api: Globe,
  mcp: Cpu,
  notification: Bell,
  execution: Zap,
  websocket: Server,
};

const SOURCE_LABELS: Record<ConsoleEntrySource, string> = {
  system: "System",
  api: "API",
  mcp: "MCP",
  notification: "Notification",
  execution: "Execution",
  websocket: "WebSocket",
};

// =============================================================================
// CVA Variants
// =============================================================================

/**
 * Console toolbar button variants
 */
// eslint-disable-next-line react-refresh/only-export-components
export const consoleToolbarButtonVariants = cva(
  "p-1 rounded transition-colors",
  {
    variants: {
      variant: {
        default: "hover:bg-neutral-3 text-neutral-10",
        active: "bg-primary-3 dark:bg-primary-4 text-primary-11",
        danger: "hover:bg-neutral-3 text-neutral-10 hover:text-error-9",
      },
    },
    defaultVariants: {
      variant: "default",
    },
  },
);

// =============================================================================
// Types
// =============================================================================

interface AugmentedConsoleEntry extends ConsoleEntry {
  friendlyMessage: string;
  structuredData: Record<string, unknown>;
  detailFields: Array<{ key: string; value: string }>;
  parsedPayload?: unknown;
}

// =============================================================================
// Main Component
// =============================================================================

export function ConsoleTab({
  filter,
  onFilterChange,
  contextEntityId,
  externalEntries = [],
  onClearExternal,
}: ConsoleTabProps) {
  const {
    entries: localEntries,
    filteredEntries: _localFilteredEntries,
    clearConsole,
  } = useConsoleEntries({
    filter,
    contextEntityId,
  });

  // Timeline integration for time-travel debugging
  const timeline = useTimelineContext();

  // Filter and search state
  const [searchTerm, setSearchTerm] = useState("");
  const [expandedRowId, setExpandedRowId] = useState<string | null>(null);
  const tableContainerRef = useRef<HTMLDivElement>(null);

  // Auto-tail support
  const { isAutoTailing, toggle: toggleAutoTail } = useAutoTail({
    containerRef: tableContainerRef,
    enabled: true,
  });

  // Reduced motion preference
  const prefersReducedMotion = useReducedMotion();

  /**
   * Merge and deduplicate local and external entries, sorted by timestamp.
   */
  const mergedEntries = useMemo(() => {
    const entryMap = new Map<string, ConsoleEntry>();

    for (const entry of localEntries) {
      entryMap.set(entry.id, entry);
    }

    for (const entry of externalEntries) {
      if (!entryMap.has(entry.id)) {
        entryMap.set(entry.id, entry);
      }
    }

    return Array.from(entryMap.values()).sort(
      (a, b) => a.timestamp - b.timestamp,
    );
  }, [localEntries, externalEntries]);

  /**
   * Enrich entries with parsed JSON and structured data for rendering.
   */
  const augmentedEntries = useMemo<AugmentedConsoleEntry[]>(() => {
    return mergedEntries.map((entry) => {
      const parsedPayload = parseLogMessage(entry.message);
      const parsedFromMessage =
        parsedPayload.isJson && parsedPayload.extra
          ? parsedPayload.extra
          : null;
      const structuredData: Record<string, unknown> = {
        ...(entry.data ?? {}),
        ...(parsedFromMessage ?? {}),
      };

      const friendlyMessage =
        (parsedPayload.message as string | undefined) ?? entry.message;

      const detailFields = Object.entries(structuredData)
        .filter(([key]) => key !== "message" && key !== "msg")
        .map(([key, value]) => ({
          key,
          value:
            typeof value === "object"
              ? JSON.stringify(value)
              : String(value ?? ""),
        }))
        .filter((field) => field.value !== "");

      return {
        ...entry,
        friendlyMessage,
        structuredData,
        parsedPayload: parsedFromMessage ?? undefined,
        detailFields,
      };
    });
  }, [mergedEntries]);

  /**
   * Filter entries by level, timeline, and search term.
   */
  const filteredEntries = useMemo(() => {
    let result = augmentedEntries;

    // Filter by level
    if (filter !== "all") {
      result = result.filter((entry) => entry.level === filter);
    }

    // Filter by timeline window
    if (timeline?.timeWindow) {
      result = result.filter((entry) => {
        return (
          entry.timestamp >= timeline.timeWindow!.start &&
          entry.timestamp <= timeline.timeWindow!.end
        );
      });
    }

    // Filter by search term
    if (searchTerm) {
      const term = searchTerm.toLowerCase();
      result = result.filter((entry) => {
        return (
          entry.friendlyMessage.toLowerCase().includes(term) ||
          entry.source.toLowerCase().includes(term) ||
          entry.level.toLowerCase().includes(term) ||
          entry.detailFields.some((field) =>
            `${field.key} ${field.value}`.toLowerCase().includes(term),
          )
        );
      });
    }

    return result;
  }, [augmentedEntries, filter, timeline?.timeWindow, searchTerm]);

  // Column definitions for OTELDataTable
  const columns = useMemo<ColumnDef<AugmentedConsoleEntry>[]>(
    () => [
      {
        accessorKey: "level",
        header: "Level",
        size: 80,
        cell: ({ row }) => (
          <OTELStatusBadge type="log-level" value={row.original.level} />
        ),
      },
      {
        accessorKey: "timestamp",
        header: "Time",
        size: 120,
        cell: ({ row }) => (
          <HumanTimestamp timestamp={row.original.timestamp} />
        ),
      },
      {
        accessorKey: "source",
        header: "Source",
        size: 100,
        cell: ({ row }) => {
          const SourceIcon = SOURCE_ICONS[row.original.source];
          return (
            <span className="flex items-center gap-1 text-xs text-neutral-10">
              <SourceIcon size={12} aria-hidden="true" />
              <span className="hidden sm:inline">
                {SOURCE_LABELS[row.original.source]}
              </span>
            </span>
          );
        },
      },
      {
        accessorKey: "friendlyMessage",
        header: "Message",
        cell: ({ row }) => (
          <span className="text-sm text-neutral-12 truncate">
            {row.original.friendlyMessage}
          </span>
        ),
      },
    ],
    [],
  );

  // Get row className based on entry level
  const getRowClassName = useCallback(
    (entry: AugmentedConsoleEntry) =>
      entry.level === "error"
        ? STATUS_BG_COLORS.error
        : entry.level === "warning"
          ? STATUS_BG_COLORS.warning
          : "",
    [],
  );

  // Render expanded row content
  const renderExpandedRow = useCallback((entry: AugmentedConsoleEntry) => {
    const hasStructuredData =
      entry.structuredData && Object.keys(entry.structuredData).length > 0;

    return (
      <div className="p-3 bg-neutral-2 space-y-3">
        {/* Detail fields as chips */}
        {entry.detailFields.length > 0 && (
          <div className="flex flex-wrap gap-1">
            {entry.detailFields.map((field) => (
              <span
                key={`${entry.id}-${field.key}`}
                className="inline-flex items-center gap-1 rounded bg-neutral-3 px-1.5 py-0.5 text-xs text-neutral-11"
              >
                <span className="font-semibold">{field.key}:</span>
                <span className="truncate max-w-[180px]">{field.value}</span>
              </span>
            ))}
          </div>
        )}
        {/* Structured data */}
        {hasStructuredData && (
          <OTELDetailsPanel
            data={entry.structuredData}
            variant="json"
          />
        )}
        {/* Stack trace */}
        {entry.stackTrace && (
          <pre
            data-testid={`stack-trace-${entry.id}`}
            className={cn(
              "whitespace-pre-wrap font-mono text-xs border-t border-neutral-5 pt-2",
              STATUS_TEXT_COLORS.error,
            )}
          >
            {entry.stackTrace}
          </pre>
        )}
        {/* Copy button */}
        <Button
          size="sm"
          variant="secondary"
          className="flex items-center gap-1 text-xs"
          onClick={() =>
            navigator.clipboard.writeText(JSON.stringify(entry, null, 2))
          }
        >
          <Copy size={12} />
          Copy JSON
        </Button>
      </div>
    );
  }, []);

  /**
   * Handle clearing both local and external entries.
   */
  const handleClearConsole = useCallback(() => {
    clearConsole();
    onClearExternal?.();
  }, [clearConsole, onClearExternal]);

  return (
    <div
      data-testid="console-tab"
      className="flex flex-col h-full min-h-0 bg-neutral-1"
    >
      {/* Toolbar */}
      <div className="flex items-center gap-2 px-2 py-1 border-b border-neutral-5 bg-neutral-1">
        {/* Filter dropdown */}
        <Select
          size="sm"
          className="h-8 text-sm py-1.5 px-2 text-neutral-11"
          data-testid="console-filter-select"
          value={filter}
          onChange={(e) => onFilterChange(e.target.value as typeof filter)}
          aria-label="Filter console entries by level"
        >
          <option value="all">All levels</option>
          <option value="info">Info</option>
          <option value="warning">Warnings</option>
          <option value="error">Errors</option>
        </Select>

        {/* Entry count */}
        <span
          data-testid="entry-count"
          className="text-xs text-neutral-10"
        >
          {filteredEntries.length}
        </span>

        {/* Search */}
        <div className="relative">
          <Search
            className="absolute left-2 top-1/2 -translate-y-1/2 h-4 w-4 text-neutral-9"
            aria-hidden="true"
          />
          <Input
            data-testid="console-search-input"
            value={searchTerm}
            onChange={(e) => setSearchTerm(e.target.value)}
            placeholder="Filter logs"
            className={cn(
              "h-8 pl-8 pr-2 py-1.5 text-sm",
              "bg-neutral-1",
              "border border-neutral-5 rounded",
              "focus:outline-none focus:ring-1 focus:ring-primary-7",
              "w-40",
            )}
            aria-label="Filter console logs"
          />
        </div>

        {/* Spacer */}
        <div className="flex-1" />

        {/* Export dropdown */}
        <div className="relative group">
          <Button size="icon"
            variant="secondary"
            className="p-1 hover:bg-neutral-3 rounded text-neutral-10"
            data-testid="export-console-button"
            type="button"
            aria-label="Export console logs"
            aria-haspopup="true"
          >
            <Download size={14} />
          </Button>
          <div className="absolute right-0 top-full mt-1 bg-neutral-1 border border-neutral-5 rounded shadow-lg z-dropdown hidden group-hover:block">
            <Button
              variant="secondary"
              size="sm"
              className="block w-full text-left px-3 py-1.5 text-xs hover:bg-neutral-2 whitespace-nowrap"
              data-testid="export-json-button"
              type="button"
              onClick={() => exportConsoleToJSON(filteredEntries)}
            >
              Export as JSON
            </Button>
            <Button
              variant="secondary"
              size="sm"
              className="block w-full text-left px-3 py-1.5 text-xs hover:bg-neutral-2 whitespace-nowrap"
              data-testid="export-csv-button"
              type="button"
              onClick={() => exportConsoleToCSV(filteredEntries)}
            >
              Export as CSV
            </Button>
          </div>
        </div>

        {/* Auto-tail toggle */}
        <motion.button
          data-testid="scroll-to-bottom"
          type="button"
          onClick={toggleAutoTail}
          aria-pressed={isAutoTailing}
          aria-label={
            isAutoTailing ? "Pause auto-tail to newest log" : "Resume auto-tail"
          }
          className={consoleToolbarButtonVariants({
            variant: isAutoTailing ? "active" : "default",
          })}
          variants={prefersReducedMotion ? undefined : motionButtonVariants}
          initial="rest"
          whileHover="hover"
          whileTap="pressed"
        >
          <ArrowDown size={14} />
        </motion.button>

        {/* Clear console */}
        <motion.button
          className={consoleToolbarButtonVariants({ variant: "danger" })}
          data-testid="clear-console-button"
          type="button"
          onClick={handleClearConsole}
          aria-label="Clear console"
          variants={prefersReducedMotion ? undefined : motionButtonVariants}
          initial="rest"
          whileHover="hover"
          whileTap="pressed"
        >
          <Trash2 size={14} />
        </motion.button>
      </div>

      {/* Content - OTELDataTable with virtualization */}
      <div className="flex-1 overflow-hidden" ref={tableContainerRef}>
        {filteredEntries.length === 0 ? (
          <div
            data-testid="console-empty-state"
            className="flex flex-col items-center justify-center h-full text-center p-8"
          >
            <Terminal size={32} className="text-neutral-9 mb-4 opacity-50" />
            <p className="text-neutral-10">No console output</p>
            <p className="text-sm text-neutral-9 mt-1">
              {searchTerm || filter !== "all"
                ? "No entries match the current filters"
                : "Logs will appear here"}
            </p>
          </div>
        ) : (
          <OTELDataTable
            data={filteredEntries}
            columns={columns}
            enableSorting
            defaultSort={{ id: "timestamp", desc: false }}
            expandedRowId={expandedRowId}
            onRowExpand={setExpandedRowId}
            renderExpandedRow={renderExpandedRow}
            getRowClassName={getRowClassName}
            virtualizeThreshold={100}
            enableAutoTail={isAutoTailing}
            getRowId={(entry) => entry.id}
            className="h-full"
          />
        )}
      </div>
    </div>
  );
}

export default ConsoleTab;
