/**
 * useStateHistory Hook
 *
 * Provides time-travel debugging functionality for the StateTab.
 * Records state snapshots and allows navigation through history.
 */
import { useState, useCallback, useMemo, useRef, useEffect } from "react";

// =============================================================================
// Types
// =============================================================================

export interface StateSnapshot {
  /** Unique ID for this snapshot */
  id: string;
  /** The state at this point in time */
  state: Record<string, unknown>;
  /** Timestamp when snapshot was recorded */
  timestamp: number;
  /** Optional label for this snapshot */
  label?: string;
}

export interface StateDiff {
  /** Properties that were added */
  added: string[];
  /** Properties that were removed */
  removed: string[];
  /** Properties that were changed */
  changed: string[];
}

export interface UseStateHistoryOptions {
  /** Initial state to record */
  initialState?: Record<string, unknown>;
  /** Maximum number of snapshots to keep */
  maxSnapshots?: number;
  /** Playback interval in milliseconds */
  playbackInterval?: number;
  /** Callback when current snapshot changes */
  onSnapshotChange?: (snapshot: StateSnapshot, index: number) => void;
  /** Callback when navigation occurs */
  onNavigate?: (newIndex: number, previousIndex: number) => void;
}

export interface UseStateHistoryReturn {
  /** All recorded snapshots */
  snapshots: StateSnapshot[];
  /** Current snapshot index */
  currentIndex: number;
  /** Current snapshot (or null if none) */
  currentSnapshot: StateSnapshot | null;
  /** Whether at the latest snapshot */
  isAtLatest: boolean;
  /** Whether playback is active */
  isPlaying: boolean;
  /** Whether can go back */
  canGoBack: boolean;
  /** Whether can go forward */
  canGoForward: boolean;
  /** Record a new snapshot */
  recordSnapshot: (state: Record<string, unknown>, label?: string) => void;
  /** Go to previous snapshot */
  goBack: () => void;
  /** Go to next snapshot */
  goForward: () => void;
  /** Jump to specific index */
  jumpTo: (index: number) => void;
  /** Jump to latest snapshot */
  jumpToLatest: () => void;
  /** Clear all history */
  clearHistory: () => void;
  /** Start playback from beginning */
  startPlayback: () => void;
  /** Stop playback */
  stopPlayback: () => void;
  /** Get diff between current and previous snapshot */
  getDiff: () => StateDiff | null;
  /** Get diff between two specific snapshots */
  getDiffBetween: (indexA: number, indexB: number) => StateDiff | null;
  /** Get snapshots with labels */
  getSnapshotsWithLabel: () => StateSnapshot[];
  /** Get snapshots within time range */
  getSnapshotsInRange: (startTime: number, endTime: number) => StateSnapshot[];
}

// =============================================================================
// Constants
// =============================================================================

const DEFAULT_MAX_SNAPSHOTS = 100;
const DEFAULT_PLAYBACK_INTERVAL = 500;

// =============================================================================
// Helper Functions
// =============================================================================

function generateId(): string {
  return `${Date.now()}-${Math.random().toString(36).slice(2, 9)}`;
}

function calculateDiff(
  prev: Record<string, unknown>,
  curr: Record<string, unknown>,
): StateDiff {
  const prevKeys = Object.keys(prev);
  const currKeys = Object.keys(curr);

  const added: string[] = [];
  const removed: string[] = [];
  const changed: string[] = [];

  // Find added and changed
  for (const key of currKeys) {
    if (!(key in prev)) {
      added.push(key);
    } else if (JSON.stringify(prev[key]) !== JSON.stringify(curr[key])) {
      changed.push(key);
    }
  }

  // Find removed
  for (const key of prevKeys) {
    if (!(key in curr)) {
      removed.push(key);
    }
  }

  return { added, removed, changed };
}

// =============================================================================
// Hook Implementation
// =============================================================================

