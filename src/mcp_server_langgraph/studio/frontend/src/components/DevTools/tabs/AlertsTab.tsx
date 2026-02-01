/**
 * AlertsTab Component
 *
 * Grafana alerts integration for observability.
 * Displays firing, pending, and resolved alerts with filtering.
 *
 * Uses shared OTEL components:
 * - OTELStatusBadge for alert state and severity badges
 * - HumanTimestamp for relative time display
 * - useLGTMIntegration for Grafana alert links
 *
 * Design System Compliance:
 * - Uses CVA for toolbar button variants
 * - Uses Motion.dev for button press feedback
 * - Implements useReducedMotion() for accessibility
 * - Uses semantic colors per STYLE.md
 */
import React, { useState, useMemo, useCallback } from "react";
import { motion, useReducedMotion, AnimatePresence } from "motion/react";
import { cva } from "class-variance-authority";
import { ExternalLink, ChevronDown } from "lucide-react";
import {
  buttonVariants as motionButtonVariants,
  dropdownVariants,
} from "@/design-system/micro-interactions";
import { useTimelineContext } from "../context/DevToolsTimelineProvider";
import { cn } from "../../../utils/cn";
import { STATUS_TEXT_COLORS } from "../utils/devToolsColors";

// Shared OTEL components
import { HumanTimestamp, OTELStatusBadge } from "../components";
import { useLGTMIntegration } from "../hooks/useLGTMIntegration";

import { Button } from "@/components/UI";

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

export type ConnectionStatus =
  | "connected"
  | "connecting"
  | "reconnecting"
  | "disconnected"
  | "error";

export interface AlertsTabProps {
  alerts?: Alert[];
  /** External alerts from WebSocket for real-time updates */
  externalAlerts?: Alert[];
  /** Callback to clear external (WebSocket) alerts */
  onClearExternal?: () => void;
  /** WebSocket connection status for indicator display */
  connectionStatus?: ConnectionStatus;
  isLoading?: boolean;
  error?: string;
  onSilence?: (alertId: string) => void;
  onAcknowledge?: (alertId: string) => void;
  className?: string;
}

// =============================================================================
// CVA Variants
// =============================================================================

/**
 * Filter dropdown button variants
 */
// eslint-disable-next-line react-refresh/only-export-components
export const filterButtonVariants = cva(
  "px-3 py-1.5 text-sm rounded-md flex items-center gap-1 transition-colors",
  {
    variants: {
      variant: {
        default: "bg-neutral-2 hover:bg-neutral-3 text-neutral-11",
        active: "bg-primary-3 dark:bg-primary-4 text-primary-11",
      },
    },
    defaultVariants: {
      variant: "default",
    },
  },
);

/**
 * Filter dropdown option variants
 */
// eslint-disable-next-line react-refresh/only-export-components
export const filterOptionVariants = cva(
  "w-full text-left px-3 py-2 text-sm transition-colors",
  {
    variants: {
      selected: {
        true: "bg-primary-1 dark:bg-primary-12",
        false: "hover:bg-neutral-2",
      },
    },
    defaultVariants: {
      selected: false,
    },
  },
);

// =============================================================================
// Sub-Components
// =============================================================================

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
  const prefersReducedMotion = useReducedMotion();
  const [isOpen, setIsOpen] = useState(false);

  return (
    <div className="relative">
      <motion.button
        type="button"
        className={filterButtonVariants({
          variant: value ? "active" : "default",
        })}
        onClick={() => setIsOpen(!isOpen)}
        aria-label={label}
        aria-expanded={isOpen}
        aria-haspopup="listbox"
        variants={prefersReducedMotion ? undefined : motionButtonVariants}
        initial="rest"
        whileHover="hover"
        whileTap="pressed"
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
      </motion.button>
      <AnimatePresence>
        {isOpen && (
          <>
            <div
              className="fixed inset-0 z-10"
              onClick={() => setIsOpen(false)}
            />
            <motion.div
              className="absolute top-full left-0 mt-1 bg-neutral-1 border border-neutral-5 rounded-md shadow-lg z-dropdown min-w-32"
              role="listbox"
              variants={prefersReducedMotion ? undefined : dropdownVariants}
              initial="hidden"
              animate="visible"
              exit="hidden"
            >
              <Button
                variant="ghost"
                type="button"
                role="option"
                aria-selected={!value}
                onClick={() => {
                  onChange("");
                  setIsOpen(false);
                }}
                className={filterOptionVariants({ selected: !value })}
                aria-label="All"
              >
                All
              </Button>
              {options.map((option) => (
                <Button
                  variant="ghost"
                  key={option}
                  type="button"
                  role="option"
                  aria-selected={value === option}
                  onClick={() => {
                    onChange(option);
                    setIsOpen(false);
                  }}
                  className={filterOptionVariants({
                    selected: value === option,
                  })}
                  aria-label={option}
                >
                  {option}
                </Button>
              ))}
            </motion.div>
          </>
        )}
      </AnimatePresence>
    </div>
  );
}

