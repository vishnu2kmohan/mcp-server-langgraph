/**
 * NetworkTab Component
 *
 * Displays API requests, WebSocket messages, and MCP tool calls.
 * Chrome DevTools Network panel-like interface.
 */
import { useState, useMemo, useCallback, useRef } from "react";
import {
  ColumnDef,
  flexRender,
  getCoreRowModel,
  getSortedRowModel,
  SortingState,
  useReactTable,
} from "@tanstack/react-table";
import {
  Trash2,
  Search,
  Circle,
  ChevronRight as _ChevronRight,
  ChevronDown as _ChevronDown,
  Globe,
  Loader2,
  Download,
  ArrowDown,
  ArrowUpDown,
} from "lucide-react";

import { cn } from "../../../utils/cn";
import HumanTimestamp from "../components/HumanTimestamp";
import { useAutoTail } from "../hooks/useAutoTail";
import { useNetworkEntries } from "../hooks/useNetworkEntries";
import { exportNetworkToJSON, exportNetworkToCSV } from "../utils/export";
import { useDebouncedValue, useStableCallback } from "../utils/performance";
import { useTimelineContext } from "../context/DevToolsTimelineProvider";
import type { NetworkTabProps, NetworkEntry } from "../types";
import {
  getStatusCodeColor,
  getHttpMethodColor,
} from "../utils/devToolsColors";

import { Button, Input } from "@/components/UI";

// =============================================================================
// Performance Constants
// =============================================================================

/** Debounce delay for search input (ms) */
const SEARCH_DEBOUNCE_MS = 150;

// =============================================================================
// Types
// =============================================================================

type FilterType = "all" | "api" | "mcp";
// =============================================================================
// Utility Functions
// =============================================================================

function formatSize(bytes: number | undefined): string {
  if (bytes === undefined || bytes === 0) return "0 B";
  if (bytes < 1024) return `${bytes} B`;
  if (bytes < 1024 * 1024) return `${Math.round(bytes / 1024)} KB`;
  return `${(bytes / (1024 * 1024)).toFixed(1)} MB`;
}

// Use semantic colors from design system (imported from devToolsColors)
const getStatusColor = getStatusCodeColor;
const getMethodColor = getHttpMethodColor;

// =============================================================================
// Subcomponents
// =============================================================================

interface NetworkEntryRowProps {
  entry: NetworkEntry;
  isSelected: boolean;
  onSelect: () => void;
}

function NetworkEntryRow({
  entry,
  isSelected,
  onSelect,
}: NetworkEntryRowProps) {
  const isPending = entry.status === "pending";
  const isError =
    entry.status === "error" ||
    (entry.statusCode !== undefined && entry.statusCode >= 400);

  // Extract path from URL
  const urlPath = entry.url.startsWith("http")
    ? new URL(entry.url).pathname + new URL(entry.url).search
    : entry.url;

  return (
    <tr
      data-testid={`network-entry-${entry.id}`}
      className={cn(
        "cursor-pointer border-b border-neutral-100 dark:border-neutral-800",
        "hover:bg-neutral-50 dark:hover:bg-neutral-800/50",
        isSelected && "bg-primary-50 dark:bg-primary-900/20",
        isError === true && "bg-error-50 dark:bg-error-900/10",
      )}
      onClick={onSelect}
    >
      {/* Method */}
      <td className="px-2 py-1.5 whitespace-nowrap">
        <span
          data-testid={`method-${entry.id}`}
          className={cn("text-xs font-medium", getMethodColor(entry.method))}
        >
          {entry.method}
        </span>
      </td>

      {/* Status */}
      <td className="px-2 py-1.5 whitespace-nowrap">
        {isPending ? (
          <span data-testid={`pending-${entry.id}`}>
            <Loader2 size={12} className="animate-spin text-primary-500" />
          </span>
        ) : (
          <span
            data-testid={`status-${entry.id}`}
            className={cn(
              "text-xs font-medium",
              getStatusColor(entry.statusCode),
            )}
          >
            {entry.statusCode}
          </span>
        )}
      </td>

      {/* Start time */}
      <td className="px-2 py-1.5 whitespace-nowrap">
        <HumanTimestamp timestamp={entry.startTime ?? 0} />
      </td>

      {/* URL */}
      <td className="px-2 py-1.5 max-w-xs truncate text-xs text-neutral-700 dark:text-neutral-300">
        {urlPath}
      </td>

      {/* Source */}
      <td className="px-2 py-1.5 whitespace-nowrap">
        {entry.source && (
          <span className="text-xs px-1.5 py-0.5 bg-neutral-100 dark:bg-neutral-700 rounded text-neutral-600 dark:text-neutral-400">
            {entry.source}
          </span>
        )}
      </td>

      {/* Size */}
      <td className="px-2 py-1.5 whitespace-nowrap text-right">
        <span
          data-testid={`size-${entry.id}`}
          className="text-xs text-neutral-500 dark:text-neutral-400"
        >
          {formatSize(entry.responseSize)}
        </span>
      </td>

      {/* Duration */}
      <td className="px-2 py-1.5 whitespace-nowrap text-right">
        {entry.duration !== undefined ? (
          <span
            data-testid={`duration-${entry.id}`}
            className="text-xs text-neutral-500 dark:text-neutral-400"
          >
            {entry.duration}ms
          </span>
        ) : (
          <span className="text-xs text-neutral-400 dark:text-neutral-400">
            -
          </span>
        )}
      </td>
    </tr>
  );
}

