/**
 * AlertsTab Component
 *
 * Grafana alerts integration for observability.
 * Displays firing, pending, and resolved alerts with filtering.
 */
import React, { useState, useMemo, useCallback } from "react";
import { useTimelineContext } from "../context/DevToolsTimelineProvider";
import { cn } from "../../../utils/cn";

// =============================================================================
// Types
// =============================================================================

export type AlertState = "firing" | "pending" | "resolved" | "silenced";
export type AlertSeverity = "critical" | "warning" | "info";

export interface Alert {
  id: string;
  name: string;
  state: AlertState;
  severity: AlertSeverity;
  service: string;
  message: string;
  startedAt: string;
  resolvedAt?: string;
  generatorUrl?: string;
  labels?: Record<string, string>;
}

export interface AlertsTabProps {
  alerts?: Alert[];
  isLoading?: boolean;
  error?: string;
  onSilence?: (alertId: string) => void;
  onAcknowledge?: (alertId: string) => void;
  className?: string;
}

// =============================================================================
// Utility Functions
// =============================================================================

function formatRelativeTime(dateString: string): string {
  const date = new Date(dateString);
  const now = new Date();
  const diffMs = now.getTime() - date.getTime();
  const diffMins = Math.floor(diffMs / (1000 * 60));
  const diffHours = Math.floor(diffMs / (1000 * 60 * 60));
  const diffDays = Math.floor(diffMs / (1000 * 60 * 60 * 24));

  if (diffMins < 1) return "just now";
  if (diffMins < 60) return `${diffMins}m ago`;
  if (diffHours < 24) return `${diffHours}h ago`;
  return `${diffDays}d ago`;
}

// =============================================================================
// Sub-Components
// =============================================================================

interface StateBadgeProps {
  state: AlertState;
}

function StateBadge({ state }: StateBadgeProps): React.ReactElement {
  const config = {
    firing: { color: "bg-red-500 text-white", icon: "\u{1F534}" }, // 🔴
    pending: { color: "bg-yellow-500 text-black", icon: "\u{1F7E1}" }, // 🟡
    resolved: { color: "bg-green-500 text-white", icon: "\u{1F7E2}" }, // 🟢
    silenced: { color: "bg-gray-500 text-white", icon: "\u{26D4}" }, // ⛔
  }[state];

  return (
    <span
      className={cn(
        "inline-flex items-center gap-1 px-2 py-0.5 text-xs font-medium rounded-full uppercase",
        config.color,
      )}
    >
      {state}
    </span>
  );
}

interface SeverityBadgeProps {
  severity: AlertSeverity;
}

function SeverityBadge({ severity }: SeverityBadgeProps): React.ReactElement {
  const config = {
    critical: "bg-red-100 text-red-800 dark:bg-red-900 dark:text-red-200",
    warning:
      "bg-yellow-100 text-yellow-800 dark:bg-yellow-900 dark:text-yellow-200",
    info: "bg-blue-100 text-blue-800 dark:bg-blue-900 dark:text-blue-200",
  }[severity];

  return (
    <span
      className={cn(
        "inline-flex items-center px-2 py-0.5 text-xs font-medium rounded",
        config,
      )}
    >
      {severity}
    </span>
  );
}

interface FilterDropdownProps {
  label: string;
  options: string[];
  value: string;
  onChange: (value: string) => void;
}

