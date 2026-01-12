/**
 * TierUsageBar Component
 *
 * Displays usage information relative to tier limits.
 * Shows progress bar, current/max values, and warning states.
 * Uses CVA for type-safe variant and tier styling.
 *
 * Part of Bob's user journey - surfacing tier limits to prevent confusion.
 */

import { cva, type VariantProps } from "class-variance-authority";
import { AlertTriangle } from "lucide-react";
import { cn } from "../../utils/cn";

/**
 * TierUsageBar variant styles using CVA
 */
export const tierUsageBarVariants = cva(
  // Base styles
  "flex items-center gap-3",
  {
    variants: {
      variant: {
        default: "",
        compact: "",
      },
    },
    defaultVariants: {
      variant: "default",
    },
  },
);

/**
 * Tier badge styles using CVA
 */
export const tierBadgeVariants = cva(
  "text-xs px-2 py-0.5 rounded-full whitespace-nowrap",
  {
    variants: {
      tier: {
        dedicated:
          "bg-insight-100 text-insight-700 dark:bg-insight-900/30 dark:text-insight-400",
        hybrid:
          "bg-primary-100 text-primary-700 dark:bg-primary-900/30 dark:text-primary-400",
        shared:
          "bg-neutral-100 dark:bg-neutral-700 text-neutral-700 dark:text-neutral-300",
      },
    },
    defaultVariants: {
      tier: "shared",
    },
  },
);

export type TierUsageBarVariant = NonNullable<
  VariantProps<typeof tierUsageBarVariants>["variant"]
>;
export type TierType = NonNullable<
  VariantProps<typeof tierBadgeVariants>["tier"]
>;

export interface TierUsageBarProps extends VariantProps<
  typeof tierUsageBarVariants
> {
  /** Current usage count */
  current: number;
  /** Maximum allowed for this tier (-1 for unlimited) */
  max: number;
  /** Label describing what's being measured */
  label: string;
  /** Organization tier name */
  tier?: TierType;
}

/**
 * Get progress bar color based on usage percentage
 */
function getProgressColor(percentage: number, isUnlimited: boolean): string {
  if (isUnlimited) return "bg-success-500";
  if (percentage >= 100) return "bg-error-500";
  if (percentage >= 80) return "bg-warning-500";
  return "bg-primary-500";
}

/**
 * Format tier name for display
 */
function formatTierName(tierName: string): string {
  return tierName.charAt(0).toUpperCase() + tierName.slice(1);
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
  variant,
}: TierUsageBarProps) {
  const resolvedVariant = variant ?? "default";
  const isUnlimited = max === -1;
  const percentage = isUnlimited ? 100 : max > 0 ? (current / max) * 100 : 0;
  const clampedPercentage = Math.min(100, Math.max(0, percentage));
  const shouldShowWarning = !isUnlimited && percentage >= 80;

  return (
    <div className={cn(tierUsageBarVariants({ variant }))}>
      {/* Label and Tier Badge */}
      {resolvedVariant !== "compact" && (
        <div className="flex items-center gap-2 min-w-0">
          <span className="text-sm font-medium text-neutral-700 dark:text-neutral-300 truncate">
            {label}
          </span>
          {tier && (
            <span className={tierBadgeVariants({ tier })}>
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
          className="flex-1 h-2 bg-neutral-200 dark:bg-neutral-700 rounded-full overflow-hidden"
        >
          <div
            data-testid="tier-usage-fill"
            className={cn(
              "h-full transition-all duration-300",
              getProgressColor(percentage, isUnlimited),
            )}
            style={{ width: `${clampedPercentage}%` }}
          />
        </div>

        {/* Usage Count */}
        <div className="flex items-center gap-1 text-sm text-neutral-600 dark:text-neutral-400 whitespace-nowrap">
          {shouldShowWarning && (
            <AlertTriangle
              size={14}
              className="text-warning-500"
              data-testid="usage-warning-icon"
            />
          )}
          {isUnlimited ? (
            <>
              <span className="font-medium">{current}</span>
              <span className="text-neutral-400 dark:text-neutral-400">
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
      {resolvedVariant === "compact" && tier && (
        <span className={tierBadgeVariants({ tier })}>
          {formatTierName(tier)}
        </span>
      )}
    </div>
  );
}

export default TierUsageBar;
