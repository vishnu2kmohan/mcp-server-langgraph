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

import { useState, useCallback, useRef, useEffect, useMemo } from "react";
import {
  MoreHorizontal,
  Copy,
  Check,
  Pencil,
  RefreshCw,
  Trash2,
  Loader2,
  Code2,
  ThumbsUp,
  ThumbsDown,
  Bookmark,
  Share2,
  GitBranch,
} from "lucide-react";

// =============================================================================
// Types
// =============================================================================

export type FeedbackType = "positive" | "negative";

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
  /** Callback when feedback is given */
  onFeedback?: (messageId: string, type: FeedbackType) => void;
  /** Current feedback state */
  feedbackState?: FeedbackType;
  /** Callback when bookmark is clicked */
  onBookmark?: (messageId: string) => void;
  /** Whether message is bookmarked */
  isBookmarked?: boolean;
  /** Callback when share is clicked */
  onShare?: (messageId: string) => void;
  /** Callback when branch is clicked */
  onBranch?: (messageId: string) => void;
  /** Whether regeneration is in progress */
  isRegenerating?: boolean;
  /** Additional CSS classes */
  className?: string;
}

// =============================================================================
// Component
// =============================================================================

// Helper to extract code blocks from content
function extractCodeBlocks(content: string): string[] {
  const codeBlockRegex = /```[\w]*\n([\s\S]*?)```/g;
  const blocks: string[] = [];
  let match;
  while ((match = codeBlockRegex.exec(content)) !== null) {
    const code = match[1];
    if (code) blocks.push(code.trim());
  }
  return blocks;
}

