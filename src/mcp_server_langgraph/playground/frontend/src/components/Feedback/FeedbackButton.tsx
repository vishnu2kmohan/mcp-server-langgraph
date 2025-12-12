/**
 * FeedbackButton Component
 *
 * Floating feedback button with quick satisfaction rating.
 * Fixes HEART Framework "Happiness" dimension.
 */

import React, { useState, useCallback } from 'react';
import clsx from 'clsx';

export interface FeedbackButtonProps {
  onSubmit?: (feedback: FeedbackData) => void;
  position?: 'bottom-right' | 'bottom-left';
}

export interface FeedbackData {
  rating: 1 | 2 | 3 | 4 | 5;
  comment?: string;
  timestamp: string;
  page: string;
}

const RATING_EMOJIS = ['😞', '😕', '😐', '🙂', '😊'] as const;
const RATING_LABELS = ['Very Unhappy', 'Unhappy', 'Neutral', 'Happy', 'Very Happy'] as const;

export function FeedbackButton({
  onSubmit,
  position = 'bottom-right',
}: FeedbackButtonProps): React.ReactElement {
  const [isOpen, setIsOpen] = useState(false);
  const [selectedRating, setSelectedRating] = useState<number | null>(null);
  const [comment, setComment] = useState('');
  const [isSubmitted, setIsSubmitted] = useState(false);

  const handleToggle = useCallback(() => {
    setIsOpen((prev) => !prev);
    if (isSubmitted) {
      setIsSubmitted(false);
      setSelectedRating(null);
      setComment('');
    }
  }, [isSubmitted]);

  const handleSubmit = useCallback(() => {
    if (selectedRating === null) return;

    const feedback: FeedbackData = {
      rating: (selectedRating + 1) as 1 | 2 | 3 | 4 | 5,
      comment: comment.trim() || undefined,
      timestamp: new Date().toISOString(),
      page: window.location.pathname,
    };

    onSubmit?.(feedback);
    setIsSubmitted(true);

    // Auto-close after 2 seconds
    setTimeout(() => {
      setIsOpen(false);
      setIsSubmitted(false);
      setSelectedRating(null);
      setComment('');
    }, 2000);
  }, [selectedRating, comment, onSubmit]);

  const positionClasses = position === 'bottom-right' ? 'right-4' : 'left-4';

  return (
    <div className={clsx('fixed bottom-4 z-40', positionClasses)}>
      {/* Feedback Panel */}
      {isOpen && (
        <div
          className={clsx(
            'mb-3 w-72 bg-white dark:bg-dark-surface',
            'rounded-lg shadow-xl border border-gray-200 dark:border-dark-border',
            'animate-in slide-in-from-bottom-2 duration-200'
          )}
        >
          <div className="p-4">
            {isSubmitted ? (
              <div className="text-center py-4">
                <div className="text-4xl mb-2">🙏</div>
                <h3 className="font-medium text-gray-900 dark:text-dark-text">
                  Thanks for your feedback!
                </h3>
                <p className="text-sm text-gray-500 dark:text-dark-textMuted mt-1">
                  We appreciate your input.
                </p>
              </div>
            ) : (
              <>
                <h3 className="font-medium text-gray-900 dark:text-dark-text mb-3">
                  How's your experience?
                </h3>

                {/* Rating buttons */}
                <div className="flex justify-between mb-4">
                  {RATING_EMOJIS.map((emoji, idx) => (
                    <button
                      key={idx}
                      onClick={() => setSelectedRating(idx)}
                      className={clsx(
                        'w-10 h-10 text-2xl rounded-lg transition-all',
                        'hover:bg-gray-100 dark:hover:bg-dark-hover',
                        selectedRating === idx
                          ? 'bg-primary-100 dark:bg-primary-900/30 ring-2 ring-primary-500'
                          : ''
                      )}
                      title={RATING_LABELS[idx]}
                      aria-label={RATING_LABELS[idx]}
                    >
                      {emoji}
                    </button>
                  ))}
                </div>

                {/* Comment input (appears after rating) */}
                {selectedRating !== null && (
                  <div className="space-y-3 animate-in fade-in duration-200">
                    <textarea
                      value={comment}
                      onChange={(e) => setComment(e.target.value)}
                      placeholder="Any additional feedback? (optional)"
                      className={clsx(
                        'w-full px-3 py-2 text-sm rounded-lg resize-none',
                        'bg-gray-50 dark:bg-dark-bg',
                        'border border-gray-200 dark:border-dark-border',
                        'text-gray-900 dark:text-dark-text',
                        'placeholder-gray-400 dark:placeholder-dark-textMuted',
                        'focus:outline-none focus:ring-2 focus:ring-primary-500'
                      )}
                      rows={3}
                    />
                    <button
                      onClick={handleSubmit}
                      className={clsx(
                        'w-full px-4 py-2 rounded-lg font-medium text-sm',
                        'bg-primary-600 text-white',
                        'hover:bg-primary-700',
                        'focus:outline-none focus:ring-2 focus:ring-primary-500'
                      )}
                    >
                      Submit Feedback
                    </button>
                  </div>
                )}
              </>
            )}
          </div>
        </div>
      )}

      {/* Floating Button */}
      <button
        onClick={handleToggle}
        className={clsx(
          'w-12 h-12 rounded-full shadow-lg',
          'bg-primary-600 text-white',
          'hover:bg-primary-700',
          'focus:outline-none focus:ring-2 focus:ring-primary-500 focus:ring-offset-2',
          'flex items-center justify-center',
          'transition-transform hover:scale-105'
        )}
        aria-label={isOpen ? 'Close feedback' : 'Give feedback'}
        aria-expanded={isOpen}
      >
        {isOpen ? (
          <svg className="w-5 h-5" fill="none" viewBox="0 0 24 24" stroke="currentColor">
            <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M6 18L18 6M6 6l12 12" />
          </svg>
        ) : (
          <svg className="w-5 h-5" fill="none" viewBox="0 0 24 24" stroke="currentColor">
            <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M8 12h.01M12 12h.01M16 12h.01M21 12c0 4.418-4.03 8-9 8a9.863 9.863 0 01-4.255-.949L3 20l1.395-3.72C3.512 15.042 3 13.574 3 12c0-4.418 4.03-8 9-8s9 3.582 9 8z" />
          </svg>
        )}
      </button>
    </div>
  );
}
