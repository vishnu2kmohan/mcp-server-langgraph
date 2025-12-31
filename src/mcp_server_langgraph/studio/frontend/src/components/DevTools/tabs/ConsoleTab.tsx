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
} from "lucide-react";

import { cn } from "../../../utils/cn";
import { useConsoleEntries } from "../hooks/useConsoleEntries";
import { exportConsoleToJSON, exportConsoleToCSV } from "../utils/export";
import { useTimelineContext } from "../context/DevToolsTimelineProvider";
import type {
  ConsoleTabProps,
  ConsoleEntry,
  ConsoleEntrySource,
} from "../types";

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

interface ConsoleEntryRowProps {
  entry: ConsoleEntry;
  isExpanded: boolean;
  isFocused: boolean;
  onToggleExpand: () => void;
  onCopy: () => void;
  style?: React.CSSProperties;
  measureRef?: (node: HTMLDivElement | null) => void;
}

function ConsoleEntryRow({
  entry,
  isExpanded,
  isFocused,
  onToggleExpand,
  onCopy,
  style,
  measureRef,
}: ConsoleEntryRowProps) {
  const [isHovered, setIsHovered] = useState(false);
  const hasData = entry.data || entry.stackTrace;
  const SourceIcon = SOURCE_ICONS[entry.source];

  const levelStyles = {
    info: "text-blue-600 dark:text-blue-400",
    warning: "text-amber-600 dark:text-amber-400",
    error: "text-red-600 dark:text-red-400",
    debug: "text-gray-500 dark:text-gray-500",
  };

  const LevelIcon = {
    info: Info,
    warning: AlertTriangle,
    error: AlertCircle,
    debug: Bug,
  }[entry.level];

  const formatTimestamp = (ts: number) => {
    const date = new Date(ts);
    return date.toLocaleTimeString("en-US", {
      hour12: false,
      hour: "2-digit",
      minute: "2-digit",
      second: "2-digit",
      fractionalSecondDigits: 3,
    });
  };

  return (
    <div
      ref={measureRef}
      data-testid={`console-entry-${entry.id}`}
      data-focused={isFocused}
      className={cn(
        "group flex flex-col border-b border-gray-100 dark:border-gray-800",
        "hover:bg-gray-50 dark:hover:bg-gray-800/50",
        levelStyles[entry.level],
        isFocused && "bg-primary-50 dark:bg-primary-900/20",
      )}
      style={style}
      onMouseEnter={() => setIsHovered(true)}
      onMouseLeave={() => setIsHovered(false)}
    >
      <div className="flex items-start gap-2 px-2 py-1">
        {/* Expand button */}
        {hasData ? (
          <button
            data-testid="expand-button"
            type="button"
            onClick={onToggleExpand}
            aria-expanded={isExpanded}
            aria-label={isExpanded ? "Collapse entry" : "Expand entry"}
            className="mt-0.5 p-0.5 hover:bg-gray-200 dark:hover:bg-gray-700 rounded"
          >
            {isExpanded ? (
              <ChevronDown size={14} />
            ) : (
              <ChevronRight size={14} />
            )}
          </button>
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
        <span className="text-xs text-gray-400 dark:text-gray-500 font-mono flex-shrink-0">
          {formatTimestamp(entry.timestamp)}
        </span>

        {/* Source indicator */}
        <span
          data-testid={`source-${entry.source}`}
          className="flex items-center gap-1 text-xs text-gray-400 dark:text-gray-500 flex-shrink-0"
        >
          <SourceIcon size={12} aria-hidden="true" />
          <span className="hidden sm:inline">
            {SOURCE_LABELS[entry.source]}
          </span>
        </span>

        {/* Message */}
        <span className="flex-1 text-sm break-all">{entry.message}</span>

        {/* Copy button (visible on hover) */}
        {isHovered && (
          <button
            data-testid="copy-button"
            type="button"
            onClick={onCopy}
            aria-label="Copy message"
            className="p-1 hover:bg-gray-200 dark:hover:bg-gray-700 rounded opacity-0 group-hover:opacity-100 transition-opacity"
          >
            <Copy size={14} />
          </button>
        )}
      </div>

      {/* Expanded data */}
      {isExpanded && hasData && (
        <div
          data-testid={`expanded-data-${entry.id}`}
          className="ml-12 mr-2 mb-2 p-2 bg-gray-100 dark:bg-gray-900 rounded text-xs font-mono overflow-x-auto"
        >
          {entry.data && (
            <pre className="whitespace-pre-wrap text-gray-600 dark:text-gray-400">
              {JSON.stringify(entry.data, null, 2)}
            </pre>
          )}
          {entry.stackTrace && (
            <pre
              data-testid={`stack-trace-${entry.id}`}
              className="mt-2 whitespace-pre-wrap text-red-600 dark:text-red-400 border-t border-gray-200 dark:border-gray-700 pt-2"
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
   * Filter merged entries by level.
   */
  const filteredEntries = useMemo(() => {
    if (filter === "all") {
      return mergedEntries;
    }
    return mergedEntries.filter((entry) => entry.level === filter);
  }, [mergedEntries, filter]);

  // Use merged entries for display
  const entries = mergedEntries;

  // Timeline integration for time-travel debugging
  const timeline = useTimelineContext();

  const [expandedEntries, setExpandedEntries] = useState<Set<string>>(
    new Set(),
  );
  const [focusedIndex, setFocusedIndex] = useState<number>(-1);
  const listRef = useRef<HTMLDivElement>(null);

  /**
   * Filter entries by timeline window for time-travel debugging.
   */
  const timelineFilteredEntries = useMemo(() => {
    const baseEntries = filteredEntries.length > 0 ? filteredEntries : entries;

    // If no time window is set, return all entries
    if (!timeline.timeWindow) return baseEntries;

    // Filter entries within the timeline window
    return baseEntries.filter((entry) => {
      return (
        entry.timestamp >= timeline.timeWindow!.start &&
        entry.timestamp <= timeline.timeWindow!.end
      );
    });
  }, [filteredEntries, entries, timeline.timeWindow]);

  /**
   * Get display entries (with timeline filtering applied).
   */
  const displayEntries = useMemo(() => {
    return timelineFilteredEntries;
  }, [timelineFilteredEntries]);

  /**
   * Only use virtualization for large lists.
   * For smaller lists, rendering all items is faster and simpler.
   */
  const shouldVirtualize = displayEntries.length >= VIRTUALIZATION_THRESHOLD;

  /**
   * Virtualizer for efficient rendering of large lists.
   * Only renders visible rows + overscan, dramatically improving performance
   * for logs with thousands of entries.
   */
  const virtualizer = useVirtualizer({
    count: displayEntries.length,
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
   * Scroll to bottom of log.
   */
  const scrollToBottom = useCallback(() => {
    if (displayEntries.length > 0) {
      if (shouldVirtualize) {
        virtualizer.scrollToIndex(displayEntries.length - 1, { align: "end" });
      } else if (listRef.current) {
        listRef.current.scrollTop = listRef.current.scrollHeight;
      }
    }
  }, [displayEntries.length, shouldVirtualize, virtualizer]);

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
        setFocusedIndex((prev) =>
          Math.min(prev + 1, displayEntries.length - 1),
        );
      } else if (e.key === "ArrowUp") {
        e.preventDefault();
        setFocusedIndex((prev) => Math.max(prev - 1, 0));
      } else if (e.key === "Enter" && focusedIndex >= 0) {
        const entry = displayEntries[focusedIndex];
        if (entry.data || entry.stackTrace) {
          toggleExpand(entry.id);
        }
      }
    },
    [displayEntries, focusedIndex, toggleExpand],
  );

  /**
   * Re-measure items when expansion state changes.
   */
  useEffect(() => {
    virtualizer.measure();
  }, [expandedEntries, virtualizer]);

  return (
    <div
      data-testid="console-tab"
      className="flex flex-col h-full bg-white dark:bg-gray-900"
    >
      {/* Toolbar */}
      <div className="flex items-center gap-2 px-2 py-1 border-b border-gray-200 dark:border-gray-700 bg-gray-50 dark:bg-gray-800">
        {/* Filter dropdown */}
        <select
          data-testid="console-filter-select"
          value={filter}
          onChange={(e) => onFilterChange(e.target.value as typeof filter)}
          aria-label="Filter console entries by level"
          className="text-xs px-2 py-1 rounded border border-gray-300 dark:border-gray-600 bg-white dark:bg-gray-700 text-gray-700 dark:text-gray-300"
        >
          <option value="all">All levels</option>
          <option value="info">Info</option>
          <option value="warning">Warnings</option>
          <option value="error">Errors</option>
        </select>

        {/* Entry count */}
        <span
          data-testid="entry-count"
          className="text-xs text-gray-500 dark:text-gray-400"
        >
          {displayEntries.length}
        </span>

        {/* Spacer */}
        <div className="flex-1" />

        {/* Export dropdown */}
        <div className="relative group">
          <button
            data-testid="export-console-button"
            type="button"
            aria-label="Export console logs"
            aria-haspopup="true"
            className="p-1 hover:bg-gray-200 dark:hover:bg-gray-700 rounded text-gray-500"
          >
            <Download size={14} />
          </button>
          <div className="absolute right-0 top-full mt-1 bg-white dark:bg-gray-800 border border-gray-200 dark:border-gray-700 rounded shadow-lg z-10 hidden group-hover:block">
            <button
              data-testid="export-json-button"
              type="button"
              onClick={() => exportConsoleToJSON(displayEntries)}
              className="block w-full text-left px-3 py-1.5 text-xs hover:bg-gray-100 dark:hover:bg-gray-700 whitespace-nowrap"
            >
              Export as JSON
            </button>
            <button
              data-testid="export-csv-button"
              type="button"
              onClick={() => exportConsoleToCSV(displayEntries)}
              className="block w-full text-left px-3 py-1.5 text-xs hover:bg-gray-100 dark:hover:bg-gray-700 whitespace-nowrap"
            >
              Export as CSV
            </button>
          </div>
        </div>

        {/* Scroll to bottom */}
        <button
          data-testid="scroll-to-bottom"
          type="button"
          onClick={scrollToBottom}
          aria-label="Scroll to bottom"
          className="p-1 hover:bg-gray-200 dark:hover:bg-gray-700 rounded"
        >
          <ArrowDown size={14} />
        </button>

        {/* Clear console */}
        <button
          data-testid="clear-console-button"
          type="button"
          onClick={handleClearConsole}
          aria-label="Clear console"
          className="p-1 hover:bg-gray-200 dark:hover:bg-gray-700 rounded text-gray-500 hover:text-red-500"
        >
          <Trash2 size={14} />
        </button>
      </div>

      {/* Entries list */}
      {displayEntries.length === 0 ? (
        <div
          data-testid="console-empty-state"
          className="flex-1 flex flex-col items-center justify-center text-gray-400 dark:text-gray-500"
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
          className="flex-1 overflow-y-auto focus:outline-none"
        >
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
                const entry = displayEntries[virtualRow.index];
                return (
                  <ConsoleEntryRow
                    key={entry.id}
                    entry={entry}
                    isExpanded={expandedEntries.has(entry.id)}
                    isFocused={focusedIndex === virtualRow.index}
                    onToggleExpand={() => toggleExpand(entry.id)}
                    onCopy={() => copyMessage(entry.message)}
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
            displayEntries.map((entry, index) => (
              <ConsoleEntryRow
                key={entry.id}
                entry={entry}
                isExpanded={expandedEntries.has(entry.id)}
                isFocused={focusedIndex === index}
                onToggleExpand={() => toggleExpand(entry.id)}
                onCopy={() => copyMessage(entry.message)}
              />
            ))
          )}
        </div>
      )}
    </div>
  );
}

export default ConsoleTab;
