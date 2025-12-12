/**
 * GuidedTour Component
 *
 * Step-by-step guided tour for onboarding users.
 * Supports navigation, progress indicators, and persistence.
 */

import React, { ReactElement, useState, useCallback, useEffect, useId } from 'react';

// =============================================================================
// Types
// =============================================================================

export interface TourStep {
  /** Unique identifier for this step */
  id: string;
  /** Step title */
  title: string;
  /** Step content/description */
  content: string;
  /** CSS selector for the target element to highlight */
  target?: string;
  /** Optional image URL */
  image?: string;
}

export interface GuidedTourProps {
  /** List of tour steps */
  steps: TourStep[];
  /** Whether the tour is open */
  isOpen: boolean;
  /** Callback when tour is closed */
  onClose: () => void;
  /** Callback when tour is completed */
  onComplete?: () => void;
  /** Callback when step changes */
  onStepChange?: (stepIndex: number, step: TourStep) => void;
  /** Initial step index */
  initialStep?: number;
  /** Unique ID for persistence */
  tourId?: string;
  /** Additional CSS classes */
  className?: string;
}

// =============================================================================
// Constants
// =============================================================================

const STORAGE_KEY = 'tours_completed';

// =============================================================================
// Helper Functions
// =============================================================================

function clsx(...classes: (string | undefined | boolean)[]): string {
  return classes.filter(Boolean).join(' ');
}

function getCompletedTours(): string[] {
  try {
    const stored = localStorage.getItem(STORAGE_KEY);
    return stored ? JSON.parse(stored) : [];
  } catch {
    return [];
  }
}

function markTourComplete(tourId: string): void {
  try {
    const completed = getCompletedTours();
    if (!completed.includes(tourId)) {
      localStorage.setItem(STORAGE_KEY, JSON.stringify([...completed, tourId]));
    }
  } catch {
    // Ignore storage errors
  }
}

function isTourCompleted(tourId: string): boolean {
  return getCompletedTours().includes(tourId);
}

// =============================================================================
// GuidedTour Component
// =============================================================================

