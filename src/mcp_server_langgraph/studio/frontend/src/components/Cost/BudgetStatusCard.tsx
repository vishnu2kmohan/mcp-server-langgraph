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
        bgColor: "bg-success-1 dark:bg-success-a3",
        borderColor: "border-success-4 dark:border-success-11",
        textColor: "text-success-11 dark:text-success-7",
        progressColor: "bg-success-9",
      };
    case "warning":
      return {
        bgColor: "bg-warning-3 bg-warning-3",
        borderColor: "border-warning-6 dark:border-warning-11",
        textColor: "text-warning-10 dark:text-warning-9",
        progressColor: "bg-warning-9",
      };
    case "critical":
      return {
        bgColor: "bg-grafana-1 dark:bg-grafana-12/20",
        borderColor: "border-grafana-3 dark:border-grafana-11",
        textColor: "text-grafana-11 dark:text-grafana-5",
        progressColor: "bg-grafana-9",
      };
    case "exceeded":
      return {
        bgColor: "bg-error-1 dark:bg-error-a3",
        borderColor: "border-error-4 dark:border-error-11",
        textColor: "text-error-11 dark:text-error-7",
        progressColor: "bg-error-9",
      };
  }
}

/** Get icon for entity type */
function EntityIcon({ entityType }: { entityType: EntityType }) {
  const className = "w-5 h-5 text-neutral-9";

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
        className={`p-4 rounded-lg border border-neutral-5 ${className}`}
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
          <span className="font-medium text-neutral-12">{displayName}</span>
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
        className="w-full h-2 bg-neutral-3 rounded-full overflow-hidden mb-3"
      >
        <div
          className={`h-full ${styles.progressColor} transition-all duration-300`}
          style={{ "--progress": `${progressWidth}%` } as React.CSSProperties}
        />
      </div>

      {/* Stats */}
      <div className="flex justify-between text-sm">
        <div>
          <span className="text-neutral-10">Spent: </span>
          <span className="font-medium text-neutral-12">
            {formatCurrency(status.currentSpend)}
          </span>
        </div>
        <div>
          <span className="text-neutral-10">Limit: </span>
          <span className="font-medium text-neutral-12">
            {formatCurrency(status.monthlyLimitUsd)}
          </span>
        </div>
      </div>

      {/* Percentage */}
      <div className="mt-2 text-center">
        <span className={`text-2xl font-bold ${styles.textColor}`}>
          {status.percentUsed.toFixed(0)}%
        </span>
        <span className="text-neutral-10 text-sm ml-1">used</span>
      </div>

      {/* Remaining */}
      {!compact && (
        <div className="mt-2 text-center text-sm text-neutral-10">
          {parseFloat(status.remaining) >= 0 ? (
            <>Remaining: {formatCurrency(status.remaining)}</>
          ) : (
            <span className="text-error-10 dark:text-error-7">
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
