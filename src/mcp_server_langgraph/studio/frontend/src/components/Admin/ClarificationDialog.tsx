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

import { useState, useEffect, useCallback, useRef } from "react";
import { useFocusTrap } from "../../hooks/useFocusTrap";
import {
  X,
  HelpCircle,
  Loader2,
  Check,
  XCircle,
  AlertTriangle,
} from "lucide-react";
import type {
  AgentClarificationRequestCamelCase,
  ClarificationUIResponseCamelCase,
} from "../../types/hitl";

import { Button, Textarea } from "@/components/UI";

// =============================================================================
// Types
// =============================================================================

// Re-export camelCase type for external consumers (ADR-0091 Phase 10)
export type { AgentClarificationRequestCamelCase } from "../../types/hitl";

// Alias for backwards compatibility
export type ClarificationResponse = ClarificationUIResponseCamelCase;

export interface ClarificationDialogProps {
  /** The clarification request to display (camelCase per ADR-0091) */
  request: AgentClarificationRequestCamelCase;
  /** Whether the dialog is open */
  isOpen: boolean;
  /** Callback to close the dialog */
  onClose: () => void;
  /** Callback when response is submitted (camelCase per ADR-0091) */
  onRespond: (response: ClarificationUIResponseCamelCase) => void;
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

  // Focus trap for WCAG 2.1 AA compliance (Sprint 5.2)
  const dialogRef = useRef<HTMLDivElement>(null);
  useFocusTrap(dialogRef, isOpen);

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

  // Handle text submit (camelCase per ADR-0091)
  const handleTextSubmit = () => {
    onRespond({
      requestId: request.requestId,
      value: textValue,
      respondedBy: currentUser,
    });
  };

  // Handle choice submit (camelCase per ADR-0091)
  const handleChoiceSubmit = () => {
    if (selectedOptionId) {
      onRespond({
        requestId: request.requestId,
        selectedOptionId: selectedOptionId,
        respondedBy: currentUser,
      });
    }
  };

  // Handle confirmation (camelCase per ADR-0091)
  const handleConfirmation = (confirmed: boolean) => {
    onRespond({
      requestId: request.requestId,
      confirmed,
      respondedBy: currentUser,
    });
  };

  if (!isOpen) {
    return null;
  }

  const isTextType = request.clarificationType === "text";
  const isChoiceType = request.clarificationType === "choice";
  const isConfirmationType = request.clarificationType === "confirmation";

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
      ref={dialogRef}
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
      <div className="relative bg-white dark:bg-neutral-900 rounded-lg shadow-xl max-w-lg w-full mx-4 max-h-[90vh] overflow-hidden">
        {/* Header */}
        <div className="flex items-center justify-between p-4 border-b border-neutral-200 dark:border-neutral-700">
          <h2 className="text-lg font-semibold text-neutral-900 dark:text-white flex items-center gap-2">
            <HelpCircle className="w-5 h-5 text-primary-500" />
            Agent Needs Your Input
          </h2>
          <Button
            variant="secondary"
            className="p-2 text-neutral-500 dark:text-neutral-400 hover:text-neutral-700 dark:text-neutral-200 dark:text-neutral-400 dark:hover:text-neutral-200 hover:bg-neutral-100 dark:bg-neutral-800 dark:hover:bg-neutral-800 rounded-lg"
            data-testid="close-dialog"
            onClick={onClose}
          >
            <X className="w-5 h-5" />
          </Button>
        </div>

        {/* Content */}
        <div className="p-4 space-y-4 overflow-y-auto max-h-[60vh]">
          {/* Error Message */}
          {error && (
            <div className="bg-error-50 dark:bg-error-900/20 border border-error-200 dark:border-error-800 rounded-lg p-3 text-error-700 dark:text-error-400">
              {error}
            </div>
          )}

          {/* Agent Info */}
          <div className="text-sm text-neutral-500 dark:text-neutral-400">
            Agent:{" "}
            <strong className="text-neutral-900 dark:text-white">
              {request.agentName}
            </strong>
          </div>

          {/* Question */}
          <p className="text-base font-medium text-neutral-900 dark:text-white">
            {request.question}
          </p>

          {/* Context Display */}
          {Object.keys(request.context).length > 0 && (
            <div className="bg-neutral-50 dark:bg-neutral-800/50 rounded-lg p-3 text-sm">
              <div className="text-neutral-500 dark:text-neutral-400">
                Context:
              </div>
              <div className="mt-1 space-y-1">
                {Object.entries(request.context).map(([key, value]) => (
                  <div
                    key={key}
                    className="text-neutral-700 dark:text-neutral-300"
                  >
                    <span className="text-neutral-500 dark:text-neutral-400">
                      {key}:
                    </span>{" "}
                    {String(value)}
                  </div>
                ))}
              </div>
            </div>
          )}

