/**
 * AuditEventPanel Component
 *
 * Real-time audit event streaming panel for admin users.
 * Displays security and compliance events from the backend.
 * Features loading states and category filtering.
 */

import { useState, useMemo, useCallback } from "react";
import {
  Wifi,
  WifiOff,
  Pause,
  Play,
  Trash2,
  RefreshCw,
  Shield,
  Filter,
  X,
  Loader2,
} from "lucide-react";
import { useAuditWebSocket } from "../../hooks/useAuditWebSocket";
import type { AuditEvent, AuditFilter } from "../../hooks/useAuditWebSocket";

// =============================================================================
// Types
// =============================================================================

export interface AuditEventPanelProps {
  /** Maximum height for the event list */
  maxHeight?: string;
}

// =============================================================================
// Constants
// =============================================================================

// Available categories for filtering
const FILTER_CATEGORIES = [
  { id: "authentication", label: "Authentication" },
  { id: "authorization", label: "Authorization" },
  { id: "data_access", label: "Data Access" },
  { id: "data_modification", label: "Data Modification" },
  { id: "system", label: "System" },
  { id: "security", label: "Security" },
];

// =============================================================================
// Utility
// =============================================================================

function cn(...classes: (string | undefined | boolean)[]): string {
  return classes.filter(Boolean).join(" ");
}

// Category color mapping
const categoryColors: Record<string, string> = {
  authentication:
    "bg-blue-100 text-blue-800 dark:bg-blue-900/30 dark:text-blue-300",
  authorization:
    "bg-purple-100 text-purple-800 dark:bg-purple-900/30 dark:text-purple-300",
  data_access:
    "bg-green-100 text-green-800 dark:bg-green-900/30 dark:text-green-300",
  data_modification:
    "bg-yellow-100 text-yellow-800 dark:bg-yellow-900/30 dark:text-yellow-300",
  system: "bg-gray-100 text-gray-800 dark:bg-gray-700 dark:text-gray-300",
  security: "bg-red-100 text-red-800 dark:bg-red-900/30 dark:text-red-300",
};

function formatTimestamp(timestamp: string): string {
  try {
    const date = new Date(timestamp);
    return date.toLocaleTimeString(undefined, {
      hour: "2-digit",
      minute: "2-digit",
      second: "2-digit",
    });
  } catch {
    return timestamp;
  }
}

// =============================================================================
// Component
// =============================================================================

