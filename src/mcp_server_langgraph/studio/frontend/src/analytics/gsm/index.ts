/**
 * GSM Framework (Goals-Signals-Metrics)
 *
 * A comprehensive framework for HEART metrics tracking.
 *
 * Goals: What you want to achieve for each HEART dimension
 * Signals: User actions that indicate progress toward goals
 * Metrics: Calculated values from aggregated signals
 *
 * Usage:
 * ```typescript
 * import { recordSignal, calculateMetric, getMetricsSummary } from "./gsm";
 *
 * // Record user actions
 * recordSignal("happiness_nps_score", 9);
 * recordSignal("engagement_feature_click", 1, { feature: "workflow_builder" });
 *
 * // Calculate specific metrics
 * const nps = calculateMetric("nps");
 * console.log(`NPS: ${nps.value} (confidence: ${nps.confidence})`);
 *
 * // Get complete summary
 * const summary = getMetricsSummary();
 * console.log(`Overall health: ${summary.overallHealthScore}`);
 * ```
 */

// Goals Definition
export {
  type HeartDimension,
  type HeartGoal,
  HEART_GOALS,
  getGoalsForDimension,
  getAllGoals,
  getGoalById,
} from "./GoalsDefinition";

// Signals Registry
export {
  type SignalValueType,
  type Signal,
  type SignalEvent,
  type SignalFilterOptions,
  SIGNALS,
  getSignalById,
  getSignalsForGoal,
  getAllSignals,
  recordSignal,
  getSignalValues,
  clearSignals,
} from "./SignalsRegistry";

// Metrics Calculator
export {
  type MetricResult,
  type GoalProgress,
  type DimensionScore,
  type MetricsSummary,
  calculateMetric,
  calculateGoalProgress,
  calculateDimensionScore,
  getMetricsSummary,
} from "./MetricsCalculator";
