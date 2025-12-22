/**
 * SlashCommandMenu - Phase 2
 *
 * Command menu for slash commands with filtering,
 * keyboard navigation, and accessibility.
 */
import { useRef, useEffect, useMemo } from "react";
import {
  HelpCircle,
  Trash2,
  Download,
  Settings,
  type LucideIcon,
} from "lucide-react";
import { cn } from "../utils/cn";

// =============================================================================
// Types
// =============================================================================

export interface SlashCommand {
  id: string;
  name: string;
  description: string;
  icon?: string;
}

export interface SlashCommandMenuProps {
  commands: SlashCommand[];
  isOpen: boolean;
  query?: string;
  selectedIndex?: number;
  onSelect: (command: SlashCommand) => void;
  onClose: () => void;
  onKeyDown?: (event: React.KeyboardEvent) => void;
  className?: string;
}

// =============================================================================
// Utility
// =============================================================================

// Icon mapping
const iconMap: Record<string, LucideIcon> = {
  "help-circle": HelpCircle,
  trash: Trash2,
  download: Download,
  settings: Settings,
};

function getIcon(iconName?: string): LucideIcon | null {
  if (!iconName) return null;
  return iconMap[iconName] || null;
}

// =============================================================================
// Component
// =============================================================================

export function SlashCommandMenu({
  commands,
  isOpen,
  query = "",
  selectedIndex = 0,
  onSelect,
  onClose,
  onKeyDown,
  className,
}: SlashCommandMenuProps) {
  const menuRef = useRef<HTMLDivElement>(null);

  // Filter commands based on query
  const filteredCommands = useMemo(() => {
    if (!query) return commands;
    const lowerQuery = query.toLowerCase();
    return commands.filter(
      (cmd) =>
        cmd.name.toLowerCase().includes(lowerQuery) ||
        cmd.description.toLowerCase().includes(lowerQuery),
    );
  }, [commands, query]);

  // Handle click outside
  useEffect(() => {
    if (!isOpen) return;

    const handleMouseDown = (e: MouseEvent) => {
      if (menuRef.current && !menuRef.current.contains(e.target as Node)) {
        onClose();
      }
    };

    document.addEventListener("mousedown", handleMouseDown);
    return () => document.removeEventListener("mousedown", handleMouseDown);
  }, [isOpen, onClose]);

  // Handle keyboard events
  const handleKeyDown = (e: React.KeyboardEvent) => {
    if (e.key === "Escape") {
      onClose();
    }
    onKeyDown?.(e);
  };

  if (!isOpen) return null;

  // Generate unique ID for active descendant
  const activeDescendantId =
    filteredCommands.length > 0
      ? `slash-cmd-${filteredCommands[selectedIndex]?.id || "none"}`
      : undefined;

  return (
    <div
      data-testid="slash-command-menu"
      ref={menuRef}
      role="listbox"
      aria-label="Slash commands"
      aria-activedescendant={activeDescendantId}
      tabIndex={0}
      onKeyDown={handleKeyDown}
      className={cn(
        "absolute bottom-full left-0 mb-2 w-80",
        "bg-white dark:bg-gray-800",
        "border border-gray-200 dark:border-gray-700",
        "rounded-lg shadow-lg",
        "max-h-80 overflow-y-auto",
        "py-2",
        className,
      )}
    >
      {filteredCommands.length === 0 ? (
        <div
          role="option"
          aria-disabled="true"
          className="p-4 text-center text-gray-500 dark:text-gray-400"
        >
          No commands found
        </div>
      ) : (
        filteredCommands.map((command, index) => {
          const Icon = getIcon(command.icon);
          const isSelected = index === selectedIndex;

          return (
            <div
              key={command.id}
              id={`slash-cmd-${command.id}`}
              data-testid="command-item"
              role="option"
              aria-selected={isSelected}
              onClick={() => onSelect(command)}
              className={cn(
                "flex items-center gap-3 px-4 py-2 cursor-pointer",
                "hover:bg-gray-100 dark:hover:bg-gray-700",
                isSelected && "selected bg-gray-100 dark:bg-gray-700",
              )}
            >
              {Icon && (
                <Icon
                  size={16}
                  className="text-gray-500 dark:text-gray-400"
                />
              )}
              <div className="flex-1 min-w-0">
                <div className="text-sm font-medium text-gray-900 dark:text-gray-100">
                  /{command.name}
                </div>
                <div className="text-xs text-gray-500 dark:text-gray-400 truncate">
                  {command.description}
                </div>
              </div>
            </div>
          );
        })
      )}
    </div>
  );
}
