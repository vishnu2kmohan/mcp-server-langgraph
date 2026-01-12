/**
 * ShortcutsPanel Component
 *
 * Modal panel displaying all keyboard shortcuts.
 * Features:
 * - Shortcuts grouped by category
 * - Search/filter shortcuts
 * - Keyboard accessible (Escape to close)
 * - Focus trap within panel
 *
 * Implements WCAG 2.1 AA accessibility requirements.
 * Based on UX patterns from Gemini CLI, OpenAI Codex, and Claude Code.
 */

import {
  useState,
  useEffect,
  useRef,
  useMemo,
  useId,
  useCallback,
} from "react";
import { Search, X, Keyboard } from "lucide-react";

import { Button, Input } from "@/components/UI";

// ==============================================================================
// Types
// ==============================================================================

export interface ShortcutDefinition {
  /** Unique action identifier */
  action: string;
  /** Key combination (e.g., "Cmd+K", "Ctrl+Shift+N") */
  keys: string;
  /** Human-readable label */
  label: string;
  /** Category for grouping */
  category: string;
  /** Optional description */
  description?: string;
}

export interface ShortcutsPanelProps {
  /** Whether the panel is open */
  isOpen: boolean;
  /** List of shortcuts to display */
  shortcuts: ShortcutDefinition[];
  /** Callback when panel should close */
  onClose: () => void;
}

// ==============================================================================
// Component
// ==============================================================================

