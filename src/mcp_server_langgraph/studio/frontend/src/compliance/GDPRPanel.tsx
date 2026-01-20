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

import { useReducedMotion } from "motion/react";
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
      return <CheckCircle size={14} className="text-success-9" />;
    case "partial":
      return <AlertCircle size={14} className="text-warning-9" />;
    case "non-compliant":
      return <XCircle size={14} className="text-error-9" />;
    default:
      return (
        <AlertCircle
          size={14}
          className="text-neutral-9"
        />
      );
  }
}

function getStatusColor(status: ControlStatus): string {
  switch (status) {
    case "compliant":
      return "text-success-10 dark:text-success-7";
    case "partial":
      return "text-warning-9 dark:text-warning-9";
    case "non-compliant":
      return "text-error-10 dark:text-error-7";
    default:
      return "text-neutral-10";
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
  // WCAG 2.2 AA: Respect user's reduced motion preference
  const prefersReducedMotion = useReducedMotion();

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
          "rounded-lg border border-neutral-5",
          "bg-neutral-1 p-4",
          className,
        )}
      >
        <div className="flex items-center gap-2 text-neutral-10">
          <Loader2 size={16} className={cn(!prefersReducedMotion && "animate-spin")} />
          <span>Loading GDPR controls...</span>
        </div>
      </div>
    );
  }

  return (
    <div
      data-testid="gdpr-panel"
      className={cn(
        "rounded-lg border border-neutral-5",
        "bg-neutral-1",
        className,
      )}
    >
      {/* Header */}
      <div className="flex items-center justify-between p-4 border-b border-neutral-5">
        <div className="flex items-center gap-2">
          <Flag size={18} className="text-primary-10" />
          <h3 className="font-semibold text-neutral-12">
            GDPR
          </h3>
        </div>
        <div className="flex items-center gap-4">
          <span className="text-2xl font-bold text-neutral-12">
            {percentage}%
          </span>
          <span className="text-sm text-neutral-10">
            {compliantCount}/{controls.length} controls
          </span>
        </div>
      </div>

      {/* Content */}
      <div className="p-4">
        {controls.length === 0 ? (
          <div className="flex items-center justify-center py-8 text-sm text-neutral-10">
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
                  "bg-neutral-1",
                  "border border-neutral-5",
                )}
              >
                {/* Status icon */}
                <div className="flex-shrink-0 mt-0.5">
                  {getStatusIcon(control.status)}
                </div>

                {/* Content */}
                <div className="flex-1 min-w-0">
                  <div className="flex items-center gap-2 flex-wrap">
                    <span className="text-sm font-medium text-neutral-11">
                      {control.name}
                    </span>
                    <span className="text-xs px-1.5 py-0.5 rounded bg-primary-3 text-primary-11 bg-primary-4 dark:text-primary-7">
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
                  <p className="text-xs text-neutral-10 mt-1">
                    {control.id}
                  </p>
                  {control.pendingRequests !== undefined &&
                    control.pendingRequests > 0 && (
                      <div className="flex items-center gap-1 mt-2 text-xs text-grafana-10 dark:text-grafana-5">
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
