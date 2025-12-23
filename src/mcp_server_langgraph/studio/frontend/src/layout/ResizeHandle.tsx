/**
 * ResizeHandle Component
 *
 * Panel resize handle for react-resizable-panels.
 * Used between resizable panels in the StudioShell layout.
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

export interface ResizeHandleProps extends Omit<
  ComponentProps<typeof PanelResizeHandle>,
  "className"
> {
  /** Additional CSS classes */
  className?: string;
  /** Whether this is a vertical resize handle (horizontal divider) */
  vertical?: boolean;
}

// =============================================================================
// Component
// =============================================================================

export function ResizeHandle({
  className,
  vertical,
  ...props
}: ResizeHandleProps) {
  return (
    <PanelResizeHandle
      className={cn(
        "transition-all",
        "bg-transparent hover:bg-primary-500/30",
        vertical
          ? "h-1 hover:h-2 cursor-row-resize"
          : "w-1 hover:w-2 cursor-col-resize",
        className,
      )}
      {...props}
    />
  );
}
