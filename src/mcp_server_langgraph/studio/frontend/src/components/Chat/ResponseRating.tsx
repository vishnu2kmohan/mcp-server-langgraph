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
 */

import { useState, useCallback } from "react";
import { ThumbsUp, ThumbsDown, Loader2, Send } from "lucide-react";

import { Button, Input } from "@/components/UI";

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
  const [feedbackText, setFeedbackText] = useState("");

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
        <Button
          className="p-1.5 rounded-lg focus:ring-primary-500/50"
          data-testid="rating-thumbs-up"
          type="button"
          onClick={() => handleRate("up")}
          onKeyDown={(e) => handleKeyDown(e, "up")}
          disabled={isSubmitting}
          aria-label="Rate as helpful"
          aria-pressed={currentRating === "up"}
        >
          <ThumbsUp size={iconSize} />
        </Button>

        {/* Thumbs Down */}
        <Button
          className="p-1.5 rounded-lg focus:ring-primary-500/50"
          data-testid="rating-thumbs-down"
          type="button"
          onClick={() => handleRate("down")}
          onKeyDown={(e) => handleKeyDown(e, "down")}
          disabled={isSubmitting}
          aria-label="Rate as not helpful"
          aria-pressed={currentRating === "down"}
        >
          <ThumbsDown size={iconSize} />
        </Button>

        {/* Loading indicator */}
        {isSubmitting && (
          <span data-testid="rating-loading" className="ml-1">
            <Loader2
              size={iconSize}
              className="animate-spin text-neutral-400 dark:text-neutral-400"
            />
          </span>
        )}

        {/* Thank you message */}
        {showThankYou && currentRating && !isSubmitting && (
          <span className="text-xs text-neutral-500 dark:text-neutral-400 ml-1">
            Thank you for your feedback!
          </span>
        )}
      </div>
      {/* Feedback input for negative ratings */}
      {showFeedbackInput && currentRating === "down" && onFeedback && (
        <div className="flex items-center gap-2">
          <Input
            className="flex-1 px-3 py-1.5 text-sm focus:ring-primary-500/50 text-neutral-700 dark:text-neutral-300 text-neutral-400 dark:text-neutral-400 dark:placeholder:text-neutral-500"
            data-testid="feedback-input"
            value={feedbackText}
            onChange={(e) => setFeedbackText(e.target.value)}
            onKeyDown={handleFeedbackKeyDown}
            placeholder="What went wrong?"
          />
          <Button
            variant="primary"
            className="p-1.5 rounded-lg text-primary-600 dark:text-primary-400 hover:bg-primary-50 dark:hover:bg-primary-900/20"
            data-testid="submit-feedback"
            type="button"
            onClick={handleSubmitFeedback}
            disabled={!feedbackText.trim()}
          >
            <Send size={16} />
          </Button>
        </div>
      )}
    </div>
  );
}

export default ResponseRating;
