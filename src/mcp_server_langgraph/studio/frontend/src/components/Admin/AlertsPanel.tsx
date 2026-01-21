/**
 * AlertsPanel Component
 *
 * Infrastructure alerts panel for Admin dashboard with real-time updates.
 *
 * Features:
 * - Display alert list with severity indicators
 * - Filter controls (severity, state)
 * - Sound toggle for critical alerts
 * - Real-time badge counts
 * - Alert selection for detail view
 *
 * Reference: ADR-0026 - Comprehensive Client Resilience Patterns
 */

import { useState, useEffect, useCallback } from "react";
import { useReducedMotion } from "motion/react";
import {
  AlertTriangle,
  Volume2,
  VolumeX,
  Loader2,
  List,
  Layers,
} from "lucide-react";
import { cn } from "../../utils/cn";
import { useAppSelector } from "../../store/hooks";
import {
  selectSelectedAlertId,
  selectSoundEnabled,
  selectFilters,
  selectCriticalAlertCount,
  selectWarningAlertCount,
  selectFilteredAlerts,
  selectFilteredAlertGroups,
  type Alert,
  type AlertFilters,
} from "../../store/slices/alertSlice";
import type { WebSocketConnectionStatus } from "../../hooks/useRealtimeSync";
import { AlertGroupsPanel } from "./AlertGroupsPanel";
import { storage } from "../../utils/storage";
import { AIEmptyState } from "../EmptyState/AIEmptyState";

import { Button } from "@/components/UI";

// =============================================================================
// Constants
// =============================================================================

const VIEW_MODE_STORAGE_KEY = "alert-view-mode";

type ViewMode = "flat" | "grouped";

// =============================================================================
// Types
// =============================================================================

export interface AlertsPanelProps {
  /** Callback when an alert is selected */
  onSelectAlert: (alertId: string) => void;
  /** Callback when sound toggle is clicked */
  onSoundToggle: () => void;
  /** Callback when filters change */
  onFilterChange?: (filters: Partial<AlertFilters>) => void;
  /** Loading state */
  isLoading?: boolean;
  /** WebSocket connection status */
  connectionStatus?: WebSocketConnectionStatus;
}

// =============================================================================
// Utility Functions
// =============================================================================

/**
 * Format relative time from ISO date string
 */
function formatRelativeTime(isoDate: string): string {
  const date = new Date(isoDate);
  const now = new Date();
  const diffMs = now.getTime() - date.getTime();
  const diffMins = Math.floor(diffMs / (1000 * 60));
  const diffHours = Math.floor(diffMs / (1000 * 60 * 60));
  const diffDays = Math.floor(diffMs / (1000 * 60 * 60 * 24));

  if (diffMins < 1) return "Just now";
  if (diffMins < 60) return `${diffMins}m ago`;
  if (diffHours < 24) return `${diffHours}h ago`;
  return `${diffDays}d ago`;
}

/**
 * Get severity badge color class
 */
function getSeverityColor(severity: Alert["severity"]): string {
  switch (severity) {
    case "critical":
      return "bg-error-9";
    case "warning":
      return "bg-warning-9";
    default:
      return "bg-neutral-5";
  }
}

/**
 * Get state badge styling
 */
function getStateStyle(state: Alert["state"]): { bg: string; text: string } {
  switch (state) {
    case "firing":
      return {
        bg: "bg-error-3 bg-error-4",
        text: "text-error-11 dark:text-error-7",
      };
    case "resolved":
      return {
        bg: "bg-success-3 bg-success-4",
        text: "text-success-11 dark:text-success-7",
      };
    default:
      return {
        bg: "bg-neutral-2",
        text: "text-neutral-11",
      };
  }
}

/**
 * Get connection status color
 */
function getConnectionColor(status?: WebSocketConnectionStatus): string {
  switch (status) {
    case "connected":
      return "bg-success-9";
    case "connecting":
    case "reconnecting":
      return "bg-warning-9";
    case "disconnected":
    case "error":
      return "bg-error-9";
    default:
      return "bg-neutral-5";
  }
}

// =============================================================================
// Sub-Components
// =============================================================================

interface AlertItemProps {
  alert: Alert;
  isSelected: boolean;
  onClick: () => void;
}

