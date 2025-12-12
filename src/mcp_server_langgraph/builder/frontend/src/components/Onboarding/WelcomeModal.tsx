/**
 * WelcomeModal Component
 *
 * Builder-specific onboarding with feature highlights.
 * Shows on first visit and can be dismissed.
 * Implements HEART Framework "Adoption" dimension.
 */

import React, { useState, useCallback, useEffect } from 'react';

// ==============================================================================
// Types
// ==============================================================================

export interface WelcomeModalProps {
  onComplete: () => void;
  onSkip: () => void;
}

interface FeatureSlide {
  title: string;
  description: string;
  icon: React.ReactNode;
}

// ==============================================================================
// Constants
// ==============================================================================

const STORAGE_KEY = 'builder_onboarding_complete';

const FEATURES: FeatureSlide[] = [
  {
    title: 'Add Nodes',
    description:
      'Drag nodes from the sidebar to the canvas to build your workflow. Choose from Tool, LLM, Conditional, and Approval nodes.',
    icon: (
      <svg className="w-12 h-12" fill="none" viewBox="0 0 24 24" stroke="currentColor">
        <path
          strokeLinecap="round"
          strokeLinejoin="round"
          strokeWidth={1.5}
          d="M12 4.5v15m7.5-7.5h-15"
        />
      </svg>
    ),
  },
  {
    title: 'Connect Nodes',
    description:
      'Link nodes together by dragging from output handles to input handles. Create complex workflows with multiple branches.',
    icon: (
      <svg className="w-12 h-12" fill="none" viewBox="0 0 24 24" stroke="currentColor">
        <path
          strokeLinecap="round"
          strokeLinejoin="round"
          strokeWidth={1.5}
          d="M7.5 21L3 16.5m0 0L7.5 12M3 16.5h13.5m0-13.5L21 7.5m0 0L16.5 12M21 7.5H7.5"
        />
      </svg>
    ),
  },
  {
    title: 'Configure Nodes',
    description:
      'Click on any node to open its configuration panel. Customize parameters, set conditions, and define behavior.',
    icon: (
      <svg className="w-12 h-12" fill="none" viewBox="0 0 24 24" stroke="currentColor">
        <path
          strokeLinecap="round"
          strokeLinejoin="round"
          strokeWidth={1.5}
          d="M9.594 3.94c.09-.542.56-.94 1.11-.94h2.593c.55 0 1.02.398 1.11.94l.213 1.281c.063.374.313.686.645.87.074.04.147.083.22.127.324.196.72.257 1.075.124l1.217-.456a1.125 1.125 0 011.37.49l1.296 2.247a1.125 1.125 0 01-.26 1.431l-1.003.827c-.293.24-.438.613-.431.992a6.759 6.759 0 010 .255c-.007.378.138.75.43.99l1.005.828c.424.35.534.954.26 1.43l-1.298 2.247a1.125 1.125 0 01-1.369.491l-1.217-.456c-.355-.133-.75-.072-1.076.124a6.57 6.57 0 01-.22.128c-.331.183-.581.495-.644.869l-.213 1.28c-.09.543-.56.941-1.11.941h-2.594c-.55 0-1.02-.398-1.11-.94l-.213-1.281c-.062-.374-.312-.686-.644-.87a6.52 6.52 0 01-.22-.127c-.325-.196-.72-.257-1.076-.124l-1.217.456a1.125 1.125 0 01-1.369-.49l-1.297-2.247a1.125 1.125 0 01.26-1.431l1.004-.827c.292-.24.437-.613.43-.992a6.932 6.932 0 010-.255c.007-.378-.138-.75-.43-.99l-1.004-.828a1.125 1.125 0 01-.26-1.43l1.297-2.247a1.125 1.125 0 011.37-.491l1.216.456c.356.133.751.072 1.076-.124.072-.044.146-.087.22-.128.332-.183.582-.495.644-.869l.214-1.281z"
        />
        <path
          strokeLinecap="round"
          strokeLinejoin="round"
          strokeWidth={1.5}
          d="M15 12a3 3 0 11-6 0 3 3 0 016 0z"
        />
      </svg>
    ),
  },
  {
    title: 'Export Code',
    description:
      'Generate production-ready Python code from your visual workflow. Copy or download the LangGraph code instantly.',
    icon: (
      <svg className="w-12 h-12" fill="none" viewBox="0 0 24 24" stroke="currentColor">
        <path
          strokeLinecap="round"
          strokeLinejoin="round"
          strokeWidth={1.5}
          d="M17.25 6.75L22.5 12l-5.25 5.25m-10.5 0L1.5 12l5.25-5.25m7.5-3l-4.5 16.5"
        />
      </svg>
    ),
  },
];

// ==============================================================================
// Helpers
// ==============================================================================

function clsx(...classes: (string | undefined | boolean)[]): string {
  return classes.filter(Boolean).join(' ');
}

// ==============================================================================
// Component
// ==============================================================================