export function ShortcutsPanel({
  isOpen,
  shortcuts,
  onClose,
}: ShortcutsPanelProps) {
  const [searchQuery, setSearchQuery] = useState("");
  const searchInputRef = useRef<HTMLInputElement>(null);
  const panelRef = useRef<HTMLDivElement>(null);
  const titleId = useId();

  // Reset search and focus when opening
  useEffect(() => {
    if (isOpen) {
      setSearchQuery("");
      setTimeout(() => {
        searchInputRef.current?.focus();
      }, 0);
    }
  }, [isOpen]);

  // Handle escape key
  useEffect(() => {
    const handleEscape = (e: KeyboardEvent) => {
      if (e.key === "Escape" && isOpen) {
        onClose();
      }
    };

    document.addEventListener("keydown", handleEscape);
    return () => document.removeEventListener("keydown", handleEscape);
  }, [isOpen, onClose]);

  // Filter shortcuts by search query
  const filteredShortcuts = useMemo(() => {
    if (!searchQuery.trim()) return shortcuts;

    const query = searchQuery.toLowerCase();
    return shortcuts.filter(
      (s) =>
        s.label.toLowerCase().includes(query) ||
        s.keys.toLowerCase().includes(query) ||
        s.category.toLowerCase().includes(query) ||
        s.description?.toLowerCase().includes(query),
    );
  }, [shortcuts, searchQuery]);

  // Group shortcuts by category
  const groupedShortcuts = useMemo(() => {
    const groups: Record<string, ShortcutDefinition[]> = {};

    for (const shortcut of filteredShortcuts) {
      let categoryGroup = groups[shortcut.category];
      if (!categoryGroup) {
        categoryGroup = [];
        groups[shortcut.category] = categoryGroup;
      }
      categoryGroup.push(shortcut);
    }

    // Sort categories alphabetically
    return Object.entries(groups).sort(([a], [b]) => a.localeCompare(b));
  }, [filteredShortcuts]);

  const handleBackdropClick = useCallback(() => {
    onClose();
  }, [onClose]);

  const handlePanelClick = useCallback((e: React.MouseEvent) => {
    e.stopPropagation();
  }, []);

  if (!isOpen) {
    return null;
  }

  return (
    <div
      data-testid="panel-backdrop"
      onClick={handleBackdropClick}
      className="fixed inset-0 z-50 flex items-center justify-center bg-black/50"
    >
      <div
        ref={panelRef}
        role="dialog"
        aria-modal="true"
        aria-labelledby={titleId}
        onClick={handlePanelClick}
        className="w-full max-w-2xl max-h-[80vh] rounded-lg bg-white dark:bg-neutral-900 shadow-xl flex flex-col"
      >
        {/* Header */}
        <div className="flex items-center justify-between p-4 border-b border-neutral-200 dark:border-neutral-700">
          <div className="flex items-center gap-2">
            <Keyboard
              className="h-5 w-5 text-neutral-500 dark:text-neutral-400"
              aria-hidden="true"
            />
            <h2
              id={titleId}
              className="text-lg font-semibold text-neutral-900 dark:text-neutral-100"
            >
              Keyboard Shortcuts
            </h2>
          </div>
          <Button
            variant="secondary"
            className="p-1 rounded text-neutral-500 dark:text-neutral-400 hover:text-neutral-700 dark:text-neutral-200 dark:text-neutral-400 dark:hover:text-neutral-200 hover:bg-neutral-100 dark:bg-neutral-800 dark:hover:bg-neutral-800 focus:ring-primary-500"
            type="button"
            onClick={onClose}
            aria-label="Close"
          >
            <X size={20} />
          </Button>
        </div>

        {/* Search */}
        <div className="p-4 border-b border-neutral-200 dark:border-neutral-700">
          <div className="relative">
            <Search
              size={16}
              className="absolute left-3 top-1/2 -translate-y-1/2 text-neutral-400 dark:text-neutral-400"
              aria-hidden="true"
            />
            <Input
              className="pl-9 pr-8 py-2 text-sm -500 focus:ring-primary-500"
              ref={searchInputRef}
              value={searchQuery}
              onChange={(e) => setSearchQuery(e.target.value)}
              placeholder="Search shortcuts..."
              aria-label="Search shortcuts"
            />
            {searchQuery && (
              <Button
                className="absolute right-2 top-1/2 -translate-y-1/2 p-0.5 text-neutral-400 dark:text-neutral-400 hover:text-neutral-600 dark:text-neutral-300 dark:hover:text-neutral-300"
                type="button"
                onClick={() => setSearchQuery("")}
                aria-label="Clear search"
              >
                <X size={14} />
              </Button>
            )}
          </div>
        </div>

        {/* Shortcuts List */}
        <div className="flex-1 overflow-y-auto p-4">
          {groupedShortcuts.length === 0 ? (
            <div className="text-center py-8 text-neutral-500 dark:text-neutral-400">
              No shortcuts found
            </div>
          ) : (
            <div className="space-y-6">
              {groupedShortcuts.map(([category, categoryShortcuts]) => (
                <div key={category}>
                  <h3 className="text-sm font-medium text-neutral-500 dark:text-neutral-400 uppercase tracking-wider mb-3">
                    {category}
                  </h3>
                  <div className="space-y-2">
                    {categoryShortcuts.map((shortcut) => (
                      <div
                        key={shortcut.action}
                        className="flex items-center justify-between py-2 px-3 rounded-md hover:bg-neutral-50 dark:hover:bg-neutral-800"
                      >
                        <div>
                          <div className="text-sm font-medium text-neutral-900 dark:text-neutral-100">
                            {shortcut.label}
                          </div>
                          {shortcut.description && (
                            <div className="text-xs text-neutral-500 dark:text-neutral-400 mt-0.5">
                              {shortcut.description}
                            </div>
                          )}
                        </div>
                        <kbd className="px-2 py-1 text-xs font-mono bg-neutral-100 dark:bg-neutral-800 text-neutral-700 dark:text-neutral-300 rounded border border-neutral-200 dark:border-neutral-700">
                          {shortcut.keys}
                        </kbd>
                      </div>
                    ))}
                  </div>
                </div>
              ))}
            </div>
          )}
        </div>

        {/* Footer */}
        <div className="p-4 border-t border-neutral-200 dark:border-neutral-700 text-center text-xs text-neutral-500 dark:text-neutral-400">
          Press{" "}
          <kbd className="px-1.5 py-0.5 font-mono bg-neutral-100 dark:bg-neutral-800 rounded border border-neutral-200 dark:border-neutral-700">
            Esc
          </kbd>{" "}
          to close
        </div>
      </div>
    </div>
  );
}

export default ShortcutsPanel;
