/**
 * MessageActions Component
 *
 * Dropdown menu for message actions including:
 * - Copy: Copy message content to clipboard
 * - Edit: Edit user messages (triggers re-send)
 * - Regenerate: Regenerate assistant responses
 * - Delete: Delete a message from the conversation
 *
 * Features:
 * - Role-based action visibility
 * - Accessible keyboard navigation
 * - Click-outside to close
 * - Delete confirmation dialog
 */

import { useState, useCallback, useRef, useEffect } from "react";
import {
  MoreHorizontal,
  Copy,
  Check,
  Pencil,
  RefreshCw,
  Trash2,
  Loader2,
} from "lucide-react";

// =============================================================================
// Types
// =============================================================================

export interface MessageActionsProps {
  /** The message ID */
  messageId: string;
  /** The message content for copying */
  content: string;
  /** The message role - determines which actions are available */
  role: "user" | "assistant" | "system";
  /** Callback when edit is triggered (user messages only) */
  onEdit?: (messageId: string) => void;
  /** Callback when regenerate is triggered (assistant messages only) */
  onRegenerate?: (messageId: string) => void;
  /** Callback when delete is triggered */
  onDelete?: (messageId: string) => void;
  /** Whether regeneration is in progress */
  isRegenerating?: boolean;
  /** Additional CSS classes */
  className?: string;
}

// =============================================================================
// Component
// =============================================================================

