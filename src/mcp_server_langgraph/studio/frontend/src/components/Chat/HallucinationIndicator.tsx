/**
 * HallucinationIndicator Component
 *
 * Allows users to report potential AI hallucinations or inaccuracies.
 * Critical for AI safety and trustworthiness.
 */

import { useState, useCallback, useEffect, useRef } from "react";
import { Flag, X, CheckCircle, AlertTriangle } from "lucide-react";

import { Button, Textarea } from "@/components/UI";

/**
 * Hallucination categories - aligned with backend API (feedback.py).
 *
 * - factual_error: AI made a factually incorrect statement
 * - outdated_info: Information is no longer current
 * - made_up_source: AI cited a non-existent source
 * - other: Other types of hallucinations
 */
export type HallucinationCategory =
  | "factual_error"
  | "outdated_info"
  | "made_up_source"
  | "other";

export interface HallucinationReport {
  messageId: string;
  category: HallucinationCategory;
  details: string;
  timestamp: number;
}

export interface HallucinationIndicatorProps {
  messageId: string;
  onReport: (report: HallucinationReport) => void;
  isReported?: boolean;
}

interface CategoryOption {
  id: HallucinationCategory;
  label: string;
  description: string;
}

const categoryOptions: CategoryOption[] = [
  {
    id: "factual_error",
    label: "Factual Error",
    description: "AI made a factually incorrect statement",
  },
  {
    id: "outdated_info",
    label: "Outdated Information",
    description: "Information is no longer current",
  },
  {
    id: "made_up_source",
    label: "Made Up Source",
    description: "AI cited a non-existent source or reference",
  },
  {
    id: "other",
    label: "Other Issue",
    description: "Other types of AI inaccuracies or hallucinations",
  },
];

