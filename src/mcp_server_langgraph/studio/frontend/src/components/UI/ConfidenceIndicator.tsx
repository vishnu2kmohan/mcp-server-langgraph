/**
 * ConfidenceIndicator Component
 *
 * Displays AI confidence scores with semantic color coding.
 * Uses CONFIDENCE_COLORS from utils/colors for centralized color management.
 *
 * Color thresholds:
 * - High (>= 0.9): Success (green)
 * - Medium (>= 0.7): Warning (amber)
 * - Low (< 0.7): Error (red)
 */

import { type HTMLAttributes } from "react";
import { getConfidenceColor } from "../../utils/colors";

export type ConfidenceIndicatorSize = "sm" | "md" | "lg";

export interface ConfidenceIndicatorProps extends Omit<
  HTMLAttributes<HTMLSpanElement>,
  "children"
> {
  /** Confidence score between 0 and 1 */
  score: number;
  /** Size of the indicator */
  size?: ConfidenceIndicatorSize;
  /** Optional label to display before the score */
  label?: string;
  /** Show as decimal instead of percentage */
  showDecimal?: boolean;
}

/**
 * Utility to combine class names
 */
function cn(...classes: (string | undefined | boolean)[]): string {
  return classes.filter(Boolean).join(" ");
}

/**
 * Get size-specific classes
 */
function getSizeClasses(size: ConfidenceIndicatorSize): string {
  const sizes: Record<ConfidenceIndicatorSize, string> = {
    sm: "text-xs",
    md: "text-sm",
    lg: "text-base",
  };
  return sizes[size];
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
  size = "md",
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
        // Base styles
        "inline-flex items-center font-medium",
        // Confidence color from design system
        getConfidenceColor(score),
        // Size styles
        getSizeClasses(size),
        className,
      )}
      {...props}
    >
      {label && <>{label}: </>}
      {formattedScore}
    </span>
  );
}