export function MessageActions({
  messageId,
  content,
  role,
  onEdit,
  onRegenerate,
  onDelete,
  isRegenerating = false,
  className = "",
}: MessageActionsProps) {
  const [isOpen, setIsOpen] = useState(false);
  const [copied, setCopied] = useState(false);
  const [showDeleteConfirm, setShowDeleteConfirm] = useState(false);
  const containerRef = useRef<HTMLDivElement>(null);

  const isUser = role === "user";
  const isAssistant = role === "assistant";

  // Handle click outside to close menu
  useEffect(() => {
    function handleClickOutside(event: MouseEvent) {
      if (
        containerRef.current &&
        !containerRef.current.contains(event.target as Node)
      ) {
        setIsOpen(false);
        setShowDeleteConfirm(false);
      }
    }

    if (isOpen) {
      document.addEventListener("mousedown", handleClickOutside);
      return () =>
        document.removeEventListener("mousedown", handleClickOutside);
    }
  }, [isOpen]);

  // Handle Escape key to close menu
  useEffect(() => {
    function handleEscape(event: KeyboardEvent) {
      if (event.key === "Escape") {
        setIsOpen(false);
        setShowDeleteConfirm(false);
      }
    }

    if (isOpen) {
      document.addEventListener("keydown", handleEscape);
      return () => document.removeEventListener("keydown", handleEscape);
    }
  }, [isOpen]);

  // Copy to clipboard
  const handleCopy = useCallback(async () => {
    try {
      await navigator.clipboard.writeText(content);
      setCopied(true);
      setTimeout(() => setCopied(false), 2000);
    } catch (err) {
      console.error("Failed to copy:", err);
    }
  }, [content]);

  // Edit action (user messages only)
  const handleEdit = useCallback(() => {
    onEdit?.(messageId);
    setIsOpen(false);
  }, [messageId, onEdit]);

  // Regenerate action (assistant messages only)
  const handleRegenerate = useCallback(() => {
    onRegenerate?.(messageId);
    setIsOpen(false);
  }, [messageId, onRegenerate]);

  // Delete action - show confirmation first
  const handleDeleteClick = useCallback(() => {
    setShowDeleteConfirm(true);
  }, []);

  // Confirm delete
  const handleConfirmDelete = useCallback(() => {
    onDelete?.(messageId);
    setIsOpen(false);
    setShowDeleteConfirm(false);
  }, [messageId, onDelete]);

  // Cancel delete
  const handleCancelDelete = useCallback(() => {
    setShowDeleteConfirm(false);
  }, []);

  // Toggle menu
  const toggleMenu = useCallback(() => {
    setIsOpen((prev) => !prev);
    setShowDeleteConfirm(false);
  }, []);

  return (
    <div
      ref={containerRef}
      data-testid="message-actions-container"
      className={`relative inline-flex ${className}`}
    >
      {/* Trigger Button */}
      <button
        data-testid="message-actions-trigger"
        onClick={toggleMenu}
        aria-label="Message actions"
        aria-expanded={isOpen}
        aria-haspopup="menu"
        className="p-1 rounded hover:bg-gray-200 dark:hover:bg-gray-700 text-gray-500 dark:text-gray-400 transition-colors"
      >
        <MoreHorizontal size={16} />
      </button>

      {/* Dropdown Menu */}
      {isOpen && (
        <div
          data-testid="message-actions-menu"
          role="menu"
          className="absolute right-0 top-full mt-1 z-50 min-w-[160px] bg-white dark:bg-gray-800 rounded-lg shadow-lg border border-gray-200 dark:border-gray-700 py-1"
        >
          {/* Delete Confirmation Dialog */}
          {showDeleteConfirm ? (
            <div data-testid="delete-confirmation" className="p-3 space-y-3">
              <p className="text-sm text-gray-700 dark:text-gray-300">
                Delete this message?
              </p>
              <div className="flex gap-2">
                <button
                  data-testid="confirm-delete"
                  onClick={handleConfirmDelete}
                  className="flex-1 px-3 py-1.5 text-sm bg-red-600 hover:bg-red-700 text-white rounded transition-colors"
                >
                  Delete
                </button>
                <button
                  data-testid="cancel-delete"
                  onClick={handleCancelDelete}
                  className="flex-1 px-3 py-1.5 text-sm bg-gray-200 dark:bg-gray-700 hover:bg-gray-300 dark:hover:bg-gray-600 text-gray-700 dark:text-gray-300 rounded transition-colors"
                >
                  Cancel
                </button>
              </div>
            </div>
          ) : (
            <>
              {/* Copy Action - always available */}
              <button
                data-testid="action-copy"
                onClick={handleCopy}
                role="menuitem"
                className="w-full flex items-center gap-2 px-3 py-2 text-sm text-gray-700 dark:text-gray-300 hover:bg-gray-100 dark:hover:bg-gray-700 transition-colors"
              >
                {copied ? (
                  <>
                    <Check size={16} className="text-green-500" />
                    <span data-testid="copy-success">Copied!</span>
                  </>
                ) : (
                  <>
                    <Copy size={16} />
                    <span>Copy</span>
                  </>
                )}
              </button>

              {/* Edit Action - user messages only */}
              {isUser && onEdit && (
                <button
                  data-testid="action-edit"
                  onClick={handleEdit}
                  role="menuitem"
                  className="w-full flex items-center gap-2 px-3 py-2 text-sm text-gray-700 dark:text-gray-300 hover:bg-gray-100 dark:hover:bg-gray-700 transition-colors"
                >
                  <Pencil size={16} />
                  <span>Edit</span>
                </button>
              )}

              {/* Regenerate Action - assistant messages only */}
              {isAssistant && onRegenerate && (
                <button
                  data-testid="action-regenerate"
                  onClick={handleRegenerate}
                  disabled={isRegenerating}
                  role="menuitem"
                  className="w-full flex items-center gap-2 px-3 py-2 text-sm text-gray-700 dark:text-gray-300 hover:bg-gray-100 dark:hover:bg-gray-700 transition-colors disabled:opacity-50 disabled:cursor-not-allowed"
                >
                  {isRegenerating ? (
                    <Loader2 size={16} className="animate-spin" />
                  ) : (
                    <RefreshCw size={16} />
                  )}
                  <span>Regenerate</span>
                </button>
              )}

              {/* Delete Action - always available */}
              {onDelete && (
                <button
                  data-testid="action-delete"
                  onClick={handleDeleteClick}
                  role="menuitem"
                  className="w-full flex items-center gap-2 px-3 py-2 text-sm text-red-600 dark:text-red-400 hover:bg-gray-100 dark:hover:bg-gray-700 transition-colors"
                >
                  <Trash2 size={16} />
                  <span>Delete</span>
                </button>
              )}
            </>
          )}
        </div>
      )}
    </div>
  );
}

export default MessageActions;
