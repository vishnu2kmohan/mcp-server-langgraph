/**
 * ResponseRating Component
 *
 * Thumbs up/down feedback component that allows users to rate AI responses.
 * Useful for collecting quality feedback to improve model performance.
 *
 * Features:
 * - Thumbs up/down rating
 * - Optional feedback text input for negative ratings
 * - Loading state during submission
 * - Thank you message after rating
 *
 * Design System Compliance:
 * - Uses CVA for rating button variants
 * - Uses Motion.dev for button press feedback
 * - Implements useReducedMotion() for accessibility
 * - Uses semantic colors per STYLE.md
 */

import { useState, useCallback } from "react";
import { motion, useReducedMotion } from "motion/react";
import { cva } from "class-variance-authority";
import { ThumbsUp, ThumbsDown, Loader2, Send } from "lucide-react";
import { buttonVariants as motionButtonVariants } from "@/design-system/micro-interactions";

import { Input } from "@/components/UI";

// =============================================================================
// CVA Variants
// =============================================================================

/**
 * Rating button variants for thumbs up/down
 */
// eslint-disable-next-line react-refresh/only-export-components
export const ratingButtonVariants = cva(
  "p-1.5 rounded-lg focus:ring-primary-a6 transition-colors",
  {
    variants: {
      state: {
        default: "text-neutral-9 hover:text-neutral-11 hover:bg-neutral-3",
        selected_up: "text-success-9 bg-success-3 hover:bg-success-4",
        selected_down: "text-error-9 bg-error-3 hover:bg-error-4",
        disabled: "text-neutral-7 cursor-not-allowed",
      },
      size: {
        compact: "p-1",
        normal: "p-1.5",
      },
    },
    defaultVariants: {
      state: "default",
      size: "normal",
    },
  },
);

/**
 * Feedback submit button variant
 */
// eslint-disable-next-line react-refresh/only-export-components
export const feedbackButtonVariants = cva(
  "p-1.5 rounded-lg transition-colors",
  {
    variants: {
      variant: {
        default: "text-primary-10 dark:text-primary-11 hover:bg-primary-1 dark:hover:bg-primary-a3",
        disabled: "text-neutral-7 cursor-not-allowed",
      },
    },
    defaultVariants: {
      variant: "default",
    },
  },
);

// =============================================================================
// Types
// =============================================================================

export type RatingValue = "up" | "down" | null;

export interface ResponseRatingProps {
  /** The message ID being rated */
  messageId: string;
  /** Callback when a rating is submitted */
  onRate: (messageId: string, rating: RatingValue) => void;
  /** Current rating value */
  currentRating?: RatingValue;
  /** Whether to show the feedback text input for negative ratings */
  showFeedbackInput?: boolean;
  /** Callback when feedback text is submitted */
  onFeedback?: (messageId: string, feedback: string) => void;
  /** Whether the rating is being submitted */
  isSubmitting?: boolean;
  /** Whether to show a thank you message after rating */
  showThankYou?: boolean;
  /** Compact mode for smaller display */
  compact?: boolean;
  /** Additional CSS classes */
  className?: string;
}

// =============================================================================
// Component
// =============================================================================

