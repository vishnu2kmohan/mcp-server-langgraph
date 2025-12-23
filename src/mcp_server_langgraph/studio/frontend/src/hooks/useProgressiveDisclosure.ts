/**
 * useProgressiveDisclosure Hook
 *
 * Manages progressive UI disclosure based on user expertise level.
 * Implements the Fogg Behavior Model by adjusting UI complexity
 * to match user ability.
 *
 * Features:
 * - 4 disclosure levels: beginner, intermediate, advanced, expert
 * - Auto-detection based on feature usage patterns
 * - Persistence to localStorage
 * - Component-level visibility control
 */

import { useCallback, useEffect, useRef } from "react";
import { useDispatch, useSelector } from "react-redux";
import {
  selectDisclosureLevel,
  selectAutoDetect,
  selectFeatureUsageCount,
  selectLevelProgress,
  setDisclosureLevel,
  setAutoDetect,
  incrementFeatureUsage,
  resetDisclosureState,
  type DisclosureLevel,
  type LevelProgress,
} from "../store/slices/disclosureSlice";
import { storage, STORAGE_KEYS } from "../utils/storage";
import { useDebouncedCallback } from "./useDebounce";

/**
 * Storage key for persisting disclosure state
 */
const STORAGE_KEY = STORAGE_KEYS.DISCLOSURE_STATE;

/**
 * Component disclosure configuration
 */
export interface DisclosureConfig {
  /** Whether the component should be visible */
  visible: boolean;
  /** Minimum level required to see this component */
  minimumLevel: DisclosureLevel;
  /** Whether to show a hint about this feature */
  showHint: boolean;
}

/**
 * Component visibility configurations by ID
 */
const COMPONENT_CONFIGS: Record<
  string,
  { minimumLevel: DisclosureLevel; hintable: boolean }
> = {
  // Beginner features - always visible
  chat: { minimumLevel: "beginner", hintable: false },
  help: { minimumLevel: "beginner", hintable: false },
  projects: { minimumLevel: "beginner", hintable: false },

  // Intermediate features
  workflows: { minimumLevel: "intermediate", hintable: true },
  traces: { minimumLevel: "intermediate", hintable: true },

  // Advanced features
  workflow_builder: { minimumLevel: "advanced", hintable: true },
  mcp: { minimumLevel: "advanced", hintable: true },
  agents: { minimumLevel: "advanced", hintable: true },

  // Expert features
  advanced_settings: { minimumLevel: "expert", hintable: true },
  custom_nodes: { minimumLevel: "expert", hintable: true },
  api_access: { minimumLevel: "expert", hintable: true },
};

/**
 * Level order for comparison
 */
const LEVEL_ORDER: Record<DisclosureLevel, number> = {
  beginner: 0,
  intermediate: 1,
  advanced: 2,
  expert: 3,
};

/**
 * Hook result interface
 */
export interface ProgressiveDisclosureResult {
  /** Current disclosure level */
  level: DisclosureLevel;
  /** Whether auto-detection is enabled */
  autoDetect: boolean;
  /** Total feature usage count */
  featureUsageCount: number;
  /** Set disclosure level manually */
  setLevel: (level: DisclosureLevel) => void;
  /** Enable/disable auto-detection */
  setAutoDetect: (enabled: boolean) => void;
  /** Track a feature use (for auto-upgrade) */
  trackFeatureUse: () => void;
  /** Check if a feature at the given level should be shown */
  shouldShow: (requiredLevel: DisclosureLevel) => boolean;
  /** Get progress toward next level */
  getLevelProgress: () => LevelProgress;
  /** Reset to initial state */
  reset: () => void;
  /** Get disclosure config for a specific component */
  getComponentConfig: (componentId: string) => DisclosureConfig;
}

/**
 * Hook for managing progressive UI disclosure.
 *
 * @example
 * ```tsx
 * const { level, shouldShow, trackFeatureUse } = useProgressiveDisclosure();
 *
 * // Show advanced features only for advanced+ users
 * {shouldShow('advanced') && <AdvancedFeature />}
 *
 * // Track feature usage for auto-upgrade
 * const handleClick = () => {
 *   trackFeatureUse();
 *   // ... do something
 * };
 * ```
 */
