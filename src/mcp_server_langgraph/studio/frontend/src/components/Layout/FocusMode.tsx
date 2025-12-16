/**
 * FocusMode Component
 *
 * JupyterLab-style Simple Interface mode.
 * Allows users to toggle between full workspace and focused single-panel view.
 *
 * Features:
 * - Toggle between showing all panels and focused main panel only
 * - Keyboard shortcut (Escape) to exit focus mode
 * - Controlled and uncontrolled modes
 * - Smooth CSS transitions
 */

import {
  useState,
  useCallback,
  useEffect,
  type ReactNode,
  type HTMLAttributes,
} from "react";
import { Maximize2, Minimize2 } from "lucide-react";

// =============================================================================
// Utility
// =============================================================================

function cn(...classes: (string | undefined | boolean)[]): string {
  return classes.filter(Boolean).join(" ");
}

// =============================================================================
// FocusModeToggle - Button to toggle focus mode
// =============================================================================

export interface FocusModeToggleProps extends Omit<
  HTMLAttributes<HTMLButtonElement>,
  "onClick"
> {
  /** Whether focus mode is active */
  isFocused: boolean;
  /** Callback when toggle is clicked */
  onToggle: () => void;
  /** Additional class names */
  className?: string;
}

export function FocusModeToggle({
  isFocused,
  onToggle,
  className,
  ...props
}: FocusModeToggleProps) {
  return (
    <button
      type="button"
      onClick={onToggle}
      className={cn(
        "p-2 rounded-lg transition-colors",
        "text-gray-500 hover:text-gray-700 dark:text-gray-400 dark:hover:text-gray-200",
        "hover:bg-gray-100 dark:hover:bg-gray-800",
        "focus:outline-none focus:ring-2 focus:ring-primary-500",
        className,
      )}
      aria-label={isFocused ? "Exit focus mode" : "Enter focus mode"}
      title={isFocused ? "Exit focus mode (Esc)" : "Enter focus mode"}
      {...props}
    >
      {isFocused ? <Minimize2 size={18} /> : <Maximize2 size={18} />}
    </button>
  );
}

// =============================================================================
// FocusMode - Main container component
// =============================================================================

export interface FocusModeProps {
  /** Left panel content */
  leftPanel: ReactNode;
  /** Main panel content (always visible) */
  mainPanel: ReactNode;
  /** Right panel content */
  rightPanel: ReactNode;
  /** Initial focus state (uncontrolled mode) */
  defaultFocused?: boolean;
  /** Controlled focus state */
  isFocused?: boolean;
  /** Callback when focus mode changes */
  onFocusChange?: (focused: boolean) => void;
  /** Enable keyboard shortcut (Escape to exit) */
  enableKeyboardShortcut?: boolean;
  /** Additional class names */
  className?: string;
}

export function FocusMode({
  leftPanel,
  mainPanel,
  rightPanel,
  defaultFocused = false,
  isFocused: controlledFocused,
  onFocusChange,
  enableKeyboardShortcut = true,
  className,
}: FocusModeProps) {
  // Internal state for uncontrolled mode
  const [internalFocused, setInternalFocused] = useState(defaultFocused);

  // Use controlled or uncontrolled value
  const isControlled = controlledFocused !== undefined;
  const focused = isControlled ? controlledFocused : internalFocused;

  // Handle toggle
  const handleToggle = useCallback(() => {
    const newFocused = !focused;

    if (!isControlled) {
      setInternalFocused(newFocused);
    }

    onFocusChange?.(newFocused);
  }, [focused, isControlled, onFocusChange]);

  // Keyboard shortcut handler
  useEffect(() => {
    if (!enableKeyboardShortcut) return;

    const handleKeyDown = (event: KeyboardEvent) => {
      // Only handle Escape when in focus mode
      if (event.key === "Escape" && focused) {
        event.preventDefault();
        handleToggle();
      }
    };

    document.addEventListener("keydown", handleKeyDown);
    return () => document.removeEventListener("keydown", handleKeyDown);
  }, [enableKeyboardShortcut, focused, handleToggle]);

  return (
    <div className={cn("flex h-full w-full relative", className)}>
      {/* Left Panel */}
      <div
        className={cn(
          "transition-all duration-300 ease-in-out overflow-hidden",
          "border-r border-gray-200 dark:border-gray-700",
          focused ? "w-0 opacity-0 invisible" : "w-64 opacity-100 visible",
        )}
        aria-hidden={focused}
      >
        {leftPanel}
      </div>

      {/* Main Panel */}
      <div className="flex-1 flex flex-col min-w-0 relative">
        {/* Focus mode toggle in corner */}
        <div className="absolute top-2 right-2 z-10">
          <FocusModeToggle isFocused={focused} onToggle={handleToggle} />
        </div>
        {mainPanel}
      </div>

      {/* Right Panel */}
      <div
        className={cn(
          "transition-all duration-300 ease-in-out overflow-hidden",
          "border-l border-gray-200 dark:border-gray-700",
          focused ? "w-0 opacity-0 invisible" : "w-64 opacity-100 visible",
        )}
        aria-hidden={focused}
      >
        {rightPanel}
      </div>
    </div>
  );
}

// =============================================================================
// useFocusMode - Hook for managing focus mode state
// =============================================================================

export interface UseFocusModeReturn {
  /** Current focus mode state */
  isFocused: boolean;
  /** Toggle focus mode */
  toggle: () => void;
  /** Enter focus mode */
  enterFocus: () => void;
  /** Exit focus mode */
  exitFocus: () => void;
}

// eslint-disable-next-line react-refresh/only-export-components
export function useFocusMode(
  initialValue: boolean = false,
): UseFocusModeReturn {
  const [isFocused, setIsFocused] = useState(initialValue);

  const toggle = useCallback(() => {
    setIsFocused((prev) => !prev);
  }, []);

  const enterFocus = useCallback(() => {
    setIsFocused(true);
  }, []);

  const exitFocus = useCallback(() => {
    setIsFocused(false);
  }, []);

  return {
    isFocused,
    toggle,
    enterFocus,
    exitFocus,
  };
}

export default FocusMode;