function FilterDropdown({
  label,
  options,
  value,
  onChange,
}: FilterDropdownProps): React.ReactElement {
  const [isOpen, setIsOpen] = useState(false);

  return (
    <div className="relative">
      <button
        onClick={() => setIsOpen(!isOpen)}
        className="px-3 py-1.5 text-sm bg-gray-100 dark:bg-gray-800 rounded-md hover:bg-gray-200 dark:hover:bg-gray-700 flex items-center gap-1"
        aria-label={label}
      >
        {label}: {value || "All"}
        <svg
          className="w-4 h-4"
          fill="none"
          viewBox="0 0 24 24"
          stroke="currentColor"
        >
          <path
            strokeLinecap="round"
            strokeLinejoin="round"
            strokeWidth={2}
            d="M19 9l-7 7-7-7"
          />
        </svg>
      </button>
      {isOpen && (
        <>
          <div
            className="fixed inset-0 z-10"
            onClick={() => setIsOpen(false)}
          />
          <div className="absolute top-full left-0 mt-1 bg-white dark:bg-gray-800 border border-gray-200 dark:border-gray-700 rounded-md shadow-lg z-20 min-w-[120px]">
            <button
              role="option"
              onClick={() => {
                onChange("");
                setIsOpen(false);
              }}
              className={cn(
                "w-full text-left px-3 py-2 text-sm hover:bg-gray-100 dark:hover:bg-gray-700",
                !value && "bg-blue-50 dark:bg-blue-900",
              )}
              aria-label="All"
            >
              All
            </button>
            {options.map((option) => (
              <button
                key={option}
                role="option"
                onClick={() => {
                  onChange(option);
                  setIsOpen(false);
                }}
                className={cn(
                  "w-full text-left px-3 py-2 text-sm hover:bg-gray-100 dark:hover:bg-gray-700",
                  value === option && "bg-blue-50 dark:bg-blue-900",
                )}
                aria-label={option}
              >
                {option}
              </button>
            ))}
          </div>
        </>
      )}
    </div>
  );
}

interface AlertCardProps {
  alert: Alert;
  onSilence?: (alertId: string) => void;
}

function AlertCard({ alert, onSilence }: AlertCardProps): React.ReactElement {
  const [showDetails, setShowDetails] = useState(false);

  const handleOpenGrafana = useCallback(() => {
    if (alert.generatorUrl) {
      window.open(alert.generatorUrl, "_blank");
    }
  }, [alert.generatorUrl]);

  const handleSilence = useCallback(() => {
    onSilence?.(alert.id);
  }, [alert.id, onSilence]);

  return (
    <div
      data-alert={alert.id}
      data-state={alert.state}
      className={cn(
        "border rounded-lg p-4",
        alert.state === "firing"
          ? "border-red-300 bg-red-50 dark:border-red-800 dark:bg-red-950"
          : alert.state === "pending"
            ? "border-yellow-300 bg-yellow-50 dark:border-yellow-800 dark:bg-yellow-950"
            : "border-gray-200 bg-white dark:border-gray-700 dark:bg-gray-800",
      )}
    >
      {/* Header */}
      <div className="flex items-start justify-between gap-4">
        <div className="flex items-center gap-2 flex-wrap">
          <StateBadge state={alert.state} />
          <span className="font-medium text-gray-900 dark:text-white">
            {alert.name}
          </span>
          <SeverityBadge severity={alert.severity} />
          <span className="text-sm text-gray-500 dark:text-gray-400">
            {alert.service}
          </span>
          <span className="text-sm text-gray-400 dark:text-gray-500">
            {formatRelativeTime(alert.startedAt)}
          </span>
        </div>
      </div>

      {/* Message */}
      <p className="mt-2 text-sm text-gray-700 dark:text-gray-300">
        {alert.message}
      </p>

      {/* Actions */}
      <div className="mt-3 flex items-center gap-2 flex-wrap">
        {alert.generatorUrl && (
          <button
            onClick={handleOpenGrafana}
            className="px-3 py-1 text-sm bg-orange-500 text-white rounded hover:bg-orange-600 transition-colors flex items-center gap-1"
            aria-label="View in Grafana"
          >
            <svg
              className="w-3 h-3"
              fill="none"
              viewBox="0 0 24 24"
              stroke="currentColor"
            >
              <path
                strokeLinecap="round"
                strokeLinejoin="round"
                strokeWidth={2}
                d="M10 6H6a2 2 0 00-2 2v10a2 2 0 002 2h10a2 2 0 002-2v-4M14 4h6m0 0v6m0-6L10 14"
              />
            </svg>
            View in Grafana
          </button>
        )}
        {alert.state === "firing" && onSilence && (
          <button
            onClick={handleSilence}
            className="px-3 py-1 text-sm bg-gray-500 text-white rounded hover:bg-gray-600 transition-colors"
            aria-label="Silence"
          >
            Silence
          </button>
        )}
        <button
          onClick={() => setShowDetails(!showDetails)}
          className="px-3 py-1 text-sm bg-gray-100 dark:bg-gray-700 text-gray-700 dark:text-gray-300 rounded hover:bg-gray-200 dark:hover:bg-gray-600 transition-colors flex items-center gap-1"
          aria-label="Details"
        >
          Details
          <svg
            className={cn(
              "w-3 h-3 transition-transform",
              showDetails && "rotate-180",
            )}
            fill="none"
            viewBox="0 0 24 24"
            stroke="currentColor"
          >
            <path
              strokeLinecap="round"
              strokeLinejoin="round"
              strokeWidth={2}
              d="M19 9l-7 7-7-7"
            />
          </svg>
        </button>
      </div>

      {/* Details */}
      {showDetails && (
        <div className="mt-3 pt-3 border-t border-gray-200 dark:border-gray-700">
          <dl className="grid grid-cols-2 gap-2 text-sm">
            <div>
              <dt className="text-gray-500 dark:text-gray-400">Alert ID</dt>
              <dd className="font-mono text-gray-900 dark:text-white">
                {alert.id}
              </dd>
            </div>
            <div>
              <dt className="text-gray-500 dark:text-gray-400">Started</dt>
              <dd className="text-gray-900 dark:text-white">
                {new Date(alert.startedAt).toLocaleString()}
              </dd>
            </div>
            {alert.resolvedAt && (
              <div>
                <dt className="text-gray-500 dark:text-gray-400">Resolved</dt>
                <dd className="text-gray-900 dark:text-white">
                  {new Date(alert.resolvedAt).toLocaleString()}
                </dd>
              </div>
            )}
            {alert.labels && Object.keys(alert.labels).length > 0 && (
              <div className="col-span-2">
                <dt className="text-gray-500 dark:text-gray-400">Labels</dt>
                <dd className="flex flex-wrap gap-1 mt-1">
                  {Object.entries(alert.labels).map(([key, value]) => (
                    <span
                      key={key}
                      className="px-2 py-0.5 bg-gray-100 dark:bg-gray-700 text-gray-700 dark:text-gray-300 text-xs rounded"
                    >
                      {key}={value}
                    </span>
                  ))}
                </dd>
              </div>
            )}
          </dl>
        </div>
      )}
    </div>
  );
}

