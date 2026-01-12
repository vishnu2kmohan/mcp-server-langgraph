/**
 * ConsoleTab Component
 *
 * Displays console logs, notifications, and execution logs.
 * Consolidates ActivityLog + execution logs + MCP logs.
 *
 * Features:
 * - Level-based filtering (all, info, warning, error)
 * - Expandable entries with structured data
 * - Copy to clipboard
 * - Clear console
 * - Auto-scroll to bottom
 * - Keyboard navigation
 * - Virtualized rendering for large lists (uses @tanstack/react-virtual)
 */
import { useState, useCallback, useRef, useMemo, useEffect } from "react";
import { useVirtualizer } from "@tanstack/react-virtual";
import {
  ColumnDef,
  getCoreRowModel,
  getSortedRowModel,
  SortingState,
  useReactTable,
} from "@tanstack/react-table";
import {
  Info,
  AlertTriangle,
  AlertCircle,
  Bug,
  ChevronRight,
  ChevronDown,
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
  ArrowUpDown,
  Search,
} from "lucide-react";

import { cn } from "../../../utils/cn";
import HumanTimestamp from "../components/HumanTimestamp";
import { useAutoTail } from "../hooks/useAutoTail";
import { parseLogMessage } from "../utils/jsonLogParser";
import { useConsoleEntries } from "../hooks/useConsoleEntries";
import { exportConsoleToJSON, exportConsoleToCSV } from "../utils/export";
import { useTimelineContext } from "../context/DevToolsTimelineProvider";
import { STATUS_TEXT_COLORS } from "../utils/devToolsColors";
import type {
  ConsoleTabProps,
  ConsoleEntry,
  ConsoleEntrySource,
} from "../types";

import { Button, Input, Select } from "@/components/UI";

// =============================================================================
// Virtualization Constants
// =============================================================================

/** Default estimated height for console entries (in pixels) */
const ESTIMATED_ROW_HEIGHT = 36;

/** Overscan count - number of items to render outside the visible area */
const OVERSCAN_COUNT = 10;

/** Threshold below which we skip virtualization for simplicity */
const VIRTUALIZATION_THRESHOLD = 100;

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
// Subcomponents
// =============================================================================

interface AugmentedConsoleEntry extends ConsoleEntry {
  friendlyMessage: string;
  structuredData: Record<string, unknown>;
  detailFields: Array<{ key: string; value: string }>;
  parsedPayload?: unknown;
}

interface ConsoleEntryRowProps {
  entry: AugmentedConsoleEntry;
  isExpanded: boolean;
  isFocused: boolean;
  onToggleExpand: () => void;
  onCopy: () => void;
  virtualIndex?: number;
  style?: React.CSSProperties;
  measureRef?: (node: HTMLDivElement | null) => void;
}

