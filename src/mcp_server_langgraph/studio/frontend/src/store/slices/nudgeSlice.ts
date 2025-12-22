/**
 * Nudge Slice
 *
 * Manages nudge state for contextual hints and feature discovery.
 * Implements queue management, history tracking, and session limits.
 *
 * Features:
 * - Active nudge management
 * - Priority-sorted queue
 * - History tracking (shown/dismissed/accepted)
 * - Session nudge limits
 * - Sound notification option
 */

import { createSlice, createSelector, PayloadAction } from "@reduxjs/toolkit";
import type { NudgeType, NudgePriority } from "../../hooks/useNudges";

// =============================================================================
// Types
// =============================================================================

/**
 * Nudge data stored in Redux state
 */
export interface StoredNudge {
  id: string;
  type: NudgeType;
  message: string;
  priority: NudgePriority;
  category: string;
  targetElement?: string;
  showAfterMs?: number;
}

/**
 * History entry for tracking nudge interactions
 */
export interface NudgeHistoryEntry {
  id: string;
  action: "shown" | "dismissed" | "accepted";
  timestamp: number;
}

/**
 * Nudge slice state
 */
export interface NudgeState {
  /** Currently displayed nudge */
  activeNudge: StoredNudge | null;
  /** Queue of pending nudges (sorted by priority) */
  queue: StoredNudge[];
  /** History of nudge interactions */
  history: NudgeHistoryEntry[];
  /** Number of nudges shown this session */
  sessionNudgeCount: number;
  /** Maximum nudges allowed per session */
  sessionLimit: number;
  /** Whether to play sound when nudge appears */
  soundEnabled: boolean;
}

// =============================================================================
// Constants
// =============================================================================

const PRIORITY_ORDER: Record<NudgePriority, number> = {
  high: 0,
  medium: 1,
  low: 2,
};

const MAX_HISTORY_SIZE = 100;

// =============================================================================
// Initial State
// =============================================================================

export const initialState: NudgeState = {
  activeNudge: null,
  queue: [],
  history: [],
  sessionNudgeCount: 0,
  sessionLimit: 5,
  soundEnabled: false,
};

// =============================================================================
// Slice
// =============================================================================

export const nudgeSlice = createSlice({
  name: "nudge",
  initialState,
  reducers: {
    /**
     * Set the active nudge to display
     */
    setActiveNudge: (state, action: PayloadAction<StoredNudge | null>) => {
      state.activeNudge = action.payload;
      if (action.payload !== null) {
        state.sessionNudgeCount += 1;
      }
    },

    /**
     * Dismiss the specified nudge
     */
    dismissNudge: (state, action: PayloadAction<string>) => {
      const nudgeId = action.payload;

      if (state.activeNudge?.id === nudgeId) {
        state.activeNudge = null;
      }

      // Add to history
      state.history.push({
        id: nudgeId,
        action: "dismissed",
        timestamp: Date.now(),
      });

      // Trim history if too large
      if (state.history.length > MAX_HISTORY_SIZE) {
        state.history = state.history.slice(-MAX_HISTORY_SIZE);
      }
    },

    /**
     * Accept/acknowledge the specified nudge
     */
    acceptNudge: (state, action: PayloadAction<string>) => {
      const nudgeId = action.payload;

      if (state.activeNudge?.id === nudgeId) {
        state.activeNudge = null;
      }

      // Add to history
      state.history.push({
        id: nudgeId,
        action: "accepted",
        timestamp: Date.now(),
      });

      // Trim history if too large
      if (state.history.length > MAX_HISTORY_SIZE) {
        state.history = state.history.slice(-MAX_HISTORY_SIZE);
      }
    },

    /**
     * Queue a nudge for later display
     */
    queueNudge: (state, action: PayloadAction<StoredNudge>) => {
      const nudge = action.payload;

      // Check if already in queue
      if (state.queue.some((n) => n.id === nudge.id)) {
        return;
      }

      // Check if already shown in session
      if (state.history.some((h) => h.id === nudge.id)) {
        return;
      }

      // Add to queue
      state.queue.push(nudge);

      // Sort by priority (high first)
      state.queue.sort(
        (a, b) => PRIORITY_ORDER[a.priority] - PRIORITY_ORDER[b.priority]
      );
    },

    /**
     * Process the next nudge from the queue
     */
    processNextNudge: (state) => {
      // Don't process if there's already an active nudge
      if (state.activeNudge !== null) {
        return;
      }

      // Don't process if session limit reached
      if (state.sessionNudgeCount >= state.sessionLimit) {
        return;
      }

      // Don't process if queue is empty
      if (state.queue.length === 0) {
        return;
      }

      // Take the first nudge from the queue
      const nextNudge = state.queue.shift();
      if (nextNudge) {
        state.activeNudge = nextNudge;
        state.sessionNudgeCount += 1;
      }
    },

    /**
     * Clear all queued nudges
     */
    clearNudgeQueue: (state) => {
      state.queue = [];
    },

    /**
     * Reset to initial state
     */
    resetNudgeState: () => initialState,

    /**
     * Set session nudge limit
     */
    setSessionLimit: (state, action: PayloadAction<number>) => {
      state.sessionLimit = Math.max(1, action.payload);
    },

    /**
     * Enable/disable sound notifications
     */
    setSoundEnabled: (state, action: PayloadAction<boolean>) => {
      state.soundEnabled = action.payload;
    },
  },
});

