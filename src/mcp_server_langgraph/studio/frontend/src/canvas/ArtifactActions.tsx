/**
 * ArtifactActions - Phase 1
 *
 * Artifact action buttons component for Copy, Fork, Export,
 * Share, and Delete operations.
 */
import { useState, useCallback } from "react";
import {
  Copy,
  GitFork,
  Download,
  Share2,
  Trash2,
  Check,
  ChevronDown,
} from "lucide-react";
import type { CanvasArtifact } from "../types/artifacts";
import { cn } from "../utils/cn";

import { Button } from "@/components/UI";

// =============================================================================
// Types
// =============================================================================

export type ExportFormat = "json" | "markdown" | "text";

export interface ArtifactActionsProps {
  /** The artifact to act upon */
  artifact: CanvasArtifact;
  /** Whether all actions are disabled */
  disabled?: boolean;
  /** Compact mode (icon-only buttons) */
  compact?: boolean;
  /** Whether sharing is enabled */
  shareable?: boolean;
  /** Whether deletion is enabled */
  deletable?: boolean;
  /** Whether forking is disabled */
  disableFork?: boolean;
  /** Callback after copying */
  onCopy?: () => void;
  /** Callback when fork is clicked */
  onFork?: (artifact: CanvasArtifact) => void;
  /** Callback when export is clicked */
  onExport?: (artifact: CanvasArtifact, format: ExportFormat) => void;
  /** Callback when share is clicked */
  onShare?: (artifact: CanvasArtifact) => void;
  /** Callback when delete is confirmed */
  onDelete?: (artifact: CanvasArtifact) => void;
  /** Additional class name */
  className?: string;
}

// =============================================================================
// Delete Confirmation Dialog
// =============================================================================

interface DeleteDialogProps {
  onConfirm: () => void;
  onCancel: () => void;
}

function DeleteConfirmDialog({ onConfirm, onCancel }: DeleteDialogProps) {
  return (
    <div
      data-testid="delete-confirm-dialog"
      className={cn(
        "fixed inset-0 z-50 flex items-center justify-center",
        "bg-black/50",
      )}
      onClick={onCancel}
    >
      <div
        className={cn(
          "bg-white dark:bg-neutral-800 rounded-lg shadow-xl p-6 max-w-sm mx-4",
        )}
        onClick={(e) => e.stopPropagation()}
      >
        <h3 className="text-lg font-medium text-neutral-900 dark:text-neutral-100 mb-2">
          Delete Artifact?
        </h3>
        <p className="text-sm text-neutral-600 dark:text-neutral-400 mb-4">
          This action cannot be undone. The artifact and all its versions will
          be permanently deleted.
        </p>
        <div className="flex justify-end gap-2">
          <Button
            data-testid="cancel-delete-button"
            type="button"
            onClick={onCancel}
            className={cn(
              "px-4 py-2 rounded-lg text-sm font-medium",
              "text-neutral-700 dark:text-neutral-300",
              "bg-neutral-100 dark:bg-neutral-700",
              "hover:bg-neutral-200 dark:bg-neutral-700 dark:hover:bg-neutral-600",
              "transition-colors",
            )}
          >
            Cancel
          </Button>
          <Button
            data-testid="confirm-delete-button"
            type="button"
            onClick={onConfirm}
            className={cn(
              "px-4 py-2 rounded-lg text-sm font-medium",
              "text-white bg-error-600 hover:bg-error-700",
              "transition-colors",
            )}
          >
            Delete
          </Button>
        </div>
      </div>
    </div>
  );
}

// =============================================================================
// Export Menu
// =============================================================================

interface ExportMenuProps {
  onExport: (format: ExportFormat) => void;
  onClose: () => void;
}

function ExportMenu({ onExport, onClose }: ExportMenuProps) {
  const formats: { format: ExportFormat; label: string }[] = [
    { format: "json", label: "JSON" },
    { format: "markdown", label: "Markdown" },
    { format: "text", label: "Plain Text" },
  ];

  return (
    <div
      data-testid="export-menu"
      className={cn(
        "absolute top-full right-0 mt-1 z-10",
        "bg-white dark:bg-neutral-800 rounded-lg shadow-lg",
        "border border-neutral-200 dark:border-neutral-700",
        "py-1 min-w-32",
      )}
    >
      {formats.map(({ format, label }) => (
        <Button
          key={format}
          type="button"
          onClick={() => {
            onExport(format);
            onClose();
          }}
          className={cn(
            "w-full px-4 py-2 text-left text-sm",
            "text-neutral-700 dark:text-neutral-300",
            "hover:bg-neutral-100 dark:bg-neutral-800 dark:hover:bg-neutral-700",
            "transition-colors",
          )}
        >
          {label}
        </Button>
      ))}
    </div>
  );
}

// =============================================================================
// Action Button Component
// =============================================================================

interface ActionButtonProps {
  icon: typeof Copy;
  label: string;
  compact?: boolean;
  disabled?: boolean;
  onClick: () => void;
  variant?: "default" | "danger";
  testId?: string;
}

