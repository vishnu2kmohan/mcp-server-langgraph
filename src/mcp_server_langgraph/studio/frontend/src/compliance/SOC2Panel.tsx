/**
 * SOC2Panel Component
 *
 * Phase 5: Compliance Dashboards
 * Displays SOC-2 compliance controls status.
 *
 * Features:
 * - Control status grid with color indicators
 * - Compliance percentage summary
 * - Remediation tracking
 */

import { useReducedMotion } from "motion/react";
import {
  Shield,
  CheckCircle,
  AlertCircle,
  XCircle,
  Loader2,
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

export interface SOC2Control {
  id: string;
  name: string;
  status: ControlStatus;
  lastAssessed: string;
  remediationDue?: string;
}

export interface SOC2PanelProps {
  controls: SOC2Control[];
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
      return <AlertCircle size={14} className="text-neutral-9" />;
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

function formatDate(dateString: string): string {
  const date = new Date(dateString);
  return date.toLocaleDateString("en-US", {
    month: "short",
    day: "numeric",
    year: "numeric",
  });
}

// =============================================================================
// Component
// =============================================================================

export function SOC2Panel({
  controls,
  isLoading = false,
  className,
}: SOC2PanelProps) {
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
        data-testid="soc2-panel"
        className={cn(
          "rounded-lg border border-neutral-5",
          "bg-neutral-1 p-4",
          className,
        )}
      >
        <div className="flex items-center gap-2 text-neutral-10">
          <Loader2
            size={16}
            className={cn(!prefersReducedMotion && "animate-spin")}
          />
          <span>Loading SOC-2 controls...</span>
        </div>
      </div>
    );
  }

  return (
    <div
      data-testid="soc2-panel"
      className={cn(
        "rounded-lg border border-neutral-5",
        "bg-neutral-1",
        className,
      )}
    >
      {/* Header */}
      <div className="flex items-center justify-between p-4 border-b border-neutral-5">
        <div className="flex items-center gap-2">
          <Shield size={18} className="text-primary-9" />
          <h3 className="font-semibold text-neutral-12">SOC-2</h3>
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
            <Shield size={20} className="mr-2 opacity-50" />
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
                  <div className="flex items-center gap-2">
                    <span className="text-sm font-medium text-neutral-11">
                      {control.id}
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
                  <p className="text-sm text-neutral-11">{control.name}</p>
                  <div className="flex items-center gap-4 mt-1 text-xs text-neutral-9">
                    <span>Assessed: {formatDate(control.lastAssessed)}</span>
                    {control.remediationDue && (
                      <span className="text-error-9">
                        Due: {formatDate(control.remediationDue)}
                      </span>
                    )}
                  </div>
                </div>
              </div>
            ))}
          </div>
        )}
      </div>
    </div>
  );
}
