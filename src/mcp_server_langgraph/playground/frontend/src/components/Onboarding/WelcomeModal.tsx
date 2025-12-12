/**
 * WelcomeModal Component
 *
 * First-time user onboarding with feature highlights.
 * Shows on first visit and can be dismissed.
 */

import React, { useState, useCallback, useEffect } from 'react';
import clsx from 'clsx';

export interface WelcomeModalProps {
  onComplete: () => void;
  onSkip: () => void;
}

interface FeatureSlide {
  title: string;
  description: string;
  icon: React.ReactNode;
}

const FEATURES: FeatureSlide[] = [
  {
    title: 'Chat with AI Agents',
    description: 'Have natural conversations with intelligent agents powered by LangGraph. Ask questions, get help with tasks, and explore ideas.',
    icon: (
      <svg className="w-12 h-12" fill="none" viewBox="0 0 24 24" stroke="currentColor">
        <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={1.5} d="M8 12h.01M12 12h.01M16 12h.01M21 12c0 4.418-4.03 8-9 8a9.863 9.863 0 01-4.255-.949L3 20l1.395-3.72C3.512 15.042 3 13.574 3 12c0-4.418 4.03-8 9-8s9 3.582 9 8z" />
      </svg>
    ),
  },
  {
    title: 'Explore MCP Tools',
    description: 'Browse and execute tools provided by connected MCP servers. See tool descriptions, parameters, and run them directly.',
    icon: (
      <svg className="w-12 h-12" fill="none" viewBox="0 0 24 24" stroke="currentColor">
        <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={1.5} d="M11.42 15.17L17.25 21A2.652 2.652 0 0021 17.25l-5.877-5.877M11.42 15.17l2.496-3.03c.317-.384.74-.626 1.208-.766M11.42 15.17l-4.655 5.653a2.548 2.548 0 11-3.586-3.586l6.837-5.63m5.108-.233c.55-.164 1.163-.188 1.743-.14a4.5 4.5 0 004.486-6.336l-3.276 3.277a3.004 3.004 0 01-2.25-2.25l3.276-3.276a4.5 4.5 0 00-6.336 4.486c.091 1.076-.071 2.264-.904 2.95l-.102.085m-1.745 1.437L5.909 7.5H4.5L2.25 3.75l1.5-1.5L7.5 4.5v1.409l4.26 4.26m-1.745 1.437l1.745-1.437m6.615 8.206L15.75 15.75M4.867 19.125h.008v.008h-.008v-.008z" />
      </svg>
    ),
  },
  {
    title: 'Browse Resources',
    description: 'Access files, data, and content exposed by MCP servers. Preview content and integrate it into your conversations.',
    icon: (
      <svg className="w-12 h-12" fill="none" viewBox="0 0 24 24" stroke="currentColor">
        <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={1.5} d="M19.5 14.25v-2.625a3.375 3.375 0 00-3.375-3.375h-1.5A1.125 1.125 0 0113.5 7.125v-1.5a3.375 3.375 0 00-3.375-3.375H8.25m0 12.75h7.5m-7.5 3H12M10.5 2.25H5.625c-.621 0-1.125.504-1.125 1.125v17.25c0 .621.504 1.125 1.125 1.125h12.75c.621 0 1.125-.504 1.125-1.125V11.25a9 9 0 00-9-9z" />
      </svg>
    ),
  },
  {
    title: 'Use Prompt Templates',
    description: 'Discover and use pre-built prompts from MCP servers. Fill in the arguments and get structured responses.',
    icon: (
      <svg className="w-12 h-12" fill="none" viewBox="0 0 24 24" stroke="currentColor">
        <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={1.5} d="M7.5 8.25h9m-9 3H12m-9.75 1.51c0 1.6 1.123 2.994 2.707 3.227 1.129.166 2.27.293 3.423.379.35.026.67.21.865.501L12 21l2.755-4.133a1.14 1.14 0 01.865-.501 48.172 48.172 0 003.423-.379c1.584-.233 2.707-1.626 2.707-3.228V6.741c0-1.602-1.123-2.995-2.707-3.228A48.394 48.394 0 0012 3c-2.392 0-4.744.175-7.043.513C3.373 3.746 2.25 5.14 2.25 6.741v6.018z" />
      </svg>
    ),
  },
];

const STORAGE_KEY = 'playground_onboarding_complete';

export function WelcomeModal({ onComplete, onSkip }: WelcomeModalProps): React.ReactElement | null {
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
        aria-label="Welcome to the Playground"
        className={clsx(
          'relative z-10 w-full max-w-lg mx-4',
          'bg-white dark:bg-dark-surface',
          'rounded-2xl shadow-2xl',
          'overflow-hidden'
        )}
      >
        {/* Header with gradient */}
        <div className="bg-gradient-to-r from-primary-500 to-primary-600 p-6 text-white">
          <h2 className="text-2xl font-bold">Welcome to the Playground</h2>
          <p className="text-primary-100 mt-1">Your gateway to AI-powered workflows</p>
        </div>

        {/* Content */}
        <div className="p-6">
          {/* Feature showcase */}
          <div className="flex flex-col items-center text-center">
            <div className="text-primary-500 dark:text-primary-400 mb-4">
              {feature.icon}
            </div>
            <h3 className="text-xl font-semibold text-gray-900 dark:text-dark-text mb-2">
              {feature.title}
            </h3>
            <p className="text-gray-600 dark:text-dark-textSecondary">
              {feature.description}
            </p>
          </div>

          {/* Progress dots */}
          <div className="flex justify-center gap-2 mt-6">
            {FEATURES.map((_, idx) => (
              <button
                key={idx}
                onClick={() => setCurrentSlide(idx)}
                className={clsx(
                  'w-2.5 h-2.5 rounded-full transition-all',
                  idx === currentSlide
                    ? 'bg-primary-500 w-6'
                    : 'bg-gray-300 dark:bg-dark-border hover:bg-gray-400'
                )}
                aria-label={`Go to slide ${idx + 1}`}
              />
            ))}
          </div>

          {/* Actions */}
          <div className="flex items-center justify-between mt-6">
            <button
              onClick={handleSkip}
              className="text-sm text-gray-500 dark:text-dark-textMuted hover:text-gray-700 dark:hover:text-dark-text"
            >
              Skip tour
            </button>

            <div className="flex gap-3">
              {currentSlide > 0 && (
                <button
                  onClick={handlePrev}
                  className={clsx(
                    'px-4 py-2 rounded-lg font-medium',
                    'bg-gray-100 dark:bg-dark-bg text-gray-700 dark:text-dark-text',
                    'hover:bg-gray-200 dark:hover:bg-dark-hover'
                  )}
                >
                  Back
                </button>
              )}
              <button
                onClick={handleNext}
                className={clsx(
                  'px-6 py-2 rounded-lg font-medium',
                  'bg-primary-600 text-white',
                  'hover:bg-primary-700',
                  'focus:outline-none focus:ring-2 focus:ring-primary-500 focus:ring-offset-2'
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

/**
 * Hook to manage onboarding state
 */
export function useOnboarding() {
  const [hasCompletedOnboarding, setHasCompletedOnboarding] = useState(() => {
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
