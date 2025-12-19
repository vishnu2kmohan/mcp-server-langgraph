/**
 * StepProgress Component
 *
 * Multi-step workflow progress indicator.
 * Features:
 * - Step states (pending, current, completed, error)
 * - Horizontal and vertical layouts
 * - Step navigation (click to jump)
 * - Connector lines between steps
 * - Optional step numbers and descriptions
 *
 * Implements WCAG 2.1 AA accessibility requirements.
 * Based on UX patterns from Gemini CLI, OpenAI Codex, and Claude Code.
 */

import { Check, AlertCircle } from "lucide-react";

// ==============================================================================
// Types
// ==============================================================================

export type StepStatus = "pending" | "current" | "completed" | "error";
export type StepSize = "sm" | "md" | "lg";
export type StepOrientation = "horizontal" | "vertical";

export interface Step {
  /** Unique step identifier */
  id: string;
  /** Step label */
  label: string;
  /** Optional description */
  description?: string;
}

export interface StepProgressProps {
  /** Array of steps */
  steps: Step[];
  /** Current step index (0-based) */
  currentStep: number;
  /** Step with error (optional) */
  errorStep?: number;
  /** Layout orientation */
  orientation?: StepOrientation;
  /** Size variant */
  size?: StepSize;
  /** Show step numbers */
  showNumbers?: boolean;
  /** Show step descriptions */
  showDescriptions?: boolean;
  /** Allow clicking future steps */
  allowFutureSteps?: boolean;
  /** Accessible label */
  ariaLabel?: string;
  /** Called when a step is clicked */
  onStepClick?: (stepIndex: number) => void;
  /** Additional CSS classes */
  className?: string;
}

// ==============================================================================
// Constants
// ==============================================================================

const SIZE_CLASSES: Record<
  StepSize,
  { circle: string; text: string; connector: string }
> = {
  sm: { circle: "w-6 h-6 text-xs", text: "text-xs", connector: "h-0.5" },
  md: { circle: "w-8 h-8 text-sm", text: "text-sm", connector: "h-0.5" },
  lg: { circle: "w-10 h-10 text-base", text: "text-base", connector: "h-1" },
};

const STATUS_CLASSES: Record<StepStatus, { circle: string; text: string }> = {
  pending: {
    circle:
      "bg-gray-100 dark:bg-gray-800 border-gray-300 dark:border-gray-600 text-gray-400 dark:text-gray-500",
    text: "text-gray-500 dark:text-gray-400",
  },
  current: {
    circle:
      "bg-blue-100 dark:bg-blue-900/30 border-blue-600 dark:border-blue-400 text-blue-600 dark:text-blue-400",
    text: "text-blue-700 dark:text-blue-300 font-medium",
  },
  completed: {
    circle:
      "bg-green-600 dark:bg-green-500 border-green-600 dark:border-green-500 text-white",
    text: "text-gray-700 dark:text-gray-300",
  },
  error: {
    circle:
      "bg-red-100 dark:bg-red-900/30 border-red-600 dark:border-red-400 text-red-600 dark:text-red-400",
    text: "text-red-700 dark:text-red-300",
  },
};

// ==============================================================================
// Helper Functions
// ==============================================================================

function getStepStatus(
  index: number,
  currentStep: number,
  errorStep?: number,
): StepStatus {
  if (errorStep !== undefined && index === errorStep) return "error";
  if (index < currentStep) return "completed";
  if (index === currentStep) return "current";
  return "pending";
}

function getStepAriaLabel(step: Step, status: StepStatus): string {
  const statusText =
    status === "completed"
      ? "completed"
      : status === "current"
        ? "current"
        : status === "error"
          ? "error"
          : "pending";
  return `${step.label}, ${statusText}`;
}

// ==============================================================================
// Component
// ==============================================================================

