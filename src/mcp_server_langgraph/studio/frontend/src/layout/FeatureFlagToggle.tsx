/**
 * FeatureFlagToggle Component
 *
 * Dev-mode toggle for switching between StudioShell and AppShell.
 * Persists state to localStorage for persistence across page reloads.
 *
 * Usage:
 * - Only visible in development mode by default
 * - Can be forced to show with forceShow prop
 * - Toggle state is persisted to localStorage
 */
import { useState, useCallback, useEffect } from "react";
import { cn } from "../utils/cn";
import { storage } from "../utils/storage";

const STORAGE_KEY = "studio-hybrid-shell-override";

export interface FeatureFlagToggleProps {
  /** Whether we're in dev mode */
  isDev: boolean;
  /** Force showing the toggle even in production */
  forceShow?: boolean;
  /** Callback when toggle changes */
  onChange?: (enabled: boolean) => void;
  /** Additional CSS classes */
  className?: string;
}

/**
 * Get initial state from storage
 */
function getInitialState(): boolean {
  const stored = storage.get<boolean>(STORAGE_KEY);
  if (stored !== undefined) {
    return stored;
  }
  // Default to hybrid shell enabled
  return true;
}

/**
 * Dev-mode feature flag toggle for shell switching
 */
export function FeatureFlagToggle({
  isDev,
  forceShow = false,
  onChange,
  className,
}: FeatureFlagToggleProps) {
  const [isHybridEnabled, setIsHybridEnabled] = useState(getInitialState);

  // Persist to storage when state changes
  useEffect(() => {
    storage.set(STORAGE_KEY, isHybridEnabled);
  }, [isHybridEnabled]);

  const handleToggle = useCallback(() => {
    const newValue = !isHybridEnabled;
    setIsHybridEnabled(newValue);
    onChange?.(newValue);
  }, [isHybridEnabled, onChange]);

  // Don't render in production unless forced
  if (!isDev && !forceShow) {
    return null;
  }

  const modeLabel = isHybridEnabled ? "Hybrid" : "Legacy";

  return (
    <div
      data-testid="feature-flag-toggle"
      className={cn(
        "flex items-center gap-2 px-2 py-1 rounded-lg",
        "bg-gray-100 dark:bg-gray-800",
        "text-xs text-gray-600 dark:text-gray-400",
        className,
      )}
    >
      <span className="font-medium">Shell Mode:</span>
      <button
        type="button"
        role="switch"
        aria-checked={isHybridEnabled}
        aria-label="Toggle shell mode between Hybrid and Legacy"
        onClick={handleToggle}
        className={cn(
          "relative flex items-center w-10 h-5 rounded-full",
          "transition-colors",
          isHybridEnabled ? "bg-primary-500" : "bg-gray-300 dark:bg-gray-600",
        )}
      >
        <span
          className={cn(
            "absolute w-4 h-4 rounded-full bg-white shadow-sm transition-transform",
            isHybridEnabled ? "translate-x-5" : "translate-x-0.5",
          )}
        />
      </button>
      <span
        data-testid="current-mode"
        className={cn(
          "min-w-12",
          isHybridEnabled
            ? "text-primary-600 dark:text-primary-400"
            : "text-gray-500 dark:text-gray-400",
        )}
      >
        {modeLabel}
      </span>
    </div>
  );
}
