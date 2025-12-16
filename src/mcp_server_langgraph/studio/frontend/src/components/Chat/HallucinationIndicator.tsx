/**
 * HallucinationIndicator Component
 *
 * Allows users to report potential AI hallucinations or inaccuracies.
 * Critical for AI safety and trustworthiness.
 */

import { useState, useCallback } from "react";
import { Flag, X, CheckCircle, AlertTriangle } from "lucide-react";

export type HallucinationCategory =
  | "factual_error"
  | "outdated_info"
  | "incorrect_citation"
  | "made_up_info";

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
    description: "The information is incorrect or misleading",
  },
  {
    id: "outdated_info",
    label: "Outdated Information",
    description: "The information is no longer current",
  },
  {
    id: "incorrect_citation",
    label: "Incorrect Citation",
    description: "Source or reference is wrong or doesn't exist",
  },
  {
    id: "made_up_info",
    label: "Made Up Information",
    description: "The AI fabricated facts or data",
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
      <span className="inline-flex items-center gap-1 text-xs text-amber-600 dark:text-amber-400">
        <Flag className="w-3 h-3" />
        Reported
      </span>
    );
  }

  if (showThankYou) {
    return (
      <span className="inline-flex items-center gap-1 text-xs text-green-600 dark:text-green-400">
        <CheckCircle className="w-3 h-3" />
        Thank you for your feedback
      </span>
    );
  }

  return (
    <>
      <button
        onClick={handleOpenDialog}
        disabled={isReported}
        aria-label="Report inaccuracy"
        className="inline-flex items-center gap-1 px-2 py-1 text-xs text-gray-500 hover:text-amber-600 dark:text-gray-400 dark:hover:text-amber-400 rounded hover:bg-amber-50 dark:hover:bg-amber-900/20 transition-colors"
      >
        <Flag className="w-3 h-3" />
        Flag
      </button>

      {isDialogOpen && (
        <div className="fixed inset-0 z-[70] flex items-center justify-center bg-black/50">
          <div
            role="dialog"
            aria-modal="true"
            aria-labelledby="hallucination-dialog-title"
            className="bg-white dark:bg-gray-800 rounded-xl shadow-2xl max-w-md w-full mx-4 overflow-hidden"
          >
            {/* Header */}
            <div className="px-5 py-4 border-b border-gray-200 dark:border-gray-700 flex items-center justify-between">
              <div className="flex items-center gap-2">
                <AlertTriangle className="w-5 h-5 text-amber-500" />
                <h2
                  id="hallucination-dialog-title"
                  className="font-semibold text-gray-900 dark:text-gray-100"
                >
                  Report Inaccuracy
                </h2>
              </div>
              <button
                onClick={handleCancel}
                aria-label="Close"
                className="p-1 text-gray-400 hover:text-gray-600 dark:hover:text-gray-300 rounded"
              >
                <X className="w-5 h-5" />
              </button>
            </div>

            {/* Content */}
            <div className="px-5 py-4">
              <p className="text-sm text-gray-600 dark:text-gray-400 mb-4">
                Help us improve by reporting inaccurate AI responses.
              </p>

              {/* Category Selection */}
              <div className="space-y-2 mb-4">
                <label className="text-sm font-medium text-gray-700 dark:text-gray-300">
                  What type of issue is this?
                </label>
                {categoryOptions.map((option) => (
                  <button
                    key={option.id}
                    onClick={() => setSelectedCategory(option.id)}
                    aria-pressed={selectedCategory === option.id}
                    className={`w-full text-left p-3 rounded-lg border-2 transition-all ${
                      selectedCategory === option.id
                        ? "border-amber-500 bg-amber-50 dark:bg-amber-900/20"
                        : "border-gray-200 dark:border-gray-700 hover:border-gray-300"
                    }`}
                  >
                    <div className="font-medium text-sm text-gray-900 dark:text-gray-100">
                      {option.label}
                    </div>
                    <div className="text-xs text-gray-600 dark:text-gray-400">
                      {option.description}
                    </div>
                  </button>
                ))}
              </div>

              {/* Details */}
              <div>
                <label className="text-sm font-medium text-gray-700 dark:text-gray-300">
                  Additional details (optional)
                </label>
                <textarea
                  value={details}
                  onChange={(e) => setDetails(e.target.value)}
                  placeholder="Provide additional details about the inaccuracy..."
                  className="w-full mt-1 px-3 py-2 bg-gray-100 dark:bg-gray-700 border-0 rounded-lg text-sm text-gray-900 dark:text-gray-100 placeholder-gray-500 resize-none h-20 focus:ring-2 focus:ring-amber-500"
                />
              </div>
            </div>

            {/* Footer */}
            <div className="px-5 py-4 border-t border-gray-200 dark:border-gray-700 flex justify-end gap-3">
              <button
                onClick={handleCancel}
                aria-label="Cancel"
                className="px-4 py-2 text-sm text-gray-600 dark:text-gray-400 hover:text-gray-800 dark:hover:text-gray-200"
              >
                Cancel
              </button>
              <button
                onClick={handleSubmit}
                disabled={!selectedCategory}
                aria-label="Submit"
                className={`px-4 py-2 text-sm rounded-lg ${
                  selectedCategory
                    ? "bg-amber-600 text-white hover:bg-amber-700"
                    : "bg-gray-200 text-gray-400 cursor-not-allowed"
                }`}
              >
                Submit
              </button>
            </div>
          </div>
        </div>
      )}
    </>
  );
}

export default HallucinationIndicator;
