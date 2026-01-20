/**
 * FedRAMPPanel Component
 *
 * Phase 5: Compliance Dashboards
 * Displays FedRAMP compliance status.
 *
 * Features:
 * - Authorization status (P-ATO, ATO)
 * - Control families and impact levels
 * - POA&M tracking
 * - Compliance percentage summary
 */

import { useReducedMotion } from "motion/react";
import {
  BadgeCheck,
  CheckCircle,
  AlertCircle,
  XCircle,
  Loader2,
  FileWarning,
} from "lucide-react";
import { cn } from "../utils/cn";
import { Badge } from "@/components/UI";

// =============================================================================
// Types
// =============================================================================

export type ControlStatus =
  | "compliant"
  | "partial"
  | "non-compliant"
  | "not-applicable";
export type ImpactLevel = "low" | "moderate" | "high";
export type AuthLevel = "P-ATO" | "ATO" | "None";

export interface FedRAMPControl {
  id: string;
  name: string;
  family: string;
  impact: ImpactLevel;
  status: ControlStatus;
  lastAssessed: string;
  poamId?: string;
}

export interface FedRAMPAuthStatus {
  level: AuthLevel;
  grantedDate?: string;
  expiresDate?: string;
}

export interface FedRAMPPanelProps {
  controls: FedRAMPControl[];
  authStatus: FedRAMPAuthStatus;
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

function getImpactColor(impact: ImpactLevel): string {
  switch (impact) {
    case "high":
      return "bg-error-3 text-error-11 bg-error-4 dark:text-error-7";
    case "moderate":
      return "bg-warning-3 text-warning-10 dark:bg-warning-a4 dark:text-warning-9";
    case "low":
      return "bg-success-3 text-success-11 bg-success-4 dark:text-success-7";
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

function getAuthLevelColor(level: AuthLevel): string {
  switch (level) {
    case "ATO":
      return "bg-success-3 text-success-11 bg-success-4 dark:text-success-7";
    case "P-ATO":
      return "bg-primary-3 text-primary-11 bg-primary-4 dark:text-primary-7";
    default:
      return "bg-neutral-2 text-neutral-11";
  }
}

// =============================================================================
// Component
// =============================================================================

export function FedRAMPPanel({
  controls,
  authStatus,
  isLoading = false,
  className,
}: FedRAMPPanelProps) {
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
        data-testid="fedramp-panel"
        className={cn(
          "rounded-lg border border-neutral-5",
          "bg-neutral-1 p-4",
          className,
        )}
      >
        <div className="flex items-center gap-2 text-neutral-10">
          <Loader2 size={16} className={cn(!prefersReducedMotion && "animate-spin")} />
          <span>Loading FedRAMP controls...</span>
        </div>
      </div>
    );
  }

  return (
    <div
      data-testid="fedramp-panel"
      className={cn(
        "rounded-lg border border-neutral-5",
        "bg-neutral-1",
        className,
      )}
    >
      {/* Header */}
      <div className="flex items-center justify-between p-4 border-b border-neutral-5">
        <div className="flex items-center gap-2">
          <BadgeCheck size={18} className="text-insight-10" />
          <h3 className="font-semibold text-neutral-12">
            FedRAMP
          </h3>
          <Badge
            size="sm"
            className={getAuthLevelColor(authStatus.level)}
          >
            {authStatus.level}
          </Badge>
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

      {/* Authorization info */}
      {authStatus.expiresDate && (
        <div className="px-4 py-2 bg-neutral-1 border-b border-neutral-5">
          <span className="text-xs text-neutral-10">
            Authorization expires: {formatDate(authStatus.expiresDate)} (2028)
          </span>
        </div>
      )}

      {/* Content */}
      <div className="p-4">
        {controls.length === 0 ? (
          <div className="flex items-center justify-center py-8 text-sm text-neutral-10">
            <BadgeCheck size={20} className="mr-2 opacity-50" />
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
                      {control.id}
                    </span>
                    <Badge
                      size="sm"
                      className={getImpactColor(control.impact)}
                    >
                      {control.impact}
                    </Badge>
                    <span
                      className={cn(
                        "text-xs font-medium",
                        getStatusColor(control.status),
                      )}
                    >
                      {control.status}
                    </span>
                  </div>
                  <p className="text-sm text-neutral-11">
                    {control.name}
                  </p>
                  <p className="text-xs text-neutral-9 mt-1">
                    {control.family}
                  </p>
                  {control.poamId && (
                    <div className="flex items-center gap-1 mt-2 text-xs text-grafana-10 dark:text-grafana-5">
                      <FileWarning size={12} />
                      <span>POA&M: {control.poamId}</span>
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
