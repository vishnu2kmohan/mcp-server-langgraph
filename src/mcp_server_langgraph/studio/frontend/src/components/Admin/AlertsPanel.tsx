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
import {
  AlertTriangle,
  AlertCircle,
  Volume2,
  VolumeX,
  Loader2,
  List,
  Layers,
} from "lucide-react";
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
import type { ConnectionStatus } from "../../hooks/useRealtimeSync";
import { AlertGroupsPanel } from "./AlertGroupsPanel";
import { storage } from "../../utils/storage";

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
  connectionStatus?: ConnectionStatus;
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
      return "bg-red-500";
    case "warning":
      return "bg-yellow-500";
    default:
      return "bg-gray-500";
  }
}

/**
 * Get state badge styling
 */
function getStateStyle(state: Alert["state"]): { bg: string; text: string } {
  switch (state) {
    case "firing":
      return {
        bg: "bg-red-100 dark:bg-red-900/30",
        text: "text-red-700 dark:text-red-400",
      };
    case "resolved":
      return {
        bg: "bg-green-100 dark:bg-green-900/30",
        text: "text-green-700 dark:text-green-400",
      };
    default:
      return {
        bg: "bg-gray-100 dark:bg-gray-800",
        text: "text-gray-700 dark:text-gray-400",
      };
  }
}

/**
 * Get connection status color
 */