// =============================================================================
// Actions
// =============================================================================

export const {
  setActiveNudge,
  dismissNudge,
  acceptNudge,
  queueNudge,
  processNextNudge,
  clearNudgeQueue,
  resetNudgeState,
  setSessionLimit,
  setSoundEnabled,
} = nudgeSlice.actions;

// =============================================================================
// Selectors
// =============================================================================

type NudgeRootState = { nudge: NudgeState };

/**
 * Select the currently active nudge
 */
export const selectActiveNudge = (state: NudgeRootState) =>
  state.nudge.activeNudge;

/**
 * Select the nudge queue
 */
export const selectNudgeQueue = (state: NudgeRootState) => state.nudge.queue;

/**
 * Select nudge history
 */
export const selectNudgeHistory = (state: NudgeRootState) =>
  state.nudge.history;

/**
 * Select session nudge count
 */
export const selectSessionNudgeCount = (state: NudgeRootState) =>
  state.nudge.sessionNudgeCount;

/**
 * Check if a specific nudge has been shown
 */
export const selectHasShownNudge =
  (nudgeId: string) => (state: NudgeRootState) =>
    state.nudge.history.some((h) => h.id === nudgeId);

/**
 * Check if more nudges can be shown this session
 */
export const selectCanShowMoreNudges = (state: NudgeRootState) =>
  state.nudge.sessionNudgeCount < state.nudge.sessionLimit;

/**
 * Select sound enabled state
 */
export const selectSoundEnabled = (state: NudgeRootState) =>
  state.nudge.soundEnabled;

/**
 * Nudge statistics
 */
export interface NudgeStats {
  totalShown: number;
  accepted: number;
  dismissed: number;
  acceptanceRate: number;
  sessionNudgeCount: number;
  canShowMore: boolean;
}

/**
 * Select comprehensive nudge stats (memoized)
 */
export const selectNudgeStats = createSelector(
  [selectNudgeHistory, selectSessionNudgeCount, selectCanShowMoreNudges],
  (history, sessionNudgeCount, canShowMore): NudgeStats => {
    const accepted = history.filter((h) => h.action === "accepted").length;
    const dismissed = history.filter((h) => h.action === "dismissed").length;
    const totalShown = accepted + dismissed;

    return {
      totalShown,
      accepted,
      dismissed,
      acceptanceRate: totalShown > 0 ? accepted / totalShown : 0,
      sessionNudgeCount,
      canShowMore,
    };
  }
);

export default nudgeSlice.reducer;
