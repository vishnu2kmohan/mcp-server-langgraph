/**
 * KeyboardShortcutOverlay Component (Sprint 3.1)
 *
 * Modal overlay displaying available keyboard shortcuts.
 * Toggled with the ? key or from Help menu.
 *
 * Features:
 * - Displays all shortcuts from the keyboardShortcuts map
 * - Formats shortcuts for Mac/Windows display
 * - Closes on Escape, backdrop click, or close button
 * - Accessible modal dialog with proper ARIA attributes
 */
import { useEffect, useCallback, useMemo, useRef } from "react";
import { X } from "lucide-react";
import { cn } from "../../utils/cn";
import { useFocusTrap } from "../../hooks/useFocusTrap";

import { Button } from "@/components/UI";

// =============================================================================
// Types
// =============================================================================

export interface KeyboardShortcutOverlayProps {
  /** Map of keyboard shortcuts (from useKeyboardShortcuts) */
  shortcuts: Record<string, () => void>;
  /** Whether the overlay is visible */
  isOpen: boolean;
  /** Callback when overlay should close */
  onClose: () => void;
}

interface FormattedShortcut {
  key: string;
  displayKey: string;
  description: string;
  category: string;
}

// =============================================================================
// Helper Functions
// =============================================================================

/**
 * Format a shortcut key for display (e.g., "meta+k" → "⌘K")
 */
function formatShortcutKey(key: string): string {
  const parts = key.toLowerCase().split("+");
  const formattedParts = parts.map((part) => {
    switch (part) {
      case "meta":
      case "cmd":
        return "⌘";
      case "ctrl":
        return "⌃";
      case "alt":
        return "⌥";
      case "shift":
        return "⇧";
      case "escape":
        return "Esc";
      default:
        return part.toUpperCase();
    }
  });
  return formattedParts.join("");
}

/**
 * Derive description from shortcut key
 */
function getShortcutDescription(key: string): string {
  const normalizedKey = key.toLowerCase().replace(/^(meta|ctrl)\+/, "");

  const descriptions: Record<string, string> = {
    "/": "Toggle Canvas",
    k: "Open Command Palette",
    "shift+i": "Toggle DevTools",
    "shift+f": "Toggle Focus Mode",
    "shift+?": "Show Shortcuts",
    "?": "Show Shortcuts",
    b: "Toggle Sidebar",
    ",": "Open Settings",
    n: "New Chat",
    escape: "Exit Focus Mode",
  };

  return descriptions[normalizedKey] || key;
}

/**
 * Get category for a shortcut
 */
function getShortcutCategory(key: string): string {
  const normalizedKey = key.toLowerCase();

  if (normalizedKey.includes("/") || normalizedKey.includes("b")) {
    return "Layout";
  }
  if (normalizedKey.includes("k")) {
    return "Navigation";
  }
  if (normalizedKey.includes("i") || normalizedKey.includes("f")) {
    return "View";
  }
  if (normalizedKey === "escape") {
    return "General";
  }
  return "General";
}

// =============================================================================
// Component
// =============================================================================

