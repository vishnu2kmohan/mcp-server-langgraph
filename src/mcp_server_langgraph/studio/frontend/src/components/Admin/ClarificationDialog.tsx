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
import { useReducedMotion } from "motion/react";
import { useFocusTrap } from "../../hooks/useFocusTrap";
import { cn } from "../../utils/cn";
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
  // WCAG 2.2 AA: Respect user's reduced motion preference
  const prefersReducedMotion = useReducedMotion();

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
        className="absolute inset-0 bg-neutral-a6"
        onClick={onClose}
        aria-hidden="true"
      />
      {/* Dialog */}
      <div className="relative bg-neutral-1 rounded-lg shadow-xl max-w-lg w-full mx-4 max-h-[90vh] overflow-hidden">
        {/* Header */}
        <div className="flex items-center justify-between p-4 border-b border-neutral-5">
          <h2 className="text-lg font-semibold text-neutral-12 flex items-center gap-2">
            <HelpCircle className="w-5 h-5 text-primary-9" />
            Agent Needs Your Input
          </h2>
          <Button size="icon"
            variant="secondary"
            className="p-2 text-neutral-10 hover:text-neutral-11 hover:bg-neutral-2 rounded-lg"
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
            <div className="bg-error-1 dark:bg-error-a3 border border-error-4 dark:border-error-11 rounded-lg p-3 text-error-11 dark:text-error-7">
              {error}
            </div>
          )}

          {/* Agent Info */}
          <div className="text-sm text-neutral-10">
            Agent:{" "}
            <strong className="text-neutral-12">
              {request.agentName}
            </strong>
          </div>

          {/* Question */}
          <p className="text-base font-medium text-neutral-12">
            {request.question}
          </p>

          {/* Context Display */}
          {Object.keys(request.context).length > 0 && (
            <div className="bg-neutral-1 rounded-lg p-3 text-sm">
              <div className="text-neutral-10">
                Context:
              </div>
              <div className="mt-1 space-y-1">
                {Object.entries(request.context).map(([key, value]) => (
                  <div
                    key={key}
                    className="text-neutral-11"
                  >
                    <span className="text-neutral-10">
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
                className="px-3 py-2 text-sm text-neutral-12 placeholder-neutral-9 focus:ring-primary-7 disabled:opacity-50 disabled:cursor-not-allowed"
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
                  variant="primary"
                  className="w-full text-left p-3 border rounded-lg"
                  key={option.id}
                  data-testid={`option-${option.id}`}
                  onClick={() => setSelectedOptionId(option.id)}
                  disabled={isSubmitting}>
                  <div className="flex items-center justify-between">
                    <span className="font-medium text-neutral-12">
                      {option.label}
                    </span>
                    {option.isRecommended && (
                      <span className="text-xs px-2 py-0.5 bg-success-3 bg-success-4 text-success-11 dark:text-success-7 rounded">
                        Recommended
                      </span>
                    )}
                  </div>
                  {option.description && (
                    <p className="text-sm text-neutral-10 mt-1">
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
                  ? "bg-error-1 dark:bg-error-a3 border border-error-4 dark:border-error-11"
                  : "bg-warning-3 bg-warning-3 border border-warning-6 dark:border-warning-11"
              }`}
            >
              <AlertTriangle
                className={`w-5 h-5 flex-shrink-0 mt-0.5 ${
                  hasDestructiveContext ? "text-error-9" : "text-warning-9"
                }`}
              />
              <div>
                <p
                  className={`font-medium ${
                    hasDestructiveContext
                      ? "text-error-11 dark:text-error-7"
                      : "text-warning-10 dark:text-warning-9"
                  }`}
                >
                  Please confirm to proceed
                </p>
                <p
                  className={`text-sm ${
                    hasDestructiveContext
                      ? "text-error-10 dark:text-error-a9"
                      : "text-warning-9 dark:text-warning-a9"
                  }`}
                >
                  This action requires your explicit confirmation.
                </p>
              </div>
            </div>
          )}
        </div>

        {/* Footer */}
        <div className="flex items-center justify-end gap-3 p-4 border-t border-neutral-5 bg-neutral-1">
          {isConfirmationType ? (
            <>
              <Button
                variant="danger"
                className="flex px-4 py-2 text-sm text-error-11 dark:text-error-7 bg-error-3 bg-error-4 rounded-lg hover:bg-error-4 dark:hover:bg-error-a6"
                data-testid="confirm-no"
                onClick={() => handleConfirmation(false)}
                disabled={isSubmitting}
              >
                <XCircle className="w-4 h-4" />
                No
              </Button>
              <Button
                variant="success"
                className="flex px-4 py-2 text-sm text-neutral-12 bg-success-10 rounded-lg hover:bg-success-11"
                data-testid="confirm-yes"
                onClick={() => handleConfirmation(true)}
                disabled={isSubmitting}
              >
                {isSubmitting ? (
                  <Loader2
                    data-testid="submit-loading"
                    className={cn("w-4 h-4", !prefersReducedMotion && "animate-spin")}
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
                className="px-4 py-2 text-sm text-neutral-11 bg-neutral-2 rounded-lg hover:bg-neutral-3"
                onClick={onClose}
              >
                Cancel
              </Button>
              <Button
                variant="primary"
                className="flex px-4 py-2 text-sm text-neutral-12 bg-primary-10 rounded-lg hover:bg-primary-11"
                data-testid="submit-button"
                onClick={isTextType ? handleTextSubmit : handleChoiceSubmit}
                disabled={!canSubmit || isSubmitting}
              >
                {isSubmitting ? (
                  <Loader2
                    data-testid="submit-loading"
                    className={cn("w-4 h-4", !prefersReducedMotion && "animate-spin")}
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
