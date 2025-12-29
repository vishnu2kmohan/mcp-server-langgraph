/**
 * NPSSurvey Component
 *
 * Net Promoter Score survey for measuring user satisfaction.
 * Scale: 0-10, where 0-6 = Detractors, 7-8 = Passives, 9-10 = Promoters
 */

import React, { useState, useCallback } from 'react';
import clsx from 'clsx';

export interface NPSSurveyProps {
  onSubmit: (score: number) => void;
  onDismiss?: () => void;
  question?: string;
}

const SCORES = [0, 1, 2, 3, 4, 5, 6, 7, 8, 9, 10] as const;

function getScoreColor(score: number, isSelected: boolean): string {
  if (!isSelected) return 'bg-gray-100 dark:bg-dark-surface hover:bg-gray-200 dark:hover:bg-dark-surfaceHover';

  // Detractors (0-6): Red
  if (score <= 6) return 'bg-error-500 text-white';
  // Passives (7-8): Yellow
  if (score <= 8) return 'bg-warning-500 text-white';
  // Promoters (9-10): Green
  return 'bg-primary-600 text-white';
}

export function NPSSurvey({
  onSubmit,
  onDismiss,
  question = 'How likely are you to recommend this tool to a colleague?',
}: NPSSurveyProps): React.ReactElement {
  const [selectedScore, setSelectedScore] = useState<number | null>(null);

  const handleSubmit = useCallback(() => {
    if (selectedScore !== null) {
      onSubmit(selectedScore);
    }
  }, [selectedScore, onSubmit]);

  return (
    <div className="p-4 bg-white dark:bg-dark-surface rounded-lg shadow-lg border border-gray-200 dark:border-dark-border">
      {/* Question */}
      <fieldset role="group" aria-label="NPS Survey">
        <legend className="text-sm font-medium text-gray-900 dark:text-dark-text mb-4">
          {question}
        </legend>

        {/* Score Buttons */}
        <div className="flex gap-1 mb-2">
          {SCORES.map((score) => (
            <button
              key={score}
              type="button"
              onClick={() => setSelectedScore(score)}
              aria-label={String(score)}
              aria-pressed={selectedScore === score}
              className={clsx(
                'flex-1 py-2 text-sm font-medium rounded transition-colors',
                'focus:outline-none focus:ring-2 focus:ring-primary-500 focus:ring-offset-2',
                getScoreColor(score, selectedScore === score)
              )}
            >
              {score}
            </button>
          ))}
        </div>

        {/* Scale Labels */}
        <div className="flex justify-between text-xs text-gray-500 dark:text-dark-textMuted mb-4">
          <span>Not likely</span>
          <span>Extremely likely</span>
        </div>
      </fieldset>

      {/* Actions */}
      <div className="flex gap-2">
        <button
          onClick={handleSubmit}
          disabled={selectedScore === null}
          className={clsx(
            'flex-1 px-4 py-2 rounded-lg font-medium transition-colors',
            'bg-primary-600 text-white',
            'hover:bg-primary-700',
            'disabled:opacity-50 disabled:cursor-not-allowed',
            'focus:outline-none focus:ring-2 focus:ring-primary-500 focus:ring-offset-2'
          )}
        >
          Submit Feedback
        </button>
        {onDismiss && (
          <button
            onClick={onDismiss}
            className={clsx(
              'px-4 py-2 rounded-lg font-medium transition-colors',
              'bg-gray-100 dark:bg-dark-border text-gray-700 dark:text-dark-text',
              'hover:bg-gray-200 dark:hover:bg-dark-surfaceHover',
              'focus:outline-none focus:ring-2 focus:ring-gray-500 focus:ring-offset-2'
            )}
            aria-label="Skip"
          >
            Skip
          </button>
        )}
      </div>
    </div>
  );
}
