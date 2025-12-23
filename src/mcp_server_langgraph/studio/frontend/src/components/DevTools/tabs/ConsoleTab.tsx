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
 */
import { useState, useCallback, useRef, useMemo } from "react";
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
import {
  useBatchedUpdates,
  useStableCallback,
} from "../utils/performance";
import type {
  ConsoleTabProps,
  ConsoleEntry,
  ConsoleEntrySource,
} from "../types";

// =============================================================================
// Performance Constants
// =============================================================================

/** Initial batch size for rendering entries (improves initial render time) */
const INITIAL_BATCH_SIZE = 100;

/** Enable batched rendering for lists larger than this threshold */
const BATCHING_THRESHOLD = 50;

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
}

function ConsoleEntryRow({
  entry,
  isExpanded,
  isFocused,
  onToggleExpand,
  onCopy,
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
      data-testid={`console-entry-${entry.id}`}
      data-focused={isFocused}
      className={cn(
        "group flex flex-col border-b border-gray-100 dark:border-gray-800",
        "hover:bg-gray-50 dark:hover:bg-gray-800/50",
        levelStyles[entry.level],
        isFocused && "bg-primary-50 dark:bg-primary-900/20",
      )}
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
}: ConsoleTabProps) {
  const { entries, filteredEntries, clearConsole } = useConsoleEntries({
    filter,
    contextEntityId,
  });

  const [expandedEntries, setExpandedEntries] = useState<Set<string>>(
    new Set(),
  );
  const [focusedIndex, setFocusedIndex] = useState<number>(-1);
  const listRef = useRef<HTMLDivElement>(null);

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
    if (listRef.current) {
      listRef.current.scrollTop = listRef.current.scrollHeight;
    }
  }, []);

  /**
   * Handle keyboard navigation.
   */
  const handleKeyDown = useCallback(
    (e: React.KeyboardEvent) => {
      if (e.key === "ArrowDown") {
        e.preventDefault();
        setFocusedIndex((prev) =>
          Math.min(prev + 1, filteredEntries.length - 1),
        );
      } else if (e.key === "ArrowUp") {
        e.preventDefault();
        setFocusedIndex((prev) => Math.max(prev - 1, 0));
      } else if (e.key === "Enter" && focusedIndex >= 0) {
        const entry = filteredEntries[focusedIndex];
        if (entry.data || entry.stackTrace) {
          toggleExpand(entry.id);
        }
      }
    },
    [filteredEntries, focusedIndex, toggleExpand],
  );

  /**
   * Get display entries.
   */
  const allEntries = useMemo(() => {
    // Use filtered entries if filter is applied, otherwise use all entries
    return filteredEntries.length > 0 ? filteredEntries : entries;
  }, [filteredEntries, entries]);

  /**
   * Use batched updates for large lists to improve initial render performance.
   * Only applies batching when list exceeds threshold.
   */
  const shouldBatch = allEntries.length > BATCHING_THRESHOLD;
  const { displayedItems: batchedEntries, hasMore, loadMore } = useBatchedUpdates(
    allEntries,
    INITIAL_BATCH_SIZE,
  );

  // Use batched entries for large lists, otherwise use all entries
  const displayEntries = shouldBatch ? batchedEntries : allEntries;

  /**
   * Load more entries when scrolling near bottom.
   */
  const stableLoadMore = useStableCallback(loadMore);
  const handleScroll = useCallback((e: React.UIEvent<HTMLDivElement>) => {
    const target = e.currentTarget;
    const nearBottom = target.scrollHeight - target.scrollTop - target.clientHeight < 100;
    if (nearBottom && hasMore) {
      stableLoadMore();
    }
  }, [hasMore, stableLoadMore]);

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
          onClick={clearConsole}
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
          {displayEntries.map((entry, index) => (
            <ConsoleEntryRow
              key={entry.id}
              entry={entry}
              isExpanded={expandedEntries.has(entry.id)}
              isFocused={focusedIndex === index}
              onToggleExpand={() => toggleExpand(entry.id)}
              onCopy={() => copyMessage(entry.message)}
            />
          ))}
        </div>
      )}
    </div>
  );
}

export default ConsoleTab;
