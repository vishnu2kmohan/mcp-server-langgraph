/**
 * NetworkTab Component
 *
 * Displays API requests, WebSocket messages, and MCP tool calls.
 * Chrome DevTools Network panel-like interface.
 */
import { useState, useMemo, useCallback } from "react";
import {
  Trash2,
  Search,
  Circle,
  ChevronRight as _ChevronRight,
  ChevronDown as _ChevronDown,
  Globe,
  Loader2,
} from "lucide-react";

import { cn } from "../../../utils/cn";
import { useNetworkEntries } from "../hooks/useNetworkEntries";
import type { NetworkTabProps, NetworkEntry } from "../types";

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

function getStatusColor(statusCode: number | undefined): string {
  if (!statusCode) return "text-gray-400";
  if (statusCode >= 200 && statusCode < 300)
    return "text-green-600 dark:text-green-400";
  if (statusCode >= 300 && statusCode < 400)
    return "text-blue-600 dark:text-blue-400";
  if (statusCode >= 400 && statusCode < 500)
    return "text-amber-600 dark:text-amber-400";
  if (statusCode >= 500) return "text-red-600 dark:text-red-400";
  return "text-gray-600";
}

function getMethodColor(method: string): string {
  switch (method) {
    case "GET":
      return "text-green-600 dark:text-green-400";
    case "POST":
      return "text-blue-600 dark:text-blue-400";
    case "PUT":
      return "text-amber-600 dark:text-amber-400";
    case "DELETE":
      return "text-red-600 dark:text-red-400";
    case "PATCH":
      return "text-purple-600 dark:text-purple-400";
    default:
      return "text-gray-600";
  }
}

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
        "cursor-pointer border-b border-gray-100 dark:border-gray-800",
        "hover:bg-gray-50 dark:hover:bg-gray-800/50",
        isSelected && "bg-blue-50 dark:bg-blue-900/20",
        isError === true && "bg-red-50 dark:bg-red-900/10",
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
            <Loader2 size={12} className="animate-spin text-blue-500" />
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

      {/* URL */}
      <td className="px-2 py-1.5 max-w-xs truncate text-xs text-gray-700 dark:text-gray-300">
        {urlPath}
      </td>

      {/* Source */}
      <td className="px-2 py-1.5 whitespace-nowrap">
        {entry.source && (
          <span className="text-xs px-1.5 py-0.5 bg-gray-100 dark:bg-gray-700 rounded text-gray-600 dark:text-gray-400">
            {entry.source}
          </span>
        )}
      </td>

      {/* Size */}
      <td className="px-2 py-1.5 whitespace-nowrap text-right">
        <span
          data-testid={`size-${entry.id}`}
          className="text-xs text-gray-500"
        >
          {formatSize(entry.responseSize)}
        </span>
      </td>

      {/* Duration */}
      <td className="px-2 py-1.5 whitespace-nowrap text-right">
        {entry.duration !== undefined ? (
          <span
            data-testid={`duration-${entry.id}`}
            className="text-xs text-gray-500"
          >
            {entry.duration}ms
          </span>
        ) : (
          <span className="text-xs text-gray-400">-</span>
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
      className="border-t border-gray-200 dark:border-gray-700 bg-gray-50 dark:bg-gray-800/50"
    >
      {/* Tabs */}
      <div className="flex border-b border-gray-200 dark:border-gray-700">
        {["headers", "payload", "response"].map((tab) => (
          <button
            key={tab}
            type="button"
            onClick={() => setActiveTab(tab as typeof activeTab)}
            className={cn(
              "px-3 py-1.5 text-xs font-medium capitalize",
              activeTab === tab
                ? "border-b-2 border-primary-500 text-primary-600"
                : "text-gray-500 hover:text-gray-700",
            )}
          >
            {tab}
          </button>
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
                  <h4 className="font-medium text-gray-700 dark:text-gray-300 mb-2">
                    Request Headers
                  </h4>
                  <dl className="grid grid-cols-[auto_1fr] gap-x-4 gap-y-1">
                    {Object.entries(entry.requestHeaders).map(
                      ([key, value]) => (
                        <div key={key} className="contents">
                          <dt className="text-gray-500">{key}:</dt>
                          <dd className="text-gray-700 dark:text-gray-300">
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
                  <h4 className="font-medium text-gray-700 dark:text-gray-300 mb-2">
                    Response Headers
                  </h4>
                  <dl className="grid grid-cols-[auto_1fr] gap-x-4 gap-y-1">
                    {Object.entries(entry.responseHeaders).map(
                      ([key, value]) => (
                        <div key={key} className="contents">
                          <dt className="text-gray-500">{key}:</dt>
                          <dd className="text-gray-700 dark:text-gray-300">
                            {value}
                          </dd>
                        </div>
                      ),
                    )}
                  </dl>
                </div>
              )}

            {!entry.requestHeaders && !entry.responseHeaders && (
              <p className="text-gray-400">No headers available</p>
            )}
          </div>
        )}

        {activeTab === "payload" && (
          <div>
            {entry.requestBody ? (
              <pre className="p-2 bg-gray-100 dark:bg-gray-900 rounded overflow-x-auto">
                {typeof entry.requestBody === "string"
                  ? entry.requestBody
                  : JSON.stringify(entry.requestBody, null, 2)}
              </pre>
            ) : (
              <p className="text-gray-400">No request payload</p>
            )}
          </div>
        )}

        {activeTab === "response" && (
          <div>
            {entry.responseBody ? (
              <pre className="p-2 bg-gray-100 dark:bg-gray-900 rounded overflow-x-auto">
                {typeof entry.responseBody === "string"
                  ? entry.responseBody
                  : JSON.stringify(entry.responseBody, null, 2)}
              </pre>
            ) : (
              <p className="text-gray-400">No response body</p>
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
}: NetworkTabProps) {
  const [filter, setFilter] = useState<FilterType>("all");
  const [searchTerm, setSearchTerm] = useState("");
  const [selectedEntryId, setSelectedEntryId] = useState<string | null>(null);

  const { entries, isRecording, toggleRecording, clearEntries } =
    useNetworkEntries({ contextEntityId, includeMCP: showMCPCalls });

  // Filter entries
  const filteredEntries = useMemo(() => {
    let result = entries;

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

    // Filter by search
    if (searchTerm) {
      const lowerSearch = searchTerm.toLowerCase();
      result = result.filter(
        (e) =>
          e.url.toLowerCase().includes(lowerSearch) ||
          e.method.toLowerCase().includes(lowerSearch) ||
          e.source?.toLowerCase().includes(lowerSearch),
      );
    }

    return result;
  }, [entries, filter, showMCPCalls, searchTerm]);

  const handleSearchChange = useCallback(
    (e: React.ChangeEvent<HTMLInputElement>) => {
      setSearchTerm(e.target.value);
    },
    [],
  );

  // Empty state
  if (filteredEntries.length === 0 && entries.length === 0) {
    return (
      <div
        data-testid="network-tab"
        className="flex flex-col h-full bg-white dark:bg-gray-900"
      >
        <div
          data-testid="network-empty"
          className="flex-1 flex flex-col items-center justify-center text-gray-400"
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
      className="flex flex-col h-full bg-white dark:bg-gray-900"
    >
      {/* Toolbar */}
      <div className="flex items-center gap-2 px-2 py-1 border-b border-gray-200 dark:border-gray-700 bg-gray-50 dark:bg-gray-800">
        {/* Recording indicator */}
        <button
          data-testid="recording-toggle"
          type="button"
          onClick={toggleRecording}
          className="flex items-center gap-1.5 px-2 py-1 rounded hover:bg-gray-200 dark:hover:bg-gray-700"
          aria-pressed={isRecording}
          aria-label={isRecording ? "Stop recording" : "Start recording"}
        >
          <Circle
            data-testid="recording-indicator"
            size={10}
            className={cn(
              isRecording
                ? "fill-red-500 text-red-500"
                : "fill-gray-400 text-gray-400",
            )}
          />
        </button>

        {/* Clear button */}
        <button
          data-testid="clear-network-button"
          type="button"
          onClick={clearEntries}
          className="p-1 hover:bg-gray-200 dark:hover:bg-gray-700 rounded text-gray-500"
          aria-label="Clear network log"
        >
          <Trash2 size={14} />
        </button>

        {/* Filter buttons */}
        <div className="flex items-center gap-1 ml-2">
          <button
            data-testid="filter-all"
            type="button"
            onClick={() => setFilter("all")}
            className={cn(
              "px-2 py-1 text-xs rounded",
              filter === "all"
                ? "bg-primary-100 dark:bg-primary-900/30 text-primary-600"
                : "hover:bg-gray-200 dark:hover:bg-gray-700 text-gray-500",
            )}
          >
            All
          </button>
          <button
            data-testid="filter-api"
            type="button"
            onClick={() => setFilter("api")}
            className={cn(
              "px-2 py-1 text-xs rounded",
              filter === "api"
                ? "bg-primary-100 dark:bg-primary-900/30 text-primary-600"
                : "hover:bg-gray-200 dark:hover:bg-gray-700 text-gray-500",
            )}
          >
            API
          </button>
          {showMCPCalls && (
            <button
              data-testid="filter-mcp"
              type="button"
              onClick={() => setFilter("mcp")}
              className={cn(
                "px-2 py-1 text-xs rounded",
                filter === "mcp"
                  ? "bg-primary-100 dark:bg-primary-900/30 text-primary-600"
                  : "hover:bg-gray-200 dark:hover:bg-gray-700 text-gray-500",
              )}
            >
              MCP
            </button>
          )}
        </div>

        {/* Spacer */}
        <div className="flex-1" />

        {/* Search */}
        <div className="relative">
          <Search
            size={12}
            className="absolute left-2 top-1/2 -translate-y-1/2 text-gray-400"
            aria-hidden="true"
          />
          <input
            data-testid="network-search"
            type="text"
            placeholder="Filter..."
            value={searchTerm}
            onChange={handleSearchChange}
            className={cn(
              "pl-6 pr-2 py-1 text-xs",
              "bg-white dark:bg-gray-900",
              "border border-gray-200 dark:border-gray-700 rounded",
              "focus:outline-none focus:ring-1 focus:ring-primary-500",
              "w-32",
            )}
            aria-label="Filter network requests"
          />
        </div>

        {/* Entry count */}
        <span className="text-xs text-gray-500">
          {filteredEntries.length} requests
        </span>
      </div>

      {/* Table */}
      <div className="flex-1 overflow-y-auto">
        <table role="table" className="w-full text-left">
          <thead className="sticky top-0 bg-gray-100 dark:bg-gray-800 text-xs text-gray-500">
            <tr>
              <th className="px-2 py-1.5 font-medium">Method</th>
              <th className="px-2 py-1.5 font-medium">Status</th>
              <th className="px-2 py-1.5 font-medium">URL</th>
              <th className="px-2 py-1.5 font-medium">Source</th>
              <th className="px-2 py-1.5 font-medium text-right">Size</th>
              <th className="px-2 py-1.5 font-medium text-right">Time</th>
            </tr>
          </thead>
          <tbody>
            {filteredEntries.map((entry) => (
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
      {selectedEntryId && (
        <RequestDetails
          entry={filteredEntries.find((e) => e.id === selectedEntryId)!}
        />
      )}
    </div>
  );
}

export default NetworkTab;
