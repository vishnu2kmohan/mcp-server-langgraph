/**
 * useHeartMetricsTracker Hook
 *
 * Enhanced HEART metrics tracking hook with:
 * - GSM (Goals-Signals-Metrics) integration
 * - Batched event sending via HeartAggregator (30s timer or 50 events)
 * - Session lifecycle tracking
 * - Persona context in all events
 *
 * Implements Google's HEART framework:
 * - Happiness: NPS scores, satisfaction ratings
 * - Engagement: Session duration, feature usage
 * - Adoption: Onboarding completion, feature discovery
 * - Retention: Return visit tracking
 * - Task Success: Goal completion rates
 *
 * Refactored in Phase 3.2 to use HeartAggregator for batching.
 */

import { useState, useCallback, useRef, useEffect, useMemo } from "react";
import { useSelector } from "react-redux";
import { storage, STORAGE_KEYS } from "../utils/storage";
import { devLogger } from "../utils/devLogger";
import { authenticatedFetch } from "../utils/authenticatedFetch";
import { recordSignal as gsmRecordSignal } from "../analytics/gsm";
import { HeartAggregator } from "../analytics";
import {
  selectSubPersona,
  selectUsername,
  selectPersona,
} from "../store/slices/personaSlice";

const logger = devLogger.withPrefix("[HEART]");

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
 * Batch configuration
 */
export interface BatchConfig {
  /** Flush interval in milliseconds */
  flushIntervalMs: number;
  /** Maximum batch size before auto-flush */
  maxBatchSize: number;
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
  /** Record a GSM signal */
  recordSignal: (
    signalId: string,
    value: number | boolean | string,
    metadata?: Record<string, unknown>,
  ) => void;
  /** Batch configuration */
  batchConfig: BatchConfig;
}

const HEART_API_ENDPOINT = "/api/v1/metrics/heart/event";
const LAST_VISIT_KEY = STORAGE_KEYS.LAST_VISIT;
const MS_PER_DAY = 86400000;