/** Debounce delay for localStorage sync (500ms) */
const STORAGE_SYNC_DEBOUNCE_MS = 500;

export function useProgressiveDisclosure(): ProgressiveDisclosureResult {
  const dispatch = useDispatch();
  const initialLoadDone = useRef(false);

  // Select state from Redux
  const level = useSelector(selectDisclosureLevel);
  const autoDetect = useSelector(selectAutoDetect);
  const featureUsageCount = useSelector(selectFeatureUsageCount);
  const levelProgress = useSelector(selectLevelProgress);

  /**
   * Debounced localStorage save to prevent excessive writes
   */
  const debouncedSave = useDebouncedCallback(
    (state: {
      level: DisclosureLevel;
      autoDetect: boolean;
      featureUsageCount: number;
    }) => {
      storage.set(STORAGE_KEY, state);
    },
    STORAGE_SYNC_DEBOUNCE_MS,
  );

  /**
   * Load persisted state on mount
   */
  useEffect(() => {
    const stored = storage.get<{
      level?: DisclosureLevel;
      autoDetect?: boolean;
    }>(STORAGE_KEY, { expectObject: true });
    if (stored) {
      if (stored.level) {
        dispatch(setDisclosureLevel(stored.level));
      }
      if (typeof stored.autoDetect === "boolean") {
        dispatch(setAutoDetect(stored.autoDetect));
      }
    }
    initialLoadDone.current = true;
  }, [dispatch]);

  /**
   * Persist state changes to localStorage (debounced to prevent excessive writes)
   */
  useEffect(() => {
    // Skip initial sync to avoid overwriting persisted state
    if (!initialLoadDone.current) return;

    debouncedSave({
      level,
      autoDetect,
      featureUsageCount,
    });
  }, [level, autoDetect, featureUsageCount, debouncedSave]);

  /**
   * Set disclosure level
   */
  const setLevel = useCallback(
    (newLevel: DisclosureLevel) => {
      dispatch(setDisclosureLevel(newLevel));
    },
    [dispatch],
  );

  /**
   * Enable/disable auto-detection
   */
  const setAutoDetectEnabled = useCallback(
    (enabled: boolean) => {
      dispatch(setAutoDetect(enabled));
    },
    [dispatch],
  );

  /**
   * Track feature usage
   */
  const trackFeatureUse = useCallback(() => {
    dispatch(incrementFeatureUsage());
  }, [dispatch]);

  /**
   * Check if a feature should be shown
   */
  const shouldShow = useCallback(
    (requiredLevel: DisclosureLevel): boolean => {
      return LEVEL_ORDER[level] >= LEVEL_ORDER[requiredLevel];
    },
    [level],
  );

  /**
   * Get progress toward next level
   */
  const getLevelProgress = useCallback((): LevelProgress => {
    return levelProgress;
  }, [levelProgress]);

  /**
   * Reset to initial state
   */
  const reset = useCallback(() => {
    dispatch(resetDisclosureState());
    storage.remove(STORAGE_KEY);
  }, [dispatch]);

  /**
   * Get disclosure config for a component
   */
  const getComponentConfig = useCallback(
    (componentId: string): DisclosureConfig => {
      const config = COMPONENT_CONFIGS[componentId] || {
        minimumLevel: "beginner" as DisclosureLevel,
        hintable: false,
      };

      const visible = LEVEL_ORDER[level] >= LEVEL_ORDER[config.minimumLevel];
      const showHint =
        config.hintable &&
        !visible &&
        LEVEL_ORDER[level] === LEVEL_ORDER[config.minimumLevel] - 1;

      return {
        visible,
        minimumLevel: config.minimumLevel,
        showHint,
      };
    },
    [level],
  );

  return {
    level,
    autoDetect,
    featureUsageCount,
    setLevel,
    setAutoDetect: setAutoDetectEnabled,
    trackFeatureUse,
    shouldShow,
    getLevelProgress,
    reset,
    getComponentConfig,
  };
}

export default useProgressiveDisclosure;
