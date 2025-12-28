/**
 * CodePreviewToggle Component
 *
 * A toggle button group for switching between Code and Preview views.
 * Used in artifact viewers (SVG, Mermaid, HTML, etc.) following Claude's pattern.
 */

import { type HTMLAttributes } from "react";

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
        "inline-flex rounded-lg border border-gray-200 dark:border-gray-700 p-0.5",
        "bg-gray-100 dark:bg-gray-800",
        className,
      )}
      {...props}
    >
      <button
        type="button"
        onClick={handleCodeClick}
        aria-pressed={mode === "code"}
        className={cn(
          "px-3 py-1 text-xs font-medium rounded-md transition-colors",
          "focus:outline-none focus:ring-2 focus:ring-brand-primary focus:ring-offset-1",
          mode === "code"
            ? "bg-blue-500 text-white shadow-sm"
            : "text-gray-600 hover:text-gray-900 dark:text-gray-400 dark:hover:text-gray-200",
        )}
      >
        Code
      </button>
      <button
        type="button"
        onClick={handlePreviewClick}
        aria-pressed={mode === "preview"}
        disabled={!previewSupported}
        title={!previewSupported ? "Preview not available" : undefined}
        className={cn(
          "px-3 py-1 text-xs font-medium rounded-md transition-colors",
          "focus:outline-none focus:ring-2 focus:ring-brand-primary focus:ring-offset-1",
          mode === "preview"
            ? "bg-blue-500 text-white shadow-sm"
            : "text-gray-600 hover:text-gray-900 dark:text-gray-400 dark:hover:text-gray-200",
          !previewSupported && "opacity-50 cursor-not-allowed",
        )}
      >
        Preview
      </button>
    </div>
  );
}

CodePreviewToggle.displayName = "CodePreviewToggle";
