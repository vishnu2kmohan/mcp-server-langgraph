/**
 * SlashCommandMenu Component
 *
 * Dropdown menu that appears when users type "/" in the chat input.
 * Provides quick access to commands like /help, /clear, /export, etc.
 *
 * Features:
 * - Command filtering based on user input
 * - Keyboard navigation (arrow keys, enter, escape)
 * - Accessible listbox pattern
 * - Icon support for visual identification
 */

import { useState, useEffect, useCallback, useMemo } from "react";
import {
  HelpCircle,
  Trash2,
  Download,
  FileText,
  Settings,
  RefreshCw,
  Copy,
  MessageSquare,
} from "lucide-react";

// =============================================================================
// Types
// =============================================================================

export type CommandIcon =
  | "help"
  | "trash"
  | "download"
  | "file-text"
  | "settings"
  | "refresh"
  | "copy"
  | "message";

export interface SlashCommand {
  /** Command name (without the slash) */
  name: string;
  /** Human-readable description */
  description: string;
  /** Icon to display */
  icon?: CommandIcon;
  /** Optional keyboard shortcut hint */
  shortcut?: string;
}

export interface SlashCommandMenuProps {
  /** Available commands */
  commands: SlashCommand[];
  /** Callback when a command is selected */
  onSelect: (command: SlashCommand) => void;
  /** Callback to close the menu */
  onClose: () => void;
  /** Whether the menu is open */
  isOpen: boolean;
  /** Filter string to match commands */
  filter?: string;
  /** Currently selected index (for external control) */
  selectedIndex?: number;
  /** Callback when selected index changes */
  onSelectedIndexChange?: (index: number) => void;
  /** Additional CSS classes */
  className?: string;
}

// =============================================================================
// Icon Map
// =============================================================================

const ICON_MAP: Record<CommandIcon, typeof HelpCircle> = {
  help: HelpCircle,
  trash: Trash2,
  download: Download,
  "file-text": FileText,
  settings: Settings,
  refresh: RefreshCw,
  copy: Copy,
  message: MessageSquare,
};

// =============================================================================
// Component
// =============================================================================

export function SlashCommandMenu({
  commands,
  onSelect,
  onClose,
  isOpen,
  filter = "",
  selectedIndex: externalSelectedIndex,
  onSelectedIndexChange,
  className = "",
}: SlashCommandMenuProps) {
  const [internalSelectedIndex, setInternalSelectedIndex] = useState(0);

  // Use external or internal selected index
  const selectedIndex = externalSelectedIndex ?? internalSelectedIndex;
  const setSelectedIndex = onSelectedIndexChange ?? setInternalSelectedIndex;

  // Filter commands based on filter string
  const filteredCommands = useMemo(() => {
    if (!filter) return commands;
    const lowerFilter = filter.toLowerCase();
    return commands.filter(
      (cmd) =>
        cmd.name.toLowerCase().includes(lowerFilter) ||
        cmd.description.toLowerCase().includes(lowerFilter),
    );
  }, [commands, filter]);

  // Reset selection when filter changes
  useEffect(() => {
    setSelectedIndex(0);
  }, [filter, setSelectedIndex]);

  // Handle keyboard navigation
  const handleKeyDown = useCallback(
    (e: React.KeyboardEvent) => {
      switch (e.key) {
        case "ArrowDown":
          e.preventDefault();
          setSelectedIndex(
            Math.min(selectedIndex + 1, filteredCommands.length - 1),
          );
          break;
        case "ArrowUp":
          e.preventDefault();
          setSelectedIndex(Math.max(selectedIndex - 1, 0));
          break;
        case "Enter":
          e.preventDefault();
          if (filteredCommands[selectedIndex]) {
            onSelect(filteredCommands[selectedIndex]);
            onClose();
          }
          break;
        case "Escape":
          e.preventDefault();
          onClose();
          break;
        case "Tab":
          e.preventDefault();
          onClose();
          break;
      }
    },
    [selectedIndex, filteredCommands, onSelect, onClose, setSelectedIndex],
  );

  // Handle command click
  const handleCommandClick = useCallback(
    (command: SlashCommand) => {
      onSelect(command);
      onClose();
    },
    [onSelect, onClose],
  );

  // Don't render if not open
  if (!isOpen) {
    return null;
  }

  return (
    <div
      data-testid="slash-command-menu"
      role="listbox"
      aria-label="Slash commands"
      tabIndex={0}
      onKeyDown={handleKeyDown}
      className={`
        absolute bottom-full left-0 mb-2 w-72
        bg-neutral-1
        border border-neutral-5
        rounded-lg shadow-lg
        max-h-64 overflow-y-auto
        z-dropdown
        ${className}
      `}
    >
      {filteredCommands.length === 0 ? (
        <div className="px-4 py-3 text-sm text-neutral-10">
          No commands found
        </div>
      ) : (
        <ul className="py-1">
          {filteredCommands.map((command, index) => {
            const Icon = command.icon ? ICON_MAP[command.icon] : MessageSquare;
            const isHighlighted = index === selectedIndex;

            return (
              <li
                key={command.name}
                data-testid={`command-item-${command.name}`}
                data-highlighted={isHighlighted}
                role="option"
                aria-selected={isHighlighted}
                onClick={() => handleCommandClick(command)}
                className={`
                  px-3 py-2 cursor-pointer flex items-center gap-3
                  ${
                    isHighlighted
                      ? "bg-primary-1 dark:bg-primary-a3 text-primary-11 dark:text-primary-11"
                      : "hover:bg-neutral-a6"
                  }
                `}
              >
                <Icon
                  size={16}
                  className={
                    isHighlighted ? "text-primary-9" : "text-neutral-9"
                  }
                />
                <div className="flex-1 min-w-0">
                  <div className="text-sm font-medium text-neutral-12">
                    /{command.name}
                  </div>
                  <div className="text-xs text-neutral-10 truncate">
                    {command.description}
                  </div>
                </div>
                {command.shortcut && (
                  <kbd className="text-xs px-1.5 py-0.5 bg-neutral-2 rounded text-neutral-10">
                    {command.shortcut}
                  </kbd>
                )}
              </li>
            );
          })}
        </ul>
      )}
    </div>
  );
}

export default SlashCommandMenu;
