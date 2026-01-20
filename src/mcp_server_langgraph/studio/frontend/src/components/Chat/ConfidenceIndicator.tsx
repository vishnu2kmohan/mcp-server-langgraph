/**
 * ConfidenceIndicator Component
 *
 * Displays AI response confidence score with visual indicators.
 * Helps users understand how confident the AI is in its response.
 *
 * Design System Compliance:
 * - Uses CVA for confidence level variants
 * - Uses Motion.dev for indicator appearance animation
 * - Implements useReducedMotion() for accessibility
 * - Uses semantic colors per STYLE.md
 */

import { motion, useReducedMotion } from "motion/react";
import { cva } from "class-variance-authority";
import { AlertTriangle } from "lucide-react";
import { badgeVariants as motionBadgeVariants } from "@/design-system/micro-interactions";

// =============================================================================
// CVA Variants
// =============================================================================

/**
 * Confidence indicator variants based on confidence level
 */
// eslint-disable-next-line react-refresh/only-export-components
export const confidenceIndicatorVariants = cva(
  "inline-flex items-center",
  {
    variants: {
      level: {
        high: "text-success-10",
        medium: "text-warning-9",
        low: "text-error-10",
      },
      size: {
        compact: "",
        full: "gap-1 text-sm",
      },
    },
    defaultVariants: {
      level: "high",
      size: "full",
    },
  },
);

/**
 * Warning badge variant for low confidence
 */
// eslint-disable-next-line react-refresh/only-export-components
export const warningBadgeVariants = cva(
  "inline-flex items-center gap-1 px-2 py-0.5 rounded text-xs",
  {
    variants: {
      variant: {
        default: "bg-warning-3 text-warning-10 dark:text-warning-11",
      },
    },
    defaultVariants: {
      variant: "default",
    },
  },
);

export interface ConfidenceIndicatorProps {
  /** Confidence score (0-1) */
  score: number;
  /** Compact mode - only shows visual indicator without text */
  compact?: boolean;
}

/**
 * Get confidence level category
 */
function getConfidenceLevel(score: number): "high" | "medium" | "low" {
  if (score >= 0.8) return "high";
  if (score >= 0.6) return "medium";
  return "low";
}


/**
 * Clamp score to valid range [0, 1]
 */
function clampScore(score: number): number {
  return Math.max(0, Math.min(1, score));
}

/**
 * ConfidenceIndicator component for displaying AI response confidence.
 *
 * @example
 * ```tsx
 * // In a chat message
 * <ChatMessage>
 *   <MessageContent>{content}</MessageContent>
 *   <ConfidenceIndicator score={0.92} />
 * </ChatMessage>
 *
 * // Compact mode
 * <ConfidenceIndicator score={0.85} compact />
 * ```
 */
export function ConfidenceIndicator({
  score,
  compact = false,
}: ConfidenceIndicatorProps) {
  const prefersReducedMotion = useReducedMotion();
  const clampedScore = clampScore(score);
  const percentage = Math.round(clampedScore * 100);
  const level = getConfidenceLevel(clampedScore);
  const showWarning = clampedScore < 0.7;

  const ariaLabel = `AI confidence: ${percentage}%, ${level} confidence`;

  if (compact) {
    return (
      <motion.div
        data-testid="confidence-indicator"
        className={confidenceIndicatorVariants({ level, size: "compact" })}
        title={`Confidence: ${percentage}%`}
        aria-label={ariaLabel}
        variants={prefersReducedMotion ? undefined : motionBadgeVariants}
        initial="hidden"
        animate="visible"
      >
        <svg className="w-3 h-3" viewBox="0 0 12 12" fill="currentColor">
          <circle cx="6" cy="6" r="5" opacity="0.2" />
          <circle cx="6" cy="6" r="3" />
        </svg>
      </motion.div>
    );
  }

  return (
    <div className="inline-flex items-center gap-2">
      <motion.div
        data-testid="confidence-indicator"
        className={confidenceIndicatorVariants({ level, size: "full" })}
        aria-label={ariaLabel}
        variants={prefersReducedMotion ? undefined : motionBadgeVariants}
        initial="hidden"
        animate="visible"
      >
        <svg className="w-3 h-3" viewBox="0 0 12 12" fill="currentColor">
          <circle cx="6" cy="6" r="5" opacity="0.2" />
          <circle cx="6" cy="6" r="3" />
        </svg>
        <span>{percentage}%</span>
      </motion.div>

      {showWarning && (
        <motion.div
          className={warningBadgeVariants({ variant: "default" })}
          variants={prefersReducedMotion ? undefined : motionBadgeVariants}
          initial="hidden"
          animate="visible"
        >
          <AlertTriangle
            data-testid="warning-icon"
            className="w-3 h-3"
            aria-hidden="true"
          />
          <span>Low confidence - verify this information</span>
        </motion.div>
      )}
    </div>
  );
}

export default ConfidenceIndicator;
