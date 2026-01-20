/**
 * GenericCommandPalette Component
 *
 * Reusable command palette modal for quick actions.
 * Features:
 * - Fuzzy search
 * - Keyboard navigation
 * - Category grouping
 * - Recent commands
 * - Shortcut display
 *
 * Implements WCAG 2.1 AA accessibility requirements.
 * Based on IDE command palette patterns.
 *
 * Note: This is the generic/reusable version. For the app-specific
 * command palette with predefined commands, see Layout/CommandPalette.
 */

import { useEffect, useRef, useState, useMemo } from "react";
import { Search, Command as CommandIcon, Clock } from "lucide-react";
import { Command } from "../../hooks/useCommandPalette";

import { Input } from "@/components/UI";

// ==============================================================================
// Types
// ==============================================================================

export interface GenericCommandPaletteProps {
  /** Whether palette is open */
  isOpen: boolean;
  /** Close handler */
  onClose: () => void;
  /** Available commands */
  commands: Command[];
  /** Execute command handler */
  onExecute: (commandId: string) => void;
  /** Recent command IDs */
  recentCommandIds?: string[];
  /** Additional CSS classes */
  className?: string;
}

// ==============================================================================
// Helper Functions
// ==============================================================================

function fuzzyMatch(query: string, target: string): boolean {
  const q = query.toLowerCase();
  const t = target.toLowerCase();

  let queryIndex = 0;
  for (let i = 0; i < t.length && queryIndex < q.length; i++) {
    if (t[i] === q[queryIndex]) {
      queryIndex++;
    }
  }

  return queryIndex === q.length;
}

// ==============================================================================
// Component
// ==============================================================================

