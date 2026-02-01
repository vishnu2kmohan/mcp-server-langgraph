/**
 * NetworkTab Component
 *
 * Displays API requests, WebSocket messages, and MCP tool calls.
 * Chrome DevTools Network panel-like interface.
 *
 * Uses shared OTEL components:
 * - OTELStatusBadge for HTTP method and status code badges
 * - HumanTimestamp for relative time display
 * - OTELDetailsPanel for request/response body display
 * - SmartValue for bytes formatting
 *
 * Design System Compliance:
 * - Uses CVA for toolbar button variants
 * - Uses Motion.dev for button press feedback
 * - Implements useReducedMotion() for accessibility
 * - Uses semantic colors per STYLE.md
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
  Globe,
  Loader2,
  Download,
  ArrowDown,
  ArrowUpDown,
} from "lucide-react";

import { motion, useReducedMotion } from "motion/react";
import { cva } from "class-variance-authority";
import { buttonVariants as motionButtonVariants } from "@/design-system/micro-interactions";
import { cn } from "../../../utils/cn";
import { useAutoTail } from "../hooks/useAutoTail";
import { useNetworkEntries } from "../hooks/useNetworkEntries";
import { exportNetworkToJSON, exportNetworkToCSV } from "../utils/export";
import { useDebouncedValue, useStableCallback } from "../utils/performance";
import { useTimelineContext } from "../context/DevToolsTimelineProvider";
import type { NetworkTabProps, NetworkEntry } from "../types";

// Shared OTEL components
import {
  HumanTimestamp,
  OTELStatusBadge,
  SmartValue,
  OTELDetailsPanel,
} from "../components";

import { Button, Input } from "@/components/UI";

// =============================================================================
// Performance Constants
// =============================================================================

/** Debounce delay for search input (ms) */
const SEARCH_DEBOUNCE_MS = 150;

// =============================================================================
// CVA Variants
// =============================================================================

/**
 * Network filter button variants
 */
// eslint-disable-next-line react-refresh/only-export-components
export const networkFilterButtonVariants = cva(
  "px-2 py-1 text-xs rounded transition-colors",
  {
    variants: {
      active: {
        true: "bg-primary-3 dark:bg-primary-4 text-primary-10",
        false: "hover:bg-neutral-3 text-neutral-10",
      },
    },
    defaultVariants: {
      active: false,
    },
  },
);

/**
 * Network auto-tail button variants
 */
// eslint-disable-next-line react-refresh/only-export-components
export const networkAutoTailButtonVariants = cva(
  "p-1 rounded transition-colors",
  {
    variants: {
      active: {
        true: "bg-primary-3 dark:bg-primary-4 text-primary-11",
        false: "hover:bg-neutral-3 text-neutral-10",
      },
    },
    defaultVariants: {
      active: false,
    },
  },
);

// =============================================================================
// Types
// =============================================================================

