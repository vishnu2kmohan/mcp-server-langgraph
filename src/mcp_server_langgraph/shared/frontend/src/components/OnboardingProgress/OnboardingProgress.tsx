/**
 * OnboardingProgress Component
 *
 * Visual checklist for tracking onboarding progress.
 * Persists completed steps to localStorage.
 */

import React, { ReactElement, useState, useCallback, useMemo, useEffect } from 'react';

// =============================================================================
// Types
// =============================================================================

export interface OnboardingStep {
  /** Unique identifier for this step */
  id: string;
  /** Step title */
  title: string;
  /** Step description */
  description: string;
  /** Optional action to perform when step is clicked */
  action?: () => void;
}

export interface OnboardingProgressProps {
  /** List of onboarding steps */
  steps: OnboardingStep[];
  /** Title for the onboarding section */
  title: string;
  /** Callback when a step is completed */
  onStepComplete?: (stepId: string) => void;
  /** Callback when all steps are completed */
  onAllComplete?: () => void;
  /** Callback when dismissed */
  onDismiss?: () => void;
  /** Additional CSS classes */
  className?: string;
}

export interface UseOnboardingResult {
  /** Check if a step is completed */
  isCompleted: (stepId: string) => boolean;
  /** Mark a step as completed */
  completeStep: (stepId: string) => void;
  /** Progress percentage (0-100) */
  progress: number;
  /** Number of completed steps */
  completedCount: number;
  /** Total number of steps */
  totalCount: number;
  /** Whether all steps are complete */
  isAllComplete: boolean;
  /** Reset all progress */
  reset: () => void;
}

// =============================================================================
// Constants
// =============================================================================

const STORAGE_KEY = 'onboarding_completed';

// =============================================================================
// Helper Functions
// =============================================================================

function clsx(...classes: (string | undefined | boolean)[]): string {
  return classes.filter(Boolean).join(' ');
}

function getCompletedSteps(): string[] {
  try {
    const stored = localStorage.getItem(STORAGE_KEY);
    return stored ? JSON.parse(stored) : [];
  } catch {
    return [];
  }
}

function saveCompletedSteps(completed: string[]): void {
  try {
    localStorage.setItem(STORAGE_KEY, JSON.stringify(completed));
  } catch {
    // Ignore storage errors
  }
}

// =============================================================================
// useOnboarding Hook
// =============================================================================

export function useOnboarding(steps: OnboardingStep[]): UseOnboardingResult {
  const [completedIds, setCompletedIds] = useState<string[]>(() => getCompletedSteps());

  const isCompleted = useCallback((stepId: string) => {
    return completedIds.includes(stepId);
  }, [completedIds]);

  const completeStep = useCallback((stepId: string) => {
    setCompletedIds((prev) => {
      if (prev.includes(stepId)) return prev;
      const updated = [...prev, stepId];
      saveCompletedSteps(updated);
      return updated;
    });
  }, []);

  const progress = useMemo(() => {
    if (steps.length === 0) return 0;
    return (completedIds.length / steps.length) * 100;
  }, [completedIds.length, steps.length]);

  const isAllComplete = useMemo(() => {
    return steps.length > 0 && completedIds.length >= steps.length;
  }, [completedIds.length, steps.length]);

  const reset = useCallback(() => {
    setCompletedIds([]);
    saveCompletedSteps([]);
  }, []);

  return {
    isCompleted,
    completeStep,
    progress,
    completedCount: completedIds.length,
    totalCount: steps.length,
    isAllComplete,
    reset,
  };
}

// =============================================================================
// OnboardingProgress Component
// =============================================================================

