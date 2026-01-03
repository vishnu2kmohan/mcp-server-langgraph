/**
 * Unified HEART Metrics Hook
 *
 * HEART framework implementation for UX metrics:
 * - Happiness: User satisfaction (NPS, ratings)
 * - Engagement: Session duration, feature usage
 * - Adoption: New user tracking, onboarding
 * - Retention: Return visits, active days
 * - Task Success: Completion rates, error rates
 *
 * Privacy features:
 * - Respects Do Not Track setting
 * - Opt-out capability
 * - No PII collection
 *
 * @module @mcp-server-langgraph/shared-frontend/hooks
 */

import { createContext, useContext, useCallback, useState, useRef, useEffect, useMemo, type ReactNode, type ReactElement } from 'react';

// =============================================================================
// Types
// =============================================================================

export interface TaskMetrics {
  tasksStarted: number;
  tasksCompleted: number;
  errors: number;
  successRate: number;
  averageCompletionTimeMs: number;
}

export interface EngagementMetrics {
  sessionDurationMs: number;
  featureUsage: Record<string, number>;
  interactions: number;
}

export interface HappinessMetrics {
  npsScore: number | null;
  satisfactionRating: number | null;
}

export interface AdoptionMetrics {
  isNewUser: boolean;
  onboardingStepsCompleted: string[];
}

export interface RetentionMetrics {
  returnVisits: number;
  daysActive: number;
  lastActiveDate: string | null;
}

export interface HeartMetrics {
  taskSuccess: TaskMetrics;
  engagement: EngagementMetrics;
  happiness: HappinessMetrics;
  adoption: AdoptionMetrics;
  retention: RetentionMetrics;
}

export interface HeartMetricsContextValue {
  metrics: HeartMetrics;
  // Privacy
  isTrackingEnabled: boolean;
  setTrackingEnabled: (enabled: boolean) => void;
  // Task Success
  trackTaskStart: (taskName: string) => void;
  trackTaskComplete: (taskName: string) => void;
  trackTaskError: (taskName: string, error: string) => void;
  // Engagement
  trackFeatureUsed: (featureName: string) => void;
  trackInteraction: (type: string, target: string) => void;
  updateSessionDuration: () => void;
  // Happiness
  recordNPSScore: (score: number) => void;
  recordSatisfaction: (rating: number) => void;
  // Adoption
  markReturningUser: () => void;
  trackOnboardingStep: (step: string) => void;
  // Retention
  trackReturnVisit: () => void;
  trackActiveDay: () => void;
  // Utils
  exportMetrics: () => HeartMetrics;
  resetMetrics: () => void;
}

export interface HeartMetricsProviderProps {
  children: ReactNode;
  /**
   * Override initial tracking state
   */
  initialTrackingEnabled?: boolean;
}

// =============================================================================
// Constants
// =============================================================================

const STORAGE_KEY = 'heart_metrics_tracking_enabled';

const initialMetrics: HeartMetrics = {
  taskSuccess: {
    tasksStarted: 0,
    tasksCompleted: 0,
    errors: 0,
    successRate: 0,
    averageCompletionTimeMs: 0,
  },
  engagement: {
    sessionDurationMs: 0,
    featureUsage: {},
    interactions: 0,
  },
  happiness: {
    npsScore: null,
    satisfactionRating: null,
  },
  adoption: {
    isNewUser: true,
    onboardingStepsCompleted: [],
  },
  retention: {
    returnVisits: 0,
    daysActive: 0,
    lastActiveDate: null,
  },
};

// =============================================================================
// Helpers
// =============================================================================

/**
 * Check if Do Not Track is enabled
 */
function isDoNotTrackEnabled(): boolean {
  if (typeof navigator === 'undefined') return false;
  return navigator.doNotTrack === '1' || navigator.doNotTrack === 'yes';
}

/**
 * Get initial tracking state from localStorage or Do Not Track
 */
function getInitialTrackingState(): boolean {
  if (isDoNotTrackEnabled()) {
    return false;
  }

  if (typeof localStorage === 'undefined') {
    return true;
  }

  const stored = localStorage.getItem(STORAGE_KEY);
  if (stored !== null) {
    return stored === 'true';
  }

  return true;
}

