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
      button: "bg-blue-600 hover:bg-blue-700 focus:ring-blue-500",
      icon: null,
    },
    warning: {
      button: "bg-yellow-600 hover:bg-yellow-700 focus:ring-yellow-500",
      icon: (
        <AlertTriangle
          data-testid="warning-icon"
          className="h-6 w-6 text-yellow-600"
          aria-hidden="true"
        />
      ),
    },
    danger: {
      button: "bg-red-600 hover:bg-red-700 focus:ring-red-500",
      icon: (
        <AlertCircle
          data-testid="danger-icon"
          className="h-6 w-6 text-red-600"
          aria-hidden="true"
        />
      ),
    },
  };

  const { button: buttonStyle, icon } = severityStyles[severity];

  return (
    <div
      data-testid="dialog-backdrop"
      onClick={handleBackdropClick}
      className="fixed inset-0 z-50 flex items-center justify-center bg-black/50"
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
        className="w-full max-w-md rounded-lg bg-white dark:bg-gray-900 shadow-xl"
      >
        <div className="p-6">
          {/* Header */}
          <div className="flex items-start gap-4">
            {icon && <div className="flex-shrink-0">{icon}</div>}
            <div className="flex-1">
              <h2
                id={titleId}
                className="text-lg font-semibold text-gray-900 dark:text-gray-100"
              >
                {title}
              </h2>
              <p
                id={descriptionId}
                className="mt-2 text-sm text-gray-600 dark:text-gray-400"
              >
                {message}
              </p>
            </div>
          </div>

          {/* Type-to-confirm input */}
          {requiresConfirmText && (
            <div className="mt-4">
              <label className="block text-sm font-medium text-gray-700 dark:text-gray-300">
                Type <span className="font-mono font-bold">{confirmText}</span>{" "}
                to confirm
              </label>
              <input
                type="text"
                value={typedText}
                onChange={(e) => setTypedText(e.target.value)}
                placeholder={`Type ${confirmText} to confirm`}
                className="mt-1 block w-full rounded-md border border-gray-300 dark:border-gray-600 bg-white dark:bg-gray-800 px-3 py-2 text-sm focus:border-red-500 focus:outline-none focus:ring-1 focus:ring-red-500"
              />
            </div>
          )}
        </div>

        {/* Footer */}
        <div className="flex justify-end gap-3 border-t border-gray-200 dark:border-gray-700 px-6 py-4">
          <button
            type="button"
            onClick={onCancel}
            disabled={isLoading}
            className="px-4 py-2 text-sm font-medium text-gray-700 dark:text-gray-300 bg-gray-100 dark:bg-gray-800 rounded-md hover:bg-gray-200 dark:hover:bg-gray-700 focus:outline-none focus:ring-2 focus:ring-gray-500 disabled:opacity-50 disabled:cursor-not-allowed"
          >
            {cancelLabel}
          </button>
          <button
            ref={confirmButtonRef}
            type="button"
            onClick={handleConfirm}
            disabled={isConfirmDisabled}
            className={`px-4 py-2 text-sm font-medium text-white rounded-md focus:outline-none focus:ring-2 focus:ring-offset-2 disabled:opacity-50 disabled:cursor-not-allowed flex items-center gap-2 ${buttonStyle}`}
          >
            {isLoading && (
              <Loader2
                data-testid="loading-spinner"
                className="h-4 w-4 animate-spin"
                aria-hidden="true"
              />
            )}
            {confirmLabel}
          </button>
        </div>
      </div>
    </div>
  );
}

export default ConfirmationDialog;
