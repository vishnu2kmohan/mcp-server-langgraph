/**
 * useNetworkEntries Hook
 *
 * Manages network request/response entries for DevTools Network tab.
 */
import { useState, useCallback } from "react";

import type { NetworkEntry } from "../types";

// =============================================================================
// Types
// =============================================================================

export interface UseNetworkEntriesOptions {
  /** Maximum entries to keep */
  maxEntries?: number;
  /** Context entity ID for filtering */
  contextEntityId?: string | null;
  /** Whether to include MCP calls */
  includeMCP?: boolean;
}

export interface UseNetworkEntriesReturn {
  /** Network entries */
  entries: NetworkEntry[];
  /** Whether recording is active */
  isRecording: boolean;
  /** Toggle recording on/off */
  toggleRecording: () => void;
  /** Clear all entries */
  clearEntries: () => void;
  /** Add a new entry */
  addEntry: (entry: NetworkEntry) => void;
  /** Update an existing entry */
  updateEntry: (id: string, updates: Partial<NetworkEntry>) => void;
}

const DEFAULT_MAX_ENTRIES = 500;

// =============================================================================
// Hook Implementation
// =============================================================================

export function useNetworkEntries(
  options: UseNetworkEntriesOptions = {}
): UseNetworkEntriesReturn {
  const { maxEntries = DEFAULT_MAX_ENTRIES } = options;

  const [entries, setEntries] = useState<NetworkEntry[]>([]);
  const [isRecording, setIsRecording] = useState(true);

  /**
   * Add a new network entry.
   */
  const addEntry = useCallback(
    (entry: NetworkEntry) => {
      if (!isRecording) return;

      setEntries((prev) => {
        const newEntries = [...prev, entry];
        if (newEntries.length > maxEntries) {
          return newEntries.slice(-maxEntries);
        }
        return newEntries;
      });
    },
    [isRecording, maxEntries]
  );

  /**
   * Update an existing entry (e.g., when response arrives).
   */
  const updateEntry = useCallback(
    (id: string, updates: Partial<NetworkEntry>) => {
      setEntries((prev) =>
        prev.map((entry) =>
          entry.id === id ? { ...entry, ...updates } : entry
        )
      );
    },
    []
  );

  /**
   * Toggle recording on/off.
   */
  const toggleRecording = useCallback(() => {
    setIsRecording((prev) => !prev);
  }, []);

  /**
   * Clear all entries.
   */
  const clearEntries = useCallback(() => {
    setEntries([]);
  }, []);

  return {
    entries,
    isRecording,
    toggleRecording,
    clearEntries,
    addEntry,
    updateEntry,
  };
}

export default useNetworkEntries;
