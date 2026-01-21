/**
 * GuidedTour Component
 *
 * Interactive guided tour that highlights key UI elements.
 * Provides step-by-step explanations for new users.
 */

import { useState, useEffect, useCallback } from "react";
import { X, ArrowRight, ArrowLeft, CheckCircle } from "lucide-react";

import { Button } from "@/components/UI";

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
        className="fixed inset-0 z-65 bg-neutral-a4 pointer-events-none"
      />
      {/* Tooltip */}
      <div
        role="tooltip"
        aria-live="polite"
        className="fixed z-70 max-w-sm bg-neutral-1 rounded-xl shadow-2xl border border-neutral-5"
        style={{
          top: "50%",
          left: "50%",
          transform: "translate(-50%, -50%)",
        }}
      >
        {/* Header */}
        <div className="flex items-center justify-between px-4 py-3 border-b border-neutral-5">
          <h3 className="font-semibold text-neutral-12">
            {currentStep.title}
          </h3>
          <Button size="icon" variant="ghost"
            className="p-1 text-neutral-9 hover:text-neutral-11 rounded"
            onClick={handleSkip}
            aria-label="Skip"
          >
            <X className="w-4 h-4" />
          </Button>
        </div>

        {/* Content */}
        <div className="px-4 py-3">
          <p className="text-sm text-neutral-11">
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
                  ? "bg-primary-9"
                  : index < currentStepIndex
                    ? "bg-primary-5"
                    : "bg-neutral-3"
              }`}
            />
          ))}
        </div>

        {/* Step Counter */}
        <div className="text-center text-xs text-neutral-10 pb-2">
          {currentStepIndex + 1} of {steps.length}
        </div>

        {/* Footer */}
        <div className="flex items-center justify-between px-4 py-3 border-t border-neutral-5 bg-neutral-1 rounded-b-xl">
          <div>
            {!isFirstStep && (
              <Button
                variant="ghost"
                className="flex px-3 py-1.5 text-sm text-neutral-11 hover:text-neutral-12"
                onClick={handlePrevious}
                aria-label="Previous">
                <ArrowLeft className="w-3 h-3" />
                Previous
              </Button>
            )}
          </div>
          <div className="flex items-center gap-2">
            {isLastStep ? (
              <Button
                variant="success"
                className="flex px-4 py-1.5 text-sm bg-success-10 text-neutral-12 rounded-lg hover:bg-success-11"
                onClick={handleNext}
                aria-label="Finish"
              >
                Finish
                <CheckCircle className="w-3 h-3" />
              </Button>
            ) : (
              <Button
                variant="primary"
                className="flex px-4 py-1.5 text-sm bg-primary-10 text-neutral-12 rounded-lg hover:bg-primary-11"
                onClick={handleNext}
                aria-label="Next"
              >
                Next
                <ArrowRight className="w-3 h-3" />
              </Button>
            )}
          </div>
        </div>
      </div>
    </>
  );
}

export default GuidedTour;
