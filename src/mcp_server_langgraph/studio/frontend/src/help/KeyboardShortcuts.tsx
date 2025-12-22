/**
 * KeyboardShortcuts Component
 *
 * Phase 6: Help & Accessibility
 * Keyboard shortcuts reference panel.
 *
 * Features:
 * - Category-based organization
 * - Key combination display
 * - Accessible structure
 */

import { Keyboard } from "lucide-react";
import { cn } from "../utils/cn";

// =============================================================================
// Types
// =============================================================================

export interface Shortcut {
  id: string;
  keys: string[];
  description: string;
}

export interface ShortcutCategory {
  id: string;
  name: string;
  shortcuts: Shortcut[];
}

export interface KeyboardShortcutsProps {
  categories: ShortcutCategory[];
  className?: string;
}

// =============================================================================
// Key Badge Component
// =============================================================================

function KeyBadge({ keyName }: { keyName: string }) {
  return (
    <kbd
      className={cn(
        "px-1.5 py-0.5 rounded",
        "bg-gray-100 dark:bg-gray-700",
        "text-xs font-mono font-medium",
        "text-gray-700 dark:text-gray-300",
        "border border-gray-200 dark:border-gray-600",
        "shadow-sm",
      )}
    >
      {keyName}
    </kbd>
  );
}

// =============================================================================
// Component
// =============================================================================

export function KeyboardShortcuts({
  categories,
  className,
}: KeyboardShortcutsProps) {
  // Empty state
  if (categories.length === 0) {
    return (
      <div
        data-testid="keyboard-shortcuts"
        className={cn(
          "rounded-lg border border-gray-200 dark:border-gray-700",
          "bg-white dark:bg-gray-900 p-4",
          "text-sm text-gray-500 dark:text-gray-400",
          className,
        )}
      >
        <div className="flex items-center gap-2">
          <Keyboard size={16} className="opacity-50" />
          <span>No shortcuts configured</span>
        </div>
      </div>
    );
  }

  return (
    <div
      data-testid="keyboard-shortcuts"
      className={cn(
        "rounded-lg border border-gray-200 dark:border-gray-700",
        "bg-white dark:bg-gray-900",
        className,
      )}
    >
      {/* Header */}
      <div className="flex items-center gap-2 p-4 border-b border-gray-200 dark:border-gray-700">
        <Keyboard size={18} className="text-primary-500" />
        <h3 className="font-semibold text-gray-900 dark:text-gray-100">
          Keyboard Shortcuts
        </h3>
      </div>

      {/* Categories */}
      <div className="p-4 space-y-6">
        {categories.map((category) => (
          <div key={category.id}>
            <h4 className="text-sm font-medium text-gray-900 dark:text-gray-100 mb-3">
              {category.name}
            </h4>
            <div className="space-y-2">
              {category.shortcuts.map((shortcut) => (
                <div
                  key={shortcut.id}
                  className="flex items-center justify-between py-1.5"
                >
                  <span className="text-sm text-gray-600 dark:text-gray-400">
                    {shortcut.description}
                  </span>
                  <div className="flex items-center gap-1">
                    {shortcut.keys.map((key, index) => (
                      <span key={`${shortcut.id}-${key}-${index}`}>
                        <KeyBadge keyName={key} />
                        {index < shortcut.keys.length - 1 && (
                          <span className="mx-0.5 text-gray-400">+</span>
                        )}
                      </span>
                    ))}
                  </div>
                </div>
              ))}
            </div>
          </div>
        ))}
      </div>
    </div>
  );
}
