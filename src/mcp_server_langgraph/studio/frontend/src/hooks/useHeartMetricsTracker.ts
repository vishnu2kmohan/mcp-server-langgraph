/**
 * useHeartMetricsTracker Hook
 *
 * HEART metrics tracking hook for measuring UX quality.
 * Implements Google's HEART framework:
 * - Happiness: NPS scores, satisfaction ratings
 * - Engagement: Session duration, feature usage
 * - Adoption: Onboarding completion, feature discovery
 * - Retention: Return visit tracking
 * - Task Success: Goal completion rates
 */

import { useState, useCallback, useRef, useEffect } from "react";
import { storage, STORAGE_KEYS } from "../utils/storage";

/**
 * Happiness tracking payload
 */
export interface HappinessPayload {
  npsScore?: number;
  feedback?: string;
  satisfactionRating?: number;
  [key: string]: unknown;
}

/**
 * Engagement tracking payload
 */
export interface EngagementPayload {
  feature: string;
  action: string;
  [key: string]: unknown;
}

/**
 * Adoption tracking payload
 */
export interface AdoptionPayload {
  step?: string;
  stepIndex?: number;
  completed?: boolean;
  feature?: string;
  discovered?: boolean;
  [key: string]: unknown;
}

/**
 * Event queued for batching
 */
interface QueuedEvent {
  event_type: string;
  payload: Record<string, unknown>;
  timestamp: number;
}

/**
 * HEART metrics tracker result
 */
export interface HeartMetricsTrackerResult {
  /** Session start timestamp */
  sessionStartTime: number;
  /** Get current session duration in ms */
  getSessionDuration: () => number;
  /** Track happiness metrics (NPS, satisfaction) */
  trackHappiness: (payload: HappinessPayload) => Promise<void>;
  /** Track engagement metrics (feature usage) */
  trackEngagement: (payload: EngagementPayload) => void;
  /** Track adoption metrics (onboarding, feature discovery) */
  trackAdoption: (payload: AdoptionPayload) => Promise<void>;
  /** Track retention metrics (return visits) */
  trackRetention: () => Promise<void>;
  /** Days since last visit (0 for first visit) */
  daysSinceLastVisit: number;
  /** Start a task for success tracking */
  startTask: (taskId: string) => void;
  /** Complete current task */
  completeTask: (success: boolean, error?: string) => Promise<void>;
  /** Current task being tracked */
  currentTaskId: string | null;
  /** Flush all pending events */
  flushMetrics: () => Promise<void>;
  /** Number of events waiting to be sent */
  pendingEventsCount: number;
}

const HEART_API_ENDPOINT = "/api/v1/metrics/heart/event";
const LAST_VISIT_KEY = STORAGE_KEYS.LAST_VISIT;
const MS_PER_DAY = 86400000;

/**
 * Hook for tracking HEART metrics.
 *
 * @example
 * ```tsx
 * const {
 *   trackHappiness,
 *   trackEngagement,
 *   trackAdoption,
 *   startTask,
 *   completeTask,
 *   daysSinceLastVisit,
 * } = useHeartMetricsTracker();
 *
 * // Track NPS survey
 * await trackHappiness({ npsScore: 9, feedback: "Great experience!" });
 *
 * // Track feature usage
 * trackEngagement({ feature: "workflow_builder", action: "create_node" });
 *
 * // Track onboarding
 * await trackAdoption({ step: "template_selected", stepIndex: 2, completed: true });
 *
 * // Track task success
 * startTask("create_workflow");
 * // ... user completes task
 * await completeTask(true);
 * ```
 */
