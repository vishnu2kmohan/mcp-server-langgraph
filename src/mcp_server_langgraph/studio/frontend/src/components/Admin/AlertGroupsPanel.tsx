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
  critical: "bg-error-500 text-white",
  warning: "bg-warning-500 text-black",
  info: "bg-primary-500 text-white",
};

const stateStyles: Record<string, string> = {
  firing: "bg-error-100 text-error-800 dark:bg-error-900 dark:text-error-200",
  resolved:
    "bg-success-100 text-success-800 dark:bg-success-900 dark:text-success-200",
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
        className="flex flex-col items-center justify-center p-8 text-gray-500 dark:text-gray-400"
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
            className="border border-gray-200 dark:border-gray-700 rounded-lg overflow-hidden"
            data-testid={`alert-group-${group.groupKey}`}
          >
            {/* Group Header */}
            <div
              role="button"
              tabIndex={0}
              aria-expanded={isExpanded}
              className="flex items-center justify-between p-3 bg-gray-50 dark:bg-gray-800 cursor-pointer hover:bg-gray-100 dark:bg-gray-800 dark:hover:bg-gray-700 transition-colors"
              data-testid={`group-header-${group.groupKey}`}
              onClick={() => onToggleGroup(group.groupKey)}
              onKeyDown={(e) => handleKeyDown(e, group.groupKey)}
            >
              <div className="flex items-center gap-3">
                {/* Expand/Collapse Icon */}
                {isExpanded ? (
                  <ChevronDown
                    className="w-4 h-4 text-gray-500 dark:text-gray-400"
                    data-testid={`collapse-icon-${group.groupKey}`}
                  />
                ) : (
                  <ChevronRight
                    className="w-4 h-4 text-gray-500 dark:text-gray-400"
                    data-testid={`expand-icon-${group.groupKey}`}
                  />
                )}

                {/* Alert Name */}
                <span className="font-medium text-gray-900 dark:text-gray-100">
                  {group.alertName}
                </span>

                {/* Service Name */}
                {group.service && (
                  <span className="text-sm text-gray-500 dark:text-gray-400">
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
                <span className="flex items-center justify-center min-w-[1.5rem] h-6 px-1.5 text-sm font-medium bg-gray-200 dark:bg-gray-700 dark:bg-gray-600 text-gray-700 dark:text-gray-200 rounded-full">
                  {group.count}
                </span>
              </div>
            </div>

            {/* Expanded Alerts */}
            {isExpanded && (
              <div className="divide-y divide-gray-100 dark:divide-gray-700">
                {group.alerts.map((alert: Alert) => (
                  <div
                    key={alert.alertId}
                    role="button"
                    tabIndex={0}
                    className={`p-3 cursor-pointer hover:bg-gray-50 dark:hover:bg-gray-800 transition-colors ${
                      selectedAlertId === alert.alertId
                        ? "border-l-4 border-primary-500 bg-primary-50 dark:bg-primary-900/20"
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
                        <p className="text-sm text-gray-900 dark:text-gray-100 truncate">
                          {alert.message}
                        </p>
                        <p className="text-xs text-gray-500 dark:text-gray-400 mt-1">
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