export function WelcomeModal({
  onComplete,
  onSkip,
}: WelcomeModalProps): React.ReactElement | null {
  const [currentSlide, setCurrentSlide] = useState(0);
  const [isVisible, setIsVisible] = useState(false);

  // Check if onboarding was already completed
  useEffect(() => {
    const completed = localStorage.getItem(STORAGE_KEY);
    if (!completed) {
      setIsVisible(true);
    }
  }, []);

  const handleNext = useCallback(() => {
    if (currentSlide < FEATURES.length - 1) {
      setCurrentSlide((prev) => prev + 1);
    } else {
      localStorage.setItem(STORAGE_KEY, 'true');
      setIsVisible(false);
      onComplete();
    }
  }, [currentSlide, onComplete]);

  const handleSkip = useCallback(() => {
    localStorage.setItem(STORAGE_KEY, 'true');
    setIsVisible(false);
    onSkip();
  }, [onSkip]);

  const handlePrev = useCallback(() => {
    if (currentSlide > 0) {
      setCurrentSlide((prev) => prev - 1);
    }
  }, [currentSlide]);

  if (!isVisible) {
    return null;
  }

  const feature = FEATURES[currentSlide];
  const isLastSlide = currentSlide === FEATURES.length - 1;

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center">
      {/* Backdrop */}
      <div className="absolute inset-0 bg-black/60" aria-hidden="true" />

      {/* Modal */}
      <div
        role="dialog"
        aria-modal="true"
        aria-label="Welcome to Visual Builder"
        className={clsx(
          'relative z-10 w-full max-w-lg mx-4',
          'bg-white dark:bg-gray-800',
          'rounded-2xl shadow-2xl',
          'overflow-hidden'
        )}
        data-testid="welcome-modal"
      >
        {/* Header with gradient */}
        <div className="bg-gradient-to-r from-blue-500 to-blue-600 p-6 text-white">
          <h2 className="text-2xl font-bold">Welcome to Visual Builder</h2>
          <p className="text-blue-100 mt-1">Create LangGraph workflows visually</p>
        </div>

        {/* Content */}
        <div className="p-6">
          {/* Feature showcase */}
          <div className="flex flex-col items-center text-center">
            <div className="text-blue-500 dark:text-blue-400 mb-4">{feature.icon}</div>
            <h3 className="text-xl font-semibold text-gray-900 dark:text-white mb-2">
              {feature.title}
            </h3>
            <p className="text-gray-600 dark:text-gray-300">{feature.description}</p>
          </div>

          {/* Progress dots */}
          <div className="flex justify-center gap-2 mt-6">
            {FEATURES.map((_, idx) => (
              <button
                key={idx}
                type="button"
                onClick={() => setCurrentSlide(idx)}
                className={clsx(
                  'w-2.5 h-2.5 rounded-full transition-all',
                  idx === currentSlide
                    ? 'bg-blue-500 w-6'
                    : 'bg-gray-300 dark:bg-gray-600 hover:bg-gray-400'
                )}
                aria-label={`Go to slide ${idx + 1}`}
              />
            ))}
          </div>

          {/* Actions */}
          <div className="flex items-center justify-between mt-6">
            <button
              type="button"
              onClick={handleSkip}
              className="text-sm text-gray-500 dark:text-gray-400 hover:text-gray-700 dark:hover:text-gray-200"
            >
              Skip tour
            </button>

            <div className="flex gap-3">
              {currentSlide > 0 && (
                <button
                  type="button"
                  onClick={handlePrev}
                  className={clsx(
                    'px-4 py-2 rounded-lg font-medium',
                    'bg-gray-100 dark:bg-gray-700 text-gray-700 dark:text-gray-200',
                    'hover:bg-gray-200 dark:hover:bg-gray-600'
                  )}
                >
                  Back
                </button>
              )}
              <button
                type="button"
                onClick={handleNext}
                className={clsx(
                  'px-6 py-2 rounded-lg font-medium',
                  'bg-blue-600 text-white',
                  'hover:bg-blue-700',
                  'focus:outline-none focus:ring-2 focus:ring-blue-500 focus:ring-offset-2'
                )}
              >
                {isLastSlide ? 'Get Started' : 'Next'}
              </button>
            </div>
          </div>
        </div>
      </div>
    </div>
  );
}

// ==============================================================================
// Hook
// ==============================================================================

/**
 * Hook to manage onboarding state
 */
export function useOnboarding() {
  const [hasCompletedOnboarding, setHasCompletedOnboarding] = useState(() => {
    if (typeof localStorage === 'undefined') return false;
    return localStorage.getItem(STORAGE_KEY) === 'true';
  });

  const resetOnboarding = useCallback(() => {
    localStorage.removeItem(STORAGE_KEY);
    setHasCompletedOnboarding(false);
  }, []);

  const completeOnboarding = useCallback(() => {
    localStorage.setItem(STORAGE_KEY, 'true');
    setHasCompletedOnboarding(true);
  }, []);

  return {
    hasCompletedOnboarding,
    resetOnboarding,
    completeOnboarding,
  };
}

export default WelcomeModal;