function ConsoleEntryRow({
  entry,
  isExpanded,
  isFocused,
  onToggleExpand,
  onCopy,
  virtualIndex,
  style,
  measureRef,
}: ConsoleEntryRowProps) {
  const [isHovered, setIsHovered] = useState(false);
  const hasData =
    Object.keys(entry.structuredData ?? {}).length > 0 || entry.stackTrace;
  const SourceIcon = SOURCE_ICONS[entry.source];

  const levelStyles = {
    info: STATUS_TEXT_COLORS.info,
    warning: STATUS_TEXT_COLORS.warning,
    error: STATUS_TEXT_COLORS.error,
    debug: STATUS_TEXT_COLORS.neutral,
  };

  const LevelIcon = {
    info: Info,
    warning: AlertTriangle,
    error: AlertCircle,
    debug: Bug,
  }[entry.level];

  return (
    <div
      ref={measureRef}
      // @tanstack/react-virtual requires `data-index` on the measured element.
      // Without it, row heights never get measured and expanded rows overlap.
      data-index={virtualIndex}
      data-testid={`console-entry-${entry.id}`}
      data-focused={isFocused}
      className={cn(
        "group flex flex-col border-b border-neutral-100 dark:border-neutral-800",
        "hover:bg-neutral-50 dark:hover:bg-neutral-800/50",
        levelStyles[entry.level],
        isFocused && "bg-primary-50 dark:bg-primary-900/20",
      )}
      style={style}
      onMouseEnter={() => setIsHovered(true)}
      onMouseLeave={() => setIsHovered(false)}
    >
      <div className="grid grid-cols-[auto_auto_130px_120px_1fr_auto] items-start gap-2 px-2 py-1">
        {/* Expand button */}
        {hasData ? (
          <Button
            variant="secondary"
            className="mt-0.5 p-0.5 hover:bg-neutral-200 dark:bg-neutral-700 dark:hover:bg-neutral-700 rounded"
            data-testid="expand-button"
            type="button"
            onClick={onToggleExpand}
            aria-expanded={isExpanded}
            aria-label={isExpanded ? "Collapse entry" : "Expand entry"}
          >
            {isExpanded ? (
              <ChevronDown size={14} />
            ) : (
              <ChevronRight size={14} />
            )}
          </Button>
        ) : (
          <div className="w-5" />
        )}

        {/* Level icon */}
        <LevelIcon
          size={14}
          className="mt-0.5 flex-shrink-0"
          aria-hidden="true"
        />

        {/* Timestamp */}
        <HumanTimestamp timestamp={entry.timestamp} />

        {/* Source indicator */}
        <span
          data-testid={`source-${entry.source}`}
          className="flex items-center gap-1 text-xs text-neutral-400 dark:text-neutral-400 flex-shrink-0"
        >
          <SourceIcon size={12} aria-hidden="true" />
          <span className="hidden sm:inline">
            {SOURCE_LABELS[entry.source]}
          </span>
        </span>

        {/* Message */}
        <div className="flex flex-col gap-1 min-w-0">
          <span className="flex-1 min-w-0 text-sm whitespace-pre-wrap break-words">
            {entry.friendlyMessage}
          </span>
          {entry.detailFields.length > 0 && (
            <div className="flex flex-wrap gap-1">
              {entry.detailFields.map((field) => (
                <span
                  key={`${entry.id}-${field.key}`}
                  className="inline-flex items-center gap-1 rounded bg-neutral-100 dark:bg-neutral-800 px-1.5 py-0.5 text-xs text-neutral-600 dark:text-neutral-300"
                >
                  <span className="font-semibold">{field.key}:</span>
                  <span className="truncate max-w-[180px]">{field.value}</span>
                </span>
              ))}
            </div>
          )}
        </div>

        {/* Copy button (visible on hover) */}
        {isHovered && (
          <Button
            variant="secondary"
            className="p-1 hover:bg-neutral-200 dark:bg-neutral-700 dark:hover:bg-neutral-700 rounded opacity-0 group-hover:opacity-100 -opacity"
            data-testid="copy-button"
            type="button"
            onClick={onCopy}
            aria-label="Copy message"
          >
            <Copy size={14} />
          </Button>
        )}
      </div>
      {/* Expanded data */}
      {isExpanded && hasData && (
        <div
          data-testid={`expanded-data-${entry.id}`}
          className="ml-12 mr-2 mb-2 p-2 bg-neutral-100 dark:bg-neutral-800 rounded text-xs font-mono overflow-x-auto"
        >
          {entry.structuredData && (
            <pre className="whitespace-pre-wrap text-neutral-600 dark:text-neutral-400">
              {JSON.stringify(entry.structuredData, null, 2)}
            </pre>
          )}
          {entry.stackTrace && (
            <pre
              data-testid={`stack-trace-${entry.id}`}
              className={cn(
                "mt-2 whitespace-pre-wrap border-t border-neutral-200 dark:border-neutral-700 pt-2",
                STATUS_TEXT_COLORS.error,
              )}
            >
              {entry.stackTrace}
            </pre>
          )}
        </div>
      )}
    </div>
  );
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

  /**
   * Merge and deduplicate local and external entries, sorted by timestamp.
   */
  const mergedEntries = useMemo(() => {
    // Create a map for deduplication by ID
    const entryMap = new Map<string, ConsoleEntry>();

    // Add local entries first
    for (const entry of localEntries) {
      entryMap.set(entry.id, entry);
    }

    // Add external entries (will overwrite duplicates)
    for (const entry of externalEntries) {
      if (!entryMap.has(entry.id)) {
        entryMap.set(entry.id, entry);
      }
    }

    // Convert to array and sort by timestamp
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

      // Prefer human-friendly text from parsed payload when available
      const friendlyMessage =
        (parsedPayload.message as string | undefined) ?? entry.message;

      // Build small set of detail chips for quick scanning
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
   * Filter merged entries by level.
   */
  const filteredEntries = useMemo(() => {
    if (filter === "all") {
      return augmentedEntries;
    }
    return augmentedEntries.filter((entry) => entry.level === filter);
  }, [augmentedEntries, filter]);

  // Timeline integration for time-travel debugging
  const timeline = useTimelineContext();

  const [expandedEntries, setExpandedEntries] = useState<Set<string>>(
    new Set(),
  );
  const [focusedIndex, setFocusedIndex] = useState<number>(-1);
  const [searchTerm, setSearchTerm] = useState("");
  const [sorting, setSorting] = useState<SortingState>([
    { id: "timestamp", desc: false },
  ]);
  const listRef = useRef<HTMLDivElement>(null);

  /**
   * Filter entries by timeline window for time-travel debugging.
   */
  const timelineFilteredEntries = useMemo(() => {
    // If no time window is set, return all entries
    if (!timeline.timeWindow) return filteredEntries;

    // Filter entries within the timeline window
    return filteredEntries.filter((entry) => {
      return (
        entry.timestamp >= timeline.timeWindow!.start &&
        entry.timestamp <= timeline.timeWindow!.end
      );
    });
  }, [filteredEntries, timeline.timeWindow]);

  /**
   * Filter by search term across message and structured data.
   */
  const searchedEntries = useMemo(() => {
    const term = searchTerm.trim().toLowerCase();
    if (!term) return timelineFilteredEntries;

    return timelineFilteredEntries.filter((entry) => {
      const haystacks = [
        entry.friendlyMessage.toLowerCase(),
        entry.source.toLowerCase(),
        entry.level.toLowerCase(),
        ...entry.detailFields.map((field) =>
          `${field.key} ${field.value}`.toLowerCase(),
        ),
      ];
      return haystacks.some((value) => value.includes(term));
    });
  }, [timelineFilteredEntries, searchTerm]);

  const displayEntries = useMemo(() => searchedEntries, [searchedEntries]);

  const columns = useMemo<ColumnDef<AugmentedConsoleEntry>[]>(
    () => [
      {
        id: "expand",
        header: "Expand",
        cell: () => null,
        size: 24,
      },
      {
        accessorKey: "level",
        header: "Level",
        size: 80,
      },
      {
        accessorKey: "timestamp",
        header: "Time",
        size: 140,
        sortingFn: "datetime",
      },
      {
        accessorKey: "source",
        header: "Source",
        size: 120,
      },
      {
        accessorKey: "friendlyMessage",
        header: "Message",
      },
    ],
    [],
  );

  const table = useReactTable({
    data: displayEntries,
    columns,
    state: { sorting },
    onSortingChange: setSorting,
    getCoreRowModel: getCoreRowModel(),
    getSortedRowModel: getSortedRowModel(),
    defaultColumn: { size: 100 },
  });

  const sortedRows = table.getRowModel().rows;

  const { isAutoTailing, toggle: toggleAutoTail } = useAutoTail({
    containerRef: listRef,
    enabled: true,
    onEntriesChange: () => {
      // virtualizer uses translateY; force measurement after scroll
      virtualizer.measure();
    },
  });

  /**
   * Only use virtualization for large lists.
   * For smaller lists, rendering all items is faster and simpler.
   */
  const shouldVirtualize = sortedRows.length >= VIRTUALIZATION_THRESHOLD;

  /**
   * Virtualizer for efficient rendering of large lists.
   * Only renders visible rows + overscan, dramatically improving performance
   * for logs with thousands of entries.
   */
  const virtualizer = useVirtualizer({
    count: sortedRows.length,
    getScrollElement: () => listRef.current,
    estimateSize: () => ESTIMATED_ROW_HEIGHT,
    overscan: OVERSCAN_COUNT,
    // Enable dynamic sizing for expanded entries
    measureElement: (element) =>
      element?.getBoundingClientRect().height ?? ESTIMATED_ROW_HEIGHT,
    // Only enable when virtualization is needed
    enabled: shouldVirtualize,
  });

  /**
   * Toggle entry expansion.
   */
  const toggleExpand = useCallback((entryId: string) => {
    setExpandedEntries((prev) => {
      const next = new Set(prev);
      if (next.has(entryId)) {
        next.delete(entryId);
      } else {
        next.add(entryId);
      }
      return next;
    });
  }, []);

  /**
   * Copy message to clipboard.
   */
  const copyMessage = useCallback(async (message: string) => {
    try {
      await navigator.clipboard.writeText(message);
    } catch {
      // Fallback for older browsers
      const textarea = document.createElement("textarea");
      textarea.value = message;
      document.body.appendChild(textarea);
      textarea.select();
      document.execCommand("copy");
      document.body.removeChild(textarea);
    }
  }, []);

  /**
   * Handle clearing both local and external entries.
   */
  const handleClearConsole = useCallback(() => {
    clearConsole();
    onClearExternal?.();
  }, [clearConsole, onClearExternal]);

  /**
   * Handle keyboard navigation.
   */
  const handleKeyDown = useCallback(
    (e: React.KeyboardEvent) => {
      if (e.key === "ArrowDown") {
        e.preventDefault();
        setFocusedIndex((prev) => Math.min(prev + 1, sortedRows.length - 1));
      } else if (e.key === "ArrowUp") {
        e.preventDefault();
        setFocusedIndex((prev) => Math.max(prev - 1, 0));
      } else if (e.key === "Enter" && focusedIndex >= 0) {
        const entry = sortedRows[focusedIndex]?.original;
        if (entry.data || entry.stackTrace) {
          toggleExpand(entry.id);
        }
      }
    },
    [sortedRows, focusedIndex, toggleExpand],
  );

  /**
   * Re-measure items when expansion state changes.
   */
  useEffect(() => {
    virtualizer.measure();
  }, [expandedEntries, virtualizer]);

  /**
   * Render helpers
   */
  const renderSortIndicator = (field: string) => {
    const column = table.getColumn(field);
    const isSorted = column?.getIsSorted();
    return (
      <ArrowUpDown
        size={12}
        className={cn(
          "ml-1 inline-block transition-transform",
          isSorted
            ? "text-primary-600"
            : "text-neutral-400 dark:text-neutral-400",
          isSorted === "desc" && "rotate-180",
        )}
        aria-hidden="true"
      />
    );
  };

  return (
    <div
      data-testid="console-tab"
      className="flex flex-col h-full min-h-0 bg-white dark:bg-neutral-900"
    >
      {/* Toolbar */}
      <div className="flex items-center gap-2 px-2 py-1 border-b border-neutral-200 dark:border-neutral-700 bg-neutral-50 dark:bg-neutral-800">
        {/* Filter dropdown */}
        <Select
          size="sm"
          className="text-xs px-2 py-1 text-neutral-700 dark:text-neutral-300"
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
          className="text-xs text-neutral-500 dark:text-neutral-400"
        >
          {sortedRows.length}
        </span>

        {/* Search */}
        <label className="relative text-xs text-neutral-500 dark:text-neutral-400 flex items-center gap-1">
          <Search
            size={12}
            className="absolute left-2 top-1/2 -translate-y-1/2 text-neutral-400 dark:text-neutral-400"
            aria-hidden="true"
          />
          <Input
            data-testid="console-search-input"
            value={searchTerm}
            onChange={(e) => setSearchTerm(e.target.value)}
            placeholder="Filter logs"
            className={cn(
              "pl-6 pr-2 py-1 text-xs",
              "bg-white dark:bg-neutral-900",
              "border border-neutral-200 dark:border-neutral-700 rounded",
              "focus:outline-none focus:ring-1 focus:ring-primary-500",
              "w-36",
            )}
            aria-label="Filter console logs"
          />
        </label>

        {/* Spacer */}
        <div className="flex-1" />

        {/* Export dropdown */}
        <div className="relative group">
          <Button
            variant="secondary"
            className="p-1 hover:bg-neutral-200 dark:bg-neutral-700 dark:hover:bg-neutral-700 rounded text-neutral-500 dark:text-neutral-400"
            data-testid="export-console-button"
            type="button"
            aria-label="Export console logs"
            aria-haspopup="true"
          >
            <Download size={14} />
          </Button>
          <div className="absolute right-0 top-full mt-1 bg-white dark:bg-neutral-800 border border-neutral-200 dark:border-neutral-700 rounded shadow-lg z-10 hidden group-hover:block">
            <Button
              variant="secondary"
              size="sm"
              className="block w-full text-left px-3 py-1.5 text-xs hover:bg-neutral-100 dark:bg-neutral-800 dark:hover:bg-neutral-700 whitespace-nowrap"
              data-testid="export-json-button"
              type="button"
              onClick={() => exportConsoleToJSON(displayEntries)}
            >
              Export as JSON
            </Button>
            <Button
              variant="secondary"
              size="sm"
              className="block w-full text-left px-3 py-1.5 text-xs hover:bg-neutral-100 dark:bg-neutral-800 dark:hover:bg-neutral-700 whitespace-nowrap"
              data-testid="export-csv-button"
              type="button"
              onClick={() => exportConsoleToCSV(displayEntries)}
            >
              Export as CSV
            </Button>
          </div>
        </div>

        {/* Auto-tail toggle */}
        <Button
          data-testid="scroll-to-bottom"
          type="button"
          onClick={toggleAutoTail}
          aria-pressed={isAutoTailing}
          aria-label={
            isAutoTailing ? "Pause auto-tail to newest log" : "Resume auto-tail"
          }
          className={cn(
            "p-1 rounded",
            isAutoTailing
              ? "bg-primary-100 text-primary-700 dark:bg-primary-900/30"
              : "hover:bg-neutral-200 dark:bg-neutral-700 dark:hover:bg-neutral-700",
          )}
        >
          <ArrowDown size={14} />
        </Button>

        {/* Clear console */}
        <Button
          variant="secondary"
          className="p-1 hover:bg-neutral-200 dark:bg-neutral-700 dark:hover:bg-neutral-700 rounded text-neutral-500 dark:text-neutral-400 hover:text-error-500"
          data-testid="clear-console-button"
          type="button"
          onClick={handleClearConsole}
          aria-label="Clear console"
        >
          <Trash2 size={14} />
        </Button>
      </div>
      {/* Entries list */}
      {sortedRows.length === 0 ? (
        <div
          data-testid="console-empty-state"
          className="flex-1 flex flex-col items-center justify-center text-neutral-400 dark:text-neutral-400"
        >
          <Terminal size={32} className="mb-2 opacity-50" />
          <p>No console output</p>
          <p className="text-xs mt-1">Logs will appear here</p>
        </div>
      ) : (
        <div
          ref={listRef}
          data-testid="console-entries-list"
          role="log"
          aria-label="Console entries"
          tabIndex={0}
          onKeyDown={handleKeyDown}
          onClick={() => setFocusedIndex(0)}
          className="flex-1 min-h-0 overflow-y-auto focus:outline-none"
        >
          {/* Header */}
          <div className="sticky top-0 z-10 bg-neutral-100 dark:bg-neutral-800/95 dark:bg-neutral-800/95 backdrop-blur border-b border-neutral-200 dark:border-neutral-700">
            <div className="grid grid-cols-[auto_auto_130px_120px_1fr_auto] items-center gap-2 px-2 py-2 text-xs font-semibold text-neutral-600 dark:text-neutral-300 uppercase tracking-wide">
              <span className="text-xs text-neutral-400 dark:text-neutral-400">
                Expand
              </span>
              <Button
                className="flex text-left"
                type="button"
                onClick={() => table.getColumn("level")?.toggleSorting()}
              >
                Level {renderSortIndicator("level")}
              </Button>
              <Button
                className="flex text-left"
                type="button"
                onClick={() => table.getColumn("timestamp")?.toggleSorting()}
              >
                Time {renderSortIndicator("timestamp")}
              </Button>
              <Button
                className="flex text-left"
                type="button"
                onClick={() => table.getColumn("source")?.toggleSorting()}
              >
                Source {renderSortIndicator("source")}
              </Button>
              <span>Message</span>
              <span className="text-right">Actions</span>
            </div>
          </div>
          {shouldVirtualize ? (
            /* Virtualized rendering for large lists */
            <div
              style={{
                height: `${virtualizer.getTotalSize()}px`,
                width: "100%",
                position: "relative",
              }}
            >
              {virtualizer.getVirtualItems().map((virtualRow) => {
                const entry = sortedRows[virtualRow.index]?.original;
                if (!entry) return null;
                return (
                  <ConsoleEntryRow
                    key={entry.id}
                    entry={entry}
                    isExpanded={expandedEntries.has(entry.id)}
                    isFocused={focusedIndex === virtualRow.index}
                    onToggleExpand={() => toggleExpand(entry.id)}
                    onCopy={() => copyMessage(entry.friendlyMessage)}
                    virtualIndex={virtualRow.index}
                    measureRef={virtualizer.measureElement}
                    style={{
                      position: "absolute",
                      top: 0,
                      left: 0,
                      width: "100%",
                      transform: `translateY(${virtualRow.start}px)`,
                    }}
                  />
                );
              })}
            </div>
          ) : (
            /* Standard rendering for small lists */
            sortedRows.map((row, index) => (
              <ConsoleEntryRow
                key={row.original.id}
                entry={row.original}
                isExpanded={expandedEntries.has(row.original.id)}
                isFocused={focusedIndex === index}
                onToggleExpand={() => toggleExpand(row.original.id)}
                onCopy={() => copyMessage(row.original.friendlyMessage)}
              />
            ))
          )}
        </div>
      )}
    </div>
  );
}

export default ConsoleTab;
