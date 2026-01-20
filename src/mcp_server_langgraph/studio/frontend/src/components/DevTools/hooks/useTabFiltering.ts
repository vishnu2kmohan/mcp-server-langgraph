/**
 * useTabFiltering Hook
 *
 * Shared hook for filtering data across all DevTools tabs.
 * Provides timeline integration, search filtering, and multi-filter support.
 *
 * Features:
 * - Debounced search across configurable fields
 * - Multi-filter support with AND logic
 * - Timeline integration for time-travel debugging
 * - Memoized results for performance
 */
import { useState, useMemo, useCallback } from "react";

import { useDebouncedValue } from "../utils/performance";
import type { TimeWindow } from "./useDevToolsTimeline";

// =============================================================================
// Types
// =============================================================================

/**
 * Timeline context interface (subset of UseDevToolsTimelineReturn)
 */
export interface TimelineContextForFiltering {
  timeWindow: TimeWindow | null;
  currentTime: number;
  isLiveMode: boolean;
}

/**
 * Options for useTabFiltering hook
 */
export interface UseTabFilteringOptions<T> {
  /** Data array to filter */
  data: T[];
  /** Timeline context for time-window filtering (null to disable) */
  timeline: TimelineContextForFiltering | null;
  /** Key in data objects containing timestamp (ISO string or epoch ms) */
  timestampKey?: keyof T;
  /** Fields to search within (if undefined, searches all string fields) */
  searchFields?: (keyof T)[];
  /** Debounce delay for search input in ms (default: 150) */
  debounceMs?: number;
}

/**
 * Return value from useTabFiltering hook
 */
export interface UseTabFilteringReturn<T> {
  /** Filtered data after applying all filters */
  filteredData: T[];
  /** Current search term (immediate) */
  searchTerm: string;
  /** Set search term */
  setSearchTerm: (term: string) => void;
  /** Debounced search term (for display/filtering) */
  debouncedSearchTerm: string;
  /** Active key-value filters */
  filters: Record<string, string>;
  /** Set a filter value (empty string removes filter) */
  setFilter: (key: string, value: string) => void;
  /** Clear all filters and search */
  clearFilters: () => void;
  /** Whether any filters or search is active */
  hasActiveFilters: boolean;
}

// =============================================================================
// Constants
// =============================================================================

const DEFAULT_DEBOUNCE_MS = 150;

// =============================================================================
// Helper Functions
// =============================================================================

/**
 * Parse timestamp to milliseconds since epoch
 */
function parseTimestamp(value: unknown): number | null {
  if (typeof value === "number") {
    return value;
  }
  if (typeof value === "string") {
    const parsed = Date.parse(value);
    return isNaN(parsed) ? null : parsed;
  }
  return null;
}

/**
 * Search a single item against the search term
 */
function matchesSearch<T>(
  item: T,
  searchTerm: string,
  searchFields: (keyof T)[] | undefined,
): boolean {
  if (!searchTerm) return true;

  const lowerSearchTerm = searchTerm.toLowerCase();

  // If searchFields specified, only search those fields
  if (searchFields && searchFields.length > 0) {
    return searchFields.some((field) => {
      const value = item[field];
      if (value === null || value === undefined) return false;
      return String(value).toLowerCase().includes(lowerSearchTerm);
    });
  }

  // Otherwise, search all string fields
  return Object.values(item as Record<string, unknown>).some((value) => {
    if (value === null || value === undefined) return false;
    if (typeof value !== "string") return false;
    return value.toLowerCase().includes(lowerSearchTerm);
  });
}

/**
 * Check if item matches all active filters
 */
function matchesFilters<T>(
  item: T,
  filters: Record<string, string>,
): boolean {
  const filterEntries = Object.entries(filters);
  if (filterEntries.length === 0) return true;

  return filterEntries.every(([key, value]) => {
    const itemValue = (item as Record<string, unknown>)[key];
    return String(itemValue) === value;
  });
}

/**
 * Check if item is within timeline time window
 */
function matchesTimeWindow<T>(
  item: T,
  timeWindow: TimeWindow | null,
  timestampKey: keyof T | undefined,
): boolean {
  if (!timeWindow) return true;
  if (!timestampKey) return true;

  const timestamp = parseTimestamp(item[timestampKey]);
  if (timestamp === null) return true; // Include items without valid timestamp

  return timestamp >= timeWindow.start && timestamp <= timeWindow.end;
}

// =============================================================================
// Hook Implementation
// =============================================================================

/**
 * Hook for filtering data in DevTools tabs.
 *
 * @example
 * ```tsx
 * const { filteredData, setSearchTerm, setFilter } = useTabFiltering({
 *   data: logs,
 *   timeline: useTimelineContext(),
 *   searchFields: ['message', 'service'],
 * });
 * ```
 */
export function useTabFiltering<T>(
  options: UseTabFilteringOptions<T>,
): UseTabFilteringReturn<T> {
  const {
    data,
    timeline,
    timestampKey,
    searchFields,
    debounceMs = DEFAULT_DEBOUNCE_MS,
  } = options;

  // ---------------------------------------------------------------------------
  // State
  // ---------------------------------------------------------------------------

  const [searchTerm, setSearchTerm] = useState("");
  const [filters, setFilters] = useState<Record<string, string>>({});

  // Debounce search term
  const debouncedSearchTerm = useDebouncedValue(searchTerm, debounceMs);

  // ---------------------------------------------------------------------------
  // Filter Management
  // ---------------------------------------------------------------------------

  const setFilter = useCallback((key: string, value: string) => {
    setFilters((prev) => {
      if (value === "" || value === null || value === undefined) {
        // Remove filter if empty value
        const { [key]: _, ...rest } = prev;
        return rest;
      }
      return { ...prev, [key]: value };
    });
  }, []);

  const clearFilters = useCallback(() => {
    setFilters({});
    setSearchTerm("");
  }, []);

  // ---------------------------------------------------------------------------
  // Computed: Has Active Filters
  // ---------------------------------------------------------------------------

  const hasActiveFilters = useMemo(() => {
    return debouncedSearchTerm !== "" || Object.keys(filters).length > 0;
  }, [debouncedSearchTerm, filters]);

  // ---------------------------------------------------------------------------
  // Computed: Filtered Data
  // ---------------------------------------------------------------------------

  const filteredData = useMemo(() => {
    // Get timeline time window if available
    const timeWindow = timeline?.timeWindow ?? null;

    return data.filter((item) => {
      // Apply time window filter
      if (!matchesTimeWindow(item, timeWindow, timestampKey)) {
        return false;
      }

      // Apply key-value filters
      if (!matchesFilters(item, filters)) {
        return false;
      }

      // Apply search filter
      if (!matchesSearch(item, debouncedSearchTerm, searchFields)) {
        return false;
      }

      return true;
    });
  }, [data, timeline?.timeWindow, timestampKey, filters, debouncedSearchTerm, searchFields]);

  // ---------------------------------------------------------------------------
  // Return
  // ---------------------------------------------------------------------------

  return {
    filteredData,
    searchTerm,
    setSearchTerm,
    debouncedSearchTerm,
    filters,
    setFilter,
    clearFilters,
    hasActiveFilters,
  };
}

export default useTabFiltering;
