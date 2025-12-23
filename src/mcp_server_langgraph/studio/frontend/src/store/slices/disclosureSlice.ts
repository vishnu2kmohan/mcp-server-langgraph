/**
 * Disclosure Slice
 *
 * Manages progressive disclosure state for UI complexity management.
 * Implements 4 disclosure levels based on user expertise:
 * - beginner: Basic features, simplified UI
 * - intermediate: More features unlocked
 * - advanced: Full feature access
 * - expert: All features + power user shortcuts
 */

import { createSlice, PayloadAction } from "@reduxjs/toolkit";

/**
 * Disclosure levels from least to most complex
 */
export type DisclosureLevel =
  | "beginner"
  | "intermediate"
  | "advanced"
  | "expert";

/**
 * Level ordering for comparison
 */
const LEVEL_ORDER: Record<DisclosureLevel, number> = {
  beginner: 0,
  intermediate: 1,
  advanced: 2,
  expert: 3,
};

/**
 * Thresholds for auto-upgrade (feature usage counts)
 */
const LEVEL_THRESHOLDS: Record<DisclosureLevel, number> = {
  beginner: 0,
  intermediate: 10,
  advanced: 50,
  expert: 100,
};

/**
 * Disclosure state
 */
export interface DisclosureState {
  /** Current disclosure level */
  level: DisclosureLevel;
  /** Whether to auto-detect level based on usage */
  autoDetect: boolean;
  /** Count of feature uses for auto-detection */
  featureUsageCount: number;
  /** History of recent actions for pattern detection */
  actionsHistory: string[];
  /** Timestamp of last level change */
  lastLevelChange?: number;
}

export const initialState: DisclosureState = {
  level: "beginner",
  autoDetect: true,
  featureUsageCount: 0,
  actionsHistory: [],
  lastLevelChange: undefined,
};

/**
 * Determine the appropriate level based on feature usage count
 */
function calculateLevelFromUsage(count: number): DisclosureLevel {
  if (count >= LEVEL_THRESHOLDS.expert) return "expert";
  if (count >= LEVEL_THRESHOLDS.advanced) return "advanced";
  if (count >= LEVEL_THRESHOLDS.intermediate) return "intermediate";
  return "beginner";
}

export const disclosureSlice = createSlice({
  name: "disclosure",
  initialState,
  reducers: {
    /**
     * Set disclosure level manually
     */
    setDisclosureLevel: (state, action: PayloadAction<DisclosureLevel>) => {
      state.level = action.payload;
      state.autoDetect = false; // Disable auto-detect when manually setting
      state.lastLevelChange = Date.now();
    },

    /**
     * Enable/disable auto-detection
     */
    setAutoDetect: (state, action: PayloadAction<boolean>) => {
      state.autoDetect = action.payload;
    },

    /**
     * Increment feature usage count and potentially auto-upgrade level
     */
    incrementFeatureUsage: (state) => {
      state.featureUsageCount += 1;

      // Auto-upgrade if enabled
      if (state.autoDetect) {
        const newLevel = calculateLevelFromUsage(state.featureUsageCount);
        if (LEVEL_ORDER[newLevel] > LEVEL_ORDER[state.level]) {
          state.level = newLevel;
          state.lastLevelChange = Date.now();
        }
      }
    },

    /**
     * Record an action for pattern detection
     */
    recordAction: (state, action: PayloadAction<string>) => {
      state.actionsHistory.push(action.payload);
      // Keep only last 50 actions
      if (state.actionsHistory.length > 50) {
        state.actionsHistory = state.actionsHistory.slice(-50);
      }
    },

    /**
     * Reset to initial state
     */
    resetDisclosureState: () => initialState,
  },
});

export const {
  setDisclosureLevel,
  setAutoDetect,
  incrementFeatureUsage,
  recordAction,
  resetDisclosureState,
} = disclosureSlice.actions;

// Selectors
type DisclosureRootState = { disclosure: DisclosureState };

export const selectDisclosureLevel = (state: DisclosureRootState) =>
  state.disclosure.level;

export const selectAutoDetect = (state: DisclosureRootState) =>
  state.disclosure.autoDetect;

export const selectFeatureUsageCount = (state: DisclosureRootState) =>
  state.disclosure.featureUsageCount;

/**
 * Check if a feature at the specified level should be shown
 */
export const selectShouldShowAdvancedFeature =
  (requiredLevel: DisclosureLevel) => (state: DisclosureRootState) => {
    const currentLevel = state.disclosure.level;
    return LEVEL_ORDER[currentLevel] >= LEVEL_ORDER[requiredLevel];
  };

/**
 * Level progress information
 */
export interface LevelProgress {
  currentLevel: DisclosureLevel;
  nextLevel: DisclosureLevel | null;
  progressPercent: number;
  actionsToNextLevel: number;
}

/**
 * Helper to calculate level progress (used by memoized selector)
 */
function calculateLevelProgress(
  level: DisclosureLevel,
  featureUsageCount: number,
): LevelProgress {
  const levels: DisclosureLevel[] = [
    "beginner",
    "intermediate",
    "advanced",
    "expert",
  ];
  const currentIndex = levels.indexOf(level);
  const nextLevel =
    currentIndex < levels.length - 1 ? levels[currentIndex + 1] : null;

  if (!nextLevel) {
    return {
      currentLevel: level,
      nextLevel: null,
      progressPercent: 100,
      actionsToNextLevel: 0,
    };
  }

  const currentThreshold = LEVEL_THRESHOLDS[level];
  const nextThreshold = LEVEL_THRESHOLDS[nextLevel];
  const range = nextThreshold - currentThreshold;
  const progress = featureUsageCount - currentThreshold;
  const progressPercent = Math.min(100, Math.floor((progress / range) * 100));
  const actionsToNextLevel = Math.max(0, nextThreshold - featureUsageCount);

  return {
    currentLevel: level,
    nextLevel,
    progressPercent,
    actionsToNextLevel,
  };
}

// Memoization cache for level progress
let cachedProgress: LevelProgress | null = null;
let cachedLevel: DisclosureLevel | null = null;
let cachedUsageCount: number | null = null;

/**
 * Get progress toward next level (memoized)
 */
export const selectLevelProgress = (
  state: DisclosureRootState,
): LevelProgress => {
  const { level, featureUsageCount } = state.disclosure;

  // Return cached result if inputs haven't changed
  if (
    cachedProgress !== null &&
    cachedLevel === level &&
    cachedUsageCount === featureUsageCount
  ) {
    return cachedProgress;
  }

  // Calculate and cache new result
  cachedLevel = level;
  cachedUsageCount = featureUsageCount;
  cachedProgress = calculateLevelProgress(level, featureUsageCount);

  return cachedProgress;
};

export default disclosureSlice.reducer;
