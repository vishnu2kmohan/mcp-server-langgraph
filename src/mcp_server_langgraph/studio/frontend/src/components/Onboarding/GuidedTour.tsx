/**
 * GuidedTour Component
 *
 * Interactive guided tour that highlights key UI elements.
 * Provides step-by-step explanations for new users.
 */

import { useState, useEffect, useCallback } from "react";
import { X, ArrowRight, ArrowLeft, CheckCircle } from "lucide-react";

export interface TourStep {
  target: string;
  title: string;
  content: string;
  position: "top" | "bottom" | "left" | "right";
}

export interface TourCompleteResult {
  stepsCompleted: number;
}

export interface TourSkipResult {
  stepSkippedAt: number;
}

export interface GuidedTourProps {
  isActive: boolean;
  steps: TourStep[];
  onComplete: (result: TourCompleteResult) => void;
  onSkip: (result: TourSkipResult) => void;
}

export function GuidedTour({
  isActive,
  steps,
  onComplete,
  onSkip,
}: GuidedTourProps) {
  const [currentStepIndex, setCurrentStepIndex] = useState(0);

  const currentStep = steps[currentStepIndex];
  const isFirstStep = currentStepIndex === 0;
  const isLastStep = currentStepIndex === steps.length - 1;

  const handleNext = useCallback(() => {
    if (isLastStep) {
      onComplete({ stepsCompleted: steps.length });
    } else {
      setCurrentStepIndex((i) => i + 1);
    }
  }, [isLastStep, steps.length, onComplete]);

  const handlePrevious = useCallback(() => {
    if (!isFirstStep) {
      setCurrentStepIndex((i) => i - 1);
    }
  }, [isFirstStep]);

  const handleSkip = useCallback(() => {
    onSkip({ stepSkippedAt: currentStepIndex + 1 });
  }, [currentStepIndex, onSkip]);

  // Keyboard navigation
  useEffect(() => {
    if (!isActive) return;

    const handleKeyDown = (e: KeyboardEvent) => {
      switch (e.key) {
        case "Escape":
          handleSkip();
          break;
        case "ArrowRight":
          handleNext();
          break;
        case "ArrowLeft":
          handlePrevious();
          break;
      }
    };

    document.addEventListener("keydown", handleKeyDown);
    return () => document.removeEventListener("keydown", handleKeyDown);
  }, [isActive, handleNext, handlePrevious, handleSkip]);

  if (!isActive || steps.length === 0 || !currentStep) {
    return null;
  }

  return (
    <>
      {/* Backdrop */}
      <div
        data-testid="tour-backdrop"
        className="fixed inset-0 z-[65] bg-black/30 pointer-events-none"
      />

      {/* Tooltip */}
      <div
        role="tooltip"
        aria-live="polite"
        className="fixed z-[70] max-w-sm bg-white dark:bg-gray-800 rounded-xl shadow-2xl border border-gray-200 dark:border-gray-700"
        style={{
          top: "50%",
          left: "50%",
          transform: "translate(-50%, -50%)",
        }}
      >
        {/* Header */}
        <div className="flex items-center justify-between px-4 py-3 border-b border-gray-200 dark:border-gray-700">
          <h3 className="font-semibold text-gray-900 dark:text-gray-100">
            {currentStep.title}
          </h3>
          <button
            onClick={handleSkip}
            aria-label="Skip"
            className="p-1 text-gray-400 hover:text-gray-600 dark:hover:text-gray-300 rounded"
          >
            <X className="w-4 h-4" />
          </button>
        </div>

        {/* Content */}
        <div className="px-4 py-3">
          <p className="text-sm text-gray-600 dark:text-gray-400">
            {currentStep.content}
          </p>
        </div>

        {/* Progress Dots */}
        <div className="flex items-center justify-center gap-1.5 px-4 py-2">
          {steps.map((_, index) => (
            <div
              key={index}
              data-testid="tour-progress-dot"
              className={`w-2 h-2 rounded-full transition-colors ${
                index === currentStepIndex
                  ? "bg-blue-500"
                  : index < currentStepIndex
                    ? "bg-blue-300"
                    : "bg-gray-300 dark:bg-gray-600"
              }`}
            />
          ))}
        </div>

        {/* Step Counter */}
        <div className="text-center text-xs text-gray-500 dark:text-gray-400 pb-2">
          {currentStepIndex + 1} of {steps.length}
        </div>

        {/* Footer */}
        <div className="flex items-center justify-between px-4 py-3 border-t border-gray-200 dark:border-gray-700 bg-gray-50 dark:bg-gray-800/50 rounded-b-xl">
          <div>
            {!isFirstStep && (
              <button
                onClick={handlePrevious}
                aria-label="Previous"
                className="flex items-center gap-1 px-3 py-1.5 text-sm text-gray-600 dark:text-gray-400 hover:text-gray-800 dark:hover:text-gray-200"
              >
                <ArrowLeft className="w-3 h-3" />
                Previous
              </button>
            )}
          </div>
          <div className="flex items-center gap-2">
            {isLastStep ? (
              <button
                onClick={handleNext}
                aria-label="Finish"
                className="flex items-center gap-1 px-4 py-1.5 text-sm bg-green-600 text-white rounded-lg hover:bg-green-700"
              >
                Finish
                <CheckCircle className="w-3 h-3" />
              </button>
            ) : (
              <button
                onClick={handleNext}
                aria-label="Next"
                className="flex items-center gap-1 px-4 py-1.5 text-sm bg-blue-600 text-white rounded-lg hover:bg-blue-700"
              >
                Next
                <ArrowRight className="w-3 h-3" />
              </button>
            )}
          </div>
        </div>
      </div>
    </>
  );
}

export default GuidedTour;