export function useStateHistory(
  options: UseStateHistoryOptions = {},
): UseStateHistoryReturn {
  const {
    initialState,
    maxSnapshots = DEFAULT_MAX_SNAPSHOTS,
    playbackInterval = DEFAULT_PLAYBACK_INTERVAL,
    onSnapshotChange,
    onNavigate,
  } = options;

  // Build initial snapshots array
  const initialSnapshots: StateSnapshot[] = initialState
    ? [
        {
          id: generateId(),
          state: initialState,
          timestamp: Date.now(),
        },
      ]
    : [];

  const [snapshots, setSnapshots] = useState<StateSnapshot[]>(initialSnapshots);
  const [currentIndex, setCurrentIndex] = useState<number>(
    initialState ? 0 : -1,
  );
  const [isPlaying, setIsPlaying] = useState<boolean>(false);

  // Refs for callbacks to avoid stale closures
  const onSnapshotChangeRef = useRef(onSnapshotChange);
  onSnapshotChangeRef.current = onSnapshotChange;

  const onNavigateRef = useRef(onNavigate);
  onNavigateRef.current = onNavigate;

  const playbackIntervalRef = useRef(playbackInterval);
  playbackIntervalRef.current = playbackInterval;

  /**
   * Record a new snapshot.
   */
  const recordSnapshot = useCallback(
    (state: Record<string, unknown>, label?: string) => {
      const newSnapshot: StateSnapshot = {
        id: generateId(),
        state,
        timestamp: Date.now(),
        label,
      };

      setSnapshots((prev) => {
        const updated = [...prev, newSnapshot];
        // Trim to max snapshots
        if (updated.length > maxSnapshots) {
          return updated.slice(-maxSnapshots);
        }
        return updated;
      });

      setCurrentIndex((prev) => {
        const newIndex = Math.min(prev + 1, maxSnapshots - 1);
        // Call callback
        onSnapshotChangeRef.current?.(newSnapshot, newIndex);
        return newIndex;
      });
    },
    [maxSnapshots],
  );

  /**
   * Go to previous snapshot.
   */
  const goBack = useCallback(() => {
    setCurrentIndex((prev) => {
      if (prev <= 0) return prev;
      const newIndex = prev - 1;
      onNavigateRef.current?.(newIndex, prev);
      return newIndex;
    });
  }, []);

  /**
   * Go to next snapshot.
   */
  const goForward = useCallback(() => {
    setCurrentIndex((prev) => {
      setSnapshots((snaps) => {
        if (prev >= snaps.length - 1) return snaps;
        const newIndex = prev + 1;
        onNavigateRef.current?.(newIndex, prev);
        setCurrentIndex(newIndex);
        return snaps;
      });
      return prev;
    });
  }, []);

  /**
   * Jump to specific index.
   */
  const jumpTo = useCallback((index: number) => {
    setCurrentIndex((prev) => {
      setSnapshots((snaps) => {
        if (index < 0 || index >= snaps.length) return snaps;
        onNavigateRef.current?.(index, prev);
        setCurrentIndex(index);
        return snaps;
      });
      return prev;
    });
  }, []);

  /**
   * Jump to latest snapshot.
   */
  const jumpToLatest = useCallback(() => {
    setSnapshots((snaps) => {
      if (snaps.length === 0) return snaps;
      setCurrentIndex(snaps.length - 1);
      return snaps;
    });
  }, []);

  /**
   * Clear all history.
   */
  const clearHistory = useCallback(() => {
    setSnapshots([]);
    setCurrentIndex(-1);
    setIsPlaying(false);
  }, []);

  /**
   * Start playback from beginning.
   */
  const startPlayback = useCallback(() => {
    setCurrentIndex(0);
    setIsPlaying(true);
  }, []);

  /**
   * Stop playback.
   */
  const stopPlayback = useCallback(() => {
    setIsPlaying(false);
  }, []);

  /**
   * Playback effect.
   */
  useEffect(() => {
    if (!isPlaying) return;

    const timer = setInterval(() => {
      setCurrentIndex((prev) => {
        setSnapshots((snaps) => {
          if (prev >= snaps.length - 1) {
            setIsPlaying(false);
            return snaps;
          }
          setCurrentIndex(prev + 1);
          return snaps;
        });
        return prev;
      });
    }, playbackIntervalRef.current);

    return () => clearInterval(timer);
  }, [isPlaying]);

  /**
   * Get diff between current and previous snapshot.
   */
  const getDiff = useCallback((): StateDiff | null => {
    if (currentIndex <= 0 || snapshots.length < 2) return null;

    const prevSnapshot = snapshots[currentIndex - 1];
    const currSnapshot = snapshots[currentIndex];

    if (!prevSnapshot || !currSnapshot) return null;

    return calculateDiff(prevSnapshot.state, currSnapshot.state);
  }, [currentIndex, snapshots]);

  /**
   * Get diff between two specific snapshots.
   */
  const getDiffBetween = useCallback(
    (indexA: number, indexB: number): StateDiff | null => {
      if (
        indexA < 0 ||
        indexB < 0 ||
        indexA >= snapshots.length ||
        indexB >= snapshots.length
      ) {
        return null;
      }

      const snapshotA = snapshots[indexA];
      const snapshotB = snapshots[indexB];

      return calculateDiff(snapshotA.state, snapshotB.state);
    },
    [snapshots],
  );

  /**
   * Get snapshots with labels.
   */
  const getSnapshotsWithLabel = useCallback((): StateSnapshot[] => {
    return snapshots.filter((s) => s.label);
  }, [snapshots]);

  /**
   * Get snapshots within time range.
   */
  const getSnapshotsInRange = useCallback(
    (startTime: number, endTime: number): StateSnapshot[] => {
      return snapshots.filter(
        (s) => s.timestamp >= startTime && s.timestamp <= endTime,
      );
    },
    [snapshots],
  );

  /**
   * Computed values.
   */
  const currentSnapshot = useMemo((): StateSnapshot | null => {
    if (currentIndex < 0 || currentIndex >= snapshots.length) return null;
    return snapshots[currentIndex];
  }, [snapshots, currentIndex]);

  const isAtLatest = currentIndex === snapshots.length - 1 || snapshots.length === 0;
  const canGoBack = currentIndex > 0;
  const canGoForward = currentIndex < snapshots.length - 1;

  return {
    snapshots,
    currentIndex,
    currentSnapshot,
    isAtLatest,
    isPlaying,
    canGoBack,
    canGoForward,
    recordSnapshot,
    goBack,
    goForward,
    jumpTo,
    jumpToLatest,
    clearHistory,
    startPlayback,
    stopPlayback,
    getDiff,
    getDiffBetween,
    getSnapshotsWithLabel,
    getSnapshotsInRange,
  };
}

export default useStateHistory;
