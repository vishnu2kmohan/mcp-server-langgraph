/**
 * ConfirmDialog Component
 *
 * Styled confirmation dialog to replace native browser confirm().
 * Uses the base Dialog component with destructive action styling.
 */

import { AlertTriangle } from "lucide-react";
import { Dialog } from "./Dialog";

import { Button } from "@/components/UI";

export interface ConfirmDialogProps {
  /** Whether the dialog is open */
  open: boolean;
  /** Callback when dialog should close */
  onClose: () => void;
  /** Callback when user confirms */
  onConfirm: () => void;
  /** Dialog title */
  title: string;
  /** Description/message to show */
  message: string;
  /** Confirm button text (default: "Delete") */
  confirmText?: string;
  /** Cancel button text (default: "Cancel") */
  cancelText?: string;
  /** Whether confirmation is destructive (shows red button) */
  isDestructive?: boolean;
  /** Whether confirm action is in progress */
  isLoading?: boolean;
}

export function ConfirmDialog({
  open,
  onClose,
  onConfirm,
  title,
  message,
  confirmText = "Delete",
  cancelText = "Cancel",
  isDestructive = true,
  isLoading = false,
}: ConfirmDialogProps) {
  const handleConfirm = () => {
    onConfirm();
  };

  return (
    <Dialog
      open={open}
      onClose={onClose}
      title={title}
      size="sm"
      footer={
        <>
          <Button
            variant="secondary"
            className="px-4 py-2 text-sm text-neutral-11 bg-neutral-1 border border-neutral-5 rounded-lg hover:bg-neutral-1 focus:ring-offset-2 focus:ring-neutral-8"
            onClick={onClose}
            disabled={isLoading}
          >
            {cancelText}
          </Button>
          <Button
            className="px-4 py-2 text-sm text-neutral-12 rounded-lg focus:ring-offset-2"
            onClick={handleConfirm}
            disabled={isLoading}
          >
            {isLoading ? (
              <span className="flex items-center gap-2">
                <svg
                  className="animate-spin h-4 w-4"
                  xmlns="http://www.w3.org/2000/svg"
                  fill="none"
                  viewBox="0 0 24 24"
                >
                  <circle
                    className="opacity-25"
                    cx="12"
                    cy="12"
                    r="10"
                    stroke="currentColor"
                    strokeWidth="4"
                  />
                  <path
                    className="opacity-75"
                    fill="currentColor"
                    d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4zm2 5.291A7.962 7.962 0 014 12H0c0 3.042 1.135 5.824 3 7.938l3-2.647z"
                  />
                </svg>
                Processing...
              </span>
            ) : (
              confirmText
            )}
          </Button>
        </>
      }
    >
      <div className="flex gap-4">
        {isDestructive && (
          <div className="flex-shrink-0">
            <div className="w-10 h-10 bg-error-3 bg-error-4 rounded-full flex items-center justify-center">
              <AlertTriangle className="w-5 h-5 text-error-10 dark:text-error-7" />
            </div>
          </div>
        )}
        <div className="flex-1">
          <p className="text-sm text-neutral-11">{message}</p>
        </div>
      </div>
    </Dialog>
  );
}

export default ConfirmDialog;