export function OnboardingProgress({
  steps,
  title,
  onStepComplete,
  onAllComplete,
  onDismiss,
  className,
}: OnboardingProgressProps): ReactElement | null {
  const [isDismissed, setIsDismissed] = useState(false);
  const { isCompleted, completeStep, progress, completedCount, totalCount, isAllComplete } = useOnboarding(steps);

  const handleStepClick = useCallback((stepId: string) => {
    const wasComplete = isCompleted(stepId);
    if (!wasComplete) {
      completeStep(stepId);
      onStepComplete?.(stepId);
    }
  }, [completeStep, isCompleted, onStepComplete]);

  // Check if all complete after render
  useEffect(() => {
    if (isAllComplete && onAllComplete) {
      onAllComplete();
    }
  }, [isAllComplete, onAllComplete]);

  const handleDismiss = useCallback(() => {
    setIsDismissed(true);
    onDismiss?.();
  }, [onDismiss]);

  if (isDismissed) {
    return null;
  }

  const progressPercent = Math.round(progress);

  return (
    <section
      role="region"
      aria-label={title}
      className={clsx(
        'rounded-lg border p-4',
        'bg-white dark:bg-gray-800',
        'border-gray-200 dark:border-gray-700',
        className
      )}
    >
      {/* Header */}
      <div className="flex items-center justify-between mb-4">
        <h3 className="text-lg font-semibold text-gray-900 dark:text-white">
          {title}
        </h3>
        <button
          type="button"
          onClick={handleDismiss}
          aria-label="Dismiss onboarding"
          className={clsx(
            'text-gray-400 hover:text-gray-600',
            'dark:text-gray-500 dark:hover:text-gray-300',
            'focus:outline-none focus:ring-2 focus:ring-offset-2 focus:ring-blue-500'
          )}
        >
          <svg className="w-5 h-5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
            <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M6 18L18 6M6 6l12 12" />
          </svg>
          <span className="sr-only">Dismiss</span>
        </button>
      </div>

      {/* Progress Bar */}
      <div className="mb-4">
        <div className="flex items-center justify-between text-sm mb-1">
          <span className="text-gray-600 dark:text-gray-400">
            {completedCount} of {totalCount} completed
          </span>
          <span className="text-gray-600 dark:text-gray-400">
            {progressPercent}%
          </span>
        </div>
        <div
          role="progressbar"
          aria-valuenow={progressPercent}
          aria-valuemin={0}
          aria-valuemax={100}
          className="h-2 bg-gray-200 dark:bg-gray-700 rounded-full overflow-hidden"
        >
          <div
            className="h-full bg-blue-500 transition-all duration-300"
            style={{ width: `${progressPercent}%` }}
          />
        </div>
      </div>

      {/* Steps List */}
      <ul className="space-y-3">
        {steps.map((step) => {
          const completed = isCompleted(step.id);
          return (
            <li key={step.id}>
              <button
                type="button"
                onClick={() => handleStepClick(step.id)}
                aria-checked={completed}
                className={clsx(
                  'w-full flex items-start gap-3 p-3 rounded-lg text-left',
                  'transition-colors duration-150',
                  completed
                    ? 'bg-green-50 dark:bg-green-900/20'
                    : 'bg-gray-50 dark:bg-gray-700/50 hover:bg-gray-100 dark:hover:bg-gray-700'
                )}
              >
                {/* Checkbox Icon */}
                <span className={clsx(
                  'flex-shrink-0 w-5 h-5 rounded-full border-2 flex items-center justify-center mt-0.5',
                  completed
                    ? 'bg-green-500 border-green-500 text-white'
                    : 'border-gray-300 dark:border-gray-600'
                )}>
                  {completed && (
                    <svg className="w-3 h-3" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                      <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={3} d="M5 13l4 4L19 7" />
                    </svg>
                  )}
                </span>

                {/* Step Content */}
                <div>
                  <span className={clsx(
                    'font-medium',
                    completed
                      ? 'text-green-700 dark:text-green-300 line-through'
                      : 'text-gray-900 dark:text-white'
                  )}>
                    {step.title}
                  </span>
                  <p className={clsx(
                    'text-sm mt-0.5',
                    completed
                      ? 'text-green-600 dark:text-green-400'
                      : 'text-gray-500 dark:text-gray-400'
                  )}>
                    {step.description}
                  </p>
                </div>
              </button>
            </li>
          );
        })}
      </ul>
    </section>
  );
}

// =============================================================================
// Exports
// =============================================================================

export default OnboardingProgress;