interface AlertCardProps {
  alert: Alert;
  onSilence?: (alertId: string) => void;
}

function AlertCard({ alert, onSilence }: AlertCardProps): React.ReactElement {
  const [showDetails, setShowDetails] = useState(false);
  const lgtm = useLGTMIntegration();

  const handleOpenGrafana = useCallback(() => {
    // Prefer LGTM integration, fallback to generatorUrl
    const url = lgtm.getAlertUrl(alert.id) ?? alert.generatorUrl;
    if (url) {
      window.open(url, "_blank");
    }
  }, [lgtm, alert.id, alert.generatorUrl]);

  const handleSilence = useCallback(() => {
    onSilence?.(alert.id);
  }, [alert.id, onSilence]);

  const canOpenInGrafana = lgtm.canOpenInGrafana || !!alert.generatorUrl;

  return (
    <div
      data-alert={alert.id}
      data-state={alert.state}
      className={cn(
        "border rounded-lg p-4",
        alert.state === "firing"
          ? "border-error-9 bg-error-1 dark:border-error-11 dark:bg-error-12"
          : alert.state === "pending"
            ? "border-warning-6 bg-warning-3 dark:border-warning-11 dark:bg-warning-12"
            : "border-neutral-5 bg-neutral-1",
      )}
    >
      {/* Header */}
      <div className="flex items-start justify-between gap-4">
        <div className="flex items-center gap-2 flex-wrap">
          <OTELStatusBadge type="alert-state" value={alert.state} />
          <span className="font-medium text-neutral-12">{alert.name}</span>
          <OTELStatusBadge type="alert-severity" value={alert.severity} />
          <span className="text-sm text-neutral-10">{alert.service}</span>
          <HumanTimestamp timestamp={alert.startedAt} format="relative" />
        </div>
      </div>
      {/* Message */}
      <p className="mt-2 text-sm text-neutral-11">{alert.message}</p>
      {/* Actions */}
      <div className="mt-3 flex items-center gap-2 flex-wrap">
        {canOpenInGrafana && (
          <Button
            variant="ghost"
            size="sm"
            className="px-3 py-1 text-sm bg-grafana-9 text-neutral-12 rounded hover:bg-grafana-10 flex gap-1"
            onClick={handleOpenGrafana}
            aria-label="View in Grafana"
          >
            <ExternalLink className="w-3 h-3" aria-hidden="true" />
            View in Grafana
          </Button>
        )}
        {alert.state === "firing" && onSilence && (
          <Button
            variant="secondary"
            size="sm"
            className="px-3 py-1 text-sm bg-neutral-5 text-neutral-12 rounded hover:bg-neutral-5"
            onClick={handleSilence}
            aria-label="Silence"
          >
            Silence
          </Button>
        )}
        <Button
          variant="secondary"
          size="sm"
          className="px-3 py-1 text-sm bg-neutral-2 text-neutral-11 rounded hover:bg-neutral-3 flex gap-1"
          onClick={() => setShowDetails(!showDetails)}
          aria-label="Details"
        >
          Details
          <ChevronDown
            className={cn(
              "w-3 h-3 transition-transform duration-fast",
              showDetails && "rotate-180",
            )}
            aria-hidden="true"
          />
        </Button>
      </div>
      {/* Details */}
      {showDetails && (
        <div className="mt-3 pt-3 border-t border-neutral-5">
          <dl className="grid grid-cols-2 gap-2 text-sm">
            <div>
              <dt className="text-neutral-10">Alert ID</dt>
              <dd className="font-mono text-neutral-12">{alert.id}</dd>
            </div>
            <div>
              <dt className="text-neutral-10">Started</dt>
              <dd className="text-neutral-12">
                <HumanTimestamp timestamp={alert.startedAt} format="datetime" />
              </dd>
            </div>
            {alert.resolvedAt && (
              <div>
                <dt className="text-neutral-10">Resolved</dt>
                <dd className="text-neutral-12">
                  <HumanTimestamp
                    timestamp={alert.resolvedAt}
                    format="datetime"
                  />
                </dd>
              </div>
            )}
            {alert.labels && Object.keys(alert.labels).length > 0 && (
              <div className="col-span-2">
                <dt className="text-neutral-10">Labels</dt>
                <dd className="flex flex-wrap gap-1 mt-1">
                  {Object.entries(alert.labels).map(([key, value]) => (
                    <span
                      key={key}
                      className="px-2 py-0.5 bg-neutral-2 text-neutral-11 text-xs rounded"
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
  externalAlerts,
  onClearExternal,
  connectionStatus,
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

  // Merge alerts from REST API and WebSocket, deduplicating by ID
  // External (WebSocket) alerts take precedence for duplicates (newer state)
  const mergedAlerts = useMemo(() => {
    const allAlerts = [...alerts];
    const existingIds = new Set(allAlerts.map((a) => a.id));

    if (externalAlerts) {
      for (const external of externalAlerts) {
        if (!existingIds.has(external.id)) {
          allAlerts.push(external);
        } else {
          // Update existing with newer data from WebSocket
          const idx = allAlerts.findIndex((a) => a.id === external.id);
          if (idx >= 0) {
            allAlerts[idx] = external;
          }
        }
      }
    }

    // Sort by startedAt descending (newest first)
    return allAlerts.sort(
      (a, b) =>
        new Date(b.startedAt).getTime() - new Date(a.startedAt).getTime(),
    );
  }, [alerts, externalAlerts]);

  // Get unique services for filter dropdown (from merged alerts)
  const services = useMemo(() => {
    const uniqueServices = new Set(mergedAlerts.map((a) => a.service));
    return Array.from(uniqueServices).sort();
  }, [mergedAlerts]);

  // Filter alerts
  const filteredAlerts = useMemo(() => {
    let result = mergedAlerts;

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
    mergedAlerts,
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
                className="h-8 w-24 bg-neutral-3 rounded animate-pulse"
              />
            ))}
          </div>
          {/* Alert skeletons */}
          {[1, 2, 3].map((i) => (
            <div
              key={i}
              className="h-32 bg-neutral-3 rounded-lg animate-pulse"
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
        <div className={cn(STATUS_TEXT_COLORS.error, "mb-4")}>
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
        <p className={STATUS_TEXT_COLORS.error}>{error}</p>
      </div>
    );
  }

  return (
    <div
      data-testid="alerts-tab"
      className={cn("flex flex-col h-full overflow-hidden", className)}
    >
      {/* Header */}
      <div className="flex items-center gap-2 p-3 border-b border-neutral-5">
        {/* Connection status indicator */}
        {connectionStatus && (
          <span
            className={cn(
              "w-2 h-2 rounded-full",
              connectionStatus === "connected" && "bg-success-9",
              connectionStatus === "connecting" && "bg-warning-9 animate-pulse",
              connectionStatus === "reconnecting" &&
                "bg-warning-9 animate-pulse",
              connectionStatus === "disconnected" && "bg-neutral-4",
              connectionStatus === "error" && "bg-error-9",
            )}
            title={`WebSocket: ${connectionStatus}`}
          />
        )}
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
          <Button
            variant="danger"
            size="sm"
            className="px-2 py-1 text-sm text-primary-10 dark:text-primary-7 hover:underline"
            onClick={() => {
              setStateFilter("");
              setSeverityFilter("");
              setServiceFilter("");
            }}
          >
            Clear filters
          </Button>
        )}

        {/* Clear external alerts button */}
        {externalAlerts && externalAlerts.length > 0 && onClearExternal && (
          <Button
            size="sm"
            variant="secondary"
            className="ml-auto px-2 py-1 text-sm"
            onClick={onClearExternal}
            aria-label="Clear real-time alerts"
          >
            Clear live ({externalAlerts.length})
          </Button>
        )}
      </div>
      {/* Content */}
      <div className="flex-1 overflow-auto p-4">
        {filteredAlerts.length === 0 ? (
          <div className="flex flex-col items-center justify-center h-full text-center">
            <svg
              className="w-12 h-12 text-neutral-9 mb-4"
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
            <p className="text-neutral-10">No alerts</p>
            <p className="text-sm text-neutral-9 mt-1">
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