function getConnectionColor(status?: ConnectionStatus): string {
  switch (status) {
    case "connected":
      return "bg-green-500";
    case "connecting":
    case "reconnecting":
      return "bg-yellow-500";
    case "disconnected":
    case "error":
      return "bg-red-500";
    default:
      return "bg-gray-500";
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

function AlertItem({ alert, isSelected, onClick }: AlertItemProps) {
  const stateStyle = getStateStyle(alert.state);
  const serviceLabel = alert.labels.service || alert.labels.pod || null;

  return (
    <button
      data-testid={`alert-item-${alert.alert_id}`}
      onClick={onClick}
      className={`w-full text-left p-3 rounded-lg border transition-colors ${
        isSelected
          ? "border-blue-500 bg-blue-50 dark:bg-blue-900/20"
          : "border-gray-200 dark:border-gray-700 hover:bg-gray-50 dark:hover:bg-gray-800"
      }`}
    >
      <div className="flex items-start gap-3">
        {/* Severity Indicator */}
        <div
          data-testid={`severity-badge-${alert.alert_id}`}
          className={`w-2 h-2 mt-2 rounded-full flex-shrink-0 ${getSeverityColor(
            alert.severity,
          )}`}
        />

        <div className="flex-1 min-w-0">
          {/* Alert Name and State */}
          <div className="flex items-center gap-2 mb-1">
            <span className="font-medium text-gray-900 dark:text-white truncate">
              {alert.name}
            </span>
            <span
              data-testid={`state-badge-${alert.alert_id}`}
              className={`text-xs px-2 py-0.5 rounded-full ${stateStyle.bg} ${stateStyle.text}`}
            >
              {alert.state.charAt(0).toUpperCase() + alert.state.slice(1)}
            </span>
          </div>

          {/* Message */}
          <p className="text-sm text-gray-600 dark:text-gray-400 truncate mb-1">
            {alert.message}
          </p>

          {/* Labels and Time */}
          <div className="flex items-center gap-2 text-xs text-gray-500 dark:text-gray-500">
            {serviceLabel && (
              <span className="px-1.5 py-0.5 bg-gray-100 dark:bg-gray-800 rounded">
                {serviceLabel}
              </span>
            )}
            <span data-testid={`alert-time-${alert.alert_id}`}>
              {formatRelativeTime(alert.started_at)}
            </span>
          </div>
        </div>
      </div>
    </button>
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
        <Loader2 className="w-8 h-8 animate-spin text-blue-500" />
      </div>
    );
  }

  return (
    <div className="flex flex-col h-full">
      {/* Header */}
      <div className="flex items-center justify-between p-4 border-b border-gray-200 dark:border-gray-700">
        <div className="flex items-center gap-2">
          <AlertTriangle className="w-5 h-5 text-gray-500" />
          <h2 className="text-lg font-semibold text-gray-900 dark:text-white">
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
            className="flex items-center bg-gray-100 dark:bg-gray-800 rounded-lg p-0.5"
          >
            <button
              data-testid="view-mode-flat"
              onClick={() => setViewMode("flat")}
              aria-pressed={viewMode === "flat"}
              className={`p-1.5 rounded transition-colors ${
                viewMode === "flat"
                  ? "bg-white dark:bg-gray-700 text-blue-600 dark:text-blue-400 shadow-sm"
                  : "text-gray-500 dark:text-gray-400 hover:text-gray-700 dark:hover:text-gray-300"
              }`}
              title="Flat view"
            >
              <List className="w-4 h-4" />
            </button>
            <button
              data-testid="view-mode-grouped"
              onClick={() => setViewMode("grouped")}
              aria-pressed={viewMode === "grouped"}
              className={`p-1.5 rounded transition-colors ${
                viewMode === "grouped"
                  ? "bg-white dark:bg-gray-700 text-blue-600 dark:text-blue-400 shadow-sm"
                  : "text-gray-500 dark:text-gray-400 hover:text-gray-700 dark:hover:text-gray-300"
              }`}
              title="Grouped view"
            >
              <Layers className="w-4 h-4" />
            </button>
          </div>

          {/* Sound Toggle */}
          <button
            data-testid="sound-toggle"
            onClick={onSoundToggle}
            aria-pressed={soundEnabled}
            className={`p-2 rounded-lg transition-colors ${
              soundEnabled
                ? "bg-blue-100 text-blue-600 dark:bg-blue-900/30 dark:text-blue-400"
                : "bg-gray-100 text-gray-500 dark:bg-gray-800 dark:text-gray-400"
            }`}
            title={soundEnabled ? "Sound enabled" : "Sound disabled"}
          >
            {soundEnabled ? (
              <Volume2 className="w-4 h-4" />
            ) : (
              <VolumeX className="w-4 h-4" />
            )}
          </button>
        </div>
      </div>

      {/* Badge Counts */}
      <div className="flex items-center gap-4 px-4 py-2 bg-gray-50 dark:bg-gray-800/50">
        <div className="flex items-center gap-1.5">
          <div className="w-2 h-2 rounded-full bg-red-500" />
          <span className="text-sm text-gray-600 dark:text-gray-400">
            Critical:
          </span>
          <span
            data-testid="critical-count"
            className="text-sm font-medium text-red-600 dark:text-red-400"
          >
            {criticalCount}
          </span>
        </div>
        <div className="flex items-center gap-1.5">
          <div className="w-2 h-2 rounded-full bg-yellow-500" />
          <span className="text-sm text-gray-600 dark:text-gray-400">
            Warning:
          </span>
          <span
            data-testid="warning-count"
            className="text-sm font-medium text-yellow-600 dark:text-yellow-400"
          >
            {warningCount}
          </span>
        </div>
      </div>

      {/* Filters */}
      <div className="flex flex-wrap gap-2 px-4 py-2 border-b border-gray-200 dark:border-gray-700">
        {/* Severity Filters */}
        <button
          onClick={() => handleSeverityToggle("critical")}
          className={`px-2 py-1 text-xs rounded-full transition-colors ${
            filters.severity.includes("critical")
              ? "bg-red-100 text-red-700 dark:bg-red-900/30 dark:text-red-400"
              : "bg-gray-100 text-gray-500 dark:bg-gray-800 dark:text-gray-400"
          }`}
        >
          Critical
        </button>
        <button
          onClick={() => handleSeverityToggle("warning")}
          className={`px-2 py-1 text-xs rounded-full transition-colors ${
            filters.severity.includes("warning")
              ? "bg-yellow-100 text-yellow-700 dark:bg-yellow-900/30 dark:text-yellow-400"
              : "bg-gray-100 text-gray-500 dark:bg-gray-800 dark:text-gray-400"
          }`}
        >
          Warning
        </button>

        <div className="w-px h-4 bg-gray-300 dark:bg-gray-600 self-center" />

        {/* State Filters */}
        <button
          onClick={() => handleStateToggle("firing")}
          className={`px-2 py-1 text-xs rounded-full transition-colors ${
            filters.state.includes("firing")
              ? "bg-red-100 text-red-700 dark:bg-red-900/30 dark:text-red-400"
              : "bg-gray-100 text-gray-500 dark:bg-gray-800 dark:text-gray-400"
          }`}
        >
          Firing
        </button>
        <button
          onClick={() => handleStateToggle("resolved")}
          className={`px-2 py-1 text-xs rounded-full transition-colors ${
            filters.state.includes("resolved")
              ? "bg-green-100 text-green-700 dark:bg-green-900/30 dark:text-green-400"
              : "bg-gray-100 text-gray-500 dark:bg-gray-800 dark:text-gray-400"
          }`}
        >
          Resolved
        </button>
      </div>

      {/* Alert List */}
      <div className="flex-1 overflow-y-auto p-4">
        {viewMode === "grouped" ? (
          // Grouped View
          filteredGroups.length === 0 ? (
            <div className="flex flex-col items-center justify-center h-32 text-gray-500 dark:text-gray-400">
              <AlertCircle className="w-8 h-8 mb-2 opacity-50" />
              <p>No alert groups matching current filters</p>
            </div>
          ) : (
            <AlertGroupsPanel
              groups={filteredGroups}
              selectedAlertId={selectedAlertId}
              onSelectAlert={onSelectAlert}
              expandedGroups={expandedGroups}
              onToggleGroup={handleToggleGroup}
            />
          )
        ) : // Flat View
        filteredAlerts.length === 0 ? (
          <div className="flex flex-col items-center justify-center h-32 text-gray-500 dark:text-gray-400">
            <AlertCircle className="w-8 h-8 mb-2 opacity-50" />
            <p>No alerts matching current filters</p>
          </div>
        ) : (
          <div className="space-y-2">
            {filteredAlerts.map((alert) => (
              <AlertItem
                key={alert.alert_id}
                alert={alert}
                isSelected={selectedAlertId === alert.alert_id}
                onClick={() => onSelectAlert(alert.alert_id)}
              />
            ))}
          </div>
        )}
      </div>
    </div>
  );
}
