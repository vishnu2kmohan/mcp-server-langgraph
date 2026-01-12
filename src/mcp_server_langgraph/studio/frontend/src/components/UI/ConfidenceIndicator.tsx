/**
 * ConfidenceIndicator Component
 *
 * Displays AI confidence scores with semantic color coding.
 * Uses CVA for type-safe size variants and dynamic color from utils/colors.
 *
 * Color thresholds:
 * - High (>= 0.9): Success (green)
 * - Medium (>= 0.7): Warning (amber)
 * - Low (< 0.7): Error (red)
 */

import { cva, type VariantProps } from "class-variance-authority";
import { type HTMLAttributes } from "react";
import { getConfidenceColor } from "../../utils/colors";
import { cn } from "../../utils/cn";

/**
 * ConfidenceIndicator variant styles using CVA
 */
export const confidenceIndicatorVariants = cva(
  // Base styles
  "inline-flex items-center font-medium",
  {
    variants: {
      size: {
        sm: "text-xs",
        md: "text-sm",
        lg: "text-base",
      },
    },
    defaultVariants: {
      size: "md",
    },
  },
);

export type ConfidenceIndicatorSize = NonNullable<
  VariantProps<typeof confidenceIndicatorVariants>["size"]
>;

export interface ConfidenceIndicatorProps
  extends
    Omit<HTMLAttributes<HTMLSpanElement>, "children">,
    VariantProps<typeof confidenceIndicatorVariants> {
  /** Confidence score between 0 and 1 */
  score: number;
  /** Optional label to display before the score */
  label?: string;
  /** Show as decimal instead of percentage */
  showDecimal?: boolean;
}

/**
 * Format score for display
 */
function formatScore(score: number, showDecimal: boolean): string {
  if (showDecimal) {
    return score.toFixed(2);
  }
  return `${Math.round(score * 100)}%`;
}

/**
 * ConfidenceIndicator component with semantic confidence-based styling
 */
export function ConfidenceIndicator({
  score,
  size,
  label,
  showDecimal = false,
  className,
  ...props
}: ConfidenceIndicatorProps) {
  const formattedScore = formatScore(score, showDecimal);
  const ariaLabel = `Confidence: ${Math.round(score * 100)}%`;

  return (
    <span
      data-testid="confidence-indicator"
      aria-label={ariaLabel}
      className={cn(
        confidenceIndicatorVariants({ size }),
        // Dynamic confidence color from design system
        getConfidenceColor(score),
        className,
      )}
      {...props}
    >
      {label && <>{label}: </>}
      {formattedScore}
    </span>
  );
}