export function GuidedTour({
  steps,
  isOpen,
  onClose,
  onComplete,
  onStepChange,
  initialStep = 0,
  tourId,
  className,
}: GuidedTourProps): ReactElement | null {
  const [currentStepIndex, setCurrentStepIndex] = useState(initialStep);
  const titleId = useId();

  // Check if this tour was already completed
  const shouldHide = tourId ? isTourCompleted(tourId) : false;

  const currentStep = steps[currentStepIndex];
  const isFirstStep = currentStepIndex === 0;
  const isLastStep = currentStepIndex === steps.length - 1;

  const handleNext = useCallback(() => {
    if (!isLastStep) {
      const nextIndex = currentStepIndex + 1;
      setCurrentStepIndex(nextIndex);
      onStepChange?.(nextIndex, steps[nextIndex]);
    }
  }, [currentStepIndex, isLastStep, onStepChange, steps]);

  const handleBack = useCallback(() => {
    if (!isFirstStep) {
      const prevIndex = currentStepIndex - 1;
      setCurrentStepIndex(prevIndex);
      onStepChange?.(prevIndex, steps[prevIndex]);
    }
  }, [currentStepIndex, isFirstStep, onStepChange, steps]);

  const handleFinish = useCallback(() => {
    if (tourId) {
      markTourComplete(tourId);
    }
    onComplete?.();
    onClose();
  }, [onClose, onComplete, tourId]);

  const handleSkip = useCallback(() => {
    onClose();
  }, [onClose]);

  const handleDotClick = useCallback((index: number) => {
    setCurrentStepIndex(index);
    onStepChange?.(index, steps[index]);
  }, [onStepChange, steps]);

  const handleKeyDown = useCallback((event: React.KeyboardEvent) => {
    if (event.key === 'Escape') {
      onClose();
    }
  }, [onClose]);

  // Handle escape key at document level
  useEffect(() => {
    if (!isOpen) return;

    const handleDocumentKeyDown = (event: KeyboardEvent) => {
      if (event.key === 'Escape') {
        onClose();
      }
    };

    document.addEventListener('keydown', handleDocumentKeyDown);
    return () => document.removeEventListener('keydown', handleDocumentKeyDown);
  }, [isOpen, onClose]);

  if (!isOpen || shouldHide || !currentStep) {
    return null;
  }

  return (
    <div
      role="dialog"
      aria-modal="true"
      aria-labelledby={titleId}
      onKeyDown={handleKeyDown}
      className={clsx(
        'fixed inset-0 z-50 flex items-center justify-center p-4',
        'bg-black/50 backdrop-blur-sm',
        className
      )}
    >
      <div className={clsx(
        'bg-white dark:bg-gray-800 rounded-xl shadow-2xl',
        'max-w-md w-full p-6',
        'animate-in fade-in zoom-in-95 duration-200'
      )}>
        {/* Header */}
        <div className="flex items-center justify-between mb-4">
          <h2
            id={titleId}
            className="text-xl font-semibold text-gray-900 dark:text-white"
          >
            {currentStep.title}
          </h2>
          <span className="text-sm text-gray-500 dark:text-gray-400">
            {currentStepIndex + 1} of {steps.length}
          </span>
        </div>

        {/* Content */}
        <div className="mb-6">
          {currentStep.image && (
            <img
              src={currentStep.image}
              alt=""
              className="w-full h-40 object-cover rounded-lg mb-4"
            />
          )}
          <p className="text-gray-600 dark:text-gray-300">
            {currentStep.content}
          </p>
        </div>

        {/* Progress Dots */}
        <div className="flex justify-center gap-2 mb-6">
          {steps.map((step, index) => (
            <button
              key={step.id}
              type="button"
              onClick={() => handleDotClick(index)}
              aria-label={`Step ${index + 1}`}
              aria-current={index === currentStepIndex ? 'step' : undefined}
              className={clsx(
                'w-2.5 h-2.5 rounded-full transition-colors',
                index === currentStepIndex
                  ? 'bg-blue-500'
                  : 'bg-gray-300 dark:bg-gray-600 hover:bg-gray-400 dark:hover:bg-gray-500'
              )}
            />
          ))}
        </div>

        {/* Navigation Buttons */}
        <div className="flex items-center justify-between">
          <button
            type="button"
            onClick={handleSkip}
            className={clsx(
              'text-sm text-gray-500 dark:text-gray-400',
              'hover:text-gray-700 dark:hover:text-gray-300',
              'focus:outline-none focus:underline'
            )}
          >
            Skip tour
          </button>

          <div className="flex gap-2">
            {!isFirstStep && (
              <button
                type="button"
                onClick={handleBack}
                className={clsx(
                  'px-4 py-2 rounded-lg text-sm font-medium',
                  'bg-gray-100 dark:bg-gray-700 text-gray-700 dark:text-gray-300',
                  'hover:bg-gray-200 dark:hover:bg-gray-600',
                  'focus:outline-none focus:ring-2 focus:ring-gray-500 focus:ring-offset-2'
                )}
              >
                Back
              </button>
            )}

            {isLastStep ? (
              <button
                type="button"
                onClick={handleFinish}
                className={clsx(
                  'px-4 py-2 rounded-lg text-sm font-medium',
                  'bg-green-600 text-white',
                  'hover:bg-green-700',
                  'focus:outline-none focus:ring-2 focus:ring-green-500 focus:ring-offset-2'
                )}
              >
                Finish
              </button>
            ) : (
              <button
                type="button"
                onClick={handleNext}
                className={clsx(
                  'px-4 py-2 rounded-lg text-sm font-medium',
                  'bg-blue-600 text-white',
                  'hover:bg-blue-700',
                  'focus:outline-none focus:ring-2 focus:ring-blue-500 focus:ring-offset-2'
                )}
              >
                Next
              </button>
            )}
          </div>
        </div>
      </div>
    </div>
  );
}

// =============================================================================
// Exports
// =============================================================================

export default GuidedTour;