export function AuditEventPanel({ maxHeight = "400px" }: AuditEventPanelProps) {
  const {
    status,
    isConnected,
    events,
    currentFilter,
    isPaused,
    setFilter,
    clearFilter,
    pause,
    resume,
    clearEvents,
    reconnect,
  } = useAuditWebSocket();

  // Local state for filter panel visibility
  const [isFilterOpen, setIsFilterOpen] = useState(false);
  const [selectedCategories, setSelectedCategories] = useState<Set<string>>(
    new Set(currentFilter?.categories || []),
  );

  // Check if a filter is active
  const hasActiveFilter = useMemo(() => {
    return (
      currentFilter !== null &&
      ((currentFilter.categories && currentFilter.categories.length > 0) ||
        (currentFilter.regulations && currentFilter.regulations.length > 0) ||
        (currentFilter.actors && currentFilter.actors.length > 0) ||
        (currentFilter.event_types && currentFilter.event_types.length > 0))
    );
  }, [currentFilter]);

  // Handle category toggle
  const handleCategoryToggle = useCallback(
    (categoryId: string) => {
      const newSelected = new Set(selectedCategories);
      if (newSelected.has(categoryId)) {
        newSelected.delete(categoryId);
      } else {
        newSelected.add(categoryId);
      }
      setSelectedCategories(newSelected);

      // Apply filter
      const newFilter: AuditFilter = {
        categories: Array.from(newSelected),
      };
      setFilter(newFilter);
    },
    [selectedCategories, setFilter],
  );

  // Handle clear filter
  const handleClearFilter = useCallback(() => {
    setSelectedCategories(new Set());
    clearFilter();
  }, [clearFilter]);

  // Status text
  const statusText = useMemo(() => {
    switch (status) {
      case "connected":
        return "Connected";
      case "connecting":
        return "Connecting...";
      case "reconnecting":
        return "Reconnecting...";
      case "disconnected":
        return "Disconnected";
      case "error":
        return "Error";
      default:
        return status;
    }
  }, [status]);

  const isConnecting = status === "connecting";
  const isReconnecting = status === "reconnecting";
  const statusColor = isConnected
    ? "text-green-500"
    : isConnecting || isReconnecting
      ? "text-yellow-500"
      : "text-red-500";

  return (
    <div
      data-testid="audit-event-panel"
      className="bg-white dark:bg-gray-800 rounded-lg border border-gray-200 dark:border-gray-700"
    >
      {/* Header */}
      <div className="flex items-center justify-between p-4 border-b border-gray-200 dark:border-gray-700">
        <div className="flex items-center gap-2">
          <Shield className="w-5 h-5 text-purple-600" />
          <h3 className="font-semibold text-gray-900 dark:text-white">
            Audit Events
          </h3>
        </div>

        <div className="flex items-center gap-3">
          {/* Connection Status with loading states */}
          <div
            data-testid="audit-status"
            className={cn("flex items-center gap-1.5 text-sm", statusColor)}
          >
            {isConnecting && (
              <Loader2
                data-testid="connecting-spinner"
                className="w-4 h-4 animate-spin"
              />
            )}
            {isReconnecting && (
              <Loader2
                data-testid="reconnecting-spinner"
                className="w-4 h-4 animate-spin"
              />
            )}
            {!isConnecting && !isReconnecting && isConnected && (
              <Wifi className="w-4 h-4" />
            )}
            {!isConnecting && !isReconnecting && !isConnected && (
              <WifiOff className="w-4 h-4" />
            )}
            <span>{statusText}</span>
          </div>

          {/* Reconnect button (when disconnected) */}
          {!isConnected && !isConnecting && !isReconnecting && (
            <button
              data-testid="reconnect-button"
              onClick={reconnect}
              className="p-1.5 text-blue-600 hover:bg-blue-50 dark:hover:bg-blue-900/30 rounded"
              title="Reconnect"
            >
              <RefreshCw className="w-4 h-4" />
            </button>
          )}

          {/* Filter button with active indicator */}
          <button
            data-testid="filter-toggle"
            onClick={() => setIsFilterOpen(!isFilterOpen)}
            className={cn(
              "p-1.5 rounded relative",
              isFilterOpen
                ? "text-blue-600 bg-blue-50 dark:bg-blue-900/30"
                : "text-gray-600 hover:bg-gray-100 dark:text-gray-400 dark:hover:bg-gray-700",
            )}
            title="Filter events"
          >
            <Filter className="w-4 h-4" />
            {hasActiveFilter && (
              <span
                data-testid="filter-active-badge"
                className="absolute -top-1 -right-1 w-2 h-2 bg-blue-500 rounded-full"
              />
            )}
          </button>

          {/* Clear filter button (when filter is active) */}
          {hasActiveFilter && (
            <button
              data-testid="clear-filter-button"
              onClick={handleClearFilter}
              className="p-1.5 text-gray-600 hover:bg-gray-100 dark:text-gray-400 dark:hover:bg-gray-700 rounded"
              title="Clear filter"
            >
              <X className="w-4 h-4" />
            </button>
          )}

          {/* Pause/Resume button */}
          <button
            data-testid="pause-button"
            onClick={isPaused ? resume : pause}
            className={cn(
              "p-1.5 rounded",
              isPaused
                ? "text-green-600 hover:bg-green-50 dark:hover:bg-green-900/30"
                : "text-gray-600 hover:bg-gray-100 dark:text-gray-400 dark:hover:bg-gray-700",
            )}
            title={isPaused ? "Resume" : "Pause"}
          >
            {isPaused ? (
              <Play className="w-4 h-4" />
            ) : (
              <Pause className="w-4 h-4" />
            )}
          </button>

          {/* Clear button */}
          {events.length > 0 && (
            <button
              data-testid="clear-button"
              onClick={clearEvents}
              className="p-1.5 text-red-600 hover:bg-red-50 dark:hover:bg-red-900/30 rounded"
              title="Clear events"
            >
              <Trash2 className="w-4 h-4" />
            </button>
          )}
        </div>
      </div>

      {/* Filter Panel */}
      {isFilterOpen && (
        <div
          data-testid="filter-panel"
          className="px-4 py-3 bg-gray-50 dark:bg-gray-700/50 border-b border-gray-200 dark:border-gray-700"
        >
          <div className="text-xs font-medium text-gray-500 dark:text-gray-400 mb-2">
            Filter by Category
          </div>
          <div className="flex flex-wrap gap-2">
            {FILTER_CATEGORIES.map((category) => (
              <label
                key={category.id}
                className="inline-flex items-center gap-1.5 cursor-pointer"
              >
                <input
                  type="checkbox"
                  data-testid={`filter-${category.id}`}
                  checked={selectedCategories.has(category.id)}
                  onChange={() => handleCategoryToggle(category.id)}
                  className="w-3.5 h-3.5 rounded border-gray-300 text-blue-600 focus:ring-blue-500"
                />
                <span className="text-xs text-gray-700 dark:text-gray-300">
                  {category.label}
                </span>
              </label>
            ))}
          </div>
        </div>
      )}

      {/* Paused indicator */}
      {isPaused && (
        <div className="px-4 py-2 bg-yellow-50 dark:bg-yellow-900/20 border-b border-yellow-200 dark:border-yellow-800">
          <p className="text-sm text-yellow-700 dark:text-yellow-300 flex items-center gap-2">
            <Pause className="w-4 h-4" />
            Event streaming paused. Click{" "}
            <button
              onClick={resume}
              className="underline font-medium hover:no-underline"
            >
              resume
            </button>{" "}
            to continue.
          </p>
        </div>
      )}

      {/* Event list */}
      <div className="overflow-y-auto" style={{ maxHeight }}>
        {events.length === 0 ? (
          <div className="flex flex-col items-center justify-center py-12 text-gray-500 dark:text-gray-400">
            <Shield className="w-12 h-12 mb-3 opacity-30" />
            <p>No audit events</p>
            <p className="text-sm mt-1">Events will appear here in real-time</p>
          </div>
        ) : (
          <div className="divide-y divide-gray-100 dark:divide-gray-700">
            {events.map((event) => (
              <AuditEventItem key={event.event_id} event={event} />
            ))}
          </div>
        )}
      </div>

      {/* Footer with event count and active filter info */}
      {(events.length > 0 || hasActiveFilter) && (
        <div className="px-4 py-2 border-t border-gray-200 dark:border-gray-700 text-xs text-gray-500 dark:text-gray-400 flex items-center justify-between">
          <span>
            {events.length} event{events.length !== 1 ? "s" : ""}
          </span>
          {hasActiveFilter && (
            <span className="text-blue-600 dark:text-blue-400">
              Filter active: {currentFilter?.categories?.join(", ")}
            </span>
          )}
        </div>
      )}
    </div>
  );
}

