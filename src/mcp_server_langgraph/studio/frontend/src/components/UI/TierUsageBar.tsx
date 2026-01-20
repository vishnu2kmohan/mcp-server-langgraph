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
          "bg-insight-2 text-insight-11 dark:bg-insight-a4 dark:text-insight-9",
        hybrid:
          "bg-primary-3 text-primary-11 bg-primary-4 dark:text-primary-7",
        shared:
          "bg-neutral-2 text-neutral-11",
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
  if (isUnlimited) return "bg-success-9";
  if (percentage >= 100) return "bg-error-9";
  if (percentage >= 80) return "bg-warning-9";
  return "bg-primary-9";
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
          <span className="text-sm font-medium text-neutral-11 truncate">
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
      <div className="flex items-center gap-2 flex-1 min-w-32">
        {/* Progress Bar */}
        <div
          role="progressbar"
          aria-label={`${label} usage`}
          aria-valuenow={current}
          aria-valuemin={0}
          aria-valuemax={isUnlimited ? current : max}
          className="flex-1 h-2 bg-neutral-3 rounded-full overflow-hidden"
        >
          <div
            data-testid="tier-usage-fill"
            className={cn(
              "h-full transition-all duration-300",
              getProgressColor(percentage, isUnlimited),
            )}
            style={{ '--progress': `${clampedPercentage}%` } as React.CSSProperties}
          />
        </div>

        {/* Usage Count */}
        <div className="flex items-center gap-1 text-sm text-neutral-11 whitespace-nowrap">
          {shouldShowWarning && (
            <AlertTriangle
              size={14}
              className="text-warning-9"
              data-testid="usage-warning-icon"
            />
          )}
          {isUnlimited ? (
            <>
              <span className="font-medium">{current}</span>
              <span className="text-neutral-9">
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