function ActionButton({
  icon: Icon,
  label,
  compact,
  disabled,
  onClick,
  variant = "default",
  testId,
}: ActionButtonProps) {
  return (
    <Button
      data-testid={testId}
      type="button"
      disabled={disabled}
      onClick={onClick}
      title={compact ? label : undefined}
      aria-label={label}
      className={cn(
        "flex items-center gap-1.5 px-2 py-1.5 rounded-lg text-sm font-medium",
        "transition-colors focus:outline-none focus:ring-2 focus:ring-primary-500",
        variant === "default" &&
          "text-neutral-600 dark:text-neutral-400 hover:bg-neutral-100 dark:bg-neutral-800 dark:hover:bg-neutral-700",
        variant === "danger" &&
          "text-error-600 dark:text-error-400 hover:bg-error-100 dark:hover:bg-error-900/30",
        disabled && "opacity-50 cursor-not-allowed",
      )}
    >
      <Icon size={14} data-testid={`${testId?.replace("-button", "")}-icon`} />
      {!compact && <span>{label}</span>}
    </Button>
  );
}

// =============================================================================
// Component
// =============================================================================

export function ArtifactActions({
  artifact,
  disabled = false,
  compact = false,
  shareable = false,
  deletable = false,
  disableFork = false,
  onCopy,
  onFork,
  onExport,
  onShare,
  onDelete,
  className,
}: ArtifactActionsProps) {
  const [showCopySuccess, setShowCopySuccess] = useState(false);
  const [showExportMenu, setShowExportMenu] = useState(false);
  const [showDeleteDialog, setShowDeleteDialog] = useState(false);

  const handleCopy = useCallback(async () => {
    try {
      await navigator.clipboard.writeText(artifact.content);
      setShowCopySuccess(true);
      onCopy?.();
      setTimeout(() => setShowCopySuccess(false), 2000);
    } catch (error) {
      console.error("Failed to copy:", error);
    }
  }, [artifact.content, onCopy]);

  const handleFork = useCallback(() => {
    onFork?.(artifact);
  }, [artifact, onFork]);

  const handleExport = useCallback(
    (format: ExportFormat) => {
      onExport?.(artifact, format);
    },
    [artifact, onExport],
  );

  const handleShare = useCallback(() => {
    onShare?.(artifact);
  }, [artifact, onShare]);

  const handleDelete = useCallback(() => {
    onDelete?.(artifact);
    setShowDeleteDialog(false);
  }, [artifact, onDelete]);

  return (
    <div
      data-testid="artifact-actions"
      className={cn("flex items-center gap-1", className)}
    >
      {/* Copy button */}
      {showCopySuccess ? (
        <div
          data-testid="copy-success"
          className="flex items-center gap-1.5 px-2 py-1.5 text-sm text-success-600 dark:text-success-400"
        >
          <Check size={14} />
          {!compact && <span>Copied!</span>}
        </div>
      ) : (
        <ActionButton
          icon={Copy}
          label="Copy"
          compact={compact}
          disabled={disabled}
          onClick={handleCopy}
          testId="copy-button"
        />
      )}
      {/* Fork button */}
      <ActionButton
        icon={GitFork}
        label="Fork"
        compact={compact}
        disabled={disabled || disableFork}
        onClick={handleFork}
        testId="fork-button"
      />
      {/* Export button with dropdown */}
      <div className="relative">
        <Button
          type="button"
          disabled={disabled}
          onClick={() => setShowExportMenu(!showExportMenu)}
          title={compact ? "Export" : undefined}
          aria-label="Export"
          className={cn(
            "flex items-center gap-1.5 px-2 py-1.5 rounded-lg text-sm font-medium",
            "transition-colors focus:outline-none focus:ring-2 focus:ring-primary-500",
            "text-neutral-600 dark:text-neutral-400 hover:bg-neutral-100 dark:bg-neutral-800 dark:hover:bg-neutral-700",
            disabled && "opacity-50 cursor-not-allowed",
          )}
        >
          <Download size={14} data-testid="export-icon" />
          {!compact && <span>Export</span>}
          <ChevronDown size={12} />
        </Button>
        {showExportMenu && (
          <ExportMenu
            onExport={handleExport}
            onClose={() => setShowExportMenu(false)}
          />
        )}
      </div>
      {/* Share button (optional) */}
      {shareable && (
        <ActionButton
          icon={Share2}
          label="Share"
          compact={compact}
          disabled={disabled}
          onClick={handleShare}
          testId="share-button"
        />
      )}
      {/* Delete button (optional) */}
      {deletable && (
        <ActionButton
          icon={Trash2}
          label="Delete"
          compact={compact}
          disabled={disabled}
          onClick={() => setShowDeleteDialog(true)}
          variant="danger"
          testId="delete-button"
        />
      )}
      {/* Delete confirmation dialog */}
      {showDeleteDialog && (
        <DeleteConfirmDialog
          onConfirm={handleDelete}
          onCancel={() => setShowDeleteDialog(false)}
        />
      )}
    </div>
  );
}
