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

import {
  BadgeCheck,
  CheckCircle,
  AlertCircle,
  XCircle,
  Loader2,
  FileWarning,
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

function getImpactColor(impact: ImpactLevel): string {
  switch (impact) {
    case "high":
      return "bg-error-100 text-error-700 dark:bg-error-900/30 dark:text-error-400";
    case "moderate":
      return "bg-warning-100 text-warning-700 dark:bg-warning-900/30 dark:text-warning-400";
    case "low":
      return "bg-success-100 text-success-700 dark:bg-success-900/30 dark:text-success-400";
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
      return "bg-success-100 text-success-800 dark:bg-success-900/30 dark:text-success-400";
    case "P-ATO":
      return "bg-primary-100 text-primary-800 dark:bg-primary-900/30 dark:text-primary-400";
    default:
      return "bg-gray-100 dark:bg-gray-800 text-gray-600 dark:text-gray-400";
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
          "rounded-lg border border-gray-200 dark:border-gray-700",
          "bg-white dark:bg-gray-900 p-4",
          className,
        )}
      >
        <div className="flex items-center gap-2 text-gray-500 dark:text-gray-400">
          <Loader2 size={16} className="animate-spin" />
          <span>Loading FedRAMP controls...</span>
        </div>
      </div>
    );
  }

  return (
    <div
      data-testid="fedramp-panel"
      className={cn(
        "rounded-lg border border-gray-200 dark:border-gray-700",
        "bg-white dark:bg-gray-900",
        className,
      )}
    >
      {/* Header */}
      <div className="flex items-center justify-between p-4 border-b border-gray-200 dark:border-gray-700">
        <div className="flex items-center gap-2">
          <BadgeCheck size={18} className="text-insight-600" />
          <h3 className="font-semibold text-gray-900 dark:text-gray-100">
            FedRAMP
          </h3>
          <span
            className={cn(
              "text-xs px-2 py-0.5 rounded font-medium",
              getAuthLevelColor(authStatus.level),
            )}
          >
            {authStatus.level}
          </span>
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

      {/* Authorization info */}
      {authStatus.expiresDate && (
        <div className="px-4 py-2 bg-gray-50 dark:bg-gray-800 border-b border-gray-200 dark:border-gray-700">
          <span className="text-xs text-gray-500 dark:text-gray-400">
            Authorization expires: {formatDate(authStatus.expiresDate)} (2028)
          </span>
        </div>
      )}

      {/* Content */}
      <div className="p-4">
        {controls.length === 0 ? (
          <div className="flex items-center justify-center py-8 text-sm text-gray-500 dark:text-gray-400">
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
                      {control.id}
                    </span>
                    <span
                      className={cn(
                        "text-xs px-1.5 py-0.5 rounded",
                        getImpactColor(control.impact),
                      )}
                    >
                      {control.impact}
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
                  <p className="text-sm text-gray-600 dark:text-gray-400">
                    {control.name}
                  </p>
                  <p className="text-xs text-gray-400 dark:text-gray-400 mt-1">
                    {control.family}
                  </p>
                  {control.poamId && (
                    <div className="flex items-center gap-1 mt-2 text-xs text-grafana-600 dark:text-grafana-400">
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
