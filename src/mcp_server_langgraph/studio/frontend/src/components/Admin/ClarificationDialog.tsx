/**
 * ClarificationDialog Component
 *
 * Modal dialog for responding to agent clarification requests.
 *
 * Features:
 * - Text input for free-form responses
 * - Choice selection for multiple options
 * - Confirmation (yes/no) dialogs
 * - Recommended option highlighting
 * - Loading states
 * - Keyboard accessibility
 *
 * Reference: Plan - Confidence-Based Human-in-the-Loop (HITL) for Multi-Agent Orchestrator
 */

import { useState, useEffect, useCallback } from "react";
import {
  X,
  HelpCircle,
  Loader2,
  Check,
  XCircle,
  AlertTriangle,
} from "lucide-react";
import type {
  AgentClarificationRequest,
  ClarificationUIResponse,
} from "../../types/hitl";

// =============================================================================
// Types
// =============================================================================

// Re-export from canonical location for backwards compatibility
export type {
  ClarificationOption,
  AgentClarificationRequest,
} from "../../types/hitl";

// Alias ClarificationUIResponse as ClarificationResponse for backwards compatibility
export type ClarificationResponse = ClarificationUIResponse;

export interface ClarificationDialogProps {
  /** The clarification request to display */
  request: AgentClarificationRequest;
  /** Whether the dialog is open */
  isOpen: boolean;
  /** Callback to close the dialog */
  onClose: () => void;
  /** Callback when response is submitted */
  onRespond: (response: ClarificationResponse) => void;
  /** Loading state for submission */
  isSubmitting?: boolean;
  /** Error message */
  error?: string | null;
  /** Current user email for attribution */
  currentUser?: string;
}

// =============================================================================
// Main Component
// =============================================================================