export function StepProgress({
  steps,
  currentStep,
  errorStep,
  orientation = "horizontal",
  size = "md",
  showNumbers = false,
  showDescriptions = false,
  allowFutureSteps = false,
  ariaLabel = "Progress steps",
  onStepClick,
  className = "",
}: StepProgressProps) {
  const sizeClasses = SIZE_CLASSES[size];
  const isHorizontal = orientation === "horizontal";

  const handleStepClick = (index: number, status: StepStatus) => {
    if (!onStepClick) return;

    // Allow clicking completed steps or current step
    if (status === "completed" || status === "current") {
      onStepClick(index);
      return;
    }

    // Allow future steps only if enabled
    if (allowFutureSteps && status === "pending") {
      onStepClick(index);
    }
  };

  return (
    <nav
      data-testid="step-progress"
      data-orientation={orientation}
      data-size={size}
      aria-label={ariaLabel}
      className={`${
        isHorizontal
          ? "flex items-start justify-between"
          : "flex flex-col space-y-4"
      } ${className}`}
    >
      {steps.map((step, index) => {
        const status = getStepStatus(index, currentStep, errorStep);
        const statusClasses = STATUS_CLASSES[status];
        const isLast = index === steps.length - 1;
        const isClickable =
          onStepClick &&
          (status === "completed" ||
            status === "current" ||
            (allowFutureSteps && status === "pending"));

        return (
          <div
            key={step.id}
            className={`${
              isHorizontal ? "flex-1 flex items-center" : "flex items-start"
            } ${isLast ? "" : ""}`}
          >
            {/* Step circle and content */}
            <div
              className={`flex ${isHorizontal ? "flex-col items-center" : "items-start gap-3"}`}
            >
              {/* Step circle */}
              {isClickable ? (
                <button
                  type="button"
                  data-testid={`step-${step.id}`}
                  data-status={status}
                  aria-current={status === "current" ? "step" : undefined}
                  aria-label={getStepAriaLabel(step, status)}
                  onClick={() => handleStepClick(index, status)}
                  className={`flex items-center justify-center rounded-full border-2 transition-colors ${sizeClasses.circle} ${statusClasses.circle} ${
                    isClickable
                      ? "cursor-pointer hover:opacity-80 focus:outline-none focus:ring-2 focus:ring-blue-500 focus:ring-offset-2"
                      : ""
                  }`}
                >
                  {status === "completed" ? (
                    <Check
                      data-testid="step-completed-icon"
                      size={size === "sm" ? 12 : size === "lg" ? 20 : 16}
                      aria-hidden="true"
                    />
                  ) : showNumbers ? (
                    <span>{index + 1}</span>
                  ) : (
                    <span className="sr-only">{index + 1}</span>
                  )}
                </button>
              ) : (
                <div
                  data-testid={`step-${step.id}`}
                  data-status={status}
                  aria-current={status === "current" ? "step" : undefined}
                  className={`flex items-center justify-center rounded-full border-2 ${sizeClasses.circle} ${statusClasses.circle}`}
                >
                  {status === "completed" ? (
                    <Check
                      data-testid="step-completed-icon"
                      size={size === "sm" ? 12 : size === "lg" ? 20 : 16}
                      aria-hidden="true"
                    />
                  ) : status === "error" ? (
                    <AlertCircle
                      size={size === "sm" ? 12 : size === "lg" ? 20 : 16}
                      aria-hidden="true"
                    />
                  ) : showNumbers ? (
                    <span>{index + 1}</span>
                  ) : (
                    <span className="sr-only">{index + 1}</span>
                  )}
                </div>
              )}

              {/* Step label and description */}
              <div
                className={`${isHorizontal ? "mt-2 text-center" : ""}`}
                onClick={
                  isClickable ? () => handleStepClick(index, status) : undefined
                }
                style={isClickable ? { cursor: "pointer" } : undefined}
              >
                <span
                  className={`block ${sizeClasses.text} ${statusClasses.text}`}
                >
                  {step.label}
                </span>
                {showDescriptions && step.description && (
                  <span
                    className={`block mt-0.5 text-gray-500 dark:text-gray-400 ${
                      size === "sm" ? "text-xs" : "text-xs"
                    }`}
                  >
                    {step.description}
                  </span>
                )}
              </div>
            </div>

            {/* Connector line */}
            {!isLast && (
              <div
                data-testid="step-connector"
                data-completed={index < currentStep ? "true" : "false"}
                className={`${
                  isHorizontal
                    ? `flex-1 mx-2 ${sizeClasses.connector}`
                    : `ml-4 w-0.5 h-8`
                } rounded-full transition-colors ${
                  index < currentStep
                    ? "bg-green-600 dark:bg-green-500"
                    : "bg-gray-200 dark:bg-gray-700"
                }`}
                aria-hidden="true"
              />
            )}
          </div>
        );
      })}
    </nav>
  );
}

export default StepProgress;