type FilterType = "all" | "api" | "mcp";

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
        "cursor-pointer border-b border-neutral-5",
        "hover:bg-neutral-a6",
        isSelected && "bg-primary-1 dark:bg-primary-a3",
        isError === true && "bg-error-1 dark:bg-error-a2",
      )}
      onClick={onSelect}
    >
      {/* Method */}
      <td className="px-2 py-1.5 whitespace-nowrap">
        <OTELStatusBadge
          type="http-method"
          value={entry.method}
          size="sm"
          data-testid={`method-${entry.id}`}
        />
      </td>

      {/* Status */}
      <td className="px-2 py-1.5 whitespace-nowrap">
        {isPending ? (
          <span data-testid={`pending-${entry.id}`}>
            <Loader2 size={12} className="animate-spin text-primary-9" />
          </span>
        ) : (
          <OTELStatusBadge
            type="http-status"
            value={entry.statusCode ?? 0}
            size="sm"
            data-testid={`status-${entry.id}`}
          />
        )}
      </td>

      {/* Start time */}
      <td className="px-2 py-1.5 whitespace-nowrap">
        <HumanTimestamp timestamp={entry.startTime ?? 0} format="relative" />
      </td>

      {/* URL */}
      <td className="px-2 py-1.5 max-w-xs truncate text-xs text-neutral-11">
        {urlPath}
      </td>

      {/* Source */}
      <td className="px-2 py-1.5 whitespace-nowrap">
        {entry.source && (
          <span className="text-xs px-1.5 py-0.5 bg-neutral-2 rounded text-neutral-11">
            {entry.source}
          </span>
        )}
      </td>

      {/* Size */}
      <td className="px-2 py-1.5 whitespace-nowrap text-right">
        <SmartValue
          value={entry.responseSize}
          type="bytes"
          data-testid={`size-${entry.id}`}
        />
      </td>

      {/* Duration */}
      <td className="px-2 py-1.5 whitespace-nowrap text-right">
        {entry.duration !== undefined ? (
          <SmartValue
            value={entry.duration}
            type="duration"
            data-testid={`duration-${entry.id}`}
          />
        ) : (
          <span className="text-xs text-neutral-9">-</span>
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

  // Combine request and response headers for header tab
  const headersData = useMemo(() => {
    const data: Record<string, unknown> = {};
    if (entry.requestHeaders && Object.keys(entry.requestHeaders).length > 0) {
      data.requestHeaders = entry.requestHeaders;
    }
    if (
      entry.responseHeaders &&
      Object.keys(entry.responseHeaders).length > 0
    ) {
      data.responseHeaders = entry.responseHeaders;
    }
    return data;
  }, [entry.requestHeaders, entry.responseHeaders]);

  const hasHeaders = Object.keys(headersData).length > 0;

  return (
    <div
      data-testid={`request-details-${entry.id}`}
      className="border-t border-neutral-5 bg-neutral-1"
    >
      {/* Tabs */}
      <div className="flex border-b border-neutral-5">
        {["headers", "payload", "response"].map((tab) => (
          <Button
            variant="primary"
            key={tab}
            type="button"
            onClick={() => setActiveTab(tab as typeof activeTab)}
            className={cn(
              "px-3 py-1.5 text-xs font-medium capitalize",
              activeTab === tab
                ? "border-b-2 border-primary-9 text-primary-10"
                : "text-neutral-10 hover:text-neutral-11",
            )}
          >
            {tab}
          </Button>
        ))}
      </div>
      {/* Content */}
      <div className="p-3 text-xs max-h-48 overflow-y-auto">
        {activeTab === "headers" && (
          <div>
            {hasHeaders ? (
              <OTELDetailsPanel
                data={headersData}
                title="Headers"
                defaultView="summary"
              />
            ) : (
              <p className="text-neutral-9">No headers available</p>
            )}
          </div>
        )}

        {activeTab === "payload" && (
          <div>
            {entry.requestBody ? (
              <OTELDetailsPanel
                data={
                  typeof entry.requestBody === "string"
                    ? { body: entry.requestBody }
                    : (entry.requestBody as Record<string, unknown>)
                }
                title="Request Payload"
                defaultView="raw"
              />
            ) : (
              <p className="text-neutral-9">No request payload</p>
            )}
          </div>
        )}

        {activeTab === "response" && (
          <div>
            {entry.responseBody ? (
              <OTELDetailsPanel
                data={
                  typeof entry.responseBody === "string"
                    ? { body: entry.responseBody }
                    : (entry.responseBody as Record<string, unknown>)
                }
                title="Response Body"
                defaultView="raw"
              />
            ) : (
              <p className="text-neutral-9">No response body</p>
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
  const prefersReducedMotion = useReducedMotion();
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
        className="flex flex-col h-full bg-neutral-1"
      >
        <div
          data-testid="network-empty"
          className="flex-1 flex flex-col items-center justify-center text-neutral-9"
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
      className="flex flex-col h-full bg-neutral-1"
    >
      {/* Toolbar */}
      <div className="flex items-center gap-2 px-2 py-1 border-b border-neutral-5 bg-neutral-1">
        {/* Recording indicator */}
        <Button
          variant="secondary"
          size="icon"
          className="flex .5 px-2 py-1 rounded hover:bg-neutral-3"
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
                ? "fill-error-9 text-error-9"
                : "fill-neutral-9 text-neutral-9",
            )}
          />
        </Button>

        {/* Clear button */}
        <Button
          size="icon"
          variant="secondary"
          className="p-1 hover:bg-neutral-3 rounded text-neutral-10"
          data-testid="clear-network-button"
          type="button"
          onClick={handleClearEntries}
          aria-label="Clear network log"
        >
          <Trash2 size={14} />
        </Button>

        {/* Filter buttons */}
        <div className="flex items-center gap-1 ml-2">
          <motion.button
            data-testid="filter-all"
            type="button"
            onClick={() => setFilter("all")}
            className={networkFilterButtonVariants({
              active: filter === "all",
            })}
            variants={prefersReducedMotion ? undefined : motionButtonVariants}
            initial="rest"
            whileHover="hover"
            whileTap="pressed"
          >
            All
          </motion.button>
          <motion.button
            data-testid="filter-api"
            type="button"
            onClick={() => setFilter("api")}
            className={networkFilterButtonVariants({
              active: filter === "api",
            })}
            variants={prefersReducedMotion ? undefined : motionButtonVariants}
            initial="rest"
            whileHover="hover"
            whileTap="pressed"
          >
            API
          </motion.button>
          {showMCPCalls && (
            <motion.button
              data-testid="filter-mcp"
              type="button"
              onClick={() => setFilter("mcp")}
              className={networkFilterButtonVariants({
                active: filter === "mcp",
              })}
              variants={prefersReducedMotion ? undefined : motionButtonVariants}
              initial="rest"
              whileHover="hover"
              whileTap="pressed"
            >
              MCP
            </motion.button>
          )}
        </div>

        {/* Spacer */}
        <div className="flex-1" />

        {/* Export dropdown */}
        <div className="relative group">
          <Button
            size="icon"
            variant="secondary"
            className="p-1 hover:bg-neutral-3 rounded text-neutral-10"
            data-testid="export-network-button"
            type="button"
            aria-label="Export network log"
            aria-haspopup="true"
          >
            <Download size={14} />
          </Button>
          <div className="absolute right-0 top-full mt-1 bg-neutral-1 border border-neutral-5 rounded shadow-lg z-dropdown hidden group-hover:block">
            <Button
              variant="secondary"
              size="sm"
              className="block w-full text-left px-3 py-1.5 text-xs hover:bg-neutral-2 whitespace-nowrap"
              data-testid="export-network-json-button"
              type="button"
              onClick={() => exportNetworkToJSON(filteredEntries)}
            >
              Export as JSON
            </Button>
            <Button
              variant="secondary"
              size="sm"
              className="block w-full text-left px-3 py-1.5 text-xs hover:bg-neutral-2 whitespace-nowrap"
              data-testid="export-network-csv-button"
              type="button"
              onClick={() => exportNetworkToCSV(filteredEntries)}
            >
              Export as CSV
            </Button>
          </div>
        </div>

        {/* Auto-tail toggle */}
        <motion.button
          data-testid="network-auto-tail"
          type="button"
          onClick={toggleAutoTail}
          aria-pressed={isAutoTailing}
          aria-label={
            isAutoTailing
              ? "Pause auto-tail to newest request"
              : "Resume auto-tail"
          }
          className={networkAutoTailButtonVariants({ active: isAutoTailing })}
          variants={prefersReducedMotion ? undefined : motionButtonVariants}
          initial="rest"
          whileHover="hover"
          whileTap="pressed"
        >
          <ArrowDown size={14} />
        </motion.button>

        {/* Search */}
        <div className="relative">
          <Search
            className="absolute left-2 top-1/2 -translate-y-1/2 h-4 w-4 text-neutral-9"
            aria-hidden="true"
          />
          <Input
            data-testid="network-search"
            placeholder="Filter..."
            value={searchTerm}
            onChange={handleSearchChange}
            className={cn(
              "h-8 pl-8 pr-2 py-1.5 text-sm",
              "bg-neutral-1",
              "border border-neutral-5 rounded",
              "focus:outline-none focus:ring-1 focus:ring-primary-7",
              "w-40",
            )}
            aria-label="Filter network requests"
          />
        </div>

        {/* Entry count */}
        <span className="text-xs text-neutral-10">
          {sortedEntries.length} requests
        </span>
      </div>
      {/* Table */}
      <div className="flex-1 overflow-y-auto" ref={listRef}>
        <table role="table" className="w-full text-left">
          <thead className="sticky top-0 bg-neutral-2 text-xs text-neutral-10">
            {table.getHeaderGroups().map((headerGroup) => (
              <tr key={headerGroup.id}>
                {headerGroup.headers.map((header) => {
                  const sorted = header.column.getIsSorted();
                  return (
                    <th key={header.id} className="px-2 py-1.5 font-medium">
                      {header.isPlaceholder ? null : (
                        <Button
                          variant="ghost"
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
                              sorted ? "text-primary-10" : "text-neutral-9",
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
