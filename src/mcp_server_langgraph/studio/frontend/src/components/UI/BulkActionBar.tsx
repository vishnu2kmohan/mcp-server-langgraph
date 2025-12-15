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
      className={`fixed bottom-0 left-0 right-0 bg-white dark:bg-gray-800 border-t border-gray-200 dark:border-gray-700 px-4 py-3 flex items-center justify-between shadow-lg ${className}`}
    >
      {/* Selection count */}
      <div className="flex items-center gap-4">
        <span
          role="status"
          className="text-sm font-medium text-gray-700 dark:text-gray-300"
        >
          {selectedCount} selected
        </span>
        <button
          type="button"
          aria-label="Clear selection"
          onClick={onClearSelection}
          className="text-sm text-gray-500 hover:text-gray-700 dark:text-gray-400 dark:hover:text-gray-200"
        >
          Clear
        </button>
      </div>

      {/* Actions */}
      <div className="flex items-center gap-2">
        {/* Custom actions */}
        {customActions.map((action) => (
          <button
            key={action.label}
            type="button"
            onClick={() => handleCustomActionClick(action)}
            className="inline-flex items-center gap-1 px-3 py-1.5 text-sm font-medium rounded-md bg-gray-100 hover:bg-gray-200 dark:bg-gray-700 dark:hover:bg-gray-600 text-gray-700 dark:text-gray-300"
          >
            {action.icon}
            {action.label}
          </button>
        ))}

        {/* Delete button */}
        <button
          type="button"
          onClick={handleDeleteClick}
          className="inline-flex items-center gap-1 px-3 py-1.5 text-sm font-medium rounded-md bg-red-100 hover:bg-red-200 dark:bg-red-900 dark:hover:bg-red-800 text-red-700 dark:text-red-300"
        >
          Delete
        </button>
      </div>

      {/* Delete confirmation dialog */}
      {showDeleteConfirm && (
        <div className="fixed inset-0 bg-black bg-opacity-50 flex items-center justify-center z-50">
          <div className="bg-white dark:bg-gray-800 rounded-lg p-6 max-w-sm mx-4 shadow-xl">
            <h3 className="text-lg font-semibold text-gray-900 dark:text-gray-100 mb-2">
              Are you sure?
            </h3>
            <p className="text-sm text-gray-600 dark:text-gray-400 mb-4">
              This will delete {selectedCount} items. This action cannot be
              undone.
            </p>
            <div className="flex justify-end gap-2">
              <button
                type="button"
                onClick={handleDeleteCancel}
                disabled={isDeleting}
                className="px-3 py-1.5 text-sm font-medium rounded-md bg-gray-100 hover:bg-gray-200 dark:bg-gray-700 dark:hover:bg-gray-600 text-gray-700 dark:text-gray-300 disabled:opacity-50"
              >
                Cancel
              </button>
              <button
                type="button"
                onClick={handleDeleteConfirm}
                disabled={isDeleting}
                className="px-3 py-1.5 text-sm font-medium rounded-md bg-red-600 hover:bg-red-700 text-white disabled:opacity-50"
              >
                {isDeleting ? "Deleting..." : "Confirm"}
              </button>
            </div>
          </div>
        </div>
      )}

      {/* Custom action confirmation dialog */}
      {pendingCustomAction && (
        <div className="fixed inset-0 bg-black bg-opacity-50 flex items-center justify-center z-50">
          <div className="bg-white dark:bg-gray-800 rounded-lg p-6 max-w-sm mx-4 shadow-xl">
            <h3 className="text-lg font-semibold text-gray-900 dark:text-gray-100 mb-2">
              Are you sure?
            </h3>
            <p className="text-sm text-gray-600 dark:text-gray-400 mb-4">
              {pendingCustomAction.confirmMessage ||
                `This will affect ${selectedCount} items.`}
            </p>
            <div className="flex justify-end gap-2">
              <button
                type="button"
                onClick={handleCustomActionCancel}
                disabled={isCustomActionLoading}
                className="px-3 py-1.5 text-sm font-medium rounded-md bg-gray-100 hover:bg-gray-200 dark:bg-gray-700 dark:hover:bg-gray-600 text-gray-700 dark:text-gray-300 disabled:opacity-50"
              >
                Cancel
              </button>
              <button
                type="button"
                onClick={handleCustomActionConfirm}
                disabled={isCustomActionLoading}
                className="px-3 py-1.5 text-sm font-medium rounded-md bg-red-600 hover:bg-red-700 text-white disabled:opacity-50"
              >
                {isCustomActionLoading ? "Processing..." : "Confirm"}
              </button>
            </div>
          </div>
        </div>
      )}
    </div>
  );
}
