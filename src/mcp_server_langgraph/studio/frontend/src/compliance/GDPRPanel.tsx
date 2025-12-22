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
      return <CheckCircle size={14} className="text-green-500" />;
    case "partial":
      return <AlertCircle size={14} className="text-yellow-500" />;
    case "non-compliant":
      return <XCircle size={14} className="text-red-500" />;
    default:
      return <AlertCircle size={14} className="text-gray-400" />;
  }
}

function getStatusColor(status: ControlStatus): string {
  switch (status) {
    case "compliant":
      return "text-green-600 dark:text-green-400";
    case "partial":
      return "text-yellow-600 dark:text-yellow-400";
    case "non-compliant":
      return "text-red-600 dark:text-red-400";
    default:
      return "text-gray-500 dark:text-gray-400";
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
          "rounded-lg border border-gray-200 dark:border-gray-700",
          "bg-white dark:bg-gray-900 p-4",
          className,
        )}
      >
        <div className="flex items-center gap-2 text-gray-500">
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
        "rounded-lg border border-gray-200 dark:border-gray-700",
        "bg-white dark:bg-gray-900",
        className,
      )}
    >
      {/* Header */}
      <div className="flex items-center justify-between p-4 border-b border-gray-200 dark:border-gray-700">
        <div className="flex items-center gap-2">
          <Flag size={18} className="text-blue-600" />
          <h3 className="font-semibold text-gray-900 dark:text-gray-100">
            GDPR
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
                    <span className="text-xs px-1.5 py-0.5 rounded bg-blue-100 text-blue-700 dark:bg-blue-900/30 dark:text-blue-400">
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
                  <p className="text-xs text-gray-500 dark:text-gray-400 mt-1">
                    {control.id}
                  </p>
                  {control.pendingRequests !== undefined &&
                    control.pendingRequests > 0 && (
                      <div className="flex items-center gap-1 mt-2 text-xs text-orange-600 dark:text-orange-400">
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