export function ClarificationDialog({
  request,
  isOpen,
  onClose,
  onRespond,
  isSubmitting = false,
  error = null,
  currentUser = "unknown",
}: ClarificationDialogProps) {
  const [textValue, setTextValue] = useState("");
  const [selectedOptionId, setSelectedOptionId] = useState<string | null>(null);

  // Reset state when dialog opens/closes
  useEffect(() => {
    if (isOpen) {
      setTextValue("");
      setSelectedOptionId(null);
    }
  }, [isOpen]);

  // Handle Escape key
  const handleKeyDown = useCallback(
    (e: KeyboardEvent) => {
      if (e.key === "Escape" && isOpen) {
        onClose();
      }
    },
    [isOpen, onClose],
  );

  useEffect(() => {
    document.addEventListener("keydown", handleKeyDown);
    return () => document.removeEventListener("keydown", handleKeyDown);
  }, [handleKeyDown]);

  // Handle text submit
  const handleTextSubmit = () => {
    onRespond({
      request_id: request.request_id,
      value: textValue,
      responded_by: currentUser,
    });
  };

  // Handle choice submit
  const handleChoiceSubmit = () => {
    if (selectedOptionId) {
      onRespond({
        request_id: request.request_id,
        selected_option_id: selectedOptionId,
        responded_by: currentUser,
      });
    }
  };

  // Handle confirmation
  const handleConfirmation = (confirmed: boolean) => {
    onRespond({
      request_id: request.request_id,
      confirmed,
      responded_by: currentUser,
    });
  };

  if (!isOpen) {
    return null;
  }

  const isTextType = request.clarification_type === "text";
  const isChoiceType = request.clarification_type === "choice";
  const isConfirmationType = request.clarification_type === "confirmation";

  const canSubmit = isTextType
    ? textValue.trim().length > 0 || !request.required
    : isChoiceType
      ? selectedOptionId !== null
      : false;

  // Check if confirmation context has destructive indicators
  const hasDestructiveContext =
    request.context.operation === "delete" ||
    String(request.question).toLowerCase().includes("delete");

  return (
    <div
      role="dialog"
      aria-modal="true"
      className="fixed inset-0 z-50 flex items-center justify-center"
    >
      {/* Backdrop */}
      <div
        className="absolute inset-0 bg-black/50"
        onClick={onClose}
        aria-hidden="true"
      />

      {/* Dialog */}
      <div className="relative bg-white dark:bg-gray-900 rounded-lg shadow-xl max-w-lg w-full mx-4 max-h-[90vh] overflow-hidden">
        {/* Header */}
        <div className="flex items-center justify-between p-4 border-b border-gray-200 dark:border-gray-700">
          <h2 className="text-lg font-semibold text-gray-900 dark:text-white flex items-center gap-2">
            <HelpCircle className="w-5 h-5 text-blue-500" />
            Agent Needs Your Input
          </h2>
          <button
            data-testid="close-dialog"
            onClick={onClose}
            className="p-2 text-gray-500 hover:text-gray-700 dark:text-gray-400 dark:hover:text-gray-200 hover:bg-gray-100 dark:hover:bg-gray-800 rounded-lg transition-colors"
          >
            <X className="w-5 h-5" />
          </button>
        </div>

        {/* Content */}
        <div className="p-4 space-y-4 overflow-y-auto max-h-[60vh]">
          {/* Error Message */}
          {error && (
            <div className="bg-red-50 dark:bg-red-900/20 border border-red-200 dark:border-red-800 rounded-lg p-3 text-red-700 dark:text-red-400">
              {error}
            </div>
          )}

          {/* Agent Info */}
          <div className="text-sm text-gray-500 dark:text-gray-400">
            Agent:{" "}
            <strong className="text-gray-900 dark:text-white">
              {request.agent_name}
            </strong>
          </div>

          {/* Question */}
          <p className="text-base font-medium text-gray-900 dark:text-white">
            {request.question}
          </p>

          {/* Context Display */}
          {Object.keys(request.context).length > 0 && (
            <div className="bg-gray-50 dark:bg-gray-800/50 rounded-lg p-3 text-sm">
              <div className="text-gray-500 dark:text-gray-400">Context:</div>
              <div className="mt-1 space-y-1">
                {Object.entries(request.context).map(([key, value]) => (
                  <div key={key} className="text-gray-700 dark:text-gray-300">
                    <span className="text-gray-500">{key}:</span>{" "}
                    {String(value)}
                  </div>
                ))}
              </div>
            </div>
          )}

          {/* Text Input */}
          {isTextType && (
            <div>
              <textarea
                data-testid="text-input"
                value={textValue}
                onChange={(e) => setTextValue(e.target.value)}
                placeholder={request.placeholder || "Enter your response..."}
                rows={3}
                disabled={isSubmitting}
                className="w-full px-3 py-2 border border-gray-300 dark:border-gray-600 rounded-lg text-sm text-gray-900 dark:text-white bg-white dark:bg-gray-800 placeholder-gray-400 focus:outline-none focus:ring-2 focus:ring-blue-500 focus:border-transparent disabled:opacity-50 disabled:cursor-not-allowed"
              />
            </div>
          )}

          {/* Choice Options */}
          {isChoiceType && (
            <div className="space-y-2">
              {request.options.map((option) => (
                <button
                  key={option.id}
                  data-testid={`option-${option.id}`}
                  onClick={() => setSelectedOptionId(option.id)}
                  disabled={isSubmitting}
                  className={`w-full text-left p-3 border rounded-lg transition-colors ${
                    selectedOptionId === option.id
                      ? "border-blue-500 bg-blue-50 dark:bg-blue-900/20"
                      : "border-gray-200 dark:border-gray-700 hover:bg-gray-50 dark:hover:bg-gray-800"
                  } disabled:opacity-50 disabled:cursor-not-allowed`}
                >
                  <div className="flex items-center justify-between">
                    <span className="font-medium text-gray-900 dark:text-white">
                      {option.label}
                    </span>
                    {option.is_recommended && (
                      <span className="text-xs px-2 py-0.5 bg-green-100 dark:bg-green-900/30 text-green-700 dark:text-green-400 rounded">
                        Recommended
                      </span>
                    )}
                  </div>
                  {option.description && (
                    <p className="text-sm text-gray-500 dark:text-gray-400 mt-1">
                      {option.description}
                    </p>
                  )}
                </button>
              ))}
            </div>
          )}

          {/* Confirmation */}
          {isConfirmationType && (
            <div
              data-testid="confirmation-warning"
              className={`flex items-start gap-3 rounded-lg p-3 ${
                hasDestructiveContext
                  ? "bg-red-50 dark:bg-red-900/20 border border-red-200 dark:border-red-800"
                  : "bg-amber-50 dark:bg-amber-900/20 border border-amber-200 dark:border-amber-800"
              }`}
            >
              <AlertTriangle
                className={`w-5 h-5 flex-shrink-0 mt-0.5 ${
                  hasDestructiveContext ? "text-red-500" : "text-amber-500"
                }`}
              />
              <div>
                <p
                  className={`font-medium ${
                    hasDestructiveContext
                      ? "text-red-700 dark:text-red-400"
                      : "text-amber-700 dark:text-amber-400"
                  }`}
                >
                  Please confirm to proceed
                </p>
                <p
                  className={`text-sm ${
                    hasDestructiveContext
                      ? "text-red-600 dark:text-red-400/80"
                      : "text-amber-600 dark:text-amber-400/80"
                  }`}
                >
                  This action requires your explicit confirmation.
                </p>
              </div>
            </div>
          )}
        </div>

        {/* Footer */}
        <div className="flex items-center justify-end gap-3 p-4 border-t border-gray-200 dark:border-gray-700 bg-gray-50 dark:bg-gray-800/50">
          {isConfirmationType ? (
            <>
              <button
                data-testid="confirm-no"
                onClick={() => handleConfirmation(false)}
                disabled={isSubmitting}
                className="flex items-center gap-2 px-4 py-2 text-sm font-medium text-red-700 dark:text-red-400 bg-red-100 dark:bg-red-900/30 rounded-lg hover:bg-red-200 dark:hover:bg-red-900/50 disabled:opacity-50 disabled:cursor-not-allowed transition-colors"
              >
                <XCircle className="w-4 h-4" />
                No
              </button>
              <button
                data-testid="confirm-yes"
                onClick={() => handleConfirmation(true)}
                disabled={isSubmitting}
                className="flex items-center gap-2 px-4 py-2 text-sm font-medium text-white bg-green-600 rounded-lg hover:bg-green-700 disabled:opacity-50 disabled:cursor-not-allowed transition-colors"
              >
                {isSubmitting ? (
                  <Loader2
                    data-testid="submit-loading"
                    className="w-4 h-4 animate-spin"
                  />
                ) : (
                  <Check className="w-4 h-4" />
                )}
                Yes, proceed
              </button>
            </>
          ) : (
            <>
              <button
                onClick={onClose}
                className="px-4 py-2 text-sm font-medium text-gray-700 dark:text-gray-300 bg-gray-100 dark:bg-gray-800 rounded-lg hover:bg-gray-200 dark:hover:bg-gray-700 transition-colors"
              >
                Cancel
              </button>
              <button
                data-testid="submit-button"
                onClick={isTextType ? handleTextSubmit : handleChoiceSubmit}
                disabled={!canSubmit || isSubmitting}
                className="flex items-center gap-2 px-4 py-2 text-sm font-medium text-white bg-blue-600 rounded-lg hover:bg-blue-700 disabled:opacity-50 disabled:cursor-not-allowed transition-colors"
              >
                {isSubmitting ? (
                  <Loader2
                    data-testid="submit-loading"
                    className="w-4 h-4 animate-spin"
                  />
                ) : (
                  <Check className="w-4 h-4" />
                )}
                Submit
              </button>
            </>
          )}
        </div>
      </div>
    </div>
  );
}