function AlertItem({
  alert,
  isSelected,
  onClick,
}: AlertItemProps) {
  const stateStyle = getStateStyle(alert.state);
  const serviceLabel = alert.labels.service || alert.labels.pod || null;

  return (
    <Button
      variant="primary"
      className={cn(
        "w-full text-left p-3 rounded-lg border",
        isSelected && "border-primary-9 bg-primary-a2",
      )}
      data-testid={`alert-item-${alert.alertId}`}
      onClick={onClick}>
      <div className="flex items-start gap-3">
        {/* Severity Indicator */}
        <div
          data-testid={`severity-badge-${alert.alertId}`}
          className={`w-2 h-2 mt-2 rounded-full flex-shrink-0 ${getSeverityColor(
            alert.severity,
          )}`}
        />

        <div className="flex-1 min-w-0">
          {/* Alert Name and State */}
          <div className="flex items-center gap-2 mb-1">
            <span className="font-medium text-neutral-12 truncate">
              {alert.name}
            </span>
            <span
              data-testid={`state-badge-${alert.alertId}`}
              className={`text-xs px-2 py-0.5 rounded-full ${stateStyle.bg} ${stateStyle.text}`}
            >
              {alert.state.charAt(0).toUpperCase() + alert.state.slice(1)}
            </span>
          </div>

          {/* Message */}
          <p className="text-sm text-neutral-11 truncate mb-1">
            {alert.message}
          </p>

          {/* Labels and Time */}
          <div className="flex items-center gap-2 text-xs text-neutral-10">
            {serviceLabel && (
              <span className="px-1.5 py-0.5 bg-neutral-2 rounded">
                {serviceLabel}
              </span>
            )}
            <span data-testid={`alert-time-${alert.alertId}`}>
              {formatRelativeTime(alert.startedAt)}
            </span>
          </div>
        </div>
      </div>
    </Button>
  );
}

// =============================================================================
// Main Component
// =============================================================================