          {/* Text Input */}
          {isTextType && (
            <div>
              <Textarea
                className="px-3 py-2 text-sm text-neutral-900 dark:text-white placeholder-neutral-400 focus:ring-primary-500 disabled:opacity-50 disabled:cursor-not-allowed"
                data-testid="text-input"
                value={textValue}
                onChange={(e) => setTextValue(e.target.value)}
                placeholder={request.placeholder || "Enter your response..."}
                rows={3}
                disabled={isSubmitting}
              />
            </div>
          )}

          {/* Choice Options */}
          {isChoiceType && (
            <div className="space-y-2">
              {request.options.map((option) => (
                <Button
                  className="w-full text-left p-3 border rounded-lg"
                  key={option.id}
                  data-testid={`option-${option.id}`}
                  onClick={() => setSelectedOptionId(option.id)}
                  disabled={isSubmitting}
                >
                  <div className="flex items-center justify-between">
                    <span className="font-medium text-neutral-900 dark:text-white">
                      {option.label}
                    </span>
                    {option.isRecommended && (
                      <span className="text-xs px-2 py-0.5 bg-success-100 dark:bg-success-900/30 text-success-700 dark:text-success-400 rounded">
                        Recommended
                      </span>
                    )}
                  </div>
                  {option.description && (
                    <p className="text-sm text-neutral-500 dark:text-neutral-400 mt-1">
                      {option.description}
                    </p>
                  )}
                </Button>
              ))}
            </div>
          )}

          {/* Confirmation */}
          {isConfirmationType && (
            <div
              data-testid="confirmation-warning"
              className={`flex items-start gap-3 rounded-lg p-3 ${
                hasDestructiveContext
                  ? "bg-error-50 dark:bg-error-900/20 border border-error-200 dark:border-error-800"
                  : "bg-warning-50 dark:bg-warning-900/20 border border-warning-200 dark:border-warning-800"
              }`}
            >
              <AlertTriangle
                className={`w-5 h-5 flex-shrink-0 mt-0.5 ${
                  hasDestructiveContext ? "text-error-500" : "text-warning-500"
                }`}
              />
              <div>
                <p
                  className={`font-medium ${
                    hasDestructiveContext
                      ? "text-error-700 dark:text-error-400"
                      : "text-warning-700 dark:text-warning-400"
                  }`}
                >
                  Please confirm to proceed
                </p>
                <p
                  className={`text-sm ${
                    hasDestructiveContext
                      ? "text-error-600 dark:text-error-400/80"
                      : "text-warning-600 dark:text-warning-400/80"
                  }`}
                >
                  This action requires your explicit confirmation.
                </p>
              </div>
            </div>
          )}
        </div>

        {/* Footer */}
        <div className="flex items-center justify-end gap-3 p-4 border-t border-neutral-200 dark:border-neutral-700 bg-neutral-50 dark:bg-neutral-800/50">
          {isConfirmationType ? (
            <>
              <Button
                variant="danger"
                className="flex px-4 py-2 text-sm text-error-700 dark:text-error-400 bg-error-100 dark:bg-error-900/30 rounded-lg hover:bg-error-200 dark:hover:bg-error-900/50"
                data-testid="confirm-no"
                onClick={() => handleConfirmation(false)}
                disabled={isSubmitting}
              >
                <XCircle className="w-4 h-4" />
                No
              </Button>
              <Button
                variant="success"
                className="flex px-4 py-2 text-sm text-white bg-success-600 rounded-lg hover:bg-success-700"
                data-testid="confirm-yes"
                onClick={() => handleConfirmation(true)}
                disabled={isSubmitting}
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
              </Button>
            </>
          ) : (
            <>
              <Button
                variant="secondary"
                className="px-4 py-2 text-sm text-neutral-700 dark:text-neutral-300 bg-neutral-100 dark:bg-neutral-800 rounded-lg hover:bg-neutral-200 dark:bg-neutral-700 dark:hover:bg-neutral-700"
                onClick={onClose}
              >
                Cancel
              </Button>
              <Button
                variant="primary"
                className="flex px-4 py-2 text-sm text-white bg-primary-600 rounded-lg hover:bg-primary-700"
                data-testid="submit-button"
                onClick={isTextType ? handleTextSubmit : handleChoiceSubmit}
                disabled={!canSubmit || isSubmitting}
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
              </Button>
            </>
          )}
        </div>
      </div>
    </div>
  );
}
