/**
 * ResizeHandle Component
 *
 * Panel resize handle for react-resizable-panels.
 * Used between resizable panels in the HybridShell layout.
 *
 * Features:
 * - Subtle visual indicator
 * - Hover effect with color highlight
 * - Smooth transition animations
 */
import { PanelResizeHandle } from "react-resizable-panels";
import type { ComponentProps } from "react";
import { cn } from "../utils/cn";

// =============================================================================
// Types
// =============================================================================

export interface ResizeHandleProps
  extends Omit<ComponentProps<typeof PanelResizeHandle>, "className"> {
  /** Additional CSS classes */
  className?: string;
}

// =============================================================================
// Component
// =============================================================================

export function ResizeHandle({ className, ...props }: ResizeHandleProps) {
  return (
    <PanelResizeHandle
      className={cn(
        "w-1 hover:w-2 transition-all",
        "bg-transparent hover:bg-primary-500/30",
        "cursor-col-resize",
        className,
      )}
      {...props}
    />
  );
}
