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

import { Button, Input, Select } from "@/components/UI";

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
  const isPublic = sharesData?.isPublic ?? false;
  const shareLink = sharesData?.shareLink ?? null;

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
    return undefined;
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
          <div className="animate-spin rounded-full h-8 w-8 border-b-2 border-primary-9"></div>
        </div>
      )}
      {/* Error State */}
      {sharesError && (
        <div className="flex items-center gap-2 p-4 bg-error-1 dark:bg-error-a3 border border-error-4 dark:border-error-11 rounded-lg">
          <AlertCircle size={20} className="text-error-9" />
          <p className="text-sm text-error-11 dark:text-error-9">
            Failed to load sharing settings. Please try again.
          </p>
        </div>
      )}
      {/* Operation Error Toast */}
      {operationError && (
        <div className="flex items-center gap-2 p-3 bg-error-1 dark:bg-error-a3 border border-error-4 dark:border-error-11 rounded-lg">
          <AlertCircle size={16} className="text-error-9 shrink-0" />
          <p className="text-sm text-error-11 dark:text-error-9">
            {operationError}
          </p>
        </div>
      )}
      {/* Main Content - only show when not loading and no fetch error */}
      {!isLoadingShares && !sharesError && (
        <>
          {/* Add User Section */}
          <div>
            <label className="block text-sm font-medium text-neutral-11 mb-2">
              Share with people
            </label>
            <div className="flex gap-2">
              <div className="flex-1">
                <Input
                  className="px-3 py-2 text-neutral-12 focus:ring-primary-7"
                  type="email"
                  placeholder="Email address"
                  value={email}
                  onChange={(e) => {
                    setEmail(e.target.value);
                    setEmailError(null);
                  }}
                />
                {emailError && (
                  <p className="mt-1 text-sm text-error-10 dark:text-error-7">
                    {emailError}
                  </p>
                )}
              </div>
              <Select
                className="px-3 py-2 text-neutral-12 focus:ring-primary-7"
                data-testid="permission-select"
                value={permission}
                onChange={(e) => setPermission(e.target.value as Permission)}
              >
                <option value="view">view</option>
                <option value="edit">edit</option>
                <option value="execute">execute</option>
              </Select>
              <Button
                variant="primary"
                className="flex px-4 py-2 bg-primary-10 text-neutral-12 rounded-lg hover:bg-primary-11"
                onClick={handleAddShare}
                disabled={isAddingShare || !email}
                aria-label="Share"
              >
                <UserPlus size={16} />
                Share
              </Button>
            </div>
          </div>

          {/* Current Shares */}
          {shares.length > 0 && (
            <div>
              <h3 className="text-sm font-medium text-neutral-11 mb-2">
                People with access
              </h3>
              <div className="space-y-2">
                {shares.map((share) => (
                  <div
                    key={share.userId}
                    className="flex items-center justify-between p-2 bg-neutral-1 rounded-lg"
                  >
                    <div className="flex items-center gap-3">
                      <div className="w-8 h-8 bg-primary-3 bg-primary-4 rounded-full flex items-center justify-center">
                        <span className="text-primary-10 dark:text-primary-7 text-sm font-medium">
                          {(share.email[0] ?? "?").toUpperCase()}
                        </span>
                      </div>
                      <div>
                        <p className="text-sm text-neutral-12">
                          {share.email}
                        </p>
                        <p className="text-xs text-neutral-10">
                          {share.permission}
                        </p>
                      </div>
                    </div>
                    <Button
                      variant="danger"
                      className="p-1 text-neutral-10 hover:text-error-10 dark:hover:text-error-7 rounded"
                      onClick={() => handleRemoveShare(share.userId)}
                      aria-label="Remove">
                      <Trash2 size={16} />
                    </Button>
                  </div>
                ))}
              </div>
            </div>
          )}

          {/* Public Link Section */}
          <div className="pt-4 border-t border-neutral-5">
            <div className="flex items-center justify-between mb-3">
              <div className="flex items-center gap-2">
                {isPublic ? (
                  <Globe size={18} className="text-success-9" />
                ) : (
                  <Lock
                    size={18}
                    className="text-neutral-10"
                  />
                )}
                <span className="text-sm font-medium text-neutral-11">
                  {isPublic ? "Public access enabled" : "Private"}
                </span>
              </div>
              <Button
                variant="primary"
                className="relative h-6 w-11 rounded-full"
                data-testid="public-toggle"
                onClick={handleTogglePublic}>
                <span
                  className={`inline-block h-4 w-4 transform rounded-full bg-neutral-1 transition-transform ${
                    isPublic ? "translate-x-6" : "translate-x-1"
                  }`}
                />
              </Button>
            </div>

            {isPublic && shareLink && (
              <div className="flex gap-2">
                <div className="flex-1 relative">
                  <Link2
                    size={16}
                    className="absolute left-3 top-1/2 -translate-y-1/2 text-neutral-9"
                  />
                  <Input
                    className="pl-9 pr-3 py-2 bg-neutral-1 text-neutral-12 text-sm"
                    readOnly
                    value={shareLink}
                  />
                </div>
                <Button
                  variant="secondary"
                  className="flex px-3 py-2 border border-neutral-5 rounded-lg hover:bg-neutral-1"
                  onClick={handleCopyLink}
                  aria-label="Copy link"
                >
                  {linkCopied ? (
                    <Check size={16} className="text-success-9" />
                  ) : (
                    <Copy
                      size={16}
                      className="text-neutral-10"
                    />
                  )}
                  Copy
                </Button>
              </div>
            )}

            <p className="mt-2 text-xs text-neutral-10">
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
