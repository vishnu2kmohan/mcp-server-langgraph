/**
 * ConnectionBulkActions Component
 *
 * Bulk action controls for connections.
 * Supports multi-select delete and test operations.
 */

import { useState } from "react";
import { Trash2, Zap, X, AlertCircle, Loader2 } from "lucide-react";
import { Dialog } from "../UI/Dialog";
import { authenticatedFetch } from "../../utils/authenticatedFetch";

interface Connection {
  id: string;
  name: string;
  status: string;
}

interface ConnectionBulkActionsProps {
  selectedIds: string[];
  connections: Connection[];
  onActionComplete: () => void;
  onClearSelection?: () => void;
}

interface DeleteResult {
  deleted_count: number;
  failed_ids: string[];
}

export function ConnectionBulkActions({
  selectedIds,
  connections: _connections,
  onActionComplete,
  onClearSelection,
}: ConnectionBulkActionsProps) {
  // _connections available for future use (e.g., showing names in confirmation dialog)
  const [showDeleteConfirm, setShowDeleteConfirm] = useState(false);
  const [isDeleting, setIsDeleting] = useState(false);
  const [isTesting, setIsTesting] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [deleteResult, setDeleteResult] = useState<DeleteResult | null>(null);

  // Don't render if no items selected
  if (selectedIds.length === 0) {
    return null;
  }

  const handleDeleteClick = () => {
    setShowDeleteConfirm(true);
    setError(null);
    setDeleteResult(null);
  };

  const handleCancelDelete = () => {
    setShowDeleteConfirm(false);
  };

  const handleConfirmDelete = async () => {
    setIsDeleting(true);
    setError(null);

    try {
      const response = await authenticatedFetch(
        "/api/v1/connections/bulk/delete",
        {
          method: "POST",
          headers: { "Content-Type": "application/json" },
          body: JSON.stringify({ connection_ids: selectedIds }),
        },
      );

      if (!response.ok) {
        throw new Error("Failed to delete connections");
      }

      const result: DeleteResult = await response.json();
      setDeleteResult(result);

      if (result.failed_ids.length === 0) {
        setShowDeleteConfirm(false);
        onActionComplete();
      }
    } catch (err) {
      setError(err instanceof Error ? err.message : "An error occurred");
    } finally {
      setIsDeleting(false);
    }
  };

  const handleTest = async () => {
    setIsTesting(true);
    setError(null);

    try {
      const response = await authenticatedFetch(
        "/api/v1/connections/bulk/test",
        {
          method: "POST",
          headers: { "Content-Type": "application/json" },
          body: JSON.stringify({ connection_ids: selectedIds }),
        },
      );

      if (!response.ok) {
        throw new Error("Failed to test connections");
      }

      // Result available for future display of test outcomes
      await response.json();
      onActionComplete();
    } catch (err) {
      setError(err instanceof Error ? err.message : "An error occurred");
    } finally {
      setIsTesting(false);
    }
  };

  const handleClearSelection = () => {
    onClearSelection?.();
  };

  return (
    <div
      data-testid="bulk-actions"
      className="mb-4 flex items-center gap-4 rounded-lg border border-primary-200 bg-primary-50 p-3 dark:border-primary-800 dark:bg-primary-900/30"
    >
      <span className="text-sm font-medium text-primary-700 dark:text-primary-300">
        {selectedIds.length} selected
      </span>

      <div className="flex items-center gap-2">
        <button
          onClick={handleDeleteClick}
          disabled={isDeleting || isTesting}
          className="flex items-center gap-1.5 rounded-md bg-error-600 px-3 py-1.5 text-sm font-medium text-white transition-colors hover:bg-error-700 disabled:cursor-not-allowed disabled:opacity-50"
        >
          <Trash2 className="h-4 w-4" />
          Delete
        </button>

        <button
          onClick={handleTest}
          disabled={isDeleting || isTesting}
          className="flex items-center gap-1.5 rounded-md bg-primary-600 px-3 py-1.5 text-sm font-medium text-white transition-colors hover:bg-primary-700 disabled:cursor-not-allowed disabled:opacity-50"
        >
          {isTesting ? (
            <Loader2 className="h-4 w-4 animate-spin" />
          ) : (
            <Zap className="h-4 w-4" />
          )}
          {isTesting ? "Testing..." : "Test"}
        </button>

        <button
          onClick={handleClearSelection}
          disabled={isDeleting || isTesting}
          className="flex items-center gap-1.5 rounded-md border border-gray-300 dark:border-gray-600 bg-white px-3 py-1.5 text-sm font-medium text-gray-700 dark:text-gray-200 transition-colors hover:bg-gray-50 disabled:cursor-not-allowed disabled:opacity-50 dark:border-gray-600 dark:bg-gray-800 dark:text-gray-300 dark:hover:bg-gray-700"
        >
          <X className="h-4 w-4" />
          Clear
        </button>
      </div>

      {error && (
        <div
          className="flex items-center gap-2 text-sm text-error-600 dark:text-error-400"
          role="alert"
        >
          <AlertCircle className="h-4 w-4" />
          Error: {error}
        </div>
      )}

      <Dialog
        open={showDeleteConfirm}
        onClose={handleCancelDelete}
        title="Confirm Delete"
        footer={
          <>
            <button
              onClick={handleCancelDelete}
              disabled={isDeleting}
              className="rounded-md px-4 py-2 text-gray-700 dark:text-gray-200 hover:bg-gray-100 dark:bg-gray-800 dark:text-gray-300 dark:hover:bg-gray-700"
            >
              Cancel
            </button>
            <button
              onClick={handleConfirmDelete}
              disabled={isDeleting}
              className="flex items-center gap-2 rounded-md bg-error-600 px-4 py-2 text-white hover:bg-error-700 disabled:cursor-not-allowed disabled:opacity-50"
            >
              {isDeleting && <Loader2 className="h-4 w-4 animate-spin" />}
              {isDeleting ? "Deleting..." : "Confirm Delete"}
            </button>
          </>
        }
      >
        <p className="mb-4 text-gray-600 dark:text-gray-400">
          Are you sure you want to delete {selectedIds.length} connections?
        </p>

        {deleteResult && deleteResult.failed_ids.length > 0 && (
          <div className="rounded-md bg-warning-50 p-3 dark:bg-warning-900/30">
            <p className="text-sm text-success-600 dark:text-success-400">
              {deleteResult.deleted_count} deleted successfully
            </p>
            <p className="text-sm text-error-600 dark:text-error-400">
              {deleteResult.failed_ids.length} failed to delete
            </p>
          </div>
        )}
      </Dialog>
    </div>
  );
}
