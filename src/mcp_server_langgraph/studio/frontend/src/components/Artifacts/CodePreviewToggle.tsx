/**
 * CodePreviewToggle Component
 *
 * A toggle button group for switching between Code and Preview views.
 * Used in artifact viewers (SVG, Mermaid, HTML, etc.) following Claude's pattern.
 */

import { type HTMLAttributes } from "react";

import { Button } from "@/components/UI";

export type ViewMode = "code" | "preview";

export interface CodePreviewToggleProps extends Omit<
  HTMLAttributes<HTMLDivElement>,
  "onChange"
> {
  /** Current view mode */
  mode: ViewMode;
  /** Callback when mode changes */
  onModeChange: (mode: ViewMode) => void;
  /** Whether preview is supported/available */
  previewSupported?: boolean;
}

/**
 * Utility to combine class names
 */
function cn(...classes: (string | undefined | boolean)[]): string {
  return classes.filter(Boolean).join(" ");
}

/**
 * CodePreviewToggle component for Code/Preview mode switching
 */
export function CodePreviewToggle({
  mode,
  onModeChange,
  previewSupported = true,
  className,
  "aria-label": ariaLabel = "View mode",
  ...props
}: CodePreviewToggleProps) {
  const handleCodeClick = () => {
    if (mode !== "code") {
      onModeChange("code");
    }
  };

  const handlePreviewClick = () => {
    if (mode !== "preview" && previewSupported) {
      onModeChange("preview");
    }
  };

  return (
    <div
      role="group"
      aria-label={ariaLabel}
      className={cn(
        "inline-flex rounded-lg border border-neutral-5 p-0.5",
        "bg-neutral-2",
        className,
      )}
      {...props}
    >
      <Button
        variant="primary"
        type="button"
        onClick={handleCodeClick}
        aria-pressed={mode === "code"}
        className={cn(
          "px-3 py-1 text-xs font-medium rounded-md transition-colors",
          "focus:outline-none focus:ring-2 focus:ring-brand-primary focus:ring-offset-1",
          mode === "code"
            ? "bg-primary-9 text-neutral-12 shadow-sm"
            : "text-neutral-11 hover:text-neutral-12",
        )}>
        Code
      </Button>
      <Button
        variant="primary"
        type="button"
        onClick={handlePreviewClick}
        aria-pressed={mode === "preview"}
        disabled={!previewSupported}
        title={!previewSupported ? "Preview not available" : undefined}
        className={cn(
          "px-3 py-1 text-xs font-medium rounded-md transition-colors",
          "focus:outline-none focus:ring-2 focus:ring-brand-primary focus:ring-offset-1",
          mode === "preview"
            ? "bg-primary-9 text-neutral-12 shadow-sm"
            : "text-neutral-11 hover:text-neutral-12",
          !previewSupported && "opacity-50 cursor-not-allowed",
        )}>
        Preview
      </Button>
    </div>
  );
}

CodePreviewToggle.displayName = "CodePreviewToggle";
