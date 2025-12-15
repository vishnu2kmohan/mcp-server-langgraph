/**
 * ShareWorkflowDialog Component
 *
 * Dialog for sharing workflows with other users.
 * Features:
 * - Add users by email with permission levels (view, edit, execute)
 * - View and manage existing shares
 * - Toggle public access with shareable link
 * - Copy share link to clipboard
 *
 * Uses RTK Query for API calls with automatic caching and refetching.
 */

import { useState, useEffect } from "react";
import {
  Link2,
  Copy,
  Check,
  UserPlus,
  Trash2,
  Globe,
  Lock,
  AlertCircle,
} from "lucide-react";
import { Dialog } from "../UI/Dialog";
import {
  useGetWorkflowSharesQuery,
  useAddWorkflowShareMutation,
  useRemoveWorkflowShareMutation,
  useUpdateWorkflowPublicMutation,
} from "../../api";

export interface ShareWorkflowDialogProps {
  open: boolean;
  onClose: () => void;
  workflow: {
    id: string;
    name: string;
  };
}

type Permission = "view" | "edit" | "execute";

export function ShareWorkflowDialog({
  open,
  onClose,
  workflow,
}: ShareWorkflowDialogProps) {
  const [email, setEmail] = useState("");
  const [permission, setPermission] = useState<Permission>("view");
  const [emailError, setEmailError] = useState<string | null>(null);
  const [linkCopied, setLinkCopied] = useState(false);
  const [operationError, setOperationError] = useState<string | null>(null);

  // RTK Query hooks
  const {
    data: sharesData,
    isLoading: isLoadingShares,
    error: sharesError,
  } = useGetWorkflowSharesQuery(workflow.id, {
    skip: !open, // Only fetch when dialog is open
  });

  const [addShare, { isLoading: isAddingShare }] =
    useAddWorkflowShareMutation();
  const [removeShare] = useRemoveWorkflowShareMutation();
  const [updatePublic] = useUpdateWorkflowPublicMutation();

  // Derived state from query data
  const shares = sharesData?.shares ?? [];
  const isPublic = sharesData?.is_public ?? false;
  const shareLink = sharesData?.share_link ?? null;

  // Clear error when dialog opens/closes
  useEffect(() => {
    if (open) {
      setOperationError(null);
      setEmailError(null);
    }
  }, [open]);

  // Clear operation error after 5 seconds
  useEffect(() => {
    if (operationError) {
      const timer = setTimeout(() => setOperationError(null), 5000);
      return () => clearTimeout(timer);
    }
  }, [operationError]);

  const validateEmail = (email: string): boolean => {
    const emailRegex = /^[^\s@]+@[^\s@]+\.[^\s@]+$/;
    return emailRegex.test(email);
  };

  const handleAddShare = async () => {
    setEmailError(null);
    setOperationError(null);

    if (!validateEmail(email)) {
      setEmailError("Please enter a valid email address");
      return;
    }

    try {
      await addShare({
        workflow_id: workflow.id,
        email,
        permission,
      }).unwrap();
      setEmail("");
    } catch (err) {
      const errorMessage =
        err && typeof err === "object" && "data" in err
          ? (err.data as { detail?: string })?.detail ||
            "Failed to share with this user"
          : "Failed to share with this user";
      setEmailError(errorMessage);
    }
  };

  const handleRemoveShare = async (userId: string) => {
    setOperationError(null);
    try {
      await removeShare({
        workflow_id: workflow.id,
        user_id: userId,
      }).unwrap();
    } catch (err) {
      const errorMessage =
        err && typeof err === "object" && "data" in err
          ? (err.data as { detail?: string })?.detail ||
            "Failed to remove user access"
          : "Failed to remove user access";
      setOperationError(errorMessage);
    }
  };

  const handleTogglePublic = async () => {
    setOperationError(null);
    try {
      await updatePublic({
        workflow_id: workflow.id,
        is_public: !isPublic,
      }).unwrap();
    } catch (err) {
      const errorMessage =
        err && typeof err === "object" && "data" in err
          ? (err.data as { detail?: string })?.detail ||
            "Failed to update public status"
          : "Failed to update public status";
      setOperationError(errorMessage);
    }
  };

  const handleCopyLink = async () => {
    if (shareLink) {
      await navigator.clipboard.writeText(shareLink);
      setLinkCopied(true);
      setTimeout(() => setLinkCopied(false), 2000);
    }
  };

  return (
    <Dialog
      open={open}
      onClose={onClose}
      title={`Share "${workflow.name}"`}
      contentClassName="space-y-6"
    >
      {/* Loading State */}
      {isLoadingShares && (
        <div className="flex justify-center py-8">
          <div className="animate-spin rounded-full h-8 w-8 border-b-2 border-blue-500"></div>
        </div>
      )}

      {/* Error State */}
      {sharesError && (
        <div className="flex items-center gap-2 p-4 bg-red-50 dark:bg-red-900/20 border border-red-200 dark:border-red-800 rounded-lg">
          <AlertCircle size={20} className="text-red-500" />
          <p className="text-sm text-red-700 dark:text-red-300">
            Failed to load sharing settings. Please try again.
          </p>
        </div>
      )}

      {/* Operation Error Toast */}
      {operationError && (
        <div className="flex items-center gap-2 p-3 bg-red-50 dark:bg-red-900/20 border border-red-200 dark:border-red-800 rounded-lg">
          <AlertCircle size={16} className="text-red-500 shrink-0" />
          <p className="text-sm text-red-700 dark:text-red-300">
            {operationError}
          </p>
        </div>
      )}

      {/* Main Content - only show when not loading and no fetch error */}
      {!isLoadingShares && !sharesError && (
        <>
          {/* Add User Section */}
          <div>
            <label className="block text-sm font-medium text-gray-700 dark:text-gray-300 mb-2">
              Share with people
            </label>
            <div className="flex gap-2">
              <div className="flex-1">
                <input
                  type="email"
                  placeholder="Email address"
                  value={email}
                  onChange={(e) => {
                    setEmail(e.target.value);
                    setEmailError(null);
                  }}
                  className="w-full px-3 py-2 border border-gray-300 dark:border-gray-600 rounded-lg bg-white dark:bg-gray-700 text-gray-900 dark:text-gray-100 focus:outline-none focus:ring-2 focus:ring-blue-500"
                />
                {emailError && (
                  <p className="mt-1 text-sm text-red-600 dark:text-red-400">
                    {emailError}
                  </p>
                )}
              </div>
              <select
                data-testid="permission-select"
                value={permission}
                onChange={(e) => setPermission(e.target.value as Permission)}
                className="px-3 py-2 border border-gray-300 dark:border-gray-600 rounded-lg bg-white dark:bg-gray-700 text-gray-900 dark:text-gray-100 focus:outline-none focus:ring-2 focus:ring-blue-500"
              >
                <option value="view">view</option>
                <option value="edit">edit</option>
                <option value="execute">execute</option>
              </select>
              <button
                onClick={handleAddShare}
                disabled={isAddingShare || !email}
                aria-label="Share"
                className="flex items-center gap-2 px-4 py-2 bg-blue-600 text-white rounded-lg hover:bg-blue-700 disabled:opacity-50 disabled:cursor-not-allowed transition-colors"
              >
                <UserPlus size={16} />
                Share
              </button>
            </div>
          </div>

          {/* Current Shares */}
          {shares.length > 0 && (
            <div>
              <h3 className="text-sm font-medium text-gray-700 dark:text-gray-300 mb-2">
                People with access
              </h3>
              <div className="space-y-2">
                {shares.map((share) => (
                  <div
                    key={share.user_id}
                    className="flex items-center justify-between p-2 bg-gray-50 dark:bg-gray-700/50 rounded-lg"
                  >
                    <div className="flex items-center gap-3">
                      <div className="w-8 h-8 bg-blue-100 dark:bg-blue-900/30 rounded-full flex items-center justify-center">
                        <span className="text-blue-600 dark:text-blue-400 text-sm font-medium">
                          {share.email[0].toUpperCase()}
                        </span>
                      </div>
                      <div>
                        <p className="text-sm text-gray-900 dark:text-gray-100">
                          {share.email}
                        </p>
                        <p className="text-xs text-gray-500 dark:text-gray-400">
                          {share.permission}
                        </p>
                      </div>
                    </div>
                    <button
                      onClick={() => handleRemoveShare(share.user_id)}
                      aria-label="Remove"
                      className="p-1 text-gray-500 hover:text-red-600 dark:text-gray-400 dark:hover:text-red-400 rounded"
                    >
                      <Trash2 size={16} />
                    </button>
                  </div>
                ))}
              </div>
            </div>
          )}

          {/* Public Link Section */}
          <div className="pt-4 border-t border-gray-200 dark:border-gray-700">
            <div className="flex items-center justify-between mb-3">
              <div className="flex items-center gap-2">
                {isPublic ? (
                  <Globe size={18} className="text-green-500" />
                ) : (
                  <Lock size={18} className="text-gray-500" />
                )}
                <span className="text-sm font-medium text-gray-700 dark:text-gray-300">
                  {isPublic ? "Public access enabled" : "Private"}
                </span>
              </div>
              <button
                data-testid="public-toggle"
                onClick={handleTogglePublic}
                className={`relative inline-flex h-6 w-11 items-center rounded-full transition-colors ${
                  isPublic ? "bg-green-500" : "bg-gray-300 dark:bg-gray-600"
                }`}
              >
                <span
                  className={`inline-block h-4 w-4 transform rounded-full bg-white transition-transform ${
                    isPublic ? "translate-x-6" : "translate-x-1"
                  }`}
                />
              </button>
            </div>

            {isPublic && shareLink && (
              <div className="flex gap-2">
                <div className="flex-1 relative">
                  <Link2
                    size={16}
                    className="absolute left-3 top-1/2 -translate-y-1/2 text-gray-400"
                  />
                  <input
                    type="text"
                    readOnly
                    value={shareLink}
                    className="w-full pl-9 pr-3 py-2 border border-gray-300 dark:border-gray-600 rounded-lg bg-gray-50 dark:bg-gray-700 text-gray-900 dark:text-gray-100 text-sm"
                  />
                </div>
                <button
                  onClick={handleCopyLink}
                  aria-label="Copy link"
                  className="flex items-center gap-2 px-3 py-2 border border-gray-300 dark:border-gray-600 rounded-lg hover:bg-gray-50 dark:hover:bg-gray-700 transition-colors"
                >
                  {linkCopied ? (
                    <Check size={16} className="text-green-500" />
                  ) : (
                    <Copy size={16} className="text-gray-500" />
                  )}
                  Copy
                </button>
              </div>
            )}

            <p className="mt-2 text-xs text-gray-500 dark:text-gray-400">
              {isPublic
                ? "Anyone with the link can view this workflow"
                : "Only people you share with can access this workflow"}
            </p>
          </div>
        </>
      )}
    </Dialog>
  );
}

export default ShareWorkflowDialog;
