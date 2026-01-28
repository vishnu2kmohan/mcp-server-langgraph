/**
 * UninstallDialog Component
 *
 * Confirmation dialog for skill uninstallation.
 * Shows skill name and warning before uninstalling.
 *
 * @see UninstallDialog.test.tsx for TDD test cases
 */

import { useEffect } from "react";
import { Button } from "@/components/UI";

interface UninstallDialogProps {
  /** Skill name to uninstall (null when closed) */
  skillName: string | null;
  /** Whether the dialog is open */
  isOpen: boolean;
  /** Callback to close the dialog */
  onClose: () => void;
  /** Callback when uninstall is confirmed */
  onConfirm: () => void;
  /** Whether uninstallation is in progress */
  isUninstalling: boolean;
}

export function UninstallDialog({
  skillName,
  isOpen,
  onClose,
  onConfirm,
  isUninstalling,
}: UninstallDialogProps): JSX.Element | null {
  // Handle Escape key to close dialog (only if not uninstalling)
  useEffect(() => {
    const handleEscape = (event: KeyboardEvent) => {
      if (event.key === "Escape" && isOpen && !isUninstalling) {
        onClose();
      }
    };

    document.addEventListener("keydown", handleEscape);
    return () => document.removeEventListener("keydown", handleEscape);
  }, [isOpen, isUninstalling, onClose]);

  // Don't render if closed or no skill
  if (!isOpen || !skillName) {
    return null;
  }

  return (
    <div
      className="fixed inset-0 z-50 flex items-center justify-center bg-black/50"
      onClick={onClose}
    >
      <div
        role="dialog"
        aria-modal="true"
        aria-labelledby="uninstall-dialog-title"
        data-testid="uninstall-dialog"
        className="relative mx-4 w-full max-w-md rounded-lg bg-neutral-1 p-6 shadow-xl"
        onClick={(e) => e.stopPropagation()}
      >
        {/* Title */}
        <h2
          id="uninstall-dialog-title"
          className="mb-4 text-lg font-semibold text-neutral-12"
        >
          Uninstall Skill
        </h2>

        {/* Content */}
        <div className="mb-6">
          {isUninstalling ? (
            /* Progress indicator during uninstallation */
            <div
              data-testid="uninstall-progress"
              className="flex flex-col items-center py-4"
            >
              <div className="mb-3 h-8 w-8 animate-spin rounded-full border-2 border-danger-6 border-t-danger-9" />
              <p
                data-testid="uninstall-progress-message"
                className="text-sm text-neutral-11"
              >
                Uninstalling <span className="font-medium">{skillName}</span>...
              </p>
              <p className="mt-1 text-xs text-neutral-10">
                Removing skill and cleaning up
              </p>
            </div>
          ) : (
            /* Confirmation message before uninstallation */
            <>
              <p className="text-sm text-neutral-11">
                Are you sure you want to uninstall{" "}
                <span className="font-medium text-neutral-12">{skillName}</span>
                ?
              </p>
              <p className="mt-2 text-sm text-danger-11">
                This action cannot be undone. Any skill-specific data will be
                removed.
              </p>
            </>
          )}
        </div>

        {/* Actions */}
        <div className="flex justify-end gap-3">
          <Button onClick={onClose} disabled={isUninstalling} variant="outline">
            Cancel
          </Button>
          <Button
            onClick={onConfirm}
            disabled={isUninstalling}
            loading={isUninstalling}
            variant="danger"
            className="bg-danger-9 hover:bg-danger-10 text-white"
          >
            {isUninstalling ? "Uninstalling..." : "Uninstall"}
          </Button>
        </div>
      </div>
    </div>
  );
}
