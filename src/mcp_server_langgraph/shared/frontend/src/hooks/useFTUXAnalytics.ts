/**
 * useFTUXAnalytics Hook
 *
 * First-Time User Experience analytics tracking.
 * Tracks onboarding progress, feature discovery, and user engagement.
 */

import { useState, useCallback, useMemo, useEffect, useRef } from 'react';

// =============================================================================
// Types
// =============================================================================

export interface FTUXAnalyticsOptions {
  /** Total number of onboarding steps */
  totalOnboardingSteps?: number;
  /** Enable persistence to localStorage */
  persist?: boolean;
}

export interface HintAction {
  hintId: string;
  action: string;
}

export interface TourSkip {
  tourId: string;
  atStep: number;
}

export interface MetricsSummary {
  isFirstTimeUser: boolean;
  sessionDuration: number;
  onboarding: {
    started: boolean;
    completed: boolean;
    skipped: boolean;
    skipStep: string | null;
    completedSteps: string[];
    progress: number;
  };
  features: {
    discovered: string[];
    hintsShown: string[];
    hintsDismissed: string[];
    hintActions: HintAction[];
  };
  tours: {
    started: string[];
    completed: string[];
    skipped: TourSkip[];
  };
}

export interface UseFTUXAnalyticsResult {
  // Session
  isFirstTimeUser: boolean;
  sessionStartTime: number;
  getSessionDuration: () => number;

  // Onboarding
  onboardingStarted: boolean;
  onboardingCompleted: boolean;
  onboardingSkipped: boolean;
  skipStep: string | null;
  completedSteps: string[];
  onboardingProgress: number;
  trackOnboardingStart: () => void;
  trackOnboardingStep: (stepId: string, stepName: string) => void;
  trackOnboardingComplete: () => void;
  trackOnboardingSkip: (atStep: string) => void;

  // Feature Discovery
  discoveredFeatures: string[];
  hintsShown: string[];
  hintsDismissed: string[];
  hintActions: HintAction[];
  trackFeatureDiscovered: (featureId: string) => void;
  trackHintShown: (hintId: string) => void;
  trackHintDismissed: (hintId: string) => void;
  trackHintActionTaken: (hintId: string, action: string) => void;

  // Tours
  toursStarted: string[];
  toursCompleted: string[];
  toursSkipped: TourSkip[];
  trackTourStart: (tourId: string) => void;
  trackTourComplete: (tourId: string) => void;
  trackTourSkip: (tourId: string, atStep: number) => void;

  // Summary
  getMetricsSummary: () => MetricsSummary;
}

// =============================================================================
// Constants
// =============================================================================

const STORAGE_KEYS = {
  FIRST_VISIT: 'ftux_first_visit',
  ONBOARDING: 'ftux_onboarding',
  FEATURES: 'ftux_features',
  TOURS: 'ftux_tours',
};

// =============================================================================
// Helper Functions
// =============================================================================

function loadFromStorage<T>(key: string, defaultValue: T): T {
  try {
    const stored = localStorage.getItem(key);
    return stored ? JSON.parse(stored) : defaultValue;
  } catch {
    return defaultValue;
  }
}

function saveToStorage<T>(key: string, value: T): void {
  try {
    localStorage.setItem(key, JSON.stringify(value));
  } catch {
    // Ignore storage errors
  }
}

// =============================================================================
// useFTUXAnalytics Hook
// =============================================================================

