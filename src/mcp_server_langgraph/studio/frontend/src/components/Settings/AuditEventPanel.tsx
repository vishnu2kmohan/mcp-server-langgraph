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

import { Button, Checkbox } from "@/components/UI";

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
    "bg-primary-3 text-primary-11 bg-primary-4 dark:text-primary-5",
  authorization:
    "bg-insight-2 text-insight-11 dark:bg-insight-a4 dark:text-insight-5",
  data_access:
    "bg-success-3 text-success-11 bg-success-4 dark:text-success-5",
  data_modification:
    "bg-warning-3 text-warning-11 dark:bg-warning-a4 dark:text-warning-6",
  system:
    "bg-neutral-2 text-neutral-12",
  security:
    "bg-error-3 text-error-11 bg-error-4 dark:text-error-9",
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
        (currentFilter.eventTypes && currentFilter.eventTypes.length > 0))
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
    ? "text-success-9"
    : isConnecting || isReconnecting
      ? "text-warning-9"
      : "text-error-9";

  return (
    <div
      data-testid="audit-event-panel"
      className="bg-neutral-1 rounded-lg border border-neutral-5"
    >
      {/* Header */}
      <div className="flex items-center justify-between p-4 border-b border-neutral-5">
        <div className="flex items-center gap-2">
          <Shield className="w-5 h-5 text-insight-10" />
          <h3 className="font-semibold text-neutral-12">
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
            <Button size="icon"
              variant="primary"
              className="p-1.5 text-primary-10 hover:bg-primary-1 dark:hover:bg-primary-a4 rounded"
              data-testid="reconnect-button"
              onClick={reconnect}
              title="Reconnect"
            >
              <RefreshCw className="w-4 h-4" />
            </Button>
          )}

          {/* Filter button with active indicator */}
          <Button
            data-testid="filter-toggle"
            onClick={() => setIsFilterOpen(!isFilterOpen)}
            className={cn(
              "p-1.5 rounded relative",
              isFilterOpen
                ? "text-primary-10 bg-primary-1 bg-primary-4"
                : "text-neutral-11 hover:bg-neutral-2",
            )}
            title="Filter events"
          >
            <Filter className="w-4 h-4" />
            {hasActiveFilter && (
              <span
                data-testid="filter-active-badge"
                className="absolute -top-1 -right-1 w-2 h-2 bg-primary-9 rounded-full"
              />
            )}
          </Button>

          {/* Clear filter button (when filter is active) */}
          {hasActiveFilter && (
            <Button size="icon"
              variant="secondary"
              className="p-1.5 text-neutral-11 hover:bg-neutral-2 rounded"
              data-testid="clear-filter-button"
              onClick={handleClearFilter}
              title="Clear filter"
            >
              <X className="w-4 h-4" />
            </Button>
          )}

          {/* Pause/Resume button */}
          <Button
            data-testid="pause-button"
            onClick={isPaused ? resume : pause}
            className={cn(
              "p-1.5 rounded",
              isPaused
                ? "text-success-10 hover:bg-success-1 dark:hover:bg-success-a4"
                : "text-neutral-11 hover:bg-neutral-2",
            )}
            title={isPaused ? "Resume" : "Pause"}
          >
            {isPaused ? (
              <Play className="w-4 h-4" />
            ) : (
              <Pause className="w-4 h-4" />
            )}
          </Button>

          {/* Clear button */}
          {events.length > 0 && (
            <Button size="icon"
              variant="danger"
              className="p-1.5 text-error-10 hover:bg-error-1 dark:hover:bg-error-a4 rounded"
              data-testid="clear-button"
              onClick={clearEvents}
              title="Clear events"
            >
              <Trash2 className="w-4 h-4" />
            </Button>
          )}
        </div>
      </div>
      {/* Filter Panel */}
      {isFilterOpen && (
        <div
          data-testid="filter-panel"
          className="px-4 py-3 bg-neutral-1 border-b border-neutral-5"
        >
          <div className="text-xs font-medium text-neutral-10 mb-2">
            Filter by Category
          </div>
          <div className="flex flex-wrap gap-2">
            {FILTER_CATEGORIES.map((category) => (
              <Checkbox
                key={category.id}
                data-testid={`filter-${category.id}`}
                checked={selectedCategories.has(category.id)}
                onChange={() => handleCategoryToggle(category.id)}
                label={category.label}
                size="sm"
              />
            ))}
          </div>
        </div>
      )}
      {/* Paused indicator */}
      {isPaused && (
        <div className="px-4 py-2 bg-warning-3 bg-warning-3 border-b border-warning-6 dark:border-warning-11">
          <p className="text-sm text-warning-10 dark:text-warning-6 flex items-center gap-2">
            <Pause className="w-4 h-4" />
            Event streaming paused. Click{" "}
            <Button variant="ghost" className="underline hover:no-underline" onClick={resume}>
              resume
            </Button>{" "}
            to continue.
          </p>
        </div>
      )}
      {/* Event list */}
      <div className="overflow-y-auto" style={{ maxHeight }}>
        {events.length === 0 ? (
          <div className="flex flex-col items-center justify-center py-12 text-neutral-10">
            <Shield className="w-12 h-12 mb-3 opacity-30" />
            <p>No audit events</p>
            <p className="text-sm mt-1">Events will appear here in real-time</p>
          </div>
        ) : (
          <div className="divide-y divide-neutral-5">
            {events.map((event) => (
              <AuditEventItem key={event.eventId} event={event} />
            ))}
          </div>
        )}
      </div>
      {/* Footer with event count and active filter info */}
      {(events.length > 0 || hasActiveFilter) && (
        <div className="px-4 py-2 border-t border-neutral-5 text-xs text-neutral-10 flex items-center justify-between">
          <span>
            {events.length} event{events.length !== 1 ? "s" : ""}
          </span>
          {hasActiveFilter && (
            <span className="text-primary-10 dark:text-primary-7">
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
    <div className="px-4 py-3 hover:bg-neutral-a6">
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
            <span className="text-xs text-neutral-10">
              {event.eventType}
            </span>
            {event.regulation && (
              <span className="px-1.5 py-0.5 text-xs font-medium bg-insight-2 text-insight-11 dark:bg-insight-a4 dark:text-insight-5 rounded">
                {event.regulation}
              </span>
            )}
          </div>
          <div className="text-sm text-neutral-12">
            {event.actor}
          </div>
          {event.resource && (
            <div className="text-xs text-neutral-10 font-mono truncate">
              {event.resource}
            </div>
          )}
        </div>
        <div className="text-xs text-neutral-9 flex-shrink-0">
          {formatTimestamp(event.timestamp)}
        </div>
      </div>
    </div>
  );
}

export default AuditEventPanel;