export function ResponseRating({
  messageId,
  onRate,
  currentRating,
  showFeedbackInput = false,
  onFeedback,
  isSubmitting = false,
  showThankYou = false,
  compact = false,
  className = "",
}: ResponseRatingProps) {
  const prefersReducedMotion = useReducedMotion();
  const [feedbackText, setFeedbackText] = useState("");

  const getButtonState = (rating: "up" | "down") => {
    if (isSubmitting) return "disabled" as const;
    if (currentRating === rating) return rating === "up" ? "selected_up" as const : "selected_down" as const;
    return "default" as const;
  };

  const handleRate = useCallback(
    (rating: "up" | "down") => {
      // If clicking the same rating, remove it
      const newRating = currentRating === rating ? null : rating;
      onRate(messageId, newRating);
    },
    [messageId, currentRating, onRate],
  );

  const handleKeyDown = useCallback(
    (e: React.KeyboardEvent, rating: "up" | "down") => {
      if (e.key === "Enter" || e.key === " ") {
        e.preventDefault();
        handleRate(rating);
      }
    },
    [handleRate],
  );

  const handleSubmitFeedback = useCallback(() => {
    if (feedbackText.trim() && onFeedback) {
      onFeedback(messageId, feedbackText.trim());
      setFeedbackText("");
    }
  }, [messageId, feedbackText, onFeedback]);

  const handleFeedbackKeyDown = useCallback(
    (e: React.KeyboardEvent) => {
      if (e.key === "Enter" && !e.shiftKey) {
        e.preventDefault();
        handleSubmitFeedback();
      }
    },
    [handleSubmitFeedback],
  );

  const iconSize = compact ? 14 : 16;

  return (
    <div
      data-testid="response-rating-container"
      className={`flex flex-col ${compact ? "gap-1" : "gap-2"} ${className}`}
    >
      <div className={`flex items-center ${compact ? "gap-1" : "gap-2"}`}>
        {/* Thumbs Up */}
        <motion.button
          className={ratingButtonVariants({
            state: getButtonState("up"),
            size: compact ? "compact" : "normal",
          })}
          data-testid="rating-thumbs-up"
          type="button"
          onClick={() => handleRate("up")}
          onKeyDown={(e) => handleKeyDown(e, "up")}
          disabled={isSubmitting}
          aria-label="Rate as helpful"
          aria-pressed={currentRating === "up"}
          variants={prefersReducedMotion ? undefined : motionButtonVariants}
          initial="rest"
          whileHover={isSubmitting ? undefined : "hover"}
          whileTap={isSubmitting ? undefined : "pressed"}
        >
          <ThumbsUp size={iconSize} />
        </motion.button>

        {/* Thumbs Down */}
        <motion.button
          className={ratingButtonVariants({
            state: getButtonState("down"),
            size: compact ? "compact" : "normal",
          })}
          data-testid="rating-thumbs-down"
          type="button"
          onClick={() => handleRate("down")}
          onKeyDown={(e) => handleKeyDown(e, "down")}
          disabled={isSubmitting}
          aria-label="Rate as not helpful"
          aria-pressed={currentRating === "down"}
          variants={prefersReducedMotion ? undefined : motionButtonVariants}
          initial="rest"
          whileHover={isSubmitting ? undefined : "hover"}
          whileTap={isSubmitting ? undefined : "pressed"}
        >
          <ThumbsDown size={iconSize} />
        </motion.button>

        {/* Loading indicator */}
        {isSubmitting && (
          <span data-testid="rating-loading" className="ml-1">
            <Loader2
              size={iconSize}
              className="animate-spin text-neutral-9"
            />
          </span>
        )}

        {/* Thank you message */}
        {showThankYou && currentRating && !isSubmitting && (
          <span className="text-xs text-neutral-10 ml-1">
            Thank you for your feedback!
          </span>
        )}
      </div>
      {/* Feedback input for negative ratings */}
      {showFeedbackInput && currentRating === "down" && onFeedback && (
        <div className="flex items-center gap-2">
          <Input
            className="flex-1 px-3 py-1.5 text-sm focus:ring-primary-a6 text-neutral-11 text-neutral-9 dark:placeholder:text-neutral-10"
            data-testid="feedback-input"
            value={feedbackText}
            onChange={(e) => setFeedbackText(e.target.value)}
            onKeyDown={handleFeedbackKeyDown}
            placeholder="What went wrong?"
          />
          <motion.button
            className={feedbackButtonVariants({
              variant: feedbackText.trim() ? "default" : "disabled",
            })}
            data-testid="submit-feedback"
            type="button"
            onClick={handleSubmitFeedback}
            disabled={!feedbackText.trim()}
            variants={prefersReducedMotion ? undefined : motionButtonVariants}
            initial="rest"
            whileHover={feedbackText.trim() ? "hover" : undefined}
            whileTap={feedbackText.trim() ? "pressed" : undefined}
          >
            <Send size={16} />
          </motion.button>
        </div>
      )}
    </div>
  );
}

export default ResponseRating;
