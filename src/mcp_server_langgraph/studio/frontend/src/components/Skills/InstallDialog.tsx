/**
 * InstallDialog Component
 *
 * Confirmation dialog for skill installation.
 * Shows skill info and confirmation buttons.
 *
 * @see InstallDialog.test.tsx for TDD test cases
 */

import { useEffect } from "react";
import { Button } from "@/components/UI";
import type { SkillMetadata } from "../../types/skills";

interface InstallDialogProps {
  /** Skill to install (null when closed) */
  skill: SkillMetadata | null;
  /** Whether the dialog is open */
  isOpen: boolean;
  /** Callback to close the dialog */
  onClose: () => void;
  /** Callback when install is confirmed */
  onConfirm: () => void;
  /** Whether installation is in progress */
  isInstalling: boolean;
}

export function InstallDialog({
  skill,
  isOpen,
  onClose,
  onConfirm,
  isInstalling,
}: InstallDialogProps): JSX.Element | null {
  // Handle Escape key to close dialog (only if not installing)
  useEffect(() => {
    const handleEscape = (event: KeyboardEvent) => {
      if (event.key === "Escape" && isOpen && !isInstalling) {
        onClose();
      }
    };

    document.addEventListener("keydown", handleEscape);
    return () => document.removeEventListener("keydown", handleEscape);
  }, [isOpen, isInstalling, onClose]);

  // Don't render if closed or no skill
  if (!isOpen || !skill) {
    return null;
  }

  return (
    <div
      className="fixed inset-0 z-50 flex items-center justify-center bg-overlay-6"
      onClick={onClose}
    >
      <div
        role="dialog"
        aria-modal="true"
        aria-labelledby="install-dialog-title"
        data-testid="install-dialog"
        className="relative mx-4 w-full max-w-md rounded-lg bg-neutral-1 p-6 shadow-xl"
        onClick={(e) => e.stopPropagation()}
      >
        {/* Title */}
        <h2
          id="install-dialog-title"
          className="mb-4 text-lg font-semibold text-neutral-12"
        >
          Install Skill
        </h2>

        {/* Content */}
        <div className="mb-6">
          {isInstalling ? (
            /* Progress indicator during installation */
            <div
              data-testid="install-progress"
              className="flex flex-col items-center py-4"
            >
              <div className="mb-3 h-8 w-8 animate-spin rounded-full border-2 border-primary-6 border-t-primary-9" />
              <p
                data-testid="install-progress-message"
                className="text-sm text-neutral-11"
              >
                Installing <span className="font-medium">{skill.name}</span>...
              </p>
              <p className="mt-1 text-xs text-neutral-10">
                This may take a few moments
              </p>
            </div>
          ) : (
            /* Confirmation message before installation */
            <>
              <p className="text-sm text-neutral-11">
                Are you sure you want to install{" "}
                <span className="font-medium text-neutral-12">
                  {skill.name}
                </span>
                ?
              </p>
              <p className="mt-2 text-sm text-neutral-10">
                Version: {skill.version}
              </p>
            </>
          )}
        </div>

        {/* Actions */}
        <div className="flex justify-end gap-3">
          <Button onClick={onClose} disabled={isInstalling} variant="outline">
            Cancel
          </Button>
          <Button
            onClick={onConfirm}
            disabled={isInstalling}
            loading={isInstalling}
            variant="primary"
          >
            {isInstalling ? "Installing..." : "Install"}
          </Button>
        </div>
      </div>
    </div>
  );
}