// =============================================================================
// Event Item Component
// =============================================================================

interface AuditEventItemProps {
  event: AuditEvent;
}

function AuditEventItem({ event }: AuditEventItemProps) {
  const categoryColor = categoryColors[event.category] || categoryColors.system;

  return (
    <div className="px-4 py-3 hover:bg-gray-50 dark:hover:bg-gray-700/50">
      <div className="flex items-start justify-between gap-4">
        <div className="min-w-0 flex-1">
          <div className="flex items-center gap-2 mb-1">
            <span
              className={cn(
                "px-2 py-0.5 text-xs font-medium rounded-full",
                categoryColor,
              )}
            >
              {event.category}
            </span>
            <span className="text-xs text-gray-500 dark:text-gray-400">
              {event.event_type}
            </span>
            {event.regulation && (
              <span className="px-1.5 py-0.5 text-[10px] font-medium bg-purple-100 text-purple-700 dark:bg-purple-900/30 dark:text-purple-300 rounded">
                {event.regulation}
              </span>
            )}
          </div>
          <div className="text-sm text-gray-900 dark:text-gray-100">
            {event.actor}
          </div>
          {event.resource && (
            <div className="text-xs text-gray-500 dark:text-gray-400 font-mono truncate">
              {event.resource}
            </div>
          )}
        </div>
        <div className="text-xs text-gray-400 dark:text-gray-500 flex-shrink-0">
          {formatTimestamp(event.timestamp)}
        </div>
      </div>
    </div>
  );
}

export default AuditEventPanel;
