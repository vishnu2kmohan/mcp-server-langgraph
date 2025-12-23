/**
 * useConsoleEntries Hook
 *
 * Manages console entries for the DevTools Console tab.
 * Handles adding, filtering, and clearing log entries.
 */
import { useState, useCallback, useMemo } from "react";

import type { ConsoleEntry, ConsoleLogLevel, ConsoleFilterLevel } from "../types";

// =============================================================================
// Types
// =============================================================================

export interface UseConsoleEntriesOptions {
  /** Maximum number of entries to keep */
  maxEntries?: number;
  /** Filter level */
  filter?: ConsoleFilterLevel;
  /** Context entity ID for filtering */
  contextEntityId?: string | null;
}

export interface ConsoleEntryCounts {
  info: number;
  warning: number;
  error: number;
  debug: number;
  total: number;
}

export interface UseConsoleEntriesReturn {
  /** All entries (unfiltered) */
  entries: ConsoleEntry[];
  /** Filtered entries based on options */
  filteredEntries: ConsoleEntry[];
  /** Whether entries are loading */
  isLoading: boolean;
  /** Add a new entry */
  addEntry: (entry: ConsoleEntry) => void;
  /** Clear all entries */
  clearConsole: () => void;
  /** Counts by level */
  counts: ConsoleEntryCounts;
}

// =============================================================================
// Constants
// =============================================================================

const DEFAULT_MAX_ENTRIES = 1000;

// =============================================================================
// Hook Implementation
// =============================================================================

export function useConsoleEntries(
  options: UseConsoleEntriesOptions = {}
): UseConsoleEntriesReturn {
  const {
    maxEntries = DEFAULT_MAX_ENTRIES,
    filter = "all",
    contextEntityId,
  } = options;

  const [entries, setEntries] = useState<ConsoleEntry[]>([]);
  const [isLoading] = useState(false);

  /**
   * Add a new entry to the console.
   */
  const addEntry = useCallback(
    (entry: ConsoleEntry) => {
      setEntries((prev) => {
        const newEntries = [...prev, entry];
        // Trim to max entries, keeping newest
        if (newEntries.length > maxEntries) {
          return newEntries.slice(-maxEntries);
        }
        return newEntries;
      });
    },
    [maxEntries]
  );

  /**
   * Clear all entries.
   */
  const clearConsole = useCallback(() => {
    setEntries([]);
  }, []);

  /**
   * Filter entries based on level and context.
   */
  const filteredEntries = useMemo(() => {
    let result = entries;

    // Filter by level
    if (filter !== "all") {
      result = result.filter((entry) => entry.level === filter);
    }

    // Filter by context entity ID
    if (contextEntityId) {
      result = result.filter((entry) => {
        // Include entries that match the context or have no context (global)
        const entrySessionId = entry.data?.sessionId as string | undefined;
        const entryWorkflowId = entry.data?.workflowId as string | undefined;
        return (
          !entrySessionId && !entryWorkflowId || // Global entry
          entrySessionId === contextEntityId ||
          entryWorkflowId === contextEntityId
        );
      });
    }

    return result;
  }, [entries, filter, contextEntityId]);

  /**
   * Calculate counts by level.
   */
  const counts = useMemo((): ConsoleEntryCounts => {
    const levelCounts: Record<ConsoleLogLevel, number> = {
      info: 0,
      warning: 0,
      error: 0,
      debug: 0,
    };

    for (const entry of entries) {
      levelCounts[entry.level]++;
    }

    return {
      ...levelCounts,
      total: entries.length,
    };
  }, [entries]);

  return {
    entries,
    filteredEntries,
    isLoading,
    addEntry,
    clearConsole,
    counts,
  };
}

export default useConsoleEntries;
