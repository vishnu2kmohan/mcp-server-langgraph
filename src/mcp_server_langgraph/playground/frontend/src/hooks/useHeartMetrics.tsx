/**
 * useHeartMetrics Hook
 *
 * HEART framework implementation for UX metrics:
 * - Happiness: User satisfaction (NPS, ratings)
 * - Engagement: Session duration, feature usage
 * - Adoption: New user tracking, onboarding
 * - Retention: Return visits, active days
 * - Task Success: Completion rates, error rates
 */

import React, { createContext, useContext, useCallback, useState, useRef, useEffect } from 'react';

// Types
interface TaskMetrics {
  tasksStarted: number;
  tasksCompleted: number;
  errors: number;
  successRate: number;
  averageCompletionTimeMs: number;
}

interface EngagementMetrics {
  sessionDurationMs: number;
  featureUsage: Record<string, number>;
  interactions: number;
}

interface HappinessMetrics {
  npsScore: number | null;
  satisfactionRating: number | null;
}

interface AdoptionMetrics {
  isNewUser: boolean;
  onboardingStepsCompleted: string[];
}

interface RetentionMetrics {
  returnVisits: number;
  daysActive: number;
  lastActiveDate: string | null;
}

interface HeartMetrics {
  taskSuccess: TaskMetrics;
  engagement: EngagementMetrics;
  happiness: HappinessMetrics;
  adoption: AdoptionMetrics;
  retention: RetentionMetrics;
}

interface HeartMetricsContextValue {
  metrics: HeartMetrics;
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

const HeartMetricsContext = createContext<HeartMetricsContextValue | null>(null);

export function HeartMetricsProvider({
  children,
}: {
  children: React.ReactNode;
}): React.ReactElement {
  const [metrics, setMetrics] = useState<HeartMetrics>(initialMetrics);
  const taskStartTimes = useRef<Map<string, number>>(new Map());
  const completionTimes = useRef<number[]>([]);
  const sessionStartTime = useRef<number>(Date.now());

  // Task Success
  const trackTaskStart = useCallback((taskName: string) => {
    taskStartTimes.current.set(taskName, Date.now());
    setMetrics((prev) => ({
      ...prev,
      taskSuccess: {
        ...prev.taskSuccess,
        tasksStarted: prev.taskSuccess.tasksStarted + 1,
      },
    }));
  }, []);

  const trackTaskComplete = useCallback((taskName: string) => {
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
  }, []);

  const trackTaskError = useCallback((taskName: string, _error: string) => {
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
  }, []);

  // Engagement
  const trackFeatureUsed = useCallback((featureName: string) => {
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
  }, []);

  const trackInteraction = useCallback((_type: string, _target: string) => {
    setMetrics((prev) => ({
      ...prev,
      engagement: {
        ...prev.engagement,
        interactions: prev.engagement.interactions + 1,
      },
    }));
  }, []);

  const updateSessionDuration = useCallback(() => {
    const duration = Date.now() - sessionStartTime.current;
    setMetrics((prev) => ({
      ...prev,
      engagement: {
        ...prev.engagement,
        sessionDurationMs: duration,
      },
    }));
  }, []);

  // Happiness
  const recordNPSScore = useCallback((score: number) => {
    const clampedScore = Math.min(10, Math.max(0, score));
    setMetrics((prev) => ({
      ...prev,
      happiness: {
        ...prev.happiness,
        npsScore: clampedScore,
      },
    }));
  }, []);

  const recordSatisfaction = useCallback((rating: number) => {
    const clampedRating = Math.min(5, Math.max(1, rating));
    setMetrics((prev) => ({
      ...prev,
      happiness: {
        ...prev.happiness,
        satisfactionRating: clampedRating,
      },
    }));
  }, []);

  // Adoption
  const markReturningUser = useCallback(() => {
    setMetrics((prev) => ({
      ...prev,
      adoption: {
        ...prev.adoption,
        isNewUser: false,
      },
    }));
  }, []);

  const trackOnboardingStep = useCallback((step: string) => {
    setMetrics((prev) => ({
      ...prev,
      adoption: {
        ...prev.adoption,
        onboardingStepsCompleted: prev.adoption.onboardingStepsCompleted.includes(step)
          ? prev.adoption.onboardingStepsCompleted
          : [...prev.adoption.onboardingStepsCompleted, step],
      },
    }));
  }, []);

  // Retention
  const trackReturnVisit = useCallback(() => {
    setMetrics((prev) => ({
      ...prev,
      retention: {
        ...prev.retention,
        returnVisits: prev.retention.returnVisits + 1,
      },
    }));
  }, []);

  const trackActiveDay = useCallback(() => {
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
  }, []);

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
    const interval = setInterval(updateSessionDuration, 30000);
    return () => clearInterval(interval);
  }, [updateSessionDuration]);

  const value: HeartMetricsContextValue = {
    metrics,
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
  };

  return (
    <HeartMetricsContext.Provider value={value}>
      {children}
    </HeartMetricsContext.Provider>
  );
}

export function useHeartMetrics(): HeartMetricsContextValue {
  const context = useContext(HeartMetricsContext);
  if (!context) {
    throw new Error('useHeartMetrics must be used within a HeartMetricsProvider');
  }
  return context;
}
