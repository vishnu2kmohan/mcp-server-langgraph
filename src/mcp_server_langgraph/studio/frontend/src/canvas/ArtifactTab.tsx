/**
 * ArtifactTab Component
 *
 * Individual tab for artifact in the canvas tab bar.
 * Supports:
 * - Click to select
 * - Double-click to rename
 * - Close button
 * - Drag-to-reorder (via @dnd-kit)
 * - Attribution indicator dot
 *
 * Design System Compliance:
 * - Radix color scale (neutral, primary, insight)
 * - 32px minimum touch targets
 * - Smooth transitions
 */

import { useState, useCallback } from "react";
import { useSortable } from "@dnd-kit/sortable";
import { CSS } from "@dnd-kit/utilities";
import { X, GripVertical } from "lucide-react";
import type { CanvasArtifact } from "../types/artifacts";
import { getAttributionType } from "../types/artifacts";
import { cn } from "../utils/cn";

interface ArtifactTabProps {
  /** The artifact to display */
  artifact: CanvasArtifact;
  /** Whether this tab is currently selected */
  isSelected: boolean;
  /** Callback when tab is clicked */
  onSelect: () => void;
  /** Callback when close button is clicked */
  onClose: () => void;
  /** Callback when tab is renamed */
  onRename: (newTitle: string) => void;
  /** Callback when duplicate is requested */
  onDuplicate: () => void;
  /** Callback when export is requested */
  onExport: () => void;
  /** Additional class names */
  className?: string;
}

export function ArtifactTab({
  artifact,
  isSelected,
  onSelect,
  onClose,
  onRename,
  className = "",
}: ArtifactTabProps) {
  const [isRenaming, setIsRenaming] = useState(false);
  const [renameValue, setRenameValue] = useState(artifact.title || "Untitled");

  const {
    attributes,
    listeners,
    setNodeRef,
    transform,
    transition,
    isDragging,
  } = useSortable({ id: artifact.id });

  const style = {
    transform: CSS.Transform.toString(transform),
    transition,
  };

  const displayTitle = artifact.title || "Untitled";
  const attributionType = getAttributionType(artifact.editMetadata);

  const handleClick = useCallback(() => {
    if (!isRenaming) {
      onSelect();
    }
  }, [isRenaming, onSelect]);

  const handleDoubleClick = useCallback(() => {
    setRenameValue(displayTitle);
    setIsRenaming(true);
  }, [displayTitle]);

  const handleCloseClick = useCallback(
    (e: React.MouseEvent) => {
      e.stopPropagation();
      onClose();
    },
    [onClose]
  );

  const handleRenameSubmit = useCallback(() => {
    if (renameValue.trim()) {
      onRename(renameValue.trim());
    }
    setIsRenaming(false);
  }, [renameValue, onRename]);

  const handleRenameKeyDown = useCallback(
    (e: React.KeyboardEvent) => {
      if (e.key === "Enter") {
        e.preventDefault();
        handleRenameSubmit();
      } else if (e.key === "Escape") {
        e.preventDefault();
        setIsRenaming(false);
      }
    },
    [handleRenameSubmit]
  );

  const handleRenameBlur = useCallback(() => {
    // Don't submit on blur, just cancel
    setIsRenaming(false);
  }, []);

  return (
    <div
      ref={setNodeRef}
      style={style}
      role="tab"
      aria-selected={isSelected}
      tabIndex={isSelected ? 0 : -1}
      onClick={handleClick}
      onDoubleClick={handleDoubleClick}
      data-testid={`artifact-tab-${artifact.id}`}
      className={cn(
        "group relative flex items-center",
        "px-3 py-1.5 rounded-t-md",
        "text-sm font-medium",
        "cursor-pointer select-none",
        "transition-colors duration-150",
        isSelected
          ? "bg-neutral-1 text-neutral-12 border-b-2 border-primary-9"
          : "bg-neutral-2 text-neutral-11 hover:bg-neutral-3 hover:text-neutral-12",
        isDragging && "opacity-50 shadow-lg z-dropdown",
        className
      )}
    >
      {/* Drag handle */}
      <button
        {...attributes}
        {...listeners}
        type="button"
        className={cn(
          "mr-1.5 p-0.5 -ml-1",
          "opacity-0 group-hover:opacity-100",
          "text-neutral-11 hover:text-neutral-11",
          "cursor-grab active:cursor-grabbing",
          "transition-opacity duration-150",
          "flex items-center justify-center"
        )}
        aria-label="Drag to reorder"
        tabIndex={-1}
      >
        <GripVertical className="w-3 h-3" />
      </button>

      {/* Attribution indicator (small dot) */}
      {attributionType === "ai-generated" && (
        <span
          data-testid="attribution-dot"
          className="w-1.5 h-1.5 rounded-full bg-insight-9 mr-1.5"
        />
      )}
      {attributionType === "user-modified" && (
        <span
          data-testid="attribution-dot"
          className="w-1.5 h-1.5 rounded-full bg-primary-9 mr-1.5"
        />
      )}

      {/* Tab title - inline edit or text */}
      {isRenaming ? (
        <input
          type="text"
          value={renameValue}
          onChange={(e) => setRenameValue(e.target.value)}
          onKeyDown={handleRenameKeyDown}
          onBlur={handleRenameBlur}
          className={cn(
            "text-sm font-medium min-w-[60px] max-w-[120px]",
            "bg-transparent border-b border-primary-7",
            "focus:outline-none focus:border-primary-9",
            "text-neutral-12"
          )}
          autoFocus
          onClick={(e) => e.stopPropagation()}
        />
      ) : (
        <span className="truncate max-w-[120px]">{displayTitle}</span>
      )}

      {/* Close button */}
      <button
        type="button"
        onClick={handleCloseClick}
        className={cn(
          "ml-2 p-0.5 rounded",
          "opacity-0 group-hover:opacity-100",
          "text-neutral-11 hover:text-neutral-12",
          "hover:bg-neutral-4",
          "transition-all duration-150",
          "min-w-6 min-h-6",
          "flex items-center justify-center"
        )}
        aria-label={`Close ${displayTitle}`}
        tabIndex={-1}
      >
        <X className="w-3 h-3" />
      </button>
    </div>
  );
}

export default ArtifactTab;
