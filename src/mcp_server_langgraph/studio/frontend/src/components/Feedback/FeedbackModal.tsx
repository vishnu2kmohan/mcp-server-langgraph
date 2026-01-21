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

import { Button, Textarea } from "@/components/UI";

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
        className="fixed inset-0 z-50 flex items-center justify-center bg-neutral-a6"
      >
        <div className="bg-neutral-1 rounded-lg shadow-xl w-full max-w-md p-6 mx-4">
          <div className="flex flex-col items-center text-center">
            <CheckCircle className="w-16 h-16 text-success-9 mb-4" />
            <h2 className="text-xl font-semibold text-neutral-12 mb-2">
              Thank You!
            </h2>
            <p className="text-neutral-11 mb-6">
              Your feedback helps us improve.
            </p>
            <Button
              variant="primary"
              size="lg"
              className="px-6 py-2 bg-primary-10 text-neutral-12 rounded-lg hover:bg-primary-11"
              onClick={onClose}
            >
              Done
            </Button>
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
      className="fixed inset-0 z-50 flex items-center justify-center bg-neutral-a6"
    >
      <div className="bg-neutral-1 rounded-lg shadow-xl w-full max-w-lg p-6 mx-4">
        {/* Header */}
        <div className="flex items-center justify-between mb-6">
          <h2
            id="feedback-modal-title"
            className="text-xl font-semibold text-neutral-12"
          >
            Share Your Feedback
          </h2>
          <Button size="icon"
            variant="secondary"
            className="p-1 hover:bg-neutral-2 rounded"
            data-testid="close-feedback-modal"
            onClick={onClose}
          >
            <X size={20} className="text-neutral-10" />
          </Button>
        </div>

        {/* NPS Section */}
        <div className="mb-6">
          <label className="block text-sm font-medium text-neutral-11 mb-3">
            How likely are you to recommend this product to a colleague?
          </label>
          <div className="flex flex-wrap gap-2 justify-center">
            {[0, 1, 2, 3, 4, 5, 6, 7, 8, 9, 10].map((score) => (
              <Button
                variant="primary"
                className="w-10 h-10 rounded-lg"
                key={score}
                data-testid={`nps-score-${score}`}
                onClick={() => setNpsScore(score)}>
                {score}
              </Button>
            ))}
          </div>
          <div className="flex justify-between mt-2 text-xs text-neutral-10">
            <span>Not likely</span>
            <span>Very likely</span>
          </div>
        </div>

        {/* CSAT Section */}
        <div className="mb-6">
          <label className="block text-sm font-medium text-neutral-11 mb-3">
            How would you rate your overall satisfaction?
          </label>
          <div className="flex justify-center gap-2">
            {[1, 2, 3, 4, 5].map((star) => (
              <Button
                variant="ghost"
                className="p-2"
                key={star}
                data-testid={`csat-star-${star}`}
                onClick={() => setCsatRating(star)}>
                <Star
                  size={32}
                  fill={
                    csatRating !== null && star <= csatRating
                      ? "currentColor"
                      : "none"
                  }
                />
              </Button>
            ))}
          </div>
        </div>

        {/* Comment Section */}
        <div className="mb-6">
          <label className="block text-sm font-medium text-neutral-11 mb-2">
            Additional comments (optional)
          </label>
          <Textarea
            className="px-3 py-2 text-neutral-12 focus:ring-primary-7"
            value={comment}
            onChange={(e) => setComment(e.target.value)}
            placeholder="Share any additional comments or suggestions..."
            rows={3}
          />
        </div>

        {/* Submit Button */}
        <div className="flex justify-end">
          <Button
            variant="primary"
            size="lg"
            className="px-6 py-2 bg-primary-10 text-neutral-12 rounded-lg hover:bg-primary-11 flex"
            onClick={handleSubmit}
            disabled={!canSubmit || isLoading}
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
          </Button>
        </div>
      </div>
    </div>
  );
}
