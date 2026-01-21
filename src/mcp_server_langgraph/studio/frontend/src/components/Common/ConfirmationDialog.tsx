/**
 * ConfirmationDialog Component
 *
 * Reusable confirmation dialog with severity levels.
 * Features:
 * - Three severity levels: info, warning, danger
 * - Type-to-confirm for dangerous actions
 * - Focus trap and keyboard navigation
 * - Loading state support
 * - Backdrop click to close
 *
 * Implements WCAG 2.1 AA accessibility requirements.
 * Based on UX patterns from Gemini CLI, OpenAI Codex, and Claude Code.
 */

import {
  useState,
  useEffect,
  useRef,
  useCallback,
  useId,
  type KeyboardEvent,
} from "react";
import { AlertTriangle, AlertCircle, Loader2 } from "lucide-react";

import { Button, Input } from "@/components/UI";

// ==============================================================================
// Types
// ==============================================================================

export type DialogSeverity = "info" | "warning" | "danger";

export interface ConfirmationDialogProps {
  /** Whether the dialog is open */
  isOpen: boolean;
  /** Dialog title */
  title: string;
  /** Dialog message/description */
  message: string;
  /** Severity level of the action */
  severity?: DialogSeverity;
  /** Text user must type to confirm (for dangerous actions) */
  confirmText?: string;
  /** Confirm button label */
  confirmLabel?: string;
  /** Cancel button label */
  cancelLabel?: string;
  /** Whether the action is in progress */
  isLoading?: boolean;
  /** Callback when user confirms */
  onConfirm: () => void;
  /** Callback when user cancels */
  onCancel: () => void;
}

// ==============================================================================
// Component
// ==============================================================================