export function AlertsPanel({
  onSelectAlert,
  onSoundToggle,
  onFilterChange,
  isLoading = false,
  connectionStatus = "connected",
}: AlertsPanelProps) {
  // WCAG 2.2 AA: Respect user's reduced motion preference
  const prefersReducedMotion = useReducedMotion();

  // Redux state
  const filteredAlerts = useAppSelector(selectFilteredAlerts);
  const filteredGroups = useAppSelector(selectFilteredAlertGroups);
  const selectedAlertId = useAppSelector(selectSelectedAlertId);
  const soundEnabled = useAppSelector(selectSoundEnabled);
  const filters = useAppSelector(selectFilters);
  const criticalCount = useAppSelector(selectCriticalAlertCount);
  const warningCount = useAppSelector(selectWarningAlertCount);

  // View mode state
  const [viewMode, setViewMode] = useState<ViewMode>(() => {
    const stored = storage.get<ViewMode>(VIEW_MODE_STORAGE_KEY);
    return stored === "grouped" ? "grouped" : "flat";
  });

  // Expanded groups state for grouped view
  const [expandedGroups, setExpandedGroups] = useState<Set<string>>(new Set());

  // Persist view mode to localStorage
  useEffect(() => {
    storage.set(VIEW_MODE_STORAGE_KEY, viewMode);
  }, [viewMode]);

  // Toggle group expansion
  const handleToggleGroup = useCallback((groupKey: string) => {
    setExpandedGroups((prev) => {
      const next = new Set(prev);
      if (next.has(groupKey)) {
        next.delete(groupKey);
      } else {
        next.add(groupKey);
      }
      return next;
    });
  }, []);

  // Filter toggles
  const handleSeverityToggle = (severity: "critical" | "warning") => {
    if (!onFilterChange) return;
    const current = filters.severity;
    if (current.includes(severity)) {
      onFilterChange({ severity: current.filter((s) => s !== severity) });
    } else {
      onFilterChange({ severity: [...current, severity] });
    }
  };

  const handleStateToggle = (state: "firing" | "resolved") => {
    if (!onFilterChange) return;
    const current = filters.state;
    if (current.includes(state)) {
      onFilterChange({ state: current.filter((s) => s !== state) });
    } else {
      onFilterChange({ state: [...current, state] });
    }
  };

  // Loading state
  if (isLoading) {
    return (
      <div
        data-testid="alerts-loading"
        className="flex items-center justify-center h-64"
      >
        <Loader2
          className={cn(
            "w-8 h-8 text-primary-9",
            !prefersReducedMotion && "animate-spin",
          )}
        />
      </div>
    );
  }

  return (
    <div className="flex flex-col h-full">
      {/* Header */}
      <div className="flex items-center justify-between p-4 border-b border-neutral-5">
        <div className="flex items-center gap-2">
          <AlertTriangle className="w-5 h-5 text-neutral-10" />
          <h2 className="text-lg font-semibold text-neutral-12">
            Infrastructure Alerts
          </h2>
          {/* Connection status indicator */}
          <div
            data-testid="connection-status"
            className={`w-2 h-2 rounded-full ${getConnectionColor(connectionStatus)}`}
            title={`Connection: ${connectionStatus}`}
          />
        </div>

        <div className="flex items-center gap-2">
          {/* View Mode Toggle */}
          <div
            data-testid="view-mode-toggle"
            className="flex items-center bg-neutral-2 rounded-lg p-0.5"
          >
            <Button
              variant="ghost"
              className={cn(
                "min-h-[44px] min-w-[44px] p-1.5 rounded",
                viewMode === "flat" && "bg-neutral-3",
              )}
              data-testid="view-mode-flat"
              onClick={() => setViewMode("flat")}
              aria-pressed={viewMode === "flat"}
              aria-label="Flat view"
            >
              <List className="w-4 h-4" />
            </Button>
            <Button
              variant="ghost"
              className={cn(
                "min-h-[44px] min-w-[44px] p-1.5 rounded",
                viewMode === "grouped" && "bg-neutral-3",
              )}
              data-testid="view-mode-grouped"
              onClick={() => setViewMode("grouped")}
              aria-pressed={viewMode === "grouped"}
              aria-label="Grouped view"
            >
              <Layers className="w-4 h-4" />
            </Button>
          </div>

          {/* Sound Toggle */}
          <Button
            variant="ghost"
            className="min-h-[44px] min-w-[44px] p-2 rounded-lg"
            data-testid="sound-toggle"
            onClick={onSoundToggle}
            aria-pressed={soundEnabled}
            aria-label={soundEnabled ? "Sound enabled, click to disable" : "Sound disabled, click to enable"}
          >
            {soundEnabled ? (
              <Volume2 className="w-4 h-4" />
            ) : (
              <VolumeX className="w-4 h-4" />
            )}
          </Button>
        </div>
      </div>
      {/* Badge Counts */}
      <div className="flex items-center gap-4 px-4 py-2 bg-neutral-1">
        <div className="flex items-center gap-1.5">
          <div className="w-2 h-2 rounded-full bg-error-9" />
          <span className="text-sm text-neutral-11">
            Critical:
          </span>
          <span
            data-testid="critical-count"
            className="text-sm font-medium text-error-10 dark:text-error-7"
          >
            {criticalCount}
          </span>
        </div>
        <div className="flex items-center gap-1.5">
          <div className="w-2 h-2 rounded-full bg-warning-9" />
          <span className="text-sm text-neutral-11">
            Warning:
          </span>
          <span
            data-testid="warning-count"
            className="text-sm font-medium text-warning-9 dark:text-warning-9"
          >
            {warningCount}
          </span>
        </div>
      </div>
      {/* Filters */}
      <div className="flex flex-wrap gap-2 px-4 py-2 border-b border-neutral-5">
        {/* Severity Filters */}
        <div role="group" aria-label="Severity filter" className="flex gap-2">
          <Button
            variant="primary"
            size="sm"
            className="min-h-8 px-2 py-1 text-xs rounded-full"
            onClick={() => handleSeverityToggle("critical")}
            aria-pressed={filters.severity.includes("critical")}>
            Critical
          </Button>
          <Button
            variant="primary"
            size="sm"
            className="min-h-8 px-2 py-1 text-xs rounded-full"
            onClick={() => handleSeverityToggle("warning")}
            aria-pressed={filters.severity.includes("warning")}>
            Warning
          </Button>
        </div>

        <div className="w-px h-4 bg-neutral-3 self-center" aria-hidden="true" />

        {/* State Filters */}
        <div role="group" aria-label="State filter" className="flex gap-2">
          <Button
            variant="primary"
            size="sm"
            className="min-h-8 px-2 py-1 text-xs rounded-full"
            onClick={() => handleStateToggle("firing")}
            aria-pressed={filters.state.includes("firing")}>
            Firing
          </Button>
          <Button
            variant="primary"
            size="sm"
            className="min-h-8 px-2 py-1 text-xs rounded-full"
            onClick={() => handleStateToggle("resolved")}
            aria-pressed={filters.state.includes("resolved")}>
            Resolved
          </Button>
        </div>
      </div>
      {/* Alert List */}
      <div className="flex-1 overflow-y-auto p-4">
        {viewMode === "grouped" ? (
          // Grouped View
          (// No matches in grouped view - AI-enhanced (Sprint 3 Migration)
          filteredGroups.length === 0 ? (<AIEmptyState
            context="alerts"
            emptyType="no-matches"
            variant="compact"
            enableAI={false}
          />) : (<AlertGroupsPanel
            groups={filteredGroups}
            selectedAlertId={selectedAlertId}
            onSelectAlert={onSelectAlert}
            expandedGroups={expandedGroups}
            onToggleGroup={handleToggleGroup}
          />))
        ) : // Flat View
        filteredAlerts.length === 0 ? (
          // No matches in flat view - AI-enhanced (Sprint 3 Migration)
          (<AIEmptyState
            context="alerts"
            emptyType="no-matches"
            variant="compact"
            enableAI={false}
          />)
        ) : (
          <div className="space-y-2">
            {filteredAlerts.map((alert) => (
              <AlertItem
                key={alert.alertId}
                alert={alert}
                isSelected={selectedAlertId === alert.alertId}
                onClick={() => onSelectAlert(alert.alertId)}
              />
            ))}
          </div>
        )}
      </div>
    </div>
  );
}
