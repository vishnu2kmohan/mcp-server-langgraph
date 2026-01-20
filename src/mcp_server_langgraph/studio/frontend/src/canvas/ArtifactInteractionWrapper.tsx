/**
 * ArtifactInteractionWrapper Component
 *
 * Wraps inline artifacts in chat to enable on-demand canvas launch.
 * Supports:
 * - Popout icon on hover (top-right)
 * - Double-click to open in canvas
 *
 * Design System Compliance:
 * - Radix color scale (neutral, primary)
 * - 32px minimum touch targets
 * - Smooth transitions
 */

import { useCallback } from "react";
import { ExternalLink } from "lucide-react";
import type { BaseArtifact } from "../types/artifacts";
import { useAppDispatch } from "../store/hooks";
import {
  setCanvasCollapsed,
  setSelectedArtifactId,
  addToTabOrder,
} from "../store/slices/canvasSlice";
import { cn } from "../utils/cn";

/**
 * Minimal artifact type for wrapper - only needs id for Redux actions
 * Accepts both Artifact (from chat) and CanvasArtifact (from canvas)
 */
type WrapperArtifact = BaseArtifact & { id: string };

interface ArtifactInteractionWrapperProps {
  /** The artifact to wrap - any artifact with an id */
  artifact: WrapperArtifact;
  /** Child content (the artifact renderer) */
  children: React.ReactNode;
  /** Optional callback when opening in canvas */
  onOpenInCanvas?: (artifact: WrapperArtifact) => void;
  /** Additional class names */
  className?: string;
  /** Disable interaction (no popout, no double-click) */
  disabled?: boolean;
}

export function ArtifactInteractionWrapper({
  artifact,
  children,
  onOpenInCanvas,
  className = "",
  disabled = false,
}: ArtifactInteractionWrapperProps) {
  const dispatch = useAppDispatch();

  const handleOpenInCanvas = useCallback(() => {
    if (disabled) return;

    // Expand canvas and select artifact
    dispatch(setCanvasCollapsed(false));
    dispatch(setSelectedArtifactId(artifact.id));
    dispatch(addToTabOrder(artifact.id));

    // Call custom callback if provided
    if (onOpenInCanvas) {
      onOpenInCanvas(artifact);
    }
  }, [artifact, disabled, dispatch, onOpenInCanvas]);

  const handleDoubleClick = useCallback(
    (e: React.MouseEvent) => {
      e.preventDefault();
      handleOpenInCanvas();
    },
    [handleOpenInCanvas]
  );

  const handlePopoutClick = useCallback(
    (e: React.MouseEvent) => {
      e.stopPropagation();
      handleOpenInCanvas();
    },
    [handleOpenInCanvas]
  );

  return (
    <div
      data-testid="artifact-interaction-wrapper"
      className={cn("group relative", className)}
      onDoubleClick={handleDoubleClick}
    >
      {children}

      {/* Popout button - appears on hover */}
      {!disabled && (
        <button
          type="button"
          data-testid="popout-button"
          onClick={handlePopoutClick}
          className={cn(
            "absolute top-2 right-2",
            "opacity-0 group-hover:opacity-100",
            "p-1.5 rounded-md",
            "bg-neutral-2 backdrop-blur-sm",
            "border border-neutral-6",
            "text-neutral-11 hover:text-neutral-12",
            "hover:bg-neutral-3",
            "transition-all duration-150",
            "shadow-sm",
            "min-w-[32px] min-h-[32px]",
            "flex items-center justify-center",
            "focus:outline-none focus:ring-2 focus:ring-primary-7"
          )}
          aria-label="Open in canvas"
        >
          <ExternalLink className="w-4 h-4" />
        </button>
      )}
    </div>
  );
}

export default ArtifactInteractionWrapper;
