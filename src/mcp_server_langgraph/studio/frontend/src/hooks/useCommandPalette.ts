/**
 * useCommandPalette Hook
 *
 * Hook to manage command palette state and functionality.
 * Features:
 * - Command registration and management
 * - Fuzzy search filtering
 * - Recent commands tracking
 * - Keyboard navigation
 * - Category grouping
 *
 * Based on IDE command palette patterns.
 */

import { useState, useCallback, useMemo, useEffect } from "react";

// ==============================================================================
// Types
// ==============================================================================

export interface Command {
  /** Unique identifier */
  id: string;
  /** Display label */
  label: string;
  /** Category for grouping */
  category: string;
  /** Action to execute */
  action: () => void;
  /** Keyboard shortcut (display only) */
  shortcut?: string;
  /** Icon name or component */
  icon?: string;
  /** Whether command is disabled */
  disabled?: boolean;
}

export interface CommandPaletteState {
  /** Whether palette is open */
  isOpen: boolean;
  /** Current search query */
  query: string;
  /** Filtered commands based on query */
  filteredCommands: Command[];
  /** Commands grouped by category */
  commandsByCategory: Record<string, Command[]>;
  /** Recent command IDs */
  recentCommands: string[];
  /** Currently selected index */
  selectedIndex: number;
  /** Open the palette */
  open: () => void;
  /** Close the palette */
  close: () => void;
  /** Toggle the palette */
  toggle: () => void;
  /** Set search query */
  setQuery: (query: string) => void;
  /** Clear search query */
  clearQuery: () => void;
  /** Execute a command by ID */
  executeCommand: (id: string) => void;
  /** Move selection to next item */
  selectNext: () => void;
  /** Move selection to previous item */
  selectPrevious: () => void;
  /** Execute the currently selected command */
  executeSelected: () => void;
}

// ==============================================================================
// Constants
// ==============================================================================

const RECENT_COMMANDS_KEY = "command-palette-recent";
const MAX_RECENT_COMMANDS = 5;

// ==============================================================================
// Helper Functions
// ==============================================================================

function loadRecentCommands(): string[] {
  try {
    const stored = localStorage.getItem(RECENT_COMMANDS_KEY);
    return stored ? JSON.parse(stored) : [];
  } catch {
    return [];
  }
}

function saveRecentCommands(commands: string[]): void {
  try {
    localStorage.setItem(RECENT_COMMANDS_KEY, JSON.stringify(commands));
  } catch {
    // localStorage unavailable
  }
}

/**
 * Simple fuzzy search implementation
 * Returns true if all characters in query appear in target in order
 */
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
// Hook
// ==============================================================================

export function useCommandPalette(commands: Command[]): CommandPaletteState {
  const [isOpen, setIsOpen] = useState(false);
  const [query, setQuery] = useState("");
  const [selectedIndex, setSelectedIndex] = useState(0);
  const [recentCommands, setRecentCommands] =
    useState<string[]>(loadRecentCommands);

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

    commands.forEach((cmd) => {
      if (!grouped[cmd.category]) {
        grouped[cmd.category] = [];
      }
      grouped[cmd.category].push(cmd);
    });

    return grouped;
  }, [commands]);

  // Reset selection when query changes
  useEffect(() => {
    setSelectedIndex(0);
  }, [query]);

  // Open/close handlers
  const open = useCallback(() => {
    setIsOpen(true);
    setQuery("");
    setSelectedIndex(0);
  }, []);

  const close = useCallback(() => {
    setIsOpen(false);
    setQuery("");
    setSelectedIndex(0);
  }, []);

  const toggle = useCallback(() => {
    if (isOpen) {
      close();
    } else {
      open();
    }
  }, [isOpen, open, close]);

  // Query handlers
  const clearQuery = useCallback(() => {
    setQuery("");
  }, []);

  // Execute command
  const executeCommand = useCallback(
    (id: string) => {
      const command = commands.find((cmd) => cmd.id === id);
      if (command && !command.disabled) {
        command.action();

        // Update recent commands
        setRecentCommands((prev) => {
          const filtered = prev.filter((cmdId) => cmdId !== id);
          const updated = [id, ...filtered].slice(0, MAX_RECENT_COMMANDS);
          saveRecentCommands(updated);
          return updated;
        });

        close();
      }
    },
    [commands, close],
  );

  // Navigation handlers
  const selectNext = useCallback(() => {
    setSelectedIndex((prev) => (prev + 1) % filteredCommands.length);
  }, [filteredCommands.length]);

  const selectPrevious = useCallback(() => {
    setSelectedIndex((prev) =>
      prev <= 0 ? filteredCommands.length - 1 : prev - 1,
    );
  }, [filteredCommands.length]);

  const executeSelected = useCallback(() => {
    const command = filteredCommands[selectedIndex];
    if (command) {
      executeCommand(command.id);
    }
  }, [filteredCommands, selectedIndex, executeCommand]);

  return {
    isOpen,
    query,
    filteredCommands,
    commandsByCategory,
    recentCommands,
    selectedIndex,
    open,
    close,
    toggle,
    setQuery,
    clearQuery,
    executeCommand,
    selectNext,
    selectPrevious,
    executeSelected,
  };
}

export default useCommandPalette;