// =============================================================================
// Main Component
// =============================================================================

export function AlertsTab({
  alerts = [],
  isLoading = false,
  error,
  onSilence,
  className,
}: AlertsTabProps): React.ReactElement {
  const timeline = useTimelineContext();

  // Filter state
  const [stateFilter, setStateFilter] = useState("");
  const [severityFilter, setSeverityFilter] = useState("");
  const [serviceFilter, setServiceFilter] = useState("");

  // Get unique services for filter dropdown
  const services = useMemo(() => {
    const uniqueServices = new Set(alerts.map((a) => a.service));
    return Array.from(uniqueServices).sort();
  }, [alerts]);

  // Filter alerts
  const filteredAlerts = useMemo(() => {
    let result = alerts;

    // Filter by timeline time window
    if (timeline?.timeWindow) {
      result = result.filter((alert) => {
        const startTime = new Date(alert.startedAt).getTime();
        return (
          startTime >= timeline.timeWindow!.start &&
          startTime <= timeline.timeWindow!.end
        );
      });
    }

    // Filter by state
    if (stateFilter) {
      result = result.filter((a) => a.state === stateFilter);
    }

    // Filter by severity
    if (severityFilter) {
      result = result.filter((a) => a.severity === severityFilter);
    }

    // Filter by service
    if (serviceFilter) {
      result = result.filter((a) => a.service === serviceFilter);
    }

    return result;
  }, [
    alerts,
    timeline?.timeWindow,
    stateFilter,
    severityFilter,
    serviceFilter,
  ]);

  // Loading state
  if (isLoading) {
    return (
      <div
        data-testid="alerts-tab"
        className={cn("flex flex-col h-full", className)}
      >
        <div data-testid="alerts-loading" className="p-4 space-y-4">
          {/* Header skeleton */}
          <div className="flex items-center gap-2">
            {[1, 2, 3].map((i) => (
              <div
                key={i}
                className="h-8 w-24 bg-gray-200 dark:bg-gray-700 rounded animate-pulse"
              />
            ))}
          </div>
          {/* Alert skeletons */}
          {[1, 2, 3].map((i) => (
            <div
              key={i}
              className="h-32 bg-gray-200 dark:bg-gray-700 rounded-lg animate-pulse"
            />
          ))}
        </div>
      </div>
    );
  }

  // Error state
  if (error) {
    return (
      <div
        data-testid="alerts-tab"
        className={cn(
          "flex flex-col items-center justify-center h-full p-8 text-center",
          className,
        )}
      >
        <div className="text-red-500 mb-4">
          <svg
            className="w-12 h-12 mx-auto"
            fill="none"
            viewBox="0 0 24 24"
            stroke="currentColor"
          >
            <path
              strokeLinecap="round"
              strokeLinejoin="round"
              strokeWidth={2}
              d="M12 9v2m0 4h.01m-6.938 4h13.856c1.54 0 2.502-1.667 1.732-3L13.732 4c-.77-1.333-2.694-1.333-3.464 0L3.34 16c-.77 1.333.192 3 1.732 3z"
            />
          </svg>
        </div>
        <p className="text-red-600 dark:text-red-400">{error}</p>
      </div>
    );
  }

  return (
    <div
      data-testid="alerts-tab"
      className={cn("flex flex-col h-full overflow-hidden", className)}
    >
      {/* Header */}
      <div className="flex items-center gap-2 p-3 border-b border-gray-200 dark:border-gray-700">
        <FilterDropdown
          label="State"
          options={["firing", "pending", "resolved", "silenced"]}
          value={stateFilter}
          onChange={setStateFilter}
        />
        <FilterDropdown
          label="Severity"
          options={["critical", "warning", "info"]}
          value={severityFilter}
          onChange={setSeverityFilter}
        />
        <FilterDropdown
          label="Service"
          options={services}
          value={serviceFilter}
          onChange={setServiceFilter}
        />

        {/* Active filter count */}
        {(stateFilter || severityFilter || serviceFilter) && (
          <button
            onClick={() => {
              setStateFilter("");
              setSeverityFilter("");
              setServiceFilter("");
            }}
            className="px-2 py-1 text-sm text-blue-600 dark:text-blue-400 hover:underline"
          >
            Clear filters
          </button>
        )}
      </div>

      {/* Content */}
      <div className="flex-1 overflow-auto p-4">
        {filteredAlerts.length === 0 ? (
          <div className="flex flex-col items-center justify-center h-full text-center">
            <svg
              className="w-12 h-12 text-gray-400 mb-4"
              fill="none"
              viewBox="0 0 24 24"
              stroke="currentColor"
            >
              <path
                strokeLinecap="round"
                strokeLinejoin="round"
                strokeWidth={2}
                d="M15 17h5l-1.405-1.405A2.032 2.032 0 0118 14.158V11a6.002 6.002 0 00-4-5.659V5a2 2 0 10-4 0v.341C7.67 6.165 6 8.388 6 11v3.159c0 .538-.214 1.055-.595 1.436L4 17h5m6 0v1a3 3 0 11-6 0v-1m6 0H9"
              />
            </svg>
            <p className="text-gray-500 dark:text-gray-400">No alerts</p>
            <p className="text-sm text-gray-400 dark:text-gray-500 mt-1">
              {stateFilter || severityFilter || serviceFilter
                ? "No alerts match the current filters"
                : "All systems are operating normally"}
            </p>
          </div>
        ) : (
          <div className="space-y-4">
            {filteredAlerts.map((alert) => (
              <AlertCard key={alert.id} alert={alert} onSilence={onSilence} />
            ))}
          </div>
        )}
      </div>
    </div>
  );
}

export default AlertsTab;
