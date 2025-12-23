/**
 * useTimelinePersistence Hook
 *
 * Persists timeline state (bookmarks, playback speed, filters) to localStorage.
 * Enables session continuity across page refreshes.
 */
import { useState, useCallback, useEffect } from "react";

import { storage } from "../../../utils/storage";

// =============================================================================
// Types
// =============================================================================

export interface TimelineBookmark {
  id: string;
  time: number;
  label: string;
  color?: string;
}

export interface ActiveFilters {
  types: string[];
}

export interface PersistedTimelineState {
  bookmarks: TimelineBookmark[];
  playbackSpeed: number;
  activeFilters: ActiveFilters;
}

export interface UseTimelinePersistenceOptions {
  sessionId: string;
  enabled?: boolean;
}

export interface UseTimelinePersistenceReturn {
  state: PersistedTimelineState;
  addBookmark: (bookmark: TimelineBookmark) => void;
  removeBookmark: (id: string) => void;
  updateBookmark: (id: string, updates: Partial<TimelineBookmark>) => void;
  setPlaybackSpeed: (speed: number) => void;
  setActiveFilters: (filters: ActiveFilters) => void;
  reset: () => void;
}

// =============================================================================
// Constants
// =============================================================================

const STORAGE_KEY_PREFIX = "devtools-timeline-";

const DEFAULT_STATE: PersistedTimelineState = {
  bookmarks: [],
  playbackSpeed: 1,
  activeFilters: { types: [] },
};

// =============================================================================
// Utility Functions
// =============================================================================

function getStorageKey(sessionId: string): string {
  return `${STORAGE_KEY_PREFIX}${sessionId}`;
}

function loadFromStorage(sessionId: string): PersistedTimelineState {
  try {
    const key = getStorageKey(sessionId);
    const data = storage.get<PersistedTimelineState>(key);
    if (!data) return DEFAULT_STATE;

    return {
      bookmarks: Array.isArray(data.bookmarks) ? data.bookmarks : [],
      playbackSpeed:
        typeof data.playbackSpeed === "number" ? data.playbackSpeed : 1,
      activeFilters: data.activeFilters || { types: [] },
    };
  } catch {
    // Handle corrupted data gracefully
    return DEFAULT_STATE;
  }
}

function saveToStorage(sessionId: string, state: PersistedTimelineState): void {
  try {
    const key = getStorageKey(sessionId);
    storage.set(key, state);
  } catch {
    // Handle storage quota exceeded or other errors
    console.warn("Failed to persist timeline state to localStorage");
  }
}

function removeFromStorage(sessionId: string): void {
  try {
    const key = getStorageKey(sessionId);
    storage.remove(key);
  } catch {
    // Ignore errors during removal
  }
}

// =============================================================================
// Hook Implementation
// =============================================================================

export function useTimelinePersistence({
  sessionId,
  enabled = true,
}: UseTimelinePersistenceOptions): UseTimelinePersistenceReturn {
  // Load initial state from localStorage
  const [state, setState] = useState<PersistedTimelineState>(() =>
    loadFromStorage(sessionId),
  );

  // Persist state changes to localStorage
  useEffect(() => {
    if (enabled) {
      saveToStorage(sessionId, state);
    }
  }, [sessionId, state, enabled]);

  // Add a new bookmark
  const addBookmark = useCallback((bookmark: TimelineBookmark) => {
    setState((prev) => ({
      ...prev,
      bookmarks: [...prev.bookmarks, bookmark],
    }));
  }, []);

  // Remove a bookmark by ID
  const removeBookmark = useCallback((id: string) => {
    setState((prev) => ({
      ...prev,
      bookmarks: prev.bookmarks.filter((b) => b.id !== id),
    }));
  }, []);

  // Update a bookmark
  const updateBookmark = useCallback(
    (id: string, updates: Partial<TimelineBookmark>) => {
      setState((prev) => ({
        ...prev,
        bookmarks: prev.bookmarks.map((b) =>
          b.id === id ? { ...b, ...updates } : b,
        ),
      }));
    },
    [],
  );

  // Set playback speed
  const setPlaybackSpeed = useCallback((speed: number) => {
    setState((prev) => ({
      ...prev,
      playbackSpeed: speed,
    }));
  }, []);

  // Set active filters
  const setActiveFilters = useCallback((filters: ActiveFilters) => {
    setState((prev) => ({
      ...prev,
      activeFilters: filters,
    }));
  }, []);

  // Reset to defaults and clear storage
  const reset = useCallback(() => {
    setState(DEFAULT_STATE);
    removeFromStorage(sessionId);
  }, [sessionId]);

  return {
    state,
    addBookmark,
    removeBookmark,
    updateBookmark,
    setPlaybackSpeed,
    setActiveFilters,
    reset,
  };
}

export default useTimelinePersistence;
