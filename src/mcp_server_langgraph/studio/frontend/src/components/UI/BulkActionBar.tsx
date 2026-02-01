/**
 * BulkActionBar Component
 *
 * A toolbar for bulk actions on selected items.
 * Features:
 * - Display selected count
 * - Clear selection button
 * - Delete action with confirmation
 * - Loading state during operations
 * - Custom action support
 */

import { useState, type ReactNode } from "react";

import { Button } from "@/components/UI";

/**
 * Custom action configuration
 */
export interface BulkAction {
  /** Button label */
  label: string;
  /** Click handler */
  onClick: () => void | Promise<void>;
  /** Optional icon */
  icon?: ReactNode;
  /** Whether this is a destructive action requiring confirmation */
  destructive?: boolean;
  /** Custom confirmation message for destructive actions */
  confirmMessage?: string;
}

/**
 * Props for BulkActionBar component
 */
export interface BulkActionBarProps {
  /** Number of selected items */
  selectedCount: number;
  /** Handler to clear selection */
  onClearSelection: () => void;
  /** Handler for delete action */
  onDelete: () => void | Promise<void>;
  /** Custom actions to display */
  customActions?: BulkAction[];
  /** Additional CSS class */
  className?: string;
}

/**
 * Bulk action toolbar component
 */
export function BulkActionBar({
  selectedCount,
  onClearSelection,
  onDelete,
  customActions = [],
  className = "",
}: BulkActionBarProps) {
  const [showDeleteConfirm, setShowDeleteConfirm] = useState(false);
  const [isDeleting, setIsDeleting] = useState(false);
  const [pendingCustomAction, setPendingCustomAction] =
    useState<BulkAction | null>(null);
  const [isCustomActionLoading, setIsCustomActionLoading] = useState(false);

  // Don't render if no items selected
  if (selectedCount === 0) {
    return null;
  }

  const handleDeleteClick = () => {
    setShowDeleteConfirm(true);
  };

  const handleDeleteConfirm = async () => {
    setIsDeleting(true);
    try {
      await onDelete();
    } finally {
      setIsDeleting(false);
      setShowDeleteConfirm(false);
    }
  };

  const handleDeleteCancel = () => {
    setShowDeleteConfirm(false);
  };

  const handleCustomActionClick = (action: BulkAction) => {
    if (action.destructive) {
      setPendingCustomAction(action);
    } else {
      action.onClick();
    }
  };

  const handleCustomActionConfirm = async () => {
    if (!pendingCustomAction) return;
    setIsCustomActionLoading(true);
    try {
      await pendingCustomAction.onClick();
    } finally {
      setIsCustomActionLoading(false);
      setPendingCustomAction(null);
    }
  };

  const handleCustomActionCancel = () => {
    setPendingCustomAction(null);
  };

  return (
    <div
      role="toolbar"
      aria-label="Bulk actions"
      className={`fixed bottom-0 left-0 right-0 bg-neutral-1 border-t border-neutral-5 px-4 py-3 flex items-center justify-between shadow-lg ${className}`}
    >
      {/* Selection count */}
      <div className="flex items-center gap-4">
        <span role="status" className="text-sm font-medium text-neutral-11">
          {selectedCount} selected
        </span>
        <Button
          variant="danger"
          className="text-sm text-neutral-10 hover:text-neutral-11"
          type="button"
          aria-label="Clear selection"
          onClick={onClearSelection}
        >
          Clear
        </Button>
      </div>
      {/* Actions */}
      <div className="flex items-center gap-2">
        {/* Custom actions */}
        {customActions.map((action) => (
          <Button
            variant="secondary"
            className="px-3 py-1.5 text-sm rounded-md bg-neutral-2 hover:bg-neutral-3 text-neutral-11"
            key={action.label}
            type="button"
            onClick={() => handleCustomActionClick(action)}
          >
            {action.icon}
            {action.label}
          </Button>
        ))}

        {/* Delete button */}
        <Button
          variant="danger"
          className="px-3 py-1.5 text-sm rounded-md bg-error-3 hover:bg-error-4 dark:bg-error-12 dark:hover:bg-error-11 text-error-11 dark:text-error-9"
          type="button"
          onClick={handleDeleteClick}
        >
          Delete
        </Button>
      </div>
      {/* Delete confirmation dialog */}
      {showDeleteConfirm && (
        <div className="fixed inset-0 bg-neutral-12 bg-opacity-50 flex items-center justify-center z-modal">
          <div className="bg-neutral-1 rounded-lg p-6 max-w-sm mx-4 shadow-xl">
            <h3 className="text-lg font-semibold text-neutral-12 mb-2">
              Are you sure?
            </h3>
            <p className="text-sm text-neutral-11 mb-4">
              This will delete {selectedCount} items. This action cannot be
              undone.
            </p>
            <div className="flex justify-end gap-2">
              <Button
                variant="secondary"
                className="px-3 py-1.5 text-sm rounded-md bg-neutral-2 hover:bg-neutral-3 text-neutral-11"
                type="button"
                onClick={handleDeleteCancel}
                disabled={isDeleting}
              >
                Cancel
              </Button>
              <Button
                variant="danger"
                className="px-3 py-1.5 text-sm rounded-md bg-error-10 hover:bg-error-11 text-neutral-12"
                type="button"
                onClick={handleDeleteConfirm}
                disabled={isDeleting}
              >
                {isDeleting ? "Deleting..." : "Confirm"}
              </Button>
            </div>
          </div>
        </div>
      )}
      {/* Custom action confirmation dialog */}
      {pendingCustomAction && (
        <div className="fixed inset-0 bg-neutral-12 bg-opacity-50 flex items-center justify-center z-modal">
          <div className="bg-neutral-1 rounded-lg p-6 max-w-sm mx-4 shadow-xl">
            <h3 className="text-lg font-semibold text-neutral-12 mb-2">
              Are you sure?
            </h3>
            <p className="text-sm text-neutral-11 mb-4">
              {pendingCustomAction.confirmMessage ||
                `This will affect ${selectedCount} items.`}
            </p>
            <div className="flex justify-end gap-2">
              <Button
                variant="secondary"
                className="px-3 py-1.5 text-sm rounded-md bg-neutral-2 hover:bg-neutral-3 text-neutral-11"
                type="button"
                onClick={handleCustomActionCancel}
                disabled={isCustomActionLoading}
              >
                Cancel
              </Button>
              <Button
                variant="danger"
                className="px-3 py-1.5 text-sm rounded-md bg-error-10 hover:bg-error-11 text-neutral-12"
                type="button"
                onClick={handleCustomActionConfirm}
                disabled={isCustomActionLoading}
              >
                {isCustomActionLoading ? "Processing..." : "Confirm"}
              </Button>
            </div>
          </div>
        </div>
      )}
    </div>
  );
}
