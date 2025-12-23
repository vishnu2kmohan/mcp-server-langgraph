/**
 * MetricsCalculator
 *
 * Calculates HEART metrics from recorded signals.
 * Supports various calculation methods:
 * - NPS calculation (promoters - detractors)
 * - Averages
 * - Percentages/rates
 * - Counts
 */

import {
  type HeartDimension,
  getAllGoals,
  getGoalById,
} from "./GoalsDefinition";
import { getSignalValues, getAllSignals } from "./SignalsRegistry";

/**
 * Metric calculation result
 */
export interface MetricResult {
  /** Calculated metric value (null if insufficient data) */
  value: number | null;
  /** Number of data points used */
  sampleSize: number;
  /** Confidence level (0-1 based on sample size) */
  confidence: number;
  /** When the metric was calculated */
  calculatedAt: number;
}

/**
 * Goal progress tracking
 */
export interface GoalProgress {
  /** Goal ID */
  goalId: string;
  /** Current metric value */
  currentValue: number | null;
  /** Target value from goal definition */
  targetValue: number;
  /** Progress percentage (0-100) */
  progressPercent: number;
  /** Whether the goal is achieved */
  isAchieved: boolean;
}

/**
 * Dimension score
 */
export interface DimensionScore {
  /** HEART dimension */
  dimension: HeartDimension;
  /** Overall score for this dimension (0-100) */
  overallScore: number;
  /** Whether this dimension has data */
  hasData: boolean;
  /** Progress for each goal in this dimension */
  goalProgresses: GoalProgress[];
}

/**
 * Complete metrics summary
 */
export interface MetricsSummary {
  /** Scores for each dimension */
  dimensions: DimensionScore[];
  /** Overall HEART health score (0-100) */
  overallHealthScore: number;
  /** When the summary was generated */
  timestamp: number;
  /** Total data points used */
  dataPointCount: number;
  /** Oldest data point timestamp */
  oldestDataPoint: number | null;
  /** Newest data point timestamp */
  newestDataPoint: number | null;
}

/**
 * Metric calculation types
 */
type MetricType =
  | "nps"
  | "satisfaction"
  | "session_duration"
  | "actions_per_session"
  | "onboarding_completion_rate"
  | "task_success_rate"
  | "error_rate";

/**
 * Calculate confidence based on sample size
 */
function calculateConfidence(sampleSize: number): number {
  if (sampleSize === 0) return 0;
  if (sampleSize >= 100) return 1;
  if (sampleSize >= 30) return 0.8;
  if (sampleSize >= 10) return 0.5;
  return 0.2;
}

/**
 * Calculate NPS from scores
 */
function calculateNPS(scores: number[]): number | null {
  if (scores.length === 0) return null;

  const promoters = scores.filter((s) => s >= 9).length;
  const detractors = scores.filter((s) => s <= 6).length;
  const total = scores.length;

  return ((promoters - detractors) / total) * 100;
}

/**
 * Calculate average from numbers
 */
function calculateAverage(values: number[]): number | null {
  if (values.length === 0) return null;
  return values.reduce((sum, v) => sum + v, 0) / values.length;
}

/**
 * Calculate rate from boolean values
 */
function calculateRate(
  values: boolean[],
  countTrue: boolean = true,
): number | null {
  if (values.length === 0) return null;
  const count = values.filter((v) => v === countTrue).length;
  return count / values.length;
}

/**
 * Calculate a specific metric
 */
export function calculateMetric(metricType: MetricType): MetricResult {
  const now = Date.now();

  switch (metricType) {
    case "nps": {
      const events = getSignalValues("happiness_nps_score");
      const scores = events.map((e) => e.value as number);
      return {
        value: calculateNPS(scores),
        sampleSize: scores.length,
        confidence: calculateConfidence(scores.length),
        calculatedAt: now,
      };
    }

    case "satisfaction": {
      const events = getSignalValues("happiness_satisfaction_rating");
      const ratings = events.map((e) => e.value as number);
      return {
        value: calculateAverage(ratings),
        sampleSize: ratings.length,
        confidence: calculateConfidence(ratings.length),
        calculatedAt: now,
      };
    }

    case "session_duration": {
      const events = getSignalValues("engagement_session_duration");
      const durations = events.map((e) => e.value as number);
      return {
        value: calculateAverage(durations),
        sampleSize: durations.length,
        confidence: calculateConfidence(durations.length),
        calculatedAt: now,
      };
    }

    case "actions_per_session": {
      const events = getSignalValues("engagement_actions_per_session");
      const actions = events.map((e) => e.value as number);
      return {
        value: calculateAverage(actions),
        sampleSize: actions.length,
        confidence: calculateConfidence(actions.length),
        calculatedAt: now,
      };
    }

    case "onboarding_completion_rate": {
      const events = getSignalValues("adoption_onboarding_complete");
      const completions = events.map((e) => e.value as boolean);
      return {
        value: calculateRate(completions),
        sampleSize: completions.length,
        confidence: calculateConfidence(completions.length),
        calculatedAt: now,
      };
    }

    case "task_success_rate": {
      const completed = getSignalValues("task_completed");
      const failed = getSignalValues("task_failed");
      const total = completed.length + failed.length;
      return {
        value: total > 0 ? completed.length / total : null,
        sampleSize: total,
        confidence: calculateConfidence(total),
        calculatedAt: now,
      };
    }

    case "error_rate": {
      const completed = getSignalValues("task_completed");
      const failed = getSignalValues("task_failed");
      const total = completed.length + failed.length;
      return {
        value: total > 0 ? failed.length / total : null,
        sampleSize: total,
        confidence: calculateConfidence(total),
        calculatedAt: now,
      };
    }

    default:
      return {
        value: null,
        sampleSize: 0,
        confidence: 0,
        calculatedAt: now,
      };
  }
}