export function useFTUXAnalytics(
  options: FTUXAnalyticsOptions = {}
): UseFTUXAnalyticsResult {
  const { totalOnboardingSteps = 5, persist = true } = options;

  // Session state
  const sessionStartTime = useRef(Date.now()).current;
  const [isFirstTimeUser] = useState(() => {
    const hasVisited = localStorage.getItem(STORAGE_KEYS.FIRST_VISIT);
    if (!hasVisited && persist) {
      localStorage.setItem(STORAGE_KEYS.FIRST_VISIT, 'true');
    }
    return !hasVisited;
  });

  // Onboarding state
  const [onboardingState, setOnboardingState] = useState(() =>
    loadFromStorage(STORAGE_KEYS.ONBOARDING, {
      started: false,
      completed: false,
      skipped: false,
      skipStep: null as string | null,
      completedSteps: [] as string[],
    })
  );

  // Feature discovery state
  const [featureState, setFeatureState] = useState(() =>
    loadFromStorage(STORAGE_KEYS.FEATURES, {
      discovered: [] as string[],
      hintsShown: [] as string[],
      hintsDismissed: [] as string[],
      hintActions: [] as HintAction[],
    })
  );

  // Tour state
  const [tourState, setTourState] = useState(() =>
    loadFromStorage(STORAGE_KEYS.TOURS, {
      started: [] as string[],
      completed: [] as string[],
      skipped: [] as TourSkip[],
    })
  );

  // Persist state changes
  useEffect(() => {
    if (persist) {
      saveToStorage(STORAGE_KEYS.ONBOARDING, onboardingState);
    }
  }, [onboardingState, persist]);

  useEffect(() => {
    if (persist) {
      saveToStorage(STORAGE_KEYS.FEATURES, featureState);
    }
  }, [featureState, persist]);

  useEffect(() => {
    if (persist) {
      saveToStorage(STORAGE_KEYS.TOURS, tourState);
    }
  }, [tourState, persist]);

  // Session methods
  const getSessionDuration = useCallback(() => {
    return Date.now() - sessionStartTime;
  }, [sessionStartTime]);

  // Onboarding methods
  const trackOnboardingStart = useCallback(() => {
    setOnboardingState((prev) => ({ ...prev, started: true }));
  }, []);

  const trackOnboardingStep = useCallback((stepId: string, _stepName: string) => {
    setOnboardingState((prev) => {
      if (prev.completedSteps.includes(stepId)) return prev;
      return {
        ...prev,
        completedSteps: [...prev.completedSteps, stepId],
      };
    });
  }, []);

  const trackOnboardingComplete = useCallback(() => {
    setOnboardingState((prev) => ({ ...prev, completed: true }));
  }, []);

  const trackOnboardingSkip = useCallback((atStep: string) => {
    setOnboardingState((prev) => ({
      ...prev,
      skipped: true,
      skipStep: atStep,
    }));
  }, []);

  // Feature discovery methods
  const trackFeatureDiscovered = useCallback((featureId: string) => {
    setFeatureState((prev) => {
      if (prev.discovered.includes(featureId)) return prev;
      return {
        ...prev,
        discovered: [...prev.discovered, featureId],
      };
    });
  }, []);

  const trackHintShown = useCallback((hintId: string) => {
    setFeatureState((prev) => {
      if (prev.hintsShown.includes(hintId)) return prev;
      return {
        ...prev,
        hintsShown: [...prev.hintsShown, hintId],
      };
    });
  }, []);

  const trackHintDismissed = useCallback((hintId: string) => {
    setFeatureState((prev) => {
      if (prev.hintsDismissed.includes(hintId)) return prev;
      return {
        ...prev,
        hintsDismissed: [...prev.hintsDismissed, hintId],
      };
    });
  }, []);

  const trackHintActionTaken = useCallback((hintId: string, action: string) => {
    setFeatureState((prev) => ({
      ...prev,
      hintActions: [...prev.hintActions, { hintId, action }],
    }));
  }, []);

  // Tour methods
  const trackTourStart = useCallback((tourId: string) => {
    setTourState((prev) => {
      if (prev.started.includes(tourId)) return prev;
      return {
        ...prev,
        started: [...prev.started, tourId],
      };
    });
  }, []);

  const trackTourComplete = useCallback((tourId: string) => {
    setTourState((prev) => {
      if (prev.completed.includes(tourId)) return prev;
      return {
        ...prev,
        completed: [...prev.completed, tourId],
      };
    });
  }, []);

  const trackTourSkip = useCallback((tourId: string, atStep: number) => {
    setTourState((prev) => ({
      ...prev,
      skipped: [...prev.skipped, { tourId, atStep }],
    }));
  }, []);

  // Calculate onboarding progress
  const onboardingProgress = useMemo(() => {
    if (totalOnboardingSteps === 0) return 0;
    return Math.round((onboardingState.completedSteps.length / totalOnboardingSteps) * 100);
  }, [onboardingState.completedSteps.length, totalOnboardingSteps]);

  // Metrics summary
  const getMetricsSummary = useCallback((): MetricsSummary => {
    return {
      isFirstTimeUser,
      sessionDuration: getSessionDuration(),
      onboarding: {
        started: onboardingState.started,
        completed: onboardingState.completed,
        skipped: onboardingState.skipped,
        skipStep: onboardingState.skipStep,
        completedSteps: onboardingState.completedSteps,
        progress: onboardingProgress,
      },
      features: {
        discovered: featureState.discovered,
        hintsShown: featureState.hintsShown,
        hintsDismissed: featureState.hintsDismissed,
        hintActions: featureState.hintActions,
      },
      tours: {
        started: tourState.started,
        completed: tourState.completed,
        skipped: tourState.skipped,
      },
    };
  }, [
    isFirstTimeUser,
    getSessionDuration,
    onboardingState,
    onboardingProgress,
    featureState,
    tourState,
  ]);

  return {
    // Session
    isFirstTimeUser,
    sessionStartTime,
    getSessionDuration,

    // Onboarding
    onboardingStarted: onboardingState.started,
    onboardingCompleted: onboardingState.completed,
    onboardingSkipped: onboardingState.skipped,
    skipStep: onboardingState.skipStep,
    completedSteps: onboardingState.completedSteps,
    onboardingProgress,
    trackOnboardingStart,
    trackOnboardingStep,
    trackOnboardingComplete,
    trackOnboardingSkip,

    // Feature Discovery
    discoveredFeatures: featureState.discovered,
    hintsShown: featureState.hintsShown,
    hintsDismissed: featureState.hintsDismissed,
    hintActions: featureState.hintActions,
    trackFeatureDiscovered,
    trackHintShown,
    trackHintDismissed,
    trackHintActionTaken,

    // Tours
    toursStarted: tourState.started,
    toursCompleted: tourState.completed,
    toursSkipped: tourState.skipped,
    trackTourStart,
    trackTourComplete,
    trackTourSkip,

    // Summary
    getMetricsSummary,
  };
}

// =============================================================================
// Exports
// =============================================================================

export default useFTUXAnalytics;
