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
        "bg-neutral-2",
        "text-xs font-mono font-medium",
        "text-neutral-11",
        "border border-neutral-5",
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
          "rounded-lg border border-neutral-5",
          "bg-neutral-1 p-4",
          "text-sm text-neutral-11",
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
        "rounded-lg border border-neutral-5",
        "bg-neutral-1",
        className,
      )}
    >
      {/* Header */}
      <div className="flex items-center gap-2 p-4 border-b border-neutral-5">
        <Keyboard size={18} className="text-primary-9" />
        <h3 className="font-semibold text-neutral-12">Keyboard Shortcuts</h3>
      </div>

      {/* Categories */}
      <div className="p-4 space-y-6">
        {categories.map((category) => (
          <div key={category.id}>
            <h4 className="text-sm font-medium text-neutral-12 mb-3">
              {category.name}
            </h4>
            <div className="space-y-2">
              {category.shortcuts.map((shortcut) => (
                <div
                  key={shortcut.id}
                  className="flex items-center justify-between py-1.5"
                >
                  <span className="text-sm text-neutral-11">
                    {shortcut.description}
                  </span>
                  <div className="flex items-center gap-1">
                    {shortcut.keys.map((key, index) => (
                      <span key={`${shortcut.id}-${key}-${index}`}>
                        <KeyBadge keyName={key} />
                        {index < shortcut.keys.length - 1 && (
                          <span className="mx-0.5 text-neutral-9">+</span>
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