/**
 * Calculate progress toward a goal
 */
export function calculateGoalProgress(goalId: string): GoalProgress {
  const goal = getGoalById(goalId);

  if (!goal) {
    return {
      goalId,
      currentValue: null,
      targetValue: 0,
      progressPercent: 0,
      isAchieved: false,
    };
  }

  // Map goal ID to metric type
  const metricTypeMap: Record<string, MetricType> = {
    happiness_nps: "nps",
    happiness_satisfaction: "satisfaction",
    engagement_session_duration: "session_duration",
    engagement_actions_per_session: "actions_per_session",
    adoption_onboarding: "onboarding_completion_rate",
    task_success_completion: "task_success_rate",
    task_success_error_rate: "error_rate",
  };

  const metricType = metricTypeMap[goalId];
  let currentValue: number | null = null;

  if (metricType) {
    const result = calculateMetric(metricType);
    currentValue = result.value;
  }

  // Calculate progress
  let progressPercent = 0;
  let isAchieved = false;

  if (currentValue !== null) {
    // For error rate, lower is better
    if (goalId === "task_success_error_rate") {
      progressPercent = Math.max(
        0,
        Math.min(100, (1 - currentValue / goal.targetValue) * 100),
      );
      isAchieved = currentValue <= goal.targetValue;
    } else {
      progressPercent = Math.max(
        0,
        Math.min(100, (currentValue / goal.targetValue) * 100),
      );
      isAchieved = currentValue >= goal.targetValue;
    }
  }

  return {
    goalId,
    currentValue,
    targetValue: goal.targetValue,
    progressPercent,
    isAchieved,
  };
}

/**
 * Calculate score for a dimension
 */
export function calculateDimensionScore(
  dimension: HeartDimension,
): DimensionScore {
  const goals = getAllGoals().filter((g) => g.dimension === dimension);
  const goalProgresses = goals.map((g) => calculateGoalProgress(g.id));

  // Check if we have any data
  const hasData = goalProgresses.some((p) => p.currentValue !== null);

  // Calculate overall score as average of goal progress
  const progressesWithData = goalProgresses.filter(
    (p) => p.currentValue !== null,
  );
  const overallScore =
    progressesWithData.length > 0
      ? progressesWithData.reduce((sum, p) => sum + p.progressPercent, 0) /
        progressesWithData.length
      : 0;

  return {
    dimension,
    overallScore,
    hasData,
    goalProgresses,
  };
}

/**
 * Get complete metrics summary
 */
export function getMetricsSummary(): MetricsSummary {
  const dimensions: HeartDimension[] = [
    "happiness",
    "engagement",
    "adoption",
    "retention",
    "task_success",
  ];

  const dimensionScores = dimensions.map((d) => calculateDimensionScore(d));

  // Calculate overall health score
  const scoresWithData = dimensionScores.filter((d) => d.hasData);
  const overallHealthScore =
    scoresWithData.length > 0
      ? scoresWithData.reduce((sum, d) => sum + d.overallScore, 0) /
        scoresWithData.length
      : 0;

  // Gather data point info
  const allSignals = getAllSignals();
  let dataPointCount = 0;
  let oldestDataPoint: number | null = null;
  let newestDataPoint: number | null = null;

  allSignals.forEach((signal) => {
    const values = getSignalValues(signal.id);
    dataPointCount += values.length;

    values.forEach((v) => {
      if (oldestDataPoint === null || v.timestamp < oldestDataPoint) {
        oldestDataPoint = v.timestamp;
      }
      if (newestDataPoint === null || v.timestamp > newestDataPoint) {
        newestDataPoint = v.timestamp;
      }
    });
  });

  return {
    dimensions: dimensionScores,
    overallHealthScore,
    timestamp: Date.now(),
    dataPointCount,
    oldestDataPoint,
    newestDataPoint,
  };
}

export default {
  calculateMetric,
  calculateGoalProgress,
  calculateDimensionScore,
  getMetricsSummary,
};