export function GenericCommandPalette({
  isOpen,
  onClose,
  commands,
  onExecute,
  recentCommandIds = [],
  className = "",
}: GenericCommandPaletteProps) {
  const [query, setQuery] = useState("");
  const [selectedIndex, setSelectedIndex] = useState(0);
  const inputRef = useRef<HTMLInputElement>(null);
  const listRef = useRef<HTMLUListElement>(null);

  // Filter commands based on query
  const filteredCommands = useMemo(() => {
    if (!query.trim()) {
      return commands;
    }

    return commands.filter(
      (cmd) =>
        fuzzyMatch(query, cmd.label) ||
        fuzzyMatch(query, cmd.category) ||
        (cmd.shortcut && fuzzyMatch(query, cmd.shortcut)),
    );
  }, [commands, query]);

  // Group commands by category
  const commandsByCategory = useMemo(() => {
    const grouped: Record<string, Command[]> = {};

    filteredCommands.forEach((cmd) => {
      let categoryGroup = grouped[cmd.category];
      if (!categoryGroup) {
        categoryGroup = [];
        grouped[cmd.category] = categoryGroup;
      }
      categoryGroup.push(cmd);
    });

    return grouped;
  }, [filteredCommands]);

  // Get recent commands that exist in the command list
  const recentCommands = useMemo(() => {
    return recentCommandIds
      .map((id) => commands.find((cmd) => cmd.id === id))
      .filter((cmd): cmd is Command => cmd !== undefined);
  }, [recentCommandIds, commands]);

  // Reset state when opening
  useEffect(() => {
    if (isOpen) {
      setQuery("");
      setSelectedIndex(0);
      // Focus input immediately
      inputRef.current?.focus();
    }
  }, [isOpen]);

  // Reset selection when query changes
  useEffect(() => {
    setSelectedIndex(0);
  }, [query]);

  // Scroll selected item into view
  useEffect(() => {
    if (listRef.current) {
      const selectedItem = listRef.current.querySelector(
        '[aria-selected="true"]',
      );
      if (selectedItem && typeof selectedItem.scrollIntoView === "function") {
        selectedItem.scrollIntoView({ block: "nearest" });
      }
    }
  }, [selectedIndex]);

  // Keyboard handler
  const handleKeyDown = (e: React.KeyboardEvent) => {
    switch (e.key) {
      case "ArrowDown":
        e.preventDefault();
        setSelectedIndex((prev) =>
          prev < filteredCommands.length - 1 ? prev + 1 : 0,
        );
        break;
      case "ArrowUp":
        e.preventDefault();
        setSelectedIndex((prev) =>
          prev > 0 ? prev - 1 : filteredCommands.length - 1,
        );
        break;
      case "Enter":
        e.preventDefault();
        if (filteredCommands[selectedIndex]) {
          onExecute(filteredCommands[selectedIndex].id);
          onClose();
        }
        break;
      case "Escape":
        e.preventDefault();
        onClose();
        break;
    }
  };

  // Handle command click
  const handleCommandClick = (commandId: string) => {
    onExecute(commandId);
    onClose();
  };

  // Don't render if closed
  if (!isOpen) {
    return null;
  }

  // Flatten commands for index tracking
  let flatIndex = 0;

  return (
    <div
      data-testid="command-palette"
      role="dialog"
      aria-modal="true"
      aria-label="Command Palette"
      className={`fixed inset-0 z-50 flex items-start justify-center pt-[20vh] ${className}`}
      onKeyDown={handleKeyDown}
    >
      {/* Backdrop */}
      <div
        data-testid="command-palette-backdrop"
        className="absolute inset-0 bg-neutral-a6"
        onClick={onClose}
      />
      {/* Modal */}
      <div className="relative w-full max-w-lg bg-neutral-1 rounded-xl shadow-2xl overflow-hidden">
        {/* Search Input */}
        <div className="flex items-center gap-3 px-4 py-3 border-b border-neutral-5">
          <Search
            size={18}
            className="text-neutral-9"
          />
          <Input
            className="flex-1 bg-transparent text-neutral-12 placeholder-neutral-9"
            ref={inputRef}
            role="combobox"
            aria-label="Search commands"
            aria-expanded="true"
            aria-controls="command-list"
            aria-activedescendant={
              filteredCommands[selectedIndex]
                ? `command-${filteredCommands[selectedIndex].id}`
                : undefined
            }
            placeholder="Type a command or search..."
            value={query}
            onChange={(e) => setQuery(e.target.value)}
          />
          <kbd className="px-2 py-0.5 text-xs text-neutral-10 bg-neutral-2 rounded">
            ESC
          </kbd>
        </div>

        {/* Command List */}
        <ul
          ref={listRef}
          id="command-list"
          role="listbox"
          className="max-h-80 overflow-y-auto py-2"
        >
          {/* Recent Commands */}
          {!query && recentCommands.length > 0 && (
            <>
              <li className="px-4 py-1.5 text-xs font-medium text-neutral-10 flex items-center gap-2">
                <Clock size={12} />
                Recent
              </li>
              {recentCommands.map((cmd) => {
                const currentIndex = flatIndex++;
                return (
                  <li
                    key={`recent-${cmd.id}`}
                    id={`command-${cmd.id}`}
                    role="option"
                    aria-selected={selectedIndex === currentIndex}
                    onClick={() => handleCommandClick(cmd.id)}
                    className={`flex items-center justify-between px-4 py-2 cursor-pointer ${
                      selectedIndex === currentIndex
                        ? "bg-primary-1 bg-primary-4 text-primary-11 dark:text-primary-5"
                        : "hover:bg-neutral-a6"
                    }`}
                  >
                    <div className="flex items-center gap-3">
                      <CommandIcon
                        size={16}
                        className="text-neutral-9"
                      />
                      <span className="text-sm text-neutral-12">
                        {cmd.label}
                      </span>
                    </div>
                    {cmd.shortcut && (
                      <kbd className="px-2 py-0.5 text-xs text-neutral-10 bg-neutral-2 rounded">
                        {cmd.shortcut}
                      </kbd>
                    )}
                  </li>
                );
              })}
              <li className="my-2 border-t border-neutral-5" />
            </>
          )}

          {/* Commands by Category */}
          {filteredCommands.length === 0 ? (
            <li
              className="px-4 py-8 text-center text-neutral-10"
              role="option"
              aria-selected={false}
            >
              No commands found
            </li>
          ) : (
            Object.entries(commandsByCategory).flatMap(([category, cmds]) => [
              <li
                key={`cat-${category}`}
                className="px-4 py-1.5 text-xs font-medium text-neutral-10"
                role="presentation"
              >
                {category}
              </li>,
              ...cmds.map((cmd) => {
                const currentIndex = query
                  ? filteredCommands.indexOf(cmd)
                  : flatIndex++;
                return (
                  <li
                    key={cmd.id}
                    id={`command-${cmd.id}`}
                    role="option"
                    aria-selected={selectedIndex === currentIndex}
                    onClick={() => handleCommandClick(cmd.id)}
                    className={`flex items-center justify-between px-4 py-2 cursor-pointer ${
                      selectedIndex === currentIndex
                        ? "bg-primary-1 bg-primary-4 text-primary-11 dark:text-primary-5"
                        : "hover:bg-neutral-a6"
                    }`}
                  >
                    <div className="flex items-center gap-3">
                      <CommandIcon
                        size={16}
                        className="text-neutral-9"
                      />
                      <span className="text-sm text-neutral-12">
                        {cmd.label}
                      </span>
                    </div>
                    {cmd.shortcut && (
                      <kbd className="px-2 py-0.5 text-xs text-neutral-10 bg-neutral-2 rounded">
                        {cmd.shortcut}
                      </kbd>
                    )}
                  </li>
                );
              }),
            ])
          )}
        </ul>

        {/* Footer */}
        <div className="px-4 py-2 border-t border-neutral-5 text-xs text-neutral-10 flex gap-4">
          <span>
            <kbd className="px-1 py-0.5 bg-neutral-2 rounded">
              ↑↓
            </kbd>{" "}
            Navigate
          </span>
          <span>
            <kbd className="px-1 py-0.5 bg-neutral-2 rounded">
              ↵
            </kbd>{" "}
            Execute
          </span>
          <span>
            <kbd className="px-1 py-0.5 bg-neutral-2 rounded">
              ESC
            </kbd>{" "}
            Close
          </span>
        </div>
      </div>
    </div>
  );
}

export default GenericCommandPalette;
