/**
 * HEART Metrics Hook
 *
 * Google's HEART Framework for UX metrics:
 * - Happiness: User satisfaction
 * - Engagement: User interaction depth
 * - Adoption: New user acquisition
 * - Retention: Return visits
 * - Task Success: Completion rates
 */

import { useState, useEffect, useCallback, useRef } from 'react';

// ==============================================================================
// Types
// ==============================================================================

export interface HeartEvent {
  category: 'happiness' | 'engagement' | 'adoption' | 'retention' | 'task' | string;
  action: string;
  label?: string;
  value?: number;
  timestamp?: number;
}

interface TaskMetric {
  startTime: number;
  endTime?: number;
  duration?: number;
  completed?: boolean;
  failed?: boolean;
  error?: string;
}

interface SessionMetrics {
  sessionId: string;
  isNewUser: boolean;
  visitCount: number;
  timeOnPage: number;
  events: HeartEvent[];
  tasks: Record<string, TaskMetric>;
  taskSuccessRate: number;
  engagementScore: number;
  featuresUsed: string[];
  userId?: string;
}

interface HeartMetricsOptions {
  enabled?: boolean;
  endpoint?: string;
  batchSize?: number;
  respectDoNotTrack?: boolean;
}

interface HeartMetricsResult {
  trackEvent: (event: Omit<HeartEvent, 'timestamp'>) => void;
  trackTaskStart: (taskId: string) => void;
  trackTaskComplete: (taskId: string, metadata?: Record<string, any>) => void;
  trackTaskFail: (taskId: string, error: string) => void;
  trackEngagement: (feature: string) => void;
  getSessionMetrics: () => SessionMetrics;
}

// ==============================================================================
// Constants
// ==============================================================================

const STORAGE_KEY = 'heart_metrics_user';
const SESSION_KEY = 'heart_metrics_session';

// ==============================================================================
// Helpers
// ==============================================================================

function generateSessionId(): string {
  return `session_${Date.now()}_${Math.random().toString(36).substr(2, 9)}`;
}

function isDoNotTrack(): boolean {
  return navigator?.doNotTrack === '1';
}

// ==============================================================================
// Hook Implementation
// ==============================================================================

