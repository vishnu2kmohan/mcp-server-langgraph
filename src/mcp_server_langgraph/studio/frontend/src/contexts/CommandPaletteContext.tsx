/**
 * CommandPaletteContext
 *
 * React context for dynamic command palette management.
 * Provides command registration/unregistration for route-aware commands
 * with deduplication support.
 *
 * Features:
 * - Static commands provided at initialization
 * - Dynamic command registration/unregistration
 * - Deduplication by ID (dynamic overrides static)
 * - Memoized merged command list
 *
 * Sprint 4: CommandPalette Enhancement
 * Reference: Plan Part 3 - AICommandPalette Enhancements
 */

import {
  createContext,
  useContext,
  useCallback,
  useState,
  useMemo,
  type ReactNode,
} from "react";
import type { Command } from "../ai/AICommandPalette";

// ==============================================================================
// Types
// ==============================================================================

interface CommandPaletteContextValue {
  /** Merged list of static and dynamic commands (deduped by id) */
  commands: Command[];
  /** Register new commands (dynamic) */
  registerCommands: (commands: Command[]) => void;
  /** Unregister commands by their IDs */
  unregisterCommands: (ids: string[]) => void;
}

interface CommandPaletteProviderProps {
  /** Static commands provided at initialization */
  staticCommands: Command[];
  /** React children */
  children: ReactNode;
}

// ==============================================================================
// Context
// ==============================================================================

const CommandPaletteContext = createContext<CommandPaletteContextValue | null>(
  null,
);

// ==============================================================================
// Provider
// ==============================================================================

export function CommandPaletteProvider({
  staticCommands,
  children,
}: CommandPaletteProviderProps) {
  // Dynamic commands state
  const [dynamicCommands, setDynamicCommands] = useState<Command[]>([]);

  // Merge static and dynamic commands with deduplication
  // Dynamic commands override static commands with the same ID
  const commands = useMemo(() => {
    const commandMap = new Map<string, Command>();

    // Add static commands first
    staticCommands.forEach((cmd) => commandMap.set(cmd.id, cmd));

    // Dynamic commands override static
    dynamicCommands.forEach((cmd) => commandMap.set(cmd.id, cmd));

    return Array.from(commandMap.values());
  }, [staticCommands, dynamicCommands]);

  // Register new commands (add or replace existing by ID)
  const registerCommands = useCallback((newCommands: Command[]) => {
    setDynamicCommands((prev) => {
      // Get IDs of new commands
      const newIds = new Set(newCommands.map((c) => c.id));

      // Filter out existing commands with same IDs
      const filtered = prev.filter((c) => !newIds.has(c.id));

      // Add new commands
      return [...filtered, ...newCommands];
    });
  }, []);

  // Unregister commands by their IDs
  const unregisterCommands = useCallback((ids: string[]) => {
    const idSet = new Set(ids);
    setDynamicCommands((prev) => prev.filter((c) => !idSet.has(c.id)));
  }, []);

  // Context value (stable reference via useMemo)
  const value = useMemo<CommandPaletteContextValue>(
    () => ({
      commands,
      registerCommands,
      unregisterCommands,
    }),
    [commands, registerCommands, unregisterCommands],
  );

  return (
    <CommandPaletteContext.Provider value={value}>
      {children}
    </CommandPaletteContext.Provider>
  );
}

// ==============================================================================
// Hook
// ==============================================================================

// Co-locating hook with provider is standard React pattern
// eslint-disable-next-line react-refresh/only-export-components
export function useCommandPalette(): CommandPaletteContextValue {
  const context = useContext(CommandPaletteContext);
  if (!context) {
    throw new Error(
      "useCommandPalette must be used within CommandPaletteProvider",
    );
  }
  return context;
}