interface RequestDetailsProps {
  entry: NetworkEntry;
}

function RequestDetails({ entry }: RequestDetailsProps) {
  const [activeTab, setActiveTab] = useState<
    "headers" | "payload" | "response"
  >("headers");

  return (
    <div
      data-testid={`request-details-${entry.id}`}
      className="border-t border-neutral-200 dark:border-neutral-700 bg-neutral-50 dark:bg-neutral-800/50"
    >
      {/* Tabs */}
      <div className="flex border-b border-neutral-200 dark:border-neutral-700">
        {["headers", "payload", "response"].map((tab) => (
          <Button
            key={tab}
            type="button"
            onClick={() => setActiveTab(tab as typeof activeTab)}
            className={cn(
              "px-3 py-1.5 text-xs font-medium capitalize",
              activeTab === tab
                ? "border-b-2 border-primary-500 text-primary-600"
                : "text-neutral-500 dark:text-neutral-400 hover:text-neutral-700 dark:text-neutral-200",
            )}
          >
            {tab}
          </Button>
        ))}
      </div>
      {/* Content */}
      <div className="p-3 text-xs max-h-48 overflow-y-auto">
        {activeTab === "headers" && (
          <div className="space-y-4">
            {/* Request Headers */}
            {entry.requestHeaders &&
              Object.keys(entry.requestHeaders).length > 0 && (
                <div>
                  <h4 className="font-medium text-neutral-700 dark:text-neutral-300 mb-2">
                    Request Headers
                  </h4>
                  <dl className="grid grid-cols-[auto_1fr] gap-x-4 gap-y-1">
                    {Object.entries(entry.requestHeaders).map(
                      ([key, value]) => (
                        <div key={key} className="contents">
                          <dt className="text-neutral-500 dark:text-neutral-400">
                            {key}:
                          </dt>
                          <dd className="text-neutral-700 dark:text-neutral-300">
                            {value}
                          </dd>
                        </div>
                      ),
                    )}
                  </dl>
                </div>
              )}

            {/* Response Headers */}
            {entry.responseHeaders &&
              Object.keys(entry.responseHeaders).length > 0 && (
                <div>
                  <h4 className="font-medium text-neutral-700 dark:text-neutral-300 mb-2">
                    Response Headers
                  </h4>
                  <dl className="grid grid-cols-[auto_1fr] gap-x-4 gap-y-1">
                    {Object.entries(entry.responseHeaders).map(
                      ([key, value]) => (
                        <div key={key} className="contents">
                          <dt className="text-neutral-500 dark:text-neutral-400">
                            {key}:
                          </dt>
                          <dd className="text-neutral-700 dark:text-neutral-300">
                            {value}
                          </dd>
                        </div>
                      ),
                    )}
                  </dl>
                </div>
              )}

            {!entry.requestHeaders && !entry.responseHeaders && (
              <p className="text-neutral-400 dark:text-neutral-400">
                No headers available
              </p>
            )}
          </div>
        )}

        {activeTab === "payload" && (
          <div>
            {entry.requestBody ? (
              <pre className="p-2 bg-neutral-100 dark:bg-neutral-800 rounded overflow-x-auto">
                {typeof entry.requestBody === "string"
                  ? entry.requestBody
                  : JSON.stringify(entry.requestBody, null, 2)}
              </pre>
            ) : (
              <p className="text-neutral-400 dark:text-neutral-400">
                No request payload
              </p>
            )}
          </div>
        )}

        {activeTab === "response" && (
          <div>
            {entry.responseBody ? (
              <pre className="p-2 bg-neutral-100 dark:bg-neutral-800 rounded overflow-x-auto">
                {typeof entry.responseBody === "string"
                  ? entry.responseBody
                  : JSON.stringify(entry.responseBody, null, 2)}
              </pre>
            ) : (
              <p className="text-neutral-400 dark:text-neutral-400">
                No response body
              </p>
            )}
          </div>
        )}
      </div>
    </div>
  );
}

