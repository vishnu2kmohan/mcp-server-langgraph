/**
 * RemoveMarketplaceDialog Component
 *
 * Confirmation dialog for removing a skill marketplace.
 * Warns user about consequences before removal.
 *
 * Following STYLE.md conventions:
 * - Radix 1-12 color scale (semantic colors)
 * - Focus-visible rings for keyboard navigation
 * - UI Button component for consistent styling
 */

import { useEffect } from "react";
import { AlertTriangle, Loader2 } from "lucide-react";
import { Button } from "@/components/UI";

// =============================================================================
// Types
// =============================================================================

export interface RemoveMarketplaceDialogProps {
  /** Name of the marketplace to remove */
  marketplaceName: string | null;
  /** Whether the dialog is open */
  isOpen: boolean;
  /** Callback when dialog closes */
  onClose: () => void;
  /** Callback when removal is confirmed */
  onConfirm: () => void;
  /** Loading state for removal */
  isRemoving?: boolean;
}

// =============================================================================
// Component
// =============================================================================

export function RemoveMarketplaceDialog({
  marketplaceName,
  isOpen,
  onClose,
  onConfirm,
  isRemoving = false,
}: RemoveMarketplaceDialogProps) {
  // Handle Escape key
  useEffect(() => {
    const handleKeyDown = (e: KeyboardEvent) => {
      if (e.key === "Escape" && isOpen && !isRemoving) {
        onClose();
      }
    };

    document.addEventListener("keydown", handleKeyDown);
    return () => document.removeEventListener("keydown", handleKeyDown);
  }, [isOpen, isRemoving, onClose]);

  // Don't render if not open or no marketplace name
  if (!isOpen || !marketplaceName) {
    return null;
  }

  return (
    <div
      className="fixed inset-0 z-50 flex items-center justify-center"
      data-testid="remove-marketplace-dialog-backdrop"
      onClick={onClose}
    >
      {/* Backdrop */}
      <div className="absolute inset-0 bg-overlay-6" aria-hidden="true" />

      {/* Dialog */}
      <div
        role="dialog"
        aria-modal="true"
        aria-labelledby="remove-marketplace-title"
        data-testid="remove-marketplace-dialog"
        className="relative z-10 w-full max-w-md rounded-xl bg-neutral-1 p-6 shadow-xl"
        onClick={(e) => e.stopPropagation()}
      >
        {/* Warning Icon */}
        <div className="mb-4 flex justify-center">
          <div className="flex h-12 w-12 items-center justify-center rounded-full bg-error-3">
            <AlertTriangle
              className="h-6 w-6 text-error-11"
              aria-hidden="true"
            />
          </div>
        </div>

        {/* Title */}
        <h2
          id="remove-marketplace-title"
          className="mb-2 text-center text-lg font-semibold text-neutral-12"
        >
          Remove Marketplace
        </h2>

        {/* Confirmation message */}
        <p className="mb-2 text-center text-sm text-neutral-11">
          Are you sure you want to remove{" "}
          <span className="font-medium text-neutral-12">{marketplaceName}</span>
          ?
        </p>

        {/* Warning about consequences */}
        <p className="mb-6 text-center text-sm text-neutral-10">
          Skills from this marketplace will no longer be available for
          installation. Installed skills will not be affected.
        </p>

        {/* Actions */}
        <div className="flex justify-center gap-3">
          <Button variant="secondary" onClick={onClose} disabled={isRemoving}>
            Cancel
          </Button>
          <Button
            variant="danger"
            onClick={onConfirm}
            disabled={isRemoving}
            className="gap-2"
          >
            {isRemoving ? (
              <>
                <Loader2 className="h-4 w-4 animate-spin" aria-hidden="true" />
                Removing...
              </>
            ) : (
              "Remove"
            )}
          </Button>
        </div>
      </div>
    </div>
  );
}
