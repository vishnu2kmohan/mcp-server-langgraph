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
import { useReducedMotion } from "motion/react";
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
  // WCAG 2.2 AA: Respect user's reduced motion preference
  const prefersReducedMotion = useReducedMotion();

  return (
    <PanelResizeHandle
      className={cn(
        !prefersReducedMotion && "transition-colors",
        "bg-transparent hover:bg-primary-a4",
        "relative z-10",
        // Invisible hit target via before: pseudo-element
        "before:absolute before:inset-0 before:z-10",
        vertical
          ? "h-1 cursor-row-resize before:-top-2 before:-bottom-2"
          : "w-1 cursor-col-resize before:-left-2 before:-right-2",
        className,
      )}
      {...props}
    />
  );
}