export function MessageActions({
  messageId,
  content,
  role,
  onEdit,
  onRegenerate,
  onDelete,
  onFeedback,
  feedbackState,
  onBookmark,
  isBookmarked = false,
  onShare,
  onBranch,
  isRegenerating = false,
  className = "",
}: MessageActionsProps) {
  const [isOpen, setIsOpen] = useState(false);
  const [copied, setCopied] = useState(false);
  const [showDeleteConfirm, setShowDeleteConfirm] = useState(false);
  const containerRef = useRef<HTMLDivElement>(null);

  const isUser = role === "user";
  const isAssistant = role === "assistant";

  // Check if content has code blocks
  const codeBlocks = useMemo(() => extractCodeBlocks(content), [content]);
  const hasCodeBlocks = codeBlocks.length > 0;

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
    return undefined;
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
    return undefined;
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

  // Copy code blocks only
  const handleCopyCode = useCallback(async () => {
    try {
      const codeText = codeBlocks.join("\n\n");
      await navigator.clipboard.writeText(codeText);
      setCopied(true);
      setTimeout(() => setCopied(false), 2000);
    } catch (err) {
      console.error("Failed to copy code:", err);
    }
  }, [codeBlocks]);

  // Feedback actions
  const handleThumbsUp = useCallback(() => {
    onFeedback?.(messageId, "positive");
  }, [messageId, onFeedback]);

  const handleThumbsDown = useCallback(() => {
    onFeedback?.(messageId, "negative");
  }, [messageId, onFeedback]);

  // Bookmark action
  const handleBookmark = useCallback(() => {
    onBookmark?.(messageId);
    setIsOpen(false);
  }, [messageId, onBookmark]);

  // Share action
  const handleShare = useCallback(() => {
    onShare?.(messageId);
    setIsOpen(false);
  }, [messageId, onShare]);

  // Branch action
  const handleBranch = useCallback(() => {
    onBranch?.(messageId);
    setIsOpen(false);
  }, [messageId, onBranch]);

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
        className="p-1 rounded hover:bg-gray-200 dark:bg-gray-700 dark:hover:bg-gray-700 text-gray-500 dark:text-gray-400 transition-colors"
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
                  className="flex-1 px-3 py-1.5 text-sm bg-error-600 hover:bg-error-700 text-white rounded transition-colors"
                >
                  Delete
                </button>
                <button
                  data-testid="cancel-delete"
                  onClick={handleCancelDelete}
                  className="flex-1 px-3 py-1.5 text-sm bg-gray-200 dark:bg-gray-700 hover:bg-gray-300 dark:bg-gray-600 dark:hover:bg-gray-600 text-gray-700 dark:text-gray-300 rounded transition-colors"
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
                className="w-full flex items-center gap-2 px-3 py-2 text-sm text-gray-700 dark:text-gray-300 hover:bg-gray-100 dark:bg-gray-800 dark:hover:bg-gray-700 transition-colors"
              >
                {copied ? (
                  <>
                    <Check size={16} className="text-success-500" />
                    <span data-testid="copy-success">Copied!</span>
                  </>
                ) : (
                  <>
                    <Copy size={16} />
                    <span>Copy</span>
                  </>
                )}
              </button>

              {/* Copy Code Action - only when message has code blocks */}
              {hasCodeBlocks && (
                <button
                  data-testid="action-copy-code"
                  onClick={handleCopyCode}
                  role="menuitem"
                  className="w-full flex items-center gap-2 px-3 py-2 text-sm text-gray-700 dark:text-gray-300 hover:bg-gray-100 dark:bg-gray-800 dark:hover:bg-gray-700 transition-colors"
                >
                  <Code2 size={16} />
                  <span>Copy Code</span>
                </button>
              )}

              {/* Feedback Actions */}
              {onFeedback && (
                <div className="flex items-center px-3 py-2 gap-2 border-t border-gray-100 dark:border-gray-700">
                  <button
                    data-testid="action-thumbs-up"
                    onClick={handleThumbsUp}
                    data-active={feedbackState === "positive"}
                    role="menuitem"
                    className={`p-1.5 rounded transition-colors ${
                      feedbackState === "positive"
                        ? "text-success-600 bg-success-100 dark:bg-success-900/30"
                        : "text-gray-500 dark:text-gray-400 hover:text-gray-700 dark:text-gray-200 dark:text-gray-400 dark:hover:text-gray-200 hover:bg-gray-100 dark:bg-gray-800 dark:hover:bg-gray-700"
                    }`}
                    aria-label="Thumbs up"
                  >
                    <ThumbsUp size={16} />
                  </button>
                  <button
                    data-testid="action-thumbs-down"
                    onClick={handleThumbsDown}
                    data-active={feedbackState === "negative"}
                    role="menuitem"
                    className={`p-1.5 rounded transition-colors ${
                      feedbackState === "negative"
                        ? "text-error-600 bg-error-100 dark:bg-error-900/30"
                        : "text-gray-500 dark:text-gray-400 hover:text-gray-700 dark:text-gray-200 dark:text-gray-400 dark:hover:text-gray-200 hover:bg-gray-100 dark:bg-gray-800 dark:hover:bg-gray-700"
                    }`}
                    aria-label="Thumbs down"
                  >
                    <ThumbsDown size={16} />
                  </button>
                </div>
              )}

              {/* Bookmark Action */}
              {onBookmark && (
                <button
                  data-testid="action-bookmark"
                  onClick={handleBookmark}
                  data-bookmarked={isBookmarked}
                  role="menuitem"
                  className={`w-full flex items-center gap-2 px-3 py-2 text-sm transition-colors ${
                    isBookmarked
                      ? "text-warning-600 dark:text-warning-400"
                      : "text-gray-700 dark:text-gray-300 hover:bg-gray-100 dark:bg-gray-800 dark:hover:bg-gray-700"
                  }`}
                >
                  <Bookmark
                    size={16}
                    fill={isBookmarked ? "currentColor" : "none"}
                  />
                  <span>{isBookmarked ? "Bookmarked" : "Bookmark"}</span>
                </button>
              )}

              {/* Share Action */}
              {onShare && (
                <button
                  data-testid="action-share"
                  onClick={handleShare}
                  role="menuitem"
                  className="w-full flex items-center gap-2 px-3 py-2 text-sm text-gray-700 dark:text-gray-300 hover:bg-gray-100 dark:bg-gray-800 dark:hover:bg-gray-700 transition-colors"
                >
                  <Share2 size={16} />
                  <span>Share</span>
                </button>
              )}

              {/* Branch Action */}
              {onBranch && (
                <button
                  data-testid="action-branch"
                  onClick={handleBranch}
                  role="menuitem"
                  className="w-full flex items-center gap-2 px-3 py-2 text-sm text-gray-700 dark:text-gray-300 hover:bg-gray-100 dark:bg-gray-800 dark:hover:bg-gray-700 transition-colors"
                >
                  <GitBranch size={16} />
                  <span>Branch</span>
                </button>
              )}

              {/* Edit Action - user messages only */}
              {isUser && onEdit && (
                <button
                  data-testid="action-edit"
                  onClick={handleEdit}
                  role="menuitem"
                  className="w-full flex items-center gap-2 px-3 py-2 text-sm text-gray-700 dark:text-gray-300 hover:bg-gray-100 dark:bg-gray-800 dark:hover:bg-gray-700 transition-colors"
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
                  className="w-full flex items-center gap-2 px-3 py-2 text-sm text-gray-700 dark:text-gray-300 hover:bg-gray-100 dark:bg-gray-800 dark:hover:bg-gray-700 transition-colors disabled:opacity-50 disabled:cursor-not-allowed"
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
                  className="w-full flex items-center gap-2 px-3 py-2 text-sm text-error-600 dark:text-error-400 hover:bg-gray-100 dark:bg-gray-800 dark:hover:bg-gray-700 transition-colors"
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