export function ConfirmationDialog({
  isOpen,
  title,
  message,
  severity = "info",
  confirmText,
  confirmLabel = "Confirm",
  cancelLabel = "Cancel",
  isLoading = false,
  onConfirm,
  onCancel,
}: ConfirmationDialogProps) {
  const [typedText, setTypedText] = useState("");
  const dialogRef = useRef<HTMLDivElement>(null);
  const confirmButtonRef = useRef<HTMLButtonElement>(null);
  const titleId = useId();
  const descriptionId = useId();

  // Reset typed text when dialog opens/closes
  useEffect(() => {
    if (isOpen) {
      setTypedText("");
    }
  }, [isOpen]);

  // Focus confirm button when dialog opens
  useEffect(() => {
    if (isOpen && confirmButtonRef.current) {
      confirmButtonRef.current.focus();
    }
  }, [isOpen]);

  // Handle escape key
  useEffect(() => {
    const handleEscape = (e: globalThis.KeyboardEvent) => {
      if (e.key === "Escape" && isOpen && !isLoading) {
        onCancel();
      }
    };

    document.addEventListener("keydown", handleEscape);
    return () => document.removeEventListener("keydown", handleEscape);
  }, [isOpen, isLoading, onCancel]);

  // Focus trap
  const handleKeyDown = useCallback((e: KeyboardEvent<HTMLDivElement>) => {
    if (e.key === "Tab" && dialogRef.current) {
      const focusableElements = dialogRef.current.querySelectorAll<HTMLElement>(
        'button:not([disabled]), [href], input:not([disabled]), select:not([disabled]), textarea:not([disabled]), [tabindex]:not([tabindex="-1"])',
      );

      if (focusableElements.length === 0) return;

      const firstElement = focusableElements[0];
      const lastElement = focusableElements[focusableElements.length - 1];
      if (!firstElement || !lastElement) return;

      if (e.shiftKey && document.activeElement === firstElement) {
        e.preventDefault();
        lastElement.focus();
      } else if (!e.shiftKey && document.activeElement === lastElement) {
        e.preventDefault();
        firstElement.focus();
      }
    }
  }, []);

  // Check if confirm is allowed
  const requiresConfirmText = severity === "danger" && confirmText;
  const isConfirmDisabled = Boolean(
    isLoading || (requiresConfirmText && typedText !== confirmText),
  );

  // Handle backdrop click
  const handleBackdropClick = useCallback(() => {
    if (!isLoading) {
      onCancel();
    }
  }, [isLoading, onCancel]);

  // Handle dialog click (stop propagation)
  const handleDialogClick = useCallback((e: React.MouseEvent) => {
    e.stopPropagation();
  }, []);

  // Handle confirm
  const handleConfirm = useCallback(() => {
    if (!isConfirmDisabled) {
      onConfirm();
    }
  }, [isConfirmDisabled, onConfirm]);

  if (!isOpen) {
    return null;
  }

  // Severity-based styles
  const severityStyles = {
    info: {
      button: "bg-primary-10 hover:bg-primary-11 focus:ring-primary-7",
      icon: null,
    },
    warning: {
      button: "bg-warning-9 hover:bg-warning-10 focus:ring-warning-7",
      icon: (
        <AlertTriangle
          data-testid="warning-icon"
          className="h-6 w-6 text-warning-9"
          aria-hidden="true"
        />
      ),
    },
    danger: {
      button: "bg-error-10 hover:bg-error-11 focus:ring-error-7",
      icon: (
        <AlertCircle
          data-testid="danger-icon"
          className="h-6 w-6 text-error-10"
          aria-hidden="true"
        />
      ),
    },
  };

  const { button: _buttonStyle, icon } = severityStyles[severity];

  return (
    <div
      data-testid="dialog-backdrop"
      onClick={handleBackdropClick}
      className="fixed inset-0 z-50 flex items-center justify-center bg-neutral-a6"
    >
      <div
        ref={dialogRef}
        role="dialog"
        aria-modal="true"
        aria-labelledby={titleId}
        aria-describedby={descriptionId}
        data-severity={severity}
        onClick={handleDialogClick}
        onKeyDown={handleKeyDown}
        className="w-full max-w-md rounded-lg bg-neutral-1 shadow-xl"
      >
        <div className="p-6">
          {/* Header */}
          <div className="flex items-start gap-4">
            {icon && <div className="flex-shrink-0">{icon}</div>}
            <div className="flex-1">
              <h2
                id={titleId}
                className="text-lg font-semibold text-neutral-12"
              >
                {title}
              </h2>
              <p
                id={descriptionId}
                className="mt-2 text-sm text-neutral-11"
              >
                {message}
              </p>
            </div>
          </div>

          {/* Type-to-confirm input */}
          {requiresConfirmText && (
            <div className="mt-4">
              <label className="block text-sm font-medium text-neutral-11">
                Type <span className="font-mono font-bold">{confirmText}</span>{" "}
                to confirm
              </label>
              <Input
                variant="error"
                className="mt-1 px-3 py-2 text-sm -500 focus:ring-error-7"
                value={typedText}
                onChange={(e) => setTypedText(e.target.value)}
                placeholder={`Type ${confirmText} to confirm`}
              />
            </div>
          )}
        </div>

        {/* Footer */}
        <div className="flex justify-end gap-3 border-t border-neutral-5 px-6 py-4">
          <Button
            variant="secondary"
            className="px-4 py-2 text-sm text-neutral-11 bg-neutral-2 rounded-md hover:bg-neutral-3 focus:ring-neutral-8"
            type="button"
            onClick={onCancel}
            disabled={isLoading}
          >
            {cancelLabel}
          </Button>
          <Button
            variant="primary"
            className="px-4 py-2 text-sm text-neutral-12 rounded-md focus:ring-offset-2 flex"
            ref={confirmButtonRef}
            type="button"
            onClick={handleConfirm}
            disabled={isConfirmDisabled}>
            {isLoading && (
              <Loader2
                data-testid="loading-spinner"
                className="h-4 w-4 animate-spin"
                aria-hidden="true"
              />
            )}
            {confirmLabel}
          </Button>
        </div>
      </div>
    </div>
  );
}

export default ConfirmationDialog;
