/**
 * BudgetStatusCard
 *
 * Component for displaying budget status with visual indicators.
 * Shows spend, limit, percentage used, and status styling.
 */

import { Building2, Folder, Users, User, Wallet } from "lucide-react";
import { Skeleton } from "../UI";

/** Budget status from the API */
export type BudgetStatusType = "ok" | "warning" | "critical" | "exceeded";
export type EntityType = "organization" | "project" | "team" | "user";

export interface BudgetStatus {
  entityType: EntityType;
  entityId: string;
  status: BudgetStatusType;
  percentUsed: number;
  currentSpend: string;
  remaining: string;
  monthlyLimitUsd: string;
  message: string;
}

export interface BudgetStatusCardProps {
  /** Budget status data */
  status: BudgetStatus | null;
  /** Loading state */
  loading?: boolean;
  /** Compact display mode */
  compact?: boolean;
  /** Additional class name */
  className?: string;
}

/** Get status-specific styling */
function getStatusStyles(status: BudgetStatusType): {
  bgColor: string;
  borderColor: string;
  textColor: string;
  progressColor: string;
} {
  switch (status) {
    case "ok":
      return {
        bgColor: "bg-success-50 dark:bg-success-900/20",
        borderColor: "border-success-200 dark:border-success-800",
        textColor: "text-success-700 dark:text-success-400",
        progressColor: "bg-success-500",
      };
    case "warning":
      return {
        bgColor: "bg-warning-50 dark:bg-warning-900/20",
        borderColor: "border-warning-200 dark:border-warning-800",
        textColor: "text-warning-700 dark:text-warning-400",
        progressColor: "bg-warning-500",
      };
    case "critical":
      return {
        bgColor: "bg-grafana-50 dark:bg-grafana-900/20",
        borderColor: "border-grafana-200 dark:border-grafana-800",
        textColor: "text-grafana-700 dark:text-grafana-400",
        progressColor: "bg-grafana-500",
      };
    case "exceeded":
      return {
        bgColor: "bg-error-50 dark:bg-error-900/20",
        borderColor: "border-error-200 dark:border-error-800",
        textColor: "text-error-700 dark:text-error-400",
        progressColor: "bg-error-500",
      };
  }
}

/** Get icon for entity type */
function EntityIcon({ entityType }: { entityType: EntityType }) {
  const className = "w-5 h-5 text-gray-400 dark:text-gray-400";

  switch (entityType) {
    case "organization":
      return <Building2 className={className} data-testid="entity-icon" />;
    case "project":
      return <Folder className={className} data-testid="entity-icon" />;
    case "team":
      return <Users className={className} data-testid="entity-icon" />;
    case "user":
      return <User className={className} data-testid="entity-icon" />;
  }
}

/** Extract display name from entity ID */
function getDisplayName(entityId: string): string {
  // Remove prefix like "organization:", "project:", etc.
  const parts = entityId.split(":");
  return parts.length > 1 ? parts[1] : entityId;
}

/** Format currency */
function formatCurrency(value: string): string {
  const num = parseFloat(value);
  return new Intl.NumberFormat("en-US", {
    style: "currency",
    currency: "USD",
  }).format(num);
}

export function BudgetStatusCard({
  status,
  loading = false,
  compact = false,
  className = "",
}: BudgetStatusCardProps) {
  // Loading skeleton
  if (loading || !status) {
    return (
      <div
        data-testid="budget-status-skeleton"
        className={`p-4 rounded-lg border border-gray-200 dark:border-gray-700 ${className}`}
      >
        <div className="flex items-center gap-3 mb-3">
          <Skeleton className="w-5 h-5 rounded" />
          <Skeleton className="w-24 h-4" />
        </div>
        <Skeleton className="w-full h-2 mb-2" />
        <div className="flex justify-between">
          <Skeleton className="w-16 h-4" />
          <Skeleton className="w-16 h-4" />
        </div>
      </div>
    );
  }

  const styles = getStatusStyles(status.status);
  const displayName = getDisplayName(status.entityId);
  const progressWidth = Math.min(status.percentUsed, 100);

  return (
    <div
      data-testid="budget-status-card"
      className={`
        p-4 rounded-lg border
        ${styles.bgColor} ${styles.borderColor}
        ${compact ? "compact" : ""}
        ${className}
      `}
    >
      {/* Header */}
      <div className="flex items-center justify-between mb-3">
        <div className="flex items-center gap-2">
          <EntityIcon entityType={status.entityType} />
          <span className="font-medium text-gray-900 dark:text-gray-100">
            {displayName}
          </span>
        </div>
        <span
          className={`text-sm font-semibold px-2 py-0.5 rounded ${styles.textColor} ${styles.bgColor}`}
        >
          {status.status.toUpperCase()}
        </span>
      </div>

      {/* Progress Bar */}
      <div
        role="progressbar"
        aria-valuenow={status.percentUsed}
        aria-valuemin={0}
        aria-valuemax={100}
        className="w-full h-2 bg-gray-200 dark:bg-gray-700 rounded-full overflow-hidden mb-3"
      >
        <div
          className={`h-full ${styles.progressColor} transition-all duration-300`}
          style={{ width: `${progressWidth}%` }}
        />
      </div>

      {/* Stats */}
      <div className="flex justify-between text-sm">
        <div>
          <span className="text-gray-500 dark:text-gray-400">Spent: </span>
          <span className="font-medium text-gray-900 dark:text-gray-100">
            {formatCurrency(status.currentSpend)}
          </span>
        </div>
        <div>
          <span className="text-gray-500 dark:text-gray-400">Limit: </span>
          <span className="font-medium text-gray-900 dark:text-gray-100">
            {formatCurrency(status.monthlyLimitUsd)}
          </span>
        </div>
      </div>

      {/* Percentage */}
      <div className="mt-2 text-center">
        <span className={`text-2xl font-bold ${styles.textColor}`}>
          {status.percentUsed.toFixed(0)}%
        </span>
        <span className="text-gray-500 dark:text-gray-400 text-sm ml-1">
          used
        </span>
      </div>

      {/* Remaining */}
      {!compact && (
        <div className="mt-2 text-center text-sm text-gray-500 dark:text-gray-400">
          {parseFloat(status.remaining) >= 0 ? (
            <>Remaining: {formatCurrency(status.remaining)}</>
          ) : (
            <span className="text-error-600 dark:text-error-400">
              Over budget:{" "}
              {formatCurrency(
                Math.abs(parseFloat(status.remaining)).toString(),
              )}
            </span>
          )}
        </div>
      )}

      {/* Icon for visual emphasis */}
      {!compact && status.status !== "ok" && (
        <div className="mt-3 flex items-center justify-center">
          <Wallet className={`w-6 h-6 ${styles.textColor}`} />
        </div>
      )}
    </div>
  );
}

export default BudgetStatusCard;
