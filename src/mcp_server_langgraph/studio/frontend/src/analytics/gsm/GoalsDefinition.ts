/**
 * GoalsDefinition
 *
 * Defines HEART goals for the Goals-Signals-Metrics (GSM) framework.
 * Each goal maps to specific signals that indicate progress.
 *
 * HEART Dimensions:
 * - Happiness: User satisfaction and sentiment
 * - Engagement: Active usage and depth
 * - Adoption: New user success and feature discovery
 * - Retention: Return visits and continued usage
 * - Task Success: Goal completion and error rates
 */

/**
 * HEART dimension types
 */
export type HeartDimension =
  | "happiness"
  | "engagement"
  | "adoption"
  | "retention"
  | "task_success";

/**
 * Goal definition
 */
export interface HeartGoal {
  /** Unique goal identifier */
  id: string;
  /** HEART dimension this goal belongs to */
  dimension: HeartDimension;
  /** Human-readable description */
  description: string;
  /** Target value to achieve */
  targetValue: number;
  /** Unit for the target value */
  unit: string;
  /** Signal IDs that contribute to this goal */
  signals: string[];
  /** Metric calculation method */
  metricType: "average" | "percentage" | "count" | "nps" | "ratio";
}

/**
 * HEART goals organized by dimension
 */
export const HEART_GOALS: Record<HeartDimension, HeartGoal[]> = {
  happiness: [
    {
      id: "happiness_nps",
      dimension: "happiness",
      description: "Achieve high Net Promoter Score (NPS) from users",
      targetValue: 50,
      unit: "NPS score",
      signals: ["happiness_nps_score"],
      metricType: "nps",
    },
    {
      id: "happiness_satisfaction",
      dimension: "happiness",
      description: "Maintain high user satisfaction ratings",
      targetValue: 4.0,
      unit: "average rating (1-5)",
      signals: ["happiness_satisfaction_rating"],
      metricType: "average",
    },
  ],
  engagement: [
    {
      id: "engagement_dau_mau",
      dimension: "engagement",
      description: "Maintain healthy DAU/MAU ratio",
      targetValue: 0.4,
      unit: "ratio",
      signals: ["engagement_daily_active", "engagement_monthly_active"],
      metricType: "ratio",
    },
    {
      id: "engagement_session_duration",
      dimension: "engagement",
      description: "Users spend meaningful time in sessions",
      targetValue: 300000, // 5 minutes in ms
      unit: "ms",
      signals: ["engagement_session_duration"],
      metricType: "average",
    },
    {
      id: "engagement_actions_per_session",
      dimension: "engagement",
      description: "Users perform multiple actions per session",
      targetValue: 10,
      unit: "actions",
      signals: ["engagement_actions_per_session", "engagement_feature_click"],
      metricType: "average",
    },
  ],
  adoption: [
    {
      id: "adoption_onboarding",
      dimension: "adoption",
      description: "New users complete onboarding",
      targetValue: 0.8,
      unit: "completion rate",
      signals: ["adoption_onboarding_complete", "adoption_onboarding_started"],
      metricType: "percentage",
    },
    {
      id: "adoption_feature",
      dimension: "adoption",
      description: "Users discover and use key features",
      targetValue: 0.6,
      unit: "adoption rate",
      signals: ["adoption_feature_first_use"],
      metricType: "percentage",
    },
  ],
  retention: [
    {
      id: "retention_d1",
      dimension: "retention",
      description: "Users return within 1 day",
      targetValue: 0.5,
      unit: "D1 retention",
      signals: ["retention_return_visit"],
      metricType: "percentage",
    },
    {
      id: "retention_d7",
      dimension: "retention",
      description: "Users return within 7 days",
      targetValue: 0.35,
      unit: "D7 retention",
      signals: ["retention_return_visit"],
      metricType: "percentage",
    },
    {
      id: "retention_d30",
      dimension: "retention",
      description: "Users return within 30 days",
      targetValue: 0.25,
      unit: "D30 retention",
      signals: ["retention_return_visit"],
      metricType: "percentage",
    },
  ],
  task_success: [
    {
      id: "task_success_completion",
      dimension: "task_success",
      description: "Users successfully complete tasks",
      targetValue: 0.9,
      unit: "success rate",
      signals: ["task_completed", "task_failed"],
      metricType: "percentage",
    },
    {
      id: "task_success_error_rate",
      dimension: "task_success",
      description: "Keep error rate low",
      targetValue: 0.05,
      unit: "error rate",
      signals: ["task_failed", "task_completed"],
      metricType: "percentage",
    },
  ],
};

/**
 * Get goals for a specific dimension
 */
export function getGoalsForDimension(dimension: HeartDimension): HeartGoal[] {
  return HEART_GOALS[dimension] ?? [];
}

/**
 * Get all goals across all dimensions
 */
export function getAllGoals(): HeartGoal[] {
  return Object.values(HEART_GOALS).flat();
}

/**
 * Get a goal by ID
 */
export function getGoalById(goalId: string): HeartGoal | undefined {
  return getAllGoals().find((g) => g.id === goalId);
}

export default {
  HEART_GOALS,
  getGoalsForDimension,
  getAllGoals,
  getGoalById,
};