export function KeyboardShortcutOverlay({
  shortcuts,
  isOpen,
  onClose,
}: KeyboardShortcutOverlayProps) {
  // Ref for focus trap
  const dialogRef = useRef<HTMLDivElement>(null);

  // Trap focus within dialog for accessibility
  useFocusTrap(dialogRef, isOpen);

  // Handle escape key to close
  const handleKeyDown = useCallback(
    (event: KeyboardEvent) => {
      if (event.key === "Escape") {
        onClose();
      }
    },
    [onClose],
  );

  useEffect(() => {
    if (isOpen) {
      document.addEventListener("keydown", handleKeyDown);
      return () => document.removeEventListener("keydown", handleKeyDown);
    }
    return undefined;
  }, [isOpen, handleKeyDown]);

  // Process shortcuts into displayable format
  // Deduplicate meta+/ctrl+ variants (prefer meta for display)
  const formattedShortcuts = useMemo((): FormattedShortcut[] => {
    const seen = new Set<string>();
    const result: FormattedShortcut[] = [];

    for (const key of Object.keys(shortcuts)) {
      // Skip ctrl variants if meta variant exists
      if (key.startsWith("ctrl+")) {
        const metaVariant = key.replace("ctrl+", "meta+");
        if (shortcuts[metaVariant]) {
          continue; // Skip, we'll use the meta variant
        }
      }

      // Normalize key for deduplication
      const normalizedKey = key.replace(/^(meta|ctrl)\+/, "");
      if (seen.has(normalizedKey)) {
        continue;
      }
      seen.add(normalizedKey);

      result.push({
        key,
        displayKey: formatShortcutKey(key),
        description: getShortcutDescription(key),
        category: getShortcutCategory(key),
      });
    }

    // Sort by category then by key
    return result.sort((a, b) => {
      if (a.category !== b.category) {
        return a.category.localeCompare(b.category);
      }
      return a.key.localeCompare(b.key);
    });
  }, [shortcuts]);

  // Group shortcuts by category
  const groupedShortcuts = useMemo(() => {
    const groups: Record<string, FormattedShortcut[]> = {};
    for (const shortcut of formattedShortcuts) {
      if (!groups[shortcut.category]) {
        groups[shortcut.category] = [];
      }
      groups[shortcut.category].push(shortcut);
    }
    return groups;
  }, [formattedShortcuts]);

  if (!isOpen) {
    return null;
  }

  return (
    <>
      {/* Backdrop */}
      <div
        data-testid="overlay-backdrop"
        className="fixed inset-0 z-50 bg-black/50 dark:bg-black/70"
        onClick={onClose}
        aria-hidden="true"
      />
      {/* Dialog */}
      <div
        ref={dialogRef}
        data-testid="keyboard-shortcut-overlay"
        role="dialog"
        aria-modal="true"
        aria-labelledby="shortcut-overlay-title"
        className={cn(
          "fixed left-1/2 top-1/2 z-50 -translate-x-1/2 -translate-y-1/2",
          "w-full max-w-md max-h-[80vh] overflow-auto",
          "bg-white dark:bg-neutral-800 rounded-lg shadow-xl",
          "border border-neutral-200 dark:border-neutral-700",
        )}
      >
        {/* Header */}
        <div className="flex items-center justify-between px-4 py-3 border-b border-neutral-200 dark:border-neutral-700">
          <h2
            id="shortcut-overlay-title"
            className="text-lg font-semibold text-neutral-900 dark:text-white"
          >
            Keyboard Shortcuts
          </h2>
          <Button
            data-testid="close-button"
            type="button"
            onClick={onClose}
            className={cn(
              "p-1 rounded-md",
              "text-neutral-500 dark:text-neutral-400 hover:text-neutral-700 dark:text-neutral-200 dark:text-neutral-400 dark:hover:text-neutral-200",
              "hover:bg-neutral-100 dark:bg-neutral-800 dark:hover:bg-neutral-700",
              "focus:outline-none focus:ring-2 focus:ring-primary-500",
            )}
            aria-label="Close shortcuts"
          >
            <X size={20} aria-hidden="true" />
          </Button>
        </div>

        {/* Shortcut List */}
        <div data-testid="shortcut-list" className="p-4 space-y-4">
          {Object.entries(groupedShortcuts).map(([category, shortcuts]) => (
            <div key={category}>
              <h3 className="text-xs font-semibold uppercase tracking-wider text-neutral-500 dark:text-neutral-400 mb-2">
                {category}
              </h3>
              <div className="space-y-1">
                {shortcuts.map((shortcut) => (
                  <div
                    key={shortcut.key}
                    className="flex items-center justify-between py-1"
                  >
                    <span className="text-sm text-neutral-700 dark:text-neutral-300">
                      {shortcut.description}
                    </span>
                    <kbd
                      className={cn(
                        "px-2 py-1 rounded",
                        "bg-neutral-100 dark:bg-neutral-700",
                        "text-sm font-mono text-neutral-800 dark:text-neutral-200",
                        "border border-neutral-300 dark:border-neutral-600",
                      )}
                    >
                      {shortcut.displayKey}
                    </kbd>
                  </div>
                ))}
              </div>
            </div>
          ))}

          {formattedShortcuts.length === 0 && (
            <p className="text-sm text-neutral-500 dark:text-neutral-400 text-center py-4">
              No keyboard shortcuts available.
            </p>
          )}
        </div>

        {/* Footer hint */}
        <div className="px-4 py-3 border-t border-neutral-200 dark:border-neutral-700">
          <p className="text-xs text-neutral-500 dark:text-neutral-400 text-center">
            Press{" "}
            <kbd className="px-1 py-0.5 rounded bg-neutral-100 dark:bg-neutral-700 font-mono">
              Esc
            </kbd>{" "}
            to close
          </p>
        </div>
      </div>
    </>
  );
}
