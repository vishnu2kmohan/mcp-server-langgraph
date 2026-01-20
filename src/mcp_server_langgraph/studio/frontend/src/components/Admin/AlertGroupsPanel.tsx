/**
 * AlertGroupsPanel Component
 *
 * Displays grouped alerts in collapsible panels to reduce noise.
 *
 * Features:
 * - Collapsible alert groups by service + alertname
 * - Group header: service name, alert count, severity badge
 * - Expand to show individual alerts
 * - Keyboard navigation (Enter/Space to toggle)
 * - Accessibility: aria-expanded, role="button"
 *
 * Reference: ADR-0026 - Comprehensive Client Resilience Patterns
 */

import { ChevronDown, ChevronRight } from "lucide-react";
import type { AlertGroup, Alert } from "../../store/slices/alertSlice";

// =============================================================================
// Types
// =============================================================================

export interface AlertGroupsPanelProps {
  groups: AlertGroup[];
  selectedAlertId: string | null;
  onSelectAlert: (alertId: string) => void;
  expandedGroups: Set<string>;
  onToggleGroup: (groupKey: string) => void;
}

// =============================================================================
// Severity Badge Styles
// =============================================================================

const severityStyles: Record<string, string> = {
  critical: "bg-error-9 text-neutral-12",
  warning: "bg-warning-9 text-neutral-1",
  info: "bg-primary-9 text-neutral-12",
};

const stateStyles: Record<string, string> = {
  firing: "bg-error-3 text-error-11 dark:bg-error-12 dark:text-error-4",
  resolved:
    "bg-success-3 text-success-11 dark:bg-success-12 dark:text-success-4",
};

// =============================================================================
// Component
// =============================================================================

export function AlertGroupsPanel({
  groups,
  selectedAlertId,
  onSelectAlert,
  expandedGroups,
  onToggleGroup,
}: AlertGroupsPanelProps) {
  // Handle keyboard navigation for group headers
  const handleKeyDown = (event: React.KeyboardEvent, groupKey: string) => {
    if (event.key === "Enter" || event.key === " ") {
      event.preventDefault();
      onToggleGroup(groupKey);
    }
  };

  // Empty state
  if (groups.length === 0) {
    return (
      <div
        className="flex flex-col items-center justify-center p-8 text-neutral-10"
        data-testid="alert-groups-empty"
      >
        <p>No alert groups</p>
      </div>
    );
  }

  return (
    <div className="space-y-2" data-testid="alert-groups-panel">
      {groups.map((group) => {
        const isExpanded = expandedGroups.has(group.groupKey);

        return (
          <div
            key={group.groupKey}
            className="border border-neutral-5 rounded-lg overflow-hidden"
            data-testid={`alert-group-${group.groupKey}`}
          >
            {/* Group Header */}
            <div
              role="button"
              tabIndex={0}
              aria-expanded={isExpanded}
              className="flex items-center justify-between p-3 bg-neutral-1 cursor-pointer hover:bg-neutral-2 transition-colors"
              data-testid={`group-header-${group.groupKey}`}
              onClick={() => onToggleGroup(group.groupKey)}
              onKeyDown={(e) => handleKeyDown(e, group.groupKey)}
            >
              <div className="flex items-center gap-3">
                {/* Expand/Collapse Icon */}
                {isExpanded ? (
                  <ChevronDown
                    className="w-4 h-4 text-neutral-10"
                    data-testid={`collapse-icon-${group.groupKey}`}
                  />
                ) : (
                  <ChevronRight
                    className="w-4 h-4 text-neutral-10"
                    data-testid={`expand-icon-${group.groupKey}`}
                  />
                )}

                {/* Alert Name */}
                <span className="font-medium text-neutral-12">
                  {group.alertName}
                </span>

                {/* Service Name */}
                {group.service && (
                  <span className="text-sm text-neutral-10">
                    {group.service}
                  </span>
                )}
              </div>

              <div className="flex items-center gap-2">
                {/* State Badge */}
                <span
                  className={`px-2 py-0.5 text-xs font-medium rounded-full capitalize ${stateStyles[group.state] || ""}`}
                  data-testid={`state-badge-${group.groupKey}`}
                >
                  {group.state === "firing" ? "Firing" : "Resolved"}
                </span>

                {/* Severity Badge */}
                <span
                  className={`px-2 py-0.5 text-xs font-medium rounded-full ${severityStyles[group.severity] || ""}`}
                  data-testid={`severity-badge-${group.groupKey}`}
                >
                  {group.severity}
                </span>

                {/* Alert Count */}
                <span className="flex items-center justify-center min-w-[1.5rem] h-6 px-1.5 text-sm font-medium bg-neutral-3 text-neutral-11 rounded-full">
                  {group.count}
                </span>
              </div>
            </div>

            {/* Expanded Alerts */}
            {isExpanded && (
              <div className="divide-y divide-neutral-5">
                {group.alerts.map((alert: Alert) => (
                  <div
                    key={alert.alertId}
                    role="button"
                    tabIndex={0}
                    className={`p-3 cursor-pointer hover:bg-neutral-1 transition-colors ${
                      selectedAlertId === alert.alertId
                        ? "border-l-4 border-primary-9 bg-primary-1 dark:bg-primary-a3"
                        : "border-l-4 border-transparent"
                    }`}
                    data-testid={`alert-item-${alert.alertId}`}
                    onClick={() => onSelectAlert(alert.alertId)}
                    onKeyDown={(e) => {
                      if (e.key === "Enter" || e.key === " ") {
                        e.preventDefault();
                        onSelectAlert(alert.alertId);
                      }
                    }}
                  >
                    <div className="flex items-start justify-between">
                      <div className="flex-1 min-w-0">
                        <p className="text-sm text-neutral-12 truncate">
                          {alert.message}
                        </p>
                        <p className="text-xs text-neutral-10 mt-1">
                          Started: {new Date(alert.startedAt).toLocaleString()}
                        </p>
                      </div>
                    </div>
                  </div>
                ))}
              </div>
            )}
          </div>
        );
      })}
    </div>
  );
}

export default AlertGroupsPanel;
