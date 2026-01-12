/**
 * GDPRPanel Component
 *
 * Phase 5: Compliance Dashboards
 * Displays GDPR compliance status.
 *
 * Features:
 * - Article-based controls
 * - Data subject request tracking
 * - Compliance percentage summary
 */

import {
  Flag,
  CheckCircle,
  AlertCircle,
  XCircle,
  Loader2,
  Users,
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

export interface GDPRControl {
  id: string;
  name: string;
  article: string;
  status: ControlStatus;
  lastAssessed: string;
  pendingRequests?: number;
}

export interface GDPRPanelProps {
  controls: GDPRControl[];
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
        <AlertCircle
          size={14}
          className="text-neutral-400 dark:text-neutral-400"
        />
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
      return "text-neutral-500 dark:text-neutral-400";
  }
}

// =============================================================================
// Component
// =============================================================================

export function GDPRPanel({
  controls,
  isLoading = false,
  className,
}: GDPRPanelProps) {
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
        data-testid="gdpr-panel"
        className={cn(
          "rounded-lg border border-neutral-200 dark:border-neutral-700",
          "bg-white dark:bg-neutral-900 p-4",
          className,
        )}
      >
        <div className="flex items-center gap-2 text-neutral-500 dark:text-neutral-400">
          <Loader2 size={16} className="animate-spin" />
          <span>Loading GDPR controls...</span>
        </div>
      </div>
    );
  }

  return (
    <div
      data-testid="gdpr-panel"
      className={cn(
        "rounded-lg border border-neutral-200 dark:border-neutral-700",
        "bg-white dark:bg-neutral-900",
        className,
      )}
    >
      {/* Header */}
      <div className="flex items-center justify-between p-4 border-b border-neutral-200 dark:border-neutral-700">
        <div className="flex items-center gap-2">
          <Flag size={18} className="text-primary-600" />
          <h3 className="font-semibold text-neutral-900 dark:text-neutral-100">
            GDPR
          </h3>
        </div>
        <div className="flex items-center gap-4">
          <span className="text-2xl font-bold text-neutral-900 dark:text-neutral-100">
            {percentage}%
          </span>
          <span className="text-sm text-neutral-500 dark:text-neutral-400">
            {compliantCount}/{controls.length} controls
          </span>
        </div>
      </div>

      {/* Content */}
      <div className="p-4">
        {controls.length === 0 ? (
          <div className="flex items-center justify-center py-8 text-sm text-neutral-500 dark:text-neutral-400">
            <Flag size={20} className="mr-2 opacity-50" />
            No controls configured
          </div>
        ) : (
          <div className="space-y-3">
            {controls.map((control) => (
              <div
                key={control.id}
                className={cn(
                  "flex items-start gap-3 p-3 rounded-lg",
                  "bg-neutral-50 dark:bg-neutral-800",
                  "border border-neutral-100 dark:border-neutral-700",
                )}
              >
                {/* Status icon */}
                <div className="flex-shrink-0 mt-0.5">
                  {getStatusIcon(control.status)}
                </div>

                {/* Content */}
                <div className="flex-1 min-w-0">
                  <div className="flex items-center gap-2 flex-wrap">
                    <span className="text-sm font-medium text-neutral-700 dark:text-neutral-300">
                      {control.name}
                    </span>
                    <span className="text-xs px-1.5 py-0.5 rounded bg-primary-100 text-primary-700 dark:bg-primary-900/30 dark:text-primary-400">
                      {control.article}
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
                  <p className="text-xs text-neutral-500 dark:text-neutral-400 mt-1">
                    {control.id}
                  </p>
                  {control.pendingRequests !== undefined &&
                    control.pendingRequests > 0 && (
                      <div className="flex items-center gap-1 mt-2 text-xs text-grafana-600 dark:text-grafana-400">
                        <Users size={12} />
                        <span>
                          {control.pendingRequests} pending request
                          {control.pendingRequests !== 1 ? "s" : ""}
                        </span>
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
