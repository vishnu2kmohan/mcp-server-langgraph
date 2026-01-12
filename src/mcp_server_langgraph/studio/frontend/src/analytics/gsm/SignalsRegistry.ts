/**
 * SignalsRegistry
 *
 * Registry for tracking HEART metric signals.
 * Signals are user actions or events that indicate progress toward goals.
 *
 * Features:
 * - Signal definition with value types
 * - Signal value recording with timestamps
 * - Filtering by time range
 * - Metadata support
 */

import { getAllGoals } from "./GoalsDefinition";

/**
 * Signal value types
 */
export type SignalValueType = "number" | "boolean" | "string" | "counter";

/**
 * Signal definition
 */
export interface Signal {
  /** Unique signal identifier */
  id: string;
  /** Human-readable name */
  name: string;
  /** Description of what this signal measures */
  description: string;
  /** Type of value this signal produces */
  valueType: SignalValueType;
}

/**
 * Recorded signal event
 */
export interface SignalEvent {
  /** Signal ID */
  signalId: string;
  /** Recorded value */
  value: number | boolean | string;
  /** When the signal was recorded */
  timestamp: number;
  /** Optional metadata */
  metadata?: Record<string, unknown>;
}

/**
 * Options for filtering signal values
 */
export interface SignalFilterOptions {
  /** Only return values after this timestamp */
  since?: number;
  /** Only return values before this timestamp */
  until?: number;
}

/**
 * All defined signals
 */
export const SIGNALS: Signal[] = [
  // Happiness signals
  {
    id: "happiness_nps_score",
    name: "NPS Score",
    description: "Net Promoter Score survey response (0-10)",
    valueType: "number",
  },
  {
    id: "happiness_satisfaction_rating",
    name: "Satisfaction Rating",
    description: "User satisfaction rating (1-5)",
    valueType: "number",
  },
  {
    id: "happiness_feedback",
    name: "User Feedback",
    description: "Qualitative feedback from users",
    valueType: "string",
  },

  // Engagement signals
  {
    id: "engagement_feature_click",
    name: "Feature Click",
    description: "User clicked on a feature",
    valueType: "counter",
  },
  {
    id: "engagement_session_duration",
    name: "Session Duration",
    description: "Duration of user session in milliseconds",
    valueType: "number",
  },
  {
    id: "engagement_actions_per_session",
    name: "Actions Per Session",
    description: "Number of actions in a session",
    valueType: "number",
  },
  {
    id: "engagement_daily_active",
    name: "Daily Active",
    description: "User was active today",
    valueType: "boolean",
  },
  {
    id: "engagement_monthly_active",
    name: "Monthly Active",
    description: "User was active this month",
    valueType: "boolean",
  },

  // Adoption signals
  {
    id: "adoption_onboarding_started",
    name: "Onboarding Started",
    description: "User started onboarding flow",
    valueType: "boolean",
  },
  {
    id: "adoption_onboarding_complete",
    name: "Onboarding Complete",
    description: "User completed onboarding flow",
    valueType: "boolean",
  },
  {
    id: "adoption_feature_first_use",
    name: "Feature First Use",
    description: "User used a feature for the first time",
    valueType: "boolean",
  },

  // Retention signals
  {
    id: "retention_return_visit",
    name: "Return Visit",
    description: "User returned after previous visit",
    valueType: "boolean",
  },
  {
    id: "retention_days_since_last_visit",
    name: "Days Since Last Visit",
    description: "Number of days since user's last visit",
    valueType: "number",
  },

  // Task success signals
  {
    id: "task_completed",
    name: "Task Completed",
    description: "User successfully completed a task",
    valueType: "boolean",
  },
  {
    id: "task_failed",
    name: "Task Failed",
    description: "User failed to complete a task",
    valueType: "boolean",
  },
  {
    id: "task_duration",
    name: "Task Duration",
    description: "Time taken to complete a task in milliseconds",
    valueType: "number",
  },

  // AI Quality signals (hallucination reporting)
  {
    id: "ai_hallucination_reported",
    name: "Hallucination Reported",
    description: "User reported an AI response as inaccurate",
    valueType: "counter",
  },
  {
    id: "ai_hallucination_category",
    name: "Hallucination Category",
    description:
      "Category of reported hallucination (factual_error, outdated_info, made_up_source, other)",
    valueType: "string",
  },
];

/**
 * In-memory storage for recorded signals
 */
let signalValues: Map<string, SignalEvent[]> = new Map();

/**
 * Get a signal by ID
 */
export function getSignalById(signalId: string): Signal | undefined {
  return SIGNALS.find((s) => s.id === signalId);
}

/**
 * Get signals associated with a goal
 */
export function getSignalsForGoal(goalId: string): Signal[] {
  const goal = getAllGoals().find((g) => g.id === goalId);
  if (!goal) return [];

  return goal.signals
    .map((signalId) => getSignalById(signalId))
    .filter((s): s is Signal => s !== undefined);
}

/**
 * Get all defined signals
 */
export function getAllSignals(): Signal[] {
  return [...SIGNALS];
}

/**
 * Record a signal value
 */
export function recordSignal(
  signalId: string,
  value: number | boolean | string,
  metadata?: Record<string, unknown>,
): void {
  const event: SignalEvent = {
    signalId,
    value,
    timestamp: Date.now(),
    metadata,
  };

  const existing = signalValues.get(signalId) ?? [];
  existing.push(event);
  signalValues.set(signalId, existing);
}

/**
 * Get recorded values for a signal
 */
export function getSignalValues(
  signalId: string,
  options: SignalFilterOptions = {},
): SignalEvent[] {
  const values = signalValues.get(signalId) ?? [];

  return values.filter((event) => {
    if (options.since && event.timestamp < options.since) {
      return false;
    }
    if (options.until && event.timestamp > options.until) {
      return false;
    }
    return true;
  });
}

/**
 * Clear recorded signal values
 */
export function clearSignals(signalId?: string): void {
  if (signalId) {
    signalValues.delete(signalId);
  } else {
    signalValues = new Map();
  }
}

export default {
  SIGNALS,
  getSignalById,
  getSignalsForGoal,
  getAllSignals,
  recordSignal,
  getSignalValues,
  clearSignals,
};