/** Default batch configuration */
const DEFAULT_BATCH_CONFIG: BatchConfig = {
  flushIntervalMs: 30000, // 30 seconds
  maxBatchSize: 50,
};

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
 *   recordSignal,
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
 *
 * // Record GSM signal
 * recordSignal("happiness_nps_score", 9, { source: "popup" });
 * ```
 */
export function useHeartMetricsTracker(): HeartMetricsTrackerResult {
  // Get persona context from Redux
  const subPersona = useSelector(selectSubPersona);
  const persona = useSelector(selectPersona);
  const username = useSelector(selectUsername);

  // Session start time - captured once on mount using Date.now() for stability
  const [sessionStartTime] = useState<number>(() => Date.now());
  const sessionStartPerfRef = useRef<number>(performance.now());

  // Task tracking
  const [currentTaskId, setCurrentTaskId] = useState<string | null>(null);
  const taskStartTimeRef = useRef<number | null>(null);

  // HeartAggregator for batched event sending (refactored Phase 3.2)
  const aggregator = useMemo(
    () =>
      new HeartAggregator({
        flushIntervalMs: DEFAULT_BATCH_CONFIG.flushIntervalMs,
        maxBatchSize: DEFAULT_BATCH_CONFIG.maxBatchSize,
      }),
    [],
  );

  // Track pending events count from aggregator
  const [pendingEventsCount, setPendingEventsCount] = useState(0);

  // Session tracking refs
  const sessionStartSentRef = useRef(false);
  const isMountedRef = useRef(true);

  // Calculate days since last visit using useState initializer
  const [daysSinceLastVisit] = useState<number>(() => {
    const lastVisit = storage.get<string>(LAST_VISIT_KEY);
    if (!lastVisit) return 0;

    const lastVisitTime = parseInt(lastVisit, 10);
    const now = Date.now();
    const daysDiff = Math.floor((now - lastVisitTime) / MS_PER_DAY);
    return daysDiff;
  });

  // Update session context when persona changes
  useEffect(() => {
    aggregator.setSessionContext({
      sessionId: sessionStartTime.toString(),
      persona: subPersona || persona,
      username: username || undefined,
    });
  }, [aggregator, sessionStartTime, subPersona, persona, username]);

  // Set session start time on aggregator
  useEffect(() => {
    aggregator.setSessionStartTime(sessionStartTime);
  }, [aggregator, sessionStartTime]);

  // Cleanup aggregator on unmount
  useEffect(() => {
    return () => {
      void aggregator.destroy(true); // Flush pending events on unmount
    };
  }, [aggregator]);

  /**
   * Get current session duration in milliseconds
   */
  const getSessionDuration = useCallback((): number => {
    return performance.now() - sessionStartPerfRef.current;
  }, []);

  /**
   * Build context object with persona info
   */
  const buildContext = useCallback(() => {
    return {
      persona: subPersona || persona,
      username: username || undefined,
    };
  }, [subPersona, persona, username]);

  /**
   * Send event to API with persona context (for immediate events like happiness)
   */
  const sendEvent = useCallback(
    async (
      eventType: string,
      payload: Record<string, unknown>,
    ): Promise<void> => {
      try {
        const context = buildContext();
        await authenticatedFetch(HEART_API_ENDPOINT, {
          method: "POST",
          body: JSON.stringify({
            event_type: eventType,
            ...payload,
            ...context,
            timestamp: Date.now(),
          }),
          // No onAuthFailure - metrics should fail silently
        });
      } catch {
        // Silently handle errors - metrics should not break the app
        logger.warn(`Failed to send HEART metric: ${eventType}`);
      }
    },
    [buildContext],
  );

  /**
   * Queue event for batching via HeartAggregator
   */
  const queueEvent = useCallback(
    (eventType: string, payload: Record<string, unknown>) => {
      aggregator.queueEvent(eventType, payload);
      setPendingEventsCount(aggregator.getPendingCount());
    },
    [aggregator],
  );

  /**
   * Record a GSM signal
   */
  const recordSignal = useCallback(
    (
      signalId: string,
      value: number | boolean | string,
      metadata?: Record<string, unknown>,
    ) => {
      // Record to GSM registry
      const context = buildContext();
      gsmRecordSignal(signalId, value, { ...metadata, ...context });

      // Also queue for backend
      queueEvent("signal", {
        signal_id: signalId,
        value,
        ...metadata,
      });
    },
    [buildContext, queueEvent],
  );

  /**
   * Track happiness metrics (NPS, satisfaction)
   */
  const trackHappiness = useCallback(
    async (payload: HappinessPayload): Promise<void> => {
      await sendEvent("happiness", payload);

      // Also record to GSM
      if (payload.npsScore !== undefined) {
        gsmRecordSignal(
          "happiness_nps_score",
          payload.npsScore,
          buildContext(),
        );
      }
      if (payload.satisfactionRating !== undefined) {
        gsmRecordSignal(
          "happiness_satisfaction_rating",
          payload.satisfactionRating,
          buildContext(),
        );
      }
    },
    [sendEvent, buildContext],
  );

  /**
   * Track engagement metrics (feature usage)
   * Uses batching to reduce API calls
   */
  const trackEngagement = useCallback(
    (payload: EngagementPayload): void => {
      queueEvent("engagement", payload);

      // Record to GSM
      gsmRecordSignal("engagement_feature_click", 1, {
        ...buildContext(),
        feature: payload.feature,
        action: payload.action,
      });
    },
    [queueEvent, buildContext],
  );

  /**
   * Track adoption metrics (onboarding, feature discovery)
   */
  const trackAdoption = useCallback(
    async (payload: AdoptionPayload): Promise<void> => {
      await sendEvent("adoption", payload);

      // Record to GSM
      if (payload.completed) {
        gsmRecordSignal("adoption_onboarding_complete", true, buildContext());
      }
      if (payload.discovered) {
        gsmRecordSignal("adoption_feature_first_use", true, {
          ...buildContext(),
          feature: payload.feature,
        });
      }
    },
    [sendEvent, buildContext],
  );

  /**
   * Track retention metrics (return visits)
   */
  const trackRetention = useCallback(async (): Promise<void> => {
    await sendEvent("retention", {
      days_since_last_visit: daysSinceLastVisit,
    });

    // Record to GSM
    gsmRecordSignal("retention_return_visit", true, buildContext());
    gsmRecordSignal(
      "retention_days_since_last_visit",
      daysSinceLastVisit,
      buildContext(),
    );
  }, [sendEvent, daysSinceLastVisit, buildContext]);

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

      // Record to GSM
      gsmRecordSignal(success ? "task_completed" : "task_failed", true, {
        ...buildContext(),
        task_id: currentTaskId,
      });
      gsmRecordSignal("task_duration", duration, {
        ...buildContext(),
        task_id: currentTaskId,
      });

      setCurrentTaskId(null);
      taskStartTimeRef.current = null;
    },
    [sendEvent, currentTaskId, buildContext],
  );

  /**
   * Flush all pending events via HeartAggregator
   */
  const flushMetrics = useCallback(async (): Promise<void> => {
    if (aggregator.getPendingCount() > 0) {
      await aggregator.flush();
      setPendingEventsCount(0);
    } else {
      // Send session duration even if no events
      await sendEvent("engagement", {
        session_duration: getSessionDuration(),
      });
    }
  }, [aggregator, sendEvent, getSessionDuration]);

  // Send session start event on mount
  useEffect(() => {
    if (!sessionStartSentRef.current) {
      sessionStartSentRef.current = true;
      sendEvent("session_start", {
        session_id: sessionStartTime,
      });
    }
  }, [sendEvent, sessionStartTime]);

  // Update last visit on mount
  useEffect(() => {
    storage.set(LAST_VISIT_KEY, Date.now().toString());
  }, []);

  // Send session end event on unmount
  useEffect(() => {
    isMountedRef.current = true;
    // Capture the ref value at effect start to avoid stale ref in cleanup
    const sessionStartPerf = sessionStartPerfRef.current;

    return () => {
      isMountedRef.current = false;

      // Sync send session end (can't await in cleanup)
      const context = buildContext();
      const duration = performance.now() - sessionStartPerf;

      // Use sendBeacon for reliable delivery on page unload
      if (navigator.sendBeacon) {
        navigator.sendBeacon(
          HEART_API_ENDPOINT,
          JSON.stringify({
            event_type: "session_end",
            session_id: sessionStartTime,
            session_duration: duration,
            ...context,
            timestamp: Date.now(),
          }),
        );
      } else {
        // Fallback to authenticatedFetch (may not complete on unload)
        authenticatedFetch(HEART_API_ENDPOINT, {
          method: "POST",
          body: JSON.stringify({
            event_type: "session_end",
            session_id: sessionStartTime,
            session_duration: duration,
            ...context,
            timestamp: Date.now(),
          }),
          keepalive: true,
          // No onAuthFailure - cleanup should fail silently
        }).catch(() => {
          // Ignore errors on unmount
        });
      }
    };
  }, [buildContext, sessionStartTime]);

  return {
    sessionStartTime,
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
    recordSignal,
    batchConfig: DEFAULT_BATCH_CONFIG,
  };
}

export default useHeartMetricsTracker;