// =============================================================================
// Main Component
// =============================================================================

export function NetworkTab({
  contextEntityId,
  showMCPCalls = true,
  externalEntries = [],
  onClearExternal,
}: NetworkTabProps) {
  const [filter, setFilter] = useState<FilterType>("all");
  const [searchTerm, setSearchTerm] = useState("");
  const [selectedEntryId, setSelectedEntryId] = useState<string | null>(null);
  const listRef = useRef<HTMLDivElement>(null);
  const [sorting, setSorting] = useState<SortingState>([
    { id: "startTime", desc: false },
  ]);

  const {
    entries: localEntries,
    isRecording,
    toggleRecording,
    clearEntries,
  } = useNetworkEntries({ contextEntityId, includeMCP: showMCPCalls });

  // Timeline integration for time-travel debugging
  const timeline = useTimelineContext();

  // Debounce search term to prevent excessive re-renders during typing
  const debouncedSearchTerm = useDebouncedValue(searchTerm, SEARCH_DEBOUNCE_MS);

  // Create stable callbacks for row selection
  const _stableSetSelectedEntryId = useStableCallback(setSelectedEntryId);

  /**
   * Merge and deduplicate local and external entries, sorted by startTime.
   */
  const entries = useMemo(() => {
    // Create a map for deduplication by ID
    const entryMap = new Map<string, NetworkEntry>();

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

    // Convert to array and sort by startTime
    return Array.from(entryMap.values()).sort(
      (a, b) => a.startTime - b.startTime,
    );
  }, [localEntries, externalEntries]);

  /**
   * Handle clearing both local and external entries.
   */
  const handleClearEntries = useCallback(() => {
    clearEntries();
    onClearExternal?.();
  }, [clearEntries, onClearExternal]);

  // Filter entries
  const filteredEntries = useMemo(() => {
    let result = entries;

    // Filter by timeline window for time-travel debugging
    if (timeline.timeWindow) {
      result = result.filter((e) => {
        const entryEnd = e.endTime ?? e.startTime;
        return (
          e.startTime <= timeline.timeWindow!.end &&
          entryEnd >= timeline.timeWindow!.start
        );
      });
    }

    // Filter by type
    if (filter === "api") {
      result = result.filter(
        (e) => !e.source?.startsWith("mcp") && !e.url.startsWith("mcp://"),
      );
    } else if (filter === "mcp") {
      result = result.filter(
        (e) => e.source?.startsWith("mcp") || e.url.startsWith("mcp://"),
      );
    }

    // Filter by showMCPCalls prop
    if (!showMCPCalls) {
      result = result.filter(
        (e) => !e.source?.startsWith("mcp") && !e.url.startsWith("mcp://"),
      );
    }

    // Filter by debounced search term for better performance
    if (debouncedSearchTerm) {
      const lowerSearch = debouncedSearchTerm.toLowerCase();
      result = result.filter(
        (e) =>
          e.url.toLowerCase().includes(lowerSearch) ||
          e.method.toLowerCase().includes(lowerSearch) ||
          e.source?.toLowerCase().includes(lowerSearch),
      );
    }

    return result;
  }, [entries, filter, showMCPCalls, debouncedSearchTerm, timeline.timeWindow]);

  const columns = useMemo<ColumnDef<NetworkEntry>[]>(
    () => [
      { accessorKey: "method", header: "Method" },
      { accessorKey: "statusCode", header: "Status" },
      { accessorKey: "startTime", header: "Start" },
      { accessorKey: "url", header: "URL" },
      { accessorKey: "source", header: "Source" },
      { accessorKey: "responseSize", header: "Size" },
      { accessorKey: "duration", header: "Time" },
    ],
    [],
  );

  const table = useReactTable({
    data: filteredEntries,
    columns,
    state: { sorting },
    onSortingChange: setSorting,
    getCoreRowModel: getCoreRowModel(),
    getSortedRowModel: getSortedRowModel(),
  });

  const sortedRows = table.getRowModel().rows;
  const sortedEntries = useMemo(
    () => sortedRows.map((row) => row.original),
    [sortedRows],
  );

  const selectedEntry = useMemo(
    () => sortedEntries.find((entry) => entry.id === selectedEntryId) ?? null,
    [sortedEntries, selectedEntryId],
  );

  const handleSearchChange = useCallback(
    (e: React.ChangeEvent<HTMLInputElement>) => {
      setSearchTerm(e.target.value);
    },
    [],
  );

  const { isAutoTailing, toggle: toggleAutoTail } = useAutoTail({
    containerRef: listRef,
    enabled: true,
  });

  // Empty state
  if (sortedEntries.length === 0 && entries.length === 0) {
    return (
      <div
        data-testid="network-tab"
        className="flex flex-col h-full bg-white dark:bg-neutral-900"
      >
        <div
          data-testid="network-empty"
          className="flex-1 flex flex-col items-center justify-center text-neutral-400 dark:text-neutral-400"
        >
          <Globe size={32} className="mb-2 opacity-50" />
          <p className="text-sm">No network activity</p>
          <p className="text-xs mt-1">Requests will appear here</p>
        </div>
      </div>
    );
  }

  return (
    <div
      data-testid="network-tab"
      className="flex flex-col h-full bg-white dark:bg-neutral-900"
    >
      {/* Toolbar */}
      <div className="flex items-center gap-2 px-2 py-1 border-b border-neutral-200 dark:border-neutral-700 bg-neutral-50 dark:bg-neutral-800">
        {/* Recording indicator */}
        <Button
          variant="secondary"
          size="sm"
          className="flex .5 px-2 py-1 rounded hover:bg-neutral-200 dark:bg-neutral-700 dark:hover:bg-neutral-700"
          data-testid="recording-toggle"
          type="button"
          onClick={toggleRecording}
          aria-pressed={isRecording}
          aria-label={isRecording ? "Stop recording" : "Start recording"}
        >
          <Circle
            data-testid="recording-indicator"
            size={10}
            className={cn(
              isRecording
                ? "fill-error-500 text-error-500"
                : "fill-neutral-400 text-neutral-400 dark:text-neutral-400",
            )}
          />
        </Button>

        {/* Clear button */}
        <Button
          variant="secondary"
          className="p-1 hover:bg-neutral-200 dark:bg-neutral-700 dark:hover:bg-neutral-700 rounded text-neutral-500 dark:text-neutral-400"
          data-testid="clear-network-button"
          type="button"
          onClick={handleClearEntries}
          aria-label="Clear network log"
        >
          <Trash2 size={14} />
        </Button>

        {/* Filter buttons */}
        <div className="flex items-center gap-1 ml-2">
          <Button
            data-testid="filter-all"
            type="button"
            onClick={() => setFilter("all")}
            className={cn(
              "px-2 py-1 text-xs rounded",
              filter === "all"
                ? "bg-primary-100 dark:bg-primary-900/30 text-primary-600"
                : "hover:bg-neutral-200 dark:bg-neutral-700 dark:hover:bg-neutral-700 text-neutral-500 dark:text-neutral-400",
            )}
          >
            All
          </Button>
          <Button
            data-testid="filter-api"
            type="button"
            onClick={() => setFilter("api")}
            className={cn(
              "px-2 py-1 text-xs rounded",
              filter === "api"
                ? "bg-primary-100 dark:bg-primary-900/30 text-primary-600"
                : "hover:bg-neutral-200 dark:bg-neutral-700 dark:hover:bg-neutral-700 text-neutral-500 dark:text-neutral-400",
            )}
          >
            API
          </Button>
          {showMCPCalls && (
            <Button
              data-testid="filter-mcp"
              type="button"
              onClick={() => setFilter("mcp")}
              className={cn(
                "px-2 py-1 text-xs rounded",
                filter === "mcp"
                  ? "bg-primary-100 dark:bg-primary-900/30 text-primary-600"
                  : "hover:bg-neutral-200 dark:bg-neutral-700 dark:hover:bg-neutral-700 text-neutral-500 dark:text-neutral-400",
              )}
            >
              MCP
            </Button>
          )}
        </div>

        {/* Spacer */}
        <div className="flex-1" />

        {/* Export dropdown */}
        <div className="relative group">
          <Button
            variant="secondary"
            className="p-1 hover:bg-neutral-200 dark:bg-neutral-700 dark:hover:bg-neutral-700 rounded text-neutral-500 dark:text-neutral-400"
            data-testid="export-network-button"
            type="button"
            aria-label="Export network log"
            aria-haspopup="true"
          >
            <Download size={14} />
          </Button>
          <div className="absolute right-0 top-full mt-1 bg-white dark:bg-neutral-800 border border-neutral-200 dark:border-neutral-700 rounded shadow-lg z-10 hidden group-hover:block">
            <Button
              variant="secondary"
              size="sm"
              className="block w-full text-left px-3 py-1.5 text-xs hover:bg-neutral-100 dark:bg-neutral-800 dark:hover:bg-neutral-700 whitespace-nowrap"
              data-testid="export-network-json-button"
              type="button"
              onClick={() => exportNetworkToJSON(filteredEntries)}
            >
              Export as JSON
            </Button>
            <Button
              variant="secondary"
              size="sm"
              className="block w-full text-left px-3 py-1.5 text-xs hover:bg-neutral-100 dark:bg-neutral-800 dark:hover:bg-neutral-700 whitespace-nowrap"
              data-testid="export-network-csv-button"
              type="button"
              onClick={() => exportNetworkToCSV(filteredEntries)}
            >
              Export as CSV
            </Button>
          </div>
        </div>

        {/* Auto-tail toggle */}
        <Button
          data-testid="network-auto-tail"
          type="button"
          onClick={toggleAutoTail}
          aria-pressed={isAutoTailing}
          aria-label={
            isAutoTailing
              ? "Pause auto-tail to newest request"
              : "Resume auto-tail"
          }
          className={cn(
            "p-1 rounded",
            isAutoTailing
              ? "bg-primary-100 text-primary-700 dark:bg-primary-900/30"
              : "hover:bg-neutral-200 dark:bg-neutral-700 dark:hover:bg-neutral-700 text-neutral-500 dark:text-neutral-400",
          )}
        >
          <ArrowDown size={14} />
        </Button>

        {/* Search */}
        <div className="relative">
          <Search
            size={12}
            className="absolute left-2 top-1/2 -translate-y-1/2 text-neutral-400 dark:text-neutral-400"
            aria-hidden="true"
          />
          <Input
            data-testid="network-search"
            placeholder="Filter..."
            value={searchTerm}
            onChange={handleSearchChange}
            className={cn(
              "pl-6 pr-2 py-1 text-xs",
              "bg-white dark:bg-neutral-900",
              "border border-neutral-200 dark:border-neutral-700 rounded",
              "focus:outline-none focus:ring-1 focus:ring-primary-500",
              "w-32",
            )}
            aria-label="Filter network requests"
          />
        </div>

        {/* Entry count */}
        <span className="text-xs text-neutral-500 dark:text-neutral-400">
          {sortedEntries.length} requests
        </span>
      </div>
      {/* Table */}
      <div className="flex-1 overflow-y-auto" ref={listRef}>
        <table role="table" className="w-full text-left">
          <thead className="sticky top-0 bg-neutral-100 dark:bg-neutral-800 text-xs text-neutral-500 dark:text-neutral-400">
            {table.getHeaderGroups().map((headerGroup) => (
              <tr key={headerGroup.id}>
                {headerGroup.headers.map((header) => {
                  const sorted = header.column.getIsSorted();
                  return (
                    <th key={header.id} className="px-2 py-1.5 font-medium">
                      {header.isPlaceholder ? null : (
                        <Button
                          className="flex"
                          type="button"
                          onClick={header.column.getToggleSortingHandler()}
                        >
                          {flexRender(
                            header.column.columnDef.header,
                            header.getContext(),
                          )}
                          <ArrowUpDown
                            size={12}
                            className={cn(
                              sorted
                                ? "text-primary-600"
                                : "text-neutral-400 dark:text-neutral-400",
                              sorted === "desc" && "rotate-180",
                            )}
                          />
                        </Button>
                      )}
                    </th>
                  );
                })}
              </tr>
            ))}
          </thead>
          <tbody>
            {sortedEntries.map((entry) => (
              <NetworkEntryRow
                key={entry.id}
                entry={entry}
                isSelected={selectedEntryId === entry.id}
                onSelect={() =>
                  setSelectedEntryId(
                    selectedEntryId === entry.id ? null : entry.id,
                  )
                }
              />
            ))}
          </tbody>
        </table>
      </div>
      {/* Details panel */}
      {selectedEntry && <RequestDetails entry={selectedEntry} />}
    </div>
  );
}

export default NetworkTab;
