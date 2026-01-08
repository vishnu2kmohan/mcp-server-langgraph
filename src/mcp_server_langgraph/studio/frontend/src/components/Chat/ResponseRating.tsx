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
        <button
          data-testid="rating-thumbs-up"
          type="button"
          onClick={() => handleRate("up")}
          onKeyDown={(e) => handleKeyDown(e, "up")}
          disabled={isSubmitting}
          aria-label="Rate as helpful"
          aria-pressed={currentRating === "up"}
          className={`
            p-1.5 rounded-lg transition-colors
            focus:outline-none focus:ring-2 focus:ring-primary-500/50
            ${
              currentRating === "up"
                ? "text-success-500 bg-success-50 dark:bg-success-900/20"
                : "text-gray-400 dark:text-gray-400 hover:text-success-500 hover:bg-gray-100 dark:bg-gray-800 dark:hover:bg-gray-800"
            }
            ${isSubmitting ? "opacity-50 cursor-not-allowed" : "cursor-pointer"}
          `}
        >
          <ThumbsUp size={iconSize} />
        </button>

        {/* Thumbs Down */}
        <button
          data-testid="rating-thumbs-down"
          type="button"
          onClick={() => handleRate("down")}
          onKeyDown={(e) => handleKeyDown(e, "down")}
          disabled={isSubmitting}
          aria-label="Rate as not helpful"
          aria-pressed={currentRating === "down"}
          className={`
            p-1.5 rounded-lg transition-colors
            focus:outline-none focus:ring-2 focus:ring-primary-500/50
            ${
              currentRating === "down"
                ? "text-error-500 bg-error-50 dark:bg-error-900/20"
                : "text-gray-400 dark:text-gray-400 hover:text-error-500 hover:bg-gray-100 dark:bg-gray-800 dark:hover:bg-gray-800"
            }
            ${isSubmitting ? "opacity-50 cursor-not-allowed" : "cursor-pointer"}
          `}
        >
          <ThumbsDown size={iconSize} />
        </button>

        {/* Loading indicator */}
        {isSubmitting && (
          <span data-testid="rating-loading" className="ml-1">
            <Loader2
              size={iconSize}
              className="animate-spin text-gray-400 dark:text-gray-400"
            />
          </span>
        )}

        {/* Thank you message */}
        {showThankYou && currentRating && !isSubmitting && (
          <span className="text-xs text-gray-500 dark:text-gray-400 ml-1">
            Thank you for your feedback!
          </span>
        )}
      </div>

      {/* Feedback input for negative ratings */}
      {showFeedbackInput && currentRating === "down" && onFeedback && (
        <div className="flex items-center gap-2">
          <input
            data-testid="feedback-input"
            type="text"
            value={feedbackText}
            onChange={(e) => setFeedbackText(e.target.value)}
            onKeyDown={handleFeedbackKeyDown}
            placeholder="What went wrong?"
            className="flex-1 px-3 py-1.5 text-sm border rounded-lg
              bg-white dark:bg-gray-800
              border-gray-300 dark:border-gray-600
              focus:outline-none focus:ring-2 focus:ring-primary-500/50
              text-gray-700 dark:text-gray-300
              placeholder:text-gray-400 dark:text-gray-400 dark:placeholder:text-gray-500"
          />
          <button
            data-testid="submit-feedback"
            type="button"
            onClick={handleSubmitFeedback}
            disabled={!feedbackText.trim()}
            className="p-1.5 rounded-lg text-primary-600 dark:text-primary-400
              hover:bg-primary-50 dark:hover:bg-primary-900/20
              disabled:opacity-50 disabled:cursor-not-allowed
              transition-colors"
          >
            <Send size={16} />
          </button>
        </div>
      )}
    </div>
  );
}

export default ResponseRating;
