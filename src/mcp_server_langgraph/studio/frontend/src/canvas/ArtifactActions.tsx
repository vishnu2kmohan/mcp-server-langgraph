/**
 * ArtifactActions - Phase 1
 *
 * Artifact action buttons component for Copy, Fork, Export,
 * Share, and Delete operations.
 */
import { useState, useCallback, useMemo } from "react";
import {
  Copy,
  GitFork,
  Download,
  Share2,
  Trash2,
  Check,
  ChevronDown,
  Wand2,
  Zap,
  MessageSquare,
  Bug,
  Sparkles,
} from "lucide-react";
import type { CanvasArtifact } from "../types/artifacts";
import { cn } from "../utils/cn";

import { Button } from "@/components/UI";

// =============================================================================
// Types
// =============================================================================

export type ExportFormat = "json" | "markdown" | "text";

/** AI action types for canvas artifacts */
export type AIActionType = "refactor" | "optimize" | "explain" | "fix";

/** AI action configuration */
interface AIAction {
  id: AIActionType;
  label: string;
  icon: typeof Wand2;
  /** Content types this action applies to */
  types: CanvasArtifact["contentType"][];
}

/** Available AI actions with type filtering */
const AI_ACTIONS: AIAction[] = [
  {
    id: "refactor",
    label: "Refactor",
    icon: Wand2,
    types: ["code", "jsx"],
  },
  {
    id: "optimize",
    label: "Optimize",
    icon: Zap,
    types: ["code", "jsx"],
  },
  {
    id: "explain",
    label: "Explain",
    icon: MessageSquare,
    types: ["code", "jsx", "markdown", "json"],
  },
  {
    id: "fix",
    label: "Fix Issues",
    icon: Bug,
    types: ["code", "jsx"],
  },
];

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
  /** Enable AI actions in toolbar (Phase 4) */
  enableAI?: boolean;
  /** Callback when AI action is triggered */
  onAIAction?: (artifact: CanvasArtifact, action: AIActionType) => void;
  /** Whether an AI action is currently loading */
  aiActionLoading?: boolean;
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
        "fixed inset-0 z-modal flex items-center justify-center",
        "bg-neutral-a6",
      )}
      onClick={onCancel}
    >
      <div
        className={cn("bg-neutral-1 rounded-lg shadow-xl p-6 max-w-sm mx-4")}
        onClick={(e) => e.stopPropagation()}
      >
        <h3 className="text-lg font-medium text-neutral-12 mb-2">
          Delete Artifact?
        </h3>
        <p className="text-sm text-neutral-11 mb-4">
          This action cannot be undone. The artifact and all its versions will
          be permanently deleted.
        </p>
        <div className="flex justify-end gap-2">
          <Button
            variant="secondary"
            data-testid="cancel-delete-button"
            type="button"
            onClick={onCancel}
            className={cn(
              "px-4 py-2 rounded-lg text-sm font-medium",
              "text-neutral-11",
              "bg-neutral-2",
              "hover:bg-neutral-3",
              "transition-colors",
            )}
          >
            Cancel
          </Button>
          <Button
            variant="danger"
            data-testid="confirm-delete-button"
            type="button"
            onClick={onConfirm}
            className={cn(
              "px-4 py-2 rounded-lg text-sm font-medium",
              "text-neutral-12 bg-error-10 hover:bg-error-11",
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
        "absolute top-full right-0 mt-1 z-dropdown",
        "bg-neutral-1 rounded-lg shadow-lg",
        "border border-neutral-5",
        "py-1 min-w-32",
      )}
    >
      {formats.map(({ format, label }) => (
        <Button
          variant="primary"
          key={format}
          type="button"
          onClick={() => {
            onExport(format);
            onClose();
          }}
          className={cn(
            "w-full px-4 py-2 text-left text-sm",
            "text-neutral-11",
            "hover:bg-neutral-2",
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
      variant="primary"
      data-testid={testId}
      type="button"
      disabled={disabled}
      onClick={onClick}
      title={compact ? label : undefined}
      aria-label={label}
      className={cn(
        "flex items-center gap-1.5 px-2 py-1.5 rounded-lg text-sm font-medium",
        "transition-colors focus:outline-none focus:ring-2 focus:ring-primary-7",
        variant === "default" && "text-neutral-11 hover:bg-neutral-2",
        variant === "danger" &&
          "text-error-11 dark:text-error-11 hover:bg-error-3 dark:hover:bg-error-a4",
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
  enableAI = false,
  onAIAction,
  aiActionLoading = false,
}: ArtifactActionsProps) {
  const [showCopySuccess, setShowCopySuccess] = useState(false);
  const [showExportMenu, setShowExportMenu] = useState(false);
  const [showDeleteDialog, setShowDeleteDialog] = useState(false);

  // Filter AI actions based on artifact content type
  const relevantAIActions = useMemo(() => {
    if (!enableAI) return [];
    return AI_ACTIONS.filter((action) =>
      action.types.includes(artifact.contentType),
    );
  }, [enableAI, artifact.contentType]);

  const handleAIAction = useCallback(
    (actionId: AIActionType) => {
      onAIAction?.(artifact, actionId);
    },
    [artifact, onAIAction],
  );

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
          className="flex items-center gap-1.5 px-2 py-1.5 text-sm text-success-11 dark:text-success-11"
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
          variant="primary"
          type="button"
          disabled={disabled}
          onClick={() => setShowExportMenu(!showExportMenu)}
          title={compact ? "Export" : undefined}
          aria-label="Export"
          className={cn(
            "flex items-center gap-1.5 px-2 py-1.5 rounded-lg text-sm font-medium",
            "transition-colors focus:outline-none focus:ring-2 focus:ring-primary-7",
            "text-neutral-11 hover:bg-neutral-2",
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
      {/* AI Actions Section (Phase 4) - separated by divider */}
      {relevantAIActions.length > 0 && (
        <>
          <div
            data-testid="ai-actions-divider"
            className="w-px h-5 bg-neutral-6 mx-1"
          />
          <div
            data-testid="ai-actions-toolbar"
            className="flex items-center gap-1"
          >
            <Sparkles
              size={14}
              className="text-insight-11 mr-0.5"
              data-testid="ai-sparkles-icon"
            />
            {relevantAIActions.map((action) => (
              <Button
                variant="primary"
                key={action.id}
                type="button"
                data-testid={`ai-action-${action.id}`}
                disabled={disabled || aiActionLoading}
                onClick={() => handleAIAction(action.id)}
                title={action.label}
                aria-label={action.label}
                className={cn(
                  "flex items-center justify-center",
                  "w-8 h-8 p-0 rounded-lg",
                  "text-neutral-11 hover:text-insight-11",
                  "hover:bg-insight-3",
                  "transition-colors duration-150",
                  "focus:outline-none focus:ring-2 focus:ring-primary-7",
                  (disabled || aiActionLoading) &&
                    "opacity-50 cursor-not-allowed",
                )}
              >
                <action.icon size={16} />
              </Button>
            ))}
          </div>
        </>
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