export function useHeartMetricsTracker(): HeartMetricsTrackerResult {
  // Session start time - captured once on mount
  const sessionStartTimeRef = useRef<number>(performance.now());

  // Task tracking
  const [currentTaskId, setCurrentTaskId] = useState<string | null>(null);
  const taskStartTimeRef = useRef<number | null>(null);

  // Event batching queue
  const eventQueueRef = useRef<QueuedEvent[]>([]);
  const [pendingEventsCount, setPendingEventsCount] = useState(0);

  // Calculate days since last visit using useState initializer
  // This captures the storage value exactly once at mount time
  const [daysSinceLastVisit] = useState<number>(() => {
    const lastVisit = storage.get<string>(LAST_VISIT_KEY);
    if (!lastVisit) return 0;

    const lastVisitTime = parseInt(lastVisit, 10);
    const now = Date.now();
    const daysDiff = Math.floor((now - lastVisitTime) / MS_PER_DAY);
    return daysDiff;
  });

  // Update last visit on mount
  useEffect(() => {
    storage.set(LAST_VISIT_KEY, Date.now().toString());
  }, []);

  /**
   * Get current session duration in milliseconds
   */
  const getSessionDuration = useCallback((): number => {
    return performance.now() - sessionStartTimeRef.current;
  }, []);

  /**
   * Send event to API
   */
  const sendEvent = useCallback(
    async (
      eventType: string,
      payload: Record<string, unknown>,
    ): Promise<void> => {
      try {
        await fetch(HEART_API_ENDPOINT, {
          method: "POST",
          headers: {
            "Content-Type": "application/json",
          },
          body: JSON.stringify({
            event_type: eventType,
            ...payload,
            timestamp: Date.now(),
          }),
        });
      } catch {
        // Silently handle errors - metrics should not break the app
        console.warn(`Failed to send HEART metric: ${eventType}`);
      }
    },
    [],
  );

  /**
   * Queue event for batching
   */
  const queueEvent = useCallback(
    (eventType: string, payload: Record<string, unknown>) => {
      eventQueueRef.current.push({
        event_type: eventType,
        payload,
        timestamp: Date.now(),
      });
      setPendingEventsCount(eventQueueRef.current.length);
    },
    [],
  );

  /**
   * Track happiness metrics (NPS, satisfaction)
   */
  const trackHappiness = useCallback(
    async (payload: HappinessPayload): Promise<void> => {
      await sendEvent("happiness", payload);
    },
    [sendEvent],
  );

  /**
   * Track engagement metrics (feature usage)
   * Uses batching to reduce API calls
   */
  const trackEngagement = useCallback(
    (payload: EngagementPayload): void => {
      queueEvent("engagement", payload);
    },
    [queueEvent],
  );

  /**
   * Track adoption metrics (onboarding, feature discovery)
   */
  const trackAdoption = useCallback(
    async (payload: AdoptionPayload): Promise<void> => {
      await sendEvent("adoption", payload);
    },
    [sendEvent],
  );

  /**
   * Track retention metrics (return visits)
   */
  const trackRetention = useCallback(async (): Promise<void> => {
    await sendEvent("retention", {
      days_since_last_visit: daysSinceLastVisit,
    });
  }, [sendEvent, daysSinceLastVisit]);

  /**
   * Start tracking a task
   */
  const startTask = useCallback((taskId: string): void => {
    setCurrentTaskId(taskId);
    taskStartTimeRef.current = performance.now();
  }, []);

  /**
   * Complete current task
   */
  const completeTask = useCallback(
    async (success: boolean, error?: string): Promise<void> => {
      const duration =
        taskStartTimeRef.current !== null
          ? performance.now() - taskStartTimeRef.current
          : 0;

      await sendEvent("task_success", {
        task_id: currentTaskId,
        success,
        duration_ms: duration,
        ...(error && { error }),
      });

      setCurrentTaskId(null);
      taskStartTimeRef.current = null;
    },
    [sendEvent, currentTaskId],
  );

  /**
   * Flush all pending events
   */
  const flushMetrics = useCallback(async (): Promise<void> => {
    // Send session duration as engagement event
    await sendEvent("engagement", {
      session_duration: getSessionDuration(),
    });

    // Send all queued events
    const events = [...eventQueueRef.current];
    eventQueueRef.current = [];
    setPendingEventsCount(0);

    for (const event of events) {
      await sendEvent(event.event_type, event.payload);
    }
  }, [sendEvent, getSessionDuration]);

  return {
    sessionStartTime: sessionStartTimeRef.current,
    getSessionDuration,
    trackHappiness,
    trackEngagement,
    trackAdoption,
    trackRetention,
    daysSinceLastVisit,
    startTask,
    completeTask,
    currentTaskId,
    flushMetrics,
    pendingEventsCount,
  };
}

export default useHeartMetricsTracker;
