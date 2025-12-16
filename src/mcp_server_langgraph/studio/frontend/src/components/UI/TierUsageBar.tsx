/**
 * TierUsageBar Component
 *
 * Displays usage information relative to tier limits.
 * Shows progress bar, current/max values, and warning states.
 * Part of Bob's user journey - surfacing tier limits to prevent confusion.
 */

import { AlertTriangle } from "lucide-react";

export interface TierUsageBarProps {
  /** Current usage count */
  current: number;
  /** Maximum allowed for this tier (-1 for unlimited) */
  max: number;
  /** Label describing what's being measured */
  label: string;
  /** Organization tier name */
  tier?: "shared" | "hybrid" | "dedicated";
  /** Display variant */
  variant?: "default" | "compact";
}

/**
 * Visual indicator for tier-based usage limits.
 *
 * @example
 * ```tsx
 * <TierUsageBar
 *   current={3}
 *   max={5}
 *   label="Active Sessions"
 *   tier="shared"
 * />
 * ```
 */
export function TierUsageBar({
  current,
  max,
  label,
  tier,
  variant = "default",
}: TierUsageBarProps) {
  const isUnlimited = max === -1;
  const percentage = isUnlimited ? 100 : max > 0 ? (current / max) * 100 : 0;
  const clampedPercentage = Math.min(100, Math.max(0, percentage));

  // Determine color based on usage percentage
  const getProgressColor = () => {
    if (isUnlimited) return "bg-green-500";
    if (percentage >= 100) return "bg-red-500";
    if (percentage >= 80) return "bg-amber-500";
    return "bg-blue-500";
  };

  const shouldShowWarning = !isUnlimited && percentage >= 80;

  // Format tier name for display
  const formatTierName = (tierName: string) => {
    return tierName.charAt(0).toUpperCase() + tierName.slice(1);
  };

  // Get tier badge color
  const getTierBadgeStyle = () => {
    switch (tier) {
      case "dedicated":
        return "bg-purple-100 text-purple-700 dark:bg-purple-900/30 dark:text-purple-400";
      case "hybrid":
        return "bg-blue-100 text-blue-700 dark:bg-blue-900/30 dark:text-blue-400";
      case "shared":
      default:
        return "bg-gray-100 text-gray-700 dark:bg-gray-700 dark:text-gray-300";
    }
  };

  return (
    <div className="flex items-center gap-3">
      {/* Label and Tier Badge */}
      {variant !== "compact" && (
        <div className="flex items-center gap-2 min-w-0">
          <span className="text-sm font-medium text-gray-700 dark:text-gray-300 truncate">
            {label}
          </span>
          {tier && (
            <span
              className={`text-xs px-2 py-0.5 rounded-full whitespace-nowrap ${getTierBadgeStyle()}`}
            >
              {formatTierName(tier)}
            </span>
          )}
        </div>
      )}

      {/* Progress Bar Container */}
      <div className="flex items-center gap-2 flex-1 min-w-[120px]">
        {/* Progress Bar */}
        <div
          role="progressbar"
          aria-label={`${label} usage`}
          aria-valuenow={current}
          aria-valuemin={0}
          aria-valuemax={isUnlimited ? current : max}
          className="flex-1 h-2 bg-gray-200 dark:bg-gray-700 rounded-full overflow-hidden"
        >
          <div
            data-testid="tier-usage-fill"
            className={`h-full transition-all duration-300 ${getProgressColor()}`}
            style={{ width: `${clampedPercentage}%` }}
          />
        </div>

        {/* Usage Count */}
        <div className="flex items-center gap-1 text-sm text-gray-600 dark:text-gray-400 whitespace-nowrap">
          {shouldShowWarning && (
            <AlertTriangle
              size={14}
              className="text-amber-500"
              data-testid="usage-warning-icon"
            />
          )}
          {isUnlimited ? (
            <>
              <span className="font-medium">{current}</span>
              <span className="text-gray-400 dark:text-gray-500">
                / Unlimited
              </span>
            </>
          ) : (
            <span className="font-medium">
              {current} / {max}
            </span>
          )}
        </div>
      </div>

      {/* Compact variant tier badge */}
      {variant === "compact" && tier && (
        <span
          className={`text-xs px-2 py-0.5 rounded-full ${getTierBadgeStyle()}`}
        >
          {formatTierName(tier)}
        </span>
      )}
    </div>
  );
}

export default TierUsageBar;