export function useHeartMetrics(options: HeartMetricsOptions = {}): HeartMetricsResult {
  const {
    enabled = true,
    endpoint,
    batchSize = 10,
    respectDoNotTrack = false,
  } = options;

  // Check if tracking should be disabled
  const isTrackingEnabled = enabled && !(respectDoNotTrack && isDoNotTrack());

  // Session ID (lazy initialization via useState)
  const [sessionId] = useState<string>(() => {
    if (typeof window === 'undefined') return generateSessionId();
    const stored = sessionStorage.getItem(SESSION_KEY);
    if (stored) return stored;
    const newId = generateSessionId();
    sessionStorage.setItem(SESSION_KEY, newId);
    return newId;
  });

  // User persistence (for retention metrics)
  const [isNewUser, setIsNewUser] = useState<boolean>(true);
  const [visitCount, setVisitCount] = useState<number>(1);

  // Events and tasks
  const [events, setEvents] = useState<HeartEvent[]>([]);
  const [tasks, setTasks] = useState<Record<string, TaskMetric>>({});
  const [featuresUsed, setFeaturesUsed] = useState<string[]>([]);

  // Time tracking
  const startTimeRef = useRef<number>(Date.now());

  // Initialize user tracking
  useEffect(() => {
    if (typeof window === 'undefined') return;

    const storedUser = localStorage.getItem(STORAGE_KEY);

    if (storedUser) {
      const userData = JSON.parse(storedUser);
      setIsNewUser(false);
      setVisitCount(userData.visitCount + 1);
      localStorage.setItem(STORAGE_KEY, JSON.stringify({
        ...userData,
        visitCount: userData.visitCount + 1,
        lastVisit: Date.now(),
      }));
    } else {
      localStorage.setItem(STORAGE_KEY, JSON.stringify({
        firstVisit: Date.now(),
        lastVisit: Date.now(),
        visitCount: 1,
      }));
    }
  }, []);

  // Send metrics on page unload
  useEffect(() => {
    if (!endpoint) return;

    const handleUnload = () => {
      if (events.length > 0) {
        const data = JSON.stringify({
          sessionId,
          events,
          tasks,
          timestamp: Date.now(),
        });
        navigator.sendBeacon?.(endpoint, data);
      }
    };

    window.addEventListener('beforeunload', handleUnload);
    return () => window.removeEventListener('beforeunload', handleUnload);
  }, [endpoint, sessionId, events, tasks]);

  // Track event
  const trackEvent = useCallback((event: Omit<HeartEvent, 'timestamp'>) => {
    if (!isTrackingEnabled) return;

    const fullEvent: HeartEvent = {
      ...event,
      timestamp: Date.now(),
    };

    setEvents((prev) => {
      const newEvents = [...prev, fullEvent];

      // Batch send if threshold reached
      if (endpoint && newEvents.length >= batchSize) {
        const data = JSON.stringify({
          sessionId,
          events: newEvents,
          timestamp: Date.now(),
        });
        navigator.sendBeacon?.(endpoint, data);
        return [];
      }

      return newEvents;
    });
  }, [isTrackingEnabled, endpoint, batchSize, sessionId]);

  // Track task start
  const trackTaskStart = useCallback((taskId: string) => {
    if (!isTrackingEnabled) return;

    setTasks((prev) => ({
      ...prev,
      [taskId]: {
        startTime: Date.now(),
      },
    }));

    trackEvent({
      category: 'task',
      action: 'start',
      label: taskId,
    });
  }, [isTrackingEnabled, trackEvent]);

  // Track task completion
  const trackTaskComplete = useCallback((taskId: string, _metadata?: Record<string, unknown>) => {
    if (!isTrackingEnabled) return;

    setTasks((prev) => {
      const task = prev[taskId];
      if (!task) return prev;

      const endTime = Date.now();
      return {
        ...prev,
        [taskId]: {
          ...task,
          endTime,
          duration: endTime - task.startTime,
          completed: true,
        },
      };
    });

    trackEvent({
      category: 'task',
      action: 'complete',
      label: taskId,
    });
  }, [isTrackingEnabled, trackEvent]);

  // Track task failure
  const trackTaskFail = useCallback((taskId: string, error: string) => {
    if (!isTrackingEnabled) return;

    setTasks((prev) => {
      const task = prev[taskId];
      if (!task) return prev;

      return {
        ...prev,
        [taskId]: {
          ...task,
          endTime: Date.now(),
          duration: Date.now() - task.startTime,
          failed: true,
          error,
        },
      };
    });

    trackEvent({
      category: 'task',
      action: 'fail',
      label: taskId,
      value: 0,
    });
  }, [isTrackingEnabled, trackEvent]);

  // Track engagement
  const trackEngagement = useCallback((feature: string) => {
    if (!isTrackingEnabled) return;

    // Extract feature name if prefixed
    const featureName = feature.startsWith('feature:')
      ? feature.substring(8)
      : feature;

    setFeaturesUsed((prev) => {
      if (prev.includes(featureName)) return prev;
      return [...prev, featureName];
    });

    trackEvent({
      category: 'engagement',
      action: 'feature_used',
      label: featureName,
    });
  }, [isTrackingEnabled, trackEvent]);

  // Get session metrics
  const getSessionMetrics = useCallback((): SessionMetrics => {
    // Calculate task success rate
    const taskEntries = Object.values(tasks);
    const completedTasks = taskEntries.filter((t) => t.completed).length;
    const failedTasks = taskEntries.filter((t) => t.failed).length;
    const totalTasks = completedTasks + failedTasks;
    const taskSuccessRate = totalTasks > 0 ? completedTasks / totalTasks : 0;

    // Calculate engagement score (simple formula)
    const engagementScore = events.length + featuresUsed.length * 2;

    return {
      sessionId,
      isNewUser,
      visitCount,
      timeOnPage: Date.now() - startTimeRef.current,
      events,
      tasks,
      taskSuccessRate,
      engagementScore,
      featuresUsed,
    };
  }, [sessionId, isNewUser, visitCount, events, tasks, featuresUsed]);

  return {
    trackEvent,
    trackTaskStart,
    trackTaskComplete,
    trackTaskFail,
    trackEngagement,
    getSessionMetrics,
  };
}

export default useHeartMetrics;