// =============================================================================
// Context
// =============================================================================

const HeartMetricsContext = createContext<HeartMetricsContextValue | null>(null);

// =============================================================================
// Provider
// =============================================================================

export function HeartMetricsProvider({
  children,
  initialTrackingEnabled,
}: HeartMetricsProviderProps): ReactElement {
  const [metrics, setMetrics] = useState<HeartMetrics>(initialMetrics);
  const [isTrackingEnabled, setTrackingEnabledState] = useState<boolean>(
    initialTrackingEnabled ?? getInitialTrackingState()
  );
  const taskStartTimes = useRef<Map<string, number>>(new Map());
  const completionTimes = useRef<number[]>([]);
  const sessionStartTime = useRef<number>(Date.now());

  // Privacy - persist tracking preference
  const setTrackingEnabled = useCallback((enabled: boolean) => {
    setTrackingEnabledState(enabled);
    if (typeof localStorage !== 'undefined') {
      localStorage.setItem(STORAGE_KEY, String(enabled));
    }
  }, []);

  // Task Success
  const trackTaskStart = useCallback(
    (taskName: string) => {
      if (!isTrackingEnabled) return;

      taskStartTimes.current.set(taskName, Date.now());
      setMetrics((prev) => ({
        ...prev,
        taskSuccess: {
          ...prev.taskSuccess,
          tasksStarted: prev.taskSuccess.tasksStarted + 1,
        },
      }));
    },
    [isTrackingEnabled]
  );

  const trackTaskComplete = useCallback(
    (taskName: string) => {
      if (!isTrackingEnabled) return;

      const startTime = taskStartTimes.current.get(taskName);
      if (startTime) {
        const duration = Date.now() - startTime;
        completionTimes.current.push(duration);
        taskStartTimes.current.delete(taskName);
      }

      setMetrics((prev) => {
        const completed = prev.taskSuccess.tasksCompleted + 1;
        const total = prev.taskSuccess.tasksStarted;
        const avgTime =
          completionTimes.current.length > 0
            ? completionTimes.current.reduce((a, b) => a + b, 0) / completionTimes.current.length
            : 0;

        return {
          ...prev,
          taskSuccess: {
            ...prev.taskSuccess,
            tasksCompleted: completed,
            successRate: total > 0 ? completed / total : 0,
            averageCompletionTimeMs: avgTime,
          },
        };
      });
    },
    [isTrackingEnabled]
  );

  const trackTaskError = useCallback(
    (taskName: string, _error: string) => {
      if (!isTrackingEnabled) return;

      taskStartTimes.current.delete(taskName);

      setMetrics((prev) => {
        const errors = prev.taskSuccess.errors + 1;
        const completed = prev.taskSuccess.tasksCompleted;
        const total = prev.taskSuccess.tasksStarted;

        return {
          ...prev,
          taskSuccess: {
            ...prev.taskSuccess,
            errors,
            successRate: total > 0 ? completed / total : 0,
          },
        };
      });
    },
    [isTrackingEnabled]
  );

  // Engagement
  const trackFeatureUsed = useCallback(
    (featureName: string) => {
      if (!isTrackingEnabled) return;

      setMetrics((prev) => ({
        ...prev,
        engagement: {
          ...prev.engagement,
          featureUsage: {
            ...prev.engagement.featureUsage,
            [featureName]: (prev.engagement.featureUsage[featureName] || 0) + 1,
          },
        },
      }));
    },
    [isTrackingEnabled]
  );

  const trackInteraction = useCallback(
    (_type: string, _target: string) => {
      if (!isTrackingEnabled) return;

      setMetrics((prev) => ({
        ...prev,
        engagement: {
          ...prev.engagement,
          interactions: prev.engagement.interactions + 1,
        },
      }));
    },
    [isTrackingEnabled]
  );

  const updateSessionDuration = useCallback(() => {
    if (!isTrackingEnabled) return;

    const duration = Date.now() - sessionStartTime.current;
    setMetrics((prev) => ({
      ...prev,
      engagement: {
        ...prev.engagement,
        sessionDurationMs: duration,
      },
    }));
  }, [isTrackingEnabled]);

  // Happiness
  const recordNPSScore = useCallback(
    (score: number) => {
      if (!isTrackingEnabled) return;

      const clampedScore = Math.min(10, Math.max(0, score));
      setMetrics((prev) => ({
        ...prev,
        happiness: {
          ...prev.happiness,
          npsScore: clampedScore,
        },
      }));
    },
    [isTrackingEnabled]
  );

  const recordSatisfaction = useCallback(
    (rating: number) => {
      if (!isTrackingEnabled) return;

      const clampedRating = Math.min(5, Math.max(1, rating));
      setMetrics((prev) => ({
        ...prev,
        happiness: {
          ...prev.happiness,
          satisfactionRating: clampedRating,
        },
      }));
    },
    [isTrackingEnabled]
  );

  // Adoption
  const markReturningUser = useCallback(() => {
    if (!isTrackingEnabled) return;

    setMetrics((prev) => ({
      ...prev,
      adoption: {
        ...prev.adoption,
        isNewUser: false,
      },
    }));
  }, [isTrackingEnabled]);

  const trackOnboardingStep = useCallback(
    (step: string) => {
      if (!isTrackingEnabled) return;

      setMetrics((prev) => ({
        ...prev,
        adoption: {
          ...prev.adoption,
          onboardingStepsCompleted: prev.adoption.onboardingStepsCompleted.includes(step)
            ? prev.adoption.onboardingStepsCompleted
            : [...prev.adoption.onboardingStepsCompleted, step],
        },
      }));
    },
    [isTrackingEnabled]
  );

  // Retention
  const trackReturnVisit = useCallback(() => {
    if (!isTrackingEnabled) return;

    setMetrics((prev) => ({
      ...prev,
      retention: {
        ...prev.retention,
        returnVisits: prev.retention.returnVisits + 1,
      },
    }));
  }, [isTrackingEnabled]);

  const trackActiveDay = useCallback(() => {
    if (!isTrackingEnabled) return;

    const today = new Date().toISOString().split('T')[0];
    setMetrics((prev) => {
      if (prev.retention.lastActiveDate === today) {
        return prev;
      }
      return {
        ...prev,
        retention: {
          ...prev.retention,
          daysActive: prev.retention.daysActive + 1,
          lastActiveDate: today,
        },
      };
    });
  }, [isTrackingEnabled]);

  // Utils
  const exportMetrics = useCallback(() => {
    return { ...metrics };
  }, [metrics]);

  const resetMetrics = useCallback(() => {
    setMetrics(initialMetrics);
    taskStartTimes.current.clear();
    completionTimes.current = [];
    sessionStartTime.current = Date.now();
  }, []);

  // Auto-update session duration periodically
  useEffect(() => {
    if (!isTrackingEnabled) return;

    const interval = setInterval(updateSessionDuration, 30000);
    return () => clearInterval(interval);
  }, [isTrackingEnabled, updateSessionDuration]);

  const value = useMemo<HeartMetricsContextValue>(
    () => ({
      metrics,
      isTrackingEnabled,
      setTrackingEnabled,
      trackTaskStart,
      trackTaskComplete,
      trackTaskError,
      trackFeatureUsed,
      trackInteraction,
      updateSessionDuration,
      recordNPSScore,
      recordSatisfaction,
      markReturningUser,
      trackOnboardingStep,
      trackReturnVisit,
      trackActiveDay,
      exportMetrics,
      resetMetrics,
    }),
    [
      metrics,
      isTrackingEnabled,
      setTrackingEnabled,
      trackTaskStart,
      trackTaskComplete,
      trackTaskError,
      trackFeatureUsed,
      trackInteraction,
      updateSessionDuration,
      recordNPSScore,
      recordSatisfaction,
      markReturningUser,
      trackOnboardingStep,
      trackReturnVisit,
      trackActiveDay,
      exportMetrics,
      resetMetrics,
    ]
  );

  return (
    <HeartMetricsContext.Provider value={value}>
      {children}
    </HeartMetricsContext.Provider>
  );
}

// =============================================================================
// Hook
// =============================================================================

export function useHeartMetrics(): HeartMetricsContextValue {
  const context = useContext(HeartMetricsContext);
  if (!context) {
    throw new Error('useHeartMetrics must be used within a HeartMetricsProvider');
  }
  return context;
}

export default useHeartMetrics;
