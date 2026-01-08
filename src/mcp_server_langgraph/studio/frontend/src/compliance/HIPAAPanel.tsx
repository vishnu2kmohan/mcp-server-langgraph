/**
 * HIPAAPanel Component
 *
 * Phase 5: Compliance Dashboards
 * Displays HIPAA compliance status.
 *
 * Features:
 * - Administrative, Physical, Technical safeguards
 * - PHI access tracking
 * - Compliance percentage summary
 */

import {
  HeartPulse,
  CheckCircle,
  AlertCircle,
  XCircle,
  Loader2,
  Eye,
} from "lucide-react";
import { cn } from "../utils/cn";

// =============================================================================
// Types
// =============================================================================

export type ControlStatus =
  | "compliant"
  | "partial"
  | "non-compliant"
  | "not-applicable";
export type HIPAACategory = "administrative" | "physical" | "technical";

export interface HIPAAControl {
  id: string;
  name: string;
  category: HIPAACategory;
  status: ControlStatus;
  lastAssessed: string;
  phiAccessCount?: number;
}

export interface HIPAAPanelProps {
  controls: HIPAAControl[];
  isLoading?: boolean;
  className?: string;
}

// =============================================================================
// Utility
// =============================================================================

function getStatusIcon(status: ControlStatus) {
  switch (status) {
    case "compliant":
      return <CheckCircle size={14} className="text-success-500" />;
    case "partial":
      return <AlertCircle size={14} className="text-warning-500" />;
    case "non-compliant":
      return <XCircle size={14} className="text-error-500" />;
    default:
      return (
        <AlertCircle size={14} className="text-gray-400 dark:text-gray-400" />
      );
  }
}

function getStatusColor(status: ControlStatus): string {
  switch (status) {
    case "compliant":
      return "text-success-600 dark:text-success-400";
    case "partial":
      return "text-warning-600 dark:text-warning-400";
    case "non-compliant":
      return "text-error-600 dark:text-error-400";
    default:
      return "text-gray-500 dark:text-gray-400";
  }
}

function getCategoryColor(category: HIPAACategory): string {
  switch (category) {
    case "administrative":
      return "bg-insight-100 text-insight-700 dark:bg-insight-900/30 dark:text-insight-400";
    case "physical":
      return "bg-grafana-100 text-grafana-700 dark:bg-grafana-900/30 dark:text-grafana-400";
    case "technical":
      return "bg-primary-100 text-primary-700 dark:bg-primary-900/30 dark:text-primary-400";
  }
}

// =============================================================================
// Component
// =============================================================================

export function HIPAAPanel({
  controls,
  isLoading = false,
  className,
}: HIPAAPanelProps) {
  // Calculate compliance stats
  const compliantCount = controls.filter(
    (c) => c.status === "compliant",
  ).length;
  const percentage =
    controls.length > 0
      ? Math.round((compliantCount / controls.length) * 100)
      : 0;

  // Loading state
  if (isLoading) {
    return (
      <div
        data-testid="hipaa-panel"
        className={cn(
          "rounded-lg border border-gray-200 dark:border-gray-700",
          "bg-white dark:bg-gray-900 p-4",
          className,
        )}
      >
        <div className="flex items-center gap-2 text-gray-500 dark:text-gray-400">
          <Loader2 size={16} className="animate-spin" />
          <span>Loading HIPAA controls...</span>
        </div>
      </div>
    );
  }

  return (
    <div
      data-testid="hipaa-panel"
      className={cn(
        "rounded-lg border border-gray-200 dark:border-gray-700",
        "bg-white dark:bg-gray-900",
        className,
      )}
    >
      {/* Header */}
      <div className="flex items-center justify-between p-4 border-b border-gray-200 dark:border-gray-700">
        <div className="flex items-center gap-2">
          <HeartPulse size={18} className="text-error-500" />
          <h3 className="font-semibold text-gray-900 dark:text-gray-100">
            HIPAA
          </h3>
        </div>
        <div className="flex items-center gap-4">
          <span className="text-2xl font-bold text-gray-900 dark:text-gray-100">
            {percentage}%
          </span>
          <span className="text-sm text-gray-500 dark:text-gray-400">
            {compliantCount}/{controls.length} controls
          </span>
        </div>
      </div>

      {/* Content */}
      <div className="p-4">
        {controls.length === 0 ? (
          <div className="flex items-center justify-center py-8 text-sm text-gray-500 dark:text-gray-400">
            <HeartPulse size={20} className="mr-2 opacity-50" />
            No controls configured
          </div>
        ) : (
          <div className="space-y-3">
            {controls.map((control) => (
              <div
                key={control.id}
                className={cn(
                  "flex items-start gap-3 p-3 rounded-lg",
                  "bg-gray-50 dark:bg-gray-800",
                  "border border-gray-100 dark:border-gray-700",
                )}
              >
                {/* Status icon */}
                <div className="flex-shrink-0 mt-0.5">
                  {getStatusIcon(control.status)}
                </div>

                {/* Content */}
                <div className="flex-1 min-w-0">
                  <div className="flex items-center gap-2 flex-wrap">
                    <span className="text-sm font-medium text-gray-700 dark:text-gray-300">
                      {control.name}
                    </span>
                    <span
                      className={cn(
                        "text-xs px-1.5 py-0.5 rounded",
                        getCategoryColor(control.category),
                      )}
                    >
                      {control.category}
                    </span>
                    <span
                      className={cn(
                        "text-xs font-medium",
                        getStatusColor(control.status),
                      )}
                    >
                      {control.status}
                    </span>
                  </div>
                  <p className="text-xs text-gray-500 dark:text-gray-400 mt-1">
                    {control.id}
                  </p>
                  {control.phiAccessCount !== undefined && (
                    <div className="flex items-center gap-1 mt-2 text-xs text-primary-600 dark:text-primary-400">
                      <Eye size={12} />
                      <span>PHI Access: {control.phiAccessCount} records</span>
                    </div>
                  )}
                </div>
              </div>
            ))}
          </div>
        )}
      </div>
    </div>
  );
}