export function HallucinationIndicator({
  messageId,
  onReport,
  isReported = false,
}: HallucinationIndicatorProps) {
  const [isDialogOpen, setIsDialogOpen] = useState(false);
  const [selectedCategory, setSelectedCategory] =
    useState<HallucinationCategory | null>(null);
  const [details, setDetails] = useState("");
  const [showThankYou, setShowThankYou] = useState(false);
  const dialogRef = useRef<HTMLDivElement>(null);
  const closeButtonRef = useRef<HTMLButtonElement>(null);

  // Focus management and keyboard handling for dialog
  useEffect(() => {
    if (!isDialogOpen) return;

    // Focus the close button when dialog opens
    closeButtonRef.current?.focus();

    // Handle ESC key to close
    const handleKeyDown = (e: KeyboardEvent) => {
      if (e.key === "Escape") {
        setIsDialogOpen(false);
        setSelectedCategory(null);
        setDetails("");
      }
    };

    document.addEventListener("keydown", handleKeyDown);
    return () => document.removeEventListener("keydown", handleKeyDown);
  }, [isDialogOpen]);

  const handleOpenDialog = useCallback(() => {
    if (!isReported) {
      setIsDialogOpen(true);
    }
  }, [isReported]);

  const handleCancel = useCallback(() => {
    setIsDialogOpen(false);
    setSelectedCategory(null);
    setDetails("");
  }, []);

  const handleSubmit = useCallback(() => {
    if (selectedCategory) {
      onReport({
        messageId,
        category: selectedCategory,
        details,
        timestamp: Date.now(),
      });
      setIsDialogOpen(false);
      setShowThankYou(true);
      setSelectedCategory(null);
      setDetails("");

      // Hide thank you after 3 seconds
      setTimeout(() => setShowThankYou(false), 3000);
    }
  }, [messageId, selectedCategory, details, onReport]);

  if (isReported) {
    return (
      <span
        className="inline-flex items-center gap-1 text-xs text-warning-9 dark:text-warning-9"
        role="status"
        aria-label="This message has been reported as inaccurate"
      >
        <Flag className="w-3 h-3" aria-hidden="true" />
        Reported
      </span>
    );
  }

  if (showThankYou) {
    return (
      <span
        className="inline-flex items-center gap-1 text-xs text-success-10 dark:text-success-11"
        role="status"
        aria-live="polite"
      >
        <CheckCircle className="w-3 h-3" aria-hidden="true" />
        Thank you for your feedback
      </span>
    );
  }

  return (
    <>
      <Button
        variant="warning"
        size="sm"
        className="px-2 py-1 text-xs text-neutral-10 hover:text-warning-9 dark:hover:text-warning-9 rounded hover:bg-warning-3 dark:hover:bg-warning-a3"
        onClick={handleOpenDialog}
        disabled={isReported}
        aria-label="Report inaccuracy in this AI response"
      >
        <Flag className="w-3 h-3" aria-hidden="true" />
        Flag
      </Button>
      {isDialogOpen && (
        <div className="fixed inset-0 z-70 flex items-center justify-center bg-neutral-a6">
          <div
            ref={dialogRef}
            role="dialog"
            aria-modal="true"
            aria-labelledby="hallucination-dialog-title"
            aria-describedby="hallucination-dialog-description"
            className="bg-neutral-1 rounded-xl shadow-2xl max-w-md w-full mx-4 overflow-hidden"
          >
            {/* Header */}
            <div className="px-5 py-4 border-b border-neutral-5 flex items-center justify-between">
              <div className="flex items-center gap-2">
                <AlertTriangle
                  className="w-5 h-5 text-warning-9"
                  aria-hidden="true"
                />
                <h2
                  id="hallucination-dialog-title"
                  className="font-semibold text-neutral-12"
                >
                  Report Inaccuracy
                </h2>
              </div>
              <Button size="icon" variant="ghost"
                ref={closeButtonRef}
                className="p-1 text-neutral-9 hover:text-neutral-11 rounded"
                onClick={handleCancel}
                aria-label="Close dialog"
              >
                <X className="w-5 h-5" aria-hidden="true" />
              </Button>
            </div>

            {/* Content */}
            <div className="px-5 py-4">
              <p
                id="hallucination-dialog-description"
                className="text-sm text-neutral-11 mb-4"
              >
                Help us improve by reporting inaccurate AI responses.
              </p>

              {/* Category Selection - radiogroup pattern for single selection */}
              <fieldset className="space-y-2 mb-4">
                <legend className="text-sm font-medium text-neutral-11">
                  What type of issue is this?
                </legend>
                <div role="radiogroup" aria-required="true">
                  {categoryOptions.map((option) => (
                    <Button
                      variant="primary"
                      className="w-full text-left p-3 rounded-lg border-2"
                      key={option.id}
                      onClick={() => setSelectedCategory(option.id)}
                      role="radio"
                      aria-checked={selectedCategory === option.id}>
                      <div className="font-medium text-sm text-neutral-12">
                        {option.label}
                      </div>
                      <div className="text-xs text-neutral-11">
                        {option.description}
                      </div>
                    </Button>
                  ))}
                </div>
              </fieldset>

              {/* Details */}
              <div>
                <label
                  htmlFor="hallucination-details"
                  className="text-sm font-medium text-neutral-11"
                >
                  Additional details (optional)
                </label>
                <Textarea
                  id="hallucination-details"
                  className="mt-1 px-3 py-2 bg-neutral-2 border-0 text-sm text-neutral-12 placeholder-neutral-9 resize-none h-20 focus:ring-warning-7"
                  value={details}
                  onChange={(e) => setDetails(e.target.value)}
                  placeholder="Provide additional details about the inaccuracy..."
                />
              </div>
            </div>

            {/* Footer */}
            <div className="px-5 py-4 border-t border-neutral-5 flex justify-end gap-3">
              <Button variant="secondary"
                className="px-4 py-2 text-sm text-neutral-11 hover:text-neutral-12"
                onClick={handleCancel}
                aria-label="Cancel"
              >Cancel</Button>
              <Button variant="primary"
                className="px-4 py-2 text-sm rounded-lg"
                onClick={handleSubmit}
                disabled={!selectedCategory}
                aria-label="Submit"
              >Submit</Button>
            </div>
          </div>
        </div>
      )}
    </>
  );
}

export default HallucinationIndicator;
