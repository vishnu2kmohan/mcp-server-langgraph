/**
 * FeedbackModal Component
 *
 * Modal for collecting NPS (Net Promoter Score) and CSAT (Customer Satisfaction)
 * feedback from users. Supports 0-10 NPS scale, 1-5 star CSAT rating, and
 * optional comments.
 */

import { useState } from "react";
import { X, Star, Loader2, CheckCircle } from "lucide-react";
import { useSubmitFeedbackMutation } from "../../api";

export interface FeedbackModalProps {
  isOpen: boolean;
  onClose: () => void;
}

export function FeedbackModal({ isOpen, onClose }: FeedbackModalProps) {
  const [npsScore, setNpsScore] = useState<number | null>(null);
  const [csatRating, setCsatRating] = useState<number | null>(null);
  const [comment, setComment] = useState("");

  const [submitFeedback, { isLoading, isSuccess }] =
    useSubmitFeedbackMutation();

  const handleSubmit = async () => {
    if (npsScore === null && csatRating === null) return;

    await submitFeedback({
      nps_score: npsScore ?? undefined,
      csat_rating: csatRating ?? undefined,
      comment: comment || undefined,
    }).unwrap();
  };

  const canSubmit = npsScore !== null || csatRating !== null;

  if (!isOpen) {
    return null;
  }

  // Success state
  if (isSuccess) {
    return (
      <div
        data-testid="feedback-modal"
        role="dialog"
        aria-labelledby="feedback-modal-title"
        className="fixed inset-0 z-50 flex items-center justify-center bg-black/50"
      >
        <div className="bg-white dark:bg-gray-800 rounded-lg shadow-xl w-full max-w-md p-6 mx-4">
          <div className="flex flex-col items-center text-center">
            <CheckCircle className="w-16 h-16 text-success-500 mb-4" />
            <h2 className="text-xl font-semibold text-gray-900 dark:text-white mb-2">
              Thank You!
            </h2>
            <p className="text-gray-600 dark:text-gray-300 mb-6">
              Your feedback helps us improve.
            </p>
            <button
              onClick={onClose}
              className="px-6 py-2 bg-primary-600 text-white rounded-lg hover:bg-primary-700 transition-colors"
            >
              Done
            </button>
          </div>
        </div>
      </div>
    );
  }

  return (
    <div
      data-testid="feedback-modal"
      role="dialog"
      aria-labelledby="feedback-modal-title"
      className="fixed inset-0 z-50 flex items-center justify-center bg-black/50"
    >
      <div className="bg-white dark:bg-gray-800 rounded-lg shadow-xl w-full max-w-lg p-6 mx-4">
        {/* Header */}
        <div className="flex items-center justify-between mb-6">
          <h2
            id="feedback-modal-title"
            className="text-xl font-semibold text-gray-900 dark:text-white"
          >
            Share Your Feedback
          </h2>
          <button
            data-testid="close-feedback-modal"
            onClick={onClose}
            className="p-1 hover:bg-gray-100 dark:bg-gray-800 dark:hover:bg-gray-700 rounded"
          >
            <X size={20} className="text-gray-500 dark:text-gray-400" />
          </button>
        </div>

        {/* NPS Section */}
        <div className="mb-6">
          <label className="block text-sm font-medium text-gray-700 dark:text-gray-300 mb-3">
            How likely are you to recommend this product to a colleague?
          </label>
          <div className="flex flex-wrap gap-2 justify-center">
            {[0, 1, 2, 3, 4, 5, 6, 7, 8, 9, 10].map((score) => (
              <button
                key={score}
                data-testid={`nps-score-${score}`}
                onClick={() => setNpsScore(score)}
                className={`
                  w-10 h-10 rounded-lg font-medium transition-colors
                  ${
                    npsScore === score
                      ? "bg-primary-600 text-white"
                      : "bg-gray-100 dark:bg-gray-700 text-gray-700 dark:text-gray-300 hover:bg-gray-200 dark:bg-gray-700 dark:hover:bg-gray-600"
                  }
                `}
              >
                {score}
              </button>
            ))}
          </div>
          <div className="flex justify-between mt-2 text-xs text-gray-500 dark:text-gray-400">
            <span>Not likely</span>
            <span>Very likely</span>
          </div>
        </div>

        {/* CSAT Section */}
        <div className="mb-6">
          <label className="block text-sm font-medium text-gray-700 dark:text-gray-300 mb-3">
            How would you rate your overall satisfaction?
          </label>
          <div className="flex justify-center gap-2">
            {[1, 2, 3, 4, 5].map((star) => (
              <button
                key={star}
                data-testid={`csat-star-${star}`}
                onClick={() => setCsatRating(star)}
                className={`
                  p-2 transition-colors
                  ${
                    csatRating !== null && star <= csatRating
                      ? "text-warning-400"
                      : "text-gray-300 dark:text-gray-600 dark:text-gray-300 hover:text-warning-300"
                  }
                `}
              >
                <Star
                  size={32}
                  fill={
                    csatRating !== null && star <= csatRating
                      ? "currentColor"
                      : "none"
                  }
                />
              </button>
            ))}
          </div>
        </div>

        {/* Comment Section */}
        <div className="mb-6">
          <label className="block text-sm font-medium text-gray-700 dark:text-gray-300 mb-2">
            Additional comments (optional)
          </label>
          <textarea
            value={comment}
            onChange={(e) => setComment(e.target.value)}
            placeholder="Share any additional comments or suggestions..."
            rows={3}
            className="w-full px-3 py-2 border border-gray-300 dark:border-gray-600 rounded-lg
              bg-white dark:bg-gray-700 text-gray-900 dark:text-gray-100
              focus:ring-2 focus:ring-primary-500 focus:border-transparent"
          />
        </div>

        {/* Submit Button */}
        <div className="flex justify-end">
          <button
            onClick={handleSubmit}
            disabled={!canSubmit || isLoading}
            className="px-6 py-2 bg-primary-600 text-white rounded-lg hover:bg-primary-700
              disabled:opacity-50 disabled:cursor-not-allowed transition-colors
              flex items-center gap-2"
          >
            {isLoading ? (
              <>
                <Loader2
                  data-testid="submit-loading"
                  size={16}
                  className="animate-spin"
                />
                Submitting...
              </>
            ) : (
              "Submit Feedback"
            )}
          </button>
        </div>
      </div>
    </div>
  );
}
